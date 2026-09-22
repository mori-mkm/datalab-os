import { formatDuration, type RunView } from "@/lib/events";
import type { Health } from "@/lib/types";
import type { RunInfo } from "@/lib/types";
import { RunHistory } from "./RunHistory";
import { StatusBadge } from "./StatusBadge";

interface Props {
  view: RunView;
  now: number;
  health: Health | null;
  backendError: string | null;
  busy: boolean;
  runs: RunInfo[] | null;
  onStart: (mode: "demo" | "real", config?: string) => void;
  onOpen: (runId: string) => void;
}

export function RunHeader({ view, now, health, backendError, busy, runs, onStart, onOpen }: Props) {
  const llm = health?.llm.available
    ? `Ollama · ${health.llm.model}`
    : health
      ? "LLM off · deterministic text"
      : "backend unreachable";
  return (
    <header className="header">
      <div className="header__title">
        <strong>DataLab OS</strong>
        <span className="muted">{view.runId ?? "no run yet"}</span>
      </div>
      <div className="header__meta">
        <span className="chip">LOCAL</span>
        <span className={`chip ${health?.llm.available ? "chip--ok" : ""}`}>{llm}</span>
        {view.mode && <span className="chip">{view.mode === "demo" ? "DEMO WORKFLOW" : "REAL RUN"}</span>}
        {view.startedAt && <span className="muted">{formatDuration(view.startedAt, view.endedAt ?? now)}</span>}
        <StatusBadge status={view.status} />
      </div>
      <RunHistory runs={runs} currentId={view.runId} onOpen={onOpen} />
      <div className="header__actions">
        <button disabled={busy || !health} onClick={() => onStart("demo")}>
          Run demo
        </button>
        <button disabled={busy || !health} onClick={() => onStart("real", "problem.example")}>
          Run real
        </button>
        <button disabled={busy || !health} onClick={() => onStart("real", "problem.leaky")} title="Dataset with a hidden target leak: the review should reject it">
          Run real (leaky)
        </button>
      </div>
      {backendError && <div className="header__error">{backendError}</div>}
    </header>
  );
}
