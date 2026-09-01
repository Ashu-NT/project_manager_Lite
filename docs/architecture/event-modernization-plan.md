# Event Modernization Plan

Living implementation roadmap for converging every capability's mutation-notification path onto
the canonical `DomainEvent` + `ViewInvalidation` pipeline and retiring the legacy `Signal[str]`
fields on `DomainEvents` (`src/core/shared/events/domain_events.py`).

This document tracks **status and sequencing**. It does not restate architectural rationale —
see [ADR-005: Domain Events](../architecture_decisions/ADR-005-domain-events.md) for the
canonical contracts, decision history, and alternatives rejected. See the top-level
[`README.md`](../../README.md#event-architecture) for a one-page developer orientation.

## 1. Objective

- Replace coarse legacy `DomainEvents` `Signal[str]` fields with typed, per-capability
  `DomainEvent`s.
- Converge each capability's mutations onto one canonical `UnitOfWork` (one physical
  transaction, one commit, one `DomainEvent` lifecycle).
- Emit typed business `DomainEvent`s from that UnitOfWork (`uow.record_event(...)` or an
  aggregate that records its own).
- Map each typed event to a scoped `ViewInvalidationHint` (`PlatformScope`/`TenantScope`/
  `OrganizationScope`/`ResourceScope`), never a bare string signal.
- Narrow UI refreshes from "reload the whole workspace" to "reload exactly what went stale."
- Delete each legacy `Signal` once its replacement is live and observably equivalent — no
  compatibility bridge, no alias.
- Reach legacy `Signal` count = 0.

## 2. Canonical Target Architecture

```
Application command/service
    v
Canonical UnitOfWork
    v
repository mutation + audit staging
    v
uow.record_event(...)
    v
transactional DomainEvent handlers        [FAIL_FAST]
    v
database commit
    v
postcommit DomainEvent bus                [ISOLATE_AND_CONTINUE]
    v
ViewInvalidation handler
    v
ViewInvalidationChannel
    v
scoped UI adapter/controller
    v
narrow read-model refresh
```

Full contracts, rationale, and the closed `EventScope`/`ScopeFilter` unions are defined in
ADR-005 §1 (Event Taxonomy), §9 (UnitOfWork Semantics), §12 (View Invalidation). This document
does not duplicate them — read ADR-005 before implementing a phase below.

## 3. Phase Completion Ledger

| Phase | Capability | Transaction ownership | Typed DomainEvents | ViewInvalidation | Legacy Signal status |
|---|---|---|---|---|---|
| P0-P8 | Foundational infrastructure (UnitOfWork/dispatcher/bus/channel contracts, taxonomy, scope model) | N/A - infrastructure only | N/A | N/A | N/A |
| P9-P10D | Organization, Module Entitlements, Role Binding / Scoped Access, Tenant Membership, Approval (5 capabilities) | Canonical, per-capability UnitOfWork | 15 classes: `OrganizationCreated`; `OrganizationProfileUpdated`/`OrganizationEnabled`/`OrganizationDisabled`; `ModuleLicensed`/`ModuleLicenseRevoked`/`ModuleEnabled`/`ModuleDisabled`/`ModuleLifecycleTransitioned`; `RoleBindingAssigned`/`RoleBindingRevoked`; `TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed`; `ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected` | Narrow, scoped adapters (`ScopedViewInvalidationSubscription`-based) | `organizations_changed` deleted (P10D closed the last gap - `update_organization`/`enable`/`disable`) |
| P12 (A/B) | Employee | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `employees_changed` deleted |
| P13 (A/B) | Department | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `departments_changed` deleted |
| P14 (A/B) | Site | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `sites_changed` deleted |
| P15 (A/B) | Party | Canonical UnitOfWork | Typed create/profile-update events | Narrow | `parties_changed` deleted |
| P16 (A/B/C/D, D-FIX) | Document + DocumentStructure + DocumentLink | Canonical `DocumentUnitOfWork` (`.documents`/`.structures`/`.links`, shared by `DocumentService` + `DocumentIntegrationService`) | `DocumentCreated`, `DocumentProfileUpdated`, `DocumentStructureCreated`, `DocumentStructureProfileUpdated`, `DocumentReferenceLinked`, `DocumentReferenceUnlinked` | Narrow, incl. the generic `ResourceScope` `EventScope` kind (P16D-FIX) for DocumentLink's cross-module target identity | `documents_changed` deleted |
| P18 (A/B) | Project Resource (Master + Capability) | Canonical `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` (`.resources`/`.skills`/`.certifications`, shared for the same reason `DocumentUnitOfWork` is) | `ResourceMasterChanged` (CREATED/UPDATED/DEACTIVATED/REACTIVATED/PURGED), `ResourceCapabilityChanged` (ADDED/UPDATED/REMOVED) — existing vocabulary, retained unchanged | Narrow: `resource_list` (`OrganizationScope`) for Master, `resource_capabilities` (`ResourceScope`, exact-resource) for Capability | `resources_changed` deleted |
| P19 (+ P19-FIX) | Finance Forecast | Canonical `FinanceGovernanceUnitOfWork` (already existed) — `ForecastVersionService`/`ForecastGenerationService` gained `record_event` wired to `uow.record_event`; the second, hidden `financial_change.apply` successor producer now reports through a new generic `ApprovalHandlerResult.domain_events` seam, `ApprovalService` recording it on its own real UoW | `ForecastVersionChanged` (CREATED/SUBMITTED/APPROVED/REJECTED/DELETED), `ForecastLineChanged` (ADDED/UPDATED/REMOVED), `ForecastDraftGenerated` | Narrow: `forecast_planning` (project-scoped `ResourceScope`) for everything except approval, `forecast_approved_basis` (same scope kind) for `ForecastVersionChanged(APPROVED)` — P19-FIX corrected APPROVED to notify **both** targets (the version's own status change is visible in `forecast_planning`'s list too), never one alone | `forecasts_changed` deleted |
| P20 | Inventory Storeroom + Storage Location | New canonical `InventoryFoundationUnitOfWork`/`InventoryFoundationUnitOfWorkFactory` (`.storerooms`/`.locations`, `src/core/modules/inventory_procurement/{contracts,infrastructure/persistence}/uow/inventory/inventory_foundation_unit_of_work.py`) — replaced raw `self._session.commit()` mutation in `InventoryService`/`InventoryFoundationService`; also fixed a real pre-existing bug where activity recording was silently dead code (never wired with an `_activity_service`) | `StoreroomCreated`, `StoreroomProfileUpdated`, `StoreroomStatusChanged` (a genuine 4-state DRAFT/ACTIVE/INACTIVE/CLOSED lifecycle, not a boolean); `LocationCreated`, `LocationProfileUpdated` (Location's `is_active` has no derived consequences, so it stays a plain profile field, unlike Site's) | Narrow: `storeroom_list` (`OrganizationScope`) — one target shared by the master list AND the `storeroom_options` reference selector (proven the same underlying projection); `location_list` (`OrganizationScope`) | `inventory_storerooms_changed`/`inventory_locations_changed` both deleted |

**Platform / Shared Master Data is fully modernized** as of P16D-FIX: Organization, Tenant
Membership, Module Entitlements, Role Binding / Scoped Access, Approval, Employee, Department,
Site, Party, Document, DocumentStructure, DocumentLink. Zero Platform-owned legacy `Signal`
fields remain on `DomainEvents`.

**Project Resource is fully modernized** as of P18B.

| Aspect | Status |
|---|---|
| Resource Master transaction ownership | MODERNIZED — canonical `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` (`src/core/modules/project_management/{contracts,infrastructure/persistence}/uow/resources/resource_unit_of_work.py`), fresh `Session` per operation |
| Resource Capability transaction ownership | MODERNIZED — same `ResourceUnitOfWork` (`.skills`/`.certifications` accessors) |
| Resource typed event transport | CANONICALIZED — `ResourceMasterChanged`/`ResourceCapabilityChanged` recorded via `uow.record_event(...)`, dispatched through the shared transactional/post-commit pipeline; the bespoke module-level `Signal[T]` publishers are DELETED |
| Resource audit / activity | ATOMIC — `record_audit_entry(uow, ...)` inside the same transaction as the mutation; activity-feed staging also rides the same fresh UoW `Session` (a real regression found and fixed mid-P18A: activity staged on the old process-lifetime shared session was never committed once the mutation itself moved to a fresh session) |
| No-op discipline | `update_resource`, `update_resource_skill`, `update_resource_certification` produce zero write/audit/event on a true no-op |
| Employee-driven Resource sync | CASE A (real Resource mutation) — `sync_linked_employee_resources` writes real `name`/`role`/`contact` columns atomically inside Employee's own canonical UoW, and now also records a typed `ResourceMasterChanged(UPDATED)` there via a `ResourceMasterEventFactory` Protocol Platform owns and PM's composition satisfies (`build_resource_master_changed_for_employee_sync`, wired only in `platform_registry.py`) — Platform's `employee_service.py` never imports PM's concrete event class |
| Resource ViewInvalidation | MODERNIZED — two targets: `resource_list` (`OrganizationScope`, every `ResourceMasterChanged`) and `resource_capabilities` (`ResourceScope`, exact-resource, every `ResourceCapabilityChanged`); proven from source that list/options projections never embed skill/certification data, so a capability change never triggers a list-scoped refresh |
| UI consumers | CUT OVER — all 8 original consumers re-audited from source (not assumed): the main Resources workspace controller narrows to `refresh()` (list) + `reload_skills_and_certs()`/activity-reload (capability/detail, entity-id-gated to the selected resource); Dashboard/Portfolio/Scheduling/Tasks/`ResourceTimesheetsController`/`TimesheetsWorkspaceController` (review queue) all react to `resource_list` only, via one `ResourceViewInvalidationAdapter` instance each (none had a genuine `resource_capabilities` dependency — proven from their own presenter/query source); Platform's Control workspace subscription was removed entirely with no replacement (no real Resource dependency found) |
| `resources_changed` | DELETED — field, all 3 producers (Resource Master, Resource Capability, Employee sync), and all 8 consumers. Legacy Signal count: 28 (29 → 28, confirmed via source) |

Only one full refresh remains genuinely coarse: the 6 non-Resources-workspace consumers
(Dashboard/Portfolio/Scheduling/Tasks/2x Timesheets) call their own existing `refresh()` on any
Resource Master change rather than a narrower, capability-specific reload — none had an existing
narrower seam, and building one would mean redesigning each of those *other* capabilities' own
presenter/query shape (explicitly out of P18B's scope: "refactor unrelated PM capabilities").
This is still a real improvement over pre-P18B behavior: none of the 6 fire on
`ResourceCapabilityChanged` any more (a skill/certification edit no longer triggers any of their
refreshes at all), and the Resources workspace itself no longer double-reacts (a coarse full
refresh plus a redundant narrow "activity" reload on every event, regardless of relevance) the
way it did before.

**Finance Forecast is fully modernized** as of P19.

| Aspect | Status |
|---|---|
| Forecast transaction ownership | Already canonical (`FinanceGovernanceUnitOfWork`, pre-existing) |
| Forecast typed event transport | CANONICALIZED — `ForecastVersionChanged`/`ForecastLineChanged`/`ForecastDraftGenerated` recorded via `uow.record_event(...)` from `ForecastVersionService`/`ForecastGenerationService` |
| Financial-change-apply forecast successor | CANONICALIZED via a new generic seam — `ApprovalHandlerResult.domain_events`, recorded by `ApprovalService` on its own real `UnitOfWork` before `uow.commit()`; the participant never receives the `UnitOfWork` (ADR-005 §24 invariant preserved) |
| No-op discipline | `update_line` produces zero write/audit/event/synthetic version bump on a true no-op (a real, newly-added guard — not present pre-P19) |
| Forecast ViewInvalidation | MODERNIZED — two project-scoped targets: `forecast_planning` (every fact except approval) and `forecast_approved_basis` (`ForecastVersionChanged(APPROVED)` only) — a real correction over legacy behavior, which invalidated `{overview, planning, performance}` for every event and never invalidated `commercial` at all |
| UI consumers | CUT OVER — the sole consumer (`FinancialsRefreshMixin`'s destination-based model) now reacts via one `ForecastViewInvalidationAdapter` on `ProjectManagementFinancialsWorkspaceController`, filtered by selected project |
| `forecasts_changed` | DELETED — field, both producers, the one consumer. Legacy Signal count: 27 (28 → 27, confirmed via source) |

See ADR-005 §26.16 for the full design (including why the financial-change-apply producer needed
a new generic Approval reporting seam rather than widening `dependencies_factory`).

**Inventory Storeroom + Storage Location is fully modernized** as of P20.

| Aspect | Status |
|---|---|
| Storeroom transaction ownership | MODERNIZED — canonical `InventoryFoundationUnitOfWork`, fresh `Session` per operation (was raw `self._session.commit()`) |
| Storage Location transaction ownership | MODERNIZED — same `InventoryFoundationUnitOfWork` (`.locations` accessor) |
| Typed event transport | CANONICALIZED — `StoreroomCreated`/`StoreroomProfileUpdated`/`StoreroomStatusChanged`/`LocationCreated`/`LocationProfileUpdated` recorded via `uow.record_event(...)` |
| Audit | ADDED — `record_audit_entry(uow, ...)` inside the same transaction (Inventory had no governance audit trail for these two capabilities before; mirrors the canonical pattern already used by this module's own `PurchaseOrderSubmissionUnitOfWork`) |
| Activity | FIXED — `record_activity` was silent dead code pre-P20 (`InventoryService`/`InventoryFoundationService` were never wired with an `_activity_service`); now atomic with the mutation via a fresh, transaction-bound `ActivityService` |
| No-op discipline | `update_storeroom`/`update_storage_location` produce zero write/audit/event/synthetic version bump on a true no-op (real, newly-added guards — not present pre-P20) |
| Cross-org / parent integrity | Audited, no bug found: a Location's `storeroom_id` is immutable after creation (no "move between storerooms" operation exists), a Storeroom must belong to the active organization to be referenced (already enforced pre-P20), parent-location cycles are already rejected. Storeroom status transitions do not cascade to child Locations (no cascade existed pre-P20 either; out of scope to add one) |
| ViewInvalidation | MODERNIZED — two org-scoped targets: `storeroom_list` (every Storeroom fact) and `location_list` (every Location fact); proven from source that `storeroom_list` is the *same* projection backing both the Inventory workspace's master list and the `storeroom_options` selector used by Pricing/Procurement/Reservations — one target, not two |
| UI consumers | CUT OVER — 6 workspaces re-audited from source (not assumed): Inventory (owner, full `refresh()` on either target — no narrower seam exists in its own monolithic `build_workspace_state`), Dashboard (KPI rollup, full `refresh()` on either target — legitimate, no seam), Pricing/Procurement (`storeroom_options` selector only, reuse the existing narrow `refresh_site_options` seam), Reservations (`storeroom_options` selector only, P20 additively extracted a new narrow `refresh_storeroom_options` seam mirroring Pricing/Procurement's), Catalog (zero real dependency — proven no Catalog presenter references Storeroom or Location at all — subscription removed with no replacement) |
| `inventory_storerooms_changed` / `inventory_locations_changed` | DELETED — both fields, all producers, all consumers. Legacy Signal count: 25 (27 → 25, confirmed via source) |
| P21 | Finance Financial Setup | Already canonical `FinanceGovernanceUnitOfWork` — `FinancialConfigurationService` gained `record_event` wired to `uow.record_event`; no new UoW | `ProjectFinancialProfileUpdated`, `ProjectFinancialProfileTransitioned` (project-scoped); `CostCodeCreated`, `CostCodeProfileUpdated`, `CostCodeActivated`, `CostCodeDeactivated` (organization-scoped — `ProjectCostCode` is a global catalog, not project-owned); `ProjectCostCodeRestrictionAdded`, `ProjectCostCodeRestrictionRemoved` (project-scoped join) — 8 events for 8 audited operations | Narrow: `financial_profile` (project-scoped `ResourceScope`) fed only by the two Profile events — proven the *sole* current Financial Setup projection (no destination in the Financials workspace ever caches Cost Code data; every cost-code picker is a live, on-demand query). Cost Code / Restriction events are recorded as canonical typed facts with deliberately zero ViewInvalidation subscription | `financial_setup_changed` deleted |

**Finance Financial Setup is fully modernized** as of P21. A significant re-audit finding: only
`create_cost_code` has a live production caller today (via a direct `commands.financial_setup(...)`
call in the desktop API) — `configure_profile`/`transition_profile`/`update_cost_code`/
`deactivate_cost_code`/`activate_cost_code`/`add_project_cost_code`/`remove_project_cost_code` are
all reachable through the governed `FinanceGovernedServicePort` (registered mutations) but have
zero current UI/API callers. All 8 still received full typed-event coverage (they are real,
complete, governed-surface operations, not dead code to delete), but this explains why P21's
ViewInvalidation retirement changes essentially nothing about today's visible behavior: the legacy
`financial_setup_changed → {planning, costs, controls}` blanket invalidation was already pure
waste for the one live producer (`create_cost_code` — no cost-code list is ever cached anywhere in
the Financials workspace), and the one destination it should invalidate (`controls`, for
`financial_profile`) has no live producer yet either. See ADR-005 §26.18 for the full design.

## 4. Current State

**Legacy Signal count: 24 as of P21** (source-derived from `src/core/shared/events/domain_events.py`,
re-verified against current source when this document was last updated).

| Area | Count |
|---|---|
| Platform | 0 |
| Auth/Security | 1 |
| Project Management | 7 |
| Finance | 7 |
| Inventory/Procurement | 9 |

> **This is a snapshot, not a fact.** Recompute the count directly from
> `src/core/shared/events/domain_events.py` before relying on it - do not trust this table if it
> is more than a few phases old. Concurrent development in any module can add or remove fields
> between updates to this document.

## 5. Current Priority

**Finance Financial Setup is fully modernized (P21, see §3).** The next capability has not yet
been chosen — the P17 ranking's provisional order (§6 below) next suggests Finance Rate Card, but
per this document's own repeated caution, re-run prioritization from current source before
committing to it: concurrent development elsewhere may have changed readiness since P17.

## 6. Provisional Roadmap

This is a **provisional sequence from the P17 system-wide ranking, not a permanent commitment.**
Re-run prioritization after each major capability - current source is authoritative, and
concurrent development elsewhere in the codebase may change any capability's readiness before
its turn comes up.

Suggested next order (P18 Project Resource, P19 Finance Forecast, P20 Inventory
Storeroom/Location, and P21 Finance Financial Setup are DONE — see §3):

```
P22  Finance Rate Card
```

Remaining capability groups, not yet assigned rigid phase numbers:

- **Project Management**: Task Lifecycle (highly overloaded - split into ~9 real facts before
  any typed-event design), Project Lifecycle, Timesheet Period, Baseline Approval, Collaboration
  Comment (+ Collaboration Presence, which needs a non-`DomainEvent` mechanism, not a migration
  target), Portfolio (Template/Scenario/Intake/Dependency), Risk Register.
- **Finance**: Financial Change, Project Commitment (fix the missing-rollback bug in
  `commitment_service.py` first), Project Cost Entry, Project Budget, Planned Cost, Billing
  Preparation.
- **Inventory/Procurement**: Item Catalog, Reorder Policy, Requisition, Purchase Order,
  Reservation, Stock Balance/Ledger, Cycle Count, Goods Receipt.
- **Auth/Security**: Auth Credential & Session Lifecycle (`auth_changed` - largest remaining
  raw-Session surface in the codebase; needs its own 2-phase split, transaction convergence
  before typed-event work).

## 7. Known Architectural Hotspots

Findings from the P17 system-wide audit, recorded here for visibility. **Not solved by this
document** - each is addressed when its owning capability's phase is implemented.

- `tasks_changed` - highly overloaded (~9 distinct real business facts under one signal name,
  the worst offender in the system by call-site count).
- `auth_changed` - covers multiple unrelated security facts (password, MFA, federated identity,
  session, bootstrap/registration, custom-role).
- `project_changed` - broadest PM fan-out signal; touches 11 consumer files.
- `inventory_balances_changed` - ledger/balance overload; StockBalance is a maintained running
  total, not a derived read, so typed events here must carry enough identity to avoid
  reintroducing ambiguity.
- `inventory_purchase_orders_changed` - mixed transaction model (one submission path already on
  a canonical UoW, everything else raw `Session`) plus cross-signal coupling with Balance and
  Receipt in the receiving flow.
- `collaboration_changed` - durable comment mutations and ephemeral presence pings share one
  signal name; a category error, not just an overload - presence needs a different mechanism
  entirely, not a `DomainEvent`.
- Reflective Approval/Finance legacy dispatch - `ApprovalService._emit_signal_safely` and
  `FinanceGovernedServicePort.__getattr__` both use `getattr(domain_events, signal_name)`
  string-keyed dispatch (bounded to their own call sites, not a generic repo-wide router, but
  still indirection worth being aware of when tracing a producer). `FinanceGovernedServicePort`'s
  reflective command *routing* (dispatching a read-service method name to the right
  `FinanceGovernanceCommandBoundary` family) is unrelated to and untouched by P19 — Forecast's
  typed-event construction happens inside `ForecastVersionService`/`ForecastGenerationService`
  themselves, not in the reflective layer, so removing the routing reflection would have zero
  effect on event correctness and was left in place. `ApprovalService._emit_signal_safely` also
  remains — P19 added a second, coexisting reporting channel (`ApprovalHandlerResult.domain_events`,
  ADR-005 §26.16) rather than replacing it, since every other Approval participant still reports
  through the legacy Signal-name bridge.
- Remaining raw process-lifetime Sessions - Auth (all 10 producer files, on one shared Session),
  most of PM and Inventory/Procurement, and part of Finance (`cost_entries_changed`,
  `commitments_changed` - notably, both already have an unused canonical UoW repo declared for
  them).
- ~~Orphan Resource typed events before P18~~ **RESOLVED by P18A** -
  `ResourceMasterChanged`/`ResourceCapabilityChanged` now dispatch through the canonical
  post-commit bus (bespoke `Signal[T]` transport deleted); still zero real UI subscribers until
  P18B builds the ViewInvalidation handler.
- Coarse Inventory workspace refresh fan-out - all 6 Inventory/Procurement workspace controllers
  subscribe to all 11 legacy signals identically; any one signal refreshes all 6 workspaces in
  full regardless of relevance.

## 8. Migration Checklist

For every capability, before it is considered modernized:

- [ ] semantic audit (enumerate every real business fact currently hidden behind the legacy
      signal - do not assume one signal = one fact)
- [ ] transaction/UoW convergence (one canonical UnitOfWork, one commit, one `DomainEvent`
      lifecycle)
- [ ] cross-org boundary verification
- [ ] no-op behavior (a request identical to already-persisted state records nothing)
- [ ] typed DomainEvents
- [ ] transactional dispatch (FAIL_FAST, pre-commit)
- [ ] postcommit dispatch (ISOLATE_AND_CONTINUE)
- [ ] ViewInvalidation target/scope
- [ ] narrow UI consumer cutover
- [ ] duplicate refresh audit (no capability left double-refreshing from both old and new paths)
- [ ] legacy producers = 0
- [ ] legacy consumers = 0
- [ ] legacy Signal deleted (field removed from `DomainEvents`, not merely unused)
- [ ] architecture guards pass (`src/tests/architecture/`, `src/tests/platform/test_p*`)
- [ ] ADR/plan updated (this document's ledger, and ADR-005 §26 if the design itself needed a
      correction, as P16D-FIX did)

## 9. Pre-Release Convergence Rule

This application is **pre-release**. Therefore, for every phase above:

- Remove obsolete architecture directly - do not leave a superseded path running "just in case."
- No compatibility aliases, unless a concrete, currently-live dependency actually requires one
  (not a hypothetical future one).
- No generic bridges for retired legacy Signals - each capability gets its own typed
  replacement, never a shared string-keyed router standing in for several at once.
- Do not preserve incorrect semantics merely for backward compatibility - if a phase finds a
  legacy behavior was already wrong (e.g. P16B's missing no-op guards), fix it as part of the
  phase and say so explicitly, rather than migrating the bug forward.
