import json
from datetime import timedelta

from rootcause.application.finalize import finalize, parse_report, report_prompt, unreadable
from rootcause.application.ports import (
    CaseNotFound,
    CrmPort,
    ErpPort,
    LlmPort,
    ManualsPort,
    RunStats,
)
from rootcause.domain.models import RootCauseReport, Verdict
from rootcause.domain.records import make_id

LOOKBACK = timedelta(days=90)
MARGIN = timedelta(days=14)


def _j(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def investigate_fixed(
    case_id: str, crm: CrmPort, erp: ErpPort, manuals: ManualsPort, llm: LlmPort
) -> tuple[RootCauseReport, RunStats]:
    case = crm.get_case(case_id)
    if case is None:
        raise CaseNotFound(case_id)
    steps, seen = 1, {make_id("Case", case_id)}
    deliveries = erp.get_delivery(case.vbeln) if case.vbeln else []
    steps += bool(case.vbeln)
    if not deliveries:
        deliveries = erp.find_deliveries(
            case.kunnr, case.matnr, case.created_on - LOOKBACK, case.created_on
        )
        steps += 1
    if not deliveries:
        return RootCauseReport(
            case_id=case_id,
            verdict=Verdict.insufficient_data,
            confidence=0.9,
            summary="No delivery found for this customer and material in the last 90 days.",
            open_questions=["ask the customer for the delivery number"],
        ), RunStats(steps, 0)

    sections, notes = [], []
    for d in deliveries:
        seen.add(make_id("LIPS", d.vbeln, d.posnr))
        origin = erp.get_batch_origin(d.charg)
        steps += 1
        if origin is None:
            sections.append(f"Delivery {_j(d.model_dump())}: batch origin not found")
            continue
        seen |= {make_id("AFKO", origin.aufnr), make_id("EQUI", origin.equnr)}
        history = erp.get_equipment_history(
            origin.equnr, origin.start.date() - MARGIN, origin.end.date() + MARGIN
        )
        steps += 1
        seen |= {e.record_id for e in history}
        notes += [e.text for e in history if e.kind == "note"]
        sections.append(
            f"Delivery LIPS:{d.vbeln}/{d.posnr} {_j(d.model_dump())}\n"
            f"Produced by AFKO:{origin.aufnr} on EQUI:{origin.equnr} {_j(origin.model_dump())}\n"
            f"Maintenance of {origin.equnr} from 14 days before to 14 days after production:\n"
            + "\n".join(f"- {e.record_id} {e.on} {e.kind}: {e.text}" for e in history)
        )
    passages = manuals.search("; ".join(notes[-4:]) or case.text)
    steps += 1
    seen |= {p.record_id for p in passages}
    user = (
        f"Complaint Case:{case.case_id} ({case.created_on}): {case.text}\n\n"
        + "\n\n".join(sections)
        + "\n\nManual passages:\n"
        + "\n".join(f"- {p.record_id} (page {p.page}): {p.text}" for p in passages)
    )
    result = llm.chat(
        [{"role": "system", "content": report_prompt()}, {"role": "user", "content": user}],
        response_format=RootCauseReport,
    )
    draft = parse_report(result.content, case_id) or unreadable(case_id)
    return finalize(draft, erp, seen), RunStats(steps + 1, result.tokens)
