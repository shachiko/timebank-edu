# -*- coding: utf-8 -*-
"""
Script migration sang kiến trúc Đa trường (Multi-tenant) an toàn và chuẩn xác.
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Thực thi VIỆC 2:
- Bảng mới: truong, violations, invite_codes, invite_code_usages
- Thêm truong_id vào: users, skills, sessions, ratings, community_tasks, task_registrations, blog_posts
- Thêm trang_thai vào: users, cập nhật CHECK constraint vai_tro cho super_admin & school_admin
- Seed 4 trường mẫu
- Migrate 100% dữ liệu cũ sang truong_id = 1, đảm bảo số dòng bảo toàn tuyệt đối.
"""

import os
import sys
import io
import sqlite3
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "timebank.db"

SCHOOLS_SEED = [
    (1, "Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy", "/static/img/logo_timebank_edu.png", "dang_thi_diem"),
    (2, "Trường THCS Nguyễn Văn Thuộc", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai"),
    (3, "Trường THCS Lê Văn Tám", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai"),
    (4, "Trường THPT Hải Đảo", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai")
]

TABLES_NEED_TRUONG_ID = [
    "skills",
    "sessions",
    "ratings",
    "community_tasks",
    "task_registrations",
    "blog_posts"
]

def migrate_sqlite():
    if not DATABASE_PATH.exists():
        print(f"[LỖI] Không tìm thấy cơ sở dữ liệu SQLite tại: {DATABASE_PATH}")
        return False

    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()

    # 1. Ghi nhận số dòng trước khi migrate
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    existing_tables = [r[0] for r in cur.fetchall()]
    counts_before = {}
    for tbl in existing_tables:
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        counts_before[tbl] = cur.fetchone()[0]

    print(f"[INFO] Bắt đầu migration SQLite. Tổng số bảng ban đầu: {len(existing_tables)}")

    cur.execute("PRAGMA foreign_keys = OFF;")

    # 2. Tạo bảng truong
    cur.execute("""
        CREATE TABLE IF NOT EXISTS truong (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ten_truong TEXT NOT NULL,
            logo TEXT,
            trang_thai TEXT CHECK(trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung')) DEFAULT 'dang_thi_diem',
            ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed 4 trường
    for s_id, s_name, s_logo, s_status in SCHOOLS_SEED:
        cur.execute("SELECT COUNT(*) FROM truong WHERE id = ?", (s_id,))
        if cur.fetchone()[0] == 0:
            cur.execute("""
                INSERT INTO truong (id, ten_truong, logo, trang_thai)
                VALUES (?, ?, ?, ?)
            """, (s_id, s_name, s_logo, s_status))
            print(f"  + Đã seed trường [{s_id}]: {s_name} ({s_status})")
        else:
            cur.execute("""
                UPDATE truong SET ten_truong = ?, logo = ?, trang_thai = ? WHERE id = ?
            """, (s_name, s_logo, s_status, s_id))

    # 3. Nâng cấp bảng users (Rebuild để cập nhật CHECK constraint vai_tro và trang_thai)
    cur.execute("PRAGMA table_info(users)")
    user_cols = {col[1]: col[2] for col in cur.fetchall()}
    
    cur.execute("""
        CREATE TABLE users_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truong_id INTEGER DEFAULT 1,
            ma_hoc_sinh TEXT UNIQUE NOT NULL,
            ho_ten TEXT NOT NULL,
            lop TEXT,
            vai_tro TEXT CHECK(vai_tro IN ('hoc_sinh', 'giao_vien', 'school_admin', 'super_admin', 'admin')) DEFAULT 'hoc_sinh',
            so_du_gio REAL DEFAULT 2.0,
            gio_ranh TEXT,
            mat_khau TEXT,
            trang_thai TEXT CHECK(trang_thai IN ('hoat_dong', 'cho_duyet', 'de_xuat_khoa', 'da_khoa')) DEFAULT 'hoat_dong',
            FOREIGN KEY (truong_id) REFERENCES truong(id)
        );
    """)

    has_truong_col = "truong_id" in user_cols
    has_trang_thai_col = "trang_thai" in user_cols

    if has_truong_col and has_trang_thai_col:
        cur.execute("""
            INSERT INTO users_new (id, truong_id, ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, trang_thai)
            SELECT id, COALESCE(truong_id, 1), ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, COALESCE(trang_thai, 'hoat_dong')
            FROM users;
        """)
    else:
        cur.execute("""
            INSERT INTO users_new (id, truong_id, ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, trang_thai)
            SELECT id, 1, ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, 'hoat_dong'
            FROM users;
        """)

    cur.execute("DROP TABLE users;")
    cur.execute("ALTER TABLE users_new RENAME TO users;")
    print("  + Đã tái cấu trúc bảng 'users' với truong_id, trang_thai và vai_tro mới")

    # Nâng cấp tài khoản 'admin' lên 'super_admin' (cô Huyền)
    cur.execute("""
        UPDATE users 
        SET vai_tro = 'super_admin',
            ho_ten = 'Cô Nguyễn Thị Huyền (Tổng Quản Trị)',
            truong_id = 1,
            trang_thai = 'hoat_dong'
        WHERE ma_hoc_sinh = 'admin';
    """)
    print("  + Đã nâng cấp tài khoản 'admin' lên vai_tro = 'super_admin' (cô Huyền)")

    # 4. Thêm cột truong_id vào các bảng còn lại
    for tbl in TABLES_NEED_TRUONG_ID:
        if tbl in existing_tables:
            cur.execute(f"PRAGMA table_info({tbl})")
            cols = [col[1] for col in cur.fetchall()]
            if "truong_id" not in cols:
                print(f"  + Thêm cột truong_id vào bảng '{tbl}'")
                cur.execute(f"ALTER TABLE {tbl} ADD COLUMN truong_id INTEGER DEFAULT 1")
            
            # Gán toàn bộ dữ liệu hiện tại về truong_id = 1
            cur.execute(f"UPDATE {tbl} SET truong_id = 1 WHERE truong_id IS NULL OR truong_id = 0")

    # 5. Bảng violations
    cur.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            truong_id INTEGER DEFAULT 1,
            loai_vi_pham TEXT NOT NULL,
            mo_ta TEXT,
            muc_do INTEGER CHECK(muc_do IN (1, 2, 3)) NOT NULL,
            thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
            session_id INTEGER,
            nguoi_bao_cao_id INTEGER,
            trang_thai TEXT DEFAULT 'cho_xu_ly',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (truong_id) REFERENCES truong(id),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    print("  + Đã cấu hình bảng 'violations'")

    # 6. Bảng invite_codes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invite_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            truong_id INTEGER NOT NULL,
            ma_code TEXT UNIQUE NOT NULL,
            loai TEXT CHECK(loai IN ('lop', 'ca_nhan')) NOT NULL,
            so_luot_toi_da INTEGER DEFAULT 1,
            da_dung INTEGER DEFAULT 0,
            ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
            nguoi_tao TEXT,
            FOREIGN KEY (truong_id) REFERENCES truong(id)
        );
    """)
    print("  + Đã cấu hình bảng 'invite_codes'")

    # 7. Bảng invite_code_usages
    cur.execute("""
        CREATE TABLE IF NOT EXISTS invite_code_usages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invite_code_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (invite_code_id) REFERENCES invite_codes(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    print("  + Đã cấu hình bảng 'invite_code_usages'")

    cur.execute("PRAGMA foreign_keys = ON;")
    conn.commit()

    # 8. Đối soát số dòng sau migration
    print("\n--- ĐỐI SOÁT DỮ LIỆU SAU MIGRATION ---")
    all_ok = True
    for tbl, cnt_before in counts_before.items():
        cur.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt_after = cur.fetchone()[0]
        if tbl in TABLES_NEED_TRUONG_ID or tbl == "users":
            cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE truong_id = 1")
            t1_cnt = cur.fetchone()[0]
        else:
            t1_cnt = cnt_after
        status = "OK" if cnt_before == cnt_after else "LỖI MẤT DÒNG"
        if cnt_before != cnt_after:
            all_ok = False
        print(f"  * Bảng {tbl:<20}: Trước={cnt_before:2d} | Sau={cnt_after:2d} | truong_id=1: {t1_cnt:2d} -> [{status}]")

    conn.close()
    return all_ok

if __name__ == "__main__":
    ok = migrate_sqlite()
    if ok:
        print("\n[THÀNH CÔNG] Migration Multi-Tenant hoàn tất 100%! Dữ liệu nguyên vẹn.")
    else:
        print("\n[THẤT BẠI] Có lỗi trong quá trình migration!")
        sys.exit(1)
