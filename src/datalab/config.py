"""Runtime settings, read from environment variables (optionally via a .env file)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

ROOT = Path(os.environ.get("DATALAB_HOME") or Path(__file__).resolve().parents[2])


class Settings(BaseModel):
    root: Path = ROOT
    workspace_dir: Path = ROOT / "workspace"
    configs_dir: Path = ROOT / "configs"
    llm_mode: Literal["auto", "off"] = "auto"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:8b"
    handoff_delay: float = 0.6  # seconds a handoff stays "active" so it is visible in the UI
    demo_delay: float = 0.8  # seconds per step of the demo workflow
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


def load_settings() -> Settings:
    _load_dotenv(ROOT / ".env")
    env = os.environ.get
    fields: dict[str, object] = {}
    for key, name, cast in [
        ("llm_mode", "DATALAB_LLM", str),
        ("ollama_url", "DATALAB_OLLAMA_URL", str),
        ("ollama_model", "DATALAB_OLLAMA_MODEL", str),
        ("handoff_delay", "DATALAB_HANDOFF_DELAY", float),
        ("demo_delay", "DATALAB_DEMO_DELAY", float),
    ]:
        if env(name):
            fields[key] = cast(env(name))
    if env("DATALAB_CORS_ORIGINS"):
        fields["cors_origins"] = [o.strip() for o in env("DATALAB_CORS_ORIGINS", "").split(",") if o.strip()]
    return Settings(**fields)
