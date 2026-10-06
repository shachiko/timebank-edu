# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M-AI+
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Nội dung kiểm thử:
1. Tạo quiz AI 5 câu giọng vui nhộn từ dàn ý + mô tả, lưu vào quiz_questions, ghi vết ai_logs.
2. Tự đánh giá mức độ tự tin trước buổi học (1-5 sao) và lưu tu_danh_gia_truoc.
3. Người học làm quiz trong app, chấm tự động, đạt >=60% -> sessions.quiz_dat_chuan = 1.
4. CHẶN LÀM LẦN 2 (Mỗi học sinh chỉ được làm bài 1 lần duy nhất).
5. Dashboard Admin / Giáo viên hiển thị khối "Kết quả học tập" đầy đủ các chỉ số:
   - Điểm TB theo môn
   - % đạt >= 4/5
   - % phiên đạt chuẩn quiz
   - So sánh tự đánh giá trước vs điểm sau.
6. Nguyên tắc sư phạm: Quiz chỉ để xác nhận kết quả, KHÔNG chặn việc chuyển giờ tín dụng.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import unittest
import sqlite3
from pathlib import Path

# Đảm bảo đường dẫn import app
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app, init_db, DATABASE_PATH, get_db
from ai_service import ai_generate_quiz


class TestMilestoneAIPlus(unittest.TestCase):
    def setUp(self):
        """Khởi tạo môi trường kiểm thử với test client và nạp lại CSDL sạch"""
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

        # Tạo lại cơ sở dữ liệu mẫu ban đầu
        if DATABASE_PATH.exists():
            DATABASE_PATH.unlink()
        init_db()

    def login(self, username, password="admin123"):
        """Hàm trợ giúp đăng nhập"""
        self.client.get("/logout", follow_redirects=True)
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def test_01_ai_generate_quiz_logic_and_log(self):
        """
        [TEST CASE 1]: Người dạy bấm 'Nhờ AI tạo quiz'
        - Sinh 5 câu trắc nghiệm 4 lựa chọn (dễ -> khó, tiếng Việt, giọng vui vẻ khích lệ)
        - Lưu vào bảng quiz_questions
        - Ghi nhật ký minh bạch vào ai_logs (chuc_nang = 'tao_quiz')
        """
        print("\n--- TEST CASE 1: Kiểm thử sinh Quiz AI 5 câu và ghi ai_logs ---")
        with app.app_context():
            db = get_db()
            # Session 4 là phiên An dạy Toán cho Minh (trạng thái hoan_thanh)
            questions, is_live = ai_generate_quiz(
                db=db,
                user_id=3, # An (người dạy)
                session_id=4,
                tieu_de="Góc giữa đường thẳng và mặt phẳng trong không gian",
                linh_vuc="Toán học",
                mo_ta="Phương pháp xác định hình chiếu vuông góc và công thức sin góc",
                dan_y_ai="Bước 1: Nhắc lại định nghĩa hình chiếu; Bước 2: 3 bài toán mẫu"
            )

            # Kiểm tra số lượng câu hỏi sinh ra
            self.assertEqual(len(questions), 5, "AI phải sinh chính xác 5 câu hỏi trắc nghiệm!")
            
            # Kiểm tra cấu trúc câu hỏi
            for idx, q in enumerate(questions, 1):
                self.assertIn("cau_hoi", q)
                self.assertIn("lua_chon_a", q)
                self.assertIn("lua_chon_b", q)
                self.assertIn("lua_chon_c", q)
                self.assertIn("lua_chon_d", q)
                self.assertIn(q["dap_an_dung"], ["A", "B", "C", "D"], f"Đáp án câu {idx} phải là A, B, C hoặc D")
                self.assertTrue(len(q["cau_hoi"]) > 5, "Câu hỏi không được rỗng")

            # Kiểm tra dữ liệu đã lưu vào database quiz_questions
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM quiz_questions WHERE session_id = 4")
            db_count = cur.fetchone()[0]
            self.assertEqual(db_count, 5, "Database phải lưu đủ 5 câu hỏi cho session 4")

            # Kiểm tra ghi vết vào ai_logs
            cur.execute("SELECT * FROM ai_logs WHERE chuc_nang = 'tao_quiz' ORDER BY id DESC LIMIT 1")
            ai_log = cur.fetchone()
            self.assertIsNotNone(ai_log, "Phải ghi nhật ký vào ai_logs với chuc_nang = 'tao_quiz'")
            self.assertIn("Toán học", ai_log["input_tom_tat"])
            print("  -> Đã sinh 5 câu trắc nghiệm thành công. Database lưu 5 câu, ghi vết ai_logs chuẩn xác.")

    def test_02_ai_quiz_route_and_permissions(self):
        """
        [TEST CASE 2]: Endpoint POST /sessions/<id>/ai-generate-quiz
        - Phân quyền: Người ngoài cuộc không được tạo quiz
        - Người dạy được tạo quiz sau khi phiên hoàn thành
        """
        print("\n--- TEST CASE 2: Kiểm thử route tạo Quiz và phân quyền ---")
        # 1. Đăng nhập học sinh không liên quan (Chi - user_id=5) cố tạo quiz cho session 4
        self.login("HS10003")
        res = self.client.post("/sessions/4/ai-generate-quiz", follow_redirects=True)
        self.assertIn("Chỉ bạn gia sư".encode("utf-8"), res.data)

        # 2. Đăng nhập đúng người dạy của session 4 (An - HS12001)
        self.login("HS12001")
        res = self.client.post("/sessions/4/ai-generate-quiz", follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            "Trợ lý AI".encode("utf-8") in res.data or "Đã khởi tạo bộ 5 câu hỏi".encode("utf-8") in res.data,
            "Phải có thông báo flash tạo quiz thành công"
        )
        print("  -> Phân quyền và tạo quiz qua route hoạt động an toàn, chính xác.")

    def test_03_quiz_submission_pre_assessment_and_pass_standard(self):
        """
        [TEST CASE 3]: Người học làm quiz trong app:
        - Chọn tự đánh giá trước (1-5 sao)
        - Làm đúng >= 60% (>= 3/5 câu) -> cập nhật sessions.quiz_dat_chuan = 1
        - Lưu đúng tu_danh_gia_truoc và diem_so trong quiz_results
        """
        print("\n--- TEST CASE 3: Học sinh tự đánh giá trước & làm quiz đạt chuẩn (>=60%) ---")
        # Tạo quiz cho Session 4 (An dạy Toán cho Minh)
        with app.app_context():
            db = get_db()
            ai_generate_quiz(db, 3, 4, "Toán học 12", "Toán học", "Hình học không gian", "Dàn ý chuẩn")
            cur = db.cursor()
            cur.execute("SELECT id, dap_an_dung FROM quiz_questions WHERE session_id = 4 ORDER BY id ASC")
            questions = cur.fetchall()

        # Đăng nhập vai trò người học của session 4 (Minh - HS11004)
        self.login("HS11004")

        # Truy cập trang làm quiz
        res_view = self.client.get("/sessions/4/quiz")
        self.assertEqual(res_view.status_code, 200)
        self.assertIn("Tự Đánh Giá Mức Độ Tự Tin".encode("utf-8"), res_view.data)

        # Nộp bài: trả lời đúng 4/5 câu (80% >= 60%) và tự tin trước = 2 sao
        post_data = {
            "tu_danh_gia_truoc": "2.0"
        }
        # Làm đúng 4 câu đầu, câu cuối chọn bừa
        for i, q in enumerate(questions):
            if i < 4:
                post_data[f"question_{q['id']}"] = q["dap_an_dung"]
            else:
                wrong_ans = "A" if q["dap_an_dung"] != "A" else "B"
                post_data[f"question_{q['id']}"] = wrong_ans

        res_submit = self.client.post("/sessions/4/quiz/submit", data=post_data, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn("ĐẠT CHUẨN KIẾN THỨC".encode("utf-8"), res_submit.data)

        # Kiểm tra database
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            # Kiểm tra quiz_results
            cur.execute("SELECT * FROM quiz_results WHERE session_id = 4 AND user_id = 6")
            q_res = cur.fetchone()
            self.assertIsNotNone(q_res, "Phải lưu kết quả vào quiz_results")
            self.assertEqual(float(q_res["diem_so"]), 4.0, "Điểm số phải là 4.0/5.0")
            self.assertEqual(float(q_res["tu_danh_gia_truoc"]), 2.0, "Tự đánh giá trước phải lưu 2.0 sao")

            # Kiểm tra cờ sessions.quiz_dat_chuan
            cur.execute("SELECT quiz_dat_chuan FROM sessions WHERE id = 4")
            dat_chuan = cur.fetchone()[0]
            self.assertEqual(dat_chuan, 1, "Khi đạt >=60% (4/5), sessions.quiz_dat_chuan phải = 1")

        print("  -> Lưu tự đánh giá trước (2★), chấm đúng 4/5 câu (80%), cập nhật quiz_dat_chuan = 1 thành công.")

    def test_04_block_second_quiz_attempt(self):
        """
        [TEST CASE 4]: Chặn làm bài lần 2 (Mỗi học sinh chỉ được làm 1 lần duy nhất)
        - Sau khi đã làm xong, gửi request nộp tiếp -> Hệ thống phải chặn và cảnh báo
        - Bảng quiz_results không bị ghi đè hay chèn thêm dòng mới
        """
        print("\n--- TEST CASE 4: Kiểm thử CHẶN làm quiz lần 2 ---")
        # Session 1 trong dữ liệu mẫu: Bình (user_id=4) đã làm xong quiz (đạt 4/5)
        self.login("HS11002") # Đăng nhập Trần Thanh Bình

        # Thử gửi request nộp bài lần 2 cho Session 1
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM quiz_results WHERE session_id = 1")
            count_before = cur.fetchone()[0]

        post_data = {
            "tu_danh_gia_truoc": "5.0"
        }
        res = self.client.post("/sessions/1/quiz/submit", data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertTrue(
            "đã hoàn thành bài quiz này rồi".encode("utf-8") in res.data or "chỉ được làm bài 1 lần duy nhất".encode("utf-8") in res.data,
            "Hệ thống phải cảnh báo chặn làm bài lần 2"
        )

        with app.app_context():
            db = get_db()
            cur = db.cursor()
            cur.execute("SELECT COUNT(*) FROM quiz_results WHERE session_id = 1")
            count_after = cur.fetchone()[0]
            self.assertEqual(count_after, count_before, "Số lượng bản ghi trong quiz_results KHÔNG được tăng thêm khi bị chặn")

        print("  -> Hệ thống chặn làm bài lần 2 triệt để, bảo toàn tính khách quan sư phạm.")

    def test_05_admin_learning_outcomes_dashboard(self):
        """
        [TEST CASE 5]: Dashboard Quản trị viên / Giáo viên (/admin)
        - Hiển thị khối 'Kết quả học tập'
        - Có điểm TB theo môn
        - Có % đạt >= 4/5
        - Có % phiên đạt chuẩn quiz
        - Có so sánh tự đánh giá trước vs điểm sau
        """
        print("\n--- TEST CASE 5: Kiểm thử Dashboard GV/Admin có khối 'Kết quả học tập' ---")
        self.login("admin")
        res = self.client.get("/admin")
        self.assertEqual(res.status_code, 200)

        # Kiểm tra sự hiện diện của các mục theo yêu cầu đề bài
        html = res.data.decode("utf-8")
        self.assertIn("KẾT QUẢ HỌC TẬP", html, "Phải có tiêu đề khối Kết quả học tập")
        self.assertIn("Phiên đạt chuẩn Quiz", html, "Phải có chỉ số % Phiên đạt chuẩn Quiz")
        self.assertIn("Tỷ lệ xuất sắc (≥4/5 điểm)", html, "Phải có chỉ số % đạt >= 4/5")
        self.assertIn("So sánh Trước vs Sau", html, "Phải có so sánh Tự đánh giá trước vs Điểm sau")
        self.assertIn("Điểm Trung Bình & Tỷ Lệ Đạt Chuẩn Theo Môn Học", html, "Phải có bảng điểm TB theo môn")
        self.assertIn("Quiz dùng để", html, "Phải có ghi chú sư phạm minh bạch về mục đích Quiz")

        print("  -> Dashboard Quản trị viên hiển thị đầy đủ, trực quan mọi chỉ số đo lường học tập.")

    def test_06_quiz_does_not_block_credit_transfer(self):
        """
        [TEST CASE 6]: Kiểm tra nguyên tắc sư phạm cốt lõi:
        - Quiz dùng để XÁC NHẬN kết quả cho giáo viên thấy
        - KHÔNG CHẶN việc chuyển giờ của học sinh (tránh phạt oan HS yếu)
        """
        print("\n--- TEST CASE 6: Kiểm thử Quiz KHÔNG chặn cộng giờ học sinh ---")
        with app.app_context():
            db = get_db()
            cur = db.cursor()
            # Session 1 đã hoàn thành: Bình được trừ -1h, An được cộng +1h
            cur.execute("SELECT * FROM credits_ledger WHERE session_id = 1")
            ledger = cur.fetchall()
            self.assertEqual(len(ledger), 2, "Sổ cái tín dụng đã ghi nhận đủ 2 bên ngay khi hoàn thành phiên")

            # Học sinh làm quiz sau đó không ảnh hưởng tới số giờ đã giao dịch
            cur.execute("SELECT so_du_gio FROM users WHERE id = 3")
            an_credits = cur.fetchone()[0]
            self.assertGreater(an_credits, 0, "Số dư người dạy được bảo toàn trọn vẹn")

        print("  -> Nguyên tắc sư phạm nhân văn được bảo toàn: Học sinh yếu vẫn được ghi nhận công sức trao đổi.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
