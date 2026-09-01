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

**Platform / Shared Master Data is fully modernized** as of P16D-FIX: Organization, Tenant
Membership, Module Entitlements, Role Binding / Scoped Access, Approval, Employee, Department,
Site, Party, Document, DocumentStructure, DocumentLink. Zero Platform-owned legacy `Signal`
fields remain on `DomainEvents`.

**P18A (in progress — Project Resource): transaction/event-pipeline convergence done, NOT fully
modernized yet.**

| Aspect | Status |
|---|---|
| Resource Master transaction ownership | MODERNIZED — canonical `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` (`src/core/modules/project_management/{contracts,infrastructure/persistence}/uow/resources/resource_unit_of_work.py`), fresh `Session` per operation |
| Resource Capability transaction ownership | MODERNIZED — same `ResourceUnitOfWork` (`.skills`/`.certifications` accessors); no operation currently spans Master + Capability, so one shared UoW was chosen over two, mirroring `DocumentUnitOfWork`'s `.documents`/`.structures`/`.links` shape |
| Resource typed event transport | CANONICALIZED — `ResourceMasterChanged`/`ResourceCapabilityChanged` (existing, retained vocabulary, unchanged shape) now recorded via `uow.record_event(...)` and dispatched through the shared transactional/post-commit pipeline; the bespoke module-level `Signal[ResourceMasterChanged]`/`Signal[ResourceCapabilityChanged]` publishers are DELETED (confirmed zero production consumers before deletion) |
| Resource audit | ATOMIC — `record_audit_entry(uow, ..., commit=False, fail_closed=True)` inside the same transaction as the mutation; audit failure or commit failure both roll back the mutation and produce zero events (typed and legacy) |
| No-op discipline | `update_resource`, `update_resource_skill`, `update_resource_certification` compare the built candidate against the existing record and return unchanged with zero write/audit/event/legacy-signal on a true no-op; `deactivate_resource`/`reactivate_resource` already rejected a no-op transition with `BusinessRuleError` (unchanged) |
| Employee-driven Resource sync | CASE A (real Resource mutation, not projection staleness) — `sync_linked_employee_resources` writes real `name`/`role`/`contact` columns on the linked Resource row, atomically inside Employee's own canonical UoW. A typed `ResourceMasterChanged(UPDATED)` is now recorded there too, via a `ResourceMasterEventFactory` Protocol Platform owns and PM's composition (`platform_registry.py`) satisfies with `build_resource_master_changed_for_employee_sync` — Platform's `employee_service.py` never imports PM's concrete event class (no new Platform → business-module dependency; the existing 2-entry `GOVERNED_EXCEPTIONS` allowlist in `test_platform_does_not_import_business_modules.py` is unchanged) |
| Resource ViewInvalidation | NOT YET — P18B |
| `resources_changed` | TEMPORARILY RETAINED — every real successful mutation across all three producers (Master, Capability, Employee sync) still emits it, post-commit, alongside the new typed event; all 8 existing consumers are unchanged. Deleted in P18B. |

**Project Resource is not yet marked fully modernized** — P18B (ViewInvalidation + consumer
cutover + `resources_changed` deletion) remains.

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
> between updates to this document.

## 5. Current Priority

**P18: Project Resource** (`resources_changed`).

Why this capability, ahead of every other remaining one:

- Typed `ResourceMasterChanged`/`ResourceCapabilityChanged` events already exist in source, with
  real `change_type` enums and explicit `tenant_id`/`organization_id` fields - genuinely usable
  vocabulary, not a stub, and the only non-Finance capability outside Platform with any typed
  events already written.
- That typed vocabulary is currently transported through a bespoke, capability-local
  `Signal[T]` - non-canonical, not routed through `uow.record_event`/the post-commit bus, and
  (high confidence) has zero live consumers today.
- `resources_changed` (the legacy field) is a live duplicate-publication case: the same
  mutations that construct the orphaned typed events also emit the legacy signal.
- The two hand-rolled "UoW" classes producing these events (`ResourceMasterUnitOfWork`,
  `ResourceCapabilityUnitOfWork`) currently have no audit call at all - a real, pre-existing gap
  this phase also closes.
- All 8 current `resources_changed` consumers do a coarse full-workspace refresh; narrowing them
  is a direct, provable payoff.

Planned split:

- **P18A (DONE)** - transaction/event-pipeline convergence: replaced `ResourceMasterUnitOfWork`/
  `ResourceCapabilityUnitOfWork` (hand-rolled, raw-Session, no audit) with one canonical
  `ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` + `uow.record_event(...)`; added the missing
  audit call; resolved the third, inconsistent `employee_service.py` producer path (now records a
  real typed `ResourceMasterChanged` inside Employee's own transaction, via a Platform-owned
  factory Protocol PM's composition satisfies — see §3 above for the full status table.
  `resources_changed` deliberately still fires everywhere it did before this phase.
- **P18B (NOT STARTED)** - ViewInvalidation consumer cutover: build the Resource
  `ViewInvalidationHandler`, cut all 8 consumers over to narrow hints, delete `resources_changed`
  (field + every producer and consumer, including the Employee sync path's legacy emission).

## 6. Provisional Roadmap

This is a **provisional sequence from the P17 system-wide ranking, not a permanent commitment.**
Re-run prioritization after each major capability - current source is authoritative, and
concurrent development elsewhere in the codebase may change any capability's readiness before
its turn comes up.

Suggested initial order:

```
P18  Project Resource
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
