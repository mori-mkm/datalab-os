"""FastAPI app. Run with: uvicorn datalab.api.app:app --reload"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from datalab.api import graph, runs
from datalab.config import Settings, load_settings
from datalab.llm import OllamaClient
from datalab.services.run_service import RunService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="DataLab OS", version="0.1.0")
    app.state.runs = RunService(settings)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])
    app.include_router(graph.router)
    app.include_router(runs.router)

    @app.get("/health")
    def health() -> dict:
        client = OllamaClient(settings.ollama_url, settings.ollama_model)
        return {
            "status": "ok",
            "llm": {
                "mode": settings.llm_mode,
                "model": settings.ollama_model,
                "available": settings.llm_mode != "off" and client.available(),
            },
        }

    return app


app = create_app()
