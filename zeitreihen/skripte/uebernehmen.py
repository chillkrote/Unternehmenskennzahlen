"""Übernimmt neue Jahreswerte aus einer Extrakt-CSV ins Langformat (bestehende Werte werden nie überschrieben).

Aufruf: python3 -I uebernehmen.py zeitreihen/rohdaten/mehrjahres_extrakt.csv "Mehrjahresübersicht" [--pruefstatus plausibilisiert]
Gibt die Zahl neuer Zeilen aus (0 = nichts mehr zu holen).
"""
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LANG = REPO / "zeitreihen/zeitreihe_lang.csv"
EINHEIT = "Mio. EUR"


def main():
    extrakt, art = Path(sys.argv[1]), sys.argv[2]
    status = sys.argv[sys.argv.index("--pruefstatus") + 1] if "--pruefstatus" in sys.argv else "plausibilisiert"
    with open(LANG, encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f)
        felder, zeilen = rd.fieldnames, list(rd)
    da = {(r["unternehmen_id"], r["kennzahl"], r["stichtag"][:4]) for r in zeilen if r["rechnungslegung"] == "HGB"}
    neu = 0
    with open(extrakt, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            k = (r["unternehmen_id"], r["kennzahl"], r["jahr"])
            if k in da:
                continue
            da.add(k)
            neu += 1
            zeilen.append({"unternehmen_id": r["unternehmen_id"], "kennzahl": r["kennzahl"], "stichtag": f"{r['jahr']}-12-31",
                           "wert": round(float(r["wert_mio_eur"]), 3), "einheit": EINHEIT, "waehrung": "EUR",
                           "rechnungslegung": "HGB", "ebene": "Einzel",
                           "quelle": f"{art}: {r['dokument']} S. {r['seite']}", "pruefstatus": status})
    zeilen.sort(key=lambda r: (r["unternehmen_id"], r["kennzahl"], r["stichtag"]))
    with open(LANG, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, felder)
        w.writeheader()
        w.writerows(zeilen)
    print(neu)


if __name__ == "__main__":
    main()
