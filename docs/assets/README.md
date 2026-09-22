# Capturing demo assets

This directory holds the recorded demo media referenced by the root `README.md`. Nothing here is
committed as binary yet — this file documents how to produce it. Follow `docs/DEMO.md` for the spoken
script; this file covers the *capture* mechanics.

## Prerequisites

- Backend running: `uvicorn datalab.api.app:app --reload`
- Frontend running: `cd apps/control-plane; npm run dev`
- Two runs ready before recording (avoid dead air waiting on a live run):
  - one completed **APPROVED** run from `configs/problem.example.yaml`
  - one completed **REJECTED** run from `configs/problem.leaky.yaml`
  - keep both `run_id`s handy for `?run=<id>` navigation during capture

## GIF capture sequence

Short, looping, README-hero-sized — no audio, no talking-head, just the product moving.

**File:** `docs/assets/demo.gif`
**Recommended dimensions:** 960×540 (16:9), ≤ 8 MB, 12–15 fps
**Length:** 12–18 seconds, loop-friendly (first and last frame visually similar)

Sequence:
1. Land on **Execution** tab, live/historical run — graph visible, a couple of nodes already completed.
2. Click a completed agent node → Agent Inspector opens showing "Tools used."
3. Switch to **Collaboration** tab → Handoff Timeline scrolls into view.
4. Switch to **Results** tab → APPROVED banner + metrics visible.
5. Hold last frame ~1s before loop restarts.

## Full video capture sequence

Matches `docs/DEMO.md` beat for beat — record screen + voiceover together, or screen first and narrate
over it after.

**File:** `docs/assets/demo-full.mp4`
**Recommended dimensions:** 1920×1080, 30fps, H.264
**Length:** 3–5 minutes (see `docs/DEMO.md` timestamps)

Exact screens to capture, in order:
1. **Overview** tab of the APPROVED run — run id, status, problem, dataset, target, verdict, model + metric.
2. **Execution** tab — full graph, department → agent expansion, animated handoff.
3. **Data** tab — dataset facts + bounded row preview.
4. A completed agent node's **Agent Inspector** — task, tools used, decision text, outputs, handoff.
5. **Collaboration** tab — Handoff Timeline, scrolled through 2–3 handoffs.
6. An edge click → **Handoff Inspector** (from/to, artifacts, summary, timestamp).
7. **Artifacts** tab — open `data_profile.json` (JSON viewer) and `report.md` (Markdown viewer).
8. **Results** tab (APPROVED run) — model, metrics table, green banner.
9. **Review** tab (APPROVED run) — full checklist, all green, verdict at top.
10. Switch to the REJECTED run via `?run=<id>`: **Results** tab red banner, then **Review** tab showing
    the failing `no_target_leakage` check with its real detail text.
11. Browser refresh on the REJECTED run's `?run=<id>` — state reconstructs, no flash of empty/error state.
12. End on **Overview** tab.

## Filenames

| File | Purpose |
|---|---|
| `docs/assets/demo.gif` | README hero GIF |
| `docs/assets/demo-full.mp4` | full spoken walkthrough (linked from README, not embedded) |
| `docs/assets/screenshot-overview.png` | static fallback if GIF/video aren't ready yet |
| `docs/assets/screenshot-review-rejected.png` | static fallback showing the REJECTED verdict |

## Notes

- Never record real credentials, tokens, or `.env` contents on screen.
- Prefer the small `problem.small.yaml` run first if you need a fast dry run of the capture flow before
  recording the final takes with `problem.example.yaml`/`problem.leaky.yaml`.
- Keep the browser window at the target recording resolution before starting the run, so the graph layout
  doesn't reflow mid-capture.
