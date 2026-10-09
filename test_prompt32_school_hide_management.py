# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — PROMPT 32: QUẢN LÝ TRƯỜNG HỌC (THÊM / SỬA / ẨN TRƯỜNG)

Nghiệm thu toàn bộ tiêu chí PROMPT 32:
1. Thêm trường mới -> hiện trong dropdown lọc ở /admin, tạo mã mời được, học sinh đăng ký vào đúng trường mới.
2. Ẩn 1 trường -> an_truong=1, biến mất khỏi trang chủ/đăng ký/dropdown người dùng; super admin vẫn thấy có nhãn "Đã ẩn".
3. Hiện lại -> an_truong=0, xuất hiện bình thường trở lại.
4. Trường Demo (ID 99) ẩn mặc định (an_truong=1); 3 tài khoản demo đăng nhập bình thường; không cho sửa/xóa/ẩn.
5. Không còn chữ "Gian hàng #N" hay "Gian hàng" ở giao diện người dùng (thay bằng "Trường #N").
6. Bảng liệt kê: tên trường, logo, trạng thái, số tài khoản, ngày tạo, nút "Sửa" và nút "Ẩn trường"/"Hiện lại" cạnh nhau. KHÔNG có nút xóa cứng.
7. Regression pass 100%.
"""

import sys
import unittest
import time
from werkzeug.security import generate_password_hash

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db, DEMO_SCHOOL_ID


class TestPrompt32SchoolHideManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        # Tạo hoặc lấy tài khoản super_admin
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE vai_tro = 'super_admin' LIMIT 1")
        row = cur.fetchone()
        if row:
            self.super_admin_id = row[0]
        else:
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, email, truong_id, trang_thai)
                VALUES ('SUPER_TEST_P32', 'Super Admin P32', 'super_admin', 999.0, ?, 'super_p32@timebankedu.vn', 1, 'hoat_dong')
            """, (generate_password_hash("Admin@123"),))
            db.commit()
            self.super_admin_id = cur.lastrowid

        # Tạo tài khoản học sinh phục vụ kiểm thử
        cur.execute("SELECT id FROM users WHERE vai_tro = 'hoc_sinh' AND ma_hoc_sinh = 'HS_TEST_P32'")
        hs_row = cur.fetchone()
        if hs_row:
            self.student_id = hs_row[0]
        else:
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, truong_id, trang_thai)
                VALUES ('HS_TEST_P32', 'Học Sinh Test P32', 'hoc_sinh', 5.0, ?, 1, 'hoat_dong')
            """, (generate_password_hash("Pass@123"),))
            db.commit()
            self.student_id = cur.lastrowid

    def tearDown(self):
        self.app_context.pop()

    def login_super_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.super_admin_id
            sess["vai_tro"] = "super_admin"
            sess["ho_ten"] = "Super Admin P32"
            sess["truong_id"] = 1

    def login_student(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["vai_tro"] = "hoc_sinh"
            sess["ho_ten"] = "Học Sinh Test P32"
            sess["truong_id"] = 1

    def logout(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_01_migration_and_demo_school_defaults(self):
        """[TC 1]: Cột an_truong tồn tại; Trường Demo (ID 99) có an_truong=1 mặc định; các trường chính an_truong=0."""
        db = get_db()
        cur = db.cursor()
        cur.execute("PRAGMA table_info(truong)")
        cols = [r[1] for r in cur.fetchall()]
        self.assertIn("an_truong", cols, "Bảng truong phải có cột an_truong")

        # Kiểm tra Trường Demo (ID 99)
        cur.execute("SELECT id, ten_truong, COALESCE(an_truong, 0) AS an_truong FROM truong WHERE id = ?", (DEMO_SCHOOL_ID,))
        demo = cur.fetchone()
        self.assertIsNotNone(demo, "Trường Demo ID 99 phải tồn tại")
        self.assertEqual(demo["an_truong"], 1, "Trường Demo ID 99 phải có an_truong = 1 (ẩn mặc định)")

        # Kiểm tra trường 1 không bị ẩn mặc định
        cur.execute("SELECT id, ten_truong, COALESCE(an_truong, 0) AS an_truong FROM truong WHERE id = 1")
        school1 = cur.fetchone()
        if school1:
            self.assertEqual(school1["an_truong"], 0, "Trường #1 mặc định không được ẩn")

    def test_02_super_admin_tab_ui_and_no_hard_delete(self):
        """[TC 2]: UI /admin tab Trường học: Form thêm trường đủ 4 trạng thái, nút Sửa & Ẩn/Hiện cạnh nhau, KHÔNG có nút xóa cứng."""
        self.login_super_admin()
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Kiểm tra tab và form
        self.assertIn("id=\"tab-schools\"", html)
        self.assertIn("Thêm Trường Học Mới Vào Hệ Thống", html)
        self.assertIn("Chuẩn bị triển khai", html)
        self.assertIn("Đang thí điểm", html)
        self.assertIn("Đang hoạt động", html)
        self.assertIn("Tạm ngưng", html)

        # Kiểm tra danh sách trường
        self.assertIn("Trường #99", html, "Cột mã phải có tiền tố Trường #ID")
        self.assertIn("Cố định (Không sửa/xóa)", html, "Trường demo phải được bảo vệ cố định")
        self.assertIn("Đã ẩn", html, "Trường demo và trường ẩn phải có badge Đã ẩn")

        # Kiểm tra nút Sửa và nút Ẩn/Hiện
        self.assertTrue("Sửa" in html and "editSchoolModal" in html, "Phải có nút Sửa và modal sửa trường")
        self.assertTrue("Ẩn trường" in html or "Hiện lại" in html, "Phải có nút Ẩn trường hoặc Hiện lại")

        # KHÔNG có nút xóa cứng trường học
        self.assertNotIn("Xóa trường", html)
        self.assertNotIn("/admin/schools/delete", html)

    def test_03_create_new_school_and_isolation(self):
        """[TC 3]: Thêm trường mới thành công -> hiện trong dropdown lọc /admin, sinh mã mời được, học sinh đăng ký đúng trường."""
        self.login_super_admin()
        school_name = f"THPT Thực Nghiệm P32_{int(time.time())}"

        # 1. Thêm trường mới
        res = self.client.post("/admin/schools/create", data={
            "ten_truong": school_name,
            "trang_thai": "dang_hoat_dong"
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Đã thêm trường học mới", html)
        self.assertIn(school_name, html)

        # Kiểm tra CSDL
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, ten_truong, trang_thai, an_truong FROM truong WHERE ten_truong = ?", (school_name,))
        new_school = cur.fetchone()
        self.assertIsNotNone(new_school)
        self.assertNotEqual(new_school["id"], DEMO_SCHOOL_ID)
        self.assertEqual(new_school["an_truong"], 0, "Trường mới thêm phải có an_truong = 0 (chưa ẩn)")
        new_id = new_school["id"]

        # Hiện trong dropdown lọc trường của /admin
        self.assertIn(f">{school_name}", html)

        # 2. Sinh mã mời cho trường mới
        invite_code = f"INV-P32-{int(time.time())}"
        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (?, ?, 'ca_nhan', 1, 0, '2026-10-09 12:00:00', 'super_admin')
        """, (new_id, invite_code))
        db.commit()

        # 3. Học sinh đăng ký bằng mã mời này
        self.logout()
        student_code = f"HS_NEW_{int(time.time())}"
        res_reg = self.client.post("/register", data={
            "ma_hoc_sinh": student_code,
            "ho_ten": "Học Sinh Trường Mới P32",
            "mat_khau": "Password@123",
            "mat_khau_xac_nhan": "Password@123",
            "ma_code": invite_code
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)

        # Kiểm tra học sinh được liên kết đúng truong_id mới
        cur.execute("SELECT truong_id FROM users WHERE ma_hoc_sinh = ?", (student_code,))
        u_row = cur.fetchone()
        self.assertIsNotNone(u_row)
        self.assertEqual(u_row["truong_id"], new_id, "Học sinh đăng ký phải gắn đúng vào trường mới")

    def test_04_hide_school_and_hiding_effects(self):
        """[TC 4]: Bấm 'Ẩn trường' -> an_truong=1, biến mất khỏi trang chủ/đăng ký/dropdown; super admin vẫn thấy có nhãn 'Đã ẩn'."""
        self.login_super_admin()
        school_name = f"Trường Sẽ Bị Ẩn P32_{int(time.time())}"
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO truong (ten_truong, logo, trang_thai, an_truong, ngay_tao)
            VALUES (?, '/static/img/logo_timebank_edu.png', 'dang_su_dung', 0, '2026-10-09 12:00:00')
        """, (school_name,))
        db.commit()
        school_id = cur.lastrowid

        # 1. Trước khi ẩn: hiển thị ở trang chủ và trang đăng ký
        self.logout()
        res_home = self.client.get("/")
        self.assertIn(school_name, res_home.data.decode("utf-8"))
        res_reg = self.client.get("/register")
        self.assertIn(school_name, res_reg.data.decode("utf-8"))

        # 2. Super admin thực hiện Ẩn trường
        self.login_super_admin()
        res_hide = self.client.post(f"/admin/schools/{school_id}/toggle-hide", follow_redirects=True)
        self.assertEqual(res_hide.status_code, 200)
        self.assertIn("Đã ẩn trường", res_hide.data.decode("utf-8"))

        # CSDL: an_truong = 1
        cur.execute("SELECT an_truong FROM truong WHERE id = ?", (school_id,))
        self.assertEqual(cur.fetchone()[0], 1)

        # 3. Sau khi ẩn: biến mất khỏi trang chủ và trang đăng ký
        self.logout()
        res_home2 = self.client.get("/")
        self.assertNotIn(school_name, res_home2.data.decode("utf-8"), "Trường đã ẩn không được xuất hiện trên trang chủ")
        res_reg2 = self.client.get("/register")
        self.assertNotIn(f">{school_name}</option>", res_reg2.data.decode("utf-8"), "Trường đã ẩn không được xuất hiện trong dropdown đăng ký")

        # 4. Super admin vẫn thấy trong /admin và có nhãn "Đã ẩn"
        self.login_super_admin()
        res_admin = self.client.get("/admin")
        admin_html = res_admin.data.decode("utf-8")
        self.assertIn(school_name, admin_html)
        self.assertIn(f"{school_name} (Đã ẩn)", admin_html, "Dropdown lọc của super admin phải có nhãn (Đã ẩn)")

    def test_05_unhide_school_success(self):
        """[TC 5]: Bấm 'Hiện lại' -> an_truong=0, xuất hiện bình thường trở lại trên hệ thống."""
        self.login_super_admin()
        school_name = f"Trường Khôi Phục P32_{int(time.time())}"
        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO truong (ten_truong, logo, trang_thai, an_truong, ngay_tao)
            VALUES (?, '/static/img/logo_timebank_edu.png', 'vo_hieu_hoa', 1, '2026-10-09 12:00:00')
        """, (school_name,))
        db.commit()
        school_id = cur.lastrowid

        # Hiện lại trường
        res_unhide = self.client.post(f"/admin/schools/{school_id}/toggle-hide", follow_redirects=True)
        self.assertEqual(res_unhide.status_code, 200)
        self.assertIn("Đã hiện lại trường", res_unhide.data.decode("utf-8"))

        # CSDL: an_truong = 0
        cur.execute("SELECT an_truong, trang_thai FROM truong WHERE id = ?", (school_id,))
        row = cur.fetchone()
        self.assertEqual(row["an_truong"], 0)
        self.assertNotEqual(row["trang_thai"], "vo_hieu_hoa")

        # Xuất hiện lại trên trang chủ
        self.logout()
        res_home = self.client.get("/")
        self.assertIn(school_name, res_home.data.decode("utf-8"), "Trường sau khi hiện lại phải xuất hiện trên trang chủ")

    def test_06_demo_school_99_protected_and_login_works(self):
        """[TC 6]: Trường Demo (ID 99) ẩn mặc định; chặn sửa/xóa/ẩn; 3 tài khoản demo đăng nhập bình thường."""
        self.login_super_admin()

        # 1. Chặn sửa
        res_edit = self.client.post(f"/admin/schools/{DEMO_SCHOOL_ID}/edit", data={
            "ten_truong": "Tên Đổi Demo",
            "trang_thai": "dang_su_dung"
        }, follow_redirects=True)
        self.assertIn("không được phép chỉnh sửa", res_edit.data.decode("utf-8"))

        # 2. Chặn ẩn/vô hiệu hóa
        res_toggle = self.client.post(f"/admin/schools/{DEMO_SCHOOL_ID}/toggle-hide", follow_redirects=True)
        self.assertIn("không được phép", res_toggle.data.decode("utf-8"))

        # 3. 3 tài khoản demo đăng nhập bình thường
        self.logout()
        demo_accounts = [
            ("demo_quantruong", "demo123", "school_admin"),
            ("demo_giaovien", "demo123", "giao_vien"),
            ("demo_hocsinh", "demo123", "hoc_sinh"),
        ]
        for uname, pwd, expected_role in demo_accounts:
            res_login = self.client.post("/login", data={
                "ma_hoc_sinh": uname,
                "mat_khau": pwd
            }, follow_redirects=False)
            self.assertEqual(res_login.status_code, 302, f"Tài khoản demo {uname} phải đăng nhập thành công (redirect)")

    def test_07_no_gian_hang_in_user_facing_ui(self):
        """[TC 7]: Không còn chữ 'Gian hàng #N' hay 'Gian hàng' ở giao diện người dùng (chỉ còn Trường #N)."""
        # Kiểm tra trang chủ
        res_home = self.client.get("/")
        home_html = res_home.data.decode("utf-8")
        self.assertNotIn("Gian hàng #", home_html)
        self.assertNotIn("Gian Hàng #", home_html)
        self.assertNotIn("gian hàng #", home_html)

        # Kiểm tra trang quản trị /admin
        self.login_super_admin()
        res_admin = self.client.get("/admin")
        admin_html = res_admin.data.decode("utf-8")
        self.assertNotIn("Gian hàng #", admin_html)
        self.assertNotIn("Gian Hàng #", admin_html)
        self.assertNotIn("gian hàng #", admin_html)
        self.assertIn("Trường #", admin_html, "Giao diện quản trị phải hiển thị Trường #N")


if __name__ == "__main__":
    unittest.main()
