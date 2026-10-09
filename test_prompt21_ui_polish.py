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
from app import app, DATABASE_PATH, init_db, get_db

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

    def test_08_prompt21_plus_author_footer_exact_3_lines(self):
        """
        NGHIỆM THU PROMPT 21+ (Ý 12):
        Footer tác giả thay bằng đúng 3 dòng:
        1: 'Tác giả sáng kiến & Thiết kế hệ sinh thái số:'
        2: 'Cô giáo Nguyễn Thị Huyền — Giáo viên Tin học, Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy'
        3: 'Bản quyền toàn vẹn về mô hình sư phạm và giải pháp kiến trúc công nghệ School Time Bank.'
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        line1 = "Tác giả sáng kiến & Thiết kế hệ sinh thái số:"
        line2 = "Cô giáo Nguyễn Thị Huyền — Giáo viên Tin học, Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy"
        line3 = "Bản quyền toàn vẹn về mô hình sư phạm và giải pháp kiến trúc công nghệ School Time Bank."

        self.assertIn(line1, html, "Footer thiếu dòng 1 thông tin tác giả")
        self.assertIn(line2, html, "Footer thiếu dòng 2 thông tin cô giáo Huyền")
        self.assertIn(line3, html, "Footer thiếu dòng 3 bản quyền mô hình")

    def test_09_prompt21_plus_tagline_no_extra_duong(self):
        """
        NGHIỆM THU PROMPT 21+ (Ý 13):
        Tagline: 'Mô hình giáo dục sáng tạo đa trường học đường:' ->
        'Mô hình giáo dục sáng tạo đa trường học. Mỗi học sinh vừa là người học,
        vừa là người thầy. Không dùng tiền mặt, mọi tri thức đều được trân trọng
        công bằng thông qua tín dụng thời gian.'
        Tuyệt đối không còn cụm 'đa trường học đường:'
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        expected_tagline = (
            "Mô hình giáo dục sáng tạo đa trường học. Mỗi học sinh vừa là người học, "
            "vừa là người thầy. Không dùng tiền mặt, mọi tri thức đều được trân trọng "
            "công bằng thông qua tín dụng thời gian."
        )
        self.assertIn("Mô hình giáo dục sáng tạo đa trường học. Mỗi học sinh vừa là người học", html)
        self.assertNotIn("đa trường học đường:", html)
        self.assertNotIn("học đường: Mỗi học sinh", html)

    def test_10_prompt21_plus_virtual_classroom_section(self):
        """
        NGHIỆM THU PROMPT 21+ (Ý 14):
        Thêm section 'Lớp học ảo' nổi bật (sau hero, trước quy trình 4 bước):
        - học ngay trên trình duyệt không cần cài app;
        - không giới hạn thời lượng buổi học;
        - đăng ký 1 lần tham gia mọi buổi;
        - hình ảnh rõ nét + đầy đủ chức năng sư phạm (điểm danh tự động, dàn ý AI, quiz, nút báo cáo).
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")

        # Kiểm tra thứ tự: Hero -> Lớp học ảo -> Quy trình 4 bước
        hero_pos = html.find('class="hero-section"')
        virtual_pos = html.find('id="lop-hoc-ao"')
        steps_pos = html.find('id="mo-hinh"')

        self.assertGreater(virtual_pos, -1, "Phải có section lop-hoc-ao")
        self.assertGreater(virtual_pos, hero_pos, "Section lớp học ảo phải đặt sau hero-section")
        self.assertGreater(steps_pos, virtual_pos, "Section lớp học ảo phải đặt trước quy trình 4 bước (mo-hinh)")

        # Kiểm tra đủ 4 ý sư phạm cốt lõi
        self.assertIn("Học ngay trên trình duyệt", html)
        self.assertIn("Không cần cài app", html)

        self.assertIn("Không giới hạn thời lượng", html)

        self.assertIn("Đăng ký 1 lần tham gia", html)
        self.assertIn("Tham gia mọi buổi", html)

        self.assertIn("Đầy đủ chức năng sư phạm", html)
        self.assertIn("Hình ảnh rõ nét", html)
        self.assertIn("điểm danh tự động", html)
        self.assertIn("dàn ý AI", html)
        self.assertIn("quiz", html)
        self.assertIn("nút báo cáo", html)

    def test_11_prompt21_plus_marquee_banner_with_dot_and_gradient(self):
        """
        NGHIỆM THU PROMPT 21+ (Ý 3, 15):
        - Banner chạy chữ: 'Chào mừng bạn đã đến với công cụ giáo dục TIME BANK EDU.' (có dấu chấm)
        - CSS: gradient giáo dục, chữ đọc rõ nét
        """
        res = self.client.get("/")
        html = res.data.decode("utf-8")
        self.assertIn("Chào mừng bạn đã đến với công cụ giáo dục TIME BANK EDU.", html)

        css_file = self.static_dir / "css" / "style.css"
        css_content = css_file.read_text(encoding="utf-8", errors="replace")
        self.assertIn(".marquee-banner-wrapper", css_content)
        self.assertIn("linear-gradient", css_content)

    def test_12_prompt21_plus_consultation_form_db_and_smtp(self):
        """
        NGHIỆM THU PROMPT 21+ (Ý 16):
        Form 'Đăng ký tư vấn triển khai':
        - Lưu DB vào bảng tu_van_trien_khai
        - Gửi email thông báo về mshuyenuka@gmail.com
        - Thiếu biến môi trường SMTP -> chỉ lưu DB, ghi log warning, không crash!
        """
        import sqlite3
        from unittest.mock import patch, MagicMock

        # 1. Test submit khi KHÔNG có cấu hình SMTP (thiếu biến môi trường)
        # Đảm bảo lưu DB thành công, trả về 200/redirect, không 500 crash
        smtp_keys = ["SMTP_HOST", "SMTP_PORT", "SMTP_USER", "SMTP_PASS"]
        old_smtp_vals = {k: os.environ.get(k) for k in smtp_keys}
        for k in smtp_keys:
            os.environ.pop(k, None)

        try:
            payload = {
                "ten_truong": "THPT Chuyên Hạ Long",
                "ho_ten": "Thầy Trần Văn Nam",
                "sdt": "0912345678",
                "email": "namtv@halong.edu.vn",
                "ghi_chu": "Mong muốn thí điểm mô hình cho 2 khối 10 và 11"
            }
            res = self.client.post("/api/contact-consultation", json=payload)
            self.assertEqual(res.status_code, 200)
            data = res.get_json()
            self.assertTrue(data["success"])
            self.assertFalse(data["email_sent"], "Chưa có SMTP thì email_sent = False")

            # Kiểm tra CSDL
            with app.app_context():
                db = get_db()
                cur = db.cursor()
                cur.execute("SELECT ten_truong, ho_ten, sdt, email FROM tu_van_trien_khai WHERE sdt = '0912345678'")
                row = cur.fetchone()
                self.assertIsNotNone(row, "Dữ liệu tư vấn phải được lưu vào bảng tu_van_trien_khai")
                self.assertEqual(row[0], "THPT Chuyên Hạ Long")
                self.assertEqual(row[1], "Thầy Trần Văn Nam")
        finally:
            for k, v in old_smtp_vals.items():
                if v is not None:
                    os.environ[k] = v
                else:
                    os.environ.pop(k, None)

        # 2. Test submit khi CÓ cấu hình SMTP -> gọi gửi mail qua SMTP
        with patch("app.send_consultation_notification_email") as mock_send_email:
            mock_send_email.return_value = True
            payload2 = {
                "ten_truong": "THCS Bãi Cháy",
                "ho_ten": "Cô Lê Thị Mai",
                "sdt": "0987654321",
                "email": "mailt@baichay.edu.vn",
                "ghi_chu": "Đăng ký thành lập CLB Ngân hàng Thời gian"
            }
            res2 = self.client.post("/api/contact-consultation", json=payload2)
            self.assertEqual(res2.status_code, 200)
            data2 = res2.get_json()
            self.assertTrue(data2["success"])
            self.assertTrue(data2["email_sent"], "Có SMTP thì email_sent = True")
            mock_send_email.assert_called_once_with(
                "THCS Bãi Cháy", "Cô Lê Thị Mai", "0987654321", "mailt@baichay.edu.vn", "Đăng ký thành lập CLB Ngân hàng Thời gian"
            )

        # 3. Test trực tiếp hàm send_consultation_notification_email với smtplib mock
        from app import send_consultation_notification_email
        with patch.dict(os.environ, {
            "SMTP_HOST": "smtp.gmail.com",
            "SMTP_PORT": "587",
            "SMTP_USER": "test@gmail.com",
            "SMTP_PASS": "secretpass123"
        }):
            with patch("smtplib.SMTP") as mock_smtp_cls:
                mock_smtp_inst = MagicMock()
                mock_smtp_cls.return_value = mock_smtp_inst

                sent = send_consultation_notification_email(
                    "THPT Cẩm Phả", "Thầy Hoàng", "0900000000", "campha@edu.vn", "Thử nghiệm"
                )
                self.assertTrue(sent)
                mock_smtp_cls.assert_called_with("smtp.gmail.com", 587, timeout=10)
                self.assertTrue(mock_smtp_inst.sendmail.called)
                args = mock_smtp_inst.sendmail.call_args[0]
                self.assertEqual(args[0], "test@gmail.com")
                self.assertEqual(args[1], ["mshuyenuka@gmail.com"])

if __name__ == "__main__":
    unittest.main()
