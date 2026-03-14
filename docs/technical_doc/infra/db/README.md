# Infrastructure Database Layer

Persistence is split between `infra/platform/db/` for shared platform concerns and `infra/modules/project_management/db/` for the current production business module.

## Components

- `infra/platform/db/base.py`: engine + session factory + DB URL resolution
- `infra/platform/db/models.py`: shared ORM schema definitions
- `infra/platform/db/optimistic.py`: version-checked update helper
- shared aggregate folders:
  - `auth/`
  - `access/`
  - `approval/`
  - `audit/`
  - `modules/`
  - `org/`
  - `time/`
- PM aggregate folders:
  - `project/`
  - `task/`
  - `resource/`
  - `cost_calendar/`
  - `baseline/`
  - `collaboration/`
  - `portfolio/`
  - `register/`
- compatibility facade wrappers:
  - `infra/platform/db/repositories.py`
  - `infra/platform/db/mappers.py`

## Schema Highlights

Core tables:

- planning: `projects`, `tasks`, `task_dependencies`, `task_assignments`
- economics: `resources`, `project_resources`, `cost_items`
- schedule calendar: `working_calendars`, `holidays`, `calendar_events`
- baseline: `project_baselines`, `baseline_tasks`
- collaboration and portfolio:
  - `task_comments`
  - `portfolio_intake_items`
  - `portfolio_scenarios`
- platform administration:
  - `organizations`
  - `employees`
  - `organization_module_entitlements`
  - `project_memberships`
- shared time:
  - `time_entries`
  - `timesheet_periods`
- security/governance:
  - `users`, `roles`, `permissions`
  - `user_roles`, `role_permissions`
  - `audit_logs`, `approval_requests`

Schema features:

- cascade delete FKs for project/task-bound aggregates
- uniqueness constraints for mapping tables
- targeted indexes for common query filters
- optimistic lock `version` columns on mutable aggregates
- employee rows include site context for shared staffing/time metadata
- time-entry rows include neutral owner metadata plus optional employee/site/department snapshots for future cross-module reuse

## Mapper Strategy

Each aggregate has a mapper translating:

- domain dataclass <-> SQLAlchemy ORM row

This keeps repository logic focused on query and transaction behavior instead of
field conversion details.

## Repository Strategy

Aggregate repositories implement the abstract interface contracts:

- CRUD operations
- list/filter operations
- cascade-aware deletions
- specialty operations (dependencies, assignments, baselines, auth bindings)

Facade wrapper modules preserve old import paths while delegating to aggregate
folder implementations.

## Concurrency Control

`optimistic.update_with_version_check(...)` performs conditional update:

- `WHERE id = ? AND version = expected_version`
- increments version on success
- raises `NotFoundError` when missing
- raises `ConcurrencyError(code=\"STALE_WRITE\")` when stale

This prevents silent lost updates in concurrent UI sessions.

## Transaction Ownership

Repositories do not own transaction boundaries. Services own commit/rollback
semantics, so multi-repository operations remain atomic at service level.
