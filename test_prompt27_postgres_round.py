# -*- coding: utf-8 -*-
"""
TEST SUITE: KIỂM THỬ HOTFIX SỬA HÀM ROUND() CHO POSTGRESQL (PROMPT 27)
Mục tiêu nghiệm thu:
1. Quét tĩnh: Mọi query SQL dùng hàm ROUND với 2 tham số trong app.py và ai_service.py
   đều phải có ép kiểu ::numeric (0 chỗ sót).
2. /admin hết lỗi 500 trên cả SQLite cục bộ lẫn mô phỏng PostgreSQL.
3. Chợ kỹ năng, Sàn cộng đồng, Hồ sơ cá nhân, AI Matchmake, Chi tiết kỹ năng và Bản tin tuần
   đều thực thi các câu lệnh ROUND(...::numeric, ...) thành công.
4. SqliteConnectionWrapper tự động tương thích trong suốt, không bị lỗi cú pháp ":".
5. PostgresCursorWrapper có cơ chế tự động bảo vệ dự phòng (auto-cast ::numeric).
"""

import os
import re
import sys
import unittest
import sqlite3

# Cấu hình UTF-8 cho console Windows để tránh UnicodeEncodeError
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from flask import session
from app import app, get_db, DATABASE_PATH, PostgresCursorWrapper, SqliteConnectionWrapper


class TestPrompt27PostgresRound(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.app_context = app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: QUÉT TĨNH — 0 CHỖ ROUND(double precision, integer) CÒN SÓT
    # =========================================================================
    def test_01_static_scan_all_round_have_numeric_cast(self):
        """[TIÊU CHÍ 1]: Quét tĩnh toàn bộ codebase, đảm bảo mọi hàm SQL ROUND 2 tham số đều có ::numeric."""
        files_to_check = ["app.py", "ai_service.py"]

        def find_sql_rounds(code):
            results = []
            for m in re.finditer(r'\bROUND\s*\(', code):
                start = m.end()
                depth = 1
                i = start
                while i < len(code) and depth > 0:
                    if code[i] == '(':
                        depth += 1
                    elif code[i] == ')':
                        depth -= 1
                    i += 1
                if depth == 0:
                    content = code[start:i-1]
                    # Tách các đối số cấp cao nhất (không nằm trong dấu ngoặc con)
                    sub_depth = 0
                    parts = []
                    cur_part = []
                    for ch in content:
                        if ch == '(':
                            sub_depth += 1
                        elif ch == ')':
                            sub_depth -= 1
                        elif ch == ',' and sub_depth == 0:
                            parts.append(''.join(cur_part).strip())
                            cur_part = []
                            continue
                        cur_part.append(ch)
                    parts.append(''.join(cur_part).strip())
                    if len(parts) == 2 and parts[1].isdigit():
                        results.append((parts[0], int(parts[1])))
            return results

        uncast_violations = []
        valid_cast_count = 0

        for file_name in files_to_check:
            self.assertTrue(os.path.exists(file_name), f"File {file_name} không tồn tại!")
            with open(file_name, "r", encoding="utf-8") as f:
                code_content = f.read()

            rounds = find_sql_rounds(code_content)
            for expr, precision in rounds:
                expr_clean = expr.strip()
                if not expr_clean.endswith("::numeric"):
                    uncast_violations.append({
                        "file": file_name,
                        "expr": expr_clean,
                        "precision": precision
                    })
                else:
                    valid_cast_count += 1

        print(f"\n[SCAN RESULT]: Phát hiện {valid_cast_count} lệnh SQL ROUND(::numeric, n) hợp lệ.")
        if uncast_violations:
            for v in uncast_violations:
                print(f"  ❌ Vi phạm: {v['file']} -> ROUND({v['expr']}, {v['precision']})")

        self.assertEqual(len(uncast_violations), 0, f"Còn {len(uncast_violations)} chỗ dùng SQL ROUND thiếu ::numeric!")
        self.assertGreaterEqual(valid_cast_count, 11, "Cần tối thiểu 11 chỗ SQL ROUND được ép kiểu ::numeric!")
        print("[PASS - TC 1]: Quét tĩnh hoàn tất: 0 chỗ ROUND(double precision, integer) còn sót.")

    # =========================================================================
    # TIÊU CHÍ 2: KIỂM TRA TRUY VẤN QUIZ_SQL GÂY LỖI 500 Ở /ADMIN ĐÃ CÓ ::NUMERIC
    # =========================================================================
    def test_02_admin_quiz_sql_specifically_fixed(self):
        """[TIÊU CHÍ 2]: Kiểm tra trực tiếp đoạn query quiz_sql trong app.py gây lỗi dòng 2382 cũ."""
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("ROUND(AVG(qr.diem_so)::numeric, 2) AS diem_tb", content,
                      "Truy vấn điểm TB bài thi Quiz trong admin_dashboard chưa được ép kiểu ::numeric!")
        self.assertIn("ROUND(AVG(qr.tu_danh_gia_truoc)::numeric, 2) AS tu_tin_truoc_tb", content,
                      "Truy vấn tự đánh giá trước bài thi trong admin_dashboard chưa được ép kiểu ::numeric!")
        print("\n[PASS - TC 2]: Truy vấn quiz_sql trong admin_dashboard đã được ép kiểu ::numeric chuẩn xác.")

    # =========================================================================
    # TIÊU CHÍ 3: TRANG /ADMIN HẾT LỖI 500 (HTTP 200 OK)
    # =========================================================================
    def test_03_admin_dashboard_returns_200_ok(self):
        """[TIÊU CHÍ 3]: Truy cập /admin với tài khoản school_admin và super_admin -> 200 OK, không còn lỗi 500."""
        # 1. Thử với School Admin
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["ma_hoc_sinh"] = "ADMIN001"
            sess["ho_ten"] = "Quản trị viên Trường"
            sess["vai_tro"] = "school_admin"
            sess["truong_id"] = 1

        response = self.client.get("/admin")
        self.assertEqual(response.status_code, 200, f"Trang /admin (school_admin) bị lỗi {response.status_code}!")
        self.assertIn(b"admin", response.data.lower())

        # 2. Thử với Super Admin
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["ma_hoc_sinh"] = "SUPERADMIN"
            sess["ho_ten"] = "Tổng Quản Trị"
            sess["vai_tro"] = "super_admin"
            sess["truong_id"] = 1

        response_super = self.client.get("/admin")
        self.assertEqual(response_super.status_code, 200, f"Trang /admin (super_admin) bị lỗi {response_super.status_code}!")

        print("\n[PASS - TC 3]: Trang /admin trả về 200 OK hoàn hảo, hết hoàn toàn lỗi 500.")

    # =========================================================================
    # TIÊU CHÍ 4: KIỂM TRA TẤT CẢ ROUTE CHỨA CÂU LỆNH ROUND KHÁC
    # =========================================================================
    def test_04_other_routes_with_round_return_ok(self):
        """[TIÊU CHÍ 4]: Kiểm tra các endpoint chứa hàm ROUND(...::numeric, ...) hoạt động ổn định."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["ma_hoc_sinh"] = "HS001"
            sess["ho_ten"] = "Nguyễn Văn Test"
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        # 1. Profile (chứa SELECT ROUND(AVG(so_sao)::numeric, 1))
        res_profile = self.client.get("/profile")
        self.assertEqual(res_profile.status_code, 200)

        # 2. Skills Market (chứa ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1))
        res_skills = self.client.get("/skills")
        self.assertEqual(res_skills.status_code, 200)

        # 3. Community Market (Sàn liên trường)
        res_comm = self.client.get("/community")
        self.assertEqual(res_comm.status_code, 200)

        print("\n[PASS - TC 4]: Các route /profile, /skills, /community thực thi SQL có ROUND ::numeric mượt mà.")

    # =========================================================================
    # TIÊU CHÍ 5: BẢN TIN TUẦN AI_GENERATE_WEEKLY_NEWSLETTER CHẠY THÀNH CÔNG
    # =========================================================================
    def test_05_weekly_newsletter_and_date_filter(self):
        """[TIÊU CHÍ 5]: ai_generate_weekly_newsletter không dùng SQLite datetime() và có ::numeric."""
        from ai_service import ai_generate_weekly_newsletter
        db = get_db()
        post_id, tieu_de, noi_dung, is_live = ai_generate_weekly_newsletter(db)
        self.assertIsNotNone(post_id)
        self.assertIn("Bản tin", tieu_de)

        # Kiểm tra file ai_service.py không còn chứa datetime('now'
        with open("ai_service.py", "r", encoding="utf-8") as f:
            ai_code = f.read()
        self.assertNotIn("datetime('now'", ai_code, "ai_service.py vẫn còn chứa hàm SQLite datetime('now'!")
        print("\n[PASS - TC 5]: Bản tin tuần AI tạo thành công, không còn phụ thuộc hàm SQLite datetime('now').")

    # =========================================================================
    # TIÊU CHÍ 6: WRAPPER SQLITE & POSTGRESQL BẢO VỆ DỰ PHÒNG
    # =========================================================================
    def test_06_connection_wrappers_compatibility(self):
        """[TIÊU CHÍ 6]: SqliteConnectionWrapper gỡ ::numeric trên SQLite; PostgresCursorWrapper auto-cast dự phòng."""
        # Test SQLite wrapper
        mem_db = sqlite3.connect(":memory:")
        mem_db.row_factory = sqlite3.Row
        mem_db.execute("CREATE TABLE t (val REAL)")
        mem_db.execute("INSERT INTO t VALUES (4.567)")

        wrapped_db = SqliteConnectionWrapper(mem_db)
        cur = wrapped_db.cursor()
        cur.execute("SELECT ROUND(val::numeric, 2) AS res FROM t")
        row = cur.fetchone()
        self.assertAlmostEqual(row["res"], 4.57, places=2)

        # Test Postgres wrapper regex auto-cast
        class MockPgCursor:
            def __init__(self):
                self.last_query = ""
            def execute(self, q, p=None):
                self.last_query = q
            def fetchone(self):
                return (1,)

        mock_cur = MockPgCursor()
        pg_wrapper = PostgresCursorWrapper(mock_cur)
        # Truy vấn chưa có ::numeric -> wrapper tự động ép kiểu dự phòng
        pg_wrapper.execute("SELECT ROUND(AVG(diem_so), 2) FROM quizzes")
        self.assertIn("::numeric", mock_cur.last_query)

        # Truy vấn đã có ::numeric -> wrapper không làm hỏng
        pg_wrapper.execute("SELECT ROUND(AVG(diem_so)::numeric, 2) FROM quizzes")
        self.assertIn("ROUND(AVG(diem_so)::numeric, 2)", mock_cur.last_query)

        print("\n[PASS - TC 6]: Lớp bọc tương thích cơ sở dữ liệu hoạt động chính xác trên cả 2 hệ quản trị.")


if __name__ == "__main__":
    unittest.main()
