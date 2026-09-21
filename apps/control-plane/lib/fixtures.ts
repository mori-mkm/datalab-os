// Test fixtures only. The graph below is deliberately NOT the real organization: the control plane must work
// for any hierarchy the backend serves, so no test may depend on the real node names.
import type { EventType, ExecutionEvent, GraphMeta, GraphNodeMeta, Status } from "./types";

const node = (id: string, label: string, type: GraphNodeMeta["type"], parent_id: string | null = null): GraphNodeMeta => ({
  id,
  label,
  role: `${label} role`,
  type,
  agent: type === "department" ? null : id.split(".").pop()!,
  parent_id,
});

export const meta: GraphMeta = {
  nodes: [
    node("intake", "Intake", "orchestrator"),
    node("alpha", "Alpha Dept", "department"),
    node("alpha.boss", "Alpha Boss", "agent", "alpha"),
    node("alpha.worker", "Alpha Worker", "agent", "alpha"),
    node("beta", "Beta Dept", "department"),
    node("beta.boss", "Beta Boss", "agent", "beta"),
    node("beta.worker", "Beta Worker", "agent", "beta"),
    node("beta.checker", "Beta Checker", "agent", "beta"),
    node("audit", "Audit", "review"),
  ],
  edges: [
    { id: "intake->alpha.boss", source: "intake", target: "alpha.boss", kind: "handoff" },
    { id: "alpha.boss->alpha.worker", source: "alpha.boss", target: "alpha.worker", kind: "internal" },
    { id: "alpha.worker->beta.boss", source: "alpha.worker", target: "beta.boss", kind: "handoff" },
    { id: "beta.boss->beta.worker", source: "beta.boss", target: "beta.worker", kind: "internal" },
    { id: "beta.boss->beta.checker", source: "beta.boss", target: "beta.checker", kind: "internal" },
    { id: "beta.worker->audit", source: "beta.worker", target: "audit", kind: "handoff" },
    { id: "beta.checker->audit", source: "beta.checker", target: "audit", kind: "handoff" },
  ],
};

let seq = 0;
export const resetSeq = () => {
  seq = 0;
};

export function ev(event_type: EventType, node_id: string | null, extra: Partial<ExecutionEvent> = {}): ExecutionEvent {
  seq += 1;
  return {
    seq,
    event_id: `evt_${seq}`,
    run_id: "r",
    timestamp: `2026-01-01T00:00:${String(seq).padStart(2, "0")}Z`,
    event_type,
    node_id,
    department: node_id ? node_id.split(".")[0] : null,
    agent: null,
    status: null,
    target: null,
    message: "",
    data: {},
    ...extra,
  };
}

export const started = (id: string, status: Status = "running") => ev("agent_started", id, { status, message: `${id} started` });
export const completed = (id: string, status: Status = "completed") => ev("agent_completed", id, { status });
