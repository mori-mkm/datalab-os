# Spoken demo script (3–5 minutes)

For recording the video/GIF referenced in the README. Timestamps assume normal speaking pace; adjust
naturally. Actions describe exactly what to click, in order — see `docs/assets/README.md` for capture
settings.

---

## 0:00–0:20 — Hook

**Say:**
> "This is DataLab OS — a local-first AI organization for Data Science. It's not a chatbot. It's a real
> LangGraph pipeline of specialized agents — data engineering, analytics, modeling, and an independent
> review — and this console shows every decision they make, live."

**Do:** Start on `localhost:3000` with a fresh run already queued (or start one on camera using
`configs/problem.example.yaml`).

## 0:20–1:00 — Architecture, in the graph itself

**Say:**
> "This graph isn't drawn by the frontend — it's read directly off the compiled LangGraph graph the
> backend actually runs. Head of Data Science plans the run, then it hands off through Data Engineering,
> Analytics, and Data Science, each a real subgraph of its own agents, then an independent Review, then
> the final report."

**Do:** Stay on the **Execution** tab. Let the graph animate through department handoffs; point the
cursor at a department expanding into its agents (Engineering Lead → Data Profiler → Quality Analyst).

## 1:00–1:40 — Data, not a black box

**Say:**
> "Before any modeling happens, the console shows exactly what the agents are looking at — the real
> dataset, its columns, missing values, target distribution — pulled from the same profiling artifact
> the agents themselves produced, not re-computed by the frontend."

**Do:** Click the **Data** tab. Scroll the bounded row preview. Point out row/column counts and the
target distribution.

## 1:40–2:30 — Agent Inspector + Collaboration (the "no fake chat" moment)

**Say:**
> "Click any agent and you get its real task, the real tool it called — pandas, scikit-learn, whatever it
> actually ran — and what it produced. And this collaboration view isn't scripted dialogue — every line
> here traces back to one real event in the run's log. If an agent didn't emit it, it's not shown."

**Do:** Click a node (e.g. Data Profiler) → show the Agent Inspector's "Tools used" row. Switch to the
**Collaboration** tab → scroll the Handoff Timeline. Click an edge in the Execution graph → show the
Handoff Inspector (from/to, artifacts, summary, timestamp).

## 2:30–3:10 — Artifacts

**Say:**
> "Every artifact an agent produces is inspectable — JSON, Markdown, whatever it is — through a
> path-safe viewer. Nothing here is invented; it's the literal file the agent wrote."

**Do:** Click the **Artifacts** tab. Open `data_profile.json` (pretty-printed), then `report.md`
(rendered Markdown).

## 3:10–3:50 — Results & Review: the APPROVED run

**Say:**
> "Once modeling finishes, an independent Review agent audits it — not the same agent grading its own
> work. It checks for a baseline, a proper train/test split, a recorded seed, required metrics, and
> target leakage. This run passes every check: APPROVED."

**Do:** Click **Results** → show model + metrics + the green APPROVED banner. Click **Review** → show
the checklist, all green, verdict at top.

## 3:50–4:30 — The REJECTED example (optional but recommended)

**Say:**
> "Here's the same pipeline on a dataset with a hidden leak — a column that's basically a copy of the
> target. The Review agent catches it on its own, computes the correlation itself, and rejects the run.
> This is the same review logic that just approved the last run — it's not soft."

**Do:** Switch to a pre-recorded/historical `?run=<id>` for `configs/problem.leaky.yaml`. Show the red
REJECTED banner on Results, then the Review tab's failing `no_target_leakage` check with its real detail
text.

## 4:30–5:00 — Close

**Say:**
> "Everything you just saw — the graph, the tools, the handoffs, the review, the report — comes from one
> event log, persisted to disk, replayable after a restart. Zero paid APIs. 118 backend tests, 97
> frontend tests, all green. Repo link is below."

**Do:** Refresh the browser on the same `?run=<id>` to show state reconstructing instantly, then end on
the Overview tab.
