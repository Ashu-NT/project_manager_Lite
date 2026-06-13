# Tenant Repository Hardening

Status: In progress  
Last updated: 2026-06-13

This README is the working follow-up for the enterprise multi-tenant repository
hardening brief in the attached audit request. It is meant to stay practical:
what was scanned, what the code actually looks like today, what has been
hardened already, and what still needs a follow-through pass.

## Scope scanned

The discovery pass covered:

- `src/core/**`
- `src/infra/**`
- `src/ui_qml/**`
- `src/tests/**`
- `src/infra/persistence/migrations/**`
- existing tenant docs in `docs/**`

## Current architecture reality

The codebase is in a mixed state.

- `TenantContextService` is already the runtime source of tenant and organization
  context.
- Several Project Management repositories already use repository-scoped tenant
  joins.
- Maintenance repositories now use shared scoped helpers across both tenant-root
  records and parent-scoped secondary records.
- Project-management portfolio and remaining secondary repositories now use the
  same helper pattern for parent-scoped project/resource/task ownership.
- Inventory/procurement and maintenance services now require injected
  `TenantContextService` at construction time instead of silently rebuilding
  session context from `organization_repo` and `user_session`.
- Inventory/procurement and maintenance-owned repositories now require
  injected `TenantContextService` at construction time instead of being patched
  after creation by their module registries.
- Access-control repositories sat in a gray area between auth bootstrap and
  business-data scoping; they needed a narrower hardening pass than the rest of
  the platform repos.
- Procurement child-line repositories do not own `tenant_id` or
  `organization_id`; they inherit scope through requisition, purchase-order,
  and receipt header joins.
- `update_with_version_check()` is already better than the legacy brief assumed:
  its existence check now respects `extra_filters` instead of falling back to an
  unsafe plain `session.get()`.
- UI settings already support organization scoping for task views, dashboard
  layout, and table column state, and the PM QML controller layer now resolves
  active-organization settings context from the live platform runtime API.

## Audit summary

### Highest-confidence priority leaks found

These were the clearest enterprise gaps and the safest first hardening target:

| Repository | Current state before this pass | Main risk |
| --- | --- | --- |
| `SqlAlchemyTaskRepository` | Scoped reads, but update trusted row id + version only | cross-scope update path |
| `SqlAlchemyAssignmentRepository` | Scoped reads, but `merge()` and delete paths were unscoped | cross-scope update/delete |
| `SqlAlchemyDependencyRepository` | No tenant context enforcement | cross-scope read/update/delete |
| `SqlAlchemyTaskCommentRepository` | Scoped reads, but `merge()` was unscoped | cross-scope update |
| `SqlAlchemyTaskPresenceRepository` | No tenant context enforcement | cross-scope collaboration presence |
| `SqlAlchemyCostRepository` | Scoped reads, unscoped delete paths | cross-scope delete |
| `SqlAlchemyCalendarEventRepository` | Scoped reads, unscoped update/delete paths | cross-scope update/delete |
| `SqlAlchemyRegisterEntryRepository` | Scoped reads, unscoped delete path | cross-scope delete |
| `SqlAlchemyBaselineRepository` | Baseline root was partly scoped, child-table access still trusted ids | baseline task and variance leakage |

### Broader repo-wide pattern findings

- Platform tenant-root repositories still need constructor-time
  `TenantContextService` requirements instead of post-build optional wiring.
- Inventory and Maintenance tenant-root repositories still stamp `tenant_id`
  conditionally instead of overwriting from runtime context.
- Project-management portfolio, project, and resource callers now use the
  scoped repository contract directly instead of forwarding explicit
  `organization_id` values through compatibility methods.
- Contract cleanup is still needed for remaining transitional repository APIs
  and composition seams that rely on optional post-build tenant-context wiring.

## Changes implemented in this pass

### Repository hardening

The first implementation tranche hardens the priority PM repositories named in
the brief.

- Repository writes now verify parent scope before inserting child rows.
- Child-table repositories now reject missing tenant context instead of
  operating in an effectively unscoped mode.
- `merge()`-based updates were replaced with explicit scoped loads and field
  updates where the prior behavior could cross tenant boundaries.
- Delete paths now execute only against ids proven to belong to the active
  tenant and organization scope.
- Baseline child-table reads and deletes now respect scoped baseline ownership.
- Access-control repositories now scope project memberships through project
  ownership, scope generic grants by active tenant, and stamp
  `organization_id` / `tenant_id` on writes.
- Inventory repositories now use a shared scope helper for catalog, storeroom,
  balance, transaction, reservation, storage location, reorder policy, and
  cycle-count data.
- Procurement repositories now use scoped header access for requisitions,
  purchase orders, and receipts, with parent-aware tenant isolation on
  requisition lines, purchase-order lines, and receipt lines.
- Maintenance root repositories now use a shared scope helper for locations,
  systems, assets, sensors, integration sources, failure codes, task
  templates, work requests, work orders, and preventive plans.
- Maintenance secondary repositories now use parent-aware scope resolution for
  asset components, sensor readings, sensor source mappings, sensor exceptions,
  work-order execution records, task-step templates, preventive plan tasks,
  runtime plan instances, and downtime events.
- Remaining PM secondary repositories now use shared PM scope helpers for
  project resources, resource skills, certifications, task skill requirements,
  PM calendar assignments, and portfolio repositories.

### Tenant-aware settings

`AppSettingsStore` now stores organization-scoped UI state under a tenant key
even when no organization id is available:

- old fallback: bare key like `task/saved_views`
- new fallback: `tenant/__no_organization__/task/saved_views`

This prevents accidental cross-context reuse of cached workspace state.

### Controller and runtime follow-up

- `PlatformRuntimeApplicationService` now requires `settings.manage` before
  switching the session-scoped active organization.
- PM QML runtime lookups now use `platformRuntimeApi.get_runtime_context()`
  instead of the nonexistent `snapshot()` path exposed by the live desktop API.
- PM task saved views and table-column state now resolve organization-aware
  settings keys through the same runtime contract used by the shell.

### PM contract cleanup

- PM portfolio repositories now use scoped `get(...)`, `list(...)`, and
  `delete(...)` methods instead of the transitional
  `*_for_organization(...)` compatibility surface.
- PM project and resource callers now consume the repository-scoped `list()`
  contract directly.
- `PortfolioService` now requires `TenantContextService` at construction time
  instead of tolerating a missing context dependency.

### Constructor-time tenant context tightening

- Inventory/procurement application services now require an injected
  `TenantContextService` instead of silently constructing a fallback instance.
- Maintenance application services now follow the same fail-fast rule.
- `MaintenanceReportingService` and
  `MaintenanceTaskWorkAllocationRepository` now require the same explicit
  tenant-context dependency.
- Shared helper `require_tenant_context_service(...)` now centralizes the
  `TENANT_CONTEXT_REQUIRED` constructor failure used by these services.

### Repository constructor tightening

- Inventory/procurement repositories now require injected
  `TenantContextService` at construction time.
- Maintenance-owned repositories now require injected
  `TenantContextService` at construction time.
- `build_inventory_procurement_service_bundle(...)` now constructs scoped
  repositories with tenant context directly instead of mutating them
  afterward.
- `build_maintenance_service_bundle(...)` now does the same for
  maintenance-owned repositories, while still using a smaller compatibility
  loop for locally created platform repositories.

## Verification added

New or expanded coverage now checks:

- priority PM repositories hide rows from another organization
- priority PM repository mutations do not delete data from another organization
- priority PM repository updates reject cross-organization objects
- newly hardened dependency and task-presence repositories require
  `TenantContextService`
- access-control repositories do not return or delete foreign-scope rows
- access-control writes stamp scope metadata and reject foreign projects
- inventory repositories hide foreign organization rows and reject foreign
  parent procurement references
- maintenance root repositories require `TenantContextService`, hide foreign
  organization rows, and reject foreign root updates
- maintenance secondary repositories require `TenantContextService`, hide
  foreign rows, and reject cross-scope parent reassignments
- portfolio and remaining PM secondary repositories require
  `TenantContextService`, hide foreign rows, and reject cross-organization
  child writes
- unscoped tenant UI state is written to a namespaced key instead of a bare key
- runtime organization switching denies users missing `settings.manage`
- PM QML task-view and table-column state follow the live runtime-context API
  when resolving tenant-aware settings keys
- PM desktop fallback helpers and portfolio flows now use the scoped
  repository contract instead of explicit organization-id compatibility methods
- inventory and maintenance service constructors now raise
  `TENANT_CONTEXT_REQUIRED` when built without injected tenant context, while
  representative injected-path service suites continue to pass
- inventory/procurement and maintenance-owned repository constructors now raise
  `TENANT_CONTEXT_REQUIRED` when built without injected tenant context, while
  focused scoped-repository regression suites continue to pass

## Progress tracker

### Completed in this pass

- Audit existing docs versus live code
- Scan repository classes and tenant-scoping patterns across modules
- Harden the priority PM repository tranche
- Harden access-control repositories and add focused repo tests
- Harden inventory catalog, stock, and foundation repositories
- Harden procurement header and child-line repositories
- Harden maintenance tenant-root repositories
- Harden maintenance secondary repositories
- Harden portfolio and remaining PM secondary repositories
- Complete controller and settings follow-up for runtime org switching and PM
  cached workspace state
- Complete PM contract cleanup round 1 for scoped repository callers
- Complete inventory + maintenance constructor tightening round 1 for service
  layer dependencies
- Complete inventory + maintenance repository constructor tightening round 1
- Repair the duplicate Alembic Phase A revision by re-chaining the
  legacy-desktop backfill as its own follow-on migration
- Convert SQLite-unsafe tenant migration FK column adds into batch-mode
  add-column plus named foreign-key steps
- Add repository-focused regression tests
- Add this follow-up README
- Add tranche notes:
  - `docs/tenant_repository_hardening/platform_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/access_control_repository_hardening.md`
  - `docs/tenant_repository_hardening/inventory_repository_hardening_round_1.md`
  - `docs/tenant_repository_hardening/procurement_repository_hardening_round_1.md`
  - `docs/tenant_repository_hardening/procurement_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/maintenance_repository_hardening_round_1.md`
  - `docs/tenant_repository_hardening/maintenance_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/project_management_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/controller_settings_followup_round_1.md`
  - `docs/tenant_repository_hardening/project_management_contract_cleanup_round_1.md`
  - `docs/tenant_repository_hardening/inventory_maintenance_constructor_tightening_round_1.md`
  - `docs/tenant_repository_hardening/inventory_maintenance_repository_constructor_tightening_round_1.md`

### Next recommended batches

1. Platform + PM repository constructor tightening after the inventory and
   maintenance-owned repo slice
   - reduce post-build `_tenant_context_service` wiring where composition still
     mutates platform and PM repositories after construction
   - prefer constructor-time repo requirements in the remaining repository
     implementations that still rely on post-build injection

2. Non-PM contract cleanup follow-up
   - remove residual explicit-organization compatibility methods outside the PM
     slice once platform, inventory, and maintenance callers have moved to the
     scoped `list()` and `get()` contract

## Notes

- Alembic Phase A chain repaired on 2026-06-13:
  `src/infra/persistence/migrations/versions/t4u5v6w7x8z0_backfill_default_organization_for_legacy_desktop_data.py`
  now follows `t4u5v6w7x8y9` instead of reusing the same revision id.
- SQLite migration hardening on 2026-06-13:
  `x8y9z0a1b2c3_add_user_role_organization_scope.py` and
  `z0a1b2c3d4e5_add_tenant_id_to_organizations.py` now use batch-mode FK
  creation so desktop startup can migrate SQLite databases cleanly.
- Existing docs under `docs/TENANT_ISOLATION_EXECUTION_STATUS.md` and
  `docs/tenant_isolation_audit/README.md` still contain historical transition
  assumptions that do not fully match the current code. Keep this README as the
  practical follow-up log for the current hardening stream.
- Verified on 2026-06-13:
  - procurement repository + workflow suite: `31 passed`
  - desktop/import-export procurement integration checks: `2 passed`
  - maintenance repository + service suite: `38 passed`
  - maintenance desktop API suite: `10 passed`
  - broader maintenance secondary-repository verification suite: `74 passed`
  - PM secondary repository + calendar integration suite: `33 passed`
  - broader PM portfolio/project-resource regression suite: `21 passed`
  - platform runtime + PM QML settings follow-up suite: `40 passed`
  - PM contract cleanup round 1 suite: `37 passed`
  - inventory + maintenance constructor tightening round 1 suite: `92 passed`
  - inventory + maintenance repository constructor tightening round 1 suite: `77 passed`
