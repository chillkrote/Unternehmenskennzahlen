"""Datenkatalog (P3.1): Quellen mit Lizenzstand und die Prognosegeber der OECD-Länder.

* data_source   eine Zeile je Quelle aus docs/datenquellen.md (Text der Tabelle) und server/katalog/datenquellen.csv
                (Kennung, Bereich, Status, Entscheidung, Pflichtangabe, Aliase). Aliase verbinden die Quelle mit den Kennungen,
                unter denen Importe sie führen: series.provider, source_document.provider, ingestion_run.adapter.
* forecaster    Prognosegeber je Land aus volkswirtschaft/prognosegeber_oecd.csv (Recherche, PROGNOSEGEBER.md).

Beide Tabellen sind Verzeichnisse aus dem Repo; der ETL (etl/katalog.py) ersetzt ihren Inhalt bei jedem geänderten Stand.
Nur neue Objekte, keine Änderung bestehender Daten.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-10
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

STATUS = ("geeignet", "namensnennung", "voraussichtlich", "pruefen", "eingeschraenkt", "kritisch", "erledigt")


def upgrade():
    op.execute(f"""
    CREATE TABLE international.data_source (
      id text PRIMARY KEY CHECK (id ~ '^[a-z0-9-]{{2,40}}$'),
      name text NOT NULL,
      area text NOT NULL,                          -- unternehmen, markt, finanzen, volkswirtschaft, handel, politik, geodaten, nachrichten, dienst
      used_for text,
      access text,                                 -- Abruf (Skript) laut Verzeichnis
      credentials text,                            -- Schlüssel nötig? (nur der Name, nie der Wert)
      license text,                                -- Lizenz / Weiterverbreitung, Text wie im Verzeichnis
      assessment text,                             -- Bewertung, Text wie im Verzeichnis
      status text NOT NULL CHECK (status IN {STATUS!r}),
      decision text CHECK (decision ~ '^E[0-9]+$'),
      attribution text,                            -- Pflichtangabe für die Seite „Quellen“
      links text[] NOT NULL DEFAULT '{{}}',          -- Fundstellen (Bedingungen, About-Seiten)
      aliases text[] NOT NULL DEFAULT '{{}}',
      position integer NOT NULL,
      run_id bigint REFERENCES international.ingestion_run(id)
    )""")
    op.execute("""
    CREATE TABLE international.forecaster (
      id integer PRIMARY KEY,                      -- Zeilennummer in prognosegeber_oecd.csv
      source_id text NOT NULL REFERENCES international.data_source(id),
      geo text NOT NULL,
      country text,
      publisher text NOT NULL,
      type text,
      publication text,
      variables text,
      horizon text,
      rhythm text,
      url text,
      access text,
      data_url text,
      priority smallint,
      note text,
      http_status_url text,
      http_status_data text,
      checked text,
      run_id bigint REFERENCES international.ingestion_run(id)
    )""")
    op.execute("CREATE INDEX forecaster_geo ON international.forecaster (geo, priority)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS international.forecaster")
    op.execute("DROP TABLE IF EXISTS international.data_source")
