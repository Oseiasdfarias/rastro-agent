import json

import pytest

from rastro.application.fixed import investigate_fixed
from rastro.application.ports import CaseNotFound
from rastro.domain.models import Case, Verdict
from synthdata.generator import generate
from tests.fakes import InMemoryCrm, InMemoryErp, ScriptedLlm, StaticManuals

DS = generate(seed=7)
ERP, CRM = InMemoryErp(DS), InMemoryCrm(DS)
NOISE = json.dumps(
    {"verdict": "no_factory_cause", "confidence": 0.6, "summary": "ok", "evidence": []}
)


def _missing_vbeln_case():
    return next(c for c in DS.tables["crm_case"] if c["vbeln"] is None)["case_id"]


def test_fixed_finds_delivery_when_vbeln_missing():
    case_id = _missing_vbeln_case()
    llm = ScriptedLlm([NOISE])
    investigate_fixed(case_id, CRM, ERP, StaticManuals(), llm)
    prompt = llm.calls[0]["messages"][-1]["content"]
    assert DS.hidden_vbeln[case_id] in prompt


def test_fixed_returns_insufficient_data_when_no_delivery():
    class LonelyCrm:
        def get_case(self, case_id):
            return Case(
                case_id=case_id,
                account_id="ACC-X",
                kunnr="0000999999",
                created_on="2026-05-01",
                matnr="MAT-1001",
                vbeln=None,
                text="x",
            )

    llm = ScriptedLlm([])
    report, stats = investigate_fixed("CS-X", LonelyCrm(), ERP, StaticManuals(), llm)
    assert report.verdict is Verdict.insufficient_data
    assert llm.calls == [] and stats.tokens == 0


def test_fixed_passes_history_to_llm():
    t = next(t for t in DS.truth if t.verdict is Verdict.factory_cause)
    llm = ScriptedLlm([NOISE])
    _, stats = investigate_fixed(t.case_id, CRM, ERP, StaticManuals(), llm)
    prompt = llm.calls[0]["messages"][-1]["content"]
    assert t.equnr in prompt and "QMEL:" in prompt and "MANUAL:200/0" in prompt
    assert llm.calls[0]["response_format"] is not None
    assert stats.tokens == 10


def test_fixed_unknown_case_raises():
    with pytest.raises(CaseNotFound):
        investigate_fixed("CS-99999", CRM, ERP, StaticManuals(), ScriptedLlm([]))
