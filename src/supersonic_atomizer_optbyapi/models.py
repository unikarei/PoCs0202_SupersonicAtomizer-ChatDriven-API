"""Pydantic models for project, case, chat plan, run, and report APIs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectRecord(BaseModel):
    project_id: str
    project_name: str
    workspace_path: str
    solver_base_url: str | None = None
    created_at: datetime


class ProjectListResponse(BaseModel):
    projects: list[ProjectRecord]


class CreateProjectRequest(BaseModel):
    project_name: str = Field(min_length=1)
    solver_base_url: str | None = None


class UpdateProjectSolverRequest(BaseModel):
    solver_base_url: str | None = None


class CaseRecord(BaseModel):
    case_id: str
    project_id: str
    source_yaml_path: str
    revision: int
    conditions: dict
    grid: dict
    created_at: datetime
    updated_at: datetime


class CaseSummary(BaseModel):
    case_id: str
    project_id: str
    source_yaml_path: str
    revision: int
    created_at: datetime
    updated_at: datetime


class CaseListResponse(BaseModel):
    project_id: str
    cases: list[CaseSummary]


class ImportCaseRequest(BaseModel):
    source_yaml_path: str = Field(min_length=1)
    case_name: str = Field(min_length=1)
    overwrite: bool = False


class UpdateCaseRequest(BaseModel):
    conditions: dict
    grid: dict
    approval_comment: str | None = None
    approved: bool = False


class ProjectTreeNode(BaseModel):
    project: ProjectRecord
    cases: list[CaseSummary]


class ProjectTreeResponse(BaseModel):
    projects: list[ProjectTreeNode]


class CreatePlanRequest(BaseModel):
    instruction: str = Field(min_length=1)
    parameter_axes: dict[str, list[str | int | float]] | None = None
    parameter_axes_hint: str | None = None
    postprocess_policy: dict | None = None
    postprocess_additional: str | None = None
    thread_id: str | None = None


class ChatMessageRecord(BaseModel):
    role: str
    content: str
    created_at: datetime


class ChatThreadRecord(BaseModel):
    thread_id: str
    project_id: str
    case_id: str
    messages: list[ChatMessageRecord]
    created_at: datetime
    updated_at: datetime


class ChatPlanRecord(BaseModel):
    plan_id: str
    thread_id: str
    project_id: str
    case_id: str
    instruction: str
    parameter_axes: dict[str, list[str | int | float]]
    postprocess_policy: dict
    assumptions: list[str]
    approval_state: str
    created_at: datetime
    approved_at: datetime | None = None


class ApprovePlanResponse(BaseModel):
    plan: ChatPlanRecord


class ExecuteRunRequest(BaseModel):
    plan_id: str = Field(min_length=1)


class RunRecord(BaseModel):
    run_id: str
    project_id: str
    case_id: str
    plan_id: str
    status: str
    diagnostics: dict
    created_at: datetime
    completed_at: datetime | None = None


class ReportBundleRecord(BaseModel):
    report_bundle_id: str
    project_id: str
    case_id: str
    plan_id: str
    run_id: str
    summary: str
    metrics: dict
    created_at: datetime


class ReportListResponse(BaseModel):
    project_id: str
    reports: list[ReportBundleRecord]
    total_count: int
    page: int
    page_size: int
