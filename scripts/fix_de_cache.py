import json

with open('scripts/translations_cache.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

for k, v in cache.items():
    if '80%%' in k and '%(rate)' in k:
        if 'de' in v:
            v['de'] = "Die Zeit, die für das gemeinsame Online-Lernen aufgewendet wird, hat nicht 80%% der Vorschriften erreicht (nur %(rate).1f%% / 80%% erreicht). Die Sitzung wurde in den Status 'Bestätigung erforderlich' verschoben, damit der Lehrer sie manuell überprüfen und genehmigen kann."

with open('scripts/translations_cache.json', 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print('Updated translations_cache.json!')
