# Inventory + Maintenance Constructor Tightening Round 1

Date: 2026-06-13

## Scope

This tranche tightened constructor-time tenant context requirements across the
inventory/procurement and maintenance service layer outside the already
completed project-management slice.

- Inventory/procurement services now fail fast when `TenantContextService` is
  not injected:
  - `ItemCategoryService`
  - `ItemMasterService`
  - `InventoryService`
  - `InventoryFoundationService`
  - `StockControlService`
  - `ReservationService`
  - `ProcurementService`
  - `PurchasingService`
- Maintenance services now fail fast when `TenantContextService` is not
  injected:
  - asset, component, location, system, document, preventive, reliability,
    work-request, work-order, work-order task, work-order task step, and
    material-requirement services
- Maintenance reporting and labor-allocation seams now follow the same rule:
  - `MaintenanceReportingService`
  - `MaintenanceTaskWorkAllocationRepository`

## Implementation notes

- Added shared helper `require_tenant_context_service(...)` under
  `src/core/platform/tenancy/tenant_context.py`.
- Replaced silent fallback construction
  `tenant_context_service or TenantContextService(...)` with explicit
  `TENANT_CONTEXT_REQUIRED` failures.
- Kept the runtime wiring aligned with the current composition registries, which
  already inject `platform_services.tenant_context_service` into these
  constructors.
- Added focused constructor regression tests for both modules.
- Updated the maintenance reliability test stub `_OrgRepo` so it satisfies the
  current `OrganizationRepository` contract during verification.

## Verification

Verified with:

```powershell
C:\Users\ashuf\miniconda3\Scripts\conda.exe run -n pmenv python -m pytest -q src/tests/inventory_procurement/test_service_constructor_requirements.py src/tests/inventory_procurement/test_inventory_procurement_foundation.py src/tests/inventory_procurement/test_inventory_procurement_reservations.py src/tests/inventory_procurement/test_inventory_procurement_purchasing.py src/tests/maintenance/test_service_constructor_requirements.py src/tests/maintenance/test_maintenance_document_service.py src/tests/maintenance/test_maintenance_execution_foundation.py src/tests/maintenance/test_maintenance_foundation.py src/tests/maintenance/test_maintenance_integration_foundation.py src/tests/maintenance/test_maintenance_labor_booking.py src/tests/maintenance/test_maintenance_phase4_foundation.py src/tests/maintenance/test_maintenance_preventive_foundation.py src/tests/maintenance/test_maintenance_preventive_generation.py src/tests/maintenance/test_maintenance_reliability_analytics.py src/tests/maintenance/test_maintenance_reliability_foundation.py src/tests/maintenance/test_maintenance_reporting.py src/tests/maintenance/test_maintenance_sensor_foundation.py
```

Result:

- `92 passed`
- `33 warnings`

Known warnings are existing `datetime.utcnow()` deprecation warnings in
`src/core/platform/calendar/application/enterprise_calendar_service.py`.
