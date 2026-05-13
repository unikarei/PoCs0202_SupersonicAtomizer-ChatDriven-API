"""Project workspace allocation and listing service."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
from urllib.parse import urlparse

from supersonic_atomizer_optbyapi.config import DEFAULT_WORKSPACE_ROOT
from supersonic_atomizer_optbyapi.models import ProjectRecord

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class ProjectExistsError(FileExistsError):
    """Raised when a project already exists."""


class InvalidProjectNameError(ValueError):
    """Raised when the project name is not safe as a directory name."""


class ProjectNotFoundError(FileNotFoundError):
    """Raised when a project does not exist."""


class WorkspaceService:
    """Manage project directories under the configured workspace root."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_root = Path(workspace_root) if workspace_root is not None else DEFAULT_WORKSPACE_ROOT

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def _validate_project_name(self, project_name: str) -> str:
        normalized = project_name.strip()
        if not normalized or not _NAME_RE.fullmatch(normalized):
            raise InvalidProjectNameError(
                "Project name must contain only ASCII letters, digits, '.', '_' or '-'."
            )
        return normalized

    def _project_dir(self, project_id: str) -> Path:
        return self._workspace_root / project_id

    def _normalize_solver_base_url(self, solver_base_url: str | None) -> str | None:
        if solver_base_url is None:
            return None
        normalized = solver_base_url.strip()
        if not normalized:
            return None
        if "://" not in normalized:
            normalized = f"http://{normalized}"
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("solver_base_url must be an absolute http(s) URL.")
        return normalized.rstrip("/") + "/"

    def create_project(self, project_name: str, solver_base_url: str | None = None) -> ProjectRecord:
        project_id = self._validate_project_name(project_name)
        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise ProjectExistsError(f"Project {project_id!r} already exists.")

        project_dir.mkdir(parents=True, exist_ok=False)
        (project_dir / "cases").mkdir()
        (project_dir / "reports").mkdir()

        record = ProjectRecord(
            project_id=project_id,
            project_name=project_name.strip(),
            workspace_path=str(project_dir),
            solver_base_url=self._normalize_solver_base_url(solver_base_url),
            created_at=datetime.now(timezone.utc),
        )
        (project_dir / "project.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def get_project(self, project_id: str) -> ProjectRecord:
        project_dir = self.require_project_dir(project_id)
        project_file = project_dir / "project.json"
        if not project_file.exists():
            raise ProjectNotFoundError(f"Project {project_id!r} was not found.")
        return ProjectRecord.model_validate(json.loads(project_file.read_text(encoding="utf-8")))

    def update_solver_base_url(self, project_id: str, solver_base_url: str | None) -> ProjectRecord:
        record = self.get_project(project_id)
        updated = record.model_copy(update={"solver_base_url": self._normalize_solver_base_url(solver_base_url)})
        project_file = self._project_dir(project_id) / "project.json"
        project_file.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
        return updated

    def list_projects(self) -> list[ProjectRecord]:
        if not self._workspace_root.exists():
            return []

        records: list[ProjectRecord] = []
        for project_dir in sorted(path for path in self._workspace_root.iterdir() if path.is_dir()):
            project_file = project_dir / "project.json"
            if not project_file.exists():
                continue
            payload = json.loads(project_file.read_text(encoding="utf-8"))
            records.append(ProjectRecord.model_validate(payload))
        return records

    def require_project_dir(self, project_id: str) -> Path:
        project_dir = self._project_dir(project_id)
        if not project_dir.exists() or not project_dir.is_dir():
            raise ProjectNotFoundError(f"Project {project_id!r} was not found.")
        return project_dir
