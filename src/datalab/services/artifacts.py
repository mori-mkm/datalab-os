"""Write run artifacts (JSON / YAML / text) under workspace/<run_id>/."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import yaml


def _scrub(obj: Any) -> Any:
    """Make pandas/numpy results strict-JSON safe (NaN/inf -> None, numpy scalars -> python)."""
    if isinstance(obj, dict):
        return {str(k): _scrub(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_scrub(v) for v in obj]
    if hasattr(obj, "item") and not isinstance(obj, (str, bytes)):  # numpy scalar
        obj = obj.item()
    if isinstance(obj, float) and not math.isfinite(obj):
        return None
    return obj


def write_json(run_dir: Path, name: str, obj: Any) -> Path:
    path = run_dir / name
    path.write_text(json.dumps(_scrub(obj), indent=2, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return path


def write_yaml(run_dir: Path, name: str, obj: Any) -> Path:
    path = run_dir / name
    path.write_text(yaml.safe_dump(_scrub(obj), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def write_text(run_dir: Path, name: str, text: str) -> Path:
    path = run_dir / name
    path.write_text(text, encoding="utf-8")
    return path


def read_json(run_dir: Path, name: str) -> Any:
    return json.loads((run_dir / name).read_text(encoding="utf-8"))
