# Run-history milestone verification

Executed locally on 2026-09-21. This report covers the recovered working tree, including previously untracked Claude implementation files. No Git staging, commit, push, reset, restore or history operation was performed.

## Automated gates

- `.\.venv\Scripts\python.exe -m pytest -q`: 114 passed, 0 failed. One dependency deprecation warning from Starlette/AnyIO.
- `npm test`: 60 passed, 0 failed across seven files.
- `npm run lint`: exit 0.
- `npm run build`: exit 0; Next.js production compilation, TypeScript and static generation succeeded.

The initial inherited backend baseline was 81 passed, 1 failed, 2 setup errors. All three failures came from positional `message` arguments in the unfinished persistence tests; `EventBus.emit` requires keyword arguments. Initial frontend baseline: 49 passed.

## Real integration

Production Next.js (`npm run start`) on `127.0.0.1:3000`, Uvicorn on `127.0.0.1:8000`, LLM disabled. Isolated generated data: `workspace/rh-verification-20260921/runs`. Browser driven with agent-browser; no mocked backend for these scenarios.

| Scenario | Observed result |
|---|---|
| Empty workspace | “No past runs”; run buttons available |
| UI Run demo | `run_20260921_222052_910f`, completed, 90 events |
| UI Run real | `run_20260921_222055_16bc`, completed, 84 events |
| UI Run real (leaky) | `run_20260921_222056_1a26`, rejected, 84 events |
| History list | All runs present, descending ID order; mode/dataset/status/time labels rendered |
| Actual backend process restart | All three summaries and event payloads identical before/after restart |
| Historical selection after restart | URL changed; replayed graph node IDs/text/statuses identical to original live view for all three runs |
| Historical SSE | Full replay, final two events, and empty responses at/beyond terminal sequence; every response closed within a 5-second timeout |
| Live SSE with future cursor | Real POST followed immediately by `Last-Event-ID: 10000`: zero frames, EOF at terminal, completed summary |
| Reload `?run=...16bc` | Same real run restored; COMPLETED and duration displayed |
| Delayed real POST, then historical selection | Response delivery delayed in browser while actual POST hit backend; later selection remained selected after POST resolved |
| Unknown run URL | “Cannot open …: run not found”; run buttons remained available |
| Backend process stopped | Backend-unreachable message, history hidden, start buttons disabled |
| Force-kill during live demo | `run_20260921_222331_b239`: persisted summary remained running; after restart, ERROR with 17 reconciled events, no node running |
| Interrupted repeated reads | Identical results, byte-identical persisted files; SSE closed; UI displayed ERROR |
| Terminal summary without log | Isolated fixture `run_20260921_222400_cafe`: synthetic recovered terminal, UI COMPLETED, no events file created by reading |
| Browser integrity | No uncaught page errors or framework error overlay in verified normal/recovery flows |

Screenshots remain generated artifacts in the ignored workspace; `recovered.png` shows the terminal-summary recovery case. Without a log, node details remain unknown/waiting rather than fabricated.

## Regression coverage

`tests/test_api.py`: two independent app instances, all run outcomes, list/get/events/stream equality, Last-Event-ID, terminal EOF, interrupted and recovered tails, invalid limits and missing/corrupt IDs.

`tests/test_run_store.py`: atomic write failures, persistence-before-delivery, independent concurrent logs, memory precedence, read-only recovery across terminal outcomes and damage types, foreign/duplicate/out-of-order sequence rejection, injected bus binding, workspace override, mixed timezone timestamps.

`apps/control-plane/app/page.test.tsx`: rendered history labels/order/tooltip, stream switching/close, terminal refresh, URL restore, unavailable/empty/unknown states, delayed start and selection, pending restore superseded or unmounted. React Testing Library and jsdom are test-only dependencies.

## Independent evaluation

The independent evaluator inspected production code and tests and reproduced two edge cases. No BLOCKER/HIGH was found.

- MEDIUM, fixed: mixed timezone timestamps could raise `TypeError` during synthetic terminal recovery. Recovery normalizes comparison to UTC, with two regression cases.
- LOW, fixed after evaluation: a cursor ahead of an active run received subsequent live events below the cursor. SSE now filters every delivered frame by `seq > after`, while still closing when a filtered terminal arrives. `test_live_stream_with_future_cursor_filters_events_but_closes_at_terminal` verifies EOF and listener cleanup.

The evaluator's independent probes are distinguished from the root's recorded full gates and browser integration above.

## Independent final review

Verdict: **APPROVE_WITH_NOTES**. The reviewer independently inspected code, tests and contract, and reran `tests/test_api.py` plus `tests/test_run_store.py`: 73 passed. No BLOCKER/HIGH or additional milestone correction was required. Accepted limitations remain documented in `docs/run-history.md`.

The verification browser and backend/frontend processes started for this session were stopped after verification. Generated evidence remains in the ignored workspace.
