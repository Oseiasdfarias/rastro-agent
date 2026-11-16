import json

import pytest

from rastro.application.ports import ToolCall
from rastro.domain.models import Verdict
from rastro.tools.registry import ToolRegistry
from synthdata.generator import generate
from tests.fakes import InMemoryCrm, InMemoryErp, StaticManuals

DS = generate(seed=7)


@pytest.fixture
def reg():
    return ToolRegistry(InMemoryErp(DS), InMemoryCrm(DS), StaticManuals())


def call(name, **args):
    return ToolCall(id="1", name=name, arguments=json.dumps(args))


def test_schemas_cover_all_tools(reg):
    names = {s["function"]["name"] for s in reg.schemas()}
    assert names == {
        "get_case",
        "get_delivery",
        "find_deliveries",
        "get_batch_origin",
        "get_equipment_history",
        "search_manuals",
    }


def test_unknown_tool_returns_error(reg):
    r = reg.execute(call("drop_tables"))
    assert r.error and "unknown tool" in r.error


def test_invalid_json_returns_error(reg):
    r = reg.execute(ToolCall(id="1", name="get_case", arguments="{case_id: CS-1"))
    assert r.error and "JSON" in r.error


def test_wrong_type_returns_error_with_field_name(reg):
    r = reg.execute(call("get_equipment_history", equnr="PR-01", start="ontem", end="2026-03-01"))
    assert r.error and "start" in r.error


def test_history_window_over_60_days_rejected(reg):
    r = reg.execute(
        call("get_equipment_history", equnr="PR-01", start="2026-01-01", end="2026-04-01")
    )
    assert r.error and "60" in r.error


def test_result_lists_record_ids(reg):
    case_id = next(t.case_id for t in DS.truth if t.verdict is Verdict.factory_cause)
    r = reg.execute(call("get_delivery", vbeln=DS.hidden_vbeln[case_id]))
    assert r.error is None
    assert r.record_ids == [f"LIPS:{DS.hidden_vbeln[case_id]}/000010"]
    assert json.loads(r.content)[0]["charg"]


def test_empty_result_is_not_error(reg):
    r = reg.execute(call("get_delivery", vbeln="99999999"))
    assert r.error is None and r.record_ids == [] and "no delivery" in r.content
