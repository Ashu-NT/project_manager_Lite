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

R6C-A closed this starting debt. `BudgetService`, `ForecastVersionService`,
`ForecastGenerationService`, `FinancialChangeService`, and
`FinancialConfigurationService` are transaction-neutral operations. The single
commit owner is `FinanceGovernanceCommandBoundary`; all production service-graph
mutation ports route through it. The former Financial Change submission UoW was
deleted rather than retained as compatibility architecture.

## 7. Unit of Work

`FinanceGovernanceUnitOfWork` is the one R6C capability UoW built on
`SqlAlchemyUnitOfWorkBase`. Each command creates a fresh Session, installs the
runtime PostgreSQL tenant/organization context, and binds typed repositories and
Enterprise Audit to that Session. Explicit `commit()` occurs once at the outward
boundary; exception/clean-without-commit rolls back and closes. Platform approval
decisions retain their Platform-owned transaction and session-parameterized
module participant.

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

**Status: COMPLETE.** `FinanceGovernanceCommandBoundary` is the canonical
application-layer command owner. Every invocation creates one fresh
`FinanceGovernanceUnitOfWork`, constructs Budget, Forecast Version, Forecast
Generation, Financial Change, and Financial Setup operations against that UoW's
Session, commits exactly once, then runs targeted invalidation and notification
reactions. Long-lived workspace/read Sessions are not reused for writes.

### R6C-A Caller Inventory

- ACTIVE: the production service graph exposes governed mutation ports for all
  five R6C service families; their reads delegate to read services and every
  mutation enters the canonical boundary.
- ACTIVE: the Financials desktop API `create_cost_code` command enters
  `financial_setup()` on the boundary. No business rule moved into the desktop
  API.
- ACTIVE: Platform Approval remains the outward transaction owner for Budget
  and Financial Change decisions. Its dependency factories build participants
  and Finance operations against the Approval UoW Session.
- DISTINCT CURRENT SEMANTIC: Forecast lifecycle decisions are currently direct
  Finance commands; no Forecast Platform Approval participant exists to migrate
  in R6C-A.
- TEST ONLY: Finance mutation fixtures now consume governed service ports or the
  boundary directly. Fresh-instance fault injection targets the operation class
  or command callback rather than a singleton repository instance.
- DEAD: the narrow Financial Change submission UoW contract, implementation,
  factory composition, imports, and tests preserving it were deleted.

### R6C-A Financial Change Submission

Submission is transaction-neutral and stages request validation, the Financial
Change transition, Platform `ApprovalRequest` plus typed event, and both audit
records through the caller-owned Finance UoW. Approval-request notification is
queued as a post-commit action. There is no inward `uow.commit()` and no
submission-specific transaction architecture.

### R6C-A Invalidation

Budget invalidates Overview/Planning/Performance through the established
project signal. Forecast invalidates Overview/Planning/Performance with an exact
tenant/organization/project scope. Financial Change invalidates Controls;
participant apply results additionally retain Budget/Forecast/Scheduling hints.
Financial Setup now emits an exact scope consumed only by dependent Planning,
Costs, and Controls surfaces. Reactions run after successful commit, are logged
and isolated if a process-local subscriber fails, and never produce a global
Finance refresh. Rollback and commit failure emit no success invalidation.

### R6C-A Atomicity And Concurrency Evidence

- Budget lifecycle and line concurrency, Forecast lifecycle/generation,
  Financial Change request/impact/submission, and Financial Setup profile/
  restriction suites pass through fresh command transactions.
- The original Forecast generation audit-failure test proves zero root, line,
  decision, metadata, or audit residue without service-owned rollback.
- Financial Change commit/audit failure proves the host transition, Approval
  request, typed event, and audit roll back together.
- Budget and Financial Change participant failure tests prove Platform Approval
  state, Finance state, and audit share one Session and transaction.
- The targeted Finance family matrix passed `75`; approval participant,
  workflow, event, and invalidation matrix passed `76`; command-boundary and
  desktop-routing guards passed `6`.

### R6C-A PostgreSQL Evidence

The repository Docker PostgreSQL 16 stack was recreated and migrated from
Alembic head. Through `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`, non-owner),
the live command smoke passed `2`: legal Financial Setup, Budget, Forecast, and
Financial Change commands persisted through the new boundary, execution-role
validation passed, and a foreign tenant/organization insert was denied. The UoW
factory explicitly installs the real runtime DB context on each fresh Session.

### R6C-A Architecture And Cleanup

AST guards prohibit `commit()`/`rollback()` in the five R6C services and Finance
approval participants and verify production composition exposes governed ports
backed by a UoW factory. The scoped production search has exactly one transaction
owner hit: `FinanceGovernanceCommandBoundary` calling `uow.commit()`. No R6C
repository or participant hit remains. Billing and Inventory submission UoWs are
distinct current semantics, not R6C compatibility. No `*_without_commit` API,
transaction bridge, deprecated caller, or Financial Change submission wrapper
remains.

R6C remains open. R6C-A added no QML workflow and started no R6D, R6E, R6F, or
R6G implementation.

## R6C-B Budget Governance Command UX

**Status: COMPLETE.** The existing Finance -> Planning -> Budgets destination is
the only Budget command UX. No route, duplicate workspace, compatibility
presenter, or generic Manage Budget page was introduced.

### R6C-B Command Architecture

Budget create/update/delete, line create/update/delete, submit, approval request,
successor, and close flow through explicit controller slots, presenter command
functions, typed desktop commands, and `FinanceGovernanceCommandBoundary`.
Money crosses the desktop boundary as a canonical decimal string and is converted
to finite `Decimal` before service execution. Successful commands commit before
the existing scoped Budget signal invalidates only Overview, Planning, and
Performance; no global Finance refresh was added.

The desktop approval-request command now invokes explicit
`request_budget_approval()`. It always creates a Platform Approval request and is
not changed into a direct approval by `PM_GOVERNANCE_MODE`. Platform Approval is
the only QML decision authority. Server-projected capabilities distinguish
manage, submit, request, decide, close, and successor rights. The pending request
ID/requester are read authoritatively, and approve/reject are deny-safe for the
requesting principal even when that principal also holds decision permission.

### R6C-B Authority And Lineage

The server retains one-open-version enforcement, assigns revisions, validates
currency/cost-code/task scope, and enforces line plus parent optimistic versions.
Approved versions and lines remain immutable. `Create Successor` requires an
approved predecessor, stores a scoped predecessor FK, clones its exact lines into
a new Draft with new identities, preserves currency and approved history, and
leaves the predecessor unchanged. Delete commands return the affected aggregate
for scoped invalidation; the desktop adapter does not call private service APIs.

### R6C-B Read And UX Cutover

The authoritative R6B Budget reader now projects row versions, lineage, approval
evidence, cost-code/task identities, and deny-safe action capabilities. Open-
version eligibility is returned in the existing count round trip, preserving the
bounded five-statement Budget master/detail read instead of adding another query.
Cost Code and optional Task use bounded server lookups. The three responsive
dialogs use the shared centered, scrollable, pinned-footer shell; validation stays
visible, entered values remain in the open dialog after a conflict, and an
authoritative Planning refresh replaces stale versions without automatic retry.

All finite Finance dropdowns use the same shared `AppControls.ComboBox` as
Projects and Tasks. Large project/task/cost-code lookups retain the shared
server-paged selector, but its UX is a continuous searchable result list:
additional bounded pages load while scrolling and table-style Previous/Next
pagination is not exposed inside the dropdown.

### R6C-B Migration And Runtime Repair

Revision `a61d8c4f2b70` adds `predecessor_budget_id` and the tenant/organization/
project-scoped self FK after the squashed baseline. This deliberately supports
both fresh databases and developer databases already stamped at
`f3c89cac079d`. App startup runs Alembic to head, so the reported SQLite
`no such column: project_finance_budgets.predecessor_budget_id` failure is
repaired on restart without deleting local data. The same runtime patch removed
the unknown `submit` icon and made selected-Budget QML state null-safe during
refresh.

The desktop SQLite engine now enables WAL and a bounded 15-second busy timeout.
This allows the long-lived read side and fresh Finance command UoWs to coexist
without read/write lock failures while preserving operation-scoped commits; it
does not add blind command retries. Unexpected Finance mutation exceptions keep
their full traceback in application logs but expose only a stable, non-sensitive
error message/code to QML, so SQL text and bound values cannot reach the UI.

Because R6C commands now use fresh sessions while the remaining desktop graph
still has one process-lived session, the Finance command boundary performs a
SQLite-only handoff: any retained transaction on that shared session is rolled
back before the fresh command UoW opens. PostgreSQL is unchanged. A file-backed
regression deliberately holds `BEGIN IMMEDIATE` on the shared session and proves
the subsequent Budget command commits through its isolated UoW.

### R6C-B Verification

- Consolidated Budget/R6B/API/controller/approval/QML/architecture matrix:
  `165 passed`.
- Docker PostgreSQL 16 fresh migration and `app_runtime` Budget, BudgetLine,
  scoped Reader, and foreign-scope denial proof: `2 passed`.
- Existing-baseline-to-head and fresh upgrade/downgrade SQLite migration proof:
  `2 passed`.
- Budget dialog viewport/focus/Escape matrix at 1024x640, 1280x720, 1366x768,
  1440x900, and 1920x1080: `15 passed`.
- Targeted PM dialog and registered-route offscreen loading: `15 passed`.
- Targeted Python compilation, authored-QML `pyside6-qmllint`, architecture
  guards, and `git diff --check`: PASS.
- No superseded Budget desktop/controller/presenter/dialog/DI path was found;
  policy-controlled direct service approval remains the distinct current
  non-QML semantic already approved in this document, not a compatibility path.
- Shared Finance selector, continuous-scroll page append, file-backed SQLite
  WAL concurrency/session handoff, Billing QML initialization, and safe
  mutation-boundary regressions: `86 passed`.
- No R6D work was started and nothing was committed.

R6C remains open. The next stage is R6C-C Forecast Governance Command UX. R6C-D
through R6C-H remain deferred to their approved stages.
