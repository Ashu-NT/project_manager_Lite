# Core Services

The executable service layer is now split between shared platform services and module-specific services.

## Service Style

- orchestrator classes plus focused mixins/helpers where needed
- explicit repository interfaces from `core/platform/common/interfaces.py`
- transaction control through injected SQLAlchemy sessions
- typed exceptions for deterministic UI and transport handling

## Platform Service Families

### Identity and Security

- `core/platform/auth/service.py`
  - user lifecycle, role/permission seeding, login, session construction, lockout handling
- `core/platform/auth/authorization.py`
  - permission requirement helpers
- `core/platform/auth/session.py`
  - active principal/session context

### Access, Audit, and Governance

- `core/platform/access/service.py`
  - project memberships and scoped access
- `core/platform/approval/service.py`
  - governed change requests and decision/apply workflow
- `core/platform/audit/service.py`
  - immutable audit log writes and reads

### Organization and Module Runtime

- `core/platform/org/service.py`
  - employee and organization lifecycle
- `core/platform/time/service.py`
  - canonical time-entry and timesheet-period workflows reused by the PM wrapper today
- `core/platform/modules/service.py`
  - catalog, entitlement, lifecycle status, and provisioning rules
- `core/platform/modules/runtime.py`
  - thin runtime-facing seam over the catalog for callers

## Project Management Service Families

- `project/`: project lifecycle, query, and project-resource planning
- `task/`: task lifecycle, assignments, dependencies, time-entry integration
- `timesheet/`: PM compatibility wrapper over the shared platform time service
- `resource/`: resource catalog and employee-linked worker handling
- `cost/`: project/task cost workflows
- `calendar/` and `work_calendar/`: persisted calendar state and working-day arithmetic
- `baseline/`: schedule/cost baseline capture
- `reporting/`: KPI, variance, EVM, labor, and cost analytics
- `finance/`: finance-oriented read models and exports
- `dashboard/`: aggregate dashboard payloads
- `register/`, `collaboration/`, `portfolio/`, `import_service/`: enterprise PM extensions

## Permission and Governance Model

- direct mutation requires the relevant `*.manage` or scoped permission
- governed actions can route through approvals instead of direct apply
- business-module entry services can be blocked by module entitlement guards when a module is disabled

## Event Emission Model

Services emit domain events after successful commit so desktop views can refresh targeted state:

- project/task/resource/cost/baseline/register
- approvals and audit-adjacent admin updates
- employees, organizations, access, collaboration, portfolio, and module-entitlement changes

## Concurrency and Data Integrity

- mutable aggregates use `version` tokens where appropriate
- stale writes raise `ConcurrencyError(code="STALE_WRITE")`
- repository update helpers enforce version-checked writes
