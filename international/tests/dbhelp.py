"""Wegwerf-Datenbank für Tests. Braucht INTERNATIONAL_TEST_DATABASE_URL (Verbindung mit CREATEDB-Recht); ohne sie werden DB-Tests übersprungen."""
import os
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict, make_conninfo

HIER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HIER))
ADMIN = os.environ.get("INTERNATIONAL_TEST_DATABASE_URL")
braucht_db = unittest.skipUnless(ADMIN, "INTERNATIONAL_TEST_DATABASE_URL nicht gesetzt")


@contextmanager
def wegwerf_db():
    name = "intl_test_" + uuid.uuid4().hex[:10]
    with psycopg.connect(ADMIN, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    url = make_conninfo(ADMIN, dbname=name)
    try:
        yield url
    finally:
        with psycopg.connect(ADMIN, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
