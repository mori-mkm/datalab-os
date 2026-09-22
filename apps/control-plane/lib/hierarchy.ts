// Read-only helpers over the graph metadata served by the backend (/api/graph).
// Nothing here knows any node name: hierarchy comes from `parent_id` and `type`, edges from the API.
import type { EdgeState, RunView } from "./events";
import type { ExecutionEvent, GraphMeta, GraphNodeMeta, Status } from "./types";

export const isContainer = (node: GraphNodeMeta): boolean => node.type === "department";

export const childrenOf = (meta: GraphMeta, id: string): GraphNodeMeta[] => meta.nodes.filter((n) => n.parent_id === id);

/** Everything that can hand work to `nodeId`, transitively, in discovery order (executable nodes only). */
export function upstreamOf(nodeId: string, meta: GraphMeta): string[] {
  const seen: string[] = [];
  const queue = [nodeId];
  while (queue.length) {
    const current = queue.shift()!;
    for (const edge of meta.edges) {
      if (edge.target === current && !seen.includes(edge.source)) {
        seen.push(edge.source);
        queue.push(edge.source);
      }
    }
  }
  return seen;
}

/** "Data Engineering › Data Profiler" for a child, the plain label otherwise. */
export function labelPath(meta: GraphMeta, id: string | null): string {
  const node = meta.nodes.find((n) => n.id === id);
  if (!node) return id ?? "";
  const parent = node.parent_id ? meta.nodes.find((n) => n.id === node.parent_id) : null;
  return parent ? `${parent.label} › ${node.label}` : node.label;
}

/** Artifacts produced upstream of a node; for a department, upstream of its agents and outside the department. */
export function inputsFor(meta: GraphMeta, view: RunView, id: string): string[] {
  const node = meta.nodes.find((n) => n.id === id);
  if (!node) return [];
  const own = new Set(isContainer(node) ? childrenOf(meta, id).map((c) => c.id) : []);
  const roots = isContainer(node) ? [...own] : [id];
  const upstream = new Set(roots.flatMap((r) => upstreamOf(r, meta)).filter((u) => !own.has(u)));
  return meta.nodes.filter((n) => upstream.has(n.id)).flatMap((n) => view.nodes[n.id]?.artifacts ?? []); // flow order

}

export const completedAgentCount = (meta: GraphMeta, view: RunView): number =>
  meta.nodes.filter((n) => n.type === "agent" && view.nodes[n.id]?.status === "completed").length;

export interface DepartmentSummary {
  agents: { id: string; label: string; status: Status }[];
  /** The agent currently running, if any (taken from the events, not inferred). */
  activeAgent: string | null;
  artifacts: string[];
  recent: ExecutionEvent[];
}

export interface HandoffInfo {
  source: string;
  target: string;
  state: EdgeState;
  /** The sender's artifacts, which (per the emit order in graphs/steps.py) are always all produced before its
   * own `handoff_started` fires — no time-of-handoff filtering needed. */
  artifacts: string[];
  /** The sender's own last status/task message, reused verbatim (no new copy generated for the inspector). */
  summary: string | null;
  /** Timestamp of `handoff_completed` if it has happened yet, else of `handoff_started`, else null (idle edge). */
  timestamp: string | null;
}

/** Everything the Handoff Inspector needs for one edge, or null if `edgeId` isn't one of the backend's edges. */
export function handoffInfo(meta: GraphMeta, view: RunView, edgeId: string): HandoffInfo | null {
  const edge = meta.edges.find((e) => e.id === edgeId);
  if (!edge) return null;
  const handoffs = view.events.filter(
    (e) =>
      e.node_id === edge.source &&
      e.target === edge.target &&
      (e.event_type === "handoff_started" || e.event_type === "handoff_completed"),
  );
  return {
    source: edge.source,
    target: edge.target,
    state: view.edges[edgeId] ?? "idle",
    artifacts: view.nodes[edge.source]?.artifacts ?? [],
    summary: view.nodes[edge.source]?.task ?? null,
    timestamp: handoffs.at(-1)?.timestamp ?? null,
  };
}

export function departmentSummary(meta: GraphMeta, view: RunView, id: string): DepartmentSummary {
  const children = childrenOf(meta, id);
  const statusOf = (childId: string): Status => view.nodes[childId]?.status ?? "waiting";
  return {
    agents: children.map((c) => ({ id: c.id, label: c.label, status: statusOf(c.id) })),
    activeAgent: children.find((c) => statusOf(c.id) === "running")?.id ?? null,
    artifacts: children.flatMap((c) => view.nodes[c.id]?.artifacts ?? []),
    recent: children
      .flatMap((c) => view.nodes[c.id]?.recent ?? [])
      .filter((e) => e.event_type !== "handoff_completed")
      .sort((a, b) => a.seq - b.seq)
      .slice(-6),
  };
}
