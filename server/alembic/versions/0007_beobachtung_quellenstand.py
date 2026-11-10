"""Beobachtungen: Quellenstand und Abruf je Fassung (Audit 2026-11, 4.4).

Bisher trug eine Fassung nur valid_from/valid_to (Erfassungszeitpunkt des Imports in dieser Datenbank). Das ist der
Datenbankstand, nicht der Veröffentlichungsstand der Quelle. Zwei neue, optionale Spalten halten je Fassung fest, was die Quelle
selbst über ihren Stand sagt:

* source_updated  Stand der Quelle laut Abruf (serien.csv: stand_quelle; z. B. Datum der letzten Aktualisierung des Datensatzes)
* fetched         Datum des Abrufs bei der Quelle (serien.csv: abruf)

Bestehende Zeilen bleiben unverändert (NULL = nicht festgehalten). Nur neue Spalten, keine Änderung bestehender Daten.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-10
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE international.observation ADD COLUMN IF NOT EXISTS source_updated text")
    op.execute("ALTER TABLE international.observation ADD COLUMN IF NOT EXISTS fetched text")


def downgrade():
    op.execute("ALTER TABLE international.observation DROP COLUMN IF EXISTS fetched")
    op.execute("ALTER TABLE international.observation DROP COLUMN IF EXISTS source_updated")
