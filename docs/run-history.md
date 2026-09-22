# Persistent run history

Runs use `Settings.workspace_dir` (overridable with `DATALAB_WORKSPACE`). Each run directory contains an atomically replaced `run.json`, an append-only `events.jsonl`, and the existing artifacts. Events are appended under the event-bus lock before listeners receive them. Persistence errors are logged and do not change the analytical outcome.

## Recovery contract clarification

This clarification implements the recovery decision authorized during the interrupted milestone takeover. It resolves the original handoff's conflict between “missing events file yields []” and “historical streams end with a terminal event.” The raw log may be empty; the reconciled read view always has a terminal outcome.

- Missing or invalid `run.json`: not found (404; omitted from history).
- Log entries are read in file order. Skip malformed entries, foreign `run_id`s, nonpositive sequences, and sequences less than or equal to the last accepted sequence. First accepted sequence wins. Gaps are retained, never renumbered. Stop after the first accepted terminal event; trailing entries cannot reopen a finished run.
- A nonterminal summary with a terminal log takes its status and finished timestamp from the terminal event.
- A nonterminal summary with no terminal log is interrupted: synthesize failures for nodes whose latest status is running, then `run_failed`. Timestamps and ordering follow the last accepted events, or summary creation time for an empty log. `data.interrupted = true` identifies these events.
- A terminal summary with a missing, corrupt, or incomplete log retains its outcome. Append one matching `run_completed`, `run_rejected`, or `run_failed`, with `data.recovered = true`, sequence `last accepted seq + 1` (or 1), and matching `evt_%04d` ID. Timestamp is summary `finished_at`, falling back to last event or `created_at`, and never earlier than the last accepted event. No lost node results are invented; a damaged log cannot reproduce details that no longer exist.
- Recovery is deterministic and idempotent. Timestamps without an offset are treated as UTC when constructing the recovered terminal timestamp; stored events are unchanged. Reading never rewrites summaries or logs. The existing event schema and reducer remain unchanged.

In-process runs use memory, including completed runs. A fresh process reads disk without hydrating the bus. The service binds an injected, unused event bus to its own store; an already active bus is rejected rather than silently losing or redirecting its history.

## API and UI

`GET /api/runs?limit=50` returns the memory/disk union in descending run-ID order (limit 1–200). Within the same second, the random ID suffix breaks ties; this is not precise subsecond creation ordering. Get and events routes use memory first, disk on a miss. Historical SSE sends events with `seq > Last-Event-ID` then closes. An in-memory terminal run also closes immediately if its terminal sequence has already been consumed.

The history picker reuses get + SSE + the current graph. Start, selection and URL restoration share a request generation: only the latest action may replace the selected run or URL. Cleanup invalidates pending restoration and closes the current stream. A superseded successful POST still creates a run and refreshes history, but does not take over the view.

## Limits

Single-process ownership; no resume, deletion, retention, database or topology snapshot. A run owned by a different process can appear interrupted. Best-effort persistence cannot recover missing event details. History listing scans directories and may read logs for nonterminal summaries. Old runs are rendered against the current graph. Artifacts remain on disk and are not served by a new endpoint.

## Verification

Backend: `.\.venv\Scripts\python.exe -m pytest -q`.

Frontend, from `apps/control-plane`: `npm test`, `npm run lint`, `npm run build`.

`tests/test_api.py` exercises two independent app instances over the same workspace for completed demo, completed real and rejected runs, checking list/get/events/SSE and resume beyond the terminal sequence. Store tests cover corruption, read-only recovery, interruption and injected buses. `app/page.test.tsx` covers rendered history, stream switching, URL restore, unavailable states, delayed requests and unmount cleanup.
