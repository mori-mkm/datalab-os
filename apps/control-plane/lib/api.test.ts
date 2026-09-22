import { afterEach, describe, expect, it, vi } from "vitest";
import { getArtifact, getDatasetPreview, listRuns } from "./api";

afterEach(() => vi.unstubAllGlobals());

const stub = (response: Partial<Response>) => {
  const fetchMock = vi.fn().mockResolvedValue(response);
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
};

describe("listRuns", () => {
  it("asks for the newest runs with a limit and returns the payload as sent", async () => {
    const runs = [{ run_id: "run_20260101_000000_abcd", mode: "demo", project_name: "p", status: "completed" }];
    const fetchMock = stub({ ok: true, json: async () => runs });
    expect(await listRuns(20)).toEqual(runs);
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/runs\?limit=20$/);
  });

  it("rejects when the endpoint is down, so the caller can hide the picker", async () => {
    stub({ ok: false, status: 404, text: async () => "nope" });
    await expect(listRuns()).rejects.toThrow("404");
  });
});

describe("getArtifact", () => {
  it("returns the raw text, whatever the content type", async () => {
    const fetchMock = stub({ ok: true, text: async () => "# Report\n" });
    expect(await getArtifact("run_1", "report.md")).toBe("# Report\n");
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/runs\/run_1\/artifacts\/report\.md$/);
  });

  it("rejects on a name not in that run's artifacts (backend 404), so the caller shows 'unavailable'", async () => {
    stub({ ok: false, status: 404, text: async () => "not found" });
    await expect(getArtifact("run_1", "ghost.json")).rejects.toThrow("404");
  });
});

describe("getDatasetPreview", () => {
  it("asks for a bounded sample and returns the payload as sent", async () => {
    const preview = { available: true, columns: ["a"], rows: [{ a: 1 }], truncated: false };
    const fetchMock = stub({ ok: true, json: async () => preview });
    expect(await getDatasetPreview("run_1", 10)).toEqual(preview);
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/runs\/run_1\/dataset-preview\?limit=10$/);
  });
});
