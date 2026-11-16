import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from langgraph.types import Command
from pydantic import ValidationError

from rootcause.agent.graph import build_graph, initial_state
from rootcause.api.schemas import CreateInvestigation, Investigation, Review
from rootcause.application.ports import LlmUnavailable

STATUS = {"approve": "approved", "reject": "rejected", "edit": "edited"}


def _default_deps():
    from rootcause.composition import build
    from rootcause.config import get_settings

    return build(get_settings())


def _postgres_saver(deps):
    from langgraph.checkpoint.postgres import PostgresSaver

    saver = PostgresSaver(deps.conn)
    saver.setup()
    return saver


def create_app(deps_factory: Callable = _default_deps, checkpointer=None) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        deps = deps_factory()
        saver = checkpointer or _postgres_saver(deps)
        state["deps"] = deps
        state["graph"] = build_graph(
            deps.llm, deps.tools, deps.erp, checkpointer=saver, max_steps=deps.max_steps
        )
        yield

    app = FastAPI(title="rootcause-agent", version="0.1.0", lifespan=lifespan)

    def _view(thread_id: str) -> Investigation:
        snap = state["graph"].get_state({"configurable": {"thread_id": thread_id}})
        v = snap.values
        if not v:
            raise HTTPException(404, f"investigation {thread_id} not found")
        if v.get("review"):
            status = STATUS[v["review"]["decision"]]
        elif "review" in snap.next:
            status = "pending_review"
        else:
            status = "running"
        return Investigation(
            thread_id=thread_id,
            case_id=v["case_id"],
            status=status,
            report=v.get("report"),
            steps=v.get("steps", 0),
            tokens=v.get("tokens", 0),
        )

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/investigations", status_code=201)
    def create(body: CreateInvestigation) -> Investigation:
        if state["deps"].crm.get_case(body.case_id) is None:
            raise HTTPException(404, f"case {body.case_id} not found")
        thread_id = uuid.uuid4().hex
        cfg = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}
        try:
            state["graph"].invoke(initial_state(body.case_id), cfg)
        except LlmUnavailable as e:
            raise HTTPException(503, f"LLM unavailable: {e}") from e
        return _view(thread_id)

    @app.get("/investigations/{thread_id}")
    def get(thread_id: str) -> Investigation:
        return _view(thread_id)

    @app.post("/investigations/{thread_id}/review")
    def review(thread_id: str, body: Review) -> Investigation:
        if _view(thread_id).status != "pending_review":
            raise HTTPException(409, "investigation is not waiting for review")
        cfg = {"configurable": {"thread_id": thread_id}}
        try:
            state["graph"].invoke(Command(resume=body.model_dump(exclude_none=True)), cfg)
        except ValidationError as e:
            raise HTTPException(422, f"edited report is invalid: {e.errors()[:3]}") from e
        return _view(thread_id)

    return app


app = create_app()
