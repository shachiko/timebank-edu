import re

vn_char_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]', re.IGNORECASE)

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

flash_calls = []
for idx, line in enumerate(lines, 1):
    s = line.strip()
    if 'flash(' in s and vn_char_pattern.search(s):
        if 'flash(_(' not in s and 'flash(_l(' not in s:
            flash_calls.append((idx, line))

print(f"Total unwrapped flash calls: {len(flash_calls)}")
with open('unwrapped_flash.txt', 'w', encoding='utf-8') as f:
    for idx, line in flash_calls:
        f.write(f"L{idx}: {line}")
print("Saved to unwrapped_flash.txt")
