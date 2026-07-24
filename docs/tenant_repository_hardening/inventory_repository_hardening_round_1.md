# Inventory Repository Hardening Round 1

## Scope completed

This tranche applies the shared tenant-aware repository pattern to the core
inventory and catalog repositories that are directly responsible for
organization-root inventory records:

- `catalog.py`
  - `SqlAlchemyInventoryItemCategoryRepository`
  - `SqlAlchemyStockItemRepository`
- `inventory.py`
  - `SqlAlchemyStoreroomRepository`
  - `SqlAlchemyStockBalanceRepository`
  - `SqlAlchemyStockTransactionRepository`
  - `SqlAlchemyStockReservationRepository`
  - `SqlAlchemyStorageLocationRepository`
  - `SqlAlchemyReorderPolicyRepository`
  - `SqlAlchemyCycleCountRepository`

## Enterprise hardening applied

- Added a shared `InventoryTenantScopedRepositorySupport` helper so inventory
  repositories now follow the same organization-context requirement used in the
  hardened platform and access-control repositories.
- Repository reads by primary key are now scoped by active organization and, if
  present on the ORM model, by active tenant.
- Repository `get_by_*` and `list_for_organization(...)` queries now short-cut
  to `None` or `[]` when callers pass an organization outside the active scope.
- Repository writes now stamp missing `organization_id` and `tenant_id` values
  from the active context and reject attempts to write rows outside the active
  scope.
- `update(...)` paths now require the target row to be visible inside the
  active organization scope before the optimistic-locking update proceeds.
- `inventory_registry.py` now injects `TenantContextService` into
  `StorageLocation`, `ReorderPolicy`, and `CycleCount` repositories in addition
  to the already-wired inventory roots.

## Coverage added

- `src/tests/inventory_procurement/test_repository_tenant_hardening.py`
  verifies:
  - repositories fail fast without `TenantContextService`
  - foreign-organization inventory rows are hidden from `get(...)`
  - foreign-organization lookups and list queries return empty results

## Verification follow-up

- Focused verification command for the tranche:
  - `conda run -n pmenv python -m pytest -q src/tests/inventory_procurement/test_repository_tenant_hardening.py src/tests/inventory_procurement/test_inventory_procurement_foundation.py`
- Verification was deferred at the end of the implementation turn because the
  shell harness was returning `windows sandbox: spawn setup refresh` before the
  pytest run could start.

## Remaining follow-up

- Procurement tenant-root repositories still need the same repository-scope
  pass:
  - `SqlAlchemyPurchaseRequisitionRepository`
  - `SqlAlchemyPurchaseOrderRepository`
  - `SqlAlchemyReceiptHeaderRepository`
- Inventory child-line repositories should be reviewed after the procurement
  roots are hardened.
- Maintenance tenant-root repositories remain the next major module-level
  tranche after the remaining inventory/procurement roots.
