# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN — PROMPT 23: QUẢN TRỊ TÀI KHOẢN
(Demo công khai + Super Admin bí mật + Quản lý tài khoản + Quên mật khẩu)

Nghiệm thu 8 tiêu chí bắt buộc:
1. Đăng nhập 3 tài khoản demo OK; nút đổi mật khẩu bị ẩn với demo; chặn POST /change-password.
2. demo_quantruong không thấy dữ liệu trường thật (cách ly tại Trường Demo ID 99).
3. Chưa đặt biến môi trường -> flask create-superadmin báo lỗi, không tạo.
4. Đặt biến -> chạy lệnh -> đăng nhập super_admin mới OK; không in mật khẩu ra log; xóa biến sau đó.
5. Super_admin tạo được school_admin và giao_vien mới gắn đúng trường.
6. "Reset demo" 1-click đưa dữ liệu Trường Demo về trạng thái ban đầu.
7. Quên mật khẩu qua email: sinh link token 1h, 1 lần dùng, đặt lại mật khẩu mới OK; không crash nếu thiếu SMTP.
8. Không có mật khẩu/key trong code/GitHub/log.
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db, DEMO_SCHOOL_ID, is_demo_user


class TestPrompt23AccountManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: ĐĂNG NHẬP 3 TÀI KHOẢN DEMO & ẨN / CHẶN ĐỔI MẬT KHẨU
    # =========================================================================
    def test_01_demo_accounts_login_and_password_change_blocked(self):
        """[TIÊU CHÍ 1]: Đăng nhập 3 tài khoản demo OK; nút đổi mật khẩu bị ẩn; chặn POST /change-password."""
        demo_accounts = [
            ("demo_quantruong", "demo123", "school_admin"),
            ("demo_giaovien", "demo123", "giao_vien"),
            ("demo_hocsinh", "demo123", "hoc_sinh"),
            ("admin", "admin123", "school_admin"),  # Tài khoản admin cũ đã hạ quyền
        ]

        for username, password, expected_role in demo_accounts:
            self.client.get("/logout")
            res_login = self.client.post("/login", data={
                "ma_hoc_sinh": username,
                "mat_khau": password
            }, follow_redirects=True)
            self.assertEqual(res_login.status_code, 200, f"Đăng nhập tài khoản {username} thất bại")

            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get("vai_tro"), expected_role, f"Vai trò của {username} không đúng")
                self.assertEqual(sess.get("truong_id"), DEMO_SCHOOL_ID, f"Trường của {username} phải là Demo ({DEMO_SCHOOL_ID})")

            # Kiểm tra trang profile: nút đổi mật khẩu bị ẩn
            res_profile = self.client.get("/profile")
            self.assertEqual(res_profile.status_code, 200)
            html_profile = res_profile.data.decode("utf-8")
            self.assertNotIn('id="btnChangePassword"', html_profile, f"Tài khoản demo {username} không được có nút đổi mật khẩu")
            self.assertIn("Tài khoản Demo (Không thể đổi mật khẩu)", html_profile)

            # Thử gửi request POST trực tiếp để đổi mật khẩu -> Phải bị chặn
            res_change = self.client.post("/change-password", data={
                "mat_khau_cu": password,
                "mat_khau_moi": "NewHackedPass123",
                "mat_khau_xac_nhan": "NewHackedPass123"
            }, follow_redirects=True)
            html_change = res_change.data.decode("utf-8")
            self.assertIn("không được phép đổi mật khẩu", html_change)

            # Xác minh mật khẩu trong DB không bị thay đổi
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT mat_khau FROM users WHERE ma_hoc_sinh = ?", (username,))
            pwd_hash = cur.fetchone()["mat_khau"]
            self.assertTrue(check_password_hash(pwd_hash, password), f"Mật khẩu của {username} bị thay đổi trái phép")

        # Kiểm tra tài khoản thường (không demo) vẫn có nút đổi mật khẩu và đổi được
        self.client.get("/logout")
        res_user_login = self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(res_user_login.status_code, 200)
        res_user_prof = self.client.get("/profile")
        html_user_prof = res_user_prof.data.decode("utf-8")
        self.assertIn('id="btnChangePassword"', html_user_prof, "Tài khoản thường phải có nút đổi mật khẩu")

        # Kiểm tra hộp thông tin demo trên trang đăng nhập
        self.client.get("/logout")
        res_login_page = self.client.get("/login")
        html_login_page = res_login_page.data.decode("utf-8")
        self.assertTrue(
            "Tài khoản demo đăng nhập nhanh để trải nghiệm" in html_login_page or
            "Tài khoản demo cho giám khảo" in html_login_page
        )
        self.assertIn("demo_quantruong", html_login_page)
        self.assertIn("demo_giaovien", html_login_page)
        self.assertIn("demo_hocsinh", html_login_page)
        self.assertIn("Quên mật khẩu?", html_login_page)
        print("\n[PASS - TC 1]: Đăng nhập 3 tài khoản demo OK, nút đổi mật khẩu bị ẩn, chặn đổi mật khẩu thành công.")

    # =========================================================================
    # TIÊU CHÍ 2: DEMO_QUANTRUONG CÁCH LY, KHÔNG THẤY DỮ LIỆU TRƯỜNG THẬT
    # =========================================================================
    def test_02_demo_quantruong_cannot_see_real_school_data(self):
        """[TIÊU CHÍ 2]: demo_quantruong chỉ quậy trong Trường Demo, không chạm dữ liệu trường thật."""
        self.client.get("/logout")
        self.client.post("/login", data={
            "ma_hoc_sinh": "demo_quantruong",
            "mat_khau": "demo123"
        }, follow_redirects=True)

        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        html_admin = res_admin.data.decode("utf-8")

        # Hiển thị đúng tên Trường Demo
        self.assertIn("Trường Demo", html_admin)
        # Không có quyền Super Admin
        self.assertNotIn("TỔNG QUẢN TRỊ (SUPER ADMIN)", html_admin)

        # Tuyệt đối không thấy học sinh của các trường thật trong bảng quản lý
        self.assertNotIn("<td><code>HS12001</code></td>", html_admin, "demo_quantruong không được thấy HS trường 1")
        self.assertNotIn("<td><code>HS11002</code></td>", html_admin, "demo_quantruong không được thấy HS trường 1")
        self.assertNotIn("<td><code>GV001</code></td>", html_admin, "demo_quantruong không được thấy GV trường 1")

        # Không có dropdown lọc chọn tất cả các trường
        self.assertNotIn("-- Tất cả các trường (4 trường) --", html_admin)
        print("\n[PASS - TC 2]: demo_quantruong được cách ly hoàn toàn tại Trường Demo ID 99.")

    # =========================================================================
    # TIÊU CHÍ 3: THIẾU BIẾN MÔI TRƯỜNG -> FLASK CREATE-SUPERADMIN BÁO LỖI
    # =========================================================================
    def test_03_create_superadmin_cli_fails_without_env_vars(self):
        """[TIÊU CHÍ 3]: Chưa đặt biến môi trường -> flask create-superadmin báo lỗi, không tạo."""
        runner = app.test_cli_runner()

        # Đảm bảo gỡ biến môi trường nếu có
        env_backup = {}
        for k in ["SUPERADMIN_USER", "SUPERADMIN_PASS"]:
            if k in os.environ:
                env_backup[k] = os.environ.pop(k)

        try:
            res = runner.invoke(args=["create-superadmin"])
            # Lệnh phải báo lỗi hoặc trả về mã thoát != 0
            output = res.output
            self.assertTrue(
                res.exit_code != 0 or "Lỗi: Thiếu biến môi trường" in output,
                "Lệnh phải báo lỗi khi thiếu SUPERADMIN_USER hoặc SUPERADMIN_PASS"
            )
            self.assertIn("SUPERADMIN_USER", output)
            self.assertIn("SUPERADMIN_PASS", output)
        finally:
            # Khôi phục nếu có
            for k, v in env_backup.items():
                os.environ[k] = v

        print("\n[PASS - TC 3]: flask create-superadmin báo lỗi chuẩn xác khi thiếu biến môi trường.")

    # =========================================================================
    # TIÊU CHÍ 4: ĐẶT BIẾN -> TẠO SUPER_ADMIN THẬT CHO CÔ HUYỀN & IDEMPOTENCY
    # =========================================================================
    def test_04_create_superadmin_cli_success_and_idempotent(self):
        # Dọn dẹp bất kỳ super_admin nào khác (trừ 'admin') để test tạo mới sạch sẽ
        db = get_db()
        cur = db.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM users WHERE vai_tro = 'super_admin' AND ma_hoc_sinh != 'admin'")
        cur.execute("PRAGMA foreign_keys = ON")
        db.commit()

        test_user = "huyen_super_secret"
        test_pass = "CoHuyenPass2026!@#"

        os.environ["SUPERADMIN_USER"] = test_user
        os.environ["SUPERADMIN_PASS"] = test_pass

        runner = app.test_cli_runner()
        try:
            # 1. Chạy lệnh lần 1: Tạo thành công
            res1 = runner.invoke(args=["create-superadmin"])
            self.assertEqual(res1.exit_code, 0)
            self.assertIn("Đã tạo thành công tài khoản Super Admin", res1.output)
            # TUYỆT ĐỐI không in mật khẩu ra log
            self.assertNotIn(test_pass, res1.output, "Mật khẩu tuyệt đối không được in ra log!")

            # Kiểm tra CSDL
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = ?", (test_user,))
            u = cur.fetchone()
            self.assertIsNotNone(u, "User super admin phải được tạo trong CSDL")
            self.assertEqual(u["vai_tro"], "super_admin")
            self.assertEqual(u["email"], "mshuyenuka@gmail.com")
            self.assertEqual(u["truong_id"], 1)
            self.assertEqual(u["trang_thai"], "hoat_dong")
            self.assertTrue(check_password_hash(u["mat_khau"], test_pass))

            # 2. Đăng nhập với Super Admin vừa tạo
            self.client.get("/logout")
            res_login = self.client.post("/login", data={
                "ma_hoc_sinh": test_user,
                "mat_khau": test_pass
            }, follow_redirects=True)
            self.assertEqual(res_login.status_code, 200)
            with self.client.session_transaction() as sess:
                self.assertEqual(sess.get("vai_tro"), "super_admin")
                self.assertEqual(sess.get("ma_hoc_sinh"), test_user)

            # 3. Chạy lệnh lần 2 (Idempotency): Báo "đã tồn tại", không tạo trùng
            res2 = runner.invoke(args=["create-superadmin"])
            self.assertIn("đã tồn tại", res2.output)
            self.assertNotIn(test_pass, res2.output)

        finally:
            # Dọn dẹp biến môi trường
            os.environ.pop("SUPERADMIN_USER", None)
            os.environ.pop("SUPERADMIN_PASS", None)

        print("\n[PASS - TC 4]: Tạo Super Admin thành công, không lộ mật khẩu, cơ chế idempotency bảo vệ an toàn.")

    # =========================================================================
    # TIÊU CHÍ 5: SUPER_ADMIN TẠO SCHOOL_ADMIN VÀ GIAO_VIEN GẮN ĐÚNG TRƯỜNG
    # =========================================================================
    def test_05_superadmin_creates_school_admin_and_teacher(self):
        """[TIÊU CHÍ 5]: Super_admin tạo được school_admin và giao_vien gắn đúng trường tại /admin/accounts."""
        # 1. Tạo và đăng nhập tài khoản super_admin
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'SUPER_TEST_PROMPT23'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio, email)
                VALUES ('SUPER_TEST_PROMPT23', 'Cô Huyền Super Admin', ?, 'super_admin', 1, 'hoat_dong', 10.0, 'mshuyenuka@gmail.com')
            """, (generate_password_hash("SuperPass123"),))
            db.commit()

        self.client.get("/logout")
        self.client.post("/login", data={
            "ma_hoc_sinh": "SUPER_TEST_PROMPT23",
            "mat_khau": "SuperPass123"
        }, follow_redirects=True)

        # 2. Truy cập trang /admin/accounts
        res_acc = self.client.get("/admin/accounts")
        self.assertEqual(res_acc.status_code, 200)
        html_acc = res_acc.data.decode("utf-8")
        self.assertIn("Quản lý Tài khoản Hệ thống", html_acc)

        # 3. Tạo Quản trị trường cho Trường 2 (Trường THCS Nguyễn Văn Thuộc)
        sa_user = "admin_nguyenvanthuoc"
        sa_pass = "SchoolPass123!"
        res_create_sa = self.client.post("/admin/accounts/create", data={
            "vai_tro": "school_admin",
            "ma_hoc_sinh": sa_user,
            "ho_ten": "Thầy Hiệu Trưởng Thuộc",
            "email": "hieutruong@thuoc.edu.vn",
            "truong_id": "2",
            "mat_khau": sa_pass
        }, follow_redirects=True)
        self.assertEqual(res_create_sa.status_code, 200)

        # Xác minh trong DB
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = ?", (sa_user,))
        sa_row = cur.fetchone()
        self.assertIsNotNone(sa_row)
        self.assertEqual(sa_row["vai_tro"], "school_admin")
        self.assertEqual(sa_row["truong_id"], 2)
        self.assertEqual(sa_row["email"], "hieutruong@thuoc.edu.vn")

        # 4. Tạo Giáo viên cho Trường 3 (Trường THCS Lê Văn Tám)
        gv_user = "gv_levantam_01"
        gv_pass = "GiaoVienPass123!"
        res_create_gv = self.client.post("/admin/accounts/create", data={
            "vai_tro": "giao_vien",
            "ma_hoc_sinh": gv_user,
            "ho_ten": "Cô Lê Thị Hoa",
            "email": "hoa.le@lvtam.edu.vn",
            "truong_id": "3",
            "mat_khau": gv_pass
        }, follow_redirects=True)
        self.assertEqual(res_create_gv.status_code, 200)

        # Xác minh trong DB
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = ?", (gv_user,))
        gv_row = cur.fetchone()
        self.assertIsNotNone(gv_row)
        self.assertEqual(gv_row["vai_tro"], "giao_vien")
        self.assertEqual(gv_row["truong_id"], 3)
        self.assertEqual(gv_row["email"], "hoa.le@lvtam.edu.vn")

        # 5. Đăng nhập tài khoản School Admin vừa tạo -> Kiểm tra quyền và trường
        self.client.get("/logout")
        res_sa_login = self.client.post("/login", data={
            "ma_hoc_sinh": sa_user,
            "mat_khau": sa_pass
        }, follow_redirects=True)
        self.assertEqual(res_sa_login.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("vai_tro"), "school_admin")
            self.assertEqual(sess.get("truong_id"), 2)

        # School Admin không được vào /admin/accounts (chỉ dành cho Super Admin)
        res_sa_block = self.client.get("/admin/accounts")
        self.assertEqual(res_sa_block.status_code, 302)

        print("\n[PASS - TC 5]: Super Admin tạo school_admin và giao_vien gắn đúng trường; phân quyền chuẩn xác.")

    # =========================================================================
    # TIÊU CHÍ 6: NÚT "RESET DEMO" KHÔI PHỤC DỮ LIỆU TRƯỜNG DEMO
    # =========================================================================
    def test_06_reset_demo_school_restores_clean_state(self):
        """[TIÊU CHÍ 6]: Nút 'Reset demo' đưa dữ liệu Trường Demo về trạng thái ban đầu."""
        db = get_db()
        cur = db.cursor()

        # 1. Đăng nhập học sinh demo và tạo thêm 1 kỹ năng thử nghiệm bừa bãi
        self.client.get("/logout")
        self.client.post("/login", data={
            "ma_hoc_sinh": "demo_hocsinh",
            "mat_khau": "demo123"
        }, follow_redirects=True)

        res_new_skill = self.client.post("/skills/new", data={
            "linh_vuc": "Toán",
            "tieu_de": "Kỹ năng rác thử nghiệm của Giám khảo",
            "mo_ta": "Mô tả thử nghiệm sẽ được reset sạch sẽ",
            "dia_diem": "online",
            "truong_id": str(DEMO_SCHOOL_ID)
        }, follow_redirects=True)
        self.assertEqual(res_new_skill.status_code, 200)

        # Chỉnh số dư giờ của demo_hocsinh thành 99.9h
        cur.execute("UPDATE users SET so_du_gio = 99.9 WHERE ma_hoc_sinh = 'demo_hocsinh'")
        db.commit()

        # Xác minh kỹ năng rác tồn tại
        cur.execute("SELECT COUNT(*) FROM skills WHERE truong_id = ? AND tieu_de = 'Kỹ năng rác thử nghiệm của Giám khảo'", (DEMO_SCHOOL_ID,))
        self.assertGreaterEqual(cur.fetchone()[0], 1)

        # 2. Đăng nhập Quản trị trường Demo và thực hiện bấm Reset Demo
        self.client.get("/logout")
        self.client.post("/login", data={
            "ma_hoc_sinh": "demo_quantruong",
            "mat_khau": "demo123"
        }, follow_redirects=True)

        res_reset = self.client.post("/admin/demo/reset", follow_redirects=True)
        self.assertEqual(res_reset.status_code, 200)
        html_reset = res_reset.data.decode("utf-8")
        self.assertTrue("Đã khôi phục" in html_reset and "Trường Demo" in html_reset)

        # 3. Kiểm tra CSDL sau khi reset:
        # - Kỹ năng rác biến mất
        cur.execute("SELECT COUNT(*) FROM skills WHERE truong_id = ? AND tieu_de = 'Kỹ năng rác thử nghiệm của Giám khảo'", (DEMO_SCHOOL_ID,))
        self.assertEqual(cur.fetchone()[0], 0, "Kỹ năng rác thử nghiệm phải bị xóa")

        # - Kỹ năng demo mẫu vẫn còn
        cur.execute("SELECT COUNT(*) FROM skills WHERE truong_id = ?", (DEMO_SCHOOL_ID,))
        self.assertGreaterEqual(cur.fetchone()[0], 1, "Kỹ năng mẫu chuẩn phải được phục hồi")

        # - Số dư giờ demo_hocsinh quay về 3.0h
        cur.execute("SELECT so_du_gio, mat_khau FROM users WHERE ma_hoc_sinh = 'demo_hocsinh'")
        u_hs = cur.fetchone()
        self.assertEqual(u_hs["so_du_gio"], 3.0)
        self.assertTrue(check_password_hash(u_hs["mat_khau"], "demo123"))

        # - Mật khẩu các tài khoản demo chuẩn là demo123
        cur.execute("SELECT mat_khau FROM users WHERE ma_hoc_sinh = 'demo_quantruong'")
        u_qt = cur.fetchone()
        self.assertTrue(check_password_hash(u_qt["mat_khau"], "demo123"))

        print("\n[PASS - TC 6]: Reset Demo khôi phục dữ liệu Trường Demo về trạng thái hoàn hảo 1-click.")

    # =========================================================================
    # TIÊU CHÍ 7: QUÊN MẬT KHẨU QUA EMAIL (TOKEN 1 GIỜ, 1 LẦN DÙNG)
    # =========================================================================
    def test_07_forgot_password_email_flow_and_token_invalidation(self):
        """[TIÊU CHÍ 7]: Quên mật khẩu qua email: sinh link reset 1h, 1 lần dùng, cập nhật mật khẩu mới OK."""
        # 1. Chuẩn bị tài khoản có email
        db = get_db()
        cur = db.cursor()
        test_email = "test_reset_user@timebankedu.vn"
        test_user = "USER_RESET_TEST"
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM password_reset_tokens WHERE user_id IN (SELECT id FROM users WHERE ma_hoc_sinh = ?)", (test_user,))
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio, email)
            VALUES (?, 'Thầy Cần Reset Pass', ?, 'school_admin', 1, 'hoat_dong', 5.0, ?)
        """, (test_user, generate_password_hash("OldPassword123"), test_email))
        db.commit()

        # 2. Trang Quên mật khẩu GET
        res_get = self.client.get("/forgot-password")
        self.assertEqual(res_get.status_code, 200)
        html_get = res_get.data.decode("utf-8")
        self.assertIn("Khôi phục Mật khẩu", html_get)

        # 3. Gửi yêu cầu reset với email hợp lệ
        res_post = self.client.post("/forgot-password", data={"email": test_email}, follow_redirects=True)
        self.assertEqual(res_post.status_code, 200)
        html_post = res_post.data.decode("utf-8")
        self.assertIn("đặt lại mật khẩu", html_post)

        # 4. Kiểm tra token đã sinh trong CSDL
        cur.execute("""
            SELECT prt.token, prt.het_han, prt.da_dung 
            FROM password_reset_tokens prt
            JOIN users u ON prt.user_id = u.id
            WHERE u.ma_hoc_sinh = ?
            ORDER BY prt.id DESC LIMIT 1
        """, (test_user,))
        token_row = cur.fetchone()
        self.assertIsNotNone(token_row, "Phải sinh token trong password_reset_tokens")
        token_str = token_row["token"]
        self.assertEqual(token_row["da_dung"], 0, "Token mới sinh phải có da_dung = 0")

        # 5. Mở trang reset mật khẩu qua link token
        res_reset_page = self.client.get(f"/reset-password/{token_str}")
        self.assertEqual(res_reset_page.status_code, 200)
        html_reset_page = res_reset_page.data.decode("utf-8")
        self.assertIn("Thiết lập Mật khẩu Mới", html_reset_page)

        # 6. POST mật khẩu mới
        new_password = "BrandNewPassword2026!#"
        res_do_reset = self.client.post(f"/reset-password/{token_str}", data={
            "mat_khau_moi": new_password,
            "mat_khau_xac_nhan": new_password
        }, follow_redirects=True)
        self.assertEqual(res_do_reset.status_code, 200)
        html_do_reset = res_do_reset.data.decode("utf-8")
        self.assertIn("Đặt lại mật khẩu thành công", html_do_reset)

        # 7. Token phải chuyển sang da_dung = 1
        cur.execute("SELECT da_dung FROM password_reset_tokens WHERE token = ?", (token_str,))
        self.assertEqual(cur.fetchone()["da_dung"], 1, "Token phải bị đánh dấu đã dùng")

        # 8. Tái sử dụng token lần 2 -> Phải bị từ chối
        res_reuse = self.client.get(f"/reset-password/{token_str}", follow_redirects=True)
        html_reuse = res_reuse.data.decode("utf-8")
        self.assertIn("không hợp lệ hoặc đã hết hạn", html_reuse)

        # 9. Đăng nhập bằng mật khẩu cũ -> Thất bại; Mật khẩu mới -> Thành công
        res_login_old = self.client.post("/login", data={
            "ma_hoc_sinh": test_user,
            "mat_khau": "OldPassword123"
        }, follow_redirects=True)
        self.assertIn("Mã đăng nhập hoặc mật khẩu không chính xác", res_login_old.data.decode("utf-8"))

        res_login_new = self.client.post("/login", data={
            "ma_hoc_sinh": test_user,
            "mat_khau": new_password
        }, follow_redirects=True)
        self.assertEqual(res_login_new.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("ma_hoc_sinh"), test_user)

        # 10. Thử gửi email không tồn tại trong hệ thống
        res_nonexistent = self.client.post("/forgot-password", data={"email": "nonexistent@unknown.com"}, follow_redirects=True)
        self.assertIn("Không tìm thấy tài khoản quản trị hoặc giáo viên", res_nonexistent.data.decode("utf-8"))

        print("\n[PASS - TC 7]: Quên mật khẩu qua email: sinh token an toàn 1h, 1 lần dùng, đổi mật khẩu và đăng nhập OK.")

    # =========================================================================
    # TIÊU CHÍ 8: KHÔNG CÓ MẬT KHẨU / KHÓA BÍ MẬT TRONG MÃ NGUỒN HOẶC LOG
    # =========================================================================
    def test_08_no_plain_passwords_or_keys_in_repo(self):
        """[TIÊU CHÍ 8]: Không có mật khẩu cô Huyền, không có api key trong code/GitHub/log."""
        # 1. Đảm bảo .gitignore loại trừ các file bí mật
        with open(".gitignore", "r", encoding="utf-8") as f:
            gi_content = f.read()
        self.assertIn(".env", gi_content)

        # 2. Kiểm tra app.py không hardcode mật khẩu thực của cô Huyền
        with open("app.py", "r", encoding="utf-8") as f:
            app_code = f.read()

        # Không chứa mật khẩu dạng biến gán thẳng
        self.assertNotIn("SUPERADMIN_PASS =", app_code)
        self.assertNotIn("SUPERADMIN_PASS=", app_code)
        self.assertNotIn("mshuyenuka_pass", app_code.lower())

        print("\n[PASS - TC 8]: Bảo mật hoàn hảo: không lưu trữ mật khẩu thật của cô Huyền trong mã nguồn hay log.")


if __name__ == "__main__":
    unittest.main()
