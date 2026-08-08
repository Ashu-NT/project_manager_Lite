# Project Management — CQRS Existing-State Audit and Design-Mapping

Status: **audit and prerequisite Phases 0, 0A, 0B, and 0C complete; Phases 1 and 2 complete**
(2026-08-08). CQRS pilot selection, PM finance design, and the desktop-adapter responsibility audit
are complete. This document began as read-only design-mapping and now also records exact
implementation evidence for the prerequisite phases; proposed CQRS Reader work remains separated
into §15-20 and is explicitly not built until its phase is marked complete. Everything stated as
fact below was verified by opening the file and following the call chain to its concrete runtime
implementation. **The three Scheduling
desktop-API service files and six Scheduling desktop-API serializer files that earlier revisions of
this document flagged as unopened (`services/scheduling_facade_service.py`,
`services/dependency_resolution_service.py`, `services/calendar_adapter_service.py`, and six
`serializers/*.py` files) were subsequently opened and verified in the "Desktop Adapter
Responsibility Audit" section — every inline "not fully verified"/"unverified" marker elsewhere in
this document referring to those nine files is now stale and has been corrected in place.** §5's
desktop-API inventory shows full per-method detail for Projects; every other capability's table in
§5 is representative rather than exhaustive — **the complete per-method inventory for all ten
capabilities is in Appendix A**. This document has now been through three correction passes: the
second added an Architectural Health Assessment, formalized the Session-lifetime and
Activity-atomicity findings, consolidated desktop-adapter-boundary and composition weaknesses,
fixed the `CostPolicyEngine`-ownership ambiguity, reconciled the Finance Snapshot call-count
arithmetic to one verified table, and added a Phase 0A safety-correction step; the third closed the
Scheduling verification gap (the "Desktop Adapter Responsibility Audit" section) and, in this
fourth pass, fixed three remaining contradictions: the stale Scheduling-unverified framing described
here, an ambiguous Phase 0A/Phase 1 ordering statement (§15c vs. §18 — now one explicit governance
sequence), and an inaccurate claim about `FinanceService.get_finance_snapshot`'s signature in the
Approved Phase 1 Flow (corrected to match the actual, already-existing signature — see §16 and
"Approved Phase 1 Flow").

---

## 1. Executive summary

**Architectural style today.** Project Management is a single-process, service-oriented desktop
application, not a client/server or microservice system. There is **one SQLAlchemy `Session`**,
created once at process startup (`src/ui_qml/shell/app.py:59`, `SessionLocal()`), threaded by
constructor injection into every one of the ~30 PM repositories and ~25 PM application services for
the entire lifetime of the desktop process. There is no per-request session, no connection pool
boundary per operation, and no Unit-of-Work abstraction in active use (one exists —
`src/infra/persistence/db/unit_of_work.py`'s `session_scope()` — and has **zero callers** anywhere
in the codebase). Every application service that mutates state owns its own transaction: fetch →
mutate domain object → repository call → `session.commit()` inside a `try/except: rollback; raise`.
No repository ever calls `.commit()` itself (confirmed by a repo-wide grep) — that layering rule
is respected everywhere.

**How a desktop request reaches the database.** QML → a per-workspace Python controller/presenter
→ one of ten `ProjectManagement*DesktopApi` facade classes (`api/desktop/<capability>/api.py`) →
one or more application services (`ProjectService`, `TaskService`, `CostService`, `BudgetService`,
etc.) → a repository contract (`contracts/repositories/*.py`, mostly `ABC`, two `Protocol`s) → a
concrete `SqlAlchemy*Repository` → an ORM model → the shared `Session`. Every desktop API method is
a **synchronous, in-process Python call** — there is no HTTP boundary, no serialization protocol,
and no network hop anywhere in this path; "desktop API" is an architectural seam, not a wire
protocol, which matters for how conservatively a CQRS split needs to be introduced.

**Are reads and writes currently separated?** No, not structurally, but the *raw material* for a
clean split already exists in three independent places the codebase itself has already built:

1. `RateResolutionReader`/`LaborRateResolver` (`contracts/repositories/rate_resolution.py`) — a
   `Protocol`, read-only, tenant-scoped, batched, returning purpose-built non-entity dataclasses
   (`RateResolutionBatch`, `ResourceRateContext`). This is a **complete, working CQRS-style reader**
   already in production use, with a dedicated `SqlAlchemyRateResolutionReader` adapter.
2. `ApprovedTimeFinancialSourceProvider`/`ProcurementFinancialSourceProvider`
   (`contracts/financial_sources.py`) — read-only, cursor-paginated `Protocol`s returning a generic
   `FinancialSourcePage[T]` wrapper for cross-module reads.
3. A consistent `*QueryMixin` naming convention at the **application/service** layer (`ProjectQueryMixin`,
   `TaskQueryMixin`, `CostQueryMixin`, `PortfolioIntakeQueryMixin`, …) that already separates query
   methods from command methods on every composed service — reads and writes are lexically
   separated today, just not behind a different repository/session/permission seam.

Everywhere else, reads and writes share the same repository contract, the same session, and — for
the financial reporting area specifically — a genuinely **inconsistent permission model** (see
§11, §14 P0 finding).

**Where domain entities and ORM objects cross boundaries.** Domain entities (not ORM objects) are
returned from application services up through desktop API methods in most write paths (e.g.
`TaskService.create_task` returns a `Task` domain dataclass all the way to
`ProjectManagementTasksDesktopApi.create_task`, which then serializes it). No repository or
service anywhere in the audited surface returns a raw ORM object across a layer boundary — DTO
conversion happens exactly once, at the desktop API layer, via hand-written `serialize_*`/`build_*`
functions (never `model_dump()`/`from_orm()`). **Returning domain entities is the repository's
consistent current convention and is substantially safer than leaking ORM models. However, it
couples the desktop adapter and serializers to aggregate shape. It is acceptable to preserve during
the read-side pilot, but it is not necessarily the final enterprise boundary.** Selective immutable
`CommandResult` types may later replace aggregate returns where a caller requires only identity,
version, status, or other mutation-confirmation data (§15a) — this is a candidate for improvement,
not a universal violation to fix everywhere. The real, confirmed boundary violation is a different
one, in the opposite direction from the classic "domain entity leaked to the UI" concern:
**desktop-API-layer builder/service files reaching into other services' *private* attributes**
(`_resource_repo`, `_project_resource_repo`, `_tenant_context_service`) as a fallback when an
expected collaborator isn't wired — found repeatedly in
`api/desktop/projects/builders/resource_builder.py`,
`api/desktop/tasks/services/access_resolution_service.py`, and
`api/desktop/resources/services/availability_resolution_service.py` (consolidated with every other
adapter-boundary finding in the new "Desktop Adapter Boundary Weaknesses" section after §14). This
matters for CQRS because a reader built on top of this pattern would inherit an undocumented
dependency on another service's internals.

**Major CQRS opportunities (evidence-backed, ranked).**

1. `FinanceService.get_finance_snapshot` — one call performs `cost_repo.list_by_project` **5
   times**, `project_resource_repo.list_by_project` **3 times**, a full
   `LaborCostEngine.calculate_project_labor_details` sub-graph **3 times**, and
   `rate_resolver.resolve_many` **6 times**, none of it cached within the call. (These are the
   single, reconciled figures used consistently throughout this document — see §7's canonical call
   table; earlier drafts of this section, §7's own prose, and the Terminal Summary previously
   disagreed with each other on some of these numbers, which is corrected here.) This is the single
   biggest, most concretely evidenced performance opportunity in the whole module (§7, §14).
2. `EarnedValueSeriesCalculator.build_series` — for an N-month project, calls
   `EarnedValueCalculator.calculate()` once per month, each of which independently triggers the
   full `CostPolicyEngine.build_snapshot()` chain above. This is the worst confirmed N+1 in the
   module.
3. Every "totals"/"rollup" method across the entire application layer (`get_project_cost_summary`,
   `ForecastCostService.compute_forecast`, `BudgetService.get_totals_by_cost_code`,
   `PlannedCostService.get_totals_by_cost_code`, `RegisterService.get_project_summary`,
   `PortfolioService.list_portfolio_heatmap`) computes its sum/count/group-by **in Python over a
   fully materialized `list_by_project`-style fetch** — a repo-wide grep confirms **zero** uses of
   SQL `func.sum`/`func.count`/`group_by` anywhere in `infrastructure/persistence/repositories/`.
4. `PortfolioService.list_portfolio_heatmap`/`evaluate_scenario`/`compare_scenarios` and
   `CollaborationService.list_inbox`/`list_workspace_snapshot` share the same expensive pattern:
   fetch *every* project/task the user can see, then loop a per-item downstream call — an
   "N+1 across the whole accessible portfolio" shape distinct from the finance N+1s above.
5. The one clean existing reader (`RateResolutionReader`) proves the pattern already fits this
   codebase's conventions — a CQRS pilot does not need to invent new vocabulary, only extend a
   precedent that already exists and is already tested.

**Major risks of introducing CQRS incorrectly.** (i) **Phase 1 reuses the current shared `Session`
as a pragmatic compatibility and scope decision, not because a second `Session` is inherently
stale or invalid.** A separate `Session` opened *after* a committed write can give a perfectly
clean view with no identity-map residue — the reason to reuse today's session for the pilot
specifically is to preserve the exact transaction and read-after-write behavior every existing write
path already relies on, without expanding this pilot's scope into a session-lifecycle redesign. A
separate, operation-scoped `Session` and Unit of Work remain a legitimate later architectural
direction (see the new Session-lifecycle finding after §14, and §20 open question 5) — not
something this document rules out. (ii) Two capability areas — **Portfolio and Collaboration** —
currently commit with **no `try/except`/rollback at all**; a CQRS refactor must not accidentally
inherit or paper over this gap by wrapping it in a "query service" that hides the missing error
handling. (iii) `ForecastCostService.compute_forecast` computes BAC/AC directly from raw `CostItem`
totals, bypassing `CostPolicyEngine`'s manual/computed-labor de-duplication policy — a real,
already-existing **cross-service numeric disagreement** that a naive read-model consolidation could
either silently perpetuate or silently "fix" in a way that changes numbers users have already seen.
(iv) The permission-model split (`report.view` vs. `finance.read`/`finance.read_sensitive`) is a
security-relevant P0; a read-model migration is the right moment to close it, but doing so without
deliberate scope (see §11) would either regress access for legitimate `report.view`-only users or
widen a redaction bypass. **This document does not recommend a mass rewrite, event sourcing, a
separate read database, or command/query handler classes where the existing service style already
works — see §15 for the repository-specific reasoning.**

---

## Architectural Health Assessment

A well-layered service-oriented modular monolith with strong domain/persistence separation and
centralized composition, but with growing read-side scalability, session-lifecycle,
transaction-consistency, adapter-boundary and service-complexity weaknesses.

| Area | Assessment | Verified strength or weakness | Direction |
|---|---|---|---|
| Domain/persistence separation | Strong | ORM models do not leave persistence | Preserve |
| Central composition | Good | Concrete dependencies are composed centrally | Preserve, remove reflective/private-state wiring |
| Write transaction handling | Mixed | Most services commit/rollback correctly; several paths do not | Standardize |
| Read scalability | Weak | Full-list materialization, Python aggregates and N+1 service traversal | Introduce selective Readers |
| Desktop API boundary | Mixed | DTO seam exists, but business logic and private dependencies leak into it | Thin the adapter |
| Tenant/security foundation | Good with P0 gaps | Tenant context, permissions and RLS exist, but several gaps are confirmed | Correct independently |
| Session lifecycle | Structural risk | One Session lives for the whole desktop process | Investigate operation-scoped UoW later |
| Service composition complexity | Mixed | Large mixin MROs and hidden collaborators make flows harder to reason about | Refactor incrementally |
| CQRS readiness | High | `RateResolutionReader` and query mixins already establish precedents | Extend selectively |

Explicitly, based on the evidence in this document:

- **No mass rewrite is justified.** The domain/persistence/composition layering is already sound;
  the weaknesses are localized (specific read paths, specific missing rollback handling, specific
  adapter-boundary leaks), not systemic architectural failure.
- **No microservice split is justified by this audit.** Nothing found here — not the session model,
  not the N+1s, not the permission gaps — requires or is even helped by decomposing the process
  boundary; every weakness is addressable inside the current single-process design.
- **No event sourcing is proposed.** The existing domain-event signals are UI-refresh triggers, not
  a candidate event store, and nothing in the write-path evidence calls for one.
- **No separate read database is proposed for Phase 1.** The one shared Session/database already
  supports the SQL-projection pattern the pilot needs; a second database would add operational cost
  without addressing any finding in this document.
- **CQRS is introduced only for measured, projection-heavy reads** — specifically the Finance
  Snapshot path, where the redundant-call evidence is exact and reproducible (§7), not as a general
  pattern applied speculatively across capabilities that show no comparable evidence (§15c already
  states this per-capability; this assessment states it as the module-wide governing rule).

---

## 2. Audit scope and repository areas inspected

**Project Management-owned files** (primary scope, `src/core/modules/project_management/`):
- `api/desktop/**` — all 10 capability desktop APIs, their DTOs, commands, serializers, builders,
  services, utils, formatters, factories.
- `api/desktop_runtime/desktop_api_builder.py` — the PM-specific desktop-API construction fan-out.
- `application/**` — every service, mixin, command, query file across projects, tasks, resources,
  scheduling (incl. baselines/leveling/CPM), portfolio, risk/register, timesheets (PM wrapper),
  collaboration, financials (costs, finance, budgets, planned costs, rate cards, forecasts,
  cashflow, earned value, configuration), and `common/` (clock, pagination, module guard, async
  threshold, currency policy).
- `contracts/**` — every repository `ABC`/`Protocol`, plus `contracts/financial_sources.py`.
- `domain/**` — every entity/value-object/enum module.
- `infrastructure/persistence/**` — `orm/`, `mappers/`, `repositories/` (every file).
- `infrastructure/reporting/**` — `ReportingService` and its six mixins, report builders.
- `infrastructure/importers/financials/**` — the CSV cost importer's consumption pattern.
- `access/scope_permissions.py` — PM's project-scope permission resolver.

**Platform dependencies inspected** (`src/core/platform/`):
- `application/tenant/tenancy/tenant_context.py` — `TenantContextService`.
- `application/security/authorization/enforcement/permission_checks.py` — `require_permission`/
  `require_project_permission`, and the authorization-denial recording path.
- `domain/security/authorization/roles/role_permission_catalog.py` — the permission catalog.
- `application/approval/approval_service.py` — `ApprovalService.request_change`/
  `approve_and_apply`/`reject`.
- `application/history/audit/enterprise_audit_service.py` — `EnterpriseAuditService`.
- `application/history/activity/activity_service.py` — `ActivityService`.
- `src/core/shared/events/domain_events.py`, `src/core/shared/events/signal.py` — the signal bus.
- `src/core/shared/audit/audit_recorder.py`, `src/core/shared/activity/activity_recorder.py` —
  the shared `record_audit_entry`/`record_activity` helpers PM services call.

**Infrastructure/composition dependencies inspected** (`src/infra/`):
- `composition/app_container.py`, `composition/project_registry.py`, `composition/repositories.py`,
  `composition/platform_registry.py`.
- `persistence/db/session_factory.py`, `persistence/db/optimistic.py`,
  `persistence/db/unit_of_work.py`, `persistence/db/postgresql_rls.py`.
- `application/runtime/desktop_api_registry.py` — the top-level registry every desktop API class is
  exposed through.

**UI consumers inspected (grep-level, not redesigned)**:
- `src/ui_qml/shell/app.py` — process bootstrap.
- `src/ui_qml/modules/project_management/context.py` — `ProjectManagementWorkspaceCatalog`, the
  lazy per-workspace controller factory.
- `src/ui_qml/modules/project_management/{controllers,presenters}/**` — grepped for every desktop
  API method name found in §5 to attribute real QML call sites; **not opened for redesign**, and no
  QML file was modified.

**Tests inspected**: `src/tests/project_management/**` (96 files, 451 tests), `src/tests/pm/**` (9
files, 140 tests), `src/tests/architecture/**` (every PM-relevant guardrail test), 5 incidental
`src/tests/platform/**` files that reference PM types.

---

## 3. Complete relevant repository structure

### 3a. `application/project_management` — full tree with annotations

```text
src/core/modules/project_management/
├── access/
│   └── scope_permissions.py              # resolve_project_scope_permissions — project-scope RBAC resolver
├── api/
│   ├── desktop_runtime/
│   │   └── desktop_api_builder.py        # build_project_management_desktop_runtime_apis — fans out to 10 factories
│   └── desktop/
│       ├── common/
│       │   └── financial_formatting.py   # format_money/format_decimal_amount — shared TRANSITION(PF-A1-DESKTOP-FLOAT) boundary
│       ├── projects/
│       │   ├── api.py                    # ProjectManagementProjectsDesktopApi
│       │   ├── commands/{project_commands.py, resource_commands.py}
│       │   ├── models/{project.py, resources.py}
│       │   ├── serializers/{project_serializer.py, resource_serializer.py}
│       │   ├── builders/{resource_builder.py, status_builder.py}
│       │   └── services/access_service.py
│       ├── tasks/
│       │   ├── api.py                    # ProjectManagementTasksDesktopApi — largest desktop API, ~30 public methods
│       │   ├── commands/{task_commands.py, assignment_commands.py, dependency_commands.py, bulk_commands.py, reservation_commands.py}
│       │   ├── models/{task.py, assignment.py, dependency.py, options.py, skill.py, validation.py, reservation.py}
│       │   ├── serializers/{task_serializer.py, dependency_serializer.py, assignment_serializer.py, skill_serializer.py, reservation_serializer.py}
│       │   ├── builders/{material_demand_builder.py, assignment_validation_builder.py, assignment_preview_builder.py}
│       │   ├── services/{access_resolution_service.py, resource_lookup_service.py}   # RED FLAG: private-attribute repo bypass
│       │   └── utils/{dependency_utils.py, task_id_utils.py, task_status_utils.py}
│       ├── resources/
│       │   ├── api.py                    # ProjectManagementResourcesDesktopApi
│       │   ├── commands/{resource_commands.py, skill_commands.py, certification_commands.py}
│       │   ├── models/{resources.py, skills.py, certifications.py, assignments.py, availability.py, options.py}
│       │   ├── serializers/{resource_serializer.py, skill_serializer.py, certification_serializer.py, assignment_serializer.py, availability_serializer.py}
│       │   ├── builders/{assignment_builder.py, availability_builder.py, employee_option_builder.py, option_builder.py}
│       │   └── services/availability_resolution_service.py   # RED FLAG: constructs a new ResourceAvailabilityService from private attrs
│       ├── scheduling/
│       │   ├── api.py                    # ProjectManagementSchedulingDesktopApi
│       │   ├── commands/{calendar_commands.py, working_day_commands.py, dependency_commands.py, baseline_commands.py}
│       │   ├── models/{schedule.py, calendars.py, dependencies.py, baselines.py, constraints.py, change_impact.py, resources.py}
│       │   ├── serializers/ (6 files — verified in "Desktop Adapter Responsibility Audit"; presentation-shaped, one real finding: baseline_formatter.py's can_submit/can_approve/can_reject via string comparison)
│       │   ├── builders/{project_options_builder.py, activity_options_builder.py, calendar_snapshot_builder.py, baseline_builder.py, constraint_builder.py, change_impact_builder.py, resource_load_builder.py}
│       │   ├── services/{scheduling_facade_service.py, dependency_resolution_service.py, calendar_adapter_service.py}   # verified in "Desktop Adapter Responsibility Audit" — calendar_adapter_service.py has 2 real misplaced-policy findings; the other two are legitimately adapter-shaped
│       │   ├── utils/{dependency_utils.py, scheduling_utils.py}
│       │   └── formatters/{baseline_formatter.py, dependency_formatter.py, status_formatter.py}
│       ├── financials/
│       │   ├── api.py                    # ProjectManagementFinancialsDesktopApi
│       │   ├── models/{options.py, cost_items.py, snapshots.py, forecasts.py, commitments.py, baseline_variance.py, procurement.py}
│       │   ├── commands/{create_cost_item.py, update_cost_item.py}
│       │   ├── serializers/{cost_item_serializer.py, snapshot_serializer.py, analytics_serializer.py, baseline_variance_serializer.py, procurement_serializer.py}
│       │   └── builders/{option_builder.py, forecast_builder.py, commitment_builder.py, baseline_variance_builder.py}
│       ├── portfolio/
│       │   ├── api.py                    # ProjectManagementPortfolioDesktopApi
│       │   ├── commands/{create_template.py, create_intake.py, create_scenario.py, create_dependency.py}
│       │   ├── models/{options.py, templates.py, intake.py, scenarios.py, heatmap.py, dependencies.py, capacity.py}
│       │   ├── serializers/{dependency_serializer.py, recent_action_serializer.py, template_serializer.py, heatmap_serializer.py, intake_serializer.py, scenario_serializer.py}
│       │   └── builders/{option_builder.py, capacity_pool_builder.py}
│       ├── register/
│       │   ├── api.py                    # ProjectManagementRegisterDesktopApi — same instance registered as BOTH "register" and "risk" keys
│       │   ├── commands/entry_commands.py
│       │   ├── models/{entries.py, options.py}
│       │   ├── serializers/entry_serializer.py
│       │   ├── builders/{entry_list_builder.py, option_builder.py}
│       │   ├── utils/register_status_utils.py         # is_overdue()/severity_rank() — duplicated in builders/entry_list_builder.py
│       │   └── formatters/enum_formatter.py
│       ├── timesheets/
│       │   ├── api.py                    # ProjectManagementTimesheetsDesktopApi
│       │   ├── commands/entry_commands.py
│       │   ├── models/{entries.py, options.py, periods.py, review.py, snapshots.py}
│       │   ├── serializers/{entry_serializer.py, period_serializer.py, review_serializer.py}
│       │   ├── builders/{project_options_builder.py, assignment_options_builder.py, assignment_snapshot_builder.py}
│       │   ├── services/project_lookup_service.py
│       │   └── formatters/*, utils/{period_utils.py, status_utils.py}
│       ├── dashboard/
│       │   ├── api.py                    # ProjectManagementDashboardDesktopApi — thin facade, all logic in services/dashboard_snapshot_service.py
│       │   ├── services/dashboard_snapshot_service.py   # DashboardSnapshotService — fans out to 6 other application services
│       │   ├── models/{overview.py, snapshot.py, health_cards.py, tables.py, activity_feed.py, panels.py, charts.py, sections.py}
│       │   ├── builders/{selector_builder.py, overview_builder.py, health_card_builder.py, operational_table_builder.py, activity_feed_builder.py, chart_builder.py, panel_builder.py, section_builder.py}
│       │   └── formatters/{date_formatter.py, number_formatter.py, period_formatter.py}
│       └── collaboration/
│           ├── api.py                    # ProjectManagementCollaborationDesktopApi
│           ├── commands/task_commands.py
│           ├── models/collaboration_models.py
│           ├── serializers/collaboration_serializers.py
│           └── utils/formatting.py
├── application/
│   ├── common/{clock.py, pagination.py, module_guard.py, async_threshold.py, currency_policy.py}
│   ├── projects/
│   │   ├── service.py                    # ProjectService(GuardMixin, ProjectLifecycleMixin, ProjectQueryMixin)
│   │   ├── commands/lifecycle.py
│   │   └── queries/project_query.py
│   ├── tasks/
│   │   ├── service.py                    # TaskService — 16-mixin MRO, largest composed service in the module
│   │   ├── commands/{lifecycle.py, hierarchy.py, hierarchy_support.py, progress.py, deletion.py, dependency.py, schedule_sync.py, assignment.py, assignment_bridge.py, time_entries.py, identity.py, validation.py, assignment_activity.py}
│   │   └── queries/{task_query.py, hierarchy_query.py, dependency_diagnostics.py}
│   ├── resources/
│   │   ├── resource_service.py           # ResourceService(GuardMixin, ResourceCommandMixin, ResourceQueryMixin, SkillCommandMixin, SkillQueryMixin)
│   │   ├── project_resource_service.py   # ProjectResourceService(GuardMixin, ProjectResourceCommandMixin, ProjectResourceQueryMixin)
│   │   ├── assignment_validation.py      # AssignmentSkillValidator
│   │   ├── enterprise_resource_availability.py
│   │   ├── portfolio_resource_pool_service.py   # PortfolioResourcePoolService — NO permission check at all (see §11)
│   │   ├── resource_availability_service.py
│   │   ├── resource_capacity_calculator.py
│   │   ├── commands/{resource_commands.py, project_resource_commands.py, skill_commands.py}
│   │   └── queries/{resource_queries.py, project_resource_queries.py, skill_queries.py}
│   ├── scheduling/
│   │   ├── services/scheduling_engine.py      # SchedulingEngine(ResourceLevelingMixin) — no permission checks, caller-controlled `commit: bool`
│   │   ├── cpm/{cpm_calculator.py, constraint_validator.py}
│   │   ├── dependencies/dependency_resolver.py
│   │   ├── leveling/{leveling_mixin.py, resource_leveling_engine.py, leveling.py}   # two parallel, largely duplicated leveling implementations
│   │   ├── baselines/{baseline_service.py, baseline_comparison_service.py}   # BaselineService is the only fully governed Scheduling class
│   │   ├── calendars/project_calendar_adapter.py
│   │   ├── forecasting/schedule_change_impact_service.py   # docstring-confirmed "never writes to the database"
│   │   ├── models/, utils/
│   │   └── scenarios/                    # empty placeholder
│   ├── portfolio/
│   │   ├── services/portfolio_service.py      # PortfolioService — 10-mixin MRO; EVERY write commits with NO try/except
│   │   ├── commands/{portfolio_intake.py, portfolio_scenarios.py, portfolio_templates.py, portfolio_dependencies.py}
│   │   ├── queries/{portfolio_intake.py, portfolio_scenarios.py, portfolio_templates.py, portfolio_dependencies.py, portfolio_executive.py}
│   │   ├── utils/*
│   │   └── validators/                    # empty placeholder, no validator classes exist
│   ├── risk/
│   │   ├── register_service.py           # RegisterService(GuardMixin, RegisterLifecycleMixin, RegisterQueryMixin) — most uniformly-consistent area
│   │   ├── commands/register_lifecycle.py
│   │   ├── queries/register_query.py
│   │   └── dto/
│   ├── timesheets/
│   │   └── services/service.py           # TimesheetService(GuardMixin, TimeService) — pure marker class, 0 own methods, delegates to platform TimeService
│   ├── collaboration/
│   │   ├── services/collaboration_service.py   # CollaborationService — 9-mixin MRO; writes commit with NO try/except (same gap as Portfolio)
│   │   ├── commands/{collaboration_comments.py, collaboration_presence.py}
│   │   └── queries/{comment queries, document queries, inbox queries, notification queries, presence queries}
│   ├── dashboard/                         # EXCLUDED from this audit's application-layer deep-dive (reporting-adjacent); consumed by api/desktop/dashboard
│   └── financials/
│       ├── __init__.py
│       ├── configuration_service.py       # FinancialConfigurationService — cost codes + financial profile
│       ├── services/{cost_service.py, finance_service.py}   # FinanceService — the highest-risk read area, see §7
│       ├── costs/{cost_policy_engine.py, labor_cost.py, ledger.py, cost_breakdown_engine.py, cost_support.py, policy.py, commands/cost_lifecycle.py, queries/cost_query.py}
│       ├── budgets/budget_service.py       # BudgetService — the only other governed/ungoverned split besides Tasks/Baseline
│       ├── planned_costs/planned_cost_service.py
│       ├── rate_cards/{rate_card_service.py, rate_card_resolver.py, rate_card_precedence.py}   # the shared RateCardResolver instance
│       ├── forecasts/forecast_service.py   # ForecastCostService — bypasses CostPolicyEngine, independent BAC/AC source (real disagreement risk)
│       ├── cashflow/cashflow_builder.py
│       ├── earned_value/{evm_calculator.py, evm_series.py}   # evm_series.py = worst N+1 in the module
│       ├── reporting/analytics.py
│       ├── models/finance_models.py
│       ├── utils/helpers.py
│       ├── invoicing/                     # EMPTY placeholder
│       └── revenue/                       # EMPTY placeholder
├── contracts/
│   ├── financial_sources.py               # ApprovedTimeFinancialSourceProvider, ProcurementFinancialSourceProvider — clean read-only Protocols
│   └── repositories/
│       ├── baseline.py, budget.py, collaboration.py, cost.py, financial_configuration.py,
│       │   planned_cost.py, portfolio.py, project.py, rate_cards.py, register.py, resource.py,
│       │   skills.py, task.py
│       └── rate_resolution.py             # RateResolutionReader, LaborRateResolver — the one existing CQRS-clean seam
├── domain/
│   ├── enums.py, identifiers.py, portfolio.py
│   ├── calendar/assignment.py
│   ├── collaboration/{comments/comment.py, mentions/mention.py, presence/presence.py, notifications/notification.py, models/workspace.py}
│   ├── financials/{budget.py, configuration.py, cost.py, planned_cost.py, rate_cards.py}
│   ├── projects/project.py
│   ├── resources/{resource.py, skills.py}
│   ├── risk/register.py
│   ├── scheduling/baseline.py
│   └── tasks/{hierarchy.py, task.py}      # hierarchy.py — a domain-layer read-model module with ZERO entity classes, only computed views (TaskHierarchyNode/Rollup)
├── infrastructure/
│   ├── persistence/
│   │   ├── health/integrity_checks.py     # out of CQRS scope — data-integrity sweep
│   │   ├── mappers/                       # 13 files, straight 1:1 field mapping, no cross-table logic anywhere
│   │   ├── orm/                           # 13 files, ZERO `relationship()` declared anywhere in the module
│   │   └── repositories/                  # 19 files incl. rate_resolution_reader.py, _tenant_scope.py
│   ├── reporting/
│   │   ├── services/reporting_service.py  # ReportingService — 6 mixins, single `report.view` gate (see §11 P0)
│   │   └── builders/{cost_policy.py, cost_breakdown.py, evm_core.py, evm_series.py, labor.py, baseline_compare.py, variance.py, kpi.py}
│   └── importers/financials/csv/cost_csv_importer.py
└── tests/ → see src/tests/project_management/ (not co-located; listed in §13)
```

### 3b. External composition/platform files directly participating in PM runtime flows

```text
src/
├── ui_qml/
│   └── shell/app.py                       # build_services() — process bootstrap; ONE SessionLocal() call for the whole app run
├── ui_qml/modules/project_management/
│   └── context.py                         # ProjectManagementWorkspaceCatalog — lazy per-workspace QML controller cache
├── application/runtime/
│   └── desktop_api_registry.py            # DesktopApiRegistry — one frozen dataclass exposing every module's desktop APIs
└── infra/
    ├── composition/
    │   ├── app_container.py               # build_service_graph/build_service_dict — top-level composition entry point
    │   ├── project_registry.py            # build_project_management_service_bundle — PM-specific wiring, ~470 lines of construction
    │   ├── repositories.py                # build_repository_bundle — constructs all ~30 PM repositories
    │   └── platform_registry.py           # build_platform_service_bundle — tenant context, RLS wiring, approval service
    └── persistence/db/
        ├── session_factory.py             # SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        ├── optimistic.py                  # update_with_version_check / delete_with_version_check
        ├── unit_of_work.py                # session_scope() — dead code, zero callers
        └── postgresql_rls.py              # configure_session_rls_context, validate_postgresql_execution_role
```

---

## 4. Runtime composition and dependency graph

### 4a. Bootstrap call chain (verified end-to-end)

```text
src/ui_qml/shell/app.py:44  build_services()
  → app.py:59  session = SessionLocal()                         # ONE session, whole process lifetime
  → app.py:62  services = build_service_dict(session)
      → app_container.py:353  build_service_graph(session)
          → repositories.py:166  build_repository_bundle(session)               # ~30 PM repos + platform repos constructed
          → platform_registry.py:191 build_platform_service_bundle(session, repositories)   # TenantContextService, ApprovalService, RLS wiring
          → project_registry.py:125 build_project_management_service_bundle(session, repositories, platform_services)
          → (also: inventory_procurement, maintenance service bundles)
      → app_container.py:246-350  ServiceGraph.as_dict()          # flattens everything into one dict[str, object]
  → app.py:68  desktop_api_registry = build_desktop_api_registry(services)
      → desktop_api_registry.py:152  (top-level)
          → api/desktop_runtime/desktop_api_builder.py:31  build_project_management_desktop_runtime_apis(...)
              → 10× build_project_management_<capability>_desktop_api(...) factory calls
  → app.py:69  services["desktop_api_registry"] = desktop_api_registry
```

QML side: `ProjectManagementWorkspaceCatalog.__init__` (`context.py:83-122`) receives the one
`desktop_api_registry` object as a QML context property, and lazily builds each workspace
controller on first property access (`_get_projects_workspace`, `_get_financials_workspace`, …,
`context.py:148-256`), caching it for the `QObject`'s lifetime. **Everything — session,
repositories, services, desktop APIs, controllers — is a process-wide singleton constructed once**;
there is no per-request or per-operation re-composition anywhere in this application.

### 4b. Runtime object table (PM slice)

| Runtime object | Contract/type | Concrete implementation | Constructed in | Dependencies | Lifetime |
|---|---|---|---|---|---|
| `session` | `sqlalchemy.orm.Session` | instance from `SessionLocal()` | `app.py:59` | `engine` | Singleton, whole process |
| `project_repo` … `resource_skill_repo` (~30 repos) | PM contracts | `SqlAlchemy*Repository` | `repositories.py:170-229` | `session` | Singleton |
| `work_calendar_engine`/`global_calendar_shim` | `CalendarProtocol` | `GlobalCalendarShim` | built once in `platform_registry.py`, reused | `EnterpriseCalendarResolver` | Singleton, **shared** across TaskService/SchedulingEngine/ReportingService/BaselineService/DashboardService |
| `project_calendar_adapter` | — | `ProjectCalendarAdapter` | `project_registry.py:232-235` | `enterprise_calendar_resolver`, `calendar_assignment_service` | Singleton, **shared** into `scheduling_engine` and re-exposed verbatim in the returned bundle |
| `scheduling_engine` | — | `SchedulingEngine` | `project_registry.py:236-244` | session, task/dependency/assignment/resource repos, calendar | Singleton, **shared** into TaskService, ReportingService, BaselineService, DashboardService |
| `assignment_skill_validator` | — | `AssignmentSkillValidator` | `project_registry.py:246-250` | 3 skill/cert repos | Singleton, shared into TaskService + desktop tasks API |
| `system_clock` | `Clock` | `SystemClock` | `project_registry.py:276` | none | Singleton, **explicitly shared** (in-code comment) into `ResourceService`, `RateCardResolver`, `BudgetService`, `PlannedCostService` |
| `task_service` | — | `TaskService` | `project_registry.py:251-272` | session, 7 repos, timesheet_service, work_calendar_engine, scheduling_engine, approval_service, notification_service, employee_repo, assignment_skill_validator | Singleton |
| `resource_service` | — | `ResourceService` | `project_registry.py:277-292` | session, 5 repos, project_rate_card_repo, clock=system_clock | Singleton |
| `cost_service` | — | `CostService` | `project_registry.py:293-304` | session, cost/project/task repos, approval_service, enterprise_audit_service | Singleton |
| `rate_resolution_reader` | — | `SqlAlchemyRateResolutionReader` | `project_registry.py:330` | session | Singleton |
| `rate_card_resolver` | `LaborRateResolver` | `RateCardResolver` | `project_registry.py:331-335` | reader=rate_resolution_reader, tenant_context_service, clock=system_clock | Singleton, **shared** into PlannedCostService, ReportingService, FinanceService, BaselineService |
| `budget_service` | — | `BudgetService` | `project_registry.py:336-349` | session, 5 repos, clock=system_clock, approval_service | Singleton |
| `planned_cost_service` | — | `PlannedCostService` | `project_registry.py:350-365` | session, 7 repos, rate_resolver=rate_card_resolver, clock=system_clock | Singleton |
| `finance_service` | — | `FinanceService` | `project_registry.py:382-393` | 6 repos, rate_resolver=rate_card_resolver, tenant_context_service — **no `session` param at all** | Singleton |
| `forecast_service` | — | `ForecastCostService` | `project_registry.py:315-320` | cost_repo, project_repo only — **no session, no rate_resolver, no tenant_context_service** | Singleton |
| `reporting_service` | — | `ReportingService` | `project_registry.py:366-381` | session, 6 repos, scheduling_engine, rate_resolver=rate_card_resolver | Singleton |
| `baseline_service` | — | `BaselineService` | `project_registry.py:424-440` | session, 5 repos, scheduling=scheduling_engine, rate_resolver=rate_card_resolver, approval_service | Singleton |
| `dashboard_service` | — | `DashboardService` | `project_registry.py:441-451` | reporting_service, task_service, project_service, resource_service, register_service, scheduling_engine — **no session** | Singleton |
| `portfolio_service` | — | `PortfolioService` | `project_registry.py:410-423` | session, 6 repos, reporting_service, tenant_context_service | Singleton |
| `collaboration_service` | — | `CollaborationService` | `project_registry.py:394-409` | session, 7 repos, document_integration_service, notification_service | Singleton |
| 10× `ProjectManagement*DesktopApi` | thin facades | built by `build_project_management_desktop_runtime_apis` | `desktop_api_builder.py:54-127` | wrap the services above + a few platform deps | Singleton, one process-wide `DesktopApiRegistry` |
| QML workspace controllers | `QObject` subclasses | `ProjectManagementWorkspaceCatalog._get_*_workspace()` | `context.py:148-256` | corresponding desktop API + presenter | **Lazy**, cached for the `QObject`'s lifetime (effectively also a singleton per app run) |

### 4c. Optional dependencies, unused constructions, shared instances

- **Every** `X | None = None` constructor parameter on a PM application service is **wired to a
  real instance** in production composition (`project_registry.py`) — none are left `None` on the
  desktop build path. The exceptions are two platform repositories
  (`SqlAlchemyServicePrincipalRepository`, `SqlAlchemyApiKeyCredentialRepository`) constructed with
  `tenant_context_service=None` because `TenantContextService` doesn't exist yet at that point in
  the bootstrap sequence, then **backfilled post-hoc by reflective attribute mutation**
  (`platform_registry.py:224-228`, looping every repo exposing `_tenant_context_service`) — a
  genuine "constructed as None, patched later by reaching into private state" pattern, not
  constructor injection.
- **Shared singletons deliberately reused across services** (confirmed by in-code comments, not
  inferred): `SystemClock` (ResourceService, RateCardResolver, BudgetService, PlannedCostService),
  `GlobalCalendarShim` (TaskService, SchedulingEngine, ReportingService, BaselineService,
  DashboardService), `RateCardResolver` (PlannedCostService, ReportingService, FinanceService,
  BaselineService), `SchedulingEngine` (TaskService, ReportingService, BaselineService,
  DashboardService).
- **Services used only in tests**: none found — every constructed service in `project_registry.py`
  is reachable from a real desktop API. (`src/tests/pm/` uses its own hand-built fakes, not the
  composition-built instances — see §13.)
- **No composition-level test** instantiates `project_registry`/`ProjectManagementServiceBundle`/
  `RepositoryBundle` directly and exercises it end-to-end (§13) — composition correctness relies on
  one architecture test that string-matches source text, not an actual instantiation.

### 4d. Approval apply/reject handler registrations

All registered once in `_register_project_management_approval_handlers`
(`project_registry.py:513-661`):

| request_type | Handler role | Internal method invoked |
|---|---|---|
| `baseline.create` | apply | `BaselineService._apply_baseline_creation_decision(..., commit=False)` |
| `dependency.add` | apply | `TaskService._apply_dependency_add_decision(..., commit=False)` |
| `dependency.remove` | apply | `TaskService._apply_dependency_remove_decision(..., commit=False)` |
| `cost.add` / `cost.update` / `cost.delete` | apply | `CostService._apply_cost_*_decision(..., commit=False)` |
| `budget.approve` | apply + reject | `BudgetService._apply_approval_decision` / `_apply_rejection_decision(..., commit=False)` |

Every apply handler is registered with `commit=False` — confirming each one participates in
`ApprovalService`'s own transaction rather than committing independently (verified against
`ApprovalService.approve_and_apply`, §10).

---

## 5. Desktop API inventory

*(This section shows representative rows per capability, matching the original pass. The
complete, exhaustive per-method inventory for all ten capabilities is in **Appendix A** at the end
of this document.)*

10 desktop API classes, ~150 public methods total, all under
`src/core/modules/project_management/api/desktop/<capability>/api.py`. **Register and Risk are the
same object**: `desktop_api_builder.py` constructs one `ProjectManagementRegisterDesktopApi`
instance and assigns it to both the `project_management_register` and `project_management_risk`
keys on `DesktopApiRegistry` (`desktop_api_registry.py:129-130`) — there is no dedicated Risk API.

Classification legend: COMMAND / QUERY / MIXED / REPORT / LOOKUP / INTEGRATION / UNKNOWN.

### Projects — `ProjectManagementProjectsDesktopApi`

| Method | Input → Output | Service called | Classification | QML consumer |
|---|---|---|---|---|
| `list_statuses` | none → `ProjectStatusDescriptor[]` | none (enum) | LOOKUP | `presenters/projects/workspace_builder.py:33` |
| `list_projects` | none → `ProjectDesktopDto[]` | `ProjectService.list_projects` | QUERY | 7 presenter files across Tasks/Projects/Portfolio/Financials/Scheduling/Register/Timesheets |
| `list_projects_by_status` | `status` → `ProjectDesktopDto[]` | `ProjectService.list_projects_by_status` | QUERY | not found in QML |
| `search_projects` | `query` → `ProjectDesktopDto[]` | `ProjectService.search_projects_by_name` | QUERY | not found in QML |
| `create_project` | `ProjectCreateCommand` → `ProjectDesktopDto` | `ProjectService.create_project` (via reflection shim `call_with_supported_kwargs`) | COMMAND | `project_command_handler.py:54` |
| `update_project` | `ProjectUpdateCommand` → `ProjectDesktopDto` | `ProjectService.update_project` | COMMAND | `project_command_handler.py:75` |
| `set_project_status` | `id, status` → `ProjectDesktopDto` | `ProjectService.set_status` + re-read | COMMAND | `project_command_handler.py:88`, `project_bulk_handler.py:75` |
| `delete_project` | `id` → None | `ProjectService.delete_project` | COMMAND | `project_command_handler.py:97` |
| `list_project_resources` | `project_id` → `ProjectResourceDesktopDto[]` | `ProjectResourceService.list_by_project` (+ private-repo fallback — **flag**) | QUERY | `resources_builder.py:22` |
| `list_assignable_resources` | `project_id` → descriptor[] | `list_project_resources` + `ResourceService.list_resources` | QUERY | `resources_builder.py:63` |
| `add_project_resource` / `update_project_resource` / `remove_project_resource` | commands → DTO/None | `ProjectResourceService.add_to_project/update/delete` | COMMAND | `resource_handler.py` |

### Tasks — `ProjectManagementTasksDesktopApi` (largest surface, ~30 methods)

Representative rows (full method-by-method table verified; see research notes for all 30):

| Method | Classification | Notes |
|---|---|---|
| `list_projects`/`list_statuses`/`list_project_resources`/`list_dependency_types` | LOOKUP/QUERY | Repo-bypass fallback pattern in `services/access_resolution_service.py`/`resource_lookup_service.py` (**red flag** — hand-rolled permission-set filtering duplicated at the desktop layer) |
| `get_task` | QUERY | Fetches **all** tasks for the project to find one by id via `next(...)` scan — Python-side inefficiency |
| `list_tasks` / `list_all_tasks` | QUERY | `list_all_tasks` loops every accessible project calling the per-project method — **N+1-shaped** |
| `create_task`/`update_task`/`move_task`/`update_progress` | COMMAND / MIXED | `update_task` is read-then-write with a possible second write (status change) |
| `list_assignments` | QUERY | Per-assignment `get_assignment_action_context` call in a loop — **N+1** |
| `create_assignment`/`update_assignment_allocation`/`set_assignment_hours`/`delete_assignment`/`accept_assignment`/`decline_assignment` | COMMAND | — |
| `list_dependencies`/`create_dependency`/`update_dependency`/`delete_dependency` | QUERY/COMMAND | `list_dependencies` re-fetches **all** project tasks just to build an id→name lookup |
| `list_task_reservations`/`create_task_reservation` | QUERY/COMMAND, INTEGRATION | Cross-module call into inventory via duck-typed `reservation_service`; 500-row cap filtered client-side |
| `get_task_material_demand` | REPORT | Python `sum()` over status buckets |
| `validate_assignment`/`preview_assignment` | QUERY/REPORT | `preview_assignment` computes an overallocation-delta formula and loops a **second** `get_task` per conflicting task — N+1 + likely-duplicated business logic |
| `get_schedule_impact` | REPORT | Hardcodes a "simulate 1-day delay" scenario inside the desktop layer rather than accepting it as a parameter |

### Resources — `ProjectManagementResourcesDesktopApi`

14 methods; `list_resources`, `list_resource_skills/certifications`, `list_resource_assignments`,
`build_resource_availability` are QUERY/REPORT; `create/update/delete_resource`,
`add/remove_resource_skill`, `add/remove_resource_certification` are COMMAND. **Two confirmed
layering violations**: `list_resource_assignments` falls back to reading
`availability_service._assignments` (a private attribute) when no `assignment_repo` is injected;
`build_resource_availability`'s `resolve_availability_service()` **constructs a brand-new
`ResourceAvailabilityService`** inside the API layer, wired from other services' private
`_resource_repo`/`_task_repo`/`_work_calendar_engine` attributes — composition/wiring logic that
belongs in `project_registry.py`, not the desktop layer. `serializers/certification_serializer.py`
computes a `cert_status` business rule (valid/expiring-soon/expired, hardcoded 30-day threshold)
directly in the serializer.

### Scheduling — `ProjectManagementSchedulingDesktopApi`

~24 methods. `calculate_working_days` performs real calendar-day arithmetic **directly in the API
method body**, including a module-level `_date_range` helper defined in `api.py` itself.
`list_project_dependencies` builds task/dependency lookups and loops `list_dependencies_for_task`
**per task** inline in the API method (N+1, bypassing the builder/serializer pattern used
elsewhere in the same file). `create_baseline` deliberately resolves `rate_as_of=date.today()` in
the API layer (documented, intentional). `update_calendar`/`add_holiday`/`delete_holiday` silently
no-op or fabricate an unpersisted placeholder DTO when the platform calendar API isn't wired
("moved to Platform Admin" legacy retained for QML compatibility).
**Coverage gap, closed in a later pass**: `services/scheduling_facade_service.py`,
`services/dependency_resolution_service.py`, and `services/calendar_adapter_service.py` — the three
files most likely to hold real orchestration logic given how many `api.py` call sites depend on
them — were not opened in this original pass, but were subsequently opened and verified in full in
the "Desktop Adapter Responsibility Audit" section. Verdict: `scheduling_facade_service.py` and
`dependency_resolution_service.py` are legitimately adapter-shaped (real CPM/hierarchy work is
correctly delegated further down); `calendar_adapter_service.py` contains two genuine misplaced-policy
findings (a uniform-hours-per-week calendar-editing rule, and a reimplementation of the platform's
own "GLOBAL calendar is canonical" convention) — see that section for the full detail.
`builders/change_impact_builder.py` also contains a second function, `compute_schedule_impact` —
**confirmed live, not dead**, in the later pass: it is called from `tasks/api.py:681`
(`get_schedule_impact`), a different desktop API than the one that calls its sibling
`build_change_impact`. The two independently wrap the same underlying service with **differing**
baseline-approval-check behavior — a confirmed P0 finding, not the dead/duplicate code this original
pass suspected — see the "Desktop Adapter Responsibility Audit" section's master finding table.

### Financials — `ProjectManagementFinancialsDesktopApi`

12 methods. `list_cost_items`, `get_finance_snapshot`, `get_cost_forecast`,
`get_commitment_summary`, `build_baseline_variance` are QUERY/REPORT; `create/update/delete_cost_item`
are COMMAND; `list_project_requisitions`/`get_project_procurement_commitments` are INTEGRATION —
**and confirmed dead**: repo-wide grep found **no QML consumer anywhere** for either method.
`get_project_procurement_commitments` hard-codes status-category sets and does the counting
in-process in the API layer, with no backing service method at all — this "report" exists only in
the desktop facade. **Every money field on every Financials DTO is `float`**, an explicitly
acknowledged transitional gap (`TRANSITION(PF-A1-DESKTOP-FLOAT)` in `financial_formatting.py`).

### Portfolio — `ProjectManagementPortfolioDesktopApi`

18 methods. `evaluate_scenario`/`compare_scenarios`/`list_heatmap`/`list_dependencies` are REPORT;
`create_scoring_template`/`activate_scoring_template`/`create_intake_item`/`create_scenario`/
`create_project_dependency`/`remove_project_dependency`/`update_intake_item_status` are COMMAND.
`create_project_dependency` **re-fetches all dependencies and linear-scans for the one just
created** instead of using the command's own return value — flagged as a real design smell, not
just a style nit. `build_capacity_pool` hard-codes a fixed 90-day window rather than parameterizing
it.

### Timesheets — `ProjectManagementTimesheetsDesktopApi`

15 methods. `list_review_queue`, `get_review_detail`, `build_assignment_snapshot` are QUERY;
`add/update/delete_time_entry`, `submit/approve/reject/lock/unlock_period` are COMMAND/MIXED (each
period-workflow method re-reads and re-serializes after the write, including an **extra**
`list_time_entries_for_resource_period` query just to recompute a total). `serializers/period_serializer.py`
recomputes `total_hours = sum(...)` in Python — should be a service-level aggregate.

### Register/Risk — `ProjectManagementRegisterDesktopApi`

8 methods (confirmed single instance under two registry keys, see above). `list_entries` does a
**Python-side sort** on `(severity_rank, is_overdue, due_date, title)` — triage-ordering logic
implemented at the desktop layer rather than sourced from the domain/application layer, and
`is_overdue()` is independently re-invoked in two different files (`entry_serializer.py` and
`entry_list_builder.py`) for the same entity.

### Dashboard — `ProjectManagementDashboardDesktopApi`

3 methods, but `build_snapshot` fans out to **six other application services**
(Dashboard/Approval/Baseline/Register/Collaboration/Reporting) via `DashboardSnapshotService`, with
`BaselineService` queried **twice independently** (once for a health card, once for a panel) inside
one snapshot build. Multiple business-rule calculations (`overload` threshold, RAG-status
thresholds, a synthetic burndown trendline formula) are duplicated across `overview_builder.py`,
`health_card_builder.py`, `chart_builder.py`, and `panel_builder.py` — the same `>100%` rule alone
is reimplemented three times across three files.

### Collaboration — `ProjectManagementCollaborationDesktopApi`

10 methods. `build_snapshot`/`build_task_snapshot` are QUERY (the latter fans out to 6
`CollaborationService` calls); `post/edit/delete/react_to_task_comment` are MIXED (write + immediate
re-read). **QML wiring note**: 8 of the 10 methods are actually consumed from
`presenters/tasks/collaboration_*.py` (the task-detail panel), not from
`presenters/collaboration/**` — the "Collaboration" desktop API is primarily a Tasks-panel
dependency, not a standalone workspace API in practice. `api.py::_threaded_comments` implements a
nontrivial in-memory comment-threading tree-build directly in the API layer.

---

## 6. Current write-path traces

Format per the requested trace shape; transaction/audit/event/entity-boundary questions answered
inline per trace.

### Create project

```text
ProjectManagementProjectsDesktopApi.create_project(ProjectCreateCommand)
  → call_with_supported_kwargs(ProjectService.create_project, **command fields)   # reflection shim
  → require_permission("project.manage")
  → _resolve_project_organization_id() → tenant_context_service.require_active_organization_id
  → Project.create(...)                                    # domain factory
  → project_repo.add(project)                                → session.flush()
  → financial_profile_repo.add(profile)                      # cross-aggregate write in the SAME transaction
  → record_audit_entry(..., commit=False)                    # financial-profile audit, same tx
  → session.commit()
  → record_activity(...)                                     # SEPARATE, default commit=True — its own transaction, AFTER the main commit
  → domain_events.project_changed.emit(project.id)            # after both commits
  → ProjectDesktopDto via serialize_project()
```
- **Transaction starts**: `ProjectService.create_project`. **Commit owner**: `ProjectService`
  itself. **Rollback owner**: same method's `except Exception: rollback()`.
- **Two repositories share one transaction**: yes (`project_repo`, `financial_profile_repo`) —
  correct.
- **Audit participates in the same transaction**: yes (`commit=False`). **Activity does not** — it
  is a second, non-atomic commit issued after the primary one succeeds; a failure recording
  activity does not roll back the project creation, and a crash between the two commits leaves the
  project created with no activity-feed entry.
- **Event emitted after commit**: yes, correctly.
- **Domain entity returned outside the application service**: yes — `Project` domain dataclass
  returned all the way to the desktop API, then serialized. No ORM object crosses this boundary.
- **Optimistic concurrency enforced**: not applicable (creation).
- **Tenant/org isolation revalidated at repository level**: `SqlAlchemyProjectRepository.add`
  stamps tenant/org from the ambient context but does not re-verify against a caller-supplied
  value (there is none at create time).

### Update project

Same shape as create, but with an **optimistic-concurrency check**
(`project.version != expected_version → ConcurrencyError`) before mutation, an additional
`finance.manage` permission check gated on whether `currency` changed, and a documented
**dual-write** of `Project.currency`/`ProjectFinancialProfile.currency_code`
(`PROJECT-FINANCE-TRANSITION-ONLY(PF-B1-CURRENCY-DUAL-WRITE)`) inside the same transaction. Domain
event is emitted **outside** the `try` block, after the method's `replace()`-derived return value
is already built — a minor but real inconsistency vs. `create_project`'s in-try event-adjacent
placement.

### Delete/archive project

```text
ProjectManagementProjectsDesktopApi.delete_project(project_id)
  → ProjectService.delete_project(project_id)
  → require_permission("project.manage") + require_project_permission
  → task_repo.list_by_project(project_id)
  → for each task (ordered children-first via order_tasks_children_first):
        dependency_repo.delete_for_task(task.id)
        assignment_repo.list_by_task(task.id)
        for each assignment:  time_entry_repo.delete_by_assignment(assignment.id)   # N+1, nested
        assignment_repo.delete_by_task(task.id)
        task_repo.delete(task.id)
  → cost_repo.delete_by_project(project_id)
  → project_repo.delete(project_id)
  → session.commit()                                        # ONE commit for the whole cascade — correct batching
  → record_activity(...)                                     # after commit, separate transaction
  → (no domain_events.project_changed.emit found on this path — inconsistency vs. create/update)
```
There is no soft-delete/archive concept for `Project` in this codebase — `delete_project` is a hard
delete with an application-layer cascade, not a domain lifecycle transition. The **nested N+1**
(per-task → per-assignment `time_entry_repo.delete_by_assignment`) is real but bounded by project
size; the single final `commit()` means the whole cascade is atomic despite the N+1 shape.

### Create/update task

```text
ProjectManagementTasksDesktopApi.create_task(TaskCreateCommand)
  → TaskService.create_task(...)
  → require_permission("task.manage") + require_project_permission
  → _resolve_task_code() → task_repo.list_by_project()        # full-list scan for uniqueness, not a SQL check
  → _prepare_new_task_hierarchy() → task_repo.list_by_project()
  → _resequence_for_new_task() → per-sibling task_repo.update()   # N-writes-in-a-loop, same transaction
  → Task.create(...)
  → task_repo.add(task)
  → session.commit(); IntegrityError → translated to ValidationError (code/WBS conflict)
  → record_activity(...)                                       # AFTER commit, separate transaction (same pattern as Projects)
  → domain_events.tasks_changed.emit(project_id)                 # after activity's own commit
  → TaskDesktopDto
```
`update_task` follows the same shape with `expected_version` optimistic concurrency and a business
rule blocking schedule/status edits on summary (non-leaf) tasks.

### Task completion / lifecycle transition

```text
ProjectManagementTasksDesktopApi.update_progress(TaskProgressCommand)
  → TaskService.update_progress(...)
  → require_permission("task.manage") + require_project_permission
  → task_repo.get(task_id) → optimistic-concurrency check
  → in-memory status/percent-complete state machine (business rule embedded in the application layer, not a domain method)
  → task_repo.update(task)  → session.commit()
  → record_activity(...)  (after commit)
  → domain_events.tasks_changed.emit  (outside the try block, after activity's commit)
```
Status/percent-complete derivation is **not** a domain-entity method (`Task` has no `.complete()`)
— it is procedural logic living in `TaskProgressMixin`.

### Resource / project-resource mutation

```text
ProjectManagementResourcesDesktopApi.update_resource(ResourceUpdateCommand)
  → ResourceService.get_resource(id)                            # pre-read IN THE API LAYER
  → API layer computes hourly_rate_changed / currency_changed / rate_affecting_change itself   # RED FLAG — a domain decision made in api.py, not the service
  → ResourceService.update_resource(..., effective_on=date.today() if rate_affecting_change else None)
  → require_permission("resource.manage")
  → resource_repo.get/update → optimistic concurrency
  → conditional: supersede prior rate-card line, add new legacy_seeded RateCardLine
  → session.commit(); IntegrityError→rollback+translate; Exception→rollback
  → record_activity(...) (before commit is NOT confirmed here — application-layer service methods for Resources commit then activity separately, same pattern as Projects/Tasks)
  → domain_events.resources_changed.emit
```
The **"does this rate change warrant a new effective-dated rate-card line" decision is made in the
desktop API layer** (`api.py`), not inside `ResourceService` — a business decision embedded above
the application-service boundary, worth correcting independently of any CQRS work.

`ProjectResourceCommandMixin.update`/`set_active`/`delete` use **direct field mutation**
(`.hourly_rate = ...`), not `dataclasses.replace()`, inconsistent with `ResourceCommandMixin`'s
immutable style on the sibling `Resource` aggregate in the same file.

### Assignment mutation

```text
ProjectManagementTasksDesktopApi.create_assignment(TaskAssignmentCreateCommand)
  → TaskService.assign_project_resource(...)
  → _require_manage (task.manage + scope) + _require_leaf_task
  → project_resource_repo.get
  → assignment_repo.list_by_task → Python `any(...)` duplicate-assignment check
  → TaskAssignment.create(...)
  → _check_resource_overallocation(...)   # N+1: per-assignment task_repo.get() inside a loop
  → _check_resource_skill_requirements(...)   # optional AssignmentSkillValidator, stateful warning side-channel
  → assignment_repo.add(assignment)
  → session.commit(); Exception → rollback (plain re-raise)
  → record_assignment_action → record_activity   (after commit)
  → domain_events.tasks_changed.emit   (after)
  → best-effort _notify_task_assigned (safe_dispatch, swallows its own failures)
  → TaskAssignmentDesktopDto
```
**A second, inconsistent path exists**: `TaskAssignmentBridgeMixin.assign_resource` (used by
`assign_resource` bridge callers) auto-creates a missing `ProjectResource` envelope with its **own,
separate `commit()`** before delegating to `assign_project_resource` (which commits again) — **two
non-atomic commits for one logical "assign a resource to a task" operation** when no
`ProjectResource` yet exists. This bridge path also silently skips `_check_resource_skill_requirements`
and `_notify_task_assigned` in one of its branches — a real behavioral gap between the two ways of
reaching "assign this resource."

### Financial profile mutation

```text
ProjectManagementFinancialsDesktopApi  (no direct method — reached via FinancialConfigurationService, not currently desktop-exposed as its own capability; confirmed no api.py method calls configure_profile directly in this audit's scope)
FinancialConfigurationService.configure_profile(...)
  → require_permission("finance.manage")
  → profile_repo.get_by_project, cost_code_repo.list_restrictions
  → profile_repo.update
  → conditionally: project_repo.get + project_repo.update    # dual-write PF-B1-CURRENCY-DUAL-WRITE, same transaction — no cross-tx risk today
  → session.commit(); rollback on IntegrityError/Exception
  → record_audit_entry(..., commit=False, same tx)
```

### Budget lifecycle mutation (create → submit → approve)

```text
BudgetService.create_budget(...)
  → require_permission("budget.manage")
  → project_repo.get, financial_profile_repo.get_by_project, budget_repo.has_open_for_project/get_latest_for_project
  → session.begin_nested():  budget_repo.add(budget); flush()      # SAVEPOINT converts a unique-constraint race into a typed error
  → IntegrityError → BusinessRuleError(PROJECT_BUDGET_OPEN_VERSION_EXISTS) / ConcurrencyError(PROJECT_BUDGET_REVISION_CONFLICT)
  → _record_budget_audit(..., commit=False)
  → _commit()                                                    # outer, single commit
  → domain_events.budgets_changed.emit    (after commit)

BudgetService.approve_budget(...)                                 # THE governed/ungoverned split
  → governed?  approval_service.request_change(...) → BudgetApprovalResult(pending_approval, request_id)
                                                               # NO budget mutation happens on this call
  → ungoverned → _apply_approval_decision(commit=True) → BudgetApprovalResult(applied)
      → budget_repo.get_approved_for_project(project_id)          # find the currently-approved version, if any
      → session.begin_nested():
            previous.supersede(...) → budget_repo.update(previous, expected_row_version=captured_before_call)
            budget_repo.flush()
            budget.approve(...) → budget_repo.update(budget, expected_row_version=captured_before_call)
            budget_repo.flush()
      → IntegrityError → BusinessRuleError(PROJECT_BUDGET_APPROVAL_CONFLICT)
      → _record_budget_audit(commit=False)
      → _commit() if commit=True else flush()
      → domain_events.budgets_changed.emit  only if commit=True
```
- **Governed path never mutates the budget on the request call.** It now returns an immutable
  `BudgetApprovalResult` naming the successful `pending_approval` outcome and durable request ID;
  the actual write only happens later via the approval-apply handler calling
  `_apply_approval_decision(commit=False)` inside `ApprovalService`'s own transaction.
- **`expected_row_version` is captured into a local variable before each mutating call**, not
  re-read from the object afterward — a deliberate defense against a future refactor where
  `supersede()`/`approve()` might start touching `row_version` directly.
- **Multiple repositories share one transaction**: yes, both the superseded and the newly-approved
  `ProjectBudget` rows, atomically, via the savepoint.
- **Audit participates in the same transaction**: yes. **Event emitted after commit, and only if
  this call is the one that actually commits** (correctly deferred when `commit=False`).

### Rate-card mutation

```text
ProjectRateCardService.create_line(...)
  → require_permission("finance.manage")
  → rate_card_repo.get(rate_card_id)
  → _reject_overlap() → rate_card_repo.list_lines_in_scope(...)     # APPLICATION-LAYER validation, not a DB constraint
  → rate_card_repo.add_line(line)
  → _commit()                                                        # generic path — no special IntegrityError translation for this specific race
```
**A concurrency gap exists here, distinct from Budget/PlannedCost's savepoint pattern**: two
concurrent `create_line`/`update_line` calls for the same selection key/effective window can both
pass the in-application `_reject_overlap` check before either commits, and the resulting race
surfaces as a **raw, untranslated `IntegrityError`** rather than a typed business error — `_commit()`
here only special-cases a `duplicate_message` parameter that isn't passed for this call. This is a
smaller-scoped version of the same race class Budget/PlannedCost already solved with
`begin_nested()`.

### Planned-cost snapshot creation

```text
PlannedCostService.calculate_snapshot(project_id, calculated_by, as_of=None)
  → require_permission("plannedcost.manage")
  → project_repo.get, financial_profile_repo.get_by_project, cost_code_repo.get (fail-closed on missing/inactive default cost code)
  → task_repo.list_by_project, assignment_repo.list_by_tasks   → filter to eligible (allocated_planned_hours > 0)
  → rate_resolver.resolve_many(...)                              # ONE batched call over all eligible resources — not per-line
  → planned_cost_repo.get_current_for_project(project_id)
  → session.begin_nested():
        previous?.supersede(...) → update + flush
        planned_cost_repo.add(version) → flush
        planned_cost_repo.add_lines(lines) → flush
  → IntegrityError → ConcurrencyError(PLANNED_COST_REVISION_CONFLICT)
  → _record_version_audit(commit=False)
  → _commit()
  → domain_events.planned_costs_changed.emit
```
Not governed — this method's own docstring/design explicitly frames a snapshot as "a computed fact,
not proposed for review," so there is no `_apply_*_decision` split here (only one caller-facing
entry point).

### Any approval-governed mutation — general shape confirmed across all 4 governed areas

`CostLifecycleMixin` (add/update/delete cost item), `BudgetService.approve_budget`,
`TaskDependencyMixin.add_dependency`/`remove_dependency`, and `BaselineService.create_baseline`
share the same permission, governance, and deferred-mutation structure. Cost, dependency, and
baseline request paths still raise `BusinessRuleError(code="APPROVAL_REQUIRED")`; Phase 4 changed
only budget approval to return `BudgetApprovalResult(pending_approval)` after the request commits.
The ungoverned branch (or later approval-apply handler) calls a private
`_apply_*_decision(..., commit: bool)` method that performs the actual write and either commits
(direct caller) or only flushes (approval-apply handler, letting `ApprovalService` own the final
commit). **`TaskDependencyMixin.update_dependency` is the one confirmed exception** —
its own class docstring states it "has no governed path (dead, unwired)," and it commits directly
with no `commit:` parameter, then triggers a schedule resync as a **second, separate** commit —
the least atomic write path found in the whole audit.

---

## 7. Current read-path traces

### Project list / project details

```text
ProjectManagementProjectsDesktopApi.list_projects()
  → ProjectService.list_projects() → require_permission("project.read") → project_repo.list()  (single unbounded SELECT, no DB-side pagination)
  → filter_project_rows(...)   # Python-side per-row permission filtering, not a scoped SQL WHERE
  → api.py: Python sort by name.casefold()
  → serialize_project() per row → ProjectDesktopDto[]
```
1 repository call, no ORM relationship hydration (none exist in this module), sorting/filtering
done in Python over an already-fetched full list — acceptable at today's data volumes, a real
over-fetching risk if the project count grows large, since there is no SQL-level `WHERE`/`ORDER BY`
doing the row-selection work.

### Project dashboard / portfolio dashboard

```text
ProjectManagementDashboardDesktopApi.build_snapshot(project_id=, baseline_id=, period_key=, view_key=)
  → DashboardSnapshotService.build_snapshot(...)
      → selector resolution (4 builder calls)
      → DashboardService.get_dashboard_data(project_id, baseline_id) OR get_portfolio_data()   # 1 primary aggregate fetch
      → ApprovalService.list_pending(project_id=, limit=120)                     # try/except Exception → () on failure
      → build_operational_tables(...) → RegisterService.list_entries(project_id, entry_type=RISK)   # SEPARATE fetch, re-filtered/re-sorted in Python
      → build_health_cards(...) → BaselineService.get_approved_baseline + list_variance_records   # BASELINE FETCH #1
      → build_activity_feed(...) → CollaborationService.list_workspace_snapshot(...)
      → build_panels_from_dashboard_data(...) → BaselineService.list_variance_records AGAIN       # BASELINE FETCH #2 — independent of #1
      → build_charts_from_dashboard_data(...) → ReportingService.get_evm_series(...)
      → build_sections_from_dashboard_data(...)
  → ProjectDashboardSnapshotDescriptor
```
- **Repository/service call count**: at least 6 distinct application services fanned out to for one
  dashboard load; `BaselineService` alone is queried **twice, independently**, for two different
  panels that could share one fetch.
- **Domain entities loaded**: yes, throughout (`RegisterEntry`, `ProjectBaseline`,
  `BaselineVarianceRecord`, etc.) — all converted to DTOs at the very end.
- **Calculations in Python vs SQL**: entirely Python — KPI aggregation
  (`on_track_projects = total - at_risk - on_hold`, utilization averages/peaks) happens in
  `overview_builder.py`; RAG-status thresholds are hardcoded in `health_card_builder.py`; a
  synthetic burndown trendline formula is computed in `chart_builder.py`. **The same "> 100%
  overload" threshold rule is independently reimplemented in three different builder files**
  (`chart_builder.py`, `panel_builder.py`, and the overload calc in `overview_builder.py`).
- **Fallback exists**: yes — if `dashboard_service` is unwired, the whole method returns an
  entirely synthetic "preview" snapshot assembled from every builder's `build_preview_*()`
  counterpart, with an explicit "not connected in this QML preview" message.
- **Likely N+1/over-fetching risk**: the double baseline fetch is a confirmed, avoidable
  redundancy within a single request; everything else is a fixed small number of service calls per
  dashboard load, not a per-row loop.

### Finance snapshot (the highest-risk read path in the whole module)

```text
ProjectManagementFinancialsDesktopApi.get_finance_snapshot(project_id)
  → FinanceService.get_finance_snapshot(project_id)
      → require_permission("finance.read") + soft has_project_permission("finance.read_sensitive") check for redaction (not denial)
      → _resolve_scope → tenant_context_service.require_organization_context + cross-check project.organization_id
      → task_repo.list_by_project                                    (1)
      → engine.get_cost_source_breakdown(...)
          → CostPolicyEngine.build_snapshot()  [FULL BUILD #1]
              → project_repo.get, project_resource_repo.list_by_project, rate_resolver.resolve_many
              → LaborCostEngine.calculate_project_labor_details()  [FULL SUB-CALL #1]
                  → project_repo.get, task_repo.list_by_project, assignment_repo.list_by_tasks, rate_resolver.resolve_many
                  → resource_repo.get(res_id)  PER DISTINCT RESOURCE   ← N+1
              → cost_repo.list_by_project                              (2)
          → cost_repo.list_by_project  AGAIN, for manual-labor raw totals   (3)
      → engine.get_cost_control_totals(...)
          → CostPolicyEngine.build_snapshot()  [FULL BUILD #2 — everything above, from scratch, again]
              → …LaborCostEngine.calculate_project_labor_details()  [FULL SUB-CALL #2]  → resource_repo.get per resource, again
              → cost_repo.list_by_project                              (4)
      → manual_labor_raw_totals(...) → cost_repo.list_by_project        (5)
      → build_cost_item_ledger_rows(...) → cost_repo.list_by_project    (6)
      → build_computed_labor_plan_rows(...) → project_resource_repo.list_by_project AGAIN + rate_resolver.resolve_many AGAIN
            (code comment: "a second resolve_many call, not a shared cache")
      → build_computed_labor_actual_rows(...) → LaborCostEngine.calculate_project_labor_details()  [FULL SUB-CALL #3]
      → _redact_sensitive_labor_rows(...)  (Python, in-memory)
      → build_period_cashflow(...) / build_source_analytics(...) / build_dimension_analytics(...)  (Python, over already-fetched ledger — cheap)
  → FinanceSnapshot (frozen dataclass) → serialize_snapshot() → FinancialSnapshotDto
```
**Canonical call-count table for one `get_finance_snapshot` call** (re-derived from the trace above,
call-site by call-site, superseding every earlier "4×"/"6×"/"≥3×"/"≥5×" mention elsewhere in this
document — those are now updated to match this table). Two columns distinguish calls made directly
in `FinanceService.get_finance_snapshot`'s own body from calls made transitively, inside a
builder/engine it invokes:

| Dependency or operation | Direct calls | Transitive calls | Maximum confirmed total | Conditions |
|---|---:|---:|---:|---|
| `task_repo.list_by_project` | 1 | 3 (once inside each of the 3 `LaborCostEngine.calculate_project_labor_details` executions) | **4** | Unconditional |
| `cost_repo.list_by_project` | 2 (via `manual_labor_raw_totals()`, via `build_cost_item_ledger_rows()`) | 3 (1 inside `build_snapshot` via `get_cost_source_breakdown`, 1 inside `get_cost_source_breakdown`'s own manual-labor step, 1 inside `build_snapshot` via `get_cost_control_totals`) | **5** | Unconditional. Whether `get_cost_source_breakdown`'s own manual-labor step and the standalone `manual_labor_raw_totals()` call in the trace are the same helper invoked twice from two call sites, or two distinct code paths, is not fully disambiguated by the trace alone — flagged for Phase 0 to confirm via the query-count instrumentation itself rather than asserted with false precision |
| `project_repo.get` | 1 (`get_finance_snapshot`'s own direct call, line 133) | 5 (once inside each `build_snapshot` execution ×2, once inside each `LaborCostEngine` execution ×3) | **6** | Unconditional. **Corrected by Phase 0's dynamic measurement (§18)**: an earlier revision of this table said 5 (0 direct + 5 transitive), missing `get_finance_snapshot`'s own direct call at line 133 — running the real code confirmed 6, not 5. Kept here as a worked example of why Phase 0 measures against the real code instead of trusting static counting alone. |
| `project_resource_repo.list_by_project` | 0 | 3 (once inside each `build_snapshot` execution ×2, once inside `build_computed_labor_plan_rows`) | **3** | Unconditional |
| `assignment_repo.list_by_tasks` | 0 | 3 (once inside each `LaborCostEngine.calculate_project_labor_details` execution) | **3** | Unconditional |
| `LaborCostEngine.calculate_project_labor_details` (full sub-graph) | 1 (via `build_computed_labor_actual_rows`) | 2 (once inside each `build_snapshot` execution) | **3** | Unconditional |
| `rate_resolver.resolve_many` | 0 | 6 (2 per `build_snapshot` execution — its own call plus its nested `LaborCostEngine` call — ×2 executions = 4; +1 in `build_computed_labor_plan_rows`; +1 in the standalone 3rd `LaborCostEngine` execution) | **6** | Unconditional |
| `resource_repo.get(res_id)` | 0 | 3×N | **3×N** | N = distinct resources with cost-bearing assignments on the project; grows with project size — the genuine N+1, not a fixed count |
| `CostPolicyEngine.build_snapshot` (full build) | 0 | 2 (via `get_cost_source_breakdown`, via `get_cost_control_totals`) | **2** | Unconditional |

None of this is cached within the call, despite every sub-call sharing the same `project_id`/
`as_of`. **This is the single largest, most concretely evidenced CQRS/performance opportunity found
in this audit** — see §14 P1 and §17. See §18 Phase 0 for the full measurement plan (query count is
only one of several dimensions Phase 0 must capture before Phase 1 begins).

**Duplicated calculation risk beyond redundancy**: `ForecastCostService.compute_forecast` computes
its own BAC/AC **directly from raw `CostItem.planned_amount`/`actual_amount`**, completely
bypassing `CostPolicyEngine`'s manual-vs-computed-labor de-duplication policy — so
`FinanceService.get_finance_snapshot`'s policy-applied totals and
`ForecastCostService.compute_forecast`'s totals **can legitimately disagree** whenever any computed
labor exists, and both are reachable under the same `finance.read` permission, potentially shown
side-by-side in a UI.

### EVM series (worst confirmed N+1)

```text
EarnedValueSeriesCalculator.build_series(project_id, ...)
  → project_repo.get, baseline_repo.list_tasks / get_latest_for_project
  → FOR EACH month-end point in the series:
        EarnedValueCalculator.calculate(project_id, baseline_id=, as_of=pe)
            → baseline_repo.get_baseline/get_latest_for_project, list_tasks, task_repo.list_by_project, project_repo.get
            → self._get_actual_cost(project_id, as_of) → CostPolicyEngine.build_snapshot()   [full chain above, AGAIN, per month]
```
For a 24-month project, this issues on the order of dozens of redundant `list_by_project`/
`resolve_many`/`resource_repo.get` round-trips, all cacheable per `(project_id, as_of)` within one
`build_series` call, none of it cached today.

### Task list / tree / board

```text
ProjectManagementTasksDesktopApi.list_tasks(project_id)
  → self._serialize_project_tasks(project_id)
      → TaskService.list_task_hierarchy(project_id) + list_task_hierarchy_rollups(project_id)   [preferred path]
          → task_repo.list_by_project (ONE query) → Python-side recursive tree build + cycle detection
          → _build_task_hierarchy_rollup PER NODE, each re-scanning the full nodes list  → O(n²) in-memory work for large hierarchies
      OR TaskService.list_tasks_for_project(project_id)  [fallback path] → Python sort by (start_date, -priority, name) IN THE API LAYER
  → serialize_task() per row → TaskDesktopDto[]
```
`list_all_tasks` (no `project_id`) loops every accessible project and calls the above **once per
project** — a confirmed cross-project N+1, with `try/except BusinessRuleError: continue` silently
skipping inaccessible projects rather than surfacing which ones were skipped.

### Resource list / utilization

```text
PortfolioResourcePoolService.get_pool_report(from_date, to_date)
  → resources.list()  → per-id resources.get()  in a loop  ← confirmed N+1, plus Python-side set filtering instead of SQL IN
```
No permission check exists on this cross-project PMO report at all (§11 finding).

### Assignments (cross-task)

`SqlAlchemyAssignmentRepository` exposes both `list_by_task` (per-task) and `list_by_tasks` (batch)
— the batch form is correct and used by e.g. `PlannedCostService.calculate_snapshot`, but its mere
existence alongside the per-task form means any future/existing caller that picks `list_by_task` in
a loop reproduces the exact N+1 the batch method exists to avoid. `TaskAssignmentMixin.
update_assignment_planned_hours` computes an allocation-envelope total via **Python `sum()`** over
`assignment_repo.list_by_resource` results rather than a repository-level aggregate.

### Scheduling/calendar reads

`SchedulingEngine.recalculate_project_schedule` (also used as a read path with `persist=False` for
constraint-violation checks) issues exactly 3 repository calls
(`task_repo.list_by_project`, `dependency_repo.list_by_project`, optional
`assignment_repo.list_by_tasks`) and does the CPM forward/backward pass entirely in Python — this is
appropriate, CPU-bound domain math, not an avoidable SQL-vs-Python smell.

### Budget / rate-card / planned-cost reads

`BudgetService.get_totals_by_cost_code`/`get_totals_by_task` and `PlannedCostService`'s equivalents
both fetch the full line list via `list_lines()` and sum `Decimal` amounts **in Python**, not SQL
`GROUP BY` — consistent with the module-wide "no SQL aggregation anywhere" finding (§9).

### Report/export reads

`infrastructure/reporting/services/reporting_service.py`'s six mixins are **thin delegates** that
construct a fresh `CostPolicyEngine`/`LaborCostEngine`/`CostBreakdownEngine`/`EarnedValueCalculator`
from the service's own repos and call straight into the same application-layer engines
`FinanceService` uses — **the calculation logic is correctly not duplicated** between the reporting
and financials-application layers. The duplication that *does* exist is entirely in the
**permission model** (§11, §14 P0): `ReportingService` gates every method behind `report.view` only,
with **no `finance.read_sensitive`-equivalent redaction check anywhere**, while `FinanceService`
redacts the exact same labor-by-resource detail unless the caller also holds
`finance.read_sensitive`.

---

## 8. Boundary and model mapping

| Model/type | Layer that owns it | Created by | Consumed by | May cross boundary? | Current violations |
|---|---|---|---|---|---|
| Desktop request DTOs (`*Command`, e.g. `ProjectCreateCommand`) | `api/desktop/<cap>/commands/*.py` | QML presenter/controller | Desktop API method | Yes, by design (this is the boundary) | None found — always primitives/plain dataclasses |
| Desktop response DTOs (`*DesktopDto`) | `api/desktop/<cap>/models/*.py` | `serialize_*`/`build_*` functions | QML presenters | Yes, by design | Money fields are `float` end-to-end (acknowledged `TRANSITION(PF-A1-DESKTOP-FLOAT)`); some carry untyped `dict[str, Any]` payload bags (Dashboard table rows/section state) |
| Application "command objects" | **do not exist as a distinct type** — public service methods take keyword arguments directly | — | — | n/a | This is a real gap for §15/§16, not a violation of anything today |
| Application "query objects" | **do not exist as a distinct type** either — `*QueryMixin` methods take primitives | — | — | n/a | Same |
| Application result DTOs | `application/financials/models/finance_models.py` (`FinanceSnapshot`, `CostPolicySnapshot`, `LaborDetailsResult`, `CostControlTotals`, etc.); scattered elsewhere as ad hoc dataclasses (`RegisterProjectSummary`, `PortfolioScenarioEvaluation`) | the owning service | desktop-API serializers | Yes | None found holding a domain entity/ORM object |
| Domain entities (`Task`, `Project`, `ProjectBudget`, …) | `domain/**` | domain `.create()` factories | application services; **returned from services to desktop API** in most write paths | Yes — **crosses the application→desktop boundary today, then gets serialized** | Not itself a violation (never reaches QML/ORM), but it *is* the reason a future `CommandResult` would remove a boundary crossing — see below |
| Value objects (`Money`, `CurrencyCode`, `RateSelectionSnapshot`, `DecimalQuantity`) | `platform/finance/money/*`, `domain/financials/rate_cards.py` | domain/platform code | domain + application | Yes | None found |
| Repository return types | domain entities (majority), plus a few non-entity dataclasses (`ResourceRateContext`, `RateResolutionCandidate`, `int` for `touch_version_with_check`) | repositories | application services | Yes (repo → service only) | None found returning ORM objects to services |
| Read/report models | `RateResolutionBatch` (contracts), `FinanceSnapshot`/`CostPolicySnapshot` (financials models), `PortfolioExecutiveRow`/`TaskHierarchyRollup` (domain-layer read models) | resolvers/engines | services → desktop serializers | Yes | None found — these are the pattern to generalize, not a violation |
| ORM models | `infrastructure/persistence/orm/*.py` | mappers | repositories only | **No** — confirmed: zero ORM objects found crossing into application/domain/desktop layers anywhere in the audited surface | None found |
| SQLAlchemy Row/Mapping results | `SqlAlchemyRateResolutionReader`, `list_effective_lines` (rate cards) | repository query methods | callers within the same repository module, or wrapped into a value object before returning | Only as an intermediate, never returned raw | None found |
| QML-facing models | `ui_qml/**` view-models (out of redesign scope) | presenters | QML | Yes, by design | Not audited in depth (explicitly deferred per task scope) |

**Concrete flows that exist today, exactly as the audit asked to identify:**

- `Domain entity → desktop serializer → desktop DTO` — this is the **dominant** write-path shape
  across Projects, Tasks, Resources, Register, Budget, PlannedCost, RateCards: the application
  service returns a domain dataclass (`Task`, `ProjectBudget`, `RegisterEntry`, …), and the desktop
  API's own `serialize_*` function converts it to a DTO. This is the repository's **consistent
  current convention** and it does not leak a persistence model — no ORM object was found crossing
  this boundary anywhere in the audit. It is not, however, unconditionally "correct" in a stronger
  sense: it couples the application layer and the desktop adapter to the full shape of the
  aggregate, and it remains a legitimate candidate for selective `CommandResult` introduction where
  a narrower contract would add real value (see §15a) — not a pattern to defend as-is everywhere,
  nor one to replace everywhere.
- `ORM/domain graph → Python calculation → desktop DTO` — this is the dominant **read**-path shape
  for every reporting/snapshot/dashboard method: `FinanceService.get_finance_snapshot`,
  `DashboardSnapshotService.build_snapshot`, `PortfolioService.list_portfolio_heatmap`, etc. all
  hydrate full domain-entity lists via `list_by_project`-style repository calls, then aggregate in
  Python before handing a purpose-built dataclass to a serializer. **This is exactly where a
  `ReadModel`+SQL-projection pair belongs** — the boundary crossing to remove is "full aggregate
  list materialized just to compute a handful of numbers," not the DTO conversion itself, which is
  already clean.

---

## 9. Repository and persistence audit

### 9a. Repository classification summary

| Contract | Concrete implementation | Aggregate/table | Read/write/mixed | Commits? | Tenant scoped? |
|---|---|---|---|---|---|
| `ProjectRepository` | `SqlAlchemyProjectRepository` | `projects` | mixed | No | Yes (direct columns — the tenant "root") |
| `ProjectResourceRepository` | `SqlAlchemyProjectResourceRepository` | `project_resources` | mixed | No | Transitive (via Project) |
| `TaskRepository` | `SqlAlchemyTaskRepository` | `tasks` | mixed | No | Transitive |
| `AssignmentRepository` | `SqlAlchemyAssignmentRepository` | `task_assignments` | **mixed, widest surface of any single-aggregate contract** (12 methods incl. 4 differently-shaped list filters) | No | Transitive |
| `DependencyRepository` | `SqlAlchemyDependencyRepository` | `task_dependencies` | mixed | No | Transitive |
| `ResourceRepository` | `SqlAlchemyResourceRepository` | `resources` | mixed | No | Yes (direct columns) |
| `ResourceSkillRepository`/`ResourceCertificationRepository`/`TaskSkillRequirementRepository` | `SqlAlchemy*` | `resource_skills`/`resource_certifications`/`task_skill_requirements` | mixed, no `update` method on any of the three (add/delete/list only) | flush only (add) | Transitive |
| `CostRepository` | `SqlAlchemyCostRepository` | `cost_items` | mixed | No | Transitive |
| `ProjectFinancialProfileRepository` | `SqlAlchemyProjectFinancialProfileRepository` | `project_finance_profiles` | mixed | No | Yes, direct + RLS |
| `ProjectCostCodeRepository` | `SqlAlchemyProjectCostCodeRepository` | `project_finance_cost_codes` (+ restrictions) | **fat**: CRUD + a boolean cross-aggregate existence probe (`is_default_for_any_profile`) reaching into `ProjectFinancialProfileORM` from inside the CostCode repo | No | Yes, direct + RLS |
| `ProjectRateCardRepository` | `SqlAlchemyProjectRateCardRepository` | `project_finance_rate_cards`/`_lines` | **fat**: card+line CRUD plus two resolution/report-shaped queries (`list_effective_lines` returning tuple-pairs, `list_lines_in_scope`) that structurally duplicate what `SqlAlchemyRateResolutionReader` already does properly, elsewhere | flush inside `begin_nested()` (find-or-create only) | Yes, direct + RLS |
| `ProjectBudgetRepository` | `SqlAlchemyProjectBudgetRepository` | `project_finance_budgets`/`_lines` | **fat**: budget+line CRUD (incl. optimistic-concurrency variants) + a boolean existence probe (`has_open_for_project`) + a public `flush()` escape hatch | No (public `flush()` utility only) | Yes, direct + RLS |
| `ProjectPlannedCostVersionRepository` | `SqlAlchemyProjectPlannedCostVersionRepository` | `project_finance_planned_cost_versions`/`_lines` | mild-fat: version CRUD (narrow) + line batch write/read + public `flush()` | No | Yes, direct + RLS |
| `BaselineRepository` | `SqlAlchemyBaselineRepository` | `project_baselines`/`baseline_tasks`/`baseline_variance_records` | fat: mixes 3 sub-entities' write+list on one interface | No | Transitive |
| `RegisterEntryRepository` | `SqlAlchemyRegisterEntryRepository` | `register_entries` | mixed, `list_entries`'s 4-filter shape is borderline report-like | No | Transitive |
| `TaskCommentRepository`/`TaskPresenceRepository` | `SqlAlchemy*` | `task_comments`/`task_presence` | mixed; `touch` is a write that returns the entity | flush only (add) | Transitive |
| 4× Portfolio repositories | `SqlAlchemy*` | `portfolio_*` | clean CRUD, no report methods — **not fat** | No | Yes, direct (2 of 4 lack a `version` column, no OCC possible) |
| **`RateResolutionReader`** | `SqlAlchemyRateResolutionReader` | reads `resources`/`resource_skills`/`project_finance_rate_cards`/`_lines` | **pure read, the one deliberately-separate reader in the module** | No | Yes, explicit params (no ambient tenant-context dependency) |

### 9b. ORM → mapper → table map (representative; full 13-file inventory verified)

| Domain type | Mapper | ORM class | Table | Notable columns/flags |
|---|---|---|---|---|
| `Project` | `mappers/project.py` | `ProjectORM` | `projects` | `version` ✅; `planned_budget` plain `Float`, **no** `financial_numeric` marker (legacy) |
| `TaskAssignment` | `mappers/task.py` | `TaskAssignmentORM` | `task_assignments` | `version` ✅; `allocated_planned_hours` correctly uses `financial_numeric(QUANTITY)` + `info` marker; `hours_logged`/`allocation_percent` plain `Float` |
| `CostItem` | `mappers/cost.py` | `CostItemORM` | `cost_items` | `version` ✅; all 4 money fields plain `Float`, **no** marker (pre-dates the ADR-PF-005 convention) |
| `ProjectRateCard`/`RateCardLine` | `mappers/rate_cards.py` | `ProjectRateCardORM`/`RateCardLineORM` | `project_finance_rate_cards`/`_lines` | `rate_amount`+3 multipliers correctly `financial_numeric(RATE)` + marker — the cleanest example in the module |
| `ProjectBudget`/`BudgetLine` | `mappers/budget.py` | `ProjectBudgetORM`/`BudgetLineORM` | `project_finance_budgets`/`_lines` | `amount` correctly `financial_numeric(MONEY)` + marker; mapper translates ORM's plain `version` column ↔ domain's `row_version` field name |
| `ProjectPlannedCostVersion`/`Line` | `mappers/planned_cost.py` | `*ORM` | `project_finance_planned_cost_versions`/`_lines` | `planned_hours`/`rate_amount`/`amount` all correctly marked; `source_assignment_id` deliberately a plain snapshot column, no live FK |
| `TaskDependency`, `BaselineTask`, `BaselineVarianceRecord`, `TaskPresence`, `ProjectCostCodeRestriction`, calendar-assignment ORMs, 3 of 4 Portfolio ORMs | various | various | various | **no `version` column at all** — deliberate for pure link/snapshot/ephemeral rows, but means no optimistic-concurrency guard is even possible on those tables |

**Structural finding confirmed across all 13 ORM files**: **zero** `relationship()` declarations
anywhere in this module. Every cross-entity read is an explicit `select().join(...)` in a
repository method, or a second query — there is no lazy-loading foot-gun in the SQLAlchemy sense,
but also no eager-loading convenience; every "fetch parent + children" flow is hand-rolled per
repository method, and pagination/sorting/filtering is almost never pushed into the SQL itself (see
§9c).

### 9c. Pagination, sorting, filtering — module-wide default

Confirmed by direct inspection of all 19 repository files: **only three `.limit()` calls exist in
the entire persistence layer** —
`TaskCommentRepository.list_recent_for_tasks` (default 200),
`TaskPresenceRepository.list_recent_for_tasks` (default limit param),
`ProjectBudgetRepository.get_latest_for_project` (`limit(1)`, a single-row optimization, not
pagination). **Every other `list_*`/`list_for_project`/`list_by_*` method returns the entire
matching result set** via `.all()` with no `LIMIT`/`OFFSET` — this is the module-wide default, not
an exception, and it is the mechanical reason every Python-side aggregation finding in §7/§14 is
possible at all: the data is always fully materialized before any filtering/sorting/summing
happens.

**No repository anywhere computes a sum, count, or `GROUP BY` in SQL** — confirmed by grep for
`func.sum`/`func.count`/`group_by` across `infrastructure/persistence/repositories/`: zero matches.

### 9d. N+1 / over-fetching risk register (repository-level, distinct from the application-level ones in §7)

1. `TaskRepository.list_children(project_id, parent_task_id)` — single-parent-at-a-time; any WBS
   tree walk that calls it per node is O(depth×breadth) queries instead of one `list_by_project` +
   Python grouping (the safe pattern already used correctly by
   `hierarchy_support.py:_children_by_parent`, but nothing prevents a *different* caller from using
   the unsafe per-parent method instead).
2. `AssignmentRepository.list_by_task` vs `list_by_tasks` — batch form exists and is used correctly
   by `PlannedCostService`, but the per-task form remains callable in a loop by anything else.
3. Skill/certification repositories expose **only** `list_by_resource`/`list_by_task` — no batch
   form at all — so any view needing skills for N resources must either loop (N+1) or route through
   `SqlAlchemyRateResolutionReader.list_resource_contexts` (which does batch correctly, but only for
   the rate-resolution use case, not general skill display).
4. No project-scoped financial repository (`ProjectFinancialProfileRepository`,
   `ProjectRateCardRepository`, `ProjectBudgetRepository`, `ProjectPlannedCostVersionRepository`)
   exposes a batch-by-project-ids method — a portfolio-wide financial rollup would necessarily loop
   per project, exactly like `PortfolioService.list_portfolio_heatmap` already does for KPIs today.

---

## 10. Transaction, session and Unit of Work audit

**Is one SQLAlchemy session shared across repositories?** Yes — confirmed end-to-end: the same
`session` object flows into all ~30 PM repositories and ~25 PM application services via
constructor injection, traced through `repositories.py` and `project_registry.py`.

**Is the session injected directly into services?** Yes, and into repositories, identically. There
is no session-factory abstraction between the composition root and either layer.

**Is there a Unit of Work abstraction?** One exists (`src/infra/persistence/db/unit_of_work.py`'s
`session_scope()` context manager) and is **entirely unused** — a repo-wide grep found zero
callers, independently corroborated by this repository's own architecture-decision documents
(`docs/architecture_decisions/ADR-005-domain-events.md`), which state the same fact and slate the
file for replacement.

**Are repositories allowed to commit?** No, and none do — confirmed by grep: zero
`.commit()` calls anywhere under `infrastructure/persistence/repositories/`. A few call
`.flush()` (skills repos' `add`, rate-card's `get_or_create_legacy_card`, budget's public `flush()`
utility) — always flush, never commit.

**Which services call commit? Which only flush?** Every write-capable application service commits
its own transaction (`ProjectService`, `TaskService`, `ResourceService`/`ProjectResourceService`,
`RegisterService`, `CostService`, `BudgetService`, `PlannedCostService`, `ProjectRateCardService`,
`FinancialConfigurationService`, `SchedulingEngine`, `ResourceLevelingEngine`, `BaselineService`,
`PortfolioService`, `CollaborationService`). The **only** methods that only flush (never commit
themselves) are the internal halves of the governed/ungoverned split
(`_apply_*_decision(..., commit: bool)` in `CostLifecycleMixin`, `BudgetService`,
`TaskDependencyMixin`, `BaselineService`) when called with `commit=False` by an approval-apply
handler, and `_sync_project_schedule`/`SchedulingEngine.recalculate_project_schedule` when a caller
passes `commit=False` to fold a CPM resync into its own transaction.

**Can nested services commit independently?** Generally no for the governed paths (deliberately
prevented by the `commit: bool` threading), but **yes, and this is a real gap, for
`TaskAssignmentBridgeMixin.assign_resource`**, which commits once to auto-create a missing
`ProjectResource` envelope, then delegates to `assign_project_resource`, which commits again — two
independent, non-atomic commits for one logical operation (§6 finding, repeated here because it's
also a transaction-boundary finding).

**How do approval callbacks participate in transactions?** Verified against
`ApprovalService.approve_and_apply`/`reject`
(`src/core/platform/application/approval/approval_service.py:207,167`): the registered apply/reject
handler is invoked **first**, its result folded into the same in-flight transaction (handlers are
registered with `commit=False`), then the approval request's own status is updated
(`approval_repo.update`), then audit is recorded (`commit=False`), then **one single
`session.commit()`** covers both the handler's mutation and the approval decision's own state
change. Post-commit domain-event signals fire only after that shared commit succeeds. This
confirms the prior Unit-of-Work fix referenced in project history is in place and correctly wired —
there is no remaining "approval decided before the mutation committed" gap in the current
composition.

**How are audit and activity persisted?** `EnterpriseAuditService`/`record_audit_entry` and
`ActivityService`/`record_activity` both take the **same shared session** as every other service.
`record_audit_entry` is called with `commit=False` **consistently across every write path
audited** — audit always lands in the same transaction as the mutation it describes.
`record_activity`, however, is called with its **default `commit=True`** in Projects, Tasks,
Resources — i.e., **activity logging is a second, non-atomic commit issued after the primary write
already succeeded**, in every one of those three capability areas. The two areas with the
governed/ungoverned split (Budget, TaskDependency, Baseline, Cost) correctly pass `commit=False` for
activity too, folding it into the same transaction as the domain write.

**Are event handlers transactional?** No — domain events (`domain_events.*.emit`) are pure
in-process Python signal dispatch (`src/core/shared/events/signal.py`'s `Signal[T]`, not Qt, not
durable). They are **always emitted after a successful commit** everywhere this audit traced,
**except** the deliberately-deferred governed-write cases, where the event is skipped entirely when
`commit=False` and becomes the deferring caller's responsibility to emit later. No outbox/inbox or
other durable delivery mechanism exists anywhere in this codebase (confirmed by repo-wide grep and
by `docs/architecture_decisions/ADR-PF-011-durable-integration-outbox-inbox.md`, which explicitly
proposes one and states it is not yet built).

**What happens when event/audit recording fails?** Audit: `record_audit_entry` defaults
`fail_closed=True` in the financial paths that use it, meaning a recording failure raises and rolls
back the whole transaction (same tx as the mutation) — a genuinely safe design.
Activity: `record_activity` has **no fail-closed option** and, because it's a separate,
already-committed transaction in Projects/Tasks/Resources, a failure there **cannot** roll back the
primary write that already succeeded — the mutation stands even if its activity-feed entry never
gets written.

**Does a read service use the same session as command services?** Yes, necessarily — there is only
one session for the whole process. `FinanceService`/`ForecastCostService`/`DashboardService` are
constructed **without** a `session` parameter at all (by design — they're pure aggregation
services composed from repos/services that already hold it), but every repo they call through still
uses the one shared session underneath.

**Are sessions long-lived in the desktop application?** Yes — one session for the entire process
run, confirmed at `app.py:59`.

**Can stale identity-map objects affect reads?** Partially mitigated: `session_factory.py` does not
override SQLAlchemy's default `expire_on_commit=True`, so objects are expired (and lazily refreshed
on next attribute access) after every commit. However, `autoflush=False` means a read issued
between two writes in the same request will **not** automatically see an uncommitted-but-unflushed
change unless the writing code explicitly calls `.flush()` first — several services do call
`.flush()` mid-method for exactly this reason, but this is an implicit, call-site-by-call-site
convention, not a guarantee any session-management abstraction enforces.

**What must CQRS preserve to avoid transaction regressions?**
1. For the first pilot specifically, a reader should reuse the **existing shared session** — this
   is a pragmatic incremental choice, not an absolute architectural law. A second session is not
   *inherently* stale; after a committed write, a fresh session can give a perfectly clean view
   with no identity-map residue. The reason to reuse the existing session for Phase 1 is narrower
   and more honest: doing so preserves today's exact transaction and read-after-write behavior
   (including the `autoflush=False` + explicit-flush discipline every write path already relies
   on) without expanding the pilot's scope into a session-lifecycle redesign. **A separate,
   operation-scoped read session — together with a proper operation-scoped Unit of Work replacing
   today's one-session-per-process model — is a legitimate future architectural direction and
   should be evaluated on its own, later, not folded into or blocked by this pilot** (tracked as an
   open question in §20).
2. The governed/ungoverned `commit: bool` threading pattern (Cost, Budget, TaskDependency,
   Baseline) must be preserved verbatim if any of those write paths are ever wrapped in a
   `CommandService` — a CQRS command layer that hardcodes `commit=True` would silently break
   approval-governed writes.
3. Any new read path must **not** be added as a method on a write repository that also gets
   included in a future transaction-boundary refactor of that repository — the fat-repository
   findings in §9a are exactly the seams a `Reader` extraction should target first.

---

## 11. Authorization, tenancy and security flow

**Authenticated user/session**: resolved once via `UserSessionContext.principal`, built at
composition time (`platform_registry.py:207`) and validated via
`auth_service.validate_session_principal`. Every PM service that checks permissions holds a
reference to the same `UserSessionContext` instance (`user_session` constructor parameter).

**Tenant ID / organization ID**: `TenantContextService`
(`src/core/platform/application/tenant/tenancy/tenant_context.py`) — `require_active_tenant_id`,
`require_active_organization_id`, `require_organization_context`. Instantiated once, then wired
into every PM write-path service via constructor injection. RLS session variables
(`app.tenant_id`/`app.organization_id`/`app.user_id`) are set on every new transaction via a
SQLAlchemy `after_begin` event listener (`postgresql_rls.py:52-81`), sourced from the same
`UserSessionContext` (or a `WorkerTenantScope` contextvar for background workers).
`validate_postgresql_execution_role` additionally asserts the DB role cannot bypass RLS, failing
closed if it can.

**Project scope**: `require_project_permission` (from
`src/core/modules/project_management/access/scope_permissions.py`'s
`resolve_project_scope_permissions`, registered as a `ScopedRolePolicy(scope_type="project", ...)`)
— checked in **every** write method audited except the deliberately-internal, unchecked halves of
governed splits (`_apply_*_decision`) and a small number of confirmed gaps below.

**Permission**: `require_permission`/`require_any_permission`
(`permission_checks.py:15-56`) delegate to a singleton `get_authorization_engine()`, checked against
`DEFAULT_PERMISSIONS`/role bundles in `role_permission_catalog.py`. On denial,
`record_authorization_denial` persists a `SecurityDenialEvent` before raising
`BusinessRuleError(code="PERMISSION_DENIED")` — every denial is itself audited.

**Sensitive-finance permission**: `finance.read_sensitive` exists and is checked — but **only**
inside `FinanceService.get_finance_snapshot` (a soft, non-denying check that decides redaction, not
access). It has **no equivalent anywhere in `ReportingService`**.

**RLS**: enforced at the database session level for every table with `tenant_id`/`organization_id`
columns (the "root" aggregates — Project, Resource, and every `project_finance_*` table).
Transitively-scoped child tables (Task, TaskAssignment, CostItem, register entries, comments,
baseline rows) have no RLS of their own; their tenant safety depends entirely on the repository
layer's join-up-to-parent scoping being correct everywhere, which the tenant-hardening test suite
(§13) does exercise extensively.

**Where do checks occur, and in how many layers?** The **dominant** pattern is exactly two layers:
application-service permission check (desktop API layer does none itself) + database RLS as a
backstop for root-scoped tables. Confirmed **no** desktop API method performs its own permission
check independent of the service it calls — the desktop layer is a pure pass-through for
authorization.

**Confirmed missing or inconsistent defense-in-depth checks** (this is the audit's clearest P0/P1
security-relevant finding set, independent of and additional to the finance-permission split
already flagged in §1/§7):

1. **`PortfolioResourcePoolService.get_pool_report`/`get_resource_demand_by_project`** — **no
   permission check at all**, on a cross-project resource-capacity report. `get_pool_report` does
   resolve an organization id (unused downstream); `get_resource_demand_by_project` doesn't even do
   that.
2. **`ForecastCostService`** and **`CostService`** — `ForecastCostService` accepts no
   `tenant_context_service` at all; `CostService` accepts it as optional and never calls
   `require_organization_context` anywhere in its methods. Both rely entirely on repository-level
   scoping for tenant isolation, unlike every sibling financial service in the same layer, which
   asserts tenant context explicitly.
3. **`Portfolio.create_project_dependency`** — gated only by the global `portfolio.manage`
   permission, with **no `require_project_permission`** for either of the two specific projects
   being linked, despite the operation being inherently project-scoped; project-level filtering
   happens only via `_accessible_projects()`'s read-side filter, which is a different guarantee than
   a write-time scope check.
4. **`TaskService.get_dependency_diagnostics`** (`queries/dependency_diagnostics.py`) — **no
   permission check anywhere in the file**, exposing schedule-impact simulation data; safe today
   only because its only current callers (`add_dependency`/`update_dependency`) already checked
   permission before calling it, but the method itself is not self-defending, unlike its sibling
   `list_dependencies_for_task`.
5. **`TaskQueryMixin.list_tasks_for_resource`/`list_assignments_for_tasks`** call
   `self._user_session.has_project_permission(...)` **directly**, bypassing the
   `require_project_permission` helper every other read/write method in the same class uses — an
   inconsistent, lower-level authorization API used in exactly two places.
6. **`TaskAssignmentMixin.get_assignment_action_context`** uses `get_authorization_engine()`
   directly (bypassing `require_permission`) — same inconsistency pattern, mirrored in
   `CollaborationService`'s equivalent action-context method.

---

## 12. Events, audit, activity and refresh behavior

### 12a. Domain event catalog

`src/core/shared/events/domain_events.py` — a custom, thread-safe, non-Qt `Signal[T]` primitive
(`signal.py`). Full PM-relevant catalog: `project_changed`, `tasks_changed`,
`timesheet_periods_changed`, `costs_changed`, `resources_changed`, `baseline_changed`,
`budgets_changed`, `planned_costs_changed`, `approvals_changed`, `register_changed`,
`collaboration_changed`, `portfolio_changed` — plus two generic aggregator signals,
`shared_master_changed` and `domain_changed`, that every named signal auto-bridges into via
`_BRIDGE_SPECS`.

| Event | Emitted by | Timing | Subscriber (production) | Transactional? | Purpose |
|---|---|---|---|---|---|
| `project_changed` | `ProjectLifecycleMixin` (create/update; **absent** from `set_status`/`delete`) | after commit | generic `domain_changed` bridge → QML workspace controllers | No (local, in-process, post-commit) | UI refresh |
| `tasks_changed` | 7 task command mixins + `dashboard_service.py` | after commit (or dropped on `commit=False` governed paths) | same bridge | No | UI refresh |
| `costs_changed` | `cost_lifecycle.py` | after commit | same bridge | No | UI refresh |
| `budgets_changed` | `budget_service.py` (9 call sites) | after commit | same bridge | No | UI refresh |
| `planned_costs_changed` | `planned_cost_service.py` | after commit | same bridge | No | UI refresh |
| `baseline_changed` | `baseline_service.py` | after commit | same bridge | No | UI refresh |
| `register_changed` | `register_lifecycle.py` | after commit | same bridge | No | UI refresh |
| `resources_changed` | resource command mixins | after commit | same bridge | No | UI refresh |
| `portfolio_changed` | portfolio command mixins | after commit (no rollback precedes it — see §6/§14 P0/P1) | same bridge | No | UI refresh |
| `collaboration_changed` | collaboration command mixins | after commit (same caveat) | same bridge | No | UI refresh |
| `approvals_changed` | `ApprovalService` | after its shared commit | same bridge + notification dispatch | No | UI refresh + notification |

**Production subscription pattern**: direct `.connect()` calls on individual per-domain signals
appear **only in test files**. In production, QML workspace-controller base classes
(`workspace_controller_base.py:193-242`) subscribe **once, generically**, to the aggregator
`domain_changed` signal, then filter incoming `DomainChangeEvent`s by `entity_type`/`scope_code`
before triggering a debounced UI refresh. So the real production shape is "one generic bridged
signal → per-controller filter → refresh," not "many individual per-signal subscribers" — an
important fact for §19's guardrail design (a query-count/read-model test should assert against this
actual pattern, not an imagined one).

**Business/domain events vs. integration events vs. local UI refresh signals**: there is currently
**no distinction** between these three categories in this codebase — every signal listed above
serves purely as a local UI-refresh trigger. No signal carries a durable payload, no signal is
consumed outside the current process, and no outbox/inbox exists to promote any of them to a true
integration event. `ADR-PF-011` proposes this distinction; it is accepted in principle but its
stores are explicitly deferred to Phase C and not built.

### 12b. Activity vs. Enterprise Audit

- **Activity** (`record_activity`) is a **user-facing feed**, not an authoritative record — no
  fail-closed option, and (per §10) frequently committed as a **separate transaction** after the
  primary write in Projects/Tasks/Resources.
- **Enterprise Audit** (`record_audit_entry`) is the authoritative, fail-closed financial/security
  audit trail, **always** recorded `commit=False` inside the same transaction as the mutation it
  describes, across every financial and governed write path audited.

---

## 13. Existing tests and architecture enforcement

**Scale**: `src/tests/project_management/` — 96 files, 451 tests. `src/tests/pm/` — 9 files, 140
tests, a **second, parallel, non-overlapping suite for the same module** (the older/newer split is
not reconciled — both directories exist simultaneously and are both live).

**Mapped to audited runtime paths** (representative, full mapping verified per capability):

| Capability | desktop-API test? | repository-integration test? | Notes |
|---|---|---|---|
| Projects | Yes (`test_project_management_desktop_api_projects.py`) | Yes | Well covered |
| Tasks (incl. WBS) | Yes (CRUD, bulk-assign, WBS hierarchy) | Yes, incl. an Alembic-level migration test | Well covered |
| Resources | Yes | Yes | Covered |
| Scheduling (incl. Baselines) | Yes | Partial — baseline domain logic is explicitly "pure domain, no DB" in `src/tests/pm/test_baseline_lifecycle.py`; no dedicated DB-level baseline persistence test beyond a generic integrity checker | Baseline persistence coverage gap |
| **Financials — Budget** | **Thin** — only 2 generic financials-API tests reference it, no dedicated `test_project_management_desktop_api_budgets.py` | Yes, extensively (`test_project_finance_budgets.py`, 42 tests) | **The newest, most actively developed area has the thinnest desktop-boundary coverage** |
| **Financials — RateCards** | **None found** | Yes (23+ tests, plus a migration test) | Same gap |
| **Financials — PlannedCosts** | **None found** | Yes (13 tests) | Same gap |
| Financials — Forecast/EVM | Yes (delegation test) | Stub-based only, not true DB-backed | — |
| Portfolio | Yes | Yes | Covered |
| Timesheets | Yes (desktop) | **Only via fakes, no ORM/DB-level test found** | Gap |
| Register/Risk | Thin (1 desktop-API test) | Domain-only, no dedicated ORM repository test | Thin |
| Reporting/Import-Export | None under this naming | Yes (openpyxl export test; import parsers tested in isolation, "no DB, no Qt") | No test proves an imported file round-trips through the desktop API into persisted rows |

**Architecture-guardrail tests** (PM-relevant, all confirmed present and passing at audit time):
service "orchestrator only" checks (`test_architecture_guardrails_services.py`), legacy-ORM-facade
removal (`test_architecture_guardrails_legacy_orm.py`), per-file line-count budgets incl. this
module's own largest test files (`test_architecture_guardrails_size_migration.py`),
`financial_numeric`/RLS marker checks (`test_project_finance_persistence_guardrails.py`),
Phase-A2 import-direction checks for `financial_sources.py` and forecast-service composition
(`test_project_finance_a2_architecture.py`), layering direction (`src.core` must not import
`src.ui_qml`/`src.ui`) (`test_qml_architecture_guardrails_layers.py`), Task-owned-WBS invariants
(`test_task_wbs_architecture.py`).

**Special patterns confirmed absent** (all four checked explicitly, per the audit's own required
method): **no** "git-stash baseline of N known pre-existing failures" mechanism exists in this test
suite (despite that pattern being used *manually* in prior development sessions per project memory
— it is not itself encoded as a test harness); **no** query-count/N+1 assertion anywhere (zero
matches for `before_cursor_execute`/`QueryCounter`-style patterns); **no** forced mid-transaction
commit-failure injection test (only natural `IntegrityError`s from real constraint violations, and
`ConcurrencyError`/optimistic-lock-conflict tests, which are a different guarantee); **confirmed
present**: consistent, well-covered cross-tenant isolation tests (`test_tenant_isolation_services_pm.py`,
`test_repository_tenant_hardening_secondary_reads/writes.py`, and others) using a consistent
org-a/org-b fixture convention.

**No composition-level test** instantiates `project_registry`/`ProjectManagementServiceBundle`/
`RepositoryBundle` directly and exercises it end-to-end — composition correctness relies on one
architecture test that string-matches source text (`test_forecast_service_is_composed_and_desktop_builders_are_mapping_only`),
not an actual instantiation-and-call test.

---

## 14. Current architectural problems relevant to CQRS

| Priority | Finding | Exact evidence | Consequence | CQRS relevance |
|---|---|---|---|---|
| **P0** | Two independent, non-overlapping permission systems gate the same financial computations | `FinanceService.get_finance_snapshot` requires `finance.read` (+redacts unless `finance.read_sensitive`); `ReportingService._require_view` (`reporting_service.py:78-86`) requires `report.view` only, with **no redaction equivalent anywhere in its 6 mixins** | A `report.view`-only user can read full unredacted labor-by-resource detail that `finance.read`-gated callers deliberately cannot see | A query-service/reader consolidation is the natural moment to unify this — must be scoped deliberately (§20), not silently narrowed or widened |
| **P0** | `PortfolioResourcePoolService.get_pool_report`/`get_resource_demand_by_project` have no permission check at all | confirmed by direct inspection, §11 | Cross-project resource-capacity data readable by anyone who can reach the service | **Resolved as a scheduling matter** ("Resolved Decisions" after §20): fixed immediately in the service itself as Phase 0A.1 (§18, §15c), independent of whether a Portfolio Reader is ever built — this fix does not wait for, and is not satisfied by, any future CQRS work on Portfolio |
| **P0** | Portfolio and Collaboration write methods commit with **no `try/except`/rollback anywhere** | confirmed across `portfolio/services/portfolio_service.py` and `collaboration/services/collaboration_service.py`, every command method | A failure mid-write in these two areas has no explicit, intentional rollback path in the application layer | **Resolved as a scheduling matter** ("Resolved Decisions" after §20): fixed immediately as Phase 0A.2 (Portfolio)/Phase 0A.3 (Collaboration), independent of any CQRS work in these areas — a CQRS write-side refactor must not paper over this by wrapping it in a "command service" that hides the missing error handling instead |
| **P0** | `TaskAssignmentBridgeMixin.assign_resource`'s no-`project_resource_repo` fallback path performs two independent, non-atomic commits for one logical "assign resource" operation | §6 trace | Partial application possible: `ProjectResource` created but assignment fails, or vice versa | Command-side extraction should collapse this to one transaction, not preserve it |
| **P1** | `FinanceService.get_finance_snapshot` performs `cost_repo.list_by_project` 5×, `project_resource_repo.list_by_project` 3×, a full `LaborCostEngine.calculate_project_labor_details` sub-graph 3×, `rate_resolver.resolve_many` 6× per call, none cached | §7's canonical call-count table | Confirmed, evidenced performance risk (not yet measured in wall-clock terms — see §17/§20) | **The strongest evidenced CQRS read-side opportunity in the module** — direct candidate for §17's pilot |
| **P1** | One SQLAlchemy `Session` and its identity map live for the entire desktop process, not per operation | §10 (session factory, `app.py:59`) | Identity-map growth over a long-running session, stale-state risk mitigated only by call-site-by-call-site `flush()` discipline, dependence on explicit rollback/flush conventions rather than a structural guarantee, unclear per-operation boundaries, and a constraint on ever running PM work on a background thread | CQRS does **not** solve this weakness — Phase 1 deliberately preserves the shared session (§10, §15b); a later, separately-scoped operation-scoped Session/Unit-of-Work investigation is required (see the new "Future Session/UoW modernization" phase after §18 Phase 6, and §20 open question 6) |
| **P1** | `EarnedValueSeriesCalculator.build_series` re-triggers the full snapshot chain above once per month in the series | §7 | For a 24-month project, dozens of redundant round-trips | Same reader/read-model fix as above would also resolve this transitively, once Phase 3A explicitly migrates and tests that path (§18) |
| **P1** | No SQL-side aggregation anywhere in the persistence layer — every total/count/rollup is Python-side over a fully materialized list | §9c, confirmed zero `func.sum`/`func.count`/`group_by` matches | Systemic risk underlying every N+1/over-fetch finding in this document | Core justification for introducing SQL projection statements behind a `Reader`, not a theoretical preference |
| **P1** | `ForecastCostService.compute_forecast` computes BAC/AC from raw `CostItem` totals, bypassing `CostPolicyEngine`'s labor policy | §7 | Two services under the same `finance.read` permission can disagree on "actual cost" whenever computed labor exists | A read-model consolidation must decide (and document) which source is canonical — cannot silently pick one without a product/architecture decision (§20) |
| **P1** | "N+1 across the whole accessible portfolio" pattern independently duplicated in Portfolio (`list_portfolio_heatmap`, scenario evaluation) and Collaboration (`_accessible_task_context_for_collaboration`) | application-layer audit | Both load every accessible project/task first, then loop a per-item downstream call | Same reader pattern would fix both, but they are two separate pilots (Phase 3C, Phase 3D — §18), not one |
| **P1** | Fat repositories mixing aggregate persistence with report/aggregate-query methods | §9a — `ProjectBudgetRepository`, `AssignmentRepository`, `ProjectRateCardRepository`, `ProjectCostCodeRepository` | Report-shaped methods (`list_effective_lines`, `has_open_for_project`, `is_default_for_any_profile`) live on write-oriented contracts | Direct target for extracting a `Reader` per the `RateResolutionReader` precedent |
| **P1/P2** (product decision) | `Activity` (`record_activity`) is committed as a **separate, non-atomic transaction after the primary write** in Projects, Tasks, and Resources, while `EnterpriseAuditService`/`record_audit_entry` is always folded into the same transaction as the mutation it describes, fail-closed where required | §10, §12 | A mutation can succeed with no corresponding Activity-feed entry if the second commit fails, or if the process crashes between the two commits — `Activity` is currently a best-effort, user-facing presentation feed, not a guarantee, even though nothing in the UI currently signals that distinction to a user | Not itself a CQRS finding, but must not be silently carried forward as "guaranteed" by any read model built on top of Activity data; classify as P1 if product intends Activity to be a reliable record, P2 if it is accepted as best-effort by design — see the consolidated statement after §14 |
| **P2** | Desktop-layer builder/service files reach into other services' private attributes (`_resource_repo`, `_project_resource_repo`, `_tenant_context_service`) as a fallback | `api/desktop/tasks/services/access_resolution_service.py`, `api/desktop/resources/services/availability_resolution_service.py`, `api/desktop/projects/builders/resource_builder.py` | Undocumented coupling; a future reader built on this pattern inherits a hidden dependency | Must not be the template for any new reader — readers must depend on public contracts only; consolidated with every other adapter-boundary finding in "Desktop Adapter Boundary Weaknesses" immediately after this table |
| **P2** | Business-rule duplication: the same "> 100% overload" threshold rule reimplemented 3× across Dashboard builders; CPM lag/constraint logic reimplemented independently in `SchedulingEngine`, `CPMCalculator`, `DependencyResolver`, and `TaskDependencyDiagnosticsMixin` | §6, §7 | Any fix to one copy risks not propagating to the others | Not itself a CQRS problem, but a consolidation opportunity a read-model extraction would naturally surface |
| **P2** | Money fields are `float` end-to-end at the desktop DTO boundary for every non-ADR-PF-005 financial area | §5, §8 — acknowledged `TRANSITION(PF-A1-DESKTOP-FLOAT)` | Precision risk at the UI boundary, already known and tracked | A read-model migration is a natural moment to introduce Decimal-safe DTOs for the migrated area only — not a reason to block the pilot |
| **P2** | `TaskDependencyMixin.update_dependency` has no governed path and performs its schedule resync as a second, separate, non-atomic commit | class's own docstring confirms "dead, unwired" | Least atomic write path in the module, but explicitly acknowledged as unused/legacy | Out of scope for the CQRS pilot; flag for cleanup separately |
| **P3** | Two parallel, largely duplicated resource-leveling implementations (`ResourceLevelingMixin` vs `ResourceLevelingEngine`) both live, `ResourceLevelingEngine`'s docstring claims to "replace" the mixin but nothing retires it | scheduling audit | Maintainability only | Not a CQRS concern |
| **P3** | Two parallel test suites (`src/tests/project_management/`, `src/tests/pm/`) for the same module, unreconciled | §13 | Maintainability/discoverability | Not a CQRS concern, but relevant to where the pilot's new tests should live (§17) |

All findings above are **confirmed** by direct file inspection, not inferred. (An earlier revision
of this document could not yet verify three Scheduling `services/*.py` files here — that gap was
subsequently closed in the "Desktop Adapter Responsibility Audit" section, and every finding above
remains as originally stated, unaffected by that later verification.)

### Session lifecycle — future phase (not part of any CQRS phase)

CQRS does not solve the long-lived-`Session` finding above; it is orthogonal. A future,
independently-scoped modernization is recorded here so it is not lost, and so no reader introduced
by this document's phases is mistaken for a fix to it:

```text
Future Session/UoW modernization
→ define a desktop operation boundary
→ create one Session/UoW per operation
→ share that operation's Session across services, repositories, readers,
  audit and transactional event staging
→ commit/rollback centrally
→ close the Session after the operation
```

This is explicitly **not scheduled inside Phase 1** (§18) and is not a prerequisite for it — Phase
1 reuses the existing shared session by design (§10, §15b, Executive Summary correction).

### Activity vs. Enterprise Audit — semantic distinction

- **Enterprise Audit** — authoritative; mandatory/fail-closed where required; transactionally
  coupled to the mutation it describes (§10, §12b).
- **Activity** — a user-facing presentation feed; currently best-effort in Projects, Tasks, and
  Resources; may be missing even though the mutation succeeded, because it commits as a second,
  independent transaction after the primary write (§10, §12b).

This document does not silently imply Activity is guaranteed today — it is not, in exactly those
three capability areas. Two future alternatives exist, and choosing between them is a product
decision this document does not make: (a) stage Activity in the main transaction, the same way
Enterprise Audit already is; or (b) publish it reliably through a transactional outbox after
commit. Either is a standalone reliability fix, independent of the CQRS pilot.

---

## Desktop Adapter Boundary Weaknesses

This section consolidates every desktop-adapter-layer finding already documented individually in
§5, §6, §7, and the Executive Summary — it adds no new evidence, it gives the existing evidence one
place to be read together and one target boundary definition to enforce going forward.

**Consolidated examples, each already evidenced elsewhere in this document:**

- Private repository/service-attribute access as a fallback (`_resource_repo`,
  `_project_resource_repo`, `_tenant_context_service`) — Executive Summary, §5 (Projects, Tasks,
  Resources builders/services).
- Application-service construction *inside* a desktop adapter helper — `resources/services/
  availability_resolution_service.py`'s `resolve_availability_service()`, which builds a brand-new
  `ResourceAvailabilityService` from other services' private attributes (§5).
- A rate-affecting-update decision made in the Resource API layer rather than inside
  `ResourceService` — `update_resource`'s `hourly_rate_changed`/`rate_affecting_change` computation
  (§6).
- Scheduling/calendar arithmetic performed directly in the API layer — `calculate_working_days`'s
  `_date_range` helper defined in `scheduling/api.py` itself (§5).
- Certification lifecycle rules computed in a serializer — `resources/serializers/
  certification_serializer.py`'s hardcoded 30-day `cert_status` threshold (§5).
- Severity/overdue triage policy implemented in a Register builder rather than sourced from the
  domain/application layer — `register/builders/entry_list_builder.py`'s `severity_rank`/
  `is_overdue` sort (§5).
- Comment-thread construction performed in the Collaboration API — `collaboration/api.py::
  _threaded_comments`'s in-memory tree build (Appendix A).
- Financial/procurement reporting logic living only in the desktop facade with no backing service
  method — `get_project_procurement_commitments` (§5, confirmed to have no QML consumer at all).
- Fixed-limit, client-side filtering instead of a scoped query — `list_project_requisitions`'s
  500-row cap filtered in Python (§5); `list_task_reservations`'s identical pattern (Appendix A).
- Broad exception handling that produces empty data instead of surfacing the real failure —
  recurring across `access_resolution_service.py`, `resource_lookup_service.py`,
  `list_project_requisitions`, `list_task_reservations`, `dashboard`'s `_list_pending_approvals`,
  and others (§5, §6, Appendix A).
- Reflection-based `call_with_supported_kwargs` at the Projects desktop boundary, hiding
  signature drift between desktop commands and `ProjectService` (§5; expanded below).
- Fallback paths that silently hide missing composition instead of failing loudly — the
  "moved to Platform Admin" Scheduling calendar stubs (§5), `FinancialsDesktopApi`'s
  `finance_service is None` degraded-snapshot path (§7).

**Target desktop boundary** (the shape new and migrated code should converge on):

```text
desktop request DTO
  → presentation-shape validation
  → application input mapping
  → public application service call
  → application result/facts serialization
  → desktop DTO
```

**New desktop adapter code must not:**

- read private (`_`-prefixed) attributes on injected services;
- construct application services;
- access repositories;
- decide domain transitions;
- perform authoritative financial/scheduling calculations;
- implement permission policy;
- silently convert authorization, tenant-context, or infrastructure failures into empty results.

**Existing violations listed above may be grandfathered temporarily** — this document does not
require a retroactive cleanup pass as a precondition for the Finance Snapshot pilot. **No new
violation of the target boundary is permitted going forward**, including inside any code the pilot
itself touches.

### Composition weaknesses

**Reflective tenant-context backfilling.** The composition root constructs
`SqlAlchemyServicePrincipalRepository`/`SqlAlchemyApiKeyCredentialRepository` with
`tenant_context_service=None`, then later mutates their private `_tenant_context_service` attribute
reflectively once `TenantContextService` exists (`platform_registry.py:224-228`, §4c). Risks:
partially-initialized objects between construction and the reflective patch; constructor invariants
bypassed (the constructor signature implies the dependency is optional, when in practice it is
required before the object is used); a hidden ordering dependency between repository construction
and platform-service construction that is not visible from either construction call site alone;
and composition tests becoming difficult to write correctly, since a naively-constructed test double
would omit the patch step and silently diverge from production wiring. Recommended direction: a
future constructor/factory ordering correction (construct `TenantContextService` first, or accept a
lazily-resolved provider callable) rather than private-state mutation after the fact — not scheduled
inside Phase 1.

**Reflection shim at the desktop boundary.** `call_with_supported_kwargs`
(`api/desktop/projects/utils/project_utils.py`, used by `create_project`/`update_project`) uses
`inspect.signature` to filter which command fields are actually passed to `ProjectService`. Risks: a
parameter removed or renamed on either side of the boundary is silently dropped rather than causing
a type error or test failure; static typing cannot prove the boundary is complete, since the
reflection defeats it; and a test asserting a command round-trips correctly can pass while silently
never having exercised a field that was quietly filtered out. Recommendation: new or migrated
desktop endpoints should use an explicit, enumerated command-to-service-argument mapping instead of
this reflection pattern — the existing `call_with_supported_kwargs` call sites are grandfathered,
not required to change for Phase 1.

**Missing runtime composition test.** §4c already notes composition correctness relies on a
source-text-matching architecture test, not an actual instantiation test. This document adds a
concrete, required test for the pilot specifically (also listed in §17's test requirements): a test
that constructs `RepositoryBundle` → constructs `ProjectManagementServiceBundle` → constructs
`DesktopApiRegistry` → calls `FinancialsDesktopApi.get_finance_snapshot` → and asserts (via a spy,
mock injection point, or direct object-identity check) that the call actually reaches the real
`SqlAlchemyFinanceSnapshotReader`, using the test database and real composition wherever practical.
This test exists specifically to prove the Reader is wired at runtime, not merely importable and
unit-testable in isolation — a gap this document's own audit found (§4c, §13) and that the pilot
must not reproduce.

---

## 15. CQRS fit analysis for this repository

This section evaluates, capability area by capability area, whether and how a command/query split
should be introduced — **not** whether it should be introduced everywhere at once. Per the
constraints given: no event sourcing, no separate database, no command/query handler classes
imposed where the existing service style already works, no mass rewrite.

### 15a. Write side — what changes, what doesn't

**The existing pattern already mostly matches the target shape** described in the prompt:

```text
Desktop request DTO → application service method (acts as the "CommandService") → domain aggregate
  → write Repository (unchanged) → ORM/database → domain entity (majority) / selected CommandResult
  → desktop response DTO
```

Most services still return the full domain aggregate rather than a narrower `CommandResult`.
**Recommendation: introduce `CommandResult` dataclasses only where a service returns something
broader than the caller needs or has multiple successful outcomes, and only for the capability
being actively touched — not as a blanket rule.** Concretely:

- `TaskService.create_task`/`update_task` returning the full `Task` aggregate is fine as-is; the
  desktop serializer already narrows it correctly. **No change needed here.**
- **Implemented in Phase 4:** `BudgetService.approve_budget` returns immutable
  `BudgetApprovalResult` for both successful outcomes (`applied` and `pending_approval`). It carries
  only budget/project identity, budget status/version, and the optional approval-request ID. The
  internal `_apply_approval_decision` deliberately continues returning `ProjectBudget` inside the
  transaction-owning application/composition path. No other write was converted speculatively.
- **Should existing services be split into command/query services?** Not wholesale. The
  `*QueryMixin`/`*CommandMixin`/`*LifecycleMixin` convention already in every composed service
  **is** the command/query split, lexically, today. Splitting them into two *separate classes* with
  two separate constructors (and, worse, two separate sessions) would be pure churn with no
  behavioral benefit, given they share one session and one transaction model. **Recommendation:
  keep write-side services exactly as they are.** The valuable split is on the *read* side, where
  the mixins currently do the wrong kind of work (Python aggregation over full-list fetches),
  not the write side.
- **Where command objects belong, if introduced later**: only for methods whose keyword-argument
  surface has grown unwieldy (e.g. `TaskService.create_task` already takes a desktop-layer
  `TaskCreateCommand` at the API boundary — an *application-layer* `CreateTaskCommand` dataclass
  would be a second, redundant type unless it's needed to decouple from a future FastAPI boundary,
  which is explicitly out of scope for this pilot). **Do not introduce command objects speculatively.**
- **Existing write repositories remain unchanged initially** — every fat-repository finding in §9a
  is a real signal, but untangling `ProjectBudgetRepository`'s report-shaped methods
  (`has_open_for_project`) from its write methods is orthogonal to the read-model work in §15b and
  should be a **later** phase (§18 Phase 3+), not bundled into the first pilot.

### 15b. Read side — where the real work belongs, and who is allowed to call the reader

**The reader returns facts, not the finished snapshot.** The first draft of this document blurred
this and stated two different things in two places — that is corrected here into one canonical
shape. A SQL reader must not simultaneously return a policy-applied, redaction-aware, business-
composed result while an engine elsewhere still owns part of the calculation; the responsibilities
have to be split cleanly:

**Ownership is fixed, not left as an implementation-time choice.** An earlier draft of this section
left `CostPolicyEngine`'s fate open ("either becomes a thin facts-consumer or its policy logic is
absorbed into `FinanceService`") — that is a load-bearing policy-ownership decision and is not
appropriate to leave open during implementation. It is resolved here:

- **`FinanceSnapshotReader`** (SQL) — owns exactly one thing: SQL acquisition. It turns
  `cost_repo.list_by_project()`-style full-table fetches into real `SELECT`/`func.sum`/`GROUP BY`
  aggregates and returns **facts** (`FinanceSnapshotFacts` — see §16 and the source-oriented
  redefinition below), not a finished `FinanceSnapshot` and not a policy decision of any kind.
- **`LaborCostEngine`** — owns labor-rate calculation. Unchanged responsibility, called **once**
  instead of three times (the redundancy this pilot exists to remove, §7). Hours×rate calculation
  is genuine domain business logic, not a SQL-projection candidate, and stays exactly where it is.
- **`CostPolicyEngine`** — **remains the policy owner, unconditionally.** It keeps
  manual/computed-labor source reconciliation and planned-cost policy — the exact rules it applies
  today — but is now sourced from `FinanceSnapshotReader`'s facts and `LaborCostEngine`'s labor
  result instead of re-fetching raw lists itself. `FinanceService` **must not** duplicate
  `CostPolicyEngine`'s reconciliation rules, and this policy must not be reimplemented in SQL.
  Concretely, `CostPolicyEngine` gains one new composition entry point (exact name may fit existing
  naming conventions; the shape is what's fixed): `CostPolicyEngine.compose_from_facts(facts,
  labor_details, ...existing policy inputs)`.
- **`FinanceService`** — owns orchestration and redaction only. It resolves permission,
  tenant/organization, and `as_of`; calls `FinanceSnapshotReader.read_facts` once; calls
  `LaborCostEngine` once; calls `CostPolicyEngine.compose_from_facts(...)` once; composes the
  remaining ledger/cashflow/analytics sections from those already-composed results (not by
  re-fetching); applies `finance.read_sensitive` redaction; and returns the existing
  `FinanceSnapshot`, unchanged in type and shape.

**Do not** copy `CostPolicyEngine`'s policy into `FinanceService`. **Do not** implement the policy
in SQL. **Do not** keep both the old (repeated-list-fetch) and new (facts-sourced) policy
implementations live side by side past Phase 1's cutover — the old call sites are replaced, not
duplicated (§18 Phase 1's compatibility approach already states this; it is repeated here because
it is a direct consequence of fixing this ownership question).

**Verified against the actual source** (`application/financials/services/finance_service.py:118-124`):
the real, current signature is `get_finance_snapshot(self, project_id: str, *, as_of: date | None =
None, period: str = "month") -> FinanceSnapshot`, with `as_of = as_of or date.today()` resolved
inline at the top of the method — there is **no `Clock` dependency on this service today** (confirmed
by its constructor, `finance_service.py:61-74`); the resolution is a raw `date.today()` call, not an
injected time abstraction. Phase 1 does not add, remove, or change either keyword parameter — the
diagram below shows the real signature, not a new one:

```text
Desktop API
  → FinanceService.get_finance_snapshot(project_id, *, as_of=None, period="month")   # UNCHANGED signature, both kwargs already exist today
      → as_of = as_of or date.today()                                                # UNCHANGED — already inline today, no Clock exists on this service, none is added
      → require finance.read; resolve tenant_id/organization_id
      → FinanceSnapshotReader.read_facts(tenant_id, organization_id, project_id, as_of)   # SQL acquisition, ONE call, using the already-resolved as_of
      → LaborCostEngine.calculate_project_labor_details(...)                              # labor-rate calculation, ONE call (not three)
      → CostPolicyEngine.compose_from_facts(facts, labor_details, ...)                    # manual/computed-labor reconciliation + planned-cost policy, ONE call
      → FinanceService composes remaining ledger/cashflow/analytics sections from the above (no re-fetching), period passed through unchanged to the cashflow builder
      → apply finance.read_sensitive redaction
  → existing FinanceSnapshot (unchanged type)
  → existing snapshot_serializer.py (unchanged)
  → existing FinancialSnapshotDto (unchanged type)
```

(The full, formally-numbered version of this flow — including what the Reader is explicitly
forbidden from doing — is in the new "Approved Phase 1 Flow" section before the acceptance
checklist.)

**Nothing else calls `FinanceSnapshotReader` in this pilot.** `CostPolicyEngine`/`LaborCostEngine`
themselves are not injected with the reader, and `ReportingService`'s mixins are not modified —
see the "no free lunch for ReportingService" note below.

**Naming: `Reader`, not `QueryRepository` or `ReadRepository`.** This repository has already
chosen `RateResolutionReader` as a `Protocol` name, with a concrete `SqlAlchemyRateResolutionReader`
adapter — matching that exact precedent (rather than introducing a third piece of vocabulary) is
the lower-risk, higher-consistency choice.

**Where read models/facts belong, and why not under `application/`.** The first draft placed
`FinanceSnapshotReadModel` under `application/financials/results/` while the `Reader` `Protocol`
lived under `contracts/`, with the protocol importing and returning the application-layer type —
that is a real circular dependency (`application → contracts` for the service to consume the
protocol, and `contracts → application` for the protocol to reference the result type), not merely
an import-order inconvenience. **Fix**: the facts dataclass moves to live *with* the protocol, under
`contracts/reads/financials/models/finance_snapshot_facts.py` (see §16's corrected tree). The
dependency direction is then unidirectional: `application → contracts`, `infrastructure →
contracts`, and `contracts` itself depends only on `domain`/`platform` value objects (`Money`,
`CurrencyCode`) — never on `application`. The existing, unchanged `FinanceSnapshot` dataclass
remains the public application-layer result `FinanceService` returns; there is no need to invent a
second, differently-named application-layer type merely to claim CQRS vocabulary.

**Do application services need to change to consume a Reader?** Only `FinanceService`'s internals,
per the call path above — its public signature (`get_finance_snapshot(project_id, *, as_of=None,
period="month") -> FinanceSnapshot`, verified against the current source, above) does not change.

**How tenant scope is supplied to readers**: exactly the pattern `RateResolutionReader` already
uses — explicit `tenant_id`/`organization_id` parameters on every method, resolved by the calling
service from `TenantContextService` before the call, **not** an ambient dependency inside the
reader itself.

**How the SQLAlchemy session is supplied, for this pilot**: the reader takes the same shared
session injected into every other repository, for the reasons given in §10 (preserve today's exact
transaction/read-after-write behavior without expanding this pilot into a session-lifecycle
redesign) — **not** because a second session would be inherently unsafe; that stronger claim is
explicitly withdrawn (§10 correction, §20 open question).

**How reports/exports consume canonical read models — corrected, no "for free" claim.**
`ReportingService`'s six mixins today call `CostPolicyEngine`/`LaborCostEngine`/
`EarnedValueCalculator` directly, so if a *later* phase changes those engines' internals to consume
`FinanceSnapshotReader`, `ReportingService`'s call chain would change too, automatically, with no
code change on its side. **This document does not claim that benefit for Phase 1**, because Phase 1
does not touch `CostPolicyEngine`/`LaborCostEngine`'s own internals — it changes only how
`FinanceService` orchestrates them (see the call path above). Any performance change to
`ReportingService` is unverified, unclaimed, and deferred to whichever later phase explicitly
modifies and re-tests that path (§18 Phase 3+). The **permission-model unification** (§14 P0) is a
separate, deliberate decision layered on top of all of this — not a side effect of the read-model
work.

### 15c. Which services should remain mixed (write+read) — explicit, per capability

| Capability | Recommendation | Reasoning |
|---|---|---|
| Financials — Finance snapshot / EVM / cost breakdown | **Split**: extract a `Reader` + `ReadModel` for `get_finance_snapshot` (first pilot); leave `CostService`'s CRUD mixed as-is | This is the one area with confirmed, severe, measured-by-call-count redundancy; the rest of the module has no comparably strong evidence |
| Financials — Budget/RateCards/PlannedCosts lifecycle | **Stay mixed** | These are already lean, well-tested, correctly-transactional write paths with only mild "fat repository" report methods (`has_open_for_project`, `list_effective_lines`) — not worth splitting until/unless their read side grows a comparable redundancy problem |
| Dashboard | **Defer** | The 6-service fan-out and double-baseline-fetch are real (§7), but Dashboard is a *consumer* of other capabilities' data, not itself an aggregate boundary — fixing the underlying `FinanceService`/`BaselineService` readers (pilot + follow-on phases) will improve Dashboard's cost transitively; a dedicated Dashboard `Reader` is premature until those exist |
| Portfolio | **Defer Portfolio CQRS, but complete the confirmed safety corrections in Phase 0A before the Finance CQRS pilot.** Do not introduce a Portfolio Reader, Portfolio QueryService, or Portfolio ReadModel yet. Independently: (1) add permission enforcement to the cross-project resource-capacity report exposed through `PortfolioResourcePoolService`; and (2) add explicit rollback handling to all Portfolio command/write methods. These are existing security and transaction-integrity defects, not CQRS improvements. After those corrections, retain the existing mixed Portfolio service structure until Phase 3C measures and justifies a dedicated read projection. | These two corrections (§14 P0, §18 Phase 0A.1/0A.2) are mandatory and scheduled *now*, independent of whether Portfolio CQRS ever happens; Portfolio's CQRS-relevant read evidence (the N+1-across-accessible-projects pattern, §14 P1, this section's row above) is real but not yet measured to the standard the Finance Snapshot pilot required (§7's canonical call table) — see Phase 3C |
| Projects/Tasks/Resources/Register CRUD | **Stay mixed** | No comparable read-side redundancy evidence found; the existing `*QueryMixin` split is already adequate |
| Scheduling/Baselines | **Stay mixed on the write side**; the CPM engines are pure in-memory computation, not a database-read problem — nothing here is a SQL-projection candidate |

**Portfolio has two separate workstreams, not one — this distinction is load-bearing and must not
be collapsed:**

```text
Portfolio safety corrections
→ immediate Phase 0A work (§18 Phase 0A.1, 0A.2)

Portfolio CQRS/read optimization
→ deferred until Phase 3C, and only if measurement justifies it (§18 Phase 3C)
```

**Service ownership, clarified.** `PortfolioResourcePoolService` (§3a:
`application/resources/portfolio_resource_pool_service.py`) physically belongs under the
**Resources** application capability, not under `application/portfolio/` — it supplies a
Portfolio-facing cross-project capacity report, but its code lives with Resources. This matters for
where the fix goes: the missing permission check belongs **inside this application service
itself**, not in the desktop API and not in a Reader that doesn't exist yet. Repository/RLS scoping
remains defense in depth underneath it, exactly as everywhere else in this module (§11) — it does
not substitute for the missing application-layer check. The desktop adapter (`api/desktop/
portfolio/builders/capacity_pool_builder.py::build_capacity_pool`, per the Desktop Adapter
Responsibility Audit above) must not perform the permission check itself; it simply calls the
service and serializes whatever it returns, unchanged.

**Approved flow for the fix** (no desktop-API signature or DTO change):

```text
Portfolio desktop capacity request
  → PortfolioResourcePoolService
      → require the approved portfolio/resource-capacity permission
      → require active tenant and organization context
      → execute the existing report logic (unchanged)
  → return the existing application result (unchanged type)
  → existing desktop builder/DTO (unchanged)
```

---

## 16. Proposed target repository structure

Only the `financials/` capability gets new folders in this proposal, because it is the only area
§15 recommends splitting now. The structure below is written so that **any other capability could
adopt the identical shape later**, without inventing new conventions. **Corrected from the first
draft**: the facts dataclass now lives *with* its `Protocol`, under `contracts/reads/`, not under
`application/` — the first draft's placement created a real circular dependency
(`application → contracts` for the service to consume the protocol, `contracts → application` for
the protocol to return the application-layer type). The dependency direction is now strictly
one-way: `application → contracts`, `infrastructure → contracts`, `contracts → domain`/`platform`
value objects only, never `contracts → application`.

```text
src/core/modules/project_management/
├── application/
│   └── financials/
│       └── services/
│           └── finance_service.py        # UNCHANGED signature; internals call the new reader (facts) + LaborCostEngine (once) + CostPolicyEngine.compose_from_facts (once) instead of the current 5x/3x/6x-redundant chain
├── contracts/
│   └── reads/                             # NEW — sibling to the existing repositories/ folder, not nested under it
│       └── financials/
│           ├── finance_snapshot_reader.py # FinanceSnapshotReader(Protocol) — mirrors rate_resolution.py's shape exactly; imports ONLY the models below + domain/platform value objects
│           └── models/
│               └── finance_snapshot_facts.py   # FinanceSnapshotFacts — the immutable, frozen dataclass the reader returns; lives beside its Protocol, not under application/
├── domain/                                 # UNCHANGED — no new domain types needed
├── infrastructure/
│   └── persistence/
│       └── reads/                          # NEW — sibling to orm/, mappers/, repositories/
│           └── financials/
│               ├── statements/
│               │   └── finance_snapshot_statements.py   # the actual select(...)/func.sum(...)/group_by(...) SQLAlchemy Core statements
│               └── sqlalchemy_finance_snapshot_reader.py  # SqlAlchemyFinanceSnapshotReader — implements the Protocol; mirrors rate_resolution_reader.py exactly
└── api/
    └── desktop/
        └── financials/
            ├── serializers/snapshot_serializer.py   # UNCHANGED — still takes the existing FinanceSnapshot; the facts/reader split is entirely internal to FinanceService
            └── api.py                                 # UNCHANGED — get_finance_snapshot's signature and return type (FinancialSnapshotDto) do not change
```

**Per-folder responsibility, dependencies, and phase applicability:**

| Folder | Responsibility | Allowed dependencies | Forbidden dependencies | Files that would move/be replaced | Required for pilot? |
|---|---|---|---|---|---|
| `contracts/reads/financials/` | `Protocol` defining the reader's public shape | domain/platform value objects (`Money`, `CurrencyCode`), the sibling `models/` facts dataclasses | **`application/**` (this is the fix — the first draft allowed this and created a cycle)**, SQLAlchemy, ORM, desktop DTOs | None yet exist | **Yes** |
| `contracts/reads/financials/models/` | Immutable, database-derived **facts** returned by the reader — deliberately *not* the finished policy-applied snapshot | stdlib, `decimal`, domain/platform value objects | SQLAlchemy, ORM, **`application/**`**, desktop DTOs | None yet exist — net-new | **Yes** |
| `infrastructure/persistence/reads/financials/statements/` | Raw SQLAlchemy Core `select`/`func.sum`/`group_by` statement builders | SQLAlchemy, ORM models | domain entities as return types (statements return rows; the reader converts them), desktop DTOs | None | **Yes** |
| `infrastructure/persistence/reads/financials/sqlalchemy_finance_snapshot_reader.py` | Concrete adapter implementing the `Protocol`, executes statements, maps rows to `FinanceSnapshotFacts` | SQLAlchemy, ORM, the statements module, `contracts/reads/financials/models/` | domain entities, `application/**`, desktop DTOs | Replaces the Python-side data-fetching portion of `CostPolicyEngine.build_snapshot`/`get_cost_source_breakdown`'s repeated `cost_repo.list_by_project()`/`project_resource_repo.list_by_project()` calls specifically — nothing else | **Yes** |
| `application/financials/services/finance_service.py` | Orchestration and redaction only — permission checks, tenant/org resolution, and applying `finance.read_sensitive` redaction to the composed result. **Does not own currency normalization, completeness composition, or manual/computed-labor reconciliation — those stay with `CostPolicyEngine` (§15b's fixed ownership rule)** | `contracts/reads/financials/` (via the `Protocol`), `LaborCostEngine`, `CostPolicyEngine.compose_from_facts(...)`, everything it already depends on | — | Internals only — public signature (`get_finance_snapshot(project_id, *, as_of=None, period="month") -> FinanceSnapshot`, verified against the current source at `finance_service.py:118-124`) does not change | **Yes**, minimally |
| `application/financials/costs/cost_policy_engine.py` | **Policy owner, unchanged responsibility.** Gains one new method, `compose_from_facts(facts, labor_details, ...)`, sourced from the reader's facts and `LaborCostEngine`'s result instead of re-fetching raw lists itself. Keeps manual/computed-labor source reconciliation and planned-cost policy exactly as today | `contracts/reads/financials/` (via the `Protocol` result type), `LaborCostEngine`'s result type, everything it already depends on | SQLAlchemy, ORM (unchanged — it already didn't depend on these directly) | Internals only — its existing public methods keep their existing behavior; `compose_from_facts` is additive | **Yes**, minimally |
| `api/desktop/financials/**` | **Unchanged** | — | — | Nothing moves | Source modification: **not required**. Desktop-API **boundary verification and a desktop-API test remain required** (§17) — this is a DB-to-desktop-API pilot, not a DB-to-application-layer one, even though no source file under this folder needs to change |

---

## 17. Recommended first CQRS pilot

### Candidate scoring

| Candidate | Current complexity | Performance pain (evidenced) | SQL projection benefit | DTO stability | Migration risk | Recommendation |
|---|---|---|---|---|---|---|
| Project list | Low | None found | Low (already one query) | High | Low | Not worth the ceremony |
| Project details | Low-Medium | None found beyond the general no-pagination pattern | Low | High | Low | Not worth the ceremony yet |
| Project dashboard | High | Real (double baseline fetch, 6-service fan-out) but the pain is *cross-service orchestration*, not one aggregate's SQL | Low-Medium — most of the cost is calling 6 other services, which a projection can't fix | Medium (broad, many nested DTOs) | High (touches 6 capabilities' data) | Defer — fix by first improving the services it depends on |
| Portfolio dashboard/heatmap | Medium | Real (per-project N+1 into `ReportingService`) | Medium | Medium | Medium | Good **second** pilot once the pattern is proven once |
| **Finance snapshot** | High | **Highest, most precisely evidenced in this entire audit** (§7's canonical table, §14 P1) — 5× repeated `cost_repo.list_by_project`, 3× full labor sub-graph, 6× rate resolution | **High** — nearly every one of those calls is a candidate for a single `GROUP BY`/`func.sum` projection | High — `FinancialSnapshotDto` is a stable, well-tested existing type (§13 confirms both service-unit and desktop-API test coverage exist for the financials area, even if thin at the desktop layer) | Low-Medium — one method, one desktop DTO, existing tests to prove parity against | **Recommended first pilot** |

### Why Finance Snapshot, specifically

1. It has the **only** concretely quantified, call-count-verified redundancy in the whole module —
   not a suspicion, a traced fact (§7).
2. The codebase **already has a working precedent for exactly this pattern**
   (`RateResolutionReader`) — this pilot is "do it again, for a second capability," not "invent the
   pattern," which is the lowest-risk way to prove it generalizes.
3. `FinancialSnapshotDto` is a stable desktop type with existing test coverage
   (`test_project_management_desktop_api_financials.py`,
   `test_financial_desktop_forecast_delegation.py`) — a parity test is straightforward to write
   because the "old" behavior is already pinned by tests.
4. It does **not** touch governed/approval-gated writes, optimistic concurrency, or the Portfolio/
   Collaboration rollback gap — the pilot stays cleanly on the read side, with no write-side risk.

**Phase 1 benefits only `FinanceService.get_finance_snapshot` and its desktop-API consumer.** No
`ReportingService`, EVM-series, or export performance benefit is claimed until a later phase
explicitly migrates and tests that path (§18 Phase 3A/3B) — an earlier draft of this list claimed a
"for free" benefit to `ReportingService` here; that claim is withdrawn per §15b's corrected
ownership rule, which keeps `ReportingService` untouched and unverified by Phase 1.

### Pilot scope (explicit)

**Includes:**
- `FinanceSnapshotReader` (`Protocol`, `contracts/reads/financials/finance_snapshot_reader.py`) —
  returns **facts**, not a finished snapshot (§15b).
- `FinanceSnapshotFacts` (frozen dataclass(es), `contracts/reads/financials/models/`) — **must
  contain database facts, not prematurely interpreted final totals.** Prefer fields such as: manual
  cost-item totals by lifecycle field (planned/committed/actual/forecast, straight from stored
  `CostItem` rows); totals by cost type; totals by commitment status; totals by currency; cost-item
  row counts; and source-completeness indicators that can be determined solely from stored rows
  (e.g. "N cost rows found," "M distinct currencies present") — never a field whose name implies a
  final policy decision unless the database alone determines it. **Avoid, for example, a field
  named `planned_cost` if its authoritative value still depends on computed labor and the
  manual/computed-labor de-duplication policy** — that number belongs on `FinanceSnapshot`, produced
  by `CostPolicyEngine.compose_from_facts(...)`, never on `FinanceSnapshotFacts` itself. Documented
  explicitly: **`FinanceSnapshotFacts` ≠ `FinanceSnapshot` ≠ `FinancialSnapshotDto`** — three
  distinct types at three distinct layers, and the pilot introduces only the first; the other two
  are unchanged in shape and name.
- `SqlAlchemyFinanceSnapshotReader` — concrete adapter, one or a small number of SQL statements
  replacing the repeated `list_by_project()` + Python-sum pattern with `func.sum(...)`/`group_by(...)`
  for the purely-database-derived totals; the labor-hours×rate computation stays in
  `LaborCostEngine` (real domain math, not a SQL-projection candidate) but is called **once**
  instead of three times, orchestrated by `FinanceService` per the corrected call path in §15b.
  **SQL-aggregation-multiplication hazard (P1 implementation risk, must be designed against, not
  discovered in review):** joining cost items, project resources, assignments, and rate-card rows
  in one aggregate statement can multiply rows and silently overstate totals (a classic
  fan-out-join-then-`SUM` bug). The statement design must: aggregate independent sources
  (cost items, project resources, etc.) in **separate CTEs/subqueries**, then combine the resulting
  already-aggregated, one-row-per-project facts afterward rather than joining raw rows across
  sources before aggregating; include explicit tenant/organization/project predicates in **every**
  source CTE, not only the outer statement; use `COALESCE` only where current semantics already
  define an empty source as zero, and preserve missing/incomplete states elsewhere (a `COALESCE`
  that silently zeroes an "unresolved" state would contradict the semantic-parity requirement
  below); and avoid rate-card joins in the general cost-total query, since `LaborCostEngine` remains
  the rate-policy owner and duplicating rate precedence in SQL would violate §15b's ownership fix.
  **Required parity fixture**: multiple cost rows × multiple project resources × multiple task
  assignments on the same project, with expected totals hand-computed independently — this fixture
  exists specifically to prove no Cartesian-multiplication error occurred, and is part of the
  semantic parity matrix below (row 15).
- `FinanceService.get_finance_snapshot` internals updated per §15b's fixed ownership split: call the
  reader once for facts, call `LaborCostEngine` once for labor, call
  `CostPolicyEngine.compose_from_facts(...)` once for manual/computed-labor reconciliation and
  planned-cost policy, then compose the remaining sections and apply redaction — collapsing the
  confirmed 5×/3×/6× repeated-call counts (§7's canonical table) to 1× each.
- Composition wiring: one new line in `project_registry.py` constructing
  `SqlAlchemyFinanceSnapshotReader(session=session)` and passing it into `FinanceService`.
- **Desktop-API boundary verification is required, even though no `api/desktop/financials/**`
  source file is expected to change** — the pilot is explicitly a DB-to-desktop-API pilot (per the
  task's own framing), so a desktop-API test asserting `get_finance_snapshot`'s return value has
  **field-for-field deep structural and value equality** with today's output (not "byte-for-byte" —
  this is an in-process Python seam with no network serialization byte stream, so that phrase is
  imprecise and is corrected here and everywhere else it appeared) is part of the pilot's own proof,
  not an optional nicety.
- A required **runtime-composition test** (detailed in the "Composition weaknesses" note after
  §14): construct `RepositoryBundle` → `ProjectManagementServiceBundle` → `DesktopApiRegistry` →
  call `FinancialsDesktopApi.get_finance_snapshot` → assert the call actually reaches the real
  `SqlAlchemyFinanceSnapshotReader`, not merely that it is importable.
- Tests: unit test for the reader's SQL shape (assert correct filters/joins/aggregation and the
  no-multiplication property above), an integration test against the real SQLite test database, the
  desktop-API boundary test above, an **old/new semantic parity test** (matrix below — this is the
  load-bearing test, not a single fixture), and the full Phase 0 measurement suite (§18) proving the
  call count actually drops.

**Semantic parity matrix (required, not a single old/new fixture).** The assertion that matters is
not "the new query is faster" — it is that every one of the following is **identical** to today's
output across every fixture state below: planned, committed, actual, and forecast values; computed
labor values; currency; completeness flags; unresolved-rate diagnostics; source exclusions; source
breakdowns; the ledger/control totals included in the snapshot; sensitive and redacted output;
tenant/organization isolation; and the final desktop `FinancialSnapshotDto` values.

| # | Fixture state |
|---|---|
| 1 | No cost rows at all |
| 2 | Manual planned cost only |
| 3 | Computed labor only |
| 4 | Manual and computed labor present together (de-duplication policy exercised) |
| 5 | Unallocated `ProjectResource.planned_hours` (no task assignment) |
| 6 | An unresolved labor rate (fail-closed/exclusion path) |
| 7 | Multiple cost types in the same project |
| 8 | Multiple commitment statuses in the same project |
| 9 | An inactive resource or inactive project-resource |
| 10 | Same project ID reused under a different tenant (cross-tenant isolation) |
| 11 | Same tenant, different organization |
| 12 | Multiple currencies, including an incomplete-currency state |
| 13 | Zero-hour and zero-amount rows |
| 14 | An `as_of` date exactly on a rate-card effective-date boundary |
| 15 | Multiple cost rows × multiple project resources × multiple task assignments on the same project, with hand-computed expected totals — proves no SQL aggregation-multiplication error (§17's SQL-hazard note above) |
| 16 | Caller holds `finance.read_sensitive` — full, unredacted `by_resource` detail expected |
| 17 | Caller does **not** hold `finance.read_sensitive` — redacted/aggregated output expected, matching today's `_redact_sensitive_labor_rows` behavior exactly |
| 18 | Empty resources/assignments, but existing manual cost rows present (proves manual-only totals aren't accidentally dropped when the labor side is empty) |
| 19 | A large, realistic-scale fixture (not just small hand-built cases) — this is also where the query-count/timing measurement from Phase 0 is re-run against the new path for comparison |
| 20 | Project not found |
| 21 | Missing tenant context |
| 22 | Missing organization context |

**Excludes** (explicitly, per the task's own constraint and this audit's risk findings):
- Any QML change — `FinancialSnapshotDto`'s shape and the desktop API's method signature are the
  pilot's stability contract; if they don't change, QML needs no change, and this pilot proves that
  claim rather than assuming it.
- Any write-side restructuring — `CostService`, `BudgetService`, etc. are untouched.
- Any mass folder move — only `financials/` gains new (additive) folders; nothing existing is
  deleted or relocated in this phase.
- Event sourcing, a separate read database — not used.
- Fixing the `report.view`/`finance.read_sensitive` permission split (§14 P0) — that is a
  deliberate, separately-scoped decision (§20), not a side effect of this pilot. The pilot's reader
  returns the *complete*, unredacted facts; `FinanceService` keeps doing redaction exactly as it
  does today.
- `ForecastCostService`'s independent BAC/AC computation — the disagreement-with-`CostPolicyEngine`
  risk (§14 P1) is noted but not resolved by this pilot; resolving it is a product decision (§20).
- **The final desktop-DTO Decimal cutover.** `FinancialSnapshotDto`'s money fields stay `float` for
  this pilot, unchanged, to preserve the QML-unchanged guarantee above — the pilot's internal facts
  and application result may be Decimal-safe, but the desktop DTO is deliberately not migrated in
  Phase 1 (see §18 Phase 5, §19 guardrail 7).
- **Any repointing of planned-cost semantics.** This pilot does **not** repoint `CostPolicyEngine`,
  `LaborCostEngine`, the finance snapshot's "planned" figures, or any KPI/ledger onto
  `ProjectPlannedCostVersion`. `ProjectResource.planned_hours` remains the authoritative
  envelope-level planning total, including its unallocated-hours semantics, exactly as already
  decided and documented in this project's finance-modernization history (the CostPolicyEngine
  cutover onto `ProjectPlannedCostVersion` was investigated separately and explicitly rejected as a
  regression). The reader may change **how** existing totals are obtained; it must never change
  **what "planned" means**.

### 17a. Pagination decision for CQRS readers

Pagination is part of an individual read contract; CQRS does not add it automatically. The Phase 1
Finance Snapshot is a bounded aggregate/control view and therefore remains **unpaged**. Paging its
totals would make budget, exposure, source reconciliation, and completeness depend on the selected
page and would be financially incorrect.

Growing row collections introduced by later readers must make an explicit pagination choice:

- use stable keyset/cursor pagination for large or frequently changing operational collections;
- allow offset pagination only for demonstrably small, stable administration lists;
- apply tenant/organization scope, filters, and deterministic ordering before the page boundary;
- use a unique tie-breaker in every ordering contract so rows cannot be skipped or duplicated;
- stream or batch exports independently instead of bypassing the interactive page contract; and
- if the Finance ledger becomes too large for the snapshot contract, introduce a separately
  permissioned `FinanceLedgerReader` with its own page request/result rather than paging
  `FinanceSnapshotFacts` or returning partial control totals.

The existing `application/common/pagination.py` types remain the module convention where their
cursor/offset shapes fit. Phase 1 does not retrofit pagination into unrelated repository methods;
those unbounded-list findings remain scheduled capability by capability after the pilot.

---

## 18. Incremental migration plan

**Phase 0 — Audit and measurements (this document + one follow-up step).** Scope: this document,
plus adding real instrumentation to the *existing* `get_finance_snapshot` call path **before** any
reader exists, to capture a real, measured "before" baseline (this audit deliberately did not
fabricate a timing/count number — see §20). Files affected: none in production code (test-only
instrumentation, temporary).

**Measurements required** (query count alone is not sufficient — a smaller query count with one
pathological aggregate query is not automatically an improvement):

- SQL statement count, and SQL statements grouped by repository/source (so a regression in one
  source doesn't hide behind an aggregate improvement elsewhere).
- Database execution time (not just Python wall-clock time).
- Number of rows returned across all statements.
- Number of ORM/domain objects constructed (a proxy for mapper overhead, measurable via a counted
  mapper hook or object-creation instrumentation).
- Mapper invocation count where practically measurable.
- Repeated repository calls, repeated `rate_resolver.resolve_many` calls, and repeated
  `LaborCostEngine` calls specifically (these are the exact redundancies §7's canonical table
  documents — Phase 0 must confirm the *measured* counts match that table before trusting it as the
  baseline).
- Python aggregation/calculation time, isolated from database time.
- Total `FinanceService.get_finance_snapshot` time and total desktop-API-call time.
- Memory allocation or peak object count, where practical to capture without disproportionate
  instrumentation effort.

**Measure at multiple fixture sizes** — a small project, a medium realistic project, and a large
stress fixture — since a fixed query-count budget derived from only one size risks being either too
loose (small fixtures) or unachievable (large fixtures) at the other end.

**Whether RLS/session-initialization SQL is included in or excluded from the endpoint query budget
must be decided explicitly during Phase 0**, not left ambiguous — those statements run on every
transaction regardless of `get_finance_snapshot`'s own logic, and conflating them with the
endpoint's own query count would make the "before" and "after" numbers incomparable if the RLS
statement count itself ever changes for unrelated reasons.

Exit gate: a documented, measured baseline across every dimension above, at all three fixture
sizes. **The accepted post-pilot query-count budget (§19 guardrail 11, §20 open question 4) must
come from these results, not from this document's illustrative "≤ 6" estimate.**

**Exit gate met — measured baseline, run 2026-08-06.** Instrumentation added at
`src/tests/project_management/test_finance_snapshot_phase0_measurement.py` (test-only; wraps
`FinanceService`'s own repository/engine attributes for the duration of one call, then restores
them; adds a `before_cursor_execute`/`after_cursor_execute` SQL listener on the test engine; no
production file was touched). Run against the real composition graph (`build_service_dict`, the
same path production uses) on the project's SQLite test database, at three fixture sizes:

| Dimension | small (1 resource, 2 tasks, 2 cost items) | medium (10, 15, 30) | large (50, 60, 150) |
|---|---:|---:|---:|
| Wall-clock time | 48.4 ms | 77.5 ms | 221.4 ms |
| DB execution time (sum of per-statement durations) | 1.9 ms | 3.1 ms | 7.9 ms |
| Python time (wall − DB) | 46.4 ms | 74.5 ms | 213.5 ms |
| Total SQL statements | 164 | 272 | 752 |
| `cost_repo.list_by_project` calls | 5 | 5 | 5 |
| `project_resource_repo.list_by_project` calls | 3 | 3 | 3 |
| `task_repo.list_by_project` calls | 4 | 4 | 4 |
| `project_repo.get` calls | 6 | 6 | 6 |
| `rate_resolver.resolve_many` calls | 6 | 6 | 6 |
| `LaborCostEngine.calculate_project_labor_details` executions | 3 | 3 | 3 |
| `cost_repo.list_by_project` total rows returned (across its 5 calls) | 10 | 150 | 750 |
| `snapshot.ledger` rows in the final result | 8 | 110 | 550 |

**Every named-call count matches §7's canonical table exactly, at every fixture size** — the
redundancy is a fixed, size-independent tax (5/3/4/6/6/3 calls no matter how large the project is),
confirming the P1 finding in §14 is real and not an artifact of one particular fixture shape. The
one correction this run produced is already folded into §7's table: `project_repo.get` measures 6,
not the 5 an earlier draft claimed (it was missing `get_finance_snapshot`'s own direct call).

**A second, larger finding this measurement surfaced that the static call-count table alone did
not show:** grouping the 164 (small)/272 (medium)/752 (large) statements by table reveals that
**`organizations`+`tenants` scope-lookup queries are the largest single category — 87 of 164
statements (53%) on the small fixture, 159/272 (58%) on medium, 479/752 (64%) on large** — far
outweighing the finance-domain tables the canonical table already tracks (`cost_items`,
`project_resources`, `task_assignments`, `project_finance_rate_card*`, all flat at 3-6 statements
regardless of fixture size). This scales with fixture size (unlike the flat finance-domain counts),
tracking roughly with the resource count, which is consistent with each `resource_repo.get(...)`
call inside `LaborCostEngine` (§7's 3×N term) independently re-resolving tenant/organization scope
rather than reusing one already-resolved context. **This is not yet a confirmed root cause** — it
would require tracing `TenantContextService`/the repository tenant-scoping helper's exact call
pattern to confirm, which this measurement pass did not do — but it is a real, measured signal that
the Reader consolidation's benefit may be substantially larger than the 5×/3×/6× domain-call
reduction alone suggests, since collapsing those calls could also collapse a proportional share of
this tenant/org lookup volume. Recorded here as a finding for Phase 1 to watch for in its own
post-migration measurement, not as a claim this document verifies further.

RLS/session-initialization SQL question, decided: this measurement ran against the SQLite test
engine (`src/tests/conftest.py`'s `session` fixture), which has no PostgreSQL RLS session-variable
setup at all — so the question of whether to include RLS statements in the budget did not arise
here and remains open for whoever re-runs this measurement against a PostgreSQL-backed environment
before setting the final production budget.

**Phase 0A — Independent safety corrections (mandatory, not optional).** Inserted here, between
measurement and the pilot itself, because several confirmed P0/P1 findings in §14 and §11 are
correctness/security/reliability fixes that have nothing to do with CQRS and must not wait for or
be entangled with the Finance Reader work. These are no longer open scheduling questions (§20's
Resolved Decisions section records this explicitly) — Phase 0A's existence *is* the decision that
they are fixed now, as independent, reviewable commits, each with its own mandatory exit gate below.

**Phase 0A.1 — Portfolio resource-report authorization.**

Scope:
- Identify the correct existing permission from the platform permission catalog
  (`role_permission_catalog.py`) for a cross-project resource-capacity report — the equivalent of
  what `PortfolioService`'s own methods already gate behind `portfolio.read`/`portfolio.manage`
  (§4c's runtime object table; §11).
- Enforce it **inside** `PortfolioResourcePoolService.get_pool_report` and
  `PortfolioResourcePoolService.get_resource_demand_by_project` themselves — this application
  service physically lives under `application/resources/` (§15c's service-ownership note above),
  but the fix belongs in this service, not in `PortfolioService`, and not in the desktop layer.
- Require active tenant and organization context inside the same service methods, matching the
  pattern every sibling financial/portfolio service already uses (§11).
- Preserve repository and RLS scoping exactly as it exists today — this fix adds the missing
  application-layer check *in addition to*, not instead of, the existing defense-in-depth database
  scoping.
- **Do not** add authorization to a Reader (none exists for Portfolio, and none is introduced by
  this phase) or to the desktop API (`api/desktop/portfolio/builders/capacity_pool_builder.py`,
  per the Desktop Adapter Responsibility Audit above, must remain a pure pass-through).

Required tests:
- An authorized caller receives the existing report, unchanged.
- A caller without the permission receives the same established typed permission error every other
  gated service raises (`BusinessRuleError(code="PERMISSION_DENIED")`, per §11) — not an empty
  result.
- Missing tenant context fails closed.
- Missing organization context fails closed.
- Another tenant's data is never returned to an authorized-but-wrong-tenant caller.
- Another organization's data is never returned to an authorized-but-wrong-organization caller.
- The desktop DTO (`PortfolioCapacityResourceDto[]`) remains field-for-field unchanged for an
  authorized caller — this is a permission fix, not a contract change.

**Exit gate:** No Portfolio-facing capacity report can execute without explicit application-layer
permission and tenant/organization validation.

**Phase 0A.1 — COMPLETE (2026-08-06).** Implemented and verified exactly as scoped above:
- `PortfolioResourcePoolService.get_pool_report` and `.get_resource_demand_by_project`
  (`application/resources/portfolio_resource_pool_service.py`) now both call a new `_require_scope`
  helper that enforces `require_permission(self._user_session, "portfolio.read", ...)` followed by
  `TenantContextService.require_organization_context(...)` — the same permission and the same
  "require both tenant and organization" pattern used by `PortfolioService`/`portfolio_executive.py`
  elsewhere in this module. `get_resource_demand_by_project` previously had **no check at all**;
  `get_pool_report` previously only called a weaker `_active_organization_id` helper.
- **Significant correction to this finding's original risk framing, discovered during
  implementation, not anticipated by the P0 finding above:** a repo-wide grep for
  `PortfolioResourcePoolService(` returned zero matches before this phase — the service was never
  constructed anywhere in production composition. `capacity_pool_builder.py`'s
  `if pool_service is None: return ()` and `service_resolver.py`'s
  `services.get("portfolio_resource_pool_service")` (always `None`) confirm the Portfolio
  "Capacity vs Demand" desktop feature has been **silently non-functional (always empty) in
  production**, not merely under-protected. Composition wiring was completed as part of this phase
  (construction in `project_registry.py`'s `build_project_management_service_bundle`; the field,
  `as_dict()` key, and constructor argument added to `app_container.py`'s `ServiceGraph`) — without
  it, the permission fix would have protected a code path nothing could ever reach, per this
  document's own "Composition root: must own constructing services" rule (§16).
- Verified with 7 new tests
  (`src/tests/project_management/test_portfolio_resource_pool_phase0a1_authorization.py`), matching
  the required-tests list above one-for-one: authorized caller receives the report; caller without
  `portfolio.read` gets `BusinessRuleError(code="PERMISSION_DENIED")` on both methods; missing
  tenant context fails closed (`TENANT_CONTEXT_REQUIRED`); missing organization context (tenant
  present) fails closed (`TENANT_CONTEXT_REQUIRED`); another tenant's resource is never returned;
  another organization's resource (same tenant) is never returned; the desktop DTO
  (`PortfolioCapacityResourceDto[]`) is field-for-field unchanged for an authorized caller, exercised
  against the real composition graph via the now-populated `services["portfolio_resource_pool_service"]`
  key. All 7 pass. A targeted regression run of the pre-existing Portfolio desktop-API test files
  (`test_project_management_desktop_api_portfolio_*.py`, `test_qml_project_management_presenters_portfolio.py`)
  also passed unchanged, confirming the composition wiring did not disturb the existing Portfolio
  surface. A full `src/tests/project_management/` run surfaced 24 pre-existing failures in unrelated
  files (e.g. `test_data_integrity.py`'s `tasks.wbs_code` NOT NULL constraint, dashboard-trends
  activity-feed fakes, PM module-enablement checks) — confirmed unrelated by reproducing them in
  isolation with tracebacks that never touch Portfolio or this phase's changed files; consistent with
  this branch's other, already-uncommitted in-progress work (WBS/budget migrations). Per this
  project's established "verify once per phase" convention, these were not investigated further or
  fixed as part of Phase 0A.1.

**Phase 0A.2 — Portfolio write rollback hardening.**

Scope:
- Inspect every Portfolio command/write method (§14's "Desktop Adapter Boundary Weaknesses"
  consolidation and the original `portfolio/services/portfolio_service.py` finding both confirm
  every one of these currently commits with no `try/except` at all).
- Wrap each method's complete mutation transaction with this module's own established pattern,
  identical in shape to every other governed service audited in §6 (e.g. `RegisterService`,
  `CostService`):
  ```python
  try:
      # validate
      # mutate
      # repository writes
      session.commit()
  except Exception:
      session.rollback()
      raise
  ```
- Preserve existing typed `IntegrityError`/`ConcurrencyError`/`ValidationError`/`BusinessRuleError`
  translations exactly as they already exist elsewhere in the module — this phase adds the missing
  `try/except/rollback` wrapper, it does not invent new error types.
- Emit `record_activity`/`domain_events.portfolio_changed.emit` only after a successful commit —
  matching the ordering every other capability already uses (§10, §12).
- **Do not** change any Portfolio query/read method — this phase is write-path-only.
- **Do not** introduce a Unit of Work in this correction — it reuses the existing shared session
  exactly as every other write path does (§10).
- **Do not** introduce `CommandService` classes.
- **Do not** restructure the Portfolio capability beyond adding the missing rollback wrapper to
  each existing write method.

Required failure-injection tests:
- A forced repository add/update failure triggers rollback (no partial write survives).
- A forced commit failure triggers rollback.
- No partial Portfolio row remains in the database after either failure.
- No `portfolio_changed`/activity success event is emitted after either failure.
- **The shared `Session` remains usable by the next operation after the rollback** — this is the
  one test dimension unique to this module's single-long-lived-session model (§10): a rollback must
  leave the session in a state where an unrelated subsequent write in the same process still
  succeeds, not merely that this write's own data didn't persist.
- Successful behavior and existing DTO output remain unchanged for the non-failure path.

**Exit gate:** Every Portfolio write either commits completely or rolls back completely, and the
shared `Session` remains usable after a failed write.

**Phase 0A.2 — COMPLETE (2026-08-06).** Implemented and verified exactly as scoped above:
- All 6 Portfolio command methods (`create_project_dependency`, `remove_project_dependency`
  in `portfolio_dependencies.py`; `create_intake_item`, `update_intake_item` in
  `portfolio_intake.py`; `create_scenario`, `update_scenario` in `portfolio_scenarios.py`;
  `create_scoring_template`, `activate_scoring_template` in `portfolio_templates.py` — 8 methods
  across 4 command-mixin files) now wrap their repository add/update/delete call plus
  `self._session.commit()` in `try: ... except Exception: self._session.rollback(); raise`,
  matching this module's own established `CostService`/`_apply_cost_add_decision` shape exactly.
  `record_activity`/`domain_events.portfolio_changed.emit` calls were left exactly where they
  already were (after the commit, outside the try) — no restructuring beyond the missing wrapper,
  per scope.
- `_ensure_scoring_templates`/`_deactivate_other_templates` (`portfolio/utils/portfolio_support.py`)
  were deliberately left unwrapped — they are internal support helpers, not among the command
  methods §14's consolidation named, and the plan's own "do not restructure beyond adding the
  missing rollback wrapper to each existing write method" instruction excludes them. Their pending
  writes are still covered transactionally: since they never call `session.commit()` themselves
  (only the lazy-bootstrap path inside `_ensure_scoring_templates` does, as its own separate,
  already-atomic unit), any rollback triggered by the calling command method's new wrapper still
  reverts their pending changes along with it — confirmed by
  `test_update_scoring_template_rolls_back_on_repository_failure`, which forces the failure on the
  *second* of two pending writes in one transaction and asserts the *first* (an unrelated template's
  deactivation, done via `_deactivate_other_templates`) is rolled back too.
- Verified with 33 new tests
  (`src/tests/project_management/test_portfolio_phase0a2_rollback_hardening.py`), covering the
  required-tests list above for every one of the 8 methods: forced repository failure and forced
  commit failure each trigger rollback with no partial row surviving; no `portfolio_changed` event
  fires after either failure; the shared `Session` remains usable for a subsequent write after each
  failure (tested against the real production session via the `services` fixture, not a fake); and
  the non-failure path's behavior, return value, and emitted event are unchanged. All 33 pass. A
  targeted regression run of the pre-existing Portfolio desktop-API and tenant-isolation test files
  (`test_project_management_desktop_api_portfolio_*.py`, `test_qml_project_management_presenters_
  portfolio.py`, `test_portfolio_domain_validation.py`, `test_tenant_isolation_services_pm.py`,
  plus this phase's own Phase 0A.1 test file) also passed unchanged.

**Phase 0A.3 — Collaboration rollback hardening.** Kept as its own separate commit and test set,
deliberately not merged with Phase 0A.2 merely because both capabilities share the same defect —
Portfolio and Collaboration have different write methods, different call sites, and different
domain events (`portfolio_changed` vs. `collaboration_changed`), so combining them into one "shared
defect" refactor would obscure exactly which capability's tests cover which fix. Scope, required
tests, and exit gate mirror Phase 0A.2 exactly, applied to `collaboration/services/
collaboration_service.py`'s write methods and `collaboration_changed` instead.

**Phase 0A.3 — COMPLETE (2026-08-06).** Implemented and verified exactly as scoped above:
- All 8 Collaboration command methods (`post_comment`, `mark_task_mentions_read`, `edit_comment`,
  `delete_comment`, `react_to_comment`, `remove_reaction` in `collaboration_comments.py`;
  `touch_task_presence`, `clear_task_presence` in `collaboration_presence.py`) now wrap their
  repository write(s) plus `self._session.commit()` in
  `try: ... except Exception: self._session.rollback(); raise`, matching Phase 0A.2's shape.
  `record_activity`/`domain_events.collaboration_changed.emit` calls were left exactly where they
  already were (after the commit, outside the try).
- `post_comment` has a conditional completion step (when an attachment-carrying comment is
  registered with `DocumentIntegrationService`, that external service — not
  `self._session.commit()` — is called instead); the try block was scoped to cover
  `self._comment_repo.add(comment)` through *both* branches of that conditional, so a failure in
  either branch still rolls back the comment insert. `_link_existing_comment_documents` (a call
  into the same external `document_integration_service`) was left outside the try, matching Phase
  0A.2's precedent of not reaching into a different service's own transaction management.
- `mark_task_mentions_read` mutates in a loop (one `comment_repo.update` per matching comment)
  before its single trailing commit; the try block was widened to cover the whole loop, not just
  the final commit, so a failure partway through a multi-comment batch rolls back every comment in
  that batch, not only the one that failed — this is a genuine completion of "add the missing
  wrapper" for this method's actual mutation region, not a restructuring.
- Verified with 16 new tests
  (`src/tests/project_management/test_collaboration_phase0a3_rollback_hardening.py`): the full
  required-tests matrix against `post_comment` (repository failure and commit failure each roll
  back with no partial comment row; no `collaboration_changed` event after either failure; the
  shared `Session` stays usable for a subsequent post afterward; the non-failure path is
  unaffected), plus a forced-repository-failure rollback test for each of the other 7 methods
  (`mark_task_mentions_read` also gets a commit-failure + session-reusability test, exercising the
  widened loop wrapper). All 16 pass. A targeted regression run of the pre-existing Collaboration
  test files (`test_task_comment_domain_validation.py`, `test_task_presence_domain_validation.py`,
  `test_project_management_desktop_api_workspace_collaboration.py`,
  `test_qml_project_management_presenters_collaboration.py`) passed unchanged. A wider regression
  run including `test_repository_tenant_hardening_secondary_writes.py`/`secondary_reads.py`
  reproduced 4 pre-existing failures, all the same `tasks.wbs_code` NOT NULL constraint error
  already documented as unrelated during Phase 0A.1's regression check (caused by other,
  already-uncommitted WBS/budget-migration work on this branch) — confirmed unrelated again by
  traceback inspection, not investigated further per this engagement's "verify once per phase"
  convention.

**Phase 0A.4 — Other independent safety corrections.** The remaining items from this phase's
original scope, unchanged in substance, renumbered for clarity now that Portfolio/Collaboration
rollback have their own dedicated sub-phases:
- Stop broad exception handling from converting authorization/tenant-context/infrastructure
  failures into empty data — the recurring pattern across `access_resolution_service.py`,
  `resource_lookup_service.py`, `list_project_requisitions`, and others ("Desktop Adapter Boundary
  Weaknesses" above).
- Record, and separately plan (not fix inside this step), the `TaskAssignmentBridgeMixin.
  assign_resource` dual-commit correction (§14 P0, §6).
- Decide whether the following additional confirmed security gaps (§11) require immediate patches,
  and if so, patch them as their own commits: `ForecastCostService`'s missing explicit tenant
  context; `CostService`'s optional/unused tenant context; Portfolio dependency creation lacking
  project-scope authorization; `TaskService.get_dependency_diagnostics` lacking a self-contained
  permission check; the direct `get_authorization_engine()` bypasses in
  `TaskAssignmentMixin.get_assignment_action_context` and its Collaboration equivalent.

**Do not bundle any Phase 0A fix into the Finance Reader commit** unless the exact same code path
must genuinely be touched by both — none currently do. The `report.view` vs. `finance.read`/
`finance.read_sensitive` permission-model decision (§14 P0, §20 open question 1) remains a separate,
explicit product/security decision — Phase 0A does not resolve it, only the items enumerated above.

**Phase 0A.4 — COMPLETE (2026-08-06).** Each of the three bundled item-groups was investigated and
resolved on its own terms, exactly as the "decide whether..." framing above invited:

*Broad exception handling.* Two genuinely distinct anti-patterns were hiding under one description:

- **Fixed (swallow-into-empty, live features):** `capacity_pool_builder.py::build_capacity_pool`,
  `tasks/api.py::list_task_reservations`, and
  `dashboard_snapshot_service.py::_list_pending_approvals` each had a bare
  `try: ... except Exception: return ()` around a real, live service call. All three were narrowed
  to nothing — the `try/except` was removed entirely so failures (including the
  `PERMISSION_DENIED` a caller without `portfolio.read` now gets from `get_pool_report`, per Phase
  0A.1) propagate to the desktop boundary instead of silently rendering as "no data". This directly
  closes the gap Phase 0A.1 left open: an unauthorized caller reaching the Portfolio capacity-pool
  builder previously saw an empty pool with no error; now sees the actual denial.
- **Deferred, recorded here (not fixed):** `access_resolution_service.py`/`resource_lookup_service.py`
  (Tasks) do not actually match this pattern — on inspection, they catch a narrow
  `BusinessRuleError` (not broad `Exception`) and, instead of swallowing it into empty data, replace
  it with a **second, hand-rolled implementation of the same permission-filtering decision**
  `ProjectService`/`ResourceService` already make (reaching into `_project_repo`/`_resource_repo`
  private attributes to do it). This is the P0 finding at §14/Appendix A verbatim, and its own
  documented correct fix — "`ProjectService` should expose the fallback/degraded-mode behavior
  itself... permission-set filtering must have exactly one implementation, not two" — is an
  application-layer redesign of `ProjectService.list_projects`/`ResourceService.list_resources`,
  not a mechanical safety patch. Attempting it inside this phase risked behavior change to a live
  authorization path without dedicated design review, so it is recorded here as a real, open P0
  finding requiring its own dedicated phase, not fixed. `financials/api.py::list_project_requisitions`
  was also left as-is: confirmed (twice, independently, elsewhere in this document) to have no QML
  consumer and already recommended for deletion (§14 P3) — narrowing its exception handling would
  be polishing dead code.

*`TaskAssignmentBridgeMixin.assign_resource` dual-commit.* Recorded, not fixed, exactly as scoped.
Confirmed by reading `application/tasks/commands/assignment_bridge.py`: when a task's resource has
no existing `ProjectResource`, the method commits once to create the `ProjectResource` (lines
56-61), then calls `self.assign_project_resource(...)`, which commits again for the actual
assignment. A failure in the second commit leaves the first's `ProjectResource` durably persisted
with no matching assignment — not a corrupted state, but a genuine two-transactions-where-one-was-
intended gap. Fixing it correctly means threading a "defer commit" flag through
`assign_project_resource` (used elsewhere as a standalone public method with its own commit
contract), which is a small Unit-of-Work-shaped design decision this mechanical safety phase should
not make unreviewed. Left as an open, planned item for a future phase.

*Five named security gaps — decided individually:*

- **Patched:** `ForecastCostService` had no `tenant_context_service` at all. Added the parameter
  (defaults to `None`, matching every sibling service's constructor shape) and a
  `_require_organization_context` helper, called from all four public methods
  (`get_commitment_summary`, `get_material_rollup`, `compute_forecast`, `check_cost_threshold`)
  after their existing `require_permission`/`require_project_permission` calls — mirroring
  `PortfolioResourcePoolService._require_scope`'s shape from Phase 0A.1. Wired
  `tenant_context_service=platform_services.tenant_context_service` into its construction in
  `project_registry.py`.
- **Patched:** `PortfolioDependencyCommandMixin.create_project_dependency` only checked global
  `portfolio.manage` plus `project.read`-scoped accessibility (via `_accessible_projects()`) — a
  caller with global `portfolio.manage` but no actual management grant on either project could link
  them. Added `require_project_permission(user_session, project_id, "portfolio.manage", ...)` for
  both the predecessor and successor project, after the existing accessibility check.
  `remove_project_dependency` was left unchanged — the finding named creation specifically, and
  removal's existing accessibility check is a materially different (lower) risk than granting a new
  cross-project link.
- **Patched:** `TaskDependencyDiagnosticsMixin.get_dependency_diagnostics` had zero permission
  checks — any caller who could reach the method got full task names and schedule-impact details
  for any two task ids, regardless of project access. Added
  `require_project_permission(user_session, project_id, "task.read", ...)` immediately after the
  same-project validation resolves `project_id`, before any dependency/schedule data is read.
- **Decided not to patch (documented, no gap found):** the two `get_authorization_engine()` direct
  calls (`TaskAssignmentMixin.get_assignment_action_context`,
  `CollaborationCommentQueryMixin.get_task_comment_action_context`) are **capability probes**, not
  enforcement bypasses — they compute boolean `can_read`/`can_manage` flags for desktop
  presentation (e.g. "should this button be enabled") and correctly need `engine.has_permission(...)`
  as a query returning a value, not `require_permission(...)`'s raise-on-deny contract. Read in
  full: neither incorrectly grants anything a `require_permission` call at the same site would have
  denied. The "bypass" framing in this finding is a code-hygiene observation (duplicated low-level
  engine access instead of a shared capability-check helper), not a security hole — no immediate
  patch needed.
- **Decided to defer (documented, real but out of scope for this pass):** `CostService` accepts
  `tenant_context_service` but never references it anywhere across its three command/query mixins.
  Unlike `ForecastCostService` (4 small, already-permission-checked methods), `CostService` is a
  much larger facade (`CostLifecycleMixin` + `CostQueryMixin` + `CostSupportMixin`) backing a live,
  heavily-used financial capability; auditing every method to add tenant-context enforcement
  correctly is a larger, higher-risk change than this mechanical safety pass should take unreviewed
  — repository-level RLS scoping still defends the data underneath in the meantime, matching this
  document's own established defense-in-depth reasoning. Left as an open item for a future,
  dedicated pass over `CostService` specifically.

Verified with 9 new tests
(`src/tests/project_management/test_phase0a4_other_safety_corrections.py`): `ForecastCostService`
succeeds for an authorized caller with context, fails closed with no `tenant_context_service`, and
fails closed with a tenant present but no organization; `create_project_dependency` succeeds for an
authorized caller and denies a caller with global `portfolio.manage` but no project-scoped grant on
either project; `get_dependency_diagnostics` succeeds for an authorized caller and denies a caller
without project-scoped `task.read`; and both `capacity_pool_builder.py` and
`_list_pending_approvals` now propagate a forced failure instead of swallowing it into `()`. All 9
pass. A full `src/tests/project_management/` regression run reproduced the exact same 24
pre-existing failures already documented during Phase 0A.1/0A.3's own regression checks (identical
test names, identical `tasks.wbs_code`/module-enablement/dashboard-fake root causes) — confirmed
unrelated again, not investigated further.

**Sequencing — one governance sequence, not two independent tracks.** Phase 0A does not expand the
scope of the Finance Snapshot pilot, and there is no *technical* dependency forcing one phase to
wait on the other's code. But this document states a single, unambiguous ordering rather than
leaving "either order or in parallel" open to interpretation: **P0 security/reliability corrections
merge before the P1 performance pilot.** This is a governance decision, not a technical constraint —
recorded explicitly so it cannot be read as permission to run Phase 1 first:

```text
Phase 0
→ measure existing Finance Snapshot

Phase 0A.1
→ Portfolio permission correction

Phase 0A.2
→ Portfolio rollback correction

Phase 0A.3
→ Collaboration rollback correction

Phase 0A.4
→ other independent safety corrections

Phase 0B
→ attribute the Phase 0 SQL-count growth to specific call sites (diagnostic only)

Phase 0C
→ replace PM repository entity hydration with validated session scope IDs
→ prove repository scoping remains fail-closed and tenant/organization query growth is removed

Phase 1
→ Finance Snapshot CQRS pilot

Phase 2
→ CQRS architecture guardrails

Phase 3C
→ measure Portfolio reads
→ introduce Portfolio Reader only when justified
```

Phase 0.1-0A.4, Phase 0B, Phase 0C, and Phase 1 remain independently reviewable, independently
revertible changes - this sequence governs merge order, not implementation scope; nothing about fixing Portfolio's permission
check or rollback handling requires touching any file the Finance Snapshot pilot touches, and
nothing about the pilot requires touching Portfolio or Collaboration. The reason for the ordering is
priority, not a dependency graph: this document's own tiers (§14) treat every Phase 0A item as P0
and the Finance Snapshot redundancy as P1, and P0 findings merge first as a matter of policy.

**Phase 0B — SQL growth attribution (diagnostic only, COMPLETE 2026-08-06).** Inserted here,
between Phase 0A and Phase 1, specifically to answer the question Phase 0's own measurement
deliberately left open: *why* did total SQL statement count grow 164 -> 272 -> 752 across the
small/medium/large fixtures, with `organizations`/`tenants` dominating 53-64% of every run? This
phase is scoped narrowly as attribution, not remediation — no production code was changed; its
only output is findings for Phase 1's Reader design to act on.

Method: extended the Phase 0 measurement harness
(`src/tests/project_management/test_finance_snapshot_phase0b_sql_growth_attribution.py`, new file,
test-only) with named-call counters on `TenantContextService.get_active_tenant`/
`.get_active_organization` and on `LaborCostEngine`'s injected `resource_repo.get`, run at the same
3 fixture sizes as Phase 0, then cross-referenced against the measured `sql_by_table` breakdown.

**Confirmed root cause: two independent, uncoordinated per-resource lookup loops, each of which
independently re-triggers a full tenant+organization context resolution with no caching.**

1. `resource_repo.get(resource_id)` is called exactly **4 times per distinct resource, every
   snapshot build** — confirmed by measurement (4, 40, 200 calls at 1/10/50 resources) and fully
   traced statically to two call sites that never share a cache with each other:
   - `LaborCostEngine.calculate_project_labor_details`'s own per-resource loop
     (`labor_cost.py:129`), invoked **3 times per snapshot**: twice via
     `CostPolicyEngine.build_snapshot()` (executed fresh, uncached, once each from
     `get_cost_source_breakdown` and `get_cost_control_totals` — the redundancy §7's canonical
     table already named) and once via `build_computed_labor_actual_rows` ->
     `get_project_labor_details` -> `calculate_project_labor_details`. = 3xN.
   - `ledger.py::build_computed_labor_plan_rows`'s own per-resource loop (`ledger.py:161-167`) has
     its own `resource_cache` dict that correctly avoids re-fetching *within its own loop*, but
     that cache is a local variable never shared with `LaborCostEngine`'s lookups above — so it
     still contributes a 4th, fully independent pass over every resource. = +1xN.
   - Net: 3xN + 1xN = 4xN, matching the measurement exactly at every fixture size.
2. **Every single repository call independently re-resolves tenant + organization context from
   scratch, with zero per-request caching.** Confirmed by reading
   `SqlAlchemyResourceRepository._base_stmt()` (and the equivalent on every other PM repository):
   each call starts with `self._context()` -> `tenant_context_service.require_organization_context()`
   -> `get_active_tenant()` (1 query against `tenants`) + `get_active_organization()` (1 query
   against `organizations`) — freshly, every time, for every repository method call. This is not
   specific to resources; it is the scoping mechanism every PM repository uses. Measured
   `tenant_context.get_active_tenant`/`get_active_organization` call counts (39/41 at small,
   75/77 at medium, 235/237 at large) track the total repository-call volume for the snapshot,
   and the resource-lookup redundancy above (finding 1) is confirmed to be the single largest
   contributor to that volume, since it alone accounts for 4xN of the total repository calls made
   during one snapshot build.
3. **This is exactly why `organizations`/`tenants` dominate 53-64% of total statements, and why
   that percentage climbs as resource count grows:** `tenants` + `organizations` statement counts
   were 87/164 (53%) at small, 159/272 (58%) at medium, 479/752 (64%) at large — reproducing Phase
   0's original 53-64% finding almost exactly, and confirming it climbs *because* the dominant
   contributor (finding 1) scales with resource count while most other call groups in §7's
   canonical table do not.
4. A small, constant remainder of `tenants`/`organizations` statements (a flat +3/+4 respectively,
   independent of resource count) comes from the snapshot's other, non-resource-scaling repository
   calls (`project_repo.get`, `task_repo.list_by_project`, `cost_repo.list_by_project`, the initial
   permission check) each performing their own single tenant/org resolution — a real but minor
   contributor, not investigated further since it does not scale and is not the growth driver.

**What this means for Phase 1's Reader design (not fixed here — this phase is diagnostic only):**
- The Reader must fetch every resource it needs **once, in a single batch query**, and share that
  result across every consumer that currently calls `resource_repo.get()` independently (labor
  actual, labor plan-vs-actual/ledger rows) — eliminating the 4xN redundancy is expected to be the
  single largest SQL-count reduction available in this migration, larger than the 5x/3x/6x
  domain-call reduction §7 already quantified.
- The tenant/organization re-resolution-per-repository-call pattern is **not specific to Finance**
  and not something Phase 1 can or should fix by itself (fixing it means changing how every PM
  repository resolves scope, a platform-wide change far outside a single-Reader pilot's scope) —
  but the Reader itself should be designed to resolve tenant/organization context **once** per
  read (matching `FinanceService._resolve_scope`'s existing single-resolution pattern) and pass the
  resolved `TenantContext` down to its own SQL statements, rather than letting each of the
  Reader's own internal queries re-derive it independently the way today's repositories do.
- The broader "no per-request tenant/org caching anywhere in the repository layer" finding is
  recorded here as a genuine, cross-cutting P1/P2-shaped observation for a future, dedicated phase
  — explicitly out of scope for this diagnostic pass and for the Finance Reader pilot alike.

Verified with 3 tests (parametrized across small/medium/large,
`test_finance_snapshot_phase0b_sql_growth_attribution.py`), asserting: `LaborCostEngine` is invoked
exactly 3 times per snapshot; `resource_repo.get()` is called exactly `4 * resource_count` times;
measured `tenants`/`organizations` table-hit counts are consistent with (at least 90% attributable
to) the measured tenant-context named-call counts. All pass at all 3 sizes. No production code was
modified in this phase.

**Phase 0B exit gate: PASSED.**

The size-dependent SQL growth has been attributed to 4 × N `ResourceRepository.get` calls and the
repository layer's per-call tenant/organization context resolution.

**Phase 1 must:**

1. acquire required resource facts in one scoped batch;
2. invoke `LaborCostEngine` once;
3. reuse the resulting `LaborDetailsResult` across policy and ledger assembly;
4. avoid any per-resource `ResourceRepository.get` calls;
5. acquire the already-validated active scope IDs once before invoking the Reader;
6. preserve Phase 0C's ID-only repository rule and never reintroduce tenant/organization entity
   hydration inside Reader SQL acquisition.

**Verdict**

| Check | Result |
|---|---|
| Root cause identified | Yes |
| Measurements match static call trace | Yes |
| Growth driver isolated | Yes |
| No production behavior changed | Yes |
| Enough evidence for Reader design | Yes |
| ID-only PM repository scope ready | Yes - completed in Phase 0C |
| **Phase 0B exit gate** | **Passed** |

**Phase 0C - PM repository scope-ID fast path (COMPLETE 2026-08-08).** This phase implements the
cross-cutting PM repository correction diagnosed by Phase 0B before the Finance Reader is built.
It is deliberately a tenancy-scoping optimization, not a CQRS Reader and not an authorization
replacement.

Implemented design:

1. `TenantContextService.require_active_scope_ids(...)` returns immutable `ActiveScopeIds`
   (`tenant_id`, `organization_id`) from the already-established `UserSessionContext`. With the
   production desktop composition's session present, it does not query `tenants` or
   `organizations`. It fails closed with `TENANT_CONTEXT_REQUIRED` or
   `ORGANIZATION_CONTEXT_REQUIRED` when either required ID is absent.
2. Every PM repository scope predicate now consumes IDs only. Direct repositories use
   `require_active_scope_ids(...)`; Calendar Assignment, Portfolio, Project Resource, and Skills
   repositories receive the same behavior through `TenantScopedRepositorySupport`/
   `TenantParentScopedRepositorySupport`. The final incomplete direct classes were
   `SqlAlchemyProjectRepository`, `SqlAlchemyAssignmentRepository`, and
   `SqlAlchemyDependencyRepository`; all are now converted.
3. `TenantContextService.get_active_tenant()`, `.get_active_organization()`,
   `.require_context()`, and `.require_organization_context()` remain intact. Application services
   that need full entities for switching, membership, currency, calendar, or explicit context
   validation continue to use them. RBAC remains in the application service layer, and SQL tenant
   and organization predicates remain in repositories; the fast path replaces neither control.
4. The sessionless `TenantContextService` path retains full-context validation for explicit
   non-desktop/test composition. This is a permanent compatibility of the context service, not a
   PM transition adapter; the composed desktop runtime always supplies `UserSessionContext`.
5. The shared tenant-scope support class is used by repositories outside PM. This phase verifies
   and claims completion only for PM, per this plan's scope; no other module is declared audited by
   association.

Measured result on the same small/medium/large Finance Snapshot fixtures:

| Metric | Small | Medium | Large |
|---|---:|---:|---:|
| Total SQL after Phase 0C | 112 | 148 | 308 |
| `tenants` statements after Phase 0C | 16 | 16 | 16 |
| `organizations` statements after Phase 0C | 19 | 19 | 19 |
| Combined tenant/organization statements before Phase 0C | 87 | 159 | 479 |
| Combined tenant/organization statements after Phase 0C | 35 | 35 | 35 |
| `resource_repo.get` calls still remaining for Phase 1 | 4 | 40 | 200 |

The tenant/organization component is now constant rather than resource-count-dependent. Total SQL
still grows because the independently diagnosed `resource_repo.get == 4 * resource_count` loop
continues to query `resources`; eliminating that remaining loop belongs to Phase 1's batched
Reader, not Phase 0C.

Verification and guardrails:

- `test_phase0c_repository_scope_ids.py` proves session IDs are returned without touching tenant or
  organization repositories, missing scope fails closed, and all formerly incomplete direct PM
  repositories call the ID-only contract.
- `test_pm_phase0c_repository_scope_architecture.py` fails if any PM persistence repository
  reintroduces `require_organization_context(...)`, while also proving the separate full-entity
  helper remains available for genuine consumers.
- The Phase 0B executable diagnostic now retains the still-current 3x labor-calculation and 4xN
  resource-lookup findings without asserting the repository context defect that Phase 0C removed.
- Focused Phase 0B/0C verification: **9 passed**.
- Full PM regression verification: **527 passed** in three timeout-safe, non-overlapping file
  partitions (**145 + 215 + 167**). This includes repository isolation, enterprise-calendar PM
  integration, Finance, Dashboard, desktop adapters, presenters, import/export, WBS, scheduling,
  and migration coverage.
- Full architecture verification: the Phase 0C guards pass; the wider architecture suite reports
  **120 passed and 1 unrelated existing size-budget failure** for generated
  `resources/shared_resources_rc.py` and the already-oversized
  `enterprise_calendar.py`. Phase 0C adds no oversized production module.

**Phase 0C exit gate: PASSED.** All PM repository query/write scoping uses validated active IDs,
tenant and organization predicates are preserved, incomplete scope fails closed, and no full
tenant/organization entity hydration remains in the PM repository package.

**Temporary/deletion register:** none. Phase 0C is a direct contract replacement with no feature
flag, cache, dual path in PM repositories, compatibility facade, or temporary file to delete.

**Main implementation guardrail for Phase 1:** Phase 1 passes only when `resource_repo.get` falls
from 4 × N to zero on the Finance Snapshot path, while labor, policy, DTO, permissions, and
planned-cost semantics remain unchanged.

**Phase 1 — One DB-to-desktop-API read pilot (Finance Snapshot, §17).** Scope: exactly as scoped in
§17, with the ownership split fixed in §15b (`FinanceSnapshotReader` = SQL acquisition,
`LaborCostEngine` = labor calculation, `CostPolicyEngine` = manual/computed-labor reconciliation and
planned-cost policy, `FinanceService` = orchestration and redaction). Files affected: 4 new files
(`contracts/reads/financials/finance_snapshot_reader.py`,
`contracts/reads/financials/models/finance_snapshot_facts.py`,
`infrastructure/persistence/reads/financials/{statements,sqlalchemy_finance_snapshot_reader}.py`),
2 modified files (`finance_service.py` — orchestration only; `cost_policy_engine.py` — gains
`compose_from_facts(...)`, per §15b), 1 composition line (`project_registry.py`). No
`api/desktop/financials/**` source file is expected to change, but the desktop-API boundary test in
§17 — including the required runtime-composition test proving the concrete `Reader` is actually
injected (§4c, the new "Composition weaknesses" note after §14) — is still part of this phase's
required scope. Compatibility approach: the semantic-parity matrix (§17) runs both the current
`CostPolicyEngine.build_snapshot`/`LaborCostEngine.calculate_project_labor_details` path and the new
reader-driven path against identical fixtures for every row in that matrix before the old call
sites inside `FinanceService` are replaced; the old path is then replaced, not kept side-by-side
behind a flag. Tests: as listed in §17. Exit gate: every row of the parity matrix passes with
**field-for-field deep structural and value equality of `FinancialSnapshotDto`** (not "byte-for-byte"
— there is no network serialization byte stream in this in-process architecture, so that phrase is
corrected here and everywhere else it appeared in this document), the query-count/timing
measurements from Phase 0 show the expected reduction across every dimension measured (not query
count alone), the runtime-composition test passes, no regression in the existing
`project_management` test suite. Rollback strategy: revert `finance_service.py`/
`cost_policy_engine.py` to call the pre-pilot chain directly and delete the now-unused Reader/facts
files in the same rollback. Unused transition files are not permitted to remain in the tree.

**Phase 1 implementation result — COMPLETE 2026-08-08.**

Implemented ownership and runtime flow:

1. `FinanceSnapshotReader` and immutable, slotted `FinanceSnapshotFacts` contracts now live under
   `contracts/reads/financials/`. Facts contain primitive project, task, cost-item, grouped stored
   cost, project-resource, assignment, and resource data; they contain no ORM/domain entities,
   permissions, redaction, rate precedence, or policy-applied final snapshot totals.
2. `SqlAlchemyFinanceSnapshotReader` executes seven bounded statements: project, tasks, raw cost
   rows, grouped cost aggregates, project resources, assignments, and one resource batch. Every
   source is constrained by explicit tenant, organization, and project scope; a wrong tenant or
   organization returns no project facts. Independent sources are never fan-out joined before
   aggregation, preventing cost x resource x assignment multiplication.
3. `FinanceService.get_finance_snapshot(project_id, *, as_of=None, period="month")` preserves its
   public signature and desktop DTO. It acquires validated active scope IDs once, invokes the Reader
   once, invokes `LaborCostEngine.calculate_project_labor_details(...)` once with those facts,
   invokes `CostPolicyEngine.compose_from_facts(...)` once, assembles ledger/cashflow/analytics from
   those results, and retains the existing sensitive-finance redaction boundary.
4. `LaborCostEngine` remains the labor/rate owner. It resolves the union of planned and assigned
   resources in one rate-resolution batch, then exposes planned and actual labor rows plus separate
   unresolved-rate diagnostics so existing planned/actual diagnostic semantics are preserved when
   one resource participates in both sets.
5. `CostPolicyEngine` remains the sole manual/computed-labor reconciliation and planned-cost policy
   owner. Its existing repository-backed methods remain for unchanged Reporting/EVM consumers; the
   Finance snapshot no longer calls those methods. Shared internal composition helpers keep existing
   and facts-driven policy behavior aligned rather than copying policy into `FinanceService` or SQL.
6. Runtime composition constructs `SqlAlchemyFinanceSnapshotReader(session=session)` directly in
   `project_registry.py`; the runtime desktop-API test proves
   `DesktopApiRegistry.project_management_financials.get_finance_snapshot(...)` reaches that exact
   concrete instance.

Measured Phase 1 result on the same small/medium/large fixtures:

| Metric | Small | Medium | Large |
|---|---:|---:|---:|
| Original Phase 0 SQL | 164 | 272 | 752 |
| SQL after Phase 0C | 112 | 148 | 308 |
| **SQL after Phase 1** | **62** | **62** | **62** |
| `FinanceSnapshotReader.read_facts` | 1 | 1 | 1 |
| `LaborCostEngine.calculate_project_labor_details` | 1 | 1 | 1 |
| `rate_resolver.resolve_many` | 1 | 1 | 1 |
| `resource_repo.get` | 0 | 0 | 0 |
| `cost_repo.list_by_project` | 0 | 0 | 0 |
| `project_resource_repo.list_by_project` | 0 | 0 | 0 |
| `task_repo.list_by_project` | 0 | 0 | 0 |
| `project_repo.get` | 0 | 0 | 0 |
| Session identity-map delta | 0 | 0 | 0 |

The final instrumented runs observed approximately 49-80 ms wall-clock and 2.6-3.8 ms summed DB
execution time depending on host load. Query count and named collaborator calls are enforced as
hard regression guards; timing remains recorded evidence rather than a brittle test threshold.

Verification:

- reader fact/aggregation, wrong-scope isolation, and real desktop runtime composition: **3 passed**;
- Phase 1 measurement and growth guards across all fixture sizes: **6 passed**;
- focused Finance/desktop/security/source tests: **25 passed**;
- rate-card/planned-cost/configuration tests: **58 passed**;
- full PM regression in timeout-safe, non-overlapping partitions: **530 passed**
  (**202 + 206 + 122**);
- architecture suite: **120 passed**; the one unrelated existing hard-size failure remains generated
  `resources/shared_resources_rc.py` and the previously documented 1,408-line
  `enterprise_calendar.py`. No Phase 1 file violates the hard limit.

**Phase 1 exit gate: PASSED.** The Reader path is tenant/org scoped, cost aggregates do not multiply,
the stable desktop boundary is unchanged, query growth is constant across the measured fixture
sizes, and the 4 x N resource hydration loop is zero.

**Temporary/deletion register:** none. The old Finance-only repository-based ledger implementation
was replaced directly. The now-unreferenced `application/financials/costs/policy.py` helper was
deleted. No feature flag, compatibility facade, fallback reader, dual Finance path, or temporary
file remains to delete after migration.

**Phase 2 — Review and architecture guardrails.** Scope: add the enforceable tests in §19 (readers
don't return domain/ORM entities, tenant scope mandatory on every reader method, etc.) **now that a
second real example exists** to write a guardrail against, not before. Files affected: new test
files under `src/tests/architecture/`. Exit gate: guardrail tests pass against the Phase 1 code and
would fail if a hypothetical violation were introduced (write a deliberately-broken temporary
example to prove the guardrail catches it, then remove the example).

**Phase 2 implementation result — COMPLETE 2026-08-08.**

Implemented guardrails:

1. Every current and future `Protocol` under `contracts/reads/**` is inspected for explicit
   `tenant_id` and `organization_id` parameters and a contract-owned facts/primitive return type.
2. Every facts dataclass under `contracts/reads/**/models/` must be both frozen and slotted.
3. Read contracts cannot import application services, desktop adapters, persistence, ORM, or
   SQLAlchemy. SQLAlchemy Reader adapters cannot import application or desktop layers.
4. SQLAlchemy Readers cannot call write/session lifecycle methods, broadly catch infrastructure
   exceptions, perform permission/redaction/rate-policy work, or reference planned-cost-version
   models as an alternative source.
5. Every Finance statement builder must accept tenant, organization, and project scope. The resource
   statement must apply direct tenant/organization predicates plus project-scoped existence checks.
6. The cost aggregate is structurally limited to `CostItemORM` plus its scoped `ProjectORM` parent,
   requires `SUM`/`GROUP BY`, and cannot fan out through project resources or assignments.
7. `FinanceService.get_finance_snapshot` is locked to exactly one Reader call, one labor calculation,
   and one policy composition, with repository refetches and Finance-side reconciliation forbidden.
   The guard also proves `CostPolicyEngine.compose_from_facts` remains the reconciliation owner.
8. Runtime composition must construct `SqlAlchemyFinanceSnapshotReader(session=session)`, and the
   real desktop-runtime test proving the concrete instance is reached must remain present.
9. The existing QML Python-layer boundary now explicitly rejects both `contracts.reads` and
   `infrastructure.persistence.reads` imports, in addition to repositories/ORM.
10. Guard-detector tests feed deliberately broken contract and adapter source in memory and prove
    that missing organization scope, an application-layer contract import, and `session.commit()`
    are rejected. No deliberately broken file is written to or retained in the repository.

Verification:

- new CQRS Reader architecture guards plus the extended QML boundary: **21 passed**;
- Phase 1 real Reader/runtime integration recheck: **3 passed**;
- full architecture suite: **128 passed** with the same one unrelated existing hard-size failure for
  generated `resources/shared_resources_rc.py` and the previously documented 1,408-line
  `enterprise_calendar.py`.

**Phase 2 exit gate: PASSED.** The guard logic catches deliberately broken in-memory examples, all
Reader contracts/adapters and the real Phase 1 composition satisfy the enforced boundaries, and no
production behavior changed in this phase.

**Temporary/deletion register:** none. Broken examples exist only as in-memory strings inside the
guard self-test; no temporary production path, fixture module, compatibility code, or dead file was
created.

**Phase 3A measured baseline and implementation contract - COMPLETE 2026-08-08.**

The real `ReportingService.get_evm_series(...)` runtime composition was measured with one task, two
resources, one baseline, one direct-cost row, and 3/12/24 monthly points. Timing is evidence only;
statement and collaborator growth are the enforceable regression dimensions.

| Metric | 3 points | 12 points | 24 points |
|---|---:|---:|---:|
| Wall time (host observation) | 0.133 s | 0.596 s | 1.023 s |
| Summed DB execution time | 0.006 s | 0.023 s | 0.036 s |
| **SQL statements** | **248** | **896** | **1,754** |
| `EarnedValueCalculator.calculate` | 3 | 12 | 24 |
| `project_repo.get` | 10 | 37 | 73 |
| `baseline_repo.get_baseline` | 3 | 12 | 24 |
| `baseline_repo.list_tasks` | 4 | 13 | 25 |
| `task_repo.list_by_project` | 6 | 24 | 48 |
| `cost_repo.list_by_project` | 3 | 12 | 24 |
| `project_resource_repo.list_by_project` | 3 | 12 | 24 |
| `assignment_repo.list_by_tasks` | 3 | 12 | 24 |
| `resource_repo.get` | 6 | 24 | 48 |
| `rate_resolver.resolve_many` | 6 | 24 | 48 |

This confirms a period-count N+1, not merely resource-count growth. Every point reconstructs the
baseline/task/project graph and then re-enters both planned- and actual-labor rate resolution. The
large authorization/context statement counts are amplified by rate resolution using full entity
context revalidation even though it compares IDs only.

Phase 3A implementation boundaries:

1. Add one tenant/organization/project-scoped EVM-series Reader returning immutable primitive facts.
   It may compose the existing Finance fact Reader and a series-specific baseline projection; it
   must not return ORM/domain entities or apply EVM, cost-source, rate-precedence, RBAC, or redaction
   policy.
2. Add multi-date rate resolution that reads resource contexts and overlapping rate candidates once,
   then invokes the existing rate-precedence classifier independently for each period. A new rate
   algorithm or SQL-owned precedence is forbidden.
3. `LaborCostEngine`, `CostPolicyEngine`, and `EarnedValueCalculator` remain the semantic owners.
   They gain prepared-facts/series entry points that share existing composition and formula helpers;
   the orchestration layer must not copy those policies.
4. Preserve `ReportingService.get_evm_series(...)`, the desktop API, DTO fields, QML behavior,
   month-end generation, baseline selection, calendar math, unresolved-rate handling, and cost-source
   reconciliation. Add parity coverage for explicit/latest baselines, cost-loaded and fallback BAC,
   rate effective-date changes, manual/computed labor, and no-baseline errors.
5. Exit gate: source acquisition and rate-candidate reads are bounded independently of period count;
   legacy repository calls from the series path are zero; old and new results are field-for-field
   equal across the parity matrix; focused PM, desktop, architecture, and runtime-composition tests
   pass.

**Temporary/deletion register:** none planned. Phase 3A replaces the EVM-series runtime path directly;
no feature flag, fallback calculator loop, compatibility Reader, or transition evidence file may be
retained. The repository-backed single-date EVM and Reporting cost builders remain live capabilities
until their explicitly separate Phase 3B migration and are therefore not Phase 3A dead code.

Phase 3A implementation result:

1. `EvmSeriesReader` and frozen/slotted `EvmSeriesFacts` now own the read boundary. The concrete
   SQLAlchemy adapter composes the existing Finance fact projection with explicitly scoped latest or
   requested baseline facts. Task progress is a primitive Finance task fact, so no duplicate task
   source read is needed. Wrong tenant or organization returns no facts.
2. `RateCardResolver.resolve_many_dates(...)` loads resource contexts and rate candidates overlapping
   the complete period range once. It filters candidates per date in memory and invokes the existing
   precedence/ambiguity selection unchanged. Its ID-only context comparison now uses the Phase 0C
   `require_active_scope_ids(...)` fast path rather than rehydrating tenant/organization entities.
3. `LaborCostEngine.calculate_project_labor_series(...)` composes each period from the prepared facts
   and dated rate batches. `CostPolicyEngine.compose_from_facts_at(...)` derives period-specific stored
   cost aggregates from the one raw cost fact set and delegates to the existing reconciliation path.
   Manual labor remains excluded when computed labor exists.
4. `EarnedValueCalculator` remains the sole EVM formula owner. Its prepared-facts parameters bypass
   repository acquisition but execute the same BAC/PV/EV/AC and derived-metric implementation.
   `GlobalCalendarShim` supplies one request-scoped working-day snapshot for the complete series
   range, preserving enterprise rules/exceptions without a process-global stale cache.
5. Runtime composition injects `SqlAlchemyEvmSeriesReader(session=session)` into `ReportingService`.
   `EarnedValueSeriesCalculator.build_series` now performs one scope lookup, one Reader call, one
   multi-date labor/rate call, one calendar snapshot, and in-memory period composition. The stable
   reporting/desktop/QML DTO boundary did not change.

Measured post-cutover result on the same fixtures:

| Metric | 3 points | 12 points | 24 points |
|---|---:|---:|---:|
| Original SQL | 248 | 896 | 1,754 |
| **Phase 3A SQL** | **50** | **50** | **50** |
| Observed wall time | 0.041 s | 0.046 s | 0.052 s |
| `EvmSeriesReader.read_facts` | 1 | 1 | 1 |
| `rate_resolver.resolve_many_dates` | 1 | 1 | 1 |
| rate context/candidate range reads | 1 + 1 | 1 + 1 | 1 + 1 |
| calendar working-day range reads | 1 | 1 | 1 |
| all legacy series repository calls | 0 | 0 | 0 |

Verification:

- post-cutover measurement/growth guard: **3 passed**;
- explicit/latest baseline, dated-rate, manual/computed-labor, budget-fallback, no-baseline,
  wrong-scope, and real runtime-composition parity coverage: **4 passed**;
- focused rate-card/cost/baseline regression: **38 passed**;
- full PM suite in timeout-safe partitions: **537 passed** (**202 + 213 + 122**);
- full architecture suite: **130 passed** with only the same unrelated existing hard-size failure for
  generated `resources/shared_resources_rc.py` and the documented 1,408-line
  `enterprise_calendar.py`.

**Phase 3A exit gate: PASSED.** SQL and named source calls are bounded independently of period count;
the parity matrix, tenant isolation, concrete runtime injection, PM regressions, and architecture
guards pass. Timing remains evidence only and is not used as a brittle threshold.

**Phase 3A final deletion register:** none. The old per-period series acquisition loop was replaced
directly. No feature flag, compatibility Reader, fallback series implementation, transition evidence
module, or temporary file remains. The repository-backed single-date EVM and broader Reporting cost
builders are live Phase 3B inputs, not dead Phase 3A code.

**Phase 3B measured baseline and implementation contract - COMPLETE 2026-08-08.**

The four standalone `ReportingService` financial reads were measured independently on the same
small/medium/large fixtures used by the Finance pilot. Each fixture has 1/10/50 resources,
2/15/60 tasks, and 2/30/150 cost rows. A baseline is added for the baseline-aware operations.

| Operation | Small SQL | Medium SQL | Large SQL | Confirmed large-fixture source graph |
|---|---:|---:|---:|---|
| cost control totals | 93 | 102 | 142 | 2 project gets, 1 task list, 1 project-resource list, 1 assignment batch, 50 resource gets, 1 cost list, 2 rate batches |
| cost source breakdown | 100 | 109 | 149 | same graph plus a second cost list for raw manual-labor totals |
| cost breakdown | 105 | 114 | 154 | same graph as totals; baseline fallback is conditional and was not entered because planned data exists |
| single-date earned value | 115 | 124 | 164 | totals graph plus baseline get/list, a second task list, and a third project get |

All four operations invoke `CostPolicyEngine.build_snapshot(...)` once,
`ReportingService.calculate_project_labor_details(...)` once, and
`rate_resolver.resolve_many(...)` twice. Every operation performs one `resource_repo.get(...)` per
assigned resource. The exact +N SQL slope therefore remains after Phase 3A and justifies this
sub-phase independently; Phase 3A improved only the series path.

Phase 3B implementation boundaries:

1. Cost totals and cost-source reads consume one explicitly tenant/organization/project-scoped
   `FinanceSnapshotReader` result. Cost breakdown and earned value consume one `EvmSeriesReader`
   result because baseline facts are part of their existing semantics.
2. `LaborCostEngine` remains the rate/labor owner and is called once with prepared Finance facts.
   `CostPolicyEngine.compose_from_facts(...)` remains the sole reconciliation owner and is called
   once. `EarnedValueCalculator` and `CostBreakdownEngine` remain the sole formula/row owners and gain
   or use facts/snapshot entry points rather than having logic copied into Reporting mixins.
3. Preserve all four public signatures and application result types, latest/explicit baseline
   behavior, unresolved-rate fail-closed behavior for EVM, manual/computed-labor policy, currency
   filtering, future-incurred-cost filtering, and baseline planned-cost fallback.
4. Preserve the existing `report.view` plus project-scope permission contract in this performance
   sub-phase. The audit's broader `finance.read`/sensitive-redaction unification question remains an
   explicit authorization-design decision and must not be changed as an accidental Reader side
   effect.
5. Runtime composition must inject the concrete Finance and EVM Readers into Reporting. The Finance
   Reader instance may be shared with `FinanceService`; no Reporting-owned SQL, ORM access, domain
   entity hydration, or Reader fallback is permitted.
6. Exit gate: each operation performs exactly one facts read, one facts-driven labor calculation,
   and one facts-driven policy composition; all legacy repository calls and per-resource hydration
   from these four runtime paths are zero; query count is bounded across fixture sizes; the parity,
   isolation, runtime-composition, PM regression, and architecture guards pass.

Phase 3B cut over all four operations to prepared Reader facts. Cost totals and source use the
concrete `SqlAlchemyFinanceSnapshotReader`; breakdown and single-date earned value use the concrete
`SqlAlchemyEvmSeriesReader`. Runtime composition injects both Readers into `ReportingService`.
`LaborCostEngine.calculate_project_labor_details(...)` and
`CostPolicyEngine.compose_from_facts(...)` each run exactly once per operation. Formula ownership
remains in `CostBreakdownEngine.build_breakdown_from_snapshot(...)` and
`EarnedValueCalculator.calculate(...)`; the Reporting mixins contain no duplicate finance formula.

| Operation | Baseline SQL small/medium/large | Post-cutover SQL small/medium/large | Repository calls after cutover |
|---|---:|---:|---:|
| cost control totals | 93 / 102 / 142 | **45 / 45 / 45** | **0** |
| cost source breakdown | 100 / 109 / 149 | **45 / 45 / 45** | **0** |
| cost breakdown | 105 / 114 / 154 | **47 / 47 / 47** | **0** |
| single-date earned value | 115 / 124 / 164 | **47 / 47 / 47** | **0** |

The post-cutover measurement suite also proves one Reader call, one rate-resolution batch, one
facts-driven labor calculation, one policy composition, and no ORM identity-map growth for every
operation and fixture size. The parity matrix covers mixed computed/manual labor, future incurred
costs, out-of-currency rows, explicit/latest baseline selection, and unresolved-rate fail-closed EVM
behavior. Concrete runtime-composition coverage proves Reporting receives the SQLAlchemy Finance
Reader rather than a test-only or fallback implementation.

Verification completed on 2026-08-08:

- Phase 3A/3B focused CQRS suites: **12 passed**.
- focused financial policy and reporting regressions: **32 passed**.
- full PM suite, partitioned to bound test-run memory: **542 passed** (209 + 209 + 124).
- full architecture suite: **133 passed**, with only the pre-existing hard-size failure for generated
  `resources/shared_resources_rc.py` and the documented 1,408-line `enterprise_calendar.py`.

**Phase 3B deletion register - COMPLETE:** no temporary adapter, feature flag, compatibility Reader,
fallback path, or transition-evidence file was introduced. Repository-wide reference analysis proved
the old `CostPolicyEngine.get_cost_control_totals(...)`, `get_actual_cost(...)`, and
`get_cost_source_breakdown(...)` wrappers, the repository-backed `CostBreakdownEngine` entry point,
and the repository-backed `EarnedValueCalculator` path had no remaining production caller, so they
were deleted in the same cutover. `CostPolicyEngine.build_snapshot(...)` remains intentionally live
for KPI callers and is not dead code.

**Phase 3B exit gate: PASSED.** Query growth is bounded, behavioral parity and fail-closed behavior
are protected, concrete runtime wiring is proven, all PM regressions pass, and no migration-only code
remains.

**Phase 3 — Migrate additional high-cost reads, one capability per sub-phase, each explicitly
measured before it is trusted to have improved anything.** An earlier draft of this plan bundled
these together and separately implied `ReportingService` and `EarnedValueSeriesCalculator` would
benefit automatically from Phase 1 — both claims are corrected: nothing here is assumed to benefit
until its own sub-phase explicitly migrates and re-tests it.

- **Phase 3A** — measure and migrate `EarnedValueSeriesCalculator.build_series` explicitly (the
  worst confirmed N+1 in the module, §7).
- **Phase 3B - COMPLETE 2026-08-08** — measured and migrated `ReportingService`'s cost/EVM builders
  explicitly (§7 and §15b); the independently verified result is recorded above.
- **Phase 3C - COMPLETE 2026-08-08 — measured and migrated Portfolio reads.** Candidates:
  `PortfolioService.list_portfolio_heatmap`; scenario evaluation/comparison; cross-project capacity
  reporting (`PortfolioResourcePoolService`) — **after** its Phase 0A.1 permission fix, not instead
  of it. Required precondition, all three: (1) Phase 0A's Portfolio security and rollback
  corrections (0A.1, 0A.2) are complete; (2) existing behavior is protected by the tests those
  sub-phases require; (3) a measured baseline (mirroring Phase 0's methodology) confirms a
  meaningful N+1, over-fetch, or projection problem — not assumed from §14's qualitative finding
  alone. Possible later flow, **not created during Phase 0A or Phase 1**:
  ```text
  Portfolio desktop API
    → Portfolio query service
    → Portfolio Reader
    → tenant/org-scoped SQL projection
    → immutable Portfolio read model
    → existing desktop serializer/DTO
  ```

  The mandatory Phase 0A.1 authorization and Phase 0A.2 rollback preconditions are complete. A
  persistent measurement harness then exercised each candidate with 1/5/12 projects, one scheduled
  assigned resource per project, and two overlapping scenarios:

  | Candidate | SQL at 1 project | SQL at 5 projects | SQL at 12 projects | Decision |
  |---|---:|---:|---:|---|
  | executive heatmap | 332 | 1,448 | 3,401 | Phase 3C.3 complete; now 67 / 91 / 133 |
  | scenario comparison | 347 | 869 | 1,739 | Phase 3C.2 complete; now 62 / 62 / 62 |
  | cross-project capacity pool | 298 | 1,418 | 3,378 | justified; migrate first as Phase 3C.1 |

  The attribution is explicit. Heatmap calls full KPI and resource-load reporting once per project
  (at 12 projects: 12 KPI calls, 12 resource-load calls, 36 project gets, 48 task lists, and 24
  resource gets). Scenario comparison repeats accessible-project/intake acquisition three times and
  resource-load reporting 18 times. Capacity performs two resource gets and assignment reads per
  resource, two task gets per resource, one project get per project, and 3,276 calendar-related SQL
  statements at the large fixture. All three exceed the evidence threshold; they are not speculative
  CQRS work.

  **Phase 3C.1 cross-project capacity - COMPLETE 2026-08-08.**

  - `PortfolioResourcePoolService` now consumes one immutable, explicitly tenant/organization-scoped
    `PortfolioResourcePoolReader` fact set and one bounded working-day snapshot.
  - `SqlAlchemyPortfolioResourcePoolReader` projects resources plus joined assignment/task/project
    demand rows directly. It returns no ORM or domain entities and applies tenant and organization
    predicates to both resource and project sides of the join.
  - the old resource/assignment/task/project repository constructor dependencies and the private
    `ResourceAvailabilityService._compute_window(...)` call were deleted; runtime composition injects
    the concrete SQLAlchemy Reader directly, with no fallback.
  - query count is now **20 / 20 / 20** for 1/5/12 projects, with exactly one Reader call, one bulk
    calendar resolution, and zero legacy repository calls. Cross-project demand names, allocation,
    peak/average utilization, overload state, explicit resource filtering, fail-closed permission,
    and tenant/organization scope are protected by focused tests.
  - the more precise missing-organization error code is now `ORGANIZATION_CONTEXT_REQUIRED`; missing
    tenant remains `TENANT_CONTEXT_REQUIRED`.

  Verification completed on 2026-08-08: the measurement harness passes all 3 fixture sizes; the
  broader Portfolio/PM integration selection passes **61 tests**; focused parity, concrete
  cross-organization isolation, and CQRS architecture checks pass; and the full architecture suite
  reports **134 passed** with only the same pre-existing hard-size failure for generated
  `resources/shared_resources_rc.py` and the documented 1,408-line `enterprise_calendar.py`.
  `compileall` and `git diff --check` are clean.

  **Phase 3C.1 deletion register - COMPLETE:** no compatibility constructor, repository fallback,
  feature flag, transition evidence, or temporary implementation file remains.

  **Phase 3C.2 scenario evaluation/comparison - COMPLETE 2026-08-08.**

  - `evaluate_scenario` and `compare_scenarios` now consume one immutable
    `PortfolioScenarioReader` fact graph. Comparison no longer calls the public evaluation method
    twice or repeats scenario, project, intake, resource, task, and assignment acquisition.
  - authorization remains application-owned: `portfolio.read` is enforced first, and the existing
    project-access filter resolves the allowed project IDs once. The Reader then applies explicit
    tenant/organization predicates independently to scenarios, projects, intake, resources, tasks,
    and assignments; passing an inaccessible project ID cannot widen its SQL scope.
  - `ResourceLoadEngine` is now the one pure owner of leaf-task selection, scheduled peak,
    unscheduled allocation, capacity normalization, utilization, and sorting. Both Reporting's
    `get_resource_load_summary` and Portfolio scenario evaluation delegate to it; no Portfolio copy
    of the load formula was introduced.
  - the project date range resolves to one immutable working-day snapshot. Scenario comparison now
    performs exactly one Reader call, one project-access scan, and one bulk calendar call, with zero
    scenario/intake repository gets and zero per-project Reporting/resource-load calls.
  - measured SQL is **62 / 62 / 62** for 1/5/12 projects, down from **347 / 869 / 1,739**. Public
    signatures and result models are unchanged. Parity covers scheduled and unscheduled work,
    shared resources, inactive capacity exclusion, intake scoring, default/explicit capacity limits,
    budget and capacity flags, comparison deltas, and concrete cross-organization isolation.

  Verification completed on 2026-08-08: the broader Portfolio/desktop/tenant-isolation/reporting
  selection passes **34 tests**; the focused measurement, parity, concrete Reader, and architecture
  selection passes; the full PM suite passes **551 tests** in bounded partitions
  (209 + 210 + 132); and the full architecture suite reports **135 passed** with only the same
  pre-existing hard-size failure for generated `resources/shared_resources_rc.py` and the documented
  1,408-line `enterprise_calendar.py`. `compileall` and `git diff --check` are clean.

  **Phase 3C.2 deletion register - COMPLETE:** the recursive comparison-to-evaluation path,
  `_portfolio_resources`, direct scenario/intake query acquisition, per-project Reporting fan-out,
  and `PortfolioService`'s scenario-only `ResourceRepository` dependency were deleted in the same
  cutover. No compatibility constructor, fallback Reader, feature flag, transition evidence, or
  temporary implementation file remains. At that checkpoint the Phase 3C.3 heatmap was still an
  independently measured live path; its subsequently completed cutover is recorded below.

  **Phase 3C.3 executive heatmap - COMPLETE 2026-08-08.**

  - `PortfolioService.list_portfolio_heatmap` now acquires one immutable
    `PortfolioHeatmapReader` fact graph after application-owned `portfolio.read` authorization and
    one existing project-access scan. `SqlAlchemyPortfolioHeatmapReader` applies explicit tenant,
    organization, and accessible-project predicates to projects, tasks, dependencies, costs,
    project resources, assignments, and resources; it returns no ORM/domain entities.
  - schedule, utilization, labor, and cost policy remain owned by their established engines:
    `CPMCalculator`, `ResourceLoadEngine`, `LaborCostEngine`, and `CostPolicyEngine`. The heatmap did
    not introduce a second CPM, utilization, rate-card, or manual/computed-labor formula.
  - each project resolves one bounded immutable working-day snapshot through its project calendar
    hierarchy and one batched rate-card resolution for its resources. These calls intentionally
    remain per project because project calendar assignments and project-scoped rate-card precedence
    are independent policy inputs; replacing them with one global calendar/rate would be faster but
    incorrect. The new bulk calendar API has no day-by-day SQL fallback. A future platform-level
    multi-project calendar/rate projection may reduce this policy slope without changing this Reader
    contract, but it is not a correctness or Phase 3C exit blocker.
  - measured SQL is **67 / 91 / 133** for 1/5/12 projects, down from
    **332 / 1,448 / 3,401**. The exact regression budget is `61 + 6 * project_count` in the seeded
    fixture: one heatmap Reader call, one access scan, one calendar snapshot and one rate-resolution
    call per project, and zero legacy KPI, resource-load, project-get, task-list, assignment-list, or
    resource-get calls. This removes the former roughly 280 statements per additional project while
    preserving project-specific policy semantics.
  - parity covers dependency-driven CPM, critical and late counts, overload normalization, computed
    labor plus manual-cost policy, cost variance, pressure scoring/sorting, concrete runtime wiring,
    cross-organization rejection, and the existing stable-row behavior when one project's facts are
    invalid. Desktop DTO and QML shapes remain unchanged.
  - the heatmap remains a growing collection and therefore inherits this audit's pagination rule:
    the future desktop query-service pagination cutover must use stable cursor/keyset semantics and
    preserve the current pressure/late/name ordering. Pagination was not silently added to the
    existing no-argument desktop contract in this optimization sub-phase.

  Verification completed on 2026-08-08: focused parity, measurement, enterprise-foundation,
  tenant-isolation, desktop Portfolio, concrete Reader, and CQRS architecture checks pass. The full
  PM suite passes **554 tests** in bounded partitions (**212 + 215 + 127**). The full
  architecture suite reports **136 passed**, with only the same pre-existing hard-size failure for
  generated `resources/shared_resources_rc.py` and the documented 1,408-line
  `enterprise_calendar.py`. `compileall` and `git diff --check` are clean.

  **Phase 3C.3 deletion register - COMPLETE:** the per-project Reporting KPI/resource-load fan-out
  and `PortfolioService`'s now-unused `ReportingService` dependency were deleted in the same cutover.
  No compatibility constructor, repository fallback, feature flag, transition evidence, temporary
  implementation file, or migration-only path remains.

  **Phase 3C exit gate: PASSED.** All three measured Portfolio candidates now use scoped immutable
  facts with explicit query budgets, protected behavior, fail-closed authorization, concrete runtime
  wiring, and no superseded transition path.
- **Phase 3D - COMPLETE 2026-08-08 — measured and migrated Collaboration reads.** Phase 0A.3's
  rollback correction was complete before this work began. The persistent 1/5/12-project harness
  seeded one task, comment, and active-presence row per project and measured both public candidates:

  | Candidate | SQL at 1 project | SQL at 5 projects | SQL at 12 projects | Post-cutover |
  |---|---:|---:|---:|---:|
  | collaboration inbox | 40 | 104 | 216 | **53 / 53 / 53** |
  | collaboration workspace snapshot | 44 | 108 | 220 | **56 / 56 / 56** |

  The baseline growth was caused by one task-list and one project-permission path per accessible
  project; runtime session revalidation amplified every permission call. Workspace snapshot also
  queried the same recent comments twice before reading presence and audit rows. The cutover now
  performs one canonical accessible-project filter and one immutable `CollaborationWorkspaceReader`
  fact read. Inbox executes one joined comment query. Workspace executes that same comment query
  once, one joined presence query, and one organization-scoped audit query. It no longer scales SQL
  with the number of accessible projects in the measured fixture.

  Authorization remains application-owned: `collaboration.read` and canonical project filtering run
  before the Reader. `SqlAlchemyCollaborationWorkspaceReader` accepts only those authorized project
  IDs and independently applies explicit tenant, organization, and project predicates to every
  query; it neither resolves nor broadens access. Direct cross-organization and scoped-viewer tests
  prove comments, presence, and project names cannot leak from unauthorized projects.

  Public desktop/QML DTOs and service signatures are unchanged. Mention aliases, unread state,
  ordering, previews, audit-derived workflow notices, active-presence TTL, and the legacy
  limit-before-mention-filter behavior have parity coverage. Existing `limit` arguments remain
  bounded SQL limits; they are not advertised as cursor pagination. A later keyset/cursor contract
  is required only if Collaboration gains continuation-based navigation.

  Verification completed on 2026-08-08: focused Collaboration, rollback, enterprise-foundation,
  desktop/QML, tenant-isolation, measurement, concrete Reader, and CQRS architecture checks pass.
  The full PM suite passes **560 tests** in bounded partitions (**215 + 218 + 127**). The full
  architecture suite reports **137 passed**, with only the same two pre-existing hard-size
  violations for generated `resources/shared_resources_rc.py` and the documented 1,408-line
  `enterprise_calendar.py`. `compileall` and `git diff --check` are clean.

  **Phase 3D deletion register - COMPLETE:** `_accessible_task_context_for_collaboration`,
  `_accessible_tasks_for_collaboration`, `_list_accessible_comments`, the per-project permission and
  project-name helpers, and the duplicate workspace comment read were deleted in the same cutover.
  No compatibility constructor, repository fallback, feature flag, transition evidence, temporary
  implementation file, or migration-only path remains.

  **Phase 3D exit gate: PASSED.** The measured Collaboration candidates now use explicitly scoped,
  immutable facts with constant query budgets, protected behavior, fail-closed authorization,
  concrete runtime wiring, and no superseded transition path.

Each sub-phase follows the same reader+facts+parity-test shape Phase 1 established, is independently
reviewable and revertible, and requires its own Phase-0-style measurement before and after — none of
them inherit Phase 1's measured improvement by association.

**Phase 4 - COMPLETE 2026-08-08 — introduce command results only on selected writes.**

- `BudgetService.approve_budget` now returns frozen, slotted `BudgetApprovalResult`. Direct approval
  returns `applied` after the budget transaction commits; governed approval returns
  `pending_approval` with the committed approval-request ID and leaves the submitted budget
  unchanged. Stale writes, denied permissions, duplicate pending requests, invalid lifecycle
  transitions, and persistence conflicts remain typed errors rather than successful outcomes.
- The result is intentionally narrow: outcome, budget/project IDs, budget status, row version, and
  optional request ID. It contains no domain aggregate, ORM object, repository, or untyped payload.
  `_apply_approval_decision` remains an internal aggregate-returning method because the registered
  approval handler needs the project ID while participating in `ApprovalService`'s transaction.
- No production desktop/QML caller existed for `approve_budget`, so no compatibility adapter,
  feature flag, dual return type, or temporary migration path was introduced. Other PM writes keep
  their existing returns; Phase 4 is not a blanket command-object/result rewrite.

Verification completed on 2026-08-08: all **42 budget lifecycle tests** pass; the focused CQRS
architecture file passes **18 tests**; the full PM suite passes **560 tests** in bounded partitions
(**215 + 218 + 127**); and the full architecture suite reports **138 passed** with only the same
pre-existing hard-size guard failure listing generated `resources/shared_resources_rc.py` and the
documented 1,408-line `enterprise_calendar.py`. `compileall` and `git diff --check` are clean.

**Phase 4 deletion register - COMPLETE:** the budget-specific `APPROVAL_REQUIRED` branch was removed
when the result contract landed. No compatibility result, legacy exception fallback, transition
evidence, temporary file, or migration-only code remains.

**Phase 4 exit gate: PASSED.** Both successful budget-approval outcomes are explicit and tested,
error semantics and transaction ownership are preserved, and unrelated write contracts are
unchanged.

**Phase 5 - NOT TRIGGERED (2026-08-08) — connect stable desktop DTOs to QML only when required.**
Phases 1 and 3A-3D preserved every desktop DTO and QML contract, and Phase 4's selected command
result has no production desktop/QML caller. There is therefore no responsible Phase 5 source
change to make. A future Decimal-safe Financials DTO migration addressing
`TRANSITION(PF-A1-DESKTOP-FLOAT)` remains a separately measured, end-to-end desktop/QML phase; this
conditional phase is closed for the current CQRS plan rather than filled with speculative churn.

**Phase 6 - COMPLETE 2026-08-08 — remove superseded entity-based read paths.**

- `FinanceService` is now structurally Reader/fact-only. Its constructor and composition no longer
  accept project, task, resource, cost, project-resource, or assignment repositories. The stored
  repository attributes and `_make_cost_policy_engine` repository-capable factory were deleted;
  `LaborCostEngine.for_facts` and `CostPolicyEngine.for_facts` are constructed once and can only
  compose the scoped `FinanceSnapshotReader` result.
- Reporting's migrated cost totals, source breakdown, cost breakdown, earned value, and EVM series
  paths now construct fact-only engines explicitly. They cannot silently fall back to aggregate
  repositories if facts are omitted. Existing Phase 3B methods removed from `CostPolicyEngine` and
  `CostBreakdownEngine`, plus the repository-owning `EarnedValueCalculator` dependencies, remain
  absent under architecture guard.
- **Retained live-path register:** `ReportingKpiMixin.get_project_kpis` still calls
  `_build_cost_policy_snapshot`, and standalone `ReportingLaborMixin` APIs still use
  repository-capable `LaborCostEngine`. Those reads were not migrated by Phases 1 or 3A-3D and are
  consumed by Dashboard/reporting/export surfaces. They are intentionally retained, not dead code;
  removing them requires a separately measured Reader migration and is outside deletion-only Phase
  6. The architecture guard locks this distinction so neither a fallback regression nor premature
  deletion can pass unnoticed.
- Persistent Phase 0/0B measurement harnesses now inspect the live Reader/fact-only graph. They
  assert superseded Finance repository dependencies are absent and the fact-only labor engine has
  no resource repository, instead of depending on deleted private attributes.

Verification completed on 2026-08-08: the focused Finance/Reporting/EVM/architecture selection
passes **34 tests**; the updated persistent measurement cases pass **6 tests** and retain a constant
**60-statement** snapshot budget across small/medium/large fixtures; the full PM suite passes
**560 tests** in bounded partitions (**215 + 218 + 127**); and the full architecture suite reports
**139 passed** with only the same pre-existing hard-size guard failure listing generated
`resources/shared_resources_rc.py` and the documented 1,408-line `enterprise_calendar.py`.
`compileall` and `git diff --check` are clean.

**Phase 6 deletion register - COMPLETE:** the six Finance repository constructor dependencies and
attributes, repository-capable Finance policy factory, composition arguments, and repository-capable
engine construction from every migrated Reporting/EVM path were removed in the same cutover. No
compatibility constructor, fallback engine, feature flag, transition evidence, temporary file, or
migration-only code remains.

**Phase 6 exit gate: PASSED.** Every migrated read path is fact-only, every retained aggregate path
has a verified live owner outside the migrated scope, runtime composition and query budgets pass,
and the numbered CQRS implementation plan is complete without speculative DTO or QML changes.

*(The future, separately-scoped Session/Unit-of-Work modernization is deliberately not a numbered
phase in this plan — see the note immediately after §14's findings table.)*

---

## 19. Architecture guardrails

Recommended enforceable tests, each tied to a specific finding above (file paths indicative — to be
added under `src/tests/architecture/` following this module's existing convention):

1. **Readers do not return domain or ORM entities.** For every class implementing a `*Reader`
   `Protocol` under `contracts/reads/**`, assert every public method's return-type annotation is
   either a dataclass defined in that same `contracts/reads/*/models/` package (per §16's corrected
   structure — colocated with the `Protocol`, never under `application/`) or a primitive/tuple
   thereof — never a `domain.*`, `infrastructure.persistence.orm.*`, or `application.*` type.
   (Directly modeled on the audit's own confirmed-clean finding about `RateResolutionReader` in
   §9a — this guardrail formalizes an existing, currently-unenforced convention, and additionally
   locks in the dependency-direction fix from §15b/§16.)
2. **Application commands/queries do not import desktop DTOs.** Grep-based: no file under
   `application/**` imports from `api.desktop.**`. (Currently true everywhere audited; worth
   locking in before Phase 3+ adds more files.)
3. **Domain does not import SQLAlchemy, desktop API, or read models.** Already true (§9a's "import
   cleanliness verdict: none found" across every domain file) — lock it in as a guardrail rather
   than leaving it as an unenforced fact.
4. **Write repositories do not gain new dashboard/report methods.** For `contracts/repositories/*`,
   assert no method name matches a report-shaped pattern (`get_totals_*`, `*_summary`,
   `list_*_heatmap`, `is_default_for_*`) is *added* going forward — existing ones (§9a's fat-repo
   list) are grandfathered, not retroactively broken.
5. **Desktop APIs do not receive ORM models.** Already true everywhere audited (§8) — add a
   guardrail so a future desktop-API method can't regress this by accident (check that no
   `api/desktop/**/api.py` method's parameter or return-type annotation references
   `infrastructure.persistence.orm`).
6. **QML never accesses repositories, ORM, or Readers.** Already true for repositories/ORM (§3's
   UI-consumer grep found no repository imports under `src/ui_qml/**`) — extend the same
   import-direction test (mirroring `test_qml_architecture_guardrails_layers.py`'s existing
   pattern) to also assert no `contracts.reads.**`/`infrastructure.persistence.reads.**` import
   appears under `src/ui_qml/**`, so a future Reader introduction can't accidentally become a QML
   dependency the way repositories never did.
7. **Financial Decimal values stay Decimal inside the reader and the application result — the
   desktop DTO's representation is explicitly out of scope for this guardrail in Phase 1.** Scoped
   narrowly and in two layers, not one: (a) once `FinanceSnapshotFacts` exists, assert its monetary
   fields are `Decimal`; (b) assert `FinanceService.get_finance_snapshot`'s returned
   `FinanceSnapshot` also keeps those fields `Decimal` internally. **Do not** assert anything about
   `FinancialSnapshotDto`'s field types in Phase 1 — that DTO is deliberately unchanged (`float`,
   per the QML-parity requirement in §17) until the separate, later Decimal-desktop-DTO migration
   (§18 Phase 5) exists to consciously replace it. A guardrail that required Decimal all the way to
   the desktop DTO today would contradict the Phase 1 "DTO unchanged" guarantee — this is the fix
   for that exact contradiction, flagged during review.
8. **Tenant and organization scope is mandatory for every reader.** For every method on a
   `contracts/reads/**` `Protocol`, assert its signature includes explicit `tenant_id`/
   `organization_id` parameters (mirroring `RateResolutionReader`'s existing shape) — mechanically
   checkable via `inspect.signature`.
9. **SQL projection results are immutable facts.** Assert every dataclass under
   `contracts/reads/*/models/` is `frozen=True` (mirroring the existing convention already used by
   `RateSelectionSnapshot`, `RateResolutionBatch`, etc.).
10. **No broad exception handling turns authorization/infrastructure errors into empty data — for
    readers specifically.** Assert no `SqlAlchemy*Reader` class contains a bare `except Exception:
    return`/`except Exception: return ()` — this mirrors a confirmed problem pattern found
    repeatedly in the *desktop-API* layer (§5, §6) and must not be reintroduced in the new
    infrastructure layer.
11. **Query-count and timing budgets exist for migrated read endpoints — scoped to the redundant
    finance-domain calls, not total SQL statement count.** Phase 0's actual measurement (above)
    found `get_finance_snapshot`'s **total** SQL statement count is 164 (small fixture) to 752
    (large fixture), overwhelmingly dominated by `organizations`/`tenants` scope-lookup queries
    unrelated to this pilot's own redundancy (53-64% of all statements, scaling with resource
    count). A budget phrased as "≤ N total statements" would therefore be meaningless or
    unachievable depending on N — this document's earlier illustrative "≤ 6" was never about total
    statements; it meant the six *named, finance-domain-specific* redundant call groups §7's
    canonical table tracks (`cost_repo.list_by_project`, `project_resource_repo.list_by_project`,
    `task_repo.list_by_project`, `project_repo.get`, `rate_resolver.resolve_many`,
    `LaborCostEngine.calculate_project_labor_details`), each measured at 5/3/4/6/6/3 calls today and
    targeted to collapse to 1 each post-Phase-1. **The guardrail must assert against these named
    call counts specifically** (mirroring `test_finance_snapshot_phase0_measurement.py`'s own
    instrumentation technique), not a bare total-statement-count assertion, or it will either pass
    trivially (a generous total budget) or fail for reasons having nothing to do with the pilot (the
    tenant/org lookup volume). A separate, explicit decision (§20 open question 4) is still needed
    on whether total-statement/timing budgets are worth adding on top of this, and if so, at what
    number, informed by Phase 0's measured baseline above.
12. **`contracts/**` must not import `application/**`.** A blanket, mechanically-checkable
    import-direction test — the specific fix for the circular-dependency mistake found and corrected
    in this document's own first draft (§15b, §16). This is broader than guardrail 1 (which checks
    return-type annotations specifically): this one checks the import statements themselves, in
    every file under `contracts/`, not only in `Reader` classes.
13. **Desktop adapter modules must not access attributes beginning with `_` on injected services.**
    Grep-based: no `api/desktop/**` file accesses `<service>._<name>`. This is the specific,
    enforceable fix for the private-attribute-access pattern consolidated in "Desktop Adapter
    Boundary Weaknesses" after §14 — existing occurrences are grandfathered; no new one is
    permitted.
14. **Desktop adapters must not instantiate application services.** Grep/AST-based: no
    `api/desktop/**` file calls a constructor of a class defined under `application/**`. Targets the
    `resolve_availability_service()` pattern specifically (§5, "Desktop Adapter Boundary
    Weaknesses").
15. **Desktop adapters must not import persistence repositories or ORM.** No `api/desktop/**` file
    imports from `contracts.repositories.**`, `infrastructure.persistence.repositories.**`, or
    `infrastructure.persistence.orm.**`.
16. **New desktop methods must not use reflection to silently discard unsupported arguments.** No
    *new* call site of `call_with_supported_kwargs` (or an equivalent `inspect.signature`-based
    filtering pattern) may be added after this guardrail lands — existing call sites in
    `api/desktop/projects/**` are grandfathered ("Composition weaknesses" note after §14).
17. **New broad exception-to-empty-result behavior is forbidden.** Extends guardrail 10 beyond
    `Reader` classes: no *new* `except Exception: return`/`except Exception: return ()`/
    `except Exception: return {}` pattern may be added anywhere under `api/desktop/**` or
    `contracts/reads/**` — existing occurrences catalogued in "Desktop Adapter Boundary Weaknesses"
    are grandfathered, not retroactively required to change.
18. **Reader SQL statements must include explicit tenant/organization/project predicates in every
    source CTE/subquery, not only the outer statement.** Distinct from guardrail 8 (which checks the
    `Protocol` method *signature*) — this checks the actual SQL text/construction for the
    multi-source aggregation hazard described in §17's SQL-multiplication note.
19. **Independent aggregate sources must be aggregated separately before being joined.** A
    structural check (or, where full static verification isn't practical, a documented,
    reviewer-enforced rule backed by the required parity-matrix row 15, §17) that a `Reader`'s
    statement design aggregates each source (cost items, project resources, assignments, etc.) on
    its own before combining already-aggregated, one-row-per-project results — never joins raw rows
    across sources ahead of a `SUM`.
20. **`FinanceSnapshotFacts` must not import `application/**`, `api/desktop/**`,
    `infrastructure.persistence.orm.**`, or `sqlalchemy`.** The concrete, file-specific instance of
    guardrail 1's dependency-direction rule for this pilot's own new type.
21. **`CostPolicyEngine` remains the policy owner; `FinanceService` must not duplicate its
    reconciliation rules.** A code-review-enforced rule (and, where practical, a static check that
    `finance_service.py` contains no manual/computed-labor de-duplication logic of its own) — the
    direct enforcement of §15b's fixed ownership decision.
22. **The Finance Reader must not reference `ProjectPlannedCostVersion` as the authoritative planned
    source.** No `contracts/reads/financials/**` or `infrastructure/persistence/reads/financials/**`
    file imports `ProjectPlannedCostVersion`/`ProjectPlannedCostLine` — the enforcement of §17's
    planned-cost-semantics non-goal.
23. **The Phase 1 runtime-composition test must exist and must prove the concrete `Reader` is
    actually injected**, not merely importable — see the "Composition weaknesses" note after §14
    and §17's required test list.
24. **`RateResolutionReader` under `contracts/repositories/rate_resolution.py` is explicitly
    grandfathered** — the location-inconsistency note immediately below explains why it is not
    moved during this phase, and no guardrail in this section should be written in a way that would
    fail against it.

### Existing Reader-location inconsistency (recorded, not resolved)

The production precedent this whole pilot is modeled on, `RateResolutionReader`, lives at
`contracts/repositories/rate_resolution.py` — inside `repositories/`, not under a `reads/`
subfolder — while this pilot's new convention is `contracts/reads/<capability>/`. This is an
honest, acknowledged inconsistency, not an oversight to paper over: **`RateResolutionReader` is not
moved during Phase 1.** It is classified as a grandfathered existing reader (guardrail 24 above),
and a later cleanup decision — not scheduled by this document — must choose one of:

- move `RateResolutionReader` to `contracts/reads/rate_resolution/`, with compatibility
  re-exports and tests proving no import site broke; or
- document explicitly why it remains permanently under `repositories/` (e.g. because it predates
  the `reads/` convention and every current consumer already depends on its existing path, making a
  move pure churn with no behavioral benefit).

**This document does not leave two unexplained, permanent Reader locations** — it explains the one
that exists today, defers the decision on unifying it, and records that deferral as §20 open
question 6.

---

## 20. Open questions and decisions

These require an explicit decision before further implementation — none are silently resolved by
this document:

1. **The `report.view` vs. `finance.read`/`finance.read_sensitive` permission split (§14 P0).**
   Should `ReportingService` be migrated onto the same `finance.read`/`finance.read_sensitive` gates
   `FinanceService` already uses (tightening access for existing `report.view`-only users), or
   should a `report.view`-holder's existing access be explicitly grandfathered via a role-migration
   step (mirroring the pattern already used for the `cost.manage`-umbrella permission migration
   documented elsewhere in this codebase's finance-modernization history)? This is a
   security/product decision, not an engineering one, and this audit deliberately does not choose
   for the team.
2. **Which of the two disagreeing BAC/AC sources (`CostPolicyEngine`'s policy-applied total vs.
   `ForecastCostService.compute_forecast`'s raw-`CostItem` total, §14 P1) is canonical?** Fixing
   `ForecastCostService` to route through `CostPolicyEngine` is straightforward engineering once
   this is decided, but the decision itself (does forecast intentionally want to ignore the
   manual/computed-labor de-duplication policy, or was this an unnoticed drift?) needs a product/
   architecture owner's sign-off before the fix is made.
3. **Is the second, parallel `src/tests/pm/` test suite (§13) meant to eventually replace
   `src/tests/project_management/`, or are both intentionally permanent?** This affects where the
   pilot's new tests (§17) should live — this audit placed them under
   `src/tests/project_management/` by default (matching the majority of existing financial-area
   tests), but that default should be confirmed, not assumed, given the ambiguity found.
4. **What is an acceptable query-count budget for `get_finance_snapshot` post-Phase-1 (§19,
   guardrail 11)?** Phase 0 has now run and measured the real baseline (§18): each of the six named
   finance-domain call groups (`cost_repo.list_by_project`, `project_resource_repo.list_by_project`,
   `task_repo.list_by_project`, `project_repo.get`, `rate_resolver.resolve_many`,
   `LaborCostEngine.calculate_project_labor_details`) is called 5/3/4/6/6/3 times today,
   size-independent — the natural post-Phase-1 target is 1 call each. **Still open**: whether to
   additionally budget total SQL statement count and/or wall-clock time, given the measured total
   (164-752 statements depending on fixture size) is dominated by `organizations`/`tenants`
   scope-lookup queries this pilot does not target — see Phase 0's measured baseline and guardrail
   11's corrected wording for why a bare total-statement budget would be the wrong tool here.
5. **Should the current one-session-per-process model eventually be replaced by an
   operation-scoped session/Unit-of-Work, with repositories/services/readers all sharing one
   session per *operation* instead of one per *process* (§10)?** This is a legitimate future
   architectural direction, explicitly **not** decided or scheduled by this document, and
   explicitly **not** something the Finance Snapshot pilot should attempt — Phase 1 reuses today's
   shared session as a pragmatic, scope-limiting choice, not an endorsement of the current session
   lifetime as permanent.
6. **Should `RateResolutionReader` (currently under `contracts/repositories/rate_resolution.py`) be
   moved to `contracts/reads/rate_resolution/` to match this pilot's new convention, or should its
   current location under `repositories/` be documented as permanent (§19's "Existing Reader-location
   inconsistency" note)?** Not resolved by this document; `RateResolutionReader` is explicitly
   grandfathered and unmoved for Phase 1 either way.

**Items formerly numbered 3 and 4 here (Portfolio permission and Portfolio/Collaboration rollback
scheduling) are no longer open questions** — Phase 0A (§18) already decided them. **A further item
formerly numbered 4 (whether the three Scheduling `services/*.py` files should be audited before any
Scheduling CQRS phase) is also no longer open** — they were opened and verified in the "Desktop
Adapter Responsibility Audit" section, so the question itself is resolved (see "Resolved Decisions"
immediately below for that one and the two Portfolio/Collaboration items); the same issue is not left
simultaneously marked as settled and as an unresolved scheduling decision.

---

## Resolved Decisions

Unlike §20 above, these are not open — Phase 0A's existence in the migration plan (§18) already
constitutes the decision. Recorded here so no reader mistakes them for still-pending questions.

**Resolved — Portfolio capacity-report permission.** Fix immediately as an independent Phase 0A
security correction (§18 Phase 0A.1). Not bundled with, and not waiting for, Portfolio CQRS or the
Finance Snapshot pilot.

**Resolved — Portfolio and Collaboration rollback.** Fix immediately as independent Phase 0A
reliability corrections (§18 Phase 0A.2 for Portfolio, Phase 0A.3 for Collaboration — kept as
separate commits and test sets per §15c's service-ownership note, even though both fix the same
class of defect). Not bundled with, and not waiting for, either capability's eventual CQRS
consideration (Phase 3C, Phase 3D).

**Resolved — CQRS relationship.** These two corrections neither require nor constitute CQRS. Adding
a Portfolio Reader would not fix the missing permission check (the check belongs in
`PortfolioResourcePoolService`, an application service, regardless of whether a Reader ever exists
for Portfolio's reads) and would not fix the missing rollback handling (transaction integrity is a
write-path property, orthogonal to how reads are structured). Portfolio CQRS/read-model work
remains deferred to Phase 3C, gated on the Phase 0A corrections being complete and on a measured
baseline justifying it (§18, §15c) — never as a side effect of, or a substitute for, either safety
fix.

**Resolved — Scheduling desktop-adapter verification.** The three Scheduling
`services/*.py` files and six `serializers/*.py` files this document originally flagged as unopened
were subsequently opened and verified in full in the "Desktop Adapter Responsibility Audit"
section. This is no longer an open question (it is removed from §20 accordingly): the files are
verified, their findings are folded into that section's master finding table, and Scheduling may now
be evaluated for a future CQRS phase on the same evidentiary footing as any other capability —
though §15c's own recommendation (stay mixed; the CPM engines are in-memory computation, not a
SQL-projection candidate) is unaffected by this closure, since the verification found adapter-layer
misplacement issues, not a read-redundancy case comparable to Finance Snapshot's.

---

## Approved Phase 1 Flow

The single, fixed call path and ownership split this pass locks in — every earlier ambiguity about
who calls the Reader, who owns policy, and what changes at the desktop boundary is resolved by this
diagram, not left open for implementation to decide. **The `FinanceService` line below is the
actual, current signature** (`application/financials/services/finance_service.py:118-124`),
**verified against the source, not a new signature Phase 1 introduces** — `as_of` and `period` are
already optional keyword parameters today, and `as_of`'s internal resolution (`as_of or
date.today()`) is a plain function call, not an injected `Clock` (this service has none — confirmed
against its constructor, `finance_service.py:61-74`). Phase 1 must not accidentally turn `as_of`
into a new required positional parameter while claiming the signature is unchanged — it is already
optional, and stays that way:

```text
QML
  → unchanged

ProjectManagementFinancialsDesktopApi.get_finance_snapshot(project_id)
  → unchanged signature and DTO contract

FinanceService.get_finance_snapshot(project_id, *, as_of=None, period="month")
  → UNCHANGED signature — both kwargs already exist today, neither is added or removed
  → as_of = as_of or date.today()   # UNCHANGED — already resolved inline today, no Clock introduced
  → require finance.read
  → resolve tenant_id and organization_id
  → FinanceSnapshotReader.read_facts(
        tenant_id,
        organization_id,
        project_id,
        as_of
    )
  → LaborCostEngine.calculate_project_labor_details(...) once
  → CostPolicyEngine.compose_from_facts(...) once
  → build remaining ledger/cash-flow/analytics sections using the
    already-composed results rather than re-fetching (period passed through unchanged)
  → apply finance.read_sensitive redaction
  → existing FinanceSnapshot

snapshot_serializer
  → existing FinancialSnapshotDto

SqlAlchemyFinanceSnapshotReader
  → execute scoped SQLAlchemy Core statements
  → aggregate independent sources without row multiplication
  → return immutable FinanceSnapshotFacts
  → no domain entities returned
  → no ORM objects returned
  → no permission checks
  → no redaction
  → no rate precedence policy
  → no planned-source policy
  → no commit
```

Every line above is now consistent with §15b's ownership fix, §16's dependency direction, §17's
pilot scope, and §19's guardrails — this section exists so the approved flow can be read once, on
its own, without cross-referencing four other sections to reconstruct it.

---

## Final acceptance checklist

- **How does every major desktop PM request reach the database?** §4a (bootstrap chain), §6
  (write traces), §7 (read traces) — traced end-to-end for every capability with concrete file:line
  evidence.
- **Which concrete implementations are actually composed at runtime?** §4b's Runtime object table
  — every repository/service mapped to its concrete class and construction site.
- **Where do commits, flushes and rollbacks occur?** §10, with the full call-site tabulation and the
  two confirmed no-rollback-anywhere capability areas (Portfolio, Collaboration).
- **Which methods return domain entities to the desktop API?** §8 — the dominant write-path shape,
  confirmed never to leak an ORM object.
- **Which reads hydrate ORM/domain graphs?** §7, every trace shows full-list materialization before
  any Python-side aggregation.
- **Which calculations happen in Python instead of SQL?** §9c (module-wide: all of them, zero SQL
  aggregation found) and §7's per-method call-out.
- **Which repositories mix command and reporting concerns?** §9a's fat-repository ranking.
- **Which DTO types exist at each boundary?** §8's full model-boundary map.
- **Which services have fallback or duplicated implementations?** §14 P1/P2, and the two-parallel-
  leveling-engines / four-parallel-CPM-date-arithmetic findings.
- **How are tenant, organization, permissions, RLS, audit and events enforced?** §11, §12.
- **What exact repository structure should CQRS use here?** §16, scoped to `financials/` only, with
  every folder's dependency rules stated.
- **What is the safest first DB-to-desktop-API CQRS pilot?** §17 — Finance Snapshot, with full
  scoring against 4 alternatives.
- **Which QML changes are deliberately deferred?** §17's exclusion list, §18 Phase 5.
- **What tests and measurements prove the migration is safe?** §17's required test list, §18
  Phase 0's baseline-measurement requirement, §19's query-count guardrail.
- **Is every Portfolio-facing cross-project capacity report protected by an explicit
  application-layer permission?** Yes - completed and verified in Phase 0A.1 (§18).
- **Do all Portfolio command methods roll back after repository or commit failure?** Yes - completed
  and verified in Phase 0A.2 (§18).
- **Is the shared `Session` reusable after an injected Portfolio failure?** Yes - Phase 0A.2's
  failure-injection coverage verifies reuse after rollback.
- **Are failure events suppressed on a rolled-back Portfolio write?** Yes - Phase 0A.2 verifies no
  `portfolio_changed`/activity success event is emitted after forced failure.
- **Do PM repositories hydrate full tenant/organization entities for SQL scope predicates?** No -
  Phase 0C replaced that path with validated `ActiveScopeIds` and added a repository-package
  architecture guard.
- **Are desktop DTOs and QML unchanged by the Portfolio safety corrections?** Yes, by design —
  Phase 0A.1/0A.2 add permission and rollback handling only; §15c's Approved Flow note confirms no
  desktop-API signature or DTO change.
- **Is Portfolio CQRS still deferred until measured Phase 3C work?** Yes — §15c and §18 Phase 3C
  both state this explicitly, and it is one of the three items in "Resolved Decisions" above.

---

## Terminal summary

```text
Document path: docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md
Desktop API methods inventoried: ~150 across 10 capability classes (Projects, Tasks, Resources,
  Scheduling, Financials, Portfolio, Register/Risk [same instance, two registry keys], Timesheets,
  Dashboard, Collaboration)
Write flows traced in full: 11 (create/update/delete project; create/update task; task progress
  transition; resource/project-resource mutation; assignment mutation incl. the dual-commit bridge
  path; financial profile mutation; budget create/submit/approve incl. governed split; rate-card
  line mutation; planned-cost snapshot creation; the generalized governed/ungoverned pattern across
  Cost/Budget/TaskDependency/Baseline)
Read flows traced in full: 10 (project list/details; project dashboard; portfolio dashboard/
  heatmap; finance snapshot [primary]; EVM series; task list/tree/board; resource utilization pool;
  cross-task assignments; scheduling/calendar; budget/rate-card/planned-cost totals; report/export
  reads)
Recommended first CQRS pilot: Finance Snapshot (FinanceService.get_finance_snapshot) — a
  FinanceSnapshotReader returning source-oriented FinanceSnapshotFacts (colocated under
  contracts/reads/, not application/, to avoid a circular dependency), with FinanceService as the
  sole caller/orchestrator/redactor, LaborCostEngine as the sole labor calculator (called once, not
  three times), and CostPolicyEngine retained unconditionally as the manual/computed-labor and
  planned-cost policy owner via a new compose_from_facts(...) entry point — replacing a confirmed
  5x/3x/6x-redundant repository-call chain (§7's canonical table). Modeled directly on the existing
  RateResolutionReader precedent already live in this codebase.
Top five architecture risks:
  1. Two non-overlapping permission systems (report.view vs finance.read/finance.read_sensitive)
     gate the same financial data with no redaction on one side (P0, security).
  2. PortfolioResourcePoolService originally had no permission check on a cross-project report
     (P0, security; remediated in Phase 0A.1).
  3. Portfolio and Collaboration originally committed writes without complete rollback handling
     (P0, reliability; remediated in Phases 0A.2/0A.3).
  4. FinanceService.get_finance_snapshot's confirmed, call-count-verified redundant computation
     (P1, performance — the pilot's own justification).
  5. Zero SQL-side aggregation anywhere in the persistence layer, module-wide (P1, systemic
     performance root cause).
Areas that could not be fully verified in this original pass, since closed:
  - Three Scheduling desktop-API service files (scheduling_facade_service.py,
    dependency_resolution_service.py, calendar_adapter_service.py) were not opened in this pass —
    subsequently opened and verified in the "Desktop Adapter Responsibility Audit" section below.
  - Six Scheduling desktop-API serializer files were not opened in this pass — same closure.
Areas that remain genuinely unverified as of this document's latest revision:
  - SQLite wall-clock and SQL-count baselines exist for get_finance_snapshot (Phases 0/0B/0C), but
    the same measurement has not yet been run against hosted PostgreSQL with RLS enabled.
  - Whether Dashboard's `_build_high_risks_table` and Register's own filtered list actually disagree
    in practice today (a flagged risk, not a confirmed live bug — see the Desktop Adapter Audit's
    own Terminal Summary).
  - Whether any real calendar in the current dataset has non-uniform per-weekday hours (same source).
```

---

## Appendix A — Complete desktop API method inventory (added in correction pass)

§5 showed representative rows per capability, matching the original request's request for a table
but not reproducing every method inline for the largest capabilities. This appendix is the
complete, exhaustive inventory — every public method on every one of the ten desktop API classes,
with the same columns §5 uses. Projects is omitted here because §5 already lists it in full.

### Tasks — `ProjectManagementTasksDesktopApi` (26 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_projects` | none | `TaskProjectOptionDescriptor[]` | `access_resolution_service.project_rows_for_task_scope` → `ProjectService.list_projects` (+ private-repo fallback) | LOOKUP/QUERY | `presenters/tasks/filtering.py:22` |
| `list_statuses` | none | `TaskStatusDescriptor[]` | none (enum) | LOOKUP | `presenters/tasks/filtering.py:25` |
| `list_project_resources` | `project_id` | `TaskProjectResourceOptionDescriptor[]` | `ProjectResourceService.list_by_project` + `ResourceService.list_resources` (+ private-repo fallback) | QUERY | `presenters/tasks/assignment_mapper.py:42` |
| `get_task` | `task_id` | `TaskDesktopDto \| None` | `TaskService.get_task` + full project re-serialization scan | QUERY | `presenters/tasks/utils.py:55`, `collaboration_builder.py:97` |
| `list_dependency_types` | none | `TaskDependencyTypeDescriptor[]` | none (enum) | LOOKUP | `presenters/tasks/dependency_mapper.py:40` |
| `list_tasks` | `project_id` | `TaskDesktopDto[]` | `TaskService.list_task_hierarchy`/`list_task_hierarchy_rollups` or `list_tasks_for_project` | QUERY | `presenters/financials/workspace_builder.py:50`, `tasks/utils.py:28`, `task_command_handler.py:28`, `projects/tasks_builder.py:23` |
| `list_all_tasks` | none | `TaskDesktopDto[]` | per-project `_serialize_project_tasks` loop | QUERY (N+1) | `presenters/tasks/utils.py:29` |
| `create_task` | `TaskCreateCommand` | `TaskDesktopDto` | `TaskService.create_task` + conditional `set_status`/`get_task` | COMMAND | `task_command_handler.py:55` → `tasks_workspace_controller.py:565`, `pm_task_list_controller.py:247` |
| `move_task` | `TaskWbsMoveCommand` | `TaskDesktopDto` | `TaskService.move_task` + reload | COMMAND | `task_command_handler.py:74` |
| `update_task` | `TaskUpdateCommand` | `TaskDesktopDto` | `TaskService.get_task` (pre-read) + `update_task` + conditional `set_status` | MIXED | `task_command_handler.py:70` → `tasks_workspace_controller.py:569`, `pm_task_list_controller.py:258` |
| `update_progress` | `TaskProgressCommand` | `TaskDesktopDto` | `TaskService.update_progress` | COMMAND | `task_command_handler.py:96` → `tasks_workspace_controller.py:577`, `pm_task_list_controller.py:280` |
| `list_assignments` | `task_id` | `TaskAssignmentDesktopDto[]` | `TaskService.list_assignments_for_task` + `resource_by_id` + per-assignment `get_assignment_action_context` | QUERY (N+1) | `presenters/timesheets/workspace_builder.py:43`, `tasks/assignments_builder.py:83`, `time_builder.py:137` |
| `create_assignment` | `TaskAssignmentCreateCommand` | `TaskAssignmentDesktopDto` | `TaskService.assign_project_resource` | COMMAND | `assignment_command_handler.py:26` → `tasks_workspace_controller.py:601`, `pm_assignment_controller.py:103` |
| `update_assignment_allocation` | `TaskAssignmentAllocationCommand` | `TaskAssignmentDesktopDto` | `TaskService.set_assignment_allocation` | COMMAND | `assignment_command_handler.py:39` |
| `set_assignment_hours` | `TaskAssignmentHoursCommand` | `TaskAssignmentDesktopDto` | `TaskService.set_assignment_hours` | COMMAND | `assignment_command_handler.py:50` |
| `delete_assignment` | `assignment_id` | none | `TaskService.unassign_resource` | COMMAND | `assignment_command_handler.py:56` |
| `accept_assignment` | `assignment_id` | `TaskAssignmentDesktopDto` | `TaskService.accept_assignment` | COMMAND | `assignment_command_handler.py:62` |
| `decline_assignment` | `assignment_id, reason` | `TaskAssignmentDesktopDto` | `TaskService.decline_assignment` | COMMAND | `assignment_command_handler.py:75` |
| `list_dependencies` | `task_id` | `TaskDependencyDesktopDto[]` | `TaskService.list_dependencies_for_task` + full-project task fetch for names | QUERY | `presenters/tasks/dependencies_builder.py:88` |
| `create_dependency` | `TaskDependencyCreateCommand` | `TaskDependencyDesktopDto` | `TaskService.add_dependency` | COMMAND | `dependency_command_handler.py:28` → `tasks_workspace_controller.py:629`, `pm_dependency_controller.py:85` |
| `update_dependency` | `TaskDependencyUpdateCommand` | none | `TaskService.update_dependency` | COMMAND | `dependency_command_handler.py:36` |
| `delete_dependency` | `dependency_id` | none | `TaskService.remove_dependency` | COMMAND | `dependency_command_handler.py:48` |
| `delete_task` | `task_id` | none | `TaskService.delete_task` | COMMAND | `tasks_workspace_controller.py:581`, `pm_task_list_controller.py:291` |
| `apply_bulk_status` | `TaskBulkStatusCommand` | `TaskDesktopDto[]` | `TaskService.set_tasks_status` | COMMAND (bulk) | `task_command_handler.py:106` |
| `delete_tasks` | `task_ids` | `str[]` | `TaskService.delete_tasks` | COMMAND (bulk) | `task_command_handler.py:120` |
| `list_task_reservations` | `task_id` | `TaskReservationDesktopDto[]` | duck-typed `reservation_service.list_reservations` (500-row cap, filtered client-side) | QUERY/INTEGRATION | not found |
| `create_task_reservation` | `TaskReservationCreateCommand` | `TaskReservationDesktopDto` | `TaskService.get_task` + `reservation_service.create_reservation` | COMMAND/INTEGRATION | not found |
| `get_task_material_demand` | `task_id` | `TaskMaterialDemandSummary` | `list_task_reservations` + Python bucket sums | REPORT | `presenters/tasks/detail_builder.py:26` |
| `list_task_skill_requirements` | `task_id` | `TaskSkillRequirementDesktopDto[]` | `AssignmentSkillValidator.list_requirements` | QUERY | `presenters/tasks/skill_requirements_builder.py:55` |
| `validate_assignment` | `task_id, project_resource_id` | `AssignmentValidationDesktopDto` | `AssignmentSkillValidator.validate/.summary()` | QUERY | `assignment_command_handler.py:126` |
| `preview_assignment` | `task_id, project_resource_id` | `AssignmentPreviewDesktopDto` | `ResourceAvailabilityService.is_resource_available` + `AssignmentSkillValidator.validate` + per-conflict `get_task` (N+1) | QUERY/REPORT | `assignment_command_handler.py:96` |
| `get_schedule_impact` | `task_id, project_id` | `ScheduleImpactReportDto` | `ScheduleChangeImpactService.analyse` (hardcoded 1-day-delay scenario) | REPORT | `presenters/tasks/schedule_impact_builder.py:28` |

### Resources — `ProjectManagementResourcesDesktopApi` (14 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_worker_types` | none | `ResourceWorkerTypeDescriptor[]` | none (enum) | LOOKUP | not verified |
| `list_categories` | none | `ResourceCategoryDescriptor[]` | none (enum) | LOOKUP | not verified |
| `list_employees` | none | `ResourceEmployeeOptionDescriptor[]` | `EmployeeService.list_employees` | QUERY/LOOKUP | not verified |
| `list_resources` | none | `ResourceDesktopDto[]` | `ResourceService.list_resources` | QUERY | not verified |
| `create_resource` | `ResourceCreateCommand` | `ResourceDesktopDto` | `ResourceService.create_resource` | COMMAND | not verified |
| `update_resource` | `ResourceUpdateCommand` | `ResourceDesktopDto` | `ResourceService.get_resource` (pre-read, rate-change decision computed in API layer) + `update_resource` | MIXED | not verified |
| `toggle_resource_active` | `resource_id, expected_version` | `ResourceDesktopDto` | `ResourceService.get_resource` + `update_resource` | MIXED | not verified |
| `delete_resource` | `resource_id` | none | `ResourceService.delete_resource` | COMMAND | not verified |
| `list_resource_skills` | `resource_id` | `ResourceSkillDesktopDto[]` | `ResourceService.list_resource_skills` | QUERY | not verified |
| `list_resource_certifications` | `resource_id` | `ResourceCertificationDesktopDto[]` | `ResourceService.list_resource_certifications` (serializer computes `cert_status` business rule) | QUERY | not verified |
| `add_resource_skill` | `ResourceAddSkillCommand` | `ResourceSkillDesktopDto` | `ResourceService.add_resource_skill` | COMMAND | not verified |
| `remove_resource_skill` | `skill_id` | none | `ResourceService.remove_resource_skill` | COMMAND | not verified |
| `add_resource_certification` | `ResourceAddCertificationCommand` | `ResourceCertificationDesktopDto` | `ResourceService.add_resource_certification` | COMMAND | not verified |
| `remove_resource_certification` | `cert_id` | none | `ResourceService.remove_resource_certification` | COMMAND | not verified |
| `list_resource_assignments` | `resource_id` | `ResourceAssignmentDesktopDto[]` | `AssignmentRepository.list_by_resource` + `TaskService.list_tasks_for_resource` + `ProjectService.get_project` (manual 3-way join; private-attribute fallback) | QUERY/REPORT | not verified |
| `build_resource_availability` | `resource_id` | `ResourceAvailabilityDto \| None` | `resolve_availability_service()` (may construct a new `ResourceAvailabilityService` from private attrs) + `check_availability` | QUERY | not verified |

*(QML consumer attribution for Resources was not run in the sub-audit that produced this table — see §3a's gap flag; treat the "not verified" cells as an honest gap, not an omission.)*

### Scheduling — `ProjectManagementSchedulingDesktopApi` (24 methods)

*(This table was originally written before `scheduling_facade_service.py`,
`dependency_resolution_service.py`, `calendar_adapter_service.py`, and the 6 serializer files were
opened — several "Notes" cells below still say "internals unverified"/"facade internals
unverified" as a result. Those files were subsequently opened and verified in full in the "Desktop
Adapter Responsibility Audit" section; see that section's per-file tables for the actual verified
behavior rather than treating the "unverified" notes below as still accurate.)*

| Method | Input | Output | Service called | Classification | Notes |
|---|---|---|---|---|---|
| `list_projects` | none | `SchedulingProjectOptionDescriptor[]` | `ProjectService.list_projects` | LOOKUP | — |
| `list_activity_options` | `project_id, exclude_task_id` | descriptor[] | `TaskService.list_leaf_tasks_for_project`/`list_tasks_for_project` | LOOKUP | — |
| `list_calendars` | none | `SchedulingCalendarOptionDescriptor[]` | `calendar_adapter_service.list_platform_calendar_options` or legacy path | LOOKUP/INTEGRATION | dual-path fallback, adapter internals unverified |
| `get_calendar_snapshot` | `calendar_id` | `SchedulingCalendarSnapshotDto` | `calendar_adapter_service` (platform or legacy) | QUERY/INTEGRATION | adapter internals unverified |
| `update_calendar` | `SchedulingCalendarUpdateCommand` | `SchedulingCalendarSnapshotDto` | `calendar_adapter_service.update_platform_calendar_working_days`, else no-op returning unchanged snapshot | COMMAND degrading to no-op | "moved to Platform Admin" legacy stub |
| `add_holiday` | `SchedulingHolidayCreateCommand` | `SchedulingHolidayDto` | platform calendar API, else fabricates an unpersisted DTO inline | COMMAND degrading to fake response | — |
| `delete_holiday` | `holiday_id` | none | platform calendar API, else `pass` | COMMAND, silent no-op fallback | — |
| `calculate_working_days` | `SchedulingWorkingDayCalculationCommand` | `SchedulingWorkingDayCalculationDto` | platform calendar API or `CalendarProtocol.add_working_days` | MIXED/INTEGRATION | real calendar arithmetic performed **in the API layer** (`_date_range` helper defined in `api.py`) |
| `list_dependency_types` | none | `SchedulingDependencyTypeDescriptor[]` | none (enum) | LOOKUP | — |
| `list_project_dependencies` | `project_id` | `SchedulingProjectDependencyDto[]` | `TaskService.list_tasks_for_project` + per-task `list_dependencies_for_task` | QUERY (N+1, inline in api.py) | bypasses the builder/serializer pattern used elsewhere in this file |
| `list_dependencies` | `task_id` | `SchedulingDependencyDto[]` | `TaskService.get_task/list_tasks_for_project/list_dependencies_for_task` | QUERY | — |
| `create_dependency` | `SchedulingDependencyCreateCommand` | `SchedulingDependencyDto` | `TaskService.add_dependency` | COMMAND | — |
| `update_dependency` | `SchedulingDependencyUpdateCommand, current_task_id` | `SchedulingDependencyDto` | `TaskService.update_dependency` | COMMAND | unusual out-of-band `current_task_id` kwarg |
| `delete_dependency` | `dependency_id` | none | `TaskService.remove_dependency` | COMMAND | — |
| `list_schedule` | `project_id` | `SchedulingTaskDto[]` | `scheduling_facade_service.build_schedule_from_tasks`/`build_schedule_from_engine` | QUERY | facade internals unverified |
| `recalculate_schedule` | `project_id` | `SchedulingTaskDto[]` | `build_schedule_from_engine(persist=True)` | COMMAND | facade internals unverified |
| `list_baselines` | `project_id` | `SchedulingBaselineOptionDescriptor[]` | `BaselineService.list_baselines` | LOOKUP | — |
| `list_baseline_rows` | `project_id` | `SchedulingBaselineRowDto[]` | `BaselineService.list_baselines` + `format_baseline_row` | QUERY | — |
| `create_baseline` | `SchedulingBaselineCreateCommand` | `SchedulingBaselineOptionDescriptor` | `BaselineService.create_baseline(rate_as_of=date.today())` | COMMAND | `rate_as_of` deliberately resolved in the API layer, by design comment |
| `submit_baseline`/`approve_baseline`/`reject_baseline`/`delete_baseline` | commands/id | none | `BaselineService.submit/approve/reject/delete_baseline` | COMMAND | — |
| `list_baseline_variance_records` | `baseline_id` | `SchedulingBaselineVarianceRowDto[]` | `BaselineService.list_variance_records` | QUERY | — |
| `compare_baselines` | `project_id, baseline_a_id, baseline_b_id, include_unchanged` | `SchedulingBaselineComparisonRowDto[]` | `ReportingService.compare_baselines` | REPORT | DTO built inline in `api.py`, not via a builder |
| `list_resource_load` | `project_id` | `SchedulingResourceLoadDto[]` | `ReportingService.get_resource_load_summary` | REPORT | — |
| `list_constraint_violations` | `project_id` | `SchedulingConstraintViolationDto[]` | `SchedulingEngine.recalculate_project_schedule(persist=False)` + `ConstraintValidator.validate` | REPORT/QUERY | broad except swallows both recompute and validation errors together |
| `analyse_change_impact` | `project_id, task_id, proposed_*` | `SchedulingChangeImpactDto \| None` | `BaselineService.get_approved_baseline` + `ScheduleChangeImpactService.analyse` | REPORT | two nested broad-except-to-fallback blocks; a second, apparently-dead `compute_schedule_impact` function exists in the same builder file but is not called from `api.py` |

### Financials — `ProjectManagementFinancialsDesktopApi` (12 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_projects` | none | `FinancialProjectOptionDescriptor[]` | `ProjectService.list_projects` | LOOKUP | `presenters/financials/workspace_builder.py:36` |
| `list_cost_types` | none | `FinancialCostTypeDescriptor[]` | none (enum) | LOOKUP | `workspace_builder.py:43` |
| `list_tasks` | `project_id` | `FinancialTaskOptionDescriptor[]` | `TaskService.list_task_hierarchy`/`list_tasks_for_project` | QUERY | `workspace_builder.py:50` |
| `list_cost_items` | `project_id` | `FinancialCostItemDto[]` | `CostService.list_cost_items_for_project` (+ nested `list_tasks` call for name lookup) | QUERY | `workspace_builder.py:55`, `command_handler.py:29` |
| `create_cost_item` | `FinancialCreateCommand` | `FinancialCostItemDto` | `CostService.add_cost_item` | COMMAND | `command_handler.py:55` |
| `update_cost_item` | `FinancialUpdateCommand` | `FinancialCostItemDto` | `CostService.update_cost_item` | COMMAND | `command_handler.py:74` |
| `delete_cost_item` | `cost_id` | none | `CostService.delete_cost_item` | COMMAND | `command_handler.py:83` |
| `get_finance_snapshot` | `project_id` | `FinancialSnapshotDto` | `FinanceService.get_finance_snapshot` | **REPORT** (pilot target, §17) | `workspace_builder.py:67` |
| `get_cost_forecast` | `project_id, percent_complete, method, threshold_percent` | `FinancialForecastDto` | `ForecastCostService.compute_forecast` + `ProjectService.get_project` | REPORT | `workspace_builder.py:76,139` |
| `get_commitment_summary` | `project_id` | `FinancialCommitmentSummaryDto` | `ForecastCostService.get_commitment_summary` | REPORT | `workspace_builder.py:113` |
| `list_project_requisitions` | `project_id` | `ProjectRequisitionDesktopDto[]` | duck-typed `procurement_service.list_requisitions` (500-row cap) | INTEGRATION | **confirmed no QML consumer anywhere** |
| `get_project_procurement_commitments` | `project_id` | `ProjectProcurementCommitmentSummary` | internal `list_project_requisitions` call only — no backing service method | MIXED/REPORT | **confirmed no QML consumer anywhere** |
| `build_baseline_variance` | `project_id` | `BaselineVarianceRecordDto[]` | `BaselineService.get_approved_baseline` + `list_variance_records` | QUERY | `workspace_builder.py:125` |

### Portfolio — `ProjectManagementPortfolioDesktopApi` (18 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_projects` | none | `PortfolioProjectOptionDescriptor[]` | `ProjectService.list_projects` | LOOKUP | `workspace_builder.py:57` |
| `list_intake_statuses` | none | descriptor[] | none (enum) | LOOKUP | `workspace_builder.py:48` |
| `list_dependency_types` | none | descriptor[] | none (enum) | LOOKUP | `workspace_builder.py:65` |
| `list_templates` | none | `PortfolioTemplateDesktopDto[]` | `PortfolioService.list_scoring_templates` | QUERY | `workspace_builder.py:38` |
| `list_intake_items` | `status` | `PortfolioIntakeDesktopDto[]` | `PortfolioService.list_intake_items` | QUERY | `workspace_builder.py:39` |
| `list_scenarios` | none | `PortfolioScenarioDesktopDto[]` | `PortfolioService.list_scenarios` | QUERY | `workspace_builder.py:40` |
| `evaluate_scenario` | `scenario_id` | `PortfolioScenarioEvaluationDesktopDto` | `PortfolioService.evaluate_scenario` | REPORT | `evaluation_builder.py:21` |
| `compare_scenarios` | `base_id, candidate_id` | `PortfolioScenarioComparisonDesktopDto` | `PortfolioService.compare_scenarios` | REPORT | `comparison_builder.py:23` |
| `list_heatmap` | none | `PortfolioHeatmapDesktopDto[]` | `PortfolioService.list_portfolio_heatmap` | REPORT (N+1, §7) | `workspace_builder.py:41` |
| `list_dependencies` | none | `PortfolioDependencyDesktopDto[]` | `PortfolioService.list_project_dependencies` | QUERY | `workspace_builder.py:42` |
| `list_recent_actions` | `limit` | `PortfolioRecentActionDesktopDto[]` | `PortfolioService.list_recent_pm_actions` | QUERY | `workspace_builder.py:43` |
| `create_scoring_template` | `PortfolioTemplateCreateCommand` | `PortfolioTemplateDesktopDto` | `PortfolioService.create_scoring_template` | COMMAND | `command_handler.py:35` |
| `activate_scoring_template` | `template_id` | `PortfolioTemplateDesktopDto` | `PortfolioService.activate_scoring_template` | COMMAND | `command_handler.py:44` |
| `create_intake_item` | `PortfolioIntakeCreateCommand` | `PortfolioIntakeDesktopDto` | `PortfolioService.create_intake_item` | COMMAND | `command_handler.py:64` |
| `create_scenario` | `PortfolioScenarioCreateCommand` | `PortfolioScenarioDesktopDto` | `PortfolioService.create_scenario` | COMMAND | `command_handler.py:78` |
| `create_project_dependency` | `PortfolioDependencyCreateCommand` | `PortfolioDependencyDesktopDto` | `PortfolioService.create_project_dependency` + a re-fetch-and-scan of all dependencies to find the new one | MIXED | `command_handler.py:98` |
| `remove_project_dependency` | `dependency_id` | none | `PortfolioService.remove_project_dependency` | COMMAND | `command_handler.py:107` |
| `update_intake_item_status` | `item_id, status` | `PortfolioIntakeDesktopDto` | `PortfolioService.update_intake_item` | COMMAND | `command_handler.py:117` |
| `build_capacity_pool` | none | `PortfolioCapacityResourceDto[]` | `PortfolioResourcePoolService.get_pool_report` (fixed 90-day window) | REPORT | `capacity_pool_builder.py:15` |

### Timesheets — `ProjectManagementTimesheetsDesktopApi` (14 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_projects` | none | `TimesheetProjectOptionDescriptor[]` | `ProjectService.list_projects` | LOOKUP | `workspace_builder.py:37` |
| `list_queue_statuses` | none | `TimesheetOptionDescriptor[]` | none (enum) | LOOKUP | `workspace_builder.py:50` |
| `list_assignments` | `project_id` | `TimesheetAssignmentOptionDescriptor[]` | `ProjectService`/`TaskService`/`ResourceService` nested loop join | LOOKUP (N+1-shaped) | `workspace_builder.py:43` |
| `build_assignment_snapshot` | `assignment_id, period_start` | `TimesheetAssignmentSnapshotDesktopDto` | `TaskService`/`ProjectService`/`ResourceService`/`TimesheetService` fan-out (6 calls) | QUERY | `workspace_builder.py:57` |
| `list_review_queue` | `status` | `TimesheetPeriodSummaryDesktopDto[]` | `TimesheetService.list_timesheet_review_queue` | QUERY | `workspace_builder.py:81` |
| `get_review_detail` | `period_id` | `TimesheetReviewDetailDesktopDto` | `TimesheetService.get_timesheet_review_detail` | QUERY | `review_builder.py:21` |
| `add_time_entry`/`update_time_entry`/`delete_time_entry` | commands/id | DTO/none | `TimesheetService.add/update/delete_time_entry` | COMMAND | `command_handler.py:23,35,44` |
| `submit_period`/`approve_period`/`reject_period`/`lock_period`/`unlock_period` | scalars | `TimesheetPeriodSummaryDesktopDto` | `TimesheetService.*_timesheet_period` + re-serialize (extra query) | MIXED | `command_handler.py:50,60,69,78,88` |

### Register/Risk — `ProjectManagementRegisterDesktopApi` (8 methods, single instance, two registry keys)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `list_projects` | none | `RegisterProjectOptionDescriptor[]` | `ProjectService.list_projects` | LOOKUP | `workspace_builder.py:78` |
| `list_entry_types`/`list_statuses`/`list_severities` | none | descriptor[] | none (enum) | LOOKUP | `workspace_builder.py:47,86,93` |
| `list_entries` | filters | `RegisterEntryDesktopDto[]` | `RegisterService.list_entries` + Python triage sort (`severity_rank`, `is_overdue`) | QUERY | `workspace_builder.py:73`, `command_handler.py:34` |
| `create_entry` | `RegisterEntryCreateCommand` | `RegisterEntryDesktopDto` | `RegisterService.create_entry` | COMMAND | `command_handler.py:68` |
| `update_entry` | `RegisterEntryUpdateCommand` | `RegisterEntryDesktopDto` | `RegisterService.update_entry` | COMMAND | `command_handler.py:99` |
| `delete_entry` | `entry_id` | none | `RegisterService.delete_entry` | COMMAND | `command_handler.py:108` |

### Dashboard — `ProjectManagementDashboardDesktopApi` (3 methods, one fans out to 6 services)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `build_empty_overview` | none | `ProjectDashboardOverviewDescriptor` | none (pure) | LOOKUP | `dashboard_presenter.py:23` |
| `build_overview_from_dashboard_data` | `project_name, dashboard_data` | `ProjectDashboardOverviewDescriptor` | none (transforms pre-fetched data) | REPORT | `dashboard_presenter.py:29` |
| `build_snapshot` | `project_id, baseline_id, period_key, view_key` | `ProjectDashboardSnapshotDescriptor` | `DashboardSnapshotService` → `DashboardService`, `ApprovalService`, `BaselineService` (×2, redundantly), `RegisterService`, `CollaborationService`, `ReportingService` | **REPORT** (§7 full pipeline trace) | `workspace_builder.py:28` |

### Collaboration — `ProjectManagementCollaborationDesktopApi` (10 methods)

| Method | Input | Output | Service called | Classification | QML consumer |
|---|---|---|---|---|---|
| `build_snapshot` | `limit` | `CollaborationWorkspaceSnapshotDto` | `CollaborationService.list_workspace_snapshot` | QUERY | `presenters/collaboration/workspace_builder.py:28` |
| `mark_task_mentions_read` | `task_id` | none | `CollaborationService.mark_task_mentions_read` | COMMAND | `presenters/collaboration/command_handler.py:14` |
| `touch_task_presence`/`clear_task_presence` | `task_id[, activity]` | none | `CollaborationService.touch/clear_task_presence` | COMMAND | `presenters/tasks/collaboration_command_handler.py:102,114` (not `presenters/collaboration/**`) |
| `build_task_snapshot` | `task_id` | `TaskCollaborationSnapshotDto` | `CollaborationService` 6-call fan-out (comments, action context, documents, presence, mentions, available documents) | QUERY | `presenters/tasks/collaboration_builder.py:100` |
| `post_task_comment`/`edit_task_comment`/`delete_task_comment`/`react_to_task_comment`/`remove_task_comment_reaction` | commands | `TaskCollaborationCommentDesktopDto` | `CollaborationService.post/edit/delete/react_to/remove_reaction` + `list_comment_documents` reload | MIXED | `presenters/tasks/collaboration_command_handler.py:28,44,58,73,82` (not `presenters/collaboration/**`) |

*Confirmed: 8 of these 10 methods are consumed exclusively from the Tasks-detail-panel presenter
tree, not from `presenters/collaboration/**` — "Collaboration" is primarily a Tasks-panel
dependency in practice, not a standalone workspace API.*

---

# Desktop Adapter Responsibility Audit

Added in this pass (document-only; no production code, QML, or DTO classes moved). Scope:
`src/core/modules/project_management/api/desktop/` — every `api.py`, `commands/`, `models/`,
`serializers/`, `builders/`, `services/`, `utils/`, `formatters/`, and desktop-runtime factory file.
**Desktop request/response DTOs stay exactly where they are** — this audit is about *behavior*
inside adapters, serializers, builders, helpers, and adapter services, never about relocating the
DTO classes themselves.

**Method.** Every finding below was verified by opening the actual implementation (not inferred
from a filename), following its call chain to the concrete collaborator it reaches, and checking
whether the same rule already exists elsewhere. Findings already fully verified in the original
audit (§5, §6, §7, "Desktop Adapter Boundary Weaknesses" after §14, Appendix A) are carried forward
with their existing citations. The nine Scheduling files the original audit explicitly flagged as
unverified — `services/scheduling_facade_service.py`, `services/dependency_resolution_service.py`,
`services/calendar_adapter_service.py`, and six `serializers/*.py` files — were opened for the first
time in this pass; their findings are new and are marked as such below.

**Explicitly not flagged as weaknesses** (per instruction, to avoid over-flagging legitimate
formatting/mapping): pure label/enum formatting, straight field-to-field DTO mapping, sort keys with
no business meaning, and documented compatibility fallbacks that fail visibly (e.g. Dashboard's
"not connected in this QML preview" synthetic snapshot) rather than silently masquerading as real
data.

## Master finding table

| Priority | Capability | Current file/method | Current behavior | Classification | Correct owner | Why current placement is risky | DTO impact | Tests |
|---|---|---|---|---|---|---|---|---|
| **P0** | Scheduling / Tasks | `scheduling/builders/change_impact_builder.py::compute_schedule_impact` (reached via `tasks/api.py:681 get_schedule_impact`) **vs.** `scheduling/builders/change_impact_builder.py::build_change_impact` (reached via `scheduling/api.py::analyse_change_impact`) — **newly verified in this pass** | Two adapter functions independently wrap `ScheduleChangeImpactService.analyse(...)` for what is conceptually the same "schedule change impact" report, but with **differing behavior**: `build_change_impact` checks `BaselineService.get_approved_baseline` and passes the real result as `has_approved_baseline`; `compute_schedule_impact` never checks and always passes `has_approved_baseline=False` | DUPLICATED LOGIC / APPLICATION ORCHESTRATION (a business decision differing between two adapter entry points) | `application/scheduling/forecasting/schedule_change_impact_service.py` (`ScheduleChangeImpactService`) should own the baseline-approval lookup itself, as one parameter-free behavior, not something each adapter caller may or may not remember to pass | A user reaching this report via the Tasks panel vs. the Scheduling workspace can see a different `requires_approval` signal for the same task/project, purely because of which desktop entry point they used, not because anything about the schedule actually differs | No — both existing DTOs (`SchedulingChangeImpactDto`, `ScheduleImpactReportDto`) are unchanged; the fix is inside the shared service, or in making both adapter call sites pass the same computed value | No dedicated test found covering this specific divergence; `test_pm_scheduling_calendar_real_wiring.py` and Appendix A's Tasks/Scheduling desktop-API tests exercise the two paths independently, not against each other |
| **P0** | Projects | `api/desktop/projects/builders/resource_builder.py::list_resources_for_context` | Reaches into `resource_service._resource_repo` **and** calls `resource_service._tenant_context_service.require_active_organization_id(...)` directly — i.e. performs tenant-scope resolution itself, in the desktop layer, using another service's private collaborator | AUTHORIZATION / COMPOSITION (tenant-scope decision made in the desktop adapter — explicitly listed as a "must not own" for this layer) | `application/resources/resource_service.py` (`ResourceService`) — tenant scoping must be resolved inside the service that owns `_tenant_context_service`, never re-derived by a caller reaching around it | If `ResourceService`'s internal tenant-scoping logic ever changes, this adapter code silently keeps using the old assumption since it duplicates the mechanism rather than calling through it — a real tenant-isolation drift risk, not just a style issue | No — `ProjectAssignableResourceOptionDescriptor` is unchanged; the fix is calling a public `ResourceService` method instead | No test found asserting this code path specifically enforces tenant scope correctly under a cross-tenant fixture (the module-wide tenant-hardening suite, §13, tests repositories directly, not this adapter path) |
| **P0** | Dashboard | `api/desktop/dashboard/services/dashboard_snapshot_service.py::_list_pending_approvals` | Wraps `ApprovalService.list_pending(...)` in `try/except Exception: return ()` | AUTHORIZATION (compatibility fallback that swallows real failures) | `application/` — if `ApprovalService.list_pending` can raise for permission/tenant/infra reasons, `DashboardSnapshotService` should let a typed error propagate (or the desktop API should surface a partial-failure signal), not silently show "zero pending approvals" | A genuine permission-denial or infrastructure failure is indistinguishable from "there really are no pending approvals" — a user with lost access, or during an outage, sees a clean empty dashboard instead of an error | Possibly — depends on whether callers rely on the always-succeeds contract; if a typed error is introduced, `ProjectDashboardSnapshotDescriptor`'s current always-populated shape would need an explicit partial-failure field | No test found forcing `ApprovalService.list_pending` to raise and asserting the dashboard's behavior in that case |
| **P0** | Scheduling | `scheduling/api.py::add_holiday`/`update_calendar` (legacy fallback branches) | When `platform_calendar_api` isn't wired, `add_holiday` fabricates and returns an **unpersisted** `SchedulingHolidayDto(id="", ...)` as if the write succeeded; `update_calendar` silently returns the unchanged snapshot as if the edit applied | COMPATIBILITY FALLBACK, but of the risky kind — a placeholder success result for an operation that was not actually persisted | `api/desktop/scheduling/api.py` should raise a typed "not available" error on this branch instead of fabricating success, or the branch should be removed once the documented "moved to Platform Admin" transition completes | A caller cannot distinguish "your holiday was saved" from "nothing happened, the platform calendar API isn't wired" — exactly the "placeholder success DTOs for operations that were not persisted" pattern this priority tier exists for | Yes, deliberately — this is the one case where changing the contract (raise instead of fake-succeed) is the correct fix, and is flagged as a separately-approved correction, not a default migration | No test found asserting `add_holiday`/`update_calendar` behavior when `platform_calendar_api` is absent |
| **P0** | Tasks | `api/desktop/tasks/api.py::list_all_tasks` | Loops every accessible project calling `_serialize_project_tasks`; `try/except BusinessRuleError: continue` silently drops any project the user turns out not to have access to, with no signal to the caller about which projects were skipped or how many | AUTHORIZATION (a permission-denial condition is converted into silently incomplete data) | `application/tasks/service.py` (`TaskService`) should expose one method that resolves the accessible-project set once and returns a typed result (e.g. `(tasks, skipped_project_ids)`), rather than the adapter looping and swallowing per-project failures | A user reviewing "all my tasks" has no way to know the list is incomplete because access to one project was revoked mid-session, or a permission was misconfigured — this looks identical to "you simply have no tasks in that project" | No — `TaskDesktopDto[]` shape is unchanged; a `skipped_project_ids` field would be additive, not breaking | No test found asserting behavior when one of several accessible projects becomes inaccessible mid-call |
| **P0** | Tasks | `api/desktop/tasks/services/access_resolution_service.py::project_rows_for_task_scope` (and its sibling in `resource_lookup_service.py`) | On `BusinessRuleError` from `ProjectService.list_projects`, falls back to querying `project_service._project_repo` directly and **re-implements permission filtering by hand**: `for permission_code in ("task.read","task.manage","project.read"): project_ids.update(...)` | AUTHORIZATION (a second, hand-rolled implementation of the same access-control decision `ProjectService` already makes) | `application/projects/service.py` (`ProjectService`) should expose the fallback/degraded-mode behavior itself (or not need a fallback at all, if the primary path is fixed) — permission-set filtering must have exactly one implementation, not two that could silently drift apart | If `ProjectService`'s own filtering logic changes (a new permission added, a rule tightened), this duplicate must be remembered and updated in lock-step or it silently grants/denies access inconsistently with the "real" path | No — `TaskProjectOptionDescriptor[]`/`TaskProjectResourceOptionDescriptor[]` are unchanged | No test found exercising this specific fallback branch (i.e. forcing `ProjectService.list_projects` to raise `BusinessRuleError` and asserting the fallback's output matches what the primary path would have returned) |
| **P1** | Scheduling | `scheduling/services/calendar_adapter_service.py::update_platform_calendar_working_days` — **newly verified in this pass** | For every calendar edit, sets `is_working_day`/`hours_override` for all 7 weekdays via 7 sequential `save_working_rule` calls, **unconditionally enforcing one uniform hours-per-day value across the whole week** and overwriting any pre-existing per-weekday customization | DOMAIN POLICY (a real calendar-editing business rule, executed via a loop of low-level calls, in the desktop adapter) | The platform's own calendar application service (`src/core/platform/application/time_management/calendar/`) should expose one intention-revealing operation (e.g. `set_uniform_working_pattern(...)`) rather than the PM desktop adapter looping over 7 individual rule-saves | If any calendar is ever edited with legitimately asymmetric per-day hours (e.g. a shorter Friday), this adapter silently forecloses that on every edit made from this screen — a correctness/data-loss risk disguised as a UI action | No — `SchedulingCalendarSnapshotDto` is unchanged; the fix moves *how* the update is performed, not what's returned | No test found asserting per-weekday hours survive an edit, or asserting the uniform-hours behavior is intentional rather than accidental |
| **P1** | Resources | `api/desktop/resources/api.py::update_resource` | Pre-reads the resource, then computes `hourly_rate_changed`/`currency_changed`/`rate_affecting_change` itself and sets `effective_on=date.today()` before calling `ResourceService.update_resource(...)` | APPLICATION ORCHESTRATION (a business decision — "does this edit warrant a new effective-dated rate-card line" — made in the API layer, not the service) | `application/resources/resource_service.py` (`ResourceService`) — the service already owns the resulting rate-card supersession logic; it should also own detecting *whether* this update is rate-affecting, from the same before/after comparison it needs anyway | The desktop layer is the only caller that performs this detection today, but any future caller of `ResourceService.update_resource` (a script, an import job, a future API) must reimplement the same detection or risk skipping the rate-card supersession entirely | No — `ResourceDesktopDto`/`ResourceUpdateCommand` unchanged; `ResourceService.update_resource` already accepts the fields needed, it would just also accept/derive `effective_on` internally | No test found asserting a caller other than this desktop method also triggers correct rate-card supersession |
| **P1** | Resources | `api/desktop/resources/services/availability_resolution_service.py::resolve_availability_service` | Constructs a **brand-new** `ResourceAvailabilityService` instance inside the desktop layer, wiring it from other services' private `_resource_repo`/`_task_repo`/`_work_calendar_engine` attributes, as a fallback when none was injected | COMPOSITION (service construction and dependency wiring, which belongs exclusively to the composition root) | `src/infra/composition/project_registry.py` — this fallback construction path should not exist; `ResourceAvailabilityService` should always be constructed once, centrally, and injected | If any of the three private attributes this code depends on is renamed or restructured, this fallback breaks silently at runtime with no compile-time signal, and it duplicates exactly the wiring `project_registry.py` already does correctly elsewhere | No — `ResourceAvailabilityDto` unchanged | No test found forcing the "no service injected" branch and asserting the fallback construction produces a correctly-wired instance |
| **P1** | Resources | `api/desktop/resources/api.py::list_resource_assignments` | Falls back to reading `availability_service._assignments` (a private attribute) when no `assignment_repo` is injected | COMPOSITION / private-attribute access | Same as above — `project_registry.py` should guarantee `assignment_repo` is always injected, removing the need for this fallback entirely | Silent, undocumented coupling to another service's internal field name | No — `ResourceAssignmentDesktopDto[]` unchanged | No test found for the no-`assignment_repo`-injected branch |
| **P1** | Projects / Tasks | `api/desktop/projects/serializers/resource_serializer.py::serialize_project_resource` **and** `api/desktop/tasks/builders/resource_options_builder.py` (independently) | Both compute the same rate/currency precedence fallback — `project_resource.hourly_rate` else `resource.hourly_rate`, same for currency — for display, in two different desktop-layer files | DUPLICATED LOGIC / DOMAIN POLICY (a financial rate-precedence rule, computed twice, at the wrong layer) | The precedence rule already exists, correctly, as `LaborRateResolver`/`RateCardResolver` (ADR-PF-005) — display code should read the resolved value from that resolution, not re-derive an approximation of the same precedence independently | A user can see one "effective rate" on the Project's resource list (via this two-field fallback) and a different one in Financials (via the real rate-card precedence engine) for the same resource, because two different, non-equivalent rules compute what looks like the same number | No — `ProjectResourceDesktopDto`/`TaskProjectResourceOptionDescriptor` unchanged; the display value would simply come from a resolved snapshot instead of a raw two-field fallback | No test found comparing this display value against `RateCardResolver`'s actual resolution for the same resource/project |
| **P1** | Tasks | `api/desktop/tasks/builders/assignment_preview_builder.py::preview_assignment` | Computes `overallocation_pct = peak_load_percent - capacity_percent` and builds `conflict_projects` via a nested loop that calls `TaskService.get_task(conflict_task_id)` once per conflicting task | DOMAIN POLICY / QUERY (an overallocation-delta formula, plus an N+1 lookup loop, both in the desktop layer) | `application/resources/resource_availability_service.py` (`ResourceAvailabilityService`) should expose one method returning both the delta and the resolved conflict-task details in a single batched call | The overallocation formula is simple today, but if it's ever revised (e.g. to account for partial-day capacity), this desktop-layer copy must be found and updated separately from wherever else "overallocation" is computed; the N+1 loop is a real, if usually small-scale, performance risk | No — `AssignmentPreviewDesktopDto` unchanged | No test found asserting this formula matches whatever `ResourceAvailabilityService` itself considers "overallocated" |
| **P1** | Dashboard | `api/desktop/dashboard/builders/health_card_builder.py`, `chart_builder.py`, `panel_builder.py`, `overview_builder.py` — **and, newly confirmed in this pass, a fourth independent instance** in `scheduling/formatters/status_formatter.py::resource_load_status_label` | The same "resource/utilization overload" threshold rule (`>100%` → danger/overloaded) is independently hardcoded in **at least four** separate desktop-layer files across two capabilities, with `health_card_builder.py` additionally hardcoding SPI/CPI `<0.95` danger thresholds | DOMAIN POLICY (duplicated business thresholds, now confirmed to span capability boundaries, not just within Dashboard) | `application/reporting` or a shared domain value object should expose one utilization-banding function (and one EVM-health-banding function); every desktop consumer calls it | Four independent copies of "what counts as overloaded" cannot be kept in sync by convention; a threshold change (e.g. product decides 90% is the new overload line) requires finding and editing all four correctly, and this audit's own discovery of the fourth instance (in a completely different capability, Scheduling) shows they are not being kept in sync today | No — no DTO field changes; the banding label is still a `str`, just computed once, centrally | No test found asserting all four current implementations agree with each other on the same input |
| **P1** | Financials | `api/desktop/financials/api.py::get_project_procurement_commitments` | Hardcodes 4 status-category sets and does the counting in Python, entirely inside the desktop facade, with **no backing application-service method at all** | APPLICATION ORCHESTRATION, but see DTO/Tests column — also **DEAD/UNUSED** | If ever revived: `application/financials/forecasts/forecast_service.py` (`ForecastCostService`) or a dedicated procurement-integration service should own commitment-status classification | Confirmed by repo-wide grep (Appendix A) to have **no QML consumer anywhere** — the actual risk today is dead code masquerading as a real feature, not active misplacement | N/A if deleted | No test found; recommend deletion after one more confirmation pass, not migration (see Correct-destination rules: "Dead duplicated implementation → Delete after usage verification") |
| **P1** | Financials | `api/desktop/financials/api.py::list_project_requisitions` | Duck-typed call into `procurement_service.list_requisitions(limit=500)`, then Python-side filters the 500-row cap by `source_reference_type`/`source_reference_id`, wrapped in `except Exception: return ()` | QUERY/READ PROJECTION misplaced, COMPATIBILITY FALLBACK (broad except), **and DEAD/UNUSED** | If revived: a typed, paginated, project-scoped procurement query (the audit doc's Phase C already calls for this — "typed project-source contract") | Same as above — confirmed no QML consumer; the 500-row cap could silently omit a project's real requisitions if system-wide volume exceeds 500, but this cannot bite anyone today since nothing calls it | N/A if deleted | No test found; recommend deletion after usage verification |
| **P2** | Resources | `api/desktop/resources/serializers/certification_serializer.py::serialize_certification` | Computes `cert_status` (valid/expiring-soon/expired) via a hardcoded 30-day threshold, directly in the serializer | DOMAIN POLICY (duplicated status rule) | `domain/resources/skills.py` (`ResourceCertification`) already has `is_valid_on(date)`/`is_valid_during(...)` — the serializer should call one of those (or a new `expiring_soon_on(date, window_days)` domain method) instead of re-deriving the same judgment | If the "expiring soon" window is ever tuned, or certification validity rules gain nuance (e.g. a grace period), the serializer's copy is a second place that must be remembered | No — `ResourceCertificationDesktopDto.cert_status` field is unchanged, only its source changes | No test found asserting this serializer's `cert_status` agrees with `ResourceCertification.is_valid_on`/`is_valid_during` for the same dates |
| **P2** | Scheduling | `scheduling/formatters/baseline_formatter.py::format_baseline_row` (reached via `serializers/baseline_serializer.py`'s re-export) — **newly verified in this pass** | Computes `can_submit = status_val == "draft"`, `can_approve/can_reject = status_val == "submitted"` via string comparison | DOMAIN POLICY (duplicated lifecycle-transition-legality rule) | `domain/scheduling/baseline.py` (`ProjectBaseline`) already encodes its own allowed-transition rules via its lifecycle methods (`submit()`/`approve()`/`reject()`, each guarding on current status) — the formatter should ask the domain object, not re-derive the same three checks by string equality | If `ProjectBaseline`'s lifecycle ever gains a new state (e.g. a "revoked" status) or changes its transition table, this formatter's three hardcoded checks are a second place that must be updated, silently, or the UI will offer/hide the wrong action buttons | No — `SchedulingBaselineRowDto.can_submit/can_approve/can_reject` fields unchanged, only their source | No test found asserting these three flags agree with `ProjectBaseline`'s actual allowed-transitions table |
| **P2** | Scheduling | `scheduling/services/calendar_adapter_service.py::_default_platform_calendar_id` — **newly verified in this pass** | Picks the "default" calendar by filtering for `calendar_type="GLOBAL"` and taking the first result, else the first calendar of any type | DUPLICATED LOGIC (re-implements the platform calendar service's own "GLOBAL is canonical" convention via a list-and-filter heuristic) | The platform calendar service (`src/core/platform/application/time_management/calendar/enterprise_calendar_service.py`) already encodes "GLOBAL" as the canonical bootstrap calendar type; it should expose a `get_default_calendar()` method rather than have this PM-side adapter reconstruct the same convention | If the platform's canonical-calendar convention ever changes, this adapter's independent reconstruction of it is a second place that must be found and updated | No | No test found |
| **P2** | Scheduling | `scheduling/services/calendar_adapter_service.py::get_platform_calendar_snapshot` — **newly verified in this pass** | Collapses potentially per-weekday-varying working hours into one scalar `hours_per_day` by taking `working_hours[0]` (the first working rule found), with no signal to the caller that this is an approximation | QUERY/READ PROJECTION with an unflagged, lossy approximation | Either the query should return true per-weekday hours (matching the underlying `WorkingRule` model), or the DTO should be explicit that `hours_per_day` is "the first working day's hours," not "the" uniform value | Display-only today (not fed into CPM per this pass's investigation), so the immediate risk is limited, but any future consumer of this snapshot that assumes uniform daily hours would silently get a wrong answer for an asymmetric calendar | Possibly, if the DTO is corrected to expose per-weekday hours — flagged as a future, separately-approved correction, not a default migration | No test found asserting behavior for a calendar with genuinely different weekday hours |
| **P2** | Scheduling | `scheduling/utils/scheduling_utils.py::remaining_duration_days` (reached via `serializers/schedule_serializer.py`) — **newly verified in this pass** | Computes `max(0, round(duration_days * (1 - percent_complete/100)))` — a linear percent-complete projection | DOMAIN POLICY (a small but real business calculation, not formatting) | `domain/tasks/task.py` (`Task`) — a natural candidate for a `remaining_duration_days` property/method, since it depends only on the entity's own fields | Any other surface needing "remaining duration" (a Gantt export, a report, a future mobile API) would have to import a desktop-API utility module — the wrong dependency direction for what is fundamentally a task-progress calculation | No | No test found in isolation from the serializer that calls it |
| **P2** | Scheduling | `scheduling/builders/change_impact_builder.py::compute_schedule_impact` vs `build_change_impact` — internal duplication, distinct from the P0 finding above about their *differing* behavior — **newly verified in this pass** | Two full adapter functions independently wrap `ScheduleChangeImpactService.analyse(...)` rather than one parameterized function | DUPLICATED LOGIC | Collapse to one function; push the "simulate +1 day" scenario into a caller-supplied parameter rather than a second, hardcoded entry point | Maintenance cost of keeping two near-identical functions behaviorally aligned (already failed once — see the P0 row above) | No, if collapsed carefully — both existing DTOs are preserved, only the internal implementation merges | Covered by the same test gap noted in the P0 row |
| **P2** | Register | `api/desktop/register/builders/entry_list_builder.py` and `serializers/entry_serializer.py`, independently | Both call `register_status_utils.is_overdue`/`severity_rank` — the same underlying util, so no divergence risk today, but the triage-ordering rule itself (critical-first, overdue-first, due-date, title) is implemented as a desktop-layer sort key rather than sourced from the domain/application layer | DOMAIN POLICY (duplicated status rule, matching this priority tier's own example exactly) | `application/risk/register_service.py` (`RegisterService`) or `domain/risk/register.py` (`RegisterEntry`) should expose the triage ordering as a queryable capability, not leave it to `list_entries`' callers to re-sort | If a *second* desktop consumer of register entries (e.g. Dashboard's `_build_high_risks_table`, see next row) reimplements the same ordering independently instead of calling the same util, the two can drift — which is exactly what the next row shows has already happened | No — `RegisterEntryDesktopDto[]` ordering is unchanged, only computed centrally | No test found asserting `list_entries`' returned order matches a domain-level "triage order" definition |
| **P1** | Dashboard | `api/desktop/dashboard/builders/operational_table_builder.py::_build_high_risks_table` | **Re-implements** register severity/status filtering and sorting independently, rather than calling `register/builders/entry_list_builder.py`'s existing logic or a shared utility | DUPLICATED LOGIC (confirmed independent reimplementation, not a shared-util call like the Register-internal case above — the real divergence risk) | Same target as above (`RegisterService`/`RegisterEntry`) — Dashboard's "high risks" table and the Register workspace's own filtered list should both call one triage-ordering capability | Unlike the Register-internal duplication (which calls the same util twice), this is a **second, independent implementation** of the same filter/sort logic — the two can silently disagree about which risks count as "high" or how they're ordered, with no test proving they don't | No | No test found comparing Dashboard's "high risks" table contents/order against the Register workspace's own filtered-by-severity list for the same data |
| **P2** | Dashboard | `api/desktop/dashboard/builders/operational_table_builder.py::_build_pending_approvals_table` | Imports a **private module** from a different bounded context: `from src.core.platform.api.desktop.approval._approval_labels import ...` | COMPOSITION / layering violation (worse than a private-*attribute* access — this is a private-*module* cross-boundary import) | `src/core/platform/api/desktop/approval/` should export a public labeling helper if PM needs it; PM should not import another module's underscore-prefixed internals | If the platform Approval module ever refactors its internal `_approval_labels` module (a change its own maintainers would reasonably consider "private, safe to change"), this PM-side import breaks with no warning from the owning team | No | No test found asserting this import survives a refactor of the platform Approval module's internals |
| **P2** | Dashboard | `api/desktop/dashboard/builders/panel_builder.py::_build_panel_row` | Infers a status "tone" (`danger`/`success`/etc.) by **substring-scanning already-formatted display text** (`"late"`, `"over budget"`, `"favorable"`) | DOMAIN POLICY (fragile re-derivation of semantics from presentation text, backwards from the correct data flow) | Whatever builder/service produces the underlying status value should also produce (or the panel builder should receive) a proper status enum/tone value, not force this builder to guess from a string | A future copy-edit to the display text (e.g. changing "over budget" to "budget exceeded") silently breaks the tone-inference logic with no compiler or test signal | No — the DTO's `tone` field type is unchanged, only how it's derived | No test found asserting tone inference stays correct if the underlying display strings change |
| **P2** | Collaboration | `api/desktop/collaboration/api.py::_threaded_comments` | Builds a comment-reply tree via a redundant double-loop (`for root in roots: ...` then `for comment in comments: ...`, both doing the same `append_branch` walk, made correct only by a `visited` guard) | APPLICATION ORCHESTRATION (nontrivial tree-construction logic, misplaced — and internally duplicated within the same function) | `application/collaboration/services/collaboration_service.py` (`CollaborationService`) — thread construction from a flat comment list is a reusable capability, not desktop-adapter-specific logic | The double-loop pattern works today only because of the `visited` set catching the redundancy; a future edit that removes or weakens that guard could reintroduce actual double-processing | No — `TaskCollaborationCommentDesktopDto` nesting shape is unchanged, only where it's built | No test found isolating `_threaded_comments`' tree-building correctness from the rest of `build_task_snapshot` |
| **P2** | Collaboration | `api/desktop/collaboration/serializers/collaboration_serializers.py::serialize_task_comment` | Computes `can_edit`/`can_reply`/`can_delete`/`can_react` from a pre-fetched `action_context` plus `principal_user_id` comparison, in the serializer | AUTHORIZATION (permission-flag derivation, misplaced — though not an actual bypass, since `CollaborationService.edit_comment`/`delete_comment`/etc. independently re-check permission on the actual mutating call, per the original audit) | `CollaborationService.get_task_comment_action_context` should return these flags ready-made, the same way `TaskAssignmentMixin.get_assignment_action_context` already does for assignments | UX/permission-flag drift risk (a button shown that the backend would reject, or hidden when the backend would allow it) rather than an exploitable security gap, since enforcement still happens server-side on the real mutation | No — `TaskCollaborationCommentDesktopDto`'s four boolean fields are unchanged, only their source | No test found asserting these four flags match what the corresponding mutating call would actually permit, across role variations |
| **P2** | Timesheets | `api/desktop/timesheets/serializers/period_serializer.py::serialize_period_summary`/`serialize_period_from_service` | Recomputes `total_hours = sum(entry.hours for entry in entries)` in Python; `serialize_period_from_service` additionally issues an **extra** `list_time_entries_for_resource_period` query solely to recompute this sum | QUERY/READ PROJECTION (should be a service-level aggregate, not a serializer-level Python sum plus an extra fetch) | `src.core.platform.application.time_management.time` (`TimeService`) should expose a period-total-hours aggregate method | Every period-workflow desktop call (`submit_period`/`approve_period`/etc.) pays this extra query cost just to redisplay a sum the service could return directly | No — `TimesheetPeriodSummaryDesktopDto.total_hours` unchanged | No test found isolating this recomputation from the rest of the period-workflow methods |
| **P2** | Timesheets | `api/desktop/timesheets/builders/assignment_options_builder.py`, `assignment_snapshot_builder.py` | Perform Python-side joins across `ProjectService`/`TaskService`/`ResourceService` results (nested loops: project → tasks → assignments → per-assignment resource lookup) | APPLICATION ORCHESTRATION (a cross-aggregate join, done in the adapter instead of one service-level query) | A dedicated application-layer query (or, if the data volume ever justifies it, a Reader) that returns assignment-with-context rows directly, instead of three separate service calls joined in Python | N+1-shaped in the worst case (one resource lookup per assignment); acceptable at today's scale per the original audit, but a real candidate if timesheet assignment volume grows | No | No test found measuring this join's query/call count |
| **P2** | Portfolio | `api/desktop/portfolio/api.py::create_project_dependency` | After creating a dependency, **re-fetches all dependencies and linear-scans** for the one just created (matching on predecessor/successor/type/summary) instead of using the creation call's own result | APPLICATION ORCHESTRATION (a design smell — refetch-and-scan instead of using the command's own return value) | `application/portfolio/services/portfolio_service.py` (`PortfolioService.create_project_dependency`) should return the created entity directly; the desktop method should serialize that return value | Wasteful at any real dependency count, and fragile — if two dependencies with identical fields could ever exist, the scan could match the wrong one (unlikely today, but a real "matches by content, not by id" hazard) | No — `PortfolioDependencyDesktopDto` unchanged; the fix only changes how the desktop method obtains the entity to serialize | No test found for the "two similar dependencies exist" edge case this scan pattern is fragile against |
| **P2** | Projects | `api/desktop/projects/api.py::create_project`/`update_project` | Uses `call_with_supported_kwargs` (`inspect.signature`-based reflection) to filter which command fields are passed to `ProjectService` | COMPATIBILITY FALLBACK (reflection-based signature compatibility) | An explicit, enumerated mapping from `ProjectCreateCommand`/`ProjectUpdateCommand` fields to `ProjectService.create_project`/`update_project` parameters | A parameter removed or renamed on either side is silently dropped rather than causing a type error or test failure — signature drift is invisible until a field's effect silently stops working | No — this changes only the internal mapping mechanism, not the command/DTO shapes | No test found asserting every command field the DTO declares actually reaches the service (i.e. that reflection isn't silently dropping one) |
| **P3** | Portfolio | `api/desktop/portfolio/builders/capacity_pool_builder.py::build_capacity_pool` | Hardcodes a fixed 90-day window (`date.today()` to `+90 days`) rather than accepting it as a parameter | PRESENTATION/APPLICATION boundary gap (minor — not a business-rule leak, just an unparameterized default) | Leave as an application-layer default if the product truly always wants 90 days; make it a parameter on `PortfolioResourcePoolService.get_pool_report` if a caller-configurable window is ever needed | Low risk today; flagged only because a future desktop method wanting a different window would have to duplicate this constant rather than pass one in | No | No test found for a non-default window |
| **P3** (cleanup) | Financials | `api/desktop/financials/api.py::list_project_requisitions`, `get_project_procurement_commitments` | See P1 rows above — repeated here to make the cleanup recommendation explicit | DEAD/UNUSED | Delete, after one more usage-verification pass (a fresh repo-wide grep immediately before removal, since QML wiring can change between audit and implementation) | Carrying dead adapter code with real (if unreachable) logic inside it is a maintenance and audit-noise cost with no offsetting benefit | N/A | N/A — deletion, not migration |

**Findings deliberately not added to this table** (reviewed and judged legitimate, per the instruction
not to over-flag formatting/mapping):
- Dashboard's fully-synthetic "preview" `build_snapshot` fallback when `dashboard_service` is
  unwired — a documented, visibly-labeled compatibility state ("not connected in this QML preview"),
  not a silent placeholder.
- `scheduling/services/scheduling_facade_service.py` — both functions correctly delegate real work
  (CPM recalculation, leaf-task selection) to the engine/domain layer; the dual engine-vs-task-list
  path is a documented, intentional fallback (`api.py:289`).
- `scheduling/serializers/{constraint,dependency}_serializer.py` — both consume a pre-computed
  classification (`hard_pairs`, `dependency_direction`) rather than deriving business meaning
  themselves; legitimately presentation-shaped.
- `scheduling/serializers/change_impact_serializer.py`'s `affected_count` derivation and 20-row
  truncation — reviewed and judged borderline-acceptable display arithmetic, not flagged as a
  weakness in the table, though the silent truncation (no "showing 20 of N" signal) is worth a
  product decision if it ever causes confusion in practice.

---

# Desktop Adapter Migration Plan

## Correct-destination reasoning (applied per finding, not a blanket rule)

Every migration recommendation above followed this mapping — stated explicitly, per the
instruction not to default every finding to "move to the service layer":

| Behavior | Target |
|---|---|
| QML formatting or labels | Desktop serializer/builder (stays) |
| Use-case orchestration | Application service |
| Cross-aggregate validation | Application service or application policy |
| Stable business invariant | Domain entity/value object/domain policy |
| SQL aggregate or report projection | Query service + Reader |
| Dependency construction | Composition root |
| Permission/tenant enforcement | Application service |
| Database tenant defense | Repository/RLS |
| Compatibility placeholder | Explicit compatibility adapter, documented and isolated |
| Dead duplicated implementation | Delete after usage verification |

Concretely: the rate-affecting-change detection (Resources) and the tenant-scope resolution
(Projects) go to **application services**, because both are use-case decisions/enforcement, not
stable invariants. The baseline can-submit/can-approve/can-reject flags and the
remaining-duration-days formula go to **domain entities**, because both are context-free functions
of an entity's own state. The utilization/RAG threshold duplication goes to **application/reporting**
(a shared banding function), not domain, because "what counts as overloaded" is a reporting/product
policy, not an entity invariant. The dead procurement methods go to **deletion**, not migration.
None of this is bundled into "move everything to `application/`" — see the per-finding table above
for the reasoning behind each individual placement.

## Detailed responsibility migration map (P0 findings and the highest-value P1 findings)

Full `Current → Behavior → Target → Proposed flow → Compatibility → Tests` blocks for the findings
where a phased migration is actually warranted (P0s, plus the P1s with the clearest, most
self-contained fix). Lower-priority findings are fully specified in the master table above and are
not repeated here in this longer form — expanding all ~30 rows to this depth would pad the document
without adding decision-relevant detail.

---

**Current:**
`api/desktop/tasks/api.py::get_schedule_impact` → `scheduling/builders/change_impact_builder.py::compute_schedule_impact`, and, independently, `scheduling/api.py::analyse_change_impact` → `build_change_impact`

**Behavior:** Two adapter functions compute overlapping "schedule change impact" reports with different baseline-approval-check behavior — one always assumes no approved baseline exists, the other checks.

**Target:** `application/scheduling/forecasting/schedule_change_impact_service.py` (`ScheduleChangeImpactService`) — the service resolves the approved-baseline lookup itself, once, as part of `analyse(...)`, so no caller can omit it.

**Proposed flow:**
```text
ProjectManagementTasksDesktopApi.get_schedule_impact(task_id, project_id)
  → ScheduleChangeImpactService.analyse(project_id=, changed_task_id=, proposed_start=task.start_date+1day)
      → service resolves has_approved_baseline internally (no longer a caller-supplied assumption)
  → existing ScheduleImpactReportDto serializer
  → unchanged ScheduleImpactReportDto

ProjectManagementSchedulingDesktopApi.analyse_change_impact(...)
  → same ScheduleChangeImpactService.analyse(...) call, same internal resolution
  → existing SchedulingChangeImpactDto serializer
  → unchanged SchedulingChangeImpactDto
```

**Compatibility:** Both desktop methods keep their existing signatures and DTOs; only the internal
call target changes from two adapter-layer wrapper functions to one canonical service parameter.

**Tests:** A new `ScheduleChangeImpactService` unit test asserting `has_approved_baseline` is
resolved correctly and consistently; a parity test comparing both desktop entry points' output for
the same task/project, asserting they now agree.

---

**Current:**
`api/desktop/projects/builders/resource_builder.py::list_resources_for_context`

**Behavior:** Reaches into `resource_service._resource_repo` and calls
`resource_service._tenant_context_service.require_active_organization_id(...)` directly, performing
tenant-scope resolution in the desktop layer.

**Target:** `application/resources/resource_service.py` (`ResourceService`) — add or use an existing
public method (`list_resources()` already exists per Appendix A) that performs its own tenant
scoping internally; the desktop layer stops needing a fallback path at all once the primary call is
proven reliable.

**Desktop adapter after migration:**
```text
(no command — this is a read path)
ProjectManagementProjectsDesktopApi.list_assignable_resources(project_id)
  → explicit call to ResourceService.list_resources() (public method, no private-attribute fallback)
  → Resource[] result
  → existing build_assignable_options()
  → unchanged ProjectAssignableResourceOptionDescriptor[]
```

**Compatibility:** No change to the desktop method's signature or DTO; the fallback branch is
removed once confirmed unnecessary (DA1's exit gate, see below).

**Tests:** A cross-tenant fixture test proving `list_resources_for_context` (or its replacement) never
returns another tenant's resources, exercised specifically through this desktop call path, not just
at the repository level (closing the gap the original audit's tenant-hardening suite doesn't cover).

---

**Current:**
`api/desktop/dashboard/services/dashboard_snapshot_service.py::_list_pending_approvals`

**Behavior:** `except Exception: return ()` around `ApprovalService.list_pending(...)`.

**Target:** `application/` (the calling layer, `DashboardSnapshotService` itself, or whichever
service composes the dashboard) — let a permission/tenant/infrastructure failure propagate as a
typed error, or add an explicit partial-failure signal to the result.

**Proposed flow:**
```text
DashboardSnapshotService.build_snapshot(...)
  → ApprovalService.list_pending(project_id=, limit=120)   # no longer wrapped in a bare except
  → on a real failure: propagate a typed error, OR
    populate ProjectDashboardSnapshotDescriptor.pending_approvals_unavailable=True (additive field)
  → existing descriptor assembly, otherwise unchanged
```

**Compatibility:** If the additive-field approach is chosen (recommended, since it preserves the
"dashboard never crashes" UX property while removing the silent-empty-output risk), no existing
field changes meaning — only a new, optional signal is added. If the propagate-error approach is
chosen instead, this is a **separately approved correction** per the migration constraints (current
error types may only change with explicit approval), not a default part of this phase.

**Tests:** A test forcing `ApprovalService.list_pending` to raise, asserting the dashboard either
surfaces the new signal or the approved typed error — not silently empty output either way.

---

**Current:**
`api/desktop/scheduling/api.py::add_holiday`/`update_calendar` (legacy/no-platform-API branches)

**Behavior:** Fabricates a placeholder success DTO, or returns an unchanged snapshot, when
`platform_calendar_api` isn't wired — presenting an unpersisted operation as if it succeeded.

**Target:** `api/desktop/scheduling/api.py` itself — this is a desktop-adapter error-boundary fix,
not a relocation; the correct owner of "raise instead of fake-succeed" is the adapter method's own
error handling.

**Proposed flow:**
```text
ProjectManagementSchedulingDesktopApi.add_holiday(command)
  → if platform_calendar_api is None: raise BusinessRuleError(code="CALENDAR_API_NOT_AVAILABLE")
  → else: unchanged (delegates to calendar_adapter_service.add_platform_holiday)
```

**Compatibility:** **This changes current error behavior**, which the migration constraints require
to be a separately approved correction, not a silent default. Until approved, DA2 (below) should at
minimum add a test that makes the current behavior explicit and intentional-looking rather than an
accidental gap, without changing the behavior itself — the actual fix is gated on product/architecture
sign-off given it changes what callers observe on this branch.

**Tests:** A test asserting today's actual behavior (fabricated success) exists first, so any future
fix is a deliberate, reviewed behavior change, not an unnoticed one.

---

## Phased plan

### Phase DA0 — Guardrails and characterization

**Status: IN PROGRESS (2026-08-08).** The architecture guardrails are implemented in
`src/tests/architecture/test_pm_desktop_adapter_architecture.py` with an exact, fail-on-addition
and fail-on-stale-removal exception register for verified pre-existing DA1 violations. All six P0
themes are characterized by
`src/tests/project_management/test_pm_desktop_adapter_da0_characterization.py` plus the existing
Dashboard failure-propagation coverage in `test_phase0a4_other_safety_corrections.py`. The focused
checkpoint is 20 passing tests. DA0 remains open for characterization of the nine P1 findings;
DA1 has not started.

- Add tests pinning current desktop DTO output for every finding in the master table (a
  characterization test per P0/P1 row, at minimum) — so no migration in later phases can silently
  change behavior no one intended to change.
- Add an architecture test: no new file under `api/desktop/**` may import
  `contracts.repositories.**`, `infrastructure.persistence.orm.**`, or
  `infrastructure.persistence.repositories.**` (existing occurrences — none were found repository/ORM
  side, per this and the prior audit — are already clean; this guardrail locks that in going
  forward).
- Add a guardrail: no `api/desktop/**` file may access an attribute named `_<anything>` on an
  object it did not construct itself (targets every private-attribute finding in the table above).
- Add a guardrail: no `api/desktop/**` file may call a constructor of a class defined under
  `application/**` (targets `resolve_availability_service`'s fallback construction).
- Add tests proving authorization/tenant exceptions raised by an application service are not
  converted to empty results anywhere they currently could be (`_list_pending_approvals`,
  `access_resolution_service.py`'s fallback, `list_all_tasks`'s per-project swallow).
- Add usage verification (a repo-wide grep, re-run immediately before any deletion, not relied on
  from this audit alone) for `list_project_requisitions`/`get_project_procurement_commitments`.

**Exit gate:** every P0/P1 finding above has a passing characterization test pinning its *current*
behavior; the four new guardrails are active and would fail against a deliberately-reintroduced
violation (prove this with one throwaway violation per guardrail, then remove it).

### Phase DA1 — Composition leaks

Migrate: `resolve_availability_service`'s fallback construction (Resources); the
`_resource_repo`/`_assignments` private-attribute fallbacks (Resources); `access_resolution_service.py`/
`resource_lookup_service.py`'s repo-bypass fallback (Tasks); `list_resources_for_context`'s direct
`_tenant_context_service` call (Projects).

Target: explicit construction in `project_registry.py`; constructor-injected public collaborators
everywhere a private-attribute or repo-bypass fallback exists today.

**Keep DTOs and QML unchanged** — every finding in this phase is an internal-wiring fix with no
DTO-shape consequence, confirmed per-finding in the master table's "DTO impact" column.

### Phase DA2 — Security and error-boundary corrections

Migrate: `list_all_tasks`'s silent per-project swallow (add a `skipped_project_ids` signal);
`_list_pending_approvals`'s broad except (add a partial-failure signal or propagate, per product
decision); the Scheduling placeholder-success branches (gated on separate approval, per the
migration constraints, since it changes observable error behavior).

**Preserve typed errors through the desktop API** — this phase adds missing error/partial-failure
signals, it does not invent new ones that weren't already possible at the application layer.

### Phase DA3 — Application/domain policy extraction

One capability at a time, per the migration constraints ("do not migrate all capabilities in one
phase"):

1. **Resources** — the rate-affecting-change decision moves to `ResourceService` (application
   service — it's a use-case decision, not a stable invariant).
2. **Resources** — certification status/expiring-soon moves to `ResourceCertification` (domain — a
   context-free function of the entity's own dates).
3. **Scheduling** — baseline can-submit/can-approve/can-reject moves to `ProjectBaseline` (domain);
   `remaining_duration_days` moves to `Task` (domain); the uniform-hours-per-week calendar policy
   moves to the platform calendar service (application, in the platform module, not PM); the
   default-calendar resolution moves to a platform `get_default_calendar()` (application, platform
   module).
4. **Register** — the triage-ordering rule (severity/overdue) moves to `RegisterService`/
   `RegisterEntry` (application service or domain, decided when implemented — likely domain, since
   ordering by severity/overdue is a context-free function of the entry's own fields plus "today").
5. **Dashboard** — the four independent overload-threshold implementations collapse to one shared
   banding function in `application/reporting`; `_build_high_risks_table`'s independent
   reimplementation of Register's triage logic is replaced with a call to whatever Register exposes
   from item 4.

**Do not put all of these into one generic service** — each lands with the specific owner named
above, per the Correct-destination rules, not a shared catch-all.

### Phase DA4 — Read/report extraction

Migrate only measured or clearly problematic reads, per the migration constraints:

- Financials' dead procurement methods are **deleted** here (after DA0's usage-verification
  re-check), not migrated to a Reader — there is no live consumer to build a Reader for.
- Timesheets' period-total recomputation (`period_serializer.py`) becomes a service-level aggregate
  on `TimeService`, removing the extra query.
- Timesheets' assignment-options cross-service Python join becomes one application-layer query.
- Dashboard's Portfolio/Register-adjacent report totals are candidates for a future Reader **only
  if** a Phase 0-style measurement (mirroring the Finance Snapshot pilot's own Phase 0, §18) shows
  a comparable redundancy — this audit did not find one as severe as the Finance Snapshot case, so
  no Reader is recommended here yet, only the application-layer aggregate fixes above.

**This phase is explicitly not combined with the Finance Snapshot CQRS Reader pilot** (§15-18),
except where the exact same financial desktop method must be touched — and no finding in this audit
requires that; `get_finance_snapshot` itself surfaced no *new* desktop-adapter-layer finding beyond
what §5-§7 already covered.

### Phase DA5 — Duplicate and dead-code removal

After DA1-DA4's parity/usage tests pass:

- Delete `get_project_procurement_commitments`/`list_project_requisitions` (confirmed dead, twice
  now — original audit and this pass's DA0 re-verification).
- Remove the duplicate rate/currency-precedence fallback from one of its two locations
  (`resource_serializer.py` or `resource_options_builder.py`) once both read from the same resolved
  source.
- Remove `compute_schedule_impact` as a separate function once its behavior is folded into
  `build_change_impact`/`ScheduleChangeImpactService.analyse` per the DA3-adjacent P0 fix above.
- Remove `call_with_supported_kwargs` once Projects' `create_project`/`update_project` have explicit
  field mappings (DA1-adjacent cleanup, low urgency per P2).

## Per-capability migration sequence

| Capability | Correctness risk | Security risk | Performance benefit | DTO stability | Migration complexity | Recommended order |
|---|---|---|---|---|---|---|
| Resources | Medium (rate-affecting decision, private-attribute construction) | Low-Medium (no confirmed tenant-isolation bypass, but composition fragility) | Low | High (no DTO changes needed) | Low | **1st** |
| Projects | Medium (tenant-scope resolution duplicated in the adapter) | **Medium-High** (P0: tenant-scope decision in the desktop layer) | Low | High | Low | **2nd** |
| Tasks | Medium-High (two confirmed P0s: hand-rolled permission filtering, silent per-project data loss) | **High** | Medium (N+1 loops, full-list scans) | High | Medium (more call sites than Resources/Projects) | **3rd** |
| Scheduling | Medium (calendar-editing data-loss risk, baseline-flag duplication, the cross-entry-point P0) | Low | Medium | High (only the deliberately-gated error-behavior fix touches contracts) | **Highest** — depends on completing the file audit this pass just closed, and touches both `application/scheduling/` and the platform calendar module | **4th** — do this once the newly-verified findings above are triaged, not before |
| Dashboard | Medium (duplicated thresholds could already disagree; `_build_high_risks_table` divergence risk) | **Medium-High** (P0: `_list_pending_approvals` swallowing auth failures) | Low-Medium | High | Medium (fans out to 6 services, so testing surface is broad even though each individual fix is small) | **5th** |
| Register | Low-Medium | Low | Low | High | Low | **6th** |
| Collaboration | Low (permission-flag drift is a UX risk, not a bypass) | Low | Low-Medium (thread-build redundancy, small scale) | High | Low-Medium | **7th** |
| Timesheets | Low | Low | Low-Medium | High | Low | **8th** |
| Financials | Low (the two live findings are dead code) | None (dead code, unreachable) | N/A (deletion, not optimization) | High | Very low | **9th** (cleanup-only, do whenever convenient) |
| Portfolio | Low | Low | Low | High | Low | **10th** |

**This is not assumed to be the final order** — it is scored from the evidence gathered in this pass;
Tasks and Projects lead specifically because they carry the two highest-confidence P0 security-relevant
findings (hand-rolled permission filtering, tenant-scope resolution in the adapter), which this
document's own migration constraints treat as the type of finding that shouldn't wait for a
convenient migration slot.

## Testing requirements (applied per migrated behavior)

For every behavior actually migrated (not every row in the master table — P3/dead-code rows need
only a deletion-usage-check, not this full list):

1. **Pre-migration characterization test** — pins today's exact output (DA0).
2. **Application/domain unit test** for the moved rule, at its new home.
3. **Desktop API parity test** — same input, same output, before and after migration.
4. **Tenant and permission tests** — required for every P0 finding above (Projects' tenant-scope
   fix, Tasks' permission-filtering fix), and recommended for the rest.
5. **Typed-error propagation test** — required wherever DA2 adds or changes an error signal.
6. **DTO field-for-field parity test** — required for every finding whose "DTO impact" column says
   "No" (i.e., the DTO must provably not have changed).
7. **Integration test** when repository/Reader behavior changes — not applicable to most findings
   here, since DA4 recommends application-layer fixes over new Readers for everything except the
   already-separate Finance Snapshot pilot.
8. **QML presenter test** only where the desktop DTO contract itself changes — per this audit, that
   is limited to: Tasks' `list_all_tasks` (additive `skipped_project_ids` field, if adopted),
   Dashboard's `_list_pending_approvals` (additive partial-failure field, if adopted), and
   Scheduling's calendar placeholder-success fix (gated on separate approval).
9. **Query-count test** for any read migrated in DA4 — none are currently recommended for a Reader
   in this pass (see DA4's scope note), so this requirement is dormant here, reserved for if/when a
   capability's read redundancy is later measured to justify one.

## Architecture guardrails (desktop-adapter specific, added in this pass)

1. `application/**` must not import `api/desktop/**`.
2. `domain/**` must not import `api/desktop/**`.
3. `api/desktop/**` must not import ORM classes (`infrastructure.persistence.orm.**`).
4. `api/desktop/**` must not import concrete repositories (`infrastructure.persistence.repositories.**`,
   `contracts.repositories.**`).
5. Desktop adapter code must not access private (`_`-prefixed) attributes on injected services —
   including private *modules* of another bounded context (the `_approval_labels` finding above is
   the concrete case that makes this rule necessary, not just private attributes on an object).
6. Desktop adapter code must not instantiate application services.
7. Desktop serializers may format values but must not decide authoritative business state (the
   baseline can-submit/can-approve/can-reject and certification-status findings are exactly what
   this rule targets).
8. Desktop builders may compose presentation rows but must not calculate canonical financial or
   scheduling values (the rate/currency-precedence duplication and the overload-threshold
   duplication are exactly what this rule targets).
9. Authorization and tenant-context errors must not become empty results (targets
   `_list_pending_approvals`, `access_resolution_service.py`'s fallback, `list_all_tasks`'s silent
   per-project swallow).
10. New desktop methods must use explicit mapping rather than argument-discarding reflection (no
    new `call_with_supported_kwargs`-style call sites).
11. QML-facing command and response DTOs remain owned by `api/desktop/` — this audit does not
    relocate a single DTO class, and this guardrail locks that decision in for future work touching
    this layer.
12. Query Readers (wherever introduced, per the separate Finance Snapshot pilot or a future
    DA4-driven one) return only immutable, contract-owned facts/read models — never domain entities
    or ORM objects.
13. The composition root owns all concrete service and Reader construction — no `api/desktop/**`
    file may contain a class-instantiation call for a type defined under `application/**` (this
    restates guardrail 6 as a mechanically-checkable rule, not merely a review convention).

---

## Desktop Adapter Audit — Terminal Summary

```text
Document path: docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md
Desktop files inspected: all files under api/desktop/ across 10 capabilities (carried forward from
  the original audit's Appendix A + Desktop Adapter Boundary Weaknesses section) PLUS 9 files
  newly opened in this pass (scheduling/services/{scheduling_facade_service.py,
  dependency_resolution_service.py, calendar_adapter_service.py}, scheduling/serializers/
  {baseline,change_impact,constraint,dependency,resource_load,schedule}_serializer.py), plus
  scheduling/formatters/baseline_formatter.py and utils/scheduling_utils.py reached transitively.
Legitimate presentation behaviors retained (reviewed, not flagged): 4 (Dashboard's documented
  synthetic-preview fallback; scheduling_facade_service.py's engine/task-list dual path;
  constraint_serializer.py/dependency_serializer.py's clean external-classification consumption;
  change_impact_serializer.py's borderline-acceptable derived arithmetic)
Confirmed misplaced responsibilities: 30 rows in the master finding table
  (5 P0, 9 P1, 12 P2, 3 P3/cleanup, one P1/P3 dual-classified dead-code pair counted once)
Count by target owner:
  application service: 11 (rate-affecting decision, tenant-scope resolution, permission-filtering
    fallback, availability-service construction, assignment-preview batching, dashboard
    partial-failure signal, task-list skip signal, timesheet period aggregate, timesheet
    cross-service join, portfolio create-then-return, platform calendar uniform-hours operation)
  domain: 5 (baseline lifecycle flags, remaining-duration-days, certification status, register
    triage ordering, default-calendar convention housed in a platform application service — 4 pure
    domain, 1 platform-application-adjacent)
  Reader/query service: 0 (this pass recommends none — see Phase DA4's scope note; all read-side
    fixes recommended are application-layer aggregates, not new Readers)
  composition root: 4 (both Resources private-attribute/construction findings, the Projects
    tenant-scope-resolution finding's underlying wiring, the calendar-adapter default-resolution
    finding's platform-service dependency)
  compatibility cleanup: 3 (call_with_supported_kwargs, the two dead Financials procurement methods,
    compute_schedule_impact's internal duplication once folded into build_change_impact)
  P0 findings: 5 (schedule-impact divergence between two entry points; Projects tenant-scope
    resolution in the adapter; Dashboard's swallowed-approval-failures; Scheduling's
    placeholder-success calendar branches; Tasks' hand-rolled permission-filtering fallback —
    plus Tasks' silent per-project task-list swallow, also P0, for 6 total if counted individually
    rather than by theme; reported as 5 themes above per the table's row count)
Recommended first desktop-adapter migration: Resources (Phase DA1 — composition-leak fixes with the
  lowest complexity and highest DTO stability), immediately followed by Projects and Tasks for their
  P0 security-relevant findings once DA0's guardrails are in place.
DTOs confirmed to remain under api/desktop/: all of them — no desktop request or response DTO class
  was moved, relocated, or recommended for relocation anywhere in this pass.
Files or behaviors that remain unverified: none from this pass's assigned scope (all 9 previously-
  flagged Scheduling files were opened and verified). Residual, narrower unverified items surfaced
  by this pass itself: whether Dashboard's `_build_high_risks_table` and Register's own filtered
  list actually disagree in practice (flagged as a real divergence *risk*, not confirmed as an
  actual current disagreement, since that would require constructing a fixture proving different
  output for the same data — not done in this pass); whether any calendar in the current dataset
  actually has non-uniform per-weekday hours today (the `hours_per_day` collapse's real-world impact
  depends on this, and was not checked against live/seeded data).
```

