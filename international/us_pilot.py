"""US-Pilot: zehn SEC-Melder aus verschiedenen Branchen (zwei Banken getrennt) registrieren, laden und importieren.

Schritte (alle wiederholbar):
  register   neue Unternehmen über stammdaten/ids.py anlegen (vorhandene ISINs behalten ihre ID)
  import     Companyfacts je Unternehmen abrufen (Live, rate-limitiert) und in die Datenbank schreiben
Aufruf: SEC_USER_AGENT="Name mail@example.org" INTERNATIONAL_DATABASE_URL=... python3 international/us_pilot.py register|import [--dry-run]
"""
import csv
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "stammdaten"))

PILOT = HIER / "us_pilot.csv"


def lies():
    with open(PILOT, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def registrieren():
    import ids
    reg = ids.lade(neu=True)
    ergebnis = {}
    for z in lies():
        uid = reg.registrieren(name=z["name"], branche=z["branche"], isin=z["isin"], land="United States", ticker=z["ticker"],
                               herkunft="SEC-Pilot", hinweis=f"SEC CIK {int(z['cik']):010d}")
        ergebnis[z["isin"]] = uid
    return ergebnis


def importieren(dry_run=False):
    import db
    import sec
    from httpsafe import SichererClient
    ids_ = registrieren()
    client = SichererClient({sec.HOST})
    bericht = []
    with db.verbinden() as conn:
        db.migrieren(conn)
        db.laender_laden(conn)
        import import_de
        import_de.importieren(conn, dry_run=dry_run)     # sorgt dafür, dass die Entitäten (inkl. neuer US-IDs) vorhanden sind
        for z in lies():
            uid = ids_[z["isin"]]
            if dry_run:
                conn.execute("INSERT INTO international.entity (id, legal_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, z["name"]))
            pfad, h, n = sec.abrufen(client, z["cik"], db.HIER / "objektspeicher" / "sec")
            neu, alt = sec.importieren(conn, pfad, h, uid, z["cik"], dry_run=dry_run, bank=z["bank"] == "ja")
            bericht.append((uid, z["name"], neu, alt, n))
            print(f"{uid} {z['name']}: neu {neu}, vorhanden {alt} ({n} Bytes)")
    return bericht


if __name__ == "__main__":
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus == "register":
        for isin, uid in registrieren().items():
            print(uid, isin)
    elif modus == "import":
        importieren("--dry-run" in sys.argv)
    else:
        sys.exit(__doc__)
