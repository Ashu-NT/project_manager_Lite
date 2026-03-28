# Architecture Blueprint

## Scope

This document captures the current architectural shape of the product, the main
remaining hotspots, and the guardrails we are using to keep the repo
maintainable while it evolves from a PM app into a modular enterprise platform.

## Current Architecture

The repo now uses five major layers:

1. `application/`
   Shared orchestration seams used by desktop today and prepared for future
   hosted delivery later.
2. `core/`
   Platform and module domain logic, business rules, and service contracts.
3. `infra/`
   Persistence, migrations, diagnostics, and dependency wiring.
4. `api/`
   Transport-facing adapters that reuse the same application-layer contracts.
5. `ui/`
   Desktop shell, platform workspaces, and module presentation logic.

Within `core/`, `infra/`, and `ui`, shared concerns live under `platform/`
while business features live under `modules/`.

## Delivered Structural Work

- Platform/module repository split is in place.
- The desktop shell is platform-aware and module-aware.
- Module licensing and organization-scoped entitlements are implemented for the
  current desktop/runtime flow.
- Shared application seams now exist for platform runtime and entitlement
  orchestration.
- Major PM feature areas have already been split into coordinator-oriented tabs
  plus focused helper modules.

## Current Hotspots

The biggest remaining maintainability hotspots are:

1. `main.py`
   Startup, CLI control flow, and service access are still bundled too tightly.
2. `core/modules/project_management/services/scheduling/engine.py`
   Forward-pass scheduling, critical-path analysis, and calendar-sensitive logic
   still share too much surface area.
3. `infra/platform/db/mappers.py`
   Mapping logic is still broader than ideal and should continue to split by
   aggregate.
4. `infra/platform/db/repositories.py`
   The remaining top-level repository facade still aggregates many focused
   repository exports.

## Next Structural Refactors

Recommended order:

1. Split `main.py` into bootstrap, CLI wiring, and command flow modules.
2. Continue breaking down the scheduling engine into smaller capability slices.
3. Split infrastructure DB mappers further by aggregate family.
4. Start the Maintenance module skeleton now that the shared time boundary can
   carry neutral work-entry ownership and employee/site/department context.

## Architecture Principles

1. Single Responsibility
   - tabs coordinate workflows
   - dialogs own dense interaction forms
   - services own business logic
2. Layered Dependency Rule
   - `core` must not import `ui`
3. Stable Interfaces
   - keep contracts explicit at service, repository, and application seams
4. Compatibility-First Refactors
   - prefer wrappers and additive moves before deleting old paths
5. Module Awareness
   - platform concerns stay separate from business-module concerns
6. Guardrail Enforcement
   - large-file budgets and dependency rules stay codified in tests

## Guardrails

Architecture guardrails are codified in:
`tests/test_architecture_guardrails.py`

These checks validate:

1. hard file-size ceilings
2. `core -> ui` import violations
3. coordinator-only patterns for major PM tabs
4. growth budgets for known large modules
