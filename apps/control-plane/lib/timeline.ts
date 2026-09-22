// Pure read model: ExecutionEvent[] -> Handoff Timeline entries (console-contract.md §4). No I/O, no LLM call,
// no fabricated copy: every entry reuses the event's own `message` (already emitted by the backend) and keeps
// its source `seq`/`event_id` so it is spot-checkable 1:1 against the raw log.
import { labelPath } from "./hierarchy";
import type { ExecutionEvent, GraphMeta } from "./types";

export type TimelineKind = "task" | "status" | "artifact" | "handoff" | "review" | "run";

export interface TimelineEntry {
  seq: number;
  event_id: string;
  timestamp: string;
  node_id: string | null;
  kind: TimelineKind;
  /** Display name to group chat-like entries by: the node/department label, or "Run" for run-level events. */
  actor: string;
  message: string;
}

const KIND_OF: Partial<Record<ExecutionEvent["event_type"], TimelineKind>> = {
  agent_started: "task",
  agent_status: "status",
  artifact_created: "artifact",
  handoff_started: "handoff",
  handoff_completed: "handoff",
  review_started: "review",
  review_completed: "review",
  run_started: "run",
  run_completed: "run",
  run_rejected: "run",
  run_failed: "run",
};

/**
 * Handoff Timeline entries: one per agent_started/agent_status/artifact_created/handoff_started/
 * handoff_completed/review_started/review_completed/run_* event, in that order.
 *
 * Intentional filter: `agent_completed`/`agent_failed` are not mapped (not in the contract's §4 list). Their
 * lifecycle is already carried by the agent_started task line plus the handoff/run event that follows, and the
 * live status is already visible on the node in the Execution tab — same reasoning as ActivityFeed's own
 * `handoff_completed` filter (avoid a second, redundant bubble per agent).
 */
export function timelineOf(events: ExecutionEvent[], meta: GraphMeta): TimelineEntry[] {
  const entries: TimelineEntry[] = [];
  for (const event of events) {
    const kind = KIND_OF[event.event_type];
    if (!kind) continue;
    entries.push({
      seq: event.seq,
      event_id: event.event_id,
      timestamp: event.timestamp,
      node_id: event.node_id,
      kind,
      actor: event.node_id ? labelPath(meta, event.node_id) : "Run",
      message: event.message,
    });
  }
  return entries;
}
