"""Südkorea-Pilot über DART: zehn Unternehmen (zwei Finanzholdings getrennt) registrieren, laden und importieren.

  register   Unternehmen über stammdaten/ids.py anlegen; corp_code, Börsenkürzel und Geschäftsjahresende gegen DART (company.json) prüfen,
             LEI per GLEIF-Volltextsuche nach dem koreanischen Namen suchen (nur bei eindeutigem Treffer, sonst bleibt sie leer)
  import     Konzernabschlüsse GJ 2015 bis zum jüngsten Jahr je Unternehmen laden (Live, rate-limitiert) und importieren
Aufruf: DART_API=… INTERNATIONAL_DATABASE_URL=… python3 international/kr_pilot.py register|import [--dry-run] [--von=2015] [--bis=2025]
Der Schlüssel wird nie ausgegeben oder gespeichert. Beträge bleiben in KRW.
"""
import csv
import re
import sys
from datetime import date
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "stammdaten"))

PILOT = HIER / "kr_pilot.csv"
LAND = "South Korea"


def lies():
    with open(PILOT, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def norm_name(s):
    return re.sub(r"\s|\(주\)|주식회사|[().,]", "", s or "")


def lei_suchen(gleif, korean_name):
    """LEI nur bei genau einem aktiven, gültigen koreanischen Treffer mit gleichem Namen (ohne Rechtsformzusatz); sonst None."""
    import json
    from urllib.parse import urlencode
    import esef
    q = urlencode({"filter[fulltext]": korean_name, "filter[entity.legalAddress.country]": "KR", "page[size]": 20})
    treffer = []
    for r in json.loads(gleif.holen(f"https://api.gleif.org/api/v1/lei-records?{q}"))["data"]:
        a = r["attributes"]
        if norm_name(a["entity"]["legalName"]["name"]) == norm_name(korean_name) and a["entity"]["status"] == "ACTIVE" and a["registration"]["status"] == "ISSUED":
            treffer.append(esef.lei_pruefen(a["lei"]))
    return treffer[0] if len(treffer) == 1 else None


def registrieren(dart, gleif):
    import dart as d
    import ids
    import db
    liste = d.firmenliste(dart, cache=db.HIER / "objektspeicher" / "dart" / "CORPCODE.zip")
    reg = ids.lade(neu=True)
    ergebnis = {}
    for z in lies():
        corp = liste.get(z["stock_code"])
        if not corp or corp[0] != z["corp_code"]:
            raise SystemExit(f"{z['name']}: corp_code {z['corp_code']} passt nicht zu Börsenkürzel {z['stock_code']} (DART: {corp})")
        f = d.firma(dart, z["corp_code"])
        if f.get("stock_code") != z["stock_code"] or f.get("acc_mt") != "12":
            raise SystemExit(f"{z['name']}: DART nennt Kürzel {f.get('stock_code')}, Geschäftsjahresende Monat {f.get('acc_mt')} (erwartet {z['stock_code']}, 12)")
        lei = lei_suchen(gleif, corp[1]) or ""
        uid = reg.registrieren(name=z["name"], branche=z["branche"], isin=z["isin"], land=LAND, ticker=z["ticker"], lei=lei, status="börsennotiert",
                               herkunft="DART-Pilot", hinweis=f"DART corp_code {z['corp_code']}, {corp[1]}")
        reg.aktualisieren(uid, isin_haupt=z["isin"], lei=lei, land=LAND)
        ergebnis[z["isin"]] = (uid, lei)
    reg.speichern()
    return ergebnis


def importieren(dry_run=False, von=2015, bis=None):
    import dart as d
    import db
    import import_de
    import esef
    dart = d.DartClient()
    ids_ = registrieren(dart, d.neutraler_client(esef.HOSTS))
    bis = bis or date.today().year - 1
    with db.verbinden() as conn:
        db.migrieren(conn)
        db.laender_laden(conn)
        import_de.importieren(conn, dry_run=dry_run)
        for z in lies():
            uid = ids_[z["isin"]][0]
            if dry_run:
                conn.execute("INSERT INTO international.entity (id, legal_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, z["name"]))
            gesamt, jahre, fehlt = 0, 0, []
            for jahr in range(von, bis + 1):
                r = d.abschluss_abrufen(dart, z["corp_code"], jahr, db.HIER / "objektspeicher" / "dart")
                if r is None:
                    fehlt.append(jahr)
                    continue
                pfad, h, n, url, _ = r
                try:
                    neu, alt = d.importieren(conn, pfad, h, url, uid, z["corp_code"], z["stock_code"], bank=z["bank"] == "ja", dry_run=dry_run)
                except ValueError as ex:
                    print(f"  übersprungen (Widerspruch) {jahr}: {ex}")
                    continue
                gesamt += neu
                jahre += 1
            print(f"{uid} {z['name']}: {jahre} Berichte, neu {gesamt}" + (f", keine Daten: {fehlt}" if fehlt else ""))


if __name__ == "__main__":
    opt = {a.split("=")[0]: a.split("=")[1] for a in sys.argv if a.startswith("--") and "=" in a}
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus == "register":
        import dart as d
        import esef
        for isin, (uid, lei) in registrieren(d.DartClient(), d.neutraler_client(esef.HOSTS)).items():
            print(uid, isin, lei or "(LEI offen)")
    elif modus == "import":
        importieren("--dry-run" in sys.argv, int(opt.get("--von", 2015)), int(opt["--bis"]) if "--bis" in opt else None)
    else:
        sys.exit(__doc__)
