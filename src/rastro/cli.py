import json
from pathlib import Path

import typer

from rastro.config import get_settings

app = typer.Typer(no_args_is_help=True, help="rastro-agent command line")


@app.command()
def investigate(case_id: str, strategy: str = "agent", model: str | None = None) -> None:
    """Investigate one CRM case and print the report."""
    from evals.runner import investigate as run_one
    from rastro.composition import build

    deps = build(get_settings(), [model] if model else None)
    report, stats = run_one(strategy, case_id, deps)
    typer.echo(
        json.dumps(
            report.model_dump(mode="json") | {"steps": stats.steps, "tokens": stats.tokens},
            indent=2,
            ensure_ascii=False,
        )
    )


@app.command("eval")
def evaluate(
    strategy: str = "agent",
    model: str | None = None,
    limit: int | None = None,
    out: Path = Path("results"),
) -> None:
    """Run the evaluation cases and save the scores."""
    from evals.runner import load_truth, run, save
    from rastro.composition import build

    settings = get_settings()
    deps = build(settings, [model] if model else None)
    name = model or settings.llm_models[0]

    def show(s):
        mark = "ok " if s.verdict_ok and s.equnr_ok else "ERR"
        typer.echo(
            f"{mark} {s.case_id} {s.predicted:<18} steps={s.steps} {s.seconds}s {s.error or ''}",
            err=True,
        )

    scores = run(strategy, deps, limit, on_case=show)
    typer.echo(json.dumps(save(strategy, name, scores, load_truth(deps.conn), out), indent=2))
