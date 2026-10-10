# -*- coding: utf-8 -*-
"""
Test Suite: Chuẩn hóa menu dropdown theo đúng vai trò
1. Học sinh: Lịch của tôi, Ví của tôi, Hồ sơ & Cài đặt, Đăng kỹ năng mới, Hoạt động Vì cộng đồng, AI gợi ý bạn học, Đăng xuất.
2. Giáo viên: Hồ sơ & Cài đặt, Đăng kỹ năng mới, Duyệt kỹ năng học sinh, Giám sát phòng học ảo, Quản lý Bảng tin, Hoạt động Vì cộng đồng, Đăng xuất.
   BỎ: Lịch của tôi, Ví của tôi.
3. Quản trị trường: Hồ sơ & Cài đặt, Quản lý Tài khoản, Quản lý Mã mời, Duyệt kỹ năng, Quản lý Bảng tin, Chương trình Cộng đồng, Báo cáo trường, Đăng xuất.
   BỎ: Lịch của tôi, Ví của tôi, Đăng kỹ năng mới.
4. Tổng quản trị: Tất cả của Quản trị trường + Quản lý Trường học, Báo cáo toàn hệ thống.
   BỎ: Lịch của tôi, Ví của tôi, Đăng kỹ năng mới.
"""
import unittest
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, init_db, get_db

class TestPromptRoleMenus(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.client = app.test_client()

    def _login(self, username, password):
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def _get_dropdown_html(self, res):
        html = res.data.decode("utf-8")
        badge_pos = html.find("user-avatar-badge")
        if badge_pos == -1:
            return "", html
        start = html.find('<ul class="dropdown-menu', badge_pos)
        if start == -1:
            return "", html
        end = html.find('</ul>', start)
        return html[start:end+5], html

    def test_01_student_menu(self):
        """Học sinh: đầy đủ 7 mục học sinh, không thấy mục giáo viên/quản trị, có số dư giờ."""
        res_login = self._login("demo_hocsinh", "demo123")
        self.assertEqual(res_login.status_code, 200)

        res = self.client.get("/")
        menu_html, full_html = self._get_dropdown_html(res)
        self.assertTrue(len(menu_html) > 0, "Không tìm thấy user dropdown menu")

        # CÁC MỤC GIỮ
        self.assertIn("Lịch của tôi", menu_html)
        self.assertIn("Ví của tôi", menu_html)
        self.assertIn("Hồ sơ &amp; Cài đặt", menu_html)
        self.assertIn("Đăng kỹ năng mới", menu_html)
        self.assertIn("Hoạt động Vì cộng đồng", menu_html)
        self.assertIn("AI gợi ý bạn học", menu_html)
        self.assertIn("Đăng xuất", menu_html)

        # CÁC MỤC BỎ / KHÔNG CÓ
        self.assertNotIn("Duyệt kỹ năng học sinh", menu_html)
        self.assertNotIn("Giám sát phòng học ảo", menu_html)
        self.assertNotIn("Quản lý Bảng tin", menu_html)
        self.assertNotIn("Quản lý Tài khoản", menu_html)
        self.assertNotIn("Quản lý Mã mời", menu_html)
        self.assertNotIn("Báo cáo trường", menu_html)
        self.assertNotIn("Quản lý Trường học", menu_html)
        self.assertNotIn("Báo cáo toàn hệ thống", menu_html)

        # BADGE SỐ DƯ TRÊN PILL
        self.assertIn("user-balance-badge", full_html)
        self.assertNotIn("user-role-badge", full_html)

    def test_02_teacher_menu(self):
        """Giáo viên: giữ 7 mục của giáo viên, BỎ Lịch của tôi & Ví của tôi, không hiện số dư giờ."""
        res_login = self._login("demo_giaovien", "demo123")
        self.assertEqual(res_login.status_code, 200)

        res = self.client.get("/")
        menu_html, full_html = self._get_dropdown_html(res)
        self.assertTrue(len(menu_html) > 0, "Không tìm thấy user dropdown menu")

        # CÁC MỤC GIỮ
        self.assertIn("Hồ sơ &amp; Cài đặt", menu_html)
        self.assertIn("Đăng kỹ năng mới", menu_html)
        self.assertIn("Duyệt kỹ năng học sinh", menu_html)
        self.assertIn("Giám sát phòng học ảo", menu_html)
        self.assertIn("Quản lý Bảng tin", menu_html)
        self.assertIn("Hoạt động Vì cộng đồng", menu_html)
        self.assertIn("Đăng xuất", menu_html)

        # CÁC MỤC BỎ
        self.assertNotIn("Lịch của tôi", menu_html)
        self.assertNotIn("Ví của tôi", menu_html)
        self.assertNotIn("AI gợi ý bạn học", menu_html)
        self.assertNotIn("Quản lý Tài khoản", menu_html)
        self.assertNotIn("Quản lý Mã mời", menu_html)
        self.assertNotIn("Báo cáo trường", menu_html)
        self.assertNotIn("Quản lý Trường học", menu_html)
        self.assertNotIn("Báo cáo toàn hệ thống", menu_html)

        # BADGE VAI TRÒ TRÊN PILL
        self.assertIn("user-role-badge", full_html)
        self.assertIn("Giáo viên", full_html)
        self.assertNotIn("user-balance-badge", full_html)

    def test_03_school_admin_menu(self):
        """Quản trị trường: giữ các mục quản trị trường, BỎ Lịch của tôi, Ví của tôi, Đăng kỹ năng mới."""
        res_login = self._login("demo_quantruong", "demo123")
        self.assertEqual(res_login.status_code, 200)

        res = self.client.get("/")
        menu_html, full_html = self._get_dropdown_html(res)
        self.assertTrue(len(menu_html) > 0, "Không tìm thấy user dropdown menu")

        # CÁC MỤC GIỮ
        self.assertIn("Hồ sơ &amp; Cài đặt", menu_html)
        self.assertIn("Quản lý Tài khoản", menu_html)
        self.assertIn("Quản lý Mã mời", menu_html)
        self.assertIn("Duyệt kỹ năng", menu_html)
        self.assertIn("Quản lý Bảng tin", menu_html)
        self.assertIn("Chương trình Cộng đồng", menu_html)
        self.assertIn("Báo cáo trường", menu_html)
        self.assertIn("Đăng xuất", menu_html)

        # CÁC MỤC BỎ
        self.assertNotIn("Lịch của tôi", menu_html)
        self.assertNotIn("Ví của tôi", menu_html)
        self.assertNotIn("Đăng kỹ năng mới", menu_html)
        self.assertNotIn("AI gợi ý bạn học", menu_html)
        self.assertNotIn("Quản lý Trường học", menu_html)
        self.assertNotIn("Báo cáo toàn hệ thống", menu_html)

        # BADGE VAI TRÒ TRÊN PILL
        self.assertIn("user-role-badge", full_html)
        self.assertIn("Quản trị trường", full_html)
        self.assertNotIn("user-balance-badge", full_html)

    def test_04_super_admin_menu(self):
        """Tổng quản trị: tất cả của Quản trị trường + Quản lý Trường học, Báo cáo toàn hệ thống. BỎ Lịch của tôi, Ví của tôi."""
        # Tạo hoặc lấy user super_admin
        with self.client.session_transaction() as sess:
            sess["user_id"] = 999
            sess["ma_hoc_sinh"] = "test_super_admin"
            sess["ho_ten"] = "Tổng Quản Trị Viên"
            sess["vai_tro"] = "super_admin"
            sess["truong_id"] = 1
            sess["so_du_gio"] = 999.0

        res = self.client.get("/")
        menu_html, full_html = self._get_dropdown_html(res)
        self.assertTrue(len(menu_html) > 0, "Không tìm thấy user dropdown menu")

        # CÁC MỤC GIỮ
        self.assertIn("Hồ sơ &amp; Cài đặt", menu_html)
        self.assertIn("Quản lý Tài khoản", menu_html)
        self.assertIn("Quản lý Mã mời", menu_html)
        self.assertIn("Duyệt kỹ năng", menu_html)
        self.assertIn("Quản lý Bảng tin", menu_html)
        self.assertIn("Chương trình Cộng đồng", menu_html)
        self.assertIn("Quản lý Trường học", menu_html)
        self.assertIn("Báo cáo toàn hệ thống", menu_html)
        self.assertIn("Đăng xuất", menu_html)

        # CÁC MỤC BỎ
        self.assertNotIn("Lịch của tôi", menu_html)
        self.assertNotIn("Ví của tôi", menu_html)
        self.assertNotIn("Đăng kỹ năng mới", menu_html)
        self.assertNotIn("AI gợi ý bạn học", menu_html)
        self.assertNotIn("Báo cáo trường", menu_html)

        # BADGE VAI TRÒ TRÊN PILL
        self.assertIn("user-role-badge", full_html)
        self.assertIn("Tổng quản trị", full_html)
        self.assertNotIn("user-balance-badge", full_html)

if __name__ == "__main__":
    unittest.main()
