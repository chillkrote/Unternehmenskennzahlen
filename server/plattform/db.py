"""Datenbankzugang der API: SQLAlchemy-Engine, je Verbindung nur lesend und mit Zeitlimit je Anweisung."""
from functools import lru_cache

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine

from .config import Einstellungen, sqlalchemy_url


@lru_cache(maxsize=4)
def engine_fuer(url: str, statement_timeout_ms: int) -> Engine:
    eng = create_engine(sqlalchemy_url(url), pool_size=5, max_overflow=5, pool_pre_ping=True, pool_recycle=1800)

    @event.listens_for(eng, "connect")
    def _sitzung(dbapi_conn, _record):
        # Die öffentliche API schreibt nie: jede Transaktion ist read-only, lange Abfragen brechen ab.
        with dbapi_conn.cursor() as cur:
            cur.execute(f"SET statement_timeout = {int(statement_timeout_ms)}")
            cur.execute("SET default_transaction_read_only = on")
            cur.execute("SET application_name = 'sphaerae-api'")
        dbapi_conn.commit()

    return eng


def engine(e: Einstellungen) -> Engine:
    if not e.database_url:
        raise RuntimeError("DATABASE_URL ist nicht gesetzt (z. B. postgresql://sphaerae:PASSWORT@db:5432/sphaerae)")
    return engine_fuer(e.database_url, e.statement_timeout_ms)
