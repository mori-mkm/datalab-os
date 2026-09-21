"""Head of Data Science: validates the problem, writes problem.yaml and the plan brief."""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.status("Validating problem definition")
    if not Path(state["dataset_path"]).is_file():
        raise FileNotFoundError(f"dataset not found: {state['dataset_path']}")
    problem_file = ctx.save_yaml("problem.yaml", problem.model_dump())

    ctx.status("Writing plan brief")
    fallback = (
        f"Binary classification of '{problem.target}' on {Path(problem.dataset_path).name}. "
        "Plan: profile the data, run a basic EDA, train a logistic-regression baseline, "
        "review the methodology (leakage, split, seed, metrics), then write the report."
    )
    prompt = (
        "You are the Head of Data Science. In at most 3 sentences, state the plan for this project.\n"
        f"Business problem: {problem.business_problem}\nTarget column: {problem.target}\n"
        "Stages: data profiling, EDA, logistic-regression baseline, methodological review, report."
    )
    brief, source = ctx.narrate(prompt, fallback)
    ctx.status(f"Plan brief ready (source: {source})")
    return {"status": "running", "brief": brief, "brief_source": source, "artifacts": {problem_file: problem_file}}
