import os
import re
import sys

vn_char_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]')

# Regex to check if a Vietnamese segment is wrapped inside _(...) or _l(...) or {{ _(...) }}
# Let's write a parser that finds text outside Jinja translation tags in HTML

def analyze_html_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find lines
    lines = content.splitlines()
    findings = []

    for lno, line in enumerate(lines, 1):
        s = line.strip()
        if not s or s.startswith('<!--') or s.startswith('{#') or s.startswith('*'):
            continue
        if vn_char_pattern.search(line):
            # Check if this line is completely wrapped in _(...) or {{ _(...) }}
            # Let's find matches of VN words
            # If the line has _('...') or _("..."), let's see what is inside and what is outside
            findings.append((lno, s))
            
    return findings

if __name__ == '__main__':
    templates_dir = 'templates'
    summary = {}
    for root, dirs, files in os.walk(templates_dir):
        for f in files:
            if f.endswith('.html'):
                p = os.path.join(root, f)
                res = analyze_html_file(p)
                if res:
                    summary[p] = res
                    
    # Also check app.py
    app_res = analyze_html_file('app.py')
    summary['app.py'] = app_res

    print(f"Total files with Vietnamese characters: {len(summary)}")
    for p, items in sorted(summary.items(), key=lambda x: len(x[1]), reverse=True):
        print(f"{p}: {len(items)} lines")
