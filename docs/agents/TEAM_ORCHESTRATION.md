# Development team orchestration

These are **development** agents (`.claude/agents/*.md`). They are not the runtime DataLab agents in
`src/datalab/agents/`. Matheus owns all Git history operations (add, commit, push, merge, PRs).

## Flow

```text
Matheus ─▶ Architect ─▶ bounded task(s) ─▶ Evaluator ─▶ Reviewer ─▶ Matheus
             (plan)     one owner each      (tries to    (independent
                                             break it)    verdict)
```

The lead Claude session coordinates: it calls the Architect, passes each specialist its handoff, and relays
results. It should not implement cross-cutting work itself.

## Roles

| Agent | Owns | Does not own |
|---|---|---|
| `architect` | task graph, contract decisions, owners, acceptance criteria, handoffs | implementation, approval |
| `langgraph-engineer` | `src/datalab/{graphs,agents,services,schemas,api}`, `state.py`, backend tests for its change | UI, statistical methodology, final review |
| `control-plane-engineer` | `apps/control-plane/**`, frontend tests, UI behavior | backend rules, methodology, workflow topology |
| `ds-methodologist` | validity of analysis: framing, splits, leakage, metrics, wording of claims; `tools/`, `configs/` when the task is analytical | frontend, orchestration |
| `evaluator` | adversarial tests, regressions, replay/failure/drift checks, browser validation | fixing product code, architectural approval |
| `reviewer` | final independent verdict on task + diff + evidence | writing code, re-running the whole project |

## Which agents does a task need?

| Task | Agents |
|---|---|
| One-file fix in a single area | that area's owner (+ `reviewer` if non-trivial) |
| Feature inside one area | owner → `evaluator` → `reviewer` |
| Contract or cross-area change | `architect` first, then owners, `evaluator`, `reviewer` |
| Changes what an analysis *means* (split, metric, leakage, claim wording) | `architect` → `ds-methodologist` **before** coding → owner → `evaluator` → `reviewer` |
| Docs-only | the author, `reviewer` if it makes claims about behavior |

Skipping an agent is the default; add one only when its concern is actually touched. Worked examples:
`docs/agents/EXAMPLES.md`.

## Context rules (token budget)

- Handoffs follow `TASK_HANDOFF.md`: objective, owner, a **short read-first list** (≤ 5 files), stable contracts,
  acceptance, out-of-scope. The repo history and the whole architecture are not part of a handoff.
- Shared principles live in the root `CLAUDE.md` and the README, not in the agent files. Agent files hold only
  mission, scope, boundaries, workflow and output contract.
- Agents locate code with targeted `Grep`/`Glob` and read line ranges, not whole directories. Widen the read only
  on evidence (a failing test, a contract that does not match) and say why in the return.
- Durable artifacts beat long messages: for multi-task work the Architect writes one file per task to
  `.claude/handoffs/` (git-ignored, ephemeral) and hands agents the path.
- Return contracts are short and structured (below); no restating the task.

## Ownership rules

- **1 task = 1 owner.** Only one agent edits files for a task at a time; two tasks that need the same file are
  sequenced, not parallelized.
- Cross-cutting features are decomposed by the Architect (backend contract → UI consumption → evaluation →
  review). Never "one agent implements everything".
- A specialist may touch a neighboring file when the change is incoherent without it, and must say so under
  `ASSUMPTIONS`. It must not redesign the neighbor's area.
- Independence: the Evaluator does not fix what it finds and the Reviewer does not reuse the Evaluator's
  conclusions unchecked. Neither implements the change under judgment.
- Blocked or ambiguous? Return `BLOCKED` or `NEEDS_DECISION`; never invent behavior to keep moving.

## Return contract (every specialist)

```text
STATUS: DONE | BLOCKED | NEEDS_DECISION
CHANGED: files (one line each, why)
TESTS: commands run and results
ASSUMPTIONS:
OPEN RISKS:
NEXT HANDOFF: who should act next and on what
```

The `evaluator` and `reviewer` add their verdicts per `REVIEW_PROTOCOL.md`.

## Parallelism

Parallel work is allowed only when tasks do not touch the same files **and** the contract between them is already
fixed. Typical: once the Architect has frozen an event/API contract, `langgraph-engineer` and
`control-plane-engineer` work independently against it. Do not parallelize while a contract is still moving, and
never for tasks that share an unstable file. Correctness before speed.

## Git worktrees (optional; Matheus creates them)

Useful for truly independent tasks on separate branches with little file overlap (for example a docs task next to
a backend task). Not useful while a shared contract is changing, when tasks touch the same files, or for tiny
changes: the merge cost exceeds the gain. Agents never create, switch or merge worktrees or branches; if a task
would benefit, say so under `NEXT HANDOFF` and let Matheus decide.

## Not part of this harness

No task database, scheduler, dashboards, external trackers, autonomous commits or PRs, and no LangGraph for the
development process. Markdown definitions plus this discipline are enough for a project this size. If
coordination costs more than the coding, simplify.
