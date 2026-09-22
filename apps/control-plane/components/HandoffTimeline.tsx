import { formatTime, type RunView } from "@/lib/events";
import { timelineOf, type TimelineEntry } from "@/lib/timeline";
import type { GraphMeta } from "@/lib/types";

/** Consecutive entries from the same actor become one chat-like group (no reordering: still chronological). */
function groupByActor(entries: TimelineEntry[]): TimelineEntry[][] {
  const groups: TimelineEntry[][] = [];
  for (const entry of entries) {
    const last = groups[groups.length - 1];
    if (last && last[0].actor === entry.actor) last.push(entry);
    else groups.push([entry]);
  }
  return groups;
}

// Chronological, chat-like view of the run's real events. Built only from `timelineOf` (lib/timeline.ts) —
// no event interpretation happens here, this component only lays out entries it's given.
export function HandoffTimeline({ view, meta }: { view: RunView; meta: GraphMeta }) {
  if (!view.runId) return <div className="muted center">No run selected.</div>;
  const entries = timelineOf(view.events, meta);
  if (!entries.length) return <div className="muted center">Start a run to see the handoff timeline.</div>;

  return (
    <div className="tabpane timeline">
      {groupByActor(entries).map((group) => (
        <div key={group[0].event_id} className="timeline__group">
          <div className="timeline__actor">{group[0].actor}</div>
          {group.map((entry) => (
            <div key={entry.event_id} className={`timeline__bubble timeline__bubble--${entry.kind}`}>
              <span className="muted">{formatTime(entry.timestamp)}</span> {entry.message}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
