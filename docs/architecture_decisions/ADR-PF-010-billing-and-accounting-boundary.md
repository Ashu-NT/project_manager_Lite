# ADR-PF-010: Billing and Accounting Boundary

- Status: accepted
- Date: 2026-08-02
- Accepted: 2026-08-11
- Implementation gate: Phase E

## Context

PM invoicing/revenue packages and QML invoice views are placeholders. The repository has no official customer invoice, payment, tax, revenue-recognition, or general-ledger aggregate. Project Finance still needs billable-source selection, billing preparation, project revenue projections, profitability, and external reconciliation.

## Decision

> Project Finance owns the commercial and managerial financial view of project execution. Accounting owns statutory and receivables truth. PM may prepare, project, reconcile, and display external accounting outcomes, but it may never manufacture those authoritative accounting records itself.

- PM owns Project billing configuration/schedules, billable source eligibility, `ProjectBillingPreparation`, approval, duplicate-selection prevention, contract-value projections, and project profitability read models.
- A future Billing/Accounting module or external system owns official invoice numbers/documents, tax, receivables, payments, statutory revenue recognition, and GL posting.
- PM sends approved billing preparations through an idempotent contract and stores external acknowledgement, invoice reference, status snapshot, and reconciliation reference.
- External invoice/payment updates are projections in PM and cannot be edited as authoritative records.
- Only billing methods explicitly accepted by product are implemented; placeholder QML does not define scope.

## Accepted First-Release Scope

- PM prepares billing for `time_and_materials`, `fixed_price`, and `cost_plus` projects. Unit and recurring billing are deferred until a separate product decision adds their source and schedule semantics.
- PM never issues the official invoice. It owns billing schedules, preparation numbers, eligible-source selection, approval state, source locks, contract-value projections, and profitability read models.
- Fixed-price billing uses PM-owned billing schedule lines. A schedule line may reference a Project milestone/Task, but the billing amount and due/acceptance state remain finance-owned facts.
- Time-and-materials preparation selects approved-time billing facts with snapshotted billing rates. Cost-plus preparation selects posted cost facts and snapshots the approved markup policy. Expense-claim capture is deferred to a future Expenses owner; externally sourced posted expenses may participate through the canonical financial-source contract.
- PM exposes contract, billable, externally invoiced, externally paid, and margin projections only. Statutory revenue recognition remains external.
- The first accounting boundary is vendor-neutral contract version `project_billing_preparation.v1`, delivered through the platform durable integration mechanism. It carries tenant, organization, project, preparation, currency, immutable line, idempotency, and correlation identifiers. External acknowledgement supplies external system, invoice/reference, status, acknowledgement time, and reconciliation reference.
- Closed financial periods reject new billing preparation for sources in that period. Corrections are reversal/replacement preparations in an open period and retain the original preparation reference; PM does not reopen an external accounting period.
- Billing preparations, source locks, approvals, acknowledgements, reconciliation evidence, and audit exports are immutable or append-only after approval. Tenant retention policy is configurable with a seven-year default; legal hold prevents deletion. Phase E introduces no hard-delete workflow.

## Alternatives Rejected

- Build a full accounting application inside PM: violates scope and ownership.
- Let external accounting read PM tables directly: bypasses contracts, tenancy, and idempotency.
- Treat vendor commitment status `INVOICED`/`PAID` as customer billing: these are unrelated semantics.

## Consequences

Phase E may now proceed. The integration contract is vendor-neutral so an ERP-specific adapter can be selected later without changing PM ownership or aggregate semantics. QML presents preparation and integration status, not unsupported official accounting behavior.

## Migration Impact

No existing invoice data is available to migrate. Legacy vendor references remain procurement/cost source snapshots and are not reclassified as customer invoices.

## Test Impact

Test billable-source eligibility and locking, retry idempotency, approval, external acknowledgement/reconciliation, tenant isolation, sensitive profitability permission, and prevention of duplicate billing.
