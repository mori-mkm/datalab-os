// GraphMeta (from the backend) + RunView (from events) -> React Flow nodes/edges.
import { MarkerType, type Edge, type Node } from "@xyflow/react";
import { formatDuration, type RunView } from "./events";
import type { GraphMeta, Status } from "./types";

export const NODE_WIDTH = 210;
export const NODE_HEIGHT = 84;
const RANK_GAP = 48;
const COLUMN_GAP = 40;

export interface AgentNodeData extends Record<string, unknown> {
  label: string;
  role: string;
  kind: string;
  status: Status;
  detail: string | null;
}

/** Layered top-to-bottom layout: rank = longest path from a source. Positions are visual only. */
export function layout(meta: GraphMeta): Record<string, { x: number; y: number }> {
  const rank: Record<string, number> = {};
  const rankOf = (id: string, seen: string[] = []): number => {
    if (rank[id] !== undefined) return rank[id];
    const parents = meta.edges.filter((e) => e.target === id && !seen.includes(e.source));
    return (rank[id] = parents.length ? 1 + Math.max(...parents.map((e) => rankOf(e.source, [...seen, id]))) : 0);
  };
  meta.nodes.forEach((n) => rankOf(n.id));

  const byRank = new Map<number, string[]>();
  meta.nodes.forEach((n) => byRank.set(rank[n.id], [...(byRank.get(rank[n.id]) ?? []), n.id]));

  const positions: Record<string, { x: number; y: number }> = {};
  byRank.forEach((ids, r) => {
    const width = ids.length * NODE_WIDTH + (ids.length - 1) * COLUMN_GAP;
    ids.forEach((id, i) => {
      positions[id] = { x: -width / 2 + i * (NODE_WIDTH + COLUMN_GAP), y: r * (NODE_HEIGHT + RANK_GAP) };
    });
  });
  return positions;
}

function nodeDetail(view: RunView, id: string, now: number): string | null {
  const node = view.nodes[id];
  if (!node || node.status === "waiting" || !node.startedAt) return null;
  return formatDuration(node.startedAt, node.endedAt ?? now);
}

export function buildNodes(meta: GraphMeta, view: RunView, now: number, positions: Record<string, { x: number; y: number }>): Node<AgentNodeData>[] {
  return meta.nodes.map((n) => ({
    id: n.id,
    type: "agent",
    width: NODE_WIDTH, // fixed size: React Flow treats the node as measured without a dimensions round-trip
    height: NODE_HEIGHT,
    position: positions[n.id] ?? { x: 0, y: 0 },
    data: {
      label: n.label,
      role: n.role,
      kind: n.type,
      status: view.nodes[n.id]?.status ?? "waiting",
      detail: nodeDetail(view, n.id, now),
    },
  }));
}

export function buildEdges(meta: GraphMeta, view: RunView): Edge[] {
  return meta.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    type: "execution",
    data: { state: view.edges[e.id] ?? "idle" },
    markerEnd: { type: MarkerType.ArrowClosed, width: 16, height: 16, color: "#8a94a6" },
  }));
}
