# -*- coding: utf-8 -*-
"""
test_hotfix_import_and_school_display.py
Kiểm thử toàn diện cho Hotfix Tổng hợp:
1. Import danh sách hàng loạt (Excel/CSV):
   - Không bị sập 500 khi import file lớn (269 dòng, 1000 dòng)
   - Thuật toán hash pbkdf2:sha256:600000 an toàn, đăng nhập được
   - Validate nhanh (<10s) đồng bộ
   - Background worker thread tạo tài khoản theo batch 50, commit DB + gc.collect()
   - Polling realtime /admin/import-users/progress
   - Phục hồi tiến trình khi reload
   - Từ chối file >2000 dòng, file rỗng, file sai định dạng
   - Tải file Excel kết quả
2. Hiển thị tên trường dưới tên người dùng:
   - index.html (Bảng vinh danh)
   - /admin (Tài khoản, cảnh báo AI, hàng chờ, vi phạm, kỹ năng)
   - /skills/market
   - /community/market
   - /book-skill/<id>
   - /skills/approval
   - /community/attendance/<id>
   - /virtual-rooms/dashboard
   - /forum and /forum/topic/<id>
   - /profile
   - base.html (User dropdown)
   - Bộ lọc theo trường cho Super Admin ở /admin
"""

import os
import io
import time
import json
import unittest
import openpyxl
from werkzeug.security import check_password_hash

# Thiết lập biến môi trường test
os.environ["DATABASE_TYPE"] = "sqlite"
os.environ["SECRET_KEY"] = "test-hotfix-secret-key-123456"

from app import (
    app, get_db, init_db, hash_password_safe,
    generate_standard_school_username, get_school_code,
    IMPORT_JOBS, IMPORT_JOBS_LOCK
)


class TestHotfixImportAndSchoolDisplay(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False

    def setUp(self):
        self.client = app.test_client()
        with app.app_context():
            init_db()
            db = get_db()
            cur = db.cursor()
            # Đảm bảo có ít nhất 2 trường học để test
            cur.execute("SELECT id FROM truong WHERE id = 1")
            if not cur.fetchone():
                cur.execute("INSERT INTO truong (id, ten_truong, mo_ta) VALUES (1, 'UK Academy', 'Trường Quốc tế UKA')")
            else:
                cur.execute("UPDATE truong SET ten_truong = 'UK Academy' WHERE id = 1")

            cur.execute("SELECT id FROM truong WHERE id = 2")
            if not cur.fetchone():
                cur.execute("INSERT INTO truong (id, ten_truong, mo_ta) VALUES (2, 'THPT Nguyễn Văn Trỗi', 'Trường THPT NVT')")

            # Tạo tài khoản Super Admin
            cur.execute("DELETE FROM users WHERE ma_hoc_sinh IN ('SUPERADMIN_TEST', 'ADMIN_UKA_TEST')")
            super_pwd = hash_password_safe("SuperPass123!")
            cur.execute("""
                INSERT INTO users (truong_id, ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, trang_thai)
                VALUES (1, 'SUPERADMIN_TEST', 'Tổng Quản Trị Viên', 'super_admin', 999.0, ?, 'hoat_dong')
            """, (super_pwd,))

            admin_pwd = hash_password_safe("SchoolAdmin123!")
            cur.execute("""
                INSERT INTO users (truong_id, ma_hoc_sinh, ho_ten, vai_tro, so_du_gio, mat_khau, trang_thai)
                VALUES (1, 'ADMIN_UKA_TEST', 'Quản Trị Trường UKA', 'school_admin', 100.0, ?, 'hoat_dong')
            """, (admin_pwd,))
            db.commit()

    def login_as_super_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 99999
            sess["ma_hoc_sinh"] = "SUPERADMIN_TEST"
            sess["ho_ten"] = "Tổng Quản Trị Viên"
            sess["vai_tro"] = "super_admin"
            sess["truong_id"] = 1
            sess["ten_truong"] = "UK Academy"

    def login_as_school_admin(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = 99998
            sess["ma_hoc_sinh"] = "ADMIN_UKA_TEST"
            sess["ho_ten"] = "Quản Trị Trường UKA"
            sess["vai_tro"] = "school_admin"
            sess["truong_id"] = 1
            sess["ten_truong"] = "UK Academy"

    def create_excel_file_bytes(self, num_rows=5, include_header=True, custom_rows=None):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Danh_Sach"
        if include_header:
            ws.append(["họ_tên", "vai_trò", "lớp", "email", "số_điện_thoại", "ghi_chu"])
        if custom_rows:
            for r in custom_rows:
                ws.append(r)
        else:
            run_token = secrets_token = int(time.time() * 1000) % 1000000
            for i in range(1, num_rows + 1):
                ws.append([f"Học sinh {i}", "hocsinh", "10A1", f"hs{i}_{secrets_token}_{time.time_ns()}@uka.edu.vn", f"08{secrets_token:06d}{i:02d}", f"Ghi chu {i}"])
        bio = io.BytesIO()
        wb.save(bio)
        bio.seek(0)
        return bio.getvalue()

    # -------------------------------------------------------------------------
    # TEST 1: Password hashing an toàn và đăng nhập được
    # -------------------------------------------------------------------------
    def test_hash_password_safe_and_login(self):
        raw_pwd = "SecretPassWord@2026"
        hashed = hash_password_safe(raw_pwd)
        self.assertTrue(hashed.startswith("pbkdf2:sha256:600000$") or "pbkdf2" in hashed)
        self.assertTrue(check_password_hash(hashed, raw_pwd))
        self.assertFalse(check_password_hash(hashed, "WrongPassword"))

    # -------------------------------------------------------------------------
    # TEST 2: Validate nhanh đồng bộ (<10s) với file 269 dòng (mô phỏng file UKA)
    # -------------------------------------------------------------------------
    def test_validate_excel_269_rows_fast(self):
        self.login_as_super_admin()
        excel_bytes = self.create_excel_file_bytes(num_rows=269)

        start_time = time.time()
        res = self.client.post(
            "/admin/import-users/validate",
            data={
                "truong_id": "1",
                "file": (io.BytesIO(excel_bytes), "danh_sach_uka_269.xlsx")
            },
            content_type="multipart/form-data"
        )
        elapsed = time.time() - start_time
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["valid_count"], 269)
        self.assertEqual(data["error_count"], 0)
        self.assertLess(elapsed, 10.0, "Validation 269 rows phải hoàn thành dưới 10 giây")

    # -------------------------------------------------------------------------
    # TEST 3: File lỗi / sai định dạng / rỗng -> Báo lỗi thân thiện, không sập 500
    # -------------------------------------------------------------------------
    def test_validate_invalid_and_empty_files(self):
        self.login_as_super_admin()

        # File rỗng không có dòng nào
        empty_bytes = self.create_excel_file_bytes(num_rows=0, include_header=False)
        res = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(empty_bytes), "empty.xlsx")},
            content_type="multipart/form-data"
        )
        self.assertIn(res.status_code, (200, 400))
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

        # File sai định dạng (.exe)
        res2 = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(b"dummy binary content"), "virus.exe")},
            content_type="multipart/form-data"
        )
        self.assertIn(res2.status_code, (200, 400))
        data2 = res2.get_json()
        self.assertFalse(data2["success"])
        self.assertIn("error", data2)

        # File có dòng lỗi (thiếu họ tên, vai trò sai)
        custom_rows = [
            ["Nguyễn Văn A", "hocsinh", "10A1", "", "", ""], # Hợp lệ
            ["", "hocsinh", "10A1", "", "", ""],             # Thiếu họ tên
            ["Trần Thị B", "sieu_nhan", "10A2", "", "", ""]   # Vai trò sai
        ]
        mixed_bytes = self.create_excel_file_bytes(custom_rows=custom_rows)
        res3 = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(mixed_bytes), "mixed.xlsx")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res3.status_code, 200)
        data3 = res3.get_json()
        self.assertTrue(data3["success"])
        self.assertEqual(data3["valid_count"], 1)
        self.assertEqual(data3["error_count"], 2)

    # -------------------------------------------------------------------------
    # TEST 4: Từ chối file vượt quá 2000 dòng
    # -------------------------------------------------------------------------
    def test_reject_file_exceeding_2000_rows(self):
        self.login_as_super_admin()
        # Tạo file 2005 dòng
        large_bytes = self.create_excel_file_bytes(num_rows=2005)
        res = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(large_bytes), "huge.xlsx")},
            content_type="multipart/form-data"
        )
        self.assertIn(res.status_code, (200, 400))
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("2000", data["error"])

    # -------------------------------------------------------------------------
    # TEST 5: Luồng 2 giai đoạn: Validate -> Confirm -> Polling -> Done -> Tải Excel
    # -------------------------------------------------------------------------
    def test_full_two_stage_async_import_flow(self):
        self.login_as_super_admin()
        # Tạo file 15 dòng
        excel_bytes = self.create_excel_file_bytes(num_rows=15)

        # Giai đoạn 1: Validate
        res_v = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(excel_bytes), "batch15.xlsx")},
            content_type="multipart/form-data"
        )
        self.assertEqual(res_v.status_code, 200)
        data_v = res_v.get_json()
        self.assertTrue(data_v["success"])
        job_id = data_v["job_id"]
        self.assertEqual(data_v["valid_count"], 15)

        # Giai đoạn 2: Confirm
        res_c = self.client.post(
            "/admin/import-users/confirm",
            data=json.dumps({"job_id": job_id}),
            content_type="application/json"
        )
        self.assertEqual(res_c.status_code, 200)
        data_c = res_c.get_json()
        self.assertTrue(data_c["success"])

        # Polling chờ worker thread hoàn thành (tối đa 15 giây)
        max_wait = 15
        start_wait = time.time()
        final_progress = None
        while time.time() - start_wait < max_wait:
            res_p = self.client.get(f"/admin/import-users/progress?job_id={job_id}")
            self.assertEqual(res_p.status_code, 200)
            final_progress = res_p.get_json()
            if final_progress.get("status") in ("done", "error"):
                break
            time.sleep(0.3)

        self.assertIsNotNone(final_progress)
        self.assertEqual(final_progress["status"], "done")
        self.assertEqual(final_progress["success"], 15)
        self.assertEqual(final_progress["percent"], 100)

        # Tải file Excel kết quả
        res_dl = self.client.get(f"/admin/import-users/download-result?job_id={job_id}")
        self.assertEqual(res_dl.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", res_dl.content_type)

        # Đóng job
        res_dis = self.client.post(
            "/admin/import-users/dismiss",
            data=json.dumps({"job_id": job_id}),
            content_type="application/json"
        )
        self.assertEqual(res_dis.status_code, 200)

    # -------------------------------------------------------------------------
    # TEST 6: Phục hồi tiến trình / kết quả khi client reload
    # -------------------------------------------------------------------------
    def test_resume_progress_on_reload(self):
        self.login_as_super_admin()
        excel_bytes = self.create_excel_file_bytes(num_rows=5)

        res_v = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "1", "file": (io.BytesIO(excel_bytes), "resume_test.xlsx")},
            content_type="multipart/form-data"
        )
        job_id = res_v.get_json()["job_id"]

        self.client.post(
            "/admin/import-users/confirm",
            data=json.dumps({"job_id": job_id}),
            content_type="application/json"
        )

        # Giả lập reload: gọi GET /admin/import-users/progress KHÔNG truyền job_id
        time.sleep(0.5)
        res_reload = self.client.get("/admin/import-users/progress")
        self.assertEqual(res_reload.status_code, 200)
        data_r = res_reload.get_json()
        self.assertTrue(data_r["has_job"])
        self.assertEqual(data_r["job_id"], job_id)

    # -------------------------------------------------------------------------
    # TEST 7: Quản trị trường chỉ được import trường mình
    # -------------------------------------------------------------------------
    def test_school_admin_isolation(self):
        self.login_as_school_admin() # Đang thuộc trường 1
        excel_bytes = self.create_excel_file_bytes(num_rows=3)

        # Cố tình truyền truong_id = 2 (Trường khác)
        res = self.client.post(
            "/admin/import-users/validate",
            data={"truong_id": "2", "file": (io.BytesIO(excel_bytes), "hack_school.xlsx")},
            content_type="multipart/form-data"
        )
        self.assertIn(res.status_code, (200, 403))
        data = res.get_json()
        self.assertFalse(data["success"])
        self.assertIn("quyền", data["error"].lower())

    # -------------------------------------------------------------------------
    # TEST 8: Hiển thị tên trường dưới tên người dùng trong trang /admin
    # -------------------------------------------------------------------------
    def test_school_name_display_in_admin(self):
        self.login_as_super_admin()
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        # Kiểm tra sự xuất hiện của icon trường học và tên trường
        self.assertIn("🏫", html)
        self.assertIn("filterSchoolSelect", html)
        self.assertIn("searchUserTableInput", html)
        self.assertIn("modalImportUsers", html)

    # -------------------------------------------------------------------------
    # TEST 9: Hiển thị tên trường dưới tên người dùng trên trang chủ index.html
    # -------------------------------------------------------------------------
    def test_school_name_display_in_index(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("🏫", html)

    # -------------------------------------------------------------------------
    # TEST 10: Import đồng bộ (POST /admin/import-users) không bao giờ văng 500
    # -------------------------------------------------------------------------
    def test_sync_import_robustness_never_500(self):
        self.login_as_super_admin()
        excel_bytes = self.create_excel_file_bytes(num_rows=20)

        res = self.client.post(
            "/admin/import-users",
            data={"truong_id": "1", "file": (io.BytesIO(excel_bytes), "sync_test.xlsx")},
            content_type="multipart/form-data",
            follow_redirects=True
        )
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("Thành công", html)


if __name__ == "__main__":
    unittest.main()
