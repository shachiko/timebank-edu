# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M1 - TIMEBANK EDU
Các ca kiểm thử:
1. Đăng ký tài khoản học sinh mới -> Có số dư khởi đầu 2.0h và ghi sổ cái credits_ledger.
2. Đăng nhập sai mật khẩu -> Báo lỗi tiếng Việt "Mã đăng nhập hoặc mật khẩu không chính xác!".
3. Phân quyền /admin:
   - Học sinh (vai_tro='hoc_sinh') truy cập /admin -> Bị chặn với mã HTTP 403 Forbidden.
   - Quản trị viên (admin / admin123) truy cập /admin -> Thành công (HTTP 200).
4. Phân quyền duyệt kỹ năng /skills/approve:
   - Học sinh truy cập -> Bị chặn với mã HTTP 403 Forbidden.
   - Giáo viên (GV001 / admin123) truy cập -> Thành công (HTTP 200).
   - Giáo viên duyệt kỹ năng -> Cập nhật trạng thái thành công.
5. Đăng xuất -> Xóa session, chuyển hướng về trang chủ.
"""

import sys
import io

# Đảm bảo in tiếng Việt chuẩn trên Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import unittest
from app import app, init_db, DATABASE_PATH


class TestMilestoneM1(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Khởi tạo DB sạch cho kiểm thử
        if DATABASE_PATH.exists():
            try:
                os.remove(DATABASE_PATH)
            except Exception:
                pass
        init_db()

    def setUp(self):
        # Mỗi ca kiểm thử sử dụng một test_client độc lập với session sạch
        self.client = app.test_client()

    def test_case_1_register_initial_balance_2h(self):
        """Test Case 1: Đăng ký tài khoản mới -> Nhận đúng 2.0h số dư ban đầu và có lịch sử sổ cái."""
        res = self.client.post("/register", data={
            "ma_hoc_sinh": "HS99001",
            "ho_ten": "Võ Thị Sáu",
            "lop": "10A5",
            "gio_ranh": "Chiều thứ 7",
            "mat_khau": "matkhau123",
            "mat_khau_xac_nhan": "matkhau123"
        }, follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        # Kiểm tra hiển thị tên và số dư 2.0h trên trang hồ sơ
        self.assertIn("Võ Thị Sáu", html)
        self.assertIn("2.0", html)

        # Kiểm tra trực tiếp trong CSDL SQLite
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT so_du_gio, vai_tro FROM users WHERE ma_hoc_sinh = 'HS99001'")
        user_row = cur.fetchone()
        self.assertIsNotNone(user_row)
        self.assertEqual(user_row[0], 2.0, "Số dư khởi đầu phải chính xác là 2.0 giờ")
        self.assertEqual(user_row[1], "hoc_sinh", "Vai trò mặc định khi đăng ký phải là hoc_sinh")

        # Kiểm tra ghi sổ cái tín dụng (credits_ledger)
        cur.execute("SELECT bien_dong, user_id FROM credits_ledger WHERE user_id = (SELECT id FROM users WHERE ma_hoc_sinh = 'HS99001')")
        ledger_row = cur.fetchone()
        self.assertIsNotNone(ledger_row)
        self.assertEqual(ledger_row[0], 2.0, "Sổ cái phải ghi nhận biến động +2.0 giờ khởi đầu")
        conn.close()

        print("\n[PASS] Case 1: Đăng ký học sinh mới thành công -> Nhận chính xác 2.0h số dư và ghi sổ cái bất biến")

    def test_case_2_wrong_password_shows_vietnamese_error(self):
        """Test Case 2: Đăng nhập sai mật khẩu -> Báo lỗi tiếng Việt chuẩn xác."""
        res = self.client.post("/login", data={
            "ma_hoc_sinh": "admin",
            "mat_khau": "sai_mat_khau_123"
        }, follow_redirects=True)

        html = res.data.decode('utf-8')
        expected_msg = "Mã đăng nhập hoặc mật khẩu không chính xác!"
        self.assertIn(expected_msg, html, f"Phải hiển thị thông báo lỗi tiếng Việt: '{expected_msg}'")
        print("[PASS] Case 2: Sai mật khẩu hiển thị thông báo lỗi tiếng Việt rõ ràng")

    def test_case_3_rbac_admin_route_protection(self):
        """Test Case 3: Phân quyền /admin: Học sinh bị chặn 403 Forbidden; Admin truy cập thành công."""
        # 1. Đăng nhập bằng tài khoản học sinh
        login_res = self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        # Học sinh cố tình truy cập /admin -> Phải bị chặn 403 Forbidden!
        admin_res_student = self.client.get("/admin")
        self.assertEqual(admin_res_student.status_code, 403, "Học sinh vào /admin phải nhận mã HTTP 403 Forbidden")
        html_403 = admin_res_student.data.decode('utf-8')
        self.assertIn("Truy cập bị từ chối", html_403)
        print("[PASS] Case 3a: Học sinh vào /admin -> Bị chặn với mã HTTP 403 Forbidden")

        # Đăng xuất tài khoản học sinh
        self.client.get("/logout")

        # 2. Đăng nhập bằng tài khoản admin có sẵn (admin / admin123)
        admin_login = self.client.post("/login", data={
            "ma_hoc_sinh": "admin",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(admin_login.status_code, 200)

        # Quản trị viên truy cập /admin -> Thành công (HTTP 200)
        admin_res_admin = self.client.get("/admin")
        self.assertEqual(admin_res_admin.status_code, 200)
        html_admin = admin_res_admin.data.decode('utf-8')
        self.assertIn("Bảng điều khiển Quản trị", html_admin)
        self.assertIn("Danh sách Tài khoản Người dùng", html_admin)
        print("[PASS] Case 3b: Quản trị viên (admin/admin123) vào /admin thành công (HTTP 200)")

    def test_case_4_rbac_skills_approval(self):
        """Test Case 4: Phân quyền Duyệt kỹ năng: Chỉ Giáo viên/Admin mới được quyền."""
        # 1. Đăng nhập học sinh
        login_hs = self.client.post("/login", data={
            "ma_hoc_sinh": "HS12001",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_hs.status_code, 200)

        # Học sinh vào trang duyệt kỹ năng -> Bị chặn 403
        hs_res = self.client.get("/skills/approve")
        self.assertEqual(hs_res.status_code, 403, "Học sinh không được phép vào /skills/approve")

        self.client.get("/logout")

        # 2. Đăng nhập Giáo viên (GV001 / admin123)
        login_gv = self.client.post("/login", data={
            "ma_hoc_sinh": "GV001",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_gv.status_code, 200)

        # Giáo viên vào trang duyệt kỹ năng -> Thành công 200
        gv_res = self.client.get("/skills/approve")
        self.assertEqual(gv_res.status_code, 200)
        self.assertIn("Kiểm duyệt Kỹ năng Học đường", gv_res.data.decode('utf-8'))

        # Giáo viên thực hiện phê duyệt kỹ năng #5 (Hóa học)
        approve_res = self.client.post("/skills/approve/5/da_duyet", follow_redirects=True)
        self.assertEqual(approve_res.status_code, 200)

        # Kiểm tra trạng thái đã chuyển sang 'da_duyet'
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai_duyet FROM skills WHERE id = 5")
        st = cur.fetchone()[0]
        conn.close()
        self.assertEqual(st, "da_duyet", "Kỹ năng phải chuyển sang trạng thái da_duyet")
        print("[PASS] Case 4: Giáo viên vào duyệt kỹ năng thành công; Học sinh bị chặn 403")

    def test_case_5_logout_flow(self):
        """Test Case 5: Đăng xuất -> Xóa sạch thông tin phiên và chuyển hướng về trang chủ."""
        # Đăng xuất
        logout_res = self.client.get("/logout", follow_redirects=True)
        self.assertEqual(logout_res.status_code, 200)
        html = logout_res.data.decode('utf-8')
        self.assertIn("đăng xuất khỏi hệ thống thành công", html)

        # Thử vào trang hồ sơ khi đã đăng xuất -> Bị chuyển hướng về trang login
        prof_res = self.client.get("/profile")
        self.assertEqual(prof_res.status_code, 302)
        self.assertIn("/login", prof_res.location)
        print("[PASS] Case 5: Đăng xuất hoạt động chính xác, bảo vệ các trang yêu cầu đăng nhập")


if __name__ == "__main__":
    unittest.main()
