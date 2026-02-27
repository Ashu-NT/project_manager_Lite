# Core Module

`core/` is the business layer. It contains domain entities, service logic,
interfaces, events, and reporting calculations. It is intentionally UI-agnostic.

## Design Role

- Source of truth for business rules.
- Defines repository/service contracts (`core/interfaces.py`).
- Owns scheduling, cost policy, baseline, governance, finance, and reporting logic.
- Emits domain events for reactive UI refresh.

## Key Packages

- `core/domain/`: dataclass domain entities and enums
- `core/services/`: service layer split by business capability
- `core/events/`: domain event hub + lightweight signal primitive
- `core/reporting/`: export API and renderers (Excel/PDF/PNG)
- `core/interfaces.py`: repository abstractions
- `core/exceptions.py`: typed domain/business error hierarchy

## Dependency Rule

Strict layering objective:

- `core` must not import `ui`.
- `infra` implements `core` interfaces.
- `ui` calls into `core` services.

Architecture guardrails in tests enforce this rule continuously.

## Domain Model Strategy

- Dataclass-first modeling for explicit, serializable business entities.
- Static `create(...)` factories centralize ID generation and safe defaults.
- Enums model constrained states (project status, task status, dependency/cost types).
- Compatibility facade (`core/models.py`) preserves legacy import paths.

## Service Strategy

Service modules are decomposed to reduce monolith growth:

- orchestration class + focused mixins
- policy helpers
- dedicated models for reporting and scheduling payloads

This supports:

- easier targeted testing
- smaller change blast radius
- lower merge conflict density

## Error Semantics

Core services use typed errors for deterministic UX handling:

- `ValidationError`: invalid input/state
- `NotFoundError`: missing aggregate/entity
- `BusinessRuleError`: governance/policy/rule violations
- `ConcurrencyError`: optimistic locking stale write

UI guard helpers map these to user-facing message dialogs.

## Transaction and Event Behavior

Typical mutation flow:

1. Validate input and permissions.
2. Read and mutate domain object(s).
3. Persist through repositories.
4. Commit SQLAlchemy session.
5. Emit domain event (`domain_events.*_changed`) for UI synchronization.

## Documentation Map

- Domain contracts: [Core Domain](domain/README.md)
- Event bus: [Core Events](events/README.md)
- Service architecture: [Core Services](services/README.md)
- Export/rendering stack: [Core Reporting Export Layer](reporting/README.md)
