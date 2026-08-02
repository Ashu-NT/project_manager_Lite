# ADR-PF-009: Cost-Code Ownership

- Status: accepted; Phase B1 foundation implemented
- Date: 2026-08-02
- Implementation gate: Phase B cost-code schema

## Context

Legacy `CostType` and `CostItem.code` do not form a true cost-code catalog. The proven need is project-cost classification, budgeting, planning, actuals, forecasts, and reporting. Procurement may carry a project cost-code reference, but the repository does not yet prove a shared organization-wide taxonomy used independently by Procurement, Inventory, and accounting integration.

## Decision

- Project Finance owns tenant/organization-scoped `ProjectCostCode` definitions plus project restrictions/mappings.
- Codes may be hierarchical, effective/active, and mapped to external accounting references.
- Procurement and other modules may carry a stable reference supplied by PM but do not mutate the catalog.
- Repository evidence at acceptance shows no independent Procurement, Inventory, or accounting catalog owner. Reopen this ADR only if a genuine organization-wide taxonomy with a second semantic owner is introduced; do not generalize based on a possible future consumer.
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

## Acceptance Evidence

Phase B1 implements the accepted boundary as `project_finance_cost_codes` and `project_finance_cost_code_restrictions`, both with direct non-null tenant/organization ownership, scoped foreign keys, forced PostgreSQL RLS policy setup, service-level cycle/effective-state rules, global plus project-scoped RBAC, optimistic updates, and fail-closed financial audit. Legacy `CostItem.code` and `CostType` remain outside the canonical catalog; no automatic identity mapping or temporary catalog adapter was added.
