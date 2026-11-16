from datetime import date

from pydantic import BaseModel, Field, model_validator

MAX_HISTORY_DAYS = 60


class GetCaseArgs(BaseModel):
    case_id: str = Field(description="CRM case id, e.g. CS-00012")


class GetDeliveryArgs(BaseModel):
    vbeln: str = Field(description="delivery number (LIKP/LIPS), 8 digits")


class FindDeliveriesArgs(BaseModel):
    kunnr: str = Field(description="customer number (KNA1)")
    matnr: str | None = Field(None, description="material number, optional")
    since: date
    until: date


class GetBatchOriginArgs(BaseModel):
    charg: str = Field(description="batch number from the delivery item")


class GetEquipmentHistoryArgs(BaseModel):
    equnr: str = Field(description="equipment id, e.g. PR-03")
    start: date
    end: date

    @model_validator(mode="after")
    def _window(self) -> "GetEquipmentHistoryArgs":
        if self.end < self.start:
            raise ValueError("end must be on or after start")
        if (self.end - self.start).days > MAX_HISTORY_DAYS:
            raise ValueError(f"window longer than {MAX_HISTORY_DAYS} days")
        return self


class SearchManualsArgs(BaseModel):
    query: str = Field(description="symptom or component to look up in the equipment manual")


DESCRIPTIONS = {
    "get_case": (GetCaseArgs, "Read a customer complaint from the CRM."),
    "get_delivery": (GetDeliveryArgs, "Read a delivery and its batch numbers."),
    "find_deliveries": (
        FindDeliveriesArgs,
        "Find a customer's deliveries in a date range (when the number is missing or wrong).",
    ),
    "get_batch_origin": (
        GetBatchOriginArgs,
        "Find the production order, work center and equipment that produced a batch.",
    ),
    "get_equipment_history": (
        GetEquipmentHistoryArgs,
        "List maintenance notes (QMEL) and orders (AUFK) of an equipment, max 60 days.",
    ),
    "search_manuals": (SearchManualsArgs, "Search the equipment maintenance manual."),
}
