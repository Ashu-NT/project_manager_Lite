# PM Data-Integrity — Follow-up Plan

**Date:** 2026-05-31
**Status:** Phase 0 (detector + tests) DONE. Phase 2 (constraints) + Phase 3 (app guard) DONE 2026-05-31. Phase 1 (run-on-prod-data cleanup) is an operator step before the migration is applied to a non-empty DB. Phase 4 optional.
**Input:** `PM_DATA_INTEGRITY_AUDIT.md`
**Principle:** the backend already enforces the invariants on new writes; this plan hardens *defense-in-depth* (DB constraints) and cleans legacy data — **detect → clean → constrain**, never auto-delete.

---

## Phase 0 — Detector + regression tests  ✅ DONE (this turn)

- `infrastructure/persistence/health/integrity_checks.py` — read-only `run_pm_data_integrity_checks(session)` returning an `IntegrityReport` of 12 checks (orphans, cross-project dependency/assignment/cost/baseline, duplicate dependency/assignment/project-resource, project_resource mismatch, overallocation).
- `tools/pm_data_integrity_check.py` — CLI; exits non-zero on any ERROR finding.
- `src/tests/project_management/test_data_integrity.py` — 13 tests, all green.

Run it: `python -m tools.pm_data_integrity_check`

---

## Phase 1 — Run against real data & clean (operator step)

1. Back up the database.
2. `python -m tools.pm_data_integrity_check` and review every finding.
3. Remediate via the normal services/UI (re-point or remove offending rows). Record what changed.
4. Re-run until the report is `OK` (or only `review`-severity overallocation remains, judged acceptable).

Do **not** proceed to Phase 2 until ERROR/WARNING counts are zero — the unique-constraint migration will fail on existing duplicates.

---

## Phase 2 — Add DB unique constraints (after Phase 1 is clean)  ✅ DONE

Implemented as migration `k4l5m6n7o8p9_add_pm_integrity_unique_constraints.py`
(unique indexes `ux_task_dependencies_pair`, `ux_task_assignments_task_resource`)
with a **pre-flight guard** that aborts with a clear message if duplicate rows
exist (pointing at the health-check) — so it is safe to attempt and will not
half-apply. Mirrored in the ORM (`orm/task.py`) so fresh DBs/tests enforce them.
The two duplicate-detection tests now assert the DB raises `IntegrityError`.

> Operator note: on a non-empty production DB, still run Phase 1 first — the
> migration's pre-flight guard will refuse to run until duplicates are cleaned.

Original DDL (now implemented):

```python
def upgrade() -> None:
    op.create_unique_constraint(
        "uq_task_dependencies_pair",
        "task_dependencies",
        ["predecessor_task_id", "successor_task_id"],
    )
    op.create_unique_constraint(
        "uq_task_assignments_task_resource",
        "task_assignments",
        ["task_id", "resource_id"],
    )

def downgrade() -> None:
    op.drop_constraint("uq_task_assignments_task_resource", "task_assignments", type_="unique")
    op.drop_constraint("uq_task_dependencies_pair", "task_dependencies", type_="unique")
```

Mirror the constraints in the ORM (`task.py`) so fresh DBs/tests get them too:
```python
# TaskDependencyORM
UniqueConstraint("predecessor_task_id", "successor_task_id", name="uq_task_dependencies_pair")
# TaskAssignmentORM
UniqueConstraint("task_id", "resource_id", name="uq_task_assignments_task_resource")
```

After this, the `duplicate_dependency` / `duplicate_assignment` health checks should always read 0, and the `test_data_integrity.py` duplicate tests must be updated to expect an `IntegrityError` on insert instead (flip them to assert the DB now rejects the dupes).

---

## Phase 3 — Application-layer duplicate-assignment guard  ✅ DONE

Implemented in **both** assignment creation paths — `assign_project_resource`
(assignment.py) and the no-repo branch of `assign_resource` (assignment_bridge.py)
— raising `ValidationError(code="ASSIGNMENT_DUPLICATE")` so the UI shows a
friendly message before the DB constraint fires. Covered by
`test_assign_resource_twice_raises_assignment_duplicate`. The existing
`test_resource_flow.py` overallocation test was updated to drive overallocation
via a distinct overlapping task (the old setup relied on a now-rejected
duplicate assignment).

Reference implementation:

```python
existing = self._assignment_repo.list_by_task(task_id)
if any(a.resource_id == project_resource.resource_id for a in existing):
    raise ValidationError("Resource is already assigned to this task.",
                          code="ASSIGNMENT_DUPLICATE")
```
Add a service test mirroring the existing `DEPENDENCY_DUPLICATE` test.

---

## Phase 4 — Optional hardening (low priority)

- Re-scope repo `delete`/`get` by id to also filter `project_id` where a project context is available (defense-in-depth; app layer already gates).
- Convert `BaselineVarianceRecordORM.project_id` to a real FK.
- Confirm `CalendarEventRepository.list_range` is project-scoped at call sites.
- UI: add required-field validation + `InlineMessage` to `TaskAssignmentHoursDialog` and `ProjectStatusDialog`.
- Wire the health-check into CI (the CLI already exits non-zero on ERROR findings) as a nightly/data-migration gate.

---

## Out of scope

- Platform **time-entry / timesheet** integrity (`src/core/platform/time/**`) — separate module; audit independently if required.
- New scoped controller properties — current scoping verified correct; no churn.
