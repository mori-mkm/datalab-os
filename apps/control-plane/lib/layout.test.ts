import { describe, expect, it } from "vitest";
import { meta } from "./fixtures";
import { absolutePosition, layout, type Layout } from "./layout";
import type { GraphMeta } from "./types";

const rect = (id: string, l: Layout, m: GraphMeta) => {
  const p = absolutePosition(id, m, l);
  return { id, x: p.x, y: p.y, w: l.sizes[id].width, h: l.sizes[id].height };
};
const overlap = (a: ReturnType<typeof rect>, b: ReturnType<typeof rect>) =>
  a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;

describe("hierarchical layout", () => {
  const result = layout(meta);
  const topLevel = meta.nodes.filter((n) => n.parent_id === null);

  it("is deterministic: same metadata, same layout (page reload stability)", () => {
    expect(layout(meta)).toEqual(result);
    expect(layout(JSON.parse(JSON.stringify(meta)))).toEqual(result);
  });

  it("gives every node a position and a size", () => {
    for (const n of meta.nodes) {
      expect(result.positions[n.id]).toBeDefined();
      expect(result.sizes[n.id].width).toBeGreaterThan(0);
    }
  });

  it("never overlaps top-level units", () => {
    const rects = topLevel.map((n) => rect(n.id, result, meta));
    rects.forEach((a, i) => rects.slice(i + 1).forEach((b) => expect(overlap(a, b), `${a.id} vs ${b.id}`).toBe(false)));
  });

  it("fits every child inside its container, with padding, and never overlaps siblings", () => {
    for (const dept of meta.nodes.filter((n) => n.type === "department")) {
      const box = rect(dept.id, result, meta);
      const kids = meta.nodes.filter((n) => n.parent_id === dept.id).map((n) => rect(n.id, result, meta));
      kids.forEach((k) => {
        expect(k.x).toBeGreaterThanOrEqual(box.x + 8);
        expect(k.y).toBeGreaterThanOrEqual(box.y + 30); // room for the department header
        expect(k.x + k.w).toBeLessThanOrEqual(box.x + box.w - 8);
        expect(k.y + k.h).toBeLessThanOrEqual(box.y + box.h - 8);
      });
      kids.forEach((a, i) => kids.slice(i + 1).forEach((b) => expect(overlap(a, b), `${a.id} vs ${b.id}`).toBe(false)));
    }
  });

  it("keeps the top-level sequence readable: rows follow the flow, children flow left to right", () => {
    const y = (id: string) => result.positions[id].y;
    expect(y("intake")).toBeLessThan(y("alpha"));
    expect(y("alpha")).toBeLessThan(y("beta"));
    expect(y("beta")).toBeLessThan(y("audit"));
    expect(result.positions["alpha.boss"].x).toBeLessThan(result.positions["alpha.worker"].x);
    expect(result.positions["alpha.boss"].y).toBe(result.positions["alpha.worker"].y);
  });

  it("stacks parallel agents of the same rank in rows, inside the container", () => {
    expect(result.positions["beta.worker"].x).toBe(result.positions["beta.checker"].x);
    expect(result.positions["beta.worker"].y).toBeLessThan(result.positions["beta.checker"].y);
  });

  it("uses positions relative to the parent for children, absolute for top-level nodes", () => {
    expect(result.positions["alpha.boss"].x).toBeLessThan(40);
    expect(absolutePosition("alpha.boss", meta, result).y).toBe(result.positions["alpha"].y + result.positions["alpha.boss"].y);
  });

  it("does not depend on any node name: a flat graph still lays out top to bottom", () => {
    const flat: GraphMeta = {
      nodes: ["p", "q", "r"].map((id) => ({ id, label: id, role: "", type: "agent", agent: id, parent_id: null })),
      edges: [
        { id: "p->q", source: "p", target: "q", kind: "handoff" },
        { id: "q->r", source: "q", target: "r", kind: "handoff" },
      ],
    };
    const l = layout(flat);
    expect(l.positions.p.y).toBeLessThan(l.positions.q.y);
    expect(l.positions.q.y).toBeLessThan(l.positions.r.y);
  });
});
