import json
from dataclasses import dataclass, field

from pydantic import ValidationError

from rastro.application.ports import CrmPort, ErpPort, ManualsPort, ToolCall
from rastro.domain.records import make_id
from rastro.tools import specs


@dataclass(frozen=True)
class ToolResult:
    content: str
    record_ids: list[str] = field(default_factory=list)
    error: str | None = None


def _dump(items: list[dict]) -> str:
    return json.dumps(items, ensure_ascii=False, separators=(",", ":"), default=str)


class ToolRegistry:
    def __init__(self, erp: ErpPort, crm: CrmPort, manuals: ManualsPort):
        self.erp, self.crm, self.manuals = erp, crm, manuals

    def schemas(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc,
                    "parameters": model.model_json_schema(),
                },
            }
            for name, (model, desc) in specs.DESCRIPTIONS.items()
        ]

    def execute(self, call: ToolCall) -> ToolResult:
        if call.name not in specs.DESCRIPTIONS:
            return ToolResult("", error=f"unknown tool '{call.name}'")
        model, _ = specs.DESCRIPTIONS[call.name]
        try:
            raw = json.loads(call.arguments or "{}")
        except ValueError:
            return ToolResult("", error="arguments are not valid JSON")
        try:
            args = model.model_validate(raw)
        except ValidationError as e:
            fields = "; ".join(
                f"{'.'.join(map(str, x['loc'])) or 'args'}: {x['msg']}" for x in e.errors()
            )
            return ToolResult("", error=f"invalid arguments: {fields}")
        return getattr(self, f"_{call.name}")(args)

    def _get_case(self, a: specs.GetCaseArgs) -> ToolResult:
        case = self.crm.get_case(a.case_id)
        if not case:
            return ToolResult(f"no case {a.case_id}")
        rid = make_id("Case", case.case_id)
        return ToolResult(_dump([{"record_id": rid, **case.model_dump(mode="json")}]), [rid])

    def _deliveries(self, found, empty: str) -> ToolResult:
        items = [
            {"record_id": make_id("LIPS", d.vbeln, d.posnr), **d.model_dump(mode="json")}
            for d in found
        ]
        return ToolResult(_dump(items) if items else empty, [i["record_id"] for i in items])

    def _get_delivery(self, a: specs.GetDeliveryArgs) -> ToolResult:
        return self._deliveries(self.erp.get_delivery(a.vbeln), f"no delivery {a.vbeln}")

    def _find_deliveries(self, a: specs.FindDeliveriesArgs) -> ToolResult:
        return self._deliveries(
            self.erp.find_deliveries(a.kunnr, a.matnr, a.since, a.until),
            "no delivery in that range",
        )

    def _get_batch_origin(self, a: specs.GetBatchOriginArgs) -> ToolResult:
        o = self.erp.get_batch_origin(a.charg)
        if not o:
            return ToolResult(f"no production order for batch {a.charg}")
        ids = [make_id("AFKO", o.aufnr), make_id("EQUI", o.equnr)]
        return ToolResult(_dump([{"record_ids": ids, **o.model_dump(mode="json")}]), ids)

    def _get_equipment_history(self, a: specs.GetEquipmentHistoryArgs) -> ToolResult:
        ev = self.erp.get_equipment_history(a.equnr, a.start, a.end)
        return ToolResult(
            _dump([e.model_dump(mode="json") for e in ev])
            if ev
            else f"no maintenance records for {a.equnr} in that window",
            [e.record_id for e in ev],
        )

    def _search_manuals(self, a: specs.SearchManualsArgs) -> ToolResult:
        hits = self.manuals.search(a.query)
        items = [{"record_id": h.record_id, "page": h.page, "text": h.text} for h in hits]
        return ToolResult(_dump(items) if items else "nothing found", [h.record_id for h in hits])
