# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — HOTFIX BỔ SUNG THƯ VIỆN GOOGLE DRIVE VÀ THÔNG BÁO UPLOAD TRUNG THỰC

Nghiệm thu:
1. requirements.txt có đầy đủ google-api-python-client>=2.0.0 và google-auth>=2.0.0.
2. Tất cả import trong drive_service.py đều thuộc chuẩn thư viện Python hoặc có trong requirements.txt.
3. Khi chưa kết nối Google Drive (rơi vào mock_drive): thông báo sau khi upload phải
   nêu rõ "Tải lên kho tạm (chưa kết nối Drive), vui lòng liên hệ quản trị viên" thay vì báo Drive 5TB.
4. Khi kết nối Google Drive thật: thông báo thành công trên Google Drive 5TB.
"""

import os
import io
import sys
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db


class TestPrompt24DrivePackages(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: REQUIREMENTS.TXT ĐỦ 2 PACKAGE GOOGLE DRIVE
    # =========================================================================
    def test_01_requirements_txt_has_google_packages(self):
        """[TIÊU CHÍ 1]: requirements.txt chứa google-api-python-client và google-auth."""
        req_path = os.path.join(os.path.dirname(__file__), "requirements.txt")
        self.assertTrue(os.path.exists(req_path))

        with open(req_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("google-api-python-client", content)
        self.assertIn("google-auth", content)
        print("\n[PASS - TC 1]: requirements.txt chứa đầy đủ google-api-python-client và google-auth.")

    # =========================================================================
    # TIÊU CHÍ 2: KIỂM TRA TOÀN BỘ IMPORT TRONG DRIVE_SERVICE.PY
    # =========================================================================
    def test_02_drive_service_imports_resolvable(self):
        """[TIÊU CHÍ 2]: Mọi package được import trong drive_service.py đều có sẵn và import thành công."""
        try:
            import google.oauth2.credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
            import drive_service
        except ImportError as e:
            self.fail(f"Lỗi import package trong drive_service.py: {e}")

        self.assertTrue(callable(drive_service.upload_document_stream))
        self.assertTrue(callable(drive_service.download_document_stream))
        self.assertTrue(callable(drive_service.delete_document_file))
        print("\n[PASS - TC 2]: Toàn bộ module Google Drive API đều import trơn tru.")

    # =========================================================================
    # TIÊU CHÍ 3: THÔNG BÁO UPLOAD TRUNG THỰC KHI RƠI VÀO KHO TẠM (MOCK_DRIVE)
    # =========================================================================
    def test_03_upload_message_truthful_when_mock_drive(self):
        """[TIÊU CHÍ 3]: Khi chưa kết nối Drive -> Báo rõ 'Tải lên kho tạm (chưa kết nối Drive), vui lòng liên hệ quản trị viên'."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Test Drive"

        fake_pdf = (io.BytesIO(b"%PDF-1.4 Mock Upload Test"), "test_de_thi.pdf")

        # Đảm bảo không có credentials thật trong env
        with patch.dict(os.environ, {"GOOGLE_REFRESH_TOKEN": ""}, clear=False):
            resp = self.client.post("/documents/upload", data={
                "mon_hoc": "Toán",
                "tieu_de": "Đề thi thử Toán học mock",
                "mo_ta": "Mô tả tài liệu học tập",
                "file": fake_pdf
            }, content_type="multipart/form-data", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode("utf-8")
            # Phải có thông báo trung thực
            self.assertIn("Tải lên kho tạm (chưa kết nối Drive), vui lòng liên hệ quản trị viên", html)
            # Tuyệt đối KHÔNG được báo thành công trên Google Drive 5TB
            self.assertNotIn("thành công vào thư mục Toán trên Google Drive 5TB", html)

        print("\n[PASS - TC 3]: Thông báo khi rơi vào kho tạm chính xác, trung thực (không nói dối người dùng).")

    # =========================================================================
    # TIÊU CHÍ 4: THÔNG BÁO THÀNH CÔNG KHI KẾT NỐI GOOGLE DRIVE THẬT
    # =========================================================================
    def test_04_upload_message_success_when_real_drive(self):
        """[TIÊU CHÍ 4]: Khi kết nối Drive thật -> Báo thành công vào thư mục trên Google Drive 5TB."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Test Drive"

        fake_pdf = (io.BytesIO(b"%PDF-1.4 Real Drive Upload Test"), "test_de_thi_real.pdf")

        with patch("app.upload_document_stream") as mock_upload:
            mock_upload.return_value = {
                "file_id": "real_drive_id_12345",
                "web_view_link": "https://drive.google.com/file/d/real_drive_id_12345/view",
                "storage_type": "google_drive"
            }

            resp = self.client.post("/documents/upload", data={
                "mon_hoc": "Vật lý",
                "tieu_de": "Tài liệu Vật lý 12 thực tế",
                "mo_ta": "Tài liệu trên Google Drive 5TB thật",
                "file": fake_pdf
            }, content_type="multipart/form-data", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)
            html = resp.data.decode("utf-8")
            self.assertIn("thành công vào thư mục Vật lý trên Google Drive 5TB!", html)

        print("\n[PASS - TC 4]: Thông báo khi kết nối Drive thật chúc mừng đúng trên Google Drive 5TB.")


if __name__ == "__main__":
    unittest.main()
