# Supersonic Atomizer OptByAPI API Endpoints

## 1. Purpose

This document defines the implemented Phase 1/early-Phase 3 HTTP contract and the next target contract shape.

Principles:

- All state mutations go through the API.
- A project is a system-managed working directory.
- Cases are system-managed records inside a project.
- Chat-generated plans are approval-gated before execution.

## 2. Resource Summary

- Project
- Case
- ChatThread
- ChatPlan
- ReportBundle

## 3. Phase 1 Endpoints

### 3.1 Projects

#### GET `/api/projects/`

List all managed projects.

Response `200 OK`:

```json
{
  "projects": [
    {
      "project_id": "demo-project",
      "project_name": "demo-project",
      "workspace_path": "D:/.../workspace/demo-project",
      "created_at": "2026-05-10T10:00:00Z"
    }
  ]
}
```

#### POST `/api/projects/`

Create a new project and allocate its working directory.

Request:

```json
{
  "project_name": "demo-project"
}
```

Response `201 Created`:

```json
{
  "project_id": "demo-project",
  "project_name": "demo-project",
  "workspace_path": "D:/.../workspace/demo-project",
  "created_at": "2026-05-10T10:00:00Z"
}
```

Errors:

- `400 Bad Request`: invalid project name
- `409 Conflict`: project already exists

#### GET `/api/projects/tree`

Return project explorer data in one response.

Response `200 OK`:

```json
{
  "projects": [
    {
      "project": {
        "project_id": "demo-project",
        "project_name": "demo-project",
        "workspace_path": "D:/.../workspace/demo-project",
        "created_at": "2026-05-10T10:00:00Z"
      },
      "cases": [
        {
          "case_id": "baseline-nozzle",
          "project_id": "demo-project",
          "source_yaml_path": "D:/cases/baseline.yaml",
          "revision": 1,
          "created_at": "2026-05-10T10:05:00Z",
          "updated_at": "2026-05-10T10:05:00Z"
        }
      ]
    }
  ]
}
```

### 3.2 Cases

#### GET `/api/projects/{project_id}/cases/`

List imported cases for the given project.

Response `200 OK`:

```json
{
  "project_id": "demo-project",
  "cases": [
    {
      "case_id": "baseline-nozzle",
      "project_id": "demo-project",
      "source_yaml_path": "D:/cases/baseline.yaml",
      "revision": 1,
      "created_at": "2026-05-10T10:05:00Z",
      "updated_at": "2026-05-10T10:05:00Z"
    }
  ]
}
```

#### POST `/api/projects/{project_id}/cases/import`

Import initial Conditions and Grid from a user-selected Case YAML.

Request:

```json
{
  "source_yaml_path": "D:/cases/baseline.yaml",
  "case_name": "baseline-nozzle"
}
```

Behavior:

- validates project existence,
- validates YAML file existence,
- extracts `conditions` and `grid`,
- creates a system-managed case record,
- stores imported snapshot under the project working directory,
- sets `revision = 1`.

Response `201 Created`:

```json
{
  "case_id": "baseline-nozzle",
  "project_id": "demo-project",
  "source_yaml_path": "D:/cases/baseline.yaml",
  "revision": 1,
  "conditions": {},
  "grid": {},
  "created_at": "2026-05-10T10:05:00Z",
  "updated_at": "2026-05-10T10:05:00Z"
}
```

Errors:

- `400 Bad Request`: invalid name, invalid YAML, missing required sections
- `404 Not Found`: project or source file not found
- `409 Conflict`: case already exists

#### GET `/api/projects/{project_id}/cases/{case_id}`

Return full case detail for editor binding.

#### PUT `/api/projects/{project_id}/cases/{case_id}`

Update Conditions and Grid for a system-managed case.

Request:

```json
{
  "conditions": {
    "Pt_in": 250000,
    "Tt_in": 420
  },
  "grid": {
    "x_start": 0.0,
    "x_end": 0.2,
    "n_cells": 120
  },
  "approved": true,
  "approval_comment": "Approved in GUI"
}
```

Behavior:

- requires `approved = true`,
- increments `revision`,
- overwrites stored `imported_source.yaml`,
- appends a new revision snapshot.

Errors:

- `400 Bad Request`: approval missing or invalid payload
- `404 Not Found`: project or case not found

## 4. Implemented Workflow Endpoints

### 4.1 Chat

#### POST `/api/projects/{project_id}/cases/{case_id}/chat/plans`

Create a candidate execution plan from user instruction.

Request (instruction-first; optional helper fields):

```json
{
  "instruction": "Sweep inlet droplet diameter 1000um, 500um, 50um. Exit pressure is same as initial case.",
  "parameter_axes": null,
  "parameter_axes_hint": null,
  "postprocess_policy": null,
  "postprocess_additional": "plot mach number, max droplet dia, average droplet dia"
}
```

Behavior:

- `instruction` is mandatory and primary.
- `parameter_axes` is optional; if omitted, server tries to infer sweep axes from instruction text and optional `parameter_axes_hint`.
- Server default post-processing always runs.
- `postprocess_policy`/`postprocess_additional` describe additional post-processing requests only.

Response includes:

- `plan_id`
- `approval_state = "pending"`
- `parameter_axes`
- `postprocess_policy`
- `assumptions`

#### POST `/api/projects/{project_id}/cases/{case_id}/chat/plans/{plan_id}/approve`

Explicitly approve a candidate plan for execution.

Response `200 OK`:

```json
{
  "plan": {
    "plan_id": "plan-123456789abc",
    "project_id": "demo-project",
    "case_id": "baseline-nozzle",
    "instruction": "Sweep inlet pressure and prepare summary plots.",
    "parameter_axes": {
      "Pt_in": [250000, 300000]
    },
    "postprocess_policy": {
      "additional_requests_text": "plot mach number, max droplet dia, average droplet dia"
    },
    "assumptions": [
      "Plan execution requires explicit user approval."
    ],
    "approval_state": "approved",
    "created_at": "2026-05-10T10:10:00Z",
    "approved_at": "2026-05-10T10:11:00Z"
  }
}
```

### 4.2 Execution

#### POST `/api/projects/{project_id}/cases/{case_id}/runs`

Dispatch an approved plan.

Request:

```json
{
  "plan_id": "plan-123456789abc"
}
```

Current PoC behavior:

- rejects pending plans,
- queues execution and returns immediately,
- advances through queued -> running -> completed,
- writes a run record,
- appends one report bundle.

#### GET `/api/projects/{project_id}/cases/{case_id}/runs/{run_id}`

Get run status and diagnostics.

### 4.3 Reports

#### GET `/api/projects/{project_id}/reports`

Return the project-wide report timeline.

Optional query params:

- `case_id`
- `plan_id`

## 5. Planned Next-Phase Endpoints

### 5.1 Chat Threads

#### GET `/api/projects/{project_id}/cases/{case_id}/chat/threads`

List chat threads for a case.

#### POST `/api/projects/{project_id}/cases/{case_id}/chat/threads`

Create a thread.

## 6. Persistence Contract

Project working directory example:

```text
{workspace_root}/
  {project_id}/
    project.json
    cases/
      {case_id}/
        case.json
        imported_source.yaml
        plans/
          {plan_id}.json
        runs/
          {run_id}.json
        revisions/
          0001.json
          0002.json
    reports/
      {report_bundle_id}.json
```

## 7. Validation Rules

### 6.1 Project Names

- ASCII letters, digits, `_`, `-`, `.` only
- no path separators
- no empty names

### 6.2 Case Import YAML

Initial Phase 1 import requires these top-level sections:

- `conditions`
- `grid`

Additional sections may exist and are preserved in the stored source snapshot, but only `conditions` and `grid` are interpreted in Phase 1.

### 7.3 Case Update Approval

- case mutation requires explicit `approved = true`
- missing approval is rejected with `400 Bad Request`

### 7.4 Run Dispatch

- run dispatch requires an existing approved plan
- pending plans cannot be executed
