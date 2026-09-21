// Read-only helpers over the graph metadata served by the backend (/api/graph).
// Nothing here knows any node name: hierarchy comes from `parent_id` and `type`, edges from the API.
import type { RunView } from "./events";
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

export interface DepartmentSummary {
  agents: { id: string; label: string; status: Status }[];
  /** The agent currently running, if any (taken from the events, not inferred). */
  activeAgent: string | null;
  artifacts: string[];
  recent: ExecutionEvent[];
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
