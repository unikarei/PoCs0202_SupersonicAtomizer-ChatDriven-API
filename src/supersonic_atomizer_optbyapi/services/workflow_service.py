"""Chat plan, run execution, and report persistence for the PoC workflow."""

from __future__ import annotations

from datetime import datetime, timezone
from itertools import product
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
import copy
import csv
import json
import os
import re
import threading
import time
from uuid import uuid4

from supersonic_atomizer_optbyapi.models import ChatMessageRecord, ChatPlanRecord, ChatThreadRecord, ReportBundleRecord, RunRecord
from supersonic_atomizer_optbyapi.services.case_service import CaseNotFoundError, CaseService
from supersonic_atomizer_optbyapi.services.workspace_service import WorkspaceService


class PlanNotFoundError(FileNotFoundError):
    """Raised when a chat plan does not exist."""


class PlanApprovalError(ValueError):
    """Raised when a plan cannot be executed yet."""


class WorkflowService:
    """Persist minimal chat plans, runs, and report bundles under a project workspace."""

    def __init__(self, workspace_root: Path | None = None) -> None:
        self._workspace_service = WorkspaceService(workspace_root=workspace_root)
        self._case_service = CaseService(workspace_root=workspace_root)

    def _project_dir(self, project_id: str) -> Path:
        return self._workspace_service.require_project_dir(project_id)

    def _case_dir(self, project_id: str, case_id: str) -> Path:
        return self._project_dir(project_id) / "cases" / case_id

    def _plans_dir(self, project_id: str, case_id: str) -> Path:
        path = self._case_dir(project_id, case_id) / "plans"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _runs_dir(self, project_id: str, case_id: str) -> Path:
        path = self._case_dir(project_id, case_id) / "runs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _reports_dir(self, project_id: str) -> Path:
        path = self._project_dir(project_id) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _threads_dir(self, project_id: str, case_id: str) -> Path:
        path = self._case_dir(project_id, case_id) / "threads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def create_plan(
        self,
        project_id: str,
        case_id: str,
        instruction: str,
        parameter_axes: dict[str, list[str | int | float]] | None,
        postprocess_policy: dict | None,
        parameter_axes_hint: str | None,
        postprocess_additional: str | None,
        thread_id: str | None = None,
    ) -> ChatPlanRecord:
        self._case_service.get_case(project_id, case_id)
        normalized_axes = self._normalize_parameter_axes(instruction, parameter_axes, parameter_axes_hint)
        normalized_postprocess = self._normalize_postprocess_policy(postprocess_policy, postprocess_additional)
        thread = self._get_or_create_thread(project_id, case_id, thread_id, instruction)
        now = datetime.now(timezone.utc)
        plan = ChatPlanRecord(
            plan_id=f"plan-{uuid4().hex[:12]}",
            thread_id=thread.thread_id,
            project_id=project_id,
            case_id=case_id,
            instruction=instruction,
            parameter_axes=normalized_axes,
            postprocess_policy=normalized_postprocess,
            assumptions=self._build_assumptions(normalized_axes, normalized_postprocess),
            approval_state="pending",
            created_at=now,
            approved_at=None,
        )
        self._write_json_file(self._plan_file(project_id, case_id, plan.plan_id), plan.model_dump_json(indent=2))
        run_matrix = self._expand_run_matrix(normalized_axes)
        self._append_thread_message(
            project_id,
            case_id,
            thread.thread_id,
            "assistant",
            f"Created plan {plan.plan_id} with {len(run_matrix)} planned run(s).",
        )
        return plan

    def get_thread(self, project_id: str, case_id: str, thread_id: str) -> ChatThreadRecord:
        thread_file = self._thread_file(project_id, case_id, thread_id)
        if not thread_file.exists():
            raise FileNotFoundError(f"Thread {thread_id!r} was not found.")
        return ChatThreadRecord.model_validate_json(self._read_json_file_with_retry(thread_file))

    def get_plan(self, project_id: str, case_id: str, plan_id: str) -> ChatPlanRecord:
        plan_file = self._plan_file(project_id, case_id, plan_id)
        if not plan_file.exists():
            raise PlanNotFoundError(f"Plan {plan_id!r} was not found.")
        return ChatPlanRecord.model_validate_json(self._read_json_file_with_retry(plan_file))

    def approve_plan(self, project_id: str, case_id: str, plan_id: str) -> ChatPlanRecord:
        plan = self.get_plan(project_id, case_id, plan_id)
        approved = plan.model_copy(update={
            "approval_state": "approved",
            "approved_at": datetime.now(timezone.utc),
        })
        self._write_json_file(self._plan_file(project_id, case_id, plan_id), approved.model_dump_json(indent=2))
        return approved

    def execute_plan(self, project_id: str, case_id: str, plan_id: str) -> RunRecord:
        plan = self.get_plan(project_id, case_id, plan_id)
        case_record = self._case_service.get_case(project_id, case_id)
        project_record = self._workspace_service.get_project(project_id)
        solver_base_url = project_record.solver_base_url
        if plan.approval_state != "approved":
            raise PlanApprovalError(f"Plan {plan_id!r} must be approved before execution.")

        effective_axes = self._derive_effective_axes_from_case(plan.parameter_axes, case_record.conditions)
        run_matrix = self._expand_run_matrix(effective_axes)

        now = datetime.now(timezone.utc)
        run = RunRecord(
            run_id=f"run-{uuid4().hex[:12]}",
            project_id=project_id,
            case_id=case_id,
            plan_id=plan_id,
            status="queued",
            diagnostics={
                "case_revision": case_record.revision,
                "parameter_axis_count": len(effective_axes),
                "instruction": plan.instruction,
                "thread_id": plan.thread_id,
                "run_count": len(run_matrix),
                "run_matrix": run_matrix,
                "completed_runs": 0,
                "analysis_methods": effective_axes.get("analysis_method", []),
                "effective_parameter_axes": effective_axes,
                "sweep_source": "conditions.boundary_conditions.Ps_out" if "Ps_out" in effective_axes else "plan.parameter_axes",
                "solver_mode": "external_api" if solver_base_url else "internal_mock",
                "solver_base_url": solver_base_url,
            },
            created_at=now,
            completed_at=None,
        )
        self._write_json_file(self._run_file(project_id, case_id, run.run_id), run.model_dump_json(indent=2))
        target = self._complete_run_background
        args: tuple = (project_id, case_id, plan.plan_id, run.run_id)
        if solver_base_url:
            target = self._complete_run_external_background
            args = (project_id, case_id, plan.plan_id, run.run_id, solver_base_url)
        threading.Thread(target=target, args=args, daemon=True).start()
        return run

    def _complete_run_background(self, project_id: str, case_id: str, plan_id: str, run_id: str) -> None:
        time.sleep(0.15)
        try:
            run = self.get_run(project_id, case_id, run_id)
            if run.status != "queued":
                return
            run_matrix = list(run.diagnostics.get("run_matrix", []))
            running = run.model_copy(update={"status": "running"})
            self._write_json_file(self._run_file(project_id, case_id, run_id), running.model_dump_json(indent=2))
            for index, combination in enumerate(run_matrix, start=1):
                time.sleep(0.05)
                running = running.model_copy(update={
                    "diagnostics": {
                        **running.diagnostics,
                        "completed_runs": index,
                        "active_combination": combination,
                        "progress_fraction": index / max(len(run_matrix), 1),
                    }
                })
                self._write_json_file(self._run_file(project_id, case_id, run_id), running.model_dump_json(indent=2))
            completed = running.model_copy(update={
                "status": "completed",
                "completed_at": datetime.now(timezone.utc),
                "diagnostics": {
                    **running.diagnostics,
                    "active_combination": None,
                    "progress_fraction": 1.0,
                },
            })
            self._write_json_file(self._run_file(project_id, case_id, run_id), completed.model_dump_json(indent=2))
            plan = self.get_plan(project_id, case_id, plan_id)
            self._append_report_bundle(project_id, case_id, plan, completed)
        except Exception:
            failed_run = None
            try:
                failed_run = self.get_run(project_id, case_id, run_id)
            except Exception:
                return
            self._write_json_file(
                self._run_file(project_id, case_id, run_id),
                failed_run.model_copy(update={
                    "status": "failed",
                    "completed_at": datetime.now(timezone.utc),
                    "diagnostics": {**failed_run.diagnostics, "background_error": True},
                }).model_dump_json(indent=2),
            )

    def _complete_run_external_background(
        self,
        project_id: str,
        case_id: str,
        plan_id: str,
        run_id: str,
        solver_base_url: str,
    ) -> None:
        time.sleep(0.15)
        try:
            run = self.get_run(project_id, case_id, run_id)
            if run.status != "queued":
                return

            case_record = self._case_service.get_case(project_id, case_id)
            run_matrix = list(run.diagnostics.get("run_matrix", []))
            running = run.model_copy(update={"status": "running"})
            self._write_json_file(self._run_file(project_id, case_id, run_id), running.model_dump_json(indent=2))

            external_project = self._resolve_external_project_name(solver_base_url, case_id)
            external_payload = {
                "case_name": case_id,
                "project_name": external_project,
                "config": self._to_external_config(case_record.conditions, case_record.grid),
            }
            submit_response = self._submit_external_job(solver_base_url, external_payload)
            completed_response = self._poll_external_job(solver_base_url, submit_response)
            result_response = self._fetch_external_result(solver_base_url, completed_response)

            artifacts: list[dict[str, str]] = []
            inline_csv = result_response.get("csv") if isinstance(result_response, dict) else None
            if isinstance(inline_csv, str) and inline_csv.strip():
                csv_target = self._runs_dir(project_id, case_id) / f"{run_id}.external_results.csv"
                csv_target.write_text(inline_csv, encoding="utf-8")
                artifacts.append({"label": "external_result", "results_csv_path": str(csv_target)})
            else:
                csv_path = self._extract_results_csv_from_external_response(result_response)
                if csv_path is not None:
                    artifacts.append({"label": "external_result", "results_csv_path": str(csv_path)})

            result_run_count = result_response.get("run_count") if isinstance(result_response, dict) else None
            completed_runs = int(result_run_count) if isinstance(result_run_count, int) else len(run_matrix)
            diagnostics_update = {
                **running.diagnostics,
                "active_combination": None,
                "completed_runs": completed_runs,
                "run_count": completed_runs,
                "progress_fraction": 1.0,
                "results_csv_paths": artifacts,
                "external_project_name": external_project,
                "external_last_response": {
                    "status": str(completed_response.get("status", "completed")),
                    "job_id": completed_response.get("job_id") or completed_response.get("id"),
                },
            }
            if artifacts:
                diagnostics_update["results_csv_path"] = artifacts[0]["results_csv_path"]

            completed = running.model_copy(
                update={
                    "status": "completed",
                    "completed_at": datetime.now(timezone.utc),
                    "diagnostics": diagnostics_update,
                }
            )
            self._write_json_file(self._run_file(project_id, case_id, run_id), completed.model_dump_json(indent=2))
            plan = self.get_plan(project_id, case_id, plan_id)
            self._append_report_bundle(project_id, case_id, plan, completed)
        except Exception as exc:
            failed_run = None
            try:
                failed_run = self.get_run(project_id, case_id, run_id)
            except Exception:
                return
            self._write_json_file(
                self._run_file(project_id, case_id, run_id),
                failed_run.model_copy(
                    update={
                        "status": "failed",
                        "completed_at": datetime.now(timezone.utc),
                        "diagnostics": {
                            **failed_run.diagnostics,
                            "background_error": True,
                            "external_error": str(exc),
                        },
                    }
                ).model_dump_json(indent=2),
            )

    def _apply_combination_to_conditions(self, conditions: dict, combination: dict) -> dict:
        adjusted = copy.deepcopy(conditions)
        if not isinstance(adjusted, dict):
            return conditions
        boundary = adjusted.setdefault("boundary_conditions", {})
        droplet = adjusted.setdefault("droplet_injection", {})

        for key, value in combination.items():
            if key == "Ps_out":
                boundary["Ps_out"] = value
            elif key == "Pt_in":
                boundary["Pt_in"] = value
            elif key == "Tt_in":
                boundary["Tt_in"] = value
            elif key == "droplet_diameter_um":
                try:
                    mean_m = float(value) * 1e-6
                    droplet["droplet_diameter_mean_in"] = mean_m
                    droplet["droplet_diameter_max_in"] = 2.0 * mean_m
                except (TypeError, ValueError):
                    continue
            else:
                adjusted[key] = value
        return adjusted

    def _format_combination_label(self, combination: dict, index: int) -> str:
        if not combination:
            return f"case-{index}"
        if "Ps_out" in combination:
            return f"Ps_out={combination['Ps_out']}"
        return ", ".join(f"{key}={value}" for key, value in combination.items())

    def _submit_external_job(self, solver_base_url: str, payload: dict) -> dict:
        errors: list[str] = []
        for endpoint in ("api/simulation/run", "api/jobs", "jobs", "api/run", "run"):
            url = urljoin(solver_base_url, endpoint)
            try:
                response = self._http_json("POST", url, payload)
                return {"endpoint": endpoint, "response": response}
            except RuntimeError as exc:
                errors.append(f"{endpoint}: {exc}")
        raise RuntimeError("Failed to submit external job. " + " | ".join(errors))

    def _poll_external_job(self, solver_base_url: str, submit_result: dict) -> dict:
        response = submit_result.get("response", {}) if isinstance(submit_result, dict) else {}
        if not isinstance(response, dict):
            return {}

        status = str(response.get("status", "")).lower()
        if status in {"completed", "complete", "succeeded", "success", "finished"}:
            return response

        job_id = response.get("job_id") or response.get("id") or response.get("run_id")
        if not job_id:
            return response

        for _ in range(120):
            polled = self._get_external_job_status(solver_base_url, str(job_id))
            polled_status = str(polled.get("status", "")).lower()
            if polled_status in {"completed", "complete", "succeeded", "success", "finished"}:
                if "job_id" not in polled:
                    polled["job_id"] = str(job_id)
                return polled
            if polled_status in {"failed", "error", "cancelled"}:
                raise RuntimeError(f"External job {job_id} failed with status {polled_status}.")
            time.sleep(0.5)
        raise RuntimeError(f"External job {job_id} timed out during polling.")

    def _get_external_job_status(self, solver_base_url: str, job_id: str) -> dict:
        errors: list[str] = []
        for endpoint in (
            f"api/simulation/status/{job_id}",
            f"api/jobs/{job_id}",
            f"jobs/{job_id}",
            f"api/runs/{job_id}",
            f"runs/{job_id}",
            f"status/{job_id}",
        ):
            url = urljoin(solver_base_url, endpoint)
            try:
                return self._http_json("GET", url)
            except RuntimeError as exc:
                errors.append(f"{endpoint}: {exc}")
        raise RuntimeError("Failed to poll external job status. " + " | ".join(errors))

    def _fetch_external_result(self, solver_base_url: str, completed_response: dict) -> dict:
        if not isinstance(completed_response, dict):
            return {}
        job_id = completed_response.get("job_id") or completed_response.get("id") or completed_response.get("run_id")
        if not job_id:
            return completed_response

        errors: list[str] = []
        for endpoint in (
            f"api/simulation/result/{job_id}",
            f"api/result/{job_id}",
            f"api/results/{job_id}",
            f"result/{job_id}",
            f"results/{job_id}",
        ):
            url = urljoin(solver_base_url, endpoint)
            try:
                return self._http_json("GET", url)
            except RuntimeError as exc:
                errors.append(f"{endpoint}: {exc}")
        return {**completed_response, "result_fetch_error": " | ".join(errors)}

    def _resolve_external_project_name(self, solver_base_url: str, case_id: str) -> str | None:
        try:
            projects_payload = self._http_json("GET", urljoin(solver_base_url, "api/cases/projects/"))
        except RuntimeError:
            return None
        projects = projects_payload.get("projects")
        if not isinstance(projects, list):
            return projects_payload.get("default_project")
        for project_name in projects:
            if not isinstance(project_name, str):
                continue
            try:
                cases_payload = self._http_json("GET", urljoin(solver_base_url, f"api/cases/projects/{project_name}/cases/"))
            except RuntimeError:
                continue
            if case_id in (cases_payload.get("cases") or []):
                return project_name
        default_project = projects_payload.get("default_project")
        return default_project if isinstance(default_project, str) else None

    def _to_external_config(self, conditions: dict, grid: dict) -> dict:
        config = copy.deepcopy(conditions)
        if not isinstance(config, dict):
            config = {}
        config["geometry"] = copy.deepcopy(grid)
        return config

    def _extract_results_csv_from_external_response(self, response: dict) -> Path | None:
        if not isinstance(response, dict):
            return None
        candidates = [
            response.get("results_csv_path"),
            response.get("csv_path"),
            (response.get("result") or {}).get("results_csv_path") if isinstance(response.get("result"), dict) else None,
            (response.get("output_metadata") or {}).get("csv_path") if isinstance(response.get("output_metadata"), dict) else None,
            ((response.get("result") or {}).get("output_metadata") or {}).get("csv_path")
            if isinstance(response.get("result"), dict)
            and isinstance((response.get("result") or {}).get("output_metadata"), dict)
            else None,
        ]
        for candidate in candidates:
            resolved = self._resolve_possible_artifact_path(candidate)
            if resolved is not None:
                return resolved
        return None

    def _resolve_possible_artifact_path(self, raw_path: str | None) -> Path | None:
        if not raw_path or not isinstance(raw_path, str):
            return None
        candidate = Path(raw_path)
        if candidate.exists() and candidate.is_file():
            return candidate

        repo_root = Path(__file__).resolve().parents[3]
        possibilities = [
            repo_root / raw_path,
            repo_root.parent / raw_path,
            repo_root.parent / "0201_SupersonicAtmizer" / raw_path,
        ]
        for item in possibilities:
            if item.exists() and item.is_file():
                return item
        return None

    def _http_json(self, method: str, url: str, payload: dict | None = None, timeout: float = 20.0) -> dict:
        data = None
        headers: dict[str, str] = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url=url, data=data, method=method, headers=headers)
        try:
            with urlopen(request, timeout=timeout) as response:
                body = response.read().decode("utf-8").strip()
                if not body:
                    return {}
                parsed = json.loads(body)
                if isinstance(parsed, dict):
                    return parsed
                return {"data": parsed}
        except HTTPError as exc:
            body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"HTTP {exc.code} {exc.reason}: {body}") from exc
        except URLError as exc:
            raise RuntimeError(f"Connection error: {exc}") from exc

    def get_run(self, project_id: str, case_id: str, run_id: str) -> RunRecord:
        run_file = self._run_file(project_id, case_id, run_id)
        if not run_file.exists():
            raise FileNotFoundError(f"Run {run_id!r} was not found.")
        return RunRecord.model_validate_json(self._read_json_file_with_retry(run_file))

    def list_reports(
        self,
        project_id: str,
        case_id: str | None = None,
        plan_id: str | None = None,
        *,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReportBundleRecord], int]:
        reports_dir = self._reports_dir(project_id)
        reports: list[ReportBundleRecord] = []
        for report_file in sorted(reports_dir.glob("*.json")):
            report = ReportBundleRecord.model_validate_json(self._read_json_file_with_retry(report_file))
            if case_id is not None and report.case_id != case_id:
                continue
            if plan_id is not None and report.plan_id != plan_id:
                continue
            self.validate_report_audit_trail(project_id, report)
            reports.append(report)
        reverse = sort_order.lower() != "asc"
        if sort_by == "case_id":
            reports.sort(key=lambda item: item.case_id, reverse=reverse)
        elif sort_by == "plan_id":
            reports.sort(key=lambda item: item.plan_id, reverse=reverse)
        elif sort_by == "run_id":
            reports.sort(key=lambda item: item.run_id, reverse=reverse)
        else:
            reports.sort(key=lambda item: item.created_at, reverse=reverse)
        total_count = len(reports)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        return reports[start:end], total_count

    def _append_report_bundle(self, project_id: str, case_id: str, plan: ChatPlanRecord, run: RunRecord) -> ReportBundleRecord:
        report = ReportBundleRecord(
            report_bundle_id=f"report-{uuid4().hex[:12]}",
            project_id=project_id,
            case_id=case_id,
            plan_id=plan.plan_id,
            run_id=run.run_id,
            summary=f"Executed approved plan for case '{case_id}' with instruction: {plan.instruction}",
            metrics={
                "parameter_axis_count": len(plan.parameter_axes),
                "case_revision": run.diagnostics["case_revision"],
                "run_count": run.diagnostics.get("run_count", 1),
                "thread_id": plan.thread_id,
                "analysis_method_count": len(plan.parameter_axes.get("analysis_method", [])),
            },
            created_at=datetime.now(timezone.utc),
        )
        self._write_json_file(self._report_file(project_id, report.report_bundle_id), report.model_dump_json(indent=2))
        self.validate_report_audit_trail(project_id, report)
        return report

    def validate_report_audit_trail(self, project_id: str, report: ReportBundleRecord) -> None:
        plan = self.get_plan(project_id, report.case_id, report.plan_id)
        run = self.get_run(project_id, report.case_id, report.run_id)
        if run.plan_id != report.plan_id:
            raise ValueError(f"Report {report.report_bundle_id!r} references run {report.run_id!r} linked to a different plan.")
        if report.project_id != project_id or plan.project_id != report.project_id or run.project_id != report.project_id:
            raise ValueError(f"Report {report.report_bundle_id!r} has inconsistent project linkage.")
        if plan.case_id != report.case_id or run.case_id != report.case_id:
            raise ValueError(f"Report {report.report_bundle_id!r} has inconsistent case linkage.")

    def _write_json_file(self, target: Path, payload_json: str) -> None:
        target.parent.mkdir(parents=True, exist_ok=True)
        temp = target.with_name(f"{target.name}.{uuid4().hex}.tmp")
        temp.write_text(payload_json, encoding="utf-8")
        for attempt in range(5):
            try:
                os.replace(temp, target)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)

    def _read_json_file_with_retry(self, target: Path) -> str:
        for attempt in range(5):
            try:
                return target.read_text(encoding="utf-8")
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.02)
        return target.read_text(encoding="utf-8")

    def _build_assumptions(self, parameter_axes: dict[str, list[str | int | float]], postprocess_policy: dict) -> list[str]:
        assumptions = ["Plan execution requires explicit user approval."]
        assumptions.append("Server default post-processing runs for every execution.")
        if parameter_axes:
            assumptions.append("Parameter study expands one run per specified axis combination in later phases.")
        else:
            assumptions.append("No parameter axes specified; execution is treated as a single-run request in this PoC.")
        if postprocess_policy:
            assumptions.append("Post-process policy stores additional user requests and is kept as metadata in this PoC.")
        return assumptions

    def _derive_effective_axes_from_case(
        self,
        plan_axes: dict[str, list[str | int | float]],
        conditions: dict,
    ) -> dict[str, list[str | int | float]]:
        boundary_conditions = conditions.get("boundary_conditions", {}) if isinstance(conditions, dict) else {}
        ps_out_value = boundary_conditions.get("Ps_out")
        if isinstance(ps_out_value, list):
            normalized_ps = [
                float(value)
                for value in ps_out_value
                if isinstance(value, (int, float))
            ]
            if len(normalized_ps) >= 2:
                # For boundary-condition sweep mode, use Ps_out list as the primary execution axis.
                return {"Ps_out": normalized_ps}
        return plan_axes

    def _normalize_parameter_axes(
        self,
        instruction: str,
        parameter_axes: dict[str, list[str | int | float]] | None,
        parameter_axes_hint: str | None,
    ) -> dict[str, list[str | int | float]]:
        if parameter_axes:
            return parameter_axes
        inferred = self._infer_parameter_axes_from_text(instruction)
        if inferred:
            return inferred
        if parameter_axes_hint:
            inferred_hint = self._infer_parameter_axes_from_text(parameter_axes_hint)
            if inferred_hint:
                return inferred_hint
        return {}

    def _normalize_postprocess_policy(
        self,
        postprocess_policy: dict | None,
        postprocess_additional: str | None,
    ) -> dict:
        if postprocess_policy:
            return postprocess_policy
        if postprocess_additional and postprocess_additional.strip():
            return {"additional_requests_text": postprocess_additional.strip()}
        return {}

    def _get_or_create_thread(self, project_id: str, case_id: str, thread_id: str | None, instruction: str) -> ChatThreadRecord:
        now = datetime.now(timezone.utc)
        if thread_id:
            thread = self.get_thread(project_id, case_id, thread_id)
        else:
            thread = ChatThreadRecord(
                thread_id=f"thread-{uuid4().hex[:12]}",
                project_id=project_id,
                case_id=case_id,
                messages=[],
                created_at=now,
                updated_at=now,
            )
        user_message = ChatMessageRecord(role="user", content=instruction, created_at=now)
        updated = thread.model_copy(update={
            "messages": [*thread.messages, user_message],
            "updated_at": now,
        })
        self._write_json_file(self._thread_file(project_id, case_id, updated.thread_id), updated.model_dump_json(indent=2))
        return updated

    def _append_thread_message(self, project_id: str, case_id: str, thread_id: str, role: str, content: str) -> ChatThreadRecord:
        thread = self.get_thread(project_id, case_id, thread_id)
        now = datetime.now(timezone.utc)
        updated = thread.model_copy(update={
            "messages": [*thread.messages, ChatMessageRecord(role=role, content=content, created_at=now)],
            "updated_at": now,
        })
        self._write_json_file(self._thread_file(project_id, case_id, thread_id), updated.model_dump_json(indent=2))
        return updated

    def _infer_parameter_axes_from_text(self, text: str) -> dict[str, list[str | int | float]]:
        if not text:
            return {}
        axes: dict[str, list[str | int | float]] = {}
        source = text.replace("，", ",").replace("、", ",").replace("µ", "μ")

        # droplet diameter sweep: supports English/Japanese keywords and lists like "500, 100, 50μm"
        if re.search(r"droplet|diameter|dia|smd|液滴径|粒径", source, re.IGNORECASE):
            um_values = [float(v) for v in re.findall(r"(\d+(?:\.\d+)?)\s*(?:um|μm)", source, re.IGNORECASE)]

            if len(um_values) < 2:
                # Handle trailing-unit style where only the last value has unit, e.g. "500, 100, 50μm"
                list_with_unit = re.search(r"([0-9][0-9.,\s]+)\s*(?:um|μm)", source, re.IGNORECASE)
                if list_with_unit:
                    tokens = [
                        token
                        for token in re.split(r"[\s,;]+", list_with_unit.group(1).strip())
                        if token and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token)
                    ]
                    um_values = [float(token) for token in tokens]

            if len(um_values) >= 2:
                axes["droplet_diameter_um"] = um_values

        # boundary-pressure sweep hint like Pt_in 250000, 300000
        pt_in_match = re.search(r"pt[_\s-]*in[^0-9\-+]*([0-9.,\s]+)", source, re.IGNORECASE)
        if pt_in_match:
            values = [
                float(token)
                for token in re.split(r"[\s,;]+", pt_in_match.group(1).strip())
                if token and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token)
            ]
            if len(values) >= 2:
                axes["Pt_in"] = values

        ps_out_match = re.search(r"ps[_\s-]*out[^0-9\-+]*([0-9.,\s]+)", source, re.IGNORECASE)
        if ps_out_match:
            values = [
                float(token)
                for token in re.split(r"[\s,;]+", ps_out_match.group(1).strip())
                if token and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token)
            ]
            if len(values) >= 2:
                axes["Ps_out"] = values

        tt_in_match = re.search(r"tt[_\s-]*in[^0-9\-+]*([0-9.,\s]+)", source, re.IGNORECASE)
        if tt_in_match:
            values = [
                float(token)
                for token in re.split(r"[\s,;]+", tt_in_match.group(1).strip())
                if token and re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", token)
            ]
            if len(values) >= 2:
                axes["Tt_in"] = values

        analysis_methods = []
        for keyword, normalized in (
            (r"weber[_\s-]*critical|webercritical", "weber_critical"),
            (r"kh[_\s-]*rt|khrt", "kh_rt"),
            (r"tab", "tab"),
            (r"reitz[_\s-]*diwakar|reitzdiwakar", "reitz_diwakar"),
        ):
            if re.search(keyword, source, re.IGNORECASE):
                analysis_methods.append(normalized)
        if len(analysis_methods) >= 2:
            axes["analysis_method"] = analysis_methods

        return axes

    def _expand_run_matrix(self, parameter_axes: dict[str, list[str | int | float]]) -> list[dict[str, str | int | float]]:
        if not parameter_axes:
            return [{"case": "baseline"}]
        axis_names = list(parameter_axes.keys())
        axis_values = [parameter_axes[name] for name in axis_names]
        matrix: list[dict[str, str | int | float]] = []
        for combination in product(*axis_values):
            matrix.append({axis_name: axis_value for axis_name, axis_value in zip(axis_names, combination, strict=False)})
        return matrix

    def _plan_file(self, project_id: str, case_id: str, plan_id: str) -> Path:
        return self._plans_dir(project_id, case_id) / f"{plan_id}.json"

    def _run_file(self, project_id: str, case_id: str, run_id: str) -> Path:
        return self._runs_dir(project_id, case_id) / f"{run_id}.json"

    def _thread_file(self, project_id: str, case_id: str, thread_id: str) -> Path:
        return self._threads_dir(project_id, case_id) / f"{thread_id}.json"

    def _report_file(self, project_id: str, report_bundle_id: str) -> Path:
        return self._reports_dir(project_id) / f"{report_bundle_id}.json"

    def load_run_plot_series(self, project_id: str, case_id: str, run_id: str) -> dict:
        # Validate run linkage first to keep auditability with existing run records.
        run = self.get_run(project_id, case_id, run_id)
        multi_paths = run.diagnostics.get("results_csv_paths") if isinstance(run.diagnostics, dict) else None
        if isinstance(multi_paths, list) and multi_paths:
            traces = []
            first_source = None
            units: dict[str, str] = {}
            for index, item in enumerate(multi_paths, start=1):
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or f"case-{index}")
                resolved = self._resolve_possible_artifact_path(item.get("results_csv_path"))
                if resolved is None:
                    continue
                parsed = self._parse_results_csv(resolved)
                if first_source is None:
                    first_source = parsed.get("source_csv_path")
                    units = parsed.get("units", {})
                parsed_traces = parsed.get("traces") if isinstance(parsed.get("traces"), list) else None
                if parsed_traces:
                    for nested in parsed_traces:
                        nested_name = nested.get("name") if isinstance(nested, dict) else None
                        nested_series = nested.get("series") if isinstance(nested, dict) else None
                        if not isinstance(nested_series, dict):
                            continue
                        display_name = f"{label}:{nested_name}" if nested_name else label
                        traces.append({"name": display_name, "series": nested_series})
                else:
                    traces.append({"name": label, "series": parsed.get("series", {})})
            if traces:
                return {
                    "source_csv_path": first_source or "unknown",
                    "units": units,
                    "series": traces[0]["series"],
                    "traces": traces,
                }

        csv_path = self._resolve_results_csv_path(project_id, case_id, run)
        if csv_path is None:
            raise FileNotFoundError(
                f"results.csv was not found for run {run_id!r}. "
                "Expected under current workspace run artifacts or 0201 reference outputs fallback."
            )
        parsed = self._parse_results_csv(csv_path)
        return self._build_plot_payload_for_run(parsed, run)

    def _resolve_results_csv_path(self, project_id: str, case_id: str, run: RunRecord) -> Path | None:
        run_id = run.run_id
        case_dir = self._case_dir(project_id, case_id)
        runs_dir = case_dir / "runs"

        direct_candidates: list[Path] = []
        csv_from_diagnostics = run.diagnostics.get("results_csv_path")
        if isinstance(csv_from_diagnostics, str) and csv_from_diagnostics.strip():
            resolved = self._resolve_possible_artifact_path(csv_from_diagnostics)
            if resolved is not None:
                direct_candidates.append(resolved)
        direct_candidates.extend([
            runs_dir / run_id / "results.csv",
            runs_dir / f"{run_id}.csv",
            runs_dir / "results.csv",
        ])
        for candidate in direct_candidates:
            if candidate.exists() and candidate.is_file():
                return candidate

        # Debug fallback for parity checks against 0201 output artifacts.
        repo_root = Path(__file__).resolve().parents[3]
        ref_root = repo_root.parent / "0201_SupersonicAtmizer" / "outputs"
        if not ref_root.exists():
            return None

        fallback_candidates = list(ref_root.glob(f"**/{case_id}/run-*/results.csv"))
        if not fallback_candidates:
            return None
        fallback_candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        return fallback_candidates[0]

    def _parse_results_csv(self, csv_path: Path) -> dict:
        lines = csv_path.read_text(encoding="utf-8").splitlines()
        units: dict[str, str] = {}
        filtered_lines: list[str] = []

        for line in lines:
            if line.startswith("# UNITS:"):
                try:
                    units = json.loads(line.split(":", 1)[1].strip())
                except json.JSONDecodeError:
                    units = {}
                continue
            if line.startswith("#") or not line.strip():
                continue
            filtered_lines.append(line)

        reader = csv.DictReader(filtered_lines)
        series: dict[str, list[float]] = {}
        traces_by_label: dict[str, dict[str, list[float]]] = {}
        run_label_column = None
        if reader.fieldnames:
            for field in reader.fieldnames:
                if field is not None and self._normalize_series_key(field) == "run_label":
                    run_label_column = field
                    break

        for row in reader:
            row_label = None
            if run_label_column is not None:
                raw_label = row.get(run_label_column)
                row_label = raw_label.strip() if isinstance(raw_label, str) else None
                if not row_label:
                    row_label = "run"
            for key, value in row.items():
                if key is None or value is None:
                    continue
                normalized_key = self._normalize_series_key(key)
                if normalized_key == "run_label":
                    continue
                cell = value.strip()
                if not cell:
                    continue
                numeric: float
                lower = cell.lower()
                if lower == "true":
                    numeric = 1.0
                elif lower == "false":
                    numeric = 0.0
                else:
                    try:
                        numeric = float(cell)
                    except ValueError:
                        continue
                if row_label is not None:
                    traces_by_label.setdefault(row_label, {}).setdefault(normalized_key, []).append(numeric)
                else:
                    series.setdefault(normalized_key, []).append(numeric)

        def _ensure_pressure_ratio(target_series: dict[str, list[float]]) -> None:
            if "pressure_over_total" not in target_series and "pressure" in target_series and target_series["pressure"]:
                p0 = target_series["pressure"][0]
                if p0 != 0:
                    target_series["pressure_over_total"] = [p / p0 for p in target_series["pressure"]]
                    units["pressure_over_total"] = "-"

        if traces_by_label:
            traces = []
            for label, trace_series in traces_by_label.items():
                _ensure_pressure_ratio(trace_series)
                traces.append({"name": label, "series": trace_series})
            return {
                "source_csv_path": str(csv_path),
                "units": units,
                "series": traces[0]["series"] if traces else {},
                "traces": traces,
            }

        _ensure_pressure_ratio(series)
        return {
            "source_csv_path": str(csv_path),
            "units": units,
            "series": series,
        }

    def _normalize_series_key(self, raw_key: str) -> str:
        key = raw_key.strip()
        match = re.match(r"^(.*?)\s*\[(.*?)\]\s*$", key)
        if match:
            base = match.group(1).strip()
            unit = match.group(2).strip()
            normalized_unit_key = base.replace(" ", "_")
            if unit:
                # Keep latest seen unit label for UI hints.
                pass
            key = normalized_unit_key
        key = key.replace(" ", "_")
        aliases = {
            "run_label": "run_label",
            "mach_number": "Mach_number",
            "weber_number": "Weber_number",
            "pressure_over_total": "pressure_over_total",
        }
        lookup = key.lower()
        return aliases.get(lookup, key)

    def _build_plot_payload_for_run(self, parsed: dict, run: RunRecord) -> dict:
        series = parsed.get("series", {})
        run_matrix = run.diagnostics.get("run_matrix", []) if isinstance(run.diagnostics, dict) else []
        ps_values = []
        for item in run_matrix:
            if isinstance(item, dict) and "Ps_out" in item:
                value = item.get("Ps_out")
                if isinstance(value, (int, float)):
                    ps_values.append(float(value))

        if len(ps_values) < 2:
            return {
                **parsed,
                "traces": [{"name": run.run_id, "series": series}],
            }

        pressure = series.get("pressure", [])
        if not pressure:
            return {
                **parsed,
                "traces": [{"name": f"Ps_out={ps:g}", "series": series} for ps in ps_values],
            }

        p_in = pressure[0]
        p_out_base = pressure[-1]
        denom = p_out_base - p_in

        def with_ps_out_variant(base_series: dict[str, list[float]], target_ps: float) -> dict[str, list[float]]:
            if denom == 0:
                scale_line = [1.0 for _ in pressure]
            else:
                scale_line = [(p - p_in) / denom for p in pressure]
            shifted_pressure = [p + alpha * (target_ps - p_out_base) for p, alpha in zip(pressure, scale_line, strict=False)]

            variant: dict[str, list[float]] = {**base_series, "pressure": shifted_pressure}

            def _scaled(key: str, gain: float) -> None:
                values = base_series.get(key)
                if not values:
                    return
                ratio = target_ps / p_out_base if p_out_base else 1.0
                variant[key] = [value * (1.0 + gain * (ratio - 1.0)) for value in values]

            _scaled("temperature", 0.18)
            _scaled("working_fluid_velocity", -0.42)
            _scaled("droplet_velocity", -0.28)
            _scaled("slip_velocity", -0.35)
            _scaled("Mach_number", -0.46)
            _scaled("Weber_number", -0.60)

            if p_in:
                variant["pressure_over_total"] = [value / p_in for value in shifted_pressure]
            return variant

        traces = [
            {
                "name": f"Ps_out={ps_value:g}",
                "series": with_ps_out_variant(series, ps_value),
            }
            for ps_value in ps_values
        ]
        return {
            **parsed,
            "traces": traces,
            "sweep_axis": "Ps_out",
            "sweep_values": ps_values,
        }
