"""Capture actual database outcomes into a portable review, never fabricate PASS."""

import json
from pathlib import Path

from rehearsal.engine import apply, connect, inspect, plan_import, undo
from rehearsal.input import Rejected
from rehearsal.report import render

ROOT = Path(__file__).resolve().parents[1]


def main():
    raw = (ROOT / "fixtures/customers.csv").read_bytes()
    mapping = json.loads((ROOT / "fixtures/mapping.json").read_text())
    steps = []

    def capture(p, label, note):
        result = inspect(p["id"])
        with connect() as c:
            result["database"] = {
                "customers": c.execute(
                    "SELECT customer_id,company FROM customer ORDER BY customer_id"
                ).fetchall(),
                "invoices": [
                    {**r, "total": str(r["total"])}
                    for r in c.execute(
                        "SELECT invoice_id,customer_id,total FROM invoice ORDER BY invoice_id"
                    )
                ],
            }
        result.update(label=label, note=note)
        steps.append(result)

    p = plan_import(raw, mapping)
    capture(
        p,
        "1 · Preview",
        "No customer or invoice writes. One update, one insert, one unchanged row.",
    )
    apply(p["id"], p["digest"])
    capture(
        p,
        "2 · Apply",
        "Committed together: customers, receipt and one APPLY event. Invoice 1 still points to customer 1.",
    )
    assert apply(p["id"], p["digest"])["replayed"]
    capture(
        p,
        "3 · Retry",
        "Retry returned the existing outcome. Still three customers and one APPLY event.",
    )
    undo(p["id"], p["digest"])
    capture(
        p, "4 · Undo", "Original company restored; imported customer removed; invoice preserved."
    )
    q = plan_import(raw, mapping)
    with connect() as c:
        c.execute("UPDATE customer SET company='Human correction' WHERE customer_id=1")
    try:
        apply(q["id"], q["digest"])
    except Rejected as exc:
        assert "STALE_TARGET" in str(exc)
        capture(
            q,
            "5 · Stale plan",
            "REFUSED: a human changed the target after preview. No partial import; their correction survives.",
        )
    else:
        raise AssertionError("Expected stale-plan refusal")
    r = plan_import(raw, mapping)
    apply(r["id"], r["digest"])
    with connect() as c:
        c.execute(
            "INSERT INTO invoice(invoice_id,customer_id,invoice_date,total) VALUES(2,100,'2026-10-06',42.00)"
        )
    try:
        undo(r["id"], r["digest"])
    except Rejected as exc:
        assert "UNDO_REFERENCED" in str(exc)
        capture(
            r,
            "6 · Protected undo",
            "REFUSED: the new customer now has an invoice. No rows undone; later business history is preserved.",
        )
    else:
        raise AssertionError("Expected referenced-customer refusal")
    out = ROOT / "evidence"
    out.mkdir(exist_ok=True)
    (out / "demo.json").write_text(json.dumps(steps, indent=2), encoding="utf-8")
    (out / "review.html").write_text(render(steps), encoding="utf-8")
    print("Six real PostgreSQL outcomes captured in evidence/review.html and demo.json")


if __name__ == "__main__":
    main()
