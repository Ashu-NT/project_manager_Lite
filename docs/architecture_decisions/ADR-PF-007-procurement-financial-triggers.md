# ADR-PF-007: Procurement Financial Triggers

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase A2 contract and Phase C consumer

## Context

Procurement owns requisitions, POs, lines, receipts, and statuses including PO APPROVED/SENT/PARTIALLY_RECEIVED/FULLY_RECEIVED/CLOSED/CANCELLED and receipt POSTED. PM currently lists project-linked requisition headers but does not create monetary commitments or actuals. No supplier-invoice aggregate exists.

## Decision

- Recommended commitment trigger: PO `SENT`, because the approved order has been issued to the supplier. APPROVED may appear as authorized pipeline but is not active committed exposure.
- Requisitions do not create commitments; they may contribute to forecast demand.
- PO changes/cancellation/closure update the idempotent PM commitment projection and preserve source history.
- Recommended first actual trigger: a POSTED receipt creates a `PROCUREMENT_RECEIPT_ACCRUAL` ProjectCostEntry and matches/reduces the PO commitment for received value.
- A future supplier invoice/accounting actual must match and reverse/reclassify the receipt accrual rather than duplicate it.
- Procurement owns quantities, prices, supplier, and source lifecycle. PM owns Project dimensions, financial period, commitment projection/matching, and actual posting.
- Source identity includes Procurement document/line/version and posting purpose.

## Alternatives Rejected

- Approved requisition as commitment: no supplier obligation exists.
- PM directly querying or mutating Procurement repositories: violates ownership and reliable pagination.
- Treat both receipt and later invoice as independent actuals: double-counts cost.

## Consequences

The product must confirm whether SENT creates legal/operational commitment and whether receipt accrual is desired before accepting this ADR. Typed contracts/events and quantity/price snapshots are required.

## Migration Impact

Existing linked requisitions are visibility data only. Historical commitments/receipts require replay from Procurement source records; fixed-limit client-side lookup is removed after the contract cutover.

## Test Impact

Test each PO/receipt transition, partial receipt/matching, cancellation, price/quantity changes, retries, source ordering, currency, cross-tenant supplier/project references, and future invoice accrual replacement.
