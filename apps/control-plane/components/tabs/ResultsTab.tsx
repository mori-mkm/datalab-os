import { VerdictBanner } from "@/components/VerdictBanner";
import { artifactNames, formatDuration, nodeTimingForArtifact, reviewVerdict, type RunView } from "@/lib/events";
import { useArtifactText } from "@/lib/useArtifact";
import type { RunInfo } from "@/lib/types";

interface Props {
  view: RunView;
  run: RunInfo | null;
  now: number;
}

interface ModelEvaluation {
  selected_model?: string;
  primary_metric?: string;
  metrics?: Record<string, number>;
}

interface Experiments {
  experiments?: unknown[];
}

function tryParseJSON<T>(text: string | null): T | null {
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

export function ResultsTab({ view, run, now }: Props) {
  const runId = view.runId;
  const artifacts = artifactNames(view);
  const modelText = useArtifactText(artifacts.includes("model_evaluation.json") ? runId : null, "model_evaluation.json");
  const experimentsText = useArtifactText(artifacts.includes("experiments.json") ? runId : null, "experiments.json");

  if (!runId) return <div className="muted center">No run selected.</div>;

  const model = tryParseJSON<ModelEvaluation>(modelText.text);
  const experiments = tryParseJSON<Experiments>(experimentsText.text);
  const verdict = reviewVerdict(view) ?? run?.review_verdict ?? null;
  const primaryMetric = model?.primary_metric && model.metrics ? model.metrics[model.primary_metric] : undefined;
  const timing = nodeTimingForArtifact(view, "experiments.json");

  return (
    <div className="tabpane">
      <VerdictBanner verdict={verdict} />
      <dl>
        <dt>Model</dt>
        <dd>{model?.selected_model ?? (artifacts.includes("model_evaluation.json") ? "—" : "not yet available")}</dd>
        <dt>Primary metric</dt>
        <dd>
          {model?.primary_metric && primaryMetric !== undefined ? `${model.primary_metric} = ${primaryMetric.toFixed(3)}` : "—"}
        </dd>
        <dt>Experiments</dt>
        <dd>
          {experiments?.experiments
            ? `${experiments.experiments.length} (${formatDuration(timing?.startedAt ?? null, timing?.endedAt ?? now)})`
            : artifacts.includes("experiments.json")
              ? "—"
              : "not yet available"}
        </dd>
        <dt>Artifacts</dt>
        <dd>{artifacts.length}</dd>
      </dl>
      {model?.metrics ? (
        <table>
          <thead>
            <tr>
              <th>metric</th>
              <th>value</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(model.metrics).map(([key, value]) => (
              <tr key={key}>
                <td>{key}</td>
                <td>{value.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <div className="muted">Metrics not yet available.</div>
      )}
    </div>
  );
}
