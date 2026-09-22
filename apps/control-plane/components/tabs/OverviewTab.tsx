import { artifactNames, currentPhase, formatDuration, reviewVerdict, type RunView } from "@/lib/events";
import { completedAgentCount, labelPath } from "@/lib/hierarchy";
import type { GraphMeta, RunInfo } from "@/lib/types";
import { useArtifactText } from "@/lib/useArtifact";

interface Props {
  meta: GraphMeta;
  view: RunView;
  run: RunInfo | null;
  now: number;
}

interface ModelEvaluation {
  selected_model?: string;
  primary_metric?: string;
  metrics?: Record<string, number>;
}

// problem.yaml is written by yaml.safe_dump from a small, known set of scalar fields (schemas/problem.py) --
// a one-line grab of `target: <value>` beats pulling in a full YAML parser for one field.
function yamlField(text: string, key: string): string | null {
  const match = text.match(new RegExp(`^${key}:\\s*(.*)$`, "m"));
  const value = match?.[1].trim().replace(/^['"]|['"]$/g, "");
  return value ? value : null;
}

function tryParseJSON<T>(text: string | null): T | null {
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

const Row = ({ label, value }: { label: string; value: string }) => (
  <>
    <dt>{label}</dt>
    <dd>{value}</dd>
  </>
);

export function OverviewTab({ meta, view, run, now }: Props) {
  const runId = view.runId;
  const artifacts = artifactNames(view);
  const problemYaml = useArtifactText(artifacts.includes("problem.yaml") ? runId : null, "problem.yaml");
  const modelEval = useArtifactText(artifacts.includes("model_evaluation.json") ? runId : null, "model_evaluation.json");

  if (!runId) return <div className="muted center">No run selected.</div>;

  const target = problemYaml.text ? (yamlField(problemYaml.text, "target") ?? "—") : "—";
  const model = tryParseJSON<ModelEvaluation>(modelEval.text);
  const metric = model?.primary_metric && model.metrics ? model.metrics[model.primary_metric] : undefined;
  const phase = currentPhase(view);

  return (
    <div className="tabpane">
      <dl>
        <Row label="Run" value={runId} />
        <Row label="Status" value={view.status} />
        <Row label="Project" value={run?.project_name ?? "—"} />
        <Row label="Dataset" value={run?.dataset ?? "—"} />
        <Row label="Target" value={target} />
        <Row label="Current phase" value={phase ? labelPath(meta, phase) : "—"} />
        <Row label="Elapsed" value={formatDuration(view.startedAt, view.endedAt ?? now)} />
        <Row label="Agents completed" value={String(completedAgentCount(meta, view))} />
        <Row label="Artifacts" value={String(artifacts.length)} />
        <Row label="Review verdict" value={reviewVerdict(view) ?? run?.review_verdict ?? "—"} />
        <Row label="Model" value={model?.selected_model ?? (artifacts.includes("model_evaluation.json") ? "—" : "not available")} />
        <Row label="Main metric" value={model?.primary_metric && metric !== undefined ? `${model.primary_metric} = ${metric.toFixed(3)}` : "—"} />
      </dl>
    </div>
  );
}
