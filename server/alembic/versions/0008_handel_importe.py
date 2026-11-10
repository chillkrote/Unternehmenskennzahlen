"""Handel: Importabhängigkeit je Importland und Gut (Audit 2026-11, 4.3) aus app/data/gueter_importe.json.

Die bisherigen Tabellen beschreiben die Exportseite (Weltmarktanteile). Ob ein bestimmtes Importland von einem Lieferland abhängt,
steht erst hier:

* trade_import            Importwert je Importland, Gut und Jahr, Zahl der Lieferländer, HHI über ALLE zuordenbaren Lieferländer,
                          nicht zuordenbarer Teil (Partner ohne ISO-Code), größtes Lieferland mit Anteil
* trade_import_supplier   die größten Lieferländer je Importland und Gut im letzten Jahr (belegte bilaterale Ströme)
* trade_export.partners / partner_hhi   Zahl und HHI aller Abnehmer eines Exportlands (letztes Jahr), statt eines HHI nur über fünf

Die vollständige bilaterale Matrix bleibt außerhalb der Datenbank (app/gueter_baci.py verdichtet sie). Nur neue Objekte und
optionale Spalten.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-10
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE international.trade_import (
      good_id text NOT NULL REFERENCES international.trade_good(id),
      geo text NOT NULL,                              -- Importland
      year smallint NOT NULL,
      value double precision NOT NULL CHECK (value >= 0),      -- Mio. US-Dollar, einschließlich nicht zuordenbarer Lieferländer
      unallocated double precision NOT NULL DEFAULT 0,         -- davon ohne zuordenbares Lieferland
      suppliers integer NOT NULL,                              -- Zahl der Lieferländer
      hhi double precision,                                    -- über alle zuordenbaren Lieferländer (0 bis 10 000)
      top_supplier text,
      top_share double precision,                              -- Anteil des größten Lieferlands am Importwert
      run_id bigint REFERENCES international.ingestion_run(id),
      PRIMARY KEY (good_id, geo, year)
    )""")
    op.execute("CREATE INDEX trade_import_geo ON international.trade_import (geo, year, good_id)")
    op.execute("CREATE INDEX trade_import_top ON international.trade_import (top_supplier, year, good_id)")
    op.execute("""
    CREATE TABLE international.trade_import_supplier (
      good_id text NOT NULL REFERENCES international.trade_good(id),
      geo text NOT NULL,                              -- Importland
      year smallint NOT NULL,
      rank smallint NOT NULL,
      supplier text NOT NULL,                         -- Lieferland
      value double precision NOT NULL,                -- Mio. US-Dollar
      run_id bigint REFERENCES international.ingestion_run(id),
      PRIMARY KEY (good_id, geo, year, rank)
    )""")
    op.execute("CREATE INDEX trade_import_supplier_lieferland ON international.trade_import_supplier (supplier, good_id, year)")
    op.execute("ALTER TABLE international.trade_export ADD COLUMN IF NOT EXISTS partners integer")
    op.execute("ALTER TABLE international.trade_export ADD COLUMN IF NOT EXISTS partner_hhi double precision")


def downgrade():
    op.execute("ALTER TABLE international.trade_export DROP COLUMN IF EXISTS partner_hhi")
    op.execute("ALTER TABLE international.trade_export DROP COLUMN IF EXISTS partners")
    op.execute("DROP TABLE IF EXISTS international.trade_import_supplier")
    op.execute("DROP TABLE IF EXISTS international.trade_import")
