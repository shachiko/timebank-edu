# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG: MILESTONE M5-BLOG (BẢNG TIN HỌC ĐƯỜNG & AI SOẠN BẢN TIN TUẦN)
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Kiểm tra 6 test cases chuẩn nghiệm thu:
1. Phân quyền: Học sinh bị chặn 403 khi vào /blog/manage, Giáo viên/Admin truy cập 200 OK.
2. CRUD bài viết: Giáo viên tạo, sửa, xóa bài viết thành công.
3. Nghiệm thu hiển thị /blog: Chỉ hiển thị bài đã đăng ('da_dang'), bài nháp ('nhap') TUYỆT ĐỐI KHÔNG xuất hiện.
4. Xem chi tiết /blog/<id>: Bài đã đăng công khai mọi người xem được; bài nháp chỉ Giáo viên/Admin xem trước (Preview), học sinh bị 404.
5. AI soạn bản tin tuần: Bản nháp đủ 5 phần (Mở đầu, Con số nổi bật, Vinh danh gia sư của tuần, Câu chuyện tiêu biểu, Lời kêu gọi), có tên thật từ dữ liệu, tac_gia_ai=1, trang_thai='nhap'.
6. Duyệt 1-click: Cô giáo bấm duyệt 1-click -> bài chuyển sang 'da_dang' -> lập tức xuất hiện công khai trên /blog với huy hiệu AI.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import unittest
import sqlite3
import os
import secrets
from app import app, get_db, init_db
from ai_service import ai_generate_weekly_newsletter


class TestMilestoneM5Blog(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Đảm bảo database đã sẵn sàng
        with app.app_context():
            init_db()

    def login_user(self, username, password="admin123"):
        """Hỗ trợ đăng nhập giả lập trong test client."""
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def logout_user(self):
        """Hỗ trợ đăng xuất."""
        return self.client.get("/logout", follow_redirects=True)

    # --------------------------------------------------------------------------
    # TEST CASE 1: PHÂN QUYỀN TRUY CẬP QUẢN LÝ BÀI VIẾT
    # --------------------------------------------------------------------------
    def test_01_access_control_blog_management(self):
        print("\n[TEST CASE 1]: Kiểm tra phân quyền truy cập trang quản trị Bảng tin...")
        
        # 1.1 Khách chưa đăng nhập vào /blog/manage -> Chuyển hướng đăng nhập (302)
        res_guest = self.client.get("/blog/manage")
        self.assertEqual(res_guest.status_code, 302, "Khách chưa đăng nhập phải bị chuyển hướng đến /login")

        # 1.2 Học sinh (HS12001) vào /blog/manage -> Bị chặn 403 Forbidden
        self.login_user("HS12001")
        res_student = self.client.get("/blog/manage")
        self.assertEqual(res_student.status_code, 403, "Học sinh không có quyền quản lý bảng tin và phải bị chặn 403 Forbidden")
        self.logout_user()

        # 1.3 Giáo viên (GV001) vào /blog/manage -> 200 OK
        self.login_user("GV001")
        res_teacher = self.client.get("/blog/manage")
        self.assertEqual(res_teacher.status_code, 200, "Giáo viên phải truy cập được trang quản lý bảng tin")
        self.assertIn("Quản lý Bảng tin", res_teacher.get_data(as_text=True))
        self.logout_user()

        # 1.4 Admin vào /blog/manage -> 200 OK
        self.login_user("admin")
        res_admin = self.client.get("/blog/manage")
        self.assertEqual(res_admin.status_code, 200, "Admin phải truy cập được trang quản lý bảng tin")
        self.logout_user()
        print("  -> PASS: Phân quyền RBAC chặt chẽ (Khách -> 302, Học sinh -> 403, Giáo viên/Admin -> 200).")

    # --------------------------------------------------------------------------
    # TEST CASE 2: CRUD BÀI VIẾT THỦ CÔNG CỦA GIÁO VIÊN / ADMIN
    # --------------------------------------------------------------------------
    def test_02_crud_blog_posts(self):
        print("\n[TEST CASE 2]: Kiểm tra các thao tác Thêm, Sửa, Xóa (CRUD) bài viết...")
        self.login_user("GV001")

        # 2.1 Tạo bài viết mới
        title_create = "Hướng dẫn sử dụng ví thời gian học kỳ 1"
        content_create = "Mỗi bạn học sinh cần chú ý số dư giờ để tham gia các buổi học đồng đẳng."
        res_create = self.client.post("/blog/create", data={
            "tieu_de": title_create,
            "noi_dung": content_create,
            "trang_thai": "nhap"
        }, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)

        # Kiểm tra bài viết đã được lưu vào database
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM blog_posts WHERE tieu_de = ?", (title_create,))
            post = cur.fetchone()
            self.assertIsNotNone(post, "Bài viết mới phải được lưu vào CSDL")
            post_id = post["id"]
            self.assertEqual(post["trang_thai"], "nhap")
            self.assertEqual(post["tac_gia_ai"], 0)

        # 2.2 Sửa bài viết
        title_edit = "Hướng dẫn sử dụng ví thời gian học kỳ 1 (Cập nhật mới)"
        res_edit = self.client.post(f"/blog/{post_id}/edit", data={
            "tieu_de": title_edit,
            "noi_dung": content_create,
            "trang_thai": "da_dang"
        }, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
            updated_post = cur.fetchone()
            self.assertEqual(updated_post["tieu_de"], title_edit)
            self.assertEqual(updated_post["trang_thai"], "da_dang")

        # 2.3 Xóa bài viết
        res_delete = self.client.post(f"/blog/{post_id}/delete", follow_redirects=True)
        self.assertEqual(res_delete.status_code, 200)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT * FROM blog_posts WHERE id = ?", (post_id,))
            deleted_post = cur.fetchone()
            self.assertIsNone(deleted_post, "Bài viết phải bị xóa khỏi CSDL")

        self.logout_user()
        print("  -> PASS: Thao tác Thêm, Sửa, Xóa bài viết hoạt động chính xác.")

    # --------------------------------------------------------------------------
    # TEST CASE 3: BÀI NHÁP KHÔNG HIỂN THỊ Ở /BLOG, CHỈ HIỆN BÀI ĐÃ ĐĂNG
    # --------------------------------------------------------------------------
    def test_03_blog_index_filters_drafts(self):
        print("\n[TEST CASE 3]: Kiểm tra bài nháp chưa duyệt TUYỆT ĐỐI KHÔNG hiện trên trang /blog...")
        
        unique_draft_title = "BẢN NHÁP BÍ MẬT KHÔNG ĐƯỢC HIỆN TRÊN BẢNG TIN"
        unique_pub_title = "BÀI VIẾT ĐÃ ĐĂNG CÔNG KHAI TOÀN TRƯỜNG"

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            # Tạo 1 bài nháp
            cur.execute("""
                INSERT INTO blog_posts (tieu_de, noi_dung, tac_gia_ai, trang_thai)
                VALUES (?, 'Nội dung chưa duyệt', 0, 'nhap')
            """, (unique_draft_title,))
            # Tạo 1 bài đã đăng
            cur.execute("""
                INSERT INTO blog_posts (tieu_de, noi_dung, tac_gia_ai, trang_thai)
                VALUES (?, 'Nội dung công khai', 0, 'da_dang')
            """, (unique_pub_title,))
            db.commit()

        # Khách hoặc học sinh truy cập /blog
        res_blog = self.client.get("/blog")
        html = res_blog.get_data(as_text=True)

        self.assertEqual(res_blog.status_code, 200)
        self.assertNotIn(unique_draft_title, html, "Bài nháp ('nhap') TUYỆT ĐỐI KHÔNG được xuất hiện trên trang /blog!")
        self.assertIn(unique_pub_title, html, "Bài đã đăng ('da_dang') PHẢI xuất hiện trên trang /blog.")
        print("  -> PASS: Trang /blog lọc chuẩn xác — bài chưa duyệt không hiển thị.")

    # --------------------------------------------------------------------------
    # TEST CASE 4: XEM CHI TIẾT /BLOG/<ID> (BẢN NHÁP CHỈ GV/ADMIN XEM ĐƯỢC)
    # --------------------------------------------------------------------------
    def test_04_blog_detail_access_and_preview(self):
        print("\n[TEST CASE 4]: Kiểm tra xem chi tiết bài viết và chế độ Preview bản nháp...")
        
        draft_title = "Bài viết nháp cần kiểm duyệt chuyên môn"
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                INSERT INTO blog_posts (tieu_de, noi_dung, tac_gia_ai, trang_thai)
                VALUES (?, 'Nội dung thảo luận nội bộ', 0, 'nhap')
            """, (draft_title,))
            draft_id = cur.lastrowid
            db.commit()

        # 4.1 Khách chưa đăng nhập xem bài nháp -> 404 Not Found
        res_guest = self.client.get(f"/blog/{draft_id}")
        self.assertEqual(res_guest.status_code, 404, "Khách không được xem bài nháp -> 404")

        # 4.2 Học sinh xem bài nháp -> 404 Not Found
        self.login_user("HS12001")
        res_student = self.client.get(f"/blog/{draft_id}")
        self.assertEqual(res_student.status_code, 404, "Học sinh không được xem bài nháp -> 404")
        self.logout_user()

        # 4.3 Giáo viên xem bài nháp -> 200 OK (Chế độ Preview có cảnh báo bản nháp và nút duyệt)
        self.login_user("GV001")
        res_teacher = self.client.get(f"/blog/{draft_id}")
        self.assertEqual(res_teacher.status_code, 200, "Giáo viên phải xem trước được bài nháp")
        html_teacher = res_teacher.get_data(as_text=True)
        self.assertIn("CHẾ ĐỘ XEM TRƯỚC (BẢN NHÁP)", html_teacher)
        self.assertIn("Duyệt & Đăng ngay", html_teacher)
        self.logout_user()
        print("  -> PASS: Phân quyền xem chi tiết bài viết chuẩn xác (Học sinh 404, Giáo viên xem trước 200).")

    # --------------------------------------------------------------------------
    # TEST CASE 5: NÚT 'NHỜ AI SOẠN BẢN TIN TUẦN' (ĐỦ 5 PHẦN & TÊN THẬT TỪ DATA)
    # --------------------------------------------------------------------------
    def test_05_ai_weekly_newsletter_generation(self):
        print("\n[TEST CASE 5]: Kiểm tra AI soạn bản tin tuần (đủ 5 phần cấu trúc & chứa tên thật)...")
        self.login_user("GV001")

        # Gọi endpoint /blog/ai-newsletter
        res_ai = self.client.get("/blog/ai-newsletter", follow_redirects=True)
        self.assertEqual(res_ai.status_code, 200)

        # Truy vấn bài viết mới nhất do AI sinh ra
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                SELECT * FROM blog_posts 
                WHERE tac_gia_ai = 1 
                ORDER BY id DESC LIMIT 1
            """)
            ai_post = cur.fetchone()
            self.assertIsNotNone(ai_post, "Phải có bài viết do AI tạo ra")
            self.assertEqual(ai_post["trang_thai"], "nhap", "Bản tin do AI soạn BẮT BUỘC lưu ở trạng thái 'nhap'")
            self.assertEqual(ai_post["tac_gia_ai"], 1, "Cột tac_gia_ai phải bằng 1")

            noi_dung = ai_post["noi_dung"]
            # NGHIỆM THU: Bản nháp đủ 5 phần theo yêu cầu đề bài
            self.assertIn("Mở đầu", noi_dung, "Bản tin AI phải có phần 1: Mở đầu")
            self.assertIn("Con số nổi bật", noi_dung, "Bản tin AI phải có phần 2: Con số nổi bật")
            self.assertIn("Vinh danh gia sư của tuần", noi_dung, "Bản tin AI phải có phần 3: Vinh danh gia sư của tuần")
            self.assertIn("Câu chuyện tiêu biểu", noi_dung, "Bản tin AI phải có phần 4: Câu chuyện tiêu biểu")
            self.assertIn("Lời kêu gọi", noi_dung, "Bản tin AI phải có phần 5: Lời kêu gọi")

            # NGHIỆM THU: Chứa tên thật từ dữ liệu trong database
            cur.execute("SELECT ho_ten FROM users WHERE vai_tro = 'hoc_sinh'")
            real_names = [r["ho_ten"] for r in cur.fetchall()]
            found_name = any(name in noi_dung for name in real_names)
            self.assertTrue(found_name, f"Bản tin AI phải chứa ít nhất một tên thật từ dữ liệu học sinh ({real_names})")

            # Kiểm tra ai_logs có ghi nhận
            cur.execute("SELECT COUNT(*) FROM ai_logs WHERE chuc_nang = 'bien_tap_vien'")
            self.assertGreater(cur.fetchone()[0], 0, "Hệ thống phải ghi vết tương tác AI vào ai_logs")

        self.logout_user()
        print("  -> PASS: Bản tin AI lưu tac_gia_ai=1, trang_thai='nhap', đủ 5 phần cấu trúc và chứa tên thật từ dữ liệu.")

    # --------------------------------------------------------------------------
    # TEST CASE 6: CÔ GIÁO DUYỆT 1-CLICK MỚI ĐĂNG
    # --------------------------------------------------------------------------
    def test_06_one_click_publish_workflow(self):
        print("\n[TEST CASE 6]: Kiểm tra luồng duyệt 1-click của cô giáo...")
        self.login_user("GV001")

        unique_title = f"Bản tin thử nghiệm duyệt 1-click {secrets.token_hex(4)}"

        # 6.1 Tạo một bài nháp của AI
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                INSERT INTO blog_posts (tieu_de, noi_dung, tac_gia_ai, trang_thai)
                VALUES (?, 'Nội dung bản tin...', 1, 'nhap')
            """, (unique_title,))
            post_id = cur.lastrowid
            db.commit()

        # 6.2 Trước khi duyệt: Kiểm tra trên /blog -> KHÔNG CÓ
        res_before = self.client.get("/blog")
        self.assertNotIn(unique_title, res_before.get_data(as_text=True))

        # 6.3 Cô giáo bấm Duyệt 1-click qua /blog/<id>/publish
        res_publish = self.client.get(f"/blog/{post_id}/publish", follow_redirects=True)
        self.assertEqual(res_publish.status_code, 200)

        # Kiểm tra database đã cập nhật trạng thái 'da_dang'
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT trang_thai FROM blog_posts WHERE id = ?", (post_id,))
            status = cur.fetchone()["trang_thai"]
            self.assertEqual(status, "da_dang", "Sau khi duyệt 1-click, trạng thái phải chuyển sang 'da_dang'")

        # 6.4 Sau khi duyệt: Truy cập lại /blog -> PHẢI XUẤT HIỆN bài viết
        res_after = self.client.get("/blog")
        html_after = res_after.get_data(as_text=True)
        self.assertIn(unique_title, html_after, "Sau khi duyệt, bài viết phải lập tức hiển thị công khai trên /blog")
        self.assertIn("Hỗ trợ bởi AI (Gemini)", html_after, "Bài viết của AI phải hiển thị rõ huy hiệu 'Hỗ trợ bởi AI (Gemini)'")

        self.logout_user()
        print("  -> PASS: Cơ chế duyệt 1-click hoạt động hoàn hảo, bảo đảm quyền kiểm duyệt của giáo viên.")


if __name__ == "__main__":
    unittest.main()
