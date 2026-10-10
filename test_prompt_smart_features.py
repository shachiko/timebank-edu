"""
Bộ kiểm thử tự động cho BỔ SUNG TÍNH NĂNG THÔNG MINH CHO HỌC SINH (5 VIỆC)
- VIỆC 1: Môn cần hỗ trợ (trang hồ sơ học sinh)
- VIỆC 2: Khung giờ rảnh theo tuần (lưu vào users.gio_ranh, tìm khung giờ chung)
- VIỆC 3: AI gợi ý bạn học (API /api/skills/smart-suggestions, 3-5 gợi ý kèm lý do, nút đặt lịch)
- VIỆC 4: Đánh giá sau buổi học (1-5 sao + nhận xét, điểm trung bình ở hồ sơ & vinh danh)
- VIỆC 5: Thông báo đăng ký học (chuông thông báo, gửi email an toàn, xác nhận buổi học)
"""
import unittest
import json
import sqlite3
from app import app, get_db, find_common_time_slots, get_ai_buddy_suggestions, send_booking_notification_email


class TestSmartFeatures(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key-smart-features"
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

        # Tạo database test trong bộ nhớ
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

    # =========================================================================
    # TEST VIỆC 1 & 2: MÔN CẦN HỖ TRỢ & KHUNG GIỜ RẢNH THEO TUẦN
    # =========================================================================
    def test_01_update_study_needs_and_weekly_schedule(self):
        """Kiểm tra lưu môn cần hỗ trợ (nhiều môn, mức độ, ghi chú) và giờ rảnh T2-CN"""
        self.login_user(user_id=4)

        # Gửi form cập nhật môn cần hỗ trợ và khung giờ rảnh
        post_data = {
            "mon_hoc": ["Toán", "Tiếng Anh"],
            "muc_do_Toán": "nang_cao",
            "ghi_chu_Toán": "Hình học không gian lớp 12",
            "muc_do_Tiếng Anh": "co_ban",
            "ghi_chu_Tiếng Anh": "Luyện ngữ pháp & phát âm",
            "ranh_t2_sang": "1",
            "ranh_t2_toi": "1",
            "ranh_t4_chieu": "1",
            "ranh_cn_sang": "1",
            "gio_ranh_khac": "Linh hoạt cuối tuần"
        }

        resp = self.client.post("/profile/update-study-needs", data=post_data, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra CSDL
        self.cur.execute("SELECT mon_can_ho_tro, gio_ranh FROM users WHERE id = 4")
        row = self.cur.fetchone()
        self.assertIsNotNone(row)
        
        # Kiểm tra JSON môn cần hỗ trợ
        study_needs = json.loads(row["mon_can_ho_tro"])
        self.assertEqual(len(study_needs), 2)
        self.assertEqual(study_needs[0]["mon"], "Toán")
        self.assertEqual(study_needs[0]["muc_do"], "Nâng cao")
        self.assertEqual(study_needs[0]["ghi_chu"], "Hình học không gian lớp 12")
        self.assertEqual(study_needs[1]["mon"], "Tiếng Anh")
        self.assertEqual(study_needs[1]["muc_do"], "Cơ bản")

        # Kiểm tra chuỗi giờ rảnh
        gio_ranh = row["gio_ranh"]
        self.assertIn("Thứ 2 (Sáng, Tối)", gio_ranh)
        self.assertIn("Thứ 4 (Chiều)", gio_ranh)
        self.assertIn("Chủ Nhật (Sáng)", gio_ranh)
        self.assertIn("Linh hoạt cuối tuần", gio_ranh)

        # Kiểm tra giao diện /profile hiển thị đúng
        profile_resp = self.client.get("/profile")
        self.assertEqual(profile_resp.status_code, 200)
        html = profile_resp.get_data(as_text=True)
        self.assertIn("Toán", html)
        self.assertIn("Nâng cao", html)
        self.assertIn("Hình học không gian lớp 12", html)
        self.assertIn("Tiếng Anh", html)
        self.assertIn("Thứ 2 (Sáng, Tối)", html)

    def test_02_find_common_time_slots(self):
        """Kiểm tra thuật toán tìm khung giờ chung giữa 2 học sinh"""
        u_ranh = "Thứ 2 (Sáng, Tối), Thứ 4 (Chiều), Thứ 6 (Tối)"
        t_ranh = "Thứ 2 (Tối), Thứ 3 (Sáng), Thứ 4 (Chiều, Tối)"

        common = find_common_time_slots(u_ranh, t_ranh)
        self.assertIn("Thứ 2 (Tối)", common)
        self.assertIn("Thứ 4 (Chiều)", common)

        # Trường hợp không có thứ trùng nhưng có buổi
        u_ranh2 = "Sáng trong tuần"
        t_ranh2 = "Sáng các ngày"
        common2 = find_common_time_slots(u_ranh2, t_ranh2)
        self.assertIn("Sáng trong tuần", common2)

        # Trường hợp trống
        self.assertEqual(find_common_time_slots("", "Thứ 2"), "Linh hoạt sắp xếp")

    # =========================================================================
    # TEST VIỆC 3: NÚT VÀ API AI GỢI Ý BẠN HỌC
    # =========================================================================
    def test_03_api_smart_suggestions(self):
        """Kiểm tra API /api/skills/smart-suggestions trả về 3-5 gợi ý kèm lý do và nút đặt lịch"""
        self.login_user(user_id=4)

        # Đảm bảo học sinh 4 có nhu cầu học Toán
        self.cur.execute("""
            UPDATE users SET 
            mon_can_ho_tro = '[{"mon": "Toán", "muc_do": "Nâng cao", "ghi_chu": "Luyện đề"}]',
            gio_ranh = 'Thứ 2 (Sáng, Tối), Thứ 6 (Chiều)'
            WHERE id = 4
        """)
        self.db.commit()

        # Gọi API
        resp = self.client.get("/api/skills/smart-suggestions")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertTrue(data.get("success"))
        self.assertGreaterEqual(data.get("count"), 1)
        self.assertLessEqual(data.get("count"), 5)

        first_sug = data["suggestions"][0]
        self.assertIn("id", first_sug)
        self.assertIn("tieu_de", first_sug)
        self.assertIn("ho_ten", first_sug)
        self.assertIn("khung_gio_chung", first_sug)
        self.assertIn("sao_tb", first_sug)
        self.assertIn("ai_ly_do", first_sug)
        self.assertIn("book_url", first_sug)
        self.assertIn("/skills/book/", first_sug["book_url"])
        self.assertTrue(len(first_sug["ai_ly_do"]) > 10)

        # Kiểm tra nút bấm trên trang Kho kỹ năng /skills
        market_resp = self.client.get("/skills")
        self.assertEqual(market_resp.status_code, 200)
        market_html = market_resp.get_data(as_text=True)
        self.assertIn('id="btnAiSuggestBuddies"', market_html)
        self.assertIn('openAiBuddySuggestions()', market_html)
        self.assertIn('AI gợi ý bạn học', market_html)

    # =========================================================================
    # TEST VIỆC 4: ĐÁNH GIÁ SAU BUỔI HỌC VÀ ĐIỂM TRUNG BÌNH
    # =========================================================================
    def test_04_session_rating_and_tutor_average(self):
        """Kiểm tra hoàn thành buổi học -> gửi đánh giá 1-5 sao -> điểm hiện ở hồ sơ & vinh danh"""
        # Tạo phiên học hoàn thành giữa HS 4 (người dạy) và HS 5 (người học)
        self.cur.execute("SELECT id FROM skills WHERE user_id = 4 LIMIT 1")
        sk = self.cur.fetchone()
        skill_id = sk[0] if sk else 1

        self.cur.execute("""
            INSERT INTO sessions (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, truong_id)
            VALUES (?, 4, 5, '2026-10-10 10:00:00', 1.0, 'hoan_thanh', 'QR-TEST-RATE-1', 1, 1, 99)
        """, (skill_id,))
        self.db.commit()
        session_id = self.cur.lastrowid

        # HS 5 (người học) gửi đánh giá 5 sao cho HS 4 (người dạy)
        self.login_user(user_id=5, username="demo_hocsinh_2")
        rate_resp = self.client.post(f"/sessions/{session_id}/rate", data={
            "so_sao": "5",
            "nhan_xet": "Bạn giảng bài cực kỳ dễ hiểu, nhiệt tình và đúng giờ!"
        }, follow_redirects=True)
        self.assertEqual(rate_resp.status_code, 200)

        # Kiểm tra CSDL bảng ratings
        self.cur.execute("SELECT * FROM ratings WHERE session_id = ? AND nguoi_danh_gia_id = 5", (session_id,))
        rating_rec = self.cur.fetchone()
        self.assertIsNotNone(rating_rec)
        self.assertEqual(rating_rec["so_sao"], 5)
        self.assertIn("dễ hiểu", rating_rec["nhan_xet"])

        # Kiểm tra chặn đánh giá lần 2 (chống spam)
        rate_again = self.client.post(f"/sessions/{session_id}/rate", data={
            "so_sao": "4",
            "nhan_xet": "Đánh giá lại"
        }, follow_redirects=True)
        self.assertEqual(rate_again.status_code, 200)
        self.assertIn("Bạn đã đánh giá buổi học này rồi", rate_again.get_data(as_text=True))

        # Kiểm tra điểm hiển thị ở trang hồ sơ của người dạy (HS 4)
        self.login_user(user_id=4)
        profile_resp = self.client.get("/profile")
        self.assertEqual(profile_resp.status_code, 200)
        p_html = profile_resp.get_data(as_text=True)
        self.assertIn("Đánh giá trung bình", p_html)
        self.assertIn("5.0", p_html)

        # Kiểm tra điểm hiển thị ở Bảng vinh danh trên trang chủ
        index_resp = self.client.get("/")
        self.assertEqual(index_resp.status_code, 200)
        i_html = index_resp.get_data(as_text=True)
        self.assertIn("Vinh danh Gia sư", i_html)

    # =========================================================================
    # TEST VIỆC 5: THÔNG BÁO ĐĂNG KÝ HỌC & XÁC NHẬN BUỔI HỌC
    # =========================================================================
    def test_05_booking_notification_email_and_confirmation(self):
        """Kiểm tra khi có người đặt lịch -> thông báo chuông cho người dạy -> người dạy xác nhận"""
        # HS 4 có kỹ năng ID 1
        self.cur.execute("SELECT id, user_id FROM skills WHERE user_id = 4 LIMIT 1")
        sk_row = self.cur.fetchone()
        if not sk_row:
            self.cur.execute("""
                INSERT INTO skills (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, truong_id)
                VALUES (4, 'Toán', 'Luyện thi Toán 12 Test', 'Mô tả test', 'da_duyet', 99)
            """)
            self.db.commit()
            skill_id = self.cur.lastrowid
        else:
            skill_id = sk_row[0]

        # Đặt email cho HS 4 để test hàm email an toàn
        self.cur.execute("UPDATE users SET email = 'tutor_test@example.com' WHERE id = 4")
        self.db.commit()

        # HS 5 (người học) đăng nhập và đặt lịch học kỹ năng của HS 4
        self.login_user(user_id=5, username="demo_hocsinh_2")
        book_resp = self.client.post("/sessions/book", data={
            "skill_id": str(skill_id),
            "thoi_gian_bat_dau": "2026-10-15 14:00:00",
            "so_gio": "1.0"
        }, follow_redirects=True)
        self.assertEqual(book_resp.status_code, 200)

        # Kiểm tra CSDL: Bảng notifications phải có thông báo gửi cho HS 4
        self.cur.execute("""
            SELECT * FROM notifications 
            WHERE user_id = 4 AND loai = 'dang_ky_hoc' 
            ORDER BY id DESC LIMIT 1
        """)
        noti = self.cur.fetchone()
        self.assertIsNotNone(noti)
        self.assertIn("đăng ký học", noti["tieu_de"])
        self.assertEqual(noti["da_doc"], 0)
        new_sess_id = noti["session_id"]
        self.assertIsNotNone(new_sess_id)

        # Đăng nhập bằng tài khoản HS 4 (người dạy)
        self.login_user(user_id=4)

        # Kiểm tra chuông thông báo hiển thị trên giao diện (unread count)
        badge_resp = self.client.get("/api/notifications/unread-count")
        self.assertEqual(badge_resp.status_code, 200)
        badge_data = json.loads(badge_resp.data)
        self.assertGreaterEqual(badge_data.get("count"), 1)

        # Người dạy bấm "Xác nhận lịch học" từ route /sessions/<id>/confirm
        confirm_resp = self.client.post(f"/sessions/{new_sess_id}/confirm", follow_redirects=True)
        self.assertEqual(confirm_resp.status_code, 200)
        self.assertIn("Bạn đã xác nhận buổi học thành công", confirm_resp.get_data(as_text=True))

        # Kiểm tra CSDL: Người học (HS 5) phải nhận được thông báo xác nhận từ người dạy
        self.cur.execute("""
            SELECT * FROM notifications 
            WHERE user_id = 5 AND loai = 'xac_nhan' AND session_id = ?
        """, (new_sess_id,))
        confirm_noti = self.cur.fetchone()
        self.assertIsNotNone(confirm_noti)
        self.assertIn("xác nhận", confirm_noti["tieu_de"])

        # Kiểm tra route đánh dấu đã đọc
        read_resp = self.client.post("/notifications/mark-all-read", follow_redirects=True)
        self.assertEqual(read_resp.status_code, 200)
        self.cur.execute("SELECT COUNT(*) FROM notifications WHERE user_id = 4 AND da_doc = 0")
        unread_after = self.cur.fetchone()[0]
        self.assertEqual(unread_after, 0)

    def test_06_send_booking_email_safety(self):
        """Kiểm tra hàm gửi email send_booking_notification_email chạy an toàn không crash khi thiếu SMTP"""
        res, msg = send_booking_notification_email(
            to_email="test@example.com",
            tutor_name="Nguyễn Văn A",
            learner_name="Trần Thị B",
            skill_title="Lập trình Python",
            start_time="2026-10-12 15:00:00",
            duration_hours=1.5,
            session_id=999
        )
        # Vì môi trường test không có SMTP_HOST, hàm phải trả về False kèm thông báo và KHÔNG raise exception
        self.assertFalse(res)
        self.assertIsNotNone(msg)


if __name__ == "__main__":
    unittest.main()
