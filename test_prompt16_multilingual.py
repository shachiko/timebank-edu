# -*- coding: utf-8 -*-
"""
BỘ TEST KIỂM THỬ PROMPT 16: ĐA NGÔN NGỮ (VIỆT / ANH / TRUNG / PHÁP / ĐỨC)
1. Tích hợp Flask-Babel:
   - Cài đặt, cấu hình 5 ngôn ngữ: vi (mặc định), en, zh, fr, de.
   - KHÔNG tự nhận diện qua IP hay Accept-Language — người dùng tự chọn bằng nút chuyển ngôn ngữ trên header.
   - Lưu lựa chọn vào session (mặc định tiếng Việt).
2. Dịch CHỈ giao diện (menu, nút bấm, tiêu đề, thông báo...),
   KHÔNG dịch nội dung do người dùng tạo (tên kỹ năng, bài đăng diễn đàn, mô tả tài liệu...).
3. Dùng gettext: bọc mọi chuỗi giao diện trong _() hoặc {{ _() }}.
4. Đủ 5 file .po và 5 file .mo biên dịch đầy đủ.
5. Kiểm tra chuyển đổi ngôn ngữ mượt mà và giữ trạng thái khi tải lại trang.
"""

import unittest
import sys
import os
from pathlib import Path

# Đảm bảo in UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, SUPPORTED_LANGUAGES


class TestPrompt16Multilingual(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_01_supported_languages_and_po_mo_files_exist(self):
        """Kiểm tra cấu hình 5 ngôn ngữ và sự tồn tại của file .po + .mo"""
        self.assertEqual(set(SUPPORTED_LANGUAGES.keys()), {"vi", "en", "zh", "fr", "de"})
        
        base_dir = Path(__file__).resolve().parent
        translations_dir = base_dir / "translations"
        self.assertTrue(translations_dir.exists(), "Thư mục translations không tồn tại")
        
        for lang in ["vi", "en", "zh", "fr", "de"]:
            po_file = translations_dir / lang / "LC_MESSAGES" / "messages.po"
            mo_file = translations_dir / lang / "LC_MESSAGES" / "messages.mo"
            self.assertTrue(po_file.exists(), f"Thiếu file .po cho ngôn ngữ {lang}")
            self.assertTrue(mo_file.exists(), f"Thiếu file .mo cho ngôn ngữ {lang}")
            self.assertGreater(po_file.stat().st_size, 100, f"File {po_file} quá nhỏ hoặc rỗng")
            self.assertGreater(mo_file.stat().st_size, 100, f"File {mo_file} quá nhỏ hoặc rỗng")

    def test_02_default_language_is_vietnamese(self):
        """Mặc định khi không có session['lang'], ngôn ngữ luôn là tiếng Việt (vi)"""
        with self.client as c:
            res = c.get("/")
            self.assertEqual(res.status_code, 200)
            html = res.get_data(as_text=True)
            self.assertIn('lang="vi"', html)
            self.assertIn("Ngân hàng Thời gian Học đường", html)
            self.assertTrue("Kho kỹ năng học đường" in html or "Chợ kỹ năng" in html)
            self.assertIn("Mô hình hoạt động", html)
            self.assertIn("Quy trình 4 bước", html)
            self.assertIn("Đăng nhập", html)
            self.assertIn("Đăng ký", html)
            self.assertIn("🇻🇳 VI", html)

    def test_03_switch_language_to_english(self):
        """Chuyển đổi sang tiếng Anh (en), session được lưu và giao diện đổi sang English"""
        with self.client as c:
            # Gọi route chuyển ngôn ngữ
            res = c.get("/set-language/en", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            # Kiểm tra session
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("lang"), "en")
                
            html = res.get_data(as_text=True)
            self.assertIn('lang="en"', html)
            self.assertIn("School Time Bank", html)
            self.assertIn("Skills Market", html)
            self.assertIn("Operating Model", html)
            self.assertIn("4-Step Process", html)
            self.assertIn("Log In", html)
            self.assertIn("Sign Up", html)
            self.assertIn("🇬🇧 EN", html)
            
            # Tải lại trang khác (vd /login) vẫn giữ ngôn ngữ en
            res_login = c.get("/login")
            self.assertEqual(res_login.status_code, 200)
            login_html = res_login.get_data(as_text=True)
            self.assertIn('lang="en"', login_html)
            self.assertIn("TimeBank Login", login_html)
            self.assertIn("Student ID / Username", login_html)
            self.assertIn("Password", login_html)
            self.assertIn("Log In to System", login_html)

    def test_04_switch_language_to_chinese(self):
        """Chuyển đổi sang tiếng Trung (zh), session được lưu và giao diện đổi sang 中文"""
        with self.client as c:
            res = c.get("/set-language/zh", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("lang"), "zh")
                
            html = res.get_data(as_text=True)
            self.assertIn('lang="zh"', html)
            self.assertIn("校园时间银行", html)
            self.assertIn("技能市集", html)
            self.assertIn("运作模式", html)
            self.assertIn("四步流程", html)
            self.assertIn("登录", html)
            self.assertIn("注册", html)
            self.assertIn("🇨🇳 中文", html)

    def test_05_switch_language_to_french(self):
        """Chuyển đổi sang tiếng Pháp (fr), session được lưu và giao diện đổi sang Français"""
        with self.client as c:
            res = c.get("/set-language/fr", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("lang"), "fr")
                
            html = res.get_data(as_text=True)
            self.assertIn('lang="fr"', html)
            self.assertIn("Banque de Temps Scolaire", html)
            self.assertIn("Marché des Compétences", html)
            self.assertIn("Modèle de Fonctionnement", html)
            self.assertIn("Processus en 4 Étapes", html)
            self.assertIn("Connexion", html)
            self.assertIn("Inscription", html)
            self.assertIn("🇫🇷 FR", html)

    def test_06_switch_language_to_german(self):
        """Chuyển đổi sang tiếng Đức (de), session được lưu và giao diện đổi sang Deutsch"""
        with self.client as c:
            res = c.get("/set-language/de", follow_redirects=True)
            self.assertEqual(res.status_code, 200)
            
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("lang"), "de")
                
            html = res.get_data(as_text=True)
            self.assertIn('lang="de"', html)
            self.assertIn("Schul-Zeitbank", html)
            self.assertIn("Kompetenzmarkt", html)
            self.assertIn("Funktionsmodell", html)
            self.assertIn("4-Schritte-Prozess", html)
            self.assertIn("Anmelden", html)
            self.assertIn("Registrieren", html)
            self.assertIn("🇩🇪 DE", html)

    def test_07_user_content_not_translated(self):
        """Nội dung người dùng tạo (tên người dùng, tên kỹ năng) KHÔNG bị dịch"""
        with self.client as c:
            # Chuyển sang tiếng Anh
            c.get("/set-language/en", follow_redirects=True)
            
            # Truy cập trang Chợ kỹ năng (/skills)
            res = c.get("/skills")
            html = res.get_data(as_text=True)
            
            # Tiêu đề kỹ năng người dùng tạo vẫn giữ nguyên tiếng Việt
            self.assertIn("Ôn tập Hình học không gian lớp 12", html)
            
            # Tên học sinh người dùng tạo vẫn giữ nguyên tiếng Việt
            self.assertIn("Nguyễn Hoàng An", html)

    def test_08_invalid_language_code_ignored(self):
        """Mã ngôn ngữ không nằm trong SUPPORTED_LANGUAGES sẽ bị bỏ qua và giữ ngôn ngữ hợp lệ"""
        with self.client as c:
            # Chọn en trước
            c.get("/set-language/en", follow_redirects=True)
            # Thử set ngôn ngữ lạ
            c.get("/set-language/invalid_xyz", follow_redirects=True)
            with c.session_transaction() as sess:
                self.assertEqual(sess.get("lang"), "en")
                
            # Xóa session thử lại
            c.get("/logout")
            c.get("/set-language/es", follow_redirects=True) # Tây Ban Nha không trong danh sách
            res = c.get("/")
            html = res.get_data(as_text=True)
            self.assertIn('lang="vi"', html)


if __name__ == "__main__":
    unittest.main()
