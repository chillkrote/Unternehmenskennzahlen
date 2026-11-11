"""Baut das Terminal (Unternehmen und Volkswirtschaft): Excel -> data/banken.json -> dist/bankterminal.html (eine Datei, Daten eingebettet)."""
import argparse
import html
import json
import sys
from pathlib import Path

import datenschicht
import globus
import regional
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


# Öffentliche Fassung (--oeffentlich, docs/datenquellen.md E1; mit --api immer an): Werte aus Yahoo Finance haben kein Weitergaberecht.
# Dieselbe Liste steht in server/plattform/lizenz.py (Import in die Server-Datenbank); server/tests/test_lizenz.py prüft die Gleichheit.
# Kurse und alles, was daraus berechnet ist (Börsenwert, Bewertungskennzahlen), sowie Marktangaben der Branchentabellen aus Yahoo
YAHOO_WERTE = ("kurs", "marktkap", "r_ytd", "r_1j", "kgv", "kbv", "kuv", "ev_ebitda", "div_rendite",
               "x_enterprise_value", "x_ev_umsatz", "x_aussch_ttungsquote", "x_kurs_nderung_52w", "x_52w_hoch", "x_52w_tief",
               "x_beta", "x_volumen_3m", "x_insider", "x_institutionen", "x_kgv_erwartet", "x_kgv")


def ohne_yahoo_firmen(firmen_json):
    """unternehmen.json ohne Kurse und kursabhängige Kennzahlen (YAHOO_WERTE); Abschlusszahlen bleiben."""
    d = json.loads(firmen_json)
    for f in d.get("unternehmen") or []:
        for k in YAHOO_WERTE:
            (f.get("werte") or {}).pop(k, None)
    d["kennzahlen"] = [k for k in d.get("kennzahlen") or [] if k.get("key") not in YAHOO_WERTE]
    d["ohne_kurse"] = 1
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


# Stufe „abschluesse“ (E6, offen; --ohne-yahoo-abschluesse): dieselben Regeln wie server/plattform/lizenz.py (firma_ohne_yahoo_abschluesse)
NICHT_YAHOO_WERTE = ("x_anteil_stimmrechte", "x_anzahl_meldepflichtige")


def ohne_yahoo_abschluesse(firmen_json):
    """unternehmen.json ohne die Konzernabschlüsse aus Yahoo, die daraus abgeleiteten Kennzahlen der Nicht-Banken und Yahoo-Termine."""
    yahoo = lambda t: "yahoo" in str(t or "").lower()
    d = json.loads(firmen_json)
    for f in d.get("unternehmen") or []:
        if f.get("abschluesse"):
            f["abschluesse"] = [a for a in f["abschluesse"] if not yahoo(a.get("quelle"))]
        if f.get("termine"):
            f["termine"] = [t for t in f["termine"] if not yahoo(t.get("quelle"))]
        if not (f.get("bank") or f.get("gruppe")):
            f["werte"] = {k: v for k, v in (f.get("werte") or {}).items() if k in NICHT_YAHOO_WERTE}
    d["ohne_yahoo_abschluesse"] = 1
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def ohne_yahoo_finanz(finanz_json):
    """finanz.json ohne die Marktpuls-Reihen aus Yahoo Finance (VIX, Gold, Brent …); EZB-, Treasury- und FRED-Reihen bleiben."""
    d = json.loads(finanz_json)
    d["puls"] = [x for x in d.get("puls") or [] if "yahoo" not in str(x.get("quelle", "")).lower()]
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


# Ordner, die der Server ausliefert (server/docker-compose.yml: ../app/dist-api); --mit-yahoo darf dorthin nicht schreiben
SERVER_ORDNER = ("dist-api", "dist-oeffentlich")
# Dateien, die nur Yahoo-Daten enthalten (wie server/plattform/lizenz.py: YAHOO_DATEIEN); eine öffentliche Fassung räumt sie aus dem Zielordner
YAHOO_DATEIEN = ("markt.json", "kurse_woche.json", "boerse.json", "live.json")

# API-Fassung: diese Blöcke stehen als data/<datei> neben der Seite statt eingebettet (Platzhalter in terminal.html)
BLOCK_NACHLADEN = ("__PARLAMENTE__", "__KOMMUNAL__", "__REGIONAL__", "__GUETER__", "__GUETER_IMPORTE__", "__GLIEDSTAATEN__")
VWL_PROGNOSEN_DATEI = "data/vwl_prognosen.json"


def vwl_fuer_api(vwl_json):
    """VWL ohne Reihenwerte (4,4 MB): nur Abdeckung je Reihe (Gebiete); die Seite lädt Werte über /observations (vwl.js: bedarf).
    Prognosen und Abgleich (1,4 MB) kommen in eine eigene Datei (VWL_PROGNOSEN_DATEI), die vwl.js mit der Ansicht Prognosen lädt.
    Gibt (JSON der Seite, Inhalt der Prognosedatei oder None) zurück."""
    if vwl_json == "null":
        return vwl_json, None
    d = json.loads(vwl_json)
    d["abdeckung"] = {k: list(v) for k, v in d.pop("daten").items()}
    d["_api"] = 1
    prog = {"prognosen": d.pop("prognosen", None) or [], "abgleich": d.pop("abgleich", None)}
    d["prognosen"], d["prognosen_nach"] = [], VWL_PROGNOSEN_DATEI
    return json.dumps(d, ensure_ascii=False, separators=(",", ":")), json.dumps(prog, ensure_ascii=False, separators=(",", ":"))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--excel", default=datenschicht.STANDARD_EXCEL)
    p.add_argument("--nur-seite", action="store_true",
                   help="data/banken.json und data/unternehmen.json nicht neu erzeugen, sondern den vorhandenen Stand einbetten "
                        "(für Änderungen an der Oberfläche, auch im teilweisen Checkout ohne Dokumentordner)")
    p.add_argument("--api", metavar="URL", default=None,
                   help="API-Modus (Server, server/): das Gesamtregister wird nicht eingebettet, Verzeichnis und Registerprofile laden "
                        "über diese API-Basisadresse, z. B. /api/v1 (gleiche Domain) oder http://127.0.0.1:8000/api/v1")
    p.add_argument("--oeffentlich", action="store_true",
                   help="Fassung für den öffentlichen Server: ohne Daten ohne Weitergaberecht (docs/datenquellen.md, E1): "
                        "Kurse, Indizes und Weltunternehmen (markt, kurse_woche, boerse), Kurs/Börsenwert in den Profilen, Marktpuls aus Yahoo")
    p.add_argument("--mit-yahoo", action="store_true",
                   help="nur für lokale Tests der API-Fassung: Yahoo-Daten trotz --api behalten (E1: auf dem Server nie)")
    p.add_argument("--ohne-yahoo-abschluesse", action="store_true",
                   help="öffentliche Fassung zusätzlich ohne die Konzernabschlüsse aus Yahoo, daraus abgeleitete Kennzahlen und Yahoo-Termine "
                        "(Entscheidung E6 offen, docs/audit-2026-11.md)")
    p.add_argument("--ziel", default="dist", help="Ausgabeordner unter app/ (Standard dist; für den Server dist-api)")
    a = p.parse_args()
    if a.mit_yahoo and a.oeffentlich:
        raise SystemExit("--mit-yahoo und --oeffentlich schließen sich aus")
    if a.mit_yahoo and Path(a.ziel).name in SERVER_ORDNER:
        # der Compose-Stack liefert app/dist-api aus: dort darf nie eine Fassung mit Yahoo-Daten liegen (Audit 2026-11, 4.5)
        raise SystemExit(f"--mit-yahoo schreibt nicht nach {a.ziel} (wird vom Server ausgeliefert); z. B. --ziel dist-lokal")
    if a.api and not a.mit_yahoo:
        a.oeffentlich = True          # E1 (Robin, 10.11.2026): die Server-Fassung (sphaerae.de) liefert keine Yahoo-Daten aus
    if a.ohne_yahoo_abschluesse and not a.oeffentlich:
        raise SystemExit("--ohne-yahoo-abschluesse gilt nur für die öffentliche Fassung (--oeffentlich oder --api)")
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
    regional.schreiben()                  # Kreisdaten (volkswirtschaft/regional) -> data/regional.json für die Weltkugel
    vd = vwl.lade()
    vroh = json.dumps(vd, ensure_ascii=False, separators=(",", ":")) if vd else "null"
    vprog = None
    if a.oeffentlich:
        markt = kurse = boerse = "null"          # Bereiche MKT und BÖR zeigen dann ihren Leerzustand
        firmen = ohne_yahoo_firmen(firmen)
        if a.ohne_yahoo_abschluesse:
            firmen = ohne_yahoo_abschluesse(firmen)
        for alt in YAHOO_DATEIEN:                # Reste eines früheren Builds mit Yahoo-Daten im selben Ordner
            (ziel_ordner / "data" / alt).unlink(missing_ok=True)
    if a.api:
        # Gesamtregister (rund 10 MB) bleibt auf dem Server; die Seite fragt es seitenweise über /companies ab
        reg = "null"
        firmen = firmen_fuer_api(firmen)
        # Börsen- und Kursdaten (rund 4 MB) als Dateien neben der Seite; terminal.html lädt sie beim Start parallel (api.js: BLOCK.warte)
        (ziel_ordner / "data").mkdir(parents=True, exist_ok=True)
        nach = {}
        # dazu Bankdaten (0,6 MB) und Unternehmenskennzahlen (1,4 MB), die start() ebenfalls vor dem ersten Zeichnen abwartet
        for datei, inhalt in (("markt.json", markt), ("kurse_woche.json", kurse), ("boerse.json", boerse), ("banken.json", roh), ("unternehmen.json", firmen)):
            if inhalt != "null":
                (ziel_ordner / "data" / datei).write_text(inhalt, encoding="utf-8")
                nach[datei] = json.dumps({"_nach": "data/" + datei})
            else:
                nach[datei] = inhalt
        markt, kurse, boerse, roh, firmen = nach["markt.json"], nach["kurse_woche.json"], nach["boerse.json"], nach["banken.json"], nach["unternehmen.json"]
        vroh, vprog = vwl_fuer_api(vroh)
    js = (HIER / "src/unternehmen.js").read_text()
    seite = (vorlage.replace("__API_JS__", (HIER / "src/api.js").read_text()).replace("__SUCHE_JS__", (HIER / "src/suche.js").read_text()).replace("__UNTERNEHMEN_JS__", js).replace("__DATEN__", roh.replace("</", "<\\/"))
             .replace("__MARKT__", markt.replace("</", "<\\/")).replace("__UNTERNEHMEN__", firmen.replace("</", "<\\/")).replace("__REGISTER__", reg.replace("</", "<\\/"))
             .replace("__VWL_JS__", (HIER / "src/vwl.js").read_text()).replace("__BOERSE_JS__", (HIER / "src/boerse.js").read_text()).replace("__FINANZ_JS__", (HIER / "src/finanz.js").read_text())
             .replace("__BOERSE__", boerse.replace("</", "<\\/")).replace("__VWL__", vroh.replace("</", "<\\/"))
             .replace("__KURSE__", kurse.replace("</", "<\\/")).replace("__KORRELATION_JS__", (HIER / "src/korrelation.js").read_text())
             .replace("__MELDUNGEN_JS__", (HIER / "src/meldungen.js").read_text())
             .replace("__HANDEL_JS__", (HIER / "src/handel.js").read_text()))
    # Handel und Weltdaten (Bereich HDL und Weltkugel): fehlt eine Datei, bleibt der Teil leer
    for platz, datei in (("__HANDEL__", "handel.json"), ("__WELT__", "welt.json"), ("__ROUTEN__", "routen.json"), ("__GUETER__", "gueter.json"), ("__GUETER_IMPORTE__", "gueter_importe.json"), ("__VERKEHR__", "verkehrsknoten.json"), ("__NEWS__", "news_routen.json"), ("__STROM_ENTSOE__", "strom_entsoe.json"),
                        ("__BOERSE_WELT__", "boerse_welt.json"), ("__FINANZ__", "finanz.json"), ("__FINANZ_MAKRO__", "finanz_makro.json"), ("__POLITIK__", "politik.json"), ("__DE_LAENDER__", "../geo/de_laender.geojson"),
                        ("__PARLAMENTE__", "parlamente.json"), ("__KOMMUNAL__", "kommunal.json"), ("__REGIONAL__", "regional.json"), ("__KOMMUNEN_GEO__", "../geo/kommunen_nrw.geojson"), ("__WAHLKREISE_BUND__", "../geo/wahlkreise_bund.geojson"), ("__GLIEDSTAATEN__", "../geo/gliedstaaten.geojson")):
        f = HIER / "data" / datei
        inhalt = f.read_text() if f.exists() else "null"
        if a.oeffentlich and platz == "__FINANZ__" and inhalt != "null":
            inhalt = ohne_yahoo_finanz(inhalt)
        if a.api and platz in ("__WAHLKREISE_BUND__", "__KOMMUNEN_GEO__"):
            inhalt = "null"          # API-Fassung: als wahlgeo/<art>.json nachgeladen (globus.py: GEO_NACH_API)
        elif a.api and platz in BLOCK_NACHLADEN and f.exists():
            # API-Fassung: Block als Datei neben der Seite, die Seite lädt ihn mit der Ansicht (api.js: BLOCK)
            name = Path(datei).stem + ".json"          # ../geo/gliedstaaten.geojson -> data/gliedstaaten.json
            (ziel_ordner / "data").mkdir(parents=True, exist_ok=True)
            (ziel_ordner / "data" / name).write_text(inhalt, encoding="utf-8")
            inhalt = json.dumps({"_nach": "data/" + name})
        elif platz == "__WAHLKREISE_BUND__" and f.exists():
            # Ergebnisse je Wahlkreis stehen im Wahlregister (data/wahlen.json); hier nur Grenzen, Nummer und Name
            inhalt = json.dumps(globus.wahlkreise_bund_schlank(json.loads(inhalt)), ensure_ascii=False, separators=(",", ":"))
        seite = seite.replace(platz, inhalt.replace("</", "<\\/"), 1)
    # API-Basisadresse für src/api.js (nur im API-Modus; ohne sie arbeitet die Seite wie bisher mit eingebetteten Daten)
    kopf_api = f'<meta name="sphaerae-api" content="{html.escape(a.api, quote=True)}">' if a.api else ""
    if a.oeffentlich:
        kopf_api += '<meta name="sphaerae-oeffentlich" content="1">'      # Leerzustände nennen dann die Lizenz statt eines Abrufbefehls
    # Artifact-Fassung ohne Dokumentgerüst (wird beim Veröffentlichen ergänzt)
    (ziel_ordner / "bankterminal.fragment.html").write_text(seite)
    # lokale Fassung: im Browser öffnen
    ziel.write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' + kopf_api +
                    '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                    + seite + "\n</body></html>\n")
    print(f"{len(banken)} Banken -> {ziel}")
    # Weltkugel: dieselbe Seite mit Karte, Ländern und Firmensitzen (alternative Oberfläche)
    welt, n_sitze = globus.seite(seite, api=bool(a.api))
    (ziel_ordner / "weltkugel.fragment.html").write_text(welt)
    globus.wahlgeo_schreiben(ziel_ordner, api=bool(a.api))             # Wahlkreisgrenzen zum Nachladen (dist/wahlgeo/*.json), beim Artifact als Zusatzdateien
    if a.api:
        if vprog:                                                      # VWL-Prognosen und Abgleich (dist-api/data/vwl_prognosen.json)
            (ziel_ordner / VWL_PROGNOSEN_DATEI).parent.mkdir(parents=True, exist_ok=True)
            (ziel_ordner / VWL_PROGNOSEN_DATEI).write_text(vprog, encoding="utf-8")
        globus.tabelle_schreiben(ziel_ordner)                          # Unternehmenspunkte der Weltkugel (dist-api/geodaten/unternehmen.json)
    (ziel_ordner / "weltkugel.html").write_text('<!doctype html>\n<html lang="de"><head><meta charset="utf-8">'
                                              '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">' + kopf_api +
                                              '<style>body{margin:0}[hidden]{display:none!important}</style></head><body>\n'
                                              + welt + "\n</body></html>\n")
    print(f"Weltkugel: {n_sitze} Firmensitze -> {ziel_ordner / 'weltkugel.html'}")
    if a.api:
        # Startseite des Servers: Weltkugel wie auf GitHub Pages (Deep Links #globus, #firma-… bleiben gültig)
        (ziel_ordner / "index.html").write_text((ziel_ordner / "weltkugel.html").read_text())
    # Manifest der Lizenzstufe: server/plattform/lizenz.py (pruefe_ausgabe) verlangt es vor der Auslieferung
    import datetime
    (ziel_ordner / "LIZENZ.json").write_text(json.dumps({
        "oeffentlich": bool(a.oeffentlich), "yahoo_kurse": not a.oeffentlich, "yahoo_abschluesse": not a.ohne_yahoo_abschluesse,
        "api": a.api, "erzeugt": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}, indent=1), encoding="utf-8")
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
