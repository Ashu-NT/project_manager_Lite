# Next Tenant Hardening Tranches

## Current state

- Platform repository hardening rounds are completed.
- Project management repository hardening rounds are completed.
- Access-control repository hardening is completed.
- Inventory repository hardening round 1 is implemented:
  - catalog roots
  - storeroom and stock roots
  - storage location, reorder policy, and cycle count repositories
- Procurement repository hardening round 1 is implemented:
  - requisition roots
  - purchase order roots
  - receipt header roots
  - verification still pending
- Procurement repository hardening round 2 is implemented:
  - requisition lines
  - purchase-order lines
  - receipt lines
  - verification still pending

## Next implementation order

1. Procurement verification pass
   - `docs/tenant_repository_hardening/procurement_repository_hardening_round_1.md`
   - `docs/tenant_repository_hardening/procurement_repository_hardening_round_2.md`
   - design note: `docs/tenant_repository_hardening/procurement_repository_hardening_plan.md`
2. Maintenance tenant-root repositories
3. Portfolio and remaining PM secondary repositories
4. Controller and settings follow-up

## Execution notes

- Reuse the same `TenantScopedRepositorySupport` style already applied in
  platform, access-control, project-management, and inventory repositories.
- Require active organization context for repository reads and writes.
- Scope `get(...)`, `get_by_*`, list, and delete behavior so foreign rows return
  `None` or `[]` and are not mutated.
- Stamp missing `organization_id` and `tenant_id` metadata from the active
  tenant context on writes.
- Add focused repository hardening tests for each tranche and append the outcome
  to the tranche-specific doc under `docs/tenant_repository_hardening/`.
