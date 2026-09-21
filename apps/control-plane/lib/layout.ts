// Deterministic hierarchical layout, computed only from the graph metadata (parent_id + edges).
//   - top-level units (department containers and standalone nodes) flow top -> bottom by rank;
//   - inside a department its agents flow left -> right by rank;
//   - child positions are relative to their container (React Flow parent/child semantics).
// No randomness and no dependency on execution order or on any node name.
import type { GraphMeta, GraphNodeMeta } from "./types";

export const TOP_SIZE = { width: 208, height: 84 };
export const CHILD_SIZE = { width: 176, height: 64 };
const PAD = 14;
const HEADER = 42;
const CHILD_GAP = { x: 40, y: 16 };
const UNIT_GAP = 40;

export interface Point {
  x: number;
  y: number;
}
export interface Size {
  width: number;
  height: number;
}
export interface Layout {
  /** Absolute for top-level nodes/containers, relative to the parent for children. */
  positions: Record<string, Point>;
  sizes: Record<string, Size>;
}

/** rank = longest path from a source, ignoring anything outside `ids`. Cycle-safe. */
function ranks(ids: string[], edges: [string, string][]): Record<string, number> {
  const rank: Record<string, number> = {};
  const rankOf = (id: string, path: string[]): number => {
    if (rank[id] !== undefined) return rank[id];
    const parents = edges.filter(([s, t]) => t === id && ids.includes(s) && !path.includes(s));
    return (rank[id] = parents.length ? 1 + Math.max(...parents.map(([s]) => rankOf(s, [...path, id]))) : 0);
  };
  ids.forEach((id) => rankOf(id, []));
  return rank;
}

function groupBy<T>(items: T[], key: (item: T) => number): T[][] {
  const groups = new Map<number, T[]>();
  items.forEach((item) => groups.set(key(item), [...(groups.get(key(item)) ?? []), item]));
  return [...groups.keys()].sort((a, b) => a - b).map((k) => groups.get(k)!);
}

export function layout(meta: GraphMeta): Layout {
  const positions: Record<string, Point> = {};
  const sizes: Record<string, Size> = {};
  const unitOf = (id: string) => meta.nodes.find((n) => n.id === id)?.parent_id ?? id;
  const topLevel = meta.nodes.filter((n) => n.parent_id === null);

  // 1. inside each department
  for (const unit of topLevel) {
    const children = meta.nodes.filter((n) => n.parent_id === unit.id);
    if (!children.length) {
      sizes[unit.id] = TOP_SIZE;
      continue;
    }
    const ids = children.map((c) => c.id);
    const rank = ranks(ids, meta.edges.map((e) => [e.source, e.target]));
    const columns = groupBy(children, (c) => rank[c.id]);
    columns.forEach((column, x) =>
      column.forEach((child, y) => {
        positions[child.id] = {
          x: PAD + x * (CHILD_SIZE.width + CHILD_GAP.x),
          y: HEADER + y * (CHILD_SIZE.height + CHILD_GAP.y),
        };
        sizes[child.id] = CHILD_SIZE;
      }),
    );
    const rows = Math.max(...columns.map((c) => c.length));
    sizes[unit.id] = {
      width: 2 * PAD + columns.length * CHILD_SIZE.width + (columns.length - 1) * CHILD_GAP.x,
      height: HEADER + rows * CHILD_SIZE.height + (rows - 1) * CHILD_GAP.y + PAD,
    };
  }

  // 2. top-level units: collapse executable edges to unit level, rank, stack rows
  const unitEdges: [string, string][] = meta.edges
    .map((e): [string, string] => [unitOf(e.source), unitOf(e.target)])
    .filter(([s, t]) => s !== t);
  const unitRank = ranks(topLevel.map((u) => u.id), unitEdges);
  let y = 0;
  for (const row of groupBy<GraphNodeMeta>(topLevel, (u) => unitRank[u.id])) {
    const width = row.reduce((sum, u) => sum + sizes[u.id].width, 0) + (row.length - 1) * UNIT_GAP;
    let x = -width / 2;
    for (const unit of row) {
      positions[unit.id] = { x, y };
      x += sizes[unit.id].width + UNIT_GAP;
    }
    y += Math.max(...row.map((u) => sizes[u.id].height)) + UNIT_GAP;
  }
  return { positions, sizes };
}

export function absolutePosition(id: string, meta: GraphMeta, layoutResult: Layout): Point {
  const node = meta.nodes.find((n) => n.id === id);
  const own = layoutResult.positions[id] ?? { x: 0, y: 0 };
  if (!node?.parent_id) return own;
  const parent = layoutResult.positions[node.parent_id] ?? { x: 0, y: 0 };
  return { x: parent.x + own.x, y: parent.y + own.y };
}
