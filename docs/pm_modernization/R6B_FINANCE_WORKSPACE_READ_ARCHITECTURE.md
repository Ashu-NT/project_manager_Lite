# R6B Finance Workspace and Read Architecture

## 1. Status

**R6B NOT CLOSED.** Implementation is in progress. The six-destination shell,
destination-scoped loading, bounded Overview projection, bounded Actual and
Commitment lists, authoritative Finance audit projection, and the Budget,
Planned Cost, and Forecast master-detail read cutovers are implemented. Rates,
Financial Changes, Billing Schedule, Performance, and remaining inspector
cutovers remain blocking.

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
Actuals and Commitments use existing bounded application queries. Remaining
configuration/lifecycle/billing paths are documented below and must be replaced
before closure.

## 6. Query Contracts

Implemented contracts normalize and allowlist Actual and Commitment sorts and
bound page sizes. Overview accepts tenant, organization, project, and as-of.
Finance audit accepts module, selected project workspace, a bounded limit, and
an allowlist of Finance operation prefixes. Immutable page/filter/sort query
objects are implemented for Budget, Planned Cost, and Forecast master-detail
reads. Forecast has separate master and line requests with bounded pages,
allowlisted sort keys, search/status/generation/source filters, and independent
query state. Equivalent contracts are still required for Rate, Financial
Change, Billing Schedule, Billing Preparation, and audit archive paging.

## 7. Reader Contracts

`FinanceOverviewReader` returns immutable scalar `FinanceOverviewFacts` and
does not mutate or commit. `SqlAlchemyFinanceSnapshotReader.read_overview_facts`
executes at most five statements. The enterprise audit repository projection
returns immutable audit entities through the Platform desktop DTO boundary and
performs one scoped statement. Budget, Planned Cost, and Forecast now use
dedicated SQL Readers returning immutable scalar facts with count/data query
pairs and stable ID tie-breakers. The Forecast Reader executes an independent
selected-version aggregate query; authoritative total ETC and line count never
depend on the visible line page. Remaining configuration reads still hydrate
domain aggregates through repositories and therefore do not satisfy the final
R6B Reader gate.

## 8. Desktop API

`get_finance_overview()` maps Overview facts to decimal-string DTOs.
`get_commitment_summary()` now maps the same bounded facts and no longer builds
the full Finance snapshot. Actual and Commitment page APIs retain authoritative
totals and sort state. The Platform Enterprise Audit desktop API now supports
additive module, workspace, and operation-prefix filters. The Forecast desktop
endpoint maps immutable facts to decimal-string DTOs and exposes selected
parent evidence separately from paged line rows. Destination-specific typed
endpoints are still required for the remaining substantial collections.

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
The Commitment summary uses bounded Overview facts. **Blocking:** Rate Cards are
unbounded parents and Rate Lines preload visible cards/resources; both require
dedicated bounded readers. The manual-actual task selector also needs a
server-backed option query before scale closure.

## 12. Performance Architecture

Variance, Cost Phasing, and Reports are grouped under Performance. Visible
`Cash Flow` terminology has been removed; no cash authority was invented.
**Blocking:** Cost Phasing and report basis still request the full Finance
snapshot. Existing EVM/variance authority is preserved and its R6A defects stay
deferred to R6E; R6B must add defensive/unavailable presentation without
duplicating formulas.

## 13. Commercial Architecture

Commercial has Billing Preparation, Projected Profitability, and Accounting
Status. Projected profitability remains server permission-gated. Accounting
Status states that Accounting owns statutory outcomes and exposes no delivery
command. **Blocking:** Billing Schedule is unbounded, Billing Preparation needs
the shared table/inspector cutover, and Accounting outcomes/integration status
need a truthful bounded read model.

## 14. Controls Architecture

Controls has Financial Setup, Change Control, and Activity. Activity now uses
immutable Enterprise Audit evidence filtered in SQL by tenant, organization,
PM module, selected project workspace, and an allowlist of Finance operation
families. It no longer reconstructs pseudo-history from current cost entries.
The feed is explicitly the latest 100 events and fails deny-safe when
`audit.read` is unavailable. **Blocking:** Financial Changes and impacts remain
unbounded; Cost Codes/Restrictions and integration status need bounded reads.

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
level deny-safe capability matrix still needs final integration coverage.

## 17. Currency / Decimal Rules

Overview fails closed on source-currency mismatch. Canonical arithmetic remains
`Decimal`; desktop monetary values use canonical decimal strings and formatted
labels. Forecast master, detail, and line amounts retain persisted currency and
never convert through `float`. QML performs no authoritative Finance
calculation. No FX conversion was introduced. The remaining legacy
snapshot/configuration reads must receive the same cross-currency
characterization before cutover.

## 18. As-of / Revision Semantics

Overview carries its as-of date, approved Budget identity/revision/approval
time, and approved Forecast identity/revision/as-of. Cost entries retain posting
and source facts; commitments retain source revision and dates. Remaining list
DTOs must expose stable selected-parent revision/as-of evidence.

## 19. DataTable Standard

Actuals, Commitments, Budgets, Planned Costs, and both Forecast tables use
shared `DataTable` server mode. Their authoritative sort state resets page one
on sort changes, survives refresh/page changes, and exposes server counts
independent of the current page. Forecast master and line state are independent:
selecting a Forecast resets only the line page and clears stale detail/lines
before refresh. The remaining enterprise collections still use custom
collection sections and are not R6B complete.

## 20. Inspector Pattern

Forecast now has an ID-driven selected-version detail projection and bounded
line detail. Source decisions are deliberately not prefetched: the current UI
does not present a derivation inspector, and fetching every decision would
violate the bounded read contract. If that surface is added later it must use a
separate bounded selected-Forecast query. Final inspectors for Cost Entry,
Commitment, Rate Card, Financial Change, and Billing Preparation remain
blocking; no ORM/domain aggregate is passed into QML.

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
mutations refresh only the active destination. Forecast, actual, commitment,
rate, and financial-change post-commit invalidation contracts remain to be
completed without reviving previously deleted emit-without-consumer signals.

## 23. Async Stale-Response Guards

The controller captures request generation, project ID, destination, and
subsection and rejects responses that no longer match. Project switches reset
selected budget/planned-cost/forecast/change/baseline IDs and pages. Budget,
Planned Cost, and Forecast selection is explicit and resets only its child-line
page. Forecast selection immediately clears stale selected detail and lines;
the request generation plus project/destination/subsection check rejects a
response after a newer selection or scope request. Organization changes
rebuild/revalidate the runtime-scoped controller and cannot reuse a selected
Forecast from the previous scope. Selected-parent request tokens for future
Rate and Billing inspectors remain blocking.

## 24. Tenant / Organization / Project Security

Overview receives explicit tenant/organization/project scope and validates the
selected Project permission in the query service. Enterprise Audit always
applies repository tenant and organization scope plus selected project
workspace. Actuals and Commitments retain their service/repository scope. Budget
Planned Cost, and Forecast count/data/detail statements receive and enforce
tenant, organization, project, and selected-parent scope. `finance.read` and
project visibility are checked before the Forecast Reader executes. New readers
must preserve the same explicit scope and project visibility.

## 25. RLS Evidence

No RLS policy was weakened. The Forecast Reader was exercised against the
Docker PostgreSQL database through `app_runtime`, which is `NOSUPERUSER`,
`NOBYPASSRLS`, and owns no protected tables. Cross-tenant/organization Forecast
master access and direct foreign `project_finance_forecast_lines` access both
returned zero rows. Runtime-role negative evidence remains blocking for later
R6B Readers as they are introduced.

## 26. Responsive Results

The six-destination page uses the existing responsive SectionDetailPage and a
shared secondary tab bar with lazy content. Forecast uses a stacked full-width
master/detail layout rather than a permanently squeezing sidebar. Actual
offscreen QML instantiation passes at 1024x640, 1280x720, 1366x768, 1440x900,
and 1920x1080, with positive master/detail table width and no R6B-owned QML
warning. Remaining table cutovers still require their own viewport evidence.

## 27. Performance Characterization

Overview is capped at five SQL statements. Enterprise Finance Audit is one
bounded SQL statement. Forecast pageable master reads use `COUNT + page` (two
Reader statements), selected summary uses one statement, and pageable line
reads use `COUNT + page` (two Reader statements). The selected Forecast query
path is at most six statements including authorization. There is no N+1 or
hidden full-line model. Inactive destination suppression and shell-only entry
are unit-tested. Statement counts for the remaining Costs, Performance,
Commercial, and Controls cutovers remain incomplete.

## 28. PostgreSQL Query Evidence

The repository's existing Dockerized PostgreSQL 16 test environment is reused.
Representative runtime-role `EXPLAIN (ANALYZE, BUFFERS)` execution measured
approximately 0.14 ms for the Forecast master projection and 0.10 ms for the
line projection on the focused fixture. Both plans were bounded by `LIMIT`; the
existing scope, project/parent, cost-code, and task indexes cover the access
shape. This small fixture is architecture evidence, not a scale benchmark. No
speculative index was added; final 10k/50k certification remains an R6H gate.

## 29. Legacy Paths Removed

The 13-peer Finance primary navigation and Controls pseudo-activity based on
cost ledger rows are removed from production. The visible Cash Flow name is
removed. The active Forecast destination no longer invokes the aggregate
snapshot forecast builder or lifecycle collection builder, and its legacy card
collection was replaced in place by two server-mode tables. No duplicate
Finance route/workspace was added.

## 30. Compatibility Paths Retained

`presenters/financials/workspace_builder.py`, its legacy Forecast builder,
Forecast lifecycle builder calls, and
`ProjectFinancialsWorkspacePresenter.build_workspace_state()` are retained only
because the monolithic compatibility path and focused legacy delegation tests
still consume them. The production Forecast destination has zero dependency on
`get_cost_forecast()`, `list_forecast_versions()`, or
`list_forecast_lines()`. `ProjectFinanceWorkspaceQuery` still powers remaining
configuration reads. **DELETE AFTER CUTOVER:** remove these compatibility
consumers and then delete the obsolete Forecast builders/API methods with the
monolithic workspace method after every destination-specific Reader is proven.
They are temporary and must not survive R6B closure.

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
The R6B-owned diff check is clean; repository-wide diff checking is temporarily
blocked by a concurrent Platform test edit with a trailing blank line. Broader
Finance, PM, later-reader RLS, and final architecture gates remain pending.

## 32. Known Deferred R6C-R6H Work

- R6C: Budget/Forecast/Financial Change write UX, approvals, and UoW cleanup.
- R6D: cost/rate/commitment write hardening.
- R6E: Decimal-only EVM replacement, final variance taxonomy, and canonical
  Cost Phasing semantic repair.
- R6F: Billing Profile/Schedule/Preparation writes and granular permissions.
- R6G: durable Accounting outbox, worker, adapter, identity, retry/quarantine,
  and external outcomes.
- R6H: final 10k/50k certification, exhaustive child-table RLS attacks, five-
  viewport closure, and final dead-code/document closure.

## 33. R6B Closure Decision

**R6B NOT CLOSED.** Blocking remediation is: replace all remaining unbounded
configuration/lifecycle/billing collections with scoped immutable Readers and
server query state; add selected-parent bounded inspectors; eliminate full
snapshot use from destination reads; complete targeted invalidation; capture
PostgreSQL/RLS/query-plan and five-viewport evidence; delete the explicitly
marked monolithic compatibility paths; and pass the full R6B exit gate.
