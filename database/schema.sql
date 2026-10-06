-- ==============================================================================
-- DỰ ÁN DỰ THI: NGÂN HÀNG THỜI GIAN HỌC ĐƯỜNG (TIMEBANK EDU)
-- NGÀY HỘI NHÀ GIÁO SÁNG TẠO VỚI CÔNG NGHỆ SỐ VÀ AI 2026 - BẢNG B
-- CẤU TRÚC CƠ SỞ DỮ LIỆU SQLITE (13 BẢNG CHUẨN ĐÚNG THEO ĐẶC TẢ KIẾN TRÚC M0 + M0-BS)
-- ==============================================================================

-- 1. BẢNG NGƯỜI DÙNG: Lưu thông tin học sinh, giáo viên phụ trách, ban quản trị
-- Mọi thành viên mới tham gia đều được cấp vốn ban đầu là 2.0 giờ tín dụng
-- gio_ranh: Lưu thời gian rảnh biểu kiến phục vụ AI gợi ý ghép cặp
-- mat_khau: Lưu chuỗi băm bảo mật (hashed password) qua werkzeug.security
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ma_hoc_sinh TEXT UNIQUE NOT NULL,
    ho_ten TEXT NOT NULL,
    lop TEXT,
    vai_tro TEXT CHECK(vai_tro IN ('hoc_sinh', 'giao_vien', 'admin')) DEFAULT 'hoc_sinh',
    so_du_gio REAL DEFAULT 2.0,
    gio_ranh TEXT,
    mat_khau TEXT
);

-- 2. BẢNG KỸ NĂNG: Danh mục kỹ năng học sinh đăng ký chia sẻ hoặc muốn học
-- Trạng thái duyệt được phân loại tự động qua AI và phê duyệt bởi giáo viên
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    linh_vuc TEXT NOT NULL,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    trang_thai_duyet TEXT CHECK(trang_thai_duyet IN ('cho_duyet', 'da_duyet', 'tu_choi')) DEFAULT 'cho_duyet',
    ly_do_ai_kiem_duyet TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 3. BẢNG PHIÊN HỌC (SESSIONS): Kết nối giữa người dạy và người học
-- Chứa mã QR điểm danh 2 chiều, dàn ý buổi học do AI hỗ trợ biên soạn và chỉ số quiz_dat_chuan
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_id INTEGER,
    nguoi_day_id INTEGER NOT NULL,
    nguoi_hoc_id INTEGER NOT NULL,
    thoi_gian_bat_dau TEXT,
    so_gio REAL DEFAULT 1.0,
    trang_thai TEXT CHECK(trang_thai IN ('da_dat', 'hoan_thanh', 'huy', 'can_xac_minh')) DEFAULT 'da_dat',
    ma_qr TEXT,
    checkin_day INTEGER DEFAULT 0,
    checkin_hoc INTEGER DEFAULT 0,
    dan_y_ai TEXT,
    quiz_dat_chuan INTEGER DEFAULT 0,
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (nguoi_day_id) REFERENCES users(id),
    FOREIGN KEY (nguoi_hoc_id) REFERENCES users(id)
);

-- 4. BẢNG ĐIỂM DANH CHI TIẾT (ATTENDANCE): Ghi nhận thời gian ra vào phiên học
CREATE TABLE IF NOT EXISTS session_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thoi_gian_vao TEXT,
    thoi_gian_ra TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 5. BẢNG SỔ CÁI TÍN DỤNG (CREDITS LEDGER): Nguyên tắc bất biến (Append-Only)
-- CHỈ ĐƯỢC INSERT, KHÔNG UPDATE/DELETE nhằm đảm bảo tính toàn vẹn và minh bạch tài chính thời gian
-- Hỗ trợ các lý do biến động như trao đổi phiên học, thưởng nhiệm vụ cộng đồng ('nhiem_vu_cong_dong')
CREATE TABLE IF NOT EXISTS credits_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bien_dong REAL NOT NULL,
    ly_do TEXT NOT NULL,
    session_id INTEGER,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

-- 6. BẢNG ĐÁNH GIÁ (RATINGS): Đánh giá tương hỗ sau mỗi buổi học (số sao & nhận xét)
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    nguoi_danh_gia_id INTEGER NOT NULL,
    nguoi_duoc_danh_gia_id INTEGER NOT NULL,
    so_sao INTEGER CHECK(so_sao BETWEEN 1 AND 5),
    nhan_xet TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (nguoi_danh_gia_id) REFERENCES users(id),
    FOREIGN KEY (nguoi_duoc_danh_gia_id) REFERENCES users(id)
);

-- 7. BẢNG CÂU HỎI TRẮC NGHIỆM (QUIZ QUESTIONS): Do AI tự động sinh theo dàn ý buổi học
CREATE TABLE IF NOT EXISTS quiz_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    cau_hoi TEXT NOT NULL,
    lua_chon_a TEXT NOT NULL,
    lua_chon_b TEXT NOT NULL,
    lua_chon_c TEXT NOT NULL,
    lua_chon_d TEXT NOT NULL,
    dap_an_dung TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

-- 8. BẢNG KẾT QUẢ TRẮC NGHIỆM (QUIZ RESULTS): Đo lường sự tiến bộ và mức độ hiểu bài
CREATE TABLE IF NOT EXISTS quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tu_danh_gia_truoc REAL,
    diem_so REAL NOT NULL,
    thoi_gian_lam TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 9. BẢNG NHẬT KÝ AI (AI LOGS): Ghi vết minh bạch mọi tương tác của AI (Gemini Pro)
-- Mở rộng hỗ trợ thêm các chức năng: 'goi_y_nhiem_vu' và 'tro_ly_ao'
CREATE TABLE IF NOT EXISTS ai_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    chuc_nang TEXT CHECK(chuc_nang IN (
        'kiem_duyet',
        'goi_y_ghep_cap',
        'dan_y_buoi_hoc',
        'tom_tat_phan_hoi',
        'canh_bao',
        'bien_tap_vien',
        'tao_quiz',
        'goi_y_nhiem_vu',
        'tro_ly_ao'
    )) NOT NULL,
    input_tom_tat TEXT,
    output_text TEXT,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 10. BẢNG BÀI VIẾT BẢN TIN (BLOG POSTS): Tuyên truyền, chia sẻ gương sáng học tập
CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tieu_de TEXT NOT NULL,
    noi_dung TEXT NOT NULL,
    anh_minh_hoa TEXT,
    tac_gia_ai INTEGER DEFAULT 0,
    trang_thai TEXT CHECK(trang_thai IN ('nhap', 'da_duyet', 'da_dang')) DEFAULT 'nhap',
    thoi_gian_dang TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 11. BẢNG NHIỆM VỤ CỘNG ĐỒNG (COMMUNITY TASKS): Hoạt động hỗ trợ trường học, thư viện, CLB
CREATE TABLE IF NOT EXISTS community_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    dia_diem TEXT,
    so_gio_thuong REAL DEFAULT 1.0,
    so_luong_toi_da INTEGER DEFAULT 5,
    han_dang_ky TEXT,
    nguoi_tao_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('mo', 'dong', 'hoan_thanh', 'huy')) DEFAULT 'mo',
    thoi_gian_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nguoi_tao_id) REFERENCES users(id)
);

-- 12. BẢNG ĐĂNG KÝ NHIỆM VỤ (TASK REGISTRATIONS): Ghi nhận học sinh tham gia nhiệm vụ cộng đồng
CREATE TABLE IF NOT EXISTS task_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('da_dang_ky', 'da_duyet', 'hoan_thanh', 'huy')) DEFAULT 'da_dang_ky',
    thoi_gian_dang_ky TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES community_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 13. BẢNG TIN NHẮN TRỢ LÝ AI (CHAT MESSAGES): Hội thoại giữa người dùng và Trợ lý học đường AI
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vai_tro TEXT CHECK(vai_tro IN ('user', 'assistant', 'system')) NOT NULL,
    noi_dung TEXT NOT NULL,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
