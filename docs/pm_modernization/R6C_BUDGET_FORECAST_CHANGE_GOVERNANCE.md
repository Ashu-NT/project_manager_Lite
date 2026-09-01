# R6C Budget, Forecast, and Financial Change Governance

## 1. Status

**R6C IN PROGRESS.** R6A and R6B are closed. This document records the verified
R6C starting state and is the execution ledger for the forward-only write
cutover. R6C must not be marked closed until every blocking exit gate is green.

## 2. Scope

R6C owns governed Budget, Forecast, Financial Change, and the existing Financial
Setup profile/cost-code/restriction commands. It includes command UX, optimistic
concurrency, approval/SoD, caller-owned transactions, atomic audit, post-commit
targeted invalidation, and authoritative R6B refresh.

## 3. Non-Scope

Actuals, Commitments, Rate Card writes, Decimal EVM, final Variance taxonomy,
Cost Phasing formulas, Billing writes, and Accounting integration remain R6D-R6G.

## 4. R6A/R6B Decisions Preserved

The six-destination IA, explicit project pinning, immutable scoped Readers,
server paging/search/sort, Decimal-string desktop boundary, targeted invalidation,
and one forward-only production architecture remain authoritative. No Project
Budget field, client-side financial formula, monolithic snapshot, or duplicate
Finance workspace may return.

## 5. Final Write Architecture

Target: QML -> controller -> desktop command API -> application command
orchestrator -> authorization/domain/repositories/audit -> flush -> caller-owned
UoW commit -> scoped post-commit invalidation -> authoritative R6B read refresh.
The desktop API maps commands and results only; business rules stay in the
application/domain layers.

## 6. Transaction Ownership

Verified starting debt: `BudgetService`, `ForecastVersionService`,
`ForecastGenerationService`, `FinancialChangeService`, and
`FinancialConfigurationService` contain direct commit paths. Financial Change
submission alone already uses a fresh-session UoW. R6C will migrate one bounded
workflow at a time and delete direct-commit production paths after all callers
move.

## 7. Unit of Work

Use narrow capability UoWs built on `SqlAlchemyUnitOfWorkBase`. Each operation
gets a fresh Session and typed repositories. Explicit `commit()` occurs once at
the orchestration boundary; exception/clean-without-commit rolls back and closes.
Platform approval decisions retain their Platform-owned transaction and
session-parameterized module participant.

## 8. Budget Authority

Approved Budget remains the exact sum of lines in the one approved Finance-owned
version. Project and portfolio projections remain read-only consumers.

## 9. Budget Lifecycle

The existing Draft -> Submitted -> Approved/Rejected -> Superseded/Closed domain
rules remain authoritative. Approved history is immutable; change requires a
successor revision.

## 10. Budget Lines

Use actual cost-code, optional task, description, amount, and currency fields.
Mutations are allowed only while the parent is mutable. Currency must equal the
Budget currency; cost-code eligibility and task/project membership remain
server enforced.

## 11. Budget Concurrency

Line mutation checks both line and parent versions where applicable and advances
the parent version. Open-version, revision, and one-approved-version uniqueness
conflicts retain named domain errors rather than leaking database exceptions.

## 12. Budget Approval

Submission, approval request, audit, and lifecycle transition must be atomic.
Governed decisions use Platform Approval. Requesters cannot decide their own
request; direct decision remains available only when governance policy permits it.

## 13. Budget Successor

The server assigns the next revision and retains predecessor/current-approved
lineage. Approval supersedes the previous approved version without modifying its
historical lines.

## 14. Forecast Authority

The approved Forecast applicable at the requested as-of date remains authority.
Revision, predecessor, generation mode, source decisions/lines, lifecycle, and
approval evidence are retained.

## 15. Forecast Generation

Generation remains server-owned from planned costs, posted actual offsets,
commitments, manual ETC, risk contingency, as-of date, and Finance dimensions.
Existing incomplete/unreconstructable/future-invalid/duplicate/currency failure
semantics must not be weakened.

## 16. Manual ETC

Manual ETC retains dimensional replacement semantics. UI wording must describe
replacement scope and must never present the amount as an additive "Extra ETC".

## 17. Risk Contingency

Register owns risk identity/status; Finance owns the monetary Forecast effect.
Selection must be bounded and eligibility server-authoritative. No new
probability weighting is introduced.

## 18. Forecast Approval

Submit/approve/reject require current versions and lifecycle. Platform Approval
enforces SoD; an approved version is immutable and becomes authority only after
the transaction commits.

## 19. Forecast Successor

Regeneration/successor behavior preserves revision, predecessor, generation
mode, source decisions, as-of date, and concurrency. QML never generates a
revision or edits generated categories unsupported by the domain.

## 20. Financial Change Authority

`FinancialChangeRequest` owns the proposal and `FinancialChangeImpact` owns
typed Budget, Forecast, and Schedule effects. Procurement and Accounting truth
remain outside this aggregate.

## 21. Typed Impacts

Only currently implemented domain fields and impact types will be exposed.
Impact create/update/delete obey request lifecycle and optimistic versions.

## 22. Base Revision Capture

Creation snapshots current approved Budget and Forecast IDs/revisions on the
server. QML cannot choose or override authoritative bases.

## 23. Apply-Time Revalidation

Apply rechecks stored base IDs/revisions against current approved authorities.
Any stale Budget or Forecast base fails before successor or Schedule mutation.

## 24. Budget Apply

Budget impacts create a successor through Budget authority. The original
approved version remains unchanged and the applied successor reference is stored.

## 25. Forecast Apply

Forecast impacts create/regenerate through Forecast authority with preserved
source and as-of semantics. The applied successor reference is stored.

## 26. Schedule Apply

Schedule impacts invoke the Scheduling-owned port. Finance must not import Task
ORM or mutate Task persistence directly.

## 27. Financial Setup Write UX

Expose only existing authoritative profile, cost-code, and project restriction
commands under Controls -> Financial Setup. Retain profile/cost-code versions,
required fields, hierarchy/effective-date rules, and bounded selectors. Rate
Card mutation is excluded.

## 28. Separation of Duties

Platform Approval remains decision authority. The existing self-decision error
contract must reach QML as an actionable inline message without raw exceptions.

## 29. Permission Matrix

Budget uses `budget.manage`, `budget.approve`, and governed
`approval.request/approval.decide` as applicable. Forecast uses its current
manage/approve permissions. Financial Change uses
`financial_change.manage` plus approval permissions. Setup uses current
`finance.manage`; every command also enforces project visibility and active
tenant/organization scope.

## 30. Optimistic Concurrency

Every mutable command carries the authoritative row version. Stale writes,
stale children, successor races, approval races, and stale apply bases fail
closed and instruct the user to refresh; no silent overwrite is permitted.

## 31. Audit Atomicity

Fail-closed audit uses the same Session and transaction as the domain mutation.
Audit failure rolls back business state. No success message or invalidation may
occur before commit.

## 32. Approval Governance

Approval request creation and submission transition are one operation. Apply
participants are built against the Platform approval UoW Session and return
post-commit events; they never use the process-lifetime Session.

## 33. Post-Commit Invalidation

Budget -> Overview/Planning/Performance; Forecast ->
Overview/Planning/Performance; Change -> Controls; applied Change additionally
invalidates the affected Budget/Forecast/Scheduling surfaces; Setup invalidates
only dependent Setup/selector surfaces. Scope is exact tenant/organization/project,
with coalescing and no global refresh.

## 34. PostgreSQL/RLS

New write integration tests must run through non-owner `app_runtime`
(`NOSUPERUSER`, `NOBYPASSRLS`) against the fresh Alembic schema. They must prove
tenant/org denial and direct child-table denial for BudgetLine, ForecastLine,
ForecastSourceDecision, FinancialChangeImpact, profile, cost code, and restriction.

## 35. Decimal/Currency/Rounding

Money remains Decimal with explicit currency. No FX, mixed-currency silent
aggregation, new float authority, QML arithmetic, or rounding-policy change is
part of R6C.

## 36. Responsive UX

Commands integrate into the existing four R6B sections. Dialogs must fit
1024x640 through 1920x1080, keep required fields visible, prevent duplicate
submission, show busy/error/success truthfully, and refresh authoritative reads.

## 37. Keyboard/Focus

Dialogs require deterministic initial focus, tab order, Enter/escape behavior,
keyboard selector operation, and focus restoration to the invoking action.

## 38. Pre-Release Cleanup

After each cutover, migrate all internal consumers and delete superseded command
APIs, direct-commit paths, dialogs, controller/presenter actions, DI registrations,
and tests. Temporary scaffolding cannot survive R6C closure.

## 39. Performance Characterization

Measure representative create/line/submit/decision/successor/generation/apply
operations after correctness. Investigate N+1, aggregate over-hydration,
duplicate approval reads, and duplicate refreshes; do not impose speculative
statement limits.

## 40. Tests

Required suites cover lifecycle happy/rejection/successor paths, manual ETC and
risk parity, typed Change apply and stale bases, SoD, concurrency races,
rollback/audit atomicity, post-commit invalidation, PostgreSQL/RLS, controller/QML
UX, all five viewports, R6B reads, and a meaningful broader PM/Finance regression.

## 41. Deferred R6D-R6H Work

R6D: Actual/Commitment/Rate writes. R6E: Decimal EVM/Variance/Cost Phasing.
R6F: Billing writes and granular permissions. R6G: durable Accounting
integration. R6H: final scale, exhaustive RLS, and release closure.

## 42. R6C Closure Decision

**R6C NOT CLOSED.** Characterization is complete enough to begin the transaction
cutover. Blocking work remains: caller-owned UoWs for all R6C command families,
complete desktop/controller/QML workflows, rollback/SoD/concurrency/RLS proof,
forward-only cleanup, and final regression evidence.

## R6C-A Transaction Ownership Migration

**Status: IN PROGRESS.** The canonical `FinanceGovernanceUnitOfWork` now owns a
fresh operation Session and binds the complete R6C repository set, Platform
approval repository, and fail-closed Enterprise Audit service to that same
Session. It is the one shared Budget/Forecast/Change/Setup transaction
construction mechanism; it does not replace the Platform Approval decision UoW.

The Budget, Forecast Version, Forecast Generation, Financial Change mutation,
and Financial Setup services have been converted to stage/flush behavior. Their
former direct commits, rollback-on-behalf-of-caller behavior, and service-side
success invalidation are being removed. Approval participants continue to stage
against the Session supplied by Platform Approval and return post-commit event
descriptors rather than publishing or committing independently.

The cutover is not complete until the outward Finance governance command
boundary constructs these transaction-neutral services against the UoW,
commits once, and publishes targeted invalidation only after success. The
existing Financial Change submission method still owns its narrower UoW and is
the remaining inward transaction owner to migrate. Fault-injection tests must
execute through the final command boundary; a transaction-neutral service is
not expected to roll back its caller's Session itself.
