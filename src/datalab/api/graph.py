from __future__ import annotations

from fastapi import APIRouter

from datalab.graphs.organization import graph_metadata

router = APIRouter(prefix="/api")


@router.get("/graph")
def get_graph_metadata() -> dict:
    return graph_metadata()
