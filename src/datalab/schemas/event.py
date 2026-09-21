"""Execution event contract: the only thing the control plane needs to observe a run."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel

from datalab.schemas.run import Status


class EventType(StrEnum):
    run_started = "run_started"
    run_completed = "run_completed"
    run_rejected = "run_rejected"
    run_failed = "run_failed"
    agent_started = "agent_started"
    agent_status = "agent_status"  # progress inside an agent (updates its "current task")
    agent_completed = "agent_completed"
    agent_failed = "agent_failed"
    handoff_started = "handoff_started"
    handoff_completed = "handoff_completed"
    artifact_created = "artifact_created"
    review_started = "review_started"
    review_completed = "review_completed"


TERMINAL_EVENTS = frozenset({EventType.run_completed, EventType.run_rejected, EventType.run_failed})


class ExecutionEvent(BaseModel):
    seq: int  # 1-based, per run; also the SSE id
    event_id: str
    run_id: str
    timestamp: datetime
    event_type: EventType
    department: str | None = None  # graph node id; None for run-level events
    agent: str | None = None
    status: Status | None = None  # status of `department` (or of the run) after this event
    target: str | None = None  # destination node of a handoff
    message: str = ""
    data: dict[str, Any] = {}
