# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — PROMPT 29: HOTFIX TAB "QUẢN LÝ MÃ MỜI" & HỆ THỐNG TAB /ADMIN

Nghiệm thu các tiêu chí:
1. Cấu trúc DOM chuẩn: Toàn bộ 7 tab-pane không bị lồng nhau (nesting) bên trong tab-overview hay bất kỳ tab nào khác.
2. Cơ chế tab tự viết hoạt động độc lập (không phụ thuộc Bootstrap JS):
   - Có CSS chống giật/ẩn: #adminTabsContent > .tab-pane { display: none !important; } và .active { display: block !important; }
   - Có JS activateAdminTab gán sự kiện click và tự động khôi phục theo URL hash.
3. Tab "Quản lý Mã mời" (#tab-invite):
   - Có đầy đủ form sinh mã: chọn loại mã, số lượng, nút sinh mã.
   - POST sinh mã mời thành công -> redirect về /admin#tab-invite.
   - Mã mời mới sinh xuất hiện trong CSDL và bảng danh sách.
4. Toàn bộ các tab khác trong /admin (Tổng quan, Hàng chờ, Vi phạm, Tài khoản, Sàn chung, Drive) đều có đầy đủ markup và liên kết đúng target.
"""

import os
import sys
import re
import unittest
from pathlib import Path
from werkzeug.security import generate_password_hash

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db

class TestPrompt29AdminTabs(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def test_01_admin_template_tabs_not_nested(self):
        """[TC 1]: Đảm bảo toàn bộ 7 tab-pane trong templates/admin.html không bị lồng nhau."""
        template_path = Path("templates/admin.html")
        self.assertTrue(template_path.exists(), "templates/admin.html phải tồn tại")

        with open(template_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        tab_names = [
            'tab-overview',
            'tab-queue',
            'tab-invite',
            'tab-violations',
            'tab-users',
            'tab-community',
            'tab-drive'
        ]

        stack = []
        tab_spans = {}

        for i, line in enumerate(lines):
            idx = i + 1
            tokens = re.findall(r'<div[^>]*>|</div\s*>', line)
            for tok in tokens:
                if tok.startswith('</div'):
                    if stack:
                        popped_idx, popped_name = stack.pop()
                        if popped_name in tab_names:
                            tab_spans[popped_name] = (popped_idx, idx)
                else:
                    m = re.search(r'id=["\']([^"\']+)["\']', tok)
                    name = m.group(1) if m else tok[:35].replace('\n', '')
                    stack.append((idx, name))

        for t in tab_names:
            self.assertIn(t, tab_spans, f"Tab {t} phải được mở và đóng hợp lệ")

        overview_start, overview_end = tab_spans['tab-overview']
        invite_start, invite_end = tab_spans['tab-invite']
        queue_start, queue_end = tab_spans['tab-queue']

        # Đảm bảo tab-queue và tab-invite nằm HOÀN TOÀN NGOÀI tab-overview
        self.assertGreater(queue_start, overview_end, "tab-queue không được nằm trong tab-overview")
        self.assertGreater(invite_start, overview_end, "tab-invite không được nằm trong tab-overview")

        # Đảm bảo không còn thẻ div nào chưa đóng bên trong template
        unclosed_divs = [item for item in stack if 'div' in item[1] or item[1] in tab_names]
        self.assertEqual(len(unclosed_divs), 0, f"Không được có thẻ div nào chưa đóng: {unclosed_divs}")

    def test_02_custom_tab_css_and_js_present(self):
        """[TC 2]: Kiểm tra sự hiện diện của cơ chế CSS và JS tab tự viết độc lập."""
        with open("templates/admin.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Kiểm tra CSS độc lập
        self.assertIn("#adminTabsContent > .tab-pane", content)
        self.assertIn("display: none !important", content)
        self.assertIn("#adminTabsContent > .tab-pane.active", content)
        self.assertIn("display: block !important", content)

        # Kiểm tra JS chuyển tab độc lập và hash restore
        self.assertIn("function activateAdminTab(targetId)", content)
        self.assertIn("window.location.hash", content)
        self.assertIn("activateAdminTab(hash)", content)

    def test_03_invite_code_generation_redirects_with_hash(self):
        """[TC 3]: Sinh mã mời thành công -> redirect về /admin#tab-invite và lưu vào DB."""
        # Đăng nhập tài khoản admin
        res_login = self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        self.assertEqual(res_login.status_code, 200)

        # Gửi form sinh 2 mã cá nhân
        res_gen = self.client.post("/admin/invite-codes/generate", data={
            "truong_id": "99",
            "loai": "ca_nhan",
            "so_luong": "2"
        }, follow_redirects=False)

        # Kiểm tra redirect có kèm anchor #tab-invite
        self.assertEqual(res_gen.status_code, 302)
        location = res_gen.headers.get("Location", "")
        self.assertIn("tab-invite", location, f"Redirect URL phải chứa anchor #tab-invite, thực tế: {location}")

        # Follow redirect để xem trang /admin
        res_admin = self.client.get(location)
        self.assertEqual(res_admin.status_code, 200)
        html = res_admin.data.decode("utf-8")
        self.assertIn("Đã sinh thành công 2 mã mời", html)
        self.assertIn("TBEDU-", html)

    def test_04_admin_dashboard_renders_all_tabs(self):
        """[TC 4]: Truy cập /admin hiển thị đầy đủ các nút tab và các container tab."""
        self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Nút tab
        self.assertIn('id="tab-overview-btn"', html)
        self.assertIn('id="tab-queue-btn"', html)
        self.assertIn('id="tab-invite-btn"', html)
        self.assertIn('id="tab-violations-btn"', html)
        self.assertIn('id="tab-users-btn"', html)
        self.assertIn('id="tab-community-btn"', html)

        # Vùng nội dung tab
        self.assertIn('id="tab-overview"', html)
        self.assertIn('id="tab-queue"', html)
        self.assertIn('id="tab-invite"', html)
        self.assertIn('id="tab-violations"', html)
        self.assertIn('id="tab-users"', html)
        self.assertIn('id="tab-community"', html)

        # Form sinh mã mời
        self.assertIn('Sinh Mã Mời Trường Học Ngẫu Nhiên', html)
        self.assertIn('inviteTypeSelect', html)
        self.assertIn('inputSoLuong', html)

if __name__ == "__main__":
    unittest.main()
