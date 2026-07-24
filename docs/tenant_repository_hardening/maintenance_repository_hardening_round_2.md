# Maintenance Repository Hardening Round 2

## Scope completed

This tranche hardens the maintenance secondary repositories that inherit tenant
or organization scope through parent maintenance records:

- `SqlAlchemyMaintenanceAssetComponentRepository`
- `SqlAlchemyMaintenanceSensorReadingRepository`
- `SqlAlchemyMaintenanceSensorSourceMappingRepository`
- `SqlAlchemyMaintenanceSensorExceptionRepository`
- `SqlAlchemyMaintenanceWorkOrderTaskRepository`
- `SqlAlchemyMaintenanceWorkOrderTaskStepRepository`
- `SqlAlchemyMaintenanceWorkOrderMaterialRequirementRepository`
- `SqlAlchemyMaintenanceTaskStepTemplateRepository`
- `SqlAlchemyMaintenancePreventivePlanTaskRepository`
- `SqlAlchemyMaintenancePreventivePlanInstanceRepository`
- `SqlAlchemyMaintenanceDowntimeEventRepository`

## Enterprise hardening applied

- Added `MaintenanceParentScopedRepositorySupport` so child repositories can
  join through their authoritative maintenance parent before returning or
  mutating a row.
- Secondary repositories now require `TenantContextService` instead of allowing
  effectively unscoped `get(...)` or list behavior.
- Parent-aware `add(...)` and `update(...)` paths now validate referenced
  assets, sensors, work orders, task templates, preventive plans, and runtime
  work-generation links before writing.
- `get(...)`, `get_by_code(...)`, `get_by_generated_work_order_id(...)`, and
  `list_for_organization(...)` paths now hide foreign rows by resolving through
  the scoped parent graph.
- Conditional-anchor repositories now validate every populated scope anchor
  before exposing data:
  - sensor exceptions validate sensor, mapping, and integration-source links
  - downtime events validate work-order, asset, and system links
- Preventive plan instance deletes now no-op outside the active scoped plan
  graph instead of trusting a raw instance id.

## Coverage added

`src/tests/maintenance/test_repository_tenant_hardening.py` now verifies:

- maintenance secondary repositories require `TenantContextService`
- foreign secondary rows are hidden from `get(...)`
- foreign organization list calls return `[]`
- cross-organization secondary updates raise `NotFoundError`
- cross-scope parent reassignments are rejected before optimistic updates run

## Verification

- Focused maintenance repository hardening verification:
  - `conda run -n pmenv python -m pytest -q src/tests/maintenance/test_repository_tenant_hardening.py`
  - result: `26 passed`
- Broader maintenance workflow verification:
  - `conda run -n pmenv python -m pytest -q src/tests/maintenance/test_repository_tenant_hardening.py src/tests/maintenance/test_maintenance_persistence.py src/tests/maintenance/test_maintenance_integration_foundation.py src/tests/maintenance/test_maintenance_execution_foundation.py src/tests/maintenance/test_maintenance_phase4_foundation.py src/tests/maintenance/test_maintenance_preventive_foundation.py src/tests/maintenance/test_maintenance_preventive_generation.py src/tests/maintenance/test_maintenance_preventive_scheduling.py src/tests/maintenance/test_maintenance_reporting.py src/tests/maintenance/test_maintenance_desktop_api.py`
  - result: `74 passed`

## Next step

- Continue with portfolio and remaining project-management secondary
  repositories that still rely on transitional organization-only list methods
  or raw-id update paths.
