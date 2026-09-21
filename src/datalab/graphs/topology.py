"""The organization's topology, read back from the compiled LangGraph (never declared a second time).

Structure comes from the graph itself: `get_subgraphs()` says which top-level nodes are real subgraphs and
`get_graph(xray=True)` lists the executable nodes (`dept:agent`) and the edges between them, including the
cross-department handoffs. Specs only add display metadata (label, role, type), and the two must agree.

Node ids are machine ids: top-level nodes keep their own id, agents inside a department are
`<department>.<agent>`. The department container is a node too (`parent_id` is None, type `department`).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from datalab.graphs.spec import DepartmentSpec, Unit


@dataclass(frozen=True)
class TopoNode:
    id: str
    label: str
    role: str
    type: str
    agent: str | None
    parent_id: str | None


@dataclass(frozen=True)
class TopoEdge:
    id: str
    source: str
    target: str
    kind: str  # "internal": inside one department · "handoff": between top-level units


class Topology:
    def __init__(self, nodes: list[TopoNode], edges: list[TopoEdge]) -> None:
        self.nodes = tuple(nodes)
        self.edges = tuple(edges)
        self._by_id = {n.id: n for n in nodes}

    def node(self, node_id: str) -> TopoNode:
        return self._by_id[node_id]

    def unit_of(self, node_id: str) -> str:
        """Top-level unit an executable node belongs to (its department, or itself)."""
        return self._by_id[node_id].parent_id or node_id

    def preds(self, node_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == node_id]

    def succs(self, node_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == node_id]

    def internal_preds(self, node_id: str) -> list[str]:
        return [e.source for e in self.edges if e.target == node_id and e.kind == "internal"]

    def internal_succs(self, node_id: str) -> list[str]:
        return [e.target for e in self.edges if e.source == node_id and e.kind == "internal"]

    def metadata(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": n.id, "label": n.label, "role": n.role, "type": n.type, "agent": n.agent, "parent_id": n.parent_id}
                for n in self.nodes
            ],
            "edges": [{"id": e.id, "source": e.source, "target": e.target, "kind": e.kind} for e in self.edges],
        }


def build_topology(compiled: Any, units: tuple[Unit, ...]) -> Topology:
    nodes: list[TopoNode] = []
    for unit in units:
        if isinstance(unit, DepartmentSpec):
            nodes.append(TopoNode(unit.id, unit.label, unit.role, "department", None, None))
            nodes += [
                TopoNode(unit.node_id(a), a.label, a.role, a.type, a.agent, unit.id) for a in unit.agents
            ]
        else:
            nodes.append(TopoNode(unit.id, unit.label, unit.role, unit.type, unit.agent, None))

    if len({n.id for n in nodes}) != len(nodes):
        raise RuntimeError("node ids must be unique across the organization")
    drawn = compiled.get_graph(xray=True)
    executable = {n.id for n in nodes if not any(m.parent_id == n.id for m in nodes)}
    in_graph = {n.replace(":", ".") for n in drawn.nodes if not n.startswith("__")}
    departments = {name for name, _ in compiled.get_subgraphs()}
    declared_departments = {u.id for u in units if isinstance(u, DepartmentSpec)}
    if in_graph != executable or departments != declared_departments:
        raise RuntimeError(
            "specs and compiled graph disagree: "
            f"graph-only={sorted(in_graph - executable)}, spec-only={sorted(executable - in_graph)}, "
            f"subgraphs={sorted(departments)} vs departments={sorted(declared_departments)}"
        )

    order = {n.id: i for i, n in enumerate(nodes)}
    parent = {n.id: n.parent_id for n in nodes}
    pairs = sorted(
        {
            (e.source.replace(":", "."), e.target.replace(":", "."))
            for e in drawn.edges
            if not e.source.startswith("__") and not e.target.startswith("__")
        },
        key=lambda p: (order[p[0]], order[p[1]]),
    )
    edges = [
        TopoEdge(f"{s}->{t}", s, t, "internal" if parent[s] is not None and parent[s] == parent[t] else "handoff")
        for s, t in pairs
    ]
    return Topology(nodes, edges)

