# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHO PROMPT 22:
PHÒNG HỌC ẢO 3 NÒNG (Daily.co CHÍNH -> JaaS DỰ PHÒNG 1 -> Jitsi DỰ PHÒNG 2)
========================================================================
Nội dung nghiệm thu:
1. VIDEO_PROVIDER=daily: vào phòng KHÔNG hỏi đăng nhập thêm;
   tên hiển thị = tên thật; người dạy có quyền chủ phòng (is_owner=True).
2. Giả lập lỗi Daily (xóa DAILY_API_KEY tạm hoặc API trả lỗi): tự chuyển sang JaaS, không crash.
3. Giả lập lỗi JaaS: tự chuyển sang Jitsi + hiện banner dự phòng.
4. VIDEO_PROVIDER=jaas: dùng JaaS ngay từ đầu, bỏ qua Daily.
5. VIDEO_PROVIDER=jitsi: dùng Jitsi trực tiếp.
6. Không có API key hardcode trong code/GitHub.
7. Cột daily_room_name, daily_room_url tồn tại trong bảng sessions.
8. Regression: điểm danh, luật 80%, dàn ý AI, các luồng cũ không vỡ.
"""

import os
import sys
import json
import sqlite3
import unittest
from unittest.mock import patch, MagicMock

# Thiết lập console utf-8
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import requests
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app import (
    app, init_db, DATABASE_PATH,
    get_video_provider, get_daily_config, get_jaas_config,
    create_daily_room, create_daily_meeting_token,
    generate_jaas_jwt
)


class TestPrompt22ThreeEngines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Sinh khóa RSA giả lập JaaS cho testing
        cls.test_rsa_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        cls.test_pem_private = cls.test_rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")
        
        cls.test_app_id = "vpaas-magic-cookie-test-p22"
        cls.test_api_key = "vpaas-magic-cookie-test-p22/test_p22_key"
        cls.test_daily_api_key = "mock_daily_api_key_test_2026"

    def setUp(self):
        self.client = app.test_client()
        # Lưu các biến môi trường
        self.orig_env = {
            "DAILY_API_KEY": os.environ.get("DAILY_API_KEY"),
            "VIDEO_PROVIDER": os.environ.get("VIDEO_PROVIDER"),
            "JAAS_APP_ID": os.environ.get("JAAS_APP_ID"),
            "JAAS_API_KEY": os.environ.get("JAAS_API_KEY"),
            "JAAS_PRIVATE_KEY": os.environ.get("JAAS_PRIVATE_KEY")
        }
        self._ensure_sample_sessions()

    def tearDown(self):
        for k, v in self.orig_env.items():
            if v is not None:
                os.environ[k] = v
            else:
                os.environ.pop(k, None)

    def _ensure_sample_sessions(self):
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_row = cur.fetchone()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_row = cur.fetchone()
        
        self.an_id = an_row["id"] if an_row else 1
        self.binh_id = binh_row["id"] if binh_row else 2

        # Tạo session test 9991
        cur.execute("SELECT id FROM sessions WHERE id = 9991")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO sessions (id, skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
                VALUES (9991, 1, ?, ?, '2026-10-25 09:00:00', 1.0, 'da_dat', 'QR-P22-3ENG-1', 0, 0)
            """, (self.an_id, self.binh_id))
        conn.commit()
        conn.close()

    def login_as(self, user_id):
        with self.client.session_transaction() as sess:
            sess["user_id"] = user_id
            sess["user_name"] = "Người Dùng Test"
            sess["role"] = "hoc_sinh"

    # =========================================================================
    # 1. KIỂM THỬ CẤU HÌNH & SCHEMA
    # =========================================================================
    def test_01_sessions_schema_has_daily_columns(self):
        """Bảng sessions phải có cột daily_room_name và daily_room_url."""
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(sessions)")
        cols = [r[1] for r in cur.fetchall()]
        conn.close()
        self.assertIn("daily_room_name", cols, "Bảng sessions thiếu cột daily_room_name")
        self.assertIn("daily_room_url", cols, "Bảng sessions thiếu cột daily_room_url")

    def test_02_video_provider_config_resolution(self):
        """VIDEO_PROVIDER có thể cấu hình từ env hoặc config.yaml."""
        # Mặc định (khi không có env) -> lấy từ config.yaml ('daily')
        if "VIDEO_PROVIDER" in os.environ:
            del os.environ["VIDEO_PROVIDER"]
        prov = get_video_provider()
        self.assertEqual(prov, "daily", "Mặc định provider phải là 'daily'")

        # Ghi đè bằng biến môi trường
        os.environ["VIDEO_PROVIDER"] = "jaas"
        self.assertEqual(get_video_provider(), "jaas")
        os.environ["VIDEO_PROVIDER"] = "jitsi"
        self.assertEqual(get_video_provider(), "jitsi")
        os.environ["VIDEO_PROVIDER"] = "invalid_provider"
        self.assertEqual(get_video_provider(), "daily", "Provider không hợp lệ phải fallback về 'daily'")

    # =========================================================================
    # 2. KIỂM THỬ BACKEND DAILY.CO: TẠO PHÒNG VÀ TOKEN
    # =========================================================================
    @patch("requests.post")
    def test_03_create_daily_room_success(self, mock_post):
        """Tạo phòng Daily.co: POST https://api.daily.co/v1/rooms và lưu vào DB."""
        os.environ["DAILY_API_KEY"] = self.test_daily_api_key
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "name": "timebank-session-9991",
            "url": "https://timebankedu.daily.co/timebank-session-9991",
            "privacy": "private"
        }
        mock_post.return_value = mock_resp

        room_name, room_url = create_daily_room(9991)
        self.assertIsNotNone(room_name)
        self.assertEqual(room_name, "timebank-session-9991")
        self.assertEqual(room_url, "https://timebankedu.daily.co/timebank-session-9991")

        # Kiểm tra xem đã lưu vào DB chưa
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT daily_room_name, daily_room_url FROM sessions WHERE id = 9991")
        row = cur.fetchone()
        conn.close()
        self.assertEqual(row[0], "timebank-session-9991")
        self.assertEqual(row[1], "https://timebankedu.daily.co/timebank-session-9991")

    @patch("requests.post")
    def test_04_daily_token_for_teacher_and_student(self, mock_post):
        """Người dạy có is_owner=True, người học có is_owner=False, tên = tên thật."""
        os.environ["DAILY_API_KEY"] = self.test_daily_api_key
        os.environ["VIDEO_PROVIDER"] = "daily"

        # Mock API tạo meeting token
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"token": "mock_daily_meeting_jwt_token_12345"}
        mock_post.return_value = mock_resp

        # 1. Đăng nhập với vai trò người dạy (an_id)
        self.login_as(self.an_id)
        res_teacher = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res_teacher.status_code, 200)
        data_teacher = res_teacher.get_json()
        self.assertTrue(data_teacher.get("success"))
        self.assertEqual(data_teacher.get("provider"), "daily")
        self.assertEqual(data_teacher.get("token"), "mock_daily_meeting_jwt_token_12345")

        # Xác thực tham số gửi đến Daily API cho người dạy: is_owner = True
        called_payload = mock_post.call_args[1]["json"]
        self.assertTrue(called_payload["properties"]["is_owner"])

        # 2. Đăng nhập với vai trò người học (binh_id)
        self.login_as(self.binh_id)
        res_student = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res_student.status_code, 200)
        data_student = res_student.get_json()
        self.assertTrue(data_student.get("success"))
        self.assertEqual(data_student.get("provider"), "daily")

        # Xác thực tham số gửi đến Daily API cho người học: is_owner = False
        called_payload_student = mock_post.call_args[1]["json"]
        self.assertFalse(called_payload_student["properties"]["is_owner"])

    # =========================================================================
    # 3. KIỂM THỬ TỰ ĐỘNG FALLBACK (DAILY -> JAAS -> JITSI)
    # =========================================================================
    def test_05_daily_fails_falls_back_to_jaas(self):
        """Giả lập thiếu DAILY_API_KEY hoặc Daily lỗi -> tự chuyển sang JaaS."""
        # Xóa DAILY_API_KEY, cài đặt JaaS
        if "DAILY_API_KEY" in os.environ:
            del os.environ["DAILY_API_KEY"]
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private
        os.environ["VIDEO_PROVIDER"] = "daily"

        self.login_as(self.an_id)
        res = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "jaas", "Thiếu Daily key phải tự động fallback sang JaaS")
        self.assertIn("token", data)
        self.assertIn("jaas_app_id", data)

    @patch("requests.post")
    def test_06_daily_api_network_error_falls_back_to_jaas(self, mock_post):
        """Giả lập Daily API bị lỗi mạng -> tự chuyển sang JaaS mà không crash 500."""
        os.environ["DAILY_API_KEY"] = self.test_daily_api_key
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private
        os.environ["VIDEO_PROVIDER"] = "daily"

        # Giả lập requests.post ném ngoại lệ mạng
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection to daily.co timed out")

        self.login_as(self.an_id)
        res = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "jaas", "Lỗi Daily API phải tự động fallback sang JaaS")

    def test_07_all_keys_missing_falls_back_to_jitsi(self):
        """Khi cả Daily và JaaS đều không có key -> fallback sang Jitsi, không crash 500."""
        if "DAILY_API_KEY" in os.environ:
            del os.environ["DAILY_API_KEY"]
        if "JAAS_APP_ID" in os.environ:
            del os.environ["JAAS_APP_ID"]
        if "JAAS_API_KEY" in os.environ:
            del os.environ["JAAS_API_KEY"]
        if "JAAS_PRIVATE_KEY" in os.environ:
            del os.environ["JAAS_PRIVATE_KEY"]

        self.login_as(self.an_id)
        # Trang HTML phòng học phải tải bình thường, báo trạng thái sẵn sàng cho Jitsi
        res_page = self.client.get("/phong-hoc/9991")
        self.assertEqual(res_page.status_code, 200)
        html = res_page.data.decode("utf-8")
        self.assertIn("Đang dùng phòng học dự phòng (Jitsi)", html)

        # Khi cả hai nòng JWT đều thiếu key, route token mặc định trả 503 thông báo thân thiện (không crash 500)
        res_token = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res_token.status_code, 503)
        self.assertIn("chưa cấu hình đầy đủ", res_token.get_json().get("error", "").lower())

        # Nhưng khi chuyển sang nòng Jitsi (dự phòng 2), route cấp phòng ngay lập tức (200)
        res_jitsi = self.client.post("/phong-hoc/9991/token?provider=jitsi", json={})
        self.assertEqual(res_jitsi.status_code, 200)
        data = res_jitsi.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "jitsi")
        self.assertIn("meet.jit.si", data.get("room_url", ""))

    # =========================================================================
    # 4. CHUYỂN ĐỔI NHANH QUA CONFIG (VIDEO_PROVIDER = "jaas" HOẶC "jitsi")
    # =========================================================================
    def test_08_provider_jaas_direct(self):
        """Khi đặt VIDEO_PROVIDER=jaas, hệ thống dùng thẳng JaaS mà không gọi Daily."""
        os.environ["VIDEO_PROVIDER"] = "jaas"
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private

        self.login_as(self.an_id)
        res = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "jaas")

    def test_09_provider_jitsi_direct(self):
        """Khi đặt VIDEO_PROVIDER=jitsi, hệ thống dùng thẳng Jitsi public."""
        os.environ["VIDEO_PROVIDER"] = "jitsi"
        self.login_as(self.an_id)
        res = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("provider"), "jitsi")

    # =========================================================================
    # 5. BẢO MẬT: BẢO VỆ PHÒNG HỌC & TOKEN PHÂN QUYỀN
    # =========================================================================
    def test_10_unauthorized_user_cannot_get_token(self):
        """Người ngoài không thuộc buổi học bị từ chối 403."""
        # User 999 là người ngoài
        self.login_as(999)
        res = self.client.post("/phong-hoc/9991/token", json={})
        self.assertEqual(res.status_code, 403)

    # =========================================================================
    # 6. GIAO DIỆN FRONTEND: BANNER, CONTAINERS, PEDAGOGICAL TOOLS
    # =========================================================================
    def test_11_frontend_template_structure(self):
        """Kiểm tra template virtual_room.html có đầy đủ 3 container và banner dự phòng."""
        with open("templates/virtual_room.html", "r", encoding="utf-8") as f:
            template_content = f.read()

        self.assertIn("@daily-co/daily-js", template_content, "Thiếu CDN Daily.js")
        self.assertIn("8x8.vc/external_api.js", template_content, "Thiếu CDN 8x8 JaaS")
        self.assertIn("Đang dùng phòng học dự phòng (Jitsi)", template_content, "Thiếu banner dự phòng Jitsi")
        self.assertIn('id="daily-room-container"', template_content)
        self.assertIn('id="jaas-meet-container"', template_content)
        self.assertIn('id="jitsi-meet-container"', template_content)

        # Bảo toàn công cụ sư phạm
        self.assertIn("roomTimer", template_content, "Mất đồng hồ đếm giờ")
        self.assertIn("reportViolationModal", template_content, "Mất modal báo cáo vi phạm")
        self.assertIn("Tiêu chí ≥ 80%", template_content, "Mất quy định 80% thời lượng")

    # =========================================================================
    # 7. QUÉT AN TOÀN: KHÔNG HARDCODE KHÓA TRONG KHO CODE
    # =========================================================================
    def test_12_no_hardcoded_keys_in_repo(self):
        """Đảm bảo không có key Daily hoặc Private Key PEM thực sự bị hardcode trong source code."""
        forbidden_patterns = [
            "DAILY_API_KEY =",
            "DAILY_API_KEY=",
            "-----BEGIN RSA PRIVATE KEY-----",
            "-----BEGIN PRIVATE KEY-----"
        ]
        # Quét các file code chính
        checked_files = [
            "app.py",
            "config.yaml",
            "ai_service.py",
            "database/schema.sql"
        ]
        for fpath in checked_files:
            if not os.path.exists(fpath):
                continue
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for pat in forbidden_patterns:
                    # Cho phép comment ví dụ nếu có, nhưng không cho phép gán string key thực
                    lines = [ln.strip() for ln in content.splitlines() if pat in ln and not ln.strip().startswith("#")]
                    self.assertEqual(len(lines), 0, f"Tìm thấy hardcoded key pattern '{pat}' trong {fpath}: {lines}")


if __name__ == "__main__":
    unittest.main()
