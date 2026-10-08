BEGIN TRANSACTION;
CREATE TABLE ai_logs (
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
INSERT INTO "ai_logs" VALUES(1,3,'dan_y_buoi_hoc','Soạn dàn ý buổi học Toán Hình học 12','Đã sinh cấu trúc 3 phần: Lý thuyết định nghĩa, bài tập mẫu và mẹo giải nhanh.','2026-09-28 13:50:00');
INSERT INTO "ai_logs" VALUES(2,4,'dan_y_buoi_hoc','Soạn dàn ý hướng dẫn đệm đàn Guitar','Đã sinh danh sách hợp âm C, Am, Dm, G7 và bài tập bấm gam.','2026-09-29 15:10:00');
INSERT INTO "ai_logs" VALUES(3,5,'kiem_duyet','Kiểm duyệt nội dung chia sẻ kỹ năng tiếng Anh','Nội dung giáo dục an toàn, tích cực, không vi phạm chuẩn mực sư phạm.','2026-10-01 10:00:00');
INSERT INTO "ai_logs" VALUES(4,3,'goi_y_nhiem_vu','Gợi ý nhiệm vụ cộng đồng phù hợp học sinh','Đã đề xuất nhiệm vụ hỗ trợ số hóa sách thư viện dựa trên kỹ năng tin học.','2026-10-05 08:30:00');
INSERT INTO "ai_logs" VALUES(5,3,'tro_ly_ao','Tư vấn lộ trình trao đổi kỹ năng học đường','Trợ lý ảo đã giải đáp thắc mắc về quy chế tín dụng thời gian cho học sinh.','2026-10-05 09:15:00');
INSERT INTO "ai_logs" VALUES(6,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(7,3,'goi_y_ghep_cap','Môn: Ngoại ngữ, Trình độ: Cần củng cố, Rảnh: Chiều thứ 3, sáng thứ 7, Số ứng viên: 1','[Rule-Based] 1 gia sư được chọn','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(8,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(9,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(10,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(11,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(12,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(13,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(14,1,'canh_bao','Học sinh ngưng học: 1, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 13:46:26');
INSERT INTO "ai_logs" VALUES(15,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:10');
INSERT INTO "ai_logs" VALUES(16,3,'goi_y_ghep_cap','Môn: Ngoại ngữ, Trình độ: Cần củng cố, Rảnh: Chiều thứ 3, sáng thứ 7, Số ứng viên: 1','[Rule-Based] 1 gia sư được chọn','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(17,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(18,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(19,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(20,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(21,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(22,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(23,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:11');
INSERT INTO "ai_logs" VALUES(24,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:16');
INSERT INTO "ai_logs" VALUES(25,3,'goi_y_ghep_cap','Môn: Ngoại ngữ, Trình độ: Cần củng cố, Rảnh: Chiều thứ 3, sáng thứ 7, Số ứng viên: 1','[Rule-Based] 1 gia sư được chọn','2026-10-08 23:54:16');
INSERT INTO "ai_logs" VALUES(26,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:16');
INSERT INTO "ai_logs" VALUES(27,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:16');
INSERT INTO "ai_logs" VALUES(28,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:16');
INSERT INTO "ai_logs" VALUES(29,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:17');
INSERT INTO "ai_logs" VALUES(30,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:17');
INSERT INTO "ai_logs" VALUES(31,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:17');
INSERT INTO "ai_logs" VALUES(32,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:17');
INSERT INTO "ai_logs" VALUES(33,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(34,3,'goi_y_ghep_cap','Môn: Ngoại ngữ, Trình độ: Cần củng cố, Rảnh: Chiều thứ 3, sáng thứ 7, Số ứng viên: 1','[Rule-Based] 1 gia sư được chọn','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(35,3,'tom_tat_phan_hoi','Tổng 2 đánh giá của user #3','[Rule-Based] Tóm tắt phản hồi học sinh','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(36,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(37,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(38,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(39,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(40,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:21');
INSERT INTO "ai_logs" VALUES(41,1,'canh_bao','Học sinh ngưng học: 2, Cặp đôi xung đột: 0','[Rule-Based] Cảnh báo sớm quản trị học đường','2026-10-08 23:54:22');
INSERT INTO "ai_logs" VALUES(42,1,'tro_ly_ao','[Quản trị viên Hệ thống] Hỏi: Xin chào bạn, tôi muốn hỏi số dư','[Rule-Based] Chào Quản trị viên Hệ thống! Hiện tại số dư tín dụng học tập trong ví của bạn là 100.0 giờ. Bạn có thể dùng số giờ này để đặt lịch học kỹ năng mới cùng bạn bè trên Chợ kỹ năng nhé!','2026-10-08 23:54:28');
INSERT INTO "ai_logs" VALUES(43,1,'tro_ly_ao','[Quản trị viên Hệ thống] Hỏi: Chào bạn','Chào bạn! Tôi là trợ lý AI học đường của TimeBank EDU, rất vui được hỗ trợ bạn hôm nay.','2026-10-08 23:54:28');
INSERT INTO "ai_logs" VALUES(44,1,'tro_ly_ao','[Quản trị viên Hệ thống] Hỏi: Xin chào bạn, tôi muốn hỏi số dư','[Rule-Based] Chào Quản trị viên Hệ thống! Hiện tại số dư tín dụng học tập trong ví của bạn là 100.0 giờ. Bạn có thể dùng số giờ này để đặt lịch học kỹ năng mới cùng bạn bè trên Chợ kỹ năng nhé!','2026-10-08 23:54:46');
INSERT INTO "ai_logs" VALUES(45,1,'tro_ly_ao','[Quản trị viên Hệ thống] Hỏi: Bạn có thể giới thiệu về TimeBank không?','[Rule-Based] Chào Quản trị viên Hệ thống! Tôi là Trợ lý Học đường TimeBank EDU (Hỗ trợ bởi AI Gemini). Số dư ví hiện tại của bạn là 100.0h. Bạn có thể hỏi tôi về: số dư giờ, lịch học sắp tới, hướng dẫn đăng kỹ năng hoặc gợi ý lộ trình học tập!','2026-10-08 23:54:48');
INSERT INTO "ai_logs" VALUES(46,1,'tro_ly_ao','[Quản trị viên Hệ thống] Hỏi: Chào bạn','Chào bạn! Tôi là trợ lý AI học đường của TimeBank EDU, rất vui được hỗ trợ bạn hôm nay.','2026-10-08 23:54:48');
CREATE TABLE blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tieu_de TEXT NOT NULL,
    noi_dung TEXT NOT NULL,
    anh_minh_hoa TEXT,
    tac_gia_ai INTEGER DEFAULT 0,
    trang_thai TEXT CHECK(trang_thai IN ('nhap', 'da_duyet', 'da_dang')) DEFAULT 'nhap',
    thoi_gian_dang TEXT DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO "blog_posts" VALUES(1,'Khởi động Mô hình Ngân hàng Thời gian Học đường: Một giờ bạn dạy - Một giờ bạn học','Chào mừng toàn thể Thầy Cô giáo và các bạn học sinh đến với TimeBank EDU! Tại đây, mọi tri thức đều bình đẳng, 1 giờ dạy đổi lấy 1 giờ học. Hãy cùng nhau chia sẻ thế mạnh và giúp đỡ bạn bè cùng tiến bộ nhé!','/static/img/newsletter_banner.svg',0,'da_dang','2026-10-01 08:00:00');
CREATE TABLE chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    vai_tro TEXT CHECK(vai_tro IN ('user', 'assistant', 'system')) NOT NULL,
    noi_dung TEXT NOT NULL,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
INSERT INTO "chat_messages" VALUES(1,3,'user','Em muốn học thêm kỹ năng giao tiếp tiếng Anh thì nên tìm bạn nào?','2026-10-01 09:00:00');
INSERT INTO "chat_messages" VALUES(2,3,'assistant','Chào An! Dựa trên hệ thống, bạn Lê Kim Chi (10A3) đang chia sẻ kỹ năng Luyện phản xạ IELTS Speaking rất phù hợp với em nhé!','2026-10-01 09:00:05');
CREATE TABLE community_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    dia_diem TEXT,
    so_gio_thuong REAL DEFAULT 1.0,
    so_luong_toi_da INTEGER DEFAULT 5,
    han_dang_ky TEXT,
    nguoi_tao_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('mo_dang_ky', 'mo', 'dong', 'hoan_thanh', 'huy')) DEFAULT 'mo_dang_ky',
    thoi_gian_tao TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (nguoi_tao_id) REFERENCES users(id)
);
INSERT INTO "community_tasks" VALUES(1,'Dọn rác bãi biển Hạ Long sáng Chủ nhật','Hoạt động thanh niên tình nguyện thu gom rác thải nhựa tại bờ biển, làm sạch cảnh quan môi trường.','Bãi tắm Bãi Cháy, TP. Hạ Long',2.0,10,'2026-10-25',2,'mo_dang_ky','2026-10-05 08:00:00');
INSERT INTO "community_tasks" VALUES(2,'Hỗ trợ thư viện trường sắp xếp sách','Phân loại sách giáo khoa mới, dán mã định danh và sắp xếp lên giá sách theo chuẩn thư viện xanh.','Phòng Thư viện - Tầng 2',1.5,5,'2026-10-20',2,'mo_dang_ky','2026-10-05 08:30:00');
INSERT INTO "community_tasks" VALUES(3,'Dạy kỹ năng số cho các em khối Tiểu học','Phụ đạo tin học, hướng dẫn các em học sinh lớp 3-4 gõ bàn phím 10 ngón và tra cứu tài liệu học tập an toàn.','Phòng máy Tin học số 2',2.0,4,'2026-10-30',2,'mo_dang_ky','2026-10-05 09:00:00');
INSERT INTO "community_tasks" VALUES(4,'Hỗ trợ số hóa tài liệu thư viện trường','Quét và phân loại sách tham khảo vào hệ thống thư viện điện tử.','Phòng Thư viện - Tầng 2',2.0,4,'2026-10-15',2,'hoan_thanh','2026-10-04 08:00:00');
CREATE TABLE credits_ledger (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    bien_dong REAL NOT NULL,
    ly_do TEXT NOT NULL,
    session_id INTEGER,
    thoi_gian TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
INSERT INTO "credits_ledger" VALUES(1,3,1.0,'Dạy Toán cho Trần Thanh Bình',1,'2026-09-28 15:00:00');
INSERT INTO "credits_ledger" VALUES(2,4,-1.0,'Học Toán từ Nguyễn Hoàng An',1,'2026-09-28 15:00:00');
INSERT INTO "credits_ledger" VALUES(3,4,1.0,'Dạy Đàn cho Lê Kim Chi',2,'2026-09-29 16:30:00');
INSERT INTO "credits_ledger" VALUES(4,5,-1.0,'Học Đàn từ Trần Thanh Bình',2,'2026-09-29 16:30:00');
INSERT INTO "credits_ledger" VALUES(5,5,1.0,'Dạy Tiếng Anh cho Nguyễn Hoàng An',3,'2026-10-01 17:00:00');
INSERT INTO "credits_ledger" VALUES(6,3,-1.0,'Học Tiếng Anh từ Lê Kim Chi',3,'2026-10-01 17:00:00');
INSERT INTO "credits_ledger" VALUES(7,3,1.0,'Dạy Toán cho Phạm Quang Minh',4,'2026-10-03 10:00:00');
INSERT INTO "credits_ledger" VALUES(8,6,-1.0,'Học Toán từ Nguyễn Hoàng An',4,'2026-10-03 10:00:00');
INSERT INTO "credits_ledger" VALUES(9,6,1.0,'Dạy Python cho Vũ Thu Hà',5,'2026-10-04 15:30:00');
INSERT INTO "credits_ledger" VALUES(10,7,-1.0,'Học Python từ Phạm Quang Minh',5,'2026-10-04 15:30:00');
INSERT INTO "credits_ledger" VALUES(11,3,2.0,'nhiem_vu_cong_dong: Hỗ trợ số hóa tài liệu thư viện',NULL,'2026-10-05 11:00:00');
CREATE TABLE quiz_questions (
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
INSERT INTO "quiz_questions" VALUES(1,1,'Khái niệm góc giữa hai mặt phẳng trong không gian được đo bằng góc giữa:','Hai đường thẳng bất kỳ trên hai mặt phẳng','Hai đường thẳng lần lượt vuông góc với giao tuyến tại cùng một điểm','Hai vectơ chỉ phương ngẫu nhiên','Giao tuyến của hai mặt phẳng','B');
INSERT INTO "quiz_questions" VALUES(2,1,'Khi hai mặt phẳng vuông góc với nhau, góc giữa chúng bằng bao nhiêu độ?','0 độ','45 độ','90 độ','180 độ','C');
INSERT INTO "quiz_questions" VALUES(3,1,'Để tính khoảng cách từ một điểm M đến mặt phẳng (P), ta cần dựng:','Đoạn vuông góc kẻ từ M đến mặt phẳng (P)','Một đường thẳng xiên bất kỳ','Đường thẳng song song với (P)','Đoạn nối M với trọng tâm tam giác đáy','A');
INSERT INTO "quiz_questions" VALUES(4,1,'Cho hình chóp S.ABC có SA vuông góc với đáy (ABC). Góc giữa đường thẳng SB và đáy là:','Góc SBA','Góc SAB','Góc ASB','Góc SCB','A');
INSERT INTO "quiz_questions" VALUES(5,1,'Tuyệt chiêu nhận diện nhanh góc giữa mặt bên và mặt đáy trong hình chóp đều là gì?','Xác định trung điểm cạnh đáy rồi nối với đỉnh','Kẻ bừa một đường thẳng nối tâm đáy','Không thể xác định','Dùng thước đo độ trên giấy','A');
INSERT INTO "quiz_questions" VALUES(6,2,'Hợp âm Đô trưởng (C) cơ bản gồm những nốt nào trong âm giai?','Đô - Mi - Son (C - E - G)','Đô - Rê - Mi (C - D - E)','La - Đô - Mi (A - C - E)','Son - Si - Rê (G - B - D)','A');
INSERT INTO "quiz_questions" VALUES(7,2,'Khi bấm hợp âm La thứ (Am), ngón trỏ thường đặt ở vị trí nào?','Ngăn 1 dây 2 (nốt Đô)','Ngăn 2 dây 3','Ngăn 3 dây 1','Ngăn 1 dây 6','A');
INSERT INTO "quiz_questions" VALUES(8,2,'Điệu Disco cơ bản thường có nhịp phách như thế nào?','Nhịp 2/4 hoặc 4/4 rộn rã, dứt khoát','Nhịp 3/4 êm dịu điệu Valse','Nhịp 6/8 chậm rãi','Không có nhịp phách cố định','A');
INSERT INTO "quiz_questions" VALUES(9,2,'Bí quyết để chuyển nhanh giữa các hợp âm mà không bị vấp tiếng là gì?','Giữ ngón tay sát phím đàn và tìm ngón chung làm trụ','Nhấc toàn bộ cả bàn tay ra thật xa cần đàn','Dừng gảy 5 giây để nhìn tay','Bấm thật mạnh cho đau ngón tay','A');
INSERT INTO "quiz_questions" VALUES(10,2,'Khi ngón tay bị đau lúc mới tập guitar, cách khắc phục khoa học nhất là:','Tập đều đặn mỗi ngày 20-30 phút để hình thành vết chai tự nhiên','Bỏ đàn 2 tháng','Dùng băng keo quấn kín các đầu ngón tay','Bôi dầu hỏa vào ngón tay','A');
INSERT INTO "quiz_questions" VALUES(11,3,'Trong bài thi IELTS Speaking Part 1, độ dài lý tưởng cho mỗi câu trả lời là:','Khoảng 2 đến 3 câu hoàn chỉnh có mở rộng ý tự nhiên','Chỉ trả lời đúng ''Yes'' hoặc ''No''','Nói độc thoại liên tục 10 phút','Im lặng mỉm cười chờ giám khảo hỏi tiếp','A');
INSERT INTO "quiz_questions" VALUES(12,3,'Để nâng cao điểm tiêu chí Từ vựng (Lexical Resource), bạn nên sử dụng:','Collocations và từ đồng nghĩa ngữ cảnh tự nhiên','Từ cổ điển thế kỷ 18 khó hiểu','Từ viết tắt tiếng lóng tin nhắn','Lặp lại 1 từ duy nhất nhiều lần','A');
INSERT INTO "quiz_questions" VALUES(13,3,'Khi gặp câu hỏi bất ngờ trong Speaking Part 1, chiến thuật câu giờ thông minh là:','Dùng filler phrase tự nhiên như ''That’s an interesting question...''','Nói to ''I don''t know'' rồi ngồi im','Xin phép giám khảo tra từ điển Google','Hỏi ngược lại giám khảo','A');
INSERT INTO "quiz_questions" VALUES(14,3,'Tiêu chí ''Fluency and Coherence'' (Trôi chảy và mạch lạc) đánh giá điều gì?','Khả năng diễn đạt liên tục, có liên kết ý logic, ít ngập ngừng kéo dài','Nói thật nhanh như đọc ráp dù sai ngữ pháp','Giọng điệu phải giống 100% người bản xứ','Số lượng từ ngữ phát âm to nhất','A');
INSERT INTO "quiz_questions" VALUES(15,3,'Bí quyết tự tin luyện nói tiếng Anh hằng ngày cùng bạn bè là gì?','Tạo môi trường trao đổi thoải mái, không sợ mắc lỗi sai','Chỉ nói khi thuộc lòng 100% kịch bản','Chỉ luyện nói một mình trước gương trong bóng tối','Không bao giờ nói chuyện với ai','A');
CREATE TABLE quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    tu_danh_gia_truoc REAL,
    diem_so REAL NOT NULL,
    thoi_gian_lam TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);
INSERT INTO "quiz_results" VALUES(1,1,4,2.0,4.0,'2026-09-28 15:15:00');
INSERT INTO "quiz_results" VALUES(2,2,5,3.0,5.0,'2026-09-29 16:45:00');
INSERT INTO "quiz_results" VALUES(3,3,3,2.0,4.0,'2026-10-01 17:15:00');
CREATE TABLE ratings (
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
INSERT INTO "ratings" VALUES(1,1,4,3,5,'Anh An giảng Toán rất dễ hiểu, giải thích bài tập góc không gian siêu hay!');
INSERT INTO "ratings" VALUES(2,2,5,4,5,'Bình dạy đàn kiên nhẫn, chỉ cách chuyển hợp âm rất dễ nhớ.');
INSERT INTO "ratings" VALUES(3,3,3,5,5,'Chi phát âm chuẩn, sửa lỗi ngữ điệu cho mình rất nhiệt tình.');
INSERT INTO "ratings" VALUES(4,4,6,3,5,'Buổi học rất bổ ích, mình đã tự tin làm được bài kiểm tra.');
INSERT INTO "ratings" VALUES(5,5,7,6,4,'Minh chỉ code dễ hiểu, mong có thêm buổi học tiếp theo.');
CREATE TABLE session_attendance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    thoi_gian_vao TEXT,
    thoi_gian_ra TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE sessions (
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
INSERT INTO "sessions" VALUES(1,1,3,4,'2026-09-28 14:00:00',1.0,'hoan_thanh','QR_SES_001',1,1,'Dàn ý AI: Khái niệm góc giữa hai mặt phẳng + 3 bài tập mẫu',1);
INSERT INTO "sessions" VALUES(2,2,4,5,'2026-09-29 15:30:00',1.0,'hoan_thanh','QR_SES_002',1,1,'Dàn ý AI: Hợp âm C-Am-Dm-G7 + bài tập bấm tay',1);
INSERT INTO "sessions" VALUES(3,3,5,3,'2026-10-01 16:00:00',1.0,'hoan_thanh','QR_SES_003',1,1,'Dàn ý AI: Chủ đề Hometown & Hobbies',1);
INSERT INTO "sessions" VALUES(4,1,3,6,'2026-10-03 09:00:00',1.0,'hoan_thanh','QR_SES_004',1,1,'Dàn ý AI: Góc giữa đường thẳng và mặt phẳng',1);
INSERT INTO "sessions" VALUES(5,4,6,7,'2026-10-04 14:30:00',1.0,'hoan_thanh','QR_SES_005',1,1,'Dàn ý AI: Biến số và lệnh input/print trong Python',1);
CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    linh_vuc TEXT NOT NULL,
    tieu_de TEXT NOT NULL,
    mo_ta TEXT,
    trang_thai_duyet TEXT CHECK(trang_thai_duyet IN ('cho_duyet', 'da_duyet', 'tu_choi')) DEFAULT 'cho_duyet',
    ly_do_ai_kiem_duyet TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT INTO "skills" VALUES(1,3,'Toán học','Ôn tập Hình học không gian lớp 12','Phương pháp giải nhanh trắc nghiệm khoảng cách và góc','da_duyet','Nội dung bổ ích, phù hợp chương trình');
INSERT INTO "skills" VALUES(2,4,'Năng khiếu','Đệm hát Guitar cơ bản cho người mới','Cách bấm các hợp âm chuẩn và kỹ thuật quạt chả điệu Disco','da_duyet','Kỹ năng giải trí tích cực');
INSERT INTO "skills" VALUES(3,5,'Ngoại ngữ','Luyện phản xạ nói Tiếng Anh IELTS Speaking','Chiến thuật trả lời Part 1 và Part 2 tự nhiên, lưu loát','da_duyet','Rất hữu ích cho học sinh hội nhập');
INSERT INTO "skills" VALUES(4,6,'Tin học','Lập trình Python cho người mới bắt đầu','Cấu trúc rẽ nhánh, vòng lặp và xử lý chuỗi căn bản','da_duyet','Định hướng chuyển đổi số trường học');
INSERT INTO "skills" VALUES(5,7,'Khoa học','Phương pháp làm bài thí nghiệm Hóa học 12','Giải thích hiện tượng và mẹo nhớ tính chất kim loại kiềm','cho_duyet','Chờ giáo viên bộ môn duyệt nội dung');
INSERT INTO "skills" VALUES(6,5,'Toán học','Phương pháp vẽ đồ thị và khảo sát hàm số 12','Kỹ thuật nhận diện bảng biến thiên và cực trị hàm số','da_duyet','Nội dung trọng tâm thi tốt nghiệp THPT');
INSERT INTO "skills" VALUES(7,7,'Toán học','Bí quyết giải nhanh Toán Xác suất và Thống kê','Phương pháp tư duy sơ đồ cây và bài toán xác suất thực tế','da_duyet','Rèn luyện tư duy logic và suy luận');
CREATE TABLE task_registrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    trang_thai TEXT CHECK(trang_thai IN ('da_dang_ky', 'da_duyet', 'hoan_thanh', 'huy', 'vang_mat')) DEFAULT 'da_dang_ky',
    thoi_gian_dang_ky TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES community_tasks(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
INSERT INTO "task_registrations" VALUES(1,4,3,'hoan_thanh','2026-10-04 08:15:00');
INSERT INTO "task_registrations" VALUES(2,2,4,'da_dang_ky','2026-10-05 08:45:00');
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
INSERT INTO "users" VALUES(1,'admin','Quản trị viên Hệ thống','Ban Giám Hiệu','admin',100.0,'Toàn thời gian','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(2,'GV001','Thầy Nguyễn Văn Đức','Tổ Toán - Tin','giao_vien',10.0,'Các buổi chiều trong tuần','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(3,'HS12001','Nguyễn Hoàng An','12A1','hoc_sinh',3.5,'Chiều thứ 3, sáng thứ 7','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(4,'HS11002','Trần Thanh Bình','11B2','hoc_sinh',2.5,'Sáng Chủ nhật, tối thứ 5','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(5,'HS10003','Lê Kim Chi','10A3','hoc_sinh',3.0,'Chiều thứ 6, sáng Chủ nhật','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(6,'HS11004','Phạm Quang Minh','11A1','hoc_sinh',2.0,'Tối thứ 2, tối thứ 4','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
INSERT INTO "users" VALUES(7,'HS12005','Vũ Thu Hà','12D2','hoc_sinh',2.0,'Sáng thứ 7, chiều Chủ nhật','scrypt:32768:8:1$ZAHojaujV35QhWe5$7b94fa9125d98487864e34924cc9a78f97db02e2c1abd4000193c28bf3995c3720ef28c918d6ac36d6c4e8ebae4ff932d022089c84520833d2543e49b7a92b85');
DELETE FROM "sqlite_sequence";
INSERT INTO "sqlite_sequence" VALUES('users',7);
INSERT INTO "sqlite_sequence" VALUES('skills',7);
INSERT INTO "sqlite_sequence" VALUES('sessions',5);
INSERT INTO "sqlite_sequence" VALUES('credits_ledger',11);
INSERT INTO "sqlite_sequence" VALUES('ratings',5);
INSERT INTO "sqlite_sequence" VALUES('ai_logs',46);
INSERT INTO "sqlite_sequence" VALUES('community_tasks',4);
INSERT INTO "sqlite_sequence" VALUES('task_registrations',2);
INSERT INTO "sqlite_sequence" VALUES('chat_messages',2);
INSERT INTO "sqlite_sequence" VALUES('quiz_questions',15);
INSERT INTO "sqlite_sequence" VALUES('quiz_results',3);
INSERT INTO "sqlite_sequence" VALUES('blog_posts',1);
COMMIT;
