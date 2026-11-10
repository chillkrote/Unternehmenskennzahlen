"""Erstbefüllung und Aktualisierung der Plattform-Datenbank aus den Dateien im Repo (Unternehmensregister und Kennzahlen).

Verwendet die bestehenden, getesteten Importe aus international/ (keine zweite Implementierung):
  1. alembic upgrade head                       Schema (Kernmodell 001–004 + Plattform-Revisionen)
  2. Länder: 38 OECD-Mitglieder (oecd_mitglieder.csv) + alle Länder der Weltkugel (app/geo/laender.geojson, deutsche Namen)
  3. import_unternehmen.importieren             Unternehmenstabelle -> company_register, entity, Aliase, Prüfmarken
  4. Sitzland je Zeile mit derselben Zuordnung wie die Oberfläche (app/register.py: land_codes)
  5. import_de.importieren                       Zeitreihen deutscher Unternehmen -> fact (mit Quelle und Vintage)
  6. etl.profile.importieren                     Unternehmensprofile aus app/data/unternehmen.json (Kennzahlen, Abschlüsse, Gremien …)
  7. etl.vwl.importieren                         VWL-Reihen aus volkswirtschaft/ (series, observation mit Vintage)
  8. etl.handel.importieren                      Exporte je Gut aus app/data/gueter.json (CEPII BACI)
  9. etl.katalog.importieren                     Datenkatalog: Quellen (docs/datenquellen.md + server/katalog/) und Prognosegeber

Jeder Import läuft in einer eigenen Transaktion mit Laufprotokoll (international.ingestion_run): schlägt ein Schritt fehl,
bleibt der letzte gültige Stand dieses Schritts unverändert. Die Unternehmens-IDs (U000123) kommen unverändert aus
stammdaten/ und unternehmen-tabelle/; dieses Skript vergibt keine IDs.

Aufruf (aus server/):  DATABASE_URL=postgresql://… python3 -m etl.laden [--ohne-kennzahlen] [--ohne-profile] [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent
SERVER = HIER.parent
REPO = SERVER.parent
sys.path.insert(0, str(REPO / "international"))
sys.path.insert(0, str(REPO / "app"))
sys.path.insert(0, str(SERVER))

from plattform.config import psycopg_url  # noqa: E402

LAENDER_GEO = REPO / "app" / "geo" / "laender.geojson"


def schema_migrieren(url):
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(SERVER / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


def laender_welt(conn):
    """Alle Länder der Weltkugel ergänzen (ISO-3166-Alpha-2). Vorhandene OECD-Zeilen behalten ihren Namen und ihr Beitrittsdatum."""
    d = json.loads(LAENDER_GEO.read_text(encoding="utf-8"))
    n, gesehen = 0, set()
    with conn.transaction():
        for f in d["features"]:
            p = f["properties"]
            iso2, iso3 = (p.get("iso") or "").upper(), (p.get("a3") or "").upper()
            if len(iso2) != 2 or not iso2.isalpha() or iso2 in gesehen:
                continue
            gesehen.add(iso2)
            iso3 = iso3 if len(iso3) == 3 and iso3.isalpha() else None
            if iso3 and conn.execute("SELECT 1 FROM international.country WHERE iso3=%s AND iso2<>%s", (iso3, iso2)).fetchone():
                iso3 = None
            conn.execute(
                "INSERT INTO international.country (iso2, iso3, name, name_de, region) VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (iso2) DO UPDATE SET name_de = EXCLUDED.name_de, region = EXCLUDED.region, "
                "iso3 = COALESCE(international.country.iso3, EXCLUDED.iso3)",
                (iso2, iso3, p.get("name_en") or p.get("name") or iso2, p.get("name") or None, p.get("region") or None))
            n += 1
    return n


def sitzland_zuordnen(conn):
    """company_register.domicile für Zeilen ohne Land nachtragen, mit der Zuordnung, die auch das Terminal nutzt (register.land_codes)."""
    import register
    codes = register.land_codes()
    bekannt = {r[0] for r in conn.execute("SELECT iso2 FROM international.country")}
    n = 0
    with conn.transaction():
        for (name,) in conn.execute("SELECT DISTINCT country_name FROM international.company_register WHERE domicile IS NULL").fetchall():
            code = codes.get(name.strip().lower())
            if code and code in bekannt:
                n += conn.execute("UPDATE international.company_register SET domicile=%s WHERE domicile IS NULL AND country_name=%s",
                                  (code, name)).rowcount
        # Sitzland der Entität aus der Registerzeile übernehmen, wo die Stammdaten keines liefern (nur Ergänzung, nie Überschreiben)
        conn.execute("UPDATE international.entity e SET domicile = r.domicile FROM international.company_register r "
                     "WHERE r.entity_id = e.id AND e.domicile IS NULL AND r.domicile IS NOT NULL")
    return n


def rechte_vergeben(conn, rolle="sphaerae_api"):
    """Leserechte für die API-Rolle (angelegt von deploy/initdb/01-rollen.sh). Fehlt die Rolle (lokale Tests), passiert nichts."""
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (rolle,)).fetchone():
        return False
    with conn.transaction():
        conn.execute(f"GRANT USAGE ON SCHEMA international TO {rolle}")
        conn.execute(f"GRANT SELECT ON ALL TABLES IN SCHEMA international TO {rolle}")
        conn.execute(f"GRANT SELECT ON public.alembic_version TO {rolle}")
        conn.execute(f"ALTER DEFAULT PRIVILEGES IN SCHEMA international GRANT SELECT ON TABLES TO {rolle}")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ohne-kennzahlen", action="store_true", help="nur Stammdaten, ohne zeitreihen/zeitreihe_lang.csv")
    ap.add_argument("--ohne-profile", action="store_true", help="ohne Unternehmensprofile (app/data/unternehmen.json)")
    ap.add_argument("--profile-erzwingen", action="store_true", help="Profile neu laden, auch wenn unternehmen.json unverändert ist")
    ap.add_argument("--ohne-vwl", action="store_true", help="ohne VWL-Reihen (volkswirtschaft/)")
    ap.add_argument("--dry-run", action="store_true", help="Importe ausführen und zurückrollen (Schema wird trotzdem migriert)")
    a = ap.parse_args(argv)
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL ist nicht gesetzt")
    schema_migrieren(url)
    import db as intl_db
    import import_de
    import import_unternehmen
    with intl_db.verbinden(psycopg_url(url)) as conn:
        print("OECD-Länder:", intl_db.laender_laden(conn))
        print("Länder (Weltkugel):", laender_welt(conn))
        for k, v in sorted(import_unternehmen.importieren(conn, dry_run=a.dry_run).items()):
            print(f"  unternehmen.{k}: {v}")
        print("Sitzland nachgetragen:", sitzland_zuordnen(conn))
        if not a.ohne_kennzahlen:
            for k, v in sorted(import_de.importieren(conn, dry_run=a.dry_run).items()):
                print(f"  kennzahlen.{k}: {v}")
        if not a.ohne_profile:
            from etl import profile
            for k, v in sorted(profile.importieren(conn, dry_run=a.dry_run, erzwingen=a.profile_erzwingen).items()):
                print(f"  profile.{k}: {v}")
        if not a.ohne_vwl:
            from etl import vwl
            for k, v in sorted(vwl.importieren(conn, dry_run=a.dry_run).items()):
                print(f"  vwl.{k}: {v}")
        from etl import handel
        for k, v in sorted(handel.importieren(conn, dry_run=a.dry_run).items()):
            print(f"  handel.{k}: {v}")
        from etl import katalog
        for k, v in sorted(katalog.importieren(conn, dry_run=a.dry_run).items()):
            print(f"  katalog.{k}: {v}")
        conn.execute("ANALYZE international.company_register")
        print("Leserechte API-Rolle:", "vergeben" if rechte_vergeben(conn) else "Rolle fehlt (nur lokal ohne Compose)")


if __name__ == "__main__":
    main()
