import { formatTime, type RunView } from "@/lib/events";
import { handoffInfo, labelPath } from "@/lib/hierarchy";
import type { GraphMeta } from "@/lib/types";

interface Props {
  edgeId: string;
  meta: GraphMeta;
  view: RunView;
  onSelect: (id: string) => void;
  onClose: () => void;
}

const list = (items: string[]) => (items.length ? items.join(", ") : "—");

// Everything here comes from `view` (already in memory from the live/replayed event stream); no new fetch.
export function HandoffInspector({ edgeId, meta, view, onSelect, onClose }: Props) {
  const info = handoffInfo(meta, view, edgeId);
  if (!info) return null;

  return (
    <aside className="details">
      <div className="details__head">
        <div>
          <div className="details__title">Handoff</div>
          <div className="muted">{info.state}</div>
        </div>
        <button className="ghost" onClick={onClose} aria-label="Close details">
          ✕
        </button>
      </div>
      <dl>
        <dt>From</dt>
        <dd>
          <button className="ghost details__link" onClick={() => onSelect(info.source)}>
            {labelPath(meta, info.source)}
          </button>
        </dd>
        <dt>To</dt>
        <dd>
          <button className="ghost details__link" onClick={() => onSelect(info.target)}>
            {labelPath(meta, info.target)}
          </button>
        </dd>
        <dt>Artifacts produced by the sender so far</dt>
        <dd>{list(info.artifacts)}</dd>
        <dt>Summary</dt>
        <dd>{info.summary ?? "—"}</dd>
        <dt>Timestamp</dt>
        <dd>{formatTime(info.timestamp)}</dd>
      </dl>
    </aside>
  );
}
