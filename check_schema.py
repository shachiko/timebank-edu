# -*- coding: utf-8 -*-
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sqlite3
from app import DATABASE_PATH, init_db

init_db()
conn = sqlite3.connect(DATABASE_PATH)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]

print(f"Tổng số bảng: {len(tables)}/13 bảng")
for idx, tbl in enumerate(tables, 1):
    cursor.execute(f"PRAGMA table_info({tbl})")
    cols = [f"{col[1]} ({col[2]})" for col in cursor.fetchall()]
    cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
    count = cursor.fetchone()[0]
    print(f"{idx:2d}. {tbl:<20} | {count:2d} dòng | Cột: {', '.join(cols)}")

conn.close()
