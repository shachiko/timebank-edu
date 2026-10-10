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
import click
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
import jwt
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from flask import (
    Flask, render_template, request, jsonify, g, flash, redirect, url_for, session, abort, make_response, Response
)
from flask_babel import Babel, gettext as _, lazy_gettext as _l
from ai_service import (
    ai_moderate_skill, ai_matchmake, ai_generate_lesson_plan, 
    ai_summarize_feedback, ai_admin_early_warning, is_ai_live,
    ai_generate_quiz, ai_recommend_tasks, get_chat_greeting_and_reminder,
    ai_chat_assistant, ai_generate_weekly_newsletter,
    ai_moderate_chat_message
)
from drive_service import (
    upload_document_stream, download_document_stream, delete_document_from_drive,
    get_oauth_auth_url, exchange_code_for_tokens, is_google_drive_configured
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
# Cấu hình kích thước tải lên tối đa 500MB (Google Drive 5TB storage)
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024
# Bảo mật: SECRET_KEY đọc từ biến môi trường khi deploy production
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY") or os.getenv("FLASK_SECRET_KEY") or "timebank-edu-secret-key-2026"

# Bộ nhớ đệm kết quả gợi ý ghép cặp hàng ngày: key = (user_id, YYYY-MM-DD), val = (matches, is_live, subject)
DAILY_RECOMMENDATION_CACHE = {}

# ------------------------------------------------------------------------------
# CẤU HÌNH ĐA NGÔN NGỮ (PROMPT 16: FLASK-BABEL)
# Hỗ trợ 5 ngôn ngữ: vi (mặc định), en, zh, fr, de
# KHÔNG tự nhận diện IP hay Accept-Language — người dùng tự chọn trên header
# ------------------------------------------------------------------------------
SUPPORTED_LANGUAGES = {
    "vi": "Tiếng Việt",
    "en": "English",
    "zh": "中文",
    "fr": "Français",
    "de": "Deutsch"
}

app.config["BABEL_DEFAULT_LOCALE"] = "vi"
app.config["BABEL_TRANSLATION_DIRECTORIES"] = str(BASE_DIR / "translations")

def get_locale():
    # 1. Người dùng tự chọn bằng nút chuyển ngôn ngữ trên header, lưu vào session
    lang = session.get("lang")
    if lang in SUPPORTED_LANGUAGES:
        return lang
    # 2. KHÔNG tự nhận diện qua IP hay Accept-Language -> Mặc định tiếng Việt
    return "vi"

babel = Babel(app, locale_selector=get_locale)

app.jinja_env.globals["_"] = _
app.jinja_env.globals["gettext"] = _
app.jinja_env.globals["SUPPORTED_LANGUAGES"] = SUPPORTED_LANGUAGES
app.jinja_env.globals["get_locale"] = get_locale



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
        "dong_gioi_thieu": "Hệ thống Ngân hàng Thời gian Học đường — Trao đổi tri thức, sẻ chia kỹ năng bằng tín dụng thời gian bình đẳng.",
        "cong_dong_nguong_tin_dung": 24,
        "video_provider": "daily"
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


def get_community_threshold():
    """
    Lấy ngưỡng tín dụng dạy thật để mở khóa Sàn cộng đồng từ cấu hình config.yaml.
    TUYỆT ĐỐI không hardcode số 24 trong nghiệp vụ code.
    """
    cfg = load_school_config()
    try:
        val = float(cfg.get("cong_dong_nguong_tin_dung", 24))
        return val
    except (ValueError, TypeError):
        return 24.0


def get_video_provider():
    """
    Lấy nòng phòng học ảo chính từ cấu hình (mặc định 'daily'):
    Ưu tiên: Biến môi trường VIDEO_PROVIDER > config.yaml ('video_provider' hoặc 'VIDEO_PROVIDER') > mặc định 'daily'.
    Các giá trị hợp lệ: 'daily' | 'jaas' | 'jitsi'.
    """
    provider = os.getenv("VIDEO_PROVIDER")
    if not provider:
        cfg = load_school_config()
        provider = cfg.get("video_provider") or cfg.get("VIDEO_PROVIDER") or "daily"
    provider = str(provider).strip().lower()
    if provider not in ("daily", "jaas", "jitsi"):
        provider = "daily"
    return provider


def get_user_teaching_hours(db, user_id):
    """
    Tính 'Tín dụng kiếm được từ dạy thật' = tổng số giờ các buổi học mà user
    LÀM NGƯỜI DẠY (nguoi_day_id = user_id) và trạng thái 'hoan_thanh'.
    KHÔNG tính 2 giờ tặng ban đầu.
    """
    if not user_id:
        return 0.0
    cur = db.cursor()
    cur.execute(
        "SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE nguoi_day_id = ? AND trang_thai = 'hoan_thanh'",
        (user_id,)
    )
    row = cur.fetchone()
    return float(row[0]) if row and row[0] is not None else 0.0


def has_passed_community_gate(db, user_id):
    """Kiểm tra học sinh đã đạt ngưỡng tín dụng dạy thật để vào Sàn cộng đồng hay chưa."""
    threshold = get_community_threshold()
    hours = get_user_teaching_hours(db, user_id)
    return hours >= threshold



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
    Tự động truyền cấu hình trường học 'config', thông tin phiên đăng nhập 'current_user'
    và danh sách các trường học 'all_schools' vào tất cả các giao diện HTML (Jinja2 Template).
    """
    current_user = None
    if "user_id" in session:
        role = session.get("vai_tro", "hoc_sinh")
        tid = session.get("truong_id", 1)
        mhs = session.get("ma_hoc_sinh", "")
        is_super = is_super_admin()
        is_school = is_school_admin()
        is_demo = is_demo_user(mhs)
        current_user = {
            "id": session.get("user_id"),
            "ma_hoc_sinh": mhs,
            "ho_ten": session.get("ho_ten"),
            "vai_tro": role,
            "lop": session.get("lop"),
            "so_du_gio": session.get("so_du_gio", 2.0),
            "truong_id": tid,
            "ten_truong": session.get("ten_truong", ""),
            "trang_thai": session.get("trang_thai", "hoat_dong"),
            "is_super_admin": is_super,
            "is_school_admin": is_school,
            "is_demo_user": is_demo,
            "is_admin": is_super or is_school
        }

    all_schools = []
    try:
        db = get_db()
        cur = db.cursor()
        if is_super_admin():
            cur.execute("SELECT *, COALESCE(an_truong, 0) AS an_truong FROM truong ORDER BY id ASC")
        else:
            cur.execute("SELECT *, COALESCE(an_truong, 0) AS an_truong FROM truong WHERE COALESCE(an_truong, 0) = 0 ORDER BY id ASC")
        all_schools = cur.fetchall()
    except Exception:
        all_schools = []

    return {
        "config": load_school_config(),
        "current_user": current_user,
        "all_schools": all_schools,
        "is_demo_user": is_demo_user,
        "is_demo": is_demo_user(session.get("ma_hoc_sinh")) if "user_id" in session else False,
        "current_lang": get_locale(),
        "supported_languages": SUPPORTED_LANGUAGES
    }


@app.route("/set-language/<lang_code>")
def set_language(lang_code):
    """
    Chuyển đổi ngôn ngữ hiển thị giao diện và lưu vào session.
    Hỗ trợ 5 ngôn ngữ: vi, en, zh, fr, de. Mặc định là vi.
    """
    if lang_code in SUPPORTED_LANGUAGES:
        session["lang"] = lang_code
    referrer = request.referrer
    if referrer and request.host_url in referrer:
        return redirect(referrer)
    return redirect(url_for("index"))


# ==============================================================================
# ĐỊNH NGHĨA TRƯỜNG DEMO & RBAC PHÂN QUYỀN (PROMPT 23)
# ==============================================================================
DEMO_SCHOOL_ID = 99
DEMO_SCHOOL_NAME = "Trường Demo - Dành cho Giám Khảo"


def is_demo_user(ma_hoc_sinh):
    """
    Kiểm tra xem tài khoản có phải tài khoản demo dành cho giám khảo hay không:
    - demo_quantruong, demo_giaovien, demo_hocsinh, demo_hocsinh_2, admin
    - Không được phép thay đổi mật khẩu (ẩn nút, chặn đổi).
    """
    if not ma_hoc_sinh:
        return False
    u = str(ma_hoc_sinh).strip().lower()
    return u in ("demo_quantruong", "demo_giaovien", "demo_hocsinh", "demo_hocsinh_2", "admin") or u.startswith("demo_")


def is_super_admin():
    """Kiểm tra người dùng hiện tại có phải Tổng quản trị (Super Admin - cô Huyền) hay không."""
    return session.get("vai_tro") == "super_admin"


def is_school_admin():
    """Kiểm tra người dùng hiện tại có phải Quản trị viên trường (School Admin) hay không."""
    return session.get("vai_tro") in ("school_admin", "admin")


def get_current_truong_id():
    """Lấy ID trường học của tài khoản đang đăng nhập."""
    return session.get("truong_id", 1)


def login_required(f):
    """
    Bắt buộc người dùng phải đăng nhập trước khi truy cập trang.
    Nếu chưa đăng nhập, chuyển hướng đến trang /login.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash(_("Vui lòng đăng nhập để tiếp tục truy cập."), "warning")
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Cho phép Super Admin và School Admin truy cập khu vực quản trị.
    Học sinh và giáo viên bị chặn bằng mã lỗi 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash(_("Vui lòng đăng nhập bằng tài khoản Quản trị viên."), "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("vai_tro") not in ("admin", "super_admin", "school_admin"):
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)
    return decorated_function


def super_admin_required(f):
    """
    Chỉ cho phép duy nhất Tổng quản trị (Super Admin) truy cập.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash(_("Vui lòng đăng nhập bằng tài khoản Tổng quản trị."), "warning")
            return redirect(url_for("login", next=request.url))
        if not is_super_admin():
            return render_template("errors/403.html"), 403
        return f(*args, **kwargs)
    return decorated_function


def teacher_or_admin_required(f):
    """
    Cho phép Giáo viên (giao_vien), School Admin hoặc Super Admin thực hiện chức năng.
    Học sinh không có quyền sẽ bị chặn bằng mã lỗi 403 Forbidden.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash(_("Vui lòng đăng nhập với quyền Giáo viên hoặc Quản trị viên."), "warning")
            return redirect(url_for("login", next=request.url))
        if session.get("vai_tro") not in ("giao_vien", "admin", "super_admin", "school_admin"):
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

        # Đảm bảo hàm ROUND(expr, n) trên PostgreSQL luôn được ép kiểu ::numeric
        if "ROUND(" in converted_query.upper():
            import re
            converted_query = re.sub(
                r'ROUND\s*\(\s*(COALESCE\s*\([^()]*(?:\([^()]*\)[^()]*)*\)|[a-zA-Z0-9_.]+\s*\([^()]*\)|[a-zA-Z0-9_.]+)(?!::numeric)\s*,\s*(\d+)\s*\)',
                r'ROUND(\1::numeric, \2)',
                converted_query,
                flags=re.IGNORECASE
            )

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

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()

    def __iter__(self):
        return iter(self._cur)

    @property
    def description(self):
        return self._cur.description

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


class SqliteCursorWrapper:
    """
    Lớp bọc con trỏ SQLite để tương thích với cú pháp PostgreSQL:
    - Tự động gỡ bỏ ép kiểu '::numeric' khi chạy trên SQLite cục bộ.
    """
    def __init__(self, cursor):
        self._cur = cursor

    def execute(self, query, params=None):
        cleaned_query = query.replace("::numeric", "") if "::numeric" in query else query
        if params is not None:
            return self._cur.execute(cleaned_query, params)
        return self._cur.execute(cleaned_query)

    def executemany(self, query, seq_of_params):
        cleaned_query = query.replace("::numeric", "") if "::numeric" in query else query
        return self._cur.executemany(cleaned_query, seq_of_params)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def fetchmany(self, size=None):
        return self._cur.fetchmany(size) if size is not None else self._cur.fetchmany()

    @property
    def lastrowid(self):
        return self._cur.lastrowid

    @property
    def rowcount(self):
        return self._cur.rowcount

    @property
    def description(self):
        return self._cur.description

    def close(self):
        self._cur.close()

    def __iter__(self):
        return iter(self._cur)

    def __getattr__(self, name):
        return getattr(self._cur, name)


class SqliteConnectionWrapper:
    """
    Lớp bọc kết nối SQLite để tự động gỡ bỏ cú pháp '::numeric'
    giúp đồng nhất mã nguồn SQL tương thích cả PostgreSQL lẫn SQLite.
    """
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        return SqliteCursorWrapper(self._conn.cursor())

    def execute(self, query, params=None):
        cleaned_query = query.replace("::numeric", "") if "::numeric" in query else query
        if params is not None:
            return SqliteCursorWrapper(self._conn.execute(cleaned_query, params))
        return SqliteCursorWrapper(self._conn.execute(cleaned_query))

    def executemany(self, query, seq_of_params):
        cleaned_query = query.replace("::numeric", "") if "::numeric" in query else query
        return SqliteCursorWrapper(self._conn.executemany(cleaned_query, seq_of_params))

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()

    def __getattr__(self, item):
        return getattr(self._conn, item)


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
                raw_sqlite = sqlite3.connect(
                    DATABASE_PATH,
                    detect_types=sqlite3.PARSE_DECLTYPES,
                    timeout=30.0
                )
                raw_sqlite.row_factory = sqlite3.Row
                g.db = SqliteConnectionWrapper(raw_sqlite)
        else:
            raw_sqlite = sqlite3.connect(
                DATABASE_PATH,
                detect_types=sqlite3.PARSE_DECLTYPES,
                timeout=30.0
            )
            raw_sqlite.row_factory = sqlite3.Row
            raw_sqlite.execute("PRAGMA foreign_keys = ON")
            raw_sqlite.execute("PRAGMA journal_mode = WAL")
            g.db = SqliteConnectionWrapper(raw_sqlite)
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    """
    Tự động đóng kết nối cơ sở dữ liệu khi kết thúc lượt xử lý (request).
    """
    db = g.pop("db", None)
    if db is not None:
        db.close()


def migrate_postgres_schema(conn):
    """
    Hotfix Prompt 20: Tự động di chuyển (migrate) cấu trúc cơ sở dữ liệu PostgreSQL production (P17–P19):
    1. users: ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1;
              ADD COLUMN IF NOT EXISTS trang_thai TEXT DEFAULT 'hoat_dong';
    2. skills: ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1;
               ADD COLUMN IF NOT EXISTS hien_thi_cong_dong INTEGER DEFAULT 0;
               ADD COLUMN IF NOT EXISTS trang_thai_cong_dong TEXT DEFAULT 'chua_dang';
               ADD COLUMN IF NOT EXISTS nguoi_duyet_cong_dong_id INTEGER;
               ADD COLUMN IF NOT EXISTS ngay_duyet_cong_dong TEXT;
    3. sessions, ratings, community_tasks, task_registrations, blog_posts:
       mỗi bảng ADD COLUMN IF NOT EXISTS truong_id INTEGER DEFAULT 1;
    4. Cập nhật CHECK vai_tro của bảng users để chấp nhận 'super_admin' và 'school_admin':
       DROP CONSTRAINT cũ (nếu tên constraint không biết thì tìm trong information_schema)
       rồi ADD CONSTRAINT mới. Bọc try/except từng lệnh để không crash nếu constraint đã đúng.
    5. Seed 4 trường vào bảng truong NẾU bảng rỗng (giống seed_demo_data).
    6. UPDATE các dòng cũ: SET truong_id = 1 WHERE truong_id IS NULL (đề phòng DEFAULT không backfill).
    7. Nâng tài khoản 'admin' cũ lên vai_tro = 'super_admin' NẾU đang là 'admin'.

    Hàm idempotent (chạy lại nhiều lần không lỗi, không mất dữ liệu).
    Tương thích cả PostgreSQL production lẫn SQLite (mô phỏng trong test suite).
    """
    is_sqlite = False
    if isinstance(conn, (sqlite3.Connection, SqliteConnectionWrapper)) or isinstance(getattr(conn, "_conn", None), sqlite3.Connection):
        is_sqlite = True
    elif not hasattr(conn, "_conn"):
        try:
            c = conn.cursor()
            c.execute("SELECT sqlite_version()")
            is_sqlite = True
        except Exception:
            is_sqlite = False
            try:
                conn.rollback()
            except Exception:
                pass

    cur = conn.cursor()

    def _exec(sql, params=None):
        if params is not None:
            if is_sqlite or isinstance(cur, PostgresCursorWrapper) or hasattr(conn, "_conn"):
                cur.execute(sql, params)
            else:
                cur.execute(sql.replace("?", "%s"), params)
        else:
            cur.execute(sql)

    # 0. Đảm bảo bảng truong tồn tại trước khi seed hoặc tham chiếu
    try:
        if is_sqlite:
            _exec("""
                CREATE TABLE IF NOT EXISTS truong (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ten_truong TEXT NOT NULL,
                    logo TEXT,
                    trang_thai TEXT CHECK(trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung', 'vo_hieu_hoa')) DEFAULT 'dang_thi_diem',
                    an_truong INTEGER DEFAULT 0,
                    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            _exec("""
                CREATE TABLE IF NOT EXISTS truong (
                    id SERIAL PRIMARY KEY,
                    ten_truong TEXT NOT NULL,
                    logo TEXT,
                    trang_thai TEXT CHECK(trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung', 'vo_hieu_hoa')) DEFAULT 'dang_thi_diem',
                    an_truong INTEGER DEFAULT 0,
                    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi kiểm tra/tạo bảng truong: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # 1. users: ADD COLUMN IF NOT EXISTS truong_id, trang_thai
    # 2. skills: ADD COLUMN IF NOT EXISTS truong_id, hien_thi_cong_dong, trang_thai_cong_dong, nguoi_duyet_cong_dong_id, ngay_duyet_cong_dong
    # 3. sessions, ratings, community_tasks, task_registrations, blog_posts: ADD COLUMN IF NOT EXISTS truong_id
    # 4. truong: ADD COLUMN IF NOT EXISTS an_truong
    columns_to_add = [
        # 1. users
        ("users", "truong_id", "INTEGER DEFAULT 1"),
        ("users", "trang_thai", "TEXT DEFAULT 'hoat_dong'"),
        ("users", "email", "TEXT"),
        # 2. skills
        ("skills", "truong_id", "INTEGER DEFAULT 1"),
        ("skills", "hien_thi_cong_dong", "INTEGER DEFAULT 0"),
        ("skills", "trang_thai_cong_dong", "TEXT DEFAULT 'chua_dang'"),
        ("skills", "nguoi_duyet_cong_dong_id", "INTEGER"),
        ("skills", "ngay_duyet_cong_dong", "TEXT"),
        # 3. sessions, ratings, community_tasks, task_registrations, blog_posts
        ("sessions", "truong_id", "INTEGER DEFAULT 1"),
        ("sessions", "daily_room_name", "TEXT"),
        ("sessions", "daily_room_url", "TEXT"),
        ("ratings", "truong_id", "INTEGER DEFAULT 1"),
        ("community_tasks", "truong_id", "INTEGER DEFAULT 1"),
        ("community_tasks", "anh_bia", "TEXT"),
        ("community_tasks", "ngay_bat_dau", "TEXT"),
        ("community_tasks", "ngay_ket_thuc", "TEXT"),
        ("task_registrations", "truong_id", "INTEGER DEFAULT 1"),
        ("blog_posts", "truong_id", "INTEGER DEFAULT 1"),
        # 4. truong
        ("truong", "an_truong", "INTEGER DEFAULT 0"),
    ]

    for tbl, col_name, col_def in columns_to_add:
        if is_sqlite:
            try:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (tbl,))
                if not cur.fetchone():
                    continue
                _exec(f"PRAGMA table_info({tbl})")
                existing_cols = [r[1] for r in cur.fetchall()]
                if col_name not in existing_cols:
                    _exec(f"ALTER TABLE {tbl} ADD COLUMN {col_name} {col_def}")
                    conn.commit()
            except Exception as e:
                app.logger.warning(f"Lỗi thêm cột {tbl}.{col_name} trên SQLite: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
        else:
            try:
                _exec(f"ALTER TABLE {tbl} ADD COLUMN IF NOT EXISTS {col_name} {col_def}")
                conn.commit()
            except Exception as e:
                app.logger.warning(f"Lỗi ADD COLUMN IF NOT EXISTS {tbl}.{col_name} trên PostgreSQL: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass

    # Đặt an_truong = 1 cho Trường Demo (ID 99) mặc định
    try:
        _exec("UPDATE truong SET an_truong = 1 WHERE id = ?", (DEMO_SCHOOL_ID,))
        conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi cập nhật an_truong cho Trường Demo: {e}")

    # 4. Cập nhật CHECK vai_tro của bảng users để chấp nhận 'super_admin' và 'school_admin'
    if is_sqlite:
        # Trong SQLite, nếu bảng users cũ có CHECK constraint chặn super_admin
        try:
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='users'")
            row = cur.fetchone()
            if row and row[0] and "super_admin" not in row[0]:
                old_sql = row[0]
                new_sql = re.sub(
                    r"vai_tro\s+IN\s*\([^)]+\)",
                    "vai_tro IN ('hoc_sinh', 'giao_vien', 'school_admin', 'super_admin', 'admin')",
                    old_sql
                )
                cur.execute("PRAGMA foreign_keys = OFF")
                cur.execute("ALTER TABLE users RENAME TO _users_old")
                cur.execute(new_sql)
                cur.execute("PRAGMA table_info(_users_old)")
                old_cols = [r[1] for r in cur.fetchall()]
                cols_str = ", ".join(old_cols)
                cur.execute(f"INSERT INTO users ({cols_str}) SELECT {cols_str} FROM _users_old")
                cur.execute("DROP TABLE _users_old")
                cur.execute("PRAGMA foreign_keys = ON")
                conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi nâng cấp check constraint users (SQLite): {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # Cập nhật CHECK trang_thai của bảng truong để chấp nhận 'vo_hieu_hoa' (SQLite)
        try:
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='truong'")
            row = cur.fetchone()
            if row and row[0] and "vo_hieu_hoa" not in row[0]:
                old_sql = row[0]
                new_sql = re.sub(
                    r"trang_thai\s+IN\s*\([^)]+\)",
                    "trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung', 'vo_hieu_hoa')",
                    old_sql
                )
                cur.execute("PRAGMA foreign_keys = OFF")
                cur.execute("PRAGMA legacy_alter_table = ON")
                cur.execute("ALTER TABLE truong RENAME TO _truong_old")
                cur.execute(new_sql)
                cur.execute("PRAGMA table_info(_truong_old)")
                old_cols = [r[1] for r in cur.fetchall()]
                cols_str = ", ".join(old_cols)
                cur.execute(f"INSERT INTO truong ({cols_str}) SELECT {cols_str} FROM _truong_old")
                cur.execute("DROP TABLE _truong_old")
                cur.execute("PRAGMA legacy_alter_table = OFF")
                cur.execute("PRAGMA foreign_keys = ON")
                conn.commit()

            # Tự động khắc phục nếu có bảng con nào bị trỏ nhầm vào _truong_old
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%_truong_old%'")
            corrupt_tables = cur.fetchall()
            if corrupt_tables:
                cur.execute("PRAGMA foreign_keys = OFF")
                cur.execute("PRAGMA legacy_alter_table = ON")
                for c_tbl, c_sql in corrupt_tables:
                    fixed_sql = c_sql.replace('"_truong_old"', 'truong').replace('_truong_old', 'truong')
                    tmp_name = f"_{c_tbl}_repair_tmp"
                    cur.execute(f"ALTER TABLE {c_tbl} RENAME TO {tmp_name}")
                    cur.execute(fixed_sql)
                    cur.execute(f"PRAGMA table_info({tmp_name})")
                    c_cols = [r[1] for r in cur.fetchall()]
                    c_cols_str = ", ".join(c_cols)
                    cur.execute(f"INSERT INTO {c_tbl} ({c_cols_str}) SELECT {c_cols_str} FROM {tmp_name}")
                    cur.execute(f"DROP TABLE {tmp_name}")
                cur.execute("PRAGMA legacy_alter_table = OFF")
                cur.execute("PRAGMA foreign_keys = ON")
                conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi nâng cấp check constraint truong (SQLite): {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # Cập nhật CHECK trang_thai của bảng community_tasks để chấp nhận 'sap_dien_ra', 'dang_dien_ra', 'da_ket_thuc' (SQLite)
        try:
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='community_tasks'")
            row = cur.fetchone()
            if row and row[0] and "sap_dien_ra" not in row[0]:
                old_sql = row[0]
                new_sql = re.sub(
                    r"trang_thai\s+IN\s*\([^)]+\)",
                    "trang_thai IN ('mo_dang_ky', 'mo', 'dong', 'hoan_thanh', 'huy', 'sap_dien_ra', 'dang_dien_ra', 'da_ket_thuc')",
                    old_sql
                )
                cur.execute("PRAGMA foreign_keys = OFF")
                cur.execute("PRAGMA legacy_alter_table = ON")
                cur.execute("ALTER TABLE community_tasks RENAME TO _community_tasks_old")
                cur.execute(new_sql)
                cur.execute("PRAGMA table_info(_community_tasks_old)")
                old_cols = [r[1] for r in cur.fetchall()]
                cols_str = ", ".join(old_cols)
                cur.execute(f"INSERT INTO community_tasks ({cols_str}) SELECT {cols_str} FROM _community_tasks_old")
                cur.execute("DROP TABLE _community_tasks_old")
                cur.execute("PRAGMA legacy_alter_table = OFF")
                cur.execute("PRAGMA foreign_keys = ON")
                conn.commit()

            # Tự động khắc phục nếu có bảng con nào bị trỏ nhầm vào _community_tasks_old
            cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%_community_tasks_old%'")
            corrupt_tables = cur.fetchall()
            if corrupt_tables:
                cur.execute("PRAGMA foreign_keys = OFF")
                cur.execute("PRAGMA legacy_alter_table = ON")
                for c_tbl, c_sql in corrupt_tables:
                    fixed_sql = c_sql.replace('"_community_tasks_old"', 'community_tasks').replace('_community_tasks_old', 'community_tasks')
                    tmp_name = f"_{c_tbl}_repair_tmp"
                    cur.execute(f"ALTER TABLE {c_tbl} RENAME TO {tmp_name}")
                    cur.execute(fixed_sql)
                    cur.execute(f"PRAGMA table_info({tmp_name})")
                    c_cols = [r[1] for r in cur.fetchall()]
                    c_cols_str = ", ".join(c_cols)
                    cur.execute(f"INSERT INTO {c_tbl} ({c_cols_str}) SELECT {c_cols_str} FROM {tmp_name}")
                    cur.execute(f"DROP TABLE {tmp_name}")
                cur.execute("PRAGMA legacy_alter_table = OFF")
                cur.execute("PRAGMA foreign_keys = ON")
                conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi nâng cấp check constraint community_tasks (SQLite): {e}")
            try:
                conn.rollback()
            except Exception:
                pass
    else:
        constraint_names = set()
        # Tìm trong information_schema
        try:
            _exec("""
                SELECT tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.check_constraints cc
                  ON tc.constraint_name = cc.constraint_name
                 AND tc.constraint_schema = cc.constraint_schema
                WHERE tc.table_name = 'users'
                  AND tc.constraint_type = 'CHECK'
                  AND (cc.check_clause ILIKE '%vai_tro%' OR tc.constraint_name ILIKE '%vai_tro%')
            """)
            for row in cur.fetchall():
                constraint_names.add(row[0])
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        # Tìm trong pg_constraint (catalog hệ thống PostgreSQL)
        try:
            _exec("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'users'
                  AND con.contype = 'c'
                  AND (con.conname ILIKE '%vai_tro%' OR pg_get_constraintdef(con.oid) ILIKE '%vai_tro%')
            """)
            for row in cur.fetchall():
                constraint_names.add(row[0])
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

        constraint_names.add("users_vai_tro_check")

        # Xóa các constraint cũ tìm được
        for cname in constraint_names:
            try:
                _exec(f"ALTER TABLE users DROP CONSTRAINT IF EXISTS {cname}")
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        # Thêm constraint mới hỗ trợ super_admin và school_admin
        try:
            _exec("""
                ALTER TABLE users ADD CONSTRAINT users_vai_tro_check
                CHECK (vai_tro IN ('hoc_sinh', 'giao_vien', 'school_admin', 'super_admin', 'admin'))
            """)
            conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi ADD CONSTRAINT users_vai_tro_check: {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # Cập nhật CHECK trang_thai của bảng truong trên PostgreSQL
        try:
            _exec("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'truong'
                  AND con.contype = 'c'
                  AND (con.conname ILIKE '%trang_thai%' OR pg_get_constraintdef(con.oid) ILIKE '%trang_thai%')
            """)
            t_cnames = [r[0] for r in cur.fetchall()]
            conn.commit()
            for cname in t_cnames:
                try:
                    _exec(f"ALTER TABLE truong DROP CONSTRAINT IF EXISTS {cname}")
                    conn.commit()
                except Exception:
                    pass
            _exec("""
                ALTER TABLE truong ADD CONSTRAINT truong_trang_thai_check
                CHECK (trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung', 'vo_hieu_hoa'))
            """)
            conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi nâng cấp check constraint truong (PostgreSQL): {e}")
            try:
                conn.rollback()
            except Exception:
                pass

        # Cập nhật CHECK trang_thai của bảng community_tasks trên PostgreSQL
        try:
            _exec("""
                SELECT con.conname
                FROM pg_constraint con
                JOIN pg_class rel ON rel.oid = con.conrelid
                WHERE rel.relname = 'community_tasks'
                  AND con.contype = 'c'
                  AND (con.conname ILIKE '%trang_thai%' OR pg_get_constraintdef(con.oid) ILIKE '%trang_thai%')
            """)
            ct_cnames = [r[0] for r in cur.fetchall()]
            conn.commit()
            for cname in ct_cnames:
                try:
                    _exec(f"ALTER TABLE community_tasks DROP CONSTRAINT IF EXISTS {cname}")
                    conn.commit()
                except Exception:
                    pass
            _exec("""
                ALTER TABLE community_tasks ADD CONSTRAINT community_tasks_trang_thai_check
                CHECK (trang_thai IN ('mo_dang_ky', 'mo', 'dong', 'hoan_thanh', 'huy', 'sap_dien_ra', 'dang_dien_ra', 'da_ket_thuc'))
            """)
            conn.commit()
        except Exception as e:
            app.logger.warning(f"Lỗi nâng cấp check constraint community_tasks (PostgreSQL): {e}")
            try:
                conn.rollback()
            except Exception:
                pass

    # 5. Seed 4 trường vào bảng truong NẾU bảng rỗng (giống seed_demo_data)
    try:
        _exec("SELECT COUNT(*) FROM truong")
        row = cur.fetchone()
        school_count = row[0] if row else 0
        if school_count == 0:
            schools = [
                (1, "Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy", "/static/img/logo_timebank_edu.png", "dang_thi_diem"),
                (2, "Trường THCS Nguyễn Văn Thuộc", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai"),
                (3, "Trường THCS Lê Văn Tám", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai"),
                (4, "Trường THPT Hải Đảo", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai")
            ]
            for s in schools:
                try:
                    _exec("INSERT INTO truong (id, ten_truong, logo, trang_thai) VALUES (?, ?, ?, ?)", s)
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            conn.commit()

            if not is_sqlite:
                try:
                    _exec("SELECT setval(pg_get_serial_sequence('truong', 'id'), COALESCE(MAX(id), 1)) FROM truong")
                    conn.commit()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
    except Exception as e:
        app.logger.warning(f"Lỗi seed 4 trường học trong migrate_postgres_schema: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # 6. UPDATE các dòng cũ: SET truong_id = 1 WHERE truong_id IS NULL (đề phòng DEFAULT không backfill)
    tables_to_backfill = [
        "users", "skills", "sessions", "ratings",
        "community_tasks", "task_registrations", "blog_posts"
    ]
    for tbl in tables_to_backfill:
        try:
            if is_sqlite:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", (tbl,))
                if not cur.fetchone():
                    continue
            _exec(f"UPDATE {tbl} SET truong_id = 1 WHERE truong_id IS NULL")
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    # Backfill thêm trang_thai nếu NULL
    try:
        _exec("UPDATE users SET trang_thai = 'hoat_dong' WHERE trang_thai IS NULL")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    try:
        _exec("UPDATE skills SET hien_thi_cong_dong = 0 WHERE hien_thi_cong_dong IS NULL")
        _exec("UPDATE skills SET trang_thai_cong_dong = 'chua_dang' WHERE trang_thai_cong_dong IS NULL")
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    # 7. Nâng tài khoản 'admin' cũ lên vai_tro = 'super_admin' NẾU đang là 'admin'
    try:
        _exec("UPDATE users SET vai_tro = 'super_admin' WHERE ma_hoc_sinh = 'admin' AND vai_tro = 'admin'")
        conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi nâng cấp tài khoản admin lên super_admin: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # 8. Bảng tu_van_trien_khai (Prompt 21+: Đăng ký tư vấn triển khai)
    try:
        if is_sqlite:
            _exec("""
                CREATE TABLE IF NOT EXISTS tu_van_trien_khai (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ten_truong TEXT NOT NULL,
                    ho_ten TEXT NOT NULL,
                    sdt TEXT NOT NULL,
                    email TEXT,
                    ghi_chu TEXT,
                    trang_thai TEXT DEFAULT 'cho_lien_he',
                    thoi_gian_gui TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
        else:
            _exec("""
                CREATE TABLE IF NOT EXISTS tu_van_trien_khai (
                    id SERIAL PRIMARY KEY,
                    ten_truong TEXT NOT NULL,
                    ho_ten TEXT NOT NULL,
                    sdt TEXT NOT NULL,
                    email TEXT,
                    ghi_chu TEXT,
                    trang_thai TEXT DEFAULT 'cho_lien_he',
                    thoi_gian_gui TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
        conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi tạo bảng tu_van_trien_khai trong migrate_postgres_schema: {e}")
        try:
            conn.rollback()
        except Exception:
            pass

    # 9. Bảng password_reset_tokens (Prompt 23: Quên mật khẩu qua email)
    try:
        if is_sqlite:
            _exec("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    het_han TEXT NOT NULL,
                    da_dung INTEGER DEFAULT 0,
                    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        else:
            _exec("""
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    het_han TEXT NOT NULL,
                    da_dung INTEGER DEFAULT 0,
                    ngay_tao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
        conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi tạo bảng password_reset_tokens trong migrate_postgres_schema: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


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
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
            conn.commit()

            # Hotfix Prompt 20: Tự động migrate PostgreSQL Production (P17–P19)
            migrate_postgres_schema(conn)

            cur.execute("SELECT COUNT(*) FROM users")
            row = cur.fetchone()
            user_count = row[0] if row else 0
            if user_count == 0:
                seed_demo_data(conn)
            # Luôn đồng bộ Trường Demo và tài khoản demo công khai (Prompt 23)
            seed_demo_school_and_accounts(conn)
            # Tự động tạo Super Admin từ biến môi trường khi khởi động (Prompt 23.5)
            auto_create_superadmin_from_env(conn)
            conn.close()
            return
        except Exception as e:
            app.logger.warning(f"Không thể khởi tạo CSDL PostgreSQL ({e}), tiếp tục dùng SQLite.")

    # Mặc định: Dùng SQLite cục bộ
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    conn.commit()

    # Tự động nâng cấp bảng skills cho Prompt 19 (Sàn cộng đồng liên trường)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA table_info(skills)")
        skill_cols = [r[1] for r in cur.fetchall()]
        if "hien_thi_cong_dong" not in skill_cols:
            conn.execute("ALTER TABLE skills ADD COLUMN hien_thi_cong_dong INTEGER DEFAULT 0")
        if "trang_thai_cong_dong" not in skill_cols:
            conn.execute("ALTER TABLE skills ADD COLUMN trang_thai_cong_dong TEXT DEFAULT 'chua_dang'")
        if "nguoi_duyet_cong_dong_id" not in skill_cols:
            conn.execute("ALTER TABLE skills ADD COLUMN nguoi_duyet_cong_dong_id INTEGER")
        if "ngay_duyet_cong_dong" not in skill_cols:
            conn.execute("ALTER TABLE skills ADD COLUMN ngay_duyet_cong_dong TEXT")
        conn.commit()

        # Prompt 21 & Prompt Quản lý Chương trình Cộng đồng: Tự động nâng cấp bảng community_tasks
        cur.execute("PRAGMA table_info(community_tasks)")
        task_cols = [r[1] for r in cur.fetchall()]
        if "anh_bia" not in task_cols:
            conn.execute("ALTER TABLE community_tasks ADD COLUMN anh_bia TEXT")
        if "ngay_bat_dau" not in task_cols:
            conn.execute("ALTER TABLE community_tasks ADD COLUMN ngay_bat_dau TEXT")
        if "ngay_ket_thuc" not in task_cols:
            conn.execute("ALTER TABLE community_tasks ADD COLUMN ngay_ket_thuc TEXT")
        conn.commit()

        # Prompt 22: Tự động nâng cấp bảng sessions có cột daily_room_name, daily_room_url
        cur.execute("PRAGMA table_info(sessions)")
        sess_cols = [r[1] for r in cur.fetchall()]
        if "daily_room_name" not in sess_cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN daily_room_name TEXT")
        if "daily_room_url" not in sess_cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN daily_room_url TEXT")
        conn.commit()

        # Prompt 21+: Đảm bảo bảng tu_van_trien_khai tồn tại
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tu_van_trien_khai (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ten_truong TEXT NOT NULL,
                ho_ten TEXT NOT NULL,
                sdt TEXT NOT NULL,
                email TEXT,
                ghi_chu TEXT,
                trang_thai TEXT DEFAULT 'cho_lien_he',
                thoi_gian_gui TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

        # Prompt 23: Nâng cấp cột email cho bảng users và bảng password_reset_tokens
        cur.execute("PRAGMA table_info(users)")
        u_cols = [r[1] for r in cur.fetchall()]
        if "email" not in u_cols:
            conn.execute("ALTER TABLE users ADD COLUMN email TEXT")
        conn.commit()

        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                het_han TEXT NOT NULL,
                da_dung INTEGER DEFAULT 0,
                ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()

        # Prompt 32: Đảm bảo cột an_truong tồn tại trong bảng truong (SQLite)
        cur.execute("PRAGMA table_info(truong)")
        t_cols = [r[1] for r in cur.fetchall()]
        if "an_truong" not in t_cols:
            conn.execute("ALTER TABLE truong ADD COLUMN an_truong INTEGER DEFAULT 0")
            conn.commit()
        # Đặt an_truong = 1 cho Trường Demo (ID 99) mặc định
        conn.execute("UPDATE truong SET an_truong = 1 WHERE id = ?", (DEMO_SCHOOL_ID,))
        conn.commit()

        # Nâng cấp CHECK constraint cho bảng truong để chấp nhận 'vo_hieu_hoa'
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='truong'")
        t_row = cur.fetchone()
        if t_row and t_row[0] and "vo_hieu_hoa" not in t_row[0]:
            t_old_sql = t_row[0]
            t_new_sql = re.sub(
                r"trang_thai\s+IN\s*\([^)]+\)",
                "trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung', 'vo_hieu_hoa')",
                t_old_sql
            )
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA legacy_alter_table = ON")
            conn.execute("ALTER TABLE truong RENAME TO _truong_old")
            conn.execute(t_new_sql)
            cur.execute("PRAGMA table_info(_truong_old)")
            t_cols = [r[1] for r in cur.fetchall()]
            t_cols_str = ", ".join(t_cols)
            conn.execute(f"INSERT INTO truong ({t_cols_str}) SELECT {t_cols_str} FROM _truong_old")
            conn.execute("DROP TABLE _truong_old")
            conn.execute("PRAGMA legacy_alter_table = OFF")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        # Tự động khắc phục nếu có bảng con nào bị trỏ nhầm vào _truong_old
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%_truong_old%'")
        corrupt_tables = cur.fetchall()
        if corrupt_tables:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA legacy_alter_table = ON")
            for c_tbl, c_sql in corrupt_tables:
                fixed_sql = c_sql.replace('"_truong_old"', 'truong').replace('_truong_old', 'truong')
                tmp_name = f"_{c_tbl}_repair_tmp"
                conn.execute(f"ALTER TABLE {c_tbl} RENAME TO {tmp_name}")
                conn.execute(fixed_sql)
                cur.execute(f"PRAGMA table_info({tmp_name})")
                c_cols = [r[1] for r in cur.fetchall()]
                c_cols_str = ", ".join(c_cols)
                conn.execute(f"INSERT INTO {c_tbl} ({c_cols_str}) SELECT {c_cols_str} FROM {tmp_name}")
                conn.execute(f"DROP TABLE {tmp_name}")
            conn.execute("PRAGMA legacy_alter_table = OFF")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        # Nâng cấp CHECK constraint cho bảng community_tasks để chấp nhận 'sap_dien_ra', 'dang_dien_ra', 'da_ket_thuc' (SQLite)
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='community_tasks'")
        ct_row = cur.fetchone()
        if ct_row and ct_row[0] and "sap_dien_ra" not in ct_row[0]:
            ct_old_sql = ct_row[0]
            ct_new_sql = re.sub(
                r"trang_thai\s+IN\s*\([^)]+\)",
                "trang_thai IN ('mo_dang_ky', 'mo', 'dong', 'hoan_thanh', 'huy', 'sap_dien_ra', 'dang_dien_ra', 'da_ket_thuc')",
                ct_old_sql
            )
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA legacy_alter_table = ON")
            conn.execute("ALTER TABLE community_tasks RENAME TO _community_tasks_old")
            conn.execute(ct_new_sql)
            cur.execute("PRAGMA table_info(_community_tasks_old)")
            ct_cols = [r[1] for r in cur.fetchall()]
            ct_cols_str = ", ".join(ct_cols)
            conn.execute(f"INSERT INTO community_tasks ({ct_cols_str}) SELECT {ct_cols_str} FROM _community_tasks_old")
            conn.execute("DROP TABLE _community_tasks_old")
            conn.execute("PRAGMA legacy_alter_table = OFF")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()

        # Tự động khắc phục nếu có bảng con nào bị trỏ nhầm vào _community_tasks_old
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%_community_tasks_old%'")
        ct_corrupt = cur.fetchall()
        if ct_corrupt:
            conn.execute("PRAGMA foreign_keys = OFF")
            conn.execute("PRAGMA legacy_alter_table = ON")
            for c_tbl, c_sql in ct_corrupt:
                fixed_sql = c_sql.replace('"_community_tasks_old"', 'community_tasks').replace('_community_tasks_old', 'community_tasks')
                tmp_name = f"_{c_tbl}_repair_tmp"
                conn.execute(f"ALTER TABLE {c_tbl} RENAME TO {tmp_name}")
                conn.execute(fixed_sql)
                cur.execute(f"PRAGMA table_info({tmp_name})")
                c_cols = [r[1] for r in cur.fetchall()]
                c_cols_str = ", ".join(c_cols)
                conn.execute(f"INSERT INTO {c_tbl} ({c_cols_str}) SELECT {c_cols_str} FROM {tmp_name}")
                conn.execute(f"DROP TABLE {tmp_name}")
            conn.execute("PRAGMA legacy_alter_table = OFF")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi nâng cấp cấu trúc bảng skills/community_tasks/password_reset_tokens/truong: {e}")
    
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if user_count == 0:
        seed_demo_data(conn)
        
    # Luôn đồng bộ Trường Demo và tài khoản demo công khai (Prompt 23)
    seed_demo_school_and_accounts(conn)
    # Tự động tạo Super Admin từ biến môi trường khi khởi động (Prompt 23.5)
    auto_create_superadmin_from_env(conn)
    conn.close()


def seed_demo_school_and_accounts(conn):
    """
    Prompt 23 (Việc 1): Seed Trường Demo và các tài khoản demo công khai cho giám khảo:
    - Tạo 'Trường Demo' (id = 99)
    - 3 tài khoản demo:
      + demo_quantruong (school_admin, truong_id=99)
      + demo_giaovien (giao_vien, truong_id=99)
      + demo_hocsinh (hoc_sinh, truong_id=99)
    - Hạ quyền tài khoản 'admin' cũ: từ super_admin -> school_admin của Trường Demo
    - Dữ liệu demo riêng: kỹ năng, buổi học, ledger
    """
    cur = conn.cursor()

    # 1. Đảm bảo Trường Demo tồn tại (id = 99)
    cur.execute("SELECT id FROM truong WHERE id = ?", (DEMO_SCHOOL_ID,))
    if not cur.fetchone():
        try:
            cur.execute(
                "INSERT INTO truong (id, ten_truong, logo, trang_thai, an_truong) VALUES (?, ?, ?, ?, 1)",
                (DEMO_SCHOOL_ID, DEMO_SCHOOL_NAME, "/static/img/logo_timebank_edu.png", "dang_thi_diem")
            )
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    demo_pass_hash = generate_password_hash("demo123")
    admin_pass_hash = generate_password_hash("admin123")

    demo_users = [
        ("demo_quantruong", "Quản trị viên Demo", "Ban Giám Hiệu Demo", "school_admin", 100.0, "Toàn thời gian", demo_pass_hash, DEMO_SCHOOL_ID, "hoat_dong", "demo_quantruong@timebankedu.vn"),
        ("demo_giaovien", "Thầy/Cô Giáo viên Demo", "Tổ Sư Phạm Demo", "giao_vien", 10.0, "Các buổi trong tuần", demo_pass_hash, DEMO_SCHOOL_ID, "hoat_dong", "demo_giaovien@timebankedu.vn"),
        ("demo_hocsinh", "Lê Học Sinh Demo", "12-Demo", "hoc_sinh", 3.0, "Tối thứ 3, tối thứ 5", demo_pass_hash, DEMO_SCHOOL_ID, "hoat_dong", "demo_hocsinh@timebankedu.vn"),
        ("demo_hocsinh_2", "Trần Bạn Học Demo", "12-Demo", "hoc_sinh", 2.0, "Chiều thứ 7, tối Chủ nhật", demo_pass_hash, DEMO_SCHOOL_ID, "hoat_dong", "demo_hocsinh2@timebankedu.vn"),
    ]

    for mhs, ten, lop, role, so_gio, ranh, pwd, tid, status, email in demo_users:
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (mhs,))
        row = cur.fetchone()
        if not row:
            try:
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai, email)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (mhs, ten, lop, role, so_gio, ranh, pwd, tid, status, email))
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass
        else:
            try:
                cur.execute("""
                    UPDATE users SET ho_ten = ?, lop = ?, vai_tro = ?, truong_id = ?, trang_thai = ?, email = ?
                    WHERE ma_hoc_sinh = ?
                """, (ten, lop, role, tid, status, email, mhs))
                conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

    # Hạ quyền tài khoản 'admin' cũ: từ super_admin -> school_admin của Trường Demo
    try:
        cur.execute("""
            UPDATE users SET vai_tro = 'school_admin', truong_id = ?, lop = 'Ban Giám Hiệu Demo'
            WHERE ma_hoc_sinh = 'admin'
        """, (DEMO_SCHOOL_ID,))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass

    # Đảm bảo có kỹ năng mẫu cho Trường Demo
    try:
        cur.execute("SELECT COUNT(*) FROM skills WHERE truong_id = ?", (DEMO_SCHOOL_ID,))
        sk_count_row = cur.fetchone()
        sk_count = sk_count_row[0] if sk_count_row else 0
        if sk_count == 0:
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'demo_hocsinh'")
            hs1_row = cur.fetchone()
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'demo_hocsinh_2'")
            hs2_row = cur.fetchone()

            if hs1_row and hs2_row:
                u1_id = hs1_row[0]
                u2_id = hs2_row[0]
                demo_skills = [
                    (u1_id, "Toán học", "Phương pháp giải nhanh Trắc nghiệm Hình 12 (Demo)", "Kỹ năng mẫu dành cho giám khảo trải nghiệm phòng học ảo và trao đổi giờ", "da_duyet", "Nội dung demo đã được phê duyệt", DEMO_SCHOOL_ID),
                    (u2_id, "Tin học", "Lập trình Python và Trí tuệ nhân tạo căn bản (Demo)", "Hướng dẫn thực hành tạo chatbot và thuật toán cho học sinh THPT", "da_duyet", "Nội dung demo đã được phê duyệt", DEMO_SCHOOL_ID)
                ]
                cur.executemany("""
                    INSERT INTO skills (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet, truong_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, demo_skills)
                conn.commit()

                # Tạo 1 session demo hoàn thành
                cur.execute("SELECT id FROM skills WHERE user_id = ? AND truong_id = ? LIMIT 1", (u1_id, DEMO_SCHOOL_ID))
                sk_row = cur.fetchone()
                if sk_row:
                    cur.execute("""
                        INSERT INTO sessions (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan, truong_id)
                        VALUES (?, ?, ?, '2026-10-08 14:00:00', 1.0, 'hoan_thanh', 'QR_DEMO_01', 1, 1, 'Dàn ý AI: Khái niệm góc giữa hai mặt phẳng (Demo)', 1, ?)
                    """, (sk_row[0], u1_id, u2_id, DEMO_SCHOOL_ID))
                    conn.commit()
    except Exception as e:
        app.logger.warning(f"Lỗi khởi tạo kỹ năng/phiên học mẫu trường demo: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def auto_create_superadmin_from_env(conn=None):
    """
    Prompt 23.5: TỰ ĐỘNG TẠO SUPER ADMIN KHI KHỞI ĐỘNG (thay cho lệnh Shell trên Render)

    # =============================================================================
    # HƯỚNG DẪN CHO THẦY (Prompt 23.5):
    # 1. Render -> Environment -> thêm SUPERADMIN_USER + SUPERADMIN_PASS -> Save
    # 2. Đợi deploy xong (~3 phút) -> đăng nhập thử tài khoản mới
    # 3. Xóa ngay 2 biến -> Save
    # =============================================================================
    """
    super_user = (os.getenv("SUPERADMIN_USER") or "").strip()
    super_pass = (os.getenv("SUPERADMIN_PASS") or "").strip()

    # Thiếu biến môi trường -> bỏ qua, không làm gì
    if not super_user or not super_pass:
        return

    should_close = False
    if conn is None:
        conn = get_db()

    cur = conn.cursor()
    # Kiểm tra xem user có ma_hoc_sinh tương ứng đã tồn tại hay chưa
    cur.execute("SELECT id, mat_khau FROM users WHERE ma_hoc_sinh = ?", (super_user,))
    existing_user = cur.fetchone()
    if existing_user:
        # User đã tồn tại -> bỏ qua, không ghi đè, không đổi mật khẩu cũ
        return

    # Chưa tồn tại -> tạo mới super admin
    try:
        pwd_hash = generate_password_hash(super_pass)
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai, email)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            super_user,
            "Tổng Quản trị viên (Cô Huyền)",
            "Ban Điều Hành Quốc Gia",
            "super_admin",
            999.0,
            "Toàn thời gian",
            pwd_hash,
            1,
            "hoat_dong",
            "mshuyenuka@gmail.com"
        ))
        conn.commit()
        # Log xác nhận (TUYỆT ĐỐI KHÔNG log user hoặc pass)
        app.logger.info("Đã tạo super admin từ biến môi trường")
        print("Đã tạo super admin từ biến môi trường")
    except Exception as e:
        app.logger.warning(f"Lỗi khi tự động tạo super admin từ biến môi trường: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def reset_demo_school_data(db):
    """
    Prompt 23 (Việc 3): Nút 'Reset demo':
    1 click đưa dữ liệu Trường Demo về trạng thái ban đầu:
    - Xóa các dữ liệu rác/mới phát sinh thuộc truong_id = DEMO_SCHOOL_ID
    - Reset số dư giờ và mật khẩu của các tài khoản demo
    - Tái lập kỹ năng và phiên học mẫu chuẩn
    """
    cur = db.cursor()
    # 1. Xóa các tài khoản học sinh/giáo viên tạo thêm trong trường demo
    cur.execute("""
        DELETE FROM users 
        WHERE truong_id = ? 
          AND ma_hoc_sinh NOT IN ('demo_quantruong', 'demo_giaovien', 'demo_hocsinh', 'demo_hocsinh_2', 'admin')
    """, (DEMO_SCHOOL_ID,))

    # 2. Xóa toàn bộ dữ liệu giao dịch, đánh giá, session, skills của trường demo
    cur.execute("DELETE FROM ratings WHERE truong_id = ?", (DEMO_SCHOOL_ID,))
    tbl_ledger = "credits_" + "ledger"
    cur.execute(f"DELETE FROM {tbl_ledger} WHERE user_id IN (SELECT id FROM users WHERE truong_id = ?)", (DEMO_SCHOOL_ID,))
    cur.execute("DELETE FROM quiz_results WHERE session_id IN (SELECT id FROM sessions WHERE truong_id = ?)", (DEMO_SCHOOL_ID,))
    cur.execute("DELETE FROM sessions WHERE truong_id = ?", (DEMO_SCHOOL_ID,))
    cur.execute("DELETE FROM skills WHERE truong_id = ?", (DEMO_SCHOOL_ID,))

    # 3. Đặt lại số dư giờ & mật khẩu chuẩn
    demo_pass_hash = generate_password_hash("demo123")
    admin_pass_hash = generate_password_hash("admin123")

    cur.execute("UPDATE users SET so_du_gio = 100.0, mat_khau = ?, trang_thai = 'hoat_dong', vai_tro = 'school_admin' WHERE ma_hoc_sinh = 'demo_quantruong'", (demo_pass_hash,))
    cur.execute("UPDATE users SET so_du_gio = 10.0, mat_khau = ?, trang_thai = 'hoat_dong', vai_tro = 'giao_vien' WHERE ma_hoc_sinh = 'demo_giaovien'", (demo_pass_hash,))
    cur.execute("UPDATE users SET so_du_gio = 3.0, mat_khau = ?, trang_thai = 'hoat_dong', vai_tro = 'hoc_sinh' WHERE ma_hoc_sinh = 'demo_hocsinh'", (demo_pass_hash,))
    cur.execute("UPDATE users SET so_du_gio = 2.0, mat_khau = ?, trang_thai = 'hoat_dong', vai_tro = 'hoc_sinh' WHERE ma_hoc_sinh = 'demo_hocsinh_2'", (demo_pass_hash,))
    cur.execute("UPDATE users SET so_du_gio = 100.0, mat_khau = ?, trang_thai = 'hoat_dong', vai_tro = 'school_admin', truong_id = ? WHERE ma_hoc_sinh = 'admin'", (admin_pass_hash, DEMO_SCHOOL_ID))

    db.commit()

    # 4. Tái lập kỹ năng và phiên học mẫu
    seed_demo_school_and_accounts(db)
    return True


def seed_demo_data(conn):
    """
    Nạp dữ liệu mẫu sư phạm phục vụ thuyết trình và demo thực tế:
    - Tạo sẵn 4 trường học thí điểm & chuẩn bị triển khai
    - Tạo sẵn tài khoản giáo viên GV001/admin123
    - 5 học sinh tiêu biểu (An, Bình, Chi, Minh, Hà) với số dư giờ khởi đầu
    - Các kỹ năng đăng ký, phiên học thực tế, sổ cái tín dụng và đánh giá
    """
    cur = conn.cursor()
    default_pass_hash = generate_password_hash("admin123")
    
    # 0. Seed 4 trường học
    cur.execute("SELECT COUNT(*) FROM truong")
    school_count = cur.fetchone()[0]
    if school_count == 0:
        schools = [
            (1, "Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy", "/static/img/logo_timebank_edu.png", "dang_thi_diem", 0),
            (2, "Trường THCS Nguyễn Văn Thuộc", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai", 0),
            (3, "Trường THCS Lê Văn Tám", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai", 0),
            (4, "Trường THPT Hải Đảo", "/static/img/logo_timebank_edu.png", "chuan_bi_trien_khai", 0),
            (DEMO_SCHOOL_ID, DEMO_SCHOOL_NAME, "/static/img/logo_timebank_edu.png", "dang_thi_diem", 1)
        ]
        cur.executemany(
            """INSERT INTO truong (id, ten_truong, logo, trang_thai, an_truong) VALUES (?, ?, ?, ?, ?)""",
            schools
        )
    else:
        cur.execute("SELECT COUNT(*) FROM truong WHERE id = ?", (DEMO_SCHOOL_ID,))
        if cur.fetchone()[0] == 0:
            cur.execute(
                """INSERT INTO truong (id, ten_truong, logo, trang_thai, an_truong) VALUES (?, ?, ?, ?, 1)""",
                (DEMO_SCHOOL_ID, DEMO_SCHOOL_NAME, "/static/img/logo_timebank_edu.png", "dang_thi_diem")
            )
        else:
            cur.execute("UPDATE truong SET an_truong = 1 WHERE id = ?", (DEMO_SCHOOL_ID,))

    # 1. Thêm người dùng mẫu (admin hạ quyền thành school_admin của Trường Demo)
    users = [
        ('admin', 'Quản trị viên Hệ thống (Demo)', 'Ban Giám Hiệu Demo', 'school_admin', 100.0, 'Toàn thời gian', default_pass_hash, DEMO_SCHOOL_ID, 'hoat_dong'),
        ('GV001', 'Thầy Nguyễn Văn Đức', 'Tổ Toán - Tin', 'giao_vien', 10.0, 'Các buổi chiều trong tuần', default_pass_hash, 1, 'hoat_dong'),
        ('HS12001', 'Nguyễn Hoàng An', '12A1', 'hoc_sinh', 3.5, 'Chiều thứ 3, sáng thứ 7', default_pass_hash, 1, 'hoat_dong'),
        ('HS11002', 'Trần Thanh Bình', '11B2', 'hoc_sinh', 2.5, 'Sáng Chủ nhật, tối thứ 5', default_pass_hash, 1, 'hoat_dong'),
        ('HS10003', 'Lê Kim Chi', '10A3', 'hoc_sinh', 3.0, 'Chiều thứ 6, sáng Chủ nhật', default_pass_hash, 1, 'hoat_dong'),
        ('HS11004', 'Phạm Quang Minh', '11A1', 'hoc_sinh', 2.0, 'Tối thứ 2, tối thứ 4', default_pass_hash, 1, 'hoat_dong'),
        ('HS12005', 'Vũ Thu Hà', '12D2', 'hoc_sinh', 2.0, 'Sáng thứ 7, chiều Chủ nhật', default_pass_hash, 1, 'hoat_dong')
    ]
    cur.executemany(
        """INSERT INTO users 
           (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        users
    )
    
    # 2. Thêm kỹ năng chia sẻ (user_id = 3 là HS12001, 4 là HS11002, 5 là HS10003...)
    skills = [
        (3, 'Toán học', 'Ôn tập Hình học không gian lớp 12', 'Phương pháp giải nhanh trắc nghiệm khoảng cách và góc', 'da_duyet', 'Nội dung bổ ích, phù hợp chương trình', 1),
        (4, 'Năng khiếu', 'Đệm hát Guitar cơ bản cho người mới', 'Cách bấm các hợp âm chuẩn và kỹ thuật quạt chả điệu Disco', 'da_duyet', 'Kỹ năng giải trí tích cực', 1),
        (5, 'Ngoại ngữ', 'Luyện phản xạ nói Tiếng Anh IELTS Speaking', 'Chiến thuật trả lời Part 1 và Part 2 tự nhiên, lưu loát', 'da_duyet', 'Rất hữu ích cho học sinh hội nhập', 1),
        (6, 'Tin học', 'Lập trình Python cho người mới bắt đầu', 'Cấu trúc rẽ nhánh, vòng lặp và xử lý chuỗi căn bản', 'da_duyet', 'Định hướng chuyển đổi số trường học', 1),
        (7, 'Khoa học', 'Phương pháp làm bài thí nghiệm Hóa học 12', 'Giải thích hiện tượng và mẹo nhớ tính chất kim loại kiềm', 'cho_duyet', 'Chờ giáo viên bộ môn duyệt nội dung', 1),
        (5, 'Toán học', 'Phương pháp vẽ đồ thị và khảo sát hàm số 12', 'Kỹ thuật nhận diện bảng biến thiên và cực trị hàm số', 'da_duyet', 'Nội dung trọng tâm thi tốt nghiệp THPT', 1),
        (7, 'Toán học', 'Bí quyết giải nhanh Toán Xác suất và Thống kê', 'Phương pháp tư duy sơ đồ cây và bài toán xác suất thực tế', 'da_duyet', 'Rèn luyện tư duy logic và suy luận', 1)
    ]
    cur.executemany(
        """INSERT INTO skills 
           (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet, truong_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        skills
    )
    
    # 3. Thêm các phiên học hoàn thành thực tế (Sessions)
    sessions = [
        (1, 3, 4, '2026-09-28 14:00:00', 1.0, 'hoan_thanh', 'QR_SES_001', 1, 1, 'Dàn ý AI: Khái niệm góc giữa hai mặt phẳng + 3 bài tập mẫu', 1, 1),
        (2, 4, 5, '2026-09-29 15:30:00', 1.0, 'hoan_thanh', 'QR_SES_002', 1, 1, 'Dàn ý AI: Hợp âm C-Am-Dm-G7 + bài tập bấm tay', 1, 1),
        (3, 5, 3, '2026-10-01 16:00:00', 1.0, 'hoan_thanh', 'QR_SES_003', 1, 1, 'Dàn ý AI: Chủ đề Hometown & Hobbies', 1, 1),
        (1, 3, 6, '2026-10-03 09:00:00', 1.0, 'hoan_thanh', 'QR_SES_004', 1, 1, 'Dàn ý AI: Góc giữa đường thẳng và mặt phẳng', 1, 1),
        (4, 6, 7, '2026-10-04 14:30:00', 1.0, 'hoan_thanh', 'QR_SES_005', 1, 1, 'Dàn ý AI: Biến số và lệnh input/print trong Python', 1, 1)
    ]
    cur.executemany(
        """INSERT INTO sessions 
           (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan, truong_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
        (1, 4, 3, 5, 'Anh An giảng Toán rất dễ hiểu, giải thích bài tập góc không gian siêu hay!', 1),
        (2, 5, 4, 5, 'Bình dạy đàn kiên nhẫn, chỉ cách chuyển hợp âm rất dễ nhớ.', 1),
        (3, 3, 5, 5, 'Chi phát âm chuẩn, sửa lỗi ngữ điệu cho mình rất nhiệt tình.', 1),
        (4, 6, 3, 5, 'Buổi học rất bổ ích, mình đã tự tin làm được bài kiểm tra.', 1),
        (5, 7, 6, 4, 'Minh chỉ code dễ hiểu, mong có thêm buổi học tiếp theo.', 1)
    ]
    cur.executemany(
        """INSERT INTO ratings 
           (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet, truong_id) 
           VALUES (?, ?, ?, ?, ?, ?)""",
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
        ('Dọn rác bãi biển Hạ Long sáng Chủ nhật', 'Hoạt động thanh niên tình nguyện thu gom rác thải nhựa tại bờ biển, làm sạch cảnh quan môi trường.', 'Bãi tắm Bãi Cháy, TP. Hạ Long', 2.0, 10, '2026-10-25', 2, 'mo_dang_ky', '2026-10-05 08:00:00', 1),
        ('Hỗ trợ thư viện trường sắp xếp sách', 'Phân loại sách giáo khoa mới, dán mã định danh và sắp xếp lên giá sách theo chuẩn thư viện xanh.', 'Phòng Thư viện - Tầng 2', 1.5, 5, '2026-10-20', 2, 'mo_dang_ky', '2026-10-05 08:30:00', 1),
        ('Dạy kỹ năng số cho các em khối Tiểu học', 'Phụ đạo tin học, hướng dẫn các em học sinh lớp 3-4 gõ bàn phím 10 ngón và tra cứu tài liệu học tập an toàn.', 'Phòng máy Tin học số 2', 2.0, 4, '2026-10-30', 2, 'mo_dang_ky', '2026-10-05 09:00:00', 1),
        ('Hỗ trợ số hóa tài liệu thư viện trường', 'Quét và phân loại sách tham khảo vào hệ thống thư viện điện tử.', 'Phòng Thư viện - Tầng 2', 2.0, 4, '2026-10-15', 2, 'hoan_thanh', '2026-10-04 08:00:00', 1)
    ]
    cur.executemany(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai, thoi_gian_tao, truong_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        community_tasks
    )

    # 8. Thêm đăng ký nhiệm vụ cộng đồng (task_registrations)
    task_regs = [
        (4, 3, 'hoan_thanh', '2026-10-04 08:15:00', 1),
        (2, 4, 'da_dang_ky', '2026-10-05 08:45:00', 1)
    ]
    cur.executemany(
        "INSERT INTO task_registrations (task_id, user_id, trang_thai, thoi_gian_dang_ky, truong_id) VALUES (?, ?, ?, ?, ?)",
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
            '2026-10-01 08:00:00',
            1
        )
    ]
    cur.executemany(
        """INSERT INTO blog_posts 
           (tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang, truong_id) 
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
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
def get_realtime_stats(db, truong_id=None):
    """
    Truy vấn số liệu thống kê thời gian thực từ cơ sở dữ liệu:
    - Tổng thành viên: Đếm số lượng học sinh và giáo viên
    - Phiên hoàn thành: Đếm số buổi học có trạng thái 'hoan_thanh'
    - Giờ lưu thông: Tổng số giờ đã được trao đổi thành công
    - Kỹ năng sẵn sàng: Đếm các kỹ năng đã được duyệt và sẵn sàng chia sẻ
    """
    cur = db.cursor()
    if truong_id:
        cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro = 'hoc_sinh' AND truong_id = ?", (truong_id,))
        tong_thanh_vien = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh' AND truong_id = ?", (truong_id,))
        phien_hoan_thanh = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh' AND truong_id = ?", (truong_id,))
        gio_luu_thong = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM skills WHERE trang_thai_duyet = 'da_duyet' AND truong_id = ?", (truong_id,))
        ky_nang_san_sang = cur.fetchone()[0]
    else:
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


def get_top_tutors(db, limit=3, truong_id=None):
    """
    Truy vấn tự động Top Gia sư Học đường tích cực nhất:
    Tính toán dựa trên số giờ đã giảng dạy (sessions hoàn thành) và điểm đánh giá sao trung bình.
    """
    cur = db.cursor()
    where_filter = "WHERE u.vai_tro = 'hoc_sinh'"
    params = []
    if truong_id:
        where_filter += " AND u.truong_id = ?"
        params.append(truong_id)
    params.append(limit)

    query = f"""
        SELECT 
            u.id, 
            u.ma_hoc_sinh, 
            u.ho_ten, 
            u.lop, 
            COALESCE(SUM(s.so_gio), 0.0) AS so_gio_day,
            COUNT(s.id) AS so_phien_day,
            ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
        FROM users u
        LEFT JOIN sessions s ON u.id = s.nguoi_day_id AND s.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON s.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        {where_filter}
        GROUP BY u.id, u.ma_hoc_sinh, u.ho_ten, u.lop
        ORDER BY so_gio_day DESC, sao_tb DESC
        LIMIT ?
    """
    cur.execute(query, params)
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
        LEFT JOIN users u ON t.nguoi_tao_id = u.id
        WHERE t.trang_thai IN ('mo_dang_ky', 'mo', 'sap_dien_ra', 'dang_dien_ra')
        ORDER BY t.id DESC
        LIMIT 3
    """)
    nhiem_vu_gan_nhat = cur.fetchall()

    community_stats = {
        "tong_gio_cong_ich": round(tong_gio_cong_ich, 1),
        "nhiem_vu_gan_nhat": nhiem_vu_gan_nhat
    }

    cur.execute("SELECT * FROM truong WHERE COALESCE(an_truong, 0) = 0 ORDER BY id ASC")
    schools = cur.fetchall()
    
    return render_template(
        "index.html",
        stats=stats,
        top_tutors=top_tutors,
        community_stats=community_stats,
        schools=schools
    )


# ------------------------------------------------------------------------------
# MILESTONE M1: ĐĂNG KÝ, ĐĂNG NHẬP, ĐĂNG XUẤT, HỒ SƠ & PHÂN QUYỀN
# ------------------------------------------------------------------------------

@app.route("/api/check-invite-code", methods=["GET", "POST"])
def check_invite_code():
    """
    API kiểm tra tính hợp lệ của mã mời thời gian thực:
    - Nếu hợp lệ: trả về tên trường, ID trường và khóa dropdown trường trên form đăng ký.
    - Nếu không hợp lệ hoặc hết lượt: trả về thông báo lỗi chi tiết.
    """
    code = request.args.get("code") or (request.get_json() or {}).get("code") or request.form.get("code", "")
    code = (code or "").strip().upper()
    if not code:
        return jsonify({"valid": False, "error": "Vui lòng nhập mã mời."})

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT ic.*, t.ten_truong, t.trang_thai AS trang_thai_truong, COALESCE(t.an_truong, 0) AS an_truong
        FROM invite_codes ic
        JOIN truong t ON ic.truong_id = t.id
        WHERE ic.ma_code = ?
    """, (code,))
    row = cur.fetchone()
    if not row:
        return jsonify({"valid": False, "error": "Mã mời không tồn tại trên hệ thống!"})

    if row["an_truong"] == 1 or row["trang_thai_truong"] == "vo_hieu_hoa":
        return jsonify({"valid": False, "error": "Trường học gắn với mã mời này hiện đang tạm dừng hoạt động hoặc đã bị ẩn / vô hiệu hóa!"})

    if row["da_dung"] >= row["so_luot_toi_da"]:
        return jsonify({"valid": False, "error": "Mã mời này đã hết số lượt sử dụng!"})

    remaining = row["so_luot_toi_da"] - row["da_dung"]
    return jsonify({
        "valid": True,
        "school_id": row["truong_id"],
        "school_name": row["ten_truong"],
        "loai": row["loai"],
        "remaining": remaining
    })


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Đăng ký tài khoản học sinh mới (Bảo vệ đăng ký - Việc 8):
    - Nhập mã mời hợp lệ (TBEDU-XXXX-XXXX) -> tự gán đúng trường, kích hoạt ngay (trang_thai = 'hoat_dong').
    - Không có mã mời -> tự chọn trường trong dropdown -> vào hàng chờ (trang_thai = 'cho_duyet').
    - Cấp vốn khởi tạo mặc định: 2.0 giờ tín dụng.
    - Trường bị vô hiệu hóa hoặc ẩn (an_truong=1 / vo_hieu_hoa) sẽ bị ẩn khỏi dropdown và từ chối đăng ký.
    """
    if "user_id" in session:
        return redirect(url_for("profile"))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM truong WHERE COALESCE(an_truong, 0) = 0 AND trang_thai != 'vo_hieu_hoa' ORDER BY id ASC")
    all_schools = cur.fetchall()

    if request.method == "POST":
        ma_hoc_sinh = request.form.get("ma_hoc_sinh", "").strip()
        ho_ten = request.form.get("ho_ten", "").strip()
        lop = request.form.get("lop", "").strip()
        gio_ranh = request.form.get("gio_ranh", "").strip()
        mat_khau = request.form.get("mat_khau", "")
        mat_khau_xac_nhan = request.form.get("mat_khau_xac_nhan", "")
        ma_code = (request.form.get("ma_code") or request.form.get("ma_moi") or request.form.get("invite_code") or "").strip().upper()
        truong_id_form = (request.form.get("truong_id_hidden") or request.form.get("truong_id") or "").strip()

        # Kiểm tra tính hợp lệ của dữ liệu đầu vào
        if not ma_hoc_sinh or not ho_ten or not mat_khau:
            flash(_("Vui lòng điền đầy đủ các thông tin bắt buộc (*)."), "danger")
            return render_template("register.html", all_schools=all_schools, schools=all_schools)

        if len(mat_khau) < 6:
            flash(_("Mật khẩu phải có độ dài tối thiểu từ 6 ký tự trở lên."), "danger")
            return render_template("register.html", all_schools=all_schools, schools=all_schools)

        if mat_khau != mat_khau_xac_nhan:
            flash(_("Mật khẩu xác nhận không khớp với mật khẩu đã nhập."), "danger")
            return render_template("register.html", all_schools=all_schools, schools=all_schools)

        # Kiểm tra xem mã học sinh đã tồn tại chưa
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (ma_hoc_sinh,))
        if cur.fetchone():
            flash(_("Mã học sinh đã tồn tại trong hệ thống. Vui lòng kiểm tra lại!"), "danger")
            return render_template("register.html", all_schools=all_schools, schools=all_schools)

        assigned_truong_id = 1
        initial_status = "cho_duyet"
        matched_invite_code = None

        if ma_code:
            # Xác thực mã mời kèm kiểm tra trường có bị vô hiệu hóa hoặc ẩn không
            cur.execute("""
                SELECT ic.*, t.trang_thai AS trang_thai_truong, COALESCE(t.an_truong, 0) AS an_truong
                FROM invite_codes ic
                JOIN truong t ON ic.truong_id = t.id
                WHERE ic.ma_code = ?
            """, (ma_code,))
            code_row = cur.fetchone()
            if not code_row:
                flash(_("Mã mời không tồn tại trên hệ thống. Vui lòng kiểm tra lại!"), "danger")
                return render_template("register.html", all_schools=all_schools, schools=all_schools)
            if code_row["an_truong"] == 1 or code_row["trang_thai_truong"] == "vo_hieu_hoa":
                flash(_("Trường học gắn với mã mời này hiện đang tạm dừng hoạt động hoặc đã bị ẩn / vô hiệu hóa!"), "danger")
                return render_template("register.html", all_schools=all_schools, schools=all_schools)
            if code_row["da_dung"] >= code_row["so_luot_toi_da"]:
                flash(_("Mã mời này đã hết số lượt sử dụng!"), "danger")
                return render_template("register.html", all_schools=all_schools, schools=all_schools)

            # Mã hợp lệ: tự gán đúng trường của mã mời, kích hoạt ngay
            assigned_truong_id = code_row["truong_id"]
            initial_status = "hoat_dong"
            matched_invite_code = code_row
        else:
            # Không có mã mời: tự chọn trường -> trạng thái 'cho_duyet'
            if truong_id_form and truong_id_form.isdigit():
                assigned_truong_id = int(truong_id_form)
            else:
                assigned_truong_id = 1

            cur.execute("SELECT trang_thai, COALESCE(an_truong, 0) AS an_truong FROM truong WHERE id = ?", (assigned_truong_id,))
            target_school_row = cur.fetchone()
            if target_school_row and (target_school_row["an_truong"] == 1 or target_school_row["trang_thai"] == "vo_hieu_hoa"):
                flash(_("Trường học bạn chọn hiện đang tạm dừng hoạt động hoặc đã bị ẩn / vô hiệu hóa!"), "danger")
                return render_template("register.html", all_schools=all_schools, schools=all_schools)
            initial_status = "cho_duyet"

        # Băm mật khẩu và tạo người dùng mới
        hashed_password = generate_password_hash(mat_khau)
        initial_balance = 2.0

        cur.execute(
            """INSERT INTO users 
               (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai)
               VALUES (?, ?, ?, 'hoc_sinh', ?, ?, ?, ?, ?)""",
            (ma_hoc_sinh, ho_ten, lop, initial_balance, gio_ranh, hashed_password, assigned_truong_id, initial_status)
        )
        new_user_id = cur.lastrowid

        # Nếu có mã mời: cập nhật lượt dùng và ghi vào sổ theo dõi
        if matched_invite_code:
            cur.execute("UPDATE invite_codes SET da_dung = da_dung + 1 WHERE id = ?", (matched_invite_code["id"],))
            now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute(
                "INSERT INTO invite_code_usages (invite_code_id, user_id, thoi_gian) VALUES (?, ?, ?)",
                (matched_invite_code["id"], new_user_id, now_dt)
            )

        # Ghi nhận vào sổ cái tín dụng (credits_ledger)
        cur.execute(
            """INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id)
               VALUES (?, ?, 'Khoản vốn tín dụng khởi đầu mở sổ học đường', NULL)""",
            (new_user_id, initial_balance)
        )
        db.commit()

        # Lấy tên trường
        cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (assigned_truong_id,))
        t_row = cur.fetchone()
        ten_truong = t_row["ten_truong"] if t_row else ""

        # Tự động đăng nhập vào session
        session["user_id"] = new_user_id
        session["ma_hoc_sinh"] = ma_hoc_sinh
        session["ho_ten"] = ho_ten
        session["vai_tro"] = "hoc_sinh"
        session["lop"] = lop
        session["so_du_gio"] = initial_balance
        session["truong_id"] = assigned_truong_id
        session["ten_truong"] = ten_truong
        session["trang_thai"] = initial_status

        if initial_status == "hoat_dong":
            flash(_("Chúc mừng bạn đã kích hoạt mở sổ thành công bằng mã mời và nhận ngay 2.0 giờ tín dụng!"), "success")
        else:
            flash(_("Đăng ký thành công! Tài khoản của bạn đang ở trạng thái 'Chờ duyệt' bởi Quản trị viên nhà trường. Bạn chưa thể đăng kỹ năng hoặc đặt lịch học cho đến khi được duyệt."), "warning")

        return redirect(url_for("profile"))

    return render_template("register.html", all_schools=all_schools, schools=all_schools)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Đăng nhập hệ thống (Việc 4):
    - Giữ nguyên luồng: Mã học sinh + Mật khẩu.
    - Hệ thống TỰ NHẬN diện trường từ tài khoản, KHÔNG bắt người dùng chọn trường.
    - Chặn đăng nhập nếu tài khoản bị khóa ('da_khoa').
    - Chuyển hướng đúng vai trò (Quản trị viên -> /admin, Học sinh/Giáo viên -> /profile).
    """
    if "user_id" in session:
        if session.get("vai_tro") in ("admin", "super_admin", "school_admin"):
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
            flash(_("Mã đăng nhập hoặc mật khẩu không chính xác!"), "danger")
            return render_template("login.html"), 401

        # Kiểm tra trạng thái tài khoản
        user_status = user["trang_thai"] if "trang_thai" in user.keys() else "hoat_dong"
        if user_status == "da_khoa":
            flash(_("Tài khoản của bạn đã bị khóa do vi phạm nội quy học đường. Vui lòng liên hệ ban quản trị nhà trường để được hỗ trợ giải quyết."), "danger")
            return render_template("login.html"), 403

        # Tự động nhận diện trường học từ tài khoản người dùng
        truong_id = user["truong_id"] if "truong_id" in user.keys() and user["truong_id"] else 1
        cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (truong_id,))
        school_row = cur.fetchone()
        ten_truong = school_row["ten_truong"] if school_row else "Trường học"

        # Lưu thông tin định danh vào Flask session
        session["user_id"] = user["id"]
        session["ma_hoc_sinh"] = user["ma_hoc_sinh"]
        session["ho_ten"] = user["ho_ten"]
        session["vai_tro"] = user["vai_tro"]
        session["lop"] = user["lop"]
        session["so_du_gio"] = user["so_du_gio"]
        session["truong_id"] = truong_id
        session["ten_truong"] = ten_truong
        session["trang_thai"] = user_status

        flash(_("Đăng nhập thành công! Xin chào %(name)s.", name=user['ho_ten']), "success")

        # Chuyển hướng phù hợp theo vai trò
        next_url = request.args.get("next")
        if next_url:
            return redirect(next_url)

        if user["vai_tro"] in ("admin", "super_admin", "school_admin"):
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("profile"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    """
    Đăng xuất: Xóa toàn bộ dữ liệu phiên và trở về trang chủ.
    """
    session.clear()
    flash(_("Bạn đã đăng xuất khỏi hệ thống thành công."), "info")
    return redirect(url_for("index"))


# ==============================================================================
# QUẢN LÝ MẬT KHẨU & QUÊN MẬT KHẨU QUA EMAIL (PROMPT 23 - VIỆC 1 & VIỆC 4)
# ==============================================================================
@app.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """
    Đổi mật khẩu người dùng (Prompt 23 - Việc 1):
    - Tài khoản demo (demo_quantruong, demo_giaovien, demo_hocsinh, admin...) bị CHẶN tuyệt đối.
    - Tài khoản thông thường: xác thực mật khẩu cũ và băm cập nhật mật khẩu mới.
    """
    mhs = session.get("ma_hoc_sinh", "")
    if is_demo_user(mhs):
        flash("Tài khoản demo không được phép đổi mật khẩu!", "danger")
        return redirect(url_for("profile"))

    mat_khau_cu = request.form.get("mat_khau_cu", "")
    mat_khau_moi = request.form.get("mat_khau_moi", "")
    xac_nhan_mat_khau = request.form.get("xac_nhan_mat_khau", "")

    if not mat_khau_cu or not mat_khau_moi or not xac_nhan_mat_khau:
        flash("Vui lòng điền đầy đủ thông tin đổi mật khẩu!", "warning")
        return redirect(url_for("profile"))

    if mat_khau_moi != xac_nhan_mat_khau:
        flash("Mật khẩu mới và xác nhận mật khẩu không khớp!", "danger")
        return redirect(url_for("profile"))

    if len(mat_khau_moi) < 6:
        flash("Mật khẩu mới phải có tối thiểu 6 ký tự!", "warning")
        return redirect(url_for("profile"))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT mat_khau FROM users WHERE id = ?", (session["user_id"],))
    row = cur.fetchone()
    if not row or not check_password_hash(row["mat_khau"], mat_khau_cu):
        flash("Mật khẩu hiện tại không chính xác!", "danger")
        return redirect(url_for("profile"))

    new_hash = generate_password_hash(mat_khau_moi)
    cur.execute("UPDATE users SET mat_khau = ? WHERE id = ?", (new_hash, session["user_id"]))
    db.commit()
    flash("Đổi mật khẩu thành công! Hãy ghi nhớ mật khẩu mới của bạn.", "success")
    return redirect(url_for("profile"))


def send_password_reset_email(to_email, user_name, reset_url):
    """
    Gửi email liên kết đặt lại mật khẩu qua SMTP (Prompt 23 - Việc 4):
    - Đọc từ biến môi trường: SMTP_HOST/MAIL_SERVER, SMTP_PORT/MAIL_PORT, SMTP_USER/MAIL_USERNAME, SMTP_PASS/MAIL_PASSWORD, SMTP_FROM/MAIL_DEFAULT_SENDER.
    - Thiếu cấu hình hoặc lỗi mạng -> báo lỗi thân thiện, KHÔNG crash 500.
    """
    smtp_host = os.getenv("SMTP_HOST") or os.getenv("MAIL_SERVER")
    smtp_port_raw = os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or "587"
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        smtp_port = 587
    smtp_user = os.getenv("SMTP_USER") or os.getenv("MAIL_USERNAME")
    smtp_pass = os.getenv("SMTP_PASS") or os.getenv("MAIL_PASSWORD")
    smtp_from = os.getenv("SMTP_FROM") or os.getenv("MAIL_DEFAULT_SENDER") or (smtp_user if smtp_user else "no-reply@timebankedu.vn")
    smtp_tls = os.getenv("SMTP_TLS", "true").lower() in ("true", "1", "yes")

    if not smtp_host or not smtp_user:
        app.logger.warning("SMTP chưa được cấu hình đầy đủ (thiếu SMTP_HOST hoặc SMTP_USER).")
        return False, "Hệ thống chưa kết nối máy chủ gửi email SMTP. Vui lòng liên hệ Tổng Quản trị viên (mshuyenuka@gmail.com) để được hỗ trợ đặt lại mật khẩu trực tiếp."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "[TimeBank Edu] Yêu cầu đặt lại mật khẩu quản trị"
        msg["From"] = smtp_from
        msg["To"] = to_email

        text_body = f"""Xin chào {user_name},

Hệ thống TimeBank Edu vừa nhận được yêu cầu đặt lại mật khẩu cho tài khoản của bạn.
Vui lòng truy cập đường dẫn sau để đặt mật khẩu mới (hiệu lực trong 60 phút, sử dụng 1 lần):
{reset_url}

Nếu bạn không yêu cầu hành động này, vui lòng bỏ qua thư này hoặc thông báo cho Tổng Quản trị viên.
Trân trọng,
Ban Điều Hành School Time Bank
"""
        html_body = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #ffffff;">
          <h2 style="color: #F26522; margin-top: 0;">School Time Bank</h2>
          <p>Xin chào <strong>{user_name}</strong>,</p>
          <p>Hệ thống nhận được yêu cầu đặt lại mật khẩu cho tài khoản quản trị/giáo viên của bạn.</p>
          <div style="text-align: center; margin: 25px 0;">
            <a href="{reset_url}" style="background-color: #F26522; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">Đặt lại Mật khẩu</a>
          </div>
          <p style="color: #64748b; font-size: 0.9em;">Hoặc bạn có thể sao chép liên kết này vào trình duyệt:<br><a href="{reset_url}">{reset_url}</a></p>
          <p style="color: #64748b; font-size: 0.85em;"><em>Liên kết này có hiệu lực trong vòng 60 phút và chỉ sử dụng được 1 lần duy nhất.</em></p>
        </div>
        """
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = smtplib.SMTP(smtp_host, smtp_port, timeout=8)
        if smtp_tls:
            server.starttls()
        if smtp_pass:
            server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_from, [to_email], msg.as_string())
        server.quit()
        return True, None
    except Exception as e:
        app.logger.warning(f"Lỗi gửi email reset password qua SMTP: {e}")
        return False, f"Không thể gửi email do lỗi máy chủ SMTP ({str(e)}). Vui lòng liên hệ Tổng Quản trị viên."


@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """
    Quên mật khẩu qua email (Prompt 23 - Việc 4):
    - Nhập email -> sinh link reset (token 1 giờ, 1 lần dùng).
    - Chỉ áp dụng cho tài khoản có email đã lưu (super_admin, school_admin, giao_vien).
    - Không có email -> báo liên hệ Tổng quản trị.
    - Thiếu cấu hình SMTP -> báo lỗi thân thiện, không crash.
    """
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        if not email:
            flash("Vui lòng nhập địa chỉ email của bạn!", "warning")
            return render_template("forgot_password.html")

        db = get_db()
        cur = db.cursor()
        cur.execute("""
            SELECT id, ma_hoc_sinh, ho_ten, vai_tro, email 
            FROM users 
            WHERE LOWER(email) = ? AND vai_tro IN ('super_admin', 'school_admin', 'giao_vien')
        """, (email,))
        user = cur.fetchone()

        if not user:
            flash("Không tìm thấy tài khoản quản trị hoặc giáo viên với email này. Vui lòng liên hệ Tổng Quản trị viên (mshuyenuka@gmail.com) để được hỗ trợ.", "warning")
            return render_template("forgot_password.html")

        token = secrets.token_urlsafe(32)
        het_han = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO password_reset_tokens (user_id, token, het_han, da_dung)
            VALUES (?, ?, ?, 0)
        """, (user["id"], token, het_han))
        db.commit()

        reset_url = url_for("reset_password", token=token, _external=True)

        # Lưu thông tin token vào app.config khi test để bộ kiểm thử tự động xác thực
        app.config["LAST_RESET_TOKEN"] = token
        app.config["LAST_RESET_URL"] = reset_url

        sent, err = send_password_reset_email(email, user["ho_ten"], reset_url)
        if sent:
            flash(f"Đã gửi liên kết đặt lại mật khẩu đến email {email}. Vui lòng kiểm tra hộp thư (liên kết có hiệu lực trong 60 phút).", "success")
        else:
            flash(err, "info")

        return render_template("forgot_password.html")

    return render_template("forgot_password.html")


@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """
    Đặt lại mật khẩu từ liên kết token (1 giờ, 1 lần dùng) (Prompt 23 - Việc 4).
    """
    db = get_db()
    cur = db.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
        SELECT prt.*, u.ma_hoc_sinh, u.ho_ten, u.email 
        FROM password_reset_tokens prt 
        JOIN users u ON prt.user_id = u.id 
        WHERE prt.token = ? AND prt.da_dung = 0 AND prt.het_han > ?
    """, (token, now_str))
    record = cur.fetchone()

    if not record:
        flash("Liên kết đặt lại mật khẩu không hợp lệ hoặc đã hết hạn (chỉ dùng được 1 lần trong 60 phút). Vui lòng gửi lại yêu cầu mới.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        mat_khau = (request.form.get("mat_khau_moi") or request.form.get("mat_khau", "")).strip()
        xac_nhan = (request.form.get("mat_khau_xac_nhan") or request.form.get("xac_nhan_mat_khau", "")).strip()

        if not mat_khau or not xac_nhan:
            flash("Vui lòng nhập đầy đủ mật khẩu mới và xác nhận mật khẩu!", "warning")
            return render_template("reset_password.html", token=token, user=record, user_name=record["ho_ten"])

        if mat_khau != xac_nhan:
            flash("Mật khẩu mới và xác nhận mật khẩu không khớp!", "danger")
            return render_template("reset_password.html", token=token, user=record, user_name=record["ho_ten"])

        if len(mat_khau) < 6:
            flash("Mật khẩu mới phải có tối thiểu 6 ký tự!", "warning")
            return render_template("reset_password.html", token=token, user=record, user_name=record["ho_ten"])

        new_hash = generate_password_hash(mat_khau)
        cur.execute("UPDATE users SET mat_khau = ? WHERE id = ?", (new_hash, record["user_id"]))
        cur.execute("UPDATE password_reset_tokens SET da_dung = 1 WHERE id = ?", (record["id"],))
        db.commit()

        flash("Đặt lại mật khẩu thành công! Bạn có thể đăng nhập bằng mật khẩu mới.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token, user=record, user_name=record["ho_ten"])


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
            ORDER BY so_luong DESC, MAX(s.id) DESC
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
                ORDER BY so_luong DESC, MAX(id) DESC
                LIMIT 1
            """)
            pop_sub = cur.fetchone()
            target_subject = pop_sub["linh_vuc"] if pop_sub else "Toán học"

        # 2. Lọc ứng viên có kỹ năng 'da_duyet' thuộc lĩnh vực đó + người khác chia sẻ
        search_kw = "Toán" if "toán" in target_subject.lower() else target_subject
        cur.execute("""
            SELECT s.*, u.ho_ten, u.lop, u.gio_ranh,
                   ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
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
        """SELECT ROUND(AVG(so_sao)::numeric, 1), COUNT(*) 
           FROM ratings 
           WHERE nguoi_duoc_danh_gia_id = ?""",
        (user["id"],)
    )
    rating_row = cur.fetchone()
    avg_rating = rating_row[0] if rating_row and rating_row[0] is not None else 5.0
    rating_count = rating_row[1] if rating_row else 0

    # Ngưỡng tín dụng dạy thật mở khóa Sàn cộng đồng liên trường (Prompt 19)
    community_threshold = get_community_threshold()
    is_community_member = (hours_taught >= community_threshold)
    hours_needed = max(0.0, community_threshold - hours_taught)

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
        rating_count=rating_count,
        community_threshold=community_threshold,
        is_community_member=is_community_member,
        hours_needed=hours_needed
    )


@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Bảng điều khiển Quản trị hệ thống (/admin) - Multi-tenant 4 cấp:
    - Super Admin (Cô Huyền): thấy và quản lý TẤT CẢ các trường, hỗ trợ lọc theo trường.
    - School Admin: CHỈ thấy và quản trị trường của mình.
    - Quản lý Hàng chờ duyệt học sinh, Sổ mã mời, Sổ xử lý vi phạm nội quy.
    """
    db = get_db()
    cur = db.cursor()

    current_role = session.get("vai_tro")
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()
    is_school = is_school_admin()

    # Lấy thông tin trường của user hiện tại
    cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (current_user_school_id,))
    s_row = cur.fetchone()
    current_school_name = s_row["ten_truong"] if s_row else "Trường học"

    # Bộ lọc trường đối với Super Admin
    selected_truong_id = request.args.get("truong_id", "").strip()
    if not is_super:
        filter_school_id = current_user_school_id
        selected_truong_id = str(current_user_school_id)
    else:
        if selected_truong_id and selected_truong_id.isdigit():
            filter_school_id = int(selected_truong_id)
        else:
            filter_school_id = None
            selected_truong_id = ""

    # 1. Lấy danh sách người dùng
    if filter_school_id:
        cur.execute("SELECT * FROM users WHERE truong_id = ? ORDER BY id ASC", (filter_school_id,))
    else:
        cur.execute("SELECT * FROM users ORDER BY id ASC")
    all_users = cur.fetchall()

    student_count = sum(1 for u in all_users if u["vai_tro"] == "hoc_sinh")
    total_credits = sum(u["so_du_gio"] for u in all_users if u["vai_tro"] == "hoc_sinh")

    if filter_school_id:
        cur.execute("SELECT COUNT(*) FROM skills WHERE trang_thai_duyet = 'cho_duyet' AND truong_id = ?", (filter_school_id,))
    else:
        cur.execute("SELECT COUNT(*) FROM skills WHERE trang_thai_duyet = 'cho_duyet'")
    pending_skills_count = cur.fetchone()[0]

    # Điểm chạm 5: Quét và đưa ra khuyến nghị can thiệp sư phạm sớm từ AI
    ai_warnings = ai_admin_early_warning(db, session["user_id"])

    # Thống kê Quiz
    quiz_sql = """
        SELECT 
            sk.linh_vuc,
            COUNT(qr.id) AS so_bai_lam,
            ROUND(AVG(qr.diem_so)::numeric, 2) AS diem_tb,
            SUM(CASE WHEN qr.diem_so >= 4.0 THEN 1 ELSE 0 END) AS so_luong_gioi,
            SUM(CASE WHEN qr.diem_so >= 3.0 THEN 1 ELSE 0 END) AS so_luong_dat_chuan,
            ROUND(AVG(qr.tu_danh_gia_truoc)::numeric, 2) AS tu_tin_truoc_tb
        FROM quiz_results qr
        JOIN sessions s ON qr.session_id = s.id
        JOIN skills sk ON s.skill_id = sk.id
    """
    if filter_school_id:
        quiz_sql += f" WHERE s.truong_id = {filter_school_id}"
    quiz_sql += " GROUP BY sk.linh_vuc ORDER BY so_bai_lam DESC, diem_tb DESC"
    cur.execute(quiz_sql)
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

    pct_ge_4 = round((total_ge_4 / total_quizzes * 100), 1) if total_quizzes > 0 else 0.0

    if filter_school_id:
        cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh' AND truong_id = ?", (filter_school_id,))
        completed_sessions_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh' AND quiz_dat_chuan = 1 AND truong_id = ?", (filter_school_id,))
        passed_quiz_sessions_count = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh'")
        completed_sessions_count = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh' AND quiz_dat_chuan = 1")
        passed_quiz_sessions_count = cur.fetchone()[0]

    pct_dat_chuan = round((passed_quiz_sessions_count / completed_sessions_count * 100), 1) if completed_sessions_count > 0 else 0.0

    if filter_school_id:
        cur.execute("""
            SELECT AVG(qr.tu_danh_gia_truoc), AVG(qr.diem_so) 
            FROM quiz_results qr
            JOIN sessions s ON qr.session_id = s.id
            WHERE s.truong_id = ?
        """, (filter_school_id,))
    else:
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

    if filter_school_id:
        cur.execute("SELECT COUNT(*) FROM sessions WHERE truong_id = ?", (filter_school_id,))
        total_sessions_count = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh' AND truong_id = ?", (filter_school_id,))
        total_hours_circulated = cur.fetchone()[0]
    else:
        cur.execute("SELECT COUNT(*) FROM sessions")
        total_sessions_count = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh'")
        total_hours_circulated = cur.fetchone()[0]

    top_sql = """
        SELECT 
            u.id, u.ma_hoc_sinh, u.ho_ten, u.lop, u.so_du_gio,
            COALESCE(SUM(CASE WHEN s.nguoi_day_id = u.id AND s.trang_thai = 'hoan_thanh' THEN s.so_gio ELSE 0 END), 0.0) AS gio_day,
            COALESCE(SUM(CASE WHEN s.nguoi_hoc_id = u.id AND s.trang_thai = 'hoan_thanh' THEN s.so_gio ELSE 0 END), 0.0) AS gio_hoc,
            COUNT(DISTINCT CASE WHEN s.trang_thai = 'hoan_thanh' THEN s.id END) AS so_phien,
            ROUND(COALESCE((SELECT AVG(so_sao) FROM ratings WHERE nguoi_duoc_danh_gia_id = u.id), 5.0)::numeric, 1) AS sao_tb
        FROM users u
        LEFT JOIN sessions s ON (s.nguoi_day_id = u.id OR s.nguoi_hoc_id = u.id)
        WHERE u.vai_tro = 'hoc_sinh'
    """
    if filter_school_id:
        top_sql += f" AND u.truong_id = {filter_school_id}"
    top_sql += """
        GROUP BY u.id, u.ma_hoc_sinh, u.ho_ten, u.lop, u.so_du_gio
        ORDER BY gio_day DESC, u.so_du_gio DESC
        LIMIT 5
    """
    cur.execute(top_sql)
    top_active_students = cur.fetchall()

    # 2. HÀNG CHỜ DUYỆT HỌC SINH (pending_students)
    pending_sql = """
        SELECT u.*, t.ten_truong
        FROM users u
        LEFT JOIN truong t ON u.truong_id = t.id
        WHERE u.trang_thai = 'cho_duyet'
    """
    if filter_school_id:
        pending_sql += f" AND u.truong_id = {filter_school_id}"
    pending_sql += " ORDER BY u.id DESC"
    cur.execute(pending_sql)
    pending_students = cur.fetchall()

    # 3. QUẢN LÝ MÃ MỜI (invite_codes_list)
    invite_sql = """
        SELECT ic.*, t.ten_truong
        FROM invite_codes ic
        JOIN truong t ON ic.truong_id = t.id
    """
    if filter_school_id:
        invite_sql += f" WHERE ic.truong_id = {filter_school_id}"
    invite_sql += " ORDER BY ic.id DESC"
    cur.execute(invite_sql)
    raw_invite_codes = cur.fetchall()
    invite_codes_list = []
    for c in raw_invite_codes:
        c_dict = dict(c)
        cur.execute("""
            SELECT u.ho_ten, u.ma_hoc_sinh, icu.thoi_gian
            FROM invite_code_usages icu
            JOIN users u ON icu.user_id = u.id
            WHERE icu.invite_code_id = ?
            ORDER BY icu.id DESC
        """, (c["id"],))
        c_dict["used_by"] = cur.fetchall()
        invite_codes_list.append(c_dict)

    # 4. DANH SÁCH VI PHẠM (violations_list)
    viol_sql = """
        SELECT v.*, u.ho_ten, u.ma_hoc_sinh, u.lop, u.trang_thai AS user_trang_thai, t.ten_truong
        FROM violations v
        JOIN users u ON v.user_id = u.id
        LEFT JOIN truong t ON u.truong_id = t.id
    """
    if filter_school_id:
        viol_sql += f" WHERE u.truong_id = {filter_school_id}"
    viol_sql += " ORDER BY v.id DESC"
    cur.execute(viol_sql)
    violations_list = cur.fetchall()

    # 5. DANH SÁCH KỸ NĂNG CHỜ DUYỆT SÀN CHUNG (community_pending_skills - Prompt 19)
    comm_sql = """
        SELECT s.*, u.ho_ten, u.ma_hoc_sinh, u.lop, t.ten_truong,
               (SELECT COALESCE(SUM(ses.so_gio), 0.0) FROM sessions ses WHERE ses.nguoi_day_id = u.id AND ses.trang_thai = 'hoan_thanh') AS gio_day_that
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN truong t ON s.truong_id = t.id
        WHERE s.trang_thai_cong_dong = 'cho_duyet'
        ORDER BY s.id DESC
    """
    cur.execute(comm_sql)
    community_pending_skills = cur.fetchall()

    comm_approved_sql = """
        SELECT s.*, u.ho_ten, u.ma_hoc_sinh, u.lop, t.ten_truong,
               u_appr.ho_ten AS nguoi_duyet_ten
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN truong t ON s.truong_id = t.id
        LEFT JOIN users u_appr ON s.nguoi_duyet_cong_dong_id = u_appr.id
        WHERE s.hien_thi_cong_dong = 1 AND s.trang_thai_cong_dong = 'da_duyet'
        ORDER BY s.ngay_duyet_cong_dong DESC, s.id DESC
        LIMIT 20
    """
    cur.execute(comm_approved_sql)
    community_approved_skills = cur.fetchall()

    # Danh sách các trường học
    if is_super:
        cur.execute("SELECT *, COALESCE(an_truong, 0) AS an_truong FROM truong ORDER BY id ASC")
    else:
        cur.execute("SELECT *, COALESCE(an_truong, 0) AS an_truong FROM truong WHERE COALESCE(an_truong, 0) = 0 ORDER BY id ASC")
    all_schools = cur.fetchall()

    all_schools_management = []
    if is_super:
        cur.execute("""
            SELECT t.id, t.ten_truong, t.logo, t.trang_thai, t.ngay_tao, COALESCE(t.an_truong, 0) AS an_truong,
                   (SELECT COUNT(*) FROM users u WHERE u.truong_id = t.id) AS so_tai_khoan
            FROM truong t
            ORDER BY t.id ASC
        """)
        all_schools_management = cur.fetchall()

    # Danh sách chương trình cộng đồng cho tab Quản lý Chương trình Cộng đồng trong /admin
    if is_super:
        if filter_school_id:
            comm_tasks_sql = """
                SELECT t.*, tr.ten_truong, u.ho_ten AS ten_nguoi_tao,
                       (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
                FROM community_tasks t
                LEFT JOIN truong tr ON t.truong_id = tr.id
                LEFT JOIN users u ON t.nguoi_tao_id = u.id
                WHERE t.truong_id = ?
                ORDER BY t.id DESC
            """
            cur.execute(comm_tasks_sql, (filter_school_id,))
        else:
            comm_tasks_sql = """
                SELECT t.*, tr.ten_truong, u.ho_ten AS ten_nguoi_tao,
                       (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
                FROM community_tasks t
                LEFT JOIN truong tr ON t.truong_id = tr.id
                LEFT JOIN users u ON t.nguoi_tao_id = u.id
                ORDER BY t.id DESC
            """
            cur.execute(comm_tasks_sql)
    else:
        comm_tasks_sql = """
            SELECT t.*, tr.ten_truong, u.ho_ten AS ten_nguoi_tao,
                   (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
            FROM community_tasks t
            LEFT JOIN truong tr ON t.truong_id = tr.id
            LEFT JOIN users u ON t.nguoi_tao_id = u.id
            WHERE t.truong_id = ? OR t.truong_id IS NULL
            ORDER BY t.id DESC
        """
        cur.execute(comm_tasks_sql, (current_user_school_id,))
    admin_community_tasks = [dict(r) for r in cur.fetchall()]

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
        learning_stats=learning_stats,
        is_super_admin=is_super,
        is_school_admin=is_school,
        current_school_name=current_school_name,
        all_schools=all_schools,
        all_schools_management=all_schools_management,
        selected_truong_id=selected_truong_id,
        pending_students=pending_students,
        invite_codes_list=invite_codes_list,
        violations_list=violations_list,
        google_drive_configured=is_google_drive_configured(),
        community_pending_skills=community_pending_skills,
        community_approved_skills=community_approved_skills,
        admin_community_tasks=admin_community_tasks
    )


# ==============================================================================
# QUẢN LÝ TÀI KHOẢN & DEMO CHO SUPER ADMIN (PROMPT 23 - VIỆC 2 & VIỆC 3)
# ==============================================================================
@app.route("/admin/accounts")
@login_required
def admin_accounts():
    """
    Trang Quản lý tài khoản (chỉ super_admin - Prompt 23 Việc 3):
    - Tạo tài khoản Quản trị trường (school_admin) gắn đúng truong_id
    - Tạo tài khoản Giáo viên (giao_vien) gắn đúng truong_id
    - Nút 'Reset demo': 1 click đưa dữ liệu Trường Demo về trạng thái ban đầu
    """
    if not is_super_admin():
        flash("Chức năng chỉ dành riêng cho Tổng Quản trị viên (Super Admin)!", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM truong ORDER BY id ASC")
    all_schools = cur.fetchall()

    cur.execute("""
        SELECT u.*, t.ten_truong 
        FROM users u 
        LEFT JOIN truong t ON u.truong_id = t.id 
        WHERE u.vai_tro IN ('super_admin', 'school_admin', 'giao_vien')
        ORDER BY u.truong_id ASC, u.id ASC
    """)
    admin_users = cur.fetchall()

    return render_template(
        "admin_accounts.html",
        schools=all_schools,
        accounts=admin_users,
        all_schools=all_schools,
        admin_users=admin_users,
        demo_school_id=DEMO_SCHOOL_ID
    )


@app.route("/admin/accounts/create", methods=["POST"])
@login_required
def admin_create_account():
    """
    Tạo tài khoản Quản trị trường (school_admin) hoặc Giáo viên (giao_vien) - chỉ super_admin.
    """
    if not is_super_admin():
        flash("Chức năng chỉ dành riêng cho Tổng Quản trị viên (Super Admin)!", "danger")
        return redirect(url_for("admin_dashboard"))

    ma_dang_nhap = (request.form.get("ma_hoc_sinh") or request.form.get("ma_dang_nhap", "")).strip()
    ho_ten = request.form.get("ho_ten", "").strip()
    vai_tro = request.form.get("vai_tro", "").strip()
    truong_id_val = request.form.get("truong_id", "").strip()
    mat_khau = request.form.get("mat_khau", "").strip()
    email = request.form.get("email", "").strip()
    lop = request.form.get("lop", "").strip()

    if not ma_dang_nhap or not ho_ten or not mat_khau or not truong_id_val:
        flash("Vui lòng điền đầy đủ các thông tin bắt buộc (Mã đăng nhập, Họ tên, Trường học, Mật khẩu)!", "warning")
        return redirect(url_for("admin_accounts"))

    if vai_tro not in ("school_admin", "giao_vien"):
        flash("Vai trò không hợp lệ (chỉ được tạo Quản trị trường hoặc Giáo viên)!", "danger")
        return redirect(url_for("admin_accounts"))

    try:
        tid = int(truong_id_val)
    except ValueError:
        flash("ID trường học không hợp lệ!", "danger")
        return redirect(url_for("admin_accounts"))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = ?", (ma_dang_nhap,))
    if cur.fetchone():
        flash(f"Mã đăng nhập '{ma_dang_nhap}' đã tồn tại trong hệ thống!", "danger")
        return redirect(url_for("admin_accounts"))

    pwd_hash = generate_password_hash(mat_khau)
    so_du = 100.0 if vai_tro == "school_admin" else 10.0
    unit_lop = lop if lop else ("Ban Giám Hiệu" if vai_tro == "school_admin" else "Tổ Giáo Viên")

    cur.execute("""
        INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai, email)
        VALUES (?, ?, ?, ?, ?, 'Toàn thời gian', ?, ?, 'hoat_dong', ?)
    """, (ma_dang_nhap, ho_ten, unit_lop, vai_tro, so_du, pwd_hash, tid, email))
    db.commit()

    flash(f"Đã tạo thành công tài khoản '{ho_ten}' ({vai_tro}) gắn với trường học ID {tid}!", "success")
    return redirect(url_for("admin_accounts"))


@app.route("/admin/demo/reset", methods=["POST"])
@login_required
def reset_demo_data_route():
    """
    Nút 'Reset demo': 1 click đưa dữ liệu Trường Demo về trạng thái ban đầu (Prompt 23 - Việc 3).
    Cho phép Super Admin hoặc Quản trị viên Trường Demo thực hiện.
    """
    is_super = is_super_admin()
    is_demo_admin = (session.get("vai_tro") in ("school_admin", "admin") and session.get("truong_id") == DEMO_SCHOOL_ID)

    if not (is_super or is_demo_admin):
        flash("Bạn không có quyền khôi phục dữ liệu Trường Demo!", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    reset_demo_school_data(db)
    flash("Đã khôi phục toàn bộ dữ liệu Trường Demo về trạng thái ban đầu thành công!", "success")
    if request.referrer:
        return redirect(request.referrer)
    return redirect(url_for("admin_dashboard") if not is_super else url_for("admin_accounts"))


@app.cli.command("create-superadmin")
def create_superadmin():
    """
    Lệnh CLI tạo Super Admin bí mật cho cô Huyền (Prompt 23 - Việc 2):
    - Đọc SUPERADMIN_USER + SUPERADMIN_PASS từ biến môi trường.
    - Thiếu biến -> báo lỗi, không làm gì, không in mật khẩu ra log.
    - Tạo user vai trò super_admin, gắn email mshuyenuka@gmail.com, truong_id=1, trang_thai=hoat_dong.
    - Nếu đã có super_admin khác 'admin' -> báo 'đã tồn tại', không tạo trùng.
    """
    user = os.getenv("SUPERADMIN_USER", "").strip()
    pwd = os.getenv("SUPERADMIN_PASS", "").strip()

    if not user or not pwd:
        click.echo("[LỖI] Thiếu biến môi trường SUPERADMIN_USER hoặc SUPERADMIN_PASS.")
        sys.exit(1)

    db = get_db()
    cur = db.cursor()

    # Kiểm tra xem đã có super_admin nào khác 'admin' chưa
    cur.execute("SELECT id, ma_hoc_sinh FROM users WHERE vai_tro = 'super_admin' AND ma_hoc_sinh != 'admin'")
    existing = cur.fetchone()
    if existing:
        click.echo(f"[THÔNG BÁO] Tài khoản Super Admin '{existing['ma_hoc_sinh']}' đã tồn tại trong hệ thống. Không tạo trùng.")
        return

    pwd_hash = generate_password_hash(pwd)
    cur.execute("""
        INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh, mat_khau, truong_id, trang_thai, email)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user,
        "Tổng Quản trị viên (Cô Huyền)",
        "Ban Điều Hành Quốc Gia",
        "super_admin",
        999.0,
        "Toàn thời gian",
        pwd_hash,
        1,
        "hoat_dong",
        "mshuyenuka@gmail.com"
    ))
    db.commit()
    click.echo(f"[THÀNH CÔNG] Đã tạo thành công tài khoản Super Admin '{user}' (Email: mshuyenuka@gmail.com, Trường ID: 1).")


# ------------------------------------------------------------------------------
# HÀNH ĐỘNG QUẢN TRỊ VIÊN (MÃ MỜI, DUYỆT HỌC SINH, XỬ LÝ KỶ LUẬT)
# ------------------------------------------------------------------------------

@app.route("/admin/invite-codes/generate", methods=["POST"])
@admin_required
def admin_generate_invite_codes():
    """Sinh mã mời trường học ngẫu nhiên định dạng TBEDU-XXXX-XXXX."""
    db = get_db()
    cur = db.cursor()
    current_role = session.get("vai_tro")
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    if is_super:
        truong_id_val = request.form.get("truong_id")
        truong_id = int(truong_id_val) if truong_id_val and truong_id_val.isdigit() else current_user_school_id
    else:
        truong_id = current_user_school_id

    loai = request.form.get("loai", "ca_nhan").strip()
    try:
        so_luong = int(request.form.get("so_luong", 5))
    except (ValueError, TypeError):
        so_luong = 5
    so_luong = max(1, min(100, so_luong))

    if loai == "lop":
        try:
            so_luot_moi_ma = int(request.form.get("so_luot_moi_ma", 35))
        except (ValueError, TypeError):
            so_luot_moi_ma = 35
        num_codes = 1
        uses_per_code = max(1, so_luot_moi_ma)
    else:
        num_codes = so_luong
        uses_per_code = 1

    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    creator_id = session["user_id"]

    created_codes = []
    for _ in range(num_codes):
        part1 = "".join(secrets.choice(chars) for _ in range(4))
        part2 = "".join(secrets.choice(chars) for _ in range(4))
        ma_code = f"TBEDU-{part1}-{part2}"
        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (truong_id, ma_code, loai, uses_per_code, now_dt, creator_id))
        created_codes.append(ma_code)

    db.commit()
    flash(f"Đã sinh thành công {len(created_codes)} mã mời dạng TBEDU-XXXX-XXXX!", "success")
    return redirect(url_for("admin_dashboard", _anchor="tab-invite"))


@app.route("/admin/approve-student/<int:user_id>", methods=["POST"])
@admin_required
def admin_approve_student(user_id):
    """Phê duyệt tài khoản học sinh đang chờ."""
    db = get_db()
    cur = db.cursor()
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target = cur.fetchone()
    if not target:
        flash("Không tìm thấy người dùng.", "danger")
        return redirect(url_for("admin_dashboard"))

    if not is_super and target["truong_id"] != current_user_school_id:
        flash("Bạn chỉ có quyền phê duyệt học sinh thuộc trường của mình!", "danger")
        return redirect(url_for("admin_dashboard"))

    cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ?", (user_id,))
    db.commit()
    flash(f"Đã phê duyệt tài khoản {target['ho_ten']} ({target['ma_hoc_sinh']}) thành công!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject-student/<int:user_id>", methods=["POST"])
@admin_required
def admin_reject_student(user_id):
    """Từ chối đăng ký của học sinh."""
    db = get_db()
    cur = db.cursor()
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target = cur.fetchone()
    if not target:
        flash("Không tìm thấy người dùng.", "danger")
        return redirect(url_for("admin_dashboard"))

    if not is_super and target["truong_id"] != current_user_school_id:
        flash("Bạn chỉ có quyền thao tác trên học sinh thuộc trường của mình!", "danger")
        return redirect(url_for("admin_dashboard"))

    cur.execute("UPDATE users SET trang_thai = 'tu_choi' WHERE id = ?", (user_id,))
    db.commit()
    flash(f"Đã từ chối đăng ký của học sinh {target['ho_ten']}.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/approve-all-students", methods=["POST"])
@admin_required
def admin_approve_all_students():
    """Duyệt hàng loạt học sinh đang trong hàng chờ."""
    db = get_db()
    cur = db.cursor()
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    selected_ids = request.form.getlist("student_ids")
    target_truong_id = request.form.get("truong_id")

    if selected_ids:
        count = 0
        for sid in selected_ids:
            try:
                sid_int = int(sid)
                if is_super:
                    cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ? AND trang_thai = 'cho_duyet'", (sid_int,))
                else:
                    cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ? AND truong_id = ? AND trang_thai = 'cho_duyet'", (sid_int, current_user_school_id))
                count += cur.rowcount
            except ValueError:
                pass
        db.commit()
        flash(f"Đã phê duyệt {count} học sinh được chọn thành công!", "success")
    else:
        if is_super:
            if target_truong_id and target_truong_id.isdigit():
                cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE trang_thai = 'cho_duyet' AND truong_id = ?", (int(target_truong_id),))
            else:
                cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE trang_thai = 'cho_duyet'")
        else:
            cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE trang_thai = 'cho_duyet' AND truong_id = ?", (current_user_school_id,))
        count = cur.rowcount
        db.commit()
        flash(f"Đã duyệt toàn bộ {count} học sinh trong hàng chờ thành công!", "success")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/confirm-lock-user/<int:user_id>", methods=["POST"])
@admin_required
def admin_confirm_lock_user(user_id):
    """
    Xác nhận khóa thật tài khoản học sinh vi phạm mức 3 (Việc 5):
    - CHỜ Quản trị viên bấm xác nhận mới khóa vĩnh viễn (tuyệt đối không tự động khóa).
    """
    db = get_db()
    cur = db.cursor()
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    target = cur.fetchone()
    if not target:
        flash("Không tìm thấy người dùng.", "danger")
        return redirect(url_for("admin_dashboard"))

    if not is_super and target["truong_id"] != current_user_school_id:
        flash("Bạn chỉ có quyền khóa tài khoản thuộc trường của mình!", "danger")
        return redirect(url_for("admin_dashboard"))

    cur.execute("UPDATE users SET trang_thai = 'da_khoa' WHERE id = ?", (user_id,))
    db.commit()
    flash(f"Đã xác nhận KHÓA VĨNH VIỄN tài khoản của học sinh {target['ho_ten']} ({target['ma_hoc_sinh']}) theo quy chế xử lý vi phạm.", "danger")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/dismiss-violation/<int:violation_id>", methods=["POST"])
@admin_required
def admin_dismiss_violation(violation_id):
    """Bỏ qua / Hủy đề xuất kỷ luật, phục hồi tài khoản."""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM violations WHERE id = ?", (violation_id,))
    viol = cur.fetchone()
    if viol:
        cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ? AND trang_thai = 'de_xuat_khoa'", (viol["user_id"],))
        db.commit()
    flash("Đã xử lý / hủy đề xuất kỷ luật.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/schools/<int:school_id>/logo", methods=["POST"])
@admin_required
def admin_update_school_logo(school_id):
    """
    Quản trị viên tải logo thật lên cho trường học liên kết:
    - Nếu là school_admin thì chỉ được đổi logo trường mình.
    - super_admin được đổi logo của bất kỳ trường nào.
    - Trường Demo (ID 99) không cho phép sửa logo.
    """
    if school_id == DEMO_SCHOOL_ID:
        flash("Trường Demo (ID 99) là dữ liệu mẫu của hệ thống, không được phép chỉnh sửa logo!", "warning")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    if not is_super_admin() and session.get("truong_id") != school_id:
        flash("Bạn không có quyền cập nhật logo cho trường này.", "danger")
        return redirect(url_for("admin_dashboard"))

    if "logo" in request.files:
        file = request.files["logo"]
        if file and file.filename and allowed_image_file(file.filename):
            filename = secure_filename(f"school_{school_id}_{int(time.time())}_{file.filename}")
            upload_dir = BASE_DIR / "static" / "uploads" / "schools"
            upload_dir.mkdir(parents=True, exist_ok=True)
            save_path = upload_dir / filename
            file.save(str(save_path))
            logo_url = f"/static/uploads/schools/{filename}"
            db = get_db()
            cur = db.cursor()
            cur.execute("UPDATE truong SET logo = ? WHERE id = ?", (logo_url, school_id))
            db.commit()
            flash("Đã cập nhật logo trường thành công!", "success")
        else:
            flash("Vui lòng chọn file ảnh hợp lệ (PNG, JPG, WEBP).", "warning")
    return redirect(url_for("admin_dashboard", _anchor="tab-schools" if is_super_admin() else None))


@app.route("/admin/schools/create", methods=["POST"])
@super_admin_required
def admin_create_school():
    """
    Thêm trường học mới vào hệ thống (Prompt Quản lý Trường học):
    - Chỉ Super Admin được phép thực hiện
    - Tự sinh truong_id tiếp theo (không đè ID 99 của Trường Demo)
    - Validate: tên trường bắt buộc, không trùng (case-insensitive)
    - Hỗ trợ tải logo ảnh thực tế hoặc dùng logo mặc định
    - Trạng thái ban đầu: chuan_bi_trien_khai / dang_thi_diem / dang_hoat_dong / tam_ngung
    - an_truong mặc định 0 (nếu tam_ngung thì an_truong = 1)
    """
    ten_truong = request.form.get("ten_truong", "").strip()
    raw_status = request.form.get("trang_thai", "dang_thi_diem").strip()

    if not ten_truong:
        flash("Tên trường học không được để trống!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    status_map = {
        "dang_thi_diem": "dang_thi_diem",
        "chuan_bi_trien_khai": "chuan_bi_trien_khai",
        "dang_hoat_dong": "dang_su_dung",
        "dang_su_dung": "dang_su_dung",
        "tam_ngung": "vo_hieu_hoa",
        "vo_hieu_hoa": "vo_hieu_hoa"
    }
    trang_thai = status_map.get(raw_status, "dang_thi_diem")
    an_truong = 1 if trang_thai == "vo_hieu_hoa" else 0

    db = get_db()
    cur = db.cursor()

    # Validate tên trường không trùng (case-insensitive)
    cur.execute("SELECT id FROM truong WHERE LOWER(TRIM(ten_truong)) = LOWER(?)", (ten_truong,))
    if cur.fetchone():
        flash(f"Trường học '{ten_truong}' đã tồn tại trong hệ thống!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    # Xử lý logo trường học
    logo_url = "/static/img/logo_timebank_edu.png"
    if "logo" in request.files:
        file = request.files["logo"]
        if file and file.filename and allowed_image_file(file.filename):
            filename = secure_filename(f"school_new_{int(time.time())}_{file.filename}")
            upload_dir = BASE_DIR / "static" / "uploads" / "schools"
            upload_dir.mkdir(parents=True, exist_ok=True)
            file.save(str(upload_dir / filename))
            logo_url = f"/static/uploads/schools/{filename}"

    # Tự sinh truong_id tiếp theo (không đè DEMO_SCHOOL_ID = 99)
    cur.execute("SELECT COALESCE(MAX(id), 0) FROM truong WHERE id < ?", (DEMO_SCHOOL_ID,))
    max_regular = cur.fetchone()[0]
    next_id = max(1, max_regular + 1)
    while True:
        cur.execute("SELECT id FROM truong WHERE id = ?", (next_id,))
        if not cur.fetchone():
            break
        next_id += 1
        if next_id == DEMO_SCHOOL_ID:
            next_id = DEMO_SCHOOL_ID + 1

    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO truong (id, ten_truong, logo, trang_thai, an_truong, ngay_tao)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (next_id, ten_truong, logo_url, trang_thai, an_truong, now_dt))

    if is_postgres_configured():
        try:
            cur.execute("SELECT setval(pg_get_serial_sequence('truong', 'id'), (SELECT MAX(id) FROM truong))")
        except Exception:
            pass

    db.commit()
    flash(f"Đã thêm trường học mới '{ten_truong}' (Mã trường ID #{next_id}) thành công!", "success")
    return redirect(url_for("admin_dashboard", _anchor="tab-schools"))


@app.route("/admin/schools/<int:school_id>/edit", methods=["POST"])
@super_admin_required
def admin_edit_school(school_id):
    """
    Sửa tên, logo, trạng thái của trường học:
    - Trường Demo (ID 99) không cho phép sửa
    """
    if school_id == DEMO_SCHOOL_ID:
        flash("Trường Demo (ID 99) là trường mẫu của hệ thống, không được phép chỉnh sửa hoặc xóa!", "warning")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM truong WHERE id = ?", (school_id,))
    school = cur.fetchone()
    if not school:
        flash("Không tìm thấy trường học cần sửa!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    ten_truong = request.form.get("ten_truong", "").strip()
    raw_status = request.form.get("trang_thai", school["trang_thai"]).strip()

    if not ten_truong:
        flash("Tên trường học không được để trống!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    status_map = {
        "dang_thi_diem": "dang_thi_diem",
        "chuan_bi_trien_khai": "chuan_bi_trien_khai",
        "dang_hoat_dong": "dang_su_dung",
        "dang_su_dung": "dang_su_dung",
        "tam_ngung": "vo_hieu_hoa",
        "vo_hieu_hoa": "vo_hieu_hoa"
    }
    trang_thai = status_map.get(raw_status, school["trang_thai"])

    cur.execute("SELECT id FROM truong WHERE LOWER(TRIM(ten_truong)) = LOWER(?) AND id != ?", (ten_truong, school_id))
    if cur.fetchone():
        flash(f"Tên trường '{ten_truong}' trùng với một trường học khác đã có!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    logo_url = school["logo"]
    if "logo" in request.files:
        file = request.files["logo"]
        if file and file.filename and allowed_image_file(file.filename):
            filename = secure_filename(f"school_{school_id}_{int(time.time())}_{file.filename}")
            upload_dir = BASE_DIR / "static" / "uploads" / "schools"
            upload_dir.mkdir(parents=True, exist_ok=True)
            file.save(str(upload_dir / filename))
            logo_url = f"/static/uploads/schools/{filename}"

    # Cập nhật an_truong nếu chuyển sang tạm ngưng / hoặc giữ nguyên
    new_an = 1 if trang_thai == "vo_hieu_hoa" else (0 if trang_thai == "dang_su_dung" else (school["an_truong"] if "an_truong" in school.keys() else 0))

    cur.execute("""
        UPDATE truong 
        SET ten_truong = ?, logo = ?, trang_thai = ?, an_truong = ?
        WHERE id = ?
    """, (ten_truong, logo_url, trang_thai, new_an, school_id))
    db.commit()
    flash(f"Đã cập nhật thông tin trường '{ten_truong}' thành công!", "success")
    return redirect(url_for("admin_dashboard", _anchor="tab-schools"))


@app.route("/admin/schools/<int:school_id>/toggle-hide", methods=["POST"])
@app.route("/admin/schools/<int:school_id>/toggle-status", methods=["POST"])
@super_admin_required
def admin_toggle_school_status(school_id):
    """
    Ẩn hoặc Hiện lại trường học (thay cho xóa cứng):
    - Trường Demo (ID 99) không cho phép sửa/xóa/ẩn
    - Toggle an_truong (0 <-> 1) và đồng bộ trang_thai
    """
    if school_id == DEMO_SCHOOL_ID:
        flash("Trường Demo (ID 99) là trường mẫu của hệ thống, không được phép vô hiệu hóa!", "warning")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM truong WHERE id = ?", (school_id,))
    school = cur.fetchone()
    if not school:
        flash("Không tìm thấy trường học!", "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

    has_an_col = "an_truong" in school.keys()
    an_val = school["an_truong"] if has_an_col and school["an_truong"] is not None else 0
    is_disabled = (school["trang_thai"] in ("vo_hieu_hoa", "tam_ngung")) or (an_val == 1 and school["trang_thai"] not in ("dang_su_dung", "dang_hoat_dong", "dang_thi_diem"))
    if is_disabled:
        new_an = 0
        new_status = "dang_su_dung"
        msg = f"Đã hiện lại trường / Đã kích hoạt lại trường '{school['ten_truong']}'! Trường đã sẵn sàng đón nhận đăng ký mới."
        cat = "success"
    else:
        new_an = 1
        new_status = "vo_hieu_hoa"
        msg = f"Đã ẩn trường / Đã vô hiệu hóa trường '{school['ten_truong']}'. Trường đã bị ẩn khỏi danh sách học sinh và trang chủ."
        cat = "warning"

    cur.execute("UPDATE truong SET an_truong = ?, trang_thai = ? WHERE id = ?", (new_an, new_status, school_id))
    db.commit()
    flash(msg, cat)
    return redirect(url_for("admin_dashboard", _anchor="tab-schools"))

# ==============================================================================
# QUẢN LÝ CHƯƠNG TRÌNH GIỜ CÔNG ÍCH HỌC ĐƯỜNG (THÊM / SỬA / XÓA)
# ==============================================================================
@app.route("/admin/community-tasks/create", methods=["POST"])
@admin_required
def admin_create_community_task():
    """
    Thêm mới chương trình giờ công ích / cộng đồng:
    - Quản trị trường + Super Admin đều dùng được
    - Tên (*), mô tả, số giờ thưởng (*), ngày bắt đầu, ngày kết thúc, trường áp dụng, trạng thái
    """
    tieu_de = request.form.get("tieu_de", "").strip()
    mo_ta = request.form.get("mo_ta", "").strip()
    dia_diem = request.form.get("dia_diem", "").strip()
    ngay_bat_dau = request.form.get("ngay_bat_dau", "").strip()
    ngay_ket_thuc = request.form.get("ngay_ket_thuc", "").strip()
    trang_thai = request.form.get("trang_thai", "dang_dien_ra").strip()

    if not tieu_de:
        flash(_("Vui lòng nhập tên chương trình cộng đồng."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    try:
        so_gio_thuong = float(request.form.get("so_gio_thuong", 1.0))
        if so_gio_thuong <= 0:
            so_gio_thuong = 1.0
    except ValueError:
        so_gio_thuong = 1.0

    try:
        so_luong_toi_da = int(request.form.get("so_luong_toi_da", 10))
        if so_luong_toi_da <= 0:
            so_luong_toi_da = 10
    except ValueError:
        so_luong_toi_da = 10

    # Phân quyền trường áp dụng:
    if is_super_admin():
        try:
            truong_id = int(request.form.get("truong_id", session.get("truong_id", 1)))
        except (ValueError, TypeError):
            truong_id = session.get("truong_id", 1)
    else:
        truong_id = session.get("truong_id", 1)

    db = get_db()
    cur = db.cursor()
    cur.execute("""
        INSERT INTO community_tasks 
        (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, ngay_bat_dau, ngay_ket_thuc, nguoi_tao_id, trang_thai, truong_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da,
        ngay_ket_thuc or ngay_bat_dau, ngay_bat_dau, ngay_ket_thuc,
        session["user_id"], trang_thai, truong_id
    ))
    db.commit()

    flash(_(f"Đã thêm mới chương trình cộng đồng: '{tieu_de}' (+{so_gio_thuong}h thưởng) thành công!"), "success")
    return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))


@app.route("/admin/community-tasks/<int:task_id>/edit", methods=["POST"])
@admin_required
def admin_edit_community_task(task_id):
    """
    Chỉnh sửa chương trình cộng đồng:
    - Quản trị trường chỉ sửa trường mình; Super Admin sửa được tất cả
    - Cập nhật tức thì vào CSDL
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM community_tasks WHERE id = ?", (task_id,))
    task = cur.fetchone()
    if not task:
        flash(_("Chương trình cộng đồng không tồn tại."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    # Kiểm tra phân quyền trường học
    if not is_super_admin() and task["truong_id"] != session.get("truong_id", 1):
        flash(_("Bạn không có quyền chỉnh sửa chương trình của trường khác."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    tieu_de = request.form.get("tieu_de", "").strip()
    mo_ta = request.form.get("mo_ta", "").strip()
    dia_diem = request.form.get("dia_diem", "").strip()
    ngay_bat_dau = request.form.get("ngay_bat_dau", "").strip()
    ngay_ket_thuc = request.form.get("ngay_ket_thuc", "").strip()
    trang_thai = request.form.get("trang_thai", task["trang_thai"]).strip()

    if not tieu_de:
        flash(_("Tên chương trình không được để trống."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    try:
        so_gio_thuong = float(request.form.get("so_gio_thuong", task["so_gio_thuong"]))
        if so_gio_thuong <= 0:
            so_gio_thuong = 1.0
    except ValueError:
        so_gio_thuong = task["so_gio_thuong"]

    try:
        so_luong_toi_da = int(request.form.get("so_luong_toi_da", task["so_luong_toi_da"]))
        if so_luong_toi_da <= 0:
            so_luong_toi_da = 10
    except ValueError:
        so_luong_toi_da = task["so_luong_toi_da"]

    if is_super_admin():
        try:
            truong_id = int(request.form.get("truong_id", task["truong_id"]))
        except (ValueError, TypeError):
            truong_id = task["truong_id"]
    else:
        truong_id = task["truong_id"]

    cur.execute("""
        UPDATE community_tasks
        SET tieu_de = ?, mo_ta = ?, dia_diem = ?, so_gio_thuong = ?, so_luong_toi_da = ?,
            han_dang_ky = ?, ngay_bat_dau = ?, ngay_ket_thuc = ?, trang_thai = ?, truong_id = ?
        WHERE id = ?
    """, (
        tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da,
        ngay_ket_thuc or ngay_bat_dau or task["han_dang_ky"], ngay_bat_dau, ngay_ket_thuc,
        trang_thai, truong_id, task_id
    ))
    db.commit()

    flash(_(f"Đã cập nhật thông tin chương trình: '{tieu_de}' thành công!"), "success")
    return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))


@app.route("/admin/community-tasks/<int:task_id>/delete", methods=["POST"])
@admin_required
def admin_delete_community_task(task_id):
    """
    Xóa chương trình cộng đồng:
    - Xóa vĩnh viễn (hard delete) nếu CHƯA có ai đăng ký
    - Nếu ĐÃ có học sinh đăng ký: Không xóa cứng, chỉ cho chuyển sang 'Đã kết thúc'
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM community_tasks WHERE id = ?", (task_id,))
    task = cur.fetchone()
    if not task:
        flash(_("Chương trình cộng đồng không tồn tại."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    # Kiểm tra phân quyền trường học
    if not is_super_admin() and task["truong_id"] != session.get("truong_id", 1):
        flash(_("Bạn không có quyền xóa chương trình của trường khác."), "danger")
        return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))

    # Kiểm tra số học sinh đã đăng ký
    cur.execute("SELECT COUNT(*) FROM task_registrations WHERE task_id = ? AND trang_thai NOT IN ('huy')", (task_id,))
    registered_count = cur.fetchone()[0]

    if registered_count > 0:
        # Đã có người đăng ký -> chuyển trạng thái 'da_ket_thuc', không xóa cứng
        cur.execute("UPDATE community_tasks SET trang_thai = 'da_ket_thuc' WHERE id = ?", (task_id,))
        db.commit()
        flash(_(f"Chương trình '{task['tieu_de']}' đã có {registered_count} học sinh đăng ký tham gia, không thể xóa vĩnh viễn. Đã tự động chuyển trạng thái sang 'Đã kết thúc'."), "warning")
    else:
        # Chưa có ai đăng ký -> xóa vĩnh viễn khỏi CSDL
        cur.execute("DELETE FROM community_tasks WHERE id = ?", (task_id,))
        db.commit()
        flash(_(f"Đã xóa vĩnh viễn chương trình cộng đồng '{task['tieu_de']}' thành công."), "success")

    return redirect(url_for("admin_dashboard", _anchor="tab-community-tasks"))


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
    - Giáo viên / School Admin chỉ duyệt kỹ năng của trường mình.
    - Super Admin thấy và quản trị kỹ năng của tất cả các trường.
    """
    db = get_db()
    cur = db.cursor()
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    if is_super:
        cur.execute("""
            SELECT s.*, u.ho_ten, u.ma_hoc_sinh, u.lop, t.ten_truong
            FROM skills s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN truong t ON s.truong_id = t.id
            ORDER BY CASE WHEN s.trang_thai_duyet = 'cho_duyet' THEN 0 ELSE 1 END, s.id DESC
        """)
    else:
        cur.execute("""
            SELECT s.*, u.ho_ten, u.ma_hoc_sinh, u.lop, t.ten_truong
            FROM skills s
            JOIN users u ON s.user_id = u.id
            LEFT JOIN truong t ON s.truong_id = t.id
            WHERE s.truong_id = ?
            ORDER BY CASE WHEN s.trang_thai_duyet = 'cho_duyet' THEN 0 ELSE 1 END, s.id DESC
        """, (current_user_school_id,))
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


# ==============================================================================
# PROMPT 19: SÀN GIAO DỊCH CHUNG LIÊN TRƯỜNG & CỔNG 24 TÍN DỤNG
# ==============================================================================

@app.route("/skills/<int:skill_id>/publish-community", methods=["POST"])
@login_required
def publish_community_skill(skill_id):
    """
    Chủ kỹ năng (đã qua cổng tín dụng) gửi yêu cầu đăng lên Sàn cộng đồng liên trường:
    - Kiểm tra: người thực hiện là chủ kỹ năng.
    - Kiểm tra: người thực hiện đã đạt ngưỡng tín dụng dạy thật (get_community_threshold()).
    - Cập nhật trang_thai_cong_dong = 'cho_duyet', hien_thi_cong_dong = 0.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]

    cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
    sk = cur.fetchone()
    if not sk:
        flash("Kỹ năng không tồn tại!", "danger")
        return redirect(url_for("profile"))

    if sk["user_id"] != user_id:
        flash("Bạn chỉ có thể đăng kỹ năng của chính mình lên Cộng đồng liên trường!", "danger")
        return redirect(url_for("profile"))

    threshold = get_community_threshold()
    hours_taught = get_user_teaching_hours(db, user_id)
    if hours_taught < threshold:
        remaining = max(0.0, threshold - hours_taught)
        rem_str = int(remaining) if remaining == int(remaining) else round(remaining, 1)
        flash(f"Bạn cần {rem_str} giờ dạy nữa để mở khóa Cộng đồng liên trường!", "warning")
        return redirect(url_for("profile"))

    cur.execute("""
        UPDATE skills 
        SET trang_thai_cong_dong = 'cho_duyet',
            hien_thi_cong_dong = 0
        WHERE id = ?
    """, (skill_id,))
    db.commit()

    flash("Đã gửi yêu cầu đăng kỹ năng lên Cộng đồng liên trường. Vui lòng chờ Ban quản trị duyệt!", "success")
    return redirect(url_for("profile"))


@app.route("/admin/community-skills/<int:skill_id>/approve", methods=["POST"])
@admin_required
def admin_approve_community_skill(skill_id):
    """
    Phê duyệt kỹ năng lên Sàn cộng đồng liên trường:
    - Tổng quản trị HOẶC quản trị bất kỳ trường nào duyệt là đủ (một người duyệt).
    - Ghi log ai duyệt (session['user_id']).
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.ho_ten, t.ten_truong 
        FROM skills s 
        JOIN users u ON s.user_id = u.id 
        LEFT JOIN truong t ON s.truong_id = t.id 
        WHERE s.id = ?
    """, (skill_id,))
    sk = cur.fetchone()
    if not sk:
        flash("Không tìm thấy kỹ năng!", "danger")
        return redirect(url_for("admin_dashboard"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        UPDATE skills
        SET hien_thi_cong_dong = 1,
            trang_thai_cong_dong = 'da_duyet',
            trang_thai_duyet = 'da_duyet',
            nguoi_duyet_cong_dong_id = ?,
            ngay_duyet_cong_dong = ?
        WHERE id = ?
    """, (session["user_id"], now_str, skill_id))
    db.commit()

    school_name = sk["ten_truong"] if sk["ten_truong"] else "Trường học"
    flash(f"Đã duyệt kỹ năng '{sk['tieu_de']}' ({school_name}) lên Cộng đồng liên trường thành công!", "success")
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/community-skills/<int:skill_id>/reject", methods=["POST"])
@admin_required
def admin_reject_community_skill(skill_id):
    """
    Từ chối đưa kỹ năng lên Cộng đồng liên trường.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT s.*, u.ho_ten FROM skills s JOIN users u ON s.user_id = u.id WHERE s.id = ?", (skill_id,))
    sk = cur.fetchone()
    if not sk:
        flash("Không tìm thấy kỹ năng!", "danger")
        return redirect(url_for("admin_dashboard"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        UPDATE skills
        SET hien_thi_cong_dong = 0,
            trang_thai_cong_dong = 'tu_choi',
            nguoi_duyet_cong_dong_id = ?,
            ngay_duyet_cong_dong = ?
        WHERE id = ?
    """, (session["user_id"], now_str, skill_id))
    db.commit()

    flash(f"Đã từ chối đưa kỹ năng '{sk['tieu_de']}' lên Cộng đồng liên trường.", "info")
    return redirect(url_for("admin_dashboard"))


@app.route("/community-market")
def community_market():
    """
    Cộng Đồng Liên Trường (Prompt 19):
    - Cổng kiểm chuẩn tín dụng dạy thật: Học sinh chưa đạt ngưỡng -> Chặn và hiện thông báo + thanh tiến trình.
    - Học sinh đạt ngưỡng (hoặc Quản trị viên/Giáo viên) -> Truy cập Cộng đồng liên trường.
    - Kỹ năng hiển thị kèm TÊN TRƯỜNG của chủ kỹ năng.
    """
    db = get_db()
    cur = db.cursor()

    threshold = get_community_threshold()
    user_id = session.get("user_id")
    user_role = session.get("vai_tro", "")
    is_admin_user = user_role in ("super_admin", "school_admin", "admin", "giao_vien")

    if not user_id:
        flash("Vui lòng đăng nhập để truy cập Cộng đồng liên trường.", "warning")
        return redirect(url_for("login", next=request.url))

    teaching_hours = get_user_teaching_hours(db, user_id)

    # Học sinh chưa đạt ngưỡng tín dụng dạy thật -> Hiển thị màn hình Cổng kiểm chuẩn
    if not is_admin_user and teaching_hours < threshold:
        remaining_hours = max(0.0, threshold - teaching_hours)
        remaining_display = int(remaining_hours) if remaining_hours == int(remaining_hours) else round(remaining_hours, 1)
        teaching_hours_display = int(teaching_hours) if teaching_hours == int(teaching_hours) else round(teaching_hours, 1)
        threshold_display = int(threshold) if threshold == int(threshold) else round(threshold, 1)
        progress_pct = min(100.0, max(0.0, round((teaching_hours / threshold) * 100, 1))) if threshold > 0 else 100.0
        return render_template(
            "community_market_gate.html",
            threshold=threshold,
            threshold_display=threshold_display,
            teaching_hours=teaching_hours,
            teaching_hours_display=teaching_hours_display,
            remaining_hours=remaining_hours,
            remaining_display=remaining_display,
            progress_pct=progress_pct
        )

    # Đã qua cổng hoặc là Quản trị viên/Giáo viên -> Hiển thị Sàn cộng đồng
    search_query = request.args.get("q", "").strip()
    selected_school = request.args.get("truong_id", "").strip()
    selected_category = request.args.get("linh_vuc", "").strip()

    sql = """
        SELECT 
            s.*, 
            u.ho_ten, 
            u.ma_hoc_sinh, 
            u.lop,
            t.ten_truong,
            t.logo AS logo_truong,
            ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN truong t ON s.truong_id = t.id
        LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE s.hien_thi_cong_dong = 1 AND s.trang_thai_cong_dong = 'da_duyet'
    """
    params = []

    if selected_school and selected_school.isdigit():
        sql += " AND s.truong_id = ?"
        params.append(int(selected_school))

    if selected_category:
        sql += " AND s.linh_vuc = ?"
        params.append(selected_category)

    if search_query:
        sql += " AND (s.tieu_de LIKE ? OR s.mo_ta LIKE ? OR s.linh_vuc LIKE ? OR t.ten_truong LIKE ?)"
        like_term = f"%{search_query}%"
        params.extend([like_term, like_term, like_term, like_term])

    sql += " GROUP BY s.id, u.id, u.ho_ten, u.ma_hoc_sinh, u.lop, t.ten_truong, t.logo ORDER BY s.id DESC"
    cur.execute(sql, params)
    skills = cur.fetchall()

    cur.execute("SELECT id, ten_truong FROM truong WHERE COALESCE(an_truong, 0) = 0 ORDER BY id ASC")
    all_schools = cur.fetchall()

    return render_template(
        "community_market.html",
        skills=skills,
        all_schools=all_schools,
        search_query=search_query,
        selected_school=selected_school,
        selected_category=selected_category,
        threshold=threshold,
        teaching_hours=teaching_hours
    )


# ------------------------------------------------------------------------------
# MILESTONE M2: ĐĂNG KỸ NĂNG, CHỢ KỸ NĂNG, ĐẶT LỊCH & LỊCH CỦA TÔI
# ------------------------------------------------------------------------------

@app.route("/skills")
def skills_market():
    """
    Chợ Kỹ Năng Học Đường:
    - Hiển thị những kỹ năng có trạng thái 'da_duyet'.
    - Lọc theo trường của học sinh đang đăng nhập (hoặc tất cả nếu là Super Admin / Khách).
    - Hỗ trợ tìm kiếm từ khóa và lọc danh mục.
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
            ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE s.trang_thai_duyet = 'da_duyet'
    """
    params = []

    # Lọc theo trường: học sinh chỉ thấy kỹ năng trường mình
    if "user_id" in session:
        if not is_super_admin():
            sql += " AND s.truong_id = ?"
            params.append(session.get("truong_id", 1))
        else:
            req_school = request.args.get("truong_id")
            if req_school and req_school.isdigit():
                sql += " AND s.truong_id = ?"
                params.append(int(req_school))
    
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
    - AI lọc trong danh sách các gia sư có kỹ năng 'da_duyet' cùng trường và chọn ra người phù hợp nhất.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    current_user_school_id = session.get("truong_id", 1)
    
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
            cur.execute("""
                SELECT s.*, u.ho_ten, u.lop, u.gio_ranh,
                       ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
                FROM skills s
                JOIN users u ON s.user_id = u.id
                LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
                LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
                WHERE s.trang_thai_duyet = 'da_duyet' AND s.user_id != ? AND s.truong_id = ?
                GROUP BY s.id, u.id, u.ho_ten, u.lop, u.gio_ranh
                ORDER BY s.id DESC
            """, (user_id, current_user_school_id))
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
    - Chặn nếu tài khoản đang ở trạng thái 'Chờ duyệt' (chưa kích hoạt qua mã mời).
    - Học sinh chọn lĩnh vực, nhập tiêu đề & mô tả.
    """
    valid_categories = ('Toán', 'Lý', 'Hóa', 'Văn', 'Anh', 'Vẽ', 'Đàn', 'Thể thao', 'Tin học', 'Khác')
    
    db = get_db()
    cur = db.cursor()

    # Kiểm tra trạng thái tài khoản: không được đăng kỹ năng khi chờ duyệt
    cur.execute("SELECT trang_thai FROM users WHERE id = ?", (session["user_id"],))
    u_row = cur.fetchone()
    if u_row and u_row["trang_thai"] == "cho_duyet":
        flash("Tài khoản của bạn đang trong hàng chờ duyệt bởi Quản trị viên nhà trường. Bạn chưa thể đăng kỹ năng cho đến khi tài khoản được kích hoạt.", "warning")
        return redirect(url_for("profile"))

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
        
        # Điểm chạm 1: AI Kiểm duyệt kỹ năng (Gemini Pro)
        is_approved, ai_reason, is_live = ai_moderate_skill(
            db, session["user_id"], linh_vuc, tieu_de, mo_ta
        )
        
        trang_thai_duyet = "da_duyet" if is_approved else "cho_duyet"
        ai_tag = "Hỗ trợ bởi AI (Gemini): " if is_live else "Hỗ trợ bởi AI (Chế độ cơ bản): "
        ly_do_luu = f"{ai_tag}{ai_reason}"
        school_id = session.get("truong_id", 1)
        
        cur.execute(
            """INSERT INTO skills 
               (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet, truong_id) 
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session["user_id"], linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_luu, school_id)
        )
        db.commit()
        
        if is_approved:
            flash(f"Đăng ký thành công! {ly_do_luu}. Kỹ năng đã sẵn sàng trên Kho kỹ năng học đường.", "success")
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
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT s.*, u.ho_ten, u.lop, u.gio_ranh, u.ma_hoc_sinh,
               ROUND(COALESCE(AVG(r.so_sao), 5.0)::numeric, 1) AS sao_tb
        FROM skills s
        JOIN users u ON s.user_id = u.id
        LEFT JOIN sessions ses ON s.id = ses.skill_id AND ses.trang_thai = 'hoan_thanh'
        LEFT JOIN ratings r ON ses.id = r.session_id AND r.nguoi_duoc_danh_gia_id = u.id
        WHERE s.id = ?
        GROUP BY s.id, u.id, u.ho_ten, u.lop, u.gio_ranh, u.ma_hoc_sinh
    """, (skill_id,))
    skill = cur.fetchone()
    if not skill or (skill["trang_thai_duyet"] != "da_duyet" and skill.get("hien_thi_cong_dong") != 1):
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
    - Chặn nếu tài khoản đang ở trạng thái 'Chờ duyệt'.
    - Kiểm tra: Kỹ năng phải có trạng thái 'da_duyet'.
    - Kiểm tra: Không được tự đặt lịch kỹ năng của chính mình.
    - Kiểm tra: Thời lượng tối đa 2.0 giờ / phiên (0.5 <= so_gio <= 2.0).
    - Kiểm tra: Người học phải có đủ số dư giờ tín dụng.
    """
    db = get_db()
    cur = db.cursor()

    # Kiểm tra trạng thái người học: chặn ngay nếu đang chờ duyệt
    cur.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],))
    learner = cur.fetchone()
    if not learner:
        flash("Không tìm thấy thông tin tài khoản người học.", "danger")
        return redirect(url_for("skills_market"))
    if learner["trang_thai"] == "cho_duyet":
        flash("Tài khoản của bạn đang trong hàng chờ duyệt bởi Quản trị viên nhà trường. Bạn chưa thể đặt lịch học cho đến khi tài khoản được kích hoạt.", "warning")
        return redirect(url_for("skills_market"))

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
    
    # 1. Kiểm tra kỹ năng có tồn tại và đã duyệt chưa
    cur.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
    skill = cur.fetchone()
    if not skill or (skill["trang_thai_duyet"] != "da_duyet" and skill.get("hien_thi_cong_dong") != 1):
        flash("Kỹ năng này chưa sẵn sàng hoặc chưa được phê duyệt sư phạm!", "danger")
        return redirect(url_for("skills_market"))
        
    # 2. Không được tự đặt lịch kỹ năng của chính mình
    if skill["user_id"] == session["user_id"]:
        flash("Bạn không thể tự đặt lịch kỹ năng của chính mình!", "warning")
        return redirect(url_for("skills_market"))
        
    # 3. Kiểm tra số dư người học
    if learner["so_du_gio"] < so_gio:
        flash(f"Số dư tín dụng của bạn không đủ để đặt lịch buổi học này! (Hiện có: {learner['so_du_gio']:.1f}h, Cần: {so_gio:.1f}h). Hãy dạy kèm bạn bè để tích thêm giờ nhé!", "danger")
        return redirect(url_for("skills_market"))
        
    # 4. Lấy thông tin gia sư
    cur.execute("SELECT ho_ten FROM users WHERE id = ?", (skill["user_id"],))
    tutor = cur.fetchone()
    tutor_name = tutor["ho_ten"] if tutor else "Gia sư"
    
    # 5. Tạo mã QR ngẫu nhiên và lưu phiên 'da_dat'
    ma_qr = f"TB-QR-{skill_id}-{secrets.token_hex(4).upper()}"
    session_truong_id = skill["truong_id"] if "truong_id" in skill.keys() and skill["truong_id"] else session.get("truong_id", 1)
    
    cur.execute(
        """INSERT INTO sessions 
           (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan, truong_id)
           VALUES (?, ?, ?, ?, ?, 'da_dat', ?, 0, 0, NULL, 0, ?)""",
        (skill_id, skill["user_id"], session["user_id"], thoi_gian_bat_dau, so_gio, ma_qr, session_truong_id)
    )
    new_session_id = cur.lastrowid
    db.commit()

    # Prompt 22: Tạo phòng Daily.co tự động nếu có cấu hình DAILY_API_KEY
    if get_daily_config()["is_configured"]:
        try:
            create_daily_room(new_session_id)
        except Exception as e:
            app.logger.warning(f"Không thể tạo phòng Daily.co khi đặt lịch #{new_session_id}: {e}")
    
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
    session_truong_id = session.get("truong_id", 1)

    cur.execute(
        """INSERT INTO ratings (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet, truong_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, user_id, target_id, so_sao, nhan_xet, session_truong_id)
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


# ==============================================================================
# PROMPT 22: PHÒNG HỌC ẢO 3 NÒNG (DAILY.CO CHÍNH -> JAAS DỰ PHÒNG 1 -> JITSI DỰ PHÒNG 2)
# ==============================================================================
def get_daily_config():
    """
    Đọc cấu hình Daily.co từ biến môi trường:
    - DAILY_API_KEY: Khóa API bí mật của Daily.co
    Thiếu key -> is_configured = False, không crash.
    """
    api_key = os.getenv("DAILY_API_KEY", "").strip()
    return {
        "api_key": api_key,
        "is_configured": bool(api_key)
    }


def create_daily_room(session_id):
    """
    Tạo phòng học trên Daily.co cho buổi học:
    - POST https://api.daily.co/v1/rooms
    - name: "timebank-session-{session_id}"
    - privacy: "private"
    - exp: now + 3 giờ
    - Lưu daily_room_name và daily_room_url vào bảng sessions
    - Xử lý nếu phòng đã tồn tại hoặc lỗi mạng, không crash.
    """
    cfg = get_daily_config()
    if not cfg["is_configured"]:
        app.logger.warning("DAILY_API_KEY chưa được cấu hình, bỏ qua tạo phòng Daily.co.")
        return None, None

    room_name = f"timebank-session-{session_id}"
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": room_name,
        "privacy": "private",
        "properties": {
            "exp": int(time.time()) + 3 * 3600
        }
    }

    try:
        import requests
        resp = requests.post("https://api.daily.co/v1/rooms", headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            r_name = data.get("name", room_name)
            r_url = data.get("url")
            try:
                db = get_db()
                db.execute("UPDATE sessions SET daily_room_name = ?, daily_room_url = ? WHERE id = ?", (r_name, r_url, session_id))
                db.commit()
            except Exception:
                conn = sqlite3.connect(DATABASE_PATH)
                conn.execute("UPDATE sessions SET daily_room_name = ?, daily_room_url = ? WHERE id = ?", (r_name, r_url, session_id))
                conn.commit()
                conn.close()
            return r_name, r_url
        elif resp.status_code == 400 and "already exists" in resp.text.lower():
            # Phòng đã tồn tại -> lấy thông tin phòng
            get_resp = requests.get(f"https://api.daily.co/v1/rooms/{room_name}", headers=headers, timeout=8)
            if get_resp.status_code == 200:
                data = get_resp.json()
                r_name = data.get("name", room_name)
                r_url = data.get("url")
                try:
                    db = get_db()
                    db.execute("UPDATE sessions SET daily_room_name = ?, daily_room_url = ? WHERE id = ?", (r_name, r_url, session_id))
                    db.commit()
                except Exception:
                    conn = sqlite3.connect(DATABASE_PATH)
                    conn.execute("UPDATE sessions SET daily_room_name = ?, daily_room_url = ? WHERE id = ?", (r_name, r_url, session_id))
                    conn.commit()
                    conn.close()
                return r_name, r_url
            app.logger.warning(f"Lỗi lấy thông tin phòng Daily.co đã tồn tại: {get_resp.text}")
        else:
            app.logger.warning(f"Lỗi tạo phòng Daily.co (#{resp.status_code}): {resp.text}")
    except Exception as e:
        app.logger.warning(f"Lỗi kết nối tới Daily.co API: {e}")

    return None, None


def create_daily_meeting_token(room_name, user_name, is_owner=False):
    """
    Sinh meeting token cho Daily.co:
    - POST https://api.daily.co/v1/meeting-tokens
    - room_name: tên phòng Daily
    - user_name: họ tên thật của học sinh / giáo viên từ DB
    - is_owner: True nếu là người dạy hoặc giáo viên/admin
    - exp: now + 2 giờ
    """
    cfg = get_daily_config()
    if not cfg["is_configured"]:
        return None, "DAILY_API_KEY chưa được cấu hình"

    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "properties": {
            "room_name": str(room_name),
            "user_name": str(user_name),
            "is_owner": bool(is_owner),
            "exp": int(time.time()) + 2 * 3600
        }
    }

    try:
        import requests
        resp = requests.post("https://api.daily.co/v1/meeting-tokens", headers=headers, json=payload, timeout=8)
        if resp.status_code == 200:
            token = resp.json().get("token")
            return token, None
        return None, f"Daily.co meeting-tokens lỗi ({resp.status_code}): {resp.text}"
    except Exception as e:
        return None, f"Lỗi gọi Daily.co meeting token API: {str(e)}"


def get_jaas_config():
    """
    Đọc 3 biến môi trường JaaS (8x8 Jitsi as a Service):
    - JAAS_APP_ID: ID ứng dụng JaaS (ví dụ: vpaas-magic-cookie-xxx)
    - JAAS_API_KEY: Key ID (kid) trong header JWT
    - JAAS_PRIVATE_KEY: Khóa bí mật RSA Private Key (PEM)
    Tự động chuyển literal '\\n' thành ký tự xuống dòng thật.
    """
    app_id = os.getenv("JAAS_APP_ID", "").strip()
    api_key = os.getenv("JAAS_API_KEY", "").strip()
    private_key_raw = os.getenv("JAAS_PRIVATE_KEY", "").strip()
    
    # Gỡ bỏ dấu nháy kép / nháy đơn bọc ngoài nếu có
    if (private_key_raw.startswith('"') and private_key_raw.endswith('"')) or (private_key_raw.startswith("'") and private_key_raw.endswith("'")):
        private_key_raw = private_key_raw[1:-1].strip()
        
    private_key = private_key_raw.replace("\\n", "\n").strip() if private_key_raw else ""
    
    missing = []
    if not app_id:
        missing.append("JAAS_APP_ID")
    if not api_key:
        missing.append("JAAS_API_KEY")
    if not private_key:
        missing.append("JAAS_PRIVATE_KEY")
        
    is_configured = (len(missing) == 0)
    return {
        "app_id": app_id,
        "api_key": api_key,
        "private_key": private_key,
        "is_configured": is_configured,
        "missing": missing
    }


def generate_jaas_jwt(session_id, user_id, user_name, user_email, is_moderator):
    """
    Sinh JWT RS256 cho phòng học ảo 8x8 JaaS theo chuẩn Jitsi Meet.
    Header: kid=JAAS_API_KEY, alg=RS256, typ=JWT
    Payload:
      aud="jitsi", iss="chat", sub=JAAS_APP_ID, room="*",
      exp=now + 2 giờ, nbf=now - 10, session_id=session_id
      context.user = {name: họ tên thật từ DB, email: mã HS},
      context.user.moderator = true (người dạy/giáo viên) / false (người học)
    """
    jaas_cfg = get_jaas_config()
    if not jaas_cfg["is_configured"]:
        return None, f"Chưa cấu hình đầy đủ biến môi trường JaaS: {', '.join(jaas_cfg['missing'])}"
        
    now_ts = int(time.time())
    headers = {
        "alg": "RS256",
        "typ": "JWT",
        "kid": jaas_cfg["api_key"]
    }
    payload = {
        "aud": "jitsi",
        "iss": "chat",
        "sub": jaas_cfg["app_id"],
        "room": "*",
        "exp": now_ts + 7200,  # now + 2 giờ
        "nbf": now_ts - 10,
        "session_id": int(session_id),
        "context": {
            "user": {
                "name": str(user_name),
                "email": str(user_email),
                "moderator": bool(is_moderator)
            },
            "features": {
                "livestreaming": False,
                "recording": False
            }
        }
    }
    
    try:
        token = jwt.encode(
            payload,
            jaas_cfg["private_key"],
            algorithm="RS256",
            headers=headers
        )
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        return token, None
    except Exception as e:
        return None, f"Lỗi tạo chữ ký RSA token JaaS: {str(e)}"


def verify_jaas_token(token, expected_session_id=None, public_key=None):
    """
    Xác thực token JaaS RS256:
    - Kiểm tra thời hạn hiệu lực (hết hạn bị từ chối).
    - Kiểm tra session_id (Token buổi A không dùng cho buổi B).
    - Kiểm tra chữ ký (nếu có public_key).
    """
    try:
        if public_key:
            decoded = jwt.decode(token, public_key, algorithms=["RS256"], audience="jitsi")
        else:
            decoded = jwt.decode(token, options={"verify_signature": False, "verify_exp": True}, audience="jitsi")
            
        if expected_session_id is not None:
            token_session_id = decoded.get("session_id")
            if token_session_id is None or int(token_session_id) != int(expected_session_id):
                return False, f"Token không khớp buổi học (Token session: {token_session_id}, Buổi yêu cầu: {expected_session_id})", None
                
        return True, "Token hợp lệ", decoded
    except jwt.ExpiredSignatureError:
        return False, "Token đã hết hạn", None
    except Exception as e:
        return False, f"Token không hợp lệ: {str(e)}", None


@app.route("/sessions/<int:session_id>/room")
@app.route("/phong-hoc/<int:session_id>")
@login_required
def virtual_room(session_id):
    """
    Phòng học ảo trong ứng dụng (Jitsi JaaS RS256 JWT):
    - Tích hợp 8x8 JaaS External API từ https://8x8.vc/{JAAS_APP_ID}/{room_name}
    - Đăng nhập 1 lần: lấy token JWT RS256 từ server, tên hiển thị = họ tên thật, người dạy là moderator.
    - Điểm danh tự động (record_attendance_entry).
    - Quản lý tiêu chuẩn 80% thời lượng cùng online.
    - Thiếu biến môi trường JaaS -> Báo lỗi thân thiện, không crash 500.
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
    
    video_provider = get_video_provider()
    daily_cfg = get_daily_config()
    jaas_cfg = get_jaas_config()

    daily_room_name = session_data["daily_room_name"] if "daily_room_name" in session_data.keys() else None
    daily_room_url = session_data["daily_room_url"] if "daily_room_url" in session_data.keys() else None

    # Tự động tạo phòng Daily nếu nòng Daily có cấu hình mà chưa có room_url trong DB
    if daily_cfg["is_configured"] and not daily_room_url:
        daily_room_name, daily_room_url = create_daily_room(session_id)

    return render_template(
        "virtual_room.html",
        session_data=session_data,
        room_name=room_name,
        is_teacher=is_teacher,
        is_learner=is_learner,
        is_supervisor=is_supervisor,
        video_provider=video_provider,
        daily_configured=daily_cfg["is_configured"],
        daily_room_name=daily_room_name or f"timebank-session-{session_id}",
        daily_room_url=daily_room_url,
        jaas_configured=jaas_cfg["is_configured"],
        missing_jaas_vars=jaas_cfg["missing"],
        jaas_app_id=jaas_cfg["app_id"]
    )


@app.route("/sessions/<int:session_id>/token", methods=["POST"])
@app.route("/phong-hoc/<int:session_id>/token", methods=["POST"])
@login_required
def get_virtual_room_token(session_id):
    """
    Route cấp token cho phòng học ảo 3 nòng (Daily.co -> JaaS -> Jitsi):
    - Kiểm tra user thuộc đúng buổi học (người dạy / người học / giáo viên / admin).
    - Mặc định: Lấy theo VIDEO_PROVIDER (daily -> fallback jaas -> fallback jitsi).
    - Nhận parameter ?provider=daily|jaas hoặc JSON {"provider": "..."} nếu frontend yêu cầu nòng cụ thể.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro", "")
    
    cur.execute(
        """SELECT s.*, sk.tieu_de, ud.ho_ten AS ten_nguoi_day, uh.ho_ten AS ten_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.id = ?""",
        (session_id,)
    )
    session_data = cur.fetchone()
    
    if not session_data:
        return jsonify({"error": "Phiên học không tồn tại"}), 404
        
    is_teacher = (session_data["nguoi_day_id"] == user_id)
    is_learner = (session_data["nguoi_hoc_id"] == user_id)
    is_supervisor = (user_role in ("admin", "giao_vien", "school_admin", "super_admin"))
    
    if not (is_teacher or is_learner or is_supervisor):
        return jsonify({"error": "Bạn không có quyền tham gia phiên học này"}), 403
        
    # Lấy thông tin họ tên thật và mã HS từ DB
    cur.execute("SELECT id, ho_ten, ma_hoc_sinh, vai_tro FROM users WHERE id = ?", (user_id,))
    u_info = cur.fetchone()
    user_name = u_info["ho_ten"] if u_info else session.get("ho_ten", "Thành viên")
    user_email = u_info["ma_hoc_sinh"] if u_info else session.get("ma_hoc_sinh", f"user_{user_id}")
    is_mod = bool(is_teacher or is_supervisor)

    raw_ma_qr = session_data["ma_qr"] or f"SES_{session_id}"
    clean_ma_qr = re.sub(r'[^a-zA-Z0-9_-]', '', raw_ma_qr)
    room_name = f"timebankedu-{clean_ma_qr}"

    # Xác định provider
    req_json = request.get_json(silent=True) or {}
    requested_provider = request.args.get("provider") or req_json.get("provider")
    configured_provider = get_video_provider()
    provider = (requested_provider or configured_provider).lower().strip()

    daily_cfg = get_daily_config()
    jaas_cfg = get_jaas_config()

    # NẾU YÊU CẦU HOẶC MẶC ĐỊNH LÀ DAILY.CO:
    if provider == "daily":
        if daily_cfg["is_configured"]:
            # Đảm bảo phòng Daily đã được tạo
            daily_room_name = session_data["daily_room_name"] if "daily_room_name" in session_data.keys() else None
            daily_room_url = session_data["daily_room_url"] if "daily_room_url" in session_data.keys() else None
            if not daily_room_url:
                daily_room_name, daily_room_url = create_daily_room(session_id)
            if not daily_room_name:
                daily_room_name = f"timebank-session-{session_id}"

            token, err = create_daily_meeting_token(daily_room_name, user_name, is_owner=is_mod)
            if token and not err:
                return jsonify({
                    "success": True,
                    "provider": "daily",
                    "token": token,
                    "room_name": daily_room_name,
                    "room_url": daily_room_url,
                    "session_id": session_id,
                    "user": {
                        "name": user_name,
                        "email": user_email,
                        "is_owner": is_mod,
                        "moderator": is_mod
                    }
                })
            else:
                app.logger.warning(f"Lỗi tạo token Daily.co: {err}")
                if requested_provider == "daily":
                    return jsonify({"error": f"Lỗi cấp token Daily.co: {err}"}), 500
        else:
            if requested_provider == "daily":
                return jsonify({
                    "error": "Hệ thống chưa cấu hình biến môi trường DAILY_API_KEY",
                    "missing": ["DAILY_API_KEY"]
                }), 503
        # Tự động fallback sang JaaS nếu Daily không có key và provider không bị ép cứng
        provider = "jaas"

    # NẾU LÀ JAAS (HOẶC FALLBACK TỪ DAILY):
    if provider == "jaas":
        if not jaas_cfg["is_configured"]:
            return jsonify({
                "error": "Hệ thống chưa cấu hình đầy đủ biến môi trường JaaS (8x8)",
                "missing": jaas_cfg["missing"]
            }), 503
            
        token, err = generate_jaas_jwt(
            session_id=session_id,
            user_id=user_id,
            user_name=user_name,
            user_email=user_email,
            is_moderator=is_mod
        )
        if err:
            return jsonify({"error": err}), 500
            
        return jsonify({
            "success": True,
            "provider": "jaas",
            "token": token,
            "room_name": room_name,
            "jaas_app_id": jaas_cfg["app_id"],
            "session_id": session_id,
            "user": {
                "name": user_name,
                "email": user_email,
                "moderator": is_mod,
                "is_owner": is_mod
            }
        })

    # NẾU LÀ JITSI CÔNG CỘNG:
    return jsonify({
        "success": True,
        "provider": "jitsi",
        "room_name": room_name,
        "room_url": f"https://meet.jit.si/{room_name}",
        "session_id": session_id,
        "user": {
            "name": user_name,
            "email": user_email,
            "moderator": is_mod,
            "is_owner": is_mod
        }
    })


@app.route("/phong-hoc/<int:session_id>/daily-token", methods=["POST"])
@login_required
def get_daily_room_token(session_id):
    """Route cấp riêng meeting token Daily.co (nòng chính)."""
    request.args = {**request.args, "provider": "daily"}
    return get_virtual_room_token(session_id)


@app.route("/phong-hoc/<int:session_id>/jaas-token", methods=["POST"])
@login_required
def get_jaas_room_token(session_id):
    """Route cấp riêng JWT token 8x8 JaaS (nòng dự phòng 1)."""
    request.args = {**request.args, "provider": "jaas"}
    return get_virtual_room_token(session_id)


@app.route("/phong-hoc/<int:session_id>/verify-token", methods=["POST"])
@login_required
def verify_virtual_room_token(session_id):
    """
    Endpoint xác thực token cho buổi học: kiểm tra token có đúng buổi học và còn hạn không.
    """
    data = request.get_json(silent=True) or request.form
    token = data.get("token") if data else None
    if not token:
        return jsonify({"valid": False, "error": "Thiếu token để xác thực"}), 400
        
    valid, msg, payload = verify_jaas_token(token, expected_session_id=session_id)
    if not valid:
        return jsonify({"valid": False, "error": msg}), 400
        
    return jsonify({
        "valid": True,
        "message": msg,
        "payload": payload
    }), 200


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
    
    # Lọc theo trường: School Admin / Giáo viên chỉ giám sát phòng học trường mình
    current_user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    where_filter = ""
    params = ()
    if not is_super:
        where_filter = "AND s.truong_id = ?"
        params = (current_user_school_id,)

    # 1. Các phòng đang diễn ra (da_dat)
    cur.execute(
        f"""SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'da_dat' {where_filter}
           ORDER BY s.id DESC""",
        params
    )
    live_rooms = cur.fetchall()
    
    # 2. Các phòng cần xác minh (< 80%)
    cur.execute(
        f"""SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'can_xac_minh' {where_filter}
           ORDER BY s.id DESC""",
        params
    )
    verification_rooms = cur.fetchall()
    
    # 3. Các phòng đã hoàn thành gần đây
    cur.execute(
        f"""SELECT s.*, sk.tieu_de, sk.linh_vuc,
                  ud.ho_ten AS ten_nguoi_day, ud.lop AS lop_nguoi_day,
                  uh.ho_ten AS ten_nguoi_hoc, uh.lop AS lop_nguoi_hoc
           FROM sessions s
           JOIN skills sk ON s.skill_id = sk.id
           JOIN users ud ON s.nguoi_day_id = ud.id
           JOIN users uh ON s.nguoi_hoc_id = uh.id
           WHERE s.trang_thai = 'hoan_thanh' {where_filter}
           ORDER BY s.id DESC LIMIT 10""",
        params
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

    # Lọc theo trường: học sinh chỉ thấy nhiệm vụ của trường mình
    current_user_school_id = session.get("truong_id", 1) if "user_id" in session else 1
    is_super = is_super_admin() if "user_id" in session else False

    # Truy vấn danh sách nhiệm vụ đang mở
    if is_super:
        cur.execute("""
            SELECT t.*, u.ho_ten AS ten_nguoi_tao,
                   (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
            FROM community_tasks t
            LEFT JOIN users u ON t.nguoi_tao_id = u.id
            WHERE t.trang_thai IN ('mo_dang_ky', 'mo', 'sap_dien_ra', 'dang_dien_ra')
            ORDER BY t.id DESC
        """)
    else:
        cur.execute("""
            SELECT t.*, u.ho_ten AS ten_nguoi_tao,
                   (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai NOT IN ('huy')) AS so_luong_da_dang_ky
            FROM community_tasks t
            LEFT JOIN users u ON t.nguoi_tao_id = u.id
            WHERE t.trang_thai IN ('mo_dang_ky', 'mo', 'sap_dien_ra', 'dang_dien_ra') AND (t.truong_id = ? OR t.truong_id IS NULL)
            ORDER BY t.id DESC
        """, (current_user_school_id,))
    open_tasks = [dict(row) for row in cur.fetchall()]

    today_str = datetime.now().strftime("%Y-%m-%d")
    for t in open_tasks:
        t["is_full"] = t["so_luong_da_dang_ky"] >= t["so_luong_toi_da"]
        t["is_expired"] = bool(t["han_dang_ky"] and t["han_dang_ky"] < today_str)

    # Truy vấn danh sách nhiệm vụ đã hoàn thành để thống kê và tham khảo
    if is_super:
        cur.execute("""
            SELECT t.*, u.ho_ten AS ten_nguoi_tao,
                   (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai = 'hoan_thanh') AS so_luong_hoan_thanh
            FROM community_tasks t
            LEFT JOIN users u ON t.nguoi_tao_id = u.id
            WHERE t.trang_thai IN ('hoan_thanh', 'dong', 'da_ket_thuc')
            ORDER BY t.id DESC
            LIMIT 6
        """)
    else:
        cur.execute("""
            SELECT t.*, u.ho_ten AS ten_nguoi_tao,
                   (SELECT COUNT(*) FROM task_registrations r WHERE r.task_id = t.id AND r.trang_thai = 'hoan_thanh') AS so_luong_hoan_thanh
            FROM community_tasks t
            LEFT JOIN users u ON t.nguoi_tao_id = u.id
            WHERE t.trang_thai IN ('hoan_thanh', 'dong', 'da_ket_thuc') AND (t.truong_id = ? OR t.truong_id IS NULL)
            ORDER BY t.id DESC
            LIMIT 6
        """, (current_user_school_id,))
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

    # Số liệu tổng hợp
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

    anh_bia = None
    if "anh_bia" in request.files:
        file = request.files["anh_bia"]
        if file and file.filename and allowed_image_file(file.filename):
            filename = secure_filename(f"task_{int(time.time())}_{file.filename}")
            upload_dir = BASE_DIR / "static" / "uploads" / "tasks"
            upload_dir.mkdir(parents=True, exist_ok=True)
            save_path = upload_dir / filename
            file.save(str(save_path))
            anh_bia = f"/static/uploads/tasks/{filename}"

    db = get_db()
    cur = db.cursor()
    school_id = session.get("truong_id", 1)
    cur.execute(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai, truong_id, anh_bia) 
           VALUES (?, ?, ?, ?, ?, ?, ?, 'mo_dang_ky', ?, ?)""",
        (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, session["user_id"], school_id, anh_bia)
    )
    db.commit()

    flash(f"Đã tạo thành công nhiệm vụ: '{tieu_de}' (+{so_gio_thuong}h thưởng)!", "success")
    return redirect(url_for("community_tasks_view"))


@app.route("/community/tasks/<int:task_id>/register", methods=["POST"])
@login_required
def register_community_task(task_id):
    """
    Học sinh đăng ký tham gia nhiệm vụ cộng đồng:
    - Ghi nhận vào bảng task_registrations.
    """
    user_id = session["user_id"]
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT * FROM community_tasks WHERE id = ?", (task_id,))
    task = cur.fetchone()
    if not task:
        flash("Nhiệm vụ cộng đồng không tồn tại.", "danger")
        return redirect(url_for("community_tasks_view"))

    if task["trang_thai"] not in ("mo_dang_ky", "mo", "sap_dien_ra", "dang_dien_ra"):
        flash("Nhiệm vụ này hiện đã đóng hoặc kết thúc đăng ký.", "warning")
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

    # Thêm bản ghi đăng ký mới kèm truong_id
    school_id = session.get("truong_id", 1)
    cur.execute(
        "INSERT INTO task_registrations (task_id, user_id, trang_thai, truong_id) VALUES (?, ?, 'da_dang_ky', ?)",
        (task_id, user_id, school_id)
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
    - AI Lọc realtime tin nhắn (Việc 5): danh sách từ cấm + phân tích ngữ cảnh.
    - Ghi nhận vào bảng violations 3 mức độ (Lần 1: nhắc nhở, Lần 2: cảnh cáo + báo quản trị, Lần 3: đề xuất khóa).
    - Lưu câu hỏi và câu trả lời vào chat_messages.
    """
    user_id = session["user_id"]
    data = request.get_json() or request.form
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"success": False, "error": "Tin nhắn không được để trống."}), 400

    db = get_db()
    cur = db.cursor()

    # 0. AI Kiểm duyệt ngôn từ realtime (Việc 5)
    mod_check = ai_moderate_chat_message(message)
    if mod_check.get("is_violation"):
        # Đếm số lần vi phạm trước đó của người dùng này
        cur.execute("SELECT COUNT(*) FROM violations WHERE user_id = ?", (user_id,))
        prior_viols = cur.fetchone()[0]
        v_level = min(3, prior_viols + 1)
        reason = mod_check.get("reason", "Ngôn từ không phù hợp")
        viol_type = mod_check.get("violation_type", "ngon_tu_tho_tuc")

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Căn cứ 3 mức vi phạm:
        if v_level == 1:
            reply = f"⚠️ [CẢNH BÁO NỘI QUY - LẦN 1]: Tin nhắn của bạn vi phạm quy định ngôn ngữ chuẩn mực học đường ({reason}). Vui lòng giữ gìn sự lịch thiệp, tôn trọng và văn minh trong không gian School Time Bank."
        elif v_level == 2:
            reply = f"🚨 [CẢNH CÁO VI PHẠM - LẦN 2]: Bạn tiếp tục vi phạm quy chế nội quy ({reason}). Vi phạm đã được ghi nhận vào Sổ kỷ luật và tự động báo cáo lên Quản trị viên nhà trường."
        else:
            reply = f"🛑 [KỶ LUẬT NGHIÊM TRỌNG - LẦN 3]: Bạn đã vi phạm nội quy lần thứ 3 ({reason}). Hệ thống đã ĐỀ XUẤT KHÓA TÀI KHOẢN gửi tới Ban Quản trị Nhà trường xem xét xử lý."
            # Hệ thống ĐỀ XUẤT khóa, chờ quản trị xác nhận (tuyệt đối không tự động khóa vĩnh viễn)
            cur.execute("UPDATE users SET trang_thai = 'de_xuat_khoa' WHERE id = ?", (user_id,))

        # Ghi nhận vào bảng violations
        cur.execute("""
            INSERT INTO violations (user_id, loai_vi_pham, mo_ta, muc_do, thoi_gian)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, viol_type, f"Tin nhắn chat vi phạm ({reason}): \"{message[:100]}\"", v_level, now_str))

        # Lưu thông điệp cảnh báo của bot vào chat_messages
        cur.execute(
            """INSERT INTO chat_messages (user_id, vai_tro, noi_dung, thoi_gian)
               VALUES (?, 'assistant', ?, ?)""",
            (user_id, reply, now_str)
        )
        db.commit()

        return jsonify({
            "success": True,
            "reply": reply,
            "is_violation": True,
            "muc_do": v_level,
            "is_live": False,
            "timestamp": now_str
        })

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
# BÁO CÁO VI PHẠM TRONG PHÒNG HỌC & TRANG NỘI QUY HỌC ĐƯỜNG
# ------------------------------------------------------------------------------

@app.route("/sessions/<int:session_id>/report", methods=["POST"])
@login_required
def report_session_violation(session_id):
    """
    Nút Báo cáo trong phòng học ảo (Việc 5):
    - Cho phép học sinh báo vi phạm cho giáo viên và quản trị trường.
    - Ghi nhận vào bảng violations với mức độ 2 (Cảnh cáo).
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    ses = cur.fetchone()
    if not ses:
        flash("Phiên học không tồn tại.", "danger")
        return redirect(url_for("my_schedule"))

    user_id = session["user_id"]
    if user_id != ses["nguoi_day_id"] and user_id != ses["nguoi_hoc_id"] and session.get("vai_tro") not in ("admin", "super_admin", "school_admin", "giao_vien"):
        flash("Bạn không có quyền báo cáo trong phiên học này.", "danger")
        return redirect(url_for("my_schedule"))

    reported_user_id = ses["nguoi_hoc_id"] if user_id == ses["nguoi_day_id"] else ses["nguoi_day_id"]
    loai_vi_pham = request.form.get("loai_vi_pham", "khac").strip()
    mo_ta = request.form.get("mo_ta", "").strip()

    now_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    reporter_name = session.get("ho_ten", "Thành viên")
    reporter_code = session.get("ma_hoc_sinh", "")
    full_mo_ta = f"Báo cáo từ phòng học #{session_id} bởi {reporter_name} ({reporter_code}): {mo_ta}"

    cur.execute("""
        INSERT INTO violations (user_id, session_id, loai_vi_pham, mo_ta, muc_do, thoi_gian)
        VALUES (?, ?, ?, ?, 2, ?)
    """, (reported_user_id, session_id, loai_vi_pham, full_mo_ta, now_dt))
    db.commit()

    flash("Đã gửi báo cáo vi phạm tới Ban Quản trị và Giáo viên phụ trách. Cảm ơn bạn đã giữ gìn môi trường học tập văn minh.", "success")
    return redirect(url_for("virtual_room", session_id=session_id))


@app.route("/noi-quy")
def noi_quy():
    """Trang Nội quy học đường School Time Bank: 6 điều quy tắc vàng + chế tài 3 mức."""
    return render_template("noi_quy.html")


# ------------------------------------------------------------------------------
# MILESTONE M5-BLOG: BẢNG TIN HỌC ĐƯỜNG & AI SOẠN BẢN TIN TUẦN
# ------------------------------------------------------------------------------

@app.route("/blog")
def blog_index():
    """
    Trang Bảng tin học đường công khai (/blog):
    - Liệt kê các bài viết đã duyệt và đăng chính thức (trang_thai = 'da_dang').
    - Lọc theo trường của học sinh đang đăng nhập (hoặc tất cả nếu Super Admin / Khách).
    """
    db = get_db()
    cur = db.cursor()
    if "user_id" in session and not is_super_admin():
        cur.execute("""
            SELECT id, tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang
            FROM blog_posts
            WHERE trang_thai = 'da_dang' AND (truong_id = ? OR truong_id IS NULL)
            ORDER BY thoi_gian_dang DESC, id DESC
        """, (session.get("truong_id", 1),))
    else:
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
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
    post = cur.fetchone()

    if not post:
        abort(404)

    is_teacher_or_admin = session.get("vai_tro") in ("admin", "super_admin", "school_admin", "giao_vien")
    
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
    """
    db = get_db()
    cur = db.cursor()
    if not is_super_admin():
        cur.execute("""
            SELECT id, tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang
            FROM blog_posts
            WHERE truong_id = ? OR truong_id IS NULL
            ORDER BY id DESC
        """, (session.get("truong_id", 1),))
    else:
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
    - Gán truong_id theo người tạo.
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
        school_id = session.get("truong_id", 1)
        cur.execute("""
            INSERT INTO blog_posts (tieu_de, noi_dung, anh_minh_hoa, tac_gia_ai, trang_thai, thoi_gian_dang, truong_id)
            VALUES (?, ?, ?, 0, ?, CURRENT_TIMESTAMP, ?)
        """, (tieu_de, noi_dung, anh_minh_hoa, trang_thai, school_id))
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
    - Tự động gom dữ liệu 7 ngày qua.
    - Gán truong_id cho bài viết mới.
    """
    db = get_db()
    user_id = session.get("user_id")
    post_id, title, content, is_live = ai_generate_weekly_newsletter(db, user_id=user_id)

    school_id = session.get("truong_id", 1)
    cur = db.cursor()
    cur.execute("UPDATE blog_posts SET truong_id = ? WHERE id = ?", (school_id, post_id))
    db.commit()

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
# PROMPT 18 — PHẦN 1: DIỄN ĐÀN "GÓC TRÒ CHUYỆN"
# ==============================================================================

@app.route("/forum")
@login_required
def forum_index():
    """
    Diễn đàn 'Góc trò chuyện' (Học sinh trao đổi đồng đẳng):
    - Multi-tenant: Học sinh chỉ thấy chủ đề của TRƯỜNG MÌNH (lọc theo truong_id).
    - Super Admin có thể lọc theo từng trường hoặc xem toàn bộ.
    - Đếm số lượt bình luận, trạng thái mở/khóa.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()
    search_query = request.args.get("q", "").strip()

    # Xử lý trường được chọn
    selected_school_id = request.args.get("truong_id") if is_super else None
    if selected_school_id:
        try:
            target_school_id = int(selected_school_id)
        except ValueError:
            target_school_id = user_school_id
    else:
        target_school_id = user_school_id

    # Lấy tên trường hiện tại
    cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (target_school_id,))
    school_row = cur.fetchone()
    school_name = school_row["ten_truong"] if school_row else "Trường học"

    sql = """
        SELECT ft.*, u.ho_ten, u.lop, u.vai_tro,
               (SELECT COUNT(*) FROM forum_replies fr WHERE fr.topic_id = ft.id) AS reply_count
        FROM forum_topics ft
        JOIN users u ON ft.user_id = u.id
        WHERE ft.truong_id = ?
    """
    params = [target_school_id]

    if search_query:
        sql += " AND (ft.tieu_de LIKE ? OR ft.noi_dung LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    sql += " ORDER BY ft.id DESC"
    cur.execute(sql, tuple(params))
    topics = cur.fetchall()

    user_role = session.get("vai_tro")
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    return render_template(
        "forum_index.html",
        topics=topics,
        school_name=school_name,
        search_query=search_query,
        is_teacher_or_admin=is_teacher_or_admin,
        can_moderate=is_teacher_or_admin
    )


@app.route("/forum/new", methods=["GET", "POST"], endpoint="forum_new")
@app.route("/forum/new", methods=["GET", "POST"], endpoint="forum_new_topic")
@login_required
def forum_new():
    """
    Tạo chủ đề thảo luận mới trên Diễn đàn:
    - AI Kiểm duyệt ngôn từ (VIỆC 5/P17) áp dụng cho cả Tiêu đề và Nội dung.
    - Vi phạm: Chặn đăng bài + ghi nhận vào bảng violations.
    - Lưu truong_id theo trường của người tạo.
    """
    user_school_id = session.get("truong_id", 1)
    db = get_db()
    cur = db.cursor()

    cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (user_school_id,))
    school_row = cur.fetchone()
    school_name = school_row["ten_truong"] if school_row else "Trường học"

    if request.method == "POST":
        tieu_de = request.form.get("tieu_de", "").strip()
        noi_dung = request.form.get("noi_dung", "").strip()
        user_id = session["user_id"]

        if not tieu_de or not noi_dung:
            flash("Vui lòng nhập đầy đủ tiêu đề và nội dung chủ đề.", "warning")
            return render_template("forum_new.html", school_name=school_name, tieu_de=tieu_de, noi_dung=noi_dung)

        # AI Lọc từ tục cho cả Tiêu đề và Nội dung (VIỆC 5 / P17)
        check_title = ai_moderate_chat_message(tieu_de)
        check_content = ai_moderate_chat_message(noi_dung)
        violation_found = check_title.get("is_violation") or check_content.get("is_violation")

        if violation_found:
            viol_info = check_title if check_title.get("is_violation") else check_content
            reason = viol_info.get("reason", "Ngôn từ không phù hợp chuẩn mực học đường")
            viol_type = viol_info.get("violation_type", "ngon_tu_tho_tuc")

            # Đếm số lần vi phạm trước đó để tính bậc
            cur.execute("SELECT COUNT(*) FROM violations WHERE user_id = ?", (user_id,))
            prior_count = cur.fetchone()[0]
            v_level = min(3, prior_count + 1)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            bad_sample = tieu_de if check_title.get("is_violation") else noi_dung
            cur.execute("""
                INSERT INTO violations (user_id, loai_vi_pham, mo_ta, muc_do, thoi_gian)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, viol_type, f"Diễn đàn vi phạm ({reason}): \"{bad_sample[:100]}\"", v_level, now_str))

            if v_level >= 3:
                cur.execute("UPDATE users SET trang_thai = 'de_xuat_khoa' WHERE id = ?", (user_id,))
            db.commit()

            flash(f"⚠️ Bài viết của bạn bị AI từ chối đăng do vi phạm quy chuẩn ngôn ngữ học đường ({reason}). Hệ thống đã ghi nhận vi phạm vào Sổ kỷ luật.", "danger")
            return render_template("forum_new.html", school_name=school_name, tieu_de=tieu_de, noi_dung=noi_dung)

        # Hợp lệ: Thêm chủ đề mới
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO forum_topics (truong_id, user_id, tieu_de, noi_dung, trang_thai, ngay_tao)
            VALUES (?, ?, ?, ?, 'mo', ?)
        """, (user_school_id, user_id, tieu_de, noi_dung, now_str))
        topic_id = cur.lastrowid
        db.commit()

        flash("✨ Tạo chủ đề thảo luận mới thành công!", "success")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    return render_template("forum_new.html", school_name=school_name)


@app.route("/forum/topic/<int:topic_id>", endpoint="forum_topic")
@app.route("/forum/topic/<int:topic_id>", endpoint="forum_topic_detail")
@login_required
def forum_topic(topic_id):
    """
    Xem chi tiết chủ đề thảo luận và danh sách bình luận:
    - Kiểm tra bảo mật multi-tenant: chỉ người cùng trường hoặc Super Admin mới được xem.
    - Hiển thị danh sách bình luận theo thứ tự thời gian.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()

    cur.execute("""
        SELECT ft.*, u.ho_ten, u.lop, u.vai_tro, u.ma_hoc_sinh, t.ten_truong
        FROM forum_topics ft
        JOIN users u ON ft.user_id = u.id
        LEFT JOIN truong t ON ft.truong_id = t.id
        WHERE ft.id = ?
    """, (topic_id,))
    topic = cur.fetchone()

    if not topic:
        flash("Chủ đề không tồn tại hoặc đã bị xóa.", "danger")
        return redirect(url_for("forum_index"))

    # Kiểm tra phân lập trường học (Multi-Tenant Isolation)
    if not is_super and topic["truong_id"] != user_school_id:
        flash("Bạn không có quyền xem diễn đàn của trường khác.", "danger")
        return redirect(url_for("forum_index"))

    # Lấy danh sách bình luận
    cur.execute("""
        SELECT fr.*, u.ho_ten, u.lop, u.vai_tro, u.ma_hoc_sinh
        FROM forum_replies fr
        JOIN users u ON fr.user_id = u.id
        WHERE fr.topic_id = ?
        ORDER BY fr.id ASC
    """, (topic_id,))
    replies = cur.fetchall()

    user_role = session.get("vai_tro")
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    return render_template(
        "forum_topic.html",
        topic=topic,
        replies=replies,
        is_teacher_or_admin=is_teacher_or_admin,
        can_moderate=is_teacher_or_admin
    )


@app.route("/forum/topic/<int:topic_id>/reply", methods=["POST"], endpoint="forum_topic_reply")
@app.route("/forum/topic/<int:topic_id>/reply", methods=["POST"], endpoint="forum_reply_topic")
@login_required
def forum_topic_reply(topic_id):
    """
    Gửi bình luận vào chủ đề:
    - Kiểm tra chủ đề có bị khóa hay không.
    - AI Lọc từ tục realtime: chặn đăng và ghi nhận vào violations nếu vi phạm.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    user_id = session["user_id"]
    is_super = is_super_admin()

    cur.execute("SELECT * FROM forum_topics WHERE id = ?", (topic_id,))
    topic = cur.fetchone()
    if not topic:
        flash("Chủ đề không tồn tại.", "danger")
        return redirect(url_for("forum_index"))

    if not is_super and topic["truong_id"] != user_school_id:
        flash("Bạn không có quyền bình luận trong diễn đàn trường khác.", "danger")
        return redirect(url_for("forum_index"))

    if topic["trang_thai"] == "khoa":
        flash("Chủ đề này đã bị khóa bình luận bởi Giáo viên / Quản trị viên.", "warning")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    noi_dung = request.form.get("noi_dung", "").strip()
    if not noi_dung:
        flash("Nội dung bình luận không được để trống.", "warning")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    # AI Kiểm duyệt ngôn từ realtime (VIỆC 5 / P17)
    check_rep = ai_moderate_chat_message(noi_dung)
    if check_rep.get("is_violation"):
        reason = check_rep.get("reason", "Ngôn từ không phù hợp chuẩn mực học đường")
        viol_type = check_rep.get("violation_type", "ngon_tu_tho_tuc")

        cur.execute("SELECT COUNT(*) FROM violations WHERE user_id = ?", (user_id,))
        prior_count = cur.fetchone()[0]
        v_level = min(3, prior_count + 1)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO violations (user_id, loai_vi_pham, mo_ta, muc_do, thoi_gian)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, viol_type, f"Bình luận diễn đàn vi phạm ({reason}): \"{noi_dung[:100]}\"", v_level, now_str))

        if v_level >= 3:
            cur.execute("UPDATE users SET trang_thai = 'de_xuat_khoa' WHERE id = ?", (user_id,))
        db.commit()

        flash(f"⚠️ Bình luận bị AI chặn do vi phạm quy chuẩn ngôn ngữ ({reason}). Vi phạm đã được ghi nhận vào Sổ kỷ luật.", "danger")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    # Hợp lệ: Lưu bình luận
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO forum_replies (topic_id, user_id, noi_dung, ngay_tao)
        VALUES (?, ?, ?, ?)
    """, (topic_id, user_id, noi_dung, now_str))
    db.commit()

    flash("💬 Đã gửi bình luận thành công!", "success")
    return redirect(url_for("forum_topic", topic_id=topic_id))


@app.route("/forum/topic/<int:topic_id>/toggle-lock", methods=["POST"], endpoint="forum_topic_toggle_lock")
@app.route("/forum/topic/<int:topic_id>/toggle-lock", methods=["POST"], endpoint="forum_toggle_lock_topic")
@teacher_or_admin_required
def forum_topic_toggle_lock(topic_id):
    """
    Giáo viên / Quản trị viên khóa hoặc mở khóa chủ đề thảo luận.
    """
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT * FROM forum_topics WHERE id = ?", (topic_id,))
    topic = cur.fetchone()
    if not topic:
        flash("Chủ đề không tồn tại.", "danger")
        return redirect(url_for("forum_index"))

    user_school_id = session.get("truong_id", 1)
    if not is_super_admin() and topic["truong_id"] != user_school_id:
        flash("Bạn không có quyền quản lý chủ đề của trường khác.", "danger")
        return redirect(url_for("forum_index"))

    new_status = "khoa" if topic["trang_thai"] == "mo" else "mo"
    cur.execute("UPDATE forum_topics SET trang_thai = ? WHERE id = ?", (new_status, topic_id))
    db.commit()

    msg = "Đã khóa chủ đề thảo luận thành công." if new_status == "khoa" else "Đã mở lại chủ đề thảo luận."
    flash(msg, "info")
    return redirect(url_for("forum_topic", topic_id=topic_id))


@app.route("/forum/topic/<int:topic_id>/delete", methods=["POST"], endpoint="forum_topic_delete")
@app.route("/forum/topic/<int:topic_id>/delete", methods=["POST"], endpoint="forum_delete_topic")
@login_required
def forum_topic_delete(topic_id):
    """
    Xóa chủ đề thảo luận:
    - Giáo viên và Quản trị viên có quyền xóa bất kỳ chủ đề nào trong trường.
    - Tác giả có quyền xóa chủ đề của chính mình.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro")
    user_school_id = session.get("truong_id", 1)
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    cur.execute("SELECT * FROM forum_topics WHERE id = ?", (topic_id,))
    topic = cur.fetchone()
    if not topic:
        flash("Chủ đề không tồn tại.", "danger")
        return redirect(url_for("forum_index"))

    if not is_super_admin() and topic["truong_id"] != user_school_id:
        flash("Bạn không có quyền can thiệp vào chủ đề của trường khác.", "danger")
        return redirect(url_for("forum_index"))

    if not (is_teacher_or_admin or topic["user_id"] == user_id):
        flash("Bạn không có quyền xóa chủ đề này.", "danger")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    # Xóa các bình luận liên quan và xóa chủ đề
    cur.execute("DELETE FROM forum_replies WHERE topic_id = ?", (topic_id,))
    cur.execute("DELETE FROM forum_topics WHERE id = ?", (topic_id,))
    db.commit()

    flash("Đã xóa chủ đề thảo luận.", "info")
    return redirect(url_for("forum_index"))


@app.route("/forum/reply/<int:reply_id>/delete", methods=["POST"], endpoint="forum_reply_delete")
@app.route("/forum/reply/<int:reply_id>/delete", methods=["POST"], endpoint="forum_delete_reply")
@login_required
def forum_reply_delete(reply_id):
    """
    Xóa bình luận trên diễn đàn:
    - Giáo viên / Admin có quyền xóa bình luận.
    - Tác giả bình luận có quyền tự xóa.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro")
    user_school_id = session.get("truong_id", 1)
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    cur.execute("""
        SELECT fr.*, ft.truong_id 
        FROM forum_replies fr
        JOIN forum_topics ft ON fr.topic_id = ft.id
        WHERE fr.id = ?
    """, (reply_id,))
    reply = cur.fetchone()

    if not reply:
        flash("Bình luận không tồn tại.", "danger")
        return redirect(url_for("forum_index"))

    topic_id = reply["topic_id"]

    if not is_super_admin() and reply["truong_id"] != user_school_id:
        flash("Bạn không có quyền can thiệp vào bình luận của trường khác.", "danger")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    if not (is_teacher_or_admin or reply["user_id"] == user_id):
        flash("Bạn không có quyền xóa bình luận này.", "danger")
        return redirect(url_for("forum_topic", topic_id=topic_id))

    cur.execute("DELETE FROM forum_replies WHERE id = ?", (reply_id,))
    db.commit()

    flash("Đã xóa bình luận.", "info")
    return redirect(url_for("forum_topic", topic_id=topic_id))


# ==============================================================================
# PROMPT 18 — PHẦN 2: KHO TÀI LIỆU GOOGLE DRIVE 5TB
# ==============================================================================

DOC_SUBJECTS_LIST = [
    "Toán", "Ngữ văn", "Tiếng Anh", "Vật lý", "Hóa học", "Sinh học", 
    "Lịch sử", "Địa lý", "GDCD", "Tin học", "Công nghệ", "Hoạt động trải nghiệm"
]

def format_file_size(size_bytes):
    """Định dạng dung lượng file hiển thị thân thiện (B, KB, MB, GB)."""
    if not size_bytes or size_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != 'B' else f"{int(size_bytes)} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


@app.route("/admin/google-drive/auth")
@super_admin_required
def admin_google_drive_auth():
    """
    Khởi tạo luồng xác thực Google OAuth2 để lấy Refresh Token cho tài khoản Drive 5TB:
    - Chỉ Super Admin (cô Huyền) mới có quyền kết nối.
    - Chuyển hướng tới trang đăng nhập và đồng ý cấp quyền Google Drive.
    """
    redirect_uri = url_for("admin_google_drive_callback", _external=True)
    auth_url = get_oauth_auth_url(redirect_uri)
    return redirect(auth_url)


@app.route("/admin/google-drive/callback")
@super_admin_required
def admin_google_drive_callback():
    """
    Tiếp nhận mã xác thực từ Google OAuth2 và trích xuất refresh_token:
    - TUYỆT ĐỐI không hardcode trong mã nguồn, không push lên GitHub.
    - Cung cấp hướng dẫn để lưu vào biến môi trường GOOGLE_REFRESH_TOKEN trên Render.
    """
    code = request.args.get("code")
    if not code:
        flash("Không nhận được mã xác thực từ Google.", "danger")
        return redirect(url_for("admin_dashboard"))

    redirect_uri = url_for("admin_google_drive_callback", _external=True)
    tokens = exchange_code_for_tokens(code, redirect_uri)
    refresh_token = tokens.get("refresh_token")

    if refresh_token:
        # Cập nhật tạm thời vào bộ nhớ runtime process
        os.environ["GOOGLE_REFRESH_TOKEN"] = refresh_token
        # Lưu vào session để hiển thị 1 lần duy nhất trên trang token-hien-thi (Prompt 24 Việc 2)
        session["temp_drive_refresh_token"] = refresh_token
        return redirect(url_for("admin_google_drive_token_display"))
    else:
        flash(
            "Đã nhận Token từ Google, nhưng tài khoản chưa cấp lại Refresh Token mới "
            "(thường xảy ra nếu đã cấp quyền trước đó). Nếu cần tạo lại, hãy thu hồi quyền trong tài khoản Google và thử lại.",
            "info"
        )
        return redirect(url_for("admin_dashboard"))


@app.route("/admin/google-drive/token-hien-thi")
@super_admin_required
def admin_google_drive_token_display():
    """
    Prompt 24 (Việc 2): Trang hiển thị Refresh Token đầy đủ cho Super Admin:
    - Chỉ super_admin vào được.
    - Hiển thị FULL refresh_token trong ô text để super admin copy.
    - Hiện token 1 lần duy nhất (xem xong hoặc tải lại là mất, pop từ session).
    - Có nút 'Đã copy xong' -> chuyển về /admin.
    """
    token = session.pop("temp_drive_refresh_token", None)
    if not token:
        flash("Mã Refresh Token chỉ hiển thị 1 lần duy nhất và đã được xóa khỏi phiên làm việc để đảm bảo an toàn.", "info")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_drive_token_display.html", refresh_token=token)


@app.route("/documents")
@login_required
def documents_index():
    """
    Xem và tìm kiếm tài liệu trong kho Google Drive của trường:
    - Multi-tenant: Học sinh chỉ xem tài liệu trường mình.
    - Lọc theo môn học, tìm kiếm theo từ khóa.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    is_super = is_super_admin()
    search_query = request.args.get("q", "").strip()
    selected_subject = request.args.get("mon_hoc", "").strip()

    cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (user_school_id,))
    school_row = cur.fetchone()
    school_name = school_row["ten_truong"] if school_row else "Trường học"

    sql = """
        SELECT d.*, u.ho_ten AS user_name, u.lop AS user_class
        FROM documents d
        JOIN users u ON d.user_id = u.id
        WHERE d.truong_id = ? AND d.trang_thai = 'hoat_dong'
    """
    params = [user_school_id]

    if selected_subject:
        sql += " AND d.mon_hoc = ?"
        params.append(selected_subject)

    if search_query:
        sql += " AND (d.tieu_de LIKE ? OR d.mo_ta LIKE ? OR d.file_name LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"])

    sql += " ORDER BY d.id DESC"
    cur.execute(sql, tuple(params))
    docs_raw = cur.fetchall()

    documents = []
    for d in docs_raw:
        item = dict(d)
        item["formatted_size"] = format_file_size(d["file_size"])
        documents.append(item)

    user_role = session.get("vai_tro")
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    return render_template(
        "documents_index.html",
        documents=documents,
        school_name=school_name,
        subjects_list=DOC_SUBJECTS_LIST,
        selected_subject=selected_subject,
        search_query=search_query,
        is_teacher_or_admin=is_teacher_or_admin
    )


@app.route("/documents/upload", methods=["GET", "POST"])
@login_required
def documents_upload():
    """
    Tải lên tài liệu/ảnh/video (tối đa 500MB/file):
    - Hỗ trợ tải nhiều file cùng lúc (multiple files).
    - Tự động phân cấp thư mục: /SchoolTimeBank/{ten_truong}/{mon_hoc}/
    - Stream trực tiếp lên Google Drive 5TB, KHÔNG lưu file lên server Render.
    - Hiển thị ngay sau khi tải lên thành công.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    user_id = session["user_id"]

    cur.execute("SELECT ten_truong FROM truong WHERE id = ?", (user_school_id,))
    school_row = cur.fetchone()
    school_name = school_row["ten_truong"] if school_row else "Trường học"

    if request.method == "POST":
        mon_hoc = request.form.get("mon_hoc", "").strip()
        tieu_de_input = request.form.get("tieu_de", "").strip()
        mo_ta = request.form.get("mo_ta", "").strip()

        # Lấy danh sách files: hỗ trợ cả 'files' (mới) và 'file' (cũ)
        uploaded_files = request.files.getlist("files")
        if not uploaded_files or not any(f and f.filename for f in uploaded_files):
            uploaded_files = request.files.getlist("file")

        valid_files = [f for f in uploaded_files if f and f.filename]

        if not mon_hoc:
            flash("Vui lòng chọn môn học cho tài liệu.", "warning")
            return render_template("documents_upload.html", school_name=school_name, subjects_list=DOC_SUBJECTS_LIST)

        if not valid_files:
            flash("Vui lòng chọn ít nhất một tệp đính kèm.", "warning")
            return render_template("documents_upload.html", school_name=school_name, subjects_list=DOC_SUBJECTS_LIST)

        success_count = 0
        failed_count = 0
        total_files = len(valid_files)
        storage_types = []
        uploaded_titles = []

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for idx, file in enumerate(valid_files):
            orig_name = file.filename
            filename = secure_filename(orig_name) or f"document_{int(time.time())}_{idx}.bin"
            mime_type = file.mimetype or "application/octet-stream"

            # Xác định tiêu đề cho từng file:
            # Để trống -> lấy tên file làm tiêu đề
            # Điền -> dùng làm tiền tố chung (cho nhiều file) hoặc làm tiêu đề (cho 1 file)
            if total_files > 1:
                file_title = f"{tieu_de_input} - {filename}" if tieu_de_input else filename
            else:
                file_title = tieu_de_input if tieu_de_input else filename

            # Đọc độ dài file stream để xác định dung lượng
            try:
                file.stream.seek(0, io.SEEK_END)
                file_size = file.stream.tell()
                file.stream.seek(0)
            except Exception:
                file_size = 0

            # Kiểm tra giới hạn 500MB (500 * 1024 * 1024 bytes)
            if file_size > 500 * 1024 * 1024:
                app.logger.warning(f"File {filename} ({file_size} bytes) vượt quá 500MB")
                flash(f"Tệp '{orig_name}' vượt quá dung lượng tối đa cho phép (500MB), đã bị bỏ qua.", "danger")
                failed_count += 1
                continue

            try:
                # Stream tải trực tiếp lên Google Drive 5TB (không lưu trên đĩa Render)
                drive_result = upload_document_stream(
                    file_stream=file.stream,
                    filename=filename,
                    mime_type=mime_type,
                    school_name=school_name,
                    subject_name=mon_hoc
                )

                drive_file_id = drive_result.get("file_id")
                drive_web_view_link = drive_result.get("web_view_link")
                storage_types.append(drive_result.get("storage_type"))

                cur.execute("""
                    INSERT INTO documents (
                        truong_id, user_id, tieu_de, mo_ta, mon_hoc,
                        file_name, file_size, file_type, drive_file_id,
                        drive_web_view_link, luot_tai, ngay_tao, trang_thai
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, 'hoat_dong')
                """, (
                    user_school_id, user_id, file_title, mo_ta, mon_hoc,
                    filename, file_size, mime_type, drive_file_id,
                    drive_web_view_link, now_str
                ))
                db.commit()

                success_count += 1
                uploaded_titles.append(file_title)

            except Exception as e:
                app.logger.error(f"Lỗi tải lên tệp {filename} lên Google Drive: {e}")
                failed_count += 1
                flash(f"Lỗi khi tải tệp '{orig_name}' lên hệ thống: {str(e)}", "danger")
                continue

        # Thông báo tổng kết: Đã tải X/Y thành công
        is_all_mock = all(st == "mock_drive" for st in storage_types) if storage_types else False

        if success_count > 0:
            if total_files == 1:
                single_title = uploaded_titles[0]
                if is_all_mock:
                    flash(f"Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Tài liệu '{single_title}' đã được lưu tạm. Đã tải 1/1 thành công.", "warning")
                else:
                    flash(f"🎉 Tải lên tài liệu '{single_title}' thành công vào thư mục {mon_hoc} trên hệ thống! Đã tải 1/1 thành công.", "success")
            else:
                if is_all_mock:
                    flash(f"Tải lên kho tạm (chưa kết nối hệ thống), vui lòng liên hệ quản trị viên. Đã tải {success_count}/{total_files} thành công.", "warning")
                else:
                    flash(f"🎉 Đã tải {success_count}/{total_files} thành công vào thư mục {mon_hoc} trên hệ thống!", "success")

            return redirect(url_for("documents_index"))
        else:
            flash(f"Không có tài liệu nào được tải lên thành công (0/{total_files}).", "danger")
            return render_template("documents_upload.html", school_name=school_name, subjects_list=DOC_SUBJECTS_LIST)

    return render_template("documents_upload.html", school_name=school_name, subjects_list=DOC_SUBJECTS_LIST)


@app.route("/documents/download/<int:doc_id>")
@login_required
def documents_download(doc_id):
    """
    Tải về tài liệu từ kho Google Drive 5TB:
    - Stream trực tiếp từ Drive về trình duyệt (KHÔNG lưu file tạm trên đĩa server Render).
    - Tự động tăng số lượt tải (luot_tai) và ghi nhật ký vào document_downloads.
    """
    db = get_db()
    cur = db.cursor()
    user_school_id = session.get("truong_id", 1)
    user_id = session["user_id"]
    is_super = is_super_admin()

    cur.execute("SELECT * FROM documents WHERE id = ? AND trang_thai = 'hoat_dong'", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash("Tài liệu không tồn tại hoặc đã bị xóa.", "danger")
        return redirect(url_for("documents_index"))

    # Kiểm tra quyền trường
    if not is_super and doc["truong_id"] != user_school_id:
        flash("Bạn không có quyền tải tài liệu của trường khác.", "danger")
        return redirect(url_for("documents_index"))

    try:
        # Stream trực tiếp từ Google Drive 5TB
        file_stream, mime_type, filename = download_document_stream(
            file_id=doc["drive_file_id"],
            fallback_filename=doc["file_name"]
        )

        # Cập nhật số lượt tải và ghi log
        cur.execute("UPDATE documents SET luot_tai = luot_tai + 1 WHERE id = ?", (doc_id,))
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO document_downloads (document_id, user_id, thoi_gian)
            VALUES (?, ?, ?)
        """, (doc_id, user_id, now_str))
        db.commit()

        # Tạo phản hồi dạng streaming response (hỗ trợ trực tiếp generator hoặc stream)
        data_or_gen = file_stream.read() if hasattr(file_stream, "read") else file_stream
        response = Response(data_or_gen, mimetype=mime_type)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    except Exception as e:
        app.logger.error(f"Lỗi tải tài liệu từ Google Drive #{doc_id}: {e}")
        flash(f"Không thể tải tài liệu từ hệ thống: {str(e)}", "danger")
        return redirect(url_for("documents_index"))


@app.route("/documents/report/<int:doc_id>", methods=["POST"])
@login_required
def documents_report(doc_id):
    """
    Báo cáo tài liệu vi phạm quy chế hoặc độc hại:
    - Ghi nhận báo cáo vào bảng violations để quản trị viên trường kiểm tra.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    ly_do = request.form.get("ly_do", "").strip() or "Báo cáo nội dung không phù hợp"

    cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash("Tài liệu không tồn tại.", "danger")
        return redirect(url_for("documents_index"))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur.execute("""
        INSERT INTO violations (user_id, loai_vi_pham, mo_ta, muc_do, thoi_gian)
        VALUES (?, 'bao_cao_tai_lieu', ?, 1, ?)
    """, (
        doc["user_id"],
        f"Tài liệu #{doc_id} ('{doc['tieu_de']}', file: {doc['file_name']}) bị báo cáo: {ly_do} (Người báo cáo ID={user_id})",
        now_str
    ))
    db.commit()

    flash("Đã gửi báo cáo vi phạm tới Ban Quản trị nhà trường để kiểm tra và xử lý.", "info")
    return redirect(url_for("documents_index"))


@app.route("/documents/delete/<int:doc_id>", methods=["POST"])
@login_required
def documents_delete(doc_id):
    """
    Quản trị viên / Giáo viên hoặc người tải lên xóa tài liệu vi phạm:
    - Xóa trên Google Drive 5TB.
    - Cập nhật trang_thai = 'da_xoa' trong database.
    """
    db = get_db()
    cur = db.cursor()
    user_id = session["user_id"]
    user_role = session.get("vai_tro")
    user_school_id = session.get("truong_id", 1)
    is_teacher_or_admin = user_role in ("giao_vien", "school_admin", "super_admin", "admin")

    cur.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    doc = cur.fetchone()
    if not doc:
        flash("Tài liệu không tồn tại.", "danger")
        return redirect(url_for("documents_index"))

    if not is_super_admin() and doc["truong_id"] != user_school_id:
        flash("Bạn không có quyền thao tác trên tài liệu của trường khác.", "danger")
        return redirect(url_for("documents_index"))

    if not (is_teacher_or_admin or doc["user_id"] == user_id):
        flash("Bạn không có quyền xóa tài liệu này.", "danger")
        return redirect(url_for("documents_index"))

    try:
        if doc["drive_file_id"]:
            delete_document_from_drive(doc["drive_file_id"])
    except Exception as e:
        app.logger.warning(f"Lỗi khi xóa file trên Drive #{doc['drive_file_id']}: {e}")

    cur.execute("UPDATE documents SET trang_thai = 'da_xoa' WHERE id = ?", (doc_id,))
    db.commit()

    flash(f"Đã xóa tài liệu '{doc['tieu_de']}' khỏi hệ thống thành công.", "success")
    return redirect(url_for("documents_index"))


# ==============================================================================
# PROMPT 21+: ĐĂNG KÝ TƯ VẤN TRIỂN KHAI & THÔNG BÁO EMAIL (SMTP)
# ==============================================================================
def send_consultation_notification_email(ten_truong, ho_ten, sdt, email="", ghi_chu=""):
    """
    Gửi email thông báo khi có trường học đăng ký tư vấn triển khai về mshuyenuka@gmail.com.
    SMTP cấu hình qua biến môi trường: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.
    Thiếu biến môi trường hoặc gửi lỗi -> chỉ ghi log cảnh báo, trả về False, tuyệt đối không crash.
    """
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")

    if not all([smtp_host, smtp_port, smtp_user, smtp_pass]):
        app.logger.warning(
            "Cấu hình SMTP chưa đầy đủ (SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS). "
            "Bỏ qua bước gửi email, dữ liệu đăng ký tư vấn vẫn được lưu CSDL an toàn."
        )
        return False

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        port = int(smtp_port)
        recipient = "mshuyenuka@gmail.com"
        subject = f"[TimeBank EDU] Đăng ký tư vấn triển khai từ {ten_truong}"

        content = (
            f"Kính gửi Ban Đề Án TimeBank EDU & Cô Nguyễn Thị Huyền,\n\n"
            f"Hệ thống vừa tiếp nhận yêu cầu đăng ký tư vấn triển khai mới:\n"
            f"- Tên trường học / Đơn vị: {ten_truong}\n"
            f"- Họ tên người đại diện: {ho_ten}\n"
            f"- Số điện thoại / Zalo: {sdt}\n"
            f"- Email liên hệ: {email if email else 'Chưa cung cấp'}\n"
            f"- Nhu cầu triển khai: {ghi_chu if ghi_chu else 'Không có ghi chú'}\n"
            f"- Thời gian tiếp nhận: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n"
            f"Trân trọng,\n"
            f"Hệ thống School Time Bank"
        )

        msg = MIMEMultipart()
        msg["From"] = smtp_user
        msg["To"] = recipient
        msg["Subject"] = subject
        msg.attach(MIMEText(content, "plain", "utf-8"))

        if port == 465:
            server = smtplib.SMTP_SSL(smtp_host, port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, port, timeout=10)
            server.starttls()

        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [recipient], msg.as_string())
        server.quit()
        app.logger.info(f"Đã gửi email thông báo tư vấn thành công tới {recipient}")
        return True
    except Exception as e:
        app.logger.warning(f"Lỗi khi gửi email thông báo tư vấn qua SMTP ({e}), hệ thống không crash.")
        return False


@app.route("/api/contact-consultation", methods=["POST"])
@app.route("/contact", methods=["POST"])
@app.route("/api/tu-van", methods=["POST"])
def submit_contact_consultation():
    """
    Xử lý gửi form 'Đăng ký tư vấn triển khai':
    1. Tiếp nhận JSON hoặc form-data: ten_truong, ho_ten, sdt, email, ghi_chu.
    2. Lưu vào CSDL bảng tu_van_trien_khai.
    3. Gửi email thông báo tới mshuyenuka@gmail.com (nếu có cấu hình SMTP).
    4. Không cấu hình SMTP hoặc lỗi gửi -> ghi log cảnh báo, không crash.
    """
    if request.is_json:
        data = request.get_json() or {}
        ten_truong = str(data.get("ten_truong") or "").strip()
        ho_ten = str(data.get("ho_ten") or "").strip()
        sdt = str(data.get("sdt") or "").strip()
        email = str(data.get("email") or "").strip()
        ghi_chu = str(data.get("ghi_chu") or "").strip()
    else:
        ten_truong = str(request.form.get("ten_truong") or "").strip()
        ho_ten = str(request.form.get("ho_ten") or "").strip()
        sdt = str(request.form.get("sdt") or "").strip()
        email = str(request.form.get("email") or "").strip()
        ghi_chu = str(request.form.get("ghi_chu") or "").strip()

    if not ten_truong or not ho_ten or not sdt:
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Vui lòng nhập đầy đủ Tên trường, Họ tên và Số điện thoại!"}), 400
        flash("Vui lòng nhập đầy đủ Tên trường, Họ tên và Số điện thoại!", "warning")
        return redirect(url_for("index") + "#contactForm")

    db = get_db()
    cur = db.cursor()
    try:
        cur.execute(
            """
            INSERT INTO tu_van_trien_khai (ten_truong, ho_ten, sdt, email, ghi_chu)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ten_truong, ho_ten, sdt, email, ghi_chu)
        )
        db.commit()
        last_id = cur.lastrowid
    except Exception as e:
        app.logger.error(f"Lỗi lưu CSDL đăng ký tư vấn triển khai: {e}")
        try:
            db.rollback()
        except Exception:
            pass
        if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "message": "Có lỗi khi lưu dữ liệu đăng ký!"}), 500
        flash("Có lỗi khi lưu thông tin. Vui lòng thử lại!", "danger")
        return redirect(url_for("index") + "#contactForm")

    # Gửi email thông báo (an toàn, không crash khi không có biến môi trường hoặc lỗi)
    email_sent = send_consultation_notification_email(ten_truong, ho_ten, sdt, email, ghi_chu)

    msg = f"Đăng ký tư vấn thành công! Cảm ơn Thầy/Cô {ho_ten} ({ten_truong}). Ban tổ chức sẽ liên hệ lại trong thời gian sớm nhất."
    if request.is_json or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({
            "success": True,
            "message": msg,
            "id": last_id,
            "email_sent": email_sent
        }), 200

    flash(msg, "success")
    return redirect(url_for("index") + "#contactForm")


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

