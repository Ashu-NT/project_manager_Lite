# Procurement Repository Hardening Round 2

## Scope completed

This tranche hardens the procurement child-line repositories with
parent-aware tenant scoping:

- `SqlAlchemyPurchaseRequisitionLineRepository`
- `SqlAlchemyPurchaseOrderLineRepository`
- `SqlAlchemyReceiptLineRepository`

## Enterprise hardening applied

- Added parent-join scoping for child-line reads so line visibility is derived
  from the active-scope parent document rather than from raw primary-key access.
- Child repositories now require `TenantContextService` and fail fast when they
  are used outside an active organization context.
- `get(...)` paths now hide foreign lines by joining through:
  - requisition line -> purchase requisition
  - purchase order line -> purchase order
  - receipt line -> receipt header
- `list_for_*` paths now return only lines whose parent document is visible in
  the active organization scope.
- Child `add(...)` paths now reject foreign parent references:
  - requisition lines require an in-scope requisition
  - purchase-order lines require an in-scope purchase order
  - receipt lines require an in-scope receipt header
- Cross-document references are also protected:
  - purchase-order lines reject foreign requisition-line references
  - receipt lines reject foreign purchase-order-line references
- `inventory_registry.py` now injects `TenantContextService` into the
  procurement line repositories so the service graph uses the same scoped
  behavior everywhere.

## Coverage added

`src/tests/inventory_procurement/test_repository_tenant_hardening.py` now
verifies:

- procurement line repositories require `TenantContextService`
- foreign requisition, purchase-order, and receipt lines are hidden from
  `get(...)`
- parent-scoped line listing returns no foreign rows
- child repositories reject foreign parent or foreign source-line references

## Verification follow-up

- Focused verification command:
  - `conda run -n pmenv python -m pytest -q src/tests/inventory_procurement/test_repository_tenant_hardening.py src/tests/inventory_procurement/test_inventory_procurement_requisition.py src/tests/inventory_procurement/test_inventory_procurement_purchasing.py`

## Next step

- Run the focused procurement verification suite.
- After procurement verification is green, continue to the maintenance
  tenant-root repository tranche.
