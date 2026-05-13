"""Project API routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, status

from supersonic_atomizer_optbyapi.models import CreateProjectRequest, ProjectListResponse, ProjectRecord, UpdateProjectSolverRequest
from supersonic_atomizer_optbyapi.services.workspace_service import InvalidProjectNameError, ProjectExistsError, WorkspaceService

router = APIRouter()


def _workspace_service(request: Request) -> WorkspaceService:
    return WorkspaceService(workspace_root=request.app.state.workspace_root)


@router.get("/", response_model=ProjectListResponse)
def list_projects(request: Request) -> ProjectListResponse:
    return ProjectListResponse(projects=_workspace_service(request).list_projects())


@router.post("/", response_model=ProjectRecord, status_code=status.HTTP_201_CREATED)
def create_project(request_body: CreateProjectRequest, request: Request) -> ProjectRecord:
    try:
        return _workspace_service(request).create_project(request_body.project_name, request_body.solver_base_url)
    except InvalidProjectNameError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ProjectExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.put("/{project_id}/solver-endpoint", response_model=ProjectRecord)
def update_solver_endpoint(project_id: str, request_body: UpdateProjectSolverRequest, request: Request) -> ProjectRecord:
    try:
        return _workspace_service(request).update_solver_base_url(project_id, request_body.solver_base_url)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
