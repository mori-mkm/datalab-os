import numpy as np
import pandas as pd
import pytest

from datalab.config import Settings
from datalab.schemas.problem import ProblemConfig
from datalab.services.run_service import RunService


@pytest.fixture
def settings(tmp_path) -> Settings:
    """No LLM, no pacing delays, isolated workspace."""
    return Settings(workspace_dir=tmp_path / "workspace", llm_mode="off", handoff_delay=0, demo_delay=0)


@pytest.fixture
def service(settings) -> RunService:
    return RunService(settings)


@pytest.fixture
def synthetic() -> tuple[pd.DataFrame, ProblemConfig]:
    rng = np.random.default_rng(0)
    n = 400
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    y = (x1 + 0.5 * x2 + rng.normal(scale=0.7, size=n) > 0).astype(int)
    df = pd.DataFrame({"id": range(n), "x1": x1, "x2": x2, "cat": rng.choice(["a", "b"], n), "y": y})
    df.loc[::20, "x2"] = np.nan
    return df, ProblemConfig(project_name="t", dataset_path="unused.csv", target="y", id_columns=["id"], seed=1)
