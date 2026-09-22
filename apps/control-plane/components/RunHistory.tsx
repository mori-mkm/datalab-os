import type { RunInfo } from "../lib/types";

interface Props {
  /** null = unknown/unavailable (endpoint down): the picker is hidden and nothing else is affected. */
  runs: RunInfo[] | null;
  currentId: string | null;
  onOpen: (runId: string) => void;
}

const shortId = (runId: string) => runId.split("_").pop() ?? runId; // run_YYYYmmdd_HHMMSS_xxxx -> xxxx

const startedAt = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit", hour12: false }) : "—";

export const runLabel = (run: RunInfo): string =>
  [`#${shortId(run.run_id)}`, run.dataset ? `${run.mode} ${run.dataset}` : run.mode, run.status, startedAt(run.created_at)].join(" · ");

export const runTitle = (run: RunInfo): string =>
  [run.project_name, run.error].filter(Boolean).join(" — ");

export function RunHistory({ runs, currentId, onOpen }: Props) {
  if (runs === null) return null;
  if (runs.length === 0) return <span className="muted">No past runs</span>;
  const current = runs.find((run) => run.run_id === currentId);
  return (
    <select
      className="history"
      aria-label="Past runs"
      value={current?.run_id ?? ""}
      title={current ? runTitle(current) : undefined}
      onChange={(event) => event.target.value && onOpen(event.target.value)}
    >
      <option value="" disabled>
        Past runs ({runs.length})
      </option>
      {runs.map((run) => (
        <option key={run.run_id} value={run.run_id} title={runTitle(run)}>
          {runLabel(run)}
        </option>
      ))}
    </select>
  );
}
