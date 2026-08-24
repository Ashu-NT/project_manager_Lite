# ADR-005 Execution Plan: Domain Events Migration

- Companion to [ADR-005-domain-events.md](ADR-005-domain-events.md) — that document owns the
  design decisions, semantics, and reconciliations; this document owns cross-Platform-and-module
  sequencing and phase exit criteria. The exact Platform how-to (files, tests, per-phase detail)
  lives in [`platform_domain_event_implementation_plan.md`](../platform_modernization/domain_event/platform_domain_event_implementation_plan.md) —
  this document does not duplicate that detail.
- Status: draft — no phase started yet (ADR-005 itself is still "proposed," not "accepted"; do not
  begin Phase 0 until it's accepted).
- Date: 2026-08-05, revised 2026-08-25 alongside ADR-005's revision 6, after a dedicated
  Platform-only architecture audit
  (`docs/platform_modernization/domain_event/platform_domain_event_audit.md`).

## Revision Note (2026-08-25)

Three corrections to this plan, all driven directly by the Platform audit, none optional:

1. **A Platform-foundation phase is inserted before any business module migrates** (new Phase 2,
   below). The audit found Platform itself runs five distinct, unreconciled transaction-boundary
   conventions and zero tenant/organization-aware invalidation — it is not "infrastructure that's
   already done," and business modules' own migrations depend on the Platform contracts this
   phase establishes.
2. **The old Phase 5 (`maintenance`) is struck entirely.** The audit confirmed the `maintenance`
   module was deleted from this codebase on 2026-08-20 (git commit `1aa1a589`) — after this plan
   was first drafted. Zero raw `DomainChangeEvent(...)` construction sites remain anywhere in
   `src/`. Retaining a phase to migrate a module that no longer exists would be dead-weight
   sequencing.
3. **The old, separate "Phase 6: Platform Signals" classification step is folded into the new
   Phase 2** — it was always about classifying Platform's own 11 named signals, which now happens
   as part of Platform's own foundation phase rather than as a late, standalone step after every
   module has already migrated.

Phases are renumbered below to keep a single, unambiguous sequence. Everything else — the
Non-Negotiable Constraints, the general shape of the per-module discovery-then-migration
discipline, the Design Guardrails — carries forward, with the additions noted inline.

## Non-Negotiable Constraints

These apply to every phase below, not just the ones that mention them explicitly.

1. **Backend-first, UI-second.** Unchanged from the original plan: each phase's QML-facing step
   is always the *last* task within that phase, done only after that phase's domain/application/
   infra work is fully tested and green.
2. **Framework-agnostic application layer.** Unchanged: every application service or
   transactional/post-commit handler depends only on `UnitOfWork`/`UnitOfWorkFactory` (and, for
   transactional handlers, a module- or capability-specific `UnitOfWork` extension exposing
   repository *contracts*), `Clock`, `DomainEventContext`, and repository/domain contracts — never
   on `src.ui_qml`, `PySide6`, `sqlalchemy`, or `src.infra` directly. Each phase's exit criteria
   includes the AST-based guardrail check (§ Design Guardrails, updated below) for this.
3. **No compatibility facades, no straddling code.** Unchanged: finish one slice, delete the old
   path for that slice, don't leave both mechanisms live for a module/capability past its own
   phase's close. Includes service-level straddling — a command-side service migrated in a given
   phase stops reading/writing through its old constructor-injected repositories for the
   operations that phase covers.
4. **A phase is one atomic integration unit.** Unchanged: intermediate backend-only commits may
   exist locally, but a phase is not complete until its QML-facing step is done *and* its old
   event path is deleted for the operations it covers.
5. **No stale reads after a migrated command commits.** Unchanged from the original plan — this
   app's process-lifetime `Session` and long-lived controller/session graphs mean a migrated
   command's committed change is not automatically visible to an already-open read path.
   Mitigation options (migrate the read path, or an explicit, called-out `expire_all()`/
   `populate_existing()` bridge) are unchanged; every phase's exit criteria requires an actual
   test proving the chosen mitigation works, not an assumption.
6. **NEW — Tenant AND organization scope is explicit everywhere, never assumed 1:1.** No phase may
   ship a `DomainEvent` or `ViewInvalidationHint` that omits `organization_id` for a fact that is
   organization-scoped, and no phase may substitute the desktop session's currently-active
   organization for an event's actual `organization_id`. Every phase's exit criteria includes the
   tenant/organization isolation test matrix (ADR-005 Test Impact; implementation plan §
   "Tenant + Organization Test Matrix").
7. **NEW — The architecture guardrail test is green before and after every phase.** The one new
   AST-based test ADR-005 §21 adds (`platform → business module` import boundary, with the two
   explicitly-cited governed exceptions) must pass at every phase boundary. A phase that needs a
   new exception must cite a governing ADR in the same commit that adds it — an uncited exception
   fails review.

## Current State Snapshot (revised 2026-08-25 against actual repository/session code)

The dual-purpose file remains `src/core/shared/events/domain_events.py`: a
`DomainChangeEvent(category, scope_code, entity_type, entity_id, source_event)` dataclass plus a
`DomainEvents` dataclass with **31** `Signal` fields (29 module-named + 2 generic bridge signals
`shared_master_changed`/`domain_changed`), auto-wired via `_wire_bridges()`.

**Corrected/added facts (2026-08-25), superseding the 2026-08-05 snapshot below where they
conflict:**

- **The real coupling surface is measured by import sites, not named-`Signal`-field counts.** 66
  application-layer files import the `domain_events` singleton directly and call `.emit(...)` —
  **25 of these are inside `src/core/platform/` itself**, 41 across business modules. The
  per-module named-field table below undercounts Platform's own migration scope for this reason;
  Phase 2 (below) is sized against the 25-in-Platform figure, not the 11-named-Platform-signals
  figure alone.
- **`maintenance` no longer exists.** Deleted 2026-08-20 (commit `1aa1a589`), after this plan's
  original 2026-08-05 draft. The row for it in the table below is struck; the corresponding phase
  is removed (§ Phase 6, below).
- **The transaction/event-coordination *concept* is not greenfield anywhere in this codebase**,
  even though Platform's own *typed-event vocabulary* is (zero typed `DomainEvent` classes exist
  under `src/core/platform/` today). `ApprovalService` (ADR-PF-008, accepted, implemented) already
  runs an outer-transaction-owns-commit, post-commit-isolated discipline over the single
  process-lifetime `Session`; `project_management`'s `Resource*UnitOfWork` classes (module-owned,
  cited for contrast) independently reinvent a typed-event + commit/rollback + isolate-and-continue
  pattern. Phase 2 (below) exists specifically because Platform is not exempt from this
  convergence problem.
- **Real AST-based architecture-enforcement tests already exist**
  (`src/tests/architecture/test_qml_architecture_guardrails_layers.py`,
  `test_pm_inventory_module_boundary.py`) — earlier assumptions that no such tooling exists are
  corrected. ADR-005 §21 adds one new test using the same technique rather than a new framework.

| Module | Files (approx.) | Named `Signal` fields | Raw `DomainChangeEvent(` construction sites | `_subscribe_domain_change(` sites |
|---|---|---|---|---|
| hr_management | 20 | 0 | 0 | 0 |
| payroll | 20 | 0 | 0 | 0 |
| qhse | 21 | 0 | 0 | 0 |
| inventory_procurement | 127 | 12 | 0 | 1 |
| project_management | 626 | 9 | 0 | 2 |
| ~~maintenance~~ | ~~145~~ | ~~0~~ | ~~25~~ | ~~6~~ | **MODULE DELETED 2026-08-20 — row struck, no migration needed** |
| platform/shell (cross-cutting) | — | 11 (+2 bridge) | 1 (in the file itself) | 2 (**understates Platform's real scope — see the 25-import-sites figure above**) |

Other confirmed facts (unchanged from the original snapshot unless noted):

- `src/infra/persistence/db/unit_of_work.py` is exactly `session_scope()` (25 lines) with **zero
  callers** anywhere in `src/` — re-confirmed by the Platform audit, safe to reclaim per ADR-005 §20.
- `src/infra/persistence/db/session_factory.py`'s `SessionLocal` has **exactly three references in
  this codebase's entire history**: its own definition, the dead `session_scope()`, and one call
  at process startup — confirmed by the Platform audit. This plan's `UnitOfWorkFactory` closing
  over it (Phase 1) would be the first genuine per-transaction use, ever.
- Repository *contracts* (as `ABC`s/`Protocol`s) already exist separately from concrete
  implementations under each module's/capability's own `contracts/repositories/` — unchanged,
  confirmed for `project_management` and for several Platform capabilities.
- `src/infra/composition/app_container.py`'s `build_service_graph(session)` and
  `src/ui_qml/shell/app.py`'s `build_services()` remain the two places a `UnitOfWorkFactory` needs
  to be constructed and threaded through.
- **Two persistence mechanisms coexist**, confirmed again by the Platform audit reading
  `SqlAlchemyTaskRepository`: `Task.update()`'s raw, version-checked `UPDATE` bypasses ORM
  attribute tracking entirely; `TaskAssignment`/`TaskDependency` rely on tracked-ORM-attribute
  flush. Every phase must call the mutated repository's `update()`/`add()` explicitly before
  `uow.commit()`, regardless of which mechanism that repository uses.
- No `mypy.ini`/`pyrightconfig.json`/CI type-checker exists; the pytest-based AST guardrails
  (above) are the only automated enforcement, confirmed still true.

## Phase 0 — Foundational Contracts (Zero Behavior Change)

**Scope:** `src/core/shared/events/*`, `src/core/shared/time/*`, `src/infra/events/*`,
`src/infra/time/*` only. No existing file touched, no module or Platform capability wired in, no
`UnitOfWork` implementation yet (Phase 1).

Tasks:

- Create `domain_event.py`, `domain_event_context.py` (**new** — `DomainEventContext`, ADR-005
  §5), `aggregate_events.py`, `domain_event_publisher.py` (`TransactionalEventDispatcher` +
  `PostCommitEventPublisher` protocols — the latter's handler shape now takes `(event, context)`,
  ADR-005 §8), `domain_event_subscriber.py`, `subscription.py`, `view_invalidation.py`
  (`ViewInvalidationHint` **with the new `organization_id: str | None` field**,
  `PlatformViewInvalidationHint`, and the **five-method** channel contract — ADR-005 §12) under
  `src/core/shared/events/`. `UnitOfWork`/`UnitOfWorkFactory` protocols do not live here — Phase 1.
- Create `src/core/shared/time/clock.py` (protocol only).
- Create `src/infra/events/{in_process_transactional_event_dispatcher.py,
  in_process_post_commit_event_bus.py, in_process_view_invalidation_channel.py}` per ADR-005 §8/§12:
  - The transactional side is the stateless `InProcessTransactionalEventDispatcher`.
  - The post-commit side is the queued `InProcessPostCommitEventBus`, race-free, with a
    lock-held handler-registry snapshot, and breadth-first dispatch **stated explicitly as a
    deliberate behavior change** from the legacy `Signal`'s accidental depth-first-under-recursion
    behavior (ADR-005 §8) — a unit test must assert this explicitly, not merely assert "it
    dispatches correctly."
  - `InProcessViewInvalidationChannel` implements all **five** subscription methods (`subscribe`,
    `subscribe_tenant_wide`, `subscribe_across_organizations`, `subscribe_across_tenants`,
    `subscribe_to_platform_wide`) and the routing rules from ADR-005 §12 exactly.
- Create `src/infra/time/system_clock.py`.
- Unit test coverage for everything above in isolation, **including the full tenant/organization
  test matrix from ADR-005's Test Impact section** — this is new relative to the original Phase 0
  scope, and is not deferred to a later phase, since the channel's routing logic is exactly what
  Phase 0 introduces.

**Exit criteria:** every new file has unit tests passing in isolation, including the full
tenant/organization routing matrix; `git diff` touches nothing outside these four new directory
trees; the app boots unchanged (nothing imports these yet); the new architecture-guardrail test
(ADR-005 §21) passes.

## Phase 1 — `UnitOfWork`: Contract, Concrete Implementation, Session Lifecycle

**Scope:** `src/core/shared/persistence/unit_of_work.py` (new — protocols), unchanged from the
original plan's `src/infra/persistence/db/unit_of_work.py` reclamation, `src/infra/composition/app_container.py`.

Tasks (unchanged from the original plan except where noted):

1. Create `src/core/shared/persistence/unit_of_work.py` with the `UnitOfWork`/`UnitOfWorkFactory`
   protocols per ADR-005 §9 — `__enter__`/`__exit__`, `register_touched`, **`record_event`
   (new — ADR-005 §6's orchestration-fact escape hatch)**, `tracked_aggregates`, `commit`, and a
   **`context: DomainEventContext` property (new — ADR-005 §5)**. `UnitOfWorkFactory.create()`
   now takes `*, context: DomainEventContext`. No `session` field, no repository accessors on the
   shared protocol.
2. Replace `session_scope()`'s body in `src/infra/persistence/db/unit_of_work.py` with
   `SqlAlchemyUnitOfWorkBase` — unchanged mechanics from the original plan, now also threading the
   constructor-supplied `context` through to `.context`.
3. Identity-map aggregate tracking lives here, unchanged (`id()`-keyed dict, `tuple` return).
4. Each module's/capability's `SqlAlchemy<Name>UnitOfWorkFactory` closes over `SessionLocal` — a
   session *factory* — plus the dispatcher and bus from Phase 0, plus whatever the caller passes
   as `context`. `create()` calls `self._session_factory()` for a genuinely new `Session` every
   call.
5. `build_service_graph` gains the plumbing to build a `SqlAlchemy<Name>UnitOfWorkFactory` per
   migrated module/capability and add it as a new field on `ServiceGraph` — additive only.
6. Tests (using a throwaway test subclass, since no real module/capability subclass exists yet):
   two independent `create()` calls open genuinely independent sessions; rollback discards
   tracked aggregate instances without affecting a separately-created `UnitOfWork`;
   `register_touched` accepts an unhashable `RecordsDomainEvents` subclass without raising and
   dedups by identity, not equality; **`record_event(event)` stages an application-authored event
   that the next collection round picks up alongside aggregate-recorded ones (new test, proving
   ADR-005 §6's escape hatch works end-to-end)**; `uow.context` returns exactly what
   `UnitOfWorkFactory.create(context=...)` was given.

**Exit criteria:** unchanged from the original plan, plus: `record_event` and `.context` are
exercised by the tests above.

## Phase 2 — Platform Foundation (NEW — must complete before any business module migrates)

**Rationale:** the Platform audit found Platform itself runs five distinct, unreconciled
transaction-boundary conventions and has zero tenant/organization-aware invalidation — it is not
"infrastructure that's already done" merely because it sits below business modules
architecturally. Every subsequent module phase depends on the contracts and adapters this phase
produces (the shared Qt invalidation adapter in particular). **No module migration (Phase 3
onward) may begin until this phase's exit criteria are met and "Platform Domain Event Foundation
Ready" is declared.**

Exact file-by-file detail, per-capability discovery tables, and step-by-step tasks live in
[`platform_domain_event_implementation_plan.md`](../platform_modernization/domain_event/platform_domain_event_implementation_plan.md)
(Phases P0-P8 there map onto this single Phase 2 here, plus Phase 0/1 above). This section states
only the sequencing and exit gate.

### 2A — Platform Transaction/UoW Convergence

Reconcile Platform's own competing transaction conventions per ADR-005 §24/§26:
- `ApprovalService` (ADR-PF-008): **ADAPT** — migrated onto the canonical `UnitOfWork`.
- `NotificationService`'s caller-controlled `commit: bool` pattern: assessed per call site,
  migrated where it composes with a migrating command, left as-is where it's a standalone
  best-effort feature unrelated to any `UnitOfWork`-owned transaction.
- `ServiceBase.commit()`'s lone real subclass: assessed, migrated or left as an isolated legacy
  primitive depending on whether that subclass's operations are in scope for this phase.

### 2B — Platform Typed Events + View Invalidation (Per-Capability Discovery)

Same discovery-before-typing discipline the original plan already required for
`inventory_procurement`/`project_management`/the deleted `maintenance` module — applied here to
Platform's own 11 named signals (`auth_changed`, `employees_changed`, `organizations_changed`,
`sites_changed`, `departments_changed`, `calendars_changed`, `documents_changed`,
`parties_changed`, `access_changed`, `modules_changed`, `approvals_changed`). **This subsumes and
replaces the original plan's separate, later "Phase 6: Platform Signals" classification step** —
the same classification work, just performed as part of Platform's own foundation phase rather
than after every module has already migrated. Each signal is classified independently (typed
business fact vs. genuinely UI-only invalidation with no underlying domain event), per a
per-emitter discovery table — not a mechanical 1:1 rename — exactly as the original Phase 6 already
specified. Every newly-typed Platform event carries `organization_id` explicitly per ADR-005 §3.

### 2C — Qt Invalidation Adapter Consolidation

Build the one shared `qt_view_invalidation_channel.py` (ADR-005 §13/§20). Migrate the three
existing `workspace_controller_base.py` copies (Platform, `project_management`,
`inventory_procurement`) to delegate their invalidation slice to it — **their other
responsibilities are explicitly untouched, per ADR-005 §25's non-goal.**

### 2D — Platform Legacy Bridge, Cutover, and Validation

Bridge Platform's migrated signals onto the new mechanism; retire `admin_console/domain_event_binder.py`
(completing its own already-self-scheduled "R2" removal) once every consumer it served has moved
to the new channel. Delete the 11 Platform-owned fields from the old `DomainEvents` dataclass only
once every consumer has migrated (Constraint 3/4 — no straddling past this phase's close).

**Exit criteria — "Platform Domain Event Foundation Ready":**
- No Platform producer depends on the legacy `domain_events` bus except an explicitly-approved,
  time-boxed compatibility edge (if any remains, it is named and dated).
- Tenant **and organization** isolation proven by the full test matrix (ADR-005 Test Impact),
  run against real Platform signals, not only the Phase 0 synthetic tests.
- Rollback behavior, post-commit failure isolation, and integration-outbox semantics
  (unchanged, ADR-PF-011) all proven for `ApprovalService`'s migrated path specifically.
- Qt refresh behavior for every migrated Platform signal is unchanged from a user's perspective
  (a real test, not an assumption — Constraint 5).
- The architecture guardrail test (ADR-005 §21) passes, including its two explicitly-cited
  exceptions and no uncited additions.
- Zero Platform-owned fields remain in the old `DomainEvents` dataclass for anything migrated in
  this phase.

Only once all of the above hold does Phase 3 begin.

## Phase 3 — Pilot Module: `inventory_procurement`

(Renumbered from the original plan's Phase 2; content unchanged except where noted, and now
explicitly gated on Phase 2's "Platform Domain Event Foundation Ready.")

**Rationale:** fewest real touch points among modules that actually use the mechanism (1
subscribe site, 0 raw `DomainChangeEvent` constructions, 12 named Signals to retire) — enough real
usage to prove the pattern end-to-end without the blast radius of `project_management`, now also
benefiting from a Qt adapter and `UnitOfWork` foundation already proven inside Platform itself in
Phase 2.

### 3A — Discovery (unchanged in method from the original Phase 2A)

Inventory every current emitter of each of the 12 inventory Signals; for each, record the actual
business operation, the raising aggregate, and the affected view(s), before writing any typed
event. Every typed event includes `organization_id` explicitly (ADR-005 §3) — `inventory_procurement`'s
own tenant/organization data shape must be confirmed against real emitters here, not assumed
from Platform's shape.

### 3B — Migration (unchanged in shape from the original Phase 2B)

1. Add `InventoryUnitOfWork`/`InventoryUnitOfWorkFactory` + concrete
   `SqlAlchemyInventoryUnitOfWork`/`SqlAlchemyInventoryUnitOfWorkFactory`, closing over
   `SessionLocal` and accepting a `DomainEventContext`.
2. Add `domain/events.py` with the typed events from the 3A table, each carrying
   `organization_id: str | None` explicitly per its own business shape.
3. Adopt `RecordsDomainEvents` + injected `Clock` on aggregate-recorded events; use
   `uow.record_event(...)` for any genuinely orchestration-level fact identified in 3A, per
   ADR-005 §6's explicit criteria — not applied blanket to every mutation.
4. Repository `register_touched` calls on load/add (automatic via `InventoryUnitOfWork`'s
   accessors).
5. Migrate command-side services off old constructor-injected repositories onto the active
   `UnitOfWork`'s own accessors (Constraint 3) — no straddling.
6. Call the mutated repository's `update()`/`add()` explicitly after every mutation, before
   `uow.commit()` (confirm per aggregate whether this module shares `Task`'s raw-`UPDATE` pattern
   or the tracked-ORM pattern before assuming either).
7. Add `application/event_handlers/view_invalidation.py` with module-owned constants; add
   `transactional.py` only if 3A surfaced a real cross-aggregate case.
8. Wire `register_post_commit_handlers` into the composition root's `SubscriptionRegistry`.
9. Full test pass on 1-8 before touching anything QML-facing.
10. Update the one existing `_subscribe_domain_change` call site (the dashboard) to consume the
    now-consolidated Qt invalidation adapter (built in Phase 2C) instead of the legacy bus — and
    apply Constraint 5's staleness mitigation.
11. Delete the 12 inventory-owned fields out of the old `DomainEvents` dataclass, and their
    now-dead emitters, in the same phase close.

**Exit criteria:** unchanged in shape from the original Phase 2, plus the tenant/organization test
matrix passes for every newly-typed inventory event, and the architecture guardrail test remains
green.

## Phase 4 — `hr_management`, `payroll`, `qhse`: No Migration Needed Yet

(Renumbered from the original Phase 3; unchanged.) These three have zero current domain-event
usage. Do not manufacture events speculatively. When one first needs a domain event for a real
feature, it adopts the Phase 0/1 contracts directly — never touching the old `DomainEvents`
dataclass, since it never used it.

## Phase 5 — `project_management` (Coordinate With PM Collaboration Upgrade First)

(Renumbered from the original Phase 4; content unchanged in shape, with one correction.)

**Risk flag, corrected:** the original plan (2026-08-05) flagged this phase as blocked on "the PM
Collaboration Upgrade's backend work being committed and stable," citing a large uncommitted diff
at that time. **As of this revision, the working tree is clean** — whatever uncommitted diff
existed on 2026-08-05 is no longer present. This is not evidence the upgrade is *done*, only that
its state has changed since the original snapshot. **Re-confirm the actual current state of the
PM Collaboration Upgrade (and get explicit user sign-off) immediately before starting this phase**
— do not carry the stale 2026-08-05 blocking condition forward as still-true without checking.

### 5A — Discovery (unchanged in method)

Same discipline applied to the 9 named signals (`project_changed`, `tasks_changed`,
`timesheet_periods_changed`, `costs_changed`, `resources_changed`, `baseline_changed`,
`register_changed`, `collaboration_changed`, `portfolio_changed`). **Additionally**, this
discovery step must reconcile with `project_management`'s own already-existing
`Resource*UnitOfWork`/`ResourceMasterChanged`/`ResourceCapabilityChanged` classes (which already
partially cover the `resources_changed` signal) — treat these as found-in-place precedent to
generalize onto the module's new `ProjectManagementUnitOfWork`, not as undiscovered territory to
design from scratch.

### 5B — Migration (unchanged in shape from the original Phase 4B)

Same shape as Phase 3B's steps 1-11, scaled to the 5A table and the 2 subscribe sites, including
`organization_id` on every newly-typed event, the explicit `update()`/`add()`-before-`commit()`
rule, and the staleness mitigation for the dashboard and financials refresh mixins.

**Exit criteria:** same shape as Phase 3, plus no regression in the PM Collaboration Upgrade's own
test suite, plus explicit confirmation that the `Resource*UnitOfWork` reconciliation from 5A was
actually carried out (not left as two live mechanisms for `resources_changed`).

## Phase 6 — `maintenance`: Struck (Module Deleted)

**This phase is intentionally removed, not renumbered forward.** The original plan's Phase 5
targeted `maintenance` (145 files, 25 raw `DomainChangeEvent(...)` constructions, 6 subscribe
sites) as the highest-risk module, scheduled last. The Platform audit confirmed `maintenance` was
deleted from this codebase in its entirety on 2026-08-20 (git commit `1aa1a589`), after this
plan's original draft. Zero raw `DomainChangeEvent(...)` construction sites remain anywhere in
`src/`. **No migration work is needed for this module.** If a `maintenance`-equivalent module is
reintroduced in the future, it adopts the Phase 0/1/2 contracts directly as a new consumer — it
never touches the old `DomainEvents` dataclass at all, since a newly-written module never used it,
exactly like Phase 4's treatment of `hr_management`/`payroll`/`qhse`.

## Phase 7 — Retire the Old Mechanism

(Renumbered from the original Phase 7; the original's separate "Phase 6: Platform Signals"
classification step no longer exists as a distinct phase — it is now Phase 2B, completed as part
of Platform's own foundation work.) Once every module has migrated (Phases 3-5 closed; Phase 6 is
a no-op per above), delete `src/core/shared/events/domain_events.py` in full — the `DomainEvents`
dataclass, `_wire_bridges()`, `_BRIDGE_SPECS`, and the 2 bridge signals along with it. No facade,
no re-export shim, per this repo's existing no-facade rule. **Additionally, per ADR-005 §19**:
rename `src/core/shared/events/signal.py`'s `Signal` class to `CallbackSignal`, since by this
phase every real caller has migrated off it for domain-event purposes and only its narrower,
non-domain-event uses (if any remain) still reference it.

## Design Guardrails Enforced Every Phase

- The QML-facing step is always the *last* task within a phase (Constraint 1).
- Before closing any phase: the AST-based architecture guardrail test (ADR-005 §21) passes,
  including the two explicitly-cited exceptions and no uncited new ones. **This replaces the
  original plan's "manually grep before closing" instruction** — the audit found real AST-based
  tooling already exists in this codebase; use it, don't grep by hand.
- No command-side service migrated in a given phase keeps both an old constructor-injected
  repository *and* the new `UnitOfWork`'s accessors live for the same operation (Constraint 3).
- Application-service tests for the phase are written directly against
  `UnitOfWorkFactory`/`Clock`/repository-contract test doubles — no Qt/QML test doubles, no
  concrete SQLAlchemy classes.
- Every module's/capability's typed events come from a discovery/mapping table over actual
  emitters — never a mechanical rename of old Signal field names to same-shaped class names.
- A phase is not complete until its old event path is deleted and its QML step lands
  (Constraint 4).
- Every mutated aggregate is persisted through its repository's explicit `update`/`add`, called
  before `uow.commit()` — never assumed captured by `commit()` alone.
- A phase is not closed until a real test confirms the module's/capability's existing UI/query
  path observes a fresh-`UnitOfWork` command's committed change without an app restart
  (Constraint 5).
- **NEW:** a phase is not closed until the tenant/organization isolation test matrix (ADR-005 Test
  Impact) passes for every event/hint type that phase introduced (Constraint 6) — "the tenant
  filter works" is not sufficient evidence on its own once organization scoping exists.
- Each migrated module/capability gets its own `<Name>UnitOfWork`/`<Name>UnitOfWorkFactory`
  protocol pair and thin concrete subclass — never one shared cross-module/cross-capability
  concrete `UnitOfWork`.
- No silent scope drift: if a phase's module/capability needs something ADR-005 didn't
  anticipate, that's a correction to ADR-005 itself, raised before the phase closes — not a local
  workaround.

## Sequencing Summary

| Phase | Scope | Size / Risk | Blocking dependency |
|---|---|---|---|
| 0 | Shared event contracts (no `UnitOfWork` yet), incl. `DomainEventContext` and organization-aware `ViewInvalidationHint` | None, additive | ADR-005 accepted |
| 1 | `UnitOfWork` contract + concrete impl + session-factory lifecycle + `record_event`/`context` | None, additive | Phase 0 |
| **2** | **Platform Foundation** — transaction convergence (`ApprovalService` et al.), typed events + invalidation for Platform's own 11 signals, Qt adapter consolidation, legacy bridge/cutover | **Large; new phase this revision** | Phase 1; gates every module phase below |
| 3 | `inventory_procurement` discovery + migration (pilot module) | Small, real usage | Phase 2's "Platform Domain Event Foundation Ready" |
| 4 | `hr_management` / `payroll` / `qhse` | No-op until a module needs it | Phase 0/1/2 only |
| 5 | `project_management` discovery + migration | Large; in-flight PM Collaboration Upgrade — re-verify current state before starting | Phase 3 proven; PM Collaboration Upgrade state re-confirmed |
| 6 | ~~`maintenance`~~ | **Struck — module deleted 2026-08-20** | — |
| 7 | Retire old mechanism (incl. bridge signals, `Signal` → `CallbackSignal` rename) | — | All prior phases closed |
