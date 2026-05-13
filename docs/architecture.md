# Supersonic Atomizer OptByAPI PoC Architecture

## 1. Architectural Intent

Design a workflow-centric architecture where:

- GUI handles interaction and visualization,
- API mediates all state mutations,
- orchestration layer translates chat intent into executable studies,
- execution layer runs analyses,
- report layer persists cumulative report bundles.

## 2. High-Level Components

1. GUI Client
2. API Service
3. Project Workspace Service
4. Case Lifecycle Service
5. Chat Orchestration Service
6. Parameter Study Planner
 Uses instruction text as the primary source and parses user intent into structured action requests.
## 3. Responsibilities and Boundaries

 If explicit parameter axes are omitted, attempts conservative axis inference from instruction text.
  - center tabs,
  - right chat panel.
- Uses fixed tab set: Conditions, Grid, Solve, Graphs, Table, Report.
 Always executes API-server default post-processing; plan policy stores only additional post-process requests.
- Exposes endpoints for project, case, chat, solve, and report operations.
- Validates input contracts and delegates to domain services.
- Returns structured status and identifiers (project_id, case_id, plan_id, report_bundle_id).

### 3.3 Project Workspace Service

- Creates and manages project working directories.
- Guarantees project equals working directory mapping.
- Handles lifecycle operations (create, list, archive/delete if enabled).

### 3.4 Case Lifecycle Service

- Imports initial Conditions and Grid from selected Case YAML.
- Materializes system-managed internal case representation.
- Applies approved modifications coming from execution plans, including in-place YAML overwrite.
- Records case revision history for every approved update.

### 3.5 Chat Orchestration Service

- Maintains case-aware chat threads.
- Uses instruction text as the primary source and parses user intent into structured action requests.
- Produces candidate execution plans with explicit assumptions.

### 3.6 Parameter Study Planner

- Expands requests into concrete run matrix.
- Supports variation of boundary conditions and analysis methods.
- Emits deterministic plan graph with traceable plan_id.
- Marks each plan as approval-required before it can be dispatched.
- If explicit parameter axes are omitted, attempts conservative axis inference from instruction text.

### 3.7 Execution Service

- Executes plan steps through solver adapters.
- Tracks run status and captures diagnostics.
- Publishes result artifacts to report service.

### 3.8 Artifact and Report Service

- Persists plots, table snapshots, scalar metrics, and metadata.
- Appends report bundles to cumulative project-wide timeline.
- Serves report bundles to Report tab.
- Keeps all report bundles and artifacts for the full PoC period.
- Always executes API-server default post-processing; plan policy stores only additional post-process requests.

## 4. Data Contracts (Logical)

Detailed HTTP endpoint contracts are defined in [docs/api-endpoints.md](api-endpoints.md).

### 4.1 Project

- project_id
- project_name
- workspace_path
- created_at

### 4.2 Case

- case_id
- project_id
- source_yaml_path
- conditions
- grid
- revision

### 4.3 ChatPlan

- thread_id
- message_id
- plan_id
- requested_objective
- parameter_axes
- postprocess_policy
- approval_state

### 4.4 ReportBundle

- report_bundle_id
- project_id
- case_id
- plan_id
- run_ids
- summary
- plots
- table_snapshot
- artifacts
- created_at

## 5. Key Sequences

### 5.1 Project Initialization

1. GUI requests project creation.
2. API asks Project Workspace Service to allocate working directory.
3. API returns project context.

### 5.2 Case Seeding

1. User selects Case YAML from explorer.
2. GUI uploads path/file reference via API.
3. Case Lifecycle Service imports Conditions and Grid.
4. API returns case context and revision 1.

### 5.3 Chat to Execution

1. User sends instruction in right-side chat.
2. Chat Orchestration Service generates candidate plan.
3. Planner expands run matrix and marks plan as approval-required.
4. User approves plan in UI.
5. Execution Service runs plan.
6. Artifact and Report Service appends report bundle.
7. GUI refreshes Graphs/Table/Report tabs.

## 6. Parity Constraints from Previous App

- Preserve tab composition: Conditions, Grid, Solve, Graphs, Table, Report.
- Preserve right-side chat placement.
- Preserve left project/case explorer role.

## 7. Extensibility Points

- Swap chat model/provider behind Chat Orchestration Service interface.
- Add planner strategies without changing GUI contracts.
- Add report renderers without changing execution contracts.

## 8. Risks and Controls

- Risk: ambiguous chat intent causes unsafe runs.
  - Control: mandatory approval gate before execution.
- Risk: report timeline bloat.
  - Control: project-level filters and pagination while retaining all artifacts.
- Risk: divergence between GUI state and persisted case revision.
  - Control: optimistic revision checks on API writes.
