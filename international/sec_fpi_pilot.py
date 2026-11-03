"""Pilot für Nicht-US-Melder bei der SEC (Formulare 20-F und 40-F, teils 10-K) aus CH, CA, AU, MX, CL, TR, IL.

Quelle wie beim US-Pilot: SEC-Companyfacts (siehe sec.py), dazu die IFRS-Tags (ifrs-full) in der jeweiligen Berichtswährung.
Die LEI stammt aus GLEIF (Name und Sitzland werden gegen den LEI-Datensatz geprüft); die ISIN ist nicht belegt und bleibt leer.
Schritte (wiederholbar):
  register   Unternehmen über stammdaten/ids.py anlegen (bestand_id ergänzt eine vorhandene Namenszeile)
  import     Companyfacts abrufen (Live, rate-limitiert) und in die Datenbank schreiben
Aufruf: INTERNATIONAL_USER_AGENT="Name mail@example.org" INTERNATIONAL_DATABASE_URL=... python3 international/sec_fpi_pilot.py register|import [--dry-run]
"""
import csv
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "stammdaten"))

PILOT = HIER / "sec_fpi_pilot.csv"
LAENDER = {"CH": "Switzerland", "CA": "Canada", "AU": "Australia", "MX": "Mexico", "CL": "Chile", "TR": "Turkey", "IL": "Israel"}


def lies():
    with open(PILOT, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def registrieren(client=None):
    import esef
    import ids
    reg = ids.lade(neu=True)
    ergebnis = {}
    for z in lies():
        esef.lei_pruefen(z["lei"])
        if client is not None:
            name, land = esef.lei_info(client, z["lei"])
            if land != z["land"]:
                raise SystemExit(f"{z['name']}: GLEIF nennt Sitzland {land}, CSV {z['land']}")
        if z["bestand_id"]:
            if z["bestand_id"] not in reg.unternehmen:
                raise SystemExit(f"{z['name']}: bestand_id {z['bestand_id']} unbekannt")
            uid = z["bestand_id"]
        else:
            uid = reg.registrieren(name=z["name"], branche=z["branche"], isin="", land=LAENDER[z["land"]], ticker="", lei=z["lei"],
                                   status="börsennotiert", herkunft="SEC-Pilot", hinweis=f"SEC CIK {int(z['cik']):010d}")
        reg.aktualisieren(uid, lei=z["lei"], land=LAENDER[z["land"]])
        ergebnis[z["lei"]] = uid
    reg.speichern()
    return ergebnis


def importieren(dry_run=False):
    import db
    import import_de
    import sec
    from httpsafe import SichererClient
    ids_ = registrieren()
    client = SichererClient({sec.HOST}, max_bytes=300_000_000)
    bericht = []
    with db.verbinden() as conn:
        db.migrieren(conn)
        db.laender_laden(conn)
        import_de.importieren(conn, dry_run=dry_run)
        for z in lies():
            uid = ids_[z["lei"]]
            if dry_run:
                conn.execute("INSERT INTO international.entity (id, legal_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, z["name"]))
            pfad, h, n = sec.abrufen(client, z["cik"], db.HIER / "objektspeicher" / "sec")
            neu, alt = sec.importieren(conn, pfad, h, uid, z["cik"], dry_run=dry_run, bank=z["bank"] == "ja")
            bericht.append((uid, z["name"], neu, alt, n))
            print(f"{uid} {z['name']}: neu {neu}, vorhanden {alt} ({n} Bytes)", flush=True)
    return bericht


if __name__ == "__main__":
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus == "register":
        from httpsafe import SichererClient
        for lei, uid in registrieren(SichererClient({"api.gleif.org"})).items():
            print(uid, lei)
    elif modus == "import":
        importieren("--dry-run" in sys.argv)
    else:
        sys.exit(__doc__)
