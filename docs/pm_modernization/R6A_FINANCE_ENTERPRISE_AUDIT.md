# R6A Finance Enterprise Audit

## 1. Status

**R6A audit status:** COMPLETE, pending owner acceptance of the decisions in Section 46.

**Audit date:** 2026-08-26

**Execution boundary:** Read-only repository audit. No production source, migration, schema, QML, or runtime behavior was changed. R6B was not started and no commit was made.

**Evidence scope:** PM Finance domain models, ORM, repositories, readers, application services, desktop API/DTOs, controllers, presenters, QML, permissions, approvals, audit/events, integration contracts, Alembic baseline, PostgreSQL RLS infrastructure, tests, and prior PM Finance decisions.

## 2. Executive Summary

PM Finance is not a greenfield feature. It already has a substantial governed financial core: versioned budgets and forecasts, canonical cost entries, source-owned commitments, rate snapshots, financial changes, billing preparation, approval workflows, direct tenant/organization scope, forced PostgreSQL RLS, and read-only Accounting outcomes. The strongest design decision is that Project Finance owns managerial/commercial project truth while Accounting owns invoices, tax, GL, statutory postings, receivables, and payments.

The current implementation is not yet enterprise-complete. The highest-risk defects are:

1. The authoritative EVM calculator converts monetary `Decimal` values to binary `float` and contains a reachable undefined `project` reference.
2. `request_delivery()` marks a billing preparation `DELIVERY_PENDING` without a durable PM-to-Accounting outbox, publisher, or worker.
3. transaction ownership is mixed: most Finance application services commit directly while governed approval paths use proper caller-owned units of work.
4. the UI calls a cost-phasing projection "Cash Flow" even though it has no authoritative cash inflow, payment, bank-date, or Accounting data.
5. Finance refresh eagerly assembles a large cross-section workspace; most lifecycle lists use custom card rows rather than server-filtered/sorted `DataTable` queries.
6. billing preparation, handoff, and external outcome mutation all depend on broad `finance.manage` rather than narrowly separated permissions.

No P0 cross-tenant or destructive money-corruption path was proven. R6 should first repair truth, transaction, and permission boundaries, then modernize Finance UI and only later implement a durable, vendor-neutral Accounting integration.

## 3. Current Finance Architecture

```text
QML Finance workspace
  -> PM Finance controller/presenters
  -> ProjectManagementFinancialsDesktopApi + string-safe DTOs
  -> Finance query/services
  -> repository/read contracts
  -> SQLAlchemy repositories/readers
  -> Finance-owned PostgreSQL tables

Time approved event -> Time outbox -> PM Finance inbox -> labor rate snapshot -> ProjectCostEntry
Procurement event    -> Procurement outbox -> PM Finance inbox -> commitment/actual projection
Billing preparation -> Accounting payload contract -> [missing durable outbound delivery]
Accounting outcome  -> external adapter command -> append-only external event
```

Artifact classification:

| Layer/capability | Classification | Finding |
|---|---|---|
| Finance domain and persistence | ACTIVE/AUTHORITATIVE | Owns managerial financial state and history. |
| Snapshot and EVM readers | ACTIVE/AUTHORITATIVE | Snapshot is canonical; EVM algorithm has a precision/runtime defect. |
| Actuals and commitments queries | ACTIVE/AUTHORITATIVE | Server-paged and server-sorted. |
| Budget/forecast/configuration/rate/planned-cost writes | ACTIVE/PARTIAL | Backend exists; governed QML command rollout is incomplete. |
| Billing preparation | ACTIVE/PARTIAL | Domain, approval, source locks, reads, and payload contract exist; outbound delivery does not. |
| Accounting outcome store | ACTIVE/PARTIAL | Append-only/idempotent result evidence exists; no production adapter/worker exists. |
| QML actual lifecycle | WRITE-CAPABLE | Real commands and projected capabilities. |
| Other Finance QML sections | READ-ONLY/PARTIAL | Mostly read surfaces using custom collection blocks. |
| Process-local `domain_events.*_changed` | ACTIVE/UI-ONLY | Post-commit invalidation, not durable business/integration events. |
| "Cash Flow" projection | ACTIVE/MISNAMED | Cost phasing/exposure projection, not authoritative cash flow. |
| Invoice ownership in PM | ABSENT/CORRECT | No fake PM invoice aggregate remains. |

## 4. Final Authority Principles

1. Approved Budget is the exact sum of lines in the one approved Finance-owned budget version. `Project` must not regain a mutable budget field.
2. Forecast ETC is the one approved forecast applicable at the requested as-of date. EAC is posted actual plus approved ETC.
3. Procurement owns purchase orders and their commercial commitment facts. PM stores a Finance projection with source evidence; it does not mutate procurement documents.
4. Time owns time entry and approval. PM Finance owns the immutable labor-cost posting produced from approved time and a historical rate snapshot.
5. Scheduling owns task dates/baselines. Finance changes request schedule mutation through the Scheduling port.
6. Project Finance owns managerial/commercial projections, billing preparation, and reconciliation evidence.
7. Accounting owns issued invoices, invoice numbers, tax, GL, statutory revenue, AR state, payments, and bank outcomes.
8. Every authoritative mutable Finance aggregate must be tenant/org/project scoped, version checked, audited in the same transaction, and changed through an application UoW.
9. Integration state must be durable, idempotent, retryable, observable, and disposable from source authority; process-local UI signals are never integration evidence.
10. QML formats values but never calculates or rounds financial truth.

## 5. Finance Domain Inventory

| Domain file | Main concepts | Authority/status |
|---|---|---|
| `configuration.py` | `ProjectFinancialProfile`, cost codes/restrictions, billing/budget control policies | Active authoritative configuration |
| `budget.py` | `ProjectBudget`, `BudgetLine`, version status | Active authoritative budget |
| `forecast.py` | forecast/version/line/source-decision models | Active authoritative ETC history |
| `planned_cost.py` | planned-cost versions/lines and completeness diagnostics | Active reproducible calculation snapshot |
| `cost_entry.py` | governed actual-cost ledger lifecycle | Active authoritative actual cost |
| `labor_posting.py` | approved-time posting evidence | Active idempotency/evidence |
| `commitment.py` | commitments, source revisions, matches | Active PM projection of Procurement facts |
| `rate_cards.py` | cost/billing rate cards, lines, selection snapshots | Active authoritative financial rates |
| `financial_change.py` | governed financial change requests and typed impacts | Active authoritative change workflow |
| `billing_profile.py` | commercial profile and fixed-price schedule | Active authoritative PM commercial setup |
| `billing_preparation.py` | preparations, lines, source locks, external events | Active partial handoff workflow |

Repository/read contracts exist for every aggregate family, plus `FinanceSnapshotReader`, `EvmSeriesReader`, rate resolution, approved-time source, Procurement source, and Accounting billing payload publication.

## 6. Schema Inventory

All listed PM Finance tables carry direct `tenant_id` and `organization_id`; project-owned records also carry direct `project_id`. They are classified `TENANT_AND_ORGANIZATION`, have explicit scope indexes, and are included in the forced-RLS baseline.

| Family | Tables | Version/concurrency |
|---|---|---|
| Configuration | `project_finance_profiles`, `project_finance_cost_codes`, `project_finance_cost_code_restrictions` | profile/config mutations are versioned where mutable; uniqueness/checks enforce scope and policy |
| Budget | `project_finance_budgets`, `project_finance_budget_lines` | parent and lines have versions; one open and one approved project version constraints |
| Forecast | `project_finance_forecasts`, `project_finance_forecast_lines`, `project_finance_forecast_source_decisions` | forecast/lines versioned; source decisions append derivation evidence |
| Planned cost | `project_finance_planned_cost_versions`, `project_finance_planned_cost_lines` | immutable/versioned snapshots and lines |
| Actual cost | `project_cost_entries`, `project_approved_time_labor_postings` | cost entry versioned; labor posting is idempotent evidence |
| Commitments | `project_commitments`, `project_commitment_lines`, `project_commitment_source_revisions`, `project_commitment_matches` | aggregate/line concurrency plus source revision/match evidence |
| Rates | `project_finance_rate_cards`, `project_finance_rate_card_lines` | effective-dated and versioned |
| Change control | `project_finance_change_requests`, `project_finance_change_impacts` | request/impact versioning and base-revision evidence |
| Billing | `project_billing_profiles`, `project_billing_schedule_lines`, `project_billing_preparations`, `project_billing_preparation_lines`, `project_billing_source_locks`, `project_billing_external_events` | mutable heads versioned; lines/locks/events governed by parent and uniqueness |
| Inbound integration | `project_finance_inbox_receipts` | source message idempotency/dedup |
| Shared/source-owned | `financial_periods`, `platform_time_financial_outbox`, `inventory_procurement_financial_outbox` | platform period authority and source-owned outboxes |

The fresh-schema Alembic baseline creates the current tables and applies RLS. No R6 migration was created. Children do not rely only on a parent policy because direct tenant/org columns and policies are present. Foreign keys protect ownership relations, while unique/check constraints cover revisions, open/approved heads, positive/nonzero monetary lines, dates, currencies, source locks, and idempotency keys.

## 7. Budget

- Authority: `ProjectBudget` plus `BudgetLine`; approved amount is exact `SUM(BudgetLine.amount)` for the approved version.
- Lifecycle: draft -> submitted -> approved/rejected/closed/superseded. Approved versions are immutable; changes create a successor revision.
- Constraints: one open draft/submitted version and one approved version per project, revision uniqueness, currency consistency, nonnegative lines.
- Concurrency: budget and line row versions; line mutation also advances the parent version.
- Approval: Platform Approval workflow applies within one UoW, rejects self-decision, writes fail-closed audit, and publishes invalidation after commit.
- Projection: Project catalog and portfolio consume the Finance read projection. Unauthorized callers are omitted/redacted server-side through `finance.read`, not only hidden in QML.
- No `Project` write field is authoritative or required. No unsafe "Manage Budget" destination was found; current Finance navigation is real but mostly read-only.

## 8. Forecast

- Authority: one approved `ProjectForecast` applicable at the explicit as-of date.
- Versions preserve revision, predecessor, generation mode, source lines, and source decisions. Approval supersedes the former approved version.
- Automatic inputs are planned-cost remainder, posted-actual offsets, and open commitments. Manual ETC and risk contingency are explicit governed inputs.
- Generation rejects incomplete planned-cost snapshots, future/unreconstructable source state, inactive risks, duplicate dimensions, and currency mismatch.
- Forecast approval is governed and audited; approved lines are immutable historical evidence.
- Backend functionality is mature, but create/edit/submit/approve QML workflows are not yet exposed.

## 9. ETC / EAC

Canonical formulas:

```text
ETC = open commitments + remaining planned cost + manual ETC + risk contingency
EAC = posted actual cost + approved forecast ETC
VAC = approved budget - EAC
Committed available = approved budget - posted actual cost - open commitments
```

Actuals and commitments offset planned slices before remaining plan is included. A cost-code manual estimate replaces all remaining plan in that cost code; a task-level manual estimate replaces only the matching cost-code/task dimension. Cost-code and task-level overrides cannot be mixed for the same cost code. Open commitments remain included and are not replaced by manual ETC. If no approved forecast exists for the as-of date, ETC/EAC/VAC are unavailable rather than silently estimated.

## 10. Risk / Contingency

Risk contingency is an additive forecast line linked to a PM Register risk. Only active/actionable risks may contribute; approved, rejected, or closed register items are rejected. A risk may appear once per generation. The amount, cost code, optional task, period, and currency are snapshotted.

There is no probability-weighting engine. The entered amount is the approved managerial contingency. Register owns risk identity/status; Finance owns the monetary forecast effect. R6 must not mutate risk authority or invent probabilistic accounting without an approved policy.

## 11. Commitments

Procurement owns purchase orders. PM Finance owns an idempotent, scoped projection in `ProjectCommitment*`, with source revisions and receipt/accrual matching. Open commitment is remaining authoritative PO obligation, not a manually editable Finance duplicate. Source messages travel through the Procurement outbox and PM Finance inbox in one consuming transaction. QML commitments use a server-paged, server-sorted `DataTable`.

## 12. Actual Costs

`ProjectCostEntry` is the single canonical actual-cost ledger for manual, approved-time, and Procurement-derived entries. Lifecycle is draft -> submitted -> approved -> posted -> reversed. Only posted entries count as actual. Corrections use an immutable reversal entry and mark the original reversed; history is not overwritten.

Posting requires an open Platform financial period and captures transaction amount/currency, organization-base amount/currency, FX rate/date/source/capture time, cost code, optional task/resource, source identity, and actor timestamps. Command/source idempotency prevents duplicate postings. Actuals QML is the most complete write surface and uses authoritative projected capabilities.

## 13. Time-Based Cost

Time remains authoritative for entry, period, submission, and approval. An approved-time event is consumed from the Time outbox, deduplicated in the Finance inbox, resolved against the effective historical cost rate, and snapshotted in `ApprovedTimeLaborPosting` plus a posted `ProjectCostEntry`. Finance never recomputes historical labor cost from a resource's current rate during reads. Sensitive labor/rate detail is separately gated by `finance.read_sensitive`.

## 14. Rates

`ProjectRateCard` and effective-dated `RateCardLine` own PM financial cost and billing rates. Resolution records origin, card/line/version, effective date, amount, currency, and modifiers. Project overrides take precedence over organization-level lines. Resource identity/capacity remains Resource-owned; Finance should continue to own historical financial rate policy and snapshots.

The current Resource hourly rate can act as a compatibility/fallback origin during rate resolution, but it must not become historical posting truth. R6D should make every fallback explicit and eventually remove any ambiguous mutable-rate dependency.

## 15. Currency / Money / Rounding

- Canonical application/domain money uses `Decimal`; database money uses `Numeric(19,4)` and explicit exchange-rate precision.
- Platform financial primitives provide `Money`, `CurrencyCode`, decimal quantity/rate types, minor-unit rules, and default half-even rounding.
- Budget, forecast, rate, billing, and preparation lines enforce parent currency consistency.
- Posted costs preserve transaction and base-currency snapshots. General reporting-currency conversion is not implemented.
- Desktop DTO monetary values are canonical decimal strings; QML formats labels and does not calculate financial truth.
- Unsafe canonical float paths remain in EVM metrics/series. Float conversion in Excel/PDF/chart adapters is presentation-only and acceptable only after canonical Decimal calculation.
- Portfolio aggregation across unlike currencies is not authoritative. R6 should fail closed or group by currency until an approved FX/reporting-currency policy exists.

## 16. Financial Change Requests

`FinancialChangeRequest` owns the governed proposal and `FinancialChangeImpact` owns typed budget, forecast, and schedule effects. Creation snapshots the approved budget/forecast IDs and revisions. Submission creates a Platform approval request in the same UoW. Apply validates that the referenced base versions remain current, creates successor Finance versions, and delegates task/schedule mutation through the Scheduling-owned port rather than importing or editing Scheduling persistence.

The aggregate does not own contracts, purchase orders, or Accounting records. The apply workflow is one of the stronger transaction designs, but older create/edit methods still use service-owned commits. R6C should bring the whole change lifecycle under one caller-owned UoW and expose a truthful command workflow.

## 17. EVM

Current authority is `EarnedValueCalculator` using `EvmSeriesFacts`, baseline task facts, current task progress, canonical actual cost, and approved forecast ETC.

```text
BAC = sum baseline task planned costs
PV  = sum baseline cost * planned completion fraction
EV  = sum baseline cost * current percent complete
AC  = canonical posted actual cost
CPI = EV / AC when AC > 0
SPI = EV / PV when PV > 0
ETC = approved forecast ETC only
EAC = AC + ETC
VAC = BAC - EAC
TCPI(BAC) = (BAC - EV) / (BAC - AC), when denominator > 0
TCPI(EAC) = (BAC - EV) / (EAC - AC), when denominator > 0
```

If cost-loaded baseline lines are absent, the calculator attempts duration-weighted allocation. It deliberately does not invent a CPI-derived ETC.

**P1 defects:** every monetary value is converted from `Decimal` to `float`, including BAC/PV/EV/AC/ETC/EAC/VAC. The no-duration fallback references an undefined `project` variable, causing a reachable `NameError` when BAC is positive and baseline durations are unusable. The result DTO also carries floats. Prior documentation claiming all canonical float paths were retired is stale. R6E must repair this before adding visual polish.

## 18. Variance

Canonical cost-control variance is `VAC = approved budget - EAC`; positive means favorable remaining budget. Portfolio budget pressure uses `EAC - approved budget`, which is mathematically the sign inverse and valid only when named as pressure/overrun. Dashboard "cost variance" currently uses `actual - planned` for the selected operational period, a different measure.

These calculations are not duplicate authorities if clearly named and dated, but current labels can conflate them. R6E must publish a variance taxonomy with formula, sign convention, currency, baseline/forecast revision, and as-of date for every read model.

## 19. Cash Flow

The current `build_period_cashflow` projection groups planned, committed, actual, and forecast cost stages by period and calculates exposure. It has no customer receipts, supplier payments, invoice due/paid dates, bank dates, or external Accounting cash facts. Therefore it is **cost phasing/project cost flow**, not authoritative cash flow.

This is a P1 semantic issue, not necessarily a calculation error. R6E should rename the current surface to "Cost Phasing" and preserve its authority. A true cash-flow surface must remain deferred until Accounting supplies authoritative inflow/outflow outcomes.

## 20. Billing Profile

`ProjectBillingProfile` is the PM-owned commercial contract projection: customer/account references, billing method, contract currency/value, payment terms, retention, legal hold, status, and version. `ProjectFinancialProfile` is separate financial control configuration; the similar names do not represent duplicate authority.

One project profile is enforced. Activation is version checked and audited. PM references commercial terms but does not create a statutory customer master or invoice.

## 21. Billing Schedule

`ProjectBillingScheduleLine` owns fixed-price preparation milestones: amount, currency, due date, optional task/acceptance reference, readiness status, and version. It is a preparation schedule, not an issued invoice schedule. Lines are PM-owned, directly scoped, checked for positive amounts, and immutable after governed consumption. The QML surface is read-only and its list is currently unbounded.

## 22. Billing Preparation

`ProjectBillingPreparation` is the governed PM commercial handoff package. It stores period, currency, status, correction link, line count/total, idempotency key, source lines, approval state, and delivery state. Supported source lines are:

1. ready fixed-price schedule lines;
2. approved time with a snapshotted billing rate;
3. posted costs with a snapshotted cost-plus markup.

Submission and approval are atomic with Platform governance. Approval finalizes source locks. Rejection releases reservations. The desktop API exposes nine command families, but QML currently exposes a read-only commercial surface, so backend maturity must not be described as completed product UX.

## 23. Source Locks

`ProjectBillingSourceLock` provides unique source-consumption protection across preparations. A source is reserved while a preparation is governed, finalized on approval, and released on rejection. Scope and unique constraints prevent duplicate billing preparation for the same source. This is authoritative PM evidence, not an Accounting invoice lock.

Concurrency protection is strong at the database boundary. R6F should add adversarial concurrent-source tests and ensure correction preparations reference, rather than mutate, prior approved packages.

## 24. Revenue

PM has no recognized/statutory revenue authority. Current commercial reads derive **projected commercial revenue** from fixed-price contract value or approved billing preparation/outcome evidence. External invoiced/paid values are Accounting outcomes, not PM-created records.

The word "Revenue" must be qualified as projected/commercial unless an Accounting-sourced recognized-revenue fact is present. No revenue-recognition schedule, tax allocation, GL posting, or accrual engine belongs in R6.

## 25. Profitability

For fixed-price work:

```text
Projected revenue at completion = contract value
Projected margin = projected revenue - canonical EAC
Projected margin % = projected margin / projected revenue, when revenue > 0
```

T&M and cost-plus profitability correctly return unavailable because forecast billable volume and recoverability policy are not authoritative. Profitability details require `finance.read_profitability`; normal Finance readers do not receive sensitive margins. This conservative absence is preferable to a fabricated estimate.

## 26. Accounting Handoff

The vendor-neutral port `ProjectBillingPreparationPublisher` and versioned `project_billing_preparation.v1` Pydantic payload establish a reusable application boundary for Desktop or future HTTP workers. The payload contains PM preparation evidence and does not claim invoice, tax, GL, or payment authority.

However, `request_delivery()` currently changes the preparation to `DELIVERY_PENDING` and commits without atomically inserting an outbound message. There is no configured publisher/worker proving delivery. This state therefore means "requested locally," not "durably queued." R6G must either add a transactional PM Accounting outbox or rename/block the state until durable enqueue exists.

## 27. Accounting Outcomes

`ProjectBillingExternalEvent` is append-only, scoped, typed, timestamped, and idempotent by external key. It records acknowledgements and externally reported invoice/payment outcomes, then updates preparation status. Latest outcomes are fetched in a batched query, avoiding per-row N+1 reads.

External events do not contain a full Accounting ledger or invoice aggregate. The existing command is not exposed to QML, which is correct; a future authenticated integration worker/service principal should own it. Broad human `finance.manage` is not an acceptable final permission for injecting external Accounting outcomes.

## 28. Integration / Outbox

| Flow | Durable outbox | Inbox/dedup | Atomic state + message | Maturity |
|---|---:|---:|---:|---|
| Approved Time -> PM Finance | Yes, source-owned | Yes | Yes | Complete |
| Procurement -> PM Finance | Yes, source-owned | Yes | Yes | Complete |
| PM billing -> Accounting | No | N/A | No | Contract only/partial |
| Accounting -> PM outcome | External idempotency supported | Event-key dedup | Adapter not implemented | Domain endpoint only/partial |
| Finance -> QML refresh | No, process-local signal | N/A | Emitted after commit | UI invalidation only |

Budget/forecast/change/billing approval events are durable Platform governance/audit evidence where emitted through UoW. `domain_events.budgets_changed`, `tasks_changed`, `planned_costs_changed`, and `billing_preparations_changed` are deliberately process-local post-commit cache invalidations and must never be documented as business integration events.

## 29. Finance Read Models

`FinanceSnapshotReader` is the canonical disposable read model. It projects approved budget identity/total/currency, approved forecast, tasks, planned cost, commitments, actuals, project resources, assignments, and rates. `EvmSeriesReader` prepares baseline/EVM facts. SQL readers always receive tenant/org/project scope.

Read-model cutover is substantially complete for workspace snapshots, approved budget, actuals, commitments, EAC/VAC, portfolio heatmap, dashboard Finance facts, desktop DTOs, and QML presenters. Remaining noncanonical or ambiguous formulas are:

- EVM's internal float recomputation;
- dashboard period `actual - planned` labeled too generically;
- portfolio pressure uses the inverse sign of VAC;
- "Cash Flow" is a cost-phasing calculation;
- chart/export adapters convert canonical values to float for rendering;
- commercial projection is intentionally not statutory revenue.

The snapshot is disposable and rebuildable from authorities. It is not written back and does not become a second source of truth.

## 30. Portfolio Finance

Portfolio heatmap reads approved budget and EAC through batched Finance projections rather than hydrating each project aggregate. This avoids an obvious N+1. Budget pressure is a managerial cross-project read, not a new authority.

Parity limitations: portfolio rows must preserve project visibility, tenant/org scope, explicit as-of semantics, and currency. Cross-currency totals are not authoritative without conversion policy. Scale beyond the current top-N/paged projections requires PostgreSQL plans and 10k/50k fixtures in R6H.

## 31. Current QML / IA

Current workspace has an explicit pinned project selector and grouped, scrollable local navigation. Its 13 sections are:

| Group | Sections |
|---|---|
| Configuration | Profile, Rate Cards |
| Planning | Budget Versions, Budget Lines, Planned Costs, Forecast |
| Cost Control | Actuals, Change Control, Commitments |
| Commercial | Billing Preparation |
| Insights | Variance, Reports, Activity |

The page uses controller/presenter DTOs and does not leak QML types into domain/application code. Planning and Finance correctly require explicit project pinning. Section QML is lazy-loaded, but controller refresh eagerly builds most section data, so visual laziness does not provide query laziness.

The IA is feature-complete in vocabulary but too fragmented for daily enterprise use. It exposes technical aggregates rather than user intents and lacks a consistent list/inspector/command pattern outside actuals and commitments.

## 32. Current Write UX

| Surface | Current UX classification |
|---|---|
| Manual actual create/edit | Authoritative and write-capable |
| Actual submit/approve/reject/post/reverse | Authoritative governed lifecycle |
| Budget version/line commands | Backend complete, QML absent |
| Forecast generation/version/approval | Backend complete, QML absent |
| Planned-cost calculation | Backend complete, QML absent |
| Profile/cost-code/rate commands | Backend complete, QML absent |
| Financial change commands | Backend complete, QML absent |
| Billing profile/schedule/preparation commands | Backend substantial, QML read-only |
| Accounting delivery | Backend command unsafe to expose until durable outbox exists |
| Accounting outcome | Integration-only command; correctly absent from QML |

Existing Finance dialogs are `ManualActualEditorDialog`, `ActualLifecycleDialog`, and `FinancialsDialogHost`. No no-op rebalance or fake invoice action was found in the Finance workspace. Missing command UX must be added incrementally with deny-safe projected capabilities, required-field validation, optimistic-concurrency feedback, and post-success authoritative refresh.

## 33. Permissions / SoD

Finance permissions currently include:

```text
finance.read
finance.read_sensitive
finance.read_profitability
finance.manage
finance.export
budget.manage / budget.approve
forecast.manage / forecast.approve
plannedcost.manage
financial_change.manage
project_cost.create / update_draft / submit / approve / post / reverse
approval.request / approval.decide
report.view / report.export
```

Global and project-scoped checks are enforced in application services/read queries. QML actual actions use server-projected capabilities rather than fail-open assumptions. Sensitive rates/labor and profitability have separate read permissions.

Platform ApprovalService forbids requester self-approval and self-rejection with `APPROVAL_SELF_DECISION_FORBIDDEN`, and records the authenticated deciding principal. This applies to budget, cost, financial change, and billing preparation participants. Default roles remain broad: `finance_controller` can prepare, approve, post, and reverse, while project-manager/owner role sets combine budget/forecast manage and approve. That supports small teams but weakens strict role separation between different users. Billing profile/preparation/handoff/external outcome all use `finance.manage`; R6F/R6G need granular `billing.prepare`, `billing.approve`, `accounting.handoff`, and integration-only outcome permissions.

## 34. Concurrency

| Mutable aggregate | Protection | Finding |
|---|---|---|
| Financial profile/cost-code configuration | version/uniqueness and scoped updates | Active; normalize under UoW |
| Budget and lines | parent + line versions, revision/open/approved DB constraints | Strong |
| Forecast and lines | versions, revision/open/approved DB constraints | Strong |
| Planned-cost version/lines | immutable calculated version plus completeness evidence | Strong snapshot semantics |
| Cost entry | expected version through lifecycle; immutable reversal | Strong |
| Commitment projection | source revision/idempotency, aggregate/line state checks | Strong ingestion semantics |
| Rate card/lines | versions/effective dates/overlap rules | Strong, add concurrent overlap tests |
| Financial change/impacts | expected versions and base budget/forecast revisions | Strong apply validation |
| Billing profile/schedule | expected versions and uniqueness | Strong |
| Billing preparation | version, idempotency key, source-lock uniqueness | Strong |
| External outcome | external idempotency key and append-only event | Strong store, missing adapter |

The primary concurrency debt is not absent row versions; it is mixed transaction ownership and incomplete adversarial PostgreSQL coverage across every mutable family.

## 35. Transactions

Repositories generally flush and do not commit, which is correct. Governed submissions/decisions use dedicated UoWs for financial changes and billing preparations. Platform Approval applies participant mutation, approval state, audit, and events in one transaction, then sends UI invalidation after commit.

Eleven Finance application services still own direct commits: budget, commitment, configuration, cost entry, financial change, forecast generation/version, billing profile/preparation, planned cost, and rate cards. Audit is usually written with `commit=False` and `fail_closed=True` in the same SQLAlchemy session before that commit, so ordinary single-service commands are atomic. The inconsistency becomes risky when commands span aggregates, outbox writes, or caller workflows.

Final target:

```text
command -> authorization -> domain mutation -> audit/outbox
        -> repository flush -> caller/UoW commit -> post-commit invalidation
```

R6C-R6G should migrate one bounded workflow at a time. Repository commits were not found; the debt is application-service commit ownership.

## 36. Audit / Events

Fail-closed audit exists for budget creation/mutation/approval, forecast generation/version/approval, cost lifecycle, financial changes, configuration/rates, billing profile/schedule/preparation, handoff request, and external outcomes. Governed approval history is append-only Platform evidence, not reconstructed pseudo-history. Cost reversals, forecast source decisions, commitment source revisions, billing source locks, and external events add domain-specific evidence.

Business-domain events are uneven. Approval UoWs record durable approval events and source integrations use durable outboxes. Most Finance "changed" events are post-commit in-process refresh signals. R6 must use explicit durable integration events such as `BillingPreparationReadyForAccounting` only when they are atomically stored in an outbox; it must not rename a QML refresh signal and treat it as evidence.

## 37. Tenant / Organization / Project Scope

Every Finance-owned table has direct tenant and organization scope; project-owned tables also store direct project scope. Services obtain active scope IDs from tenant context, repositories add scope predicates, readers receive explicit scope, and project permissions/visibility are checked above persistence.

Tenant/org RLS is defense in depth; it does not replace per-user project authorization. Source consumers validate source and target scope before writing. Parent-child IDs, source locks, and idempotency records are constrained within the same scope. No nullable-tenant Finance table or intentional Finance RLS exclusion was found.

## 38. RLS

All Finance tables are enumerated in `TENANT_AND_ORGANIZATION_TABLES`. The fresh PostgreSQL baseline applies `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, and explicit SELECT/INSERT/UPDATE/DELETE policies. Runtime transaction context comes from the authenticated session or validated worker scope. Runtime-role validation rejects superuser and `BYPASSRLS`; the runtime role does not own protected tables.

Existing PostgreSQL integration evidence proves policy coverage, missing-context denial, cross-scope denial, and generic parent/child isolation under a non-superuser, non-`BYPASSRLS` role. R6H should add Finance-specific negative tests that directly attack budget-line, forecast-line, cost-entry, commitment-line, billing-line, source-lock, and external-event tables with mismatched parent IDs. This is a coverage gap, not evidence that current policies fail.

## 39. Performance

The canonical snapshot runs a bounded set of roughly ten SQL statements, but loads complete project tasks, planned/forecast lines, commitments, actuals, resources, and assignments, then aggregates in Python. Workspace refresh additionally loads all project/task options, configuration, lifecycle history, selected lines, change impacts, billing schedule, paged preparations, and latest outcomes regardless of active section.

Strengths:

- actuals and commitments use database count, allowed sort-key maps, deterministic tie-breakers, and server pagination;
- billing preparations are paged and latest outcomes are batched;
- portfolio Finance uses batched projections rather than per-project aggregate hydration;
- forecast generation pages through commitment/actual source repositories rather than imposing a silent single-page cap.

Debt:

- budget/forecast/planned-cost versions, financial changes, and billing schedule are unbounded;
- configuration labeling loads complete task/resource/code option sets;
- custom collection sections lack server filter/sort;
- Python aggregation and eager workspace assembly will not scale to high-line-count projects;
- no R6-specific 10k/50k PostgreSQL `EXPLAIN (ANALYZE, BUFFERS)` closure evidence exists yet.

R6B should establish section-scoped query contracts before visual redesign. R6H owns query plans and scale fixtures.

## 40. Responsive Findings

Source review shows a sound shell foundation: fixed contextual navigation, explicit project selector, grouped/scrollable section navigation, fill-width layouts, and a billing grid that changes 3/2/1 columns around 720/440 px. Risks remain:

- fixed dialog preferred widths of roughly 480/620 px need shell-width clamping;
- `FinancialsCollectionBlock` keeps row metadata near 250 px and does not consistently switch to a stacked layout;
- 13 sections create long navigation and deep page switching;
- custom card collections can create excess whitespace and weak scanability;
- eager controller refresh remains expensive even when QML sections are lazy;
- no current visual certification was proven at 1024x640, 1280x720, 1366x768, 1440x900, and 1920x1080.

No QML client-side monetary formula was found. R6B/R6H must add characterization and visual checks rather than redesign blindly.

## 41. Legacy / Duplicate Paths

| Path/claim | Classification | Required disposition |
|---|---|---|
| Mutable Project budget field | Retired | Must remain absent |
| PM invoice aggregate/placeholder | Retired | Must remain absent |
| Transitional Finance read fallbacks | Mostly retired | Remove any formula fallback after R6E cutover tests |
| `domain_events.*_changed` | Active UI-only, not legacy | Keep only as post-commit invalidation; do not treat as integration |
| `FinancialsCollectionBlock` lists | Active partial UI | Replace where enterprise table/query behavior is required, then delete dead QML/qmldir entries |
| EVM float result path | Active defective legacy calculation | Replace with Decimal authority in R6E; delete old float path and tests that encode it |
| "Cash Flow" name | Active semantic legacy | Rename to Cost Phasing unless true Accounting cash facts are added |
| Resource mutable hourly-rate fallback | Active compatibility path | Mark explicit and retire when rate-card coverage is complete |
| Prior docs claiming all float paths retired | Stale documentation | Supersede during R6 closure |
| Accounting publisher contract | Active seam, not dead code | Keep; implement durable adapter path or do not expose delivery |

No duplicate authoritative budget, forecast, commitment, actual, billing preparation, or Accounting invoice store was found. Similar projections exist for different semantics and must be renamed, not merged. Any code made temporary during R6 must be marked with its deletion phase and removed before R6H closure.

## 42. Final Authority Matrix

| Concept | Authority/domain owner | Persistence/read model | Write service/permission | Version/audit/integration | Status / R6 owner |
|---|---|---|---|---|---|
| Approved Budget | PM Finance approved budget lines | budget tables / snapshot | BudgetService; `budget.manage/approve` | Versioned, audited, governed | Authoritative / R6C |
| Budget version | PM Finance | budget + lines | BudgetService | Revisioned/immutable after approval | Authoritative / R6C |
| Forecast | PM Finance approved forecast | forecast tables / snapshot | Forecast services; `forecast.manage/approve` | Revisioned, source decisions, audited | Authoritative / R6C |
| ETC | approved forecast lines | Finance snapshot | forecast generation | As-of/versioned/audited | Authoritative / R6C |
| EAC | posted actual + approved ETC | Finance snapshot | derived read; `finance.read` | Disposable read | Authoritative / R6C |
| Risk contingency | PM Finance amount linked to Register risk | forecast line/decision | forecast generation | Versioned snapshot | Authoritative / R6C |
| Commitment | Procurement PO fact; PM Finance projection | commitment tables / snapshot | source consumer; Finance read/manage | Source revision + inbox/outbox | Authoritative projection / R6D |
| Actual cost | PM Finance posted cost entry | cost-entry ledger / snapshot | CostEntryService; granular project-cost permissions | Versioned, audited, reversal | Authoritative / R6D |
| Time-derived cost | PM Finance posting from Time authority | labor posting + cost entry | Time consumer | Rate snapshot + inbox/outbox | Authoritative / R6D |
| Rates | PM Finance financial rate cards | rate tables/resolver | RateCardService; currently `finance.manage` | Effective/versioned/audited | Authoritative / R6D |
| Financial change | PM Finance governed request | change/impact tables | FinancialChangeService; `financial_change.manage` + approval | Version/base refs/audit | Authoritative / R6C |
| EVM | PM Finance calculation over baseline/progress/cost facts | EVM reader/calculator | read; `finance.read` | Disposable read | Defective precision / R6E |
| Variance | PM Finance named derived metrics | snapshot/dashboard/portfolio | read | Disposable read | Partial taxonomy / R6E |
| Cost phasing | PM Finance staged cost projection | cashflow builder | read | Disposable read | Misnamed / R6E |
| Billing Profile | PM Finance commercial setup | billing profile | BillingProfileService; `finance.manage` | Versioned/audited | Authoritative / R6F |
| Billing Schedule | PM Finance preparation schedule | schedule lines | BillingProfileService | Versioned/audited | Authoritative / R6F |
| Billing Preparation | PM Finance handoff package | preparation/lines/locks | PreparationService; `finance.manage` + approval | Versioned/governed | Authoritative PM package / R6F |
| Source Lock | PM Finance consumption evidence | source-lock table | PreparationService | Unique/reserved/finalized | Authoritative / R6F |
| Projected revenue | PM Finance commercial projection | projection DTO | read; `finance.read` | Disposable read | Limited / R6F |
| Profitability | PM Finance projection | calculator/read DTO | read; `finance.read_profitability` | Disposable read | Fixed-price only / R6F |
| Accounting Handoff | PM request; Accounting receives | payload contract; no outbox | delivery command; broad `finance.manage` | Not durably queued | Partial / R6G |
| Accounting Outcome | External Accounting | append-only external event/read | future worker-only command | Idempotent evidence | Partial adapter / R6G |
| Invoice/tax/GL/AR/payment | External Accounting | External system only | External system | External authority | Explicit non-scope |

## 43. Defect Priority Matrix

### P0

No proven P0 cross-tenant access, destructive corruption, duplicate financial authority, or fabricated Accounting record.

### P1

| Defect | Impact | Resolution phase |
|---|---|---|
| EVM uses binary floats for canonical money and has undefined `project` fallback | Incorrect/unstable financial metrics and runtime failure | R6E |
| Billing delivery state changes without durable outbound enqueue | False delivery semantics; lost handoff after crash | R6G |
| Mixed application-service commit ownership | Cross-aggregate/outbox atomicity and composability risk | R6C-R6G |
| "Cash Flow" is cost phasing, not authoritative cash flow | Misleading managerial decision support | R6E |
| Broad `finance.manage` controls billing preparation, handoff, and external outcomes | Weak least privilege/integration identity boundary | R6F-R6G |

### P2

| Defect | Impact | Resolution phase |
|---|---|---|
| Eager all-section workspace assembly/full snapshot hydration | Slow refresh and poor high-volume scalability | R6B/R6H |
| Most Finance lists lack shared server table/filter/sort contracts | Page-local usability and scale gaps | R6B |
| Governed backend commands absent from QML | Product workflow incomplete | R6C-R6F |
| Unbounded version/schedule/change lists | Memory/query growth | R6B/R6H |
| Cross-currency portfolio totals lack an approved conversion policy | Unsafe aggregate reporting | R6B owner decision |
| Finance-specific child-table RLS attack tests absent | Security evidence incomplete | R6H |
| Variance labels/sign/as-of semantics are inconsistent | User interpretation risk | R6E |
| Responsive behavior is source-reviewed but not five-size certified | Layout regression risk | R6H |

### P3

Stale modernization claims, "Financials"/"Finance" naming inconsistency, technical 13-section IA, custom collection duplication, and compatibility-rate terminology require cleanup after authoritative cutovers.

## 44. Proposed Final Finance IA

Retain one canonical PM Finance workspace and explicit project pinning. Replace the 13 technical destinations with six intent-oriented local destinations:

1. **Overview** - approved budget, actual, commitment, ETC/EAC/VAC, key alerts, currency/as-of evidence.
2. **Planning** - budget versions/lines, planned costs, forecast versions/lines, risk contingency.
3. **Costs** - actual ledger, commitments, rates, source and financial-period evidence.
4. **Performance** - EVM, variance taxonomy, cost phasing, reports.
5. **Commercial** - billing profile, schedule, preparation, projected revenue/profitability, Accounting outcomes.
6. **Controls** - financial profile, cost codes, change control, approvals, audit/integration status.

Each destination should have section-scoped server queries, truthful capability projection, a shared table/list and inspector where appropriate, fixed contextual controls, and no hidden mutation. All-project support remains query-contract and permission dependent; Planning and Commercial require an explicit project.

## 45. Proposed R6B-R6H Plan

### R6B - Finance Workspace and Read Architecture

- Scope: six-destination IA, section-scoped query DTOs/readers, server paging/filter/sort, authoritative loading/error/empty states, query lazy-loading, permission projection, and truthful currency/as-of labels.
- Non-scope: no new financial formulas or write commands.
- Prerequisites: approve IA and single/multi-currency policy.
- Schema: none expected; indexes only if PostgreSQL evidence proves need.
- QML: restructure read surfaces behind existing desktop facade; actual/commitment behavior preserved.
- Gates: no eager inactive-section reads, deterministic server queries, 1024 minimum layout characterization, tenant/project visibility tests, no client-side money logic.

### R6C - Budget and Forecast Governance

- Scope: governed budget/forecast/change write UX, manual ETC/risk semantics, successor revisions, approval/SoD, concurrency refresh, caller-owned UoWs.
- Non-scope: actual/commitment posting and Accounting.
- Prerequisites: R6B read contracts and SoD decision.
- Schema: only constraints/indexes proven necessary; no duplicate authority.
- QML: required fields, version conflicts, approval evidence, post-command authoritative refresh.
- Gates: approved-budget exact-sum tests, manual-override/risk tests, self-approval denial, stale-write tests, audit atomicity, no service-owned commits in migrated workflows.

### R6D - Cost, Commitments, Actuals, and Rates

- Scope: canonical ledger UX, commitment provenance/matching, historical rate selection, financial periods, currency snapshots, granular commands, transaction normalization.
- Non-scope: Procurement document mutation, payroll, or HR compensation.
- Prerequisites: R6B and rate-ownership decision.
- Schema: only evidence-driven constraints/indexes.
- QML: server tables/inspectors, source evidence, correction/reversal workflow.
- Gates: Time/Procurement idempotency, historical-rate immutability, reversal math, period lock, concurrent posting, sensitive-field redaction.

### R6E - EVM, Variance, and Cost Phasing

- Scope: Decimal-only EVM, remove undefined fallback, explicit formula/as-of/currency metadata, variance taxonomy, rename current Cash Flow to Cost Phasing.
- Non-scope: real bank/accounting cash flow or CPI-invented forecasts.
- Prerequisites: canonical R6B reads and R6C forecast facts.
- Schema: none expected.
- QML: truthful metrics, unavailable states, no formulas.
- Gates: Decimal precision/rounding tests, zero-denominator tests, cross-reader parity, no legacy float authority, clear sign conventions.

### R6F - Billing Preparation, Projected Revenue, and Profitability

- Scope: governed profile/schedule/preparation command UX, source locks/corrections, granular permissions, projected-commercial terminology, fixed-price profitability.
- Non-scope: invoice issuance, tax, GL, AR, payment mutation, or external delivery.
- Prerequisites: R6B and revenue/approval decisions.
- Schema: permission seed changes and only proven billing constraints/indexes.
- QML: phased commands with inspector/evidence; handoff remains disabled until R6G.
- Gates: source-lock concurrency, approval/self-decision denial, sensitive profitability redaction, no fake invoice state, no duplicate source consumption.

### R6G - Accounting Handoff and Integration

- Scope: transactional outbound outbox, `BillingPreparationReadyForAccounting` integration event, publisher/worker, retries/backoff, idempotency, quarantine, service-principal outcome ingestion, durable delivery/ack status.
- Non-scope: vendor-specific Accounting domain logic inside PM.
- Prerequisites: approved target adapter behavior and R6F package authority.
- Schema: PM outbound outbox/delivery-attempt state if the shared outbox cannot serve it.
- QML: read-only integration status/retry authorization; never direct external mutation.
- Gates: crash-before/after-publish tests, duplicate delivery tests, poison-message quarantine, scoped worker context, audit/outbox atomicity, external acknowledgement evidence.

### R6H - Integrated Hardening, Validation, and Closure

- Scope: PostgreSQL concurrency/RLS/scale suite, 10k/50k fixtures, `EXPLAIN (ANALYZE, BUFFERS)`, five-size QML verification, qmllint, stale-code/docs cleanup, authority reconciliation.
- Non-scope: new Finance product capabilities.
- Prerequisites: R6B-R6G accepted or explicitly deferred.
- Schema: final baseline/index reconciliation only.
- QML: regression/accessibility/responsive closure.
- Gates: direct Finance child-table RLS attacks, runtime role proof, query budgets, no dead/temporary paths, no service-owned commits in migrated Finance commands, no canonical monetary floats, complete docs and targeted/full-suite evidence agreed for closure.

## 46. Owner Decisions Required

| Decision | Option A | Option B | Recommendation and consequence |
|---|---|---|---|
| Final Finance IA | Six intent destinations in Section 44 | Retain 13 technical sections | **A.** Fewer context switches and a stable enterprise workspace; requires R6B QML/query regrouping. |
| Currency scope for R6 | One project currency; group/fail closed across currencies | Add reporting currency and FX aggregation now | **A.** Preserves correctness and keeps R6 bounded; enterprise FX becomes a later shared financial-platform program. |
| SoD strength | Enforce self-approval plus granular prepare/approve/handoff roles | Keep broad `finance_controller` only | **A.** Least privilege; small local teams can assign multiple roles to different principals, never bypass self-decision. |
| Rate history ownership | PM Finance owns financial rate cards/snapshots; Resource owns identity/capacity | Resource mutable rate owns financial history | **A.** Preserves historical cost/billing truth and module boundaries. |
| Revenue terminology | "Projected commercial revenue/margin" | Generic "Revenue" | **A.** Avoids claiming statutory recognition. |
| Billing command rollout | Profile/schedule -> preparation -> approval -> handoff | Expose all commands together | **A.** Prevents unsafe handoff exposure before R6G durability. |
| R6G activation | Build durable generic outbox/worker only when adapter behavior is approved | Mark delivery from the existing local state only | **A.** Never claim queued/delivered without durable evidence; until approved, handoff stays disabled/deferred. |

These decisions block final R6B/R6F presentation contracts. Budget/forecast authority, Accounting ownership, explicit project pinning, and self-approval prohibition are already proven and are not open decisions.

## 47. Explicit Deferred Scope

R6 will not implement General Ledger, Accounts Payable, Accounts Receivable, tax, payroll, bank reconciliation, statutory accounting, HR compensation, CRM, a Procurement redesign, an external invoice renderer, payment collection, revenue recognition, or an Accounting customer/vendor master. True cash flow and multi-currency portfolio conversion remain deferred until authoritative shared/Accounting contracts are approved.

## 48. R6A Closure Decision

**Decision:** R6A is complete as a repository audit. R6B must not start until the owner accepts or adjusts the seven decisions in Section 46. No P0 issue blocks the application, but the five P1 items must be assigned to their stated R6 phases and cannot be waived as UI polish.

Exit-gate reconciliation:

- [x] 1-10: all domain, ORM, reader, repository, service, desktop API, QML, permission, event, and migration/table artifacts inventoried.
- [x] 11-25: budget, forecast, ETC/EAC, override, risk, commitment, actual, time cost, rate, currency, and rounding authority identified.
- [x] 26-29: EVM, variance, cost-phasing/cash-flow, and portfolio formulas characterized.
- [x] 30-38: billing profile/schedule/preparation, source locks, approval, outcomes, handoff, projected revenue, and profitability characterized.
- [x] 39-42: read-model cutover, fallbacks, duplicate calculations, and duplicate authorities classified.
- [x] 43-47: mutable aggregate concurrency, transaction ownership, commit boundaries, audit atomicity, and outbox atomicity classified.
- [x] 48-51: tenant/org/project visibility, RLS, and direct child-table risks characterized.
- [x] 52-54: monetary float paths, Decimal serialization, and rounding duplication characterized.
- [x] 55-59: IA, dead/placeholder QML, write UX, responsive behavior, and DataTable usage documented.
- [x] 60-63: Resource/Task/Time, Procurement, Scheduling, and external Accounting boundaries preserved.
- [x] 64-70: authority matrix, defect matrix, final IA, phase sequence/gates, genuine decisions, and non-scope completed.
- [x] 71-75: no production implementation, migration, behavior change, R6B work, or commit.

DataTable reconciliation: only Actuals and Commitments currently use shared `DataTable` in authoritative server mode. Billing preparations are server-paged behind a custom collection. Budget, forecast, rate, planned-cost, change, billing schedule, reports, and variance collections use custom blocks or metric layouts and do not provide consistent server sorting/filtering.

R6A evidence is sufficient to plan implementation, but it does not claim five-size visual certification, R6-scale PostgreSQL query plans, a working Accounting adapter, or corrected EVM behavior. Those are explicit later-phase exit gates.

Targeted audit evidence executed with the `pmenv` interpreter:

- 96 selected architecture, approved-budget, forecast, billing, approval, RLS-context, CQRS-reader, and financial edge-case tests passed.
- 2 assertions in `test_project_finance_persistence_guardrails.py` failed because they still encode the retired combined-policy shape: they expect two context-predicate occurrences and fixed teardown indexes. The current shared RLS helper deliberately emits SELECT, INSERT, UPDATE, and DELETE policies (five predicate occurrences because UPDATE has `USING` and `WITH CHECK`) and drops all four before `NO FORCE`/`DISABLE`. Platform RLS-context tests for the current helper passed. This is stale test debt for R6H/architecture-test maintenance, not evidence of weaker RLS and not changed during R6A.
