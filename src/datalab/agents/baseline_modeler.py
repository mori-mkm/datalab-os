"""Baseline Modeler: trains the Logistic Regression baseline on the lead's plan (experiments.json)."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.baseline import train_baseline
from datalab.tools.profiling import load_dataset


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    plan = state["plans"]["modeling"]
    df = load_dataset(Path(state["dataset_path"]))
    ctx.status(f"Training baseline: {plan['model']} on {len(plan['features'])} features")
    result = train_baseline(df, problem, features=plan["features"])
    name = ctx.save_json("experiments.json", result)
    return {
        "experiments": result["experiments"],
        "artifacts": {name: name},
        "_tools": [
            "sklearn.model_selection.train_test_split",
            "sklearn.pipeline.Pipeline",
            "sklearn.linear_model.LogisticRegression",
        ],
    }
