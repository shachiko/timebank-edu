# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — PROMPT 30: QUẢN LÝ TRƯỜNG HỌC (THÊM / SỬA / VÔ HIỆU HÓA TRƯỜNG MỚI)

Nghiệm thu các tiêu chí:
1. Thêm tab "Quản lý Trường học" trong /admin (chỉ super_admin thấy):
   - Bảng liệt kê: tên trường, logo, trạng thái, số tài khoản, ngày tạo.
   - Form thêm trường mới: tên trường (*), logo, trạng thái.
   - Nút sửa tên/logo/trạng thái, nút vô hiệu hóa (không xóa cứng).
2. Khi thêm trường mới:
   - Tự sinh truong_id tiếp theo (tránh trùng DEMO_SCHOOL_ID = 99).
   - Trường mới hiện trong dropdown lọc trường ở /admin.
   - Có thể tạo mã mời riêng, học sinh đăng ký đúng vào trường mới (cách ly dữ liệu).
3. Validate: Tên trường không trùng (case-insensitive), không để trống.
4. Vô hiệu hóa trường:
   - Trường bị ẩn khỏi dropdown đăng ký (/register).
   - Từ chối đăng ký mã mời của trường bị vô hiệu hóa.
   - Kích hoạt lại: trường xuất hiện trở lại trên /register.
5. Trường Demo (ID 99):
   - Không cho phép sửa tên, trạng thái, logo hoặc vô hiệu hóa.
"""

import sys
import unittest
from werkzeug.security import generate_password_hash

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db, DEMO_SCHOOL_ID


class TestPrompt30SchoolManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        # Tạo hoặc lấy tài khoản super_admin phục vụ kiểm thử
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE vai_tro = 'super_admin' LIMIT 1")
        row = cur.fetchone()
        if row:
            self.super_admin_id = row[0]
        else:
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, email, truong_id, trang_thai)
                VALUES ('SUPER_TEST', 'Super Admin Test', 'super_admin', 999.0, ?, 'super_test@timebankedu.vn', 1, 'hoat_dong')
            """, (generate_password_hash("Admin@123"),))
            db.commit()
            self.super_admin_id = cur.lastrowid

        # Tạo tài khoản học sinh thông thường phục vụ test phân quyền
        cur.execute("SELECT id FROM users WHERE vai_tro = 'hoc_sinh' AND ma_hoc_sinh = 'HS_TEST_P30'")
        hs_row = cur.fetchone()
        if hs_row:
            self.student_id = hs_row[0]
        else:
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, truong_id, trang_thai)
                VALUES ('HS_TEST_P30', 'Học Sinh Test P30', 'hoc_sinh', 5.0, ?, 1, 'hoat_dong')
            """, (generate_password_hash("Pass@123"),))
            db.commit()
            self.student_id = cur.lastrowid

        # Dọn dẹp trường rác nếu có
        cur.execute("DELETE FROM truong WHERE ten_truong = 'uk academy quốc tế hạ long'")
        db.commit()

    def tearDown(self):
        self.app_context.pop()

    def login_super_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.super_admin_id
            sess["vai_tro"] = "super_admin"
            sess["ho_ten"] = "Super Admin Test"
            sess["truong_id"] = 1

    def login_student(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.student_id
            sess["vai_tro"] = "hoc_sinh"
            sess["ho_ten"] = "Học Sinh Test P30"
            sess["truong_id"] = 1

    def logout(self):
        with self.client.session_transaction() as sess:
            sess.clear()

    def test_01_super_admin_tab_schools_rendered(self):
        """[TC 1]: Super admin thấy tab Quản lý Trường học, nút tab, form thêm trường và danh sách trường."""
        self.login_super_admin()
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn("tab-schools-btn", html, "Nút tab Quản lý Trường học phải có trong thanh điều hướng")
        self.assertIn("id=\"tab-schools\"", html, "Tab-pane #tab-schools phải tồn tại")
        self.assertIn("Thêm Trường Học Mới Vào Hệ Thống", html, "Phải có tiêu đề Form thêm trường học mới")
        self.assertIn("/admin/schools/create", html, "Phải có action thêm trường học mới")
        self.assertIn("Danh Sách Trường Học Đang Quản Trị", html, "Phải có bảng danh sách trường học")
        self.assertIn("Cố định (Không sửa/xóa)", html, "Trường Demo 99 phải có badge cố định bảo vệ")

    def test_02_create_school_success_and_auto_id(self):
        """[TC 2]: Thêm trường mới thành công, tự sinh truong_id tiếp theo, hiện trong filter dropdown."""
        self.login_super_admin()
        school_name = "THPT Chuyên Hạ Long Test P30"

        # Dọn dẹp nếu đã tồn tại trước đó
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM truong WHERE ten_truong = ?", (school_name,))
        prev_s = cur.fetchone()
        if prev_s:
            s_id = prev_s[0]
            cur.execute("DELETE FROM invite_code_usages WHERE user_id IN (SELECT id FROM users WHERE truong_id = ?)", (s_id,))
            cur.execute("DELETE FROM invite_code_usages WHERE invite_code_id IN (SELECT id FROM invite_codes WHERE truong_id = ?)", (s_id,))
            cur.execute("DELETE FROM invite_codes WHERE truong_id = ?", (s_id,))
            cur.execute("DELETE FROM credits_ledger WHERE user_id IN (SELECT id FROM users WHERE truong_id = ?)", (s_id,))
            cur.execute("DELETE FROM users WHERE truong_id = ?", (s_id,))
            cur.execute("DELETE FROM truong WHERE id = ?", (s_id,))
            db.commit()

        res = self.client.post("/admin/schools/create", data={
            "ten_truong": school_name,
            "trang_thai": "dang_thi_diem"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Đã thêm trường học mới", html)
        self.assertIn(school_name, html)

        # Kiểm tra CSDL
        cur.execute("SELECT id, ten_truong, trang_thai FROM truong WHERE ten_truong = ?", (school_name,))
        row = cur.fetchone()
        self.assertIsNotNone(row, "Trường mới phải được lưu vào CSDL")
        self.assertNotEqual(row["id"], DEMO_SCHOOL_ID, "Mã trường tự sinh không được trùng ID 99 của Trường Demo")
        self.assertEqual(row["trang_thai"], "dang_thi_diem")

        # Kiểm tra xuất hiện trong dropdown lọc trường ở /admin
        self.assertIn(f">{school_name}", html, "Trường mới phải xuất hiện trong dropdown lọc trường của /admin")

    def test_03_create_school_validation(self):
        """[TC 3]: Validate tên trường: không để trống, không trùng lặp (case-insensitive)."""
        self.login_super_admin()

        # 1. Tên trường để trống
        res_empty = self.client.post("/admin/schools/create", data={
            "ten_truong": "   ",
            "trang_thai": "dang_thi_diem"
        }, follow_redirects=True)
        self.assertIn("Tên trường học không được để trống", res_empty.data.decode("utf-8"))

        # 2. Tên trường trùng lặp (không phân biệt hoa thường)
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT ten_truong FROM truong LIMIT 1")
        existing_name = cur.fetchone()[0]
        res_dup = self.client.post("/admin/schools/create", data={
            "ten_truong": existing_name.lower(),
            "trang_thai": "dang_thi_diem"
        }, follow_redirects=True)
        self.assertIn("đã tồn tại trong hệ thống", res_dup.data.decode("utf-8"))

    def test_04_edit_school_success_and_validation(self):
        """[TC 4]: Sửa tên và trạng thái trường học thành công; chặn sửa tên trùng hoặc rỗng."""
        self.login_super_admin()

        # Dọn dẹp các bản ghi thử nghiệm trước đó
        test_name = "Trường Thực Nghiệm Sửa P30"
        new_name = "Trường Thực Nghiệm Đã Đổi Tên P30"
        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM truong WHERE ten_truong IN (?, ?)", (test_name, new_name))
        db.commit()

        # Tạo trường thử nghiệm
        cur.execute("""
            INSERT INTO truong (ten_truong, logo, trang_thai, ngay_tao)
            VALUES (?, '/static/img/logo_timebank_edu.png', 'dang_thi_diem', '2026-10-09 12:00:00')
        """, (test_name,))
        db.commit()
        target_id = cur.lastrowid

        # Sửa thành công
        res_edit = self.client.post(f"/admin/schools/{target_id}/edit", data={
            "ten_truong": new_name,
            "trang_thai": "dang_su_dung"
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)
        self.assertIn("Đã cập nhật thông tin trường", res_edit.data.decode("utf-8"))

        cur.execute("SELECT ten_truong, trang_thai FROM truong WHERE id = ?", (target_id,))
        row = cur.fetchone()
        self.assertEqual(row["ten_truong"], new_name)
        self.assertEqual(row["trang_thai"], "dang_su_dung")

        # Chặn sửa tên rỗng
        res_empty = self.client.post(f"/admin/schools/{target_id}/edit", data={
            "ten_truong": "   ",
            "trang_thai": "dang_su_dung"
        }, follow_redirects=True)
        self.assertIn("Tên trường học không được để trống", res_empty.data.decode("utf-8"))

        # Chặn sửa tên trùng với trường khác
        cur.execute("SELECT ten_truong FROM truong WHERE id != ? LIMIT 1", (target_id,))
        other_name = cur.fetchone()[0]
        res_dup = self.client.post(f"/admin/schools/{target_id}/edit", data={
            "ten_truong": other_name.lower(),
            "trang_thai": "dang_su_dung"
        }, follow_redirects=True)
        self.assertIn("trùng với một trường học khác", res_dup.data.decode("utf-8"))

    def test_05_protect_demo_school_99(self):
        """[TC 5]: Trường Demo (ID 99) được bảo vệ: không cho phép sửa thông tin, đổi logo hay vô hiệu hóa."""
        self.login_super_admin()

        # 1. Thử sửa trường Demo
        res_edit = self.client.post(f"/admin/schools/{DEMO_SCHOOL_ID}/edit", data={
            "ten_truong": "Tên Bị Sửa Demo",
            "trang_thai": "vo_hieu_hoa"
        }, follow_redirects=True)
        self.assertIn("Trường Demo (ID 99) là trường mẫu của hệ thống, không được phép chỉnh sửa", res_edit.data.decode("utf-8"))

        # 2. Thử vô hiệu hóa trường Demo
        res_toggle = self.client.post(f"/admin/schools/{DEMO_SCHOOL_ID}/toggle-status", follow_redirects=True)
        self.assertIn("không được phép vô hiệu hóa", res_toggle.data.decode("utf-8"))

        # 3. Thử cập nhật logo trường Demo
        res_logo = self.client.post(f"/admin/schools/{DEMO_SCHOOL_ID}/logo", data={}, follow_redirects=True)
        self.assertIn("không được phép chỉnh sửa logo", res_logo.data.decode("utf-8"))

        # Kiểm tra CSDL trường 99 không hề bị thay đổi
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT ten_truong, trang_thai FROM truong WHERE id = ?", (DEMO_SCHOOL_ID,))
        row = cur.fetchone()
        self.assertIn("Demo", row["ten_truong"])
        self.assertNotEqual(row["trang_thai"], "vo_hieu_hoa")

    def test_06_toggle_school_status_and_registration_hiding(self):
        """[TC 6]: Vô hiệu hóa trường: ẩn khỏi /register, từ chối mã mời; Kích hoạt lại: mở lại bình thường."""
        self.login_super_admin()

        # Tạo trường thử nghiệm
        db = get_db()
        cur = db.cursor()
        toggle_school_name = "Trường Thử Nghiệm Vô Hiệu Hóa P30"
        cur.execute("SELECT id FROM truong WHERE ten_truong = ?", (toggle_school_name,))
        prev_tog = cur.fetchone()
        if prev_tog:
            target_id = prev_tog[0]
            cur.execute("UPDATE truong SET trang_thai = 'dang_su_dung' WHERE id = ?", (target_id,))
            db.commit()
        else:
            cur.execute("""
                INSERT INTO truong (ten_truong, logo, trang_thai, ngay_tao)
                VALUES (?, '/static/img/logo_timebank_edu.png', 'dang_su_dung', '2026-10-09 12:00:00')
            """, (toggle_school_name,))
            db.commit()
            target_id = cur.lastrowid

        # 1. Ban đầu trường đang sử dụng -> hiển thị trên /register (đăng xuất trước khi vào /register)
        self.logout()
        res_reg1 = self.client.get("/register")
        self.assertIn(toggle_school_name, res_reg1.data.decode("utf-8"))

        # 2. Vô hiệu hóa trường (đăng nhập lại super admin để thực hiện)
        self.login_super_admin()
        res_toggle = self.client.post(f"/admin/schools/{target_id}/toggle-status", follow_redirects=True)
        self.assertIn("Đã vô hiệu hóa trường", res_toggle.data.decode("utf-8"))

        # Kiểm tra trạng thái CSDL
        cur.execute("SELECT trang_thai FROM truong WHERE id = ?", (target_id,))
        self.assertEqual(cur.fetchone()[0], "vo_hieu_hoa")

        # 3. Sau khi vô hiệu hóa -> ẨN khỏi dropdown /register (đăng xuất để xem /register)
        self.logout()
        res_reg2 = self.client.get("/register")
        self.assertNotIn(f">{toggle_school_name}</option>", res_reg2.data.decode("utf-8"))

        # 4. Tạo mã mời thử cho trường này và test kiểm tra mã mời
        import time
        disabled_code = f"TBEDU-DIS-{int(time.time() * 1000)}"
        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (?, ?, 'ca_nhan', 1, 0, '2026-10-09 12:00:00', 'test')
        """, (target_id, disabled_code))
        db.commit()

        # API check invite code trả về lỗi trường bị vô hiệu hóa
        res_check = self.client.get(f"/api/check-invite-code?code={disabled_code}")
        check_json = res_check.get_json()
        self.assertFalse(check_json["valid"])
        self.assertIn("vô hiệu hóa", check_json["error"])

        # Đăng ký với mã mời này bị từ chối
        dis_student = f"HS_DIS_{int(time.time() * 1000)}"
        res_reg_post = self.client.post("/register", data={
            "ma_hoc_sinh": dis_student,
            "ho_ten": "Học Sinh Thử Nghiệm",
            "mat_khau": "123456",
            "mat_khau_xac_nhan": "123456",
            "ma_code": disabled_code
        }, follow_redirects=True)
        self.assertIn("vô hiệu hóa", res_reg_post.data.decode("utf-8"))

        # 5. Kích hoạt lại trường
        self.login_super_admin()
        res_reactivate = self.client.post(f"/admin/schools/{target_id}/toggle-status", follow_redirects=True)
        self.assertIn("Đã kích hoạt lại trường", res_reactivate.data.decode("utf-8"))

        cur.execute("SELECT trang_thai FROM truong WHERE id = ?", (target_id,))
        self.assertEqual(cur.fetchone()[0], "dang_su_dung")

        # Trường hiển thị lại trên /register
        self.logout()
        res_reg3 = self.client.get("/register")
        self.assertIn(toggle_school_name, res_reg3.data.decode("utf-8"))

    def test_07_invite_code_and_student_isolation_in_new_school(self):
        """[TC 7]: Sinh mã mời cho trường mới -> học sinh đăng ký đúng trường và cách ly tài khoản."""
        self.login_super_admin()

        db = get_db()
        cur = db.cursor()
        iso_school_name = "Trường Cách Ly Dữ Liệu P30"
        cur.execute("SELECT id FROM truong WHERE ten_truong = ?", (iso_school_name,))
        prev_iso = cur.fetchone()
        if prev_iso:
            new_school_id = prev_iso[0]
            cur.execute("UPDATE truong SET trang_thai = 'dang_su_dung' WHERE id = ?", (new_school_id,))
            db.commit()
        else:
            cur.execute("""
                INSERT INTO truong (ten_truong, logo, trang_thai, ngay_tao)
                VALUES (?, '/static/img/logo_timebank_edu.png', 'dang_su_dung', '2026-10-09 12:00:00')
            """, (iso_school_name,))
            db.commit()
            new_school_id = cur.lastrowid

        # Sinh mã mời cho trường mới qua route admin
        res_gen = self.client.post("/admin/invite-codes/generate", data={
            "truong_id": str(new_school_id),
            "loai": "ca_nhan",
            "so_luong": "1"
        }, follow_redirects=False)
        self.assertEqual(res_gen.status_code, 302)

        # Lấy mã mời vừa sinh cho trường này
        cur.execute("SELECT ma_code FROM invite_codes WHERE truong_id = ? ORDER BY id DESC LIMIT 1", (new_school_id,))
        code_row = cur.fetchone()
        self.assertIsNotNone(code_row)
        new_code = code_row[0]

        # Đăng xuất tài khoản admin để học sinh có thể đăng ký
        self.logout()

        # Học sinh đăng ký bằng mã mời này
        import time
        new_student_code = f"HS_ISO_{int(time.time() * 1000)}"
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh = ?", (new_student_code,))
        db.commit()

        res_reg = self.client.post("/register", data={
            "ma_hoc_sinh": new_student_code,
            "ho_ten": "Học Sinh Trường Mới",
            "lop": "10A1",
            "mat_khau": "Password@123",
            "mat_khau_xac_nhan": "Password@123",
            "ma_code": new_code
        }, follow_redirects=True)
        self.assertEqual(res_reg.status_code, 200)

        # Kiểm tra học sinh được lưu chính xác vào trường mới
        cur.execute("SELECT id, truong_id, trang_thai FROM users WHERE ma_hoc_sinh = ?", (new_student_code,))
        student_row = cur.fetchone()
        self.assertIsNotNone(student_row)
        self.assertEqual(student_row["truong_id"], new_school_id, "Học sinh phải thuộc đúng trường mới")
        self.assertEqual(student_row["trang_thai"], "hoat_dong", "Học sinh có mã mời hợp lệ phải được kích hoạt ngay")

    def test_08_non_super_admin_forbidden(self):
        """[TC 8]: Tài khoản không phải super_admin bị chặn (403 Forbidden) khi gọi route trường."""
        self.login_student()

        # 1. Thử thêm trường
        res_create = self.client.post("/admin/schools/create", data={"ten_truong": "Hack School"})
        self.assertEqual(res_create.status_code, 403)

        # 2. Thử sửa trường
        res_edit = self.client.post("/admin/schools/1/edit", data={"ten_truong": "Hack School"})
        self.assertEqual(res_edit.status_code, 403)

        # 3. Thử vô hiệu hóa trường
        res_toggle = self.client.post("/admin/schools/1/toggle-status")
        self.assertEqual(res_toggle.status_code, 403)


if __name__ == "__main__":
    unittest.main(verbosity=2)
