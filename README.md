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

## 8. Tính trung thực về AI
Hệ thống tuân thủ nghiêm ngặt nguyên tắc minh bạch: Mọi vị trí có sự tham gia của Trí tuệ nhân tạo (kiểm duyệt, gợi ý ghép cặp, dàn ý buổi học, tạo trắc nghiệm) đều được gắn nhãn nhận diện rõ ràng: **"Hỗ trợ bởi AI (Gemini)"**.
