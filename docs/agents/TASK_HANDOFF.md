# Task handoff

The unit of delegation. Keep each handoff under ~40 lines; it replaces conversation history, so it must be
self-sufficient. For multi-task work save it as `.claude/handoffs/<task-id>.md` (git-ignored) and pass the path.

## Template

```text
TASK <id>
Owner: architect | langgraph-engineer | control-plane-engineer | ds-methodologist | evaluator | reviewer
Objective: one or two sentences, observable outcome

Read first (≤ 5, in order):
- path[:lines], why

Inputs / dependencies:
- completed tasks or artifacts this builds on (with paths)

Must preserve:
- contracts and behavior that may not change (events, /api/graph, artifact schemas, ids, tests)

Implement:
- concrete steps, smallest change that satisfies the objective

Acceptance:
- testable criteria; commands that must pass

Do not touch:
- files/areas and features out of scope

Return: STATUS / CHANGED / TESTS / ASSUMPTIONS / OPEN RISKS / NEXT HANDOFF
```

## Rules

- **Objective and acceptance are mandatory.** A task without testable acceptance is not ready.
- **Read first is a starting point, not a cage.** Widen only on evidence and report why.
- **One owner.** If two owners are needed, it is two tasks with a stated dependency.
- **Contracts by name.** Refer to `schemas/event.py`, `/api/graph`, `artifact: experiments.json`, not to prose.
- **Out-of-scope is explicit.** Include the tempting neighbors (persistence, new agents, UI polish...).
- **Ambiguity is returned, not guessed:** use `NEEDS_DECISION` with options and a recommendation.

## Return contract

```text
STATUS: DONE | BLOCKED | NEEDS_DECISION
CHANGED: path: why
TESTS: exact commands and results (X passed / Y failed); what is NOT covered
ASSUMPTIONS: decisions taken without confirmation, neighbor files touched and why
OPEN RISKS: known gaps, things the evaluator/reviewer should look at
NEXT HANDOFF: next owner and the one thing they need to know
```
