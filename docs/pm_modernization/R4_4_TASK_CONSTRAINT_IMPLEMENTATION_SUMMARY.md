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
- **Backward-pass CPM constraint-blindness was NOT fixed** — a deliberate,
  documented STOP (see `test_backward_pass_constraint_blindness.py`).
  `run_backward_pass` is depended on by many unaudited consumers beyond
  this pass's scope; total float and criticality can still be
  meaningless for a constrained task's own float number. This is the one
  finding from the audit's numbered list that remains open by design, not
  by oversight.
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
| Backend 3 | Backward pass fully constraint-blind (§36.3) | **Deliberately not fixed** — documented STOP, §2 |
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
- **Backward-pass constraint-blindness** (see §2) — an explicit,
  documented non-fix.
- Everything explicitly out of scope per the standing constraints: R4.4
  resource leveling, ALAP, a full Scheduling workspace redesign, R5.
