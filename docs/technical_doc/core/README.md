# Core Layer

`core/` is the business layer. It contains the canonical rules, aggregates, policies, and services for both shared platform behavior and business modules.

## Current Structure

- `core/platform/`
  - shared business concerns such as auth, access, org, approval, audit, modules, notifications, and time
- `core/modules/project_management/`
  - the current production-ready business module
- `core/modules/maintenance_management/`
- `core/modules/qhse/`
- `core/modules/payroll/`
  - planned or placeholder module roots

## Design Role

- source of truth for domain rules
- repository and service contract ownership through `core/platform/common/interfaces.py`
- module guard enforcement for business capabilities
- domain-event emission for reactive desktop refresh behavior

## Key Packages

- `core/platform/common/`: shared interfaces, exceptions, and compatibility facades
- `core/platform/modules/`: module entitlement rules and runtime guards
- `core/platform/notifications/`: domain event hub and signal primitive
- `core/platform/org/`: organization and employee domain/services
- `core/platform/time/`: canonical time-entry and timesheet-period domain and service boundary
- `core/modules/project_management/domain/`: PM aggregates and enums
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
- compatibility exports in `core/platform/common/models.py` keep older import paths working while the focused package structure evolves

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
