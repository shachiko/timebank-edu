import re
import sys

VN_CHARS = r'[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđĐ]'
VN_PATTERN = re.compile(VN_CHARS, re.IGNORECASE)

def wrap_text_snippet(text):
    text_clean = text.strip()
    if not text_clean:
        return text
    # Escape single quotes if any
    escaped = text_clean.replace("'", "\\'")
    return text.replace(text_clean, f"{{{{ _('{escaped}') }}}}")

print("Module loaded.")
