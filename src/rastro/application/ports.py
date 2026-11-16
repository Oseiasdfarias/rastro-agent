from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from pydantic import BaseModel

from rastro.domain.models import BatchOrigin, Case, Delivery, MaintenanceEvent, ManualPassage


class CrmPort(Protocol):
    def get_case(self, case_id: str) -> Case | None: ...
    def list_case_ids(self) -> list[str]: ...


class ErpPort(Protocol):
    def get_delivery(self, vbeln: str) -> list[Delivery]: ...
    def find_deliveries(
        self, kunnr: str, matnr: str | None, since: date, until: date
    ) -> list[Delivery]: ...
    def get_batch_origin(self, charg: str) -> BatchOrigin | None: ...
    def get_equipment_history(
        self, equnr: str, start: date, end: date
    ) -> list[MaintenanceEvent]: ...
    def record_exists(self, record_id: str) -> bool: ...


class ManualsPort(Protocol):
    def search(self, query: str, k: int = 4) -> list[ManualPassage]: ...


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: str


@dataclass(frozen=True)
class ChatResult:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens: int = 0
    model: str = ""


class LlmUnavailable(RuntimeError):
    pass


class LlmPort(Protocol):
    def chat(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        response_format: type[BaseModel] | None = None,
    ) -> ChatResult: ...


class CaseNotFound(LookupError):
    pass


@dataclass(frozen=True)
class RunStats:
    steps: int
    tokens: int
