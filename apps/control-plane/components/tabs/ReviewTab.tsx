import { VerdictBanner } from "@/components/VerdictBanner";
import { artifactNames, reviewVerdict, type RunView } from "@/lib/events";
import { useArtifactText } from "@/lib/useArtifact";

interface Props {
  view: RunView;
}

interface ReviewCheck {
  name: string;
  passed: boolean;
  detail: string;
}

interface Review {
  verdict?: string;
  checks?: ReviewCheck[];
}

function tryParseJSON<T>(text: string | null): T | null {
  if (!text) return null;
  try {
    return JSON.parse(text) as T;
  } catch {
    return null;
  }
}

export function ReviewTab({ view }: Props) {
  const runId = view.runId;
  const artifacts = artifactNames(view);
  const reviewText = useArtifactText(artifacts.includes("review.json") ? runId : null, "review.json");

  if (!runId) return <div className="muted center">No run selected.</div>;

  const review = tryParseJSON<Review>(reviewText.text);
  const verdict = review?.verdict ?? reviewVerdict(view) ?? null;

  return (
    <div className="tabpane">
      <VerdictBanner verdict={verdict} />
      {review?.checks ? (
        <ul className="checklist">
          {review.checks.map((check) => (
            <li key={check.name} className={`checklist__item ${check.passed ? "checklist__item--pass" : "checklist__item--fail"}`}>
              <span className="checklist__icon" aria-hidden>
                {check.passed ? "✓" : "✕"}
              </span>
              <span className="checklist__name">{check.name}</span>
              <span className="checklist__detail">{check.detail}</span>
            </li>
          ))}
        </ul>
      ) : (
        <div className="muted">Review checklist not yet available.</div>
      )}
    </div>
  );
}
