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

DA2 checkpoint (2026-08-08):

- Added `TaskListResultDto` with `tasks`, `skipped_project_ids`, and `is_partial`. Only
  `PERMISSION_DENIED` is converted to a partial result; tenant/context and all other business errors
  remain typed failures and propagate.
- Carried the partial-load signal through the Tasks presenter/view model/controller and display a
  warning above the task table without presenting raw project IDs to the user.
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

## 1. Finance — Phase B, remaining

Source: `../project_finance_existing_state_and_implementation_plan.md` §19 Phase B, items 7-8.

- **Item 7, second half (not done):** `CostPolicyEngine`/`LaborCostEngine`'s own "planned"
  figures (feeding KPIs/dashboards/`FinanceSnapshot.planned`) still read
  `ProjectResource.planned_hours` directly instead of `ProjectPlannedCostVersion`. A full
  cutover was investigated and explicitly rejected for now — see the doc's Phase B item 7
  sub-section — because of a granularity mismatch (envelope-level vs allocated-to-task),
  three call sites that would disagree, and no freshness/recalculation-trigger mechanism.
  Before revisiting: decide whether unallocated envelope hours should still count as
  "planned," and build an assignment-change-triggered recalculation mechanism.
- Baseline provenance (which exact rate-card line/version valued each baseline task) is not
  recorded — would need a baseline financial-snapshot extension.
- **Item 8 (complete 2026-08-09):** replaced the QML combined "Budget" cost-line section with
  separate project-level Profile, Budget Versions, Budget Lines, Rate Cards, and Planned Costs
  views. A canonical application projection owns RBAC, scope, totals, and label resolution with a
  warm-path ceiling of 11 SQL statements. The Views menu reaches configuration when no legacy cost
  row exists; cost rows open Actuals. `FinancialsBudgetSection.qml` was deleted with no temporary
  fallback. Phase B regression: 90 passed; focused projection/isolation/measurement: 5 passed;
  desktop/QML architecture checkpoint: 30 passed.

The next unblocked consolidated phase is Finance Phase C in section 2. Item 7 remains a deliberate
product/architecture decision gate and must not be implemented as a mechanical source swap.

## 2. Finance — Phase C: actual ledger, commitments, time, procurement, periods (not started)

Source: same doc, §19 Phase C. All 8 items are unstarted; only the prerequisite
`TRANSITION(PF-A0-UOW-BRIDGE)` cleanup that items 2/6 depend on is done (governed
commands now own their own Unit of Work). ADR gate: ADR-PF-004/006/007/008 already
ACCEPTED, so the ADR gate itself is not blocking.

1. Organization financial periods + closure/lock policy (separate from scheduling calendars).
2. `ProjectCostEntry` draft/approval/post/reversal lifecycle with Money/base-Money/FX
   snapshot, source, period, dimensions, actor/timestamps, scoped idempotency.
3. PM commitment projections/lines, matching, cancellation/closure, remaining-balance policy.
4. Approved-Time contract/event + idempotent labor-cost consumer (snapshot rate,
   reverse/replace on corrected approvals).
5. Typed Procurement project-source queries/events (PO lines, changes, cancellation,
   receipts, supplier invoice references).
6. Replace manual combined `CostItem` writes with distinct planned/commitment/manual-actual
   commands; posted actuals never editable/deletable.
7. Backfill/split legacy `CostItem` rows, dual-read for reports, reconcile totals, quarantine
   unresolved currency/source cases.
8. Redesign QML Actuals/Commitments as ledgers (status, source, period, matching, approval,
   posting, reversal); remove generic edit/delete on posted rows.

## 3. Finance — Phase D and E (future, not started)

- **Phase D** (forecasts/ETC/change control/reporting): forecast versions+lines, ETC source
  precedence, typed financial change requests, rebuilt read models off canonical Money,
  export metadata (as-of/basis/period/pagination/reconciliation), remove desktop forecast
  fallback formulas, redesign QML Forecast/ETC/Change/Variance tabs.
- **Phase E** (billing/revenue/external accounting): blocked on ADR-PF-010 (currently
  PROPOSED, not accepted) and the product decisions in §24 items 10-15 of the master doc.

## 4. Finance — open transition-code register items

Source: same doc §20 "Transition-code deletion register." `OPEN`/`NOT CREATED` rows only
(everything else is `CLOSED`):

| Component | Removal gate |
| --- | --- |
| `cost.manage` umbrella/alias | Target command permissions active across desktop/services |
| Legacy combined `CostItem` write API | Phase C distinct commands + QML cutover |
| Legacy `CostItem` reader/projection | Phase D ledger/report reconciliation complete |
| `Project.planned_budget` compatibility projection | Budget read cutover + reconciliation complete |
| `Project.currency` compatibility projection | Profile currency cutover, all consumers migrated |
| Profile/Project currency dual-write (`PF-B1-CURRENCY-DUAL-WRITE`) | Desktop/presenters/reports/imports read profile currency exclusively; parity test passes |
| Float monetary/rate/quantity persistence | Numeric backfill + read cutover + reconciliation complete |
| Planned dual-read comparison (Phase C) | Phase D canonical report reconciliation complete — not created yet |
| Planned dual-write adapter (Phase C, only if required) | not created yet |
| Client-side fixed-limit Procurement lookup | Phase C typed project-source contract |
| Legacy financial permission aliases/feature flags | Phase E final role/API/controller inventory — not created yet |
| `Money.from_legacy_float` / `decimal_from_legacy_float` (`PF-A1-LEGACY-FLOAT`) | Phase D legacy reconciliation + float retirement complete |
| PM desktop formatter legacy-float branch (`PF-A1-DESKTOP-FLOAT`) | Phase D canonical decimal-string read DTO cutover |

## 5. Finance — open product decisions blocking later phases

Source: same doc §24. Unresolved (items already resolved by an accepted ADR are omitted):

- Which budget dimensions are mandatory in the first release beyond cost code/WBS (department,
  period, funding source)?
- Are projects single-currency, multi-currency-with-one-reporting-currency, or unrestricted
  multi-currency?
- Monetary precision, rounding mode, and line-vs-total rounding rules?
- Are manual actual costs allowed, and who may post/reverse them?
- Approval thresholds and separation-of-duties rules by tenant/org/department/project/amount/currency?
- Are expense claims in-product, a future Expenses module, or external-only?
- Which billing methods are in first PM scope — does PM only prepare billing or issue invoices?
- Is revenue recognition required, or are contract/billable/invoiced projections enough?
- Target external accounting/ERP system, identifiers, export format, acknowledgement/reconciliation workflow?
- Period-close authority and late-adjustment policy?
- Retention/export rules for financial audit, approval, source documents, reversals?
- ADR-PF-010 (billing vs. external-accounting boundary) needs to move from PROPOSED to ACCEPTED
  before any Phase E work.

## 6. PM Enterprise UI/UX — pending items

Source: `../README.md`, "PM UI/UX Inspection & Improvement Plan" section (Phases 1-11) and
the audit's "Known Limitations."

- **Phase 3 — Resource Assignment Visibility (⬜ not started):** wire
  `ResourceAvailabilityService`/`AssignmentValidationResult` into the Assign Resource dialog
  so selecting a resource shows overallocation %, conflicting projects, skill/cert match
  inline before the user clicks Assign.
- **Phase 4 — Lazy Loading Feedback (⬜ not started):** every `LazySectionLoader` section
  needs a `LoadingOverlay` while busy, an `EmptyState` when empty, and an `InlineMessage`
  danger + Retry button on load failure (pattern is written out in the source doc).
- **Phase 10 — Permission and Capability Handling (⬜ not started):** RBAC-gated buttons
  (Submit Baseline, Approve/Reject, Apply Leveling, Import) are always visible regardless of
  role. Add `can*` bool Q_PROPERTYs to each workspace controller, computed from
  `AuthorizationEngine.has_permission()` (table of required properties is in the source doc).
- **Phase 11 — Tests and Verification (⬜ not started):** add/extend tests for Phase 2, 3, 5,
  7, 10 behaviors listed in the source doc (presenter row-mapping tests, `previewAssignment`
  mapping test, `addTimeEntry` not triggering a full refresh, DataTable height regression
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
