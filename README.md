# Ngân hàng Thời gian Học đường (TimeBank EDU)

> **Sản phẩm dự thi Bảng B:** *"Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026"*  
> **Đơn vị chủ trì:** Bộ Giáo dục và Đào tạo phối hợp cùng Đại học RMIT Việt Nam  
> **Triết lý sư phạm:** *"Một giờ bạn dạy — một giờ bạn được học"* (Mọi tri thức đều bình đẳng, không dùng tiền mặt)

---

## 1. Giới thiệu dự án

**Ngân hàng Thời gian Học đường (TimeBank EDU)** là mô hình sư phạm đổi mới kết hợp nền tảng số và Trợ lý AI (Gemini Pro), nhằm khuyến khích học sinh chia sẻ kỹ năng, kèm cặp bạn bè và tích lũy tín dụng thời gian:
- **1 giờ chia sẻ = 1 tín dụng thời gian**: Học sinh giỏi Toán dạy 1 giờ sẽ nhận 1 tín dụng để "đổi" lấy 1 giờ học Tiếng Anh, Đàn guitar, Lập trình hoặc Vẽ từ bạn khác.
- **Bình đẳng tri thức**: Không phân biệt môn phụ hay môn chính; mọi kỹ năng đều được trân trọng.
- **Gắn kết học đường**: Giảm áp lực học thêm, xây dựng văn hóa sẻ chia, phòng ngừa bạo lực học đường qua hoạt động đôi bạn cùng tiến.

---

## 2. Kiến trúc kỹ thuật: Single-Tenant

Hệ thống được thiết kế theo kiến trúc **Single-Tenant (Mỗi trường một bản cài đặt độc lập)**:
- **Bảo mật tuyệt đối**: Cơ sở dữ liệu SQLite lưu trữ tại chỗ, không chia sẻ dữ liệu giữa các trường.
- **Tùy biến thương hiệu trong 5 phút**: Toàn bộ tên trường, logo, màu sắc chủ đạo, email liên hệ được cấu hình tập trung trong tệp `config.yaml`. Khi chuyển giao sang trường mới, giáo viên chỉ cần sửa `config.yaml` mà không phải can thiệp mã nguồn.
- **Công nghệ tối giản & bền vững**: Python Flask + SQLite + HTML/CSS/JS thuần (Bootstrap 5). Không cần Docker, không cần cài đặt database server phức tạp.

---

## 3. Hướng dẫn chạy cục bộ (Chạy đúng 1 lệnh)

### Yêu cầu môi trường
- Máy tính đã cài đặt Python 3.10 trở lên.

### Bước 1: Cài đặt thư viện (Chỉ làm 1 lần đầu)
Mở Terminal hoặc PowerShell tại thư mục dự án và chạy:
```bash
pip install -r requirements.txt
```

### Bước 2: Khởi chạy hệ thống (ĐÚNG 1 LỆNH)
Chạy lệnh duy nhất sau:
```bash
python app.py
```
> **Cơ chế tự động:** Hệ thống sẽ tự động khởi tạo cơ sở dữ liệu `database/timebank.db` với đầy đủ 10 bảng chuẩn và nạp sẵn dữ liệu mẫu thực tế.

Mở trình duyệt truy cập: **`http://127.0.0.1:5000`**

---

## 4. Hướng dẫn Deploy lên Render (Free Tier)

Dự án đã được tối ưu sẵn để triển khai trực tuyến hoàn toàn miễn phí trên nền tảng **Render.com**:

### Bước 1: Đẩy mã nguồn lên GitHub cá nhân
Đảm bảo mã nguồn dự án đã được đẩy lên GitHub (tệp `.env` đã được `.gitignore` tự động bỏ qua).

### Bước 2: Tạo Web Service trên Render
1. Đăng nhập vào [Render.com](https://render.com) (bằng tài khoản GitHub).
2. Nhấn **New +** ➔ Chọn **Web Service**.
3. Chọn kho mã nguồn GitHub của bạn: `timebank-edu`.

### Bước 3: Điền thông số cấu hình Render
- **Name**: `timebank-edu` (hoặc tên tùy thích)
- **Region**: `Singapore` (để tốc độ tải từ Việt Nam nhanh nhất)
- **Branch**: `main`
- **Runtime**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  gunicorn app:app
  ```
- **Instance Type**: Chọn gói **Free**.

### Bước 4: Thiết lập biến môi trường (Environment Variables)
Trong mục **Environment Variables** trên Render, thêm 2 khóa sau:
- `FLASK_SECRET_KEY`: `chuoi-khoa-bi-mat-tuy-y-2026`
- `GEMINI_API_KEY`: *(Dán mã API Key Google Gemini của bạn vào đây)*

Nhấn **Create Web Service**. Sau 1–2 phút, Render sẽ cấp cho bạn một địa chỉ web trực tuyến dạng `https://timebank-edu.onrender.com` để gửi ban giám khảo trải nghiệm!

---

## 5. Cấu trúc thư mục dự án

```text
timebankEDU/
├── app.py                  # Mã nguồn chính Flask, quản lý kết nối DB & điều hướng
├── config.yaml             # Cấu hình thương hiệu nhà trường (Single-tenant)
├── requirements.txt        # Danh sách thư viện phụ thuộc (Flask, Gemini, QRCode, Gunicorn)
├── .env.example            # Mẫu cấu hình biến môi trường
├── .gitignore              # Loại trừ .env, database sqlite, cache
├── README.md               # Hướng dẫn chi tiết bằng tiếng Việt
├── database/
│   ├── schema.sql          # Định nghĩa 13 bảng SQLite chuẩn theo đặc tả kiến trúc M0-BS
│   └── timebank.db         # File CSDL SQLite (tự động tạo khi chạy app)
├── static/
│   ├── css/
│   │   └── style.css       # Giao diện responsive, đồng bộ mã màu nhà trường
│   └── img/
│       └── logo_timebank_edu.png # Biểu trưng chính thức TimeBank EDU (PNG trong suốt)
└── templates/
    ├── base.html           # Khung giao diện chung (Navbar, Footer, Modal đăng nhập)
    └── index.html          # Trang chủ Landing Page gồm 6 khối chức năng
```

---

## 6. Cấu trúc Cơ sở dữ liệu (Đủ 13 bảng chuẩn)

1. `users`: Thông tin học sinh, giáo viên, quản trị viên; số dư mặc định 2.0 giờ; thêm `gio_ranh` (thời gian rảnh để AI ghép cặp).
2. `skills`: Danh mục kỹ năng học sinh đăng ký chia sẻ hoặc cần học.
3. `sessions`: Các phiên học kết nối 1-1, mã QR xác thực, dàn ý bài học từ AI và `quiz_dat_chuan`.
4. `session_attendance`: Ghi nhận chi tiết thời gian ra/vào buổi học.
5. `credits_ledger`: Sổ cái tín dụng bất biến (**CHỈ INSERT**, không sửa/xóa) bảo đảm minh bạch; hỗ trợ lý do `nhiem_vu_cong_dong`.
6. `ratings`: Đánh giá chất lượng và số sao sau mỗi buổi học.
7. `quiz_questions`: Câu hỏi trắc nghiệm đánh giá kiến thức do AI biên soạn.
8. `quiz_results`: Kết quả làm bài lượng giá của học sinh.
9. `ai_logs`: Nhật ký minh bạch ghi vết AI (hỗ trợ thêm `goi_y_nhiem_vu` và `tro_ly_ao`).
10. `blog_posts`: Bảng tin học đường, gương sáng gia sư và tin tức chuyển đổi số.
11. `community_tasks`: Hoạt động, nhiệm vụ tình nguyện hỗ trợ nhà trường nhận giờ tín dụng.
12. `task_registrations`: Ghi nhận đăng ký và phê duyệt tham gia nhiệm vụ cộng đồng.
13. `chat_messages`: Lịch sử tương tác giữa học sinh/giáo viên với Trợ lý ảo AI học đường.

---

## 7. Đổi cấu hình trường trong 5 phút

Mở tệp `config.yaml` và chỉnh sửa các trường sau:
```yaml
ten_truong: "Trường Quốc tế Song ngữ UKA Academy Hạ Long"
logo_path: "/static/img/logo_timebank_edu.png"
mau_chu_dao: "#F26522"
email_lien_he: "mshuyenuka@gmail.com"
dong_gioi_thieu: "Nền tảng Ngân hàng Thời gian Học đường..."
```
Lưu tệp và tải lại trang, toàn bộ nhận diện và tiêu đề của website sẽ được đồng bộ ngay tức khắc!

---

## 8. Tài khoản mẫu & Phân quyền (Milestone M1)

Hệ thống thiết lập sẵn các tài khoản để Ban Giám khảo và giáo viên trải nghiệm ngay:
- **Quản trị viên (Admin):** `admin` / mật khẩu: `admin123` (Truy cập toàn quyền dashboard `/admin`, duyệt kỹ năng).
- **Giáo viên phụ trách:** `GV001` / mật khẩu: `admin123` (Truy cập duyệt kỹ năng `/skills/approve`).
- **Học sinh:** `HS12001` / mật khẩu: `admin123` (Hồ sơ cá nhân, bị chặn 403 khi vào `/admin` và `/skills/approve`).

### Phân quyền hệ thống (RBAC):
- `/register`: Đăng ký tài khoản học sinh mới, tự động cấp **2.0 giờ tín dụng ban đầu** vào sổ cái.
- `/login`, `/logout`: Đăng nhập/Đăng xuất bảo mật với mật khẩu băm, báo lỗi tiếng Việt nếu sai.
- `/profile`: Hồ sơ cá nhân, số dư giờ thực tế và lịch sử biến động sổ cái tín dụng (`credits_ledger`).
- `/admin`: Bảng điều khiển quản trị tối cao — **chỉ Admin**, học sinh vào sẽ bị chặn với mã 403 Forbidden.
- `/skills/approve`: Khu vực duyệt kỹ năng học sinh — **chỉ Giáo viên & Admin**, học sinh vào bị chặn 403.

---

## 9. Đăng kỹ năng, Chợ kỹ năng & Đặt lịch học (Milestone M2)

- **Đăng kỹ năng (`/skills/new`):** Học sinh chia sẻ chuyên đề thế mạnh thuộc 10 lĩnh vực chuẩn (*Toán, Lý, Hóa, Văn, Anh, Vẽ, Đàn, Thể thao, Tin học, Khác*). Khi đăng ký, kỹ năng tự động ở trạng thái `cho_duyet` chờ giáo viên phê duyệt sư phạm.
- **Chợ kỹ năng (`/skills`):** Chỉ hiển thị các kỹ năng đã được phê duyệt (`da_duyet`). Kỹ năng chưa duyệt bị ẩn hoàn toàn. Hỗ trợ tìm kiếm từ khóa và lọc danh mục lĩnh vực.
- **Đặt lịch học (`/sessions/book`):**
  * Học sinh chọn chuyên đề muốn học từ bạn bè.
  * Giới hạn thời lượng: **Tối đa 2.0 giờ / phiên** (0.5h đến 2.0h).
  * Kiểm soát số dư: Học sinh phải có đủ giờ tín dụng trong sổ cái.
  * Bảo đảm tính công bằng: Học sinh không thể tự đặt lịch kỹ năng của chính mình.
  * Phiên học được khởi tạo với trạng thái `da_dat` và gắn mã QR xác thực định danh.
- **Lịch của tôi (`/my-schedule`):**
  * Cả 2 bên (**Người dạy** và **Người học**) đều theo dõi được phiên học trong lịch trình cá nhân.
  * Phân loại rõ ràng: *Phiên tôi dạy* (vai trò Gia sư) và *Phiên tôi học* (vai trò Học sinh).

---

## 10. Ví tín dụng thời gian & Điểm danh Check-in QR 2 chiều (Milestone M3)

- **Trang chi tiết phiên học (`/sessions/<id>`):**
  * Hiển thị toàn bộ thông tin buổi học: chuyên đề, thời gian hẹn, thời lượng, gia sư và bạn học.
  * Sinh mã QR ngẫu nhiên an toàn (`ma_qr`), chuyển đổi thành ảnh Base64 PNG hiển thị trực quan ngay trên điện thoại hoặc trình duyệt máy tính.
  * Điểm danh 2 chiều: Cung cấp nút Check-in cho cả Người dạy (`checkin_day = 1`) và Người học (`checkin_hoc = 1`).
  * Nút **"Xác nhận hoàn thành & Chuyển giờ"**: Chỉ cho phép người dạy thao tác khi **CẢ HAI BÊN ĐÃ CHECK-IN**.

- **Cơ chế chuyển giờ tín dụng & Sổ cái bất biến:**
  * Khi người dạy bấm xác nhận sau khi cả hai đã check-in:
    - Ghi nhận nguyên tử 2 dòng vào bảng `credits_ledger`:
      + Người dạy: nhận `+so_gio` giờ với lý do `'day_hoc'`.
      + Người học: trừ `-so_gio` giờ với lý do `'hoc'`.
    - Tự động cộng/trừ số dư `so_du_gio` trong bảng `users`.
    - Chuyển trạng thái phiên học `sessions` sang `'hoan_thanh'`.
  * **Ràng buộc an toàn:** Nếu chỉ có 1 bên check-in hoặc chưa ai check-in, hệ thống kiên quyết chặn lại, không chuyển giờ và hiển thị cảnh báo tiếng Việt rõ ràng.

- **Chặn đặt lịch khi số dư không đủ:**
  * Khi học sinh có số dư không đủ (ví dụ có 0.5h nhưng đặt phiên 1.0h), hệ thống lập tức chặn đặt lịch tại `/sessions/book` và hướng dẫn bạn học đăng ký kỹ năng để dạy kèm tích thêm giờ.

- **Trang "Ví của tôi" (`/wallet`):**
  * Hiển thị số dư khả dụng hiện tại với định dạng trực quan.
  * Thống kê tổng giờ đã tích lũy (`+h`) và tổng giờ đã trao đổi (`-h`).
  * Danh sách lịch sử biến động sổ cái tín dụng (`credits_ledger`) sắp xếp theo thời gian mới nhất xếp trước (`ORDER BY id DESC`).
  * Tuân thủ nghiêm ngặt nguyên tắc **Append-Only** (chỉ `INSERT`, không `UPDATE`/`DELETE`).

- **Chạy kiểm thử nghiệm thu Milestone M3:**
  ```bash
  python test_m3.py
  ```
  * Kết quả: 6/6 test cases đạt chuẩn 100%.

---

## 11. Phòng học ảo trong ứng dụng & Đối soát thời lượng online (Milestone M3+)

- **Phòng học ảo tích hợp (`/sessions/<id>/room`):**
  * Nhúng trực tiếp giải pháp hội nghị truyền hình Jitsi Meet thông qua iframe HTML chuẩn (`https://meet.jit.si/timebankedu-{ma_qr}`).
  * Không yêu cầu tài khoản bên thứ ba, bảo mật riêng biệt từng buổi học theo mã định danh `ma_qr`.
  * Cung cấp giao diện tích hợp: khung video 2 bên, đồng hồ đếm giờ trực tiếp (timer JS), dàn ý gợi ý bài giảng và bảng đối soát quy tắc 80%.

- **Nhật ký vào/ra (`session_attendance`) & Tự động Check-in 2 bên:**
  * Khi người dạy hoặc người học truy cập phòng học ảo, hệ thống tự động ghi vết thời gian vào (`thoi_gian_vao`) trong bảng `session_attendance`.
  * Tự động kích hoạt cờ check-in tương ứng: `sessions.checkin_day = 1` và `sessions.checkin_hoc = 1` mà không cần thao tác thủ công.

- **Cơ chế đối soát thông minh: Tiêu chí thời lượng cùng học ≥ 80%:**
  * Khi bấm **"Kết thúc buổi học"**, hệ thống tự động chốt thời gian ra và tính tổng thời lượng giao nhau (cùng online đồng thời) giữa người dạy và người học.
  * **Trường hợp cùng online ≥ 80% thời lượng quy định:**
    - Tự động hoàn thành phiên (`sessions.trang_thai = 'hoan_thanh'`).
    - Tự động ghi 2 dòng `credits_ledger` (`+so_gio` cho người dạy, `-so_gio` cho người học) và cập nhật số dư tức thì.
  * **Trường hợp cùng online < 80% thời lượng quy định:**
    - Tuyệt đối không tự động chuyển giờ!
    - Phiên học chuyển sang trạng thái `'can_xac_minh'`.
    - Thông báo rõ ràng cho học sinh và gửi yêu cầu tới Giáo viên / Ban Giám Hiệu để kiểm tra nhật ký và duyệt tay.

- **Dashboard Giám sát phòng học ảo cho Giáo viên & Admin (`/virtual-rooms`):**
  * Danh sách các lớp học trực tuyến đang diễn ra với tính năng **"Ghé thăm phòng học" (Dự giờ sư phạm)** bất kỳ lúc nào.
  * Danh sách các phiên học cần xác minh thời lượng (&lt; 80%) với tính năng **"Duyệt tay & Chuyển giờ"** hoặc **"Hủy phiên"**.

- **Chạy kiểm thử nghiệm thu Milestone M3+:**
  ```bash
  python test_m3_plus.py
  ```
  * Kết quả: 4/4 test cases đạt chuẩn 100%.

---

---

## 12. Trợ lý AI Thông minh & 5 Điểm chạm Sư phạm (Milestone M-AI)

Tích hợp Trợ lý Trí tuệ Nhân tạo thế hệ mới (Gemini Pro API) đồng hành cùng học sinh và giáo viên trong toàn bộ chu trình trao đổi tri thức học đường:

### 5 Điểm chạm AI Cốt lõi:
1. **AI Kiểm duyệt kỹ năng (`ai_moderate_skill`):**
   - Khi học sinh đăng ký kỹ năng mới (`/skills/new`), AI thẩm định tính phù hợp với môi trường sư phạm phổ thông.
   - Nội dung tích cực, lành mạnh $\rightarrow$ Phê duyệt tự động (`da_duyet`), hiển thị ngay trên Chợ kỹ năng.
   - Nội dung có dấu hiệu vi phạm (bạo lực, cờ bạc, gian lận thi cử) $\rightarrow$ Chuyển trạng thái `'cho_duyet'` để Giáo viên duyệt tay, ghi nhận lý do sư phạm vào `ly_do_ai_kiem_duyet`.
2. **AI Gợi ý ghép cặp bạn học (`ai_matchmake`):**
   - Nút nổi bật **"AI Gợi Ý Ghép Cặp"** tại Chợ kỹ năng dẫn đến giao diện `/skills/matchmake`.
   - Học sinh nhập môn học cần bổ trợ, trình độ và khung giờ rảnh.
   - Gemini chọn lọc 3 gia sư phù hợp nhất, đưa ra lời giải thích sư phạm tiếng Việt ngắn gọn và nút **"Đặt lịch ngay"**.
3. **AI Soạn dàn ý buổi học 4 bước 60 phút (`ai_generate_lesson_plan`):**
   - Trong trang chi tiết phiên học (`/sessions/<id>`), người dạy bấm nút **"Nhờ AI soạn dàn ý"**.
   - Gemini xây dựng cấu trúc bài học chuẩn mực 60 phút: *Mở đầu & Khởi động (5 phút)*, *Kiến thức trọng tâm (25 phút)*, *Kèm cặp & Luyện tập (20 phút)*, *Tổng kết & Đánh giá (10 phút)*.
   - Dàn ý lưu trực tiếp vào trường `sessions.dan_y_ai` để cả 2 bên cùng theo dõi.
4. **AI Tóm tắt phản hồi học sinh (`ai_summarize_feedback`):**
   - Hiển thị tại Dashboard/Hồ sơ người dạy (`/profile`).
   - Tổng hợp các đánh giá thực tế của bạn bè thành: **Điểm mạnh nổi bật** (2-3 ý) + **Gợi ý hoàn thiện** (2-3 ý) bằng giọng văn sư phạm chân thành, khích lệ.
5. **AI Cảnh báo sớm quản trị học đường (`ai_admin_early_warning`):**
   - Hiển thị tại Bảng điều khiển Quản trị (`/admin`) cho Ban Giám Hiệu và Giáo viên chủ nhiệm.
   - Tự động quét và phát hiện:
     * Học sinh hơn 7 ngày không tham gia phiên học nào (nguy cơ bị cô lập hoặc quên lịch).
     * Cặp đôi gia sư - người học bị đánh giá thấp (&le; 2 sao từ 2 lần trở lên).
   - Đề xuất các giải pháp can thiệp sư phạm nhân văn (nhắn tin riêng, đổi bạn học kèm cặp, mini-workshop).

### Nguyên tắc Vận hành An toàn & Minh bạch:
- **Cơ chế dự phòng Rule-Based (Graceful Degradation):** Nếu chưa cấu hình `GEMINI_API_KEY` hoặc API bên ngoài gặp sự cố mạng, hệ thống tự động chuyển sang chế độ cơ bản (rule-based heuristic), đảm bảo ứng dụng **KHÔNG BAO GIỜ CRASH**, giao diện hiển thị rõ *"Hỗ trợ bởi AI (Chế độ cơ bản)"*.
- **Lưu vết kiểm định (`ai_logs`):** 100% các lần gọi AI đều được ghi nhận vào bảng `ai_logs` (`user_id`, `chuc_nang`, `input_tom_tat`, `output_text`, `thoi_gian`).
- **Trung thực về AI:** Mọi vị trí có sự tham gia của AI trên giao diện đều được gắn nhãn nhận diện đồng bộ: `<span class="badge-ai"><i class="bi bi-stars"></i> Hỗ trợ bởi AI (Gemini)</span>`.

- **Chạy kiểm thử nghiệm thu Milestone M-AI:**
  ```bash
  python test_m_ai.py
  ```
  * Kết quả: 6/6 test cases đạt chuẩn 100%.

- **Chạy toàn bộ bộ kiểm thử hồi quy hệ thống (M0 + M1 + M2 + M3 + M3+ + M-AI):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m_ai.py
  ```
  * Kết quả: 30/30 test cases đạt chuẩn 100%.

---

## 13. Quiz Trắc Nghiệm AI Adaptive & Đo lường Kết quả Học tập (Milestone M-AI+)

Hệ thống bổ sung chu trình khép kín đánh giá lượng giá năng lực học sinh sau mỗi buổi trao đổi tri thức bằng Quiz trắc nghiệm thông minh:

### Quy trình Sư phạm & Kỹ thuật:
1. **Khởi tạo Quiz bằng Trí tuệ Nhân tạo (`ai_generate_quiz`):**
   - Sau khi buổi học được xác nhận hoàn thành, người dạy (hoặc Giáo viên) bấm **"Nhờ AI tạo quiz"** tại trang chi tiết phiên (`/sessions/<id>`).
   - Gemini Pro phân tích nội dung dàn ý buổi học (`sessions.dan_y_ai`) và mô tả kỹ năng (`skills.mo_ta`) để biên soạn **5 câu trắc nghiệm 4 lựa chọn** (A, B, C, D) theo mức độ nhận thức từ dễ đến khó.
   - Ngôn ngữ tiếng Việt tự nhiên, giọng văn vui tươi, gần gũi, khích lệ như trò chơi trí tuệ học đường.
   - Câu hỏi được lưu tự động vào bảng `quiz_questions` và ghi vết minh bạch vào `ai_logs` (`chuc_nang = 'tao_quiz'`).
2. **Tự đánh giá mức độ tự tin đầu vào (`tu_danh_gia_truoc`):**
   - Trước khi làm bài, học sinh tự đánh giá: *"Trước buổi học, em tự tin ở mức nào về chuyên đề này? (1 - 5 sao)"*.
   - Chỉ số này giúp đo lường mức độ tiến bộ năng lực và giá trị gia tăng tri thức mà buổi học đem lại.
3. **Làm bài và chấm điểm tự động trong app (Chặn làm lại lần 2):**
   - Học sinh thực hiện bài kiểm tra trực tiếp trên nền tảng web tại `/sessions/<id>/quiz`.
   - **Chặn làm lại lần 2:** Mỗi học sinh chỉ được làm bài **1 lần duy nhất** nhằm đảm bảo tính khách quan và trung thực sư phạm.
   - Hệ thống tự động chấm điểm, hiển thị tỷ lệ % đạt được, giải thích đáp án đúng/sai để học sinh ôn tập củng cố bài giảng.
   - Nếu đạt $\ge 60\%$ ($\ge 3/5$ câu đúng): Hệ thống tự động cập nhật cờ `sessions.quiz_dat_chuan = 1`.
4. **Bảng điều khiển "Kết quả học tập" cho Giáo viên & Quản trị viên (`/admin`):**
   - Thống kê trực quan 4 chỉ số cốt lõi:
     * **% Phiên đạt chuẩn Quiz (≥60%):** Tỷ lệ phiên học sinh nắm vững kiến thức trọng tâm.
     * **% Đạt điểm Giỏi (≥4/5 điểm):** Tỷ lệ học sinh tiếp thu xuất sắc.
     * **So sánh Tự đánh giá trước vs Điểm thực tế sau:** Minh chứng trực quan sự tiến bộ năng lực của học sinh.
     * **Điểm trung bình theo từng môn học:** Toán, Lý, Hóa, Ngoại ngữ, Tin học, Năng khiếu...
5. **Nguyên tắc Sư phạm Nhân văn Cốt lõi:**
   - Quiz trắc nghiệm dùng để **XÁC NHẬN kết quả học tập** cho giáo viên theo dõi và định hướng hỗ trợ, **TUYỆT ĐỐI KHÔNG CHẶN** việc cộng/trừ giờ tín dụng của học sinh (đã được ghi nhận vào sổ cái lúc hoàn thành phiên).
   - Quy tắc này giúp tránh phạt oan học sinh có xuất phát điểm còn yếu, khuyến khích tinh thần dám học hỏi và tự tin trao đổi tri thức.

### Hướng dẫn kiểm thử nghiệm thu Milestone M-AI+:
- **Chạy riêng bộ kiểm thử M-AI+:**
  ```bash
  python test_m_ai_plus.py
  ```
  * Kết quả: 6/6 test cases đạt chuẩn 100%.

- **Chạy toàn bộ bộ kiểm thử hồi quy hệ thống (M0 + M1 + M2 + M3 + M3+ + M-AI + M-AI+):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m_ai.py ; python test_m_ai_plus.py
  ```
  * Kết quả: 36/36 test cases đạt chuẩn 100%.

---

## 14. Đánh giá Tương hỗ, Dashboard Nâng cao & Xuất CSV Nghiên cứu Sư phạm (Milestone M4-lite)

Hệ thống hoàn thiện chu trình vận hành sư phạm và xuất báo cáo khoa học phục vụ nghiên cứu thực nghiệm:

### 1. Đánh giá tương hỗ 2 chiều sau hoàn thành (`/sessions/<id>/rate`):
- Sau khi phiên học được xác nhận hoàn thành, cả 2 bên (Người dạy và Người học) thực hiện đánh giá lẫn nhau:
  * Số sao: 1 - 5 sao
  * Nhận xét định tính chân thành, khích lệ
- **Chặn đánh giá 2 lần (Tiêu chí nghiệm thu):** Mỗi thành viên chỉ được đánh giá 1 lần duy nhất cho mỗi phiên học để đảm bảo tính khách quan và tin cậy sư phạm.

### 2. Dashboard Học sinh & Quản trị nâng cao:
- **Dashboard Học sinh (`/profile`):**
  * **Tổng giờ đã dạy:** Giờ công hiến kèm cặp bạn học.
  * **Tổng giờ đã học:** Giờ tham gia tiếp thu tri thức.
  * **Sao trung bình (Sao TB):** Điểm uy tín sư phạm trung bình nhận được từ bạn bè.
- **Dashboard Giáo viên / Quản trị viên (`/admin`):**
  * **Tổng phiên học:** Số phiên trao đổi tri thức trên toàn trường.
  * **Tổng giờ lưu thông:** Tổng số giờ trao đổi thành công từ các phiên hoàn thành.
  * **Bảng vinh danh Top học sinh tích cực nhất:** Top 5 gương sáng học đường cống hiến nhiều giờ dạy nhất.
  * **AI Cảnh báo sớm:** Quét học sinh ngưng học & cặp đôi xung đột.
  * **Kết quả học tập:** Phân tích điểm trung bình và chuẩn đầu ra qua Quiz.

### 3. Nút "Xuất CSV" Dữ liệu Nghiên cứu Sư phạm (`/admin/export-csv`):
- Nút bấm **"Xuất CSV (Nghiên cứu sư phạm)"** nổi bật tại thanh tác vụ Bảng điều khiển Quản trị.
- Gộp đầy đủ 5 bảng dữ liệu cốt lõi:
  1. `SESSIONS` (Phiên học)
  2. `CREDITS_LEDGER` (Sổ cái biến động giờ)
  3. `RATINGS` (Đánh giá tương hỗ 2 chiều)
  4. `QUIZ_RESULTS` (Lượng giá Quiz)
  5. `AI_LOGS` (Nhật ký minh bạch tương tác AI)
- **Chuẩn hóa mở bằng Excel:** Tệp xuất mã hóa chuẩn UTF-8 with BOM (`utf-8-sig`), mở trực tiếp bằng Microsoft Excel trên Windows hoàn toàn không bị lỗi font tiếng Việt.
- **BẢO MẬT PII NGHIÊM NGẶT (Tiêu chí nghiệm thu):** Toàn bộ họ tên thật của học sinh và giáo viên đều được **ẩn danh hóa 100%** thành mã định danh (`HS12001`, `HS11002`, `GV001`...), tuyệt đối không lộ danh tính cá nhân trong tệp nghiên cứu xuất ra.

### Hướng dẫn kiểm thử nghiệm thu Milestone M4-lite:
- **Chạy riêng bộ kiểm thử M4-lite:**
  ```bash
  python test_m4_lite.py
  ```
  * Kết quả: 6/6 test cases đạt chuẩn 100%.

- **Chạy toàn bộ 42 test cases kiểm thử hồi quy hệ thống (M0 -> M4-lite):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m_ai.py ; python test_m_ai_plus.py ; python test_m4_lite.py
  ```
  * Kết quả: 42/42 test cases đạt chuẩn 100%.

---

## 15. Hoạt động Vì cộng đồng & Giờ công ích Học đường (Milestone M6)

Mô hình Ngân hàng Thời gian Học đường được mở rộng vượt bậc từ việc trao đổi kỹ năng giữa 2 bạn học sinh sang **hoạt động phụng sự cộng đồng và trường học ("giờ công ích")**:

### 1. Giáo viên / Quản trị viên khởi tạo nhiệm vụ cộng đồng:
- Thầy cô và Đoàn trường tạo các hoạt động cống hiến thực tế:
  * *"Dọn rác bãi biển Hạ Long sáng Chủ nhật"* (+2.0h thưởng)
  * *"Hỗ trợ thư viện trường sắp xếp sách"* (+1.5h thưởng)
  * *"Dạy kỹ năng số cho các em khối Tiểu học"* (+2.0h thưởng)
- Thuộc tính nhiệm vụ: Tiêu đề, mô tả yêu cầu, địa điểm, số giờ thưởng, số lượng học sinh tối đa, hạn đăng ký.
- Nhiệm vụ tạo xong tự động chuyển sang trạng thái `mo_dang_ky`.
- **Phân quyền chặt chẽ:** Chỉ Giáo viên (`giao_vien`) hoặc Quản trị viên (`admin`) mới có quyền tạo nhiệm vụ; học sinh cố tình thao tác sẽ bị hệ thống chặn với mã lỗi **403 Forbidden**.

### 2. Không gian "Vì cộng đồng" (`/community`) & Đăng ký tham gia:
- Liệt kê toàn bộ các hoạt động công ích đang mở với số lượng chỉ tiêu và thời hạn rõ ràng.
- Học sinh bấm **"Đăng ký tham gia"** chỉ với 1 click.
- **Cơ chế kiểm soát tự động:**
  * **Khóa khi đủ số lượng:** Nếu số bạn đăng ký đã đạt `so_luong_toi_da`, nút chuyển sang trạng thái vô hiệu hóa kèm nhãn *"Đã đủ số lượng"*.
  * **Khóa khi quá hạn:** Nếu ngày hiện tại vượt quá `han_dang_ky`, nút chuyển sang vô hiệu hóa kèm nhãn *"Đã hết hạn đăng ký"*.
  * **Chống trùng lặp:** Học sinh đã đăng ký sẽ hiển thị nhãn *"Bạn đã đăng ký tham gia"*.

### 3. Giáo viên điểm danh sau hoạt động & Cơ chế Sổ cái Tín dụng:
- Giáo viên truy cập giao diện điểm danh `/community/tasks/<id>/attendance` để ghi nhận kết quả tham gia thực tế:
  * **'hoan_thanh' (Tham gia đầy đủ):** Hệ thống lập tức `INSERT credits_ledger` với nguyên tắc bất biến: `bien_dong = +so_gio_thuong`, `ly_do = 'nhiem_vu_cong_dong'`, đồng thời cập nhật tăng trực tiếp vào `users.so_du_gio`. Học sinh có thể dùng ngay số giờ thưởng này để đổi lấy các buổi học kỹ năng từ bạn bè.
  * **'vang_mat' (Vắng mặt không lý do):** Cập nhật trạng thái `vang_mat`, **tuyệt đối KHÔNG cộng giờ thưởng**, đảm bảo tính nghiêm minh và công bằng sư phạm.

### 4. Điểm chạm AI: "Việc phù hợp với bạn" (Gemini Pro):
- Tại trang `/community`, Trợ lý AI Cố vấn Học đường tự động phân tích hồ sơ của học sinh: thế mạnh kỹ năng đang sở hữu, sở thích cá nhân, các phiên học đã trao đổi.
- AI (Gemini Pro) đề xuất **3 nhiệm vụ phù hợp nhất** kèm lời giải thích ngắn gọn, ấm áp và khích lệ bằng tiếng Việt:
  * Ví dụ: *"Tận dụng tốt thế mạnh kỹ năng số và tin học của bạn để đóng góp vào hoạt động chuyển đổi số của trường."*
- Minh bạch: Giao diện gắn huy hiệu `Hỗ trợ bởi AI (Gemini Pro)` hoặc `Chế độ cơ bản (Rule-based)`.
- Ghi vết suy luận của AI vào bảng `ai_logs` với `chuc_nang = 'goi_y_nhiem_vu'`.

### 5. Khối "Vì cộng đồng" trên Landing Page (`/`):
- Hiển thị tổng số giờ công ích đã đóng góp trên toàn trường (tổng hợp realtime từ `credits_ledger`).
- Trình bày 3 nhiệm vụ cộng đồng gần nhất để phụ huynh, giáo viên và học sinh toàn trường cùng theo dõi, hưởng ứng.

### Hướng dẫn kiểm thử nghiệm thu Milestone M6:
- **Chạy riêng bộ kiểm thử M6:**
  ```bash
  python test_m6.py
  ```
  * Kết quả: **6/6 test cases đạt chuẩn 100% OK**.

- **Chạy toàn bộ 48 test cases kiểm thử hồi quy hệ thống (M0 -> M6):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m4_lite.py ; python test_m_ai.py ; python test_m_ai_plus.py ; python test_m6.py
  ```
  * Kết quả: **48/48 test cases đạt chuẩn 100% OK**.

---

## 16. Trợ lý Học đường AI — Khung Chat Tương tác Cá nhân hóa (Milestone M-CHAT)

Nền tảng tích hợp **Trợ lý Học đường AI (TimeBank Assistant)** hoạt động 24/7 dưới dạng khung chat nổi tiện lợi (biểu tượng 💬 ở góc dưới bên phải mọi màn hình sau khi đăng nhập):

### 1. Phản hồi thông minh với Ngữ cảnh Cá nhân hóa (Personalized Context):
- Trợ lý không chỉ trả lời kiến thức chung mà được nạp trực tiếp hồ sơ người học vào System Prompt:
  * **Họ tên & Lớp của học sinh:** Giao tiếp tự nhiên, gần gũi như người cố vấn học đường thực thụ.
  * **Số dư tín dụng giờ thực tế:** Đọc trực tiếp từ `users.so_du_gio`. Khi học sinh hỏi *"Tôi còn bao nhiêu giờ?"*, AI trả lời chính xác số dư thật đến từng chữ số thập phân.
  * **Kỹ năng đã chia sẻ:** Nắm rõ thế mạnh của học sinh để định hướng phát triển.
  * **Lịch hẹn học tập sắp tới:** Đọc các phiên có trạng thái `da_dat` để giải đáp cụ thể.
- Mọi tương tác hội thoại được lưu vết vào bảng `chat_messages` (`vai_tro` 'user'/'assistant') và bảng minh bạch `ai_logs` (`chuc_nang = 'tro_ly_ao'`).

### 2. Chủ động nhắc lịch học tập (Smart Greeting & Reminder):
- Mỗi lần học sinh mở khung chat, Trợ lý chủ động kiểm tra và gửi lời chào kèm lời nhắc:
  * *"Xin chào [Tên HS]! Bạn có [N] lịch hẹn sắp tới: • [Chi tiết môn, bạn học, thời gian]... Số dư ví hiện tại: [X]h. Bạn cần hỗ trợ gì thêm không?"*
- Nếu không có lịch hẹn, trợ lý gợi ý học sinh ghé thăm Chợ kỹ năng để ghép cặp đôi bạn cùng tiến.

### 3. Gợi ý câu hỏi nhanh (Quick Prompts):
- 4 nút bấm gợi ý phổ biến giúp học sinh thao tác nhanh chóng trên cả điện thoại:
  * *"Tôi còn bao nhiêu giờ?"* $\rightarrow$ Tra cứu số dư tức thì.
  * *"Lịch học sắp tới của tôi?"* $\rightarrow$ Điểm danh các buổi học đã hẹn.
  * *"Làm sao đăng kỹ năng?"* $\rightarrow$ Hướng dẫn quy trình chia sẻ tri thức.
  * *"Gợi ý lộ trình học Toán trong 4 tuần?"* $\rightarrow$ Thiết kế lộ trình sư phạm bài bản từ củng cố lý thuyết đến làm Quiz lượng giá.

### 4. Chế độ dự phòng thông minh (Rule-based Fallback):
- Khi trường học gặp sự cố mất mạng hoặc chưa cấu hình API Key, Trợ lý tự động chuyển sang chế độ dự phòng theo bộ FAQ sư phạm chuẩn hóa, **cam kết hệ thống không bao giờ gặp lỗi 500 hay gián đoạn trải nghiệm**.

### Hướng dẫn kiểm thử nghiệm thu Milestone M-CHAT:
- **Chạy riêng bộ kiểm thử M-CHAT:**
  ```bash
  python test_m_chat.py
  ```
  * Kết quả: **6/6 test cases đạt chuẩn 100% OK**.

- **Chạy toàn bộ 54 test cases kiểm thử hồi quy hệ thống (M0 -> M-CHAT):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m4_lite.py ; python test_m_ai.py ; python test_m_ai_plus.py ; python test_m6.py ; python test_m_chat.py
  ```
  * Kết quả: **54/54 test cases đạt chuẩn 100% OK**.

---

## 17. HƯỚNG DẪN DEPLOY TRÊN RENDER & CẤU HÌNH TÊN MIỀN (Milestone DEPLOY)

Hệ thống được đóng gói sẵn sàng để triển khai trực tuyến trên nền tảng đám mây **Render (PaaS)** với quy trình chuẩn hóa, vận hành ổn định và bảo mật:

### 1. Cấu hình tệp khởi chạy đám mây:
- **`runtime.txt`**: Khai báo phiên bản môi trường `python-3.11.9`.
- **`Procfile`**: Lệnh khởi chạy máy chủ WSGI hiệu năng cao: `web: gunicorn app:app`.
- **`render.yaml`**: Bản thiết kế tự động (Render Blueprint) định nghĩa Web Service, các biến môi trường và thiết lập Production.
- **Tương thích Cơ sở dữ liệu linh hoạt:**
  * **Mặc định (Không có `DATABASE_URL`):** Hệ thống vận hành trơn tru với **SQLite cục bộ** (`database/timebank.db`), đảm bảo kiến trúc Single-Tenant chuẩn mực cho từng trường học.
  * **Khi có `DATABASE_URL`:** Hệ thống tự động kích hoạt bộ điều hợp **PostgreSQL** (`psycopg2-binary`), tự động chuẩn hóa chuỗi kết nối và khởi tạo 13 bảng dữ liệu.

---

### 2. Các bước triển khai chi tiết trên Render (Từng bước cụ thể):

#### Bước 1: Tạo tài khoản và Đăng nhập Render
1. Truy cập trang chủ [https://render.com](https://render.com).
2. Chọn **"Get Started for Free"** hoặc đăng nhập nhanh bằng tài khoản **GitHub** của trường học.

#### Bước 2: Kết nối Repository GitHub
1. Tại bảng điều khiển Render Dashboard, chọn **"New +"** $\rightarrow$ chọn **"Web Service"** (hoặc chọn **"Blueprint"** để Render tự đọc tệp `render.yaml`).
2. Chọn kho lưu trữ chứa mã nguồn dự án: `timebank-edu`.
3. Đặt tên dịch vụ: `timebank-edu` (hoặc tên viết tắt của trường, ví dụ: `timebank-thpt-chuyen`).
4. Chọn vùng triển khai (Region): `Singapore` (để tối ưu hóa tốc độ truy cập từ Việt Nam).
5. Nhánh (Branch): `main`.
6. Cấu hình lệnh:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`

#### Bước 3: Cấu hình Biến Môi trường (Environment Variables)
Tại mục **"Environment Variables"** trên Render, thêm các khóa bí mật:
- **`GEMINI_API_KEY`**: Dán mã khóa API Google Gemini Pro (lấy từ [Google AI Studio](https://aistudio.google.com)).
- **`SECRET_KEY`**: Nhập chuỗi bảo mật phiên ngẫu nhiên (hoặc Render tự sinh tự động nếu dùng `render.yaml`).
- **`FLASK_DEBUG`**: Đặt giá trị `0` để tắt chế độ gỡ lỗi (bảo mật production).
- **`DATABASE_URL`** *(Tùy chọn)*: Nếu trường muốn kết nối dịch vụ Render PostgreSQL, dán chuỗi kết nối vào đây; nếu không, để trống để hệ thống tự động sử dụng SQLite.

#### Bước 4: Khởi chạy triển khai (Deploy Web Service)
1. Bấm nút **"Create Web Service"** (hoặc **"Apply"**).
2. Render sẽ tự động kéo mã nguồn từ GitHub, cài đặt các gói trong `requirements.txt` và khởi động máy chủ Gunicorn.
3. Khi màn hình thông báo **"Your service is live 🎉"**, ứng dụng đã chạy công khai tại địa chỉ:
   `https://timebank-edu.onrender.com`

---

### 3. Hướng dẫn trỏ tên miền chính thức (`timebankedu.com`):

Sau khi ứng dụng đã chạy trên Render, thực hiện các bước sau để gắn tên miền riêng của nhà trường:

1. **Thêm Custom Domain trên Render:**
   - Vào mục **Settings** của Web Service `timebank-edu` trên Render Dashboard.
   - Cuộn xuống phần **Custom Domains** $\rightarrow$ Nhấn **"Add Custom Domain"**.
   - Nhập tên miền: `timebankedu.com` và `www.timebankedu.com` $\rightarrow$ Nhấn **Save**.

2. **Cấu hình bản ghi DNS tại Nhà cung cấp Tên miền (PA Việt Nam, Mắt Bão, Cloudflare...):**
   Đăng nhập vào trang quản trị DNS của tên miền `timebankedu.com` và tạo các bản ghi sau:

   | Loại bản ghi (Type) | Tên máy chủ (Host / Name) | Giá trị trỏ đến (Value / Target) | Mục đích |
   |:---:|:---:|:---:|---|
   | **CNAME** | `www` | `timebank-edu.onrender.com` | Trỏ tên miền phụ www về máy chủ Render |
   | **ANAME / ALIAS** *(hoặc A Record)* | `@` (root domain) | `timebank-edu.onrender.com` *(hoặc địa chỉ IP Render cung cấp)* | Trỏ tên miền gốc về máy chủ Render |

3. **Xác thực và Kích hoạt SSL/TLS (HTTPS Miễn phí):**
   - Sau khi cấu hình DNS (khoảng 5 - 15 phút), Render tự động xác minh bản ghi và cấp chứng chỉ bảo mật **SSL Let's Encrypt** hoàn toàn miễn phí.
   - Truy cập chính thức tại: `https://timebankedu.com` (tất cả kết nối HTTP đều được tự động chuyển hướng an toàn sang HTTPS).

---

### Hướng dẫn kiểm thử nghiệm thu Milestone DEPLOY:
- **Chạy riêng bộ kiểm thử DEPLOY:**
  ```bash
  python test_deploy.py
  ```
  * Kết quả: **6/6 test cases đạt chuẩn 100% OK**.

- **Chạy toàn bộ 60 test cases kiểm thử hồi quy hệ thống (M0 -> DEPLOY):**
  ```bash
  python test_m0.py ; python test_m1.py ; python test_m2.py ; python test_m3.py ; python test_m3_plus.py ; python test_m4_lite.py ; python test_m_ai.py ; python test_m_ai_plus.py ; python test_m6.py ; python test_m_chat.py ; python test_deploy.py
  ```
  * Kết quả: **60/60 test cases đạt chuẩn 100% OK**.

---

---

## 18. Tính bảo mật và biến môi trường
- File `.env` chứa `GEMINI_API_KEY` và `FLASK_SECRET_KEY` được bảo vệ nghiêm ngặt bằng `.gitignore`, **TUYỆT ĐỐI KHÔNG BAO GIỜ** được push lên GitHub công khai.
- Cung cấp file mẫu `.env.example` với hướng dẫn cấu hình chi tiết cho các trường triển khai.

---

## 19. Milestone M5-blog: Bảng tin học đường & AI Soạn bản tin tuần (Gemini Pro)

### 1. Ý nghĩa sư phạm & Triết lý vận hành
- **Bảng tin học đường (`/blog`):** Không gian truyền thông nội bộ nhà trường nhằm lan tỏa các câu chuyện đẹp về tinh thần chia sẻ kỹ năng, tinh thần trách nhiệm xã hội và văn hóa học tập đồng đẳng không dùng tiền mặt (1 giờ dạy = 1 tín dụng thời gian).
- **Trợ lý AI Biên tập viên (`bien_tap_vien`):** Hỗ trợ Thầy Cô giáo tự động tổng hợp hoạt động tuần thành bản tin hấp dẫn, chính xác và nhân văn mà không làm mất thời gian viết bài thủ công của giáo viên.

### 2. Các chức năng chính (CRUD Bài viết cho Giáo viên & Admin)
1. **Trang công khai (`/blog`):**
   - Liệt kê các bài viết và bản tin đã được duyệt/đăng chính thức (`trang_thai = 'da_dang'`).
   - Các bài viết bản nháp (`trang_thai = 'nhap'`) **TUYỆT ĐỐI KHÔNG HIỂN THỊ** đối với học sinh và khách vãng lai.
   - Thẻ bài viết hiển thị ảnh minh họa, tiêu đề, ngày đăng, trích đoạn nội dung và huy hiệu **"Hỗ trợ bởi AI (Gemini)"** đối với các bản tin do AI biên soạn.
2. **Trang chi tiết bài viết (`/blog/<id>`):**
   - Đọc toàn văn bài viết, định dạng phân đoạn sư phạm chuẩn mực.
   - Chế độ **Xem trước (Preview):** Khi bài viết đang là bản nháp, chỉ Giáo viên và Admin mới có thể xem trước, giao diện có banner cảnh báo màu vàng cùng nút nổi bật **"Duyệt & Đăng ngay (1-Click)"**. Học sinh truy cập bài nháp sẽ nhận mã lỗi 404 Not Found.
3. **Bảng quản lý bài viết (`/blog/manage`):**
   - Chỉ Giáo viên (`giao_vien`) và Admin (`admin`) mới có quyền truy cập (Học sinh bị chặn 403 Forbidden).
   - Thống kê tổng số bài, số bài đã đăng, số bản nháp và số bài do AI tạo.
   - Cung cấp nút 1-click **"Duyệt & Đăng"**, nút Chỉnh sửa (`/blog/<id>/edit`), Xóa bài (`/blog/<id>/delete`) và Viết bài mới (`/blog/create`).

### 3. Nút "Nhờ AI soạn bản tin tuần" (Gemini Pro API)
- **Cơ chế thu thập dữ liệu tự động 7 ngày gần nhất:**
  1. **Phiên học mới:** Đếm tổng số phiên và số giờ tín dụng lưu thông trong tuần từ bảng `sessions`.
  2. **Top 3 gia sư của tuần:** Truy vấn 3 học sinh dạy nhiều giờ nhất và đạt điểm đánh giá cao nhất (kèm họ tên thật, lớp từ bảng `users`).
  3. **Lĩnh vực hot:** Phân tích môn học/kỹ năng được trao đổi nhiều nhất trong tuần từ bảng `skills`.
  4. **Nhận xét 5 sao tiêu biểu:** Trích xuất 2-3 lời phản hồi 5 sao xuất sắc nhất từ bảng `ratings` (kèm họ tên người khen và người được khen).
- **Cấu trúc bản tin BẮT BUỘC ĐỦ 5 PHẦN SƯ PHẠM:**
  1. **Mở đầu:** Lời chào, không khí học tập tích cực và tinh thần tương trợ học đường.
  2. **Con số nổi bật:** Tóm tắt các con số thực tế ấn tượng (số phiên, số giờ, môn hot).
  3. **Vinh danh gia sư của tuần:** Nêu đích danh họ tên thật, lớp và lời khen ngợi cho Top 3 gia sư.
  4. **Câu chuyện tiêu biểu:** Trích dẫn các phản hồi 5 sao thực tế đầy xúc động giữa bạn bè.
  5. **Lời kêu gọi:** Động viên học sinh toàn trường tiếp tục mở ví, trao đổi kỹ năng và đồng hành cùng TimeBank EDU.
- **Quy trình duyệt 1-click (Human-in-the-loop):**
  - AI sinh bài viết và tự động lưu vào bảng `blog_posts` với `tac_gia_ai = 1`, `trang_thai = 'nhap'`.
  - Cô giáo chỉ cần xem lại nội dung và nhấn **"Duyệt & Đăng ngay" (1-Click)** $\rightarrow$ Bài chuyển sang `da_dang` và lập tức hiển thị công khai trên `/blog`.
- **Cơ chế dự phòng Rule-Based (Graceful Degradation):** Nếu chưa cấu hình `GEMINI_API_KEY` hoặc API mất kết nối mạng, thuật toán dự phòng tự động biên soạn bản tin chuẩn mực với đầy đủ 5 phần cấu trúc và dữ liệu học sinh thật, đảm bảo hệ thống không bao giờ gặp sự cố.

### 4. Hướng dẫn kiểm thử nghiệm thu Milestone M5-blog:
```bash
python test_m5_blog.py
```
* Bộ kiểm thử tự động gồm 6 test cases chuẩn:
  1. `test_01_access_control_blog_management`: Kiểm tra phân quyền RBAC chặt chẽ (Học sinh 403, Khách 302, GV/Admin 200).
  2. `test_02_crud_blog_posts`: Kiểm tra các thao tác Thêm, Sửa, Xóa bài viết thành công.
  3. `test_03_blog_index_filters_drafts`: Xác nhận trang `/blog` chỉ hiển thị bài đã đăng, bài nháp chưa duyệt không xuất hiện.
  4. `test_04_blog_detail_access_and_preview`: Xác nhận xem chi tiết bài viết và chế độ Preview bài nháp dành cho giáo viên.
  5. `test_05_ai_weekly_newsletter_generation`: Xác nhận bản tin AI lưu `tac_gia_ai=1`, `trang_thai='nhap'`, đủ 5 phần cấu trúc và chứa tên thật từ dữ liệu CSDL.
  6. `test_06_one_click_publish_workflow`: Xác nhận cơ chế duyệt 1-click của cô giáo hoạt động chuẩn xác, sau duyệt bài lập tức xuất hiện công khai trên `/blog` kèm huy hiệu AI.
* Kết quả: **6/6 test cases đạt chuẩn 100% OK**.

---

## 🏛️ PROMPT 17 — ĐẠI PHẪU ĐA TRƯỜNG (MULTI-TENANT CORE ARCHITECTURE)

Hệ thống được nâng cấp toàn diện từ mô hình đơn trường sang **Kiến trúc Đa trường ("Gian hàng học đường")** phục vụ đợt thí điểm thực tế, sẵn sàng mở rộng quy mô.

### 1. Kiến trúc Đa trường & Phân quyền 4 cấp (RBAC):
- **Bảng `truong`:** Quản lý danh mục các trường tham gia (`id`, `ten_truong`, `logo`, `trang_thai`, `ngay_tao`).
- **Seed 4 trường học:**
  1. *Trường Tiểu học, THCS, THPT Quốc tế song ngữ học viện Anh Quốc-UK Academy* (`dang_thi_diem`)
  2. *Trường THCS Nguyễn Văn Thuộc* (`chuan_bi_trien_khai`)
  3. *Trường THCS Lê Văn Tám* (`chuan_bi_trien_khai`)
  4. *Trường THPT Hải Đảo* (`chuan_bi_trien_khai`)
- **Phân quyền 4 cấp nghiêm ngặt:**
  - `super_admin`: Tài khoản quản trị tối cao (Cô Nguyễn Thị Huyền) — thấy, quản lý và duyệt toàn bộ 4 trường; có chức năng "Duyệt tất cả" hàng loạt.
  - `school_admin`: Quản trị viên riêng của từng trường — chỉ thấy và quản lý dữ liệu trường mình (duyệt kỹ năng, sinh mã mời, duyệt học sinh, xử lý vi phạm).
  - `giao_vien`: Giám sát sư phạm, dự giờ phòng học ảo, duyệt kỹ năng và bài viết.
  - `hoc_sinh`: Tham gia học tập, chia sẻ kỹ năng và tương tác trong không gian trường mình.
- **Cách ly dữ liệu (Data Isolation):** Mọi query dữ liệu (chợ kỹ năng, phòng học ảo, hoạt động cộng đồng, bài viết, sổ vi phạm) đều tự động lọc theo `truong_id` của người dùng đăng nhập.

### 2. Bảo vệ Đăng ký & Cơ chế Mã mời (Anti-Impersonation):
- Bảng `invite_codes` sinh mã ngẫu nhiên chuẩn hóa dạng `TBEDU-XXXX-XXXX` (phân loại mã lớp dùng chung hoặc mã cá nhân 1 lần).
- Đăng ký nhập mã hợp lệ $\rightarrow$ Tự động gán đúng trường và kích hoạt tài khoản ngay lập tức (`hoat_dong`, cấp 2.0h khởi đầu).
- Đăng ký không có mã $\rightarrow$ Tự chọn trường và chuyển vào trạng thái `cho_duyet`, bị chặn đăng kỹ năng và đặt lịch học cho đến khi được quản trị viên trường hoặc cô Huyền phê duyệt.

### 3. AI Lọc Chat Realtime & Kỷ luật 3 Mức độ:
- Lọc tin nhắn realtime trong khung chat: Từ điển từ cấm kết hợp biểu thức chính quy (Regex) bắt biến thể lách luật và Gemini AI phân tích ngữ cảnh học đường.
- Bảng `violations` ghi nhận vi phạm với 3 mức độ nhân văn:
  - **Lần 1:** Bot tự động nhắc nhở ngay trong chat.
  - **Lần 2:** Cảnh cáo chính thức và thông báo tới Ban Quản trị nhà trường.
  - **Lần 3:** Hệ thống ĐỀ XUẤT khóa và chuyển hồ sơ chờ Quản trị viên bấm xác nhận mới khóa thật (tuyệt đối không tự động khóa vĩnh viễn).
- Nút **"Báo cáo vi phạm"** được tích hợp trực tiếp trong phòng học ảo để học sinh báo cáo hành vi không chuẩn mực cho giáo viên phụ trách.

### 4. Trang Nội quy Học đường (`/noi-quy`) & Thương hiệu Mới:
- Trang trọng công bố **6 Điều Quy tắc Vàng** (Trung thực, Trang phục, Ngôn ngữ, Lành mạnh, Công bằng, Tôn trọng) và chế tài 3 cấp độ.
- Tiêu đề trung tâm trang chủ đổi mới: **"School Time Bank"** kèm dòng phụ đề in nghiêng *"Ngân hàng Thời gian Học đường"*.
- Xóa bỏ định danh cũ tại Header, Hero và Footer; chỉ giữ trong danh mục các trường tham gia.

### 5. Kiểm thử Tự động & Regression Toàn diện:
- Bộ test suite `test_prompt17_multitenant.py` nghiệm thu 8/8 tiêu chí khắt khe.
---

## 💬 PROMPT 18 — DIỄN ĐÀN "GÓC TRÒ CHUYỆN" & KHO GOOGLE DRIVE 5TB

### 1. Diễn đàn Học đường "Góc Trò Chuyện":
- Bảng `forum_topics` và `forum_replies` hỗ trợ học sinh và giáo viên tạo chủ đề, thảo luận tương tác.
- Cách ly trường học: Mỗi trường chỉ thấy và tham gia diễn đàn của trường mình (`truong_id`).
- AI lọc từ tục realtime: Kế thừa cơ chế phòng vệ kép (từ điển + regex + AI), vi phạm ghi nhận tự động vào bảng `violations`.
- Phân quyền kiểm duyệt: Giáo viên và Quản trị trường có quyền khóa chủ đề hoặc xóa bình luận không phù hợp.

### 2. Kho Tài liệu Google Drive 5TB Toàn Hệ thống:
- Sử dụng tài khoản Google Drive 5TB làm kho lưu trữ học tập tập trung toàn hệ thống.
- Cấu trúc thư mục sư phạm tự động: Thư mục gốc `TimeBank-EDU-Shared-5TB/` phân chia theo từng trường học và môn học.
- Quản trị viên Super Admin kết nối tài khoản Google qua OAuth 2.0 hoặc Service Account.
- Stream tải lên & tải về an toàn, không tốn bộ nhớ đĩa cục bộ.

---

## 🌐 PROMPT 19 — SÀN GIAO DỊCH CHUNG LIÊN TRƯỜNG & CỔNG 24 TÍN DỤNG

### 1. Cổng Kiểm Chuẩn 24 Tín Dụng (Cổng Mở Khóa Sàn Chung):
- Tham số cấu hình `cong_dong_nguong_tin_dung: 24` trong `config.yaml` — **TUYỆT ĐỐI không hardcode số 24 trong mã nguồn**.
- **"Tín dụng kiếm được từ dạy thật"**: Tổng số giờ các buổi học mà học sinh làm **Người dạy** và trạng thái đạt `'hoan_thanh'`. Tuyệt đối không tính 2 giờ tặng ban đầu.
- Học sinh chưa đạt ngưỡng $\rightarrow$ Vào Sàn chung thấy màn hình **Cổng Kiểm Chuẩn** với thông báo: *"Bạn cần [X] giờ dạy nữa để mở khóa Sàn cộng đồng"* kèm thanh tiến trình trực quan và định hướng sư phạm.
- Học sinh đạt ngưỡng $\rightarrow$ Hệ thống tự động mở khóa và gắn huy hiệu **"Thành viên Cộng đồng"** trên hồ sơ cá nhân.

### 2. Sàn Giao Dịch Tri Thức & Kỹ Năng Liên Trường:
- Mở rộng bảng `skills` với các trường: `hien_thi_cong_dong` (0/1), `trang_thai_cong_dong` (`chua_dang`, `cho_duyet`, `da_duyet`, `tu_choi`), `nguoi_duyet_cong_dong_id`, `ngay_duyet_cong_dong`.
- Chủ kỹ năng (đã qua cổng kiểm chuẩn) có nút **"Đăng lên sàn chung"** trên hồ sơ $\rightarrow$ Kỹ năng chuyển sang trạng thái chờ duyệt. Học sinh chưa qua cổng không thấy nút này.
- **Cơ chế duyệt linh hoạt liên trường:** Tổng quản trị HOẶC Quản trị viên bất kỳ trường nào đều có quyền duyệt (một người duyệt là đủ). Hệ thống ghi log định danh người duyệt.
- Kỹ năng đã duyệt hiển thị công khai trên Sàn chung kèm **TÊN TRƯỜNG** của chủ kỹ năng.
- Học sinh trường A đặt lịch học kỹ năng của trường B hoàn toàn bình thường; tín dụng giờ được luân chuyển liên trường qua **VÍ CHUNG DUY NHẤT** (không tách ví).

### 3. Giao diện & Trải nghiệm Người dùng:
- Menu điều hướng bổ sung mục **"Sàn cộng đồng"** (phân biệt rạch ròi với "Chợ kỹ năng" nội trường).
- Bảng điều khiển Quản trị (`/admin`) bổ sung tab **"Duyệt Sàn Chung"** hiển thị danh sách kỹ năng chờ duyệt từ mọi trường học.
- Hồ sơ học sinh hiển thị huy hiệu vinh danh **"Thành viên Cộng đồng"** khi đạt chuẩn.

### 4. Kết quả Kiểm thử & Nghiệm thu (Test Suite):
- Bộ test suite chuyên sâu `test_prompt19_community_market.py` vượt qua **7/7 test cases (100% PASS)**:
  1. Học sinh 23 giờ dạy bị chặn ở cổng, hiển thị số giờ còn thiếu chính xác (1 giờ).
  2. Học sinh 24 giờ dạy tự động mở khóa và nhận huy hiệu "Thành viên Cộng đồng".
  3. Thay đổi ngưỡng trong `config.yaml` áp dụng ngay lập tức (chứng minh không hardcode).
  4. Đăng kỹ năng lên sàn chung $\rightarrow$ Admin trường khác duyệt thành công $\rightarrow$ Hiển thị trên sàn kèm tên trường.
  5. Học sinh trường A học xong buổi trường B $\rightarrow$ Ví chung cộng/trừ chính xác, không sai lệch.
  6. Học sinh chưa qua cổng không thấy nút "Đăng lên sàn chung".
  7. Regression suite toàn bộ **15/15 test suites đạt 100% PASS**.

---

## 🏫 PROMPT 30 — QUẢN LÝ TRƯỜNG HỌC (THÊM / SỬA / VÔ HIỆU HÓA TRƯỜNG MỚI)

Nâng cấp Bảng điều khiển Quản trị (`/admin`) giúp Cô Huyền (Tổng Quản trị - `super_admin`) chủ động thêm trường học mới khi có trường đối tác đăng ký tham gia mô hình TimeBank EDU, chỉnh sửa thông tin hoặc vô hiệu hóa trường khi cần:

### 1. Tab "Quản lý Trường học" trong `/admin`:
- **Chỉ hiển thị cho `super_admin`:** Thẻ Tab riêng biệt có badge hiển thị số lượng trường đang quản trị.
- **Form thêm trường học mới:**
  - Tên trường (*): validate bắt buộc, không được để trống, không được trùng với trường đã có (case-insensitive).
  - Trạng thái ban đầu: Đang thí điểm (`dang_thi_diem`), Chuẩn bị triển khai (`chuan_bi_trien_khai`), Đang sử dụng (`dang_su_dung`).
  - Logo trường: hỗ trợ tải lên tệp ảnh thực tế (PNG, JPG, WEBP) hoặc tự động dùng logo mặc định hệ thống.
  - Tự động sinh `truong_id` tiếp theo kế tiếp an toàn, tuyệt đối không đè lên ID mẫu của Trường Demo (`DEMO_SCHOOL_ID = 99`).
- **Bảng danh sách trường học quản trị:**
  - Cột hiển thị: Mã ID, Logo trường, Tên trường, Trạng thái (badge màu sắc trực quan), Số lượng tài khoản hiện tại, Ngày tạo, Thao tác.
  - Nút **"Sửa"**: Mở modal cho phép sửa tên trường, cập nhật logo mới và thay đổi trạng thái hoạt động.
  - Nút **"Vô hiệu hóa" / "Kích hoạt"**: Chuyển đổi trạng thái mềm (`vo_hieu_hoa`), tuyệt đối **không xóa cứng** để bảo toàn toàn vẹn dữ liệu học sinh, phiên học và sổ cái thời gian.
  - **Bảo vệ Trường Demo (ID 99):** Hiển thị huy hiệu "Cố định (Không sửa/xóa)", các nút chỉnh sửa/vô hiệu hóa bị khóa và được bảo vệ nghiêm ngặt ở tầng backend.

### 2. Tự động liên kết và cách ly dữ liệu trường mới:
- Trường mới tự động xuất hiện trong dropdown lọc trường tại `/admin`.
- Trường mới có thể sinh mã mời riêng (`invite_codes`), tạo tài khoản quản trị trường (`school_admin`) và giáo viên (`giao_vien`) riêng biệt.
- Khi trường bị vô hiệu hóa (`vo_hieu_hoa`):
  - Tự động ẩn khỏi danh sách lựa chọn trường trên form đăng ký (`/register`).
  - Hệ thống từ chối các mã mời thuộc về trường bị vô hiệu hóa kèm thông báo rõ ràng.
  - Khi được kích hoạt lại (`dang_su_dung`), trường lập tức xuất hiện trở lại trên form đăng ký.

### 3. Nghiệm thu & Regression Suite:
- Bộ test suite `test_prompt30_school_management.py` bao gồm 8 test cases chuyên sâu kiểm thử toàn diện quy trình thêm, sửa, validate, phân quyền, cách ly dữ liệu và bảo vệ trường Demo.
- Toàn bộ **29/29 bộ test trong hệ thống (100% PASS)** xác nhận không có bất kỳ lỗi hồi quy nào.

---

## 🎨 PROMPT 31 — CHỈNH TỪ NGỮ + PHỐI MÀU GIAO DIỆN HIỆN ĐẠI

Nâng cấp giao diện người dùng và nhận diện thương hiệu học đường chuẩn mực, tinh tế và hiện đại:

### 1. Chuẩn hóa từ ngữ toàn site (UI Wording):
- **"GIAN HÀNG" → "TRƯỜNG HỌC":**
  - Trang chủ: *"HỆ THỐNG GIAN HÀNG ĐA TRƯỜNG"* → *"HỆ THỐNG ĐA TRƯỜNG HỌC"*; *"Gian hàng #1"* → *"Trường #1"*.
  - Bảng Quản trị (`/admin`): *"Hệ thống Quản trị Gian hàng Đa trường"* → *"Hệ thống Quản trị Đa trường học"*.
  - Trang Đăng ký (`/register`): *"Hệ thống Gian hàng Đa trường — School Time Bank"* → *"Hệ thống Đa trường học — School Time Bank"*.
- **"phòng học JaaS WebRTC" → "lớp học ảo":**
  - Trang chủ: *"Trải nghiệm phòng học JaaS WebRTC hiện đại"* → *"Trải nghiệm lớp học ảo hiện đại"*.
  - Trang phòng học ảo (`/phong-hoc/<id>`): Tiêu đề, hướng dẫn và thông báo kết nối chuyển sang *"Lớp học ảo trực tuyến"* thân thiện, ẩn hoàn toàn các tên công nghệ kỹ thuật bên dưới khỏi mắt học sinh/giáo viên.
- **Giữ nguyên code kỹ thuật:** Các biến cấu hình môi trường, hàm backend và log kỹ thuật được bảo toàn nguyên vẹn 100%.

### 2. Dấu ngoặc kép chuẩn tiếng Việt:
- Câu slogan sư phạm: `“Một giờ bạn dạy — một giờ bạn được học.”` được sửa đúng chuẩn dấu mở `“` và đóng `”` tiếng Việt, loại bỏ lỗi hiển thị 2 icon đóng `bi-quote` trước đây.

### 3. Phối màu hiện đại (Modern Palette & UI/UX):
- **Menu ngang (`.navbar-custom .nav-link`):**
  - Tách từng mục thành các tab pill bo tròn (`border-radius: 9999px`) với màu nền nhẹ `#F8FAFC` và viền `#E2E8F0`, chữ `#1E293B` tương phản cao dễ đọc.
  - Hover chuyển sang nền cam ấm `#FFF7ED` viền `#FED7AA` và chữ `#EA580C`.
  - Mục active hiển thị dải màu gradient cam-vàng chủ đạo (`#F26522` → `#F59E0B`) nổi bật.
  - Tối ưu hoàn hảo trên cả desktop, laptop nhỏ và mobile menu drawer.
- **4 thẻ mô hình hoạt động (`.step-card`):**
  - Đổ 4 màu nền pastel dịu mắt riêng biệt cho 4 bước:
    - Bước 1 (Đăng kỹ năng): Nền cam ấm `#FFF7ED` → `#FFFFFF`, viền `#FFEDD5`, badge cam `#F26522`.
    - Bước 2 (AI gợi ý ghép cặp): Nền tím AI `#FAF5FF` → `#FFFFFF`, viền `#EDE9FE`, badge tím `#7C3AED`.
    - Bước 3 (Học & Check-in QR): Nền xanh dương `#F0F9FF` → `#FFFFFF`, viền `#E0F2FE`, badge xanh `#0284C7`.
    - Bước 4 (Tích giờ & Đổi kỹ năng): Nền xanh lá `#F0FDF4` → `#FFFFFF`, viền `#DCFCE7`, badge xanh ngọc `#059669`.
- **4 chỉ số vận hành (`.stat-card`):**
  - Đổ màu nền gradient hiện đại cho từng thẻ số liệu:
    - Thẻ 1 (Học sinh thành viên): Gradient Sky Blue `#EFF6FF` → `#DBEAFE`, số `#1E40AF`.
    - Thẻ 2 (Phiên hoàn thành): Gradient Mint Green `#ECFDF5` → `#D1FAE5`, số `#065F46`.
    - Thẻ 3 (Giờ lưu thông): Gradient Sunset Amber `#FFF7ED` → `#FFEDD5`, số `#C2410C`.
    - Thẻ 4 (Kỹ năng sẵn sàng): Gradient Royal Indigo `#EEF2FF` → `#E0E7FF`, số `#3730A3`.
  - Kích thước số lớn nổi bật (`2.75rem`, `font-weight: 800`), hiệu ứng hover đổ bóng mượt mà.

### 4. Nghiệm thu & Regression Testing:
- Test suite `test_prompt31_ui_wording_color.py` bao gồm 8 test cases chuyên sâu kiểm thử toàn diện từ ngữ, ngoặc kép và CSS phối màu.
- Toàn bộ **30/30 bộ test trong hệ thống (100% PASS)** xác nhận regression pass hoàn hảo.

---

## 🏫 PROMPT 32 — QUẢN LÝ TRƯỜNG HỌC (THÊM / SỬA / ẨN TRƯỜNG HỌC)

Nâng cấp trung tâm quản trị hệ thống cho Tổng Quản trị viên (Super Admin) đáp ứng nhu cầu phát triển mạng lưới trường học tham gia TimeBank EDU:

### 1. Tab "Quản lý Trường học" trong `/admin` (Chỉ Super Admin):
- **Form Thêm Trường Học Mới:**
  - Tên trường học (*) với cơ chế tự động validate không để trống và không trùng lặp (case-insensitive).
  - Tự động sinh `truong_id` kế tiếp (bảo vệ tránh trùng `DEMO_SCHOOL_ID = 99` của Trường Demo).
  - Trạng thái ban đầu đầy đủ 4 tùy chọn: *Chuẩn bị triển khai*, *Đang thí điểm*, *Đang hoạt động*, *Tạm ngưng*.
  - Upload ảnh logo trường học thực tế hoặc gán logo nhận diện chuẩn.
- **Bảng Thống kê & Quản trị Danh sách Trường:**
  - Cột mã trường định dạng chuẩn học đường: `Trường #ID`.
  - Hiển thị logo, tên trường, trạng thái hoạt động và nhãn cảnh báo `Đã ẩn` (nếu trường bị ẩn).
  - Thống kê thời gian thực số lượng tài khoản thuộc từng trường và ngày tạo.
  - Cặp nút điều khiển tinh gọn: Nút **"Sửa"** (mở modal cập nhật tên, logo, trạng thái) và nút **"Ẩn trường" / "Hiện lại"** đặt ngay cạnh nhau trên từng dòng.
  - **Tuyệt đối không có nút xóa cứng:** Bảo vệ 100% tính toàn vẹn dữ liệu, triệt tiêu nguy cơ mồ côi dữ liệu tài khoản, lịch sử học tập hay tín dụng giờ học.

### 2. Cơ chế Ẩn / Hiện Trường Học (`an_truong`):
- **Migration Idempotent:** Thêm cột `an_truong INTEGER DEFAULT 0` tương thích hoàn hảo cả SQLite cục bộ lẫn PostgreSQL production.
- **Ẩn trường (`an_truong = 1`):**
  - Biến mất hoàn toàn khỏi trang chủ (`/`), dropdown đăng ký (`/register`), sàn cộng đồng liên trường (`/community-market`) và các bộ lọc phía người dùng thông thường.
  - Từ chối đăng ký mã mời của trường bị ẩn kèm thông báo rõ ràng cho phụ huynh/học sinh.
- **Hiện lại (`an_truong = 0`):**
  - Lập tức xuất hiện trở lại trên toàn bộ giao diện công khai và đón nhận đăng ký bình thường.
- **Phân quyền Super Admin:**
  - Tổng quản trị viên vẫn quan sát được toàn bộ danh sách trường trong bảng điều khiển và dropdown lọc với nhãn phân biệt rõ nét `(Đã ẩn)`.
- **Bảo vệ Trường Demo (ID 99):**
  - Thiết lập `an_truong = 1` mặc định để ẩn khỏi trang chủ và form đăng ký học sinh mới.
  - Khóa cố định: Chặn mọi thao tác sửa tên, thay logo, ẩn hoặc xóa đối với Trường Demo.
  - Bảo toàn đăng nhập cho 3 tài khoản demo công khai (`demo_quantruong`, `demo_giaovien`, `demo_hocsinh`) phục vụ giám khảo chấm thi.

### 3. Chuẩn hóa từ ngữ toàn site:
- Chuyển đổi toàn bộ tiền tố `Gian hàng #N` sang `Trường #N` ở mọi vị trí hiển thị người dùng.

### 4. Nghiệm thu & Regression Suite:
- Bộ test suite `test_prompt32_school_hide_management.py` (7 test cases chuyên sâu) kiểm thử tự động toàn diện.
- Toàn bộ **31/31 bộ test trong hệ thống (100% PASS)** xác nhận chất lượng hệ thống đạt chuẩn tuyệt đối.

---

## 🌐 PROMPT 16 — ĐA NGÔN NGỮ (VIỆT / ANH / TRUNG / PHÁP / ĐỨC)

Hệ thống được quốc tế hóa (i18n) và địa phương hóa (l10n) toàn diện với **Flask-Babel** nhằm mở rộng quy mô hợp tác quốc tế và nâng cao điểm số sáng tạo tại các hội thi khoa học - giáo dục:

### 1. Kiến trúc Đa ngôn ngữ (Flask-Babel & Session):
- **5 ngôn ngữ hỗ trợ chính thức:**
  - 🇻🇳 **Tiếng Việt (`vi`)**: Ngôn ngữ mặc định của nền tảng học đường.
  - 🇬🇧 **English (`en`)**: Tiếng Anh chuẩn mực, tự nhiên.
  - 🇨🇳 **中文 (`zh`)**: Tiếng Trung Quốc giản thể (sư phạm, chuẩn giáo dục).
  - 🇫🇷 **Français (`fr`)**: Tiếng Pháp thanh lịch, chuẩn mực.
  - 🇩🇪 **Deutsch (`de`)**: Tiếng Đức chính xác, chuẩn xác thuật ngữ sư phạm.
- **Nguyên tắc chọn ngôn ngữ (User-Driven, No Auto-IP):**
  - **KHÔNG tự động nhận diện** qua IP hay `Accept-Language` của trình duyệt.
  - Người dùng chủ động lựa chọn ngôn ngữ qua dropdown chuyển đổi trên thanh header điều hướng.
  - Lưu lựa chọn vào `session['lang']`; tải lại trang, đổi thiết bị hay điều hướng vẫn duy trì ngôn ngữ đã chọn.
  - Cung cấp route `/set-language/<lang_code>` với cơ chế kiểm tra mã ngôn ngữ hợp lệ và redirect an toàn (`request.referrer`).

### 2. Phân định ranh giới bản dịch (UI Translation vs. User-Generated Content):
- **Dịch CHỈ giao diện:**
  - Toàn bộ thanh điều hướng (navbar), các nút bấm (buttons), tiêu đề (headings), nhãn trường (form labels), thông báo hệ thống (flash messages), lỗi xác thực (validation errors) và chân trang (footer).
  - Sử dụng chuẩn `gettext` với hàm `_()` trong Python code và `{{ _('...') }}` trong Jinja2 templates.
- **KHÔNG dịch nội dung do người dùng / nhà trường tạo:**
  - Tên kỹ năng của gia sư, mô tả chi tiết, bài viết diễn đàn, bình luận, bài tập, dàn ý bài dạy, tên trường học và tài liệu học tập được giữ nguyên bản gốc để bảo toàn tính xác thực của dữ liệu trao đổi tri thức.

### 3. Quy trình biên dịch & Biên tập bản dịch:
- **Trích xuất chuỗi:** Cấu hình `babel.cfg` và sinh tệp mẫu `messages.pot` với hơn 200 thông điệp giao diện.
- **5 tệp bản dịch chuyên nghiệp (`.po`):**
  - `translations/vi/LC_MESSAGES/messages.po`
  - `translations/en/LC_MESSAGES/messages.po`
  - `translations/zh/LC_MESSAGES/messages.po`
  - `translations/fr/LC_MESSAGES/messages.po`
  - `translations/de/LC_MESSAGES/messages.po`
- **Biên dịch mã nhị phân (`.mo`):** Toàn bộ 5 tệp nhị phân `.mo` được biên dịch sẵn sàng bằng `pybabel compile -d translations` và được commit đầy đủ lên GitHub để triển khai tức thì trên mọi môi trường máy chủ.

### 4. Kiểm thử nghiệm thu & Regression Suite:
- **Test suite độc lập `test_prompt16_multilingual.py`:** 8 test cases chuyên sâu bao gồm:
  1. Ngôn ngữ mặc định `vi`.
  2. Nút chuyển đổi `/set-language/<lang_code>` và lưu `session['lang']`.
  3. Giao diện tiếng Anh (`en`) chính xác.
  4. Giao diện tiếng Trung (`zh`) chính xác.
  5. Giao diện tiếng Pháp (`fr`) chính xác.
  6. Giao diện tiếng Đức (`de`) chính xác.
  7. Nội dung người dùng tạo (user content) được giữ nguyên, không bị can thiệp.
  8. Xử lý mã ngôn ngữ không hợp lệ an toàn, tự động fallback về tiếng Việt.
- **Toàn bộ 33/33 bộ test regression (100% PASS)** xác nhận tương thích hoàn hảo với mọi tính năng trước đó.

---

## 🤝 QUẢN LÝ CHƯƠNG TRÌNH GIỜ CÔNG ÍCH HỌC ĐƯỜNG (THÊM / SỬA / XÓA)

Hệ thống nâng cấp toàn diện phân hệ hoạt động phục vụ cộng đồng, chuyển đổi từ danh mục định sẵn trong mã nguồn sang cơ chế quản trị động hoàn toàn trong CSDL, cho phép nhà trường tự chủ tổ chức các chiến dịch thiện nguyện và giờ công ích học đường:

### 1. Bảng Điều Khiển Quản Trị (`/admin` & Tab "Chương trình Cộng đồng"):
- **Giao diện Tab chuyên biệt (`#tab-community-tasks`):**
  - Tích hợp liền mạch vào hệ thống tab quản trị viện với icon `bi-heart-fill` nổi bật.
  - Hỗ trợ cả **Quản trị trường (`school_admin`)** và **Tổng quản trị (`super_admin`)**.
- **Form thêm mới chương trình:**
  - Nhập liệu đầy đủ: Tên chương trình (*), Mô tả chi tiết, Số giờ tín dụng thưởng (*), Ngày bắt đầu, Ngày kết thúc, Địa điểm thực hiện, Số lượng học sinh tối đa.
  - Lựa chọn trạng thái: *Sắp diễn ra (`sap_dien_ra`)*, *Đang diễn ra (`dang_dien_ra`)*, *Đã kết thúc (`da_ket_thuc`)*.
  - Phân quyền gán trường: Super Admin có quyền chọn phân bổ cho bất kỳ trường học nào trong hệ thống; Quản trị trường tự động gán cho trường của mình.
- **Bảng thống kê & Quản lý danh sách:**
  - Liệt kê trực quan: Tên chương trình, mô tả tóm tắt, số giờ thưởng, thời gian diễn ra, trạng thái (badge màu tương ứng), trường áp dụng và số lượng học sinh đã đăng ký tham gia theo thời gian thực.
  - Nút **"Sửa"**: Mở Modal chỉnh sửa tức thì toàn bộ thông tin chương trình và cập nhật trực tiếp vào CSDL.
  - Nút **"Xóa" an toàn:**
    + **Chương trình chưa có ai đăng ký:** Thực hiện xóa vĩnh viễn (hard delete) khỏi CSDL.
    + **Chương trình đã có học sinh đăng ký:** Hệ thống **chặn tuyệt đối việc xóa cứng**, tự động chuyển trạng thái sang **"Đã kết thúc"** kèm thông báo bảo vệ tính toàn vẹn dữ liệu điểm tích lũy và lịch sử tham gia của học sinh.

### 2. Cách Ly Đa Trường (Multi-tenant Data Isolation):
- Quản trị viên của trường A chỉ nhìn thấy, chỉnh sửa và quản lý các chương trình thuộc phạm vi trường A.
- Ngăn chặn mọi hành vi can thiệp trái phép (chặn đọc, chặn sửa, chặn xóa) giữa các trường học khác nhau.
- Super Admin có góc nhìn toàn cục, giám sát và quản lý chương trình công ích trên toàn bộ mạng lưới trường học.

### 3. Tự Động Hiển Thị Trang "Vì Cộng Đồng" (`/community`):
- Toàn bộ chương trình mới tạo hoặc cập nhật lập tức hiển thị động trên trang `/community` của học sinh.
- Hiển thị badge trạng thái chuẩn hóa (*Sắp diễn ra*, *Đang diễn ra*), mốc thời gian bắt đầu – kết thúc và số giờ tín dụng học đường nhận được.
- Học sinh có thể đăng ký tham gia trực tiếp chỉ với 1 click.

### 4. AI Gợi Ý Nhiệm Vụ Thông Minh (`ai_recommend_tasks`):
- Trợ lý AI tự động truy vấn động danh sách nhiệm vụ từ bảng `community_tasks` trong CSDL thay cho danh sách fix cứng.
- Phân tích sở thích, năng khiếu và kỹ năng của từng học sinh để gợi ý nhiệm vụ công ích phù hợp nhất (trồng cây xanh, bảo vệ môi trường, hỗ trợ thư viện, gia sư thiện nguyện, thăm mái ấm tình thương...).

### 5. Nghiệm Thu & Kiểm Thử Tự Động:
- **Test suite `test_prompt_community_management.py` (8/8 test cases PASS):**
  1. Kiểm tra sự hiện diện của Tab Chương trình Cộng đồng cho Super Admin và School Admin.
  2. Tạo chương trình mới và kiểm tra hiển thị thời gian thực trên trang `/community`.
  3. Sửa thông tin chương trình và xác thực cập nhật tức thì trong CSDL và giao diện.
  4. Xóa cứng thành công khi chương trình chưa có ai đăng ký.
  5. Chặn xóa cứng và tự động chuyển 'đã kết thúc' khi chương trình đã có học sinh đăng ký.
  6. Cách ly đa trường tuyệt đối giữa Quản trị trường A và Trường B.
  7. AI gợi ý nhiệm vụ động từ CSDL theo kỹ năng người dùng.
  8. Phân quyền Super Admin quản trị và phân bổ chương trình cho mọi trường.
- **Toàn bộ 33/33 bộ kiểm thử hồi quy (100% PASS):** Hệ thống ổn định tuyệt đối, sẵn sàng triển khai thực tế.

---

## 💎 BỔ SUNG QUAN TRỌNG — CHUẨN HÓA TỪ NGỮ SƯ PHẠM & KIỂM THỬ RESPONSIVE

Nhằm nâng cao tính sư phạm, thuần khiết và thân thiện trong môi trường giáo dục học đường theo định hướng của Ban Giám hiệu và các trường đối tác, hệ thống đã thực hiện đợt chuẩn hóa từ ngữ hiển thị trên toàn bộ giao diện:

### 1. Nguyên Tắc Bất Di Bất Dịch:
- **CHỈ thay đổi chuỗi text hiển thị người dùng nhìn thấy** (templates HTML, flash messages, tiêu đề trang, nhãn nút bấm).
- **TUYỆT ĐỐI KHÔNG ĐỔI CẤU TRÚC KỸ THUẬT:**
  - Giữ nguyên toàn bộ Routes/URLs hệ thống: `/skills`, `/community-market`, `/community`, v.v. (đảm bảo 100% không gãy liên kết hay bookmark cũ).
  - Giữ nguyên tên biến, tên hàm, controller logic và cột CSDL.
  - Giữ nguyên các giá trị logic lưu trong CSDL (`type='community_market'`, `hien_thi_cong_dong`, v.v.).

### 2. Danh Mục Từ Ngữ Chuẩn Hóa Sư Phạm:
| Thuật ngữ cũ | Thuật ngữ chuẩn hóa mới | Vị trí áp dụng |
| :--- | :--- | :--- |
| **Chợ kỹ năng** | **Kho kỹ năng học đường** | Header navbar, footer, tiêu đề `/skills`, link điều hướng từ trang ví, trang lịch học, nội quy |
| **Sàn cộng đồng** / **Sàn chung** | **Cộng đồng liên trường** | Header navbar, tiêu đề `/community-market`, thông báo cổng kiểm chuẩn, tab admin `/admin` |
| **Chợ nội trường** | **Kho nội trường** | Nút chuyển đổi nhanh tại `/community-market` và `/community-market-gate` |
| **Duyệt Sàn Chung** | **Duyệt Liên Trường** | Tab `#tab-community` và tiêu đề danh sách duyệt trong Bảng điều khiển Quản trị `/admin` |
| **Đăng lên sàn chung** | **Đăng lên cộng đồng liên trường** | Nút hành động và badge trạng thái trên trang Hồ sơ cá nhân (`/profile`) |

### 3. Đồng Bộ Đa Ngôn Ngữ (Flask-Babel i18n):
- Bổ sung chuỗi khóa `msgid "Kho kỹ năng học đường"` và `msgid "Cộng đồng liên trường"` vào toàn bộ 5 tệp ngôn ngữ:
  - 🇻🇳 Tiếng Việt (`vi`): *Kho kỹ năng học đường* | *Cộng đồng liên trường*
  - 🇬🇧 English (`en`): *School Skills Repository* | *Inter-School Community*
  - 🇨🇳 中文 (`zh`): *校园技能库* | *校际互助社区*
  - 🇫🇷 Français (`fr`): *Répertoire de compétences scolaires* | *Communauté interscolaire*
  - 🇩🇪 Deutsch (`de`): *Schulkompetenz-Repository* | *Schulübergreifende Gemeinschaft*
- Toàn bộ 5 tệp nhị phân `.mo` đã được tái biên dịch (`pybabel compile -d translations`).

### 4. Kiểm Thử Giao Diện & Phối Màu Thanh Navbar:
- **Đổ Màu Nền Thanh Menu Ngang:** Áp dụng dải màu cam kem ấm nhẹ (`#FFFDFB` $\rightarrow$ `#FFF8F1`, viền `#FED7AA`), đổ bóng nhẹ `rgba(242, 101, 34, 0.08)`.
- **Tương Phản Menu Pills:** Các nút menu bên trong có nền trắng bo tròn (`#FFFFFF`, viền `#FED7AA`, icon cam `#F26522`), hover cam ấm `#FFF7ED`, active gradient cam-vàng, phân tách cực kỳ rõ ràng và thẩm mỹ trên nền thanh navbar.
- **Cố Định Header 1 Hàng Duy Nhất (Single-Row Navbar):** Khóa thuộc tính `flex-wrap: nowrap !important` trên toàn bộ container, collapse và navbar-nav trên Desktop/Laptop; tối ưu đệm padding của các nút menu và khống chế độ rộng hiển thị tên Quản trị viên (`max-width: 90px-110px`), triệt tiêu hoàn toàn hiện tượng tràn sang hàng 2, đảm bảo 100% các thành phần nằm gọn trên một hàng duy nhất đẹp mắt và chuyên nghiệp.
- **Cập Nhật Chữ Chạy Ngang (Marquee/Ticker Banner):** Tôn vinh Hệ sinh thái Giáo dục số TIME BANK EDU, khẳng định Tác giả phát triển & Thiết kế hệ thống: Cô giáo Nguyễn Thị Huyền (Giáo viên Tin học — Trường Quốc tế Song ngữ UK Academy) cùng Bản quyền toàn vẹn về mô hình sư phạm và giải pháp kiến trúc công nghệ School Time Bank; tích hợp trọn bộ icon sư phạm chuyên nghiệp (✨, 🎓, ✦, 👩‍🏫, 🛡️), đồng bộ đa ngôn ngữ 5 thứ tiếng và cơ chế tạm dừng mượt mà khi hover.
- **Tinh Gọn Khung Tài Khoản Demo Tại Trang Đăng Nhập:** Loại bỏ toàn bộ các dòng chữ rườm rà ("Tài khoản demo cho giám khảo", "Mật khẩu: demo123", "Dành riêng cho Ban Giám Khảo trải nghiệm..."), thay thế bằng dòng chữ tinh gọn và thân thiện: *"Tài khoản demo đăng nhập nhanh để trải nghiệm."*, giữ nguyên tính năng điền nhanh 1-click cho các vai trò và đồng bộ đa ngôn ngữ 5 thứ tiếng.
- **Kiểm thử Desktop:** Mở menu "Hoạt động", các mục "Kho kỹ năng học đường" và "Cộng đồng liên trường" hiển thị sắc nét, click điều hướng chính xác 100% tới `/skills` và `/community-market`.
- **Kiểm thử Mobile (Viewport 375px x 750px):**
  - Mở thanh điều hướng Hamburger Drawer và menu con "Hoạt động".
  - Chữ hiển thị cân đối, vừa vặn, không bị tràn dòng hay vỡ khung responsive.
  - Kiểm thử click từng link điều hướng: Đảm bảo phản hồi mượt mà, **tuyệt đối không có link nào bị gãy**.
- **Kiểm Thử Hồi Quy (Regression Testing):**
  - Chạy toàn bộ hệ thống test suites: `python -X utf8 run_all_tests.py`
  - Kết quả: **34/34 Test Suites ĐẠT 100% PASS (282+ tests passed)**.

---

## 📥 TÍNH NĂNG NHẬP DANH SÁCH HỌC SINH / GIÁO VIÊN HÀNG LOẠT (EXCEL/CSV)

Phát triển tính năng quản trị quy mô lớn phục vụ các trường gửi danh sách hàng trăm người (quản trị trường, giáo viên, học sinh) để tạo tài khoản đồng loạt an toàn, tự động và dùng lâu dài ngay trong `/admin` thay vì nhập tay.

### 1. Kiến trúc Kỹ thuật & Nguyên Tắc Bảo Mật:
- **Tuyệt đối không dùng chung mật khẩu mặc định:** Mỗi tài khoản được tự sinh mật khẩu ngẫu nhiên RIÊNG BIỆT (8 ký tự kết hợp chữ hoa, chữ thường, số, loại bỏ ký tự dễ nhầm lẫn như l, 1, O, 0).
- **Mã hóa một chiều:** Mật khẩu được băm an toàn bằng `werkzeug.security.generate_password_hash` trước khi lưu vào CSDL.
- **Bảo mật dữ liệu học sinh:** Không lưu file danh sách chứa thông tin học sinh vào repository; mọi luồng xử lý Excel/CSV đều diễn ra in-memory thông qua thư viện `openpyxl` và `io.BytesIO`.
- **Tự sinh Mã định danh (Tên đăng nhập):** Tự động sinh từ họ tên (ví dụ `Nguyễn Văn An` $\rightarrow$ `an.nv`), kiểm tra trùng lặp tự động với số thứ tự (`an.nv1`, `an.nv2`), đảm bảo duy nhất 100%.
- **Cô lập Đa trường (Multi-Tenant Isolation):** 
  - `school_admin`: Chỉ có quyền nhập danh sách cho trường của mình (`session['truong_id']`), tuyệt đối bị chặn nếu cố tình truyền `truong_id` trường khác.
  - `super_admin`: Được phép chọn trường học cần nhập qua danh sách chọn trường.
- **Kích hoạt & Vốn giờ ban đầu:** Tài khoản tạo ở trạng thái `hoat_dong` ngay (đăng nhập được luôn, không cần chờ duyệt); học sinh được tự động cấp `+2.0` giờ ban đầu đúng triết lý sư phạm TimeBank.
- **Cơ chế Bỏ qua dòng lỗi (Fault Tolerance):** Validate từng dòng độc lập; dòng lỗi bị bỏ qua và ghi nhận lý do cụ thể, tuyệt đối không chặn các dòng đúng.
- **Chống trùng lặp (Idempotency):** Chạy lại cùng file cũ sẽ phát hiện tài khoản đã tồn tại và bỏ qua, không tạo trùng lặp.

### 2. Giao Diện & Quy Trình Trải Nghiệm (/admin):
- **Tab Quản lý Tài khoản (`#tab-users`):** Nút *"Nhập danh sách (Excel/CSV)"* bo góc pill nổi bật.
- **Modal Nhập Dữ Liệu (`#modalImportUsers`):**
  - Nút *"Tải file Excel mẫu"* (`GET /admin/import-users/template`): Tải file mẫu 6 cột (`họ_tên`, `vai_trò`, `lớp`, `email`, `số_điện_thoại`, `ghi_chú`) có sẵn 3 dòng mẫu trực quan.
  - Form chọn file upload hỗ trợ `.xlsx`, `.xls`, `.csv` (UTF-8).
  - Khung hướng dẫn bảo mật và quy chuẩn tự động hóa.
- **Bảng Tổng Kết & Xuất File Kết Quả:**
  - Sau khi nạp, hiển thị bảng tổng kết: số dòng thành công, số dòng lỗi, bảng chi tiết từng dòng lỗi kèm số dòng và lý do.
  - Nút *"Tải file Excel kết quả (Tên đăng nhập & Mật khẩu)"* (`GET /admin/import-users/download-result`): Xuất file Excel định dạng chuyên nghiệp để nhà trường in ấn hoặc bàn giao thông tin đăng nhập riêng cho từng người.

### 3. Nghiệm Thu & Kiểm Thử Tự Động:
- Đã xây dựng bộ kiểm thử chuyên biệt `test_prompt_import_users.py` với 7 test cases kiểm tra 100% các tiêu chí:
  1. `test_01_download_template`: Tải file Excel mẫu đúng chuẩn 6 cột quy định.
  2. `test_02_import_10_rows_with_2_errors`: Nạp 10 dòng (2 lỗi cố ý) $\rightarrow$ 8 thành công, 2 báo lỗi đúng lý do, 8 dòng đúng tạo bình thường.
  3. `test_03_passwords_unique_and_immediate_login`: 100% mật khẩu ngẫu nhiên riêng biệt, đăng nhập được ngay lập tức với mật khẩu ban đầu.
  4. `test_04_download_result_excel`: Tải file kết quả có đủ họ tên, tên đăng nhập, mật khẩu ban đầu.
  5. `test_05_school_admin_cross_tenant_blocked`: Quản trị trường 1 bị chặn khi nhập cho trường 2 (RBAC bảo vệ dữ liệu).
  6. `test_06_idempotency_no_duplicate_accounts`: Chạy lại file cũ không tạo tài khoản trùng.
  7. `test_07_import_csv_format`: Hỗ trợ file CSV định dạng UTF-8.
- **Kết quả Regression:** **34/34 Test Suites ĐẠT 100% PASS**.

---

## 🎟️ TÍNH NĂNG XUẤT EXCEL & SAO CHÉP TOÀN BỘ MÃ MỜI TRƯỜNG HỌC (/admin)

Sau khi sinh mã mời hàng loạt (dạng chuẩn `TBEDU-XXXX-XXXX`), quản trị viên cần chia sẻ mã cho giáo viên chủ nhiệm, học sinh hoặc gửi nhanh qua Zalo/Email. Hệ thống đã bổ sung bộ công cụ thao tác nhanh ngay trên Bảng mã mời đã phát hành:

### 1. Nút "Xuất Excel" (`GET /admin/invite-codes/export-excel`):
- **Vị trí:** Đặt trang trọng trên thanh tiêu đề của thẻ *Danh Sách Mã Mời Đã Phát Hành* (Tab Quản lý mã mời `#tab-invite`).
- **Định dạng:** File `.xlsx` chuẩn với nhận diện thương hiệu Royal Blue, căn lề và định dạng ô chuyên nghiệp.
- **Dữ liệu xuất chuẩn hóa 7 cột:**
  1. `STT`: Số thứ tự tăng dần.
  2. `Mã mời`: Định dạng chuẩn in đậm (ví dụ: `TBEDU-ABCD-1234`).
  3. `Loại mã`: Phân loại rõ ràng (*Mã lớp* hoặc *Cá nhân*).
  4. `Trường`: Tên trường học được cấp phát mã.
  5. `Số lượt còn lại`: Số lượt sử dụng khả dụng còn lại.
  6. `Ngày tạo`: Thời điểm phát hành mã định dạng `DD/MM/YYYY HH:MM`.
  7. `Trạng thái`: Trạng thái trực quan (*Khả dụng* - màu xanh hoặc *Đã hết lượt* - màu đỏ).
- **Phân quyền & Cách ly Đa trường (Multi-Tenant Isolation):**
  - Quản trị viên trường (`school_admin`): Chỉ xuất được danh sách mã thuộc trường của mình.
  - Quản trị viên cấp cao (`super_admin`): Hỗ trợ xuất toàn bộ hệ thống hoặc lọc linh hoạt theo từng trường.

### 2. Nút "Sao chép tất cả" (1-Click Copy to Clipboard):
- **Công dụng:** 1 click sao chép toàn bộ danh sách mã mời (mỗi mã 1 dòng) vào clipboard hệ thống.
- **Tiện ích:** Dán nhanh trực tiếp vào tin nhắn Zalo, nhóm lớp hoặc email thông báo mà không cần bôi đen thủ công từng mã.
- **Trải nghiệm tương tác (UX):** Nút tự động chuyển trạng thái màu xanh *"Đã sao chép (X mã)"* trong 2.5 giây; tích hợp cơ chế fallback an toàn cho mọi trình duyệt.
- **Sao chép nhanh từng mã:** Bổ sung icon sao chép nhanh 1 chạm bên cạnh từng mã mời trong bảng dữ liệu.

### 3. Nghiệm Thu & Kiểm Thử Tự Động:
- Bộ kiểm thử tự động `test_prompt_export_invite_codes.py` (5/5 tests PASS):
  1. `test_01_ui_has_export_and_copy_buttons`: Kiểm tra sự hiện diện của 2 nút `#btnExportInviteCodesExcel` và `#btnCopyAllInviteCodes`.
  2. `test_02_export_excel_endpoint_returns_valid_xlsx`: Kiểm tra tính toàn vẹn của file Excel tải về (6 cột nghiệp vụ + STT, tính đúng đắn của số lượt còn lại và trạng thái).
  3. `test_03_copy_all_logic_and_format`: Kiểm tra định dạng sao chép clipboard mỗi mã 1 dòng.
  4. `test_04_tenant_isolation_school_admin`: Bảo vệ phân quyền dữ liệu giữa các trường.
  5. `test_05_unauthorized_access_blocked`: Chặn người dùng chưa đăng nhập.
- **Kết quả Regression:** **36/36 Test Suites ĐẠT 100% PASS**.

---

## 🤖 BỔ SUNG TÍNH NĂNG THÔNG MINH CHO HỌC SINH (5 VIỆC)

Hệ thống được nâng cấp bộ tính năng thông minh hỗ trợ ghép cặp học sinh cùng tiến, quản lý lịch rảnh cá nhân, chuông thông báo thời gian thực và đánh giá tương hỗ sư phạm:

### 1. VIỆC 1 — "Môn cần hỗ trợ" (Trang hồ sơ học sinh `/profile`):
- **Giao diện & Cấu hình:** Thêm mục *"Tôi cần được giúp đỡ môn:"* cho phép học sinh chọn nhiều môn học (Toán, Lý, Hóa, Sinh, Văn, Tiếng Anh, Tin học, v.v.), chỉ định mức độ kiến thức (*Cơ bản (Củng cố kiến thức gốc)* hoặc *Nâng cao (Luyện thi & Chuyên sâu)*) kèm ghi chú chi tiết phần kiến thức đang gặp khó khăn.
- **Lưu trữ CSDL:** Dữ liệu lưu dưới định dạng JSON có cấu trúc trong cột `users.mon_can_ho_tro`, tự động hiển thị dưới dạng các huy hiệu trực quan trên thẻ hồ sơ cá nhân và làm dữ liệu đầu vào cốt lõi cho thuật toán ghép cặp AI.

### 2. VIỆC 2 — "Khung giờ rảnh theo tuần" (Trang hồ sơ `/profile`):
- **Lịch chọn linh hoạt:** Bảng chọn lịch tuần trực quan từ Thứ 2 đến Chủ Nhật, mỗi ngày lựa chọn được nhiều ca (Sáng: 8h-11h30, Chiều: 14h-17h30, Tối: 19h-21h30) kèm ô ghi chú linh hoạt.
- **Lưu trữ & Tương thích:** Lưu vào cột `users.gio_ranh`, tương thích với các thuật toán ghép cặp cũ và hỗ trợ hàm `find_common_time_slots(user_ranh, tutor_ranh)` để tự động tính toán và hiển thị "Khung giờ chung" lý tưởng giữa đôi bạn học.

### 3. VIỆC 3 — Nút "AI gợi ý bạn học" (Trang Kho Kỹ năng & Hồ sơ cá nhân):
- **Giao diện nổi bật:** Nút bấm màu vàng cam với hiệu ứng sao AI (`#btnAiSuggestBuddies`) đặt tại thanh tiêu đề Kho kỹ năng học đường (`/skills`) và trên trang hồ sơ cá nhân (`/profile`).
- **Phân tích AI:** Gọi API `/api/skills/smart-suggestions`, đối soát đa chiều (Môn cần học + Giờ rảnh + Kỹ năng gia sư đang dạy + Điểm đánh giá sao uy tín + Trường học) $\rightarrow$ Trả về 3-5 bạn học lý tưởng nhất.
- **Lý do đề xuất & Đặt lịch:** Mỗi gợi ý đi kèm hộp giải thích lý do do AI đề xuất rõ ràng (ví dụ: *"Bạn Nguyễn Văn A dạy tốt môn Toán (5.0★) và trùng lịch rảnh vào Thứ 2 (Tối) với bạn"*) và nút **"Đặt lịch ngay"** dẫn trực tiếp tới trang đặt lịch.

### 4. VIỆC 4 — Đánh giá tương hỗ sau buổi học (1-5 sao + nhận xét):
- **Form đánh giá sau hoàn thành:** Khi buổi học chuyển sang trạng thái `hoan_thanh`, form đánh giá 1-5 sao kèm nhận xét ngắn xuất hiện nổi bật tại trang chi tiết buổi học (`/sessions/<id>`) và có nút truy cập nhanh từ trang *Lịch của tôi* (`/my-schedule`).
- **Bảo đảm tính khách quan:** Mỗi thành viên chỉ được gửi đánh giá đúng 1 lần duy nhất cho mỗi phiên (chống spam).
- **Hiển thị điểm uy tín:** Điểm trung bình sao (`sao_tb`) và tổng lượt đánh giá được cập nhật tức thì trên Hồ sơ cá nhân và Bảng Vinh danh Gia sư Học đường Tích cực trên trang chủ.

### 5. VIỆC 5 — Chuông thông báo & Xác nhận buổi học thời gian thực:
- **Chuông thông báo Navbar:** Biểu tượng chuông với huy hiệu đỏ đếm số lượng chưa đọc (`#notificationDropdown`), xem nhanh danh sách thông báo và nút *"Đánh dấu đã đọc"*.
- **Thông báo khi có người đăng ký:** Khi học sinh đặt lịch học kỹ năng, hệ thống tự động ghi bản ghi vào bảng `notifications` cho người dạy, đồng thời gọi hàm `send_booking_notification_email` gửi email an toàn (tích hợp SMTP dự phòng, không crash).
- **Xác nhận lịch học:** Người dạy có thể bấm **"Xác nhận lịch học"** trực tiếp từ thông báo hoặc trên trang chi tiết buổi học. Khi xác nhận, hệ thống gửi thông báo phản hồi ngay cho người học.

### 6. Nghiệm Thu & Kiểm Thử Tự Động:
- Bộ kiểm thử tự động `test_prompt_smart_features.py` (6/6 tests PASS):
  1. `test_01_update_study_needs_and_weekly_schedule`: Cập nhật môn cần hỗ trợ & giờ rảnh T2-CN, lưu CSDL và hiển thị trên hồ sơ.
  2. `test_02_find_common_time_slots`: Thuật toán tìm khung giờ chung chính xác theo từng ngày và ca học.
  3. `test_03_api_smart_suggestions`: API `/api/skills/smart-suggestions` trả về 3-5 gợi ý kèm lý do và nút đặt lịch.
  4. `test_04_session_rating_and_tutor_average`: Đánh giá 1-5 sao, chống lặp lại, cập nhật điểm trung bình ở hồ sơ và vinh danh.
  5. `test_05_booking_notification_email_and_confirmation`: Chuông thông báo đặt lịch cho người dạy, xác nhận buổi học gửi thông báo cho người học.
  6. `test_06_send_booking_email_safety`: Hàm gửi email chạy an toàn không crash khi thiếu SMTP.
- **Kết quả Regression:** **37/37 Test Suites ĐẠT 100% PASS**.

---

## CHUẨN HÓA MENU DROPDOWN THEO ĐÚNG VAI TRÒ (ROLE-BASED NAVIGATION)

### Nguyên Tắc Cốt Lõi:
> "Mỗi vai trò CHỈ thấy những mục mình thực sự dùng."
- Học sinh là chủ thể trao đổi tín chỉ học tập (tích lũy & giao dịch giờ).
- Giáo viên & Quản trị viên đóng vai trò sư phạm và vận hành hệ thống, không tham gia lưu thông số dư giờ học sinh $\rightarrow$ Ẩn hoàn toàn "Lịch của tôi", "Ví của tôi" và badge số dư giờ trên thanh điều hướng.

---

### Phân Định Chi Tiết 4 Vai Trò:

#### 1. HỌC SINH (`hoc_sinh` — người học + người dạy):
- **User Pill Badge:** Hiển thị số dư giờ `user-balance-badge` (ví dụ: `3.0h`).
- **Mục Dropdown Giữ lại (7 mục):**
  1. `Lịch của tôi` (`/my-schedule`)
  2. `Ví của tôi` (`/wallet`) kèm số dư giờ
  3. `Hồ sơ & Cài đặt` (`/profile`)
  4. `Đăng kỹ năng mới` (`/skills/new`)
  5. `Hoạt động Vì cộng đồng` (`/community-tasks`)
  6. `AI gợi ý bạn học` (Kích hoạt trực tiếp modal AI thông minh)
  7. `Đăng xuất` (`/logout`)
- **Mục BỎ:** Không hiển thị bất kỳ mục quản trị, duyệt kỹ năng hay giám sát phòng học ảo.

#### 2. GIÁO VIÊN (`giao_vien`):
- **User Pill Badge:** Hiển thị huy hiệu `Giáo viên` (nền xanh dương). Ẩn badge số dư giờ.
- **Mục Dropdown Giữ lại (7 mục):**
  1. `Hồ sơ & Cài đặt` (`/profile`)
  2. `Đăng kỹ năng mới` (`/skills/new`)
  3. `Duyệt kỹ năng học sinh` (`/skills/approve`)
  4. `Giám sát phòng học ảo` (`/virtual-rooms`)
  5. `Quản lý Bảng tin` (`/blog/manage`)
  6. `Hoạt động Vì cộng đồng` (`/community-tasks`)
  7. `Đăng xuất` (`/logout`)
- **Mục BỎ:** BỎ "Lịch của tôi", BỎ "Ví của tôi", BỎ "AI gợi ý bạn học".

#### 3. QUẢN TRỊ TRƯỜNG (`school_admin`):
- **User Pill Badge:** Hiển thị huy hiệu `Quản trị trường` (nền vàng cam). Ẩn badge số dư giờ.
- **Mục Dropdown Giữ lại (8 mục):**
  1. `Hồ sơ & Cài đặt` (`/profile`)
  2. `Quản lý Tài khoản` (`/admin#tab-users`)
  3. `Quản lý Mã mời` (`/admin#tab-invite`)
  4. `Duyệt kỹ năng` (`/skills/approve`)
  5. `Quản lý Bảng tin` (`/blog/manage`)
  6. `Chương trình Cộng đồng` (`/admin#tab-community-tasks`)
  7. `Báo cáo trường` (`/admin#tab-overview`)
  8. `Đăng xuất` (`/logout`)
- **Mục BỎ:** BỎ "Lịch của tôi", BỎ "Ví của tôi", BỎ "Đăng kỹ năng mới".

#### 4. TỔNG QUẢN TRỊ (`super_admin`):
- **User Pill Badge:** Hiển thị huy hiệu `Tổng quản trị` (nền đỏ quyền lực). Ẩn badge số dư giờ.
- **Mục Dropdown Giữ lại (9 mục):**
  1. `Hồ sơ & Cài đặt` (`/profile`)
  2. `Quản lý Tài khoản` (`/admin/accounts`)
  3. `Quản lý Mã mời` (`/admin#tab-invite`)
  4. `Duyệt kỹ năng` (`/skills/approve`)
  5. `Quản lý Bảng tin` (`/blog/manage`)
  6. `Chương trình Cộng đồng` (`/admin#tab-community-tasks`)
  7. `Quản lý Trường học` (`/admin#tab-schools`)
  8. `Báo cáo toàn hệ thống` (`/admin#tab-overview`)
  9. `Đăng xuất` (`/logout`)
- **Mục BỎ:** BỎ "Lịch của tôi", BỎ "Ví của tôi", BỎ "Đăng kỹ năng mới".

---

### Nghiệm Thu & Kiểm Thử Tự Động:
- **Bộ kiểm thử tự động:** `test_prompt_role_menus.py` (4/4 tests PASS):
  1. `test_01_student_menu`: Kiểm thử người dùng học sinh `demo_hocsinh`.
  2. `test_02_teacher_menu`: Kiểm thử người dùng giáo viên `demo_giaovien`.
  3. `test_03_school_admin_menu`: Kiểm thử quản trị trường `demo_quantruong`.
  4. `test_04_super_admin_menu`: Kiểm thử tổng quản trị `super_admin`.
- **Kiểm thử giao diện trực quan:** Đã xác minh thực tế trên desktop (1280x800) và mobile (390x844 responsive).
- **Kết quả Regression:** **38/38 Test Suites ĐẠT 100% PASS**.

---

## 23. HOTFIX TỔNG HỢP: IMPORT HÀNG LOẠT (EXCEL/CSV) & HIỂN THỊ TÊN TRƯỜNG

### 1. Sửa Lỗi Sập Trang 500 & Kiến Trúc Chịu Tải Cao (File 1000+ dòng):
- **Thuật toán băm mật khẩu:** Chuyển đổi sang `pbkdf2:sha256:600000` (Werkzeug tiêu chuẩn) thay vì scrypt/argon2 nhằm tối ưu hóa bộ nhớ RAM, chống tràn RAM/SIGKILL trên môi trường Render Free 512MB.
- **Xử lý theo từng Batch & Thu gom rác:** Xử lý chia khối 30-50 tài khoản/batch, commit database nguyên tử và gọi `gc.collect()` giải phóng RAM ngay sau mỗi batch.
- **Quy trình 2 giai đoạn bất đồng bộ (Async Worker Thread):**
  - **Giai đoạn 1 (Validate nhanh đồng bộ <10s):** Kiểm tra cấu trúc file (`.xlsx`, `.xls`, `.csv` UTF-8), giới hạn tối đa 2.000 dòng và dung lượng <= 10MB. Kiểm tra tính hợp lệ của từng dòng (họ tên, vai trò quantruong/giaovien/hocsinh, lớp, email, số điện thoại, trùng lặp). Hiển thị bảng tóm tắt: **X dòng hợp lệ, Y dòng lỗi / bỏ qua**.
  - **Giai đoạn 2 (Tạo tài khoản nền):** Người dùng bấm "Xác nhận tạo X tài khoản", hệ thống khởi tạo worker thread chạy ngầm, tạo tài khoản độc lập, sinh tên đăng nhập chuẩn hóa `[MÃ TRƯỜNG]-<lớp>-<tên>-<STT>` (VD: `UKA-4.1-An-01`), mật khẩu ngẫu nhiên riêng 8 ký tự, tự động kích hoạt tài khoản `hoat_dong` và cộng +2.0 giờ khởi tạo cho học sinh.
  - **Thanh tiến trình Realtime:** Endpoint `GET /admin/import-users/progress` polling mỗi 2 giây trả về tiến độ `{total, done, success, failed, percent, status}`. Tự động phục hồi trạng thái khi người dùng tải lại trang hoặc mất kết nối mạng.
  - **Hoàn tất & Xuất Excel:** Sau khi hoàn thành, hệ thống hiển thị bảng kết quả và nút **"Tải file Excel kết quả"** chứa thông tin đăng nhập ban đầu để bàn giao cho từng cá nhân; nút "Đóng" gọi `/admin/import-users/dismiss` dọn dẹp bộ nhớ.

### 2. Hiển Thị Tên Trường Dưới Tên Người Dùng:
- Mọi vị trí hiển thị họ tên người dùng trên toàn hệ thống đều có dòng định danh trường học: `🏫 [Tên trường]` (hoặc `🏫 Chưa phân trường` nếu chưa phân bổ).
- **Quy chuẩn giao diện:** `font-size: 0.8em; color: #6c757d; font-weight: normal;`.
- **Các màn hình đã áp dụng đồng bộ:**
  1. Trang chủ `index.html` (Bảng vinh danh gia sư tích cực).
  2. Bảng điều khiển Quản trị `/admin` (Tab tài khoản, Cảnh báo sớm AI, Hàng chờ duyệt, Vi phạm nội quy, Kỹ năng chờ duyệt & đã duyệt).
  3. Quản lý tài khoản liên trường `/admin/accounts`.
  4. Sàn / Chợ kỹ năng nội bộ `/skills/market` và liên trường `/community/market`.
  5. Trang chi tiết & đặt lịch kỹ năng `/book-skill/<id>`.
  6. Trang duyệt kỹ năng giáo viên `/skills/approval`.
  7. Điểm danh hoạt động vì cộng đồng `/community/attendance/<id>`.
  8. Giám sát phòng học ảo `/virtual-rooms/dashboard` (Phòng đang diễn ra, Cần xác minh, Đã hoàn thành).
  9. Diễn đàn thảo luận `/forum` và bài viết chi tiết `/forum/topic/<id>` (Tác giả bài viết & người bình luận).
  10. Trang hồ sơ cá nhân `/profile` (Tiêu đề hồ sơ & Thẻ bạn gia sư gợi ý từ AI).
  11. Menu Dropdown người dùng trên thanh điều hướng `base.html`.
- **Bộ lọc theo trường:** Dropdown chọn trường `#filterSchoolSelect` kết hợp ô tìm kiếm từ khóa `#searchUserTableInput` ở đầu bảng tài khoản `/admin` (Dropdown chỉ hiển thị với Super Admin).

### 3. Nghiệm Thu & Kiểm Thử:
- **Test suite:** `test_hotfix_import_and_school_display.py` đạt **10/10 tests PASS (100%)**.
- **Toàn bộ hệ thống:** **38/38 Test Suites ĐẠT 100% PASS** qua `run_all_tests.py`.

---

## 24. REDESIGN MODAL "MÔN CẦN HỖ TRỢ & KHUNG GIỜ RẢNH" (HỒ SƠ CÁ NHÂN)

### 1. Vấn Đề Đã Giải Quyết (Thực tế Production):
- **Khắc phục modal quá dài:** Trước đây mỗi môn có 1 thẻ card riêng với toggle switch (11 môn $\rightarrow$ modal dài vô tận, vượt quá chiều cao màn hình khiến chân trang chứa nút Lưu bị cắt mất).
- **Khắc phục layout nhảy:** Bật toggle mới bung dropdown và ghi chú làm form nhảy giật khó thao tác.
- **Header & Footer cố định 100%:** Thiết lập `max-height: 85vh`, `modal-header` và `modal-footer` luôn cố định với `flex-shrink: 0`, thanh cuộn dọc chỉ xuất hiện độc lập trong `modal-body`. Nút Lưu luôn nằm trong tầm nhìn của người dùng trên mọi kích cỡ màn hình.

### 2. Thiết Kế Layout 2 Cột Gọn Gàng & Thông Minh:
- **Khu vực Trái — "Môn cần hỗ trợ" (`col-12 col-md-5`):**
  - **1 Dropdown chọn nhiều môn:** Menu chọn môn học (`#selectSubjectDropdown`), khi chọn sẽ tự động sinh các tag/chip dạng badge bo tròn (`#selectedSubjectsChips`) kèm nút xóa `×`.
  - **Mức độ cần hỗ trợ chung:** Dropdown 3 mức độ rõ ràng: *Cơ bản (Củng cố kiến thức gốc)* / *Nâng cao (Nâng cao & Điểm 8+)* / *Luyện thi (Luyện thi chuyên sâu & Đại học)*.
  - **Ô ghi chú chi tiết:** Textarea 3 dòng nhập nhanh *"Phần kiến thức đang gặp khó khăn (VD: Hình không gian, viết đoạn văn, phát âm...)"*.
  - Gọn gàng trong 1 cột thẻ trắng duy nhất, loại bỏ hoàn toàn 11 thẻ card switch cồng kềnh.
- **Khu vực Phải — "Khung giờ rảnh" (`col-12 col-md-7`):**
  - **Danh sách 7 ngày (T2 - CN):** Mỗi ngày có 1 checkbox gọn gàng.
  - **Hiển thị linh hoạt theo ngày:** Khi tích chọn ngày $\rightarrow$ card ngày chuyển sang viền xanh nổi bật, hiển thị 2 ô chọn giờ: *Giờ bắt đầu* và *Giờ kết thúc*.
  - **Nút "+ Thêm khung giờ":** Cho phép thêm nhiều khung giờ trong 1 ngày (VD: Sáng 08:00 - 10:00, Chiều 14:00 - 16:00).
  - **Nút xóa (`×`):** Cho từng khung giờ đã thêm; khi xóa hết khung giờ, ngày tự động bỏ chọn.
  - **Ô ghi chú giờ giấc:** Ghi chú thêm (VD: *"Linh hoạt các buổi tối cuối tuần sau 20h"*).
- **Nút Lưu Thay Đổi Bắt Buộc:**
  - Footer trang bị nút **[Hủy bỏ]** (`btn-secondary`, màu xám) và nút **[💾 Lưu thay đổi]** (`btn-primary fw-bold shadow-sm`, màu xanh nổi bật).
  - Validation client: Kiểm tra giờ kết thúc phải sau giờ bắt đầu trên từng ngày đã chọn.
  - Lưu CSDL nguyên tử: Cập nhật `users.mon_can_ho_tro` và `users.gio_ranh`, xóa cache gợi ý AI để cập nhật tức thì.
  - Đóng modal, hiển thị thông báo thành công *"Đã cập nhật thành công!"* và tự động refresh giao diện hồ sơ.
- **Phục hồi dữ liệu tự động (Two-way Persistence):**
  - Khi mở lại modal, JavaScript tự động phân tích chuỗi giờ rảnh và JSON môn học để phục hồi chính xác toàn bộ chip môn học, mức độ, ghi chú, các ngày đã chọn và từng khung giờ (tương thích 100% cả dữ liệu cũ lẫn mới).
- **Responsive Hoàn Hảo:**
  - **Desktop ($\ge$ 768px):** 2 cột song song (Môn bên trái 5 phần, Giờ bên phải 7 phần) nằm trọn trong 1 màn hình.
  - **Mobile (< 768px):** Tự động xếp chồng dọc mượt mà (Khu vực môn trước, Khu vực giờ sau), footer và nút Lưu luôn ghim chắc chắn dưới cùng.

### 3. Nghiệm Thu & Kiểm Thử Toàn Diện:
- **Kiểm thử tự động:** Tạo mới bộ test `test_redesign_study_needs_modal.py` (5/5 tests PASS).
- **Tương thích ngược:** Giữ vững `test_prompt_smart_features.py` (6/6 tests PASS) và thuật toán `find_common_time_slots` nâng cấp nhận diện tự động khung giờ `HH:MM`.
- **Kiểm thử giao diện Playwright:** Đã tự động chụp và lưu ảnh minh chứng kiểm thử tại artifacts:
  - `desktop_modal_redesigned.png`: Giao diện 2 cột desktop đầy đủ chip, nhiều ca học trong ngày.
  - `mobile_modal_redesigned.png`: Giao diện responsive mobile xếp chồng dọc, nút Lưu cố định.
  - `profile_after_save.png`: Trang hồ sơ cập nhật thành công các huy hiệu môn và khung giờ rảnh.
  - `modal_restored_data.png`: Mở lại modal phục hồi chính xác 100% dữ liệu đã lưu.
- **Kết quả Regression:** **39/39 Test Suites ĐẠT 100% PASS** qua `run_all_tests.py`.

