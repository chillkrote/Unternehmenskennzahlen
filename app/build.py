"""Baut das Bank-Terminal: Excel -> data/banken.json -> dist/bankterminal.html (eine Datei, Daten eingebettet)."""
import argparse
import json
from pathlib import Path

import datenschicht

HIER = Path(__file__).resolve().parent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=datenschicht.STANDARD_EXCEL)
    a = p.parse_args()
    banken = datenschicht.lade(a.excel)
    daten = {"meta": {"quelle": Path(a.excel).name, "stichtag": "2025-12-31", "anzahl": len(banken)}, "banken": banken}
    roh = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
    (HIER / "data").mkdir(exist_ok=True)
    (HIER / "data/banken.json").write_text(roh)
    vorlage = (HIER / "src/terminal.html").read_text()
    (HIER / "dist").mkdir(exist_ok=True)
    ziel = HIER / "dist/bankterminal.html"
    seite = vorlage.replace("__DATEN__", roh.replace("</", "<\\/"))
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
