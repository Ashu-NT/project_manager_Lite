# Maintenance Repository Hardening Round 1

## Scope completed

This tranche hardens the maintenance tenant-root repositories:

- `SqlAlchemyMaintenanceLocationRepository`
- `SqlAlchemyMaintenanceSystemRepository`
- `SqlAlchemyMaintenanceAssetRepository`
- `SqlAlchemyMaintenanceSensorRepository`
- `SqlAlchemyMaintenanceIntegrationSourceRepository`
- `SqlAlchemyMaintenanceFailureCodeRepository`
- `SqlAlchemyMaintenanceTaskTemplateRepository`
- `SqlAlchemyMaintenanceWorkRequestRepository`
- `SqlAlchemyMaintenanceWorkOrderRepository`
- `SqlAlchemyMaintenancePreventivePlanRepository`

## Enterprise hardening applied

- Added `MaintenanceTenantScopedRepositorySupport` so maintenance roots follow
  the same scoped repository pattern already used in platform and inventory.
- Root repositories now require `TenantContextService` and fail fast when they
  are used outside an active organization context.
- `add(...)` paths now stamp missing `organization_id` and `tenant_id` values
  from the active tenant context and reject out-of-scope writes.
- `get(...)`, `get_by_code(...)`, and `list_for_organization(...)` paths now
  resolve only rows inside the active organization scope.
- Root `update(...)` paths now reject foreign-organization rows before running
  optimistic concurrency updates.
- `maintenance_registry.py` now wires tenant context into the full maintenance
  repository bundle, including newly scoped maintenance roots and the
  maintenance document-link repository instance used by the service graph.

## Coverage added

`src/tests/maintenance/test_repository_tenant_hardening.py` now verifies:

- maintenance root repositories require `TenantContextService`
- foreign maintenance root rows are hidden from `get(...)`
- foreign organization reads return `None` or `[]`
- cross-organization root updates raise `NotFoundError`

## Verification

- Focused maintenance repository + service verification:
  - `conda run -n pmenv python -m pytest -q src/tests/maintenance/test_repository_tenant_hardening.py src/tests/maintenance/test_maintenance_persistence.py src/tests/maintenance/test_maintenance_document_service.py src/tests/maintenance/test_maintenance_preventive_generation.py src/tests/maintenance/test_maintenance_reporting.py`
  - result: `38 passed`
- Maintenance desktop API verification:
  - `conda run -n pmenv python -m pytest -q src/tests/maintenance/test_maintenance_desktop_api.py`
  - result: `10 passed`

## Next step

- Continue with maintenance secondary repositories that inherit scope through
  parent roots:
  - asset components
  - sensor readings, source mappings, and exceptions
  - work-order tasks, task steps, and material requirements
  - task-step templates, plan tasks, runtime plan instances, and downtime
    events
