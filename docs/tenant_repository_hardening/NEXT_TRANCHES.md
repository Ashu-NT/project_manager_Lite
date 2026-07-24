# Next Tenant Hardening Tranches

## Current state

- Platform repository hardening rounds are completed.
- Project-management repository hardening round 1 is implemented and verified:
  - task, assignment, dependency, collaboration, cost, calendar, register, and
    baseline repositories
- Project-management repository hardening round 2 is implemented and verified:
  - project resources
  - portfolio intake, scenario, dependency, and scoring-template repositories
  - resource skills, certifications, and task skill requirements
  - PM project and resource calendar assignments
- Access-control repository hardening is completed.
- Inventory repository hardening round 1 is implemented:
  - catalog roots
  - storeroom and stock roots
  - storage location, reorder policy, and cycle count repositories
- Procurement repository hardening round 1 is implemented and verified:
  - requisition roots
  - purchase order roots
  - receipt header roots
- Procurement repository hardening round 2 is implemented and verified:
  - requisition lines
  - purchase-order lines
  - receipt lines
- Maintenance tenant-root repository hardening round 1 is implemented and verified:
  - locations
  - systems
  - assets
  - sensors
  - integration sources
  - failure codes
  - task templates
  - work requests
  - work orders
  - preventive plans
- Maintenance secondary repository hardening round 2 is implemented and verified:
  - asset components
  - sensor readings
  - sensor source mappings
  - sensor exceptions
  - work-order tasks
  - work-order task steps
  - work-order material requirements
  - task-step templates
  - preventive plan tasks
  - preventive plan instances
  - downtime events
- Controller and settings follow-up is implemented and verified:
  - runtime organization switching now requires `settings.manage`
  - PM QML saved-view and table-column settings now resolve active organization
    context from `platformRuntimeApi.get_runtime_context()`
  - PM task-view fallback settings now use `tenant/__no_organization__/...`
    instead of bare keys
- Project-management contract cleanup round 1 is implemented and verified:
  - PM portfolio repositories now use scoped `get/list/delete` contracts
  - PM project and resource callers no longer use explicit
    `list_for_organization(...)` compatibility methods
  - `PortfolioService` now requires `TenantContextService` at construction time
- Inventory + maintenance constructor tightening round 1 is implemented and
  verified:
  - inventory catalog, stock, reservation, and procurement application services
  - maintenance application services
  - maintenance reporting service
  - maintenance work-allocation adapter
- Inventory + maintenance repository constructor tightening round 1 is
  implemented and verified:
  - inventory/procurement repositories now require constructor-time tenant
    context
  - maintenance-owned repositories now require constructor-time tenant context
  - inventory registry no longer patches repository tenant context post-build
  - maintenance registry patching is reduced to locally created platform repos

## Next implementation order

1. Platform + PM repository constructor tightening for remaining post-build tenant-context wiring
2. Non-PM contract cleanup for remaining transitional repository APIs

## Execution notes

- Reuse the same `TenantScopedRepositorySupport` style already applied in
  platform, access-control, project-management, inventory, procurement, and
  maintenance root repositories.
- Prefer shared runtime-context helpers when QML workspaces need the active
  organization id from the platform runtime API.
- Prefer scoped repository `list()` / `get()` contracts once the active tenant
  and organization are already enforced by the repository itself.
- Require active organization context for repository reads and writes.
- Scope `get(...)`, `get_by_*`, list, and delete behavior so foreign rows return
  `None` or `[]` and are not mutated.
- Stamp missing `organization_id` and `tenant_id` metadata from the active
  tenant context on writes.
- Add focused repository hardening tests for each tranche and append the
  verification outcome to the tranche-specific doc under
  `docs/tenant_repository_hardening/`.
