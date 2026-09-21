import json
import time

import pytest
from fastapi.testclient import TestClient

from datalab.api.app import create_app
from datalab.schemas.event import ExecutionEvent


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as c:
        yield c


def _wait_finished(client: TestClient, run_id: str, timeout: float = 60) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        info = client.get(f"/api/runs/{run_id}").json()
        if info["status"] not in ("waiting", "running"):
            return info
        time.sleep(0.05)
    raise AssertionError("run did not finish")


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["llm"]["available"] is False  # llm_mode=off in tests


def test_graph_endpoint(client):
    body = client.get("/api/graph").json()
    assert [n["id"] for n in body["nodes"]][0] == "head_ds"
    assert {"id": "modeling->review", "source": "modeling", "target": "review"} in body["edges"]


def test_create_run_get_run_and_events(client):
    created = client.post("/api/runs", json={"mode": "demo"})
    assert created.status_code == 202
    run_id = created.json()["run_id"]
    info = _wait_finished(client, run_id)
    assert info["status"] == "completed" and info["mode"] == "demo"
    events = [ExecutionEvent(**e) for e in client.get(f"/api/runs/{run_id}/events").json()]
    assert events[0].event_type == "run_started" and events[-1].event_type == "run_completed"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))


def test_real_run_rejected_via_api(client):
    run_id = client.post("/api/runs", json={"mode": "real", "config": "problem.leaky"}).json()["run_id"]
    assert _wait_finished(client, run_id)["status"] == "rejected"


def test_unknown_run_and_bad_config(client):
    assert client.get("/api/runs/nope").status_code == 404
    assert client.get("/api/runs/nope/stream").status_code == 404
    assert client.post("/api/runs", json={"mode": "real", "config": "missing"}).status_code == 422
    assert client.post("/api/runs", json={"mode": "real", "config": "../secrets"}).status_code == 422


def _sse_events(lines) -> list[dict]:
    return [json.loads(line[len("data: "):]) for line in lines if line.startswith("data: ")]


def test_sse_stream_delivers_all_events_and_closes(client):
    run_id = client.post("/api/runs", json={"mode": "demo"}).json()["run_id"]
    with client.stream("GET", f"/api/runs/{run_id}/stream") as response:
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _sse_events(response.iter_lines())  # returns only because the stream closes after the terminal event
    assert events[0]["event_type"] == "run_started" and events[-1]["event_type"] == "run_completed"
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert [e["department"] for e in events if e["event_type"] == "agent_started"][-1] == "report"


def test_sse_resumes_after_last_event_id(client):
    run_id = client.post("/api/runs", json={"mode": "demo"}).json()["run_id"]
    _wait_finished(client, run_id)
    total = len(client.get(f"/api/runs/{run_id}/events").json())
    with client.stream("GET", f"/api/runs/{run_id}/stream", headers={"Last-Event-ID": str(total - 2)}) as response:
        events = _sse_events(response.iter_lines())
    assert [e["seq"] for e in events] == [total - 1, total]
