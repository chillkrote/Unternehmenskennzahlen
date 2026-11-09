"""Unternehmensprofile: Kennzahlenstand, Abschlussposten, Gremien, Dokumente und Termine aus app/data/unternehmen.json.

Bisher bettet die Seite den ganzen Bestand ein (22,5 MB, davon 20 MB Bilanz- und GuV-Posten). Diese Revision legt die Tabellen
an, in die etl/profile.py den Stand übernimmt; die Seite lädt das Profil dann über /companies/{id}/profile.

* profile_snapshot        ein Importstand (Datei, SHA-256, Quellenliste, Laufprotokoll); immer genau einer ist aktuell
* profile_metric          Kennzahlenkatalog des Terminals (Name, Einheit, Format, Gruppe, „höher ist besser“, Hilfe)
* company_profile         je Unternehmen: Branche, Gruppe, Kopfangaben, Zeitreihen, Gremien, Dokumente, Termine (jsonb wie im Terminal)
* company_profile_value   Kennzahlenwerte des Profils (ein Wert je Unternehmen und Kennzahl, ohne Periode: Stand des Builds)
* financial_statement(_line)  gelieferte Abschlussposten je Stichtag, Teil (bilanz/guv) und Reihenfolge, mit Quelle je Teil

Die Kennzahlen-Fakten mit Periode und Vintage (international.fact) bleiben unverändert; diese Tabellen sind der Profilstand.
Nur neue Objekte, keine Änderung bestehender Daten.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-09
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""
    CREATE TABLE international.profile_snapshot (
      id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      source_id bigint NOT NULL REFERENCES international.source_document(id),
      run_id bigint REFERENCES international.ingestion_run(id),
      imported_at timestamptz NOT NULL DEFAULT now(),
      file_sha256 text NOT NULL CHECK (file_sha256 ~ '^[a-f0-9]{64}$'),
      sources text[] NOT NULL DEFAULT '{}',          -- Quelldateien laut Build (unternehmen.json: quellen)
      sectors jsonb NOT NULL DEFAULT '[]',           -- Branchenliste mit Gruppen und Schwerpunktkennzahlen
      groups text[] NOT NULL DEFAULT '{}',           -- Reihenfolge der Kennzahlengruppen
      alt_ids jsonb NOT NULL DEFAULT '{}',           -- alte Schreibweisen der IDs -> zentrale ID
      demo boolean NOT NULL DEFAULT false,
      is_current boolean NOT NULL DEFAULT false
    )""")
    op.execute("CREATE UNIQUE INDEX profile_snapshot_current ON international.profile_snapshot (is_current) WHERE is_current")
    op.execute("""
    CREATE TABLE international.profile_metric (
      code text PRIMARY KEY,
      name text NOT NULL,
      unit text,
      fmt text,
      metric_group text,
      higher_is_better boolean,
      help text,
      aliases text[] NOT NULL DEFAULT '{}',
      position integer NOT NULL
    )""")
    op.execute("""
    CREATE TABLE international.company_profile (
      entity_id text PRIMARY KEY REFERENCES international.entity(id),
      snapshot_id bigint NOT NULL REFERENCES international.profile_snapshot(id),
      name text NOT NULL,
      sector text NOT NULL,
      peer_group text,
      listed boolean NOT NULL DEFAULT false,
      position integer NOT NULL,                     -- Reihenfolge wie in unternehmen.json
      attributes jsonb NOT NULL DEFAULT '{}',        -- Kopfangaben (Sitz, Segment, Indizes, Rolle, Mutter, Archiv …)
      series jsonb NOT NULL DEFAULT '{}',            -- Zeitreihen je Kennzahl {basis, punkte}
      governance jsonb,                              -- Gremien, Kennzahlen, Vergütung, Quellen
      documents jsonb NOT NULL DEFAULT '[]',
      report_dates jsonb NOT NULL DEFAULT '[]'
    )""")
    op.execute("CREATE INDEX company_profile_sector ON international.company_profile (sector, peer_group)")
    op.execute("""
    CREATE TABLE international.company_profile_value (
      entity_id text NOT NULL REFERENCES international.company_profile(entity_id) ON DELETE CASCADE,
      metric_code text NOT NULL REFERENCES international.profile_metric(code),
      value double precision NOT NULL,
      PRIMARY KEY (entity_id, metric_code)
    )""")
    op.execute("CREATE INDEX company_profile_value_metric ON international.company_profile_value (metric_code)")
    op.execute("""
    CREATE TABLE international.financial_statement (
      id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
      entity_id text NOT NULL REFERENCES international.company_profile(entity_id) ON DELETE CASCADE,
      position integer NOT NULL,                     -- Reihenfolge der Abschlüsse im Profil
      period_end date NOT NULL,
      fiscal_year integer NOT NULL,
      currency text NOT NULL,
      source text,
      source_url text,
      fetched text,
      status text,
      part_sources jsonb NOT NULL DEFAULT '{}',      -- Quelle je Teil (bilanz, guv): quelle, quelle_url, abruf, seiten, hinweis, status
      UNIQUE (entity_id, position)
    )""")
    op.execute("""
    CREATE TABLE international.financial_statement_line (
      statement_id bigint NOT NULL REFERENCES international.financial_statement(id) ON DELETE CASCADE,
      part text NOT NULL CHECK (part IN ('bilanz', 'guv')),
      position integer NOT NULL,
      label text NOT NULL,
      value double precision,
      PRIMARY KEY (statement_id, part, position)
    )""")


def downgrade():
    for t in ("financial_statement_line", "financial_statement", "company_profile_value", "company_profile", "profile_metric",
              "profile_snapshot"):
        op.execute(f"DROP TABLE IF EXISTS international.{t}")
