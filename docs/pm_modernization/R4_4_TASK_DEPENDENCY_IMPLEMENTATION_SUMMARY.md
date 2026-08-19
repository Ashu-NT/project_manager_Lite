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

## 17. Task Detail — Schedule Impact

A follow-up pass (PRE-R4.4 — TASK DETAIL SCHEDULE IMPACT SECTION ENTERPRISE
WIRING + UX COMPLETION) completed the standalone Task Detail → Schedule
Impact section, which the dependency-foundation pass above had left
untouched. Concepts A (dependency change preview, in the Dependencies
dialogs), B (this section, task-level schedule analysis), and C (whole-
project leveling/planning, future R4.4 Planning) remain deliberately
separate — this pass only builds B.

### Why it was previously empty

Traced end-to-end before any code changed: the wiring was live, not dead
— `TasksDetailPanel.qml`'s lazy loader called
`ProjectManagementTasksWorkspaceController.loadSelectedTaskScheduleImpact`
→ `tasks_workspace_presenter.py` → the old `schedule_impact_builder.py`
→ `ProjectManagementTasksDesktopApi.get_schedule_impact` →
`ScheduleChangeImpactService.analyse_delay(..., delay_days=1)`. The
defect was that `get_schedule_impact` **always** simulated a hardcoded
1-*calendar*-day slip and returned nothing else — no current-position
facts, no criticality/float, no drivers, no conflicts, no downstream
exposure, no milestone awareness, and no way for the user to choose a
delay amount. The QML rendered whatever that single hardcoded probe
produced, which for most tasks is not useful — hence "displays no useful
data" without the wiring itself being broken.

### Final backend source and relationship to `ScheduleChangeImpactService`/`run_cpm`

No second CPM implementation was introduced. `ScheduleChangeImpactService`
gained two capabilities, both orchestration over the existing canonical
`run_cpm`, `ConstraintValidator`, and `find_dependency_actual_variances`:

- `get_task_schedule_overview(project_id, task_id)` — ONE `run_cpm` pass
  (current, committed state; no hypothetical change) plus new pure
  orchestration helpers in
  `application/scheduling/forecasting/task_schedule_overview.py`
  (`compute_free_float_days`, `compute_downstream_exposure`,
  `build_schedule_drivers`) that read the CPM result rather than
  recomputing anything.
- `analyse_working_day_delay(...)` — a thin wrapper over the existing,
  general-purpose `analyse(project_id, changed_task_id, proposed_start=...)`
  that computes `proposed_start` via the same `shift_working_days`
  primitive every other working-day calculation in this codebase uses
  (unlike the pre-existing `analyse_delay`, which added raw calendar
  days via `timedelta` — kept unchanged for its own existing caller, the
  Scheduling workspace's separate, already-live "Change Impact" panel;
  see below).
- `analyse()`'s report gained `is_milestone` per affected row,
  `critical_path_changed`, and `dependency_conflicts` (reusing
  `ConstraintValidator` against the proposed schedule) — additive,
  default-valued fields, so the Scheduling workspace's existing consumer
  is unaffected.
- Bug fix, found while wiring this: `analyse()` mutated a proposed
  task's `start_date` and `end_date` as two sequential attribute writes;
  `Task`'s validated-assignment enforces `end >= start` on every
  individual write, so proposing a start date past the task's *current*
  end (the common case for "delay by N days") could raise
  `ValidationError` even though the two-field combination was valid.
  Fixed as one atomic `dataclasses.replace()`, with the new end computed
  via the same start+duration→finish formula `compute_duration_dates`
  uses. This also benefits the Scheduling workspace's panel, which calls
  the same `analyse()`.

**A confirmed separate, already-live, untouched feature:** the Scheduling
workspace has its own "Change Impact" panel
(`SchedulingDetailPanel.qml`/`SchedulingWorkspacePage.qml` →
`scheduling_calculation_actions.py` → `schedule_impact_controller.py` →
`ProjectManagementSchedulingDesktopApi.analyse_change_impact` →
`build_change_impact` → `ScheduleChangeImpactService.analyse()`), general
-purpose and user-driven (explicit proposed start/finish/duration). This
pass does not touch `change_impact_builder.py`,
`change_impact_serializer.py`'s `serialize_change_impact`,
`SchedulingChangeImpactDto`, or `schedule_impact_controller.py` — a
different, correct concept (whole-project "what if" from Scheduling, not
Task Detail's task-level analysis), left exactly as it was.

### Current schedule facts (always visible, no simulation required)

`TaskScheduleImpactOverviewDesktopDto` (new,
`api/desktop/scheduling/models/change_impact.py`) carries: current
start/finish labels, criticality, total float, free float, baseline
finish + schedule variance (only populated when a genuinely approved
baseline has a snapshot for this exact task — see below), schedule
drivers, dependency/constraint conflicts, actual-vs-dependency variances,
and downstream exposure (direct successor count, transitive downstream
task count, downstream milestone count, critical-downstream count).
Auto-loaded on task selection via
`load_selected_task_schedule_impact`/`get_task_schedule_overview` — cheap
(one CPM pass over already-loaded project data), safe to run
automatically (§26).

**Free float** is only reported when every direct successor edge is
Finish-to-Start (the only case where "successor's earliest start minus my
earliest finish" is unambiguous); a task with any SS/FF/SF successor
reports free float as unavailable rather than showing a value that could
be wrong for that relationship type — no invented values.

**Milestone** uses the exact same predicate the CPM engine itself uses to
branch into milestone-vs-duration math (`duration_days <= 0`), not a
separately invented definition.

**Baseline comparison** required one new, minimal, read-only method —
`BaselineService.get_baseline_task(baseline_id, task_id)` — exposing the
repository's already-existing `list_tasks(baseline_id)` (previously
unexposed through the service layer). This is a passthrough read, not new
baseline management capability; baseline creation/approval/lifecycle are
unchanged.

**Schedule drivers** deliberately list every incoming dependency (not
just whichever one is currently binding, which the forward pass does not
expose per-edge) plus any hard constraint and any recorded actual
start/finish — explanatory summary only, not a duplicate of the
Dependencies section.

### What-if preview (explicit only, never automatic)

`preview_task_schedule_impact(task_id, project_id, delay_working_days)`
on the desktop API and `previewTaskScheduleImpact(delayWorkingDays)` on
the QML controller are called **only** when the user clicks "Preview
Impact" with a chosen working-day delay — `loadSelectedTaskScheduleImpact`
never triggers it. This is a genuine two-CPM-pass simulation (original vs
proposed) and is never persisted; the section's own copy states this
explicitly ("This preview does not modify the project schedule.").
Affected-task rows carry current/projected dates, shift, criticality, and
milestone flag; the result summary surfaces affected/milestone counts,
largest shift, critical-path-changed, and conflict count — all backend
facts, none computed in QML.

**Not implemented, deliberately:** per-row "impact path" trace (A → B →
C) — `TaskImpact`/`ScheduleChangeImpactReport` carry no path-trace field
today, and none was fabricated; the affected-task inspector omits an
Impact Path row rather than inventing one. If a future pass adds path
tracing to the backend, the QML has a natural place for it (§16 of the
directive explicitly permits surfacing it "where backend impact facts
contain trace/path information").

### Dependencies-section boundary / Planning boundary

No dependency CRUD (add/edit/remove) exists inside Schedule Impact —
that remains exclusively Task Detail → Dependencies. No whole-project
leveling, bulk rescheduling, calendar administration, baseline
management, or constraint editing was added — those remain out of scope
for R4.4 Planning/Scheduling.

### Lazy loading and performance

Current-state facts load automatically on task selection (cheap: one
`run_cpm` pass over already-loaded project data, no per-task repository
calls — `get_task_schedule_overview` loads tasks/dependencies once via
the same `list_by_project` calls `analyse()` already used). The
downstream-exposure traversal is an in-memory BFS over the same
already-loaded dependency edges — no additional queries. The explicit
"Preview Impact" simulation (two CPM passes) runs only on user action,
never automatically, consistent with §26's "prefer explicit Preview
Impact for expensive simulation."

### Tests

19 new tests: 7 in `test_task_schedule_overview.py` (free
float/downstream-exposure/drivers orchestration), 13 in
`test_schedule_change_impact_extensions.py` (overview facts, working-day
delay, extended `analyse()` fields, baseline comparison,
`get_baseline_task`), 6 in `test_task_schedule_impact_desktop_api.py`
(desktop API surface), and 7 in
`test_qml_tasks_schedule_impact_section_contract.py` (QML runtime-load:
no blank default, current facts render without simulation, preview
button emits the chosen delay, task-switch clears delay/selection state,
no schedule math in QML source). One pre-existing characterization test
(`test_pm_desktop_adapter_da0_characterization.py`) was updated for the
renamed desktop API method, not for new behavior.

### Known, disclosed gaps

- Literal pixel verification at 1024×640/1280×720/etc. was not performed
  (same disclosed limitation as the Dependencies redesign — this
  environment cannot render a windowed Qt app). The layout reuses the
  same `GridLayout`/`Layout.fillWidth`/`InspectorPanel` primitives already
  validated at these breakpoints elsewhere.
- Critical-path *change* is surfaced as a boolean fact ("Critical path
  changed"), not a before/after path listing — no backend fact for the
  latter exists, and none was invented (§18's own fallback: "'Critical
  path changed' is sufficient").

### Post-hoc bugfixes from live-app testing

Four defects surfaced by live use of the above, all fixed and covered by
`test_task_schedule_impact_bugfixes.py`:

- A summary/parent task showing its own `start_date` still reported the
  generic "needs a computed start date" message — indistinguishable from
  a genuinely date-less leaf task. `select_leaf_tasks` correctly excludes
  summary tasks from CPM regardless of their own dates; the UI just had
  no way to say so. Fixed via `TaskScheduleOverview.unavailable_reason`
  (`summary_task` / `not_found` / `no_computed_date` /
  `service_not_configured` / `error`), threaded through the DTO and
  surfaced as a distinct QML message per reason.
- Adding/editing/removing a dependency didn't refresh the Dependencies
  table or Schedule Impact facts for the selected task until the user
  left and re-entered Task Detail. The generic `facade_refresh` shared by
  every subcontroller only rebuilds the task list, never per-section
  detail state — and QML's `LazySectionLoader.active` only (re-)loads on
  a false→true transition, not on every property change. Fixed via
  `refresh_after_dependency_mutation()`, a dependency-specific
  `facade_refresh` that forces an immediate, targeted reload of
  Dependencies + Schedule Impact + the task-list row.
- Every task showed the generic unavailable message regardless of its
  actual dates, and no backend log line ever fired to explain why. Root
  cause: the Tasks workspace's project_id is a project **filter**
  ("All Projects" leaves it blank), not the selected task's own project —
  `schedule_impact_builder.py` bailed to the empty state whenever that
  filter was blank, before the backend call ever ran. Fixed by resolving
  the task's real `project_id` via `desktop_api.get_task()` when the
  filter is blank, mirroring `task_lookup.py`'s `resolve_selected_task`
  fallback already used by Dependencies.
- "Preview Impact" worked for a 1 working-day delay but silently showed
  nothing for larger delays. Root cause: the task has a hard `deadline`
  field (distinct from `end_date`); a delay pushing the proposed start
  past it raised `ValidationError` deep inside `analyse()`'s
  `dataclasses.replace()` — silently swallowed by a bare
  `except Exception`. Fixed by detecting the conflict before `replace()`
  and returning `ScheduleChangeImpactReport.blocked_by_deadline` /
  `blocked_reason` instead of crashing; the preview panel now shows a
  danger-toned message explaining the conflict. The two remaining bare
  `except Exception` blocks in this call chain now log at `warning`/
  `exception` level instead of swallowing silently; the routine
  diagnostic breadcrumbs added alongside them log at `debug`.

## 18. Milestones

A task's milestone status was previously implicit and inconsistent:
`run_cpm`/`task_date_math.py` treat any task with `duration_days <= 0`
as a milestone for date-math purposes (EFT == EST), while
`dashboard/widgets/professional.py`'s `_is_explicit_milestone` separately
guessed from `duration_days == 0` OR a `"milestone"`/`"gate"` substring
in the task name. There was no dedicated concept a user could set, view,
or filter on directly, and the two guesses could disagree with each
other and with user intent.

### Domain model

`Task.is_milestone: bool = False` (`domain/tasks/task.py`) is now the
single source of truth. A model validator normalizes `duration_days` to
`0` whenever `is_milestone` is true — milestones are zero-duration by
definition, the same convention every consumer already used, so callers
never need to remember to zero the duration themselves. This does *not*
touch CPM's own `duration_days <= 0` date-math branches
(`task_date_math.py`, `passes.py`, `date_compute.py`,
`resource_leveling_engine.py`/`leveling_mixin.py`) — those are pure
arithmetic ("zero-or-negative duration means EFT=EST"), not a milestone
classification, and R4.4's leveling boundary (§16) means the leveling
files were not touched at all.

Persisted via `TaskORM.is_milestone` (`Boolean`, default `False`) and
migration `x4y5z6a7b8c9_add_task_is_milestone.py`, which backfills
`is_milestone = true` for existing rows with `duration_days = 0` —
already-recognized milestones (per CPM's own convention) keep displaying
as one after the migration, with no manual re-tagging. The unreliable
name-sniffing heuristic is deliberately not used for backfill.

### Repointed consumers

`task_schedule_overview.py`'s `_is_milestone()` (drives Schedule
Impact's downstream-milestone-count) and
`schedule_change_impact_service.py`'s `TaskImpact.is_milestone` (drives
the Preview Impact rows' milestone flag) now read `task.is_milestone`
directly instead of guessing from `duration_days`.
`dashboard/widgets/professional.py`'s `_is_explicit_milestone` now reads
`task.is_milestone` only — the name-sniff is dropped, since the real
flag makes it both unnecessary and a source of false positives.

### Application / desktop API / QML threading

`TaskLifecycleMixin.create_task`/`update_task` accept `is_milestone`
(create: `bool = False`; update: `bool | None = None`, meaning "leave
unchanged") and keep `end_date` consistent with whatever `duration_days`
the domain settles on — computed from the *post-normalization* value,
not the raw caller-supplied one, so a milestone's `end_date` always
equals its `start_date`. `TaskCreateCommand`/`TaskUpdateCommand`,
`TaskDesktopDto`, and `task_serializer.py` all carry `is_milestone`
through to the QML layer.

`TaskEditorDialog.qml` gained a "This is a milestone (zero-duration)"
checkbox (`milestoneCheck`): checking it disables and zeroes the
Duration field client-side (the domain normalizes it regardless, but the
UI shouldn't show a stale non-zero value); the payload's `durationDays`
is forced to `"0"` when checked.

### Task list badge and filter

The Tasks workspace list is a generic column-driven `DataTable` (plain
text cells via `TasksColumnConfig.js`, not per-cell rich rendering), so
the lowest-risk way to surface milestone status in the list is a small
glyph prefix on the title (`◆ `) in `task_mapper.py`'s
`to_task_record_view_model` — consistent with how hierarchy indentation
is already done there, and visible without any `DataTable.qml` changes.

A server-side "Milestones only" filter was added end-to-end (query-time,
like the existing status/priority/schedule filters, not a client-side
filter over one already-fetched page — tasks are paginated server-side,
so a page-local filter would silently miss milestones on other pages):
`TaskWorkspaceCriteria.milestones_only` →
`SqlAlchemyTaskWorkspaceReader._filtered_conditions` (a plain
`is_milestone.is_(True)` predicate) → `TaskQueryMixin.query_workspace_page`
→ `ProjectManagementTasksDesktopApi.list_task_page` →
`TasksWorkspaceState`/`ProjectManagementTasksWorkspaceController`
(`milestonesOnlyFilter` property, `setMilestonesOnlyFilter` slot,
`task_filter_actions.set_milestones_only_filter`, folded into
`clearFilters`) → a "Milestones only" checkbox in `TasksFilterPopup.qml`.
Also threaded into `list_export_records`/`export_tasks` so an export
taken while the filter is active matches what's on screen, consistent
with the existing search/status/priority/schedule export-consistency
guarantee.

### Tests

Domain: `test_task_domain_validation.py` (default false, duration
normalization, truthy coercion). Migration:
`test_task_is_milestone_migration.py` (backfill from zero duration,
clean downgrade — run against a real Alembic upgrade/downgrade chain,
not just the ORM). Application: `test_project_management_desktop_api_tasks_crud.py`
(create/update threading end-to-end through the desktop API, including
duration normalization). Query/filter: `test_workspace_database_pagination.py`
(milestones-only filter against the real SQL reader). List badge:
`test_tasks_serializer.py` (title marker + filter, through the real
desktop API and serializer). Dialog:
`test_qml_project_management_dialogs.py` (checkbox zeroes duration on
check, populates correctly from an existing milestone task) — QML
runtime-load tests via the same `create_qml_engine()`/`QMetaObject.invokeMethod`
harness used throughout R4.4.

### Known, disclosed gaps

- No dedicated "Milestones" view/report (e.g. a project-wide milestone
  timeline) was built — only list-level badge/filter, per the requested
  scope. A milestone-focused view would be a separate, larger feature.
- `TasksFilterPopup.qml`'s new checkbox was not given its own QML
  runtime-load test — no QML test of any kind exists for this popup
  (every one of its existing filters is equally untested at that layer);
  adding one would mean building fake-controller test infrastructure for
  the whole popup as a side effect of this feature, which was judged out
  of proportion here. The checkbox itself is the same `AppControls.CheckBox`
  `checked`/`onCheckedChanged` idiom already covered by
  `TaskEditorDialog.qml`'s `milestoneCheck` test.
- `list_export_records`/export threading covers CSV/table export;
  baseline snapshots (`BaselineTask`) do not carry `is_milestone` — that
  was judged a separate enhancement outside this feature's requested
  scope (baselines snapshot schedule facts, not this flag).
