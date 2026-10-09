# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHUYÊN SÂU — PROMPT 21:
ĐẠI TU GIAO DIỆN TRANG CHỦ THEO REVIEW UX

Tiêu chí nghiệm thu chuẩn Prompt 21:
1. Không còn dòng badge "Sáng kiến Giáo dục Số 2026 / Nền tảng Đa trường Học đường".
2. Tiêu đề căn giữa + Banner chạy chữ hoạt động, đúng nội dung, dừng khi hover.
3. Menu 5 dropdown hoạt động, đủ 11 mục cũ, không mất mục nào; 2 nút Đăng nhập/Đăng ký pill 38px.
4. Tìm "sổ cái" trong templates = 0 kết quả.
5. Quy trình 4 bước có mũi tên nối; Sơ đồ tròn An-Bình-Chi hiển thị đúng vòng khép kín.
6. Chất liệu con người thật: avatar tròn chữ cái đầu tên, thẻ nhiệm vụ có ảnh/placeholder, thẻ trường có logo/tên trường.
7. Mobile responsive, copywriting chuẩn và regression các luồng chính status 200.
"""

import unittest
import os
import re
from pathlib import Path
from app import app, DATABASE_PATH, init_db

class TestPrompt21UIPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        cls.templates_dir = Path(__file__).resolve().parent / "templates"
        cls.static_dir = Path(__file__).resolve().parent / "static"
        init_db()

    def test_01_no_badge_sang_kien_giao_duc_so_2026(self):
        """
        NGHIỆM THU 1: XÓA HẲN dòng badge 'Sáng kiến Giáo dục Số 2026 / Nền tảng Đa trường Học đường'.
        Đảm bảo không còn tồn tại trong bất kỳ template nào.
        """
        html_files = list(self.templates_dir.rglob("*.html"))
        violations = []
        for f in html_files:
            content = f.read_text(encoding="utf-8", errors="replace")
            if "Sáng kiến Giáo dục Số 2026" in content:
                violations.append(f"{f.name}: chứa badge 'Sáng kiến Giáo dục Số 2026'")
        self.assertEqual(len(violations), 0, f"Vẫn còn badge 'Sáng kiến Giáo dục Số 2026':\n" + "\n".join(violations))

        # Kiểm tra trên HTML trang chủ
        res = self.client.get("/")
        html = res.data.decode("utf-8")
        self.assertNotIn("Sáng kiến Giáo dục Số 2026", html)
        self.assertNotIn("Nền tảng Đa trường Học đường", html)

    def test_02_centered_title_and_marquee_banner(self):
        """
        NGHIỆM THU 2:
        - Tiêu đề 'School Time Bank' căn GIỮA trang + dòng nghiêng 'Ngân hàng Thời gian Học đường' bên dưới.
        - Banner chạy chữ từ phải sang trái ngay dưới tiêu đề:
          'Chào mừng bạn đã đến với công cụ giáo dục TIME BANK EDU'
          (CSS marquee thuần, tốc độ vừa phải, dừng khi hover).
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # 1. Tiêu đề căn giữa
        self.assertIn("hero-center-title", html, "Phải có class hero-center-title cho tiêu đề căn giữa")
        self.assertIn("hero-center-subtitle", html, "Phải có class hero-center-subtitle cho dòng chữ nghiêng")
        self.assertIn("School Time Bank", html)
        self.assertIn("Ngân hàng Thời gian Học đường", html)

        # 2. Banner marquee chạy chữ
        self.assertIn("marquee-banner-wrapper", html)
        self.assertIn("marquee-banner-track", html)
        self.assertIn("Chào mừng bạn đã đến với công cụ giáo dục TIME BANK EDU", html)

        # 3. Kiểm tra CSS marquee trong style.css: dừng khi hover
        css_file = self.static_dir / "css" / "style.css"
        css_content = css_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("marqueeAnimation", css_content, "Phải có keyframe marqueeAnimation")
        self.assertIn("animation-play-state: paused", css_content, "CSS marquee phải dừng khi hover (:hover { animation-play-state: paused; })")

    def test_03_dropdown_navbar_5_groups_11_items_and_pill_auth_buttons(self):
        """
        NGHIỆM THU 3:
        - Menu 5 nhóm dropdown: Mô hình, Hoạt động, Tài nguyên, Vinh danh, Dành cho Nhà trường.
        - Đủ 11 mục cũ: Mô hình hoạt động, Quy trình 4 bước, Số liệu vận hành,
          Chợ kỹ năng, Sàn cộng đồng, Vì cộng đồng, Diễn đàn,
          Nội quy, Kho tài liệu, Bản tin, Vinh danh.
        - 2 nút Đăng nhập/Đăng ký: cùng bo góc pill, cùng chiều cao 38px;
          Đăng nhập = nút viền ghost, Đăng ký = nền đặc cam.
        - Header nền trắng.
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # 1. 5 nhóm dropdown
        self.assertIn("Mô hình", html)
        self.assertIn("Hoạt động", html)
        self.assertIn("Tài nguyên", html)
        self.assertIn("Vinh danh", html)
        self.assertIn("Dành cho Nhà trường", html)

        # 2. Đủ 11 mục cũ
        old_11_items = [
            "Mô hình hoạt động",
            "Quy trình 4 bước",
            "Số liệu vận hành",
            "Chợ kỹ năng",
            "Sàn cộng đồng",
            "Vì cộng đồng",
            "Diễn đàn",
            "Nội quy",
            "Kho tài liệu",
            "Bản tin",
            "Bảng vàng thành tích"  # Vinh danh
        ]
        for item in old_11_items:
            self.assertIn(item, html, f"Menu phải chứa mục: '{item}'")

        # 3. 2 nút Đăng nhập / Đăng ký: cùng bo góc pill, viền ghost / solid cam
        self.assertIn("btn-auth-ghost", html, "Phải có nút Đăng nhập viền ghost")
        self.assertIn("btn-auth-solid", html, "Phải có nút Đăng ký nền đặc")

        # Kiểm tra CSS của 2 nút: pill (border-radius: 50px) và height: 38px
        css_file = self.static_dir / "css" / "style.css"
        css_content = css_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn("btn-auth-ghost", css_content)
        self.assertIn("btn-auth-solid", css_content)
        self.assertIn("38px", css_content, "Hai nút auth phải có cùng chiều cao 38px")

    def test_04_zero_occurrences_of_so_cai_in_all_templates(self):
        """
        NGHIỆM THU 4: Tìm 'sổ cái' (không phân biệt hoa thường) trong toàn bộ templates: kết quả = 0.
        """
        html_files = list(self.templates_dir.rglob("*.html"))
        violations = []
        pattern = re.compile(r"sổ\s+cái", re.IGNORECASE)

        for f in html_files:
            content = f.read_text(encoding="utf-8", errors="replace")
            matches = pattern.findall(content)
            if matches:
                lines = content.splitlines()
                for idx, line in enumerate(lines, 1):
                    if pattern.search(line):
                        violations.append(f"{f.name}:{idx} -> {line.strip()}")

        self.assertEqual(
            len(violations), 0,
            f"Vẫn còn 'sổ cái' trong templates (yêu cầu kết quả = 0):\n" + "\n".join(violations)
        )

    def test_05_steps_and_circular_closed_loop_diagram(self):
        """
        NGHIỆM THU 5:
        - Quy trình 4 bước: thêm mũi tên/đường nối 1->2->3->4, số thứ tự tăng độ đậm (fw-bolder).
        - Sơ đồ tròn An-Bình-Chi: hiển thị đúng vòng khép kín An -> Bình -> Chi -> An (SVG thuần).
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # Quy trình 4 bước
        self.assertIn("step-connector-arrow", html, "Phải có mũi tên nối giữa các bước")
        self.assertIn("fw-bolder", html, "Số thứ tự bước phải có class fw-bolder")

        # Sơ đồ tròn SVG
        self.assertIn("circular-flow-svg", html, "Phải có sơ đồ tròn circular-flow-svg")
        self.assertIn("An (12A1)", html)
        self.assertIn("Bình (11B2)", html)
        self.assertIn("Chi (10A3)", html)
        self.assertIn("arrow-orange", html)
        self.assertIn("arrow-green", html)
        self.assertIn("arrow-blue", html)
        self.assertIn("An → Bình → Chi → An", html, "Phải có dòng chú thích vòng lặp khép kín An → Bình → Chi → An")

    def test_06_human_materials_genuine_avatars_and_cards(self):
        """
        NGHIỆM THU 6: 'Chất liệu con người' (trung thực, không bịa ảnh):
        - Vinh danh: avatar tròn = chữ cái đầu tên học sinh trên nền màu (avatar-initial-circle).
        - Thẻ nhiệm vụ cộng đồng: khung ảnh bìa + placeholder trang nhã.
        - Thẻ trường liên kết: khung logo trường / tên trường.
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # 1. Avatar tròn chữ cái đầu
        self.assertIn("avatar-initial-circle", html, "Phải có avatar-initial-circle tạo avatar từ chữ cái đầu")

        # 2. Thẻ nhiệm vụ cộng đồng: khung ảnh bìa / placeholder
        self.assertIn("task-cover-container", html, "Phải có task-cover-container cho thẻ nhiệm vụ")

        # 3. Thẻ trường: khung logo
        self.assertIn("school-logo-frame", html, "Phải có school-logo-frame cho thẻ trường liên kết")

    def test_07_regression_and_copywriting(self):
        """
        NGHIỆM THU 7:
        - 'Lan tỏa trách nhiệm xã hội cùng TimeBank EDU': thu nhỏ, 1 hàng (text-nowrap).
        - 'Chuyển giao và cài đặt dữ liệu cho các trường chỉ 5 phút'.
        - 'Dễ dàng tùy chỉnh logo, màu sắc và thông điệp riêng để biến hệ thống thành phiên bản độc quyền của trường bạn.'
        - Regression các luồng chính status 200.
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # 1. Chữ nghĩa chuẩn
        self.assertIn("Lan tỏa trách nhiệm xã hội cùng TimeBank EDU", html)
        self.assertIn("text-nowrap", html)
        self.assertIn("Chuyển giao và cài đặt dữ liệu cho các trường chỉ 5 phút", html)
        self.assertIn("Dễ dàng tùy chỉnh logo, màu sắc và thông điệp riêng để biến hệ thống thành phiên bản độc quyền của trường bạn.", html)
        self.assertNotIn("Đổi thương hiệu chỉ trong 5 phút", html)

        # 2. Regression các route chính
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        routes = ["/", "/skills", "/community-market", "/forum", "/documents", "/blog", "/noi-quy", "/profile", "/wallet", "/my-schedule"]
        for route in routes:
            r = self.client.get(route)
            self.assertEqual(r.status_code, 200, f"Route {route} phải trả về 200 OK")

if __name__ == "__main__":
    unittest.main()
