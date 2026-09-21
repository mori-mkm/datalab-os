# Worked examples (hypothetical, not implemented)

Read this only when planning; it is intentionally not part of every agent's context. Paths marked *(new)* do not
exist yet; every other path exists today. Handoffs are shown condensed: real ones follow `TASK_HANDOFF.md`.

## A. "Persist run history and replay after API restart"

No analytical semantics change, so **`ds-methodologist` is not invoked**.

| Task | Owner | Depends on | Parallel? |
|---|---|---|---|
| A. Freeze the persistence contract | `architect` | none | no |
| B. `RunRepository` + write-through + list/replay API | `langgraph-engineer` | A | with C |
| C. Run-history list and loading a past run | `control-plane-engineer` | A | with B |
| D. Restart / replay / corruption tests | `evaluator` | B, C | no |
| E. Final diff review | `reviewer` | D | no |

**A. Contract (Architect writes it into B's and C's handoffs).** Reuse `workspace/<run_id>/` (no database):
`run.json` (a serialized `RunInfo`) and append-only `events.jsonl` (one `ExecutionEvent` per line, `seq`
contiguous from 1). On startup, load runs from disk; a run still `running` becomes `error` ("interrupted").
New `GET /api/runs` returns run summaries, newest first. Existing endpoints and event fields stay unchanged.
Corrupt trailing line: ignore and log, never crash. *Out of scope:* SQLite/Postgres, retention, resume of
interrupted runs, authentication.

**B. LangGraph Engineer.** Read first: `services/run_service.py`, `services/event_bus.py`, `schemas/run.py`,
`api/runs.py`, `tests/test_api.py`. Must preserve: SSE replay semantics (`Last-Event-ID`), event contract,
in-memory behavior for live runs. Accept: restart test recovers events and status; `GET /api/runs` payload as
frozen in A. Not touched: `apps/control-plane/`, `tools/`, graph topology.
*(New file: `services/run_repository.py`.)*

**C. Control Plane Engineer.** Read first: `apps/control-plane/lib/api.ts`, `lib/types.ts`, `lib/events.ts`,
`app/page.tsx`, and the frozen `GET /api/runs` payload from A (a fixture, not the backend code). Must preserve:
the reducer is pure and unchanged in meaning; graph comes from `/api/graph`. Accept: history list; opening a
past run reproduces the same final view as live delivery; tests pass. Not touched: `src/`.

**D. Evaluator.** Receives A's acceptance + `git diff --stat`. Attacks: restart with a run mid-flight;
truncated last JSONL line; duplicated or gapped `seq`; missing `run.json`; empty workspace; two runs at once;
`Last-Event-ID` beyond history; page refresh on a historical run; every persisted `node_id` exists in
`/api/graph`. Reports bugs, does not fix them.

**E. Reviewer.** Receives A, the diff, D's report. Checks: no database crept in, no second `RunInfo`
definition, `workspace/` not committed, path handling of `run_id` from URLs (no traversal), README claims.

## B. "Replace the random train/test split with temporal validation"

Analytical semantics change, so **`ds-methodologist` runs before any code**.

| Task | Owner | Depends on | Parallel? |
|---|---|---|---|
| A. Scope and affected contracts | `architect` | none | no |
| B. Validation protocol (scientific contract) | `ds-methodologist` | A | no |
| C. Implement the protocol | `langgraph-engineer` | B | no |
| D. Leakage / reproducibility / edge tests | `evaluator` | C | no |
| E. Final diff review | `reviewer` | D | no |

`control-plane-engineer` is not invoked: nothing in `/api/graph` or the event stream changes.

**A. Architect.** Affected: `schemas/problem.py` (new split config), `agents/ds_lead.py` (plan),
`agents/baseline_modeler.py` and `tools/baseline.py` (split), `tools/review.py` (split checks),
`agents/report.py` (wording), `experiments.json` schema, `tests/test_tools.py`, `tests/test_graph.py`.
Decision needed first: what "temporal" means, so it is B's task, not a coding choice.

**B. Methodologist (protocol mode) must define**, before coding: required `time_column` and its validation
(parseable, no missing values, timezone handling); cutoff rule (earliest to cutoff train, later test; no
shuffling, no stratification) and how ties at the cutoff are treated; both classes required in both partitions
or fail loudly; the time column excluded from features; preprocessing fitted on train only; what is recorded
(cutoff, train/test date ranges, sizes, seed for the model); what the review must check (train max < test min;
time column not a feature; split kind recorded); report wording ("out-of-time estimate", not comparable to the
random-split numbers, no causal language); tests the evaluator must write. Output goes to
`.claude/handoffs/<id>-protocol.md` and becomes C's handoff.

**C. LangGraph Engineer.** Read first: the protocol, `schemas/problem.py`, `tools/baseline.py`,
`tools/review.py`, `agents/ds_lead.py`. Must preserve: `problem.example.yaml` still APPROVED and
`problem.leaky.yaml` still REJECTED unless the protocol says otherwise; `DataLabState` small; event contract.
Accept: protocol implemented exactly; existing suites green. It does not choose analytical details.

**D. Evaluator.** Attacks: test rows earlier than train rows must be rejected; unsorted input; duplicated
timestamps at the cutoff; missing or unparseable timestamps; one class in the test partition; time column
leaking into features; same seed gives identical results; leaky config still REJECTED.

**E. Reviewer.** Adds a check that the protocol's wording rules appear in the report and that no claim outruns
the evidence; may call `ds-methodologist` in review mode if a validity doubt remains.

## Context each role should NOT receive (quick self-check)

| Role | Not part of its context |
|---|---|
| `langgraph-engineer` (A-B) | React components, layout code, browser concerns |
| `control-plane-engineer` (A-C) | `services/`, `graphs/`, backend tests; only the frozen payload |
| `evaluator` | the implementer's reasoning; tasks it did not attack |
| `reviewer` | the full repository; anything outside the diff unless confirming a finding |
| `ds-methodologist` | orchestration, UI; present only in example B |
