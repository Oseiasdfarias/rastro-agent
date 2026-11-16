from typing import TypedDict


class AgentState(TypedDict, total=False):
    case_id: str
    messages: list[dict]
    seen_ids: list[str]
    calls: list[str]
    steps: int
    tokens: int
    report: dict | None
    review: dict | None
