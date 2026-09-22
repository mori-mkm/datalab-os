import { useEffect, useState } from "react";
import { artifactNames, type RunView } from "@/lib/events";
import { getDatasetPreview, type DatasetPreview } from "@/lib/api";
import type { RunInfo } from "@/lib/types";
import { useArtifactText } from "@/lib/useArtifact";

interface Props {
  view: RunView;
  run: RunInfo | null;
}

interface DataProfile {
  rows: number;
  columns: number;
  dtypes: Record<string, string>;
  missing: Record<string, { count: number; pct: number }>;
  target?: { column: string; positive_rate: number };
}

interface DataQuality {
  duplicate_rows: number;
  missing_pct: number;
  issues: string[];
}

function tryParseJSON<T>(text: string | null): T | null {
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

function useDatasetPreview(runId: string | null): DatasetPreview | null {
  const [preview, setPreview] = useState<DatasetPreview | null>(null);
  useEffect(() => {
    if (!runId) return;
    let live = true;
    getDatasetPreview(runId).then(
      (value) => { if (live) setPreview(value); },
      () => { if (live) setPreview({ available: false, columns: [], rows: [], truncated: false }); },
    );
    return () => { live = false; };
  }, [runId]);
  return preview;
}

export function DataTab({ view, run }: Props) {
  const runId = view.runId;
  const artifacts = artifactNames(view);
  const profile = tryParseJSON<DataProfile>(useArtifactText(artifacts.includes("data_profile.json") ? runId : null, "data_profile.json").text);
  const quality = tryParseJSON<DataQuality>(useArtifactText(artifacts.includes("data_quality.json") ? runId : null, "data_quality.json").text);
  const preview = useDatasetPreview(runId);

  if (!runId) return <div className="muted center">No run selected.</div>;

  return (
    <div className="tabpane">
      <h3>{run?.dataset ?? "Dataset"}</h3>
      {!profile ? (
        <div className="muted">Profile not available for this run.</div>
      ) : (
        <>
          <dl>
            <dt>Rows</dt>
            <dd>{profile.rows}</dd>
            <dt>Columns</dt>
            <dd>{profile.columns}</dd>
            {profile.target && (
              <>
                <dt>Target</dt>
                <dd>
                  {profile.target.column} · positive rate {(profile.target.positive_rate * 100).toFixed(1)}%
                </dd>
              </>
            )}
            {quality && (
              <>
                <dt>Quality</dt>
                <dd>
                  {quality.duplicate_rows} duplicate rows · {(quality.missing_pct * 100).toFixed(2)}% missing cells
                  {quality.issues.length > 0 && ` · ${quality.issues.join(", ")}`}
                </dd>
              </>
            )}
          </dl>
          <table>
            <thead>
              <tr>
                <th>Column</th>
                <th>Type</th>
                <th>Missing</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(profile.dtypes).map(([column, dtype]) => {
                const missing = profile.missing[column];
                return (
                  <tr key={column}>
                    <td>{column}</td>
                    <td>{dtype}</td>
                    <td>{missing ? `${missing.count} (${(missing.pct * 100).toFixed(1)}%)` : "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}
      <h3>Preview</h3>
      {!preview ? (
        <div className="muted">Loading…</div>
      ) : !preview.available ? (
        <div className="muted">Preview unavailable for this run.</div>
      ) : (
        <>
          <table>
            <thead>
              <tr>
                {preview.columns.map((column) => (
                  <th key={column}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row, i) => (
                <tr key={i}>
                  {preview.columns.map((column) => (
                    <td key={column}>{String(row[column] ?? "")}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
          {preview.truncated && <div className="muted">Bounded sample shown; not the full dataset.</div>}
        </>
      )}
    </div>
  );
}
