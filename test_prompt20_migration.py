# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG CHUYÊN SÂU — PROMPT 20:
HOTFIX: MIGRATE POSTGRESQL PRODUCTION (P17–P19)

Tiêu chí nghiệm thu:
1. Chạy init_db() 2 lần liên tiếp trên SQLite local → không lỗi, không mất dữ liệu.
2. Viết test mô phỏng: tạo DB SQLite với schema CŨ (không có các cột mới),
   chạy hàm migrate → kiểm tra đủ cột, dữ liệu cũ còn nguyên, truong_id = 1.
3. Kiểm tra tính Idempotent: chạy hàm migrate_postgres_schema nhiều lần liên tiếp không lỗi,
   không nhân đôi dữ liệu.
4. Kiểm tra mô phỏng PostgreSQL: ghi nhận chính xác các câu lệnh ADD COLUMN IF NOT EXISTS,
   DROP CONSTRAINT / ADD CONSTRAINT qua information_schema và pg_constraint.
5. Toàn bộ test P17, P18, P19 vẫn pass nguyên vẹn.
"""

import unittest
import sqlite3
import os
from unittest.mock import MagicMock
from app import (
    app, init_db, migrate_postgres_schema,
    PostgresConnectionWrapper, PostgresCursorWrapper,
    DATABASE_PATH
)

class TestPrompt20PostgresMigration(unittest.TestCase):
    def setUp(self):
        # Thiết lập in-memory SQLite connection với schema CŨ (pre-P17)
        self.old_db = sqlite3.connect(":memory:")
        self.old_db.row_factory = sqlite3.Row
        self._create_legacy_pre_p17_schema(self.old_db)

    def tearDown(self):
        self.old_db.close()

    def _create_legacy_pre_p17_schema(self, conn):
        """
        Tạo schema CŨ của hệ thống thời điểm trước Prompt 17:
        - Bảng users: KHÔNG có truong_id, KHÔNG có trang_thai.
        - Bảng skills: KHÔNG có truong_id, KHÔNG có 4 cột sàn chung (hien_thi_cong_dong, v.v.).
        - Bảng sessions, ratings, community_tasks, task_registrations, blog_posts: KHÔNG có truong_id.
        - Chưa có bảng truong.
        """
        cur = conn.cursor()

        # 1. users cũ
        cur.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ma_hoc_sinh TEXT UNIQUE NOT NULL,
                ho_ten TEXT NOT NULL,
                lop TEXT,
                vai_tro TEXT CHECK(vai_tro IN ('hoc_sinh', 'giao_vien', 'admin')) DEFAULT 'hoc_sinh',
                so_du_gio REAL DEFAULT 2.0,
                gio_ranh TEXT,
                mat_khau TEXT
            );
        """)

        # 2. skills cũ
        cur.execute("""
            CREATE TABLE skills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                linh_vuc TEXT NOT NULL,
                tieu_de TEXT NOT NULL,
                mo_ta TEXT,
                trang_thai_duyet TEXT CHECK(trang_thai_duyet IN ('cho_duyet', 'da_duyet', 'tu_choi')) DEFAULT 'cho_duyet',
                ly_do_ai_kiem_duyet TEXT
            );
        """)

        # 3. sessions cũ
        cur.execute("""
            CREATE TABLE sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                skill_id INTEGER,
                nguoi_day_id INTEGER NOT NULL,
                nguoi_hoc_id INTEGER NOT NULL,
                thoi_gian_bat_dau TEXT,
                so_gio REAL DEFAULT 1.0,
                trang_thai TEXT DEFAULT 'da_dat',
                ma_qr TEXT,
                checkin_day INTEGER DEFAULT 0,
                checkin_hoc INTEGER DEFAULT 0,
                dan_y_ai TEXT,
                quiz_dat_chuan INTEGER DEFAULT 0
            );
        """)

        # 4. ratings cũ
        cur.execute("""
            CREATE TABLE ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                nguoi_danh_gia_id INTEGER NOT NULL,
                nguoi_duoc_danh_gia_id INTEGER NOT NULL,
                so_sao INTEGER,
                nhan_xet TEXT
            );
        """)

        # 5. community_tasks cũ
        cur.execute("""
            CREATE TABLE community_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tieu_de TEXT NOT NULL,
                mo_ta TEXT,
                dia_diem TEXT,
                so_gio_thuong REAL DEFAULT 1.0,
                so_luong_toi_da INTEGER DEFAULT 5,
                han_dang_ky TEXT,
                nguoi_tao_id INTEGER NOT NULL,
                trang_thai TEXT DEFAULT 'mo_dang_ky',
                thoi_gian_tao TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 6. task_registrations cũ
        cur.execute("""
            CREATE TABLE task_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                trang_thai TEXT DEFAULT 'da_dang_ky',
                thoi_gian_dang_ky TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # 7. blog_posts cũ
        cur.execute("""
            CREATE TABLE blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tieu_de TEXT NOT NULL,
                noi_dung TEXT NOT NULL,
                anh_minh_hoa TEXT,
                tac_gia_ai INTEGER DEFAULT 0,
                trang_thai TEXT DEFAULT 'nhap',
                thoi_gian_dang TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Nạp dữ liệu cũ vào
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, mat_khau)
            VALUES ('admin', 'Quản trị viên Cũ', 'BGH', 'admin', 100.0, 'hash_admin')
        """)
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, mat_khau)
            VALUES ('HS12001', 'Nguyễn Hoàng An', '12A1', 'hoc_sinh', 5.5, 'hash_hs')
        """)
        cur.execute("""
            INSERT INTO skills (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet)
            VALUES (2, 'Toán học', 'Ôn tập Hình học', 'Hình học không gian', 'da_duyet')
        """)
        cur.execute("""
            INSERT INTO sessions (skill_id, nguoi_day_id, nguoi_hoc_id, so_gio, trang_thai)
            VALUES (1, 2, 1, 2.0, 'hoan_thanh')
        """)
        cur.execute("""
            INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
            VALUES (1, 1, 2, 5, 'Dạy rất tốt')
        """)
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, nguoi_tao_id)
            VALUES ('Hỗ trợ thư viện', 1)
        """)
        cur.execute("""
            INSERT INTO task_registrations (task_id, user_id)
            VALUES (1, 2)
        """)
        cur.execute("""
            INSERT INTO blog_posts (tieu_de, noi_dung)
            VALUES ('Bản tin khai giảng', 'Nội dung bản tin cũ')
        """)

        conn.commit()

    def test_01_sqlite_migration_from_old_schema(self):
        """
        TIÊU CHÍ 2: Tạo DB SQLite với schema CŨ (không có các cột mới),
        chạy hàm migrate → kiểm tra đủ cột, dữ liệu cũ còn nguyên, truong_id = 1.
        """
        cur = self.old_db.cursor()

        # Xác minh trước migrate: chưa có các cột mới
        cur.execute("PRAGMA table_info(users)")
        u_cols_before = [r["name"] for r in cur.fetchall()]
        self.assertNotIn("truong_id", u_cols_before)
        self.assertNotIn("trang_thai", u_cols_before)

        cur.execute("PRAGMA table_info(skills)")
        sk_cols_before = [r["name"] for r in cur.fetchall()]
        self.assertNotIn("truong_id", sk_cols_before)
        self.assertNotIn("hien_thi_cong_dong", sk_cols_before)

        # Chạy migrate_postgres_schema trên kết nối CSDL cũ
        migrate_postgres_schema(self.old_db)

        # 1. Kiểm tra bảng truong đã được tạo và seed 4 trường
        cur.execute("SELECT COUNT(*) FROM truong")
        school_count = cur.fetchone()[0]
        self.assertEqual(school_count, 4, "Phải seed đủ 4 trường học khi bảng truong rỗng")

        cur.execute("SELECT id, ten_truong, trang_thai FROM truong ORDER BY id ASC")
        schools = cur.fetchall()
        self.assertEqual(schools[0]["id"], 1)
        self.assertIn("UK Academy", schools[0]["ten_truong"])
        self.assertEqual(schools[1]["id"], 2)
        self.assertIn("Nguyễn Văn Thuộc", schools[1]["ten_truong"])

        # 2. Kiểm tra các cột mới trong bảng users
        cur.execute("PRAGMA table_info(users)")
        u_cols_after = [r["name"] for r in cur.fetchall()]
        self.assertIn("truong_id", u_cols_after, "users phải có cột truong_id")
        self.assertIn("trang_thai", u_cols_after, "users phải có cột trang_thai")

        # 3. Kiểm tra các cột mới trong bảng skills
        cur.execute("PRAGMA table_info(skills)")
        sk_cols_after = [r["name"] for r in cur.fetchall()]
        self.assertIn("truong_id", sk_cols_after, "skills phải có cột truong_id")
        self.assertIn("hien_thi_cong_dong", sk_cols_after, "skills phải có hien_thi_cong_dong")
        self.assertIn("trang_thai_cong_dong", sk_cols_after, "skills phải có trang_thai_cong_dong")
        self.assertIn("nguoi_duyet_cong_dong_id", sk_cols_after, "skills phải có nguoi_duyet_cong_dong_id")
        self.assertIn("ngay_duyet_cong_dong", sk_cols_after, "skills phải có ngay_duyet_cong_dong")

        # 4. Kiểm tra truong_id trên các bảng khác
        for tbl in ["sessions", "ratings", "community_tasks", "task_registrations", "blog_posts"]:
            cur.execute(f"PRAGMA table_info({tbl})")
            cols = [r["name"] for r in cur.fetchall()]
            self.assertIn("truong_id", cols, f"Bảng {tbl} phải có cột truong_id")

        # 5. Kiểm tra dữ liệu cũ còn nguyên vẹn và truong_id = 1
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = 'HS12001'")
        hs = cur.fetchone()
        self.assertEqual(hs["ho_ten"], "Nguyễn Hoàng An")
        self.assertEqual(hs["so_du_gio"], 5.5)
        self.assertEqual(hs["truong_id"], 1, "Dữ liệu học sinh cũ phải được gán về truong_id = 1")
        self.assertEqual(hs["trang_thai"], "hoat_dong")

        # 6. Kiểm tra tài khoản 'admin' cũ được nâng lên 'super_admin'
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = 'admin'")
        adm = cur.fetchone()
        self.assertEqual(adm["vai_tro"], "super_admin", "Tài khoản 'admin' cũ phải được nâng lên 'super_admin'")
        self.assertEqual(adm["truong_id"], 1)

        # 7. Kiểm tra dữ liệu các bảng liên kết cũ
        cur.execute("SELECT truong_id, hien_thi_cong_dong FROM skills WHERE tieu_de = 'Ôn tập Hình học'")
        sk = cur.fetchone()
        self.assertEqual(sk["truong_id"], 1)
        self.assertEqual(sk["hien_thi_cong_dong"], 0)

        cur.execute("SELECT truong_id FROM sessions WHERE id = 1")
        self.assertEqual(cur.fetchone()["truong_id"], 1)

        cur.execute("SELECT truong_id FROM ratings WHERE id = 1")
        self.assertEqual(cur.fetchone()["truong_id"], 1)

        cur.execute("SELECT truong_id FROM community_tasks WHERE id = 1")
        self.assertEqual(cur.fetchone()["truong_id"], 1)

        cur.execute("SELECT truong_id FROM task_registrations WHERE id = 1")
        self.assertEqual(cur.fetchone()["truong_id"], 1)

        cur.execute("SELECT truong_id FROM blog_posts WHERE id = 1")
        self.assertEqual(cur.fetchone()["truong_id"], 1)

    def test_02_idempotency_run_multiple_times(self):
        """
        TIÊU CHÍ: Hàm phải idempotent (chạy lại nhiều lần không lỗi, không mất dữ liệu, không duplicate).
        """
        # Chạy lần 1
        migrate_postgres_schema(self.old_db)
        # Chạy lần 2
        migrate_postgres_schema(self.old_db)
        # Chạy lần 3
        migrate_postgres_schema(self.old_db)

        cur = self.old_db.cursor()
        cur.execute("SELECT COUNT(*) FROM truong")
        self.assertEqual(cur.fetchone()[0], 4, "Bảng truong không bị duplicate khi chạy migrate nhiều lần")

        cur.execute("SELECT COUNT(*) FROM users")
        self.assertEqual(cur.fetchone()[0], 2, "Số lượng user vẫn giữ nguyên 2 bản ghi")

        cur.execute("SELECT vai_tro FROM users WHERE ma_hoc_sinh = 'admin'")
        self.assertEqual(cur.fetchone()["vai_tro"], "super_admin")

    def test_03_init_db_twice_on_local_sqlite(self):
        """
        TIÊU CHÍ 1: Chạy init_db() 2 lần liên tiếp trên SQLite local → không lỗi, không mất dữ liệu.
        """
        # Chạy lần 1
        init_db()
        # Chạy lần 2
        init_db()

        # Kiểm tra CSDL local vẫn hoạt động bình thường
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM users")
        user_count = cur.fetchone()[0]
        self.assertGreater(user_count, 0, "Users phải tồn tại sau khi chạy init_db")

        cur.execute("SELECT COUNT(*) FROM truong")
        school_count = cur.fetchone()[0]
        self.assertGreaterEqual(school_count, 4, "Phải có ít nhất 4 trường học sau init_db")

        cur.execute("SELECT vai_tro FROM users WHERE ma_hoc_sinh = 'admin'")
        admin_row = cur.fetchone()
        if admin_row:
            self.assertIn(admin_row["vai_tro"], ("super_admin", "school_admin"), "Admin hệ thống phải là super_admin hoặc school_admin")

        conn.close()

    def test_04_mock_postgres_schema_migration_commands(self):
        """
        TIÊU CHÍ 4: Mô phỏng kết nối PostgreSQL (psycopg2 wrapper) để kiểm tra:
        - Các câu lệnh ALTER TABLE ... ADD COLUMN IF NOT EXISTS ...
        - Truy vấn information_schema / pg_constraint
        - DROP CONSTRAINT và ADD CONSTRAINT users_vai_tro_check
        - UPDATE backfill truong_id và nâng tài khoản admin
        """
        executed_sqls = []

        class MockPgCursor:
            def execute(self, sql, params=None):
                executed_sqls.append((sql.strip(), params))
                return self
            def fetchone(self):
                # Trả về 0 cho SELECT COUNT(*) FROM truong để kích hoạt seed
                return [0]
            def fetchall(self):
                # Trả về danh sách constraint giả lập cho information_schema
                return [("users_vai_tro_check_old",)]

        class MockPgConn:
            def __init__(self):
                self._conn = MagicMock()
                self._cur = MockPgCursor()
            def cursor(self):
                return self._cur
            def commit(self):
                pass
            def rollback(self):
                pass

        mock_conn = MockPgConn()
        migrate_postgres_schema(mock_conn)

        all_sql_texts = " \n ".join([s[0] for s in executed_sqls])

        # 1. Kiểm tra ADD COLUMN IF NOT EXISTS cho users
        self.assertIn("ALTER TABLE users ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1", all_sql_texts)
        self.assertIn("ALTER TABLE users ADD COLUMN IF NOT EXISTS trang_thai TEXT DEFAULT 'hoat_dong'", all_sql_texts)

        # 2. Kiểm tra ADD COLUMN IF NOT EXISTS cho skills
        self.assertIn("ALTER TABLE skills ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1", all_sql_texts)
        self.assertIn("ALTER TABLE skills ADD COLUMN IF NOT EXISTS hien_thi_cong_dong INTEGER DEFAULT 0", all_sql_texts)
        self.assertIn("ALTER TABLE skills ADD COLUMN IF NOT EXISTS trang_thai_cong_dong TEXT DEFAULT 'chua_dang'", all_sql_texts)
        self.assertIn("ALTER TABLE skills ADD COLUMN IF NOT EXISTS nguoi_duyet_cong_dong_id INTEGER", all_sql_texts)
        self.assertIn("ALTER TABLE skills ADD COLUMN IF NOT EXISTS ngay_duyet_cong_dong TEXT", all_sql_texts)

        # 3. Kiểm tra các bảng sessions, ratings, community_tasks, task_registrations, blog_posts
        for tbl in ["sessions", "ratings", "community_tasks", "task_registrations", "blog_posts"]:
            self.assertIn(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1", all_sql_texts)

        # 4. Kiểm tra tìm kiếm và cập nhật CONSTRAINT
        self.assertIn("information_schema.table_constraints", all_sql_texts)
        self.assertIn("DROP CONSTRAINT IF EXISTS", all_sql_texts)
        self.assertIn("ALTER TABLE users ADD CONSTRAINT users_vai_tro_check", all_sql_texts)
        self.assertIn("'super_admin'", all_sql_texts)
        self.assertIn("'school_admin'", all_sql_texts)

        # 5. Kiểm tra Seed 4 trường học
        self.assertIn("INSERT INTO truong", all_sql_texts)

        # 6. Kiểm tra UPDATE backfill truong_id = 1
        self.assertIn("UPDATE users SET truong_id = 1 WHERE truong_id IS NULL", all_sql_texts)
        self.assertIn("UPDATE skills SET truong_id = 1 WHERE truong_id IS NULL", all_sql_texts)

        # 7. Kiểm tra nâng admin lên super_admin
        self.assertIn("UPDATE users SET vai_tro = 'super_admin' WHERE ma_hoc_sinh = 'admin' AND vai_tro = 'admin'", all_sql_texts)

if __name__ == "__main__":
    unittest.main()
