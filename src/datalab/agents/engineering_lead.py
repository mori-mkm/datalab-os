"""Data Engineering lead: profiles the dataset and assesses basic data quality."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.profiling import load_dataset, profile_dataset


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.status("Loading dataset")
    df = load_dataset(Path(state["dataset_path"]))
    ctx.status(f"Profiling {len(df)} rows x {df.shape[1]} columns")
    result = profile_dataset(df, problem.target, problem.positive_label)
    name = ctx.save_json("data_profile.json", result)
    return {
        "dataset_profile": result["profile"],
        "data_quality": result["quality"],
        "artifacts": {name: name},
    }
