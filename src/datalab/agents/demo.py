"""Demo workflow: every executable node runs (the SAME topology as a real run), but only sleeps briefly and
writes a small, clearly-labelled placeholder.

It exists to validate the orchestration and the control plane. It analyses no data and produces no scientific
result; artifacts are named `*.demo.json` so they cannot be mistaken for real ones.
"""

from __future__ import annotations

from datalab.services.context import RunContext
from datalab.state import DataLabState

REPORT_TEXT = """# DEMO WORKFLOW

This run used the demo workflow: no dataset was read, no model was trained and no review was performed.
It only validates the orchestration (LangGraph), the event stream and the control plane.
"""


def _simulate(ctx: RunContext) -> None:
    delay = ctx.settings.demo_delay
    ctx.status("[demo] step 1/2: simulating work (no data is analysed)")
    ctx.pause(delay)
    ctx.status("[demo] step 2/2: writing demo artifact")
    ctx.pause(delay / 2)


def run(ctx: RunContext, state: DataLabState) -> dict:
    _simulate(ctx)
    name = ctx.save_json(
        f"{ctx.agent}.demo.json",
        {"mode": "demo", "node_id": ctx.node_id, "note": "placeholder produced by the demo workflow"},
    )
    return {"artifacts": {name: name}}


def run_report(ctx: RunContext, state: DataLabState) -> dict:
    _simulate(ctx)
    name = ctx.save_text("report.md", REPORT_TEXT)
    return {"status": "completed", "artifacts": {name: name}}
