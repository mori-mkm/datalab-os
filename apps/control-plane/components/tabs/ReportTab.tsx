import Markdown from "markdown-to-jsx";
import { artifactNames, type RunView } from "@/lib/events";
import { useArtifactText } from "@/lib/useArtifact";

interface Props {
  view: RunView;
}

export function ReportTab({ view }: Props) {
  const runId = view.runId;
  const artifacts = artifactNames(view);
  const report = useArtifactText(artifacts.includes("report.md") ? runId : null, "report.md");

  if (!runId) return <div className="muted center">No run selected.</div>;
  if (!artifacts.includes("report.md")) return <div className="muted center">Report not yet available.</div>;
  if (report.error) return <div className="muted center">Report unavailable.</div>;
  if (report.text === null) return <div className="muted center">Loading…</div>;

  return (
    <div className="tabpane">
      <Markdown>{report.text}</Markdown>
    </div>
  );
}
