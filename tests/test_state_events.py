import pytest
from pydantic import ValidationError

from datalab.schemas.event import EventType, ExecutionEvent
from datalab.schemas.problem import DEMO_PROBLEM, ProblemConfig
from datalab.services.event_bus import EventBus
from datalab.state import new_state

REQUIRED_KEYS = {
    "run_id", "project_name", "problem", "dataset_path", "current_phase", "status", "dataset_profile",
    "data_quality", "eda", "hypotheses", "experiments", "selected_model", "review", "artifacts", "errors",
    "plans", "model_evaluation",
}


def test_new_state_has_all_required_keys():
    state = new_state("run_x", DEMO_PROBLEM, "", "demo")
    assert REQUIRED_KEYS <= state.keys()
    assert state["status"] == "waiting" and state["current_phase"] == "created"
    assert state["artifacts"] == {} and state["errors"] == []


def test_problem_rejects_unsupported_task_type():
    with pytest.raises(ValidationError):
        ProblemConfig(project_name="x", dataset_path="a.csv", target="y", task_type="regression")


def test_state_transitions_through_the_run(service):
    info = service.run_sync("demo")
    assert info.status == "completed"
    assert info.current_phase == "report"  # last node that ran
    assert "report.md" in info.artifacts


def test_event_schema_roundtrip_and_validation():
    bus = EventBus()
    event = bus.emit(
        "r1", EventType.agent_started, node_id="analytics.eda_analyst", department="analytics",
        agent="eda_analyst", status="running", message="hi",
    )
    assert ExecutionEvent.model_validate_json(event.model_dump_json()) == event
    assert event.event_id == "evt_0001"
    assert (event.node_id, event.department, event.agent) == ("analytics.eda_analyst", "analytics", "eda_analyst")
    assert bus.emit("r1", EventType.run_started).node_id is None  # run-level events have no node
    with pytest.raises(ValidationError):
        ExecutionEvent(seq=1, event_id="e", run_id="r", timestamp="2026-01-01T00:00:00Z", event_type="nope")


def test_bus_orders_events_and_replays_then_streams_live():
    bus = EventBus()
    bus.emit("r1", EventType.run_started)
    bus.emit("r1", EventType.agent_started, node_id="a")
    received: list[int] = []
    unsubscribe = bus.subscribe("r1", lambda e: received.append(e.seq), after=1)
    bus.emit("r1", EventType.run_completed)
    unsubscribe()
    bus.emit("r1", EventType.run_failed)  # after unsubscribe: not delivered
    assert received == [2, 3]
    assert [e.seq for e in bus.history("r1")] == [1, 2, 3, 4]
    assert bus.history("other") == []
