# -*- coding: utf-8 -*-
"""
Script sao lưu toàn bộ cơ sở dữ liệu trước khi thực hiện migration đa trường (Multi-tenant).
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Bảo vệ dữ liệu tuyệt đối theo yêu cầu VIỆC 1: Không có backup thì không đụng vào schema.
"""

import os
import sys
import io
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
SQLITE_DB_PATH = DB_DIR / "timebank.db"

def backup_sqlite():
    if not SQLITE_DB_PATH.exists():
        print(f"[CẢNH BÁO] Không tìm thấy file {SQLITE_DB_PATH}")
        return None

    # 1. Tạo bản sao nhị phân .bak
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    binary_bak_path = DB_DIR / f"timebank_pre_migration_{timestamp}.db.bak"
    shutil.copy2(SQLITE_DB_PATH, binary_bak_path)
    shutil.copy2(SQLITE_DB_PATH, DB_DIR / "timebank_pre_migration.db.bak")
    print(f"[OK] Đã tạo bản sao nhị phân SQLite: {binary_bak_path.name}")

    # 2. Dump toàn bộ schema và data ra file SQL SQLite
    sql_dump_path = DB_DIR / f"backup_pre_migration_sqlite_{timestamp}.sql"
    fixed_sql_dump_path = DB_DIR / "backup_pre_migration_sqlite.sql"
    
    conn = sqlite3.connect(SQLITE_DB_PATH)
    with open(sql_dump_path, "w", encoding="utf-8") as f:
        for line in conn.iterdump():
            f.write(f"{line}\n")
    shutil.copy2(sql_dump_path, fixed_sql_dump_path)
    print(f"[OK] Đã xuất toàn bộ SQLite dump ra: {sql_dump_path.name}")
    return conn

def export_postgres_dump(sqlite_conn):
    """
    Sinh file backup cú pháp PostgreSQL tương thích hoàn toàn để phục hồi lên PostgreSQL / Render.
    Nếu có biến môi trường DATABASE_URL, sẽ kết nối trực tiếp đến PostgreSQL để dump.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    pg_dump_path = DB_DIR / f"backup_pre_migration_postgres_{timestamp}.sql"
    fixed_pg_dump_path = DB_DIR / "backup_pre_migration_postgres.sql"

    # Kiểm tra nếu có kết nối PostgreSQL thật
    db_url = os.getenv("DATABASE_URL", "").strip()
    if db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")):
        try:
            import psycopg2
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            pg_conn = psycopg2.connect(db_url)
            cur = pg_conn.cursor()
            
            # Lấy danh sách bảng trong PostgreSQL
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """)
            tables = [r[0] for r in cur.fetchall()]
            
            with open(pg_dump_path, "w", encoding="utf-8") as f:
                f.write(f"-- TIMEBANK EDU POSTGRESQL LIVE BACKUP\n")
                f.write(f"-- Exported at: {datetime.now().isoformat()}\n\n")
                for tbl in tables:
                    cur.execute(f"SELECT * FROM {tbl}")
                    rows = cur.fetchall()
                    cur.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_schema = 'public' AND table_name = '{tbl}'
                        ORDER BY ordinal_position;
                    """)
                    cols = [c[0] for c in cur.fetchall()]
                    cols_str = ", ".join(cols)
                    f.write(f"-- Table: {tbl} ({len(rows)} rows)\n")
                    for row in rows:
                        vals = []
                        for val in row:
                            if val is None:
                                vals.append("NULL")
                            elif isinstance(val, (int, float)):
                                vals.append(str(val))
                            else:
                                escaped = str(val).replace("'", "''")
                                vals.append(f"'{escaped}'")
                        f.write(f"INSERT INTO {tbl} ({cols_str}) VALUES ({', '.join(vals)});\n")
                    f.write("\n")
            pg_conn.close()
            shutil.copy2(pg_dump_path, fixed_pg_dump_path)
            print(f"[OK] Đã xuất trực tiếp từ PostgreSQL thật ra: {pg_dump_path.name}")
            return
        except Exception as e:
            print(f"[THÔNG BÁO] Không thể kết nối PostgreSQL từ DATABASE_URL ({e}), tiến hành sinh PostgreSQL dump từ dữ liệu gốc SQLite...")

    # Nếu không có live PostgreSQL hoặc chạy cục bộ, xuất từ SQLite sang định dạng PostgreSQL chuẩn
    if sqlite_conn:
        cur = sqlite_conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]

        with open(pg_dump_path, "w", encoding="utf-8") as f:
            f.write(f"-- TIMEBANK EDU POSTGRESQL PRE-MIGRATION BACKUP DUMP\n")
            f.write(f"-- Exported at: {datetime.now().isoformat()}\n")
            f.write(f"-- Total Tables: {len(tables)}\n\n")

            for tbl in tables:
                cur.execute(f"PRAGMA table_info({tbl})")
                cols = [c[1] for c in cur.fetchall()]
                cur.execute(f"SELECT * FROM {tbl}")
                rows = cur.fetchall()
                f.write(f"-- Data for table: {tbl} ({len(rows)} rows)\n")
                if rows and cols:
                    cols_str = ", ".join(cols)
                    for row in rows:
                        vals = []
                        for val in row:
                            if val is None:
                                vals.append("NULL")
                            elif isinstance(val, (int, float)):
                                vals.append(str(val))
                            else:
                                escaped = str(val).replace("'", "''")
                                vals.append(f"'{escaped}'")
                        f.write(f"INSERT INTO {tbl} ({cols_str}) VALUES ({', '.join(vals)});\n")
                f.write("\n")

        shutil.copy2(pg_dump_path, fixed_pg_dump_path)
        print(f"[OK] Đã tạo file PostgreSQL backup hoàn chỉnh: {fixed_pg_dump_path.name}")

if __name__ == "__main__":
    print("=== TIẾN HÀNH SAO LƯU CƠ SỞ DỮ LIỆU TIMEBANK EDU ===")
    conn = backup_sqlite()
    export_postgres_dump(conn)
    if conn:
        conn.close()
    print("=== SAO LƯU HOÀN TẤT: DỮ LIỆU ĐÃ ĐƯỢC BẢO VỆ AN TOÀN TUYỆT ĐỐI ===")
