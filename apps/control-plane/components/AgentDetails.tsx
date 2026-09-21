import { formatDuration, formatTime, type RunView } from "@/lib/events";
import { departmentSummary, inputsFor, isContainer, labelPath } from "@/lib/hierarchy";
import type { GraphMeta } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

interface Props {
  nodeId: string;
  meta: GraphMeta;
  view: RunView;
  now: number;
  onSelect: (id: string) => void;
  onClose: () => void;
}

const list = (items: string[]) => (items.length ? items.join(", ") : "—");

// Every value comes from the run's events and the backend graph; nothing here is computed or invented client-side.
export function AgentDetails({ nodeId, meta, view, now, onSelect, onClose }: Props) {
  const spec = meta.nodes.find((n) => n.id === nodeId);
  const node = view.nodes[nodeId];
  if (!spec || !node) return null;
  const department = isContainer(spec) ? departmentSummary(meta, view, nodeId) : null;
  const task = department
    ? department.activeAgent
      ? `${labelPath(meta, department.activeAgent)}: ${view.nodes[department.activeAgent]?.task ?? "—"}`
      : null
    : node.task;
  const artifacts = department ? department.artifacts : node.artifacts;
  const recent = (department ? department.recent : node.recent).filter((e) => e.event_type !== "handoff_completed");
  const duration = node.startedAt ? formatDuration(node.startedAt, node.endedAt ?? now) : "—";

  return (
    <aside className="details">
      <div className="details__head">
        <div>
          <div className="details__title">{spec.label}</div>
          <div className="muted">
            {spec.role}
            {spec.agent ? ` · agent: ${spec.agent}` : ` · ${spec.type}`}
          </div>
          {spec.parent_id && <div className="muted">in {labelPath(meta, spec.parent_id)}</div>}
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
        {department && (
          <>
            <dt>Agents</dt>
            <dd>
              <ul className="details__agents">
                {department.agents.map((a) => (
                  <li key={a.id}>
                    <button className="ghost details__link" onClick={() => onSelect(a.id)}>
                      {a.label}
                    </button>
                    <StatusBadge status={a.status} />
                  </li>
                ))}
              </ul>
            </dd>
          </>
        )}
        <dt>Current task</dt>
        <dd>{task ?? "—"}</dd>
        <dt>Input</dt>
        <dd>{list(inputsFor(meta, view, nodeId))}</dd>
        <dt>Artifacts</dt>
        <dd>{list(artifacts)}</dd>
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
                  <span className="muted">{formatTime(e.timestamp)}</span>
                  {department && e.node_id && e.event_type !== "handoff_started"
                    ? ` ${meta.nodes.find((n) => n.id === e.node_id)?.label}: `
                    : " "}
                  {e.message}
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
