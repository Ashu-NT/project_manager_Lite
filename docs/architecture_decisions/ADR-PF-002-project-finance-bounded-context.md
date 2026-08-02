# ADR-PF-002: Project Finance Bounded Context

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase A2 and Phase B

## Context

The current finance implementation is under Project Management and directly depends on Project, Task, Resource, scheduling, and reporting. Shared Organization, Time, Party, Approval, Audit, and Procurement capabilities already have valid owners. Moving all financial concepts to a platform module would create a finance dumping ground; keeping universal monetary primitives in PM would duplicate them.

## Decision

- Project Finance remains a subdomain of the Project Management bounded context.
- PM owns ProjectFinancialProfile, ProjectCostCode under ADR-PF-009, ProjectRateCard policy, budgets, planned costs, commitment projections, project actuals, forecasts, changes, billing preparation, profitability, and project financial reporting.
- Platform finance owns only dependency-free Money/Currency/Quantity/Rate/Rounding and later shared FX/period primitives when justified.
- Time owns approved hours; Procurement owns requisitions/POs/receipts; Party owns identities; Approval and Audit remain platform capabilities.
- Official invoices, payments, reimbursement, tax, and general-ledger accounting remain external or future bounded-context responsibilities.
- Cross-module communication uses stable contracts/events and IDs. No module imports another module's repository or mutates another aggregate.
- Desktop/QML contracts follow application/domain contracts and may be replaced when the backend model changes.

## Alternatives Rejected

- A standalone accounting application in this repository: outside present product scope.
- A broad platform finance domain containing project behavior: violates dependency and ownership boundaries.
- Procurement or Time directly writing PM finance tables: bypasses aggregate policy and tenant controls.

## Consequences

Application orchestration coordinates cross-module facts without transferring ownership. Reporting may denormalize snapshots but cannot become an authority. Shared primitives must pass architecture tests proving no PM imports.

## Migration Impact

Existing PM finance paths evolve in place. Source references replace direct cross-module scans. No immediate physical package relocation is required.

## Test Impact

Add architecture/import-boundary tests, contract tests for Time/Procurement integrations, and tests proving external modules cannot mutate PM finance aggregates.
