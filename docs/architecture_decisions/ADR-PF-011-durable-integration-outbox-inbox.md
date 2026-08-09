# ADR-PF-011: Durable Integration Outbox and Inbox

- Status: accepted; durable foundation and Phase C.4/C.5 financial delivery implemented
- Date: 2026-08-02
- Implementation gate: Phase A2 decision and contract; Phase C persistence/consumers

## Context

Project Finance must consume approved Time and Procurement facts without importing their repositories or relying on process-local notifications. Delivery can be retried, duplicated, delayed, or received out of order. The existing collaboration inbox is user-facing collaboration data, and the shared process-local domain events are UI refresh signals; neither is a durable integration mechanism.

The domain-event half of that observation — giving each bounded context typed, immutable, past-tense domain events instead of the shared string-keyed signal file — is addressed separately in [ADR-005](ADR-005-domain-events.md). That decision is complementary, not a dependency: this ADR's outbox/inbox contract stands regardless of when or whether ADR-005 is implemented.

## Decision

- A source module owns a transactional outbox record written in the same database transaction as its aggregate transition. Time writes approved-time events; Procurement writes PO/receipt lifecycle events.
- Each consuming bounded context owns its durable inbox receipts and applies the inbox claim, financial mutation, required audit record, and any resulting outbox records in one transaction.
- Delivery is at least once. The inbox deduplicates transport delivery by consumer, tenant, and event ID. Project Finance separately enforces semantic uniqueness using tenant/organization, source module/type, source document/line, source revision, and posting purpose.
- A replay with the same semantic key but a different project or content hash is a conflict and is quarantined; it is not treated as a successful duplicate.
- Events use a transport-neutral, typed, schema-versioned envelope containing event identity/type, tenant/organization scope, aggregate identity/version, UTC occurrence time, correlation/causation IDs, and a JSON payload.
- Ordering is enforced per aggregate/version, not globally. Stale or conflicting events are retained for diagnosis; retries use bounded backoff and exhausted deliveries move to an operator-visible dead-letter state.
- Initial transport may be a database polling/post-commit dispatcher. Broker transport can replace it later without changing application contracts or financial semantic identity.
- Process-local signals remain suitable only for post-commit UI refresh. They are never evidence that financial integration delivery succeeded.

## Alternatives Rejected

- Direct cross-module repository reads/writes: breaks ownership, pagination, tenancy, and replay safety.
- In-memory event callbacks: lose events on process failure and cannot provide durable retry or deduplication.
- Broker publish without a transactional outbox: can commit business state without publishing, or publish state that later rolls back.
- One shared inbox table owned by no bounded context: obscures consumer transaction ownership and retention policy.
- Message ID deduplication alone: does not prevent two event IDs from producing the same financial posting.

## Consequences

The source modules and PM Finance now have additive owned outbox/inbox persistence and lifecycle services with operational retry/dead-letter state. Message delivery identity and financial source identity remain intentionally separate. C.4 applies this design to approved Time and C.5 applies it to project-linked Procurement PO/receipt lifecycle facts without replacing or bypassing the permanent foundation.

## Migration Impact

No current process-local signal is reclassified as durable. Phase C adds tables and dispatch/consumer infrastructure before Time or Procurement posting cutover. Historical facts are replayed through source contracts with explicit revisions and content hashes rather than fabricated event history.

## Test Impact

Test atomic outbox writes, duplicate transport delivery, duplicate semantic sources under different event IDs, cross-tenant scope, out-of-order aggregate versions, conflict quarantine, retry/dead-letter behavior, replay, consumer rollback, and post-commit UI notification behavior.

## Implementation Evidence

- `src/core/platform/integration/events.py` defines the immutable versioned envelope, UTC normalization, payload hashing, and consumer/tenant/event inbox deduplication key.
- `src/core/modules/project_management/contracts/financial_sources.py` defines the separate scoped semantic source identity and source content hash required by Project Finance.
- `src/core/platform/integration/delivery.py` and `src/core/platform/application/integration/delivery_service.py` define commit-neutral outbox/inbox records, leasing, bounded retry/dead-letter, deduplication, ordering, and quarantine behavior.
- Migration `r5s6t7u8v9w0` creates Time-owned and Procurement-owned outboxes plus the PM Finance-owned inbox with direct tenant/organization scope, forced PostgreSQL RLS, claim/aggregate indexes, and immutable-envelope database guards.
- The three scoped SQLAlchemy repositories and composition services are permanent infrastructure. No in-memory bridge or direct PM-to-source implementation import was introduced.
- Platform Time writes approved-entry events atomically with approval and audit. `ApprovedTimeFinancialDispatcher` claims the Time outbox, applies the PM Finance inbox and financial mutation transactionally, acknowledges only after commit, and is replayed in a bounded startup pass without threads or timers.
- Failed consumption rolls back the financial transaction, then persists matching retry/dead-letter evidence in the PM inbox and Time outbox using the canonical domain error code. It does not expose a raw exception to QML or lose the committed source fact.
- PM Finance independently enforces semantic source revision/content identity, snapshots the selected rate, writes the posted labor actual and immutable posting detail, and reverses/replaces corrected approvals. Process-local cost signals remain post-commit UI refresh only.
- Procurement writes PO-line and receipt-line events to its owned outbox in the same transaction as source lifecycle, stock, and receipt changes. PM applies commitment revision or receipt actual/match plus inbox/audit atomically; non-project POs never enter the financial channel.
- `src/tests/platform/test_integration_delivery_foundation.py` verifies the generic delivery guarantees. `src/tests/project_management/test_approved_time_labor_integration.py` covers C.4 and `src/tests/project_management/test_procurement_financial_integration.py` covers C.5 source atomicity, lifecycle projection, accrual/matching, variance, retry, isolation, and replay behavior.
