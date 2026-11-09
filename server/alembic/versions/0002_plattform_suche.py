"""Plattform-API: Volltext-/Ähnlichkeitssuche (pg_trgm), deutsche Ländernamen, Indizes für Filter.

* pg_trgm: fehlertolerante Suche über Namen und Aliase (Trigramm-GIN-Indizes), kein eigener Suchserver nötig.
* country.name_de, country.region: deutsche Namen und Weltregion (aus app/geo/laender.geojson, ETL), damit „Deutschland“ findet.
* Indizes für die Filter der Unternehmensliste (Land, Branche, Notierung).
Nur neue Objekte, keine Änderung bestehender Daten.

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-09
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute("ALTER TABLE international.country ADD COLUMN IF NOT EXISTS name_de text")
    op.execute("ALTER TABLE international.country ADD COLUMN IF NOT EXISTS region text")
    op.execute("CREATE INDEX IF NOT EXISTS company_register_name_trgm ON international.company_register USING gin (lower(name) gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS company_alias_trgm ON international.company_alias USING gin (lower(alias) gin_trgm_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS company_register_domicile ON international.company_register (domicile) WHERE active")
    op.execute("CREATE INDEX IF NOT EXISTS company_register_sector ON international.company_register (sector) WHERE active")
    op.execute("CREATE INDEX IF NOT EXISTS company_register_ticker ON international.company_register (lower(ticker)) WHERE ticker IS NOT NULL")
    op.execute("CREATE INDEX IF NOT EXISTS fact_entity ON international.fact (entity_id)")


def downgrade():
    for idx in ("fact_entity", "company_register_ticker", "company_register_sector", "company_register_domicile",
                "company_alias_trgm", "company_register_name_trgm"):
        op.execute(f"DROP INDEX IF EXISTS international.{idx}")
    op.execute("ALTER TABLE international.country DROP COLUMN IF EXISTS region")
    op.execute("ALTER TABLE international.country DROP COLUMN IF EXISTS name_de")
