import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

vn_char_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]', re.IGNORECASE)

new_lines = []
modified_count = 0

for line in lines:
    s = line.strip()
    if 'flash(' in s and vn_char_pattern.search(s) and 'flash(_(' not in s and 'flash(_l(' not in s:
        # Check plain string: flash("...", "cat") or flash('...', 'cat')
        # Regex for plain double quotes
        m_plain_double = re.search(r'flash\("([^"]+)"(\s*,\s*["\']\w+["\']\s*)\)', line)
        m_plain_single = re.search(r'flash\(\'([^\']+)\'(\s*,\s*["\']\w+["\']\s*)\)', line)
        
        if m_plain_double and not m_plain_double.group(1).startswith('f'):
            # Double quote plain
            msg = m_plain_double.group(1)
            cat = m_plain_double.group(2)
            # Avoid if contains curly braces or quotes
            old_call = f'flash("{msg}"{cat})'
            new_call = f'flash(_("{msg}"){cat})'
            if old_call in line:
                line = line.replace(old_call, new_call)
                modified_count += 1
                new_lines.append(line)
                continue
                
        if m_plain_single:
            msg = m_plain_single.group(1)
            cat = m_plain_single.group(2)
            old_call = f"flash('{msg}'{cat})"
            new_call = f"flash(_('{msg}'){cat})"
            if old_call in line:
                line = line.replace(old_call, new_call)
                modified_count += 1
                new_lines.append(line)
                continue

    new_lines.append(line)

new_content = '\n'.join(new_lines)
with open('app.py', 'w', encoding='utf-8') as f:
    f.write(new_content)

print(f"Pass 1: Wrapped {modified_count} plain flash calls in app.py")
