// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReportTab } from "./ReportTab";
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

describe("ReportTab", () => {
  it("renders report.md as Markdown", async () => {
    vi.mocked(api.getArtifact).mockResolvedValue("# Report\n\nDone.");
    render(<ReportTab view={viewWith(["report.md"])} />);
    expect(await screen.findByRole("heading", { name: "Report" })).toBeTruthy();
  });

  it("shows 'not yet available' before report.md exists, never a crash", () => {
    render(<ReportTab view={viewWith([])} />);
    expect(screen.getByText("Report not yet available.")).toBeTruthy();
  });

  it("shows nothing to fetch when no run is open", () => {
    render(<ReportTab view={initialView(meta)} />);
    expect(screen.getByText("No run selected.")).toBeTruthy();
    expect(api.getArtifact).not.toHaveBeenCalled();
  });
});
