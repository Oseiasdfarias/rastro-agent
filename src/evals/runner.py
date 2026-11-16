import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from evals.score import CaseScore, score, summarize
from rastro.agent.graph import run_agent
from rastro.application.fixed import investigate_fixed
from rastro.application.ports import LlmUnavailable
from rastro.composition import Deps
from synthdata.generator import GroundTruth

Strategy = Literal["agent", "fixed"]


def load_truth(conn) -> list[GroundTruth]:
    rows = conn.execute(
        "SELECT case_id, verdict, equnr, failure_mode, window_start, window_end"
        " FROM eval_truth ORDER BY case_id"
    )
    return [GroundTruth.model_validate(r) for r in rows]


def investigate(strategy: Strategy, case_id: str, deps: Deps):
    if strategy == "agent":
        return run_agent(case_id, deps.llm, deps.tools, deps.erp, deps.max_steps)
    return investigate_fixed(case_id, deps.crm, deps.erp, deps.manuals, deps.llm)


def run(strategy: Strategy, deps: Deps, limit: int | None = None, on_case=None) -> list[CaseScore]:
    truth = load_truth(deps.conn)[:limit]
    scores = []
    for t in truth:
        t0 = time.monotonic()
        try:
            report, stats = investigate(strategy, t.case_id, deps)
            s = score(report, t, deps.erp, stats.steps, stats.tokens, time.monotonic() - t0)
        except LlmUnavailable:
            raise
        except Exception as e:  # noqa: BLE001 - a crash on one case is a failed case
            s = CaseScore(
                t.case_id,
                False,
                False,
                False,
                False,
                seconds=round(time.monotonic() - t0, 2),
                error=repr(e)[:300],
            )
        scores.append(s)
        if on_case:
            on_case(s)
    return scores


def save(strategy: Strategy, model: str, scores: list[CaseScore], truth, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    summary = summarize(scores, truth) | {
        "strategy": strategy,
        "model": model,
        "date": datetime.now(UTC).date().isoformat(),
    }
    name = f"eval-{strategy}-{model.replace('/', '_').replace(':', '-')}.json"
    (out / name).write_text(
        json.dumps({"summary": summary, "cases": [s.as_dict() for s in scores]}, indent=2)
    )
    table = out / "README.md"
    if not table.exists():
        table.write_text(
            "| date | strategy | model | n | verdict | equipment | mode | evidence "
            "| noise | steps | tokens | s/case | errors |\n" + "|---" * 13 + "|\n"
        )
    with table.open("a") as f:
        f.write(
            "| {date} | {strategy} | {model} | {n} | {verdict_acc} | {equnr_acc} | {mode_acc} "
            "| {evidence_valid_rate} | {noise_correct} | {mean_steps} | {mean_tokens} "
            "| {mean_seconds} | {errors} |\n".format(**summary)
        )
    return summary
