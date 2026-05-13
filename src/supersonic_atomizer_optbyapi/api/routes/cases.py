"""Case API routes."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile, status

from supersonic_atomizer_optbyapi.models import CaseListResponse, CaseRecord, ImportCaseRequest, UpdateCaseRequest
from supersonic_atomizer_optbyapi.services.case_service import (
    CaseApprovalRequiredError,
    CaseExistsError,
    CaseImportError,
    CaseNotFoundError,
    CaseService,
    InvalidCaseNameError,
)
from supersonic_atomizer_optbyapi.services.workspace_service import ProjectNotFoundError

router = APIRouter()


def _case_service(request: Request) -> CaseService:
    return CaseService(workspace_root=request.app.state.workspace_root)


@router.get("/{project_id}/cases/", response_model=CaseListResponse)
def list_cases(project_id: str, request: Request) -> CaseListResponse:
    try:
        cases = _case_service(request).list_cases(project_id)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return CaseListResponse(project_id=project_id, cases=cases)


@router.post("/{project_id}/cases/import", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
def import_case(project_id: str, request_body: ImportCaseRequest, request: Request) -> CaseRecord:
    try:
        service = _case_service(request)
        return service.import_case(
            project_id,
            request_body.source_yaml_path,
            request_body.case_name,
            overwrite=request_body.overwrite,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidCaseNameError, CaseImportError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CaseExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{project_id}/cases/import-upload", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
async def import_case_upload(
    project_id: str,
    request: Request,
    case_name: str = Form(...),
    source_yaml: UploadFile = File(...),
    overwrite: bool = Form(False),
) -> CaseRecord:
    try:
        service = _case_service(request)
        source_bytes = await source_yaml.read()
        source_name = source_yaml.filename or "uploaded.yaml"
        return service.import_case_upload(project_id, case_name, source_name, source_bytes, overwrite=overwrite)
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (InvalidCaseNameError, CaseImportError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CaseExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{project_id}/cases/{case_id}", response_model=CaseRecord)
def update_case(project_id: str, case_id: str, request_body: UpdateCaseRequest, request: Request) -> CaseRecord:
    try:
        return _case_service(request).update_case(
            project_id,
            case_id,
            request_body.conditions,
            request_body.grid,
            approved=request_body.approved,
        )
    except (ProjectNotFoundError, CaseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (CaseApprovalRequiredError, CaseImportError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
