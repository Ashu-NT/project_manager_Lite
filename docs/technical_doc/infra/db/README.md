# Infrastructure Database Layer

`infra/db/` implements persistence for all `core/interfaces.py` repository
contracts using SQLAlchemy ORM and aggregate-specific mappers/repositories.

## Components

- `base.py`: engine + session factory and DB URL resolution
- `models.py`: ORM schema definitions, indexes, and constraints
- `optimistic.py`: generic version-checked update helper
- aggregate folders:
  - `project/`
  - `task/`
  - `resource/`
  - `cost_calendar/`
  - `baseline/`
  - `auth/`
  - `audit/`
  - `approval/`
- facade wrappers:
  - `repositories.py`
  - `repositories_*`
  - `mappers.py`

## Schema Highlights

Core tables:

- planning: `projects`, `tasks`, `task_dependencies`, `task_assignments`
- economics: `resources`, `project_resources`, `cost_items`
- schedule calendar: `working_calendars`, `holidays`, `calendar_events`
- baseline: `project_baselines`, `baseline_tasks`
- security/governance:
  - `users`, `roles`, `permissions`
  - `user_roles`, `role_permissions`
  - `audit_logs`, `approval_requests`

Schema features:

- cascade delete FKs for project/task-bound aggregates
- uniqueness constraints for mapping tables
- targeted indexes for common query filters
- optimistic lock `version` columns on mutable aggregates

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
