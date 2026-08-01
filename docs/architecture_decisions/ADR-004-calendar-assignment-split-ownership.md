# ADR-004: Calendar Assignment Split Ownership

- Status: accepted
- Date: 2026-08-01

## Context

The Platform Enterprise Calendar (`src/core/platform/calendar/`) resolves a
working-day schedule through a fixed hierarchy: GLOBAL → SITE → DEPARTMENT →
EMPLOYEE → PROJECT → RESOURCE. Site, department, and employee calendar
assignments are straightforward — `SiteCalendarAssignment`,
`DepartmentCalendarAssignment`, and `EmployeeCalendarAssignment` all live in
the platform module, since `sites`, `departments`, and `employees` are
platform-owned tables.

Project and resource calendar assignments don't fit that pattern.
`ProjectCalendarAssignment` and `ResourceCalendarAssignment` FK into
`projects.id` / `resources.id`, both owned by `project_management`. Platform
must never depend on a module's schema (see ADR-001/ADR-002 precedent), so
these two assignment tables cannot live in the platform module even though
they are conceptually two more rungs on the exact same calendar-assignment
ladder as site/department/employee.

Without a documented decision here, a future contributor could reasonably
read this split and assume it's accidental duplication — either merging the
tables (breaking the module boundary) or building a second, PM-owned
calendar-assignment service (duplicating `CalendarAssignmentService`).

## Decision

`ProjectCalendarAssignment` and `ResourceCalendarAssignment` — domain class,
ORM, and repository — live in `project_management`
(`domain/calendar/assignment.py`,
`infrastructure/persistence/{orm,repositories}/calendar_assignment.py`),
**not** in the platform module.

They are still exposed through the **same** platform services as
site/department/employee assignment:

- `CalendarAssignmentService` (`src/core/platform/calendar/application/calendar_assignment_service.py`)
  takes `project_assignment_repo`/`resource_assignment_repo` as `Any`-typed
  constructor parameters, and its `assign_project_calendar`/
  `assign_resource_calendar` methods import the PM domain types *locally
  inside the method body* (not at module scope) to avoid a hard top-level
  platform → PM dependency.
- `EnterpriseCalendarResolver` (`enterprise_calendar_resolver.py`) takes the
  same two repos, also `Any`-typed, and treats PROJECT/RESOURCE as two more
  levels of the same resolution chain as SITE/DEPARTMENT/EMPLOYEE.

The composition root (`src/infra/composition/repositories.py` +
`platform_registry.py`) is the only place that constructs the concrete PM
repository classes and wires them into these platform services — it is the
one layer allowed to know both modules concretely.

## Why

- Table ownership follows FK ownership, not conceptual grouping. A join
  table's home is determined by which side of the FK is more foreign to
  change independently; here that's the PM-owned `project_id`/`resource_id`.
- One logical concept — "which calendar does this thing use" — should have
  one API surface (`CalendarAssignmentService`) and one resolution algorithm
  (`EnterpriseCalendarResolver`), regardless of where the underlying storage
  lives. Splitting the *service* along the same lines as the *storage* would
  turn one coherent five-level hierarchy into two parallel, harder-to-reason-about
  systems.
- `Any`-typing plus function-local imports is the established pattern in
  this codebase for "the composition root knows the concrete type, the
  consuming module only needs the duck-typed shape" — it keeps
  `test_platform_calendar_does_not_import_project_management_at_module_scope`
  (`src/tests/architecture/test_architecture_guardrails_legacy_orm.py`)
  green without sacrificing a unified API.

## Consequences

- Anyone adding a new calendar-assignment level (e.g. a future
  `CustomerCalendarAssignment` in another module) should follow the same
  pattern: table in the owning module, wired into
  `CalendarAssignmentService`/`EnterpriseCalendarResolver` via an `Any`-typed
  constructor param and a composition-root wiring change — not a new
  parallel service.
- The architecture guardrail test above will fail loudly if a future change
  accidentally adds a module-scope `project_management` import to
  `src/core/platform/calendar/`, which is the main risk this split
  introduces.
