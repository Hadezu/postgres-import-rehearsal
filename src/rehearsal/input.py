"""Deliberately bounded, explicit mapping. No guessed identity or silent row loss."""

import csv
import hashlib
import io
import json
import re

FIELDS = ("customer_id", "first_name", "last_name", "email", "company", "country", "support_rep_id")
LIMITS = {"first_name": 40, "last_name": 20, "email": 60, "company": 80, "country": 40}
MAX_ROWS = 1000
MAX_BYTES = 1_048_576
ADAPTER = "chinook-customer-v1"


class Rejected(Exception):
    """An expected, recoverable refusal; the target transaction is not committed."""


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
    ).hexdigest()


def parse(raw: bytes, mapping: dict):
    if len(raw) > MAX_BYTES:
        raise Rejected("INPUT_TOO_LARGE: maximum 1 MiB")
    if not isinstance(mapping, dict) or set(mapping) != set(FIELDS):
        raise Rejected("MAPPING_FIELDS: map exactly the seven documented target fields")
    if any(not isinstance(v, str) or not v for v in mapping.values()) or len(
        set(mapping.values())
    ) != len(FIELDS):
        raise Rejected("MAPPING_HEADERS: use distinct nonempty source headers")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True)
        headers = reader.fieldnames
        if (
            not headers
            or len(headers) != len(set(headers))
            or set(headers) != set(mapping.values())
        ):
            raise Rejected(
                "CSV_HEADERS: missing, extra or duplicate headers; no silently ignored fields"
            )
        rows, seen = [], set()
        for number, row in enumerate(reader, 2):
            if len(rows) >= MAX_ROWS:
                raise Rejected("ROW_LIMIT: maximum 1000 customers per transaction")
            if None in row or any(v is None for v in row.values()):
                raise Rejected(f"CSV_SHAPE at record {number}")
            item = {field: row[header] for field, header in mapping.items()}
            for key in ("customer_id", "support_rep_id"):
                value = item[key]
                if key == "support_rep_id" and value == "":
                    item[key] = None
                elif not re.fullmatch(r"[1-9][0-9]{0,9}", value) or int(value) > 2147483647:
                    raise Rejected(f"INTEGER_FORMAT {key} at record {number}")
                else:
                    item[key] = int(value)
            if item["customer_id"] in seen:
                raise Rejected(f"DUPLICATE_ID at record {number}")
            seen.add(item["customer_id"])
            for key, limit in LIMITS.items():
                value = item[key]
                if len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value):
                    raise Rejected(f"TEXT_FORMAT {key} at record {number}")
                if key in ("company", "country") and value == "":
                    item[key] = None
                elif not value.strip() or value != value.strip():
                    raise Rejected(f"TEXT_WHITESPACE {key} at record {number}")
            if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", item["email"]):
                raise Rejected(f"EMAIL_FORMAT at record {number}")
            rows.append(item)
        if not rows:
            raise Rejected("EMPTY_INPUT")
        return sorted(rows, key=lambda r: r["customer_id"])
    except (UnicodeError, csv.Error) as exc:
        raise Rejected("CSV_ENCODING_OR_SYNTAX") from exc
