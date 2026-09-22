"""Hypothesis Analyst: derives data-driven hypotheses from the EDA (hypotheses.json). Association, not causation."""

from __future__ import annotations

from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.eda import derive_hypotheses


def run(ctx: RunContext, state: DataLabState) -> dict:
    if not state["eda"]:
        raise RuntimeError("hypothesis_analyst needs the EDA from the eda_analyst")
    ctx.status("Deriving hypotheses from correlations")
    hypotheses = derive_hypotheses(state["eda"])
    name = ctx.save_json(
        "hypotheses.json",
        {"hypotheses": hypotheses, "note": "Statistical associations only; no causal inference is made."},
    )
    return {"hypotheses": hypotheses, "artifacts": {name: name}, "_tools": ["derive_hypotheses"]}
