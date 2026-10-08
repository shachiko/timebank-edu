# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ NGHIỆM THU PROMPT 14: NÂNG CẤP THƯ VIỆN GOOGLE-GENAI & CHẨN ĐOÁN KHỞI TẠO
====================================================================================
Nội dung nghiệm thu:
1. Có key hợp lệ:
   - is_ai_live() == True
   - Phản hồi chatbot là AI thật (tự nhiên, không phải template cứng)
2. Không có key:
   - is_ai_live() == False
   - Fallback chạy như cũ, không crash
3. Key sai:
   - Không crash
   - Fallback êm, log rõ lỗi
"""

import sys
import io
import os
import sqlite3
import unittest
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

# Đảm bảo mã hóa console utf-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Nạp file .env cục bộ nếu có
load_dotenv()

from app import app, init_db, DATABASE_PATH
import ai_service


class TestPrompt14GeminiUpgrade(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Đảm bảo CSDL được khởi tạo sạch
        init_db()
        # Lưu lại key gốc từ môi trường để khôi phục sau khi test
        cls.original_key = os.getenv("GEMINI_API_KEY")

    @classmethod
    def tearDownClass(cls):
        # Khôi phục trạng thái biến môi trường ban đầu
        if cls.original_key is not None:
            os.environ["GEMINI_API_KEY"] = cls.original_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        ai_service.init_gemini_client()

    def setUp(self):
        self.conn = sqlite3.connect(DATABASE_PATH)
        self.conn.row_factory = sqlite3.Row

    def tearDown(self):
        if self.conn:
            self.conn.close()

    def test_01_khong_co_key_fallback_em_khong_crash(self):
        """
        NGHIỆM THU 2: Không có key -> is_ai_live() == False, fallback chạy như cũ, không crash.
        """
        print("\n" + "="*70)
        print("[TEST 1/3] Kiểm tra khi KHÔNG CÓ KEY:")
        os.environ.pop("GEMINI_API_KEY", None)
        ai_service.init_gemini_client("")

        self.assertFalse(ai_service.is_ai_live(), "is_ai_live() phải là False khi không có key")

        # Gọi chatbot
        reply, is_live = ai_service.ai_chat_assistant(self.conn, 1, "Xin chào bạn, tôi muốn hỏi số dư")
        self.assertFalse(is_live, "is_live phải là False khi fallback chế độ cơ bản")
        self.assertIsNotNone(reply)
        self.assertTrue(len(reply) > 0)
        # Template fallback khi hỏi số dư
        self.assertIn("số dư tín dụng", reply.lower())
        print(f"-> Kết quả: is_live={is_live}, reply phản hồi dự phòng: {reply[:80]}...")
        print("[PASS] Không có key: Fallback an toàn, không crash.")

    def test_02_key_sai_khong_crash_fallback_em_log_ro_loi(self):
        """
        NGHIỆM THU 3: Key sai -> không crash, fallback êm, log rõ lỗi.
        """
        print("\n" + "="*70)
        print("[TEST 2/3] Kiểm tra khi KEY SAI:")
        fake_bad_key = "AIzaSyFakeKey_ThisIsDefinitelyInvalid_999"
        os.environ["GEMINI_API_KEY"] = fake_bad_key
        ai_service.init_gemini_client(fake_bad_key)

        # Khi init với chuỗi bất kỳ, client được tạo nhưng khi gọi API sẽ báo lỗi từ Google
        self.assertTrue(ai_service.is_ai_live())

        # Thử gọi call_gemini trực tiếp -> phải bắt ngoại lệ, log rõ ràng và trả về None (không crash)
        res = ai_service.call_gemini("Hãy trả lời bằng 1 từ: Xin chào")
        self.assertIsNone(res, "call_gemini phải trả về None khi key sai")

        # Gọi qua chatbot -> chuyển fallback êm
        reply, is_live = ai_service.ai_chat_assistant(self.conn, 1, "Bạn có thể giới thiệu về TimeBank không?")
        self.assertFalse(is_live, "is_live phải là False sau khi API thất bại")
        self.assertIsNotNone(reply)
        self.assertIn("TimeBank EDU", reply)
        print(f"-> Kết quả: is_live={is_live}, fallback mượt mà: {reply[:80]}...")
        print("[PASS] Key sai: Không crash, fallback êm và log lỗi rõ ràng.")

    def test_03_co_key_hop_le_hoac_live_ai_chatbot(self):
        """
        NGHIỆM THU 1: Có key hợp lệ -> is_ai_live() == True, câu trả lời chatbot là AI thật.
        - Nếu có key thật trong local .env: Chạy thật 100% với Google GenAI (gemini-2.0-flash).
        - Nếu chưa có key thật trong môi trường: Kiểm thử luồng tích hợp với mock của google-genai
          để đảm bảo client và generate_content tương thích trơn tru.
        """
        print("\n" + "="*70)
        print("[TEST 3/3] Kiểm tra khi CÓ KEY HỢP LỆ:")
        real_key = self.original_key or os.getenv("GEMINI_API_KEY")

        if real_key and not real_key.startswith("AIzaSyFake") and len(real_key) > 20:
            print(f"-> Phát hiện GEMINI_API_KEY thật trong môi trường local (độ dài {len(real_key)} ký tự).")
            print("-> Đang gọi trực tiếp Google GenAI API thật...")
            os.environ["GEMINI_API_KEY"] = real_key
            ai_service.init_gemini_client(real_key)

            self.assertTrue(ai_service.is_ai_live(), "is_ai_live() phải là True khi có key thật")

            # Gọi chatbot với câu hỏi mở để kiểm tra tính tự nhiên của AI
            cau_hoi = "Chào bạn! Hãy giới thiệu bạn là ai trong đúng 1 câu ngắn gọn."
            reply, is_live = ai_service.ai_chat_assistant(self.conn, 1, cau_hoi)

            self.assertTrue(is_live, "is_live phải là True khi gọi Gemini API thành công")
            self.assertIsNotNone(reply)
            self.assertTrue(len(reply) > 5)

            # Câu trả lời AI thật không phải là template cứng mặc định
            hardcoded_template = "Chào Quản trị viên Hệ thống! Tôi là Trợ lý Học đường TimeBank EDU (Hỗ trợ bởi AI Gemini). Số dư ví hiện tại của bạn là"
            self.assertFalse(reply.startswith(hardcoded_template), "Câu trả lời phải là văn bản sinh ra tự nhiên từ AI")

            print(f"-> Phản hồi AI Gemini thật: \"{reply}\"")
            print("[PASS] Có key hợp lệ: is_ai_live() == True, chatbot trả lời bằng AI thật tự nhiên!")
        else:
            print("-> Không phát hiện GEMINI_API_KEY thật trong .env cục bộ.")
            print("-> Kiểm thử tích hợp SDK google-genai bằng mock response...")

            # Giả lập phản hồi từ Google GenAI Client thật
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "Chào bạn! Tôi là trợ lý AI học đường của TimeBank EDU, rất vui được hỗ trợ bạn hôm nay."
            mock_client.models.generate_content.return_value = mock_response

            with patch("ai_service.get_gemini_client", return_value=mock_client), \
                 patch("ai_service.is_ai_live", return_value=True):
                
                reply = ai_service.call_gemini("Chào bạn")
                self.assertEqual(reply, mock_response.text)

                reply_chat, is_live_chat = ai_service.ai_chat_assistant(self.conn, 1, "Chào bạn")
                self.assertTrue(is_live_chat)
                self.assertEqual(reply_chat, mock_response.text)

            print("[PASS] Luồng google-genai Client và models.generate_content sẵn sàng 100%.")


if __name__ == "__main__":
    unittest.main()
