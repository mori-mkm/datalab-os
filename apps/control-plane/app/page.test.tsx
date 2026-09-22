// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import ControlPlane from "./page";
import * as api from "@/lib/api";
import { meta } from "@/lib/fixtures";
import type { RunInfo } from "@/lib/types";

vi.mock("@/lib/api", () => ({
  API_URL: "http://test", getGraph: vi.fn(), getHealth: vi.fn(), listRuns: vi.fn(),
  getRun: vi.fn(), createRun: vi.fn(), streamUrl: (id: string) => `/api/runs/${id}/stream`,
}));
vi.mock("@/components/graph/ExecutionGraph", () => ({ ExecutionGraph: () => <div>Execution graph</div> }));
vi.mock("@/components/ActivityFeed", () => ({ ActivityFeed: () => null }));
vi.mock("@/components/AgentDetails", () => ({ AgentDetails: () => null }));

const a: RunInfo = { run_id: "run_20260102_120000_ab12", mode: "demo", project_name: "A", status: "completed" };
const b: RunInfo = { run_id: "run_20260101_120000_cd34", mode: "real", project_name: "B", status: "error", dataset: "sales.csv", error: "interrupted", created_at: "2026-01-01T12:00:00Z" };
class FakeSource {
  static instances: FakeSource[] = [];
  onmessage: ((message: { data: string }) => void) | null = null;
  close = vi.fn();
  constructor(public url: string) { FakeSource.instances.push(this); }
  terminal() {
    this.onmessage?.({ data: JSON.stringify({ seq: 1, event_id: "evt_0001", run_id: b.run_id, event_type: "run_failed", status: "error", timestamp: "2026-01-01T12:01:00Z", data: {} }) });
  }
}
function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
const ready = () => waitFor(() => expect((screen.getByRole("button", { name: "Run demo" }) as HTMLButtonElement).disabled).toBe(false));
const pick = (run: RunInfo) => fireEvent.change(screen.getByRole("combobox", { name: "Past runs" }), { target: { value: run.run_id } });

beforeEach(() => {
  vi.resetAllMocks();
  window.history.replaceState(null, "", "/");
  FakeSource.instances = [];
  vi.stubGlobal("EventSource", FakeSource);
  vi.mocked(api.getGraph).mockResolvedValue(meta);
  vi.mocked(api.getHealth).mockResolvedValue({ status: "ok", llm: { available: false, mode: "off", model: "none" } });
  vi.mocked(api.listRuns).mockResolvedValue([a, b]);
  vi.mocked(api.getRun).mockImplementation(async (id) => id === a.run_id ? a : b);
  vi.mocked(api.createRun).mockResolvedValue(a);
});
afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

describe("history interaction", () => {
  it("preserves newest-first order, labels and tooltip; opens, replays, closes and refreshes", async () => {
    render(<ControlPlane />);
    await ready();
    const options = screen.getAllByRole("option") as HTMLOptionElement[];
    expect(options.slice(1).map((option) => option.value)).toEqual([a.run_id, b.run_id]);
    expect(options[2].textContent).toContain("#cd34 · real sales.csv · error");
    expect(options[2].textContent).toContain(new Date(b.created_at!).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }));
    expect(options[2].title).toContain("interrupted");
    pick(a);
    await waitFor(() => expect(FakeSource.instances).toHaveLength(1));
    pick(b);
    await waitFor(() => expect(window.location.search).toBe(`?run=${b.run_id}`));
    expect(FakeSource.instances[0].close).toHaveBeenCalledOnce();
    const stream = FakeSource.instances[1];
    await act(async () => stream.terminal());
    expect(screen.getByText("ERROR")).toBeTruthy();
    expect(stream.close).toHaveBeenCalledOnce();
    expect(api.listRuns).toHaveBeenCalledTimes(2);
    expect(api.createRun).not.toHaveBeenCalled();
  });

  it("restores the run from the URL and closes the stream on unmount", async () => {
    window.history.replaceState(null, "", `?run=${b.run_id}`);
    const view = render(<ControlPlane />);
    await waitFor(() => expect(FakeSource.instances).toHaveLength(1));
    expect(api.getRun).toHaveBeenCalledWith(b.run_id);
    expect(FakeSource.instances[0].url).toContain(b.run_id);
    view.unmount();
    expect(FakeSource.instances[0].close).toHaveBeenCalledOnce();
  });

  it.each(["empty", "unavailable"])("keeps run buttons usable when history is %s", async (state) => {
    if (state === "empty") vi.mocked(api.listRuns).mockResolvedValue([]);
    else vi.mocked(api.listRuns).mockRejectedValue(new Error("offline"));
    render(<ControlPlane />);
    await ready();
    expect(screen.queryByRole("combobox")).toBeNull();
    if (state === "empty") expect(screen.getByText("No past runs")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Run demo" }));
    await waitFor(() => expect(FakeSource.instances).toHaveLength(1));
  });

  it("reports an unknown run without breaking the buttons", async () => {
    vi.mocked(api.getRun).mockRejectedValue(new Error("404"));
    render(<ControlPlane />);
    await ready();
    pick(b);
    expect(await screen.findByText(`Cannot open ${b.run_id}: run not found`)).toBeTruthy();
    expect(FakeSource.instances).toHaveLength(0);
    await ready();
  });

  it("reports an unavailable backend", async () => {
    vi.mocked(api.getGraph).mockRejectedValue(new Error("offline"));
    render(<ControlPlane />);
    expect(await screen.findByText(/Cannot reach the API/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Run demo" }) as HTMLButtonElement).disabled).toBe(true);
  });
});

describe("latest user action wins", () => {
  it.each(["resolve", "reject"] as const)("a pending start cannot override a later selection on %s", async (outcome) => {
    const post = deferred<RunInfo>();
    vi.mocked(api.createRun).mockReturnValue(post.promise);
    render(<ControlPlane />);
    await ready();
    fireEvent.click(screen.getByRole("button", { name: "Run demo" }));
    pick(b);
    await waitFor(() => expect(window.location.search).toBe(`?run=${b.run_id}`));
    await act(async () => { if (outcome === "resolve") post.resolve(a); else post.reject(new Error("late error")); });
    expect(window.location.search).toBe(`?run=${b.run_id}`);
    expect(FakeSource.instances).toHaveLength(1);
    expect(screen.queryByText("late error")).toBeNull();
    await ready();
  });

  it("a pending historical GET cannot override a later start", async () => {
    const get = deferred<RunInfo>();
    vi.mocked(api.getRun).mockReturnValue(get.promise);
    render(<ControlPlane />);
    await ready();
    pick(b);
    fireEvent.click(screen.getByRole("button", { name: "Run demo" }));
    await waitFor(() => expect(window.location.search).toBe(`?run=${a.run_id}`));
    await act(async () => get.resolve(b));
    expect(window.location.search).toBe(`?run=${a.run_id}`);
    expect(FakeSource.instances).toHaveLength(1);
  });

  it.each(["select", "unmount"])("pending URL restore is invalidated by %s", async (action) => {
    const get = deferred<RunInfo>();
    window.history.replaceState(null, "", `?run=${a.run_id}`);
    vi.mocked(api.getRun).mockImplementation((id) => id === a.run_id ? get.promise : Promise.resolve(b));
    const view = render(<ControlPlane />);
    await ready();
    if (action === "unmount") view.unmount();
    else {
      pick(b);
      await waitFor(() => expect(window.location.search).toBe(`?run=${b.run_id}`));
    }
    await act(async () => get.resolve(a));
    expect(FakeSource.instances).toHaveLength(action === "unmount" ? 0 : 1);
    if (action === "select") expect(window.location.search).toBe(`?run=${b.run_id}`);
  });
});
