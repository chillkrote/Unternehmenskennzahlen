"""Handel (Revision 0006): Exporte je Gut aus app/data/gueter.json (CEPII BACI) in die Datenbank.

Gleiche Datei wie die Weltkugel (Reiter Handel, Güter). Inhalt der drei Tabellen wird in einer Transaktion ersetzt
(ingestion_run „handel“); ist die Datei unverändert, passiert nichts.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATEI = REPO / "app" / "data" / "gueter.json"
BLOB = "https://github.com/chillkrote/Unternehmenskennzahlen/blob/main/"


def importieren(conn, dry_run=False, erzwingen=False, datei=DATEI):
    import ingest
    bericht = Counter()
    datei = Path(datei)
    if not datei.exists():
        bericht["keine_datei"] = 1
        return bericht
    roh = datei.read_bytes()
    sha = hashlib.sha256(roh).hexdigest()
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
        conn.execute("DELETE FROM international.trade_partner")
        conn.execute("DELETE FROM international.trade_export")
        conn.execute("DELETE FROM international.trade_good")
        for pos, g in enumerate(d["gruppen"]):
            conn.execute("INSERT INTO international.trade_good (id, name, area, hs, position) VALUES (%s,%s,%s,%s,%s)",
                         (g["id"], g["name"], g.get("bereich"), g.get("hs") or [], pos))
            bericht["gueter"] += 1
        with conn.cursor().copy("COPY international.trade_export (good_id, geo, year, value, run_id) FROM STDIN") as cp:
            for geo, gueter in sorted(d["laender"].items()):
                for gid, e in gueter.items():
                    for jahr, v in zip(jahre, e.get("v") or []):
                        if v is not None:
                            cp.write_row((gid, geo, jahr, v, lauf.run_id))
                            bericht["exporte"] += 1
        with conn.cursor().copy("COPY international.trade_partner (good_id, geo, year, rank, partner, value, run_id) FROM STDIN") as cp:
            for geo, gueter in sorted(d["laender"].items()):
                for gid, e in gueter.items():
                    for rang, (partner, v) in enumerate(e.get("partner") or [], start=1):
                        cp.write_row((gid, geo, letzt, rang, partner, v, lauf.run_id))
                        bericht["partner"] += 1
        lauf.anzahl = bericht["exporte"] + bericht["partner"]
        lauf.wasserzeichen = {"sha256": sha, "jahr": letzt}
    return bericht
