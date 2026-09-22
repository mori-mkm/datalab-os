"use client";

import { useEffect, useState } from "react";
import { getArtifact } from "./api";

export interface ArtifactText {
  /** null until loaded (or when `name` is null, i.e. not requested yet). */
  text: string | null;
  error: boolean;
}

const idle: ArtifactText = { text: null, error: false };

function key(runId: string | null, name: string | null): string {
  return `${runId ?? ""}\u0000${name ?? ""}`;
}

/** Fetches one artifact's raw content once per (runId, name) pair. Works identically for a live run and a
 * historical replay: both go through the same `GET /artifacts/{name}` call. Callers should key their component
 * by run id so switching runs resets this state instead of showing the previous run's artifact. */
export function useArtifactText(runId: string | null, name: string | null): ArtifactText {
  // State is tagged with the (runId, name) it was fetched for. If the caller has since moved on to a
  // different pair, the render below reports `idle` instead of the stale result — this avoids ever
  // showing one artifact's content mislabeled as another's while the new fetch is in flight, without
  // resorting to a synchronous setState in the effect (disallowed: react-hooks/set-state-in-effect).
  const [{ forKey, result }, setState] = useState<{ forKey: string; result: ArtifactText }>({
    forKey: key(null, null),
    result: idle,
  });

  useEffect(() => {
    if (!runId || !name) return;
    let live = true;
    getArtifact(runId, name).then(
      (text) => { if (live) setState({ forKey: key(runId, name), result: { text, error: false } }); },
      () => { if (live) setState({ forKey: key(runId, name), result: { text: null, error: true } }); },
    );
    return () => { live = false; };
  }, [runId, name]);

  return forKey === key(runId, name) ? result : idle;
}
