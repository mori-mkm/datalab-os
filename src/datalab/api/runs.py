from __future__ import annotations

import re

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, ValidationError

from datalab.api.events import event_stream, replay_stream
from datalab.schemas.event import ExecutionEvent
from datalab.schemas.problem import load_problem
from datalab.schemas.run import RunInfo, RunMode
from datalab.services.artifacts import _scrub
from datalab.services.run_service import RunService
from datalab.tools.profiling import load_dataset

router = APIRouter(prefix="/api")

_CONTENT_TYPES = {".json": "application/json", ".md": "text/markdown", ".yaml": "text/yaml", ".yml": "text/yaml"}


class RunRequest(BaseModel):
    mode: RunMode = "demo"
    config: str = "problem.example"  # name of a file in configs/ (without .yaml); real mode only


def _service(request: Request) -> RunService:
    return request.app.state.runs


def _known_run(request: Request, run_id: str) -> RunInfo:
    info = _service(request).get(run_id)
    if info is None:
        raise HTTPException(404, f"run '{run_id}' not found")
    return info


@router.post("/runs", status_code=202)
def create_run(body: RunRequest, request: Request) -> RunInfo:
    service = _service(request)
    problem = None
    if body.mode == "real":
        if not re.fullmatch(r"[\w.-]+", body.config):
            raise HTTPException(422, "invalid config name")
        path = service.settings.configs_dir / f"{body.config}.yaml"
        if not path.is_file():
            raise HTTPException(422, f"config '{body.config}' not found in configs/")
        try:
            problem = load_problem(path)
        except ValidationError as exc:
            raise HTTPException(422, str(exc)) from exc
    return service.start(body.mode, problem)


@router.get("/runs")
def list_runs(request: Request, limit: int = Query(50, ge=1, le=200)) -> list[RunInfo]:
    return _service(request).list_runs(limit)


@router.get("/runs/{run_id}")
def get_run(run_id: str, request: Request) -> RunInfo:
    return _known_run(request, run_id)


@router.get("/runs/{run_id}/events")
def get_events(run_id: str, request: Request) -> list[ExecutionEvent]:
    events = _service(request).events(run_id)  # ids that are not real run ids are "not found" in the store
    if events is None:
        raise HTTPException(404, f"run '{run_id}' not found")
    return events


@router.get("/runs/{run_id}/stream")
async def stream_events(
    run_id: str, request: Request, last_event_id: int = Header(0, alias="Last-Event-ID")
) -> StreamingResponse:
    _known_run(request, run_id)
    service = _service(request)
    if service.in_memory(run_id):
        body = event_stream(service.bus, run_id, last_event_id)
    else:  # persisted by an earlier process: replay from disk, then close
        events = service.events(run_id)
        if events is None:
            raise HTTPException(404, f"run '{run_id}' not found")
        body = replay_stream(events, last_event_id)
    return StreamingResponse(
        body,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/runs/{run_id}/artifacts/{name}")
def get_artifact(run_id: str, name: str, request: Request) -> Response:
    """Raw content of one artifact belonging to that run. `name` is only ever used as a dict-key lookup into
    `info.artifacts` (never joined raw onto a path) — that dict is server-written, so this cannot escape the
    run directory."""
    info = _known_run(request, run_id)
    if name not in info.artifacts:
        raise HTTPException(404, f"artifact '{name}' not found for run '{run_id}'")
    settings = _service(request).settings
    path = settings.workspace_dir / run_id / info.artifacts[name]
    if not path.is_file():
        raise HTTPException(404, f"artifact '{name}' not found for run '{run_id}'")
    content_type = _CONTENT_TYPES.get(path.suffix.lower(), "text/plain")
    return Response(content=path.read_bytes(), media_type=content_type)


@router.get("/runs/{run_id}/dataset-preview")
def get_dataset_preview(run_id: str, request: Request, limit: int = Query(15, ge=1, le=50)) -> dict:
    """Bounded sample of the run's dataset, resolved only from that run's own `problem.yaml` artifact — never
    from client input. `available=false` (never a 500) when there is no dataset to preview."""
    info = _known_run(request, run_id)
    settings = _service(request).settings
    unavailable = {"available": False, "columns": [], "rows": [], "truncated": False}
    problem_artifact = info.artifacts.get("problem.yaml")
    if problem_artifact is None:
        return unavailable
    problem_path = settings.workspace_dir / run_id / problem_artifact
    if not problem_path.is_file():
        return unavailable
    try:
        problem = load_problem(problem_path)
        df = load_dataset(problem.resolved_dataset(settings.root))
    except Exception:
        return unavailable
    head = df.head(limit)
    return {
        "available": True,
        "columns": list(head.columns),
        "rows": _scrub(head.to_dict(orient="records")),
        "truncated": len(df) > limit,
    }
