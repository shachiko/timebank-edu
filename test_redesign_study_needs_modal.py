# -*- coding: utf-8 -*-
"""
Test Suite: REDESIGN MODAL "MÔN CẦN HỖ TRỢ & GIỜ RẢNH"
Nghiệm thu:
1. Mở modal -> layout 2 cột gọn gàng, scrollable, header & footer cố định
2. Chọn nhiều môn qua dropdown -> tag/chip hiển thị
3. Tích ngày T2, T4 -> chọn giờ -> thêm nhiều khung giờ trong 1 ngày
4. Bấm Lưu -> dữ liệu lưu vào DB, thông báo thành công
5. Mở lại modal -> dữ liệu đã lưu hiện đúng
6. Tương thích ngược format cũ
7. AI tìm khung giờ chung hoạt động chính xác với khung giờ mới
"""
import unittest
import json
import re
from app import app, get_db, find_common_time_slots


class TestRedesignStudyNeedsModal(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-redesign-modal"
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        self.db = get_db()
        self.cur = self.db.cursor()

    def tearDown(self):
        self.app_context.pop()

    def login_user(self, user_id=4, username="demo_hocsinh", role="hoc_sinh", school_id=99):
        """Helper đăng nhập phiên làm việc giả lập"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["ma_hoc_sinh"] = username
            sess["ho_ten"] = "Học sinh Test"
            sess["vai_tro"] = role
            sess["truong_id"] = school_id
            sess["so_du_gio"] = 10.0
            sess["lop"] = "12A1"

    def test_01_modal_ui_structure_in_profile(self):
        """1. Kiểm tra cấu trúc HTML modal 2 cột, header & footer cố định, các ID và element bắt buộc"""
        self.login_user(user_id=4)
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Kiểm tra modal tồn tại và có các thuộc tính scrollable, cố định
        self.assertIn('id="modalStudyNeeds"', html)
        self.assertIn('id="formStudyNeeds"', html)
        self.assertIn('modal-dialog-scrollable', html)
        self.assertIn('overflow-y-auto', html)

        # Kiểm tra 2 cột: Môn học (trái) và Giờ rảnh (phải)
        self.assertIn('col-12 col-md-5', html)
        self.assertIn('col-12 col-md-7', html)
        self.assertIn('Môn Cần Hỗ Trợ', html)
        self.assertIn('Khung Giờ Rảnh', html)

        # Kiểm tra Dropdown chọn môn & Chips container
        self.assertIn('id="selectSubjectDropdown"', html)
        self.assertIn('id="selectedSubjectsChips"', html)
        self.assertIn('id="selectStudyLevel"', html)
        self.assertIn('id="inputStudyNote"', html)

        # Kiểm tra danh sách 7 ngày T2 - CN
        for day in ['t2', 't3', 't4', 't5', 't6', 't7', 'cn']:
            self.assertIn(f'id="chk_{day}"', html)
            self.assertIn(f'id="btnAddSlot_{day}"', html)
            self.assertIn(f'id="slots_{day}"', html)

        # Kiểm tra Footer: nút Hủy bỏ và nút Lưu thay đổi nổi bật
        self.assertIn('id="btnCancelStudyNeeds"', html)
        self.assertIn('id="btnSaveStudyNeeds"', html)
        self.assertIn('Lưu thay đổi', html)

    def test_02_submit_new_two_column_format(self):
        """2. Kiểm tra lưu dữ liệu theo format mới: nhiều môn, mức độ chung, ghi chú chung, nhiều slot trong ngày"""
        self.login_user(user_id=4)

        post_data = {
            "mon_hoc": ["Toán", "Lý", "Tin học"],
            "muc_do": "nang_cao",
            "ghi_chu": "Phần kiến thức lập trình đồ họa và hình học không gian",
            # T2 có 2 khung giờ: 08:00 - 10:00 và 14:00 - 16:00
            "slot_start_t2": ["08:00", "14:00"],
            "slot_end_t2": ["10:00", "16:00"],
            # T4 có 1 khung giờ: 19:00 - 21:00
            "slot_start_t4": ["19:00"],
            "slot_end_t4": ["21:00"],
            "gio_ranh_khac": "Linh hoạt trao đổi qua Zalo cuối tuần"
        }

        resp = self.client.post("/profile/update-study-needs", data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Xác minh trong CSDL
        self.cur.execute("SELECT mon_can_ho_tro, gio_ranh FROM users WHERE id = 4")
        row = self.cur.fetchone()
        self.assertIsNotNone(row)

        study_needs = json.loads(row["mon_can_ho_tro"])
        self.assertEqual(len(study_needs), 3)
        subjects = [s["mon"] for s in study_needs]
        self.assertEqual(subjects, ["Toán", "Lý", "Tin học"])
        for s in study_needs:
            self.assertEqual(s["muc_do"], "Nâng cao")
            self.assertEqual(s["ghi_chu"], "Phần kiến thức lập trình đồ họa và hình học không gian")

        gio_ranh = row["gio_ranh"]
        self.assertIn("Thứ 2 (08:00 - 10:00, 14:00 - 16:00)", gio_ranh)
        self.assertIn("Thứ 4 (19:00 - 21:00)", gio_ranh)
        self.assertIn("Linh hoạt trao đổi qua Zalo cuối tuần", gio_ranh)

    def test_03_ajax_submission_returns_json(self):
        """3. Kiểm tra submit bằng AJAX nhận phản hồi JSON thành công"""
        self.login_user(user_id=4)

        post_data = {
            "mon_hoc": ["Hóa", "Sinh"],
            "muc_do": "luyen_thi",
            "ghi_chu": "Luyện đề thi THPT Quốc gia",
            "slot_start_t6": ["14:30"],
            "slot_end_t6": ["17:00"],
            "gio_ranh_khac": "Rảnh chiều T6"
        }

        resp = self.client.post(
            "/profile/update-study-needs",
            data=post_data,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertIn("thành công", data["message"].lower())
        self.assertEqual(len(data["mon_can_ho_tro"]), 2)
        self.assertIn("Thứ 6 (14:30 - 17:00)", data["gio_ranh"])

    def test_04_profile_renders_updated_data(self):
        """4. Mở lại trang /profile hiển thị đầy đủ môn đã chọn và giờ rảnh"""
        self.login_user(user_id=4)

        # Cập nhật dữ liệu
        post_data = {
            "mon_hoc": ["Văn", "Tiếng Anh"],
            "muc_do": "co_ban",
            "ghi_chu": "Ngữ pháp và viết đoạn văn",
            "slot_start_t7": ["08:30"],
            "slot_end_t7": ["11:00"],
            "gio_ranh_khac": "Buổi sáng rảnh"
        }
        self.client.post("/profile/update-study-needs", data=post_data, follow_redirects=True)

        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Kiểm tra hiển thị ở badge profile
        self.assertIn("Văn", html)
        self.assertIn("Tiếng Anh", html)
        self.assertIn("Thứ 7 (08:30 - 11:00)", html)

    def test_05_common_time_slots_with_specific_hours(self):
        """5. Thuật toán find_common_time_slots nhận diện thông minh khung giờ HH:MM và ghép cặp"""
        # User 1 rảnh T2 từ 08:00 - 10:00 (buổi sáng)
        u1_ranh = "Thứ 2 (08:00 - 10:00), Thứ 4 (14:00 - 16:00)"
        # Tutor rảnh Thứ 2 (Sáng, Tối)
        tutor_ranh = "Thứ 2 (Sáng, Tối), Thứ 5 (Chiều)"

        common = find_common_time_slots(u1_ranh, tutor_ranh)
        self.assertIn("Thứ 2", common)
        self.assertIn("Sáng", common)


if __name__ == "__main__":
    unittest.main()
