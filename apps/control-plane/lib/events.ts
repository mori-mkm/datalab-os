// Pure reducer: execution events -> what the control plane shows. No I/O, no business logic:
// the backend (LangGraph) decides every status, this only folds the event stream.
import type { ExecutionEvent, GraphMeta, RunMode, Status } from "./types";

export type EdgeState = "idle" | "active" | "done";

export interface NodeView {
  status: Status;
  task: string | null;
  startedAt: string | null;
  endedAt: string | null;
  artifacts: string[];
  recent: ExecutionEvent[];
}

export interface RunView {
  runId: string | null;
  mode: RunMode | null;
  status: Status;
  startedAt: string | null;
  endedAt: string | null;
  nodes: Record<string, NodeView>;
  edges: Record<string, EdgeState>;
  events: ExecutionEvent[];
  lastSeq: number;
}

const RECENT_LIMIT = 6;
const HANDOFFS = new Set(["handoff_started", "handoff_completed"]);
const RUN_ENDED = new Set(["run_completed", "run_rejected", "run_failed"]);

const blankNode = (): NodeView => ({
  status: "waiting",
  task: null,
  startedAt: null,
  endedAt: null,
  artifacts: [],
  recent: [],
});

export function initialView(meta: GraphMeta | null, runId: string | null = null, mode: RunMode | null = null): RunView {
  return {
    runId,
    mode,
    status: "waiting",
    startedAt: null,
    endedAt: null,
    nodes: Object.fromEntries((meta?.nodes ?? []).map((n) => [n.id, blankNode()])),
    edges: Object.fromEntries((meta?.edges ?? []).map((e) => [e.id, "idle" as EdgeState])),
    events: [],
    lastSeq: 0,
  };
}

export function applyEvent(view: RunView, event: ExecutionEvent): RunView {
  if (event.seq <= view.lastSeq) return view; // replay after a reconnect
  const next: RunView = { ...view, events: [...view.events, event], lastSeq: event.seq };

  if (event.event_type === "run_started") {
    next.status = "running";
    next.startedAt = event.timestamp;
    next.mode = (event.data.mode as RunMode | undefined) ?? view.mode;
  } else if (RUN_ENDED.has(event.event_type)) {
    next.status = event.status ?? "error";
    next.endedAt = event.timestamp;
  }

  const department = event.department;
  if (!department) return next;

  if (HANDOFFS.has(event.event_type) && event.target) {
    const state: EdgeState = event.event_type === "handoff_started" ? "active" : "done";
    next.edges = { ...view.edges, [`${department}->${event.target}`]: state };
  }

  const node: NodeView = { ...(view.nodes[department] ?? blankNode()) };
  if (!HANDOFFS.has(event.event_type) && event.status) node.status = event.status;
  switch (event.event_type) {
    case "agent_started":
      node.startedAt = event.timestamp;
      node.endedAt = null;
      node.task = event.message;
      break;
    case "agent_status":
      node.task = event.message;
      break;
    case "agent_completed":
    case "agent_failed":
      node.endedAt = event.timestamp;
      break;
    case "artifact_created": {
      const name = event.data.artifact;
      if (typeof name === "string" && !node.artifacts.includes(name)) node.artifacts = [...node.artifacts, name];
      break;
    }
  }
  node.recent = [...node.recent, event].slice(-RECENT_LIMIT);
  next.nodes = { ...view.nodes, [department]: node };
  return next;
}

export function upstreamOf(nodeId: string, meta: GraphMeta): string[] {
  const seen: string[] = [];
  const queue = [nodeId];
  while (queue.length) {
    const current = queue.shift()!;
    for (const edge of meta.edges) {
      if (edge.target === current && !seen.includes(edge.source)) {
        seen.push(edge.source);
        queue.push(edge.source);
      }
    }
  }
  return seen;
}

export function formatDuration(from: string | null, to: string | number | null): string {
  if (!from || to === null) return "—";
  const seconds = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, "0")}s`;
}

export const formatTime = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleTimeString([], { hour12: false }) : "—";
