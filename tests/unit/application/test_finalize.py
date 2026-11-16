from rootcause.application.finalize import finalize, parse_report
from rootcause.domain.models import RootCauseReport, Verdict
from synthdata.generator import generate
from tests.fakes import InMemoryErp

ERP = InMemoryErp(generate(seed=7))
REAL = "EQUI:PR-01"


def _draft(**kw):
    base = dict(
        case_id="CS-00001",
        verdict="factory_cause",
        equnr="PR-01",
        failure_mode="bearing_wear",
        evidence=[REAL, "QMEL:999999999"],
        confidence=0.8,
        summary="s",
    )
    return RootCauseReport(**(base | kw))


def test_finalize_drops_unknown_ids_and_lowers_confidence():
    r = finalize(_draft(), ERP, seen_ids={REAL, "QMEL:999999999"})
    assert r.evidence == [REAL]
    assert r.confidence == 0.4
    assert any("QMEL:999999999" in q for q in r.open_questions)


def test_finalize_drops_ids_not_seen():
    r = finalize(_draft(evidence=[REAL]), ERP, seen_ids=set())
    assert r.evidence == []


def test_finalize_keeps_seen_manual_ids():
    r = finalize(_draft(evidence=[REAL, "MANUAL:200/0"]), ERP, seen_ids={REAL, "MANUAL:200/0"})
    assert r.evidence == [REAL, "MANUAL:200/0"] and r.confidence == 0.8


def test_finalize_downgrades_factory_cause_without_evidence():
    r = finalize(_draft(evidence=["QMEL:999999999"]), ERP, seen_ids={"QMEL:999999999"})
    assert r.verdict is Verdict.insufficient_data


def test_parse_report_handles_garbage_and_fences():
    assert parse_report("not json", "CS-1") is None
    r = parse_report(
        '```json\n{"verdict": "no_factory_cause", "confidence": 0.7, "summary": "transporte"}\n```',
        "CS-1",
    )
    assert r.case_id == "CS-1" and r.verdict is Verdict.no_factory_cause
