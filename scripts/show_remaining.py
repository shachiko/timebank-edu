import sys, os
sys.path.insert(0, os.getcwd())
import glob
from scripts.scan_unwrapped import find_unwrapped_vn_in_html

all_unwrapped = {}
for p in sorted(glob.glob('templates/**/*.html', recursive=True)):
    un = find_unwrapped_vn_in_html(p)
    clean_un = [x for x in un if not x[1].startswith('//') and not x[1].startswith('/*')]
    if clean_un:
        all_unwrapped[p] = clean_un

for p, lines in sorted(all_unwrapped.items(), key=lambda x: len(x[1]), reverse=True):
    print(f"\n=== {p} ({len(lines)}) ===")
    for lno, raw, cleaned in lines:
        print(f"  L{lno}: {raw[:100]}")
