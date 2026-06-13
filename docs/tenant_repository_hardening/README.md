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
- Maintenance root repositories now use a shared scoped repository helper, but
  several maintenance secondary repositories still use older organization-only
  or parent-trusting patterns.
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
  layout, and table column state, but unscoped fallback keys still needed an
  enterprise-safe namespace.

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
- Portfolio repositories still carry legacy `get_for_organization()` /
  `list_for_organization()` transitional APIs and some unscoped `get()` /
  `delete()` behavior.
- UI and controller follow-up is still needed for organization switching and
  tenant-aware settings behavior outside the PM repository tranche.

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

### Tenant-aware settings

`AppSettingsStore` now stores organization-scoped UI state under a tenant key
even when no organization id is available:

- old fallback: bare key like `task/saved_views`
- new fallback: `tenant/__no_organization__/task/saved_views`

This prevents accidental cross-context reuse of cached workspace state.

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
- unscoped tenant UI state is written to a namespaced key instead of a bare key

## Progress tracker

### Completed in this pass

- Audit existing docs versus live code
- Scan repository classes and tenant-scoping patterns across modules
- Harden the priority PM repository tranche
- Harden access-control repositories and add focused repo tests
- Harden inventory catalog, stock, and foundation repositories
- Harden procurement header and child-line repositories
- Harden maintenance tenant-root repositories
- Add repository-focused regression tests
- Add this follow-up README
- Add tranche notes:
  - `docs/tenant_repository_hardening/platform_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/access_control_repository_hardening.md`
  - `docs/tenant_repository_hardening/inventory_repository_hardening_round_1.md`
  - `docs/tenant_repository_hardening/procurement_repository_hardening_round_1.md`
  - `docs/tenant_repository_hardening/procurement_repository_hardening_round_2.md`
  - `docs/tenant_repository_hardening/maintenance_repository_hardening_round_1.md`

### Next recommended batches

1. Maintenance secondary repositories
   - add parent-aware scoping to child repositories that inherit organization
     and tenant boundaries from maintenance root records
   - tighten secondary update/delete paths that still trust raw ids

2. Portfolio and PM secondary repositories
   - remove residual legacy compatibility methods once all callers have moved
     to the scoped `list()` and `get()` contract
   - harden `ProjectResourceRepository` and portfolio dependency flows

3. Controller and settings follow-up
   - review organization switching permissions end-to-end
   - audit any remaining organization-scoped settings or caches

## Notes

- There is an untracked migration file in the working tree:
  `src/infra/persistence/migrations/versions/t4u5v6w7x8y9_backfill_default_organization_for_legacy_desktop_data.py`
- Existing docs under `docs/TENANT_ISOLATION_EXECUTION_STATUS.md` and
  `docs/tenant_isolation_audit/README.md` still contain historical transition
  assumptions that do not fully match the current code. Keep this README as the
  practical follow-up log for the current hardening stream.
- Verified on 2026-06-13:
  - procurement repository + workflow suite: `31 passed`
  - desktop/import-export procurement integration checks: `2 passed`
  - maintenance repository + service suite: `38 passed`
  - maintenance desktop API suite: `10 passed`
