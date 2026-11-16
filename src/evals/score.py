from dataclasses import asdict, dataclass

from rastro.application.ports import ErpPort
from rastro.domain.models import RootCauseReport, Verdict
from synthdata.generator import GroundTruth


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    verdict_ok: bool
    equnr_ok: bool
    mode_ok: bool
    evidence_valid: bool
    steps: int = 0
    tokens: int = 0
    seconds: float = 0.0
    predicted: str = ""
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)


def _exists(rid: str, erp: ErpPort) -> bool:
    return rid.startswith("MANUAL:") or erp.record_exists(rid)


def score(
    report: RootCauseReport,
    truth: GroundTruth,
    erp: ErpPort,
    steps: int = 0,
    tokens: int = 0,
    seconds: float = 0.0,
) -> CaseScore:
    verdict_ok = report.verdict is truth.verdict
    if truth.verdict is Verdict.factory_cause:
        equnr_ok = report.equnr == truth.equnr
        mode_ok = report.failure_mode == truth.failure_mode
        window = {
            e.record_id
            for e in erp.get_equipment_history(truth.equnr, truth.window_start, truth.window_end)
        }
        supports = any(r in window for r in report.evidence)
    else:
        equnr_ok = mode_ok = verdict_ok
        supports = True
    valid = bool(report.evidence or truth.verdict is not Verdict.factory_cause)
    valid = valid and supports and all(_exists(r, erp) for r in report.evidence)
    return CaseScore(
        report.case_id,
        verdict_ok,
        equnr_ok,
        mode_ok,
        valid,
        steps,
        tokens,
        round(seconds, 2),
        report.verdict.value,
    )


def summarize(scores: list[CaseScore], truth: list[GroundTruth]) -> dict:
    kind = {t.case_id: t.verdict for t in truth}
    fault = [s for s in scores if kind[s.case_id] is Verdict.factory_cause]
    noise = [s for s in scores if kind[s.case_id] is not Verdict.factory_cause]

    def rate(xs, attr):
        return round(sum(getattr(x, attr) for x in xs) / len(xs), 3) if xs else None

    def mean(attr):
        return round(sum(getattr(s, attr) for s in scores) / len(scores), 1) if scores else None

    return {
        "n": len(scores),
        "verdict_acc": rate(scores, "verdict_ok"),
        "equnr_acc": rate(fault, "equnr_ok"),
        "mode_acc": rate(fault, "mode_ok"),
        "evidence_valid_rate": rate(scores, "evidence_valid"),
        "noise_correct": rate(noise, "verdict_ok"),
        "mean_steps": mean("steps"),
        "mean_tokens": mean("tokens"),
        "mean_seconds": mean("seconds"),
        "errors": sum(s.error is not None for s in scores),
    }
