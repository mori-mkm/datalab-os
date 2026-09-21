"""Problem definition: what the user asks the organization to solve."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class ProblemConfig(BaseModel):
    project_name: str
    business_problem: str = ""
    dataset_path: str  # relative paths are resolved against the project root
    target: str
    task_type: Literal["tabular_binary_classification"] = "tabular_binary_classification"
    positive_label: str | int | bool | None = None  # default: the larger of the two target values
    id_columns: list[str] = []  # dropped from the features
    leakage_columns: list[str] = []  # declared leakage: dropped from the features
    test_size: float = Field(0.25, gt=0, lt=1)
    seed: int = 42

    def resolved_dataset(self, root: Path) -> Path:
        path = Path(self.dataset_path)
        return path if path.is_absolute() else root / path


# The demo workflow analyses no data, so its problem is a labelled placeholder.
DEMO_PROBLEM = ProblemConfig(
    project_name="demo-workflow",
    business_problem="Demo workflow: validates the orchestration and the control plane only.",
    dataset_path="",
    target="",
)


def load_problem(path: Path) -> ProblemConfig:
    return ProblemConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
