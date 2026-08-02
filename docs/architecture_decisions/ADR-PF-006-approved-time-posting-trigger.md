# ADR-PF-006: Approved-Time Posting Trigger

- Status: accepted; Phase A2 source contract implemented
- Date: 2026-08-02
- Implementation gate: Phase A2 contract and Phase C consumer

## Context

Platform Time periods support OPEN, SUBMITTED, APPROVED, REJECTED, and LOCKED. PM finance currently costs aggregate assignment hours regardless of approval and at the current rate. APPROVED is the existing business acceptance point; LOCKED is a later immutability control.

## Decision

- Recommended trigger: transition of a TimesheetPeriod to APPROVED publishes/provides an approved-time snapshot for finance posting.
- Finance posts one labor ProjectCostEntry per approved TimeEntry/version and posting purpose after scope/rate/period validation.
- Transition to LOCKED is idempotent and does not create another posting.
- Rejection before approval creates no financial entry. Corrections after posting create reversal/replacement entries from a new approved source version; no posted amount is edited.
- Time owns hours and approval. Finance owns rate selection, Money, posting, reversal, and financial period.
- The contract must expose a durable TimeEntry version or approved snapshot ID/content hash because the current TimeEntry has no explicit version field.

## Alternatives Rejected

- Cost every saved hour: includes unapproved work.
- Wait for LOCKED: delays actual costs and conflates approval with administrative locking.
- Read `TaskAssignment.hours_logged`: loses source/date/version detail and idempotency.

## Consequences

Time needs a stable approved-entry query/event contract and correction semantics. Finance must tolerate retries and out-of-order delivery.

## Migration Impact

Existing assignment-hour totals are not migrated as postings without approved source detail. Environments may rebuild from approved periods or classify historical labor as legacy estimates.

## Test Impact

Test approved-only generation, LOCKED no-op, retry/out-of-order handling, source versioning, correction reversal/replacement, cross-tenant references, rate snapshots, and period closure.

## Implementation Evidence

- `ApprovedTimeFinancialSource` requires an APPROVED snapshot ID, source revision/content hash, tenant/organization/project scope, TimeEntry and period identity, work allocation/resource dimensions, work date, and canonical Decimal hours.
- The contract intentionally contains no labor rate or amount. Time owns the approved quantity; PM Finance selects and snapshots the financial rate when the Phase C consumer posts it.
- The provider protocol is tenant/organization/project scoped and cursor paginated. The adapter and durable consumer remain Phase C work.
