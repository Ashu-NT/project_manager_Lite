# Procurement Repository Hardening Round 1

## Scope completed

This first procurement tranche applies the tenant-aware root repository pattern
to the top-level procurement document repositories:

- `SqlAlchemyPurchaseRequisitionRepository`
- `SqlAlchemyPurchaseOrderRepository`
- `SqlAlchemyReceiptHeaderRepository`

The child-line repositories are intentionally left for the next procurement
pass because they inherit scope from their parent documents and need
parent-aware scoping instead of simple root-column scoping.

## Changes applied

- Root procurement repositories now inherit from
  `InventoryTenantScopedRepositorySupport`.
- Primary-key reads are being routed through scoped helper access instead of
  unscoped `session.get(...)`.
- `get_by_number(...)` and `list_for_organization(...)` flows now short-circuit
  when the requested organization is outside the active scope.
- Root `add(...)` paths now stamp missing `organization_id` and `tenant_id`
  values from the active tenant context.
- Root `update(...)` protection has been added where the repository already had
  a normal update path and the visible row can be checked before optimistic
  locking proceeds.

## Why lines were deferred

The repository split matters:

- requisitions, purchase orders, and receipt headers are organization-root
  business records
- requisition lines, purchase order lines, and receipt lines are subordinate
  records whose scope should be validated through their parent document

That means the next round should harden child repositories by joining or
resolving through the parent header rows rather than by assuming the line table
is independently scoping itself correctly.

## Verification status

- Automated verification is still pending.
- The local shell harness is still returning
  `windows sandbox: spawn setup refresh`, so this pass has not yet been
  confirmed with pytest.

## Next step

The immediate next implementation pass is:

1. verify this procurement root tranche with focused tests
2. harden procurement child-line repositories with parent-aware scoping
3. continue to maintenance tenant-root repositories
