"""Bestehendes Kernmodell (international/migrations/001–004) unter Alembic stellen.

Die SQL-Dateien bleiben unverändert die Quelle für das Grundschema; die bisherigen Skripte (international/db.py) wenden sie
weiterhin an. Diese Revision führt genau dieselben Dateien mit derselben Buchführung (public.international_migrations,
SHA-256 je Datei) aus. Dadurch ist es egal, ob zuerst `alembic upgrade head` oder ein bestehendes Importskript läuft:
keine Datei wird doppelt angewendet, eine nachträglich geänderte Datei bricht ab. Neue Schemaänderungen kommen ab jetzt
nur noch als Alembic-Revisionen.

Revision ID: 0001
Revises:
Create Date: 2026-11-09
"""
import hashlib
from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

SQL_ORDNER = Path(__file__).resolve().parents[3] / "international" / "migrations"
BESTAND = ["001_kernmodell.sql", "002_metriken.sql", "003_metriken_minderheiten.sql", "004_unternehmenstabelle.sql"]


def upgrade():
    roh = op.get_bind().connection.dbapi_connection          # psycopg-Verbindung: SQL-Dateien mit $$-Funktionen unverändert ausführen
    with roh.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS public.international_migrations "
                    "(name text PRIMARY KEY, sha256 text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        for name in BESTAND:
            text = (SQL_ORDNER / name).read_text(encoding="utf-8")
            h = hashlib.sha256(text.encode()).hexdigest()
            cur.execute("SELECT sha256 FROM public.international_migrations WHERE name = %s", (name,))
            alt = cur.fetchone()
            if alt:
                if alt[0] != h:
                    raise RuntimeError(f"{name} wurde nach der Anwendung geändert; neue Alembic-Revision anlegen statt ändern")
                continue
            cur.execute(text)
            cur.execute("INSERT INTO public.international_migrations (name, sha256) VALUES (%s, %s)", (name, h))


def downgrade():
    # Bewusst nicht umkehrbar: würde alle Daten löschen. Zurück nur über ein Backup (docs/betrieb.md).
    raise RuntimeError("Das Kernmodell wird nicht per Downgrade entfernt; Wiederherstellung über Backup")
