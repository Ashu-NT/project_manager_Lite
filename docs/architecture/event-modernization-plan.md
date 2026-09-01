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

## 4. Current State

**Legacy Signal count: 29 as of P17** (source-derived from `src/core/shared/events/domain_events.py`,
re-verified against current source when this document was last updated).

| Area | Count |
|---|---|
| Platform | 0 |
| Auth/Security | 1 |
| Project Management | 8 |
| Finance | 9 |
| Inventory/Procurement | 11 |

> **This is a snapshot, not a fact.** Recompute the count directly from
> `src/core/shared/events/domain_events.py` before relying on it - do not trust this table if it
> is more than a few phases old. Concurrent development in any module can add or remove fields
> between updates to this document. As of P18B this table's PM count (8) is one field stale by
> construction — it still includes `resources_changed`, which P18B deleted; PM is 7 as of P18B,
> total legacy count 28. Left as a P17-snapshot artifact rather than silently edited, per this
> section's own "recompute, don't trust" instruction; the P18B section above and §3's ledger are
> the current source of truth for Project Resource specifically.

## 5. Current Priority

**Project Resource is fully modernized (P18A + P18B, see §3).** The next capability has not yet
been chosen — the P17 ranking's provisional order (§6 below) starts with Finance Forecast, but
per this document's own repeated caution, re-run prioritization from current source before
committing to it: concurrent development (Finance in particular has had recent, active,
concurrent work per this project's own tracking) may have changed readiness since P17.

## 6. Provisional Roadmap

This is a **provisional sequence from the P17 system-wide ranking, not a permanent commitment.**
Re-run prioritization after each major capability - current source is authoritative, and
concurrent development elsewhere in the codebase may change any capability's readiness before
its turn comes up.

Suggested next order (P18 Project Resource is DONE — see §3):

```
P19  Finance Forecast
P20  Inventory Storeroom/Location
P21  Finance Financial Setup
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
  still indirection worth being aware of when tracing a producer).
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
