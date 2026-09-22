"""Builds LangGraph nodes and department subgraphs, wrapping every executable node with the events it emits.

Event order for one node (same for top-level nodes and agents inside a department):

    handoff_completed (from each predecessor)  ->  [department agent_started, if first in its department]
    -> agent_started -> ... agent_status / artifact_created ... -> agent_completed
    -> [department agent_completed, if last in its department] -> handoff_started (to each successor)

If the node raises: agent_failed for the node, then agent_failed for its department, then the exception
propagates out of the graph (the run service emits run_failed).

Neighbours (predecessors, successors, first/last in department) are looked up lazily in the topology read
back from the compiled graph, so events always match what `/api/graph` serves.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from datalab.agents import demo
from datalab.graphs.spec import AgentSpec, DepartmentSpec
from datalab.graphs.topology import Topology
from datalab.schemas.event import EventType
from datalab.services.context import RunContext
from datalab.state import DataLabState

TopologyProvider = Callable[[], Topology]
Step = Callable[[DataLabState, RunnableConfig], dict[str, Any]]


def make_step(spec: AgentSpec, node_id: str, topology: TopologyProvider) -> Step:
    def node(state: DataLabState, config: RunnableConfig) -> dict[str, Any]:
        base: RunContext = config["configurable"]["ctx"]
        topo = topology()
        me = topo.node(node_id)
        unit = topo.unit_of(node_id)
        department = topo.node(unit) if me.parent_id else None
        ctx = base.scoped(node_id, unit, spec.agent)
        dept_ctx = base.scoped(unit, unit, None)

        for source in topo.preds(node_id):
            src = topo.node(source)
            base.scoped(source, topo.unit_of(source), src.agent).emit(
                EventType.handoff_completed, f"{src.label} → {me.label}", target=node_id
            )
        if department and not topo.internal_preds(node_id):
            dept_ctx.emit(EventType.agent_started, f"{department.label}: {department.role}", status="running")
        ctx.emit(EventType.agent_started, f"{me.label}: {me.role}", status="running")

        try:
            fn = (spec.demo or demo.run) if ctx.mode == "demo" else spec.run
            update = fn(ctx, state)
        except Exception as exc:
            ctx.emit(EventType.agent_failed, f"{type(exc).__name__}: {exc}", status="error")
            if department:
                dept_ctx.emit(EventType.agent_failed, f"caused by {me.label}", status="error")
            raise

        node_status = update.pop("_node_status", "completed")
        tools = update.pop("_tools", [])
        ctx.emit(
            EventType.agent_completed,
            f"{me.label} {node_status}",
            status=node_status,
            **({"tools": tools} if tools else {}),
        )
        if department and not topo.internal_succs(node_id):
            dept_ctx.emit(EventType.agent_completed, f"{department.label} completed", status="completed")
        for target in topo.succs(node_id):
            ctx.emit(EventType.handoff_started, f"{me.label} → {topo.node(target).label}", target=target)
            ctx.pause(ctx.settings.handoff_delay)
        return {**update, "current_phase": node_id}

    return node


def build_department(spec: DepartmentSpec, topology: TopologyProvider):
    """A real compiled LangGraph subgraph: START -> agent_1 -> ... -> agent_n -> END."""
    builder = StateGraph(DataLabState)
    for agent in spec.agents:
        builder.add_node(agent.id, make_step(agent, spec.node_id(agent), topology))
    builder.add_edge(START, spec.agents[0].id)
    for a, b in zip(spec.agents, spec.agents[1:]):
        builder.add_edge(a.id, b.id)
    builder.add_edge(spec.agents[-1].id, END)
    return builder.compile()
