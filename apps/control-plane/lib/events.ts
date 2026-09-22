// Pure reducer: execution events -> what the control plane shows. No I/O, no business logic:
// the backend (LangGraph) decides every status, including department lifecycle, this only folds the
// event stream. State is indexed by the graph node id (`event.node_id`), never by display labels.
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
  /** Keyed by edge id `<source node id>-><target node id>`. */
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

export const edgeKey = (source: string, target: string): string => `${source}->${target}`;

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

  const nodeId = event.node_id;
  if (!nodeId) return next;

  if (HANDOFFS.has(event.event_type) && event.target) {
    const state: EdgeState = event.event_type === "handoff_started" ? "active" : "done";
    next.edges = { ...view.edges, [edgeKey(nodeId, event.target)]: state };
  }

  const node: NodeView = { ...(view.nodes[nodeId] ?? blankNode()) };
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
  next.nodes = { ...view.nodes, [nodeId]: node };
  return next;
}

export function formatDuration(from: string | null, to: string | number | null): string {
  if (!from || to === null) return "—";
  const seconds = Math.max(0, Math.round((new Date(to).getTime() - new Date(from).getTime()) / 1000));
  return seconds < 60 ? `${seconds}s` : `${Math.floor(seconds / 60)}m${String(seconds % 60).padStart(2, "0")}s`;
}

export const formatTime = (iso: string | null): string =>
  iso ? new Date(iso).toLocaleTimeString([], { hour12: false }) : "—";

/** Artifact names in creation order, derived from `artifact_created` events: identical for a live run and a
 * replay (unlike `RunInfo.artifacts`, which the backend only fills in once the run has ended). */
export function artifactNames(view: RunView): string[] {
  const names: string[] = [];
  for (const event of view.events) {
    if (event.event_type !== "artifact_created") continue;
    const name = event.data.artifact;
    if (typeof name === "string" && !names.includes(name)) names.push(name);
  }
  return names;
}

/** The top-level unit (department/orchestrator/review/report) most recently touched by an event, or null before
 * anything has run. Same idea as the backend's `current_phase`, but live-updating. */
export function currentPhase(view: RunView): string | null {
  for (let i = view.events.length - 1; i >= 0; i--) {
    const department = view.events[i].department;
    if (department) return department;
  }
  return null;
}

/** Start/end timestamps of the node that produced a given artifact (found by scanning `NodeView.artifacts`, not
 * by name), or null if that artifact hasn't been created yet. No node id is hardcoded: whichever node reports
 * the artifact is the one timed. */
export function nodeTimingForArtifact(view: RunView, name: string): { startedAt: string | null; endedAt: string | null } | null {
  const node = Object.values(view.nodes).find((n) => n.artifacts.includes(name));
  return node ? { startedAt: node.startedAt, endedAt: node.endedAt } : null;
}

/** Tool/library names reported by `agent_completed.data.tools` for one node, in event order, deduped.
 * Empty on older runs / agents that don't set `_tools` — the caller renders "not recorded", never an error. */
export function toolsFor(view: RunView, nodeId: string): string[] {
  const names: string[] = [];
  for (const event of view.events) {
    if (event.event_type !== "agent_completed" || event.node_id !== nodeId) continue;
    const tools = event.data.tools;
    if (!Array.isArray(tools)) continue;
    for (const tool of tools) if (typeof tool === "string" && !names.includes(tool)) names.push(tool);
  }
  return names;
}

/** The verdict of the most recent completed review, or null before one has happened. */
export function reviewVerdict(view: RunView): string | null {
  for (let i = view.events.length - 1; i >= 0; i--) {
    const event = view.events[i];
    if (event.event_type === "review_completed") {
      const verdict = event.data.verdict;
      return typeof verdict === "string" ? verdict : null;
    }
  }
  return null;
}
