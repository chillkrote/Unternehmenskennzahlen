"""Volkswirtschaftliche Reihen (VWL) mit Vintage: volkswirtschaft/serien.csv und zeitreihe_lang.csv in der Datenbank.

* series        eine Zeile je Reihe aus serien.csv (Thema, Einheit, Format, Art, Frequenz, Quelle, Datensatz, Filter, Abruf …)
* observation   Werte je Reihe, Gebiet und Zeitraum. Ändert ein Import einen Wert, bleibt die alte Fassung mit valid_to erhalten
                (Vintage); verschwindet ein Wert aus der Quelle, wird er mit valid_to beendet, nicht gelöscht.
                Aktueller Stand: valid_to IS NULL. Stand „bekannt zum“ Zeitpunkt t: valid_from <= t < valid_to.

Gebiete (geo) sind die Codes der Quellen (DE, EA20, EU27_2020, UK, EL, OECD …), daher kein Fremdschlüssel auf country.
Zeiträume als Text wie in der Quelle: JJJJ, JJJJ-MM, JJJJ-Qn (innerhalb einer Reihe gleich lang, Textsortierung = Zeitsortierung).
Nur neue Objekte, keine Änderung bestehender Daten.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-09
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE international.series (
      id text PRIMARY KEY,
      topic text,
      name text NOT NULL,
      unit text,
      fmt text,
      kind text,                                   -- rate, niveau, index, saldo …
      frequency text,                              -- A, Q, M
      core boolean NOT NULL DEFAULT false,
      provider text,
      dataset text,
      filter text,
      url text,
      fetched text,                                -- Abruf laut serien.csv
      forecast_from text,                          -- ab diesem Zeitraum Projektion (OECD Economic Outlook)
      note text,
      position integer NOT NULL,
      meta jsonb NOT NULL DEFAULT '{}',            -- übrige Spalten von serien.csv unverändert
      run_id bigint REFERENCES international.ingestion_run(id)
    )""")
    op.execute("""
    CREATE TABLE international.observation (
      series_id text NOT NULL REFERENCES international.series(id),
      geo text NOT NULL,
      period text NOT NULL CHECK (period ~ '^\\d{4}(-(0[1-9]|1[0-2])|-Q[1-4])?$'),
      value double precision NOT NULL,
      valid_from timestamptz NOT NULL DEFAULT now(),
      valid_to timestamptz,
      run_id bigint REFERENCES international.ingestion_run(id),
      source_id bigint NOT NULL REFERENCES international.source_document(id),
      CHECK (valid_to IS NULL OR valid_to > valid_from)
    )""")
    op.execute("CREATE UNIQUE INDEX observation_aktuell ON international.observation (series_id, geo, period) WHERE valid_to IS NULL")
    op.execute("CREATE INDEX observation_reihe ON international.observation (series_id, geo, period, valid_from)")


def downgrade():
    op.execute("DROP TABLE IF EXISTS international.observation")
    op.execute("DROP TABLE IF EXISTS international.series")
