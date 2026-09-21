"""The organization graph: the single source of truth for the workflow.

    START -> head_ds -> [data_engineering] -> [analytics] -> [modeling] -> review -> report -> END

Each `[department]` is a real compiled LangGraph subgraph (`graphs/<department>.py`, built by
`steps.build_department`) added as a node of this graph; LangGraph itself runs the child agents.
The top-level order is `UNITS`. Everything else (nesting, edges, handoffs) is read back from the compiled
graph by `topology.build_topology`, which is what `/api/graph` serves.

Execution inside a department is sequential and deterministic; there is no parallelism or dynamic delegation.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from langgraph.graph import END, START, StateGraph

from datalab.agents import demo, head_ds, report, review_lead
from datalab.graphs import analytics, data_engineering, modeling
from datalab.graphs.spec import AgentSpec, DepartmentSpec, Unit
from datalab.graphs.steps import build_department, make_step
from datalab.graphs.topology import Topology, build_topology
from datalab.state import DataLabState

HEAD_DS = AgentSpec("head_ds", "Head of Data Science", "Plans the run", head_ds.run, type="orchestrator")
REVIEW = AgentSpec("review", "Review Lead", "Audits the methodology", review_lead.run, type="review", agent_id="review_lead")
REPORT = AgentSpec(
    "report", "Report", "Writes the report", report.run, type="report", agent_id="report_writer", demo=demo.run_report
)

UNITS: tuple[Unit, ...] = (HEAD_DS, data_engineering.SPEC, analytics.SPEC, modeling.SPEC, REVIEW, REPORT)


@cache
def get_graph():
    builder = StateGraph(DataLabState)
    for unit in UNITS:
        if isinstance(unit, DepartmentSpec):
            builder.add_node(unit.id, build_department(unit, topology))
        else:
            builder.add_node(unit.id, make_step(unit, unit.id, topology))
    builder.add_edge(START, UNITS[0].id)
    for a, b in zip(UNITS, UNITS[1:]):
        builder.add_edge(a.id, b.id)
    builder.add_edge(UNITS[-1].id, END)
    return builder.compile()


@cache
def topology() -> Topology:
    return build_topology(get_graph(), UNITS)


def graph_metadata() -> dict[str, Any]:
    """Serializable organization for the control plane: nodes (with `parent_id`) and edges (with `kind`)."""
    return topology().metadata()
