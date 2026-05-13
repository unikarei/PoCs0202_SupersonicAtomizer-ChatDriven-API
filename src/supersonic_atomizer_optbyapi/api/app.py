"""FastAPI application factory for the OptByAPI PoC."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from supersonic_atomizer_optbyapi.api.routes.cases import router as cases_router
from supersonic_atomizer_optbyapi.api.routes.projects import router as projects_router
from supersonic_atomizer_optbyapi.api.routes.ui import router as ui_router
from supersonic_atomizer_optbyapi.api.routes.workflow import router as workflow_router


def create_app(workspace_root: Path | None = None) -> FastAPI:
    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    app = FastAPI(
        title="Supersonic Atomizer OptByAPI",
        version="0.1.0",
        description="Phase 1 project workspace and case import API",
    )
    app.state.workspace_root = workspace_root
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.include_router(ui_router)
    app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
    app.include_router(cases_router, prefix="/api/projects", tags=["cases"])
    app.include_router(workflow_router, prefix="/api/projects", tags=["workflow"])
    return app


app = create_app()
