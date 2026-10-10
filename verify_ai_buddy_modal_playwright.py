# -*- coding: utf-8 -*-
"""
Script kiểm tra giao diện Modal "AI Gợi Ý Bạn Học Thông Minh" bằng Playwright.
Xác minh nút "Đăng ký học" / "Đã gửi yêu cầu" bên phải card không còn bị tràn/cắt mất viền.
"""
import os
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

ARTIFACTS_DIR = Path(r"C:\Users\MrPeter\.gemini\antigravity-ide\brain\38c84a5c-528a-4267-a0fa-01a1cb31be1e")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 1. Desktop Viewport (1280 x 800)
        context = browser.new_context(viewport={"width": 1280, "height": 800})
        page = context.new_page()

        print("[1] Đăng nhập HS12001...")
        page.goto("http://127.0.0.1:5000/login", wait_until="networkidle")
        page.fill('input[name="ma_hoc_sinh"]', "HS12001")
        page.fill('input[name="mat_khau"]', "admin123")
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle")

        print("[2] Mở trang profile...")
        page.goto("http://127.0.0.1:5000/profile", wait_until="networkidle")

        print("[3] Mở modal AI Gợi Ý Bạn Học Thông Minh...")
        page.click("#btnAiSuggestBuddiesProfile")
        page.wait_for_selector("#modalAiBuddySuggestions.show", state="visible")

        # Chờ API smart-suggestions tải xong
        page.wait_for_selector("#aiBuddyResults:not(.d-none)", state="visible", timeout=10000)
        page.wait_for_selector(".card", state="visible")
        time.sleep(1)

        # Chụp ảnh modal trên desktop
        modal_el = page.locator("#modalAiBuddySuggestions .modal-content")
        desktop_img = ARTIFACTS_DIR / f"ai_buddy_modal_desktop_{int(time.time()*1000)}.png"
        modal_el.screenshot(path=str(desktop_img))
        print(f"-> Chụp ảnh desktop: {desktop_img}")

        # 2. Medium Viewport (768 x 800 - giống kích thước tablet/split screen của user)
        context_med = browser.new_context(viewport={"width": 768, "height": 800})
        page_med = context_med.new_page()
        page_med.goto("http://127.0.0.1:5000/login", wait_until="networkidle")
        page_med.fill('input[name="ma_hoc_sinh"]', "HS12001")
        page_med.fill('input[name="mat_khau"]', "admin123")
        page_med.click('button[type="submit"]')
        page_med.wait_for_load_state("networkidle")

        page_med.goto("http://127.0.0.1:5000/profile", wait_until="networkidle")
        page_med.click("#btnAiSuggestBuddiesProfile")
        page_med.wait_for_selector("#modalAiBuddySuggestions.show", state="visible")
        page_med.wait_for_selector("#aiBuddyResults:not(.d-none)", state="visible", timeout=10000)
        time.sleep(1)

        modal_med = page_med.locator("#modalAiBuddySuggestions .modal-content")
        med_img = ARTIFACTS_DIR / f"ai_buddy_modal_768_{int(time.time()*1000)}.png"
        modal_med.screenshot(path=str(med_img))
        print(f"-> Chụp ảnh 768px: {med_img}")

        # 3. Mobile Viewport (390 x 844)
        context_mobile = browser.new_context(viewport={"width": 390, "height": 844})
        page_mob = context_mobile.new_page()
        page_mob.goto("http://127.0.0.1:5000/login", wait_until="networkidle")
        page_mob.fill('input[name="ma_hoc_sinh"]', "HS12001")
        page_mob.fill('input[name="mat_khau"]', "admin123")
        page_mob.click('button[type="submit"]')
        page_mob.wait_for_load_state("networkidle")

        page_mob.goto("http://127.0.0.1:5000/profile", wait_until="networkidle")
        page_mob.click("#btnAiSuggestBuddiesProfile")
        page_mob.wait_for_selector("#modalAiBuddySuggestions.show", state="visible")
        page_mob.wait_for_selector("#aiBuddyResults:not(.d-none)", state="visible", timeout=10000)
        time.sleep(1)

        modal_mob = page_mob.locator("#modalAiBuddySuggestions .modal-content")
        mob_img = ARTIFACTS_DIR / f"ai_buddy_modal_mobile_{int(time.time()*1000)}.png"
        modal_mob.screenshot(path=str(mob_img))
        print(f"-> Chụp ảnh mobile: {mob_img}")

        browser.close()
        print("HOÀN TẤT CHỤP ẢNH XÁC MINH!")

if __name__ == "__main__":
    main()
