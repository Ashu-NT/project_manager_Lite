# Project Management — Data-Integrity & UI/Backend Consistency Audit

**Date:** 2026-05-31
**Scope:** Project Management module only (`src/core/modules/project_management/**`, `src/ui_qml/modules/project_management/**`).
**Method:** Layer-by-layer read of ORM, repositories, application/command handlers, controllers/presenters, and QML dialogs, followed by **direct source verification** of every high-severity finding.
**Companion:** `PM_DATA_INTEGRITY_FOLLOWUP.md` (phased plan + migration DDL).

> **Headline:** The PM backend already enforces the core project-scoping invariants — cross-project dependencies, cross-project resource assignment, and cost↔task project mismatch are all blocked at the application layer **and covered by existing tests**. The genuine gaps are **defense-in-depth** (missing DB unique constraints; repo delete/get-by-id not re-scoped) and the **absence of a bad-data detector**. This audit adds a read-only health-check + tests now; schema constraints are staged behind a data-cleanup step.

---

## 0. Verification note

An initial multi-agent sweep produced a large list of "HIGH" risks. Direct source reading **disproved several** of them. This report records only **verified** facts, with file:line evidence. Disproven claims are listed in §A so they are not re-investigated.

---

## 1. PM data-model relationships (verified)

```
Project  (projects.id, String PK)                      ← root scope
 ├─ Task (tasks.project_id → projects.id, NOT NULL, CASCADE)        [idx_tasks_project_id]
 │   ├─ TaskAssignment (task_assignments.task_id → tasks.id, CASCADE)
 │   │      .resource_id → resources.id (CASCADE)
 │   │      .project_resource_id → project_resources.id (nullable, CASCADE)
 │   ├─ TaskDependency (predecessor_task_id, successor_task_id → tasks.id, CASCADE)
 │   ├─ CostItem.task_id → tasks.id (nullable, SET NULL)
 │   └─ BaselineTask.task_id  (String snapshot — NO FK by design)
 ├─ ProjectResource (project_resources: project_id, resource_id → CASCADE)
 │      UNIQUE ux_project_resource_project_resource(project_id, resource_id)   ✓ exists
 ├─ CostItem (cost_items.project_id → projects.id, NOT NULL, CASCADE)          [idx_costs_project]
 ├─ RegisterEntry (register_entries.project_id → projects.id, NOT NULL)        [idx_register_entries_project]
 ├─ ProjectBaseline (project_baselines.project_id → projects.id, CASCADE)      [idx_baseline_project, idx_baseline_project_status]
 │   ├─ BaselineTask (baseline_id → project_baselines.id, CASCADE)
 │   └─ BaselineVarianceRecord (project_id: String — NOT a FK)
 └─ PortfolioProjectDependency (predecessor/successor_project_id → projects.id)
        UNIQUE ux_portfolio_project_dependencies_pair                          ✓ exists

Resource (resources.id, String PK)  — GLOBAL pool, many-to-many with Project via project_resources.
Time entries — owned by the platform time module (src/core/platform/time/**, work-allocation based),
               NOT a PM-local ORM table. Out of PM-module scope; see §9.
```

PK/type consistency: all PKs/FKs are `String` — **no type mismatches**. SQLite FK enforcement is on in tests.

---

## 2. Risky queries / missing filters

| # | File:line | Method | Finding | Verified severity |
|---|---|---|---|---|
| 2.1 | repositories/task.py (`delete`, dep `delete`) | delete by id only | No `project_id` in WHERE | **Defense-in-depth** — app layer calls `require_project_permission` + resolves the row's project first (e.g. `dependency.py:62-68`, `assignment.py:195`). Not exploitable through the service API. |
| 2.2 | repositories/cost_calendar.py / baseline.py | `get`/`delete` by id only | Same as 2.1 | Defense-in-depth |
| 2.3 | repositories/project.py `list_all`, resource.py `list_all` | returns global pool | **By design** — workspace selectors; user chooses a project, data is then scoped. Not a leak. |
| 2.4 | repositories/cost_calendar.py `CalendarEventRepository.list_range` | possibly unscoped | **To confirm** in follow-up (scoped variants `list_for_project` exist alongside). |
| 2.5 | all repositories | — | **No raw/string-interpolated SQL anywhere** — every query is parameterized SQLAlchemy. ✓ |

There is **no verified path** by which the service API returns or writes another project's records. The repo-level gaps are real but mitigated; they are listed for defense-in-depth hardening in the follow-up.

---

## 3. QML dialogs / dropdowns — option scoping

| Dialog / option | Claimed | **Verified** |
|---|---|---|
| TaskDependencyEditorDialog → predecessor/successor list | "global leak" | **FALSE.** Built from `_load_tasks_for_project(selected_task.project_id)` → `list_tasks(project_id)` (tasks_workspace_presenter.py:362, 810-814). Project-scoped. |
| CostItemEditorDialog → task list | "unvalidated" | Scoped to selected project (`list_tasks(resolved_project_id)`); backend re-checks `cost.task.project_id == project_id` (cost_support.py:71). |
| TaskAssignmentEditorDialog → resource list | "global pool" | Scoped via `list_project_resources(project_id)`; backend re-checks `project_resource.project_id == task.project_id` (assignment.py:201). |
| Workspace `projectOptions` (tasks/financials/scheduling/timesheets) | "leak" | **By design** — top-level project selector. |

**Genuine (minor) UI gaps:** `TaskAssignmentHoursDialog` and `ProjectStatusDialog` lack in-dialog required-field validation / `InlineMessage`. Backend still validates, so this is UX polish, not an integrity hole. (Follow-up, low priority.)

Stale-state handling in the Tasks controller is **correct**: selecting a project clears `selectedTaskId/assignment/timeperiod/timeEntry` and resets lazy sections (`tasks_workspace_controller.py:567-577`); selecting a task resets assignment/time/dependency selection.

---

## 4. Backend validations — present vs. added

**Already present AND tested** (verified in source + `test_business_rules_and_edge_cases.py`):

| Rule | Where | Error code |
|---|---|---|
| Cross-project dependency blocked | dependency_diagnostics.py:113 (via `add_dependency`) | `DEPENDENCY_CROSS_PROJECT` |
| Duplicate dependency blocked | diagnostics | `DEPENDENCY_DUPLICATE` |
| Self dependency blocked | diagnostics / `_validate_not_self_dependency` | — |
| Dependency cycle detection | DFS diagnostics + Kahn topo-sort in scheduling engine | `DEPENDENCY_CYCLE` |
| Allocation range (0 < x ≤ 100) | assignment.py:189 | `ValidationError` |
| Resource overallocation (date-aware) | `TaskValidationMixin._check_resource_overallocation` | — |
| project_resource ↔ task project match | assignment.py:201 | `PROJECT_RESOURCE_MISMATCH` |
| Inactive project_resource blocked | assignment.py:207 | `PROJECT_RESOURCE_INACTIVE` |
| Cost ↔ task project match | cost_support.py:71 | — |
| Cost requires existing project | cost_lifecycle.py:34 (`_require_project`) | — |
| RBAC on create/update/delete (project, task, cost, dependency, baseline, register) | `require_permission` + `require_project_permission` throughout `application/**` | — |

**Added this turn:** a read-only **PM data-integrity health-check** (`infrastructure/persistence/health/integrity_checks.py`) that detects *legacy* rows violating the above invariants (data created before the guards existed, or via direct DB edits).

**Recommended (follow-up, not yet applied):** an explicit duplicate-assignment guard `(task_id, resource_id)` in `assign_project_resource` to match the dependency-duplicate behavior, backed by a DB unique constraint.

---

## 5. Repository constraints / filters

**Verified existing:** `ux_project_resource_project_resource`, `ux_portfolio_project_dependencies_pair`, `idx_baseline_project_status`, plus FK indexes on all `project_id` columns.

**Verified MISSING (empirically — the health-check tests insert these rows with no DB error):**

| Table | Constraint to add | Why |
|---|---|---|
| `task_dependencies` | UNIQUE(`predecessor_task_id`, `successor_task_id`) | App blocks dupes; DB has no guard. |
| `task_assignments` | UNIQUE(`task_id`, `resource_id`) | App does **not** block a duplicate (task,resource) assignment. |

These are **staged behind data cleanup** (see follow-up) — adding them to a DB with existing duplicates would fail the migration.

No repository query was modified this turn (the scoped query methods already exist and are used by the services).

---

## 6. Controller / presenter changes

**None required.** Verified that option lists are project/task-scoped and that stale selections are cleared on project/task change with the correct change signals. The agent-reported "leaks" were disproven (§3, §A).

---

## 7. Tests added

`src/tests/project_management/test_data_integrity.py` — **13 tests**, all passing:
- clean single project & fully-valid same-project graph report `ok`
- detect: cross-project dependency, self dependency, duplicate dependency
- detect: assignment resource-not-in-project, project_resource mismatch, duplicate assignment, resource overallocation
- detect: cost linked to another project's task
- detect: baseline task whose live task is in another project; and that a snapshot of a *deleted* task is **not** falsely flagged
- report rendering

These also **empirically prove** the missing DB unique constraints (§5) by inserting duplicate rows successfully.

> Cross-project *service* guarantees are already covered by the existing `test_business_rules_and_edge_cases.py`; no duplication added.

---

## 8. Files changed

**New (additive only — no existing source modified):**
- `src/core/modules/project_management/infrastructure/persistence/health/__init__.py`
- `src/core/modules/project_management/infrastructure/persistence/health/integrity_checks.py`
- `tools/pm_data_integrity_check.py` (CLI runner; exits non-zero on ERROR findings)
- `src/tests/project_management/test_data_integrity.py`
- `docs/PM_DATA_INTEGRITY_AUDIT.md`, `docs/PM_DATA_INTEGRITY_FOLLOWUP.md`

---

## 9. Remaining risks / migrations needed

1. **Run the health-check on the real DB** (`python -m tools.pm_data_integrity_check`); clean any findings. **Then** apply the unique-constraint migration (DDL in follow-up). Do not auto-delete.
2. `task_assignments` duplicate guard in `assign_project_resource` (app) + UNIQUE constraint (DB).
3. `task_dependencies` UNIQUE(predecessor, successor) constraint (DB).
4. `BaselineVarianceRecordORM.project_id` is a plain String, not a FK — low risk (variance snapshot table); convert when convenient.
5. Confirm `CalendarEventRepository.list_range` is project-scoped at its call sites.
6. **Time-entry integrity** is owned by the platform time module (`src/core/platform/time/**`), not PM. If timesheet/period integrity is in scope, audit that module separately.
7. Optional UI polish: required-field validation + `InlineMessage` in `TaskAssignmentHoursDialog` and `ProjectStatusDialog`.

---

## Appendix A — Disproven agent claims (do not re-investigate)

- ❌ "Cross-project dependencies can be created" — blocked at `dependency_diagnostics.py:113`.
- ❌ "Resource from another project can be assigned" — blocked at `assignment.py:201`.
- ❌ "Cost can link a task from another project" — blocked at `cost_support.py:71`.
- ❌ "Dependency/cost/task/register create has no RBAC" — all gated via `require_permission`/`require_project_permission`.
- ❌ "dependencyTaskOptions / cost task options leak global tasks" — scoped via `list_tasks(project_id)`.
- ❌ "TimeEntry ORM is missing" — time tracking is a platform module concern, not a missing PM table.
- ❌ "Missing idx on baseline (project_id,status)" — `idx_baseline_project_status` exists.

## Appendix B — Validation commands

- `python -m pytest src/tests/project_management/test_data_integrity.py -q` → **13 passed**.
- `python -m tools.pm_data_integrity_check` → prints report; exit 1 if any ERROR finding (CI/pre-migration gate).
- Search for raw SQL: none found in PM repositories (all parameterized SQLAlchemy).
