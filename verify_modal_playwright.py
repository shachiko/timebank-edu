# -*- coding: utf-8 -*-
"""
Automation script to visually test and verify the Redesigned Study Needs Modal using Playwright.
Generates screenshots for:
1. Desktop 2-column modal with chips, level, note, multi-slot schedule
2. Mobile responsive stacked view (<768px)
3. Profile page updated with new chips and schedule
4. Modal re-opened with restored data
"""
import sys
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = Path(r"C:\Users\MrPeter\.gemini\antigravity-ide\brain\38c84a5c-528a-4267-a0fa-01a1cb31be1e")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Desktop context
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        # Handle dialogs automatically (alert 'Đã cập nhật thành công!')
        page.on("dialog", lambda dialog: dialog.accept())

        print("[1] Đăng nhập tài khoản HS12001...")
        page.goto("http://127.0.0.1:5000/login", wait_until="networkidle")
        page.fill('input[name="ma_hoc_sinh"]', "HS12001")
        page.fill('input[name="mat_khau"]', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        print("[2] Điều hướng tới trang hồ sơ cá nhân...")
        page.goto("http://127.0.0.1:5000/profile", wait_until="networkidle")

        print("[3] Mở modal Môn Cần Hỗ Trợ & Khung Giờ Rảnh...")
        page.click("#btnEditStudyNeeds")
        page.wait_for_selector("#modalStudyNeeds.show", state="visible")
        time.sleep(0.5)

        print("[4] Thêm các môn học từ dropdown (Toán, Tiếng Anh, Tin học)...")
        # Chọn Toán
        page.select_option("#selectSubjectDropdown", "Toán")
        time.sleep(0.3)
        # Chọn Tiếng Anh
        page.select_option("#selectSubjectDropdown", "Tiếng Anh")
        time.sleep(0.3)
        # Chọn Tin học
        page.select_option("#selectSubjectDropdown", "Tin học")
        time.sleep(0.3)

        # Chọn mức độ Nâng cao
        page.select_option("#selectStudyLevel", "nang_cao")

        # Nhập ghi chú
        page.fill("#inputStudyNote", "Hình không gian, giải tích & thuật toán Python")

        print("[5] Cấu hình khung giờ rảnh (T2 2 khung giờ, T4 1 khung giờ)...")
        # Check T2
        chk_t2 = page.locator("#chk_t2")
        if not chk_t2.is_checked():
            chk_t2.check()
        time.sleep(0.3)

        # Thêm khung giờ thứ 2 cho T2
        page.click("#btnAddSlot_t2")
        time.sleep(0.3)
        # Set giờ slot 2 của T2
        slot2_starts = page.locator('input[name="slot_start_t2"]')
        slot2_ends = page.locator('input[name="slot_end_t2"]')
        slot2_starts.nth(1).fill("14:00")
        slot2_ends.nth(1).fill("16:00")

        # Check T4
        chk_t4 = page.locator("#chk_t4")
        if not chk_t4.is_checked():
            chk_t4.check()
        time.sleep(0.3)
        page.locator('input[name="slot_start_t4"]').nth(0).fill("19:00")
        page.locator('input[name="slot_end_t4"]').nth(0).fill("21:00")

        # Ghi chú thêm
        page.fill("#inputGioRanhKhac", "Linh hoạt trao đổi trực tuyến cuối tuần")

        print("[6] Chụp ảnh Modal 2 cột Desktop...")
        shot1 = ARTIFACTS_DIR / "desktop_modal_redesigned.png"
        page.screenshot(path=str(shot1))
        print(f"  -> Lưu tại: {shot1}")

        print("[7] Chụp ảnh Modal Responsive Mobile (390x844)...")
        page.set_viewport_size({"width": 390, "height": 844})
        time.sleep(0.5)
        shot2 = ARTIFACTS_DIR / "mobile_modal_redesigned.png"
        page.screenshot(path=str(shot2))
        print(f"  -> Lưu tại: {shot2}")

        print("[8] Chuyển lại Desktop và bấm [💾 Lưu thay đổi]...")
        page.set_viewport_size({"width": 1280, "height": 800})
        time.sleep(0.3)
        page.click("#btnSaveStudyNeeds")
        page.wait_for_load_state("networkidle")
        time.sleep(1.0)

        print("[9] Chụp ảnh Trang Hồ sơ sau khi cập nhật thành công...")
        shot3 = ARTIFACTS_DIR / "profile_after_save.png"
        page.screenshot(path=str(shot3))
        print(f"  -> Lưu tại: {shot3}")

        print("[10] Mở lại Modal để kiểm chứng dữ liệu đã lưu phục hồi chính xác...")
        page.click("#btnEditStudyNeeds")
        page.wait_for_selector("#modalStudyNeeds.show", state="visible")
        time.sleep(0.5)
        shot4 = ARTIFACTS_DIR / "modal_restored_data.png"
        page.screenshot(path=str(shot4))
        print(f"  -> Lưu tại: {shot4}")

        browser.close()
        print("\nHOÀN THÀNH 100% CÁC BƯỚC KIỂM THỬ GIAO DIỆN VÀ CHỤP ẢNH MINH CHỨNG!")

if __name__ == "__main__":
    main()
