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
│       └── logo.svg        # Biểu trưng TimeBank EDU (Đồng hồ & Giáo dục)
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
ten_truong: "THPT Chuyên Thực Nghiệm Sáng Tạo"
logo_path: "/static/img/logo.svg"
mau_chu_dao: "#1e40af"
email_lien_he: "lienhe@timebank-edu.vn"
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

## 14. Tính bảo mật và biến môi trường
- File `.env` chứa `GEMINI_API_KEY` và `FLASK_SECRET_KEY` được bảo vệ nghiêm ngặt bằng `.gitignore`, **TUYỆT ĐỐI KHÔNG BAO GIỜ** được push lên GitHub công khai.
- Cung cấp file mẫu `.env.example` với hướng dẫn cấu hình chi tiết cho các trường triển khai.



