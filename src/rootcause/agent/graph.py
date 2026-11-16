import json
from importlib.resources import files

from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from rootcause.adapters.tracing.steplog import log_step
from rootcause.agent.state import AgentState
from rootcause.application.finalize import finalize, parse_report, report_prompt, unreadable
from rootcause.application.ports import ErpPort, LlmPort, RunStats, ToolCall
from rootcause.domain.models import RootCauseReport
from rootcause.tools.registry import ToolRegistry

DECISIONS = {"approve", "reject", "edit"}


def _prompt(name: str) -> str:
    return files("rootcause.agent").joinpath(f"prompts/{name}").read_text()


def initial_state(case_id: str) -> AgentState:
    return {
        "case_id": case_id,
        "messages": [
            {"role": "system", "content": _prompt("system.md")},
            {"role": "user", "content": f"Investigate complaint {case_id}."},
        ],
        "seen_ids": [],
        "calls": [],
        "steps": 0,
        "tokens": 0,
        "report": None,
        "review": None,
    }


def _thread(config) -> str:
    return (config or {}).get("configurable", {}).get("thread_id", "-")


def build_graph(
    llm: LlmPort,
    tools: ToolRegistry,
    erp: ErpPort,
    checkpointer=None,
    max_steps: int = 8,
    review: bool = True,
):
    schemas = tools.schemas()

    def llm_node(state: AgentState, config) -> dict:
        r = llm.chat(state["messages"], tools=schemas)
        msg: dict = {"role": "assistant", "content": r.content or ""}
        if r.tool_calls:
            msg["tool_calls"] = [
                {
                    "id": c.id,
                    "type": "function",
                    "function": {"name": c.name, "arguments": c.arguments},
                }
                for c in r.tool_calls
            ]
        log_step(
            _thread(config),
            "llm",
            {"model": r.model, "tokens": r.tokens, "tool_calls": [c.name for c in r.tool_calls]},
        )
        return {
            "messages": [*state["messages"], msg],
            "steps": state["steps"] + 1,
            "tokens": state["tokens"] + r.tokens,
        }

    def after_llm(state: AgentState) -> str:
        last = state["messages"][-1]
        if last.get("tool_calls") and state["steps"] < max_steps:
            return "tools"
        return "finalize"

    def tools_node(state: AgentState, config) -> dict:
        messages, seen, calls = (
            list(state["messages"]),
            list(state["seen_ids"]),
            list(state["calls"]),
        )
        for tc in messages[-1]["tool_calls"]:
            call = ToolCall(
                id=tc["id"], name=tc["function"]["name"], arguments=tc["function"]["arguments"]
            )
            sig = f"{call.name}:{_canonical(call.arguments)}"
            if sig in calls:
                content = f"ERROR: repeated call {call.name}; use the earlier result"
            else:
                calls.append(sig)
                res = tools.execute(call)
                seen += [r for r in res.record_ids if r not in seen]
                content = f"ERROR: {res.error}" if res.error else res.content
            log_step(
                _thread(config),
                "tool",
                {"name": call.name, "args": call.arguments, "error": content.startswith("ERROR")},
            )
            messages.append({"role": "tool", "tool_call_id": call.id, "content": content})
        return {"messages": messages, "seen_ids": seen, "calls": calls}

    def finalize_node(state: AgentState, config) -> dict:
        ask = {"role": "user", "content": report_prompt() + "\nNow write the final report."}
        r = llm.chat([*state["messages"], ask], response_format=RootCauseReport)
        draft = parse_report(r.content, state["case_id"]) or unreadable(state["case_id"])
        report = finalize(draft, erp, set(state["seen_ids"]))
        log_step(_thread(config), "finalize", {"verdict": report.verdict, "tokens": r.tokens})
        return {"report": report.model_dump(mode="json"), "tokens": state["tokens"] + r.tokens}

    def review_node(state: AgentState) -> dict:
        decision = interrupt({"report": state["report"]})
        update: dict = {"review": decision}
        if decision.get("decision") == "edit" and decision.get("report"):
            edited = RootCauseReport.model_validate(
                decision["report"] | {"case_id": state["case_id"]}
            )
            update["report"] = edited.model_dump(mode="json")
        return update

    g = StateGraph(AgentState)
    g.add_node("llm", llm_node)
    g.add_node("tools", tools_node)
    g.add_node("finalize", finalize_node)
    g.add_edge(START, "llm")
    g.add_conditional_edges("llm", after_llm, ["tools", "finalize"])
    g.add_edge("tools", "llm")
    if review:
        g.add_node("review", review_node)
        g.add_edge("finalize", "review")
        g.add_edge("review", END)
    else:
        g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer)


def _canonical(arguments: str) -> str:
    try:
        return json.dumps(json.loads(arguments), sort_keys=True)
    except ValueError:
        return arguments


def run_agent(
    case_id: str, llm: LlmPort, tools: ToolRegistry, erp: ErpPort, max_steps: int = 8
) -> tuple[RootCauseReport, RunStats]:
    graph = build_graph(llm, tools, erp, max_steps=max_steps, review=False)
    out = graph.invoke(initial_state(case_id), {"recursion_limit": 4 * max_steps + 10})
    return RootCauseReport.model_validate(out["report"]), RunStats(out["steps"], out["tokens"])
