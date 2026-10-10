# -*- coding: utf-8 -*-
"""
Test Suite cho PROMPT 31: Chỉnh từ ngữ + Phối màu giao diện
- VIỆC 1: Sửa từ ngữ toàn site ("GIAN HÀNG" -> "TRƯỜNG HỌC", "phòng học JaaS WebRTC" -> "lớp học ảo")
- VIỆC 2: Sửa dấu ngoặc kép chuẩn tiếng Việt (mở “ và đóng ”)
- VIỆC 3: Phối màu hiện đại (Menu ngang phân tách nền, 4 thẻ mô hình pastel, 4 thẻ chỉ số gradient nổi bật)
"""
import unittest
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, init_db, get_db

class TestPrompt31UIWordingAndColor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()

    def test_01_no_forbidden_wording_in_rendered_public_pages(self):
        """Kiểm tra các trang công khai không còn từ 'Gian hàng', 'JaaS', 'WebRTC' ở text hiển thị."""
        public_urls = ["/", "/login", "/register", "/noi-quy", "/skills"]
        for url in public_urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"URL {url} failed with {res.status_code}")
            html = res.data.decode("utf-8")
            
            # Không được chứa 'gian hàng' (không phân biệt hoa thường) ở user-facing
            self.assertNotIn("GIAN HÀNG", html, f"URL {url} vẫn chứa 'GIAN HÀNG'")
            self.assertNotIn("Gian hàng", html, f"URL {url} vẫn chứa 'Gian hàng'")
            self.assertNotIn("gian hàng", html, f"URL {url} vẫn chứa 'gian hàng'")
            
            # Không được chứa JaaS hay WebRTC ở giao diện
            self.assertNotIn("JaaS", html, f"URL {url} vẫn chứa 'JaaS'")
            self.assertNotIn("WebRTC", html, f"URL {url} vẫn chứa 'WebRTC'")

    def test_02_new_wording_on_homepage(self):
        """Kiểm tra các cụm từ mới chuẩn hóa trên trang chủ."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Hệ thống đa trường học
        self.assertIn("HỆ THỐNG ĐA TRƯỜNG HỌC", html)
        self.assertIn("Trường #1", html)

        # Trải nghiệm lớp học ảo hiện đại
        self.assertIn("Trải nghiệm lớp học ảo hiện đại", html)

    def test_03_vietnamese_quotation_marks(self):
        """Kiểm tra câu khẩu hiệu dùng dấu ngoặc kép tiếng Việt chuẩn (mở “ và đóng ”)."""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Dấu ngoặc kép chuẩn tiếng Việt
        self.assertIn("“Một giờ bạn dạy — một giờ bạn được học.”", html)
        # Đảm bảo không còn 2 icon bi-quote đóng bao quanh
        self.assertNotIn('bi-quote fs-4 text-warning"></i> Một giờ bạn dạy', html)

    def test_04_admin_and_register_wording(self):
        """Kiểm tra tiêu đề quản trị và trang đăng ký đã đổi sang Đa trường học."""
        # 1. Đăng ký
        res_reg = self.client.get("/register")
        self.assertIn("Hệ thống Đa trường học — School Time Bank", res_reg.data.decode("utf-8"))

        # 2. Đăng nhập admin và kiểm tra trang admin
        self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        admin_html = res_admin.data.decode("utf-8")
        self.assertIn("Hệ thống Quản trị Đa trường học", admin_html)
        self.assertNotIn("Hệ thống Quản trị Gian hàng Đa trường", admin_html)

    def test_05_virtual_room_template_wording(self):
        """Kiểm tra template virtual_room.html không chứa JaaS hay WebRTC ở giao diện người dùng."""
        vr_path = os.path.join(os.path.dirname(__file__), "templates", "virtual_room.html")
        with open(vr_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Kiểm tra tiêu đề giao diện
        self.assertIn("Lớp Học Ảo Trực Tuyến Chưa Được Cấu Hình", content)
        self.assertNotIn("Phòng Học Trực Tuyến JaaS (8x8) Chưa Được Cấu Hình", content)

        # Kiểm tra nhãn trạng thái lớp học
        self.assertIn("Lớp học ảo trực tuyến: <code>{{ room_name }}</code>", content)
        self.assertNotIn("Phòng học trực tuyến JaaS: <code>{{ room_name }}</code>", content)

        # Kiểm tra thông báo loading
        self.assertIn('showLoading("Đang Kết Nối Lớp Học Ảo..."', content)
        self.assertNotIn('showLoading("Đang Kết Nối Phòng Học JaaS', content)

    def test_06_modern_navbar_menu_styling(self):
        """Kiểm tra CSS menu ngang có nền màu phân tách từng mục, tông cam-vàng chủ đạo."""
        css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        # Navbar có nền cam kem ấm nhẹ và menu links có nền phân tách
        self.assertIn(".navbar-custom", css)
        self.assertTrue("#FFF8F1" in css or "#FFFDFB" in css)
        self.assertIn(".navbar-custom .nav-link", css)
        self.assertTrue("background-color: #FFFFFF" in css or "background-color: #F8FAFC" in css)
        self.assertTrue("border: 1px solid #FED7AA" in css or "border: 1px solid #E2E8F0" in css)

        # Hover & Active giữ tông cam-vàng chủ đạo
        self.assertIn("background-color: #FFF7ED", css)
        self.assertIn("linear-gradient(135deg, #F26522 0%, #F59E0B 100%)", css)

    def test_07_four_step_cards_distinct_pastel_backgrounds(self):
        """Kiểm tra 4 thẻ mô hình hoạt động có 4 màu nền nhẹ pastel khác nhau."""
        # 1. Markup trong index.html
        index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()

        self.assertIn("step-card-1", index_html)
        self.assertIn("step-card-2", index_html)
        self.assertIn("step-card-3", index_html)
        self.assertIn("step-card-4", index_html)

        # 2. CSS trong style.css
        css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".step-card.step-card-1", css)
        self.assertIn(".step-card.step-card-2", css)
        self.assertIn(".step-card.step-card-3", css)
        self.assertIn(".step-card.step-card-4", css)

        # Đảm bảo 4 mã màu pastel khác nhau
        self.assertIn("#FFF7ED", css)  # Thẻ 1: Cam ấm pastel
        self.assertIn("#FAF5FF", css)  # Thẻ 2: Tím AI pastel
        self.assertIn("#F0F9FF", css)  # Thẻ 3: Xanh dương pastel
        self.assertIn("#F0FDF4", css)  # Thẻ 4: Xanh lá pastel

    def test_08_four_stats_gradient_modern_cards(self):
        """Kiểm tra 4 chỉ số vận hành có nền gradient hiện đại và số liệu nổi bật."""
        # 1. Markup trong index.html
        index_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
        with open(index_path, "r", encoding="utf-8") as f:
            index_html = f.read()

        self.assertIn("stat-card-1", index_html)
        self.assertIn("stat-card-2", index_html)
        self.assertIn("stat-card-3", index_html)
        self.assertIn("stat-card-4", index_html)

        # 2. CSS trong style.css
        css_path = os.path.join(os.path.dirname(__file__), "static", "css", "style.css")
        with open(css_path, "r", encoding="utf-8") as f:
            css = f.read()

        self.assertIn(".stat-card.stat-card-1", css)
        self.assertIn(".stat-card.stat-card-2", css)
        self.assertIn(".stat-card.stat-card-3", css)
        self.assertIn(".stat-card.stat-card-4", css)

        # Kiểm tra các gradient của 4 thẻ chỉ số
        self.assertIn("linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%)", css)  # Thẻ 1: Sky / Blue
        self.assertIn("linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%)", css)  # Thẻ 2: Mint / Green
        self.assertIn("linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%)", css)  # Thẻ 3: Amber / Orange
        self.assertIn("linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%)", css)  # Thẻ 4: Purple / Indigo

        # Số liệu to nổi bật
        self.assertIn("font-size: 2.75rem", css)
        self.assertIn("font-weight: 800", css)

if __name__ == "__main__":
    unittest.main()
