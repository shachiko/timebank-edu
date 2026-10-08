# -*- coding: utf-8 -*-
"""
DỰ ÁN DỰ THI: NGÂN HÀNG THỜI GIAN HỌC ĐƯỜNG (TIMEBANK EDU)
CUỘC THI: "NGÀY HỘI NHÀ GIÁO SÁNG TẠO VỚI CÔNG NGHỆ SỐ VÀ AI 2026" - BẢNG B
ĐƠN VỊ TỔ CHỨC: BỘ GIÁO DỤC VÀ ĐÀO TẠO & ĐẠI HỌC RMIT VIỆT NAM

Tác giả: Nhóm tác giả / Giáo viên hướng dẫn
Mục tiêu kiến trúc: Single-Tenant (Cài đặt độc lập cho từng trường), Python Flask + SQLite
Triết lý sư phạm: "Một giờ bạn dạy — một giờ bạn được học" (Mọi tri thức đều bình đẳng)
"""

import os
import io
import re
import time
import base64
import secrets
import sqlite3
import yaml
import csv
import qrcode
from datetime import datetime
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, jsonify, g, flash, redirect, url_for, session, abort, make_response
)
from ai_service import (
    ai_moderate_skill, ai_matchmake, ai_generate_lesson_plan, 
    ai_summarize_feedback, ai_admin_early_warning, is_ai_live,
    ai_generate_quiz, ai_recommend_tasks, get_chat_greeting_and_reminder,
    ai_chat_assistant, ai_generate_weekly_newsletter
)

# 1. Tải các biến môi trường từ file .env (nếu có)
# Lưu ý: File .env chứa API Key tuyệt đối không được đưa lên GitHub
load_dotenv()

# Đường dẫn thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "timebank.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
CONFIG_PATH = BASE_DIR / "config.yaml"
UPLOAD_BLOG_FOLDER = BASE_DIR / "static" / "uploads" / "blog"
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif"}

# Đảm bảo thư mục upload tồn tại
UPLOAD_BLOG_FOLDER.mkdir(parents=True, exist_ok=True)

def allowed_image_file(filename):
    """Kiểm tra định dạng file ảnh tải lên có hợp lệ hay không."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
# Cấu hình kích thước tải lên tối đa 16MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
# Bảo mật: SECRET_KEY đọc từ biến môi trường khi deploy production
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "timebank-edu-secret-key-2026"

# Bộ nhớ đệm kết quả gợi ý ghép cặp hàng ngày: key = (user_id, YYYY-MM-DD), val = (matches, is_live, subject)
DAILY_RECOMMENDATION_CACHE = {}


# ==============================================================================
# HÀM XỬ LÝ CẤU HÌNH NHÀ TRƯỜNG (CONFIG.YAML)
# ==============================================================================
def load_school_config():
    """
    Đọc tệp cấu hình config.yaml để tùy biến nhận diện thương hiệu cho từng trường.
    Giáo viên chỉ cần sửa file config.yaml trong 5 phút là có thể chuyển giao hệ thống
    sang một trường học khác mà không cần viết lại mã nguồn.
    """
    default_config = {
        "ten_truong": "Trường Quốc tế Song ngữ UKA Academy Hạ Long",
        "logo_path": "/static/img/logo_timebank_edu.png",
        "mau_chu_dao": "#F26522",
        "email_lien_he": "mshuyenuka@gmail.com",
        "dong_gioi_thieu": "Hệ thống Ngân hàng Thời gian Học đường — Trao đổi tri thức, sẻ chia kỹ năng bằng tín dụng thời gian bình đẳng."
    }
    
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if data and isinstance(data, dict):
                    default_config.update(data)
        except Exception as e:
            app.logger.warning(f"Không thể đọc file config.yaml, dùng cấu hình mặc định: {e}")
            
    return default_config


@app.template_filter("format_date")
def format_date_filter(value):
    """
    Bộ lọc Jinja2 chuẩn hóa định dạng ngày sang dd/mm/yyyy:
    Nhận chuỗi YYYY-MM-DD HH:MM:SS hoặc YYYY-MM-DD và chuyển thành dd/mm/yyyy.
    """
    if not value:
        return "N/A"
    try:
        val_str = str(value).strip()
        date_part = val_str.split(" ")[0]
        parts = date_part.split("-")
        if len(parts) == 3 and len(parts[0]) == 4:
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return val_str
    except Exception:
        return str(value)


@app.context_processor
def inject_template_globals():
    """
    Tự động truyền cấu hình trường học 'config' và thông tin phiên đăng nhập 'current_user'
    vào tất cả các giao diện HTML (Jinja2 Template).
    """
    current_user = None
    if "user_id" in session:
        # Lấy số dư mới nhất từ cơ sở dữ liệu nếu có kết nối
        current_user = {
            "id": session.get("user_id"),
            "ma_hoc_sinh": session.get("ma_hoc_sinh"),
            "ho_ten": session.get("ho_ten"),
            "vai_tro": session.get("vai_tro"),
            "lop": session.get("lop"),
            "so_du_gio": session.get("so_du_gio", 2.0)
        }
    return {
        "config": load_school_config(),
        "current_user": current_user
    }


# ==============================================================================
# DECORATORS PHÂN QUYỀN TRUY CẬP (ACCESS CONTROL / RBAC)
# ==============================================================================
def login_required(f):
    """
    Bắt buộc người dùng phải đăng nhập trước khi truy cập trang.
    Nếu chưa đăng nhập, chuyển hướng đến trang /login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập để tiếp tục truy cập.", "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Chỉ cho phép tài khoản có vai_tro = 'admin' truy cập.
    Nếu là học sinh hoặc giáo viên, lập tức chặn truy cập và trả về mã lỗi 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập bằng tài khoản Quản trị viên.", "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("vai_tro") != "admin":
            # Chặn học sinh và giáo viên: trả về trang lỗi 403
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)
    return decorated_function


def teacher_or_admin_required(f):
    """
    Chỉ cho phép Giáo viên (giao_vien) hoặc Quản trị viên (admin) thực hiện chức năng.
    Học sinh không có quyền sẽ bị chặn bằng mã lỗi 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Vui lòng đăng nhập với quyền Giáo viên hoặc Quản trị viên.", "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("vai_tro") not in ("giao_vien", "admin"):
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)
    return decorated_function


@app.errorhandler(403)
def handle_forbidden(e):
    """
    Trang xử lý lỗi 403 Forbidden: Hiển thị giao diện thông báo tiếng Việt lịch sự, rõ ràng.
    """
    return render_template("errors/403.html"), 403


# ==============================================================================
# QUẢN LÝ KẾT NỐI VÀ KHỞI TẠO CƠ SỞ DỮ LIỆU (SQLITE & POSTGRESQL DEPLOYMENT)
# ==============================================================================

def is_postgres_configured():
    """
    Kiểm tra xem hệ thống có được cấu hình kết nối PostgreSQL qua biến môi trường DATABASE_URL hay không.
    - Có DATABASE_URL (ví dụ khi Deploy trên Render) -> Trả về True (dùng PostgreSQL).
    - Không có DATABASE_URL (mặc định môi trường trường học) -> Trả về False (dùng SQLite cục bộ).
    """
    url = os.getenv("DATABASE_URL", "").strip()
    return bool(url and (url.startswith("postgres://") or url.startswith("postgresql://")))


def get_postgres_url():
    """
    Chuẩn hóa URL kết nối PostgreSQL (Render thường cung cấp URL bắt đầu bằng postgres://,
    cần đổi thành postgresql:// để tương thích với thư viện psycopg2).
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class PostgresCursorWrapper:
    """
    Lớp bọc con trỏ PostgreSQL (psycopg2) để tương thích trong suốt với mã nguồn SQLite:
    - Tự động chuyển đổi ký tự giữ chỗ (placeholder) từ '?' của SQLite sang '%s' của PostgreSQL.
    - Hỗ trợ thuộc tính lastrowid đối với các câu lệnh INSERT (bằng cách bổ sung RETURNING id).
    - Hỗ trợ cả truy cập cột theo tên (row['cot']) và theo chỉ số số nguyên (row[0]).
    """
    def __init__(self, cursor):
        self._cur = cursor
        self._lastrowid = None

    def execute(self, query, params=None):
        converted_query = query
        # Chuyển đổi '?' thành '%s' cho psycopg2 nếu có
        if "?" in converted_query:
            converted_query = converted_query.replace("?", "%s")

        is_insert = converted_query.strip().upper().startswith("INSERT INTO")
        has_returning = "RETURNING" in converted_query.upper()

        if is_insert and not has_returning:
            cleaned = converted_query.rstrip("; \t\n")
            converted_query = f"{cleaned} RETURNING id;"

        if params is not None:
            self._cur.execute(converted_query, params)
        else:
            self._cur.execute(converted_query)

        if is_insert and not has_returning:
            try:
                row = self._cur.fetchone()
                self._lastrowid = row[0] if row else None
            except Exception:
                self._lastrowid = None
        else:
            self._lastrowid = None

        return self

    def executemany(self, query, seq_of_params):
        converted_query = query
        if "?" in converted_query:
            converted_query = converted_query.replace("?", "%s")
        return self._cur.executemany(converted_query, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    @property
    def lastrowid(self):
        return self._lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    def close(self):
        self._cur.close()


class PostgresConnectionWrapper:
    """
    Lớp bọc kết nối PostgreSQL để cung cấp giao diện tương tự đối tượng connection của sqlite3.
    """
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        import psycopg2.extras
        raw_cur = self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        return PostgresCursorWrapper(raw_cur)

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()


def get_db():
    """
    Mở kết nối tới cơ sở dữ liệu cho mỗi request:
    - Nếu có biến môi trường DATABASE_URL: Tự động kết nối PostgreSQL.
    - Nếu không có: Sử dụng SQLite cục bộ (database/timebank.db).
    """
    if "db" not in g:
        if is_postgres_configured():
            try:
                import psycopg2
                pg_url = get_postgres_url()
                raw_conn = psycopg2.connect(pg_url)
                g.db = PostgresConnectionWrapper(raw_conn)
            except Exception as e:
                app.logger.warning(f"Lỗi kết nối PostgreSQL ({e}), tự động chuyển về SQLite dự phòng.")
                g.db = sqlite3.connect(
                    DATABASE_PATH,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                g.db.row_factory = sqlite3.Row
                g.db.execute("PRAGMA foreign_keys = ON")
        else:
            g.db = sqlite3.connect(
                DATABASE_PATH,
                detect_types=sqlite3.PARSE_DECLTYPES
            )
            g.db.row_factory = sqlite3.Row
            g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """
    Tự động đóng kết nối cơ sở dữ liệu khi kết thúc lượt xử lý (request).
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """
    Khởi tạo cấu trúc cơ sở dữ liệu (13 bảng):
    - Đọc DATABASE_URL từ biến môi trường:
      + Có -> Kết nối PostgreSQL, tự động chuẩn hóa schema.sql và nạp seed data nếu bảng chưa có.
      + Không -> Khởi tạo vào SQLite cục bộ (database/timebank.db).
    """
    global DAILY_RECOMMENDATION_CACHE
    DAILY_RECOMMENDATION_CACHE.clear()

    if is_postgres_configured():
        try:
            import psycopg2
            pg_url = get_postgres_url()
            raw_conn = psycopg2.connect(pg_url)
            conn = PostgresConnectionWrapper(raw_conn)

            with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
                schema_sql = f.read()

            pg_schema = schema_sql.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
            pg_schema = pg_schema.replace("PRAGMA foreign_keys = ON;", "")

            cur = conn.cursor()
            for stmt in pg_schema.split(";"):
                stmt = stmt.strip()
                if stmt:
                    try:
                        cur.execute(stmt)
                    except Exception:
                        pass
            conn.commit()

            cur.execute("SELECT COUNT(*) FROM users")
            row = cur.fetchone()
            user_count = row[0] if row else 0
            if user_count == 0:
                seed_demo_data(conn)
            conn.close()
            return
        except Exception as e:
            app.logger.warning(f"Không thể khởi tạo CSDL PostgreSQL ({e}), tiếp tục dùng SQLite.")

    # Mặc định: Dùng SQLite cục bộ
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    conn.commit()
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        seed_demo_data(conn)
        
    conn.close()



def seed_demo_data(conn):
    """
    Nạp dữ liệu mẫu sư phạm phục vụ thuyết trình và demo thực tế:
    - Tạo sẵn admin/admin123 cho Ban Giám Khảo và Quản trị viên
    - Tạo sẵn tài khoản giáo viên GV001/admin123
    - 5 học sinh tiêu biểu (An, Bình, Chi, Minh, Hà) với số dư giờ khởi đầu
    - Các kỹ năng đăng ký, phiên học thực tế, sổ cái tín dụng và đánh giá
    """
    cur = conn.cursor()
    default_pass_hash = generate_password_hash("admin123")
    
    # 1. Thêm người dùng mẫu (có mật khẩu băm, giờ rảnh và vai trò)
    users = [
        ('admin', 'Quản trị viên Hệ thống', 'Ban Giám Hiệu', 'admin', 100.0, 'Toàn thời gian', default_pass_hash),
        ('GV001', 'Thầy Nguyễn Văn Đức', 'Tổ Toán - Tin', 'giao_vien', 10.0, 'Các buổi chiều trong tuần', default_pass_hash),
        ('HS12001', 'Nguyễn Hoàng An', '12A1', 'hoc_sinh', 3.5, 'Chiều thứ 3, sáng thứ 7', default_pass_hash),
        ('HS11002', 'Trần Thanh Bình', '11B2', 'hoc_sinh', 2.5, 'Sáng Chủ nhật, tối thứ 5', default_pass_hash),
        ('HS10003', 'Lê Kim Chi', '10A3', 'hoc_sinh', 3.0, 'Chiều thứ 6, sáng Chủ nhật', default_pass_hash),
        ('HS11004', 'Phạm Quang Minh', '11A1', 'hoc_sinh', 2.0, 'Tối thứ 2, tối thứ 4', default_pass_hash),
        ('HS12005', 'Vũ Thu Hà', '12D2', 'hoc_sinh', 2.0, 'Sáng thứ 7, chiều Chủ nhật', default_pass_hash)
    ]
    cur.executemany(
        """INSERT INTO users 
           (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        users
    )
    
    # 2. Thêm kỹ năng chia sẻ (user_id = 3 là HS12001, 4 là HS11002, 5 là HS10003...)
    skills = [
        (3, 'Toán học', 'Ôn tập Hình học không gian lớp 12', 'Phương pháp giải nhanh trắc nghiệm khoảng cách và góc', 'da_duyet', 'Nội dung bổ ích, phù hợp chương trình'),
        (4, 'Năng khiếu', 'Đệm hát Guitar cơ bản cho người mới', 'Cách bấm các hợp âm chuẩn và kỹ thuật quạt chả điệu Disco', 'da_duyet', 'Kỹ năng giải trí tích cực'),
        (5, 'Ngoại ngữ', 'Luyện phản xạ nói Tiếng Anh IELTS Speaking', 'Chiến thuật trả lời Part 1 và Part 2 tự nhiên, lưu loát', 'da_duyet', 'Rất hữu ích cho học sinh hội nhập'),
        (6, 'Tin học', 'Lập trình Python cho người mới bắt đầu', 'Cấu trúc rẽ nhánh, vòng lặp và xử lý chuỗi căn bản', 'da_duyet', 'Định hướng chuyển đổi số trường học'),
        (7, 'Khoa học', 'Phương pháp làm bài thí nghiệm Hóa học 12', 'Giải thích hiện tượng và mẹo nhớ tính chất kim loại kiềm', 'cho_duyet', 'Chờ giáo viên bộ môn duyệt nội dung'),
        (5, 'Toán học', 'Phương pháp vẽ đồ thị và khảo sát hàm số 12', 'Kỹ thuật nhận diện bảng biến thiên và cực trị hàm số', 'da_duyet', 'Nội dung trọng tâm thi tốt nghiệp THPT'),
        (7, 'Toán học', 'Bí quyết giải nhanh Toán Xác suất và Thống kê', 'Phương pháp tư duy sơ đồ cây và bài toán xác suất thực tế', 'da_duyet', 'Rèn luyện tư duy logic và suy luận')
    ]
    cur.executemany(
        """INSERT INTO skills 
           (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        skills
    )
    
    # 3. Thêm các phiên học hoàn thành thực tế (Sessions)
    # Session 1: An dạy Toán cho Bình (1.0 giờ)
    # Session 2: Bình dạy Đàn cho Chi (1.0 giờ)
    # Session 3: Chi dạy Tiếng Anh cho An (1.0 giờ)
    # Session 4: An dạy Toán cho Minh (1.0 giờ)
    # Session 5: Minh dạy Python cho Hà (1.0 giờ)
    sessions = [
        (1, 3, 4, '2026-09-28 14:00:00', 1.0, 'hoan_thanh', 'QR_SES_001', 1, 1, 'Dàn ý AI: Khái niệm góc giữa hai mặt phẳng + 3 bài tập mẫu', 1),
        (2, 4, 5, '2026-09-29 15:30:00', 1.0, 'hoan_thanh', 'QR_SES_002', 1, 1, 'Dàn ý AI: Hợp âm C-Am-Dm-G7 + bài tập bấm tay', 1),
        (3, 5, 3, '2026-10-01 16:00:00', 1.0, 'hoan_thanh', 'QR_SES_003', 1, 1, 'Dàn ý AI: Chủ đề Hometown & Hobbies', 1),
        (1, 3, 6, '2026-10-03 09:00:00', 1.0, 'hoan_thanh', 'QR_SES_004', 1, 1, 'Dàn ý AI: Góc giữa đường thẳng và mặt phẳng', 1),
        (4, 6, 7, '2026-10-04 14:30:00', 1.0, 'hoan_thanh', 'QR_SES_005', 1, 1, 'Dàn ý AI: Biến số và lệnh input/print trong Python', 1)
    ]
    cur.executemany(
        """INSERT INTO sessions 
           (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sessions
    )
    
    # 4. Ghi sổ cái tín dụng (credits_ledger) - Nguyên tắc chỉ Insert
    ledger_entries = [
        (3, 1.0, 'Dạy Toán cho Trần Thanh Bình', 1, '2026-09-28 15:00:00'),
        (4, -1.0, 'Học Toán từ Nguyễn Hoàng An', 1, '2026-09-28 15:00:00'),
        (4, 1.0, 'Dạy Đàn cho Lê Kim Chi', 2, '2026-09-29 16:30:00'),
        (5, -1.0, 'Học Đàn từ Trần Thanh Bình', 2, '2026-09-29 16:30:00'),
        (5, 1.0, 'Dạy Tiếng Anh cho Nguyễn Hoàng An', 3, '2026-10-01 17:00:00'),
        (3, -1.0, 'Học Tiếng Anh từ Lê Kim Chi', 3, '2026-10-01 17:00:00'),
        (3, 1.0, 'Dạy Toán cho Phạm Quang Minh', 4, '2026-10-03 10:00:00'),
        (6, -1.0, 'Học Toán từ Nguyễn Hoàng An', 4, '2026-10-03 10:00:00'),
        (6, 1.0, 'Dạy Python cho Vũ Thu Hà', 5, '2026-10-04 15:30:00'),
        (7, -1.0, 'Học Python từ Phạm Quang Minh', 5, '2026-10-04 15:30:00'),
        (3, 2.0, 'nhiem_vu_cong_dong: Hỗ trợ số hóa tài liệu thư viện', None, '2026-10-05 11:00:00')
    ]
    cur.executemany(
        "INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) VALUES (?, ?, ?, ?, ?)",
        ledger_entries
    )
    
    # 5. Thêm đánh giá chất lượng (ratings)
    ratings = [
        (1, 4, 3, 5, 'Anh An giảng Toán rất dễ hiểu, giải thích bài tập góc không gian siêu hay!'),
        (2, 5, 4, 5, 'Bình dạy đàn kiên nhẫn, chỉ cách chuyển hợp âm rất dễ nhớ.'),
        (3, 3, 5, 5, 'Chi phát âm chuẩn, sửa lỗi ngữ điệu cho mình rất nhiệt tình.'),
        (4, 6, 3, 5, 'Buổi học rất bổ ích, mình đã tự tin làm được bài kiểm tra.'),
        (5, 7, 6, 4, 'Minh chỉ code dễ hiểu, mong có thêm buổi học tiếp theo.')
    ]
    cur.executemany(
        """INSERT INTO ratings 
           (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet) 
           VALUES (?, ?, ?, ?, ?)""",
        ratings
    )
    
    # 6. Ghi nhật ký AI minh bạch (ai_logs)
    ai_logs = [
        (3, 'dan_y_buoi_hoc', 'Soạn dàn ý buổi học Toán Hình học 12', 'Đã sinh cấu trúc 3 phần: Lý thuyết định nghĩa, bài tập mẫu và mẹo giải nhanh.', '2026-09-28 13:50:00'),
        (4, 'dan_y_buoi_hoc', 'Soạn dàn ý hướng dẫn đệm đàn Guitar', 'Đã sinh danh sách hợp âm C, Am, Dm, G7 và bài tập bấm gam.', '2026-09-29 15:10:00'),
        (5, 'kiem_duyet', 'Kiểm duyệt nội dung chia sẻ kỹ năng tiếng Anh', 'Nội dung giáo dục an toàn, tích cực, không vi phạm chuẩn mực sư phạm.', '2026-10-01 10:00:00'),
        (3, 'goi_y_nhiem_vu', 'Gợi ý nhiệm vụ cộng đồng phù hợp học sinh', 'Đã đề xuất nhiệm vụ hỗ trợ số hóa sách thư viện dựa trên kỹ năng tin học.', '2026-10-05 08:30:00'),
        (3, 'tro_ly_ao', 'Tư vấn lộ trình trao đổi kỹ năng học đường', 'Trợ lý ảo đã giải đáp thắc mắc về quy chế tín dụng thời gian cho học sinh.', '2026-10-05 09:15:00')
    ]
    cur.executemany(
        "INSERT INTO ai_logs (user_id, chuc_nang, input_tom_tat, output_text, thoi_gian) VALUES (?, ?, ?, ?, ?)",
        ai_logs
    )

    # 7. Thêm nhiệm vụ cộng đồng mẫu (community_tasks)
    community_tasks = [
        ('Dọn rác bãi biển Hạ Long sáng Chủ nhật', 'Hoạt động thanh niên tình nguyện thu gom rác thải nhựa tại bờ biển, làm sạch cảnh quan môi trường.', 'Bãi tắm Bãi Cháy, TP. Hạ Long', 2.0, 10, '2026-10-25', 2, 'mo_dang_ky', '2026-10-05 08:00:00'),
        ('Hỗ trợ thư viện trường sắp xếp sách', 'Phân loại sách giáo khoa mới, dán mã định danh và sắp xếp lên giá sách theo chuẩn thư viện xanh.', 'Phòng Thư viện - Tầng 2', 1.5, 5, '2026-10-20', 2, 'mo_dang_ky', '2026-10-05 08:30:00'),
        ('Dạy kỹ năng số cho các em khối Tiểu học', 'Phụ đạo tin học, hướng dẫn các em học sinh lớp 3-4 gõ bàn phím 10 ngón và tra cứu tài liệu học tập an toàn.', 'Phòng máy Tin học số 2', 2.0, 4, '2026-10-30', 2, 'mo_dang_ky', '2026-10-05 09:00:00'),
        ('Hỗ trợ số hóa tài liệu thư viện trường', 'Quét và phân loại sách tham khảo vào hệ thống thư viện điện tử.', 'Phòng Thư viện - Tầng 2', 2.0, 4, '2026-10-15', 2, 'hoan_thanh', '2026-10-04 08:00:00')
    ]
    cur.executemany(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai, thoi_gian_tao) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        community_tasks
    )

    # 8. Thêm đăng ký nhiệm vụ cộng đồng (task_registrations)
    # Học sinh An (id=3) đã hoàn thành nhiệm vụ số 4 (đã cộng giờ ở credits_ledger)
    # Học sinh Bình (id=4) đăng ký tham gia nhiệm vụ số 2
    task_regs = [
        (4, 3, 'hoan_thanh', '2026-10-04 08:15:00'),
        (2, 4, 'da_dang_ky', '2026-10-05 08:45:00')
    ]
    cur.executemany(
        "INSERT INTO task_registrations (task_id, user_id, trang_thai, thoi_gian_dang_ky) VALUES (?, ?, ?, ?)",
        task_regs
    )

    # 9. Thêm tin nhắn Trợ lý ảo (chat_messages)
    chat_samples = [
        (3, 'user', 'Em muốn học thêm kỹ năng giao tiếp tiếng Anh thì nên tìm bạn nào?', '2026-10-01 09:00:00'),
        (3, 'assistant', 'Chào An! Dựa trên hệ thống, bạn Lê Kim Chi (10A3) đang chia sẻ kỹ năng Luyện phản xạ IELTS Speaking rất phù hợp với em nhé!', '2026-10-01 09:00:05')
    ]
    cur.executemany(
        "INSERT INTO chat_messages (user_id, vai_tro, noi_dung, thoi_gian) VALUES (?, ?, ?, ?)",
        chat_samples
    )

    # 10. Thêm bộ câu hỏi trắc nghiệm mẫu (quiz_questions) do AI tạo
    # Session 1: Toán Hình học 12 (5 câu từ dễ đến khó)
    sample_questions = [
        (1, "Khái niệm góc giữa hai mặt phẳng trong không gian được đo bằng góc giữa:", 
         "Hai đường thẳng bất kỳ trên hai mặt phẳng", 
         "Hai đường thẳng lần lượt vuông góc với giao tuyến tại cùng một điểm", 
         "Hai vectơ chỉ phương ngẫu nhiên", 
         "Giao tuyến của hai mặt phẳng", "B"),
        (1, "Khi hai mặt phẳng vuông góc với nhau, góc giữa chúng bằng bao nhiêu độ?", 
         "0 độ", "45 độ", "90 độ", "180 độ", "C"),
        (1, "Để tính khoảng cách từ một điểm M đến mặt phẳng (P), ta cần dựng:", 
         "Đoạn vuông góc kẻ từ M đến mặt phẳng (P)", 
         "Một đường thẳng xiên bất kỳ", 
         "Đường thẳng song song với (P)", 
         "Đoạn nối M với trọng tâm tam giác đáy", "A"),
        (1, "Cho hình chóp S.ABC có SA vuông góc với đáy (ABC). Góc giữa đường thẳng SB và đáy là:", 
         "Góc SBA", "Góc SAB", "Góc ASB", "Góc SCB", "A"),
        (1, "Tuyệt chiêu nhận diện nhanh góc giữa mặt bên và mặt đáy trong hình chóp đều là gì?", 
         "Xác định trung điểm cạnh đáy rồi nối với đỉnh", 
         "Kẻ bừa một đường thẳng nối tâm đáy", 
         "Không thể xác định", 
         "Dùng thước đo độ trên giấy", "A"),

        # Session 2: Đệm hát Guitar (5 câu)
        (2, "Hợp âm Đô trưởng (C) cơ bản gồm những nốt nào trong âm giai?", 
         "Đô - Mi - Son (C - E - G)", 
         "Đô - Rê - Mi (C - D - E)", 
         "La - Đô - Mi (A - C - E)", 
         "Son - Si - Rê (G - B - D)", "A"),
        (2, "Khi bấm hợp âm La thứ (Am), ngón trỏ thường đặt ở vị trí nào?", 
         "Ngăn 1 dây 2 (nốt Đô)", 
         "Ngăn 2 dây 3", 
         "Ngăn 3 dây 1", 
         "Ngăn 1 dây 6", "A"),
        (2, "Điệu Disco cơ bản thường có nhịp phách như thế nào?", 
         "Nhịp 2/4 hoặc 4/4 rộn rã, dứt khoát", 
         "Nhịp 3/4 êm dịu điệu Valse", 
         "Nhịp 6/8 chậm rãi", 
         "Không có nhịp phách cố định", "A"),
        (2, "Bí quyết để chuyển nhanh giữa các hợp âm mà không bị vấp tiếng là gì?", 
         "Giữ ngón tay sát phím đàn và tìm ngón chung làm trụ", 
         "Nhấc toàn bộ cả bàn tay ra thật xa cần đàn", 
         "Dừng gảy 5 giây để nhìn tay", 
         "Bấm thật mạnh cho đau ngón tay", "A"),
        (2, "Khi ngón tay bị đau lúc mới tập guitar, cách khắc phục khoa học nhất là:", 
         "Tập đều đặn mỗi ngày 20-30 phút để hình thành vết chai tự nhiên", 
         "Bỏ đàn 2 tháng", 
         "Dùng băng keo quấn kín các đầu ngón tay", 
         "Bôi dầu hỏa vào ngón tay", "A"),

        # Session 3: IELTS Speaking (5 câu)
        (3, "Trong bài thi IELTS Speaking Part 1, độ dài lý tưởng cho mỗi câu trả lời là:", 
         "Khoảng 2 đến 3 câu hoàn chỉnh có mở rộng ý tự nhiên", 
         "Chỉ trả lời đúng 'Yes' hoặc 'No'", 
         "Nói độc thoại liên tục 10 phút", 
         "Im lặng mỉm cười chờ giám khảo hỏi tiếp", "A"),
        (3, "Để nâng cao điểm tiêu chí Từ vựng (Lexical Resource), bạn nên sử dụng:", 
         "Collocations và từ đồng nghĩa ngữ cảnh tự nhiên", 
         "Từ cổ điển thế kỷ 18 khó hiểu", 
         "Từ viết tắt tiếng lóng tin nhắn", 
         "Lặp lại 1 từ duy nhất nhiều lần", "A"),
        (3, "Khi gặp câu hỏi bất ngờ trong Speaking Part 1, chiến thuật câu giờ thông minh là:", 
         "Dùng filler phrase tự nhiên như 'That’s an interesting question...'", 
         "Nói to 'I don't know' rồi ngồi im", 
         "Xin phép giám khảo tra từ điển Google", 
         "Hỏi ngược lại giám khảo", "A"),
        (3, "Tiêu chí 'Fluency and Coherence' (Trôi chảy và mạch lạc) đánh giá điều gì?", 
         "Khả năng diễn đạt liên tục, có liên kết ý logic, ít ngập ngừng kéo dài", 
         "Nói thật nhanh như đọc ráp dù sai ngữ pháp", 
         "Giọng điệu phải giống 100% người bản xứ", 
         "Số lượng từ ngữ phát âm to nhất", "A"),
        (3, "Bí quyết tự tin luyện nói tiếng Anh hằng ngày cùng bạn bè là gì?", 
         "Tạo môi trường trao đổi thoải mái, không sợ mắc lỗi sai", 
         "Chỉ nói khi thuộc lòng 100% kịch bản", 
         "Chỉ luyện nói một mình trước gương trong bóng tối", 
         "Không bao giờ nói chuyện với ai", "A")
    ]
    cur.executemany(
        """INSERT INTO quiz_questions 
           (session_id, cau_hoi, lua_chon_a, lua_chon_b, lua_chon_c, lua_chon_d, dap_an_dung) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        sample_questions
    )

    # 11. Thêm kết quả trắc nghiệm mẫu (quiz_results)
    # Session 1: Bình làm quiz Hình học -> 4/5 điểm (80%), tự tin trước = 2★
    # Session 2: Chi làm quiz Guitar -> 5/5 điểm (100%), tự tin trước = 3★
    # Session 3: An làm quiz Tiếng Anh -> 4/5 điểm (80%), tự tin trước = 2★
    quiz_results_data = [
        (1, 4, 2.0, 4.0, '2026-09-28 15:15:00'),
        (2, 5, 3.0, 5.0, '2026-09-29 16:45:00'),
        (3, 3, 2.0, 4.0, '2026-10-01 17:15:00')
    ]
    cur.executemany(
        """INSERT INTO quiz_results 
           (session_id, user_id, tu_danh_gia_truoc, diem_so, thoi_gian_lam) 
           VALUES (?, ?, ?, ?, ?)""",
        quiz_results_data
    )

    # 12. Thêm bài viết Bảng tin mẫu (blog_posts) - Đã đăng công khai
    sample_blogs = [
        (
            'Khởi động Mô hình Ngân hàng Thời gian Học đường: Một giờ bạn dạy - Một giờ bạn học',
            'Chào mừng toàn thể Thầy Cô giáo và các bạn học sinh đến với TimeBank EDU! Tại đây, mọi tri thức đều bình đẳng, 1 giờ dạy đổi lấy 1 giờ học. Hãy cùng nhau chia sẻ thế mạnh và giúp đỡ bạn bè cùng tiến bộ nhé!',
            '/static/img/newsletter_banner.svg',
            0,
            'da_dang',
            '2026-10-01 08:00:00'
        )
    ]
    cur.executemany(
        """INSERT INTO blog_posts 
           (tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        sample_blogs
    )
    
    conn.commit()


# ==============================================================================
# TỰ ĐỘNG KHỞI TẠO CƠ SỞ DỮ LIỆU Ở CẤP MODULE (DÀNH CHO GUNICORN / RENDER PAAS)
# ==============================================================================
# Gunicorn (gunicorn app:app) chỉ import module mà không chạy khối __main__.
# Khởi tạo tại đây giúp 13 bảng luôn được tạo sẵn sàng trước request đầu tiên,
# bọc try/except an toàn để không bao giờ làm sập ứng dụng.
try:
    init_db()
except Exception as e:
    app.logger.warning(f"Lỗi khởi tạo CSDL ở cấp module: {e}")


# ==============================================================================
# HÀM TRUY VẤN SỐ LIỆU THỐNG KÊ REALTIME VÀ VINH DANH GIA SƯ
# ==============================================================================
def get_realtime_stats(db):
    """
    Truy vấn số liệu thống kê thời gian thực từ cơ sở dữ liệu SQLite:
    - Tổng thành viên: Đếm số lượng học sinh và giáo viên
    - Phiên hoàn thành: Đếm số buổi học có trạng thái 'hoan_thanh'
    - Giờ lưu thông: Tổng số giờ đã được trao đổi thành công trong toàn trường
    - Kỹ năng sẵn sàng: Đếm các kỹ năng đã được duyệt và sẵn sàng chia sẻ
    """
    cur = db.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro = 'hoc_sinh'")
    tong_thanh_vien = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    phien_hoan_thanh = cur.fetchone()[0]
    
    cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    gio_luu_thong = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM skills WHERE trang_thai_duyet = 'da_duyet'")
    ky_nang_san_sang = cur.fetchone()[0]
    
    return {
        "tong_thanh_vien": tong_thanh_vien,
        "phien_hoan_thanh": phien_hoan_thanh,
        "gio_luu_thong": round(gio_luu_thong, 1),
        "ky_nang_san_sang": ky_nang_san_sang
    }


def get_top_tutors(db, limit=3):
    """
    Truy vấn tự động Top 3 Gia sư Học đường tích cực nhất:
    Tính toán dựa trên số giờ đã giảng dạy (sessions hoàn thành) và điểm đánh giá sao trung bình.
    """
    cur = db.cursor()
    query = """
        SELECT 
            u.id, 
            u.ma_hoc_sinh, 
            u.ho_ten, 
            u.lop, 
            COALESCE(SUM(s.so_gio), 0.0) AS so_gio_day,
            COUNT(s.id) AS so_phien_day,
            ROUND(COALESCE(AVG(r.so_sao), 5.0), 1) AS sao_tb
        FROM users u
        LEFT JOIN sessions s ON u.id = s.nguoi_day_id AND s.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON s.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE u.vai_tro = 'hoc_sinh'
        GROUP BY u.id, u.ma_hoc_sinh, u.ho_ten, u.lop
        ORDER BY so_gio_day DESC, sao_tb DESC
        LIMIT ?
    """
    cur.execute(query, (limit,))
    return cur.fetchall()


# ==============================================================================
# CÁC ROUTE ĐIỀU HƯỚNG CHÍNH (CONTROLLERS)
# ==============================================================================

@app.route("/")
def index():
    """
    Trang chủ (Landing Page) của Ngân hàng Thời gian Học đường.
    Gồm các khối chức năng sư phạm hoàn chỉnh, tích hợp số liệu thời gian thực
    và khối 'Vì cộng đồng' (tổng giờ công ích + nhiệm vụ gần nhất).
    """
    db = get_db()
    stats = get_realtime_stats(db)
    top_tutors = get_top_tutors(db, limit=3)
    
    # Số liệu cho khối 'Vì cộng đồng' trên Landing Page (Milestone M6)
    cur = db.cursor()
    cur.execute("""
        SELECT COALESCE(SUM(bien_dong), 0.0) 
        FROM credits_ledger 
        WHERE bien_dong > 0 AND (ly_do = 'nhiem_vu_cong_dong' OR ly_do LIKE '%nhiem_vu_cong_dong%')
    """)
    tong_gio_cong_ich = cur.fetchone()[0]

    cur.execute("""
        SELECT t.*, u.ho_ten AS ten_nguoi_tao,
               (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
        FROM community_tasks t
        JOIN users u ON t.nguoi_tao_id = u.id
        WHERE t.trang_thai IN ('mo_dang_ky', 'mo')
        ORDER BY t.id DESC
        LIMIT 3
    """)
    nhiem_vu_gan_nhat = cur.fetchall()

    community_stats = {
        "tong_gio_cong_ich": round(tong_gio_cong_ich, 1),
        "nhiem_vu_gan_nhat": nhiem_vu_gan_nhat
    }
    
    return render_template(
        "index.html",
        stats=stats,
        top_tutors=top_tutors,
        community_stats=community_stats
    )


# ------------------------------------------------------------------------------
# MILESTONE M1: ĐĂNG KÝ, ĐĂNG NHẬP, ĐĂNG XUẤT, HỒ SƠ & PHÂN QUYỀN
# ------------------------------------------------------------------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Đăng ký tài khoản học sinh mới:
    - Thu thập: mã học sinh, họ tên, lớp, mật khẩu (được băm an toàn), giờ rảnh
    - Cấp vốn khởi tạo mặc định: 2.0 giờ tín dụng
    - Tự động ghi sổ cái (credits_ledger) đảm bảo tính minh bạch
    """
    if "user_id" in session:
        return redirect(url_for("profile"))

    if request.method == "POST":
        ma_hoc_sinh = request.form.get("ma_hoc_sinh", "").strip()
        ho_ten = request.form.get("ho_ten", "").strip()
        lop = request.form.get("lop", "").strip()
        gio_ranh = request.form.get("gio_ranh", "").strip()
        mat_khau = request.form.get("mat_khau", "")
        mat_khau_xac_nhan = request.form.get("mat_khau_xac_nhan", "")

        # Kiểm tra tính hợp lệ của dữ liệu đầu vào
        if not ma_hoc_sinh or not ho_ten or not mat_khau:
            flash("Vui lòng điền đầy đủ các thông tin bắt buộc (*).", "danger")
            return render_template("register.html")

        if len(mat_khau) < 6:
            flash("Mật khẩu phải có độ dài tối thiểu từ 6 ký tự trở lên.", "danger")
            return render_template("register.html")

        if mat_khau != mat_khau_xac_nhan:
            flash("Mật khẩu xác nhận không khớp với mật khẩu đã nhập.", "danger")
            return render_template("register.html")

        db = get_db()
        cur = db.cursor()

        # Kiểm tra xem mã học sinh đã tồn tại chưa
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (ma_hoc_sinh,))
        if cur.fetchone():
            flash("Mã học sinh đã tồn tại trong hệ thống. Vui lòng kiểm tra lại!", "danger")
            return render_template("register.html")

        # Băm mật khẩu và tạo người dùng mới với số dư khởi đầu 2.0h
        hashed_password = generate_password_hash(mat_khau)
        initial_balance = 2.0

        cur.execute(
            """INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau)
               VALUES (?, ?, ?, 'hoc_sinh', ?, ?, ?)""",
            (ma_hoc_sinh, ho_ten, lop, initial_balance, gio_ranh, hashed_password)
        )
        new_user_id = cur.lastrowid

        # Ghi nhận vào sổ cái tín dụng (credits_ledger - nguyên tắc append-only)
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id)
               VALUES (?, ?, 'Khoản vốn tín dụng khởi đầu mở sổ học đường', NULL)""",
            (new_user_id, initial_balance)
        )
        db.commit()

        # Tự động đăng nhập vào session sau khi đăng ký thành công
        session["user_id"] = new_user_id
        session["ma_hoc_sinh"] = ma_hoc_sinh
        session["ho_ten"] = ho_ten
        session["vai_tro"] = "hoc_sinh"
        session["lop"] = lop
        session["so_du_gio"] = initial_balance

        flash("Chúc mừng bạn đã mở sổ thành công và nhận ngay 2.0 giờ tín dụng!", "success")
        return redirect(url_for("profile"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Đăng nhập hệ thống:
    - Xác thực mã đăng nhập và mật khẩu băm
    - Báo lỗi tiếng Việt rõ ràng khi sai thông tin
    - Chuyển hướng đúng vai trò (Admin -> /admin, Học sinh/Giáo viên -> /profile)
    """
    if "user_id" in session:
        if session.get("vai_tro") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("profile"))

    if request.method == "POST":
        ma_hoc_sinh = request.form.get("ma_hoc_sinh", "").strip()
        mat_khau = request.form.get("mat_khau", "")

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM users WHERE ma_hoc_sinh = ?", (ma_hoc_sinh,))
        user = cur.fetchone()

        # Kiểm tra người dùng và so khớp mật khẩu băm
        if not user or not user["mat_khau"] or not check_password_hash(user["mat_khau"], mat_khau):
            flash("Mã đăng nhập hoặc mật khẩu không chính xác!", "danger")
            return render_template("login.html"), 401

        # Lưu thông tin định danh vào Flask session
        session["user_id"] = user["id"]
        session["ma_hoc_sinh"] = user["ma_hoc_sinh"]
        session["ho_ten"] = user["ho_ten"]
        session["vai_tro"] = user["vai_tro"]
        session["lop"] = user["lop"]
        session["so_du_gio"] = user["so_du_gio"]

        flash(f"Đăng nhập thành công! Xin chào {user['ho_ten']}.", "success")

        # Chuyển hướng phù hợp theo vai trò
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)

        if user["vai_tro"] == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Đăng xuất: Xóa toàn bộ dữ liệu phiên và trở về trang chủ.
    """
    session.clear()
    flash("Bạn đã đăng xuất khỏi hệ thống thành công.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    """
    Trang hồ sơ cá nhân của người dùng:
    - Hiển thị họ tên, lớp, vai trò, thời gian rảnh
    - Hiển thị số dư giờ thời gian thực
    - Liệt kê lịch sử biến động từ Sổ cái tín dụng (credits_ledger)
    - Liệt kê các kỹ năng học sinh đã đăng ký
    """
    db = get_db()
    cur = db.cursor()
    
    # Lấy thông tin mới nhất từ cơ sở dữ liệu
    cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    user = cur.fetchone()
    
    if not user:
        session.clear()
        return redirect(url_for("login"))
        
    # Cập nhật lại số dư trong session
    session["so_du_gio"] = user["so_du_gio"]

    # Lấy lịch sử biến động tín dụng (credits_ledger)
    cur.execute(
        "SELECT * FROM credits_ledger WHERE user_id = ? ORDER BY id DESC LIMIT 15",
        (user["id"],)
    )
    ledger_entries = cur.fetchall()

    # Lấy danh sách kỹ năng đã đăng ký
    cur.execute(
        "SELECT * FROM skills WHERE user_id = ? ORDER BY id DESC",
        (user["id"],)
    )
    my_skills = cur.fetchall()

    # Điểm chạm 4: AI Tóm tắt phản hồi học sinh dành cho bạn gia sư (Gemini Pro)
    cur.execute(
        """SELECT so_sao, nhan_xet FROM ratings 
           WHERE nguoi_duoc_danh_gia_id = ? 
           ORDER BY id DESC LIMIT 20""",
        (user["id"],)
    )
    user_ratings = cur.fetchall()
    ai_feedback, _ = ai_summarize_feedback(db, user["id"], user_ratings)

    # Điểm chạm ghép cặp tự động: "Gợi ý cho bạn hôm nay" (Cache theo ngày)
    today_str = datetime.now().strftime("%Y-%m-%d")
    cache_key = (user["id"], today_str)

    if cache_key in DAILY_RECOMMENDATION_CACHE:
        daily_matches, is_live_rec, target_subject = DAILY_RECOMMENDATION_CACHE[cache_key]
    else:
        # 1. Tự suy ra môn HS đang cần học: từ lịch sử các phiên đã học (lĩnh vực kỹ năng)
        cur.execute("""
            SELECT sk.linh_vuc, COUNT(*) AS so_luong
            FROM sessions s
            JOIN skills sk ON s.skill_id = sk.id
            WHERE s.nguoi_hoc_id = ?
            GROUP BY sk.linh_vuc
            ORDER BY so_luong DESC, s.id DESC
            LIMIT 1
        """, (user["id"],))
        learned_sub = cur.fetchone()

        if learned_sub and learned_sub["linh_vuc"]:
            target_subject = learned_sub["linh_vuc"]
        else:
            # Chưa có lịch sử học -> Lấy lĩnh vực phổ biến nhất trên sàn
            cur.execute("""
                SELECT linh_vuc, COUNT(*) AS so_luong
                FROM skills
                WHERE trang_thai_duyet = 'da_duyet'
                GROUP BY linh_vuc
                ORDER BY so_luong DESC, id DESC
                LIMIT 1
            """)
            pop_sub = cur.fetchone()
            target_subject = pop_sub["linh_vuc"] if pop_sub else "Toán học"

        # 2. Lọc ứng viên có kỹ năng 'da_duyet' thuộc lĩnh vực đó + người khác chia sẻ
        search_kw = "Toán" if "toán" in target_subject.lower() else target_subject
        cur.execute("""
            SELECT s.*, u.ho_ten, u.lop, u.gio_ranh,
                   ROUND(COALESCE(AVG(r.so_sao), 5.0), 1) AS sao_tb
            FROM skills s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
            LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
            WHERE s.trang_thai_duyet = 'da_duyet'
              AND s.user_id != ?
              AND (s.linh_vuc LIKE ? OR s.tieu_de LIKE ?)
            GROUP BY s.id, u.id, u.ho_ten, u.lop, u.gio_ranh
            ORDER BY s.id DESC
        """, (user["id"], f"%{search_kw}%", f"%{search_kw}%"))
        subject_candidates = cur.fetchall()

        # 3. So khớp giờ rảnh đơn giản (chuỗi) với giờ rảnh của HS đang xem
        user_ranh = user["gio_ranh"] or ""

        def match_schedule(u_ranh, c_ranh):
            if not u_ranh or not c_ranh:
                return True
            u_l = u_ranh.lower()
            c_l = c_ranh.lower()
            keywords = ["thứ 2", "thứ 3", "thứ 4", "thứ 5", "thứ 6", "thứ 7", "chủ nhật", "sáng", "chiều", "tối"]
            matched_kws = [k for k in keywords if k in u_l]
            if matched_kws:
                return any(k in c_l for k in matched_kws)
            parts = [p.strip() for p in re.split(r'[,;\s]+', u_l) if len(p.strip()) >= 3]
            return any(p in c_l for p in parts)

        overlapping_candidates = [c for c in subject_candidates if match_schedule(user_ranh, c["gio_ranh"])]

        # Nếu danh sách trùng giờ rảnh < 3 người, bổ sung thêm các ứng viên cùng môn còn lại để đủ 3
        chosen_candidates = list(overlapping_candidates)
        if len(chosen_candidates) < 3:
            existing_ids = {c["id"] for c in chosen_candidates}
            for c in subject_candidates:
                if c["id"] not in existing_ids:
                    chosen_candidates.append(c)
                if len(chosen_candidates) >= 3:
                    break

        # 4. Gọi ai_matchmake có sẵn (hỗ trợ cả Gemini và Rule-based fallback, tự ghi ai_logs)
        if chosen_candidates:
            daily_matches, is_live_rec = ai_matchmake(
                db, user["id"], target_subject, "Cần củng cố", user_ranh, chosen_candidates
            )
        else:
            daily_matches, is_live_rec = [], is_ai_live()

        DAILY_RECOMMENDATION_CACHE[cache_key] = (daily_matches, is_live_rec, target_subject)

    # Milestone M4-lite: Thống kê cá nhân học sinh: Giờ đã dạy, Giờ đã học, Sao trung bình
    # 1. Tổng giờ đã dạy (các phiên hoàn thành đóng vai trò người dạy)
    cur.execute(
        """SELECT COALESCE(SUM(so_gio), 0.0) 
           FROM sessions 
           WHERE nguoi_day_id = ? AND trang_thai = 'hoan_thanh'""",
        (user["id"],)
    )
    hours_taught = cur.fetchone()[0]

    # 2. Tổng giờ đã học (các phiên hoàn thành đóng vai trò người học)
    cur.execute(
        """SELECT COALESCE(SUM(so_gio), 0.0) 
           FROM sessions 
           WHERE nguoi_hoc_id = ? AND trang_thai = 'hoan_thanh'""",
        (user["id"],)
    )
    hours_learned = cur.fetchone()[0]

    # 3. Số sao đánh giá trung bình nhận được từ bạn bè
    cur.execute(
        """SELECT ROUND(AVG(so_sao), 1), COUNT(*) 
           FROM ratings 
           WHERE nguoi_duoc_danh_gia_id = ?""",
        (user["id"],)
    )
    rating_row = cur.fetchone()
    avg_rating = rating_row[0] if rating_row and rating_row[0] is not None else 5.0
    rating_count = rating_row[1] if rating_row else 0

    return render_template(
        "profile.html",
        user=user,
        ledger_entries=ledger_entries,
        my_skills=my_skills,
        ai_feedback=ai_feedback,
        daily_matches=daily_matches,
        is_live_rec=is_live_rec,
        target_subject=target_subject,
        hours_taught=hours_taught,
        hours_learned=hours_learned,
        avg_rating=avg_rating,
        rating_count=rating_count
    )


@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Bảng điều khiển Quản trị hệ thống (/admin):
    - CHỈ ADMIN mới có quyền truy cập. Học sinh và giáo viên bị chặn 403 Forbidden.
    - Thống kê toàn trường: người dùng, số học sinh mở sổ, tổng giờ lưu thông
    - Quản lý danh sách tài khoản người dùng
    - Điểm chạm 5: AI Cảnh báo sớm quản trị học đường (học sinh ngưng học > 7 ngày, cặp đôi xung đột)
    """
    db = get_db()
    cur = db.cursor()

    # Lấy danh sách toàn bộ người dùng
    cur.execute("SELECT * FROM users ORDER BY id ASC")
    all_users = cur.fetchall()

    # Thống kê nhanh
    student_count = sum(1 for u in all_users if u["vai_tro"] == "hoc_sinh")
    total_credits = sum(u["so_du_gio"] for u in all_users if u["vai_tro"] == "hoc_sinh")

    cur.execute("SELECT COUNT(*) FROM skills WHERE trang_thai_duyet = 'cho_duyet'")
    pending_skills_count = cur.fetchone()[0]

    # Điểm chạm 5: Quét và đưa ra khuyến nghị can thiệp sư phạm sớm từ AI
    ai_warnings = ai_admin_early_warning(db, session["user_id"])

    # Milestone M-AI+: Thống kê khối "Kết quả học tập" lượng giá qua Quiz
    # 1. Điểm TB theo môn (linh_vuc) và % đạt >= 4/5 theo môn
    cur.execute("""
        SELECT 
            sk.linh_vuc,
            COUNT(qr.id) AS so_bai_lam,
            ROUND(AVG(qr.diem_so), 2) AS diem_tb,
            SUM(CASE WHEN qr.diem_so >= 4.0 THEN 1 ELSE 0 END) AS so_luong_gioi,
            SUM(CASE WHEN qr.diem_so >= 3.0 THEN 1 ELSE 0 END) AS so_luong_dat_chuan,
            ROUND(AVG(qr.tu_danh_gia_truoc), 2) AS tu_tin_truoc_tb
        FROM quiz_results qr
        JOIN sessions s ON qr.session_id = s.id
        JOIN skills sk ON s.skill_id = sk.id
        GROUP BY sk.linh_vuc
        ORDER BY so_bai_lam DESC, diem_tb DESC
    """)
    subject_stats_rows = cur.fetchall()

    subject_stats = []
    total_quizzes = 0
    total_ge_4 = 0
    for r in subject_stats_rows:
        cnt = r["so_bai_lam"]
        total_quizzes += cnt
        total_ge_4 += r["so_luong_gioi"]
        pct_gioi = round((r["so_luong_gioi"] / cnt * 100), 1) if cnt > 0 else 0.0
        pct_chuan_mon = round((r["so_luong_dat_chuan"] / cnt * 100), 1) if cnt > 0 else 0.0
        subject_stats.append({
            "linh_vuc": r["linh_vuc"],
            "so_bai_lam": cnt,
            "diem_tb": r["diem_tb"] or 0.0,
            "pct_gioi": pct_gioi,
            "pct_chuan": pct_chuan_mon,
            "tu_tin_truoc_tb": r["tu_tin_truoc_tb"] or 0.0
        })

    # % đạt >= 4/5 toàn trường
    pct_ge_4 = round((total_ge_4 / total_quizzes * 100), 1) if total_quizzes > 0 else 0.0

    # % phiên đạt chuẩn quiz (sessions.quiz_dat_chuan = 1)
    cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    completed_sessions_count = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh' AND quiz_dat_chuan = 1")
    passed_quiz_sessions_count = cur.fetchone()[0]

    pct_dat_chuan = round((passed_quiz_sessions_count / completed_sessions_count * 100), 1) if completed_sessions_count > 0 else 0.0

    # So sánh tự đánh giá trước vs điểm sau
    cur.execute("SELECT AVG(tu_danh_gia_truoc), AVG(diem_so) FROM quiz_results")
    avg_row = cur.fetchone()
    avg_before = round(avg_row[0], 2) if avg_row and avg_row[0] is not None else 0.0
    avg_after = round(avg_row[1], 2) if avg_row and avg_row[1] is not None else 0.0
    growth_diff = round(avg_after - avg_before, 2)

    learning_stats = {
        "subject_stats": subject_stats,
        "total_quizzes": total_quizzes,
        "total_ge_4": total_ge_4,
        "pct_ge_4": pct_ge_4,
        "completed_sessions_count": completed_sessions_count,
        "passed_quiz_sessions_count": passed_quiz_sessions_count,
        "pct_dat_chuan": pct_dat_chuan,
        "avg_before": avg_before,
        "avg_after": avg_after,
        "growth_diff": growth_diff
    }

    # Milestone M4-lite: Thống kê quản trị cấp trường
    # 1. Tổng số phiên học trong hệ thống
    cur.execute("SELECT COUNT(*) FROM sessions")
    total_sessions_count = cur.fetchone()[0]

    # 2. Tổng số giờ lưu thông thực tế (từ các phiên hoàn thành)
    cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    total_hours_circulated = cur.fetchone()[0]

    # 3. Top học sinh tích cực nhất (theo giờ dạy và cống hiến)
    cur.execute("""
        SELECT 
            u.id, u.ma_hoc_sinh, u.ho_ten, u.lop, u.so_du_gio,
            COALESCE(SUM(CASE WHEN s.nguoi_day_id = u.id AND s.trang_thai = 'hoan_thanh' THEN s.so_gio ELSE 0 END), 0.0) AS gio_day,
            COALESCE(SUM(CASE WHEN s.nguoi_hoc_id = u.id AND s.trang_thai = 'hoan_thanh' THEN s.so_gio ELSE 0 END), 0.0) AS gio_hoc,
            COUNT(DISTINCT CASE WHEN s.trang_thai = 'hoan_thanh' THEN s.id END) AS so_phien,
            ROUND(COALESCE((SELECT AVG(so_sao) FROM ratings WHERE nguoi_duoc_danh_gia_id = u.id), 5.0), 1) AS sao_tb
        FROM users u
        LEFT JOIN sessions s ON (s.nguoi_day_id = u.id OR s.nguoi_hoc_id = u.id)
        WHERE u.vai_tro = 'hoc_sinh'
        GROUP BY u.id, u.ma_hoc_sinh, u.ho_ten, u.lop, u.so_du_gio
        ORDER BY gio_day DESC, u.so_du_gio DESC
        LIMIT 5
    """)
    top_active_students = cur.fetchall()

    return render_template(
        "admin.html",
        users=all_users,
        student_count=student_count,
        total_credits=total_credits,
        total_sessions_count=total_sessions_count,
        total_hours_circulated=total_hours_circulated,
        top_active_students=top_active_students,
        pending_skills_count=pending_skills_count,
        ai_warnings=ai_warnings,
        learning_stats=learning_stats
    )


@app.route("/admin/export-csv")
@teacher_or_admin_required
def export_data_csv():
    """
    Xuất dữ liệu toàn diện phục vụ nghiên cứu sư phạm và báo cáo (Milestone M4-lite):
    - Gộp 5 bảng: sessions + credits_ledger + ratings + quiz_results + ai_logs
    - NGUYÊN TẮC BẢO MẬT: Họ tên -> Mã học sinh ẩn danh (CSV TUYỆT ĐỐI KHÔNG LỘ TÊN THẬT)
    - Tương thích 100% với Microsoft Excel (UTF-8 with BOM utf-8-sig)
    """
    db = get_db()
    cur = db.cursor()

    # Lấy bản đồ tên thật -> mã học sinh để lọc sạch mọi trường hợp lộ danh tính
    cur.execute("SELECT id, ma_hoc_sinh, ho_ten FROM users")
    all_users_meta = cur.fetchall()
    name_to_code = {u["ho_ten"]: u["ma_hoc_sinh"] for u in all_users_meta if u["ho_ten"]}

    def sanitize_text(text):
        if not text:
            return ""
        sanitized = str(text)
        for real_name, student_code in name_to_code.items():
            if len(real_name.strip()) > 1 and real_name in sanitized:
                sanitized = sanitized.replace(real_name, student_code)
        return sanitized

    output = io.StringIO()
    writer = csv.writer(output, lineterminator="\r\n")

    # Header báo cáo
    writer.writerow(["# NGAN HANG THOI GIAN HOC DUONG (TIMEBANK EDU) - DU LIEU NGHIEN CUU SU PHAM (DA AN DANH)"])
    writer.writerow(["# Thoi gian xuat:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
    writer.writerow([])

    # 1. BẢNG SESSIONS
    writer.writerow(["=== 1. BANG PHIEN HOC (SESSIONS) ==="])
    writer.writerow([
        "session_id", "ma_nguoi_day", "ma_nguoi_hoc", "linh_vuc", "tieu_de",
        "thoi_gian_bat_dau", "so_gio", "trang_thai", "checkin_day", "checkin_hoc", "quiz_dat_chuan"
    ])
    cur.execute("""
        SELECT 
            s.id, ud.ma_hoc_sinh AS ma_day, uh.ma_hoc_sinh AS ma_hoc, 
            sk.linh_vuc, sk.tieu_de, s.thoi_gian_bat_dau, s.so_gio, 
            s.trang_thai, s.checkin_day, s.checkin_hoc, s.quiz_dat_chuan
        FROM sessions s
        JOIN skills sk ON s.skill_id = sk.id
        JOIN users ud ON s.nguoi_day_id = ud.id
        JOIN users uh ON s.nguoi_hoc_id = uh.id
        ORDER BY s.id ASC
    """)
    for row in cur.fetchall():
        writer.writerow([
            row["id"], row["ma_day"], row["ma_hoc"], row["linh_vuc"],
            sanitize_text(row["tieu_de"]), row["thoi_gian_bat_dau"],
            row["so_gio"], row["trang_thai"], row["checkin_day"],
            row["checkin_hoc"], row["quiz_dat_chuan"]
        ])
    writer.writerow([])

    # 2. BẢNG CREDITS_LEDGER
    writer.writerow(["=== 2. BANG SO CAI TIN DUNG (CREDITS_LEDGER) ==="])
    writer.writerow(["ledger_id", "ma_hoc_sinh", "bien_dong_gio", "ly_do", "session_id", "thoi_gian"])
    cur.execute("""
        SELECT cl.id, u.ma_hoc_sinh, cl.bien_dong, cl.ly_do, cl.session_id, cl.thoi_gian
        FROM credits_ledger cl
        JOIN users u ON cl.user_id = u.id
        ORDER BY cl.id ASC
    """)
    for row in cur.fetchall():
        writer.writerow([
            row["id"], row["ma_hoc_sinh"], row["bien_dong"],
            sanitize_text(row["ly_do"]), row["session_id"] or "", row["thoi_gian"]
        ])
    writer.writerow([])

    # 3. BẢNG RATINGS
    writer.writerow(["=== 3. BANG DANH GIA TUONG HO (RATINGS) ==="])
    writer.writerow(["rating_id", "session_id", "ma_nguoi_danh_gia", "ma_nguoi_duoc_danh_gia", "so_sao", "nhan_xet"])
    cur.execute("""
        SELECT r.id, r.session_id, uf.ma_hoc_sinh AS ma_from, ut.ma_hoc_sinh AS ma_to, r.so_sao, r.nhan_xet
        FROM ratings r
        JOIN users uf ON r.nguoi_danh_gia_id = uf.id
        JOIN users ut ON r.nguoi_duoc_danh_gia_id = ut.id
        ORDER BY r.id ASC
    """)
    for row in cur.fetchall():
        writer.writerow([
            row["id"], row["session_id"], row["ma_from"], row["ma_to"],
            row["so_sao"], sanitize_text(row["nhan_xet"])
        ])
    writer.writerow([])

    # 4. BẢNG QUIZ_RESULTS
    writer.writerow(["=== 4. BANG KET QUA QUIZ TRAC NGHIEM (QUIZ_RESULTS) ==="])
    writer.writerow(["quiz_result_id", "session_id", "ma_hoc_sinh", "tu_danh_gia_truoc", "diem_so", "thoi_gian_lam"])
    cur.execute("""
        SELECT qr.id, qr.session_id, u.ma_hoc_sinh, qr.tu_danh_gia_truoc, qr.diem_so, qr.thoi_gian_lam
        FROM quiz_results qr
        JOIN users u ON qr.user_id = u.id
        ORDER BY qr.id ASC
    """)
    for row in cur.fetchall():
        writer.writerow([
            row["id"], row["session_id"], row["ma_hoc_sinh"],
            row["tu_danh_gia_truoc"], row["diem_so"], row["thoi_gian_lam"]
        ])
    writer.writerow([])

    # 5. BẢNG AI_LOGS
    writer.writerow(["=== 5. BANG NHAT KY MINH BACH AI (AI_LOGS) ==="])
    writer.writerow(["log_id", "ma_nguoi_dung", "chuc_nang", "input_tom_tat", "output_text", "thoi_gian"])
    cur.execute("""
        SELECT al.id, COALESCE(u.ma_hoc_sinh, 'He_thong') AS ma_user, al.chuc_nang, al.input_tom_tat, al.output_text, al.thoi_gian
        FROM ai_logs al
        LEFT JOIN users u ON al.user_id = u.id
        ORDER BY al.id ASC
    """)
    for row in cur.fetchall():
        writer.writerow([
            row["id"], row["ma_user"], row["chuc_nang"],
            sanitize_text(row["input_tom_tat"]), sanitize_text(row["output_text"]), row["thoi_gian"]
        ])

    csv_data = output.getvalue()
    # Mã hóa utf-8-sig để Excel mở không lỗi font tiếng Việt
    response = make_response(csv_data.encode("utf-8-sig"))
    response.headers["Content-Disposition"] = "attachment; filename=timebank_edu_export_anonymized.csv"
    response.headers["Content-Type"] = "text/csv; charset=utf-8-sig"
    return response


@app.route("/skills/approve")
@teacher_or_admin_required
def skills_approval():
    """
    Khu vực duyệt kỹ năng:
    - CHỈ GIÁO VIÊN VÀ ADMIN có quyền truy cập. Học sinh bị chặn 403 Forbidden.
    - Liệt kê các kỹ năng học sinh đăng ký và lý do kiểm duyệt từ AI (Gemini).
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.ho_ten, u.ma_hoc_sinh, u.lop
        FROM skills s
        JOIN users u ON s.user_id = u.id
        ORDER BY CASE WHEN s.trang_thai_duyet = 'cho_duyet' THEN 0 ELSE 1 END, s.id DESC
    """)
    skills_list = cur.fetchall()

    return render_template("skills_approval.html", skills=skills_list)


@app.route("/skills/approve/<int:skill_id>/<action>", methods=["POST"])
@teacher_or_admin_required
def approve_skill_action(skill_id, action):
    """
    Xử lý thao tác duyệt hoặc từ chối kỹ năng từ Giáo viên / Admin:
    - action: 'da_duyet' hoặc 'tu_choi'
    """
    if action not in ("da_duyet", "tu_choi"):
        flash("Hành động không hợp lệ.", "danger")
        return redirect(url_for("skills_approval"))

    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE skills SET trang_thai_duyet = ? WHERE id = ?", (action, skill_id))
    db.commit()

    action_label = "phê duyệt" if action == "da_duyet" else "từ chối"
    flash(f"Đã {action_label} kỹ năng #{skill_id} thành công.", "success")
    return redirect(url_for("skills_approval"))


# ------------------------------------------------------------------------------
# MILESTONE M2: ĐĂNG KỸ NĂNG, CHỢ KỸ NĂNG, ĐẶT LỊCH & LỊCH CỦA TÔI
# ------------------------------------------------------------------------------

@app.route("/skills")
def skills_market():
    """
    Chợ Kỹ Năng Học Đường:
    - CHỈ HIỂN THỊ những kỹ năng có trạng thái 'da_duyet' (đã qua kiểm duyệt sư phạm).
    - Các kỹ năng 'cho_duyet' hoặc 'tu_choi' tuyệt đối KHÔNG xuất hiện ở chợ.
    - Hỗ trợ tìm kiếm từ khóa và lọc danh mục: Toán, Lý, Hóa, Văn, Anh, Tin học, Đàn, Vẽ, Thể thao, Khác.
    """
    db = get_db()
    cur = db.cursor()
    
    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("linh_vuc", "").strip()
    
    sql = """
        SELECT 
            s.*, 
            u.ho_ten, 
            u.ma_hoc_sinh, 
            u.lop,
            ROUND(COALESCE(AVG(r.so_sao), 5.0), 1) AS sao_tb
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE s.trang_thai_duyet = 'da_duyet'
    """
    params = []
    
    if selected_category:
        sql += " AND s.linh_vuc = ?"
        params.append(selected_category)
        
    if search_query:
        sql += " AND (s.tieu_de LIKE ? OR s.mo_ta LIKE ? OR s.linh_vuc LIKE ?)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term])
        
    sql += " GROUP BY s.id, u.id, u.ho_ten, u.ma_hoc_sinh, u.lop ORDER BY s.id DESC"
    cur.execute(sql, params)
    skills = cur.fetchall()
    
    return render_template(
        "skills_market.html",
        skills=skills,
        search_query=search_query,
        selected_category=selected_category
    )


@app.route("/skills/matchmake", methods=["GET", "POST"])
@login_required
def ai_matchmake_view():
    """
    Điểm chạm 2: AI Gợi ý ghép cặp bạn học (Gemini Pro):
    - Học sinh nhập môn cần học, trình độ, khung giờ rảnh.
    - AI lọc trong danh sách các gia sư có kỹ năng 'da_duyet' và chọn ra 3 người phù hợp nhất.
    - Trình bày lời nhận xét sư phạm và nút 'Đặt lịch ngay'.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    
    cur.execute("SELECT gio_ranh FROM users WHERE id = ?", (user_id,))
    user_row = cur.fetchone()
    user_gio_ranh = user_row["gio_ranh"] if user_row and user_row["gio_ranh"] else ""
    
    matches = None
    form_data = None
    is_live = is_ai_live()
    
    if request.method == "POST":
        mon_hoc = request.form.get("mon_hoc", "").strip()
        trinh_do = request.form.get("trinh_do", "").strip()
        gio_ranh = request.form.get("gio_ranh", "").strip()
        form_data = {"mon_hoc": mon_hoc, "trinh_do": trinh_do, "gio_ranh": gio_ranh}
        
        if mon_hoc:
            # Lấy danh sách kỹ năng đã duyệt của các bạn khác
            cur.execute("""
                SELECT s.*, u.ho_ten, u.lop, u.gio_ranh,
                       ROUND(COALESCE(AVG(r.so_sao), 5.0), 1) AS sao_tb
                FROM skills s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
                LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
                WHERE s.trang_thai_duyet = 'da_duyet' AND s.user_id != ?
                GROUP BY s.id, u.id, u.ho_ten, u.lop, u.gio_ranh
                ORDER BY s.id DESC
            """, (user_id,))
            candidates = cur.fetchall()
            
            matches, is_live = ai_matchmake(db, user_id, mon_hoc, trinh_do, gio_ranh, candidates)
            
    return render_template(
        "ai_matchmake.html",
        matches=matches,
        form_data=form_data,
        user_gio_ranh=user_gio_ranh,
        is_live=is_live
    )


@app.route("/skills/new", methods=["GET", "POST"])
@login_required
def new_skill():
    """
    Đăng ký kỹ năng học đường mới:
    - Học sinh chọn lĩnh vực (Toán, Lý, Hóa, Văn, Anh, Vẽ, Đàn, Thể thao, Tin học, Khác), nhập tiêu đề & mô tả.
    - Tự động đặt trạng thái ban đầu là 'cho_duyet'.
    """
    valid_categories = ('Toán', 'Lý', 'Hóa', 'Văn', 'Anh', 'Vẽ', 'Đàn', 'Thể thao', 'Tin học', 'Khác')
    
    if request.method == "POST":
        linh_vuc = request.form.get("linh_vuc", "").strip()
        tieu_de = request.form.get("tieu_de", "").strip()
        mo_ta = request.form.get("mo_ta", "").strip()
        
        if not linh_vuc or not tieu_de or not mo_ta:
            flash("Vui lòng điền đầy đủ lĩnh vực, tiêu đề và mô tả kỹ năng.", "danger")
            return render_template("skills_new.html")
            
        if linh_vuc not in valid_categories:
            flash("Lĩnh vực đã chọn không hợp lệ.", "danger")
            return render_template("skills_new.html")
            
        db = get_db()
        cur = db.cursor()
        
        # Điểm chạm 1: AI Kiểm duyệt kỹ năng (Gemini Pro)
        is_approved, ai_reason, is_live = ai_moderate_skill(
            db, session["user_id"], linh_vuc, tieu_de, mo_ta
        )
        
        # Nếu PHU_HOP -> da_duyet (sẵn sàng trên Chợ kỹ năng)
        # Nếu KHONG_PHU_HOP -> cho_duyet (chuyển giáo viên duyệt tay)
        trang_thai_duyet = "da_duyet" if is_approved else "cho_duyet"
        ai_tag = "Hỗ trợ bởi AI (Gemini): " if is_live else "Hỗ trợ bởi AI (Chế độ cơ bản): "
        ly_do_luu = f"{ai_tag}{ai_reason}"
        
        cur.execute(
            """INSERT INTO skills 
               (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet) 
               VALUES (?, ?, ?, ?, ?, ?)""",
            (session["user_id"], linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_luu)
        )
        db.commit()
        
        if is_approved:
            flash(f"Đăng ký thành công! {ly_do_luu}. Kỹ năng đã sẵn sàng trên Chợ kỹ năng.", "success")
        else:
            flash(f"Kỹ năng đang ở trạng thái 'Chờ duyệt' để Giáo viên thẩm định thêm. {ly_do_luu}", "warning")
        return redirect(url_for("profile"))
        
    return render_template("skills_new.html")


@app.route("/skills/book/<int:skill_id>", methods=["GET"])
@login_required
def book_skill_page(skill_id):
    """
    Trang đặt lịch học kỹ năng chuyên biệt:
    - Hiển thị thông tin gia sư, kỹ năng, số dư hiện có.
    - Cung cấp form chọn thời gian hẹn học và thời lượng (tối đa 2.0h).
    - Submit trực tiếp tới POST /sessions/book.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.ho_ten, u.lop, u.gio_ranh, u.ma_hoc_sinh,
               ROUND(COALESCE(AVG(r.so_sao), 5.0), 1) AS sao_tb
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE s.id = ?
        GROUP BY s.id, u.id, u.ho_ten, u.lop, u.gio_ranh, u.ma_hoc_sinh
    """, (skill_id,))
    skill = cur.fetchone()
    if not skill or skill["trang_thai_duyet"] != "da_duyet":
        flash("Kỹ năng này chưa sẵn sàng để đặt lịch học!", "warning")
        return redirect(url_for("skills_market"))

    cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    current_user = cur.fetchone()

    return render_template("book_session_page.html", skill=skill, current_user=current_user)


@app.route("/sessions/book", methods=["POST"])
@login_required
def book_session():
    """
    Đặt lịch học kỹ năng:
    - Kiểm tra: Kỹ năng phải có trạng thái 'da_duyet'.
    - Kiểm tra: Không được tự đặt lịch kỹ năng của chính mình.
    - Kiểm tra: Thời lượng tối đa 2.0 giờ / phiên (0.5 <= so_gio <= 2.0).
    - Kiểm tra: Người học phải có đủ số dư giờ tín dụng.
    - Tạo phiên có trạng thái 'da_dat' để cả 2 bên (người dạy và người học) cùng theo dõi trong 'Lịch của tôi'.
    """
    try:
        skill_id = int(request.form.get("skill_id", 0))
    except (ValueError, TypeError):
        flash("Kỹ năng không hợp lệ.", "danger")
        return redirect(url_for("skills_market"))
        
    thoi_gian_bat_dau = request.form.get("thoi_gian_bat_dau", "").strip()
    try:
        so_gio = float(request.form.get("so_gio", 1.0))
    except (ValueError, TypeError):
        so_gio = 1.0
        
    if not thoi_gian_bat_dau:
        flash("Vui lòng chọn thời gian hẹn học.", "danger")
        return redirect(url_for("skills_market"))
        
    # Giới hạn tối đa 2 giờ / phiên
    if so_gio <= 0 or so_gio > 2.0:
        flash("Thời lượng mỗi buổi học tối đa là 2.0 giờ (và tối thiểu 0.5 giờ)!", "danger")
        return redirect(url_for("skills_market"))
        
    db = get_db()
    cur = db.cursor()
    
    # 1. Kiểm tra kỹ năng có tồn tại và đã duyệt chưa
    cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
    skill = cur.fetchone()
    if not skill or skill["trang_thai_duyet"] != "da_duyet":
        flash("Kỹ năng này chưa sẵn sàng hoặc chưa được phê duyệt sư phạm!", "danger")
        return redirect(url_for("skills_market"))
        
    # 2. Không được tự đặt lịch kỹ năng của chính mình
    if skill["user_id"] == session["user_id"]:
        flash("Bạn không thể tự đặt lịch kỹ năng của chính mình!", "warning")
        return redirect(url_for("skills_market"))
        
    # 3. Kiểm tra số dư người học
    cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    learner = cur.fetchone()
    if not learner or learner["so_du_gio"] < so_gio:
        flash(f"Số dư tín dụng của bạn không đủ để đặt lịch buổi học này! (Hiện có: {learner['so_du_gio']:.1f}h, Cần: {so_gio:.1f}h). Hãy dạy kèm bạn bè để tích thêm giờ nhé!", "danger")
        return redirect(url_for("skills_market"))
        
    # 4. Lấy thông tin gia sư
    cur.execute("SELECT ho_ten FROM users WHERE id = ?", (skill["user_id"],))
    tutor = cur.fetchone()
    tutor_name = tutor["ho_ten"] if tutor else "Gia sư"
    
    # 5. Tạo mã QR ngẫu nhiên và lưu phiên 'da_dat'
    ma_qr = f"TB-QR-{skill_id}-{secrets.token_hex(4).upper()}"
    
    cur.execute(
        """INSERT INTO sessions 
           (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan)
           VALUES (?, ?, ?, ?, ?, 'da_dat', ?, 0, 0, NULL, 0)""",
        (skill_id, skill["user_id"], session["user_id"], thoi_gian_bat_dau, so_gio, ma_qr)
    )
    db.commit()
    
    flash(f"Đặt lịch học thành công với {tutor_name} ({so_gio:.1f} giờ)! Cả hai bạn đều có thể theo dõi trong 'Lịch của tôi'.", "success")
    return redirect(url_for("my_schedule"))


@app.route("/my-schedule")
@login_required
def my_schedule():
    """
    Trang 'Lịch của tôi':
    - Hiển thị danh sách các phiên học của người dùng hiện tại ở cả 2 vai trò:
      1. Phiên tôi dạy (Gia sư): Người dạy thấy bạn học nào đã đặt lịch với mình.
      2. Phiên tôi học (Người học): Người học thấy gia sư nào sẽ kèm cặp mình.
    - Cả 2 bên đều thấy phiên với trạng thái 'da_dat' và mã QR xác thực.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    session["so_du_gio"] = user["so_du_gio"]
    
    # 1. Danh sách các phiên người dùng đóng vai trò Người Dạy (Gia sư)
    cur.execute(
        """SELECT 
               s.*, 
               sk.tieu_de, 
               sk.linh_vuc, 
               u.ho_ten AS ten_nguoi_hoc, 
               u.lop AS lop_nguoi_hoc, 
               u.ma_hoc_sinh AS ma_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users u ON s.nguoi_hoc_id = u.id
           WHERE s.nguoi_day_id = ?
           ORDER BY s.id DESC""",
        (user_id,)
    )
    teaching_sessions = cur.fetchall()
    
    # 2. Danh sách các phiên người dùng đóng vai trò Người Học
    cur.execute(
        """SELECT 
               s.*, 
               sk.tieu_de, 
               sk.linh_vuc, 
               u.ho_ten AS ten_nguoi_day, 
               u.lop AS lop_nguoi_day, 
               u.ma_hoc_sinh AS ma_nguoi_day
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users u ON s.nguoi_day_id = u.id
           WHERE s.nguoi_hoc_id = ?
           ORDER BY s.id DESC""",
        (user_id,)
    )
    learning_sessions = cur.fetchall()
    
    upcoming_count = sum(1 for s in teaching_sessions if s["trang_thai"] == "da_dat") + \
                     sum(1 for s in learning_sessions if s["trang_thai"] == "da_dat")
                     
    return render_template(
        "my_schedule.html",
        user=user,
        teaching_sessions=teaching_sessions,
        learning_sessions=learning_sessions,
        upcoming_count=upcoming_count
    )


# ==============================================================================
# MILESTONE M3: VÍ TÍN DỤNG, CHI TIẾT PHIÊN HỌC & ĐIỂM DANH CHECK-IN QR 2 CHIỀU
# ==============================================================================

def generate_qr_base64(data_text):
    """
    Tạo ảnh mã QR từ chuỗi dữ liệu (mã ngẫu nhiên ma_qr) và chuyển đổi thành
    định dạng ảnh Base64 (PNG) hiển thị trực tiếp trên giao diện HTML.
    
    Ý nghĩa sư phạm và kỹ thuật:
    - Học sinh không cần kết nối máy in hay tạo file tạm trên máy chủ.
    - Mã QR hiển thị trực tiếp trên điện thoại để bạn học cùng quét và xác thực.
    """
    if not data_text:
        return ""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(data_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


@app.route("/wallet")
@login_required
def wallet():
    """
    Trang 'Ví của tôi' (Sổ cái tín dụng thời gian):
    - Hiển thị số dư khả dụng hiện tại của học sinh / giáo viên.
    - Thống kê tổng giờ đã nhận (+) từ các buổi dạy kèm hoặc công tác phục vụ cộng đồng.
    - Thống kê tổng giờ đã dùng (-) cho việc tham gia các khóa trao đổi tri thức.
    - Liệt kê toàn bộ lịch sử biến động trong sổ cái credits_ledger theo thứ tự
      mới nhất xếp trước (ORDER BY id DESC).
    - Tuân thủ nguyên tắc 'Append-Only': Sổ cái chỉ ghi nhận thêm dòng mới, không sửa/xóa.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    
    # 1. Truy vấn thông tin tài khoản và cập nhật số dư phiên làm việc
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        flash("Không tìm thấy thông tin người dùng!", "danger")
        return redirect(url_for("index"))
    session["so_du_gio"] = user["so_du_gio"]
    
    # 2. Truy vấn lịch sử biến động sổ cái tín dụng (mới nhất xếp trước)
    cur.execute(
        """SELECT * FROM credits_ledger 
           WHERE user_id = ? 
           ORDER BY id DESC""",
        (user_id,)
    )
    ledger_entries = cur.fetchall()
    
    # 3. Tính toán tổng tích lũy nhận và tổng giờ đã trao đổi
    total_earned = sum(item["bien_dong"] for item in ledger_entries if item["bien_dong"] > 0)
    total_spent = abs(sum(item["bien_dong"] for item in ledger_entries if item["bien_dong"] < 0))
    
    return render_template(
        "wallet.html",
        user=user,
        total_earned=total_earned,
        total_spent=total_spent,
        ledger_entries=ledger_entries
    )


@app.route("/sessions/<int:session_id>")
@login_required
def session_detail(session_id):
    """
    Trang chi tiết phiên học và xác thực check-in:
    - Hiển thị thông tin phiên: kỹ năng trao đổi, gia sư, học sinh, thời gian hẹn.
    - Hiển thị mã QR xác thực 2 bên (sinh ngẫu nhiên bằng chuỗi base64).
    - Thể hiện trạng thái check-in của cả 2 bên (checkin_day, checkin_hoc).
    - Cung cấp nút Check-in cho từng bên và nút 'Xác nhận hoàn thành' cho người dạy.
    - Phân quyền: Chỉ người dạy, người học trong phiên, hoặc Giáo viên/Admin mới được xem.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    
    cur.execute(
        """SELECT 
               s.*,
               sk.tieu_de,
               sk.linh_vuc,
               sk.mo_ta,
               ud.ho_ten AS ten_nguoi_day,
               ud.lop AS lop_nguoi_day,
               ud.ma_hoc_sinh AS ma_nguoi_day,
               uh.ho_ten AS ten_nguoi_hoc,
               uh.lop AS lop_nguoi_hoc,
               uh.ma_hoc_sinh AS ma_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.id = ?""",
        (session_id,)
    )
    session_data = cur.fetchone()
    
    if not session_data:
        flash("Phiên học không tồn tại trong hệ thống!", "danger")
        return redirect(url_for("my_schedule"))
        
    is_teacher = (session_data["nguoi_day_id"] == user_id)
    is_learner = (session_data["nguoi_hoc_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))
    
    # Bảo mật: Không cho học sinh ngoài cuộc xem chi tiết phiên của người khác
    if not (is_teacher or is_learner or is_admin):
        flash("Bạn không có quyền truy cập thông tin phiên học này!", "danger")
        return redirect(url_for("my_schedule"))
        
    # Kiểm tra số lượng câu hỏi quiz và kết quả làm bài (Milestone M-AI+)
    cur.execute("SELECT COUNT(*) FROM quiz_questions WHERE session_id = ?", (session_id,))
    quiz_question_count = cur.fetchone()[0]

    cur.execute(
        """SELECT * FROM quiz_results 
           WHERE session_id = ? AND user_id = ? 
           ORDER BY id DESC LIMIT 1""",
        (session_id, session_data["nguoi_hoc_id"])
    )
    quiz_result = cur.fetchone()

    # Truy vấn thông tin đánh giá tương hỗ của phiên (Milestone M4-lite)
    cur.execute(
        """SELECT r.*, u_from.ho_ten AS ten_nguoi_danh_gia, u_to.ho_ten AS ten_nguoi_duoc_danh_gia
           FROM ratings r
           JOIN users u_from ON r.nguoi_danh_gia_id = u_from.id
           JOIN users u_to ON r.nguoi_duoc_danh_gia_id = u_to.id
           WHERE r.session_id = ?""",
        (session_id,)
    )
    all_session_ratings = cur.fetchall()

    my_rating = next((r for r in all_session_ratings if r["nguoi_danh_gia_id"] == user_id), None)
    partner_rating = next((r for r in all_session_ratings if r["nguoi_duoc_danh_gia_id"] == user_id), None)

    # Tạo mã QR dạng Base64 để hiển thị trực quan
    qr_b64 = generate_qr_base64(session_data["ma_qr"] or f"TB-SES-{session_id}")
    
    return render_template(
        "session_detail.html",
        session_data=session_data,
        qr_b64=qr_b64,
        is_teacher=is_teacher,
        is_learner=is_learner,
        is_admin=is_admin,
        quiz_question_count=quiz_question_count,
        quiz_result=quiz_result,
        all_session_ratings=all_session_ratings,
        my_rating=my_rating,
        partner_rating=partner_rating
    )


@app.route("/sessions/<int:session_id>/ai-lesson-plan", methods=["POST"])
@login_required
def generate_ai_lesson_plan_route(session_id):
    """
    Điểm chạm 3: AI Soạn dàn ý buổi học (Gemini Pro):
    - Người dạy (Gia sư) hoặc GV/Admin yêu cầu AI soạn dàn ý sư phạm.
    - Tạo cấu trúc 60 phút: Mở đầu 5', Trọng tâm 25', Luyện tập 20', Tổng kết 10'.
    - Lưu kết quả vào sessions.dan_y_ai và ghi nhận vào ai_logs.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")

    cur.execute(
        """SELECT s.*, sk.tieu_de, sk.linh_vuc, sk.mo_ta 
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           WHERE s.id = ?""",
        (session_id,)
    )
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))

    # Kiểm tra quyền: người dạy hoặc GV/Admin
    if s_row["nguoi_day_id"] != user_id and user_role not in ("admin", "giao_vien"):
        flash("Chỉ người dạy (Gia sư) của phiên học này mới có thể nhờ AI soạn dàn ý!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    dan_y, is_live = ai_generate_lesson_plan(
        db, user_id, session_id,
        s_row["tieu_de"], s_row["linh_vuc"], s_row["mo_ta"],
        s_row["so_gio"]
    )

    cur.execute(
        "UPDATE sessions SET dan_y_ai = ? WHERE id = ?",
        (dan_y, session_id)
    )
    db.commit()

    if is_live:
        flash("AI (Gemini Pro) đã soạn xong dàn ý buổi học 4 bước chuẩn 60 phút!", "success")
    else:
        flash("Đã tạo dàn ý buổi học 4 bước chuẩn 60 phút (Hỗ trợ bởi AI - Chế độ cơ bản)!", "info")

    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/sessions/<int:session_id>/checkin", methods=["POST"])
@login_required
def checkin_session(session_id):
    """
    Xử lý điểm danh check-in phiên học (quét mã QR / bấm nút xác thực):
    - Người dạy xác thực: cập nhật checkin_day = 1.
    - Người học xác thực: cập nhật checkin_hoc = 1.
    - Điều kiện: Phiên học phải đang ở trạng thái 'da_dat'.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    role_claim = request.form.get("role", "").strip()
    
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))
        
    if s_row["trang_thai"] != "da_dat":
        flash(f"Phiên học hiện đang ở trạng thái '{s_row['trang_thai']}', không thể điểm danh check-in!", "warning")
        return redirect(url_for("session_detail", session_id=session_id))
        
    updated = False
    
    # 1. Trường hợp người dạy check-in
    if role_claim == "teacher" or (not role_claim and s_row["nguoi_day_id"] == user_id):
        if s_row["nguoi_day_id"] == user_id or user_role in ("admin", "giao_vien"):
            cur.execute("UPDATE sessions SET checkin_day = 1 WHERE id = ?", (session_id,))
            updated = True
            flash("Người dạy (Gia sư) đã check-in xác nhận thành công!", "success")
        else:
            flash("Bạn không phải người dạy trong phiên học này!", "danger")
            return redirect(url_for("session_detail", session_id=session_id))
            
    # 2. Trường hợp người học check-in
    elif role_claim == "learner" or (not role_claim and s_row["nguoi_hoc_id"] == user_id):
        if s_row["nguoi_hoc_id"] == user_id or user_role in ("admin", "giao_vien"):
            cur.execute("UPDATE sessions SET checkin_hoc = 1 WHERE id = ?", (session_id,))
            updated = True
            flash("Người học (Học sinh) đã check-in xác nhận thành công!", "success")
        else:
            flash("Bạn không phải người học trong phiên học này!", "danger")
            return redirect(url_for("session_detail", session_id=session_id))
    else:
        flash("Thông tin vai trò điểm danh không hợp lệ!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))
        
    if updated:
        db.commit()
        
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/sessions/<int:session_id>/complete", methods=["POST"])
@login_required
def complete_session(session_id):
    """
    Xác nhận hoàn thành phiên học & Chuyển giờ tín dụng:
    1. Kiểm tra quyền thao tác: Chỉ người dạy (hoặc Quản trị viên/Giáo viên) mới được xác nhận hoàn thành.
    2. Kiểm tra điều kiện bắt buộc: CẢ HAI BÊN ĐỀU PHẢI CHECK-IN (checkin_day == 1 VÀ checkin_hoc == 1).
       Nếu chỉ 1 bên hoặc chưa bên nào check-in -> Chặn lại và báo lỗi tiếng Việt.
    3. Thực hiện giao dịch nguyên tử (Atomic Transaction):
       - INSERT 2 dòng vào sổ cái tín dụng (credits_ledger):
         + Người dạy nhận +so_gio với ly_do = 'day_hoc'
         + Người học đổi -so_gio với ly_do = 'hoc'
       - Cập nhật số dư so_du_gio trong bảng users cho cả 2 bạn.
       - Cập nhật trạng thái phiên sessions.trang_thai = 'hoan_thanh'.
       - Commit cơ sở dữ liệu.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))
        
    is_teacher = (s_row["nguoi_day_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))
    
    if not (is_teacher or is_admin):
        flash("Chỉ bạn gia sư (người dạy) hoặc Quản trị viên mới có quyền xác nhận hoàn thành buổi học!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))
        
    if s_row["trang_thai"] != "da_dat":
        flash(f"Phiên học này hiện đang ở trạng thái '{s_row['trang_thai']}', không thể xác nhận hoàn thành lại!", "warning")
        return redirect(url_for("session_detail", session_id=session_id))
        
    # ĐIỀU KIỆN TIÊN QUYẾT NGHIỆM THU: CẢ HAI BÊN ĐỀU PHẢI CHECK-IN
    if s_row["checkin_day"] != 1 or s_row["checkin_hoc"] != 1:
        flash("Chưa thể hoàn thành! Yêu cầu cả hai bên (Người dạy và Người học) đều phải check-in.", "danger")
        return redirect(url_for("session_detail", session_id=session_id))
        
    so_gio = float(s_row["so_gio"])
    nguoi_day_id = s_row["nguoi_day_id"]
    nguoi_hoc_id = s_row["nguoi_hoc_id"]
    
    try:
        # Ghi nhận 2 dòng credits_ledger (Append-Only)
        # Dòng 1: Người dạy nhận +so_gio
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
               VALUES (?, ?, 'day_hoc', ?, CURRENT_TIMESTAMP)""",
            (nguoi_day_id, so_gio, session_id)
        )
        
        # Dòng 2: Người học dùng -so_gio
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
               VALUES (?, ?, 'hoc', ?, CURRENT_TIMESTAMP)""",
            (nguoi_hoc_id, -so_gio, session_id)
        )
        
        # Cập nhật số dư người dạy (+so_gio)
        cur.execute(
            "UPDATE users SET so_du_gio = so_du_gio + ? WHERE id = ?",
            (so_gio, nguoi_day_id)
        )
        
        # Cập nhật số dư người học (-so_gio)
        cur.execute(
            "UPDATE users SET so_du_gio = so_du_gio - ? WHERE id = ?",
            (so_gio, nguoi_hoc_id)
        )
        
        # Cập nhật trạng thái phiên thành 'hoan_thanh'
        cur.execute(
            "UPDATE sessions SET trang_thai = 'hoan_thanh' WHERE id = ?",
            (session_id,)
        )
        
        db.commit()
        
        # Đồng bộ số dư trong session người dùng đang đăng nhập
        if user_id == nguoi_day_id:
            cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (user_id,))
            session["so_du_gio"] = cur.fetchone()[0]
            
        flash(f"Buổi học đã hoàn thành xuất sắc! Đã cộng +{so_gio:.1f}h cho người dạy và trừ -{so_gio:.1f}h của người học.", "success")
    except Exception as e:
        db.rollback()
        app.logger.error(f"Lỗi khi hoàn thành phiên học và chuyển giờ: {e}")
        flash(f"Có lỗi xảy ra trong quá trình hoàn thành phiên học: {e}", "danger")
        
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/sessions/<int:session_id>/rate", methods=["POST"])
@login_required
def rate_session(session_id):
    """
    Đánh giá tương hỗ sau khi phiên học hoàn thành (Milestone M4-lite):
    - Người dạy đánh giá Người học (1-5 sao + nhận xét)
    - Người học đánh giá Người dạy (1-5 sao + nhận xét)
    - Mỗi chiều CHỈ ĐƯỢC 1 LẦN DUY NHẤT. Nếu gửi lần 2 -> Bị chặn và cảnh báo.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")

    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))

    if s_row["trang_thai"] != "hoan_thanh":
        flash("Chỉ có thể đánh giá sau khi buổi học đã hoàn thành!", "warning")
        return redirect(url_for("session_detail", session_id=session_id))

    is_teacher = (s_row["nguoi_day_id"] == user_id)
    is_learner = (s_row["nguoi_hoc_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))

    if not (is_teacher or is_learner or is_admin):
        flash("Bạn không phải thành viên tham gia phiên học này!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    # Xác định người được đánh giá
    if is_teacher:
        target_id = s_row["nguoi_hoc_id"]
    elif is_learner:
        target_id = s_row["nguoi_day_id"]
    else:
        # Admin kiểm thử
        target_id = s_row["nguoi_hoc_id"] if request.form.get("target_role") == "learner" else s_row["nguoi_day_id"]

    # ĐIỀU KIỆN TIÊN QUYẾT: CHẶN ĐÁNH GIÁ LẦN 2
    cur.execute(
        "SELECT id FROM ratings WHERE session_id = ? AND nguoi_danh_gia_id = ?",
        (session_id, user_id)
    )
    existing = cur.fetchone()
    if existing:
        flash("Bạn đã đánh giá buổi học này rồi! Mỗi thành viên chỉ được đánh giá 1 lần duy nhất để bảo đảm tính khách quan.", "warning")
        return redirect(url_for("session_detail", session_id=session_id))

    try:
        so_sao = int(request.form.get("so_sao", 5))
        if so_sao < 1 or so_sao > 5:
            so_sao = 5
    except (ValueError, TypeError):
        so_sao = 5

    nhan_xet = request.form.get("nhan_xet", "").strip()

    cur.execute(
        """INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, user_id, target_id, so_sao, nhan_xet)
    )
    db.commit()

    flash("Cảm ơn bạn đã gửi đánh giá tương hỗ! Phản hồi của bạn giúp cộng đồng học tập ngày càng gắn kết và tiến bộ.", "success")
    return redirect(url_for("session_detail", session_id=session_id))


# ==============================================================================
# MILESTONE M-AI+: TRẮC NGHIỆM AI (QUIZ ADAPTIVE) & LƯỢNG GIÁ KẾT QUẢ HỌC TẬP
# ==============================================================================

@app.route("/sessions/<int:session_id>/ai-generate-quiz", methods=["POST"])
@login_required
def generate_ai_quiz_route(session_id):
    """
    Điểm chạm AI+: Người dạy bấm 'Nhờ AI tạo quiz' sau phiên hoàn thành:
    - Gemini đọc dan_y_ai + mo_ta kỹ năng -> tạo 5 câu trắc nghiệm 4 lựa chọn (dễ->khó, TV, giọng vui vẻ)
    - Lưu vào quiz_questions và ghi vết vào ai_logs (chuc_nang = 'tao_quiz')
    - Phân quyền: Người dạy của phiên hoặc Giáo viên / Admin
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")

    cur.execute(
        """SELECT s.*, sk.tieu_de, sk.linh_vuc, sk.mo_ta 
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           WHERE s.id = ?""",
        (session_id,)
    )
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))

    # Phân quyền: người dạy hoặc GV/Admin
    if s_row["nguoi_day_id"] != user_id and user_role not in ("admin", "giao_vien"):
        flash("Chỉ bạn gia sư (người dạy) hoặc Giáo viên mới có thể nhờ AI tạo bộ câu hỏi quiz!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    if s_row["trang_thai"] != "hoan_thanh":
        flash("Buổi học cần được xác nhận hoàn thành trước khi tạo Quiz lượng giá!", "warning")
        return redirect(url_for("session_detail", session_id=session_id))

    questions, is_live = ai_generate_quiz(
        db, user_id, session_id,
        s_row["tieu_de"], s_row["linh_vuc"], s_row["mo_ta"],
        s_row["dan_y_ai"] or ""
    )

    if is_live:
        flash("Trợ lý AI (Gemini Pro) đã thiết kế thành công bộ 5 câu hỏi trắc nghiệm lượng giá vui nhộn!", "success")
    else:
        flash("Đã khởi tạo bộ 5 câu hỏi trắc nghiệm chuẩn sư phạm (Hỗ trợ bởi AI - Chế độ cơ bản)!", "info")

    return redirect(url_for("session_quiz_view", session_id=session_id))


@app.route("/sessions/<int:session_id>/quiz")
@login_required
def session_quiz_view(session_id):
    """
    Trang làm và xem kết quả Quiz trắc nghiệm:
    - Người học: Tự đánh giá mức độ tự tin trước buổi học (1-5 sao) và làm 5 câu trắc nghiệm (1 lần duy nhất).
    - Sau khi làm: Hiển thị điểm số, tỷ lệ %, đáp án đúng/sai để học sinh ôn lại.
    - Người dạy / GV / Admin: Có thể vào xem trước câu hỏi hoặc xem kết quả làm bài của học sinh.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")

    cur.execute(
        """SELECT 
               s.*,
               sk.tieu_de,
               sk.linh_vuc,
               sk.mo_ta,
               ud.ho_ten AS ten_nguoi_day,
               ud.lop AS lop_nguoi_day,
               ud.ma_hoc_sinh AS ma_nguoi_day,
               uh.ho_ten AS ten_nguoi_hoc,
               uh.lop AS lop_nguoi_hoc,
               uh.ma_hoc_sinh AS ma_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.id = ?""",
        (session_id,)
    )
    session_data = cur.fetchone()
    if not session_data:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))

    is_teacher = (session_data["nguoi_day_id"] == user_id)
    is_learner = (session_data["nguoi_hoc_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))

    if not (is_teacher or is_learner or is_admin):
        flash("Bạn không có quyền truy cập bài kiểm tra của phiên học này!", "danger")
        return redirect(url_for("my_schedule"))

    # Lấy danh sách câu hỏi
    cur.execute(
        """SELECT * FROM quiz_questions 
           WHERE session_id = ? 
           ORDER BY id ASC""",
        (session_id,)
    )
    questions = cur.fetchall()

    # Lấy kết quả làm bài của học sinh (nếu có)
    cur.execute(
        """SELECT * FROM quiz_results 
           WHERE session_id = ? AND user_id = ? 
           ORDER BY id DESC LIMIT 1""",
        (session_id, session_data["nguoi_hoc_id"])
    )
    quiz_result = cur.fetchone()

    return render_template(
        "session_quiz.html",
        session_data=session_data,
        questions=questions,
        quiz_result=quiz_result,
        is_teacher=is_teacher,
        is_learner=is_learner,
        is_admin=is_admin
    )


@app.route("/sessions/<int:session_id>/quiz/submit", methods=["POST"])
@login_required
def submit_quiz_route(session_id):
    """
    Nộp bài làm Quiz trắc nghiệm:
    1. Kiểm tra quyền: Người học của phiên (hoặc admin kiểm thử).
    2. CHẶN LÀM LẦN 2: Kiểm tra bảng quiz_results, nếu đã có kết quả -> Chặn lại và cảnh báo.
    3. Ghi nhận 'tu_danh_gia_truoc' (1-5 sao).
    4. Chấm điểm tự động từng câu (so khớp dap_an_dung).
    5. Đạt >= 60% (>= 3/5 câu) -> cập nhật sessions.quiz_dat_chuan = 1.
    6. Quiz dùng để xác nhận kết quả cho giáo viên thấy, KHÔNG chặn việc cộng/trừ giờ của học sinh.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")

    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))

    is_learner = (s_row["nguoi_hoc_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))

    if not (is_learner or is_admin):
        flash("Chỉ người học trong phiên mới có quyền nộp bài làm Quiz!", "danger")
        return redirect(url_for("session_detail", session_id=session_id))

    # CHẶN LÀM LẦN 2 (YÊU CẦU NGHIỆM THU BẮT BUỘC)
    cur.execute(
        "SELECT * FROM quiz_results WHERE session_id = ? AND user_id = ?",
        (session_id, user_id)
    )
    existing_result = cur.fetchone()
    if existing_result:
        flash("Bạn đã hoàn thành bài quiz này rồi! Mỗi học sinh chỉ được làm bài 1 lần duy nhất để đảm bảo tính khách quan sư phạm.", "warning")
        return redirect(url_for("session_quiz_view", session_id=session_id))

    # Lấy danh sách câu hỏi
    cur.execute("SELECT * FROM quiz_questions WHERE session_id = ? ORDER BY id ASC", (session_id,))
    questions = cur.fetchall()
    if not questions:
        flash("Chưa có bộ câu hỏi nào được tạo cho buổi học này!", "warning")
        return redirect(url_for("session_detail", session_id=session_id))

    # Lấy tự đánh giá trước (1-5 sao)
    try:
        tu_danh_gia_truoc = float(request.form.get("tu_danh_gia_truoc", 3.0))
        if tu_danh_gia_truoc < 1.0 or tu_danh_gia_truoc > 5.0:
            tu_danh_gia_truoc = 3.0
    except (ValueError, TypeError):
        tu_danh_gia_truoc = 3.0

    # Chấm điểm tự động
    correct_count = 0
    total_count = len(questions)
    for q in questions:
        field_name = f"question_{q['id']}"
        selected = request.form.get(field_name, "").strip().upper()
        if selected and selected == q["dap_an_dung"].strip().upper():
            correct_count += 1

    diem_so = float(correct_count)

    # Lưu kết quả vào quiz_results
    cur.execute(
        """INSERT INTO quiz_results 
           (session_id, user_id, tu_danh_gia_truoc, diem_so, thoi_gian_lam) 
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (session_id, user_id, tu_danh_gia_truoc, diem_so)
    )

    # Đạt >= 60% (tức >= 3/5 câu) -> cập nhật sessions.quiz_dat_chuan = 1
    pct = (correct_count / total_count) if total_count > 0 else 0.0
    if pct >= 0.60:
        cur.execute("UPDATE sessions SET quiz_dat_chuan = 1 WHERE id = ?", (session_id,))
        db.commit()
        flash(f"Chúc mừng em! Em đã làm đúng {correct_count}/{total_count} câu ({pct*100:.0f}%) — ĐẠT CHUẨN KIẾN THỨC!", "success")
    else:
        db.commit()
        flash(f"Em đã hoàn thành bài quiz: đúng {correct_count}/{total_count} câu ({pct*100:.0f}%). Hãy ôn lại các đáp án giải thích để nắm vững kiến thức hơn nhé!", "info")

    return redirect(url_for("session_quiz_view", session_id=session_id))


# ==============================================================================
# MILESTONE M3+: PHÒNG HỌC ẢO TRỰC TUYẾN, SESSION ATTENDANCE & ĐỐI SOÁT 80% THỜI LƯỢNG
# ==============================================================================

def record_attendance_entry(db, session_id, user_id):
    """
    Ghi nhận lượt tham gia phòng học ảo của học sinh vào bảng session_attendance.
    Đồng thời tự động cập nhật cờ check-in trong bảng sessions:
    - Nếu là người dạy: sessions.checkin_day = 1
    - Nếu là người học: sessions.checkin_hoc = 1
    """
    cur = db.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 1. Ghi nhận thời gian vào phòng
    cur.execute(
        """INSERT INTO session_attendance (session_id, user_id, thoi_gian_vao, thoi_gian_ra)
           VALUES (?, ?, ?, NULL)""",
        (session_id, user_id, now_str)
    )
    att_id = cur.lastrowid
    
    # 2. Tự động cập nhật checkin cho người tương ứng
    cur.execute("SELECT nguoi_day_id, nguoi_hoc_id FROM sessions WHERE id = ?", (session_id,))
    s = cur.fetchone()
    if s:
        if s["nguoi_day_id"] == user_id:
            cur.execute("UPDATE sessions SET checkin_day = 1 WHERE id = ?", (session_id,))
        elif s["nguoi_hoc_id"] == user_id:
            cur.execute("UPDATE sessions SET checkin_hoc = 1 WHERE id = ?", (session_id,))
            
    db.commit()
    return att_id


def close_attendance_entries(db, session_id, user_id=None):
    """
    Chốt thời gian ra (thoi_gian_ra) cho các bản ghi attendance đang mở.
    """
    cur = db.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if user_id:
        cur.execute(
            """UPDATE session_attendance 
               SET thoi_gian_ra = ? 
               WHERE session_id = ? AND user_id = ? AND (thoi_gian_ra IS NULL OR thoi_gian_ra = '')""",
            (now_str, session_id, user_id)
        )
    else:
        cur.execute(
            """UPDATE session_attendance 
               SET thoi_gian_ra = ? 
               WHERE session_id = ? AND (thoi_gian_ra IS NULL OR thoi_gian_ra = '')""",
            (now_str, session_id)
        )
    db.commit()


def calculate_session_online_overlap(db, session_id, nguoi_day_id, nguoi_hoc_id):
    """
    Tính tổng thời gian (giây) mà cả Người dạy và Người học cùng có mặt đồng thời
    trong phòng học ảo, dựa trên dữ liệu nhật ký session_attendance.
    """
    cur = db.cursor()
    cur.execute(
        """SELECT user_id, thoi_gian_vao, thoi_gian_ra 
           FROM session_attendance 
           WHERE session_id = ? AND user_id IN (?, ?) 
           ORDER BY id ASC""",
        (session_id, nguoi_day_id, nguoi_hoc_id)
    )
    rows = cur.fetchall()
    
    now = datetime.now()
    
    def parse_dt(s):
        if not s:
            return now
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return now

    teacher_spans = []
    learner_spans = []
    
    for r in rows:
        start_t = parse_dt(r["thoi_gian_vao"])
        end_t = parse_dt(r["thoi_gian_ra"]) if r["thoi_gian_ra"] else now
        if end_t > start_t:
            if r["user_id"] == nguoi_day_id:
                teacher_spans.append((start_t, end_t))
            elif r["user_id"] == nguoi_hoc_id:
                learner_spans.append((start_t, end_t))
                
    # Gộp các khoảng thời gian bị lồng/chồng nhau của từng người
    def merge_spans(spans):
        if not spans:
            return []
        spans = sorted(spans, key=lambda x: x[0])
        merged = [spans[0]]
        for cur_start, cur_end in spans[1:]:
            last_start, last_end = merged[-1]
            if cur_start <= last_end:
                merged[-1] = (last_start, max(last_end, cur_end))
            else:
                merged.append((cur_start, cur_end))
        return merged

    merged_t = merge_spans(teacher_spans)
    merged_l = merge_spans(learner_spans)
    
    total_overlap_sec = 0.0
    for ts, te in merged_t:
        for ls, le in merged_l:
            overlap_s = max(ts, ls)
            overlap_e = min(te, le)
            if overlap_e > overlap_s:
                total_overlap_sec += (overlap_e - overlap_s).total_seconds()
                
    return total_overlap_sec


@app.route("/sessions/<int:session_id>/room")
@login_required
def virtual_room(session_id):
    """
    Phòng học ảo trong ứng dụng (Milestone M3+):
    - Nhúng Jitsi Meet (meet.jit.si) qua iframe, tên phòng = 'timebankedu-' + ma_qr.
    - Không cần tài khoản Jitsi.
    - Tự động ghi session_attendance (vào phòng) và cập nhật check-in cho 2 bên.
    - Giáo viên / Admin có quyền ghé thăm bất kỳ phòng học nào để dự giờ sư phạm.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    
    cur.execute(
        """SELECT 
               s.*,
               sk.tieu_de,
               sk.linh_vuc,
               sk.mo_ta,
               ud.ho_ten AS ten_nguoi_day,
               ud.lop AS lop_nguoi_day,
               ud.ma_hoc_sinh AS ma_nguoi_day,
               uh.ho_ten AS ten_nguoi_hoc,
               uh.lop AS lop_nguoi_hoc,
               uh.ma_hoc_sinh AS ma_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.id = ?""",
        (session_id,)
    )
    session_data = cur.fetchone()
    
    if not session_data:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))
        
    is_teacher = (session_data["nguoi_day_id"] == user_id)
    is_learner = (session_data["nguoi_hoc_id"] == user_id)
    is_supervisor = (user_role in ("admin", "giao_vien"))
    
    if not (is_teacher or is_learner or is_supervisor):
        flash("Bạn không có quyền tham gia phòng học ảo của phiên này!", "danger")
        return redirect(url_for("my_schedule"))
        
    # Ghi nhận lượt tham gia vào session_attendance và tự động check-in
    record_attendance_entry(db, session_id, user_id)
    
    # Sinh tên phòng chuẩn hóa cho Jitsi Meet
    raw_ma_qr = session_data["ma_qr"] or f"SES_{session_id}"
    clean_ma_qr = re.sub(r'[^a-zA-Z0-9_-]', '', raw_ma_qr)
    room_name = f"timebankedu-{clean_ma_qr}"
    
    return render_template(
        "virtual_room.html",
        session_data=session_data,
        room_name=room_name,
        is_teacher=is_teacher,
        is_learner=is_learner,
        is_supervisor=is_supervisor
    )


@app.route("/sessions/<int:session_id>/finish", methods=["POST"])
@login_required
def finish_virtual_room(session_id):
    """
    Kết thúc buổi học từ phòng ảo:
    - Chốt thoi_gian_ra trong session_attendance.
    - Tính tổng thời gian cùng online giữa người dạy và người học.
    - Tiêu chí: cùng online >= 80% so_gio:
      + Đạt (>= 80%): Tự động chuyển giờ tín dụng (ghi 2 dòng credits_ledger, cập nhật số dư, sessions -> 'hoan_thanh').
      + Không đạt (< 80%): Phiên chuyển sang 'can_xac_minh' để Giáo viên/Admin kiểm tra và duyệt tay.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("my_schedule"))
        
    is_teacher = (s_row["nguoi_day_id"] == user_id)
    is_learner = (s_row["nguoi_hoc_id"] == user_id)
    is_admin = (user_role in ("admin", "giao_vien"))
    
    if not (is_teacher or is_learner or is_admin):
        flash("Bạn không có quyền thao tác trên phiên học này!", "danger")
        return redirect(url_for("my_schedule"))
        
    # 1. Chốt thời gian ra cho các bản ghi attendance đang mở
    close_attendance_entries(db, session_id)
    
    so_gio = float(s_row["so_gio"])
    nguoi_day_id = s_row["nguoi_day_id"]
    nguoi_hoc_id = s_row["nguoi_hoc_id"]
    
    # 2. Tính tổng thời gian cùng online giữa 2 bên
    overlap_seconds = calculate_session_online_overlap(db, session_id, nguoi_day_id, nguoi_hoc_id)
    so_gio_quy_dinh_seconds = so_gio * 3600.0
    ti_le = (overlap_seconds / so_gio_quy_dinh_seconds) if so_gio_quy_dinh_seconds > 0 else 0.0
    
    # 3. Kiểm tra tiêu chí 80%
    if ti_le >= 0.80:
        # Đạt chuẩn >= 80%: Tự động chuyển giờ
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
               VALUES (?, ?, 'day_hoc', ?, CURRENT_TIMESTAMP)""",
            (nguoi_day_id, so_gio, session_id)
        )
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
               VALUES (?, ?, 'hoc', ?, CURRENT_TIMESTAMP)""",
            (nguoi_hoc_id, -so_gio, session_id)
        )
        cur.execute("UPDATE users SET so_du_gio = so_du_gio + ? WHERE id = ?", (so_gio, nguoi_day_id))
        cur.execute("UPDATE users SET so_du_gio = so_du_gio - ? WHERE id = ?", (so_gio, nguoi_hoc_id))
        cur.execute("UPDATE sessions SET trang_thai = 'hoan_thanh' WHERE id = ?", (session_id,))
        db.commit()
        
        flash(f"Buổi học đã hoàn thành xuất sắc! Thời lượng cùng học online đạt {ti_le*100:.1f}% (≥ 80%), giờ tín dụng đã được tự động chuyển thành công.", "success")
    else:
        # Không đạt < 80%: Chuyển sang 'can_xac_minh'
        cur.execute("UPDATE sessions SET trang_thai = 'can_xac_minh' WHERE id = ?", (session_id,))
        db.commit()
        
        flash(f"Thời lượng cùng học trực tuyến chưa đạt 80% quy định (chỉ đạt {ti_le*100:.1f}% / 80%). Phiên học đã chuyển sang trạng thái 'Cần xác minh' để Thầy/Cô kiểm tra và phê duyệt tay.", "warning")
        
    return redirect(url_for("session_detail", session_id=session_id))


@app.route("/admin/sessions/<int:session_id>/approve-transfer", methods=["POST"])
@teacher_or_admin_required
def manual_approve_session(session_id):
    """
    Giáo viên / Admin duyệt tay phiên học 'can_xac_minh':
    - Chuyển sessions.trang_thai = 'hoan_thanh'
    - Ghi nhận 2 dòng credits_ledger và cộng/trừ giờ cho hai học sinh.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    s_row = cur.fetchone()
    if not s_row:
        flash("Phiên học không tồn tại!", "danger")
        return redirect(url_for("virtual_rooms_dashboard"))
        
    so_gio = float(s_row["so_gio"])
    nguoi_day_id = s_row["nguoi_day_id"]
    nguoi_hoc_id = s_row["nguoi_hoc_id"]
    
    cur.execute(
        """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
           VALUES (?, ?, 'day_hoc', ?, CURRENT_TIMESTAMP)""",
        (nguoi_day_id, so_gio, session_id)
    )
    cur.execute(
        """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) 
           VALUES (?, ?, 'hoc', ?, CURRENT_TIMESTAMP)""",
        (nguoi_hoc_id, -so_gio, session_id)
    )
    cur.execute("UPDATE users SET so_du_gio = so_du_gio + ? WHERE id = ?", (so_gio, nguoi_day_id))
    cur.execute("UPDATE users SET so_du_gio = so_du_gio - ? WHERE id = ?", (so_gio, nguoi_hoc_id))
    cur.execute("UPDATE sessions SET trang_thai = 'hoan_thanh' WHERE id = ?", (session_id,))
    db.commit()
    
    flash(f"Đã duyệt tay thành công phiên #{session_id}! Giờ tín dụng đã được chuyển cho hai học sinh.", "success")
    return redirect(request.referrer or url_for("virtual_rooms_dashboard"))


@app.route("/admin/sessions/<int:session_id>/reject", methods=["POST"])
@teacher_or_admin_required
def manual_reject_session(session_id):
    """
    Giáo viên / Admin hủy phiên học 'can_xac_minh' nếu không hợp lệ.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE sessions SET trang_thai = 'huy' WHERE id = ?", (session_id,))
    db.commit()
    flash(f"Đã hủy phiên học #{session_id}.", "info")
    return redirect(request.referrer or url_for("virtual_rooms_dashboard"))


@app.route("/virtual-rooms")
@teacher_or_admin_required
def virtual_rooms_dashboard():
    """
    Dashboard Giáo viên/Admin: Danh sách các phòng học đang diễn ra
    + Ghé thăm dự giờ bất kỳ phòng nào + Duyệt tay các phiên 'can_xac_minh'.
    """
    db = get_db()
    cur = db.cursor()
    
    # 1. Các phòng đang diễn ra (da_dat)
    cur.execute(
        """SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'da_dat'
           ORDER BY s.id DESC"""
    )
    live_rooms = cur.fetchall()
    
    # 2. Các phòng cần xác minh (< 80%)
    cur.execute(
        """SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'can_xac_minh'
           ORDER BY s.id DESC"""
    )
    verification_rooms = cur.fetchall()
    
    # 3. Các phòng đã hoàn thành gần đây
    cur.execute(
        """SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'hoan_thanh'
           ORDER BY s.id DESC LIMIT 10"""
    )
    completed_rooms = cur.fetchall()
    
    return render_template(
        "virtual_rooms_dashboard.html",
        live_rooms=live_rooms,
        verification_rooms=verification_rooms,
        completed_rooms=completed_rooms
    )


# ==============================================================================
# MILESTONE M6: MÔ HÌNH VÌ CỘNG ĐỒNG (HOẠT ĐỘNG GIỜ CÔNG ÍCH HỌC ĐƯỜNG)
# ==============================================================================

@app.route("/community")
def community_tasks_view():
    """
    Trang 'Vì cộng đồng' (Community Tasks):
    - Liệt kê toàn bộ nhiệm vụ cộng đồng đang mở ('mo_dang_ky', 'mo').
    - Hiển thị mục 'Việc phù hợp với bạn' — Trợ lý AI (Gemini Pro) phân tích kỹ năng,
      sở thích và lịch sử học tập của học sinh để gợi ý 3 việc phù hợp nhất.
    - Học sinh bấm 'Đăng ký tham gia' (nút bị khóa khi đủ số lượng hoặc quá hạn).
    - Giáo viên / Admin có quyền tạo nhiệm vụ mới và tiến hành điểm danh cộng giờ.
    """
    db = get_db()
    cur = db.cursor()

    # Truy vấn danh sách nhiệm vụ đang mở
    cur.execute("""
        SELECT t.*, u.ho_ten AS ten_nguoi_tao,
               (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
        FROM community_tasks t
        JOIN users u ON t.nguoi_tao_id = u.id
        WHERE t.trang_thai IN ('mo_dang_ky', 'mo')
        ORDER BY t.id DESC
    """)
    open_tasks = [dict(row) for row in cur.fetchall()]

    today_str = datetime.now().strftime("%Y-%m-%d")
    for t in open_tasks:
        t["is_full"] = t["so_luong_da_dang_ky"] >= t["so_luong_toi_da"]
        t["is_expired"] = bool(t["han_dang_ky"] and t["han_dang_ky"] < today_str)

    # Truy vấn danh sách nhiệm vụ đã hoàn thành để thống kê và tham khảo
    cur.execute("""
        SELECT t.*, u.ho_ten AS ten_nguoi_tao,
               (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai = 'hoan_thanh') AS so_luong_hoan_thanh
        FROM community_tasks t
        JOIN users u ON t.nguoi_tao_id = u.id
        WHERE t.trang_thai = 'hoan_thanh'
        ORDER BY t.id DESC
        LIMIT 6
    """)
    completed_tasks = cur.fetchall()

    # Lấy thông tin đăng ký của người dùng hiện tại
    user_registrations = {}
    ai_recommended = []
    is_ai_live_flag = False

    if "user_id" in session:
        cur.execute("SELECT task_id, trang_thai FROM task_registrations WHERE user_id = ?", (session["user_id"],))
        for r in cur.fetchall():
            user_registrations[r["task_id"]] = r["trang_thai"]

        # Nếu là học sinh, kích hoạt Trợ lý AI gợi ý 3 việc phù hợp
        if session.get("vai_tro") == "hoc_sinh" and open_tasks:
            ai_recommended, is_ai_live_flag = ai_recommend_tasks(db, session["user_id"], open_tasks)
            for t in ai_recommended:
                t["is_full"] = t.get("so_luong_da_dang_ky", 0) >= t.get("so_luong_toi_da", 1)
                t["is_expired"] = bool(t.get("han_dang_ky") and t["han_dang_ky"] < today_str)

    # Số liệu tổng hợp toàn trường
    cur.execute("""
        SELECT COALESCE(SUM(bien_dong), 0.0) 
        FROM credits_ledger 
        WHERE bien_dong > 0 AND (ly_do = 'nhiem_vu_cong_dong' OR ly_do LIKE '%nhiem_vu_cong_dong%')
    """)
    tong_gio_cong_ich = round(cur.fetchone()[0], 1)

    cur.execute("SELECT COUNT(DISTINCT user_id) FROM task_registrations WHERE trang_thai = 'hoan_thanh'")
    so_hs_tham_gia = cur.fetchone()[0]

    return render_template(
        "community.html",
        open_tasks=open_tasks,
        completed_tasks=completed_tasks,
        ai_recommended=ai_recommended,
        is_ai_live=is_ai_live_flag,
        user_registrations=user_registrations,
        tong_gio_cong_ich=tong_gio_cong_ich,
        so_hs_tham_gia=so_hs_tham_gia,
        today_str=today_str
    )


@app.route("/community/tasks/new", methods=["POST"])
@teacher_or_admin_required
def create_community_task():
    """
    Giáo viên / Quản trị viên tạo nhiệm vụ cộng đồng:
    - Tiêu đề, mô tả, địa điểm, số giờ thưởng, số lượng tối đa, hạn đăng ký.
    - Trạng thái mặc định: 'mo_dang_ky'.
    - Học sinh không có quyền sẽ nhận mã lỗi 403 Forbidden.
    """
    tieu_de = request.form.get("tieu_de", "").strip()
    mo_ta = request.form.get("mo_ta", "").strip()
    dia_diem = request.form.get("dia_diem", "").strip()
    
    try:
        so_gio_thuong = float(request.form.get("so_gio_thuong", 1.0))
        if so_gio_thuong <= 0:
            so_gio_thuong = 1.0
    except ValueError:
        so_gio_thuong = 1.0

    try:
        so_luong_toi_da = int(request.form.get("so_luong_toi_da", 5))
        if so_luong_toi_da <= 0:
            so_luong_toi_da = 5
    except ValueError:
        so_luong_toi_da = 5

    han_dang_ky = request.form.get("han_dang_ky", "").strip()

    if not tieu_de:
        flash("Vui lòng nhập tiêu đề cho nhiệm vụ cộng đồng.", "danger")
        return redirect(url_for("community_tasks_view"))

    db = get_db()
    cur = db.cursor()
    cur.execute(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai) 
           VALUES (?, ?, ?, ?, ?, ?, ?, 'mo_dang_ky')""",
        (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, session["user_id"])
    )
    db.commit()

    flash(f"Đã tạo thành công nhiệm vụ: '{tieu_de}' (+{so_gio_thuong}h thưởng)!", "success")
    return redirect(url_for("community_tasks_view"))


@app.route("/community/tasks/<int:task_id>/register", methods=["POST"])
@login_required
def register_community_task(task_id):
    """
    Học sinh đăng ký tham gia nhiệm vụ cộng đồng:
    - Kiểm tra trạng thái đang mở đăng ký.
    - Khóa khi đủ số lượng tối đa hoặc quá hạn đăng ký.
    - Ghi nhận vào bảng task_registrations (trang_thai = 'da_dang_ky').
    """
    user_id = session["user_id"]
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM community_tasks WHERE id = ?", (task_id,))
    task = cur.fetchone()
    if not task:
        flash("Nhiệm vụ cộng đồng không tồn tại.", "danger")
        return redirect(url_for("community_tasks_view"))

    if task["trang_thai"] not in ("mo_dang_ky", "mo"):
        flash("Nhiệm vụ này hiện đã đóng đăng ký.", "warning")
        return redirect(url_for("community_tasks_view"))

    # Kiểm tra hạn đăng ký
    today_str = datetime.now().strftime("%Y-%m-%d")
    if task["han_dang_ky"] and task["han_dang_ky"] < today_str:
        flash("Rất tiếc! Đã quá hạn đăng ký cho nhiệm vụ này.", "danger")
        return redirect(url_for("community_tasks_view"))

    # Kiểm tra số lượng người tham gia
    cur.execute(
        "SELECT COUNT(*) FROM task_registrations WHERE task_id = ? AND trang_thai NOT IN ('huy')",
        (task_id,)
    )
    so_luong_hien_tai = cur.fetchone()[0]
    if so_luong_hien_tai >= task["so_luong_toi_da"]:
        flash(f"Nhiệm vụ đã đủ số lượng người đăng ký ({task['so_luong_toi_da']} bạn).", "warning")
        return redirect(url_for("community_tasks_view"))

    # Kiểm tra xem đã đăng ký trước đó chưa
    cur.execute("SELECT id, trang_thai FROM task_registrations WHERE task_id = ? AND user_id = ?", (task_id, user_id))
    existing = cur.fetchone()
    if existing:
        if existing["trang_thai"] != "huy":
            flash("Bạn đã đăng ký nhiệm vụ này rồi!", "info")
            return redirect(url_for("community_tasks_view"))
        else:
            cur.execute("UPDATE task_registrations SET trang_thai = 'da_dang_ky' WHERE id = ?", (existing["id"],))
            db.commit()
            flash("Đã kích hoạt lại đăng ký tham gia nhiệm vụ thành công!", "success")
            return redirect(url_for("community_tasks_view"))

    # Thêm bản ghi đăng ký mới
    cur.execute(
        "INSERT INTO task_registrations (task_id, user_id, trang_thai) VALUES (?, ?, 'da_dang_ky')",
        (task_id, user_id)
    )
    db.commit()

    flash(f"Đăng ký tham gia '{task['tieu_de']}' thành công! Hãy có mặt đúng giờ nhé.", "success")
    return redirect(url_for("community_tasks_view"))


@app.route("/community/tasks/<int:task_id>/attendance", methods=["GET", "POST"])
@teacher_or_admin_required
def task_attendance(task_id):
    """
    Giáo viên / Quản trị viên điểm danh học sinh sau hoạt động cộng đồng:
    - 'hoan_thanh': INSERT credits_ledger (bien_dong = +so_gio_thuong, ly_do = 'nhiem_vu_cong_dong')
      và cập nhật users.so_du_gio.
    - 'vang_mat': Cập nhật trang_thai = 'vang_mat', tuyệt đối không cộng giờ.
    """
    db = get_db()
    cur = db.cursor()

    cur.execute("""
        SELECT t.*, u.ho_ten AS ten_nguoi_tao 
        FROM community_tasks t 
        JOIN users u ON t.nguoi_tao_id = u.id 
        WHERE t.id = ?
    """, (task_id,))
    task = cur.fetchone()
    if not task:
        flash("Không tìm thấy nhiệm vụ cộng đồng.", "danger")
        return redirect(url_for("community_tasks_view"))

    if request.method == "POST":
        reg_id = request.form.get("registration_id")
        single_status = request.form.get("status")

        items_to_process = []
        if reg_id and single_status:
            try:
                items_to_process.append((int(reg_id), single_status))
            except ValueError:
                pass
        else:
            for key, val in request.form.items():
                if key.startswith("status_"):
                    try:
                        rid = int(key.replace("status_", ""))
                        items_to_process.append((rid, val))
                    except ValueError:
                        pass

        so_gio_thuong = float(task["so_gio_thuong"])
        so_ban_hoan_thanh = 0
        so_ban_vang = 0

        for rid, st in items_to_process:
            cur.execute("SELECT * FROM task_registrations WHERE id = ? AND task_id = ?", (rid, task_id))
            reg = cur.fetchone()
            if not reg:
                continue

            current_reg_status = reg["trang_thai"]

            if st == "hoan_thanh":
                if current_reg_status != "hoan_thanh":
                    cur.execute("UPDATE task_registrations SET trang_thai = 'hoan_thanh' WHERE id = ?", (rid,))
                    # Ghi sổ cái credits_ledger: bien_dong = +so_gio_thuong, ly_do = 'nhiem_vu_cong_dong'
                    cur.execute(
                        """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id) 
                           VALUES (?, ?, 'nhiem_vu_cong_dong', NULL)""",
                        (reg["user_id"], so_gio_thuong)
                    )
                    # Cập nhật số dư giờ của học sinh
                    cur.execute(
                        "UPDATE users SET so_du_gio = so_du_gio + ? WHERE id = ?",
                        (so_gio_thuong, reg["user_id"])
                    )
                    so_ban_hoan_thanh += 1
            elif st == "vang_mat":
                cur.execute("UPDATE task_registrations SET trang_thai = 'vang_mat' WHERE id = ?", (rid,))
                so_ban_vang += 1

        # Cập nhật trạng thái nhiệm vụ nếu hoàn tất toàn bộ hoạt động
        if request.form.get("hoan_thanh_nhiem_vu") == "1":
            cur.execute("UPDATE community_tasks SET trang_thai = 'hoan_thanh' WHERE id = ?", (task_id,))

        db.commit()
        flash(f"Điểm danh thành công! Đã ghi nhận {so_ban_hoan_thanh} bạn hoàn thành (+{so_gio_thuong}h vào ví) và {so_ban_vang} bạn vắng mặt.", "success")
        return redirect(url_for("task_attendance", task_id=task_id))

    # Lấy danh sách học sinh đăng ký
    cur.execute("""
        SELECT r.*, u.ma_hoc_sinh, u.ho_ten, u.lop, u.so_du_gio
        FROM task_registrations r
        JOIN users u ON r.user_id = u.id
        WHERE r.task_id = ?
        ORDER BY r.id ASC
    """, (task_id,))
    registrations = cur.fetchall()

    return render_template(
        "community_attendance.html",
        task=task,
        registrations=registrations
    )


# ==============================================================================
# MILESTONE M-CHAT: KHUNG CHAT TRỢ LÝ HỌC ĐƯỜNG ẢO (GEMINI PRO)
# ==============================================================================

@app.route("/api/chat/history")
@login_required
def api_chat_history():
    """
    API lấy lịch sử trò chuyện và thông điệp chào mừng kèm nhắc lịch học sắp tới:
    - Truy vấn tối đa 50 tin nhắn gần nhất từ bảng chat_messages theo user_id.
    - Tạo lời chào mừng chủ động nhắc nhở N lịch hẹn sắp tới ('da_dat').
    """
    user_id = session["user_id"]
    db = get_db()
    cur = db.cursor()

    # 1. Lấy thông điệp chào hỏi và nhắc lịch
    greeting_info = get_chat_greeting_and_reminder(db, user_id)

    # 2. Lấy lịch sử tin nhắn
    cur.execute("""
        SELECT id, vai_tro, noi_dung, thoi_gian
        FROM chat_messages
        WHERE user_id = ?
        ORDER BY id ASC
        LIMIT 50
    """, (user_id,))
    messages = [dict(m) for m in cur.fetchall()]

    return jsonify({
        "success": True,
        "greeting": greeting_info["greeting"],
        "upcoming_count": greeting_info["upcoming_count"],
        "so_du_gio": greeting_info["so_du_gio"],
        "is_ai_live": is_ai_live(),
        "messages": messages
    })


@app.route("/api/chat/send", methods=["POST"])
@login_required
def api_chat_send():
    """
    API tiếp nhận tin nhắn từ học sinh và phản hồi thông minh:
    - Nhận câu hỏi qua JSON hoặc Form.
    - Lưu câu hỏi của học sinh vào bảng chat_messages (vai_tro = 'user').
    - Gọi hàm ai_chat_assistant với đầy đủ ngữ cảnh cá nhân hóa (số dư thật, lịch học, kỹ năng).
    - Lưu câu trả lời vào bảng chat_messages (vai_tro = 'assistant').
    - Ghi nhận nhật ký suy luận minh bạch vào bảng ai_logs (chuc_nang = 'tro_ly_ao').
    """
    user_id = session["user_id"]
    data = request.get_json() or request.form
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống."}), 400

    db = get_db()
    cur = db.cursor()

    # 1. Lưu câu hỏi của người dùng
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """INSERT INTO chat_messages (user_id, vai_tro, noi_dung, thoi_gian)
           VALUES (?, 'user', ?, ?)""",
        (user_id, message, now_str)
    )
    db.commit()

    # 2. Xử lý câu trả lời từ Trợ lý AI (có ngữ cảnh cá nhân)
    reply, is_live = ai_chat_assistant(db, user_id, message)

    # 3. Lưu câu trả lời của trợ lý
    now_reply_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute(
        """INSERT INTO chat_messages (user_id, vai_tro, noi_dung, thoi_gian)
           VALUES (?, 'assistant', ?, ?)""",
        (user_id, reply, now_reply_str)
    )
    db.commit()

    return jsonify({
        "success": True,
        "reply": reply,
        "is_live": is_live,
        "timestamp": now_reply_str
    })


@app.route("/api/chat/clear", methods=["POST"])
@login_required
def api_chat_clear():
    """
    API làm mới / xóa lịch sử trò chuyện của học sinh hiện tại.
    """
    user_id = session["user_id"]
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM chat_messages WHERE user_id = ?", (user_id,))
    db.commit()
    return jsonify({"success": True, "message": "Đã làm mới cuộc trò chuyện."})


# ------------------------------------------------------------------------------
# MILESTONE M5-BLOG: BẢNG TIN HỌC ĐƯỜNG & AI SOẠN BẢN TIN TUẦN
# ------------------------------------------------------------------------------

@app.route("/blog")
def blog_index():
    """
    Trang Bảng tin học đường công khai (/blog):
    - Liệt kê các bài viết đã duyệt và đăng chính thức (trang_thai = 'da_dang').
    - Các bài viết bản nháp ('nhap') hoặc chưa duyệt TUYỆT ĐỐI KHÔNG xuất hiện tại đây.
    - Sắp xếp mới nhất lên đầu, hỗ trợ giao diện responsive chuẩn bị cho thuyết trình.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang
        FROM blog_posts
        WHERE trang_thai = 'da_dang'
        ORDER BY thoi_gian_dang DESC, id DESC
    """)
    posts = cur.fetchall()
    return render_template("blog_list.html", posts=posts)


@app.route("/blog/<int:post_id>")
def blog_detail(post_id):
    """
    Trang xem chi tiết bài viết (/blog/<id>):
    - Hiển thị toàn văn bài viết, tiêu đề, ảnh minh họa và huy hiệu tác giả.
    - Nếu tac_gia_ai = 1: Giao diện hiển thị rõ 'Hỗ trợ bởi AI (Gemini)'.
    - Phân quyền: Nếu bài viết đang là bản nháp ('nhap'), chỉ Giáo viên hoặc Admin
      mới được xem trước (chế độ Preview) kèm nút 'Duyệt & Đăng ngay'. Học sinh hoặc
      khách truy cập ngoài sẽ bị từ chối 404 để đảm bảo tính riêng tư trước khi công khai.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
    post = cur.fetchone()

    if not post:
        abort(404)

    is_teacher_or_admin = session.get("vai_tro") in ("admin", "giao_vien")
    
    # Kiểm tra quyền xem bản nháp: chưa duyệt thì học sinh/khách không xem được
    if post["trang_thai"] != "da_dang" and not is_teacher_or_admin:
        abort(404)

    return render_template(
        "blog_detail.html", 
        post=post, 
        is_preview=(post["trang_thai"] != "da_dang")
    )


@app.route("/blog/manage")
@teacher_or_admin_required
def blog_manage():
    """
    Bảng điều khiển quản lý bài viết dành riêng cho Giáo viên & Ban Quản trị:
    - Liệt kê toàn bộ bài viết (kể cả Bản nháp, Đã duyệt, Đã đăng).
    - Thống kê số lượng bài viết, phân loại bài AI / bài giáo viên.
    - Cung cấp nút 1-click 'Duyệt & Đăng' cho cô giáo.
    - Cung cấp nút 'Nhờ AI soạn bản tin tuần' sử dụng mô hình Gemini Pro.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT id, tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang
        FROM blog_posts
        ORDER BY id DESC
    """)
    posts = cur.fetchall()

    total_posts = len(posts)
    published_count = sum(1 for p in posts if p["trang_thai"] == "da_dang")
    draft_count = sum(1 for p in posts if p["trang_thai"] == "nhap")
    ai_count = sum(1 for p in posts if p["tac_gia_ai"] == 1)

    return render_template(
        "blog_manage.html",
        posts=posts,
        total_posts=total_posts,
        published_count=published_count,
        draft_count=draft_count,
        ai_count=ai_count
    )


@app.route("/blog/create", methods=["GET", "POST"])
@teacher_or_admin_required
def blog_create():
    """
    Tạo bài viết mới thủ công dành cho Giáo viên / Admin:
    - Nhập tiêu đề, nội dung bài viết.
    - Hỗ trợ tải lên ảnh minh họa hoặc sử dụng ảnh mặc định của nhà trường.
    - Lựa chọn trạng thái: Lưu nháp ('nhap') hoặc Đăng ngay ('da_dang').
    """
    if request.method == "POST":
        tieu_de = request.form.get("tieu_de", "").strip()
        noi_dung = request.form.get("noi_dung", "").strip()
        trang_thai = request.form.get("trang_thai", "nhap").strip()
        if trang_thai not in ("nhap", "da_duyet", "da_dang"):
            trang_thai = "nhap"

        if not tieu_de or not noi_dung:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung bài viết.", "danger")
            return render_template("blog_form.html", post=None, action="create")

        # Xử lý upload ảnh minh họa
        anh_minh_hoa = "/static/img/newsletter_banner.svg"
        if "anh_minh_hoa" in request.files:
            file = request.files["anh_minh_hoa"]
            if file and file.filename and allowed_image_file(file.filename):
                fname = secure_filename(file.filename)
                _, ext = os.path.splitext(fname)
                unique_name = f"blog_{int(time.time())}_{secrets.token_hex(4)}{ext}"
                file.save(str(UPLOAD_BLOG_FOLDER / unique_name))
                anh_minh_hoa = f"/static/uploads/blog/{unique_name}"

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            INSERT INTO blog_posts (tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang)
            VALUES (?, ?, ?, 0, ?, CURRENT_TIMESTAMP)
        """, (tieu_de, noi_dung, anh_minh_hoa, trang_thai))
        db.commit()

        flash("Bài viết đã được tạo thành công!", "success")
        return redirect(url_for("blog_manage"))

    return render_template("blog_form.html", post=None, action="create")


@app.route("/blog/<int:post_id>/edit", methods=["GET", "POST"])
@teacher_or_admin_required
def blog_edit(post_id):
    """
    Chỉnh sửa bài viết hiện có:
    - Cho phép cập nhật tiêu đề, nội dung, thay ảnh minh họa và đổi trạng thái.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
    post = cur.fetchone()

    if not post:
        abort(404)

    if request.method == "POST":
        tieu_de = request.form.get("tieu_de", "").strip()
        noi_dung = request.form.get("noi_dung", "").strip()
        trang_thai = request.form.get("trang_thai", post["trang_thai"]).strip()
        if trang_thai not in ("nhap", "da_duyet", "da_dang"):
            trang_thai = post["trang_thai"]

        if not tieu_de or not noi_dung:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung bài viết.", "danger")
            return render_template("blog_form.html", post=post, action="edit")

        anh_minh_hoa = post["anh_minh_hoa"]
        if "anh_minh_hoa" in request.files:
            file = request.files["anh_minh_hoa"]
            if file and file.filename and allowed_image_file(file.filename):
                fname = secure_filename(file.filename)
                _, ext = os.path.splitext(fname)
                unique_name = f"blog_{int(time.time())}_{secrets.token_hex(4)}{ext}"
                file.save(str(UPLOAD_BLOG_FOLDER / unique_name))
                anh_minh_hoa = f"/static/uploads/blog/{unique_name}"

        cur.execute("""
            UPDATE blog_posts 
            SET tieu_de = ?, noi_dung = ?, anh_minh_hoa = ?, trang_thai = ?
            WHERE id = ?
        """, (tieu_de, noi_dung, anh_minh_hoa, trang_thai, post_id))
        db.commit()

        flash("Cập nhật bài viết thành công!", "success")
        return redirect(url_for("blog_manage"))

    return render_template("blog_form.html", post=post, action="edit")


@app.route("/blog/<int:post_id>/delete", methods=["POST", "GET"])
@teacher_or_admin_required
def blog_delete(post_id):
    """
    Xóa bài viết khỏi cơ sở dữ liệu.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("DELETE FROM blog_posts WHERE id = ?", (post_id,))
    db.commit()
    flash("Đã xóa bài viết thành công.", "info")
    return redirect(url_for("blog_manage"))


@app.route("/blog/<int:post_id>/publish", methods=["POST", "GET"])
@teacher_or_admin_required
def blog_publish(post_id):
    """
    Duyệt 1-click bài viết (Milestone M5-blog):
    - Chuyển trạng thái từ 'nhap' sang 'da_dang' ngay lập tức.
    - Cập nhật thời gian đăng bài thành thời điểm hiện tại.
    - Sau khi duyệt, bài viết lập tức hiển thị công khai trên /blog.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        UPDATE blog_posts 
        SET trang_thai = 'da_dang', thoi_gian_dang = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (post_id,))
    db.commit()

    flash("Duyệt thành công! Bài viết đã được đăng công khai trên Bảng tin học đường.", "success")
    return redirect(url_for("blog_detail", post_id=post_id))


@app.route("/blog/ai-newsletter", methods=["POST", "GET"])
@teacher_or_admin_required
def blog_ai_newsletter():
    """
    Nút 'Nhờ AI soạn bản tin tuần' (Gemini Pro API):
    - Tự động gom dữ liệu 7 ngày qua (phiên học mới, top 3 gia sư, lĩnh vực hot, 2-3 nhận xét 5 sao).
    - Gọi Gemini Pro API để biên soạn bản tin tiếng Việt có cấu trúc 5 phần chuẩn mực:
      1. Mở đầu -> 2. Con số nổi bật -> 3. Vinh danh gia sư của tuần -> 4. Câu chuyện tiêu biểu -> 5. Lời kêu gọi.
    - Tự động lưu với tac_gia_ai = 1, trang_thai = 'nhap'.
    - Cô giáo xem lại và duyệt 1-click để đăng chính thức.
    """
    db = get_db()
    user_id = session.get("user_id")
    post_id, title, content, is_live = ai_generate_weekly_newsletter(db, user_id=user_id)

    ai_mode_note = "Gemini Pro" if is_live else "Chế độ dự phòng Sư phạm"
    flash(
        f"✨ AI ({ai_mode_note}) đã soạn xong Bản tin tuần với đầy đủ 5 phần! "
        f"Bản tin hiện đang ở trạng thái 'Bản nháp'. Cô giáo hãy xem lại và bấm 'Duyệt & Đăng ngay' để công khai lên Bảng tin.",
        "success"
    )
    return redirect(url_for("blog_detail", post_id=post_id))


# ------------------------------------------------------------------------------
# CÁC API HỖ TRỢ VÀ LIÊN HỆ
# ------------------------------------------------------------------------------

@app.route("/api/stats")
def api_stats():
    """
    API cung cấp dữ liệu số liệu thời gian thực (JSON) cho frontend hoặc ứng dụng ngoài.
    """
    db = get_db()
    stats = get_realtime_stats(db)
    return jsonify({"success": True, "data": stats})


@app.route("/api/contact", methods=["POST"])
def api_contact():
    """
    API tiếp nhận thông tin đăng ký tư vấn và chuyển giao mô hình từ các trường học.
    """
    data = request.get_json() or request.form
    ten_truong = data.get("ten_truong", "")
    ho_ten = data.get("ho_ten", "")
    sdt = data.get("sdt", "")
    email = data.get("email", "")
    ghi_chu = data.get("ghi_chu", "")
    
    app.logger.info(f"Đăng ký tư vấn mới: {ho_ten} - {ten_truong} - {sdt} - {email}")
    
    return jsonify({
        "success": True,
        "message": f"Cảm ơn Thầy/Cô {ho_ten} ({ten_truong})! Ban đề án TimeBank EDU sẽ liên hệ lại qua SĐT {sdt}."
    })


# ==============================================================================
# ĐIỂM KHỞI CHẠY CHÍNH (CHẠY BẰNG ĐÚNG 1 LỆNH)
# ==============================================================================
if __name__ == "__main__":
    # Tự động khởi tạo database nếu chưa có tệp database/timebank.db hoặc bảng trên PostgreSQL
    init_db()
    
    config = load_school_config()
    port = int(os.getenv("PORT", 5000))
    debug_mode = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true")
    db_mode_str = "PostgreSQL (DATABASE_URL)" if is_postgres_configured() else "SQLite cục bộ (Single-Tenant)"

    print("=" * 70)
    print("🏫 TIMEBANK EDU - NGÂN HÀNG THỜI GIAN HỌC ĐƯỜNG")
    print(f"📍 Đơn vị: {config.get('ten_truong')}")
    print(f"🚀 Máy chủ đang khởi động tại: http://127.0.0.1:{port}")
    print(f"⚙️ Chế độ cơ sở dữ liệu: {db_mode_str}")
    print(f"🛡️ Debug Mode: {'BẬT' if debug_mode else 'TẮT (Production)'}")
    print("🔑 Tài khoản quản trị mặc định: admin / admin123")
    print("=" * 70)
    
    # Khởi chạy Flask Server
    app.run(host="0.0.0.0", port=port, debug=debug_mode)

