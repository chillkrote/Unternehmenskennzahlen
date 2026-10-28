"""Datenbankzugang, Migrationen und Länderstammdaten. Zugangsdaten nur über Umgebungsvariablen (INTERNATIONAL_DATABASE_URL)."""
import csv
import hashlib
import os
from pathlib import Path

import psycopg

HIER = Path(__file__).resolve().parent
MIGRATIONEN = HIER / "migrations"
LAENDER_CSV = HIER / "oecd_mitglieder.csv"


def verbinden(url=None):
    url = url or os.environ.get("INTERNATIONAL_DATABASE_URL")
    if not url:
        raise SystemExit("INTERNATIONAL_DATABASE_URL ist nicht gesetzt (z. B. postgresql://postgres:PASSWORT@127.0.0.1:5433/international)")
    return psycopg.connect(url, autocommit=True)   # Transaktionen immer ausdrücklich mit conn.transaction()


def migrieren(conn):
    """Wendet neue Migrationen in Dateinamenreihenfolge an, je Datei eine Transaktion. Geänderte, schon angewendete Dateien brechen ab."""
    with conn.transaction():
        conn.execute("CREATE TABLE IF NOT EXISTS public.international_migrations (name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
    angewendet = []
    for pfad in sorted(MIGRATIONEN.glob("*.sql")):
        text = pfad.read_text(encoding="utf-8")
        h = hashlib.sha256(text.encode()).hexdigest()
        alt = conn.execute("SELECT sha256 FROM public.international_migrations WHERE name=%s", (pfad.name,)).fetchone()
        if alt:
            if alt[0] != h:
                raise RuntimeError(f"Migration {pfad.name} wurde nach der Anwendung geändert; neue Migration anlegen statt ändern")
            continue
        with conn.transaction():
            conn.execute(text)
            conn.execute("INSERT INTO public.international_migrations (name, sha256) VALUES (%s, %s)", (pfad.name, h))
        angewendet.append(pfad.name)
    return angewendet


def laender_laden(conn, csv_pfad=LAENDER_CSV):
    n = 0
    with open(csv_pfad, encoding="utf-8", newline="") as f, conn.transaction():
        for z in csv.DictReader(f):
            conn.execute(
                "INSERT INTO international.country (iso2, iso3, name, oecd_from) VALUES (%s,%s,%s,%s) "
                "ON CONFLICT (iso2) DO UPDATE SET iso3=EXCLUDED.iso3, name=EXCLUDED.name, oecd_from=EXCLUDED.oecd_from",
                (z["iso2"], z["iso3"], z["name"], z["oecd_from"] or None))
            n += 1
    return n


if __name__ == "__main__":
    with verbinden() as c:
        print("angewendet:", migrieren(c) or "nichts Neues")
        print("Länder:", laender_laden(c))
