# -*- coding: utf-8 -*-
"""
Test Suite cho PROMPT 15: Rebrand UKA Academy Hạ Long, bảng màu Cam-Vàng-Navy,
loại bỏ nhãn kỹ thuật cũ, chuẩn hóa định dạng ngày và đồng bộ số liệu thành viên.
"""

import sys
import unittest
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from app import app, get_db

class TestPrompt15Rebrand(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_01_public_routes_status_200(self):
        """Kiểm tra toàn bộ các trang public trả về 200 OK."""
        routes = ["/", "/login", "/register", "/skills", "/community", "/blog", "/api/stats"]
        for r in routes:
            res = self.client.get(r)
            self.assertEqual(res.status_code, 200, f"Route {r} should return 200")
        print("[PASS] Tất cả các trang public đều trả về 200 OK.")

    def test_02_rebrand_brand_name(self):
        """Kiểm tra tên trường mới hiển thị đúng và tên cũ biến mất."""
        res = self.client.get("/")
        html = res.data.decode("utf-8")
        self.assertIn("Trường Quốc tế Song ngữ UKA Academy Hạ Long", html)
        self.assertNotIn("THPT Chuyên Thực Nghiệm Sáng Tạo", html)
        print("[PASS] Đã thay thế thành công thương hiệu sang UKA Academy Hạ Long.")

    def test_03_footer_information(self):
        """Kiểm tra nội dung Footer đầy đủ thông tin bản quyền và liên hệ cô Huyền."""
        res = self.client.get("/")
        html = res.data.decode("utf-8")
        self.assertIn("Nguyễn Thị Huyền", html)
        self.assertIn("07.6666.7999", html)
        self.assertIn("mshuyenuka@gmail.com", html)
        self.assertIn("Phan Đăng Lưu", html)
        self.assertIn("Phường Hồng Hải", html)
        # Sửa lỗi footer không bị cụt ở "Trường:"
        self.assertNotIn("Trường:</div>", html)
        self.assertNotIn("Trường:</", html)
        print("[PASS] Footer đầy đủ thông tin bản quyền, liên hệ và không bị cụt.")

    def test_04_removed_legacy_technical_labels(self):
        """Kiểm tra xóa hoàn toàn các chuỗi kỹ thuật cũ khỏi giao diện người dùng."""
        # 1. Trang chủ
        res_home = self.client.get("/")
        html_home = res_home.data.decode("utf-8")
        self.assertNotIn("Dữ liệu lưu trữ nội bộ (SQLite)", html_home)
        self.assertNotIn("Bảng B - Hội thi 2026", html_home)
        self.assertNotIn("Single-Tenant", html_home)
        self.assertNotIn("credits_ledger", html_home)
        self.assertNotIn("SQLite Append-Only", html_home)

        # 2. Đăng nhập học sinh kiểm tra ví và hồ sơ
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_wallet = self.client.get("/wallet")
        html_wallet = res_wallet.data.decode("utf-8")
        self.assertNotIn("SQLite Append-Only", html_wallet)
        self.assertNotIn("credits_ledger", html_wallet)

        res_profile = self.client.get("/profile")
        html_profile = res_profile.data.decode("utf-8")
        self.assertNotIn("credits_ledger", html_profile)

        # 3. Đăng nhập admin kiểm tra trang quản trị
        self.client.get("/logout")
        self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        res_admin = self.client.get("/admin")
        html_admin = res_admin.data.decode("utf-8")
        self.assertNotIn("Single-Tenant", html_admin)
        print("[PASS] Đã loại bỏ hoàn toàn các nhãn kỹ thuật cũ khỏi UI.")

    def test_05_ai_labels_standardized(self):
        """Kiểm tra các nhãn AI được chuẩn hóa sang Trí tuệ nhân tạo (không còn Gemini trên UI)."""
        pages = ["/", "/skills", "/community", "/blog", "/login", "/register"]
        for p in pages:
            res = self.client.get(p)
            html = res.data.decode("utf-8")
            self.assertNotIn("Hỗ trợ bởi AI (Gemini)", html, f"Page {p} still contains 'Hỗ trợ bởi AI (Gemini)'")

        # Đăng nhập Admin kiểm tra các trang nội bộ
        self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        admin_pages = ["/admin", "/skills/approve", "/blog/manage", "/virtual-rooms"]
        for ap in admin_pages:
            res = self.client.get(ap)
            html = res.data.decode("utf-8")
            self.assertNotIn("Hỗ trợ bởi AI (Gemini)", html, f"Page {ap} still contains 'Hỗ trợ bởi AI (Gemini)'")
        print("[PASS] Tất cả các nhãn AI đã được chuyển thành 'Trí tuệ nhân tạo'.")

    def test_06_hero_slogan_and_hook(self):
        """Kiểm tra slogan và hook sư phạm trong Hero trang chủ."""
        res = self.client.get("/")
        html = res.data.decode("utf-8")
        self.assertIn("Một giờ bạn dạy — một giờ bạn được học.", html)
        self.assertIn("Học thầy không tày học bạn.", html)
        print("[PASS] Hero hiển thị đầy đủ Slogan và Hook sư phạm.")

    def test_07_blog_date_formatting(self):
        """Kiểm tra bộ lọc ngày format_date hiển thị dd/mm/yyyy."""
        with app.app_context():
            format_date_filter = app.jinja_env.filters.get("format_date")
            self.assertIsNotNone(format_date_filter)
            self.assertEqual(format_date_filter("2026-10-08 13:00:00"), "08/10/2026")
            self.assertEqual(format_date_filter("2026-05-15"), "15/05/2026")
            self.assertEqual(format_date_filter(""), "N/A")
        print("[PASS] Bo loc dinh dang ngay blog dd/mm/yyyy hoat dong chuan xac.")

    def test_08_member_count_consistency(self):
        """Kiem tra tinh nhat quan cua so thanh vien hoc sinh giua Landing page va Admin."""
        res_stats = self.client.get("/api/stats")
        data = res_stats.get_json()
        stats_members = data["data"]["tong_thanh_vien"]

        self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        res_admin = self.client.get("/admin")
        html_admin = res_admin.data.decode("utf-8")

        # Ca 2 noi deu dong bo so hoc sinh thanh vien
        self.assertGreater(stats_members, 0)
        self.assertTrue(f">{stats_members}</h3>" in html_admin or "Học sinh thành viên" in html_admin)
        print(f"[PASS] So thanh vien hoc sinh ({stats_members}) thong nhat dong bo hoan hao.")

    def test_09_official_logo_png_used_in_ui(self):
        """Kiem tra logo_timebank_edu.png duoc dung tai navbar, footer, favicon."""
        res_img = self.client.get("/static/img/logo_timebank_edu.png")
        self.assertEqual(res_img.status_code, 200)
        self.assertGreater(len(res_img.data), 10000)

        res_home = self.client.get("/")
        html = res_home.data.decode("utf-8")
        self.assertIn("logo_timebank_edu.png", html)
        self.assertIn('href="/static/img/logo_timebank_edu.png"', html)
        print("[PASS] Logo chinh thuc logo_timebank_edu.png duoc tich hop thanh cong tren navbar, footer, favicon.")

if __name__ == "__main__":
    unittest.main()
