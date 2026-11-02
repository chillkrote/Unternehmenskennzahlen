"""Importiert die vorhandenen deutschen Daten (stammdaten/ und zeitreihen/zeitreihe_lang.csv) in das Schema international.

* Unternehmens-IDs kommen unverändert aus stammdaten/unternehmen_ids.csv; dieses Skript schreibt nie in stammdaten/.
* Werte werden von Mio. EUR in EUR umgerechnet; Originalwert und Skalierung stehen in fact.provenance.
* Nicht abbildbare Zeilen werden gezählt und mit Grund ausgegeben, nie geraten (z. B. Zeitraumwerte ohne 31.12.-Stichtag).
* --dry-run führt alles aus und rollt zurück. Wiederholte Läufe fügen nichts doppelt ein.
Aufruf: INTERNATIONAL_DATABASE_URL=... python3 international/import_de.py [--dry-run]
"""
import argparse
import csv
import hashlib
import re
import sys
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
sys.path.insert(0, str(HIER))
import db  # noqa: E402
import ingest  # noqa: E402
from international_core import scale_value  # noqa: E402

STAMM = REPO / "stammdaten" / "unternehmen_ids.csv"
ZEITREIHE = REPO / "zeitreihen" / "zeitreihe_lang.csv"
MAPPING_VERSION = "de-zeitreihe-v1"
BLOB = "https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/"

KENNZAHL = {   # Spalte kennzahl in zeitreihe_lang.csv -> metric.code
    "bilanzsumme": "assets", "eigenkapital": "equity", "jahresueberschuss": "net_income", "fonds_340g": "de_fonds_340g",
    "cet1": "cet1_capital", "t1": "t1_capital", "eigenmittel": "own_funds", "rwa": "rwa",
    "cet1_quote": "cet1_ratio", "t1_quote": "t1_ratio", "gk_quote": "total_capital_ratio", "gk_anforderung": "total_capital_requirement",
    "leverage_ratio": "leverage_ratio", "leverage_exposure": "leverage_exposure", "lcr": "lcr", "nsfr": "nsfr", "hqla": "hqla",
}
DAUER = {"net_income"}   # Zeitraumwerte; der Beginn wird nur bei Stichtag 31.12. als 1. Januar abgeleitet
LAND_ISO2 = {"Germany": "DE", "France": "FR", "Luxembourg": "LU", "Switzerland": "CH", "Austria": "AT", "Netherlands": "NL", "Italy": "IT", "Spain": "ES", "Belgium": "BE", "Finland": "FI", "Ireland": "IE", "Portugal": "PT", "Denmark": "DK", "Norway": "NO",
             "Bulgaria": "BG", "United States": "US", "Cyprus": "CY", "China": "CN", "Poland": "PL", "Malta": "MT",
             "Sweden": "SE", "United Kingdom": "GB", "Australia": "AU"}
NICHT_OECD = {"BG": "Bulgaria", "CY": "Cyprus", "CN": "China", "MT": "Malta"}   # Sitzländer außerhalb der OECD, damit domicile gesetzt werden kann
GRUPPEN_EBENEN = ("konzern", "gruppe", "institutsgruppe")


def lies_csv(pfad):
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def konsolidierung(rechnungslegung, ebene):
    if rechnungslegung == "aufsichtlich":
        return "regulatory"
    e = ebene.lower()
    if e in ("einzel", "einzelinstitut"):
        return "solo"
    if any(g in e for g in GRUPPEN_EBENEN):
        return "group"
    return "unknown"


def standard(rechnungslegung):
    return "CRR" if rechnungslegung == "aufsichtlich" else rechnungslegung


def entitaeten_importieren(conn, stamm, bericht):
    with conn.transaction():
        for iso2, name in NICHT_OECD.items():
            conn.execute("INSERT INTO international.country (iso2, name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (iso2, name))
    for z in stamm:
        uid = z["unternehmen_id"]
        iso2 = LAND_ISO2.get(z["land"])
        known = iso2 and conn.execute("SELECT 1 FROM international.country WHERE iso2=%s", (iso2,)).fetchone()
        if z["land"] and not known:
            bericht["sitzland_unbekannt"] += 1
        lei = z["lei"] if re.fullmatch(r"[A-Z0-9]{20}", z["lei"] or "") else None
        if z["lei"] and not lei:
            bericht["lei_ungueltig"] += 1
        conn.execute(
            "INSERT INTO international.entity (id, legal_name, domicile, lei, sector) VALUES (%s,%s,%s,%s,%s) "
            "ON CONFLICT (id) DO UPDATE SET legal_name=EXCLUDED.legal_name, domicile=EXCLUDED.domicile, sector=EXCLUDED.sector, lei=COALESCE(EXCLUDED.lei, international.entity.lei)",
            (uid, z["name"], iso2 if known else None, lei, z["branche"] or None))
        ids = [("LEI", lei)] if lei else []
        ids += [("YAHOO_TICKER", z["ticker"])] if z["ticker"] else []
        for isin in filter(None, [z["isin_haupt"]] + re.split(r"[;, ]+", z["weitere_isins"] or "")):
            ids.append(("ISIN", isin))
            conn.execute("INSERT INTO international.instrument (entity_id, isin, kind) VALUES (%s,%s,'security') ON CONFLICT (isin) DO NOTHING", (uid, isin))
        for scheme, value in ids:
            conn.execute("INSERT INTO international.identifier (scheme, value, entity_id) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (scheme, value, uid))
        bericht["entitaeten"] += 1


def fakten_zeilen(zeitreihe, vorhandene_ids, quelle_id, bericht):
    gesehen = set()
    for z in zeitreihe:
        uid, kz = z["unternehmen_id"], z["kennzahl"]
        if uid not in vorhandene_ids:
            bericht["uebersprungen: ID nicht in stammdaten"] += 1
            continue
        metric = KENNZAHL.get(kz)
        if not metric:
            bericht[f"uebersprungen: Kennzahl {kz} ohne Mapping"] += 1
            continue
        end = date.fromisoformat(z["stichtag"])
        start = None
        if metric in DAUER:
            if (end.month, end.day) != (12, 31):
                bericht["uebersprungen: Zeitraumwert ohne 31.12.-Stichtag"] += 1
                continue
            start = date(end.year, 1, 1)
        if z["einheit"] == "Mio. EUR":
            wert, einheit, skal = scale_value(z["wert"], 6), z["waehrung"], 6
        elif z["einheit"] == "Anteil":
            wert, einheit, skal = Decimal(z["wert"]), "ratio", 0
        else:
            bericht[f"uebersprungen: Einheit {z['einheit']}"] += 1
            continue
        schluessel = "|".join([uid, kz, z["stichtag"], z["rechnungslegung"], z["ebene"]])
        if schluessel in gesehen:
            raise ValueError(f"doppelter Schlüssel in zeitreihe_lang.csv: {schluessel}")
        gesehen.add(schluessel)
        yield {
            "entity_id": uid, "metric_code": metric, "period_start": start, "period_end": end, "value": wert, "unit": einheit,
            "accounting_standard": standard(z["rechnungslegung"]), "consolidation": konsolidierung(z["rechnungslegung"], z["ebene"]),
            "dimensions": {"ebene_laut_quelle": z["ebene"]}, "source_id": quelle_id, "source_fact_key": schluessel, "mapping_version": MAPPING_VERSION,
            "quality": "raw" if z["pruefstatus"] == "geparst" else "validated",
            "provenance": {"kennzahl": kz, "originalwert": z["wert"], "originaleinheit": z["einheit"], "skalierung_exp10": skal,
                           "rechnungslegung": z["rechnungslegung"], "ebene": z["ebene"], "pruefstatus": z["pruefstatus"], "quelle": z["quelle"]},
        }


def importieren(conn, dry_run=False, stamm_pfad=STAMM, zeitreihe_pfad=ZEITREIHE):
    bericht = Counter()
    stamm, zeitreihe = lies_csv(stamm_pfad), lies_csv(zeitreihe_pfad)
    roh = Path(zeitreihe_pfad).read_bytes()
    with ingest.ingestion_lauf(conn, "import-de", dry_run=dry_run) as lauf:
        entitaeten_importieren(conn, stamm, bericht)
        try:
            rel = str(Path(zeitreihe_pfad).resolve().relative_to(REPO))
        except ValueError:
            rel = str(zeitreihe_pfad)
        sid = ingest.quelle_registrieren(conn, "repo-zeitreihe", rel, BLOB + rel, hashlib.sha256(roh).hexdigest(), rel,
                                         rights_status="eigene Erhebung aus frei zugänglichen Quellen")
        for f in fakten_zeilen(zeitreihe, {z["unternehmen_id"] for z in stamm}, sid, bericht):
            if ingest.fakt_einfuegen(conn, f):
                bericht["fakten_neu"] += 1
            else:
                bericht["fakten_vorhanden"] += 1
        lauf.anzahl = bericht["fakten_neu"]
        lauf.wasserzeichen = {"zeitreihe_sha256": hashlib.sha256(roh).hexdigest()}
    return bericht


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="alles ausführen und zurückrollen")
    a = ap.parse_args()
    with db.verbinden() as c:
        db.migrieren(c)
        db.laender_laden(c)
        for k, v in sorted(importieren(c, dry_run=a.dry_run).items()):
            print(f"{k}: {v}")
        if a.dry_run:
            print("Dry-Run: zurückgerollt")
