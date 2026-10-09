# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M3+ - TIMEBANK EDU
Các ca kiểm thử theo đúng yêu cầu đề bài:
1. 2 tài khoản (Người dạy và Người học) vào cùng phòng học ảo thấy nhau:
   - Cùng iframe Jitsi Meet (tên phòng = "timebankedu-" + ma_qr);
   - Ghi session_attendance (thoi_gian_vao);
   - Tự động cập nhật checkin_day = 1 và checkin_hoc = 1 trong sessions.
2. Thời gian cùng online < 80% so_gio:
   - Bấm kết thúc buổi học -> KHÔNG tự chuyển giờ;
   - Phiên chuyển trạng thái 'can_xac_minh' để giáo viên duyệt tay.
3. Thời gian cùng online >= 80% so_gio:
   - Bấm kết thúc buổi học -> TỰ ĐỘNG chuyển giờ tín dụng (+so_gio và -so_gio);
   - Ghi nhận 2 dòng credits_ledger, sessions -> 'hoan_thanh'.
4. Giáo viên / Admin mở được bất kỳ phòng học nào đang diễn ra:
   - Ghé thăm phòng học ảo qua Dashboard /virtual-rooms hoặc trực tiếp /sessions/<id>/room;
   - Không bị chặn bởi phân quyền;
   - Phê duyệt tay thành công cho phiên 'can_xac_minh'.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import sqlite3
import unittest
from datetime import datetime, timedelta
from app import app, init_db, DATABASE_PATH, calculate_session_online_overlap


class TestMilestoneM3Plus(unittest.TestCase):

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
        self.client = app.test_client()

    def test_case_1_both_users_enter_virtual_room_and_auto_checkin(self):
        """
        Nghiệm thu Case 1:
        2 tài khoản (An - Người dạy, Bình - Người học) vào cùng phòng ảo:
        - Iframe hiển thị cùng room_name (timebankedu-{ma_qr});
        - Ghi session_attendance;
        - sessions.checkin_day = 1 và sessions.checkin_hoc = 1.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # Tạo phiên học mới
        test_ma_qr = "TB-QR-M3PLUS-ROOM1"
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-15 09:00:00', 1.0, 'da_dat', ?, 0, 0)
        """, (an_id, binh_id, test_ma_qr))
        session_id = cur.lastrowid
        conn.commit()
        conn.close()

        expected_room = f"timebankedu-{test_ma_qr}"

        # 1. An (Người dạy) vào phòng học ảo
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_an = self.client.get(f"/sessions/{session_id}/room")
        self.assertEqual(res_an.status_code, 200)
        html_an = res_an.data.decode('utf-8')
        self.assertTrue(expected_room in html_an, "Trang phòng học phải chứa đúng mã phòng của phiên")
        self.assertIn("TRỰC TUYẾN", html_an)

        # 2. Bình (Người học) vào phòng học ảo trên trình duyệt khác
        client_binh = app.test_client()
        client_binh.post("/login", data={"ma_hoc_sinh": "HS11002", "mat_khau": "admin123"}, follow_redirects=True)
        res_binh = client_binh.get(f"/sessions/{session_id}/room")
        self.assertEqual(res_binh.status_code, 200)
        html_binh = res_binh.data.decode('utf-8')
        self.assertTrue(expected_room in html_binh, "Cả hai bạn phải vào cùng mã phòng học")

        # 3. Kiểm tra cơ sở dữ liệu:
        # a) session_attendance phải có 2 dòng (1 của An, 1 của Bình)
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT user_id, thoi_gian_vao, thoi_gian_ra FROM session_attendance WHERE session_id = ?", (session_id,))
        att_rows = cur.fetchall()
        user_ids_in_room = [r[0] for r in att_rows]

        self.assertIn(an_id, user_ids_in_room, "session_attendance phải ghi nhận thời gian vào của người dạy")
        self.assertIn(binh_id, user_ids_in_room, "session_attendance phải ghi nhận thời gian vào của người học")

        # b) Cả 2 bên đều đã tự động check-in trong bảng sessions
        cur.execute("SELECT checkin_day, checkin_hoc FROM sessions WHERE id = ?", (session_id,))
        ci_day, ci_hoc = cur.fetchone()
        conn.close()

        self.assertEqual(ci_day, 1, "Người dạy vào phòng ảo phải tự động check-in (checkin_day = 1)")
        self.assertEqual(ci_hoc, 1, "Người học vào phòng ảo phải tự động check-in (checkin_hoc = 1)")

        print("\n[PASS] Case 1: 2 tài khoản vào cùng phòng học ảo thấy nhau, ghi nhận session_attendance và tự động check-in 2 chiều")

    def test_case_2_less_than_80_percent_online_blocks_auto_transfer(self):
        """
        Nghiệm thu Case 2:
        Thời gian cùng online < 80% thời lượng quy định:
        - Bấm kết thúc buổi học -> KHÔNG tự chuyển giờ;
        - sessions.trang_thai chuyển sang 'can_xac_minh' để giáo viên duyệt tay.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Đặt lại số dư ban đầu: An = 2.0h, Bình = 2.0h
        cur.execute("UPDATE users SET so_du_gio = 2.0 WHERE ma_hoc_sinh IN ('HS12001', 'HS11002')")
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # Tạo phiên học 1.0 giờ (60 phút quy định, 80% là 48 phút)
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-16 14:00:00', 1.0, 'da_dat', 'TB-QR-M3PLUS-SHORT', 1, 1)
        """, (an_id, binh_id))
        session_id = cur.lastrowid

        # Giả lập lịch sử điểm danh: Cả 2 cùng online chỉ 15 phút (15 phút / 60 phút = 25% < 80%)
        t0 = datetime(2026, 10, 16, 14, 0, 0)
        t_out = t0 + timedelta(minutes=15)
        t0_str = t0.strftime("%Y-%m-%d %H:%M:%S")
        tout_str = t_out.strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("INSERT INTO session_attendance (session_id, user_id, thoi_gian_vao, thoi_gian_ra) VALUES (?, ?, ?, ?)",
                    (session_id, an_id, t0_str, tout_str))
        cur.execute("INSERT INTO session_attendance (session_id, user_id, thoi_gian_vao, thoi_gian_ra) VALUES (?, ?, ?, ?)",
                    (session_id, binh_id, t0_str, tout_str))
        conn.commit()
        conn.close()

        # An (Người dạy) bấm 'Kết thúc buổi học'
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_finish = self.client.post(f"/sessions/{session_id}/finish", follow_redirects=True)
        self.assertEqual(res_finish.status_code, 200)
        html_finish = res_finish.data.decode('utf-8')

        # Thông báo cảnh báo chưa đạt 80%
        self.assertIn("chưa đạt 80%", html_finish)

        # Kiểm tra cơ sở dữ liệu:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_id,))
        status = cur.fetchone()[0]

        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (an_id,))
        an_bal = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (binh_id,))
        binh_bal = cur.fetchone()[0]

        cur.execute("SELECT COUNT(*) FROM credits_ledger WHERE session_id = ?", (session_id,))
        ledger_count = cur.fetchone()[0]
        conn.close()

        self.assertEqual(status, "can_xac_minh", "Khi online < 80%, phiên phải chuyển sang 'can_xac_minh'")
        self.assertEqual(an_bal, 2.0, "Số dư người dạy không được thay đổi")
        self.assertEqual(binh_bal, 2.0, "Số dư người học không được thay đổi")
        self.assertEqual(ledger_count, 0, "Tuyệt đối không được ghi nhận vào credits_ledger khi chưa đủ 80%")

        print("[PASS] Case 2: Online dưới 80% thời lượng quy định -> Không tự chuyển giờ, phiên chuyển trạng thái 'can_xac_minh'")

    def test_case_3_greater_equal_80_percent_online_auto_transfers(self):
        """
        Nghiệm thu Case 3:
        Thời gian cùng online >= 80% thời lượng quy định:
        - Bấm kết thúc buổi học -> TỰ ĐỘNG chuyển giờ tín dụng;
        - sessions.trang_thai -> 'hoan_thanh';
        - Ghi nhận 2 dòng credits_ledger (+so_gio và -so_gio).
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("UPDATE users SET so_du_gio = 2.0 WHERE ma_hoc_sinh IN ('HS12001', 'HS11002')")
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # Tạo phiên học 1.0 giờ
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-17 15:00:00', 1.0, 'da_dat', 'TB-QR-M3PLUS-SUFFICIENT', 1, 1)
        """, (an_id, binh_id))
        session_id = cur.lastrowid

        # Giả lập lịch sử điểm danh: Cả 2 cùng online 50 phút (50 phút / 60 phút = 83.3% >= 80%)
        t0 = datetime(2026, 10, 17, 15, 0, 0)
        t_out = t0 + timedelta(minutes=50)
        t0_str = t0.strftime("%Y-%m-%d %H:%M:%S")
        tout_str = t_out.strftime("%Y-%m-%d %H:%M:%S")

        cur.execute("INSERT INTO session_attendance (session_id, user_id, thoi_gian_vao, thoi_gian_ra) VALUES (?, ?, ?, ?)",
                    (session_id, an_id, t0_str, tout_str))
        cur.execute("INSERT INTO session_attendance (session_id, user_id, thoi_gian_vao, thoi_gian_ra) VALUES (?, ?, ?, ?)",
                    (session_id, binh_id, t0_str, tout_str))
        conn.commit()
        conn.close()

        # Bấm kết thúc buổi học
        self.client.post("/login", data={"ma_hoc_sinh": "HS12001", "mat_khau": "admin123"}, follow_redirects=True)
        res_finish = self.client.post(f"/sessions/{session_id}/finish", follow_redirects=True)
        self.assertEqual(res_finish.status_code, 200)

        # Kiểm tra cơ sở dữ liệu:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_id,))
        status = cur.fetchone()[0]

        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (an_id,))
        an_bal = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (binh_id,))
        binh_bal = cur.fetchone()[0]

        cur.execute("SELECT user_id, bien_dong, ly_do FROM credits_ledger WHERE session_id = ? ORDER BY id ASC", (session_id,))
        ledger_rows = cur.fetchall()
        conn.close()

        self.assertEqual(status, "hoan_thanh", "Khi online >= 80%, phiên phải chuyển sang 'hoan_thanh'")
        self.assertEqual(an_bal, 3.0, f"Số dư người dạy phải tăng lên 3.0h (thực tế: {an_bal})")
        self.assertEqual(binh_bal, 1.0, f"Số dư người học phải giảm còn 1.0h (thực tế: {binh_bal})")
        self.assertEqual(len(ledger_rows), 2, "credits_ledger phải ghi nhận chính xác 2 dòng")
        self.assertEqual(ledger_rows[0][1], 1.0)
        self.assertEqual(ledger_rows[0][2], "day_hoc")
        self.assertEqual(ledger_rows[1][1], -1.0)
        self.assertEqual(ledger_rows[1][2], "hoc")

        print("[PASS] Case 3: Online đạt >= 80% thời lượng quy định -> Tự động chuyển giờ tín dụng và ghi nhận 2 dòng sổ cái")

    def test_case_4_teacher_and_admin_supervision_and_manual_approval(self):
        """
        Nghiệm thu Case 4:
        - Giáo viên / Admin truy cập được Dashboard /virtual-rooms;
        - Giáo viên ghé thăm dự giờ được bất kỳ phòng học nào đang diễn ra;
        - Giáo viên duyệt tay thành công phiên ở trạng thái 'can_xac_minh'.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Đặt lại số dư
        cur.execute("UPDATE users SET so_du_gio = 2.0 WHERE ma_hoc_sinh IN ('HS12001', 'HS11002')")
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS12001'")
        an_id = cur.fetchone()[0]
        cur.execute("SELECT id FROM users WHERE ma_hoc_sinh = 'HS11002'")
        binh_id = cur.fetchone()[0]

        # 4a. Tạo 1 phiên đang diễn ra (da_dat)
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-18 10:00:00', 1.0, 'da_dat', 'TB-QR-M3PLUS-VISIT', 1, 1)
        """, (an_id, binh_id))
        session_live_id = cur.lastrowid

        # 4b. Tạo 1 phiên cần xác minh (can_xac_minh)
        cur.execute("""
            INSERT INTO sessions 
            (skill_id, nguoi_day_id, nguoi_hoc_id, thoi_gian_bat_dau, so_gio, trang_thai, ma_qr, checkin_day, checkin_hoc)
            VALUES (1, ?, ?, '2026-10-18 11:00:00', 1.0, 'can_xac_minh', 'TB-QR-M3PLUS-VERIFY', 1, 1)
        """, (an_id, binh_id))
        session_verify_id = cur.lastrowid
        conn.commit()
        conn.close()

        # 1. Đăng nhập Giáo viên GV001
        self.client.post("/login", data={"ma_hoc_sinh": "GV001", "mat_khau": "admin123"}, follow_redirects=True)

        # 2. Truy cập Dashboard /virtual-rooms
        res_dashboard = self.client.get("/virtual-rooms")
        self.assertEqual(res_dashboard.status_code, 200)
        html_dashboard = res_dashboard.data.decode('utf-8')
        self.assertIn("Quản Lý Phòng Học Ảo", html_dashboard)
        self.assertIn(f"#{session_live_id}", html_dashboard)
        self.assertIn(f"#{session_verify_id}", html_dashboard)

        # 3. Giáo viên ghé thăm dự giờ phòng đang diễn ra (/sessions/<id>/room)
        res_visit = self.client.get(f"/sessions/{session_live_id}/room")
        self.assertEqual(res_visit.status_code, 200, "Giáo viên phải mở được phòng học đang diễn ra")
        html_visit = res_visit.data.decode('utf-8')
        self.assertIn("Chế độ Giám sát Sư phạm (GV/Admin)", html_visit)

        # 4. Giáo viên duyệt tay phiên cần xác minh (manual_approve_session)
        res_approve = self.client.post(f"/admin/sessions/{session_verify_id}/approve-transfer", follow_redirects=True)
        self.assertEqual(res_approve.status_code, 200)

        # Kiểm tra phiên đã được duyệt chuyển sang hoan_thanh và số dư cập nhật
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai FROM sessions WHERE id = ?", (session_verify_id,))
        new_status = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (an_id,))
        an_bal = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = ?", (binh_id,))
        binh_bal = cur.fetchone()[0]
        conn.close()

        self.assertEqual(new_status, "hoan_thanh", "Phiên phải chuyển sang 'hoan_thanh' sau khi giáo viên duyệt tay")
        self.assertEqual(an_bal, 3.0, "Số dư người dạy phải là 3.0h sau duyệt tay")
        self.assertEqual(binh_bal, 1.0, "Số dư người học phải là 1.0h sau duyệt tay")

        print("[PASS] Case 4: Giáo viên ghé thăm dự giờ phòng học ảo thành công và duyệt tay phiên cần xác minh chính xác")


if __name__ == "__main__":
    unittest.main()
