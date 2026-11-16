import pytest

from rootcause.domain.records import make_id, parse_id


def test_make_and_parse_id_roundtrip():
    rid = make_id("LIPS", "80001234", "000010")
    assert rid == "LIPS:80001234/000010"
    assert parse_id(rid) == ("LIPS", ("80001234", "000010"))


def test_parse_id_rejects_unknown_table():
    with pytest.raises(ValueError):
        parse_id("VBRK:1")
    with pytest.raises(ValueError):
        make_id("VBRK", "1")
