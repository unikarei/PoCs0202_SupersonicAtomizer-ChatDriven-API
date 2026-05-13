# Supersonic Atomizer OptByAPI PoC Specification

## 1. Goal

Provide a GUI + API workflow where users can:

- initialize analysis from an existing Case YAML,
- instruct parameter study and post-processing through chat,
- execute studies under system-managed case control,
- accumulate report artifacts over time in the Report tab.

## 2. Primary User Flow

1. User creates a project.
2. System creates and owns a working directory for that project.
3. User selects an existing Case YAML in explorer.
4. System imports initial Conditions and Grid from the selected Case YAML.
5. User gives chat instructions for parameter study and post-processing policy.
6. System plans and executes required runs (boundary conditions, analysis method options, etc.).
7. System appends outputs into the Report tab as report bundles.
8. User reviews Graphs, Table, and Report, then iterates through chat.

## 3. Project and Case Management Model

### 3.1 Project

- A project is equivalent to a working directory.
- Working directory lifecycle is fully system-managed.
- Project creation must allocate a unique working directory.

### 3.2 Case

- Cases are system-managed entities inside a project workspace.
- Users do not manually maintain case file hierarchy after initial import.
- Initial Conditions and Grid are seeded from a user-selected Case YAML.

## 4. GUI Requirements

The main GUI tab composition must match the previous application:

- Conditions
- Grid
- Solve
- Graphs
- Table
- Report

Additional layout requirements:

- Chat panel must be on the right side of the GUI.
- Left side remains project/case explorer.
- Main center area hosts the tabbed workflow.

## 5. Chat-Driven Workflow Requirements

- Chat is case-aware and project-aware.
- User messages can request:
  - parameter sweeps,
  - boundary condition changes,
  - analysis method changes,
  - post-processing policies.
- System converts chat requests into executable plans.
- Instruction text is the primary input channel for user intent.
- Parameter axes input is optional; when omitted, the system infers sweep axes from instruction text where possible.
- Post-process input records additional requests only; server default post-processing is always executed.
- Chat-generated execution plans require explicit user approval before execution.
- Plans must be traceable and reproducible in stored metadata.

## 6. Report Accumulation Requirements

- Report tab stores a cumulative report collection, not only latest run.
- Report timeline scope is project-wide (aggregates all cases in the project).
- Each executed plan adds a report bundle with:
  - request summary,
  - execution settings,
  - produced metrics/plots/tables,
  - timestamp and case/project context.
- Users can review history in chronological order.
- Report bundles and generated artifacts are retained without deletion during the PoC period.

## 6.1 Case YAML Mutability Policy

- Imported Case YAML can be overwritten by later approved changes.
- System must keep revision metadata for each approved update.

## 6.2 Graph Display Policy (SDD)

- Default Graphs behavior must be case-scoped: render the latest report for the case selected in Conditions.
- Graphs tab must support a comparison mode for user-selected report entries.
- Comparison mode must provide two display styles:
  - overlay mode: merge selected datasets into the same graph panels,
  - separate mode: render selected datasets as independent graph groups.
- Report list must allow explicit data selection for comparison; comparison rendering uses only selected entries.

## 7. Non-Functional Requirements

- Preserve UI parity for tab structure and right-side chat placement.
- Keep API contracts explicit for project/case/chat/report operations.
- Ensure each run is attributable to a user instruction and plan ID.
- Support resumable workflow within a project working directory.

## 8. Decisions Confirmed

1. Chat plans are executed only after explicit user approval.
2. Report tab timeline is shared project-wide.
3. Artifact/report retention is full retention for the PoC period.
4. Imported Case YAML is updatable (overwrite allowed) after approval.
