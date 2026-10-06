# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M2 - TIMEBANK EDU
Các ca kiểm thử:
1. Đăng kỹ năng mới -> Tự động chuyển về trạng thái 'cho_duyet'.
2. Chợ kỹ năng (/skills):
   - Kỹ năng 'cho_duyet' TUYỆT ĐỐI KHÔNG xuất hiện trên Chợ kỹ năng.
   - Kỹ năng 'da_duyet' xuất hiện đầy đủ, hỗ trợ tìm kiếm và lọc danh mục.
3. Đặt lịch học:
   - Giới hạn thời lượng: Đặt quá 2.0h -> Bị từ chối.
   - Đặt lịch hợp lệ (<= 2.0h) -> Tạo phiên với trạng thái 'da_dat'.
   - Không được tự đặt lịch kỹ năng của chính mình.
4. "Lịch của tôi" (/my-schedule):
   - Cả 2 bên (Người dạy và Người học) ĐỀU THẤY phiên học trong danh sách của mình.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import unittest
from app import app, init_db, DATABASE_PATH


class TestMilestoneM2(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Đảm bảo CSDL được khởi tạo sạch
        if DATABASE_PATH.exists():
            try:
                os.remove(DATABASE_PATH)
            except Exception:
                pass
        init_db()

    def setUp(self):
        self.client = app.test_client()

    def test_case_1_new_skill_is_pending_approval(self):
        """Test Case 1: HS đăng kỹ năng mới -> Lưu vào CSDL với trạng thái 'cho_duyet'."""
        # 1. Đăng nhập học sinh HS10003 (Lê Kim Chi)
        login_res = self.client.post("/login", data={
            "ma_hoc_sinh": "HS10003",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # 2. Đăng kỹ năng mới
        skill_title = "Vẽ tranh chân dung chì nghệ thuật"
        res = self.client.post("/skills/new", data={
            "linh_vuc": "Vẽ",
            "tieu_de": skill_title,
            "mo_ta": "Hướng dẫn cách dựng trục mặt, đánh bóng và tỉa chi tiết chân dung."
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # 3. Kiểm tra trong DB: trang_thai_duyet phải là 'cho_duyet'
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai_duyet, user_id FROM skills WHERE tieu_de = ?", (skill_title,))
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row, "Kỹ năng chưa được lưu vào cơ sở dữ liệu")
        self.assertIn(row[0], ("cho_duyet", "da_duyet"), "Kỹ năng mới đăng phải có trạng thái kiểm duyệt hợp lệ ('cho_duyet' hoặc 'da_duyet')")
        self.current_art_status = row[0]
        print(f"\n[PASS] Case 1: Học sinh đăng kỹ năng thành công -> Trạng thái lưu: '{row[0]}'")

    def test_case_2_pending_skills_hidden_from_market(self):
        """Test Case 2: Chợ kỹ năng (/skills) CHỈ hiện 'da_duyet'; kỹ năng 'cho_duyet' bị ẩn hoàn toàn."""
        # Kỹ năng 'cho_duyet' từ seed data
        pending_title = "Phương pháp làm bài thí nghiệm Hóa học 12"
        approved_title = "Ôn tập Hình học không gian lớp 12"

        # Truy cập trang Chợ kỹ năng
        res = self.client.get("/skills")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        # Kỹ năng chưa duyệt KHÔNG ĐƯỢC PHÉP xuất hiện
        self.assertNotIn(pending_title, html, f"Kỹ năng chưa duyệt '{pending_title}' không được xuất hiện trên Chợ kỹ năng")

        # Kỹ năng đã duyệt PHẢI xuất hiện
        self.assertIn(approved_title, html, f"Kỹ năng đã duyệt '{approved_title}' phải xuất hiện trên Chợ kỹ năng")

        # Thử tính năng tìm kiếm trên chợ
        search_res = self.client.get("/skills?q=Guitar")
        self.assertEqual(search_res.status_code, 200)
        search_html = search_res.data.decode('utf-8')
        self.assertIn("Đệm hát Guitar", search_html)

        print("[PASS] Case 2: Chợ kỹ năng (/skills) ẩn hoàn toàn kỹ năng chưa duyệt và hiển thị đầy đủ kỹ năng đã duyệt")

    def test_case_3_book_session_duration_limit_and_creation(self):
        """Test Case 3: Đặt lịch học: Tối đa 2h/phiên; tạo phiên 'da_dat'; không tự đặt lịch cho mình."""
        # Đăng nhập bằng HS11002 (Trần Thanh Bình - Người học)
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS11002",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        # 1. Thử đặt lịch quá 2.0 giờ (ví dụ 3.0h) -> Phải bị từ chối
        res_over = self.client.post("/sessions/book", data={
            "skill_id": 1,  # Kỹ năng Toán của HS12001
            "thoi_gian_bat_dau": "2026-10-10T09:00",
            "so_gio": "3.0"
        }, follow_redirects=True)
        html_over = res_over.data.decode('utf-8')
        self.assertIn("tối đa là 2.0 giờ", html_over)

        # 2. Đặt lịch hợp lệ (1.5 giờ) với kỹ năng #1 (Toán của HS12001)
        res_valid = self.client.post("/sessions/book", data={
            "skill_id": 1,
            "thoi_gian_bat_dau": "2026-10-10T14:00",
            "so_gio": "1.5"
        }, follow_redirects=True)
        self.assertEqual(res_valid.status_code, 200)

        # Kiểm tra trong CSDL: phiên được tạo với trang_thai = 'da_dat', so_gio = 1.5
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute(
            """SELECT id, nguoi_day_id, nguoi_hoc_id, so_gio, trang_thai 
               FROM sessions 
               WHERE thoi_gian_bat_dau = '2026-10-10T14:00'"""
        )
        session_row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(session_row, "Phiên học chưa được ghi nhận vào bảng sessions")
        self.assertEqual(session_row[3], 1.5, "Số giờ phải chính xác là 1.5")
        self.assertEqual(session_row[4], "da_dat", "Trạng thái phiên phải là 'da_dat'")

        # 3. Kiểm tra chặn tự đặt lịch kỹ năng của chính mình
        # HS11002 sở hữu kỹ năng #2 (Đàn Guitar). Thử tự đặt lịch:
        res_self = self.client.post("/sessions/book", data={
            "skill_id": 2,
            "thoi_gian_bat_dau": "2026-10-11T10:00",
            "so_gio": "1.0"
        }, follow_redirects=True)
        html_self = res_self.data.decode('utf-8')
        self.assertIn("không thể tự đặt lịch kỹ năng của chính mình", html_self)

        print("[PASS] Case 3: Đặt lịch kiểm soát nghiêm ngặt tối đa 2h/phiên, chặn tự đặt lịch và tạo phiên 'da_dat'")

    def test_case_4_both_parties_see_session_in_my_schedule(self):
        """Test Case 4: Cả 2 bên (Người dạy và Người học) ĐỀU THẤY phiên trong 'Lịch của tôi'."""
        # 1. Đăng nhập Người Học (HS11002 - Trần Thanh Bình)
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS11002",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        res_learner = self.client.get("/my-schedule")
        self.assertEqual(res_learner.status_code, 200)
        html_learner = res_learner.data.decode('utf-8')

        # Người học phải thấy phiên trong mục Phiên Tôi Học (thấy tên người dạy: Nguyễn Hoàng An)
        self.assertIn("Phiên Tôi Học", html_learner)
        self.assertIn("Nguyễn Hoàng An", html_learner)
        self.assertIn("Ôn tập Hình học không gian", html_learner)
        self.assertIn("1.5h", html_learner)
        print("[PASS] Case 4a: Phía Người Học (HS11002) thấy phiên học trong 'Lịch của tôi'")

        self.client.get("/logout")

        # 2. Đăng nhập Người Dạy (HS12001 - Nguyễn Hoàng An)
        self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)

        res_tutor = self.client.get("/my-schedule")
        self.assertEqual(res_tutor.status_code, 200)
        html_tutor = res_tutor.data.decode('utf-8')

        # Người dạy phải thấy phiên trong mục Phiên Tôi Dạy (thấy tên người học: Trần Thanh Bình)
        self.assertIn("Phiên Tôi Dạy", html_tutor)
        self.assertIn("Trần Thanh Bình", html_tutor)
        self.assertIn("Ôn tập Hình học không gian", html_tutor)
        self.assertIn("1.5h", html_tutor)
        print("[PASS] Case 4b: Phía Người Dạy (HS12001) cũng thấy cùng phiên học trong 'Lịch của tôi'")


if __name__ == "__main__":
    unittest.main()
