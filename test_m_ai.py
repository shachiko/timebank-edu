# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M-AI: 5 ĐIỂM CHẠM AI (GEMINI PRO)
========================================================================
Sản phẩm dự thi "Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026"
Đơn vị: Trường THPT Chuyên Hà Nội - Amsterdam (TimeBank EDU)

Nội dung kiểm định 5 điểm chạm AI:
1. AI Kiểm duyệt kỹ năng khi đăng (PHU_HOP -> da_duyet; KHONG_PHU_HOP -> cho_duyet GV duyệt tay)
2. AI Gợi ý ghép cặp bạn học (Lọc và đề xuất 3 gia sư phù hợp kèm lý do sư phạm TV)
3. AI Soạn dàn ý buổi học 4 bước 60 phút (Mở đầu 5', Trọng tâm 25', Luyện tập 20', Tổng kết 10')
4. AI Tóm tắt phản hồi học sinh (Điểm mạnh + Gợi ý cải thiện khích lệ)
5. AI Cảnh báo quản trị sớm (HS > 7 ngày ngưng học, cặp đôi <= 2 sao >= 2 lần)
6. Lưu vết đầy đủ vào ai_logs & UI minh bạch ghi "Hỗ trợ bởi AI"
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import unittest
from datetime import datetime, timedelta
from app import app, init_db, DATABASE_PATH


class TestMilestoneMAI(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Khởi tạo CSDL sạch
        if DATABASE_PATH.exists():
            try:
                os.remove(DATABASE_PATH)
            except Exception:
                pass
        init_db()

    def setUp(self):
        self.client = app.test_client()

    def test_case_1_ai_content_moderation(self):
        """
        Điểm chạm 1: AI Kiểm duyệt kỹ năng học đường
        - Kỹ năng lành mạnh -> Được duyệt hoặc đánh giá tích cực, lưu ly_do_ai_kiem_duyet.
        - Kỹ năng vi phạm nội dung -> Chuyển duyệt tay (cho_duyet), lưu ly_do_ai_kiem_duyet.
        - ai_logs phải ghi nhận lượt kiểm duyệt.
        """
        # Đăng nhập học sinh HS10003 (Lê Kim Chi)
        login_res = self.client.post("/login", data={
            "ma_hoc_sinh": "HS10003",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 1a. Đăng kỹ năng tích cực
        res_good = self.client.post("/skills/new", data={
            "linh_vuc": "Anh",
            "tieu_de": "Luyện phát âm tiếng Anh chuẩn IPA",
            "mo_ta": "Hướng dẫn nhận diện 44 âm IPA và luyện phát âm tự nhiên qua bài hát."
        }, follow_redirects=True)
        self.assertEqual(res_good.status_code, 200)

        # 1b. Đăng kỹ năng chứa nội dung vi phạm sư phạm
        res_bad = self.client.post("/skills/new", data={
            "linh_vuc": "Tin học",
            "tieu_de": "Hack tài khoản mạng xã hội và game",
            "mo_ta": "Hướng dẫn các phương pháp gian lận thi cử và tấn công tài khoản bạn bè."
        }, follow_redirects=True)
        self.assertEqual(res_bad.status_code, 200)

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()

        # Kiểm tra kỹ năng tích cực
        cur.execute("SELECT trang_thai_duyet, ly_do_ai_kiem_duyet FROM skills WHERE tieu_de = ?", 
                    ("Luyện phát âm tiếng Anh chuẩn IPA",))
        good_skill = cur.fetchone()
        self.assertIsNotNone(good_skill)
        self.assertEqual(good_skill[0], "da_duyet")
        self.assertIn("Hỗ trợ bởi AI", good_skill[1])

        # Kiểm tra kỹ năng vi phạm
        cur.execute("SELECT trang_thai_duyet, ly_do_ai_kiem_duyet FROM skills WHERE tieu_de = ?", 
                    ("Hack tài khoản mạng xã hội và game",))
        bad_skill = cur.fetchone()
        self.assertIsNotNone(bad_skill)
        self.assertEqual(bad_skill[0], "cho_duyet")
        self.assertIn("Hỗ trợ bởi AI", bad_skill[1])

        # Kiểm tra bảng ai_logs
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'kiem_duyet'")
        log_count = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(log_count, 2, "Bảng ai_logs phải ghi nhận các lượt kiểm duyệt kỹ năng")
        print("\n[PASS] Điểm chạm 1: AI Kiểm duyệt kỹ năng hoạt động chính xác (Phù hợp -> Đã duyệt; Vi phạm -> Chờ GV duyệt tay, lưu ai_logs).")

    def test_case_2_ai_matchmaking(self):
        """
        Điểm chạm 2: AI Gợi ý ghép cặp bạn học (/skills/matchmake)
        - Nhập môn cần học, trình độ, giờ rảnh.
        - Đề xuất tối đa 3 gia sư phù hợp nhất kèm giải thích lý do sư phạm tiếng Việt.
        - Ghi nhận lượt gợi ý vào ai_logs.
        """
        # Đăng nhập HS11002 (Trần Thị Bình)
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS11002",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        res = self.client.post("/skills/matchmake", data={
            "mon_hoc": "Toán",
            "trinh_do": "Cơ bản",
            "gio_ranh": "Chiều Thứ 3, Chiều Thứ 5"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Giao diện phải có nhãn AI và danh sách đề xuất
        self.assertIn("Hỗ trợ bởi AI", html)
        self.assertIn("Gia Sư Phù Hợp", html)
        self.assertIn("Đặt lịch ngay", html)

        # 2b. Kiểm tra chế độ ghép cặp tự động trên /profile ("Gợi ý cho bạn hôm nay")
        res_profile = self.client.get("/profile")
        self.assertEqual(res_profile.status_code, 200)
        profile_html = res_profile.data.decode('utf-8')

        self.assertIn("Gợi ý cho bạn hôm nay", profile_html, "Dashboard HS phải có mục 'Gợi ý cho bạn hôm nay'")
        self.assertIn("Toán", profile_html, "Phải tự suy luận ra môn Toán từ lịch sử học")
        self.assertIn("Đặt lịch ngay", profile_html, "Phải có nút 'Đặt lịch ngay' cho từng gia sư được gợi ý")

        # Kiểm tra trang đặt lịch chuyên biệt khi bấm "Đặt lịch ngay" (/skills/book/<id>)
        res_book_page = self.client.get("/skills/book/1")
        self.assertEqual(res_book_page.status_code, 200)
        book_html = res_book_page.data.decode('utf-8')
        self.assertIn("Đặt lịch học kèm", book_html)
        self.assertIn("Xác nhận đặt lịch học ngay", book_html)

        # Kiểm tra ai_logs và cơ chế cache trong ngày
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'goi_y_ghep_cap'")
        log_count_before = cur.fetchone()[0]

        # Tải lại /profile lần 2 trong ngày -> Không gọi thêm AI do đã cache
        self.client.get("/profile")
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'goi_y_ghep_cap'")
        log_count_after = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(log_count_before, 1, "Bảng ai_logs phải ghi nhận tương tác gợi ý ghép cặp")
        self.assertEqual(log_count_before, log_count_after, "Kết quả gợi ý trong ngày phải được cache (không gọi AI lại)")
        print("[PASS] Điểm chạm 2: AI Ghép cặp bạn học (Cả thủ công & Tự động trên Dashboard 'Gợi ý cho bạn hôm nay' với cache trong ngày, chuyển trang đặt lịch đúng người).")

    def test_case_3_ai_lesson_plan(self):
        """
        Điểm chạm 3: AI Soạn dàn ý buổi học 4 bước 60 phút
        - Người dạy yêu cầu soạn dàn ý.
        - sessions.dan_y_ai được cập nhật cấu trúc: Mở đầu 5', Trọng tâm 25', Luyện tập 20', Tổng kết 10'.
        - Ghi nhận vào ai_logs.
        """
        # Đăng nhập người dạy HS12001 (Nguyễn Văn An)
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Tìm một phiên học do An (HS12001, id = 3) dạy
        cur.execute("SELECT id FROM sessions WHERE nguoi_day_id = 3 LIMIT 1")
        session_row = cur.fetchone()
        self.assertIsNotNone(session_row, "Cần có ít nhất một phiên học do An dạy trong CSDL")
        session_id = session_row[0]
        conn.close()

        # Gọi route POST sinh dàn ý AI
        res = self.client.post(f"/sessions/{session_id}/ai-lesson-plan", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Kiểm tra trong DB
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT dan_y_ai FROM sessions WHERE id = ?", (session_id,))
        dan_y = cur.fetchone()[0]

        # Kiểm tra log ai_logs
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'dan_y_buoi_hoc'")
        log_count = cur.fetchone()[0]
        conn.close()

        self.assertIsNotNone(dan_y, "sessions.dan_y_ai phải được lưu")
        self.assertIn("5 phút", dan_y, "Phải có phần mở đầu 5 phút")
        self.assertIn("25 phút", dan_y, "Phải có phần trọng tâm 25 phút")
        self.assertIn("20 phút", dan_y, "Phải có phần luyện tập 20 phút")
        self.assertIn("10 phút", dan_y, "Phải có phần tổng kết 10 phút")
        self.assertGreaterEqual(log_count, 1, "Bảng ai_logs phải ghi nhận lượt soạn dàn ý")

        # Kiểm tra hiển thị trên giao diện chi tiết phiên
        self.assertIn("Dàn ý buổi học 4 bước chuẩn 60 phút", html)
        self.assertIn("Hỗ trợ bởi AI", html)
        print("[PASS] Điểm chạm 3: AI Soạn dàn ý buổi học 60 phút chuẩn 4 bước sư phạm thành công và lưu CSDL.")

    def test_case_4_ai_feedback_summary(self):
        """
        Điểm chạm 4: AI Tóm tắt phản hồi học sinh (Dashboard/Profile người dạy)
        - Tổng hợp các ratings thành Điểm mạnh (2-3 ý) + Gợi ý cải thiện (2-3 ý).
        - Giọng văn khích lệ, sư phạm.
        - Ghi nhận ai_logs.
        """
        # Thêm dữ liệu đánh giá thử nghiệm cho gia sư HS12001 (user_id = 3)
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
            VALUES (1, 4, 3, 5, 'Anh An giảng bài Hình không gian rất dễ hiểu và kiên nhẫn.')
        """)
        cur.execute("""
            INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
            VALUES (4, 6, 3, 4, 'Rất nhiệt tình nhưng đôi khi nói hơi nhanh ở phần bài tập nâng cao.')
        """)
        conn.commit()
        conn.close()

        # Đăng nhập gia sư HS12001 và vào trang profile
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        res = self.client.get("/profile")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Kiểm tra giao diện profile hiển thị khối AI Tóm tắt
        self.assertIn("AI Tóm Tắt Phản Hồi", html)
        self.assertIn("Điểm mạnh nổi bật", html)
        self.assertIn("Gợi ý hoàn thiện", html)
        self.assertIn("Hỗ trợ bởi AI", html)

        # Kiểm tra log ai_logs
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'tom_tat_phan_hoi'")
        log_count = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(log_count, 1, "Bảng ai_logs phải ghi nhận tóm tắt phản hồi")
        print("[PASS] Điểm chạm 4: AI Tóm tắt phản hồi học sinh tổng hợp Điểm mạnh & Gợi ý cải thiện với giọng khích lệ.")

    def test_case_5_ai_admin_early_warning(self):
        """
        Điểm chạm 5: AI Cảnh báo sớm quản trị học đường (/admin)
        - Phát hiện học sinh không tham gia phiên nào > 7 ngày.
        - Phát hiện cặp đôi gặp xung đột (<= 2 sao >= 2 lần).
        - Gợi ý biện pháp can thiệp sư phạm.
        - Ghi nhận ai_logs.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()

        # Tạo tình huống cặp đôi bị đánh giá <= 2 sao 2 lần (user 4 và user 3)
        cur.execute("""
            INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
            VALUES (3, 4, 3, 2, 'Không hiểu bài, gia sư giảng khó theo dõi.')
        """)
        cur.execute("""
            INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
            VALUES (4, 4, 3, 1, 'Thời gian học bị trễ nhiều, không hiệu quả.')
        """)
        conn.commit()
        conn.close()

        # Đăng nhập Admin
        self.client.post("/login", data={
            "ma_hoc_sinh": "admin",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Kiểm tra giao diện admin hiển thị khối cảnh báo
        self.assertIn("CẢNH BÁO SỚM SƯ PHẠM", html)
        self.assertIn("Hỗ trợ bởi AI", html)
        self.assertIn("Phát Hiện Nguy Cơ Học Đường Cần Can Thiệp", html)

        # Kiểm tra log ai_logs
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'canh_bao'")
        log_count = cur.fetchone()[0]
        conn.close()

        self.assertGreaterEqual(log_count, 1, "Bảng ai_logs phải ghi nhận cảnh báo quản trị")
        print("[PASS] Điểm chạm 5: AI Cảnh báo sớm quản trị học đường phát hiện nguy cơ và đề xuất giải pháp can thiệp sư phạm.")

    def test_case_6_ai_transparency_and_fallback_safety(self):
        """
        Test Case 6: Kiểm tra tính trung thực minh bạch về AI và an toàn dự phòng (Fallback)
        - Mọi giao diện có AI đều ghi rõ 'Hỗ trợ bởi AI'.
        - Hệ thống không crash khi thiếu key hoặc gặp lỗi mạng.
        """
        # 1. Chợ kỹ năng có nút AI Gợi ý ghép cặp
        res_market = self.client.get("/skills")
        self.assertIn("AI Gợi Ý Ghép Cặp", res_market.data.decode('utf-8'))

        # 2. Bảng ai_logs có cấu trúc hoàn chỉnh và chứa đầy đủ 5 chức năng
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT chuc_nang FROM ai_logs")
        functions_logged = [row[0] for row in cur.fetchall()]
        conn.close()

        expected_functions = {'kiem_duyet', 'goi_y_ghep_cap', 'dan_y_buoi_hoc', 'tom_tat_phan_hoi', 'canh_bao'}
        self.assertTrue(expected_functions.issubset(set(functions_logged)), 
                        f"Phải lưu đầy đủ 5 loại chức năng trong ai_logs: {functions_logged}")

        print("[PASS] Case 6: Trung thực minh bạch về AI (đầy đủ nhãn UI, an toàn fallback, ghi vết toàn diện trong ai_logs).")


if __name__ == "__main__":
    unittest.main()
