"""Engineering Lead: validates the department's prerequisites and records the plan its agents work from.

It reads only the CSV header; the profiling itself belongs to the Data Profiler.
"""

from __future__ import annotations

from pathlib import Path

from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.profiling import read_columns


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.status("Validating prerequisites: dataset schema")
    columns = read_columns(Path(state["dataset_path"]))
    declared = {problem.target, *problem.id_columns, *problem.leakage_columns}
    missing = sorted(declared - set(columns))
    if missing:
        raise ValueError(f"columns declared in the problem are not in the dataset: {missing}")
    ctx.status(f"Delegating profiling and quality assessment ({len(columns)} columns)")
    return {"plans": {"data_engineering": {"columns": columns}}}
