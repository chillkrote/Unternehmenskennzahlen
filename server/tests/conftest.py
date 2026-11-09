"""Testumgebung: Wegwerf-Datenbank auf einem echten PostgreSQL 16 (TEST_DATABASE_URL mit CREATEDB-Recht).

Ohne TEST_DATABASE_URL werden die Datenbanktests übersprungen; die übrigen Tests laufen immer.
Die Daten kommen aus dem Repo (Unternehmenstabelle, Stammdaten, Zeitreihen) über denselben ETL wie im Betrieb."""
import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from urllib.parse import urlsplit, urlunsplit

SERVER = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER))
ADMIN = os.environ.get("TEST_DATABASE_URL") or os.environ.get("INTERNATIONAL_TEST_DATABASE_URL")


def _neue_db():
    name = "sphaerae_test_" + uuid.uuid4().hex[:8]
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f'CREATE DATABASE "{name}"')
    t = urlsplit(ADMIN)                       # URL-Form behalten (SQLAlchemy und Alembic brauchen eine URL)
    return name, urlunsplit((t.scheme, t.netloc, "/" + name, t.query, t.fragment))


def _weg(name):
    with psycopg.connect(ADMIN, autocommit=True) as c:
        c.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')


@pytest.fixture
def leere_db():
    if not ADMIN:
        pytest.skip("TEST_DATABASE_URL nicht gesetzt")
    name, url = _neue_db()
    yield url
    _weg(name)


@pytest.fixture(scope="session")
def geladene_db():
    """Einmal je Testlauf: Schema migrieren und die echten Repo-Daten laden (ca. 30–60 s)."""
    if not ADMIN:
        pytest.skip("TEST_DATABASE_URL nicht gesetzt")
    name, url = _neue_db()
    alt = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        from etl import laden
        laden.main([])
        yield url
    finally:
        if alt is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = alt
        _weg(name)


@pytest.fixture(scope="session")
def client(geladene_db):
    from fastapi.testclient import TestClient
    from plattform.config import Einstellungen
    from plattform.main import erstellen
    app = erstellen(Einstellungen(database_url=geladene_db, rate_limit_per_minute=0, cors_origins=["http://localhost:8080"]))
    with TestClient(app) as c:
        yield c
