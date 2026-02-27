# Core Domain Module

`core/domain/` defines the canonical business entities and enums used across
services, repositories, and reporting.

## Modeling Approach

- Python dataclasses for explicit immutable-ish contracts at service boundaries.
- static `create(...)` constructors generate IDs and apply canonical defaults.
- enums constrain state transitions and validation logic.
- optimistic-locking `version` fields exist on mutable aggregates where needed.

## Aggregate and Value Types

### Project Aggregate

- `Project`:
  - identity: `id`
  - plan window: `start_date`, `end_date`
  - status: `ProjectStatus`
  - commercial fields: `planned_budget`, `currency`
  - client metadata: `client_name`, `client_contact`
  - concurrency token: `version`
- `ProjectResource`:
  - per-project resource assignment with optional rate/currency override
  - contains `planned_hours` and `is_active`

### Task Aggregate

- `Task`:
  - schedule fields: `start_date`, `end_date`, `duration_days`, `deadline`
  - execution fields: `percent_complete`, `actual_start`, `actual_end`
  - status/priority
  - concurrency token: `version`
- `TaskAssignment`:
  - binds task to resource
  - includes allocation and logged hours
  - optional `project_resource_id` bridge
- `TaskDependency`:
  - predecessor/successor edges
  - dependency type + lag

### Resource and Cost

- `Resource`:
  - skill/role + default labor economics
  - `cost_type` and `currency_code`
  - active flag and `version`
- `CostItem`:
  - project/task scoped cost record
  - planned/committed/actual amounts
  - optional incurred date and currency
  - `version` for optimistic updates

### Calendar and Baseline

- `CalendarEvent`: project/task-linked all-day range events
- `WorkingCalendar`: working day set + hours/day
- `Holiday`: non-working date by calendar
- `ProjectBaseline`: baseline snapshot header
- `BaselineTask`: per-task schedule/cost snapshot at baseline time

### Auth, Audit, Governance

- `UserAccount`, `Role`, `Permission`
- `UserRoleBinding`, `RolePermissionBinding`
- `AuditLogEntry`: immutable action record
- `ApprovalRequest` + `ApprovalStatus`

## Enums

- `ProjectStatus`: lifecycle state for projects.
- `TaskStatus`: lifecycle state for tasks.
- `DependencyType`: FS/FF/SS/SF constraints.
- `CostType`: labor/material/overhead cost classifications.
- `ApprovalStatus`: pending/approved/rejected governance state.

## ID Strategy

- `core.domain.identifiers.generate_id()` provides globally unique string IDs.
- IDs are generated in domain factories instead of repositories.

## Compatibility Layer

`core/models.py` re-exports all domain symbols to preserve legacy imports while
new code can import directly from focused `core.domain.*` modules.
