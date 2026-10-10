import json

with open('scripts/translations_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

for k, v in cache.items():
    if '%(rate)' in k:
        if 'zh' in v:
            v['zh'] = v['zh'].replace('%(率).1f%%', '%(rate).1f%%').replace('%(率)', '%(rate)')
        if 'de' in v:
            v['de'] = v['de'].replace('%(Rate).1f%%', '%(rate).1f%%').replace('%(Rate)', '%(rate)')
            v['de'] = v['de'].replace('% %', '%%').replace('80 % %', '80%%').replace('80 %', '80%%')

with open('scripts/translations_cache.json', 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print('Updated translations_cache.json!')
