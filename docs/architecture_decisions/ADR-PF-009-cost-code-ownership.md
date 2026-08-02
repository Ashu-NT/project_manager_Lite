# ADR-PF-009: Cost-Code Ownership

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase B cost-code schema

## Context

Legacy `CostType` and `CostItem.code` do not form a true cost-code catalog. The proven need is project-cost classification, budgeting, planning, actuals, forecasts, and reporting. Procurement may carry a project cost-code reference, but the repository does not yet prove a shared organization-wide taxonomy used independently by Procurement, Inventory, and accounting integration.

## Decision

- Recommended current owner: Project Finance, using tenant/organization-scoped `ProjectCostCode` definitions plus project restrictions/mappings.
- Codes may be hierarchical, effective/active, and mapped to external accounting references.
- Procurement and other modules may carry a stable reference supplied by PM but do not mutate the catalog.
- Before schema acceptance, product must confirm whether one organization taxonomy is required across PM, Procurement, Inventory, and accounting. If proven, reopen this ADR and use organization-owned `OrganizationCostCode`; PM then owns project restrictions and mappings.
- Legacy `CostItem.code` is a line/legacy reference and never automatically becomes the new cost-code identity.

## Alternatives Rejected

- Generalize immediately to platform: no second proven semantic consumer.
- Keep fixed `CostType` only: cannot support hierarchy, effective state, tenant configuration, or mappings.
- Use WBS or GL account as cost code: conflates separate dimensions.

## Consequences

The API must distinguish cost-code identity from source line code, WBS, expense category, and external GL mapping.

## Migration Impact

Legacy type/code values require a reviewed mapping table. Unmapped values retain source metadata and enter a quarantine/default-review workflow rather than creating arbitrary catalog identities.

## Test Impact

Test hierarchy/cycles, scoped uniqueness, effective/active behavior, project restrictions, cross-tenant references, external mappings, and legacy mapping determinism.
