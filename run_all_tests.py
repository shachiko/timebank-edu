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
    "test_prompt23_account_management.py"
]

results = {}
all_passed = True

print("=" * 70)
print("CHẠY TOÀN BỘ REGRESSION TEST SUITE CHO TIMEBANK EDU (PROMPT 23)")
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
        print("--- STDOUT ---")
        print(res.stdout[-500:] if len(res.stdout) > 500 else res.stdout)
        print("--- STDERR ---")
        print(res.stderr[-500:] if len(res.stderr) > 500 else res.stderr)
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
