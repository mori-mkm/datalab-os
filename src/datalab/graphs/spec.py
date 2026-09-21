"""Declarative pieces of the organization: who exists, what they are called, what they run.

Structure (which nodes exist, nesting, edges) is NOT stored here: it lives in the compiled LangGraph and is
read back by `topology.py`. Specs only carry display metadata and the node function.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from datalab.services.context import RunContext
from datalab.state import DataLabState

NodeFn = Callable[[RunContext, DataLabState], dict[str, Any]]

# Ids are machine ids: they are joined with "." (department.agent) and LangGraph joins namespaces with ":",
# so neither may appear inside an id.
_ID = re.compile(r"[a-z][a-z0-9_]*")


def _check_id(value: str) -> None:
    if not _ID.fullmatch(value):
        raise ValueError(f"invalid node id {value!r}: use lowercase letters, digits and underscores")


@dataclass(frozen=True)
class AgentSpec:
    id: str  # local node name: unique inside its department (or in the organization for top-level agents)
    label: str
    role: str
    run: NodeFn
    type: str = "agent"  # agent | orchestrator | review | report
    agent_id: str | None = None  # name used in events; defaults to `id`
    demo: NodeFn | None = None  # demo-mode behaviour; None = the generic placeholder in agents/demo.py

    def __post_init__(self) -> None:
        _check_id(self.id)

    @property
    def agent(self) -> str:
        return self.agent_id or self.id


@dataclass(frozen=True)
class DepartmentSpec:
    id: str
    label: str
    role: str
    agents: tuple[AgentSpec, ...]  # executed in this order (linear subgraph)

    def __post_init__(self) -> None:
        _check_id(self.id)
        if not self.agents:
            raise ValueError(f"department {self.id!r} has no agents")
        if len({a.id for a in self.agents}) != len(self.agents):
            raise ValueError(f"department {self.id!r} has duplicate agent ids")

    def node_id(self, agent: AgentSpec) -> str:
        return f"{self.id}.{agent.id}"


Unit = AgentSpec | DepartmentSpec
