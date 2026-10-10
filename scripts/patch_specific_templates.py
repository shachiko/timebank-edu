import os

def patch_file(filepath, mapping):
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    for src, dst in mapping:
        if src in content:
            content = content.replace(src, dst)
        else:
            print(f"[{filepath}] Not found: {src[:40]}")
    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {filepath}")

# 1. community.html
patch_file('templates/community.html', [
    ("Mở rộng mô hình ngân hàng thời gian: Tham gia dọn dẹp bãi biển, hỗ trợ số hóa sách thư viện,\n      dạy tin học cho đàn em... để nhận thêm tín dụng thời gian vào ví học tập!",
     "{{ _('Mở rộng mô hình ngân hàng thời gian: Tham gia dọn dẹp bãi biển, hỗ trợ số hóa sách thư viện, dạy tin học cho đàn em... để nhận thêm tín dụng thời gian vào ví học tập!') }}"),
    ("{{ so_hs_tham_gia }} bạn</h3>", "{{ so_hs_tham_gia }} {{ _('bạn') }}</h3>"),
    ("<h4 class=\"fw-bold text-dark mb-0\">Trợ lý AI Đề xuất Riêng cho {{ current_user.ho_ten }}</h4>",
     "<h4 class=\"fw-bold text-dark mb-0\">{{ _('Trợ lý AI Đề xuất Riêng cho') }} {{ current_user.ho_ten }}</h4>"),
    ("+{{ \"%.1f\"|format(task.so_gio_thuong) }}h thưởng",
     "+{{ \"%.1f\"|format(task.so_gio_thuong) }}{{ _('h thưởng') }}"),
    ("{{ task.so_luong_da_dang_ky }}/{{ task.so_luong_toi_da }} bạn",
     "{{ task.so_luong_da_dang_ky }}/{{ task.so_luong_toi_da }} {{ _('bạn') }}"),
    ("<i class=\"bi bi-check-circle-fill me-1\"></i> Đã hoàn thành (+{{ \"%.1f\"|format(task.so_gio_thuong) }}h)",
     "<i class=\"bi bi-check-circle-fill me-1\"></i> {{ _('Đã hoàn thành') }} (+{{ \"%.1f\"|format(task.so_gio_thuong) }}h)"),
    ("Thưởng +{{ \"%.1f\"|format(task.so_gio_thuong) }} giờ",
     "{{ _('Thưởng') }} +{{ \"%.1f\"|format(task.so_gio_thuong) }} {{ _('giờ') }}"),
    ("{{ task.so_luong_da_dang_ky }} / {{ task.so_luong_toi_da }} bạn",
     "{{ task.so_luong_da_dang_ky }} / {{ task.so_luong_toi_da }} {{ _('bạn') }}"),
    ("<i class=\"bi bi-card-checklist me-1\"></i> Danh sách & Điểm danh ({{ task.so_luong_da_dang_ky }})",
     "<i class=\"bi bi-card-checklist me-1\"></i> {{ _('Danh sách & Điểm danh') }} ({{ task.so_luong_da_dang_ky }})"),
    ("<span class=\"text-muted small\">+{{ \"%.1f\"|format(c_task.so_gio_thuong) }}h thưởng</span>",
     "<span class=\"text-muted small\">+{{ \"%.1f\"|format(c_task.so_gio_thuong) }}{{ _('h thưởng') }}</span>"),
    ("{{ c_task.so_luong_hoan_thanh }} bạn đã nhận tín dụng",
     "{{ c_task.so_luong_hoan_thanh }} {{ _('bạn đã nhận tín dụng') }}"),
    ("để học sinh đăng ký tham gia.",
     "{{ _('để học sinh đăng ký tham gia.') }}"),
    ("Sau khi hoạt động kết thúc, Thầy/Cô điểm danh để cộng giờ thưởng vào ví học sinh.",
     "{{ _('Sau khi hoạt động kết thúc, Thầy/Cô điểm danh để cộng giờ thưởng vào ví học sinh.') }}"),
])

# 2. session_detail.html
patch_file('templates/session_detail.html', [
    ("<div class=\"text-muted small\">Lớp: {{ session_data.lop_nguoi_day }} • Mã: <code>{{ session_data.ma_nguoi_day }}</code></div>",
     "<div class=\"text-muted small\">{{ _('Lớp:') }} {{ session_data.lop_nguoi_day }} • {{ _('Mã:') }} <code>{{ session_data.ma_nguoi_day }}</code></div>"),
    ("Nhận +{{ \"%.1f\"|format(session_data.so_gio) }} giờ khi xong",
     "{{ _('Nhận') }} +{{ \"%.1f\"|format(session_data.so_gio) }} {{ _('giờ khi xong') }}"),
    ("<div class=\"text-muted small\">Lớp: {{ session_data.lop_nguoi_hoc }} • Mã: <code>{{ session_data.ma_nguoi_hoc }}</code></div>",
     "<div class=\"text-muted small\">{{ _('Lớp:') }} {{ session_data.lop_nguoi_hoc }} • {{ _('Mã:') }} <code>{{ session_data.ma_nguoi_hoc }}</code></div>"),
    ("Đổi -{{ \"%.1f\"|format(session_data.so_gio) }} giờ khi xong",
     "{{ _('Đổi') }} -{{ \"%.1f\"|format(session_data.so_gio) }} {{ _('giờ khi xong') }}"),
    ("{{ \"%.1f\"|format(session_data.so_gio) }} giờ ({{ \"%.0f\"|format(session_data.so_gio * 60) }} phút)",
     "{{ \"%.1f\"|format(session_data.so_gio) }} {{ _('giờ') }} ({{ \"%.0f\"|format(session_data.so_gio * 60) }} {{ _('phút') }})"),
    ("<div class=\"fw-bold text-dark\">Bộ câu hỏi trắc nghiệm ({{ quiz_question_count }} câu)</div>",
     "<div class=\"fw-bold text-dark\">{{ _('Bộ câu hỏi trắc nghiệm') }} ({{ quiz_question_count }} {{ _('câu') }})</div>"),
    ("Học sinh đã hoàn thành: <strong>{{ \"%.1f\"|format(quiz_result.diem_so) }}/5.0 điểm</strong> (Tự tin trước: {{ \"%.1f\"|format(quiz_result.tu_danh_gia_truoc) }}★).",
     "{{ _('Học sinh đã hoàn thành:') }} <strong>{{ \"%.1f\"|format(quiz_result.diem_so) }}/5.0 {{ _('điểm') }}</strong> ({{ _('Tự tin trước:') }} {{ \"%.1f\"|format(quiz_result.tu_danh_gia_truoc) }}★)."),
    ("Đã sẵn sàng. Đang chờ học sinh làm bài lượng giá kiến thức.",
     "{{ _('Đã sẵn sàng. Đang chờ học sinh làm bài lượng giá kiến thức.') }}"),
    ("<i class=\"bi bi-pencil-square me-1\"></i> Làm bài Quiz ngay",
     "<i class=\"bi bi-pencil-square me-1\"></i> {{ _('Làm bài Quiz ngay') }}"),
    ("<i class=\"bi bi-eye me-1\"></i> Xem chi tiết Quiz",
     "<i class=\"bi bi-eye me-1\"></i> {{ _('Xem chi tiết Quiz') }}"),
    ("alt=\"Mã QR Phiên Học\"",
     "alt=\"{{ _('Mã QR Phiên Học') }}\""),
    ("<span class=\"fw-semibold text-dark\">1. Người dạy ({{ session_data.ten_nguoi_day }}):</span>",
     "<span class=\"fw-semibold text-dark\">1. {{ _('Người dạy') }} ({{ session_data.ten_nguoi_day }}):</span>"),
    ("<span class=\"fw-semibold text-dark\">2. Người học ({{ session_data.ten_nguoi_hoc }}):</span>",
     "<span class=\"fw-semibold text-dark\">2. {{ _('Người học') }} ({{ session_data.ten_nguoi_hoc }}):</span>"),
    ("Đã ghi nhận 2 giao dịch vào Ví: +{{ \"%.1f\"|format(session_data.so_gio) }}h cho {{ session_data.ten_nguoi_day }} và -{{ \"%.1f\"|format(session_data.so_gio) }}h cho {{ session_data.ten_nguoi_hoc }}.",
     "{{ _('Đã ghi nhận 2 giao dịch vào Ví: +') }}{{ \"%.1f\"|format(session_data.so_gio) }}{{ _('h cho') }} {{ session_data.ten_nguoi_day }} {{ _('và -') }}{{ \"%.1f\"|format(session_data.so_gio) }}{{ _('h cho') }} {{ session_data.ten_nguoi_hoc }}."),
    ("my_rating.nhan_xet if my_rating.nhan_xet else 'Không có nhận xét thêm'",
     "my_rating.nhan_xet if my_rating.nhan_xet else _('Không có nhận xét thêm')"),
    ("Bạn hãy đánh giá thái độ học tập và mức độ tương tác của bạn học <strong>{{ session_data.ten_nguoi_hoc }}</strong>:",
     "{{ _('Bạn hãy đánh giá thái độ học tập và mức độ tương tác của bạn học') }} <strong>{{ session_data.ten_nguoi_hoc }}</strong>:"),
    ("Bạn hãy đánh giá kỹ năng truyền đạt và sự nhiệt tình của bạn gia sư <strong>{{ session_data.ten_nguoi_day }}</strong>:",
     "{{ _('Bạn hãy đánh giá kỹ năng truyền đạt và sự nhiệt tình của bạn gia sư') }} <strong>{{ session_data.ten_nguoi_day }}</strong>:"),
    ("<i class=\"bi bi-chat-quote-fill me-1\"></i> {{ partner_rating.ten_nguoi_danh_gia }} nhận xét về bạn:",
     "<i class=\"bi bi-chat-quote-fill me-1\"></i> {{ partner_rating.ten_nguoi_danh_gia }} {{ _('nhận xét về bạn:') }}"),
    ("partner_rating.nhan_xet if partner_rating.nhan_xet else 'Không có nhận xét thêm'",
     "partner_rating.nhan_xet if partner_rating.nhan_xet else _('Không có nhận xét thêm')"),
])

# 3. virtual_room.html
patch_file('templates/virtual_room.html', [
    ("Đang khởi tạo mã định danh 1 chạm an toàn cho {{ current_user.ho_ten }}",
     "{{ _('Đang khởi tạo mã định danh 1 chạm an toàn cho') }} {{ current_user.ho_ten }}"),
    ("onclick=\"window.switchToPublicJitsi('Lỗi khởi tạo nòng chính, chuyển thủ công sang Jitsi')\"",
     "onclick=\"window.switchToPublicJitsi('{{ _('Lỗi khởi tạo nòng chính, chuyển thủ công sang Jitsi') }}')\""),
    ("<div class=\"text-muted small\">Lớp: {{ session_data.lop_nguoi_day }} • <code>{{ session_data.ma_nguoi_day }}</code></div>",
     "<div class=\"text-muted small\">{{ _('Lớp:') }} {{ session_data.lop_nguoi_day }} • <code>{{ session_data.ma_nguoi_day }}</code></div>"),
    ("<div class=\"text-muted small\">Lớp: {{ session_data.lop_nguoi_hoc }} • <code>{{ session_data.ma_nguoi_hoc }}</code></div>",
     "<div class=\"text-muted small\">{{ _('Lớp:') }} {{ session_data.lop_nguoi_hoc }} • <code>{{ session_data.ma_nguoi_hoc }}</code></div>"),
    ("{{ \"%.1f\"|format(session_data.so_gio) }} giờ ({{ \"%.0f\"|format(session_data.so_gio * 60) }} phút)",
     "{{ \"%.1f\"|format(session_data.so_gio) }} {{ _('giờ') }} ({{ \"%.0f\"|format(session_data.so_gio * 60) }} {{ _('phút') }})"),
    ("{{ \"%.0f\"|format(session_data.so_gio * 60 * 0.8) }} phút",
     "{{ \"%.0f\"|format(session_data.so_gio * 60 * 0.8) }} {{ _('phút') }}"),
    ("showLoading(\"Đang Kết Nối Phòng Học Daily.co...\", \"Đang khởi tạo mã phòng học 1 chạm cho \" + userName);",
     "showLoading(\"{{ _('Đang Kết Nối Phòng Học...') }}\", \"{{ _('Đang khởi tạo mã phòng học 1 chạm cho ') }}\" + userName);"),
    ("switchToJaaS(\"Không thể kết nối Daily.co. Tự động chuyển nòng dự phòng...\");",
     "switchToJaaS(\"{{ _('Không thể kết nối Daily.co. Tự động chuyển nòng dự phòng...') }}\");"),
    ("switchToJaaS(\"Thiếu URL hoặc token phòng học Daily.co. Tự động chuyển nòng dự phòng...\");",
     "switchToJaaS(\"{{ _('Thiếu URL hoặc token phòng học Daily.co. Tự động chuyển nòng dự phòng...') }}\");"),
    ("switchToJaaS(\"Không thể tải SDK Daily.co. Tự động chuyển nòng dự phòng...\");",
     "switchToJaaS(\"{{ _('Không thể tải SDK Daily.co. Tự động chuyển nòng dự phòng...') }}\");"),
    ("switchToJaaS(\"Không thể vào phòng Daily.co. Tự động chuyển nòng dự phòng...\");",
     "switchToJaaS(\"{{ _('Không thể vào phòng Daily.co. Tự động chuyển nòng dự phòng...') }}\");"),
    ("showLoading(\"Đang Kết Nối Lớp Học Ảo...\", reasonMsg || (\"Đang khởi tạo mã định danh 1 chạm an toàn cho \" + userName));",
     "showLoading(\"{{ _('Đang Kết Nối Lớp Học Ảo...') }}\", reasonMsg || (\"{{ _('Đang khởi tạo mã định danh 1 chạm an toàn cho ') }}\" + userName));"),
    ("fallbackText.textContent = \"Đang dùng phòng học dự phòng (Jitsi)\";",
     "fallbackText.textContent = \"{{ _('Đang dùng phòng học dự phòng (Jitsi)') }}\";"),
    ("window.switchToPublicJitsi(\"Cấu hình chọn dùng trực tiếp phòng học dự phòng Jitsi.\");",
     "window.switchToPublicJitsi(\"{{ _('Cấu hình chọn dùng trực tiếp phòng học dự phòng Jitsi.') }}\");"),
])

# 4. ai_matchmake.html
patch_file('templates/ai_matchmake.html', [
    ("<option value=\"Mất gốc / Người mới bắt đầu\" {% if form_data and form_data.trinh_do == 'Mất gốc / Người mới bắt đầu' %}selected{% endif %}>Mất gốc / Người mới bắt đầu</option>",
     "<option value=\"Mất gốc / Người mới bắt đầu\" {% if form_data and form_data.trinh_do == 'Mất gốc / Người mới bắt đầu' %}selected{% endif %}>{{ _('Mất gốc / Người mới bắt đầu') }}</option>"),
    ("<option value=\"Cơ bản (Cần luyện thêm bài tập)\" {% if not form_data or form_data.trinh_do == 'Cơ bản (Cần luyện thêm bài tập)' %}selected{% endif %}>Cơ bản (Cần luyện thêm bài tập)</option>",
     "<option value=\"Cơ bản (Cần luyện thêm bài tập)\" {% if not form_data or form_data.trinh_do == 'Cơ bản (Cần luyện thêm bài tập)' %}selected{% endif %}>{{ _('Cơ bản (Cần luyện thêm bài tập)') }}</option>"),
    ("<option value=\"Khá (Muốn nâng cao tư duy)\" {% if form_data and form_data.trinh_do == 'Khá (Muốn nâng cao tư duy)' %}selected{% endif %}>Khá (Muốn nâng cao tư duy)</option>",
     "<option value=\"Khá (Muốn nâng cao tư duy)\" {% if form_data and form_data.trinh_do == 'Khá (Muốn nâng cao tư duy)' %}selected{% endif %}>{{ _('Khá (Muốn nâng cao tư duy)') }}</option>"),
    ("<option value=\"Ôn thi học kỳ / Đề thi tốt nghiệp\" {% if form_data and form_data.trinh_do == 'Ôn thi học kỳ / Đề thi tốt nghiệp' %}selected{% endif %}>Ôn thi học kỳ / Đề thi tốt nghiệp</option>",
     "<option value=\"Ôn thi học kỳ / Đề thi tốt nghiệp\" {% if form_data and form_data.trinh_do == 'Ôn thi học kỳ / Đề thi tốt nghiệp' %}selected{% endif %}>{{ _('Ôn thi học kỳ / Đề thi tốt nghiệp') }}</option>"),
    ("Tìm thấy {{ matches|length }} gợi ý</span>",
     "{{ _('Tìm thấy') }} {{ matches|length }} {{ _('gợi ý') }}</span>"),
    ("(Lớp {{ item.lop }})",
     "({{ _('Lớp') }} {{ item.lop }})"),
    ("Rảnh: {{ item.gio_ranh }}",
     "{{ _('Rảnh:') }} {{ item.gio_ranh }}"),
    ("Đặt Lịch Học Kèm Với {{ item.ho_ten }}",
     "{{ _('Đặt Lịch Học Kèm Với') }} {{ item.ho_ten }}"),
])

# 5. profile.html
patch_file('templates/profile.html', [
    ("'Chưa cập nhật'", "_('Chưa cập nhật')"),
    ("Từ {{ rating_count }} lượt đánh giá",
     "{{ _('Từ') }} {{ rating_count }} {{ _('lượt đánh giá') }}"),
    ("Gia sư phù hợp nhất cho môn {{ target_subject }}",
     "{{ _('Gia sư phù hợp nhất cho môn') }} {{ target_subject }}"),
    ("(Lớp {{ match.lop }})",
     "({{ _('Lớp') }} {{ match.lop }})"),
    ("Phiên #{{ item.session_id }}</span>",
     "{{ _('Phiên #') }}{{ item.session_id }}</span>"),
])

# 6. blog_form.html & blog_list.html & blog_manage.html
patch_file('templates/blog_form.html', [
    ("{% if action == 'create' %}Viết bài mới{% else %}Chỉnh sửa bài #{{ post.id }}{% endif %}",
     "{% if action == 'create' %}{{ _('Viết bài mới') }}{% else %}{{ _('Chỉnh sửa bài #') }}{{ post.id }}{% endif %}"),
    ("<i class=\"bi bi-pencil-square me-2\"></i>Viết bài mới cho Bảng tin học đường",
     "<i class=\"bi bi-pencil-square me-2\"></i>{{ _('Viết bài mới cho Bảng tin học đường') }}"),
    ("<i class=\"bi bi-pencil me-2\"></i>Chỉnh sửa bài viết: {{ post.tieu_de }}",
     "<i class=\"bi bi-pencil me-2\"></i>{{ _('Chỉnh sửa bài viết:') }} {{ post.tieu_de }}"),
    ("{% if action == 'create' %}Lưu bài viết{% else %}Cập nhật bài viết{% endif %}",
     "{% if action == 'create' %}{{ _('Lưu bài viết') }}{% else %}{{ _('Cập nhật bài viết') }}{% endif %}"),
])

patch_file('templates/blog_list.html', [
    ("Tổng số: {{ posts|length }} bài viết đã công khai",
     "{{ _('Tổng số:') }} {{ posts|length }} {{ _('bài viết đã công khai') }}"),
    ("{% if post.tac_gia_ai == 1 %}Bản tin AI{% else %}Giáo viên{% endif %}",
     "{% if post.tac_gia_ai == 1 %}{{ _('Bản tin AI') }}{% else %}{{ _('Giáo viên') }}{% endif %}"),
])

patch_file('templates/blog_manage.html', [
    ("Tổng số: {{ posts|length }} mục",
     "{{ _('Tổng số:') }} {{ posts|length }} {{ _('mục') }}"),
])

# 7. documents_index.html & documents_upload.html
patch_file('templates/documents_index.html', [
    ("{{ doc.luot_tai or 0 }} lượt tải",
     "{{ doc.luot_tai or 0 }} {{ _('lượt tải') }}"),
])

patch_file('templates/documents_upload.html', [
    ("notice.textContent = 'Có tệp vượt quá giới hạn 500MB!';",
     "notice.textContent = '{{ _('Có tệp vượt quá giới hạn 500MB!') }}';"),
])

# 8. wallet.html & my_schedule.html & noi_quy.html
patch_file('templates/wallet.html', [
    ("Tổng {{ ledger_entries|length }} giao dịch",
     "{{ _('Tổng') }} {{ ledger_entries|length }} {{ _('giao dịch') }}"),
    ("Phiên #{{ item.session_id }}",
     "{{ _('Phiên #') }}{{ item.session_id }}"),
])

patch_file('templates/my_schedule.html', [
    ("Lớp {{ s.lop_nguoi_hoc }}",
     "{{ _('Lớp') }} {{ s.lop_nguoi_hoc }}"),
    ("Lớp {{ s.lop_nguoi_day }}",
     "{{ _('Lớp') }} {{ s.lop_nguoi_day }}"),
])

patch_file('templates/noi_quy.html', [
    ("Để đảm bảo một không gian giáo dục an toàn, tích cực, không bạo lực học đường và tôn trọng lẫn nhau, mọi học sinh và cán bộ giáo viên tham gia hệ thống phải tuân thủ nghiêm ngặt",
     "{{ _('Để đảm bảo một không gian giáo dục an toàn, tích cực, không bạo lực học đường và tôn trọng lẫn nhau, mọi học sinh và cán bộ giáo viên tham gia hệ thống phải tuân thủ nghiêm ngặt') }}"),
])

# 9. errors/403.html
patch_file('templates/errors/403.html', [
    ("không có thẩm quyền truy cập vào bảng điều khiển quản trị hoặc tính năng này.",
     "{{ _('không có thẩm quyền truy cập vào bảng điều khiển quản trị hoặc tính năng này.') }}"),
    ("'Chưa đăng nhập'",
     "_('Chưa đăng nhập')"),
])

print("Finished targeted patching.")
