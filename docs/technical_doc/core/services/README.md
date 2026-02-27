# Core Services Module

`core/services/` is the executable business layer. It coordinates repositories,
enforces permissions and policy, manages transactions, and publishes domain
events after state changes.

## Architectural Style

- Service orchestrators plus mixin decomposition.
- Explicit repository interfaces from `core/interfaces.py`.
- Transactional behavior through injected SQLAlchemy session.
- Typed exceptions for deterministic UI handling.

## Service Families

### Auth and Security

- `auth/service.py`:
  - bootstraps default permissions, roles, and admin account
  - password policy and hashing verification
  - user and role lifecycle operations
  - principal construction for runtime session context
- `auth/authorization.py`: permission requirement helpers
- `auth/session.py`: runtime principal/session container

### Governance and Audit

- `approval/service.py`:
  - request, approve, reject governed changes
  - self-approval prevention
  - request-type apply handler registry
- `approval/policy.py`:
  - governance mode from env vars
  - default governed action set
- `audit/service.py`:
  - immutable action logging with actor attribution

### Planning and Execution

- `project/service.py` with lifecycle and query mixins
- `task/service.py` with lifecycle, dependency, assignment, query, validation mixins
- `resource/service.py` for resource CRUD and optimistic lock checks
- `cost/service.py` for cost CRUD and cost summaries

### Schedule and Calendar

- `scheduling/engine.py`:
  - CPM forward and backward passes
  - FS, FF, SS, SF dependencies with lag
  - actual start/end constraint application
  - computed dates persisted back to tasks
- `scheduling/leveling*.py`: over-allocation detection and leveling actions
- `work_calendar/engine.py`: working-day arithmetic and holiday exclusion
- `work_calendar/service.py`: persisted calendar and holiday configuration
- `calendar/service.py`: manual and task-derived calendar events

### Baseline, Reporting, Finance, Dashboard

- `baseline/service.py`:
  - baseline snapshots of schedule and cost state
  - duration-weighted allocation of unassigned budget and labor
  - governance-aware baseline creation path
- `reporting/service.py` plus mixins:
  - KPI, EVM, variance, baseline compare, cost breakdown, labor analytics
- `finance/service.py`:
  - ledger, cashflow, and analytics read models aligned with reporting policy
- `dashboard/service.py`:
  - aggregate payload for dashboard UI
  - resource conflict preview and leveling operations

## Permission and Governance Model

- Direct mutation requires `*.manage` permission.
- If governance is enabled and action is governed:
  - non-admin users with `approval.request` create a request instead of immediate apply.
- Decision actions require `approval.decide`.

## Event Emission Model

Services emit domain events after successful commit so UI tabs can refresh
targeted state by concern (project/task/resource/cost/baseline/approval).

## Concurrency and Data Integrity

- mutable aggregates include `version` tokens
- stale writes raise `ConcurrencyError(code=\"STALE_WRITE\")`
- repository update helpers enforce version-checked writes
