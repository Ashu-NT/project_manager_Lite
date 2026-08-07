# ADR-005: Domain Events

- Status: proposed
- Date: 2026-08-05 (revised repeatedly on 2026-08-05 — three full team-review
  rounds, numerous targeted follow-up corrections, a fourth external review
  against the companion execution plan, and a fifth review checking both
  documents against this codebase's actual session/persistence wiring; see
  "Open Items Before This Can Move to Accepted" for the complete resolved
  list)

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
creation site. **Round four**, reviewing this design against the
companion execution plan, found five further issues, all substantive
rather than cosmetic: a transactional handler constructing a concrete
`SqlAlchemyProjectRepository` directly from `uow.session`, breaking the
framework-agnostic guarantee the execution plan itself requires (§2.5,
§2.6); a `UnitOfWorkFactory` described as closing over an
already-created, process-lifetime `Session` instance rather than a
session factory — which would make every "fresh" `UnitOfWork` share the
same underlying session, defeating rollback isolation (§2.6.1); a genuine
cross-transaction bug in the transactional bus's shared queue, where one
thread's drain loop could dispatch a *different* thread's queued event
using the wrong `UnitOfWork` (§2.9); no reconciliation between
tenant-less (`tenant_id: str | None`) domain events and
`ViewInvalidationHint`'s required, non-optional `tenant_id: str` (§2.10);
and a handler-registry read outside the lock in the post-commit bus's
dispatch loop, racing a concurrent `subscribe()`/`dispose()` (§2.9). All
five are fixed below. **Round five**, checking both documents directly
against this codebase's actual repository/session code (not just the
design in the abstract), found three more: `uow.commit()` was assumed to
persist a mutated aggregate on its own, but this codebase's own
`Task.update()` persists through a raw, version-checked `UPDATE` that
bypasses ORM attribute tracking entirely — so nothing would have flushed
a mutated `Task` without an explicit repository call (§2.6, §2.7); the
base `UnitOfWorkFactory.create() -> UnitOfWork` return type doesn't
support `uow.tasks`/`uow.projects` at all, and one cross-module concrete
`SqlAlchemyUnitOfWork` would import every module's repository vocabulary
into a single class per transaction (§2.6, §2.6.1); and
`ViewInvalidationHandler[PlatformViewInvalidationHint]` (§2.10) subscripted
a `Protocol` that round four had declared non-generic. All three are
fixed below, alongside a newly-identified migration-time risk (process-
lifetime session staleness during partial migration) that this ADR
records but whose concrete handling belongs in the companion execution
plan, not here — see §2.6.1's closing note and the execution plan's
Constraint 5.

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
  domain_event_publisher.py        # TransactionalEventDispatcher + PostCommitEventPublisher
  domain_event_subscriber.py       # TransactionalEventHandler/PostCommitEventHandler
                                    # + TransactionalEventSubscriber/PostCommitEventSubscriber
  subscription.py                  # Subscription protocol (dispose)
  view_invalidation.py             # ViewInvalidationHint + ViewInvalidationHandler
                                    # + channel contract
  signal.py                        # existing generic Signal[T] primitive — unchanged

src/core/shared/time/
  clock.py                         # Clock protocol — general time abstraction,
                                    # not events-specific; used BY aggregate_events.py

src/core/shared/persistence/
  unit_of_work.py                  # UnitOfWork + UnitOfWorkFactory protocols (§2.6/§2.7).
                                    # Moved out of shared/events/ (round four correction,
                                    # §2.6.1) — not events-specific, same reasoning as Clock.

src/infra/events/
  in_process_transactional_event_dispatcher.py  # stateless, FAIL_FAST, (event, uow) — §2.9
  in_process_post_commit_event_bus.py    # queued, ISOLATE_AND_CONTINUE, handlers take (event)
  in_process_view_invalidation_channel.py  # non-marshaling concrete channel

src/infra/time/
  system_clock.py                  # concrete Clock implementation

src/infra/persistence/db/
  unit_of_work.py                  # REPLACED (0 callers on session_scope() — §2.6.1):
                                    # now SqlAlchemyUnitOfWorkBase (aggregate tracking +
                                    # event coordination, module-agnostic); owns a Session
                                    # plus the dispatcher/bus above as collaborators.
                                    # Per-module SqlAlchemy<Module>UnitOfWork subclasses
                                    # live under each module's own infrastructure/
                                    # persistence/ (round five — §2.6)

src/infra/composition/
  app_container.py                 # build_service_graph(session) — creation site for
                                    # each module's SqlAlchemy<Module>UnitOfWorkFactory,
                                    # alongside today's RepositoryBundle (§2.6.1); every
                                    # factory closes over SessionLocal (a session
                                    # factory), not the existing session instance

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
class TransactionalEventDispatcher(Protocol):
    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None: ...

class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
```

**Naming correction (round four):** the transactional side is named
`TransactionalEventDispatcher` with a `dispatch(...)` method, not
`...Publisher`/`publish(...)` — see §2.9 for why: it's a stateless
synchronous call, not a publish-into-a-queue operation, and the name now
says so. `PostCommitEventPublisher`/`publish(...)` is unchanged — that
side genuinely queues and returns.

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
def handle_task_completed(
    event: TaskCompleted, uow: ProjectManagementUnitOfWork
) -> None:
    # uow.projects.get(...) auto-registers `project` with the UoW (§2.6),
    # so its recorded events get drained too, per §2.7 — no manual
    # uow.register_touched(project) call needed here.
    project = uow.projects.get(event.project_id)
    project.record_progress_from_task_completion(event.task_id)
    uow.projects.update(project)  # persist explicitly — see §2.6's
    # round-five correction: commit() alone does not persist a mutated
    # aggregate for every entity type in this codebase.
```

**Correction (round four): the previous revision had this handler build a
concrete `SqlAlchemyProjectRepository(uow.session)` directly.** That
imports a concrete infrastructure class and a raw SQLAlchemy `Session`
type straight into application-layer handler code — exactly the coupling
§2.6 exists to prevent, and exactly what would need to be redone the
moment a second transport (a future FastAPI command handler, per the
execution plan) needed to call the same domain logic through a different
concrete `UnitOfWork`. **Fix: `uow.projects` is a repository *contract*
(an `ABC`/`Protocol`, e.g. `src/core/modules/project_management/contracts/
repositories/project.py`'s `ProjectRepository`), never a concrete
SQLAlchemy class, and the raw `Session` is never exposed on `UnitOfWork`
at all** — see §2.6's corrected protocol. The handler above is typed
against `ProjectManagementUnitOfWork`, a module-owned `Protocol` that
extends the shared `UnitOfWork` contract with this module's own typed
repository accessors (`projects: ProjectRepository`, `tasks:
TaskRepository`, ...); the concrete `SqlAlchemyProjectManagementUnitOfWork`
(§2.6.1) satisfies that extended protocol structurally, and is the *only* place a concrete
repository class or a `Session` is ever constructed or held.

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
Application services do not depend on `TransactionalEventDispatcher`
directly — they depend on the unit of work and a `Clock`:

```python
class TaskApplicationService:
    def __init__(
        self, uow_factory: ProjectManagementUnitOfWorkFactory, clock: Clock
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def reassign_task(self, task_id: str, assignee_id: str | None) -> None:
        with self._uow_factory.create() as uow:
            task = uow.tasks.get(task_id)
            task.reassign(assignee_id, clock=self._clock)
            uow.tasks.update(task)  # persist the mutation explicitly — see
            uow.commit()            # the round-five correction below
```

**Correction (round five): `uow.commit()` does not implicitly persist a
mutated aggregate — this codebase's own repositories already prove why.**
Checked against `SqlAlchemyTaskRepository`: `Task.update()` persists
through `update_with_version_check` (`src/infra/persistence/db/optimistic.py`),
a raw, parameterized `UPDATE ... WHERE id = ? AND version = ?` issued
directly against the table — it does **not** go through a
SQLAlchemy-tracked ORM instance's attribute assignment, so there is
nothing for a plain `session.flush()`/`commit()` to pick up on its own.
Other entities in the same module (`TaskAssignment`, `TaskDependency`)
instead mutate a tracked ORM row's attributes directly and rely on
SQLAlchemy's own flush — a second, different persistence mechanism
coexisting with the first. **This ADR does not get to assume either
mechanism uniformly**, so the rule has to hold regardless of which one a
given aggregate's repository happens to use: **every repository exposes
an explicit `update(aggregate)` (or `add(aggregate)` for new instances),
and every application service or transactional handler calls it after
mutating an aggregate and before `uow.commit()` — `register_touched` and
`commit()` coordinate event dispatch and the transaction boundary; neither
one persists field mutations by itself.** `handle_task_completed` (§2.5)
needs the same correction — its `project.record_progress_from_task_completion(...)`
call must be followed by `uow.projects.update(project)` before the handler
returns, exactly like `reassign_task` above.

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
(§2.7) and exposing repository *contracts* — not a raw `Session` — that a
handler needs to touch another aggregate in the same transaction (the
corrected shape below; see the round-four correction directly after the
protocol for why `session` does not appear here):

```python
class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def register_touched(self, aggregate: RecordsDomainEvents) -> None: ...
    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]: ...
    def commit(self) -> None: ...

class UnitOfWorkFactory(Protocol):
    def create(self) -> UnitOfWork: ...
```

**Correction (round four): the previous revision put `session: Session`
directly on this shared protocol.** Any code typed against `UnitOfWork`
could then reach `.session` and build a concrete SQLAlchemy repository
inline — which is exactly what happened in §2.5's first-cut handler
example, and it's a framework-agnosticism leak at the contract level, not
just at one call site: nothing about the shared `UnitOfWork` protocol
itself is or should be SQLAlchemy-specific. **The shared protocol above
exposes no session, no repositories, nothing persistence-technology-
specific — only transaction/aggregate-tracking behavior.** Each module
extends it with its own repository-contract accessors, typed against that
module's existing repository `ABC`/`Protocol` contracts (which already
exist under each module's `contracts/repositories/`, e.g.
`project_management`'s `ProjectRepository`, `TaskRepository`):

```python
# src/core/modules/project_management/contracts/unit_of_work.py
class ProjectManagementUnitOfWork(UnitOfWork, Protocol):
    projects: ProjectRepository
    tasks: TaskRepository

class ProjectManagementUnitOfWorkFactory(Protocol):
    def create(self) -> ProjectManagementUnitOfWork: ...
```

**Correction (round five): the base `UnitOfWorkFactory.create() ->
UnitOfWork` return type is not enough on its own.** A service constructor
typed `uow_factory: UnitOfWorkFactory` and calling
`self._uow_factory.create()` gets back a plain `UnitOfWork` — which
doesn't declare `.tasks`/`.projects` — so `uow.tasks.get(...)` in
`reassign_task` (§2.6) has no contract to type-check against. Each module
pairs its `UnitOfWork` extension with a matching factory `Protocol`
returning that same extended type, and application services depend on the
module-specific factory (`ProjectManagementUnitOfWorkFactory`), not the
generic one — see `TaskApplicationService.__init__` above. `inventory_procurement`
follows the identical shape: `InventoryUnitOfWork(UnitOfWork, Protocol)`
with `items`/`balances`/`reservations` accessors, plus a matching
`InventoryUnitOfWorkFactory`.

A transactional handler for a module is typed against that module's
`UnitOfWork` extension, never against the shared `UnitOfWork` base
directly and never against a concrete class — it only ever imports
repository *contracts*, the same ones the module's application services
already import today.

**Concrete implementation shape (round five): module-specific concrete
classes, not one cross-module `SqlAlchemyUnitOfWork`.** A single concrete
class declaring every module's repository accessors together
(`tasks`, `projects`, `inventory_items`, `purchase_orders`,
`maintenance_work_orders`, ...) would import every module's repository
vocabulary into one object — this deliberately does **not** mirror how
`src/infra/composition/repositories.py`'s existing `RepositoryBundle`
is shaped today (one flat dataclass with every module's repositories as
siblings): `RepositoryBundle` is built once at composition time and
paying that flat cost there is cheap, but a `UnitOfWork` is constructed
per transaction, and a modular-monolith structure (`src/core/modules/<module>/`)
gains nothing from replicating that same flatness at a per-transaction
granularity. Instead: a private shared base carries session
lifecycle/aggregate-tracking/dispatch (the parts that are genuinely
module-agnostic), and each module gets its own thin concrete subclass
declaring only its own repository accessors:

```python
# src/infra/persistence/db/unit_of_work.py
class SqlAlchemyUnitOfWorkBase:
    # session lifecycle (§2.6.1), identity-map aggregate tracking (§2.7),
    # dispatch coordination (§2.9), outbox mapping (§2.12) — everything
    # that is NOT specific to any one module's repository vocabulary.
    ...

# src/core/modules/project_management/infrastructure/persistence/unit_of_work.py
class SqlAlchemyProjectManagementUnitOfWork(SqlAlchemyUnitOfWorkBase):
    def __init__(self, session: Session, ...) -> None:
        super().__init__(session, ...)
        self.projects = SqlAlchemyProjectRepository(session)
        self.tasks = SqlAlchemyTaskRepository(session)
```

satisfying `ProjectManagementUnitOfWork` structurally. Each concrete
subclass holds its own `Session` as a private implementation detail used
to build its module's concrete repositories at construction time — that
`Session` is never a public attribute on any `UnitOfWork` protocol,
module-specific or shared.

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
expose them) call `register_touched` automatically on load — this is why
`handle_task_completed` (§2.5) needs no explicit `register_touched` call
for the `project` it loads via `uow.projects.get(...)`. Manual
`register_touched` is only needed for the narrower case of an aggregate a
handler builds or mutates *without* going through one of `uow`'s own
repository accessors (rare — most handlers load via `uow.<repo>.get()`/
`add()` and get this for free).

The dependency shape:

```text
Application service
├── UnitOfWork (or UnitOfWorkFactory)
└── Clock

UnitOfWork / EventCoordinator (owned by the UoW, not the application service)
├── transactional_event_dispatcher  (TransactionalEventDispatcher, FAIL_FAST,
│                                    stateless, handlers receive (event, uow) — §2.9)
├── post_commit_event_bus    (PostCommitEventPublisher, ISOLATE_AND_CONTINUE,
│                             queued, handlers receive (event) only)
├── integration event mapper (selects + builds IntegrationEventEnvelope rows)
└── outbox repository
```

Ordinary application services never need either the dispatcher or the bus
merely to publish events an aggregate already recorded — that would let
two different call paths dispatch the same event twice, or let dispatch
depend on which service happened to be used. A service *would* take
`PostCommitEventPublisher` directly only if it needs to publish something
that isn't tied to a specific aggregate's recorded events at all (an edge
case, not the common path) — it would never take
`TransactionalEventDispatcher` directly, since dispatching transactionally
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
needs repointing. **Decision: `SqlAlchemyUnitOfWorkBase` (round five —
§2.6's module-agnostic base class) claims
`src/infra/persistence/db/unit_of_work.py` directly; `session_scope()`'s
try/commit/except-rollback/finally-close shape is folded in as the
private helper the new class's `__enter__`/`__exit__` use internally**
(the same behavior, just no longer a free-standing, unused public
function) — nothing is deleted outright, since that same shape is
exactly what rollback-on-exception (§2.8) needs:

```text
src/core/shared/persistence/unit_of_work.py  # UnitOfWork + UnitOfWorkFactory protocols
                                              # (contract only — §2.6). Not under shared/events/:
                                              # same reasoning as Clock (§2.3) — a transaction/
                                              # aggregate-tracking abstraction that coordinates
                                              # events is not itself events-specific vocabulary.
src/infra/persistence/db/unit_of_work.py  # REPLACED — was session_scope() only (0 callers);
                                          # now SqlAlchemyUnitOfWorkBase: session lifecycle,
                                          # identity-map aggregate tracking, dispatch/outbox
                                          # coordination — the module-agnostic parts only
                                          # (round five: NOT every module's repository
                                          # vocabulary in one class — see below)

src/core/modules/<module>/contracts/unit_of_work.py
    # <Module>UnitOfWork + <Module>UnitOfWorkFactory protocols, extending
    # the shared base with that module's own repository contract accessors

src/core/modules/<module>/infrastructure/persistence/unit_of_work.py
    # SqlAlchemy<Module>UnitOfWork(SqlAlchemyUnitOfWorkBase), e.g.
    # SqlAlchemyProjectManagementUnitOfWork, SqlAlchemyInventoryUnitOfWork —
    # added per module, in that module's own phase (see execution plan)
```

**Correction (round four): the previous revision kept the `UnitOfWork`/
`UnitOfWorkFactory` protocols under `src/core/shared/events/`.** That
package is for events contracts; a transaction-boundary/aggregate-tracking
abstraction is not events-specific any more than `Clock` was (§2.3) — it
happens to coordinate event dispatch as one of its responsibilities, but a
future consumer with no interest in domain events (e.g. a plain
read-modify-write command with no events at all) would still need
`UnitOfWork` for its transaction boundary. **Moved to its own
`src/core/shared/persistence/` package**, mirroring the concrete side
already living under `src/infra/persistence/db/`.

`SqlAlchemyUnitOfWorkBase` sits under `src/infra/persistence/db/` — the
same package as `engine.py`/`session_factory.py` — rather than under
`src/infra/events/`, since its primary job is transaction and
aggregate-tracking, not event dispatch; it *owns* a
`transactional_event_dispatcher`/`post_commit_event_bus` pair (both from
`src/infra/events/`) as collaborators, the same way it owns a `Session`.
Each module's concrete `SqlAlchemy<Module>UnitOfWork` subclass lives under
that module's own `infrastructure/persistence/`, not here — see §2.6's
round-five correction for why one cross-module concrete class was
rejected in favor of a shared base plus thin per-module subclasses.

**Where instances get created, and correction on session lifetime:** composition
in this codebase is centralized, not per-module — repositories are already
built this way in `src/infra/composition/repositories.py`
(`RepositoryBundle`, one instance per `Session`, e.g.
`task_repo=SqlAlchemyTaskRepository(session)`) and wired together in
`src/infra/composition/app_container.py`'s `build_service_graph(session)` /
`build_service_dict(session)`, both called from
`src/ui_qml/shell/app.py`'s `build_services()` with the one
process-lifetime `Session` that function creates today for the existing,
unmigrated constructor-injection pattern — that part is unchanged.

**The previous revision said the `UnitOfWorkFactory` would be "a factory
closing over `session`" — i.e. that same single, process-lifetime
`Session` instance. That directly contradicts this ADR's own claim, a few
paragraphs up, that "a fresh `UnitOfWork` is created per transaction": a
factory closing over one already-created `Session` object hands out that
same session (and the same underlying transaction) to every `UnitOfWork`
it creates, which breaks rollback isolation (§2.8 requires discarding a
rolled-back `UnitOfWork`'s session state without affecting anything
else), breaks concurrency (two "fresh" units of work would silently share
one transaction), and contradicts the Test Impact claim that a retry
loads genuinely fresh state.** **Fix: `build_service_graph` also receives
(or itself constructs) a session *factory* — `SessionLocal`, the existing
`sessionmaker` in `src/infra/persistence/db/session_factory.py` — and each
module's `UnitOfWorkFactory` closes over that callable, not over an
already-created `Session`.** Shown once here for `project_management`
(§2.6's `SqlAlchemyProjectManagementUnitOfWork(SqlAlchemyUnitOfWorkBase)`
— every other migrated module follows the identical shape with its own
names):

```python
# src/core/modules/project_management/infrastructure/persistence/unit_of_work.py
class SqlAlchemyProjectManagementUnitOfWorkFactory:
    def __init__(
        self,
        session_factory: Callable[[], Session],   # e.g. SessionLocal
        transactional_dispatcher: TransactionalEventDispatcher,
        post_commit_bus: PostCommitEventPublisher,
    ) -> None:
        self._session_factory = session_factory
        self._transactional_dispatcher = transactional_dispatcher
        self._post_commit_bus = post_commit_bus

    def create(self) -> "SqlAlchemyProjectManagementUnitOfWork":
        return SqlAlchemyProjectManagementUnitOfWork(
            session=self._session_factory(),  # a NEW Session every call
            transactional_dispatcher=self._transactional_dispatcher,
            post_commit_bus=self._post_commit_bus,
        )
```

`build_service_graph` builds one module-specific `SqlAlchemy<Module>UnitOfWorkFactory`
per migrated module this way — closing over `SessionLocal` directly,
alongside (not instead of) the existing single `session` still used to
build today's `RepositoryBundle` — and hands each factory into that
module's registry function exactly as `RepositoryBundle` already is —
e.g. `src/infra/composition/project_registry.py`'s
`build_project_management_service_bundle(session, repositories,
platform_services)` gains a `uow_factory: ProjectManagementUnitOfWorkFactory`
parameter, which is what `TaskApplicationService.__init__(self, uow_factory:
ProjectManagementUnitOfWorkFactory, clock: Clock)` above actually receives
at construction time. The two session lifetimes now coexist deliberately:
the existing single process-lifetime `Session` continues to back every
not-yet-migrated service exactly as today, while each `uow_factory.create()`
call opens a genuinely new `Session` scoped to one transaction — this is
expected during the module-by-module migration (Migration Impact), not a
temporary inconsistency to resolve early.

**Known risk during migration (round five), recorded here but resolved in
the execution plan, not this ADR:** while a module has some
`uow_factory`-backed command paths and some still-unmigrated
`RepositoryBundle`-backed read paths open on the *same* rows, a
committed change made through a fresh `uow_factory.create()` `Session`
is not automatically visible to an already-identity-mapped instance held
by the long-lived `RepositoryBundle` `Session` — SQLAlchemy does not
overwrite an already-loaded, non-expired instance's attributes from a
later `select()` result unless that instance was expired or the query
used `populate_existing()`, and expiry from one session's commit has no
effect on a different session's identity map. Concretely confirmed
against this codebase: the existing dashboard/workspace controllers hold
their repository/session graph for the controller's entire lifetime and
re-run the *same* `select()`-based `get()`/`list_*()` methods on refresh
(`src/ui_qml/modules/project_management/controllers/common/workspace_controller_base.py`),
so a fresh-`UnitOfWork` command's committed change would not reliably
reach an already-open dashboard without either refreshing that read path
too or explicitly expiring the stale instances. This is a per-phase
migration concern, not a design flaw in the mechanism itself — see the
execution plan's Constraint 5 and its per-phase exit criteria for the
required handling.

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
# src/infra/persistence/db/unit_of_work.py — SqlAlchemyUnitOfWorkBase,
# the module-agnostic base every SqlAlchemy<Module>UnitOfWork subclass
# extends (round five, §2.6) — aggregate tracking belongs here, not on
# any one module's subclass, since it has no module-specific vocabulary.
# Constructor also accepts session/transactional_dispatcher/post_commit_bus
# per §2.6.1's factory shape — omitted below to keep this snippet focused
# on aggregate tracking.
class SqlAlchemyUnitOfWorkBase:
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
Caller (service or handler) explicitly calls uow.<repo>.update(aggregate)
   (or .add(...) for a new instance) to stage the mutation for persistence
   — commit() alone does not persist it (round-five correction: this
   codebase's own Task.update() proves why — see §2.6)
        ↓
UoW registers every touched aggregate as it's loaded/added
        ↓
UoW collects pending events (collect_pending_events, above)
        ↓
UoW dispatches those events through
transactional_event_dispatcher.dispatch(event, uow)
   (FAIL_FAST) — the SAME uow is passed to every handler, so a handler
   updating a different aggregate does so through uow's own typed
   repository accessors (e.g. uow.projects, never a raw uow.session —
   see §2.6's corrected protocol), the identical transaction the
   triggering aggregate is part of, and stages that aggregate's own
   mutation the same explicit way before returning
        ↓
UoW re-collects — transactional handlers may have touched MORE
   aggregates (newly registered via uow.register_touched, called either
   automatically by uow.<repo>.get()/add() or explicitly by a handler
   using another of uow's own repository accessors) or recorded MORE
   events; repeat until a round produces nothing new, or
   MAX_DISPATCH_ROUNDS is hit (fail loudly on the cap — a real cycle is a
   bug, not a hang)
        ↓
Selected events are mapped to IntegrationEventEnvelope rows (§2.12)
        ↓
Outbox rows + every staged repository update are written and committed
   together (the explicit update()/add() calls above staged the mapping;
   this is where they're actually flushed)
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

### 2.9 Post-commit bus (queued, race-fixed, handler-snapshot-safe) and transactional dispatcher (stateless — round four correction)

**Correction (round four): the previous revision gave the transactional
side the identical queue/`_dispatching`-flag shape as the post-commit
bus, differing only by threading `uow` through `publish`/`_dispatch_one`.
That shape is a real, confirmed bug for the transactional side
specifically** — not a style preference. `InProcessTransactionalEventBus`
was a **long-lived singleton reused across every transaction** (stated
explicitly in the previous revision's own comment on `except BaseException`
below), yet its `_drain(uow)` method took a *single* `uow` parameter and
used that same `uow` for every event popped off `self._queue`, regardless
of which `publish(event, uow)` call had originally enqueued that event.
Concretely:

```text
Thread A: publish(eventA, uowA) — sees not-dispatching, starts _drain(uowA)
Thread B: publish(eventB, uowB) — sees dispatching=True, appends eventB, returns
Thread A's _drain(uowA) loop: pops eventB off the shared queue,
                              calls _dispatch_one(eventB, uowA)
```

Event B — which belongs to transaction B — gets dispatched using
`uowA`, transaction A's unit of work. A handler for `eventB` would then
touch `uowA.session`/`uowA`'s repositories instead of its own transaction's
— silently corrupting or cross-contaminating whichever transaction
committed second, and potentially crossing tenant boundaries if the two
transactions belonged to different tenants. **This is not fixable by
tightening the lock** (§2.9's earlier race fix, still correct for the
post-commit bus below, doesn't address this — the bug is that one `uow`
gets bound to a *drain loop*, not to the specific event it's dispatching).

**Fix: the transactional side is not a queued bus at all — it's a
stateless synchronous dispatcher.** Nothing about the transactional
dispatch needs an internal queue in the first place: §2.7's own flow
already implements breadth-first, multi-round draining *at the
`UnitOfWork` level* (`collect_pending_events` → dispatch → re-collect →
repeat) — a second, independent queue inside the bus underneath that is
redundant, and it's the redundant one that introduced the cross-`uow`
bug. Each `dispatch(event, uow)` call handles exactly the `event`/`uow`
pair it was given, synchronously, with no shared per-call state beyond
the handler registry itself (read once, under lock, as a snapshot):

```python
# src/infra/events/in_process_transactional_event_dispatcher.py
from threading import RLock

class InProcessTransactionalEventDispatcher(
    TransactionalEventDispatcher, TransactionalEventSubscriber
):
    def __init__(self) -> None:
        self._handlers: dict[type, list[TransactionalEventHandler]] = {}
        self._lock = RLock()

    def subscribe(
        self, event_type: type, handler: TransactionalEventHandler
    ) -> Subscription:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return _TransactionalSubscription(self, event_type, handler)

    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None:
        with self._lock:
            handlers = tuple(self._handlers.get(type(event), ()))
        for handler in handlers:
            handler(event, uow)  # FAIL_FAST: no try/except — propagates
            # straight out of dispatch(), which the UoW's draining loop
            # (§2.7) lets abort the whole transaction. There is no queue
            # to clear on the way out, because there is no queue.
```

No `_dispatching` flag, no `deque`, no drain loop, no `except BaseException`
queue-clear — none of that machinery was ever solving a problem this side
of the dispatch actually has, once the UoW itself owns the breadth-first
looping. `FAIL_FAST` no longer needs its own file/class name distinct from
"bus" for this reason: it's renamed
`in_process_transactional_event_dispatcher.py` /
`InProcessTransactionalEventDispatcher` throughout this ADR (file tree:
§2.3.1), to stop implying queue/bus semantics it no longer has. Every
other reference in this document (§2.6's dependency diagram, §2.7's flow,
§2.11's composition-root wiring) is updated to `transactional_event_dispatcher`/
`.dispatch(...)` accordingly.

**The post-commit bus keeps its queue** (it genuinely needs one — best-effort,
re-entrant, multiple independent adapters, "isolate and continue" —
none of which the transactional side needs), with §2.9's original
empty-queue/`_dispatching`-flip race fix, **plus one further correction:
handler lookup must be a snapshot taken under the lock, not a bare read
outside it:**

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

    def subscribe(
        self, event_type: type, handler: PostCommitEventHandler
    ) -> Subscription:
        with self._lock:
            self._handlers.setdefault(event_type, []).append(handler)
        return _PostCommitSubscription(self, event_type, handler)

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
        # Correction (round four): the handler list is snapshotted under
        # the SAME lock subscribe()/dispose() use, not read bare — a
        # concurrent subscribe()/dispose() must not be observed mid-iteration.
        with self._lock:
            handlers = tuple(self._handlers.get(type(event), ()))
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception("Post-commit handler failed for %r", type(event))
```

`_PostCommitSubscription.dispose()` removes its handler from
`self._handlers` under the same `self._lock` (mirrored by
`_TransactionalSubscription.dispose()` on the dispatcher above). Semantics
are explicit, not left implied: **a handler removed *before* a given
event's snapshot is taken does not receive that event; a handler removed
*after* the snapshot was already taken may still receive that one event,
but receives no event dispatched afterward.** This is the same
snapshot-then-iterate discipline either way — subscribe/dispose only ever
mutate `self._handlers` under the lock, dispatch only ever reads a
snapshot of it under the lock, and no handler ever runs while the lock is
held.

The lock is never held while a handler runs — only while mutating
queue/dispatching state or taking a handler snapshot — so a handler that
itself calls `publish()` (post-commit) or is invoked with a `uow` it uses
to trigger further events (transactional, via §2.7's own re-collection,
not via this dispatcher) doesn't deadlock.

**Thread policy is now narrower than before, not fully resolved.** The
transactional dispatcher's statelessness means concurrent `dispatch()`
calls from different threads, each with their own `uow`, no longer share
any per-call state that could cross-contaminate — that half of the
previous open item is resolved by this fix, not merely documented as safe.
**Still open:** whether the *post-commit* bus needs to tolerate concurrent
`publish()` calls from multiple background workers (its queue/lock design
already supports this; the open question is whether handler code itself —
especially anything touching QML-bound state — is safe to run off the
Qt main thread), and which call sites can publish from a non-Qt-main
thread at all. See "Open Items Before This Can Move to Accepted."

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

H = TypeVar("H", ViewInvalidationHint, "PlatformViewInvalidationHint")

class ViewInvalidationHandler(Protocol[H]):
    def __call__(self, hint: H) -> None: ...

class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(
        self,
        handler: ViewInvalidationHandler[ViewInvalidationHint],
        *,
        tenant_id: str,
    ) -> Subscription: ...
```

**Typing correction (round five): `ViewInvalidationHandler` must be
generic, not a plain `Protocol`.** §2.10's platform-wide fix later uses
`ViewInvalidationHandler[PlatformViewInvalidationHint]` — subscripting a
`Protocol` declared without `Protocol[H]` is invalid, not just loosely
typed. `H` is bound to exactly the two hint types this ADR defines — the
same generic-handler idiom §2.5 already established for
`TransactionalEventHandler(Protocol[E])`/`PostCommitEventHandler(Protocol[E])`,
applied consistently here instead of a second, differently-shaped way of
naming a handler protocol.

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
    def subscribe(self, handler: ViewInvalidationHandler[ViewInvalidationHint], *, tenant_id: str) -> Subscription: ...
    def subscribe_across_tenants(self, handler: ViewInvalidationHandler[ViewInvalidationHint]) -> Subscription: ...
```

so a cross-tenant subscription is a deliberate, searchable, auditable
choice at the call site — never the accidental result of a missing
argument. `scope_code`/`entity_type` filtering stays exactly where it is
today, as a binder-level closure over the (now tenant-safe) delivered
hints — this correction only narrows the channel's new responsibility to
the one dimension that actually needs to be a hard boundary.

**Correction (round four): tenant-less domain events had no defined path
to `ViewInvalidationHint` at all.** §2.1 allows a genuinely platform-wide
domain event to declare `tenant_id: str | None`, but `ViewInvalidationHint`
above declares `tenant_id: str` — required, non-optional — and every
delivery method (`notify`, `subscribe`, `subscribe_across_tenants`) is
built around that same required field. There was no rule for what a
post-commit adapter should put in `ViewInvalidationHint.tenant_id` when
translating a genuinely tenant-less event, and inventing one now (`None`
coerced to a sentinel string such as `"*"`) is exactly the kind of
undocumented, unauditable special case §2.1 already refuses to allow for
tenant IDs on domain events themselves — the same discipline applies
here. **Fix: a platform-wide hint is a distinct type, delivered through
its own explicit, auditable channel operation — never `ViewInvalidationHint`
with a sentinel tenant:**

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class PlatformViewInvalidationHint:
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None
    # deliberately no tenant_id field — this type exists ONLY for hints
    # with no tenant to scope them to; a hint that has a tenant uses
    # ViewInvalidationHint instead, never this type with a fabricated one.

class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(self, handler: ViewInvalidationHandler[ViewInvalidationHint], *, tenant_id: str) -> Subscription: ...
    def subscribe_across_tenants(self, handler: ViewInvalidationHandler[ViewInvalidationHint]) -> Subscription: ...

    def notify_platform_wide(self, hint: PlatformViewInvalidationHint) -> None: ...
    def subscribe_to_platform_wide(
        self, handler: "ViewInvalidationHandler[PlatformViewInvalidationHint]"
    ) -> Subscription: ...
```

A post-commit adapter for a tenant-scoped event only ever has
`ViewInvalidationHint` available to construct (it has a real `tenant_id`
to put in it); an adapter for a genuinely tenant-less event only ever has
`PlatformViewInvalidationHint` available (there is no `tenant_id` field to
even consider filling in) — the type system, not a convention, prevents
mixing the two. `subscribe_to_platform_wide` is intentionally separate
from `subscribe_across_tenants`: the latter is "give me every tenant's
hints" (a cross-tenant *subscriber* choice, e.g. a platform-admin
console), the former is "this hint was never scoped to any tenant to
begin with" (a property of the *event*, decided at the publishing end,
not the subscribing end) — conflating them would let a genuinely
tenant-scoped hint quietly reach `subscribe_to_platform_wide` handlers or
vice versa.

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
    project_management.register_transactional_handlers(transactional_event_dispatcher)
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
- Recursive (depth-first) re-entrant dispatch — breadth-first is far less
  surprising. For post-commit, that's an internal queue (§2.9); for
  transactional dispatch, breadth-first comes from the `UnitOfWork`'s own
  collect/dispatch/re-collect loop (§2.7), not from a queue inside the
  dispatcher itself — see §2.9's round-four correction for why the
  dispatcher having its own queue too was actually a bug, not redundant
  safety.
- Polymorphic/supertype event subscription in v1 — no demonstrated need,
  creates double-dispatch ambiguity.
- **Application services holding a `TransactionalEventDispatcher` and
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
  the transaction they need, or letting a post-commit handler reach back
  into a closed one.
- **A concrete `SqlAlchemyProjectRepository` (or `Session`) reachable from
  a `UnitOfWork`-typed handler.** Rejected per §2.5/§2.6 (round four) —
  handlers depend on module-owned repository *contracts* exposed by the
  UoW (`uow.projects`, typed against `ProjectRepository`), never a
  concrete class or raw `Session`, so the same handler works unmodified
  behind any future transport (e.g. a FastAPI command handler) that
  constructs its own concrete `UnitOfWork`.
- **A `UnitOfWorkFactory` closing over an already-created, process-lifetime
  `Session`.** Rejected per §2.6.1 (round four) — every "fresh"
  `UnitOfWork` it produced would share that one session/transaction,
  defeating rollback isolation and the "fresh state per retry" guarantee;
  the factory closes over a session *factory* (`SessionLocal`) instead.
- **A queued, stateful transactional bus sharing one `_dispatching` flag
  across concurrent transactions.** Rejected per §2.9 (round four) — a
  confirmed bug, not a hypothetical: one thread's drain loop could pop and
  dispatch a different thread's queued event using the wrong `uow`. The
  transactional side is a stateless synchronous dispatcher instead; only
  the post-commit side needs a queue.

## Consequences

- Every module gains `domain/events.py` (tenant-aware event classes),
  `application/event_handlers/view_invalidation.py` (or a UI-side
  equivalent), and module-owned constants for invalidation-hint values.
- Application services depend on `UnitOfWork` + `Clock`, never on
  `TransactionalEventDispatcher`/`PostCommitEventPublisher` directly (§2.6)
  — this is now the documented dependency shape, replacing the previous,
  contradictory migration text.
- Transactional handlers receive `(event, uow)`, never just `(event)` —
  `uow`'s own repository-contract accessors (e.g. `uow.projects`) operate
  in the same transaction the triggering aggregate used; no concrete
  repository class or raw `Session` is ever reachable from a `UnitOfWork`
  protocol, shared or module-specific (§2.5, §2.6). Post-commit handlers
  receive `(event)` only, by design, since the transaction is already
  closed by the time they run.
- `UnitOfWork` gains dynamic aggregate tracking (`register_touched`,
  `tracked_aggregates`) so the draining loop can't miss aggregates touched
  by handlers mid-dispatch — tracked in an identity map (keyed by
  `id(aggregate)`), not a `set`, since aggregates are not guaranteed
  hashable and a `set` would dedup by equality, not identity, anyway
  (§2.7).
- `src/core/shared/events/` holds event contracts + `Signal`;
  `src/core/shared/persistence/unit_of_work.py` holds the `UnitOfWork`/
  `UnitOfWorkFactory` protocols (moved out of `shared/events/`, round
  four — not events-specific); `src/core/shared/time/clock.py` holds the
  general-purpose `Clock` protocol (not events-specific either); the
  transactional dispatcher and post-commit bus live in `src/infra/events/`
  and `SystemClock` lives in `src/infra/time/`; the Qt-marshaling channel
  lives in `src/ui_qml/infrastructure/events/`.
- Concrete `SqlAlchemyUnitOfWorkBase` replaces the content of
  `src/infra/persistence/db/unit_of_work.py` — checked, its existing
  `session_scope()` helper has zero callers anywhere in `src/`, so
  reclaiming the enterprise-standard name for the real Unit of Work costs
  no import-site migration; `session_scope()`'s commit/rollback/close
  shape is folded in as the private helper `__enter__`/`__exit__` use
  internally (§2.6.1). Each module gets its own thin
  `SqlAlchemy<Module>UnitOfWork(SqlAlchemyUnitOfWorkBase)` subclass and
  matching `<Module>UnitOfWorkFactory` (round five) — not one cross-module
  class importing every module's repository vocabulary, and not mirroring
  `RepositoryBundle`'s existing flat, all-modules-together shape, since a
  `UnitOfWork` is constructed per transaction rather than once at
  composition time. Every factory closes over `SessionLocal` (a session
  *factory*), not the existing process-lifetime `session` instance — a
  fresh `Session` per `UnitOfWork`, per the round-four correction — and is
  created in `src/infra/composition/app_container.py`'s
  `build_service_graph`, the same centralized composition point that
  already builds today's `RepositoryBundle` (which keeps using the one
  process-lifetime `session` unchanged, for not-yet-migrated services).
- Every repository exposes an explicit `update(aggregate)`/`add(aggregate)`,
  and every service/handler calls it before `uow.commit()` — `commit()`
  coordinates the transaction and event dispatch, it does not persist a
  mutated aggregate by itself (round five; confirmed against this
  codebase's own `Task.update()`, which persists through a raw
  version-checked `UPDATE` that bypasses ORM attribute tracking entirely).
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
  (`handle_task_completed` updating `Project`, loaded via `uow.projects`)
  does so within the same still-open transaction as the triggering
  aggregate — verified by asserting both changes are visible before
  commit, and that rolling back that transaction undoes both together,
  not just the originating aggregate's change.
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
- Two threads calling `publish()` on the **post-commit bus** concurrently
  do not corrupt the internal queue or double-dispatch (bus-level thread
  safety, independent of whatever thread-confinement policy is eventually
  decided per the still-open item in "Open Items Before This Can Move to
  Accepted").
- A `publish()` (post-commit bus) that arrives at the exact moment a drain
  loop is checking "is the queue empty" is never stranded — it either gets
  picked up by the in-progress drain, or `_dispatching` has genuinely
  already flipped back to `False` and the new `publish()` starts its own
  drain (§2.9's race fix). This needs a deliberately adversarial test —
  e.g. a handler that, on its last invocation, blocks until a second
  thread's `publish()` call has entered `publish()`'s own critical
  section, to force the exact interleaving the bug required.
- **Round four:** two threads calling `TransactionalEventDispatcher.dispatch(event, uow)`
  concurrently, each with its *own* `uow`, never cross-contaminate — every
  handler invocation only ever receives the `uow` its own caller passed in
  (confirms the §2.9 cross-transaction bug is actually gone, not just
  described as gone: the old test asserting a `FAIL_FAST` exception
  "clears any remaining queued events for that bus" no longer applies —
  there is no queue left to clear, and this replaces it).
- The post-commit bus's handler-registry snapshot is taken under the same
  lock `subscribe()`/`dispose()` use: a handler disposed *before* a given
  event's dispatch snapshot is not called for that event; one disposed
  *after* the snapshot may still be called once more but never again
  (§2.9's snapshot-semantics correction, directly tested with a
  disposal-during-dispatch race).
- Events do not leak across a reused/rehydrated ORM entity instance.
- `UnitOfWorkFactory.create()` returns a `UnitOfWork` backed by a genuinely
  new `Session` each call — two `create()` calls in sequence must not
  share a session/transaction, and rolling one back must have no effect on
  the other (§2.6.1's session-factory-vs-shared-session correction,
  directly tested).
- No transactional handler can reach a concrete repository class or a raw
  `Session` through a `UnitOfWork`-typed parameter — enforced at the type
  level by the shared protocol declaring neither (§2.6); a handler that
  needs another aggregate's repository only compiles against a
  module-specific `UnitOfWork` extension (e.g. `ProjectManagementUnitOfWork`)
  exposing that repository's *contract* type.
- A genuinely tenant-less event's post-commit adapter can only construct a
  `PlatformViewInvalidationHint`, never a `ViewInvalidationHint` with a
  fabricated `tenant_id`; `notify_platform_wide`/`subscribe_to_platform_wide`
  are exercised as a channel distinct from `notify`/`subscribe`/
  `subscribe_across_tenants` — a handler subscribed one way never receives
  hints delivered the other way (§2.10's tenant-less reconciliation).
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
- **Round five:** mutating an aggregate and calling `uow.commit()`
  *without* first calling the repository's `update(aggregate)` does
  **not** persist the change — directly tested against at least one
  aggregate using each of this codebase's two confirmed persistence
  mechanisms (a raw optimistic-concurrency `update_with_version_check`
  call, and a tracked-ORM-attribute mutation relying on flush), so the
  rule is proven for both, not just whichever one happened to be
  convenient to test.
- A transactional handler typed against a module-specific `UnitOfWork`
  extension (e.g. `ProjectManagementUnitOfWork`) can access that module's
  own repository accessors (`uow.projects`), and a type checker rejects
  code that tries to access another module's repository accessor through
  it (confirms the module-specific typing actually constrains what a
  handler can reach, not just that it happens to work at runtime).

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

**Round four** (external review against the companion execution plan)
resolved five further issues, all substantive: a transactional handler
constructing a concrete `SqlAlchemyProjectRepository` straight from
`uow.session`, breaking the framework-agnostic guarantee the execution
plan requires — fixed by dropping `session` from the shared `UnitOfWork`
protocol entirely and typing handlers against module-specific repository
*contracts* exposed by an extended per-module protocol (§2.5, §2.6); a
`UnitOfWorkFactory` described as closing over an already-created
process-lifetime `Session` rather than a session factory, which would
have made every "fresh" `UnitOfWork` share one transaction — fixed by
closing over `SessionLocal` instead (§2.6.1); a confirmed cross-transaction
bug where the transactional bus's shared queue and single `_dispatching`
flag let one thread's drain loop dispatch a *different* thread's event
using the wrong `uow` — fixed by making the transactional side a stateless
synchronous dispatcher with no queue at all, renamed
`TransactionalEventDispatcher`/`in_process_transactional_event_dispatcher.py`
throughout (§2.9); no defined mapping from a tenant-less domain event to
`ViewInvalidationHint`'s required `tenant_id` — fixed with a distinct
`PlatformViewInvalidationHint` type and `notify_platform_wide`/
`subscribe_to_platform_wide` channel operations (§2.10); and the
post-commit bus reading its handler registry outside the lock, racing a
concurrent `subscribe()`/`dispose()` — fixed with a lock-held snapshot
before iterating (§2.9). The `UnitOfWork`/`UnitOfWorkFactory` protocols
also moved out of `shared/events/` into their own `shared/persistence/`
package, for the same reason `Clock` got its own `shared/time/` package
in round three (§2.6.1).

**Round five** (checked directly against this codebase's actual
repository and session code, not just the design in the abstract)
resolved three more: `uow.commit()` was implicitly assumed to persist a
mutated aggregate on its own, but this codebase's own
`SqlAlchemyTaskRepository.update()` persists through
`update_with_version_check` — a raw, version-checked `UPDATE` that
bypasses SQLAlchemy's ORM attribute tracking entirely — so nothing would
have flushed a mutated `Task` without an explicit call; fixed by requiring
every repository to expose `update(aggregate)`/`add(aggregate)` and every
service/handler to call it before `commit()` (§2.6, §2.7 — the flow
diagram now shows this as its own step); the base
`UnitOfWorkFactory.create() -> UnitOfWork` return type couldn't support
`uow.tasks`/`uow.projects`, and one concrete cross-module
`SqlAlchemyUnitOfWork` would have imported every module's repository
vocabulary into a single per-transaction object — fixed with paired
per-module `<Module>UnitOfWork`/`<Module>UnitOfWorkFactory` protocols and
thin concrete `SqlAlchemy<Module>UnitOfWork(SqlAlchemyUnitOfWorkBase)`
subclasses, deliberately not mirroring `RepositoryBundle`'s existing flat,
all-modules-together shape (§2.6, §2.6.1); and
`ViewInvalidationHandler[PlatformViewInvalidationHint]` (§2.10) subscripted
a `Protocol` round four had declared non-generic — fixed by making
`ViewInvalidationHandler(Protocol[H])` generic over the two hint types
(§2.10). Round five also recorded (in §2.6.1, not resolved there) a
migration-time session-staleness risk: while a module is partially
migrated, a committed change through a fresh per-transaction `Session` is
not guaranteed to be visible to an already-open, long-lived
`RepositoryBundle`-backed read path for the same rows, since SQLAlchemy
does not overwrite an already-identity-mapped instance's attributes from
a later `select()` unless it was expired or `populate_existing()` was
used — confirmed against this codebase's own dashboard/workspace
controllers, which hold their repository/session graph for the
controller's whole lifetime. This is a per-phase migration concern with
its concrete handling in the execution plan (Constraint 5), not a defect
in the mechanism itself.

**Still genuinely open** (narrower than before — round four's stateless
transactional dispatcher resolves the transactional side's share of this;
what's left is squarely about the post-commit bus and QML thread policy):

1. Which specific call sites can publish from a non-Qt-main thread (needed
   to build `qt_view_invalidation_channel.py`'s marshaling behavior).
2. Given (1), whether the **post-commit bus** needs to tolerate concurrent
   `publish()` calls from multiple background workers, and — regardless of
   the answer — whether post-commit handler code itself (especially
   anything touching QML-bound state) is safe to run off the Qt main
   thread. The transactional dispatcher no longer has an analogous open
   question: it holds no state across calls beyond a lock-protected
   handler-registry snapshot, so concurrent `dispatch()` calls from
   different threads with different `uow`s are already safe by
   construction (§2.9).
3. Confirmation, per module phase, of the session-staleness mitigation
   actually chosen (migrate the read path too vs. an explicit
   `expire_all()`/`populate_existing()` bridge) — the execution plan
   requires *a* choice be made and tested per phase, but which one is a
   per-phase decision, not settled here.

All three should be resolved before this ADR is marked Accepted.
