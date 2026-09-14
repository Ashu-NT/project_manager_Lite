# Project Finance Existing-State Audit and Implementation Plan

Status: R6C closed; R6D CLOSED; R6E CLOSED; R6F-A COMPLETE; R6F-B COMPLETE; R6F-C IN PROGRESS (NOT CLOSED)
Last updated: 2026-09-14
Scope: Project Management finance plus reusable platform financial foundations

## R6F-C Governed Billing Preparation Progress (2026-09-14)

R6F-C is **not closed**. The existing domain already makes draft the only
mutable state, submission creates a Platform Approval request, approval
finalizes source locks, rejection releases them, and approved preparation
lines remain immutable. A domain-level creator-versus-approver check now
rejects self-approval even when another user submitted the request; the
distinct-actor regression passes. Existing success fixtures now use a truly
independent reviewer rather than the creator.

The coupled source-lock defect was resolved with a forward migration and
active-only partial unique index on tenant/org/source identity. A released
lock remains historical evidence but no longer blocks reuse; a reserved or
finalized lock still blocks a duplicate. The repository's active-lock lookup
excludes released history. Draft-line removal atomically deletes the
unapproved line/reservation, recalculates Decimal totals and version, audits,
and emits a typed Commercial event. Draft cancellation retains the preparation
and its lines, releases reserved locks in the governed UoW, and emits a typed
status event. Both reject stale versions or non-draft state. Tests prove source
reuse after rejection, removal, and cancellation. A database partial unique
index also prohibits two non-rejected/non-cancelled corrections from the same
predecessor, permitting a rejected/cancelled attempt to be retried. The
fresh-schema Alembic index test passes. PostgreSQL RLS/concurrency and
correction-chain application tests remain pending; these indexes alone do not
close those gates.

Focused verification at this checkpoint: 43 Billing domain/application/
desktop/approval/migration tests passed. Targeted Ruff F/I, Python compilation,
and `git diff --check` passed. No QML changed in this slice, so visual,
viewport, keyboard, and QML workflow gates remain open. PostgreSQL runtime
role/RLS and concurrent-writer integration remain unverified.

Remaining R6F-C work includes any required draft metadata/replacement editing,
bounded source selectors, profile/schedule/preparation write UX with server
capabilities, correction-chain application/race proofs, PostgreSQL RLS tests,
responsive and keyboard checks, and the full regression matrix. Do not mark
R6F-C complete or begin R6F-D based on the SoD fix alone. No Accounting
publisher or invoice/payment authority was added.

## R6F-B Commercial Read Truth and Setup Closure (2026-09-14)

**R6F-B COMPLETE.** The Commercial projection now uses one tenant/org/project-
scoped SQL `SUM` over approved and subsequent local preparation states, rather
than walking every preparation page and querying external events per row. The
sum is the **approved preparation amount**, not invoiced, paid, collected, or
statutory revenue. Rejected, cancelled, submitted, and draft preparations do
not contribute. A correction is an incremental signed delta: the reconciled
predecessor remains in the sum and the correction changes the net amount only
when approved. It is not a replacement gross claim. There is no second
commercial aggregate or compatibility path. The existing Billing Reader's
bounded count/page/filter/sort contract (default 50, cap 200, ID tie-breaker)
is unchanged. The characterization test grows from 4 to 124 preparations and
observes the same 13 SQL statements for the full projection; no N+1 external-
event or high-cardinality preload remains. No new index or migration is needed.

`RECONCILED` no longer manufactures a paid amount, and an invoice reference
no longer manufactures an invoiced amount. Those false DTO/presenter fields
were removed. `delivery_pending` remains a **local handoff request**; the
Accounting Status serializer labels it "Local handoff requested" and separately
marks whether a persisted external event exists. No production publisher or
payment/invoice outcome source exists. Neutral future R6G contracts remain.

The desktop request resolves `as_of_date` once and passes it to the canonical
Finance EAC/cost-policy composition and the fixed-price profitability
calculation. Fixed-price projected commercial revenue remains the PM-entered
contract value, projected margin is revenue minus canonical EAC, and margin
percentage requires a nonzero revenue denominator. T&M and cost-plus remain
unavailable without forecast billable-volume and recoverable-cost authorities;
EV is not substituted for revenue. Decimal zero revenue, margin, and margin
percentage now serialize/render as zero instead of "Restricted or unavailable";
missing, not-configured, and restricted remain distinct. Currency stays the
project financial currency; no FX or float authority was added.

Security classification: `finance.read` plus project scope permits customer
Party identity, entered contract/PO/customer references, contract value,
payment terms, and contractual cost-plus markup as ordinary managerial Billing
terms. `finance.read_profitability` gates projected revenue/EAC-derived margin
detail. `finance.read_sensitive` gates resource-identified preparation line
rate/source/card provenance, now redacted server-side before desktop
serialization; the UI is not the security boundary. Historical approved lines
continue to use snapshotted `RateType.BILLING` evidence, never current COST or
`Resource.hourly_rate`. Tenant/org/project filters apply to the aggregate and
every Billing Reader query. A future broader sharing model should reassess
contract-term classification before access is widened.

Commercial invalidation remains typed and project-scoped. Billing Profile,
Schedule, Preparation, and External Event events target `billing_commercial`;
ProjectFinancialProfile changes now do too because billing method/currency
affect the projection. Actual Cost and approved Forecast/EAC changes already
invalidate Commercial through their typed targets. BILLING Rate and approved
Time/correction changes affect **future preparation valuation**, not an
already approved immutable line or the present fixed-price contract-value
projection, so they do not trigger an additional Commercial refresh now. A
future live draft-valuation read must add those dependencies when introduced.
Customer/contract changes currently occur through Billing Profile creation,
which already emits the Billing invalidation. Same-commit coalescing and
operation-identity (not correlation-ID) behavior are unchanged; no global
Finance refresh was introduced.

Setup UX map for R6F-C: desktop commands already exist for creating and
activating a Billing Profile, adding a schedule line, and marking it ready,
with Finance manage checks and optimistic version on activation/readiness.
Commercial QML remains read-only and exposes none of these setup commands or
the existing preparation commands. R6F-C must design governed setup and
preparation mutation together, including source editing, creator/decider SoD,
correction semantics, and permission-aware controls; it must not add an
Accounting publisher. No Billing Preparation mutation UI was added in R6F-B.

Verification: focused profitability (16), Billing Reader (30), Billing
commands (25), invalidation/architecture (3), R6E/R6D (44), and R6C (27)
tests passed. A final architecture/profitability batch passed 28 tests.
Targeted Ruff F/I, Python compilation, Commercial-section QML lint, and
`git diff --check` passed. The broad Ruff rule set still reports pre-existing
style findings in touched large files; F/I correctness/import checks are clean.
No visible QML file changed, so viewport screenshots were not required.
R6D and R6E remain closed; R6F-C has not started. No Accounting, AR, GL,
tax, payment, invoice issuance, FX, or unrelated module was implemented.
No commit created.

## R6F-A Commercial Authority and Model Characterization (2026-09-14)

**R6F-A COMPLETE; characterization only.** R6D/R6E remain closed. PM Finance
owns managerial commercial setup, billable evidence selection, preparation,
approval, and projections. External Accounting alone owns legal invoices and
numbers, tax, GL, AR, payment, and statutory revenue. The neutral boundary is
`gateway/billing/accounting_billing.py` (`ProjectBillingPreparationPayload`
and `ProjectBillingPreparationPublisher`), not an Accounting module import.
No publisher implementation or issued-invoice workflow was found. R6G owns
durable outbound handoff and external outcome ingestion; R6F must not treat a
local delivery request as an accepted invoice. No FX or migration was added.

### Current Commercial path and visible truth

`FinancialsDetailPanel.qml` exposes **Billing Preparation**, **Projected
Profitability**, and **Accounting Status** under Finance/Commercial. The first
uses `FinancialsBillingPreparationSection.qml`, the second
`FinancialsCommercialProjectionSection.qml`; Accounting Status is an inline
panel with the same preparation collection and an external-ownership notice.
`FinancialsWorkspacePage.qml` binds the shared controller. The controller's
`financials_refresh_mixin.py` requests only the active destination/subsection;
`presenters/financials/destination_builder.py` builds the corresponding view.
`ProjectManagementFinancialsDesktopApi` serializes `FinanceWorkspaceQuery` and
`SqlAlchemyFinanceBillingReader` facts. The billing Reader returns immutable
profile, schedule, preparation, detail, line, and latest external-status
projections; all queries take tenant, organization, and project IDs. SQL-side
search/filter/sort/count/paging uses a default page size of 50, a maximum of
200, and an ID tie-breaker. No ORM object reaches QML. Empty states are real
empty query results, not fabricated Accounting outcomes. Current Billing and
Accounting sections are **read-only UI despite existing desktop write APIs**;
the projection is real for eligible fixed-price projects, explicitly
unavailable for other methods, and not a statutory revenue figure. Accounting
Status can be empty because no production external-outcome adapter exists;
it is a read surface, not proof that Accounting is operational.

### Source authorities and evidence

`ProjectFinancialProfile` owns project billability, method, and the single
project financial currency. Methods are `non_billable`, `time_and_materials`,
`fixed_price`, and `cost_plus`; no retainer/periodic engine exists.
`ProjectBillingProfile` is one per scoped project and stores a customer Party
ID, contract and optional external customer/PO references, contract value,
markup, payment terms, and currency. Activation requires a customer and
positive contract value, and checks currency against the financial profile.
There is no canonical contract aggregate or customer-contract FK in the
billing table; references are project-level text/Party IDs, not verified
contract truth. The schedule is a PM billing schedule line with amount, due
date, optional Task ID, and acceptance reference. `mark_schedule_line_ready`
is a Finance action, not automatic proof of Task completion or customer
acceptance. Fixed-price preparation selects only a ready schedule line.

Rate Cards distinguish `RateType.COST` from `RateType.BILLING`. Approved-Time
preparation resolves **BILLING** at the work date, with project/customer/
contract/resource context, then stores line/card IDs and versions, modifier,
quantity, rate, currency, and net amount. Precedence is project resource plus
customer/contract, project resource, project role/skill/department, organization
resource, then organization role/skill/department; effective-date and active
line checks apply, and equal-specificity ties fail. There is no fallback to
`Resource.hourly_rate` or a COST rate. Missing BILLING rate fails preparation,
not silently zero. The immutable preparation line protects historical value
from later Rate edits; source revision/hash and source locks protect reuse.

Approved-Time source evidence comes from the immutable Finance labor posting
derived from approved Time, not direct mutable TimeEntry cost valuation. No
per-TimeEntry billable/non-billable or contract-chargeable classification was
found; project-level billability plus manual source selection is the current
limit. Cost-plus selects a positive posted `ProjectCostEntry` and applies the
profile markup; there is no recoverable-cost taxonomy or Procurement expense
pass-through contract. A ProjectCostEntry is cost truth, not itself an invoice.
No independent commercial milestone/deliverable acceptance aggregate exists;
schedule lines may reference a Task and acceptance text only. Contract value
is PM's entered managerial commercial term, not an external contract ledger.

### Lifecycle, security, and persistence

Billing profile states: draft, active, on_hold, closed. Schedule states:
planned, ready, billed, cancelled. Preparation states: draft, submitted,
approved, delivery_pending, delivered, acknowledged, reconciled, rejected,
cancelled. Draft can add method-matched sources, but no general edit/remove
line command was found. Submission requires a nonzero line set and creates a
Platform Approval request; approval/rejection use the registered fresh-session
participant. Platform Approval prevents the request submitter from deciding
their own request. It does not separately compare the original preparation
creator, so a stricter preparer-versus-approver SoD needs an explicit R6F-C
decision/test. Corrections can reference a reconciled same-project predecessor;
rejected preparations are not edited in place. Approved source locks become
finalized; correction/successor rules need UX and version characterization in
R6F-C. `request_delivery` builds an immutable payload and marks local
`delivery_pending`, but its desktop adapter discards the payload and does not
publish it. Delivered/acknowledged/reconciled require recorded external events,
for which only a service/test caller exists today. None means invoiced or paid.

Six PM billing tables exist: profiles, schedule lines, preparations,
preparation lines, source locks, and external events. Each carries direct
tenant/organization/project scope, composite scoped FKs and `rls_scope` marker;
amounts use canonical Decimal Numeric money/rate/quantity conventions.
Unique keys cover one profile per project, scoped preparation number and
idempotency key, source reservation, and external event idempotency.
Preparations/profile/schedule rows have optimistic versions; lines preserve
source and rate provenance. R6F-A adds no table, duplicate mutable revenue
truth, or migration. Finance reads require `finance.read` plus project scope;
writes use `finance.manage`; decisions use Platform `approval.decide` and its
self-decision guard. Margin/revenue projection detail requires
`finance.read_profitability`. Resource-identified Rate evidence requires
`finance.read_sensitive`; customer/contract terms are currently exposed under
`finance.read`, so R6F-B must explicitly review whether finer redaction is
needed before widening the UI. No direct Accounting repository/import or
vendor-specific coupling was found.

### Projection and defects

`ProjectProfitabilityCalculator` is the single current margin formula. For
fixed price, **Projected Commercial Revenue at Completion = contract value**;
with an available canonical Finance EAC, projected margin = contract value -
EAC and margin percent = margin / contract value * 100. Zero contract value
yields an unavailable ratio; absent approved Forecast/EAC leaves margin
unavailable, not zero. T&M remains unavailable because no forecast billable
volume/rate authority exists; cost-plus remains unavailable because no
recoverable-cost basis exists. EV is not revenue. `ReportingProfitabilityMixin`
uses the calculator, but walks all preparation pages and then external events
per preparation for billable/invoiced/paid-like totals; this is not a bounded
Commercial Reader. It uses current `date.today()` for cost-policy EAC rather
than an explicit commercial as-of query. The desktop serializer preserves
Decimal as strings; QML `Number()` in Billing is pagination-only. Monetary
business paths inspected contain no authoritative binary-float operation and
reject currency mismatch; no FX conversion is performed.

**P0:** No confirmed cross-scope leakage, statutory invoice mutation, or
mixed-currency aggregation in the characterized paths. The outward adapter is
absent, so live Accounting handoff must remain unavailable.

**P1:** `externally_paid_amount` currently treats a `RECONCILED` preparation
event as payment and `externally_invoiced_amount` uses the entire preparation
amount whenever any event has an invoice reference. Neither proves external
paid/invoiced amount; stop presenting these as authoritative until R6G
contracts provide amounts/statuses. The profitability projection's
all-preparation plus per-preparation-event loop is unbounded/N+1. Its `billable`
sum also needs a correction/successor double-count proof. The presenter uses
truthiness for projected revenue/margin/percent, rendering valid zero as
"Restricted or unavailable". Local `delivery_pending` has no publisher and
must not imply handoff. Customer Party/contract reference validation, manual
milestone readiness, per-entry billability, and cost-plus recoverability need
explicit authority before broad commercial claims. Creator-versus-decider SoD
is weaker than submitter-versus-decider SoD.

**P2:** Billing is read-only in QML despite live commands; profile hold/close
and draft line revision are not surfaced. Accounting Status reuses a generic
preparation list rather than a dedicated external-evidence explanation. The
current Billing Reader is bounded, but representative statement-count and
high-cardinality proofs should accompany R6F-B. Commercial invalidation is
typed and coalesces Billing Profile/Schedule/Preparation/External events into
one project-scoped `billing_commercial` target. R6F-B must reconcile missing
dependencies from financial profile, approved Time/correction, BILLING Rate,
cost/Forecast/EAC, and customer/contract changes without a global refresh.

### R6F execution sequence and boundary

1. **R6F-B - Commercial read truth and setup:** remove false paid/invoiced
   projections and zero/unavailable presentation defects; make Commercial
   reads bounded, scoped, as-of explicit, and permission-redacted. Characterize
   customer/contract identity and profile/schedule command UX against existing
   aggregates; prove typed invalidation and query bounds.
2. **R6F-C - Governed Billing Preparation:** harden draft revision, source
   billability/recoverability evidence, rate provenance, immutable approval,
   source locks, correction/successor rules, SoD, and read/write UX. Do not
   publish to Accounting. Any missing product authority remains unavailable.
3. **R6F-D - Projected Commercial Revenue and Profitability:** keep fixed-price
   contract-value projection and canonical EAC; add T&M or cost-plus forecast
   only after an explicit billable-volume/recoverable-cost authority decision.
   Preserve Decimal, currency, availability, and non-statutory labels.
4. **R6F-E - Integrated security, performance, cleanup, closure:** cross-source
   lifecycle, tenant/org/project, RLS, SoD, rate independence, export/report,
   QML, and scale regression; delete superseded paths. R6G alone may implement
   durable Accounting delivery, external acknowledgement/reconciliation, and
   true invoice/payment evidence. Do not conflate R6F approval with issuance.

Characterization verification: focused Billing, profitability, and Finance
destination tests **61 passed**. Existing R6E and R6D closure evidence is
unchanged. R6F-B has not begun; no production source, migration, or Accounting
adapter was changed by this audit. No commit was created.

Current checkpoint: R6D-G final regression and repository reconciliation are complete. The
R6D-D Approved-Time Labor Posting Hardening path is complete. The
authoritative path is Time approval -> immutable Time financial outbox -> leased
delivery -> Finance inbox -> fresh Finance worker UoW -> canonical cost-rate
resolution -> immutable labor posting and posted `ProjectCostEntry` -> one commit
-> typed post-commit invalidation -> eventual Time outbox acknowledgement. New
postings preserve complete rate-selection and service-principal evidence;
historical rows are marked truthfully incomplete and are never revalued. Exact
replay is idempotent, corrections reverse and replace rather than overwrite,
failures are durable, and the project-scoped `Posting Failures` subsection offers
bounded read-only diagnosis with `finance.read_sensitive` redaction. PostgreSQL
evidence runs through the `app_runtime` role with `NOSUPERUSER` and `NOBYPASSRLS`.

The R6D-D ownership boundary is explicit: Time owns approved work facts and PM
Finance owns their managerial project-cost valuation. PM Finance does not create
general-ledger entries, journals, payables, payroll, official invoices, or other
Accounting truth. Future Accounting integration remains an outward gateway under
[ADR-PF-010](../architecture_decisions/ADR-PF-010-billing-and-accounting-boundary.md);
the approved-time worker does not invoke or emulate that future module.

### R6D-G Final closure checkpoint (2026-09-13)

R6D-G is **complete; R6D CLOSED**. Commit `9e392e48a913de9f74f31d43f9359ab88cd2c861`
(`update rate card`, Ashu, 2026-09-12 23:14:53 +02:00, parent
`07227df5d11bfc3132826aaba40e2f0d7d51291f`) contains R6D Rate/Actual/
Commitment and invalidation work. Git proves the commit metadata and contents,
not which external process created it. Preserve it; no history rewrite. The
working tree was clean at the start of G. Later external commits `e32a05458`
and `5b7ff2900` captured this run's Finance invalidation, Finance UoW,
test-fixture, and checkpoint work. This agent created no commit.

### R6E-A EVM, Variance and Cost Phasing authority characterization (2026-09-13)

R6E-A is **complete**. This was a read-only, characterization-first audit: no
production implementation changed, no earlier Finance phase was reopened, and
no commit was created. R6E-B must replace the current EVM authority rather
than retain it as a compatibility path. Project Finance remains a managerial
project-cost consumer; it does not create Accounting, payroll, AP, AR, cash,
or statutory truth.

#### Authority map

| Concept | Current evidence | R6E decision |
| --- | --- | --- |
| BAC | `EarnedValueCalculator` sums `BaselineTask.baseline_planned_cost`. | Retain an approved, cost-loaded baseline as EVM BAC; reject incomplete/non-cost-loaded baseline input rather than duration-allocating a different budget. |
| PV | The calculator interpolates baseline task start/finish dates by injected enterprise-calendar working days. | Retain calendar semantics, make the calendar/baseline basis explicit in Decimal facts, and report unavailable when required facts are absent. |
| EV | Cost-loaded baseline task cost times current `TaskFact.percent_complete`. | Retain task-progress ownership; convert progress to Decimal at the reader boundary and declare the method in result metadata. |
| AC | `SqlAlchemyFinanceSnapshotReader` reads posted/reversed `ProjectCostEntry`; `CostPolicyEngine` totals that immutable ledger. | This is the sole AC authority. Never revalue posted labor from a current rate. |
| ETC/EAC | Approved Forecast ETC; `EAC = AC + ETC`; no CPI extrapolation. | Retain governed Forecast authority and typed unavailable state if no approved Forecast exists. |
| CV/SV/CPI/SPI/VAC/TCPI | Current calculator computes CPI/SPI/VAC/TCPI, while the Performance query publishes `cv=None` and `sv=None`. | Publish Decimal CV (`EV - AC`) and SV (`EV - PV`) with typed denominator/unavailable behavior. Keep both TCPI variants distinct. |
| Control variance | `FinanceControlFact.VAC` is approved Budget minus EAC, not baseline BAC minus EAC. | Rename it to a control/forecast variance or budget headroom. It must not share EVM `VAC` code/label. |
| Cost Phasing | `SqlAlchemyFinancePerformanceReader` is the scoped Decimal desktop reader; `FinanceService` separately builds snapshot-ledger phasing for reporting/export. | Migrate reporting/export to one explicit bounded Decimal phasing contract, then delete the old snapshot-ledger builder/service surface. |

#### Confirmed defects and risk priority

1. **P0 - binary-float authority.** `EarnedValueCalculator`,
   `EarnedValueMetrics`, `EvmSeriesPoint`, `DashboardEVM`, and
   `PerformanceEvmFact` use floats for Money/ratios. The desktop serializer's
   `Decimal(str(value))` formats but cannot recover precision. R6E-B/C must
   introduce one scoped Decimal EVM fact/result and remove all float consumers.
2. **P0 - reachable undefined fallback.** `evm_calculator.py` references an
   undefined `project` variable in its duration fallback. The Performance query
   contains it as `calculator_error`, so QML does not crash, but valid edge
   data can lose EVM. Delete this fallback; do not turn it into another BAC
   authority.
3. **P0 - baseline lifecycle bypass.** `evm_baseline_statement` scopes tenant,
   organization, and project but selects the newest baseline regardless of
   status; an explicit ID is also unrestricted. The domain supports draft,
   submitted, approved, rejected, and superseded. R6E-B must require an
   approved baseline, with an intentional approved/superseded historical
   as-of policy.
4. **P0 - AC is incorrectly gated by current rate setup.**
   `ReportingEvmCoreMixin` rejects EVM for unresolved `LaborCostEngine` rates,
   even though the policy obtains AC from posted/reversed cost entries. Valid
   historical actuals can therefore disappear after a rate-card change. Remove
   `LaborCostEngine` from EVM/EVM-series composition; retain it only for a
   separately justified, explicitly labeled analytical consumer.
5. **P1 - unavailable series becomes zero.** `EarnedValueSeriesCalculator`
   coerces missing values with `or 0.0`; charts/tone can then display an
   unavailable value as real zero. It also accepts `freq` but always returns
   monthly points. R6E-C must preserve nullability and make frequency real or
   remove it.
6. **P1 - variance taxonomy is misleading.** The Variance destination calls
   approved-Budget-minus-EAC `VAC`, while EVM calls baseline-BAC-minus-EAC
   `VAC`; EVM CV/SV are not published. Baseline movement records are correctly
   distinct plan-to-plan history and must remain separate.
7. **P1 - Cost Phasing is bounded but not truthful planned-time phasing.**
   Actuals use posted/reversed entries by posting date; commitments use open
   exposure; forecasts use approved facts. Planned cost selects one latest
   snapshot and anchors every row to its snapshot date; unperiodized Forecast
   rows land at forecast as-of. R6E-D must introduce authoritative allocation
   facts or label these as point-in-time snapshots, never distributed cash flow.
8. **P2 - scale is unproven.** Cost Phasing caps requests at 36 months but
   buckets materialized facts in Python. EVM materializes project facts and
   repeats policy/calculation per month. Preloaded calendar dates avoid repeat
   reads, but per-task counting remains linear. R6E-E needs bounded SQL,
   EXPLAIN/index evidence, statement budgets, and 10k/50k fixtures.

#### Scope, currency, calendar, and unavailable invariants

Current Performance and Reporting reads carry tenant, organization, and
project scope and require Finance/project permissions. Readers fail closed on
project-currency mismatch; Portfolio does not roll project EVM across
currencies. R6E preserves: no cross-project/cross-currency EVM total, no
implicit FX, no raw error to QML, and no conversion of unavailable into zero.
The injected enterprise calendar remains the working-day authority. R6E-B
must characterize non-working days, zero/missing durations, as-of boundaries,
reversals, no Forecast, and scope isolation.

#### Consumer and deletion map

| Consumer/path | Current role | Required R6E action |
| --- | --- | --- |
| `ReportingService.get_earned_value` and `DashboardEvmMixin` | Project-scoped EVM authority/dashboard adapter. | Move to Decimal authority in R6E-C; retain project-only dashboard scope. |
| `EarnedValueSeriesCalculator`, dashboard charts, PDF/XLSX renderers | Trend/export consumers. | Migrate to nullable Decimal series; convert only at chart/PDF/XLSX presentation edges. |
| Performance query, desktop serializer, presenter, Finance QML | Desktop Performance surface. | Migrate contracts/labels in R6E-C/D; keep QML display-only. |
| `SqlAlchemyFinancePerformanceReader` | Active Decimal Cost Phasing reader. | Evolve in R6E-D as the sole Performance phasing reader. |
| `FinanceService.get_finance_snapshot` and `build_period_cost_phasing` | Separate snapshot/export phasing, still used by reporting/export infrastructure. | Migrate every reporting/export caller in R6E-D, then delete builder, obsolete snapshot phasing members, DI, and retired-behavior tests. Do not delete before migration. |
| `LaborCostEngine` in `_compose_evm_policy` | Incorrect current-rate gate on posted-ledger AC. | Remove from EVM/EVM-series in R6E-B/C. Retain only independently justified consumers. |
| Float EVM models and `binary_float_*` labels | Temporary legacy authority markers. | Delete after Decimal parity and consumer cutover. No pre-release compatibility facade remains. |

#### R6E delivery sequence and exit gates

**R6E-B - Decimal EVM authority:** add immutable scoped Decimal input/result
facts with lifecycle, currency, calendar, progress, and reason metadata.
Replace float arithmetic and the duration fallback with cost-loaded-baseline
validation. Use only posted/reversed AC and approved Forecast ETC. Test
BAC/PV/EV/AC/CV/SV/CPI/SPI/ETC/EAC/VAC/TCPI, zero denominators, calendar edge
cases, reversal, no Forecast/baseline, tenant/org isolation.

**R6E-C - consumer cutover/float retirement:** migrate Reporting, dashboard,
desktop API/serializer, QML presenter, trend/export to Decimal facts and
preserved unavailable values. Delete `EarnedValueCalculator`, float EVM models,
and the EVM `LaborCostEngine` gate only after all active consumers are green.

**R6E-D - variance/Cost Phasing truth:** separate EVM CV/SV/VAC, approved-Budget
control variance, and baseline-history variance in contracts and UI. Define
truthful planned/forecast allocation, move reporting/export off snapshot
phasing, then delete `build_period_cost_phasing` and superseded snapshot API.
Continue excluding receipts, payments, liquidity, AR, AP, and Accounting.

**R6E-E - performance/final closure:** prove RLS negative cases through
`app_runtime`, Decimal/currency guards, deterministic series ordering, bounded
SQL/materialization, EXPLAIN plans, and 10k/50k performance. Run targeted
domain, reader, desktop, dashboard, exporter, QML, SQLite, and PostgreSQL
tests. Delete every temporary adapter/dead test in the same cutover. Close
only with one EVM authority, one Performance read path, one desktop path, and
no float/legacy compatibility surface.

R6E-A evidence is source/contract inspection plus the existing R6D closure
evidence; no executable behavior changed, so no new test was necessary.
`ruff 0.16.7` is available in `pmenv`. Its isolated `E4,E7,E9,F` audit of the
current EVM/Performance files intentionally fails with six `F821` occurrences
of the documented undefined `project` fallback and one `F841` unused exception
binding in the containment path. R6E-B must remove those defects as part of the
authoritative replacement and run the same correctness rules on every changed
Python file.

### R6E-B Canonical Decimal EVM authority closure (2026-09-13)

R6E-B is **complete**. R6D remains closed. One new pure calculation authority,
`CanonicalEarnedValueCalculator`, consumes immutable `EvmCalculationInput`
facts and returns immutable Decimal `EarnedValueMetrics`; no ORM, repository,
desktop, QML, Rate Card, or Time revaluation is reachable from the formula
layer. The explicit as-of date is part of the input and all money and ratios
remain Decimal until a chart or document renderer crosses its presentation
boundary.

- **Formula/source contract:** BAC is the sum of approved cost-loaded baseline
  task cost; PV is enterprise-calendar working-day interpolation of those
  baseline dates; EV is that same baseline cost weighted by current task
  progress; AC is only scoped posted/reversed `ProjectCostEntry` total;
  ETC is only approved Forecast ETC; EAC is `AC + ETC`; EVM VAC is
  `BAC - EAC`; CV is `EV - AC`; SV is `EV - PV`; CPI, SPI, TCPI(BAC), and
  TCPI(EAC) are Decimal ratios. No CPI/Rate/current-plan fallback was added.
- **Availability:** no approved baseline, an empty/uncosted baseline, incomplete
  baseline dates, or missing current progress returns structured unavailable
  facts, never fabricated zero. A missing approved Forecast leaves BAC/PV/EV/AC
  available but makes ETC/EAC/VAC/TCPI(EAC) unavailable. Zero AC/PV yields a
  null CPI/SPI respectively; zero remains distinct from unavailable.
- **Lifecycle/security/currency:** `evm_baseline_statement` now scopes tenant,
  organization, and project and only admits `approved` baselines, both implicit
  and explicit. Draft/rejected/superseded baselines cannot silently become the
  current EVM basis. Project-currency fail-closed reader behavior and existing
  Finance/project authorization remain unchanged; no FX, EVM persistence, or
  sensitive Rate evidence was introduced.
- **Actual safety:** EVM now reads `FinanceControlFact.posted_actual` directly.
  The prior `LaborCostEngine`/current-Rate dependency and
  `ACTUAL_COST_INCOMPLETE` gate are removed from EVM snapshots and series.
  Manual, approved-Time, Procurement-supported, and signed reversal Actuals
  contribute only through their already-posted `ProjectCostEntry` facts.
  `Resource.hourly_rate` is not read by the new authority.
- **Consumer/deletion cutover:** Reporting, Dashboard, Performance query,
  desktop serializer/DTOs, EVM series, chart/export edges, and tests now use
  Decimal facts. Deleted
  `application/financials/earned_value/evm_calculator.py`; no adapter, old/new
  routing, undefined `project` branch, binary-float EVM DTO field, old float
  serializer helper, or compatibility calculator remains. Finance snapshot
  Cost Phasing is intentionally untouched for R6E-D.
- **Performance:** one draft-baseline EVM snapshot is characterized at at most
  **10 SQL statements**, including the entitlement guard, with one scoped EVM
  fact read and no per-task/Rate query loop. No index was added. Series keeps a
  single scoped fact read and the existing calendar bulk-day capability, without
  Rate/policy recomposition.

R6E-B evidence: 51 architecture/Decimal/R6B Performance tests, 13 EVM/export
tests, 15 business-rule tests, and 14 R6C Forecast/R6D Actual governance tests
passed in focused runs. Targeted `ruff --select E4,E7,E9,F` is clean for every
changed Python file; compilation and `git diff --check` are clean. No QML file
changed, so no QML lint was required. The full PM/PostgreSQL suite was not run
because this phase used targeted evidence only. R6E-C (consumer/display
refinement), R6F-R6H, Cost Phasing redesign, Billing, Accounting, FX, and
Procurement correction semantics are **not started**. No commit was made.

### R6E-C Variance taxonomy and analytical read migration closure (2026-09-13)

R6E-C is **complete**. R6E-B remains closed and its canonical Decimal EVM
authority was not redesigned. The Performance Variance subsection consumes that
authority once for the same explicit project/as-of date and combines it only
with the authoritative approved-Budget projection needed for Budget Pressure.
The subsection, desktop serializer, presenter, and QML remain read-only; QML
has no financial formula or sign interpretation.

- **Canonical taxonomy:** CV is `EV - AC`, SV is `EV - PV` (a monetary EVM
  value variance, never schedule days), and VAC is `BAC - EAC`. All three are
  canonical EVM results. Budget Pressure is separately `EAC - Approved Budget`.
  Its inverse sign convention is explicit: positive is unfavorable pressure,
  zero is on target, and negative is favorable headroom. Period Actual versus
  Planned remains unavailable by design until R6E-D bounded Cost Phasing; no
  unbounded or guessed period value was introduced. The Dashboard's former
  generic `Forecast Var.` label now identifies `EVM VAC` precisely.
- **Control rename and deletion:** the former control/overview field named
  `variance_at_completion` was approved-Budget minus EAC, not EVM VAC. It is
  now `budget_headroom` through immutable facts, cost-policy, overview DTO,
  Finance snapshot, presenter, and finance export projection. No compatibility
  alias remains. Baseline plan-to-plan records retain their distinct
  schedule/planned-cost movement semantics and remain visibly separate from
  EVM SV/CV/VAC.
- **Contract and availability:** immutable `PerformanceVarianceMetricFact` now
  carries server-authored favorability, a concise semantic tooltip, Decimal
  value, currency, source revision, availability, and unavailable reason.
  Missing baseline/forecast facts propagate canonical unavailable states; a
  missing approved Budget makes only Budget Pressure unavailable. Neither null
  nor unavailable becomes zero.
- **Scope/money/performance:** Finance/project permissions, explicit
  tenant/organization/project scope, project currency, and the canonical
  as-of date are preserved. A live eight-task Variance request is bounded at 17
  statements, including entitlement/context checks and one canonical EVM
  assembly, with no per-task/cost-entry loop; no index was needed.
- **Consumer audit:** Finance Performance is the active Variance destination.
  Reporting/export baseline history remains a distinct schedule comparison; no
  report or export independently computes CV/SV/VAC/Budget Pressure. Existing
  EVM chart/export consumers continue to use canonical EVM facts and cross a
  float boundary only in presentation.

R6E-C focused evidence: 7 taxonomy/availability/Decimal/desktop-tone tests, 28
Performance reader/QML viewport tests, 30 Finance destination-query tests, 6
immutable Finance-read contract tests, and 35 architecture/Forecast/Actual
governance regressions passed. Targeted Ruff, compilation, QML lint, and `git
diff --check` passed. R6E-D Cost Phasing,
R6F-R6H, Billing, Accounting, FX, and Procurement correction semantics remain
**not started**. No commit was made.

### R6E-D Cost Phasing implementation checkpoint (2026-09-13)

R6E-D is **in progress, not closed**. The Performance Cost Phasing contract now
carries immutable per-series availability facts. Its scoped reader has begun the
authoritative source cutover: planned cost uses only an approved cost-loaded
baseline and the shared enterprise calendar; Actual uses posted/reversed cost
entries by posting date; Forecast uses only approved lines with complete
same-period timing evidence; and open Commitment uses only its remaining amount
at `expected_delivery_date`. Missing or cross-period Forecast timing and missing
Commitment timing are marked `partially_unphased`, never fabricated. These
series are distinct and non-additive; Cost Phasing remains explicitly separate
from cash flow, Billing, Accounting, and FX.

The snapshot, desktop, and export-backed snapshot paths now consume the one
canonical reader; `build_period_cost_phasing` and its package export were
deleted with no source references or compatibility wrapper. Forecast and
Commitment availability carries exact phased and unphased Decimal totals all
the way through the desktop and export metadata contracts. Actual Cost Phasing
is now grouped by posting month in SQL with currency reconciliation performed
in that same bounded query; application code only rolls those source groups
into the requested display grain.

Remaining R6E-D closure work is reconciliation/source-lifecycle evidence,
representative PostgreSQL query-plan characterization, and the full focused
matrix. R6E-E, R6F-R6H, Billing, Accounting, FX, and Procurement correction
semantics are not started. No commit was made.

### R6E-D final aggregation checkpoint (2026-09-13)

Forecast and Commitment now also use bounded SQL monthly aggregation. A Cost
Phasing request treats `as_of_date` as the authoritative information cutoff and
`date_from`/`date_to` as the display window. Consequently a Commitment known at
the cutoff may phase into a later expected-delivery month when that month is in
the window. Facts outside the window are not shifted into a visible bucket;
missing delivery timing remains explicitly unphased. The normal request
executes eight fixed statements: project/forecast/baseline authority plus
Actual, phaseable and unphased Forecast, and phaseable and unphased Commitment
aggregates. This count does
not grow with Cost Entry, Forecast Line, Commitment Line, or period counts.

The remaining R6E-D blockers are PostgreSQL EXPLAIN/reconciliation evidence and
the final lifecycle/range/consumer focused matrix. R6E-E remains not started.

### R6E-D PostgreSQL aggregate evidence (2026-09-13)

The existing dedicated PostgreSQL integration environment was executed through
the `app_runtime` role with RLS context. The final production Actual, Forecast,
and Commitment aggregate statement builders were each inspected with `EXPLAIN
(ANALYZE, BUFFERS, FORMAT JSON)`: all produced aggregate plan roots on the
representative fixture, with execution times of 0.085 ms, 0.108 ms, and 0.088
ms respectively. The fixture is intentionally small, so its plan does not
demonstrate an index deficiency; **no index change is required**. The reader
has a fixed eight-statement shape and no source-row N+1 path.

R6E-D focused lifecycle and regression evidence is green in completed batches:
14 Commitment/Actual lifecycle and partial-match tests, 19 Forecast and
canonical snapshot/export tests, and 75 Performance-reader, Rate-governance,
and Finance authorization tests (108 total). These cover posted and reversed
Actuals, commitment remaining-amount semantics, Forecast approval/supersession,
snapshot/export lineage, tenant scope, and rate governance. No R6E-D-owned
report consumer exists beyond snapshot-backed PDF/Excel rendering.

### R6E-D closure evidence (2026-09-13)

**R6E-D COMPLETE.** The preceding in-progress entries are historical checkpoints,
not the current gate status. The canonical scoped Reader is the sole Cost Phasing
calculation authority; snapshot and Excel/PDF export consume its monthly facts.
No independent R6E-D report calculation exists. The retired
`build_period_cost_phasing` authority has no production references.

Lifecycle and boundary characterization covers approved-only cost-loaded
baselines with exact enterprise-calendar allocation across December/January;
posted and reversed Actuals, excluding draft/submitted/approved-but-unposted
entries; approved Forecast selection including a subsequently superseded
historical version; and open, matched, closed, and cancelled Commitments.
Display range and `as_of_date` are separate: future delivery can phase in a
future bucket if known by the cutoff, Actual after the cutoff is excluded,
outside-window facts are not shifted, and missing timing remains unphased.
First/last month days, a mid-month range, and the year boundary are exercised.

Exact `Decimal` assertions reconcile planned calendar allocation, Actual
monthly facts (26.70 total in the boundary fixture), a 25/-25 reversal,
Forecast phased/unphased 80.10 + 0.50 = 80.60, and Commitment phased/unphased
100 + 100 = 200. A 100 Commitment partially matched by a 30 posted Actual
leaves 70 open; combined exposure is 100, not 130. Changing/deactivating
the current Rate Card after posting does not change historical Actual phasing.
For the same project, as-of, and monthly window, canonical Reader facts agree
with snapshot rows and Excel period rows; PDF uses the same snapshot basis.

Focused verification: 37 canonical/read-architecture, 28
commitment/cost/Forecast lifecycle, 58 Decimal EVM/variance/Rate/security,
25 R6C/R6D governance, 35 destination/dashboard, 3 live PostgreSQL RLS,
and 21 finance architecture-guard tests passed (207 non-overlapping tests).
Targeted Ruff and Python compilation passed. PostgreSQL aggregate EXPLAIN,
bounded query count, and index analysis are recorded above. R6E-E was not
started at this checkpoint; no commit was made in this work session.

### R6E-E integrated hardening and final R6E closure (2026-09-14)

**R6E-E COMPLETE; R6E CLOSED.** The final authorities are the governed approved
cost-loaded baseline for BAC/PV/EV and planned phasing, posted/reversed
`ProjectCostEntry` for AC, approved Forecast for ETC, R6D Commitment projection
for open Commitment, and Scheduling/calendar for working-time facts. The
canonical Decimal EVM calculator owns EVM formulas; Variance delegates to its
facts (CV = EV - AC, SV = EV - PV, VAC = BAC - EAC); the scoped Finance
Performance Reader owns Cost Phasing. Budget Pressure is EAC minus approved
Budget; Budget Headroom is its inverse. Commitment is not added blindly to
Forecast ETC, and Receipt-derived Actual reduces matched open Commitment.

An integrated approved-baseline project now proves matching Performance,
Variance, Cost Phasing, snapshot, and reporting EVM for the same project and
as-of date. The scenario exposed and fixed a live Variance contract defect:
`BaselineService.list_variance_records` did not accept the caller's
`expected_project_id`. The service now verifies that project before returning
records; a wrong-project request raises `BASELINE_NOT_FOUND`. Dedicated R6D
and R6E-D tests provide complementary approved-Time posting, reversal,
partial-match, future/unphased Commitment, Forecast lifecycle, and export
parity evidence. Missing baseline/Forecast and zero-denominator ratios remain
structured unavailable rather than monetary zero; timed and unphased amounts
remain distinct. Money stays Decimal in project currency; ratios use canonical
Decimal/optional representation. No FX or analytical truth table was added.

Production consumer review: Performance and reporting call the canonical EVM
authority; Dashboard delegates to reporting; Variance consumes the canonical
EVM facts; snapshot and Excel/PDF export consume the canonical phasing Reader;
QML and presenters serialize/display rather than recalculate financial truth.
Subsection reads remain lazy, and existing generation/context guards and
committed-operation invalidation tests remain green. Static float search of
R6E-owned EVM/Variance/Reader/reporting paths found no authoritative binary
float usage; QML `Number()` hits are pagination/version or display concerns,
not monetary authority. The old EVM calculator and old phasing builder are
absent; no R6E-owned compatibility calculator remains. No R6E schema migration
or duplicate persisted current-EVM fields were introduced.

Final verification: complete Project Management suite **1,621 passed, 2
skipped**; 42 impacted baseline/canonical/read tests passed after the service
fix; 39 finance/CQRS architecture guards passed; 65 Finance presenter,
controller, and platform-approval tests passed; 17 scheduling/approval/SQLite
integration tests passed; 8 live PostgreSQL approved-Time/RLS tests passed.
Finance QML lint passed with repository import paths; five standard viewport
sizes are covered by the Performance-section tests in the full PM suite.
Targeted Ruff, Python compilation, retired-path search, and `git diff --check`
passed. R6D remains closed. R6F Billing Preparation / Projected Commercial
Revenue / Profitability is next but not started; Billing, Accounting, FX, and
Procurement correction semantics were not expanded. No commit was created.

The R6D authority map remains: Rate Card/Line and the canonical resolver for
Finance rates; `ProjectCostEntry` for managerial Actual; Time for worked/approved
hours; Procurement for PO and receipt source truth; Finance Commitment/Match
as a projection; Accounting remains a future outward boundary. The old
`cost_entries_changed` signal and interactive Commitment mutations are absent.
`Resource.hourly_rate` remains resource/planning metadata and is not a Finance
posting fallback. The former float-based EVM authority was retired in R6E-B;
remaining LaborCost work is not a second EVM ledger authority. No future Procurement receipt
correction producer or Accounting functionality was invented; changed receipt
semantics unsupported by the neutral contract remain quarantinable/non-posting.

R6D-G corrected five remaining Finance invalidation handlers (Budget, Forecast,
Planned Cost, Financial Change, Billing) to coalesce by committed-operation
`DomainEventContext` identity, not trace correlation. One commit still coalesces
repeated targets; two commits sharing a trace each notify. Existing Rate,
Actual, Commitment, approved-Time, and setup handlers already used this rule.
No duplicate production read/write path or D-class superseded R6D code was
found in the focused legacy/DI/action search; legitimate `old_value` audit,
presentation fallback, Resource rate metadata, and R6E analytical code remain.

The full PM suite's first pass found an R6D-owned SQLite audit-atomicity defect:
a released SAVEPOINT could escape an outer session rollback without a physical
SQLite `BEGIN`. The Finance governance UoW now starts that outer transaction
on entry; the failed Manual Actual audit-rollback test passes without changing
the shared UoW. A stale Commitment desktop test double now accepts the authoritative
`exposure` query parameter. An older R6B live Financial Change seed now writes
the schema-required `updated_at`; this changed only the test fixture.

Final evidence: live R6D/R6B PostgreSQL selection **30 passed** after the
Finance UoW fix; fresh-schema
PostgreSQL security **14 passed**; live R6C/R6B readers **23 passed** after the
fixture repair; Finance invalidation **79 passed, 1 skipped**; Platform Approval,
shared QML, architecture, and SQLite migration guards **87 passed**; shared
UoW/platform transaction guards **56 passed** after the narrowed fix; direct Finance QML lint clean;
Python compilation clean. The first full PM run had **2245 passed, 2 skipped,
2 failed**; both failures were fixed. The final full PM suite passed **2247,
2 skipped**. Three lint-only test edits were then verified with **42 passed,
1 skipped**. `ruff 0.16.7` is available in `pmenv`: isolated correctness rules
`E4,E7,E9,F` pass on all changed Python files. Repository-default Ruff still
reports 54 pre-existing style findings in those files (39 verbose Decimal
constructors, 9 import-order, 4 `__all__` order, 2 unused unpacked values);
these are not new R6D behavior defects and were not mass-reformatted in G.

#### R6D-G closure inventory

- **Write and transaction owners:** interactive Rate and Manual Actual commands
  use the typed desktop API and `FinanceGovernanceCommandBoundary`; the fresh
  Finance UoW alone commits. Approved-Time and Procurement dispatchers own
  their respective source-outbox claim/ack transaction and fresh Finance worker
  UoW. Inner Rate, Actual, and Commitment services do not commit or roll back.
  Four retained R6D savepoints have local roles only: Commitment source-revision
  race, Commitment match race, Actual source-idempotency race, and immutable
  Actual reversal race. Audit, inbox completion, and financial facts share the
  Finance commit; typed view hints publish after it. No interactive Commitment
  mutation remains.
- **Events and diagnostics:** Rate, Actual, Commitment, Budget, Forecast,
  Planned Cost, Financial Change, Billing, approved-Time, and setup Finance
  invalidation handlers use operation-context identity for target coalescing,
  not a trace correlation as a commit key. Relevant event subscriptions have
  one producer/handler registration per type. `Posting Failures` remains a
  bounded, project-scoped, sensitive-permission-redacted, read-only
  **approved-Time** diagnostic, not a Procurement failure queue or replay
  shortcut. The retired `cost_entries_changed` signal is absent.
- **Database/security/read:** R6D migration lineage includes
  `e9f2a5b8c4d1` (Rate provenance), `f4b7c9d2e6a1` (approved-Time posting),
  and `b7d2e4f9a6c1` (Procurement Commitment). SQLite migration/ORM guard
  tests and fresh Alembic-to-head PostgreSQL runs pass. Live RLS evidence uses
  non-owner `app_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`) over all nine current
  R6D Finance tables, denies foreign-scope and forged-parent writes, and
  preserves legal same-scope command/worker paths. Rate, Actual, Commitment,
  and Posting Failures readers stay bounded; Actual and Posting Failures use
  one scoped count plus one limited page query. R6D-F representative plans
  justify no new index, and none was added here.
- **Authority and cleanup:** authoritative Rate/Actual/Commitment amounts use
  Decimal/Money/MonetaryRate, explicit currency, and immutable Rate selection
  evidence; no Resource-rate posting fallback or new FX subsystem was added.
  Historical posted Actual changes use reversal/replacement, not overwrite.
  The focused production legacy/DI/controller/QML search found zero
  superseded R6D read/write paths to delete. `old_value` audit fields,
  presentation fallbacks, operational Resource rates, and current float-based
  R6E analytical code have different active semantics and were retained.
  No source or documentation file was created or deleted in G.
- **Boundary and next phase:** R6D Commitment integration is closed **only for
  the current neutral Procurement contract**. Without an authoritative future
  receipt-correction/reversal linkage, changed receipt semantics remain
  rejected/quarantinable and non-posting. Finance does not manufacture PO,
  Accounting, journals, AP, payroll, invoice-issuance, or other statutory
  truth. Existing managerial Billing preparation was not expanded. R6C stays
  closed; R6E (EVM/Variance/Cost Phasing) is next and has not started.

### R6D-F Integrated Hardening checkpoint (2026-09-12)

R6D-F is **complete**. Its integrated evidence and exit gates are tracked in
[R6D-F integrated hardening](r6d_f_integrated_hardening.md).
One concrete defect was fixed: Rate, Actual, and Commitment post-commit
invalidation previously deduplicated on correlation ID. Independent worker
commits can share a trace correlation, so later committed facts could omit
view invalidation. Handlers now coalesce by the UoW-owned event-context
instance, retaining one target hint per commit while notifying again for a
separate commit with the same correlation. A real two-delivery Procurement
test covers this case. R6D-G is closed; R6E has not started.

### R6D-E Commitment Projection Hardening checkpoint (2026-09-12)

R6D-E is **closed for the currently defined neutral Procurement contract**. The
contract publishes one PO-line financial-state fact and one posted receipt-line
fact. It is not a whole-PO line-set snapshot. A second line is added by its own
stable source-line ID; a missing line in another event is not interpreted as a
deletion. Explicit `CLOSED`/`CANCELLED` state preserves historical rows while
releasing open exposure. The Procurement producer module does not yet exist in
this pre-release tree; these are contract/consumer tests, not a claim that a
live Procurement product emits the facts.

Implemented and verified for R6D-E:

- Procurement outbox delivery uses a fresh Finance UoW and Finance-owned inbox
  for each event. Projection, source revision, receipt-derived posted
  `ProjectCostEntry`, immutable match, audit, domain events, and inbox completion
  share one worker commit; source-outbox acknowledgement follows that commit.
  A typed event is registered once, by the dispatcher, not again by inner
  services. The worker uses a configured service principal and explicit
  source-event/correlation audit evidence, not a fabricated human actor.
- Interactive Finance `ingest_procurement_source`, `match_cost_entry`, and
  `reverse_match` commands and their unused Finance governance family were
  retired. Commitments remain read-only in Finance. Unused reversal callable
  helpers were removed; immutable evidence columns remain available for a
  future explicit correction contract, not as a second active write path.
- The source contract permits increasing line revisions with gaps. Same
  revision/same hash is a no-op; conflicting content and stale deliveries fail
  closed. Exact inbox replay and the post-Finance-commit/source-ack crash window
  do not create duplicate lines, revisions, Actuals, or matches. Receipt source
  identity now has a partial unique database index. Since there is no neutral
  receipt correction/reversal event, a changed revision for the same receipt
  identity is quarantined rather than overwriting posted Actual.
- `open_commitment_amount` is the shared Decimal authority for domain,
  forecast, snapshot, performance, and portfolio Python reads. Closed/cancelled
  rows contribute zero. A receipt Actual is kept separate from matched/open
  Commitment; partial, cumulative-full, and over-commitment receipt behavior
  is characterized. Over-receipt remains a full posted Actual while only the
  available Commitment is matched; no negative open balance is created.
- The existing paged, deterministically server-sorted read-only Commitments
  list now has a server-side open/no-open exposure filter. Changing the filter
  resets to page one; no page-local filtering or Finance-side PO/Commitment
  mutator was added. The list is the bounded read surface; no selected-detail
  preload, Accounting write, retired signal, or generic Finance refresh was
  introduced.
- PostgreSQL transaction-scoped locking serializes competing PO projections,
  so a newer line revision wins even if two workers receive N and N+1
  concurrently. Duplicate receipt workers produce one Actual and one Match;
  a closure/receipt race preserves both historical facts and zero open exposure.

Focused evidence: 22 commitment/delivery tests, 47 R6D-B/C/R6C plus delivery
tests, 21 approved-time R6D-D tests, 9 existing architecture/QML/migration
checks plus 2 new boundary guards, and
18 combined R6D-C/D/E live PostgreSQL tests and 5 Commitment-section
QML runtime width checks passed. The PostgreSQL tests use non-owner `app_runtime`
(`NOSUPERUSER`, `NOBYPASSRLS`), prove valid worker delivery and two-dispatcher
single-claim behavior, forced RLS, foreign-scope invisibility/DELETE no-op,
and direct foreign-scope UPDATE/INSERT denial on header, line, source revision,
match, Actual, and Finance inbox. A fault-injection test proves audit failure
rolls back financial facts and leaves a durable retry without success hints.
The changed Finance QML passes direct Qt `qmllint`; its checked-in controller
type metadata now declares the active Commitment exposure and Posting Failures
members. Representative seeded SQLite worker dispatches execute 32 SQL
statements for create, 30 for revise, 30 for close, 38 for receipt, 9 for stale
delivery, and 1 for published-event replay. These are characterization values,
not a production-volume performance claim; high-volume EXPLAIN/benchmarking
belongs to R6D-F.

Current-contract boundary: Procurement has no producer implementation in this
pre-release tree and publishes no neutral accepted-receipt correction/reversal
event. A changed receipt identity is durably quarantined, not silently applied
to posted Actual. Therefore reversal/replacement, Match correction, and a
correction race cannot be demonstrated for this source contract; they are
**not claimed as implemented** and must be designed with the future Procurement
correction contract before corrections can be enabled. This does not authorize
Finance to invent Procurement lifecycle or Accounting records. The existing
source event/line-set contract is per line, so absence from a different event
never deletes an existing line; explicit terminal state retains history.

R6D-F later completed integrated security/events/performance work on this
single production worker path without reviving interactive Commitment writes
or introducing a second Finance ledger.

The current desktop dispatcher resolves the principal and claims the source
outbox in the active organization. The fresh Finance UoW/RLS context is scoped
to that event, but this is **not** an autonomous all-tenant daemon. A future
multi-tenant worker host must explicitly enumerate/authorize scopes rather
than treating the desktop user's active organization as a global queue drain.

Historical checkpoint: Phase D is complete. Project snapshot, cash flow,
analytics, EVM, portfolio variance, desktop forecast, and commitment controls now consume approved
budget/current-or-historical-approved forecast versions, posted actuals/reversals, and open
commitments as Decimal Money. Excel and PDF now share one explicit as-of/currency/period/version
basis, full-snapshot reconciliation controls, bounded source drill-down, and sensitive-detail state.
The transient forecast formula service, misleading duplicate UI/export placeholder, empty Insights
component, and deprecated export wrapper are deleted. Forecast/ETC, Change Control, stored baseline
Variance, and Reports now expose canonical version basis and source drill-down without desktop
formulas. All registered Phase D float conversions and Float-backed PM money/rate/quantity columns
are retired. ADR-PF-010 and the Phase E product decisions were accepted on
2026-08-11. See [TODO/README.md](TODO/README.md) for
the concise execution checkpoint.

Historical implementation checkpoint: Task-owned WBS, effective-dated rate cards (ADR-PF-005) with the
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
Remaining Phase B scope: item 7's planning-report source decision remains blocked on the
documented envelope-versus-allocation product decision and a snapshot freshness mechanism.
Item 8's QML combined-Budget replacement is complete. Phase C item 1's organization financial-
period, actual-ledger, commitment, approved-Time, and Procurement financial-delivery foundations
are complete. Phase C item 6's canonical command cutover from combined `CostItem` is complete;
item 7 deterministic migration and reconciliation is next.

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
| Project financial settings | `ProjectFinancialProfile.currency_code`; approved `ProjectBudget` + `BudgetLine` total | Finance domain/ORM plus scoped CQRS readers | Profile owns currency; approved budget versions own authorization | Yes, direct tenant/org scope and scoped FKs | finance configuration, budget, CQRS, and portfolio tests | CANONICAL |
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
| Billing preparation/revenue | billing profile, schedule, source-lock, preparation, typed Accounting boundary, reconciliation evidence, and read-only QML are implemented; commercial revenue/profitability projection remains pending | `application/financials/invoicing/`; `contracts/accounting_billing.py`; `FinancialsBillingPreparationSection.qml`; `revenue/__init__.py` | PM prepares commercial evidence; Accounting owns statutory truth | `finance.read`; `finance.manage`; platform approval permissions | Direct tenant/org/project ownership plus forced RLS | PARTIAL - PHASE E |
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

**Status: IMPLEMENTED; clean cutover completed 2026-08-11.** `ProjectFinancialProfile` owns currency, financial lifecycle/dates, billable/funded state, billing method, budget-control mode, cost-code policy, and default cost-code reference with one profile per scoped Project and optimistic concurrency. New projects create the profile atomically from an explicit create-command currency or Organization base currency. Mutations require global and project-scoped finance permission and fail-closed Enterprise Audit. The former `Project.currency` projection and both synchronization paths are deleted; migration `u8v9w0x1y2z3` removes the database column. Catalog, finance, portfolio, project-resource, reporting, desktop, and QML consumers now use the profile authority directly.

### 11.2 Cost Codes

**Status: IMPLEMENTED.** PM-owned `ProjectCostCode` provides scoped unique identity, hierarchy/cycle guards, effective/active state, external-system mappings, optimistic concurrency, project restrictions, default-code safeguards, direct tenant/organization ownership, scoped foreign keys, and PostgreSQL RLS policy setup. The obsolete `CostItem` aggregate and its code field are deleted; canonical planned costs, commitments, and actual entries reference cost-code identities directly. Cost code is "what" and remains separate from WBS "where."

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
history). The approved budget and its lines are now the sole budget-authorization authority.
Scoped project catalog, finance snapshot, portfolio heatmap, and scenario readers aggregate the
approved lines in SQL. The former `Project.planned_budget` field and database column are deleted.
EVM BAC remains correctly owned by the cost-loaded approved baseline rather than budget
authorization.

### 11.6 Planned Costing

**Status: IMPLEMENTED, authoritative for KPI/dashboard/FinanceSnapshot planned totals
(2026-08-11; item 7 closure 2026-08-12).** Versioned
`ProjectPlannedCostVersion`/`ProjectPlannedCostLine` snapshots (CURRENT/SUPERSEDED, no
approval lifecycle — see `project_planned_cost_snapshot_plan.md`, deleted 2026-08-06: its
design deviated from what was actually built, see 11.6 below for the accurate shape)
are built and tested, sourced from `TaskAssignment.allocated_planned_hours` resolved through
the same rate-card resolver `CostPolicyEngine`/`LaborCostEngine` use, with source lineage
(`source_assignment_id`), WBS (`task_id`), and cost-code (the project's single
`ProjectFinancialProfile.default_cost_code_id` — a stated, coarser-than-`BudgetLine`
limitation) dimensions. Completeness is tracked as three independent flags
(`rates_complete`/`allocations_complete`/`cost_codes_complete`) plus diagnostic reason codes,
not one ambiguous flag. `CostPolicyEngine`/`ledger.py` now source KPI, dashboard, cost
breakdown, and `FinanceSnapshot.planned` totals from this versioned, allocated-to-task model —
not from `ProjectResource.planned_hours` (see §19 Phase B item 7). `calculate_snapshot` is a
governed, permission-gated (`plannedcost.manage`) action, consistent with Budget/Forecast/
Baseline generation elsewhere in this system — it is not, and does not need to be,
auto-triggered on every assignment/rate mutation; a project with no snapshot yet correctly
shows no planned-cost contribution rather than an error. A design review's recommendation to
additionally build a full versioned `ProjectLaborPlan`/`LaborPlanAllocation` aggregate (its own
DRAFT/SUBMIT/APPROVE lifecycle, and a genuinely distinct resource-envelope-capacity question,
not a competing "planned cost" source) remains deliberately deferred as a larger, separately
scoped future phase; the interim `LaborCostEngine.calculate_project_labor_plan_vs_actual`
placeholder for that question was unreached by any production caller and was deleted
(2026-08-12) rather than left half-alive. Manual/material planned-cost lines and
baseline-comparison sourcing (which exact rate-card line/version valued each baseline task)
remain unimplemented.

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
| `ProjectFinancialProfile` | Project finance configuration and defaults | Project, Organization, default cost-code/rate-card/calendar IDs | Canonically mutates only its profile; no Project currency projection or dual write exists |
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

Implementation progress (2026-08-11 update — F0, `RBAC reporting`):

- The 2026-08-02 pass above closed `report.view` only for `FinanceService`/`ProjectFinanceWorkspaceQuery`. `ReportingService` (EVM, cost breakdown, cost source breakdown, labor detail) and `DashboardService` (cost-source/EVM/KPI financial fields) still authorized on `report.view` alone, re-exposing the same finding through the reporting/dashboard/export surface.
- Added `ReportingService._require_finance_view` (`finance.read`) and `_require_finance_sensitive_view` (`finance.read_sensitive`) gates and wired them into `get_cost_breakdown`/`get_project_cost_source_breakdown`/`get_project_cost_control_totals` (`cost_breakdown.py`, `cost_policy.py`), `get_earned_value`/`get_evm_series` (`evm_core.py`, `evm_series.py`), and `get_project_labor_details`/`get_project_labor_plan_vs_actual`/`calculate_project_labor_details` (`labor.py`).
- `report.view` remains the correct, sufficient gate for genuinely non-financial reports (`get_gantt_data`, `get_resource_load_summary`, `get_critical_path`) — it was not blanket-replaced.
- `get_project_kpis` and `DashboardService.get_dashboard_data` mix schedule/non-financial facts with financial fields in one DTO; both now redact the financial fields (`financial_detail_included`/`cost_sources`/`evm` become `false`/`None`) for a `report.view`-only caller instead of denying the whole call, mirroring the existing `FinanceService` labor-redaction convention.
- New regression coverage in `src/tests/project_management/test_project_finance_phase_a0_security.py` (the "F0 — ReportingService / DashboardService authorization boundary closure" section): `report.view`-alone allow/deny split, KPI/dashboard redaction-not-denial, `finance.read` vs `finance.read_sensitive` tiering, export-permission-is-not-read, and cross-project/cross-organization isolation. Full file: 18 passed.
- All A0 code gates are now met for the reporting/dashboard/export surface as well, not only `FinanceService`.

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
   **Item 7 closed (2026-08-12).** The rejection below (2026-08-06) is
   retained as historical record, but the cutover it rejected was
   subsequently performed anyway by an unrelated legacy-`CostItem` deletion
   pass (2026-08-11, `CostPolicyEngine`/`ledger.py` rewrite) — and, once
   re-audited, the two objections that made it look unsafe turned out not
   to hold at the scope this project actually needed:
   - **The granularity mismatch was real, but resolvable by not merging.**
     `CostPolicyEngine`/`ledger.py`'s KPI/dashboard/`FinanceSnapshot.planned`
     figures now source exclusively from `ProjectPlannedCostVersion`
     (allocated-to-task), which is correct — this is the single canonical
     "planned cost" figure. `LaborCostEngine.calculate_project_labor_plan_vs_actual`
     (the third call site, answering the *different* question "is this
     resource over/under their envelope") was never merged into it; it sat
     unreached by any production caller and has been **deleted** (pre-release,
     no compatibility burden to preserve) rather than resurrected as a
     competing "planned" source. A resource-capacity plan-vs-actual report,
     if wanted later, should be rebuilt cleanly and explicitly scoped as
     that — not left half-alive next to the canonical figure.
   - **The "no freshness mechanism" concern was investigated further and is
     not a gap.** `PlannedCostService.calculate_snapshot` requires
     `plannedcost.manage` — it is an explicit, governed, permission-gated
     action, exactly like Budget-version and Forecast-version generation and
     Baseline creation elsewhere in this system. None of those recalculate
     automatically on every underlying mutation either. A project with no
     snapshot calculated yet correctly shows no planned-cost contribution —
     the same graceful-degradation behavior `BaselineService.create_baseline`
     already relies on today (verified: it creates baselines against
     projects with zero `ProjectPlannedCostVersion` rows without error,
     `test_baseline_comparison_workflow.py`). This is optional-capability
     behavior, not tactical debt, and does not require an auto-recalculation
     pipeline.
   - Baseline provenance (which exact rate-card line/version valued each
     task) remains unrecorded — still a real, separately-scoped gap if a
     baseline financial-snapshot extension is ever wanted, not part of this
     item's closure.
8. Complete (2026-08-09): replaced the QML combined "Budget" cost-line section with separate Profile, Budget Versions, Budget Lines, Rate Cards, and Planned Costs views. The false legacy component was deleted rather than retained as compatibility UI.

Exit gate: approved budgets cannot mutate; rate selection is deterministic; historical snapshots remain stable after rate changes; plan totals reconcile by cost code/WBS/period; cross-tenant references fail.

Implementation progress (Phase B1, 2026-08-02):

- Accepted ADR-PF-003 (Task-owned WBS), ADR-PF-005 (rate-card precedence), and ADR-PF-009 (PM-owned cost-code catalog) after revalidating the complete Scheduling, Finance, Inventory, and Procurement ownership evidence.
- Added Pydantic-validated `ProjectFinancialProfile`, `ProjectCostCode`, and `ProjectCostCodeRestriction` domain models. Profile transitions and billing invariants, cost-code syntax/effective dates/external mappings, hierarchy cycles, active ancestors/children, and default restrictions are explicit.
- Added canonical repository contracts, mappers, fail-closed scoped SQLAlchemy repositories, optimistic updates, and service composition through `RepositoryBundle`, `ProjectManagementServiceBundle`, and `ServiceGraph`.
- Added `project_finance_profiles`, `project_finance_cost_codes`, and `project_finance_cost_code_restrictions` in revision `j8k9l0m1n2o3`. Every table has non-null tenant/organization scope, scoped uniqueness/foreign keys, check constraints, RLS metadata, and forced PostgreSQL tenant/organization policy setup.
- New Project creation flushes and inserts its financial profile before the same commit. Existing profiles backfill deterministically from a supported Project currency then a supported Organization base currency; migration fails with a repair message if neither is valid. No write-on-read repair path exists.
- Added global plus project-scoped `finance.read`/`finance.manage` enforcement, owner-only project financial configuration, mandatory optimistic versions, and fail-closed Enterprise Audit in the mutation transaction.
- Verification: 23 focused B1 domain, service, repository, RBAC, architecture, transition-register, migration upgrade/backfill/downgrade, and audit rollback tests pass. The pre-existing Phase A0 finance/RBAC integration set also passes (14 tests in the combined check). The broader PM suite passes 345 tests with only the three known unrelated dashboard date-relative/entitlement-order cases deselected; Architecture passes 113 tests with only its two pre-existing size-budget breaches.
- The B1 currency transition is closed. The two-way Project/Profile synchronization, marker,
  Project field, ORM column, desktop/import contracts, and QML editor path were deleted on
  2026-08-11. No compatibility adapter or dual read remains.

Implementation checkpoint (Phase B item 8, 2026-08-09):

- Added a canonical `ProjectFinanceWorkspaceQuery` application read projection guarded by
  global and project-scoped `finance.read`. It resolves profile, budget lifecycle versions and
  lines, organization/project-visible rate cards and lines, and planned-cost snapshots and lines.
- Reconciliation totals and task/resource/cost-code labels are application-owned. Repository
  bulk methods and grouped summaries keep the warm projection bounded to at most 14 SQL statements
  regardless of the number of versions, cards, or lines; cross-organization reads fail closed.
  Growing budget, rate, and planned-cost line collections use explicit 50-row offset pages with
  total counts and in-section pagination; profile/version/card administration lists remain small,
  stable project configuration collections.
- Desktop DTOs format the immutable projection only. Presenter/controller state exposes five
  distinct project-level collections, and the Views menu can open them even when the legacy cost
  register has no rows. Cost-row activation now opens Actuals rather than pretending the row is a
  budget.
- Deleted `FinancialsBudgetSection.qml` and its registration. No fallback, dual-read adapter,
  temporary component, or transition file was introduced. Canonical lifecycle mutations remain
  in their existing application services; this item intentionally adds lifecycle-aware views,
  not duplicate QML-owned write policy.
- Verification: 86 underlying Phase B configuration/rate-card/budget/planned-cost tests pass with two
  existing SQLite datetime-adapter deprecation warnings. The focused desktop/QML architecture
  checkpoint passes 30 tests, and the new projection/isolation/pagination/measurement suite passes 6 tests.
  The combined final application/desktop/QML/architecture checkpoint passes 51 tests.

### Phase C - Actual ledger, commitments, time, procurement, and periods

Ownership: **PROJECT FINANCE + PLATFORM TIME + INVENTORY PROCUREMENT + PLATFORM FOUNDATION + INTEGRATION**

ADR gate: ADR-PF-004, ADR-PF-006, ADR-PF-007, and ADR-PF-008 must be accepted before ledger/source integration cutover.

1. **Complete 2026-08-09:** add organization financial periods and closure/lock policy. Keep them separate from operational scheduling calendars.
2. **Complete 2026-08-09:** add ProjectCostEntry draft/approval/post/reversal lifecycle with direct scope, Money/base-Money/FX snapshot, source, period, dimensions, actor/timestamps, and scoped idempotency constraints.
3. **Complete 2026-08-09:** add PM commitment projections/lines, monotonic immutable source
   revisions, receipt-actual matching/reversal, cancellation/closure, and remaining-balance policy.
4. **Complete 2026-08-09:** add an approved-Time contract/event and idempotent labor-cost consumer. Snapshot rate and reverse/replace corrected approvals.
5. **Complete 2026-08-09 for available source lifecycles:** add typed Procurement project-source events for PO SENT/status/cancellation/closure and POSTED receipts. PM creates projections/postings; Procurement remains owner. Governed post-send amendment and supplier-invoice sources remain future because those source aggregates/commands do not yet exist.
6. **Complete 2026-08-09:** replace combined CostItem runtime writes with canonical planning,
   source-owned commitment, and manual-actual commands. Posted actuals are never editable/deletable.
7. Backfill/split legacy CostItem rows, dual-read for reports, reconcile totals, and quarantine unresolved currency/source cases.
8. Redesign QML Actuals and Commitments as ledgers with status, source, period, matching, approval, posting, and reversal actions. Remove the generic edit/delete behavior from posted rows.

Exit gate: only approved time generates actuals; one source/version cannot duplicate; rate/FX changes do not change history; commitment matching avoids double count; closed periods reject normal posting; RLS and tenant tests pass; legacy and new totals reconcile.

Implementation progress:

- The 2026-08-06 `TRANSITION(PF-A0-UOW-BRIDGE)` cleanup that items 2/6 depend on
  remains complete: dedicated approved commands own their Unit of Work.
- Item 1 is complete. The reusable Platform Finance period aggregate is independent of
  operational calendars and owns code/year/number/date identity plus an irreversible normal
  open -> closed -> locked lifecycle. Persistence has direct tenant/organization ownership,
  composite organization foreign keys, RLS metadata/migration, scoped uniqueness, optimistic
  concurrency, and an organization-row write lock before overlap validation. PostgreSQL thereby
  serializes concurrent catalog writers; local SQLite retains the same application invariant.
- `FinancialPeriodService` applies `finance.read`/`finance.manage`, fail-closed Enterprise Audit,
  and a canonical `require_open_period_for_date()` policy for item 2 and later source consumers.
  The typed desktop adapter exposes list/get/create/update/close/lock without carrying domain
  policy into QML. No delete, reopen, late-post adapter, fallback, or temporary transition file
  exists.
- The current `finance.manage` close/lock boundary is deliberately coarse. Dedicated close
  authority, separation of duties, reopen, and late-adjustment behavior remain blocked on the
  section 24 product decision; item 2 may implement normal posting without inventing those paths.
- Verification: all 9 new C.1 tests pass; the combined C.1 plus Project Finance persistence
  guardrail suite passes 19 tests. A fresh SQLite Alembic upgrade/downgrade passed and the graph
  remains single-headed; the final selected C.1/PM-finance/migration/graph checkpoint passes 30
  tests. The broader desktop-registry/PM-finance run passed 24 tests; its two
  failures are the pre-existing Site timezone-comparison and inactive-organization provisioning
  defects.
- Item 2 is complete. `ProjectCostEntry` is a validated signed aggregate with dedicated manual
  actual/adjustment draft commands, explicit submit/approve/reject/post transitions, and a
  separate equal-and-opposite posted reversal. Submitted facts are frozen; posting captures the
  open financial period, transaction and base Money, base-per-transaction FX rate/date/source/
  capture timestamp, dimensions, source identity/content hash, actor metadata, and optimistic
  row version. Rejection returns the entry to an editable draft while preserving rejection
  evidence. A reversal preserves the original currencies and FX conversion snapshot but posts
  into the open period selected by its own posting date.
- The canonical service applies `project_cost.create`, `.update_draft`, `.submit`, `.approve`,
  `.post`, and `.reverse` globally and at project scope. Finance Controller and project-owner
  authority support posting/reversal; planners/project leads prepare and submit; approvers decide.
  Optional governed approval stages mutations under ApprovalService's outer Unit of Work and
  records the deciding principal. Every mutation writes fail-closed Enterprise Audit and emits a
  dedicated post-commit cost-entry event.
- `project_cost_entries` has direct tenant/organization/project ownership, Numeric Money/FX
  columns, scoped project/cost-code/period/reversal foreign keys, deterministic source
  idempotency, one-reversal uniqueness, database-side filtered pagination/counts, RLS metadata,
  and PostgreSQL/SQLite update/delete guards for posted financial facts. Normal posting rejects
  missing/closed/locked periods; cross-currency posting requires a complete immutable FX
  snapshot. The migration graph is single-headed at `p3q4r5s6t7u8`.
- C.2 introduced no dual-write, legacy adapter, feature flag, or temporary file. Legacy
  `CostItem` remains deliberately unchanged until items 6-8 perform command cutover, deterministic
  migration/reconciliation, read cutover, and QML redesign; its deletion-register rows therefore
  remain open. Verification: 7 focused C.2 tests pass, and the combined period/ledger/budget/
  authorization/security checkpoint passes 105 tests.
- Item 3 is complete. PM now owns a canonical `ProjectCommitment` projection header per opaque
  Procurement purchase-order ID and a `ProjectCommitmentLine` per opaque purchase-order-line ID.
  It does not import Inventory packages, query Inventory repositories, or create cross-module
  foreign keys. The typed PM inbound source contract is consumed at the application boundary;
  C.5 now supplies the outbox/inbox dispatcher outside both business modules. A permanent
  architecture test rejects direct PM-to-Inventory and Inventory-to-PM imports.
- Each line snapshots Decimal quantity/rate, transaction and organization-base Money, FX rate/
  date/source/capture timestamp, project/cost-code/task/supplier/site dimensions, source content
  hash and positive integer revision, lifecycle, matched amount, actors/timestamps, and optimistic
  row version. Every accepted source version also creates an immutable full JSON source snapshot.
  Same-version/same-content retry is idempotent; same-version/different-content and older unseen
  delivery are rejected. Project, unit, transaction currency, and base currency cannot silently
  change after recognition.
- Remaining exposure is `committed - matched` for sent, partially received, and fully received
  lines. Fully received deliberately retains unmatched exposure until the receipt actual arrives,
  preventing event-lag understatement. Closed/cancelled lines release unmatched exposure while
  preserving original amount, source history, and any matches. Source lifecycle cannot regress,
  and a revision cannot reduce committed value below matched actuals.
- Matching accepts only posted Procurement receipt-accrual `ProjectCostEntry` facts in the same
  project and transaction currency. Immutable signed match/reversal rows enforce one original
  match per actual and one reversal per match; line locking, optimistic concurrency, amount checks,
  scoped uniqueness, and savepoints prevent overmatch and retry races. Every mutation is protected
  by `finance.read`/`finance.manage`, project-scope authorization, active financial configuration,
  effective/allowed cost codes, supplier/site/task validation, and fail-closed Enterprise Audit.
- `project_commitments`, `project_commitment_lines`,
  `project_commitment_source_revisions`, and `project_commitment_matches` directly own tenant/
  organization/project scope where applicable and use composite scoped foreign keys, canonical
  Numeric precision, RLS metadata/migration, source and match uniqueness, database amount bounds,
  immutable history/match triggers, and database-side stable pagination. Migration
  `q4r5s6t7u8v9` is the single head. Five focused C.3 tests plus the module-boundary architecture
  test pass; the combined C.3/persistence/period architecture checkpoint passes 20 tests and C.2's
  7-test suite remains green. The migration downgrades independently to C.2 revision
  `p3q4r5s6t7u8` while preserving the actual ledger. C.3 introduced no transition code,
  dual-write, temporary adapter, or legacy `CostItem` change.
- Item 4 is complete. Platform Time approval atomically writes one immutable, content-addressed
  event per changed approved entry to its owned outbox. Reapproval after a reason-required
  correction creates a monotonic source revision; rejection emits nothing and LOCKED is an
  administrative no-op for Finance.
- The infrastructure dispatcher uses the PM-owned durable inbox and applies the inbox receipt,
  rate/financial-period validation, posted actual, immutable labor posting detail, reversal or
  replacement, and fail-closed audit in one transaction. Source acknowledgement occurs only after
  that commit. Delivery failures retain retry/dead-letter state, and a bounded startup replay plus
  post-approval dispatch provide desktop operation without a task-specific thread or timer.
- PM Finance resolves the effective COST/HOUR rate as of the work date and snapshots the complete
  rate-card selection evidence. The Time contract carries hours and identity only; no Time
  implementation type, repository, or rate crosses the boundary. The directly scoped labor table
  has composite tenant/organization/project references, RLS, immutable database guards, and a
  reversible `s6t7u8v9w0x1` migration.
- Six focused C.4 integration tests cover first approval, rejection no-op, approval/outbox
  rollback atomicity, correction reversal/replacement, rate evidence, LOCKED no-op, closed-period
  rejection with durable retry evidence, inbox/outbox completion, post-commit UI refresh isolation,
  and migration reversibility. Combined C.1-C.4 period/ledger/commitment/delivery/architecture
  verification passes 43 tests; the selected related Time lifecycle/workspace verification passes
  17 tests. C.4 introduced no transition file, temporary adapter, dual-write,
  legacy `CostItem` mutation, or deletion-register item. The typed desktop correction command is
  complete; its final QML reason dialog/action remains at item 8's ledger redesign gate.
- Item 5 is complete for the Procurement lifecycles that exist. Project/task-linked PO SENT and
  later status revisions atomically write immutable Decimal quantity/rate snapshots to the
  Procurement-owned outbox. POSTED accepted receipt lines emit accrual facts; rejected quantities
  do not create actuals. Unlinked purchasing remains outside Project Finance.
- PM resolves opaque task references inside its own boundary, applies active project/profile/
  default-cost-code/supplier/site/currency validation, creates monotonic commitment revisions,
  posts receipt accruals into open periods, and matches no more than remaining commitment value.
  Receipt price variance remains fully visible in actual cost rather than being dropped or
  overmatched. Reason-required active cancellation releases on-order quantity and financial
  exposure while preserving source and match history.
- Source mutation plus outbox is atomic, and PM inbox plus commitment/actual/match/audit is atomic.
  Delivery uses bounded immediate/startup replay with durable retry/dead-letter and canonical
  failure codes; local QML refresh is post-commit only. Seven focused C.5 tests and the selected
  C.1-C.5/Procurement/architecture checkpoint pass 73 tests. No direct cross-module business
  import, foreign key, temporary adapter, dual-write, thread/timer, migration, legacy `CostItem`
  mutation, or deletion-register entry was added.
- Procurement does not yet own a governed post-send commercial amendment command or supplier-
  invoice aggregate. Those future source capabilities must publish later revisions/reclassification
  through this same contract; they are not simulated in PM.
- Item 6 is complete. Runtime `CostService` is query-only. Its combined create/update/delete
  mixins, desktop commands, QML editor and bulk mutations, cost CSV importer, approval handlers,
  governance aliases, and `cost.manage` permission/grants were deleted. Actuals use typed,
  idempotent `ProjectCostEntry` commands and the Actuals workspace exposes `New Manual Actual`;
  planned cost remains a versioned planning snapshot and commitments remain Procurement-owned
  source projections rather than ambiguous manual amount fields.
- Canonical actual audit and commit exceptions explicitly roll back their Unit of Work. The
  focused command/security checkpoint passes 17 tests; the complete legacy-report compatibility
  surface passes 103 tests with 1 skip. Targeted QML lint has no missing controller members.
  `TRANSITION(PF-C6-LEGACY-TEST-SEED)` is test-only and is due for deletion during item 7; it does
  not restore any production writer or dual-write behavior. Item 7 deterministic backfill,
  quarantine, reconciliation, and dual-read comparison is next.
- Item 7 is in progress. Migration head `t7u8v9w0x1y2` adds directly scoped/RLS migration runs
  and one restart-safe source-purpose checkpoint per legacy responsibility. Checkpoints preserve
  source and target Decimal values, rounding delta, currency resolution, default-cost-code
  mapping, target identity, quarantine/deferred reason, and original legacy classification/code.
  Dry-run writes control evidence only. Execute creates idempotent review-required actual drafts
  through the canonical `DATA_EXCHANGE/IMPORT_ROW/LEGACY_MIGRATION` identity; it never infers
  approval or posting. Missing default cost-code mapping is quarantined.
- Planned and commitment values currently remain durable deferred checkpoints while their
  explicit legacy source variants are built; no resource, supplier, site, PO, or assignment is
  fabricated. Forecast overrides remain deferred until Phase D owns a canonical forecast
  aggregate. Report dual-read/parity, raw-invalid-row quarantine, planned/commitment target
  creation, and test-seeder deletion are still required before item 7 can close. Four focused
  C.7 tests pass, including active-organization isolation, and the combined C.6/C.7/security/
  persistence/QML checkpoint passes 33 tests;
  Alembic remains single-headed at `t7u8v9w0x1y2`.

### Phase D - Forecasts, ETC, change control, and enterprise reporting

Ownership: **PROJECT FINANCE**

1. Add forecast versions/lines and explicit automatic/manual source metadata.
2. Define ETC source precedence and exclusion/matching rules across remaining plan, commitments, risks, and manual estimates.
3. Add typed financial change requests that apply approved budget, forecast, and schedule impacts atomically through their canonical owners. Keep procurement commitments source-owned and defer project contract value to Phase E product decisions.
4. Rebuild snapshot, cash flow, EVM, variance, and portfolio financial read models from canonical Money, posted actuals, open commitments, and approved/current forecast versions.
5. Add as-of/basis/period metadata, pagination, source drill-down, reconciliation/control totals, and sensitive-field filtering to exports.
6. Remove desktop forecast fallback formulas and legacy CostItem reporting once parity is proven.
7. Redesign QML Forecast, ETC, Change, Variance, and reporting tabs around version selection and drill-down; keep fixed contextual tools and section headers consistent with existing PM workspace standards.

Exit gate: forecasts are reproducible and historical; no commitment/ETC double count; approved changes create traceable versions; all report totals reconcile to ledger sources; legacy read code is removed.

Implementation progress (2026-08-11):

- **D.1A COMPLETE — canonical forecast persistence and governed lifecycle.** PM now owns
  `ProjectForecast` and `ForecastLine` aggregates with explicit DRAFT/SUBMITTED/APPROVED/
  REJECTED/SUPERSEDED transitions, immutable project revision, separate optimistic row version,
  `as_of_date`, generation mode, currency, actor/timestamp history, and one-open/one-approved
  database invariants. Approval atomically supersedes the prior approved forecast.
- Forecast lines use canonical Decimal Money and carry cost-code, optional WBS task, optional
  period, and explicit automatic/manual source metadata. Automatic remaining-plan and
  open-commitment lines require a stable source type/id and snapshot timestamp. Manual lines are
  either explicit `manual_estimate` rows or contingencies linked to a snapshotted risk. Domain and
  database constraints reject mixed source semantics, invalid periods, negative amounts, and
  cross-scope parent references.
- `ForecastVersionService` is composed through the PM service graph with `forecast.manage`/
  `forecast.approve` RBAC, project-scope enforcement, active tenant/organization ID scoping,
  optimistic concurrency, cost-code/task eligibility checks, fail-closed audit, and domain-change
  events. PostgreSQL forced RLS is delivered by reversible migration `v9w0x1y2z3a4`; D.1B
  revision `w0x1y2z3a4b5` now follows it as the sole Alembic head.
- No data migration or compatibility path was created because the application is pre-release and
  has no client forecast data. D.4 subsequently deleted the transient `ForecastCostService` after
  canonical read reconciliation and desktop parity were proven.
- Verification: 8 focused forecast lifecycle/tenant/migration tests pass; 44 RBAC/security tests
  pass; 12 desktop-adapter architecture tests pass; the migration graph passes with the unrelated
  repository size guard deselected; and the canonical PM suite passes with 567 tests. The older
  `src/tests/pm` tree still has 12 pre-existing scheduling contract mismatches unrelated to this
  implementation.

- **D.1B COMPLETE — canonical automatic ETC generation and source evidence.** The composed
  `ForecastGenerationService` reads every paginated canonical source through PM repository
  contracts and writes one `ProjectForecast`, all `ForecastLine` rows, all reason-coded
  `ForecastSourceDecision` rows, and the fail-closed audit entry under one commit boundary. Any
  persistence or audit failure rolls back the complete generated version. Permission checks remain
  `forecast.manage` plus project scope; active tenant/organization scope is resolved once through
  the canonical context service.
- The generator selects the latest complete planned-cost version whose business `as_of` is not
  later than the requested forecast date. Posted actuals at or before that date are netted as signed
  offsets by cost-code/task; reversals and future postings are excluded with evidence. Each open
  commitment contributes only `amount - matched_amount` (or its snapshotted base-currency
  equivalent) to ETC and offsets the same remaining-plan envelope. Applying both offsets before
  emitting remaining plan makes commitment/ETC double counting impossible. A taskless offset is
  allocated deterministically across task slices for the same cost code.
- Manual ETC has narrow replacement semantics: it suppresses remaining-plan ETC only for its exact
  task dimension, or for the whole cost code when intentionally entered without a task. It never
  suppresses an open commitment. Risk contingency is additive only when the caller supplies an
  explicit monetary estimate linked to an active project risk; register severity is not assigned a
  fabricated monetary value. Overlapping manual scopes, duplicate risks, inactive/newer risks,
  incomplete plan snapshots, unsupported currencies, future forecast dates, and newer commitment
  state without historical reconstruction fail with typed errors.
- Every considered source leaves durable evidence containing source identity/type/snapshot,
  cost-code/task dimension, action, reason, source amount, included amount, and excluded amount.
  The amounts must reconcile in both Pydantic domain validation and database constraints.
  Evidence-backed zero ETC is valid and submit-able; a request with no source facts is rejected.
  Migration `w0x1y2z3a4b5` adds this tenant/org/project-scoped evidence table, task/source indexes,
  linked-risk line constraint, and forced PostgreSQL RLS. It is the sole Alembic head and is
  reversible.
- D.1B is a direct pre-release implementation: no backfill, compatibility facade, dual read/write,
  legacy forecast model, or temporary transition file was introduced. D.4 has now removed the
  transient desktop formula service at the canonical read-model/QML parity gate.
- D.1B verification: 13 focused lifecycle/generation/precedence/risk/zero-ETC/atomicity/tenant/
  migration tests pass. The affected finance architecture, persistence, security, and composition
  checkpoint passes 39 tests; its only global-suite failure is the pre-existing hard-size guard for
  generated `resources/shared_resources_rc.py` and platform `enterprise_calendar.py`.

- **D.2 COMPLETE - governed budget/forecast/schedule financial changes.** PM now owns scoped
  `FinancialChangeRequest` and typed impacts with immutable change revisions, optimistic
  concurrency, snapshotted approved bases, exact target-line deltas, actor/timestamp history,
  applied-version references, and fail-closed audit. A two-actor Platform Approval decision
  atomically supersedes the approved budget and/or forecast and creates approved successors.
  Forecast copies and changes retain durable `base_forecast`/`financial_change` line and decision
  lineage. Stale bases, concurrent open versions, invalid dimensions, negative successor values,
  duplicate targets, unsupported dimensions, and audit failures fail closed and roll back.
- Schedule impacts snapshot the target task version and apply through the PM task owner's internal
  batch command. It accepts only unstarted execution leaves, validates project working days and
  project bounds, writes all requested windows, recalculates dependencies once, and verifies the
  exact approved result. Typed applied references identify budget lines, forecast lines, or tasks;
  mixed changes participate in the same approval/audit transaction and publish only after commit.
- Migration `pfchg_d2_001` is reversible and is the sole head. It adds composite scoped ownership,
  typed-shape/lifecycle constraints, indexes, and forced PostgreSQL RLS. No legacy model, backfill,
  dual path, compatibility facade, or temporary transition code was introduced.
- **Ownership correction:** `contract` was removed from D.2 before release. Existing PM commitment
  lines are procurement-sourced projections and must change only through ordered procurement source
  revisions. Project contract value is a missing revenue/billing aggregate gated by Phase E and
  ADR-PF-010. The ambiguous task-level planned-hours delta was also removed; cost effects require
  explicit budget/forecast impacts, while assignment hours remain resource/task planning authority.
- D.2 verification: nine focused change-control/domain/schedule/atomicity/migration tests pass;
  combined change, forecast, task hierarchy/domain, schedule-impact, RBAC reconciliation, and
  session-permission coverage passes 53 tests; the comprehensive affected budget/forecast/change/
  task/schedule/RBAC checkpoint passes 95 tests. Architecture coverage with the known hard-line
  limit deselected reports 152 passes and two unrelated stale-guard failures: a reference to the
  removed `repositories/cost.py` and a 410-line budget for the pre-existing 449-line scheduling
  engine. Neither touches D.2.

**D.4 COMPLETE - disposable canonical finance read models (2026-08-11).**

- `FinanceSnapshotFacts`, `FinanceControlFact`, application snapshots, cash-flow/analytics rows, and
  portfolio rows are disposable, on-demand projections. They have no ORM, table, migration,
  repository, or write command; deleting/rebuilding them loses no business data. An architecture
  guard enforces this rule. Persisted approved budget/forecast versions, posted/reversal entries,
  and Procurement-owned commitment projections remain the authorities.
- The scoped reader preserves Decimal Money through the application boundary and selects the latest
  approved or superseded-approved forecast valid at the requested as-of date. It reconciles approved
  budget, net posted actual, unmatched open commitment, approved ETC, EAC (`actual + ETC`), and VAC
  (`budget - EAC`). Open commitments are visible controls but are not added to forecast EAC again.
- Cash flow uses posting dates and approved forecast periods, not `max(...)` exposure heuristics.
  EVM retains baseline-owned BAC/PV/EV and posted AC, while EAC/ETC/VAC use the approved forecast and
  remain unavailable without one. Portfolio overrun is EAC minus approved budget and no longer
  invokes labor-rate calculation per project or reports `actual - planned` as cost variance.
- The temporary `ForecastCostService`, EAC formula enum, composition/runtime plumbing, recalculation
  action, old tests, fake invoiced/paid commitment totals, and duplicate non-EVM Finance UI section
  were deleted. Desktop mapping converts Decimal only at the QML boundary; the forecast card now
  exposes approved version/as-of, budget, posted actual, ETC, EAC, and VAC.
- Verification: focused D.4/security/CQRS/disposal coverage passes 38 tests; broad affected finance,
  reporting, and portfolio coverage passes 101 tests. Architecture/QML coverage passes 153 tests;
  only the three already-documented repository-wide stale/size guard failures remain.
- Portfolio measurement passes at small/medium/large sizes and now enforces `13 + 4N` heatmap SQL
  statements with zero per-project rate-resolution calls, improving the previous `12 + 6N` graph.
  The complete PM run reached 73% before the five-minute limit; its only emitted failures were the
  three stale performance expectations, which pass after updating the measurement contract.

**D.5 COMPLETE - governed finance report/export parity (2026-08-11).**

- `FinanceSnapshot` remains disposable and now exposes `PROJECT_CURRENCY` basis, requested as-of,
  period granularity, approved budget/forecast version evidence, sensitive-detail state, and exact
  Decimal reconciliation controls. Posted actual, open commitment, and approved ETC authority totals
  must equal their full ledger totals; an inconsistency fails closed before an export can render.
- Canonical ledger rows retain source type, cost-code ID, reference type/ID, task/resource IDs,
  actual financial-period IDs, and forecast period boundaries. Sensitive labor rows are aggregated
  and replace those identifiers with an explicit restricted source; export metadata records whether
  detail is included or redacted.
- Excel and PDF consume the same shared finance export projection and expose equivalent metadata,
  summary, controls, reconciliation status, cash-flow/source analytics, and source drill-down. Format
  renderers do not calculate independent finance formulas.
- Ledger detail uses validated offset paging with a hard 500-row page maximum. Page range, total,
  limit, and continuation state are included in the report. Summary and reconciliation values always
  come from the complete canonical snapshot, never a partial page.
- Finance report generation requires the existing `report.export` runtime permission plus explicit
  global/project `finance.export`; reading the snapshot still requires global/project `finance.read`.
  Project owner scope now includes `finance.export`. The deprecated unused
  `infrastructure/reporting/exporters.py` wrapper was deleted rather than retained as dead code.
- Verification: the broad finance/reporting/commitment/portfolio selection passes 241 tests with 21
  dependency warnings. Real Excel/PDF rendering, metadata, bounded lineage, redaction state,
  reconciliation, and permission tests pass. Architecture passes 153 tests; only the three existing
  stale/size guard failures documented under D.4 remain, and none concerns D.5.

**D.7 COMPLETE - governed QML lifecycle and report drill-down.** The financial workspace now reads
forecast revisions/ETC source lines from `ForecastVersionService`, financial requests/typed impacts
from `FinancialChangeService`, and approved/superseded schedule-baseline comparison history from
`BaselineService`. Child forecast-line and change-impact reads first revalidate the requested parent
against the selected scoped project's collection. Authorization and context failures propagate to
the fixed section-scoped inline message instead of being swallowed as empty data.

Forecast preserves the canonical approved ETC/EAC/VAC summary and adds selectable historical/current
versions with source type/reference/snapshot/period drill-down. Change Control shows snapshotted base
budget/forecast versions and applied owner references. Variance explicitly identifies its measure as
stored plan-to-plan schedule and planned-cost movement, not actual-cost performance, and excludes
draft/rejected baselines from selection. Reports exposes its currency/forecast/baseline/source-page
basis and fixed contextual Excel/PDF actions; generation delegates to the D.5 shared reconciled
projection with the selected governed baseline and performs no QML/controller/presenter formula.

The broad exception fallback and old `build_baseline_variance` contract, the nonfunctional export
message, empty `FinancialsInsightsSection.qml`, and stale nonexistent workspace-state module entry
were deleted. No persisted snapshot, compatibility alias, legacy branch, temporary adapter, dual
read, or transition code remains from D.7. Focused lifecycle/security/export tests pass `6`; the PM
finance/financial/reporting selection passes `167` (`427 deselected`, 19 dependency warnings),
desktop-boundary/canonical-read coverage passes `22`, presenter/QML runtime coverage passes `13`,
and changed-workspace `qmllint` is clean.

Phase D closeout (2026-08-11): PM monetary/rate/quantity desktop DTOs now expose canonical decimal
text, while authoritative domain/read models use `Decimal`. Revisions `pfnum_d8_001` and
`pfnum_d8_002` migrate resource/project-resource rates and hours, portfolio budgets, baseline costs
and variances, and assignment logged hours to platform `Numeric` precision. Percentage fields remain
intentional floating-point ratios. `Money.from_legacy_float`, `decimal_from_legacy_float`, their
exports/tests, both transition markers, and the PM formatter float branch are deleted. The obsolete
baseline unassigned-budget allocation branch was deleted rather than converted. Architecture
guardrails pin all eight canonical PM columns and reject restoration of either converter.
Focused persistence/DTO/migration coverage passes `54` tests. The broader PM finance/resource/
portfolio/baseline/assignment selection passes `342` tests (`253 deselected`, 22 dependency warnings).

### Phase E - Billing preparation, revenue, and external accounting

Ownership: **PROJECT FINANCE + FUTURE BILLING/ACCOUNTING OWNER + INTEGRATION**

ADR gate: **OPENED 2026-08-11.** ADR-PF-010 and the first-release product scope are accepted.

1. Complete: resolve the product decisions in Section 24 before implementation.
2. **Complete 2026-08-11:** PM billing profiles, fixed-price schedules, preparation/line
   aggregates, direct tenant/org/project ownership, optimistic versions, canonical Numeric storage,
   scoped foreign keys, and forced PostgreSQL RLS are implemented by `pfbill_e1_001`.
3. **Complete 2026-08-11:** fixed-price milestones, approved-time billing-rate snapshots, and
   posted-cost markup snapshots use idempotent source locks. Approval finalizes locks; rejection
   releases them; a scoped uniqueness constraint prevents duplicate selection under retry/race.
4. **In progress:** the vendor-neutral `project_billing_preparation.v1` contract, durable
   delivery-pending lifecycle, append-only idempotent outcomes, external invoice-reference display,
   and reconciliation references are implemented. A deployable Accounting publisher/worker adapter
   remains pending because no Accounting module/system is selected; PM does not simulate one.
5. **Pending:** add disposable contract-value, billable/prepared/external-outcome, revenue projection,
   and permission-redacted profitability read models. Statutory revenue recognition, invoices, tax,
   payments, receivables, and GL posting remain external.
6. **Complete read-only checkpoint 2026-08-11:** the misleading invoice EmptyState and legacy
   section filename are removed. The Billing Preparation view shows commercial terms, schedules,
   preparation lifecycle, and Accounting outcomes with database pagination and a batched latest-
   outcome query. Governed command dialogs remain pending until their complete workflows are wired.
7. **Pending final gate:** no Phase E transition DTO, dual write, legacy column/reader, permission
   alias, or feature flag has been created. Repeat the inventory after the publisher and command-UI
   cutovers, then close the phase only if it remains empty.

Phase E foundation verification (2026-08-11): fresh full-history migration upgrade/downgrade,
domain lifecycle, decimal contract, accounting-ownership guard, PM finance persistence/RLS,
service composition, approval registration, tenant-scope architecture, desktop boundaries, and QML
guardrails pass. Focused runs report `18 passed`, `41 passed`, `35 passed`, `12 passed`, and
`24 passed`; the expanded PM financial/billing selection passes `48` tests and the combined
architecture checkpoint passes `60` tests; `qmllint` reports no warnings. The repository-wide
hard-size guard still has only its
documented generated Qt-resource and pre-existing enterprise-calendar failures.

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
| Actual ledger | `project_cost_entries` | IMPLEMENTED in C.2: direct tenant/org/project scope; posting/reversal state; source idempotency; scoped reversal links; one full reversal; Numeric Money/FX snapshots; immutable posted financial facts and delete guards |
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
| `report.view` finance authorization | Pre-existing | A0 finance permission grants and policy tests pass | Platform Security / PM Finance | CLOSED; replaced by `finance.read` on 2026-08-02 for `FinanceService`; extended to `ReportingService`/`DashboardService` (EVM, cost breakdown, cost source breakdown, labor detail, KPI/dashboard redaction) on 2026-08-11 (F0, commit `RBAC reporting`) — see Phase A0 implementation progress above |
| Admin-session cost-governance bypass | Pre-existing | A0 removal tests pass | Platform Security | CLOSED; removed 2026-08-02 |
| `cost.manage` umbrella/alias | Pre-existing; transitional mapping in A0 | Target command permissions active across desktop/services | Platform Security / PM Finance | CLOSED 2026-08-09; removed after C.6 runtime command/QML cutover |
| Hard-coded PM `EUR` defaults | Pre-existing | A1 Organization/Profile currency resolution cutover | Platform Foundation / PM | CLOSED; command constants removed and Organization resolution active 2026-08-02 |
| Duplicate PM money formatters | Pre-existing | A1 canonical serialization/formatting adopted | Desktop UI / PM | CLOSED; four implementations replaced by one Decimal-aware boundary 2026-08-02 |
| Legacy combined CostItem write API | Pre-existing | C distinct planned/commitment/manual-actual commands and QML cutover | PM Finance / Desktop UI | CLOSED 2026-08-09; runtime service/API/QML/import/approval writers deleted |
| `TRANSITION(PF-C6-LEGACY-TEST-SEED)` test-only row factory | C.6 regression closeout | C.7 canonical fixtures no longer require legacy setup | PM Finance / Test Architecture | CLOSED 2026-08-11; deleted |
| `TRANSITION(PF-C7-LEGACY-IMPORT)` canonical import-draft command | C.7 actual split | No production data exists to replay | PM Finance / Data Migration | CLOSED 2026-08-11; deleted rather than retained |
| Legacy CostItem reader/projection | Pre-existing; retained in B/C | Canonical planned/commitment/actual readers active | PM Finance | CLOSED 2026-08-11; runtime stack and table deleted |
| `Project.planned_budget` compatibility projection | Pre-existing; retained in B | Approved-budget SQL read cutover complete | PM Finance | CLOSED 2026-08-11; field and column deleted by `u8v9w0x1y2z3` |
| `Project.currency` compatibility projection | Pre-existing; retained in B | Profile currency cutover complete | PM Finance | CLOSED 2026-08-11; field and column deleted by `u8v9w0x1y2z3` |
| Profile-to-Project and Project-to-profile currency synchronization | B1; `PF-B1-CURRENCY-DUAL-WRITE` | All consumers use profile currency | PM Finance / Desktop UI | CLOSED 2026-08-11; both branches and marker deleted |
| Float monetary/rate/quantity persistence | Pre-existing | Relevant Numeric backfill, read cutover, and reconciliation complete | Platform/Data/Module owners | CLOSED 2026-08-11; eight PM columns migrated by `pfnum_d8_001`/`pfnum_d8_002`, canonical reads active |
| Planned dual-read comparison | C | D canonical report reconciliation complete | PM Finance | NOT CREATED |
| Planned dual-write adapter, only if required | C | New writes and reports reconcile; legacy writes disabled | PM Finance | NOT CREATED |
| Client-side fixed-limit Procurement lookup | Pre-existing | C typed project-source contract active | Procurement / PM Integration | CLOSED 2026-08-08; caller-free desktop projection deleted in DA0 instead of retained |
| Legacy financial permission aliases/feature flags | A0 onward | E final role/API/controller inventory passes | Platform Security / PM Finance | CLOSED 2026-08-12; E final role/API/controller inventory (item 7 gate) confirmed no alias or feature-flag code was ever added to `role_permission_catalog.py` or any Phase E desktop/controller surface — row closes as never-created rather than removed |
| Approval `commit=False` transaction switches in legacy cost/baseline/dependency/scheduling services | A0 | C dedicated approved commands own the shared Unit of Work | Platform Workflow / PM | CLOSED 2026-08-06; `CostLifecycleMixin`/`BaselineService`/`TaskDependencyMixin` each split into a public governed method + a private `_apply_*_decision` (mirroring `BudgetService`); `SchedulingEngine`/`_sync_project_schedule`'s `commit` params re-scoped as plain caller-owned batching, not an approval bridge — no regressions (24 pre-existing failures unchanged, 428 passed) |
| Approved-handler `bypass_approval=True` switches | Pre-existing; constrained in A0 handlers | C handlers call dedicated internal approved commands with no public bypass flag | Platform Workflow / PM | CLOSED 2026-08-06; `bypass_approval` parameter removed entirely from `add_cost_item`/`update_cost_item`/`delete_cost_item`/`create_baseline`/`add_dependency`/`remove_dependency` — no caller anywhere (checked) passed `bypass_approval=True` except the composition apply handlers, now rewired to call `_apply_*_decision` directly. `TaskDependencyMixin.update_dependency`'s governed branch was dead code (not in `DEFAULT_GOVERNED_ACTIONS`, no apply handler ever registered) — deleted rather than wired up. |
| Unused FinanceService ReportingService compatibility argument | A0 candidate | Remove before A0 merge | PM Finance | CLOSED; deleted 2026-08-02 |
| `Money.from_legacy_float` and `decimal_from_legacy_float` converters | A1 | D legacy CostItem reconciliation, float DTO, and float-column retirement complete | Platform Finance / Data Migration | CLOSED 2026-08-11; APIs, exports, tests, and marker deleted |
| PM desktop formatter legacy-float branch | A1 | D canonical decimal-string read DTO cutover complete | Desktop UI / PM Finance | CLOSED 2026-08-11; branch and marker deleted after canonical-text DTO cutover |

## 21. Permission Migration Plan

Use the repository's canonical permission catalog and policy evaluation; do not check role names.

| Current permission/path | Transitional mapping | Target permissions |
| --- | --- | --- |
| `report.view` for FinanceService | Grant finance read to intended existing PM roles before code switch | `finance.read`; `finance.read_sensitive` |
| `report.export` / `finance.export` | Retain alias only during rollout | `project_finance.export` |
| `cost.read` | Map to non-sensitive finance read | `cost.read` or canonical `finance.read` by query responsibility |
| `cost.manage` | Canonical ProjectCostEntry commands use target permissions; retain the umbrella only for unmigrated legacy CostItem callers until C.6-C.8 cutover | `project_cost.create`, `.update_draft`, `.submit`, `.approve`, `.post`, `.reverse` |
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
| [ADR-PF-004](../architecture_decisions/ADR-PF-004-financial-posting-and-reversal.md) | Posting and signed reversal model | ACCEPTED; PROJECT COST LEDGER IMPLEMENTED IN C.2 | A1/C ledger schema |
| [ADR-PF-005](../architecture_decisions/ADR-PF-005-rate-card-precedence.md) | Rate-card precedence | ACCEPTED; IMPLEMENTED INCLUDING COST-ENGINE CUTOVER (2026-08-05) | B rate-card implementation |
| [ADR-PF-006](../architecture_decisions/ADR-PF-006-approved-time-posting-trigger.md) | Approved-time posting trigger | ACCEPTED; PHASE C.4 SOURCE EVENT AND CONSUMER IMPLEMENTED | A2 contract/C consumer |
| [ADR-PF-007](../architecture_decisions/ADR-PF-007-procurement-financial-triggers.md) | Procurement commitment and actual triggers | ACCEPTED; PHASE C.5 PO/RECEIPT DELIVERY IMPLEMENTED | A2 contract/C consumer |
| [ADR-PF-008](../architecture_decisions/ADR-PF-008-approval-unit-of-work.md) | Approval and unit-of-work transaction model | ACCEPTED; INITIAL TRANSACTION CUTOVER IMPLEMENTED | A0 approval refactor |
| [ADR-PF-009](../architecture_decisions/ADR-PF-009-cost-code-ownership.md) | Cost-code ownership and hierarchy | ACCEPTED; PHASE B1 FOUNDATION IMPLEMENTED | B cost-code schema |
| [ADR-PF-010](../architecture_decisions/ADR-PF-010-billing-and-accounting-boundary.md) | Billing versus external accounting ownership | ACCEPTED 2026-08-11; PHASE E IN PROGRESS | E implementation |
| [ADR-PF-011](../architecture_decisions/ADR-PF-011-durable-integration-outbox-inbox.md) | Durable outbox/inbox ownership and delivery semantics | ACCEPTED; C.4/C.5 OWNED STORES AND CONSUMERS IMPLEMENTED | A2 decision/C consumers |

### Product questions

These are genuine product/ownership decisions. Questions mapped to A0/A1/A2 ADRs are blockers for those subphases; later questions do not block A0 security analysis:

1. Resolved by ADR-PF-003: hierarchical Tasks own WBS; a separate WorkPackage is deferred until a proven non-schedulable financial-node requirement exists.
2. Which budget dimensions are mandatory in the first release: cost code, WBS/task, department, period, funding source?
3. Are projects single transaction-currency, multi-currency with one reporting currency, or unrestricted multi-currency?
4. What monetary precision, rounding mode, and line-versus-total rounding rules are contractual?
5. Resolved by ADR-PF-005: cost and billing are separate; deterministic customer/project/resource/role-skill-department/organization precedence applies; overtime/holiday behavior is an explicit snapshotted modifier.
6. Resolved by ADR-PF-006: labor cost originates from an APPROVED period snapshot; LOCKED is an idempotent administrative control.
7. Resolved by ADR-PF-007: PO SENT creates commitment and receipt POSTED creates accrual actual; a later invoice reclassifies that accrual.
8. Implementation baseline: manual actuals are allowed through the canonical governed lifecycle; Finance Controller authority plus project-owner scope may post/reverse. Confirm whether tenants may disable manual actuals or require stricter amount/department separation-of-duties policy.
9. Which approval thresholds and separation-of-duties rules vary by tenant, organization, department, project, amount, and currency?
10. Resolved by ADR-PF-010: expense-claim capture belongs to a future Expenses owner. Canonical externally sourced posted expenses may be selected for billing.
11. Resolved by ADR-PF-010: first release supports T&M, fixed-price schedules/milestones, and cost-plus preparation only. PM does not issue official invoices.
12. Resolved by ADR-PF-010: contract, billable, externally invoiced/paid, and profitability projections are sufficient; statutory revenue recognition remains external.
13. Resolved by ADR-PF-010: use vendor-neutral `project_billing_preparation.v1` durable delivery and acknowledgement/reconciliation contracts; ERP adapters remain outside PM.
14. Resolved by ADR-PF-010: closed periods reject new preparation; corrections use linked reversal/replacement preparations in an open period.
15. Resolved by ADR-PF-010: approved billing and reconciliation evidence is immutable/append-only, legal hold blocks deletion, and tenant policy has a seven-year default.

## 25. Final Recommendation

Proceed with the upgrade, but do not recreate the removed combined CostItem model. Phases A-C and
the clean C.9 cutover are complete. Phase D.1A-D.2 now provide canonical forecast persistence,
lifecycle, automatic ETC generation, durable source decisions, and governed atomic budget/forecast
and schedule change control. Continue to D.4 canonical finance read models before changing QML;
keep procurement commitments source-owned and project contract value behind its Phase E gate.
Item 7's planned-cost source
cutover remains explicitly blocked by planning
semantics and freshness ownership; do not force it or treat the new forecast aggregate as a
substitute for a real planning source.

Then build Project Finance as explicit PM-owned aggregates while preserving valid module ownership: Time supplies approved hours, Procurement supplies PO/receipt facts, Party supplies identities, Approval and Audit remain platform services, and external accounting owns official ledger/payment behavior. Because the application is pre-release with no client data, use direct canonical cutovers and do not add fallback, dual-write, alias, compatibility, or transition adapters.

The existing QML workspace is not a constraint. Redesign it to expose Financial Profile, Budget Versions, Planned Cost, Commitments, Posted Actuals, Forecast Versions, Change Control, and Billing Preparation as distinct lifecycle-aware sections. This backend-first sequence is the safest path from the current tested cost-reporting feature to a professional multi-tenant SaaS Project Finance capability without creating an unnecessary accounting application.
