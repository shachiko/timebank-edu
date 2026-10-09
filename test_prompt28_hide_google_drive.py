# -*- coding: utf-8 -*-
"""
TEST SUITE: KIỂM THỬ ẨN 'GOOGLE DRIVE' KHỎI GIAO DIỆN NGƯỜI DÙNG (PROMPT 28)
Mục tiêu nghiệm thu:
1. Học sinh/giáo viên không thấy chữ 'Google Drive' hoặc '5TB' ở bất kỳ trang tài liệu nào (/documents, /documents/upload).
2. Các mẫu câu giao diện người dùng chuyển chuẩn:
   - 'Google Drive 5TB' -> 'hệ thống'
   - 'Kho 5TB Google Drive' -> 'Kho tài liệu'
   - 'Stream trực tiếp lên Google Drive 5TB' -> 'Tải trực tiếp lên hệ thống'
   - 'Đang truyền tệp sang Google Drive...' -> 'Đang tải tệp lên hệ thống...'
   - Flash upload: 'Tải lên tài liệu X thành công vào thư mục Y trên hệ thống.'
3. Trang /admin vẫn hiện đầy đủ thông tin cấu hình Google Drive (OAuth2, token, tab Drive).
4. Code, comment, log kỹ thuật giữ nguyên.
5. Regression test pass.
"""

import os
import io
import sys
import unittest
from unittest.mock import patch

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from app import app


class TestPrompt28HideGoogleDrive(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: QUÉT TĨNH CÁC TEMPLATE TÀI LIỆU NGƯỜI DÙNG THƯỜNG
    # =========================================================================
    def test_01_user_document_templates_do_not_contain_google_drive(self):
        """[TIÊU CHÍ 1]: documents_index.html và documents_upload.html không chứa 'Google Drive'."""
        user_templates = [
            "templates/documents_index.html",
            "templates/documents_upload.html"
        ]

        for t_path in user_templates:
            self.assertTrue(os.path.exists(t_path), f"File {t_path} không tồn tại!")
            with open(t_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Không được chứa Google Drive
            self.assertNotIn("Google Drive", content,
                             f"File {t_path} vẫn còn chứa chữ 'Google Drive' dành cho người dùng thường!")
            self.assertNotIn("Google", content,
                             f"File {t_path} vẫn còn chứa chữ 'Google'!")

        # Kiểm tra chi tiết các cụm từ mới theo yêu cầu
        with open("templates/documents_upload.html", "r", encoding="utf-8") as f:
            upload_content = f.read()
        self.assertIn("Tải Lên Tài Liệu - Kho tài liệu", upload_content)
        self.assertIn("Lưu trữ đám mây hệ thống", upload_content)
        self.assertIn("Tải trực tiếp lên hệ thống", upload_content)
        self.assertIn("Đang tải tệp lên hệ thống...", upload_content)

        with open("templates/documents_index.html", "r", encoding="utf-8") as f:
            index_content = f.read()
        self.assertIn("Kho Tài Liệu Học Tập", index_content)
        self.assertIn("Hệ thống lưu trữ đám mây tốc độ cao", index_content)
        self.assertIn("xóa tài liệu này khỏi hệ thống?", index_content)

        print("\n[PASS - TC 1]: Quét tĩnh template tài liệu học sinh/giáo viên: 0 chữ 'Google Drive', chuẩn cụm từ mới.")

    # =========================================================================
    # TIÊU CHÍ 2: TRANG /ADMIN VẪN HIỆN ĐẦY ĐỦ THÔNG TIN GOOGLE DRIVE
    # =========================================================================
    def test_02_admin_templates_retain_google_drive_configuration(self):
        """[TIÊU CHÍ 2]: admin.html và admin_drive_token_display.html vẫn giữ đầy đủ thông tin Google Drive."""
        admin_templates = [
            "templates/admin.html",
            "templates/admin_drive_token_display.html"
        ]

        for t_path in admin_templates:
            self.assertTrue(os.path.exists(t_path), f"File {t_path} không tồn tại!")
            with open(t_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn("Google Drive", content,
                          f"File {t_path} quản trị phải giữ nguyên thông tin 'Google Drive' để Super Admin cấu hình!")

        # Kiểm tra trang /admin khi render thực tế cho Super Admin
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["ma_hoc_sinh"] = "SUPERADMIN"
            sess["ho_ten"] = "Tổng Quản Trị"
            sess["vai_tro"] = "super_admin"
            sess["truong_id"] = 1

        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200)
        html_admin = res_admin.data.decode("utf-8")
        self.assertIn("Google Drive", html_admin)

        print("\n[PASS - TC 2]: Trang /admin giữ trọn vẹn thông tin kỹ thuật Google Drive phục vụ quản trị viên.")

    # =========================================================================
    # TIÊU CHÍ 3: TIN NHẮN FLASH KHÔNG CHỨA GOOGLE DRIVE VÀ DÙNG CHUẨN 'HỆ THỐNG'
    # =========================================================================
    def test_03_flash_messages_use_system_terminology(self):
        """[TIÊU CHÍ 3]: Thông báo tải lên và xóa tài liệu dùng 'hệ thống' thay cho 'Google Drive'."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Nguyễn Văn Test"

        # Mock tải lên thành công 1 tệp
        fake_pdf = (io.BytesIO(b"%PDF-1.4 Single Test"), "bai_tap.pdf")
        with patch("app.upload_document_stream") as mock_upload:
            mock_upload.return_value = {
                "file_id": "file_id_999",
                "web_view_link": "https://drive.google.com/test",
                "storage_type": "google_drive"
            }
            res_single = self.client.post("/documents/upload", data={
                "mon_hoc": "Toán",
                "tieu_de": "Chuyên đề Hàm Số",
                "files": [fake_pdf]
            }, content_type="multipart/form-data", follow_redirects=True)

            self.assertEqual(res_single.status_code, 200)
            html_single = res_single.data.decode("utf-8")
            self.assertIn("thành công vào thư mục Toán trên hệ thống!", html_single)
            self.assertNotIn("Google Drive", html_single)

        # Mock tải lên thành công nhiều tệp
        fake_pdf_1 = (io.BytesIO(b"%PDF-1.4 Multi 1"), "bt1.pdf")
        fake_pdf_2 = (io.BytesIO(b"%PDF-1.4 Multi 2"), "bt2.pdf")
        with patch("app.upload_document_stream") as mock_upload:
            mock_upload.return_value = {
                "file_id": "file_id_888",
                "web_view_link": "https://drive.google.com/test",
                "storage_type": "google_drive"
            }
            res_multi = self.client.post("/documents/upload", data={
                "mon_hoc": "Hóa học",
                "tieu_de": "Bộ Đề Hóa",
                "files": [fake_pdf_1, fake_pdf_2]
            }, content_type="multipart/form-data", follow_redirects=True)

            self.assertEqual(res_multi.status_code, 200)
            html_multi = res_multi.data.decode("utf-8")
            self.assertIn("thành công vào thư mục Hóa học trên hệ thống!", html_multi)
            self.assertNotIn("Google Drive", html_multi)

        print("\n[PASS - TC 3]: Tin nhắn flash thông báo tải lên chuẩn format 'trên hệ thống', không lộ Google Drive.")

    # =========================================================================
    # TIÊU CHÍ 4: HỌC SINH TRUY CẬP /DOCUMENTS VÀ /DOCUMENTS/UPLOAD KHÔNG THẤY GOOGLE DRIVE
    # =========================================================================
    def test_04_rendered_pages_have_zero_google_drive_for_students(self):
        """[TIÊU CHÍ 4]: Render thực tế trang /documents và /documents/upload: 0 chữ 'Google Drive'."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Trường Một"

        # 1. Trang danh sách tài liệu
        res_index = self.client.get("/documents")
        self.assertEqual(res_index.status_code, 200)
        html_index = res_index.data.decode("utf-8")
        self.assertNotIn("Google Drive", html_index)
        self.assertNotIn("5TB", html_index)

        # 2. Trang tải lên tài liệu
        res_upload = self.client.get("/documents/upload")
        self.assertEqual(res_upload.status_code, 200)
        html_upload = res_upload.data.decode("utf-8")
        self.assertNotIn("Google Drive", html_upload)
        self.assertNotIn("5TB", html_upload)

        print("\n[PASS - TC 4]: Giao diện người dùng học sinh/giáo viên hoàn toàn sạch bóng chữ 'Google Drive' & '5TB'.")


if __name__ == "__main__":
    unittest.main()
