"use client";

import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { ActivityFeed } from "@/components/ActivityFeed";
import { AgentDetails } from "@/components/AgentDetails";
import { ExecutionGraph } from "@/components/graph/ExecutionGraph";
import { RunHeader } from "@/components/RunHeader";
import { API_URL, createRun, getGraph, getHealth, getRun, streamUrl } from "@/lib/api";
import { applyEvent, initialView, type RunView } from "@/lib/events";
import type { ExecutionEvent, GraphMeta, Health, RunMode } from "@/lib/types";

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
  const source = useRef<EventSource | null>(null);

  const attach = useCallback((runId: string) => {
    source.current?.close();
    const es = new EventSource(streamUrl(runId)); // the browser reconnects with Last-Event-ID; the reducer dedupes by seq
    source.current = es;
    es.onmessage = (message) => {
      const event = JSON.parse(message.data) as ExecutionEvent;
      dispatch({ type: "event", event });
      if (TERMINAL.has(event.event_type)) es.close();
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [graph, healthInfo] = await Promise.all([getGraph(), getHealth()]);
        if (cancelled) return;
        setMeta(graph);
        setHealth(healthInfo);
        const runId = new URLSearchParams(window.location.search).get("run");
        const run = runId ? await getRun(runId).catch(() => null) : null; // survives a page refresh
        dispatch({ type: "reset", meta: graph, runId: run?.run_id ?? null, mode: run?.mode ?? null });
        if (run) attach(run.run_id);
      } catch {
        if (!cancelled) setBackendError(`Cannot reach the API at ${API_URL}. Start it: uvicorn datalab.api.app:app`);
      }
    })();
    return () => {
      cancelled = true;
      source.current?.close();
    };
  }, [attach]);

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
    try {
      const run = await createRun(mode, config);
      dispatch({ type: "reset", meta, runId: run.run_id, mode: run.mode });
      window.history.replaceState(null, "", `?run=${run.run_id}`);
      attach(run.run_id);
      setBackendError(null);
      getHealth().then(setHealth, () => undefined);
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : String(error));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="app">
      <RunHeader view={view} now={now} health={health} backendError={backendError} busy={busy} onStart={start} />
      <main className="main">
        <div className="canvas">
          {meta ? (
            <ExecutionGraph meta={meta} view={view} now={now} selected={selected} onSelect={setSelected} />
          ) : (
            <div className="muted center">{backendError ? "Graph unavailable" : "Loading graph…"}</div>
          )}
        </div>
        {meta && selected && (
          <AgentDetails
            nodeId={selected}
            meta={meta}
            view={view}
            now={now}
            onSelect={setSelected}
            onClose={() => setSelected(null)}
          />
        )}
      </main>
      {meta && <ActivityFeed events={view.events} meta={meta} />}
    </div>
  );
}
