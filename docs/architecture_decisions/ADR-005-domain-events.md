# ADR-005: Domain Events

- Status: proposed (revision 6 — Platform architecture audit incorporated)
- Date: 2026-08-05, revised 2026-08-25 after a dedicated, evidence-based Platform-only
  architecture audit (`docs/platform_modernization/domain_event/platform_domain_event_audit.md`)
  found this design was not landing on the blank slate its earlier revisions assumed.
- Companion documents: [ADR-005 Execution Plan](ADR-005-execution-plan.md) (cross-Platform-and-module
  sequencing), [`platform_domain_event_implementation_plan.md`](../platform_modernization/domain_event/platform_domain_event_implementation_plan.md)
  (exact Platform how-to, files, tests, exit criteria).
- Related decisions: [ADR-PF-008](ADR-PF-008-approval-unit-of-work.md) (accepted, implemented —
  reconciled explicitly below), [ADR-PF-011](ADR-PF-011-durable-integration-outbox-inbox.md)
  (accepted, implemented — boundary preserved, not merged), [ADR-004](ADR-004-calendar-assignment-split-ownership.md)
  (governs one of the two dependency-direction findings below).

## Revision History (condensed)

Rounds 1-5 (2026-08-05, same day, prior to any implementation) hammered out the mechanics
still in force below: a composition-root pattern that avoided recreating the old bridge-wiring
problem; a hint object that could actually satisfy tenant scoping; a wiring bug where events
referenced a field their own class didn't declare; an ownership contradiction between two
sections; a missing aggregate-discovery gap in the draining loop; a rollback-safety rule; a
thread-safety gap in the bus; a `Clock` placement inconsistency (settled at
`shared/time/clock.py` + `infra/time/system_clock.py`); a `UnitOfWork`/`UnitOfWorkFactory`
protocol pair that hadn't been defined despite being used; a transactional handler
constructing a concrete `SqlAlchemyProjectRepository` directly, breaking framework-agnosticism;
a `UnitOfWorkFactory` closing over an already-created process-lifetime `Session` instead of a
session factory (would have defeated rollback isolation); a genuine cross-transaction bug in a
queued transactional bus design (fixed by making that side a stateless synchronous dispatcher);
a missing `ViewInvalidationHint` path for tenant-less events (fixed with a distinct
`PlatformViewInvalidationHint` type); a post-commit bus reading its handler registry outside its
lock; `uow.commit()` wrongly assumed to persist a mutated aggregate on its own (this codebase's
own `Task.update()` proved otherwise); a base `UnitOfWorkFactory` return type that couldn't
support `uow.tasks`/`uow.projects`; and one cross-module concrete `UnitOfWork` design that would
have imported every migrated module's repository vocabulary into one class. All of these were
resolved in rounds 1-5 and their fixes are reflected directly in the Decision sections below
without being re-narrated blow-by-blow. Full contemporaneous detail remains in this file's git
history if ever needed.

**Round 6 (this revision)** is a response to a dedicated, evidence-based audit of Platform's
*actual* current architecture (not just this ADR's own design-in-the-abstract). The audit found
five things this ADR had gotten wrong or left unaddressed, all corrected below:

1. This design is **not greenfield for the transaction/event *concept*, only for typed
   *vocabulary***. `ApprovalService` (ADR-PF-008, accepted and implemented) already runs almost
   exactly the transaction discipline §11 (UnitOfWork Semantics) describes, under a different
   name, at a different granularity, without this ADR ever mentioning it. See §26 (Related
   Decisions) and §11.
2. **The scope model was tenant-only.** This is wrong for this product: a tenant can and does
   contain multiple organizations, and nothing in the original design prevented an
   organization-A-scoped fact from reaching an organization-B-scoped subscriber inside the same
   tenant. See §6 (Scope / Tenant / Organization Semantics) and §14 (View Invalidation).
3. **Event metadata (correlation/causation) was left as an open question with no shape decided.**
   §8 (Event Metadata Decision) now resolves it, deliberately keeping it off the business-fact
   dataclasses themselves.
4. **Event recording (aggregate-records-its-own-events vs. hand-construction) was left as an
   explicit "revisit later" item in the decision matrix.** §9 (Event Recording Decision) now
   resolves it, with explicit criteria rather than a blanket rule.
5. **Naming, repository-location, and architecture-guardrail gaps** the audit found in Platform's
   *existing* code (a real, ungoverned `platform → business module` import; a genuine `Signal`
   name collision with Qt's own `Signal`; `PlatformEvent` sharing "event" vocabulary with an
   unrelated audit record; three independently duplicated Qt controller bases) are now addressed
   explicitly rather than left for an implementer to discover the same way the audit did. See §19
   (Naming), §20 (Repository Ownership / Locations), §21 (Architecture Guardrails), §23 (Legacy
   Compatibility).

The execution plan is revised alongside this ADR (see its own revision note) to insert an
explicit Platform-foundation phase before any business module migrates, and to strike the dead
`maintenance`-module phase the audit found targets a module deleted from this codebase on
2026-08-20.

## Context

`src/core/shared/events/domain_events.py` currently does two unrelated jobs under one name:

1. A **UI refresh notifier** — after a change, tell whichever desktop controllers are alive right
   now to re-fetch their view. In-memory, synchronous, best-effort, same process only.
2. An attempt at **domain events** — the same file enumerates roughly 30 hardcoded `Signal`
   fields, one per module entity (`tasks_changed`, `inventory_items_changed`, `auth_changed`, ...),
   each carrying a generic `DomainChangeEvent(category, scope_code, entity_type, entity_id,
   source_event)` — four free-form strings and an ID.

[ADR-PF-011](ADR-PF-011-durable-integration-outbox-inbox.md) already called this out: *"the shared
process-local domain events are UI refresh signals; neither is a durable integration mechanism."*
ADR-PF-011 answers the *integration* half of that observation and explicitly defers the *domain
event* half. This ADR is that other half. **Integration events remain out of scope here** —
ADR-PF-011 owns that decision; §13 (Integration Event / Outbox Boundary) only restates the one
ordering constraint between the two, unchanged from earlier revisions.

## Current State

Verified by the Platform audit (2026-08-25) against actual repository/session code, not assumed:

- **The old mechanism's actual scope is larger than named-`Signal`-field counts suggest.** 66
  application-layer files import the `domain_events` singleton directly and call `.emit(...)` on
  it — 25 of those inside `src/core/platform/` itself, 41 across business modules. This is the
  real coupling surface a migration has to unwind, not just the ~30 named fields on
  `DomainEvents`.
- **Platform owns zero typed domain-event classes today** (confirmed: no
  `@dataclass(frozen=True)` class ending in `Changed`/`Created`/`Approved`/`Completed`/etc.
  anywhere under `src/core/platform/`). This part of the design genuinely is greenfield for
  Platform.
- **The transaction/event-coordination *concept* is not greenfield anywhere in this codebase.**
  `ApprovalService` (`src/core/platform/application/approval/approval_service.py`, governed by
  the accepted ADR-PF-008) already implements: one outer operation owns commit; apply handlers
  stage only; post-commit reactions run after a successful commit and are individually
  isolated from failure. Outside Platform (cited here only for contrast, not audited as part of
  this revision), `project_management`'s `Resource*UnitOfWork` classes independently reinvent a
  typed frozen-dataclass event, a commit/rollback wrapper, and isolate-and-continue post-commit
  dispatch that dual-emits into the legacy bus. Neither of these shares an abstraction with the
  other, or with this ADR's proposed one — three independent inventions of overlapping pieces of
  the same idea is itself evidence for building the general mechanism, not evidence it is
  unnecessary.
- **`SessionLocal` (the real session factory this ADR's `UnitOfWorkFactory` needs) has exactly
  three references in this codebase's entire history**: its own definition, the dead
  `session_scope()` (§11.1), and one call at process startup. This ADR's proposed per-transaction
  usage would be the first real per-transaction use of it, ever.
- **The old mechanism has zero tenant isolation and zero organization concept.**
  `DomainChangeEvent` has no `tenant_id` field at all; no consumer anywhere filters by tenant;
  nothing in the codebase's UI-invalidation path has ever modeled "organization" as a dimension
  distinct from tenant, despite `IntegrationEventEnvelope` and `PlatformEvent` both already
  carrying `organization_id` correctly.
- **The `maintenance` module referenced throughout the (now superseded) execution plan's old
  Phase 5 was deleted from this codebase on 2026-08-20** — after this ADR was first drafted. Zero
  raw `DomainChangeEvent(...)` construction sites remain anywhere in `src/`.
- **Real architecture-enforcement tooling already exists** (AST-based import-boundary tests under
  `src/tests/architecture/`), correcting an earlier assumption that no such tooling exists. It has
  a real coverage gap on exactly the axis this migration needs (`platform → business module`
  imports) — see §21.

## Problem

Business logic, UI refresh, audit recording, user notification, and durable cross-process
integration are all reachable through vocabulary containing the word "event," under one shared,
untyped, tenant-blind, organization-blind, globally-mutable singleton that nothing was ever
designed to be. Concretely, this makes it impossible to:

- express "this fact belongs to Organization A1 of Tenant A, not Organization A2" — the mechanism
  has no organization concept and no tenant concept;
- let a cross-aggregate business reaction (e.g. "a completed task should update its project's
  progress") happen atomically with the change that triggered it — there is no shared transaction
  boundary the reaction can join;
- distinguish "the fact that happened" from "the read model that needs to be refreshed" — every
  real payload is a bare ID with no business content, and every real consumer only ever decides
  whether to call `refresh()`;
- trust that a new call site emitting an event won't silently break isolation between subscribers,
  since the underlying `Signal` primitive's only isolation is for two specific Qt-lifecycle
  exceptions, and every other exception aborts the remaining subscribers in that dispatch.

## Decision

### 1. Event Taxonomy

Five concepts, kept structurally and vocabulary-distinct. None of the first four collapse into a
single "universal event bus" — the audit found no evidence supporting that collapse, and this
revision explicitly rejects it as an alternative (§27).

| Concept | Meaning | Current mechanism | This ADR's disposition |
|---|---|---|---|
| **Domain Event** | A business fact that occurred in the domain (`TaskCompleted`, `PurchaseOrderApproved`, `EmployeeAssigned`) | None exist under Platform; module-owned examples exist ad hoc (`ResourceMasterChanged`) | **New** — §7 defines the contract |
| **View Invalidation** | A transport-independent hint that a read model is stale and should be re-read — *not* a business fact | The legacy `domain_events`/`Signal` mechanism, functioning as this despite its name | **New, formalized** — §14 |
| **Integration Event** | A durable, cross-process, schema-versioned message governed by ADR-PF-011 | `IntegrationEventEnvelope` + outbox/inbox — mature, correct, already separate | **Unchanged** — §13 preserves the boundary |
| **Notification** | A persisted, user-facing, multi-channel in-app notification feature | `Notification`/`NotificationService` | **Unchanged** — not part of this taxonomy at all |
| **Audit Record** | An immutable, append-only governance/compliance log entry | `PlatformEvent` (misleadingly named — it is not dispatched, only persisted), `AuditEntry` | **Unchanged behavior; naming addressed non-blockingly** — §19 |

A **Domain Event is never**: a UI refresh signal (`tasks_changed`), an application-orchestration
verb (`refresh_project`), or a cache-invalidation trigger (`reload_dashboard`). Those are all
**View Invalidation** concerns.

### 2. Repository Ownership Terminology

The audit correctly found that `src/core/shared/` sits *below* both `src/core/platform/` and
`src/core/modules/<module>/`, not inside Platform. This ADR uses precise ownership language
throughout, not "Platform owns shared/events":

- **Core Shared** (`src/core/shared/`) owns generic, cross-cutting *contracts* with zero business
  vocabulary — `DomainEvent`, `RecordsDomainEvents`, `Signal`'s eventual successor, `UnitOfWork`/
  `UnitOfWorkFactory` protocols, `Clock`. Consumed by both Platform and every module; depends on
  neither.
- **Platform composition** (`src/infra/composition/`) wires the concrete, generic infrastructure
  (dispatchers, buses, channels) that implements Core Shared's contracts.
- **Platform capabilities** (`src/core/platform/domain/<capability>/`, `.../application/<capability>/`)
  own Platform-specific business event vocabulary, if and when a capability adopts one.
- **Business modules** (`src/core/modules/<module>/domain/`) own module-specific business event
  vocabulary — unchanged from this ADR's original design.
- **UI** (`src/ui_qml/`) owns the Qt-specific adapter that turns `ViewInvalidationHint`s into Qt
  signal emissions.
- **Infrastructure** (`src/infra/`) owns concrete, technology-specific implementations of Core
  Shared's contracts (the in-process dispatcher, the in-process bus, `SystemClock`).

### 3. Scope / Tenant / Organization Semantics

**Decision:** every tenant-owned `DomainEvent` and `ViewInvalidationHint` carries both
`tenant_id: str` (always required for tenant-owned facts) and `organization_id: str | None`
(explicit — non-`None` when the fact belongs to one organization, explicitly `None` when the fact
is genuinely tenant-wide and not owned by any single organization). Genuinely
installation/platform-wide facts — no tenant at all — use a **separate type** with no `tenant_id`
field, exactly as this ADR's earlier revisions already established for the tenant dimension; the
same discipline now extends one level down for organization.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class OrganizationRenamed:
    tenant_id: str
    organization_id: str          # this event IS about one specific organization
    previous_name: str
    new_name: str
    occurred_at: datetime

@dataclass(frozen=True, slots=True, kw_only=True)
class TenantSecurityPolicyChanged:
    tenant_id: str
    organization_id: None = None  # explicitly tenant-wide — never omitted, never a sentinel
    policy_field: str
    occurred_at: datetime
```

**Never** substitute the desktop session's currently-active organization for an event's own
`organization_id`. An organization-scoped mutation's event carries the organization it actually
mutated — read directly off the aggregate/command, not off mutable "current organization" UI
state, which may differ (a user could mutate Organization A1 while their session's active
organization selector is pointed at A2, in a future multi-org-aware UI).

**Decision — representation:** plain `tenant_id`/`organization_id` fields directly on each event/
hint type, not a nested `EventScope`/`TenantScope`/`OrganizationScope` type hierarchy.
*Rationale:* `IntegrationEventEnvelope` already proves this flat shape works in production
(ADR-PF-011); a nested scope hierarchy adds an indirection layer with no behavior of its own, and
no code anywhere in this codebase has ever needed to pattern-match over "kinds of scope" as a
first-class concept. *Alternatives considered:* a sealed `EventScope` class hierarchy
(`TenantScope`/`OrganizationScope`/`PlatformScope`) — rejected as unnecessary structure for a
distinction two plain fields already express unambiguously, and inconsistent with the one proven
precedent this codebase already has. *Consequences:* every tenant-owned event/hint type is
slightly more verbose (two fields instead of one field or one nested object) in exchange for
being trivially greppable and directly consistent with `IntegrationEventEnvelope`.

### 4. Domain Event Contract

Unchanged in shape from earlier revisions, restated for completeness. Each module (and, per §1,
each Platform capability that adopts one) declares its own event types, as frozen dataclasses,
named in the past tense, in its own `domain/events.py`:

```python
# src/core/modules/project_management/domain/events.py
from dataclasses import dataclass
from datetime import datetime

@dataclass(frozen=True, slots=True, kw_only=True)
class TaskReassigned:
    tenant_id: str
    organization_id: str
    task_id: str
    project_id: str
    previous_assignee_id: str | None
    new_assignee_id: str | None
    occurred_at: datetime
```

`slots=True` and `kw_only=True` on every event class, consistently — `kw_only` added in this
revision so that adding `organization_id` to every existing worked example never becomes a
positional-argument ambiguity risk as more fields are added later. Fields use `str` IDs for now
(no module currently has typed ID value objects); adopt typed IDs once/if a module introduces
them for other reasons.

A minimal shared marker lives under Core Shared:

```python
# src/core/shared/events/domain_event.py
from typing import Protocol, runtime_checkable
from datetime import datetime

@runtime_checkable
class DomainEvent(Protocol):
    occurred_at: datetime
```

Typing contract only — zero business vocabulary, zero tenant/organization vocabulary (those are
per-event fields, not part of the marker protocol, since a genuinely platform-wide event
legitimately has neither).

### 5. Event Metadata Decision

**Decision:** business-fact data and dispatch/execution metadata are two different things, kept
in two different places. A `DomainEvent` dataclass carries **only** fields that are part of the
business fact itself (identifiers, previous/new state, `tenant_id`/`organization_id`,
`occurred_at`). A separate, small `DomainEventContext` carries dispatch-time tracing metadata,
owned by the `UnitOfWork` for the lifetime of one transaction, not embedded in the event:

```python
# src/core/shared/events/domain_event_context.py
@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEventContext:
    correlation_id: str
    causation_id: str | None = None
    command_id: str | None = None
```

A `UnitOfWork` is constructed with a context (`UnitOfWorkFactory.create(context=...)`) and
exposes it as a read-only property. `TransactionalEventDispatcher.dispatch(event, uow)`'s handler
signature is unchanged — a handler that needs tracing metadata reads `uow.context`, since it
already has `uow`. `PostCommitEventPublisher.publish(event, context)` **does** gain the context
as an explicit second parameter (a deliberate change from this ADR's earlier revisions, which had
`publish(event) -> None` only) — the transaction is closed by the time post-commit handlers run,
so `uow` itself is unavailable, but the correlation/causation metadata needed to make a failure
log line useful (§18) still has to reach that handler somehow.

**Rationale:** keeps every `DomainEvent` dataclass pure business vocabulary — a module author
defining `TaskCompleted` never has to think about tracing plumbing — while still making
correlation/causation available exactly where the audit found it missing (§18, Observability).
**Alternatives considered:** (a) put `correlation_id`/`causation_id` directly on every
`DomainEvent` — rejected: pollutes business vocabulary with infrastructure concerns, and
duplicates data that's actually one-per-transaction, not one-per-event, when several events fire
in the same unit of work; (b) a generic `DomainEventEnvelope[DomainEvent]` wrapper type threaded
everywhere instead of a UoW-owned context — rejected: forces every handler signature to unwrap a
generic envelope even when it has no interest in the metadata, whereas the context-on-the-UoW
design makes tracing data available only to the two dispatch points that actually need to pass it
onward (transactional handlers already have `uow`; post-commit handlers get it as an explicit,
opt-in parameter).

**Fields explicitly excluded and why:** `actor_id` is deliberately **not** a generic context
field. Where "who did this" is genuinely part of a business fact's own meaning (e.g. an approval
decision), the owning module names its own explicit field (`decided_by_user_id`) rather than
reusing a generic, business-vocabulary-free slot — this keeps the distinction between "business
fact" and "dispatch metadata" honest rather than smuggling business meaning into the metadata
side. `schema_version` is **not** added to `DomainEvent` or `DomainEventContext` at all — see the
explicit decision in §13 (Integration Event / Outbox Boundary) for why in-process domain events
do not need one.

### 6. Event Recording Decision

**Decision:** aggregates record their own domain events (Option A) as the default for a genuine
aggregate state transition. This is **not** a mandate to add `RecordsDomainEvents` to every
Platform entity or service. Explicit criteria:

| Situation | Recording model |
|---|---|
| An aggregate's own invariant/state transition (a mutation whose meaning is intrinsic to that aggregate — `Task.complete()`, `Organization.rename()`) | **Aggregate-recorded** — `RecordsDomainEvents` mixin, `_record_event(...)` inside the mutating method |
| An application-orchestration fact with no single owning aggregate (a bulk import summary, a cross-service reconciliation result) | **Application-authored** — the service constructs the `DomainEvent` directly and hands it to `uow.record_event(event)` (§10, a small, explicit escape hatch alongside aggregate-based collection) |
| A view refresh | **Never a `DomainEvent`** — this is exclusively `ViewInvalidationHint` territory, produced downstream of a real `DomainEvent` (or, only during the legacy-bridge window, directly from a compatibility adapter — never a new source of truth) |

```python
# src/core/shared/events/aggregate_events.py
class RecordsDomainEvents:
    _pending_domain_events: list[DomainEvent]

    def _ensure_event_storage(self) -> None:
        if not hasattr(self, "_pending_domain_events"):
            self._pending_domain_events = []

    def _record_event(self, event: DomainEvent) -> None:
        self._ensure_event_storage()
        self._pending_domain_events.append(event)

    def domain_events(self) -> tuple[DomainEvent, ...]:
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
        self._record_event(TaskReassigned(
            tenant_id=self.tenant_id,
            organization_id=self.organization_id,
            task_id=self.id, project_id=self.project_id,
            previous_assignee_id=previous_assignee_id,
            new_assignee_id=new_assignee_id,
            occurred_at=clock.now(),
        ))
```

**Rationale:** matches the criteria this ADR's original author preferred, made concrete rather
than aspirational — "true aggregate business state transitions should record their own domain
events," bounded by an explicit list of what counts as one. **Alternatives considered:** (b)
application services always hand-construct events, aggregates never record anything — rejected as
the sole model, since it lets a caller forget to construct an event with no structural safeguard
(exactly the class of bug `_record_event`'s no-op-on-no-change guard prevents); accepted as a
*secondary*, explicitly-scoped path for the orchestration case above, where there genuinely is no
single aggregate whose method could have recorded it. **The Platform implementation plan (§28,
Phase P5) lists the specific Platform capabilities to assess against this criteria table** — this
ADR does not pre-judge which Platform capabilities get aggregate-recorded events versus
orchestration-authored ones; that is a per-capability discovery task, not a blanket rule.

### 7. Transactional Dispatch

Unchanged from earlier revisions — validated, not altered, by the audit. Transactional handlers
run *before* commit, in the same unit of work as the aggregate change that raised the event (the
motivating example remains `TaskCompleted` → update project progress, committed together or not
at all). A transactional handler failure rolls back the whole transaction (FAIL_FAST). The
dispatcher itself is **stateless** — no queue, no `_dispatching` flag — since the `UnitOfWork`
itself already implements breadth-first, multi-round draining (§10):

```python
# src/infra/events/in_process_transactional_event_dispatcher.py
class InProcessTransactionalEventDispatcher(TransactionalEventDispatcher, TransactionalEventSubscriber):
    def __init__(self) -> None:
        self._handlers: dict[type, list[TransactionalEventHandler]] = {}
        self._lock = RLock()

    def dispatch(self, event: DomainEvent, uow: UnitOfWork) -> None:
        with self._lock:
            handlers = tuple(self._handlers.get(type(event), ()))
        for handler in handlers:
            handler(event, uow)  # FAIL_FAST — propagates straight out
```

Handler shape is a named `Protocol`, never an inline `Callable`, so the shape can't drift between
the bus's registry, registration functions, and any future adapter:

```python
class TransactionalEventHandler(Protocol[E]):
    def __call__(self, event: E, uow: UnitOfWork) -> None: ...
```

A transactional handler is typed against a *module-specific* `UnitOfWork` extension exposing
repository *contracts* (`uow.projects: ProjectRepository`), never a concrete SQLAlchemy class or a
raw `Session` — this is what lets `handle_task_completed` update `Project` in the same transaction
without importing infrastructure:

```python
def handle_task_completed(event: TaskCompleted, uow: ProjectManagementUnitOfWork) -> None:
    project = uow.projects.get(event.project_id)  # auto-registers `project` with the UoW
    project.record_progress_from_task_completion(event.task_id)
    uow.projects.update(project)  # persist explicitly — commit() alone does not (§10)
```

### 8. Post-Commit Publication

Queued, race-fixed, handler-snapshot-safe — unchanged in mechanics from earlier revisions, now
explicitly carrying `DomainEventContext` (§5):

```python
class PostCommitEventHandler(Protocol[E]):
    def __call__(self, event: E, context: DomainEventContext) -> None: ...

class PostCommitEventPublisher(Protocol):
    def publish(self, event: DomainEvent, context: DomainEventContext) -> None: ...
```

ISOLATE_AND_CONTINUE: one handler's exception is caught, logged (with `event type`, `handler
name`, `tenant_id`, `organization_id`, `correlation_id` — see §18), and does not block the next
handler or the next event. The queue/`_dispatching`-flip race fix and lock-held handler-registry
snapshot from earlier revisions are unchanged. **Dispatch ordering is explicitly breadth-first —
a deliberate design choice, not a preservation of the legacy `Signal` primitive's accidental
depth-first-under-recursion behavior** (the audit confirmed today's `Signal.emit()` lets a
re-entrant nested `emit()` run to full completion before the outer loop's next subscriber runs;
this design intentionally does not carry that accident forward).

### 9. UnitOfWork Semantics

**Decision:** "Unit of Work" means exactly one thing in this codebase going forward: **one
physical database transaction, owning one fresh `Session`, owning commit/rollback, owning the
event collection/dispatch lifecycle for that transaction.**

```python
class UnitOfWork(Protocol):
    def __enter__(self) -> "UnitOfWork": ...
    def __exit__(self, exc_type, exc_val, exc_tb) -> None: ...
    def register_touched(self, aggregate: RecordsDomainEvents) -> None: ...
    def record_event(self, event: DomainEvent) -> None: ...  # NEW — §6's orchestration escape hatch
    def tracked_aggregates(self) -> tuple[RecordsDomainEvents, ...]: ...
    def commit(self) -> None: ...
    context: DomainEventContext  # NEW — §5

class UnitOfWorkFactory(Protocol):
    def create(self, *, context: DomainEventContext) -> UnitOfWork: ...
```

No `session` field, no repository accessors on the shared protocol — a module-specific extension
(`ProjectManagementUnitOfWork(UnitOfWork, Protocol)`) adds its own typed repository accessors.
`tracked_aggregates()` returns a `tuple`, keyed internally by `id(aggregate)` in a dict, not a
`set` — aggregates are not guaranteed hashable, and identity (not equality) is the correct
dedup semantics. `__exit__` never auto-commits on clean exit; `commit()` is always explicit,
since that is where event coordination happens.

**Rationale for the semantic reservation:** the audit found `ApprovalService`'s existing
"unit of work" is a *logical* convention (only one method calls `.commit()`) enforced over the
*same shared, process-lifetime `Session`* every other Platform service uses — not a physically
isolated transaction. Two different guarantees sharing one name is a real risk once both exist
side by side; reserving "UnitOfWork" for the stronger, physical guarantee and requiring anything
weaker to use different vocabulary (§26) removes the ambiguity going forward.

Every repository exposes an explicit `update(aggregate)`/`add(aggregate)`, and every service or
handler calls it before `uow.commit()` — confirmed necessary by this codebase's own
`SqlAlchemyTaskRepository`, whose `Task.update()` persists through a raw, version-checked
`UPDATE` that bypasses ORM attribute tracking entirely, so nothing would flush a mutated `Task`
without an explicit call. This rule holds regardless of which of this codebase's two confirmed
persistence mechanisms (raw optimistic-concurrency update vs. tracked-ORM-attribute mutation) a
given repository happens to use.

A rolled-back unit of work discards every aggregate instance associated with it — pending events
may remain for inspection, but are never automatically replayed, and the instances are never
reused in a later unit of work (their in-memory state may not match what was actually persisted).
A retry means starting a genuinely new unit of work that re-loads fresh state.

### 10. Dynamic Aggregate Discovery, Ordering, and Cycle Handling

Because §6 adopts aggregate-recorded events as the default, the exact motivating scenario earlier
revisions worried about is real: a transactional handler for `TaskCompleted` loads or creates a
`Project` aggregate that itself records `ProjectProgressChanged` — if `Project` weren't
discovered, that event would be silently dropped. **Dynamic re-collection is therefore adopted,
not optional:**

```text
UoW registers every touched aggregate as it's loaded/added (uow.<repo>.get()/add() call
    register_touched automatically; a handler using another of the UoW's own repository
    accessors gets this for free — manual register_touched is only needed for an aggregate
    built or mutated without going through one of the UoW's own accessors)
        ↓
UoW collects pending events from every currently-tracked aggregate, plus anything
    staged via uow.record_event(...) (§6's orchestration path)
        ↓
UoW dispatches those events through transactional_event_dispatcher.dispatch(event, uow)
        ↓
UoW re-collects — a transactional handler may have touched MORE aggregates or recorded
    MORE events; repeat until a round produces nothing new, or MAX_DISPATCH_ROUNDS is hit
    (fail loudly — a real cycle is a bug, not a hang)
```

Deduplication is by object identity (`id(event)`), an explicit interim decision — a future need
for events to survive process boundaries with a stable identity would revisit this, not before.
`MAX_DISPATCH_ROUNDS` exists specifically because dynamic re-collection is real under the adopted
event-recording model; if a future revision ever reverted to hand-construction-only with no
re-collection, this guard would have nothing to guard against and should be removed rather than
kept as unused ceremony.

### 11. Integration Event / Outbox Boundary

**Preserved exactly, restated unambiguously per the audit's explicit request.** The transaction
boundary between in-process dispatch and durable integration publication is:

```text
Command
    ↓
Application Service
    ↓
Aggregate → records DomainEvent
    ↓
TransactionalEventDispatcher.dispatch(event, uow)
    ├── transactional business handlers (FAIL_FAST, same transaction)
    │
    └── integration-event mapping (selects events that warrant a durable fact,
          builds an IntegrationEventEnvelope, calls Outbox.add(...) — still
          inside the same open transaction, never after commit)
    ↓
uow.commit()  (staged repository updates + outbox rows written and committed together)
    ↓
PostCommitEventPublisher.publish(event, context)
    ├── ViewInvalidation handler
    ├── local, best-effort projection handlers
    └── (never a second, later attempt at outbox mapping — that already happened above)
    ↓
(separately, asynchronously) Outbox Worker → IntegrationEventEnvelope → consumer inbox
```

The outbox write is **never** a reaction to a published in-process event, and is **never**
performed from `PostCommitEventPublisher` — it happens during the transactional phase,
constructed from the same `event`/`uow` the transactional dispatcher already has, so a rolled-back
transaction never produces an outbox row. ADR-PF-011 remains fully authoritative for everything
downstream of the outbox row itself (delivery, retry, dead-letter, inbox dedup, semantic
conflict quarantine) — none of that is touched or re-decided here.

**`schema_version` is deliberately not added to in-process `DomainEvent`s.** *Rationale:*
`IntegrationEventEnvelope`'s `schema_version` exists to let a durable message survive a consumer
reading it at a different code version than the producer — a real concern for messages that
outlive one deploy and cross process boundaries. An in-process `DomainEvent` is constructed and
fully consumed within one call stack, one process, one deploy; there is no reader that could ever
be running different code than the writer. *Convention adopted instead:* domain-event field
changes are additive-only by default; a rename or removal is called out in the event class's own
docstring with a brief note on why, and any handler still relying on the old shape is updated in
the same change — the same lightweight discipline the audit's PLAT-VER-001 finding recommended,
without inventing a version field with no reader to check it. *Alternatives considered:* copying
`schema_version: int` onto every `DomainEvent` "for consistency with the integration envelope" —
rejected as importing a durable-messaging concern into a mechanism that never crosses a durable
boundary; ADR-PF-011's own mapping step is exactly where a domain-event-shaped fact picks up a
`schema_version` for the first time, and that is the correct place for it to happen.

### 12. View Invalidation

A transport-independent hint that a read model is stale — never a business fact, never routed
through the same contract as a `DomainEvent`.

```python
@dataclass(frozen=True, slots=True, kw_only=True)
class ViewInvalidationHint:
    tenant_id: str
    organization_id: str | None   # NEW — required to be explicit; None means tenant-wide
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None

@dataclass(frozen=True, slots=True, kw_only=True)
class PlatformViewInvalidationHint:
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None
    # deliberately no tenant_id or organization_id — this type exists ONLY for hints with
    # no tenant to scope them to; a hint that has a tenant, org-scoped or not, uses
    # ViewInvalidationHint instead, never this type with fabricated values.
```

**Subscription is structurally enforced at both the tenant boundary and the organization
boundary — five distinct, non-overlapping entry points, mirroring how this ADR already treated
tenant isolation as a structural (not binder-discipline) guarantee:**

```python
class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def notify_platform_wide(self, hint: PlatformViewInvalidationHint) -> None: ...

    def subscribe(
        self, handler: ViewInvalidationHandler[ViewInvalidationHint],
        *, tenant_id: str, organization_id: str,
    ) -> Subscription: ...
    """Exact match: this org's views only. A hint for a different organization in the
    same tenant is never delivered here."""

    def subscribe_tenant_wide(
        self, handler: ViewInvalidationHandler[ViewInvalidationHint], *, tenant_id: str,
    ) -> Subscription: ...
    """Only hints with organization_id=None (genuinely tenant-wide facts). An org-scoped
    hint, even for an organization in this same tenant, is never delivered here."""

    def subscribe_across_organizations(
        self, handler: ViewInvalidationHandler[ViewInvalidationHint], *, tenant_id: str,
    ) -> Subscription: ...
    """Deliberate breadth: every hint for this tenant, tenant-wide or any organization's.
    For genuine tenant-admin/organization-selector screens — a searchable, auditable
    opt-in, never the default."""

    def subscribe_across_tenants(
        self, handler: ViewInvalidationHandler[ViewInvalidationHint],
    ) -> Subscription: ...
    """Unchanged from earlier revisions — every tenant's hints, for a genuinely
    cross-tenant platform-admin consumer. Not to be conflated with
    subscribe_across_organizations, which is still scoped to one tenant."""

    def subscribe_to_platform_wide(
        self, handler: ViewInvalidationHandler[PlatformViewInvalidationHint],
    ) -> Subscription: ...
```

**Routing, stated explicitly (this is what the implementation plan's tenant/organization test
matrix, §29, directly exercises):**

- `notify(hint)` where `hint.organization_id is not None` → delivered to exact-match `subscribe`
  subscribers for that `(tenant_id, organization_id)`, and to `subscribe_across_organizations`
  subscribers for that `tenant_id`. **Never** to `subscribe_tenant_wide` subscribers (wrong shape
  of fact for that contract) and **never** across tenants (unless via `subscribe_across_tenants`).
- `notify(hint)` where `hint.organization_id is None` (tenant-wide fact) → delivered to
  `subscribe_tenant_wide` subscribers for that `tenant_id`, and to `subscribe_across_organizations`
  subscribers for that `tenant_id` (breadth naturally includes tenant-wide facts). **Never** to an
  exact-match `subscribe(tenant_id, organization_id=...)` subscriber — a specific organization's
  view must not refresh on a fact that isn't about that organization.
- `subscribe_across_tenants` subscribers receive every `notify(...)` call regardless of tenant or
  organization — unchanged, rare, auditable.
- `notify_platform_wide(hint)` only ever reaches `subscribe_to_platform_wide` subscribers.

`scope_code`/`entity_type` filtering remains a binder-level convenience closure, exactly as
before — only the tenant and organization dimensions are genuine security/correctness boundaries
enforced by the channel itself; everything else is business-convenience filtering, unchanged from
this ADR's original reasoning.

Two independent failure-isolation responsibilities, unchanged from earlier revisions:
`post_commit_event_bus` isolates failures between event *adapters*; `ViewInvalidationChannel.notify()`
isolates failures between UI *subscribers* — a second, independent catch-log-continue boundary
inside the channel itself.

### 13. Desktop Adapter Boundary

```text
DomainEvent → application handler → ViewInvalidationHint → ViewInvalidationChannel → adapter
```

Today: `ViewInvalidationChannel → Qt adapter (marshals to the Qt main thread) → QML`. Neither QML
nor any future web client ever consumes a `DomainEvent` directly — confirmed today's controllers
already only ever decide "should I refresh," never inspect business content, so this is a
low-regret boundary to formalize now, not a hypothetical constraint.

**Qt adapter consolidation scope, deliberately bounded.** The audit found three independently
duplicated `workspace_controller_base.py` implementations (Platform, `project_management`,
`inventory_procurement`) with two genuinely different refresh-scheduling algorithms. This ADR
centralizes only the reusable *invalidation* concern — subscription, tenant/organization matching,
disposal, refresh coalescing/scheduling, Qt-thread adaptation — into one shared component
(`qt_view_invalidation_channel.py`, §20). **This is explicitly not a QML controller-hierarchy
unification project**: the three controller bases' other responsibilities (loading/busy state,
lazy-load gating, unrelated per-family behavior) are untouched; each base delegates its
invalidation slice to the shared adapter instead of reimplementing it. The Platform
implementation plan (§28, Phase P6) scopes this precisely.

### 14. Future SaaS Boundary

Tomorrow: `ViewInvalidationChannel → a WebSocket/SSE adapter → web client`, built later, as a new
adapter beside the Qt one — never a reason to touch `DomainEvent`/`UnitOfWork`/dispatcher
contracts. **This ADR does not implement WebSockets, SSE, FastAPI, request-scoped tenant context,
or `contextvars` — that remains a separate, not-yet-made architecture decision** (§25, Explicit
Non-Goals). What this ADR *does* guarantee now, so that future decision isn't blocked: no
`DomainEvent`/`ViewInvalidationHint` contract designed here assumes one process serves one tenant,
or that one tenant has one organization — both assumptions are explicitly false for this product
and neither is baked into any type defined above.

The audit separately found that `TenantContextService`'s current ambient, mutable-session-object
tenant model would not safely generalize to a concurrent multi-request server unchanged. That is
a tenancy-architecture decision, out of scope here, and is recorded as an open dependency (§24)
for whoever eventually designs the web adapter — not something this ADR resolves or should be
read as having resolved.

### 15. Dependency Injection / Composition

No bare module-level singleton (`domain_events = DomainEvents()` is the anti-pattern being
replaced, not a template). `TransactionalEventDispatcher`, `PostCommitEventPublisher`,
`ViewInvalidationChannel`, and every `UnitOfWorkFactory` are constructed inside
`src/infra/composition/{app_container.py, platform_registry.py}`, receiving their collaborators
as explicit constructor parameters — the same convention `ApprovalService` and `NotificationService`
already use correctly today. Module-level post-commit handler registrations are collected into a
`SubscriptionRegistry` owned by the composition root and disposed on shutdown; QML controller
subscriptions to `ViewInvalidationChannel` are owned and disposed by the controller itself.

### 16. Failure Semantics

| Phase | Handler raises → behavior |
|---|---|
| Transactional dispatch | Propagates immediately — no try/except inside the dispatcher. The `UnitOfWork`'s draining loop lets this abort the whole transaction (FAIL_FAST). |
| Post-commit publication | Caught, logged with full context (§18), never re-raised. Business transaction stays committed. Remaining handlers for that event, and remaining events, still run (ISOLATE_AND_CONTINUE). |
| `ViewInvalidationChannel.notify()` fan-out to subscribers | Caught and logged per-subscriber, independently of the post-commit bus's own isolation — one bad controller callback never blocks another controller's refresh. |

This matches the isolate-and-continue behavior already de facto present in this codebase's three
independent hand-rolled try/except-log sites (`ApprovalService`, both `Resource*UnitOfWork`
classes) — this ADR formalizes it as a structural guarantee of the shared bus, closing the gap
the audit found: today, any *new* emit call site that doesn't hand-wrap itself silently regresses
to fail-fast, because the underlying `Signal` primitive only catches two specific Qt-lifecycle
exception types.

### 17. Rollback Safety

Unchanged from earlier revisions: a rolled-back unit of work discards every associated aggregate
instance; pending events may remain for debugging but are never automatically replayed; a retry
means a genuinely new unit of work re-loading fresh state, never reusing the old in-memory
objects.

### 18. Observability

Kept deliberately proportionate — not a telemetry-platform project. At minimum, every dispatch
failure (transactional or post-commit) is logged with enough structured context to answer: which
event type, which handler, which `tenant_id`, which `organization_id`, which `correlation_id`
(from `DomainEventContext`), and whether it succeeded or failed. No metrics/tracing rollout
(Prometheus, OpenTelemetry, or otherwise) is introduced by this ADR — none exists elsewhere in
this codebase today, and inventing one here would be scope well beyond what this migration needs
to be diagnosable in production. If a future, separate observability initiative adds
metrics/tracing platform-wide, this mechanism's dispatch points are exactly where such
instrumentation would attach — nothing in this design precludes it later.

### 19. Naming

The audit found "event" already names four unrelated things in shipped code, and "Signal" names
two unrelated things in the same file. Resolved:

| Term | Decision | Blocking? |
|---|---|---|
| `DomainEvent`, `RecordsDomainEvents`, `TransactionalEventDispatcher`, `PostCommitEventPublisher`, `ViewInvalidationHint`/`Channel`, `UnitOfWork`/`UnitOfWorkFactory` | Adopt as specified above | New code only — no rename of anything existing |
| `Signal[T]` (`src/core/shared/events/signal.py`) | **Rename to `CallbackSignal`** in a later phase (§28, Phase P7/P8) — resolves the same-file collision with `PySide6.QtCore.Signal` that today forces an import alias | **Not blocking** for Phase 0-P4 — scheduled as legacy-bridge cleanup once callers have migrated off it |
| `PlatformEvent` | Document clearly as an **audit/governance record, not a Domain Event** (§1's taxonomy table). A future rename to `PlatformAuditEntry` is recommended | **DEFERRED — NOT BLOCKING.** It has exactly one real construction site (`tenant_admin_service.py`), is never dispatched or subscribed to, and its collision with "Domain Event" vocabulary is documentation-level, not functional. Renaming it is not a prerequisite for anything in this ADR. |
| `ApprovalService`'s existing pattern | Do **not** call it a "Unit of Work" going forward (§9) — call it a transaction convention, pending its own migration (§26) | N/A — naming clarification only |

`CallbackSignal` was chosen over `Observable` (implies reactive-programming operators — `map`/
`filter`/etc. — this primitive has none, and the name would overpromise) and `EventEmitter`
(reintroduces "Event" into the name of something that is not a `DomainEvent`, precisely the
collision being resolved). The generic primitive is kept, not deleted, once
`PostCommitEventPublisher`/`ViewInvalidationChannel` exist — it still has legitimate, narrower
uses (simple property-change notification with no domain-event semantics) and 66+ existing
callers that migrate gradually, not atomically.

### 20. Repository Locations

```text
src/core/shared/events/
  domain_event.py                  # DomainEvent marker protocol
  domain_event_context.py          # DomainEventContext (§5)
  aggregate_events.py              # RecordsDomainEvents mixin
  domain_event_publisher.py        # TransactionalEventDispatcher + PostCommitEventPublisher (protocols)
  domain_event_subscriber.py       # handler-shape + subscriber protocols
  subscription.py                  # Subscription (dispose) protocol
  view_invalidation.py             # ViewInvalidationHint + PlatformViewInvalidationHint + channel contract
  signal.py                        # existing generic primitive — class renamed to CallbackSignal in
                                    #   a later phase (§19), not during initial contract work

src/core/shared/persistence/
  unit_of_work.py                  # UnitOfWork + UnitOfWorkFactory protocols (contract only)

src/core/shared/time/
  clock.py                         # Clock protocol — general-purpose, not events-specific

src/infra/events/
  in_process_transactional_event_dispatcher.py
  in_process_post_commit_event_bus.py
  in_process_view_invalidation_channel.py

src/infra/time/
  system_clock.py

src/infra/persistence/db/
  unit_of_work.py                  # RECLAIMED from dead session_scope() (0 callers) —
                                    #   SqlAlchemyUnitOfWorkBase, module-agnostic parts only

src/core/platform/infrastructure/persistence/
  unit_of_work.py                  # SqlAlchemyPlatformUnitOfWork(SqlAlchemyUnitOfWorkBase) —
                                    #   Platform's own thin subclass, added in Phase P4

src/core/platform/domain/<capability>/
  events.py                        # NEW, per Platform capability, only if/when that capability
                                    #   adopts typed events — explicitly NOT under the existing,
                                    #   already-occupied platform/domain/events/ path (§1's audit
                                    #   naming collision)

src/core/modules/<module>/
  domain/events.py                 # unchanged convention — module-owned
  contracts/unit_of_work.py        # unchanged convention
  infrastructure/persistence/unit_of_work.py   # unchanged convention

src/ui_qml/infrastructure/events/
  qt_view_invalidation_channel.py  # the ONE shared Qt adapter (§13) — consolidates, does not
                                    #   duplicate, the three existing controller bases' subscribe/
                                    #   dispose/scheduling logic
```

**Explicitly rejected:** module-specific business events living under Platform
(`platform/events/project_management_events.py`-shaped paths) — Platform never owns another
module's business vocabulary. **Also explicitly rejected:** a *new* Platform capability's typed
events landing in the *existing* `platform/domain/events/` package — that path is already
occupied by the unrelated `PlatformEvent`/`Notification` concepts; deepening that collision would
repeat the exact naming mistake this revision is correcting.

### 21. Architecture Guardrails

The audit found real AST-based import-boundary tests already exist and work
(`src/tests/architecture/test_qml_architecture_guardrails_layers.py`,
`test_pm_inventory_module_boundary.py`) — this ADR does **not** introduce a new enforcement
framework. It adds **one** test using the same technique: `src/core/platform/{domain,application}/`
must not import `src.core.modules.*`.

**Governed exceptions, explicit and auditable, not silent:**
- `calendar_assignment_service.py`'s import of `project_management` domain types is governed by
  [ADR-004](ADR-004-calendar-assignment-split-ownership.md) — allowlisted with that citation.
- `SqlAlchemyApprovalRepository`'s import of `ProjectORM` has **no governing ADR** — see §22 for
  its classification. It is allowlisted *temporarily*, with an explicit `# TODO` citing this ADR
  revision and stating no new exception may be added without an equivalent governing decision.

Any future addition to the exception list requires a citation to an accepted ADR — an
un-cited addition fails review, not just the test.

### 22. Existing Platform → Business-Module Layering Violation

`SqlAlchemyApprovalRepository` imports and joins against `project_management`'s `ProjectORM`
directly, with no governing ADR. **Classification: can remain as separately tracked architectural
debt; not a blocker for this ADR's implementation, and not to be silently fixed as a side effect
of it.** The eventual fix is a project-scoping contract Platform can depend on instead of the
concrete ORM — out of scope here. It is allowlisted in the new guardrail test (§21) with an
explicit citation back to this section, so it remains visible rather than quietly permanent.

### 23. Legacy Compatibility

| Mechanism | Disposition |
|---|---|
| `domain_events` singleton / `Signal` / `DomainChangeEvent` | Bridge incrementally, module/capability by module/capability, per the execution plan; retire once every consumer has migrated |
| `admin_console/domain_event_binder.py` | Already self-scheduled for removal ("phase R2" per its own docstring) — this migration's Phase P6/P7 (implementation plan) absorbs and completes that already-planned removal, rather than leaving it as a separate, uncoordinated cleanup |
| Three `workspace_controller_base.py` copies | Generalize the invalidation slice into one shared adapter (§13); do not bridge each of the three separately, and do not unify the rest of their responsibilities |
| `ApprovalService`'s existing transaction convention | **Adapt** (§26) — migrate onto the canonical `UnitOfWork` in Phase P4, not bridged indefinitely and not left permanently distinct |
| `project_management`'s `Resource*UnitOfWork` (module-owned, cited for comparison only) | Out of this ADR's Platform-scoped decision — resolved when `project_management`'s own module migration phase runs |
| `PlatformEvent` | Kept as-is; rename deferred, non-blocking (§19) |
| `NotificationService`/`Notification` | Kept as-is; unrelated to this migration |
| `IntegrationEventEnvelope`/outbox-inbox (ADR-PF-011) | Kept as-is; unrelated mechanism, already correct |
| Dead `session_scope()` | Reclaimed (§20) — zero callers, no migration cost |

No compatibility facades that outlive their own migration phase, and no straddling: per this
codebase's existing hard rule (also stated in `docs/repo_structure_plan/EXECUTION_SPEC.md`), a
command-side service migrated in a given phase stops reading/writing through its old path for the
operations that phase covers.

### 24. Related Decisions

**[ADR-PF-008](ADR-PF-008-approval-unit-of-work.md) — Approval Unit of Work.** Decision:
**ADAPT.** `ApprovalService`'s existing discipline (outer operation owns commit; handlers stage
only; post-commit reactions run after a successful commit, individually isolated from failure) is
philosophically identical to what this ADR formalizes generically. It is migrated onto the
canonical `UnitOfWork` in the Platform implementation plan's Phase P4 — not adopted for free (it
currently shares the single process-lifetime `Session` with every other Platform service, not a
fresh per-transaction one, so real migration work is required), not bridged indefinitely, and not
left permanently distinct (which would leave a second, competing meaning of "unit of work" in
Platform's own code, exactly the ambiguity §9 exists to remove). *Alternatives considered:*
ADOPT wholesale (rejected — ignores the real session-sharing difference that must actually
change); BRIDGE indefinitely (rejected — leaves two live conventions past this migration's own
close, violating this codebase's no-straddling rule); PERMANENTLY KEEP DISTINCT (rejected — the
two mechanisms solve the identical problem; keeping them separate forever is exactly the
"competing convention" outcome this ADR exists to prevent).

**[ADR-PF-011](ADR-PF-011-durable-integration-outbox-inbox.md) — Durable Integration Outbox and
Inbox.** Decision: **preserved unchanged**, boundary restated unambiguously in §13. No merge, no
shared class hierarchy, no change to its retry/dead-letter/dedup/quarantine semantics.

**[ADR-004](ADR-004-calendar-assignment-split-ownership.md) — Calendar Assignment Split
Ownership.** Cited as the governing decision for one of the two Platform→module import findings
in §21/§22; not otherwise affected by this ADR.

### 25. Explicit Non-Goals

This ADR does **not**:

- implement FastAPI, WebSockets, SSE, request-scoped tenant context, or `contextvars` — that is a
  separate, not-yet-made tenancy/transport architecture decision (§14);
- assume one process serves one tenant, or one tenant has one organization — both are explicitly
  false and neither assumption is present in any contract defined here (§3);
- merge Domain Events, Integration Events, Notifications, or Audit Records into one universal bus
  (§1, §27);
- fix the pre-existing `SqlAlchemyApprovalRepository → ProjectORM` layering violation as a side
  effect of this migration (§22);
- unify the three `workspace_controller_base.py` classes' non-invalidation responsibilities into
  one QML controller hierarchy (§13);
- rename `PlatformEvent` as a blocking prerequisite (§19);
- introduce a metrics/tracing platform (§18);
- change ADR-PF-011's durable delivery semantics in any way (§13, §24).

## Alternatives Rejected

All alternatives rejected in earlier revisions remain rejected (recursive/depth-first re-entrant
dispatch; polymorphic/supertype event subscription; application services holding a
`TransactionalEventDispatcher` directly; a frozen up-front "touched aggregates" list; reusing a
rolled-back aggregate instance; one publisher/subscriber pair for both transactional and
post-commit dispatch; a concrete repository/`Session` reachable from a `UnitOfWork`-typed
handler; a `UnitOfWorkFactory` closing over an already-created process-lifetime `Session`; a
queued, stateful transactional bus sharing one `_dispatching` flag across concurrent
transactions). Added this revision:

- **One universal event bus for Domain Events, Integration Events, Notifications, and Audit
  Records.** Rejected — the audit found these are already five genuinely separate mechanisms
  with different durability, transport, and tenancy requirements; collapsing them would not
  simplify anything and would break ADR-PF-011's durability guarantees the moment a "convenient"
  in-process shortcut got taken.
- **A nested `EventScope`/`TenantScope`/`OrganizationScope` type hierarchy.** Rejected per §3 —
  unnecessary indirection over a distinction two plain fields already express, inconsistent with
  the one proven precedent (`IntegrationEventEnvelope`) this codebase already has.
- **`schema_version` on every in-process `DomainEvent`.** Rejected per §11 — imports a
  durable-messaging concern into a mechanism that never crosses a durable boundary.
- **Correlation/causation IDs directly on every `DomainEvent`.** Rejected per §5 — pollutes
  business vocabulary with per-transaction metadata; a `DomainEventContext` owned by the
  `UnitOfWork` is the correct home.
- **Treating `ApprovalService`'s existing pattern as already "the" Unit of Work.** Rejected per
  §9/§24 — it is a logical convention over a shared session, not the physical, per-transaction
  guarantee this ADR reserves the name for; conflating the two was the original gap the audit
  found.
- **Fixing the `SqlAlchemyApprovalRepository → ProjectORM` violation, or unifying the three
  controller bases wholesale, as part of this migration.** Rejected per §22/§13/§25 — genuine,
  real problems, but out of this ADR's scope; fixing them here would be uncontrolled scope creep
  into a migration that already has enough surface area.

## Consequences

- Every module (and, per capability, Platform) gains `domain/events.py`, an
  `application/event_handlers/{transactional,view_invalidation}.py` pair, and module/capability-
  owned invalidation-hint constants.
- Every tenant-owned `DomainEvent` and `ViewInvalidationHint` now carries an explicit
  `organization_id: str | None`, not just `tenant_id` — a real, structural change from this ADR's
  earlier revisions, driven directly by this product's actual tenant/organization data model.
- `ViewInvalidationChannel` gains five distinct subscription entry points instead of the three
  earlier revisions specified, to make the organization dimension a structural boundary alongside
  the tenant dimension.
- `PostCommitEventHandler`'s signature gains an explicit `context: DomainEventContext` parameter
  — a deliberate, documented change from `(event) -> None` to `(event, context) -> None`.
- `UnitOfWork` gains `record_event(event)` (the orchestration-fact escape hatch, §6) and a
  `context: DomainEventContext` property (§5), alongside the dynamic aggregate-tracking machinery
  already specified in earlier revisions.
- `ApprovalService` has a named, scoped migration destination (Phase P4) rather than being
  ignored by this design.
- One new architecture-enforcement test is added (§21), with one explicitly-cited, temporary
  exception for the pre-existing, separately-tracked `SqlAlchemyApprovalRepository` violation.
- `Signal`'s eventual rename to `CallbackSignal` is scheduled, not immediate — no production code
  is renamed by this ADR itself.

## Migration Impact

See [ADR-005-execution-plan.md](ADR-005-execution-plan.md) for cross-Platform-and-module
sequencing (which now inserts an explicit Platform-foundation phase before any business module
migrates, and strikes the dead `maintenance`-module phase), and
[`platform_domain_event_implementation_plan.md`](../platform_modernization/domain_event/platform_domain_event_implementation_plan.md)
for the exact, file-by-file Platform how-to.

## Test Impact

In addition to every test already specified in earlier revisions (transactional handler updating
a different aggregate within the same open transaction; post-commit handler signature genuinely
cannot accept `uow`; no-op mutations record nothing; a transactional handler exception aborts the
transaction while a post-commit one does not; `register_touched` identity-map semantics;
subscription disposal at both lifetimes; rollback discards associated instances without permitting
reuse; a cyclical transactional setup fails loudly at `MAX_DISPATCH_ROUNDS` rather than hanging;
concurrent `publish()` calls don't corrupt the post-commit bus; the empty-queue/`_dispatching`-flip
race is closed; handler-registry snapshots are lock-consistent with concurrent subscribe/dispose):

- A `ViewInvalidationHint` for `(Tenant A, Organization A1)` reaches an exact-match
  `subscribe(tenant_id="A", organization_id="A1")` subscriber and a
  `subscribe_across_organizations(tenant_id="A")` subscriber, but **not** a
  `subscribe(tenant_id="A", organization_id="A2")` subscriber, **not** a
  `subscribe_tenant_wide(tenant_id="A")` subscriber, and **not** any `Tenant B` subscriber.
- A tenant-wide hint (`organization_id=None`) for Tenant A reaches `subscribe_tenant_wide` and
  `subscribe_across_organizations` subscribers for Tenant A, but **not** any exact-match
  `subscribe(tenant_id="A", organization_id=...)` subscriber.
- `subscribe_across_tenants` receives hints from every tenant; `subscribe_to_platform_wide`
  receives only `PlatformViewInvalidationHint`s and never a tenant-scoped `ViewInvalidationHint`.
- An organization-scoped `DomainEvent` constructed with `organization_id=None` where the event's
  own type declares it required is a construction-time type error, not a runtime surprise.
- A transactional handler loading and mutating a second aggregate that itself records a new event
  causes that event to be discovered and dispatched in a subsequent round (§10), directly tested.
- `PostCommitEventHandler`'s context parameter carries the same `correlation_id` the triggering
  `UnitOfWork` was constructed with.
- Integration-event mapping (where a module opts an event into it) happens strictly before
  `uow.commit()`, and a rolled-back transaction produces zero outbox rows for that event.

## Implementation Evidence

None yet — this ADR is a design proposal, not yet implemented. See the Platform implementation
plan for the concrete, sequenced how-to once this revision is reviewed and approved.

## Open Items Before This Can Move to Accepted

Everything resolved across rounds 1-5 remains resolved (see Revision History). This revision
(round 6) resolves the five gaps listed at the top of this document. **Still genuinely open,
narrower than before:**

1. Which specific call sites can publish from a non-Qt-main thread (needed to finalize the Qt
   adapter's marshaling behavior) — unchanged open item from earlier revisions.
2. Whether post-commit handler code itself is safe to run off the Qt main thread — unchanged open
   item from earlier revisions.
3. Confirmation, per module/capability phase, of which session-staleness mitigation is actually
   chosen (migrate the read path too vs. an explicit, called-out `expire_all()` bridge) — a
   per-phase decision, not settled here.
4. The tenant-context concurrency model for a future concurrent web server (§14) — explicitly
   **DEFERRED — NOT BLOCKING** for this ADR's own implementation, since nothing here assumes an
   answer to it, but it must be resolved by a separate decision before any WebSocket/SSE adapter
   is designed.
5. The `platform/access/{domain,application}` vs. `platform/domain/security/authorization`
   relationship the audit flagged as unresolved — **DEFERRED — NOT BLOCKING** for this ADR, since
   neither package is where any new event/invalidation contract is placed.

All five should be resolved (1-3 before this ADR is marked Accepted; 4-5 before they become
load-bearing for whatever later work depends on them).
