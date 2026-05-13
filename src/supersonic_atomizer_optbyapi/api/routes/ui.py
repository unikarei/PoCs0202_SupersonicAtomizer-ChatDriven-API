"""UI route serving the 3-pane GUI shell."""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import FileResponse
from pathlib import Path

router = APIRouter()
_STATIC_DIR = Path(__file__).resolve().parents[1] / "static"


@router.get("/")
def index() -> FileResponse:
    return FileResponse(_STATIC_DIR / "index.html")