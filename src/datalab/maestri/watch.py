"""CLI: watch a department's events on the newest (or given) run through the API only.

    python -m datalab.maestri.watch --department data_engineering [--base-url URL] [--run-id ID] [--no-color]

HTTP only, via `client.py`. No second authoritative event log: the only state kept here is the small,
ephemeral, in-process attachment state described in .claude/handoffs/maestri-bridge-contract.md
("Package shape / watch.py", point 5) -- never written to disk.
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import httpx

from datalab.maestri import client
from datalab.schemas.event import EventType, ExecutionEvent
from datalab.schemas.run import RunInfo

DEPARTMENTS = ("data_engineering", "analytics", "modeling", "review", "report", "orchestrator")
TERMINAL_RUN_STATUSES = frozenset({"completed", "rejected", "error"})

POLL_SECONDS = 2
BACKOFF_STEPS = (1, 2, 4, 8, 10)  # capped reconnect backoff, seconds

_RESET, _BOLD, _CYAN, _YELLOW = "\033[0m", "\033[1m", "\033[36m", "\033[33m"


def department_filter(event: ExecutionEvent, department: str) -> bool:
    """Pure predicate: keep `event` for the given department, per the contract's six rules verbatim."""
    if department in ("data_engineering", "analytics", "modeling"):
        if event.department == department:
            return True
        if event.event_type in (EventType.handoff_started, EventType.handoff_completed):
            return event.node_id == department or event.target == department
        return False
    if department == "review":
        return event.event_type in (EventType.review_started, EventType.review_completed)
    if department == "report":
        return event.department == "report" or event.event_type == EventType.artifact_created
    if department == "orchestrator":
        if event.event_type in (
            EventType.run_started,
            EventType.run_completed,
            EventType.run_rejected,
            EventType.run_failed,
            EventType.handoff_started,
            EventType.handoff_completed,
        ):
            return True
        return event.node_id is None
    raise ValueError(f"unknown department: {department}")


def header_status(has_run: bool, connection_ok: bool, terminal: bool) -> str:
    """Pure mapping for the header line: WAITING FOR RUN -> ATTACHED -> RECONNECTING.

    Once the run is terminal we stop trying to reconnect, so a terminal run is always shown ATTACHED
    (its final state) regardless of the last connection attempt.
    """
    if not has_run:
        return "WAITING FOR RUN"
    if terminal or connection_ok:
        return "ATTACHED"
    return "RECONNECTING"


def render_header(run_id: str | None, connection_ok: bool, terminal: bool, color: bool) -> str:
    status = header_status(run_id is not None, connection_ok, terminal)
    text = status if run_id is None else f"{status} / run_{run_id}"
    return f"{_BOLD}{text}{_RESET}" if color else text


def render_event(event: ExecutionEvent, color: bool) -> str:
    node = event.node_id or event.run_id
    line = f"[{event.timestamp.strftime('%H:%M:%S')}] {event.event_type} {node} {event.message}"
    if not color:
        return line
    sgr = _YELLOW if event.status in ("rejected", "error") else _CYAN
    return f"{sgr}{line}{_RESET}"


def _color_enabled(no_color_flag: bool) -> bool:
    return not no_color_flag and not os.environ.get("NO_COLOR")


def _await_newest_run(base_url: str, color: bool) -> RunInfo:
    """Poll for the newest run, but never settle for one that is already terminal.

    A stale completed/rejected/error run from prior workspace/ history must not be mistaken for the
    run the operator just started; keep polling until the newest run is still in progress.
    """
    print(render_header(None, connection_ok=True, terminal=False, color=color))
    while True:
        runs = client.list_runs(base_url, limit=1)
        if runs and runs[0].status not in TERMINAL_RUN_STATUSES:
            return runs[0]
        time.sleep(POLL_SECONDS)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Watch a department's events on a DataLab run.")
    parser.add_argument("--department", required=True, choices=DEPARTMENTS)
    parser.add_argument("--base-url", default=client.DEFAULT_BASE_URL)
    parser.add_argument("--run-id", default=None, help="watch a specific run instead of polling for the newest")
    parser.add_argument("--no-color", action="store_true")
    args = parser.parse_args(argv)
    color = _color_enabled(args.no_color)

    # Event messages may carry Unicode (e.g. the "->" handoff arrow); legacy Windows consoles are
    # stuck on cp1252. Replace what can't be shown rather than crashing the watcher mid-run.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    if args.run_id:
        run_id = args.run_id
    else:
        run_id = _await_newest_run(args.base_url, color).run_id

    print(render_header(run_id, connection_ok=True, terminal=False, color=color))

    last_seq = 0
    backoff_idx = 0
    terminal = False
    while not terminal:
        try:
            for event in client.stream(args.base_url, run_id, last_event_id=last_seq):
                last_seq = event.seq
                backoff_idx = 0
                if department_filter(event, args.department):
                    print(render_event(event, color))
                if event.event_type in (EventType.run_completed, EventType.run_rejected, EventType.run_failed):
                    terminal = True
        except httpx.HTTPError:
            pass  # dropped connection: fall through to the reconnect check below

        if terminal:
            break
        try:
            if client.get_run(args.base_url, run_id).status in TERMINAL_RUN_STATUSES:
                terminal = True
                break
        except httpx.HTTPError:
            pass  # backend unreachable too: keep backing off and retrying rather than crashing

        print(render_header(run_id, connection_ok=False, terminal=False, color=color))
        time.sleep(BACKOFF_STEPS[min(backoff_idx, len(BACKOFF_STEPS) - 1)])
        backoff_idx += 1

    print(render_header(run_id, connection_ok=True, terminal=True, color=color))


if __name__ == "__main__":
    main()
