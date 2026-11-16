from datetime import timedelta

import pytest

from rootcause.domain.models import Verdict
from synthdata.generator import generate


@pytest.fixture(scope="module")
def ds():
    return generate(seed=7)


def _origin(ds, charg):
    afpo = next(r for r in ds.tables["AFPO"] if r["charg"] == charg)
    afko = next(r for r in ds.tables["AFKO"] if r["aufnr"] == afpo["aufnr"])
    equi = next(r for r in ds.tables["EQUI"] if r["arbpl"] == afko["arbpl"])
    return equi["equnr"], afko


def _delivery_of(ds, case):
    truth_case = next(c for c in ds.tables["crm_case"] if c["case_id"] == case.case_id)
    vbeln = ds.hidden_vbeln[case.case_id]
    assert truth_case["case_id"] == case.case_id
    return next(r for r in ds.tables["LIPS"] if r["vbeln"] == vbeln)


def test_same_seed_same_dataset():
    a, b = generate(seed=7), generate(seed=7)
    assert a.tables == b.tables and a.truth == b.truth
    assert generate(seed=8).tables != a.tables


def test_counts(ds):
    assert len(ds.truth) == 40
    assert sum(t.verdict is Verdict.factory_cause for t in ds.truth) == 30
    assert len(ds.tables["crm_case"]) == 40
    assert len(ds.tables["EQUI"]) == 6
    assert len(ds.tables["MARA"]) == 12
    assert len(ds.tables["KNA1"]) == 40


def test_every_fault_case_traces_to_equipment(ds):
    for t in ds.truth:
        if t.verdict is not Verdict.factory_cause:
            continue
        equnr, afko = _origin(ds, _delivery_of(ds, t)["charg"])
        assert equnr == t.equnr
        assert t.window_start <= afko["gstrp"].date() <= t.window_end


def test_noise_batches_outside_fault_windows(ds):
    windows = [(t.equnr, t.window_start, t.window_end) for t in ds.truth if t.equnr]
    for t in ds.truth:
        if t.verdict is Verdict.factory_cause:
            continue
        assert t.verdict is Verdict.no_factory_cause
        equnr, afko = _origin(ds, _delivery_of(ds, t)["charg"])
        day = afko["gstrp"].date()
        for e, s, end in windows:
            assert not (e == equnr and s - timedelta(days=3) <= day <= end + timedelta(days=3))


def test_routine_maintenance_on_all_equipment(ds):
    routine = {r["equnr"] for r in ds.tables["AUFK"] if r["auart"] == "PM02"}
    assert routine == {r["equnr"] for r in ds.tables["EQUI"]}


def test_some_cases_missing_or_wrong_vbeln(ds):
    lips = {r["vbeln"] for r in ds.tables["LIPS"]}
    bad = [c for c in ds.tables["crm_case"] if c["vbeln"] is None or c["vbeln"] not in lips]
    assert 6 <= len(bad) <= 12
    assert any(c["vbeln"] is None for c in bad)
    assert any(c["vbeln"] is not None for c in bad)
