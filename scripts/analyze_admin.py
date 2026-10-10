import sys
import os
sys.path.insert(0, os.getcwd())

from scripts.scan_unwrapped import find_unwrapped_vn_in_html

un = find_unwrapped_vn_in_html('templates/admin.html')
clean_un = [x for x in un if not x[1].startswith('//') and not x[1].startswith('/*')]

print(f"Total unwrapped in admin.html: {len(clean_un)}")

with open('unwrapped_admin.txt', 'w', encoding='utf-8') as f:
    for lno, raw, cleaned in clean_un:
        f.write(f"{lno}: {raw}\n")

print("Written to unwrapped_admin.txt")
