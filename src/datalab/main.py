"""Headless CLI: run the organization without the API or the control plane.

    python -m datalab.main --config configs/problem.example.yaml
    python -m datalab.main --demo
Exit code: 0 completed, 2 rejected by the review, 1 error.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from datalab.config import load_settings
from datalab.schemas.event import ExecutionEvent
from datalab.schemas.problem import load_problem
from datalab.services.run_service import RunService


def _print(event: ExecutionEvent) -> None:
    where = f" [{event.node_id}]" if event.node_id else ""
    print(f"{event.timestamp.astimezone():%H:%M:%S} {event.event_type.value:<18}{where} {event.message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="datalab", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path, help="problem YAML for a real run")
    group.add_argument("--demo", action="store_true", help="run the demo workflow (no data analysed)")
    parser.add_argument("--no-llm", action="store_true", help="never call Ollama (deterministic text)")
    args = parser.parse_args(argv)

    settings = load_settings()
    if args.no_llm:
        settings.llm_mode = "off"
    service = RunService(settings)
    info, state = service.create("demo" if args.demo else "real", None if args.demo else load_problem(args.config))
    service.bus.subscribe(info.run_id, _print)
    service.execute(info.run_id, state)
    print(f"\nrun {info.run_id}: {info.status}  (artifacts in {settings.workspace_dir / info.run_id})")
    return {"completed": 0, "rejected": 2}.get(info.status, 1)


if __name__ == "__main__":
    sys.exit(main())
