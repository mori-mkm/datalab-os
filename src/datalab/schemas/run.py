"""Run-level types shared by the state, the events and the API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# One vocabulary for both a node's status and a run's status.
Status = Literal["waiting", "running", "completed", "rejected", "error"]
RunMode = Literal["demo", "real"]


class RunInfo(BaseModel):
    run_id: str
    mode: RunMode
    project_name: str
    status: Status = "waiting"
    current_phase: str | None = None
    review_verdict: str | None = None
    artifacts: dict[str, str] = {}
    error: str | None = None
    created_at: datetime
    finished_at: datetime | None = None
