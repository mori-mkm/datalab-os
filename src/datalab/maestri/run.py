"""CLI: start a real DataLab run through the API only (never `RunService`/`get_graph()` in-process).

    python -m datalab.maestri.run --config problem.small [--no-llm] [--base-url URL] [--follow]
"""

from __future__ import annotations

import argparse
import sys

from datalab.maestri import client
from datalab.schemas.event import TERMINAL_EVENTS

NO_LLM_WARNING = "warning: backend is not running with DATALAB_LLM=off; head_ds/report may call the LLM"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Start a DataLab real run and watch it via the API.")
    parser.add_argument("--config", required=True, help="config name in configs/, e.g. problem.small")
    parser.add_argument("--no-llm", action="store_true", help="warn (does not block) if the server isn't DATALAB_LLM=off")
    parser.add_argument("--base-url", default=client.DEFAULT_BASE_URL)
    parser.add_argument("--follow", action="store_true", help="tail the run's event stream until it finishes")
    args = parser.parse_args(argv)

    # Event messages may carry Unicode (e.g. the "->" handoff arrow); legacy Windows consoles are
    # stuck on cp1252. Replace what can't be shown rather than crashing --follow mid-run. Same guard
    # as watch.py, applied at the same point (before any printing).
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")

    status = client.health(args.base_url)
    if args.no_llm and status["llm"]["mode"] != "off":
        print(NO_LLM_WARNING)

    run = client.create_run(args.base_url, mode="real", config=args.config)
    print(f"run_id={run.run_id} dataset={run.dataset} status={run.status}")

    if args.follow:
        for event in client.stream(args.base_url, run.run_id):
            print(f"[{event.seq}] {event.event_type} {event.node_id} {event.message}")
            if event.event_type in TERMINAL_EVENTS:
                break


if __name__ == "__main__":
    main()
