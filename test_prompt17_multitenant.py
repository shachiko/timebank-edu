# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN — PROMPT 17: ĐẠI PHẪU ĐA TRƯỜNG (MULTI-TENANT CORE)
Nghiệm thu 8 tiêu chí bắt buộc:
1. Có file backup trước migrate (PostgreSQL & SQLite).
2. Đăng nhập tài khoản cũ OK, dữ liệu cũ nguyên vẹn, thuộc trường số 1.
3. Tạo school_admin trường 2 -> chỉ thấy dữ liệu trường 2, không thấy trường 1.
4. Super-admin thấy tất cả 4 trường + nút "Duyệt tất cả" hoạt động.
5. Tạo mã mời số lượng tùy chọn -> mã dạng TBEDU-XXXX-XXXX;
   đăng ký nhập mã hợp lệ -> vào đúng trường & kích hoạt ngay;
   mã sai -> báo lỗi; mã hết lượt -> báo hết hiệu lực;
   không mã -> vào hàng chờ duyệt, không đăng kỹ năng / đặt lịch được.
6. Gửi từ cấm trong chat -> bị chặn + ghi violations mức 1, mức 2, mức 3 đề xuất khóa.
7. Trang /noi-quy hiển thị đúng 6 điều + chế tài; không còn tên UKA ở header/hero/footer;
   tiêu đề "School Time Bank" trang trọng + phụ đề "Ngân hàng Thời gian Học đường".
8. Báo cáo vi phạm trong phòng học ảo gửi trực tiếp tới giáo viên/quản trị.
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

from app import app, get_db, DATABASE_PATH, init_db

class TestPrompt17MultiTenant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'SUPER_ADMIN_TEST'")
            if not cur.fetchone():
                cur.execute("""
                    INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
                    VALUES ('SUPER_ADMIN_TEST', 'Super Admin Test', ?, 'super_admin', 1, 'hoat_dong', 10.0)
                """, (generate_password_hash("admin123"),))
                db.commit()

    def setUp(self):
        self.app_context = app.app_context()
        self.app_context.push()
        self.client = app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # =========================================================================
    # TIÊU CHÍ 1: KIỂM TRA FILE BACKUP TRƯỚC MIGRATE
    # =========================================================================
    def test_01_backup_files_exist_and_not_empty(self):
        """[TIÊU CHÍ 1]: Export toàn bộ PostgreSQL & SQLite ra backup trước khi đụng schema."""
        pg_backup = Path("database/backup_pre_migration_postgres.sql")
        sqlite_sql_backup = Path("database/backup_pre_migration_sqlite.sql")
        sqlite_db_backup = Path("database/timebank_pre_migration.db.bak")

        self.assertTrue(pg_backup.exists(), "Tệp backup PostgreSQL phải tồn tại")
        self.assertGreater(pg_backup.stat().st_size, 500, "Tệp backup PostgreSQL không được rỗng")

        self.assertTrue(sqlite_sql_backup.exists(), "Tệp SQL backup SQLite phải tồn tại")
        self.assertGreater(sqlite_sql_backup.stat().st_size, 500, "Tệp SQL backup SQLite không được rỗng")

        self.assertTrue(sqlite_db_backup.exists(), "Tệp binary backup SQLite phải tồn tại")
        self.assertGreater(sqlite_db_backup.stat().st_size, 500, "Tệp binary backup SQLite không được rỗng")
        print("\n[PASS - TC 1]: File backup PostgreSQL và SQLite đầy đủ, dung lượng hợp lệ.")

    # =========================================================================
    # TIÊU CHÍ 2: ĐĂNG NHẬP TÀI KHOẢN CŨ, DỮ LIỆU THUỘC TRƯỜNG 1
    # =========================================================================
    def test_02_old_accounts_login_ok_and_assigned_to_school_1(self):
        """[TIÊU CHÍ 2]: Đăng nhập tài khoản cũ OK, dữ liệu cũ nguyên vẹn, thuộc trường số 1."""
        # 1. Đăng nhập Admin cũ (nâng lên super_admin)
        res_admin = self.client.post("/login", data={"ma_hoc_sinh": "admin", "mat_khau": "admin123"}, follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertIn(sess.get("vai_tro"), ("super_admin", "school_admin"))

        self.client.get("/logout")

        # 2. Đăng nhập Giáo viên cũ
        res_gv = self.client.post("/login", data={"ma_hoc_sinh": "GV001", "mat_khau": "admin123"}, follow_redirects=True)
        self.assertEqual(res_gv.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("vai_tro"), "giao_vien")
            self.assertEqual(sess.get("truong_id"), 1)

        self.client.get("/logout")

        # 3. Đăng nhập Học sinh cũ (HS12001)
        res_hs = self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        self.assertEqual(res_hs.status_code, 200)
        with self.client.session_transaction() as sess:
            self.assertEqual(sess.get("vai_tro"), "hoc_sinh")
            self.assertEqual(sess.get("truong_id"), 1)

        self.client.get("/logout")

        # 4. Kiểm tra CSDL: Bảng truong có đủ 4 trường
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id, ten_truong, trang_thai FROM truong ORDER BY id ASC")
        schools = cur.fetchall()
        self.assertGreaterEqual(len(schools), 4, "Phải có ít nhất 4 trường học được seed")
        self.assertEqual(schools[0]["trang_thai"], "dang_thi_diem")
        self.assertEqual(schools[1]["trang_thai"], "chuan_bi_trien_khai")

        # 5. Kiểm tra dữ liệu demo thuộc trường 1
        cur.execute("SELECT COUNT(*) FROM users WHERE truong_id = 1")
        self.assertGreaterEqual(cur.fetchone()[0], 7)
        cur.execute("SELECT COUNT(*) FROM skills WHERE truong_id = 1")
        self.assertGreaterEqual(cur.fetchone()[0], 5)

        print("\n[PASS - TC 2]: Đăng nhập tài khoản cũ thành công, toàn bộ dữ liệu ban đầu thuộc trường 1.")

    # =========================================================================
    # TIÊU CHÍ 3: PHÂN QUYỀN SCHOOL_ADMIN TRƯỜNG 2 (MULTI-TENANT ISOLATION)
    # =========================================================================
    def test_03_school_admin_school_2_isolation(self):
        """[TIÊU CHÍ 3]: Tạo school_admin trường 2 -> chỉ thấy dữ liệu trường 2, không thấy trường 1."""
        db = get_db()
        cur = db.cursor()

        # Tạo school_admin trường 2
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh IN ('ADMIN_TRUONG2', 'HS_TRUONG2_TEST', 'HS_TRUONG1_PENDING')")
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
            VALUES ('ADMIN_TRUONG2', 'Quản trị viên Trường Thuộc', ?, 'school_admin', 2, 'hoat_dong', 2.0)
        """, (generate_password_hash("admin123"),))

        # Tạo 1 học sinh chờ duyệt ở trường 1 và 1 học sinh chờ duyệt ở trường 2
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
            VALUES ('HS_TRUONG1_PENDING', 'Em Chờ Trường 1', ?, 'hoc_sinh', 1, 'cho_duyet', 0.0)
        """, (generate_password_hash("123456"),))
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
            VALUES ('HS_TRUONG2_TEST', 'Em Chờ Trường 2', ?, 'hoc_sinh', 2, 'cho_duyet', 0.0)
        """, (generate_password_hash("123456"),))
        db.commit()

        # Đăng nhập school_admin trường 2
        self.client.post("/login", data={"ma_hoc_sinh": "ADMIN_TRUONG2", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Phải thấy học sinh trường 2, TUYỆT ĐỐI không thấy học sinh trường 1 trong hàng chờ
        self.assertIn("HS_TRUONG2_TEST", html, "School_admin trường 2 phải thấy học sinh chờ duyệt trường 2")
        self.assertNotIn("HS_TRUONG1_PENDING", html, "School_admin trường 2 KHÔNG được thấy học sinh trường 1")

        print("\n[PASS - TC 3]: School admin trường 2 cách ly dữ liệu hoàn hảo, không thấy dữ liệu trường 1.")

    # =========================================================================
    # TIÊU CHÍ 4: SUPER-ADMIN THẤY TOÀN BỘ 4 TRƯỜNG & DUYỆT TẤT CẢ HOẠT ĐỘNG
    # =========================================================================
    def test_04_super_admin_views_all_schools_and_batch_approves(self):
        """[TIÊU CHÍ 4]: Super-admin thấy tất cả 4 trường + nút 'Duyệt tất cả' hoạt động."""
        # Chuẩn bị dữ liệu kiểm thử độc lập: tạo 2 học sinh chờ duyệt ở trường 1 và trường 2
        db = get_db()
        cur = db.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh IN ('HS_TRUONG1_PENDING', 'HS_TRUONG2_TEST')")
        cur.execute("PRAGMA foreign_keys = ON")
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
            VALUES ('HS_TRUONG1_PENDING', 'Em Chờ Trường 1', ?, 'hoc_sinh', 1, 'cho_duyet', 2.0)
        """, (generate_password_hash("123456"),))
        cur.execute("""
            INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, trang_thai, so_du_gio)
            VALUES ('HS_TRUONG2_TEST', 'Em Chờ Trường 2', ?, 'hoc_sinh', 2, 'cho_duyet', 2.0)
        """, (generate_password_hash("123456"),))
        db.commit()

        self.client.get("/logout")
        self.client.post("/login", data={"ma_hoc_sinh": "SUPER_ADMIN_TEST", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Super-admin thấy dropdown lọc cả 4 trường
        self.assertIn("Tất cả các trường", html)
        self.assertIn("Trường THCS Nguyễn Văn Thuộc", html)
        self.assertIn("Trường THCS Lê Văn Tám", html)
        self.assertIn("Trường THPT Hải Đảo", html)

        # Super-admin thấy cả HS trường 1 và HS trường 2 trong hàng chờ
        self.assertIn("HS_TRUONG1_PENDING", html)
        self.assertIn("HS_TRUONG2_TEST", html)

        # Thực thi "Duyệt tất cả"
        res_approve_all = self.client.post("/admin/approve-all-students", follow_redirects=True)
        self.assertEqual(res_approve_all.status_code, 200)

        # Kiểm tra trạng thái trong DB: cả 2 em đã được kích hoạt 'hoat_dong' và cấp 2.0h
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT trang_thai, so_du_gio FROM users WHERE ma_hoc_sinh = 'HS_TRUONG1_PENDING'")
        st1 = cur.fetchone()
        self.assertEqual(st1["trang_thai"], "hoat_dong")
        self.assertEqual(st1["so_du_gio"], 2.0)

        cur.execute("SELECT trang_thai, so_du_gio FROM users WHERE ma_hoc_sinh = 'HS_TRUONG2_TEST'")
        st2 = cur.fetchone()
        self.assertEqual(st2["trang_thai"], "hoat_dong")
        self.assertEqual(st2["so_du_gio"], 2.0)

        print("\n[PASS - TC 4]: Super-admin thấy toàn bộ 4 trường và nút 'Duyệt tất cả' kích hoạt hàng loạt thành công.")

    # =========================================================================
    # TIÊU CHÍ 5: MÃ MỜI ĐỊNH DẠNG TBEDU-XXXX-XXXX & BẢO VỆ ĐĂNG KÝ
    # =========================================================================
    def test_05_invite_codes_generation_validation_and_registration_protection(self):
        db = get_db()
        cur = db.cursor()
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM invite_code_usages WHERE user_id IN (SELECT id FROM users WHERE ma_hoc_sinh IN ('HS_INV_VALID', 'HS_INV_EXHAUSTED', 'HS_INV_INVALID', 'HS_PENDING_REG'))")
        cur.execute("DELETE FROM credits_ledger WHERE user_id IN (SELECT id FROM users WHERE ma_hoc_sinh IN ('HS_INV_VALID', 'HS_INV_EXHAUSTED', 'HS_INV_INVALID', 'HS_PENDING_REG'))")
        cur.execute("DELETE FROM users WHERE ma_hoc_sinh IN ('HS_INV_VALID', 'HS_INV_EXHAUSTED', 'HS_INV_INVALID', 'HS_PENDING_REG')")
        cur.execute("DELETE FROM invite_code_usages WHERE invite_code_id IN (SELECT id FROM invite_codes WHERE truong_id = 2)")
        cur.execute("DELETE FROM invite_codes WHERE truong_id = 2")
        cur.execute("PRAGMA foreign_keys = ON")
        db.commit()

        self.client.get("/logout")
        self.client.post("/login", data={"ma_hoc_sinh": "SUPER_ADMIN_TEST", "mat_khau": "admin123"}, follow_redirects=True)

        # 1. Tạo 2 mã cá nhân cho Trường 2
        res_gen = self.client.post("/admin/invite-codes/generate", data={
            "truong_id": "2",
            "loai": "ca_nhan",
            "so_luong": "2",
            "ghi_chu": "Mã cá nhân test"
        }, follow_redirects=True)
        self.assertEqual(res_gen.status_code, 200)

        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT ma_code, loai, so_luot_toi_da, da_dung, truong_id FROM invite_codes WHERE truong_id = 2 ORDER BY id DESC LIMIT 2")
        codes = cur.fetchall()
        self.assertEqual(len(codes), 2)
        code1 = codes[0]["ma_code"]
        code2 = codes[1]["ma_code"]

        # Kiểm tra regex định dạng TBEDU-XXXX-XXXX
        pattern = r"^TBEDU-[A-Z0-9]{4}-[A-Z0-9]{4}$"
        self.assertTrue(re.match(pattern, code1), f"Mã mời '{code1}' không khớp mẫu TBEDU-XXXX-XXXX")
        self.assertTrue(re.match(pattern, code2), f"Mã mời '{code2}' không khớp mẫu TBEDU-XXXX-XXXX")

        # 2. Đăng xuất và đăng ký học sinh với mã hợp lệ
        self.client.get("/logout")
        res_reg_ok = self.client.post("/register", data={
            "ma_hoc_sinh": "HS_INV_VALID",
            "ho_ten": "Học Sinh Có Mã",
            "lop": "11A1",
            "gio_ranh": "Sáng CN",
            "mat_khau": "123456",
            "mat_khau_xac_nhan": "123456",
            "ma_moi": code1,
            "truong_id": "1"  # Dù chọn trường 1 nhưng có mã trường 2 thì hệ thống phải tự gán trường 2
        }, follow_redirects=True)
        self.assertEqual(res_reg_ok.status_code, 200)

        # Xác minh học sinh này vào đúng trường 2 và kích hoạt ngay (hoat_dong, 2.0h)
        cur.execute("SELECT truong_id, trang_thai, so_du_gio FROM users WHERE ma_hoc_sinh = 'HS_INV_VALID'")
        u_valid = cur.fetchone()
        self.assertEqual(u_valid["truong_id"], 2, "Học sinh dùng mã trường 2 phải được gán vào trường 2")
        self.assertEqual(u_valid["trang_thai"], "hoat_dong", "Có mã hợp lệ phải được kích hoạt ngay")
        self.assertEqual(u_valid["so_du_gio"], 2.0)

        # Kiểm tra mã 1 đã dùng 1 lượt
        cur.execute("SELECT da_dung, so_luot_toi_da FROM invite_codes WHERE ma_code = ?", (code1,))
        c1_db = cur.fetchone()
        self.assertEqual(c1_db["da_dung"], 1)

        # 3. Đăng ký với mã đã hết lượt
        self.client.get("/logout")
        res_reg_exhausted = self.client.post("/register", data={
            "ma_hoc_sinh": "HS_INV_EXHAUSTED",
            "ho_ten": "Học Sinh Hết Lượt",
            "mat_khau": "123456",
            "mat_khau_xac_nhan": "123456",
            "ma_moi": code1,
            "truong_id": "2"
        }, follow_redirects=True)
        html_ex = res_reg_exhausted.data.decode("utf-8")
        self.assertIn("đã hết số lượt sử dụng", html_ex)

        # 4. Đăng ký với mã sai
        self.client.get("/logout")
        res_reg_invalid = self.client.post("/register", data={
            "ma_hoc_sinh": "HS_INV_INVALID",
            "ho_ten": "Học Sinh Mã Sai",
            "mat_khau": "123456",
            "mat_khau_xac_nhan": "123456",
            "ma_moi": "TBEDU-9999-XXXX",
            "truong_id": "2"
        }, follow_redirects=True)
        html_inv = res_reg_invalid.data.decode("utf-8")
        self.assertIn("Mã mời không tồn tại", html_inv)

        # 5. Đăng ký KHÔNG MÃ -> Tự chọn trường 3 -> Trạng thái 'cho_duyet'
        self.client.get("/logout")
        res_reg_no_code = self.client.post("/register", data={
            "ma_hoc_sinh": "HS_PENDING_REG",
            "ho_ten": "Học Sinh Chờ Duyệt",
            "lop": "10B2",
            "gio_ranh": "Chiều T5",
            "mat_khau": "123456",
            "mat_khau_xac_nhan": "123456",
            "ma_moi": "",
            "truong_id": "3"
        }, follow_redirects=True)
        self.assertEqual(res_reg_no_code.status_code, 200)

        cur.execute("SELECT truong_id, trang_thai, so_du_gio FROM users WHERE ma_hoc_sinh = 'HS_PENDING_REG'")
        u_pending = cur.fetchone()
        self.assertEqual(u_pending["truong_id"], 3)
        self.assertEqual(u_pending["trang_thai"], "cho_duyet")
        self.assertEqual(u_pending["so_du_gio"], 2.0)

        # Đăng nhập bằng tài khoản chờ duyệt: bị chặn đăng kỹ năng & đặt lịch
        self.client.post("/login", data={"ma_hoc_sinh": "HS_PENDING_REG", "mat_khau": "123456"}, follow_redirects=True)

        res_post_skill = self.client.get("/skills/new", follow_redirects=True)
        html_skill = res_post_skill.data.decode("utf-8")
        self.assertIn("hàng chờ duyệt", html_skill, "Tài khoản chờ duyệt không được đăng kỹ năng")

        res_book = self.client.post("/sessions/book", data={"skill_id": 1, "thoi_luong_gio": 1.0}, follow_redirects=True)
        html_book = res_book.data.decode("utf-8")
        self.assertIn("hàng chờ duyệt", html_book, "Tài khoản chờ duyệt không được đặt lịch")

        print("\n[PASS - TC 5]: Mã mời TBEDU-XXXX-XXXX và quy trình bảo vệ đăng ký hoạt động chuẩn xác.")

    # =========================================================================
    # TIÊU CHÍ 6: AI LỌC CHAT REALTIME & 3 MỨC VI PHẠM
    # =========================================================================
    def test_06_realtime_chat_moderation_and_violations(self):
        """[TIÊU CHÍ 6]: Gửi từ cấm trong chat -> chặn + bot nhắc nhở + ghi bảng violations 3 mức."""
        # Đăng xuất và đăng nhập học sinh HS12001
        self.client.get("/logout")
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)

        # Xóa vi phạm cũ của HS12001 nếu có
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        u_id = cur.fetchone()["id"]
        cur.execute("DELETE FROM violations WHERE user_id = ?", (u_id,))
        cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ?", (u_id,))
        db.commit()

        # Lần 1: Gửi từ thô tục trực tiếp
        res1 = self.client.post("/api/chat/send", json={"message": "Ê mày đồ ngu dốt chửi thề vãi lồn"})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1.get("is_violation"))
        self.assertEqual(data1.get("muc_do"), 1)
        self.assertIn("LẦN 1", data1.get("reply"))

        # Kiểm tra bảng violations có mức 1
        cur.execute("SELECT muc_do, mo_ta FROM violations WHERE user_id = ? ORDER BY id DESC LIMIT 1", (u_id,))
        v1 = cur.fetchone()
        self.assertEqual(v1["muc_do"], 1)

        # Lần 2: Gửi biến thể lách luật (v.c.l)
        res2 = self.client.post("/api/chat/send", json={"message": "Sao khó v.c.l thế này"})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertTrue(data2.get("is_violation"))
        self.assertEqual(data2.get("muc_do"), 2)
        self.assertIn("LẦN 2", data2.get("reply"))

        cur.execute("SELECT muc_do FROM violations WHERE user_id = ? ORDER BY id DESC LIMIT 1", (u_id,))
        v2 = cur.fetchone()
        self.assertEqual(v2["muc_do"], 2)

        # Lần 3: Gửi vi phạm lần thứ 3 -> Hệ thống ĐỀ XUẤT khóa (de_xuat_khoa), KHÔNG tự động khóa vĩnh viễn
        res3 = self.client.post("/api/chat/send", json={"message": "Đm bực mình quá rồi đấy"})
        self.assertEqual(res3.status_code, 200)
        data3 = res3.get_json()
        self.assertTrue(data3.get("is_violation"))
        self.assertEqual(data3.get("muc_do"), 3)
        self.assertIn("LẦN 3", data3.get("reply"))
        self.assertIn("ĐỀ XUẤT KHÓA TÀI KHOẢN", data3.get("reply"))

        cur.execute("SELECT trang_thai FROM users WHERE id = ?", (u_id,))
        u_status = cur.fetchone()["trang_thai"]
        self.assertEqual(u_status, "de_xuat_khoa", "Lần 3 chỉ chuyển sang 'de_xuat_khoa', chờ quản trị xác nhận")

        # Quản trị viên vào xác nhận khóa thật
        self.client.get("/logout")
        self.client.post("/login", data={"ma_hoc_sinh": "SUPER_ADMIN_TEST", "mat_khau": "admin123"}, follow_redirects=True)
        res_lock = self.client.post(f"/admin/confirm-lock-user/{u_id}", follow_redirects=True)
        self.assertEqual(res_lock.status_code, 200)

        cur.execute("SELECT trang_thai FROM users WHERE id = ?", (u_id,))
        self.assertEqual(cur.fetchone()["trang_thai"], "da_khoa", "Sau khi quản trị xác nhận mới khóa thật")

        # Khôi phục tài khoản học sinh về 'hoat_dong' để không ảnh hưởng test khác
        cur.execute("UPDATE users SET trang_thai = 'hoat_dong' WHERE id = ?", (u_id,))
        cur.execute("DELETE FROM violations WHERE user_id = ?", (u_id,))
        db.commit()

        print("\n[PASS - TC 6]: Lọc chat realtime và quy trình kỷ luật 3 mức hoạt động đúng quy tắc nhân văn.")

    # =========================================================================
    # TIÊU CHÍ 7: TRANG NỘI QUY (/noi-quy) & ĐỔI THƯƠNG HIỆU
    # =========================================================================
    def test_07_rules_page_and_brand_updates(self):
        """[TIÊU CHÍ 7]: Trang /noi-quy đủ 6 điều + chế tài; xóa UKA khỏi header/hero/footer; tiêu đề School Time Bank."""
        # 1. Kiểm tra trang /noi-quy
        res_rules = self.client.get("/noi-quy")
        self.assertEqual(res_rules.status_code, 200)
        html_rules = res_rules.data.decode("utf-8")

        # 6 điều quy tắc vàng
        self.assertIn("Trung thực", html_rules)
        self.assertIn("Trang phục", html_rules)
        self.assertIn("Ngôn ngữ", html_rules)
        self.assertIn("Lành mạnh", html_rules)
        self.assertIn("Công bằng", html_rules)
        self.assertIn("Tôn trọng", html_rules)

        # Chế tài xử lý
        self.assertIn("Lần 1 — Nhắc nhở", html_rules)
        self.assertIn("Lần 2 — Cảnh cáo", html_rules)
        self.assertIn("Lần 3 — Đưa ra khỏi lớp học và khóa tài khoản vĩnh viễn", html_rules)

        # 2. Kiểm tra link /noi-quy ở navbar và footer
        res_home = self.client.get("/")
        html_home = res_home.data.decode("utf-8")
        self.assertIn('href="/noi-quy"', html_home, "Phải có link /noi-quy trong navbar hoặc footer")

        # 3. Tiêu đề chính giữa trang: School Time Bank + Ngân hàng Thời gian Học đường
        self.assertIn("School Time Bank", html_home)
        self.assertIn("Ngân hàng Thời gian Học đường", html_home)

        # 4. Kiểm tra xóa UKA khỏi header, hero, footer, title
        # Lưu ý: Chỉ GIỮ trong danh sách trường tham gia (#nha-truong)
        parts = html_home.split('<section id="nha-truong"')
        header_hero_part = parts[0]
        after_schools_part = parts[1].split('</section>')[1] if len(parts) > 1 else ""

        self.assertNotIn("UKA Academy", header_hero_part, "Header & Hero không được chứa UKA Academy")
        self.assertNotIn("UKA Academy", after_schools_part, "Footer không được chứa UKA Academy")

        # 5. Badge AI xóa khỏi header/footer, giữ ở giữa trang
        self.assertNotIn('<span class="badge-ai">', header_hero_part[:500], "Header không được chứa badge AI")
        self.assertIn("Trí tuệ nhân tạo", html_home, "Trang chủ phải giữ nhãn AI ở phần giữa trang")

        print("\n[PASS - TC 7]: Trang /noi-quy đầy đủ 6 điều, thương hiệu School Time Bank trang trọng.")

    # =========================================================================
    # TIÊU CHÍ 8: PHÒNG HỌC ẢO CÓ NÚT BÁO CÁO VI PHẠM
    # =========================================================================
    def test_08_virtual_room_report_violation(self):
        """[TIÊU CHÍ 8]: Học sinh có nút Báo cáo trong phòng học ảo gửi vi phạm cho giáo viên/quản trị."""
        # Đăng nhập học sinh HS11002 vào phòng học của phiên 1
        self.client.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)
        res_room = self.client.get("/sessions/1/room")
        self.assertEqual(res_room.status_code, 200)
        html_room = res_room.data.decode("utf-8")

        # Nút báo cáo và modal báo cáo tồn tại
        self.assertIn("Báo cáo vi phạm", html_room)
        self.assertIn("reportViolationModal", html_room)

        # Gửi báo cáo vi phạm
        res_rep = self.client.post("/sessions/1/report", data={
            "loai_vi_pham": "ngon_tu_khong_chuan_muc",
            "mo_ta": "Bạn học bật mic nói từ ngữ không phù hợp trong lúc giải bài."
        }, follow_redirects=True)
        self.assertEqual(res_rep.status_code, 200)

        # Xác minh bản ghi lưu vào violations
        db = get_db()
        cur = db.cursor()
        cur.execute("SELECT loai_vi_pham, mo_ta FROM violations WHERE loai_vi_pham = 'ngon_tu_khong_chuan_muc' ORDER BY id DESC LIMIT 1")
        v_rep = cur.fetchone()
        self.assertIsNotNone(v_rep)
        self.assertIn("nói từ ngữ không phù hợp", v_rep["mo_ta"])

        print("\n[PASS - TC 8]: Nút Báo cáo phòng học ảo gửi thông tin vi phạm lên giáo viên thành công.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
