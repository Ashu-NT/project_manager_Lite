# ADR-PF-008: Approval Unit of Work

- Status: accepted; initial transaction cutover implemented
- Date: 2026-08-02
- Implementation gate: Phase A0

## Context

`ApprovalService.approve_and_apply` invokes an apply handler before updating and committing the approval decision. The registered PM cost handlers call services that commit their own mutations. A later failure can leave a financial mutation committed while its approval remains pending. Process-local signals may also fire before the final transaction is durable.

## Decision

- The outer approve-and-apply application use case owns one database transaction/unit of work.
- Apply handlers may validate and stage repository/domain mutations but must not commit, roll back, dispatch notifications, or emit process-local success signals.
- Financial mutation, approval decision, Enterprise Audit intent/row, idempotency/inbox state, and durable outbox records commit atomically.
- Domain/UI notifications are dispatched only after successful commit. Delivery failure does not roll back committed business state; the durable outbox retries.
- Any exception before commit rolls back all staged changes and leaves the request pending or records a separately atomic failed-application state according to policy.
- Self-approval and request-type permissions are checked before handler invocation. Admin identity never bypasses the transaction or decision policy.

## Alternatives Rejected

- Nested service commits: breaks atomicity.
- Compensating delete after failure: unsafe for posted/approved financial history.
- Commit approval first, then apply asynchronously without state model: can mark unapplied requests approved.

## Consequences

Existing committing services need transaction-aware command variants or repository orchestration. The change affects other approval consumers and requires platform contract tests.

## Migration Impact

No financial data migration is required, but pending approval handlers must be inventoried and migrated before the old callback contract is removed.

## Test Impact

Add failure injection before/after handler staging, audit, outbox, and decision update; concurrency/double-decision tests; post-commit notification tests; and regression tests for every registered approval handler.

## Implementation Evidence

- `ApprovalService` owns commit/rollback for approval application and rejection; registered handlers return typed post-commit events rather than emitting success signals while the transaction is open.
- PM baseline/dependency/cost and Inventory requisition/purchase-order handlers stage writes and Activity with `commit=False`; approval and required Enterprise Audit rows share the outer transaction.
- Cost mutations write old/new-state Enterprise Audit records and fail closed when required audit persistence fails.
- Failure-injection tests prove cost state remains unchanged when decision persistence or required audit fails, and no cost success signal escapes a rolled-back transaction.
- Temporary legacy service switches are marked `TRANSITION(PF-A0-UOW-BRIDGE)` and are registered for deletion at the Phase C dedicated-command cutover.

ADR-PF-011 now governs durable outbox/inbox ownership. The current post-commit process-local signals remain UI refresh notifications and are not a substitute for durable integration delivery.
