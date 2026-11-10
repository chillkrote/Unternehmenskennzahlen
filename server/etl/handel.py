"""Handel (Revisionen 0006, 0008): Exporte je Gut aus app/data/gueter.json und Importseite aus app/data/gueter_importe.json
(beide CEPII BACI, app/gueter_baci.py) in die Datenbank.

Gleiche Dateien wie die Oberfläche. Der Inhalt der Tabellen wird in einer Transaktion ersetzt (ingestion_run „handel“); sind
die Dateien unverändert, passiert nichts. Fehlt gueter_importe.json, bleiben die Importtabellen leer (die Exportseite lädt trotzdem).
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATEI = REPO / "app" / "data" / "gueter.json"
DATEI_IMPORTE = REPO / "app" / "data" / "gueter_importe.json"
BLOB = "https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/"


def importieren(conn, dry_run=False, erzwingen=False, datei=DATEI, datei_importe=None):
    import ingest
    bericht = Counter()
    datei = Path(datei)
    if not datei.exists():
        bericht["keine_datei"] = 1
        return bericht
    roh = datei.read_bytes()
    # Importseite: neben der Exportdatei (gleicher Ordner), wenn nicht ausdrücklich angegeben
    datei_importe = Path(datei_importe) if datei_importe else (DATEI_IMPORTE if datei == DATEI else datei.with_name("gueter_importe.json"))
    roh_imp = datei_importe.read_bytes() if datei_importe.exists() else b""
    sha = hashlib.sha256(roh + roh_imp).hexdigest() if roh_imp else hashlib.sha256(roh).hexdigest()
    alt = conn.execute("SELECT watermark->>'sha256' FROM international.ingestion_run WHERE adapter = 'handel' AND status = 'ok' "
                       "ORDER BY id DESC LIMIT 1").fetchone()
    if alt and alt[0] == sha and not erzwingen:
        bericht["unveraendert"] = 1
        return bericht
    d = json.loads(roh)
    jahre, letzt = d["jahre"], d["jahr"]
    try:
        rel = str(datei.resolve().relative_to(REPO))
    except ValueError:
        rel = str(datei)
    with ingest.ingestion_lauf(conn, "handel", dry_run=dry_run) as lauf:
        ingest.quelle_registrieren(conn, "repo-baci", rel + "@" + sha[:12], BLOB + rel, sha, rel,
                                   rights_status=d.get("quelle", "CEPII BACI (Etalab 2.0)"))
        conn.execute("DELETE FROM international.trade_import_supplier")
        conn.execute("DELETE FROM international.trade_import")
        conn.execute("DELETE FROM international.trade_partner")
        conn.execute("DELETE FROM international.trade_export")
        conn.execute("DELETE FROM international.trade_good")
        for pos, g in enumerate(d["gruppen"]):
            conn.execute("INSERT INTO international.trade_good (id, name, area, hs, position) VALUES (%s,%s,%s,%s,%s)",
                         (g["id"], g["name"], g.get("bereich"), g.get("hs") or [], pos))
            bericht["gueter"] += 1
        with conn.cursor().copy("COPY international.trade_export (good_id, geo, year, value, partners, partner_hhi, run_id) FROM STDIN") as cp:
            for geo, gueter in sorted(d["laender"].items()):
                for gid, e in gueter.items():
                    for jahr, v in zip(jahre, e.get("v") or []):
                        if v is not None:
                            # Zahl und HHI aller Abnehmer liegen nur für das letzte Jahr vor
                            cp.write_row((gid, geo, jahr, v, e.get("pn") if jahr == letzt else None, e.get("phhi") if jahr == letzt else None, lauf.run_id))
                            bericht["exporte"] += 1
        with conn.cursor().copy("COPY international.trade_partner (good_id, geo, year, rank, partner, value, run_id) FROM STDIN") as cp:
            for geo, gueter in sorted(d["laender"].items()):
                for gid, e in gueter.items():
                    for rang, (partner, v) in enumerate(e.get("partner") or [], start=1):
                        cp.write_row((gid, geo, letzt, rang, partner, v, lauf.run_id))
                        bericht["partner"] += 1
        if roh_imp:
            imp = json.loads(roh_imp)
            ij, il = imp["jahre"], imp["jahr"]
            bekannt = {g["id"] for g in d["gruppen"]}
            with conn.cursor().copy("COPY international.trade_import (good_id, geo, year, value, unallocated, suppliers, hhi, top_supplier, top_share, run_id) "
                                    "FROM STDIN") as cp:
                for geo, gueter in sorted(imp["laender"].items()):
                    for gid, e in gueter.items():
                        if gid not in bekannt:
                            continue
                        u = e.get("u") or [0] * len(ij)
                        for k, jahr in enumerate(ij):
                            if e["v"][k] is None:
                                continue
                            t1 = e["t1"][k] or [None, None]
                            cp.write_row((gid, geo, jahr, e["v"][k], u[k] or 0, e["n"][k], e["hhi"][k], t1[0], t1[1], lauf.run_id))
                            bericht["importe"] += 1
            with conn.cursor().copy("COPY international.trade_import_supplier (good_id, geo, year, rank, supplier, value, run_id) FROM STDIN") as cp:
                for geo, gueter in sorted(imp["laender"].items()):
                    for gid, e in gueter.items():
                        if gid not in bekannt:
                            continue
                        for rang, (lief, v) in enumerate(e.get("top") or [], start=1):
                            cp.write_row((gid, geo, il, rang, lief, v, lauf.run_id))
                            bericht["lieferlaender"] += 1
        lauf.anzahl = bericht["exporte"] + bericht["partner"] + bericht["importe"] + bericht["lieferlaender"]
        lauf.wasserzeichen = {"sha256": sha, "jahr": letzt}
    return bericht
