"""Datenbankmigrationen: reproduzierbar, idempotent und verträglich mit dem bisherigen Migrationslauf (international/db.py)."""
import sys
from pathlib import Path

import psycopg
from alembic import command
from alembic.config import Config

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER.parent / "international"))


def _cfg(url):
    cfg = Config(str(SERVER / "alembic.ini"))
    cfg.set_main_option("script_location", str(SERVER / "alembic"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def _tabellen(url):
    with psycopg.connect(url) as c:
        return {r[0] for r in c.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='international'")}


def test_upgrade_auf_leerer_db_und_wiederholung(leere_db):
    command.upgrade(_cfg(leere_db), "head")
    t = _tabellen(leere_db)
    assert {"entity", "fact", "company_register", "company_alias", "country", "ingestion_run",
            "company_profile", "company_profile_value", "financial_statement", "financial_statement_line", "profile_metric", "series", "observation", "data_source", "forecaster", "trade_good", "trade_export", "trade_partner"} <= t
    command.upgrade(_cfg(leere_db), "head")                       # zweiter Lauf ändert nichts
    with psycopg.connect(leere_db) as c:
        assert c.execute("SELECT version_num FROM public.alembic_version").fetchone()[0] == "0006"
        assert c.execute("SELECT count(*) FROM public.international_migrations").fetchone()[0] == 4
        assert c.execute("SELECT 1 FROM pg_extension WHERE extname='pg_trgm'").fetchone()


def test_alter_lauf_nach_alembic_wendet_nichts_doppelt_an(leere_db):
    import db as intl_db
    command.upgrade(_cfg(leere_db), "head")
    with intl_db.verbinden(leere_db) as c:
        assert intl_db.migrieren(c) == []


def test_alembic_nach_altem_lauf(leere_db):
    import db as intl_db
    with intl_db.verbinden(leere_db) as c:
        assert len(intl_db.migrieren(c)) == 4
    command.upgrade(_cfg(leere_db), "head")
    with psycopg.connect(leere_db) as c:
        assert c.execute("SELECT count(*) FROM public.international_migrations").fetchone()[0] == 4


def test_downgrade_der_plattform_revision(leere_db):
    command.upgrade(_cfg(leere_db), "head")
    command.downgrade(_cfg(leere_db), "0001")
    with psycopg.connect(leere_db) as c:
        assert not c.execute("SELECT 1 FROM information_schema.columns WHERE table_name='country' AND column_name='name_de'").fetchone()
    command.upgrade(_cfg(leere_db), "head")


def test_downgrade_der_profiltabellen(leere_db):
    command.upgrade(_cfg(leere_db), "head")
    command.downgrade(_cfg(leere_db), "0002")
    assert not {"company_profile", "financial_statement_line", "profile_snapshot"} & _tabellen(leere_db)
    command.upgrade(_cfg(leere_db), "head")
    assert "company_profile" in _tabellen(leere_db)
