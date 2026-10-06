import concurrent.futures
import os
import subprocess
import sys
import threading

import psycopg
import pytest

from rehearsal.engine import apply, connect, inspect, plan_import, undo
from rehearsal.input import Rejected


def test_lost_acknowledgement_after_commit(db, raw, mapping):
    p = plan_import(raw, mapping)
    code = f"import os; from rehearsal.engine import apply; apply({p['id']!r},{p['digest']!r}); os._exit(72)"
    proc = subprocess.run([sys.executable, "-c", code], timeout=15, check=False)
    assert proc.returncode == 72
    assert inspect(p["id"])["status"] == "APPLIED"
    assert apply(p["id"], p["digest"])["replayed"]
    assert len(inspect(p["id"])["events"]) == 1


def test_journal_failure_rolls_back_target_and_receipt(db, raw, mapping):
    p = plan_import(raw, mapping)
    with connect() as c:
        c.execute(
            "CREATE TRIGGER test_fail BEFORE INSERT ON rehearsal.events FOR EACH ROW EXECUTE FUNCTION rehearsal.no_mutation()"
        )
    with pytest.raises(psycopg.errors.RaiseException):
        apply(p["id"], p["digest"])
    with connect() as c:
        assert (
            c.execute("SELECT company FROM customer WHERE customer_id=1").fetchone()["company"]
            == "Old Demo"
        )
        assert c.execute("SELECT count(*) AS n FROM customer").fetchone()["n"] == 2
    p = inspect(p["id"])
    assert p["status"] == "PLANNED" and p["receipt"] is None and p["events"] == []


def test_unaware_writer_waits_then_undo_protects_it(db, raw, mapping):
    p = plan_import(raw, mapping)
    importer_wrote = threading.Event()
    writer_started = threading.Event()
    release = threading.Event()

    def pause(c, n):
        if n == 1:
            importer_wrote.set()
            assert release.wait(5)

    def human():
        assert importer_wrote.wait(5)
        with connect() as c:
            writer_started.set()
            c.execute("UPDATE customer SET company='Later human work' WHERE customer_id=1")

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        a = pool.submit(apply, p["id"], p["digest"], _after_write=pause)
        b = pool.submit(human)
        try:
            assert writer_started.wait(5)
            # Writer cannot complete while importer holds its normal PostgreSQL table lock.
            with pytest.raises(concurrent.futures.TimeoutError):
                b.result(timeout=0.1)
        finally:
            release.set()
        a.result(timeout=10)
        b.result(timeout=10)
    with pytest.raises(Rejected, match="UNDO_CONFLICT"):
        undo(p["id"], p["digest"])
    with connect() as c:
        assert (
            c.execute("SELECT company FROM customer WHERE customer_id=1").fetchone()["company"]
            == "Later human work"
        )


def test_two_undos_are_idempotent(db, raw, mapping):
    p = plan_import(raw, mapping)
    apply(p["id"], p["digest"])
    barrier = threading.Barrier(2)

    def run():
        barrier.wait()
        return undo(p["id"], p["digest"])

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    assert len(inspect(p["id"])["events"]) == 2


def test_database_unavailable_cli_is_nonzero_and_redacts_password(db, raw, mapping):
    env = {
        **os.environ,
        "PGHOST": "127.0.0.1",
        "PGPORT": "1",
        "PGPASSWORD": "redaction-test-password",
    }
    proc = subprocess.run(
        [sys.executable, "-m", "rehearsal.cli", "show", "00000000-0000-0000-0000-000000000000"],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )
    assert proc.returncode == 3 and "DATABASE_ERROR" in proc.stderr
    assert "redaction-test-password" not in proc.stderr + proc.stdout
