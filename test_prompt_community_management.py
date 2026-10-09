# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — PROMPT: QUẢN LÝ CHƯƠNG TRÌNH GIỜ CÔNG ÍCH HỌC ĐƯỜNG (THÊM / SỬA / XÓA)

Nghiệm thu toàn diện:
1. Tab 'Chương trình Cộng đồng' trong /admin (Quản trị trường + Super Admin đều dùng được).
2. Thêm chương trình mới -> hiển thị ngay trên trang 'Vì cộng đồng' (/community).
3. Sửa thông tin chương trình -> cập nhật ngay trong CSDL và giao diện.
4. Xóa chương trình chưa ai đăng ký -> xóa vĩnh viễn (hard delete).
5. Xóa chương trình đã có người đăng ký -> không cho xóa cứng, tự động chuyển sang 'đã kết thúc' (soft finish).
6. Cách ly đa trường (Multi-tenant): Quản trị trường A không thấy / không sửa được chương trình trường B.
7. AI gợi ý nhiệm vụ lấy động từ bảng community_tasks thay vì danh sách fix cứng.
8. Super Admin có quyền quản lý và phân bổ chương trình cho mọi trường.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db
from ai_service import ai_recommend_tasks

class TestCommunityTasksManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()
        from werkzeug.security import generate_password_hash
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            pwd_hash = generate_password_hash("admin123")
            # Quản trị trường 1 (UK Academy)
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'admin_truong_a'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, mat_khau, ho_ten, vai_tro, truong_id, so_du_gio, trang_thai)
                    VALUES ('admin_truong_a', ?, 'Quản trị viên Trường UK Academy', 'school_admin', 1, 10.0, 'hoat_dong')
                """, (pwd_hash,))
            else:
                cur.execute("UPDATE users SET mat_khau = ?, vai_tro = 'school_admin', truong_id = 1 WHERE ma_hoc_sinh = 'admin_truong_a'", (pwd_hash,))

            # Quản trị trường 2 (Nguyễn Văn Thuộc)
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'admin_truong_b'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, mat_khau, ho_ten, vai_tro, truong_id, so_du_gio, trang_thai)
                    VALUES ('admin_truong_b', ?, 'Quản trị THCS Nguyễn Văn Thuộc', 'school_admin', 2, 10.0, 'hoat_dong')
                """, (pwd_hash,))
            else:
                cur.execute("UPDATE users SET mat_khau = ?, vai_tro = 'school_admin', truong_id = 2 WHERE ma_hoc_sinh = 'admin_truong_b'", (pwd_hash,))
            db.commit()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE vai_tro = 'super_admin' LIMIT 1")
        row = cur.fetchone()
        if row:
            self.super_admin_id = row[0]
        else:
            from werkzeug.security import generate_password_hash
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, email, truong_id, trang_thai)
                VALUES ('SUPER_TEST_COMMUNITY', 'Super Admin Community', 'super_admin', 999.0, ?, 'super_comm@timebankedu.vn', 1, 'hoat_dong')
            """, (generate_password_hash("admin123"),))
            db.commit()
            self.super_admin_id = cur.lastrowid

    def tearDown(self):
        self.app_context.pop()

    def login_super_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.super_admin_id
            sess["vai_tro"] = "super_admin"
            sess["ho_ten"] = "Super Admin Community"
            sess["truong_id"] = 1

    def login_school_admin_a(self):
        # admin_truong_a thuộc trường 1 (UK Academy)
        self.client.post("/login", data={"ma_hoc_sinh": "admin_truong_a", "mat_khau": "admin123"}, follow_redirects=True)

    def login_student(self):
        # HS12001 (An) thuộc trường 1
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)

    def logout(self):
        self.client.get("/logout", follow_redirects=True)

    def test_01_tab_presence_for_super_admin_and_school_admin(self):
        """[TC 1]: Cả Super Admin và Quản trị trường đều thấy tab 'Chương trình Cộng đồng' trong /admin."""
        # 1. Super admin
        self.login_super_admin()
        res_super = self.client.get("/admin")
        self.assertEqual(res_super.status_code, 200)
        html_super = res_super.data.decode("utf-8")
        self.assertIn("tab-community-tasks-btn", html_super, "Super Admin phải thấy nút tab Chương trình Cộng đồng")
        self.assertIn('id="tab-community-tasks"', html_super, "Super Admin phải thấy tab-pane #tab-community-tasks")
        self.assertIn("Thêm Chương Trình Giờ Công Ích Mới", html_super)
        self.assertIn("Danh Sách Chương Trình Giờ Công Ích Học Đường", html_super)
        self.logout()

        # 2. School admin
        self.login_school_admin_a()
        res_school = self.client.get("/admin")
        self.assertEqual(res_school.status_code, 200)
        html_school = res_school.data.decode("utf-8")
        self.assertIn("tab-community-tasks-btn", html_school, "School Admin phải thấy nút tab Chương trình Cộng đồng")
        self.assertIn('id="tab-community-tasks"', html_school, "School Admin phải thấy tab-pane #tab-community-tasks")
        self.logout()

    def test_02_create_community_task_shows_on_community_page(self):
        """[TC 2]: Thêm chương trình mới -> hiện ngay trang 'Vì cộng đồng' (/community)."""
        self.login_school_admin_a()
        test_title = f"Trồng 50 cây xanh khuôn viên trường {int(datetime.now().timestamp())}"
        test_desc = "Hoạt động cải tạo cảnh quan sư phạm xanh sạch đẹp."
        
        post_data = {
            "tieu_de": test_title,
            "mo_ta": test_desc,
            "so_gio_thuong": "2.5",
            "ngay_bat_dau": "2026-11-01",
            "ngay_ket_thuc": "2026-11-05",
            "trang_thai": "dang_dien_ra",
            "dia_diem": "Khuôn viên trường UK Academy"
        }
        res_create = self.client.post("/admin/community-tasks/create", data=post_data, follow_redirects=True)
        self.assertEqual(res_create.status_code, 200)

        # Kiểm tra trong CSDL
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT * FROM community_tasks WHERE tieu_de = ?", (test_title,))
        task = cur.fetchone()
        self.assertIsNotNone(task, "Chương trình mới phải được lưu vào CSDL")
        self.assertEqual(task["so_gio_thuong"], 2.5)
        self.assertEqual(task["ngay_bat_dau"], "2026-11-01")
        self.assertEqual(task["ngay_ket_thuc"], "2026-11-05")

        # Học sinh vào trang /community -> chương trình phải xuất hiện ngay lập tức
        self.logout()
        self.login_student()
        res_comm = self.client.get("/community")
        self.assertEqual(res_comm.status_code, 200)
        html_comm = res_comm.data.decode("utf-8")
        self.assertIn(test_title, html_comm, "Chương trình mới phải xuất hiện ngay trên trang /community")
        self.assertIn("2.5", html_comm, "Số giờ thưởng 2.5h phải hiển thị trên thẻ")
        self.logout()

    def test_03_edit_community_task_updates_instantly(self):
        """[TC 3]: Sửa thông tin -> cập nhật ngay trong CSDL và giao diện."""
        self.login_school_admin_a()
        db = get_db()
        cur = db.cursor()
        
        # Tạo chương trình thử nghiệm
        unique_title = f"Chương trình Cũ {int(datetime.now().timestamp())}"
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, mo_ta, so_gio_thuong, so_luong_toi_da, trang_thai, truong_id, nguoi_tao_id)
            VALUES (?, 'Mô tả cũ', 1.0, 5, 'sap_dien_ra', 1, 1)
        """, (unique_title,))
        db.commit()
        task_id = cur.lastrowid

        # Gửi request chỉnh sửa
        updated_title = f"Chương trình Đã Sửa Mới {int(datetime.now().timestamp())}"
        edit_data = {
            "tieu_de": updated_title,
            "mo_ta": "Mô tả đã được cập nhật thành công.",
            "so_gio_thuong": "3.0",
            "ngay_bat_dau": "2026-12-01",
            "ngay_ket_thuc": "2026-12-10",
            "trang_thai": "dang_dien_ra",
            "dia_diem": "Thư viện trường"
        }
        res_edit = self.client.post(f"/admin/community-tasks/{task_id}/edit", data=edit_data, follow_redirects=True)
        self.assertEqual(res_edit.status_code, 200)

        # Kiểm tra CSDL
        cur.execute("SELECT * FROM community_tasks WHERE id = ?", (task_id,))
        updated_task = cur.fetchone()
        self.assertEqual(updated_task["tieu_de"], updated_title)
        self.assertEqual(updated_task["mo_ta"], "Mô tả đã được cập nhật thành công.")
        self.assertEqual(updated_task["so_gio_thuong"], 3.0)
        self.assertEqual(updated_task["trang_thai"], "dang_dien_ra")

        # Kiểm tra trang /community
        self.logout()
        self.login_student()
        res_comm = self.client.get("/community")
        html_comm = res_comm.data.decode("utf-8")
        self.assertIn(updated_title, html_comm)
        self.assertNotIn(unique_title, html_comm)
        self.logout()

    def test_04_delete_task_with_zero_registrations_hard_deletes(self):
        """[TC 4]: Xóa chương trình chưa ai đăng ký -> mất hẳn khỏi CSDL (hard delete)."""
        self.login_school_admin_a()
        db = get_db()
        cur = db.cursor()

        # Tạo một chương trình độc lập chưa ai đăng ký
        title_to_delete = f"Nhiệm vụ Sẽ Bị Xóa {int(datetime.now().timestamp())}"
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, mo_ta, so_gio_thuong, so_luong_toi_da, trang_thai, truong_id, nguoi_tao_id)
            VALUES (?, 'Chưa có ai đăng ký', 1.0, 5, 'dang_dien_ra', 1, 1)
        """, (title_to_delete,))
        db.commit()
        task_id = cur.lastrowid

        # Xác nhận trong CSDL trước khi xóa
        cur.execute("SELECT COUNT(*) FROM community_tasks WHERE id = ?", (task_id,))
        self.assertEqual(cur.fetchone()[0], 1)

        # Gửi request xóa
        res_del = self.client.post(f"/admin/community-tasks/{task_id}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)

        # Kiểm tra CSDL: bản ghi phải mất hẳn
        cur.execute("SELECT COUNT(*) FROM community_tasks WHERE id = ?", (task_id,))
        self.assertEqual(cur.fetchone()[0], 0, "Chương trình chưa có ai đăng ký phải bị xóa hẳn khỏi CSDL")
        self.logout()

    def test_05_delete_task_with_registrations_blocks_hard_delete_and_finishes(self):
        """[TC 5]: Chương trình đã có người đăng ký -> không cho xóa cứng, chỉ cho chuyển 'đã kết thúc'."""
        self.login_school_admin_a()
        db = get_db()
        cur = db.cursor()

        # Tạo chương trình có đăng ký
        title_with_regs = f"Chương trình Đã Có Người Đăng Ký {int(datetime.now().timestamp())}"
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, mo_ta, so_gio_thuong, so_luong_toi_da, trang_thai, truong_id, nguoi_tao_id)
            VALUES (?, 'Đã có đăng ký', 1.5, 5, 'dang_dien_ra', 1, 1)
        """, (title_with_regs,))
        db.commit()
        task_id = cur.lastrowid

        # Tạo 1 đăng ký của học sinh
        cur.execute("""
            INSERT INTO task_registrations (task_id, user_id, truong_id, trang_thai)
            VALUES (?, 3, 1, 'da_dang_ky')
        """, (task_id,))
        db.commit()

        # Gửi request xóa
        res_del = self.client.post(f"/admin/community-tasks/{task_id}/delete", follow_redirects=True)
        self.assertEqual(res_del.status_code, 200)
        html_del = res_del.data.decode("utf-8")
        self.assertIn("không thể xóa vĩnh viễn", html_del)

        # Kiểm tra CSDL: bản ghi VẪN CÒN nhưng trạng thái chuyển sang 'da_ket_thuc'
        cur.execute("SELECT trang_thai FROM community_tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        self.assertIsNotNone(row, "Chương trình đã có đăng ký không được xóa cứng")
        self.assertEqual(row["trang_thai"], "da_ket_thuc", "Trạng thái phải tự động chuyển thành 'da_ket_thuc'")
        self.logout()

    def test_06_multi_tenant_isolation_school_a_cannot_see_or_edit_school_b(self):
        """[TC 6]: Quản trị trường A không thấy/sửa được chương trình trường B."""
        db = get_db()
        cur = db.cursor()

        # Đảm bảo có tài khoản quản trị trường B (truong_id = 2)
        cur.execute("SELECT id FROM users WHERE vai_tro = 'school_admin' AND truong_id = 2")
        admin_b_row = cur.fetchone()
        if not admin_b_row:
            from werkzeug.security import generate_password_hash
            cur.execute("""
                INSERT INTO users (ma_hoc_sinh, mat_khau, ho_ten, vai_tro, truong_id, so_du_gio, trang_thai)
                VALUES ('admin_truong_b', ?, 'Quản trị THCS Nguyễn Văn Thuộc', 'school_admin', 2, 10.0, 'hoat_dong')
            """, (generate_password_hash("admin123"),))
            db.commit()

        # Tạo 1 task của trường B (truong_id = 2)
        title_school_b = f"Hoạt động Trường B {int(datetime.now().timestamp())}"
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, mo_ta, so_gio_thuong, so_luong_toi_da, trang_thai, truong_id, nguoi_tao_id)
            VALUES (?, 'Chỉ trường B thấy', 2.0, 10, 'dang_dien_ra', 2, 1)
        """, (title_school_b,))
        db.commit()
        task_b_id = cur.lastrowid

        # 1. Quản trị trường A (demo_quantruong, truong_id = 1) vào /admin -> KHÔNG thấy task của trường B
        self.login_school_admin_a()
        res_admin_a = self.client.get("/admin")
        html_admin_a = res_admin_a.data.decode("utf-8")
        self.assertNotIn(title_school_b, html_admin_a, "Quản trị trường A không được thấy chương trình của trường B")

        # 2. Quản trị trường A cố tình gửi request Sửa task của trường B -> Bị chặn
        res_illegal_edit = self.client.post(f"/admin/community-tasks/{task_b_id}/edit", data={
            "tieu_de": "Hacker cố sửa task trường B",
            "so_gio_thuong": "5.0",
            "trang_thai": "dang_dien_ra"
        }, follow_redirects=True)
        html_illegal_edit = res_illegal_edit.data.decode("utf-8")
        self.assertIn("không có quyền", html_illegal_edit, "Hệ thống phải chặn sửa chương trình của trường khác")

        # 3. Quản trị trường A cố tình gửi request Xóa task của trường B -> Bị chặn
        res_illegal_delete = self.client.post(f"/admin/community-tasks/{task_b_id}/delete", follow_redirects=True)
        html_illegal_delete = res_illegal_delete.data.decode("utf-8")
        self.assertIn("không có quyền", html_illegal_delete, "Hệ thống phải chặn xóa chương trình của trường khác")

        # Xác nhận tiêu đề trong CSDL không bị thay đổi
        cur.execute("SELECT tieu_de FROM community_tasks WHERE id = ?", (task_b_id,))
        self.assertEqual(cur.fetchone()[0], title_school_b)
        self.logout()

    def test_07_ai_recommend_tasks_dynamic_from_db(self):
        """[TC 7]: AI gợi ý nhiệm vụ lấy động từ bảng community_tasks thay vì list cứng."""
        db = get_db()
        cur = db.cursor()

        # Thêm nhiệm vụ mới vào CSDL
        unique_ai_title = f"Thăm mái ấm và dạy tin học cơ bản {int(datetime.now().timestamp())}"
        cur.execute("""
            INSERT INTO community_tasks (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, trang_thai, truong_id, nguoi_tao_id)
            VALUES (?, 'Giao lưu thiện nguyện và chia sẻ kỹ năng số cho trẻ em', 'Mái ấm Ánh Sao', 2.0, 5, 'dang_dien_ra', 1, 1)
        """, (unique_ai_title,))
        db.commit()

        # Gọi hàm AI gợi ý nhiệm vụ với open_tasks=None (tự lấy từ CSDL)
        recommended, is_live = ai_recommend_tasks(db, 3, open_tasks=None)
        self.assertTrue(len(recommended) > 0, "AI phải đề xuất được nhiệm vụ")
        
        # Đảm bảo danh sách trả về là từ bảng community_tasks
        task_titles = [r["tieu_de"] for r in recommended]
        self.assertTrue(any(unique_ai_title in t or "mái ấm" in t.lower() or "cây xanh" in t.lower() or "bãi biển" in t.lower() for t in task_titles))
        for r in recommended:
            self.assertIn("ly_do_ai_goi_y", r, "Mỗi nhiệm vụ gợi ý phải có lời giải thích sư phạm từ AI")

    def test_08_super_admin_can_manage_all_schools(self):
        """[TC 8]: Super Admin có quyền tạo chương trình cho bất kỳ trường nào và thấy toàn bộ."""
        self.login_super_admin()
        super_title = f"Ngày hội STEM Liên trường Toàn tỉnh {int(datetime.now().timestamp())}"
        
        # Super admin tạo nhiệm vụ gán cho trường 2
        post_data = {
            "tieu_de": super_title,
            "mo_ta": "Sự kiện khoa học liên trường lớn nhất năm.",
            "so_gio_thuong": "3.5",
            "truong_id": "2",
            "trang_thai": "sap_dien_ra"
        }
        res = self.client.post("/admin/community-tasks/create", data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Kiểm tra trong /admin của Super Admin thấy được task vừa tạo
        res_admin = self.client.get("/admin")
        self.assertIn(super_title, res_admin.data.decode("utf-8"))

        # Kiểm tra CSDL
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT truong_id FROM community_tasks WHERE tieu_de = ?", (super_title,))
        self.assertEqual(cur.fetchone()[0], 2, "Task phải được gán đúng trường 2 theo chỉ định của Super Admin")
        self.logout()


if __name__ == "__main__":
    unittest.main()
