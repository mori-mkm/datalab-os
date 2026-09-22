"""Thin httpx client over the existing FastAPI run API (`src/datalab/api/runs.py`).

HTTP only: no import of `datalab.services.*` / `datalab.graphs.*`. See
.claude/handoffs/maestri-bridge-contract.md for the full contract.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Iterator

import httpx

from datalab.schemas.event import ExecutionEvent
from datalab.schemas.run import RunInfo, RunMode

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def health(base_url: str = DEFAULT_BASE_URL) -> dict:
    response = httpx.get(f"{base_url}/health")
    response.raise_for_status()
    return response.json()


def create_run(base_url: str, mode: RunMode, config: str = "problem.example") -> RunInfo:
    response = httpx.post(f"{base_url}/api/runs", json={"mode": mode, "config": config})
    response.raise_for_status()
    return RunInfo(**response.json())


def get_run(base_url: str, run_id: str) -> RunInfo:
    response = httpx.get(f"{base_url}/api/runs/{run_id}")
    response.raise_for_status()
    return RunInfo(**response.json())


def list_runs(base_url: str, limit: int = 50) -> list[RunInfo]:
    response = httpx.get(f"{base_url}/api/runs", params={"limit": limit})
    response.raise_for_status()
    return [RunInfo(**item) for item in response.json()]


def _parse_sse(lines: Iterable[str]) -> Iterator[ExecutionEvent]:
    """Turn raw SSE `id:`/`data:` lines (per `format_sse` in `api/events.py`) into events.

    Blank line = dispatch. `: keepalive` comment lines and any frame missing a `data:` are skipped.
    """
    data_lines: list[str] = []
    for line in lines:
        if line == "":
            if data_lines:
                yield ExecutionEvent(**json.loads("\n".join(data_lines)))
            data_lines = []
        elif line.startswith("data:"):
            data_lines.append(line[len("data:") :].strip())
        # `id:` is redundant with `data.seq` and `:`-prefixed lines are comments/keepalives — both ignored.
    if data_lines:  # tolerate a final frame with no trailing blank line
        yield ExecutionEvent(**json.loads("\n".join(data_lines)))


def stream(base_url: str, run_id: str, last_event_id: int = 0) -> Iterator[ExecutionEvent]:
    """Open the run's SSE stream and yield `ExecutionEvent`s. Reconnect-on-drop is the caller's job."""
    headers = {"Last-Event-ID": str(last_event_id)}
    with httpx.stream("GET", f"{base_url}/api/runs/{run_id}/stream", headers=headers, timeout=None) as response:
        response.raise_for_status()
        yield from _parse_sse(response.iter_lines())
