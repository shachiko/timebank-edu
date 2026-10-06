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
import sqlite3
import yaml
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, g, flash, redirect, url_for

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
def inject_school_config():
    """
    Tự động truyền biến 'config' vào tất cả các giao diện HTML (Jinja2 Template).
    Nhờ hàm này, mọi trang web đều đọc được 'config.ten_truong', 'config.mau_chu_dao', v.v.
    """
    return {"config": load_school_config()}


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
    Khởi tạo cấu trúc cơ sở dữ liệu (10 bảng) từ file database/schema.sql.
    Đồng thời tự động nạp dữ liệu mẫu ban đầu nếu hệ thống chưa có dữ liệu,
    đảm bảo khi giám khảo chấm thi thì hệ thống hoạt động đầy đủ ngay.
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
    - 5 học sinh tiêu biểu (An, Bình, Chi, Minh, Hà) và 1 giáo viên phụ trách
    - Các kỹ năng đăng ký (Toán, Guitar, Tiếng Anh, Tin học...)
    - Các phiên học hoàn thành thể hiện vòng tròn tuần hoàn thời gian
    - Nhật ký sổ cái tín dụng (credits_ledger) và đánh giá sao (ratings)
    """
    cur = conn.cursor()
    
    # 1. Thêm người dùng mẫu (có thêm trường gio_ranh)
    users = [
        ('HS12001', 'Nguyễn Hoàng An', '12A1', 'hoc_sinh', 3.5, 'Chiều thứ 3, sáng thứ 7'),
        ('HS11002', 'Trần Thanh Bình', '11B2', 'hoc_sinh', 2.5, 'Sáng Chủ nhật, tối thứ 5'),
        ('HS10003', 'Lê Kim Chi', '10A3', 'hoc_sinh', 3.0, 'Chiều thứ 6, sáng Chủ nhật'),
        ('HS11004', 'Phạm Quang Minh', '11A1', 'hoc_sinh', 2.0, 'Tối thứ 2, tối thứ 4'),
        ('HS12005', 'Vũ Thu Hà', '12D2', 'hoc_sinh', 2.0, 'Sáng thứ 7, chiều Chủ nhật'),
        ('GV001', 'Thầy Nguyễn Văn Đức', 'Tổ Toán - Tin', 'giao_vien', 10.0, 'Các buổi chiều trong tuần'),
        ('ADMIN01', 'Quản trị viên Nhà trường', 'BGH', 'admin', 100.0, 'Toàn thời gian')
    ]
    cur.executemany(
        "INSERT INTO users (ma_hoc_sinh, ho_ten, lop, vai_tro, so_du_gio, gio_ranh) VALUES (?, ?, ?, ?, ?, ?)",
        users
    )
    
    # 2. Thêm kỹ năng chia sẻ
    skills = [
        (1, 'Toán học', 'Ôn tập Hình học không gian lớp 12', 'Phương pháp giải nhanh trắc nghiệm khoảng cách và góc', 'da_duyet', 'Nội dung bổ ích, phù hợp chương trình'),
        (2, 'Năng khiếu', 'Đệm hát Guitar cơ bản cho người mới', 'Cách bấm các hợp âm chuẩn và kỹ thuật quạt chả điệu Disco', 'da_duyet', 'Kỹ năng giải trí tích cực'),
        (3, 'Ngoại ngữ', 'Luyện phản xạ nói Tiếng Anh IELTS Speaking', 'Chiến thuật trả lời Part 1 và Part 2 tự nhiên, lưu loát', 'da_duyet', 'Rất hữu ích cho học sinh hội nhập'),
        (4, 'Tin học', 'Lập trình Python cho người mới bắt đầu', 'Cấu trúc rẽ nhánh, vòng lặp và xử lý chuỗi căn bản', 'da_duyet', 'Định hướng chuyển đổi số trường học'),
        (5, 'Khoa học', 'Phương pháp làm bài thí nghiệm Hóa học 12', 'Giải thích hiện tượng và mẹo nhớ tính chất kim loại kiềm', 'da_duyet', 'Hỗ trợ ôn thi tốt nghiệp')
    ]
    cur.executemany(
        "INSERT INTO skills (user_id, linh_vuc, tieu_de, mo_ta, trang_thai_duyet, ly_do_ai_kiem_duyet) VALUES (?, ?, ?, ?, ?, ?)",
        skills
    )
    
    # 3. Thêm các phiên học hoàn thành thực tế (Sessions) - có quiz_dat_chuan
    # Session 1: An dạy Toán cho Bình (1.0 giờ)
    # Session 2: Bình dạy Đàn cho Chi (1.0 giờ)
    # Session 3: Chi dạy Tiếng Anh cho An (1.0 giờ)
    # Session 4: An dạy Toán cho Minh (1.0 giờ)
    # Session 5: Minh dạy Python cho Hà (1.0 giờ)
    sessions = [
        (1, 1, 2, '2026-09-28 14:00:00', 1.0, 'hoan_thanh', 'QR_SES_001', 1, 1, 'Dàn ý AI: Khái niệm góc giữa hai mặt phẳng + 3 bài tập mẫu', 1),
        (2, 2, 3, '2026-09-29 15:30:00', 1.0, 'hoan_thanh', 'QR_SES_002', 1, 1, 'Dàn ý AI: Hợp âm C-Am-Dm-G7 + bài tập bấm tay', 1),
        (3, 3, 1, '2026-10-01 16:00:00', 1.0, 'hoan_thanh', 'QR_SES_003', 1, 1, 'Dàn ý AI: Chủ đề Hometown & Hobbies', 1),
        (1, 1, 4, '2026-10-03 09:00:00', 1.0, 'hoan_thanh', 'QR_SES_004', 1, 1, 'Dàn ý AI: Góc giữa đường thẳng và mặt phẳng', 1),
        (4, 4, 5, '2026-10-04 14:30:00', 1.0, 'hoan_thanh', 'QR_SES_005', 1, 1, 'Dàn ý AI: Biến số và lệnh input/print trong Python', 1)
    ]
    cur.executemany(
        """INSERT INTO sessions 
           (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc, dan_y_ai, quiz_dat_chuan) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        sessions
    )
    
    # 4. Ghi sổ cái tín dụng (credits_ledger) - Nguyên tắc chỉ Insert
    ledger_entries = [
        (1, 1.0, 'Dạy Toán cho Trần Thanh Bình', 1, '2026-09-28 15:00:00'),
        (2, -1.0, 'Học Toán từ Nguyễn Hoàng An', 1, '2026-09-28 15:00:00'),
        (2, 1.0, 'Dạy Đàn cho Lê Kim Chi', 2, '2026-09-29 16:30:00'),
        (3, -1.0, 'Học Đàn từ Trần Thanh Bình', 2, '2026-09-29 16:30:00'),
        (3, 1.0, 'Dạy Tiếng Anh cho Nguyễn Hoàng An', 3, '2026-10-01 17:00:00'),
        (1, -1.0, 'Học Tiếng Anh từ Lê Kim Chi', 3, '2026-10-01 17:00:00'),
        (1, 1.0, 'Dạy Toán cho Phạm Quang Minh', 4, '2026-10-03 10:00:00'),
        (4, -1.0, 'Học Toán từ Nguyễn Hoàng An', 4, '2026-10-03 10:00:00'),
        (4, 1.0, 'Dạy Python cho Vũ Thu Hà', 5, '2026-10-04 15:30:00'),
        (5, -1.0, 'Học Python từ Phạm Quang Minh', 5, '2026-10-04 15:30:00'),
        (1, 2.0, 'nhiem_vu_cong_dong: Hỗ trợ số hóa tài liệu thư viện', None, '2026-10-05 11:00:00')
    ]
    cur.executemany(
        "INSERT INTO credits_ledger (user_id, bien_dong, ly_do, session_id, thoi_gian) VALUES (?, ?, ?, ?, ?)",
        ledger_entries
    )
    
    # 5. Thêm đánh giá chất lượng (ratings)
    ratings = [
        (1, 2, 1, 5, 'Anh An giảng Toán rất dễ hiểu, giải thích bài tập góc không gian siêu hay!'),
        (2, 3, 2, 5, 'Bình dạy đàn kiên nhẫn, chỉ cách chuyển hợp âm rất dễ nhớ.'),
        (3, 1, 3, 5, 'Chi phát âm chuẩn, sửa lỗi ngữ điệu cho mình rất nhiệt tình.'),
        (4, 4, 1, 5, 'Buổi học rất bổ ích, mình đã tự tin làm được bài kiểm tra.'),
        (5, 5, 4, 4, 'Minh chỉ code dễ hiểu, mong có thêm buổi học tiếp theo.')
    ]
    cur.executemany(
        """INSERT INTO ratings 
           (session_id, nguoi_danh_gia_id, nguoi_duoc_danh_gia_id, so_sao, nhan_xet) 
           VALUES (?, ?, ?, ?, ?)""",
        ratings
    )
    
    # 6. Ghi nhật ký AI minh bạch (ai_logs) - bao gồm goi_y_nhiem_vu, tro_ly_ao
    ai_logs = [
        (1, 'dan_y_buoi_hoc', 'Soạn dàn ý buổi học Toán Hình học 12', 'Đã sinh cấu trúc 3 phần: Lý thuyết định nghĩa, bài tập mẫu và mẹo giải nhanh.', '2026-09-28 13:50:00'),
        (2, 'dan_y_buoi_hoc', 'Soạn dàn ý hướng dẫn đệm đàn Guitar', 'Đã sinh danh sách hợp âm C, Am, Dm, G7 và bài tập bấm gam.', '2026-09-29 15:10:00'),
        (3, 'kiem_duyet', 'Kiểm duyệt nội dung chia sẻ kỹ năng tiếng Anh', 'Nội dung giáo dục an toàn, tích cực, không vi phạm chuẩn mực sư phạm.', '2026-10-01 10:00:00'),
        (1, 'goi_y_nhiem_vu', 'Gợi ý nhiệm vụ cộng đồng phù hợp học sinh', 'Đã đề xuất nhiệm vụ hỗ trợ số hóa sách thư viện dựa trên kỹ năng tin học.', '2026-10-05 08:30:00'),
        (1, 'tro_ly_ao', 'Tư vấn lộ trình trao đổi kỹ năng học đường', 'Trợ lý ảo đã giải đáp thắc mắc về quy chế tín dụng thời gian cho học sinh.', '2026-10-05 09:15:00')
    ]
    cur.executemany(
        "INSERT INTO ai_logs (user_id, chuc_nang, input_tom_tat, output_text, thoi_gian) VALUES (?, ?, ?, ?, ?)",
        ai_logs
    )

    # 7. Thêm nhiệm vụ cộng đồng mẫu (community_tasks)
    community_tasks = [
        ('Hỗ trợ số hóa tài liệu thư viện trường', 'Quét và phân loại sách tham khảo vào hệ thống thư viện điện tử', 'Phòng Thư viện - Tầng 2', 2.0, 4, '2026-10-15', 6, 'mo', '2026-10-05 08:00:00'),
        ('Phụ đạo Tin học văn phòng cho CLB Học tập', 'Hướng dẫn trình bày slide và bảng tính Excel căn bản', 'Phòng máy số 3', 1.5, 3, '2026-10-20', 6, 'mo', '2026-10-05 09:00:00')
    ]
    cur.executemany(
        """INSERT INTO community_tasks 
           (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai, thoi_gian_tao) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        community_tasks
    )

    # 8. Thêm đăng ký nhiệm vụ cộng đồng (task_registrations)
    task_regs = [
        (1, 1, 'da_duyet', '2026-10-05 08:45:00')
    ]
    cur.executemany(
        "INSERT INTO task_registrations (task_id, user_id, trang_thai, thoi_gian_dang_ky) VALUES (?, ?, ?, ?)",
        task_regs
    )

    # 9. Thêm tin nhắn Trợ lý ảo (chat_messages)
    chat_samples = [
        (1, 'user', 'Em muốn học thêm kỹ năng giao tiếp tiếng Anh thì nên tìm bạn nào?', '2026-10-01 09:00:00'),
        (1, 'assistant', 'Chào An! Dựa trên hệ thống, bạn Lê Kim Chi (10A3) đang chia sẻ kỹ năng Luyện phản xạ IELTS Speaking rất phù hợp với em nhé!', '2026-10-01 09:00:05')
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
    
    # 1. Tổng số thành viên
    cur.execute("SELECT COUNT(*) FROM users WHERE vai_tro IN ('hoc_sinh', 'giao_vien')")
    tong_thanh_vien = cur.fetchone()[0]
    
    # 2. Số phiên học đã hoàn thành
    cur.execute("SELECT COUNT(*) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    phien_hoan_thanh = cur.fetchone()[0]
    
    # 3. Tổng số giờ lưu thông (tính từ các phiên đã hoàn thành)
    cur.execute("SELECT COALESCE(SUM(so_gio), 0.0) FROM sessions WHERE trang_thai = 'hoan_thanh'")
    gio_luu_thong = cur.fetchone()[0]
    
    # 4. Kỹ năng sẵn sàng trao đổi
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
    Bao gồm 6 khối chính:
    1. Hero Banner: Logo, tên trường, khẩu hiệu sư phạm, nút tham gia
    2. Mô hình hoạt động: 4 bước chuẩn sư phạm + ví dụ minh họa An - Bình - Chi
    3. Số liệu realtime: Chỉ số thực tế trích xuất trực tiếp từ SQLite
    4. Vinh danh tuần: Top 3 học sinh có giờ dạy cao nhất
    5. Dành cho nhà trường: Triết lý Single-Tenant & Form đăng ký tư vấn
    6. Footer: Thông tin trường, bản quyền và xác thực "Hỗ trợ bởi AI (Gemini)"
    """
    db = get_db()
    stats = get_realtime_stats(db)
    top_tutors = get_top_tutors(db, limit=3)
    
    return render_template(
        "index.html",
        stats=stats,
        top_tutors=top_tutors
    )


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
    print("=" * 70)
    
    # Khởi chạy Flask Server trên cổng 5000
    app.run(host="0.0.0.0", port=5000, debug=True)
