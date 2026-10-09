# -*- coding: utf-8 -*-
import unittest
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, init_db, get_db

class TestPrompt25ResponsiveHeader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

    def setUp(self):
        self.client = app.test_client()

    def test_base_html_responsive_markup(self):
        """Kiểm tra file base.html có đầy đủ markup và class responsive cho navbar."""
        base_path = os.path.join(os.path.dirname(__file__), "templates", "base.html")
        with open(base_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Navbar container & classes
        self.assertIn("navbar-custom", content)
        self.assertIn("navbar-toggler", content)
        self.assertIn("mainNavbar", content)
        self.assertIn("brand-logo-img", content)
        self.assertIn("brand-title-text", content)
        self.assertIn("brand-sub-text", content)

        # 2. User pill classes
        self.assertIn("user-pill", content)
        self.assertIn("user-display-name", content)
        self.assertIn("text-truncate", content)
        self.assertIn("user-avatar-badge", content)
        self.assertIn("user-balance-badge", content)
        self.assertIn("flex-shrink-0", content)
        self.assertIn("user-pill-container", content)

        # 3. Auth buttons classes
        self.assertIn("nav-auth-buttons", content)
        self.assertIn("btn-auth-ghost", content)
        self.assertIn("btn-auth-solid", content)

    def test_style_css_responsive_rules(self):
        """Kiểm tra style.css có đầy đủ CSS rules cho responsive header, hamburger, và laptop scaling."""
        css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # 1. Global overflow-x hidden
        self.assertIn("overflow-x: hidden", css)
        self.assertIn("max-width: 100vw", css)

        # 2. Mobile / Tablet breakpoint < 1024px (Hamburger button)
        self.assertIn("@media (max-width: 1023.98px)", css)
        self.assertIn(".navbar-custom .navbar-toggler", css)
        self.assertIn(".navbar-custom .navbar-collapse:not(.show):not(.collapsing)", css)
        self.assertIn(".navbar-custom .navbar-collapse.show", css)

        # 3. Desktop breakpoint >= 1024px
        self.assertIn("@media (min-width: 1024px)", css)
        self.assertIn("flex-wrap: wrap", css)

        # 4. Small laptop scaling (1024px - 1399px, đặc biệt 1280px & 1366px)
        self.assertIn("@media (min-width: 1024px) and (max-width: 1399.98px)", css)
        self.assertIn(".brand-sub-text", css)
        self.assertIn("display: none !important", css)
        self.assertIn(".user-display-name", css)
        self.assertIn("max-width: 90px !important", css)

        # 5. Desktop >= 1400px (1440px+) preserves original layout
        self.assertIn("@media (min-width: 1400px)", css)
        self.assertIn("max-width: 140px", css)

        # 6. Mobile <= 576px (375px) logo & name scaling
        self.assertIn("@media (max-width: 576px)", css)

    def test_render_unauthenticated_navbar(self):
        """Kiểm tra trang chủ render đúng với khách chưa đăng nhập."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn("School Time Bank", html)
        self.assertIn("nav-auth-buttons", html)
        self.assertIn("Đăng nhập", html)
        self.assertIn("Đăng ký", html)

    def test_render_authenticated_navbar_compact_user(self):
        """Kiểm tra người dùng đăng nhập có đầy đủ avatar, tên thu gọn, và badge số dư giờ."""
        # Đăng nhập bằng tài khoản demo_hocsinh
        res_login = self.client.post("/login", data={
            "ma_hoc_sinh": "demo_hocsinh",
            "mat_khau": "demo123"
        }, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)

        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn("user-pill", html)
        self.assertIn("user-display-name", html)
        self.assertIn("user-balance-badge", html)
        self.assertIn("user-avatar-badge", html)

if __name__ == "__main__":
    unittest.main()
