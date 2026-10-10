import os
import re

def replace_in_file(path, replacements):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
        else:
            print(f"[{path}] Not found: {old[:50]}")
    if content != orig:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Patched {path}")
    else:
        print(f"No changes in {path}")

# 1. admin_drive_token_display.html
replace_in_file('templates/admin_drive_token_display.html', [
    ('btnText.textContent = "Đã sao chép vào bộ nhớ tạm! ✓";', 'btnText.textContent = "{{ _(\'Đã sao chép vào bộ nhớ tạm! ✓\') }}";'),
    ('btnText.textContent = "Sao chép Token đầy đủ";', 'btnText.textContent = "{{ _(\'Sao chép Token đầy đủ\') }}";')
])

# 2. blog_list.html
replace_in_file('templates/blog_list.html', [
    ('Nơi lan tỏa các câu chuyện tương trợ tri thức, vinh danh gia sư tiêu biểu và cập nhật nhịp đập hoạt động tại {{ config.ten_truong }}.',
     '{{ _(\'Nơi lan tỏa các câu chuyện tương trợ tri thức, vinh danh gia sư tiêu biểu và cập nhật nhịp đập hoạt động tại %(ten_truong)s.\', ten_truong=config.ten_truong) }}')
])

# 3. book_session_page.html
replace_in_file('templates/book_session_page.html', [
    ("{{ skill.gio_ranh if skill.gio_ranh else 'Linh hoạt' }}",
     "{{ skill.gio_ranh if skill.gio_ranh else _('Linh hoạt') }}"),
    ('<strong class="text-primary fs-5">{{ "%.1f"|format(current_user.so_du_gio) }} giờ</strong>',
     '<strong class="text-primary fs-5">{{ "%.1f"|format(current_user.so_du_gio) }} {{ _(\'giờ\') }}</strong>')
])

# 4. community.html
replace_in_file('templates/community.html', [
    ('Mở rộng mô hình ngân hàng thời gian: Tham gia dọn dẹp bãi biển, hỗ trợ số hóa sách thư viện,',
     '{{ _(\'Mở rộng mô hình ngân hàng thời gian: Tham gia dọn dẹp bãi biển, hỗ trợ số hóa sách thư viện,\') }}'),
    ('dạy tin học cho đàn em... để nhận thêm tín dụng thời gian vào ví học tập!',
     '{{ _(\'dạy tin học cho đàn em... để nhận thêm tín dụng thời gian vào ví học tập!\') }}')
])

# 5. community_attendance.html
replace_in_file('templates/community_attendance.html', [
    ('<i class="bi bi-gift-fill me-1"></i>Thưởng +{{ "%.1f"|format(task.so_gio_thuong) }} giờ / bạn',
     '<i class="bi bi-gift-fill me-1"></i>{{ _(\'Thưởng\') }} +{{ "%.1f"|format(task.so_gio_thuong) }} {{ _(\'giờ / bạn\') }}'),
    ('Trạng thái: {{ task.trang_thai }}',
     '{{ _(\'Trạng thái:\') }} {{ task.trang_thai }}'),
    ('{{ task.so_luong_toi_da }} bạn</strong>',
     '{{ task.so_luong_toi_da }} {{ _(\'bạn\') }}</strong>'),
    ('<i class="bi bi-card-checklist text-primary me-2"></i>Danh sách học sinh đăng ký tham gia ({{ registrations|length }})',
     '<i class="bi bi-card-checklist text-primary me-2"></i>{{ _(\'Danh sách học sinh đăng ký tham gia\') }} ({{ registrations|length }})'),
    ('Đã hoàn thành (+{{ "%.1f"|format(task.so_gio_thuong) }}h)',
     '{{ _(\'Đã hoàn thành\') }} (+{{ "%.1f"|format(task.so_gio_thuong) }}h)')
])

# 6. community_market_gate.html
replace_in_file('templates/community_market_gate.html', [
    ('{{ teaching_hours_display }} / {{ threshold_display }} giờ dạy',
     '{{ teaching_hours_display }} / {{ threshold_display }} {{ _(\'giờ dạy\') }}'),
    ('<span>Ngưỡng mở khóa: {{ threshold_display }}h dạy thật</span>',
     '<span>{{ _(\'Ngưỡng mở khóa:\') }} {{ threshold_display }}h {{ _(\'dạy thật\') }}</span>')
])

# 7. documents_upload.html
replace_in_file('templates/documents_upload.html', [
    ("totalBadge.textContent = 'Tổng: ' + formatFileSize(totalBytes);",
     "totalBadge.textContent = '{{ _(\'Tổng:\') }} ' + formatFileSize(totalBytes);"),
    ("notice.textContent = `Hợp lệ (${files.length} tệp)`;",
     "notice.textContent = '{{ _(\'Hợp lệ\') }} (' + files.length + ' {{ _(\'tệp\') }})';"),
    ("submitBtn.innerHTML = '<span class=\"spinner-border spinner-border-sm me-2\" role=\"status\" aria-hidden=\"true\"></span>Đang tải tệp lên hệ thống...';",
     "submitBtn.innerHTML = '<span class=\"spinner-border spinner-border-sm me-2\" role=\"status\" aria-hidden=\"true\"></span>' + '{{ _(\'Đang tải tệp lên hệ thống...\') }}';")
])

# 8. forum_topic.html
replace_in_file('templates/forum_topic.html', [
    ('{% block title %}{{ topic.tieu_de }} - Diễn đàn School Time Bank{% endblock %}',
     '{% block title %}{{ topic.tieu_de }} - {{ _(\'Diễn đàn School Time Bank\') }}{% endblock %}'),
    ('<i class="bi bi-lock-fill text-warning me-2"></i>Khóa chủ đề',
     '<i class="bi bi-lock-fill text-warning me-2"></i>{{ _(\'Khóa chủ đề\') }}'),
    ('<i class="bi bi-unlock-fill text-success me-2"></i>Mở khóa chủ đề',
     '<i class="bi bi-unlock-fill text-success me-2"></i>{{ _(\'Mở khóa chủ đề\') }}'),
    ('<i class="bi bi-chat-square-text-fill text-primary me-2"></i>Ý kiến thảo luận ({{ replies|length }})',
     '<i class="bi bi-chat-square-text-fill text-primary me-2"></i>{{ _(\'Ý kiến thảo luận\') }} ({{ replies|length }})')
])

# 9. my_schedule.html
replace_in_file('templates/my_schedule.html', [
    ('(Mã: <code>{{ user.ma_hoc_sinh }}</code>',
     '({{ _(\'Mã:\') }} <code>{{ user.ma_hoc_sinh }}</code>'),
    ('{{ "%.1f"|format(user.so_du_gio) }} giờ</strong>',
     '{{ "%.1f"|format(user.so_du_gio) }} {{ _(\'giờ\') }}</strong>')
])

# 10. profile.html
replace_in_file('templates/profile.html', [
    ("match.gio_ranh if match.gio_ranh else 'Linh hoạt'",
     "match.gio_ranh if match.gio_ranh else _('Linh hoạt')")
])

# 11. session_quiz.html
replace_in_file('templates/session_quiz.html', [
    ('(Lớp {{ session_data.lop_nguoi_day }})',
     '({{ _(\'Lớp\') }} {{ session_data.lop_nguoi_day }})'),
    ('(Lớp {{ session_data.lop_nguoi_hoc }})',
     '({{ _(\'Lớp\') }} {{ session_data.lop_nguoi_hoc }})'),
    ('{{ "%.1f"|format(session_data.so_gio) }} giờ</strong>',
     '{{ "%.1f"|format(session_data.so_gio) }} {{ _(\'giờ\') }}</strong>'),
    ('Câu {{ loop.index }} / {{ questions|length }}',
     '{{ _(\'Câu\') }} {{ loop.index }} / {{ questions|length }}'),
    ('Đáp án đúng: {{ q.dap_an_dung }}',
     '{{ _(\'Đáp án đúng:\') }} {{ q.dap_an_dung }}'),
    ('>Câu {{ loop.index }}</span>',
     '>{{ _(\'Câu\') }} {{ loop.index }}</span>'),
    ('Bộ Quiz gồm {{ questions|length }} câu hỏi do AI biên soạn đã sẵn sàng',
     '{{ _(\'Bộ Quiz gồm %(count)s câu hỏi do AI biên soạn đã sẵn sàng\', count=questions|length) }}')
])

# 12. skills_approval.html
replace_in_file('templates/skills_approval.html', [
    ('Tổng số: {{ skills|length }}',
     '{{ _(\'Tổng số:\') }} {{ skills|length }}'),
    ('• Lớp: {{ item.lop }}',
     '• {{ _(\'Lớp:\') }} {{ item.lop }}')
])

# 13. skills_new.html
replace_in_file('templates/skills_new.html', [
    ('— 1 giờ bạn dạy = 1 tín dụng nhận về',
     '— {{ _(\'1 giờ bạn dạy = 1 tín dụng nhận về\') }}')
])

# 14. virtual_rooms_dashboard.html
replace_in_file('templates/virtual_rooms_dashboard.html', [
    ('{{ live_rooms|length }} lớp</span>',
     '{{ live_rooms|length }} {{ _(\'lớp\') }}</span>'),
    ('<small class="text-muted">Lớp {{ s.lop_nguoi_day }}</small>',
     '<small class="text-muted">{{ _(\'Lớp\') }} {{ s.lop_nguoi_day }}</small>'),
    ('<small class="text-muted">Lớp {{ s.lop_nguoi_hoc }}</small>',
     '<small class="text-muted">{{ _(\'Lớp\') }} {{ s.lop_nguoi_hoc }}</small>'),
    ('{{ verification_rooms|length }} phiên</span>',
     '{{ verification_rooms|length }} {{ _(\'phiên\') }}</span>')
])

# 15. wallet.html
replace_in_file('templates/wallet.html', [
    ('(Mã: <code>{{ user.ma_hoc_sinh }}</code>)',
     '({{ _(\'Mã:\') }} <code>{{ user.ma_hoc_sinh }}</code>)'),
    ('<strong>{{ "%.1f"|format(user.so_du_gio) }} giờ</strong>',
     '<strong>{{ "%.1f"|format(user.so_du_gio) }} {{ _(\'giờ\') }}</strong>')
])

# 16. virtual_room.html
replace_in_file('templates/virtual_room.html', [
    ('DEFAULT_REMOTE_DISPLAY_NAME: "Thành viên TimeBank"',
     'DEFAULT_REMOTE_DISPLAY_NAME: "{{ _(\'Thành viên TimeBank\') }}"'),
    ('switchToJaaS("Lỗi phòng học Daily.co (" + (e.errorMsg || "mất kết nối") + "). Tự động chuyển nòng dự phòng...");',
     'switchToJaaS("{{ _(\'Lỗi phòng học Daily.co\') }} (" + (e.errorMsg || "{{ _(\'mất kết nối\') }}") + "). {{ _(\'Tự động chuyển nòng dự phòng...\') }}");'),
    ('switchToJaaS("Lỗi khởi tạo Daily.co: " + e.message + ". Tự động chuyển nòng dự phòng...");',
     'switchToJaaS("{{ _(\'Lỗi khởi tạo Daily.co:\') }} " + e.message + ". {{ _(\'Tự động chuyển nòng dự phòng...\') }}");'),
    ('switchToJaaS("Không thể tải thư viện Daily.co qua CDN. Tự động chuyển nòng dự phòng...");',
     'switchToJaaS("{{ _(\'Không thể tải thư viện Daily.co qua CDN. Tự động chuyển nòng dự phòng...\') }}");'),
    ('switchToJaaS("Lỗi mạng Daily.co: " + err.message + ". Tự động chuyển nòng dự phòng...");',
     'switchToJaaS("{{ _(\'Lỗi mạng Daily.co:\') }} " + err.message + ". {{ _(\'Tự động chuyển nòng dự phòng...\') }}");'),
    ('window.switchToPublicJitsi("Không thể cấp token lớp học (" + (result.data.error || "lỗi cấu hình") + "). Tự động chuyển nòng dự phòng (Jitsi)...");',
     'window.switchToPublicJitsi("{{ _(\'Không thể cấp token lớp học\') }} (" + (result.data.error || "{{ _(\'lỗi cấu hình\') }}") + "). {{ _(\'Tự động chuyển nòng dự phòng (Jitsi)...\') }}");'),
    ('window.switchToPublicJitsi("Không thể nạp thư viện kết nối lớp học. Chuyển nòng dự phòng (Jitsi)...");',
     'window.switchToPublicJitsi("{{ _(\'Không thể nạp thư viện kết nối lớp học. Chuyển nòng dự phòng (Jitsi)...\') }}");'),
    ('window.switchToPublicJitsi("Không thể khởi tạo lớp học: " + e.message + ". Chuyển nòng dự phòng (Jitsi)...");',
     'window.switchToPublicJitsi("{{ _(\'Không thể khởi tạo lớp học:\') }} " + e.message + ". {{ _(\'Chuyển nòng dự phòng (Jitsi)...\') }}");'),
    ('window.switchToPublicJitsi("Không thể tải thư viện lớp học ảo. Chuyển nòng dự phòng (Jitsi)...");',
     'window.switchToPublicJitsi("{{ _(\'Không thể tải thư viện lớp học ảo. Chuyển nòng dự phòng (Jitsi)...\') }}");'),
    ('window.switchToPublicJitsi("Lỗi kết nối lớp học: " + err.message + ". Chuyển nòng dự phòng (Jitsi)...");',
     'window.switchToPublicJitsi("{{ _(\'Lỗi kết nối lớp học:\') }} " + err.message + ". {{ _(\'Chuyển nòng dự phòng (Jitsi)...\') }}");')
])

print("Finished patch_remaining_templates.py")
