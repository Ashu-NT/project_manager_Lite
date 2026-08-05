# ADR-005: Domain Events

- Status: proposed
- Date: 2026-08-05 (revised repeatedly on 2026-08-05 — three full team-review
  rounds plus numerous targeted follow-up corrections; see "Open Items
  Before This Can Move to Accepted" for the complete resolved list)

## Context

`src/core/shared/events/domain_events.py` currently does two unrelated jobs
under one name:

1. A **UI refresh notifier** — after a change, tell whichever desktop
   controllers are alive right now to re-fetch their view. In-memory,
   synchronous, best-effort, same process only.
2. An attempt at **domain events** — the same file also enumerates roughly
   30 hardcoded `Signal` fields, one per module entity
   (`tasks_changed`, `inventory_items_changed`, `auth_changed`, ...), each
   carrying a generic `DomainChangeEvent(category, scope_code, entity_type,
   entity_id, source_event)` — four free-form strings and an ID.

This has already been called out once, in
[ADR-PF-011](ADR-PF-011-durable-integration-outbox-inbox.md): *"the shared
process-local domain events are UI refresh signals; neither is a durable
integration mechanism."* ADR-PF-011 answers the *integration* half of that
observation and explicitly defers the *domain event* half. This ADR is
that other half. **Integration events are out of scope here** — ADR-PF-011
owns that decision; §2.12 only clarifies one ordering constraint between
the two.

**This has been through three full rounds of team review, plus numerous
targeted follow-up corrections raised individually afterward.** Round one
corrected an absolute "never before commit" rule and caught a
composition-root pattern that would have recreated the exact problem this
ADR removes. Round two found the fix for round one was described but never
actually wired into one design, plus a hint object that couldn't satisfy
its own test. Round three found the wiring still had a real bug (events
referencing a field the event class didn't declare), an ownership
contradiction between two sections, an aggregate-discovery gap in the
draining loop, a missing rollback-safety rule, a thread-safety gap in the
bus sketch, and a placement inconsistency in the `Clock` example. The
follow-up rounds after that (each individually resolved — see "Open Items
Before This Can Move to Accepted" for the full list) found: `Clock`'s
final placement corrected twice, a tenant-isolation gap in the
view-invalidation channel, a missing link between transactional handlers
and the current transaction, a real race in the bus's drain loop, the
handler shape promoted to a named contract, an unsafe `set`-based
aggregate tracker, and the concrete `UnitOfWork`'s file placement and
creation site. All are fixed below.

## Decision

### 2.1 Domain events — typed, immutable, bounded-context-owned, tenant-aware

Each module declares its **own** domain event types, as frozen dataclasses,
named in the past tense, in its own `domain/events.py`:

```python
# src/core/modules/project_management/domain/events.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True)
class TaskReassigned:
    tenant_id: str
    task_id: str
    project_id: str
    previous_assignee_id: str | None
    new_assignee_id: str | None
    occurred_at: datetime

@dataclass(frozen=True, slots=True)
class TaskCompleted:
    tenant_id: str
    task_id: str
    project_id: str
    occurred_at: datetime
```

**Correction:** the previous revision's post-commit adapter referenced
`e.tenant_id`, but the event classes it was constructed from never
declared that field — it would have failed at the first call. Every
tenant-owned aggregate's domain events carry `tenant_id` explicitly,
recorded from the aggregate's own tenant, e.g.:

```python
self._record_event(
    TaskReassigned(
        tenant_id=self.tenant_id,
        task_id=self.id,
        project_id=self.project_id,
        previous_assignee_id=previous_assignee_id,
        new_assignee_id=new_assignee_id,
        occurred_at=clock.now(),
    )
)
```

For genuinely platform-wide events that have no tenant, use
`tenant_id: str | None` on that specific event type, or — if a module's
events are a real mix of tenant-scoped and platform-wide facts — define
separate event bases/contracts for each rather than one shared optional
field used inconsistently. **Never invent a placeholder tenant ID** to
force a value into a required field; a genuinely tenant-less event should
say so in its type, not fake a tenant.

`slots=True` on every event class, consistently. Fields use `str` IDs for
now (no module in this codebase currently has typed ID value objects);
adopt typed IDs in domain events once/if a module introduces them for
other reasons.

A minimal shared marker lives in `src/core/shared/events/`:

```python
# src/core/shared/events/domain_event.py
from typing import Protocol, runtime_checkable
from datetime import datetime

@runtime_checkable
class DomainEvent(Protocol):
    occurred_at: datetime
```

Typing contract only — zero business vocabulary.

### 2.2 Aggregate event recording

```python
# src/core/shared/events/aggregate_events.py
class RecordsDomainEvents:
    _pending_domain_events: list[DomainEvent]

    def _ensure_event_storage(self) -> None:
        # Defensive, not strictly required: this codebase's domain objects
        # are always rebuilt via an explicit mapper calling the dataclass's
        # own constructor (e.g. `ProjectBaseline(id=obj.id, ...)` in
        # infrastructure/persistence/mappers/*.py), never instantiated
        # directly by SQLAlchemy's declarative machinery — so __init__
        # does run on every rehydrated aggregate today. Cheap insurance
        # against that assumption changing later, not a workaround for a
        # known-broken path.
        if not hasattr(self, "_pending_domain_events"):
            self._pending_domain_events = []

    def _record_event(self, event: DomainEvent) -> None:
        self._ensure_event_storage()
        self._pending_domain_events.append(event)

    def domain_events(self) -> tuple[DomainEvent, ...]:
        """Read-only snapshot. Does not clear anything."""
        self._ensure_event_storage()
        return tuple(self._pending_domain_events)

    def clear_domain_events(self) -> None:
        """Called by the unit of work only after commit has succeeded."""
        self._ensure_event_storage()
        self._pending_domain_events.clear()
```

The no-op guard runs before any mutation or recording:

```python
class Task(RecordsDomainEvents):
    def reassign(self, new_assignee_id: str | None, *, clock: Clock) -> None:
        if self.assignee_id == new_assignee_id:
            return  # no-op: nothing changed, nothing recorded

        previous_assignee_id = self.assignee_id
        self.assignee_id = new_assignee_id
        self._record_event(
            TaskReassigned(
                tenant_id=self.tenant_id,
                task_id=self.id,
                project_id=self.project_id,
                previous_assignee_id=previous_assignee_id,
                new_assignee_id=new_assignee_id,
                occurred_at=clock.now(),
            )
        )
```

### 2.3 `Clock` — protocol in `shared/time/`, implementation in `infra/time/`

The previous revision put both the `Clock` protocol *and* the concrete
`SystemClock` in the same file — directly contradicting this ADR's own
rule that concrete implementations live in infrastructure, not in
`shared/`. Split. **Corrected again, semantically: `Clock` is not
events-specific vocabulary — it's a general time abstraction that simply
happens to be used by the event-recording mixin here — so it does not
belong nested under either package's `events/` folder.** It gets its own
small `time/` package on each side instead:

```python
# src/core/shared/time/clock.py
from typing import Protocol
from datetime import datetime

class Clock(Protocol):
    def now(self) -> datetime: ...
```

```python
# src/infra/time/system_clock.py
from datetime import datetime, timezone
from src.core.shared.time.clock import Clock

class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
```

`SystemClock` lives beside the event bus implementations only in the
sense that both are under `src/infra/`, not in the same package — it gets
its own `src/infra/time/` (§2.3.1 file tree), separate from
`src/infra/events/` and from `src/infra/platform/`'s more general,
not-time-specific grab-bag of app-wide utilities, since a future consumer
that needs `Clock` but has nothing to do with domain events (e.g. an
audit-log timestamp, a rate-card effective-date check) should not have to
import through an `events` package to get it.

### 2.3.1 File placement (full tree, corrected)

```text
src/core/shared/events/
  domain_event.py                  # DomainEvent marker protocol
  aggregate_events.py              # RecordsDomainEvents mixin
  domain_event_publisher.py        # TransactionalEventPublisher + PostCommitEventPublisher
  domain_event_subscriber.py       # TransactionalEventHandler/PostCommitEventHandler
                                    # + TransactionalEventSubscriber/PostCommitEventSubscriber
  subscription.py                  # Subscription protocol (dispose)
  unit_of_work.py                  # UnitOfWork + UnitOfWorkFactory protocols (§2.6/§2.7)
  view_invalidation.py             # ViewInvalidationHint + ViewInvalidationHandler
                                    # + channel contract
  signal.py                        # existing generic Signal[T] primitive — unchanged

src/core/shared/time/
  clock.py                         # Clock protocol — general time abstraction,
                                    # not events-specific; used BY aggregate_events.py

src/infra/events/
  in_process_transactional_event_bus.py  # FAIL_FAST, handlers take (event, uow)
  in_process_post_commit_event_bus.py    # ISOLATE_AND_CONTINUE, handlers take (event)
  in_process_view_invalidation_channel.py  # non-marshaling concrete channel

src/infra/time/
  system_clock.py                  # concrete Clock implementation

src/infra/persistence/db/
  unit_of_work.py                  # REPLACED (0 callers on session_scope() — §2.6.1):
                                    # now the concrete SqlAlchemyUnitOfWork (aggregate
                                    # tracking + event coordination); owns a Session
                                    # plus the two buses above as collaborators

src/infra/composition/
  app_container.py                 # build_service_graph(session) — creation site for
                                    # SqlAlchemyUnitOfWork/UnitOfWorkFactory, alongside
                                    # today's RepositoryBundle (§2.6.1)

src/ui_qml/infrastructure/events/
  qt_view_invalidation_channel.py   # Qt main-thread-marshaling channel
```

Contracts and the one genuinely generic primitive (`Signal`) stay in
`shared/events/`; `Clock` gets its own `shared/time/`/`infra/time/` pair
since it's general-purpose, not events-specific; every other concrete
implementation that isn't Qt-specific
lives in `infra/events/`; the Qt-marshaling implementation is UI-owned
under `ui_qml/`, keeping Qt imports out of `src/core/` and `src/infra/`.

### 2.4 Dispatch policy — transactional vs. post-commit

**Transactional domain handlers** run *before* commit, in the same unit
of work as the aggregate change that raised the event — e.g.
`TaskCompleted` → update project progress, committed together or not at
all. A transactional handler failure rolls back the whole transaction.

**Post-commit handlers** run only *after* commit, and are limited to **UI
invalidation and other reactions that are explicitly best-effort and safe
to lose.** Anything that must not be lost — a durable notification, an
email receipt, an integration event — is never a bare post-commit
callback; it's either part of the transactional phase (the outbox write,
per §2.12) or a durably-scheduled job.

### 2.5 Two *pairs* of contracts — transactional handlers need the current transaction, post-commit handlers must not have it

The previous revision defined one publisher/subscriber pair with handler
signature `Callable[[E], None]` and used it for both buses. That's a real
gap: a transactional handler that needs to update a *different* aggregate
as part of the same transaction (§2.4's own motivating example —
`TaskCompleted` → update `Project`) has no way to know which repository,
session, or transaction to use. A handler registered once, at application
startup, closing over a repository built some other way could easily end
up reading/writing through a different session than the aggregate that
raised the event — silently breaking the very atomicity guarantee §2.4
promises.

**Fix: transactional and post-commit handlers have genuinely different
signatures, not the same one reused.** A transactional handler receives
the *current* unit of work as an explicit parameter; a post-commit
handler deliberately does not, since by the time it runs the transaction
is already closed and touching it further would be actively wrong.

```python
# src/core/shared/events/domain_event_publisher.py
class TransactionalEventPublisher(Protocol):
    def publish(self, event: DomainEvent, uow: UnitOfWork) -> None: ...

class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
```

**Further correction: the handler shape must be a named contract element,
not an inline `Callable[...]` repeated at every use site.** An anonymous
`Callable[[E, UnitOfWork], None]` typed directly on `subscribe()`'s
parameter is easy to let drift — the bus's internal handler registry, the
registration-function signatures in §2.11, and any future adapter all had
their own copy of the same shape with nothing forcing them to agree, and
nothing for a type checker or an IDE to name back at you when they don't.
**Fix: each handler shape gets its own `Protocol`, and every signature
that accepts or stores a handler is typed against that `Protocol`, never
against a raw `Callable`:**

```python
# src/core/shared/events/domain_event_subscriber.py
class TransactionalEventHandler(Protocol[E]):
    def __call__(self, event: E, uow: UnitOfWork) -> None: ...

class PostCommitEventHandler(Protocol[E]):
    def __call__(self, event: E) -> None: ...

class TransactionalEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E], handler: TransactionalEventHandler[E]
    ) -> Subscription: ...

class PostCommitEventSubscriber(Protocol):
    def subscribe(
        self, event_type: type[E], handler: PostCommitEventHandler[E]
    ) -> Subscription: ...
```

Any plain function or lambda with a matching parameter list still
satisfies these structurally — `Protocol` with `__call__` doesn't require
handlers to subclass anything, it only gives the shape a name. That name
is what now appears everywhere a handler is stored or passed — the bus's
internal registry (§2.9) and the registration-function parameters (§2.11)
— instead of each of those re-declaring `Callable[[E, UnitOfWork], None]`
or `Callable[[E], None]` on its own and risking the two falling out of
sync.

A cross-aggregate transactional handler now has an unambiguous answer to
"which repository and transaction":

```python
# src/core/modules/project_management/application/event_handlers/transactional.py
def handle_task_completed(event: TaskCompleted, uow: UnitOfWork) -> None:
    project_repo = SqlAlchemyProjectRepository(uow.session)
    project = project_repo.get(event.project_id)
    project.record_progress_from_task_completion(event.task_id)
    uow.register_touched(project)  # so ITS events get drained too, per §2.7
```

`uow.session` is the *same* SQLAlchemy session the triggering `Task`
aggregate was loaded and saved through — not a new one, not a singleton
repository with independent lifetime. `SqlAlchemyProjectRepository(uow.session)`
mirrors exactly how this codebase's application services already build
their repositories today (constructor-injected `Session`, per the
existing pattern — see §2.6's note); a transactional handler builds one
the same way, just handed the session through `uow` instead of through
`__init__`.

### 2.6 Who owns dispatch — the unit of work, not application services (contradiction fixed)

The previous revision's migration text said to "wire `DomainEventPublisher`
through application services," while §2.5 (as it was) described the unit
of work doing all the collecting, dispatching, outbox-mapping, committing,
and clearing. **Those are two different orchestration models, and having
both described in the same document means dispatch behavior would depend
on which code path a given change went through — possibly double-dispatching,
possibly not dispatching at all.**

**Decision: the unit of work (or a dedicated event coordinator it owns) is
the single place that collects, dispatches, and clears aggregate events.**
Application services do not depend on `TransactionalEventPublisher`
directly — they depend on the unit of work and a `Clock`:

```python
class TaskApplicationService:
    def __init__(self, uow_factory: UnitOfWorkFactory, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def reassign_task(self, task_id: str, assignee_id: str | None) -> None:
        with self._uow_factory.create() as uow:
            task = uow.tasks.get(task_id)
            task.reassign(assignee_id, clock=self._clock)
            uow.commit()  # event coordination happens inside commit()
```

**`UnitOfWork` — the aggregate-tracking, event-coordinating abstraction —
is new; it does not exist in this codebase today.** Checked before
writing this: application services currently take an already-constructed
SQLAlchemy `Session` plus already-constructed repositories directly as
constructor parameters, all wired together at the composition root.
There *is* a same-named file, `src/infra/persistence/db/unit_of_work.py`
— but it currently contains only a `session_scope()` transaction-boundary
helper, not a class with aggregate tracking or event coordination; see
§2.6.1 for the exact distinction, why that helper turns out to have zero
callers, and why the concrete implementation reclaims that same file
rather than being parked under a different name. This ADR's `UnitOfWork`
is deliberately minimal,
and does **not** propose replacing the existing constructor-injection
pattern everywhere. Its only new responsibilities are event coordination
(§2.7) and exposing the same `session` a handler needs to build a
repository the same way services already do:

```python
class UnitOfWork(Protocol):
    session: Session  # the same Session type already used throughout this codebase

    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def register_touched(self, aggregate: RecordsDomainEvents) -> None: ...
    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]: ...
    def commit(self) -> None: ...

class UnitOfWorkFactory(Protocol):
    def create(self) -> UnitOfWork: ...
```

**Correction: the usage example above (`with self._uow_factory.create() as
uow:`) requires context-manager support that the protocol didn't
declare.** `__enter__`/`__exit__` are part of the contract, not an
implementation-only detail — `__exit__` rolls back (discarding the
aggregate instances per §2.8) if an exception propagated out of the
`with` block before `commit()` was reached; on a clean exit it does
nothing further. Unlike the existing `session_scope()` (§2.6.1),
`__exit__` never auto-commits on clean exit — `commit()` must always be
called explicitly inside the block, since that's where event coordination
happens (§2.7) and it must never happen implicitly. `UnitOfWorkFactory` is
the thing application services actually hold (`uow_factory: UnitOfWorkFactory`
in the example above) — it, not `UnitOfWork` itself, is the constructor
dependency, since a fresh `UnitOfWork` is created per transaction.

`tracked_aggregates()` returns a `tuple`, not a `frozenset` — see §2.7:
domain aggregates are not guaranteed hashable, so a `set`/`frozenset` of
them is not a safe contract return type.

Aggregates loaded through `uow.tasks`/`uow.projects`/etc.-style
convenience accessors (however a given concrete `UnitOfWork` chooses to
expose them) call `register_touched` automatically on load; a
transactional handler building its own repository directly from
`uow.session` (as `handle_task_completed` does above) calls
`uow.register_touched(project)` itself, explicitly, since the UoW has no
way to know about that repository access otherwise.

The dependency shape:

```text
Application service
├── UnitOfWork (or UnitOfWorkFactory)
└── Clock

UnitOfWork / EventCoordinator (owned by the UoW, not the application service)
├── transactional_event_bus  (TransactionalEventPublisher, FAIL_FAST,
│                             handlers receive (event, uow))
├── post_commit_event_bus    (PostCommitEventPublisher, ISOLATE_AND_CONTINUE,
│                             handlers receive (event) only)
├── integration event mapper (selects + builds IntegrationEventEnvelope rows)
└── outbox repository
```

Ordinary application services never need either publisher dependency
merely to publish events an aggregate already recorded — that would let
two different call paths dispatch the same event twice, or let dispatch
depend on which service happened to be used. A service *would* take
`PostCommitEventPublisher` directly only if it needs to publish something
that isn't tied to a specific aggregate's recorded events at all (an edge
case, not the common path) — it would never take
`TransactionalEventPublisher` directly, since publishing transactionally
without the current `uow` is exactly the gap this section closes.

#### 2.6.1 Concrete placement and creation site

**Correction: `src/infra/persistence/db/unit_of_work.py` already exists —
checked, and it is not this abstraction.** Its entire content is one
function:

```python
# src/infra/persistence/db/unit_of_work.py — EXISTING code, unchanged by this ADR
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

That's a bare transaction-boundary helper: get a `Session`, commit or
roll it back, always close it. It has no aggregate tracking, no
`register_touched`/`tracked_aggregates`, and no event coordination — it
solves "give every repository the same session for one transaction,"
which is a real but different problem than this ADR's "know which
aggregates changed so their recorded events can be drained and
dispatched."

**Correction (superseding the first cut at this section): `session_scope()`
has zero callers anywhere in `src/`.** Checked directly — it is defined
and never imported or invoked elsewhere; `src/ui_qml/shell/app.py` builds
its session with `SessionLocal()` directly, not through this helper. It
is dead code left over from the platform layer-first restructure, which
deliberately chose the name `unit_of_work.py` for this file (see
`docs/repo_structure_plan/README.md`/`EXECUTION_SPEC.md`) without yet
putting a real Unit of Work behind it.

**Given that, parking the real implementation under an awkwardly
disambiguated `sqlalchemy_unit_of_work.py` — the first cut at this
section — was the wrong call.** Enterprise-standard naming says the file
called `unit_of_work.py` should *be* the Unit of Work; a reader grepping
for the pattern expects to find it there, not a bare session-scope
helper wearing its name. Since nothing depends on `session_scope()`,
there is no real migration cost to reclaiming the name — no import site
needs repointing. **Decision: `SqlAlchemyUnitOfWork` claims
`src/infra/persistence/db/unit_of_work.py` directly; `session_scope()`'s
try/commit/except-rollback/finally-close shape is folded in as the
private helper the new class's `__enter__`/`__exit__` use internally**
(the same behavior, just no longer a free-standing, unused public
function) — nothing is deleted outright, since that same shape is
exactly what rollback-on-exception (§2.8) needs:

```text
src/core/shared/events/unit_of_work.py   # UnitOfWork + UnitOfWorkFactory protocols (contract only — §2.6)
src/infra/persistence/db/unit_of_work.py  # REPLACED — was session_scope() only (0 callers);
                                          # now the concrete SqlAlchemyUnitOfWork, with the
                                          # same try/commit/rollback/close shape folded in
                                          # as a private helper used by __enter__/__exit__
```

`SqlAlchemyUnitOfWork` sits under `src/infra/persistence/db/` — the same
package as `engine.py`/`session_factory.py` — rather than under
`src/infra/events/`, since its primary job is transaction and
aggregate-tracking, not event dispatch; it *owns* a
`transactional_event_bus`/`post_commit_event_bus` pair (both from
`src/infra/events/`) as collaborators, the same way it owns a `Session`.

**Where instances get created:** composition in this codebase is
centralized, not per-module — repositories are already built this way in
`src/infra/composition/repositories.py` (`RepositoryBundle`, one instance
per `Session`, e.g. `task_repo=SqlAlchemyTaskRepository(session)`) and
wired together in `src/infra/composition/app_container.py`'s
`build_service_graph(session)` / `build_service_dict(session)`, both
called from `src/ui_qml/shell/app.py`'s `build_services()` with the one
process-lifetime `Session` that function creates. A `UnitOfWork`/
`UnitOfWorkFactory` is created the same way, at the same place —
`build_service_graph(session)` builds one `SqlAlchemyUnitOfWork` (or a
factory closing over `session`, the two registered buses, and the
outbox repository) alongside today's `RepositoryBundle`, and hands it
into each module's registry function exactly as `RepositoryBundle`
already is — e.g. `src/infra/composition/project_registry.py`'s
`build_project_management_service_bundle(session, repositories,
platform_services)` gains a `uow`/`uow_factory` parameter, which is what
`TaskApplicationService.__init__(self, uow_factory: UnitOfWorkFactory,
clock: Clock)` above actually receives at construction time. No new
composition mechanism is introduced — this follows the exact
shape already established for repositories.

### 2.7 The unit-of-work flow, with dynamic aggregate discovery (gap fixed)

The previous revision's draining loop read only from a frozen
`touched_aggregates` list passed in at the start. That misses the exact
scenario the ADR itself uses as its own motivating example: a
transactional handler for `TaskCompleted` loads or creates a `Project`
aggregate that records `ProjectProgressChanged` — if `Project` wasn't in
the original list, that event is silently never discovered.

**Fix: the unit of work tracks aggregates dynamically, not from a frozen
list handed in up front.** Repositories register an aggregate with the
UoW whenever one is loaded, added, or otherwise touched — including by a
transactional handler mid-dispatch:

**Correction: a plain `set`/`frozenset` is the wrong data structure here.**
The previous revision's `self._tracked_aggregates.add(aggregate)` assumed
a hashable-by-identity `set`, but Python doesn't give objects
identity-based hashing for free — a mutable dataclass or domain entity
that defines `__eq__` (most of this codebase's aggregates do, for
business-key equality) has its `__hash__` implicitly set to `None` unless
it's frozen or explicitly opts back in, so `.add(aggregate)` raises
`TypeError: unhashable type` the first time this runs against a real
aggregate. Even for the aggregates that *are* hashable, a `set` still
dedups by `__eq__`, not by `id()` — two distinct in-memory instances that
compare equal would collapse into one, which is exactly the wrong
semantics for "every object touched during this unit of work," including
transient instances that are equal-by-key but not the same object.

**Fix: track by `id()` in a plain dict — an identity map — never a
`set`:**

```python
# src/infra/persistence/db/unit_of_work.py — extends the UnitOfWork
# protocol shape introduced in §2.6 (concrete placement and creation
# site: §2.6.1)
class SqlAlchemyUnitOfWork:
    def __init__(self) -> None:
        self._tracked_aggregates: dict[int, RecordsDomainEvents] = {}

    def register_touched(self, aggregate: RecordsDomainEvents) -> None:
        self._tracked_aggregates[id(aggregate)] = aggregate

    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]:
        return tuple(self._tracked_aggregates.values())
```

Keying by `id(aggregate)` gives genuine identity-based dedup regardless
of whether the aggregate defines `__eq__`/`__hash__` at all — registering
the same object twice is a no-op (same `id()`, same dict slot), while two
distinct-but-equal instances are correctly tracked as two separate
entries. The dict also holds a strong reference to each aggregate for the
lifetime of the unit of work, so there's no risk of an `id()` being
reused by a different, garbage-collected object while the UoW is still
open. `tracked_aggregates()` returns a `tuple`, not a `frozenset` — the
values may themselves be unhashable, and callers only ever iterate this,
never need set operations on it.

Every repository `get()`/`add()` call registers the returned aggregate.
Each drain round reads the UoW's *current* tracked set, not a snapshot
taken before dispatch began:

```python
def collect_pending_events(uow: UnitOfWork, already_seen: set[int]) -> list[DomainEvent]:
    new_events: list[DomainEvent] = []
    for aggregate in uow.tracked_aggregates():
        for event in aggregate.domain_events():
            identity = id(event)
            if identity not in already_seen:
                already_seen.add(identity)
                new_events.append(event)
    return new_events
```

**Deduplication is by object identity (`id(event)`), decided explicitly
here, not left as an implementation footnote** — the previous revision
flagged equality-based dedup as insufficient but didn't promote a real
choice. Object identity is the interim decision; if a future need arises
for events to survive process boundaries with a stable identity (e.g. for
retrying dispatch after a crash), that needs a real generated occurrence
ID, at which point this decision is revisited — not before.

Full flow:

```text
Aggregate method runs inside a UoW-managed transaction, records event(s)
        ↓
UoW registers every touched aggregate as it's loaded/added
        ↓
UoW collects pending events (collect_pending_events, above)
        ↓
UoW dispatches those events through transactional_event_bus.publish(event, uow)
   (FAIL_FAST) — the SAME uow is passed to every handler, so a handler
   updating a different aggregate does so through uow.session, the
   identical session/transaction the triggering aggregate is part of
        ↓
UoW re-collects — transactional handlers may have touched MORE
   aggregates (newly registered via uow.register_touched, called either
   automatically by uow.<repo>.get()/add() or explicitly by a handler
   building its own repository from uow.session) or recorded MORE events;
   repeat until a round produces nothing new, or MAX_DISPATCH_ROUNDS is
   hit (fail loudly on the cap — a real cycle is a bug, not a hang)
        ↓
Selected events are mapped to IntegrationEventEnvelope rows (§2.12)
        ↓
Outbox rows + business changes are written and committed together
        ↓
Only on successful commit: clear_domain_events() on every tracked aggregate
        ↓
The same collected events dispatch through post_commit_event_bus.publish(event)
   (ISOLATE_AND_CONTINUE) — note: no uow parameter here at all; the
   transaction is closed, and a post-commit handler must not be able to
   reach back into it (§2.4)
        ↓
Post-commit adapters call ViewInvalidationChannel.notify(...) (§2.10)
```

### 2.8 Rollback safety — discard, never reuse or retry (missing rule added)

The previous revision said only that a rolled-back UoW "leaves events
intact for inspection." That's true but incomplete, and the word "retry"
in the test plan was actively dangerous: an aggregate instance from a
failed unit of work may also hold **mutated in-memory state that was
never persisted** — e.g. `task.assignee_id` already changed in memory
while the database still has the previous value. Reusing that instance in
a later unit of work risks acting on state that was never actually
committed.

**Rule:** a rolled-back unit of work discards every aggregate instance
associated with it. Pending events may remain on those instances for
debugging/inspection, but they must never be automatically replayed, and
the instances themselves must never be reused in a later unit of work —
depending on the session/ORM model, rollback should expire or detach
those entities and the failed UoW should be closed outright. A retry means
starting a new unit of work that re-loads fresh aggregate state from the
database, not reusing the old in-memory objects.

### 2.9 Bus internals — queued dispatch, thread-safe, and correctly atomic (race fixed)

Breadth-first via an internal queue, and thread-safe via an `RLock`
(unchanged in intent from the prior revision) — but the previous sketch
had a real race between checking "is the queue empty" and flipping
`_dispatching` back to `False`, because those two steps happened under
**two separate** lock acquisitions:

```text
Thread A: acquire lock, see queue empty, release lock (loop `break`)
Thread B: acquire lock, append event, see _dispatching is still True,
          return — trusting Thread A's loop to pick it up
Thread A: acquire lock again (in `finally`), set _dispatching = False
```

Thread B's event is now stranded — not lost forever (a future,
unrelated `publish()` call will eventually notice the queue isn't empty
and drain it too), but processed at some arbitrary later time instead of
now, which for a post-commit UI-refresh bus means a silently stale view
until something unrelated happens to trigger the next dispatch.

**Fix: the emptiness check and the `_dispatching` flip must happen inside
the same lock acquisition**, so no other thread can observe a state in
between them. Since §2.5 now gives the transactional and post-commit
buses genuinely different handler signatures (`(event, uow)` vs.
`(event)`), they're two distinct public classes rather than one
parameterized by a `FailurePolicy` flag — but they share the same
queue/lock/drain shape, shown once here on the post-commit bus (no `uow`
to thread through) and then noted for the transactional variant:

```python
from collections import deque
from threading import RLock

class InProcessPostCommitEventBus(PostCommitEventPublisher, PostCommitEventSubscriber):
    def __init__(self) -> None:
        # Keyed by concrete event type; each stored handler is checked
        # against the named PostCommitEventHandler protocol at subscribe()
        # time, not a bare Callable — see the "named contract element" fix
        # in §2.5.
        self._handlers: dict[type, list[PostCommitEventHandler]] = {}
        self._queue: deque[DomainEvent] = deque()
        self._dispatching = False
        self._lock = RLock()

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            self._queue.append(event)
            if self._dispatching:
                return
            self._dispatching = True
        self._drain()

    def _drain(self) -> None:
        while True:
            with self._lock:
                if not self._queue:
                    # Empty-check and the "no longer dispatching" flip
                    # happen atomically, in the SAME critical section —
                    # this is the fix. A publish() arriving between these
                    # two statements is now impossible; it either
                    # completes its own append+check before this block
                    # runs (and this block then sees a non-empty queue and
                    # keeps looping), or it runs after this block has
                    # already flipped _dispatching to False (and correctly
                    # starts its own new drain).
                    self._dispatching = False
                    return
                current = self._queue.popleft()
            self._dispatch_one(current)  # never called while holding _lock

    def _dispatch_one(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), ()):
            try:
                handler(event)
            except Exception:
                logger.exception("Post-commit handler failed for %r", type(event))
```

`InProcessTransactionalEventBus` has the identical queue/lock/drain
shape and the same `self._handlers: dict[type, list[TransactionalEventHandler]]`
registry typing (against `TransactionalEventHandler`, not `PostCommitEventHandler`
— the two are not interchangeable, so a handler registered on the wrong
bus fails at subscribe() time instead of at the first missing-`uow`
`TypeError`) — `publish(self, event, uow)` and `_dispatch_one(self, event, uow)`
each carry the extra `uow` parameter through to `handler(event, uow)` —
with one difference: it is `FAIL_FAST`, so `_dispatch_one` does **not**
catch the handler's exception, and `_drain`'s loop needs its own
`except BaseException` around the `while` loop to clear the queue and
reset `_dispatching` before re-raising:

```python
    def _drain(self, uow: UnitOfWork) -> None:
        try:
            while True:
                with self._lock:
                    if not self._queue:
                        self._dispatching = False
                        return
                    current = self._queue.popleft()
                self._dispatch_one(current, uow)
        except BaseException:
            # Must not leave _dispatching stuck True, and must not leave
            # stale, half-processed-batch events for some LATER, unrelated
            # publish() to pick up — this bus is a long-lived singleton
            # reused across every future transaction, not created fresh
            # per unit of work. Discarding the rest of this batch and
            # letting the exception propagate (to abort the transaction)
            # is the correct behavior for FAIL_FAST (§2.4).
            with self._lock:
                self._queue.clear()
                self._dispatching = False
            raise

    def _dispatch_one(self, event: DomainEvent, uow: UnitOfWork) -> None:
        for handler in self._handlers.get(type(event), ()):
            handler(event, uow)  # propagates into _drain's except above
```

In a real implementation these two classes should share the queue/lock/
drain plumbing through a small private base rather than duplicating it —
shown as two full classes here only so each one's public contract and
failure behavior stay easy to read on their own.

The lock is never held while a handler runs — only while mutating queue/
dispatching state — so a handler that itself calls `publish()` re-entrantly
doesn't deadlock and doesn't need to know about the lock at all.

**This does not fully resolve thread policy, only the bus's own internal
safety.** Whether a *transactional* bus instance should even accept
publishes from more than one thread concurrently (a single UoW/transaction
is normally single-threaded already, which may make this moot for that
bus) versus whether the *post-commit* bus needs to tolerate concurrent
publishes from multiple background workers is still an open decision —
see "Open Items Before This Can Move to Accepted" below (this is not yet
a numbered Decision subsection; it's the one item still blocking
Accepted status).

### 2.10 The view-invalidation channel — two independent isolation layers

```python
# src/core/shared/events/view_invalidation.py
@dataclass(frozen=True, slots=True, kw_only=True)
class ViewInvalidationHint:
    tenant_id: str
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None

class ViewInvalidationHandler(Protocol):
    def __call__(self, hint: ViewInvalidationHint) -> None: ...

class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(
        self,
        handler: ViewInvalidationHandler,
        *,
        tenant_id: str,
    ) -> Subscription: ...
```

Same rule as §2.5: the handler shape is a named `Protocol`
(`ViewInvalidationHandler`), not an inline `Callable[[ViewInvalidationHint],
None]` — this is exactly the same kind of stored-callback contract as
`TransactionalEventHandler`/`PostCommitEventHandler`, so it gets the same
treatment for the same reason.

`kw_only=True`; `entity_id` optional for hints that don't correspond to
one entity (auth changes, tenant switches, bulk recalculation). `category`
and `scope_code` are both kept as independent dimensions — checked
against the real production QML binders before deciding this: every real
`_subscribe_domain_change(...)` call site passes `scope_code` and
positional entity-type arguments; none currently passes `category=`, but
`category` is a real field on today's `DomainChangeEvent` (it gates the
`shared_master_changed` bridge internally), so it's kept rather than
dropped on an unverified assumption.

**Correction: tenant isolation is enforced by the channel, not left to
binder discipline.** A plain `subscribe(handler)` is a broadcast — every
subscriber receives every hint regardless of tenant, so "a hint scoped to
tenant A does not reach a controller bound to tenant B" was never actually
guaranteed by that shape; a forgotten `if hint.tenant_id != ...: return`
in one binder would silently leak a cross-tenant refresh.

Two ways to fix this were considered: (a) keep the broadcast contract and
downgrade the guarantee to an *effect* claim — "a tenant-A hint must not
cause a tenant-B controller to refresh or query data" — enforced entirely
by binder-level `if` checks; or (b) make the channel itself refuse
delivery to a non-matching subscriber. **(b) is the decision, but
narrowly** — not a fully generic `predicate` parameter (which would just
duplicate the `scope_code`/`entity_type` filtering that already works
fine as binder-level closures), only a required `tenant_id` on
`subscribe()`, since tenant isolation is the one dimension here that's a
genuine security/correctness boundary rather than a business convenience
filter — consistent with how this codebase already treats tenant
isolation everywhere else (RLS at the DB layer, the repository
`_tenant_scope.py` mixin, `TenantContextService`): as something the
infrastructure guarantees structurally, never something every call site
is trusted to remember.

`tenant_id` is a **required** keyword parameter, with no default — a
controller cannot subscribe without stating which tenant it's bound to.
A genuinely cross-tenant subscriber (e.g. a platform-admin console) is
not served by passing some sentinel value through the same parameter;
it gets its own, clearly-named method:

```python
class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(self, handler: ViewInvalidationHandler, *, tenant_id: str) -> Subscription: ...
    def subscribe_across_tenants(self, handler: ViewInvalidationHandler) -> Subscription: ...
```

so a cross-tenant subscription is a deliberate, searchable, auditable
choice at the call site — never the accidental result of a missing
argument. `scope_code`/`entity_type` filtering stays exactly where it is
today, as a binder-level closure over the (now tenant-safe) delivered
hints — this correction only narrows the channel's new responsibility to
the one dimension that actually needs to be a hard boundary.

**Two separate failure-isolation responsibilities, not one:**

- `post_commit_event_bus` isolates failures **between event adapters** —
  one adapter's exception doesn't stop other adapters from running for
  the same or other events.
- `ViewInvalidationChannel.notify()` isolates failures **between UI
  subscribers** — a `notify()` call fans out to potentially many QML
  controllers, and one controller's callback raising must not prevent
  `notify()` from reaching the rest. This is a second, independent
  catch-log-continue boundary, inside the channel implementation, not
  something the post-commit bus provides for free. Without this, a single
  adapter can report success to the bus while a faulty controller still
  silently blocks every other controller's refresh.

### 2.11 Composition-root registration — per module, with explicit ownership of the returned subscriptions

Each module exposes registration functions; the composition root calls
one function per module, never one per event:

```python
# src/core/modules/project_management/application/event_handlers/view_invalidation.py
class ProjectManagementInvalidation:
    """Controlled constants, not raw literals repeated per call site —
    and deliberately matching today's existing DomainChangeEvent values
    exactly, not intuitively-plausible new ones, since some consumer may
    already filter on the current literal string."""
    CATEGORY = "module"
    SCOPE = "project_management"
    TASK = "task"

def register_post_commit_handlers(
    subscriber: PostCommitEventSubscriber,
    channel: ViewInvalidationChannel,
) -> list[Subscription]:
    def _task_hint(e) -> ViewInvalidationHint:
        return ViewInvalidationHint(
            tenant_id=e.tenant_id,
            category=ProjectManagementInvalidation.CATEGORY,
            scope_code=ProjectManagementInvalidation.SCOPE,
            entity_type=ProjectManagementInvalidation.TASK,
            entity_id=e.task_id,
        )

    return [
        subscriber.subscribe(TaskReassigned, lambda e: channel.notify(_task_hint(e))),
        subscriber.subscribe(TaskCompleted, lambda e: channel.notify(_task_hint(e))),
    ]
```

The transactional side registers the same way, using
`TransactionalEventSubscriber` and handlers shaped `(event, uow)` — this
is where `handle_task_completed` from §2.5 gets wired in:

```python
# src/core/modules/project_management/application/event_handlers/transactional.py
def register_transactional_handlers(
    subscriber: TransactionalEventSubscriber,
) -> list[Subscription]:
    return [
        subscriber.subscribe(TaskCompleted, handle_task_completed),
    ]
```

```python
# composition root
application_subscriptions.extend(
    project_management.register_transactional_handlers(transactional_event_bus)
)
```

**Someone must own the returned `list[Subscription]` for the application's
lifetime — the previous revision's composition-root example discarded the
return value entirely.** Two distinct lifetimes, both need documenting and
both are now explicit:

- **Module-level post-commit handlers**: owned by the composition root,
  collected into one registry, disposed on application shutdown.

  ```python
  application_subscriptions = SubscriptionRegistry()
  application_subscriptions.extend(
      project_management.register_post_commit_handlers(post_commit_event_bus, view_invalidation)
  )
  application_subscriptions.extend(
      inventory_procurement.register_post_commit_handlers(post_commit_event_bus, view_invalidation)
  )
  # on shutdown:
  application_subscriptions.dispose()
  ```

- **QML controller subscriptions to `ViewInvalidationChannel`**: owned by
  the controller itself, disposed during its own teardown — this part is
  unchanged from the previous revision, just now stated alongside the
  module-level lifetime so both are documented, not just one.

### 2.12 Ordering constraint with ADR-PF-011's outbox

Unchanged in substance from the previous revision, restated against the
now-concrete flow in §2.7: the outbox write happens during the
transactional phase, after the draining loop and before commit — never as
a reaction to a published in-process event. This doesn't reopen
ADR-PF-011; it only keeps this ADR's own description consistent with it.

## Alternatives Rejected

- Reorganizing the shared `DomainEvents` dataclass into subfolders —
  doesn't fix central bridge-wiring knowledge.
- Routing domain events through Qt signals directly — couples
  domain/application layers to a UI framework.
- Aggregates publishing straight to the UI channel — the original
  anti-pattern restated.
- Automatic promotion of every domain event to a durable integration
  event — out of scope; ADR-PF-011 governs promotion.
- One bus/one failure policy for both transactional and post-commit
  dispatch — contradictory failure requirements.
- One composition-root subscription per event — recreates
  `_wire_bridges()` in a new file.
- Recursive (depth-first) re-entrant dispatch — breadth-first via a queue
  is far less surprising.
- Polymorphic/supertype event subscription in v1 — no demonstrated need,
  creates double-dispatch ambiguity.
- **Application services holding a `TransactionalEventPublisher` and
  dispatching events themselves.** Rejected per §2.6 — two orchestration
  models in one design risks double-dispatch or silently-skipped dispatch
  depending on call path; the unit of work is the single owner.
- **A frozen, up-front list of "touched aggregates" for the draining
  loop.** Rejected per §2.7 — misses aggregates a transactional handler
  loads or creates mid-dispatch, exactly the scenario this ADR uses as its
  own motivating example.
- **Reusing or retrying a rolled-back aggregate instance.** Rejected per
  §2.8 — its in-memory state may not match what's actually persisted.
- **One publisher/subscriber pair, with one handler signature
  (`Callable[[E], None]`), reused for both transactional and post-commit
  dispatch.** Rejected per §2.5 — a transactional handler needs the
  current unit of work to safely touch another aggregate in the same
  transaction; a post-commit handler must *not* have it, since the
  transaction is already closed by the time it runs. One shared signature
  can't express both without either starving transactional handlers of
  the session they need, or letting a post-commit handler reach back into
  a closed transaction.

## Consequences

- Every module gains `domain/events.py` (tenant-aware event classes),
  `application/event_handlers/view_invalidation.py` (or a UI-side
  equivalent), and module-owned constants for invalidation-hint values.
- Application services depend on `UnitOfWork` + `Clock`, never on
  `TransactionalEventPublisher`/`PostCommitEventPublisher` directly (§2.6)
  — this is now the documented dependency shape, replacing the previous,
  contradictory migration text.
- Transactional handlers receive `(event, uow)`, never just `(event)` —
  `uow.session` is the same session/transaction the triggering aggregate
  used, closing the "which repository and transaction does the handler
  use" gap (§2.5). Post-commit handlers receive `(event)` only, by design,
  since the transaction is already closed by the time they run.
- `UnitOfWork` gains dynamic aggregate tracking (`register_touched`,
  `tracked_aggregates`) so the draining loop can't miss aggregates touched
  by handlers mid-dispatch — tracked in an identity map (keyed by
  `id(aggregate)`), not a `set`, since aggregates are not guaranteed
  hashable and a `set` would dedup by equality, not identity, anyway
  (§2.7).
- `src/core/shared/events/` holds contracts + `Signal`; `src/core/shared/
  time/clock.py` holds the general-purpose `Clock` protocol (not
  events-specific); concrete buses live in `src/infra/events/` and
  `SystemClock` lives in `src/infra/time/`; the Qt-marshaling channel
  lives in `src/ui_qml/infrastructure/events/`.
- Concrete `SqlAlchemyUnitOfWork` replaces the content of
  `src/infra/persistence/db/unit_of_work.py` — checked, its existing
  `session_scope()` helper has zero callers anywhere in `src/`, so
  reclaiming the enterprise-standard name for the real Unit of Work costs
  no import-site migration; `session_scope()`'s commit/rollback/close
  shape is folded in as the private helper `__enter__`/`__exit__` use
  internally (§2.6.1). Instances are created in
  `src/infra/composition/app_container.py`'s `build_service_graph(session)`,
  the same centralized composition point that already builds today's
  `RepositoryBundle`.
- Subscription ownership is explicit at both the module (composition-root
  registry, app-shutdown disposal) and controller (self-owned,
  teardown-time disposal) level.

## Migration Impact

See [ADR-005-execution-plan.md](ADR-005-execution-plan.md) for the
concrete, per-phase sequencing (which module goes first and why, exit
criteria per phase, and the still-open platform-signals decision). This
section states the general rule that plan follows.

Pick one module, smallest event count first. Add its `domain/events.py`
with `tenant_id` on every tenant-scoped event; adopt `RecordsDomainEvents`
and the injected `Clock` in its aggregates; give its repositories
`register_touched` calls on load/add; add its
`register_post_commit_handlers` function with module-owned constants; add
its subscriptions to the composition root's `SubscriptionRegistry`; audit
its existing QML binder filters against the new hint fields; then delete
that module's fields out of the old `DomainEvents` dataclass. Repeat per
module.

## Test Impact

- A transactional handler that updates a *different* aggregate
  (`handle_task_completed` updating `Project`) does so through the same
  `uow.session` as the triggering aggregate — verified by asserting both
  changes are visible in the same still-open transaction before commit,
  and that rolling back that transaction undoes both together, not just
  the originating aggregate's change.
- A post-commit handler's signature genuinely cannot accept a `uow`
  parameter (a type-level guarantee, not just a runtime check) — confirms
  the two handler kinds can't be accidentally swapped.
- Aggregate records the correct event, with accurate previous/new state
  and `tenant_id`, using an injected fixed `Clock`.
- No event is recorded when the operation is a no-op.
- A transactional handler exception aborts the transaction; a post-commit
  handler exception does not roll anything back.
- Failed transaction produces no post-commit UI invalidation, and no
  outbox row.
- A transactional handler that loads or creates a *different* aggregate,
  which itself records an event, causes that event to be discovered and
  dispatched too — not silently dropped (the §2.7 fix, directly tested).
- `register_touched` accepts an aggregate that defines `__eq__` but not
  `__hash__` (i.e. is unhashable) without raising — and registering the
  *same* object twice does not double-count it, while two distinct
  instances that compare equal are still tracked as two separate entries
  (identity, not equality, semantics — the §2.7 identity-map fix, directly
  tested).
- Handler dispatch is by exact event type only.
- One failing post-commit **adapter** does not block other adapters
  (bus-level isolation); separately, one failing **controller callback**
  inside `notify()` does not block other controllers (channel-level
  isolation) — tested as two distinct cases, not one.
- Subscription disposal prevents later callbacks, at both the
  controller-owned and composition-root-owned lifetimes.
- `domain_events()` does not clear anything; `clear_domain_events()` only
  runs after a successful commit.
- **Rollback discards the associated aggregate instances** — a simulated
  rollback must not permit those same instances to be reused in a
  subsequent unit of work, and must produce no published events and no
  outbox rows (replaces the previous, misleading "retry" wording).
- A transactional handler that raises additional events causes further
  dispatch rounds; a deliberately cyclical setup fails loudly within the
  round ceiling rather than hanging.
- Two threads calling `publish()` on the same bus concurrently do not
  corrupt the internal queue or double-dispatch (bus-level thread safety,
  independent of whatever thread-confinement policy is eventually decided
  per the still-open item in "Open Items Before This Can Move to
  Accepted").
- A `publish()` that arrives at the exact moment a drain loop is checking
  "is the queue empty" is never stranded — it either gets picked up by the
  in-progress drain, or `_dispatching` has genuinely already flipped back
  to `False` and the new `publish()` starts its own drain (§2.9's race
  fix). This needs a deliberately adversarial test — e.g. a handler that,
  on its last invocation, blocks until a second thread's `publish()` call
  has entered `publish()`'s own critical section, to force the exact
  interleaving the bug required.
- A `FAIL_FAST` handler exception clears any remaining queued events for
  that bus, not just the one that raised — confirming a later, unrelated
  `publish()` doesn't silently dispatch stale events left over from an
  aborted transaction.
- Events do not leak across a reused/rehydrated ORM entity instance.
- Selected integration events are written to the outbox in the same
  transaction as the business change, never after.
- A `ViewInvalidationHint` scoped to tenant A does not reach a handler
  subscribed via `subscribe(handler, tenant_id="B")` — enforced by the
  channel itself, not by a binder-level `if` check (§2.10's correction).
- A handler registered via `subscribe_across_tenants(...)` does receive
  hints for every tenant — confirming the two methods are genuinely
  distinct, not the same broadcast behavior under two names.
- `subscribe()` with no `tenant_id` argument is a `TypeError` at the call
  site (there is no default to silently fall back to), not a runtime
  cross-tenant leak discovered later.
- Re-entrant publish during a dispatch pass is processed breadth-first.
- Old and new mechanisms emit equivalent invalidation behavior for any
  event migrated during the transition, verified per-module.

## Implementation Evidence

None yet — this ADR is a design proposal, not yet implemented.

## Open Items Before This Can Move to Accepted

Resolved across this and subsequent follow-up corrections: the missing
`tenant_id` field, the application-service-vs-UoW ownership
contradiction, dynamic aggregate discovery in the draining loop, the
rollback-reuse hazard, `Clock`'s contract/implementation placement
(and its final home in `shared/time/clock.py` + `infra/time/system_clock.py`
— its own general-purpose package, not nested under either side's
`events/`, and not `infra/platform/`), the bus's internal thread-safety,
explicit subscription ownership at both lifetimes, structural (not
binder-discipline) tenant enforcement on `ViewInvalidationChannel.subscribe()`,
the empty-queue/`_dispatching`-flip race in the bus's drain loop,
transactional handlers receiving the current `UnitOfWork` so
cross-aggregate updates share the triggering aggregate's own
session/transaction instead of an ambiguous, separately-injected
repository, the handler shape itself promoted from an inline
`Callable[...]` repeated per call site to named
`TransactionalEventHandler`/`PostCommitEventHandler` protocols that every
subscriber contract, bus registry, and registration function now types
against consistently; `UnitOfWork` aggregate tracking switched from a
`set`/`frozenset` (which requires hashability and dedups by equality, not
identity) to an `id()`-keyed identity map returning a `tuple`; and — from
an end-to-end consistency pass over the whole document — six internal
inconsistencies: two phantom `§2.14` cross-references pointing at a
Decision subsection that was never written (reworded to point at this
section instead); `ViewInvalidationChannel.subscribe()` still typing its
handler as a raw `Callable` after §2.5 had already established that
handler shapes must be named protocols (added `ViewInvalidationHandler`
to match); the `UnitOfWork` protocol missing the `__enter__`/`__exit__`
methods its own usage example depends on, and `UnitOfWorkFactory` being
used in two places without ever being defined (both added to §2.6); the
concrete aggregate-tracking example in §2.7 still being named
`UnitOfWork` instead of the `SqlAlchemyUnitOfWork` name §2.6.1 later
established; and this document's own header/Context undercounting how
many review rounds it has actually been through. One further correction
after that pass: §2.6.1's first cut parked `SqlAlchemyUnitOfWork` under a
disambiguated `sqlalchemy_unit_of_work.py` to avoid the existing
`unit_of_work.py`/`session_scope()` filename — checked, and
`session_scope()` has zero callers anywhere in `src/`, so the real
`UnitOfWork` now reclaims `unit_of_work.py` directly (the
enterprise-standard expectation for that name), with `session_scope()`'s
shape folded in as a private helper rather than left stranded as unused
public code.

**Still genuinely open, and now broader than before** (referenced above
from §2.9 as future work — not yet promoted to its own numbered Decision
subsection, since the answer isn't settled):

1. Which specific call sites can publish from a non-Qt-main thread (needed
   to build `qt_view_invalidation_channel.py`'s marshaling behavior).
2. Given (1), whether each bus instance should be **thread-confined**
   (one UoW/application thread only, cross-thread publish rejected or
   asserted against) or genuinely **multi-thread-tolerant** end to end —
   §2.9 makes the bus's own queue/state safe to call from multiple
   threads, but that's necessary, not sufficient: handler code itself
   (especially anything touching QML-bound state) still needs a thread
   policy decided, not just a thread-safe mailbox in front of it.

Both should be resolved, together, before this ADR is marked Accepted.
