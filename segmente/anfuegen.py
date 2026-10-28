"""Hilfsskript: hängt geprüfte Segmentwerte an segmente_lang.csv an (ersetzt vorhandene Zeilen derselben Unternehmen/GJ/Dokumente).
Aufruf: python3 segmente/anfuegen.py eingabe.json   (Liste von Zeilen-Objekten)"""
import csv
import json
import sys
from pathlib import Path

DATEI = Path(__file__).resolve().parent / "segmente_lang.csv"
KOPF = ["unternehmen_id", "gj", "segment", "kennzahl", "wert_mio", "waehrung", "quelle_dokument", "pdf_seite", "pruefstatus", "bemerkung"]
alt = list(csv.DictReader(open(DATEI, encoding="utf-8-sig"), delimiter=";")) if DATEI.exists() else []
neu = json.load(open(sys.argv[1], encoding="utf-8"))
schluessel = {(r["unternehmen_id"], r["quelle_dokument"]) for r in neu}
alt = [r for r in alt if (r["unternehmen_id"], r["quelle_dokument"]) not in schluessel]
with open(DATEI, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.DictWriter(f, KOPF, delimiter=";", lineterminator="\n")
    w.writeheader()
    for r in sorted(alt + neu, key=lambda r: (r["unternehmen_id"], str(r["gj"]), r["kennzahl"], r["segment"])):
        w.writerow({k: r.get(k, "") for k in KOPF})
print(len(alt) + len(neu), "Zeilen")
