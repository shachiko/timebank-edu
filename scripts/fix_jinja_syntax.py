import os

def fix_file(filepath, replacements):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    orig = content
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
        else:
            print(f"[{filepath}] Not found: {old}")
    if content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {filepath}")
    else:
        print(f"No changes in {filepath}")

# 1. admin.html
fix_file('templates/admin.html', [
    ("lbl.textContent = '{{ _(\\'Số lượng mã lớp\\') }}';", 'lbl.textContent = "{{ _(\'Số lượng mã lớp\') }}";'),
    ("lbl.textContent = '{{ _(\\'Số lượng mã cá nhân\\') }}';", 'lbl.textContent = "{{ _(\'Số lượng mã cá nhân\') }}";')
])

# 2. community.html
fix_file('templates/community.html', [
    ("{{ task.dia_diem or '_('Trong khuôn viên trường') }}", "{{ task.dia_diem or _('Trong khuôn viên trường') }}")
])

# 3. community_attendance.html
fix_file('templates/community_attendance.html', [
    ("{{ task.dia_diem or '_('Tại trường') }}", "{{ task.dia_diem or _('Tại trường') }}")
])

# 4. documents_index.html
fix_file('templates/documents_index.html', [
    ('{{ doc.mo_ta or "_(\'Không có mô tả chi tiết.\') }}', '{{ doc.mo_ta or _(\'Không có mô tả chi tiết.\') }}')
])
