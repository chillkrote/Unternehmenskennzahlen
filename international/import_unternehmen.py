"""Importiert die zusammengeführte Unternehmenstabelle (unternehmen-tabelle/Unternehmen_Tabelle.csv) in das Schema international.

* Schlüssel ist die Repo-ID (U000123, entity.id). Zeilen ohne ID bekommen KEINE neue ID (die vergibt nur stammdaten/ids.py), sondern
  einen stabilen row_key (ISIN, sonst LEI, sonst Land+Name) in company_register.
* Aliase (stammdaten/unternehmen_aliase.csv, zusammengelegte Namen aus den Bereinigungsprotokollen) und Prüfmarkierungen werden mit importiert.
* Eine ISIN steht höchstens bei einem Unternehmen: Konflikte brechen den Import vor dem ersten Schreiben ab.
* Wiederholbar: Zeilen werden per Upsert fortgeschrieben, Zeilen, die in der Datei fehlen, werden active=false (nie gelöscht).
* --dry-run führt alles aus und rollt zurück. Schreibt nie in stammdaten/ oder unternehmen-tabelle/.
Aufruf: INTERNATIONAL_DATABASE_URL=... python3 international/import_unternehmen.py [--dry-run] [--datei PFAD]
"""
import argparse
import csv
import hashlib
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

HIER = Path(__file__).resolve().parent
REPO = HIER.parent
sys.path.insert(0, str(HIER))
import db  # noqa: E402
import import_de  # noqa: E402
import ingest  # noqa: E402

TABELLE = REPO / "unternehmen-tabelle" / "Unternehmen_Tabelle.csv"
ALIASE = REPO / "stammdaten" / "unternehmen_aliase.csv"
PROT_BEREINIGUNG = REPO / "unternehmen-tabelle" / "bereinigung_protokoll.csv"
PROT_PRUEFLISTE = REPO / "unternehmen-tabelle" / "bereinigung_protokoll_pruefliste.csv"
PRUEFLISTE = REPO / "unternehmen-tabelle" / "bereinigung_pruefliste.csv"
SPALTEN = ["unternehmen_id", "Name *", "Rechtsform", "Land *", "Sitz", "ISIN", "Ticker", "Börse", "Börsennotiert *", "Branche *",
           "WZ/NACE-Code", "LEI", "Handelsregisternummer", "Website", "Bank *", "Index-Zugehörigkeit", "Beschreibung", "Quelle Stammdaten (URL) *"]
LAND_ALIAS = {"USA": "US", "United States": "US", "UK": "GB", "United Kingdom": "GB", "South Korea": "KR", "Korea": "KR", "Czech Republic": "CZ",
              "Turkey": "TR", "Türkei": "TR"}


def lies_csv(pfad, delimiter=","):
    with open(pfad, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimiter))


def norm(name):
    s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def zeilenschluessel(zeilen):
    """Stabiler Schlüssel je Zeile; bei Kollisionen (gleiche Basis) wird #2, #3 ... angehängt."""
    gesehen, ergebnis = Counter(), []
    for z in zeilen:
        if z["ISIN"]:
            basis = "ISIN:" + z["ISIN"]
        elif z["LEI"]:
            basis = "LEI:" + z["LEI"]
        else:
            basis = f"NAME:{z['Land *']}|{norm(z['Name *'])}"
        gesehen[basis] += 1
        ergebnis.append(basis if gesehen[basis] == 1 else f"{basis}#{gesehen[basis]}")
    return ergebnis


def pruefen(zeilen, isin_zuordnung, stammdaten):
    """Gibt Fehler (brechen ab) zurück: doppelte ID/ISIN/LEI, ISIN bei fremder ID, unbekannte ID."""
    fehler = []
    for spalte, bez in (("unternehmen_id", "ID"), ("ISIN", "ISIN"), ("LEI", "LEI")):
        zaehler = Counter(z[spalte] for z in zeilen if z[spalte])
        fehler += [f"{bez} {k} steht in {n} Zeilen" for k, n in zaehler.items() if n > 1]
    for z in zeilen:
        uid, isin = z["unternehmen_id"], z["ISIN"]
        if uid and uid not in stammdaten:
            fehler.append(f"ID {uid} ({z['Name *']}) nicht in stammdaten/unternehmen_ids.csv")
        if isin and isin in isin_zuordnung and isin_zuordnung[isin] != uid:
            fehler.append(f"ISIN {isin} ({z['Name *']}): Register sagt {isin_zuordnung[isin]}, Tabelle {uid or 'keine ID'}")
    return fehler


def pruefmarken(z, isin_zuordnung):
    """(code, detail) je Zeile. Leere Liste = nichts zu prüfen."""
    m = []
    beschr = z["Beschreibung"]
    if "bitte prüfen" in beschr:
        m.append(("automatisch_ergaenzt", beschr))
    if z["Börsennotiert *"] == "ja" and not z["ISIN"]:
        m.append(("boersennotiert_ohne_isin", ""))
    if z["Branche *"] == "sonstige":
        m.append(("branche_platzhalter", ""))
    return m


def importieren(conn, dry_run=False, datei=TABELLE):
    bericht = Counter()
    zeilen = lies_csv(datei, ";")
    if not zeilen or list(zeilen[0]) != SPALTEN:
        raise SystemExit(f"unerwartete Spalten in {datei}: {list(zeilen[0]) if zeilen else 'leer'}")
    roh = Path(datei).read_bytes()
    stamm = lies_csv(import_de.STAMM)
    stammdaten = {z["unternehmen_id"]: z for z in stamm}
    isin_zuordnung = {z["isin"]: z["unternehmen_id"] for z in lies_csv(REPO / "stammdaten" / "isin_zuordnung.csv")}
    fehler = pruefen(zeilen, isin_zuordnung, stammdaten)
    if fehler:
        raise SystemExit("Import abgebrochen, bitte zuerst klären:\n  " + "\n  ".join(fehler[:50]) + (f"\n  … {len(fehler) - 50} weitere" if len(fehler) > 50 else ""))
    schluessel = zeilenschluessel(zeilen)
    nach_id = {z["unternehmen_id"]: k for z, k in zip(zeilen, schluessel) if z["unternehmen_id"]}
    nach_name = defaultdict(list)
    for z, k in zip(zeilen, schluessel):
        nach_name[z["Name *"]].append(k)
        nach_name[(z["Land *"], z["Name *"])].append(k)

    with ingest.ingestion_lauf(conn, "import-unternehmenstabelle", dry_run=dry_run) as lauf:
        # Entitäten für die Registerfirmen sicherstellen (idempotent, gleiche Logik wie import_de)
        import_de.entitaeten_importieren(conn, stamm, bericht)
        laender = {r[0].lower(): r[1] for r in conn.execute("SELECT name, iso2 FROM international.country")}
        iso2s = {r[0] for r in conn.execute("SELECT iso2 FROM international.country")}
        for i, (z, k) in enumerate(zip(zeilen, schluessel), 1):
            iso = LAND_ALIAS.get(z["Land *"]) or laender.get(z["Land *"].lower())
            conn.execute(
                "INSERT INTO international.company_register (row_key,row_no,entity_id,name,legal_form,country_name,domicile,seat,isin,ticker,exchange,"
                "listed,sector,nace,lei,register_no,website,is_bank,indices,description,source_url,active,imported_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,true,now()) "
                "ON CONFLICT (row_key) DO UPDATE SET row_no=EXCLUDED.row_no, entity_id=EXCLUDED.entity_id, name=EXCLUDED.name, legal_form=EXCLUDED.legal_form,"
                " country_name=EXCLUDED.country_name, domicile=EXCLUDED.domicile, seat=EXCLUDED.seat, isin=EXCLUDED.isin, ticker=EXCLUDED.ticker,"
                " exchange=EXCLUDED.exchange, listed=EXCLUDED.listed, sector=EXCLUDED.sector, nace=EXCLUDED.nace, lei=EXCLUDED.lei,"
                " register_no=EXCLUDED.register_no, website=EXCLUDED.website, is_bank=EXCLUDED.is_bank, indices=EXCLUDED.indices,"
                " description=EXCLUDED.description, source_url=EXCLUDED.source_url, active=true, imported_at=now()",
                (k, i, z["unternehmen_id"] or None, z["Name *"], z["Rechtsform"] or None, z["Land *"], iso if iso in iso2s else None,
                 z["Sitz"] or None, z["ISIN"] or None, z["Ticker"] or None, z["Börse"] or None, z["Börsennotiert *"] == "ja", z["Branche *"],
                 z["WZ/NACE-Code"] or None, z["LEI"] or None, z["Handelsregisternummer"] or None, z["Website"] or None, z["Bank *"] == "ja",
                 z["Index-Zugehörigkeit"] or None, z["Beschreibung"] or None, z["Quelle Stammdaten (URL) *"]))
            bericht["zeilen"] += 1
            bericht["davon_mit_id"] += bool(z["unternehmen_id"])
        weg = conn.execute("UPDATE international.company_register SET active=false WHERE active AND NOT (row_key = ANY(%s))", (schluessel,)).rowcount
        bericht["nicht_mehr_in_tabelle"] = weg

        # Aliase und Prüfmarken werden bei jedem Lauf vollständig aus den Dateien neu aufgebaut (die Dateien sind die Quelle)
        conn.execute("DELETE FROM international.company_alias WHERE source LIKE 'datei:%'")
        conn.execute("DELETE FROM international.review_flag")
        alias = set()
        for a in lies_csv(ALIASE):
            k = nach_id.get(a["unternehmen_id"])
            if k:
                alias.add((a["alias"], k, a["art"], "datei:stammdaten/unternehmen_aliase.csv"))
            else:
                bericht["alias_ohne_tabellenzeile"] += 1
        for p in lies_csv(PROT_BEREINIGUNG):
            ks = nach_name.get((p["land"], p["name_behalten"]), [])
            if len(ks) == 1:
                alias.add((p["name_entfernt"], ks[0], p["aktion"], "datei:unternehmen-tabelle/bereinigung_protokoll.csv"))
            else:
                bericht["protokoll_nicht_eindeutig"] += 1
        for p in lies_csv(PROT_PRUEFLISTE):
            ks = nach_name.get(p["name_behalten"], [])
            if len(ks) == 1:
                alias.add((p["name_entfernt"], ks[0], p["aktion"], "datei:unternehmen-tabelle/bereinigung_protokoll_pruefliste.csv"))
            else:
                bericht["protokoll_nicht_eindeutig"] += 1
        for a in sorted(alias):
            conn.execute("INSERT INTO international.company_alias (alias,row_key,kind,source) VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING", a)
        bericht["aliase"] = len(alias)

        marken = set()
        for z, k in zip(zeilen, schluessel):
            for code, detail in pruefmarken(z, isin_zuordnung):
                marken.add((k, code, detail, None, None))
        for p in lies_csv(PRUEFLISTE):
            for name in (p["name_1"], p["name_2"]):
                ks = nach_name.get(name, [])
                if len(ks) == 1:
                    marken.add((ks[0], "pruefliste_" + ("zusammengelegt" if p["entscheidung"] == "zusammengelegt" else "getrennt"),
                                p["grund"], p["entscheidung"], p["begruendung"]))
        for m in sorted(marken, key=lambda t: tuple(map(str, t))):
            conn.execute("INSERT INTO international.review_flag (row_key,code,detail,decision,reason) VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING", m)
        bericht["pruefmarken"] = len(marken)
        for code, n in conn.execute("SELECT code, count(*) FROM international.review_flag GROUP BY code"):
            bericht[f"marke_{code}"] = n

        try:
            rel = str(Path(datei).resolve().relative_to(REPO))
        except ValueError:
            rel = str(datei)
        sha = hashlib.sha256(roh).hexdigest()
        conn.execute("INSERT INTO international.register_import (file, sha256, rows) VALUES (%s,%s,%s)", (rel, sha, len(zeilen)))
        lauf.anzahl = len(zeilen)
        lauf.wasserzeichen = {"tabelle_sha256": sha}
    return bericht


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="alles ausführen und zurückrollen")
    ap.add_argument("--datei", default=str(TABELLE))
    a = ap.parse_args()
    with db.verbinden() as c:
        db.migrieren(c)
        db.laender_laden(c)
        for k, v in sorted(importieren(c, dry_run=a.dry_run, datei=a.datei).items()):
            print(f"{k}: {v}")
        if a.dry_run:
            print("Dry-Run: zurückgerollt")
