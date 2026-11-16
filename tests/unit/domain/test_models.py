import pytest
from pydantic import ValidationError

from rastro.domain.models import FailureMode, RootCauseReport, Verdict


def _report(**kw):
    base = dict(
        case_id="C-1",
        verdict=Verdict.no_factory_cause,
        equnr=None,
        failure_mode=None,
        window_start=None,
        window_end=None,
        evidence=[],
        confidence=0.5,
        summary="s",
        open_questions=[],
    )
    return RootCauseReport(**(base | kw))


def test_report_rejects_confidence_above_1():
    with pytest.raises(ValidationError):
        _report(confidence=1.2)


def test_factory_cause_requires_equnr_and_mode():
    with pytest.raises(ValidationError):
        _report(verdict=Verdict.factory_cause, failure_mode=FailureMode.bearing_wear)
    with pytest.raises(ValidationError):
        _report(verdict=Verdict.factory_cause, equnr="PR-03")
    ok = _report(verdict=Verdict.factory_cause, equnr="PR-03", failure_mode="bearing_wear")
    assert ok.failure_mode is FailureMode.bearing_wear
