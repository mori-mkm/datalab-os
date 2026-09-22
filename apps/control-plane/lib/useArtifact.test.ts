// @vitest-environment jsdom
import { act, renderHook } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { useArtifactText } from "./useArtifact";
import * as api from "./api";

vi.mock("./api", () => ({ getArtifact: vi.fn() }));
afterEach(() => vi.resetAllMocks());

/** Deferred promise: lets the test control exactly when a fetch "resolves". */
function deferred<T>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((r) => { resolve = r; });
  return { promise, resolve };
}

describe("useArtifactText", () => {
  it("does not show the previous artifact's content while a different (runId, name) is loading", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const get = vi.mocked(api.getArtifact);
    get.mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);

    const { result, rerender } = renderHook(
      ({ name }: { name: string }) => useArtifactText("run_1", name),
      { initialProps: { name: "review.json" } },
    );

    await act(async () => { first.resolve('{"verdict":"APPROVED"}'); await first.promise; });
    expect(result.current.text).toBe('{"verdict":"APPROVED"}');

    // Selection moves to a different artifact; its fetch has not resolved yet.
    rerender({ name: "report.md" });

    // BUG: the hook keeps rendering review.json's content (mislabeled as report.md) instead of
    // resetting to the loading state (text === null) while the new artifact is in flight.
    // ArtifactsTab.tsx only shows "Loading…" when `content.text === null`, so a caller switching
    // artifacts sees stale, wrongly-attributed content until the new fetch resolves.
    expect(result.current.text).toBeNull(); // fails today: still '{"verdict":"APPROVED"}'

    await act(async () => { second.resolve("# Report"); await second.promise; });
    expect(result.current.text).toBe("# Report");
  });

  it("resets to idle when name transitions back to null (deselecting an artifact)", async () => {
    const first = deferred<string>();
    const get = vi.mocked(api.getArtifact);
    get.mockReturnValueOnce(first.promise);

    const { result, rerender } = renderHook(
      ({ name }: { name: string | null }) => useArtifactText("run_1", name),
      { initialProps: { name: "review.json" as string | null } },
    );

    await act(async () => { first.resolve('{"verdict":"APPROVED"}'); await first.promise; });
    expect(result.current.text).toBe('{"verdict":"APPROVED"}');

    rerender({ name: null });
    expect(result.current.text).toBeNull();
    expect(result.current.error).toBe(false);
  });
});
