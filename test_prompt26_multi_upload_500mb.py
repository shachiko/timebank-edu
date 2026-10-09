# -*- coding: utf-8 -*-
"""
TEST SUITE PROMPT 26: UPLOAD NHIỀU FILE + NÂNG GIỚI HẠN LÊN 500MB
Nghiệm thu:
1. Chọn 3 file -> tải 1 lần -> cả 3 lên Drive.
2. File quá 500MB -> bị từ chối với thông báo rõ ràng.
3. File 200-500MB tải thành công không timeout.
4. Để trống tiêu đề -> lấy tên file. Điền tiêu đề -> dùng làm tiền tố.
5. Cấu hình gunicorn timeout 300s và MAX_CONTENT_LENGTH 500MB.
"""
import io
import os
import sys
import uuid
import tempfile
import unittest
from unittest.mock import patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from app import app, get_db, init_db

class TestPrompt26MultiUpload500MB(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def setUp(self):
        self.client = app.test_client()
        with self.client.session_transaction() as sess:
            sess["user_id"] = 1
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Kiểm thử"
        self.uid = uuid.uuid4().hex[:6]

    # =========================================================================
    # TIÊU CHÍ 1: CHỌN 3 FILE -> TẢI 1 LẦN -> CẢ 3 LÊN DRIVE
    # =========================================================================
    def test_01_upload_multiple_files_batch_success(self):
        """[TIÊU CHÍ 1]: Chọn 3 file -> tải 1 lần -> cả 3 file được lưu vào documents."""
        fn1 = f"tailieu_{self.uid}_1.pdf"
        fn2 = f"tailieu_{self.uid}_2.pdf"
        fn3 = f"tailieu_{self.uid}_3.pdf"

        file1 = (io.BytesIO(b"%PDF-1.4 File 1 Content"), fn1)
        file2 = (io.BytesIO(b"%PDF-1.4 File 2 Content"), fn2)
        file3 = (io.BytesIO(b"%PDF-1.4 File 3 Content"), fn3)

        res = self.client.post("/documents/upload", data={
            "mon_hoc": "Toán",
            "tieu_de": "Tài liệu Toán đợt 1",
            "mo_ta": "Mô tả bộ 3 tài liệu",
            "files": [file1, file2, file3]
        }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")

        # Kiểm tra thông báo có tổng kết số lượng thành công (3/3)
        self.assertIn("3/3", html)
        self.assertIn("thành công", html)

        # Kiểm tra CSDL xem cả 3 file đã được lưu chưa
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("""
                SELECT tieu_de, file_name FROM documents 
                WHERE file_name IN (?, ?, ?)
            """, (fn1, fn2, fn3))
            rows = cur.fetchall()
            self.assertEqual(len(rows), 3, "Phải có đủ 3 bản ghi documents được tạo!")
            for row in rows:
                self.assertTrue(row["tieu_de"].startswith("Tài liệu Toán đợt 1 - "))

    # =========================================================================
    # TIÊU CHÍ 2: FILE QUÁ 500MB -> BỊ TỪ CHỐI VỚI THÔNG BÁO RÕ RÀNG
    # =========================================================================
    def test_02_oversized_file_rejected_over_500mb(self):
        """[TIÊU CHÍ 2]: Tệp có dung lượng > 500MB bị từ chối và báo rõ ràng."""
        fn_huge = f"video_{self.uid}_505mb.mp4"
        file_mock = (io.BytesIO(b"Simulated oversized payload"), fn_huge)

        with patch("tempfile.SpooledTemporaryFile.tell", return_value=505 * 1024 * 1024):
            res = self.client.post("/documents/upload", data={
                "mon_hoc": "Vật lý",
                "tieu_de": "Video bài giảng siêu nặng",
                "files": [file_mock]
            }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("500MB", html)
        self.assertIn("vượt quá dung lượng tối đa cho phép", html)

        # Đảm bảo không tạo bản ghi trong DB
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) as cnt FROM documents WHERE file_name = ?", (fn_huge,))
            count = cur.fetchone()["cnt"]
            self.assertEqual(count, 0, "File quá 500MB không được phép lưu vào DB!")

    # =========================================================================
    # TIÊU CHÍ 3: FILE 200MB - 500MB TẢI THÀNH CÔNG
    # =========================================================================
    def test_03_file_between_200mb_and_500mb_allowed(self):
        """[TIÊU CHÍ 3]: Tệp dung lượng 350MB (nằm giữa 200MB và 500MB) tải lên thành công."""
        fn_350 = f"baigiang_{self.uid}_350mb.zip"
        file_mock = (io.BytesIO(b"Simulated 350MB file content"), fn_350)

        with patch("tempfile.SpooledTemporaryFile.tell", return_value=350 * 1024 * 1024):
            res = self.client.post("/documents/upload", data={
                "mon_hoc": "Hóa học",
                "tieu_de": "Gói tài nguyên Hóa 12",
                "files": [file_mock]
            }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("thành công", html)

        # Kiểm tra file đã được lưu với đúng dung lượng 350MB
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT file_size FROM documents WHERE file_name = ? ORDER BY id DESC LIMIT 1", (fn_350,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["file_size"], 350 * 1024 * 1024)

    # =========================================================================
    # TIÊU CHÍ 4: ĐỂ TRỐNG TIÊU ĐỀ -> LẤY TÊN FILE; ĐIỀN TIÊU ĐỀ -> LÀM TIỀN TỐ
    # =========================================================================
    def test_04_title_optional_and_prefix_behavior(self):
        """[TIÊU CHÍ 4]: Để trống tiêu đề -> lấy tên file; Điền tiêu đề -> làm tiền tố chung."""
        fn_notitle = f"dethi_{self.uid}.docx"
        file_no_title = (io.BytesIO(b"Content A"), fn_notitle)
        res1 = self.client.post("/documents/upload", data={
            "mon_hoc": "Tiếng Anh",
            "tieu_de": "",  # Để trống
            "files": [file_no_title]
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT tieu_de FROM documents WHERE file_name = ? ORDER BY id DESC LIMIT 1", (fn_notitle,))
            row = cur.fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["tieu_de"], fn_notitle, "Để trống tiêu đề phải lấy đúng tên file!")

        # 2. Điền tiêu đề -> Dùng làm tiền tố chung cho nhiều file
        fn_m1 = f"baitap_{self.uid}_1.pdf"
        fn_m2 = f"baitap_{self.uid}_2.pdf"
        f_multi1 = (io.BytesIO(b"Data 1"), fn_m1)
        f_multi2 = (io.BytesIO(b"Data 2"), fn_m2)

        res2 = self.client.post("/documents/upload", data={
            "mon_hoc": "Sinh học",
            "tieu_de": "[Chuyên đề Di truyền]",
            "files": [f_multi1, f_multi2]
        }, content_type="multipart/form-data", follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT tieu_de, file_name FROM documents WHERE file_name IN (?, ?)", (fn_m1, fn_m2))
            rows = cur.fetchall()
            self.assertEqual(len(rows), 2)
            for r in rows:
                self.assertEqual(r["tieu_de"], f"[Chuyên đề Di truyền] - {r['file_name']}")

    # =========================================================================
    # TIÊU CHÍ 5: FILE LỖI BỎ QUA -> TIẾP TỤC FILE KHÁC -> BÁO TỔNG KẾT
    # =========================================================================
    def test_05_partial_failure_continues_others(self):
        """[TIÊU CHÍ 5]: 1 file lỗi (>500MB) bị bỏ qua, các file khác vẫn tải thành công -> Báo tổng kết X/Y."""
        fn_ok1 = f"ok_{self.uid}_1.pdf"
        fn_bad = f"bad_{self.uid}_600mb.pdf"
        fn_ok2 = f"ok_{self.uid}_2.pdf"

        f_ok1 = (io.BytesIO(b"Good 1"), fn_ok1)
        f_bad = (io.BytesIO(b"Bad"), fn_bad)
        f_ok2 = (io.BytesIO(b"Good 2"), fn_ok2)

        real_tell = tempfile.SpooledTemporaryFile.tell
        def mocked_tell(obj):
            # Nếu tên file liên quan đến fn_bad thì báo 600MB
            val = real_tell(obj)
            # Dùng call counter hoặc kiểm tra
            return val

        # Hoặc dùng side_effect list cho 3 lần gọi tell():
        # Lần 1: 1024, Lần 2: 600MB, Lần 3: 1024
        with patch("tempfile.SpooledTemporaryFile.tell", side_effect=[1024, 600 * 1024 * 1024, 1024]):
            res = self.client.post("/documents/upload", data={
                "mon_hoc": "Lịch sử",
                "tieu_de": "Tài liệu Sử 11",
                "files": [f_ok1, f_bad, f_ok2]
            }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        # Phải báo tổng kết 2/3 thành công
        self.assertIn("2/3", html)
        self.assertIn("bị bỏ qua", html)

        # Kiểm tra DB: file 1 và file 2 thành công, file bad không có
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT file_name FROM documents WHERE file_name IN (?, ?, ?)", (fn_ok1, fn_bad, fn_ok2))
            saved = [r["file_name"] for r in cur.fetchall()]
            self.assertIn(fn_ok1, saved)
            self.assertIn(fn_ok2, saved)
            self.assertNotIn(fn_bad, saved)

    # =========================================================================
    # TIÊU CHÍ 6: KIỂM TRA CẤU HÌNH MAX_CONTENT_LENGTH, RENDER.YAML VÀ PROCFILE
    # =========================================================================
    def test_06_configuration_and_templates_500mb(self):
        """[TIÊU CHÍ 6]: Cấu hình 500MB và timeout 300s trong hệ thống."""
        # 1. app.config MAX_CONTENT_LENGTH = 500MB
        self.assertEqual(app.config["MAX_CONTENT_LENGTH"], 500 * 1024 * 1024)

        # 2. render.yaml có --timeout 300
        render_yaml_path = os.path.join(os.path.dirname(__file__), "render.yaml")
        with open(render_yaml_path, "r", encoding="utf-8") as f:
            yaml_content = f.read()
        self.assertIn("--timeout 300", yaml_content)

        # 3. Procfile có --timeout 300
        procfile_path = os.path.join(os.path.dirname(__file__), "Procfile")
        with open(procfile_path, "r", encoding="utf-8") as f:
            proc_content = f.read()
        self.assertIn("--timeout 300", proc_content)

        # 4. Giao diện documents_upload.html có multiple và 500MB
        html_path = os.path.join(os.path.dirname(__file__), "templates", "documents_upload.html")
        with open(html_path, "r", encoding="utf-8") as f:
            tpl_content = f.read()
        self.assertIn("multiple", tpl_content)
        self.assertIn("500MB", tpl_content)
        self.assertIn("selectedFilesContainer", tpl_content)


if __name__ == "__main__":
    unittest.main()
