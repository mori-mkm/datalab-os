import { beforeEach, describe, expect, it } from "vitest";
import { timelineOf } from "./timeline";
import { completed, ev, meta, resetSeq, started } from "./fixtures";
import type { ExecutionEvent } from "./types";

beforeEach(resetSeq);

describe("timelineOf", () => {
  it("every produced entry traces back to a real event seq in the input (no fabrication)", () => {
    const events = [
      ev("run_started", null, { data: { mode: "demo" } }),
      started("alpha.boss"),
      ev("agent_status", "alpha.boss", { message: "delegating" }),
      ev("artifact_created", "alpha.boss", { data: { artifact: "plan.json" } }),
      completed("alpha.boss"),
      ev("handoff_started", "alpha.boss", { target: "alpha.worker" }),
      ev("handoff_completed", "alpha.boss", { target: "alpha.worker" }),
      ev("review_started", "audit", {}),
      ev("review_completed", "audit", { data: { verdict: "APPROVED" } }),
      ev("run_completed", null, {}),
    ];
    const input = new Set(events.map((e) => e.seq));
    const entries = timelineOf(events, meta);
    for (const entry of entries) expect(input.has(entry.seq)).toBe(true);
  });

  it("maps agent_started/agent_status/artifact_created/handoff_*/review_*/run_* 1:1, in order", () => {
    const events: ExecutionEvent[] = [
      ev("run_started", null, {}),
      started("alpha.boss"),
      ev("agent_status", "alpha.boss", { message: "delegating" }),
      ev("artifact_created", "alpha.boss", { data: { artifact: "plan.json" } }),
      ev("handoff_started", "alpha.boss", { target: "alpha.worker" }),
      ev("handoff_completed", "alpha.boss", { target: "alpha.worker" }),
      ev("review_started", "audit", {}),
      ev("review_completed", "audit", { data: { verdict: "APPROVED" } }),
      ev("run_completed", null, {}),
    ];
    const entries = timelineOf(events, meta);
    expect(entries.map((e) => e.seq)).toEqual(events.map((e) => e.seq));
    expect(entries.map((e) => e.kind)).toEqual([
      "run",
      "task",
      "status",
      "artifact",
      "handoff",
      "handoff",
      "review",
      "review",
      "run",
    ]);
  });

  it("intentionally drops agent_completed/agent_failed: they carry no entry of their own", () => {
    const events = [started("alpha.boss"), completed("alpha.boss"), ev("agent_failed", "alpha.worker", {})];
    const entries = timelineOf(events, meta);
    expect(entries).toHaveLength(1); // only the agent_started survives
    expect(entries[0].kind).toBe("task");
  });

  it("groups run-level events under the 'Run' actor and node events under their label path", () => {
    const entries = timelineOf([ev("run_started", null, {}), started("alpha.boss")], meta);
    expect(entries[0].actor).toBe("Run");
    expect(entries[1].actor).toBe("Alpha Dept › Alpha Boss");
  });

  it("is empty for an empty event list", () => {
    expect(timelineOf([], meta)).toEqual([]);
  });
});
