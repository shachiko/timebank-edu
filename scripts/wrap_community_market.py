with open('templates/community_market.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ("{% block title %}Cộng Đồng Liên Trường — School Time Bank{% endblock %}",
     "{% block title %}{{ _('Cộng Đồng Liên Trường — School Time Bank') }}{% endblock %}"),
    ('<i class="bi bi-globe2 me-1"></i> KHÔNG GIAN GIAO LƯU LIÊN TRƯỜNG',
     '<i class="bi bi-globe2 me-1"></i> {{ _(\'KHÔNG GIAN GIAO LƯU LIÊN TRƯỜNG\') }}'),
    ('Cổng kiểm chuẩn {{ threshold|int if threshold == threshold|int else threshold }}h dạy',
     '{{ _(\'Cổng kiểm chuẩn\') }} {{ threshold|int if threshold == threshold|int else threshold }}{{ _(\'h dạy\') }}'),
    ('<h2 class="fw-bold mb-0 text-dark">Cộng Đồng Liên Trường</h2>',
     '<h2 class="fw-bold mb-0 text-dark">{{ _(\'Cộng Đồng Liên Trường\') }}</h2>'),
    ('Nơi học sinh các trường trao đổi tri thức, sẻ chia kỹ năng bằng ví tín dụng thời gian hợp nhất.',
     '{{ _(\'Nơi học sinh các trường trao đổi tri thức, sẻ chia kỹ năng bằng ví tín dụng thời gian hợp nhất.\') }}'),
    ('<i class="bi bi-award-fill text-warning me-1"></i> Hồ sơ & Kỹ năng của tôi',
     '<i class="bi bi-award-fill text-warning me-1"></i> {{ _(\'Hồ sơ & Kỹ năng của tôi\') }}'),
    ('<i class="bi bi-shop me-1"></i> Kho nội trường',
     '<i class="bi bi-shop me-1"></i> {{ _(\'Kho nội trường\') }}'),
    ('placeholder="Tìm kiếm kỹ năng, môn học, trường..."',
     'placeholder="{{ _(\'Tìm kiếm kỹ năng, môn học, trường...\') }}"'),
    ('<option value="">-- Tất cả trường học --</option>',
     '<option value="">-- {{ _(\'Tất cả trường học\') }} --</option>'),
    ('<option value="">-- Lĩnh vực --</option>',
     '<option value="">-- {{ _(\'Lĩnh vực\') }} --</option>'),
    ('title="Lọc dữ liệu"', 'title="{{ _(\'Lọc dữ liệu\') }}"'),
    ('title="Xóa bộ lọc"', 'title="{{ _(\'Xóa bộ lọc\') }}"'),
    ('<i class="bi bi-award-fill text-warning me-1"></i>Liên trường',
     '<i class="bi bi-award-fill text-warning me-1"></i>{{ _(\'Liên trường\') }}'),
    ('<small class="text-muted d-block" style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;">Trường học</small>',
     '<small class="text-muted d-block" style="font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.5px;">{{ _(\'Trường học\') }}</small>'),
    ('<div class="text-muted" style="font-size: 0.75rem;">Lớp: {{ skill.lop }} • Mã: <code>{{ skill.ma_hoc_sinh }}</code></div>',
     '<div class="text-muted" style="font-size: 0.75rem;">{{ _(\'Lớp:\') }} {{ skill.lop }} • {{ _(\'Mã:\') }} <code>{{ skill.ma_hoc_sinh }}</code></div>'),
    ('<span class="text-muted">Đánh giá uy tín:</span>',
     '<span class="text-muted">{{ _(\'Đánh giá uy tín:\') }}</span>'),
    ('<i class="bi bi-person-check me-1"></i> Kỹ năng của bạn',
     '<i class="bi bi-person-check me-1"></i> {{ _(\'Kỹ năng của bạn\') }}'),
    ('<i class="bi bi-calendar-plus me-1"></i> Đặt lịch học liên trường',
     '<i class="bi bi-calendar-plus me-1"></i> {{ _(\'Đặt lịch học liên trường\') }}'),
    ('<h4 class="fw-bold text-dark">Chưa có kỹ năng nào trên Cộng đồng liên trường</h4>',
     '<h4 class="fw-bold text-dark">{{ _(\'Chưa có kỹ năng nào trên Cộng đồng liên trường\') }}</h4>'),
    ('Các kỹ năng đang chờ học sinh ưu tú đăng ký và Ban quản trị nhà trường phê duyệt.',
     '{{ _(\'Các kỹ năng đang chờ học sinh ưu tú đăng ký và Ban quản trị nhà trường phê duyệt.\') }}'),
    ('<i class="bi bi-shop me-1"></i> Khám phá Kho kỹ năng nội trường',
     '<i class="bi bi-shop me-1"></i> {{ _(\'Khám phá Kho kỹ năng nội trường\') }}'),
]

for s, d in replacements:
    content = content.replace(s, d)

with open('templates/community_market.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("community_market.html updated.")
