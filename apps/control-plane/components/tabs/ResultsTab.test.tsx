// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ResultsTab } from "./ResultsTab";
import * as api from "@/lib/api";
import { applyEvent, initialView } from "@/lib/events";
import { ev, meta, resetSeq } from "@/lib/fixtures";
import type { RunInfo } from "@/lib/types";

vi.mock("@/lib/api", () => ({ getArtifact: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  resetSeq();
});

const run: RunInfo = { run_id: "run_1", mode: "real", project_name: "churn", status: "completed", review_verdict: "APPROVED" };

const viewWith = (names: string[]) =>
  names.map((name) => ev("artifact_created", "alpha.boss", { data: { artifact: name } })).reduce(applyEvent, initialView(meta, "run_1"));

describe("ResultsTab", () => {
  it("shows model, primary metric, full metrics table and an APPROVED banner", async () => {
    vi.mocked(api.getArtifact).mockImplementation(async (_runId, name) =>
      name === "model_evaluation.json"
        ? JSON.stringify({ selected_model: "baseline_logreg", primary_metric: "roc_auc", metrics: { roc_auc: 0.827, f1: 0.667 } })
        : JSON.stringify({ experiments: [{ id: "baseline_logreg" }] }),
    );
    render(<ResultsTab view={viewWith(["model_evaluation.json", "experiments.json"])} run={run} now={0} />);
    expect(await screen.findByText("baseline_logreg")).toBeTruthy();
    expect(await screen.findByText("roc_auc = 0.827")).toBeTruthy();
    expect(await screen.findByText("0.667")).toBeTruthy();
    expect(screen.getByText("APPROVED")).toBeTruthy();
  });

  it("shows REJECTED just as prominently as APPROVED, not a small easy-to-miss badge", () => {
    render(<ResultsTab view={viewWith([])} run={{ ...run, review_verdict: "REJECTED" }} now={0} />);
    const banner = screen.getByText("REJECTED");
    expect(banner.className).toContain("verdict--rejected");
  });

  it("shows 'not yet available' instead of crashing while running (no artifacts yet)", () => {
    render(<ResultsTab view={viewWith([])} run={{ ...run, status: "running", review_verdict: null }} now={0} />);
    expect(screen.getAllByText("not yet available").length).toBeGreaterThan(0);
    expect(screen.getByText("Not yet reviewed.")).toBeTruthy();
  });

  it("shows nothing to fetch when no run is open", () => {
    render(<ResultsTab view={initialView(meta)} run={null} now={0} />);
    expect(screen.getByText("No run selected.")).toBeTruthy();
    expect(api.getArtifact).not.toHaveBeenCalled();
  });
});
