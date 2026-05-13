# Supersonic Atomizer OptByAPI PoC Task Plan

## Phase 0: Document Baseline

- [x] T0-1: Establish spec, architecture, and task documents.
- [x] T0-2: Align copilot-instructions with new project documents.
- [x] T0-3: Record confirmed policy decisions (approval, report scope, retention, mutability).

## Phase 1: Project and Case Foundations

- [x] T1-1: Implement project creation as working-directory allocation.
- [x] T1-2: Implement project listing/loading from managed workspace roots.
- [x] T1-3: Implement case import from user-selected Case YAML.
- [x] T1-4: Persist imported Conditions and Grid as system-managed case revision.
- [x] T1-5: Add validation and error taxonomy for import failures.

## Phase 2: GUI Parity Layout

- [x] T2-1: Build 3-pane layout (left explorer, center tabs, right chat).
- [x] T2-2: Implement fixed tab bar: Conditions, Grid, Solve, Graphs, Table, Report.
- [x] T2-3: Bind left explorer to project and system-managed case state.
- [x] T2-4: Implement tab data refresh behavior after run completion.

## Phase 3: Chat Orchestration

- [x] T3-1: Add case-aware chat thread model.
- [x] T3-2: Define chat intent schema for parameter study and post-process policy.
- [x] T3-3: Implement intent-to-plan translation with plan_id and trace metadata.
- [x] T3-4: Add mandatory plan preview + explicit user approval gate.

## Phase 4: Parameter Study and Execution

- [x] T4-1: Implement planner for boundary-condition sweep expansion.
- [x] T4-2: Implement planner for analysis-method variation.
- [x] T4-3: Execute run matrix and capture run diagnostics.
- [x] T4-4: Provide run status API and progress model for GUI.

## Phase 5: Report Accumulation

- [x] T5-1: Define ReportBundle schema.
- [x] T5-2: Append each completed plan into ReportBundle timeline.
- [x] T5-3: Render report timeline in Report tab.
- [x] T5-4: Add filtering/sorting by case, plan, and timestamp for project-wide timeline.
- [x] T5-5: Add pagination/virtualization to keep project-wide report timeline responsive.

## Phase 6: Quality and Operations

- [x] T6-1: Add integration tests for project->case import->chat->run->report flow.
- [x] T6-2: Add regression checks for tab layout parity.
- [x] T6-3: Add audit trail validation for plan_id and report_bundle_id linkage.
- [x] T6-4: Document operational playbook for full-retention artifact management in PoC.

## Current Sprint Proposal

1. Extend the GUI shell with richer project/case forms and report rendering.
2. Add better progress feedback for background runs.
3. Implement parameter-sweep expansion beyond metadata-only plan persistence.

## Implemented Foundation

1. Project create/list APIs are implemented.
2. Project explorer tree API is implemented.
3. Case import, detail, and approved update APIs are implemented.
4. Chat plan preview, explicit approval, queued/background run dispatch, run status, and project report list APIs are implemented as PoC workflow persistence.
5. A 3-pane GUI shell is implemented at the repository root.
6. End-to-end integration test covers project -> case -> update -> plan -> approve -> run -> report.

## Next SDD Slice

1. Make Solve plan input instruction-centric and keep JSON fields optional helper inputs.
2. Infer parameter axes from instruction text when explicit axes are omitted.
3. Treat post-process input as additional requests only while always running server defaults.

## Confirmed Decisions

1. Approval mode: explicit approve per plan.
2. Report scope: project-wide timeline.
3. Artifact retention: keep all artifacts in PoC.
4. Case mutability: in-place update allowed after approval.
