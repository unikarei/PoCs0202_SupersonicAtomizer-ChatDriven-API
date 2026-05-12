# Supersonic Atomizer OptByAPI

GUI + API workflow PoC for supersonic atomizer project and case orchestration.

## What works now

- Project create/list
- Project explorer tree
- Case import from user-selected YAML
- Case detail and approved update
- Chat plan creation and explicit approval
- Case-aware chat thread continuity across repeated plans
- Background run dispatch with queued / running / completed status
- Parameter sweep and analysis-method run matrix expansion with diagnostics
- Project-wide report listing with sort and paging controls
- 3-pane GUI shell: Explorer, Workspace tabs, Right-side Chat

## Quick Start

### 1. Install dependencies

```powershell
python -m pip install -e .
```

### 2. Run the app

On Windows, use:

```bat
run.bat
```

This starts the FastAPI app at:

```text
http://127.0.0.1:8000/
```

### 3. Open the GUI

Open the root URL in a browser. The current shell includes:

- left Project Explorer
- center tabs: Conditions, Grid, Solve, Graphs, Table, Report
- right Chat panel

## Verification

Run the integration test with:

```powershell
python -m pytest tests/test_phase1_api.py
```

Expected result at this stage:

- the root page loads
- a project can be created
- a case can be imported from YAML
- a plan can be approved and executed
- run-matrix diagnostics are captured for parameter sweeps
- a report bundle is created after run completion
- report listing supports sort and paging metadata

## Notes

- `PYTHONPATH` is set by `run.bat` so the `src/` layout works from the repository root.
- The current run execution is a PoC background flow, not a full solver pipeline.
- Case updates require explicit approval.

## Operational Playbook

1. Start the server with `run.bat` from the repository root so the `src/` package path is active.
2. Create or select a project first. A project maps to one managed working directory under the workspace root.
3. Import each Case YAML through the GUI. Re-importing the same case name creates a new case revision after confirmation.
4. Create plans from the case chat. The system keeps a case-aware thread ID across repeated plan creation for the selected case.
5. Approve a plan before execution. Every approved run stores the plan ID, thread ID, case revision, run matrix, and report linkage for audit.
6. Use the Report tab controls to sort by created time, case, plan, or run and page through retained report bundles.
7. Keep all generated artifacts. This PoC follows full-retention behavior; do not manually delete plan, run, thread, or report JSON files if auditability matters.
8. If a run appears stalled, reload the GUI first. If needed, restart the server and inspect the latest files under the selected project's `cases/<case_id>/runs` and `reports` directories.
