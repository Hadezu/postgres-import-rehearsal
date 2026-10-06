import argparse
import json
import sys
from pathlib import Path

import psycopg

from . import engine
from .input import MAX_BYTES, Rejected
from .report import render


def main():
    parser = argparse.ArgumentParser(
        description="Chinook customer import: plan → review → apply → guarded undo"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("plan")
    p.add_argument("csv", type=Path)
    p.add_argument("--mapping", type=Path, required=True)
    for name in ("apply", "undo", "show", "report"):
        p = sub.add_parser(name)
        p.add_argument("id")
        if name in ("apply", "undo"):
            p.add_argument("--expect", required=True, help="Full digest from the plan you reviewed")
        if name == "report":
            p.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "plan":
            with args.csv.open("rb") as f:
                raw = f.read(MAX_BYTES + 1)
            mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
            result = engine.plan_import(raw, mapping)
        elif args.command in ("apply", "undo"):
            result = getattr(engine, args.command)(args.id, args.expect)
        else:
            result = engine.inspect(args.id)
            if args.command == "report":
                args.output.write_text(render([result]), encoding="utf-8")
                result = {"report": str(args.output), "status": result["status"]}
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Rejected as exc:
        print(json.dumps({"error": str(exc), "outcome": "REFUSED"}), file=sys.stderr)
        return 2
    except psycopg.Error as exc:
        # Do not expose connection strings, secrets or rejected row data.
        print(
            json.dumps(
                {
                    "error": "DATABASE_ERROR",
                    "sqlstate": exc.sqlstate,
                    "next_step": "Recheck connectivity/locks; use show before retrying an uncertain commit.",
                }
            ),
            file=sys.stderr,
        )
        return 3
    except (OSError, ValueError) as exc:
        print(
            json.dumps({"error": "INPUT_OR_OUTPUT_ERROR", "type": type(exc).__name__}),
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
