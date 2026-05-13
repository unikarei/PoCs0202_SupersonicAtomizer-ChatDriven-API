"""Case import and listing service for Phase 1."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re

import yaml

from supersonic_atomizer_optbyapi.models import CaseRecord, CaseSummary
from supersonic_atomizer_optbyapi.services.workspace_service import ProjectNotFoundError, WorkspaceService

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")


class InvalidCaseNameError(ValueError):
    """Raised when the case name is invalid."""


class CaseExistsError(FileExistsError):
    """Raised when the case already exists."""


class CaseImportError(ValueError):
    """Raised when the YAML cannot be interpreted as a Phase 1 case."""


class CaseNotFoundError(FileNotFoundError):
    """Raised when a case does not exist."""


class CaseApprovalRequiredError(PermissionError):
    """Raised when a mutating operation requires explicit approval."""


class CaseService:
    """Import YAML-backed cases into a managed project workspace."""

    def __init__(
        self,
        workspace_service: WorkspaceService | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self._workspace_service = workspace_service or WorkspaceService(workspace_root=workspace_root)

    def _validate_case_name(self, case_name: str) -> str:
        normalized = case_name.strip()
        if not normalized or not _NAME_RE.fullmatch(normalized):
            raise InvalidCaseNameError(
                "Case name must contain only ASCII letters, digits, '.', '_' or '-'."
            )
        return normalized

    def _case_dir(self, project_id: str, case_id: str) -> Path:
        project_dir = self._workspace_service.require_project_dir(project_id)
        return project_dir / "cases" / case_id

    def _case_file(self, project_id: str, case_id: str) -> Path:
        return self._case_dir(project_id, case_id) / "case.json"

    def get_case(self, project_id: str, case_id: str) -> CaseRecord:
        case_dir = self._case_dir(project_id, case_id)
        case_file = case_dir / "case.json"
        if not case_file.exists():
            raise CaseNotFoundError(f"Case {case_id!r} was not found in project {project_id!r}.")
        payload = json.loads(case_file.read_text(encoding="utf-8"))
        return CaseRecord.model_validate(payload)

    def import_case(self, project_id: str, source_yaml_path: str, case_name: str, *, overwrite: bool = False) -> CaseRecord:
        case_id = self._validate_case_name(case_name)
        source_path = Path(source_yaml_path)
        if not source_path.exists() or not source_path.is_file():
            raise FileNotFoundError(f"Source YAML {source_yaml_path!r} was not found.")
        raw_bytes = source_path.read_bytes()
        return self._import_case_bytes(
            project_id=project_id,
            case_id=case_id,
            source_yaml_path=str(source_path),
            source_bytes=raw_bytes,
            overwrite=overwrite,
        )

    def import_case_upload(
        self,
        project_id: str,
        case_name: str,
        source_name: str,
        source_bytes: bytes,
        *,
        overwrite: bool = False,
    ) -> CaseRecord:
        case_id = self._validate_case_name(case_name)
        return self._import_case_bytes(
            project_id=project_id,
            case_id=case_id,
            source_yaml_path=f"upload://{source_name}",
            source_bytes=source_bytes,
            overwrite=overwrite,
        )

    def _import_case_bytes(
        self,
        *,
        project_id: str,
        case_id: str,
        source_yaml_path: str,
        source_bytes: bytes,
        overwrite: bool,
    ) -> CaseRecord:
        project_dir = self._workspace_service.require_project_dir(project_id)
        case_dir = project_dir / "cases" / case_id
        case_exists = case_dir.exists()
        if case_exists and not overwrite:
            raise CaseExistsError(f"Case {case_id!r} already exists in project {project_id!r}.")

        payload = self._load_yaml_payload(source_bytes)
        conditions, grid = self._extract_conditions_grid(payload)

        now = datetime.now(timezone.utc)
        if case_exists:
            previous = self.get_case(project_id, case_id)
            next_revision = previous.revision + 1
            created_at = previous.created_at
        else:
            case_dir.mkdir(parents=True, exist_ok=False)
            (case_dir / "revisions").mkdir()
            next_revision = 1
            created_at = now

        record = CaseRecord(
            case_id=case_id,
            project_id=project_id,
            source_yaml_path=source_yaml_path,
            revision=next_revision,
            conditions=conditions,
            grid=grid,
            created_at=created_at,
            updated_at=now,
        )
        self._write_case_record(case_dir, record)
        (case_dir / "imported_source.yaml").write_bytes(source_bytes)
        (case_dir / "revisions").mkdir(exist_ok=True)
        (case_dir / "revisions" / f"{record.revision:04d}.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return record

    def list_cases(self, project_id: str) -> list[CaseSummary]:
        project_dir = self._workspace_service.require_project_dir(project_id)
        cases_dir = project_dir / "cases"
        if not cases_dir.exists():
            return []

        summaries: list[CaseSummary] = []
        for case_dir in sorted(path for path in cases_dir.iterdir() if path.is_dir()):
            case_file = case_dir / "case.json"
            if not case_file.exists():
                continue
            payload = json.loads(case_file.read_text(encoding="utf-8"))
            record = CaseRecord.model_validate(payload)
            summaries.append(
                CaseSummary(
                    case_id=record.case_id,
                    project_id=record.project_id,
                    source_yaml_path=record.source_yaml_path,
                    revision=record.revision,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                )
            )
        return summaries

    def update_case(
        self,
        project_id: str,
        case_id: str,
        conditions: dict,
        grid: dict,
        *,
        approved: bool,
    ) -> CaseRecord:
        if not approved:
            raise CaseApprovalRequiredError("Case update requires explicit approval.")
        if not isinstance(conditions, dict) or not isinstance(grid, dict):
            raise CaseImportError("'conditions' and 'grid' must be mappings.")

        case_dir = self._case_dir(project_id, case_id)
        record = self.get_case(project_id, case_id)
        now = datetime.now(timezone.utc)
        updated = CaseRecord(
            case_id=record.case_id,
            project_id=record.project_id,
            source_yaml_path=record.source_yaml_path,
            revision=record.revision + 1,
            conditions=conditions,
            grid=grid,
            created_at=record.created_at,
            updated_at=now,
        )
        self._write_case_record(case_dir, updated)
        self._write_imported_source(case_dir, updated)
        revision_name = f"{updated.revision:04d}.json"
        (case_dir / "revisions" / revision_name).write_text(
            updated.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return updated

    def _write_imported_source(self, case_dir: Path, record: CaseRecord) -> None:
        payload = {
            "conditions": record.conditions,
            "grid": record.grid,
        }
        (case_dir / "imported_source.yaml").write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )

    def _write_case_record(self, case_dir: Path, record: CaseRecord) -> None:
        (case_dir / "case.json").write_text(record.model_dump_json(indent=2), encoding="utf-8")

    def _load_yaml_payload(self, raw_bytes: bytes) -> dict:
        text = None
        for enc in ("utf-8-sig", "utf-8", "cp932"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            raise CaseImportError("Unable to decode YAML file content.")
        try:
            payload = yaml.safe_load(text)
        except yaml.YAMLError as exc:
            raise CaseImportError(f"Invalid YAML: {exc}") from exc
        if not isinstance(payload, dict):
            raise CaseImportError("Case YAML must contain a top-level mapping.")
        return payload

    def _extract_conditions_grid(self, payload: dict) -> tuple[dict, dict]:
        # Native OptByAPI shape
        if "conditions" in payload and "grid" in payload:
            if not isinstance(payload["conditions"], dict) or not isinstance(payload["grid"], dict):
                raise CaseImportError("'conditions' and 'grid' must be mappings.")
            return payload["conditions"], payload["grid"]

        # Legacy 0201 shape compatibility
        if "boundary_conditions" in payload and "geometry" in payload:
            conditions: dict = {}
            for key in (
                "fluid",
                "boundary_conditions",
                "droplet_injection",
                "model_selection",
                "models",
                "outputs",
            ):
                value = payload.get(key)
                if isinstance(value, dict):
                    conditions[key] = value
            geometry = payload.get("geometry")
            if not isinstance(geometry, dict):
                raise CaseImportError("Legacy YAML 'geometry' must be a mapping.")
            grid = geometry
            return conditions, grid

        raise CaseImportError(
            "Case YAML must include either ('conditions' and 'grid') or legacy ('boundary_conditions' and 'geometry') sections."
        )
