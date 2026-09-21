"""Creates and executes runs. Used by the API (background thread) and the CLI (synchronous)."""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timezone

from datalab.config import Settings
from datalab.graphs.organization import get_graph
from datalab.schemas.event import EventType
from datalab.schemas.problem import DEMO_PROBLEM, ProblemConfig
from datalab.schemas.run import RunInfo, RunMode
from datalab.services.context import RunContext
from datalab.services.event_bus import EventBus
from datalab.state import DataLabState, new_state


class RunService:
    def __init__(self, settings: Settings, bus: EventBus | None = None) -> None:
        self.settings = settings
        self.bus = bus or EventBus()
        self._runs: dict[str, RunInfo] = {}

    def get(self, run_id: str) -> RunInfo | None:
        return self._runs.get(run_id)

    def create(self, mode: RunMode, problem: ProblemConfig | None = None) -> tuple[RunInfo, DataLabState]:
        problem = DEMO_PROBLEM if mode == "demo" else problem
        if problem is None:
            raise ValueError("a real run needs a problem definition")
        run_id = f"run_{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:4]}"
        (self.settings.workspace_dir / run_id).mkdir(parents=True, exist_ok=True)
        dataset = "" if mode == "demo" else str(problem.resolved_dataset(self.settings.root))
        info = RunInfo(
            run_id=run_id, mode=mode, project_name=problem.project_name, created_at=datetime.now(timezone.utc)
        )
        self._runs[run_id] = info
        return info, new_state(run_id, problem, dataset, mode)

    def start(self, mode: RunMode, problem: ProblemConfig | None = None) -> RunInfo:
        """Create a run and execute it in a background thread (API)."""
        info, state = self.create(mode, problem)
        threading.Thread(target=self.execute, args=(info.run_id, state), daemon=True, name=info.run_id).start()
        return info

    def run_sync(self, mode: RunMode, problem: ProblemConfig | None = None) -> RunInfo:
        """Create a run and execute it in the calling thread (CLI / tests)."""
        info, state = self.create(mode, problem)
        self.execute(info.run_id, state)
        return info

    def execute(self, run_id: str, state: DataLabState) -> None:
        info = self._runs[run_id]
        ctx = RunContext(
            run_id=run_id,
            run_dir=self.settings.workspace_dir / run_id,
            mode=info.mode,
            bus=self.bus,
            settings=self.settings,
        )
        info.status = "running"
        ctx.emit(EventType.run_started, f"Run started ({info.mode} workflow)", status="running", mode=info.mode)
        try:
            final = get_graph().invoke(state, config={"configurable": {"ctx": ctx}})
        except Exception as exc:
            info.status, info.error = "error", f"{type(exc).__name__}: {exc}"
            info.finished_at = datetime.now(timezone.utc)
            ctx.emit(EventType.run_failed, info.error, status="error")
            return
        info.status = final["status"]
        info.current_phase = final["current_phase"]
        info.artifacts = final["artifacts"]
        info.review_verdict = final.get("review", {}).get("verdict")
        info.finished_at = datetime.now(timezone.utc)
        if info.status == "rejected":
            ctx.emit(EventType.run_rejected, "Run rejected by the review", status="rejected")
        else:
            ctx.emit(EventType.run_completed, "Run completed", status="completed")
