"""Baut das Bank-Terminal: Excel -> data/banken.json -> dist/bankterminal.html (eine Datei, Daten eingebettet)."""
import argparse
import json
from pathlib import Path

import datenschicht
import unternehmen

HIER = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=datenschicht.STANDARD_EXCEL)
    a = p.parse_args()
    banken = datenschicht.lade(a.excel)
    daten = {"meta": {"quelle": Path(a.excel).name, "stichtag": "2025-12-31", "anzahl": len(banken)}, "banken": banken,
             "gruppen_zr": datenschicht.lade_gruppen()}
    roh = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    (HIER / "data").mkdir(exist_ok=True)
    (HIER / "data/banken.json").write_text(roh)
    vorlage = (HIER / "src/terminal.html").read_text()
    (HIER / "dist").mkdir(exist_ok=True)
    ziel = HIER / "dist/bankterminal.html"
    # Börsendaten liegen getrennt (marktdaten.py, täglich); fehlen sie, zeigt das Terminal MKT leer
    markt_datei = HIER / "data/markt.json"
    markt = markt_datei.read_text() if markt_datei.exists() else "null"
    # Unternehmen anderer Branchen: generisch aus den Branchen-Tabellen im Repo (sonst Beispieldaten)
    firmen = json.dumps(unternehmen.lade(banken=banken, markt=json.loads(markt) if markt != "null" else None), ensure_ascii=False, separators=(",", ":"))
    (HIER / "data/unternehmen.json").write_text(firmen)
    js = (HIER / "src/unternehmen.js").read_text()
    seite = (vorlage.replace("__UNTERNEHMEN_JS__", js).replace("__DATEN__", roh.replace("</", "<\\/"))
             .replace("__MARKT__", markt.replace("</", "<\\/")).replace("__UNTERNEHMEN__", firmen.replace("</", "<\\/")))
    # Artifact-Fassung ohne Dokumentgerüst (wird beim Veröffentlichen ergänzt)
    (HIER / "dist/bankterminal.fragment.html").write_text(seite)
    # lokale Fassung: im Browser öffnen
    ziel.write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                    + seite + "\n</body></html>\n")
    print(f"{len(banken)} Banken -> {ziel}")


if __name__ == "__main__":
    main()
