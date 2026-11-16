import json

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from rastro.agent.graph import build_graph, initial_state, run_agent
from rastro.application.ports import ChatResult, ToolCall
from rastro.domain.models import Verdict
from rastro.tools.registry import ToolRegistry
from synthdata.generator import generate
from tests.fakes import InMemoryCrm, InMemoryErp, ScriptedLlm, StaticManuals

DS = generate(seed=7)
ERP = InMemoryErp(DS)
TOOLS = ToolRegistry(ERP, InMemoryCrm(DS), StaticManuals())
CASE = DS.truth[0].case_id
REPORT = json.dumps(
    {
        "verdict": "no_factory_cause",
        "confidence": 0.7,
        "summary": "ok",
        "evidence": [f"Case:{CASE}"],
    }
)


def tool(name, **args):
    return ChatResult(
        content=None,
        tokens=5,
        tool_calls=[ToolCall(id=name, name=name, arguments=json.dumps(args))],
    )


def tool_messages(llm):
    return [m for m in llm.calls[-1]["messages"] if m["role"] == "tool"]


def test_agent_follows_tool_calls_and_finalizes():
    llm = ScriptedLlm([tool("get_case", case_id=CASE), ChatResult(content="done"), REPORT])
    report, stats = run_agent(CASE, llm, TOOLS, ERP, max_steps=8)
    assert report.verdict is Verdict.no_factory_cause
    assert report.evidence == [f"Case:{CASE}"]
    assert stats.steps == 2 and stats.tokens == 5 + 0 + 10
    assert CASE in tool_messages(llm)[0]["content"]
    assert llm.calls[-1]["response_format"] is not None


def test_agent_stops_at_max_steps():
    llm = ScriptedLlm([tool("get_case", case_id="CS-1"), tool("get_case", case_id="CS-2"), REPORT])
    report, stats = run_agent(CASE, llm, TOOLS, ERP, max_steps=2)
    assert stats.steps == 2 and len(llm.calls) == 3
    assert report.case_id == CASE


def test_repeated_call_not_executed():
    llm = ScriptedLlm(
        [
            tool("get_case", case_id=CASE),
            tool("get_case", case_id=CASE),
            ChatResult(content="done"),
            REPORT,
        ]
    )
    run_agent(CASE, llm, TOOLS, ERP, max_steps=8)
    msgs = tool_messages(llm)
    assert len(msgs) == 2 and "repeated call" in msgs[1]["content"]


def test_invalid_tool_args_do_not_crash():
    bad = ChatResult(content=None, tool_calls=[ToolCall(id="x", name="get_case", arguments="{")])
    llm = ScriptedLlm([bad, ChatResult(content="done"), REPORT])
    report, _ = run_agent(CASE, llm, TOOLS, ERP, max_steps=8)
    assert "ERROR" in tool_messages(llm)[0]["content"]
    assert report.verdict is Verdict.no_factory_cause


def test_interrupt_then_approve_sets_review():
    llm = ScriptedLlm([ChatResult(content="done"), REPORT])
    graph = build_graph(llm, TOOLS, ERP, checkpointer=MemorySaver(), max_steps=8)
    cfg = {"configurable": {"thread_id": "t1"}}
    out = graph.invoke(initial_state(CASE), cfg)
    assert out["__interrupt__"][0].value["report"]["verdict"] == "no_factory_cause"
    final = graph.invoke(Command(resume={"decision": "approve"}), cfg)
    assert final["review"] == {"decision": "approve"}
