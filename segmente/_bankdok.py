"""Hilfsskript: trägt eine PDF der Bank-Ablage (banken/bilanzvergleich-gj2025/dokumente) in deren index.csv ein.
Aufruf: python3 segmente/_bankdok.py BANKNAME ART JAHR DATEI URL"""
import csv, hashlib, io, sys
from pathlib import Path
W = Path(__file__).resolve().parent.parent
name, art, jahr, datei, url = sys.argv[1:6]
idx = W / "banken/bilanzvergleich-gj2025/dokumente/index.csv"
txt = open(idx, encoding="utf-8-sig", newline="").read()
rows = list(csv.reader(io.StringIO(txt), delimiter=";"))
rows = [r for r in rows if not (len(r) > 3 and r[3] == datei)]
rows.append([name, art, jahr, datei, "Originaldokument (PDF)", url, "Download 28.10.2026", hashlib.sha256((idx.parent.parent / datei).read_bytes()).hexdigest(), "segmente/segmente_lang.csv", "", ""])
o = io.StringIO(newline="")
csv.writer(o, delimiter=";", lineterminator="\r\n" if "\r\n" in txt else "\n").writerows(rows)
open(idx, "w", encoding="utf-8-sig", newline="").write(o.getvalue())
