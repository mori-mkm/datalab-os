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
    """Identifiers (all machine ids, never display labels; stable and independent of execution order):

    - `node_id`: the graph node this event is about; the key the control plane indexes state by.
      Top-level nodes use their own id (`head_ds`, `review`, `report`), a department container uses the
      department id (`data_engineering`) and an agent inside a department is `<department>.<agent>`
      (`data_engineering.data_profiler`). `None` for run-level events.
    - `department`: the top-level unit the node belongs to: the department id for a container and for its
      agents, the node's own id for top-level nodes. `None` for run-level events.
    - `agent`: the agent's local id (`data_profiler`); `None` for department containers and run-level events.
    - `target`: for handoffs, the `node_id` of the executable node that receives control
      (`node_id` is then the node handing over).
    - `status`: status of `node_id` (or of the run, for run events) after this event.
    """

    seq: int  # 1-based, per run; also the SSE id
    event_id: str
    run_id: str
    timestamp: datetime
    event_type: EventType
    node_id: str | None = None
    department: str | None = None
    agent: str | None = None
    status: Status | None = None
    target: str | None = None
    message: str = ""
    data: dict[str, Any] = {}
