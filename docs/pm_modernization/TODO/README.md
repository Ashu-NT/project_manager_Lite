# PM Modernization — Consolidated Pending Work

Generated 2026-08-06 by reading every file in `docs/pm_modernization/` and separating
done/partial/pending. This is the single place to look for what's left; the other docs
in this folder describe what already exists and why. Three fully-superseded implementation
logs were deleted as part of the cleanup; their disposition is recorded at the bottom.

Updated 2026-08-08 after completing the numbered CQRS plan and reconciling the subsequent
Desktop Adapter Responsibility Audit. CQRS Phases 0A-0C and 1-6 are complete. The
Session/Unit-of-Work investigation remains a separate future architecture decision; it is
not an unfinished CQRS phase.

## 0. Desktop adapter responsibility hardening (complete 2026-08-09)

Source: `../CQRS/project_management_cqrs_existing_state_audit.md`, "Desktop Adapter
Responsibility Audit." This work was identified after the original consolidated TODO was
generated and therefore takes priority over starting the much larger Finance Phase C.

- **DA0 - Guardrails and characterization (complete 2026-08-08):** architecture guardrails
  are implemented and all six P0 plus ten P1 rows are characterized or, for the two confirmed
  dead Financials methods, usage-verified and deleted.
- **DA1 - Composition leaks (complete 2026-08-08):** Resources, Projects, and Tasks now use
  explicit public application queries; the desktop architecture register contains no repository
  imports or private collaborator access exceptions.
- **DA2 - Security and error boundaries (complete 2026-08-08):** Tasks reports partial
  permission-scoped loads, Dashboard propagates approval failures, and dead PM calendar mutation
  compatibility stubs were deleted in favor of Platform Admin's canonical calendar CRUD.
- **DA3 - Domain policy (complete 2026-08-08):** Resources, Scheduling, Register, and Dashboard are complete. Normalized
  resource-rate decisions belong to `ResourceService`, certification lifecycle status belongs
  to `ResourceCertification`, baseline actions belong to `ProjectBaseline`, task remaining
  duration belongs to `Task`, and default-calendar selection belongs to Platform's
  `EnterpriseCalendarService`. Register overdue/triage policy belongs to `RegisterEntry`, and
  `RegisterService` applies it after RBAC scope filtering. Dashboard consumes the same Register
  snapshot and canonical resource-utilization policy across every desktop projection.
- **DA4 - Read/report extraction (complete 2026-08-08):** Timesheet period transitions now
  return immutable aggregate facts built from the entries already loaded by the command, and
  assignment options/details use one tenant-scoped joined application query. No speculative
  Reader was introduced.
- **DA5 - Duplicate and dead-code removal (complete 2026-08-08):** removed the remaining
  schedule-impact wrapper and Projects reflection fallback after parity tests. The Resources
  rate/currency options fallback and dead Financials procurement projection had already been
  deleted in DA1/DA0 respectively.

### DA0/DA1 exception deletion register

These are verified pre-existing violations, not permanent exemptions. The architecture suite
holds the exact set so both additions and removals require an explicit update. Delete each test
exception in the same change that removes its runtime violation.

| Exception group | Current locations | Removal gate | Status |
| --- | --- | --- | --- |
| Repository contracts imported by desktop Resources | None; all three imports removed | Resources pilot | CLOSED 2026-08-08 |
| Private collaborator access | None; all Tasks access/resource lookup reach-throughs removed | DA1 Tasks migration | CLOSED 2026-08-08 |
| Application objects constructed in desktop code | None; runtime composition injects `ConstraintValidator` | Scheduling composition migration provides the constructed collaborator | CLOSED 2026-08-09 |
| Private platform module imports | None; PM consumes public money and approval-label package exports | Expose and consume public platform contracts | CLOSED 2026-08-09 |

**DA0 exit gate:** all P0/P1 behaviors have characterization coverage; architecture scanners
reject synthetic violations; every remaining exception above has a named DA1 removal owner.

Implementation checkpoint (2026-08-08):

- `test_pm_desktop_adapter_architecture.py` pins the exact repository-import, private-access,
  application-construction, and private-module exception sets; it also blocks reverse
  application/domain imports and proves the scanners detect synthetic violations.
- `test_pm_desktop_adapter_da0_characterization.py` pins the schedule-impact baseline
  divergence and the former Projects/Tasks adapter-boundary behavior. Migrated cases are converted
  to assertions against their replacement public contracts rather than retained as legacy tests.
- Dashboard authorization/infrastructure error propagation was already corrected and remains
  covered by `test_phase0a4_other_safety_corrections.py`.
- All live P1 behaviors now have focused coverage: desktop-owned rate decisions, Resources
  composition fallbacks, duplicate rate precedence, assignment-preview
  calculation/query behavior, overload thresholds, and Register/Dashboard risk parity.
- Removed the caller-free PM Financials procurement methods, DTOs, serializer, exports, and
  wiring. A deletion guard prevents their accidental restoration before Phase C introduces a
  typed project-source Procurement contract.
- Corrected Dashboard risk filtering from the nonexistent `IN_REVIEW` status to canonical
  `IN_PROGRESS` and added parity coverage against Register ordering.
- Focused checkpoint: 31 tests passed. DA0 is complete; DA1 Resources is next.

DA1 Resources checkpoint (2026-08-08):

- Added tenant/RBAC-aware `TaskService.list_assignments_for_resource()` as the public
  application query used by the Resources workspace.
- Removed `AssignmentRepository` from the desktop API/factory, the `_assignments` fallback,
  desktop-side `ResourceAvailabilityService` construction, private repository/calendar
  reach-through, and the now-empty resolution module.
- Runtime composition now injects the existing availability service directly; absence produces
  the existing unavailable/empty UI state rather than constructing a hidden service graph.
- Focused checkpoint: 22 tests passed. Resources is complete; DA1 continues with Projects,
  followed by Tasks.

DA1 Projects checkpoint (2026-08-08):

- Added canonical `require_any_project_permission()` with centralized denial evidence for
  project-scoped read/manage alternatives.
- Added public `ResourceService.list_for_project_workspace()` and
  `ProjectResourceService.list_for_project_workspace()` queries. Tenant/organization scope and
  project RBAC are now application responsibilities.
- Deleted the desktop access helper and all `_user_session`, `_resource_repo`,
  `_tenant_context_service`, and `_project_resource_repo` reach-throughs from Projects.
- Verified a project-scoped manager can read the project's resources without receiving the
  unrelated global `resource.read` permission. Targeted checkpoint: 21 tests passed.
- Combined desktop/architecture regression: 63 tests passed. Projects is complete; DA1
  continues with Tasks.

DA1 Tasks checkpoint (2026-08-08):

- Added public `ProjectService.list_for_task_workspace()`,
  `ProjectResourceService.list_for_task_workspace()`, and
  `ResourceService.list_for_task_workspace()` queries. They enforce canonical global/project RBAC
  while repositories retain tenant/organization isolation.
- Removed exception-message parsing and all `_project_repo`, `_resource_repo`,
  `_project_resource_repo`, `_tenant_context_service`, and `_user_session` access from the Tasks
  desktop adapter. Obsolete fallback helpers and their parameters were deleted rather than retained
  as transition code.
- Added a real-service scoped `task.read` test proving project filtering and resource/membership
  access, converted desktop characterization tests to the public contracts, and reduced the
  private-collaborator architecture exception set to zero.
- Focused checkpoint: 28 tests passed. Broader task/desktop-adapter checkpoint: 124 tests passed,
  458 deselected, with three pre-existing warnings. DA1 is complete; DA2 is next.

DA2 checkpoint (2026-08-08; transition mechanism removed 2026-08-09):

- DA2 originally added a partial-load result around the adapter's per-project loop. Section 0A's
  atomic scoped Task SQL query made that loop and its failure mode obsolete. `TaskListResultDto`,
  `list_all_tasks()`, skipped-project state, QML warning, and transition tests are deleted; tenant,
  organization, and project RBAC are now resolved before one catalog query executes.
- Confirmed Dashboard approval failures already propagate under the Phase 0A4 correction and kept
  its regression coverage instead of adding a second partial-failure mechanism.
- Removed caller-free PM Scheduling `update_calendar`, `add_holiday`, and `delete_holiday` methods,
  their command DTOs, duplicate adapter helpers, exports, and transition tests. Calendar mutation
  remains available only through the canonical Platform Admin calendar API/controller; PM retains
  calendar reads and working-day calculation.
- Focused DA2 checkpoint: 42 tests passed. Broader Tasks/Scheduling/adapter checkpoint: 145
  passed, 436 deselected, with three pre-existing warnings. Canonical Platform Admin calendar CRUD:
  14 passed after updating its test fixture to the hardened `ActiveScopeIds` repository contract.
  DA2 is complete; DA3 is next.

DA3 Resources checkpoint (2026-08-08):

- `ResourceService.update_resource()` now decides whether normalized hourly-rate/currency values
  actually differ from the persisted resource. Actual rate changes still require optimistic
  concurrency and retain the optional explicit effective date for dedicated rate-card workflows;
  ordinary callers default through the service's injected `Clock`.
- Desktop Resources and the CSV importer now forward full-form values without pre-reading,
  comparing persisted rates, or calling `date.today()`. The duplicate adapter/importer policy
  and the obsolete `RESOURCE_RATE_EFFECTIVE_ON_REQUIRED` path are removed.
- `ResourceCertification.status_on()` owns valid, expiring-soon, and expired boundary rules and
  returns typed `CertificationStatus`; the desktop serializer only maps its value into the
  unchanged DTO.
- An architecture deletion guard prevents the removed policy from returning to adapters.
  Combined Resources, characterization, and architecture checkpoint: 54 passed. DA3 remains in
  progress; Scheduling lifecycle/derived-state extraction is next.

DA3 Scheduling checkpoint (2026-08-08):

- `ProjectBaseline.can_submit/can_approve/can_reject` now expose the same lifecycle legality
  enforced by its transition methods; the desktop formatter only projects those properties.
- `Task.remaining_duration_days` owns the progress-based duration calculation. The duplicate
  desktop `scheduling_utils.py` implementation was deleted, not retained as compatibility code.
- Platform `EnterpriseCalendarService.get_default_calendar()` now resolves the active
  organization's canonical active GLOBAL calendar under `task.read` and tenant/organization
  scope. Platform's desktop API exposes the query and PM consumes it instead of independently
  listing/filtering calendars.
- The former uniform-hours calendar mutation policy requires no migration because DA2 deleted its
  caller-free PM mutation surface. The separate first-working-day `hours_per_day` snapshot
  approximation remains the documented P2 DTO-design follow-up; changing that response shape is
  outside this no-DTO-change tranche.
- Domain, Platform service, real PM-to-Platform wiring, QML presenter, and architecture checkpoint:
  45 passed. The broader PM Scheduling/Baseline/architecture regression passed 69 tests with 658
  unrelated tests deselected. DA3 remains in progress; Register triage ownership is next.

DA3 Register checkpoint (2026-08-08):

- `RegisterEntry.is_overdue_on()` now owns terminal-status and due-date interpretation, while
  `RegisterEntry.triage_key()` owns severity-first, overdue-first, due-date, and title ordering for
  an explicit as-of date.
- `RegisterService.list_entries()` applies the canonical ordering only after project RBAC filtering;
  `get_project_summary()` reuses the same domain rule for urgent ordering and overdue totals.
- The desktop Register builder now only coerces filters and forwards the service result. Its
  duplicate `register_status_utils.py` policy helper was deleted rather than retained as transition
  code, and the serializer projects `RegisterEntry.is_overdue_on()` into the unchanged DTO.
- Domain, application query, desktop API, QML presenter, DA0 characterization, and architecture
  checkpoint: 33 passed. The complete PM/architecture regression passed 729 tests; its one
  unrelated existing failure is the hard line-limit guard for generated `shared_resources_rc.py`
  and Platform `enterprise_calendar.py`. That checkpoint closed Register; Dashboard followed below.

DA3 Dashboard and workspace-performance checkpoint (2026-08-08):

- `ResourceUtilizationBand` now owns the canonical idle/stable/hot/near-capacity/overloaded
  boundaries. Reporting rows expose policy facts; Dashboard and Scheduling desktop serializers
  only project those facts. The duplicate Scheduling status formatter was deleted.
- `RegisterService.get_dashboard_snapshot()` returns summary and high-risk rows from one
  RBAC-filtered load using `RegisterEntry.triage_key()`. Dashboard no longer injects or calls
  `RegisterService` from its desktop adapter.
- Dashboard loads tasks, batch assignments, resources, KPI, schedule, and Register data once per
  snapshot. A no-baseline view no longer executes EVM/EVM-series queries. Portfolio obtains its
  heatmap and dependency projection from one typed executive snapshot.
- Repeated permission checks now use a 30-second validated-principal lease. The QML runtime
  heartbeat and application activation force persisted revalidation, preserving revocation and
  graceful re-login behavior. Same-process authority changes still rebuild or clear the principal
  immediately.
- Repository entitlement reads use the existing ID-only active scope contract. Full tenant and
  organization entity validation remains on login, context switch, mutation, and explicit runtime
  revalidation paths.
- Scheduling uses the previously-unused bounded `WorkingDaySnapshotCalendar`; CPM calculations run
  against one range load. Resource-load reporting also uses range resolution instead of one
  calendar query per day.
- Persistent evidence is in
  `test_dashboard_portfolio_workspace_performance_measurement.py`. On the single-project SQLite
  fixture, Dashboard improved from approximately 0.70s/1,501 SQL statements to 0.08s/96, and
  Portfolio from approximately 0.30s/494 to 0.06s/68. These are regression evidence, not a
  production SLA.
- Existing scale fixtures confirm the authorization lease removes fixed per-operation overhead:
  Collaboration inbox/workspace reads moved from 53/56 SQL statements to 3/6, EVM series from 50
  to 15, Portfolio scenario comparison from 62 to 12, capacity pool from 20 to 5, and Finance
  snapshot/EVM reads from 45/47 to 10/12. Their persistent budgets now pin the lower counts.
- Focused resource, Dashboard, architecture, auth, and runtime checkpoint: 68 passed. The broad PM
  and architecture run covered 599 tests: 596 passed in the complete run and its three stale
  Phase 3B measurement budgets passed after recalibration. The directly affected Platform security
  set passed 126 tests; its one unrelated existing failure is the global PostgreSQL RLS inventory,
  which does not yet classify newly added Project Finance tenant tables. DA3 is complete; DA4
  followed below.

DA4 Timesheets checkpoint (2026-08-08):

- `TimesheetPeriodAggregate` is an immutable Platform application result containing period state,
  entry count, total hours, and project IDs. Submit/approve/reject/lock/unlock build it from the
  same entries already required for validation, audit, and events; the desktop serializer no
  longer fetches entries or calculates totals.
- `TaskService.list_timesheet_assignment_contexts()` and
  `get_timesheet_assignment_context()` enforce canonical `task.read` plus project RBAC before
  returning contract-owned immutable rows. `SqlAlchemyAssignmentRepository` obtains project,
  task, assignment, and resource context in one tenant/organization-scoped joined query.
- Both the assignment picker and assignment snapshot consume that application query. Their prior
  project-to-task-to-assignment loops and per-assignment resource lookups were deleted rather than
  retained as fallbacks.
- The QML-facing `TimesheetPeriodSummaryDesktopDto` and assignment descriptor fields are unchanged.
  Persistent measurement verifies one joined assignment data query, with at most one additional
  bounded runtime-session lease statement; transition characterization verifies desktop
  serialization performs no second resource-period entry read.
- Focused Platform, PM desktop, isolation, architecture, and measurement checkpoint: 52 passed.
  DA4 is complete; DA5 duplicate/dead-code removal is next.

DA5 cleanup checkpoint (2026-08-08):

- `ScheduleChangeImpactService` now owns approved-baseline resolution and the standard delayed-task
  scenario. Tasks and Scheduling therefore cannot disagree about `requires_approval` based on
  entry point. The standalone `compute_schedule_impact` function and all exports were deleted.
- Projects `create_project` and `update_project` explicitly forward every declared command field
  to the exact `ProjectService` contract. `call_with_supported_kwargs` and its `inspect.signature`
  filtering were deleted, so field/signature drift now fails tests instead of silently dropping
  data.
- The Resources `resource_options_builder.py` fallback named by the original DA5 register had
  already been removed during DA1/DA3; the current option builder contains only enum presentation
  options and no rate/currency precedence.
- Focused Projects, Scheduling, Tasks, characterization, and architecture checkpoint: 35 passed.
  DA5 is complete.
- Bounded DA4/DA5 regression matrix: 195 passed. Two unrelated existing architecture size guards
  remain red in untouched files: `scheduling_engine.py` is 449 lines against its 410-line growth
  budget, while the hard 1,200-line inventory flags generated `shared_resources_rc.py` and Platform
  `enterprise_calendar.py`. Four existing SQLAlchemy delete-count warnings remain in cascading
  time-entry cleanup tests.

Architecture exception closure checkpoint (2026-08-09):

- Platform Money publicly exports its decimal conversion helpers, and Platform Approval publicly
  exports its display/context/module label helpers. PM no longer imports underscore-prefixed
  modules from either platform package.
- Runtime composition constructs and injects `ConstraintValidator`; the Scheduling desktop
  builder no longer instantiates an application object.
- The architecture exception sets are empty. Desktop adapter responsibility hardening DA0-DA5 is
  complete. Public-export, Dashboard/Financials, Scheduling-injection, and architecture closure
  checkpoint: 20 passed. Finance Phase B item 8 was completed next and is recorded in section 1.

## 0A. Database-side workspace queries and pagination (complete 2026-08-09)

This post-CQRS phase is the next PM modernization priority before Finance Phase C. The desktop
presenter must not load an entire growing collection merely to filter, sort, count, and slice 25
rows. Pagination belongs to an application read contract and its infrastructure reader, not QML,
the presenter, or a generic command repository.

Rules for every migrated collection:

- apply tenant and organization scope, project-level RBAC, search, filters, and deterministic
  ordering before the page boundary;
- return immutable read rows plus explicit page metadata and filtered totals; obtain overview
  metrics from separate scoped aggregate queries rather than reconstructing them from one page;
- use a unique ordering tie-breaker. The current numbered desktop controls use deterministic
  database offset pages; introduce a cursor/keyset HTTP contract when measured concurrent churn or
  page depth makes offset paging unsuitable, without moving filtering back into the presenter;
- fetch selected-row detail independently, and replace unbounded dropdown payloads with bounded
  searchable option queries where their cardinality can grow;
- stream or batch exports independently. `page_size=99999` and similar interactive-pagination
  bypasses are forbidden; and
- preserve fail-closed authorization. A count, empty state, page boundary, or option lookup must
  not disclose rows outside the active tenant/organization/project scope.

| Workspace collection | Current disposition | Approved action |
| --- | --- | --- |
| Tasks, including All Projects | Database-side tenant/org/RBAC scope, structured/free-text filters, WBS-effective rollups, aggregates, ordering, and page boundary | **COMPLETE.** Cross-project loading and partial-load transition DTOs were deleted. WBS parent options use a separate selected-project hierarchy query; exports iterate bounded 500-row database pages. |
| Projects catalog | Database search/status/order/count and offset page under tenant/org/project RBAC | **COMPLETE.** Overview status metrics are scoped SQL aggregates; exports iterate bounded 500-row pages. |
| Resources catalog | Database active/category/search filters, employee/department/site joins, aggregates, ordering, and offset page | **COMPLETE.** Employee dialog options remain a distinct selector contract and are not used to filter or page the catalog; exports iterate bounded 500-row pages. |
| Register and Risk catalogs | Shared database project/type/status/severity/search query with aggregates, real page metadata, and database-limited urgent queue | **COMPLETE.** Previously cosmetic QML paging now reaches SQL and reports the filtered total. |
| Timesheets review queue | Fixed-query database page joined through period/resource/assignment/task/project, with tenant/org/project RBAC and aggregate hours | **COMPLETE.** Removed the 200-row desktop ceiling; one assignment-period's detail entries remain a bounded detail read. |
| Financial configuration line views | Database offset pagination, scope, counts, and deterministic ordering are already implemented | **Keep.** Do not regress these readers to presenter slicing. |
| Legacy Financials combined `CostItem` list | Complete project list is filtered in the presenter; model is scheduled for Phase C removal | **Do not modernize dead-end code.** Phase C replaces it with typed Actual and Commitment ledger readers with their own database page contracts. |
| Scheduling activities/timeline | CPM, float, criticality, delay, hierarchy, and diagnostics are calculated from the complete selected-project graph before display paging | **Do not page source tasks before calculation.** Keep the authoritative schedule calculation complete; introduce a persisted/materialized schedule read model only if measured scale requires database-side interactive filtering. |
| Dashboard operational tables | Bounded rows are derived from cross-service KPI/report aggregates | **Do not mechanically push paging into entity repositories.** Keep bounded aggregate contracts; create a dedicated operational Reader only when realistic-scale measurement exceeds the recorded budget. |
| Portfolio heatmap/scenario/capacity | Values are calculated from complete accessible-portfolio facts; Phase 3C already removed N+1 acquisition | **Do not page facts before portfolio calculations.** A future materialized portfolio projection may add cursor pagination without corrupting totals/rankings. |
| Collaboration feeds | Recent activity/mentions/presence use explicit bounded read limits | **Keep bounded.** Add cursor delivery only when cross-session notification delivery becomes a user-facing feature. |

Implementation sequence: Tasks -> Projects -> Resources -> Register/Risk -> Timesheet review queue.
Each cutover deletes its presenter-side filter/pagination helper in the same change after parity,
tenant-isolation, RBAC, ordering, total-count, and query-growth tests pass. Calculated-projection
exceptions above are permanent semantic decisions unless a separately measured materialized read
model replaces them; they are not permission to return unbounded entity rows.

Completion checkpoint (2026-08-09): all five growing workspace collections above now cross a
typed application read contract and execute scope, filtering, aggregate counts, deterministic
ordering, and page boundaries in SQL. Real-composition integration coverage lives in
`test_workspace_database_pagination.py`. Scheduling, Dashboard, Portfolio, bounded collaboration
feeds, and the Phase-C-bound legacy Finance list retain the dispositions recorded in this table;
they are not unfinished 0A work.

Verification checkpoint: 65 focused database/desktop/presenter/architecture tests passed, followed
by 165 tests covering the remaining QML-through-PM functional segment. The full PM directory run
reached 62% without failure before its five-minute measurement-suite timeout; a second functional
run exposed one stale task test fake, which was migrated to the shared fake workspace query and
then passed with its affected six-test cluster. Query budgets are pinned at 4/4/4/5/3 statements
for Projects/Tasks/Resources/Register/empty Timesheet review, including the shared entitlement
guard statement.

## 1. Finance — Phase B (complete)

Source: `../project_finance_existing_state_and_implementation_plan.md` §19 Phase B, items 7-8.

- **Item 7 closed (2026-08-12).** `CostPolicyEngine`/`ledger.py`'s own "planned" figures
  (feeding KPIs/dashboards/`FinanceSnapshot.planned`) now source from the versioned,
  allocated-to-task `ProjectPlannedCostVersion` (cut over 2026-08-11, alongside the legacy
  `CostItem` deletion), not `ProjectResource.planned_hours` — see the doc's Phase B item 7
  sub-section for what the original 2026-08-06 rejection got right (the granularity
  mismatch was real) versus what it got wrong (the "no freshness mechanism" concern; the
  versioned snapshot is a governed, explicitly-triggered action like Budget/Forecast/
  Baseline generation, not something that needs auto-recalculation). The third, competing
  call site the rejection cited — `LaborCostEngine.calculate_project_labor_plan_vs_actual`,
  a resource-envelope-capacity report, not a "planned cost" duplicate — was unreached by any
  production caller and was deleted (2026-08-12) rather than merged or left half-alive; a
  distinct resource-capacity report remains deliberately deferred to the still-unscoped
  `ProjectLaborPlan`/`LaborPlanAllocation` future phase if wanted.
- Baseline provenance (which exact rate-card line/version valued each baseline task) is not
  recorded — would need a baseline financial-snapshot extension. Not part of item 7's
  closure; still open if ever needed.
- **Item 8 (complete 2026-08-09):** replaced the QML combined "Budget" cost-line section with
  separate project-level Profile, Budget Versions, Budget Lines, Rate Cards, and Planned Costs
  views. A canonical application projection owns RBAC, scope, totals, and label resolution with a
  warm-path ceiling of 14 SQL statements. Growing line collections use explicit 50-row offset
  pages with totals and in-section navigation. The Views menu reaches configuration when no legacy cost
  row exists; cost rows open Actuals. `FinancialsBudgetSection.qml` was deleted with no temporary
  fallback. Underlying Phase B regression: 86 passed; projection/isolation/pagination: 6 passed;
  combined application/desktop/QML/architecture checkpoint: 51 passed.

Finance Phase C in section 2 is complete under the pre-launch, fresh-database decision recorded
below. No customer data exists and the product will not ship an upgrade path from the retired
combined cost register.

## 2. Finance — Phase C: actual ledger, commitments, time, procurement, periods (complete)

Source: same doc, §19 Phase C. Items 1-8 are complete. The prerequisite
`TRANSITION(PF-A0-UOW-BRIDGE)` cleanup that items 2/6 depend on is done (governed
commands now own their own Unit of Work). ADR gate: ADR-PF-004/006/007/008 already
ACCEPTED, so the ADR gate itself is not blocking.

1. **Organization financial periods + closure/lock policy (foundation complete 2026-08-09).**
   Platform-owned periods are separate from scheduling calendars and have direct tenant/org
   scope, RLS metadata/migration, organization-serialized non-overlap checks, optimistic
   concurrency, immutable open -> closed -> locked lifecycle metadata, fail-closed Enterprise
   Audit, `finance.read`/`finance.manage` enforcement, normal-posting rejection for missing or
   non-open periods, composition wiring, and a typed desktop adapter. There is deliberately no
   delete, reopen, or late-post compatibility path. The existing `finance.manage` permission is
   the coarse initial close/lock boundary; a dedicated authority/separation-of-duties rule and
   late-adjustment policy remain the explicit product gate in section 5 before such commands may
   be added.
2. **Canonical ProjectCostEntry lifecycle (complete 2026-08-09).** Manual actual and signed
   adjustment drafts use dedicated create/update/delete-draft/submit/approve/reject/post/reverse
   commands. The aggregate owns transaction Money, immutable base-Money and FX snapshots,
   posting period/date, cost-code/task/resource dimensions, source identity/content hash,
   actor/timestamps, row version, and exact linked negative reversals. Persistence has direct
   tenant/org/project scope, database pagination/counts, composite scoped foreign keys, source and
   reversal uniqueness, RLS metadata, and database triggers that reject posted financial-fact
   updates or deletion. The service enforces active project finance configuration, effective and
   allowed cost codes, dimension scope, open periods, canonical command permissions, fail-closed
   audit, approval-owned Unit of Work, and deterministic source retry/conflict behavior.
3. **Canonical PM commitments (complete 2026-08-09).** One PM-owned projection header per
   Procurement purchase order and one versioned line per purchase-order line preserve opaque
   source identity without importing or foreign-keying Inventory implementation packages.
   Monotonic immutable source-revision snapshots make retry idempotent and reject conflicting or
   out-of-order delivery. Lines own Decimal quantity/rate, transaction/base Money and immutable FX
   snapshot, project/cost-code/task/supplier/site dimensions, lifecycle, matched amount, and
   optimistic row version. Sent/partially received/fully received exposure is committed minus
   matched; closure/cancellation releases unmatched exposure, while fully received does not hide
   exposure before a delayed actual arrives. Immutable signed match/reversal rows link only posted
   Procurement receipt-accrual `ProjectCostEntry` facts and prevent duplicate actual matching.
   Four directly scoped/RLS tables, composite foreign keys, database amount/source/match
   constraints, immutable revision/match triggers, stable database pagination, fail-closed Audit,
   RBAC/project authorization, savepoint conflict handling, and migration `q4r5s6t7u8v9` complete
   the boundary. The permanent ADR-PF-011 owned-store foundation is now complete: Time and
   Procurement have separate tenant/org-scoped outboxes and PM Finance owns its inbox, with
   leasing, bounded retry/dead-letter, deduplication, ordering, quarantine, RLS, immutable-envelope
   guards, and composition wiring. C.5 now supplies Procurement event creation, dispatch, and the
   financial consumer at contracts/composition boundaries without direct PM-to-Inventory
   implementation imports.
4. **Approved-Time event + idempotent labor-cost consumer (complete 2026-08-09).** Platform
   Time approval atomically writes immutable, monotonic per-entry snapshots to its owned outbox.
   PM Finance consumes through its inbox, validates scope/revision, resolves and snapshots the
   effective COST/HOUR rate, requires an open period and project default cost code, and writes a
   posted actual plus immutable labor detail. Corrected approval creates an equal reversal and
   replacement; later LOCKED/unlocked transitions create no posting. Database transport supports
   immediate bounded dispatch and startup replay with retry/dead-letter state.
5. **Procurement project-source events and PM consumers (complete 2026-08-09).** PO SENT and
   later recognized status revisions create/update PM commitment projections; POSTED accepted
   receipt lines create canonical accrual actuals and match remaining commitment value. Project
   and task references remain opaque to Procurement and are resolved by PM. Reason-required
   cancellation after approval releases remaining operational/financial exposure; full receipt
   and close preserve source/match history.
   Source/outbox and inbox/financial mutations are atomic with durable retry/dead-letter state.
   Post-send commercial amendment approval and supplier-invoice reclassification remain named
   future source-owner capabilities because neither aggregate/command exists yet.
6. **Canonical command cutover complete 2026-08-09.** Combined `CostItem` runtime writes,
   desktop commands, QML editor/bulk mutations, CSV import, approval handlers, and the
   `cost.manage` umbrella were deleted. Manual actuals now use idempotent typed
   `ProjectCostEntry` commands; planned costs remain versioned planning snapshots and
   commitments remain source-owned Procurement projections. Posted actuals cannot be edited or
   deleted and use explicit reversal. Canonical audit/commit failures roll back the command Unit
   of Work. The read-only `CostItem` projection and all repository/service/DTO/presenter/QML
   surfaces were subsequently deleted by C.7.
7. **Fresh-database clean break complete 2026-08-11.** The team confirmed that there are no
   customers or production rows to preserve. The proposed migration-run/checkpoint tables,
   import-draft command, `DATA_EXCHANGE/IMPORT_ROW/LEGACY_MIGRATION` source variants, transition
   evidence, dual-read, backfill, quarantine, and test seeder were therefore deleted rather than
   promoted into permanent architecture. Revision `t7u8v9w0x1y2` is the undeployed clean-break
   head and drops `cost_items`; its downgrade exists only for Alembic graph reversibility.
   Planned, committed, and actual reads now compose exclusively from versioned planned-cost
   lines, PM commitment projections, and posted/reversed `ProjectCostEntry` facts. Baselines,
   reporting, forecasts, dashboard, and portfolio consume those canonical facts. Approved Time
   is not recomputed as a second actual because its consumer already posts canonical entries.
8. **Canonical QML ledgers complete 2026-08-11.** Actuals show the paged `ProjectCostEntry`
   lifecycle with source, status, posting date, approval capabilities, and reversal capability;
   posted rows have no generic edit/delete. Commitments show a separate server-paged PM-owned
   projection with PO-line identity, lifecycle state, committed/matched/remaining values,
   delivery/order date, task link, and source revision. The desktop boundary receives
   `ProjectCommitmentService` through composition and does not import Inventory implementation
   packages.

Phase C.1 verification checkpoint: all 9 new domain/service/tenant/RBAC/desktop/migration/
architecture tests pass; the combined period and Project Finance persistence-guard suite passes
19 tests. Fresh-database Alembic upgrade/downgrade passed and the graph remains single-headed.
The final selected C.1/PM-finance/migration/graph checkpoint passes 30 tests.
The broader desktop-registry/PM-finance check passed 24 tests; its two failures are pre-existing,
unrelated Site datetime and inactive-organization provisioning defects. No temporary C.1 code or
deletion-register entry was introduced.

Phase C.2 verification checkpoint: all 7 new domain/service/governance/tenant/FX/reversal/
migration tests pass. The combined C.1/C.2, budget lifecycle, authorization hierarchy, project
scope, role reconciliation, and Phase-A finance security run passes 105 tests. Alembic remains
single-headed at `p3q4r5s6t7u8`. No legacy `CostItem` reader or writer was modified, no dual-write
or compatibility adapter was introduced, and no C.2 code is temporary. Items 6-8 remain the named
cutover/removal gates for legacy writes, reads, and QML.

Phase C.3 verification checkpoint: all 5 focused domain/source-revision/lifecycle/matching/tenant/
migration tests pass, plus the permanent architecture test forbidding direct PM <-> Inventory
module imports. The combined C.3 and Project Finance persistence/period architecture checkpoint
passes 20 tests, and the existing 7-test C.2 actual-ledger suite remains green against the new
schema. A fresh Alembic upgrade reaches the single head `q4r5s6t7u8v9`; immutable source-history
and match triggers are present. No legacy `CostItem` path changed, no direct cross-module import,
dual-write, in-memory event bridge, compatibility adapter, temporary file, or deletion-register
item was introduced. One pre-existing PM desktop runtime import used only for Inventory runtime
type checks was removed; composition continues to supply the opaque reservation capability.
The migration also downgrades independently to C.2 revision `p3q4r5s6t7u8` while preserving the
actual ledger.

ADR-PF-011 delivery-foundation checkpoint (complete 2026-08-09): migration `r5s6t7u8v9w0` adds
the two source-owned outboxes and PM Finance-owned inbox. Five focused lifecycle/migration tests
pass, including atomic rollback, active-scope isolation, lease ownership, retry/dead-letter,
transport deduplication, conflict/stale quarantine, reversible schema, and immutable-envelope
guards; Alembic remains single-headed. There is no process-local delivery shim, cross-module
implementation import, temporary file, or deletion-register item.

Phase C.4 verification checkpoint: six focused approved-Time tests cover first approval,
rejection no-op, approval/outbox rollback atomicity, correction reversal/replacement, rate snapshot
retention, LOCKED no-op, closed-period rejection with durable retry evidence, inbox/outbox
completion, post-commit UI refresh isolation, and reversible immutable migration. The combined
C.1-C.4 period/ledger/commitment/delivery/architecture checkpoint passes 43 tests and Alembic
remains single-headed at `s6t7u8v9w0x1`; the selected related Time lifecycle/workspace checkpoint
passes 17 tests. No process-local financial delivery, thread/timer, direct cross-module implementation
import, temporary file, dual-write, legacy `CostItem` mutation, or deletion-register item was
introduced. The desktop correction command is available; final QML ledger action/dialog work
remains at the existing C.8 UI cutover gate.

Phase C.5 verification checkpoint: seven focused tests cover SENT commitment creation, partial and
full receipt accrual/matching, close/cancel, price variance, task/project source resolution,
non-project isolation, duplicate empty replay, closed-period retry evidence, and PO/receipt outbox
atomic rollback. The selected C.1-C.5 plus existing Procurement lifecycle/domain/composition/
architecture checkpoint passes 73 tests. No direct PM <-> Inventory business-package import,
cross-module foreign key, temporary adapter, dual-write, background thread/timer, legacy
`CostItem` mutation, migration, or deletion-register item was introduced.

Phase C.6 verification checkpoint: the canonical actual command/security suite passes 17 tests,
including idempotency and fail-closed audit rollback. The complete legacy-report compatibility
surface passes 103 tests with 1 skip. Its five remaining failures are pre-existing and unrelated:
the scheduling-engine line budget, three unresolved-labor-rate export fixtures, and one module-
entitlement expectation. Targeted `qmllint` reports no missing controller members after the PM
controller typeinfo was synchronized. The temporary historical read-model test seeder introduced
for C.6 was deleted by the C.7 clean break; no production writer or dual-write path was restored.

Phase C.7/C.8 clean-break checkpoint (2026-08-11): all runtime `CostItem` domain, ORM, mapper,
repository, service, desktop DTO/API, presenter, controller, and QML list/editor files are removed.
The transition import/checkpoint implementation and its tests are removed. The finance reader and
portfolio reader use separate scoped canonical authorities and aggregate only after acquisition;
architecture tests enforce scope and prohibit cross-source SQL fan-out. Alembic revision IDs are
unique and the graph is single-headed. Focused canonical finance, commitment, command, migration,
CQRS, and QML checks pass. Obsolete legacy fixtures and phase-measurement suites were deleted or
rewritten against canonical facts; neutral SQL measurement helpers were extracted for the
remaining performance suites. Full test collection succeeds, and the cleanup also found and fixed
one real baseline leftover (`planned_labor_total`). Canonical labor rows from every source are
aggregated and identity-redacted unless the caller has project-scoped `finance.read_sensitive`.

Phase C.9 finance-authority clean break (2026-08-11): `Project.planned_budget` and
`Project.currency` were deleted from the domain aggregate, ORM, mapper, repository, project
commands, CSV import, desktop DTOs, presenters, and QML editor. Migration
`u8v9w0x1y2z3` drops both database columns. `ProjectFinancialProfile.currency_code` is now the
only project-finance currency authority, including project-resource and reporting defaults.
The project catalog, finance snapshot, portfolio heatmap, and scenario readers obtain currency
from the profile and approved budget totals from `ProjectBudget`/`BudgetLine` in scoped SQL.
Baseline/EVM no longer treat budget authorization as a cost-loaded performance baseline, and
the two-way currency synchronization plus its transition marker were deleted. This is a direct
pre-release cutover: no backfill, dual read, compatibility alias, or dormant legacy branch exists.
Verification: the complete PM suite passes (`559 passed`), and the targeted architecture,
migration-graph, service-composition, CQRS, and QML suite passes (`54 passed`, with only the
unrelated repository-wide generated-file size guard deselected).

## 3. Finance — Phase D complete (2026-08-11)

- **Phase D.1A — COMPLETE (2026-08-11): canonical forecast persistence and lifecycle.**
  Added PM-owned `ProjectForecast`/`ForecastLine` domain models, tenant/org/project-scoped
  repositories, composed `ForecastVersionService`, explicit `forecast.manage` and
  `forecast.approve` permissions, fail-closed financial audit entries, optimistic concurrency,
  one-open/one-approved version rules, approval supersession, and a reversible forced-RLS
  migration (`v9w0x1y2z3a4`). Forecasts carry an `as_of_date`, generation mode, immutable
  business revision, currency, and approval history. Lines persist Decimal Money, cost-code/
  task/period dimensions, and explicit automatic/manual origin. Automatic lines cannot be
  stored without a source type, source id, and snapshot timestamp. This is a pre-release clean
  cutover: no legacy forecast backfill, dual read, compatibility facade, or temporary code was
  added.
- **Phase D.1B — COMPLETE (2026-08-11): canonical automatic ETC generation.** The composed
  `ForecastGenerationService` creates one complete draft, its ETC lines, durable source-decision
  evidence, and fail-closed audit in one transaction. It reads the latest complete planned-cost
  snapshot at or before `as_of_date`, nets posted actuals by cost-code/task, includes only each
  commitment's unmatched open balance, and then reduces remaining plan by both actuals and open
  commitments. Taskless offsets are distributed deterministically within the cost code.
- **D.1B precedence is fixed and tested:** open commitments always remain explicit ETC; a manual
  ETC estimate replaces only remaining-plan ETC in its cost-code/task scope and cannot hide an
  open commitment; an explicitly valued contingency linked to an active project risk is additive.
  Generic risk severity is never converted into money. Reversed/future actuals, credits,
  closed/cancelled commitments, exhausted plan, and manual overrides retain reason-coded evidence
  instead of disappearing. Evidence-backed zero ETC is a valid forecast; a source-empty generation
  request is rejected.
- Migration `w0x1y2z3a4b5` adds the tenant/org/project-scoped source-decision table, reconciled Money
  checks, source/task references, forced PostgreSQL RLS, and linked-risk line semantics. There is no
  backfill, dual-read, compatibility branch, or temporary transition code.
- **Phase D.2 - COMPLETE (2026-08-11): governed budget/forecast/schedule change control.** PM now owns
  tenant/org/project-scoped `FinancialChangeRequest` and typed impact records with immutable
  business revisions, optimistic row versions, snapshotted approved budget/forecast bases, exact
  target-line deltas, lifecycle actors/timestamps, applied-version references, fail-closed audit,
  and Platform Approval separation of duties. Approval atomically supersedes the snapshotted
  approved budget/forecast and creates approved successor versions; stale bases, open drafts,
  negative results, duplicate targets, unsupported dimensions, and audit failure block or roll
  back the whole decision. Forecast successor lines and durable source decisions retain explicit
  `base_forecast` or `financial_change` lineage. Schedule impacts snapshot exact task versions and
  apply through the PM task owner's batch command. Only unstarted execution leaves are eligible;
  project-calendar validation, one dependency recalculation, and exact-result verification occur
  inside the approval transaction. Mixed budget/forecast/task changes roll back together.
- Migration `pfchg_d2_001` adds scoped change-request/impact tables, composite ownership FKs,
  lifecycle and typed-shape checks, indexes, forced PostgreSQL RLS, and the new forecast-lineage
  constraints. It is the sole Alembic head and is reversible. This is a direct pre-release cutover:
  no backfill, compatibility path, dual read/write, legacy change model, or temporary transition
  file exists. Planner finance-read capability was made coherent with its existing budget,
  forecast, and financial-change write responsibilities; sensitive finance remains separately
  protected by `finance.read_sensitive`.
- **Contract ownership correction:** the provisional `contract` impact and ambiguous task-level
  planned-hours delta were deleted before release. Procurement commitment rows are read-only PM
  projections and may change only through authoritative procurement revisions. PM project contract
  value does not yet exist and remains behind Phase E/ADR-PF-010 product decisions; D.2 does not
  create a fake contract authority or leave blocked/dead fields.
- **Phase D.4 - COMPLETE (2026-08-11): disposable canonical finance read models.** The scoped
  project snapshot, cash-flow, analytics, EVM, and batched portfolio paths now read Decimal Money
  from approved budget versions, the latest approved/superseded forecast version valid for the
  requested as-of date, net posted/reversed actual entries, and unmatched open Procurement
  commitments. ETC is the approved forecast total; EAC is posted actual plus approved ETC; VAC is
  approved budget minus EAC. Open commitments remain a separate control and are never added to EAC
  a second time. Historical as-of reads select the applicable superseded approved forecast rather
  than silently using today's version.
- **Read-model ownership rule:** `FinanceSnapshotFacts`, `FinanceControlFact`, application snapshot,
  cash-flow, analytics, and portfolio rows are rebuilt on demand, have no ORM/table/repository/write
  command, and are disposable without data loss. The sources of truth remain the versioned budget/
  forecast aggregates, immutable posting/reversal ledger, and Procurement-owned commitment
  projection. An architecture test blocks a finance-snapshot persistence authority from appearing.
- Cash flow now uses actual posting dates and approved forecast periods instead of `max(planned,
  committed)` heuristics. EVM retains baseline-owned BAC/PV/EV and canonical posted AC, but EAC/ETC/
  VAC use the approved forecast and are unavailable when one does not exist; the former CPI fallback
  is deleted. Portfolio cost pressure now uses EAC minus approved budget and no longer performs
  per-project labor-rate calculation to manufacture `actual - planned` variance.
- The transient `ForecastCostService`, EAC method enum/formulas, runtime composition, tests, desktop
  fallback path, recalculation action, fake invoiced/paid commitment totals, and duplicate Finance
  "Earned Value" card were deleted. The QML forecast card now identifies approved revision/as-of and
  displays approved budget, posted actual, ETC, EAC, and VAC only.
- **Phase D.5 - COMPLETE (2026-08-11): governed finance report/export parity.** The disposable
  snapshot now carries an explicit project-currency basis, period granularity, sensitive-detail
  state, canonical source lineage, and exact Decimal reconciliation evidence for posted actuals,
  open commitments, and approved forecast ETC. A mismatch fails closed before presentation.
- Excel and PDF consume one shared finance export projection. Both identify the requested as-of,
  generation timestamp, approved budget/forecast IDs and revisions, forecast as-of, redaction
  state, canonical control totals, reconciliation deltas/status, and bounded ledger page metadata.
  Source drill-down retains source/cost-code/reference/task/resource IDs, actual financial-period
  IDs, and forecast period dates.
- Finance ledger exports require `report.export`, `finance.export`, `finance.read`, and matching
  project scope. Offset pagination has a hard 500-row page limit; report totals and controls always
  come from the full reconciled snapshot, never from the page. The unused deprecated
  `infrastructure/reporting/exporters.py` compatibility wrapper was deleted.
- **Phase D.7 - COMPLETE (2026-08-11): governed lifecycle and reporting workspace.** Forecast now
  combines the canonical approved ETC/EAC/VAC controls with selectable forecast revisions and their
  persisted source lines. Change Control exposes selectable governed requests, snapshotted budget/
  forecast bases, typed impacts, and applied owner references. Variance exposes only approved or
  superseded schedule baselines and clearly labels its stored plan-to-plan schedule/planned-cost
  movement so it cannot be mistaken for actual-cost performance.
- Reports is now a real finance section rather than a placeholder. Its fixed contextual toolbar
  provides Excel/PDF export, passes the selected governed schedule baseline, and delegates to the
  D.5 canonical reconciled snapshot/export projection. The desktop and QML layers perform no
  finance calculations. Forecast-line and change-impact reads revalidate ownership against the
  selected scoped project before child retrieval.
- The exception-swallowing `build_baseline_variance` path, misleading financial export placeholder,
  empty `FinancialsInsightsSection.qml`, and stale nonexistent `FinancialsWorkspaceState.qml`
  module entry were deleted. No alias, compatibility branch, duplicate formula, persisted snapshot,
  temporary adapter, or transition code was introduced.
- **Phase D float retirement - COMPLETE (2026-08-11):** PM finance, project budget, portfolio
  budget/variance, resource rate, project-resource rate/hours, baseline cost/variance, and assignment
  hours now cross the desktop boundary as canonical decimal text. Eight PM-owned persisted money,
  rate, and quantity columns use the platform `Numeric` precision conventions; percentage columns
  remain intentional ratios. Revisions `pfnum_d8_001` and `pfnum_d8_002` provide the schema cutover.
- `Money.from_legacy_float`, `decimal_from_legacy_float`, their exports/tests, and the PM formatter
  float branch were deleted. The dead baseline unassigned-budget allocation branch was also removed;
  baselines consume only canonical immutable planned-cost lines. Architecture tests prevent the
  converters, transition markers, or Float-backed PM financial columns from returning.
- **Phase E** (billing preparation/revenue projections/external accounting): **in progress**.
  ADR-PF-010 was accepted on 2026-08-11 and the product decisions in section 24 items 10-15
  are resolved. PM owns commercial preparation and managerial projections; Accounting owns
  statutory invoices, receivables, payments, tax, and ledger truth.

Phase D.1A-D.2 verification: focused financial-change and forecast lifecycle/lineage/migration
coverage passes (`22 passed`). Combined D.2, forecast, task hierarchy/domain, schedule-impact,
RBAC reconciliation, and session-permission coverage passes (`53 passed`). The comprehensive
affected budget/forecast/change/task/schedule/RBAC checkpoint passes (`95 passed`). Architecture
coverage excluding the known hard-line-limit test reports `152 passed`, `2 failed`: one stale guard
still opens the removed `repositories/cost.py`, and one stale growth budget allows 410 lines for the
pre-existing 449-line scheduling engine. Neither touches D.2. The excluded repository-wide hard-size
guard still identifies generated `resources/shared_resources_rc.py` and platform
`enterprise_calendar.py`.
RBAC/security coverage passes (`44 passed`); PM desktop adapter architecture passes
(`12 passed`); migration graph passes (`11 passed`, with only the
unrelated repository-wide generated/platform size guard deselected). The previous D.1A canonical
PM baseline passed (`567 passed`, 29 warnings); the current D.1B run reached 89% with no failures
before the five-minute command limit. A combined run that also includes the older `src/tests/pm`
tree reports 12 pre-existing scheduling-test contract mismatches (legacy `ValueError`/clamping
expectations and legacy constraint-field fixtures); none touches Project Finance.

Phase D.4 verification: focused canonical read-model, as-of forecast selection, reversal,
desktop-mapping, security, disposal-guard, and CQRS architecture coverage passes (`38 passed`). The
broader budget/forecast/change/actual/commitment/reporting/portfolio compatibility suite passes
(`101 passed`, 10 warnings). Architecture/QML coverage passes 153 tests; its only three failures are
the already documented stale removed-`cost.py` guard, scheduling-engine growth budget, and the
repository-wide generated/platform hard-size guard. No D.4 architecture or QML guard fails.
Portfolio measurement now enforces the improved D.4 heatmap graph (`13 + 4N` statements for N
projects, previously `12 + 6N`) and zero per-project rate-resolution calls; all three measured sizes
pass. The complete PM run reached 73% before the five-minute limit; its only emitted failures were
the three stale performance expectations, which were corrected and then passed separately.

Phase D.5 verification: the broad finance/reporting/commitment/portfolio selection passes
`241 passed` (`354 deselected`, 21 dependency warnings). Focused real Excel/PDF, source-lineage,
bounded-page, reconciliation, redaction-state, and distinct-export-permission coverage passes. The
architecture suite passes `153` tests; its only three failures remain the documented stale removed-
`cost.py` guard, scheduling-engine growth budget, and repository-wide generated/platform hard-size
guard. No D.5 boundary, persistence, or deleted-wrapper import failure exists.

Phase D.7 verification: focused lifecycle ownership, authorization propagation, governed-baseline,
and canonical report-delegation coverage passes `6` tests. The broader PM finance/financial/reporting
selection passes `167 passed` (`427 deselected`, 19 dependency warnings). PM desktop-boundary and
canonical read-model coverage passes `22` tests; existing presenter/QML runtime coverage passes
`13` tests. `qmllint` reports no warnings or errors for every changed financial workspace QML file.

## 4. Finance — transition-code register status

Source: same doc §20 "Transition-code deletion register." No created transition code remains.
The only retained row is a future Phase E mechanism that has never been created:

| Component | Removal gate |
| --- | --- |
| Legacy financial permission aliases/feature flags | Phase E final role/API/controller inventory — not created yet |

Phase D float-retirement verification: canonical persistence/DTO/baseline/assignment and migration
graph checkpoint passes `54` tests. The broader PM finance/resource/portfolio/baseline/assignment
selection passes `342` tests (`253 deselected`, 22 dependency warnings) after correcting stale
Decimal-contract fixtures. Phase E implementation is proceeding under accepted ADR-PF-010.

- **F0 — `report.view` finance-authorization boundary, full closure (complete 2026-08-11).** The
  2026-08-02 A0 pass replaced `report.view` with `finance.read`/`finance.read_sensitive` only for
  `FinanceService`; `ReportingService` (EVM, cost breakdown, cost source breakdown, labor detail)
  and `DashboardService` (cost-source/EVM/KPI financial fields) still authorized on `report.view`
  alone. Both now gate financial-authority methods on `finance.read`/`finance.read_sensitive`,
  while `report.view` correctly remains sufficient for genuinely non-financial reports (Gantt,
  resource load, critical path), and mixed schedule/financial DTOs (`get_project_kpis`,
  dashboard data) redact financial fields for a `report.view`-only caller instead of denying the
  whole call. See `../project_finance_existing_state_and_implementation_plan.md` Phase A0
  implementation progress and the transition-code register (§20) for detail. Regression:
  `src/tests/project_management/test_project_finance_phase_a0_security.py`, 18 passed.

## 5. Finance — resolved Phase E product decisions

Source: master doc section 24 and accepted ADR-PF-010.

- First-release billing methods are time-and-materials, fixed-price, and cost-plus. Unit and
  recurring billing remain deferred.
- PM prepares governed billing payloads only. It never creates authoritative invoices,
  receivables, payments, tax postings, or general-ledger records.
- Fixed-price preparation uses PM-owned schedule lines, optionally linked to task milestones;
  time-and-materials uses approved time plus an immutable billing-rate snapshot; cost-plus uses
  posted cost plus an immutable markup snapshot.
- Expense capture is deferred to a future Expenses capability. PM may consume externally posted,
  reconciled expense cost facts as billable sources.
- PM provides contract, billable, externally invoiced, and revenue projections only. Statutory
  revenue recognition remains in Accounting.
- The vendor-neutral outbound contract is `project_billing_preparation.v1`; external outcomes are
  consumed as idempotent, append-only reconciliation evidence.
- Closed periods reject new preparation. Corrections use linked reversal/replacement preparations
  in an open period rather than mutating historical evidence.
- Billing evidence is append-only with configurable retention of at least seven years and legal
  hold support.

Phase E implementation checkpoint (2026-08-11):

- Complete: governed billing profile/schedule/preparation/source-lock/external-event domain and
  persistence foundation; migration `pfbill_e1_001`; forced tenant/org RLS; typed decimal-text
  `project_billing_preparation.v1` contract; approval handlers; all three approved source methods;
  append-only idempotent external outcomes; and the read-only Billing Preparation desktop/QML view.
- Complete: preparation rows are database-paginated and latest external outcomes are fetched in one
  batched query rather than an N+1 loop.
- Pending: a real Accounting publisher/worker adapter, because no target Accounting module/system
  exists yet; PM will not manufacture a fake authoritative invoice path.
- Pending: disposable commercial revenue/profitability projections with sensitive-margin redaction,
  plus complete governed command dialogs and the final no-transition/no-dead-code inventory.
- Verification: focused Phase E/domain/migration/persistence/service/desktop/QML runs pass; latest
  checkpoints include `18`, `41`, `35`, `12`, and `24` passing tests. The expanded PM financial/
  billing selection passes `48` tests and the combined architecture checkpoint passes `60` tests,
  with clean `qmllint`.

## 6. PM Enterprise UI/UX — pending items

Source: `../README.md`, "PM UI/UX Inspection & Improvement Plan" section (Phases 1-11) and
the audit's "Known Limitations."

- **Phase 3 — Resource Assignment Visibility (complete 2026-08-11):** the Assign Resource dialog
  now invokes the existing typed availability preview and assignment-policy validation whenever a
  resource is selected. It displays overallocation, conflicting projects, skill/certification
  evidence, warnings, and block reasons inline, and prevents submission when either policy blocks.
  No availability or authorization rule is duplicated in QML.
- **Phase 4 — Lazy Loading Feedback (⬜ not started):** every `LazySectionLoader` section
  needs a `LoadingOverlay` while busy, an `EmptyState` when empty, and an `InlineMessage`
  danger + Retry button on load failure (pattern is written out in the source doc).
- **Phase 10 — Permission and Capability Handling (⬜ not started):** RBAC-gated buttons
  (Submit Baseline, Approve/Reject, Apply Leveling, Import) are always visible regardless of
  role. Add `can*` bool Q_PROPERTYs to each workspace controller, computed from
  `AuthorizationEngine.has_permission()` (table of required properties is in the source doc).
- **Phase 11 — Tests and Verification (partial):** Phase 3 `previewAssignment` mapping coverage is
  complete. Add/extend the remaining tests for Phase 2, 5, 7, and 10 behaviors listed in the source
  doc (presenter row-mapping tests, `addTimeEntry` not triggering a full refresh, DataTable height regression
  check, `can*` property tests against a mock `AuthorizationEngine`).
- **No export infrastructure**: `infrastructure/exporters/` is empty. All export actions must
  stay disabled with a tooltip until Excel/PDF/Gantt renderers exist behind an adapter — do
  not ship empty stubs.
- **No tree-table component**: WBS hierarchy in Tasks uses a flat filtered list with
  on-demand children. Functional, but a dedicated tree-table component may be needed for deep
  WBS hierarchies later.
- **Async progress UX not wired**: `AsyncThresholdGuard` exists in the backend but no
  controller currently calls `classify_*`/`should_run_async()` before dispatching a LARGE+
  operation (recalculate schedule, leveling, forecast, schedule-impact preview, portfolio
  demand, report renders).

## 7. Team Collaboration — pending items

Source: `../TEAM_COLLABORATION_UPGRADE_PLAN.md` and `../TEAM_COLLABORATION_AUDIT_FINDINGS.md`
(2026-08-02 ground truth; supersedes README's collaboration claims wherever they disagree).

- **Phase 2 — cross-session delivery (open decision, not started):** notification
  persistence exists but nothing delivers a notification across sessions/users in real time.
  Needs a product decision between the Tier A/B/C options in the upgrade plan before any
  implementation starts.
- **Phase 3 — real notification channels (not started):** blocked on Phase 2.
- **Deferred, no committed timeline:** document version history; the "Delegate" approval
  quick-action.
- Notification persistence itself (Phase 1) is implemented but explicitly **not a shipped
  user-facing feature** — it has zero desktop consumer today; don't assume it's live.

## Deleted docs (2026-08-06 cleanup)

These were fully-superseded, no-longer-accurate, or complete-with-no-pending-work. Their
content is preserved in git history if a future reconciliation needs the detailed rationale
(rate precedence edge cases, budget concurrency proofs, etc.):

- `rate_card_cost_engine_cutover_plan.md` — status was "implemented and tested," zero pending
  items; substance is already captured in the master doc's §11.4 and Phase B item 4.
- `project_budget_lifecycle_plan.md` — status was "implementation complete and verified,"
  zero pending items; substance already captured in §11.5 and Phase B item 5.
- `project_planned_cost_snapshot_plan.md` — worse than merely done: its design (field name
  `planned_hours`, a single `is_complete` flag, optional non-authoritative
  `assignment_id` with `SET NULL`, no dual-version-token reconciliation) does **not** match
  what was actually built (`allocated_planned_hours`, three completeness flags
  `rates_complete`/`allocations_complete`/`cost_codes_complete`, required
  `source_assignment_id` with no live FK, dual optimistic-concurrency tokens on
  `TaskAssignment` and `ProjectResource`). Keeping it risked misleading a future reader about
  the real implementation; the accurate description lives in the master doc's §11.6.
