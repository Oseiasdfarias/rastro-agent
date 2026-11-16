from datetime import date

from rastro.adapters import rows
from rastro.domain.models import BatchOrigin, Case, Delivery, MaintenanceEvent
from rastro.domain.records import parse_id
from synthdata.generator import Dataset


class InMemoryErp:
    def __init__(self, ds: Dataset):
        t = ds.tables
        likp = {r["vbeln"]: r for r in t["LIKP"]}
        self._lips = [
            r | {"kunnr": likp[r["vbeln"]]["kunnr"], "wadat_ist": likp[r["vbeln"]]["wadat_ist"]}
            for r in t["LIPS"]
        ]
        afko = {r["aufnr"]: r for r in t["AFKO"]}
        equi = {r["arbpl"]: r["equnr"] for r in t["EQUI"]}
        self._origin = {
            p["charg"]: afko[p["aufnr"]]
            | {"charg": p["charg"], "equnr": equi[afko[p["aufnr"]]["arbpl"]]}
            for p in t["AFPO"]
        }
        self._notes, self._orders = t["QMEL"], t["AUFK"]
        self._keys = {
            table: {tuple(r[c] for c in cols) for r in t[table if table != "Case" else "crm_case"]}
            for table, (_, cols) in rows.KEYS.items()
        }

    def get_delivery(self, vbeln: str) -> list[Delivery]:
        return [rows.delivery(r) for r in self._lips if r["vbeln"] == vbeln]

    def find_deliveries(self, kunnr, matnr, since: date, until: date) -> list[Delivery]:
        found = [
            r
            for r in self._lips
            if r["kunnr"] == kunnr
            and since <= r["wadat_ist"] <= until
            and (matnr is None or r["matnr"] == matnr)
        ]
        return [rows.delivery(r) for r in sorted(found, key=lambda r: (r["wadat_ist"], r["vbeln"]))]

    def get_batch_origin(self, charg: str) -> BatchOrigin | None:
        r = self._origin.get(charg)
        return rows.origin(r) if r else None

    def get_equipment_history(self, equnr, start: date, end: date) -> list[MaintenanceEvent]:
        ev = [
            rows.note(r) for r in self._notes if r["equnr"] == equnr and start <= r["qmdat"] <= end
        ]
        ev += [
            rows.order(r)
            for r in self._orders
            if r["equnr"] == equnr and start <= r["erdat"] <= end
        ]
        return sorted(ev, key=lambda e: (e.on, e.record_id))

    def record_exists(self, record_id: str) -> bool:
        try:
            table, keys = parse_id(record_id)
        except ValueError:
            return False
        return keys in self._keys.get(table, set())


class InMemoryCrm:
    def __init__(self, ds: Dataset):
        kunnr = {a["account_id"]: a["kunnr"] for a in ds.tables["crm_account"]}
        self._cases = {
            c["case_id"]: c | {"kunnr": kunnr[c["account_id"]]} for c in ds.tables["crm_case"]
        }

    def get_case(self, case_id: str) -> Case | None:
        r = self._cases.get(case_id)
        return rows.case(r) if r else None

    def list_case_ids(self) -> list[str]:
        return sorted(self._cases)


class StaticManuals:
    def __init__(self, passages=None):
        from rastro.domain.models import ManualPassage

        self._p = passages or [
            ManualPassage(
                record_id="MANUAL:200/0",
                page=200,
                score=0.9,
                text="Rolamentos: ruído e vibração indicam desgaste; substituir.",
            ),
        ]

    def search(self, query, k=4):
        return self._p[:k]


class ScriptedLlm:
    def __init__(self, responses):
        self.responses, self.calls = list(responses), []

    def chat(self, messages, tools=None, response_format=None):
        from rastro.application.ports import ChatResult

        self.calls.append(
            {"messages": messages, "tools": tools, "response_format": response_format}
        )
        r = self.responses.pop(0)
        return r if isinstance(r, ChatResult) else ChatResult(content=r, tokens=10, model="fake")
