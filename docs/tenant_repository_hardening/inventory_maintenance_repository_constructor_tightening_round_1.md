# Inventory + Maintenance Repository Constructor Tightening Round 1

Date: 2026-06-13

## Scope

This tranche moved inventory/procurement repositories and maintenance-owned
repositories from post-build tenant-context mutation to constructor-time
requirements.

- Inventory/procurement repositories now require injected
  `TenantContextService` at construction:
  - catalog repositories
  - storeroom, balance, transaction, reservation, storage location, reorder
    policy, and cycle count repositories
  - requisition, purchase-order, and receipt repositories
- Maintenance-owned repositories now require injected
  `TenantContextService` at construction:
  - root repositories
  - parent-scoped secondary repositories
  - preventive runtime plan-instance repository
  - reliability repositories

## Implementation notes

- Reused the shared `require_tenant_context_service(...)` helper under
  `src/core/platform/tenancy/tenant_context.py`.
- Inventory/procurement repository constructors now fail fast instead of being
  patched in `build_inventory_procurement_service_bundle(...)` after creation.
- Maintenance-owned repository constructors now fail fast instead of relying on
  the broad post-build mutation loop in `build_maintenance_service_bundle(...)`.
- Removed the inventory/procurement registry loop entirely.
- Reduced the maintenance registry loop to the remaining platform repositories
  it still creates locally:
  - document repositories
  - user repository
  - employee repository
  - time repositories
- Updated repository hardening tests to inject tenant context through
  constructors and to assert missing-context failures at construction time.

## Verification

Verified with:

```powershell
C:\Users\ashuf\miniconda3\Scripts\conda.exe run -n pmenv python -m pytest -q src/tests/inventory_procurement/test_repository_tenant_hardening.py src/tests/inventory_procurement/test_service_constructor_requirements.py src/tests/maintenance/test_repository_tenant_hardening.py src/tests/maintenance/test_service_constructor_requirements.py
```

Result:

- `77 passed`
- `8 warnings`

Known warnings are existing `datetime.utcnow()` deprecation warnings in
`src/core/platform/calendar/application/enterprise_calendar_service.py`.
