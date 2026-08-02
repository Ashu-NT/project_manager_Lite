# ADR-PF-011: Durable Integration Outbox and Inbox

- Status: accepted; envelope contract implemented, durable stores deferred to Phase C
- Date: 2026-08-02
- Implementation gate: Phase A2 decision and contract; Phase C persistence/consumers

## Context

Project Finance must consume approved Time and Procurement facts without importing their repositories or relying on process-local notifications. Delivery can be retried, duplicated, delayed, or received out of order. The existing collaboration inbox is user-facing collaboration data, and the shared process-local domain events are UI refresh signals; neither is a durable integration mechanism.

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

The source modules and PM Finance require additive outbox/inbox persistence and operational retry/dead-letter visibility in Phase C. Message delivery identity and financial source identity remain intentionally separate. The accepted `IntegrationEventEnvelope` is permanent platform contract code; no temporary integration implementation is introduced in Phase A2.

## Migration Impact

No current process-local signal is reclassified as durable. Phase C adds tables and dispatch/consumer infrastructure before Time or Procurement posting cutover. Historical facts are replayed through source contracts with explicit revisions and content hashes rather than fabricated event history.

## Test Impact

Test atomic outbox writes, duplicate transport delivery, duplicate semantic sources under different event IDs, cross-tenant scope, out-of-order aggregate versions, conflict quarantine, retry/dead-letter behavior, replay, consumer rollback, and post-commit UI notification behavior.

## Implementation Evidence

- `src/core/platform/integration/events.py` defines the immutable versioned envelope, UTC normalization, payload hashing, and consumer/tenant/event inbox deduplication key.
- `src/core/modules/project_management/contracts/financial_sources.py` defines the separate scoped semantic source identity and source content hash required by Project Finance.
- Durable outbox/inbox repositories, dispatchers, and consumers are Phase C deliverables and are not represented by an in-memory compatibility shim.
