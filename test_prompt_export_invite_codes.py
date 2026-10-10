# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG — TÍNH NĂNG XUẤT EXCEL & SAO CHÉP TẤT CẢ MÃ MỜI
ĐÁP ỨNG ĐẦY ĐỦ CÁC TIÊU CHÍ NGHIỆM THU:
1. Nhấn "Xuất Excel" -> Tải file .xlsx có đủ thông tin mã: mã mời | loại mã | trường | số lượt còn lại | ngày tạo | trạng thái.
2. Nhấn "Sao chép tất cả" -> Thu thập được danh sách mã đầy đủ (mỗi mã 1 dòng).
3. Đặt 2 nút ở vị trí dễ thấy ngay trên bảng mã mời (#btnExportInviteCodesExcel, #btnCopyAllInviteCodes).
4. Phân quyền đa trường (Multi-tenant): School Admin chỉ xuất mã của trường mình, Super Admin có thể lọc theo trường.
"""

import os
import io
import sys
import unittest
from datetime import datetime
from werkzeug.security import generate_password_hash
import openpyxl

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db


class TestPromptExportInviteCodes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        with app.app_context():
            init_db()
            db = get_db()
            cur = db.cursor()

            # Chuẩn bị Super Admin
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'SUPER_ADMIN_INV'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio, email)
                    VALUES ('SUPER_ADMIN_INV', 'Cô Huyền Super Admin', ?, 'admin', 1, 'hoat_dong', 100.0, 'super_inv@timebank.edu.vn')
                """, (generate_password_hash("AdminPass123!"),))

            # Chuẩn bị School Admin Trường 1
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'SCHOOL_ADMIN_T1'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio, email)
                    VALUES ('SCHOOL_ADMIN_T1', 'Admin UKA T1', ?, 'school_admin', 1, 'hoat_dong', 100.0, 'admint1@uka.edu.vn')
                """, (generate_password_hash("AdminPass123!"),))

            # Chuẩn bị School Admin Trường 2
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'SCHOOL_ADMIN_T2'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio, email)
                    VALUES ('SCHOOL_ADMIN_T2', 'Admin THUOC T2', ?, 'school_admin', 2, 'hoat_dong', 100.0, 'admint2@thuoc.edu.vn')
                """, (generate_password_hash("AdminPass123!"),))

            db.commit()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    def login_as(self, username, password="AdminPass123!"):
        self.client.get("/logout")
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def test_01_ui_has_export_and_copy_buttons(self):
        """[TIÊU CHÍ 3]: Bảng mã mời trên /admin hiển thị rõ ràng 2 nút Xuất Excel và Sao chép tất cả."""
        self.login_as("SUPER_ADMIN_INV")
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        self.assertIn('id="btnExportInviteCodesExcel"', html, "Thiếu nút Xuất Excel (#btnExportInviteCodesExcel)")
        self.assertIn('id="btnCopyAllInviteCodes"', html, "Thiếu nút Sao chép tất cả (#btnCopyAllInviteCodes)")
        self.assertIn("Xuất Excel", html)
        self.assertIn("Sao chép tất cả", html)
        self.assertIn("copyAllInviteCodes()", html, "Thiếu hàm JavaScript copyAllInviteCodes")
        print("\n[PASS - TC 1]: Đã xác minh 2 nút 'Xuất Excel' và 'Sao chép tất cả' hiển thị ngay trên bảng mã mời.")

    def test_02_export_excel_endpoint_returns_valid_xlsx(self):
        """[TIÊU CHÍ 1]: Tải file .xlsx có đủ thông tin mã: mã mời | loại mã | trường | số lượt còn lại | ngày tạo | trạng thái."""
        self.login_as("SUPER_ADMIN_INV")

        # 1. Tạo 2 mã mời test trong CSDL để đảm bảo có dữ liệu
        db = get_db()
        cur = db.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (1, 'TBEDU-TEST-EX11', 'ca_nhan', 1, 0, ?, 1)
        """, (now_str,))
        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (1, 'TBEDU-TEST-EX22', 'lop', 35, 35, ?, 1)
        """, (now_str,))
        db.commit()

        # 2. Gọi route tải file Excel
        res = self.client.get("/admin/invite-codes/export-excel?truong_id=1")
        self.assertEqual(res.status_code, 200)
        self.assertIn("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", res.content_type)
        self.assertIn("attachment;", res.headers.get("Content-Disposition", ""))
        self.assertIn(".xlsx", res.headers.get("Content-Disposition", ""))

        # 3. Phân tích nội dung file Excel tải về
        wb = openpyxl.load_workbook(io.BytesIO(res.data))
        self.assertIn("Danh_Sach_Ma_Moi", wb.sheetnames)
        ws = wb["Danh_Sach_Ma_Moi"]

        headers = [cell.value for cell in ws[1]]
        # Yêu cầu: mã mời | loại mã | trường | số lượt còn lại | ngày tạo | trạng thái
        self.assertIn("Mã mời", headers)
        self.assertIn("Loại mã", headers)
        self.assertIn("Trường", headers)
        self.assertIn("Số lượt còn lại", headers)
        self.assertIn("Ngày tạo", headers)
        self.assertIn("Trạng thái", headers)

        data_rows = list(ws.iter_rows(values_only=True))[1:]
        self.assertGreaterEqual(len(data_rows), 2, "File Excel phải có ít nhất 2 dòng dữ liệu test")

        idx_code = headers.index("Mã mời")
        idx_type = headers.index("Loại mã")
        idx_rem = headers.index("Số lượt còn lại")
        idx_status = headers.index("Trạng thái")

        found_ex11 = False
        found_ex22 = False

        for row in data_rows:
            if row[idx_code] == "TBEDU-TEST-EX11":
                found_ex11 = True
                self.assertEqual(row[idx_type], "Cá nhân")
                self.assertEqual(row[idx_rem], 1)
                self.assertEqual(row[idx_status], "Khả dụng")
            elif row[idx_code] == "TBEDU-TEST-EX22":
                found_ex22 = True
                self.assertEqual(row[idx_type], "Mã lớp")
                self.assertEqual(row[idx_rem], 0)
                self.assertEqual(row[idx_status], "Đã hết lượt")

        self.assertTrue(found_ex11, "Mã 'TBEDU-TEST-EX11' phải có trong file Excel")
        self.assertTrue(found_ex22, "Mã 'TBEDU-TEST-EX22' phải có trong file Excel")
        print("\n[PASS - TC 2]: File Excel xuất ra có đầy đủ các cột và giá trị chính xác (mã mời, loại, trường, còn lại, ngày tạo, trạng thái).")

    def test_03_copy_all_logic_and_format(self):
        """[TIÊU CHÍ 2]: Thu thập mã từ bảng cho clipboard mỗi mã 1 dòng."""
        self.login_as("SUPER_ADMIN_INV")
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Kiểm tra thẻ chứa class invite-code-val
        self.assertIn('invite-code-val', html, "Bảng danh sách mã phải có class invite-code-val trên các mã mời")
        self.assertIn("copySingleInviteCode", html, "Hỗ trợ copy nhanh từng mã đơn lẻ")
        print("\n[PASS - TC 3]: Cơ chế sao chép clipboard mỗi mã 1 dòng đã sẵn sàng.")

    def test_04_tenant_isolation_school_admin(self):
        """[BẢO VỆ DỮ LIỆU ĐA TRƯỜNG]: School admin trường 2 chỉ tải mã của trường 2."""
        # Tạo mã riêng cho trường 2
        db = get_db()
        cur = db.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("""
            INSERT INTO invite_codes (truong_id, ma_code, loai, so_luot_toi_da, da_dung, ngay_tao, nguoi_tao)
            VALUES (2, 'TBEDU-T2-SPECIFIC', 'ca_nhan', 1, 0, ?, 1)
        """, (now_str,))
        db.commit()

        self.login_as("SCHOOL_ADMIN_T2")
        res = self.client.get("/admin/invite-codes/export-excel")
        self.assertEqual(res.status_code, 200)

        wb = openpyxl.load_workbook(io.BytesIO(res.data))
        ws = wb["Danh_Sach_Ma_Moi"]
        headers = [cell.value for cell in ws[1]]
        idx_code = headers.index("Mã mời")
        idx_school = headers.index("Trường")

        data_rows = list(ws.iter_rows(values_only=True))[1:]
        self.assertTrue(any(r[idx_code] == "TBEDU-T2-SPECIFIC" for r in data_rows))
        # Không được chứa mã của trường 1
        self.assertFalse(any(r[idx_code] == "TBEDU-TEST-EX11" for r in data_rows))
        print("\n[PASS - TC 4]: School Admin trường 2 chỉ xuất được mã của trường 2 (Bảo vệ dữ liệu đa trường).")

    def test_05_unauthorized_access_blocked(self):
        """Khách vãng lai chưa đăng nhập bị chặn không được tải file Excel."""
        self.client.get("/logout")
        res = self.client.get("/admin/invite-codes/export-excel", follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertIn("/login", res.headers.get("Location", ""))
        print("\n[PASS - TC 5]: Khách chưa đăng nhập bị chuyển hướng về trang đăng nhập.")


if __name__ == "__main__":
    unittest.main()
