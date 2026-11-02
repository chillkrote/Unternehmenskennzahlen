"""ESEF-Pilot (Frankreich, Niederlande, Italien, Spanien): je zehn Melder (Banken getrennt) registrieren, laden und importieren.

  register   Unternehmen über stammdaten/ids.py anlegen, LEI je ISIN gegen GLEIF prüfen
  import     alle im Index vorhandenen Einreichungen je Unternehmen laden (Live, rate-limitiert) und importieren
Aufruf: INTERNATIONAL_USER_AGENT="Name mail@example.org" INTERNATIONAL_DATABASE_URL=... python3 international/fr_pilot.py register|import [--dry-run] [--csv=nl_pilot.csv]
Ohne --csv gilt fr_pilot.csv. Spalte "land" (ISO-2) ist optional, Standard FR.
"""
import csv
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
sys.path.insert(0, str(HIER))
sys.path.insert(0, str(HIER.parent / "stammdaten"))

PILOT = HIER / "fr_pilot.csv"
LAENDER = {"FR": "France", "NL": "Netherlands", "IT": "Italy", "ES": "Spain"}


def waehle(argv):
    """--csv=<Datei im Ordner international/> wählt die Pilotliste; Standard Frankreich."""
    global PILOT
    for a in argv:
        if a.startswith("--csv="):
            p = (HIER / a[6:]).resolve()
            if p.parent != HIER or p.suffix != ".csv":
                raise SystemExit("--csv nur mit einer CSV-Datei im Ordner international/")
            PILOT = p


def lies():
    with open(PILOT, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def registrieren(client=None):
    """Legt fehlende Unternehmen an. Mit client: LEI und Land je ISIN gegen GLEIF prüfen, Abweichung bricht ab."""
    import esef
    import ids
    reg = ids.lade(neu=True)
    ergebnis = {}
    for z in lies():
        esef.lei_pruefen(z["lei"])
        if client is not None:
            lei, name, land = esef.lei_zu_isin(client, z["isin"])
            iso = z.get("land") or "FR"
            if lei != z["lei"] or land != iso:
                raise SystemExit(f"{z['name']}: GLEIF nennt {lei} ({land}), CSV {z['lei']}")
        bestand = z.get("bestand_id") or ""
        if bestand:
            # schon erfasste Zeile (nur Name, aus der Tabellenerhebung): ID behalten, ISIN/LEI/Ticker ergänzen
            if bestand not in reg.unternehmen or reg.unternehmen[bestand]["land"] != LAENDER[z.get("land") or "FR"]:
                raise SystemExit(f"{z['name']}: bestand_id {bestand} unbekannt oder anderes Land")
            reg.isins_zuordnen(bestand, z["isin"], ())
            uid = bestand
        else:
            uid = reg.registrieren(name=z["name"], branche=z["branche"], isin=z["isin"], land=LAENDER[z.get("land") or "FR"], ticker=z["ticker"],
                                   lei=z["lei"], herkunft="ESEF-Pilot", hinweis=f"ESEF-Pilot {LAENDER[z.get('land') or 'FR']}")
        r = reg.unternehmen[uid]
        # schon vorhandene Zeilen (z. B. aus der Tabellenerhebung, nur mit Namen) ergänzen; abweichende Angaben nie überschreiben
        for feld, wert in (("isin_haupt", z["isin"]), ("lei", z["lei"])):
            if r[feld] and r[feld] != wert:
                raise SystemExit(f"{uid} {z['name']}: {feld} {r[feld]} weicht von {wert} ab")
        reg.aktualisieren(uid, isin_haupt=z["isin"], lei=z["lei"], ticker=z["ticker"] if not r["ticker"] else "", land=LAENDER[z.get("land") or "FR"])
        ergebnis[z["isin"]] = uid
    reg.speichern()
    return ergebnis


def importieren(dry_run=False):
    import db
    import esef
    import import_de
    from httpsafe import AbrufFehler, SichererClient
    client = SichererClient(esef.HOSTS, max_bytes=200_000_000)   # einzelne Konzern-JSON (z. B. UniCredit) sind größer als 50 MB
    ids_ = registrieren(client)
    with db.verbinden() as conn:
        db.migrieren(conn)
        db.laender_laden(conn)
        import_de.importieren(conn, dry_run=dry_run)     # Entitäten (inkl. neuer FR-IDs) anlegen
        for z in lies():
            uid = ids_[z["isin"]]
            if dry_run:
                conn.execute("INSERT INTO international.entity (id, legal_name) VALUES (%s,%s) ON CONFLICT DO NOTHING", (uid, z["name"]))
            gesamt_neu = 0
            liste = [e for e in esef.einreichungen(client, z["lei"]) if e["attributes"].get("json_url")]
            for e in sorted(liste, key=lambda x: x["attributes"]["fxo_id"]):
                try:
                    pfad, h, n, url = esef.abrufen(client, e, db.HIER / "objektspeicher" / "esef")
                except AbrufFehler as ex:
                    if "größer als" not in str(ex):
                        raise
                    print(f"  übersprungen (zu groß): {e['attributes']['fxo_id']}")
                    continue
                neu, alt = esef.importieren(conn, pfad, h, url, e, uid, z["lei"], dry_run=dry_run, bank=z["bank"] == "ja")
                gesamt_neu += neu
            print(f"{uid} {z['name']}: {len(liste)} Einreichungen, neu {gesamt_neu}")


if __name__ == "__main__":
    waehle(sys.argv)
    modus = sys.argv[1] if len(sys.argv) > 1 else ""
    if modus == "register":
        import esef
        from httpsafe import SichererClient
        for isin, uid in registrieren(SichererClient(esef.HOSTS)).items():
            print(uid, isin)
    elif modus == "import":
        importieren("--dry-run" in sys.argv)
    else:
        sys.exit(__doc__)
