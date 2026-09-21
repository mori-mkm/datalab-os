# Evaluation and review protocol

Two independent roles, in this order. Neither implements the change it judges.

## Evaluator (tries to prove the acceptance criteria are NOT met)

**Receives:** the task's `Objective` + `Acceptance` + `Must preserve`, and the change scope
(`git diff --stat` and the list of changed files). Not the implementer's reasoning.

**Does:**
- runs the relevant suites, then goes past them: edge cases, failure paths, event order, replay/reconnect,
  demo vs real, graph metadata vs emitted events, backend schema vs `apps/control-plane/lib/types.ts`,
  missing artifacts, concurrent runs, invalid analytical output
- adds failing tests as evidence, or regression tests for confirmed gaps, in `tests/` or
  `apps/control-plane/lib/*.test.ts` only
- browser-validates UI-facing changes when appropriate
- **reports** product bugs; does not fix them

**Returns:** the standard return contract plus

```text
CRITERIA: each acceptance line -> MET | NOT MET | NOT VERIFIED (how it was checked)
FINDINGS: [severity] title, reproduction (test/command), expected vs actual
COVERAGE GAPS: what was not tried and why
```

## Reviewer (independent final verdict)

**Receives:** the task/handoff (objective, acceptance, out-of-scope), the Architect's plan if any, the diff
(`git diff --stat`, then per-file diffs), and the Evaluator's report. Not the whole repository.

**Checks:**
scope creep against the handoff's out-of-scope list · duplicated logic or a second definition of a contract ·
decorative abstractions/agents · new dependencies · hidden coupling (names, ids, paths) · security/privacy
(secrets, paths from user input, data leaving the machine) · scientific validity and wording of claims
(`ds-methodologist` findings resolved?) · missing or weak tests · docs/README claims the code does not support ·
accidental files (`workspace/`, `.next/`, `.venv/`, data, logs, screenshots) · contract drift
(events, `/api/graph`, artifact schemas, TypeScript types).

It reads outside the diff only to confirm a finding, and re-runs a test only to verify a claim it doubts.

**Verdicts**

| Verdict | Meaning |
|---|---|
| `APPROVE` | criteria met, no material findings |
| `APPROVE_WITH_NOTES` | mergeable; notes are non-blocking and listed |
| `REQUEST_CHANGES` | at least one reproducible blocking finding |

**Finding format** (must be reproducible):

```text
[BLOCKER|MAJOR|MINOR|NOTE] title
Where: file:line
Evidence: command/test/diff hunk that shows it
Why it matters: one sentence
Suggested fix: optional
```

A finding without evidence is a question, not a finding. Unsupported claims in the final report are findings.
