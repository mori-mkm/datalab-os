"""RunContext: what a node function gets. Emits events, writes artifacts, optionally asks the local LLM."""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from datalab.config import Settings
from datalab.llm import OllamaClient
from datalab.schemas.event import EventType
from datalab.schemas.run import RunMode, Status
from datalab.services import artifacts
from datalab.services.event_bus import EventBus


@dataclass(frozen=True)
class RunContext:
    run_id: str
    run_dir: Path
    mode: RunMode
    bus: EventBus
    settings: Settings
    department: str | None = None
    agent: str | None = None

    def scoped(self, department: str, agent: str | None) -> RunContext:
        return replace(self, department=department, agent=agent)

    def emit(
        self,
        event_type: EventType,
        message: str = "",
        *,
        status: Status | None = None,
        target: str | None = None,
        **data: Any,
    ) -> None:
        self.bus.emit(
            self.run_id,
            event_type,
            department=self.department,
            agent=self.agent,
            status=status,
            target=target,
            message=message,
            **data,
        )

    def status(self, message: str) -> None:
        """Progress update: becomes the agent's 'current task'."""
        self.emit(EventType.agent_status, message, status="running")

    def pause(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)

    def _saved(self, path: Path) -> str:
        self.emit(EventType.artifact_created, f"Artifact created: {path.name}", artifact=path.name)
        return path.name

    def save_json(self, name: str, obj: Any) -> str:
        return self._saved(artifacts.write_json(self.run_dir, name, obj))

    def save_yaml(self, name: str, obj: Any) -> str:
        return self._saved(artifacts.write_yaml(self.run_dir, name, obj))

    def save_text(self, name: str, text: str) -> str:
        return self._saved(artifacts.write_text(self.run_dir, name, text))

    def narrate(self, prompt: str, fallback: str) -> tuple[str, str]:
        """Return (text, source). The source is always explicit: an Ollama model or 'deterministic'."""
        if self.mode == "demo" or self.settings.llm_mode == "off":
            return fallback, "deterministic"
        client = OllamaClient(self.settings.ollama_url, self.settings.ollama_model)
        if not client.available():
            return fallback, "deterministic (ollama unavailable)"
        try:
            return client.generate(prompt), client.name
        except Exception as exc:  # network / model errors must not fail the run
            return fallback, f"deterministic (ollama failed: {type(exc).__name__})"
