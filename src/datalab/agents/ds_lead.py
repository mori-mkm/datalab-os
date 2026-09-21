"""Data Science lead: trains and evaluates the baseline model."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.baseline import train_baseline
from datalab.tools.profiling import load_dataset


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    df = load_dataset(Path(state["dataset_path"]))
    ctx.status("Training baseline: Logistic Regression")
    result = train_baseline(df, problem)
    metrics = result["experiments"][0]["metrics"]
    ctx.status(f"Baseline evaluated: roc_auc={metrics['roc_auc']:.3f}, f1={metrics['f1']:.3f}")
    name = ctx.save_json("experiments.json", result)
    return {**result, "artifacts": {name: name}}
