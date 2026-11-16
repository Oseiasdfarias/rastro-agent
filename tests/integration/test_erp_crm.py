from datetime import date

import pytest

from rootcause.domain.models import Verdict
from synthdata.generator import generate
from tests.fakes import InMemoryCrm, InMemoryErp

DS = generate(seed=7)


@pytest.fixture(
    params=["memory", pytest.param("postgres", marks=pytest.mark.integration)],
)
def ports(request):
    if request.param == "memory":
        return InMemoryErp(DS), InMemoryCrm(DS)
    from rootcause.adapters.crm.postgres import PostgresCrm
    from rootcause.adapters.db import connect
    from rootcause.adapters.erp.postgres import PostgresErp

    request.getfixturevalue("loaded_db")
    conn = connect(request.getfixturevalue("db_url"))
    request.addfinalizer(conn.close)
    return PostgresErp(conn), PostgresCrm(conn)


def test_get_delivery_unknown_returns_empty(ports):
    erp, _ = ports
    assert erp.get_delivery("99999999") == []


def test_find_deliveries_window(ports):
    erp, _ = ports
    kunnr = DS.tables["KNA1"][0]["kunnr"]
    found = erp.find_deliveries(kunnr, None, date(2026, 2, 1), date(2026, 2, 28))
    assert found
    assert all(
        d.kunnr == kunnr and date(2026, 2, 1) <= d.delivered_on <= date(2026, 2, 28) for d in found
    )
    matnr = found[0].matnr
    assert all(
        d.matnr == matnr
        for d in erp.find_deliveries(kunnr, matnr, date(2026, 2, 1), date(2026, 2, 28))
    )


def test_batch_origin_matches_truth(ports):
    erp, crm = ports
    faults = [t for t in DS.truth if t.verdict is Verdict.factory_cause][:3]
    for t in faults:
        [delivery] = erp.get_delivery(DS.hidden_vbeln[t.case_id])
        origin = erp.get_batch_origin(delivery.charg)
        assert origin.equnr == t.equnr
        assert t.window_start <= origin.start.date() <= t.window_end
    assert crm.get_case(faults[0].case_id).kunnr.startswith("00001")


def test_history_filters_by_date(ports):
    erp, _ = ports
    events = erp.get_equipment_history("PR-01", date(2026, 3, 1), date(2026, 3, 31))
    assert events
    assert all(e.equnr == "PR-01" and date(2026, 3, 1) <= e.on <= date(2026, 3, 31) for e in events)
    assert [e.on for e in events] == sorted(e.on for e in events)
    assert {e.kind for e in events} == {"note", "order"}


def test_record_exists_true_and_false(ports):
    erp, crm = ports
    events = erp.get_equipment_history("PR-02", date(2026, 1, 1), date(2026, 6, 30))
    assert all(erp.record_exists(e.record_id) for e in events)
    assert not erp.record_exists("QMEL:999999999")
    assert erp.record_exists("EQUI:PR-02")
    assert not erp.record_exists("garbage")
    assert len(crm.list_case_ids()) == 40
    assert crm.get_case("CS-99999") is None
