# Core Domain

The domain model is now split between shared platform aggregates and business-module aggregates.

## Modeling Approach

- Python dataclasses for explicit service-layer contracts
- `create(...)` constructors generate IDs and canonical defaults
- enums constrain lifecycle and policy states
- optimistic-locking `version` fields are used on mutable aggregates where needed

## Platform Aggregates

Shared platform domain types include:

- `Organization`
- `Employee`
- `UserAccount`, `Role`, `Permission`
- `ProjectMembership`
- `ApprovalRequest`, `ApprovalStatus`
- `AuditLogEntry`

These live under `core/platform/*/domain.py`.

## Project Management Aggregates

Project Management currently owns:

- `Project`, `ProjectResource`
- `Task`, `TaskAssignment`, `TaskDependency`
- `Resource`
- `CostItem`
- `TimeEntry`, `TimesheetPeriod`
- `RegisterEntry`
- `TaskComment` and collaboration mention helpers
- `PortfolioIntakeItem`, `PortfolioScenario`
- `CalendarEvent`, `WorkingCalendar`, `Holiday`
- `ProjectBaseline`, `BaselineTask`

These live under `core/modules/project_management/domain/`.

## Key Enum Families

- planning and execution:
  - `ProjectStatus`
  - `TaskStatus`
  - `DependencyType`
- commercial/resource:
  - `CostType`
  - `WorkerType`
  - `EmploymentType`
- governance and enterprise:
  - `ApprovalStatus`
  - register and portfolio status enums
  - timesheet period status enums

## ID Strategy

`core/modules/project_management/domain/identifiers.generate_id()` remains the shared ID generator used across current aggregates.

## Import Direction

Domain consumers now import types directly from their owning platform or module
packages instead of going through a shared model facade.
