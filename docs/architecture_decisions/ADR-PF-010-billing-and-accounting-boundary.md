# ADR-PF-010: Billing and Accounting Boundary

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase E

## Context

PM invoicing/revenue packages and QML invoice views are placeholders. The repository has no official customer invoice, payment, tax, revenue-recognition, or general-ledger aggregate. Project Finance still needs billable-source selection, billing preparation, project revenue projections, profitability, and external reconciliation.

## Decision

- PM owns Project billing configuration/schedules, billable source eligibility, `ProjectBillingPreparation`, approval, duplicate-selection prevention, contract-value projections, and project profitability read models.
- A future Billing/Accounting module or external system owns official invoice numbers/documents, tax, receivables, payments, statutory revenue recognition, and GL posting.
- PM sends approved billing preparations through an idempotent contract and stores external acknowledgement, invoice reference, status snapshot, and reconciliation reference.
- External invoice/payment updates are projections in PM and cannot be edited as authoritative records.
- Only billing methods explicitly accepted by product are implemented; placeholder QML does not define scope.

## Alternatives Rejected

- Build a full accounting application inside PM: violates scope and ownership.
- Let external accounting read PM tables directly: bypasses contracts, tenancy, and idempotency.
- Treat vendor commitment status `INVOICED`/`PAID` as customer billing: these are unrelated semantics.

## Consequences

Phase E depends on a selected external owner/system and product decisions for fixed-price, milestone, T&M, cost-plus, unit, and recurring methods. QML presents preparation/integration status, not unsupported official accounting behavior.

## Migration Impact

No existing invoice data is available to migrate. Legacy vendor references remain procurement/cost source snapshots and are not reclassified as customer invoices.

## Test Impact

Test billable-source eligibility and locking, retry idempotency, approval, external acknowledgement/reconciliation, tenant isolation, sensitive profitability permission, and prevention of duplicate billing.
