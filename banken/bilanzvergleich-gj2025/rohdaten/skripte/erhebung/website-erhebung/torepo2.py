"""Website-Erhebung 27.10.2026: verwendete Originaldokumente ins Repo kopieren und dokumente/index.csv fortschreiben."""
import json, os, re, csv, hashlib, shutil, unicodedata, urllib.parse
R = "/home/user/unternehmenskennzahlen/banken/bilanzvergleich-gj2025/"
items = json.load(open('websites_2026-10-27.json'))['items']
files = json.load(open('crawl/dl1.json')) + json.load(open('crawl/manual.json'))
loc = {r['url']: r['file'] for r in files}
idx = list(csv.reader(open(R + 'dokumente/index.csv', encoding='utf-8-sig'), delimiter=';'))
hdr, rows = idx[0], idx[1:]
known = {r[5] for r in rows}; shas = {r[7] for r in rows}
def slug(s):
    s = unicodedata.normalize('NFKD', s.replace('ß', 'ss').replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('Ä', 'Ae').replace('Ö', 'Oe').replace('Ü', 'Ue')).encode('ascii', 'ignore').decode()
    return re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-').lower()[:60]
jobs = [(d['bank'], d['url'], d['typ']) for d in items]
jobs.append(("VR TeilhaberBank Metropolregion Nürnberg eG", [u for u, f in loc.items() if 'f42f9c76' in f][0], "Jahresabschluss HGB (Kurzfassung)"))
new = 0
for bank, u, typ in jobs:
    p = loc.get(u)
    if not p or open(p, 'rb').read(5) != b'%PDF-':
        print('fehlt', bank, u); continue
    sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    if u in known or sha in shas:
        print('schon da', bank); continue
    base = slug(re.sub(r'\.pdf$', '', urllib.parse.unquote(u.split('?')[0]).split('/')[-1], flags=re.I))[:80] or 'dokument'
    d = R + 'dokumente/' + slug(bank) + '/'; os.makedirs(d, exist_ok=True)
    fn = base + '.pdf'
    if os.path.exists(d + fn):
        fn = f"{base}-{sha[:6]}.pdf"
    shutil.copy(p, d + fn)
    art = 'Offenlegungsbericht' if 'Offenleg' in typ else 'Jahresabschluss/Geschäftsbericht'
    y = '2024' if 'Offenleg' in typ or '2024' in fn else '2025'
    rows.append([bank, art, y, 'dokumente/' + slug(bank) + '/' + fn, 'Originaldokument (PDF)', u, 'Download 27.10.2026', sha,
                 'websites_2026-10-27.json; xlsx:Übersicht', '', ''])
    shas.add(sha); known.add(u); new += 1
w = csv.writer(open(R + 'dokumente/index.csv', 'w', encoding='utf-8-sig', newline=''), delimiter=';')
w.writerow(hdr); w.writerows(rows)
print('neu', new)
