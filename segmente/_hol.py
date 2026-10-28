"""Hilfsskript: lädt ein Dokument höflich (robots.txt, ehrliche Kennung) in den Unternehmensordner und trägt es in dokumente/index.csv ein.
Aufruf: python3 segmente/_hol.py UID BRANCHE SLUG NAME GJ ART URL DATEINAME"""
import csv, hashlib, io, subprocess, sys
from pathlib import Path
import requests
W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "lib"))
from hoeflich import UA, erlaubt
uid, branche, slug, name, gj, art, url, fn = sys.argv[1:9]
if not erlaubt(url):
    sys.exit("robots.txt verbietet " + url)
ziel = W / f"boersennotierte-unternehmen/{branche}/dokumente/{slug}/{fn}"
ziel.parent.mkdir(parents=True, exist_ok=True)
r = requests.get(url, headers={"User-Agent": UA}, timeout=180, stream=True)
if r.status_code != 200 or "pdf" not in r.headers.get("content-type", "").lower():
    sys.exit(f"Abruf fehlgeschlagen: {r.status_code} {r.headers.get('content-type')}")
with open(ziel, "wb") as f:
    for c in r.iter_content(1 << 20):
        f.write(c)
daten = ziel.read_bytes()
seiten = ""
try:
    info = subprocess.run(["pdfinfo", str(ziel)], capture_output=True, text=True).stdout
    seiten = next((z.split()[-1] for z in info.splitlines() if z.startswith("Pages:")), "")
except Exception:
    pass
idx = W / f"boersennotierte-unternehmen/{branche}/dokumente/index.csv"
txt = open(idx, encoding="utf-8-sig", newline="").read()
rows = list(csv.reader(io.StringIO(txt), delimiter=";"))
rel = f"dokumente/{slug}/{fn}"
rows = [x for x in rows if not (len(x) > 4 and x[4] == rel)]
rows.append([name, uid, art, gj, rel, "Originaldokument (PDF)", url, "Download 28.10.2026", hashlib.sha256(daten).hexdigest(), seiten, str(len(daten)), "segmente/segmente_lang.csv", ""])
o = io.StringIO(newline="")
csv.writer(o, delimiter=";", lineterminator="\r\n" if "\r\n" in txt else "\n").writerows(rows)
idx.write_text(o.getvalue(), encoding="utf-8-sig", newline="")
print(ziel, len(daten), seiten, "Seiten")
