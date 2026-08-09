# ADR-PF-006: Approved-Time Posting Trigger

- Status: accepted; Phase C.4 source event and labor-cost consumer implemented
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
- Platform Time emits one canonical `platform_time.time_entry.approved.v1` envelope per changed approved entry. The Time-owned outbox preserves immutable snapshots and monotonic revisions; approval, audit, and outbox writes share one transaction.
- PM Finance consumes through its owned inbox, resolves and snapshots the effective COST/HOUR rate, requires the default cost code and open financial period, and atomically writes the posted actual, immutable labor detail, audit, and receipt.
- Correction reapproval references the latest source revision and creates an equal posted reversal plus replacement. `LOCKED` is a later administrative transition and emits no financial event; unlocking returns to APPROVED, while a reason-required correction command reopens to OPEN.
- Database transport dispatches immediately after approval and replays a bounded pending batch at composition startup. Failures remain retryable/dead-letterable and never roll back an already committed approval.
- A closed financial period creates no PM posting. The approved Time fact remains committed while both owned delivery stores retain retry state and the canonical `FINANCIAL_PERIOD_POSTING_BLOCKED` operator code.
- Migration `s6t7u8v9w0x1` adds the directly scoped/RLS `project_approved_time_labor_postings` table with immutable update/delete guards and complete quantity/rate-card selection evidence.
- The typed desktop correction adapter is implemented. Its final QML reason dialog/action is deliberately owned by Phase C.8's ledger redesign, not a temporary C.4 component.
- No temporary files, in-memory delivery adapters, direct PM-to-Time implementation imports, or new deletion-register entries were added.
