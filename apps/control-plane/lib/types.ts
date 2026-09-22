// Mirrors the backend contract (src/datalab/schemas). Keep in sync with schemas/event.py and schemas/run.py.

export type Status = "waiting" | "running" | "completed" | "rejected" | "error";
export type RunMode = "demo" | "real";

export type EventType =
  | "run_started"
  | "run_completed"
  | "run_rejected"
  | "run_failed"
  | "agent_started"
  | "agent_status"
  | "agent_completed"
  | "agent_failed"
  | "handoff_started"
  | "handoff_completed"
  | "artifact_created"
  | "review_started"
  | "review_completed";

export interface ExecutionEvent {
  seq: number;
  event_id: string;
  run_id: string;
  timestamp: string;
  event_type: EventType;
  /** The graph node the event is about: `head_ds`, a department id, or `<department>.<agent>`. Null for run-level events. */
  node_id: string | null;
  /** The top-level unit the node belongs to (department id, or the node's own id). */
  department: string | null;
  agent: string | null;
  /** Status of `node_id` (or of the run for run events) after this event. */
  status: Status | null;
  /** For handoffs: the executable node id receiving control (`node_id` is the sender). */
  target: string | null;
  message: string;
  data: Record<string, unknown>;
}

export type NodeType = "orchestrator" | "department" | "agent" | "review" | "report";

export interface GraphNodeMeta {
  id: string;
  label: string;
  role: string;
  type: NodeType;
  agent: string | null;
  /** Department id for agents inside a department; null for top-level nodes and department containers. */
  parent_id: string | null;
}

export interface GraphEdgeMeta {
  id: string;
  source: string;
  target: string;
  /** internal: between agents of one department · handoff: between top-level units. */
  kind: "internal" | "handoff";
}

export interface GraphMeta {
  nodes: GraphNodeMeta[];
  edges: GraphEdgeMeta[];
}

export interface RunInfo {
  run_id: string;
  mode: RunMode;
  project_name: string;
  status: Status;
  // Persisted-run fields (schemas/run.py). Optional: absent on older payloads.
  created_at?: string | null;
  finished_at?: string | null;
  error?: string | null;
  /** File name of the dataset for real runs; null in demo. */
  dataset?: string | null;
  review_verdict?: string | null;
}

export interface Health {
  status: string;
  llm: { mode: string; model: string; available: boolean };
}
