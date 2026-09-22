"""Server-Sent Events transport for the event bus."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from datalab.schemas.event import TERMINAL_EVENTS, ExecutionEvent
from datalab.services.event_bus import EventBus

KEEPALIVE_SECONDS = 15


def format_sse(event: ExecutionEvent) -> str:
    # No `event:` field on purpose: the browser's EventSource.onmessage receives every event type.
    return f"id: {event.seq}\ndata: {event.model_dump_json()}\n\n"


async def replay_stream(events: list[ExecutionEvent], after: int = 0) -> AsyncIterator[str]:
    """Persisted (not live) run: the stored events with seq > `after`, then close (the log ends with a terminal event)."""
    for event in events:
        if event.seq > after:
            yield format_sse(event)


async def event_stream(bus: EventBus, run_id: str, after: int = 0) -> AsyncIterator[str]:
    """Replay history after `after`, then stream live events; ends after the run's terminal event."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()
    unsubscribe = bus.subscribe(run_id, lambda e: loop.call_soon_threadsafe(queue.put_nowait, e), after)
    try:
        # Subscribe first so a concurrent terminal emit cannot fall through a gap.
        history = bus.history(run_id)
        if history and history[-1].event_type in TERMINAL_EVENTS and history[-1].seq <= after:
            return
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), KEEPALIVE_SECONDS)
            except TimeoutError:
                yield ": keepalive\n\n"
                continue
            if event.seq > after:
                yield format_sse(event)
            if event.event_type in TERMINAL_EVENTS:
                return
    finally:
        unsubscribe()
