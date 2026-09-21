"""Data Science Lead: checks modeling prerequisites and records the experiment plan the modeler follows."""

from __future__ import annotations

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.baseline import select_features


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.status("Validating prerequisites: profile and EDA")
    if not state["dataset_profile"] or not state["eda"]:
        raise RuntimeError("modeling needs the profile and EDA produced by the previous departments")
    counts = {k: v for k, v in state["dataset_profile"]["target"]["counts"].items() if k != "nan"}
    if min(counts.values()) < 2:
        raise ValueError(f"a stratified split needs at least 2 rows per target class, got {counts}")
    features, dropped = select_features(state["plans"]["data_engineering"]["columns"], problem)
    if not features:
        raise ValueError("no feature left after removing the target, id and declared-leakage columns")
    ctx.status(f"Experiment plan: logistic-regression baseline, {len(features)} features, seed {problem.seed}")
    plan = {
        "model": "LogisticRegression",
        "features": features,
        "dropped": dropped,
        "split": {"test_size": problem.test_size, "seed": problem.seed, "stratified": True},
    }
    return {"plans": {"modeling": plan}}
