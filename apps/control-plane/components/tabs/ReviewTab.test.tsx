// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReviewTab } from "./ReviewTab";
import * as api from "@/lib/api";
import { applyEvent, initialView } from "@/lib/events";
import { ev, meta, resetSeq } from "@/lib/fixtures";

vi.mock("@/lib/api", () => ({ getArtifact: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  resetSeq();
});

const viewWith = (names: string[]) =>
  names.map((name) => ev("artifact_created", "alpha.boss", { data: { artifact: name } })).reduce(applyEvent, initialView(meta, "run_1"));

describe("ReviewTab", () => {
  it("renders the checklist verbatim from review.json, with the verdict prominent at the top", async () => {
    vi.mocked(api.getArtifact).mockResolvedValue(
      JSON.stringify({
        verdict: "REJECTED",
        checks: [
          { name: "no_target_leakage", passed: false, detail: "declared leakage/target used as feature: ['tenure_months']" },
          { name: "baseline_exists", passed: true, detail: "baseline experiment found" },
        ],
      }),
    );
    render(<ReviewTab view={viewWith(["review.json"])} />);
    expect(await screen.findByText("REJECTED")).toBeTruthy();
    expect(await screen.findByText("declared leakage/target used as feature: ['tenure_months']")).toBeTruthy();
    expect(screen.getByText("no_target_leakage")).toBeTruthy();
    expect(screen.getByText("baseline_exists")).toBeTruthy();
  });

  it("shows 'not yet available' before review.json exists, never a crash", () => {
    render(<ReviewTab view={viewWith([])} />);
    expect(screen.getByText("Review checklist not yet available.")).toBeTruthy();
    expect(screen.getByText("Not yet reviewed.")).toBeTruthy();
  });

  it("shows nothing to fetch when no run is open", () => {
    render(<ReviewTab view={initialView(meta)} />);
    expect(screen.getByText("No run selected.")).toBeTruthy();
    expect(api.getArtifact).not.toHaveBeenCalled();
  });
});
