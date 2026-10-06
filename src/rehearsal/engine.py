"""DB-backed reviewed plans and short, bounded, all-or-nothing target writes."""

import hashlib
import uuid
from collections import Counter

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from .input import ADAPTER, FIELDS, Rejected, digest, parse


def connect():
    # Standard libpq PG* environment; no connection string appears in reports.
    return psycopg.connect(
        "",
        row_factory=dict_row,
        connect_timeout=5,
        options="-c search_path=public -c statement_timeout=10000 -c lock_timeout=2000",
    )


def snapshot(conn, cid):
    # Same transaction/table locks or REPEATABLE READ protect this pair of reads.
    row = conn.execute("SELECT * FROM public.customer WHERE customer_id=%s", (cid,)).fetchone()
    rev = conn.execute(
        "SELECT revision FROM rehearsal.revisions WHERE customer_id=%s", (cid,)
    ).fetchone()
    return {"row": row, "revision": rev["revision"] if rev else 0}


def read_plan(conn, pid, lock=False):
    try:
        uuid.UUID(str(pid))
    except ValueError as exc:
        raise Rejected("PLAN_ID_FORMAT") from exc
    plan = conn.execute(
        "SELECT * FROM rehearsal.plans WHERE id=%s" + (" FOR UPDATE" if lock else ""), (pid,)
    ).fetchone()
    if not plan:
        raise Rejected("PLAN_NOT_FOUND")
    if digest(plan["payload"]) != plan["digest"]:
        raise Rejected("PLAN_INTEGRITY")
    return plan


def plan_import(raw, mapping):
    rows = parse(raw, mapping)
    with connect() as conn:
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        target = str(
            conn.execute("SELECT target_id FROM rehearsal.identity").fetchone()["target_id"]
        )
        entries = []
        reps = {r["employee_id"] for r in conn.execute("SELECT employee_id FROM public.employee")}
        for row in rows:
            if row["support_rep_id"] is not None and row["support_rep_id"] not in reps:
                raise Rejected(f"MISSING_SUPPORT_REP for customer {row['customer_id']}")
            before = snapshot(conn, row["customer_id"])
            if before["row"] is None:
                action = "INSERT"
            elif all(before["row"][f] == row[f] for f in FIELDS):
                action = "UNCHANGED"
            else:
                action = "UPDATE"
            entries.append({"action": action, "before": before, "after": row})
        payload = {
            "adapter": ADAPTER,
            "target_id": target,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "mapping": mapping,
            "entries": entries,
            "counts": dict(Counter(e["action"] for e in entries)),
        }
        pid, checksum = str(uuid.uuid4()), digest(payload)
        conn.execute(
            "INSERT INTO rehearsal.plans(id,digest,payload) VALUES(%s,%s,%s)",
            (pid, checksum, Jsonb(payload)),
        )
        return {"id": pid, "digest": checksum, "status": "PLANNED", "payload": payload}


def _lock_target(conn):
    # Coarse by design: one <=1000-row import, short maintenance transaction.
    # Conflicts with *all* normal writers, including writers unaware of this tool.
    conn.execute("LOCK TABLE public.customer, public.invoice IN SHARE ROW EXCLUSIVE MODE")


def _check(plan, expected, conn):
    if expected != plan["digest"]:
        raise Rejected("REVIEW_DIGEST_MISMATCH")
    target = str(conn.execute("SELECT target_id FROM rehearsal.identity").fetchone()["target_id"])
    if plan["payload"]["target_id"] != target or plan["payload"]["adapter"] != ADAPTER:
        raise Rejected("TARGET_OR_ADAPTER_MISMATCH")


def _write(conn, values, insert=False):
    # Column names are code constants, never CSV/user-supplied SQL.
    if insert:
        conn.execute(
            f"INSERT INTO public.customer ({','.join(FIELDS)}) VALUES ({','.join(['%s'] * len(FIELDS))})",
            [values[f] for f in FIELDS],
        )
    else:
        fields = FIELDS[1:]
        conn.execute(
            f"UPDATE public.customer SET {','.join(f + '=%s' for f in fields)} WHERE customer_id=%s",
            [values[f] for f in fields] + [values["customer_id"]],
        )


def apply(pid, expected, *, _after_write=None):
    with connect() as conn:
        plan = read_plan(conn, pid, lock=True)
        _check(plan, expected, conn)
        if plan["status"] == "UNDONE":
            raise Rejected("PLAN_ALREADY_UNDONE: create a fresh preview")
        if plan["status"] == "APPLIED":
            return {"id": str(pid), "status": "APPLIED", "replayed": True}
        _lock_target(conn)
        for entry in plan["payload"]["entries"]:
            if snapshot(conn, entry["after"]["customer_id"]) != entry["before"]:
                raise Rejected(
                    f"STALE_TARGET customer {entry['after']['customer_id']}: create a fresh preview"
                )
        receipt = []
        for entry in plan["payload"]["entries"]:
            if entry["action"] == "UNCHANGED":
                continue
            _write(conn, entry["after"], insert=entry["action"] == "INSERT")
            receipt.append(
                {
                    "customer_id": entry["after"]["customer_id"],
                    "applied": snapshot(conn, entry["after"]["customer_id"]),
                }
            )
            if _after_write:
                _after_write(conn, len(receipt))  # test seam; never exposed as CLI input
        conn.execute(
            "UPDATE rehearsal.plans SET status='APPLIED',receipt=%s WHERE id=%s",
            (Jsonb(receipt), pid),
        )
        conn.execute("INSERT INTO rehearsal.events(plan_id,action) VALUES(%s,'APPLY')", (pid,))
        return {"id": str(pid), "status": "APPLIED", "replayed": False}


def undo(pid, expected, *, _after_write=None):
    with connect() as conn:
        plan = read_plan(conn, pid, lock=True)
        _check(plan, expected, conn)
        if plan["status"] == "UNDONE":
            return {"id": str(pid), "status": "UNDONE", "replayed": True}
        if plan["status"] != "APPLIED":
            raise Rejected("NOT_APPLIED")
        _lock_target(conn)
        changed = {r["customer_id"]: r["applied"] for r in plan["receipt"]}
        entries = [e for e in plan["payload"]["entries"] if e["action"] != "UNCHANGED"]
        for entry in entries:
            cid = entry["after"]["customer_id"]
            if snapshot(conn, cid) != changed[cid]:
                raise Rejected(f"UNDO_CONFLICT customer {cid}: later write; nothing undone")
            if (
                entry["action"] == "INSERT"
                and conn.execute(
                    "SELECT 1 FROM public.invoice WHERE customer_id=%s LIMIT 1", (cid,)
                ).fetchone()
            ):
                raise Rejected(f"UNDO_REFERENCED customer {cid}: related invoice; nothing undone")
        for count, entry in enumerate(entries, 1):
            cid = entry["after"]["customer_id"]
            if entry["action"] == "INSERT":
                conn.execute("DELETE FROM public.customer WHERE customer_id=%s", (cid,))
            else:
                _write(conn, entry["before"]["row"])
            if _after_write:
                _after_write(conn, count)
        conn.execute("UPDATE rehearsal.plans SET status='UNDONE' WHERE id=%s", (pid,))
        conn.execute("INSERT INTO rehearsal.events(plan_id,action) VALUES(%s,'UNDO')", (pid,))
        return {"id": str(pid), "status": "UNDONE", "replayed": False}


def inspect(pid):
    with connect() as conn:
        plan = read_plan(conn, pid)
        plan["id"] = str(plan["id"])
        plan["created_at"] = plan["created_at"].isoformat()
        plan["events"] = [
            dict(r, at=r["at"].isoformat())
            for r in conn.execute(
                "SELECT action,at FROM rehearsal.events WHERE plan_id=%s ORDER BY id", (pid,)
            )
        ]
        return plan
