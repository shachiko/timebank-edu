# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M-CHAT
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Nội dung kiểm thử Milestone M-CHAT (Trợ lý Học đường AI - Chatbot):
1. NHẮC LỊCH CHỦ ĐỘNG: Mở khung chat -> thấy nhắc lịch hẹn sắp tới (đọc từ sessions 'da_dat') và số dư ví.
2. HỎI SỐ DƯ: Hỏi "Tôi còn bao nhiêu giờ?" -> trả lời chính xác số dư thật của học sinh.
3. LỊCH SỬ CHAT LƯU LẠI: Tin nhắn được ghi nhận vào bảng chat_messages (vai_tro 'user'/'assistant'), tải lại trang vẫn còn.
4. GỢI Ý CÂU HỎI NHANH: Trả lời chuẩn xác các câu hỏi FAQ và lộ trình học Toán trong 4 tuần.
5. MINH BẠCH AI: Nhật ký tương tác được lưu vào bảng ai_logs (chuc_nang = 'tro_ly_ao').
6. BẢO VỆ PHIÊN ĐĂNG NHẬP: Chưa đăng nhập không thể truy cập API chat.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import unittest
import sqlite3
import json
from pathlib import Path

# Đảm bảo đường dẫn import app
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app, init_db, DATABASE_PATH, get_db
from ai_service import ai_chat_assistant, get_chat_greeting_and_reminder


class TestMilestoneMChat(unittest.TestCase):
    def setUp(self):
        """Khởi tạo môi trường kiểm thử với test client và nạp lại CSDL sạch"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Tạo lại cơ sở dữ liệu mẫu ban đầu
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
        init_db()

    def login(self, username, password="admin123"):
        """Hàm trợ giúp đăng nhập sạch phiên"""
        self.client.get("/logout", follow_redirects=True)
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def test_01_chat_greeting_and_upcoming_reminder(self):
        """
        [TEST CASE 1]: NHẮC LỊCH CHỦ ĐỘNG:
        Mỗi lần mở khung chat (/api/chat/history), Trợ lý chủ động hiện:
        'Bạn có N lịch hẹn sắp tới: ...' đọc từ sessions 'da_dat'.
        """
        # Thêm 1 lịch hẹn 'da_dat' cho học sinh An (id=3)
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai)
            VALUES (1, 3, 4, '2026-10-15 14:00:00', 1.0, 'da_dat')
        """)
        conn.commit()
        conn.close()

        # Học sinh An (HS12001) đăng nhập và gọi API lịch sử chat
        self.login("HS12001")
        resp = self.client.get("/api/chat/history")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()

        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("upcoming_count"), 1)
        self.assertIn("lịch hẹn sắp tới", data.get("greeting", ""))
        self.assertIn("1", data.get("greeting", ""))

    def test_02_ask_credit_balance_returns_exact_number(self):
        """
        [TEST CASE 2]: HỎI SỐ DƯ TÍN DỤNG:
        Học sinh hỏi 'Tôi còn bao nhiêu giờ?' -> Trợ lý trả lời chính xác số dư thực tế trong ví.
        """
        self.login("HS12001") # An có số dư ban đầu là 3.5h

        resp = self.client.post("/api/chat/send", json={
            "message": "Tôi còn bao nhiêu giờ?"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        reply = data.get("reply", "")

        # Kiểm tra trả lời đúng số dư thật (3.5)
        self.assertIn("3.5", reply)

        # Cập nhật số dư của An lên 5.5h và kiểm tra lại
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET so_du_gio = 5.5 WHERE id = 3")
        conn.commit()
        conn.close()

        resp2 = self.client.post("/api/chat/send", json={
            "message": "Kiểm tra ví của tôi còn bao nhiêu credit?"
        })
        self.assertEqual(resp2.status_code, 200)
        reply2 = resp2.get_json().get("reply", "")
        self.assertIn("5.5", reply2)

    def test_03_chat_history_persisted_in_database(self):
        """
        [TEST CASE 3]: LỊCH SỬ CHAT LƯU LẠI TRONG CSDL:
        Các câu hỏi và câu trả lời được lưu vào bảng chat_messages (vai_tro 'user'/'assistant'),
        khi tải lại trang (/api/chat/history) lịch sử vẫn đầy đủ.
        """
        self.login("HS12001")
        question = "Làm sao để đăng ký kỹ năng mới?"
        self.client.post("/api/chat/send", json={"message": question})

        # Kiểm tra trực tiếp bảng chat_messages trong SQLite
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM chat_messages WHERE user_id = 3 ORDER BY id DESC LIMIT 2")
        rows = cur.fetchall()
        self.assertEqual(len(rows), 2)
        # Bản ghi mới nhất là assistant, trước đó là user
        self.assertEqual(rows[0]["vai_tro"], "assistant")
        self.assertEqual(rows[1]["vai_tro"], "user")
        self.assertEqual(rows[1]["noi_dung"], question)
        conn.close()

        # Gọi lại API lịch sử chat (giả lập F5 / tải lại trang)
        resp = self.client.get("/api/chat/history")
        data = resp.get_json()
        messages = data.get("messages", [])
        user_msgs = [m["noi_dung"] for m in messages if m["vai_tro"] == "user"]
        self.assertIn(question, user_msgs)

    def test_04_quick_prompts_and_math_roadmap(self):
        """
        [TEST CASE 4]: CÂU HỎI NHANH & LỘ TRÌNH HỌC TOÁN 4 TUẦN:
        Trợ lý cung cấp lộ trình học tập sư phạm rõ ràng theo 4 tuần.
        """
        self.login("HS12001")
        resp = self.client.post("/api/chat/send", json={
            "message": "Gợi ý lộ trình học Toán trong 4 tuần?"
        })
        self.assertEqual(resp.status_code, 200)
        reply = resp.get_json().get("reply", "")

        # Kiểm tra nội dung chứa đủ 4 tuần
        self.assertIn("Tuần 1", reply)
        self.assertIn("Tuần 2", reply)
        self.assertIn("Tuần 3", reply)
        self.assertIn("Tuần 4", reply)

    def test_05_ai_logs_transparency_for_chat(self):
        """
        [TEST CASE 5]: MINH BẠCH TƯƠNG TÁC AI:
        Mọi tương tác trong khung chat đều được lưu vào bảng ai_logs (chuc_nang = 'tro_ly_ao').
        """
        self.login("HS12001")
        self.client.post("/api/chat/send", json={
            "message": "Lịch học sắp tới của tôi?"
        })

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ai_logs WHERE user_id = 3 AND chuc_nang = 'tro_ly_ao'")
        count = cur.fetchone()[0]
        self.assertGreater(count, 0)
        conn.close()

    def test_06_unauthenticated_user_access_blocked(self):
        """
        [TEST CASE 6]: BẢO VỆ PHIÊN ĐĂNG NHẬP:
        Người dùng chưa đăng nhập gọi API chat sẽ bị chặn (chuyển hướng sang /login).
        """
        self.client.get("/logout", follow_redirects=True)
        resp_history = self.client.get("/api/chat/history")
        self.assertEqual(resp_history.status_code, 302)

        resp_send = self.client.post("/api/chat/send", json={"message": "Chào bạn"})
        self.assertEqual(resp_send.status_code, 302)


if __name__ == "__main__":
    unittest.main(verbosity=2)
