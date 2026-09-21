import { useEffect, useRef } from "react";
import { formatTime } from "@/lib/events";
import { labelPath } from "@/lib/hierarchy";
import type { ExecutionEvent, GraphMeta } from "@/lib/types";

function describe(event: ExecutionEvent, meta: GraphMeta): string {
  const name = labelPath(meta, event.node_id);
  switch (event.event_type) {
    case "handoff_started":
      return `Handoff: ${labelPath(meta, event.node_id)} → ${labelPath(meta, event.target)}`;
    case "agent_started":
      return `${name} started`;
    case "agent_completed":
      return `${name} ${event.status ?? "completed"}`;
    case "agent_failed":
      return `${name} failed: ${event.message}`;
    default:
      return event.node_id ? `${name}: ${event.message}` : event.message;
  }
}

export function ActivityFeed({ events, meta }: { events: ExecutionEvent[]; meta: GraphMeta }) {
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
            <span>{describe(e, meta)}</span>
          </div>
        ))}
        <div ref={end} />
      </div>
    </section>
  );
}
