import json
import asyncio
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


def test_graph_endpoint_serves_the_hierarchy(client):
    body = client.get("/api/graph").json()
    by_id = {n["id"]: n for n in body["nodes"]}
    assert [n["id"] for n in body["nodes"]][0] == "head_ds"
    assert by_id["data_engineering"]["type"] == "department" and by_id["data_engineering"]["parent_id"] is None
    assert by_id["data_engineering.data_profiler"]["parent_id"] == "data_engineering"
    assert {"id": "modeling.model_evaluator->review", "source": "modeling.model_evaluator", "target": "review", "kind": "handoff"} in body["edges"]
    assert {"id": "analytics.analytics_lead->analytics.eda_analyst", "source": "analytics.analytics_lead", "target": "analytics.eda_analyst", "kind": "internal"} in body["edges"]
    assert body == client.get("/api/graph").json()  # deterministic payload


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
    assert [e["node_id"] for e in events if e["event_type"] == "agent_started"][-1] == "report"
    assert "data_engineering.data_profiler" in [e["node_id"] for e in events]


def test_sse_resumes_after_last_event_id(client):
    run_id = client.post("/api/runs", json={"mode": "demo"}).json()["run_id"]
    _wait_finished(client, run_id)
    total = len(client.get(f"/api/runs/{run_id}/events").json())
    with client.stream("GET", f"/api/runs/{run_id}/stream", headers={"Last-Event-ID": str(total - 2)}) as response:
        events = _sse_events(response.iter_lines())
    assert [e["seq"] for e in events] == [total - 1, total]


def _wait_disk_terminal(settings, run_id):
    path = settings.workspace_dir / run_id / "run.json"
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        info = json.loads(path.read_text("utf-8"))
        if info["status"] in ("completed", "rejected", "error"):
            return
        time.sleep(0.01)
    pytest.fail("terminal summary was not persisted")


def test_restart_reconstructs_demo_real_and_rejected_through_all_endpoints(settings):
    saved = {}
    with TestClient(create_app(settings)) as first:
        for mode, config, expected in [
            ("demo", "problem.example", "completed"),
            ("real", "problem.example", "completed"),
            ("real", "problem.leaky", "rejected"),
        ]:
            response = first.post("/api/runs", json={"mode": mode, "config": config})
            assert response.status_code == 202
            rid = response.json()["run_id"]
            _wait_disk_terminal(settings, rid)
            info = first.get(f"/api/runs/{rid}").json()
            events = first.get(f"/api/runs/{rid}/events").json()
            assert info["status"] == expected
            assert _sse_events(first.get(f"/api/runs/{rid}/stream").text.splitlines()) == events
            saved[rid] = (info, events)
    del first  # new app has no memory from app A
    with TestClient(create_app(settings)) as second:
        assert second.app.state.runs._runs == {}
        listed = second.get("/api/runs").json()
        assert [r["run_id"] for r in listed] == sorted(saved, reverse=True)
        assert second.get("/api/runs?limit=1").json() == listed[:1]
        for rid, (info, events) in saved.items():
            assert second.get(f"/api/runs/{rid}").json() == info
            assert second.get(f"/api/runs/{rid}/events").json() == events
            for after in [0, events[-1]["seq"] - 2, events[-1]["seq"], events[-1]["seq"] + 100]:
                response = second.get(f"/api/runs/{rid}/stream", headers={"Last-Event-ID": str(after)})
                assert response.status_code == 200
                assert _sse_events(response.text.splitlines()) == [e for e in events if e["seq"] > after]
        assert second.app.state.runs._runs == {}


@pytest.mark.parametrize("limit", ["0", "201", "invalid"])
def test_history_limit_validation(client, limit):
    assert client.get(f"/api/runs?limit={limit}").status_code == 422


def test_restart_interrupted_and_missing_terminal_replay(settings, partial_run):
    from datalab.services.run_store import RunStore
    from datalab.schemas.run import RunInfo
    from datetime import datetime, timezone
    rid = "run_20260101_000001_abcd"
    RunStore(settings.workspace_dir).save_info(RunInfo(
        run_id=rid, mode="demo", project_name="p", status="completed", created_at=datetime.now(timezone.utc),
    ))
    before = {str(p): p.read_bytes() for p in settings.workspace_dir.rglob("*") if p.is_file()}
    with TestClient(create_app(settings)) as restarted:
        for run_id, expected in [(partial_run, "error"), (rid, "completed")]:
            assert restarted.get(f"/api/runs/{run_id}").json()["status"] == expected
            events = restarted.get(f"/api/runs/{run_id}/events").json()
            assert events[-1]["status"] == expected
            assert _sse_events(restarted.get(f"/api/runs/{run_id}/stream").text.splitlines()) == events
            assert restarted.get(f"/api/runs/{run_id}/events").json() == events
    assert before == {str(p): p.read_bytes() for p in settings.workspace_dir.rglob("*") if p.is_file()}


@pytest.mark.parametrize("after", [2, 100])
def test_live_terminal_stream_closes_when_all_events_consumed(after):
    from datalab.api.events import event_stream
    from datalab.services.event_bus import EventBus
    bus = EventBus()
    bus.emit("r", "run_started")
    bus.emit("r", "run_completed")

    async def collect():
        return [frame async for frame in event_stream(bus, "r", after)]

    assert asyncio.run(asyncio.wait_for(collect(), timeout=1)) == []
    assert bus._listeners["r"] == []


def test_live_stream_with_future_cursor_filters_events_but_closes_at_terminal():
    from datalab.api.events import event_stream
    from datalab.services.event_bus import EventBus
    bus = EventBus()
    bus.emit("r", "run_started")

    async def scenario():
        async def collect():
            return [frame async for frame in event_stream(bus, "r", after=100)]
        task = asyncio.create_task(collect())
        await asyncio.sleep(0)  # let the consumer subscribe while the run is live
        bus.emit("r", "agent_started", node_id="a")
        bus.emit("r", "run_completed")
        return await asyncio.wait_for(task, timeout=1)

    assert asyncio.run(scenario()) == []
    assert bus._listeners["r"] == []


def test_get_artifact_returns_raw_content_and_404s_on_unknown_run_or_name(client):
    run_id = client.post("/api/runs", json={"mode": "real", "config": "problem.example"}).json()["run_id"]
    info = _wait_finished(client, run_id)
    assert info["status"] == "completed"

    response = client.get(f"/api/runs/{run_id}/artifacts/review.json")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["verdict"] == "APPROVED"

    report = client.get(f"/api/runs/{run_id}/artifacts/report.md")
    assert report.status_code == 200 and report.headers["content-type"].startswith("text/markdown")

    assert client.get(f"/api/runs/nope/artifacts/review.json").status_code == 404
    assert client.get(f"/api/runs/{run_id}/artifacts/no_such.json").status_code == 404
    # path-traversal attempt: not a key in info.artifacts, so it 404s rather than escaping the run dir
    assert client.get(f"/api/runs/{run_id}/artifacts/..%2Fproblem.example.yaml").status_code == 404


def test_dataset_preview_real_run_has_rows_demo_run_is_unavailable(client):
    real_id = client.post("/api/runs", json={"mode": "real", "config": "problem.example"}).json()["run_id"]
    _wait_finished(client, real_id)
    preview = client.get(f"/api/runs/{real_id}/dataset-preview?limit=5").json()
    assert preview["available"] is True
    assert preview["columns"] and len(preview["rows"]) == 5
    assert "churned" in preview["columns"]

    demo_id = client.post("/api/runs", json={"mode": "demo"}).json()["run_id"]
    _wait_finished(client, demo_id)
    demo_preview = client.get(f"/api/runs/{demo_id}/dataset-preview").json()
    assert demo_preview == {"available": False, "columns": [], "rows": [], "truncated": False}

    assert client.get("/api/runs/nope/dataset-preview").status_code == 404


@pytest.mark.parametrize("suffix", ["", "/events", "/stream"])
def test_history_invalid_unknown_and_corrupt_runs_are_404(client, settings, suffix):
    rid = "run_20260101_000001_abcd"
    assert client.get(f"/api/runs/{rid}{suffix}").status_code == 404
    path = settings.workspace_dir / rid
    path.mkdir(parents=True, exist_ok=True)
    (path / "run.json").write_text("{broken", encoding="utf-8")
    assert client.get(f"/api/runs/{rid}{suffix}").status_code == 404
    assert client.get(f"/api/runs/not-a-run{suffix}").status_code == 404
    assert client.get("/api/runs").json() == []
