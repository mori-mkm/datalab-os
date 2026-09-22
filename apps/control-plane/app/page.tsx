"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ActivityFeed } from "@/components/ActivityFeed";
import { AgentDetails } from "@/components/AgentDetails";
import { ExecutionGraph } from "@/components/graph/ExecutionGraph";
import { HandoffInspector } from "@/components/HandoffInspector";
import { HandoffTimeline } from "@/components/HandoffTimeline";
import { RunHeader } from "@/components/RunHeader";
import { TabNav, type TabId } from "@/components/TabNav";
import { OverviewTab } from "@/components/tabs/OverviewTab";
import { DataTab } from "@/components/tabs/DataTab";
import { ArtifactsTab } from "@/components/tabs/ArtifactsTab";
import { ResultsTab } from "@/components/tabs/ResultsTab";
import { ReviewTab } from "@/components/tabs/ReviewTab";
import { ReportTab } from "@/components/tabs/ReportTab";
import { API_URL, createRun, getGraph, getHealth, getRun, listRuns, streamUrl } from "@/lib/api";
import { applyEvent, initialView, type RunView } from "@/lib/events";
import type { ExecutionEvent, GraphMeta, Health, RunInfo, RunMode } from "@/lib/types";

type Action =
  | { type: "reset"; meta: GraphMeta; runId: string | null; mode: RunMode | null }
  | { type: "event"; event: ExecutionEvent };

const reducer = (view: RunView, action: Action): RunView =>
  action.type === "reset" ? initialView(action.meta, action.runId, action.mode) : applyEvent(view, action.event);

const TERMINAL = new Set(["run_completed", "run_rejected", "run_failed"]);

export default function ControlPlane() {
  const [meta, setMeta] = useState<GraphMeta | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [view, dispatch] = useReducer(reducer, null, () => initialView(null));
  const [selected, setSelected] = useState<string | null>(null);
  const [now, setNow] = useState(0);
  const [busy, setBusy] = useState(false);
  const [runs, setRuns] = useState<RunInfo[] | null>(null); // null: history unavailable, picker hidden
  const [runInfo, setRunInfo] = useState<RunInfo | null>(null); // the static fields (project, dataset) for the open run
  const [tab, setTab] = useState<TabId>("execution"); // Execution is today's unchanged default view
  const source = useRef<EventSource | null>(null);
  const opening = useRef(0); // latest open/start wins over a slower earlier getRun
  const mounted = useRef(false);
  const listing = useRef(0);

  const refreshRuns = useCallback(() => {
    const ticket = ++listing.current;
    listRuns().then(
      (items) => { if (mounted.current && ticket === listing.current) setRuns(items); },
      () => { if (mounted.current && ticket === listing.current) setRuns(null); },
    );
  }, []);

  const attach = useCallback((runId: string) => {
    source.current?.close();
    const es = new EventSource(streamUrl(runId)); // the browser reconnects with Last-Event-ID; the reducer dedupes by seq
    source.current = es;
    es.onmessage = (message) => {
      if (!mounted.current || source.current !== es) return;
      const event = JSON.parse(message.data) as ExecutionEvent;
      dispatch({ type: "event", event });
      if (TERMINAL.has(event.event_type)) {
        es.close();
        refreshRuns();
      }
    };
  }, [refreshRuns]);

  // Same steps for a page-load restore, a new run and a history pick: reset the view, then replay + follow the stream.
  const show = useCallback(
    (graph: GraphMeta, run: RunInfo | null) => {
      dispatch({ type: "reset", meta: graph, runId: run?.run_id ?? null, mode: run?.mode ?? null });
      setRunInfo(run);
      if (run) attach(run.run_id);
    },
    [attach],
  );

  useEffect(() => {
    let cancelled = false;
    mounted.current = true;
    const ticket = ++opening.current;
    refreshRuns();
    (async () => {
      try {
        const [graph, healthInfo] = await Promise.all([getGraph(), getHealth()]);
        if (cancelled) return;
        setMeta(graph);
        setHealth(healthInfo);
        const runId = new URLSearchParams(window.location.search).get("run");
        const run = runId ? await getRun(runId).catch(() => null) : null; // survives a page refresh
        if (cancelled || ticket !== opening.current) return;
        if (runId && !run) setBackendError(`Cannot open ${runId}: run not found`);
        show(graph, run);
      } catch {
        if (!cancelled) setBackendError(`Cannot reach the API at ${API_URL}. Start it: uvicorn datalab.api.app:app`);
      }
    })();
    return () => {
      cancelled = true;
      mounted.current = false;
      opening.current += 1;
      listing.current += 1;
      source.current?.close();
      source.current = null;
    };
  }, [show, refreshRuns]);

  useEffect(() => {
    if (view.status !== "running") return;
    const tick = () => setNow(Date.now());
    const first = setTimeout(tick, 0);
    const timer = setInterval(tick, 1000);
    return () => {
      clearTimeout(first);
      clearInterval(timer);
    };
  }, [view.status]);

  const start = async (mode: RunMode, config?: string) => {
    if (!meta) return;
    setBusy(true);
    setSelected(null);
    const ticket = ++opening.current;
    try {
      const run = await createRun(mode, config);
      if (!mounted.current) return;
      refreshRuns(); // a superseded POST still created a run, so keep history current
      if (ticket !== opening.current) return;
      show(meta, run);
      window.history.replaceState(null, "", `?run=${run.run_id}`);
      setBackendError(null);
      getHealth().then((value) => { if (mounted.current && ticket === opening.current) setHealth(value); }, () => undefined);
    } catch (error) {
      if (mounted.current && ticket === opening.current) setBackendError(error instanceof Error ? error.message : String(error));
    } finally {
      if (mounted.current) setBusy(false);
    }
  };

  const openRun = async (runId: string) => {
    if (!meta) return;
    const ticket = ++opening.current;
    try {
      const run = await getRun(runId);
      if (!mounted.current || ticket !== opening.current) return;
      setSelected(null);
      show(meta, run);
      window.history.replaceState(null, "", `?run=${run.run_id}`);
      setBackendError(null);
    } catch {
      if (mounted.current && ticket === opening.current) setBackendError(`Cannot open ${runId}: run not found`);
    }
  };

  return (
    <div className="app">
      <RunHeader
        view={view}
        now={now}
        health={health}
        backendError={backendError}
        busy={busy}
        runs={runs}
        onStart={start}
        onOpen={openRun}
      />
      <TabNav active={tab} onSelect={setTab} />
      {tab === "execution" && (
        <>
          <main className="main">
            <div className="canvas">
              {meta ? (
                <ExecutionGraph meta={meta} view={view} now={now} selected={selected} onSelect={setSelected} />
              ) : (
                <div className="muted center">{backendError ? "Graph unavailable" : "Loading graph…"}</div>
              )}
            </div>
            {meta && selected && (meta.edges.some((e) => e.id === selected) ? (
              <HandoffInspector
                edgeId={selected}
                meta={meta}
                view={view}
                onSelect={setSelected}
                onClose={() => setSelected(null)}
              />
            ) : (
              <AgentDetails
                nodeId={selected}
                meta={meta}
                view={view}
                now={now}
                onSelect={setSelected}
                onClose={() => setSelected(null)}
              />
            ))}
          </main>
          {meta && <ActivityFeed events={view.events} meta={meta} />}
        </>
      )}
      {tab === "overview" && meta && <OverviewTab key={view.runId ?? "none"} meta={meta} view={view} run={runInfo} now={now} />}
      {tab === "data" && <DataTab key={view.runId ?? "none"} view={view} run={runInfo} />}
      {tab === "collaboration" && meta && <HandoffTimeline key={view.runId ?? "none"} view={view} meta={meta} />}
      {tab === "artifacts" && <ArtifactsTab key={view.runId ?? "none"} view={view} />}
      {tab === "results" && <ResultsTab key={view.runId ?? "none"} view={view} run={runInfo} now={now} />}
      {tab === "review" && <ReviewTab key={view.runId ?? "none"} view={view} />}
      {tab === "report" && <ReportTab key={view.runId ?? "none"} view={view} />}
    </div>
  );
}
