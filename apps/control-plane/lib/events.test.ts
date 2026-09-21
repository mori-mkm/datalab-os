import { describe, expect, it } from "vitest";
import { applyEvent, formatDuration, initialView, upstreamOf } from "./events";
import type { EventType, ExecutionEvent, GraphMeta, Status } from "./types";

const meta: GraphMeta = {
  nodes: ["a", "b", "c"].map((id) => ({ id, label: id, role: "", type: "department", agent: id })),
  edges: [
    { id: "a->b", source: "a", target: "b" },
    { id: "b->c", source: "b", target: "c" },
  ],
};

let seq = 0;
const ev = (event_type: EventType, extra: Partial<ExecutionEvent> = {}): ExecutionEvent => ({
  seq: ++seq,
  event_id: `evt_${seq}`,
  run_id: "r",
  timestamp: `2026-01-01T00:00:${String(seq).padStart(2, "0")}Z`,
  event_type,
  department: null,
  agent: null,
  status: null,
  target: null,
  message: "",
  data: {},
  ...extra,
});
const fold = (events: ExecutionEvent[]) => events.reduce(applyEvent, initialView(meta, "r"));

describe("node status mapping", () => {
  it("starts every node as waiting", () => {
    const view = initialView(meta);
    expect(Object.values(view.nodes).map((n) => n.status)).toEqual(["waiting", "waiting", "waiting"]);
    expect(Object.values(view.edges)).toEqual(["idle", "idle"]);
  });

  it.each<[EventType, Status | null, Status]>([
    ["agent_started", "running", "running"],
    ["agent_completed", "completed", "completed"],
    ["agent_completed", "rejected", "rejected"],
    ["agent_failed", "error", "error"],
    ["review_completed", "rejected", "rejected"],
  ])("%s with status %s -> node %s", (type, status, expected) => {
    expect(fold([ev(type, { department: "a", status })]).nodes.a.status).toBe(expected);
  });

  it("does not change a node's status on handoff or artifact events", () => {
    const view = fold([
      ev("agent_completed", { department: "a", status: "completed" }),
      ev("handoff_started", { department: "a", target: "b" }),
      ev("artifact_created", { department: "a", data: { artifact: "x.json" } }),
    ]);
    expect(view.nodes.a.status).toBe("completed");
    expect(view.nodes.a.artifacts).toEqual(["x.json"]);
  });
});

describe("run + edges", () => {
  it("tracks task, timing and run status", () => {
    const view = fold([
      ev("run_started", { status: "running", data: { mode: "demo" } }),
      ev("agent_started", { department: "a", status: "running", message: "Start" }),
      ev("agent_status", { department: "a", status: "running", message: "Working" }),
      ev("agent_completed", { department: "a", status: "completed" }),
      ev("run_rejected", { status: "rejected" }),
    ]);
    expect(view.mode).toBe("demo");
    expect(view.nodes.a.task).toBe("Working");
    expect(view.nodes.a.startedAt).not.toBeNull();
    expect(view.nodes.a.endedAt).not.toBeNull();
    expect(view.status).toBe("rejected");
  });

  it("activates an edge on handoff_started and settles it on handoff_completed", () => {
    const started = fold([ev("handoff_started", { department: "a", target: "b" })]);
    expect(started.edges).toEqual({ "a->b": "active", "b->c": "idle" });
    const done = applyEvent(started, ev("handoff_completed", { department: "a", target: "b" }));
    expect(done.edges["a->b"]).toBe("done");
  });

  it("ignores events already applied (SSE replay)", () => {
    const first = ev("agent_started", { department: "a", status: "running" });
    const view = applyEvent(fold([first]), first);
    expect(view.events).toHaveLength(1);
  });
});

describe("helpers", () => {
  it("finds upstream nodes through the graph", () => {
    expect(upstreamOf("c", meta)).toEqual(["b", "a"]);
    expect(upstreamOf("a", meta)).toEqual([]);
  });

  it("formats durations", () => {
    expect(formatDuration("2026-01-01T00:00:00Z", "2026-01-01T00:00:12Z")).toBe("12s");
    expect(formatDuration("2026-01-01T00:00:00Z", "2026-01-01T00:01:12Z")).toBe("1m12s");
    expect(formatDuration(null, 5)).toBe("—");
  });
});
