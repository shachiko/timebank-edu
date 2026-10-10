with open('unwrapped_flash.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

f_strings = [l for l in lines if 'flash(f"' in l or "flash(f'" in l]

print(f"Total f-strings: {len(f_strings)}")
for idx, l in enumerate(f_strings, 1):
    print(f"{idx}: {l.strip()}")
