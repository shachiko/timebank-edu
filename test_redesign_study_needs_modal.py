"""
Kiểm thử tự động cho:
1. Redesign Modal 'Môn Cần Hỗ Trợ & Khung Giờ Rảnh' 2 cột (cuộn độc lập, nút Lưu cố định, lưu đúng CSDL).
2. Nút '📝 Đăng ký học' trên thẻ gợi ý AI, mở form đặt lịch, gửi qua AJAX, cập nhật nút 'Đã gửi yêu cầu'.
3. Chế độ Giám sát Sư phạm cho Trợ giảng/Giáo viên/Quản trị viên vào phòng học ảo mà không làm hỏng logic điểm danh 80%.
"""
import unittest
import json
from app import app, get_db


class TestRedesignStudyNeedsModal(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-study-needs-redesign"
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        self.db = get_db()
        self.cur = self.db.cursor()

    def tearDown(self):
        self.app_context.pop()

    def login_user(self, user_id=4, username="demo_hocsinh", role="hoc_sinh", school_id=1):
        """Helper đăng nhập phiên làm việc giả lập"""
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["ma_hoc_sinh"] = username
            sess["ho_ten"] = "Học sinh Test"
            sess["vai_tro"] = role
            sess["truong_id"] = school_id
            sess["so_du_gio"] = 15.0
            sess["lop"] = "12A1"

    def test_01_update_study_needs_new_2column_format(self):
        """1. Kiểm tra lưu dữ liệu từ modal 2 cột mới (danh sách môn, mức độ chung, ghi chú chung, time slots T2-CN)"""
        self.login_user(user_id=4)

        # Gửi form theo cấu trúc 2 cột mới
        post_data = {
            "mon_hoc": ["Toán", "Hóa", "Tiếng Anh"],
            "muc_do": "nang_cao",
            "ghi_chu": "Trọng tâm phương trình lượng giác và đề thi thử",
            "slot_start_t2": ["08:00", "14:00"],
            "slot_end_t2": ["10:00", "16:00"],
            "slot_start_t5": ["19:30"],
            "slot_end_t5": ["21:30"],
            "gio_ranh_khac": "Linh hoạt cuối tuần"
        }

        resp = self.client.post("/profile/update-study-needs", data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra CSDL bảng users: mon_can_ho_tro và gio_ranh
        self.cur.execute("SELECT mon_can_ho_tro, gio_ranh FROM users WHERE id = 4")
        u = self.cur.fetchone()
        self.assertIsNotNone(u)

        # Kiểm tra JSON môn cần hỗ trợ
        study_needs = json.loads(u["mon_can_ho_tro"])
        self.assertEqual(len(study_needs), 3)
        subjects = [n["mon"] for n in study_needs]
        self.assertListEqual(sorted(subjects), ["Hóa", "Tiếng Anh", "Toán"])
        for n in study_needs:
            self.assertEqual(n["muc_do"], "Nâng cao")
            self.assertEqual(n["ghi_chu"], "Trọng tâm phương trình lượng giác và đề thi thử")

        # Kiểm tra CSDL users.gio_ranh
        self.assertIsNotNone(u["gio_ranh"])
        gio_ranh_val = u["gio_ranh"]
        self.assertIn("Thứ 2 (08:00 - 10:00, 14:00 - 16:00)", gio_ranh_val)
        self.assertIn("Thứ 5 (19:30 - 21:30)", gio_ranh_val)
        self.assertIn("Linh hoạt cuối tuần", gio_ranh_val)

    def test_02_update_study_needs_via_ajax(self):
        """2. Kiểm tra lưu dữ liệu qua AJAX trả về JSON thành công"""
        self.login_user(user_id=4)

        post_data = {
            "mon_hoc": ["Vật lý"],
            "muc_do": "co_ban",
            "ghi_chu": "Phần điện xoay chiều",
            "slot_start_t3": ["08:30"],
            "slot_end_t3": ["10:30"],
            "gio_ranh_khac": ""
        }

        resp = self.client.post(
            "/profile/update-study-needs",
            data=post_data,
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("thành công", data.get("message", "").lower())

    def test_03_modal_render_on_profile_page(self):
        """3. Kiểm tra trang /profile render đúng modal 2 cột, nút Lưu và script khởi tạo"""
        self.login_user(user_id=4)
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)
        html = resp.get_data(as_text=True)

        # Kiểm tra ID modal, nút Lưu, các container mới
        self.assertIn('id="modalStudyNeeds"', html)
        self.assertIn('id="btnSaveStudyNeeds"', html)
        self.assertIn('id="selectSubjectDropdown"', html)
        self.assertIn('id="selectedSubjectsChips"', html)
        self.assertIn('id="daysScheduleList"', html)
        self.assertIn('💾 Lưu thay đổi', html)

    def test_04_ai_smart_suggestions_and_quick_booking(self):
        """4. Kiểm tra API AI smart suggestions có da_gui_yeu_cau và đặt lịch nhanh qua AJAX"""
        # Đảm bảo có ít nhất 1 kỹ năng đã duyệt từ user khác
        self.cur.execute("""
            SELECT s.id, s.user_id, s.tieu_de, u.ho_ten 
            FROM skills s 
            JOIN users u ON s.user_id = u.id 
            WHERE s.trang_thai_duyet = 'da_duyet' AND s.user_id != 4
            LIMIT 1
        """)
        skill = self.cur.fetchone()
        if not skill:
            # Tạo 1 skill mẫu
            self.cur.execute("""
                INSERT INTO skills (user_id, truong_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
                VALUES (2, 1, 'Toán', 'Kèm giải tích 12', 'Ôn thi đại học', 'da_duyet')
            """)
            self.db.commit()
            skill_id = self.cur.lastrowid
        else:
            skill_id = skill["id"]

        self.login_user(user_id=4)

        # Gọi API smart-suggestions
        resp = self.client.get("/api/skills/smart-suggestions")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("suggestions", data)

        # Kiểm tra cấu trúc suggestion: có book_url và da_gui_yeu_cau
        if data["suggestions"]:
            first_sug = data["suggestions"][0]
            self.assertIn("da_gui_yeu_cau", first_sug)
            self.assertIn("book_url", first_sug)
            self.assertNotIn("${sug.book_url}", first_sug["book_url"])

        # Đặt lịch nhanh qua AJAX tới /sessions/book
        book_resp = self.client.post(
            "/sessions/book",
            data={
                "skill_id": str(skill_id),
                "thoi_gian_bat_dau": "2026-10-25 15:00:00",
                "so_gio": "1.0"
            },
            headers={"X-Requested-With": "XMLHttpRequest"}
        )
        self.assertEqual(book_resp.status_code, 200)
        book_data = book_resp.get_json()
        self.assertTrue(book_data.get("success"))
        self.assertIn("redirect_url", book_data)
        self.assertIn("my-schedule", book_data["redirect_url"])

        # Gọi lại API smart-suggestions, kỹ năng này phải có da_gui_yeu_cau == True
        resp2 = self.client.get("/api/skills/smart-suggestions")
        data2 = resp2.get_json()
        matched = [s for s in data2.get("suggestions", []) if s["id"] == skill_id]
        if matched:
            self.assertTrue(matched[0]["da_gui_yeu_cau"])

    def test_05_virtual_room_supervisor_role_isolation(self):
        """5. Kiểm tra Trợ giảng/Giám thị vào phòng học ảo không làm hỏng logic điểm danh 80%"""
        # Tạo 1 phiên học giữa user 4 (người học) và user 2 (gia sư)
        self.cur.execute("""
            INSERT INTO sessions (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, truong_id)
            VALUES (1, 2, 4, '2026-10-20 09:00:00', 1.0, 'da_dat', 1)
        """)
        self.db.commit()
        session_id = self.cur.lastrowid

        # Đăng nhập vai trò Giám thị / Giáo viên (user 1)
        self.login_user(user_id=1, username="admin_edu", role="admin", school_id=1)

        # Vào phòng học ảo qua route /sessions/<session_id>/room
        room_resp = self.client.get(f"/sessions/{session_id}/room")
        self.assertEqual(room_resp.status_code, 200)
        html = room_resp.get_data(as_text=True)

        # Kiểm tra giao diện có banner Giám sát Sư phạm
        self.assertIn("Chế độ Giám sát Sư phạm", html)
        self.assertIn("Chế độ Giám sát Sư phạm (GV/Admin)", html)
        self.assertIn("Đang giám sát", html)

        # Kiểm tra CSDL: session_attendance KHÔNG có bản ghi nào của supervisor (user 1)
        self.cur.execute("SELECT COUNT(*) AS cnt FROM session_attendance WHERE session_id = ? AND user_id = 1", (session_id,))
        att_cnt = self.cur.fetchone()
        self.assertEqual(att_cnt["cnt"], 0)


if __name__ == "__main__":
    unittest.main()
