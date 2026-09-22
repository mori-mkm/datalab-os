"""Data Quality Analyst: turns the profile into quality findings (data_quality.json). Does not reload the data."""

from __future__ import annotations

from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.profiling import assess_quality


def run(ctx: RunContext, state: DataLabState) -> dict:
    if not state["dataset_profile"]:
        raise RuntimeError("data_quality_analyst needs the dataset profile from the data_profiler")
    ctx.status("Assessing missingness, duplicates and target balance")
    quality = assess_quality(state["dataset_profile"])
    ctx.status(f"{len(quality['issues'])} data-quality issue(s) found")
    name = ctx.save_json("data_quality.json", quality)
    return {"data_quality": quality, "artifacts": {name: name}, "_tools": ["assess_quality"]}
