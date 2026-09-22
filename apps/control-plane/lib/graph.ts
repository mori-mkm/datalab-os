// GraphMeta (from the backend) + RunView (from events) -> React Flow nodes/edges.
import { MarkerType, type Edge, type Node } from "@xyflow/react";
import { formatDuration, type RunView } from "./events";
import { isContainer } from "./hierarchy";
import type { Layout, Point } from "./layout";
import type { GraphMeta, NodeType, Status } from "./types";

export interface GraphNodeData extends Record<string, unknown> {
  label: string;
  role: string;
  kind: NodeType;
  status: Status;
  detail: string | null;
}

function detail(view: RunView, id: string, now: number): string | null {
  const node = view.nodes[id];
  if (!node || node.status === "waiting" || !node.startedAt) return null;
  return formatDuration(node.startedAt, node.endedAt ?? now);
}

/** Parents come before their children (React Flow requires it). `moved` holds user-dragged positions (visual only). */
export function buildNodes(
  meta: GraphMeta,
  view: RunView,
  now: number,
  layoutResult: Layout,
  moved: Record<string, Point> = {},
  selected: string | null = null,
): Node<GraphNodeData>[] {
  const nodes = meta.nodes.map((n): Node<GraphNodeData> => ({
    id: n.id,
    type: isContainer(n) ? "department" : "agent",
    ...(n.parent_id ? { parentId: n.parent_id, extent: "parent" as const } : {}),
    // Fixed size. `measured` matters: nodes are rebuilt on every event, and React Flow drops a node's handle
    // bounds (so all its edges vanish until re-measured) when a new node object arrives without `measured`.
    width: layoutResult.sizes[n.id].width,
    height: layoutResult.sizes[n.id].height,
    measured: { width: layoutResult.sizes[n.id].width, height: layoutResult.sizes[n.id].height },
    position: moved[n.id] ?? layoutResult.positions[n.id] ?? { x: 0, y: 0 },
    selected: n.id === selected,
    data: {
      label: n.label,
      role: n.role,
      kind: n.type,
      status: view.nodes[n.id]?.status ?? "waiting",
      detail: detail(view, n.id, now),
    },
  }));
  return nodes.sort((a, b) => Number(Boolean(a.parentId)) - Number(Boolean(b.parentId)));
}

export function buildEdges(meta: GraphMeta, view: RunView, selected: string | null = null): Edge[] {
  return meta.edges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    // Agents inside a department flow left -> right. A handoff leaves a unit from the bottom and enters the next
    // agent from its left side, so the line wraps around the container instead of crossing its header text.
    sourceHandle: e.kind === "internal" ? "r" : "b",
    targetHandle: "l",
    type: "execution",
    zIndex: 10,
    selected: e.id === selected,
    data: { state: view.edges[e.id] ?? "idle", kind: e.kind },
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14, color: "#8a94a6" },
  }));
}
