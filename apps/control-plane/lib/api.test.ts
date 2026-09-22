import { afterEach, describe, expect, it, vi } from "vitest";
import { listRuns } from "./api";

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
