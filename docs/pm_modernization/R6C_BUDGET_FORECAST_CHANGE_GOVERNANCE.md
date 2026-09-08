# R6C Budget, Forecast, and Financial Change Governance

## 1. Status

**R6C IN PROGRESS.** R6A and R6B are closed. R6C-A through R6C-F are
complete. R6C-G and R6C-H remain open. This document records the verified
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

**R6C NOT CLOSED.** R6C-A through R6C-F are complete. Pre-release cleanup and
the broad final regression remain blocking in R6C-G and R6C-H.

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
Authorized users always retain a visible `Create Version` action. While a Draft
or Submitted version is open, the shared button presents a dimmed disabled state
and the adjacent reusable information control exposes the server-projected reason
on hover or keyboard focus; users without Budget management permission do not
receive the action. Approved history remains immutable and exposes
`Create Successor` when lineage-preserving revision creation is eligible.
Cost Code and optional Task use bounded server lookups. The three responsive
dialogs use the shared centered, scrollable, pinned-footer shell; validation stays
visible, entered values remain in the open dialog after a conflict, and an
authoritative Planning refresh replaces stale versions without automatic retry.

All finite Finance dropdowns use the same shared `AppControls.ComboBox` as
Projects and Tasks. Large project/task/cost-code lookups retain the shared
server-paged selector, but its UX is a continuous searchable result list:
additional bounded pages load while scrolling and table-style Previous/Next
pagination, page labels, and loaded/total result counts are not exposed inside
the dropdown.

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

## R6C-C Forecast Governance Command UX

**Status: COMPLETE.** The existing Finance -> Planning -> Forecast destination
is the only Forecast command UX. R6C remains open; R6C-D through R6C-H were not
started by this stage.

### R6C-C Authority Inventory

- CURRENT AUTHORITATIVE COMMAND: `generate_draft` creates one server-calculated
  Draft Forecast, its lines, source decisions, audit, and typed events in one
  Finance UoW. It resolves Planned Cost, posted Actual offsets, open
  Commitments, financial dimensions, project currency, Manual ETC decisions,
  and Risk contingency decisions on the server.
- CURRENT AUTHORITATIVE COMMAND: `submit_forecast` transitions a populated
  mutable Draft using the selected row version. `request_forecast_approval`
  creates the explicit Platform Approval request for the Submitted revision.
  These are deliberate separate user actions, matching the established Budget
  governance UX; neither action can partially perform the other.
- CURRENT AUTHORITATIVE COMMAND: Platform Approval `forecast.approve` applies or
  rejects through a fresh session-bound `ForecastApprovalParticipant`. The
  requester cannot decide their own request, and the deciding principal is the
  actor recorded on the Forecast.
- INTERNAL SUPPORT OPERATION: `create_forecast`, Forecast line add/update/delete,
  and direct domain transition helpers remain transaction-neutral application
  operations. They are not exposed by Forecast QML or its desktop command API.
  The R6B line DataTable remains a read projection, not a generic editor.
- NOT SUPPORTED: explicit successor creation, predecessor identity, regeneration,
  Draft metadata editing, and post-generation Manual ETC/Risk contingency CRUD.
  Generation assigns the next revision and the one-open-version invariant
  prevents parallel current drafts. Approval supersedes the previous approved
  revision. No unsupported button or synthetic lineage was added.
- DEAD/SUPERSEDED: no older Forecast desktop command, controller slot, presenter,
  QML dialog, route, DI registration, compatibility write adapter, or transaction
  wrapper was found. Nothing was retained as a legacy production path.

### R6C-C Command Architecture

The active path is QML -> Financials controller -> presenter command mapper ->
typed desktop DTO/API -> `FinanceGovernanceCommandBoundary` -> transaction-neutral
Forecast service -> Finance UoW -> commit -> typed ViewInvalidation -> existing
R6B Reader refresh. The desktop DTO uses canonical decimal strings and ISO dates;
the adapter converts finite monetary values to `Decimal`. There is no Forecast
`float()` conversion or persisted calculation in QML.

Generation uses `FinancialGenerateForecastCommand` with typed Manual ETC and
Risk contingency items. Submit and approval request use
`FinancialVersionedForecastCommand`, preserving the authoritative row version.
Approval/rejection use the shared Platform Approval desktop path and request ID,
not a Forecast-specific decision engine.

### R6C-C Generation And Source Semantics

Manual ETC is replacement authority, never extra ETC. A Cost Code-level amount
replaces remaining plan for that Cost Code; a Cost Code + Task amount replaces
only that matching slice. Overlapping dimensions and duplicate decisions are
rejected server-side. Manual inputs are generation-time decisions and cannot be
edited as generic generated lines.

Risk identity and lifecycle remain Register-owned. The bounded selector returns
only scoped, eligible open/in-progress/mitigated project Risks. Finance stores
only the explicit monetary contingency; no probability-times-impact engine was
introduced. Cost Code, Task, and Risk selectors use bounded server paging,
search, deterministic ordering, project/tenant/organization scope, and stale
lookup generation guards.

The server retains source-decision evidence for included, excluded, offset, and
replacement facts. As-of, ETC, EAC, VAC, currency, and supersession mathematics
were not changed. Currency is resolved from the selected Project financial
profile; the dialog communicates this without making currency a client-owned
input or adding FX behavior.

### R6C-C Lifecycle, Capabilities, And UX

The Forecast section exposes Generate, Submit, Request Approval, Approve, and
Reject only from server-projected capabilities. Manage, approval-request, and
approval-decision rights remain distinct; requester identity is included in the
read model so SoD is deny-safe. Capability state clears before Forecast refresh
and on destination reset, preventing privileged-button flicker or stale actions
after project/organization/permission changes.

The existing master/detail DataTables retain authoritative server paging,
filtering, sorting, explicit selection, and no first-row auto-selection. Commands
never mutate visible rows locally. Success refreshes Planning, Overview, and
Performance through the existing scoped invalidation/read flow. Conflicts are
not retried; the authoritative Forecast is refreshed and intentional input must
be reviewed. Shared mutation state prevents double submission and generation.

The centered dialogs use the shared scrollable body and pinned action footer.
Generation stages all inputs required by the one atomic backend operation and
states replacement/Risk/currency authority. Lifecycle dialogs show Project,
Forecast revision/name, status, as-of/generation basis, and decision notes.
Viewport, footer reachability, initial focus, Escape, and validation focus are
covered at 1024x640, 1280x720, 1366x768, 1440x900, and 1920x1080.

### R6C-C Concurrency, Atomicity, And Invalidation

All mutable operations preserve optimistic row versions. Stale Submit fails with
`STALE_WRITE`; a second open generation fails with
`PROJECT_FORECAST_OPEN_VERSION_EXISTS`, backed by the scoped unique constraint.
Approval request state permits one decision; Platform Approval owns the decision
transaction and enforces self-decision denial.

Forecast approval previously used an inner SQLAlchemy SAVEPOINT. Under SQLite's
deferred transaction behavior, a participant failure after the SAVEPOINT release
could leave the Forecast Approved while the Platform request rolled back. R6C-C
removed that nested transaction: the Platform Approval UoW is now the sole
physical transaction owner. Fault injection proves both the Forecast transition
and Approval decision roll back together. Existing generation audit-failure and
command-boundary commit-failure tests prove no partial root, line, source
decision, audit, or success invalidation.

Approval participants return canonical `ForecastVersionChanged` domain events.
They do not reintroduce the retired `forecasts_changed` signal. Approved events
invalidate Forecast planning and approved-basis projections; rejected/submitted
events invalidate planning only. Commit happens before observable invalidation.

### R6C-C PostgreSQL And Authorization Evidence

The repository Docker PostgreSQL 16 stack was recreated and migrated from
Alembic head. Live tests run through `app_runtime`, which is non-owner,
`NOSUPERUSER`, and `NOBYPASSRLS`. Governed generation persisted a Forecast and
Manual ETC line through the real command boundary. Cross-tenant and same-tenant
cross-organization commands were denied. Direct foreign-scope inserts into both
Forecast Line and Forecast Source Decision were denied. The bounded Forecast and
Finance lookup Readers also passed through the runtime role. Application-layer
tests separately deny generation without `forecast.manage`; RLS is defense in
depth, not application authorization.

### R6C-C Verification And Reconciliation

- Final targeted Forecast/Finance/Budget/controller/approval/read/concurrency
  matrix: `148 passed, 1 skipped`; responsive Forecast/Budget/read slice:
  `33 passed`.
- Live PostgreSQL R6C command/RLS matrix: `5 passed`; combined Forecast
  Reader/lookup/command runtime-role slice: `9 passed`.
- Forecast dialogs at all five required viewports: `10 passed` within the
  responsive matrix. Authored Forecast/host/workspace QML passes `qmllint`.
- Targeted Python compilation and `git diff --check`: PASS.
- Forecast transaction-neutrality, governed-port composition, typed-event
  retirement, and approval registration guards pass.
- The broad pre-existing P8 legacy-signal guard remains red for active
  `financial_changes_changed`, `commitments_changed`, and
  `cost_entries_changed` production paths (`5 failed, 29 passed`). It has no
  Forecast failure and is deferred to the owning R6C-D/R6C-F cleanup; R6C-C did
  not expand its frozen allowlist or modify those unrelated signals.
- No files were deleted because the source scan found no superseded Forecast
  production path. No compatibility marker or temporary R6C-C scaffold remains.
- No Financial Change UX, R6C-D, or R6D-R6G implementation was started. Nothing
  was committed by this implementation pass.

At R6C-C closure, the next approved stage was R6C-D Financial Change Governance
Command UX. Its completed implementation record follows.

## R6C-D Financial Change Governance Command UX

**Status: COMPLETE.** Finance -> Controls -> Change Control is the only
Financial Change workspace and command UX. R6C remains open; R6C-E through
R6C-H were not started by this stage.

### R6C-D Authority And Lifecycle

- CURRENT AUTHORITATIVE COMMANDS: create and versioned edit of a Draft Change
  Request; add, versioned edit, and versioned removal of Draft Budget, Forecast,
  or Schedule Impacts; versioned Submit; and Platform Approval Approve-and-Apply
  or Reject.
- INTERNAL SUPPORT OPERATIONS: approval participant apply/reject and the
  Budget, Forecast, and Scheduling authority calls used by an approved Change.
  They are not separate desktop or QML commands.
- NOT SUPPORTED: cancel, withdraw, reopen, generic JSON Impact editing, direct
  apply, and a separate post-approval apply queue. Approval and application are
  one existing atomic decision semantic, so `canApprove` governs the single
  **Approve & Apply** action; inventing a separate `canApply` button would expose
  a lifecycle the domain does not have.
- DEAD/SUPERSEDED: the broad `financial_changes_changed` signal and its Finance
  controller consumer are deleted. The obsolete generic scoped-emission helper
  left in the governance boundary after typed-event cutover is also deleted.
  No compatibility Change command API, presenter, dialog, route, transaction
  wrapper, or approval engine remains.

Only Draft requests and their unapplied Impacts are mutable. Submit freezes the
aggregate and creates one Platform Approval request. Reject preserves governed
history. Approve atomically applies all supported effects and marks the request
Applied; a second decision or application cannot create duplicate successors.

### R6C-D Command Architecture

The sole production path is QML -> Financials controller -> presenter command
mapper -> typed desktop DTO/API -> `FinanceGovernanceCommandBoundary` ->
transaction-neutral `FinancialChangeService` -> repositories/authority ports ->
one Finance UoW commit -> typed post-commit invalidation -> existing R6B Change
Reader refresh. No visible rows are mutated optimistically in QML.

Create resolves tenant, organization, Project, actor, Project currency, and the
current approved Budget/Forecast IDs and revisions on the server. QML never
supplies those bases as authority. Request and parent mutations carry the
request row version; Impact edit/removal also carries the Impact row version.
Stale writes fail with `STALE_WRITE` and are not automatically retried.

Desktop Impact DTOs preserve money as canonical decimal strings. The adapter
converts to `Decimal`; there is no Financial Change monetary `float()` path and
no FX or mixed-currency aggregation in QML.

### R6C-D Typed Impact Semantics

- Budget Impact records a proposed amount, currency, Cost Code, optional Task,
  and optional captured base Budget Line. It does not mutate Budget before
  approval. Apply delegates successor creation, revision allocation, line
  adjustment, supersession, and audit to the R6C-B Budget authority.
- Forecast Impact has the corresponding governed Forecast line semantics and
  does not mutate Forecast before approval. Apply delegates to the R6C-C
  Forecast authority; Financial Change does not duplicate source-decision,
  Manual ETC, EAC, or VAC calculation logic.
- Schedule Impact records a Task and requested dates. The server captures the
  Task version, validates the proposal through the Scheduling port, and applies
  it through the Task/Scheduling owner with `commit=False` inside the caller's
  Finance transaction. Finance imports no Task ORM and runs no CPM or dependency
  calculation.

Cost Code, Task, and base-line choices use bounded server-side search, paging,
deterministic ordering, tenant/organization/Project scope, and stale lookup
generation guards. Budget/Forecast line lookup is limited to the exact base
captured by the selected Draft Change; arbitrary IDs and non-Draft requests fail
closed. Type-specific domain validation rejects incomplete shapes, inactive or
unauthorized Cost Codes, cross-Project Tasks, stale Task snapshots, duplicate
targets, unsupported currencies, and immutable Impact type changes.

### R6C-D Approval, Bases, And Consistency

Platform Approval remains the only decision authority. `financial_change.manage`,
`approval.request`, and `approval.decide` remain distinct permissions, enforced
globally and at Project scope. Read facts project deny-safe create/edit/add/
remove/submit/approve/reject capabilities. Decision capability also compares the
authenticated requester user ID with the current principal, preventing a
requester from approving or rejecting their own request.

Submit and Apply both revalidate relevant captured Budget/Forecast authority.
Apply reloads current approved bases immediately before successor creation; any
ID or revision movement fails closed with a specific stale-base conflict. There
is no silent rebase, latest-version substitution, or apply-anyway path. Budget
and Forecast effects use the same database Session and UoW as the Change. The
Scheduling owner participates in that same transaction boundary, so mixed
effects are all-or-nothing in the current modular-monolith deployment.

Request transition, Platform Approval request, Impact/application evidence,
successors, audit, and domain events are staged before one outward commit. No
nested transaction or SAVEPOINT was added. Fault tests prove commit, audit,
Budget/Forecast/Schedule participant failures roll back the complete operation.
Post-commit notification failure is logged without undoing committed business
state.

### R6C-D UX And Invalidation

The Change destination retains R6B authoritative master/detail DataTables with
server paging, filtering, sorting, counts, explicit selection, and no first-row
auto-selection. Server-projected capabilities control Create, Edit, Add/Edit/
Remove Impact, Submit, Approve & Apply, and Reject. Capability state resets
deny-safe during refresh and context changes; shared mutation state prevents
double commands and stale async responses are ignored.

Centralized request, typed Impact, and lifecycle dialogs use the shared
scrollable-body/pinned-footer pattern. Required fields are marked and focus is
moved to invalid input. Dialogs preserve entered values after command failure,
support Escape/shared keyboard behavior, and fit 1024x640, 1280x720, 1366x768,
1440x900, and 1920x1080.

`FinancialChangeChanged` is the canonical typed event. Ordinary mutations
invalidate only Change Control. Applied events always invalidate Change Control
and add only the Budget, Forecast, or Schedule scopes represented by actual
effects. Correlation-scoped deduplication prevents refresh storms. Events are
dispatched after commit; no global Finance refresh was introduced.

### R6C-D PostgreSQL, Cleanup, And Verification

The repository Docker PostgreSQL 16 environment was recreated from Alembic head.
The live command suite ran through non-owner `app_runtime` with `NOSUPERUSER` and
`NOBYPASSRLS`. Legal same-scope Request and Impact commands succeeded. Foreign
tenant and same-tenant foreign-organization commands were denied. Direct foreign
Impact INSERT was rejected, while UPDATE and DELETE saw zero rows. Request and
Impact stale-version writes failed closed through the real command boundary.

- Focused Change command/domain/read/QML/approval/UoW/SQLite session/event slice:
  `72 passed`.
- Live PostgreSQL Finance governance command/RLS/concurrency slice: `7 passed`.
- Financial Change dialogs pass the five required viewport matrix. Python
  compilation and `git diff --check`: PASS. Runtime QML component tests are
  green; standalone `qmllint` and optional `ruff` are unavailable in `pmenv`.
- The P8 Financial Change stale-signal assertion was reconciled to the canonical
  typed event and `financial_changes_changed` now has zero production references.
  Current P8 result is `26 passed, 4 failed`; every remaining failure is owned by
  pre-existing Commitment/Cost signals (`commitments_changed` and
  `cost_entries_changed`). R6C-D did not alter or allowlist them.
- Search found no Financial Change compatibility workflow, deprecated action,
  direct Task persistence mutation, duplicate Budget/Forecast successor
  algorithm, nested transaction, or temporary delete-later scaffold.

R6C remains open. R6C-E completion evidence follows; R6C-F through R6C-H and
R6D-R6G remained untouched during the Financial Change stage.

## R6C-E Financial Setup Governance Command UX

**Status: COMPLETE.** R6C remains open. The next stage is R6C-F Integrated
Governance Hardening; it was not started as part of R6C-E.

### R6C-E Command Inventory And Boundaries

The authoritative Setup command inventory is:

- Financial Profile update and lifecycle transition.
- Organization Cost Code create, edit, activate, and deactivate.
- Project Cost Code restriction add and remove.
- Profile-owned default Cost Code, Budget control mode, Cost Code policy,
  billing method, funded/billable flags, financial dates, and currency update.

Financial Profile creation is an internal Project-creation support operation,
not a second Setup workflow. Rate Card/Rate Line writes, Actual and Commitment
lifecycle, Billing Preparation, Accounting delivery, Procurement, EVM, and
Task/Schedule configuration remain outside R6C-E. No unsupported restriction
type was invented: the persisted restriction is exactly Project-to-Cost-Code;
there is no Task, Resource, Role, Site, or Department restriction model.

The final write path is singular:

`Financial Setup QML -> Financials controller -> Financials presenter -> typed
desktop command -> ProjectManagementFinancialsDesktopApi ->
FinanceGovernanceCommandBoundary.financial_setup -> transaction-neutral
FinancialConfigurationService -> scoped repositories/audit -> one UoW commit ->
post-commit invalidation -> FinanceSetupReader refresh`.

The unused direct `FinancialConfigurationService` dependency on the desktop
facade, factory, runtime builder, and runtime resolver was deleted. The service
bundle's `financial_configuration_service` remains intentionally as a
`FinanceGovernedServicePort`: it is the governed internal module port used by
composition and test setup, not a direct-commit or desktop bypass. No Setup
compatibility API, fallback workflow, duplicate route, duplicate presenter, or
second visible Create Cost Code action remains.

### R6C-E Read Model And UX

`FinanceSetupReader` remains the only production read authority. Its immutable
SQL implementation now supplies the Profile plus independently counted,
server-paged, server-filtered, and server-sorted Cost Code and project allow-list
collections. Ordering is allowlisted and deterministic; searches are bounded
and tenant/organization/project scoped. QML performs no collection filtering,
sorting, count, eligibility, or authority calculation.

Controls -> Financial Setup contains a scalar Profile presentation, a Cost Code
DataTable, and a project allow-list DataTable. The contextual toolbar owns
Create Cost Code; selected-row actions own edit/status/restriction behavior.
Centralized Profile, Cost Code, restriction, and lifecycle dialogs use shared
currency/date/selector/dialog primitives, required-field validation, pinned
actions, busy state, and actionable server errors. Cost Code parent/default/
restriction selectors use bounded server search rather than preloading an
enterprise collection.

All four dialogs and the Setup section load at 1024x640, 1280x720, 1366x768,
1440x900, and 1920x1080. Escape closes each dialog and the shared
`EntityDialog.focusReturnTarget` contract restores keyboard focus to the
invoking action. Existing PM, Platform, and Inventory dialog consumers remain
green. Editable dialogs set initial focus on the first meaningful field;
standard shared-dialog tab traversal remains authoritative.

### R6C-E Profile And Cost Code Governance

Profile writes require the current Profile version. Cost Code edits and status
changes require the current Cost Code version. Stale writes raise explicit
concurrency conflicts and the controller invalidates the authoritative Setup
read rather than patching QML state. Profile status transitions retain the
existing Draft/Active/On Hold/Closed domain lifecycle.

The current domain treats currency as a versioned editable Profile field; it
does not yet define a dependent-financial-activity lock. R6C-E preserves that
actual server policy and does not pretend currency is client-read-only or invent
an FX/migration workflow. Setup commands contain no monetary amount and add no
float, Decimal conversion, rounding, or FX authority.

Cost Code uniqueness, normalized code/name rules, hierarchy acyclicity, active
ancestor rules, effective dates, paired external references, and lifecycle are
server-owned. There is no hard-delete command: deactivation preserves all
historical references, active children must be handled first, and a Cost Code
used as any Profile default cannot be deactivated. A default must resolve in the
same tenant/organization, be active/effective today, and, under restricted
policy, belong to the selected Project's allow-list.

Restriction uniqueness is enforced by the domain/database and duplicate add now
returns an explicit business error. Add/remove is scoped to the selected Project
and Cost Code. The restriction row is not versioned and does not advance a
Profile version; concurrent duplicate Add is protected by uniqueness, while
Remove is a scoped idempotent absence result. No historical Budget, Forecast,
Actual, Commitment, Billing, or Change row is rewritten by policy or restriction
changes.

### R6C-E Permissions, Atomicity, And Invalidation

The repository currently has one actual Setup write permission:
`finance.manage`; reads require `finance.read`. Both global permission and
Project-scoped permission/visibility are enforced for Project operations.
Server-projected `canEditProfile`, `canTransitionProfile`,
`canCreateCostCode`, per-row edit/status/restriction capabilities, and
`canManageRestrictions` default false before refresh and remain false for a
read-only or hidden Project. QML does not infer elevated authority.

All Setup writes execute in a fresh operation Session. Business mutation,
before/after Enterprise Audit evidence, and typed events are staged before the
single outward commit. Audit or commit failure rolls back state and audit and
cannot emit success invalidation. The shared Finance mutation guard rejects a
second command with `FINANCE_COMMAND_BUSY`. Commands are synchronous on the UI
thread and never populate local response state; successful completion marks
Readers stale, while project/org-scoped invalidation binding prevents an event
for one context from populating another.

Profile events invalidate the exact Project Profile/dependent Setup read.
Organization Cost Code events emit the organization-scoped
`financial_cost_code_catalog` hint so active selectors refresh. Restriction
events emit exact-project `financial_cost_code_restrictions` hints. Controller
refresh dependencies are limited to Controls, Planning, and Costs where Profile
or eligibility is projected. Dispatch is post-commit, correlation-deduplicated,
and never performs a global Finance refresh.

### R6C-E PostgreSQL And Test Evidence

The touched tables are `project_finance_profiles`,
`project_finance_cost_codes`, `project_finance_cost_code_restrictions`, and the
transactional Enterprise Audit/Event infrastructure already owned by the UoW.
The disposable PostgreSQL 16 environment was recreated from Alembic head. All
live commands ran through non-owner `app_runtime`, validated as `NOSUPERUSER`
and `NOBYPASSRLS`.

- Legal same-scope Profile update, Cost Code creation, and restriction Add pass
  through the real `FinanceGovernanceCommandBoundary`.
- Cross-tenant and same-tenant/cross-organization Profile access/update see no
  foreign row. Foreign Cost Code INSERT is rejected and UPDATE/DELETE affect
  zero rows. Foreign restriction INSERT is rejected and UPDATE/DELETE affect
  zero rows.
- Application authorization separately proves hidden-Project denial, missing
  `finance.manage` denial, and deny-safe read-only capabilities.
- Focused R6C-E command/read/rule/authorization/invalidation/QML suite:
  `36 passed`.
- Setup authorization and transactional audit regression plus desktop facade,
  presenter, and command-cutover regression: `76 passed` before the additional
  keyboard cases were added.
- R6C-A/B/C/D plus R6B Setup read regression: all `68` non-P8 tests passed.
- Live PostgreSQL R6C governance/RLS/concurrency suite: `8 passed`.
- Shared dialog regression across PM, Platform, and Inventory: `51 passed`.
- P8 remains `26 passed, 4 failed`. Reconciliation now shows all four failures
  are the pre-existing Cost-owned `cost_entries_changed` legacy signal; no
  Commitment failure remains. R6C-E did not modify or allowlist it. Its removal
  remains an R6D Cost cutover responsibility.

Python compilation passes. Repository QML runtime/static component tests pass.
Standalone `qmllint` and optional `ruff` remain unavailable in `pmenv` and were
not installed. No Rate Card write, Actual/Commitment redesign, Billing write,
Accounting integration, R6C-F, R6D, R6E, R6F, or R6G work was started.

## R6C-F Integrated Governance Hardening

**Status: COMPLETE.** R6C remains open for R6C-G cleanup and R6C-H final
closure only. R6C-F added no Finance product feature and did not start R6D-R6G.

### Integrated Architecture

The final integrated command path remains singular: a typed desktop command
enters `FinanceGovernanceCommandBoundary`, which creates one operation-scoped
Session/UoW, binds the Finance service, repositories, Enterprise Audit, and
transactional events to that Session, commits once, then publishes targeted
post-commit invalidation. Platform Approval owns its own fresh decision UoW and
injects that exact Session into Budget, Forecast, or Financial Change
participants. Readers remain immutable R6B query authorities.

R6C services and all three approval participants contain no `commit()` or
`rollback()`. The remaining Budget/Forecast `begin_nested()` uses are local
constraint-conflict translation scopes inside the caller-owned transaction;
they neither commit nor create a second authority. Financial Change mixed
Budget/Forecast/Schedule apply has no independent transaction boundary.

### Final Permission And Capability Matrix

All Project operations require both the global permission and the same
Project-scoped permission/visibility. Organization Cost Code creation without a
Project still requires active tenant/organization context.

| Capability | Required permission | Additional server-owned conditions |
| --- | --- | --- |
| Budget create/edit/delete/lines/submit/successor | `budget.manage` | visible Project; current row versions; mutable lifecycle; eligible dimensions; one-open-version rule; successor source approved |
| Budget request approval | `approval.request` | Submitted; current version; no existing request |
| Budget direct approve/reject/close | `budget.approve` | valid lifecycle and current version |
| Budget Platform decision | `approval.decide` | pending matching request; deciding principal is not requester |
| Forecast generate/create/input mutation/submit/regenerate | `forecast.manage` | visible Project; current parent/line versions; mutable lifecycle; authoritative source evidence; one-open-version rule |
| Forecast request approval | `approval.request` | Submitted; current version; no existing request |
| Forecast direct approve/reject | `forecast.approve` | valid lifecycle and current version |
| Forecast Platform decision | `approval.decide` | pending matching request; deciding principal is not requester |
| Change create/edit/Impact mutation | `financial_change.manage` | visible Project; Draft; current Request/Impact versions; valid target and base evidence |
| Change submit | `financial_change.manage` + `approval.request` | non-empty valid Impacts; current approved bases; no conflicting open Budget/Forecast |
| Change approve/reject/apply | `approval.decide` | pending matching request; non-requester; unchanged bases and target versions |
| Setup Profile, Cost Code, lifecycle/default/control/restriction writes | `finance.manage` | visible Project where Project-scoped; current version where versioned; lifecycle, hierarchy, eligibility, uniqueness, and default rules |

Permission alone is never presented as capability. Project visibility,
lifecycle, entity version/state, open-version constraints, requester identity,
approval status, and apply state are projected by the authoritative query.
`manage` does not imply approval. A genuine second principal succeeds; a
requester holding both management and decision permissions is still denied
approve and reject with `APPROVAL_SELF_DECISION_FORBIDDEN` for Budget, Forecast,
and Financial Change. Setup is not forced into Platform Approval because its
authoritative model does not require that workflow.

### Deny-Safe Presentation And Context Safety

Before each active Budget, Forecast, Change, or Setup authority read, the
controller clears that visible surface's privileged capabilities and
capability-bearing rows. Failed or delayed reads therefore remain denied rather
than displaying prior authority. Project switches clear all destination state.
Forecast and Change parent switches already clear their detail/child state;
Budget parent switching now also clears prior lines immediately. The existing
generation token rejects stale A/B/C selection/filter responses.

Refresh and command errors clear safely through the controller boundary.
Commands remain synchronously guarded by `FINANCE_COMMAND_BUSY`; no timer,
thread, event loop, optimistic local patch, or duplicate command path was added.
Tenant/organization matching remains mandatory for event consumption, and live
PostgreSQL tests prove that a different tenant or same-tenant foreign
organization cannot read or mutate the governed rows.

### Approval And Concurrency Hardening

Approval decisions now load the scoped `ApprovalRequest` with PostgreSQL
`SELECT ... FOR UPDATE OF approval_requests` before checking `PENDING`, SoD, or
invoking any participant. The row lock serializes Budget, Forecast, Change, and
approve-versus-reject races through one shared Platform invariant. The losing
transaction observes the committed terminal status and raises
`APPROVAL_ALREADY_DECIDED`; it cannot execute duplicate downstream effects.

The live `app_runtime` race test holds the first decision lock, proves a second
runtime transaction blocks, commits `REJECTED`, and proves the contender then
observes `REJECTED`. A separate service guard proves decision code cannot fall
back to the unlocked repository read.

Budget stale header/line/parent writes, submit/delete races, open-version and
revision races, approval conflict translation, successor uniqueness, and
immutable approved history remain green. Forecast stale mutation/submit,
one-open generation, successor supersession, source evidence, and immutable
approved history remain green. Financial Change stale Request/Impact,
submit/apply/reapply, and audit rollback remain green.

New cross-family tests move the approved Budget only, Forecast only, and both
bases after Change submission. Apply fails closed with the exact Budget or
Forecast stale-base code, performs no silent rebase, creates no additional
successor, and leaves both Change and Approval pending. The existing mixed
Budget+Forecast test proves one atomic apply and the audit-fault test proves all
successors and Schedule effects roll back together.

### Fault, Audit, And Authority Boundaries

- Validation, authorization, lifecycle, optimistic-concurrency, and participant
  failures roll back the business mutation and fail-closed audit together.
- Commit failure emits no success invalidation. Post-commit invalidation or
  notification failure cannot undo committed business state.
- Budget, Forecast, Change, and Setup audit writes share the command Session.
  Platform decision audit shares the Platform decision Session.
- Schedule effects continue through Task-owned command authority; Finance does
  not import or directly mutate Task ORM. Project does not regain Budget truth,
  and Resource/Assignment/Time, Procurement, Rate, Actual, Commitment, Billing,
  and Accounting ownership are unchanged.
- Decimal amounts and canonical decimal strings remain authoritative. QML uses
  numeric conversion only for versions, paging, and display mechanics; it does
  not calculate Finance amounts. Currency remains explicit, with no FX or
  unlike-currency aggregation. Existing float EVM/Cost calculations are R6E
  scope and were not changed.

### Final Invalidation Map

| Mutation family | Exact read destinations/scopes |
| --- | --- |
| Budget | Finance `overview`, `planning`, and `performance`; typed Budget read invalidation |
| Forecast | Forecast version/line and approved-basis scopes; Finance `overview`, `planning`, and `performance` |
| Financial Change draft/submit/reject | `financial_change_workspace` / Finance `controls` |
| Financial Change apply | Change workspace plus only represented `financial_change_budget_basis`, `financial_change_forecast_basis`, and/or `financial_change_schedule`; affected Finance destinations only |
| Setup Profile | exact Project `financial_profile`; dependent `controls`, `planning`, and `costs` |
| Setup Cost Code catalog | organization `financial_cost_code_catalog`; dependent bounded selectors |
| Setup restriction | exact Project `financial_cost_code_restrictions`; dependent bounded selectors |

Dispatch remains post-commit and correlation-deduplicated. Reads emit nothing.
Controller teardown/reopen does not duplicate subscriptions, and no generic
global Finance refresh or event loop was introduced.

### PostgreSQL Security Evidence

The repository PostgreSQL 16 compose environment was recreated through Alembic
and the complete R6C command/RLS file passed `9` tests. `app_runtime` is verified
`NOSUPERUSER`, `NOBYPASSRLS`, and non-owner. Legal same-scope commands pass.
Foreign tenant and same-tenant/foreign-organization access fails closed for
Budget/BudgetLine, Forecast/ForecastLine/ForecastSourceDecision, Financial
Change/Impact, and Setup Profile/Cost Code/restriction surfaces. Direct foreign
INSERT is rejected and scoped UPDATE/DELETE sees zero rows. Application-layer
permission denial is tested separately from RLS.

### SQL Characterization

The rerunnable R6C-F characterization test records current SQLite statement
counts without imposing a speculative threshold:

| Family | Observed command counts |
| --- | --- |
| Budget | create `14`; line add `12`; line update `11`; submit `9`; approval request `21`; decision `18`; successor `16` |
| Forecast | generate `23`; input add `12`; submit `10`; approval request `22`; decision `16`; regenerate successor `23` |
| Change | create `11`; Impact add `15`; Impact update `16`; submit `27`; decision/apply `36` |
| Setup | Profile update `3`; Cost Code create `7`; update `6`; restriction add `12`; remove `10` |

Characterization exposed a real Approval notification N+1: recipient discovery
issued one `role_permissions` query for each of 30 roles. The repository now
resolves all role IDs for `approval.decide` in one inverse lookup and then loads
bindings only for matching roles. Budget request dropped `51 -> 21`, Forecast
request `52 -> 22`, and Change submit `57 -> 27`. Remaining repeated
tenant/organization and audit statements in mixed Change apply are fixed-size
per authority/audit operation, not per result row. Existing server-bounded
Budget, Forecast manual ETC/risk, Change target, and Setup selector tests remain
green.

### Verification And Remaining Work

- R6C A-E command/domain/read/participant matrix: `164 passed`; added SoD and
  participant transaction guards: `4 passed`.
- Platform Approval, invalidation, controller/presenter, responsive QML,
  keyboard/Escape, and cross-module shared-dialog matrix: `192 passed, 1
  skipped`.
- Post-N+1 Approval/notification/SQL characterization matrix: `22 passed`.
- R6B destination/read/bounded-query/invalidation regression: `99 passed`.
- Architecture/module/read-write guards: `45 passed`.
- PostgreSQL runtime-role/RLS/concurrency matrix: `9 passed`.
- P8 currently reports `25 passed, 4 failed`. All four failures are the same
  pre-existing Cost-owned `cost_entries_changed` producer/allowlist mismatch,
  untouched by R6C and assigned to R6D. No R6C-owned P8 failure remains; no dead
  signal was restored to satisfy the frozen allowlist.
- Runtime QML tests cover all required viewports, including 1024x640, and shared
  `EntityDialog` focus return across Finance and existing PM/Platform/Inventory
  consumers. Standalone `qmllint` and optional `ruff` remain unavailable in
  `pmenv`; they were not installed.
- Targeted Python compilation and `git diff --check` pass. No files were
  committed.

R6C-F has no blocker. R6C-G cleanup and R6C-H broad final closure remain. This
stage stops here: R6C-G, R6D, R6E, R6F, and R6G were not started.
