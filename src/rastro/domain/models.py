from datetime import date, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FailureMode(StrEnum):
    bearing_wear = "bearing_wear"
    heater_drift = "heater_drift"
    mold_wear = "mold_wear"
    misalignment = "misalignment"
    sensor_fault = "sensor_fault"


class Verdict(StrEnum):
    factory_cause = "factory_cause"
    no_factory_cause = "no_factory_cause"
    insufficient_data = "insufficient_data"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class Case(_Frozen):
    case_id: str
    account_id: str
    kunnr: str
    created_on: date
    matnr: str | None
    vbeln: str | None
    text: str


class Delivery(_Frozen):
    vbeln: str
    posnr: str
    matnr: str
    charg: str
    kunnr: str
    delivered_on: date


class BatchOrigin(_Frozen):
    charg: str
    aufnr: str
    arbpl: str
    equnr: str
    start: datetime
    end: datetime


class MaintenanceEvent(_Frozen):
    record_id: str
    equnr: str
    on: date
    kind: Literal["note", "order"]
    text: str


class ManualPassage(_Frozen):
    record_id: str
    page: int
    text: str
    score: float


class RootCauseReport(_Frozen):
    case_id: str
    verdict: Verdict
    equnr: str | None = None
    failure_mode: FailureMode | None = None
    window_start: date | None = None
    window_end: date | None = None
    evidence: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    summary: str
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _factory_cause_needs_target(self) -> "RootCauseReport":
        if self.verdict is Verdict.factory_cause and (not self.equnr or not self.failure_mode):
            raise ValueError("factory_cause requires equnr and failure_mode")
        return self
