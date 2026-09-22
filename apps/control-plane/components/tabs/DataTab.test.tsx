// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { DataTab } from "./DataTab";
import * as api from "@/lib/api";
import { applyEvent, initialView } from "@/lib/events";
import { ev, meta, resetSeq } from "@/lib/fixtures";
import type { RunInfo } from "@/lib/types";

vi.mock("@/lib/api", () => ({ getArtifact: vi.fn(), getDatasetPreview: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  resetSeq();
});

const run: RunInfo = { run_id: "run_1", mode: "real", project_name: "p", status: "completed", dataset: "sample.csv" };

const viewWith = (names: string[]) =>
  names.map((name) => ev("artifact_created", "alpha.boss", { data: { artifact: name } })).reduce(applyEvent, initialView(meta, "run_1"));

describe("DataTab", () => {
  it("renders profile, quality and a bounded preview once available", async () => {
    vi.mocked(api.getArtifact).mockImplementation(async (_runId, name) =>
      name === "data_profile.json"
        ? JSON.stringify({ rows: 10, columns: 2, dtypes: { a: "int64" }, missing: { a: { count: 0, pct: 0 } }, target: { column: "a", positive_rate: 0.3 } })
        : JSON.stringify({ duplicate_rows: 1, missing_pct: 0.01, issues: ["1 duplicated row"] }),
    );
    vi.mocked(api.getDatasetPreview).mockResolvedValue({ available: true, columns: ["a"], rows: [{ a: 1 }], truncated: true });
    render(<DataTab view={viewWith(["data_profile.json", "data_quality.json"])} run={run} />);
    expect(await screen.findByText("10")).toBeTruthy();
    expect(await screen.findByText(/1 duplicate rows/)).toBeTruthy();
    expect(await screen.findByText("Bounded sample shown; not the full dataset.")).toBeTruthy();
  });

  it("shows graceful messages when profile/preview are unavailable, never invented rows", async () => {
    vi.mocked(api.getDatasetPreview).mockResolvedValue({ available: false, columns: [], rows: [], truncated: false });
    render(<DataTab view={viewWith([])} run={run} />);
    expect(await screen.findByText("Preview unavailable for this run.")).toBeTruthy();
    expect(screen.getByText("Profile not available for this run.")).toBeTruthy();
  });
});
