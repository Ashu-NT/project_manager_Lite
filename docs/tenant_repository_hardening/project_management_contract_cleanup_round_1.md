# Project Management Contract Cleanup Round 1

Date: 2026-06-13

## Scope completed

This tranche removes the remaining project-management repository compatibility
methods that still threaded explicit `organization_id` values through code that
already runs behind active tenant and organization scope:

- portfolio intake, scenario, dependency, and scoring-template repositories
- project and resource repository callers in PM services and desktop fallbacks
- PM collaboration and portfolio helper flows that still depended on
  `list_for_organization(...)`, `get_for_organization(...)`, or
  `delete_for_organization(...)`

## Enterprise hardening applied

- PM portfolio repositories now expose only scoped `get(...)`, `list(...)`, and
  `delete(...)` operations for active-context reads and mutations.
- PM project and resource repositories no longer carry the transitional
  `list_for_organization(...)` compatibility wrapper.
- Portfolio service mixins, collaboration support, portfolio resource-pool
  analysis, and desktop fallback helpers now rely on the repository-scoped
  contract directly instead of re-supplying the active organization id.
- `PortfolioService` now fails fast when `TenantContextService` is missing, so
  the service contract matches the tenant-aware behavior it already requires at
  runtime.

## Coverage added

- `src/tests/project_management/test_repository_tenant_hardening.py`
  - portfolio secondary repositories still hide foreign rows and no-op foreign
    deletes through the scoped `get/list/delete` contract
  - tenant-context requirements are asserted through the updated scoped methods
- `src/tests/project_management/test_tenant_isolation_services.py`
  - `PortfolioService` now explicitly requires `TenantContextService`
- `src/tests/project_management/test_project_management_desktop_api.py`
  - task/project/resource desktop fallback helpers still work when they fall
    back to repository-scoped reads

## Verification

- Focused PM contract-cleanup verification:
  - `conda run -n pmenv python -m pytest -q src/tests/project_management/test_repository_tenant_hardening.py src/tests/project_management/test_tenant_isolation_services.py src/tests/project_management/test_project_management_desktop_api.py`
  - result: `37 passed`

## Next step

- Continue with constructor-time tenant-context tightening in the remaining
  inventory, maintenance, and platform services and repositories that still
  rely on optional fallback context creation or post-build wiring.
