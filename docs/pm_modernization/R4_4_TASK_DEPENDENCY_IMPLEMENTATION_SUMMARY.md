# R4.4 Task Dependency — Enterprise Foundation Upgrade: Implementation Summary

This document records what the **PRE-R4.4 — TASK DEPENDENCY ENTERPRISE
FOUNDATION UPGRADE** implementation pass actually built, as the *after*
counterpart to
[`R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md`](./R4_4_TASK_DEPENDENCY_CURRENT_STATE_AND_TARGET_GAPS.md)
(the *before* audit). Read the audit first for the findings; this document
says what changed in response to each one, with file/test references so
every claim below is checkable.

This pass explicitly did **not** start R4.4 resource leveling or R5, and
did not commit any of its own work (all changes landed as uncommitted
working-tree edits, per the pass's own standing constraint).

## 1. Canonical dependency semantics

One module is now the single source of truth for dependency date math:
`src/core/modules/project_management/application/scheduling/cpm/dependency_schedule_math.py`.
Both the forward pass (`passes.py::run_forward_pass`) and the backward pass
(`passes.py::run_backward_pass`) call into it via a single shared primitive,
`shift_working_days(calendar, anchor, signed_offset)`, used with the sign
flipped for backward vs forward — so the two passes cannot independently
drift apart the way the four pre-existing duplicated implementations had.
41 unit tests in
`src/tests/project_management/dependency/test_dependency_schedule_math.py`
pin the exact per-type formulas.

## 2. Zero-lag definition for all four types

For `lag_days=0`, all four relationship types now resolve to the immediate
next/same working day per the relationship's own anchor, with no implicit
same-day or off-by-one drift between types — e.g. FS with lag 0 means the
successor may start the working day immediately after the predecessor
finishes; SS with lag 0 means same day. Table-driven cases for all four
types × lag 0 are in `test_dependency_schedule_math.py`.

## 3. Positive lag semantics

Positive lag adds working days *after* the zero-lag anchor, uniformly
across all four types via `shift_working_days`'s positive branch. Fixed a
confirmed off-by-one on SS/FF/SF (the audit's finding: these previously
used `add_working_days(anchor, lag)` where FS correctly used
`add_working_days(anchor, lag + 1)`) — see
`test_technical_math_reporting_scheduling.py::test_cpm_dependency_type_math`,
updated with an explanatory comment for the fix.

## 4. Negative lead semantics

Negative lag ("lead") now moves the dependent date *before* the zero-lag
anchor, monotonically, via the same primitive with a negative offset —
fixing the audit's finding of non-monotonic lead behavior. Covered in
`test_dependency_schedule_math.py`'s lead-specific cases and
`test_actual_date_dependency_semantics.py`.

## 5. Working-day authority

Forward and backward passes, actual-date constraint application, and
scheduling-constraint application (MSO/MFO/SNET/FNET) all resolve the
project calendar through one path —
`SchedulingEngine.calendar_for_project` / `_resolve_task_calendar` — and
the non-persisting preview path
(`dependency_diagnostics.py::_resolve_calendar_for_diagnostics`) now
resolves the *same* calendar object rather than a separate wrapper, closing
the "preview and committed schedule can silently disagree" gap the audit
found (§7/Phase E).

## 6. Authoritative scheduling implementation

`src/core/modules/project_management/application/scheduling/cpm/pure_cpm.py`
(`run_cpm`) is now the **one** non-persisting CPM entry point. It is used
by: `SchedulingEngine.recalculate_project_schedule` (via shared per-task
date-math helpers in `task_date_math.py`), the Portfolio executive read
path (previously its own drifted `CPMCalculator`), `ScheduleChangeImpactService`
(via an injectable `_run_cpm` seam for testability), and
`dependency_diagnostics.py`'s preview/impact computations. There is no
second CPM implementation left in the codebase.

## 7. Removed duplicate/dead implementations

Deleted outright:

- `application/scheduling/cpm/cpm_calculator.py` (`CPMCalculator`) — its
  one caller (Portfolio executive) migrated to `run_cpm`.
- `application/scheduling/dependencies/dependency_resolver.py`
  (`DependencyResolver`) and the now-empty `dependencies/` subpackage —
  zero production callers at any point in its history.
- Four independently-drifting dependency-type label/coercion modules
  (`tasks/utils/dependency_utils.py`, `scheduling/utils/dependency_utils.py`,
  `scheduling/formatters/dependency_formatter.py`,
  `portfolio/utils/dependency_type_utils.py`) — consolidated into one
  canonical `api/desktop/common/dependency_presentation.py`, imported by
  all three workspaces (Tasks, Scheduling, Portfolio). This also fixed the
  Dependencies table's "Lag" column, which was rendering the linked task's
  raw UUID instead of the lag value (`dependency_mapper.py`'s `meta_text`
  field) — the exact defect Phase N's directive named by title.
- `ResourceLevelingEngine`/`DependencyResolver` corrected in
  `docs/pm_modernization/README.md`'s Implementation Order / Public
  Interfaces checklist, which previously marked both ✅ as if still live;
  see that file's corrections for exact wording.

Left in place, deliberately, per the audit's own scope boundary:
`ResourceLevelingEngine` (dead code, but its fate belongs to the dedicated
R4.4 leveling decision, not this pass) and Scheduling's fully-built but
orphaned dependency-CRUD QML surface (documented as dead, not wired — see
§16 below).

## 8. Constraint/dependency conflict semantics

`ConstraintValidator` gained a `DependencyConstraintConflict` dataclass and
a `dependency_conflicts` field on `ConstraintValidationResult`, populated
by comparing each task's dependency-implied dates (captured via a new
`on_dependency_implied` callback threaded through
`compute_task_dates_common` at the correct pre-actual-constraint point)
against its scheduling-constraint-driven dates. Previously a hard
constraint could silently override a dependency's implied date with no
signal that the two disagreed; this is now a reported, non-silent fact.
See `test_constraint_dependency_conflict.py`.

## 9. Create/update/delete transaction model

`add_dependency`/`update_dependency`/`remove_dependency`
(`application/tasks/commands/dependency.py`) are each fully atomic:
repository mutation, schedule recalculation, and activity recording share
one commit (`commit=False` internally, one final commit), so a failure in
schedule recalculation can no longer leave a committed dependency edit with
a stale schedule and no audit record. The approval-apply path
(`_apply_dependency_add_decision` / `_apply_dependency_update_decision` /
`_apply_dependency_remove_decision`) always re-fetches and re-validates
against the *current* row/graph at apply time, fixing a TOCTOU hole where
a request valid at submission time could still be blindly applied after
the graph changed while it was pending. `exclude_dependency_id` was added
to `get_dependency_diagnostics` so `update_dependency` no longer has to
blindly whitelist `DEPENDENCY_DUPLICATE` against itself (which had also
made the cycle check unreachable on that path).

## 10. Governance model

All three mutations check `is_governance_required(...)` against
`DEFAULT_GOVERNED_ACTIONS` (now including `dependency.update`, added this
pass — previously only add/remove were governed, an inconsistency the
audit flagged); when governed, they call `ApprovalService.request_change`
and raise `BusinessRuleError(code="APPROVAL_REQUIRED")` rather than
applying immediately or pretending to succeed. `project_registry.py`
registers apply handlers for all three (`dependency.add/remove/update`).

## 11. Optimistic concurrency

`TaskDependency` gained a `version` column (Alembic migration
`k3i9kex13spt_add_task_dependency_version_and_self_check.py`, alongside a
`ck_task_dependencies_not_self` CHECK constraint). `SqlAlchemyDependencyRepository.update`
and `.delete` use `update_with_version_check`/`delete_with_version_check`.
**New this phase (Phase N10):** `update_dependency` previously always
re-fetched fresh and compared a version against itself — meaning it could
never actually detect a real stale write, unlike delete. It now accepts an
`expected_version` (threaded from the QML edit dialog's loaded state,
through `TaskDependencyUpdateCommand.expected_version`), raises
`ConcurrencyError(code="STALE_WRITE")` on mismatch, and threads the
request-time version into the governed-path approval payload so an
approval applied long after submission re-checks against whatever is
current *at apply time*, not the requester's now-stale view. See
`test_dependency_concurrency_and_governance.py::TestUpdateOptimisticConcurrency`
(4 tests, including a TOCTOU-style approval-apply case).

## 12. DB integrity

At-rest cycle detection (`_dependency_cycle_finding`, generalized from a
tree-only WBS check to a general graph DFS) is wired into
`integrity_checks.py`'s health-check list. Repository-level
`_ensure_same_project` defense-in-depth blocks a cross-project edge from
being persisted even if a caller bypasses the diagnostics check (the
schema itself cannot express "both endpoints in the same project" — no
`project_id` column on `task_dependencies`).

## 13. Impact preview

`dependency_diagnostics.py`'s `get_dependency_diagnostics(...,
include_impact=True)` — previously reachable only from tests, per the
audit's "~370 lines of effectively dead code" finding — is now live: three
new desktop-API methods (`preview_create_dependency`,
`preview_update_dependency`, and a new `preview_dependency_removal` /
`preview_delete_dependency` closing the DELETE gap) expose it through typed
DTOs (`TaskDependencyImpactPreviewDesktopDto`,
`TaskDependencyImpactRowDesktopDto`), which the Task Detail dialog calls
live as the user edits (Phase N9) and the delete confirmation calls before
the user confirms (Phase N11). All three reuse the exact canonical
`run_cpm` path the committed schedule uses — a preview can never disagree
with what saving would actually produce.

## 14. Task Detail UX

`TasksDependenciesSection.qml` was redesigned per the Phase N spec:
Predecessors/Successors tab split with compact counts (no more direction
hidden under a "Status" column), a 3-column table (Task / Relationship /
Lag-Lead, no UUIDs), row-select-opens-inspector (shared `InspectorPanel`
pattern, matching `TasksAssignmentsSection`) with Direction / Relationship
/ Lag-Lead / Related-task-dates / Current-task-dates /
schedule-impact-if-removed, and `[Edit Relationship] [Open Task] [Remove]`
actions. `TaskDependencyEditorDialog.qml` now serves both Create and Edit
in one dialog (matching the app's established create/edit-mode pattern),
with a relationship preview and the live schedule-impact panel described
above. Errors surface in-context via the existing shared
`EntityDialog`/`_handleResult`/`InlineMessage` machinery (already proven
correct by sibling dialogs' tests) rather than a dependency-specific
reimplementation. Task switching clears selection/tab/preview state before
the new task's rows render (`onDependenciesModelChanged`).

**Known, disclosed gap:** literal pixel-level verification at every named
breakpoint (1024×640 … 1920×1080) was not performed — this environment
cannot render a windowed Qt app for visual inspection. The layout uses the
same relative-sizing primitives (`Layout.fillWidth`, `InspectorPanel`'s
theme-driven width, `DataTable`'s `flex` columns) already used by sibling
sections that *have* been visually validated at these breakpoints, so it
inherits their responsive behavior rather than introducing new fixed-width
assumptions — but this is inherited-correctness reasoning, not a literal
visual check.

## 15. Performance evidence

- Query count: `list_dependencies_for_project` was an N+1 loop
  (`list_by_task` once per task); now one `list_by_project` call
  regardless of task count —
  `test_dependency_query_performance.py::test_list_project_dependencies_is_one_query_not_per_task_loop`.
- Changed-task persistence: `recalculate_project_schedule` previously
  wrote every leaf task unconditionally on every recalculation; now
  compares each task's pre-recalculation `(start_date, end_date)` against
  the CPM result and skips the repository write when unchanged (verified
  safe: `build_schedule_result` never mutates any other field, so this
  comparison is a complete proxy for "did this task's persistable state
  change"). Two regression tests prove 0 writes on a stable re-run and
  exactly the downstream-shifted count on a real shift.
- Large-graph characterization: an existing, broader (5000-task default)
  seed→schedule→baseline→report→dashboard SLA suite already exercises CPM
  at a scale well beyond the requested 100/1000 tasks
  (`src/tests/test_large_scale_performance.py`, opt-in via
  `PM_RUN_PERF_TESTS=1`); no separate smaller-scale duplicate was added.

## 16. Explicit R4.4 leveling boundary

See §13 ("Leveling Interaction") of the audit document, which now also
carries a "Phase P" subsection stating the invariant R4.4 must satisfy
("a subsequent canonical schedule recalculation must NOT silently erase a
valid leveling decision") and pointing at the pinned regression —
`test_leveling_dependency_boundary.py::test_auto_leveling_shift_on_a_dependency_linked_task_is_silently_reverted_by_the_next_cpm_run` —
that proves today's behavior violates it. This pass does not fix that
interaction; R4.4 must reconcile dependency minimum dates, hard
constraints, resource-capacity leveling, and actual dates through one
schedule model, not four independently-consulted ones.

## Test count

83 tests in the dedicated `src/tests/project_management/dependency/`
package (created this pass), plus QML runtime-load tests in
`test_qml_project_management_dialogs.py` and
`test_qml_tasks_dependencies_section_contract.py`, plus updates to
pre-existing suites this pass touched
(`test_technical_math_reporting_scheduling.py`,
`test_schedule_impact_da5.py`, `test_repository_tenant_hardening_priority.py`,
`test_data_integrity.py`, `test_pm_cqrs_reader_architecture.py`,
`src/tests/pm/test_constraint_validator.py`). One pre-existing, unrelated
failure was observed throughout this pass's regression runs
(`test_task_skill_requirements_version_migration.py::test_task_skill_requirements_version_migration_downgrades_cleanly`)
— a different table's migration; neither of this pass's two commits
(`6eb43a8c`, `83d373878`) touch any `task_skill_requirements`-related file,
confirmed via `git show --stat` on both.
