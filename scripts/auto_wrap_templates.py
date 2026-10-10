import re
import os
import glob

VN_CHARS = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]'
VN_PATTERN = re.compile(VN_CHARS, re.IGNORECASE)

def wrap_html_content(html):
    # 1. block title
    def repl_title(m):
        content = m.group(1).strip()
        if VN_PATTERN.search(content) and not content.startswith('{{'):
            escaped = content.replace("'", "\\'")
            return "{% block title %}{{ _('" + escaped + "') }}{% endblock %}"
        return m.group(0)
    html = re.sub(r'{%\s*block\s+title\s*%}(.*?){%\s*endblock\s*%}', repl_title, html, flags=re.DOTALL)

    # 2. Attributes: placeholder, title, aria-label
    def repl_attr(m):
        attr = m.group(1)
        val = m.group(2)
        if VN_PATTERN.search(val) and not val.startswith('{{') and not val.endswith('}}'):
            escaped = val.replace("'", "\\'")
            return attr + '="{{ _(\'' + escaped + '\') }}"'
        return m.group(0)
    html = re.sub(r'(placeholder|title|aria-label)="([^"]+)"', repl_attr, html)

    # 3. Confirm / alert
    def repl_confirm(m):
        func = m.group(1)
        quote = m.group(2)
        msg = m.group(3)
        if VN_PATTERN.search(msg) and not msg.startswith('{{') and not msg.endswith('}}'):
            escaped = msg.replace("'", "\\'")
            return func + '("{{ _(\'' + escaped + '\') }}")'
        return m.group(0)
    html = re.sub(r'\b(confirm|alert)\(([\'"])([^\'"]+)\2\)', repl_confirm, html)

    # 4. Jinja or fallback: or 'VN_TEXT' or or "VN_TEXT"
    def repl_or(m):
        prefix = m.group(1)
        val = m.group(2)
        if VN_PATTERN.search(val):
            escaped = val.replace("'", "\\'")
            return prefix + "_('" + escaped + "')"
        return m.group(0)
    html = re.sub(r'(\bor\s+[\'"])([^\'"]+)([\'"])', repl_or, html)

    # 5. Text nodes between > and <
    def repl_text_node(m):
        leading_ws = m.group(1)
        text = m.group(2).strip()
        trailing_ws = m.group(3)
        
        # Must contain VN, no braces, no tags
        if VN_PATTERN.search(text) and '{{' not in text and '{%' not in text and '<' not in text and '>' not in text:
            if text.startswith("_('") or text.startswith('_("'):
                return m.group(0)
            escaped = text.replace("'", "\\'")
            return '>' + leading_ws + '{{ _(\'' + escaped + '\') }}' + trailing_ws + '<'
        return m.group(0)

    # Run twice to catch adjacent text fragments
    html = re.sub(r'>(\s*)([^<>{}\n\r]+)(\s*)<', repl_text_node, html)
    html = re.sub(r'>(\s*)([^<>{}\n\r]+)(\s*)<', repl_text_node, html)

    return html

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        orig = f.read()

    new_content = wrap_html_content(orig)
    if new_content != orig:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

if __name__ == '__main__':
    templates = sorted(glob.glob('templates/**/*.html', recursive=True))
    updated = []
    for t in templates:
        norm_p = t.replace('\\', '/')
        if norm_p not in [
            'templates/index.html',
            'templates/admin.html',
            'templates/base.html',
            'templates/admin_accounts.html',
            'templates/register.html',
            'templates/login.html'
        ]:
            if process_file(t):
                updated.append(norm_p)

    print(f"Updated {len(updated)} templates:")
    for u in updated:
        print(f"  {u}")
