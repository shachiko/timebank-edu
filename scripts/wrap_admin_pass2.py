import re

with open('templates/admin.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ("{{ learning_stats.completed_sessions_count }} phiên</div>",
     "{{ learning_stats.completed_sessions_count }} {{ _('phiên') }}</div>"),
    ("{{ learning_stats.total_quizzes }} bài làm</div>",
     "{{ learning_stats.total_quizzes }} {{ _('bài làm') }}</div>"),
    ("{{ \"%.2f\"|format(learning_stats.growth_diff) }} điểm</div>",
     "{{ \"%.2f\"|format(learning_stats.growth_diff) }} {{ _('điểm') }}</div>"),
    ("Danh sách học sinh trường {{ current_school_name }} {{ _('chưa có mã mời đang chờ duyệt.') }}",
     "{{ _('Danh sách học sinh trường') }} {{ current_school_name }} {{ _('chưa có mã mời đang chờ duyệt.') }}"),
    ("{{ last_import_result.errors|length }} dòng</span>",
     "{{ last_import_result.errors|length }} {{ _('dòng') }}</span>"),
    ("<th style=\"width: 220px;\">Họ và tên</th>",
     "<th style=\"width: 220px;\">{{ _('Họ và tên') }}</th>"),
    ("• Lớp: {{ sk.lop }}</small>",
     "• {{ _('Lớp:') }} {{ sk.lop }}</small>"),
    ("<i class=\"bi bi-check-lg me-1\"></i>{{ _('Duyệt') }} lên Liên trường",
     "<i class=\"bi bi-check-lg me-1\"></i>{{ _('Duyệt lên Liên trường') }}"),
    ("<label class=\"form-label small fw-semibold\">Trường áp dụng</label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Trường áp dụng') }}</label>"),
    ("<th style=\"width: 130px;\">Trạng thái</th>",
     "<th style=\"width: 130px;\">{{ _('Trạng thái') }}</th>"),
    ("{{ task.ten_truong or 'Toàn hệ thống' }}",
     "{{ task.ten_truong or _('Toàn hệ thống') }}"),
    ("<span class=\"badge bg-info text-dark rounded-pill px-2 py-1\"><i class=\"bi bi-hourglass-split me-1\"></i>Sắp diễn ra</span>",
     "<span class=\"badge bg-info text-dark rounded-pill px-2 py-1\"><i class=\"bi bi-hourglass-split me-1\"></i>{{ _('Sắp diễn ra') }}</span>"),
    ("<span class=\"badge bg-success rounded-pill px-2 py-1\"><i class=\"bi bi-play-circle me-1\"></i>Đang diễn ra</span>",
     "<span class=\"badge bg-success rounded-pill px-2 py-1\"><i class=\"bi bi-play-circle me-1\"></i>{{ _('Đang diễn ra') }}</span>"),
    ("<span class=\"badge bg-secondary rounded-pill px-2 py-1\"><i class=\"bi bi-check2-circle me-1\"></i>Đã kết thúc</span>",
     "<span class=\"badge bg-secondary rounded-pill px-2 py-1\"><i class=\"bi bi-check2-circle me-1\"></i>{{ _('Đã kết thúc') }}</span>"),
    ("{{ task.so_luong_da_dang_ky }} bạn\n",
     "{{ task.so_luong_da_dang_ky }} {{ _('bạn') }}\n"),
    ("title=\"{{ 'Chuyển sang Đã kết thúc' if task.so_luong_da_dang_ky > 0 else 'Xóa vĩnh viễn' }}\"",
     "title=\"{{ _('Chuyển sang Đã kết thúc') if task.so_luong_da_dang_ky > 0 else _('Xóa vĩnh viễn') }}\""),
    ("<i class=\"bi bi-trash me-1\"></i>Xóa\n",
     "<i class=\"bi bi-trash me-1\"></i>{{ _('Xóa') }}\n"),
    ("<i class=\"bi bi-pencil-square text-primary me-2\"></i>Chỉnh Sửa Chương Trình Cộng Đồng #{{ task.id }}",
     "<i class=\"bi bi-pencil-square text-primary me-2\"></i>{{ _('Chỉnh Sửa Chương Trình Cộng Đồng') }} #{{ task.id }}"),
    ("<label class=\"form-label small fw-semibold\">Tên chương trình <span class=\"text-danger\">*</span></label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Tên chương trình') }} <span class=\"text-danger\">*</span></label>"),
    ("<option value=\"sap_dien_ra\" {% if task.trang_thai == 'sap_dien_ra' %}selected{% endif %}>Sắp diễn ra</option>",
     "<option value=\"sap_dien_ra\" {% if task.trang_thai == 'sap_dien_ra' %}selected{% endif %}>{{ _('Sắp diễn ra') }}</option>"),
    ("<option value=\"dang_dien_ra\" {% if task.trang_thai in ('dang_dien_ra', 'mo_dang_ky', 'mo') %}selected{% endif %}>Đang diễn ra</option>",
     "<option value=\"dang_dien_ra\" {% if task.trang_thai in ('dang_dien_ra', 'mo_dang_ky', 'mo') %}selected{% endif %}>{{ _('Đang diễn ra') }}</option>"),
    ("<option value=\"da_ket_thuc\" {% if task.trang_thai in ('da_ket_thuc', 'hoan_thanh', 'dong') %}selected{% endif %}>Đã kết thúc</option>",
     "<option value=\"da_ket_thuc\" {% if task.trang_thai in ('da_ket_thuc', 'hoan_thanh', 'dong') %}selected{% endif %}>{{ _('Đã kết thúc') }}</option>"),
    ("<label class=\"form-label small fw-semibold\">Địa điểm tổ chức</label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Địa điểm tổ chức') }}</label>"),
    ("placeholder=\"Ví dụ: Thư viện tầng 2, Sân trường...\"",
     "placeholder=\"{{ _('Ví dụ: Thư viện tầng 2, Sân trường...') }}\""),
    ("<label class=\"form-label small fw-semibold\">Mô tả nội dung</label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Mô tả nội dung') }}</label>"),
    ("<button type=\"button\" class=\"btn btn-light rounded-pill px-3\" data-bs-dismiss=\"modal\">Hủy</button>",
     "<button type=\"button\" class=\"btn btn-light rounded-pill px-3\" data-bs-dismiss=\"modal\">{{ _('Hủy') }}</button>"),
    ("<i class=\"bi bi-check2-circle me-1\"></i> Lưu thay đổi",
     "<i class=\"bi bi-check2-circle me-1\"></i> {{ _('Lưu thay đổi') }}"),
    ("<h6 class=\"fw-bold\">Chưa có chương trình cộng đồng nào</h6>",
     "<h6 class=\"fw-bold\">{{ _('Chưa có chương trình cộng đồng nào') }}</h6>"),
    ("<p class=\"small mb-0\">Hãy sử dụng biểu mẫu phía trên để phát động chương trình giờ công ích đầu tiên cho học sinh!</p>",
     "<p class=\"small mb-0\">{{ _('Hãy sử dụng biểu mẫu phía trên để phát động chương trình giờ công ích đầu tiên cho học sinh!') }}</p>"),
    ("<i class=\"bi bi-building-add text-primary me-2\"></i>{{ _('Thêm Trường Học Mới') }} Vào Hệ Thống",
     "<i class=\"bi bi-building-add text-primary me-2\"></i>{{ _('Thêm Trường Học Mới Vào Hệ Thống') }}"),
    ("<p class=\"text-muted small mb-0\">Hệ thống sẽ tự động cấp phát ID mới, cho phép tạo mã mời riêng và cách ly dữ liệu học sinh theo trường.</p>",
     "<p class=\"text-muted small mb-0\">{{ _('Hệ thống sẽ tự động cấp phát ID mới, cho phép tạo mã mời riêng và cách ly dữ liệu học sinh theo trường.') }}</p>"),
    ("placeholder=\"Ví dụ: THPT Chuyên Hạ Long\"",
     "placeholder=\"{{ _('Ví dụ: THPT Chuyên Hạ Long') }}\""),
    ("<label class=\"form-label small fw-semibold\">Trạng thái ban đầu <span class=\"text-danger\">*</span></label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Trạng thái ban đầu') }} <span class=\"text-danger\">*</span></label>"),
    ("<option value=\"chuan_bi_trien_khai\">Chuẩn bị triển khai</option>",
     "<option value=\"chuan_bi_trien_khai\">{{ _('Chuẩn bị triển khai') }}</option>"),
    ("<option value=\"dang_thi_diem\" selected>Đang thí điểm</option>",
     "<option value=\"dang_thi_diem\" selected>{{ _('Đang thí điểm') }}</option>"),
    ("<option value=\"tam_ngung\">Tạm ngưng</option>",
     "<option value=\"tam_ngung\">{{ _('Tạm ngưng') }}</option>"),
    ("<label class=\"form-label small fw-semibold\">Logo trường (Tùy chọn tải lên)</label>",
     "<label class=\"form-label small fw-semibold\">{{ _('Logo trường (Tùy chọn tải lên)') }}</label>"),
    ("<i class=\"bi bi-plus-circle me-1\"></i> Thêm Trường Mới",
     "<i class=\"bi bi-plus-circle me-1\"></i> {{ _('Thêm Trường Mới') }}"),
    ("<i class=\"bi bi-buildings-fill me-2 text-primary\"></i>Danh Sách Trường Học Đang Quản Trị",
     "<i class=\"bi bi-buildings-fill me-2 text-primary\"></i>{{ _('Danh Sách Trường Học Đang Quản Trị') }}"),
    ("<th class=\"ps-3\" style=\"width: 100px;\">Mã trường</th>",
     "<th class=\"ps-3\" style=\"width: 100px;\">{{ _('Mã trường') }}</th>"),
    ("<th>Tên trường học</th>",
     "<th>{{ _('Tên trường học') }}</th>"),
    ("<th class=\"text-center\" style=\"width: 200px;\">Trạng thái</th>",
     "<th class=\"text-center\" style=\"width: 200px;\">{{ _('Trạng thái') }}</th>"),
    ("<th class=\"text-center\" style=\"width: 130px;\">Số tài khoản</th>",
     "<th class=\"text-center\" style=\"width: 130px;\">{{ _('Số tài khoản') }}</th>"),
    ("<th style=\"width: 160px;\">Ngày tạo</th>",
     "<th style=\"width: 160px;\">{{ _('Ngày tạo') }}</th>"),
    ("<th class=\"text-end pe-3\" style=\"width: 220px;\">Thao tác</th>",
     "<th class=\"text-end pe-3\" style=\"width: 220px;\">{{ _('Thao tác') }}</th>"),
    ("Trường #{{ s.id }}</span>",
     "{{ _('Trường #') }}{{ s.id }}</span>"),
    ("<small class=\"text-muted fst-italic\">Trường dữ liệu mẫu demo hệ thống</small>",
     "<small class=\"text-muted fst-italic\">{{ _('Trường dữ liệu mẫu demo hệ thống') }}</small>"),
    ("<i class=\"bi bi-flag-fill me-1\"></i>Đang thí điểm",
     "<i class=\"bi bi-flag-fill me-1\"></i>{{ _('Đang thí điểm') }}"),
    ("&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;├── 📁 Toán/<br>",
     "&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;├── 📁 {{ _('Toán') }}/<br>"),
    ("&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;├── 📁 Ngữ văn/<br>",
     "&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;├── 📁 {{ _('Ngữ văn') }}/<br>"),
    ("&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;└── 📁 Tiếng Anh/...<br>",
     "&nbsp;&nbsp;│&nbsp;&nbsp;&nbsp;└── 📁 {{ _('Tiếng Anh') }}/...<br>"),
    ("<span class=\"badge bg-primary-subtle text-primary ms-auto\">Trường của {{ _('bạn') }}</span>",
     "<span class=\"badge bg-primary-subtle text-primary ms-auto\">{{ _('Trường của bạn') }}</span>"),
]

for src, dst in replacements:
    if src in content:
        content = content.replace(src, dst)
    else:
        print(f"Not found: {src[:40]}")

# Also replace the confirm on line 1122 and 1345 safely
content = content.replace(
    "onsubmit=\"return confirm('{{ 'Chương trình này đã có học sinh đăng ký tham gia. Hệ thống sẽ chuyển trạng thái sang Đã kết thúc thay vì xóa vĩnh viễn để bảo toàn lịch sử học tập. Bạn có đồng ý không?' if task.so_luong_da_dang_ky > 0 else 'Bạn có chắc chắn muốn xóa vĩnh viễn chương trình cộng đồng này không?' }}');\"",
    "onsubmit=\"return confirm('{{ _('Chương trình này đã có học sinh đăng ký tham gia. Hệ thống sẽ chuyển trạng thái sang Đã kết thúc thay vì xóa vĩnh viễn để bảo toàn lịch sử học tập. Bạn có đồng ý không?') if task.so_luong_da_dang_ky > 0 else _('Bạn có chắc chắn muốn xóa vĩnh viễn chương trình cộng đồng này không?') }}');\""
)

content = content.replace(
    "onsubmit=\"return confirm('{{ 'Bạn có chắc chắn muốn hiện lại trường này? Trường sẽ xuất hiện trở lại trên hệ thống.' if s.an_truong == 1 or s.trang_thai in ('vo_hieu_hoa', 'tam_ngung') else 'Bạn có chắc chắn muốn ẩn trường này khỏi hệ thống? Dữ liệu không bị xóa.' }}');\"",
    "onsubmit=\"return confirm('{{ _('Bạn có chắc chắn muốn hiện lại trường này? Trường sẽ xuất hiện trở lại trên hệ thống.') if s.an_truong == 1 or s.trang_thai in ('vo_hieu_hoa', 'tam_ngung') else _('Bạn có chắc chắn muốn ẩn trường này khỏi hệ thống? Dữ liệu không bị xóa.') }}');\""
)

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Pass 2 complete.")
