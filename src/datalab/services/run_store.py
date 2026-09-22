"""Run history as plain files: `<workspace>/<run_id>/run.json` (atomic) + `events.jsonl` (append-only).

Writes never raise into a run (errors are logged). Reads never raise either: unreadable runs are "not found",
invalid log entries are skipped. Missing terminal events are reconciled at read time, never written back.
"""

from __future__ import annotations

import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from datalab.schemas.event import TERMINAL_EVENTS, EventType, ExecutionEvent
from datalab.schemas.run import RunInfo, Status

log = logging.getLogger(__name__)

RUN_ID = re.compile(r"run_\d{8}_\d{6}_[0-9a-f]{4}", re.ASCII)  # use with fullmatch: blocks path traversal
INTERRUPTED = "interrupted: the server stopped before the run finished"
_ENDED: dict[EventType, Status] = {
    EventType.run_completed: "completed",
    EventType.run_rejected: "rejected",
    EventType.run_failed: "error",
}


class RunStore:
    def __init__(self, workspace_dir: Path) -> None:
        self.root = Path(workspace_dir)

    # ---- writes: best effort, never raise

    def save_info(self, info: RunInfo) -> None:
        try:
            path = self.root / info.run_id / "run.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_name("run.json.tmp")
            tmp.write_text(info.model_dump_json(), encoding="utf-8")
            os.replace(tmp, path)
        except Exception as exc:
            log.warning("could not persist run.json of %s: %s", info.run_id, exc)

    def append_event(self, event: ExecutionEvent) -> None:
        try:
            path = self.root / event.run_id / "events.jsonl"
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(event.model_dump_json() + "\n")
        except Exception as exc:
            log.warning("could not persist event %s of %s: %s", event.seq, event.run_id, exc)

    # ---- reads: None == not found

    def run_ids(self) -> list[str]:
        try:
            return [p.name for p in self.root.iterdir() if p.is_dir() and RUN_ID.fullmatch(p.name)]
        except OSError:
            return []

    def load_run(self, run_id: str) -> tuple[RunInfo, list[ExecutionEvent]] | None:
        info = self._read_info(run_id)
        return None if info is None else _reconcile(info, self._read_events(run_id))

    def load_info(self, run_id: str) -> RunInfo | None:
        """Like `load_run(...)[0]` but skips the log when run.json already holds a final status (cheap listing)."""
        info = self._read_info(run_id)
        if info is None or info.status in ("completed", "rejected", "error"):
            return info
        return _reconcile(info, self._read_events(run_id))[0]

    def _read_info(self, run_id: str) -> RunInfo | None:
        if not RUN_ID.fullmatch(run_id):
            return None
        try:
            info = RunInfo.model_validate_json((self.root / run_id / "run.json").read_bytes())
        except (OSError, ValueError):
            return None
        return info if info.run_id == run_id else None

    def _read_events(self, run_id: str) -> list[ExecutionEvent]:
        try:
            lines = (self.root / run_id / "events.jsonl").read_bytes().splitlines()
        except OSError:
            return []
        events = []
        for line in lines:
            try:
                event = ExecutionEvent.model_validate_json(line)
            except ValueError:  # a crash can truncate the last line; skip anything undecodable
                continue
            # Keep file order and original sequence numbers (gaps may be lost lines).
            # First accepted sequence wins; a terminal event closes the accepted log.
            if event.run_id != run_id or event.seq <= (events[-1].seq if events else 0):
                continue
            events.append(event)
            if event.event_type in TERMINAL_EVENTS:
                break
        return events


def _reconcile(info: RunInfo, events: list[ExecutionEvent]) -> tuple[RunInfo, list[ExecutionEvent]]:
    last = events[-1] if events else None
    if info.status in ("completed", "rejected", "error"):
        if last is not None and last.event_type in TERMINAL_EVENTS:
            return info, events
        # A valid terminal summary survives a damaged/missing log. Recover only the
        # run outcome; do not invent lost agent results or write repairs to disk.
        seq = last.seq + 1 if last else 1
        stamp = info.finished_at or (last.timestamp if last else info.created_at)
        # Older/external JSON may omit an offset (the event schema allows it).
        # Treat those timestamps as UTC for recovery, without editing stored events.
        if stamp.tzinfo is None:
            stamp = stamp.replace(tzinfo=timezone.utc)
        if last is not None:
            last_stamp = last.timestamp if last.timestamp.tzinfo else last.timestamp.replace(tzinfo=timezone.utc)
            stamp = max(stamp, last_stamp)
        terminal = ExecutionEvent(
            seq=seq, event_id=f"evt_{seq:04d}", run_id=info.run_id, timestamp=stamp,
            event_type=next(kind for kind, status in _ENDED.items() if status == info.status),
            status=info.status, message=info.error or "Run outcome recovered from summary",
            data={"recovered": True},
        )
        return info, events + [terminal]
    if last is not None and last.event_type in TERMINAL_EVENTS:  # the log's terminal event wins over a stale run.json
        update: dict = {"status": _ENDED[last.event_type], "finished_at": last.timestamp}
        if last.event_type == EventType.run_failed and info.error is None:
            update["error"] = last.message
        return info.model_copy(update=update), events

    # Interrupted: close every node still "running" (same rule as the control plane's reducer), then the run.
    stamp: datetime = last.timestamp if last else info.created_at
    seq = last.seq if last else 0
    latest: dict[str, ExecutionEvent] = {}
    for e in events:
        if e.node_id and e.status and not e.event_type.value.startswith("handoff_"):
            latest.pop(e.node_id, None)  # re-insert: dict order == order of each node's last event
            latest[e.node_id] = e

    def synthetic(event_type: EventType, message: str, src: ExecutionEvent | None = None) -> ExecutionEvent:
        nonlocal seq
        seq += 1
        return ExecutionEvent(
            seq=seq,
            event_id=f"evt_{seq:04d}",
            run_id=info.run_id,
            timestamp=stamp,
            event_type=event_type,
            node_id=src.node_id if src else None,
            department=src.department if src else None,
            agent=src.agent if src else None,
            status="error",
            message=message,
            data={"interrupted": True},
        )

    tail = [synthetic(EventType.agent_failed, "Interrupted", e) for e in latest.values() if e.status == "running"]
    tail.append(synthetic(EventType.run_failed, INTERRUPTED))
    interrupted = info.model_copy(update={"status": "error", "error": INTERRUPTED, "finished_at": stamp})
    return interrupted, events + tail
