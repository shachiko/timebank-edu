with open('templates/forum_index.html', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ("{% block title %}Diễn đàn Học đường - Góc Trò Chuyện - School Time Bank{% endblock %}",
     "{% block title %}{{ _('Diễn đàn Học đường - Góc Trò Chuyện - School Time Bank') }}{% endblock %}"),
    ('<i class="bi bi-chat-quote-fill me-1"></i> GÓC TRÒ CHUYỆN HỌC ĐƯỜNG',
     '<i class="bi bi-chat-quote-fill me-1"></i> {{ _(\'GÓC TRÒ CHUYỆN HỌC ĐƯỜNG\') }}'),
    ('<h2 class="display-6 fw-bold text-dark mb-2">Diễn Đàn Trao Đổi & Kết Nối Tri Thức</h2>',
     '<h2 class="display-6 fw-bold text-dark mb-2">{{ _(\'Diễn Đàn Trao Đổi & Kết Nối Tri Thức\') }}</h2>'),
    ('Không gian thảo luận tích cực, giải đáp thắc mắc học tập và sẻ chia kinh nghiệm giữa các bạn học sinh.',
     '{{ _(\'Không gian thảo luận tích cực, giải đáp thắc mắc học tập và sẻ chia kinh nghiệm giữa các bạn học sinh.\') }}'),
    ('Mọi nội dung đều được kiểm duyệt văn hóa sư phạm theo 6 Điều Quy tắc Vàng.',
     '{{ _(\'Mọi nội dung đều được kiểm duyệt văn hóa sư phạm theo 6 Điều Quy tắc Vàng.\') }}'),
    ('<i class="bi bi-plus-circle me-1"></i> Tạo chủ đề mới',
     '<i class="bi bi-plus-circle me-1"></i> {{ _(\'Tạo chủ đề mới\') }}'),
    ('<i class="bi bi-shield-check me-1"></i> Xem nội quy trao đổi',
     '<i class="bi bi-shield-check me-1"></i> {{ _(\'Xem nội quy trao đổi\') }}'),
    ('placeholder="Tìm kiếm chủ đề, câu hỏi, kiến thức..."',
     'placeholder="{{ _(\'Tìm kiếm chủ đề, câu hỏi, kiến thức...\') }}"'),
    ('<i class="bi bi-filter me-1"></i> Tìm kiếm',
     '<i class="bi bi-filter me-1"></i> {{ _(\'Tìm kiếm\') }}'),
    ('>Xóa lọc</a>',
     '>{{ _(\'Xóa lọc\') }}</a>'),
    ('<i class="bi bi-chat-dots me-1"></i>Đang mở',
     '<i class="bi bi-chat-dots me-1"></i>{{ _(\'Đang mở\') }}'),
    ('<i class="bi bi-lock-fill me-1"></i>Đã khóa',
     '<i class="bi bi-lock-fill me-1"></i>{{ _(\'Đã khóa\') }}'),
    ('<i class="bi bi-lock-fill text-warning me-2"></i>Khóa chủ đề',
     '<i class="bi bi-lock-fill text-warning me-2"></i>{{ _(\'Khóa chủ đề\') }}'),
    ('<i class="bi bi-unlock-fill text-success me-2"></i>Mở khóa chủ đề',
     '<i class="bi bi-unlock-fill text-success me-2"></i>{{ _(\'Mở khóa chủ đề\') }}'),
    ('onsubmit="return confirm(\'Bạn có chắc chắn muốn xóa chủ đề này không?\');"',
     'onsubmit="return confirm(\'{{ _(\'Bạn có chắc chắn muốn xóa chủ đề này không?\') }}\');"'),
    ('<i class="bi bi-trash3-fill me-2"></i>Xóa chủ đề',
     '<i class="bi bi-trash3-fill me-2"></i>{{ _(\'Xóa chủ đề\') }}'),
    ('{{ t.reply_count }} phản hồi',
     '{{ t.reply_count }} {{ _(\'phản hồi\') }}'),
    ('Xem chi tiết <i class="bi bi-arrow-right ms-1"></i>',
     '{{ _(\'Xem chi tiết\') }} <i class="bi bi-arrow-right ms-1"></i>'),
    ('<h5 class="fw-bold text-dark mb-1">Chưa có chủ đề nào được đăng tải</h5>',
     '<h5 class="fw-bold text-dark mb-1">{{ _(\'Chưa có chủ đề nào được đăng tải\') }}</h5>'),
    ('Hãy là người đầu tiên khơi nguồn cuộc thảo luận bổ ích cho học sinh trường bạn!',
     '{{ _(\'Hãy là người đầu tiên khơi nguồn cuộc thảo luận bổ ích cho học sinh trường bạn!\') }}'),
    ('<i class="bi bi-plus-circle me-1"></i> Tạo chủ đề ngay',
     '<i class="bi bi-plus-circle me-1"></i> {{ _(\'Tạo chủ đề ngay\') }}'),
]

for s, d in replacements:
    content = content.replace(s, d)

with open('templates/forum_index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("forum_index.html updated.")
