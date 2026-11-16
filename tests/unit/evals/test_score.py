import pytest

from evals.score import score, summarize
from rastro.domain.models import RootCauseReport, Verdict
from synthdata.generator import generate
from tests.fakes import InMemoryErp

DS = generate(seed=7)
ERP = InMemoryErp(DS)
FAULT = next(t for t in DS.truth if t.verdict is Verdict.factory_cause)
NOISE = next(t for t in DS.truth if t.verdict is Verdict.no_factory_cause)


def _fault_note_id():
    ev = ERP.get_equipment_history(FAULT.equnr, FAULT.window_start, FAULT.window_end)
    return next(e.record_id for e in ev if e.kind == "note")


def test_score_correct_factory_case():
    r = RootCauseReport(
        case_id=FAULT.case_id,
        verdict="factory_cause",
        equnr=FAULT.equnr,
        failure_mode=FAULT.failure_mode,
        evidence=[_fault_note_id()],
        confidence=0.8,
        summary="s",
    )
    s = score(r, FAULT, ERP, steps=4, tokens=100)
    assert (s.verdict_ok, s.equnr_ok, s.mode_ok, s.evidence_valid) == (True, True, True, True)


def test_score_wrong_equipment():
    other = "EX-02" if FAULT.equnr != "EX-02" else "PR-01"
    r = RootCauseReport(
        case_id=FAULT.case_id,
        verdict="factory_cause",
        equnr=other,
        failure_mode=FAULT.failure_mode,
        evidence=[_fault_note_id()],
        confidence=0.8,
        summary="s",
    )
    s = score(r, FAULT, ERP)
    assert s.verdict_ok and not s.equnr_ok


def test_score_noise_case_correct_when_no_factory_cause():
    r = RootCauseReport(
        case_id=NOISE.case_id,
        verdict="no_factory_cause",
        confidence=0.7,
        summary="s",
        evidence=[f"Case:{NOISE.case_id}"],
    )
    s = score(r, NOISE, ERP)
    assert s.verdict_ok and s.evidence_valid


def test_evidence_invalid_when_id_missing():
    r = RootCauseReport(
        case_id=FAULT.case_id,
        verdict="factory_cause",
        equnr=FAULT.equnr,
        failure_mode=FAULT.failure_mode,
        evidence=["QMEL:999999999"],
        confidence=0.8,
        summary="s",
    )
    assert not score(r, FAULT, ERP).evidence_valid


def test_summarize_rates():
    good = RootCauseReport(
        case_id=NOISE.case_id, verdict="no_factory_cause", confidence=0.7, summary="s"
    )
    bad = RootCauseReport(
        case_id=FAULT.case_id, verdict="no_factory_cause", confidence=0.7, summary="s"
    )
    m = summarize(
        [score(good, NOISE, ERP, steps=2, tokens=10), score(bad, FAULT, ERP, steps=4, tokens=30)],
        [NOISE, FAULT],
    )
    assert m["n"] == 2 and m["verdict_acc"] == 0.5
    assert m["noise_correct"] == 1.0 and m["equnr_acc"] == 0.0
    assert m["mean_steps"] == 3 and m["mean_tokens"] == 20
    assert m["mode_acc"] == pytest.approx(0.0)
