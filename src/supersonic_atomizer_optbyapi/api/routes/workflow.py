"""Workflow routes for project explorer, chat plans, runs, and reports."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request, status

from supersonic_atomizer_optbyapi.models import (
    ApprovePlanResponse,
    CaseRecord,
    CreatePlanRequest,
    ExecuteRunRequest,
    ProjectTreeNode,
    ProjectTreeResponse,
    ReportListResponse,
    RunRecord,
)
from supersonic_atomizer_optbyapi.services.case_service import CaseNotFoundError, CaseService
from supersonic_atomizer_optbyapi.services.workflow_service import PlanApprovalError, PlanNotFoundError, WorkflowService
from supersonic_atomizer_optbyapi.services.workspace_service import ProjectNotFoundError, WorkspaceService

router = APIRouter()


def _workspace_service(request: Request) -> WorkspaceService:
    return WorkspaceService(workspace_root=request.app.state.workspace_root)


def _case_service(request: Request) -> CaseService:
    return CaseService(workspace_root=request.app.state.workspace_root)


def _workflow_service(request: Request) -> WorkflowService:
    return WorkflowService(workspace_root=request.app.state.workspace_root)


@router.get("/tree", response_model=ProjectTreeResponse)
def get_project_tree(request: Request) -> ProjectTreeResponse:
    workspace = _workspace_service(request)
    case_service = _case_service(request)
    nodes: list[ProjectTreeNode] = []
    for project in workspace.list_projects():
        nodes.append(ProjectTreeNode(project=project, cases=case_service.list_cases(project.project_id)))
    return ProjectTreeResponse(projects=nodes)


@router.get("/{project_id}/cases/{case_id}", response_model=CaseRecord)
def get_case(project_id: str, case_id: str, request: Request) -> CaseRecord:
    try:
        return _case_service(request).get_case(project_id, case_id)
    except (ProjectNotFoundError, CaseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{project_id}/cases/{case_id}/chat/plans", response_model=ApprovePlanResponse, status_code=status.HTTP_201_CREATED)
def create_plan(project_id: str, case_id: str, request_body: CreatePlanRequest, request: Request) -> ApprovePlanResponse:
    try:
        plan = _workflow_service(request).create_plan(
            project_id,
            case_id,
            request_body.instruction,
            request_body.parameter_axes,
            request_body.postprocess_policy,
            request_body.parameter_axes_hint,
            request_body.postprocess_additional,
            request_body.thread_id,
        )
    except (ProjectNotFoundError, CaseNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApprovePlanResponse(plan=plan)


@router.post("/{project_id}/cases/{case_id}/chat/plans/{plan_id}/approve", response_model=ApprovePlanResponse)
def approve_plan(project_id: str, case_id: str, plan_id: str, request: Request) -> ApprovePlanResponse:
    try:
        plan = _workflow_service(request).approve_plan(project_id, case_id, plan_id)
    except (ProjectNotFoundError, CaseNotFoundError, PlanNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ApprovePlanResponse(plan=plan)


@router.post("/{project_id}/cases/{case_id}/runs", response_model=RunRecord, status_code=status.HTTP_202_ACCEPTED)
def execute_run(project_id: str, case_id: str, request_body: ExecuteRunRequest, request: Request) -> RunRecord:
    try:
        return _workflow_service(request).execute_plan(project_id, case_id, request_body.plan_id)
    except (ProjectNotFoundError, CaseNotFoundError, PlanNotFoundError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PlanApprovalError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/{project_id}/cases/{case_id}/runs/{run_id}", response_model=RunRecord)
def get_run(project_id: str, case_id: str, run_id: str, request: Request) -> RunRecord:
    try:
        return _workflow_service(request).get_run(project_id, case_id, run_id)
    except (ProjectNotFoundError, CaseNotFoundError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{project_id}/cases/{case_id}/runs/{run_id}/plot-series")
def get_run_plot_series(project_id: str, case_id: str, run_id: str, request: Request) -> dict:
    try:
        return _workflow_service(request).load_run_plot_series(project_id, case_id, run_id)
    except (ProjectNotFoundError, CaseNotFoundError, FileNotFoundError) as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{project_id}/reports", response_model=ReportListResponse)
def list_reports(
    project_id: str,
    request: Request,
    case_id: str | None = Query(default=None),
    plan_id: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    sort_order: str = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> ReportListResponse:
    try:
        reports, total_count = _workflow_service(request).list_reports(
            project_id,
            case_id=case_id,
            plan_id=plan_id,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size,
        )
    except ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return ReportListResponse(project_id=project_id, reports=reports, total_count=total_count, page=page, page_size=page_size)
