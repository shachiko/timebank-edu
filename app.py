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
import time
import base64
import secrets
import sqlite3
import yaml
import qrcode
from pathlib import Path
from functools import wraps
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from flask import (
    Flask, render_template, request, jsonify, g, flash, redirect, url_for, session, abort
)

# 1. Tải các biến môi trường từ file .env (nếu có)
# Lưu ý: File .env chứa API Key tuyệt đối không được đưa lên GitHub
load_dotenv()

# Đường dẫn thư mục gốc dự án
BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "database" / "timebank.db"
SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"
CONFIG_PATH = BASE_DIR / "config.yaml"

# Khởi tạo ứng dụng Flask
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "timebank-edu-secret-key-2026")


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
        "ten_truong": "THPT Chuyên Thực Nghiệm Sáng Tạo",
        "logo_path": "/static/img/logo.svg",
        "mau_chu_dao": "#1e40af",
        "email_lien_he": "lienhe@timebank-edu.vn",
        "dong_gioi_thieu": "Nền tảng Ngân hàng Thời gian Học đường — Trao đổi kỹ năng bằng tín dụng thời gian."
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
# QUẢN LÝ KẾT NỐI VÀ KHỞI TẠO CƠ SỞ DỮ LIỆU SQLITE
# ==============================================================================
def get_db():
    """
    Mở kết nối tới cơ sở dữ liệu SQLite cục bộ cho mỗi request.
    Sử dụng sqlite3.Row để dễ dàng truy xuất các cột theo tên.
    """
    if "db" not in g:
        g.db = sqlite3.connect(
            DATABASE_PATH,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
        # Kích hoạt tính năng kiểm tra khóa ngoại (Foreign Keys) trong SQLite
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
    Khởi tạo cấu trúc cơ sở dữ liệu (13 bảng) từ file database/schema.sql.
    Đồng thời tự động nạp dữ liệu mẫu ban đầu nếu hệ thống chưa có dữ liệu,
    bao gồm tài khoản quản trị sẵn: admin/admin123.
    """
    # Đảm bảo thư mục database tồn tại
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
        
    conn.commit()
    
    # Kiểm tra xem đã có dữ liệu người dùng mẫu chưa, nếu chưa thì nạp dữ liệu ban đầu
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
        (7, 'Khoa học', 'Phương pháp làm bài thí nghiệm Hóa học 12', 'Giải thích hiện tượng và mẹo nhớ tính chất kim loại kiềm', 'cho_duyet', 'Chờ giáo viên bộ môn duyệt nội dung')
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
        ('Hỗ trợ số hóa tài liệu thư viện trường', 'Quét và phân loại sách tham khảo vào hệ thống thư viện điện tử', 'Phòng Thư viện - Tầng 2', 2.0, 4, '2026-10-15', 2, 'mo', '2026-10-05 08:00:00'),
        ('Phụ đạo Tin học văn phòng cho CLB Học tập', 'Hướng dẫn trình bày slide và bảng tính Excel căn bản', 'Phòng máy số 3', 1.5, 3, '2026-10-20', 2, 'mo', '2026-10-05 09:00:00')
    ]
    cur.executemany(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai, thoi_gian_tao) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        community_tasks
    )

    # 8. Thêm đăng ký nhiệm vụ cộng đồng (task_registrations)
    task_regs = [
        (1, 3, 'da_duyet', '2026-10-05 08:45:00')
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
    
    conn.commit()


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
    
    cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro IN ('hoc_sinh', 'giao_vien')")
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
        GROUP BY u.id
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
    Gồm 6 khối chức năng sư phạm hoàn chỉnh.
    """
    db = get_db()
    stats = get_realtime_stats(db)
    top_tutors = get_top_tutors(db, limit=3)
    
    return render_template(
        "index.html",
        stats=stats,
        top_tutors=top_tutors
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

    return render_template(
        "profile.html",
        user=user,
        ledger_entries=ledger_entries,
        my_skills=my_skills
    )


@app.route("/admin")
@admin_required
def admin_dashboard():
    """
    Bảng điều khiển Quản trị hệ thống (/admin):
    - CHỈ ADMIN mới có quyền truy cập. Học sinh và giáo viên bị chặn 403 Forbidden.
    - Thống kê toàn trường: người dùng, số học sinh mở sổ, tổng giờ lưu thông
    - Quản lý danh sách tài khoản người dùng
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

    return render_template(
        "admin.html",
        users=all_users,
        student_count=student_count,
        total_credits=total_credits,
        pending_skills_count=pending_skills_count
    )


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
        
    sql += " GROUP BY s.id ORDER BY s.id DESC"
    cur.execute(sql, params)
    skills = cur.fetchall()
    
    return render_template(
        "skills_market.html",
        skills=skills,
        search_query=search_query,
        selected_category=selected_category
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
        
        cur.execute(
            """INSERT INTO skills 
               (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet) 
               VALUES (?, ?, ?, ?, 'cho_duyet', ?)""",
            (session["user_id"], linh_vuc, tieu_de, mo_ta, "Nội dung học tập tích cực, chờ giáo viên phê duyệt")
        )
        db.commit()
        
        flash("Đăng ký kỹ năng thành công! Kỹ năng đang ở trạng thái 'Chờ duyệt' trước khi hiển thị trên Chợ kỹ năng.", "success")
        return redirect(url_for("profile"))
        
    return render_template("skills_new.html")


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
        
    # Tạo mã QR dạng Base64 để hiển thị trực quan
    qr_b64 = generate_qr_base64(session_data["ma_qr"] or f"TB-SES-{session_id}")
    
    return render_template(
        "session_detail.html",
        session_data=session_data,
        qr_b64=qr_b64,
        is_teacher=is_teacher,
        is_learner=is_learner,
        is_admin=is_admin
    )


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
    # Tự động khởi tạo database nếu chưa có tệp database/timebank.db
    init_db()
    
    config = load_school_config()
    print("=" * 70)
    print("🏫 TIMEBANK EDU - NGÂN HÀNG THỜI GIAN HỌC ĐƯỜNG")
    print(f"📍 Đơn vị: {config.get('ten_truong')}")
    print("🚀 Máy chủ đang khởi động tại: http://127.0.0.1:5000")
    print("🔑 Tài khoản quản trị mặc định: admin / admin123")
    print("=" * 70)
    
    # Khởi chạy Flask Server trên cổng 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
