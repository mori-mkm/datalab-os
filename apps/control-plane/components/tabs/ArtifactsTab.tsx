import { useState } from "react";
import Markdown from "markdown-to-jsx";
import { artifactNames, type RunView } from "@/lib/events";
import { useArtifactText } from "@/lib/useArtifact";

function renderArtifact(name: string, text: string) {
  if (name.endsWith(".json")) {
    try {
      return <pre>{JSON.stringify(JSON.parse(text), null, 2)}</pre>;
    } catch {
      return <pre>{text}</pre>; // malformed on disk: show it verbatim rather than crash
    }
  }
  if (name.endsWith(".md")) return <Markdown>{text}</Markdown>;
  return <pre>{text}</pre>;
}

export function ArtifactsTab({ view }: { view: RunView }) {
  const runId = view.runId;
  const names = artifactNames(view);
  const [selected, setSelected] = useState<string | null>(null);
  const content = useArtifactText(selected ? runId : null, selected);

  if (!runId) return <div className="muted center">No run selected.</div>;

  return (
    <div className="tabpane artifacts">
      <ul className="artifacts__list">
        {names.length === 0 && <li className="muted">No artifacts yet.</li>}
        {names.map((name) => (
          <li key={name}>
            <button className="ghost details__link" aria-current={selected === name} onClick={() => setSelected(name)}>
              {name}
            </button>
          </li>
        ))}
      </ul>
      <div className="artifacts__viewer">
        {!selected && <div className="muted center">Select an artifact.</div>}
        {selected && content.error && <div className="muted">Artifact unavailable.</div>}
        {selected && !content.error && content.text === null && <div className="muted">Loading…</div>}
        {selected && content.text !== null && renderArtifact(selected, content.text)}
      </div>
    </div>
  );
}
