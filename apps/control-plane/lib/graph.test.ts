import { beforeEach, describe, expect, it } from "vitest";
import { applyEvent, initialView } from "./events";
import { completed, ev, meta, resetSeq, started } from "./fixtures";
import { buildEdges, buildNodes } from "./graph";
import { layout } from "./layout";

beforeEach(resetSeq);
const computed = layout(meta);

describe("buildNodes", () => {
  const nodes = buildNodes(meta, initialView(meta), 0, computed);
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));

  it("renders departments as containers and agents as children through React Flow parentId", () => {
    expect(byId["alpha"].type).toBe("department");
    expect(byId["alpha"].parentId).toBeUndefined();
    expect(byId["alpha.boss"]).toMatchObject({ type: "agent", parentId: "alpha", extent: "parent" });
    expect(byId["intake"]).toMatchObject({ type: "agent" });
    expect(byId["intake"].parentId).toBeUndefined();
  });

  it("puts every parent before its children", () => {
    const order = nodes.map((n) => n.id);
    for (const n of nodes) if (n.parentId) expect(order.indexOf(n.parentId)).toBeLessThan(order.indexOf(n.id));
  });

  it("creates exactly the nodes of the metadata: nothing is hardcoded in the frontend", () => {
    expect(nodes.map((n) => n.id).sort()).toEqual(meta.nodes.map((n) => n.id).sort());
    expect(byId["beta.checker"].data.label).toBe("Beta Checker");
  });

  it("carries status (container and child independently), duration and selection", () => {
    const view = [started("alpha"), started("alpha.boss")].reduce(applyEvent, initialView(meta, "r"));
    const built = Object.fromEntries(buildNodes(meta, view, Date.parse("2026-01-01T00:00:10Z"), computed, {}, "alpha.boss").map((n) => [n.id, n]));
    expect(built["alpha"].data.status).toBe("running");
    expect(built["alpha.boss"].data).toMatchObject({ status: "running", detail: "8s" });
    expect(built["alpha.worker"].data).toMatchObject({ status: "waiting", detail: null });
    expect(built["alpha.boss"].selected).toBe(true);
    expect(built["alpha"].selected).toBe(false);
  });

  it("applies user-dragged positions visually only", () => {
    const moved = buildNodes(meta, initialView(meta), 0, computed, { "alpha.boss": { x: 99, y: 77 } });
    expect(moved.find((n) => n.id === "alpha.boss")!.position).toEqual({ x: 99, y: 77 });
    expect(computed.positions["alpha.boss"]).not.toEqual({ x: 99, y: 77 });
  });
});

describe("buildEdges", () => {
  it("uses the backend edges as they are and picks handles by kind", () => {
    const edges = buildEdges(meta, initialView(meta));
    expect(edges.map((e) => e.id)).toEqual(meta.edges.map((e) => e.id));
    const internal = edges.find((e) => e.id === "alpha.boss->alpha.worker")!;
    expect([internal.sourceHandle, internal.targetHandle]).toEqual(["r", "l"]);
    const handoff = edges.find((e) => e.id === "alpha.worker->beta.boss")!;
    expect([handoff.sourceHandle, handoff.targetHandle]).toEqual(["b", "l"]);
  });

  it("reflects internal and cross-department edge states from events", () => {
    const view = [
      ev("handoff_started", "alpha.boss", { target: "alpha.worker" }),
      ev("handoff_completed", "alpha.boss", { target: "alpha.worker" }),
      completed("alpha.worker"),
      ev("handoff_started", "alpha.worker", { target: "beta.boss" }),
    ].reduce(applyEvent, initialView(meta, "r"));
    const state = Object.fromEntries(buildEdges(meta, view).map((e) => [e.id, (e.data as { state: string }).state]));
    expect(state["alpha.boss->alpha.worker"]).toBe("done");
    expect(state["alpha.worker->beta.boss"]).toBe("active");
    expect(state["intake->alpha.boss"]).toBe("idle");
  });
});
