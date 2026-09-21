import { formatDuration, formatTime, upstreamOf, type RunView } from "@/lib/events";
import type { GraphMeta } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  nodeId: string;
  meta: GraphMeta;
  view: RunView;
  now: number;
  onClose: () => void;
}

const list = (items: string[]) => (items.length ? items.join(", ") : "—");

// Every value comes from the run's events; nothing here is computed or invented client-side.
export function AgentDetails({ nodeId, meta, view, now, onClose }: Props) {
  const spec = meta.nodes.find((n) => n.id === nodeId);
  const node = view.nodes[nodeId];
  if (!spec || !node) return null;
  const inputs = upstreamOf(nodeId, meta).flatMap((id) => view.nodes[id]?.artifacts ?? []);
  const recent = node.recent.filter((e) => e.event_type !== "handoff_completed");
  const duration = node.startedAt ? formatDuration(node.startedAt, node.endedAt ?? now) : "—";

  return (
    <aside className="details">
      <div className="details__head">
        <div>
          <div className="details__title">{spec.label}</div>
          <div className="muted">
            {spec.role} · agent: {spec.agent}
          </div>
        </div>
        <button className="ghost" onClick={onClose} aria-label="Close details">
          ✕
        </button>
      </div>
      <dl>
        <dt>Status</dt>
        <dd>
          <StatusBadge status={node.status} />
        </dd>
        <dt>Current task</dt>
        <dd>{node.task ?? "—"}</dd>
        <dt>Input</dt>
        <dd>{list(inputs)}</dd>
        <dt>Artifacts</dt>
        <dd>{list(node.artifacts)}</dd>
        <dt>Started</dt>
        <dd>{formatTime(node.startedAt)}</dd>
        <dt>Duration</dt>
        <dd>{duration}</dd>
        <dt>Recent activity</dt>
        <dd>
          {recent.length ? (
            <ul>
              {[...recent].reverse().map((e) => (
                <li key={e.seq}>
                  <span className="muted">{formatTime(e.timestamp)}</span> {e.message}
                </li>
              ))}
            </ul>
          ) : (
            "—"
          )}
        </dd>
      </dl>
    </aside>
  );
}
