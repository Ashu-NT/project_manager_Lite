# Next Tenant Hardening Tranches

## Current state

- Platform repository hardening rounds are completed.
- Project management repository hardening rounds are completed.
- Access-control repository hardening is completed.
- Inventory repository hardening round 1 is implemented:
  - catalog roots
  - storeroom and stock roots
  - storage location, reorder policy, and cycle count repositories
- Procurement repository hardening round 1 is implemented and verified:
  - requisition roots
  - purchase order roots
  - receipt header roots
- Procurement repository hardening round 2 is implemented and verified:
  - requisition lines
  - purchase-order lines
  - receipt lines
- Maintenance tenant-root repository hardening round 1 is implemented and verified:
  - locations
  - systems
  - assets
  - sensors
  - integration sources
  - failure codes
  - task templates
  - work requests
  - work orders
  - preventive plans

## Next implementation order

1. Maintenance secondary repositories
   - `docs/tenant_repository_hardening/maintenance_repository_hardening_round_1.md`
2. Portfolio and remaining PM secondary repositories
3. Controller and settings follow-up

## Execution notes

- Reuse the same `TenantScopedRepositorySupport` style already applied in
  platform, access-control, project-management, inventory, procurement, and
  maintenance root repositories.
- Require active organization context for repository reads and writes.
- Scope `get(...)`, `get_by_*`, list, and delete behavior so foreign rows return
  `None` or `[]` and are not mutated.
- Stamp missing `organization_id` and `tenant_id` metadata from the active
  tenant context on writes.
- Add focused repository hardening tests for each tranche and append the
  verification outcome to the tranche-specific doc under
  `docs/tenant_repository_hardening/`.
