"""Analytics lead: basic EDA (summaries, correlations, target rate) and data-derived hypotheses."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.eda import run_eda
from datalab.tools.profiling import load_dataset


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    df = load_dataset(Path(state["dataset_path"]))
    ctx.status("Computing summaries and correlations")
    eda = run_eda(df, problem.target, problem.positive_label, exclude=problem.id_columns)
    name = ctx.save_json("eda.json", eda)
    return {"eda": eda, "hypotheses": eda["hypotheses"], "artifacts": {name: name}}
