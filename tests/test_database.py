import concurrent.futures
import json
import subprocess
import sys
import threading

import psycopg
import pytest

from rehearsal.engine import apply, connect, inspect, plan_import, undo
from rehearsal.input import Rejected
from rehearsal.report import render


def state():
    with connect() as c:
        return {
            "customers": c.execute("SELECT * FROM customer ORDER BY customer_id").fetchall(),
            "invoices": c.execute("SELECT * FROM invoice ORDER BY invoice_id").fetchall(),
            "events": c.execute(
                "SELECT plan_id,action FROM rehearsal.events ORDER BY id"
            ).fetchall(),
        }


def test_preview_is_target_read_only_and_counts(db, raw, mapping):
    before = state()
    p = plan_import(raw, mapping)
    assert p["payload"]["counts"] == {"UPDATE": 1, "UNCHANGED": 1, "INSERT": 1}
    assert state() == before
    assert inspect(p["id"])["status"] == "PLANNED"


def test_apply_replay_undo_preserves_invoice_and_unmapped_address(db, raw, mapping):
    before = state()
    p = plan_import(raw, mapping)
    assert apply(p["id"], p["digest"])["replayed"] is False
    after = state()
    assert after["customers"][0]["company"] == "North Demo"
    assert after["customers"][0]["address"] == "Synthetic address 1"
    assert after["invoices"] == before["invoices"]
    assert len(after["customers"]) == 3
    assert apply(p["id"], p["digest"])["replayed"] is True
    assert state() == after
    undo(p["id"], p["digest"])
    undone = state()
    assert undone["customers"] == before["customers"]
    assert undone["invoices"] == before["invoices"]
    assert undo(p["id"], p["digest"])["replayed"] is True
    assert state() == undone
    with pytest.raises(Rejected, match="ALREADY_UNDONE"):
        apply(p["id"], p["digest"])


def test_wrong_review_hash(db, raw, mapping):
    p = plan_import(raw, mapping)
    before = state()
    with pytest.raises(Rejected, match="DIGEST"):
        apply(p["id"], "0" * 64)
    assert state() == before


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE customer SET company='Human edit' WHERE customer_id=1",
        "UPDATE customer SET address='Other address' WHERE customer_id=1",
        "UPDATE customer SET company='X' WHERE customer_id=1; UPDATE customer SET company='Old Demo' WHERE customer_id=1",
        "INSERT INTO customer(customer_id,first_name,last_name,email) VALUES(100,'X','Y','x@example.invalid'); DELETE FROM customer WHERE customer_id=100",
        "DELETE FROM customer WHERE customer_id=2; INSERT INTO customer(customer_id,first_name,last_name,email,company,country,support_rep_id) VALUES(2,'Noah','Example','noah@example.invalid','Studio Demo','Poland',1)",
    ],
)
def test_stale_plan_and_aba_refuse_entire_batch(db, raw, mapping, change):
    p = plan_import(raw, mapping)
    with connect() as c:
        c.execute(change)
    before = state()
    with pytest.raises(Rejected, match="STALE_TARGET"):
        apply(p["id"], p["digest"])
    assert state() == before
    assert inspect(p["id"])["status"] == "PLANNED"


def test_other_customer_edit_does_not_invalidate_plan(db, raw, mapping):
    p = plan_import(raw, mapping)
    with connect() as c:
        c.execute(
            "INSERT INTO customer(customer_id,first_name,last_name,email) VALUES(999,'Unrelated','Fixture','other@example.invalid')"
        )
    apply(p["id"], p["digest"])
    assert len(state()["customers"]) == 4


@pytest.mark.parametrize(
    "change",
    [
        "UPDATE customer SET company='Human edit' WHERE customer_id=1",
        "UPDATE customer SET company='X' WHERE customer_id=1; UPDATE customer SET company='North Demo' WHERE customer_id=1",
        "DELETE FROM customer WHERE customer_id=100; INSERT INTO customer(customer_id,first_name,last_name,email,company,country,support_rep_id) VALUES(100,'Mira','Fixture','mira@example.invalid','New Demo','Germany',1)",
    ],
)
def test_undo_refuses_later_writes_including_aba(db, raw, mapping, change):
    p = plan_import(raw, mapping)
    apply(p["id"], p["digest"])
    with connect() as c:
        c.execute(change)
    before = state()
    with pytest.raises(Rejected, match="UNDO_CONFLICT"):
        undo(p["id"], p["digest"])
    assert state() == before
    assert inspect(p["id"])["status"] == "APPLIED"


def test_undo_refuses_new_invoice_without_partial_restore(db, raw, mapping):
    p = plan_import(raw, mapping)
    apply(p["id"], p["digest"])
    with connect() as c:
        c.execute(
            "INSERT INTO invoice(invoice_id,customer_id,invoice_date,total) VALUES(2,100,'2026-10-06',42.00)"
        )
    before = state()
    with pytest.raises(Rejected, match="UNDO_REFERENCED"):
        undo(p["id"], p["digest"])
    assert state() == before


def test_unchanged_rows_are_not_undone(db, raw, mapping):
    p = plan_import(raw, mapping)
    apply(p["id"], p["digest"])
    with connect() as c:
        c.execute("UPDATE customer SET company='Human edit' WHERE customer_id=2")
    undo(p["id"], p["digest"])
    assert state()["customers"][1]["company"] == "Human edit"


@pytest.mark.parametrize("action", ["apply", "undo"])
def test_exception_rolls_back_all_writes_and_ledger(db, raw, mapping, action):
    p = plan_import(raw, mapping)
    if action == "undo":
        apply(p["id"], p["digest"])
    before = state()

    def fail(c, n):
        raise RuntimeError("simulated failure after first target write")

    with pytest.raises(RuntimeError):
        (apply if action == "apply" else undo)(p["id"], p["digest"], _after_write=fail)
    assert state() == before
    assert inspect(p["id"])["status"] == ("PLANNED" if action == "apply" else "APPLIED")


@pytest.mark.parametrize("action", ["apply", "undo"])
def test_actual_process_death_rolls_back(db, raw, mapping, action):
    p = plan_import(raw, mapping)
    if action == "undo":
        apply(p["id"], p["digest"])
    before = state()
    code = f"import os; from rehearsal.engine import {action}; {action}({p['id']!r},{p['digest']!r},_after_write=lambda c,n:os._exit(71))"
    proc = subprocess.run([sys.executable, "-c", code], timeout=15, check=False)
    assert proc.returncode == 71
    # This obtains table locks, also waiting for the dead backend's transaction cleanup.
    with connect() as c:
        c.execute("LOCK TABLE customer IN SHARE ROW EXCLUSIVE MODE")
    assert state() == before
    (apply if action == "apply" else undo)(p["id"], p["digest"])


def test_two_simultaneous_applies_one_commit_one_replay(db, raw, mapping):
    p = plan_import(raw, mapping)
    barrier = threading.Barrier(2)

    def run():
        barrier.wait()
        return apply(p["id"], p["digest"])

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sorted(r["replayed"] for r in results) == [False, True]
    assert len(state()["events"]) == 1
    assert len(state()["customers"]) == 3


def test_overlapping_plans_one_refused(db, raw, mapping):
    a = plan_import(raw, mapping)
    b = plan_import(raw, mapping)
    barrier = threading.Barrier(2)

    def run(p):
        barrier.wait()
        try:
            return apply(p["id"], p["digest"])["status"]
        except Rejected:
            return "STALE"

    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        results = list(pool.map(run, [a, b]))
    assert sorted(results) == ["APPLIED", "STALE"]


def test_lock_timeout_is_bounded_and_retryable(db, raw, mapping):
    p = plan_import(raw, mapping)
    before = state()
    with connect() as c:
        c.execute("LOCK TABLE customer IN ROW EXCLUSIVE MODE")
        with pytest.raises(psycopg.errors.LockNotAvailable):
            apply(p["id"], p["digest"])
    assert state() == before
    apply(p["id"], p["digest"])


def test_fk_loss_after_preview_causes_transaction_rollback(db, raw, mapping):
    with connect() as c:
        c.execute(
            "INSERT INTO employee(employee_id,first_name,last_name) VALUES(50,'Demo','Support')"
        )
    p = plan_import(raw.replace(b",Germany,1", b",Germany,50"), mapping)
    with connect() as c:
        c.execute("DELETE FROM employee WHERE employee_id=50")
    before = state()
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        apply(p["id"], p["digest"])
    assert state() == before


def test_missing_rep_prevents_plan(db, raw, mapping):
    with pytest.raises(Rejected, match="MISSING_SUPPORT_REP"):
        plan_import(raw.replace(b",Germany,1", b",Germany,500"), mapping)
    with connect() as c:
        assert c.execute("SELECT count(*) AS n FROM rehearsal.plans").fetchone()["n"] == 0


def test_db_plan_immutability(db, raw, mapping):
    p = plan_import(raw, mapping)
    with pytest.raises(psycopg.errors.RaiseException), connect() as c:
        c.execute("UPDATE rehearsal.plans SET digest='fake' WHERE id=%s", (p["id"],))
    with pytest.raises(psycopg.errors.RaiseException), connect() as c:
        c.execute("DELETE FROM rehearsal.plans WHERE id=%s", (p["id"],))


def test_journal_immutability(db, raw, mapping):
    p = plan_import(raw, mapping)
    apply(p["id"], p["digest"])
    with pytest.raises(psycopg.errors.RaiseException), connect() as c:
        c.execute("DELETE FROM rehearsal.events")


def test_primary_key_rewrite_rejected(db):
    with pytest.raises(psycopg.errors.RaiseException), connect() as c:
        c.execute("UPDATE customer SET customer_id=200 WHERE customer_id=2")


def test_html_escaped_no_remote_assets(db, raw, mapping):
    p = plan_import(raw.replace(b"New Demo", b"<script>alert(1)</script>"), mapping)
    html = render([p])
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'src="http' not in html and 'href="http' not in html


def test_setup_refuses_existing_database(db):
    from setup_demo import setup

    before = state()
    with pytest.raises(RuntimeError, match="not empty"):
        setup()
    assert state() == before


def test_cli_error_and_show(db, raw, mapping):
    p = plan_import(raw, mapping)
    proc = subprocess.run(
        [sys.executable, "-m", "rehearsal.cli", "apply", p["id"], "--expect", "wrong"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 2 and json.loads(proc.stderr)["outcome"] == "REFUSED"
    proc = subprocess.run(
        [sys.executable, "-m", "rehearsal.cli", "show", p["id"]],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0 and json.loads(proc.stdout)["status"] == "PLANNED"


def test_noop_import_and_not_applied_undo(db, raw, mapping):
    p = plan_import(raw, mapping)
    with pytest.raises(Rejected, match="NOT_APPLIED"):
        undo(p["id"], p["digest"])
    apply(p["id"], p["digest"])
    q = plan_import(raw, mapping)
    assert q["payload"]["counts"] == {"UNCHANGED": 3}
    apply(q["id"], q["digest"])
    undo(q["id"], q["digest"])
    assert len(state()["customers"]) == 3
