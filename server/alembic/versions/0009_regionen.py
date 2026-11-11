"""Regionen unterhalb der Staaten (NUTS-3, in Deutschland Kreise und kreisfreie Städte) als gemeinsamer Schlüssel für
Wirtschafts- und Wahldaten.

* region   ein Gebiet je Code der Quelle (NUTS-3 „DE111“), mit amtlichem Landesschlüssel (Kreisschlüssel/AGS „08111“), Name,
           Staat, übergeordnetem Gebiet (Bundesland „DE-BW“) und Klassifikationsstand (NUTS 2024). Die Werte der Regionen stehen wie
           alle Reihen in series/observation (geo = Code); Wahlergebnisse je Kreis nutzen den Landesschlüssel.

Nur neue Objekte.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-11
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE international.region (
      code text PRIMARY KEY,                          -- Code der Quelle (NUTS-3)
      level text NOT NULL,                            -- nuts3
      country text NOT NULL,                          -- ISO-2 (Eurostat-Schreibweise)
      national_code text,                             -- amtlicher Schlüssel im Land (DE: fünfstelliger Kreisschlüssel)
      name text NOT NULL,
      name_source text,                               -- Bezeichnung bei Eurostat
      parent text,                                    -- übergeordnetes Gebiet (DE: Bundesland ISO 3166-2)
      classification text NOT NULL,                   -- NUTS 2024
      run_id bigint REFERENCES international.ingestion_run(id)
    )""")
    op.execute("CREATE UNIQUE INDEX region_national ON international.region (country, level, national_code) WHERE national_code IS NOT NULL")
    op.execute("CREATE INDEX region_parent ON international.region (parent)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS international.region")
