import pytest

from rehearsal.input import MAX_BYTES, Rejected, parse


def test_valid(raw, mapping):
    assert [r["customer_id"] for r in parse(raw, mapping)] == [1, 2, 100]


@pytest.mark.parametrize(
    "old,new",
    [
        (b"Customer ID", b"Wrong ID"),
        (b"100,Mira", b"1,Mira"),
        (b"100,Mira", b"01,Mira"),
        (b"100,Mira", b"-1,Mira"),
        (b"100,Mira", b"2147483648,Mira"),
        (b"Mira,Fixture", b"Mira ," + b"Fixture"),
        (b"Mira,Fixture", b"Mira," + b"x" * 21),
        (b"mira@example.invalid", b"not an email"),
        (b"Mira,Fixture", b"Mira\x00,Fixture"),
        (b"Mira,Fixture", b",Fixture"),
        (b",Germany,1", b",Germany,1,extra"),
        (b",Germany,1", b",Germany"),
        (b",Germany,1", b",Germany,0"),
        (b"Mira,Fixture", b"\xff,Fixture"),
    ],
)
def test_bad_rows_rejected(raw, mapping, old, new):
    with pytest.raises(Rejected):
        parse(raw.replace(old, new), mapping)


def test_limits(raw, mapping):
    with pytest.raises(Rejected, match="INPUT_TOO_LARGE"):
        parse(b"x" * (MAX_BYTES + 1), mapping)
    header = raw.splitlines()[0]
    with pytest.raises(Rejected, match="ROW_LIMIT"):
        parse(
            header
            + b"\n"
            + b"\n".join(f"{i},A,B,a@example.invalid,,,".encode() for i in range(1, 1002)),
            mapping,
        )
    with pytest.raises(Rejected, match="EMPTY_INPUT"):
        parse(header + b"\n", mapping)


def test_mapping_is_exact(raw, mapping):
    mapping["sql"] = "DROP TABLE customer"
    with pytest.raises(Rejected, match="MAPPING_FIELDS"):
        parse(raw, mapping)


def test_nulls_unicode_bom_and_quoted_comma(raw, mapping):
    rows = parse(
        b"\xef\xbb\xbf"
        + raw.replace(b"New Demo", b'"Demo, Ltd"')
        .replace(b"Mira", "Míra".encode())
        .replace(b",Germany,1", b",Germany,"),
        mapping,
    )
    assert rows[-1]["company"] == "Demo, Ltd"
    assert rows[-1]["support_rep_id"] is None
