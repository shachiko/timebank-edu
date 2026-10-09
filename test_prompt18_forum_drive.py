# -*- coding: utf-8 -*-
"""
BỘ TEST TOÀN DIỆN CHO PROMPT 18:
1. Diễn đàn "Góc trò chuyện": Phân lập trường học (truong_id), AI lọc từ tục & ghi violations, Khóa & Xóa chủ đề/bình luận.
2. Kho tài liệu Google Drive 5TB: Phân cấp thư mục /SchoolTimeBank/{ten_truong}/{mon_hoc}/, Stream tải lên/tải về, Báo cáo & Xóa vi phạm, Log lượt tải.
3. Kiểm tra bảo mật: Không hardcode bất kỳ credential/refresh_token nào trong code & git.
"""

import os
import io
import unittest
import sqlite3
from pathlib import Path
from app import app, init_db
from drive_service import is_google_drive_configured, upload_document_stream, download_document_stream


class TestPrompt18ForumAndDrive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        init_db()

    def get_db(self):
        conn = sqlite3.connect("database/timebank.db", timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def execute_db(self, query, args=()):
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            conn.commit()
            return cur.lastrowid

    def query_db(self, query, args=(), one=False):
        with self.get_db() as conn:
            cur = conn.cursor()
            cur.execute(query, args)
            rv = cur.fetchall()
            return (rv[0] if rv else None) if one else rv

    def setUp(self):
        self.client = app.test_client()

        # Đảm bảo trường 1 và 2 tồn tại
        schools = self.query_db("SELECT id FROM truong WHERE id IN (1, 2)")
        if len(schools) < 2:
            self.execute_db("INSERT OR IGNORE INTO truong (id, ten_truong, trang_thai) VALUES (1, 'Trường UK Academy', 'dang_thi_diem')")
            self.execute_db("INSERT OR IGNORE INTO truong (id, ten_truong, trang_thai) VALUES (2, 'Trường THCS Nguyễn Văn Thuộc', 'chuan_bi_trien_khai')")

        # Học sinh trường 1
        r1 = self.query_db("SELECT id FROM users WHERE ma_hoc_sinh = 'HS_P18_T1'", one=True)
        if not r1:
            self.user1_id = self.execute_db("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, so_du_gio, trang_thai)
                VALUES ('HS_P18_T1', 'Học sinh Trường Một', 'hash', 'hoc_sinh', 1, 5.0, 'hoat_dong')
            """)
        else:
            self.user1_id = r1["id"]

        # Học sinh trường 2
        r2 = self.query_db("SELECT id FROM users WHERE ma_hoc_sinh = 'HS_P18_T2'", one=True)
        if not r2:
            self.user2_id = self.execute_db("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, so_du_gio, trang_thai)
                VALUES ('HS_P18_T2', 'Học sinh Trường Hai', 'hash', 'hoc_sinh', 2, 5.0, 'hoat_dong')
            """)
        else:
            self.user2_id = r2["id"]

        # Giáo viên trường 1
        rgv = self.query_db("SELECT id FROM users WHERE ma_hoc_sinh = 'GV_P18_T1'", one=True)
        if not rgv:
            self.teacher1_id = self.execute_db("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, so_du_gio, trang_thai)
                VALUES ('GV_P18_T1', 'Thầy giáo Trường Một', 'hash', 'giao_vien', 1, 10.0, 'hoat_dong')
            """)
        else:
            self.teacher1_id = rgv["id"]

        # Super admin
        rsa = self.query_db("SELECT id FROM users WHERE ma_hoc_sinh = 'SA_P18'", one=True)
        if not rsa:
            self.super_id = self.execute_db("""
                INSERT INTO users (ma_hoc_sinh, ho_ten, mat_khau, vai_tro, truong_id, so_du_gio, trang_thai)
                VALUES ('SA_P18', 'Tổng quản trị P18', 'hash', 'super_admin', 1, 100.0, 'hoat_dong')
            """)
        else:
            self.super_id = rsa["id"]

    # --------------------------------------------------------------------------
    # PHẦN 1: DIỄN ĐÀN "GÓC TRÒ CHUYỆN"
    # --------------------------------------------------------------------------
    def test_01_forum_create_topic_and_reply(self):
        """Học sinh trường 1 tạo chủ đề và bình luận thành công."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Trường Một"

        # 1. Tạo chủ đề
        resp = self.client.post("/forum/new", data={
            "tieu_de": "Hỏi cách giải phương trình vi phân bậc hai",
            "noi_dung": "Chào mọi người, có bạn nào biết mẹo giải nhanh bài tập toán này không?"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Hỏi cách giải phương trình vi phân bậc hai".encode("utf-8"), resp.data)

        # Lấy topic_id vừa tạo
        topic = self.query_db("SELECT id FROM forum_topics WHERE tieu_de = ? ORDER BY id DESC LIMIT 1", 
                              ("Hỏi cách giải phương trình vi phân bậc hai",), one=True)
        self.assertIsNotNone(topic)
        topic_id = topic["id"]

        # 2. Gửi bình luận
        reply_resp = self.client.post(f"/forum/topic/{topic_id}/reply", data={
            "noi_dung": "Bạn hãy dùng phương pháp biến thiên hằng số hoặc định lý nghiệm đặc trưng nhé!"
        }, follow_redirects=True)
        self.assertEqual(reply_resp.status_code, 200)
        self.assertIn("phương pháp biến thiên hằng số".encode("utf-8"), reply_resp.data)

    def test_02_forum_school_isolation(self):
        """Mỗi trường chỉ thấy diễn đàn của trường mình; trường khác không thấy."""
        # Tạo chủ đề cho trường 1
        topic1_id = self.execute_db("""
            INSERT INTO forum_topics (truong_id, user_id, tieu_de, noi_dung, trang_thai, ngay_tao)
            VALUES (1, ?, 'Chủ đề bí mật Trường 1', 'Nội dung trường 1', 'mo', CURRENT_TIMESTAMP)
        """, (self.user1_id,))

        # Đăng nhập bằng học sinh Trường 2
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user2_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 2
            sess["ho_ten"] = "Học sinh Trường Hai"

        # Kiểm tra danh sách diễn đàn: KHÔNG được thấy chủ đề trường 1
        resp = self.client.get("/forum")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("Chủ đề bí mật Trường 1".encode("utf-8"), resp.data)

        # Cố tình truy cập trực tiếp URL của topic trường 1: Bị chặn và redirect
        resp_direct = self.client.get(f"/forum/topic/{topic1_id}", follow_redirects=True)
        self.assertIn("không có quyền xem diễn đàn của trường khác".encode("utf-8"), resp_direct.data)

    def test_03_forum_ai_profanity_moderation_and_violations(self):
        """AI chặn từ ngữ thô tục trong Tiêu đề và Bình luận, ghi nhận vào violations."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Trường Một"

        # Đếm violations ban đầu
        cnt_before = self.query_db("SELECT COUNT(*) FROM violations WHERE user_id = ?", (self.user1_id,), one=True)[0]

        # 1. Thử tạo chủ đề chứa từ tục
        resp_bad_topic = self.client.post("/forum/new", data={
            "tieu_de": "Bài giảng này như đm vậy các bạn",
            "noi_dung": "Thực sự quá vcl luôn"
        }, follow_redirects=True)
        self.assertIn("bị AI từ chối đăng do vi phạm quy chuẩn ngôn ngữ".encode("utf-8"), resp_bad_topic.data)

        # Kiểm tra bảng violations đã tăng lên
        cnt_after = self.query_db("SELECT COUNT(*) FROM violations WHERE user_id = ?", (self.user1_id,), one=True)[0]
        self.assertGreater(cnt_after, cnt_before)

        # 2. Thử bình luận chứa từ tục trên chủ đề hợp lệ
        clean_topic_id = self.execute_db("""
            INSERT INTO forum_topics (truong_id, user_id, tieu_de, noi_dung, trang_thai)
            VALUES (1, ?, 'Chủ đề bình thường', 'Nội dung bình thường', 'mo')
        """, (self.user1_id,))

        resp_bad_reply = self.client.post(f"/forum/topic/{clean_topic_id}/reply", data={
            "noi_dung": "Mẹ mày ngu như chó ấy mà cũng hỏi"
        }, follow_redirects=True)
        self.assertIn("Bình luận bị AI chặn do vi phạm quy chuẩn ngôn ngữ".encode("utf-8"), resp_bad_reply.data)

        # Kiểm tra bình luận KHÔNG được lưu vào forum_replies
        replies_count = self.query_db("SELECT COUNT(*) FROM forum_replies WHERE topic_id = ?", (clean_topic_id,), one=True)[0]
        self.assertEqual(replies_count, 0)

    def test_04_forum_lock_and_delete_permissions(self):
        """Giáo viên có quyền Khóa chủ đề (ngăn bình luận) và Xóa bài viết vi phạm."""
        # Tạo chủ đề trường 1
        topic_id = self.execute_db("""
            INSERT INTO forum_topics (truong_id, user_id, tieu_de, noi_dung, trang_thai)
            VALUES (1, ?, 'Chủ đề sắp bị khóa', 'Nội dung', 'mo')
        """, (self.user1_id,))

        # Đăng nhập bằng Giáo viên trường 1
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.teacher1_id
            sess["vai_tro"] = "giao_vien"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Thầy giáo Trường Một"

        # Khóa chủ đề
        resp_lock = self.client.post(f"/forum/topic/{topic_id}/toggle-lock", follow_redirects=True)
        self.assertEqual(resp_lock.status_code, 200)

        status = self.query_db("SELECT trang_thai FROM forum_topics WHERE id = ?", (topic_id,), one=True)["trang_thai"]
        self.assertEqual(status, "khoa")

        # Đăng nhập lại học sinh: thử bình luận vào chủ đề đã khóa -> Bị từ chối
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_reply_locked = self.client.post(f"/forum/topic/{topic_id}/reply", data={
            "noi_dung": "Cố tình bình luận vào chủ đề đã khóa"
        }, follow_redirects=True)
        self.assertIn("Chủ đề này đã bị khóa bình luận".encode("utf-8"), resp_reply_locked.data)

        # Giáo viên xóa chủ đề
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.teacher1_id
            sess["vai_tro"] = "giao_vien"
            sess["truong_id"] = 1

        resp_delete = self.client.post(f"/forum/topic/{topic_id}/delete", follow_redirects=True)
        self.assertEqual(resp_delete.status_code, 200)

        cnt = self.query_db("SELECT COUNT(*) FROM forum_topics WHERE id = ?", (topic_id,), one=True)[0]
        self.assertEqual(cnt, 0)

    # --------------------------------------------------------------------------
    # PHẦN 2: KHO TÀI LIỆU GOOGLE DRIVE 5TB
    # --------------------------------------------------------------------------
    def test_05_drive_upload_stream_and_hierarchy(self):
        """Học sinh tải lên file (<=500MB); nằm đúng thư mục /SchoolTimeBank/{ten_truong}/{mon_hoc}/."""
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1
            sess["ho_ten"] = "Học sinh Trường Một"

        fake_file_content = b"%PDF-1.4 Fake Math Exam for School 1 on Google Drive 5TB storage"
        file_storage = (io.BytesIO(fake_file_content), "de_thi_toan_giua_ky.pdf")

        resp_upload = self.client.post("/documents/upload", data={
            "mon_hoc": "Toán",
            "tieu_de": "Đề thi thử giữa kỳ 1 môn Toán khối 10",
            "mo_ta": "Đề thi thử gồm 50 câu trắc nghiệm chuẩn Bộ GD&ĐT",
            "file": file_storage
        }, content_type="multipart/form-data", follow_redirects=True)

        self.assertEqual(resp_upload.status_code, 200)
        self.assertIn("Đề thi thử giữa kỳ 1 môn Toán khối 10".encode("utf-8"), resp_upload.data)

        # Kiểm tra trong cơ sở dữ liệu
        doc = self.query_db("SELECT * FROM documents WHERE tieu_de = ? ORDER BY id DESC LIMIT 1",
                            ("Đề thi thử giữa kỳ 1 môn Toán khối 10",), one=True)
        self.assertIsNotNone(doc)
        self.assertEqual(doc["truong_id"], 1)
        self.assertEqual(doc["mon_hoc"], "Toán")
        self.assertEqual(doc["user_id"], self.user1_id)
        self.assertTrue(len(doc["drive_file_id"]) > 0)

    def test_06_drive_stream_download_and_counter(self):
        """Tải về file: stream trực tiếp từ Drive và tăng lượt tải (luot_tai)."""
        stream = io.BytesIO(b"Hello from Google Drive 5TB Stream Content!")
        res = upload_document_stream(stream, "bai_giang_ly.pdf", "application/pdf", "UK Academy", "Vật lý")
        
        doc_id = self.execute_db("""
            INSERT INTO documents (truong_id, user_id, tieu_de, mo_ta, mon_hoc, file_name, file_size, file_type, drive_file_id, luot_tai, trang_thai)
            VALUES (1, ?, 'Slide Bài giảng Vật lý 10', 'Chuyển động thẳng đều', 'Vật lý', 'bai_giang_ly.pdf', 1024, 'application/pdf', ?, 0, 'hoat_dong')
        """, (self.user1_id, res["file_id"]))

        # Học sinh trường 1 tải về
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_dl = self.client.get(f"/documents/download/{doc_id}")
        self.assertEqual(resp_dl.status_code, 200)
        self.assertIn(b"Hello from Google Drive 5TB Stream Content!", resp_dl.data)

        # Kiểm tra số lượt tải tăng lên 1
        luot_tai = self.query_db("SELECT luot_tai FROM documents WHERE id = ?", (doc_id,), one=True)["luot_tai"]
        self.assertEqual(luot_tai, 1)

        # Kiểm tra nhật ký document_downloads
        dl_cnt = self.query_db("SELECT COUNT(*) FROM document_downloads WHERE document_id = ? AND user_id = ?", 
                               (doc_id, self.user1_id), one=True)[0]
        self.assertEqual(dl_cnt, 1)

    def test_07_drive_report_and_admin_delete(self):
        """Báo cáo tài liệu vi phạm ghi vào violations; Quản trị viên xóa được file khỏi Drive & DB."""
        doc_id = self.execute_db("""
            INSERT INTO documents (truong_id, user_id, tieu_de, mo_ta, mon_hoc, file_name, file_size, file_type, drive_file_id, trang_thai)
            VALUES (1, ?, 'Tài liệu bị nghi ngờ bản quyền', 'Mô tả', 'Toán', 'doc_violate.pdf', 500, 'application/pdf', 'mock_id_viol', 'hoat_dong')
        """, (self.user1_id,))

        # Học sinh báo cáo
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 1

        resp_rep = self.client.post(f"/documents/report/{doc_id}", data={
            "ly_do": "Tài liệu sao chép trái phép đề cương trường khác"
        }, follow_redirects=True)
        self.assertEqual(resp_rep.status_code, 200)

        # Kiểm tra violations có bản ghi 'bao_cao_tai_lieu'
        viol = self.query_db("SELECT * FROM violations WHERE loai_vi_pham = 'bao_cao_tai_lieu' AND user_id = ?", (self.user1_id,), one=True)
        self.assertIsNotNone(viol)

        # Thầy giáo / Admin xóa file
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.teacher1_id
            sess["vai_tro"] = "giao_vien"
            sess["truong_id"] = 1

        resp_del = self.client.post(f"/documents/delete/{doc_id}", follow_redirects=True)
        self.assertEqual(resp_del.status_code, 200)

        # File đã đổi trạng thái 'da_xoa'
        st = self.query_db("SELECT trang_thai FROM documents WHERE id = ?", (doc_id,), one=True)["trang_thai"]
        self.assertEqual(st, "da_xoa")

    def test_08_drive_school_isolation(self):
        """Học sinh trường 2 không thấy và không tải được tài liệu của trường 1."""
        doc_id = self.execute_db("""
            INSERT INTO documents (truong_id, user_id, tieu_de, mo_ta, mon_hoc, file_name, file_size, file_type, drive_file_id, trang_thai)
            VALUES (1, ?, 'Tài liệu riêng của trường UK Academy', 'Bí mật', 'Hóa học', 'secret.pdf', 100, 'application/pdf', 'mock_sec_1', 'hoat_dong')
        """, (self.user1_id,))

        # Đăng nhập học sinh trường 2
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user2_id
            sess["vai_tro"] = "hoc_sinh"
            sess["truong_id"] = 2

        # Không thấy trong danh sách
        resp_list = self.client.get("/documents")
        self.assertNotIn("Tài liệu riêng của trường UK Academy".encode("utf-8"), resp_list.data)

        # Không tải được
        resp_dl = self.client.get(f"/documents/download/{doc_id}", follow_redirects=True)
        self.assertIn("không có quyền tải tài liệu của trường khác".encode("utf-8"), resp_dl.data)

    def test_09_security_zero_credentials_audit(self):
        """Kiểm tra tuyệt đối không có refresh_token, client_secret hay token hardcode trong code."""
        import glob
        pattern_prefix = "1/" + "/0"
        suspect_patterns = [
            pattern_prefix, "ya29.", "GOCSPX-", "client_secret = \"", "refresh_token = \""
        ]
        
        py_files = [f for f in glob.glob("*.py") if not f.startswith("test_")] + glob.glob("database/*.sql")
        for fpath in py_files:
            with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for pat in suspect_patterns:
                    self.assertNotIn(pat, content, f"Phát hiện nguy cơ credential trong file {fpath}: '{pat}'")


if __name__ == "__main__":
    unittest.main()
