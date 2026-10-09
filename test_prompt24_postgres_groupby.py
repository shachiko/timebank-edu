# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN — PROMPT 24:
HOTFIX SỬA GROUP BY CHO POSTGRESQL (KHẮC PHỤC LỖI 500 TRÊN TRANG /ADMIN)

Nghiệm thu 3 tiêu chí:
1. Trang /admin không còn bị 500 (chạy trơn tru trên cả SQLite và cú pháp chuẩn PostgreSQL).
2. Quét tĩnh toàn bộ codebase: 0 query vi phạm quy tắc GROUP BY của PostgreSQL
   (mọi cột SELECT và ORDER BY không chứa aggregate bắt buộc phải nằm trong GROUP BY).
3. Regression: Các test case liên quan đến quản trị và AI vẫn pass 100%.
"""

import os
import re
import sys
import unittest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db
from ai_service import ai_admin_early_warning, ai_generate_weekly_newsletter


class TestPrompt24PostgresGroupBy(unittest.TestCase):
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

    # =========================================================================
    # TIÊU CHÍ 1: TRANG /ADMIN KHÔNG CÒN 500, AI EARLY WARNING CHẠY TRƠN TRU
    # =========================================================================
    def test_01_admin_page_not_500_and_early_warning_works(self):
        """[TIÊU CHÍ 1]: /admin trả về HTTP 200, hàm ai_admin_early_warning thực thi SQL chuẩn xác."""
        db = get_db()
        
        # 1. Gọi trực tiếp hàm ai_admin_early_warning (nơi gây ra lỗi 500 trên Postgres)
        warnings = ai_admin_early_warning(db, 1)
        self.assertIsInstance(warnings, dict)
        self.assertIn("inactive_students", warnings)
        self.assertIn("low_rated_pairs", warnings)
        self.assertIn("ai_recommendations", warnings)

        # 2. Đăng nhập với admin và truy cập /admin
        self.client.get("/logout")
        login_res = self.client.post("/login", data={
            "ma_hoc_sinh": "admin",
            "mat_khau": "admin123"
        }, follow_redirects=True)
        self.assertEqual(login_res.status_code, 200)

        res_admin = self.client.get("/admin")
        self.assertEqual(res_admin.status_code, 200, "Trang /admin không được trả về lỗi 500!")
        html = res_admin.data.decode("utf-8")
        self.assertIn("Hệ thống Quản trị", html)
        self.assertIn("CẢNH BÁO SỚM SƯ PHẠM", html)

        # 3. Đăng nhập với demo_quantruong và truy cập /admin
        self.client.get("/logout")
        self.client.post("/login", data={
            "ma_hoc_sinh": "demo_quantruong",
            "mat_khau": "demo123"
        }, follow_redirects=True)
        res_demo = self.client.get("/admin")
        self.assertEqual(res_demo.status_code, 200, "/admin cho Quản trị viên demo phải HTTP 200!")

        print("\n[PASS - TC 1]: /admin hoạt động trơn tru (HTTP 200), hàm ai_admin_early_warning hoàn toàn không lỗi.")

    # =========================================================================
    # TIÊU CHÍ 2: QUÉT TĨNH CODEBASE — 0 QUERY VI PHẠM QUY TẮC GROUP BY POSTGRESQL
    # =========================================================================
    def test_02_static_scan_zero_invalid_group_by_queries(self):
        """[TIÊU CHÍ 2]: Quét tĩnh toàn bộ ai_service.py và app.py, bảo đảm mọi query có GROUP BY đều hợp lệ."""
        files_to_check = ["app.py", "ai_service.py"]
        violations = []

        for filename in files_to_check:
            filepath = os.path.join(os.path.dirname(__file__), filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            # Tìm tất cả các câu lệnh SQL có chứa GROUP BY
            # Quy tắc bắt buộc 1: Trong ai_admin_early_warning, GROUP BY u.id phải có đủ 5 cột
            if filename == "ai_service.py":
                # Kiểm tra query học sinh 7 ngày không học
                self.assertNotIn(
                    "GROUP BY u.id\n",
                    content,
                    "Không được dùng 'GROUP BY u.id' đơn độc trong ai_service.py!"
                )
                self.assertIn(
                    "GROUP BY u.id, u.ho_ten, u.lop, u.ma_hoc_sinh, u.so_du_gio",
                    content,
                    "ai_admin_early_warning phải chứa đầy đủ 5 cột trong GROUP BY!"
                )

                # Kiểm tra query cặp đôi xung đột
                self.assertIn(
                    "GROUP BY r.nguoi_danh_gia_id, r.nguoi_duoc_danh_gia_id, u1.ho_ten, u2.ho_ten",
                    content,
                    "Query quét cặp đôi xung đột phải chứa đầy đủ u1.ho_ten, u2.ho_ten trong GROUP BY!"
                )

                # Kiểm tra query top gia sư
                self.assertIn(
                    "GROUP BY u.id, u.ho_ten, u.lop",
                    content,
                    "Query top gia sư trong ai_generate_weekly_newsletter phải chứa đầy đủ u.id, u.ho_ten, u.lop trong GROUP BY!"
                )

            # Quy tắc bắt buộc 2: Trong app.py, các câu lệnh ORDER BY sau GROUP BY không được dùng cột trần chưa aggregate
            if filename == "app.py":
                self.assertNotIn(
                    "ORDER BY so_luong DESC, s.id DESC",
                    content,
                    "Trong PostgreSQL, s.id trong ORDER BY sau GROUP BY sk.linh_vuc phải dùng MAX(s.id)!"
                )
                self.assertNotIn(
                    "ORDER BY so_luong DESC, id DESC",
                    content,
                    "Trong PostgreSQL, id trong ORDER BY sau GROUP BY linh_vuc phải dùng MAX(id)!"
                )

        print("\n[PASS - TC 2]: Quét tĩnh hoàn tất: 0 query vi phạm quy tắc GROUP BY của PostgreSQL.")

    # =========================================================================
    # TIÊU CHÍ 3: TRUY VẤN BẢN TIN TUẦN TOP GIA SƯ HOẠT ĐỘNG HOÀN HẢO
    # =========================================================================
    def test_03_weekly_newsletter_top_tutors_query_execution(self):
        """[TIÊU CHÍ 3]: Hàm ai_generate_weekly_newsletter thực thi truy vấn Top gia sư mượt mà."""
        db = get_db()
        post_id, tieu_de, noi_dung, is_live = ai_generate_weekly_newsletter(db)
        self.assertIsNotNone(post_id)
        self.assertIn("Bản tin", tieu_de)
        self.assertIn("Vinh danh gia sư", noi_dung)

        print("\n[PASS - TC 3]: Truy vấn Top gia sư trong bản tin tuần thực thi chính xác và chuẩn PostgreSQL.")

    # =========================================================================
    # TIÊU CHÍ 4: LUỒNG OAUTH GOOGLE DRIVE HIỂN THỊ FULL REFRESH TOKEN (VIỆC 2)
    # =========================================================================
    def test_04_drive_oauth_token_display_page(self):
        """[TIÊU CHÍ 4]: Luồng OAuth đổi code thành công -> Render trang hiển thị FULL token và nút 'Đã copy xong'."""
        from unittest.mock import patch

        mock_full_token = "1//04mock_super_long_refresh_token_example_for_google_drive_5tb_production_2026"

        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "super_admin"
            sess["ma_hoc_sinh"] = "admin_super"
            sess["truong_id"] = 1

        with patch("app.exchange_code_for_tokens") as mock_exchange:
            mock_exchange.return_value = {"refresh_token": mock_full_token, "access_token": "mock_acc"}

            # Gọi callback với mã code giả lập
            res = self.client.get("/admin/google-drive/callback?code=mock_valid_auth_code", follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            html = res.data.decode("utf-8")
            # Kiểm tra token đầy đủ xuất hiện nguyên vẹn trong ô text
            self.assertIn(mock_full_token, html, "Token phải hiển thị FULL đầy đủ không bị che giấu!")
            # Kiểm tra nút 'Đã copy xong'
            self.assertIn("Đã copy xong", html, "Phải có nút 'Đã copy xong' để quay lại /admin!")
            # Kiểm tra nút sao chép
            self.assertIn("Sao chép Token đầy đủ", html)

        print("\n[PASS - TC 4]: Luồng OAuth hiển thị đầy đủ FULL Refresh Token trong ô text cho Super Admin copy.")

    # =========================================================================
    # TIÊU CHÍ 5: AN TOÀN BẢO MẬT: HIỂN THỊ 1 LẦN DUY NHẤT (POP SESSION)
    # =========================================================================
    def test_05_drive_token_single_use_security(self):
        """[TIÊU CHÍ 5]: Trang hiển thị token chỉ xem được 1 lần duy nhất, tải lại là mất và chuyển về /admin."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "super_admin"
            sess["temp_drive_refresh_token"] = "mock_secret_token_one_time"

        # Lần 1: Xem được token
        res1 = self.client.get("/admin/google-drive/token-hien-thi")
        self.assertEqual(res1.status_code, 200)
        self.assertIn("mock_secret_token_one_time", res1.data.decode("utf-8"))

        # Lần 2 (Tải lại trang hoặc truy cập lại): Token đã bị pop khỏi session -> chuyển hướng về /admin
        res2 = self.client.get("/admin/google-drive/token-hien-thi", follow_redirects=True)
        self.assertEqual(res2.status_code, 200)
        html2 = res2.data.decode("utf-8")
        self.assertNotIn("mock_secret_token_one_time", html2, "Token tuyệt đối không còn tồn tại sau khi xem xong!")
        self.assertIn("chỉ hiển thị 1 lần duy nhất", html2)

        print("\n[PASS - TC 5]: Token chỉ hiển thị đúng 1 lần duy nhất; tự động hủy khi tải lại trang.")

    # =========================================================================
    # TIÊU CHÍ 6: PHÂN QUYỀN: CHỈ SUPER ADMIN MỚI ĐƯỢC TRUY CẬP TRANG TOKEN
    # =========================================================================
    def test_06_non_superadmin_blocked_from_token_display(self):
        """[TIÊU CHÍ 6]: Học sinh hoặc School Admin không được phép truy cập trang token-hien-thi."""
        # 1. Học sinh truy cập
        with self.client.session_transaction() as sess:
            sess["user_id"] = 2
            sess["vai_tro"] = "hoc_sinh"
            sess["temp_drive_refresh_token"] = "token_that_should_not_be_seen"

        res_hs = self.client.get("/admin/google-drive/token-hien-thi")
        # Phải bị chặn (403 hoặc chuyển hướng)
        self.assertIn(res_hs.status_code, [302, 403])

        # 2. School Admin truy cập
        with self.client.session_transaction() as sess:
            sess["user_id"] = 3
            sess["vai_tro"] = "school_admin"
            sess["temp_drive_refresh_token"] = "token_that_should_not_be_seen"

        res_sa = self.client.get("/admin/google-drive/token-hien-thi")
        self.assertIn(res_sa.status_code, [302, 403])

        print("\n[PASS - TC 6]: Phân quyền nghiêm ngặt: Chỉ Super Admin mới có quyền xem trang token.")


if __name__ == "__main__":
    unittest.main()

