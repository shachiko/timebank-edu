# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHO PROMPT 22:
ĐĂNG NHẬP 1 LẦN CHO PHÒNG HỌC ẢO (JITSI JAAS RS256 JWT)
======================================================
Nội dung nghiệm thu:
1. Đọc 3 biến môi trường JAAS_APP_ID, JAAS_API_KEY, JAAS_PRIVATE_KEY (\n escape handled).
2. Thiếu biến môi trường -> Trang báo lỗi thân thiện, không 500, không crash.
3. Sinh JWT RS256: header kid, aud="jitsi", iss="chat", sub=JAAS_APP_ID, room="*", exp=now+2h.
4. Tên hiển thị = họ tên thật từ DB; người dạy có quyền moderator=True; người học moderator=False.
5. Học sinh không thuộc buổi học bị từ chối (403 Forbidden).
6. Token buổi A không dùng cho buổi B; token hết hạn bị từ chối.
7. Frontend: Bỏ iframe meet.jit.si cũ, dùng container JaaS External API + fetch token; bảo toàn 80%, điểm danh, báo cáo, dàn ý AI.
"""

import os
import sys
import time
import sqlite3
import unittest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# Thiết lập console utf-8
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from app import (
    app, init_db, DATABASE_PATH,
    get_jaas_config, generate_jaas_jwt, verify_jaas_token
)


class TestPrompt22JitsiJWT(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        # Sinh cặp khóa RSA test động hoàn toàn trong bộ nhớ (không lưu key cố định)
        cls.test_rsa_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        cls.test_pem_private = cls.test_rsa_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode("utf-8")
        
        cls.test_pem_public = cls.test_rsa_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("utf-8")

        cls.test_app_id = "vpaas-magic-cookie-test2026"
        cls.test_api_key = "vpaas-magic-cookie-test2026/test_key_01"

    def setUp(self):
        self.client = app.test_client()
        # Lưu biến môi trường gốc
        self.orig_env = {
            "JAAS_APP_ID": os.environ.get("JAAS_APP_ID"),
            "JAAS_API_KEY": os.environ.get("JAAS_API_KEY"),
            "JAAS_PRIVATE_KEY": os.environ.get("JAAS_PRIVATE_KEY")
        }
        # Đảm bảo có session mẫu trong DB
        self._ensure_sample_sessions()

    def tearDown(self):
        # Khôi phục biến môi trường
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

        # Tạo hoặc lấy session test 1
        cur.execute("SELECT id FROM sessions WHERE id = 9998")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO sessions (id, skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
                VALUES (9998, 1, ?, ?, '2026-10-20 10:00:00', 1.0, 'da_dat', 'QR-P22-SES1', 0, 0)
            """, (self.an_id, self.binh_id))

        # Tạo hoặc lấy session test 2
        cur.execute("SELECT id FROM sessions WHERE id = 9999")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO sessions (id, skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
                VALUES (9999, 1, ?, ?, '2026-10-21 14:00:00', 1.5, 'da_dat', 'QR-P22-SES2', 0, 0)
            """, (self.an_id, self.binh_id))

        conn.commit()
        conn.close()

    def test_01_missing_env_vars_handled_gracefully(self):
        """
        Nghiệm thu 6: Thiếu biến môi trường -> Trang báo lỗi thân thiện, không 500 crash.
        """
        # Xóa các biến JaaS
        os.environ.pop("JAAS_APP_ID", None)
        os.environ.pop("JAAS_API_KEY", None)
        os.environ.pop("JAAS_PRIVATE_KEY", None)

        cfg = get_jaas_config()
        self.assertFalse(cfg["is_configured"])
        self.assertEqual(len(cfg["missing"]), 3)

        # Đăng nhập An (Người dạy) và vào phòng học
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/sessions/9998/room")
        self.assertEqual(res.status_code, 200, "Trang phòng học phải trả về 200 ngay cả khi thiếu biến môi trường")
        html = res.data.decode("utf-8")
        
        # Báo lỗi thân thiện hướng dẫn cấu hình
        self.assertIn("Chưa Được Cấu Hình", html)
        self.assertIn("JAAS_APP_ID", html)
        self.assertIn("JAAS_API_KEY", html)
        self.assertIn("JAAS_PRIVATE_KEY", html)

        # Route token khi thiếu biến môi trường trả về 503 (không crash 500)
        res_token = self.client.post("/phong-hoc/9998/token")
        self.assertEqual(res_token.status_code, 503)
        data = res_token.get_json()
        self.assertIn("chưa cấu hình đầy đủ", data.get("error", "").lower())

    def test_02_escaped_newlines_handled(self):
        """
        Nghiệm thu 1: JAAS_PRIVATE_KEY chứa \\n escape được code tự chuyển thành xuống dòng thật.
        """
        escaped_pem = self.test_pem_private.replace("\n", "\\n")
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = escaped_pem

        cfg = get_jaas_config()
        self.assertTrue(cfg["is_configured"])
        self.assertIn("\n", cfg["private_key"], "Private key phải chứa newline thật sau khi unescape")
        self.assertTrue(cfg["private_key"].startswith("-----BEGIN"))

    def test_03_jwt_token_generation_and_roles(self):
        """
        Nghiệm thu 2, 3:
        - Sinh JWT RS256: header kid, payload aud, iss, sub, room="*", exp=now+2h.
        - Tên hiển thị = họ tên thật từ DB.
        - Người dạy có quyền moderator = True; Người học moderator = False.
        """
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private

        # Lấy tên thật từ DB để đối chiếu
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT ho_ten FROM users WHERE id = ?", (self.an_id,))
        expected_an_name = cur.fetchone()[0]
        cur.execute("SELECT ho_ten FROM users WHERE id = ?", (self.binh_id,))
        expected_binh_name = cur.fetchone()[0]
        conn.close()

        # 1. An (Người dạy) lấy token
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_an = self.client.post("/phong-hoc/9998/token")
        self.assertEqual(res_an.status_code, 200)
        data_an = res_an.get_json()
        self.assertTrue(data_an["success"])
        token_an = data_an["token"]

        # Kiểm tra JWT Header và Payload của Người dạy
        unverified_headers = jwt.get_unverified_header(token_an)
        self.assertEqual(unverified_headers.get("alg"), "RS256")
        self.assertEqual(unverified_headers.get("kid"), self.test_api_key)

        decoded_an = jwt.decode(token_an, self.test_pem_public, algorithms=["RS256"], audience="jitsi")
        self.assertEqual(decoded_an["aud"], "jitsi")
        self.assertEqual(decoded_an["iss"], "chat")
        self.assertEqual(decoded_an["sub"], self.test_app_id)
        self.assertEqual(decoded_an["room"], "*")
        self.assertGreater(decoded_an["exp"], time.time() + 7000)

        user_an = decoded_an["context"]["user"]
        self.assertEqual(user_an["name"], expected_an_name)  # Họ tên thật từ DB
        self.assertEqual(user_an["email"], "HS12001")
        self.assertTrue(user_an["moderator"], "Người dạy phải có quyền moderator = True")

        # 2. Bình (Người học) lấy token
        client_binh = app.test_client()
        client_binh.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)
        res_binh = client_binh.post("/phong-hoc/9998/token")
        self.assertEqual(res_binh.status_code, 200)
        data_binh = res_binh.get_json()
        token_binh = data_binh["token"]

        decoded_binh = jwt.decode(token_binh, self.test_pem_public, algorithms=["RS256"], audience="jitsi")
        user_binh = decoded_binh["context"]["user"]
        self.assertEqual(user_binh["name"], expected_binh_name)  # Họ tên thật từ DB
        self.assertEqual(user_binh["email"], "HS11002")
        self.assertFalse(user_binh["moderator"], "Người học phải có moderator = False")

    def test_04_unauthorized_user_forbidden(self):
        """
        Nghiệm thu: User không thuộc buổi học gọi /phong-hoc/<id>/token bị từ chối 403.
        """
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private

        # Chi (HS10003) không thuộc session 9998
        client_chi = app.test_client()
        client_chi.post("/login", data={"ma_hoc_sinh": "HS10003", "mat_khau": "admin123"}, follow_redirects=True)
        res_chi = client_chi.post("/phong-hoc/9998/token")
        self.assertEqual(res_chi.status_code, 403, "Học sinh không thuộc phiên học phải bị chặn 403 Forbidden")

    def test_05_token_session_isolation_and_expiration(self):
        """
        Nghiệm thu 4:
        - Token buổi A không dùng cho buổi B.
        - Token hết hạn bị từ chối.
        """
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private

        # Sinh token hợp lệ cho session 9998
        token_a, err = generate_jaas_jwt(
            session_id=9998,
            user_id=self.an_id,
            user_name="Trần An",
            user_email="HS12001",
            is_moderator=True
        )
        self.assertIsNone(err)

        # 1. Dùng token buổi 9998 cho buổi 9998 -> Hợp lệ
        valid_same, msg_same, _ = verify_jaas_token(token_a, expected_session_id=9998, public_key=self.test_pem_public)
        self.assertTrue(valid_same)

        # 2. Mang token buổi 9998 sang dùng cho buổi 9999 -> BỊ TỪ CHỐI
        valid_diff, msg_diff, _ = verify_jaas_token(token_a, expected_session_id=9999, public_key=self.test_pem_public)
        self.assertFalse(valid_diff, "Token buổi A không được dùng cho buổi B")
        self.assertIn("không khớp", msg_diff.lower())

        # 3. Token hết hạn (exp trong quá khứ) -> BỊ TỪ CHỐI
        expired_payload = {
            "aud": "jitsi",
            "iss": "chat",
            "sub": self.test_app_id,
            "room": "*",
            "exp": int(time.time()) - 100,  # Đã hết hạn
            "session_id": 9998,
            "context": {"user": {"name": "Trần An", "email": "HS12001", "moderator": True}}
        }
        expired_token = jwt.encode(
            expired_payload,
            self.test_pem_private,
            algorithm="RS256",
            headers={"kid": self.test_api_key}
        )
        valid_exp, msg_exp, _ = verify_jaas_token(expired_token, expected_session_id=9998, public_key=self.test_pem_public)
        self.assertFalse(valid_exp, "Token hết hạn phải bị từ chối")
        self.assertIn("hết hạn", msg_exp.lower())

    def test_06_frontend_jaas_elements_and_no_old_iframe(self):
        """
        Nghiệm thu 3, 5:
        - Iframe meet.jit.si cũ bị xóa bỏ hoàn toàn.
        - Khung JaaS External API (#jaas-meet-container) và script tích hợp hiện diện.
        - Luật 80%, Điểm danh, Báo cáo, Dàn ý AI, Đồng hồ được giữ nguyên vẹn.
        """
        os.environ["JAAS_APP_ID"] = self.test_app_id
        os.environ["JAAS_API_KEY"] = self.test_api_key
        os.environ["JAAS_PRIVATE_KEY"] = self.test_pem_private

        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/phong-hoc/9998")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # KHÔNG còn iframe meet.jit.si
        self.assertNotIn("https://meet.jit.si", html, "Iframe meet.jit.si cũ phải bị gỡ bỏ hoàn toàn")

        # Có vùng chứa JaaS External API và script fetch token
        self.assertIn("jaas-meet-container", html)
        self.assertIn("/phong-hoc/9998/token", html)
        self.assertIn("8x8.vc", html)

        # Bảo toàn nghiệp vụ sư phạm
        self.assertIn("Tiêu Chuẩn Chuyển Giờ", html)
        self.assertIn("Tiêu chí ≥ 80%", html)
        self.assertIn("reportViolationModal", html)  # Nút báo cáo vi phạm
        self.assertIn("roomTimer", html)             # Đồng hồ bấm giờ
        self.assertIn("Kết thúc buổi học", html)


if __name__ == "__main__":
    unittest.main()
