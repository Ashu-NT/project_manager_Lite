# R6B Finance Workspace and Read Architecture

## 1. Status

**R6B CLOSED.** The six-destination shell,
destination-scoped loading, bounded Overview projection, bounded Actual and
Commitment lists, authoritative Finance audit projection, and the Budget,
Planned Cost, Forecast, Rate Card/Rate Line, Financial Change, Billing, and
Performance read cutovers are implemented. Financial Setup now uses its scoped
immutable Reader. Live PostgreSQL runtime-role/RLS/query-plan evidence,
responsive evidence, targeted invalidation, capability reconciliation, and the
forward-only legacy cleanup are complete.

## 2. R6A Decisions Applied

R6B preserves Finance ownership of approved Budget, Forecast, ETC/EAC, actual
cost, historical rates, and managerial commercial projections. Procurement
remains commitment authority; Time remains time-entry authority; Scheduling
remains schedule authority; Accounting remains invoice, tax, GL, receivable,
payment, bank, and statutory authority. The visible commercial terms are
Projected Commercial Revenue and Projected Commercial Margin. No Accounting
delivery command or state was added.

## 3. Final Finance IA

The production Finance workspace exposes exactly six primary destinations:

1. Overview
2. Planning
3. Costs
4. Performance
5. Commercial
6. Controls

They are direct Finance-local navigation items. A redundant single `Finance`
group header is intentionally not rendered; grouping is reserved for navigation
rails containing multiple meaningful groups.

## 4. Current-to-Target Navigation Map

| Former primary section | R6B destination / subsection |
|---|---|
| Summary | Overview / Summary |
| Budget Versions, Budget Lines | Planning / Budgets |
| Planned Costs | Planning / Planned Costs |
| Forecast | Planning / Forecast |
| Actuals | Costs / Actuals |
| Commitments | Costs / Commitments |
| Rate Cards | Costs / Rate Cards |
| Variance | Performance / Variance |
| Cash Flow | Performance / Cost Phasing |
| Reports | Performance / Reports |
| Billing | Commercial / Billing Preparation |
| Profitability | Commercial / Projected Profitability |
| Financial Profile | Controls / Financial Setup |
| Change Control | Controls / Change Control |
| Activity | Controls / Activity |

## 5. Read Architecture

Production entry now loads workspace metadata, the project selector shell, and
only the active destination/subsection. `destination_builder.py` is the current
destination orchestrator. Overview and Finance audit use immutable read facts.
Actuals and Commitments use existing bounded application queries. Billing,
Performance, and Financial Setup use destination-specific immutable read
contracts.

## 6. Query Contracts

Implemented contracts normalize and allowlist Actual and Commitment sorts and
bound page sizes. Overview accepts tenant, organization, project, and as-of.
Finance audit accepts module, selected project workspace, a bounded limit, and
an allowlist of Finance operation prefixes. Immutable page/filter/sort query
objects are implemented for Budget, Planned Cost, Forecast, Rate, Financial
Change, Billing, and Performance reads. Rates use separate card and line requests with bounded
pages, allowlisted sort keys, independent query state, card search/scope/status
filters, and line search/type/status/effective-status filters. An explicit line
`as_of` date supports historical effective-state queries; the current UI
defaults to the current business date. Financial Changes use independent
request and Impact queries with bounded pages, allowlisted sorts, stable ID
tie-breakers, and search/status/approval/apply-state/type filters. Billing owns
separate Schedule, Preparation, and Preparation Line requests. Performance owns
explicit as-of/range/granularity contracts for EVM, Variance, Cost Phasing, and
Reports. Audit archive paging remains outside the bounded latest-activity scope.

## 7. Reader Contracts

`FinanceOverviewReader` returns immutable scalar `FinanceOverviewFacts` and
does not mutate or commit. `SqlAlchemyFinanceSnapshotReader.read_overview_facts`
executes at most five statements. The enterprise audit repository projection
returns immutable audit entities through the Platform desktop DTO boundary and
performs one scoped statement. Budget, Planned Cost, Forecast, and Rates now use
dedicated SQL Readers returning immutable scalar facts with count/data query
pairs and stable ID tie-breakers. The Forecast Reader executes an independent
selected-version aggregate query; authoritative total ETC and line count never
depend on the visible line page. The Rate Reader uses a separate one-statement
selected-card projection and never invokes rate resolution or hydrates Rate
aggregates. The Financial Change Reader uses a two-statement request page, a
one-statement selected-request detail, and a two-statement selected-parent
Impact page. Approval, base-current, and applied-successor evidence are scalar
server projections; no Change aggregate is passed to QML. Billing uses bounded
profile/master/detail/line projections. Performance uses a scoped SQL Reader
for period facts and invokes existing EVM/Baseline authorities only through its
application query boundary. Financial Setup uses one immutable SQL projection
joining the scoped project/profile and optional scoped default cost code. Its
desktop query no longer depends on mutable profile or cost-code repositories.

## 8. Desktop API

`get_finance_overview()` maps Overview facts to decimal-string DTOs.
`get_commitment_summary()` now maps the same bounded facts and no longer builds
the full Finance snapshot. Actual and Commitment page APIs retain authoritative
totals and sort state. The Platform Enterprise Audit desktop API now supports
additive module, workspace, and operation-prefix filters. The Forecast desktop
endpoint maps immutable facts to decimal-string DTOs and exposes selected
parent evidence separately from paged line rows. The Rates endpoint maps
immutable card/line facts to desktop DTOs, preserves amounts as canonical
decimal strings with explicit currency, and exposes selected-card evidence
independently from paged lines. `get_change_workspace()` maps immutable request,
detail, and typed-Impact facts to Decimal-string DTOs and preserves nullable
governance/revision evidence. Billing and Performance expose destination-
specific typed endpoints; the removed monolithic desktop Finance surface is not
retained as a fallback.

## 9. Overview Architecture

Overview shows approved Budget, open Commitments, posted Actual, available
amount, approved Forecast ETC, EAC, and VAC. Budget/Forecast revision and as-of
evidence are serialized from authoritative facts. Missing approved authority is
shown as `Not approved` or `Not available`, not a fabricated zero.

## 10. Planning Architecture

Planning has Budgets, Planned Costs, and Forecast tabs and loads only the active
tab. All three use a paged/sorted immutable version Reader and an explicitly
selected-version, paged/sorted line Reader; no first row is silently selected.
Forecast master search/status/generation filters and line search/source filters
execute in SQL. Every Forecast count/data/detail statement carries explicit
tenant, organization, project, and selected-parent scope. The selected Forecast
summary carries authoritative ETC, currency, line count, revision, as-of,
generation, lifecycle, and row-version evidence.

## 11. Costs Architecture

Actuals and Commitments preserve server paging, deterministic server sorting,
authoritative totals, project scope, permissions, and source/lifecycle facts.
The Commitment summary uses bounded Overview facts. Rates now presents a
server-paged Rate Card master and independently server-paged selected-card line
detail. The effective merged scope is resolved in SQL: organization cards and
cards for the explicitly pinned project are visible and clearly labelled; no
client-side scope merge occurs. No Rate write action was exposed. The
manual-actual task selector still needs a server-backed option query before
scale closure.

The resolver precedence is project resource/customer, project resource,
project role/skill/department, organization resource, then organization
role/skill/department. Same-tier ambiguity remains fail-closed. Rate Cards are
the only Finance rate authority. Resource `hourly_rate` remains operational
resource metadata and no Resource command creates, supersedes, or deactivates a
Finance Rate Line. The `legacy_seeded` origin, legacy-card discriminator,
repository bridge, composition dependency, migration columns/index, and
behavioral tests are deleted. Approved labor postings retain immutable rate
snapshots and are never recomputed from a current Rate Card or Resource field.

## 12. Performance Architecture

EVM, Variance, Cost Phasing, and Reports are grouped under Performance and load
only the selected subsection. Visible `Cash Flow` terminology and its old
presentation state are removed; Cost Phasing never claims cash authority. The
bounded Reader applies tenant, organization, project, date-range, and
month/quarter granularity directly in SQL and returns Decimal facts. EVM remains
the single existing calculator authority until R6E and failures are converted
to truthful unavailable state after authorization; permission denials still
propagate. VAC and Budget Pressure remain distinct metrics with explicit sign
conventions. Reports require report authorization and expose authoritative
revision/as-of basis without loading the full Finance desktop snapshot.

## 13. Commercial Architecture

Commercial has Billing Preparation, Projected Profitability, and Accounting
Status. Projected profitability remains server permission-gated. Accounting
Status states that Accounting owns statutory outcomes and exposes no delivery
command. Billing Schedule and Preparation use bounded server tables and an
explicit selected-Preparation inspector. Durable Accounting integration status
and outcomes remain R6G work, not an R6B read-cutover blocker.

## 14. Controls Architecture

Controls has Financial Setup, Change Control, and Activity. Activity now uses
immutable Enterprise Audit evidence filtered in SQL by tenant, organization,
PM module, selected project workspace, and an allowlist of Finance operation
families. It no longer reconstructs pseudo-history from current cost entries.
The feed is explicitly the latest 100 events and fails deny-safe when
`audit.read` is unavailable. Financial Changes now use a bounded request
master, explicit ID selection, bounded selected detail, and bounded typed
Impact table. Approval and base/apply evidence are read-only projections. Cost
Codes remain command-side configuration; Financial Setup reads the profile and
default code in one immutable projection. Restriction management belongs to
R6C write UX, and Accounting integration status belongs to R6G.

## 15. Project Context

Finance retains a local explicit project selector. Project changes clear every
destination model, page, and selected version before loading only the active
destination. Selecting/opening a project elsewhere does not silently change
the Finance project.

## 16. Permission Projection

Backend services enforce `finance.read`, project visibility, sensitive Finance
permissions, profitability permission, and `audit.read` for immutable audit
evidence. QML does not grant access. Missing or failed audit authorization
returns no audit rows and never falls back to a broader feed. A destination-
level deny-safe capability matrix is covered by focused authorization tests. The
authoritative existing Rates policy is option B: both `finance.read` and
`finance.read_sensitive`, including project permission, are required; callers
without sensitive permission are denied the entire Rates destination by the
query service. QML visibility is not the security boundary.

## 17. Currency / Decimal Rules

Overview fails closed on source-currency mismatch. Canonical arithmetic remains
`Decimal`; desktop monetary values use canonical decimal strings and formatted
labels. Forecast, Rate line, Financial Change Impact, Billing, and Performance
amounts retain persisted currency and never
convert through `float`. Rate Cards do not invent a parent currency that is not
present in the authoritative schema; every line carries its persisted currency
and no cross-currency comparison is performed. QML performs no authoritative
Finance calculation. No FX conversion was introduced. Financial Setup projects
its persisted profile currency without conversion or cross-currency arithmetic.

## 18. As-of / Revision Semantics

Overview carries its as-of date, approved Budget identity/revision/approval
time, and approved Forecast identity/revision/as-of. Cost entries retain posting
and source facts; commitments retain source revision and dates. Rate lines
classify current, future, expired, open-ended, and inactive state against an
explicit Reader `as_of` when supplied; historical callers therefore do not
depend on the wall clock. Card and line row versions are projected explicitly.
All applicable R6B selected-parent contracts expose stable revision/as-of
evidence; later write-phase DTOs must preserve the same rule.

## 19. DataTable Standard

Actuals, Commitments, Budgets, Planned Costs, both Forecast tables, both Rates
tables, and both Financial Change tables use shared `DataTable` server mode.
Their authoritative sort state
resets page one
on sort changes, survives refresh/page changes, and exposes server counts
independent of the current page. Forecast master and line state are independent:
selecting a Forecast resets only the line page and clears stale detail/lines
before refresh. Rate card and line paging/filter/sort state is independent;
changing the selected card resets and clears only line state. R6B scalable
collections use authoritative server queries; non-tabular scalar profile,
metric, and report-definition surfaces are intentionally not paged.

## 20. Inspector Pattern

Forecast now has an ID-driven selected-version detail projection and bounded
line detail. Source decisions are deliberately not prefetched: the current UI
does not present a derivation inspector, and fetching every decision would
violate the bounded read contract. If that surface is added later it must use a
separate bounded selected-Forecast query. Rates has an ID-driven bounded
selected-card header and a separate paged line table; it does not fetch all
lines for header metadata. Financial Change and Billing Preparation use scoped
selected-parent inspectors. Cost Entry and Commitment inspector expansion is
deferred to their approved write-hardening phases; no ORM/domain aggregate is
passed into QML. Financial Change request selection is explicit,
resets only Impact paging, and clears stale detail/Impact rows before refresh.

## 21. Lazy Loading

Finance entry performs shell/project option loading and one active destination
query. Secondary tab changes load only the selected subsection. Production no
longer calls the monolithic `build_workspace_state()`. Destination/project
request generation is validated before applying a response.

## 22. Event / Invalidation Map

Project changes invalidate the shell and all Finance destinations. Task changes
invalidate Planning, Costs, and Performance. Budget changes invalidate Overview,
Planning, and Performance. Planned-cost changes invalidate Planning and
Performance. Billing preparation changes invalidate Commercial. Direct
mutations invalidate only their dependent loaded destinations; posted and
reversed actuals also invalidate Overview and Performance. Additional cross-
process/outbox invalidation belongs to later write/integration phases and must
not revive deleted emit-without-consumer signals.

## 23. Async Stale-Response Guards

The controller captures request generation, project ID, destination, and
subsection and rejects responses that no longer match. Project switches reset
selected budget/planned-cost/forecast/change/baseline IDs and pages. Budget,
Planned Cost, and Forecast selection is explicit and resets only its child-line
page. Forecast selection immediately clears stale selected detail and lines;
the request generation plus project/destination/subsection check rejects a
response after a newer selection or scope request. Organization changes
rebuild/revalidate the runtime-scoped controller and cannot reuse a selected
Forecast, Rate Card, or Financial Change from the previous scope. Rate and
Financial Change A -> B -> C selection are covered by the same request-
generation, project, destination, and subsection guard; only C may publish
selected detail/lines. Filter and project changes immediately clear
incompatible Rate/Change models and selection. Selected-parent request guards
also protect Billing Preparation detail and line responses.

## 24. Tenant / Organization / Project Security

Overview receives explicit tenant/organization/project scope and validates the
selected Project permission in the query service. Enterprise Audit always
applies repository tenant and organization scope plus selected project
workspace. Actuals and Commitments retain their service/repository scope. Budget,
Planned Cost, Forecast, Rate, and Financial Change count/data/detail statements
receive and enforce tenant, organization, project, and selected-parent scope. `finance.read` and
project visibility are checked before the Forecast Reader executes; Rates also
requires `finance.read_sensitive`. Financial Change Impact rows repeat direct
parent scope, and Task labels join through the already-scoped project identity.
Rate Line joins to Resource and Department
repeat tenant and organization scope so display/search joins cannot borrow
labels from another scope. New readers must preserve the same explicit scope
and project visibility. Billing, Performance, and Setup Readers follow the same
scope and project-permission boundary.

## 25. RLS Evidence

No RLS policy was weakened. The Forecast Reader was exercised against the
Docker PostgreSQL database through `app_runtime`, which is `NOSUPERUSER`,
`NOBYPASSRLS`, and owns no protected tables. Cross-tenant/organization Forecast
master access and direct foreign `project_finance_forecast_lines` access both
returned zero rows. The Rate Reader was validated through the same runtime role:
foreign tenant/organization cards return no rows, and direct attacks against
foreign Rate Card and child Rate Line tables return zero rows. The Financial
Change Reader was also validated through `app_runtime`: foreign request,
detail, and Impact reads and direct attacks against the foreign child Impact
table return zero rows. Runtime-role tests also cover Billing and Performance,
including direct foreign child-table attacks. The focused live R6B PostgreSQL
matrix is `15 passed` through `app_runtime`; no protected table is owned by that
role.

## 26. Responsive Results

The six-destination page uses the existing responsive SectionDetailPage and a
shared secondary tab bar with lazy content. Forecast uses a stacked full-width
master/detail layout rather than a permanently squeezing sidebar. Actual
offscreen QML instantiation passes at 1024x640, 1280x720, 1366x768, 1440x900,
and 1920x1080, with positive master/detail table width and no R6B-owned QML
warning. The stacked full-width Rates and Financial Change master/detail
surfaces pass the same five viewports without permanently crushing either
table. Billing passed the same five viewports. All four Performance sections
pass the same five-viewport offscreen matrix and Finance QML is lint-clean.

## 27. Performance Characterization

Overview is capped at five SQL statements. Enterprise Finance Audit is one
bounded SQL statement. Forecast pageable master reads use `COUNT + page` (two
Reader statements), selected summary uses one statement, and pageable line
reads use `COUNT + page` (two Reader statements). The selected Forecast query
path is at most six statements including authorization. Rate Card pages use
`COUNT + page` (two Reader statements), selected-card detail uses one, and Rate
Line pages use `COUNT + page` (two); counts are independent of total cardinality
and there is no Resource resolution fanout. There is no N+1 or hidden full-line
model. Financial Changes use fixed `COUNT + page` request reads, one selected-
detail statement, and fixed `COUNT + page` Impact reads. Approval evidence is
included in request/detail SQL and adds no governance query. Billing uses a
fixed `1 + 2 + 2 + 1 + 2` profile/master/line/detail statement envelope for a
fully selected workspace. Cost Phasing is bounded to at most six Reader
statements independent of row cardinality; EVM and Variance reuse their single
current authorities rather than introducing duplicate formulas. Inactive
destination suppression and shell-only entry are unit-tested. Financial Setup
is a single Reader statement with no aggregate hydration or second default-
cost-code lookup. Successful Finance mutations invalidate only dependent loaded
destinations; posted/reversed actuals also invalidate Overview and Performance.

## 28. PostgreSQL Query Evidence

The repository's existing Dockerized PostgreSQL 16 test environment is reused.
Representative runtime-role `EXPLAIN (ANALYZE, BUFFERS)` execution measured
approximately 0.14 ms for the Forecast master projection and 0.10 ms for the
line projection on the focused fixture. Both plans were bounded by `LIMIT`; the
existing scope, project/parent, cost-code, and task indexes cover the access
shape. The Rate master and line plans are also bounded by `LIMIT`, retain
explicit scope and parent predicates, and use the existing Rate Card
scope/project and Rate Line scope/parent indexes. Financial Change request and
Impact plans are bounded by `LIMIT`, include tenant/organization/project and
selected-parent predicates, and completed without evidence requiring a new
index. Billing has equivalent runtime-role scope, child-table denial, and
bounded plan evidence. Performance project/profile and Cost Phasing plans ran
through `app_runtime` at approximately 0.069 ms and 0.059 ms on the focused
fixture, with cross-scope profile/forecast/line reads denied. These small
fixtures are architecture evidence, not scale
benchmarks. No speculative index was added; final 10k/50k certification remains
an R6H gate.

## 29. Legacy Paths Removed

The 13-peer Finance primary navigation and Controls pseudo-activity based on
cost ledger rows are removed from production. The old Cash Flow presentation,
state, and application package are removed. Forecast no longer invokes an
aggregate snapshot/lifecycle builder. Rates no longer preloads cards, lines,
and Resources into a QML collection. Change Control no longer invokes
`build_change_lifecycle_views()` or old list APIs. Billing no longer invokes
the domain-aggregate workspace path. Performance no longer requests the full
desktop Finance snapshot.

The monolithic Finance presenter, old Forecast/Billing/analytics/lifecycle
builders and serializers, superseded desktop DTO collections, old desktop API
methods, obsolete DI dependencies, and stale tests were deleted after active
consumers moved. The Resource-to-Rate-Card seeding bridge and its schema were
also deleted. The fresh Alembic history contains no compatibility Rate Card
kind or `legacy_seeded` origin.

## 30. Forward-Only Production Invariant

No Finance compatibility read path is retained. Planned Cost, Forecast, Rates,
Financial Changes, Billing, and Performance each have one active desktop API,
presenter/controller, and QML path. `ProjectFinanceWorkspaceQuery` remains only
for distinct current setup/billing semantics; it is not an old/new fallback.
`FinanceService.get_finance_snapshot()` remains the canonical report/export and
cost-policy projection, not a desktop compatibility endpoint. The existing
binary-float EVM calculator remains the sole EVM authority until its R6E Decimal
replacement proves parity; R6E must delete it in the same cutover.

The PM route compatibility QML is not part of Finance read architecture. It is
the separately approved R0 deep-link migration contract and may be retired only
after its route dependencies are removed. No new Finance compatibility code may
be added under that exception.

## 31. Tests

Current targeted evidence covers shell/destination suppression; Overview,
Actual, Commitment, Budget, and Planned Cost regression; Forecast paging,
filters, allowed/default sorts, cross-page order, explicit selection,
authoritative parent totals, wrong-scope rejection, Decimal DTO serialization,
controller reset rules, and all five required Forecast viewport sizes. The
dedicated live PostgreSQL Forecast suite adds runtime-role statement bounds,
cross-scope parent/child denial, and query-plan inspection. Python compilation,
changed-Finance QML lint, PM CQRS Reader architecture, and `git diff --check`
are required at each focused closure run. Latest Forecast closure evidence is
`89 passed` for the focused Finance/Forecast/Planned Cost/controller/architecture
matrix (including rapid A/B/C stale-response rejection and organization-context
workspace refresh), `14 passed` for shared QML/runtime guardrails, and `3
passed` against live PostgreSQL. Targeted Python compilation and Finance
`qmllint` are clean.
Rates-focused evidence covers card/line scope, paging, filters, allowed/default
sorts, deterministic ties, effective dates, explicit selection, no first-row
selection, Decimal-string DTOs, sensitive-permission denial, page/reset rules,
rapid A/B/C stale-response rejection, read-only QML contracts, and all five
required viewports. The dedicated PostgreSQL Rates suite covers the
non-privileged runtime role, fixed 2/1/2 Reader statement counts, cross-scope
parent/direct-child denial, and bounded master/line plans. Historical snapshot
and resolver precedence characterization remains covered by the focused Rate
Card and approved-time labor tests.

Latest Rates closure evidence is `72 passed` across the focused Rates,
resolver, approved-time posting, Planned Cost/Forecast regression, controller,
organization-switch, and Reader-architecture tests, plus `3 passed` against live
PostgreSQL. Targeted Python compilation, Rates `qmllint`, canonical/generated
QML metadata parity, and the R6B-owned diff check are clean. Later destination
Reader, RLS, and final architecture gates are recorded below as complete.

Financial Change focused evidence covers explicit request/Impact scope,
bounded paging, filters, allowed/default sorts, deterministic ID ties, no first
auto-selection, selected-detail approval/base-current/apply evidence, typed
Budget/Forecast/Schedule facts, Decimal-string DTOs, permission denial,
project-switch reset, rapid A/B/C selection/filter rejection, read-only QML,
and all five viewports. The active destination facade is independently proven
not to call retired list APIs. The focused R6B regression matrix is `104 passed`;
the destination-only retirement assertion adds `1 passed`; shared QML
guardrails are `5 passed`; PM CQRS Reader architecture is `21 passed`; and live
PostgreSQL Change tests are `3 passed`. Targeted compilation, changed-QML
`qmllint`, and `git diff --check` are clean. No full PM suite was run.

Performance-focused evidence covers lazy subsection loading, tenant/org/project
and date-range forwarding, Decimal Cost Phasing facts, bounded SQL, wrong-scope
denial, EVM error containment after authorization, permission-denial
propagation, distinct VAC/Budget Pressure identities, and all four sections at
five supported viewports. Financial Setup evidence covers one-statement reads,
immutable facts, explicit wrong-scope denial, desktop serialization, and the
absence of repository fallback. The current focused query/controller/QML matrix
is `59 passed`. The Performance integration module subsequently passed live as
`3 passed`; the complete focused R6B PostgreSQL matrix is `15 passed`.

## 32. Billing Schedule / Preparation Read Cutover

**Status: COMPLETE.** The active Finance -> Commercial -> Billing destination
no longer calls the domain-aggregate `get_billing_workspace()` path, the
unbounded Schedule repository collection, or custom Preparation collection
blocks. It now calls `get_billing_read_workspace()` through
`ProjectFinanceWorkspaceQuery`, with `finance.read` and project permission
checks before any Reader statement executes.

The immutable read contract consists of a bounded scalar Billing Profile,
`BillingScheduleQuery`, `BillingPreparationQuery`, and
`BillingPreparationLineQuery`. Schedule, Preparation master, selected
Preparation detail, and Preparation Lines repeat tenant, organization, and
project predicates. The child Line query also joins the scoped parent
Preparation. Sort keys are allowlisted, direction is normalized, pages are
bounded to 200 rows, and every sort has a deterministic ID tie-breaker.

The controller owns independent page, sort, and filter state for Schedule,
Preparation master, and Preparation Lines. Preparation selection is explicit;
there is no first-row auto-selection. Selection resets only Line paging and
clears stale detail/Line models. Preparation filters clear incompatible
selection; Schedule filters do not reset Preparation state. Project switching
clears all Billing master/detail/line models and pages. Runtime organization
switching continues through the established fail-closed controller/context
rebuild. Request generation plus captured project/destination/subsection state
rejects rapid Preparation A -> B -> C responses so only C may publish.

The QML surface uses three shared `DataTable` instances with
`sortingMode: "server"`: Billing Schedule, Billing Preparations, and selected
Preparation Lines. Profile and selected detail are scalar cards; the tables and
pagination remain separate. The stacked full-width layout avoids a permanently
crushed master at 1024px and passed 1024x640, 1280x720, 1366x768, 1440x900,
and 1920x1080. Targeted `qmllint` is silent.

Billing Profile remains PM commercial setup, Schedule remains PM schedule
evidence, Preparation remains the governed PM handoff package, Source Lock
remains duplicate-source authority, and External Event remains append-only
Accounting outcome evidence. The selected detail includes Platform approval,
correction reference, authoritative total/line count, Source Lock aggregate,
and latest external outcome without loading all lines or locks. Line facts
preserve `approved_time`, `posted_cost`, `schedule_line`, and `adjustment`
source types and stored quantity/rate/markup snapshots; historical rates are
never re-resolved.

Delivery wording is deliberately conservative. `delivery_pending` and
`delivery_requested_at` mean only "Local handoff requested" and explicitly say
that no durable Accounting queue, delivery, or acknowledgement is evidenced.
Only a stored `ProjectBillingExternalEvent` is presented as an external
Accounting outcome. No PM Invoice aggregate, write action, handoff command,
human external-outcome mutation, Accounting delivery implementation, FX, mixed-
currency aggregation, or QML monetary calculation was added. Monetary values
remain `Decimal` through the Reader and canonical strings at the desktop
boundary with explicit currency.

Measured SQL is fixed: Profile `1`; Schedule `COUNT + page` (`2`);
Preparation master `COUNT + page` (`2`); selected detail `1`; Lines
`COUNT + page` (`2`). Latest Accounting outcome is joined into master/detail
and Source Lock summary into detail, adding `0` separate statements and no
N+1. Runtime-role PostgreSQL plans are bounded by `LIMIT` with scope/project or
parent predicates. Existing scope/project, due-date, preparation-parent,
Source Lock, and External Event access paths were sufficient for the focused
fixture, so no speculative index or migration was added.

Live PostgreSQL evidence ran through `app_runtime` (`NOSUPERUSER`,
`NOBYPASSRLS`, non-owner): cross-tenant and cross-organization reads and direct
attacks against Billing Profile, Schedule Line, Preparation, Preparation Line,
Source Lock, and External Event returned zero foreign rows. The live Billing
suite is `3 passed`. Billing/controller/viewport tests are `40 passed`; the
existing R6B destination/presenter regression is `52 passed`. Targeted Python
compilation passes. No full PM suite was run. The superseded Billing workspace
API, serializer/builder, aggregate read DTOs, monolithic presenter consumer, and
tests preserving that path are deleted.

## 33. Financial Setup Read Cutover

**Status: COMPLETE.** `FinanceSetupReader` returns immutable profile/control
facts from one tenant/organization/project-scoped statement and left-joins the
default cost-code label under the same scope. `ProjectFinanceWorkspaceQuery`
authorizes before resolving active scope and invoking the Reader. The old
`ProjectFinanceSetupRead` domain-entity wrapper, its file, and the workspace
query's profile/cost-code repository dependencies are deleted. Configuration
repositories remain only on current command-side services.

## 34. Known Deferred R6C-R6H Work

- R6C: Budget/Forecast/Financial Change write UX, approvals, and UoW cleanup.
- R6D: cost/rate/commitment write hardening.
- R6E: Decimal-only EVM replacement, final variance taxonomy, and canonical
  Cost Phasing semantic repair.
- R6F: Billing Profile/Schedule/Preparation writes and granular permissions.
- R6G: durable Accounting outbox, worker, adapter, identity, retry/quarantine,
  and external outcomes.
- R6H: final 10k/50k certification, exhaustive child-table RLS attacks, and
  final release-wide dead-code/document closure.

## 35. R6B Closure Decision

**R6B CLOSED.** All destinations use one active production read path, inactive
subsections remain lazy, scalable collections are bounded, selected-parent
reads are scoped, Performance and Setup satisfy immutable Reader gates, the
five-viewport matrix is green, and PostgreSQL runtime-role/RLS evidence is
green. There are zero accepted Finance compatibility paths waiting for later
cleanup. R6C-R6H retain only their explicitly distinct write, Decimal-EVM,
Accounting-integration, and scale-certification scopes.
