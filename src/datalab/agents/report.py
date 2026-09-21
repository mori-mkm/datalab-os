"""Report writer: assembles report.md from the state and closes the run's status."""

from __future__ import annotations

from datalab.services.context import RunContext
from datalab.state import DataLabState


def _fmt(x: object) -> str:
    return f"{x:.3f}" if isinstance(x, float) else str(x)


def build_report(state: DataLabState, summary: str, summary_source: str) -> str:
    verdict = state["review"].get("verdict", "N/A")
    profile, quality = state["dataset_profile"], state["data_quality"]
    exp = state["experiments"][0]
    lines = [
        f"# {state['project_name']}: DataLab OS report",
        "",
        f"- Run: `{state['run_id']}` (mode: real)",
        f"- Review verdict: **{verdict}**",
        "",
        "## Plan",
        f"{state['brief']}  \n*(source: {state['brief_source']})*",
        "",
        "## Data",
        f"- {profile['rows']} rows x {profile['columns']} columns; {quality['duplicate_rows']} duplicated rows; "
        f"{quality['missing_cells']} missing cells",
        f"- Target `{profile['target']['column']}` positive rate: {profile['target']['positive_rate']:.1%}",
        *[f"- Data issue: {i}" for i in quality["issues"]],
        "",
        "## Hypotheses",
        *[f"- {h}" for h in state["hypotheses"]],
        "",
        "## Model",
        f"- {exp['model']} (`{exp['id']}`), {len(exp['features'])} features, seed {exp['seed']}, "
        f"stratified split {exp['split']['n_train']}/{exp['split']['n_test']}",
        "",
        "| metric | value |",
        "|---|---|",
        *[f"| {k} | {_fmt(v)} |" for k, v in exp["metrics"].items()],
        "",
        "## Review",
        *[f"- {'PASS' if c['passed'] else 'FAIL'} `{c['name']}`: {c['detail']}" for c in state["review"]["checks"]],
        "",
        "## Summary",
        f"{summary}  \n*(source: {summary_source})*",
        "",
        "## Artifacts",
        *[f"- `{name}`" for name in state["artifacts"]],
        "",
    ]
    if verdict == "REJECTED":
        lines[1:1] = ["", "> **This run was REJECTED by the review. Do not use the model.**"]
    return "\n".join(lines)


def run(ctx: RunContext, state: DataLabState) -> dict:
    verdict = state["review"]["verdict"]
    ctx.status("Writing executive summary")
    m = state["experiments"][0]["metrics"]
    fallback = (
        f"The logistic-regression baseline reached roc_auc {m['roc_auc']:.3f} and f1 {m['f1']:.3f} on the hold-out set. "
        f"The methodological review verdict is {verdict}."
    )
    prompt = (
        "Write a 3-sentence executive summary of this data science run. Do not invent numbers.\n"
        f"Baseline metrics on the hold-out set: {m}\nReview verdict: {verdict}\n"
        f"Hypotheses: {state['hypotheses']}"
    )
    summary, source = ctx.narrate(prompt, fallback)
    name = ctx.save_text("report.md", build_report(state, summary, source))
    return {
        "status": "rejected" if verdict == "REJECTED" else "completed",
        "artifacts": {name: name},
    }
