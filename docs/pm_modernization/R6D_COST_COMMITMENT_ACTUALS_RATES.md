# R6D Cost, Commitment, Actuals, and Rates

## 1. Status

**R6D-A: COMPLETE - characterization and implementation design only.**

R6C remains closed. No R6D production behavior was changed during R6D-A. No R6E, R6F, R6G, or R6H work was started. This document records the repository state inspected on 2026-09-08 and is the authority for starting R6D-B.

## 2. Scope

R6D owns the enterprise authority and governed write architecture for:

- Finance Rate Cards and effective-dated Rate Card Lines.
- Manual and source-derived `ProjectCostEntry` actuals.
- Approved-time labor valuation and posting evidence.
- Procurement-owned commitment projections consumed by Finance.
- Cost approval, posting, reversal, transaction, security, event, and UI hardening.

## 3. Non-Scope

R6D does not reopen Budget, Forecast, Financial Change, or Financial Setup governance closed by R6C. It does not own TimeEntry work truth, Procurement Purchase Order lifecycle, Resource capacity, Scheduling, billing writes, Accounting delivery, invoices, tax, GL, AR/payment, payroll, HR compensation, FX conversion, EVM formula replacement, final variance taxonomy, or cost-phasing semantic redesign.

## 4. R6C Invariants Preserved

- Typed Finance commands cross an outward command boundary and run in a fresh operation UoW.
- Application services remain transaction-neutral; one outer owner commits and post-commit invalidation follows.
- Platform Approval remains the governed decision authority where configured.
- Finance uses one active read/controller/QML path per R6B destination.
- Tenant and organization context is mandatory and PostgreSQL RLS remains defense in depth.
- Posted monetary facts are immutable; corrections use new evidence rather than rewriting history.
- No pre-release compatibility architecture is accepted as permanent production code.

## 5. Finance Cost Authority Map

| Business fact | Authoritative owner | PM Finance representation | Mutation authority |
|---|---|---|---|
| Financial rates | PM Finance | `ProjectRateCard`, `RateCardLine` | PM Finance governed commands |
| Actual cost | PM Finance | Posted/reversed `ProjectCostEntry` ledger facts | PM Finance posting/reversal services |
| Worked hours and approval | Platform Time | Approved TimeEntry event snapshot | Time only; Finance consumes |
| Labor valuation | PM Finance | `ApprovedTimeLaborPosting` plus posted cost entry | Finance integration consumer |
| Purchase Order lifecycle | Inventory/Procurement | Source events only | Procurement only |
| Project commitment | Procurement source, Finance projection | `ProjectCommitment`, lines, revisions, matches | Finance consumer; read-only to Finance users |
| Resource identity/capacity | PM Resource | Referenced resource metadata | Resource capability |
| Statutory/receivable truth | Accounting | External outcome only | Accounting only |

## 6. Rate Card Domain

`domain/financials/rate_cards.py` defines `ProjectRateCard` with tenant, organization, optional project scope, name, card version, active state, and audit timestamps. A null project means organization scope. Its current lifecycle is create and deactivate; there is no explicit successor/predecessor revision chain, metadata edit, or reactivation operation.

`RateCardLine` stores card scope, cost/billing rate type, unit, `Decimal` amount, currency, effective date range, active state, optimistic version, and audit timestamps. Selection can be resource-specific, resource/customer/contract-specific, or dimensional by role, skill, and department. Overtime, weekend, and holiday multipliers are Decimal values. Domain validation rejects negative values, invalid date ranges, unpaired customer/contract selectors, selector-less lines, and ambiguous resource-plus-dimensional definitions.

Persistence uses `project_finance_rate_cards` and `project_finance_rate_card_lines`, canonical financial numeric columns, scoped foreign keys, tenant/organization RLS classification, and deterministic list indexes.

## 7. Rate Resolution

`application/financials/rate_cards/rate_card_resolver.py` and `rate_card_precedence.py` are the current authority. Resolution is active and effective-date constrained, with this exact precedence:

1. Project resource plus customer/contract.
2. Project resource.
3. Project dimensional match; the line matching the most role/skill/department dimensions wins.
4. Organization resource.
5. Organization dimensional match; most matching dimensions wins.

Equal specificity is rejected as `RATE_CARD_AMBIGUOUS_SELECTION`; no row is selected arbitrarily. No applicable line is `RATE_CARD_NO_APPLICABLE_RATE`. A required but unavailable modifier is `RATE_CARD_MODIFIER_NOT_CONFIGURED`. There is no Finance fallback to `Resource.hourly_rate`.

Current production consumers are approved-time labor posting, planned-cost snapshot generation, billing-preparation approved-time valuation, and `LaborCostEngine` reporting/EVM inputs. Manual Actual accepts an entered monetary fact and does not resolve a labor rate. Forecast consumes planned-cost evidence rather than establishing another rate authority.

## 8. Historical Rate Snapshot

`RateSelectionSnapshot` captures rate money, card ID, line ID, card version, origin, precedence, effective date, resolved timestamp, and optional modifier/multiplier. `ApprovedTimeLaborPosting` persists rate amount/currency, card/line IDs, card version, precedence, effective date, hours, work date, actual/reversal entry references, source revision/hash, and timestamps.

Posted cost rows and labor-posting rows are database-protected against destructive historical mutation. Retroactive card edits therefore do not rewrite posted labor amounts. The evidence is incomplete for forensic reconstruction because the labor posting does not persist a distinct Rate Line version or the resolved modifier/multiplier. R6D-B/D must extend the snapshot contract before relying on mutable line history.

## 9. Resource Rate Boundary

Remaining `Resource.hourly_rate` uses belong to Resource editors/import/listing, project-resource planning, and assignment-option presentation. They are valid operational/planning metadata, not Finance financial-rate authority.

`application/financials/utils/helpers.py::resolve_rate()` and its callers in older ledger/cost-phasing/service calculations still expose float-based project/resource-rate fallback semantics. These are superseded Finance authority candidates. R6D-G must delete them once each active consumer is migrated or prove that a caller has a distinct non-financial semantic. No bridge back into canonical posting is permitted.

## 10. ProjectCostEntry Domain

`ProjectCostEntry` contains tenant, organization, project, description, kind, signed Decimal amount, transaction currency/date, cost code, optional task/resource, source module/type/ID/line/revision/content hash/posting purpose/idempotency, optional base amount/currency and FX snapshot, posting date and financial period, reversal links, row version, lifecycle actors/timestamps, and rejection evidence.

Kinds are `actual`, `adjustment`, and `reversal`. Statuses are `draft`, `submitted`, `approved`, `posted`, and `reversed`. ORM constraints enforce legal kind/sign combinations, lifecycle posting snapshots, positive exchange rate, versioning, scoped project/cost-code/period/reversal references, source indexes, idempotency uniqueness, and one reversal per original entry.

## 11. Cost Lifecycle

The interactive lifecycle is:

`draft -> submitted -> approved -> posted -> reversed`

Rejection returns a submitted entry to a non-posted state according to the domain method and records actor/time/reason. Drafts may be updated or deleted. Posted and reversed facts are protected by domain rules and database triggers. Canonical actual queries include only status `posted` and `reversed`; draft, submitted, and approved entries do not contribute actual cost. The signed reversal offsets its original while preserving both facts.

No canonical actual aggregation was found reading TimeEntry or Purchase Order rows directly. Analytical labor reporting that estimates cost from hours and a currently effective rate is not ledger truth and must remain clearly separated until R6E replaces that path.

## 12. Manual Actual Workflow

The desktop boundary has typed commands for create, update draft, versioned lifecycle actions, approve/reject, post, and reverse. The QML editor uses bounded paged Project, Task, and Cost Code selectors; no high-cardinality preload is introduced.

Current QML supports create, submit, approve/reject, post, and reverse. Backend update/delete-draft operations exist but are not exposed consistently. After R6D-C, actions must be permission-aware as well as state-aware, refresh authoritative pages after success, clear stale selection, and preserve bounded selectors.

## 13. Cost Correction / Reversal

A posted entry is not edited or deleted. Correction creates a signed negative reversal linked to the original, marks the original reversed, and permits a separate replacement/new entry when required. A partial unique constraint prevents multiple reversal entries for one original, and a nested transaction currently translates a concurrent uniqueness race.

Search found no supported production path that directly updates or deletes posted monetary fields. Database guards reject such attempts even if service checks are bypassed.

## 14. Posting Semantics

Posting captures transaction amount/currency, base amount/currency, exchange-rate value/date/source/captured time, posting date, financial period, posted actor/time, cost code, project/task/resource references, and source evidence in the same transaction as lifecycle transition and audit/event collection.

Manual posting may accept an explicit existing FX snapshot contract. R6D must not add an FX provider. Source-derived labor and commitment flows currently fail closed when currencies differ and no authoritative conversion evidence exists.

## 15. Approved-Time Flow

The implemented flow is:

1. Time approves a TimesheetPeriod and builds immutable approved-entry facts.
2. Time writes `platform_time.time_entry.approved.v1` to its financial outbox in the approval transaction.
3. The dispatcher leases an outbox batch and opens the Finance inbox delivery.
4. A fresh PM worker UoW validates scope and source revision, resolves the effective cost rate, creates posted/reversal facts and `ApprovedTimeLaborPosting`, marks inbox delivery processed, and commits once.
5. Domain events are published for view invalidation only after the durable commit; the Time outbox is then marked published.

Corrections chain to the latest source revision, reverse the previous posted cost, and post the corrected fact atomically.

## 16. Time/Finance Ownership

Time owns worked hours, work date, assignment/work-allocation identity, and approval state. Finance consumes an immutable approved snapshot and owns rate selection, valuation, financial period validation, posted cost, and historical rate evidence. No Finance mutation of TimeEntry was found.

## 17. Labor Rate Resolution

The Finance consumer resolves a cost rate for the source work date and `HOUR` unit after validating tenant, organization, active project financial profile, default cost code, resource/task dimensions, and an open integration period. It uses the canonical Rate Card resolver, not resource hourly-rate metadata. Amount is Decimal hours multiplied by Decimal rate and rounded by the `Money` value object.

## 18. Labor Idempotency

Time computes a canonical content hash, skips identical source state, increments aggregate revision, and records correction ancestry. Delivery is protected by outbox event identity, Finance inbox consumer/event/dedupe uniqueness, source revision/hash checks, approved snapshot uniqueness, labor-posting uniqueness, and cost-entry idempotency uniqueness.

Exact replay is a no-op. A stale or conflicting revision is rejected/quarantined rather than reposted. The worker transaction includes Finance facts and inbox completion, so a failure cannot durably acknowledge an incomplete posting.

## 19. Rate-Not-Found Behavior

Missing or ambiguous rates never post zero. Resolution raises a typed error. The dispatcher rolls back the operation, records retry state, and eventually records durable failure/quarantine under the inbox/outbox policy. The operational gap is not correctness but visibility and remediation UX: R6D-D must expose enough evidence to diagnose, correct the rate configuration, and replay safely.

## 20. Commitment Source Authority

Inventory/Procurement owns Purchase Orders, lines, approval/state changes, receipt acceptance, closure, and cancellation. It emits financial events only for project-linked source data and relevant PO states (`sent`, `partially_received`, `fully_received`, `closed`, `cancelled`). Accepted receipt lines produce separate actual-cost evidence.

Finance imports neutral event contracts and does not import Procurement repositories or mutate PO aggregates. This modular boundary is correct and must remain.

## 21. Finance Commitment Projection

Finance stores a `ProjectCommitment` header per source PO, `ProjectCommitmentLine` rows, immutable source-revision snapshots, and immutable `ProjectCommitmentMatch` evidence. Projection fields include tenant/organization/project, PO/line/reference identity, supplier/site, task and cost code where resolved, quantity/unit price, amount/currency, optional base/FX snapshot, source state/revision/hash/idempotency, matched amount, row version, and audit timestamps.

Line amount is canonical quantity multiplied by `MonetaryRate`, then rounded. Open amount is non-negative amount minus matched amount, and closed/cancelled lines have zero open amount. Historical fact reads may retain closed lines while open-total reads exclude closed/cancelled lines; these are distinct valid semantics.

## 22. Commitment Idempotency

Procurement emits monotonically revised, content-hashed line events and skips identical state. The Finance inbox rejects stale aggregate delivery and uses exact replay as a no-op. The service additionally verifies latest source revision, hash, ordering, and correction continuity.

Database uniqueness protects the source PO header, source PO line, line revision, idempotency key, receipt match, and one original match per cost entry. Receipt actual creation plus commitment matching and inbox completion share one worker UoW.

## 23. Commitment / Actual Distinction

A commitment is expected/open commercial obligation projected from Procurement. A receipt-derived `ProjectCostEntry` is posted actual cost. Receipt matching reduces open commitment while retaining both audit histories. Overview aggregation must present commitments and actuals separately and must not add the same received value as both open commitment and actual.

## 24. Current Readers

| Destination | Current contract | Paging/filter/sort | Detail and SQL shape |
|---|---|---|---|
| Rates | `SqlAlchemyFinanceRateReader` | Server paging; search/scope/status/effective filters; allowlisted sorts; ID tie-break | Cards count+page = 2 statements, selected card = 1, lines count+page = 2; PostgreSQL test evidence exists |
| Actuals | Scoped `ProjectCostEntryRepository.list_for_project` projection | Server paging, status and allowlisted sort; ID tie-break; no broad search/source/date/currency filters | Current-page DTO is selected detail; count+page = 2, stale-page normalization can requery to 4 |
| Commitments | Scoped `ProjectCommitmentRepository` projection | Server paging and allowlisted sort; ID tie-break; limited filters | Current-page DTO is selected detail; count+page = 2, stale-page normalization can requery to 4 |

All page sizes are bounded, currently capped at 200. R6D must preserve authoritative server sorting and tenant/organization/project predicates. Dedicated Actual and Commitment detail readers are recommended only where write UX requires stable detail beyond the current page.

## 25. Current Desktop/QML Writes

Actuals have typed desktop commands and dialogs for creation and lifecycle decisions. UI row actions are currently derived mainly from lifecycle status; `New Manual Actual` is displayed without a complete effective-capability contract. Backend enforcement remains fail-closed, but presentation is not yet deny-safe. Draft edit/delete capability exists below QML and should either be exposed properly or deleted if product policy rejects it.

Commitments are intentionally read-only in Finance UI. R6D must not add PO/commitment editing.

Rates have authoritative R6B master-detail reads but no complete desktop/controller/QML command UX. Existing service operations are create card, deactivate card, add line, update line monetary/effective/modifier values, and deactivate line. Missing product operations include governed metadata revision/successor behavior and a complete capability-safe UI.

## 26. Transaction Ownership

Desktop Rate, Cost, and Commitment mutations are composed through `FinanceGovernedServicePort` and the R6C `FinanceGovernanceCommandBoundary`. The target remains typed command -> boundary -> fresh UoW -> transaction-neutral service -> one commit -> post-commit invalidation.

No application-level direct `commit()` was found in the R6D services. Two `session.rollback()` calls remain in `cost_entry_service.py` (around current lines 517 and 1179); these can abort an outward-owned transaction and are R6D-C P1 debt. `begin_nested()` remains in cost reversal and commitment source/match race handling. A savepoint is acceptable only as an explicitly documented local uniqueness-race translator that never commits or owns the outer transaction.

## 27. Background Consumer Transactions

Approved-time and Procurement consumers correctly use worker-specific fresh UoWs rather than desktop command architecture. Dispatchers claim durable outbox work, then atomically write Finance facts, inbox state, audits, and domain events before one worker-owned commit. Failures roll back and retain retry/quarantine evidence. Post-commit invalidation is not emitted before durable success.

The workers normally execute through the application runtime database role and scoped session context. Their audit actor is a hardcoded integration identity rather than a first-class service principal. R6D-D/E must strengthen identity without forcing workers through interactive-user permissions.

## 28. Permissions

Actual permissions are already separated:

| Operation | Permission |
|---|---|
| Read Finance | `finance.read` |
| Read sensitive labor/rates | `finance.read_sensitive` in addition to Finance read |
| Create manual actual | `project_cost.create` |
| Edit/delete draft | `project_cost.update_draft` |
| Submit | `project_cost.submit` |
| Approve/reject | `project_cost.approve`, or Platform `approval.request`/`approval.decide` in governed mode |
| Post | `project_cost.post` |
| Reverse | `project_cost.reverse` |

Rate management currently relies on broad `finance.manage`; R6D-B should introduce narrowly named rate prepare/manage/activate permissions if that matches the existing role catalog convention. Commitment user mutations are not authorized because Finance does not own them. All services additionally enforce project-scoped authorization where applicable.

## 29. Approval / SoD

When `PM_GOVERNANCE_MODE=required`, cost approval creates a Platform Approval request. Platform Approval denies a requester deciding their own request. Approval and posting are separate permissions and actions.

When governance is disabled, a holder of `project_cost.approve` can directly approve their own submitted manual actual; no local self-approval guard was found. The enterprise target is deny self-approval consistently for governed monetary actuals, preferably through the canonical Platform Approval path, while retaining a documented break-glass policy only if product governance explicitly requires it.

## 30. Event / Invalidation Architecture

Typed domain events feed post-commit invalidation:

- Any cost event invalidates the cost-entry list.
- Posted or reversed actual events invalidate Overview, Performance, and Commercial financial views in addition to Costs.
- Commitment changes invalidate Overview, Planning, Costs, Performance, and Commercial.
- Rate changes invalidate Rate views. R6D must add only proven live dependencies; posted historical facts must never be recomputed on rate invalidation.

Background consumers collect events inside their UoW and publish invalidation after commit. This architecture is canonical.

## 31. cost_entries_changed Reconciliation

No production producer or consumer of `cost_entries_changed` remains. Architecture tests identify it as forbidden/retired, and zero-consumer cleanup tests assert its absence. Typed cost-entry domain events and the R6B view-invalidation map replaced it.

Decision: do not restore the signal. Any stale test expecting it must be deleted or migrated to canonical event assertions. No current stale production path was found.

## 32. PostgreSQL/RLS

R6D-owned or directly related transport tables are:

- `project_finance_rate_cards`
- `project_finance_rate_card_lines`
- `project_cost_entries`
- `project_approved_time_labor_postings`
- `project_commitments`
- `project_commitment_lines`
- `project_commitment_source_revisions`
- `project_commitment_matches`
- `project_finance_inbox_receipts`
- `platform_time_financial_outbox`
- `inventory_procurement_financial_outbox`

These tables carry direct tenant/organization scope and are classified by the baseline RLS helpers. Fresh PostgreSQL migration installs and forces policies. Integration infrastructure separates bootstrap admin, schema owner, and `app_runtime`; runtime is `NOSUPERUSER`, `NOBYPASSRLS`, does not own protected tables, and receives only runtime DML grants. Runtime session hooks install the application's actual tenant/organization context.

R6D-specific direct child attack tests are incomplete. R6D-F must attempt cross-scope INSERT/UPDATE/DELETE through `app_runtime` for Rate Lines, cost/reversal references, labor postings, commitment lines/revisions/matches, and inbox rows, including foreign-parent IDs. Existing composite scoped foreign keys are helpful but are not a substitute for executable RLS evidence.

## 33. Money / Decimal

Authoritative domain and persistence use Decimal-backed `Money`, `MonetaryRate`, and quantities with canonical `Numeric(19,4)` money precision and higher precision for rates/quantities. Labor cost uses Decimal hours times Decimal rate and `Money.rounded()`. Commitment amount uses `MonetaryRate.apply(quantity).rounded()`.

Active analytical/reporting debt remains: `LaborCostEngine` and `finance_models.py` convert monetary/rate results to float, and older cost-phasing/ledger helpers expose float rate fallback. These paths must not become posting authority. R6D-G should delete superseded rate helpers; authoritative EVM/reporting formula replacement remains R6E.

QML `Number()`/`toFixed()` calls are acceptable only for display formatting and non-authoritative percentages/versions. No JavaScript monetary calculation may feed a write command.

## 34. Currency

Every authoritative amount and rate has explicit currency. Posting stores transaction and base snapshot evidence where available. Project totals select transaction amount when it matches project currency, otherwise base amount only when that matches; unresolved mixed currency fails closed rather than being silently added.

Approved-time and Procurement integrations reject cross-currency valuation when no enterprise FX evidence exists. R6D will not implement FX or reporting currency. Existing explicit posting snapshots remain supported but are not expanded into an FX subsystem.

## 35. Performance

- Rate card/line reads have proven bounded 2/1/2 statement shapes and PostgreSQL `EXPLAIN` coverage.
- Actual and Commitment masters normally execute count plus page (2 statements); stale-page correction can execute a second count/page pair.
- Manual Actual lookup selectors are paged and bounded.
- Batched rate resolution fetches resource context and candidate lines instead of querying once per row; multi-date resolution reuses a candidate set.
- Time outbox construction batches work-allocation lookup; dispatch defaults to bounded batches.
- Approved-time and Procurement ingestion perform several scoped locks/lookups per event. Exact PostgreSQL statement budgets are not yet established and belong to R6D-F.

No index is added during characterization. Query plans must prove a need first.

## 36. Scale Risks

- Actual and Commitment lists lack complete search/date/source/status filters and stable selected-detail reads for large ledgers.
- Stale-page normalization can double list statement count.
- `LaborCostEngine` loads project tasks, assignments, resources, and rates into memory; it is project-bounded but not page-bounded.
- Full Finance snapshot/report paths can materialize large project collections and aggregate in Python.
- Rate-line ambiguity and overlap are checked in application code; concurrent line writes need PostgreSQL race evidence.
- Integration throughput and lock contention at large approved-time/receipt batches are unmeasured.
- Rate write UI must use paged selectors and must not preload resources, departments, skills, customers, or contracts.

## 37. P0 Findings

No P0 defect is proven in the inspected current path. Canonical posting is scoped, idempotent, immutable, and fail-closed; Procurement remains authoritative for POs; historical labor postings are not recomputed after rate changes.

R6D-F must still prove this under hostile PostgreSQL child writes and concurrent replay before R6D closes. A failure of those tests would be promoted to P0 immediately.

## 38. P1 Findings

1. `ProjectCostEntryService` performs direct session rollback inside an outward-owned transaction at two locations, violating transaction neutrality.
2. Rate Lines can be updated in place without a formal successor/revision lifecycle; immutable postings survive, but historical rate-definition reconstruction is weaker than enterprise audit expectations.
3. Approved labor evidence lacks distinct Rate Line version and applied modifier/multiplier fields.
4. Actual QML actions are lifecycle-driven rather than fully permission/capability-driven, despite fail-closed backend checks.
5. Direct self-approval remains possible when Platform governance is disabled and a user has cost-approval permission.
6. Background workers use a hardcoded integration actor instead of a first-class auditable service principal.
7. R6D child-table RLS and foreign-parent negative tests are not yet comprehensive.
8. Current-rate float analytical labor cost can be mistaken for historical ledger actual; it must remain non-authoritative and be replaced in R6E.

## 39. P2 Findings

1. Rate write desktop/controller/QML coverage is incomplete.
2. Actual draft edit/delete exists in backend contracts but is not consistently exposed in QML.
3. Actual and Commitment masters have limited server filters and no dedicated selected-detail query.
4. Rate permissions are broad (`finance.manage`) rather than operation-specific.
5. Rate cards lack a governed metadata/successor/reactivation design.
6. Resolver iteration includes an unused precedence level beyond the five implemented classifiers.
7. Stale-page list normalization may use four statements.
8. Superseded float/resource-rate Finance helpers remain reachable and require consumer-by-consumer retirement.

## 40. Superseded Paths

The following are marked for deletion, not compatibility preservation:

- Finance uses of `financials/utils/helpers.py::resolve_rate()` that fall back to project/resource hourly metadata after active callers move to Rate Card authority.
- Any float-based duplicate rate/cost builder superseded by the canonical R6D Reader/domain contract.
- Any stale test or adapter referring to `cost_entries_changed`.
- Any temporary old/new Rate, Actual, or Commitment command/API/controller/QML path created during an active cutover.
- Any unused CRUD method left after the approved QML/product command surface is finalized.

`Resource.hourly_rate` itself is not marked for deletion because it has valid Resource operational/planning semantics. The `EarnedValueCalculator` is not R6D compatibility debt; R6E owns its authoritative Decimal replacement and eventual deletion.

## 41. Recommended R6D Implementation Sequence

### R6D-B - Rate Card governance

Define immutable successor/effective lifecycle, complete rate-line snapshot version/modifier evidence, narrow permissions, optimistic concurrency/race handling, typed desktop commands, bounded selectors, deny-safe capabilities, and complete QML command UX. This comes first because approved-time evidence depends on the rate contract.

### R6D-C - Actual Cost governance

Remove service-owned rollback, document or relocate savepoint conflict translation, enforce consistent SoD, expose authoritative capabilities and selected detail, complete approved draft edit/delete UX or delete the unused surface, and add required filters without changing posted/reversal authority.

### R6D-D - Approved-Time labor posting hardening

Adopt the completed rate snapshot contract, introduce an auditable service identity, prove correction/replay atomicity, expose durable no-rate remediation evidence, and preserve Time ownership.

### R6D-E - Commitment projection hardening

Keep Finance mutation read-only, strengthen worker identity and stale/update/match/reversal concurrency, add only justified read filters/detail, and preserve Procurement event authority.

### R6D-F - Integrated security, concurrency, events, and performance

Run `app_runtime` PostgreSQL child attacks, concurrent duplicate/reversal/rate-overlap tests, outbox/inbox replay tests, invalidation proofs, statement budgets, and `EXPLAIN (ANALYZE, BUFFERS)` at representative volume.

### R6D-G - Cleanup, broad regression, and closure

Migrate remaining internal consumers, delete all superseded/temporary paths and stale tests, run the broad PM/Platform/PostgreSQL gates, reconcile this document, and close only with one production architecture per concept.

Dependency rule: R6D-B precedes D; R6D-C precedes D/E integration closure; R6D-F follows all write cutovers; R6D-G deletes every migration scaffold before closure.

## 42. Deferred R6E

R6E owns Decimal EVM authority, earned-value formula remediation, variance taxonomy, cost-phasing semantics, and removal of the old float-based EVM/calculation authority after parity is proven. R6D may prevent those paths from being mistaken for ledger truth but will not redesign them.

## 43. Deferred R6F

R6F owns Billing Preparation write/governance modernization and any current product plan assigned to that phase. R6D may preserve read-only rate evidence consumed by billing but will not create billing or Accounting authority.

## 44. Deferred R6G

R6G owns projected commercial revenue, profitability, and related product semantics. R6D supplies governed cost/rate facts only and does not invent commercial formulas.

## 45. Deferred R6H

R6H owns final Finance integration, broad validation, cleanup, and phase closure at the roadmap level after R6D-R6G. R6D-G still closes R6D locally and must not defer its own dead-code removal to R6H.

## 46. R6D-A Decision

**Decision: R6D-A is complete and R6D-B is the approved recommended next step.**

The repository is not greenfield. It already has credible enterprise foundations: scoped Decimal domain models, immutable posted facts, deterministic rate precedence, durable outbox/inbox delivery, source revisions/hashes, idempotency constraints, worker UoWs, typed events, server reads, and forced RLS. R6D should harden and converge this architecture rather than replace it.

The implementation priority is Rate Card governance because labor posting consumes that contract. The highest immediate correction after it is transaction-neutral Actual Cost handling. There is no evidence supporting Finance ownership of Procurement mutation, a fallback to Resource hourly rate, zero-cost posting, historical recomputation, or parallel compatibility architecture.

### R6D-A Exit Gate

| Gate | Result | Evidence summary |
|---|---|---|
| Rates 1-12 | PASS | Models, lifecycle, precedence, consumers, snapshots, resource-rate boundary, writes/UI, permissions, and transaction owner identified |
| Actual Cost 13-22 | PASS | Domain/lifecycle, posted-only rule, sources, Manual Actual, posting, reversal, immutability, permission, approval, and UoW identified |
| Time Labor 23-30 | PASS | Time outbox -> Finance inbox/UoW -> rate -> immutable posting traced; retries and no-rate behavior identified |
| Commitments 31-39 | PASS | Procurement source, Finance projection, revisions, idempotency, stale handling, open semantics, matching, and read-only boundary proven |
| Read/UI 40-45 | PASS | Rate, Actual, and Commitment readers plus Manual Actual/Rate/Commitment UI authority characterized |
| Transactions 46-50 | PASS | No service commit; two unsafe rollbacks and scoped savepoints identified; desktop and worker owners separated |
| Events 51-56 | PASS | Retired signal has zero production consumers; canonical typed invalidation map identified |
| Security 57-61 | PASS | Tables, scopes, roles, RLS, sensitive permission, and required child attack tests recorded |
| Money 62-67 | PASS | Decimal authorities, float debt, rounding, commitment math, currency failure, and no-FX boundary recorded |
| Performance 68-72 | PASS | Known statement shapes and high-cardinality risks recorded; no speculative indexes added |
| Boundaries 73-81 | PASS | Budget, Forecast, Time, Procurement, Resource, Scheduling, Billing, Accounting, and EVM ownership preserved |
| Planning 82-90 | PASS | P0/P1/P2, dependency-ordered plan, documentation, scope restraint, clean unrelated work, and no commit confirmed |

### Source Path Index

- Rate domain/service/resolver: `src/core/modules/project_management/domain/financials/rate_cards.py`, `application/financials/rate_cards/`
- Cost domain/service: `domain/financials/cost_entry.py`, `application/financials/cost/entries/cost_entry_service.py`
- Commitment domain/service: `domain/financials/commitment.py`, `application/financials/commitments/commitment_service.py`
- Labor evidence: `domain/financials/labor_posting.py`, `infrastructure/persistence/orm/labor_posting.py`
- Finance persistence: `infrastructure/persistence/orm/rate_cards.py`, `cost_entry.py`, `commitment.py`, `finance_inbox.py`
- Desktop commands: `api/desktop/financials/commands/cost_entries.py`
- RLS/schema guards: `src/infra/persistence/migrations/helpers/rls_classification.py`, `schema_guards.py`
- Fresh baseline: `src/infra/persistence/migrations/versions/f3c89cac079d_initial_schema.py`

