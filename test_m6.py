# -*- coding: utf-8 -*-
"""
BỘ KIỂM THỬ TỰ ĐỘNG NGHIỆM THU MILESTONE M6
Dự án: Ngân hàng Thời gian Học đường (TimeBank EDU)
Cuộc thi: Ngày hội Nhà giáo sáng tạo với công nghệ số và AI 2026 - Bảng B

Nội dung kiểm thử Milestone M6 (Hoạt động Vì cộng đồng - Giờ công ích):
1. GV/Admin tạo nhiệm vụ: tiêu đề, mô tả, địa điểm, số giờ thưởng, số lượng tối đa, hạn đăng ký -> trạng thái 'mo_dang_ky'. Chặn HS tạo nhiệm vụ (403).
2. Trang 'Vì cộng đồng' (/community): liệt kê nhiệm vụ đang mở + nút 'Đăng ký tham gia'. HS đăng ký thành công.
3. CHẶN ĐĂNG KÝ: Quá số lượng tối đa hoặc quá hạn đăng ký bị chặn, không thêm vào CSDL.
4. GV ĐIỂM DANH:
   - 'hoan_thanh' -> INSERT credits_ledger (bien_dong = +so_gio_thuong, ly_do = 'nhiem_vu_cong_dong') + cập nhật users.so_du_gio.
   - 'vang_mat' -> cập nhật trang_thai = 'vang_mat', tuyệt đối KHÔNG cộng giờ.
5. AI GỢI Ý NHIỆM VỤ: Mục 'Việc phù hợp với bạn' gợi ý 3 việc phù hợp + giải thích TV ngắn -> lưu ai_logs ('goi_y_nhiem_vu').
6. LANDING PAGE: Khối 'Vì cộng đồng' hiển thị tổng giờ công ích + nhiệm vụ gần nhất.
"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import unittest
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Đảm bảo đường dẫn import app
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from app import app, init_db, DATABASE_PATH, get_db
from ai_service import ai_recommend_tasks


class TestMilestoneM6(unittest.TestCase):
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
        """Hàm trợ giúp đăng nhập sạch phiên"""
        self.client.get("/logout", follow_redirects=True)
        return self.client.post("/login", data={
            "ma_hoc_sinh": username,
            "mat_khau": password
        }, follow_redirects=True)

    def test_01_teacher_creates_task_and_student_forbidden(self):
        """
        [TEST CASE 1]: GV/admin tạo nhiệm vụ mới thành công ('mo_dang_ky');
        Học sinh không có quyền sẽ bị chặn trả về 403 Forbidden.
        """
        # 1. Giáo viên đăng nhập và tạo nhiệm vụ mới
        self.login("GV001")
        future_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        resp = self.client.post("/community/tasks/new", data={
            "tieu_de": "Hỗ trợ chuẩn bị Lễ Khai mạc Tuần lễ STEM 2026",
            "mo_ta": "Sắp xếp bàn ghế, thiết lập biển chỉ dẫn và hướng dẫn đại biểu",
            "dia_diem": "Hội trường A",
            "so_gio_thuong": "2.5",
            "so_luong_toi_da": "6",
            "han_dang_ky": future_date
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra bản ghi trong CSDL
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM community_tasks WHERE tieu_de LIKE '%Tuần lễ STEM%'")
        task = cur.fetchone()
        self.assertIsNotNone(task)
        self.assertEqual(task["trang_thai"], "mo_dang_ky")
        self.assertEqual(task["so_gio_thuong"], 2.5)
        self.assertEqual(task["so_luong_toi_da"], 6)
        conn.close()

        # 2. Học sinh (HS12001) cố tình tạo nhiệm vụ -> Bị chặn 403 Forbidden
        self.login("HS12001")
        resp_forbidden = self.client.post("/community/tasks/new", data={
            "tieu_de": "Học sinh tự tạo nhiệm vụ trái quyền",
            "mo_ta": "Không được phép",
            "dia_diem": "Sân trường",
            "so_gio_thuong": "1.0",
            "so_luong_toi_da": "5",
            "han_dang_ky": future_date
        })
        self.assertEqual(resp_forbidden.status_code, 403)

    def test_02_community_page_and_student_registration(self):
        """
        [TEST CASE 2]: Trang 'Vì cộng đồng' hiển thị danh sách nhiệm vụ đang mở
        và học sinh đăng ký tham gia thành công.
        """
        # Học sinh đăng nhập
        self.login("HS12001") # user_id = 3
        resp = self.client.get("/community")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Chương trình Giờ Công ích Học đường".encode("utf-8"), resp.data)
        self.assertIn("Dọn rác bãi biển Hạ Long sáng Chủ nhật".encode("utf-8"), resp.data)

        # Học sinh An (id=3) đăng ký tham gia nhiệm vụ số 1 (Dọn rác bãi biển Hạ Long)
        reg_resp = self.client.post("/community/tasks/1/register", follow_redirects=True)
        self.assertEqual(reg_resp.status_code, 200)
        self.assertIn("thành công".encode("utf-8"), reg_resp.data)

        # Kiểm tra bản ghi trong CSDL task_registrations
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT trang_thai FROM task_registrations WHERE task_id = 1 AND user_id = 3")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], "da_dang_ky")
        conn.close()

    def test_03_blocked_registration_when_full_or_expired(self):
        """
        [TEST CASE 3]: CHẶN ĐĂNG KÝ:
        - Quá số lượng tối đa -> Bị chặn, không cho đăng ký thêm.
        - Quá hạn đăng ký -> Bị chặn, không cho đăng ký.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()

        # 1. Tạo nhiệm vụ chỉ cho tối đa 1 người (so_luong_toi_da = 1)
        cur.execute("""
            INSERT INTO community_tasks 
            (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai)
            VALUES ('Nhiệm vụ giới hạn 1 người', 'Test full', 'P101', 1.0, 1, '2026-12-31', 2, 'mo_dang_ky')
        """)
        full_task_id = cur.lastrowid

        # Cho học sinh Bình (id=4) đăng ký trước để chiếm chỗ
        cur.execute(
            "INSERT INTO task_registrations (task_id, user_id, trang_thai) VALUES (?, 4, 'da_dang_ky')",
            (full_task_id,)
        )

        # 2. Tạo nhiệm vụ đã hết hạn (han_dang_ky ở quá khứ)
        cur.execute("""
            INSERT INTO community_tasks 
            (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai)
            VALUES ('Nhiệm vụ đã hết hạn', 'Test expired', 'P102', 1.0, 5, '2020-01-01', 2, 'mo_dang_ky')
        """)
        expired_task_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Học sinh An (id=3) cố tình đăng ký nhiệm vụ đã đầy
        self.login("HS12001")
        resp_full = self.client.post(f"/community/tasks/{full_task_id}/register", follow_redirects=True)
        self.assertIn("đủ số lượng".encode("utf-8"), resp_full.data)

        # Kiểm tra học sinh An không được thêm vào CSDL của full_task
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM task_registrations WHERE task_id = ? AND user_id = 3", (full_task_id,))
        self.assertEqual(cur.fetchone()[0], 0)

        # Học sinh An cố tình đăng ký nhiệm vụ đã hết hạn
        resp_expired = self.client.post(f"/community/tasks/{expired_task_id}/register", follow_redirects=True)
        self.assertIn("quá hạn".encode("utf-8"), resp_expired.data)

        cur.execute("SELECT COUNT(*) FROM task_registrations WHERE task_id = ? AND user_id = 3", (expired_task_id,))
        self.assertEqual(cur.fetchone()[0], 0)
        conn.close()

    def test_04_teacher_attendance_credits_ledger_and_absence(self):
        """
        [TEST CASE 4]: GV điểm danh sau hoạt động:
        - 'hoan_thanh' -> INSERT credits_ledger (bien_dong = +so_gio_thuong, ly_do = 'nhiem_vu_cong_dong')
          và số dư ví tăng chính xác.
        - 'vang_mat' -> cập nhật trang_thai = 'vang_mat', tuyệt đối không cộng giờ thưởng.
        """
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        # Lấy số dư ban đầu của học sinh Minh (id=6, 2.0h) và Hà (id=7, 2.0h)
        cur.execute("SELECT so_du_gio FROM users WHERE id = 6")
        minh_balance_before = cur.fetchone()[0]
        cur.execute("SELECT so_du_gio FROM users WHERE id = 7")
        ha_balance_before = cur.fetchone()[0]

        # Tạo một nhiệm vụ thưởng 2.0 giờ
        cur.execute("""
            INSERT INTO community_tasks 
            (tieu_de, mo_ta, dia_diem, so_gio_thuong, so_luong_toi_da, han_dang_ky, nguoi_tao_id, trang_thai)
            VALUES ('Trồng cây xanh khuôn viên trường', 'Hoạt động Thứ Bảy xanh', 'Vườn trường', 2.0, 5, '2026-11-20', 2, 'mo_dang_ky')
        """)
        task_id = cur.lastrowid

        # Minh và Hà đăng ký
        cur.execute("INSERT INTO task_registrations (task_id, user_id, trang_thai) VALUES (?, 6, 'da_dang_ky')", (task_id,))
        reg_minh_id = cur.lastrowid
        cur.execute("INSERT INTO task_registrations (task_id, user_id, trang_thai) VALUES (?, 7, 'da_dang_ky')", (task_id,))
        reg_ha_id = cur.lastrowid
        conn.commit()
        conn.close()

        # Giáo viên GV001 thực hiện điểm danh: Minh 'hoan_thanh', Hà 'vang_mat'
        self.login("GV001")
        resp = self.client.post(f"/community/tasks/{task_id}/attendance", data={
            f"status_{reg_minh_id}": "hoan_thanh",
            f"status_{reg_ha_id}": "vang_mat",
            "hoan_thanh_nhiem_vu": "1"
        }, follow_redirects=True)
        self.assertEqual(resp.status_code, 200)

        # Kiểm tra kết quả trong CSDL
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1. Kiểm tra Minh: được cộng 2.0h và có dòng ledger ly_do = 'nhiem_vu_cong_dong'
        cur.execute("SELECT so_du_gio FROM users WHERE id = 6")
        minh_balance_after = cur.fetchone()[0]
        self.assertEqual(minh_balance_after, minh_balance_before + 2.0)

        cur.execute("SELECT * FROM credits_ledger WHERE user_id = 6 AND ly_do = 'nhiem_vu_cong_dong'")
        ledger_minh = cur.fetchone()
        self.assertIsNotNone(ledger_minh)
        self.assertEqual(ledger_minh["bien_dong"], 2.0)
        self.assertEqual(ledger_minh["ly_do"], "nhiem_vu_cong_dong")

        # 2. Kiểm tra Hà: vắng mặt, không thay đổi số dư, không có ledger
        cur.execute("SELECT so_du_gio FROM users WHERE id = 7")
        ha_balance_after = cur.fetchone()[0]
        self.assertEqual(ha_balance_after, ha_balance_before)

        cur.execute("SELECT * FROM credits_ledger WHERE user_id = 7 AND ly_do = 'nhiem_vu_cong_dong'")
        ledger_ha = cur.fetchone()
        self.assertIsNone(ledger_ha)

        # 3. Kiểm tra trạng thái trong task_registrations
        cur.execute("SELECT trang_thai FROM task_registrations WHERE id = ?", (reg_minh_id,))
        self.assertEqual(cur.fetchone()[0], "hoan_thanh")

        cur.execute("SELECT trang_thai FROM task_registrations WHERE id = ?", (reg_ha_id,))
        self.assertEqual(cur.fetchone()[0], "vang_mat")

        conn.close()

    def test_05_ai_recommend_tasks_and_logs(self):
        """
        [TEST CASE 5]: AI GỢI Ý NHIỆM VỤ:
        - Mục 'Việc phù hợp với bạn' gợi ý tối đa 3 nhiệm vụ phù hợp với học sinh.
        - Mỗi nhiệm vụ có lời giải thích tiếng Việt sư phạm ngắn gọn.
        - Ghi vết minh bạch vào bảng ai_logs (chuc_nang = 'goi_y_nhiem_vu').
        """
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT * FROM community_tasks WHERE trang_thai IN ('mo_dang_ky', 'mo')")
        open_tasks = [dict(r) for r in cur.fetchall()]

        # Gọi hàm AI gợi ý cho học sinh An (id=3)
        recommended, is_live = ai_recommend_tasks(conn, 3, open_tasks)
        self.assertTrue(len(recommended) > 0 and len(recommended) <= 3)

        # Kiểm tra mỗi task có lý do giải thích
        for task in recommended:
            self.assertIn("ly_do_ai_goi_y", task)
            self.assertTrue(len(task["ly_do_ai_goi_y"]) > 5)

        # Kiểm tra ghi log vào bảng ai_logs với chuc_nang = 'goi_y_nhiem_vu'
        cur.execute("SELECT * FROM ai_logs WHERE user_id = 3 AND chuc_nang = 'goi_y_nhiem_vu' ORDER BY id DESC LIMIT 1")
        log_entry = cur.fetchone()
        self.assertIsNotNone(log_entry)
        self.assertEqual(log_entry["chuc_nang"], "goi_y_nhiem_vu")
        conn.close()

        # Kiểm tra hiển thị mục 'Việc phù hợp với bạn' trên giao diện /community
        self.login("HS12001")
        resp = self.client.get("/community")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("VIỆC PHÙ HỢP VỚI BẠN".encode("utf-8"), resp.data)
        self.assertIn("Lý do AI gợi ý".encode("utf-8"), resp.data)

    def test_06_landing_page_community_block(self):
        """
        [TEST CASE 6]: Landing page (/) hiển thị khối 'Vì cộng đồng':
        - Tổng giờ công ích toàn trường.
        - Danh sách các nhiệm vụ gần nhất.
        """
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("VÌ CỘNG ĐỒNG".encode("utf-8"), resp.data)
        self.assertIn("Tổng giờ công ích toàn trường".encode("utf-8"), resp.data)
        self.assertIn("Dọn rác bãi biển Hạ Long sáng Chủ nhật".encode("utf-8"), resp.data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
