from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateInvestigation(BaseModel):
    case_id: str = Field(min_length=1, max_length=40)


class Review(BaseModel):
    decision: Literal["approve", "reject", "edit"]
    report: dict | None = None
    comment: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def _edit_needs_report(self) -> "Review":
        if self.decision == "edit" and not self.report:
            raise ValueError("decision 'edit' requires a report")
        return self


Status = Literal["pending_review", "approved", "rejected", "edited", "running"]


class Investigation(BaseModel):
    thread_id: str
    case_id: str
    status: Status
    report: dict | None
    steps: int
    tokens: int
