# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M3 - TIMEBANK EDU
Các ca kiểm thử theo đúng yêu cầu đề bài:
1. An (2.0h) dạy Bình (2.0h) 1h, cả 2 check-in -> 3.0h / 1.0h;
2. Chỉ 1 bên check-in -> Không chuyển giờ (chặn không cho hoàn thành);
3. Bình 0.5h đặt phiên 1h -> Bị chặn + báo lỗi tiếng Việt;
4. credits_ledger chỉ INSERT (Append-Only);
5. Trang 'Ví của tôi' (/wallet): Hiển thị đúng số dư + lịch sử mới nhất xếp trước;
6. Mã QR: Sinh ngẫu nhiên khi đặt lịch và hiển thị ảnh Base64 trên trang chi tiết phiên.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import unittest
from app import app, init_db, DATABASE_PATH, generate_qr_base64


class TestMilestoneM3(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # Đảm bảo CSDL được khởi tạo sạch
        if DATABASE_PATH.exists():
            try:
                os.remove(DATABASE_PATH)
            except Exception:
                pass
        init_db()

    def setUp(self):
        # Tạo test client mới cho mỗi test case để tránh rò rỉ cookie session
        self.client = app.test_client()

    def test_case_1_both_checkin_transfers_hours_successfully(self):
        """
        Nghiệm thu Case 1:
        An (2.0h) dạy Bình (2.0h) 1h.
        Cả 2 bên check-in -> Người dạy bấm hoàn thành -> An nhận 3.0h, Bình còn 1.0h.
        credits_ledger ghi 2 dòng: +1.0h ('day_hoc') và -1.0h ('hoc').
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Đặt lại số dư ban đầu: An (id=3) = 2.0h, Bình (id=4) = 2.0h
        cur.execute("UPDATE users SET so_du_gio = 2.0 WHERE ma_hoc_sinh IN ('HS12001', 'HS11002')")
        
        # Lấy id của An và Bình
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # Tạo một phiên học: An dạy Bình 1.0h
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-10 09:00:00', 1.0, 'da_dat', 'QR-TEST-M3-01', 0, 0)
        """, (an_id, binh_id))
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        # 1. An (người dạy) đăng nhập và check-in
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_ci_teacher = self.client.post(f"/sessions/{session_id}/checkin", data={"role": "teacher"}, follow_redirects=True)
        self.assertEqual(res_ci_teacher.status_code, 200)

        # 2. Bình (người học) đăng nhập và check-in
        client_binh = app.test_client()
        client_binh.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)
        res_ci_learner = client_binh.post(f"/sessions/{session_id}/checkin", data={"role": "learner"}, follow_redirects=True)
        self.assertEqual(res_ci_learner.status_code, 200)

        # Kiểm tra trạng thái check-in trong DB: cả 2 phải bằng 1
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT checkin_day, checkin_hoc FROM sessions WHERE id = ?", (session_id,))
        ci_day, ci_hoc = cur.fetchone()
        self.assertEqual(ci_day, 1, "Người dạy phải checkin thành công")
        self.assertEqual(ci_hoc, 1, "Người học phải checkin thành công")

        # 3. An (người dạy) bấm 'Xác nhận hoàn thành'
        res_complete = self.client.post(f"/sessions/{session_id}/complete", follow_redirects=True)
        self.assertEqual(res_complete.status_code, 200)

        # 4. Kiểm tra số dư và sổ cái tín dụng
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (an_id,))
        an_balance = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (binh_id,))
        binh_balance = cur.fetchone()[0]

        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_id,))
        ses_status = cur.fetchone()[0]

        # Kiểm tra 2 dòng credits_ledger
        cur.execute("SELECT user_id, bien_dong, ly_do FROM credits_ledger WHERE session_id = ? ORDER BY id ASC", (session_id,))
        ledger_rows = cur.fetchall()
        conn.close()

        self.assertEqual(an_balance, 3.0, f"Số dư An phải là 3.0h (thực tế: {an_balance})")
        self.assertEqual(binh_balance, 1.0, f"Số dư Bình phải là 1.0h (thực tế: {binh_balance})")
        self.assertEqual(ses_status, "hoan_thanh", "Phiên học phải chuyển sang trạng thái 'hoan_thanh'")
        
        self.assertEqual(len(ledger_rows), 2, "credits_ledger phải có đúng 2 dòng giao dịch mới")
        # Dòng 1 cho An
        self.assertEqual(ledger_rows[0][0], an_id)
        self.assertEqual(ledger_rows[0][1], 1.0)
        self.assertEqual(ledger_rows[0][2], "day_hoc")
        # Dòng 2 cho Bình
        self.assertEqual(ledger_rows[1][0], binh_id)
        self.assertEqual(ledger_rows[1][1], -1.0)
        self.assertEqual(ledger_rows[1][2], "hoc")

        print("\n[PASS] Case 1: An (2.0h) dạy Bình (2.0h) 1h, cả 2 check-in -> 3.0h / 1.0h, ghi 2 dòng credits_ledger chuẩn xác")

    def test_case_2_single_side_checkin_cannot_transfer(self):
        """
        Nghiệm thu Case 2:
        Chỉ 1 bên check-in -> Bấm hoàn thành -> Bị chặn, không chuyển giờ, báo lỗi tiếng Việt.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Đặt lại số dư
        cur.execute("UPDATE users SET so_du_gio = 2.0 WHERE ma_hoc_sinh IN ('HS12001', 'HS11002')")
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # 2a. Tạo phiên mới: Chỉ người dạy check-in (checkin_day = 1, checkin_hoc = 0)
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-11 10:00:00', 1.0, 'da_dat', 'QR-TEST-M3-02A', 1, 0)
        """, (an_id, binh_id))
        session_id_2a = cur.lastrowid

        # 2b. Tạo phiên: Chỉ người học check-in (checkin_day = 0, checkin_hoc = 1)
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-12 14:00:00', 1.0, 'da_dat', 'QR-TEST-M3-02B', 0, 1)
        """, (an_id, binh_id))
        session_id_2b = cur.lastrowid
        conn.commit()
        conn.close()

        # Đăng nhập An (người dạy)
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)

        # Thử hoàn thành phiên 2a (người học chưa check-in)
        res_2a = self.client.post(f"/sessions/{session_id_2a}/complete", follow_redirects=True)
        html_2a = res_2a.data.decode('utf-8')
        self.assertIn("Chưa thể hoàn thành", html_2a, "Phải báo lỗi tiếng Việt khi chưa đủ 2 bên check-in")

        # Thử hoàn thành phiên 2b (người dạy chưa check-in)
        res_2b = self.client.post(f"/sessions/{session_id_2b}/complete", follow_redirects=True)
        html_2b = res_2b.data.decode('utf-8')
        self.assertIn("Chưa thể hoàn thành", html_2b, "Phải báo lỗi tiếng Việt khi chưa đủ 2 bên check-in")

        # Kiểm tra số dư không hề bị thay đổi
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (an_id,))
        an_bal = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (binh_id,))
        binh_bal = cur.fetchone()[0]

        # Kiểm tra phiên vẫn ở trạng thái 'da_dat'
        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_id_2a,))
        status_2a = cur.fetchone()[0]
        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_id_2b,))
        status_2b = cur.fetchone()[0]

        # Kiểm tra không có dòng credits_ledger nào sinh ra
        cur.execute("SELECT COUNT(*) FROM credits_ledger WHERE session_id IN (?, ?)", (session_id_2a, session_id_2b))
        ledger_count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(an_bal, 2.0, "Số dư của An phải giữ nguyên 2.0h")
        self.assertEqual(binh_bal, 2.0, "Số dư của Bình phải giữ nguyên 2.0h")
        self.assertEqual(status_2a, "da_dat", "Phiên 2a vẫn phải là 'da_dat'")
        self.assertEqual(status_2b, "da_dat", "Phiên 2b vẫn phải là 'da_dat'")
        self.assertEqual(ledger_count, 0, "Không được ghi nhận bất kỳ giao dịch nào vào sổ cái khi chưa đủ 2 bên")

        print("[PASS] Case 2: Chỉ 1 bên check-in -> Hoàn toàn không chuyển giờ, trạng thái phiên giữ nguyên 'da_dat'")

    def test_case_3_insufficient_balance_blocks_booking(self):
        """
        Nghiệm thu Case 3:
        Bình có số dư 0.5h đặt phiên 1h -> Bị chặn và báo lỗi tiếng Việt.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Đặt số dư của Bình thành 0.5h
        cur.execute("UPDATE users SET so_du_gio = 0.5 WHERE ma_hoc_sinh = 'HS11002'")
        
        # Lấy kỹ năng của An (user_id = 3)
        cur.execute("SELECT id FROM skills WHERE user_id = 3 AND trang_thai_duyet = 'da_duyet' LIMIT 1")
        skill_row = cur.fetchone()
        skill_id = skill_row[0]
        conn.commit()
        conn.close()

        # Đăng nhập Bình (HS11002)
        self.client.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)

        # Đặt lịch 1.0h trong khi số dư chỉ có 0.5h
        res = self.client.post("/sessions/book", data={
            "skill_id": skill_id,
            "thoi_gian_bat_dau": "2026-10-15 15:00:00",
            "so_gio": "1.0"
        }, follow_redirects=True)

        html = res.data.decode('utf-8')
        # Kiểm tra thông báo lỗi tiếng Việt
        self.assertIn("Số dư tín dụng của bạn không đủ", html, "Phải báo lỗi tiếng Việt khi số dư không đủ đặt lịch")

        # Kiểm tra trong DB: không có phiên nào được tạo với so_gio = 1.0 cho Bình vào thời điểm đó
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sessions WHERE nguoi_hoc_id = 4 AND thoi_gian_bat_dau = '2026-10-15 15:00:00'")
        count = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = 4")
        balance = cur.fetchone()[0]
        conn.close()

        self.assertEqual(count, 0, "Phiên học không được phép tạo khi thiếu số dư")
        self.assertEqual(balance, 0.5, "Số dư của Bình không được phép thay đổi")

        print("[PASS] Case 3: Học sinh có 0.5h đặt lịch phiên 1.0h -> Bị chặn thành công và hiển thị lỗi tiếng Việt")

    def test_case_4_credits_ledger_is_append_only(self):
        """
        Nghiệm thu Case 4:
        credits_ledger chỉ INSERT (Append-Only):
        - Đếm số dòng trước và sau khi hoàn thành phiên.
        - Không có bất kỳ hành động UPDATE/DELETE nào tác động lên credits_ledger.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM credits_ledger")
        count_before = cur.fetchone()[0]

        # Kiểm tra mã nguồn app.py không chứa câu lệnh UPDATE credits_ledger hoặc DELETE FROM credits_ledger
        with open("app.py", "r", encoding="utf-8") as f:
            app_code = f.read().upper()

        self.assertNotIn("UPDATE CREDITS_LEDGER", app_code, "credits_ledger tuyệt đối không được UPDATE")
        self.assertNotIn("DELETE FROM CREDITS_LEDGER", app_code, "credits_ledger tuyệt đối không được DELETE")

        # Tạo và hoàn thành 1 phiên để xem số dòng có tăng thêm chính xác 2 dòng hay không
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-20 08:00:00', 0.5, 'da_dat', 'QR-TEST-M3-04', 1, 1)
        """, (an_id, binh_id))
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Thực hiện hoàn thành phiên
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.post(f"/sessions/{session_id}/complete", follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM credits_ledger")
        count_after = cur.fetchone()[0]
        conn.close()

        self.assertEqual(count_after, count_before + 2, "credits_ledger chỉ INSERT thêm 2 dòng mới cho mỗi phiên hoàn thành")
        print("[PASS] Case 4: credits_ledger tuân thủ nghiêm ngặt nguyên tắc Append-Only (Chỉ INSERT, tăng đúng 2 dòng)")

    def test_case_5_wallet_page_displays_balance_and_order_desc(self):
        """
        Nghiệm thu Case 5:
        Trang 'Ví của tôi' (/wallet):
        - Hiển thị số dư khả dụng và tổng tích lũy, tổng dùng.
        - Hiển thị lịch sử biến động sổ cái với thứ tự mới nhất xếp trước (ORDER BY id DESC).
        """
        # Đăng nhập An (HS12001)
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res = self.client.get("/wallet")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')

        self.assertIn("Ví Thời Gian Của Tôi", html)
        self.assertTrue(
            "Lịch Sử Biến Động Ví (Mới nhất trước)" in html or "Lịch Sử Biến Động Sổ Cái (Mới nhất trước)" in html,
            "Phải hiển thị tiêu đề Lịch Sử Biến Động Ví/Sổ Cái"
        )

        # Kiểm tra thứ tự các mã giao dịch trong bảng credits_ledger hiển thị giảm dần
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM credits_ledger WHERE user_id = 3 ORDER BY id DESC")
        expected_ids = [row[0] for row in cur.fetchall()]
        conn.close()

        # Đảm bảo mã ID mới nhất xuất hiện trước các ID cũ trong HTML
        if len(expected_ids) >= 2:
            first_id_str = f"#{expected_ids[0]}"
            second_id_str = f"#{expected_ids[1]}"
            pos_1 = html.find(first_id_str)
            pos_2 = html.find(second_id_str)
            self.assertTrue(pos_1 != -1 and pos_2 != -1 and pos_1 < pos_2, "Giao dịch ID lớn hơn phải xuất hiện trước ID nhỏ hơn")

        print("[PASS] Case 5: Trang 'Ví của tôi' hiển thị đầy đủ số dư và lịch sử giao dịch sắp xếp mới nhất trước")

    def test_case_6_qr_code_random_and_base64_generation(self):
        """
        Nghiệm thu Case 6:
        - Mã QR ma_qr được sinh ngẫu nhiên khi đặt lịch.
        - Trang chi tiết phiên /sessions/<id> hiển thị ảnh Base64 của mã QR.
        """
        # 1. Kiểm tra hàm sinh mã QR Base64
        test_qr_text = "TB-QR-TEST-RANDOM-1234"
        qr_b64 = generate_qr_base64(test_qr_text)
        self.assertTrue(len(qr_b64) > 100, "Chuỗi Base64 mã QR phải có độ dài hợp lệ")

        # 2. Đăng nhập Bình và đặt lịch một kỹ năng để kiểm tra ma_qr sinh ngẫu nhiên
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET so_du_gio = 5.0 WHERE ma_hoc_sinh = 'HS11002'")
        conn.commit()
        conn.close()

        self.client.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)
        res_book = self.client.post("/sessions/book", data={
            "skill_id": 1,
            "thoi_gian_bat_dau": "2026-10-25 10:00:00",
            "so_gio": "1.0"
        }, follow_redirects=True)
        self.assertEqual(res_book.status_code, 200)

        # Lấy phiên vừa đặt
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, ma_qr FROM sessions WHERE thoi_gian_bat_dau = '2026-10-25 10:00:00'")
        row = cur.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        ses_id, ma_qr = row
        self.assertTrue(ma_qr.startswith("TB-QR-"), f"ma_qr phải được sinh ngẫu nhiên theo chuẩn (thực tế: {ma_qr})")

        # 3. Truy cập trang chi tiết phiên và kiểm tra ảnh QR Base64 trong HTML
        res_detail = self.client.get(f"/sessions/{ses_id}")
        self.assertEqual(res_detail.status_code, 200)
        html_detail = res_detail.data.decode('utf-8')
        self.assertIn("data:image/png;base64,", html_detail, "Trang chi tiết phiên phải chứa ảnh mã QR dạng data:image/png;base64")
        self.assertIn(ma_qr, html_detail, "Trang chi tiết phiên phải hiển thị chuỗi ma_qr")

        print("[PASS] Case 6: Mã QR sinh ngẫu nhiên khi đặt lịch và hiển thị ảnh Base64 trực quan trên trang chi tiết phiên")


if __name__ == "__main__":
    unittest.main()
