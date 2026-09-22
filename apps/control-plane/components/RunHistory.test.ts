import { describe, expect, it } from "vitest";
import type { RunInfo } from "../lib/types";
import { runLabel, runTitle } from "./RunHistory";

const run: RunInfo = { run_id: "run_20260101_120000_ab12", mode: "real", project_name: "Proj", status: "error", created_at: "2026-01-01T12:00:00Z" };

describe("history entry text", () => {
  it("shows short id, mode with dataset, status and start time", () => {
    const label = runLabel({ ...run, dataset: "sales.csv" });
    expect(label).toContain("#ab12");
    expect(label).toContain("real sales.csv");
    expect(label).toContain("error");
    expect(label).not.toContain("run_2026");
  });

  it("copes with a demo run without dataset or start time", () => {
    expect(runLabel({ ...run, mode: "demo", created_at: null })).toBe("#ab12 · demo · error · —");
  });

  it("puts project and the error text in the tooltip", () => {
    expect(runTitle({ ...run, error: "interrupted: boom" })).toBe("Proj — interrupted: boom");
    expect(runTitle(run)).toBe("Proj");
  });
});
