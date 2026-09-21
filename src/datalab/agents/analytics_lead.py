"""Analytics Lead: checks that Data Engineering delivered, and decides which columns the analysis covers."""

from __future__ import annotations

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.status("Validating prerequisites: profile and data quality")
    if not state["dataset_profile"] or not state["data_quality"]:
        raise RuntimeError("analytics needs the profile and data quality produced by data_engineering")
    excluded = {problem.target, *problem.id_columns}
    features = [c for c in state["plans"]["data_engineering"]["columns"] if c not in excluded]
    ctx.status(f"Delegating EDA and hypotheses over {len(features)} columns")
    return {"plans": {"analytics": {"features": features}}}
