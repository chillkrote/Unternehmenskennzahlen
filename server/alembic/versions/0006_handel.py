"""Handel (P5a): Exporte je Gut, Land und Jahr aus CEPII BACI (app/data/gueter.json, erzeugt von app/gueter_baci.py).

* trade_good      Gütergruppen (HS-Positionen, Bereich)
* trade_export    Exportwert je Exportland, Gut und Jahr (Mio. US-Dollar). Die Summe über alle Länder ist der Weltwert,
                  daraus folgen Weltmarktanteile und die Konzentration (HHI) – abgeleitete Kennzahlen.
* trade_partner   die fünf größten Abnehmer je Exportland und Gut im letzten Jahr (belegte Handelsbeziehungen laut BACI).

Nur neue Objekte. Der ETL (etl/handel.py) ersetzt den Inhalt bei geänderter Datei.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-10
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE international.trade_good (
      id text PRIMARY KEY,
      name text NOT NULL,
      area text,
      hs text[] NOT NULL DEFAULT '{}',
      position integer NOT NULL
    )""")
    op.execute("""
    CREATE TABLE international.trade_export (
      good_id text NOT NULL REFERENCES international.trade_good(id),
      geo text NOT NULL,
      year smallint NOT NULL,
      value double precision NOT NULL CHECK (value >= 0),   -- Mio. US-Dollar
      run_id bigint REFERENCES international.ingestion_run(id),
      PRIMARY KEY (good_id, year, geo)
    )""")
    op.execute("CREATE INDEX trade_export_geo ON international.trade_export (geo, good_id, year)")
    op.execute("""
    CREATE TABLE international.trade_partner (
      good_id text NOT NULL REFERENCES international.trade_good(id),
      geo text NOT NULL,                             -- Exportland
      year smallint NOT NULL,
      rank smallint NOT NULL,
      partner text NOT NULL,                         -- Abnehmerland
      value double precision NOT NULL,               -- Mio. US-Dollar
      run_id bigint REFERENCES international.ingestion_run(id),
      PRIMARY KEY (good_id, geo, year, rank)
    )""")
    op.execute("CREATE INDEX trade_partner_partner ON international.trade_partner (partner, good_id, year)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS international.trade_partner")
    op.execute("DROP TABLE IF EXISTS international.trade_export")
    op.execute("DROP TABLE IF EXISTS international.trade_good")
