# R4.4 Task Scheduling Constraints — Implementation Summary

Implementation pass following the read-only audit in
`R4_4_TASK_CONSTRAINT_CURRENT_STATE_AND_TARGET_GAPS.md`. That audit is the
authoritative before-state; this document records what changed, the
product/domain decisions made along the way, and what remains
deliberately out of scope.

Standing constraints honored throughout: no R4.4 resource leveling, no
ALAP (not implemented or exposed anywhere), no full redesign of the
Scheduling workspace, no R5 work, no commits made by the assistant.

---

## 1. Final architecture

The constraint feature is now a complete vertical slice, mirroring the
shape the dependency feature already had (Task Detail → Dependencies /
Schedule Impact):

```
Task (domain)                    constraint_type: ConstraintType | None
                                  constraint_date: date | None
                                  cross-field validation (dated-constraint
                                  requires a date; DEADLINE is rejected as
                                  a Task.constraint_type value; a stray
                                  date with no type is normalized away)
        |
ORM / mapper / repository        real columns (from a pre-existing 2024
                                  migration, previously unmapped), threaded
                                  through TaskRepository.update's
                                  version-checked write dict
        |
Application layer                TaskSchedulingConstraintMixin
                                  .update_task_scheduling_constraint /
                                  ._apply_task_scheduling_constraint_decision
                                  — governed (ApprovalService, TOCTOU-safe
                                  re-validation at apply time), atomic with
                                  schedule recalculation
        |
Desktop API                      TaskConstraintUpdateCommand,
                                  list_constraint_options(),
                                  create_task(constraint_type/_date),
                                  update_task_scheduling_constraint()
        |
Presentation boundary            constraint_presentation.py — the single
                                  canonical (value, code, label,
                                  description, requires_date, category)
                                  map, consumed by Tasks, Scheduling
                                  diagnostics, and Schedule Impact
        |
QML                              TaskEditorDialog's collapsed-by-default
                                  "Advanced scheduling" section; Schedule
                                  Impact's hard-constraint conflict banner;
                                  Scheduling workspace's per-activity
                                  Constraints panel
```

Product-model decisions carried through unchanged from the audit's
Phase B framing:

- **ASAP is a UI concept, not a domain enum member.** `ConstraintType` has
  the same 7 members it always had; the picker's first entry (`value:
  ""`, `code: "ASAP"`) is `constraint_presentation.py`'s own construct,
  not a new enum value. Clearing a task's constraint sets
  `constraint_type = None`.
- **ALAP was not implemented or exposed anywhere** — not in the enum, not
  in the picker, not as a disabled placeholder.
- **Deadline stays a separate concept from FINISH_NO_LATER_THAN.** Task
  Editor's "Deadline" field and the constraint picker are two different
  controls; the Scheduling workspace's synthetic "Constraints" panel,
  which previously mislabeled Deadline as "Finish No Later Than", now
  labels it plainly "Deadline" and only shows a "Constraints" row when a
  real `Task.constraint_type` is set.
- **Canonical labels everywhere.** Every consumer that shows a constraint
  to a user (Task Editor picker, Schedule Impact conflict banner,
  Scheduling diagnostics, the Scheduling workspace's Constraints panel)
  now goes through `constraint_presentation()` — no raw snake_case, no
  independently hand-titled strings.

## 2. Domain decisions

- **`DEADLINE` is not a legal `Task.constraint_type` value.** It exists in
  `ConstraintType` only so `ConstraintValidator`/`constraint_presentation`
  can classify and render a deadline-exceeded violation; the domain
  layer's `Task` model rejects it outright if ever assigned as the
  constraint type, since `Task.deadline` is the real, separate field for
  that concept.
- **Backward-pass CPM constraint-blindness — RESOLVED in a follow-up pass.**
  The original documented STOP (kept below for history) was reversed once
  a dedicated pass characterized `run_backward_pass`'s exact behavior and
  fixed it without touching forward-pass semantics. See §10,
  "Constraint-aware backward CPM," for the full write-up.
  ~~Backward-pass CPM constraint-blindness was NOT fixed — a deliberate,
  documented STOP (see `test_backward_pass_constraint_blindness.py`).
  `run_backward_pass` is depended on by many unaudited consumers beyond
  this pass's scope; total float and criticality can still be
  meaningless for a constrained task's own float number. This is the one
  finding from the audit's numbered list that remains open by design, not
  by oversight.~~
- **Actual dates take precedence over MSO/MFO.** `apply_scheduling
  _constraints` was fixed so a locked `actual_start`/`actual_end` is never
  silently overridden by a start/finish-fixing constraint — the
  constraint's own EST/EFT is still computed, but a recorded actual wins.
- **The dependency-conflict model was extended to ceiling constraints.**
  `DependencyConstraintConflict` previously only covered MSO/MFO silently
  overriding a dependency; it now also covers SNLT/FNLT ceilings that are
  infeasible against a dependency-implied date (the dependency always
  wins in the forward pass; the conflict fact records why the plain
  `ConstraintViolation` fired).
- **Deadline governance decision**: `Task.deadline` is deliberately NOT
  part of the new governed `update_task_scheduling_constraint` command —
  it stays on the plain, ungoverned `update_task` path. Deadline never
  drives CPM (it's validation-only, same enforcement weight as FNLT), so
  it doesn't carry the same "can silently move a schedule" risk the six
  real constraint types do; folding it into the new governed command
  would also have meant either duplicating deadline's existing update
  path or migrating its behavior, neither of which this pass's scope
  called for. This intentionally leaves the audit's Backend Defect #5
  (deadline changes have no governance parity with dependency changes)
  and #6 (a deadline edit alone doesn't force a targeted Schedule
  Impact/Dependencies refresh) open — both are pre-existing gaps in
  `Task.deadline`'s own update path, not introduced or fixed by this
  constraint-type pass. See the exit-gate table below.
- **An explicit constraint date must be a real working day** under the
  project's authoritative calendar, or the mutation is rejected outright
  with the nearest working day named in the error — not silently
  snapped, since that would change the user's explicit instruction
  without telling them.

## 3. UI description

**Task Editor dialog** — a collapsed-by-default "▸ Advanced scheduling"
section (auto-expands if the task already has a constraint set) containing:
- A "Scheduling constraint" picker bound to the desktop API's
  `list_constraint_options()` (ASAP + the 6 editable types, never ALAP).
- A "Constraint date" field, shown only for constraint types that require
  one; selecting ASAP hides it and the picker toggling away from a dated
  type clears the value at submit time.
- The selected option's description shown as inline help text.
- A warning banner (amber `InlineMessage`, `tone: "warning"`) shown only
  for MUST_START_ON / MUST_FINISH_ON ("fixed_date" category), since those
  can override dependency-driven scheduling.
- Client-side validation blocks submission if a dated type has no date.

On save, a changed constraint is routed through the dedicated governed
`updateSchedulingConstraint` mutation (not the generic `updateTask`
command, which deliberately excludes constraint fields) before the rest
of the edit is applied, so an approval-required response is reported
precisely rather than silently folded into a generic save.

**Task Detail → Schedule Impact** — the hard-constraint conflict banner
now reads the humanized `constraintTypeLabel` (e.g. "Must Start On
(MSO)") instead of the raw enum value it previously rendered verbatim.

**Scheduling workspace → selected activity → Constraints panel** — no
longer fabricates a "Planned Start" row for every task with a start date
(ASAP-computed dates are not a constraint); reports a real constraint row
only when `Task.constraint_type` is actually set, titled with its
canonical label; the deadline row is titled plainly "Deadline".

**Not built in this pass**: a live schedule-effect preview inside the
Task Editor dialog as the user changes the constraint picker (deferred —
see §5). Everything else needed to set, persist, govern, and see the
effects of a real constraint is in place.

## 4. Changed files

**Domain**
- `domain/enums.py` — `ConstraintType` (moved here from the validator module)
- `domain/tasks/task.py` — typed field, normalization, cross-field validation

**Application**
- `application/scheduling/cpm/constraint_validator.py` — re-exports `ConstraintType`; `DependencyConstraintConflict` extended for SNLT/FNLT
- `application/scheduling/cpm/task_date_math.py` — actual-date precedence fix
- `application/tasks/commands/scheduling_constraint.py` (new) — `TaskSchedulingConstraintMixin`
- `application/tasks/commands/lifecycle.py` — `create_task` threads constraint params
- `application/tasks/service.py` — mixin wired into `TaskService`
- `application/scheduling/forecasting/task_schedule_overview.py` — driver now emits the raw enum value (layering fix; was rendering `str(ConstraintType.X)`)

**Infrastructure / persistence**
- `infrastructure/persistence/orm/task.py` — mapped columns
- `infrastructure/persistence/mappers/task.py` — enum↔string threading
- `infrastructure/persistence/repositories/tasks/task.py` — write dict now includes `constraint_type`, `constraint_date`, and (pre-existing bug fixed opportunistically) `is_milestone`

**Governance**
- `core/platform/domain/approval/policy.py` — `"task.constraint.update"` added to `DEFAULT_GOVERNED_ACTIONS`
- `infra/composition/project_registry.py` — apply handler registered

**Desktop API (Tasks)**
- `api/desktop/common/constraint_presentation.py` (new) — canonical presentation module
- `api/desktop/tasks/models/task.py`, `models/options.py`, `commands/task_commands.py`, `serializers/task_serializer.py`, `api.py`, `__init__.py` (+ package `__init__.py`)

**Desktop API (Scheduling)**
- `api/desktop/scheduling/models/change_impact.py` — `constraint_type_label` on `ScheduleConflictDto`
- `api/desktop/scheduling/models/schedule.py` — `constraint_type`/`constraint_type_label`/`constraint_date` added to `SchedulingTaskDto`
- `api/desktop/scheduling/serializers/change_impact_serializer.py` — conflict + driver labels re-derived at the boundary
- `api/desktop/scheduling/serializers/constraint_serializer.py` — uses `constraint_presentation()`
- `api/desktop/scheduling/serializers/schedule_serializer.py` — both schedule-item serializers thread the real constraint

**QML presenters / controllers**
- `presenters/tasks/task_mapper.py`, `task_command_handler.py`, `schedule_impact_builder.py` (conflict label fix)
- `presenters/scheduling/detail_builder.py`, `formatters.py` (Constraints panel fix)
- `controllers/tasks/tasks_workspace_presenter.py`, `tasks_workspace_controller.py`, `task_mutation_facade.py`, `pm_task_list_controller.py`, `task_subcontroller_factory.py`, `task_lazy_section_loader.py` (targeted schedule-impact refresh after a constraint mutation, mirroring the dependency-mutation refresh)

**QML**
- `qml/workspaces/tasks/dialogs/TaskEditorDialog.qml` — Advanced scheduling section
- `qml/workspaces/tasks/TasksDialogHost.qml` — routes a changed constraint through the dedicated mutation before the generic update
- `qml/workspaces/tasks/sections/TasksScheduleImpactSection.qml` — humanized conflict label

## 5. Migrations

None. The `constraint_type`/`constraint_date` columns already existed
from a prior migration (`i2j3k4l5m6n7`); the audit's central finding was
that nothing above the database read or wrote them. No new migration was
needed — this pass is entirely mapper/repository/application/API/QML
wiring on top of already-existing columns.

## 6. Tests added / counts

90 constraint-focused tests exist across the repository after this pass
(`pytest -k constraint`), spanning:

- Domain validation and normalization (`test_task_domain_validation.py`,
  `test_constraint_validator.py`)
- Persistence round-trip (`test_task_constraint_persistence.py`)
- Governance parity (`test_task_constraint_governance.py`)
- The documented backward-pass decision record
  (`test_backward_pass_constraint_blindness.py`)
- Actual-date precedence (`test_actual_start_constraint_precedence.py`)
- Ceiling-constraint/dependency conflict expansion
  (`test_ceiling_constraint_dependency_conflict.py`,
  `test_constraint_dependency_conflict.py`)
- Canonical presentation metadata and humanization
  (`test_constraint_presentation.py`, `test_constraint_humanization.py`)
- End-to-end desktop API (`test_task_constraint_desktop_api.py`)
- QML dialog behavior — ASAP default, dated-constraint validation,
  auto-expand on existing constraint
  (`test_qml_project_management_dialogs.py`)
- Schedule Impact conflict-label regression
  (`test_task_schedule_impact_bugfixes.py`)
- Scheduling workspace Constraints panel — row content, label
  precedence, and DTO threading (`test_scheduling_constraints_panel.py`)

## 7. Pre-existing unrelated failures

A full `src/tests/project_management` regression run (1044 tests,
735s) finished at **1043 passed, 1 failed**. The one failure —
`test_financial_desktop_forecast_delegation.py::
test_financial_desktop_maps_paged_canonical_commitment_lines` — asserts
a commitment-listing pagination offset/limit pair (`(0, 20)` returned vs.
`(10, 20)` expected) in the Financials desktop API. It reproduces in
complete isolation, touches no file this pass changed, and sits in an
unrelated in-progress area (Financials/`ProjectCostEntry`) — pre-existing
and unrelated to this constraint pass.

## 8. Exit gate — audit findings closed

Checked against the audit's own §36 (Backend Defects), §37 (UI/UX
Defects), and §38 (Dead/Duplicate Code) numbered findings — the most
concrete, individually-verifiable items in the audit:

| # | Finding (audit §) | Status |
|---|---|---|
| Backend 1 | `constraint_type`/`constraint_date` fully unreachable in production (§36.1) | **Fixed** — full vertical slice, §1 |
| Backend 2 | Domain field type mismatch, `None` coerced to `""` (§36.2) | **Fixed** — retyped `ConstraintType \| None`, real validator |
| Backend 3 | Backward pass fully constraint-blind (§36.3) | **Fixed** in a follow-up pass — see §10, "Constraint-aware backward CPM" |
| Backend 4 | Constraint dates never checked against the working calendar (§36.4) | **Fixed** — `_validate_constraint_date_is_working_day`, rejects with the nearest working day named |
| Backend 5 | Deadline changes have no governance parity (§36.5) | **Deliberately out of scope** — deadline decision, §2 |
| Backend 6 | Deadline edit doesn't force a targeted stale-UI refresh (§36.6) | **Still open** — pre-existing gap in `Task.deadline`'s own path, not this pass's scope. The equivalent gap for the *new* constraint mutation itself is fixed (Phase T) |
| Backend 7 | `build_schedule_drivers`'s constraint-driver branch has no enum validation guard (§36.7) | **Moot** — Task's own field validator now fails closed on an invalid `constraint_type` at construction, so a garbage value can no longer reach this branch in the first place |
| UI/UX 1 | Two same-named "Constraints" panels reading unrelated data models (§37.1) | **Data-correctness fixed** — both panels' underlying data is now accurate; the panels are in fact separately titled ("Constraints" vs. "Diagnostics") already, so the naming-collision concern as literally described did not reproduce |
| UI/UX 2 | Second "Constraints" panel mislabels Deadline as FNLT (§37.2) | **Fixed** — Phase S |
| UI/UX 3 | Terminology inconsistency, title-cased vs. raw snake_case (§37.3) | **Fixed** — single `constraint_presentation()` source of truth everywhere |
| UI/UX 4 | No user-facing surface ever shows the SNET/SNLT/MSO/MFO-style terminology (§37.4) | **Fixed** — Task Editor picker, Schedule Impact banner, Scheduling Constraints panel |
| UI/UX 5 | Task Detail has no constraint UI at all (§37.5) | **Fixed** — TaskEditorDialog's Advanced scheduling section |
| Dead code | `ResourceLevelingEngine` duplicate, zero callers (§38) | **Not touched** — out of this pass's scope (resource leveling is explicitly excluded); flagged again here for a future cleanup pass, same as the audit itself flagged it |
| Dead code | Four independent constraint-interpretation sites (§38) | **Consolidated to the extent layering allows** — `constraint_label_for_activity` now prefers the real constraint; `build_schedule_drivers` emits a raw value re-labeled at the desktop boundary (an application layer cannot import the desktop-layer presentation module) |
| Dead code | Five enum→label mapping sites, no shared source (§38) | **Fixed** — `constraint_presentation.py` is now the only place that renders a `ConstraintType` to a user-facing string |
| Dead code | DB columns orphaned at the ORM layer (§38) | **Fixed** — mapped, no new migration needed |

## 9. Unresolved / deferred items

- **Phase P (live schedule-effect preview inside the Task Editor
  dialog)** — not built. The dialog validates and saves a constraint
  correctly, and Schedule Impact reflects its effect once saved, but
  there is no in-dialog "here's what this constraint would do" preview
  as the user picks a type/date. This is a UX enhancement, not a
  correctness gap; deferred given the scope already delivered.
- ~~Backward-pass constraint-blindness (see §2) — an explicit, documented
  non-fix.~~ **Resolved — see §10.**
- Everything explicitly out of scope per the standing constraints: R4.4
  resource leveling, ALAP, a full Scheduling workspace redesign, R5.

---

## 10. Constraint-aware backward CPM

Follow-up pass (PRE-R4.4 — CONSTRAINT-AWARE BACKWARD CPM / FLOAT
CORRECTNESS) that reverses §2's original "not fixed" decision.
`run_backward_pass` (`application/scheduling/cpm/passes.py`) previously
never read `constraint_type`/`constraint_date`/`deadline` at all — LS/LF,
total float, and criticality were computed purely from the dependency
graph, so a constrained task's own float number could be actively
misleading. This section documents the fix, exactly as directive item 22
requires: final LS/LF semantics, per-constraint treatment, the Deadline
decision, negative-float/infeasible semantics, free-float semantics,
criticality semantics, actual-date handling, test evidence, and the
leveling-consumption verdict.

Standing constraints honored in this follow-up pass too: no QML changes,
no resource-leveling changes, no ALAP, no R5, no commits.

### 10.1 Final LS/LF semantics — decision table

| Constraint | Backward-pass treatment | Own float impact |
|---|---|---|
| None (ASAP) | Untouched — network-derived LS/LF exactly as before | Unchanged from pre-existing behavior |
| `START_NO_EARLIER_THAN` (floor) | **No change** — the forward-pass floor already raised est/eft, which flows into every downstream computation; this task's own LS is bounded by its successors, not its own floor | Unchanged |
| `FINISH_NO_EARLIER_THAN` (floor) | **No change**, same reasoning | Unchanged |
| `MUST_START_ON` (exact pin) | LS forced to equal est (already == the pin) whenever not overridden by an actual-start lock | Own float forced to 0 (both dimensions, since duration ties them together) |
| `MUST_FINISH_ON` (exact pin) | LF forced to equal eft (already == the pin); active even once started, matching the forward pass's own "always applies unless actual_end is set" rule | Own float forced to 0 |
| `START_NO_LATER_THAN` (ceiling) | LS capped at the constraint date when the network-implied LS would be later; LF re-derived from the capped LS | Can legitimately go negative (infeasible) |
| `FINISH_NO_LATER_THAN` (ceiling) | LF capped at the constraint date; LS re-derived from the capped LF, UNLESS the start already happened (actual_start set), in which case only LF is capped | Can legitimately go negative (infeasible) |
| `task.deadline` (independent ceiling) | Same treatment as `FINISH_NO_LATER_THAN`, applied on top of whatever constraint_type already produced | Can legitimately go negative (infeasible) |
| `actual_end` set (completed) | LS/LF forced to the task's own est/eft, unconditionally — dominates every other rule | Own float forced to 0; never re-opened by any constraint |
| `actual_start` set only (started, unfinished) | LS forced to est (start cannot move); LF left to the ceiling/network logic above, since the not-yet-happened remainder can still legitimately have finish-side slack or a finish-side ceiling | Start-dimension float 0; finish dimension follows the ceiling rules independently |

Implementation: `task_date_math.apply_backward_scheduling_constraints`,
applied inline inside `run_backward_pass`'s existing reversed-topological
loop (NOT as a separate post-pass — a predecessor reads its successor's
adjusted LS/LF later in the SAME loop, so the adjustment has to land
before that read happens, exactly like any other successor-derived
bound). A shared `_coerce_task_constraint` helper is now used by both the
forward (`apply_scheduling_constraints`) and backward direction, so the
two cannot drift apart (directive item 15).

### 10.2 Deadline decision

`task.deadline` receives the exact same backward-pass ceiling treatment
as `FINISH_NO_LATER_THAN`, but it is a value read independently of
`constraint_type` and is applied as an ADDITIONAL cap on top of whatever
`constraint_type` already produced — it never becomes a `ConstraintType`
member, is never coerced into FNLT, and `ConstraintValidator` continues
to report it as its own distinct `ConstraintType.DEADLINE` violation.
Verified directly: `test_deadline_never_reported_as_fnlt_constraint_type`
asserts `task.constraint_type is None` on a task whose only ceiling is a
deadline that the backward pass nonetheless caps correctly.

### 10.3 Negative float / infeasible semantics

`results.py`'s `total_float_days` formula previously clamped ANY
`lst < est` situation to exactly `0`. That branch was structurally
unreachable before this pass (a plain dependency graph, with no
constraint adjustment, can never produce `lst < est`), so the clamp was
silently hiding the one thing that COULD now produce it: a hard ceiling
or pin making the dependency-required schedule genuinely infeasible.
Fixed: when `lst < est`, `total_float_days` is now a real, signed
negative magnitude — `-(working_days_between(lst, est) - 1)` — computed
by calling `working_days_between` in the earlier-to-later argument order
every real `CalendarProtocol` implementation actually supports (the
reversed order returns `0`, not a signed value, in every production
calendar checked — `WorkingDaySnapshotCalendar`, `ProjectCalendarAdapter`,
the global calendar shim — so relying on a signed reversed-order result,
as some test-only fake calendars implement, would have silently produced
`0` in production).

A new `CPMTaskInfo.is_infeasible: bool` field (default `False`) is set
whenever `total_float_days < 0`, and threaded through to
`TaskScheduleOverview.is_infeasible` (Task Detail → Schedule Impact's
application-layer fact model) — but deliberately NOT threaded further
into the desktop DTO/QML layers in this pass (no QML changes; leveling,
the only other real consumer, reads the application layer directly).

**Scope boundary, stated explicitly rather than hidden**: `is_infeasible`
is derived from the SAME single float metric this codebase already
tracks (`total_float_days`, itself derived from EST vs. LST only) — it
does NOT introduce a second, finish-based float dimension. A started
task whose OWN start float is a clean `0` but whose remaining duration
cannot fit before an active `FINISH_NO_LATER_THAN`/deadline ceiling will
NOT flip `is_infeasible` (see
`test_started_but_unfinished_task_start_does_not_move`) — that
finish-side violation is, and remains, `ConstraintValidator`'s job to
report as a `ConstraintViolation`, independent of this flag. Widening
`is_infeasible` into a full two-dimensional (start AND finish) float
metric was judged disproportionate to this pass's scope.

### 10.4 Free-float semantics

Audited, not modified. `compute_free_float_days`
(`task_schedule_overview.py`) is computed purely from EARLIEST dates (a
task's own ES/EF vs. its successors' ES) and never reads LS/LF at all —
so it was already correct wherever a constraint's effect flows through
the (unchanged) forward pass, and this pass's backward-only changes
cannot alter it EXCEPT via its own documented fallback (a leaf task with
no successors reports `total_float_days` as its free float), which now
correctly inherits the fixed, possibly-negative value automatically. See
`TestFreeFloatOnConstrainedTasks` for direct coverage of both the
zero-float (pinned) and negative-float (infeasible ceiling) leaf cases.

### 10.5 Criticality semantics

`is_critical` stays `total_float_days <= 0` — a deliberate, explicit
choice (directive item 14), not a mechanical carry-over: it means an
infeasible task is ALSO reported critical (a strict superset), which is
semantically defensible (infeasible is at least as urgent as merely
critical) while `is_infeasible` remains the sharper, more severe fact a
future consumer (leveling) can check independently when "zero slack but
achievable" must be told apart from "cannot be satisfied as specified."

### 10.6 Actual-date handling

- **Completed** (`actual_end` set): LS/LF forced to the task's own
  historical est/eft, unconditionally — no constraint, ceiling, or
  network slack can reopen it. `test_completed_task_ignores_ceiling_
  entirely` proves an active `FINISH_NO_LATER_THAN` that would otherwise
  be violated has zero effect on a completed task's reported float.
- **Started, unfinished** (`actual_start` set only): the start dimension
  is pinned to history (LS = actual_start); the finish dimension remains
  governed by whatever ceiling is active, since the not-yet-executed
  remainder of the task can still legitimately be tight or loose. See
  §10.3's scope boundary for exactly what this does and does not surface
  as `is_infeasible`.

### 10.7 Test evidence

- `test_backward_pass_constraint_blindness.py` — rewritten from a
  decision record documenting the gap into a regression suite proving
  the fix (6 tests), including a corrected 3-task propagation case: the
  original 2-task fixture could not distinguish "the pin was honored"
  from "the pinned task happened to be last in the chain," which give
  the same number by coincidence.
- `test_backward_cpm_constraint_matrix.py` — the full matrix (18 tests):
  unconstrained baseline (byte-verified unchanged against the pre-fix
  code), SNET/FNET floors (verified no-op), Deadline-vs-FNLT distinction,
  all four dependency types (FS/SS/FF/SF) combined with a ceiling/pin,
  multiple predecessors, actual-date handling, a non-weekend-only
  (holiday-aware) calendar, and free-float on constrained tasks.
- `test_task_schedule_impact_bugfixes.py` —
  `TestScheduleOverviewInfeasibleFlag` (2 tests) proves the
  `is_infeasible` flag threads end-to-end through the real, DB-backed
  `ScheduleChangeImpactService`, not just at the pure `run_cpm` unit
  level.
- Full `src/tests/project_management` + `src/tests/pm` regression run:
  only the same 7 pre-existing, unrelated `test_baseline_lifecycle.py`
  failures observed before this pass (confirmed identical with this
  pass's changes stashed out) — zero regressions attributable to this
  work.

### 10.8 Leveling consumption verdict (directive item 20)

**`total_float_days`, `free_float_days`, and `is_critical` are now safe
for R4.4 leveling to consume on constrained tasks, WITH one explicit
caveat**: leveling must also check `is_infeasible` (or, for a
finer-grained finish-side check, consult `ConstraintValidator`'s
violations directly) rather than treating `total_float_days <= 0` as a
uniform "tight but movable" signal — a `False` `is_infeasible` value
does NOT guarantee the finish dimension is free of a ceiling violation
for a started-but-unfinished task (§10.3). Every other constrained
scenario in the test matrix (§10.7) reports a float number leveling can
trust as the REAL constraint-adjusted bound, including genuine
negative-float infeasibility, which is never silently clamped to zero
or otherwise disguised.

---

## 11. Wiring is_infeasible to desktop/QML

Follow-up pass (PRE-R4.4 — WIRE CPM INFEASIBILITY STATE TO DESKTOP/QML).
§10 added `is_infeasible` at the CPM/application layer but never threaded
it past `TaskScheduleOverview` — the desktop DTOs and every QML surface
still only knew about `is_critical`/`total_float_days`. This section
closes that gap on both scheduling read-path surfaces this codebase has.

### 11.1 Read-path trace and where is_infeasible was lost

```
CPMTaskInfo.is_infeasible (already existed, §10)
        |
        ├── TaskScheduleOverview.is_infeasible (already existed, §10)
        |         |
        |         └── TaskScheduleImpactOverviewDesktopDto  -- MISSING (fixed here)
        |                   |
        |                   └── schedule_impact_builder.py "isInfeasible" -- MISSING (fixed here)
        |                             |
        |                             └── TasksScheduleImpactSection.qml -- MISSING (fixed here)
        |
        └── (Scheduling workspace path, never touched by §10 at all)
                  SchedulingTaskDto.is_infeasible  -- MISSING (fixed here)
                            |
                            ├── diagnostics_builder.py "Negative Float" row
                            |         (was re-deriving total_float_days < 0) -- FIXED
                            ├── overview_builder.py "Neg. float" metric
                            |         (same re-derivation) -- FIXED
                            └── record_mappers.py criticalLabel (binary
                                      Critical/Normal, no infeasible
                                      distinction) -- FIXED (3-way)
```

`ConstraintValidator`/`ConstraintViolation`/`DependencyConstraintConflict`
were confirmed orthogonal to this trace — they never read `is_critical`/
`total_float_days`/`is_infeasible` at all, so nothing there needed
changing; they remain the "why" explanation surfaced alongside the
infeasible status, not a second feasibility calculator.

### 11.2 Desktop DTO contract

- `TaskScheduleImpactOverviewDesktopDto.is_infeasible: bool` (Task Detail
  → Schedule Impact) — threaded in `serialize_task_schedule_overview`
  (both the available and unavailable branches).
- `SchedulingTaskDto.is_infeasible: bool` (Scheduling workspace) —
  threaded in both `serialize_schedule_item` (real CPM data, via
  `getattr(item, "is_infeasible", False)` so a pre-existing fake/duck-typed
  `CPMTaskInfo`-shaped test double without the field still serializes
  safely) and `serialize_task_as_schedule_item` (the no-CPM-data fallback,
  hardcoded `False`).

Neither DTO's consumers ever compare `total_float_days < 0` themselves —
the flag is read directly, per the directive's explicit "the backend
already owns that semantic distinction."

### 11.3 Task Detail → Schedule Impact presentation

`schedule_impact_builder.py` adds two derived fields to the state dict,
computed ONCE at the Python boundary and rendered verbatim by QML:

- `"isInfeasible"` — the raw boolean, for styling (e.g. the Total Float
  value renders in `Theme.AppTheme.error` red when true).
- `"scheduleStatusLabel"` — the canonical, precedence-ordered string
  (`_schedule_status_label`): `"Infeasible"` if `is_infeasible`, else
  `"Critical"` if `is_critical`, else `"Flexible"`. This is what the
  "Schedule Status" chip (formerly a binary "Critical"/"Not critical"
  "Critical Path" field) renders — QML never compares booleans or floats
  itself to pick a label.

`TasksScheduleImpactSection.qml` changes:

- The "Critical Path" field/chip → "Schedule Status" field/chip bound to
  `scheduleStatusLabel`.
- Total Float's value colors red when `isInfeasible` (a style decision
  based on the flag, not a feasibility decision — the number itself is
  unchanged).
- A new fallback `InlineMessage` (danger tone), visible only when
  `isInfeasible` is true AND no structured `conflicts`/`actualVariances`
  already explain why (both already rendered under SCHEDULE DRIVERS,
  unchanged from §10/earlier passes) — showing the canonical generic
  explanation: *"Current scheduling constraints, dependencies, or fixed
  execution facts cannot all be satisfied simultaneously."* When a
  structured conflict DOES exist, that specific cause is shown instead
  and this generic banner stays hidden — no second conflict calculator
  was written.
- `AppWidgets.StatusChip` (a shared, app-wide component) gained two new
  recognized status words: `"infeasible"` → danger (same tone as
  `"critical"`) and `"flexible"` → success. Purely additive — no existing
  keyword's behavior changed.

Task-switch staleness was found to already be architecturally
impossible: `reset_task_lazy_sections` (`task_selection_handler.py`) sets
`scheduleImpactModel` to `{}` synchronously on every task-selection
change, before the next task's data is fetched — since every field this
section reads (`isInfeasible`, `isCritical`, `scheduleStatusLabel`,
`totalFloatDays`, …) derives from that SAME model object, there is no
code path where one field could update while another still reflects the
previous task. Confirmed with a dedicated test rather than left as an
assumption.

### 11.4 Scheduling workspace (diagnostics/overview/table) presentation

- `diagnostics_builder.py`: the "Negative Float" row (id `negative-float`)
  became "Infeasible Activities" (id `infeasible`), counting
  `item.is_infeasible` instead of `(item.total_float_days or 0) < 0`.
- `overview_builder.py`: the "Neg. float" overview metric became
  "Infeasible", same counting change.
- `record_mappers.py` / `formatters.py`: `to_schedule_record`'s
  `criticalLabel` (feeding the main Scheduling table's status column) now
  calls a new `activity_criticality_label()` helper —
  `"Infeasible"` > `"Critical"` > `"Normal"` — instead of the old binary
  `"Critical"`/`"Normal"`. `to_timeline_record`/`to_critical_path_record`
  were deliberately left as plain booleans/pre-filtered-critical lists —
  extending those further was judged unnecessary broadening beyond what
  the directive asked for on this surface.

No second, parallel diagnostics system was created — both existing
DTOs/read models were extended in place, per the directive's explicit
"prefer extending the existing diagnostics/read DTO."

### 11.5 Test evidence

- `test_qml_tasks_schedule_impact_section_contract.py` — 11 new tests:
  flexible/critical/infeasible chip states, infeasible-takes-precedence,
  negative float rendering, generic-warning shown/suppressed by a
  structured conflict, task-switch staleness (both to another task and
  to an empty/unavailable model), and a source-level assertion that no
  `totalFloatDays < 0`/`<= 0`/`== 0`-style comparison exists in the QML
  file.
- `test_qml_status_chip_priority_severity_variants.py` — confirms
  `"Infeasible"`/`"Flexible"` map to the intended danger/success tones.
- `test_task_schedule_impact_bugfixes.py` —
  `TestTaskScheduleImpactOverviewDesktopDtoInfeasibleRoundTrip` (3 tests):
  true/false round-trip through the actual desktop DTO (not just the
  application-layer fact §10 already covered), plus the
  unavailable-branch construction.
- `test_scheduling_constraints_panel.py` —
  `TestSchedulingTaskDtoInfeasibleThreading` (4 tests): true/false
  round-trip through `SchedulingTaskDto`, zero float not automatically
  infeasible, positive float not infeasible.
- `test_scheduling_infeasible_presenters.py` (new file, 8 tests):
  diagnostics row and overview metric read the flag rather than
  re-deriving it, plus the 3-way `activity_criticality_label`/
  `criticalLabel` precedence.
- Full `src/tests/project_management` regression run: **1078 passed, 1
  failed** (768s) — the single failure is the same pre-existing,
  unrelated `test_financial_desktop_forecast_delegation.py` pagination
  bug already documented in §7, reproducing in complete isolation and
  touching no file this pass changed. Zero regressions attributable to
  this wiring pass. One self-caught regression during development
  (`serialize_schedule_item` crashing on a fake `CPMTaskInfo`-shaped test
  double lacking `is_infeasible`) was found and fixed via
  `getattr(..., False)` before this run.

### 11.6 Exit gate

1. `is_infeasible` reaches both desktop DTOs — done (§11.2).
2. Schedule Impact consumes it — done (§11.3).
3. Infeasible is visually distinct from Critical — done (dedicated status
   word, dedicated danger tone, precedence-tested).
4. Negative float remains visible — done (unchanged rendering, now
   additionally colored on `isInfeasible`).
5. Zero float alone does not imply infeasible — done and tested
   (`test_zero_float_critical_task_is_not_automatically_infeasible`,
   `test_no_infeasible_activities_reports_stable`).
6. QML does not derive infeasibility itself — done and enforced by a
   source-scan test; every comparison lives in Python
   (`_schedule_status_label`, `activity_criticality_label`).
7. Structured conflict details are reused where available — done; the
   generic banner explicitly suppresses itself when `conflicts`/
   `actualVariances` already exist, no new conflict calculator written.
8. Task switching is stale-safe — done and confirmed to be already
   architecturally guaranteed, not just patched.
9. Scheduling diagnostics remain truthful — done (both the row and the
   overview metric now read the real flag).
10. Tests pass — done (see §11.5); full regression clean of new
    regressions.
11. Resource leveling was not modified.
12. ALAP was not implemented.
