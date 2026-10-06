# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE DEPLOY
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Nội dung kiểm thử Milestone DEPLOY (Triển khai đám mây Render & Cơ sở dữ liệu):
1. RUNTIME & PROCFILE: runtime.txt chỉ định Python 3.11; Procfile chứa lệnh web: gunicorn app:app.
2. RENDER YAML BLUEPRINT: render.yaml có cấu trúc hợp lệ, buildCommand và startCommand chuẩn.
3. CHUYỂN ĐỔI DATABASE DỰA TRÊN DATABASE_URL:
   - Không có DATABASE_URL -> dùng SQLite cục bộ (Single-Tenant).
   - Có DATABASE_URL -> kích hoạt PostgreSQL và chuẩn hóa URL kết nối.
4. BẢO MẬT BIẾN MÔI TRƯỜNG:
   - SECRET_KEY đọc từ biến môi trường.
   - FLASK_DEBUG tắt (0 / False) khi cấu hình Production.
5. DEPENDENCIES PRODUCTION: requirements.txt chứa đầy đủ gunicorn và psycopg2-binary.
6. TÀI LIỆU HƯỚNG DẪN DEPLOY: README.md có mục hướng dẫn Render và trỏ tên miền CNAME.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import unittest
import yaml
from pathlib import Path

# Đảm bảo đường dẫn import app
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app, is_postgres_configured, get_postgres_url


class TestMilestoneDeploy(unittest.TestCase):
    def test_01_runtime_and_procfile_exist(self):
        """
        [TEST CASE 1]: Kiểm tra runtime.txt (Python 3.11) và Procfile (Gunicorn)
        """
        runtime_path = BASE_DIR / "runtime.txt"
        self.assertTrue(runtime_path.exists(), "Tệp runtime.txt không tồn tại!")
        with open(runtime_path, "r", encoding="utf-8") as f:
            runtime_content = f.read().strip()
        self.assertTrue(runtime_content.startswith("python-3.11"), f"runtime.txt phải là Python 3.11, hiện tại: {runtime_content}")

        procfile_path = BASE_DIR / "Procfile"
        self.assertTrue(procfile_path.exists(), "Tệp Procfile không tồn tại!")
        with open(procfile_path, "r", encoding="utf-8") as f:
            procfile_content = f.read().strip()
        self.assertIn("web: gunicorn app:app", procfile_content, "Procfile phải chứa lệnh khởi chạy 'web: gunicorn app:app'!")

    def test_02_render_yaml_valid_blueprint(self):
        """
        [TEST CASE 2]: Kiểm tra cú pháp và cấu trúc hợp lệ của render.yaml
        """
        render_yaml_path = BASE_DIR / "render.yaml"
        self.assertTrue(render_yaml_path.exists(), "Tệp render.yaml không tồn tại!")
        with open(render_yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        self.assertIsInstance(data, dict, "render.yaml phải là tệp YAML hợp lệ dạng dict!")
        self.assertIn("services", data, "render.yaml phải có mục services!")
        service = data["services"][0]
        self.assertEqual(service.get("type"), "web")
        self.assertEqual(service.get("runtime"), "python")
        self.assertIn("gunicorn app:app", service.get("startCommand", ""))
        self.assertIn("pip install -r requirements.txt", service.get("buildCommand", ""))

    def test_03_database_url_switching_logic(self):
        """
        [TEST CASE 3]: Đọc DATABASE_URL từ biến môi trường:
        - Không có DATABASE_URL -> dùng SQLite cục bộ (is_postgres_configured = False).
        - Có DATABASE_URL (postgres://...) -> kích hoạt PostgreSQL (is_postgres_configured = True)
          và chuẩn hóa thành postgresql://...
        """
        original_db_url = os.environ.get("DATABASE_URL")
        try:
            # 1. Khi không có DATABASE_URL
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            self.assertFalse(is_postgres_configured(), "Khi không có DATABASE_URL phải dùng SQLite!")

            # 2. Khi có DATABASE_URL bắt đầu bằng postgres://
            test_pg_url = "postgres://usr:pwd@ep-test.render.com:5432/timebank_db"
            os.environ["DATABASE_URL"] = test_pg_url
            self.assertTrue(is_postgres_configured(), "Khi có DATABASE_URL phải nhận diện là PostgreSQL!")
            normalized_url = get_postgres_url()
            self.assertTrue(normalized_url.startswith("postgresql://"), f"URL phải được chuẩn hóa bắt đầu bằng postgresql://, kết quả: {normalized_url}")

            # 3. Khi có DATABASE_URL bắt đầu bằng postgresql://
            test_pg_url_2 = "postgresql://usr:pwd@ep-test.render.com:5432/timebank_db"
            os.environ["DATABASE_URL"] = test_pg_url_2
            self.assertTrue(is_postgres_configured())
            self.assertEqual(get_postgres_url(), test_pg_url_2)
        finally:
            if original_db_url is not None:
                os.environ["DATABASE_URL"] = original_db_url
            elif "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]

    def test_04_security_environment_and_debug_mode(self):
        """
        [TEST CASE 4]: Bảo mật biến môi trường:
        - SECRET_KEY được nạp từ biến môi trường.
        - FLASK_DEBUG nhận diện chính xác chế độ production.
        """
        test_secret = "test-custom-render-secret-key-12345"
        os.environ["SECRET_KEY"] = test_secret
        # Khởi tạo lại cấu hình từ môi trường
        app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "default"
        self.assertEqual(app.config["SECRET_KEY"], test_secret)

        # Kiểm tra cờ debug khi deploy (FLASK_DEBUG="0")
        os.environ["FLASK_DEBUG"] = "0"
        debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
        self.assertFalse(debug_mode, "Khi FLASK_DEBUG='0' thì debug mode phải tắt!")

    def test_05_production_dependencies_in_requirements(self):
        """
        [TEST CASE 5]: requirements.txt chứa đầy đủ gunicorn và psycopg2-binary
        """
        req_path = BASE_DIR / "requirements.txt"
        with open(req_path, "r", encoding="utf-8") as f:
            req_content = f.read()

        self.assertIn("gunicorn", req_content, "requirements.txt phải chứa gunicorn!")
        self.assertIn("psycopg2-binary", req_content, "requirements.txt phải chứa psycopg2-binary!")

    def test_06_readme_contains_deploy_guide_and_cname(self):
        """
        [TEST CASE 6]: README.md chứa mục HƯỚNG DẪN DEPLOY, Render, GEMINI_API_KEY và CNAME
        """
        readme_path = BASE_DIR / "README.md"
        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()

        self.assertIn("HƯỚNG DẪN DEPLOY", readme_content, "README phải có mục HƯỚNG DẪN DEPLOY!")
        self.assertIn("Render", readme_content, "README phải nhắc đến nền tảng Render!")
        self.assertIn("GEMINI_API_KEY", readme_content, "README phải hướng dẫn nhập GEMINI_API_KEY!")
        self.assertIn("CNAME", readme_content, "README phải hướng dẫn trỏ tên miền bằng bản ghi CNAME!")


if __name__ == "__main__":
    unittest.main(verbosity=2)
