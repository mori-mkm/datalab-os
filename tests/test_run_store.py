"""Run history on disk: what is written, what is read back, and how damaged or unfinished runs are reported."""

import json
import logging
import time
from datetime import datetime, timezone

import pytest

from datalab.schemas.event import ExecutionEvent
from datalab.schemas.run import RunInfo
from datalab.services import run_store
from datalab.services.event_bus import EventBus
from datalab.services.run_service import RunService
from datalab.services.run_store import INTERRUPTED, RunStore

RID = "run_20260101_000000_abcd"


def _info(run_id=RID, **kw) -> RunInfo:
    return RunInfo(run_id=run_id, mode="demo", project_name="p", created_at=datetime.now(timezone.utc), **kw)


def _wait_persisted(settings, run_id, timeout=60):
    """run.json (written after the terminal event) holds a final status."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            if json.loads((settings.workspace_dir / run_id / "run.json").read_text("utf-8"))["status"] in (
                "completed", "rejected", "error",
            ):
                return
        except (OSError, ValueError):
            pass
        time.sleep(0.05)
    raise AssertionError("run was not persisted")


def _running(events) -> set[str]:
    """Same fold as the control plane: latest status per node, handoffs ignored."""
    status = {}
    for e in events:
        if e.node_id and e.status and not e.event_type.value.startswith("handoff_"):
            status[e.node_id] = e.status
    return {n for n, s in status.items() if s == "running"}


# ---------------------------------------------------------------- round trip


def test_finished_runs_read_back_identically_from_a_fresh_store(service, settings, synthetic_problem):
    demo = service.run_sync("demo")
    real = service.run_sync("real", synthetic_problem)
    assert demo.dataset is None and real.dataset == "synthetic.csv"  # name only, never the path
    fresh = RunStore(settings.workspace_dir)
    for info in (demo, real):
        loaded_info, events = fresh.load_run(info.run_id)
        assert loaded_info == info and events == service.bus.history(info.run_id)
        assert fresh.load_info(info.run_id) == info
    assert set(fresh.run_ids()) == {demo.run_id, real.run_id}


def test_event_log_is_the_sse_payload_one_line_per_event(service, settings):
    info = service.run_sync("demo")
    lines = (settings.workspace_dir / info.run_id / "events.jsonl").read_text("utf-8").splitlines()
    assert lines == [e.model_dump_json() for e in service.bus.history(info.run_id)]


def test_events_are_persisted_before_listeners_see_them(settings):
    store = RunStore(settings.workspace_dir)
    bus, seen = EventBus(store), []
    bus.subscribe(RID, lambda e: seen.append(len(store._read_events(RID)) == e.seq))
    for _ in range(3):
        bus.emit(RID, "agent_status", message="x")
    assert seen == [True, True, True]


def test_bus_without_store_still_works():
    bus = EventBus()
    bus.emit("r", "run_started")
    assert [e.seq for e in bus.history("r")] == [1]


# ---------------------------------------------------------------- interrupted / terminal-wins


def test_interrupted_run_is_derived_at_read_time_and_never_written_back(settings, partial_run):
    store = RunStore(settings.workspace_dir)
    run_json = (settings.workspace_dir / partial_run / "run.json").read_text("utf-8")
    log_before = (settings.workspace_dir / partial_run / "events.jsonl").read_text("utf-8")

    info, events = store.load_run(partial_run)
    stored = events[:7]
    assert info.status == "error" and info.error == INTERRUPTED and info.finished_at == stored[-1].timestamp
    tail = events[7:]
    # each node still running is failed, in order of its last event, then the run
    assert [(e.event_type.value, e.node_id, e.status) for e in tail] == [
        ("agent_failed", "data_engineering", "error"),
        ("agent_failed", "data_engineering.data_profiler", "error"),
        ("run_failed", None, "error"),
    ]
    assert tail[1].department == "data_engineering" and tail[1].agent == "data_profiler"
    assert all(e.timestamp == stored[-1].timestamp and e.data == {"interrupted": True} for e in tail)
    assert [e.seq for e in events] == list(range(1, 11)) and events[-1].event_id == "evt_0010"
    assert _running(events) == set()  # nothing left "running"; head_ds stayed completed
    # pure and idempotent; the files are untouched
    assert store.load_run(partial_run) == (info, events) and store.load_info(partial_run) == info
    assert (settings.workspace_dir / partial_run / "run.json").read_text("utf-8") == run_json
    assert (settings.workspace_dir / partial_run / "events.jsonl").read_text("utf-8") == log_before


def test_waiting_run_without_events_is_interrupted_too(settings):
    store = RunStore(settings.workspace_dir)
    created = _info()
    store.save_info(created)
    info, events = store.load_run(RID)
    assert info.status == "error" and info.finished_at == created.created_at
    assert [(e.seq, e.event_type.value, e.node_id) for e in events] == [(1, "run_failed", None)]


def test_terminal_event_wins_over_a_stale_run_json(settings):
    store = RunStore(settings.workspace_dir)
    bus = EventBus(store)
    store.save_info(_info(status="running"))
    bus.emit(RID, "run_started", status="running")
    done = bus.emit(RID, "run_rejected", status="rejected")
    info, events = store.load_run(RID)
    assert info.status == "rejected" and info.finished_at == done.timestamp and len(events) == 2  # no synthetic events

    other = "run_20260101_000001_abcd"
    store.save_info(_info(other, status="running"))
    failed = bus.emit(other, "run_failed", message="boom", status="error")
    info, events = store.load_run(other)
    assert info.status == "error" and info.error == "boom" and info.finished_at == failed.timestamp


# ---------------------------------------------------------------- damaged files


def test_truncated_last_line_garbage_middle_line_and_blank_lines_are_skipped(settings, partial_run):
    path = settings.workspace_dir / partial_run / "events.jsonl"
    lines = path.read_text("utf-8").splitlines()
    path.write_bytes(
        ("\n".join(lines[:3] + ["not json", "", '{"seq": 1}'] + lines[3:]) + '\n{"seq": 8, "event_id": "evt_00').encode()
        + b"\n\xff\xfe\n"
    )
    info, events = RunStore(settings.workspace_dir).load_run(partial_run)
    assert [e.seq for e in events[:7]] == list(range(1, 8))  # the 7 good events survive
    assert info.status == "error" and events[-1].event_type == "run_failed" and events[-1].seq == 10


def test_missing_events_file_recovers_terminal_event(settings):
    store = RunStore(settings.workspace_dir)
    store.save_info(_info(status="completed"))
    info, events = store.load_run(RID)
    assert info.status == "completed"
    assert len(events) == 1 and events[0].event_type == "run_completed"
    assert events[0].seq == 1 and events[0].data == {"recovered": True}


@pytest.mark.parametrize(
    "content",
    [None, "", "{not json", "[]", '{"run_id": "x"}', b"\xff\xfe\x00", "null",
     _info("run_20260101_000000_beef").model_dump_json()],  # last: valid, but belongs to another run id
)
def test_corrupt_or_missing_run_json_means_not_found_everywhere(settings, content):
    d = settings.workspace_dir / RID
    d.mkdir(parents=True)
    if content is not None:
        (d / "run.json").write_bytes(content if isinstance(content, bytes) else content.encode())
    (d / "events.jsonl").write_text("{}\n", encoding="utf-8")
    good = RunService(settings).run_sync("demo")
    service = RunService(settings)
    assert service.store.load_run(RID) is None and service.store.load_info(RID) is None
    assert service.get(RID) is None and service.events(RID) is None
    assert [r.run_id for r in service.list_runs()] == [good.run_id]  # skipped, the healthy run is still listed


def test_missing_workspace_lists_nothing(settings):
    assert RunStore(settings.workspace_dir).run_ids() == []
    assert RunService(settings).list_runs() == []


@pytest.mark.parametrize(
    "bad",
    ["", "..", ".", "../" + RID, "..\\" + RID, RID + "\n", RID.upper(), "run_2026010_000000_abcd", "run_20260101_000000_abcde",
     "run_٢٠٢٦٠١٠١_000000_abcd", "nope", "/etc", "C:\\Windows"],
)
def test_ids_that_are_not_run_ids_never_touch_the_filesystem(settings, tmp_path, bad):
    outside = RunStore(tmp_path)  # a valid run one level above the workspace: "../<id>" must not reach it
    outside.save_info(_info())
    store = RunStore(settings.workspace_dir)
    (settings.workspace_dir).mkdir(parents=True)
    assert store.load_run(bad) is None and store.load_info(bad) is None
    assert RunService(settings).get(bad) is None and RunService(settings).events(bad) is None


# ---------------------------------------------------------------- concurrency / precedence / failures


def test_concurrent_runs_write_separate_files_with_contiguous_seq(service, settings):
    ids = [service.start("demo").run_id for _ in range(3)]
    for run_id in ids:
        _wait_persisted(settings, run_id)
    assert len(set(ids)) == 3
    for run_id in ids:
        events = [
            ExecutionEvent.model_validate_json(line)
            for line in (settings.workspace_dir / run_id / "events.jsonl").read_text("utf-8").splitlines()
        ]
        assert [e.seq for e in events] == list(range(1, len(events) + 1))
        assert {e.run_id for e in events} == {run_id} and events[-1].event_type == "run_completed"


def test_memory_wins_over_a_stale_or_damaged_disk_copy(service, settings):
    info = service.run_sync("demo")
    d = settings.workspace_dir / info.run_id
    (d / "run.json").write_text(_info(info.run_id, status="waiting").model_copy(update={"project_name": "STALE"}).model_dump_json())
    (d / "events.jsonl").write_text("garbage\n", encoding="utf-8")
    assert service.get(info.run_id) is info and service.get(info.run_id).status == "completed"
    assert service.events(info.run_id) == service.bus.history(info.run_id) and len(service.events(info.run_id)) > 10
    assert service.list_runs()[0] is info
    # a process that does not know the run sees the disk copy instead (here: the stale one, derived as interrupted)
    assert RunService(settings).get(info.run_id).project_name == "STALE"


def test_list_is_newest_first_limited_and_merges_memory_with_disk(settings):
    store = RunStore(settings.workspace_dir)
    old_ids = ["run_20260101_000000_aaaa", "run_20260301_000000_aaaa", "run_20260201_000000_aaaa"]
    for rid in old_ids:
        store.save_info(_info(rid, status="completed"))
    service = RunService(settings)
    live = service.run_sync("demo")  # named with today's date: newest
    ids = [r.run_id for r in service.list_runs()]
    assert ids == [live.run_id, old_ids[1], old_ids[2], old_ids[0]]
    assert [r.run_id for r in service.list_runs(2)] == ids[:2]


def test_store_failure_never_alters_a_run(settings, tmp_path, caplog):
    (tmp_path / "blocker").write_text("a file, so nothing can be created below it")
    service = RunService(settings)
    service.store.root = tmp_path / "blocker" / "ws"  # every persistence write now fails
    with caplog.at_level(logging.WARNING, logger="datalab.services.run_store"):
        info = service.run_sync("demo")
    events = service.bus.history(info.run_id)
    assert info.status == "completed" and events[0].event_type == "run_started" and events[-1].event_type == "run_completed"
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert (settings.workspace_dir / info.run_id / "report.md").is_file()  # artifacts are not the store's business
    assert "could not persist" in caplog.text


def test_run_json_write_failure_is_swallowed_and_leaves_no_partial_file(service, settings, monkeypatch):
    def boom(*_):
        raise OSError("disk full")

    monkeypatch.setattr(run_store.os, "replace", boom)
    info = service.run_sync("demo")
    assert info.status == "completed"
    d = settings.workspace_dir / info.run_id
    assert not (d / "run.json").exists()  # the atomic write never half-wrote the real file
    assert len((d / "events.jsonl").read_text("utf-8").splitlines()) == len(service.bus.history(info.run_id))


@pytest.mark.parametrize("status,kind", [("completed", "run_completed"), ("rejected", "run_rejected"), ("error", "run_failed")])
@pytest.mark.parametrize("damage", ["missing", "garbage", "truncated", "absent_terminal"])
def test_terminal_summary_recovers_read_only_deterministic_tail(settings, status, kind, damage):
    store = RunStore(settings.workspace_dir)
    original = _info(status=status, error="boom" if status == "error" else None)
    store.save_info(original)
    path = settings.workspace_dir / RID / "events.jsonl"
    if damage != "missing":
        if damage == "garbage":
            path.write_text("garbage\n", encoding="utf-8")
        else:
            bus = EventBus(store)
            bus.emit(RID, "run_started", status="running")
            if damage == "truncated":
                with path.open("a", encoding="utf-8") as stream:
                    stream.write('{"seq":2')
    before = {p.name: p.read_bytes() for p in path.parent.iterdir()}
    info, events = store.load_run(RID)
    assert info == original and store.load_info(RID) == info
    assert events[-1].event_type == kind and events[-1].status == status
    assert events[-1].data == {"recovered": True}
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert events[-1].timestamp >= events[0].timestamp
    assert store.load_run(RID) == (info, events)
    assert before == {p.name: p.read_bytes() for p in path.parent.iterdir()}


def test_log_rejects_foreign_duplicate_nonpositive_and_out_of_order_events(settings):
    store = RunStore(settings.workspace_dir)
    store.save_info(_info(status="running"))
    bus = EventBus()
    first = bus.emit(RID, "run_started", status="running")
    terminal = bus.emit(RID, "run_completed", status="completed").model_copy(update={"seq": 5})
    entries = [
        first.model_copy(update={"seq": 0}),
        first.model_copy(update={"run_id": "run_20260101_000001_abcd", "seq": 100}),
        first, first,
        first.model_copy(update={"seq": 3}),
        first.model_copy(update={"seq": 2}), terminal,
        first.model_copy(update={"seq": 6}),
    ]
    path = settings.workspace_dir / RID / "events.jsonl"
    path.write_text("\n".join(e.model_dump_json() for e in entries), encoding="utf-8")
    before = path.read_bytes()
    info, events = store.load_run(RID)
    assert info.status == "completed"
    assert [e.seq for e in events] == [1, 3, 5]
    assert {e.run_id for e in events} == {RID}
    assert store.load_run(RID) == (info, events) and path.read_bytes() == before


@pytest.mark.parametrize("preconfigured", [False, True])
def test_injected_bus_uses_service_store(settings, tmp_path, preconfigured):
    bus = EventBus(RunStore(tmp_path / "other")) if preconfigured else EventBus()
    service = RunService(settings, bus=bus)
    info = service.run_sync("demo")
    assert service.bus is bus
    assert RunStore(settings.workspace_dir).load_run(info.run_id) == (info, bus.history(info.run_id))
    assert not (tmp_path / "other").exists()


def test_injected_active_bus_is_rejected_without_rebinding(settings):
    bus = EventBus()
    bus.emit("existing", "run_started")
    with pytest.raises(ValueError, match="unused EventBus"):
        RunService(settings, bus=bus)


def test_workspace_environment_override(monkeypatch, tmp_path):
    from datalab.config import load_settings
    monkeypatch.setenv("DATALAB_WORKSPACE", str(tmp_path))
    assert load_settings().workspace_dir == tmp_path


@pytest.mark.parametrize("naive_summary", [True, False])
def test_recovery_accepts_mixed_timezone_timestamps(settings, naive_summary):
    store = RunStore(settings.workspace_dir)
    finished = datetime(2026, 1, 1, 12, tzinfo=None if naive_summary else timezone.utc)
    store.save_info(_info(status="completed", finished_at=finished))
    event = EventBus().emit(RID, "run_started", status="running").model_copy(update={
        "timestamp": datetime(2026, 1, 1, 13, tzinfo=timezone.utc if naive_summary else None),
    })
    store.append_event(event)
    info, events = store.load_run(RID)
    assert events[0] == event
    assert events[-1].timestamp == datetime(2026, 1, 1, 13, tzinfo=timezone.utc)
    assert store.load_run(RID) == (info, events)
