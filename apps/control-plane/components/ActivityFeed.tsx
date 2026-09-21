import { useEffect, useRef } from "react";
import { formatTime } from "@/lib/events";
import type { ExecutionEvent, GraphMeta } from "@/lib/types";

function describe(event: ExecutionEvent, labels: Record<string, string>): string {
  const name = (id: string | null) => (id ? (labels[id] ?? id) : "");
  switch (event.event_type) {
    case "handoff_started":
      return `Handoff: ${name(event.department)} → ${name(event.target)}`;
    case "agent_started":
      return `${name(event.department)} started`;
    case "agent_completed":
      return `${name(event.department)} ${event.status ?? "completed"}`;
    case "agent_failed":
      return `${name(event.department)} failed: ${event.message}`;
    default:
      return event.department ? `${name(event.department)}: ${event.message}` : event.message;
  }
}

export function ActivityFeed({ events, meta }: { events: ExecutionEvent[]; meta: GraphMeta }) {
  const labels = Object.fromEntries(meta.nodes.map((n) => [n.id, n.label]));
  const shown = events.filter((e) => e.event_type !== "handoff_completed"); // the started line already says it
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ block: "nearest" });
  }, [shown.length]);

  return (
    <section className="feed">
      <div className="feed__title">Activity</div>
      <div className="feed__list">
        {shown.length === 0 && <div className="muted">Start a run to see events.</div>}
        {shown.map((e) => (
          <div key={e.seq} className={`feed__row feed__row--${e.event_type}`}>
            <span className="muted">{formatTime(e.timestamp)}</span>
            <span className="feed__type">{e.event_type}</span>
            <span>{describe(e, labels)}</span>
          </div>
        ))}
        <div ref={end} />
      </div>
    </section>
  );
}
