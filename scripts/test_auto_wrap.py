import re
import os

VN_CHARS = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]'
VN_PATTERN = re.compile(VN_CHARS, re.IGNORECASE)

def wrap_tag_contents(html_content):
    # 1. Attributes: placeholder="VN", title="VN", aria-label="VN"
    def repl_attr(m):
        attr = m.group(1)
        val = m.group(2)
        if VN_PATTERN.search(val) and not val.startswith('{{') and not val.endswith('}}'):
            escaped = val.replace("'", "\\'")
            return f'{attr}="{{{{ _(\'{escaped}\') }}}}"'
        return m.group(0)

    html_content = re.sub(r'(placeholder|title|aria-label)="([^"]+)"', repl_attr, html_content)

    # 2. Confirm / Alert
    def repl_confirm(m):
        func = m.group(1)
        quote = m.group(2)
        msg = m.group(3)
        if VN_PATTERN.search(msg) and not msg.startswith('{{') and not msg.endswith('}}'):
            escaped = msg.replace("'", "\\'")
            return f'{func}("{{{{ _(\'{escaped}\') }}}}")'
        return m.group(0)

    html_content = re.sub(r'\b(confirm|alert)\(([\'"])([^\'"]+)\2\)', repl_confirm, html_content)

    # 3. Simple text nodes between > and <
    # e.g. >Tiêu đề< or >   Tiêu đề   < or ><i ...></i> Tiêu đề<
    # We should only match plain text without { or } inside
    def repl_text_node(m):
        leading_ws = m.group(1)
        text = m.group(2).strip()
        trailing_ws = m.group(3)
        
        # Check if text contains VN characters and no Jinja tags
        if VN_PATTERN.search(text) and '{{' not in text and '{%' not in text and '<' not in text and '>' not in text:
            # Check if text is already wrapped
            if text.startswith("_('") or text.startswith('_("'):
                return m.group(0)
            escaped = text.replace("'", "\\'")
            return f'>{leading_ws}{{{{ _(\'{escaped}\') }}}}{trailing_ws}<'
        return m.group(0)

    html_content = re.sub(r'>(\s*)([^<>{}\n\r]+)(\s*)<', repl_text_node, html_content)

    return html_content

if __name__ == '__main__':
    test_file = 'templates/noi_quy.html'
    with open(test_file, 'r', encoding='utf-8') as f:
        orig = f.read()
    wrapped = wrap_tag_contents(orig)
    print(f"Original length: {len(orig)}, Wrapped length: {len(wrapped)}")
    with open('test_wrapped_noi_quy.html', 'w', encoding='utf-8') as f:
        f.write(wrapped)
    print("Saved test_wrapped_noi_quy.html")
