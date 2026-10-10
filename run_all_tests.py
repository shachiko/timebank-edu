# -*- coding: utf-8 -*-
import subprocess
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

test_files = [
    "test_m0.py",
    "test_m1.py",
    "test_m2.py",
    "test_m3.py",
    "test_m3_plus.py",
    "test_m4_lite.py",
    "test_m5_blog.py",
    "test_m6.py",
    "test_m_chat.py",
    "test_deploy.py",
    "test_prompt14_ai.py",
    "test_prompt15_rebrand.py",
    "test_prompt17_multitenant.py",
    "test_prompt18_forum_drive.py",
    "test_prompt19_community_market.py",
    "test_prompt20_migration.py",
    "test_prompt21_ui_polish.py",
    "test_prompt22_jitsi_jwt.py",
    "test_prompt22_three_engines.py",
    "test_prompt23_account_management.py",
    "test_prompt23_5_auto_superadmin.py",
    "test_prompt24_postgres_groupby.py",
    "test_prompt24_drive_packages.py",
    "test_prompt25_responsive_header.py",
    "test_prompt26_multi_upload_500mb.py",
    "test_prompt27_postgres_round.py",
    "test_prompt28_hide_google_drive.py",
    "test_prompt29_admin_tabs.py",
    "test_prompt30_school_management.py",
    "test_prompt31_ui_wording_color.py",
    "test_prompt32_school_hide_management.py",
    "test_prompt16_multilingual.py",
    "test_prompt_community_management.py",
    "test_prompt_import_users.py",
    "test_prompt_export_invite_codes.py",
    "test_prompt_smart_features.py",
    "test_prompt_role_menus.py",
    "test_hotfix_import_and_school_display.py",
    "test_redesign_study_needs_modal.py",
    "test_prompt_admin_enhancements.py"
]

results = {}
all_passed = True

print("=" * 70)
print("CHẠY TOÀN BỘ REGRESSION TEST SUITE CHO TIMEBANK EDU (COMMUNITY MANAGEMENT)")
print("=" * 70)

for tf in test_files:
    print(f"\n[EXEC] Đang chạy {tf} ...")
    cmd = [sys.executable, "-X", "utf8", tf]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        print(f"  --> [PASS] {tf}")
        results[tf] = "PASS"
    else:
        print(f"  --> [FAIL] {tf}")
        print("--- STDERR SUMMARY ---")
        for line in res.stderr.splitlines():
            if any(k in line for k in ["FAIL:", "ERROR:", "AssertionError", "test_0", "Traceback", "File "]):
                print("  ", line)
        if not any(k in res.stderr for k in ["FAIL:", "ERROR:"]):
            print(res.stderr[-800:])
        results[tf] = "FAIL"
        all_passed = False

print("\n" + "=" * 70)
print("TỔNG KẾT KẾT QUẢ KIỂM THỬ:")
print("=" * 70)
for tf, st in results.items():
    print(f"  * {tf:<32}: {st}")

print("=" * 70)
if all_passed:
    print(f"XÁC NHẬN: 100% TẤT CẢ {len(test_files)} BỘ TEST PASSED! SẴN SÀNG TRIỂN KHAI & PUSH GIT!")
    sys.exit(0)
else:
    print("CẢNH BÁO: CÓ TEST CASE THẤT BẠI. CẦN KHẮC PHỤC TRƯỚC KHI PUSH GIT.")
    sys.exit(1)
