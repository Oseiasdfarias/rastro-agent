import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from langgraph.checkpoint.memory import MemorySaver

from rastro.api.app import create_app
from rastro.application.ports import LlmUnavailable
from rastro.tools.registry import ToolRegistry
from synthdata.generator import generate
from tests.fakes import InMemoryCrm, InMemoryErp, ScriptedLlm, StaticManuals

DS = generate(seed=7)
CASE = DS.truth[0].case_id
REPORT = json.dumps({"verdict": "no_factory_cause", "confidence": 0.7, "summary": "ok"})


def _client(llm):
    erp, crm = InMemoryErp(DS), InMemoryCrm(DS)
    deps = SimpleNamespace(
        crm=crm, erp=erp, llm=llm, max_steps=8, tools=ToolRegistry(erp, crm, StaticManuals())
    )
    return TestClient(create_app(lambda: deps, checkpointer=MemorySaver())).__enter__()


class DownLlm:
    def chat(self, *a, **k):
        raise LlmUnavailable("ollama down")


def test_health():
    assert _client(ScriptedLlm([])).get("/health").json() == {"status": "ok"}


def test_create_returns_pending_review():
    c = _client(ScriptedLlm(["done", REPORT]))
    r = c.post("/investigations", json={"case_id": CASE})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "pending_review" and body["report"]["verdict"] == "no_factory_cause"
    assert c.get(f"/investigations/{body['thread_id']}").json()["status"] == "pending_review"


def test_review_approve_then_twice_409():
    c = _client(ScriptedLlm(["done", REPORT]))
    tid = c.post("/investigations", json={"case_id": CASE}).json()["thread_id"]
    r = c.post(f"/investigations/{tid}/review", json={"decision": "approve"})
    assert r.status_code == 200 and r.json()["status"] == "approved"
    assert c.post(f"/investigations/{tid}/review", json={"decision": "reject"}).status_code == 409
    assert c.get(f"/investigations/{tid}").json()["status"] == "approved"


def test_unknown_case_404():
    assert (
        _client(ScriptedLlm([])).post("/investigations", json={"case_id": "CS-99999"}).status_code
        == 404
    )


def test_unknown_thread_404():
    c = _client(ScriptedLlm([]))
    assert c.get("/investigations/nope").status_code == 404
    assert c.post("/investigations/nope/review", json={"decision": "approve"}).status_code == 404


@pytest.mark.parametrize("decision", ["maybe", ""])
def test_invalid_decision_422(decision):
    c = _client(ScriptedLlm(["done", REPORT]))
    tid = c.post("/investigations", json={"case_id": CASE}).json()["thread_id"]
    assert c.post(f"/investigations/{tid}/review", json={"decision": decision}).status_code == 422


def test_llm_unavailable_503():
    r = _client(DownLlm()).post("/investigations", json={"case_id": CASE})
    assert r.status_code == 503 and "unavailable" in r.json()["detail"]
