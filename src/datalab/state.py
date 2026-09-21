"""Shared LangGraph state. Only small JSON-like data lives here; big data stays on disk (paths / artifacts)."""

from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict

from datalab.schemas.problem import ProblemConfig
from datalab.schemas.run import RunMode, Status


def _merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    return {**a, **b}


class DataLabState(TypedDict, total=False):
    run_id: str
    project_name: str
    mode: RunMode
    problem: dict[str, Any]
    dataset_path: str  # resolved absolute path; nodes reload the CSV from it

    current_phase: str  # id of the last node that ran ("created" before the first)
    status: Status

    brief: str  # head_ds plan text
    brief_source: str  # "ollama:<model>" or "deterministic"

    plans: Annotated[dict[str, dict[str, Any]], _merge]  # department id -> its lead's work plan (small dict)

    dataset_profile: dict[str, Any]
    data_quality: dict[str, Any]

    eda: dict[str, Any]
    hypotheses: list[str]

    experiments: list[dict[str, Any]]
    model_evaluation: dict[str, Any]
    selected_model: str | None

    review: dict[str, Any]

    artifacts: Annotated[dict[str, str], _merge]  # name -> path relative to the run dir
    errors: Annotated[list[str], operator.add]


def new_state(run_id: str, problem: ProblemConfig, dataset_path: str, mode: RunMode) -> DataLabState:
    return DataLabState(
        run_id=run_id,
        project_name=problem.project_name,
        mode=mode,
        problem=problem.model_dump(),
        dataset_path=dataset_path,
        current_phase="created",
        status="waiting",
        brief="",
        brief_source="",
        plans={},
        dataset_profile={},
        data_quality={},
        eda={},
        hypotheses=[],
        experiments=[],
        model_evaluation={},
        selected_model=None,
        review={},
        artifacts={},
        errors=[],
    )
