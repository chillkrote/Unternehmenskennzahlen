"""Löscht inhaltsgleiche PDFs im selben Ordner und stellt alle Verweise auf die behaltene Datei um.

Quelle: pruefung/dubletten_pdf.csv (Gruppen mit art "gleicher Ordner"). Behalten wird die Datei, auf die
im Repo am häufigsten verwiesen wird (bei Gleichstand die alphabetisch erste). Dubletten über verschiedene
Ordner bleiben stehen, damit jeder Unternehmensordner vollständig ist.
Aufruf: python3 pruefung/dubletten_loeschen.py [--ausfuehren]   (ohne Schalter nur Vorschau)"""
import csv
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

W = Path(__file__).resolve().parent.parent
ausf = "--ausfuehren" in sys.argv
gr = defaultdict(list)
for r in csv.DictReader(open(W / "pruefung/dubletten_pdf.csv", encoding="utf-8-sig"), delimiter=";"):
    if r["art"] == "gleicher Ordner":
        gr[r["gruppe"]].append(r["datei"])
texte = [p for p in subprocess.run(["git", "-C", str(W), "grep", "--cached", "-I", "-l", "-F", "dokumente/", "--", ".", ":!pruefung/dubletten_pdf.csv"],
                                   capture_output=True, text=True, check=True).stdout.split() if (W / p).exists()]
inhalt = {}
for p in texte:
    try:
        inhalt[p] = (W / p).read_bytes().decode("utf-8")
    except UnicodeDecodeError:
        print("übersprungen (kein UTF-8):", p)
def schluessel(pfad):
    teile = pfad.split("/")
    return "/".join(teile[-2:])
umschreib, loeschen = {}, []
for k, dateien in gr.items():
    zaehl = {d: sum(t.count(schluessel(d)) for t in inhalt.values()) for d in dateien}
    behalte = max(dateien, key=lambda d: (zaehl[d], -dateien.index(d)))
    for d in dateien:
        if d != behalte:
            umschreib[schluessel(d)] = schluessel(behalte)
            loeschen.append(d)
print(len(gr), "Gruppen,", len(loeschen), "Dateien zu löschen")
n = 0
for p, t in inhalt.items():
    neu = t
    for alt, nw in umschreib.items():
        neu = neu.replace(alt, nw)
    if neu != t:
        n += 1
        if ausf:
            (W / p).write_bytes(neu.encode("utf-8"))
print(n, "Textdateien mit umgestellten Verweisen")
if ausf:
    subprocess.run(["git", "-C", str(W), "rm", "-q", "--sparse", "--cached", "--"] + loeschen, check=True)
    for d in loeschen:
        (W / d).unlink(missing_ok=True)
