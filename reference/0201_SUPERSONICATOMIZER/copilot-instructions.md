# GitHub Copilot Instructions for This Repository

## 1. Source of Truth

Treat the following documents as authoritative and binding for all work in this repository:

- [docs/spec.md](../docs/spec.md)
- [docs/architecture.md](../docs/architecture.md)
- [docs/tasks.md](../docs/tasks.md)

When there is any uncertainty:

1. follow [docs/spec.md](../docs/spec.md) for product scope and requirements,
2. follow [docs/architecture.md](../docs/architecture.md) for structure and boundaries,
3. follow [docs/tasks.md](../docs/tasks.md) for implementation order and task granularity.

Do not silently invent requirements that are not consistent with these documents.

---

## 2. Mandatory Development Workflow

This repository uses strict specification-driven development.

Always work in this order:

1. spec
2. architecture
3. tasks
4. implementation
5. update documents

If the repository state is not aligned with that order, prefer updating documents before writing code.

Do not jump ahead to broad implementation when the current task is still architectural, planning, or validation related.

---

## 3. Task-First Implementation Policy

Only implement work that can be traced to an approved task in [docs/tasks.md](../docs/tasks.md).

Before making code changes:

- identify the relevant phase and task ID,
- keep changes scoped to that task and its direct prerequisites,
- avoid bundling multiple unrelated tasks into one implementation step.

If a requested change is larger than a small, testable task:

- break it down first,
- preserve the phase structure,
- do not generate a large all-at-once implementation.

Prefer a sequence of small, reviewable changes over large code drops.

---

## 4. Anti-Overreach Rules

Do not:

- implement features not yet justified by the spec,
- introduce out-of-scope physics,
- add GUI features,
- add optimization workflows,
- add 3D CFD behavior,
- add droplet collision/coalescence,
- add wall-film physics,
- add external free-jet or impingement models,
- add non-equilibrium condensation,
- add high-fidelity turbulence modeling,
- add large abstractions that are not needed by the current approved task.

Do not perform broad refactors unless required by the current task or necessary to preserve architecture boundaries.

Do not mix planning documents and implementation changes in the same step unless explicitly requested.

---

## 5. Scope Guardrails for the MVP

The MVP is limited to:

- steady quasi-1D internal compressible flow,
- user-provided area distribution $A(x)$,
- working fluid support for air and steam at the abstraction level,
- clean future IF97-ready steam support,
- representative droplet transport,
- slip-velocity-based droplet acceleration,
- simple Weber-threshold breakup,
- YAML input,
- CLI execution,
- CSV and JSON outputs,
- Matplotlib plotting.

Maintain focus on quasi-1D internal flow plus droplet transport plus simple breakup.

---

## 6. Architectural Boundaries That Must Be Preserved

Keep the codebase modular and aligned with [docs/architecture.md](../docs/architecture.md).

Maintain clear separation between:

- config
- domain models
- thermo
- geometry
- grid
- gas solver
- droplet solver
- breakup model
- IO
- plotting
- validation
- CLI
- application orchestration

### Required boundary rules

- Config code must not contain solver logic.
- Solver code must not parse raw YAML.
- Plotting code must remain separate from physics and solver code.
- IO code must serialize results only and must not recompute physics.
- Validation code must remain separate from production solver logic.
- CLI code must remain thin and orchestration-focused.

---

## 7. Thermodynamic Model Rules

Thermodynamic behavior must stay behind a clean abstraction.

Always:

- depend on thermo interfaces from solver code,
- keep air and steam implementations separate from the gas solver core,
- preserve clean swappability for future IF97-based steam support,
- keep backend selection configuration-driven,
- surface invalid thermo states explicitly.

Do not:

- hard-code steam-specific logic directly into unrelated modules,
- couple the gas solver directly to one concrete property backend,
- bypass the thermo abstraction for convenience.

If adding steam support, keep it compatible with the equilibrium-steam MVP assumption unless the spec changes.

---

## 8. Breakup Model Rules

Breakup behavior must remain pluggable.

Always:

- keep breakup logic behind a breakup-model interface or equivalent abstraction,
- make breakup model selection configuration-driven,
- keep Weber number calculation and breakup decision logic explicit and testable,
- return structured breakup decisions or equivalent data rather than hidden side effects.

Do not:

- hard-wire breakup logic across multiple unrelated modules,
- embed future advanced breakup models prematurely,
- mix breakup visualization with breakup physics.

The MVP breakup behavior is a simple Weber-threshold model only.

---

## 9. Units, Data, and Numerical Safety

Use SI units throughout the repository.

Always:

- assume SI units unless explicitly documented otherwise,
- validate physical inputs,
- reject nonphysical states such as negative pressure, negative temperature, negative density, or negative diameter where invalid,
- prefer numerically robust and readable formulations over clever but fragile ones,
- make assumptions explicit in code comments or docstrings where needed.

Do not introduce mixed-unit behavior.

If a unit assumption is unclear, resolve it in favor of explicit SI handling and document the assumption.

---

## 10. Coding Style Expectations

Prefer:

- readability over cleverness,
- maintainability over short-term convenience,
- explicit data flow over hidden mutation,
- small focused functions,
- type hints on non-trivial public functions and data models,
- docstrings for non-obvious logic,
- validation close to boundaries,
- descriptive naming consistent with the domain.

Avoid:

- large monolithic modules,
- multipurpose classes with mixed responsibilities,
- implicit global state,
- hidden side effects across layers,
- premature micro-optimization.

When implementing domain logic, keep code understandable to an engineering user who may need to audit assumptions.

---

## 11. Testing Requirements

Non-trivial logic must have tests.

At minimum, add or update tests when changing:

- config validation,
- geometry interpolation,
- grid generation,
- thermo provider behavior,
- gas solver logic,
- droplet transport logic,
- Weber number evaluation,
- breakup decisions,
- output formatting or serialization.

Prefer:

- unit tests for isolated logic,
- contract tests for swappable interfaces,
- integration tests for YAML-to-result workflows,
- regression tests for stable reference behaviors.

Do not add significant non-trivial logic without corresponding tests or a clearly documented reason.

---

## 12. Incremental Change Rules

When implementing a task:

- keep the diff small,
- change only the modules relevant to the current task,
- preserve existing public interfaces unless the task explicitly requires change,
- avoid opportunistic cleanup unrelated to the task,
- leave clear extension points only where the architecture already calls for them.

If a change reveals a missing prerequisite:

- implement the prerequisite first if it is still small and task-aligned, or
- update planning documents instead of forcing a large workaround.

---

## 13. Documentation Behavior

When making meaningful implementation changes, keep documentation aligned with the code.

If implementation reveals ambiguity:

- do not silently invent behavior,
- add or preserve an explicit assumptions note,
- prefer updating documentation before widening scope.

If a request conflicts with the current spec or architecture, say so and propose the smallest compliant next step.

---

## 14. Preferred Implementation Order

Use the phase order in [docs/tasks.md](../docs/tasks.md):

1. project bootstrap
2. config and domain models
3. geometry and grid
4. thermodynamic abstraction
5. quasi-1D gas solver
6. droplet transport solver
7. breakup model
8. outputs and plotting
9. tests
10. examples and documentation

Do not skip foundational phases to implement downstream features prematurely.

---

## 15. Behavior for GitHub Copilot

When assisting in this repository, GitHub Copilot should:

- check the current request against [docs/spec.md](../docs/spec.md), [docs/architecture.md](../docs/architecture.md), and [docs/tasks.md](../docs/tasks.md),
- keep responses and edits aligned to the current approved phase/task,
- prefer small incremental implementations,
- prefer modular, typed, validated Python,
- keep plotting, IO, and validation separate from solver physics,
- preserve the thermo abstraction,
- preserve pluggable breakup boundaries,
- keep SI units throughout,
- add tests for meaningful logic,
- avoid speculative or large-scale code generation.

If unsure, choose the smallest change that preserves the architecture and advances the current approved task.

---

## Utility scripts

This repository includes lightweight helper scripts that may be useful to run after completing small, reviewable tasks.

- `scripts/commit_after_task.sh` — POSIX shell script that stages all changes and runs `git commit -m "<message>"`. Usage:

```bash
./scripts/commit_after_task.sh "Short commit message describing the task"
```

- `scripts/commit_after_task.bat` — Windows batch variant. Usage:

```bat
scripts\commit_after_task.bat "Short commit message describing the task"
```

Both scripts default to the message "Automated commit after task completion" when no message argument is supplied.

Note: these helpers simply run `git add -A` followed by `git commit -m`. Use them for small, self-contained commits only — prefer PRs and feature branches for larger changes.
