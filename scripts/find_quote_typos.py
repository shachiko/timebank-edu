import glob

all_html = sorted(list(set(glob.glob('templates/**/*.html', recursive=True) + glob.glob('templates/*.html'))))

for h in all_html:
    with open(h, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for idx, line in enumerate(lines, 1):
        if "'_(" in line or '"_(' in line:
            print(f"{h}:{idx}: {line.strip()}")
