from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from datalab.config import Settings
from datalab.schemas.event import EventType
from datalab.schemas.problem import ProblemConfig
from datalab.schemas.run import RunInfo
from datalab.services.event_bus import EventBus
from datalab.services.run_service import RunService
from datalab.services.run_store import RunStore


@pytest.fixture
def settings(tmp_path) -> Settings:
    """No LLM, no pacing delays, isolated workspace."""
    return Settings(workspace_dir=tmp_path / "workspace", llm_mode="off", handoff_delay=0, demo_delay=0)


@pytest.fixture
def service(settings) -> RunService:
    return RunService(settings)


PARTIAL_RUN_ID = "run_20260101_000000_abcd"


@pytest.fixture
def partial_run(settings) -> str:
    """A run whose server died mid-way: run.json says running, the log has no terminal event (7 events)."""
    store = RunStore(settings.workspace_dir)
    store.save_info(
        RunInfo(run_id=PARTIAL_RUN_ID, mode="demo", project_name="p", status="running", created_at=datetime.now(timezone.utc))
    )
    bus, rid = EventBus(store), PARTIAL_RUN_ID
    de, prof = "data_engineering", "data_engineering.data_profiler"
    bus.emit(rid, EventType.run_started, status="running", mode="demo")
    bus.emit(rid, EventType.agent_started, node_id="head_ds", department="head_ds", status="running")
    bus.emit(rid, EventType.agent_completed, node_id="head_ds", department="head_ds", status="completed")
    bus.emit(rid, EventType.handoff_started, node_id="head_ds", department="head_ds", target=de, status="running")
    bus.emit(rid, EventType.agent_started, node_id=de, department=de, status="running")
    bus.emit(rid, EventType.agent_started, node_id=prof, department=de, agent="data_profiler", status="running")
    bus.emit(rid, EventType.agent_status, message="profiling", node_id=prof, department=de, agent="data_profiler", status="running")
    return rid


@pytest.fixture
def synthetic_problem(synthetic, tmp_path) -> ProblemConfig:
    """The synthetic frame written to disk, as a problem a real run can execute."""
    df, problem = synthetic
    csv = tmp_path / "synthetic.csv"
    df.to_csv(csv, index=False)
    return problem.model_copy(update={"dataset_path": str(csv)})


@pytest.fixture
def synthetic() -> tuple[pd.DataFrame, ProblemConfig]:
    rng = np.random.default_rng(0)
    n = 400
    x1, x2 = rng.normal(size=n), rng.normal(size=n)
    y = (x1 + 0.5 * x2 + rng.normal(scale=0.7, size=n) > 0).astype(int)
    df = pd.DataFrame({"id": range(n), "x1": x1, "x2": x2, "cat": rng.choice(["a", "b"], n), "y": y})
    df.loc[::20, "x2"] = np.nan
    return df, ProblemConfig(project_name="t", dataset_path="unused.csv", target="y", id_columns=["id"], seed=1)
