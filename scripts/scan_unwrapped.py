import os
import re

vn_char_pattern = re.compile(r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]', re.IGNORECASE)

# Pattern to strip out already-wrapped Jinja expressions:
# {{ _('...') }} or {{ _("...") }} or {{ _l('...') }} etc.
# Also jinja comments {# ... #}
# Also html comments <!-- ... -->
# Also <script>...</script> or <style>...</style> if any (though script strings might also need i18n, let's see)

def find_unwrapped_vn_in_html(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # Remove comments
    content_no_comments = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)
    content_no_comments = re.sub(r'{#.*?#}', '', content_no_comments, flags=re.DOTALL)

    # Let's check lines
    lines = content_no_comments.splitlines()
    unwrapped = []

    for idx, line in enumerate(lines, 1):
        if not vn_char_pattern.search(line):
            continue
        
        # Now remove all {{ _(...) }} from this line
        # Regex to remove {{ _(...) }} including multiline or nested
        line_cleaned = re.sub(r'\{\{\s*_\([\'"].*?[\'"]\)\s*\}\}', '', line)
        line_cleaned = re.sub(r'\{\{\s*_l\([\'"].*?[\'"]\)\s*\}\}', '', line)
        line_cleaned = re.sub(r'_\([\'"].*?[\'"]\)', '', line_cleaned)

        # Check if line still has Vietnamese characters
        if vn_char_pattern.search(line_cleaned):
            unwrapped.append((idx, line.strip(), line_cleaned.strip()))

    return unwrapped

if __name__ == '__main__':
    for target in ['templates/index.html', 'templates/base.html', 'templates/login.html', 'templates/register.html', 'templates/admin.html']:
        res = find_unwrapped_vn_in_html(target)
        print(f"=== {target}: {len(res)} unwrapped lines ===")
        for lno, raw, cleaned in res[:10]:
            print(f"  Line {lno}: {raw[:90]}")
