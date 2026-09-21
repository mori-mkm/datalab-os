"""In-process event bus. Agents/graphs only call `emit`; the transport (SSE, CLI print, ...) is a listener."""

from __future__ import annotations

import threading
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from datalab.schemas.event import EventType, ExecutionEvent
from datalab.schemas.run import Status

Listener = Callable[[ExecutionEvent], None]


class EventBus:
    """Thread-safe. Graphs run in worker threads; listeners must not block (e.g. `loop.call_soon_threadsafe`)."""

    # ponytail: history is kept in memory for the process lifetime; persist to workspace/<run>/events.jsonl for run history (MVP).
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, list[ExecutionEvent]] = {}
        self._listeners: dict[str, list[Listener]] = {}

    def emit(
        self,
        run_id: str,
        event_type: EventType,
        *,
        department: str | None = None,
        agent: str | None = None,
        status: Status | None = None,
        target: str | None = None,
        message: str = "",
        **data: Any,
    ) -> ExecutionEvent:
        with self._lock:
            history = self._events.setdefault(run_id, [])
            seq = len(history) + 1
            event = ExecutionEvent(
                seq=seq,
                event_id=f"evt_{seq:04d}",
                run_id=run_id,
                timestamp=datetime.now(timezone.utc),
                event_type=event_type,
                department=department,
                agent=agent,
                status=status,
                target=target,
                message=message,
                data=data,
            )
            history.append(event)
            for listener in list(self._listeners.get(run_id, [])):
                listener(event)
        return event

    def history(self, run_id: str) -> list[ExecutionEvent]:
        with self._lock:
            return list(self._events.get(run_id, []))

    def subscribe(self, run_id: str, listener: Listener, after: int = 0) -> Callable[[], None]:
        """Replay events with seq > `after`, then deliver live ones (no gap: both happen under the lock)."""
        with self._lock:
            for event in self._events.get(run_id, [])[after:]:
                listener(event)
            self._listeners.setdefault(run_id, []).append(listener)

        def unsubscribe() -> None:
            with self._lock:
                if listener in self._listeners.get(run_id, []):
                    self._listeners[run_id].remove(listener)

        return unsubscribe
