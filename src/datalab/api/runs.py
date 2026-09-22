from __future__ import annotations

import re

from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ValidationError

from datalab.api.events import event_stream, replay_stream
from datalab.schemas.event import ExecutionEvent
from datalab.schemas.problem import load_problem
from datalab.schemas.run import RunInfo, RunMode
from datalab.services.run_service import RunService

router = APIRouter(prefix="/api")


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
