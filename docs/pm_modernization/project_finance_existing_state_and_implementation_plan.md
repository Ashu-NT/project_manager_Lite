# Project Finance Existing-State Audit and Implementation Plan

Status: audit complete; Phase A0, A1, A2, and Phase B1 configuration code gates complete; hosted PostgreSQL validation pending
Last updated: 2026-08-06
Scope: Project Management finance plus reusable platform financial foundations
Current increment: Task-owned WBS, effective-dated rate cards (ADR-PF-005) with the
`CostPolicyEngine`/`LaborCostEngine` cutover, the versioned `ProjectBudget`/`BudgetLine`
lifecycle (item 5, including governed approval integration), and versioned labor
planned-cost snapshots (item 6) are all now implemented and tested (uncommitted); their
design docs (`rate_card_cost_engine_cutover_plan.md`, `project_budget_lifecycle_plan.md`,
`project_planned_cost_snapshot_plan.md`) were deleted 2026-08-06 as fully-superseded
implementation logs once done — see [TODO/README.md](TODO/README.md) and git history for
their content. The planned-cost slice is explicitly tactical/transitional: `TaskAssignment` gained a new
`allocated_planned_hours` field (envelope-constrained against `ProjectResource
.planned_hours`, which remains the authoritative planning total) rather than the fuller
versioned `ProjectLaborPlan`/`LaborPlanAllocation` aggregate a design review recommended;
that fuller model is deferred as a named future phase, not built here. Also fixed as part
of the budget slice's own verification: `project_finance_rate_card_lines`'s Numeric columns
(`rate_amount`/`overtime_multiplier`/`weekend_multiplier`/`holiday_multiplier`) were missing
the `info['financial_numeric']` marker the A1 architecture guardrail requires — a pre-existing
gap masked by ORM-table import order, only surfaced once the new budget table changed that
order. Both rate-card and budget Numeric columns now declare it.
Remaining Phase B scope: repoint baseline comparison/planning reports onto Money and the new
planned-cost snapshots, and replace the QML combined "Budget" section (items 7-8 below),
before Phase C's actual ledger/commitments/time/procurement work.

## 1. Executive Summary

The repository has a useful project-cost reporting feature, but it does not yet have an enterprise Project Finance domain. The current implementation can create one mutable `CostItem` containing planned, committed, actual, and forecast amounts, calculate labor from assignment hours and current resource rates, display summary/ledger/cash-flow/EVM projections, and export reports. Those paths are tenant-aware and the focused baseline is green. They are not sufficient for accounting-grade SaaS behavior because concept lifecycles, source records, posting, reversals, rate snapshots, period control, currency conversion, and immutable history are absent.

Five findings are release blockers for a professional finance upgrade:

1. Monetary amounts use Python/SQL floating point and currency is optional. Mismatched currencies can be excluded from totals, while projects without a currency can numerically combine currencies.
2. `CostItem` conflates budget/planned cost, commitment, actual cost, and forecast. Actuals can be edited and physically deleted; no posting or reversal model exists.
3. Labor actuals use all synchronized assignment hours and the current rate. They do not originate only from approved time, and later rate changes rewrite historical results.
4. Finance reads are authorized with `report.view`, exposing rates and financial data more broadly than the existing `finance.*` permissions imply.
5. Approval application is not demonstrably atomic. The platform approval service invokes a PM cost handler, and that handler calls a cost service that commits before the approval service commits its decision. A later failure can leave the cost mutation applied while the request remains pending.

The recommended target is an incremental extension of the existing Project Management bounded context, not a separate accounting application. Introduce a small platform foundation for `Money`, `CurrencyCode`, decimal-safe quantities/rates, and common rounding because Project Finance, Time, and Procurement are already real consumers. Reuse the existing platform Approval and Enterprise Audit capabilities after strengthening transaction orchestration. Keep budgets, cost codes, rate-card policy, planned costs, commitments, actuals, forecasts, change orders, billing preparation, and profitability inside Project Finance. Time continues to own approved hours; Procurement owns requisitions, purchase orders, and receipts; Party owns supplier/customer identities; official invoices, payments, reimbursement, and the general ledger remain external or future-module responsibilities.

The QML model must follow the corrected backend concepts. Existing `CostItem` dialogs and sections should not constrain the domain design. They should be replaced phase by phase after stable application DTOs exist.

## 2. Repository Areas Inspected

The audit searched domain types, services, contracts, composition, persistence, migrations, desktop APIs, QML controllers/presenters/views, reporting/export, RBAC, tenancy/RLS, shared workflows/events, and tests in these areas:

| Area | Representative evidence |
| --- | --- |
| PM finance domain/application | `src/core/modules/project_management/domain/financials/cost.py`; `application/financials/` |
| PM Project/Task/Resource | `domain/projects/project.py`; `domain/tasks/task.py`; `domain/resources/resource.py` |
| PM persistence/contracts | `contracts/repositories/cost.py`; `infrastructure/persistence/{orm,mappers,repositories}/cost.py` |
| PM desktop adapter | `src/core/modules/project_management/api/desktop/financials/` |
| QML presentation | `src/ui_qml/modules/project_management/{controllers,presenters,qml/workspaces/financials}/` |
| Reporting/import/export | `infrastructure/reporting/`; `infrastructure/importers/financials/` |
| Platform organization/time | `src/core/platform/org/`; `src/core/platform/time/` |
| Platform approval/audit | `src/core/platform/approval/`; `src/core/platform/audit/` |
| Procurement/party | `src/core/modules/inventory_procurement/`; `src/core/platform/party/` |
| RBAC/tenancy/RLS | `src/core/platform/auth/`; `src/infra/persistence/db/postgresql_rls.py`; tenant RLS migrations |
| Composition/events | `src/infra/composition/project_registry.py`; `src/core/shared/events/domain_events.py` |
| Migrations | `src/infra/persistence/migrations/versions/` including baseline, PM upgrades, versioning, cost codes, and RLS |
| Tests | `src/tests/project_management/`, `src/tests/pm/`, and `src/tests/platform/` |

Semantic searches included money/decimal/currency/exchange/rounding, budget/actual/forecast/ETC/EAC, commitment/PO/invoice/billing/revenue, WBS/work package, rate cards, financial periods, approvals/audit, source references/idempotency, soft delete/reversal, and tenant/organization scope.

## 3. Existing Architecture Summary

Project Finance currently follows the repository's established layering:

```text
QML workspace
  -> financials controller/presenter
  -> PM desktop FinancialsApi
  -> CostService / FinanceService
  -> repository contracts
  -> SQLAlchemy PM repositories and ORM
  -> cost_items plus project/resource/task tables
```

`CostService` owns mutable cost CRUD and optional governance approvals. `FinanceService` builds read-only snapshots by composing `CostPolicyEngine`, labor costing, ledger, EVM, analytics, and reporting. `ForecastCostService` exists and has unit tests, but `src/infra/composition/project_registry.py` composes only `FinanceService`; no production composition supplies `forecast_service` to the desktop API. The desktop forecast and commitment builders therefore use fallback formulas that mirror application logic.

The module boundaries are broadly valid and should be retained. The problem is conceptual density inside `CostItem`, not the existence of PM finance under Project Management. Shared platform capabilities already provide tenant context, permission evaluation, generic approvals, enterprise audit storage, organization base currency, and operational calendars. They should be reused rather than copied into finance.

## 4. Existing Finance and Cost Inventory

| Capability | Existing implementation | Layer and exact evidence | Main behavior | Tenant-scoped | Tests | Status |
| --- | --- | --- | --- | --- | --- | --- |
| Project financial settings | `Project.planned_budget`, `Project.currency`, client/site/org references | Domain: `domain/projects/project.py`; ORM: `infrastructure/persistence/orm/project.py` | Stores one optional budget total and currency on Project | Yes, through Project tenant/org scope | `test_currency_defaults.py`, project tests | MINIMAL |
| Manual cost line | `CostItem`, `CostService` | `domain/financials/cost.py`; `application/financials/services/cost_service.py` | One row stores planned, committed, actual, forecast, and vendor/status fields | Yes, inherited through Project in repository queries | `test_cost_domain_validation.py`, `test_cost_flow.py` | INCONSISTENT |
| Cost persistence | `CostItemModel`, `SqlAlchemyCostRepository` | `infrastructure/persistence/orm/cost.py`; `repositories/cost.py` | SQL `Float`; optimistic update version; physical delete | Application-scoped through joined Project; no direct child-table RLS | Repository tenant hardening tests | PARTIAL |
| Cost classification | `CostType`, `CostItem.code` | `domain/financials/cost.py`; cost-code migration | Enum classification and one project-unique line code | Through cost owner | Domain tests | MINIMAL |
| Resource rates | `Resource.hourly_rate`; `ProjectResource.hourly_rate`, `planned_hours` | `domain/resources/resource.py`; `domain/projects/project.py` | Current base rate with project override | Yes | resource/currency tests | MINIMAL |
| Labor costing | `LaborCostEngine` | `application/financials/costs/labor_cost.py` | `TaskAssignment.hours_logged * current selected rate` | Inputs obtained from scoped repositories | finance integration tests | INCONSISTENT |
| Planned labor | `CostPolicyEngine` | `application/financials/costs/cost_policy_engine.py` | `ProjectResource.planned_hours * current rate` | Yes | finance/math tests | PARTIAL |
| PM baseline planned cost | `ProjectBaseline`, `BaselineTask.baseline_planned_cost` | `domain/scheduling/baseline.py`; baseline ORM/service | Snapshots task schedule and one float planned-cost value | Yes | baseline tests | PARTIAL |
| Commitments | `CommitmentStatus`, committed amount on `CostItem` | `domain/financials/cost.py`; `forecasts/forecast_service.py` | Manual amount/status; simple remaining summaries | Yes | forecast/cost tests | MINIMAL |
| Procurement linkage | requisition source reference; desktop procurement serializers | Procurement `domain/procurement/purchasing.py`; PM desktop `financials/api.py` | Lists up to 500 requisitions, then filters project links client-side; reports counts, not PO values | Procurement service is tenant/org scoped | desktop API/procurement tests | INCONSISTENT |
| Actual cost | `CostItem.actual_amount`; calculated labor ledger entries | cost domain and policy/ledger engines | Manually mutable amount plus transient calculated labor | Yes | finance integration/math tests | MINIMAL |
| Time approvals | `TimeEntry`, `TimesheetPeriod` | `src/core/platform/time/domain/timesheet_models.py` | Platform period supports OPEN/SUBMITTED/APPROVED/REJECTED/LOCKED | Direct tenant/org ownership | platform time tests | PARTIAL foundation |
| Forecast | `ForecastCostService`, desktop fallback builder | `application/financials/forecasts/forecast_service.py`; desktop `builders/forecast_builder.py` | Transient ETC/EAC calculation; service not runtime-composed | Service checks scope when used | `src/tests/pm/test_forecast_cost_service.py` | DUPLICATED |
| Cash flow/analytics | cash-flow and analytics builders | `application/financials/cashflow/cashflow_builder.py`; `reporting/analytics.py` | Calendar grouping and `max(committed, actual)` exposure heuristic | Based on scoped data | math/report tests | PARTIAL |
| EVM | EVM calculator/series and finance snapshot | `application/financials/earned_value/` | Computes EVM/KPI values from current weak cost sources | Yes | technical math/report tests | PARTIAL |
| Cost approvals | governed cost add/update/delete | `application/financials/costs/commands/cost_lifecycle.py`; platform approval service | Generic approval request when governance is on; admin bypass | Request carries tenant/org/project | platform approval and cost tests | INCONSISTENT |
| Activity/audit | `record_activity`; Enterprise Audit platform | PM cost lifecycle; `src/core/platform/audit/application/enterprise_audit_service.py` | Cost writes activity feed, not enterprise old/new-state audit | Both scoped | activity/audit tests separately | INCONSISTENT |
| Import | `CostImportSchema`, `CostCsvImporter` | `infrastructure/importers/financials/` | Creates/updates mutable cost rows; no stable external idempotency key | Uses service path | importer tests | PARTIAL |
| Export/reporting | Excel/PDF/report builders | `infrastructure/reporting/exporters.py`; reporting API | Summary, ledger, cash flow, EVM, variance; row/period caps in outputs | Uses scoped services and report permissions | integration/report tests | PARTIAL |
| Budget package | package placeholder | `application/financials/budgets/__init__.py` | Documentation string only | N/A | None | MISSING |
| Invoicing/revenue packages | package placeholders and QML empty states | `application/financials/invoicing/__init__.py`; `revenue/__init__.py`; `FinancialsInvoicesSection.qml` | No domain, persistence, or workflow | N/A | None | MISSING |
| Money/currency foundation | strings, floats, organization base currency | `src/core/platform/org/domain/organization.py`; PM and Procurement types | Uppercases strings; no ISO/minor-unit validation or safe arithmetic | Organization-scoped config only | currency default tests | MISSING |
| Financial periods/FX/accounting refs | no equivalent implementation found | repository-wide semantic search | Operational calendar and generic external references are not financial periods/FX/accounting references | N/A | None | MISSING |
| QML finance workspace | sections/dialog host/list/detail | `src/ui_qml/modules/project_management/qml/workspaces/financials/` | Usable UI over current cost-line model; invoice/PO sections are explicit future states | Controller uses desktop API | presenter/API tests | PARTIAL |

## 5. Current End-to-End Financial Flows

| Flow | Current trace | Authorization and tenancy | Stop point or defect |
| --- | --- | --- | --- |
| Project setup | QML project dialog -> desktop projects API -> project service -> Project repository/table | PM project permission; tenant/org-scoped repository | Stores optional float budget/currency only; independently defaults to `EUR` |
| Cost creation | Financial QML dialog -> `FinancialsApi.create_cost_item` -> `CostService.add_cost_item` -> `CostItem.create` -> cost repository -> `cost_items` -> `costs_changed` | `cost.manage`; Project and Task scope checked; repository joins Project scope | One request may create planned, committed, actual, and forecast amounts simultaneously |
| Governed cost mutation | Cost service -> generic `ApprovalRequest` -> approval decision -> composed cost callback -> CostService -> repository | Generic approval permission; self-approval prevention; tenant/org/project on request | Governance defaults off; admin bypass; nested service commit can precede approval decision commit |
| Cost query | QML refresh -> desktop API -> CostService/FinanceService -> scoped repositories -> serializer/presenter | Cost paths use `cost.read`; aggregate finance uses `report.view` | Sensitive finance is reachable via general report permission |
| Planned labor | FinanceService -> CostPolicyEngine -> ProjectResource + Resource current rate and planned hours | Scoped source repositories | No rate card/effective date/snapshot; assignment task effort is not the authoritative plan |
| Time entry to labor actual | Platform Time service synchronizes `TaskAssignment.hours_logged`; FinanceService reads assignment -> LaborCostEngine -> transient ledger | Time writes are scoped; finance reads scoped assignments | Includes unapproved hours; uses current rate; no generated idempotent posted cost entry |
| Manual commitment | Cost dialog writes `committed_amount` and `CommitmentStatus` on CostItem -> summary projection | `cost.manage` | No commitment line, procurement source, partial matching, invoice amount, close/cancel history |
| Procurement visibility | PM desktop financial API calls procurement list with limit 500 -> client-side project source-reference filter -> requisition count summary | Procurement service enforces tenant/org | No PO/receipt values, typed contract, durable event, commitment/actual generation, or pagination correctness |
| Forecast | Desktop API -> optional ForecastCostService; runtime receives none -> desktop fallback reads CostService and repeats formulas | `cost.read`/service-specific checks | Not persisted, versioned, approved, historical, or single-sourced |
| Financial report/export | FinanceService snapshot -> reporting/export builders -> Excel/PDF/QML | `report.view` and `report.export` | Reliable presentation of an incomplete model; amounts are floats and currency handling is unsafe |
| Billing/revenue/accounting | UI/package placeholders | None | No workflow begins |

The existing local signals in `src/core/shared/events/domain_events.py` refresh process-local UI and projections. They are not a durable integration/outbox mechanism and cannot guarantee exactly-once financial posting across modules.

### Source-specific actual-cost workflows

All source workflows converge on the same canonical `ProjectCostEntry`, but they must not be forced through one artificial lifecycle:

| Source | Workflow | Canonical result | Important rule |
| --- | --- | --- | --- |
| Manual financial entry | DRAFT -> SUBMITTED -> APPROVED -> POSTED | User-originated ProjectCostEntry | Requires explicit create, approve, and post permissions; posted entry is immutable |
| Approved Time | SOURCE_RECEIVED -> VALIDATED -> POSTED | Labor ProjectCostEntry | Trigger from approved time through a stable contract; idempotent by time-entry ID/version; LOCKED must not create a duplicate |
| Procurement | SOURCE_RECEIVED -> VALIDATED -> POSTED or commitment update | Procurement-derived ProjectCostEntry or ProjectCommitment | Exact PO/receipt trigger is governed by ADR-PF-007; source lifecycle remains owned by Procurement |
| External accounting import | IMPORTED -> VALIDATED -> RECONCILED -> POSTED | Externally sourced ProjectCostEntry | Requires external system/reference, import batch, idempotency, and reconciliation evidence |

Workflow state before posting belongs to the source-specific application process. The posted ledger uses one consistent entry model, source metadata, audit policy, reversal rule, and tenant boundary.

## 6. Existing Domain Model

### Current aggregate facts

`CostItem` is a Pydantic-validated dataclass with identity, project/task references, description/code/type, four float amount fields, optional currency, commitment status/vendor/date, and optimistic version. It correctly rejects negative amounts and normalizes text/currency casing. It does not enforce that each monetary amount has a valid currency, model an amount as one value, or constrain lifecycle-specific edits.

`Project` contains `planned_budget` and `currency` alongside operational project data. This is suitable for a lightweight default/reference, but adding budget versions, billing settings, period policy, and rate-card behavior directly would make Project a finance god object. A dedicated `ProjectFinancialProfile` is warranted, with Project retaining only a stable one-to-one reference or convenience projection.

`Resource` and `ProjectResource` carry current hourly rates. They are valid operational defaults, not historical rate cards. `TaskAssignment` carries `hours_logged` and allocation but no applied rate, billable state, cost source, or planned/remaining effort financial snapshot.

`ProjectBaseline` has a mature approval/supersede lifecycle worth reusing as a pattern. `BaselineTask.baseline_planned_cost` is a schedule-baseline snapshot, not a budget authorization or actual-cost ledger.

### Domain invariants absent today

- Money is a signed, decimal-safe value. Arithmetic must reject currency mismatch and use explicit rounding; business aggregates decide whether negative values are allowed.
- Every persisted amount must carry transaction currency; converted amounts must snapshot base currency, rate, date, and source.
- Approved budgets/forecasts and posted actuals must be immutable.
- Corrections to posted actuals use one reversal model: signed postings. An original cost is positive, its reversal is an equal negative entry linked by `reverses_entry_id`, and adjustments are explicitly typed signed entries. No separate debit/credit direction field is used.
- One source record must generate at most one active financial posting per posting purpose.
- Commitment reductions and matched actuals must not be counted twice.
- Approved time must snapshot the selected rate and generate an idempotent labor entry.
- Closed periods must reject posting except through an explicit controlled adjustment path.
- Rates are not bare Money. A reusable `MonetaryRate` pairs Money with a normalized unit, while PM rate-card lines own rate type, selection dimensions, and effective interval. Quantities/hours use decimal-safe values rather than floats.

## 7. Existing Database Model

`cost_items` is the only dedicated finance table. Its amount columns are SQL `Float`; `currency_code` is optional; Project and Task are foreign keys; and `(project_id, cost_code)` is unique. It has a version and useful project/task/type/status indexes but lacks source type/id, posting status/date, period, rate/FX snapshots, reversal links, created/updated actors, direct tenant/org ownership, soft retirement, and immutable-posting constraints. Repository deletion is physical.

Project, Resource, ProjectResource, baseline cost, assignment hours, requisition estimated costs, PO line prices, and receipt unit costs also use float-based storage. Thus fixing only `cost_items` would leave calculations unsafe at their inputs.

Application repositories scope `CostItem` through a join/subquery to Project tenant and organization. PostgreSQL RLS protects directly tenant-owned tables, but `cost_items` has no tenant/organization columns and therefore no equivalent direct policy. Also, repository task validation proves a Task is in the active tenant/org but does not prove it belongs to the supplied Project; the service does this on normal creation, leaving a defense-in-depth gap for direct repository callers.

Relevant migration evidence includes:

- `ef8d1d37eabf_baseline.py`: initial PM float budget/rate/cost structures.
- `i2j3k4l5m6n7_pm_enterprise_upgrade.py`: forecast and commitment fields.
- PM version and cost-code migrations: optimistic versions and line code additions.
- `h6i7j8k9l0m1_enable_postgresql_tenant_rls.py`: RLS on directly tenant-owned tables, not `cost_items`.

At audit time no migration existed. Phase B1 implementation has since added revision `j8k9l0m1n2o3`; Section 20 is the authoritative migration tracker.

## 8. Existing API, Commands, Queries, and Workflows

The active external surface is desktop-only and lives correctly under `src/core/modules/project_management/api/desktop/financials/`. It exposes cost CRUD, project/task/cost lists, snapshots, forecasts, commitment summaries, project-linked requisitions, baseline variance, and option data. Its dataclass commands are adapter DTOs; they are not the right place for domain financial invariants.

Important API findings:

- `FinancialsApi.list_project_requisitions` catches broad exceptions and returns an empty result. Authorization, tenant-context, and infrastructure failures can therefore look like "no requisitions."
- Requisitions are fetched with a fixed limit of 500 and filtered in the PM adapter by string source-reference fields. This can omit valid records and is not a stable integration contract.
- The dedicated forecast service is optional in the factory/API. Composition never provides it, so fallback calculations in desktop builders are the production path.
- Currency/default and display logic is duplicated. Three PM desktop money formatters independently convert floats and format strings.
- The QML "Budget" detail is a selected cost line's planned amount, not a versioned project budget. This label must change during adapter/UI migration.

The correct direction is backend-first: explicit commands for profile, budget versions, rate cards, planned-cost refresh, commitment ingestion, actual posting/reversal, forecast versions, and change application. The desktop adapter then maps these contracts for QML. No compatibility facade is required merely to preserve the misleading combined `CostItem` editor, although staged read compatibility is required while legacy data exists.

## 9. Existing Permissions and Tenant Isolation

The permission catalog already contains `cost.read`, `cost.manage`, `finance.read`, `finance.manage`, and `finance.export`. Project-scoped PM roles include cost/report capabilities. `CostService` consistently checks `cost.read`/`cost.manage`, but `FinanceService` uses `report.view`. Therefore the catalog intent and runtime behavior diverge.

Tenant isolation is generally strong in normal service/repository paths:

- Cost repository methods require an active `TenantContextService` and join Project tenant/org scope.
- Project, Task, Resource, Time, Procurement, Approval, and Audit repositories are tenant/org aware.
- Repository composition injects tenant context centrally.
- Approval requests carry tenant, organization, and project context.
- PostgreSQL sessions set tenant/org/user RLS variables and validate that the application role does not bypass RLS.

Required corrections:

- Replace `report.view` finance authorization with specific finance permissions.
- Split mutation permissions by lifecycle action; deciding an approval must not imply creating, posting, reversing, or exporting.
- Add a distinct sensitive-finance permission for internal rates, margins, and detailed labor cost.
- Remove role/admin shortcuts from financial approval policy. Emergency overrides must be an explicit permission with mandatory reason and audit.
- Give new finance transaction tables direct tenant and organization ownership, RLS policies, and scoped unique constraints.
- Validate every cross-reference under the same tenant/org and ensure Task/Project, Resource/Project, supplier/org, period/org, and cost-code/org relationships agree.
- Do not return empty data on authorization/context exceptions.

## 10. Existing Tests

Focused baseline run on 2026-08-02:

```text
29 passed in 11.45s
```

The run covered cost domain validation, CRUD flow, currency defaults, finance integration, math/report policy, forecast service, desktop finance API, and QML finance presenter tests.

Current strengths include nonnegative validation, versioned cost updates, basic CRUD/summary behavior, finance snapshot consistency, EVM/report formula coverage, desktop serialization, and a tenant-hardening repository suite. Platform Time, Approval, Activity, and Enterprise Audit also have their own tests.

Coverage does not currently prove safe money arithmetic, ISO currency validity, FX snapshots, approved-time-only costing, historical rate stability, posting/reversal, period locking, idempotent source ingestion, commitment matching, approval transaction atomicity, financial separation of duties, sensitive-field permissions, or end-to-end cross-tenant finance references. `ForecastCostService` unit tests also do not prove runtime use because it is not composed.

## 11. Capability Assessment

### 11.1 Project Financial Profile

**Status: Phase B1 foundation implemented.** `ProjectFinancialProfile` now owns currency, financial lifecycle/dates, billable/funded state, billing method, budget-control mode, cost-code policy, and default cost-code reference with one profile per scoped Project and optimistic concurrency. New projects create the profile atomically; revision `j8k9l0m1n2o3` backfills existing profile currency from valid Project data or Organization base currency. Mutations require global and project-scoped finance permission and fail-closed Enterprise Audit. `Project.currency` remains a marked synchronized compatibility projection until desktop/read-model cutover. Rate-card default, period policy, overrun tolerance, and the proper versioned Budget aggregate remain later Phase B/C work; legacy planned budget was intentionally not copied into a second temporary total.

### 11.2 Cost Codes

**Status: Phase B1 foundation implemented.** PM-owned `ProjectCostCode` now provides scoped unique identity, hierarchy/cycle guards, effective/active state, external-system mappings, optimistic concurrency, project restrictions, default-code safeguards, direct tenant/organization ownership, scoped foreign keys, and PostgreSQL RLS policy setup. `CostType` and `CostItem.code` remain legacy classification/line references and are not silently converted into canonical identities. Their reviewed migration mapping remains future reconciliation work. Cost code is "what" and remains separate from WBS "where."

### 11.3 Work Breakdown Structure

**Status: IMPLEMENTED.** ADR-PF-003's Task-owned WBS is built: `Task.parent_task_id`/`wbs_code`
with cycle prevention, project-unique code validation, and migration backfill
(`test_task_wbs_migration.py`). Project Finance references stable Task/WBS IDs and never owns
hierarchy mutation. A separate WorkPackage aggregate remains deferred unless a proven
non-schedulable financial-node requirement appears.

### 11.4 Rate Cards

**Status: IMPLEMENTED, including the cost-engine cutover (2026-08-05).** ADR-PF-005's
7-level cost/billing precedence, effective-dated lines, ambiguity failure, explicit
modifiers, and immutable `RateSelectionSnapshot` are built and tested
(`domain/financials/rate_cards.py`, `application/financials/rate_cards/`). `CostPolicyEngine`
and `LaborCostEngine` now resolve both planned and actual labor rates through
`LaborRateResolver.resolve_many` (batched, tenant/org-scoped, explicit `as_of`) instead of
reading `ProjectResource.hourly_rate`/`Resource.hourly_rate` directly — see
`rate_card_cost_engine_cutover_plan.md` (deleted, fully superseded; see git history). Resources
still carry `hourly_rate`/`currency_code` as inputs, but they now only reach cost
calculations by auto-seeding a `legacy_seeded` rate-card line at creation/update time; the
engines never read those fields directly. Unresolved rates are excluded from totals (not
zeroed) and surfaced through `unresolved_labor_rates`/`labor_rates_complete` up to the
desktop `FinancialSnapshotDto`. `EVM.get_actual_cost` fails closed
(`ACTUAL_COST_INCOMPLETE`) rather than understating AC.

### 11.5 Budgeting

**Status: IMPLEMENTED (2026-08-06).** Versioned `ProjectBudget`/`BudgetLine` aggregates are built with the full DRAFT -> SUBMITTED -> APPROVED/REJECTED, APPROVED -> SUPERSEDED/CLOSED lifecycle, immutable approved versions (one approved + optionally one open version per project, both DB-enforced), currency (immutable once lines exist), cost-code/task(WBS) line dimensions, and governed approval integration through the existing Platform Approval service — see
`project_budget_lifecycle_plan.md` (deleted 2026-08-06, fully implemented/verified; see git
history). `Project.planned_budget` remains the BAC/threshold source this phase; no `CostPolicyEngine`/`EarnedValueCalculator` cutover onto approved budget totals yet (a future cutover plan, mirroring the rate-card cutover, will do that separately).

### 11.6 Planned Costing

**Status: IMPLEMENTED (tactical), assignment-labor-only (2026-08-06).** Versioned
`ProjectPlannedCostVersion`/`ProjectPlannedCostLine` snapshots (CURRENT/SUPERSEDED, no
approval lifecycle — see `project_planned_cost_snapshot_plan.md`, deleted 2026-08-06: its
design deviated from what was actually built, see 11.6 below for the accurate shape)
are built and tested, sourced from `TaskAssignment.allocated_planned_hours` resolved through
the same rate-card resolver `CostPolicyEngine`/`LaborCostEngine` use, with source lineage
(`source_assignment_id`), WBS (`task_id`), and cost-code (the project's single
`ProjectFinancialProfile.default_cost_code_id` — a stated, coarser-than-`BudgetLine`
limitation) dimensions. Completeness is tracked as three independent flags
(`rates_complete`/`allocations_complete`/`cost_codes_complete`) plus diagnostic reason codes,
not one ambiguous flag. `ProjectResource.planned_hours` remains the authoritative
project-resource planning envelope; `allocated_planned_hours` is a constrained WBS
distribution of it, enforced at write time, not an independent planning total — a design
review's recommendation to instead build a full versioned `ProjectLaborPlan`/
`LaborPlanAllocation` aggregate (its own DRAFT/SUBMIT/APPROVE lifecycle) was deliberately
deferred as a larger, separately scoped future phase rather than done here. Manual/material
planned-cost lines and baseline-comparison sourcing remain unimplemented in this slice.

### 11.7 Commitments

**Status: MINIMAL.** A mutable amount/status/vendor reference on `CostItem` does not model commitment lines, partial invoicing/fulfilment, cancellation, closure, or matching. Procurement has the authoritative requisition/PO/receipt lifecycles, but PM only consumes requisition counts. Create PM financial commitment projections linked idempotently to Procurement PO lines and allow controlled manual commitments. Procurement remains owner; integration events/contracts carry source IDs, currency, amount, supplier, project/task/WBS/cost code, and lifecycle. Exposure must use open commitment remainder, not `max(committed, actual)`.

### 11.8 Actual Costs

**Status: MINIMAL and unsafe.** Manual `actual_amount` and transient labor ledger rows have no source identity, approval/posting lifecycle, period, reversal, idempotency, or immutable history. Create PM `ProjectCostEntry` with DRAFT -> SUBMITTED -> APPROVED -> POSTED -> REVERSED, direct tenant/org/project ownership, Money plus optional snapshotted base Money/FX, transaction/posting dates, period, dimensions, source type/id, and reversal relationship. Posted rows cannot update or delete. Legacy actual amounts migrate to clearly marked manual legacy entries after currency resolution.

### 11.9 Timesheet Costing

**Status: INCONSISTENT.** Platform Time owns entries and approved/locked periods, but PM finance uses aggregate `TaskAssignment.hours_logged` and current rates. This can include unapproved time and makes history change when a rate changes. Add an integration/use case triggered only by approved time-period state, query approved entry details through a Time contract, resolve and snapshot the applicable rate, and post one idempotent labor cost per time entry/version. Rejection or approved correction creates reversal/replacement entries. Add billable metadata only through an explicit time/project billing contract.

### 11.10 Expenses

**Status: MISSING.** No expense claim/line/receipt/reimbursement domain was found; "expense" in analytics is only a label for cost categories. Product must decide whether a future Expenses module owns claims. Project Finance should consume finance-approved expense lines and create actual-cost projections; it should not own payroll reimbursement. If a PM-only first slice is required, keep claim workflow in a dedicated business module and reference Project/Task/CostCode through contracts.

### 11.11 Forecasting

**Status: MINIMAL and DUPLICATED.** `ForecastCostService` calculates transient ETC/EAC but is not composed; desktop builders duplicate fallback logic. No forecast aggregate, periods, lines, versions, approval, manual adjustments, or historical comparison exists. First establish one calculation service and remove fallback duplication after composition. Then create versioned ProjectForecast/ForecastLine with automatic source snapshot plus controlled adjustments and DRAFT/SUBMITTED/APPROVED/SUPERSEDED lifecycle.

### 11.12 Estimate to Complete

**Status: MINIMAL.** ETC is derived by forecast/EVM formulas from weak planned/actual/commitment data. It is not a distinct, dimensioned, persisted, or approved estimate, and the `max` exposure heuristic is not a robust double-count policy. Define source precedence per forecast line: matched commitment, remaining plan, manual estimate, risk/contingency. Store calculation origin and exclusions so an amount cannot be open commitment and remaining plan simultaneously.

### 11.13 Change Control

**Status: MINIMAL.** The generic PM register supports a `CHANGE` entry with narrative impacts but no typed budget, cost, revenue, forecast, contract, or schedule deltas and no APPLIED financial state. Create PM `ProjectFinancialChange` linked to the existing change/register item where appropriate. Approval must atomically create a new budget/forecast version and record applied references; direct mutation of approved versions is forbidden.

### 11.14 Financial Approvals

**Status: PARTIAL and transactionally unsafe.** Platform Approval supplies tenant/project context, decisions/history, and self-approval prevention. PM cost governance can create generic requests, but defaults off, allows an admin shortcut, has no amount/currency thresholds, steps, delegation/escalation, or finance-specific policy. More critically, `src/core/platform/approval/application/approval_service.py` calls an apply handler before committing the approval decision, while the cost handler composed in `src/infra/composition/project_registry.py` invokes a committing CostService. Refactor to a shared unit of work so state transition, financial mutation, outbox/audit, and approval decision commit or roll back together. Extend the existing approval engine; do not create a finance-only engine.

### 11.15 Billing

**Status: MISSING.** The invoicing package and QML invoice section are placeholders. There is no contract, billing method/schedule, billable-time/expense selection, unbilled ledger, preparation, approval, or duplicate-billing prevention. PM may own `ProjectBillingPreparation` for fixed price, milestone, T&M, cost-plus, unit, and recurring source selection. Official invoices and payments should be sent to/reconciled from a future Billing/Accounting integration, not implemented as a general ledger in PM.

### 11.16 Revenue and Profitability

**Status: MISSING.** There is no contract value, planned/earned/billable/invoiced/paid revenue, margin, or profitability aggregate. Add only after billing/revenue product scope is decided. PM can own project contract-value and planning projections plus margin reporting. Official revenue recognition and payment remain external unless explicitly brought into product scope. Profitability must compare revenue with actual/forecast cost, not budget.

### 11.17 Currency Management

**Status: INCONSISTENT and release-blocking.** Amounts are floats, currencies are optional strings, multiple services hard-code `EUR`, and no FX/rounding/snapshot model exists. `Organization.base_currency` is a useful configuration source but only uppercases text. Introduce platform `CurrencyCode`, `Money`, and `RoundingPolicy`; migrate SQL amounts to explicit `Numeric`; reject mixed-currency arithmetic. Introduce an exchange-rate contract/snapshot only when conversion is requested. PM owns when a rate is applied; the shared foundation owns safe conversion mechanics.

### 11.18 Financial Periods

**Status: MISSING.** Cash-flow month/quarter/year grouping and the operational enterprise calendar do not constitute fiscal periods or posting controls. Create organization-owned financial/fiscal periods in a small platform foundation when actual posting is introduced because Procurement, Billing, and Project Finance are genuine consumers. PM owns whether a project transaction can post into the selected period. Never overload scheduling calendars with accounting closure semantics.

### 11.19 Financial Reporting

**Status: PARTIAL.** Snapshot, ledger, cash flow, EVM, KPI, baseline variance, Excel, and PDF are useful and tested. Their correctness is bounded by float values, missing currencies, mutable source data, current-rate labor, heuristics, and output caps. Retain report builders as read-model consumers, then repoint them to posted actuals/open commitment remainders/versioned forecasts. Add explicit as-of date, currency basis, financial period, source lineage, sensitive-field policy, pagination, and reconciliation totals.

### 11.20 Audit Trail

**Status: INCONSISTENT.** Cost mutations write shared Activity entries, while `EnterpriseAuditService` already supports actor, tenant/org, entity, old/new state, source/request metadata, and has tests. Finance should continue emitting user-facing activity but must also record immutable enterprise audit within the mutation unit of work. Posted entries, reversals, approvals, rate/FX selection, import source, overrides, and period exceptions require dedicated audit actions.

### 11.21 Accounting Integration

**Status: MISSING.** Party external references and Department cost-center code are isolated strings, not typed accounting integration contracts. No GL account, reconciliation, external transaction, export status, or idempotency model exists. Add stable reference value objects/contracts only when integration begins. PM exports posted project entries and receives acknowledgements/reconciliation references; it must not implement ledger, payment, or tax accounting behavior.

## 12. Cross-Module Impact

### 12.1 Project

Add a one-to-one financial profile reference/projection. Do not add budget versions, rate lines, or transaction histories directly to Project. Existing planned budget/currency become compatibility projections and are retired only after migration parity.

### 12.2 Task

Keep operational ownership in PM Tasks. Add hierarchy/WBS support only after the product decision. Finance references Task and optional WorkPackage IDs and validates they belong to the same Project/tenant/org.

### 12.3 Resource

Keep current hourly rate as an operational default during transition. Effective-dated rate cards own authoritative cost/billing rates; posted entries snapshot the selected value.

### 12.4 Resource Assignment

Add or expose planned/remaining effort and billability references only if operational planning needs them. Do not store mutable actual financial amounts on assignments. Financial entries reference source assignment/time IDs.

### 12.5 Timesheet

Platform Time remains owner of entries, periods, approval, and locked hours. It needs a stable query/event contract that exposes approved entry identity/version, date, hours, resource/employee, project/task/work-allocation, and correction state. Finance owns generated cost/revenue postings and idempotency.

### 12.6 Tenant and Organization

Organization base currency becomes the default source, not a hard-coded service constant. Add supported currency and fiscal-period configuration when needed. Every new aggregate and source-reference query is directly tenant/org scoped and RLS protected.

### 12.7 Supplier and Customer

Party remains the shared identity owner. Procurement owns supplier PO/receipt behavior. Add/clarify customer party semantics, contract/billing references, and validation without duplicating Party. Financial records snapshot display/reference values needed for history.

### 12.8 RBAC

Replace umbrella cost/report access with explicit read-sensitive, create, submit, approve, post, reverse, manage profile/rates/budgets/forecasts, export, and override permissions. Keep permission checks in application services and query policies.

### 12.9 Audit

Reuse Enterprise Audit storage and correlation metadata. Activity remains a presentation feed, not the authoritative financial audit log. Integration events should carry audit/correlation IDs.

### 12.10 Reporting and Integrations

Reports consume stable finance read models. Cross-module financial updates use contracts and durable outbox/inbox processing rather than importing another module's repository or relying only on process-local signals.

## 13. Tenant-Isolation and Security Findings

| Priority | Finding | Evidence | Required treatment |
| --- | --- | --- | --- |
| P0 | General report permission exposes finance data | `FinanceService` checks `report.view`; policy catalog separately defines `finance.*` | Switch to finance-specific query policy before exposing richer rates/margins |
| P0 | Approval application can commit before approval decision | approval service apply-handler order plus committing PM CostService callback in `project_registry.py` | One unit of work and one outer commit; add failure-injection tests |
| P0 | Admin session bypasses financial governance | cost lifecycle governance branch | Replace with explicit audited override permission or remove bypass |
| P1 | Cost child table lacks direct RLS ownership | `cost_items` has no tenant/org; RLS migration protects direct-owner tables | New finance tables carry tenant/org and policies; optionally backfill legacy table |
| P1 | Repository task scope does not prove Task belongs to Cost Project | cost repository validates active tenant/org task; service validates project relation | Enforce in repository/application and, where feasible, schema relation/trigger |
| P1 | Sensitive internal rates/margins lack field-level policy | same snapshot served under broad report permission | Add `project_finance.read_sensitive`; redact DTOs otherwise |
| P1 | Broad exception becomes empty procurement result | desktop financial API | Preserve typed authorization/context/infrastructure errors |
| P2 | Fixed 500-row cross-module scan can hide linked records | desktop requisition query/filter | Add typed paginated project-source query contract |
| P2 | No durable cross-module delivery or idempotent consumer | local `domain_events` Signal hub | Transactional outbox/inbox for postings; local signals remain UI refresh only |

All identifier-based operations must test Tenant A against Tenant B IDs for Project, Task, Resource, assignment, time entry, supplier/customer, cost code, budget, period, source document, approval request, and reversal target. Missing tenant or organization context must fail closed.

## 14. Financial Integrity Findings

| Priority | Finding | Consequence | Corrective principle |
| --- | --- | --- | --- |
| P0 | Float money in domain and SQL | Rounding drift and unstable equality/aggregation | `Decimal` Money and SQL `Numeric`, explicit scale/rounding |
| P0 | Optional/unchecked currency and hard-coded defaults | Wrong totals and misstatement | Required currency, ISO validation, organization-derived defaults |
| P0 | Mixed currencies skipped or summed | Silent incomplete or invalid reports | Reject/report mismatch or convert with snapshotted FX |
| P0 | Mutable/physically deletable actuals | History can be rewritten | Immutable posted entries and linked reversals |
| P0 | Unapproved time and current rates drive actual labor | Premature and retroactively changing cost | Approved-time source plus rate snapshot/idempotent posting |
| P0 | Combined CostItem financial stages | Double counting and invalid lifecycle combinations | Separate planned, commitment, actual, forecast responsibilities |
| P1 | No source identity/idempotency | Duplicate import/event posting | Scoped source uniqueness and inbox/idempotency key |
| P1 | No period/posting controls | Closed history can move | Financial periods and explicit posting date/status |
| P1 | `max(committed, actual)` heuristic | Incorrect exposure as matching evolves | Commitment-line matching and remaining balance |
| P1 | No immutable budget/forecast versions | No authorization/history basis | Versioned lifecycle and supersede semantics |
| P1 | Forecast logic duplicated and runtime service absent | Divergent calculations | Compose one application service; delete fallback after cutover |
| P2 | Report/export caps and weak lineage | Incomplete exports and poor reconciliation | Pagination, as-of/basis metadata, control totals, source trace |

## 15. Architectural Mapping

### Platform-foundation decisions

| Concept | Existing implementation | Existing location | Current consumers | PM dependency | Reusable | Recommended owner | Action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Money | Float amounts and three PM formatters | PM domain/ORM/desktop; Procurement purchasing domain | PM, Procurement, Portfolio planning | None in the primitive | Yes | Platform finance foundation | EXTRACT_TO_PLATFORM |
| CurrencyCode | Uppercased strings; `Organization.base_currency` | Platform Org plus module entities | PM, Procurement, Organization/Site | None in universal code | Yes | Platform finance foundation; tenant policy remains Org | EXTRACT_TO_PLATFORM |
| RoundingPolicy | No implementation found | N/A | PM and Procurement need it | None | Yes | Platform finance foundation | EXTRACT_TO_PLATFORM |
| DecimalQuantity | Float hours, quantities, and allocation | Platform Time; PM assignments; Procurement lines | Time, PM, Procurement | None in the primitive | Yes | Platform common/finance foundation | EXTRACT_TO_PLATFORM |
| MonetaryRate | Hourly rate and unit price represented as float | PM Resource/ProjectResource; Procurement lines | PM, Procurement | None in the primitive | Yes | Platform finance foundation | EXTRACT_TO_PLATFORM |
| ExchangeRate and conversion | No implementation found | N/A | PM first; Billing/Procurement likely | Conversion primitive has none | Not yet two active conversion users | Platform contract/value objects when Phase C requires it | DEFER, then EXTRACT_TO_PLATFORM |
| Organization base-currency policy | `Organization.base_currency` | `src/core/platform/org/domain/organization.py` | All organization-scoped modules | None | Yes | Platform Organization | UPGRADE_IN_PLACE |
| Financial/Fiscal Period | Operational calendar only | Platform calendar/time areas | PM, Procurement/Billing once posting exists | Shared period has none | Yes once posting is cross-module | Platform finance foundation | DEFER to Phase C, then EXTRACT_TO_PLATFORM |
| Generic approvals | `ApprovalRequest`, `ApprovalService`, policy | `src/core/platform/approval/` | Platform, PM, Procurement | None | Yes | Existing Platform Approval | UPGRADE_IN_PLACE |
| Financial approval rules | Cost governance flag and payload | PM cost lifecycle | PM | Yes | No | Project Finance | KEEP_IN_PROJECT_FINANCE |
| Enterprise audit | `EnterpriseAuditService` and persistence | `src/core/platform/audit/` | Multiple modules | None | Yes | Existing Platform Audit | REUSE_AS_IS with transaction integration |
| User-facing activity | Activity entry/service | `src/core/platform/activity/`; PM recorder | Multiple modules | None | Yes | Existing Platform Activity | REUSE_AS_IS, not as finance audit |
| External accounting references | Party external ref; Department cost-center string | Platform Party/Org | Party, Org, future integrations | Reference type has none | Potentially | Platform value objects/contracts | REFERENCE_THROUGH_CONTRACT when integration starts |
| Idempotency/integration envelope | No finance implementation; local Signals only | `src/core/shared/events/domain_events.py` | PM/Time/Procurement integration | Generic envelope has none | Yes | Existing/shared integration infrastructure if available; otherwise small platform contract | UPGRADE_IN_PLACE or EXTRACT_TO_PLATFORM |
| Project cost codes | `CostType`, `CostItem.code` | PM finance | PM only | Direct | No | Project Finance | KEEP_IN_PROJECT_FINANCE; deprecate ambiguous line-code use |
| Project rates | Resource and ProjectResource current rates | PM Resource/Project | PM only | Direct | No | Project Finance, with Resource defaults referenced | KEEP_IN_PROJECT_FINANCE |
| Budgets/plans/commitments/actuals/forecasts | Combined `CostItem` and projections | PM finance | PM only | Direct | No | Project Finance | CREATE/UPGRADE in PM; deprecate combined model |
| Purchase orders/receipts | Procurement aggregates | Inventory Procurement | Procurement, PM consumer | No | Owned business data, not primitive | Inventory Procurement | KEEP_IN_EXISTING_MODULE |
| Approved hours | Time entries and periods | Platform Time | Time, PM finance consumer | No | Owned business data | Platform Time | KEEP_IN_EXISTING_MODULE |
| Supplier/customer identity | Party | Platform Party | Multiple modules | No | Yes | Platform Party | KEEP_IN_EXISTING_MODULE |
| Official invoice/payment/GL | No implementation | N/A | Future Billing/Accounting | No | Separate business ownership | External system or future bounded context | REFERENCE_THROUGH_CONTRACT / DEFER |

### Cross-module consumer analysis

| Foundation | Project Finance | Procurement | Inventory | Billing/Subscriptions | Decision |
| --- | ---: | ---: | ---: | ---: | --- |
| Money | Yes | Yes: estimated cost, PO price, receipt cost | Likely for valuation | Future | Build now; two current consumers justify platform ownership |
| CurrencyCode | Yes | Yes | Site/item valuation may use it | Future | Build now; universal code separate from tenant configuration |
| RoundingPolicy | Yes | Yes once Money is adopted | Likely | Future | Build with Money to prevent divergent arithmetic |
| DecimalQuantity | Yes: hours/allocation/units | Yes: requested/ordered/received quantities | Yes | Future | Build as a dependency-free decimal primitive |
| MonetaryRate | Yes: hourly/daily/unit rates | Yes: price per UOM | Yes: valuation rate may consume it | Future | Share amount-per-unit invariant; keep rate-card selection in PM |
| ExchangeRate | Yes when multi-currency is enabled | Possible | Possible | Future | Define only required value/port first; no speculative provider |
| FinancialPeriod | Yes for posting/forecast | Yes when commitment/receipt posting is integrated | Possible | Future | Build in Phase C when posting creates multiple real consumers |
| ProjectCostCode | Yes | No; Procurement may carry a reference | No | No | PM-owned, never platform-owned |
| Approval engine | Reuse | Reuse | Reuse | Reuse | Upgrade existing engine transaction/policy extension points |
| Enterprise audit | Reuse | Reuse | Reuse | Reuse | Reuse existing storage and service |

### Recommended logical target

This is a logical decomposition under existing PM layers, not a mandatory mass file move:

```text
src/core/platform/finance/
  money/                 # Money, CurrencyCode, rounding only
  exchange_rates/        # value/port when conversion is implemented
  periods/               # organization fiscal periods in Phase C

src/core/modules/project_management/
  domain/financials/
    profiles/
    cost_codes/
    rates/
    budgets/
    planned_costs/
    commitments/
    actuals/
    forecasts/
    change_control/
    billing/
  application/financials/
  contracts/financials/
  infrastructure/persistence/financials/
  api/desktop/financials/
```

Existing paths may be evolved incrementally instead of immediately creating every folder. Approval stays in `src/core/platform/approval`; Audit stays in `src/core/platform/audit`. Platform finance must never import Project, Task, Resource, Timesheet, Budget, Forecast, or Project Cost types.

### Aggregate ownership and mutation boundaries

| Aggregate root | Owns | References only | Mutation boundary |
| --- | --- | --- | --- |
| `ProjectFinancialProfile` | Project finance configuration and defaults | Project, Organization, default cost-code/rate-card/calendar IDs | Canonically mutates only its profile; the application layer temporarily synchronizes legacy `Project.currency` under deletion marker `PF-B1-CURRENCY-DUAL-WRITE` |
| `ProjectCostCode` | Code identity, hierarchy position, effective/active state, mappings | Organization, optional parent code | Mutates one code hierarchy under a catalog policy; projects carry restrictions/references |
| `ProjectRateCard` | Version/effective-dated rate lines and precedence metadata | Project, Resource, Role/Skill/Department/Customer references | Selects/snapshots rates; never rewrites Resource or posted entries |
| `ProjectBudget` | Budget version, lifecycle, and budget lines | Project, CostCode, WBS/Task, Period, approval | One version is the consistency boundary; approval/supersede creates state/version transitions |
| `ProjectPlannedCostVersion` | Planned-cost snapshot and lines | Plan source, Project, Task/WBS, Resource, CostCode, rate snapshot | Recalculation creates a new version; it does not mutate an approved budget |
| `ProjectCommitment` | Financial commitment projection, lines, matches, and remaining balance | Procurement source, supplier Party, Project dimensions, matching CostEntry IDs | Procurement facts are consumed; the aggregate cannot mutate Procurement or CostEntry |
| `ProjectCostEntry` | Posted actual/adjustment/reversal lifecycle and financial snapshots | Project, Task/WBS, Resource, CostCode, source, Period, reversed entry | Each entry is immutable after posting; reversal is a new signed entry, not mutation |
| `ProjectForecast` | Forecast version, lines, source/exclusion metadata, and lifecycle | Budget version, commitment/cost-entry IDs, plan version, Project dimensions | One forecast version is the boundary; application orchestration reads other aggregates |
| `ProjectFinancialChange` | Proposed impacts, approval, and application references | Budget/Forecast versions, schedule/change/register references | Approval application orchestrates creation of new versions atomically; no direct cross-aggregate mutation |
| `ProjectBillingPreparation` | Billing batch/version and selected source lines | Customer/contract, billable Time/Expense/Milestone IDs, external invoice reference | Locks source selection idempotently; official invoice remains externally owned |

Cross-aggregate operations belong in application orchestration under one explicit unit of work. Aggregates may retain stable IDs and immutable snapshots from other owners, but they do not call or mutate one another.

### Money, quantity, and rate decisions

- `Money` supports negative, zero, and positive values. It contains only Decimal amount and CurrencyCode plus safe arithmetic/rounding.
- Budget, planned-cost, and commitment aggregates normally require non-negative Money. Manual original actual postings normally require positive Money.
- ProjectCostEntry uses signed posting values. Reversals are exact negative linked entries; no second direction/sign mechanism is permitted.
- `DecimalQuantity` carries a Decimal value and normalized unit where applicable. Hours, days, units, kilograms, and percentages cannot enter finance calculations as binary floats.
- `MonetaryRate` is Money per normalized unit. PM's `ResourceCostRate`/rate-card line adds cost-versus-billing type, dimensions, precedence, and effective dates without duplicating Money arithmetic.

## 16. Dependency Map

```text
Platform Common IDs / Pydantic / Exceptions
        |
        +--> Platform Finance: Money, CurrencyCode, Rounding
        |          |
        |          +--> Procurement monetary fields
        |          +--> PM Project Finance monetary fields
        |
        +--> Platform Organization: base/supported currency
        +--> Platform Approval: generic request/decision/history
        +--> Platform Audit: immutable audit storage
        +--> Platform Time: approved hours
        +--> Platform Party: supplier/customer identity
                   |
Inventory Procurement: PO/receipt ownership --contract/event--> PM Project Finance
Platform Time: approved time ownership --------contract/event--> PM Project Finance
Platform Party: identities ---------------------------reference--> PM Project Finance

PM Project / Task / Resource / Scheduling
        |
        +--> PM Project Finance aggregates and policies
                    |
                    +--> PM finance query/read models
                    +--> Desktop API DTOs
                    +--> QML controller/presenter/workspace
                    +--> Reports/exports
                    +--> external accounting/billing contracts
```

Rules:

1. QML never calls repositories or recalculates authoritative finance formulas.
2. Desktop DTOs may be redesigned; the domain is not shaped around current dialogs.
3. Other modules do not mutate PM finance aggregates or import PM repositories.
4. Integration consumers are idempotent and execute inside a unit of work with posting, audit, and outbox/inbox state.
5. Read models may denormalize names/codes, but source aggregate ownership remains explicit.
6. The reporting layer consumes one canonical calculation/read-model service; it does not duplicate forecast policy.

## 17. Gap Matrix

| Capability | Current status | Priority | Keep/reuse | Required target |
| --- | --- | --- | --- | --- |
| Project financial profile | MINIMAL | P1 | Project org/site/client references | Dedicated versioned profile and policy defaults |
| Cost codes | MINIMAL | P1 | Legacy code/type as migration input | Tenant/org catalog, hierarchy, effective state, mappings |
| WBS | IMPLEMENTED | P2/product gate | Task hierarchy is the accepted model | Done: `Task.parent_task_id`/`wbs_code` with cycle prevention and migration |
| Rate cards | IMPLEMENTED, engines cut over | P0 for actual costing | — | Done: ADR-PF-005 precedence + `CostPolicyEngine`/`LaborCostEngine` cutover (2026-08-05) |
| Budgeting | IMPLEMENTED | P1 | Baseline lifecycle pattern | Done: versioned `ProjectBudget`/`BudgetLine` with governed approval (2026-08-06) |
| Planned costing | IMPLEMENTED (tactical, assignment-labor-only) | P1 | Existing assignment/resource inputs | Done: versioned `ProjectPlannedCostVersion`/`ProjectPlannedCostLine` (2026-08-06); baseline-comparison sourcing and a full `ProjectLaborPlan` model remain deferred |
| Commitments | MINIMAL | P0/P1 | Procurement ownership and source refs | PM projections, matching, remaining balance, lifecycle |
| Actual costs | MINIMAL | P0 | Legacy data as migration source | Posted immutable ledger, reversals, periods, idempotency |
| Timesheet costing | INCONSISTENT | P0 | Platform approved-time ownership | Approved-only idempotent labor postings with rate snapshot |
| Expenses | MISSING | P3/product gate | None | External/future module ownership plus PM projection |
| Forecasting | MINIMAL/DUPLICATED | P1 | Existing formulas/tests after single-sourcing | Versioned forecasts and lines |
| ETC | MINIMAL | P1 | Formula concepts | Source precedence and anti-double-count controls |
| Change control | MINIMAL | P2 | Existing register/change references | Typed financial impacts and atomic application |
| Financial approvals | PARTIAL | P0 | Platform Approval | Atomic unit of work, finance policies, SoD, thresholds |
| Billing | MISSING | P3/product gate | Placeholders only | PM billing preparation; external official invoice |
| Revenue/profitability | MISSING | P3/product gate | Existing report infrastructure | Contract/revenue projections and margin read models |
| Currency | INCONSISTENT | P0 | Organization base currency | Money/Currency/Rounding, Numeric storage, FX snapshots |
| Financial periods | MISSING | P1 | Operational calendar only as reference pattern | Organization fiscal periods and posting locks |
| Reporting | PARTIAL | P1 | Existing EVM/export/read-model structure | Canonical posted/versioned sources and reconciliation |
| Audit | INCONSISTENT | P0/P1 | Enterprise Audit plus Activity | Transactional immutable financial audit |
| Accounting integration | MISSING | P4 until scope chosen | Party/Department external refs | Typed contracts, export/reconciliation/idempotency only |

Priority meaning:

- **P0:** security, transaction, or financial-correctness prerequisite; do before expanding UI capability.
- **P1:** core SaaS Project Finance capability required for reliable budgets, costs, and forecasts.
- **P2:** professional control/structure that follows the core ledger.
- **P3:** product-scope feature that can be deferred without corrupting core cost management.
- **P4:** external enterprise integration; defer until a target system and contract are selected.

## 18. Recommended Target Adaptation

### Reuse as the foundation

- Existing PM module layering, composition registries, repository contracts, tenant context, Pydantic domain pattern, and optimistic concurrency conventions.
- Platform Organization for base-currency ownership.
- Platform Time as authoritative owner of approved hours.
- Inventory Procurement as authoritative owner of requisitions, POs, and receipts.
- Platform Party as supplier/customer identity owner.
- Platform Approval after making apply/decision transaction handling atomic.
- Platform Enterprise Audit for immutable audit storage; Activity remains user-facing history.
- PM baseline lifecycle as a design pattern for version submit/approve/supersede, not as a budget replacement.
- Existing reporting/EVM/export infrastructure once its inputs are canonical.

### Upgrade in place

- `FinanceService` authorization, canonical calculation ownership, pagination, currency basis, and report metadata.
- Organization currency validation and service default resolution.
- Approval extension points/unit-of-work behavior.
- Time and Procurement application contracts for project-finance consumption.
- Existing repositories' cross-reference and tenant/org assertions.
- Desktop error propagation and QML capability-driven actions.

### Create inside Project Finance

- `ProjectFinancialProfile`, `ProjectCostCode`, `ProjectRateCard` and rate lines.
- `ProjectBudget`/`BudgetLine`, planned-cost versions/lines.
- Financial commitments/projections and commitment matching.
- Posted `ProjectCostEntry`, reversal, source identity, and posting policy.
- Versioned forecast/ETC lines and financial change orders.
- Billing preparation and profitability only after product scope approval.

### Deprecate and remove after cutover

- Combined `CostItem` write API and editor.
- Mutable `actual_amount`, `committed_amount`, and `forecast_amount` as authoritative sources.
- Physical deletion of financial history.
- Hard-coded module-level `EUR` defaults.
- Float-based monetary columns after verified Numeric backfill.
- Desktop forecast/commitment fallback formulas after canonical service composition.
- Duplicate PM money formatters after shared formatting/serialization policy exists.
- `report.view` as finance authorization.
- Admin-session governance bypass.
- Client-side fixed-limit Procurement lookup.
- Transition adapters, dual-write code, and legacy projections once parity gates pass. No migration scaffolding or compatibility branch is allowed to remain as dead code.

### Explicitly defer

- A full accounting/general-ledger system.
- Payment processing and employee reimbursement.
- Tax calculation/filing.
- An exchange-rate provider before multi-currency source and operational requirements are selected.
- Official invoice issuance before Billing/Accounting ownership is decided.
- Expense claims before a product/module owner is selected.

### Cost-code ownership gate

The current recommendation remains PM-owned `ProjectCostCode` because the only proven semantic requirement is classification and rollup of project costs. Procurement may carry a stable reference supplied by Project Finance but must not own or mutate that code. Before Phase B schema is accepted, ADR-PF-009 must confirm whether the organization wants one taxonomy shared across PM, Procurement, Inventory, and accounting integration. If that real requirement is confirmed, the shared aggregate should be an organization-owned `OrganizationCostCode`, while PM owns project restrictions and mappings. The code must not be generalized merely for hypothetical reuse.

## 19. Incremental Implementation Plan

### Phase A - Safety and canonical foundations

Phase A is deliberately split into three independently reviewable increments. A0 must complete before any new financial write model; A1 must complete before new monetary persistence; A2 must complete before source-driven postings or forecast UI expansion.

#### Phase A0 - Security and transaction correctness

Ownership: **PLATFORM SECURITY + PLATFORM WORKFLOW + PROJECT FINANCE**

Status: **CODE COMPLETE; HOSTED POSTGRESQL DEPLOYMENT VALIDATION PENDING**

1. Introduce finance-specific query/mutation/sensitive permissions and switch `FinanceService` away from `report.view`.
2. Remove the admin-session financial governance bypass. If emergency override remains a product requirement, use only a narrowly scoped permission, mandatory reason, and Enterprise Audit.
3. Refactor Approval apply handling to participate in one outer unit of work. Financial mutation, approval decision, Enterprise Audit, and any outbox record commit or roll back together.
4. Integrate Enterprise Audit for financial mutations while retaining Activity as a non-authoritative UX feed.
5. Define direct tenant/org ownership, scoped foreign-reference validation, and PostgreSQL RLS policy templates for every new finance table.
6. Accept ADR-PF-008 before changing the shared Approval callback contract.

Exit gate: finance reads require finance permission; sensitive fields redact correctly; failure injection proves approval application is atomic; admin session alone grants no finance override; direct-scope/RLS architecture tests pass.

QML impact: capability properties, sensitive-field hiding, and typed error handling only.

Implementation progress (2026-08-02):

- Implemented canonical `finance.read` and `finance.read_sensitive` policy enforcement for finance and forecast queries; unauthorized detailed labor identity is aggregated/redacted.
- Removed the admin-session bypass from governed CostService mutations. Admin identity alone can no longer apply governed financial changes directly.
- Accepted and implemented the initial ADR-PF-008 transaction cutover: ApprovalService plus all registered PM/Procurement handlers stage mutation, decision, Activity, and mandatory Enterprise Audit in one outer transaction. Success signals are emitted only after commit.
- Added failure-injection tests proving rollback when either approval persistence or required audit fails.
- Added Enterprise Audit old/new-state records for cost create/update/delete and hardened CostItem task references to require the same project.
- Added a permanent tenant-plus-organization PostgreSQL RLS migration helper and an architecture guard requiring every future `project_finance_*` table to own non-null tenant/org columns and declare `info['rls_scope']='tenant_organization'`.
- Verification: the final focused A0 approval/event/security/RLS set has 32 passing tests; the finance/forecast/reporting batch has 30 passes; and 116 Inventory tests pass. The wider PM/platform run has 465 passes and 15 independently identified unrelated legacy/date-relative failures.
- All A0 code gates are met. A hosted PostgreSQL run under a non-owner, non-superuser, non-`BYPASSRLS` application role remains a deployment-environment gate; it is not replaced by SQLite architecture tests.

#### Phase A1 - Monetary foundations

Ownership: **PLATFORM FOUNDATION + PLATFORM ORGANIZATION + PROJECT FINANCE/PROCUREMENT/TIME ADOPTION**

1. Add dependency-free `CurrencyCode`, signed `Money`, `RoundingPolicy`, `DecimalQuantity`, and `MonetaryRate` primitives.
2. Reject cross-currency Money arithmetic and unit-mismatched rate/quantity operations. Business aggregates enforce non-negative or positive values where required.
3. Define Numeric persistence conventions separately for Money, rates, quantities, percentages, and exchange-rate precision.
4. Upgrade Organization currency validation and replace hard-coded `EUR` resolution with explicit transaction -> Project/Profile -> Organization rules. Ambiguous legacy rows are quarantined.
5. Define one Pydantic/JSON/desktop serialization contract. Consolidate formatting only after domain serialization is stable.
6. Approve ADR-PF-001 and ADR-PF-004 before implementation; the selected reversal model is signed postings with explicit entry kind and reversal link.

Exit gate: primitive/domain/property tests pass; no new finance amount/rate/quantity uses float; round-trip serialization is exact; organization currency resolution is deterministic; platform primitives import no business module.

QML impact: adapters convert canonical decimal strings for display/input; QML never performs financial arithmetic.

Implementation progress (2026-08-02):

- Added dependency-light platform `CurrencyCode`, signed `Money`, `RoundingPolicy`, `DecimalQuantity`, and `MonetaryRate` primitives with cross-currency and unit-mismatch rejection, deterministic allocation, and named half-even rounding boundaries.
- Vendored the official SIX ISO 4217 List One published 2026-01-01, including active-code and minor-unit metadata; Organization, Site, Project, ProjectResource, Resource, and CostItem Pydantic write models now reject invalid or unsuitable transaction currencies.
- Added strict immutable Pydantic payloads for Money, quantities, and rates. JSON/desktop values use canonical decimal strings, reject binary floats, forbid unknown fields, and round-trip exactly.
- Added reviewed Numeric precision conventions and SQLAlchemy `Numeric(..., asdecimal=True)` factories. Architecture tests require every future `project_finance_*` Numeric column to declare and match its financial precision kind.
- Removed all PM command-layer `EUR` constants. Project/Resource resolve explicit -> active Organization; Cost/ProjectResource resolve explicit -> Project -> active Organization. The explicit installation bootstrap currency remains an Organization policy default, not a transaction fallback.
- Deleted four duplicate PM desktop formatter implementations and routed financial/resource/project/portfolio labels through one Decimal-aware boundary that respects ISO currency minor units.
- Temporary conversion is limited to `TRANSITION(PF-A1-LEGACY-FLOAT)` and `TRANSITION(PF-A1-DESKTOP-FLOAT)`, both registered below for Phase D deletion. No unmarked A1 transition code was introduced.
- Verification: 40 focused domain/service/platform tests pass; the final primitives/formatting/architecture set has 26 passes; PM has 327 passes with 3 unrelated existing date/entitlement-order failures; Platform has 701 passes with 3 unrelated existing Site datetime/QML-route failures.
- All A1 code gates are met. Existing float columns and float legacy read DTOs remain governed migration inputs until their additive Numeric backfill and Phase D cutover; no new finance amount, rate, or quantity field uses float.

#### Phase A2 - Canonical application foundations

Ownership: **PLATFORM INTEGRATION + PROJECT FINANCE**

1. Define canonical source references and scoped idempotency keys for Time, Procurement, imports, and manual entries.
2. Make and record the outbox/inbox architecture decision. No reusable implementation was found in the current repository; collaboration "inbox" naming is unrelated.
3. Compose one canonical forecast/calculation service through `project_registry.py` and the desktop runtime.
4. Add parity tests between the canonical service and existing desktop fallback formulas, then remove the fallback at the phase gate.
5. Define source-specific actual-cost orchestration contracts while preserving one canonical posted ProjectCostEntry model.
6. Accept ADR-PF-002, ADR-PF-006, and ADR-PF-007 before their dependent contracts/consumers are implemented.

Exit gate: service composition is the production path; fallback formula deletion is verified; source retries have deterministic identity; outbox/inbox ownership is accepted; application contracts expose no QML-specific types.

QML impact: forecast/commitment presenters consume only canonical application DTOs; no fallback calculations remain.

Implementation progress (2026-08-02):

- Added immutable PM-owned financial source contracts with tenant/organization/project scope, source document/line/revision, canonical content hash, and deterministic semantic idempotency keys for approved Time, Procurement PO commitments, Procurement receipt accruals, manual entries, and imports.
- Added approved-Time and Procurement source snapshots plus cursor-paginated provider protocols. Contracts use canonical Decimal quantity/rate payloads and import no Time, Procurement, desktop, or QML types.
- Accepted ADR-PF-002, ADR-PF-006, and ADR-PF-007. The approved trigger rules are TimesheetPeriod APPROVED, PO SENT, and receipt POSTED; LOCKED does not duplicate labor posting and a future invoice must reclassify the receipt accrual.
- Accepted ADR-PF-011: source-owned transactional outbox, consumer-owned durable inbox, at-least-once delivery, separate transport and financial semantic deduplication, conflict quarantine, per-aggregate ordering, and retry/dead-letter operations. The permanent transport-neutral integration envelope is implemented; durable stores/consumers remain Phase C.
- Composed one `ForecastCostService` in `project_registry.py`, exposed it through `ServiceGraph`, resolved it in the desktop runtime, and injected it into the financial desktop API.
- Deleted all desktop forecast/commitment fallback calculations and empty compatibility builders. Desktop code now maps only canonical application results; missing production composition fails explicitly rather than calculating a divergent result.
- Verification at the A2 phase gate: 31 focused source-contract, event-envelope, architecture, desktop-delegation, QML financial-workspace, financial desktop API, and canonical forecast-service tests pass. PM has 335 passes with only 3 unrelated existing date-relative dashboard/entitlement-order failures. Architecture has 112 passes with 2 unrelated existing size-budget breaches deselected. The full Platform run reached 61% with no failures before the 240-second command limit; the affected focused Platform contract tests pass.
- No temporary A2 code or files were introduced. Phase C persistence/consumer work is deferred explicitly rather than represented by an in-memory outbox, direct repository adapter, or compatibility shim.

### Phase B - Configuration, budget, rates, and planned cost

Ownership: **PROJECT FINANCE**, with one Scheduling product decision

ADR gate: complete. ADR-PF-003, ADR-PF-005, and ADR-PF-009 are accepted.

1. Complete: add ProjectFinancialProfile and backfill project currency without deleting legacy fields. Planned-budget conversion is intentionally reserved for the versioned Budget aggregate rather than copied into another mutable profile field.
2. Complete: add ProjectCostCode catalog and project restrictions. Legacy `CostType` remains only on legacy cost records until explicit reviewed mapping/reconciliation.
3. Complete: Task-owned WBS (`parent_task_id`/`wbs_code`, cycle prevention, migration backfill).
4. Complete: versioned effective-dated rate cards (ADR-PF-005) for internal cost and billing rates, with deterministic priority/fallback and immutable snapshot selection — **and** `CostPolicyEngine`/`LaborCostEngine` are cut over onto them (2026-08-05; design doc `rate_card_cost_engine_cutover_plan.md` deleted, fully implemented/tested — see git history). `Resource.hourly_rate`/`ProjectResource.hourly_rate` now only reach cost calculations through an auto-seeded `legacy_seeded` rate-card line, never by direct field read.
5. Complete: versioned Budget/BudgetLine lifecycle and governed approval integration. Approved versions are immutable and supersede rather than update.
6. Complete: versioned planned-cost calculation/snapshots (2026-08-06) from
   `TaskAssignment.allocated_planned_hours`, dimensioned by cost code + WBS/task in parity
   with `BudgetLine`, with retained source lineage (`source_assignment_id`, immutable, not a
   live FK). Manual/material planned-cost inputs and baseline-comparison sourcing are
   explicitly deferred, as is a full `ProjectLaborPlan`/`LaborPlanAllocation` lifecycle
   aggregate (a design review's recommendation for the eventual, non-tactical version of this
   capability).
7. Partial (2026-08-06): `BaselineService.create_baseline`'s planned-labor
   snapshot now resolves `RateType.COST` through the rate-card resolver
   (batched, fail-closed on unresolved/currency-mismatched rates) instead
   of reading `Resource.hourly_rate`/`ProjectResource.hourly_rate`
   directly — a rate-source-consistency fix only. The quantity/allocation
   model (`ProjectResource.planned_hours`, duration-weighted task
   allocation) and `BaselineTask.baseline_planned_cost`'s `float` type are
   both deliberately unchanged. `create_baseline` now requires an explicit
   `rate_as_of: date` argument (never `date.today()` inside the service).
   **Still remaining under item 7:** the "planning reports" half —
   `CostPolicyEngine`/`LaborCostEngine`'s own "planned" figures (feeding
   KPIs/dashboards/`FinanceSnapshot.planned`) still read
   `ProjectResource.planned_hours` directly rather than the new
   `ProjectPlannedCostVersion`. Baseline provenance (which exact rate-card
   line/version valued each task) is also not recorded — a later baseline
   financial-snapshot extension would be needed for that.

   **Investigated and explicitly rejected (2026-08-06): cutting
   `CostPolicyEngine`/`ledger.py`/`LaborCostEngine` over onto
   `ProjectPlannedCostVersion`.** This is not a safe data-source swap and
   would be a regression if done as literally scoped:
   - **Granularity mismatch.** The three existing call sites
     (`CostPolicyEngine._resolve_planned_labor_map`, `ledger.py`'s
     `build_computed_labor_plan_rows`, `LaborCostEngine
     .calculate_project_labor_plan_vs_actual`) all sum a resource's full
     `ProjectResource.planned_hours` *envelope*, with no dependency on any
     task assignment existing. `ProjectPlannedCostVersion` only counts
     hours actually *allocated* to a task
     (`TaskAssignment.allocated_planned_hours`) — partial/zero allocation
     is an explicitly normal state. Cutting over would silently drop
     unallocated planned hours from every KPI/dashboard reading them (a
     real, confirmed test regression: `test_technical_math_reporting_
     cost_policy.py::test_cost_policy_consistent_across_kpi_evm_
     breakdown_and_totals` has 10 planned hours with 0 allocated to any
     task; `total_planned_cost` would drop from 1150.0 to 150.0).
   - **Three call sites, not one, and they'd disagree.** `ledger.py`'s own
     docstring states its planned-labor rows intentionally share
     `CostPolicyEngine`'s exact source "so this ledger's rows never
     disagree with the engine's totals in the same finance snapshot."
     Cutting over only one of the three would break that invariant within
     a single `FinanceSnapshot`.
   - **No freshness mechanism exists.** `ProjectPlannedCostVersion` only
     updates via an explicit `calculate_snapshot()` call; nothing in
     production ever calls it today (only tests do), `planned_costs_changed`
     has zero subscribers, and no assignment-mutating command triggers a
     recalculation. `CostPolicyEngine`/KPIs are live, always-current read
     paths — reading this snapshot instead would show `$0` planned for
     every project until someone manually triggers a calculation.

   Decision: leave `CostPolicyEngine`/`ledger.py`/`LaborCostEngine` as they
   are — they already resolve through the rate-card resolver correctly at
   their own (coarser, envelope-level) granularity, which is not wrong,
   just a different, legitimate view than the new snapshot's
   allocated-to-task view. The real gap is that nothing yet surfaces
   `ProjectPlannedCostVersion` to users (no desktop endpoint/report exists
   for it) — a future additive report, not a replacement of existing
   figures, would be the correct way to make it visible. A genuine full
   cutover would require, at minimum, an assignment-change-triggered
   recalculation mechanism and a product decision on whether unallocated
   envelope hours should still count as "planned" — out of scope for this
   phase.
8. Replace the QML combined "Budget" cost-line section with separate Profile, Budget Versions, Budget Lines, Rate Cards, and Planned Costs views. Current QML may be broken/replaced as contracts move; do not preserve false semantics.

Exit gate: approved budgets cannot mutate; rate selection is deterministic; historical snapshots remain stable after rate changes; plan totals reconcile by cost code/WBS/period; cross-tenant references fail.

Implementation progress (Phase B1, 2026-08-02):

- Accepted ADR-PF-003 (Task-owned WBS), ADR-PF-005 (rate-card precedence), and ADR-PF-009 (PM-owned cost-code catalog) after revalidating the complete Scheduling, Finance, Inventory, and Procurement ownership evidence.
- Added Pydantic-validated `ProjectFinancialProfile`, `ProjectCostCode`, and `ProjectCostCodeRestriction` domain models. Profile transitions and billing invariants, cost-code syntax/effective dates/external mappings, hierarchy cycles, active ancestors/children, and default restrictions are explicit.
- Added canonical repository contracts, mappers, fail-closed scoped SQLAlchemy repositories, optimistic updates, and service composition through `RepositoryBundle`, `ProjectManagementServiceBundle`, and `ServiceGraph`.
- Added `project_finance_profiles`, `project_finance_cost_codes`, and `project_finance_cost_code_restrictions` in revision `j8k9l0m1n2o3`. Every table has non-null tenant/organization scope, scoped uniqueness/foreign keys, check constraints, RLS metadata, and forced PostgreSQL tenant/organization policy setup.
- New Project creation flushes and inserts its financial profile before the same commit. Existing profiles backfill deterministically from a supported Project currency then a supported Organization base currency; migration fails with a repair message if neither is valid. No write-on-read repair path exists.
- Added global plus project-scoped `finance.read`/`finance.manage` enforcement, owner-only project financial configuration, mandatory optimistic versions, and fail-closed Enterprise Audit in the mutation transaction.
- Verification: 23 focused B1 domain, service, repository, RBAC, architecture, transition-register, migration upgrade/backfill/downgrade, and audit rollback tests pass. The pre-existing Phase A0 finance/RBAC integration set also passes (14 tests in the combined check). The broader PM suite passes 345 tests with only the three known unrelated dashboard date-relative/entitlement-order cases deselected; Architecture passes 113 tests with only its two pre-existing size-budget breaches.
- No temporary B1 files or in-memory adapters were added. The only B1 transition code is the two-way legacy `Project.currency` projection, marked `PROJECT-FINANCE-TRANSITION-ONLY(PF-B1-CURRENCY-DUAL-WRITE)` at both write paths and registered below for deletion.

### Phase C - Actual ledger, commitments, time, procurement, and periods

Ownership: **PROJECT FINANCE + PLATFORM TIME + INVENTORY PROCUREMENT + PLATFORM FOUNDATION + INTEGRATION**

ADR gate: ADR-PF-004, ADR-PF-006, ADR-PF-007, and ADR-PF-008 must be accepted before ledger/source integration cutover.

1. Add organization financial periods and closure/lock policy. Keep them separate from operational scheduling calendars.
2. Add ProjectCostEntry draft/approval/post/reversal lifecycle with direct scope, Money/base-Money/FX snapshot, source, period, dimensions, actor/timestamps, and scoped idempotency constraints.
3. Add PM commitment projections/lines, matching, cancellation/closure, and remaining-balance policy.
4. Add an approved-Time contract/event and idempotent labor-cost consumer. Snapshot rate and reverse/replace corrected approvals.
5. Add typed Procurement project-source queries/events for PO lines, changes, cancellation, receipts, and supplier invoice references when available. PM creates projections/postings; Procurement remains owner.
6. Replace manual combined CostItem writes with distinct planned, commitment, and manual-actual commands. Posted actuals are never editable/deletable.
7. Backfill/split legacy CostItem rows, dual-read for reports, reconcile totals, and quarantine unresolved currency/source cases.
8. Redesign QML Actuals and Commitments as ledgers with status, source, period, matching, approval, posting, and reversal actions. Remove the generic edit/delete behavior from posted rows.

Exit gate: only approved time generates actuals; one source/version cannot duplicate; rate/FX changes do not change history; commitment matching avoids double count; closed periods reject normal posting; RLS and tenant tests pass; legacy and new totals reconcile.

Prep work only (2026-08-06): the `TRANSITION(PF-A0-UOW-BRIDGE)` cleanup this
phase's items 2/6 depend on (dedicated approved commands owning their own
Unit of Work) is done — see the transition-code register above. None of
Phase C's 8 items themselves have started.

### Phase D - Forecasts, ETC, change control, and enterprise reporting

Ownership: **PROJECT FINANCE**

1. Add forecast versions/lines and explicit automatic/manual source metadata.
2. Define ETC source precedence and exclusion/matching rules across remaining plan, commitments, risks, and manual estimates.
3. Add typed financial change requests that apply approved budget, forecast, contract, and schedule impacts atomically by creating new versions.
4. Rebuild snapshot, cash flow, EVM, variance, and portfolio financial read models from canonical Money, posted actuals, open commitments, and approved/current forecast versions.
5. Add as-of/basis/period metadata, pagination, source drill-down, reconciliation/control totals, and sensitive-field filtering to exports.
6. Remove desktop forecast fallback formulas and legacy CostItem reporting once parity is proven.
7. Redesign QML Forecast, ETC, Change, Variance, and reporting tabs around version selection and drill-down; keep fixed contextual tools and section headers consistent with existing PM workspace standards.

Exit gate: forecasts are reproducible and historical; no commitment/ETC double count; approved changes create traceable versions; all report totals reconcile to ledger sources; legacy read code is removed.

### Phase E - Billing preparation, revenue, and external accounting

Ownership: **PROJECT FINANCE + FUTURE BILLING/ACCOUNTING OWNER + INTEGRATION**

ADR gate: ADR-PF-010 must be accepted before billing or external-accounting implementation.

1. Resolve the product decisions in Section 24 before implementation.
2. Add PM billing profiles/schedules and billing-preparation aggregates for the approved methods only.
3. Select eligible billable time/expenses/milestones with idempotent source locks to prevent duplicate billing.
4. Export approved billing preparations or posted costs through typed accounting contracts and store acknowledgement/reconciliation references.
5. Add project contract-value, revenue projection, and profitability read models. Keep statutory revenue recognition, invoices, tax, payment, and GL posting external unless scope explicitly changes.
6. Replace QML invoice EmptyState with billing-preparation and integration-status views only after backend ownership is real.
7. Remove all remaining transition DTOs, dual writes, legacy columns/readers, aliases, and dead feature flags after migration verification.

Exit gate: duplicate billing/export is impossible under retry; external acknowledgements reconcile; margins honor sensitive permission; no PM code claims ownership of official accounting records; transition code inventory is empty.

## 20. Database and Migration Plan

The audit itself created no migration. Implementation revision `j8k9l0m1n2o3` now delivers the independently reversible Phase B1 configuration schema and deterministic profile-currency backfill. Later persistence groups remain additive and independently gated.

### Proposed persistence groups

| Group | Candidate tables | Essential constraints |
| --- | --- | --- |
| Profile/config | `project_finance_profiles`, `project_finance_cost_codes`, `project_finance_cost_code_restrictions` | IMPLEMENTED in B1: direct tenant/org/project scope; one profile per project; scoped unique code; scoped parent/project/default references; forced RLS |
| Rates | `project_rate_cards`, `project_rate_card_lines` | version/effective interval; rate type; Money currency; no invalid overlap for same selection key |
| Budgets/plans | `project_budgets`, `project_budget_lines`, `project_planned_cost_versions`, `project_planned_cost_lines` | immutable approved/superseded versions; dimension scope; version uniqueness |
| Commitments | `project_commitments`, `project_commitment_lines`, `project_commitment_matches` | unique source type/system/id/line; matched amount cannot exceed committed amount |
| Actual ledger | `project_cost_entries` | direct tenant/org; posting/reversal state; source uniqueness; reversal target same scope/currency; immutable posted rows |
| Periods | organization fiscal calendar/period tables | non-overlapping dates per calendar; controlled status transitions |
| Forecast/change | `project_forecasts`, `project_forecast_lines`, `project_financial_changes`, impact/apply references | immutable approved versions; one application result per approved change |
| Billing/integration | billing preparation/line and accounting export/inbox records | source-selection uniqueness; idempotency; acknowledgement/reconciliation state |

All monetary columns should use a documented `Numeric` precision/scale suitable for storage, with domain rounding to currency minor units at defined boundaries. Rates and quantities may require a wider scale than posted Money. Currency must be non-null on every monetary value. Converted values store original Money, base Money, FX rate, source, and effective timestamp; never recompute history from a mutable rate table.

### Field-by-field legacy CostItem migration map

One legacy `CostItem` can create multiple target records. Every generated row carries source system `legacy_pm`, source type `cost_item`, source ID equal to the legacy ID, and the generated-record purpose in its idempotency key.

| Legacy field | Target | Deterministic rule |
| --- | --- | --- |
| `id` | Source reference on every generated record | Preserve exactly; never reuse as the new aggregate identity for multiple target responsibilities |
| `project_id` | Scope and Project reference on all targets | Resolve Project, tenant, and organization; quarantine if missing/inactive/inconsistent |
| `task_id` | Optional financial dimension | Validate Task belongs to the same Project/tenant/org; quarantine invalid cross-project references |
| `description` | Line/entry description snapshot | Preserve normalized text on every generated responsibility |
| `code` / ORM `cost_code` | Legacy line reference and optional reviewed CostCode mapping | Do not treat it as a new ProjectCostCode identity; map only through an explicit mapping table |
| `cost_type` | Initial classification mapping | Translate through a versioned, reviewed legacy-type-to-cost-code/category map; preserve original value in migration metadata |
| `planned_amount` | `ProjectPlannedCostLine` | Create when non-zero; represent zero only when required to preserve an explicit source line |
| `committed_amount` | `ProjectCommitment`/line | Create a legacy manual commitment when greater than zero; preserve legacy commitment status separately |
| `actual_amount` | `ProjectCostEntry` | Create when greater than zero. Migration configuration must choose legacy manual POSTED versus review-required DRAFT for the environment; never infer per row from amount alone |
| `forecast_amount` | Initial `ProjectForecastLine` | Create when non-null; zero remains an explicit forecast override rather than "missing" |
| `commitment_status` | Commitment migration state/snapshot | Map only valid operational equivalents. `INVOICED` and `PAID` do not prove an actual invoice/payment record; preserve and flag for reconciliation |
| `vendor_reference` | External-document text snapshot; optional supplier Party link | Resolve a Party only through a verified mapping; otherwise retain text without inventing a supplier identity |
| `incurred_date` | Actual transaction date and source-date snapshot | Use for actual transaction date when an actual is generated; retain on other generated records as legacy source metadata; apply an explicit missing-date policy |
| `currency_code` | CurrencyCode on every generated Money value | Resolve in order: explicit valid item currency -> valid Project currency -> Organization base currency; quarantine when unresolved |
| `version` | Migration metadata only | Preserve for traceability; each target aggregate begins with its own version/lifecycle rules |
| Derived tenant/org | Direct target ownership | Backfill from the validated Project, not from ambient/default session context |

Migration reconciliation reports must show one-to-many generated IDs, source/target amounts by project and currency, rounding deltas, quarantined rows, and every explicit mapping decision.

### Migration sequence

1. Add new tables/columns, constraints initially permissive where backfill requires it, indexes, direct tenant/org ownership, and RLS policies.
2. Add deterministic backfill tooling with dry-run counts, per-row outcome, audit correlation, and restart-safe checkpoints.
3. Resolve currency in order: explicit legacy item -> Project currency -> Organization base currency. Quarantine rows that remain ambiguous; never silently inject `EUR`.
4. Split each legacy CostItem by nonzero responsibility: planned line, manual commitment projection, manual actual draft/posted-as-decided, and initial forecast input. Preserve a legacy source reference so reconciliation is reproducible.
5. Convert float through decimal string representation under a documented rounding policy; report pre/post totals and rounding deltas by project/currency.
6. Add dual-read comparison, not indefinite dual ownership. If dual-write is temporarily required, one service owns both writes in one unit of work and records parity failures.
7. Backfill direct tenant/org from Project and validate every Task belongs to the same Project; quarantine invalid cross-project relations.
8. Build new reports behind an internal feature flag and compare project/currency/period totals, record counts, and source lineage with legacy outputs.
9. Switch application writes to new commands, then reads/reporting, then QML. Disable legacy mutations before removing compatibility readers.
10. Make non-null/check/unique/RLS constraints strict after backfill validation.
11. Remove legacy APIs, fallback formulas, dual-write paths, and transitional flags after a named parity release gate.
12. Drop legacy amount columns/table only in a later migration after backups, rollback window, audit retention, and test evidence are accepted.

**ASSUMPTION - MUST BE CONFIRMED BEFORE MIGRATION EXECUTION:** the application currently has no production clients. Even if confirmed, development, demonstration, staging, and test data may require preservation and reconciliation. A shorter deployment window may be approved, but deterministic conversion, quarantine, audit, and reconciliation requirements do not change.

### Rollback strategy

- Before write cutover, rollback by disabling the new read feature flag and leaving additive data intact.
- During dual write, rollback only if the compatibility path can replay from source/idempotency records; do not reverse posted entries by deleting them.
- After new-only writes, rollback means a forward repair/replay or explicit financial reversal, not restoring mutable legacy writes.
- Every migration script must publish counts, rejected rows, rounding deltas, and a verification query set.

### Transition-code deletion register

This register is mandatory implementation scope. A phase cannot close while its due transition components remain open without a newly approved ADR and removal gate.

| Transitional component | Origin/added in | Removal gate | Owner | Status |
| --- | --- | --- | --- | --- |
| Desktop forecast/commitment fallback builders | Pre-existing | A2 canonical service composition and parity tests pass | PM Finance | CLOSED; formulas and empty compatibility paths deleted 2026-08-02 |
| `report.view` finance authorization | Pre-existing | A0 finance permission grants and policy tests pass | Platform Security / PM Finance | CLOSED; replaced by `finance.read` on 2026-08-02 |
| Admin-session cost-governance bypass | Pre-existing | A0 removal tests pass | Platform Security | CLOSED; removed 2026-08-02 |
| `cost.manage` umbrella/alias | Pre-existing; transitional mapping in A0 | Target command permissions active across desktop/services | Platform Security / PM Finance | OPEN |
| Hard-coded PM `EUR` defaults | Pre-existing | A1 Organization/Profile currency resolution cutover | Platform Foundation / PM | CLOSED; command constants removed and Organization resolution active 2026-08-02 |
| Duplicate PM money formatters | Pre-existing | A1 canonical serialization/formatting adopted | Desktop UI / PM | CLOSED; four implementations replaced by one Decimal-aware boundary 2026-08-02 |
| Legacy combined CostItem write API | Pre-existing | C distinct planned/commitment/manual-actual commands and QML cutover | PM Finance / Desktop UI | OPEN |
| Legacy CostItem reader/projection | Pre-existing; retained in B/C | D ledger/report reconciliation complete | PM Finance | OPEN |
| `Project.planned_budget` compatibility projection | Pre-existing; retained in B | B budget read cutover and reconciliation complete | PM Finance | OPEN |
| `Project.currency` compatibility projection | Pre-existing; retained in B | Profile currency cutover and all consumers migrated | PM Finance | OPEN |
| Profile-to-Project and Project-to-profile currency synchronization | B1; `PF-B1-CURRENCY-DUAL-WRITE` | Desktop APIs, presenters, reports, imports, and Project DTOs read profile currency exclusively; parity test passes; then delete both marked branches and legacy field writer | PM Finance / Desktop UI | OPEN; both branches marked and covered by B1 tests |
| Float monetary/rate/quantity persistence | Pre-existing | Relevant Numeric backfill, read cutover, and reconciliation complete | Platform/Data/Module owners | OPEN |
| Planned dual-read comparison | C | D canonical report reconciliation complete | PM Finance | NOT CREATED |
| Planned dual-write adapter, only if required | C | New writes and reports reconcile; legacy writes disabled | PM Finance | NOT CREATED |
| Client-side fixed-limit Procurement lookup | Pre-existing | C typed project-source contract active | Procurement / PM Integration | OPEN |
| Legacy financial permission aliases/feature flags | A0 onward | E final role/API/controller inventory passes | Platform Security / PM Finance | NOT CREATED |
| Approval `commit=False` transaction switches in legacy cost/baseline/dependency/scheduling services | A0 | C dedicated approved commands own the shared Unit of Work | Platform Workflow / PM | CLOSED 2026-08-06; `CostLifecycleMixin`/`BaselineService`/`TaskDependencyMixin` each split into a public governed method + a private `_apply_*_decision` (mirroring `BudgetService`); `SchedulingEngine`/`_sync_project_schedule`'s `commit` params re-scoped as plain caller-owned batching, not an approval bridge — no regressions (24 pre-existing failures unchanged, 428 passed) |
| Approved-handler `bypass_approval=True` switches | Pre-existing; constrained in A0 handlers | C handlers call dedicated internal approved commands with no public bypass flag | Platform Workflow / PM | CLOSED 2026-08-06; `bypass_approval` parameter removed entirely from `add_cost_item`/`update_cost_item`/`delete_cost_item`/`create_baseline`/`add_dependency`/`remove_dependency` — no caller anywhere (checked) passed `bypass_approval=True` except the composition apply handlers, now rewired to call `_apply_*_decision` directly. `TaskDependencyMixin.update_dependency`'s governed branch was dead code (not in `DEFAULT_GOVERNED_ACTIONS`, no apply handler ever registered) — deleted rather than wired up. |
| Unused FinanceService ReportingService compatibility argument | A0 candidate | Remove before A0 merge | PM Finance | CLOSED; deleted 2026-08-02 |
| `Money.from_legacy_float` and `decimal_from_legacy_float` converters | A1 | D legacy CostItem reconciliation, float DTO, and float-column retirement complete | Platform Finance / Data Migration | OPEN; marked `TRANSITION(PF-A1-LEGACY-FLOAT)` |
| PM desktop formatter legacy-float branch | A1 | D canonical decimal-string read DTO cutover complete | Desktop UI / PM Finance | OPEN; marked `TRANSITION(PF-A1-DESKTOP-FLOAT)` |

## 21. Permission Migration Plan

Use the repository's canonical permission catalog and policy evaluation; do not check role names.

| Current permission/path | Transitional mapping | Target permissions |
| --- | --- | --- |
| `report.view` for FinanceService | Grant finance read to intended existing PM roles before code switch | `finance.read`; `finance.read_sensitive` |
| `report.export` / `finance.export` | Retain alias only during rollout | `project_finance.export` |
| `cost.read` | Map to non-sensitive finance read | `cost.read` or canonical `finance.read` by query responsibility |
| `cost.manage` | Temporary umbrella with telemetry | `project_cost.create`, `.update_draft`, `.submit`, `.post`, `.reverse` |
| `finance.manage` | Temporary administrative umbrella, no automatic approval | profile/cost-code/rate/budget/forecast/change-specific manage permissions |
| `approval.decide` | Require request-type policy as well | `project_budget.approve`, `project_cost.approve`, `project_forecast.approve`, `project_change.approve` |
| Admin session bypass | No compatibility mapping | Explicit `project_finance.emergency_override`, reason required, Enterprise Audit mandatory |

Migration steps:

1. Add target permissions and role grants without removing existing grants.
2. Add policy tests and optional decision telemetry comparing old and new authorization.
3. Switch FinanceService and new commands to target permissions.
4. Ensure approval decision permissions do not confer create/post/reverse rights.
5. Enforce creator/approver separation according to configurable tenant/org policy; privileged override remains separate.
6. Redact rates, margins, and sensitive labor details unless `read_sensitive` is present, including exports and cached/read-model payloads.
7. Remove aliases/umbrellas after every controller/API/report path and seeded role has migrated.

## 22. Test Plan

### Domain and calculation tests

- Money creation, serialization, equality, add/subtract/multiply/allocation, rounding, zero, large amounts, invalid precision, and currency mismatch.
- CurrencyCode ISO/minor-unit behavior and organization currency policy.
- Rate priority, effective boundaries, overlaps, overtime/weekend choice, project/customer override, and immutable snapshots.
- Budget and forecast state transitions, version/supersede invariants, line reconciliation, and immutable approved state.
- Planned-cost calculation and source/version lineage.
- Posting, reversal/netting, commitment matching/partial matching, ETC source exclusion, EAC and margin formulas.
- Financial period open/closed/locked behavior and controlled exception posting.

### Application and transaction tests

- Every command/query permission, including sensitive DTO redaction and export.
- Missing tenant/org context fails closed; all cross-reference scope combinations.
- Approval apply failure before/after mutation, audit, and outbox proves total rollback.
- Source retry, duplicated/out-of-order Time and Procurement events, and concurrent posting prove idempotency.
- Approved-time-only generation; correction creates reversal/replacement; current rate changes do not alter history.
- Governance thresholds, currency-normalized threshold input, self-approval, delegation/escalation when added, and explicit override audit.

### Repository/database/RLS tests

- Tenant A cannot read/write/reference Tenant B Project, Task, Resource, rate, cost code, budget, period, supplier, source document, approval, cost entry, commitment, or reversal.
- Same-tenant cross-organization IDs fail where organization is part of scope.
- Direct SQL under the application role observes RLS on every new financial table.
- Unique source/idempotency, version concurrency, effective-rate overlap, period date, matched-amount, reversal-scope, and immutable-posting constraints.
- Aggregate/read-model queries reconcile by project, currency, WBS, cost code, and period under pagination.

### Adapter, QML, reporting, and migration tests

- Desktop validation maps domain errors without broad swallowing; QML actions reflect capabilities and lifecycle state.
- No QML component calculates authoritative EAC/ETC/exposure or mutates posted records.
- List/detail/report/export totals use the same canonical query and display currency basis/as-of/period.
- Imports are dry-runnable, idempotent, tenant-scoped, and report row-level source outcomes.
- Legacy conversion fixtures cover multiple nonzero CostItem fields, missing currency, cross-project task, rounding edge cases, and restart after partial backfill.
- Golden reconciliation compares old/new totals with documented expected differences; transition code deletion has architecture/grep checks.

### Mandatory financial regressions

- One time entry or supplier source cannot create duplicate active actual cost.
- Matching an actual reduces open commitment without double-counting exposure.
- Historical rate/FX changes leave posted entries unchanged.
- Closed-period totals remain stable.
- Reversals net correctly and preserve both records.
- Budget/forecast histories remain queryable after supersede.
- Unauthorized users cannot infer rates/margins through totals, exports, error text, logs, or caches.

## 23. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Scope becomes a general accounting rewrite | Delayed PM value and ownership confusion | Enforce bounded-context decisions; official invoices/payments/GL remain external |
| Big-bang replacement of CostItem | Data loss and long unstable branch | Additive schema, split backfill, parity read, staged cutover |
| Platform finance becomes a dumping ground | Coupling and circular dependencies | Admit only dependency-free concepts with two real consumers; architecture tests |
| Float-to-Decimal changes totals | User distrust/reconciliation failure | Document conversion/rounding, calculate deltas, approve reconciliation |
| Legacy missing currency cannot be resolved | Misstated historical totals | Deterministic hierarchy plus quarantine; no silent EUR |
| Approval refactor affects other modules | Cross-platform regression | Add platform contract tests and migrate handlers one at a time under UoW |
| Time/Procurement events retry or arrive out of order | Duplicate or stale postings | Durable outbox/inbox, source version, idempotency, monotonic transition rules |
| Permission split locks out valid users | Operational disruption | Add grants first, compare decisions, then switch and remove aliases |
| Sensitive rates leak through read models/export | Confidentiality breach | Field policy at query/DTO layer; export and cache security tests |
| QML and backend contracts diverge | Broken desktop workflow | Backend contract first, presenter mapping tests, replace sections per phase |
| Compatibility code remains indefinitely | Duplicate logic and hidden defects | Maintain a transition-code deletion register with owner and phase exit gate |
| WBS/billing/expense product ambiguity | Rework | Resolve Section 24 decisions before the dependent phase |

## 24. Open Questions Requiring Product Decisions

### Architecture decision gate

The repository already uses global ADR-001 through ADR-004, so Project Finance decisions use the non-conflicting `ADR-PF-*` namespace. Every ADR contains Context, Decision, Alternatives rejected, Consequences, Migration impact, and Test impact. `PROPOSED` ADRs must become `ACCEPTED` before the named dependent implementation begins.

| ADR | Decision | Current status | Required before |
| --- | --- | --- | --- |
| [ADR-PF-001](../architecture_decisions/ADR-PF-001-money-currency-precision-rounding.md) | Money, currency, precision, quantities, rates, and rounding | ACCEPTED; PHASE A1 FOUNDATION IMPLEMENTED | A1 implementation |
| [ADR-PF-002](../architecture_decisions/ADR-PF-002-project-finance-bounded-context.md) | Project Finance bounded-context and module ownership | ACCEPTED; PHASE A2 BOUNDARY CONTRACTS IMPLEMENTED | A2/B contracts |
| [ADR-PF-003](../architecture_decisions/ADR-PF-003-wbs-and-hierarchical-tasks.md) | WBS versus hierarchical Tasks | ACCEPTED; TASK-OWNED WBS IMPLEMENTED | B WBS/planned-cost dimensions |
| [ADR-PF-004](../architecture_decisions/ADR-PF-004-financial-posting-and-reversal.md) | Posting and signed reversal model | ACCEPTED; LEDGER IMPLEMENTATION DEFERRED TO C | A1/C ledger schema |
| [ADR-PF-005](../architecture_decisions/ADR-PF-005-rate-card-precedence.md) | Rate-card precedence | ACCEPTED; IMPLEMENTED INCLUDING COST-ENGINE CUTOVER (2026-08-05) | B rate-card implementation |
| [ADR-PF-006](../architecture_decisions/ADR-PF-006-approved-time-posting-trigger.md) | Approved-time posting trigger | ACCEPTED; PHASE A2 SOURCE CONTRACT IMPLEMENTED | A2 contract/C consumer |
| [ADR-PF-007](../architecture_decisions/ADR-PF-007-procurement-financial-triggers.md) | Procurement commitment and actual triggers | ACCEPTED; PHASE A2 SOURCE CONTRACTS IMPLEMENTED | A2 contract/C consumer |
| [ADR-PF-008](../architecture_decisions/ADR-PF-008-approval-unit-of-work.md) | Approval and unit-of-work transaction model | ACCEPTED; INITIAL TRANSACTION CUTOVER IMPLEMENTED | A0 approval refactor |
| [ADR-PF-009](../architecture_decisions/ADR-PF-009-cost-code-ownership.md) | Cost-code ownership and hierarchy | ACCEPTED; PHASE B1 FOUNDATION IMPLEMENTED | B cost-code schema |
| [ADR-PF-010](../architecture_decisions/ADR-PF-010-billing-and-accounting-boundary.md) | Billing versus external accounting ownership | PROPOSED | E implementation |
| [ADR-PF-011](../architecture_decisions/ADR-PF-011-durable-integration-outbox-inbox.md) | Durable outbox/inbox ownership and delivery semantics | ACCEPTED; ENVELOPE CONTRACT IMPLEMENTED, STORES DEFERRED TO C | A2 decision/C consumers |

### Product questions

These are genuine product/ownership decisions. Questions mapped to A0/A1/A2 ADRs are blockers for those subphases; later questions do not block A0 security analysis:

1. Resolved by ADR-PF-003: hierarchical Tasks own WBS; a separate WorkPackage is deferred until a proven non-schedulable financial-node requirement exists.
2. Which budget dimensions are mandatory in the first release: cost code, WBS/task, department, period, funding source?
3. Are projects single transaction-currency, multi-currency with one reporting currency, or unrestricted multi-currency?
4. What monetary precision, rounding mode, and line-versus-total rounding rules are contractual?
5. Resolved by ADR-PF-005: cost and billing are separate; deterministic customer/project/resource/role-skill-department/organization precedence applies; overtime/holiday behavior is an explicit snapshotted modifier.
6. Resolved by ADR-PF-006: labor cost originates from an APPROVED period snapshot; LOCKED is an idempotent administrative control.
7. Resolved by ADR-PF-007: PO SENT creates commitment and receipt POSTED creates accrual actual; a later invoice reclassifies that accrual.
8. Are manual actual costs allowed, and who may post or reverse them?
9. Which approval thresholds and separation-of-duties rules vary by tenant, organization, department, project, amount, and currency?
10. Are expense claims in this product, a future Expenses module, or external-only?
11. Which billing methods are in the first PM scope, and does PM only prepare billing or issue official invoices?
12. Is revenue recognition required, or are contract/billable/invoiced projections sufficient?
13. Which external accounting/ERP system is the first target, and what identifiers, export format, acknowledgements, and reconciliation workflow does it require?
14. What period-close authority and late-adjustment policy applies?
15. What retention and export rules apply to financial audit, approval, source documents, and reversals?

## 25. Final Recommendation

Proceed with the upgrade, but do not extend the current combined CostItem/QML model. Phase A0 security/transaction correctness, A1 monetary foundations, A2 canonical application foundations, the Phase B1 configuration foundation, Task-owned WBS, effective-dated rate cards with the `CostPolicyEngine`/`LaborCostEngine` cutover, the versioned Budget/BudgetLine lifecycle, and tactical, assignment-labor-only versioned planned-cost snapshots are all implemented. Continue with repointing baseline/planning reports onto the new snapshots and the QML "Budget" section replacement (Phase B items 7-8) before Phase C's actual ledger/commitments/time/procurement work. This keeps security, Decimal Money/rate/quantity work, integration composition, and configuration aggregates independently testable.

Then build Project Finance as explicit PM-owned aggregates while preserving valid module ownership: Time supplies approved hours, Procurement supplies PO/receipt facts, Party supplies identities, Approval and Audit remain platform services, and external accounting owns official ledger/payment behavior. Use additive persistence and temporary compatibility only to migrate verified data; delete every fallback, dual-write, alias, and transition adapter at its named phase gate.

The existing QML workspace is not a constraint. Redesign it to expose Financial Profile, Budget Versions, Planned Cost, Commitments, Posted Actuals, Forecast Versions, Change Control, and Billing Preparation as distinct lifecycle-aware sections. This backend-first sequence is the safest path from the current tested cost-reporting feature to a professional multi-tenant SaaS Project Finance capability without creating an unnecessary accounting application.
