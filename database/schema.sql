-- ==============================================================================
-- DỰ ÁN DỰ THI: NGÂN HÀNG THỜI GIAN HỌC ĐƯỜNG (TIMEBANK EDU)
-- NGÀY HỘI NHÀ GIÁO SÁNG TẠO VỚI CÔNG NGHỆ SỐ VÀ AI 2026 - BẢNG B
-- CẤU TRÚC CƠ SỞ DỮ LIỆU ĐA TRƯỜNG (MULTI-TENANT CORE) - 17 BẢNG CHUẨN
-- ==============================================================================

-- 1. BẢNG TRƯỜNG HỌC (TRUONG): Quản lý các đơn vị trường học tham gia hệ thống
CREATE TABLE IF NOT EXISTS truong (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ten_truong TEXT NOT NULL,
    logo TEXT,
    trang_thai TEXT CHECK(trang_thai IN ('dang_thi_diem', 'chuan_bi_trien_khai', 'dang_su_dung')) DEFAULT 'dang_thi_diem',
    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP
);

-- 2. BẢNG NGƯỜI DÙNG: Lưu thông tin học sinh, giáo viên, quản trị trường, tổng quản trị
-- truong_id: Xác định tài khoản thuộc đơn vị trường nào
-- trang_thai: 'hoat_dong', 'cho_duyet', 'de_xuat_khoa', 'da_khoa'
CREATE TABLE IF NOT EXISTS users (
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

-- 3. BẢNG KỸ NĂNG: Danh mục kỹ năng học sinh đăng ký chia sẻ hoặc muốn học
CREATE TABLE IF NOT EXISTS skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
    user_id INTEGER NOT NULL,
    linh_vuc TEXT NOT NULL,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    trang_thai_duyet TEXT CHECK(trang_thai_duyet IN ('cho_duyet', 'da_duyet', 'tu_choi')) DEFAULT 'cho_duyet',
    ly_do_ai_kiem_duyet TEXT,
    hien_thi_cong_dong INTEGER DEFAULT 0,
    trang_thai_cong_dong TEXT CHECK(trang_thai_cong_dong IN ('chua_dang', 'cho_duyet', 'da_duyet', 'tu_choi')) DEFAULT 'chua_dang',
    nguoi_duyet_cong_dong_id INTEGER,
    ngay_duyet_cong_dong TEXT,
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (nguoi_duyet_cong_dong_id) REFERENCES users(id)
);

-- 4. BẢNG PHIÊN HỌC (SESSIONS): Kết nối giữa người dạy và người học
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
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
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id),
    FOREIGN KEY (nguoi_day_id) REFERENCES users(id),
    FOREIGN KEY (nguoi_hoc_id) REFERENCES users(id)
);

-- 5. BẢNG ĐIỂM DANH CHI TIẾT (ATTENDANCE): Ghi nhận thời gian ra vào phiên học
CREATE TABLE IF NOT EXISTS session_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thoi_gian_vao TEXT,
    thoi_gian_ra TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. BẢNG SỔ CÁI TÍN DỤNG (CREDITS LEDGER): Nguyên tắc bất biến (Append-Only)
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

-- 7. BẢNG ĐÁNH GIÁ (RATINGS): Đánh giá tương hỗ sau mỗi buổi học
CREATE TABLE IF NOT EXISTS ratings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
    session_id INTEGER NOT NULL,
    nguoi_danh_gia_id INTEGER NOT NULL,
    nguoi_duoc_danh_gia_id INTEGER NOT NULL,
    so_sao INTEGER CHECK(so_sao BETWEEN 1 AND 5),
    nhan_xet TEXT,
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (nguoi_danh_gia_id) REFERENCES users(id),
    FOREIGN KEY (nguoi_duoc_danh_gia_id) REFERENCES users(id)
);

-- 8. BẢNG CÂU HỎI TRẮC NGHIỆM (QUIZ QUESTIONS): Do AI tự động sinh theo dàn ý buổi học
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

-- 9. BẢNG KẾT QUẢ TRẮC NGHIỆM (QUIZ RESULTS): Đo lường sự tiến bộ và mức độ hiểu bài
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

-- 10. BẢNG NHẬT KÝ AI (AI LOGS): Ghi vết minh bạch mọi tương tác của AI (Gemini Pro)
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
        'tro_ly_ao',
        'loc_chat'
    )) NOT NULL,
    input_tom_tat TEXT,
    output_text TEXT,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 11. BẢNG BÀI VIẾT BẢN TIN (BLOG POSTS): Tuyên truyền, chia sẻ gương sáng học tập
CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
    tieu_de TEXT NOT NULL,
    noi_dung TEXT NOT NULL,
    anh_minh_hoa TEXT,
    tac_gia_ai INTEGER DEFAULT 0,
    trang_thai TEXT CHECK(trang_thai IN ('nhap', 'da_duyet', 'da_dang')) DEFAULT 'nhap',
    thoi_gian_dang TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (truong_id) REFERENCES truong(id)
);

-- 12. BẢNG NHIỆM VỤ CỘNG ĐỒNG (COMMUNITY TASKS): Hoạt động hỗ trợ trường học, thư viện, CLB
CREATE TABLE IF NOT EXISTS community_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    dia_diem TEXT,
    so_gio_thuong REAL DEFAULT 1.0,
    so_luong_toi_da INTEGER DEFAULT 5,
    han_dang_ky TEXT,
    nguoi_tao_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('mo_dang_ky', 'mo', 'dong', 'hoan_thanh', 'huy')) DEFAULT 'mo_dang_ky',
    thoi_gian_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (nguoi_tao_id) REFERENCES users(id)
);

-- 13. BẢNG ĐĂNG KÝ NHIỆM VỤ (TASK REGISTRATIONS): Ghi nhận học sinh tham gia nhiệm vụ
CREATE TABLE IF NOT EXISTS task_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER DEFAULT 1,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('da_dang_ky', 'da_duyet', 'hoan_thanh', 'huy', 'vang_mat')) DEFAULT 'da_dang_ky',
    thoi_gian_dang_ky TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (task_id) REFERENCES community_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 14. BẢNG TIN NHẮN TRỢ LÝ AI (CHAT MESSAGES): Hội thoại giữa người dùng và Trợ lý học đường AI
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vai_tro TEXT CHECK(vai_tro IN ('user', 'assistant', 'system')) NOT NULL,
    noi_dung TEXT NOT NULL,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 15. BẢNG VI PHẠM NỘI QUY (VIOLATIONS): Ghi vết xử lý vi phạm 3 mức độ và báo cáo phòng học
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

-- 16. BẢNG MÃ MỜI ĐĂNG KÝ (INVITE CODES): Chống mạo danh trường, phân định lớp/cá nhân
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

-- 17. BẢNG THEO DÕI SỬ DỤNG MÃ MỜI (INVITE CODE USAGES): Minh bạch ai đã kích hoạt mã
CREATE TABLE IF NOT EXISTS invite_code_usages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invite_code_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invite_code_id) REFERENCES invite_codes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 18. BẢNG CHỦ ĐỀ DIỄN ĐÀN (FORUM TOPICS): Góc trò chuyện trao đổi học đường
CREATE TABLE IF NOT EXISTS forum_topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tieu_de TEXT NOT NULL,
    noi_dung TEXT NOT NULL,
    trang_thai TEXT DEFAULT 'mo' CHECK(trang_thai IN ('mo', 'khoa')),
    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 19. BẢNG BÌNH LUẬN DIỄN ĐÀN (FORUM REPLIES): Ý kiến, câu trả lời trong chủ đề
CREATE TABLE IF NOT EXISTS forum_replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    topic_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    noi_dung TEXT NOT NULL,
    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (topic_id) REFERENCES forum_topics(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 20. BẢNG KHO TÀI LIỆU GOOGLE DRIVE (DOCUMENTS): Học liệu số hóa toàn trường
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    truong_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    mon_hoc TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_type TEXT,
    drive_file_id TEXT,
    drive_web_view_link TEXT,
    luot_tai INTEGER DEFAULT 0,
    ngay_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    trang_thai TEXT DEFAULT 'hoat_dong' CHECK(trang_thai IN ('hoat_dong', 'da_xoa')),
    FOREIGN KEY (truong_id) REFERENCES truong(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- 21. BẢNG THEO DÕI LƯỢT TẢI TÀI LIỆU (DOCUMENT DOWNLOADS): Minh bạch nhật ký tải file
CREATE TABLE IF NOT EXISTS document_downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
