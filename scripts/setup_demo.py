"""Explicit initialization, refuses any existing public table or rehearsal schema."""

import uuid
from pathlib import Path

from rehearsal.engine import connect

ROOT = Path(__file__).resolve().parents[1]


def setup():
    with connect() as conn:
        if (
            conn.execute("SELECT 1 FROM pg_tables WHERE schemaname='public'").fetchone()
            or conn.execute("SELECT 1 FROM pg_namespace WHERE nspname='rehearsal'").fetchone()
        ):
            raise RuntimeError(
                "Database is not empty. Create a separate disposable database; setup never resets data."
            )
        conn.execute((ROOT / "vendor/chinook/schema.sql").read_text(encoding="utf-8"))
        conn.execute((ROOT / "sql/ledger.sql").read_text(encoding="utf-8"))
        conn.execute("INSERT INTO rehearsal.identity VALUES(true,%s)", (uuid.uuid4(),))
        conn.execute((ROOT / "fixtures/seed.sql").read_text(encoding="utf-8"))


if __name__ == "__main__":
    setup()
    print("Initialized schema and synthetic fixtures. Existing databases are never reset.")
