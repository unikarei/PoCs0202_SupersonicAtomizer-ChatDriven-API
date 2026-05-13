from __future__ import annotations

from pathlib import Path
import time

from fastapi.testclient import TestClient
import yaml

from supersonic_atomizer_optbyapi.api.app import create_app
from supersonic_atomizer_optbyapi.models import ReportBundleRecord
from supersonic_atomizer_optbyapi.services.workflow_service import WorkflowService


def test_project_create_and_case_import_flow(tmp_path: Path) -> None:
    sample_yaml = tmp_path / "sample_case.yaml"
    sample_yaml.write_text(
        yaml.safe_dump(
            {
                "conditions": {"Pt_in": 200000, "Tt_in": 400},
                "grid": {"x_start": 0.0, "x_end": 0.1, "n_cells": 100},
            }
        ),
        encoding="utf-8",
    )
    sample_yaml_overwrite = tmp_path / "sample_case_overwrite.yaml"
    sample_yaml_overwrite.write_text(
        yaml.safe_dump(
            {
                "conditions": {"Pt_in": 310000, "Tt_in": 450},
                "grid": {"x_start": 0.0, "x_end": 0.12, "n_cells": 140},
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))

    root = client.get("/")
    assert root.status_code == 200
    assert "Supersonic Atomizer OptByAPI" in root.text

    create_project = client.post("/api/projects/", json={"project_name": "demo-project"})
    assert create_project.status_code == 201

    import_case = client.post(
        "/api/projects/demo-project/cases/import",
        json={"source_yaml_path": str(sample_yaml), "case_name": "baseline"},
    )
    assert import_case.status_code == 201
    payload = import_case.json()
    assert payload["revision"] == 1
    assert payload["conditions"]["Pt_in"] == 200000
    assert payload["grid"]["n_cells"] == 100

    duplicate_import = client.post(
        "/api/projects/demo-project/cases/import",
        json={"source_yaml_path": str(sample_yaml), "case_name": "baseline"},
    )
    assert duplicate_import.status_code == 409

    overwrite_import = client.post(
        "/api/projects/demo-project/cases/import",
        json={"source_yaml_path": str(sample_yaml_overwrite), "case_name": "baseline", "overwrite": True},
    )
    assert overwrite_import.status_code == 201
    overwrite_payload = overwrite_import.json()
    assert overwrite_payload["revision"] == 2
    assert overwrite_payload["conditions"]["Pt_in"] == 310000
    assert overwrite_payload["grid"]["n_cells"] == 140

    list_cases = client.get("/api/projects/demo-project/cases/")
    assert list_cases.status_code == 200
    list_payload = list_cases.json()
    assert list_payload["project_id"] == "demo-project"
    assert len(list_payload["cases"]) == 1
    assert list_payload["cases"][0]["case_id"] == "baseline"

    project_tree = client.get("/api/projects/tree")
    assert project_tree.status_code == 200
    tree_payload = project_tree.json()
    assert len(tree_payload["projects"]) == 1
    assert tree_payload["projects"][0]["project"]["project_id"] == "demo-project"
    assert tree_payload["projects"][0]["cases"][0]["case_id"] == "baseline"

    case_detail = client.get("/api/projects/demo-project/cases/baseline")
    assert case_detail.status_code == 200
    assert case_detail.json()["revision"] == 2

    rejected_update = client.put(
        "/api/projects/demo-project/cases/baseline",
        json={
            "conditions": {"Pt_in": 250000, "Tt_in": 420},
            "grid": {"x_start": 0.0, "x_end": 0.2, "n_cells": 120},
            "approved": False,
        },
    )
    assert rejected_update.status_code == 400

    approved_update = client.put(
        "/api/projects/demo-project/cases/baseline",
        json={
            "conditions": {"Pt_in": 250000, "Tt_in": 420},
            "grid": {"x_start": 0.0, "x_end": 0.2, "n_cells": 120},
            "approved": True,
            "approval_comment": "Approved in GUI",
        },
    )
    assert approved_update.status_code == 200
    updated_payload = approved_update.json()
    assert updated_payload["revision"] == 3
    assert updated_payload["conditions"]["Pt_in"] == 250000

    create_plan = client.post(
        "/api/projects/demo-project/cases/baseline/chat/plans",
        json={
            "instruction": "入口液滴径を1000, 500, 50μmとして解析する。出口圧は初期ケースと同じ。",
            "postprocess_additional": "plot mach number, max droplet dia, average droplet dia",
        },
    )
    assert create_plan.status_code == 201
    plan_payload = create_plan.json()["plan"]
    assert plan_payload["approval_state"] == "pending"
    assert plan_payload["thread_id"].startswith("thread-")
    assert plan_payload["parameter_axes"]["droplet_diameter_um"] == [1000.0, 500.0, 50.0]
    assert plan_payload["postprocess_policy"]["additional_requests_text"].startswith("plot mach number")
    plan_id = plan_payload["plan_id"]

    rejected_run = client.post(
        "/api/projects/demo-project/cases/baseline/runs",
        json={"plan_id": plan_id},
    )
    assert rejected_run.status_code == 400

    approve_plan = client.post(f"/api/projects/demo-project/cases/baseline/chat/plans/{plan_id}/approve")
    assert approve_plan.status_code == 200
    approved_plan_payload = approve_plan.json()["plan"]
    assert approved_plan_payload["approval_state"] == "approved"

    execute_run = client.post(
        "/api/projects/demo-project/cases/baseline/runs",
        json={"plan_id": plan_id},
    )
    assert execute_run.status_code == 202
    run_payload = execute_run.json()
    assert run_payload["status"] == "queued"
    assert run_payload["diagnostics"]["run_count"] == 3
    run_id = run_payload["run_id"]

    final_run = None
    for _ in range(20):
        current = client.get(f"/api/projects/demo-project/cases/baseline/runs/{run_id}")
        assert current.status_code == 200
        final_run = current.json()
        if final_run["status"] == "completed":
            break
        time.sleep(0.1)
    assert final_run is not None
    assert final_run["status"] == "completed"

    run_detail = client.get(f"/api/projects/demo-project/cases/baseline/runs/{run_id}")
    assert run_detail.status_code == 200
    assert run_detail.json()["plan_id"] == plan_id

    reports = client.get("/api/projects/demo-project/reports?case_id=baseline&plan_id=" + plan_id)
    assert reports.status_code == 200
    reports_payload = reports.json()
    assert reports_payload["total_count"] == 1
    assert reports_payload["page"] == 1
    assert len(reports_payload["reports"]) == 1
    assert reports_payload["reports"][0]["plan_id"] == plan_id
    assert reports_payload["reports"][0]["metrics"]["run_count"] == 3


def test_report_sorting_pagination_and_audit_linkage(tmp_path: Path) -> None:
    sample_yaml = tmp_path / "sample_case.yaml"
    sample_yaml.write_text(
        yaml.safe_dump(
            {
                "conditions": {"Pt_in": 200000, "Tt_in": 400},
                "grid": {"x_start": 0.0, "x_end": 0.1, "n_cells": 100},
            }
        ),
        encoding="utf-8",
    )

    workspace_root = tmp_path / "workspace"
    client = TestClient(create_app(workspace_root=workspace_root))
    assert client.post("/api/projects/", json={"project_name": "demo-project"}).status_code == 201
    assert client.post(
        "/api/projects/demo-project/cases/import",
        json={"source_yaml_path": str(sample_yaml), "case_name": "baseline"},
    ).status_code == 201

    thread_id = None
    for instruction in (
        "Sweep Pt_in 200000, 250000 and compare breakup model WeberCritical KH-RT.",
        "Sweep Pt_in 260000, 280000 and compare breakup model WeberCritical TAB.",
    ):
        payload = {"instruction": instruction}
        if thread_id:
            payload["thread_id"] = thread_id
        create_plan = client.post("/api/projects/demo-project/cases/baseline/chat/plans", json=payload)
        assert create_plan.status_code == 201
        plan_payload = create_plan.json()["plan"]
        if thread_id is None:
            thread_id = plan_payload["thread_id"]
        assert plan_payload["thread_id"] == thread_id
        assert "analysis_method" in plan_payload["parameter_axes"]

        approve_plan = client.post(f"/api/projects/demo-project/cases/baseline/chat/plans/{plan_payload['plan_id']}/approve")
        assert approve_plan.status_code == 200

        execute_run = client.post(
            "/api/projects/demo-project/cases/baseline/runs",
            json={"plan_id": plan_payload["plan_id"]},
        )
        assert execute_run.status_code == 202
        run_id = execute_run.json()["run_id"]
        final_run = None
        for _ in range(30):
            current = client.get(f"/api/projects/demo-project/cases/baseline/runs/{run_id}")
            assert current.status_code == 200
            final_run = current.json()
            if final_run["status"] == "completed":
                break
            time.sleep(0.1)
        assert final_run is not None
        assert final_run["status"] == "completed"
        assert final_run["diagnostics"]["run_count"] == 4

    page_one = client.get("/api/projects/demo-project/reports?case_id=baseline&sort_by=created_at&sort_order=desc&page=1&page_size=1")
    assert page_one.status_code == 200
    page_one_payload = page_one.json()
    assert page_one_payload["total_count"] == 2
    assert len(page_one_payload["reports"]) == 1

    page_two = client.get("/api/projects/demo-project/reports?case_id=baseline&sort_by=created_at&sort_order=desc&page=2&page_size=1")
    assert page_two.status_code == 200
    page_two_payload = page_two.json()
    assert len(page_two_payload["reports"]) == 1
    assert page_one_payload["reports"][0]["report_bundle_id"] != page_two_payload["reports"][0]["report_bundle_id"]

    service = WorkflowService(workspace_root=workspace_root)
    for report_payload in page_one_payload["reports"] + page_two_payload["reports"]:
        service.validate_report_audit_trail("demo-project", ReportBundleRecord.model_validate(report_payload))


def test_ui_tab_layout_contract(tmp_path: Path) -> None:
    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    root = client.get("/")
    assert root.status_code == 200
    for label in ("Conditions", "Grid", "Solve", "Graphs", "Table", "Report"):
        assert label in root.text
    for element_id in (
        "tab-conditions",
        "tab-grid",
        "tab-solve",
        "tab-graphs",
        "tab-table",
        "tab-report",
        "report-sort-by",
        "report-sort-order",
        "report-prev-page",
        "report-next-page",
    ):
        assert f'id="{element_id}"' in root.text


def test_legacy_yaml_and_upload_import(tmp_path: Path) -> None:
    legacy_yaml = tmp_path / "legacy_case.yaml"
    legacy_yaml.write_text(
        yaml.safe_dump(
            {
                "fluid": {"working_fluid": "steam", "inlet_wetness": 0.0},
                "boundary_conditions": {"Pt_in": 300000, "Tt_in": 520, "Ps_out": [200000, 150000]},
                "geometry": {
                    "x_start": 0.0,
                    "x_end": 0.5,
                    "n_cells": 100,
                    "area_distribution": {
                        "type": "table",
                        "x": [0.0, 0.1, 0.5],
                        "A": [0.00018, 0.0001, 0.00014],
                    },
                },
                "droplet_injection": {"droplet_velocity_in": 10.0},
                "model_selection": {"breakup_model": "weber_critical"},
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    create_project = client.post("/api/projects/", json={"project_name": "legacy-project"})
    assert create_project.status_code == 201

    import_by_path = client.post(
        "/api/projects/legacy-project/cases/import",
        json={"source_yaml_path": str(legacy_yaml), "case_name": "legacy-path"},
    )
    assert import_by_path.status_code == 201
    imported_path_payload = import_by_path.json()
    assert imported_path_payload["conditions"]["boundary_conditions"]["Pt_in"] == 300000
    assert imported_path_payload["grid"]["n_cells"] == 100

    with legacy_yaml.open("rb") as fp:
        import_by_upload = client.post(
            "/api/projects/legacy-project/cases/import-upload",
            data={"case_name": "legacy-upload"},
            files={"source_yaml": ("001_WeberCritical_ForAgents.yaml", fp, "application/x-yaml")},
        )
    assert import_by_upload.status_code == 201
    imported_upload_payload = import_by_upload.json()
    assert imported_upload_payload["source_yaml_path"].startswith("upload://")
    assert imported_upload_payload["conditions"]["fluid"]["working_fluid"] == "steam"


def test_ps_out_list_in_conditions_drives_sweep_run_count(tmp_path: Path) -> None:
    case_yaml = tmp_path / "ps_out_case.yaml"
    case_yaml.write_text(
        yaml.safe_dump(
            {
                "conditions": {
                    "boundary_conditions": {
                        "Pt_in": 300000,
                        "Tt_in": 520,
                        "Ps_out": [264547.5, 226105.55, 207259.55, 191105.85, 49704.25, 33136.15, 25000.0],
                    }
                },
                "grid": {"x_start": 0.0, "x_end": 0.5, "n_cells": 100},
            }
        ),
        encoding="utf-8",
    )

    client = TestClient(create_app(workspace_root=tmp_path / "workspace"))
    assert client.post("/api/projects/", json={"project_name": "ps-project"}).status_code == 201
    assert client.post(
        "/api/projects/ps-project/cases/import",
        json={"source_yaml_path": str(case_yaml), "case_name": "ps-case"},
    ).status_code == 201

    create_plan = client.post(
        "/api/projects/ps-project/cases/ps-case/chat/plans",
        json={"instruction": "run with existing conditions"},
    )
    assert create_plan.status_code == 201
    plan_id = create_plan.json()["plan"]["plan_id"]
    assert client.post(f"/api/projects/ps-project/cases/ps-case/chat/plans/{plan_id}/approve").status_code == 200

    execute_run = client.post(
        "/api/projects/ps-project/cases/ps-case/runs",
        json={"plan_id": plan_id},
    )
    assert execute_run.status_code == 202
    run_payload = execute_run.json()
    assert run_payload["diagnostics"]["run_count"] == 7
    assert run_payload["diagnostics"]["sweep_source"] == "conditions.boundary_conditions.Ps_out"
