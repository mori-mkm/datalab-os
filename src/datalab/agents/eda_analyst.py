"""EDA Analyst: numeric/categorical summaries, correlations and target rate (eda.json)."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.eda import summarize_features
from datalab.tools.profiling import load_dataset


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    df = load_dataset(Path(state["dataset_path"]))
    ctx.status("Computing summaries and correlations")
    eda = summarize_features(df, problem.target, problem.positive_label, state["plans"]["analytics"]["features"])
    name = ctx.save_json("eda.json", eda)
    return {"eda": eda, "artifacts": {name: name}}
