# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHUYÊN SÂU — PROMPT 21:
POLISH GIAO DIỆN (Menu vuông bo tròn + Nút bấm + Chữ nghĩa)

Tiêu chí nghiệm thu:
1. Menu vuông hiển thị đúng 7 nút + active state xanh đúng trang.
2. Tìm "sổ cái" (không phân biệt hoa thường) trong toàn bộ templates: kết quả = 0.
3. Nút Đăng nhập/Đăng ký kiểu mới, responsive mobile OK.
4. Các dòng chữ yêu cầu đúng nội dung, đúng 1 hàng (text-nowrap).
5. Regression: đăng nhập, các trang chính 200, không vỡ layout cũ.
"""

import unittest
import os
import re
from pathlib import Path
from app import app, DATABASE_PATH

class TestPrompt21UIPolish(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        cls.client = app.test_client()
        cls.templates_dir = Path(__file__).resolve().parent / "templates"

    def test_01_squircle_navigation_7_buttons_and_active_states(self):
        """
        TIÊU CHÍ 1: Menu vuông bo tròn squircle hiển thị đủ 7 nút
        (Trang chủ, Chợ kỹ năng, Sàn cộng đồng, Diễn đàn, Kho tài liệu, Bản tin, Nội quy)
        và active state xanh chuẩn xác theo từng trang.
        """
        # Đăng nhập để kiểm tra được cả các trang yêu cầu login
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)

        test_pages = [
            ("/", "Trang chủ", "bi-house-fill"),
            ("/skills", "Chợ kỹ năng", "bi-shop"),
            ("/community-market", "Sàn cộng đồng", "bi-globe2"),
            ("/forum", "Diễn đàn", "bi-chat-dots-fill"),
            ("/documents", "Kho tài liệu", "bi-folder2-open"),
            ("/blog", "Bản tin", "bi-newspaper"),
            ("/noi-quy", "Nội quy", "bi-shield-check")
        ]

        expected_labels = [
            "Trang chủ", "Chợ kỹ năng", "Sàn cộng đồng",
            "Diễn đàn", "Kho tài liệu", "Bản tin", "Nội quy"
        ]

        for path, active_label, active_icon in test_pages:
            res = self.client.get(path, follow_redirects=True)
            self.assertEqual(res.status_code, 200, f"Trang {path} phải trả về 200")
            html = res.data.decode("utf-8")

            # 1. Kiểm tra tồn tại nav-squircle-bar
            self.assertIn("nav-squircle-bar", html, f"Thanh squircle bar phải tồn tại trên trang {path}")

            # 2. Đếm số lượng nút nav-squircle
            squircle_matches = re.findall(r'class="nav-squircle\s+([^"]+)"', html)
            self.assertEqual(len(squircle_matches), 7, f"Thanh menu phải có đúng 7 nút vuông trên trang {path}")

            # 3. Kiểm tra đủ 7 nhãn nút
            for exp_lbl in expected_labels:
                self.assertIn(f"<span>{exp_lbl}</span>", html, f"Nút {exp_lbl} phải có trong menu trang {path}")

            # 4. Kiểm tra nút active
            active_btn_pattern = re.compile(
                r'<a\s+[^>]*class="nav-squircle\s+active"[^>]*>[\s\S]*?<i\s+class="bi\s+([^"]+)"[\s\S]*?<span>([^<]+)</span>',
                re.IGNORECASE
            )
            m = active_btn_pattern.search(html)
            self.assertIsNotNone(m, f"Phải tìm thấy nút nav-squircle active trên trang {path}")
            icon_found, label_found = m.group(1).strip(), m.group(2).strip()
            self.assertEqual(label_found, active_label, f"Trang {path} phải active nút '{active_label}', nhưng lại là '{label_found}'")
            self.assertEqual(icon_found, active_icon, f"Trang {path} nút active phải có icon '{active_icon}'")

    def test_02_zero_occurrences_of_so_cai_in_all_templates(self):
        """
        TIÊU CHÍ 2: Tìm "sổ cái" (không phân biệt hoa thường) trong toàn bộ templates: kết quả = 0.
        """
        html_files = list(self.templates_dir.rglob("*.html"))
        self.assertGreater(len(html_files), 0, "Phải tìm thấy các file template html")

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

    def test_03_redesigned_login_and_register_buttons_and_mobile_responsive(self):
        """
        TIÊU CHÍ 3: Nút Đăng nhập / Đăng ký kiểu mới tương phản rõ rệt, responsive mobile OK.
        """
        anon_client = app.test_client()
        res = anon_client.get("/")
        html = res.data.decode("utf-8")

        # Nút Đăng nhập viền & Đăng ký nền đậm
        self.assertIn("btn-auth-login", html, "Phải có class .btn-auth-login cho nút Đăng nhập")
        self.assertIn("btn-auth-register", html, "Phải có class .btn-auth-register cho nút Đăng ký")
        self.assertIn("Đăng nhập", html)
        self.assertIn("Đăng ký", html)

        # Kiểm tra container squircle có class hỗ trợ cuộn ngang trên mobile
        self.assertIn("nav-squircle-wrapper", html, "Phải có .nav-squircle-wrapper hỗ trợ cuộn ngang trên mobile")

    def test_04_copywriting_and_one_line_constraints(self):
        """
        TIÊU CHÍ 4:
        - "Lan tỏa trách nhiệm xã hội cùng TimeBank EDU": thu nhỏ, ép 1 hàng (text-nowrap).
        - Section nhân rộng: "Chuyển giao và cài đặt dữ liệu cho các trường chỉ 5 phút"
        - "Dễ dàng tùy chỉnh logo, màu sắc và thông điệp riêng để biến hệ thống thành phiên bản độc quyền của trường bạn."
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # 1. Kiểm tra tiêu đề Lan tỏa trách nhiệm xã hội ép 1 hàng
        self.assertIn("Lan tỏa trách nhiệm xã hội cùng TimeBank EDU", html)
        self.assertIn("text-nowrap", html, "Tiêu đề 'Lan tỏa trách nhiệm xã hội...' phải có class 'text-nowrap'")

        # 2. Section nhân rộng
        self.assertIn("Chuyển giao và cài đặt dữ liệu cho các trường chỉ 5 phút", html)
        self.assertIn("Dễ dàng tùy chỉnh logo, màu sắc và thông điệp riêng để biến hệ thống thành phiên bản độc quyền của trường bạn.", html)

        # 3. Đảm bảo câu cũ đã biến mất
        self.assertNotIn("Đổi thương hiệu chỉ trong 5 phút", html)
        self.assertNotIn("Chỉ cần chỉnh sửa tệp config.yaml là có ngay hệ thống mang logo", html)

    def test_05_regression_key_pages_status_200(self):
        """
        TIÊU CHÍ 5: Đăng nhập & các trang chính trả về 200 OK, dropdown avatar đầy đủ 3 mục cá nhân.
        """
        login_res = self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        pages = ["/", "/skills", "/community-market", "/noi-quy", "/forum", "/documents", "/blog", "/wallet", "/profile", "/my-schedule"]
        for p in pages:
            r = self.client.get(p)
            self.assertEqual(r.status_code, 200, f"Trang {p} phải trả về status 200")

        # Kiểm tra dropdown avatar tài khoản chứa: Lịch của tôi, Ví của tôi, Hồ sơ cá nhân
        prof_html = self.client.get("/profile").data.decode("utf-8")
        self.assertIn("Ví của tôi", prof_html)
        self.assertIn("Lịch của tôi", prof_html)
        self.assertIn("Hồ sơ cá nhân", prof_html)

if __name__ == "__main__":
    unittest.main()
