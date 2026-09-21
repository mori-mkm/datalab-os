import { beforeEach, describe, expect, it } from "vitest";
import { applyEvent, formatDuration, initialView } from "./events";
import { completed, ev, meta, resetSeq, started } from "./fixtures";
import type { ExecutionEvent, Status } from "./types";

beforeEach(resetSeq);
const fold = (events: ExecutionEvent[]) => events.reduce(applyEvent, initialView(meta, "r"));

describe("initial view", () => {
  it("has a waiting entry for every node of the graph (containers included) and an idle edge for every edge", () => {
    const view = initialView(meta);
    expect(Object.keys(view.nodes)).toEqual(meta.nodes.map((n) => n.id));
    expect(new Set(Object.values(view.nodes).map((n) => n.status))).toEqual(new Set(["waiting"]));
    expect(Object.keys(view.edges)).toEqual(meta.edges.map((e) => e.id));
    expect(new Set(Object.values(view.edges))).toEqual(new Set(["idle"]));
  });
});

describe("child agents, keyed by node_id", () => {
  it("tracks start, status updates, artifacts and completion of a child without touching its siblings", () => {
    const view = fold([
      started("alpha.boss"),
      ev("agent_status", "alpha.boss", { status: "running", message: "delegating" }),
      ev("artifact_created", "alpha.boss", { data: { artifact: "plan.json" } }),
      ev("artifact_created", "alpha.boss", { data: { artifact: "plan.json" } }), // duplicate name is listed once
      completed("alpha.boss"),
    ]);
    const boss = view.nodes["alpha.boss"];
    expect(boss.status).toBe("completed");
    expect(boss.task).toBe("delegating");
    expect(boss.artifacts).toEqual(["plan.json"]);
    expect(boss.startedAt).not.toBeNull();
    expect(boss.endedAt).not.toBeNull();
    expect(view.nodes["alpha.worker"].status).toBe("waiting");
    expect(view.nodes["alpha"].status).toBe("waiting"); // the container only changes on its own lifecycle events
    expect(view.nodes["alpha"].artifacts).toEqual([]);
  });

  it.each<[ExecutionEvent["event_type"], Status | null, Status]>([
    ["agent_started", "running", "running"],
    ["agent_completed", "completed", "completed"],
    ["agent_completed", "rejected", "rejected"],
    ["agent_failed", "error", "error"],
    ["review_completed", "rejected", "rejected"],
  ])("%s with status %s -> node %s", (type, status, expected) => {
    resetSeq();
    expect(fold([ev(type, "alpha.worker", { status })]).nodes["alpha.worker"].status).toBe(expected);
  });

  it("creates a blank entry for a node the graph did not announce instead of crashing", () => {
    expect(fold([started("gamma.unknown")]).nodes["gamma.unknown"].status).toBe("running");
  });
});

describe("department lifecycle", () => {
  it("takes the container's status from the backend's lifecycle events, not from its children", () => {
    const running = fold([started("alpha"), started("alpha.boss"), completed("alpha.boss"), started("alpha.worker")]);
    expect(running.nodes["alpha"].status).toBe("running");
    const done = applyEvent(applyEvent(running, completed("alpha.worker")), completed("alpha"));
    expect(done.nodes["alpha"].status).toBe("completed");
    expect(done.nodes["alpha"].endedAt).not.toBeNull();
  });

  it("marks the container and the failing child as error", () => {
    const view = fold([started("alpha"), started("alpha.boss"), ev("agent_failed", "alpha.boss", { status: "error" }), ev("agent_failed", "alpha", { status: "error" })]);
    expect(view.nodes["alpha"].status).toBe("error");
    expect(view.nodes["alpha.boss"].status).toBe("error");
    expect(view.nodes["alpha.worker"].status).toBe("waiting");
  });
});

describe("handoffs and edges", () => {
  it("activates an internal edge on handoff_started and settles it on handoff_completed", () => {
    const active = fold([ev("handoff_started", "alpha.boss", { target: "alpha.worker" })]);
    expect(active.edges["alpha.boss->alpha.worker"]).toBe("active");
    const done = applyEvent(active, ev("handoff_completed", "alpha.boss", { target: "alpha.worker" }));
    expect(done.edges["alpha.boss->alpha.worker"]).toBe("done");
  });

  it("handles cross-department handoffs between executable nodes, leaving other edges alone", () => {
    const view = fold([ev("handoff_started", "alpha.worker", { target: "beta.boss" })]);
    expect(view.edges["alpha.worker->beta.boss"]).toBe("active");
    expect(view.edges["intake->alpha.boss"]).toBe("idle");
    expect(view.edges["beta.boss->beta.worker"]).toBe("idle");
  });

  it("does not change any node status on handoff events", () => {
    const view = fold([completed("alpha.worker"), ev("handoff_started", "alpha.worker", { target: "beta.boss", status: "running" })]);
    expect(view.nodes["alpha.worker"].status).toBe("completed");
  });

  it("supports fan-out: two edges leaving one node are independent", () => {
    const view = fold([ev("handoff_started", "beta.boss", { target: "beta.worker" }), ev("handoff_completed", "beta.boss", { target: "beta.worker" })]);
    expect(view.edges["beta.boss->beta.worker"]).toBe("done");
    expect(view.edges["beta.boss->beta.checker"]).toBe("idle");
  });
});

describe("run status", () => {
  it("follows run-level events, including rejection and failure", () => {
    expect(fold([ev("run_started", null, { status: "running", data: { mode: "demo" } })])).toMatchObject({ status: "running", mode: "demo" });
    expect(fold([ev("run_started", null, { status: "running" }), ev("run_rejected", null, { status: "rejected" })])).toMatchObject({ status: "rejected" });
    expect(fold([ev("run_failed", null, { status: "error" })]).endedAt).not.toBeNull();
    expect(fold([ev("run_completed", null, { status: "completed" })]).status).toBe("completed");
  });

  it("shows a rejected review while the earlier departments stay completed", () => {
    const view = fold([completed("alpha"), completed("beta"), ev("review_completed", "audit", { status: "rejected", message: "REJECTED" }), completed("audit", "rejected"), ev("run_rejected", null, { status: "rejected" })]);
    expect(view.nodes["audit"].status).toBe("rejected");
    expect(view.nodes["alpha"].status).toBe("completed");
    expect(view.status).toBe("rejected");
  });
});

describe("replay", () => {
  it("ignores events already applied (SSE replay after a reconnect)", () => {
    const events = [started("alpha"), started("alpha.boss"), completed("alpha.boss")];
    const once = fold(events);
    const replayed = events.reduce(applyEvent, once);
    expect(replayed).toBe(once); // same reference: nothing changed
    expect(replayed.events).toHaveLength(3);
  });

  it("rebuilds the same view from a full replay as from live delivery", () => {
    const events = [started("alpha"), started("alpha.boss"), ev("handoff_started", "alpha.boss", { target: "alpha.worker" }), completed("alpha.boss")];
    expect(fold(events)).toEqual(events.reduce(applyEvent, applyEvent(initialView(meta, "r"), events[0])));
  });

  it("keeps only a bounded amount of recent activity per node", () => {
    const view = fold(Array.from({ length: 12 }, () => ev("agent_status", "alpha.boss", { status: "running", message: "tick" })));
    expect(view.nodes["alpha.boss"].recent).toHaveLength(6);
    expect(view.events).toHaveLength(12);
  });
});

describe("formatDuration", () => {
  it("formats seconds and minutes", () => {
    expect(formatDuration("2026-01-01T00:00:00Z", "2026-01-01T00:00:12Z")).toBe("12s");
    expect(formatDuration("2026-01-01T00:00:00Z", "2026-01-01T00:01:12Z")).toBe("1m12s");
    expect(formatDuration(null, 5)).toBe("—");
  });
});
