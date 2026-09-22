// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { OverviewTab } from "./OverviewTab";
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

const run: RunInfo = { run_id: "run_1", mode: "real", project_name: "churn", status: "completed", dataset: "sample.csv" };

const viewWith = (names: string[]) =>
  names.map((name) => ev("artifact_created", "alpha.boss", { data: { artifact: name } })).reduce(applyEvent, initialView(meta, "run_1"));

describe("OverviewTab", () => {
  it("renders target and model metric once problem.yaml and model_evaluation.json are available", async () => {
    vi.mocked(api.getArtifact).mockImplementation(async (_runId, name) =>
      name === "problem.yaml"
        ? "project_name: churn\ntarget: churned\n"
        : JSON.stringify({ selected_model: "baseline_logreg", primary_metric: "roc_auc", metrics: { roc_auc: 0.827 } }),
    );
    render(<OverviewTab meta={meta} view={viewWith(["problem.yaml", "model_evaluation.json"])} run={run} now={0} />);
    expect(await screen.findByText("churned")).toBeTruthy();
    expect(await screen.findByText("baseline_logreg")).toBeTruthy();
    expect(await screen.findByText("roc_auc = 0.827")).toBeTruthy();
  });

  it("tolerates a run with no model_evaluation.json yet (still running, or rejected before modeling)", () => {
    render(<OverviewTab meta={meta} view={viewWith([])} run={run} now={0} />);
    expect(screen.getByText("not available")).toBeTruthy();
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("shows nothing to fetch when no run is open", () => {
    render(<OverviewTab meta={meta} view={initialView(meta)} run={null} now={0} />);
    expect(screen.getByText("No run selected.")).toBeTruthy();
    expect(api.getArtifact).not.toHaveBeenCalled();
  });
});
