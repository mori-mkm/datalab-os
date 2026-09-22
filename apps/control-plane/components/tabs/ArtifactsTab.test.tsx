// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ArtifactsTab } from "./ArtifactsTab";
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

describe("ArtifactsTab", () => {
  it("lists artifacts and pretty-prints a selected JSON one", async () => {
    vi.mocked(api.getArtifact).mockResolvedValue('{"a":1}');
    render(<ArtifactsTab view={viewWith(["review.json"])} />);
    fireEvent.click(screen.getByText("review.json"));
    expect(await screen.findByText(/"a": 1/)).toBeTruthy();
  });

  it("renders a .md artifact as Markdown", async () => {
    vi.mocked(api.getArtifact).mockResolvedValue("# Report\n\nDone.");
    render(<ArtifactsTab view={viewWith(["report.md"])} />);
    fireEvent.click(screen.getByText("report.md"));
    expect(await screen.findByRole("heading", { name: "Report" })).toBeTruthy();
  });

  it("shows a graceful 'unavailable' for a name the backend rejects, never a crash", async () => {
    vi.mocked(api.getArtifact).mockRejectedValue(new Error("404"));
    render(<ArtifactsTab view={viewWith(["ghost.json"])} />);
    fireEvent.click(screen.getByText("ghost.json"));
    expect(await screen.findByText("Artifact unavailable.")).toBeTruthy();
  });
});
