# ADR-005 Execution Plan: Domain Events Migration

- Companion to [ADR-005-domain-events.md](ADR-005-domain-events.md) — that
  document owns the design decisions and rationale; this document owns
  sequencing, scope per phase, and exit criteria.
- Status: draft — no phase started yet (ADR-005 itself is still "proposed,"
  not "accepted"; do not begin Phase 0 until it's accepted).
- Date: 2026-08-05, based on a direct codebase survey (module file counts,
  grep for `DomainChangeEvent(`, `_subscribe_domain_change(`, `unit_of_work`
  callers) run the same day — see "Current State Snapshot" below. Revised
  twice the same day after external review: a first pass found four
  acceptance-blocking issues in ADR-005 itself (now fixed there) and
  several phase-boundary/scoping issues here (fixed then): repository-
  contract-typed `UnitOfWork` accessors instead of raw `uow.session`, a
  session-factory-backed `UnitOfWorkFactory` instead of one closing over
  an existing process session, a stateless transactional dispatcher
  instead of a queued bus, and business-fact discovery preceding
  typed-event definition for every module, not only `maintenance`. A
  second pass, checking both documents directly against this codebase's
  actual repository/session code, found three more (now fixed): a real
  SQLAlchemy identity-map staleness risk during partial migration
  (Constraint 5, below), a missing "call the repository's `update()`
  explicitly before `commit()`" task in every module phase (this
  codebase's `Task.update()` bypasses ORM tracking entirely, confirmed by
  reading it), and module-specific `UnitOfWork`/factory typing instead of
  one cross-module concrete class.

## Non-Negotiable Constraints

These apply to every phase below, not just the ones that mention them
explicitly.

1. **Backend-first, UI-second.** Each phase's QML-facing step (updating a
   `_subscribe_domain_change` call site, wiring a controller to
   `ViewInvalidationChannel`) is always the *last* task within that phase,
   done only after that module's domain/application/infra work is fully
   tested and green. No phase's domain or application design is shaped
   around what's convenient for QML. UI/UX polish on top of the new
   mechanism is explicitly out of scope until the backend for that module
   is solid — QML/UX fixes are a separate follow-on pass per module, not
   part of this migration.
2. **Framework-agnostic application layer.** Every application service or
   transactional/post-commit handler depends only on `UnitOfWork`/
   `UnitOfWorkFactory` (and, for transactional handlers, a module-specific
   `UnitOfWork` extension exposing that module's own repository
   *contracts* — never a concrete repository class or a raw `Session`;
   see ADR-005 §2.5/§2.6), `Clock`, and repository/domain contracts —
   never on `src.ui_qml`, any `PySide6`/Qt import, `sqlalchemy`, or
   `src.infra`. This is what the repo's own `EXECUTION_SPEC.md` already
   anticipates with its future HTTP call chain (`HTTP router/controller ->
   module HTTP API -> application handler -> domain + contracts ->
   infrastructure`) sharing the same `application handler` layer as
   today's desktop path. A FastAPI adapter, when it arrives, is a new thin
   module under `src/core/modules/<module>/api/http/` or `src/api/http/`
   calling the *same* application handlers the desktop presenters call
   today — not a reason to touch `domain/` or `application/`. Each phase's
   exit criteria includes a grep check for this (see "Design Guardrails"
   below). Writing application-service tests directly against
   `UnitOfWorkFactory`/`Clock`/repository-contract test doubles (no Qt
   test doubles, no concrete SQLAlchemy classes) is how this gets proven
   per phase, not just asserted.
3. **No compatibility facades, no straddling code.** Matches this repo's
   existing hard rule in `EXECUTION_SPEC.md`: finish one slice, delete the
   old path for that slice, don't leave both mechanisms live for a module
   past its own phase's close. This includes **service-level straddling**:
   a command-side service being migrated in a given phase must stop
   reading/writing through its old constructor-injected repositories for
   the operations covered by that phase and use the active `UnitOfWork`'s
   own repository accessors instead (`uow.tasks`, not a separately
   injected `task_repo`) — a service that keeps both live for the same
   command can silently operate through two different sessions, which
   breaks `register_touched`, transactional dispatch, rollback, and
   outbox atomicity all at once, even though each half looks correct in
   isolation. This is an explicit task in every module phase below, not
   assumed to fall out of the other steps.
4. **A module phase is one atomic integration unit.** Intermediate
   backend-only commits may exist locally while a phase is in progress,
   but the phase is not merged, released, or considered complete until its
   QML-facing step is done *and* the module's old event path (its
   `Signal` fields / `DomainChangeEvent` construction sites) is deleted.
   Otherwise steps 1–6 of a phase (see Phase 2 below) could ship with
   production still depending on the old UI event path indefinitely,
   silently doubling the mechanisms a module runs on past the point this
   plan intends.
5. **No stale reads after a migrated command commits.** Confirmed
   codebase-specific risk, not hypothetical: this app builds one
   process-lifetime `Session` for `RepositoryBundle` (`src/ui_qml/shell/app.py`'s
   `build_services()`), and existing dashboard/workspace controllers hold
   their repository/session graph for the controller's entire lifetime,
   re-running the same `select()`-based read methods on every refresh
   (`workspace_controller_base.py`). SQLAlchemy does not overwrite an
   already-identity-mapped instance's attributes from a later `select()`
   result unless that instance was expired or the query used
   `populate_existing()` — and a commit on a *different*, fresh
   `uow_factory.create()` session has no effect on the long-lived
   session's identity map at all. Concretely: a migrated command can
   commit successfully, fire `ViewInvalidationHint` correctly, and the
   existing dashboard can still redisplay the old cached values. Every
   module phase's exit criteria (Phase 2B, 4B, 5) must include: **after a
   fresh-`UnitOfWork` command commits, that module's existing UI/query
   path observes the committed values without an app restart — verified
   by an actual test, not assumed.** Acceptable mitigations, in order of
   preference:
   - **Migrate the read path too.** For the entities a phase's commands
     touch, give the affected read/query methods (and, if needed, the
     controllers backing the affected views) their own fresh, short-lived
     sessions instead of the process-lifetime one — the strongest option,
     and the only one that doesn't leave the new event path coupled back
     to the legacy session.
   - **A narrow, explicit `legacy_session.expire_all()`** (or a targeted
     `session.expire(instance)` for just the affected rows) called right
     before the old UI repository re-queries, if migrating the full read
     path in the same phase isn't practical. This is an explicitly
     transitional bridge, not the destination — call it out by name in
     that phase's own notes when used, so it's a deliberate, temporary
     choice and not a silent workaround left in place indefinitely.

## Current State Snapshot (codebase survey, 2026-08-05)

The dual-purpose file is `src/core/shared/events/domain_events.py`: a
`DomainChangeEvent(category, scope_code, entity_type, entity_id,
source_event)` dataclass plus a `DomainEvents` dataclass with **31**
`Signal` fields (29 module-named + 2 generic bridge signals
`shared_master_changed`/`domain_changed`), auto-wired via `_wire_bridges()`.

| Module | Files (approx.) | Named `Signal` fields | Raw `DomainChangeEvent(` construction sites | `_subscribe_domain_change(` sites |
|---|---|---|---|---|
| hr_management | 20 | 0 | 0 | 0 |
| payroll | 20 | 0 | 0 | 0 |
| qhse | 21 | 0 | 0 | 0 |
| inventory_procurement | 127 | 12 | 0 | 1 |
| project_management | 626 | 9 | 0 | 2 |
| maintenance | 145 | 0 | 25 | 6 |
| platform/shell (cross-cutting) | — | 11 (+2 bridge) | 1 (in the file itself) | 2 |

Other confirmed facts:

- `src/infra/persistence/db/unit_of_work.py` is exactly `session_scope()`
  (25 lines) with **zero callers** anywhere in `src/` — safe to reclaim per
  ADR-005 §2.6.1.
- `src/infra/persistence/db/session_factory.py` defines `SessionLocal =
  sessionmaker(bind=engine, ...)` — a genuine session *factory* callable,
  confirmed to exist and usable as the thing `UnitOfWorkFactory` closes
  over (ADR-005 §2.6.1's round-four correction), not the single `Session`
  instance `app.py` creates from it.
- Repository *contracts* (as `ABC`s, e.g. `EmployeeRepository`) already
  exist separately from concrete repository implementations under each
  module's own `contracts/repositories/` (or platform's
  `contract/<capability>/<entity>/contracts.py`) — confirmed for
  `project_management` (`contracts/repositories/task.py`,
  `.../project.py`, etc.) and platform modules. This is what a
  module-specific `UnitOfWork` extension's repository accessors are typed
  against — no new contract layer needs inventing.
- `src/infra/composition/app_container.py`'s `build_service_graph(session)`
  and `src/ui_qml/shell/app.py`'s `build_services()` are the two places a
  `UnitOfWorkFactory` needs to be constructed and threaded through — the
  existing single `session` keeps backing today's `RepositoryBundle`
  unchanged; the new `UnitOfWorkFactory` is built alongside it, closing
  over `SessionLocal` instead.
- No `domain/events.py` or `RecordsDomainEvents` pattern exists anywhere —
  this is fully greenfield.
- No FastAPI/Flask/web framework is present in `requirements*.txt` or
  `pyproject.toml` yet — confirmed clean slate, nothing to integrate
  against today.
- **Two persistence mechanisms coexist in this codebase, confirmed by
  reading `SqlAlchemyTaskRepository`.** `Task.update()` persists through
  `update_with_version_check` (`src/infra/persistence/db/optimistic.py`)
  — a raw, parameterized `UPDATE ... WHERE id = ? AND version = ?` that
  bypasses SQLAlchemy's ORM attribute tracking entirely. `TaskAssignment`/
  `TaskDependency`, in the same module, instead mutate a tracked ORM
  row's attributes directly and rely on SQLAlchemy's own flush. Neither
  is assumed uniformly by this plan — every repository's existing
  `update`/`add` must be called explicitly by whatever mutates an
  aggregate, regardless of which mechanism that repository happens to use
  underneath (ADR-005 §2.6, §2.7).
- `src/infra/composition/repositories.py`'s `RepositoryBundle` is already
  one large flat dataclass with ~55 repository attributes spanning every
  module (`task_repo`, `project_repo`, `employee_repo`, ... all siblings).
  The module-specific `UnitOfWork`/concrete-class split (ADR-005 §2.6,
  §2.6.1) deliberately does **not** mirror this shape for the new
  per-transaction object — see Phase 1 below for why the same flatness at
  per-transaction granularity was rejected.
- No `mypy.ini`/`pyrightconfig.json`/`[tool.mypy]` exists anywhere in this
  repo, and no CI workflow runs a static type checker (the only workflow,
  `.github/workflows/release.yml`, only packages the app). Type hints are
  present throughout but not enforced by tooling today — the
  module-specific `UnitOfWork`/factory typing fix (Phase 1) is still worth
  doing for IDE correctness and documentation value, but is not fixing an
  active CI failure.

## Phase 0 — Foundational Contracts (Zero Behavior Change)

**Scope:** `src/core/shared/events/*`, `src/core/shared/time/*`,
`src/infra/events/*`, `src/infra/time/*` only. No existing file touched, no
module wired in, **no `UnitOfWork` implementation yet** — that's Phase 1,
deliberately separated below.

Tasks:

- Create `domain_event.py`, `aggregate_events.py`, `domain_event_publisher.py`
  (`TransactionalEventDispatcher` + `PostCommitEventPublisher` protocols),
  `domain_event_subscriber.py`, `subscription.py`, `view_invalidation.py`
  under `src/core/shared/events/` per ADR-005 §2.1–§2.5, §2.10. (The
  `UnitOfWork`/`UnitOfWorkFactory` protocols do **not** live here — they
  move to `src/core/shared/persistence/unit_of_work.py` in Phase 1, per
  ADR-005 §2.6.1's round-four correction; this package is events-only.)
- Create `src/core/shared/time/clock.py` (protocol only).
- Create `src/infra/events/{in_process_transactional_event_dispatcher.py,
  in_process_post_commit_event_bus.py, in_process_view_invalidation_channel.py}`
  per ADR-005 §2.9/§2.10:
  - The transactional side is the **stateless** `InProcessTransactionalEventDispatcher`
    (`dispatch(event, uow)`, no queue, no `_dispatching` flag — see §2.9's
    round-four correction for why the previous queued design was an actual
    cross-transaction bug, not just unnecessary).
  - The post-commit side is the **queued** `InProcessPostCommitEventBus`,
    with the race-free empty-queue/`_dispatching`-flip drain loop *and* a
    lock-held handler-registry snapshot before iterating in
    `_dispatch_one` (§2.9's snapshot-semantics correction).
  - `PlatformViewInvalidationHint` + `notify_platform_wide`/
    `subscribe_to_platform_wide` on `ViewInvalidationChannel`, alongside
    the tenant-scoped `ViewInvalidationHint`/`subscribe`/
    `subscribe_across_tenants` (§2.10's tenant-less-event reconciliation).
- Create `src/infra/time/system_clock.py`.
- Unit test coverage for everything above in isolation: post-commit bus
  thread-safety, its empty-queue/`_dispatching` race fix, its handler-
  snapshot-under-lock semantics; the transactional dispatcher's
  statelessness under concurrent `dispatch()` calls with different `uow`s;
  tenant isolation and the platform-wide/tenant-scoped channel split on
  `ViewInvalidationChannel`. **No aggregate-tracking or rollback tests
  here** — there is no `UnitOfWork` yet to test them against; those move
  to Phase 1.

**Exit criteria:** every new file has unit tests passing in isolation;
`git diff` touches nothing outside these four new directory trees; the app
boots unchanged (nothing imports these yet).

## Phase 1 — `UnitOfWork`: Contract, Concrete Implementation, Session Lifecycle

**Scope:** `src/core/shared/persistence/unit_of_work.py` (new — protocols),
`src/infra/persistence/db/unit_of_work.py` (reclaimed — concrete),
`src/infra/composition/app_container.py`.

Tasks:

1. Create `src/core/shared/persistence/unit_of_work.py` with the
   `UnitOfWork`/`UnitOfWorkFactory` protocols (ADR-005 §2.6, corrected):
   `__enter__`/`__exit__`, `register_touched`, `tracked_aggregates`,
   `commit` — **no `session` field, no repository accessors** on the
   shared protocol. Module-specific extensions (e.g.
   `ProjectManagementUnitOfWork` with `projects`/`tasks` typed against
   that module's existing repository contracts, plus a matching
   `ProjectManagementUnitOfWorkFactory`) are added per module, in that
   module's own `contracts/` package, as each module phase needs them —
   not invented speculatively here for modules not yet migrated.
2. Replace `session_scope()`'s body in
   `src/infra/persistence/db/unit_of_work.py` with `SqlAlchemyUnitOfWorkBase`
   per §2.6.1/§2.7/§2.9 — fold the existing try/commit/rollback/close
   shape in as a private helper used by `__enter__`/`__exit__`. Nothing
   imports `session_scope` today, so nothing else changes. **This is a
   base class only** — module-agnostic session lifecycle, aggregate
   tracking, and dispatch/outbox coordination. It declares no repository
   accessors; each module phase (2, 4, 5) adds its own thin
   `SqlAlchemy<Module>UnitOfWork(SqlAlchemyUnitOfWorkBase)` subclass under
   that module's own `infrastructure/persistence/`, not here — one
   cross-module concrete class would import every module's repository
   vocabulary into a single per-transaction object, and would also
   duplicate `RepositoryBundle`'s existing flat, all-modules-together
   shape at a granularity (per-transaction) where that cost is much less
   justified than it is for `RepositoryBundle`'s one-time construction
   (ADR-005 §2.6.1).
3. **Identity-map aggregate tracking lives here, on `SqlAlchemyUnitOfWorkBase`**
   (`self._tracked_aggregates: dict[int, RecordsDomainEvents]`,
   `id()`-keyed, per ADR-005 §2.7) — not in `src/infra/events/`, and not
   duplicated per module. It's a property of the base, not of either
   event dispatcher/bus, and not of any one module's repository
   vocabulary.
4. Each module's `SqlAlchemy<Module>UnitOfWorkFactory` (added in that
   module's own phase, not here) closes over `SessionLocal` (the existing
   `sessionmaker` in `src/infra/persistence/db/session_factory.py`) — a
   session *factory* — plus the transactional dispatcher and post-commit
   bus from Phase 0. `create()` calls `self._session_factory()` and
   returns a fresh `SqlAlchemy<Module>UnitOfWork` backed by a brand-new
   `Session` every time. **This is not the same `session` instance
   `build_service_graph` already threads through to `RepositoryBundle`**
   — that single process-lifetime session keeps backing every
   not-yet-migrated service exactly as today; each module's factory is a
   second, independent thing built alongside it, closing over
   `SessionLocal` directly rather than over `build_service_graph`'s
   `session` parameter. Phase 1 itself only proves this shape works
   end-to-end with a throwaway test subclass — the first *real* module
   subclass is added in Phase 2.
5. `build_service_graph` gains the plumbing to build a
   `SqlAlchemy<Module>UnitOfWorkFactory` per migrated module and add it
   as a new field on `ServiceGraph` — additive only, no existing field
   changes shape. (No real module factory exists until Phase 2 adds one.)
6. Tests (moved here from Phase 0, since they need a concrete class —
   using a throwaway test subclass of `SqlAlchemyUnitOfWorkBase` with no
   real repository accessors, since no module has one yet):
   - Two separate `uow_factory.create()` calls open two genuinely
     independent `Session`s — committing/rolling back one has no effect
     on the other (proves the session-factory fix, not just the absence
     of a bug).
   - Rollback discards the unit of work's tracked aggregate instances —
     a rolled-back `UnitOfWork`'s aggregates must not be reusable in a
     later one, and rollback must not affect a separately-created
     `UnitOfWork` (§2.8).
   - `register_touched` accepts a small test aggregate that subclasses
     `RecordsDomainEvents` but defines `__eq__` without `__hash__` (i.e.
     is unhashable) without raising, and registering the *same* instance
     twice does not double-count it, while two distinct equal instances
     are tracked separately (§2.7's identity-map fix). **Use a real
     `RecordsDomainEvents` subclass for this test, not a plain unrelated
     object** — the contract is typed against `RecordsDomainEvents`, and
     testing against something outside that contract doesn't exercise it.

**Exit criteria:** app boots; `SqlAlchemyUnitOfWorkBase` is constructible
(via a throwaway test subclass) and produces a genuinely fresh session per
`create()` call (tested, not assumed); zero application services
reference it yet; no real module-specific subclass exists yet (that's
Phase 2's job).

## Phase 2 — Pilot Module: `inventory_procurement`

**Rationale:** fewest real touch points among modules that actually use
the mechanism (1 subscribe site, 0 raw `DomainChangeEvent` constructions,
12 named Signals to retire) — enough real usage to prove the pattern
end-to-end without the blast radius of `project_management` or
`maintenance`.

### Phase 2A — Discovery (before writing any event class)

A named `Signal` field is a UI-refresh category, not a business fact —
one signal (e.g. `inventory_items_changed`) can legitimately be emitted by
several distinct operations (item created, renamed, deactivated,
recategorized, deleted, ...), and collapsing it back into one
identically-shaped typed event class would just rename the coarse model
without fixing it. Before writing `domain/events.py`:

1. Inventory every current emitter of each of the 12 inventory Signals
   (grep the `.emit(...)`/construction call sites feeding each named
   Signal field, not just the field declarations).
2. For each emitter, record the actual business operation it represents,
   which aggregate raises it, and which existing view(s) it currently
   refreshes. A table shaped like:

   | Current emitter | Business operation | Proposed typed event | UI hint(s) affected |
   |---|---|---|---|
   | `ItemService.create_item` | Item created | `InventoryItemCreated` | item collection view |
   | `ItemService.rename_item` | Item renamed | `InventoryItemRenamed` | item detail/list |
   | `StockService.reserve` | Reservation created | `StockReserved` | balances + reservations |
   | `StockService.release` | Reservation released | `StockReservationReleased` | balances + reservations |

3. Define `domain/events.py`'s typed events **from this table**, not from
   the 12 Signal *names* directly — a single old Signal may map to several
   typed events (as above), and a single typed event's post-commit
   handler may need to raise more than one `ViewInvalidationHint` (see the
   "UI hint(s) affected" column) if it was previously refreshing more than
   one view.

This discovery step is checked in as part of the phase's own working
notes before any code changes, the same discipline Phase 5 already
requires for `maintenance`'s 25 raw construction sites — applied here too,
since named Signals hide the same granularity problem, just less visibly.

### Phase 2B — Migration (backend first, QML step deliberately last)

1. Add `src/core/modules/inventory_procurement/contracts/unit_of_work.py`
   with `InventoryUnitOfWork(UnitOfWork, Protocol)` (`items`/`balances`/
   `reservations`/... accessors typed against this module's existing
   repository contracts) and `InventoryUnitOfWorkFactory`; add the
   concrete `SqlAlchemyInventoryUnitOfWork(SqlAlchemyUnitOfWorkBase)` and
   `SqlAlchemyInventoryUnitOfWorkFactory` under
   `infrastructure/persistence/unit_of_work.py`, closing over `SessionLocal`
   (ADR-005 §2.6, §2.6.1 — this is the first *real* module subclass;
   Phase 1 only proved the base class shape).
2. Add `src/core/modules/inventory_procurement/domain/events.py` with the
   typed events from the Phase 2A table.
3. Adopt `RecordsDomainEvents` + injected `Clock` on the aggregates that
   raise these.
4. Repository `register_touched` calls on load/add for inventory
   repositories (automatic via the module's `InventoryUnitOfWork`
   repository accessors, per ADR-005 §2.6).
5. **Migrate the command-side services covered by this phase off their
   old constructor-injected repositories and onto the active `UnitOfWork`'s
   own repository accessors** (Constraint 3) — a service must not keep
   both an old injected `ItemRepository` *and* `uow.items` live for the
   same command; whichever operations this phase covers switch fully.
6. **Call the mutated repository's `update(aggregate)`/`add(aggregate)`
   explicitly after every aggregate mutation, before `uow.commit()`**
   (Constraint 5 does not cover this — this is ADR-005 §2.6/§2.7's
   round-five correction: `commit()` alone does not persist a mutation).
   Confirm per aggregate whether its repository persists through tracked
   ORM attribute mutation or an explicit optimistic-concurrency call (this
   module hasn't been read yet the way `project_management`'s `Task` was —
   check `inventory_procurement`'s own repositories for the same
   raw-`UPDATE`-vs-tracked-ORM split before assuming either one).
7. Add `application/event_handlers/view_invalidation.py` with
   module-owned constants (mirroring ADR-005 §2.11's
   `ProjectManagementInvalidation` example); add a `transactional.py` only
   if the Phase 2A table surfaced a real cross-aggregate case (none is
   evident from the initial survey — confirm against the table before
   writing one speculatively).
8. Wire `register_post_commit_handlers` into the composition root's
   `SubscriptionRegistry`.
9. Full test pass on 1–8 before touching anything QML-facing.
10. **Only now:** update the one existing `_subscribe_domain_change` call
    site (the dashboard) to consume `ViewInvalidationChannel` instead —
    and apply Constraint 5's staleness mitigation for whichever entities
    this phase's commands touch (migrate the dashboard's read path to a
    fresh session, or an explicit, called-out `expire_all()`/
    `expire(instance)` bridge).
11. Delete the 12 inventory-owned fields out of the old `DomainEvents`
    dataclass, and their now-dead emitters, in the same phase close
    (Constraint 4 — no straddling past this point).

**Exit criteria:** inventory module tests green; dashboard refresh behavior
unchanged from a user's perspective; **a real test confirms the dashboard
observes a fresh-`UnitOfWork` command's committed change without an app
restart** (Constraint 5 — not merely "the hint fired"); zero
inventory-owned fields left in the old `DomainEvents` dataclass; grep
confirms no `ui_qml`/`PySide6`/
`sqlalchemy`/`src.infra` import in `inventory_procurement/domain/` or
`/application/`; no inventory command-side service still holds both an
old injected repository and the new `UnitOfWork` for the same operation.

## Phase 3 — `hr_management`, `payroll`, `qhse`: No Migration Needed Yet

These three have **zero** current domain-event usage — there is nothing to
migrate and no old Signal fields to retire. Do not manufacture events for
them speculatively. When one of these modules first needs a domain event
for a real feature, it adopts the Phase 0/1 contracts directly as a new
consumer — it never touches the old `DomainEvents` dataclass at all, since
it never used it.

## Phase 4 — `project_management` (Coordinate With PM Collaboration Upgrade First)

**Risk flag:** this is the largest module in the codebase (626 files, 9
named Signals, 2 subscribe sites) *and*, per current project tracking, the
PM Collaboration Upgrade is mid-flight here with backend Phases 0/1/4 done
and a large uncommitted diff, QML UI + Phases 2/3 still pending. **Do not
start this phase until that upgrade's own backend work is committed and
stable** — migrating the event mechanism underneath an in-flight,
uncommitted backend change risks conflicts neither piece of work can see
coming. Confirm with the user before starting this phase specifically.

### Phase 4A — Discovery

Same discipline as Phase 2A, applied to the 9 named signals
(`project_changed`, `tasks_changed`, `timesheet_periods_changed`,
`costs_changed`, `resources_changed`, `baseline_changed`,
`register_changed`, `collaboration_changed`, `portfolio_changed`): inventory
every emitter feeding each signal, map each to its actual business
operation/aggregate/affected view(s), and define typed events from that
table — not from the 9 signal names directly. Given this module's size,
expect several typed events per signal, not a 1:1 rename.

### Phase 4B — Migration

Same shape as Phase 2B's steps 1–11, scaled to the Phase 4A table and the
2 subscribe sites (dashboard, financials refresh mixins) — including
step 1's `ProjectManagementUnitOfWork`/`ProjectManagementUnitOfWorkFactory`
+ `SqlAlchemyProjectManagementUnitOfWork` (this is the module ADR-005's
own worked examples already use, §2.5/§2.6 — reuse those, don't redefine
them differently here), the explicit command-side-service migration off
old injected repositories (Constraint 3), the explicit
`update`/`add`-before-`commit()` call on every mutated aggregate (step 6 —
check whether `project_management`'s other repositories share `Task`'s
raw-`UPDATE`-via-`update_with_version_check` pattern or the tracked-ORM
pattern `TaskAssignment`/`TaskDependency` use, per-repository, before
assuming either one), and the staleness mitigation for the dashboard and
financials refresh mixins (Constraint 5).

**Exit criteria:** same shape as Phase 2, plus: no regression in the
PM Collaboration Upgrade's own in-flight work (run its existing test
suite, not just the new event tests).

## Phase 5 — `maintenance` (Highest Risk — Do Last)

**Rationale for going last:** this module has the heaviest actual abuse of
the old pattern — 25 raw `DomainChangeEvent(...)` constructions scattered
directly across `application/*_service.py` files, plus 6 subscribe sites —
despite having *zero* dedicated Signal fields (it rides the generic
`domain_changed`/`shared_master_changed` bridge entirely). Deliberately
scheduled after Phases 2 and 4 so the pattern — including the discovery-
before-typing discipline now required for every module (Phases 2A/4A) —
has been proven twice on modules with cleaner starting points first.

Tasks: same shape as Phase 2B (steps 1–11 — including its own
`MaintenanceUnitOfWork`/`MaintenanceUnitOfWorkFactory` +
`SqlAlchemyMaintenanceUnitOfWork`, the explicit `update`/`add`-before-
`commit()` call per aggregate, and the staleness mitigation for this
module's 6 subscribe sites), preceded by the construction-site-to-typed-
event mapping table this phase already required (all 25 raw
`DomainChangeEvent(...)` sites, before touching any of them) — the same
table shape as Phase 2A/4A, just starting from raw construction call
sites instead of named Signal fields.

## Phase 6 — Platform Signals: Bridge Artifacts Are Deleted, Named Signals Are Classified Individually

**Correction from the initial draft of this phase:** the 2 generic bridge
signals (`shared_master_changed`, `domain_changed`) are **not** platform
business facts alongside the 11 named ones — they are transport/bridge
artifacts of the *old* mechanism itself (the generic
`DomainChangeEvent`-carrying fields `_wire_bridges()` wires up). They have
no independent meaning to classify; they simply cease to exist when
`src/core/shared/events/domain_events.py` — `DomainEvents`, `_wire_bridges()`,
`_BRIDGE_SPECS` — is deleted in Phase 7. Nothing needs deciding about
them specifically; they're folded into Phase 7's retirement, not this
phase's decision.

**What this phase actually decides** is the 11 named platform-wide
signals not owned by any business module: `auth_changed`,
`employees_changed`, `organizations_changed`, `sites_changed`,
`departments_changed`, `calendars_changed`, `documents_changed`,
`parties_changed`, `access_changed`, `modules_changed`,
`approvals_changed`. **Each is classified independently, not decided as
one all-or-nothing group** — some may be real business facts (a typed
platform domain event under `src/core/platform/domain/events.py`, e.g.
`employees_changed` covering `EmployeeHired`/`EmployeeTransferred`-shaped
facts), others may be purely UI-invalidation with no underlying domain
event at all (e.g. `modules_changed`, if its only emitters are
configuration/feature-flag toggles with no domain meaning beyond "refresh
this view"). A worked classification table, built from each signal's
actual emitters (same discovery discipline as Phases 2A/4A/5), precedes
any code change here:

| Signal | Likely classification | Notes |
|---|---|---|
| `auth_changed` | Split — some emitters may be typed events (e.g. `UserSignedIn`, `RoleAssignmentsChanged`), others pure UI/session invalidation | Needs its emitters inventoried before deciding |
| `employees_changed` | Typed business facts, where emitters represent real HR operations | |
| `sites_changed` | Typed business facts, where emitters represent real operations | |
| `modules_changed` | Likely UI/config invalidation only | Confirm no domain-meaningful emitter exists before settling this |
| *(remaining 7 signals)* | To be classified the same way | Not yet surveyed at this level of detail |

This phase is blocked on completing that classification and getting user
sign-off on each row, not on engineering effort.

## Phase 7 — Retire the Old Mechanism

Once every module and the platform layer have migrated (Phase 6's
classification fully applied, with each platform signal either promoted
to a typed event or explicitly kept as plain UI invalidation on purpose),
delete `src/core/shared/events/domain_events.py` in full — the
`DomainEvents` dataclass, `_wire_bridges()`, `_BRIDGE_SPECS`, and the 2
bridge signals along with it. No facade, no re-export shim, per this
repo's existing no-facade rule.

## Design Guardrails Enforced Every Phase

- The QML-facing step is always the *last* task within a phase (see
  Constraint 1) — never a co-requisite of the domain/application design
  for that phase.
- Before closing any phase: grep that module's `domain/` and
  `application/` for `PySide6`/`ui_qml`/`sqlalchemy`/`src.infra` imports —
  must be zero of all four. This is the same discipline that makes a
  future FastAPI HTTP adapter a pure addition alongside `src/ui_qml/`,
  sharing the same application-handler layer, rather than a rewrite (see
  Constraint 2). A transactional handler reaching a concrete repository
  class or a raw `Session` is exactly the bug round four found in
  ADR-005 §2.5 — this grep is what would have caught it.
- No command-side service migrated in a given phase keeps both an old
  constructor-injected repository *and* the new `UnitOfWork`'s repository
  accessors live for the same operation (Constraint 3) — check this
  explicitly per phase, not assumed from "the new mechanism was added."
- Application-service tests for the phase are written directly against
  `UnitOfWorkFactory`/`Clock`/repository-contract test doubles — no
  Qt/QML test doubles, no concrete SQLAlchemy classes — as the concrete
  proof of Constraint 2, not just a design claim.
- Every module phase's typed events come from a discovery/mapping table
  over that module's actual emitters (Phases 2A/4A, and Phase 5's
  construction-site table) — never a mechanical rename of old Signal
  field names to same-shaped class names.
- A phase is not complete until its old event path is deleted and its
  QML step lands (Constraint 4) — no phase ships with two live mechanisms
  for the same module past its own close.
- Every mutated aggregate is persisted through its repository's explicit
  `update`/`add`, called before `uow.commit()` — never assumed to be
  captured by `commit()` alone (round five; this codebase's own
  `Task.update()`, a raw version-checked `UPDATE` bypassing ORM tracking
  entirely, is why this can't be assumed uniformly).
- A phase is not closed until a real test confirms the module's existing
  UI/query path observes a fresh-`UnitOfWork` command's committed change
  without an app restart (Constraint 5) — "the `ViewInvalidationHint`
  fired" is not sufficient evidence on its own; SQLAlchemy's identity map
  can leave a long-lived session's cached instance stale even after a
  correct hint is delivered.
- Each migrated module gets its own `<Module>UnitOfWork`/
  `<Module>UnitOfWorkFactory` protocol pair and thin
  `SqlAlchemy<Module>UnitOfWork(SqlAlchemyUnitOfWorkBase)` concrete class
  — never one shared cross-module concrete `UnitOfWork` accumulating
  every migrated module's repository accessors.
- No silent scope drift: if a phase's module turns out to need something
  ADR-005 didn't anticipate (e.g. a real cross-aggregate transactional
  handler in `inventory_procurement`), that's a correction to ADR-005
  itself, raised before the phase closes — not a local workaround.

## Sequencing Summary

| Phase | Scope | Size / Risk | Blocking dependency |
|---|---|---|---|
| 0 | Shared event contracts (no `UnitOfWork` yet) | None, additive | ADR-005 accepted |
| 1 | `UnitOfWork` contract + concrete impl + session-factory lifecycle | None, additive | Phase 0 |
| 2A/2B | `inventory_procurement` discovery + migration (pilot) | Small, real usage | Phase 1 |
| 3 | `hr_management` / `payroll` / `qhse` | No-op until a module needs it | Phase 0/1 only |
| 4A/4B | `project_management` discovery + migration | Large; in-flight PM Collaboration Upgrade | Phase 2 proven; PM Collaboration Upgrade backend stable + user confirmation |
| 5 | `maintenance` | Large; most tangled call sites (25 raw constructions) | Phases 2 and 4 proven |
| 6 | Platform signals — per-signal classification | Blocked on a decision, not effort | User sign-off on classification table |
| 7 | Retire old mechanism (incl. bridge signals) | — | All prior phases closed |
