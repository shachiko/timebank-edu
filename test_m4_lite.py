# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M4-LITE
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Nội dung kiểm thử:
1. Sau 'hoan_thanh', 2 bên đánh giá nhau (sao 1-5 + nhận xét), mỗi chiều 1 lần.
2. CHẶN ĐÁNH GIÁ 2 LẦN: Mỗi thành viên chỉ được đánh giá 1 lần duy nhất cho mỗi phiên.
3. Dashboard HS (/profile): Thống kê giờ đã dạy, giờ đã học, sao TB.
4. Dashboard GV/Admin (/admin): Thống kê tổng phiên, tổng giờ lưu thông, top tích cực, AI cảnh báo, kết quả học tập.
5. Xuất CSV (/admin/export-csv): Gộp sessions + credits_ledger + ratings + quiz_results + ai_logs.
6. BẢO MẬT PII: File CSV tuyệt đối KHÔNG lộ tên thật của học sinh/giáo viên (được ẩn danh hóa thành mã định danh).
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import unittest
import sqlite3
from pathlib import Path

# Đảm bảo đường dẫn import app
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app, init_db, DATABASE_PATH, get_db


class TestMilestoneM4Lite(unittest.TestCase):
    def setUp(self):
        """Khởi tạo môi trường kiểm thử với test client và nạp lại CSDL sạch"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Tạo lại cơ sở dữ liệu mẫu ban đầu
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
        init_db()

    def login(self, username, password="admin123"):
        """Hàm trợ giúp đăng nhập sạch phiên"""
        self.client.get("/logout", follow_redirects=True)
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def test_01_peer_rating_bidirectional_success(self):
        """
        [TEST CASE 1]: Sau khi phiên 'hoan_thanh', hai bên đánh giá nhau (1-5 sao + nhận xét)
        - Session 4: An dạy Toán cho Minh (đã hoàn thành)
        - Chiều 1: An (người dạy) đánh giá Minh (người học)
        - Chiều 2: Minh (người học) đánh giá An (người dạy)
        """
        print("\n--- TEST CASE 1: Đánh giá tương hỗ 2 chiều sau buổi học hoàn thành ---")
        # Xóa đánh giá demo cũ của Session 4 để kiểm thử cả 2 chiều mới tinh
        with app.app_context():
            db = get_db()
            db.execute("DELETE FROM ratings WHERE session_id = 4")
            db.commit()

        # 1. An (HS12001 - Người dạy) đánh giá Minh
        self.login("HS12001")
        res1 = self.client.post("/sessions/4/rate", data={
            "so_sao": "5",
            "nhan_xet": "Minh tiếp thu rất nhanh và chủ động hỏi bài!"
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)
        self.assertIn("Cảm ơn bạn đã gửi đánh giá tương hỗ".encode("utf-8"), res1.data)

        # 2. Minh (HS11004 - Người học) đánh giá An
        self.login("HS11004")
        res2 = self.client.post("/sessions/4/rate", data={
            "so_sao": "5",
            "nhan_xet": "Anh An giảng bài cực kỳ dễ hiểu và nhiệt tình!"
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        self.assertIn("Cảm ơn bạn đã gửi đánh giá tương hỗ".encode("utf-8"), res2.data)

        # Kiểm tra database lưu đủ 2 bản ghi cho session 4
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM ratings WHERE session_id = 4")
            rows = cur.fetchall()
            self.assertEqual(len(rows), 2, "Phiên học phải có đủ 2 chiều đánh giá")
            print("  -> Cả hai bên đã đánh giá nhau thành công (1-5 sao + nhận xét).")

    def test_02_block_second_rating_attempt(self):
        """
        [TEST CASE 2 - TIÊU CHÍ NGHIỆM THU]: Đánh giá 2 lần -> BỊ CHẶN
        - An đã đánh giá Session 4 rồi, nếu gửi tiếp lần 2 -> Hệ thống phải chặn lại và cảnh báo
        - Không ghi nhận thêm bản ghi mới trong bảng ratings
        """
        print("\n--- TEST CASE 2: Kiểm thử CHẶN đánh giá lần 2 ---")
        # An đánh giá lần 1
        self.login("HS12001")
        self.client.post("/sessions/4/rate", data={
            "so_sao": "5",
            "nhan_xet": "Buổi học rất tích cực!"
        }, follow_redirects=True)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM ratings WHERE session_id = 4 AND nguoi_danh_gia_id = 3")
            count_before = cur.fetchone()[0]

        # An cố tình gửi đánh giá lần 2 trên cùng Session 4
        res_second = self.client.post("/sessions/4/rate", data={
            "so_sao": "1",
            "nhan_xet": "Cố tình đánh giá lần 2"
        }, follow_redirects=True)

        self.assertEqual(res_second.status_code, 200)
        self.assertTrue(
            "đã đánh giá buổi học này rồi".encode("utf-8") in res_second.data or "chỉ được đánh giá 1 lần duy nhất".encode("utf-8") in res_second.data,
            "Hệ thống phải hiển thị thông báo cảnh báo chặn đánh giá lần 2"
        )

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM ratings WHERE session_id = 4 AND nguoi_danh_gia_id = 3")
            count_after = cur.fetchone()[0]
            self.assertEqual(count_after, count_before, "Bảng ratings KHÔNG được thêm dòng mới khi bị chặn")

        print("  -> Hệ thống chặn đánh giá lần 2 thành công, mỗi chiều chỉ được đánh giá 1 lần duy nhất.")

    def test_03_student_dashboard_metrics(self):
        """
        [TEST CASE 3]: Dashboard Học sinh (/profile)
        - Hiển thị: Giờ đã dạy, Giờ đã học, Sao trung bình (Sao TB)
        """
        print("\n--- TEST CASE 3: Kiểm thử Dashboard Học sinh có giờ đã dạy/học và sao TB ---")
        # Đăng nhập An (HS12001 - user_id=3)
        # Trong dữ liệu demo: An dạy Session 1 (1h) + Session 4 (1h) = 2.0h đã dạy
        # An học Session 3 (1h) = 1.0h đã học
        self.login("HS12001")
        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Tổng giờ đã dạy", html, "Phải có chỉ số Tổng giờ đã dạy")
        self.assertIn("Tổng giờ đã học", html, "Phải có chỉ số Tổng giờ đã học")
        self.assertIn("Đánh giá trung bình", html, "Phải có chỉ số Đánh giá trung bình (Sao TB)")
        self.assertIn("2.0", html, "Số giờ đã dạy của An phải là 2.0h")
        self.assertIn("1.0", html, "Số giờ đã học của An phải là 1.0h")

        print("  -> Dashboard Học sinh hiển thị đầy đủ, chính xác: Giờ đã dạy (2.0h), Giờ đã học (1.0h), Sao TB.")

    def test_04_admin_dashboard_metrics_and_top_students(self):
        """
        [TEST CASE 4]: Dashboard Giáo viên / Quản trị viên (/admin)
        - Tổng phiên, Tổng giờ lưu thông
        - Top tích cực (Bảng vinh danh học sinh)
        - AI cảnh báo sớm
        - Kết quả học tập
        """
        print("\n--- TEST CASE 4: Kiểm thử Dashboard Quản trị/GV có tổng phiên, giờ lưu thông, top tích cực ---")
        self.login("admin")
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)

        html = res.data.decode("utf-8")
        self.assertIn("Tổng phiên học", html, "Phải có thống kê Tổng phiên học")
        self.assertIn("Tổng giờ lưu thông", html, "Phải có thống kê Tổng giờ lưu thông")
        self.assertIn("Top Học Sinh Tích Cực", html, "Phải có khối Top học sinh tích cực nhất")
        self.assertIn("CẢNH BÁO SỚM SƯ PHẠM", html, "Phải có khối AI Cảnh báo sớm")
        self.assertIn("KẾT QUẢ HỌC TẬP", html, "Phải có khối Kết quả học tập qua Quiz")

        print("  -> Dashboard Quản trị viên hiển thị đầy đủ tổng phiên, giờ lưu thông, top tích cực, AI cảnh báo và kết quả học tập.")

    def test_05_export_csv_structure_and_excel_compatibility(self):
        """
        [TEST CASE 5]: Endpoint Xuất CSV (/admin/export-csv)
        - Gộp đủ 5 bảng: sessions, credits_ledger, ratings, quiz_results, ai_logs
        - Tương thích Excel với UTF-8 with BOM (charset=utf-8-sig)
        """
        print("\n--- TEST CASE 5: Kiểm thử xuất CSV gộp 5 bảng tương thích Excel ---")
        self.login("admin")
        res = self.client.get("/admin/export-csv")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers.get("Content-Type"), "text/csv; charset=utf-8-sig")

        # Kiểm tra nội dung chứa đủ 5 bảng
        raw_bytes = res.data
        self.assertTrue(raw_bytes.startswith(b'\xef\xbb\xbf'), "File CSV phải bắt đầu bằng UTF-8 BOM để Excel hiển thị tiếng Việt")

        csv_text = raw_bytes.decode("utf-8-sig")
        self.assertIn("BANG PHIEN HOC (SESSIONS)", csv_text)
        self.assertIn("BANG SO CAI TIN DUNG (CREDITS_LEDGER)", csv_text)
        self.assertIn("BANG DANH GIA TUONG HO (RATINGS)", csv_text)
        self.assertIn("BANG KET QUA QUIZ TRAC NGHIEM (QUIZ_RESULTS)", csv_text)
        self.assertIn("BANG NHAT KY MINH BACH AI (AI_LOGS)", csv_text)

        print("  -> File CSV xuất thành công, có UTF-8 BOM, gộp đầy đủ 5 bảng dữ liệu.")

    def test_06_export_csv_privacy_no_real_names(self):
        """
        [TEST CASE 6 - TIÊU CHÍ NGHIỆM THU]: CSV KHÔNG LỘ TÊN THẬT
        - Mọi họ tên học sinh / giáo viên trong DB phải được ẩn danh hóa
        - Kiểm tra toàn bộ nội dung CSV không được chứa họ tên thật của học sinh trong demo
        """
        print("\n--- TEST CASE 6: Nghiệm thu CSV TUYỆT ĐỐI KHÔNG LỘ TÊN THẬT ---")
        self.login("admin")
        res = self.client.get("/admin/export-csv")
        self.assertEqual(res.status_code, 200)

        csv_text = res.data.decode("utf-8-sig")

        # Danh sách tên thật trong CSDL demo
        real_names = [
            "Nguyễn Hoàng An",
            "Trần Thanh Bình",
            "Lê Kim Chi",
            "Phạm Quang Minh",
            "Vũ Thu Hà",
            "Thầy Nguyễn Văn Đức"
        ]

        # Kiểm tra nghiêm ngặt không có tên nào xuất hiện trong file CSV
        for name in real_names:
            self.assertNotIn(name, csv_text, f"Vi phạm bảo mật PII: Tên thật '{name}' bị lộ trong file CSV xuất ra!")

        # Đồng thời kiểm tra mã định danh ẩn danh có mặt đầy đủ
        self.assertIn("HS12001", csv_text)
        self.assertIn("HS11002", csv_text)
        self.assertIn("HS10003", csv_text)

        print("  -> Tuyệt đối an toàn: Toàn bộ họ tên thật đã được ẩn danh hóa thành mã học sinh (HS12001, HS11002...).")


if __name__ == "__main__":
    unittest.main(verbosity=2)
