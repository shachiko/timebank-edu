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









