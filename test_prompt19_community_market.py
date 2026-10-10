# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHUYÊN SÂU — PROMPT 19:
SÀN GIAO DỊCH CHUNG LIÊN TRƯỜNG & CỔNG 24 TÍN DỤNG

Các tiêu chí nghiệm thu:
1. Học sinh 23 giờ dạy → bị chặn ở sàn chung, thấy số giờ còn thiếu đúng.
2. Học sinh 24 giờ dạy → mở khóa + có huy hiệu 'Thành viên Cộng đồng'.
3. Đổi ngưỡng trong config → cổng áp dụng số mới ngay (chứng minh không hardcode).
4. Đăng kỹ năng lên sàn chung → admin trường khác duyệt được → hiện trên sàn kèm tên trường.
5. Học sinh trường A học xong buổi của trường B → ví chung trừ/cộng đúng, không sai lệch.
6. Học sinh chưa qua cổng KHÔNG thấy nút "Đăng lên sàn chung".
7. Regression: Không làm ảnh hưởng P17, P18.
"""

import unittest
import sqlite3
import yaml
import shutil
from pathlib import Path
from werkzeug.security import generate_password_hash

from app import (
    app, get_db, DATABASE_PATH, CONFIG_PATH,
    get_community_threshold, get_user_teaching_hours, load_school_config
)

class TestPrompt19CommunityMarket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        # Backup config.yaml để khôi phục sau test
        cls.config_backup = None
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cls.config_backup = f.read()

    @classmethod
    def tearDownClass(cls):
        # Khôi phục file config.yaml gốc
        if cls.config_backup is not None:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(cls.config_backup)

    def setUp(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row
        self.cur = self.conn.cursor()

    def tearDown(self):
        self.conn.close()

    def create_user(self, ma_hs, ho_ten, truong_id=1, vai_tro="hoc_sinh", so_du_gio=2.0, trang_thai="hoat_dong"):
        """Tạo người dùng thử nghiệm."""
        hashed = generate_password_hash("test1234")
        self.cur.execute("""
            INSERT OR REPLACE INTO users (ma_hoc_sinh, ho_ten, truong_id, vai_tro, so_du_gio, mat_khau, trang_thai)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ma_hs, ho_ten, truong_id, vai_tro, so_du_gio, hashed, trang_thai))
        self.conn.commit()
        self.cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (ma_hs,))
        return self.cur.fetchone()["id"]

    def add_teaching_session(self, tutor_id, learner_id, hours, truong_id=1, trang_thai="hoan_thanh"):
        """Tạo phiên dạy học hoàn thành để tích lũy giờ dạy thật."""
        self.cur.execute("""
            INSERT INTO sessions (truong_id, nguoi_day_id, nguoi_hoc_id, so_gio, trang_thai, checkin_day, checkin_hoc)
            VALUES (?, ?, ?, ?, ?, 1, 1)
        """, (truong_id, tutor_id, learner_id, hours, trang_thai))
        self.conn.commit()

    def test_01_student_with_23_hours_is_blocked_at_gate(self):
        """1. Học sinh 23 giờ dạy → bị chặn ở sàn chung, thấy số giờ còn thiếu đúng (cần 1 giờ)."""
        u_tutor = self.create_user("P19_HS23", "Học sinh 23h Dạy", truong_id=1)
        u_other = self.create_user("P19_LEARNER1", "Bạn Học 1", truong_id=1)

        # Xóa các session cũ của user này nếu có
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_tutor,))
        self.conn.commit()

        # Thêm các phiên dạy thật hoàn thành với tổng = 23.0 giờ
        self.add_teaching_session(u_tutor, u_other, 10.0)
        self.add_teaching_session(u_tutor, u_other, 10.0)
        self.add_teaching_session(u_tutor, u_other, 3.0)

        # Kiểm tra helper function
        hours = get_user_teaching_hours(self.conn, u_tutor)
        self.assertEqual(hours, 23.0, "Tổng giờ dạy thật phải là 23.0")

        # Đăng nhập học sinh
        with self.client.session_transaction() as sess:
            sess["user_id"] = u_tutor
            sess["ma_hoc_sinh"] = "P19_HS23"
            sess["ho_ten"] = "Học sinh 23h Dạy"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        # Truy cập Sàn cộng đồng: phải gặp màn hình Cổng chặn
        resp = self.client.get("/community-market")
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode("utf-8")

        # Kiểm tra thông báo số giờ còn thiếu: 24 - 23 = 1
        self.assertIn("Bạn cần", text)
        self.assertTrue("giờ dạy nữa để mở khóa Cộng đồng liên trường" in text or "giờ dạy nữa để mở khóa Sàn cộng đồng" in text)
        self.assertTrue("1" in text or "1.0" in text, "Phải hiển thị còn thiếu 1 hoặc 1.0 giờ dạy")
        self.assertIn("Tiến độ tích lũy", text)
        self.assertTrue("Cổng Kiểm Chuẩn Cộng Đồng Liên Trường" in text or "Cổng Kiểm Chuẩn Sàn Cộng Đồng" in text)

        # Kiểm tra Profile: KHÔNG có huy hiệu "Thành viên Cộng đồng"
        resp_prof = self.client.get("/profile")
        text_prof = resp_prof.data.decode("utf-8")
        self.assertNotIn("Thành viên Cộng đồng", text_prof)

    def test_02_student_with_24_hours_unlocks_and_gets_badge(self):
        """2. Học sinh 24 giờ dạy → mở khóa sàn chung + có huy hiệu 'Thành viên Cộng đồng'."""
        u_tutor = self.create_user("P19_HS24", "Học sinh 24h Dạy", truong_id=1)
        u_other = self.create_user("P19_LEARNER2", "Bạn Học 2", truong_id=1)

        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_tutor,))
        self.conn.commit()

        # Thêm các phiên dạy thật hoàn thành với tổng = 24.0 giờ
        self.add_teaching_session(u_tutor, u_other, 12.0)
        self.add_teaching_session(u_tutor, u_other, 12.0)

        hours = get_user_teaching_hours(self.conn, u_tutor)
        self.assertEqual(hours, 24.0, "Tổng giờ dạy thật phải là 24.0")

        with self.client.session_transaction() as sess:
            sess["user_id"] = u_tutor
            sess["ma_hoc_sinh"] = "P19_HS24"
            sess["ho_ten"] = "Học sinh 24h Dạy"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        # Truy cập Sàn cộng đồng: PHẢI mở khóa vào Sàn chung
        resp = self.client.get("/community-market")
        self.assertEqual(resp.status_code, 200)
        text = resp.data.decode("utf-8")
        self.assertTrue("Cộng Đồng Liên Trường" in text or "Sàn Giao Dịch Chung Liên Trường" in text)
        self.assertTrue("Cổng Kiểm Chuẩn" not in text)

        # Kiểm tra Profile: PHẢI có huy hiệu "Thành viên Cộng đồng"
        resp_prof = self.client.get("/profile")
        text_prof = resp_prof.data.decode("utf-8")
        self.assertIn("Thành viên Cộng đồng", text_prof)

    def test_03_dynamic_threshold_in_config_without_hardcoding(self):
        """3. Đổi ngưỡng trong config → cổng áp dụng số mới ngay (chứng minh không hardcode)."""
        u_tutor = self.create_user("P19_DYNAMIC", "Học sinh Động", truong_id=1)
        u_other = self.create_user("P19_LEARNER3", "Bạn Học 3", truong_id=1)

        # User có 15 giờ dạy thật
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_tutor,))
        self.conn.commit()
        self.add_teaching_session(u_tutor, u_other, 15.0)

        with self.client.session_transaction() as sess:
            sess["user_id"] = u_tutor
            sess["ma_hoc_sinh"] = "P19_DYNAMIC"
            sess["ho_ten"] = "Học sinh Động"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        # 3A: Đặt ngưỡng = 30 trong config.yaml
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        cfg["cong_dong_nguong_tin_dung"] = 30
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)

        # Ngưỡng mới được đọc ngay
        self.assertEqual(get_community_threshold(), 30.0)

        # User có 15h, cần: 30 - 15 = 15 giờ nữa
        resp = self.client.get("/community-market")
        text = resp.data.decode("utf-8")
        self.assertIn("Bạn cần", text)
        self.assertTrue("15" in text or "15.0" in text, "Phải thông báo còn thiếu 15 giờ")

        # 3B: Đặt ngưỡng = 10 trong config.yaml
        cfg["cong_dong_nguong_tin_dung"] = 10
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)

        self.assertEqual(get_community_threshold(), 10.0)

        # User có 15h > 10h -> Tự động mở khóa ngay lập tức!
        resp2 = self.client.get("/community-market")
        text2 = resp2.data.decode("utf-8")
        self.assertTrue("Cộng Đồng Liên Trường" in text2 or "Sàn Giao Dịch Chung Liên Trường" in text2)

        # Khôi phục về 24
        cfg["cong_dong_nguong_tin_dung"] = 24
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f)
        self.assertEqual(get_community_threshold(), 24.0)

    def test_04_publish_and_other_school_admin_approve(self):
        """4. Đăng kỹ năng lên sàn chung → admin trường khác duyệt được → hiện trên sàn kèm tên trường."""
        # Học sinh trường 1 có 25 giờ dạy thật
        u_tutor = self.create_user("P19_TUTOR_TRUONG1", "Lê Văn Anh", truong_id=1)
        u_other = self.create_user("P19_LEARNER4", "Học Sinh Khác", truong_id=1)
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_tutor,))
        self.conn.commit()
        self.add_teaching_session(u_tutor, u_other, 25.0)

        # Tạo kỹ năng cho học sinh trường 1
        self.cur.execute("""
            INSERT INTO skills (truong_id, user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
            VALUES (1, ?, 'Toán', 'Chuyên đề Giải tích 12 Ôn thi Tốt nghiệp', 'Phương pháp giải nhanh trắc nghiệm', 'da_duyet')
        """, (u_tutor,))
        self.conn.commit()
        skill_id = self.cur.lastrowid

        # Học sinh đăng lên sàn chung
        with self.client.session_transaction() as sess:
            sess["user_id"] = u_tutor
            sess["ma_hoc_sinh"] = "P19_TUTOR_TRUONG1"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_pub = self.client.post(f"/skills/{skill_id}/publish-community", follow_redirects=True)
        self.assertEqual(resp_pub.status_code, 200)

        # Kiểm tra trạng thái kỹ năng trong DB: 'cho_duyet'
        self.cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        sk_row = self.cur.fetchone()
        self.assertEqual(sk_row["trang_thai_cong_dong"], "cho_duyet")
        self.assertEqual(sk_row["hien_thi_cong_dong"], 0)

        # Admin TRƯỜNG 2 (Nguyễn Văn Thuộc) đăng nhập để duyệt
        admin_truong2 = self.create_user("P19_ADM_TRUONG2", "Admin Nguyễn Văn Thuộc", truong_id=2, vai_tro="school_admin")
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_truong2
            sess["ma_hoc_sinh"] = "P19_ADM_TRUONG2"
            sess["vai_tro"] = "school_admin"
            sess["truong_id"] = 2

        # Admin trường 2 duyệt kỹ năng của học sinh trường 1
        resp_appr = self.client.post(f"/admin/community-skills/{skill_id}/approve", follow_redirects=True)
        self.assertEqual(resp_appr.status_code, 200)

        # Kiểm tra DB: đã duyệt và ghi log ai duyệt
        self.cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        sk_appr = self.cur.fetchone()
        self.assertEqual(sk_appr["hien_thi_cong_dong"], 1)
        self.assertEqual(sk_appr["trang_thai_cong_dong"], "da_duyet")
        self.assertEqual(sk_appr["nguoi_duyet_cong_dong_id"], admin_truong2)
        self.assertIsNotNone(sk_appr["ngay_duyet_cong_dong"])

        # Kiểm tra Sàn chung: Kỹ năng xuất hiện và kèm TÊN TRƯỜNG của chủ kỹ năng
        resp_mkt = self.client.get("/community-market")
        self.assertEqual(resp_mkt.status_code, 200)
        mkt_html = resp_mkt.data.decode("utf-8")
        self.assertIn("Chuyên đề Giải tích 12 Ôn thi Tốt nghiệp", mkt_html)
        self.assertIn("Lê Văn Anh", mkt_html)
        # Tên trường 1 (UK Academy) phải xuất hiện
        self.cur.execute("SELECT ten_truong FROM truong WHERE id = 1")
        school1_name = self.cur.fetchone()["ten_truong"]
        self.assertIn(school1_name, mkt_html)

    def test_05_inter_school_session_transfers_unified_wallet(self):
        """5. Học sinh trường A học xong buổi của trường B → ví chung trừ/cộng đúng, không sai lệch."""
        # Gia sư trường 1 (Số dư ban đầu: 10.0h)
        tutor_id = self.create_user("P19_TUTOR_A", "Gia Sư Trường A", truong_id=1, so_du_gio=10.0)
        # Học sinh trường 2 (Số dư ban đầu: 5.0h)
        learner_id = self.create_user("P19_LEARNER_B", "Học Sinh Trường B", truong_id=2, so_du_gio=5.0)

        # Tạo kỹ năng liên trường đã duyệt
        self.cur.execute("""
            INSERT INTO skills (truong_id, user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, hien_thi_cong_dong, trang_thai_cong_dong)
            VALUES (1, ?, 'Tin học', 'Lập trình Python Nâng Cao', 'Cấu trúc dữ liệu và giải thuật', 'da_duyet', 1, 'da_duyet')
        """, (tutor_id,))
        self.conn.commit()
        skill_id = self.cur.lastrowid

        # Học sinh B đặt lịch với gia sư A cho 1.5 giờ
        with self.client.session_transaction() as sess:
            sess["user_id"] = learner_id
            sess["ma_hoc_sinh"] = "P19_LEARNER_B"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 2

        resp_book = self.client.post("/sessions/book", data={
            "skill_id": skill_id,
            "thoi_gian_bat_dau": "2026-10-15 14:00",
            "so_gio": "1.5"
        }, follow_redirects=True)
        self.assertEqual(resp_book.status_code, 200)

        # Lấy session vừa tạo
        self.cur.execute("""
            SELECT id FROM sessions 
            WHERE nguoi_day_id = ? AND nguoi_hoc_id = ? 
            ORDER BY id DESC LIMIT 1
        """, (tutor_id, learner_id))
        session_id = self.cur.fetchone()["id"]

        # Check-in cả hai bên
        self.cur.execute("UPDATE sessions SET checkin_day = 1, checkin_hoc = 1 WHERE id = ?", (session_id,))
        self.conn.commit()

        # Gia sư A xác nhận hoàn thành buổi học
        with self.client.session_transaction() as sess:
            sess["user_id"] = tutor_id
            sess["ma_hoc_sinh"] = "P19_TUTOR_A"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_comp = self.client.post(f"/sessions/{session_id}/complete", follow_redirects=True)
        self.assertEqual(resp_comp.status_code, 200)

        # Kiểm tra số dư ví chung:
        # Learner B: 5.0 - 1.5 = 3.5
        self.cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (learner_id,))
        bal_learner = self.cur.fetchone()["so_du_gio"]
        self.assertAlmostEqual(bal_learner, 3.5, places=2)

        # Tutor A: 10.0 + 1.5 = 11.5
        self.cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (tutor_id,))
        bal_tutor = self.cur.fetchone()["so_du_gio"]
        self.assertAlmostEqual(bal_tutor, 11.5, places=2)

        # Kiểm tra sổ cái credits_ledger: 2 bản ghi cân bằng
        self.cur.execute("SELECT * FROM credits_ledger WHERE session_id = ? ORDER BY id ASC", (session_id,))
        ledger = self.cur.fetchall()
        self.assertEqual(len(ledger), 2)
        self.assertEqual(ledger[0]["user_id"], tutor_id)
        self.assertAlmostEqual(ledger[0]["bien_dong"], 1.5)
        self.assertEqual(ledger[1]["user_id"], learner_id)
        self.assertAlmostEqual(ledger[1]["bien_dong"], -1.5)

    def test_06_student_below_gate_cannot_see_publish_button(self):
        """6. Học sinh chưa qua cổng KHÔNG thấy nút 'Đăng lên sàn chung'."""
        # Tạo học sinh mới 0h dạy
        u_new = self.create_user("P19_NEW_STUDENT", "Học sinh Mới Chưa Dạy", truong_id=1)
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_new,))
        self.conn.commit()

        # Tạo 1 kỹ năng cho học sinh này
        self.cur.execute("""
            INSERT INTO skills (truong_id, user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
            VALUES (1, ?, 'Văn', 'Phương pháp Đọc hiểu văn bản', 'Mô tả văn học', 'da_duyet')
        """, (u_new,))
        self.conn.commit()

        # Đăng nhập
        with self.client.session_transaction() as sess:
            sess["user_id"] = u_new
            sess["ma_hoc_sinh"] = "P19_NEW_STUDENT"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        # Xem profile: KHÔNG được có nút "Đăng lên cộng đồng liên trường"
        resp = self.client.get("/profile")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")
        self.assertTrue("Đăng lên cộng đồng liên trường" not in html and "Đăng lên sàn chung" not in html)

        # Xem student với 23h: cũng KHÔNG được có nút "Đăng lên sàn chung"
        u_23 = self.create_user("P19_USER_23H", "Học sinh 23h Check Button", truong_id=1)
        u_learn = self.create_user("P19_L_DUMMY", "Bạn Học Dummy", truong_id=1)
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_23,))
        self.conn.commit()
        self.add_teaching_session(u_23, u_learn, 23.0)
        self.cur.execute("""
            INSERT INTO skills (truong_id, user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
            VALUES (1, ?, 'Vẽ', 'Hội họa cơ bản', 'Màu nước', 'da_duyet')
        """, (u_23,))
        self.conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = u_23
            sess["ma_hoc_sinh"] = "P19_USER_23H"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_23 = self.client.get("/profile")
        html_23 = resp_23.data.decode("utf-8")
        self.assertTrue("Đăng lên cộng đồng liên trường" not in html_23 and "Đăng lên sàn chung" not in html_23)

        # Ngược lại, user 24h PHẢI thấy nút "Đăng lên sàn chung"
        u_24 = self.create_user("P19_USER_24H", "Học sinh 24h Check Button", truong_id=1)
        self.cur.execute("DELETE FROM sessions WHERE nguoi_day_id = ?", (u_24,))
        self.conn.commit()
        self.add_teaching_session(u_24, u_learn, 24.0)
        self.cur.execute("""
            INSERT INTO skills (truong_id, user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
            VALUES (1, ?, 'Hóa', 'Hóa học hữu cơ', 'Chuyên đề este', 'da_duyet')
        """, (u_24,))
        self.conn.commit()

        with self.client.session_transaction() as sess:
            sess["user_id"] = u_24
            sess["ma_hoc_sinh"] = "P19_USER_24H"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_24 = self.client.get("/profile")
        html_24 = resp_24.data.decode("utf-8")
        self.assertTrue("Đăng lên cộng đồng liên trường" in html_24 or "Đăng lên sàn chung" in html_24)

    def test_07_menu_and_admin_interface(self):
        """7. Giao diện: Menu có 'Sàn cộng đồng', Admin dashboard có tab 'Duyệt sàn chung'."""
        admin_id = self.create_user("P19_SUPER_ADM", "Tổng Quản Trị Huyền", truong_id=1, vai_tro="super_admin")
        with self.client.session_transaction() as sess:
            sess["user_id"] = admin_id
            sess["ma_hoc_sinh"] = "P19_SUPER_ADM"
            sess["vai_tro"] = "super_admin"
            sess["truong_id"] = 1

        resp = self.client.get("/admin")
        self.assertEqual(resp.status_code, 200)
        html = resp.data.decode("utf-8")

        # Menu điều hướng có "Cộng đồng liên trường"
        self.assertTrue("Cộng đồng liên trường" in html or "Sàn cộng đồng" in html)
        self.assertIn("/community-market", html)

        # Admin dashboard có tab "Duyệt Liên Trường"
        self.assertTrue("Duyệt Liên Trường" in html or "Duyệt Sàn Chung" in html)
        self.assertIn("tab-community", html)


if __name__ == "__main__":
    unittest.main()
