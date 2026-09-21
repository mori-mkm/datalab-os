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
  department: string | null;
  agent: string | null;
  status: Status | null;
  target: string | null;
  message: string;
  data: Record<string, unknown>;
}

export interface GraphNodeMeta {
  id: string;
  label: string;
  role: string;
  type: string;
  agent: string;
}

export interface GraphEdgeMeta {
  id: string;
  source: string;
  target: string;
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
}

export interface Health {
  status: string;
  llm: { mode: string; model: string; available: boolean };
}
