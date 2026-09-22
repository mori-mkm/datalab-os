import io
from datetime import datetime, timezone

import pytest

from datalab.api.events import format_sse
from datalab.maestri import client, run, watch
from datalab.schemas.event import ExecutionEvent
from datalab.schemas.run import RunInfo


def _event(seq: int, event_type: str, **kwargs) -> ExecutionEvent:
    fields = {"node_id": "head_ds", "message": "hi", **kwargs}
    return ExecutionEvent(
        seq=seq, event_id=f"e{seq}", run_id="r1", timestamp=datetime.now(timezone.utc),
        event_type=event_type, **fields,
    )


def test_parse_sse_turns_raw_frames_into_execution_events():
    e1, e2 = _event(1, "run_started"), _event(2, "run_completed")
    raw = format_sse(e1) + ": keepalive\n\n" + format_sse(e2)
    events = list(client._parse_sse(raw.split("\n")))
    assert events == [e1, e2]


def test_parse_sse_ignores_comment_only_stream():
    assert list(client._parse_sse(": keepalive\n\n".split("\n"))) == []


def test_no_llm_warns_when_server_llm_is_not_off(monkeypatch, capsys):
    monkeypatch.setattr(client, "health", lambda base_url: {"llm": {"mode": "auto"}})
    monkeypatch.setattr(
        client, "create_run",
        lambda base_url, mode, config: RunInfo(
            run_id="run_x", mode="real", project_name="p", status="waiting",
            created_at=datetime.now(timezone.utc), dataset="d.csv",
        ),
    )
    run.main(["--config", "problem.small", "--no-llm"])
    out = capsys.readouterr().out
    assert run.NO_LLM_WARNING in out
    assert "run_id=run_x dataset=d.csv status=waiting" in out


def test_no_llm_silent_when_server_is_already_off(monkeypatch, capsys):
    monkeypatch.setattr(client, "health", lambda base_url: {"llm": {"mode": "off"}})
    monkeypatch.setattr(
        client, "create_run",
        lambda base_url, mode, config: RunInfo(
            run_id="run_x", mode="real", project_name="p", status="waiting",
            created_at=datetime.now(timezone.utc),
        ),
    )
    run.main(["--config", "problem.small", "--no-llm"])
    assert run.NO_LLM_WARNING not in capsys.readouterr().out


# --- watch.department_filter: one representative event per department, per the contract's six rules ---

@pytest.mark.parametrize(
    "department, event, kept",
    [
        # data_engineering: own department's events kept, unrelated department's events dropped.
        ("data_engineering", _event(1, "agent_status", department="data_engineering", node_id="data_engineering.data_profiler"), True),
        ("data_engineering", _event(1, "agent_status", department="analytics", node_id="analytics.eda_analyst"), False),
        # data_engineering: handoff into/out of the department, seen from the orchestrator side.
        ("data_engineering", _event(1, "handoff_started", department=None, node_id="head_ds", target="data_engineering"), True),
        ("data_engineering", _event(1, "handoff_completed", department=None, node_id="data_engineering", target="analytics"), True),
        ("data_engineering", _event(1, "handoff_started", department=None, node_id="head_ds", target="analytics"), False),
        # analytics / modeling: same shape, different department id.
        ("analytics", _event(1, "agent_completed", department="analytics", node_id="analytics.hypothesis_analyst"), True),
        ("modeling", _event(1, "agent_started", department="modeling", node_id="modeling.baseline_modeler"), True),
        ("modeling", _event(1, "agent_started", department="analytics", node_id="analytics.eda_analyst"), False),
        # review: event_type only; verdict travels in status/data, not a separate event type.
        ("review", _event(1, "review_started", department="review", node_id="review"), True),
        ("review", _event(1, "review_completed", department="review", node_id="review", status="rejected", data={"verdict": "REJECTED"}), True),
        ("review", _event(1, "agent_completed", department="review", node_id="review"), False),
        # report: own department's events, plus every artifact_created notification regardless of origin.
        ("report", _event(1, "agent_completed", department="report", node_id="report"), True),
        ("report", _event(1, "artifact_created", department="data_engineering", node_id="data_engineering.data_profiler"), True),
        ("report", _event(1, "agent_completed", department="data_engineering", node_id="data_engineering.data_profiler"), False),
        # orchestrator: run-level + handoff events; explicitly excludes agent_* and artifact_created.
        ("orchestrator", _event(1, "run_started", department=None, node_id=None), True),
        ("orchestrator", _event(1, "run_completed", department=None, node_id=None, status="completed"), True),
        ("orchestrator", _event(1, "handoff_started", department=None, node_id="head_ds", target="data_engineering"), True),
        ("orchestrator", _event(1, "agent_started", department="data_engineering", node_id="data_engineering.data_profiler"), False),
        ("orchestrator", _event(1, "artifact_created", department="report", node_id="report"), False),
    ],
)
def test_department_filter(department, event, kept):
    assert watch.department_filter(event, department) is kept


def test_department_filter_rejects_unknown_department():
    with pytest.raises(ValueError):
        watch.department_filter(_event(1, "run_started"), "not-a-department")


# --- watch.header_status: pure mapping of (has_run, connection_ok, terminal) -> status label ---

@pytest.mark.parametrize(
    "has_run, connection_ok, terminal, expected",
    [
        (False, True, False, "WAITING FOR RUN"),
        (False, False, False, "WAITING FOR RUN"),
        (True, True, False, "ATTACHED"),
        (True, False, False, "RECONNECTING"),
        (True, False, True, "ATTACHED"),  # terminal: stop reconnecting, show the final state as attached
    ],
)
def test_header_status(has_run, connection_ok, terminal, expected):
    assert watch.header_status(has_run, connection_ok, terminal) == expected


def test_render_header_includes_run_id_once_attached():
    assert watch.render_header(None, connection_ok=True, terminal=False, color=False) == "WAITING FOR RUN"
    assert watch.render_header("run_1", connection_ok=True, terminal=False, color=False) == "ATTACHED / run_run_1"
    assert watch.render_header("run_1", connection_ok=False, terminal=False, color=False) == "RECONNECTING / run_run_1"


# --- evaluator (mb-4) regression: watch.py started without --run-id must not attach to a stale,
# already-terminal run from prior workspace/ history. It must keep polling until a run that is not
# yet terminal (in-progress or freshly started) shows up as the newest run.

def _run_info(run_id: str, status: str) -> RunInfo:
    return RunInfo(
        run_id=run_id, mode="real", project_name="p", status=status,
        created_at=datetime.now(timezone.utc),
    )


def test_await_newest_run_ignores_stale_terminal_run_and_waits_for_new_one(monkeypatch):
    stale = _run_info("old_run", "completed")
    fresh = _run_info("new_run", "running")
    # First two polls only see the stale, already-terminal run; the third poll finally sees a new,
    # non-terminal run -- the watcher must skip the first two and attach to the third.
    responses = [[stale], [stale], [fresh]]
    monkeypatch.setattr(client, "list_runs", lambda base_url, limit=1: responses.pop(0))
    monkeypatch.setattr(watch.time, "sleep", lambda seconds: None)

    result = watch._await_newest_run("http://x", color=False)

    assert result.run_id == "new_run"
    assert responses == []  # polled exactly 3 times: didn't stop early on the stale run


# --- evaluator (mb-4) regression: run.py --follow crashes on the legacy-console encoding watch.py already
# guards against. Live repro: `python -m datalab.maestri.run --config problem.small --follow` under a
# stdout whose codepage cannot encode U+2192 (the handoff arrow, e.g. cp1252 -- the exact console watch.py's
# `sys.stdout.reconfigure(errors="replace")` was added for) raises UnicodeEncodeError. run.py has no such
# reconfigure call, so `--follow` (which reuses client.stream and prints every event.message verbatim) is not
# protected. This test pins the crash down without needing an actual legacy Windows console.

def test_follow_does_not_crash_on_legacy_console_encoding(monkeypatch, capsys):
    monkeypatch.setattr(client, "health", lambda base_url: {"llm": {"mode": "off"}})
    monkeypatch.setattr(
        client, "create_run",
        lambda base_url, mode, config: RunInfo(
            run_id="run_x", mode="real", project_name="p", status="running",
            created_at=datetime.now(timezone.utc), dataset="d.csv",
        ),
    )
    events = [
        _event(1, "handoff_started", node_id="head_ds", target="data_engineering",
               message="Head of Data Science → Engineering Lead"),
        _event(2, "run_completed", node_id=None, message="Run completed"),
    ]
    monkeypatch.setattr(client, "stream", lambda base_url, run_id, last_event_id=0: iter(events))

    # A legacy Windows console's stdout: strict cp1252, can't encode U+2192 (the handoff arrow).
    legacy_stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252", errors="strict")
    monkeypatch.setattr("sys.stdout", legacy_stdout)
    try:
        run.main(["--config", "problem.small", "--follow"])  # must not raise UnicodeEncodeError
    finally:
        monkeypatch.undo()
