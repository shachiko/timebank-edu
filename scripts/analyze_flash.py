with open('unwrapped_flash.txt', 'r', encoding='utf-8') as f:
    lines = f.readlines()

f_strings = [l for l in lines if 'flash(f"' in l or "flash(f'" in l]
plain_strings = [l for l in lines if 'flash("' in l or "flash('" in l]
print(f"Plain strings: {len(plain_strings)}, f-strings: {len(f_strings)}, total: {len(lines)}")

print("\nSample f-strings:")
for l in f_strings[:10]:
    print(" ", l.strip())

print("\nSample plain strings:")
for l in plain_strings[:10]:
    print(" ", l.strip())
