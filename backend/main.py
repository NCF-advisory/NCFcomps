"""Application FastAPI — expose le moteur `comparables/` en API REST interne (lot 1).

Lancement dev :
    uvicorn backend.main:app --reload --port 8000
Docs interactives : http://localhost:8000/api/docs

NB : la file de tâches (backend/jobs.py) est en mémoire -> 1 seul worker uvicorn.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.routers import auth, cessions, comparables, runs
from comparables.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title="NCF Comparables API", version="0.1.0",
                  docs_url="/api/docs", openapi_url="/api/openapi.json")

    origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True,
                           allow_methods=["*"], allow_headers=["*"])

    for r in (auth.router, comparables.router, cessions.router, runs.router):
        app.include_router(r, prefix="/api")

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()
