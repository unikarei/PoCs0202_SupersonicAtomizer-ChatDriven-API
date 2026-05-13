# GitHub Copilot Instructions for This Repository

## 1. Source of Truth

Treat these files as the only planning authority for this repository:

- [docs/spec.md](docs/spec.md)
- [docs/architecture.md](docs/architecture.md)
- [docs/api-endpoints.md](docs/api-endpoints.md)
- [docs/task.md](docs/task.md)

If there is a conflict:

1. Follow [docs/spec.md](docs/spec.md) for product behavior.
2. Follow [docs/architecture.md](docs/architecture.md) for boundaries and interfaces.
3. Follow [docs/api-endpoints.md](docs/api-endpoints.md) for API contracts.
4. Follow [docs/task.md](docs/task.md) for implementation order.

Do not silently invent requirements.

## 2. Workflow

Always work in this order:

1. Update spec when behavior changes.
2. Update architecture when structure changes.
3. Update task list when scope or order changes.
4. Implement code for the active task only.
5. Validate and keep docs synchronized.

## 3. Scope Guardrails

This PoC targets GUI + API orchestration for supersonic atomizer analyses.

In scope:

- GUI with original tab structure from previous app.
- Right-side chat panel in GUI.
- Project model where one project equals one working directory.
- System-managed case lifecycle.
- User-provided initial Conditions and Grid through selecting a Case YAML file.
- Chat-driven parameter study and post-processing instructions.
- Explicit user approval before any chat-generated execution plan runs.
- Report accumulation in the Report tab.
- Project-wide report timeline with full artifact retention during PoC.

Out of scope unless explicitly added to spec:

- New physics models that are unrelated to requested workflows.
- Large UI redesign that breaks parity with previous tab model.
- Replacing chat-driven workflow with manual-only workflow.

## 4. Architecture Rules

Keep clear separation:

- UI rendering (tabs, panels, forms)
- API transport (HTTP endpoints, schemas)
- Workflow orchestration (chat intent to execution plan)
- Simulation execution adapters
- Artifact and report persistence

Rules:

- UI must call APIs and not run solver internals directly.
- Chat must issue structured intent and not directly mutate files.
- Project and case operations must go through a dedicated service.
- Report tab reads persisted report bundles only.

## 5. Definition of Done

For any non-trivial change:

- Behavior is traceable to one or more items in [docs/task.md](docs/task.md).
- Interfaces and data contracts are documented in [docs/architecture.md](docs/architecture.md).
- User-facing behavior is reflected in [docs/spec.md](docs/spec.md).
- Relevant tests or validation notes are added.
