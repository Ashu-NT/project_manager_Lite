# Core Layer

`core/` is the business layer. It contains the canonical rules, aggregates, policies, and services for both shared platform behavior and business modules.

## Current Structure

- `core/platform/`
  - shared business concerns such as auth, access, org, approval, audit, modules, notifications, and time
- `core/modules/project_management/`
  - the current production-ready business module
- `core/modules/inventory_procurement/`
- `core/modules/maintenance_management/`
- `core/modules/qhse/`
- `core/modules/hr_management/`
  - `inventory_procurement` and `maintenance_management` now have real module-owned services
  - `qhse` and `hr_management` remain planned or placeholder module roots

Legacy compatibility package roots such as `core/modules/payroll/` are still preserved where helpful during the rename transition.

## Design Role

- source of truth for domain rules
- shared repository contracts through `core/platform/common/interfaces.py`
- platform-owned integration ports through package-local interfaces such as `core/platform/time/interfaces.py` and `core/platform/org/interfaces.py`
- PM repository contracts through `core/modules/project_management/interfaces.py`
- module guard enforcement for business capabilities
- domain-event emission for reactive desktop refresh behavior

## Key Packages

- `core/platform/common/`: shared interfaces, exceptions, IDs, and error contracts
- `core/platform/modules/`: module entitlement rules and runtime guards
- `core/platform/notifications/`: domain event hub and signal primitive
- `core/platform/org/`: organization and employee domain/services, including site context on employees
- `core/platform/time/`: canonical work-entry/time-entry and timesheet-period domain, service boundary, and neutral work ports
- `core/modules/project_management/domain/`: PM aggregates and enums
- `core/modules/project_management/interfaces.py`: PM-owned repository/service contracts
- `core/modules/project_management/services/`: PM business services
- `core/modules/project_management/reporting/`: export and rendering pipeline

## Dependency Rule

- `core` must not import `ui`
- `infra` implements core contracts
- `application`, `api`, and `ui` consume `core` behavior through stable seams

Architecture guardrails in `tests/test_architecture_guardrails.py` enforce the main layering rules continuously.

## Modeling Strategy

- dataclass-first aggregates and typed enums
- `create(...)` factories centralize ID generation and safe defaults
- domain types now import directly from their owning platform or module packages

## Error Semantics

Core services use typed errors for deterministic UX and transport handling:

- `ValidationError`
- `NotFoundError`
- `BusinessRuleError`
- `ConcurrencyError`

## Transaction and Event Behavior

Typical mutation flow:

1. validate input and permissions
2. read and mutate aggregate state
3. persist through repositories
4. commit the session
5. emit the relevant `domain_events.*_changed` signal

## Documentation Map

- [Core Domain](domain/README.md)
- [Core Events](events/README.md)
- [Core Services](services/README.md)
- [Core Reporting Export Layer](reporting/README.md)
