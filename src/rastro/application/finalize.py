import json
from importlib.resources import files

from pydantic import ValidationError

from rastro.application.ports import ErpPort
from rastro.domain.models import RootCauseReport, Verdict


def report_prompt() -> str:
    return files("rastro.agent").joinpath("prompts/report.md").read_text()


def parse_report(content: str | None, case_id: str) -> RootCauseReport | None:
    text = (content or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```")
    try:
        data = json.loads(text)
        return RootCauseReport.model_validate(data | {"case_id": case_id})
    except (ValueError, TypeError, ValidationError):
        return None


def unreadable(case_id: str) -> RootCauseReport:
    return RootCauseReport(
        case_id=case_id,
        verdict=Verdict.insufficient_data,
        confidence=0,
        summary="The model did not return a valid report.",
        open_questions=["model output was not a valid report"],
    )


def finalize(draft: RootCauseReport, erp: ErpPort, seen_ids: set[str]) -> RootCauseReport:
    def valid(rid: str) -> bool:
        return rid in seen_ids and (rid.startswith("MANUAL:") or erp.record_exists(rid))

    kept = list(dict.fromkeys(r for r in draft.evidence if valid(r)))
    dropped = [r for r in draft.evidence if r not in kept]
    update: dict = {"evidence": kept}
    if dropped:
        update["confidence"] = round(draft.confidence * 0.5, 4)
        update["open_questions"] = [
            *draft.open_questions,
            f"removed unverified evidence: {', '.join(dropped)}",
        ]
    maintenance = [r for r in kept if r.startswith(("QMEL:", "AUFK:"))]
    if draft.verdict is Verdict.factory_cause and not maintenance:
        update["verdict"] = Verdict.insufficient_data
        note = (f"no maintenance record cited for {draft.equnr} / {draft.failure_mode}; "
                "cause not accepted")
        update["open_questions"] = [*update.get("open_questions", draft.open_questions), note]
    return draft.model_copy(update=update)
