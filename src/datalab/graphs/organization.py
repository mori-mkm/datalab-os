"""The organization graph: the single source of truth for the workflow.

`NODES` + `EDGES` build the LangGraph. `graph_metadata()` reads the *compiled* graph back, so the
control plane always draws what LangGraph will execute.

Each department is one node function today (`agents/<lead>.py::run`). That function is the seam where a
department becomes its own subgraph later; nothing else in this module has to change.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import cache
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from datalab.agents import analytics_lead, demo, ds_lead, engineering_lead, head_ds, report, review_lead
from datalab.schemas.event import EventType
from datalab.services.context import RunContext
from datalab.state import DataLabState

NodeFn = Callable[[RunContext, DataLabState], dict[str, Any]]


@dataclass(frozen=True)
class NodeSpec:
    id: str
    label: str
    role: str
    type: str  # orchestrator | department | report
    agent: str
    run: NodeFn


NODES: list[NodeSpec] = [
    NodeSpec("head_ds", "Head of Data Science", "Plans the run", "orchestrator", "head_ds", head_ds.run),
    NodeSpec("data_engineering", "Data Engineering", "Profiles the dataset", "department", "engineering_lead", engineering_lead.run),
    NodeSpec("analytics", "Analytics", "EDA and hypotheses", "department", "analytics_lead", analytics_lead.run),
    NodeSpec("modeling", "Data Science", "Trains the baseline model", "department", "ds_lead", ds_lead.run),
    NodeSpec("review", "Review", "Audits the methodology", "department", "review_lead", review_lead.run),
    NodeSpec("report", "Report", "Writes the report", "report", "report_writer", report.run),
]
EDGES: list[tuple[str, str]] = [(a.id, b.id) for a, b in zip(NODES, NODES[1:])]  # linear for the PoC


def _step(spec: NodeSpec) -> Callable[[DataLabState, RunnableConfig], dict[str, Any]]:
    """Wrap a node function with the events every node emits: start, handoffs, completion, failure."""
    sources = [s for s, t in EDGES if t == spec.id]
    targets = [t for s, t in EDGES if s == spec.id]

    def node(state: DataLabState, config: RunnableConfig) -> dict[str, Any]:
        base: RunContext = config["configurable"]["ctx"]
        ctx = base.scoped(spec.id, spec.agent)
        for source in sources:
            base.scoped(source, None).emit(EventType.handoff_completed, f"{source} -> {spec.id}", target=spec.id)
        ctx.emit(EventType.agent_started, f"{spec.label}: {spec.role}", status="running")
        try:
            fn = demo.run if ctx.mode == "demo" else spec.run
            update = fn(ctx, state)
        except Exception as exc:
            ctx.emit(EventType.agent_failed, f"{type(exc).__name__}: {exc}", status="error")
            raise
        node_status = update.pop("_node_status", "completed")
        ctx.emit(EventType.agent_completed, f"{spec.label} {node_status}", status=node_status)
        for target in targets:
            ctx.emit(EventType.handoff_started, f"{spec.id} -> {target}", target=target)
            ctx.pause(ctx.settings.handoff_delay)
        return {**update, "current_phase": spec.id}

    return node


@cache
def get_graph():
    builder = StateGraph(DataLabState)
    for spec in NODES:
        builder.add_node(spec.id, _step(spec))
    builder.add_edge(START, NODES[0].id)
    for source, target in EDGES:
        builder.add_edge(source, target)
    builder.add_edge(NODES[-1].id, END)
    return builder.compile()


def graph_metadata() -> dict[str, Any]:
    """Serializable graph for the control plane. Edges come from the compiled LangGraph."""
    drawn = get_graph().get_graph()
    order = {s.id: i for i, s in enumerate(NODES)}
    edges = [  # compiled edges are unordered; sort by node order so the payload is stable
        {"id": f"{e.source}->{e.target}", "source": e.source, "target": e.target}
        for e in sorted(drawn.edges, key=lambda e: (order.get(e.source, -1), order.get(e.target, -1)))
        if not e.source.startswith("__") and not e.target.startswith("__")
    ]
    nodes = [
        {"id": s.id, "label": s.label, "role": s.role, "type": s.type, "agent": s.agent}
        for s in NODES
        if s.id in drawn.nodes
    ]
    return {"nodes": nodes, "edges": edges}
