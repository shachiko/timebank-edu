# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN — PROMPT 23.5:
TỰ ĐỘNG TẠO SUPER ADMIN KHI KHỞI ĐỘNG (DÀNH CHO RENDER MIỄN PHÍ KHÔNG CÓ SHELL)

Nghiệm thu 4 tiêu chí bắt buộc theo yêu cầu:
1. Chưa đặt biến môi trường -> Khởi động bình thường, không tạo gì thêm.
2. Đặt biến môi trường -> init_db() tạo super admin mới (vai_tro='super_admin',
   email='mshuyenuka@gmail.com', truong_id=1, trang_thai='hoat_dong') -> Đăng nhập thành công.
3. Khởi động lại khi đã tồn tại -> Không trùng, không ghi đè, không đổi mật khẩu cũ.
4. Không có mật khẩu trong code/GitHub/log (Log chỉ ghi đúng thông điệp an toàn).
"""

import os
import sys
import io
import unittest
import logging
from werkzeug.security import check_password_hash

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db, auto_create_superadmin_from_env


class TestPrompt23_5AutoSuperAdmin(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()
        # Đảm bảo môi trường sạch trước mỗi test
        os.environ.pop("SUPERADMIN_USER", None)
        os.environ.pop("SUPERADMIN_PASS", None)

    def tearDown(self):
        os.environ.pop("SUPERADMIN_USER", None)
        os.environ.pop("SUPERADMIN_PASS", None)
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: CHƯA ĐẶT BIẾN -> KHỞI ĐỘNG BÌNH THƯỜNG, KHÔNG TẠO GÌ
    # =========================================================================
    def test_01_no_env_vars_creates_nothing(self):
        """[TIÊU CHÍ 1]: Chưa đặt biến -> khởi động bình thường, không tạo super admin mới."""
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro = 'super_admin' AND ma_hoc_sinh != 'admin'")
        initial_count = cur.fetchone()[0]

        # Chạy init_db() khi không có biến môi trường
        init_db()

        cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro = 'super_admin' AND ma_hoc_sinh != 'admin'")
        new_count = cur.fetchone()[0]
        self.assertEqual(initial_count, new_count, "Không được tự ý tạo tài khoản khi thiếu biến môi trường!")

        # Thử trường hợp chỉ có 1 trong 2 biến môi trường
        os.environ["SUPERADMIN_USER"] = "only_user_no_pass"
        init_db()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'only_user_no_pass'")
        self.assertIsNone(cur.fetchone(), "Chỉ có SUPERADMIN_USER mà thiếu SUPERADMIN_PASS thì không được tạo!")

        os.environ.pop("SUPERADMIN_USER", None)
        os.environ["SUPERADMIN_PASS"] = "only_pass_no_user"
        init_db()
        cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro = 'super_admin' AND ma_hoc_sinh != 'admin'")
        self.assertEqual(cur.fetchone()[0], initial_count)

        print("\n[PASS - TC 1]: Chưa đặt biến -> khởi động hoàn toàn bình thường, không tạo tài khoản.")

    # =========================================================================
    # TIÊU CHÍ 2: ĐẶT BIẾN -> KHỞI ĐỘNG TẠO SUPER ADMIN -> ĐĂNG NHẬP THÀNH CÔNG
    # =========================================================================
    def test_02_set_env_vars_creates_superadmin_and_login_success(self):
        """[TIÊU CHÍ 2]: Đặt biến -> init_db() tự động tạo tài khoản -> Đăng nhập thành công với vai_tro='super_admin'."""
        test_user = "huyen_render_super"
        test_pass = "CoHuyenRender2026@!"

        db = get_db()
        cur = db.cursor()
        # Dọn dẹp nếu đã tồn tại từ trước
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        db.commit()

        os.environ["SUPERADMIN_USER"] = test_user
        os.environ["SUPERADMIN_PASS"] = test_pass

        # Giả lập Render khởi động app: gọi init_db()
        init_db()

        # Kiểm tra thông tin trong CSDL
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        u = cur.fetchone()
        self.assertIsNotNone(u, "Tài khoản super admin phải được tạo tự động khi khởi động có biến môi trường!")
        self.assertEqual(u["vai_tro"], "super_admin", "Vai trò phải là 'super_admin'")
        self.assertEqual(u["email"], "mshuyenuka@gmail.com", "Email mặc định phải là mshuyenuka@gmail.com")
        self.assertEqual(u["truong_id"], 1, "Trường ID phải là 1 (UK Academy)")
        self.assertEqual(u["trang_thai"], "hoat_dong", "Trạng thái phải là 'hoat_dong'")
        self.assertTrue(check_password_hash(u["mat_khau"], test_pass), "Mật khẩu phải được hash chính xác bằng werkzeug")

        # Đăng nhập thử với tài khoản vừa tạo
        self.client.get("/logout")
        res = self.client.post("/login", data={
            "ma_hoc_sinh": test_user,
            "mat_khau": test_pass
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Kiểm tra session của phiên đăng nhập
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("ma_hoc_sinh"), test_user)
            self.assertEqual(sess.get("vai_tro"), "super_admin")

        print("\n[PASS - TC 2]: Đặt biến môi trường -> tự động tạo Super Admin chuẩn và đăng nhập thành công.")

    # =========================================================================
    # TIÊU CHÍ 3: KHỞI ĐỘNG LẠI KHI ĐÃ TỒN TẠI -> KHÔNG TRÙNG, KHÔNG ĐỔI MẬT KHẨU CŨ
    # =========================================================================
    def test_03_restart_when_user_exists_preserves_old_account(self):
        """[TIÊU CHÍ 3]: Khởi động lại khi tài khoản đã tồn tại -> Không duplicate, không ghi đè, không đổi mật khẩu cũ."""
        test_user = "huyen_persistent_admin"
        original_pass = "OriginalPass2026@!"
        attacker_pass = "AttackerModifiedPass999@!"

        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        db.commit()

        # Bước 1: Tạo tài khoản với mật khẩu gốc
        os.environ["SUPERADMIN_USER"] = test_user
        os.environ["SUPERADMIN_PASS"] = original_pass
        init_db()

        cur.execute("SELECT id, mat_khau FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        u1 = cur.fetchone()
        self.assertIsNotNone(u1)
        original_hash = u1["mat_khau"]

        # Bước 2: Giả lập deploy lại hoặc ai đó đổi SUPERADMIN_PASS
        os.environ["SUPERADMIN_PASS"] = attacker_pass
        init_db()

        # Kiểm tra xem user có bị trùng hay bị đổi mật khẩu không
        cur.execute("SELECT COUNT(*) FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        self.assertEqual(cur.fetchone()[0], 1, "Không được tạo bản ghi trùng lặp!")

        cur.execute("SELECT id, mat_khau FROM users WHERE ma_hoc_sinh = ?", (test_user,))
        u2 = cur.fetchone()
        self.assertEqual(u2["mat_khau"], original_hash, "Mật khẩu cũ không được phép bị ghi đè!")
        self.assertTrue(check_password_hash(u2["mat_khau"], original_pass))
        self.assertFalse(check_password_hash(u2["mat_khau"], attacker_pass))

        # Đăng nhập bằng mật khẩu cũ vẫn thành công
        self.client.get("/logout")
        res_old = self.client.post("/login", data={
            "ma_hoc_sinh": test_user,
            "mat_khau": original_pass
        }, follow_redirects=True)
        self.assertEqual(res_old.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("ma_hoc_sinh"), test_user)

        # Đăng nhập bằng mật khẩu mới bị từ chối
        self.client.get("/logout")
        res_new = self.client.post("/login", data={
            "ma_hoc_sinh": test_user,
            "mat_khau": attacker_pass
        }, follow_redirects=True)
        with self.client.session_transaction() as sess:
            self.assertIsNone(sess.get("ma_hoc_sinh"))

        print("\n[PASS - TC 3]: Idempotency hoàn hảo: khởi động lại không tạo trùng, không ghi đè mật khẩu cũ.")

    # =========================================================================
    # TIÊU CHÍ 4: BẢO MẬT: KHÔNG LOG USER/PASS, AN TOÀN SAU KHI XÓA BIẾN MÔI TRƯỜNG
    # =========================================================================
    def test_04_security_no_credentials_in_logs_and_safe_removal(self):
        """[TIÊU CHÍ 4]: Log an toàn ('Đã tạo super admin từ biến môi trường', KHÔNG in user/pass) & tài khoản vẫn tồn tại sau khi xóa biến."""
        secret_user = "huyen_top_secret_usr"
        secret_pass = "SuperUltraSecret2026!@#"

        db = get_db()
        cur = db.cursor()
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh = ?", (secret_user,))
        db.commit()

        os.environ["SUPERADMIN_USER"] = secret_user
        os.environ["SUPERADMIN_PASS"] = secret_pass

        # Bắt stdout và log để kiểm tra
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        app.logger.addHandler(handler)

        old_stdout = sys.stdout
        stdout_capture = io.StringIO()
        sys.stdout = stdout_capture

        try:
            init_db()
        finally:
            sys.stdout = old_stdout
            app.logger.removeHandler(handler)

        captured_stdout = stdout_capture.getvalue()
        captured_logs = log_stream.getvalue()
        combined_logs = captured_stdout + "\n" + captured_logs

        # Kiểm tra thông điệp xác nhận chuẩn
        self.assertIn("Đã tạo super admin từ biến môi trường", combined_logs)
        # Tuyệt đối không chứa mật khẩu hay username
        self.assertNotIn(secret_pass, combined_logs, "Mật khẩu tuyệt đối không được xuất hiện trong log!")
        self.assertNotIn(secret_user, combined_logs, "Tên đăng nhập tuyệt đối không được xuất hiện trong log thông báo!")

        # Bước tiếp theo của hướng dẫn cho thầy: Xóa ngay 2 biến môi trường
        os.environ.pop("SUPERADMIN_USER", None)
        os.environ.pop("SUPERADMIN_PASS", None)

        # Chạy lại init_db() khi đã xóa biến môi trường
        init_db()

        # Tài khoản vẫn còn nguyên vẹn trong CSDL và đăng nhập bình thường
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (secret_user,))
        self.assertIsNotNone(cur.fetchone())

        self.client.get("/logout")
        res_after = self.client.post("/login", data={
            "ma_hoc_sinh": secret_user,
            "mat_khau": secret_pass
        }, follow_redirects=True)
        self.assertEqual(res_after.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("ma_hoc_sinh"), secret_user)
            self.assertEqual(sess.get("vai_tro"), "super_admin")

        print("\n[PASS - TC 4]: Không rò rỉ thông tin đăng nhập trong log; an toàn tuyệt đối khi xóa biến môi trường.")


if __name__ == "__main__":
    unittest.main()
