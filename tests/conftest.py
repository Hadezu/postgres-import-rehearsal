import os
import sys
import uuid
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


@pytest.fixture
def db(monkeypatch):
    """Own a fresh database. Never drop/reset the PGDATABASE supplied by a user."""
    name = "rehearsal_test_" + uuid.uuid4().hex
    admin = psycopg.connect(dbname=os.environ.get("PGDATABASE", "postgres"), autocommit=True)
    admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    monkeypatch.setenv("PGDATABASE", name)
    from setup_demo import setup

    try:
        setup()
        yield name
    finally:
        admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))
        admin.close()


@pytest.fixture
def raw():
    return (ROOT / "fixtures/customers.csv").read_bytes()


@pytest.fixture
def mapping():
    import json

    return json.loads((ROOT / "fixtures/mapping.json").read_text())
