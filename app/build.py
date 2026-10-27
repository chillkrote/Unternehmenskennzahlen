"""Baut das Terminal (Unternehmen und Volkswirtschaft): Excel -> data/banken.json -> dist/bankterminal.html (eine Datei, Daten eingebettet)."""
import argparse
import json
import sys
from pathlib import Path

import datenschicht
import unternehmen
import vwl

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
    # Wochenkurse aller börsennotierten Unternehmen (kurse_historie.py), getrennt von markt.json, damit das Terminal klein bleibt
    kd = HIER / "data/kurse_woche.json"
    kurse = kd.read_text() if kd.exists() else "null"
    vd = vwl.lade()
    vroh = json.dumps(vd, ensure_ascii=False, separators=(",", ":")) if vd else "null"
    js = (HIER / "src/unternehmen.js").read_text()
    seite = (vorlage.replace("__UNTERNEHMEN_JS__", js).replace("__DATEN__", roh.replace("</", "<\\/"))
             .replace("__MARKT__", markt.replace("</", "<\\/")).replace("__UNTERNEHMEN__", firmen.replace("</", "<\\/"))
             .replace("__VWL_JS__", (HIER / "src/vwl.js").read_text()).replace("__VWL__", vroh.replace("</", "<\\/"))
             .replace("__KURSE__", kurse.replace("</", "<\\/")).replace("__KORRELATION_JS__", (HIER / "src/korrelation.js").read_text()))
    # Artifact-Fassung ohne Dokumentgerüst (wird beim Veröffentlichen ergänzt)
    (HIER / "dist/bankterminal.fragment.html").write_text(seite)
    # lokale Fassung: im Browser öffnen
    ziel.write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">'
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                    + seite + "\n</body></html>\n")
    print(f"{len(banken)} Banken -> {ziel}")
    # Kontrolle der zentralen Unternehmens-IDs (u. a.: jede ISIN nur bei einer ID); ein Verstoß lässt den Bau fehlschlagen,
    # damit die Workflows (marktdaten, termine) nichts Fehlerhaftes committen
    sys.path.insert(0, str(HIER.parent / "stammdaten"))
    import pruefe_ids
    fehler, info = pruefe_ids.pruefen()
    print(f"Stammdaten: {info['unternehmen']} Unternehmen, {info['isins']} ISINs, {info['verweise']} ID-Verweise geprüft, {len(fehler)} Fehler")
    if fehler:
        raise SystemExit("Stammdaten-Prüfung fehlgeschlagen:\n  " + "\n  ".join(fehler[:30]))


if __name__ == "__main__":
    main()
