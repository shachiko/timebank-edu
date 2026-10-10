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
    for ph in original_placeholders:
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

    placeholders = list(set(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]|%[sdf]|{[0-9]+}', text)))
    mapping = {}
    protected = text

    for i, p in enumerate(placeholders):
        token = f"VAR{i}X"
        mapping[token] = p
        protected = protected.replace(p, token)

    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=vi&tl={target_lang}&dt=t&q=" + urllib.parse.quote(protected)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                trans = "".join([part[0] for part in data[0] if part and part[0]])
                break
        except Exception:
            if attempt == 2:
                return text
            time.sleep(0.5)

    for token, orig in mapping.items():
        trans = re.sub(r'(?i)\b' + token + r'\b|\bVAR\s*' + token[3:-1] + r'\s*X\b', orig, trans)
        trans = trans.replace(token, orig)

    return clean_placeholders(trans, placeholders)

def translate_batch(batch, target_lang):
    """Translate a batch of strings using delimiter |||."""
    delim = " ||| "
    # Prepare batch with placeholders protected
    protected_items = []
    item_mappings = []

    for text in batch:
        placeholders = list(set(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]|%[sdf]|{[0-9]+}', text)))
        mapping = {}
        protected = text
        for i, p in enumerate(placeholders):
            token = f"VAR{i}X"
            mapping[token] = p
            protected = protected.replace(p, token)
        protected_items.append(protected)
        item_mappings.append((mapping, placeholders))

    combined = delim.join(protected_items)
    url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=vi&tl={target_lang}&dt=t&q=" + urllib.parse.quote(combined)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            full = "".join([part[0] for part in data[0] if part and part[0]])
            parts = [p.strip() for p in full.split("|||")]
    except Exception as e:
        parts = []

    # If count matches, post-process each part
    if len(parts) == len(batch):
        results = []
        for part, (mapping, placeholders) in zip(parts, item_mappings):
            for token, orig in mapping.items():
                part = re.sub(r'(?i)\b' + token + r'\b|\bVAR\s*' + token[3:-1] + r'\s*X\b', orig, part)
                part = part.replace(token, orig)
            part = clean_placeholders(part, placeholders)
            results.append(part)
        return results

    # If mismatch, fallback to individual translation
    return [translate_single(item, target_lang) for item in batch]

def process_catalogs():
    cache = load_cache()
    locales = ["en", "zh", "fr", "de"]

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

    print(f"Total unique msgids: {len(all_msgids)}")

    # For each language, find items missing from cache
    for lang in locales:
        missing_for_lang = []
        for msgid in all_msgids:
            if msgid not in cache:
                cache[msgid] = {}

            # Check manual translations
            if msgid in MANUAL_TRANSLATIONS.get(lang, {}):
                cache[msgid][lang] = MANUAL_TRANSLATIONS[lang][msgid]
                continue

            # Check catalog existing
            cat = catalogs[lang][1]
            existing_msg = cat.get(msgid)
            if existing_msg and existing_msg.string and existing_msg.string != msgid:
                cache[msgid][lang] = existing_msg.string
                continue

            # Check cache
            if lang in cache[msgid] and cache[msgid][lang]:
                continue

            missing_for_lang.append(msgid)

        print(f"[{lang}] Missing strings to translate: {len(missing_for_lang)}")

        if not missing_for_lang:
            continue

        # Chunk into batches of 15
        batch_size = 15
        batches = [missing_for_lang[i:i + batch_size] for i in range(0, len(missing_for_lang), batch_size)]

        def batch_worker(b):
            res = translate_batch(b, lang)
            return list(zip(b, res))

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_b = {executor.submit(batch_worker, b): b for b in batches}
            done_count = 0
            for future in as_completed(future_to_b):
                pairs = future.result()
                for orig, trans in pairs:
                    cache[orig][lang] = trans
                done_count += len(pairs)
                if done_count % 90 == 0 or done_count >= len(missing_for_lang):
                    print(f"[{lang}] Progress: {done_count}/{len(missing_for_lang)}")
                    save_cache(cache)

        save_cache(cache)
        print(f"[{lang}] Done translating missing strings.")

    # Apply back to catalogs
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
                    orig_ph = sorted(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]', msg.id))
                    trans_ph = sorted(re.findall(r'%\([a-zA-Z0-9_]+\)[sdf]', val))
                    if orig_ph != trans_ph:
                        val = clean_placeholders(val, orig_ph)
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
