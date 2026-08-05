# ADR-005: Domain Events

- Status: proposed
- Date: 2026-08-05 (revised 2026-08-05 after three rounds of team review)

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

**This is the third revision, after three rounds of team review.** Round
one corrected an absolute "never before commit" rule and caught a
composition-root pattern that would have recreated the exact problem this
ADR removes. Round two found the fix for round one was described but never
actually wired into one design, plus a hint object that couldn't satisfy
its own test. Round three found the wiring still had a real bug (events
referencing a field the event class didn't declare), an ownership
contradiction between two sections, an aggregate-discovery gap in the
draining loop, a missing rollback-safety rule, a thread-safety gap in the
bus sketch, and a placement inconsistency in the `Clock` example. All are
fixed below.

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

### 2.3 `Clock` — protocol in shared, implementation in infra (placement fixed)

The previous revision put both the `Clock` protocol *and* the concrete
`SystemClock` in the same `src/core/shared/clock.py` file — directly
contradicting this ADR's own rule that concrete implementations live in
infrastructure, not in `shared/`. Split:

```python
# src/core/shared/clock.py
from typing import Protocol
from datetime import datetime

class Clock(Protocol):
    def now(self) -> datetime: ...
```

```python
# src/infra/system_clock.py
from datetime import datetime, timezone
from src.core.shared.clock import Clock

class SystemClock:
    def now(self) -> datetime:
        return datetime.now(timezone.utc)
```

`Clock` is deliberately not nested under `events/` — it's a general
cross-cutting utility any aggregate can use, not an events-specific
concern, so it sits at `shared/` root next to `signal.py`'s package.

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

### 2.5 Two contracts, not one combined bus

```python
# src/core/shared/events/domain_event_publisher.py
class DomainEventPublisher(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
```

```python
# src/core/shared/events/domain_event_subscriber.py
class DomainEventSubscriber(Protocol):
    def subscribe(self, event_type: type[E], handler: Callable[[E], None]) -> Subscription: ...
```

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
Application services do not depend on `DomainEventPublisher` directly —
they depend on the unit of work and a `Clock`:

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

The dependency shape:

```text
Application service
├── UnitOfWork (or UnitOfWorkFactory)
└── Clock

UnitOfWork / EventCoordinator (owned by the UoW, not the application service)
├── transactional_event_bus  (DomainEventPublisher, FAIL_FAST)
├── post_commit_event_bus    (DomainEventPublisher, ISOLATE_AND_CONTINUE)
├── integration event mapper (selects + builds IntegrationEventEnvelope rows)
└── outbox repository
```

Ordinary application services never need a `DomainEventPublisher`
dependency merely to publish events an aggregate already recorded — that
would let two different call paths dispatch the same event twice, or let
dispatch depend on which service happened to be used. A service *would*
take a `DomainEventPublisher` directly only if it needs to publish
something that isn't tied to a specific aggregate's recorded events at
all — an edge case, not the common path.

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

```python
class UnitOfWork:
    def register_touched(self, aggregate: RecordsDomainEvents) -> None:
        self._tracked_aggregates.add(aggregate)  # identity-based set

    def tracked_aggregates(self) -> frozenset[RecordsDomainEvents]:
        return frozenset(self._tracked_aggregates)
```

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
UoW dispatches those events through transactional_event_bus (FAIL_FAST)
        ↓
UoW re-collects — transactional handlers may have touched MORE
   aggregates (newly registered) or recorded MORE events; repeat until
   a round produces nothing new, or MAX_DISPATCH_ROUNDS is hit (fail
   loudly on the cap — a real cycle is a bug, not a hang)
        ↓
Selected events are mapped to IntegrationEventEnvelope rows (§2.12)
        ↓
Outbox rows + business changes are written and committed together
        ↓
Only on successful commit: clear_domain_events() on every tracked aggregate
        ↓
The same collected events dispatch through post_commit_event_bus
   (ISOLATE_AND_CONTINUE)
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

### 2.9 Bus internals — queued dispatch, and now explicitly thread-safe

Breadth-first via an internal queue (unchanged from the prior revision),
but the previous sketch used `self._queue`/`self._dispatching` with **no
locking at all** — a real gap, given this same ADR already anticipates
publishers that might not all be on one thread (§2.11). `Signal` (the
existing primitive this is built on) already uses an `RLock` internally;
the bus wrapping it should not be less careful:

```python
from collections import deque
from threading import RLock

class InProcessDomainEventBus(DomainEventPublisher, DomainEventSubscriber):
    def __init__(self, *, failure_policy: FailurePolicy) -> None:
        self._failure_policy = failure_policy
        self._handlers: dict[type, list[Callable]] = {}
        self._queue: deque[DomainEvent] = deque()
        self._dispatching = False
        self._lock = RLock()

    def publish(self, event: DomainEvent) -> None:
        with self._lock:
            self._queue.append(event)
            if self._dispatching:
                return
            self._dispatching = True
        try:
            while True:
                with self._lock:
                    if not self._queue:
                        break
                    current = self._queue.popleft()
                self._dispatch_one(current)  # never called while holding _lock
        finally:
            with self._lock:
                self._dispatching = False

    def _dispatch_one(self, event: DomainEvent) -> None:
        for handler in self._handlers.get(type(event), ()):
            if self._failure_policy is FailurePolicy.FAIL_FAST:
                handler(event)
            else:
                try:
                    handler(event)
                except Exception:
                    logger.exception("Post-commit handler failed for %r", type(event))
```

The lock is never held while a handler runs — only while mutating queue/
dispatching state — so a handler that itself calls `publish()` re-entrantly
doesn't deadlock and doesn't need to know about the lock at all.

**This does not fully resolve thread policy, only the bus's own internal
safety.** Whether a *transactional* bus instance should even accept
publishes from more than one thread concurrently (a single UoW/transaction
is normally single-threaded already, which may make this moot for that
bus) versus whether the *post-commit* bus needs to tolerate concurrent
publishes from multiple background workers is still an open decision — see
§2.14.

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

class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(self, handler: Callable[[ViewInvalidationHint], None]) -> Subscription: ...
```

`kw_only=True`; `entity_id` optional for hints that don't correspond to
one entity (auth changes, tenant switches, bulk recalculation). `category`
and `scope_code` are both kept as independent dimensions — checked
against the real production QML binders before deciding this: every real
`_subscribe_domain_change(...)` call site passes `scope_code` and
positional entity-type arguments; none currently passes `category=`, but
`category` is a real field on today's `DomainChangeEvent` (it gates the
`shared_master_changed` bridge internally), so it's kept rather than
dropped on an unverified assumption.

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
    subscriber: DomainEventSubscriber,
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
- **Application services holding a `DomainEventPublisher` and dispatching
  events themselves.** Rejected per §2.6 — two orchestration models in one
  design risks double-dispatch or silently-skipped dispatch depending on
  call path; the unit of work is the single owner.
- **A frozen, up-front list of "touched aggregates" for the draining
  loop.** Rejected per §2.7 — misses aggregates a transactional handler
  loads or creates mid-dispatch, exactly the scenario this ADR uses as its
  own motivating example.
- **Reusing or retrying a rolled-back aggregate instance.** Rejected per
  §2.8 — its in-memory state may not match what's actually persisted.

## Consequences

- Every module gains `domain/events.py` (tenant-aware event classes),
  `application/event_handlers/view_invalidation.py` (or a UI-side
  equivalent), and module-owned constants for invalidation-hint values.
- Application services depend on `UnitOfWork` + `Clock`, not on
  `DomainEventPublisher` directly (§2.6) — this is now the documented
  dependency shape, replacing the previous, contradictory migration text.
- `UnitOfWork` gains dynamic aggregate tracking (`register_touched`,
  `tracked_aggregates`) so the draining loop can't miss aggregates touched
  by handlers mid-dispatch.
- `src/core/shared/events/` holds contracts + `Signal`; concrete buses
  live in `src/infra/events/`; `SystemClock` lives in `src/infra/`; the
  Qt-marshaling channel lives in `src/ui_qml/infrastructure/events/`.
- Subscription ownership is explicit at both the module (composition-root
  registry, app-shutdown disposal) and controller (self-owned,
  teardown-time disposal) level.

## Migration Impact

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
  independent of whatever thread-confinement policy §2.14 eventually
  decides).
- Events do not leak across a reused/rehydrated ORM entity instance.
- Selected integration events are written to the outbox in the same
  transaction as the business change, never after.
- A `ViewInvalidationHint` scoped to tenant A does not reach a controller
  bound to tenant B.
- Re-entrant publish during a dispatch pass is processed breadth-first.
- Old and new mechanisms emit equivalent invalidation behavior for any
  event migrated during the transition, verified per-module.

## Implementation Evidence

None yet — this ADR is a design proposal, not yet implemented.

## Open Items Before This Can Move to Accepted

Resolved by this revision: the missing `tenant_id` field, the
application-service-vs-UoW ownership contradiction, dynamic aggregate
discovery in the draining loop, the rollback-reuse hazard, `Clock`'s
contract/implementation placement, the bus's internal thread-safety, and
explicit subscription ownership at both lifetimes.

**§2.14 — still genuinely open, and now broader than before:**

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
