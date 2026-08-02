# ADR-PF-004: Financial Posting and Reversal

- Status: proposed
- Date: 2026-08-02
- Implementation gate: Phase A1 conventions and Phase C ledger

## Context

Legacy actual amounts are non-negative mutable fields and can be physically deleted. A canonical project-cost ledger requires immutable postings and one unambiguous reversal representation. Supporting both signed values and a separate debit/credit direction would create two sources of truth.

## Decision

- Use signed ProjectCostEntry postings.
- Original cost entries are positive. A reversal is a new equal negative Money entry with `entry_kind=REVERSAL` and `reverses_entry_id` pointing to the original.
- Adjustments are explicitly typed signed entries. The amount sign is authoritative; there is no separate CREDIT/DEBIT or reversal direction field.
- A posted entry is immutable and cannot be physically deleted. A reversal must use the same transaction/base currencies and exact snapshotted conversion relationship as the original.
- Full reversal is the first implementation. Partial reversal requires a later explicit rule and cumulative-reversal constraint.
- Draft manual entries may be edited/deleted under policy; posting freezes financial and source snapshots.

## Alternatives Rejected

- Positive amount plus direction: duplicates sign interpretation across calculations and exports.
- Editing/deleting posted rows: destroys audit and period stability.
- In-place status-only reversal: does not produce a balancing financial record.

## Consequences

Money must support negatives, while Budget and Commitment policies remain non-negative. Aggregations sum signed amounts. UI shows entry kind and reversal relationship rather than offering edit/delete for posted rows.

## Migration Impact

Legacy positive actuals become original entries according to the migration posting-state decision. Existing records are never converted into negative values unless a verified reversal source exists.

## Test Impact

Test exact net-zero reversal, duplicate reversal prevention, cross-scope/currency rejection, closed-period policy, immutable posted state, audit lineage, and signed report aggregation.
