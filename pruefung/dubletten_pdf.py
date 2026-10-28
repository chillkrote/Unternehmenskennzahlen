"""Findet inhaltsgleiche Dateien im Repo über die Git-Blob-Hashes (kein Checkout der Dateien nötig).

Schreibt pruefung/dubletten_pdf.csv (eine Zeile je Datei einer Dublettengruppe) und nennt die überflüssigen Megabyte.
Es wird nichts gelöscht: Verweise (index.csv, Governance-Quellen, Excel-Fundstellen) müssten vorher umgestellt werden.
Aufruf: python3 pruefung/dubletten_pdf.py"""
import csv
import subprocess
from collections import defaultdict
from pathlib import Path

WURZEL = Path(__file__).resolve().parent.parent
aus = subprocess.run(["git", "-C", str(WURZEL), "ls-tree", "-r", "-l", "HEAD"], capture_output=True, text=True, check=True).stdout
gruppen = defaultdict(list)
for z in aus.splitlines():
    meta, pfad = z.split("\t", 1)
    _, _, blob, groesse = meta.split()
    if pfad.lower().endswith(".pdf") and groesse.isdigit():
        gruppen[blob].append((pfad, int(groesse)))
dub = {b: sorted(v) for b, v in gruppen.items() if len(v) > 1}
with open(WURZEL / "pruefung/dubletten_pdf.csv", "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["gruppe", "blob_sha", "bytes", "datei", "art"])
    for i, (b, v) in enumerate(sorted(dub.items(), key=lambda x: x[1][0][0]), 1):
        ordner = {p.rsplit("/", 1)[0] for p, _ in v}
        art = "gleicher Ordner" if len(ordner) == 1 else "verschiedene Ordner"
        for p, g in v:
            w.writerow([i, b[:12], g, p, art])
mb = sum((len(v) - 1) * v[0][1] for v in dub.values()) / 1e6
print(f"{len(dub)} Dublettengruppen, {sum(len(v) for v in dub.values())} Dateien, {mb:.0f} MB überflüssig im Checkout -> pruefung/dubletten_pdf.csv")
