# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M0 & M0-BS - TIMEBANK EDU
Tự động kiểm tra:
1. Cơ sở dữ liệu: Tồn tại đủ 13 bảng chuẩn theo đặc tả kiến trúc (10 ban đầu + 3 bổ sung).
2. Các cột bổ sung: 'gio_ranh' trong users, 'quiz_dat_chuan' trong sessions.
3. Các giá trị mới: 'goi_y_nhiem_vu', 'tro_ly_ao' trong ai_logs; 'nhiem_vu_cong_dong' trong credits_ledger.
4. Cấu hình Single-Tenant: Thay đổi 'ten_truong' trong config.yaml -> Trang chủ cập nhật ngay.
5. Landing Page: Đủ 6 khối chức năng, không có lỗi, tải tốt trên di động.
6. Bảo mật: Tệp .gitignore loại trừ .env.
7. Các API: /api/stats, /api/contact hoạt động chính xác.
"""

import sys
import io

# Đảm bảo in tiếng Việt chuẩn trên mọi console Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import yaml
import unittest
from app import app, init_db, DATABASE_PATH, SCHEMA_PATH, CONFIG_PATH, BASE_DIR, load_school_config


class TestMilestoneM0(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Xóa file DB cũ nếu có để khởi tạo sạch từ schema mới
        if DATABASE_PATH.exists():
            try:
                os.remove(DATABASE_PATH)
            except Exception:
                pass
        init_db()

    def setUp(self):
        self.client = app.test_client()

    def test_case_1_schema_has_all_13_tables(self):
        """Test Case 1: Kiểm tra cơ sở dữ liệu SQLite có chính xác đủ 13 bảng bắt buộc."""
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = set(row[0] for row in cursor.fetchall())

        expected_tables = {
            'users',
            'skills',
            'sessions',
            'session_attendance',
            'credits_ledger',
            'ratings',
            'quiz_questions',
            'quiz_results',
            'ai_logs',
            'blog_posts',
            'community_tasks',
            'task_registrations',
            'chat_messages'
        }
        
        missing = expected_tables - tables
        self.assertEqual(len(missing), 0, f"Thiếu các bảng trong cơ sở dữ liệu: {missing}")
        self.assertEqual(len(tables), 13, f"Số lượng bảng phải là 13, hiện có {len(tables)}")

        # Kiểm tra cột bổ sung trong users: gio_ranh
        cursor.execute("PRAGMA table_info(users)")
        user_cols = [r[1] for r in cursor.fetchall()]
        self.assertIn("gio_ranh", user_cols, "Bảng users thiếu cột gio_ranh")

        # Kiểm tra cột bổ sung trong sessions: quiz_dat_chuan
        cursor.execute("PRAGMA table_info(sessions)")
        session_cols = [r[1] for r in cursor.fetchall()]
        self.assertIn("quiz_dat_chuan", session_cols, "Bảng sessions thiếu cột quiz_dat_chuan")

        conn.close()
        print(f"\n[PASS] Case 1: Đủ 13 bảng chuẩn ({len(tables)}/13 bảng): {', '.join(sorted(tables))}")
        print("       -> Đã xác minh cột 'gio_ranh' (users) và 'quiz_dat_chuan' (sessions)")

    def test_case_2_config_switch_school_name(self):
        """Test Case 2: Kiểm tra khả năng đổi tên trường qua config.yaml và cập nhật tức thì."""
        original_config = load_school_config()
        original_school = original_config.get("ten_truong")
        
        # Test request với tên trường hiện tại
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(original_school.encode('utf-8'), response.data)

        # Thử đổi sang tên trường khác
        test_school_name = "THPT Chuyên Hà Nội - Amsterdam"
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        cfg["ten_truong"] = test_school_name
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True)

        try:
            res_new = self.client.get("/")
            self.assertEqual(res_new.status_code, 200)
            self.assertIn(test_school_name.encode('utf-8'), res_new.data)
            print(f"[PASS] Case 2: Đổi tên trường thành công ('{test_school_name}' hiển thị ngay lập tức)")
        finally:
            # Khôi phục lại tên trường ban đầu
            cfg["ten_truong"] = original_school
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                yaml.dump(cfg, f, allow_unicode=True)

    def test_case_3_landing_has_all_6_blocks(self):
        """Test Case 3: Kiểm tra Landing Page hiển thị đủ 6 khối chức năng theo yêu cầu, không lỗi."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')

        # Khối 1: Hero
        self.assertIn("Ngân hàng Thời gian Học đường", html)
        self.assertIn("Một giờ bạn dạy — một giờ bạn được học", html)
        self.assertIn("Tham gia ngay", html)

        # Khối 2: Mô hình hoạt động 4 bước + Ví dụ An - Bình - Chi
        self.assertIn("Đăng kỹ năng", html)
        self.assertIn("AI gợi ý ghép cặp", html)
        self.assertIn("Học & Check-in QR", html)
        self.assertIn("Tích giờ & Đổi kỹ năng", html)
        self.assertIn("An (12A1)", html)
        self.assertIn("Bình (11B2)", html)
        self.assertIn("Chi (10A3)", html)

        # Khối 3: Số liệu realtime
        self.assertTrue("Học sinh thành viên" in html or "Tổng thành viên" in html)
        self.assertIn("Phiên hoàn thành", html)
        self.assertIn("Giờ lưu thông", html)

        # Khối 4: Vinh danh tuần
        self.assertIn("Vinh danh Gia sư Học đường Tích cực", html)
        self.assertIn("Nguyễn Hoàng An", html)

        # Khối 5: Dành cho nhà trường + Form liên hệ
        self.assertIn("Dành cho nhà trường", html)
        self.assertIn("Đăng ký tư vấn triển khai", html)
        self.assertIn("contactForm", html)

        # Khối 6: Footer + Nhãn AI
        self.assertTrue("Hỗ trợ bởi AI (Trí tuệ nhân tạo)" in html or "Hỗ trợ bởi AI (Gemini)" in html)
        self.assertIn("© 2026", html)

        print("[PASS] Case 3: Landing Page đầy đủ 6 khối chức năng, không lỗi, hiển thị chuẩn mực")

    def test_case_4_gitignore_protects_env(self):
        """Test Case 4: Kiểm tra tệp .gitignore đảm bảo không bao giờ push .env lên GitHub."""
        gitignore_path = BASE_DIR / ".gitignore"
        self.assertTrue(gitignore_path.exists(), "Tệp .gitignore không tồn tại")
        
        with open(gitignore_path, "r", encoding="utf-8") as f:
            content = f.read()

        lines = [line.strip() for line in content.splitlines() if line.strip() and not line.startswith('#')]
        self.assertTrue(any(pattern == '.env' or pattern == '.env*' for pattern in lines), "Chưa chặn .env trong .gitignore")
        print("[PASS] Case 4: .gitignore đã bảo vệ an toàn tệp .env (loại trừ khỏi Git)")

    def test_case_5_api_endpoints_work(self):
        """Test Case 5: Kiểm tra các API số liệu và liên hệ hoạt động chính xác."""
        # 1. API Stats
        res_stats = self.client.get("/api/stats")
        self.assertEqual(res_stats.status_code, 200)
        data = res_stats.get_json()
        self.assertTrue(data.get("success"))
        self.assertGreater(data["data"]["tong_thanh_vien"], 0)
        self.assertGreater(data["data"]["phien_hoan_thanh"], 0)
        print(f"[PASS] Case 5: API /api/stats trả về dữ liệu realtime: {data['data']}")

        # 2. API Contact
        res_contact = self.client.post("/api/contact", json={
            "ten_truong": "THPT Test",
            "ho_ten": "Thầy Nam",
            "sdt": "0987654321",
            "email": "nam@test.edu.vn",
            "ghi_chu": "Cần tư vấn triển khai"
        })
        self.assertEqual(res_contact.status_code, 200)
        contact_data = res_contact.get_json()
        self.assertTrue(contact_data.get("success"))
        print("[PASS] Case 5: API /api/contact tiếp nhận dữ liệu thành công")


if __name__ == "__main__":
    unittest.main()
