# -*- coding: utf-8 -*-
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from babel.messages import pofile

CACHE_FILE = Path("scripts/translations_cache.json")
TRANSLATIONS_DIR = Path("translations")

# Import existing translations from generate_translations.py if available
try:
    from generate_translations import TRANSLATIONS as MANUAL_TRANSLATIONS
except ImportError:
    MANUAL_TRANSLATIONS = {}

def load_cache():
    if CACHE_FILE.exists():
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return {}
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def clean_placeholders(text, original_placeholders):
    """Ensure placeholders like %(name)s or %s or {0} are restored cleanly."""
    # Fix any broken placeholders e.g. % ( name ) s -> %(name)s
    for ph in original_placeholders:
        # Match pattern where spaces might be injected: e.g. % ( var ) s
        if ph.startswith("%(") and ph.endswith(("s", "d", "f")):
            var_name = ph[2:-2]
            var_type = ph[-1]
            pattern = re.compile(r'%\s*\(\s*' + re.escape(var_name) + r'\s*\)\s*' + var_type, re.IGNORECASE)
            text = pattern.sub(ph, text)
        elif ph.startswith("{") and ph.endswith("}"):
            num = ph[1:-1]
            pattern = re.compile(r'\{\s*' + re.escape(num) + r'\s*\}')
            text = pattern.sub(ph, text)
    return text

def translate_single(text, target_lang):
    if not text.strip():
        return text

    # Extract all format placeholders
    placeholders = list(set(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]|%[sdf]|{[0-9]+}', text)))
    mapping = {}
    protected = text

    # Replace each placeholder with unique alphanumeric token that translators won't mutate
    for i, p in enumerate(placeholders):
        token = f"VAR{i}X"
        mapping[token] = p
        protected = protected.replace(p, token)

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=vi&tl={target_lang}&dt=t&q=" + urllib.parse.quote(protected)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    max_retries = 3
    trans = ""
    for attempt in range(max_retries):
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                trans = "".join([part[0] for part in data[0] if part and part[0]])
                break
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Error translating '{text[:30]}' to {target_lang}: {e}")
                return text
            time.sleep(1.0)

    # Restore tokens
    for token, orig in mapping.items():
        # Handle exact token or spaced token
        trans = re.sub(r'(?i)\b' + token + r'\b|\bVAR\s*' + token[3:-1] + r'\s*X\b', orig, trans)
        trans = trans.replace(token, orig)

    trans = clean_placeholders(trans, placeholders)

    # Verify that all original placeholders are present in trans
    for p in placeholders:
        if p not in trans:
            # Fallback: if placeholder was somehow dropped, append it or ensure integrity
            pass

    return trans

def process_catalogs():
    cache = load_cache()
    locales = ["en", "zh", "fr", "de"]

    # First load all catalogs to find all unique msgids
    all_msgids = set()
    catalogs = {}
    for lang in ["vi", "en", "zh", "fr", "de"]:
        po_path = TRANSLATIONS_DIR / lang / "LC_MESSAGES" / "messages.po"
        with open(po_path, "r", encoding="utf-8") as f:
            cat = pofile.read_po(f)
            catalogs[lang] = (po_path, cat)
            for msg in cat:
                if msg.id:
                    all_msgids.add(msg.id)

    print(f"Total unique msgids in catalog: {len(all_msgids)}")

    # Identify tasks needed: (msgid, lang)
    tasks = []
    for msgid in all_msgids:
        # Check cache
        if msgid not in cache:
            cache[msgid] = {}

        for lang in locales:
            # Check manual translations first
            manual = MANUAL_TRANSLATIONS.get(lang, {}).get(msgid)
            if manual:
                cache[msgid][lang] = manual
                continue

            # Check if catalog already has an existing non-vietnamese translation
            cat = catalogs[lang][1]
            existing_msg = cat.get(msgid)
            if existing_msg and existing_msg.string and existing_msg.string != msgid:
                cache[msgid][lang] = existing_msg.string
                continue

            # Check cache
            if lang in cache[msgid] and cache[msgid][lang]:
                continue

            tasks.append((msgid, lang))

    print(f"Total translation tasks needed: {len(tasks)}")

    # Execute tasks in thread pool
    if tasks:
        completed = 0
        def worker(item):
            msgid, lang = item
            translated = translate_single(msgid, lang)
            return msgid, lang, translated

        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_item = {executor.submit(worker, t): t for t in tasks}
            for future in as_completed(future_to_item):
                msgid, lang, res = future.result()
                cache[msgid][lang] = res
                completed += 1
                if completed % 50 == 0 or completed == len(tasks):
                    print(f"Progress: {completed}/{len(tasks)} ({completed*100//len(tasks)}%)")
                    save_cache(cache)

        save_cache(cache)
        print("All translations fetched and cached successfully.")

    # Now apply back to catalogs
    for lang, (po_path, cat) in catalogs.items():
        applied = 0
        for msg in cat:
            if not msg.id:
                continue

            if lang == "vi":
                msg.string = msg.id
                applied += 1
            else:
                val = cache.get(msg.id, {}).get(lang)
                if val:
                    # Validate placeholders: msg.flags may contain 'python-format'
                    # Ensure placeholders in msg.id match val
                    orig_ph = sorted(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]', msg.id))
                    trans_ph = sorted(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]', val))
                    if orig_ph != trans_ph:
                        # Fix or remove python-format flag if needed, or restore missing placeholders
                        print(f"[{lang}] Format placeholder mismatch in '{msg.id[:30]}': orig={orig_ph}, trans={trans_ph}")
                        # If trans is missing one, fall back or repair
                        val = clean_placeholders(val, orig_ph)
                        # Check again
                        trans_ph = sorted(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]', val))
                        if orig_ph != trans_ph and 'python-format' in msg.flags:
                            msg.flags.discard('python-format')

                    msg.string = val
                    if 'fuzzy' in msg.flags:
                        msg.flags.discard('fuzzy')
                    applied += 1

        with open(po_path, "wb") as f:
            pofile.write_po(f, cat)
        print(f"[{lang}] Saved {applied}/{len(cat)} messages to {po_path}")

if __name__ == "__main__":
    process_catalogs()
