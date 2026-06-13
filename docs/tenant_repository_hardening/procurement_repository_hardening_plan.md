# Procurement Repository Hardening Plan

## Why this tranche is next

The inventory module now has tenant-aware scoping on its catalog, stock, and
foundation repositories. The next isolation boundary inside the same module is
the procurement layer, because it still owns organization-root records that can
cross tenant boundaries if repositories rely on raw primary-key access.

This tranche is the natural continuation before maintenance because:

- procurement repositories are built in the same `inventory_registry.py`
  composition bundle as the already-hardened inventory repositories
- procurement services reuse the same tenant context and organization-aware
  service flow
- requisitions, purchase orders, and receipts are top-level business records
  with subordinate line rows, so they need both root scoping and parent-child
  scoping

## Current architecture map

### Root procurement repositories

These repositories already expose a familiar pre-hardening pattern:

- `SqlAlchemyPurchaseRequisitionRepository`
- `SqlAlchemyPurchaseOrderRepository`
- `SqlAlchemyReceiptHeaderRepository`

From the earlier code scan, they already:

- carry `_tenant_context_service`
- stamp `tenant_id` on add when missing
- query `organization_id` in `get_by_number(...)` and
  `list_for_organization(...)`
- use raw `session.get(...)` for primary-key reads
- rely on tenant filtering only after fetching the row

That makes them structurally similar to the inventory repositories before round
1 hardening.

### Child line repositories

These repositories appear to be subordinate to procurement roots:

- `SqlAlchemyPurchaseRequisitionLineRepository`
- `SqlAlchemyPurchaseOrderLineRepository`
- `SqlAlchemyReceiptLineRepository`

From the earlier scan, they use raw `session.get(...)` for line access. The
important design difference is that child-line records usually inherit scope
from their parent requisition, purchase order, or receipt header rather than
from their own independent organization root.

That means their hardening should probably not be a blind copy of the root
repository pattern.

## Deep understanding of the scope model

### Requisition, purchase order, and receipt headers are tenant roots

These records are direct business documents. They should behave like other
tenant-root repositories:

- require an active organization context for repository operations
- scope `get(...)` by active organization and tenant
- treat foreign-organization `get_by_number(...)` and
  `list_for_organization(...)` calls as `None` or `[]`
- stamp missing `organization_id` and `tenant_id` from the active context on
  writes
- reject updates to rows that are outside the active organization scope before
  optimistic locking proceeds
- make delete behavior a no-op for foreign rows

### Procurement lines inherit scope from their parent document

The line repositories need a slightly richer model:

- line rows should only be visible if their parent requisition, purchase order,
  or receipt header is visible in the active scope
- direct `get(line_id)` access should be validated through the parent document,
  not just through the line primary key
- line adds should only succeed when the parent document is accessible in the
  active organization scope
- line delete and update behavior should no-op or fail safely when the parent
  belongs to another organization

If the line ORM tables do not carry `organization_id` or `tenant_id` directly,
the safest implementation will be parent-join scoping rather than local-column
scoping.

## Service-path understanding

The procurement repositories are not isolated utilities; they sit under active
workflow services.

### Procurement service path

`ProcurementService` is the main requisition lifecycle boundary. It uses:

- the requisition root repository
- the requisition line repository
- inventory and item services for validating storerooms and materials
- approval integration for submission workflow

This means repository hardening must preserve normal requisition authoring and
submission flows while hiding foreign requisitions and requisition lines.

### Purchasing service path

`PurchasingService` uses:

- the purchase order root repository
- the purchase order line repository
- the receipt header repository
- the receipt line repository
- requisition repositories for upstream sourcing
- stock balance integration for receiving effects

This is more interconnected than the inventory root tranche, so the root
repositories should be hardened first and the line repositories should follow
with parent-aware scoping once their exact ORM shape is re-read.

## Recommended implementation order

1. Harden procurement root repositories
   - `SqlAlchemyPurchaseRequisitionRepository`
   - `SqlAlchemyPurchaseOrderRepository`
   - `SqlAlchemyReceiptHeaderRepository`
2. Re-read and harden child-line repositories with parent-aware scoping
   - `SqlAlchemyPurchaseRequisitionLineRepository`
   - `SqlAlchemyPurchaseOrderLineRepository`
   - `SqlAlchemyReceiptLineRepository`
3. Add focused repository tests for both root and child behavior
4. Re-run existing procurement workflow tests

## Expected implementation pattern

### Root repositories

Reuse the same inventory helper style already introduced in:

- `catalog.py`
- `inventory.py`

Expected changes:

- inherit from `InventoryTenantScopedRepositorySupport`
- replace raw `session.get(...)` with scoped helper reads
- short-circuit foreign `organization_id` calls
- require visible rows before optimistic updates

### Child repositories

Likely introduce a procurement-specific parent scope helper, or at minimum a
small internal helper pattern that:

- resolves the parent header row
- ensures the parent is visible within the active tenant context
- only then reads, writes, updates, or deletes the child line

## Test strategy

### Repository hardening tests

Add a focused procurement tenant-hardening suite that verifies:

- root repositories require `TenantContextService`
- foreign requisitions, purchase orders, and receipts are hidden from `get(...)`
- foreign `get_by_number(...)` and `list_for_organization(...)` calls return no
  data
- child lines under foreign parent documents are inaccessible
- delete operations do not mutate foreign rows

### Regression tests to re-run

When shell execution is available again, the first verification pass should
include:

- `src/tests/inventory_procurement/test_repository_tenant_hardening.py`
- `src/tests/inventory_procurement/test_inventory_procurement_foundation.py`
- procurement workflow tests such as the existing requisition and purchasing
  suites

## Open verification questions

Once shell reads are stable again, confirm these details before editing:

- whether procurement line ORM tables carry `organization_id` and/or `tenant_id`
- which child repository methods exist beyond `get(...)` and `add/update`
- whether receipts and purchase order lines are always addressed through parent
  identifiers in the application layer
- whether delete methods exist on the procurement roots and lines and need the
  same no-op-on-foreign protection used elsewhere

## Current blocker

Fresh code re-reading and pytest execution are temporarily blocked by the local
shell harness returning `windows sandbox: spawn setup refresh`. This note keeps
the architectural understanding and next implementation strategy explicit so the
next active coding pass can start from a clean, shared plan.
