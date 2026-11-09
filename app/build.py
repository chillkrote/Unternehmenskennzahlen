"""Baut das Terminal (Unternehmen und Volkswirtschaft): Excel -> data/banken.json -> dist/bankterminal.html (eine Datei, Daten eingebettet)."""
import argparse
import html
import json
import sys
from pathlib import Path

import datenschicht
import globus
import register
import seiten
import unternehmen
import vwl

HIER = Path(__file__).resolve().parent


# In der API-Fassung nicht eingebettet: kommen je Profil aus /companies/{id}/profile (server/etl/profile.py)
AUSGELAGERT = ("abschluesse", "gov", "dokumente")


def firmen_fuer_api(firmen_json):
    """unternehmen.json ohne Abschlussposten, Gremien und Dokumente (rund 22 MB weniger). Übrig bleiben Kennzahlen, Zeitreihen und
    Termine (Branchenansichten, Korrelation, Terminübersicht) sowie Kurzfassungen für die Abdeckungstabelle und die Dokumentzahl."""
    d = json.loads(firmen_json)
    for f in d.get("unternehmen") or []:
        ab = f.get("abschluesse") or []
        if ab:
            f["abs_kurz"] = [[a["jahr"], a.get("waehrung") or "", len(a.get("bilanz") or {}), len(a.get("guv") or {})] for a in ab]
        if f.get("dokumente"):
            f["dok_n"] = len(f["dokumente"])
        for k in AUSGELAGERT:
            f.pop(k, None)
        f["_api"] = 1
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=datenschicht.STANDARD_EXCEL)
    p.add_argument("--nur-seite", action="store_true",
                   help="data/banken.json und data/unternehmen.json nicht neu erzeugen, sondern den vorhandenen Stand einbetten "
                        "(für Änderungen an der Oberfläche, auch im teilweisen Checkout ohne Dokumentordner)")
    p.add_argument("--api", metavar="URL", default=None,
                   help="API-Modus (Server, server/): das Gesamtregister wird nicht eingebettet, Verzeichnis und Registerprofile laden "
                        "über diese API-Basisadresse, z. B. /api/v1 (gleiche Domain) oder http://127.0.0.1:8000/api/v1")
    p.add_argument("--ziel", default="dist", help="Ausgabeordner unter app/ (Standard dist; für den Server dist-api)")
    a = p.parse_args()
    ziel_ordner = HIER / a.ziel
    if a.nur_seite:
        roh = (HIER / "data/banken.json").read_text()
        banken = json.loads(roh)["banken"]
    else:
        banken = datenschicht.lade(a.excel)
        daten = {"meta": {"quelle": Path(a.excel).name, "stichtag": "2025-12-31", "anzahl": len(banken)}, "banken": banken,
                 "gruppen_zr": datenschicht.lade_gruppen()}
        roh = json.dumps(daten, ensure_ascii=False, separators=(",", ":"))
        (HIER / "data").mkdir(exist_ok=True)
        (HIER / "data/banken.json").write_text(roh)
    vorlage = (HIER / "src/terminal.html").read_text()
    # Fußleiste (Impressum, Kontakt, About): Texte aus app/seiten/*.md, Oberfläche aus src/seiten.js/.css
    vorlage = (vorlage.replace("__SEITEN_JS__", (HIER / "src/seiten.js").read_text()).replace("__SEITEN_CSS__", (HIER / "src/seiten.css").read_text())
               .replace("__SEITEN__", seiten.json_text().replace("</", "<\\/")))
    ziel_ordner.mkdir(exist_ok=True)
    ziel = ziel_ordner / "bankterminal.html"
    # Börsendaten liegen getrennt (marktdaten.py, täglich); fehlen sie, zeigt das Terminal MKT leer
    markt_datei = HIER / "data/markt.json"
    markt = markt_datei.read_text() if markt_datei.exists() else "null"
    # Unternehmen anderer Branchen: generisch aus den Branchen-Tabellen im Repo (sonst Beispieldaten)
    if a.nur_seite:
        firmen = (HIER / "data/unternehmen.json").read_text()
    else:
        firmen = json.dumps(unternehmen.lade(banken=banken, markt=json.loads(markt) if markt != "null" else None), ensure_ascii=False, separators=(",", ":"))
        (HIER / "data/unternehmen.json").write_text(firmen)
    # Wochenkurse aller börsennotierten Unternehmen (kurse_historie.py), getrennt von markt.json, damit das Terminal klein bleibt
    kd = HIER / "data/kurse_woche.json"
    kurse = kd.read_text() if kd.exists() else "null"
    # Indizes und Weltunternehmen (boersen_abruf.py, Workflow Börsendaten Terminal); fehlt die Datei, bleibt der Bereich leer
    bdat = HIER / "data/boerse.json"
    boerse = bdat.read_text() if bdat.exists() else "null"
    # Gesamtregister: alle Zeilen der Unternehmenstabelle (nur Stammdaten), getrennt von den Kennzahlen
    if a.nur_seite and (HIER / "data/register.json").exists():
        reg = (HIER / "data/register.json").read_text()
    else:
        rd, unbekannt = register.lade()
        reg = json.dumps(rd, ensure_ascii=False, separators=(",", ":"))
        (HIER / "data/register.json").write_text(reg)
        if unbekannt:
            print("Länder ohne ISO-Code im Register:", unbekannt)
    vd = vwl.lade()
    vroh = json.dumps(vd, ensure_ascii=False, separators=(",", ":")) if vd else "null"
    if a.api:
        # Gesamtregister (rund 10 MB) bleibt auf dem Server; die Seite fragt es seitenweise über /companies ab
        reg = "null"
        firmen = firmen_fuer_api(firmen)
    js = (HIER / "src/unternehmen.js").read_text()
    seite = (vorlage.replace("__API_JS__", (HIER / "src/api.js").read_text()).replace("__UNTERNEHMEN_JS__", js).replace("__DATEN__", roh.replace("</", "<\\/"))
             .replace("__MARKT__", markt.replace("</", "<\\/")).replace("__UNTERNEHMEN__", firmen.replace("</", "<\\/")).replace("__REGISTER__", reg.replace("</", "<\\/"))
             .replace("__VWL_JS__", (HIER / "src/vwl.js").read_text()).replace("__BOERSE_JS__", (HIER / "src/boerse.js").read_text()).replace("__FINANZ_JS__", (HIER / "src/finanz.js").read_text())
             .replace("__BOERSE__", boerse.replace("</", "<\\/")).replace("__VWL__", vroh.replace("</", "<\\/"))
             .replace("__KURSE__", kurse.replace("</", "<\\/")).replace("__KORRELATION_JS__", (HIER / "src/korrelation.js").read_text())
             .replace("__MELDUNGEN_JS__", (HIER / "src/meldungen.js").read_text())
             .replace("__HANDEL_JS__", (HIER / "src/handel.js").read_text()))
    # Handel und Weltdaten (Bereich HDL und Weltkugel): fehlt eine Datei, bleibt der Teil leer
    for platz, datei in (("__HANDEL__", "handel.json"), ("__WELT__", "welt.json"), ("__ROUTEN__", "routen.json"), ("__GUETER__", "gueter.json"), ("__VERKEHR__", "verkehrsknoten.json"), ("__NEWS__", "news_routen.json"),
                        ("__BOERSE_WELT__", "boerse_welt.json"), ("__FINANZ__", "finanz.json"), ("__FINANZ_MAKRO__", "finanz_makro.json"), ("__POLITIK__", "politik.json"), ("__DE_LAENDER__", "../geo/de_laender.geojson"),
                        ("__PARLAMENTE__", "parlamente.json"), ("__KOMMUNAL__", "kommunal.json"), ("__KOMMUNEN_GEO__", "../geo/kommunen_nrw.geojson"), ("__WAHLKREISE_BUND__", "../geo/wahlkreise_bund.geojson"), ("__GLIEDSTAATEN__", "../geo/gliedstaaten.geojson")):
        f = HIER / "data" / datei
        inhalt = f.read_text() if f.exists() else "null"
        if platz == "__WAHLKREISE_BUND__" and f.exists():
            # Ergebnisse je Wahlkreis stehen im Wahlregister (data/wahlen.json); hier nur Grenzen, Nummer und Name
            wk = json.loads(inhalt)
            for ft in wk["features"]:
                ft["properties"] = {k: ft["properties"][k] for k in ("nr", "name", "land")}
            inhalt = json.dumps(wk, ensure_ascii=False, separators=(",", ":"))
        seite = seite.replace(platz, inhalt.replace("</", "<\\/"), 1)
    # API-Basisadresse für src/api.js (nur im API-Modus; ohne sie arbeitet die Seite wie bisher mit eingebetteten Daten)
    kopf_api = f'<meta name="sphaerae-api" content="{html.escape(a.api, quote=True)}">' if a.api else ""
    # Artifact-Fassung ohne Dokumentgerüst (wird beim Veröffentlichen ergänzt)
    (ziel_ordner / "bankterminal.fragment.html").write_text(seite)
    # lokale Fassung: im Browser öffnen
    ziel.write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' + kopf_api +
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                    + seite + "\n</body></html>\n")
    print(f"{len(banken)} Banken -> {ziel}")
    # Weltkugel: dieselbe Seite mit Karte, Ländern und Firmensitzen (alternative Oberfläche)
    welt, n_sitze = globus.seite(seite)
    (ziel_ordner / "weltkugel.fragment.html").write_text(welt)
    globus.wahlgeo_schreiben(ziel_ordner)             # Wahlkreisgrenzen zum Nachladen (dist/wahlgeo/*.json), beim Artifact als Zusatzdateien
    (ziel_ordner / "weltkugel.html").write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                                              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' + kopf_api +
                                              '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                                              + welt + "\n</body></html>\n")
    print(f"Weltkugel: {n_sitze} Firmensitze -> {ziel_ordner / 'weltkugel.html'}")
    if a.api:
        # Startseite des Servers: Weltkugel wie auf GitHub Pages (Deep Links #globus, #firma-… bleiben gültig)
        (ziel_ordner / "index.html").write_text((ziel_ordner / "weltkugel.html").read_text())
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
