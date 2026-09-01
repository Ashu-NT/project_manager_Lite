# ADR-005: Domain Events

- Status: accepted, Platform-scoped implementation complete through P8 (revision 9 — final
  canonicalization; see §26)
- Date: 2026-08-05, revised 2026-08-25 after a dedicated, evidence-based Platform-only
  architecture audit (`docs/platform_modernization/domain_event/platform_domain_event_audit.md`)
  found this design was not landing on the blank slate its earlier revisions assumed; revised
  again 2026-08-25 (same day) after a P4A pre-implementation investigation found §24's `TDeps`
  design, as originally specified, does not match how the real, production apply handlers work
  (Round 7); revised again 2026-08-25 (same day) after an explicit user decision that, since this
  application is pre-release with no backward-compatibility requirement, the P4-PRE prerequisite
  should converge the 8 approval-backed services directly onto session-parameterized participants
  rather than first building a temporary adapter on the legacy shared session (Round 8, and §24).
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
   exactly the transaction discipline §9 (UnitOfWork Semantics) describes, under a different
   name, at a different granularity, without this ADR ever mentioning it. See §24 (Related
   Decisions) and §9.
2. **The scope model was tenant-only.** This is wrong for this product: a tenant can and does
   contain multiple organizations, and nothing in the original design prevented an
   organization-A-scoped fact from reaching an organization-B-scoped subscriber inside the same
   tenant. See §3 (Scope / Tenant / Organization Semantics) and §12 (View Invalidation).
3. **Event metadata (correlation/causation) was left as an open question with no shape decided.**
   §8 (Event Metadata Decision) now resolves it, deliberately keeping it off the business-fact
   dataclasses themselves.
4. **Event recording (aggregate-records-its-own-events vs. hand-construction) was left as an
   explicit "revisit later" item in the decision matrix.** §6 (Event Recording Decision) now
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

**Round 7 (this revision)** is a response to a pre-implementation investigation performed before
Phase P4 (`ApprovalService` migration, per the Platform implementation plan) was allowed to begin
writing any code — per that plan's own instruction to stop and report rather than silently
redesign if current source conflicts with approved architecture. It does conflict, narrowly:

1. **§24's `TDeps` design assumed apply handlers receive raw *repository*-contract dependencies.**
   An exhaustive inventory of all 18 real, production `register_apply_handler`/
   `register_reject_handler` registrations (`src/infra/composition/project_registry.py`,
   `inventory_registry.py`) found every one calls into an already-constructed, long-lived PM/
   Inventory *application service*, never a bare repository, and every one of the 8 backing
   services holds a circular `approval_service=` constructor reference. §24 is revised below to
   resolve `TDeps` as a module-supplied *factory function* producing whatever collaborator (often
   the module's own existing service, freshly reconstructed against a supplied session) the
   handler actually needs — not a generic, repository-shaped dataclass resolved from a binder
   registry keyed by type.
2. **A new prerequisite phase is required before Phase P4 can migrate `ApprovalService` itself.**
   The revised `TDeps` mechanism requires each of the 8 backing services to become
   session-parameterizable first; this is real, non-trivial, per-service work, not something that
   can be folded silently into Phase P4. See the Execution Plan's revised Phase 2 sequencing.

**Round 8 (this revision, same day)** responds to an explicit user decision: this application is
pre-release, with no external users and no backward-compatibility requirement for the current
process-lifetime `Session` architecture. Round 7's prerequisite phase had been designed as four
steps specifically so a temporary adapter could prove parity on the *still-shared* session before
anything moved — caution appropriate for a live system, unnecessary here. Round 8 collapses that
into two direct steps (port the 8 services' approval-facing logic straight into standalone,
session-parameterized participants; then cut `ApprovalService` over) and, from a wider 30-service
PM/Inventory audit performed to size this correctly, explicitly confirms what stays out of scope
(the other ~22 services' full command surfaces, two more services with an identical but unrelated
`commit: bool` pattern, and the pre-existing `Resource*UnitOfWork` classes) and states plainly that
the process-lifetime `Session` cannot be removed from `app_container` until Execution Plan Phases 3
and 5 both close — this correction narrows *how* 2A-PRE converges the 8 services, it does not
widen *what* 2A-PRE covers. See §24.

**Round 9 (this revision) is the P8 closeout** — the Platform-scoped implementation (P0 through
P8 of `platform_domain_event_implementation_plan.md`) is now complete and this ADR is updated to
describe what was actually built, not merely what was planned. §26 (new) is the authoritative
implementation-status section. In summary: five capabilities reached genuinely typed
DomainEvent → ViewInvalidation → Qt adapter presentation (Module Entitlement, RoleBinding, Tenant
Membership, Approval, and Organization's own `create` transition only); the legacy
`domain_events`/`Signal`/`DomainChangeEvent` generic bridge described as a temporary migration aid
in §23 below was not merely bridged down — it was deleted entirely (P7A), followed by two rounds
of dead-signal deletion (P7B: zero-producer signals; P7C: zero-consumer signals, including their
producers). §23's own table is corrected in place rather than left describing a bridge that no
longer exists. Every other decision in this document (§1-§25) held as originally decided; none
were reversed during implementation.

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
  `session_scope()` (§20), and one call at process startup. This ADR's proposed per-transaction
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
revision explicitly rejects it as an alternative (see Alternatives Rejected, below).

| Concept | Meaning | Current mechanism | This ADR's disposition |
|---|---|---|---|
| **Domain Event** | A business fact that occurred in the domain (`TaskCompleted`, `PurchaseOrderApproved`, `EmployeeAssigned`) | None exist under Platform; module-owned examples exist ad hoc (`ResourceMasterChanged`) | **New** — §4 defines the contract |
| **View Invalidation** | A transport-independent hint that a read model is stale and should be re-read — *not* a business fact | The legacy `domain_events`/`Signal` mechanism, functioning as this despite its name | **New, formalized** — §12 |
| **Integration Event** | A durable, cross-process, schema-versioned message governed by ADR-PF-011 | `IntegrationEventEnvelope` + outbox/inbox — mature, correct, already separate | **Unchanged** — §11 preserves the boundary |
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

**Revised this pass**, after a targeted review of the representation question specifically (see
§12 for why the answer differs between `DomainEvent` and `ViewInvalidationHint` — it did not, on
reflection, deserve one uniform answer).

**Decision — `DomainEvent` keeps plain fields.** Every tenant-owned `DomainEvent` carries
`tenant_id: str` (always required for tenant-owned facts) and `organization_id: str | None`
(explicit — non-`None` when the fact belongs to one organization, explicitly `None` when the fact
is genuinely tenant-wide and not owned by any single organization). Genuinely
installation/platform-wide facts — no tenant at all — use a separate event type with no
`tenant_id` field at all.

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

**Explicit invariant — `organization_id` on a tenant-owned `DomainEvent` has exactly two valid
meanings, never a third:**

| Value | Meaning | Never means |
|---|---|---|
| `organization_id="A1"` (a real ID) | This fact belongs to Organization A1 and no other | — |
| `organization_id=None` | This fact is **intentionally, genuinely tenant-wide** — it does not belong to any single organization | organization unknown; organization not loaded; organization omitted by an oversight; "use whatever the active session's current organization is" |

**Never** substitute the desktop session's currently-active organization for an event's own
`organization_id`, under any circumstance. An organization-scoped mutation's event carries the
organization it actually mutated — read directly off the aggregate/command, not off mutable
"current organization" UI state, which may legitimately differ (a user could mutate Organization
A1 while their session's active organization selector is pointed at A2). No handler, transactional
or post-commit, may compute or default `organization_id` from ambient session state after the
fact — it is always read from the mutation itself, at the point the event is constructed.

**Rationale for keeping `DomainEvent` on plain fields (not the typed `EventScope` §12 adopts for
`ViewInvalidationHint`):** a module author writing `TaskReassigned`/`OrganizationRenamed` is
naming a *business fact*; `tenant_id: str, organization_id: str | None` reads exactly like the two
plain, unremarkable identifier fields they already are in every other part of this codebase's
domain vocabulary (compare `project_id: str`, `task_id: str` on the very same dataclass) — wrapping
them in a `scope: EventScope` object would be a foreign, transport-flavored indirection sitting
inside otherwise-plain business vocabulary, for no benefit `DomainEvent` itself needs (a
`DomainEvent` is never subscribed-to or filtered-by-breadth the way a `ViewInvalidationHint` is —
see §12 for why that dimension is exactly where the ambiguity, and therefore the benefit of a typed
union, actually lives).

### 3a. Cross-Organization Effects — the Multi-Hint Rule

A single mutation can legitimately affect more than one organization within a tenant (e.g. a
shared resource reassigned from Organization A1 to Organization A2 within Tenant A) without being
tenant-wide (Organization A3 in the same tenant is unaffected). **Decision: represent this as
multiple, individually organization-scoped `ViewInvalidationHint`s — one per affected
organization — never as a single hint with `organization_id=None`.** `organization_id=None` means
"genuinely tenant-wide," which this scenario is not; encoding "affects A1 and A2, not A3" as
tenant-wide would incorrectly notify A3's subscribers too.

```python
for organization_id in affected_organization_ids:  # e.g. {"A1", "A2"}, never including "A3"
    channel.notify(ViewInvalidationHint(
        scope=OrganizationScope(tenant_id="A", organization_id=organization_id),
        category=..., scope_code=..., entity_type=..., entity_id=...,
    ))
```

**Explicitly rejected:** a `MultiOrganizationScope`/`organization_ids: list[str]`-shaped scope
type collapsing this into one hint. Nothing in this product's current requirements needs it — the
affected-organization set is always small and known at the point of mutation, and multiple
individually-correct hints are simpler to route, test, and reason about than a new scope kind
whose own subscription-matching semantics would need to be designed and justified. Revisit only if
a real, evidenced need for a genuinely bulk, large-fan-out multi-organization notification pattern
emerges — do not build it speculatively now.

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
explicit decision in §11 (Integration Event / Outbox Boundary) for why in-process domain events
do not need one.

### 6. Event Recording Decision

**Decision (strengthened this pass from "default" to a explicit rule):** *If a `DomainEvent`
represents a business fact produced directly by an aggregate's own state transition, the
aggregate MUST record that event itself, via `RecordsDomainEvents`.* `uow.record_event(...)` is
**reserved exclusively** for a fact that genuinely has no single owning aggregate — it is not a
convenience default for skipping the (admittedly more invasive) work of adding
`RecordsDomainEvents` to an aggregate class. A code reviewer encountering
`uow.record_event(SomeFact(...))` in a change should be able to ask "which aggregate's state
transition does this represent?" and get "none — this is genuinely cross-aggregate orchestration"
as the only acceptable answer; "the aggregate exists but recording on it seemed like more work"
is not a valid justification for reaching for the escape hatch instead. This is **not** a mandate
to add `RecordsDomainEvents` to every Platform entity or service — plenty of Platform/module
mutations have no business-fact-worthy event at all (§1's taxonomy already excludes UI-refresh
verbs from being events in the first place). Explicit criteria:

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
single aggregate whose method could have recorded it. **The Platform implementation plan (Phase
P5) lists the specific Platform capabilities to assess against this criteria table** — this ADR
does not pre-judge which Platform capabilities get aggregate-recorded events versus
orchestration-authored ones; that is a per-capability discovery task, not a blanket rule.

**Enforcement, not just intention:** the Platform implementation plan requires, for every event
introduced in Phase P5, an explicit reviewer check — "does an aggregate exist whose state
transition this event represents? If yes, it MUST be `_record_event`-ed there, not
`uow.record_event`-ed from the service" — recorded as a per-event checklist item, not merely
asserted in this ADR's prose. A worked example of each path (one genuinely aggregate-recorded
event, one genuinely orchestration-authored event with a documented reason no aggregate could have
owned it) is required test coverage before Phase P5 closes, so the distinction is demonstrated,
not only described.

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

**Explicit boundary — `UnitOfWork` exposes the transaction, never a general dependency lookup.**
Neither the shared `UnitOfWork` protocol nor any module-specific extension gains a generic
`repository_for(contract: type[R]) -> R`-shaped method callable with an arbitrary contract type
from arbitrary handler code. An earlier draft of this revision proposed exactly that as a way to
let `ApprovalService`'s cross-module apply handlers reach another module's repository within the
same transaction; a critical review found it would let a `UnitOfWork` quietly become a general
service locator (`uow.repository_for(ProjectRepository)`, `uow.repository_for(EmployeeRepository)`,
`uow.repository_for(AnythingAtAll)`), which weakens module-boundary visibility, static
enforcement, and testability exactly as much as any other ambient service locator does. **The one
genuine cross-module case this codebase has (`ApprovalService`'s apply handlers) is resolved
narrowly, in §24, by a per-handler-registration dependency declaration — not by a general method
on `UnitOfWork` itself.** No other module's `UnitOfWork` extension gets, or needs, an equivalent
mechanism; a transactional handler that needs another aggregate reaches it the ordinary way,
through its own module-specific `UnitOfWork` extension's named, typed accessors
(`uow.projects`, `uow.tasks`), decided per module at that module's own migration time, exactly as
already specified below.

**Rationale for the semantic reservation:** the audit found `ApprovalService`'s existing
"unit of work" is a *logical* convention (only one method calls `.commit()`) enforced over the
*same shared, process-lifetime `Session`* every other Platform service uses — not a physically
isolated transaction. Two different guarantees sharing one name is a real risk once both exist
side by side; reserving "UnitOfWork" for the stronger, physical guarantee and requiring anything
weaker to use different vocabulary (§24) removes the ambiguity going forward.

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

**Revised this pass.** The previous revision gave `ViewInvalidationChannel` five separately-named
subscription methods (`subscribe`, `subscribe_tenant_wide`, `subscribe_across_organizations`,
`subscribe_across_tenants`, `subscribe_to_platform_wide`) plus two separate hint types
(`ViewInvalidationHint`/`PlatformViewInvalidationHint`), to keep `organization_id`/`tenant_id`
structurally unambiguous. A critical review found this was solving a real problem
(`organization_id: str | None` genuinely has two meanings that must never be confused) with the
wrong tool (method proliferation) — and that the method count would keep growing with any future
dimension. **Decision: replace the flat `tenant_id`/`organization_id`/two-hint-type shape with one
typed, closed `EventScope` union, and collapse the five subscribe methods into one, parameterized
by a small, equally closed `ScopeFilter` hierarchy.**

```python
# src/core/shared/events/view_invalidation.py

class EventScope(Protocol):
    """A closed union of exactly three kinds — sealed by convention (only these three
    dataclasses implement it; do not add a fourth without revisiting this ADR)."""

@dataclass(frozen=True, slots=True)
class PlatformScope(EventScope):
    """No tenant at all. Genuinely installation-wide facts only."""

@dataclass(frozen=True, slots=True)
class TenantScope(EventScope):
    """Tenant-wide — NOT organization-scoped. There is no organization_id field on this
    type at all; a fact that belongs to one organization is never represented this way."""
    tenant_id: str

@dataclass(frozen=True, slots=True)
class OrganizationScope(EventScope):
    """Exactly one organization within one tenant. organization_id is a required
    constructor argument — there is no way to construct this type without one."""
    tenant_id: str
    organization_id: str

@dataclass(frozen=True, slots=True, kw_only=True)
class ViewInvalidationHint:
    scope: EventScope             # PlatformScope | TenantScope | OrganizationScope
    category: str
    scope_code: str
    entity_type: str
    entity_id: str | None = None
```

**Revised again in P16D-FIX (§26.14):** `EventScope` gained a fourth kind, `ResourceScope`
(`tenant_id`/`organization_id`/`module_code`/`entity_type`/`entity_id` — exactly one
resource/entity within one organization), after an earlier attempt to solve the same problem by
adding `module_code: str | None = None` directly to `ViewInvalidationHint` was judged to violate
this hint's own shape (target + typed scope, never an accumulating capability-specific field). See
§26.14 for the full correction and rationale; `ViewInvalidationHint` itself keeps the five fields
shown below, unchanged from this revision.

**Why this resolves the `organization_id=None` ambiguity structurally, not by convention:** under
the flat shape, `organization_id=None` had to carry the entire weight of meaning "intentionally
tenant-wide" versus every other, forbidden reading (§3's invariant table) — a discipline enforced
only by this document's prose and code review. Under the typed union, a `TenantScope` **has no
`organization_id` field to be ambiguous about** — the Python type checker rejects
`TenantScope(tenant_id="A", organization_id="A1")` outright, and there is no constructor call that
can produce an organization-scoped fact without supplying a real `organization_id`. The invariant
becomes a fact about the type system, not a fact developers must remember.

**Why `DomainEvent` does *not* also adopt `EventScope`:** see §3 — a `DomainEvent`'s
`tenant_id`/`organization_id` are business vocabulary, read naturally alongside a dataclass's other
plain identifier fields; `ViewInvalidationHint` is transport/filtering infrastructure, precisely
where a subscriber needs to reason about *breadth* of interest (exact organization vs. any
organization in a tenant vs. every tenant), a concept `DomainEvent` never needs at all. The two
types are allowed, deliberately, to represent the same underlying fact differently, because they
serve genuinely different readers.

**Subscription collapses to one method, parameterized by a `ScopeFilter` — a *distinct* concept
from `EventScope`, because "breadth of interest" is not itself a kind of scope a fact can have; it
is a property of what a subscriber wants:**

```python
class ScopeFilter(Protocol):
    def matches(self, scope: EventScope) -> bool: ...

@dataclass(frozen=True, slots=True)
class ExactOrganization(ScopeFilter):
    """This organization's views only. A hint for a different organization in the same
    tenant, or a tenant-wide hint, is never delivered here."""
    tenant_id: str
    organization_id: str
    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, OrganizationScope) and \
            scope.tenant_id == self.tenant_id and scope.organization_id == self.organization_id

@dataclass(frozen=True, slots=True)
class TenantWide(ScopeFilter):
    """Only genuinely tenant-wide facts for this tenant. An organization-scoped hint,
    even for an organization in this same tenant, is never delivered here."""
    tenant_id: str
    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, TenantScope) and scope.tenant_id == self.tenant_id

@dataclass(frozen=True, slots=True)
class AnyOrganizationInTenant(ScopeFilter):
    """Deliberate breadth: every hint for this tenant, tenant-wide or any organization's.
    For genuine tenant-admin/organization-selector screens — a searchable, auditable
    opt-in, never the default."""
    tenant_id: str
    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, (TenantScope, OrganizationScope)) and scope.tenant_id == self.tenant_id

@dataclass(frozen=True, slots=True)
class AllTenants(ScopeFilter):
    """Every tenant's hints. Rare, auditable, platform-admin-only. Not to be conflated
    with AnyOrganizationInTenant, which is still scoped to one tenant."""
    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, (TenantScope, OrganizationScope))

@dataclass(frozen=True, slots=True)
class PlatformWide(ScopeFilter):
    """Only genuinely platform-wide facts — never a tenant-scoped hint of any kind."""
    def matches(self, scope: EventScope) -> bool:
        return isinstance(scope, PlatformScope)

class ViewInvalidationChannel(Protocol):
    def notify(self, hint: ViewInvalidationHint) -> None: ...
    def subscribe(
        self, filter: ScopeFilter, handler: ViewInvalidationHandler[ViewInvalidationHint],
    ) -> Subscription: ...
```

**One `notify`, one `subscribe` — the five named entry points from the previous revision become
five `ScopeFilter` dataclasses instead of five channel methods.** This is a genuine simplification,
not a relabeling: a sixth filter kind, if one is ever needed, is a new dataclass implementing
`ScopeFilter`, never a new method on the channel contract itself — the channel's own
`subscribe`/`notify` implementation never has to change to support it, since routing is just
"call `filter.matches(hint.scope)` for every registered subscription and deliver to the ones that
return `True`." The channel implementation therefore contains no per-filter-kind branching logic
at all.

**Routing, stated once, by construction, not enumerated per filter (this is exactly what the
implementation plan's tenant/organization test matrix directly exercises):** `notify(hint)`
delivers to every currently-registered `(filter, handler)` pair where `filter.matches(hint.scope)`
is `True`. Every example from the previous revision's routing table still holds, now as a
*consequence* of the five filters' own `matches` implementations above rather than as separately
documented channel behavior — an `OrganizationScope(A, A1)` hint reaches `ExactOrganization(A, A1)`
and `AnyOrganizationInTenant(A)` subscribers, never `TenantWide(A)` or any `Tenant B` subscriber
(unless `AllTenants()`); a `TenantScope(A)` hint reaches `TenantWide(A)` and
`AnyOrganizationInTenant(A)` subscribers, never `ExactOrganization(A, ...)` for any organization
value; a `PlatformScope()` hint reaches only `PlatformWide()` subscribers.

`scope_code`/`entity_type` filtering remains a binder-level convenience closure, exactly as
before — only the tenant and organization dimensions (now expressed through `EventScope`/
`ScopeFilter`) are genuine security/correctness boundaries enforced by the channel itself.

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
implementation plan (Phase P6) scopes this precisely.

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
a tenancy-architecture decision, out of scope here, and is recorded as an open dependency (see
"Open Items Before This Can Move to Accepted," below) for whoever eventually designs the web
adapter — not something this ADR resolves or should be read as having resolved.

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
| `Signal[T]` (`src/core/shared/events/signal.py`) | **Rename to `CallbackSignal`** in a later phase (the Platform implementation plan, Phase P7/P8) — resolves the same-file collision with `PySide6.QtCore.Signal` that today forces an import alias | **Not blocking** for Phase 0-P4 — scheduled as legacy-bridge cleanup once callers have migrated off it |
| `PlatformEvent` | Document clearly as an **audit/governance record, not a Domain Event** (§1's taxonomy table). A future rename to `PlatformAuditEntry` is recommended | **DEFERRED — NOT BLOCKING.** It has exactly one real construction site (`tenant_admin_service.py`), is never dispatched or subscribed to, and its collision with "Domain Event" vocabulary is documentation-level, not functional. Renaming it is not a prerequisite for anything in this ADR. |
| `ApprovalService`'s existing pattern | Do **not** call it a "Unit of Work" going forward (§9) — call it a transaction convention, pending its own migration (§24) | N/A — naming clarification only |

`CallbackSignal` was chosen over `Observable` (implies reactive-programming operators — `map`/
`filter`/etc. — this primitive has none, and the name would overpromise) and `EventEmitter`
(reintroduces "Event" into the name of something that is not a `DomainEvent`, precisely the
collision being resolved).

**Lifecycle, stated explicitly rather than left as "kept forever" or "deleted eventually" without
a plan:**

1. **Now → Phase P4:** kept, unchanged, as `Signal[T]` — still the mechanism the legacy
   `domain_events.py` bag depends on.
2. **Phase P7 (per the execution plan):** renamed to `CallbackSignal` once `domain_events.py`'s own
   consumers have migrated to `TransactionalEventDispatcher`/`PostCommitEventPublisher`/
   `ViewInvalidationChannel` for domain-event purposes. At this point its **intended scope
   narrows**: it is no longer the mechanism anything reaches for by default for a new
   domain-event-shaped need — the three named mechanisms above supersede it for that purpose
   entirely. It may still be used internally by their own concrete implementations if convenient
   (an implementation detail, not a public contract), and it remains available for a genuinely
   narrow, non-domain-event pub-sub need unrelated to this ADR's scope, if one exists.
3. **Post-P8, explicitly not decided here:** whether `CallbackSignal` has any legitimate caller
   left once `domain_events.py` itself is fully retired is an open question this ADR does not
   resolve — the Platform audit's scope was domain-event-related usage specifically, not an
   exhaustive inventory of every `Signal` call site in the codebase, so this ADR cannot responsibly
   claim "zero remaining callers" or commit to a deletion date. **Full retirement is deferred,
   pending a dedicated inventory of any non-domain-event callers, performed after Phase P8** — not
   because retirement is undesirable, but because committing to it now would be a guess this ADR
   is not in a position to make honestly.

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
framework. It adds **one** test using the same technique: the **whole** `src/core/platform/`
tree (`domain/`, `application/`, `infrastructure/`, `contract/`, `api/`, etc.) must not import
`src.core.modules.*`.

**Correction found during P0 implementation:** an earlier draft of this section scoped the
guardrail to `src/core/platform/{domain,application}/` only — that scope statement was
inconsistent with this section's own two governed exceptions below, one of which
(`SqlAlchemyApprovalRepository`) lives under `src/core/platform/infrastructure/`, outside a
domain/application-only scan. A domain/application-only guardrail would never have seen that
violation, making its own "allowlisted in the guardrail test" statement meaningless. Corrected to
scan the whole `src/core/platform/` tree, matching both governed exceptions and the audit's own
methodology (which found both violations by scanning all of `src/core/platform/`, not a narrower
subtree). No new violation surfaced by widening the scope — confirmed the whole tree contains
exactly these two `src.core.modules` imports, no more.

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

**As originally planned (below, unchanged from Round 6-8):**

| Mechanism | Disposition |
|---|---|
| `domain_events` singleton / `Signal` / `DomainChangeEvent` | Bridge incrementally, module/capability by module/capability, per the execution plan; retire once every consumer has migrated |
| `admin_console/domain_event_binder.py` | Already self-scheduled for removal ("phase R2" per its own docstring) — this migration's Phase P6/P7 (implementation plan) absorbs and completes that already-planned removal, rather than leaving it as a separate, uncoordinated cleanup |
| Three `workspace_controller_base.py` copies | Generalize the invalidation slice into one shared adapter (§13); do not bridge each of the three separately, and do not unify the rest of their responsibilities |
| `ApprovalService`'s existing transaction convention | **Adapt** (§24) — migrate onto the canonical `UnitOfWork` in Phase P4, not bridged indefinitely and not left permanently distinct |
| `project_management`'s `Resource*UnitOfWork` (module-owned, cited for comparison only) | Out of this ADR's Platform-scoped decision — resolved when `project_management`'s own module migration phase runs |
| `PlatformEvent` | Kept as-is; rename deferred, non-blocking (§19) |
| `NotificationService`/`Notification` | Kept as-is; unrelated to this migration |
| `IntegrationEventEnvelope`/outbox-inbox (ADR-PF-011) | Kept as-is; unrelated mechanism, already correct |
| Dead `session_scope()` | Reclaimed (§20) — zero callers, no migration cost |

**As actually implemented (P8 closeout — see §26 for the full ledger):**

| Mechanism | Actual final disposition |
|---|---|
| `domain_events` singleton / `Signal[str]` fields | **26 remain, LEGACY-ONLY, frozen allowlist** (§26.5) — not "bridged," never merged into anything typed. Each has a real producer and a real consumer, direct-wired (no generic routing of any kind). New Signal fields are architecture-guarded against; deletion remains unrestricted per-capability as each is semantically migrated. |
| `_BRIDGE_SPECS` / `_wire_bridges` / `_build_bridge` / `domain_changed` / `DomainChangeEvent` / `_subscribe_domain_change` | **Deleted entirely (P7A)** — this went further than "bridge down and retire": the generic entity_type/scope_code dispatch mechanism itself was removed, not merely emptied. All 17 production callers were converted to direct `_subscribe_domain_signal(specific_signal, callback)` wiring first. |
| `shared_master_changed` | **Deleted (P7)** — zero production consumers found; fully redundant with `domain_changed`'s own routing even before P7A removed that mechanism too. |
| `costs_changed`, `calendars_changed` | **Deleted (P7B)** — zero production producers of any kind (direct or reflective), despite live UI consumers; the consumers were dead code by construction. |
| `cost_entries_changed`, `commitments_changed`, `forecasts_changed`, `financial_changes_changed` | **Deleted (P7C)** — real producers (direct `.emit(` and reflective `ApprovalPostCommitEvent`), zero consumers of any kind; both the signals and their producer call sites were removed. |
| `admin_console/domain_event_binder.py` | **KEPT, unchanged** — the P7 audit found it was never a generic bridge in the first place (it always subscribed directly to specific signals); it owns a real, still-required composite-refresh responsibility. Its own "R2" self-scheduled removal remains separate, future, not performed here. |
| Three `workspace_controller_base.py` copies | **KEPT, all three, unchanged** — P6's own audit found the ViewInvalidation-adapter lifecycle was never duplicated across them in the first place (adapter construction lives at the catalog level, not any controller base); §13's shared adapter (`ScopedViewInvalidationSubscription`, composition-based) was built and adopted by all five capability adapters instead. |
| `ApprovalService`'s transaction convention | **Adapted exactly as planned** — migrated onto the canonical `UnitOfWork` in P4/P4-PRE. |
| `PlatformEvent` / `NotificationService` / `IntegrationEventEnvelope` (outbox/inbox) | **Kept as-is, exactly as planned** — confirmed still structurally distinct from `DomainEvent` (§26.1). |
| Dead `session_scope()` | Reclaimed as planned. |
| Organization update/set-active | **Not in the original table at all** — discovered during P7 to still use the direct (never-bridged) `organizations_changed` signal; P5A only ever typed `OrganizationCreated`. Documented as a correction, not migrated (§26.4). **Migrated (P10D):** `update_organization`/`enable_organization`/`disable_organization` now record `OrganizationProfileUpdated`/`OrganizationEnabled`/`OrganizationDisabled` on the same canonical `OrganizationUnitOfWork` `OrganizationCreated` already used, mapped onto the existing `organization_list` ViewInvalidation target. `organizations_changed` is deleted from `DomainEvents` entirely — zero remaining producers, zero remaining consumers. Session-context selection (`TenantContextService.set_active_organization`) was never in scope for this migration and produces no DomainEvent of any kind. |
| Employee create/update | Not in the original table — `employees_changed` was a direct (never-bridged) legacy signal, un-typed prior to P12A/P12B. **Migrated (P12B):** `create_employee`/`update_employee` now record `EmployeeCreated`/`EmployeeProfileUpdated` on the canonical `EmployeeUnitOfWork` P12A converged onto, mapped onto a new `employee_list` ViewInvalidation target (`OrganizationScope`, matching Employee's actual ownership — organization-scoped, not tenant-wide). `employees_changed` is deleted from `DomainEvents` entirely — zero remaining producers, zero remaining consumers. `resources_changed` (Employee's other, PM-owned legacy signal, still emitted by `update_employee`'s linked-resource sync) is explicitly untouched — Resource capability remains NOT MODERNIZED. |
| Department create/update | Not in the original table — `departments_changed` was a direct (never-bridged) legacy signal, un-typed prior to P13A/P13B. **Migrated (P13B):** `create_department`/`update_department` now record `DepartmentCreated`/`DepartmentProfileUpdated` on the canonical `DepartmentUnitOfWork` P13A converged onto, mapped onto a new `department_list` ViewInvalidation target (`OrganizationScope`). `departments_changed` is deleted from `DomainEvents` entirely — zero remaining producers, zero remaining consumers (Admin Console was its only consumer, per P11's audit). |
| Site create/update | Not in the original table — `sites_changed` was a direct (never-bridged) legacy signal, un-typed prior to P14A/P14B, with five real consumers (Admin Console plus Inventory/Pricing/Procurement/Reservations). **Migrated (P14B):** `create_site`/`update_site` (extracted into `site_commands.py` during this phase, off the canonical `SiteUnitOfWork` P14A converged onto) now record `SiteCreated`, `SiteProfileUpdated`, and — mirroring Organization's own `is_enabled`-boolean precedent — `SiteEnabled`/`SiteDisabled` for the one genuine lifecycle transition (`is_active`), mapped onto a new `site_list` ViewInvalidation target (`OrganizationScope`). A single mutation that changes both profile fields and availability in the same call records both distinct typed events (both still individually published on the post-commit bus) but the `site_list` handler coalesces them to one ViewInvalidation hint per commit (keyed on the UoW's `DomainEventContext.correlation_id`), so one Site mutation never causes more than one downstream refresh. `sites_changed` is deleted from `DomainEvents` entirely — zero remaining producers, zero remaining consumers. Of the five prior consumers: Admin Console got a new narrow `refresh_sites()`; Inventory/Pricing/Procurement each got a new narrow `refresh_site_options()` (rebuilding only their `site_options`/`storeroom_options` reference data, since storeroom labels embed the site name) via three new `SiteViewInvalidationAdapter` instances wired in a from-scratch ViewInvalidation seam built for `InventoryProcurementWorkspaceCatalog` (previously had none); Reservations had zero real Site dependency (confirmed by audit) and was simply dropped with no replacement wiring. |

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
"competing convention" outcome this ADR exists to prevent). `ADR-PF-008` itself remains a
**precedent being adapted**, never a second, permanently-standing definition of "Unit of Work" —
once Phase P4 closes, `ApprovalService`'s own transaction boundary *is* a canonical `UnitOfWork`,
not a parallel concept still called by the same name for a different guarantee.

**The cross-module apply-handler problem, and the `repository_for(contract)` design it produces —
reviewed and narrowed.** Migrating `ApprovalService` to a genuinely fresh, per-call `Session`
(required for it to be a real `UnitOfWork` per §9) raises a real complication: its apply handlers
are registered by *other modules* (PM's baseline/dependency/cost handlers, Inventory's
requisition/PO handlers, per ADR-PF-008's own implementation evidence) and today mutate their own
modules' repositories bound to the single shared session — a binding that becomes stale the moment
`ApprovalService` moves to a fresh session per call.

*Rejected first cut:* an early draft of this revision proposed
`PlatformUnitOfWork.repository_for(contract: type[R]) -> R`, an open, contract-keyed lookup any
handler could call with any repository contract type at any point in its body. **A critical review
correctly identified this as a hidden general-purpose service locator in disguise** —
`uow.repository_for(ProjectRepository)`, `uow.repository_for(EmployeeRepository)`,
`uow.repository_for(AnythingAtAll)` — which would make a handler's real dependencies invisible at
its registration site, undiscoverable by the architecture guardrail test (§21), and hard to unit
test without faking an entire `UnitOfWork`'s lookup behavior. This directly contradicts the
principle §9 already states: `UnitOfWork` exposes the transaction boundary; it must not become a
general application dependency container.

**`repository_for` is REMOVED from `UnitOfWork`'s surface entirely (as §9 already states).** The
shape it was replaced with — below — is itself revised this pass (Round 7), after the shape
originally proposed here was checked against the real apply-handler surface and found not to fit.

**Round 7 finding: the originally-specified `TDeps` (a repository-shaped dataclass resolved from a
generic binder registry) does not match how any real apply handler works.** A pre-implementation
investigation (required by the Platform implementation plan's own Phase P4 gate: inspect the
actual current implementations before writing code; stop and report rather than silently redesign
if source conflicts with approved architecture) inventoried all 18 real, production
`register_apply_handler`/`register_reject_handler` registrations:

- 14 in `src/infra/composition/project_registry.py` — `baseline.create`;
  `dependency.add`/`remove`/`update`; `task.constraint.update`; `scheduling.leveling.apply`;
  `budget.approve` (apply+reject); `project_cost.approve` (apply+reject); `financial_change.apply`
  (apply+reject); `project_billing_preparation.approve` (apply+reject).
- 4 in `src/infra/composition/inventory_registry.py` — `purchase_requisition.submit`
  (apply+reject); `purchase_order.submit` (apply+reject).

**Every one of the 18, without exception, calls into an already-constructed, long-lived PM/
Inventory *application service*** (`BaselineService`, `TaskService`, `BudgetService`,
`ProjectCostEntryService`, `FinancialChangeService`, `ProjectBillingPreparationService`,
`ProcurementService`, `PurchasingService` — 8 distinct services backing the 18 registrations),
**never a bare repository**. Each of these 8 services is built exactly once, at composition time,
bound to the single process-lifetime `Session` every other Platform/PM/Inventory service shares —
and **every one of the 8 also takes `approval_service=platform_services.approval_service` as a
constructor argument**, a real, structural, 8-for-8 circular object-graph reference, not an
isolated case.

A repository-shaped `TDeps` is one layer too low for this surface: forcing an apply handler to
receive raw repositories instead of the service it actually calls would require re-deriving that
service's own business orchestration (its staged mutation, its own audit/notification side
effects, its own multi-repository coordination) directly inside Platform's dispatch code, or
duplicating it there — exactly the business-logic absorption §1/§25 already forbid Platform from
doing. **Verdict: KEEP the mechanism's shape — an explicit, per-registration-site, statically
declared dependency, resolved by `ApprovalService`'s own dispatch logic, never a method on
`UnitOfWork` — REVISE what that dependency is and how it is produced.**

**Revised decision:**

```python
# src/core/platform/contracts/approval.py
class ApprovalApplyHandler(Protocol[TDeps]):
    def __call__(
        self, request: ApprovalRequest, uow: PlatformUnitOfWork, deps: TDeps,
    ) -> ApprovalHandlerResult: ...

def register_apply_handler(
    request_type: str,
    handler: ApprovalApplyHandler[TDeps],
    *,
    dependencies_factory: Callable[[Session], TDeps],   # module-owned; constructs TDeps fresh,
                                  #   bound to the CURRENT approve_and_apply/reject call's session
) -> None: ...
```

`TDeps` is still a small, module-owned type declared **at the same call site** as
`register_apply_handler` — the difference from the original design is that it is produced by a
**module-supplied factory function**, not resolved from a generic, type-keyed binder registry
populated at startup. *(Round 7 originally described this factory as reconstructing a fresh
instance of the module's own existing, unmodified service class — Round 8, below, supersedes that
specific mechanism: given this application is pre-release with no backward-compatibility
constraint, the factory instead produces a standalone, purpose-built, session-parameterized
participant with the approval-facing logic ported directly into it, never a whole reconstructed
service instance. The `dependencies_factory(session) -> TDeps` *shape* is unchanged; what it
builds is not a resurrected legacy object.)* e.g. `project_management` declares
`build_budget_approval_deps(session: Session) -> BudgetApprovalDeps`, which constructs whatever
fresh repositories the participant needs via the already-proven-reusable
`build_repository_bundle(session)` (`src/infra/composition/repositories.py:202`) and wraps them,
alongside the ported apply logic, in `BudgetApprovalDeps`.

**A previously-unconfirmed fact that de-risks this:** `build_repository_bundle(session)` is
already a pure, stateless, per-session factory — every repository any of the 8 backing services
uses is already constructible fresh from an arbitrary `Session`, with no startup-only assumption
in it. The missing piece is one layer up: a per-module, per-request-type factory that reconstructs
the *service* itself (not just its repositories) bound to a supplied session. This is finite,
per-service work — 8 services — not an open-ended rewrite, but it is real work that must happen
*before* `ApprovalService` can move to a fresh session, not as an incidental part of moving it. See
the Execution Plan's revised Phase 2 sequencing for the gated prerequisite this now requires.

**The circular `approval_service=` reference does not block this** — and, per Round 8 below, does
not need managing at all for the *new* code path. The investigation confirmed the back-reference
exists so each of the 8 services can independently call `approval_service.request_change(...)`
for *its own*, later, unrelated approval flows — it is not a call `approve_and_apply`/`reject`
makes back into itself during the same apply invocation. Round 7 proposed handling this by keeping
a freshly-constructed instance's outbound reference pointed at the original `ApprovalService`;
Round 8 makes the question moot for the apply path specifically — a standalone participant has no
reason to hold an `approval_service` reference at all, since it isn't the whole service, only the
apply-facing slice of it. The **old** service instance (unchanged, still used for its own other,
non-approval commands) keeps its existing `approval_service=` reference exactly as today; only
collaborators that must land in the *same* transaction as the apply decision (the participant's
own repositories, and any Platform cross-cutting service that also writes — e.g.
`enterprise_audit_service`, itself session-bound and required by ADR-PF-008 to commit atomically
with the mutation) are constructed fresh, bound to the current session.

- **Allowed usage:** only `ApprovalService`'s own internal dispatch logic calls a handler's
  registered `dependencies_factory` with the current call's session. A module declares its
  dependency shape and construction once, at registration.
- **Forbidden usage:** no handler body calls anything resembling `uow.repository_for(...)` or a
  generic `resolve(TDeps)`; no such method exists on `UnitOfWork`, base or Platform-extended, after
  this decision. No other module's `UnitOfWork` extension gains an equivalent open lookup — this
  mechanism is scoped to `ApprovalService`'s specific cross-module registration shape, not offered
  as a general pattern.
- **How `ApprovalService` works afterward:** `approve_and_apply` constructs a fresh
  `PlatformUnitOfWork`, looks up the registered handler and its `dependencies_factory` for the
  request's `request_type`, calls `dependencies_factory(uow's session)` to obtain `deps: TDeps`,
  calls `handler(request, uow, deps)`.
- **How module boundaries remain visible:** reading one `register_apply_handler(...,
  dependencies_factory=build_budget_approval_deps)` call site, plus that one factory function's
  body, shows exactly what that handler needs and how it is built, statically, in one place — no
  runtime lookup calls scattered through a handler's body to trace, and no generic registry mapping
  types to constructors that a reviewer has to cross-reference separately.
- **Testing implications:** a handler is unit-tested by constructing its own `TDeps` directly with
  fakes — no need to fake an entire `PlatformUnitOfWork`, a binder registry, or intercept an open
  lookup method.

`ApprovalHandlerResult.post_commit_events` also changes shape in this same phase, from
`(signal_name: str, payload: str)` string-keyed reflection into the legacy bus, to
`tuple[DomainEvent, ...]` — typed events, dispatched through the new `PostCommitEventPublisher`,
per §7/§8.

**Prerequisite phase required before Phase P4 begins.** Making each of the 8 backing services'
apply-relevant logic session-parameterizable is now a named, separately gated prerequisite
(Execution Plan Phase 2, sub-phase 2A-PRE) — not something Phase P4 absorbs silently while also
migrating `ApprovalService`'s own transaction boundary. See the Execution Plan for the staged
sequencing and its own review gates.

**Round 8 correction — direct convergence, no legacy-session adapter (pre-release scope
decision).** Round 7 designed 2A-PRE as four steps, the first two of which (Step A: extract an
adapter that still delegates to the 8 services' existing instances on the shared session; Step B:
separately make those adapters' dependencies session-parameterizable) existed specifically to
prove behavioral parity incrementally before touching transaction mechanics — a caution
appropriate for a system with live users and a backward-compatibility obligation. **This
application is pre-release: there are no external users and no backward-compatibility requirement
for the current process-lifetime `Session` architecture.** Building a Step-A adapter that still
targets the shared session, only to delete it again in Step B/D once its session-parameterized
replacement exists, is exactly the "temporary architecture that will immediately be deleted" this
correction removes. **Steps A and B are collapsed into one direct step; Steps C and D are
unchanged (they are `ApprovalService`'s own cutover and cleanup, not the services' construction
model).**

A wider audit (beyond the 8 approval-backed services) was performed to size this correctly and
confirm it does not silently expand into a full module migration:

- **30 PM/Inventory application services are mutation-capable and permanently hold repositories
  bound to the single process-lifetime `Session`** (22 in `project_management`, 8 in
  `inventory_procurement`), each built once at composition time in `project_registry.py`/
  `inventory_registry.py`. Of these, **~20 are "transaction-owning commands"** — they call
  `self._session.commit()`/`.rollback()` directly and have no caller-composable staging mode at
  all (`ProjectService`, `PortfolioService`, `CollaborationService`, `RegisterService`,
  `ProjectResourceService`, `ProjectRateCardService`, `PlannedCostService`,
  `ProjectBillingProfileService`, `ForecastVersionService`, `ForecastGenerationService`,
  `FinancialConfigurationService`, `ReservationService`, `InventoryService`,
  `InventoryFoundationService`, plus the non-approval command surface of the 8 mixed services
  below, and others). **These are explicitly out of scope for 2A-PRE** — migrating their full
  command surface onto a per-command `UnitOfWork` is exactly what the Execution Plan's Phase 3
  (`inventory_procurement` pilot) and Phase 5 (`project_management`) already exist to do, with
  their own discovery-then-migration discipline and typed-event work (P5). Doing it here would
  make 2A-PRE swallow those phases prematurely and out of order.
- **8 services are "caller-owned transaction participants" for their approval-facing methods
  specifically** (`BaselineService`, `TaskService` — 5 of its 13 command mixins —, `BudgetService`,
  `ProjectCostEntryService`, `FinancialChangeService`, `ProjectBillingPreparationService`,
  `ProcurementService`, `PurchasingService`) — these are exactly the 8 already known from the P4A
  investigation, confirmed unchanged by the wider audit.
- **Two more services already have an identical, independent `commit: bool` staging surface with
  no relationship to approval at all** — `ProjectCommitmentService` and `StockControlService`.
  **These are explicitly out of scope for 2A-PRE too.** They are the same architectural pattern as
  the 8, but converging them is not required to unblock `ApprovalService`; per this ADR's existing
  convention of naming adjacent debt without opportunistically fixing it (§22's
  `SqlAlchemyApprovalRepository`→`ProjectORM` violation is the precedent), they are recorded here
  as separately-tracked debt for their own future phase, not pulled into this one.
- **`project_management` already has its own `ResourceMasterUnitOfWork`/
  `ResourceCapabilityUnitOfWork` classes** (cited in this ADR's Context section as prior art) —
  confirmed by direct read to be constructed with an *already-created* `Session` (not a session
  *factory*), built once at composition time, not per-operation. They independently reinvent
  exactly the commit/rollback-plus-event-emit wrapper this ADR's audit already characterized them
  as — further, unrelated evidence that "session ownership" is the one dimension nothing in this
  codebase has gotten right yet, not a reason to fold their own migration into 2A-PRE.
- **`build_repository_bundle(session)` already returns all 69 repository fields** spanning every
  PM, Inventory, and Platform repository used by all 30 services above (confirmed by direct read),
  meaning the repository-construction half of a full convergence is *already done* — the real,
  remaining work everywhere is only ever "stop holding a service instance across multiple calls,"
  never "find a way to construct its repositories fresh."

**Revised 2A-PRE design (2 direct steps, not 4):**

1. **Step 1 — `PlatformUnitOfWork`/`Factory`, plus module-owned, session-parameterized approval
   participants, built directly.** For each of the 8 services, the approval-facing logic currently
   living as a private method on the long-lived instance (`_apply_approval_decision`,
   `apply_submitted_requisition_approval`, etc.) is **ported** — not delegated-to-via-a-fresh-copy
   of the whole service — into a small, standalone, module-owned participant (a plain function or
   thin stateless class) that takes its repositories/collaborators as explicit parameters,
   constructed fresh per call from the session `ApprovalService`'s own `PlatformUnitOfWork`
   supplies via `dependencies_factory(session) -> TDeps`. Because a participant is not the whole
   service object, **it has no reason to hold an `approval_service=` reference at all** — Round 7's
   "keep the outbound reference pointed at the original instance" concern doesn't arise for new
   code; the **old** service instance keeps its existing `approval_service=` reference, unchanged,
   for its own unrelated, non-approval commands. The now-unused old approval-facing methods are
   deleted from the 8 service classes in this same step — not left dead until a later cleanup step,
   since dead code awaiting deletion is itself "temporary architecture."
2. **Step 2 — `ApprovalService` cutover (this is Phase P4 itself, unchanged in substance).**
   `request_change`/`approve_and_apply`/`reject` all move onto `PlatformUnitOfWorkFactory` in the
   same change, dispatching to the participants registered in Step 1.

**Explicit non-goal, stated because it would otherwise be tempting given "pre-release, no
compatibility constraint":** 2A-PRE does **not** migrate any of the ~20 pure transaction-owning
PM/Inventory services, does **not** converge `ProjectCommitmentService`/`StockControlService`, does
**not** touch `ResourceMasterUnitOfWork`/`ResourceCapabilityUnitOfWork`, and does **not** remove the
process-lifetime `Session` from `app_container`/`build_service_graph`. **The process-lifetime
`Session` can only be removed once every one of the 30 services above has migrated its full command
surface onto a per-command `UnitOfWork` — i.e., not before Execution Plan Phase 3
(`inventory_procurement`) and Phase 5 (`project_management`) have both closed.** 2A-PRE removes
only the approval-apply path's own dependency on that shared session; every other command in the
application continues to run against it, unchanged, until those later, already-planned phases
migrate their own module's command surface. Stating this explicitly prevents 2A-PRE's pre-release
latitude from being read as license to converge everything at once.

**[ADR-PF-011](ADR-PF-011-durable-integration-outbox-inbox.md) — Durable Integration Outbox and
Inbox.** Decision: **preserved unchanged**, boundary restated unambiguously in §11. No merge, no
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
  (§1; see Alternatives Rejected);
- fix the pre-existing `SqlAlchemyApprovalRepository → ProjectORM` layering violation as a side
  effect of this migration (§22);
- unify the three `workspace_controller_base.py` classes' non-invalidation responsibilities into
  one QML controller hierarchy (§13);
- rename `PlatformEvent` as a blocking prerequisite (§19);
- introduce a metrics/tracing platform (§18);
- change ADR-PF-011's durable delivery semantics in any way (§11, §24).

### 26. Implementation Status: P8 Closeout

> For live, capability-by-capability migration status, the current legacy `Signal` count, and
> the provisional roadmap for what's next, see
> [`docs/architecture/event-modernization-plan.md`](../architecture/event-modernization-plan.md)
> - this section records the design decisions and their rationale; that document tracks
> sequencing and is expected to change between ADR revisions.

This section is the authoritative record of what the Platform-scoped implementation (P0-P8 of
`platform_domain_event_implementation_plan.md`) actually built, as distinct from what earlier
sections of this ADR proposed. Nothing in §1-§25 was reversed; this section records completion,
scope, and the handful of corrections discovered along the way.

**26.1 The five concepts remain distinct, exactly as designed.** Verified against current source,
not merely restated from §1:

1. **`DomainEvent`** (`src/core/shared/events/domain_event.py`) — a `Protocol` (`runtime_checkable`,
   structural typing, zero base-class inheritance possible), the marker every module's own concrete
   event dataclass satisfies. In-process only, business-vocabulary only, never a UI message, never
   durable transport.
2. **`DomainEventContext`** (`src/core/shared/events/domain_event_context.py`) — correlation/
   causation/command metadata, kept off the business-fact dataclasses themselves exactly as §5
   decided.
3. **`ViewInvalidationHint`** (`src/core/shared/events/view_invalidation.py`) — a plain frozen
   dataclass (scope/category/scope_code/entity_type/entity_id), never a business fact, never routed
   through the same contract as a `DomainEvent`. Never crosses directly into QML/controller
   presentation without going through a capability-specific Qt adapter (§15 below).
4. **`IntegrationEventEnvelope`** (`src/core/platform/integration/events.py`) — a `pydantic.BaseModel`
   (schema-versioned, `event_id`/`event_type`/`schema_version`/`aggregate_type`/`aggregate_id`/
   `aggregate_version`/`payload`), structurally incapable of inheriting from the `DomainEvent`
   `Protocol` or vice versa. Owned by ADR-PF-011, untouched by this migration.
5. **`Notification`** (`src/core/platform/domain/events/notifications/notification.py`) and
   **`PlatformEvent`** (`src/core/platform/domain/events/platform_events/platform_event.py`) —
   persisted, user-facing communication and persisted governance/audit record respectively, both
   confirmed still structurally separate from `DomainEvent`, never merged into one "universal event"
   type as §25/Alternatives Rejected already forbid.

**26.2 The canonical write/reaction pipeline is now real, not aspirational, for five capabilities.**
Confirmed by source: `command/application operation → canonical UnitOfWork (`src/core/platform/
contract/persistence/*_unit_of_work.py` + `src/core/platform/infrastructure/persistence/
*_unit_of_work.py`) → aggregate-recorded DomainEvent (via `RecordsDomainEvents`,
`src/core/shared/events/aggregate_events.py`) or a justified `uow.record_event(...)` call →
`InProcessTransactionalEventDispatcher` (FAIL_FAST, pre-commit) → integration-event mapping/outbox
staging before commit where ADR-PF-011 applies → database commit →
`InProcessPostCommitEventBus` (ISOLATE_AND_CONTINUE, post-commit) → a per-capability mapper
(`event_handlers/view_invalidation.py`) producing exactly one `ViewInvalidationHint` per target →
`InProcessViewInvalidationChannel` → a capability-specific Qt adapter
(`src/ui_qml/platform/adapters/*_view_invalidation_adapter.py`, all five now built on the shared
`ScopedViewInvalidationSubscription` mechanics-only helper, §26.6) → a narrow controller/read-model
refresh method. 15 typed `DomainEvent` classes exist across 5 capabilities: `OrganizationCreated`
(1); `ModuleLicensed`/`ModuleLicenseRevoked`/`ModuleEnabled`/`ModuleDisabled`/
`ModuleLifecycleTransitioned` (5); `RoleBindingAssigned`/`RoleBindingRevoked` (2);
`TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed` (4);
`ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected` (3).

**26.3 Canonical rules for new Platform semantic behavior (§4/§5/§6/§9 restated as binding
policy, not merely design).** For any NEW Platform capability:
- Prefer an aggregate that implements `RecordsDomainEvents` and records its own typed events; the
  `uow.record_event(...)` escape hatch is allowed only for a legitimate application/orchestration
  fact with no natural aggregate owner (§6) — never merely to tell the UI to refresh.
- One `UnitOfWork` = one physical transaction = one fresh `Session` = owns commit/rollback = owns
  the `DomainEvent` lifecycle for that transaction (§9). No nested participant commit.
- Transactional handlers run pre-commit, FAIL_FAST (a failure rolls back the whole transaction).
  Integration-event mapping/outbox staging happens before commit, in the same transaction, where
  ADR-PF-011 applies. Post-commit handlers run only after a successful commit, ISOLATE_AND_CONTINUE
  (one handler's failure never blocks a sibling or un-commits already-persisted state). No
  post-commit publication ever follows a rollback or a commit failure — proven per-capability by
  each phase's own audit/commit-failure regression tests.
- UI staleness is expressed exclusively through `ViewInvalidationHint`, never a direct
  `DomainEvent` subscription from QML/a controller, and never a new `Signal[str]` field.

**26.4 Organization: FULLY MODERNIZED (P10D) — was PARTIALLY MODERNIZED, corrected not silently
upgraded, as of the original writing below.** `create_organization` is fully typed:
`OrganizationCreated` → `ViewInvalidation` → `OrganizationViewInvalidationAdapter`, zero legacy
signal involvement (confirmed: `organizations_changed` does not appear anywhere in
`create_organization`'s own source) — unchanged by P10D. As originally written here,
`update_organization`/`set_active_organization` — never in P5A's scope — still emitted the direct,
un-bridged `organizations_changed` signal, consumed directly by `settings_workspace_controller.py`
and `admin_console/domain_event_binder.py`; no `OrganizationUpdated`/`OrganizationActivated` event
had been invented to close that gap.

**P10D closed it correctly, not with the forbidden shortcut:** `update_organization` now records
`OrganizationProfileUpdated` (profile field changes) and/or `OrganizationEnabled`/
`OrganizationDisabled` (availability changes, matching P10A's `is_enabled` semantics) as
appropriate — never a generic `OrganizationChanged`/`OrganizationUpdated` blanket event, and never
`OrganizationActivated`/`OrganizationSelected`/`TenantActiveOrganizationChanged` (P9A-R/P10A/P10B/
P10C already settled that session-context selection is not a business fact and stays outside
`DomainEvent` vocabulary entirely — `TenantContextService.set_active_organization` still produces
none of these events). `enable_organization`/`disable_organization` record the same two
availability events directly. All three route through the same canonical `OrganizationUnitOfWork`
`uow.record_event(...)` pre-commit pattern `OrganizationCreated` established — no aggregate
refactor, no new UoW ownership model. Both consumers (`settings_workspace_controller.py`,
`admin_console/domain_event_binder.py`) had their direct `organizations_changed` subscriptions
removed; both already had (from P5A/P6A) a narrow `refresh_organization_profiles()`/
`refresh_organizations()` wired to the same `OrganizationViewInvalidationAdapter`
`organizationCollectionStale` signal `OrganizationCreated` uses, so no new UI wiring was needed —
only the legacy subscription removal. `organizations_changed` is now deleted from `DomainEvents`
entirely (zero producers, zero consumers, zero remaining allowlist members referencing it as
current).

**26.5 Legacy `Signal[str]` allowlist policy — frozen, growth-blocked, deletion-open.** 26 fields
remain on `DomainEvents` (`src/core/shared/events/domain_events.py`), enumerated exactly in §27's
ledger and guarded by `test_p8_platform_event_architecture_canonicalization.py`'s allowlist test
(`current_signal_names ⊆ frozen_allowlist`, never `==`) — a newly-added field not in the frozen
set fails; deleting an allowlisted field (the expected outcome of each future capability's own
semantic migration) always passes. These are grandfathered existing capabilities, not an approved
mechanism for new work (§26.3). `admin_console/domain_event_binder.py` is classified as a
**legacy-signal presentation coordinator** (direct-wired, real composite-refresh responsibility),
never a generic compatibility bridge — its own "R2" removal remains separate, future work, not
performed in P8.

**26.6 P6's `ScopedViewInvalidationSubscription` composition choice, confirmed as the shared
mechanics-only seam.** All five capability Qt adapters (Organization, Module Entitlement,
RoleBinding, Tenant Membership, Approval) compose one or two instances of this helper rather than
inheriting from a shared `QObject` base — chosen because each adapter's own Qt signal name is
deliberately distinct presentation vocabulary, and RoleBinding's polymorphic scope model needs two
simultaneous subscriptions (tenant-wide + exact-organization) that would strain a single-
subscription base class. The helper owns subscribe/replace-filter/dispose lifecycle mechanics
only — no capability names, no `DomainEvent` imports, no tenant/org discovery, no controller
refresh methods, confirmed unchanged by P7A/P7B/P7C's own architecture guards.

**26.7 `domain_events` singleton status: LEGACY-ONLY, not removable yet.** Still constructed and
still live (26 real signal fields with real producers and consumers depend on it) — new Platform
typed-event infrastructure (the five capabilities in §26.2) has zero dependency on it, confirmed
by each capability's own mapper-module architecture guard (no `domain_events` import). It may be
deleted only after the final remaining allowlisted `Signal` is semantically migrated to a typed
`DomainEvent`/deleted outright — not before.

**26.8 Explicitly deferred, not solved, by P8 (carried forward as pre-existing debt):** the ADR-004
calendar transitional dependency (§22); the `SqlAlchemyApprovalRepository → project_management`'s
`ProjectORM` concrete-import layering violation (§22, §25); observability/metrics/tracing (§18,
§25 — no telemetry work was added in P8); PM/Inventory's own extensive, still-unmigrated
`Signal[str]` usage (module-migration backlog, never a Platform-migration blocker); the seven
auth-adjacent Platform capabilities still on `auth_changed` and its siblings (§27); the four
architecture-suite baseline failures already known and unrelated to this migration (WBS/RLS/QML-
layering/size-guardrail failures, unchanged in identity across every phase's regression run).

**26.9 Pre-release migration policy, stated explicitly.** This application is pre-release: every
phase from P4-PRE Round 8 onward chose direct convergence and deletion of obsolete paths over
compatibility aliases, deprecated wrappers, or typed-event → legacy-signal bridges, except where a
genuinely still-live production dependency required temporary retention (the 26-signal allowlist
itself, and `admin_console/domain_event_binder.py`). Future per-capability migrations should
default to the same choice.

**26.10 Employee: FULLY MODERNIZED (P12A/P12B).** P12A converged `create_employee`/
`update_employee` off the shared, process-lifetime `Session` onto a canonical fresh-session
`EmployeeUnitOfWork`/`EmployeeUnitOfWorkFactory` pair (mirroring `OrganizationUnitOfWork` exactly,
including the injected `resource_repo_factory` seam so Platform's own infrastructure never imports
`project_management`'s concrete `SqlAlchemyResourceRepository` directly — only the composition
root, which already legitimately depends on both, knows that binding). P12B then recorded
`EmployeeCreated`/`EmployeeProfileUpdated` on that same UoW, pre-commit, via `uow.record_event(...)`
— no `EmployeeChanged` blanket event, no aggregate refactor. `update_employee` gained a genuine
no-op guard (mirroring P10D's `update_organization`): a call whose fields are already identical to
the persisted state performs no write, no audit entry, and records no event. Both events map onto
one new `employee_list` ViewInvalidation target, `OrganizationScope`-filtered (Employee is
organization-owned, not tenant-wide — confirmed via the same ownership check P11's audit already
established for `employees_changed`). Both legacy consumers (`admin_console/domain_event_binder.py`,
the PM Resources binder) had their direct `employees_changed` subscriptions removed. Admin Console
gained a new narrow `refresh_employees()` delegating to its existing employee sub-controller's own
`refresh()`. PM Resources needed a genuinely new narrow reload (`refresh_employee_options()`,
rebuilding only its employee picker list) rather than reusing its existing coarse `refresh()`:
`employees_changed` and `resources_changed` are NOT redundant there — an Employee profile change
with no linked PM Resource produces only the former, and `resources_changed` (PM Resource row
sync, still fully legacy, still unmodernized) already independently triggers PM Resources' full
`refresh()` whenever a linked resource is actually touched. Wiring the new `employee_list` hint to
the same coarse `refresh()` would have double-refreshed the workspace on every employee update that
also touches a linked resource; wiring it to the new narrow reload instead means exactly one
narrow-plus-one-full refresh happens on that path, never two full refreshes for one Employee
transaction — verified directly by a dedicated regression test. `resources_changed` itself is
completely untouched by this phase: still legacy, still emitted exactly where P12A left it, still
consumed exactly as before. Resource capability remains NOT MODERNIZED — this phase did not
redesign Employee↔PM-Resource synchronization, only stopped the Employee side from needlessly
double-refreshing around it. `employees_changed` is now deleted from `DomainEvents` entirely (zero
producers, zero consumers); the legacy Signal count on `DomainEvents` is 27 as of this phase,
recomputed directly from `dataclasses.fields(domain_events)` rather than incrementally adjusting
any previously-stated count.

**26.11 Department: FULLY MODERNIZED (P13A/P13B).** P13A converged `create_department`/
`update_department` off the shared, process-lifetime `Session` onto a canonical fresh-session
`DepartmentUnitOfWork`/`DepartmentUnitOfWorkFactory` pair. Both of Department's cross-entity
dependencies (`SiteRepository` for site-organization validation, `EmployeeRepository` for
manager-employee validation, plus `DepartmentRepository` itself for parent-department validation)
are Platform-owned, so — unlike Employee's `resource_repo_factory` injection seam — no
cross-module layering workaround was needed. A P13A-FIX pass closed a real integrity gap found
during that convergence: manager-employee validation originally checked only that the Employee
existed, not that it belonged to the active organization; both `create_department` and
`update_department` now resolve the manager through the UoW's own organization-scoped
`EmployeeRepository.get_for_organization(...)`, reusing the existing `DEPARTMENT_MANAGER_INVALID`
error rather than inventing a new one. P13B then recorded `DepartmentCreated`/
`DepartmentProfileUpdated` on that same UoW, pre-commit, via `uow.record_event(...)` — no
`DepartmentChanged` blanket event. `update_department` gained a genuine no-op guard: a call whose
user-controlled fields (code/name/description/site/parent/type/cost-center/manager/active/notes)
are already identical to the persisted state performs no write, no audit entry, records no event,
and — critically, since P13A had preserved an unconditional `updated_at=datetime.now(...)` bump on
every update — no longer bumps `updated_at` either; the candidate is built without the timestamp
touch, compared field-by-field, and the timestamp is only applied once a real change is confirmed.
Both events map onto one new `department_list` ViewInvalidation target, `OrganizationScope`-
filtered (Department is organization-owned, matching Employee's own scope choice). Department had
only one legacy consumer (Admin Console, per P11's audit — unlike Employee's dual-consumer case,
no duplicate-refresh concern existed here): its direct `departments_changed` subscription was
removed from `admin_console/domain_event_binder.py`, and a new narrow
`AdminConsoleController.refresh_departments()` (delegating to the existing Department
sub-controller's own `refresh()`, the narrowest existing refresh path — no full-workspace
cascade) was wired to a new `DepartmentViewInvalidationAdapter` in `context.py`, mirroring the
Employee/Organization adapter pattern exactly. `departments_changed` is now deleted from
`DomainEvents` entirely (zero producers, zero consumers); the legacy Signal count is 26 as of this
phase, recomputed directly from `dataclasses.fields(domain_events)`.

**26.12 Site: FULLY MODERNIZED (P14A/P14B).** P14A converged `create_site`/`update_site` off the
shared, process-lifetime `Session` onto a canonical fresh-session `SiteUnitOfWork`/
`SiteUnitOfWorkFactory` pair — the smallest of the four UoWs, since Site has no cross-entity
dependency at all beyond its own organization-ownership check. A P14A-FIX pass reverted a mistaken
architecture line-budget increase on `site_service.py` (360→400): the file's 383→385-line growth
across P14A was 2 real lines against a pre-existing, already-violated budget, not a new breach
caused by the migration; the budget was restored to 360 and the pre-existing breach left visible.
P14B then recorded `SiteCreated` on create, and on update recorded `SiteProfileUpdated` and/or
`SiteEnabled`/`SiteDisabled` depending on which of two independent, correctly-distinguished
concepts actually changed: Site's fifteen ordinary profile fields, and its one genuine lifecycle
concept (`is_active`, with `opened_at`/`closed_at`/`status` as automatic derived side-effects of
that single boolean, never independently-triggerable states — deliberately not modeled as
`SiteOpened`/`SiteClosed`, which would have invented lifecycle vocabulary the domain doesn't have).
A retroactive `opened_at`/`closed_at`/`status` correction made without an accompanying `is_active`
flip still counts as a genuine profile change, since nothing about availability actually
transitioned. `update_site` gained the same no-op discipline as Department: a call identical to the
persisted state on every relevant field records zero events, zero audit entry, zero write, and
does not bump `updated_at`. Both events map onto one new `site_list` ViewInvalidation target
(`OrganizationScope`); because a single mixed update can legitimately record two typed events in
one commit, the `site_list` handler deduplicates by the UoW's own `DomainEventContext
.correlation_id` so one Site mutation never produces more than one `site_list` hint — the two
business events themselves are still both published individually on the post-commit bus. To keep
`site_service.py` under its (deliberately untouched, per explicit instruction) 360-line budget once
this event-recording logic was added, `create_site`/`update_site` were extracted into a sibling
`site_commands.py` module (with `site_context.py`/`site_utils.py` helpers), mirroring the
`department_commands.py` split Department already used — `site_service.py` now only owns
construction and the read-only query surface. All five prior `sites_changed` consumers were
individually re-audited rather than mechanically rewired: Admin Console got a new narrow
`refresh_sites()` (delegating to its existing Site sub-controller's own `refresh()`); Inventory,
Pricing, and Procurement each have a genuine, narrow dependency on `site_options` and (since
storeroom option labels embed the owning site's name) `storeroom_options`, so each gained a new
`build_site_reference_options()`/`refresh_site_options()` pair and its own
`SiteViewInvalidationAdapter` instance, wired inside a ViewInvalidation seam built from scratch for
`InventoryProcurementWorkspaceCatalog` (which had none before this phase — no
`_view_invalidation_channel`, no tenant/organization-id resolution helpers; a new local
`resolve_active_organization_id_from_runtime_api`-equivalent was added under
`inventory_procurement/controllers/common/` rather than cross-importing PM's own copy, to avoid an
Inventory↔PM business-module coupling); Reservations had zero real Site dependency anywhere in its
controller or presenter and was simply dropped from `sites_changed`'s subscribers with no
replacement wiring at all. `sites_changed` is now deleted from `DomainEvents` entirely (zero
producers, zero consumers); the legacy Signal count is 25 as of this phase, recomputed directly
from `dataclasses.fields(domain_events)`. Two pre-existing, out-of-scope items remain unchanged and
undisturbed by this phase: the Site ORM's non-timezone-aware `DateTime` columns
(`opened_at`/`closed_at`/`created_at`/`updated_at`) — the root cause of a known naive-vs-aware
`TypeError` whenever a previously-persisted, previously-active site is deactivated, reproduced
identically before and after both P14A's and P14B's own changes — and Inventory's own business
events, which remain fully legacy; this phase modernized only Site's producer side and its
consumers' Site-specific reaction, never Inventory/Pricing/Procurement/Reservations' own domain
events.

**26.13 Party: FULLY MODERNIZED (P15A/P15B).** P15A converged `create_party`/`update_party` off
the shared, process-lifetime `Session` onto a canonical fresh-session `PartyUnitOfWork`/
`PartyUnitOfWorkFactory` pair, mirroring Employee/Department/Site's own UoW shape exactly. P15B
then recorded `PartyCreated` on create and `PartyProfileUpdated` on update, pre-commit, via
`uow.record_event(...)` — Party has no genuine lifecycle-availability split the way
Organization/Employee/Department/Site do; its `is_active` flag is treated as an ordinary profile
field, folded into the same `profile_changed` check as every other field, never a separate
`PartyEnabled`/`PartyDisabled` pair. `update_party` has the same no-op discipline as its
predecessors: a call identical to the persisted state on every relevant field records zero events,
zero audit entry, zero write, and does not bump `updated_at`. Both events map onto one new
`party_list` ViewInvalidation target (`OrganizationScope`).

This phase found the typed-event producer side (P15A's UoW convergence, and the
`PartyCreated`/`PartyProfileUpdated` recording plus the `party_list` ViewInvalidation handler
function) already committed from a prior, incomplete session — but the handler was never
subscribed to the post-commit bus in `platform_registry.py`, the `PartyViewInvalidationAdapter` Qt
adapter existed but was wired into no `context.py`, and three of four real Inventory-Procurement-
side narrow-refresh pairs (`refresh_party_options()`/`build_party_reference_options()` for
Inventory/Pricing/Procurement) existed but were likewise never wired to an adapter — while
Catalog's own `business_party_options` dependency had no narrow-refresh pair built for it at all,
and the legacy `parties_changed` signal was still live with two real, unconverted consumers (Admin
Console's composite binder, and Catalog's own binder) despite `party_service.py` no longer ever
emitting it (a real, silent regression: any party mutation stopped refreshing Admin Console's
Party page and Catalog's supplier options in production, since the swap to `uow.record_event(...)`
had removed the legacy emission without wiring its typed replacement). P15B closed all of this: the
`party_list` handler is now subscribed in `platform_registry.py` (mirroring Department/Site's own
registration exactly); `PartyViewInvalidationAdapter` is wired in `ui_qml/platform/context.py` to a
new narrow `AdminConsoleController.refresh_parties()` (delegating to the Party sub-controller's own
`refresh()`); Catalog gained its own additive `build_party_reference_options()`/
`refresh_party_options()` pair (extracted from its previously-inline `business_party_options`
construction, mirroring Inventory/Pricing/Procurement's existing shape) and its own
`PartyViewInvalidationAdapter` instance in `inventory_procurement/context.py`; Inventory, Pricing,
and Procurement's three pre-existing but unwired adapters were wired the same way. `parties_changed`
was removed from both remaining legacy consumers (Admin Console's and Catalog's own binders) and is
now deleted from `DomainEvents` entirely (zero producers, zero consumers) — the legacy Signal count
is 30 as of this phase (six Finance-family signals were added to `DomainEvents` between P14B and
this phase, outside this migration's scope, per `FROZEN_LEGACY_SIGNAL_ALLOWLIST`'s own
subset-only invariant — not touched here).

**26.14 Document + DocumentStructure + DocumentLink: FULLY MODERNIZED (P16A/P16B/P16C/P16D) —
`documents_changed` DELETED.** Document is a genuinely three-sub-capability slice, discovered by P16A's
audit rather than assumed: Document metadata, DocumentStructure (a separate repo/aggregate,
cross-referenced by `document_structure_id`, with its own Admin sub-controller), and DocumentLink
(a third, even smaller aggregate — create/delete only, never updated — shared by **two** producer
services, `DocumentService` and `DocumentIntegrationService`, and referencing a business entity in
a *different* module via an opaque `(module_code, entity_type, entity_id)` tuple rather than a
typed foreign key). P16A found this shape and 9 real `documents_changed` producers (matching P11's
original count exactly, confirmed by re-audit rather than trusted); P16B converged all 9 onto one
canonical `DocumentUnitOfWork` (`.documents`/`.structures`/`.links` accessors, shared by both
services — the first capability where two application services genuinely need the same UoW
factory instance, not two separate ones) and added the no-op guards `update_document`/
`update_document_structure` had never had at all (a real pre-release behavior correction, not
preserved legacy behavior — both previously wrote/audited/emitted unconditionally on an
identical-to-persisted request).

P16C then split its own scope deliberately narrower than "all of Document": only the two
mutation categories with a genuinely simple Created/ProfileUpdated shape (Document,
DocumentStructure) were given typed events (`DocumentCreated`/`DocumentProfileUpdated`/
`DocumentStructureCreated`/`DocumentStructureProfileUpdated`, `is_active`/`is_current` folded
into `ProfileUpdated` exactly like Party — neither carries a derived-state side effect the way
Site's `opened_at`/`closed_at` did, so no `DocumentArchived`/`DocumentRestored` pair was
justified) and two new ViewInvalidation targets (`document_list`, `document_structure_list`,
`OrganizationScope`, correlation-id deduped exactly like `site_list`/`party_list`). DocumentLink's
five producers (`add_link`, `remove_link`, `register_entity_attachments`,
`link_existing_document`, `unlink_existing_document`) were deliberately left on `documents_changed`
— not a compatibility bridge, an explicitly unmodernized capability slice still using its own
pre-existing legacy signal, exactly as P16A's phase plan called for. `documents_changed` is
therefore **partially retired**: 4 of 9 original emission call sites are gone (the two `create_`/
`update_document`/`_document_structure` fact categories); the field itself stays in `DomainEvents`
(deletion is P16D's, once DocumentLink has its own typed replacement) and both of its consumers
(Admin Console's and Catalog's composite binders) are unchanged and still correctly fire for the
five remaining Link-related emissions — confirmed by re-proving both consumers still react, using
`add_link` instead of `create_document` as the trigger.

`register_entity_attachments` is the one path that straddles both slices in a single commit: for N
attachments it records N typed `DocumentCreated` events (coalesced by the shared correlation-id
dedup mechanism to exactly one `document_list` hint, since all N share the one
`DomainEventContext` from the method's single `uow_factory.create()` call) **and** still emits the
legacy `documents_changed` N times unchanged, because the same commit also creates N
unmodernized `DocumentLink` facts — deliberately not suppressed, since the Link side has no typed
replacement yet. This means Admin/Catalog currently receive one narrow `document_list` reaction
plus N legacy full-refresh reactions for one batch import — a real, visible duplicate-refresh
gap, left in place on purpose (fixing it would require the Link-scoped ViewInvalidation design
P16D owns) and explicitly not hidden or pretended away by this phase.

Admin Console gained two new narrow reactions — `refresh_documents()`/
`refresh_document_structures()`, delegating to the existing `_document_controller`/
`_document_structure_controller` sub-controllers' own `refresh()`, mirroring every prior
capability's narrow-refresh shape — wired via two new adapters
(`DocumentViewInvalidationAdapter`, `DocumentStructureViewInvalidationAdapter`). Catalog's
`available_documents` dropdown (previously inline in `build_workspace_state`, now extracted into
`build_document_reference_options()`/`refresh_document_options()`, mirroring the Party/Site
extraction shape exactly) is wired to `document_list` only — confirmed by source that Catalog's
available-documents list carries no structure metadata, so `document_structure_list` correctly
does not reach Catalog at all. Catalog's per-item `linked_documents` panel and Reservations/
Procurement's own document-link dependency remain entirely on the legacy path, explicitly deferred
to P16D along with the cross-org trust-boundary characteristic P16A found in `DocumentLink.entity_id`
(never independently organization-validated by the Document layer itself, relying on the calling
module having already done so) — neither fixed nor newly introduced here.

P16D closed the last slice: `DocumentReferenceLinked`/`DocumentReferenceUnlinked` (minimal
identity — `tenant_id`/`organization_id`/`document_id`/`module_code`/`entity_type`/`entity_id`/
`link_role`/`occurred_at`), recorded via `uow.record_event(...)` in all five DocumentLink
producers (`add_link`, `remove_link`, `register_entity_attachments`, `link_existing_document`,
`unlink_existing_document`), inside the same canonical `DocumentUnitOfWork` P16B built — no new
transaction machinery needed. The genuinely new design work was the ViewInvalidation target
itself: `document_links` needs to identify one specific cross-module business entity
(`module_code`/`entity_type`/`entity_id`), which the existing three-kind `EventScope` union
cannot express (that union is about *organizational* breadth, not entity identity) and which
`ViewInvalidationHint`'s existing `entity_type`/`entity_id` fields almost cover — Approval and
TenantMembership already use them for one-row identity — except `entity_id` here is a
cross-module *opaque* identifier, unlike every other capability's own-namespace id. Resolved by
adding one new optional field, `module_code: str | None = None`, to the shared
`ViewInvalidationHint` itself (a minimal, backward-compatible extension — every other
capability's hints simply never set it) rather than adding a fourth `EventScope` kind or
inventing a stringly-typed compound identity (`"inventory:item:123"`) or a dict payload. Each
`document_links` event produces **two** typed hints, not one: the forward shape
(`entity_type`/`entity_id`/`module_code` = the linked business entity) for
Catalog/Reservations/Procurement's own linked-document projections, and the reverse shape
(`entity_type="document"`, `entity_id` = the document's own id, `module_code=None`) for Admin's
per-document link panel — the same DocumentLink row genuinely has two independent consumers
asking two different questions ("what changed for entity X" vs. "what changed for document Y"),
so one hint shape could not serve both. Both shapes dedupe independently, keyed by
`(transaction correlation_id, target identity)` rather than correlation_id alone like every
prior single-target capability — `register_entity_attachments` can legitimately touch one shared
entity across N distinct documents in one commit, so a Site/Party-style single-slot dedup would
have wrongly collapsed N genuinely-different document-shape facts into one. Both dedup sets are
transaction-scoped (cleared on every new correlation_id), never a global/unbounded registry.

Entity-level filtering happens client-side in each consumer's own slot, comparing the hint against
whatever it currently has selected — never a per-entity re-scoping adapter. The single new
`DocumentLinksViewInvalidationAdapter` stays org-scoped only at the channel level (identical to
every other adapter) and forwards every `document_links` hint to its consumer via a
`(module_code, entity_type, entity_id)`-carrying Qt signal; Admin Console's
`AdminConsoleController.on_document_links_stale()` and Catalog's
`InventoryProcurementCatalogWorkspaceController.on_document_links_stale()` each independently
decide whether the hint matches what they currently have open before calling their own existing
narrow refresh path (`PlatformDocumentController.refreshFocus()`, and a new
`refresh_selected_item_linked_documents()` built on a new `build_selected_item_detail()` seam that
rebuilds only the selected item's own detail, not the whole catalog). This mirrors how "currently
selected" state already lives in the consuming controller, not the adapter, so no dynamic
re-scoping plumbing was needed as a user's selection changes.

Reservations' and Procurement's own `list_reservation_documents`/`list_purchase_order_documents`/
`link_document`/`unlink_document` exist at the application-service layer but were found, by source
absence (zero references anywhere under `src/ui_qml` or the desktop-API layer), to have no UI
consumer at all today — proven, not assumed, and left unwired rather than adding a refresh for
symmetry. Both already self-cover their own mutations via their own existing legacy signals
(`inventory_reservations_changed`/`inventory_purchase_orders_changed`), untouched by this
migration. Catalog's own link/unlink wrapper (`item_document_service.py`) still emits
`inventory_items_changed` unmodernized (out of scope, explicitly not touched) — the real fix this
phase made was removing `documents_changed` from Catalog's binder entirely, so a link/unlink no
longer causes two full refreshes (`inventory_items_changed` + `documents_changed`) for one action;
the new narrow `document_links` reaction is additive coverage for cross-consumer staleness
(e.g. a document linked via Admin while Catalog has the same item open), not a replacement for
Catalog's own still-legacy self-refresh path.

`register_entity_attachments` now produces, per commit of N attachments: N typed `DocumentCreated`
+ N typed `DocumentReferenceLinked` events, coalesced to exactly one `document_list` hint and
exactly one `document_links` forward-shape hint (all N share one entity target) plus N distinct
`document_links` reverse-shape hints (N genuinely distinct documents) — and zero legacy signal
emissions, `documents_changed` having been deleted entirely.

P16A's `DocumentLink.entity_id` trust-boundary finding was re-audited rather than fixed: no clean,
generic, typed cross-module entity-resolution seam exists in this codebase, and building one would
be exactly the generic entity resolver/service locator this ADR has repeatedly rejected (§9/§24).
All four real business-workflow callers (`item_document_service.link_document`/`unlink_document`,
`ReservationService.link_document`/`unlink_document`, `PurchasingService.link_document`/
`unlink_document`, `CollaborationCommentCommandMixin.post_comment`) were confirmed by source
inspection to resolve their entity through their own organization-scoped lookup
(`get_item`/`get_reservation`/`get_purchase_order`/`_require_task`) before ever calling into
`DocumentIntegrationService` — kept as caller-owned validation, now with an explicit architecture
guard proving it holds. Admin Console's manual `add_link` desktop-API path is a deliberately
different, `settings.manage`-gated free-text tool (an admin operator types `module_code`/
`entity_type`/`entity_id` directly) and is documented as exempt from this invariant rather than
silently held to a standard it was never designed to meet — a mistyped or cross-org entity_id
there produces an orphaned link row scoped to the admin's own active organization, never a
cross-tenant/cross-org data leak, since every read path re-scopes by the reader's own active
organization independently.

`documents_changed` is now deleted from `DomainEvents` entirely — zero producers, zero consumers,
field absent — the legacy Signal count is 29 as of this phase (30 minus the one deletion; no
alias, no wrapper, no deleted-signal bookkeeping, matching every prior deletion in this ledger).
The Document capability — Document, DocumentStructure, and DocumentLink — is fully modernized:
this is the last Shared Master Data slice.

**P16D-FIX correction: `module_code` moved off `ViewInvalidationHint` into a new `ResourceScope`
`EventScope` kind.** P16D's original design (previous three paragraphs, left as written for
history) resolved `document_links`' cross-module opaque-entity-identity problem by adding one new
optional field, `module_code: str | None = None`, directly to the shared `ViewInvalidationHint`
dataclass. On review this was judged to violate the hint's own canonical shape — target + typed
scope, never accumulating capability-specific optional fields — since the very next capability
needing similar cross-module resource identity would have had nowhere to put it except more
one-off optional fields on the same shared dataclass. The corrected design instead extends
`EventScope` itself to a fourth, still-generic kind: `ResourceScope(tenant_id, organization_id,
module_code, entity_type, entity_id)` — exactly one resource/entity within one organization,
identified the same generic way `OrganizationScope` identifies an organization. `module_code` here
names the *resource's own* owning module (the linked business entity's module for the forward
shape; the literal `"platform"` — the same convention `record_audit_entry(..., module="platform",
...)` already uses — for the reverse, Document-owns-itself shape), not a property of the hint's
transport. `ViewInvalidationHint` is restored to its original five fields (`scope`, `category`,
`scope_code`, `entity_type`, `entity_id`); `document_links`' `build_document_links_view_invalidation_handler`
now constructs `scope=ResourceScope(...)` for both shapes instead of `scope=OrganizationScope(...)`
plus a `module_code=` hint kwarg. Because a `ResourceScope` is a strict refinement of
`OrganizationScope` (always carries a real `organization_id`), `ExactOrganization`/
`AnyOrganizationInTenant`/`AllTenants` were each extended to match it exactly as they already
matched `OrganizationScope` — preserving `DocumentLinksViewInvalidationAdapter`'s existing
org-scoped-only channel subscription and every observable P16D behavior (both hint shapes, both
dedup sets, Catalog/Admin narrow refresh, Reservations/Procurement disposition, the caller-owned
entity-org-validation invariant, and `documents_changed`'s deletion) unchanged; `TenantWide`/
`PlatformWide` deliberately do not match `ResourceScope`, since both exist specifically to exclude
organization-scoped facts. A new `ExactResource` `ScopeFilter` was added alongside it — the
narrowest possible single-resource channel-level subscription — for any future consumer that wants
it, though no current adapter needs it (client-side entity-identity comparison in the consuming
controller remains the chosen filtering point for `document_links`, per §12's existing guidance
that presentation-state comparison belongs in the controller, not the shared contract). `EventScope`
is accordingly now a closed union of four kinds, not three; ADR-005 §12 should be read with that
correction in mind wherever it still says "three."

**26.15 Project Resource: TRANSACTION/EVENT-PIPELINE CONVERGED (P18A) — NOT YET FULLY
MODERNIZED, ViewInvalidation remains P18B.** P17's audit found `ResourceMasterChanged`/
`ResourceCapabilityChanged` already existed as real, well-designed typed vocabulary (explicit
`tenant_id`/`organization_id`, meaningful `change_type` enums), but transported through their own
module-level `Signal[T]` objects rather than the canonical pipeline, with three structurally
different, non-canonical producers: two hand-rolled `ResourceMasterUnitOfWork`/
`ResourceCapabilityUnitOfWork` classes that borrowed `ResourceService`'s own process-lifetime
shared `Session` (never creating a fresh one) and had no audit call at all, plus a third path in
`employee_service.py` that emitted only the legacy `resources_changed` Signal with no typed event
at all. P18A closed all three gaps without inventing new business vocabulary: a new
`ResourceUnitOfWork`/`ResourceUnitOfWorkFactory` pair (`src/core/modules/project_management/
{contracts,infrastructure/persistence}/uow/resources/resource_unit_of_work.py`, mirroring
`DocumentUnitOfWork`/`SqlAlchemyFinanceGovernanceUnitOfWork`'s exact shape — fresh `Session` per
operation, `resources`/`skills`/`certifications` named accessors, no repository-map/service-locator)
now owns every Resource Master and Capability mutation; the existing `ResourceMasterChanged`/
`ResourceCapabilityChanged` dataclasses were retained unchanged and are now recorded via
`uow.record_event(...)` before `uow.commit()`, dispatched through the shared transactional
(FAIL_FAST) and post-commit (ISOLATE_AND_CONTINUE) pipeline; the bespoke `Signal[T]` publishers
were deleted outright after re-confirming zero production consumers (no compatibility bridge, no
forwarding). `record_audit_entry(uow, ..., commit=False, fail_closed=True)` now runs inside the
same transaction as every mutation, closing the "no audit at all" gap P17 found — an audit
failure or a commit failure both roll back the mutation and produce zero typed event and zero
legacy signal, proven by dedicated regression tests. Update-style operations
(`update_resource`/`update_resource_skill`/`update_resource_certification`) gained true no-op
detection (build the candidate, compare to the existing record, write/audit/event/legacy-signal
only on an actual change) — a real pre-release behavior correction, since the prior code wrote
unconditionally even for an identical-to-persisted request, exactly the class of gap this ADR has
corrected in every prior phase (P16B's Document no-op guards, etc.).

The `employee_service.py` producer required its own semantic audit before any code changed:
`sync_linked_employee_resources` (`employee_support.py`) writes real `name`/`role`/`contact`
columns on the linked Resource row via `resource_repo.update(resource)` — inside Employee's own
already-canonical `EmployeeUnitOfWork` transaction (which already carries a `resources` repository
participant) — so this is a genuine Resource business-fact mutation, not merely Resource display
data going stale. The correct fix was NOT to have `employee_service.py` construct
`ResourceMasterChanged` directly: `Resource` is business-module (`project_management`) vocabulary,
and `src/core/platform/` importing it would be an uncited addition to the `GOVERNED_EXCEPTIONS`
allowlist §21/§22 established as closed (`test_platform_does_not_import_business_modules.py`'s own
`test_governed_exceptions_are_exactly_the_two_known_violations` guard would fail). Instead, Platform
defines a new `ResourceMasterEventFactory` `Protocol` (`src/core/platform/contract/interface/
master_data/employee/contracts.py`, alongside the existing `LinkedEmployeeResource` Protocol this
sync path already used) — `Callable[[LinkedEmployeeResource, tenant_id, organization_id],
DomainEvent]` — that `EmployeeService` calls if configured, never importing the concrete return
type. The concrete builder, `build_resource_master_changed_for_employee_sync`, lives in PM's own
`resource_master_events.py` and is wired into `EmployeeService` only at the composition root
(`platform_registry.py`, which — like every composition root — is outside the guarded
`src/core/platform/` scope and already imports PM's concrete `SqlAlchemyResourceRepository` for
this exact same sync path). This is the same dependency-inversion shape the `resource_repo_factory:
Callable[[Session], LinkedEmployeeResourceRepository]` collaborator already used for the read/write
side of this sync — extended, not newly invented, to cover event construction too. Employee's own
`EmployeeProfileUpdated` event and canonical UoW/audit path are unchanged.

`resources_changed` is deliberately NOT deleted by P18A and NOT yet routed through
ViewInvalidation — its 8 existing consumers are unchanged, and every one of the three producers
above still emits it, post-commit, alongside the new typed event, exactly the same temporary
dual-emission pattern P16C used for Document/DocumentStructure while DocumentLink was still
unmodernized. This duplication is explicitly temporary: P18B builds the Resource
`ViewInvalidationHandler`, cuts the 8 consumers to narrow hints, and deletes `resources_changed`
(field, all three producers, all consumers) in one direct-convergence pass, per this ADR's
pre-release policy (§26.9) — Project Resource is not marked fully modernized until then.

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
- **A nested `EventScope` hierarchy for `DomainEvent`.** Rejected per §3 for `DomainEvent`
  specifically — a business-fact dataclass reads more naturally with plain `tenant_id`/
  `organization_id` fields alongside its other plain identifiers than with a wrapped, transport-
  flavored `scope` object it never needs to filter or route by breadth. **Adopted, not rejected,
  for `ViewInvalidationHint`/`ViewInvalidationChannel`** (§12, revised this pass) — the ambiguity
  a flat `organization_id: str | None` created for a *subscriber-facing, breadth-filtering*
  contract was real, and the earlier revision's five-separately-named-methods fix was the wrong
  tool for it; a closed `EventScope` union removes the ambiguity structurally instead.
- **`schema_version` on every in-process `DomainEvent`.** Rejected per §11 — imports a
  durable-messaging concern into a mechanism that never crosses a durable boundary.
- **Correlation/causation IDs directly on every `DomainEvent`.** Rejected per §5 — pollutes
  business vocabulary with per-transaction metadata; a `DomainEventContext` owned by the
  `UnitOfWork` is the correct home.
- **Treating `ApprovalService`'s existing pattern as already "the" Unit of Work.** Rejected per
  §9/§24 — it is a logical convention over a shared session, not the physical, per-transaction
  guarantee this ADR reserves the name for; conflating the two was the original gap the audit
  found.
- **An open `uow.repository_for(contract: type[R]) -> R` method on `UnitOfWork`.** Rejected per
  §9/§24, after being proposed and then critically reviewed within this same revision — it would
  let `UnitOfWork` become a general, ambient service locator, weakening dependency visibility,
  static enforcement, and testability exactly as much as any other service locator does. Replaced
  with an explicit, declarative per-handler dependency mechanism scoped to `ApprovalService`'s own
  registration API (§24), not a feature of `UnitOfWork` itself.
- **A repository-shaped `TDeps` resolved from a generic, type-keyed binder registry (Round 6's
  original `dependencies: type[TDeps]` design).** Rejected per §24 (Round 7), after being checked
  against all 18 real apply-handler registrations and found to sit one layer below where every
  real handler actually operates (a long-lived application service, never a bare repository).
  Replaced with a module-supplied `dependencies_factory: Callable[[Session], TDeps]` registered
  per handler, which the module itself uses to reconstruct its own existing service against a
  supplied session — same visibility/no-service-locator properties, correct granularity.
- **Five separately-named `ViewInvalidationChannel` subscription methods
  (`subscribe`/`subscribe_tenant_wide`/`subscribe_across_organizations`/`subscribe_across_tenants`/
  `subscribe_to_platform_wide`).** Rejected per §12, after being proposed and then critically
  reviewed within this same revision — the method count would keep growing with any future
  filtering dimension. Replaced with one `subscribe(filter: ScopeFilter, handler)` method and a
  small, closed, independently-extensible `ScopeFilter` dataclass hierarchy.
- **Fixing the `SqlAlchemyApprovalRepository → ProjectORM` violation, or unifying the three
  controller bases wholesale, as part of this migration.** Rejected per §22/§13/§25 — genuine,
  real problems, but out of this ADR's scope; fixing them here would be uncontrolled scope creep
  into a migration that already has enough surface area.
- **A `MultiOrganizationScope`/`organization_ids: list[str]`-shaped scope for facts affecting a
  known, finite set of organizations.** Rejected per §3a — multiple individually-correct,
  organization-scoped hints are simpler to route, test, and reason about, and nothing in this
  product's current requirements evidences a need for genuine bulk multi-organization fan-out.

## Consequences

- Every module (and, per capability, Platform) gains `domain/events.py`, an
  `application/event_handlers/{transactional,view_invalidation}.py` pair, and module/capability-
  owned invalidation-hint constants.
- Every tenant-owned `DomainEvent` now carries an explicit `organization_id: str | None`, not
  just `tenant_id` — a real, structural change driven directly by this product's actual
  tenant/organization data model. `ViewInvalidationHint` represents the same distinction through a
  closed `EventScope` union (`PlatformScope`/`TenantScope`/`OrganizationScope`) instead of plain
  fields, so the ambiguity of `organization_id=None` is resolved by the type system rather than by
  convention (§3, §12).
- `ViewInvalidationChannel` collapses to **one** `notify` and **one** `subscribe` method,
  parameterized by a small, closed, independently-extensible `ScopeFilter` hierarchy — replacing
  an intermediate draft of this revision that had proposed five separately-named subscription
  methods (§12).
- `UnitOfWork` does **not** gain a general `repository_for(contract)`-style lookup — an
  intermediate draft of this revision proposed one and a critical review found it would make
  `UnitOfWork` a hidden service locator; the one genuine cross-module need
  (`ApprovalService`'s apply handlers) is met instead by an explicit, declarative dependency
  mechanism scoped to `ApprovalService`'s own registration API (§24). **Round 7 revises that
  mechanism's shape again**, after checking it against all 18 real apply-handler registrations: a
  module-supplied `dependencies_factory(session) -> TDeps` replaces the originally-specified
  repository-shaped `TDeps` resolved from a generic binder registry, since every real handler
  calls into a long-lived application service, never a bare repository. A new prerequisite phase
  (Execution Plan Phase 2A-PRE) is required before `ApprovalService` itself can migrate.
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

- A `ViewInvalidationHint(scope=OrganizationScope("A", "A1"), ...)` reaches an
  `ExactOrganization("A", "A1")` subscriber and an `AnyOrganizationInTenant("A")` subscriber, but
  **not** an `ExactOrganization("A", "A2")` subscriber, **not** a `TenantWide("A")` subscriber,
  and **not** any Tenant B subscriber (unless `AllTenants()`).
- A `ViewInvalidationHint(scope=TenantScope("A"), ...)` reaches `TenantWide("A")` and
  `AnyOrganizationInTenant("A")` subscribers, but **not** any `ExactOrganization("A", ...)`
  subscriber for any organization value.
- `AllTenants()` receives hints from every tenant, any scope kind except `PlatformScope`;
  `PlatformWide()` receives only `PlatformScope`-scoped hints and never a tenant-scoped one.
- **`TenantScope("A", organization_id="A1")` and `OrganizationScope("A")` (missing
  `organization_id`) are both construction-time errors** — the type system, not a runtime check,
  makes an organization-scoped fact without an organization, or a tenant-wide fact with one,
  structurally impossible to construct (§12).
- A mutation known to affect exactly `{A1, A2}` within Tenant A, not A3, is represented as two
  `OrganizationScope`-scoped hints (`Hint(A, A1)`, `Hint(A, A2)`) — **never** as a single
  `TenantScope(A)` hint — and neither reaches an `ExactOrganization("A", "A3")` subscriber (§3a),
  directly tested as its own case distinct from the genuinely-tenant-wide case above.
- A `TenantScope`/`PlatformScope` hint is only ever produced by an explicit, deliberate
  construction call at the point a genuinely tenant-wide or platform-wide fact is known — never
  derived implicitly from an organization-scoped fact whose organization happened to be omitted.
- An organization-scoped `DomainEvent` constructed with `organization_id=None` where the event's
  own type declares it required is a construction-time type error, not a runtime surprise (§3).
- A transactional handler loading and mutating a second aggregate that itself records a new event
  causes that event to be discovered and dispatched in a subsequent round (§10), directly tested.
- `PostCommitEventHandler`'s context parameter carries the same `correlation_id` the triggering
  `UnitOfWork` was constructed with.
- Integration-event mapping (where a module opts an event into it) happens strictly before
  `uow.commit()`, and a rolled-back transaction produces zero outbox rows for that event.
- An event genuinely produced by an aggregate's own state transition, recorded instead via
  `uow.record_event(...)` by mistake, is caught by the Phase P5 per-event reviewer checklist (§6)
  — demonstrated by one worked aggregate-recorded example and one worked, justified
  orchestration-authored example, not merely asserted.
- `ApprovalService`'s apply handler receives a fully-constructed `deps: TDeps`, produced by exactly
  the `dependencies_factory` it declared at registration, called with the *same* fresh session as
  the triggering `approve_and_apply` call — and no handler can reach a collaborator (service or
  repository) it did not obtain through that declared factory (§24) — proven by a test asserting a
  handler's declared `dependencies_factory` is the only way it obtains its collaborators, not an
  incidental fact about the current implementation.

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

6. **(New, Round 7) Whether the 8 PM/Inventory apply-handler-backing services can be made
   session-parameterizable without a genuinely invasive change to their own module's composition
   code** — the investigation found `build_repository_bundle(session)` already de-risks the
   repository layer, but no equivalent factory exists yet at the service layer, and this has not
   been attempted for any of the 8 services. **DEFERRED — BLOCKING for Phase P4 specifically**
   (Execution Plan Phase 2A-PRE must complete and be reviewed first), **not blocking** for this
   ADR's other phases (P0-P3, P5-P8) or for this ADR being marked Accepted.
