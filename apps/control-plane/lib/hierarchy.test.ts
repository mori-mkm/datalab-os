import { beforeEach, describe, expect, it } from "vitest";
import { applyEvent, initialView } from "./events";
import { completed, ev, meta, resetSeq, started } from "./fixtures";
import { childrenOf, completedAgentCount, departmentSummary, inputsFor, isContainer, labelPath, upstreamOf } from "./hierarchy";

beforeEach(resetSeq);

describe("hierarchy mapping (from backend metadata only)", () => {
  it("maps children to their department through parent_id", () => {
    expect(childrenOf(meta, "alpha").map((n) => n.id)).toEqual(["alpha.boss", "alpha.worker"]);
    expect(childrenOf(meta, "beta").map((n) => n.id)).toEqual(["beta.boss", "beta.worker", "beta.checker"]);
    expect(childrenOf(meta, "intake")).toEqual([]);
    expect(meta.nodes.filter(isContainer).map((n) => n.id)).toEqual(["alpha", "beta"]);
  });

  it("finds upstream executable nodes transitively, across departments", () => {
    expect(upstreamOf("beta.worker", meta)).toEqual(["beta.boss", "alpha.worker", "alpha.boss", "intake"]);
    expect(upstreamOf("intake", meta)).toEqual([]);
    expect(upstreamOf("audit", meta)).toContain("beta.checker");
  });

  it("builds readable labels without using labels as ids", () => {
    expect(labelPath(meta, "alpha.worker")).toBe("Alpha Dept › Alpha Worker");
    expect(labelPath(meta, "alpha")).toBe("Alpha Dept");
    expect(labelPath(meta, "intake")).toBe("Intake");
    expect(labelPath(meta, null)).toBe("");
    expect(labelPath(meta, "ghost")).toBe("ghost");
  });
});

describe("department parent data", () => {
  const view = [
    started("alpha"),
    started("alpha.boss"),
    ev("artifact_created", "alpha.boss", { data: { artifact: "a.json" } }),
    completed("alpha.boss"),
    started("alpha.worker"),
    ev("agent_status", "alpha.worker", { status: "running", message: "crunching" }),
    ev("artifact_created", "alpha.worker", { data: { artifact: "b.json" } }),
  ].reduce(applyEvent, initialView(meta, "r"));

  it("summarises its agents, the active one, aggregated artifacts and recent activity", () => {
    const summary = departmentSummary(meta, view, "alpha");
    expect(summary.agents).toEqual([
      { id: "alpha.boss", label: "Alpha Boss", status: "completed" },
      { id: "alpha.worker", label: "Alpha Worker", status: "running" },
    ]);
    expect(summary.activeAgent).toBe("alpha.worker");
    expect(summary.artifacts).toEqual(["a.json", "b.json"]);
    expect(summary.recent.map((e) => e.seq)).toEqual([...summary.recent.map((e) => e.seq)].sort((a, b) => a - b));
    expect(summary.recent.at(-1)?.event_type).toBe("artifact_created");
  });

  it("has no active agent when nothing runs, and empty data before the run starts", () => {
    expect(departmentSummary(meta, initialView(meta), "beta")).toMatchObject({ activeAgent: null, artifacts: [], recent: [] });
  });

  it("derives inputs from upstream artifacts, excluding the department's own", () => {
    expect(inputsFor(meta, view, "alpha")).toEqual([]); // nothing upstream produced anything
    expect(inputsFor(meta, view, "beta")).toEqual(["a.json", "b.json"]); // all of alpha, none of beta's own
    expect(inputsFor(meta, view, "alpha.worker")).toEqual(["a.json"]);
    expect(inputsFor(meta, view, "ghost")).toEqual([]);
  });

  it("counts only agent-type nodes that reached completed, not departments or running agents", () => {
    expect(completedAgentCount(meta, view)).toBe(1); // alpha.boss only: alpha.worker is still running
  });
});
