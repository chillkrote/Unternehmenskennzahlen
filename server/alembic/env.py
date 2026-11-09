"""Alembic-Umgebung. Das Schema wird mit handgeschriebenen Migrationen gepflegt (kein Autogenerate), weil das Kernmodell
Trigger, Funktionen und Ausschluss-Constraints nutzt, die SQLAlchemy-Modelle nicht vollständig abbilden."""
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from plattform.config import sqlalchemy_url  # noqa: E402

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)


def _url():
    url = config.get_main_option("sqlalchemy.url") or os.environ.get("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL ist nicht gesetzt")
    return sqlalchemy_url(url)


def run_migrations_offline():
    context.configure(url=_url(), literal_binds=True, version_table_schema="public")
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    eng = create_engine(_url(), poolclass=pool.NullPool)
    with eng.connect() as conn:
        context.configure(connection=conn, version_table_schema="public", transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
