import pytest

pytestmark = pytest.mark.integration


def test_load_roundtrip(loaded_db, conn):
    assert conn.execute("SELECT count(*) FROM eval_truth").fetchone()[0] == 40
    assert conn.execute("SELECT count(*) FROM lips").fetchone()[0] == len(loaded_db.tables["LIPS"])
