"""Review lead: audits the modeling output. REJECTED marks the node (and the run) as rejected."""

from __future__ import annotations

from datalab.schemas.event import EventType
from datalab.schemas.problem import ProblemConfig
from datalab.services.context import RunContext
from datalab.state import DataLabState
from datalab.tools.review import review_experiments


def run(ctx: RunContext, state: DataLabState) -> dict:
    problem = ProblemConfig(**state["problem"])
    ctx.emit(EventType.review_started, "Reviewing methodology", status="running")
    result = review_experiments(
        problem, {"experiments": state["experiments"]}, state["eda"]
    )
    review = result.model_dump()
    failed = [c.name for c in result.checks if not c.passed]
    rejected = result.verdict == "REJECTED"
    ctx.emit(
        EventType.review_completed,
        f"Review {result.verdict}" + (f": failed {failed}" if failed else ""),
        status="rejected" if rejected else "running",
        verdict=result.verdict,
    )
    name = ctx.save_json("review.json", review)
    return {"review": review, "artifacts": {name: name}, "_node_status": "rejected" if rejected else "completed"}
