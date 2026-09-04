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

**26.15 Project Resource: FULLY MODERNIZED (P18A/P18B) — `resources_changed` DELETED.** P17's audit found `ResourceMasterChanged`/
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

`resources_changed` was deliberately NOT deleted by P18A — its 8 existing consumers were left
unchanged, and every one of the three producers emitted it, post-commit, alongside the new typed
event, exactly the same temporary dual-emission pattern P16C used for Document/DocumentStructure
while DocumentLink was still unmodernized.

**P18B closed the loop.** Two `ViewInvalidation` targets, both source-justified rather than
mapped mechanically: `resource_list` (`OrganizationScope`, `src/core/modules/project_management/
application/resources/event_handlers/view_invalidation.py`) for every `ResourceMasterChanged`
change type, and `resource_capabilities` (`ResourceScope` — `tenant_id`/`organization_id`/
`module_code="project_management"`/`entity_type="resource"`/`entity_id`) for every
`ResourceCapabilityChanged`. The two-target split, not one coarse `resource_changed` target, was
proven from source, not assumed: the Resources workspace's own list-row builder never reads
skill/certification data, so a capability change correctly never needs to invalidate the list.

**Dedupe identity is derived from each target's own scope identity, not raw event fields
(P18B-FIX)** — the first pass wrongly keyed `resource_list`'s dedupe by `(correlation_id,
resource_id)`, the same shape as `resource_capabilities`, which would have let two different
resources changing within one transaction produce two `resource_list` hints for what is
structurally the *same* org-wide target. Corrected: `resource_list` dedupes by
`(correlation_id, scope_code, tenant_id, organization_id)` — `OrganizationScope` carries no
per-resource identity, so two resources in one transaction correctly collapse to one hint;
`resource_capabilities` dedupes by `(correlation_id, scope_code, tenant_id, organization_id,
module_code, entity_type, entity_id)` — `ResourceScope` *does* carry exact-resource identity, so
two different resources' capability changes in one transaction correctly stay two hints. Both
built via small local helper functions deriving the dedupe key from the constructed `EventScope`
object itself, per this ADR's general rule: dedupe identity is (transaction correlation_id) +
(ViewInvalidation target/scope identity), never a capability-specific bag of raw event fields. A
new `ResourceViewInvalidationAdapter` (`src/ui_qml/platform/adapters/`, the established shared
adapters home regardless of which capability's handler backs it —
`DocumentLinksViewInvalidationAdapter` already set this precedent) exposes
`resourceListStale`/`resourceCapabilitiesStale`, org-scoped at the channel level exactly like
every other adapter.

All 8 original consumers were re-audited from current source (a dedicated fork per consumer
group), not assumed unchanged from P17: the main Resources workspace controller (`resource_list`
→ `refresh()`; `resource_capabilities` → `reload_skills_and_certs()`, entity-id-gated to the
selected resource — resolving P17's own finding of two redundant, unconditional
`resources_changed` subscriptions firing together on every event regardless of relevance);
Dashboard, Portfolio, Scheduling, Tasks, `ResourceTimesheetsController`, and the timesheets
review-queue workspace (`TimesheetsWorkspaceController`) all subscribe to `resource_list` only,
each via its own `ResourceViewInvalidationAdapter` instance (the established per-consumer
pattern, not a shared fan-out) connected to that controller's own existing `refresh()` — none had
a genuine `resource_capabilities` dependency, confirmed from their own presenter/query source
(resource name/capacity/options only, never skill/certification fields); Platform's Control
workspace subscription was removed entirely with no replacement, since no real Resource
dependency existed there at all (an "incidental" P17 classification, confirmed). None of the 6
non-Resources-workspace consumers gained a narrower-than-`refresh()` reaction — no existing seam
was found, and building one would mean redesigning each of those *other* capabilities' own
presenter/query shape, explicitly out of P18B's scope. This is still a real, provable reduction
from pre-P18B behavior: none of the 6 react to `ResourceCapabilityChanged` at all any more (a
skill/certification edit previously triggered every one of their full refreshes too, since the
old blanket `resources_changed` signal never distinguished master from capability).

A real regression was found and fixed mid-implementation, not merely mid-P18A: once Resource
Master/Capability mutations moved off the process-lifetime shared `Session` P18A's own hand-rolled
predecessor UoWs had accidentally relied on, activity-feed staging (a separate, lighter-weight
UX trail from the governance `AuditEntry`) silently stopped persisting, since it was still bound to
that old shared session. Fixed by giving `SqlAlchemyResourceUnitOfWork` its own `_activity_service`
bound to the same fresh transaction — activity-feed atomicity is now structurally guaranteed
rather than an accident of a shared session, a genuine correctness improvement over the pre-P18A
state, not merely a preserved behavior.

`resources_changed` is now deleted from `DomainEvents` entirely — zero producers (Resource
Master, Resource Capability, and the Employee sync path all removed their legacy emission), zero
consumers (all 8 re-wired to the typed targets above), field absent. The legacy Signal count is
28 as of this phase (29 minus the one deletion — confirmed source-derived, not assumed
arithmetic). The Project Resource capability — Resource Master and Resource Capability — is
fully modernized.

**26.16 Finance Forecast: FULLY MODERNIZED (P19) — `forecasts_changed` DELETED, plus a new
generic Approval seam.** P19's re-audit found `forecasts_changed` had *two* structurally
different producers, not one: `ForecastVersionService`/`ForecastGenerationService` (behind
`FinanceGovernanceCommandBoundary.forecast_version`/`.forecast_generation`, already on the
canonical `FinanceGovernanceUnitOfWork`), and a second, hidden one inside
`FinancialChangeService._apply_forecast_successor` — when an approved Financial Change with a
FORECAST impact atomically creates, submits, and approves a successor forecast, the
`financial_change.apply` participant fired `ApprovalPostCommitEvent("forecasts_changed", ...)`
through `ApprovalService`'s generic post-commit Signal-name bridge.

Three typed events, in `application/financials/forecasts/forecast_events.py`: `ForecastVersionChanged`
(`change_type` enum CREATED/SUBMITTED/APPROVED/REJECTED/DELETED, mirroring the
`ResourceMasterChanged` enum-per-family shape from §26.15), `ForecastLineChanged` (ADDED/UPDATED/
REMOVED), and `ForecastDraftGenerated` (a genuinely distinct fact — `generate_draft` atomically
snapshots planned cost/commitments/actuals/manual estimates/risk into one new forecast plus its
`ForecastSourceDecision` audit trail — but the same read-model impact as `ForecastVersionChanged
(CREATED)`). `ForecastVersionService`/`ForecastGenerationService` gained a `record_event: Callable[
[object], None] | None` constructor parameter, wired to `uow.record_event` at the composition root
(`build_finance_governance_operations` in `project_registry.py`) — the same shape already used by
`FinancialChangeService._record_event` for its own `submit_change` path. `update_line` gained true
no-op detection (P19 §12): the line's mutable fields are snapshotted before conditional
assignment and compared after; if none actually changed, zero repository write, zero audit, zero
event, no synthetic version bump — `update_resource`'s `replace()`-and-compare idiom (§26.15)
adapted to `ForecastLine`'s mutable (non-frozen) dataclass shape via before/after tuple
comparison instead. `command_boundary.py`'s `forecast_version`/`forecast_generation` methods no
longer call `_emit_scoped("forecasts_changed", ...)` at all; `_execute`'s `invalidation` parameter
became `Callable[[T], None] | None` so a Forecast-cutover command can pass `invalidation=None`
without inventing a no-op lambda.

Exactly two ViewInvalidation targets, both project-scoped (`application/financials/forecasts/
event_handlers/view_invalidation.py`), proven from source, not assumed: `forecast_planning`
(category="forecast" — the forecast_versions list + selected_forecast detail + forecast_lines
that back the "planning" destination's "forecasts" subsection, per
`FinancialsRefreshMixin._apply_destination_state`; the list carries each version's own `status`
field) and `forecast_approved_basis` (the downstream consumers of "whichever forecast is
currently approved" — `ReportingProfitabilityMixin.get_project_commercial_projection` →
`CostPolicyEngine` → `facts.approved_forecast`, and `performance_query.py`'s EVM/variance
basis, both of which read only the *approved* forecast, never a draft/submitted one).
`ForecastVersionChanged(change_type=APPROVED)` is the one fact that stales BOTH — it notifies
both targets as two distinct hints, never coalesced together (P19-FIX §1-2, corrected from an
initial P19 design that mapped APPROVED to `forecast_approved_basis` only, missing that the
approved version's own status transition, and the previously-approved version's transition to
SUPERSEDED, are both visible in the `forecast_planning` list too). Every other Forecast fact
(version create/submit/reject/delete, line add/update/remove, draft generation) can only ever
touch a mutable, non-approved forecast (`_require_mutable_forecast` forbids editing an approved
one), so it can only ever affect `forecast_planning` alone — that part of the split was already
correct and P19-FIX left it unchanged. This is a real, source-proven correction to pre-P19 UI
behavior, not merely a preservation of it: the legacy `_forecasts_changed` handler in
`financials_refresh_mixin.py` invalidated `{overview, planning, performance}` for *every* Forecast
event and never invalidated `commercial` at all — meaning the commercial/profitability projection
was silently stale after every forecast approval, pre-P19. The current mapping (post P19-FIX)
recomposes an equivalent destination set on approval — `forecast_planning` invalidates
`{planning}`, `forecast_approved_basis` invalidates `{overview, performance, commercial}`, a union
of `{overview, planning, performance, commercial}` — while *narrowing* every non-approval
Forecast fact down to `planning` alone, both corrections falling directly out of tracing the real
read-model dependency rather than assuming the legacy destination set was correct. The
`financial_change.apply` successor path (below) needs no second event type for this either: it
already reports the same canonical `ForecastVersionChanged(APPROVED)`, so the successor's
appearance in the `forecast_planning` list is covered by the same dual notification. Both targets
use `ResourceScope(module_code="project_management", entity_type="project",
entity_id=project_id)` — `ResourceScope` proven generic beyond Resource itself, per its
`entity_type` already being used for arbitrary business entities in `DocumentLink`'s own
ViewInvalidation handler (§26.14). Dedupe follows the P18B-FIX-corrected rule from day one: a
`(scope_code, tenant_id, organization_id, module_code, entity_type, entity_id)` target derived
from the constructed scope, cleared per transaction correlation_id — so one APPROVED event's two
targets are always two separate hints, while a repeat of the same target within one transaction
still coalesces to one.

The `financial_change.apply` producer required an architecture decision, not a mechanical port:
`ApprovalService.approve_approval_request`/`.reject` already own a real `UnitOfWork` (with
`uow.record_event`), but that `UnitOfWork` is deliberately never handed to a participant or its
`dependencies_factory` (P4 Step 2, ADR-005 §24 — "Neither ever receives the `UnitOfWork` itself").
Widening `DependenciesFactory`'s call signature to thread `record_event` through would have
touched every registered apply/reject handler across both Platform business modules that use
`ApprovalService` (PM's own five families plus Inventory/Procurement's), for the sake of one
participant — out of P19's scope and a violation of "never modify unrelated capabilities." The
chosen fix instead extends `ApprovalHandlerResult` with a second, coexisting reporting channel:
`domain_events: tuple[DomainEvent, ...] = ()`, alongside the existing `post_commit_events` legacy
Signal-name tuple. A participant that has migrated a given fact returns it here instead;
`ApprovalService` — the sole owner of the decision's `UnitOfWork` — records each one via
`uow.record_event(...)` *before* its own `uow.commit()`, so it dispatches through the same
transactional/post-commit pipeline as any other canonical event, with the same
FAIL_FAST/ISOLATE_AND_CONTINUE/rollback semantics: a participant that raises never reaches event
recording; a transactional handler failure or a commit failure yields zero published event.
`FinancialChangeApprovalParticipant.apply()` now builds `ForecastVersionChanged(
change_type=APPROVED, ...)` directly when `change.applied_forecast_id` is set — the same
canonical vocabulary the direct `ForecastVersionService.approve_forecast` path uses, not a second,
approval-specific event type, because the business semantics genuinely overlap: both are "this
forecast is now the project's approved ETC basis." `dependencies_factory`'s call signature is
completely unchanged; Inventory/Procurement's approval dependency factories were not touched. The
two Approval reporting mechanisms coexist, capability-by-capability, with no bridge between them —
every other Approval participant (Budget, Task, Baseline, Billing Preparation, Project Cost, and
Financial Change's own non-Forecast branches) still reports exclusively through
`post_commit_events`, unchanged.

`forecasts_changed` is now deleted from `DomainEvents` entirely — zero producers (both the direct
Forecast path and the financial-change-apply successor path emit only typed events now), zero
consumers (`financials_refresh_mixin.py`'s legacy subscription removed; the real UI consumer is
now a single `ForecastViewInvalidationAdapter` instance wired into
`ProjectManagementFinancialsWorkspaceController`, connected to two narrow methods —
`onForecastPlanningStale`/`onForecastApprovedBasisStale` — that each filter by the hint's project
id against the workspace's currently-selected project before invalidating their proven, narrower
destination set), field absent. `FinanceInvalidationScope` remains untouched and still carries the
other, still-legacy Finance signals (`budgets_changed`, `cost_entries_changed`,
`commitments_changed`, `rates_changed`, `financial_changes_changed`, `financial_setup_changed`,
`planned_costs_changed`, `billing_preparations_changed`) — P19 retired it from the Forecast path
only, per its own scope. The legacy Signal count is 27 as of this phase (28 minus the one
deletion — confirmed source-derived). The Finance Forecast capability is fully modernized.

**26.17 Inventory Storeroom + Storage Location: FULLY MODERNIZED (P20) —
`inventory_storerooms_changed`/`inventory_locations_changed` DELETED.** The first
Inventory/Procurement capability modernized. Both entities were on raw, hand-rolled
`self._session.commit()` mutation (`InventoryService.create_storeroom`/`update_storeroom`,
`InventoryFoundationService.create_storage_location`/`update_storage_location`), with the legacy
signal emitted manually after commit — not through any canonical pipeline. P20 also found two
real, pre-existing, unrelated-to-events bugs in the same code paths: `record_activity(self, ...)`
was silently dead code (`InventoryService`/`InventoryFoundationService` were never constructed
with an `_activity_service` at the composition root), and `update_storeroom`/
`update_storage_location` had no no-op detection at all — every update wrote, audited (well,
attempted to — see above), and emitted regardless of whether any field actually changed.

One new canonical `InventoryFoundationUnitOfWork`/`InventoryFoundationUnitOfWorkFactory`
(`.storerooms`/`.locations` accessors, `src/core/modules/inventory_procurement/{contracts,
infrastructure/persistence}/uow/inventory/inventory_foundation_unit_of_work.py`, matching this
module's own established `PurchaseOrderSubmissionUnitOfWork`/`RequisitionSubmissionUnitOfWork`
shape) now owns both. It also carries a fresh, transaction-bound `EnterpriseAuditService` —
`record_audit_entry(uow, ...)` is a new addition for these two capabilities, not merely a
convergence, since Inventory's older CRUD paths never had governance audit trail coverage — and
a fresh `ActivityService`, finally making `record_activity` genuinely fire (and atomically, unlike
its previously-dead, previously-non-atomic state).

Domain semantics were audited, not assumed: Storeroom carries a genuine four-state lifecycle
(`STOREROOM_STATUS_TRANSITIONS`: DRAFT→ACTIVE→{INACTIVE,CLOSED}, INACTIVE→ACTIVE, CLOSED
terminal), enforced by `validate_transition` — a real lifecycle operation, not merely a mutable
profile field — so it gets its own `StoreroomStatusChanged(status: str, ...)` event, an
enum-payload shape (mirroring `ResourceMasterChanged`'s `change_type` from §26.15) rather than
one dataclass per transition. Storage Location's `is_active` boolean, by contrast, has no derived
consequences at all (no `opened_at`/`closed_at` side effects the way Site's does — §26.12), so
it stays folded into `LocationProfileUpdated`, per this ADR's own rule: model a lifecycle event
only when a flag has a real lifecycle operation or derived consequences, not merely because it
exists. Five typed events total: `StoreroomCreated`, `StoreroomProfileUpdated`,
`StoreroomStatusChanged`, `LocationCreated`, `LocationProfileUpdated` — no
`StoreroomChanged`/`LocationChanged`/`InventoryFoundationChanged` blanket type. Neither entity
carries a `tenant_id` column (Inventory/Procurement is organization-scoped only, with tenant
resolved via RLS at the ORM layer); events derive `tenant_id` from the active
`Organization.tenant_id`, matching `update_site`'s own established convention.

Storeroom ↔ Location integrity was audited from source, not assumed, per this phase's own
mandate: a Location's `storeroom_id` is immutable after creation (no "move between storerooms"
operation exists in `update_storage_location`'s signature at all); a Storeroom must belong to the
active organization to be referenced (`InventoryService.get_storeroom` already raises
`NotFoundError` otherwise — confirmed pre-existing and correct, no cross-org bug found); parent
Location cycles were already rejected (`_validate_parent_location`'s walk-to-root check). A
Storeroom's status transition does not cascade to its child Locations — not a cross-org integrity
bug, a business-rule completeness question outside this phase's mandate, left exactly as found.

Exactly two ViewInvalidation targets, both `OrganizationScope`
(`application/inventory/event_handlers/view_invalidation.py`): `storeroom_list` and
`location_list`. `storeroom_list` is deliberately one target covering two visually different
projections — the Inventory workspace's own Storeroom master list AND the `storeroom_options`
reference selector embedded in Pricing/Procurement/Reservations — proven from source that both
are populated from the same underlying storeroom rows and always go stale together (this ADR's
own "no target duplication for the same projection" rule, §12). `location_list` has exactly one
real consumer (the Inventory workspace) — proven from source that no other Inventory/Procurement
workspace presenter references Storage Location data at all, unlike Storeroom.

All 6 Inventory/Procurement workspaces were re-audited from source, not assumed from their
(pre-P20, byte-for-byte identical across 5 of them) blanket 11-signal subscriptions: Inventory
(the owner — full `refresh()` on either target; its own `build_workspace_state` is one monolithic
query bundling storerooms/balances/transactions/foundation together, so no narrower existing seam
could be extracted without a deeper presenter refactor outside this phase's mandate), Dashboard
(KPI rollup — full `refresh()` on either target, the same "genuinely reacts to any inventory
mutation by design, no narrower seam" justification already established for Resource's Dashboard
consumer in §26.15), Pricing and Procurement (storeroom_options selector only — both already had
an existing narrow `refresh_site_options` seam that also refreshes `storeroom_options`, reused
directly, zero new code), Reservations (storeroom_options selector only — no existing narrow seam,
so P20 additively extracted one, `refresh_storeroom_options`, mirroring Pricing/Procurement's
exact shape), and Catalog (zero real dependency — proven no Catalog presenter references
Storeroom or Location at all — the subscription was removed entirely with no replacement, the
same "classification E, no adapter" treatment §26.15 gave Platform's Control workspace for
Resource).

`inventory_storerooms_changed` and `inventory_locations_changed` are now both deleted from
`DomainEvents` entirely — zero producers, zero consumers, fields absent. The legacy Signal count
is 25 as of this phase (27 minus the two deletions — confirmed source-derived). The Inventory
Storeroom and Storage Location capabilities are fully modernized.

**26.18 Finance Financial Setup: FULLY MODERNIZED (P21) —
`financial_setup_changed` DELETED.** Transaction ownership and audit were already canonical
(the existing `FinanceGovernanceUnitOfWork`/`FinancialConfigurationService`, using
`record_audit_entry` already), matching P17's finding — no new UoW was created, per this phase's
explicit mandate. `FinancialConfigurationService` gained the same `record_event: Callable[
[object], None] | None` constructor parameter already established for `ForecastVersionService`/
`ForecastGenerationService` (§26.16) and `FinancialChangeService` (its own `submit_change` path),
wired to `uow.record_event` at the composition root.

The re-audit decomposed "Financial Setup" into three genuinely distinct sub-capabilities, not
one: `ProjectFinancialProfile` (project-owned — `configure_profile`/`transition_profile`),
`ProjectCostCode` (organization-owned, NOT project-owned — a global cost-code catalog with its
own parent/child hierarchy, referenced by projects rather than belonging to one —
`create_cost_code`/`update_cost_code`/`activate_cost_code`/`deactivate_cost_code`), and
`ProjectCostCodeRestriction` (a project-scoped join table recording which cost codes are
allow-listed for a RESTRICTED-policy project — `add_project_cost_code`/`remove_project_cost_code`).
Eight typed events for eight audited operations: `ProjectFinancialProfileUpdated`,
`ProjectFinancialProfileTransitioned` (a real status lifecycle,
`FinancialProfileStatus`-governed); `CostCodeCreated`, `CostCodeProfileUpdated`,
`CostCodeActivated`, `CostCodeDeactivated` (the last two mirroring Site's own
Enabled/Disabled-as-two-dataclasses shape, §26.12, since Cost Code's `is_active` is a genuine
binary lifecycle rather than Storeroom's richer 4-state one, §26.17); `ProjectCostCodeRestrictionAdded`,
`ProjectCostCodeRestrictionRemoved`. No `FinancialSetupChanged`/`FinanceChanged` catch-all.
`configure_profile` and `update_cost_code` had no no-op detection at all pre-P21 (always
wrote/audited/emitted on identical input) — both fixed with the same before/after
field-comparison idiom used throughout this migration (P18A §10 onward); `transition_profile`/
`activate_cost_code`/`deactivate_cost_code`/`add_project_cost_code`/`remove_project_cost_code`
already had correct existence/state guards and needed no correction.

A significant re-audit finding shaped the whole ViewInvalidation design: only `create_cost_code`
has a live production caller today, reached via a direct `commands.financial_setup(...)` call in
the Financials desktop API (`api.py`'s `create_cost_code` endpoint) — bypassing
`FinancialConfigurationService`'s own governed port entirely for that one call site. The other
seven operations (`configure_profile`, `transition_profile`, `update_cost_code`,
`deactivate_cost_code`, `activate_cost_code`, `add_project_cost_code`, `remove_project_cost_code`)
are registered in `FinanceGovernedServicePort`'s `financial_setup` mutations set (so they are real,
reachable, complete governed operations, not dead code) but have zero current UI/API callers.
`FinancialConfigurationService.get_profile`/`list_cost_codes`/`list_available_cost_codes` (the
read side) are equally uncalled from the UI today — `state.financial_profile`, the one Financial
Setup fact actually rendered (in `financials_refresh_mixin.py`'s "controls" destination, "setup"
subsection), is populated by a separate reader, not this service. All 8 operations still received
complete typed-event coverage regardless of current UI reachability — matching how every other
migrated capability's typed events describe the real business model, not merely what today's UI
happens to exercise.

Exactly one ViewInvalidation target, `financial_profile` (project-scoped `ResourceScope`,
`module_code="project_management"`, matching Forecast's own convention, §26.16), fed only by the
two Profile events. Cost Code and Restriction events are recorded as canonical typed
`DomainEvent`s — real, useful business facts for audit/history/future consumers — but
*deliberately* have zero ViewInvalidation subscription: proven from source
(`destination_builder.py` and `workspace_query.py`) that no Financials-workspace destination ever
caches a cost-code list; `search_manual_actual_cost_codes`/`search_budget_cost_codes`/
`resolve_*_cost_code` are all live, on-demand `FinanceLookupReader` queries, never a cached
projection, so a Cost Code fact has nothing to make stale. This directly corrects the legacy
signal's own over-breadth: `financial_setup_changed → {planning, costs, controls}` invalidated
three destinations for *every* Financial Setup event, including Cost Code changes, even though
none of them ever needed it — a second real, source-proven narrowing this phase found (the first
being P19-FIX's dual-target correction for Forecast approval, §26.16). Because the sole live
producer (`create_cost_code`) turns out to need zero ViewInvalidation hints, and the one
destination that Profile events *do* need (`controls`) has no live producer yet, P21's cutover is
architecturally complete but changes essentially nothing about today's actually-visible behavior
— which is itself the correct, narrow outcome once the true dependencies are traced, not a
shortfall of the migration.

`financial_setup_changed` is now deleted from `DomainEvents` entirely — zero producers (the one
real producer, `create_cost_code`, now records `CostCodeCreated` with no legacy emission; the
other seven operations never had a reachable legacy emission to retire either, since they had no
caller), zero consumers (`financials_refresh_mixin.py`'s legacy subscription removed; the real UI
consumer is a `FinancialProfileViewInvalidationAdapter` instance wired into
`ProjectManagementFinancialsWorkspaceController`, connected to `onFinancialProfileStale`, which
filters by the hint's project id and invalidates `{controls}` only — narrower than the legacy
`{planning, costs, controls}`), field absent. `FinanceInvalidationScope` remains untouched and
still carries the other, still-legacy Finance signals (`budgets_changed`, `cost_entries_changed`,
`commitments_changed`, `rates_changed`, `financial_changes_changed`, `planned_costs_changed`,
`billing_preparations_changed`) — P21 retired it from the Financial Setup path only, per its own
scope. The legacy Signal count is 24 as of this phase (25 minus the one deletion — confirmed
source-derived). The Finance Financial Setup capability is fully modernized.

**26.19 Finance Rate Card: FULLY MODERNIZED (P22) — `rates_changed`
DELETED.** The narrowest Finance capability found so far — exactly one producer file
(`rate_card_service.py`), one legacy field, one UI consumer, confirming P17's own
characterization. Unlike every other capability migrated in this ADR, Rate Card was not merely
on raw `Signal` transport; its *transaction ownership itself* was raw `Session` (P17's finding),
never routed through `FinanceGovernanceCommandBoundary`/`FinanceGovernedServicePort` at all —
confirmed from source: `project_registry.py` constructed `rate_card_service` directly, with no
`FinanceGovernedServicePort` wrap anywhere, unlike Budget/Forecast/Setup which already had one.

P22 chose Option A (§3): add a `rate_cards` named repository accessor to the existing
`FinanceGovernanceUnitOfWork`, rather than a dedicated `RateCardUnitOfWork`. Rationale: Rate Card
uses the identical `finance.manage`/`finance.read` permission model and identical audit
conventions (`record_audit_entry(..., compliance_tag="financial", commit=False)`) as every other
governance-boundary capability, and its own repository (`ProjectRateCardRepository`) already
bundles both `ProjectRateCard` and `RateCardLine` operations on one interface — the same shape
`ProjectForecastRepository` already has for `ProjectForecast`/`ForecastLine` (§26.16) — so no
"unnatural repository bag" concern applied. `ProjectRateCardService` moved off
`self._session.commit()`/`rollback()` entirely; the outer `FinanceGovernanceCommandBoundary`'s
existing `with self._uow_factory.create(...) as uow: ... uow.commit()` machinery now owns the
whole transaction, exactly like Budget/Forecast/Setup already do. A previously dead code path was
removed in the process: `_commit`'s `duplicate_message`/`IntegrityError`→`ValidationError`
conversion was never actually invoked at any of its four call sites, and `ProjectRateCardORM`
carries no unique constraint on `name` — confirmed there was never a real "duplicate rate card"
business rule being enforced; removing the dead machinery is a simplification, not a regression
(P22 §4's "preserve existing error semantics" was satisfied because there was no real semantic to
preserve).

Domain boundary audited (§2): `ProjectRateCard` (aggregate root, dual-owned — `project_id: str |
None` makes a card either organization-wide or project-specific, both persisted under the SAME
`organization_id` RLS scope) and `RateCardLine` (child entity, no separate `project_id` of its
own — resolved transitively via its parent card). Rate Card's lifecycle is asymmetric and
one-way: `create_rate_card`/`deactivate_rate_card` exist, but no rename/profile-update method and
no reactivate method exist at all — confirmed from source, not assumed — so exactly two typed
Card events: `RateCardCreated`, `RateCardDeactivated` (no `RateCardProfileUpdated`, since no such
operation exists). Lines have three: `RateCardLineAdded`, `RateCardLineUpdated` (no-op detection
added — `update_line` previously always wrote/audited/emitted on identical input, matching the
same gap found in every prior no-op-audited phase), `RateCardLineDeactivated` (already had a
correct existence guard). No vague `RatesChanged`/`RateCardChanged` catch-all.

Exactly two ViewInvalidation targets (`application/financials/rate_cards/event_handlers/
view_invalidation.py`), proven from source: `rate_card_list` (`OrganizationScope`) — the "costs"
destination's rate-card-subsection collection (`state.rate_cards`) — and `rate_card_detail`
(exact-card `ResourceScope`, `module_code="project_management"`, `entity_type="rate_card"`) — the
SAME query's `state.selected_rate_card` (detail) + `state.rate_lines` (its lines), proven to be
one combined projection, not two. `RateCardCreated` notifies only `rate_card_list` (a brand-new
card cannot be the currently-selected one). `RateCardDeactivated` notifies BOTH — the list's own
row changes AND, if that card happens to be selected, its detail's `is_active` field goes stale
too — the same dual-notification correction P19-FIX established for Forecast approval (§26.16),
applied here from day one rather than needing a follow-up fix. Line facts notify only
`rate_card_detail`, proven from source that the list query never embeds a line count or any
line-derived value.

**P22-FIX correction**: the original `OrganizationScope`-only design above was a deliberate
precision trade-off, documented as such — but it was rejected as insufficient. The corrected
design is a dual-shape scope, chosen per event from the event's own persisted `project_id`
(never inferred from UI selection state), mirroring the read model's own dual-ownership query
(`SqlAlchemyFinanceRateReader._card_conditions`: `project_id IS NULL OR project_id ==
:project_id`): an organization-wide card (`project_id is None`) still invalidates
`OrganizationScope(tenant_id, organization_id)` — every project in the organization may
refresh; a project-specific card (`project_id is not None`) invalidates a project-keyed
`ResourceScope(tenant_id, organization_id, module_code="project_management",
entity_type="project", entity_id=project_id)` instead — only that project refreshes, and a
different project's list is never touched. Project identity travels only through the hint's own
`scope`/`entity_id`, never a second field on `ViewInvalidationHint` (still no capability-specific
field, per P16D-FIX). Dedupe for the project-scoped shape reuses the same generic
`ResourceScope`-keyed dedupe helper as `rate_card_detail`, distinguished by `entity_type`
("project" vs "rate_card") within one set — both an organization-wide and a Project A-specific
change in the same transaction produce two separate hints, never collapsed.

`rates_changed` is now deleted from `DomainEvents` entirely — zero producers (the one producer,
`_commit`'s post-commit `domain_events.rates_changed.emit(...)`, is gone along with the raw
Session commit it rode on), zero consumers (`financials_refresh_mixin.py`'s legacy subscription
removed; the real UI consumer is a `RateCardViewInvalidationAdapter` instance wired into
`ProjectManagementFinancialsWorkspaceController`, connected to `onRateCardListStale`
(unconditional `{costs}`, for the organization-wide shape), `onRateCardListStaleForProject`
(P22-FIX; `{costs}` only if the hint's project is the currently selected one, mirroring
`on_forecast_planning_stale`), and `onRateCardDetailStale` (`{costs}` only if the hint's card is
the currently selected one)), field absent. `FinanceInvalidationScope` remains untouched and still carries the
other, still-legacy Finance signals (`budgets_changed`, `cost_entries_changed`,
`commitments_changed`, `financial_changes_changed`, `planned_costs_changed`,
`billing_preparations_changed`) — P22 retired it from the Rate Card path only, per its own scope.
The legacy Signal count is 23 as of this phase (24 minus the one deletion — confirmed
source-derived). The Finance Rate Card capability is fully modernized.

**26.20 PM Baseline Approval: FULLY MODERNIZED (P23) — `baseline_changed`
DELETED.** Re-audited from CURRENT source, not P17's own characterization — P17 saw only the
approval-gated create producer (`ApprovalPostCommitEvent("baseline_changed", project_id)` in
`baseline_apply_participant.py`) and described the business fact as narrowly as "approved
request created/applied a baseline." Source shows a materially richer capability: `BaselineService`
owns a full DRAFT — SUBMITTED — APPROVED/REJECTED status lifecycle
(`submit_baseline`/`approve_baseline`/`reject_baseline`, permission-gated on `baseline.manage`/
`baseline.approve`) plus `delete_baseline`, all real, UI-reachable desktop-API operations
(`ProjectManagementSchedulingDesktopApi.submit_baseline`/`approve_baseline`/`reject_baseline`/
`delete_baseline`) that emitted NOTHING at all before this phase — not `baseline_changed`,
not any other Signal — a previously silent gap distinct from `rates_changed`'s single-producer
case (P22, ADR-005 §26.19). `create_baseline` itself is dual-path: governed (via
`ApprovalService.request_change("baseline.create", ...)`, when `is_governance_required` and the
session is non-admin) or direct — both funnel through the SAME `_apply_baseline_creation_decision`,
unchanged in shape by this phase (still flush-only, still never commits its own Session).

Five typed events, one per real lifecycle transition, matching source semantics exactly:
`ProjectBaselineCreated`, `ProjectBaselineSubmitted`, `ProjectBaselineApproved`,
`ProjectBaselineRejected`, `ProjectBaselineDeleted`. `approve_baseline`'s richest fact — it
supersedes the project's previous approved baseline (if any, and if distinct from the one being
approved) and builds per-task `BaselineVarianceRecord`s in the same transaction — is represented
as ONE `ProjectBaselineApproved` event carrying a `superseded_baseline_id: str | None` field,
not two events (no `ProjectBaselineSuperseded`): no source path ever supersedes a baseline
independently of approving another one, so a separate event would describe a fact that can never
occur on its own (the "no vague catch-all, but do not multiply for technical field changes"
balance, per this phase's own §3 instruction). No `ProjectBaselineActivated` either — "approved"
and "the project's current baseline" are the same persisted fact
(`BaselineRepository.get_approved_baseline`), with no separate activation step in source.

Transaction ownership — the genuinely novel finding of this phase: `BaselineService`'s Session is
the SAME long-lived, process-shared Session most other PM services share (constructed once in
`project_registry.py`, still in use by many other services after any one Baseline operation
completes) — never a fresh per-request Session the way every Finance/Resource capability's own
canonical UoW works. `SqlAlchemyUnitOfWorkBase.commit()` unconditionally closes its Session at the
end — calling it as-is on this shared Session would silently break every other PM service still
relying on it after the very first Baseline mutation. A full convergence onto a fresh-per-request
UoW (`SchedulingEngine` and this service's four repositories all rebuilt fresh, bound to a new
Session, per call — the shape every other capability's UoW uses) was evaluated and rejected as
out of this phase's scope: `SchedulingEngine` is itself a heavy, session-bound collaborator shared
by Task/Portfolio/other Scheduling-dependent services at startup, and rebuilding it per-transaction
for Baseline's sake alone would ripple into capabilities this phase explicitly excludes ("do not
modernize Tasks," "do not redesign all PM baseline functionality"). Instead, `SqlAlchemyBaselineUnitOfWork`
(a `SqlAlchemyUnitOfWorkBase` subclass) reuses the SAME transactional-dispatch/postcommit-publish
machinery verbatim, but overrides `commit()` and `_rollback_and_close()` to skip closing the
Session — the shared Session survives every commit and rollback, proven by a real multi-operation
lifecycle test (create, then submit, then approve, all on the same long-lived `baseline_service`
instance) passing without modification. This precedent (`build_baseline_approval_deps` already
constructs a fresh `SchedulingEngine` bound to a fresh Session for the APPROVAL path specifically,
proven safe since P4-PRE) is what de-risked adding the SAME per-call construction discipline to
the DIRECT path's own small `SqlAlchemyBaselineUnitOfWorkFactory` (which wraps the existing shared
Session, not a fresh one — `BaselineService`'s own four repositories and `SchedulingEngine` did
not need to move). The approval-mediated create path itself needed zero new transaction plumbing:
already fully session-parameterized since P4-PRE (Round 8), it reuses `ApprovalHandlerResult.
domain_events` directly — the participant now returns `ProjectBaselineCreated` (built from the
created baseline's own `id` plus `TenantContext` resolved via `_require_context`) instead of the
legacy `ApprovalPostCommitEvent`; the participant still never receives a `UnitOfWork` or
`record_event` callback, matching the invariant this ADR has held since P19.

Exactly one ViewInvalidation target (`application/scheduling/baselines/event_handlers/
view_invalidation.py`): `project_baseline` (project-scoped `ResourceScope`,
`module_code="project_management"`, `entity_type="project"`). Every current consumer re-audited
from source — Scheduling workspace (baseline register/compare/variance rows, the owning
capability) and Dashboard workspace (baseline selector + KPIs scoped to the selected baseline) —
rebuilds from the same project-scoped baseline projection via a single coarse workspace refresh
(`_request_domain_refresh()`), not independently-cached sub-projections; source does not justify
splitting `baseline_schedule`/`baseline_variance` out as separate targets. All five events map to
this one target uniformly — ViewInvalidation is not a second business-event vocabulary.
The Control workspace's `baseline_changed` subscription is removed with no replacement (the same
class of finding as P18B's `resources_changed` removal): its overview/queue presenters (an
approval-request queue + an audit feed) never referenced Baseline business data at all — proven
from source, not assumed. Both narrow-workspace consumers gate on the controller's own
`_selected_project_id`, mirroring `on_forecast_planning_stale`'s established pattern (the hint's
`entity_id` matches the scope's own `entity_id`); the Qt adapter
(`BaselineViewInvalidationAdapter.projectBaselineStale`) carries the project id, never a
capability-specific field.

`baseline_changed` is now deleted from `DomainEvents` entirely — zero producers (the sole prior
producer, the approval participant's legacy `ApprovalPostCommitEvent`, is gone), zero consumers
(Scheduling workspace, Dashboard workspace, and Control workspace's subscriptions all removed or
replaced), field absent. The legacy Signal count is 22 as of this phase (23 minus the one
deletion — confirmed source-derived). The PM Baseline Approval capability is fully modernized.

**26.21 Inventory Item Catalog + Item Category: FULLY MODERNIZED (P24) —
`inventory_items_changed`/`inventory_item_categories_changed` BOTH DELETED.** Re-audited from
CURRENT source, confirming P17's own producer findings exactly: `item_commands.py`
(`create_item`/`update_item`), `category_commands.py` (`create_category`/`update_category`), and
a redundant third producer in `item_document_service.py` (`link_document`/`unlink_document`,
emitting `inventory_items_changed` on every call despite never mutating the Item row — see
below). Both capabilities used raw `Session` transaction ownership before this phase (`ItemMasterService`/
`ItemCategoryService` calling `owner._session.commit()`/`rollback()` directly), with zero
compliance audit entries ever recorded for either — only an activity-feed entry (`record_activity`,
never `record_audit_entry`), confirmed absent from source, not merely un-wired.

P24 chose Option A (§4): one coherent `InventoryCatalogUnitOfWork`/`Factory` for both `items` and
`categories`, mirroring `InventoryFoundationUnitOfWork`'s own `storerooms`/`locations` pairing
(P20, §3) exactly — Items reference Categories by code within the same organization boundary,
and both share the identical `inventory.manage`/`inventory.read` permission model, so no
"unnatural repository bag" concern applied. `ItemMasterService`/`ItemCategoryService` each
gained a `uow_factory` constructor parameter (optional, matching `InventoryService`'s own P20
shape) and a `_new_uow()`/`_require_uow_factory()` pair; their own repositories
(`_item_repo`/`_category_repo`, bound to the service's original shared Session) remain
read-only lookups, exactly like every other governed capability's pre-UoW-convergence repos —
only the fresh, per-operation `uow.items`/`uow.categories` repositories are ever written to.
Real `record_audit_entry(uow, ..., commit=False, fail_closed=True)` calls were added for the
first time in this phase, atomic with the same transaction as the mutation and its typed event.

Domain boundary audited (§2/§3): `StockItem` has a genuine DRAFT/ACTIVE/INACTIVE/OBSOLETE
status-transition lifecycle (`ITEM_STATUS_TRANSITIONS`), structurally identical in shape to
Storeroom's own (P20) — so Item's typed events mirror Storeroom's exact split:
`InventoryItemCreated`, `InventoryItemProfileUpdated`, `InventoryItemStatusChanged` (carries
`status: str`). `is_active` on `StockItem` is fully derived from `status` by a model validator
(`object.__setattr__(self, "is_active", self.status == "ACTIVE")`) — never an independent
field a caller sets, so it needed no separate handling in the profile/status split.
`InventoryItemCategory` has no such lifecycle at all: no parent/hierarchy field exists, and
`is_active` is a plain profile flag with no transition validation of its own — confirmed from
source, not assumed — so exactly two Category events: `InventoryItemCategoryCreated`,
`InventoryItemCategoryProfileUpdated` (covering every field including `is_active`). No vague
`ItemChanged`/`CategoryChanged` catch-all. True no-op detection added to both `update_item` and
`update_category` (candidate-vs-current comparison before any timestamp bump — previously
always wrote/audited/emitted on identical input, the same gap found in every prior
no-op-audited phase).

Category reference integrity (§5) audited, no bug found: `_resolve_category_reference`'s
lookup (`_category_repo.get_by_code(organization.id, category_code)`) is itself
organization-scoped, so a category code from a different organization is indistinguishable from
"not found" — a cross-organization assignment is already structurally impossible, not merely
validated after the fact. An item keeps its OWN current category across an update even if that
category later became inactive (`allow_existing_code`), but assigning a DIFFERENT category
requires it to be active — a genuine, pre-existing, deliberate business rule, left unchanged.

Exactly two ViewInvalidation targets (`application/catalog/event_handlers/view_invalidation.py`):
`item_list` (`OrganizationScope`) and `item_category_list` (`OrganizationScope`). Proven from
source that Catalog's `search_items`/`search_categories` are the SAME single query as their
respective `list_*` calls (`search_items` is an in-memory filter over `list_items`'s own rows;
`search_categories` likewise over `list_categories`) — no separately cached Item or Category
detail projection exists at all (`build_selected_item_detail` re-derives from the same full item
list on every call, never a second query), so no `ResourceScope` detail target was needed for
either capability, unlike Forecast/RateCard/Baseline's genuinely separate detail caches. Category
facts never invalidate `item_list`: `search_items`'s category label/equipment/project-usage
flags (`_category_label`, `_is_equipment_item`) are computed live, at read time, from a freshly
queried category lookup on every call — nothing is cached on the Item row that a Category change
could make stale.

Item document link/unlink duplicate publication (§12, the phase's critical finding): `item_document_service.
link_document`/`unlink_document` never mutate the Item row at all — both call ONLY
`document_integration_service.link_existing_document`/`unlink_existing_document` (P16D), which
already records typed `DocumentReferenceLinked`/`DocumentReferenceUnlinked` via `uow.record_event`
and drives the canonical `document_links` ViewInvalidation target. The `inventory_items_changed.
emit(item.id)` call previously fired on every link/unlink was pure redundant coarse publication —
confirmed, not assumed, since no Item field, version, or `updated_at` is ever touched by either
method. Removed entirely, with no replacement `InventoryItemProfileUpdated` fabricated in its
place: document linkage is a DocumentLink business fact, not an Item profile mutation. Proven
that no Item list/options/detail projection needs a second invalidation for this action: P16D's
own `document_links` target already drives Catalog's `refresh_selected_item_linked_documents()`
narrow seam, unchanged by this phase.

Six Inventory workspace binders re-audited from CURRENT source (not P17's own six-workspace
characterization, which predates P20's own incidental-subscription removals): Catalog (owner —
full `refresh()` on either target, since no narrower seam exists in its own monolithic
`build_workspace_state`, the exact same acceptance P20 already established for Storeroom/
Location — `item_list` and `item_category_list` are BOTH wired to `refresh()`, not a narrower
split, because the state builder computes items/categories/overview/filter-options together in
one call); Dashboard (`item_list` only, full `refresh()` — its low-stock rows' item labels
(`item_lookup`) are a real, source-proven Item dependency; zero Category dependency found);
Inventory/Procurement/Reservations (`item_list` only, each wired to a NEWLY EXTRACTED narrow
`refresh_item_options()` seam — mirroring the `refresh_site_options`/`refresh_storeroom_options`
pattern P20 already established for the identical class of dependency; zero Category dependency
found in any of the three); Pricing (ZERO dependency on Item or Category anywhere in its own
presenter/state builders — site/storeroom/supplier options only — subscription removed with no
replacement, the same class of finding as P18B's Control-workspace `resources_changed` removal).

`inventory_items_changed`/`inventory_item_categories_changed` are now BOTH deleted from
`DomainEvents` entirely — zero producers (all three prior producers gone: `create_item`/
`update_item`, `create_category`/`update_category`, and the redundant `item_document_service`
emission), zero consumers (all six workspace binders' legacy subscriptions removed or replaced),
both fields absent. The legacy Signal count is 20 as of this phase (22 minus the two deletions —
confirmed source-derived). The Inventory Item Catalog and Item Category capabilities are fully
modernized.

**26.22 Inventory Reorder Policy: FULLY MODERNIZED (P25) —
`inventory_reorder_policies_changed` DELETED.** Re-audited from CURRENT source: exactly one
producer method, `InventoryFoundationService.upsert_reorder_policy` (`foundation_service.py`),
confirming P17's own one-producer finding. Resolved P17's own explicitly-left-open semantic
uncertainty ("create/update may be combined into one service operation"): this IS a genuine
upsert, not two business actions disguised as one — the desktop API command itself is literally
named `InventoryReorderPolicyUpsertCommand`, and the service method looks up an existing policy
either by explicit `policy_id` (editing a known row) or by natural-key scope lookup
(`get_for_scope(organization_id, stock_item_id, storeroom_id, location_id)`, when `policy_id` is
omitted), then either creates or updates depending on whether one is found. The caller never
distinguishes the two cases. Per this phase's own §2 instruction ("do not mechanically split a
true business command merely because persistence sometimes INSERTs and sometimes UPDATEs"), one
semantic event was chosen: `InventoryReorderPolicyConfigured` — not `Created`/`Updated`.

Domain boundary audited (§3/§4): `ReorderPolicy`'s natural business identity is the composite
(organization, Item, Storeroom, optional Location) key, not `policy_id` alone — confirmed from
the repository's own `get_for_scope` signature and the IntegrityError message ("A reorder policy
already exists for the selected stock scope"), proving a real DB uniqueness constraint on this
exact tuple. `is_active` is a plain profile flag with no transition validation of its own (no
`REORDER_POLICY_STATUS_TRANSITIONS`-equivalent map exists in source) — folded into the single
Configured event, matching Category's own precedent (P24) rather than Item/Storeroom's separate
status-change event.

Transaction ownership (§5): Option A convergence — added a `reorder_policies` named repository
accessor to the EXISTING `InventoryFoundationUnitOfWork` (P20's own Storeroom + Storage Location
UoW), rather than building a new `InventoryReorderPolicyUnitOfWork` or reusing the Item-centric
`InventoryCatalogUnitOfWork` (P24). Chosen because `ReorderPolicy` is owned by the SAME
`InventoryFoundationService` class that already holds Storeroom/Location's own commands (not a
separate service), is validated against those SAME repositories
(`self._inventory_service.get_storeroom`/`self._get_location`), and uses the identical
`storeroom`-scoped `require_scope_permission` authorization model — the same transactional
cohesion criteria P20/P21/P22/P24 each applied for their own Option A choices. `upsert_reorder_policy`
moved off raw `self._session.commit()`/`rollback()` onto `self._require_uow_factory().create(...)`,
the SAME factory instance `InventoryFoundationService` was already constructed with (it had
`uow_factory`/`_require_uow_factory()`/`_new_context()` wired in already, from Location's own
prior convergence — only `upsert_reorder_policy` itself had not yet been migrated). True no-op
detection added to the update-via-scope-lookup path (candidate-vs-current comparison before any
timestamp bump — previously always wrote/audited/emitted on identical input, the same gap found
in every prior no-op-audited phase). A real compliance audit entry (`record_audit_entry(uow, ...,
commit=False, fail_closed=True)`) was added for the first time — confirmed absent from source
before this phase, only an activity-feed entry existed.

Reference integrity (§6) audited, no bug found: Item/Storeroom/Location/supplier references are
all validated through the SAME already-org-scoped lookups Storeroom/Location/Item Catalog
themselves use (`ItemMasterService.get_item`, `InventoryService.get_storeroom`,
`_validate_optional_location` — which also confirms a supplied Location genuinely belongs to the
selected Storeroom, not just the same organization). No cross-org bug existed to fix.

Exactly one ViewInvalidation target (`application/inventory/event_handlers/view_invalidation.py`,
joining Storeroom/Location's own handlers): `reorder_policy_list` (`OrganizationScope`). Re-audit
of all six Inventory workspace binders (not P17's own outdated six-workspace assumption) found
only ONE real consumer: the owning Inventory workspace's own "Foundation" panel
(`build_foundation_snapshot`, the SAME monolithic state builder that already justifies
Storeroom/Location's own full `refresh()` — P20). The other five (Catalog, Dashboard, Pricing,
Procurement, Reservations) have ZERO dependency on the `ReorderPolicy` entity at all — confirmed
a genuinely separate mechanism drives the Dashboard/Pricing "reorder required" low-stock signal:
it is computed entirely from `StockItem`'s OWN embedded `reorder_point`/`min_qty` fields at
stock-movement time (`stock_control_movements.py`), never consulting the `ReorderPolicy` table —
a genuine, pre-existing architectural gap (the deeper per-storeroom policy is not yet wired into
the live reorder decision), noted here for visibility but out of this phase's scope to fix. All
five incidental subscriptions removed with no replacement, the same class of finding as P18B's
Control-workspace `resources_changed` removal and P24's Pricing removal.

`inventory_reorder_policies_changed` is now deleted from `DomainEvents` entirely — zero
producers, zero consumers (all six workspace binders' legacy subscriptions removed, one replaced
by the typed `InventoryFoundationViewInvalidationAdapter.reorderPolicyListStale` signal wired to
the Inventory workspace's full `refresh()`), field absent. The legacy Signal count is 19 as of
this phase (20 minus the one deletion — confirmed source-derived). The Inventory Reorder
Policy capability is fully modernized.

**26.23 Purchase Order: FULLY MODERNIZED (P28B) — `inventory_purchase_orders_changed` DELETED.**
Implemented P28A's audit exactly as recommended, no deviation. `PurchaseOrderSubmissionUnitOfWork`
broadened from submit-only to ALL of create/add-line/update/submit/cancel/send/close (name kept —
same precedent as `InventoryFoundationUnitOfWork` keeping its name across P20→P25's widened
scope), gaining `purchase_order_lines`/`balances`/`_activity_service` accessors; approve/reject
stay `ApprovalService`-owned. 10 PO-owned typed events
(`InventoryPurchaseOrderCreated`/`LineAdded`/`ProfileUpdated`/`Submitted`/`Approved`/`Rejected`/
`Cancelled`/`Sent`/`Closed`/`ReceivingAdvanced`) for the 10 confirmed PO-owned facts —
document link/unlink get zero PO event (P28A/P28B §2: the PO row is never mutated by that path,
P16D's typed `DocumentReferenceLinked`/`Unlinked` was already the canonical record).

**Cross-capability event return (the core design question P28A posed):** the PO approval
participant returns BOTH `InventoryPurchaseOrderApproved` and one `InventoryRequisitionSourcingAdvanced`
(new `requisition_events.py` — Requisition's own vocabulary, not PO's) per touched Requisition, in
the SAME `ApprovalHandlerResult.domain_events` tuple (Option A). This is not a bridge: it is one
transaction — the participant already mutates `PurchaseRequisitionLine`/`PurchaseRequisition` in
the identical `ApprovalService`-owned `PlatformUnitOfWork` Session as the PO's own status change —
producing two capabilities' worth of legitimate business facts. `ApprovalService.approve_and_apply`'s
pre-existing `for domain_event in handler_result.domain_events: uow.record_event(domain_event)`
loop (already present, previously always draining an empty tuple for this family) required zero
new plumbing. Batched per touched Requisition, never per PO line — multiple PO lines sourcing the
same Requisition in one approval still produce exactly one `InventoryRequisitionSourcingAdvanced`,
mirroring the pre-existing `touched_requisition_ids` dedup the approval participant already had.
`resulting_status` is the Requisition's header status after the sourcing pass whether or not it
changed (one event, not separate PartiallySourced/FullySourced lifecycle events — "prefer minimal
vocabulary"). Balance's `on_order_qty` mutation (confirmed a real, not merely notificational,
mutation — P28A) stays on the legacy `ApprovalPostCommitEvent("inventory_balances_changed", ...)`
bridge, since Balance's own modernization is out of this phase's scope.

**Concurrency fix:** `PurchaseRequisitionLine` had no `version` column at all (domain nor ORM) —
migration `c3f6a1b8d9e0` adds one; the repository's `update()` now uses the same atomic
conditional `UPDATE ... WHERE version = :expected` (rowcount-verified, `update_with_version_check`)
already used by `PurchaseOrder`/`PurchaseRequisition`. A losing concurrent transaction raises
`ConcurrencyError`, and since the whole mutation runs inside `ApprovalService`'s own `with uow:`
block, the loss rolls back everything (PO status change included) and publishes zero postcommit
events — proven by a genuine two-Session regression test, not merely a sequential
`expected_version` retry.

**`post_receipt`** converges onto the same PO UoW; its Receipt/Balance/`StockControlService`
collaborators are constructed fresh per-transaction via a composition-owned factory
(`receiving_collaborators_factory`, injected into `PurchasingService`) rather than named UoW
accessors, avoiding both an ownership claim over Receipt/Balance and (the reason this seam exists
at all) a real circular import discovered mid-implementation: `application.procurement` importing
SQLAlchemy repositories directly pulled in `infrastructure.importers.service`, which imports back
`application.procurement`. The factory pattern mirrors `ApprovalService.dependencies_factory`
exactly.

Cross-org integrity (§24): PO approval now explicitly verifies the sourced `PurchaseRequisitionLine`'s
parent Requisition belongs to the PO's own organization — P27A/P28A both flagged this as
previously relying only on the requisition-line repository's ambient tenant-scoped query, never an
explicit assertion.

ViewInvalidation: `purchase_order_list`/`purchase_order_detail` (`OrganizationScope`/`ResourceScope`,
every PO fact notifies both — P19-FIX/P22-FIX "notify both" precedent, since Procurement's cached
detail read is field-richer than its list row and both go stale together on most facts); the
Requisition-sourcing fact reuses the exact `requisition_list`/`requisition_detail` scope shapes
P27A already proposed, so P29 inherits a working target. Consumer cutover: a new
`PurchaseOrderViewInvalidationAdapter` (mirrors `InventoryCatalogViewInvalidationAdapter`'s exact
shape) wired into Procurement (owner) and Dashboard (real KPI dependency, P28A §8); the 4
incidental legacy subscriptions (Reservations/Pricing/Inventory/Catalog) removed with no
replacement — the same class of finding P18B/P24/P25 already established for those workspaces.

A real, pre-existing bug (predates this phase — confirmed via `git show HEAD`) was found and
reported but NOT fixed (out of scope): `PurchasingService.link_document`/`unlink_document` call
`DocumentIntegrationService.link_existing_document`/`unlink_existing_document` with a `module=...`
keyword neither method accepts — these two methods have never worked in production.

`inventory_purchase_orders_changed` is now deleted from `DomainEvents` entirely — zero producers
(all 12 sites converged), zero consumers (all 6 workspace binder subscriptions removed), field
absent. The legacy Signal count is 18 as of this phase (19 minus the one deletion — confirmed
source-derived). The Purchase Order capability is fully modernized. This also unblocks Requisition
(P29): the sole non-Requisition-owned producer of `inventory_requisitions_changed` is gone.

**26.24 P28B-FIX: Requisition-sourcing ViewInvalidation had a real UI-consumer gap, now closed.**
§26.23's "so P29 inherits a working target" claim was accurate for the domain-event handler and
its `platform_post_commit_bus` wiring (both were already correct), but incomplete: no QML adapter
anywhere consumed `requisition_list`/`requisition_detail` hints — `PurchaseOrderViewInvalidationAdapter`
filters strictly on the two PO scope codes, so a Requisition-sourcing hint reached it and was
silently dropped. This meant a PO approval that sourced a Requisition stopped emitting the legacy
`inventory_requisitions_changed` (§26.23's intended change) but nothing typed replaced it in the
UI — a real regression versus pre-P28B behavior. Fixed with a new `RequisitionViewInvalidationAdapter`
(structurally identical to `PurchaseOrderViewInvalidationAdapter`), wired in `context.py` for
Procurement only; Dashboard was deliberately not wired after re-confirming from source that its
only Requisition filter (`{SUBMITTED, UNDER_REVIEW}`) is never touched by sourcing transitions.
No backend/domain/transaction code changed. Legacy Signal count unchanged at 18.

**26.25 Inventory Requisition: FULLY MODERNIZED (P29) — `inventory_requisitions_changed`
DELETED.** Implemented P27A's audit exactly as recommended (Option A extension of the existing
`RequisitionSubmissionUnitOfWork`; name kept, matching §26.23's own precedent for the identical
"broaden but don't rename" decision — unlike PO's UoW, Requisition's already carried every
accessor (`requisitions`/`requisition_lines`/`approvals`/`_enterprise_audit_service`) create/
add-line/update/cancel needed, so no new named repositories were required at all). `create_
requisition`/`add_requisition_line`/`update_requisition`/`cancel_requisition` moved off raw
`self._session.commit()` onto this canonical UoW, gaining real compliance audit for the first time
(previously activity-feed only); `update_requisition` gained a true no-op guard it never had.

Typed events: `InventoryRequisitionCreated`, `LineAdded`, `ProfileUpdated`, `Submitted`,
`Approved`, `Rejected`, `Cancelled` — 7 events for P27A's 7 confirmed facts, added to the existing
`requisition_events.py` alongside the unmodified `InventoryRequisitionSourcingAdvanced` (§26.23).
Approve/reject (`ProcurementApprovalMixin`) converted off the legacy `ApprovalPostCommitEvent`
bridge onto `ApprovalHandlerResult.domain_events`, reusing the exact same
`ApprovalService.approve_and_apply`/`reject` drain loop P28B already exercised for Purchase Order
— no new plumbing, no participant exposure to `UnitOfWork`/`record_event`.

ViewInvalidation: the handler that only ever covered the one PO-triggered sourcing event
(`build_requisition_sourcing_view_invalidation_handler`) was generalized into `build_requisition_
view_invalidation_handler`, its type union widened to all 8 Requisition event types — mirroring
`build_purchase_order_view_invalidation_handler`'s own single-handler shape for 10 PO events, one
dedupe-state pool per correlation_id rather than eight independent ones. Every event notifies both
`requisition_list`/`requisition_detail` (P19-FIX/P22-FIX/P28B "notify both" precedent). Consumer
cutover reuses §26.24's `RequisitionViewInvalidationAdapter` unchanged — no second adapter class.
Procurement's existing wiring needed no change; Dashboard gained a **new** wiring, since Requisition's
own Submitted/Approved/Rejected/Cancelled facts (unlike the sourcing-only event §26.24 evaluated)
genuinely move a Requisition into or out of Dashboard's `{SUBMITTED, UNDER_REVIEW}` "Awaiting
Approval" KPI filter — confirmed via source, not assumed from §26.24's opposite conclusion for a
different event.

A significant correction to three prior phases' own characterization: P27A/P28A/P28B all read
`_ensure_business_supplier_scope` in isolation and concluded a Requisition line's suggested
supplier was never checked for organization membership — a "real gap." Tracing its sole caller
(`_validate_supplier_reference`) one line up shows `PartyService.get_party` already scopes its own
lookup to the active organization, raising `NotFoundError` for a cross-org party before
`_ensure_business_supplier_scope` ever runs — confirmed by a real regression test constructing a
genuine cross-org Party row. No code was added for this (a second, unreachable check would be dead
code); the finding is corrected here rather than carried forward again.

`inventory_requisitions_changed` is now deleted from `DomainEvents` entirely — zero producers (all
7 remaining sites converged), zero consumers (all 6 workspace binder subscriptions removed), field
absent. The legacy Signal count is 17 as of this phase (18 minus the one deletion — confirmed
source-derived). Both Purchase Order and Requisition are now fully modernized; no next
Inventory/Procurement capability has been chosen (Reservation, Stock Balance/Ledger, Cycle Count,
and Goods Receipt remain unaudited).

**26.26 P29-FIX: Requisition invalidation precision + UI refresh coalescing — two real gaps
found and closed, no backend change.** §26.25's "every event notifies both targets" and "Dashboard
wired to `requisitionListStale`/`requisitionDetailStale`" were both real but imprecise. Re-reading
the actual read models (`to_requisition_record_view_model` for `requisition_list`,
`build_requisition_detail` for `requisition_detail`) showed `Created` can never stale an
already-open detail projection for an id that didn't exist before the transaction (corrected to
`requisition_list` only) and `LineAdded` touches no field the list row shows (corrected to
`requisition_detail` only); the remaining six event types genuinely touch both, now for a proven
reason. Re-reading `dashboard.py::build_snapshot` confirmed Dashboard's sole Requisition dependency
is the `{SUBMITTED, UNDER_REVIEW}`-filtered "Awaiting Approval" KPI — a new dedicated org-scoped
target, `requisition_pending_approval`, is notified only for Submitted/Approved/Rejected/Cancelled,
mirroring §26.16's `forecast_approved_basis` precedent (a distinct approval-summary projection,
not a screen-specific target); `RequisitionViewInvalidationAdapter` gained a third signal,
`requisitionPendingApprovalStale`, on the same adapter class (no second adapter). `Cancelled`
still notifies unconditionally since the event carries no prior-status field to filter the
"was it actually pending" case precisely — a documented, narrow exception, not a return to
blanket over-inclusion.

A third, previously-undocumented gap was found while investigating the first two:
`_request_domain_refresh()` executed `refresh()` synchronously on every call with no cross-call
coalescing, so any transaction producing 2+ Procurement-relevant hints (Requisition's own
list+detail pair from this phase, or PO's pre-existing list+detail pair from §26.23) rebuilt the
entire monolithic Procurement workspace twice. Fixed by porting `project_management`'s own
already-established `QTimer(0)`-coalesced scheduling mechanism
(`_schedule_domain_refresh`/`_execute_scheduled_domain_refresh`, gated on the app-wide
`pmEventLoopRunning` property already set in `src/ui_qml/shell/app.py`) into
`InventoryProcurementWorkspaceControllerBase` verbatim — reusing an existing generic UI scheduling
primitive, not inventing a new debounce service. `requisition_detail`'s scope stayed the exact
`ResourceScope` throughout; Procurement's own consumption remains one full monolithic refresh per
transaction (unchanged breadth, now guaranteed to fire once, not twice). No typed event, UoW,
audit, concurrency, or approval-architecture behavior changed. Legacy Signal count unchanged: 17.

**26.27 P30B: Inventory Reservation full modernization — implements P30A's audit exactly,
`inventory_reservations_changed` deleted.** New canonical `InventoryReservationUnitOfWork`/
`SqlAlchemyInventoryReservationUnitOfWorkFactory` (fresh Session per call, matching
`InventoryFoundationUnitOfWork`'s own shape) replaces the raw shared `platform_services.session`
ReservationService previously wrote through — no existing Inventory UoW naturally owned this
transaction (unlike Requisition, which had an extendable `RequisitionSubmissionUnitOfWork`), so
this is a genuinely new UoW, not an Option-A extension. Named accessors: `reservations`,
`balances`, `stock_transactions` (repos), `stock_service` (the existing, unmodified
`StockControlService` posting logic — UOM conversion, average cost, reorder threshold,
negative-quantity guards — rebound to this UoW's own session/repos rather than re-implemented, per
P30A's explicit "do not modernize Balance/Ledger" boundary), `_enterprise_audit_service` and
`_activity_service` (both newly wired — Reservation gains real compliance audit entries for the
first time, the same P24-class governance upgrade, atomic in the same commit as the Reservation/
Balance/StockTransaction writes; a monkeypatched audit-backend failure is proven, by test, to roll
back all three together and publish zero postcommit events).

Four typed events, matching P30A's semantic decomposition exactly (3 real business facts plus a
lifecycle split kept for terminal-decision clarity): `InventoryReservationCreated`,
`InventoryReservationConsumptionAdvanced` (covers both partial and full issue — `resulting_status`
distinguishes them, not a fact split; `issue_reserved_stock`'s existing quantity/transition logic
is otherwise untouched), `InventoryReservationReleased`, `InventoryReservationCancelled` (kept
distinct from Released even though both still share the `_close_reservation` implementation
helper — implementation sharing does not imply semantic-event sharing). No
`InventoryReservationProfileUpdated`/`InventoryReservationChanged` exists, matching P30A's finding
that no profile-update operation exists on this aggregate at all.

Document link/unlink: confirmed, by re-reading `link_document`/`unlink_document`, to mutate only
`DocumentLink`, never the Reservation row, Balance, or a StockTransaction — the legacy
`inventory_reservations_changed.emit(...)` call in both is deleted with no replacement Reservation
event, mirroring PO's own `link_document`/`unlink_document` (§26.23) and P24's identical Item
finding exactly. `document_integration_service.link_existing_document`/`unlink_existing_document`
already reports through P16D's own typed `document_links` ViewInvalidation target, unmodified. A
regression test proves zero Reservation DomainEvent, zero `reservation_list`/`reservation_detail`/
`reservation_open_count` hints, and an unchanged `version`/`status` from either operation.

ViewInvalidation: `reservation_list` (`OrganizationScope`) and `reservation_detail`
(`ResourceScope`, `entity_type="stock_reservation"`) — the identical shape §26.23 established for
Requisition — plus a third, narrower target, `reservation_open_count` (`OrganizationScope`),
reserved for Dashboard's "Open Reservations" KPI, mirroring §26.26's `requisition_pending_approval`
precedent (a distinct capability-summary target, not a screen-specific one). `Created` notifies
`reservation_list` + `reservation_open_count` only, never `reservation_detail` (no pre-existing
detail view can be stale for an id that didn't exist a moment ago, same reasoning §26.26 applied to
Requisition's own `Created`). `reservation_open_count` is computed precisely from the same
open-membership predicate the KPI's own query uses (`{ACTIVE, PARTIALLY_ISSUED}`): Created,
Released, and Cancelled always change membership; `ConsumptionAdvanced` only when
`resulting_status == FULLY_ISSUED` (a partial issue keeps the reservation in the counted set and
must NOT stale the KPI) — proven by two dedicated regression tests, one per issue outcome.

**Exact, source-derived event → target mapping (P30B-FIX confirms no ambiguity remains)**:

| Event | `reservation_list` | `reservation_detail` | `reservation_open_count` |
|---|---|---|---|
| `InventoryReservationCreated` | yes | no | yes |
| `InventoryReservationConsumptionAdvanced(PARTIALLY_ISSUED)` | yes | yes | no |
| `InventoryReservationConsumptionAdvanced(FULLY_ISSUED)` | yes | yes | yes |
| `InventoryReservationReleased` | yes | yes | yes |
| `InventoryReservationCancelled` | yes | yes | yes |
| document link/unlink | no (no event at all) | no | no |

Consumer cutover: Reservations workspace (owner) subscribed to `reservationListStale`/
`reservationDetailStale` via a new `ReservationViewInvalidationAdapter` (mirrors
`RequisitionViewInvalidationAdapter` exactly), full `_request_domain_refresh()` on either — same
class of acceptance already established for every other Inventory workspace's own monolithic
`build_workspace_state`. Dashboard subscribed only to `reservationOpenCountStale`. The legacy
`inventory_reservations_changed` subscription was removed outright (no replacement) from Catalog,
Pricing, Procurement, and Inventory(Foundation)'s binders — P30A proved all four had zero real
Reservation dependency; Inventory(Foundation)'s own `Stock Balances` table dependency is on
Balance, already covered by its unchanged, untouched `inventory_balances_changed` subscription.
Reservations workspace's own binder was re-audited for a Balance dependency (P30B §24's own
question, not raised in P30A): none exists — its "available stock" references are UI copy text,
not a data dependency. **P30B-FIX corrects P30B's own initial disposition here**: P30B left the
`inventory_balances_changed` subscription in place, reasoning that narrowing a Balance-signal
consumer was Balance-capability wiring and out of scope. On review this reasoning does not hold —
removing a *proven-incidental* consumer of a legacy signal is not Balance modernization (Balance's
producers, business semantics, and every other genuine consumer are untouched); it is simply
finishing the same class of cleanup already applied to Catalog/Pricing/Procurement in the same
phase. The subscription is removed, no replacement — Reservations workspace's `inventory_
balances_changed` consumer count is now 0, and its Reservation/availability UI behavior is
unchanged (it never read Balance data to begin with).

**P30B-FIX also found and fixed a genuine, previously-unverified duplicate-refresh risk unique to
Reservation**: Dashboard's `reservationOpenCountStale` was originally wired with a direct
`.connect(self._dashboard_workspace.refresh)` — the same pattern PO's/Requisition's own Dashboard
signals use. Unlike PO/Requisition, Reservation is the only capability whose typed events
co-occur, in the same transaction, with a legacy signal Dashboard *already* independently reacts
to (`inventory_balances_changed`, since Reservation genuinely mutates Balance) — so Created,
full-issue, Released, and Cancelled each risked triggering Dashboard's `refresh()` twice: once via
the direct typed-signal connection, once via the legacy binder's `_request_domain_refresh()`. Fixed
by connecting `reservationOpenCountStale` to `self._dashboard_workspace._request_domain_refresh`
instead of `.refresh` directly — the same coalescing entrypoint the legacy binder already uses,
collapsing both triggers into one rebuild per transaction under a live Qt event loop (P29-FIX's own
established remedy for this exact class of problem). PO's and Requisition's own direct-`.refresh`
Dashboard connections are untouched — P30A/P28A found neither co-emits a legacy signal alongside
its typed events, so this risk class does not apply to them.

Concurrency: P30A's audited mechanism (`update_with_version_check`, an atomic
`UPDATE ... WHERE id=? AND version=?`) is unchanged, now exercised through the canonical UoW's own
`balances` repo instead of the raw session. A genuine two-Session regression test (mirroring
§26.23's own `PurchaseRequisitionLine` race template) proves it directly: available stock 10, two
transactions each attempt to reserve 8 against the same stale read; the first commits, the second's
version-guarded write raises `ConcurrencyError` and the final persisted `reserved_qty` is 8, never
16 — no lost update, no oversubscription, not merely asserted from sequential test order.

`inventory_reservations_changed` is now deleted from `DomainEvents` entirely — zero producers (all
5 former sites converged: 3 onto typed events, 2 onto no event at all), zero consumers (all 6
workspace binder subscriptions removed), field absent. `inventory_balances_changed` is
unmodified/retained — Reservation genuinely mutates persisted Balance state and continues to emit
it exactly as before; Balance itself remains a separate, still-legacy capability, explicitly out of
this phase's scope. The legacy Signal count is 16 as of this phase (17 minus the one deletion —
confirmed source-derived). Reservation is now fully modernized; no next Inventory/Procurement
capability has been chosen (Stock Balance/Ledger, Cycle Count, and Goods Receipt remain unaudited).

**26.28 P31B: Stock Balance full modernization — implements P31A's audit exactly,
`inventory_balances_changed` deleted, distributed transaction ownership preserved.** Three typed,
field-oriented events (`domain/inventory/balance_events.py`): `StockOnHandQuantityChanged`,
`StockReservedQuantityChanged`, `StockOnOrderQuantityChanged` — chosen over a 9-event
movement-type-mirroring vocabulary (would recreate the legacy signal's own overload) and over a
single generic `StockBalanceChanged`/`InventoryStockBalanceUpdated` (would recreate the exact
imprecision this phase exists to fix). Each carries `tenant_id`/`organization_id`/`balance_id`/
`stock_item_id`/`storeroom_id`/`quantity_delta`/`resulting_quantity`/`occurred_at`;
`quantity_delta` is always computed as `resulting − previous` (a before/after `StockBalance` read,
not re-derived from a caller's line-UOM quantity) — avoids duplicating `StockControlService`'s own
UOM-to-stock-UOM conversion math at every one of the ~10 call sites that now record an event.

**No centralized Balance UoW was created — P31A's own explicit warning against one was followed.**
Each capability keeps recording its own Balance fact inside its own, already-atomic transaction:
Reservation's own `InventoryReservationUnitOfWork` (P30B, unchanged) for create/issue/release/
cancel; `ApprovalService`'s own fresh `PlatformUnitOfWork` for PO approval; the shared
`PurchaseOrderSubmissionUnitOfWork` for PO cancel and Receipt (P31A's own critical finding —
Receipt was *already* canonical, contradicting the pre-P28B characterization ADR-005 §26.23 had
carried forward; zero transaction-boundary work was needed there). Cycle Count and Inventory
(Foundation)'s manual stock movements (opening balance/adjustment/issue/return/transfer) were the
only two genuinely raw-Session paths P31A found — both converged onto the *existing*
`InventoryFoundationUnitOfWork` (P20/P25's own canonical UoW for Storeroom/Location/ReorderPolicy),
extended with `cycle_counts`/`balances`/`stock_transactions` repository accessors and a
`stock_service` accessor (the same, unmodified `StockControlService` posting logic rebound to this
UoW's own session — the identical "capability-UoW-session → fresh `StockControlService`" pattern
P30B and Receipt's own `_build_purchase_order_receiving_collaborators` factory already proved
twice). This closed a genuine composition-root circular dependency (`InventoryService` needs this
UoW factory for its own Storeroom commands per P20, while the extended factory's own
`stock_service` needs a constructed `InventoryService`) via a `configure_stock_dependencies()`
late-binding call — the factory is built first with `item_service`/`inventory_service` unset, then
configured moments later in the same composition function once both exist; every real `.create()`
call happens well after composition completes. A second, smaller circular *import* (the contracts
Protocol importing the concrete `StockControlService` class, which itself imports `InventoryService`,
which imports the contracts module) was closed with a `TYPE_CHECKING` guard — the annotation-only
reference never needed to be a runtime import.

**`StockControlService` itself is unmodified in shape** — still the dual-mode domain/invariant
service P31A characterized it as, self-committing by default, a clean `commit=False` participant
otherwise, reused verbatim by every writer. The one narrow addition: `transfer_stock` gained the
same `commit: bool = True` parameter every sibling posting method already had (previously it
unconditionally called `self._session.commit()`, which would have prematurely committed a caller's
UoW out from under it the moment a capability tried to reuse it with `commit=False`) — a one-line
signature extension matching an existing convention, not a broader refactor.

**Reservation → Balance**: unchanged mutation behavior (P30B); now records
`StockReservedQuantityChanged` (create/release/cancel) and, for `issue_reserved_stock` (which
mutates both `on_hand_qty` and `reserved_qty` in one call), both `StockOnHandQuantityChanged` and
`StockReservedQuantityChanged` — two genuine facts from one operation, not merged, mirroring PO
approval's own precedent of returning multiple `domain_events` from one participant call.

**Purchase Order → Balance**: approval records `StockOnOrderQuantityChanged` via
`ApprovalHandlerResult.domain_events` — the reflective `ApprovalPostCommitEvent("inventory_
balances_changed", balance_id)` bridge is deleted outright, not left coexisting with the typed
event. **Cancel fixes P31A's confirmed silent-mutation gap**: `cancel_purchase_order`'s on-order
reversal (only reached when cancelling a PO that was ever approved, `prior_status != DRAFT`) now
records `StockOnOrderQuantityChanged` in the same `PurchaseOrderSubmissionUnitOfWork` transaction
as its own `InventoryPurchaseOrderCancelled` event — previously this path emitted no Balance
notification of any kind, confirmed both by the P31A audit and by a dedicated regression test here
proving a real `stock_balance_list`/`stock_balance_detail` hint now fires. Rejection is confirmed,
again, to touch no Balance state (on-order was never incremented for a PO that was never
approved) — zero Balance event, not a defensive no-op event.

**Goods Receipt → Balance**: `post_receipt` records both `StockOnHandQuantityChanged` (from the
existing `StockControlService.post_adjustment` path) and `StockOnOrderQuantityChanged` (from the
existing direct-repo `_adjust_on_order_balance` path) per line, in the same already-canonical UoW;
`inventory_receipts_changed` is unmodified/retained — Receipt itself is explicitly not modernized
as a capability in this phase, per its own scope boundary.

**Cycle Count → Balance**: `complete_cycle_count` moved from raw `self._session`/the shared
`self._stock_service` instance onto the extended `InventoryFoundationUnitOfWork`; records
`StockOnHandQuantityChanged` only `if abs(variance) > 1e-9` — a zero-variance completion mutates
nothing and records nothing, preserving "counting stock ≠ changing stock" exactly as P31A required.
Gains real atomic `record_audit_entry` for the first time (previously zero enterprise audit at
all, only a best-effort, non-atomic activity-feed entry) — proven atomic by a monkeypatched
audit-failure test rolling back the Balance mutation together with it. `inventory_cycle_counts_
changed` is unmodified/retained — Cycle Count itself is not modernized as a capability.

**Manual stock movements**: `post_opening_balance`/`post_adjustment`/`issue_stock`/`return_stock`/
`transfer_stock` moved from the `movements.py` desktop API calling the raw, process-shared
`StockControlService` instance directly (self-committing, no Balance event, no atomic audit) to
calling 5 new `InventoryFoundationService` methods that open the same extended UoW, delegate to
`uow.stock_service.*(commit=False)`, record the resulting Balance fact(s), stage atomic enterprise
audit, and commit. `transfer_stock` records two independent `StockOnHandQuantityChanged` facts —
source and destination are two distinct `StockBalance` aggregate identities, not one
organization-wide "stock changed" event.

**Concurrency**: unchanged mechanism (`update_with_version_check`, atomic `UPDATE ... WHERE id=?
AND version=?`), now exercised uniformly by every writer regardless of which capability's UoW
originates the call. A genuine cross-capability two-Session regression test (mirroring §26.23's
own template) proves the P31A-flagged whole-row-versioning trade-off directly: a manual on-hand
adjustment and a reservation hold, concurrently reading the *same* balance row before either
writes (different fields, `on_hand_qty` vs. `reserved_qty`), still conflict at the version level —
the second writer's `ConcurrencyError` is raised and its change never persists, confirming the
existing safety property (never a lost update) at the cost of contention Balance's own future
design could reduce but that this phase does not attempt to.

**ViewInvalidation**: new `StockBalanceViewInvalidationAdapter` (`stockBalanceListStale`/
`stockBalanceDetailStale`), targets `stock_balance_list` (`OrganizationScope`) and
`stock_balance_detail` (`ResourceScope`, `entity_type="stock_balance"`) — identical shape to every
prior capability's own list/detail pair. All 3 event types route to *both* targets identically;
this is not a missed field-sensitivity opportunity — P31A/P31B's own field-level re-audit of every
consumer found each of the 3 confirmed-genuine ones (Inventory(Foundation)'s own Balance table +
detail panel; Pricing's stock-status report, which reads `reorder_required`/`on_order_qty`/
`reserved_qty`/`available_qty`/`average_cost` — broader than the audit's own working hypothesis;
Dashboard's "Stock Positions"/"Low Stock"/"On Order Qty" KPIs, spanning all three quantity
dimensions between them) genuinely depends on all three dimensions for *some* part of its own
single monolithic refresh. **Consumer re-audit corrects P30B's carried-forward "5 genuine
consumers" label to 3**: Catalog and Procurement are confirmed incidental — zero real Balance-field
reference anywhere in either's desktop-API or presenter layers — their legacy subscriptions are
removed outright, no replacement, proven by a dedicated zero-reaction regression test. All three
genuine consumers connect through `_request_domain_refresh`, not a direct `.refresh` connect,
matching the coalescing-safe pattern P30B-FIX established for Dashboard's own Reservation KPI.

`inventory_balances_changed` is now deleted from `DomainEvents` entirely — zero producers (all 9
former mechanisms converged: 8 direct `.emit()` sites across `stock_control_adjustments.py`/
`stock_control_movements.py`/`reservation_service.py`/`purchasing_receiving.py`/
`foundation_service.py`, plus the 1 reflective `ApprovalPostCommitEvent` bridge — including the
one confirmed-dead `_post_reservation_transaction` branch, deleted rather than converted since it
had no reachable caller), zero consumers (all 5 legacy subscriptions removed). `inventory_
receipts_changed`/`inventory_cycle_counts_changed` are unmodified/retained — Receipt and Cycle
Count remain separate, still-legacy capabilities, explicitly out of this phase's scope. The legacy
Signal count is 15 as of this phase (16 minus the one deletion — confirmed source-derived). Stock
Balance is now fully modernized; no next Inventory/Procurement capability has been chosen (Goods
Receipt and Cycle Count remain unaudited as their own capabilities).

**26.29 P32B: Inventory Cycle Count full modernization — implements P32A's own comparative
selection, `inventory_cycle_counts_changed` deleted, `schedule_cycle_count` gains atomic
transaction ownership for the first time.** Two typed, field-oriented events
(`domain/inventory/cycle_count_events.py`): `InventoryCycleCountScheduled` (`tenant_id`/
`organization_id`/`cycle_count_id`/`storeroom_id`/`occurred_at`) and `InventoryCycleCountCompleted`
(adds `variance_qty`) — chosen over a single generic `CycleCountChanged` (would recreate the
imprecision this phase exists to fix) and over a third "variance recorded" event (P32A's own audit
found no consumer reads variance independently of completion; folding it into
`InventoryCycleCountCompleted` avoids inventing a fact no reader needs).

**`schedule_cycle_count` converges onto the existing `InventoryFoundationUnitOfWork`** — the same
class `complete_cycle_count` began using in P31B, requiring zero new UoW/repository plumbing (the
`cycle_counts` accessor already existed). Previously raw `self._session.add()`/`self._session.
commit()`, with only a best-effort, non-atomic activity-feed entry and, critically, **zero**
enterprise audit of any kind — the same first-touched-raw-Session gap class P24/P30B/P31B each
closed for their own capability's first-modernized operation. Now: `uow.cycle_counts.add(...)`,
`record_activity(uow, ..., commit=False)`, a new atomic `record_audit_entry(uow, operation="create",
..., commit=False, fail_closed=True)`, `uow.record_event(InventoryCycleCountScheduled(...))`, one
`uow.commit()` — proven atomic by a monkeypatched audit-failure test rolling back the CycleCount
creation itself, not merely a downstream Balance mutation (there is none to roll back here — this
is scheduling, before any count is taken). `complete_cycle_count`'s own already-canonical shape
(P31B) is unchanged; it gains only the new `InventoryCycleCountCompleted` event recorded alongside
its pre-existing conditional `StockOnHandQuantityChanged` (still gated on `abs(variance) > 1e-9` —
Stock Balance's own event semantics, untouched by this phase).

**No lifecycle change.** `PLANNED → COMPLETED` (with `CANCELLED` as the only other terminal state)
is exactly as P30A/P31A/P32A characterized it — no start/in-progress state was invented, no cancel
operation was invented, matching this phase's own explicit scope boundary.

**ViewInvalidation**: new `CycleCountViewInvalidationAdapter` (`cycleCountListStale`/
`cycleCountDetailStale`), targets `cycle_count_list` (`OrganizationScope`) and `cycle_count_detail`
(`ResourceScope`, `entity_type="inventory_cycle_count"`) — identical shape to every prior
capability's own list/detail pair. `InventoryCycleCountScheduled` invalidates list only — mirroring
§26.26's own reasoning for Requisition/Reservation Created events, a row that did not exist a
moment ago cannot have a stale pre-existing detail view open anywhere; `InventoryCycleCountCompleted`
invalidates both. P32A's audit found Cycle Count owned by exactly one workspace
(Inventory(Foundation)) with **5 of 6** legacy subscribers confirmed incidental — the highest
incidental ratio of any Inventory/Procurement signal audited to date. Catalog, Pricing, Procurement,
Dashboard, and Reservations are removed with no replacement, proven by a dedicated zero-reaction
regression test; Inventory(Foundation)'s own subscription is replaced by the new adapter, connected
through `_request_domain_refresh`, matching the coalescing-safe pattern P30B-FIX established.

`inventory_cycle_counts_changed` is now deleted from `DomainEvents` entirely — zero producers (both
former `.emit()` sites, in `schedule_cycle_count` and `complete_cycle_count`, converted), zero
consumers (all 6 legacy subscriptions removed — 5 incidental plus Inventory(Foundation)'s own,
replaced by the typed adapter). `inventory_receipts_changed` is unmodified/retained — Goods Receipt
remains a separate, still-legacy capability, explicitly out of this phase's scope, and is the
expected next Inventory/Procurement phase per P32A's own comparison. The legacy Signal count is 14
as of this phase (15 minus the one deletion — confirmed source-derived). Cycle Count is now fully
modernized — the eighth Inventory/Procurement capability to reach that state.

**26.30 P33: Goods Receipt full modernization — `inventory_receipts_changed` deleted,
Inventory/Procurement's entire event-modernization surface COMPLETE.** One typed, fact-oriented
event (`domain/procurement/receipt_events.py`): `InventoryReceiptPosted` (`tenant_id`,
`organization_id`, `receipt_id`, `purchase_order_id`, `occurred_at`) — the business fact is "a
Receipt was posted," nothing more; it does not represent PO receiving state or Balance state, both
of which already have their own canonical typed facts (`InventoryPurchaseOrderReceivingAdvanced`
since P28, Balance facts since P31B). **Source correction to this phase's own brief**: the
suggested payload's `storeroom_id` field does not exist on `ReceiptHeader` — storeroom is a
per-*line* attribute (`destination_storeroom_id`), which can differ across a single receipt's
lines, not a Receipt-header identity field, so it was omitted.

**Transaction ownership unchanged — `post_receipt` already used the canonical
`PurchaseOrderSubmissionUnitOfWork`** (confirmed already-atomic by P28A/P31A, re-confirmed here).
The new event is simply recorded, precommit, in the same transaction as the pre-existing PO/Balance
facts, immediately before `uow.commit()`. No `GoodsReceiptUnitOfWork` was created; no Receipt
lifecycle, update, cancel, or reversal operation was invented — Receipt remains immutable-after-
post, created directly in a POSTED state, exactly as P32A characterized it.

**One receipt, one fact — proven by a dedicated multi-line, multi-item regression test.** A Receipt
spanning several lines (potentially touching several distinct Items/Balances) still records exactly
one `InventoryReceiptPosted`; Balance facts remain per affected `StockBalance` row (P31B semantics,
unchanged) and PO receiving facts remain exactly as P28 defined them (unchanged).

**ViewInvalidation — `receipt_list` only, no `receipt_detail` invented.** Source audit found
`get_receipt` is purely an internal application-layer helper (used only by `list_receipt_lines` for
scope validation) — never exposed through any desktop API, and no UI presenter fetches a single
Receipt by id. Every genuine consumer reads Receipt exclusively through list-shaped queries
(`list_receipts`/`list_receipt_lines`, optionally filtered by `purchase_order_id` at query time but
never cached as a separate per-filter projection, mirroring `reorder_policy_list`'s own precedent
for a single org-wide target with query-time filtering rather than a list/detail pair). New
`ReceiptViewInvalidationAdapter` (`receiptListStale`), target `receipt_list` (`OrganizationScope`,
category `procurement`, `entity_type="inventory_receipt"`) — a deliberate, source-justified
departure from every prior phase's list/detail-pair default, since inventing a `receipt_detail`
`ResourceScope` would have had no corresponding stale read model to invalidate.

**Consumer re-audit, field-precise, not inferred from co-occurring PO/Balance events.** All 4 of
P32A's "genuine" consumers were independently re-derived from source and confirmed still genuine,
each for a distinct, non-overlapping reason: **Procurement** (OWNER) reads `list_receipts`/
`list_receipt_lines` directly for its PO-scoped receipt-history panel and an org-wide receipt count
in its overview KPIs — the same monolithic `build_workspace_state()` already re-runs both queries on
any refresh, so one org-wide target suffices for both. **Dashboard** reads `list_receipts` directly
for a per-PO "Receipts N" count embedded in its Receiving Queue rows — genuinely Receipt-owned data,
not derivable from `InventoryPurchaseOrderReceivingAdvanced`'s own payload (`resulting_status`
only), so Dashboard is NOT fully covered by its pre-existing PO subscription despite both events
co-occurring in every `post_receipt` call. **Pricing** reads `list_receipts` (via the reporting
service) directly for its own live "Receipts" metric count in `build_snapshot` — confirmed NOT
explainable by its Balance dependency alone: Pricing's `last_receipt_at` field usage IS Balance-
derived (a field already on `StockBalance`, set by `post_adjustment`, already covered by
`StockOnHandQuantityChanged`) but the "Receipts" metric is separate, genuine Receipt data, so
Pricing was NOT reclassified as incidental despite this phase's own brief inviting that
re-classification if the dependency turned out to be Balance-only. **Inventory(Foundation)** reads
`list_receipts`/`list_receipt_lines` directly for its lot/serial/expiry tracking-signal panel
(`_tracking_signals`). **Catalog and Reservations** (INCIDENTAL) — zero Receipt-data references
anywhere in either, confirmed by source and by a dedicated zero-reaction regression test; their
legacy subscriptions are removed with no replacement.

**Six legacy binder files, all now empty stubs — deleted outright by the immediately-following
P33-CLEANUP pass (see below), not kept.** All 6 (Catalog, Procurement, Pricing, Reservations,
Inventory(Foundation), Dashboard's own inline binder) had `inventory_receipts_changed` as their
ONLY remaining subscription — the last Inventory legacy signal standing after P32B. At P33 time
each `bind_domain_events(ctrl)` function body was replaced with a documented no-op rather than
deleting the binder files/call sites outright, preserving the calling convention each controller's
`__init__` relies on while the rest of P33 was still landing. The 4 genuine consumers' real Receipt
dependency is covered instead by 4 separate `ReceiptViewInvalidationAdapter` instances (one per
consuming workspace: Procurement, Dashboard, Pricing, Inventory(Foundation)), wired through
`_request_domain_refresh` in `context.py` — mirroring the per-workspace-adapter-instance pattern
already established for the PO/Requisition adapters.

**P33-CLEANUP (structural cleanup, not a modernization phase) then deleted the no-op stubs.** Per
this document's own Pre-Release Convergence Rule (no compatibility shell, no deprecated wrapper, no
empty placeholder): the 5 free-function binder files, Dashboard's inline method, and their import/
call sites in each controller's `__init__` are gone; the now-zero-caller `_subscribe_domain_signal`/
`_disconnect_domain_event_subscriptions` legacy-Signal machinery on
`InventoryProcurementWorkspaceControllerBase` (and its now-unused `Callable`/`Any`/`DomainSignal`
imports) is gone too. The still-live `_request_domain_refresh` coalescing mechanism every typed
ViewInvalidation adapter depends on is untouched. No business behavior changed.

**§14 finding — PurchaseOrderLine concurrency, pre-existing, deliberately NOT fixed.** Source audit
confirms `PurchaseOrderLineORM` has no `version` column at all (unlike `PurchaseOrder`/`CycleCount`/
`StockBalance`/`StockReservation`/`PurchaseRequisitionLine`, all `update_with_version_check`-
protected) and `SqlAlchemyPurchaseOrderLineRepository.update()` performs a blind field overwrite.
Not new — P28A already documented it neutrally ("child PurchaseOrderLine (no own version field,
additive-only mutation)"). A repository-level two-session regression test (mirroring P31B's own
template, and directly contrasted against P28B's own `PurchaseRequisitionLine` concurrency test,
which DOES prove rejection) proves the PO-line race is real: two independent reads of the same
line's `quantity_received` before either write, followed by two independent writes, both succeed —
neither is rejected, confirming a genuine lost-update risk on concurrent same-line receiving.
Deliberately not fixed here — hardening it would require a schema migration (a new `version`
column) unrelated to and out of proportion with this phase's actual goal; neither `post_receipt`'s
per-call `outstanding` guard nor its idempotency behavior is touched by the Receipt DomainEvent/
ViewInvalidation work itself. Carried forward as an explicit, source-confirmed, unresolved
architectural note, exactly as P31A carried forward (and P31B later fixed, when directly relevant to
its own scope) the analogous PO-cancel silent-mutation gap.

`inventory_receipts_changed` is now deleted from `DomainEvents` entirely — zero producers (the one
`.emit()` site in `post_receipt` converted), zero consumers (all 6 legacy subscriptions removed — 2
incidental with no replacement, 4 replaced by the typed adapter). **Zero Inventory/Procurement
legacy Signal fields remain** — `dataclasses.fields(DomainEvents)` carries no `inventory_`-prefixed
name at all, proven by a dedicated architecture-guard test. The legacy Signal count is 13 as of this
phase (14 minus the one deletion — confirmed source-derived). Goods Receipt is now fully modernized
— the ninth and final Inventory/Procurement capability to reach that state. **Inventory/
Procurement's entire event-modernization surface is complete.** `StockTransaction` remains,
throughout, the unmodified canonical persistence ledger. This does not mark the overall (all-module)
event-modernization project complete — Project Management, Finance, and Auth/Security legacy
signals remain.

**26.31 P35: Finance Planned Cost full modernization — `planned_costs_changed` deleted, first of
P34A's Finance-first trio.** One typed event
(`application/financials/planned_costs/planned_cost_events.py`): `PlannedCostSnapshotCalculated`
(`tenant_id`, `organization_id`, `project_id`, `planned_cost_version_id`, `occurred_at`) — the
business fact is "the project's planned-cost snapshot was recalculated." `calculate_snapshot`
(confirmed, again, to be the ONLY Planned Cost write operation) always produces one new, immutable
`ProjectPlannedCostVersion` and, when a prior version existed, supersedes it in the same call — one
fact, not two. No `PlannedCostCreated`/`Updated`/`Removed` vocabulary was invented; source genuinely
exposes only this one semantic operation, the same reasoning `ForecastDraftGenerated` (P19)
established for a single-operation Finance flow.

**Transaction ownership: wired into the already-existing `FinanceGovernanceUnitOfWork`, not a new
stack** — its `planned_costs` repository accessor existed since the UoW was built but had zero real
caller before this phase. A new `FinanceGovernanceCommandBoundary.planned_cost()` method is a direct
structural copy of `forecast_version()` (`invalidation=None`; ViewInvalidation flows entirely
through the canonical post-commit dispatch of the typed event). `PlannedCostService` is wrapped in a
6th `FinanceGovernedServicePort` family (`family="planned_cost"`, `mutations={"calculate_snapshot"}`),
reusing the exact generic read/write routing every sibling family already relies on —
`calculate_snapshot`'s `project_id`-is-the-first-positional-arg shape already matched the existing
`{"create_budget", "create_forecast", ...}` shortcut in `_project_id`, so no new family-specific
branch was needed there either.

**The UoW itself gained two new accessors**: `calculate_snapshot`'s diagnostics computation reads
`AssignmentRepository`/`ProjectResourceRepository`, neither previously on
`FinanceGovernanceUnitOfWork`'s Protocol. Rather than mix an outer-scope, different-session repo
into an otherwise UoW-pure operation (every sibling operation in `build_finance_governance_operations`
uses only `uow.*` repos), both were added as `assignments`/`project_resources` named accessors on
the Protocol and concrete class, bound to the same per-call session as every other repo — a small,
precedent-following extension (mirroring Inventory's own repeated UoW-accessor extensions across
P25/P31B/P32B), not a new transaction stack, and not a generic "repository bag."

**ViewInvalidation — one project-scoped target, no `planned_cost_detail` invented.** Source audit
(`ProjectFinanceWorkspaceQuery.get_planned_cost_workspace`) found the version list and the selected
version's lines are always fetched together, in one query — there is no independently cached detail
read model to route a separate scope to. New handler `build_planned_cost_view_invalidation_handler`
(`planned_cost_snapshot`, `ResourceScope(module_code="project_management", entity_type="project")`)
is a direct structural copy of `forecast_planning`'s own single-target shape (P19). New
`PlannedCostViewInvalidationAdapter` (`plannedCostSnapshotStale`) and binder function
`on_planned_cost_snapshot_stale` (invalidating `"planning"`/`"performance"`, exactly matching the
legacy signal's own destination set) follow the identical wiring chain already established for
Forecast/RateCard in `financials_workspace_controller.py`/`context.py`. The sole owning legacy
consumer (`financials_refresh_mixin.py`) had its `planned_costs_changed` subscription removed with
no replacement of any kind — no other file ever subscribed to it.

**Concurrency preserved exactly, unweakened.** The pre-existing guard — a version-checked supersede
of the previous version (`expected_row_version`) plus a DB-level per-project-revision uniqueness
constraint mapped to `ConcurrencyError` — is untouched. A two-session repository-level regression
test proves the second writer is genuinely rejected — unlike the Inventory `PurchaseOrderLine`
finding (P33 §14), this aggregate was already correctly protected. Enterprise audit was already
atomic (`record_audit_entry(..., commit=False, fail_closed=True)`) and stays atomic.

**Finance reflective wrapper untouched.** Planned Cost never used `FinanceGovernanceCommandBoundary.
_emit_scoped`/`_emit_budget` — it had its own direct `domain_events.planned_costs_changed.emit(...)`
call, now removed. Neither helper was modified; Budget's and Financial Change's own behavior through
them is unchanged.

**A genuine, source-confirmed finding, explicitly out of this phase's scope.** A monkeypatched
audit-failure test proved the exception correctly propagates and produces zero postcommit hints, but
whether the already-flushed version row itself is rolled back could not be reliably asserted through
this specific shared-connection test harness — reproduced identically against completely unmodified
`ForecastVersionService.create_forecast`, confirming this is a pre-existing characteristic of the
shared `FinanceGovernanceCommandBoundary`/UoW machinery itself, not introduced by P35. No other
Finance family's test suite asserts persisted-state-after-failure through this boundary either.
Recorded, not fixed — redesigning `FinanceGovernanceCommandBoundary` is explicitly out of scope for
a single-signal capability phase.

`planned_costs_changed` is now deleted from `DomainEvents` entirely — zero producers (the one
`.emit()` site converted), zero consumers (the sole owning subscription removed, replaced by the
typed adapter). The legacy Signal count is 12 as of this phase (13 minus the one deletion —
confirmed source-derived). Planned Cost is now fully modernized — the first of P34A's Finance-first
trio. Next planned target remains Commitment, unchanged by this phase.

**26.32 P36: Finance Commitment full modernization + transaction-correctness fix —
`commitments_changed` deleted, second of P34A's Finance-first trio.** Two typed events
(`application/financials/commitments/commitment_events.py`): `CommitmentLineChanged` (`tenant_id`,
`organization_id`, `project_id`, `commitment_line_id`, `change_type: CREATED | REVISED`,
`occurred_at`) and `CommitmentMatchChanged` (same shape, `match_id`,
`change_type: MATCHED | REVERSED`) — the business facts are "a commitment line was created or
revised by a source projection" and "a commitment line was matched or had a match reversed."
Source was re-audited to confirm the real mutation surface first: `_apply_source_projection` has
exactly two real write paths (`create_from_source`, `apply_source_revision`) plus a true no-op
replay branch (identical content replayed under the same source revision — zero write, zero
event); `_create_match` similarly has one real write path plus an idempotency-key replay no-op.
The brief's own suggested `CommitmentCreated`/`Updated`/`Cancelled`/`Closed`/`Removed` vocabulary
was deliberately rejected — source has no cancel/close/remove operation, only a source-driven
`state` field folded into `REVISED` — in favor of naming after Commitment's two real aggregate
parts (line, match), mirroring `ForecastVersionChanged`/`ForecastLineChanged`'s (§26.9-ish) own
aggregate-part split rather than a generic CRUD vocabulary.

**Transaction ownership — the core bug fix — wired into the already-existing
`FinanceGovernanceUnitOfWork`, not a new stack.** Its `commitments` repository accessor existed
since the UoW was built (added alongside P35's Forecast-generation work) but had zero real
governed caller before this phase. A new `FinanceGovernanceCommandBoundary.commitment()` method is
a direct structural copy of `planned_cost()` (`invalidation=None`). `ProjectCommitmentService` is
wrapped in a 7th `FinanceGovernedServicePort` family (`family="commitment"`,
`mutations={"ingest_procurement_source", "match_cost_entry", "reverse_match"}`). Unlike every
prior family, Commitment's three governed methods do not fit the existing `_project_id()`
shortcuts (`ingest_procurement_source` takes a `source` object, not a project id, as its first
argument; `match_cost_entry`/`reverse_match` are fully keyword-only) — a new `family == "commitment"`
branch was added, resolving `ingest_procurement_source` via `source.reference.project_id` directly,
and `match_cost_entry`/`reverse_match` via the read service's own `get_line`
(`_commitment_repo.get_match(...).commitment_line_id` for the latter, reached the same way
`financial_change`'s own branch already reaches `_require_impact`) — a private-attribute reach
already established as acceptable by that sibling family, not a new pattern.

This directly fixes the confirmed, twice-reconfirmed (P34A, P35) commit-without-rollback defect:
`commitment_service.py`'s old `_commit()` called `self._session.commit()` then
`domain_events.commitments_changed.emit(...)` with zero try/except/rollback around either call.
The method is deleted entirely. All three governed methods now end in
`self._record_event(event)` (when a `record_event` callable is wired — see below) plus
`self._session.flush()`, with the owning transaction's commit and rollback-on-any-exception
entirely delegated to `FinanceGovernanceCommandBoundary._execute`'s `with uow_factory.create(...)
as uow: ... uow.commit()` — the same canonical mechanism proven for every sibling Finance family.

**The second producer P35-CLEANUP found was deliberately NOT converged onto the UoW.**
`ProcurementFinancialDispatcher._emit_refresh` (`src/infra/integration/
procurement_financial_dispatcher.py`) already wraps its own `self._session.commit()` in a correct
try/except/rollback around the dispatcher's own inbox/outbox transaction — re-confirmed by reading
its full 136 lines before touching anything; it was never the buggy path, and forcing it onto a
second, competing `FinanceGovernanceUnitOfWork` transaction would have meant two commits for one
logical delivery. `apply_procurement_source`/`apply_procurement_receipt_match` — the two
Procurement-inbox-facing methods, confirmed to have no other callers — therefore stay on the raw,
dispatcher-owned `ProjectCommitmentService` instance (`record_event=None`) with unchanged
transaction ownership. What changed is their *return contract*: each now returns the constructed
typed event, or `None` on a true replay, instead of the mutated entity (the entity was never used
by their one caller, `ProcurementFinancialConsumer`, whose return value was previously discarded
entirely). `ProcurementFinancialConsumption.commitment_events: tuple[object, ...]` replaces the old
hardcoded-`True` `commitment_changed: bool` field — a latent over-notification bug (a true replay
would have still reported "changed") fixed as a direct side effect of threading the real event
through instead of a boolean. `ProcurementFinancialDispatcher._emit_refresh` (now an instance
method, needing `self._post_commit_bus`) publishes each collected commitment event via
`self._post_commit_bus.publish(event, DomainEventContext(correlation_id=generate_id()))` — one
fresh correlation per delivery, matching the dispatcher's own one-delivery-per-outbox-record
granularity — while its `cost_entries_changed.emit(scope)` branch is completely untouched (Cost
Entry is not yet modernized). Pre-commit `TransactionalEventDispatcher` dispatch was deliberately
skipped for this path — confirmed, by direct inspection, that zero pre-commit handlers are
registered anywhere in the codebase for any ViewInvalidation-only event type, making that step
pure unused ceremony for a dispatcher with no `UnitOfWork` to plug it into.

**ViewInvalidation — one project-scoped target for both event types, no narrower split invented.**
The legacy signal's own confirmed consumer fanned to 5 destinations
(overview/planning/costs/performance/commercial) — the widest of any Finance signal — implying
committed-cost genuinely affects all five identically; not narrowed without stronger field-level
evidence, the same reasoning P31B applied to Balance. New handler
`build_commitment_view_invalidation_handler` (`commitment_list`,
`ResourceScope(module_code="project_management", entity_type="project")`) is a direct structural
copy of `planned_cost`'s single-target shape. New `CommitmentViewInvalidationAdapter`
(`commitmentListStale`) and binder function `on_commitment_stale` (invalidating the same 5
destinations) follow the identical wiring chain already established for Forecast/RateCard/Planned
Cost in `financials_workspace_controller.py`/`context.py`. The sole owning legacy consumer
(`financials_refresh_mixin.py`) had its `commitments_changed` subscription removed with no
replacement of any kind.

**Concurrency preserved exactly, unweakened.** The pre-existing defense-in-depth guard — a
pessimistic `for_update` row lock on the read, combined with an optimistic
`expected_row_version`-checked `update_line`/`update_with_version_check`, plus
idempotency-key/content-hash-based replay detection and `IntegrityError`→`BusinessRuleError`
conflict translation — is entirely untouched (`_apply_source_projection`/`_create_match` were not
modified beyond adding the trailing event-construction step). A two-session repository-level
regression test proves the second writer is genuinely rejected. Enterprise audit was already
atomic (`record_audit_entry(..., commit=False, fail_closed=True)`) and stays atomic; a
monkeypatched audit-failure test proves the exception correctly propagates and produces zero
postcommit hints — and, going one step further than P35's equivalent test, also proves the shared
session remains usable for a subsequent legitimate operation afterward (the specific regression
the old commit-without-rollback bug could have caused: a poisoned session). Whether the
already-flushed line row itself is independently visible-as-rolled-back through this same
shared-connection test harness was, per P35's own documented precedent, not asserted directly.

`commitments_changed` is now deleted from `DomainEvents` entirely — zero producers (both `.emit()`
sites converted), zero consumers (the sole owning subscription removed, replaced by the typed
adapter) — and added to `_DELETED_BRIDGE_NAMES` in
`test_p8_platform_event_architecture_canonicalization.py`. `current − frozen` is now exactly
`{cost_entries_changed}` — the one remaining, deliberately-unresolved P35-CLEANUP violation. The
legacy Signal count is 10 as of this phase (11 minus the one deletion — confirmed source-derived).
Commitment is now fully modernized — the second of P34A's Finance-first trio. Next planned target:
`cost_entries_changed`, the last of the trio.

**26.33 P36-FIX/P36-FIX2: canonical event lifecycle for the Procurement Commitment producer
(verification + fix, no new phase number).** P36-FIX traced the exact Procurement-driven
Commitment flow end-to-end and found a real gap the P36 report's own wording had glossed over:
`CommitmentLineChanged`/`CommitmentMatchChanged` were constructed precommit inside
`ProcurementFinancialConsumer.consume()` but never staged into any canonical event lifecycle —
they were bare Python return values, hand-carried through `ProcurementFinancialConsumption` across
the commit boundary, then manually published to `platform_post_commit_bus` *after*
`self._session.commit()` succeeded. No pre-commit transactional-handler guarantee existed for
them at all — accidentally harmless only because zero handlers happen to be registered for any
ViewInvalidation-only event anywhere in this codebase. First fix: `ProcurementFinancialDispatcher`
gained a `_record_precommit()` calling `self._transactional_dispatcher.dispatch(event, self)`
immediately before its own commit.

**P36-FIX2 found that fix itself violated the architecture it was restoring**: passing `self`
(the dispatcher) as the handler's `uow: UnitOfWork` argument is real duck-typed impersonation —
`ProcurementFinancialDispatcher` implements none of `record_event`/`commit`/`__enter__`/`__exit__`/
`context`/`register_touched`/`tracked_aggregates`, and `InProcessTransactionalEventDispatcher`'s
own docstring confirms `uow` is typed `UnitOfWork` throughout the architecture (Protocol, handler
signature) even though its concrete implementation never inspects it structurally. A fresh-UoW-
per-delivery alternative (§6 of that verification's own brief) was evaluated and rejected: `commitment_service`/`cost_entry_service`/`inbox_service`/`outbox_service` are
composition-root singletons already bound to the dispatcher's one long-lived session at
construction time; splitting only the event-recording portion onto a separate fresh session would
break the existing atomicity between inbox-delivery-state (`begin_delivery`/`mark_processed`) and
the Commitment mutation, which currently share one commit. Final, canonical design: a new private
`_consume_under_unit_of_work()` wraps the dispatcher's own already-owned `self._session` in a real
`SqlAlchemyUnitOfWorkBase` (`session=self._session` — the literal same object, not a new one) for
the scope of one delivery — `consumer.consume()` runs inside it, `uow.record_event(event)` for
each returned Commitment event, `uow.commit()` runs the exact same drain → precommit-dispatch →
`self._session.commit()` → postcommit-publish lifecycle every other canonical UoW in this codebase
already runs. `_record_precommit()` and the manual `_emit_refresh()` publish loop for
`commitment_events` are both deleted — the dispatcher no longer directly invokes
`transactional_dispatcher.dispatch(...)` or `post_commit_bus.publish(...)` for DomainEvent
lifecycle purposes anywhere. A strengthened test proves the handler receives the real
`SqlAlchemyUnitOfWorkBase` instance (`isinstance` + `is not dispatcher` + `handler_uow._session is
dispatcher._session`), and a companion test proves a raising precommit handler rolls back the
mutation and reaches zero postcommit event. Full platform suite before/after: identical
23-failed/1599-passed/12-error totals across both passes — zero regressions. No production
commits were made by the agent in either pass; HEAD advanced only through the same external
auto-commit process observed throughout this engagement.

**26.34 P37: Finance Cost Entry full modernization — `cost_entries_changed` deleted, third and
LAST of P34A's Finance-first trio; the P8 architecture budget is restored.** Source reconfirmed
`ProjectCostEntry` as a genuine hybrid: a mutable draft/lifecycle aggregate (`DRAFT` →
`SUBMITTED` → `APPROVED` → `POSTED`, or `SUBMITTED` → `DRAFT` via `reject()`) with a true
immutable-ledger correction concept for `POSTED` entries — `reverse` never mutates the original's
financial facts, it flips `status` to `REVERSED` and records a brand-new, sign-flipped reversal
entry (`ProjectCostEntry.create_posted_reversal`). Five typed events
(`application/financials/cost/entries/cost_entry_events.py`) reflect that split rather than a
CRUD-shaped `CostEntryCreated`/`Updated`/`Deleted` (rejected — source is not uniform CRUD across
its whole lifecycle) or a single catch-all `CostEntryChanged` (rejected — an explicit test,
`test_no_new_business_domain_event_or_replacement_signal_introduced`, forbids exactly that name):

- `CostEntryRecorded` (`tenant_id`, `organization_id`, `project_id`, `cost_entry_id`, `status`,
  `occurred_at`) — a new entry now exists. Manual `create_manual_entry` arrives `DRAFT`; both
  integration sources (`apply_approved_time_source`, `apply_procurement_receipt_source`) arrive
  already `POSTED`, since those two paths advance draft→submit→approve→post synchronously inside
  one command and the intermediate transitions are internal plumbing, not independent
  UI-observable facts — `status` lets the ViewInvalidation handler decide whether actual-cost
  destinations need invalidating too.
- `CostEntryUpdated` — `update_draft`'s genuine mutable-CRUD field edit.
- `CostEntryStatusChanged` (`change_type: SUBMITTED | APPROVED | REJECTED | POSTED`) — one class,
  not four near-identical ones: `submit`/`approve`/`reject`/`post` are literally the same *kind*
  of fact (the entry's status field changed), differentiated only by the resulting state, mirroring
  the already-accepted `CommitmentLineChanged`/`FinancialChangeChanged` enum-in-one-class shape
  (§26.32/§26.16) rather than Rate Card's separate-class-per-operation shape (§26.22) — the
  deciding factor was that these four operations share an identical payload shape and downstream
  meaning (only "which status is it now" matters to a consumer), unlike Rate Card's genuinely
  distinct operations. `REJECTED` exists as its own `change_type` value specifically because
  `reject()` returns the domain status to `DRAFT` (there is no `REJECTED` value in
  `ProjectCostEntryStatus`) — `entry.status` alone cannot disambiguate "was rejected back to
  draft" from "was newly created as draft"; the typed event's `change_type` can.
- `CostEntryReversed` (`cost_entry_id` = the new reversal entry, `reverses_entry_id` = the
  original) — both the manual `reverse` command and the correction-of-a-prior-revision branch
  inside `apply_approved_time_source` (a correction produces two real facts from one call: the
  prior entry was reversed, and the new corrected entry was recorded — both returned).
- `CostEntryRemoved` — `delete_draft`.

**Transaction ownership.** All eight direct commands (`create_manual_entry`, `update_draft`,
`delete_draft`, `submit`, `approve`, `reject`, `post`, `reverse`) converge onto the
already-existing `FinanceGovernanceUnitOfWork.cost_entries` accessor (unused before this phase,
same pattern as Commitment's own previously-unused `commitments` accessor) via a new
`FinanceGovernanceCommandBoundary.cost_entry()` method, a direct structural copy of
`commitment()`. `ProjectCostEntryService` is wrapped in an 8th `FinanceGovernedServicePort` family
(`family="cost_entry"`). `_project_id()` needed exactly one new branch — every mutation except
`create_manual_entry` resolves via `self._read_service.get_entry(args[0]).project_id`;
`create_manual_entry` already passes `project_id` as an explicit kwarg, caught by the port's
pre-existing generic `kwargs.get("project_id")` shortcut with no family-specific case needed. The
shared private helpers behind both the direct `approve()`/`reject()` and the Approval
participant — `_apply_approval_decision`/`_apply_rejection_decision` — construct and return
`(entry, event)`, mirroring `ProjectCommitmentService._create_match`'s exact dual-path shape from
P36: `self._record_event(event)` fires when wired (the governed direct path), and the returned
event is used directly by the participant (whose fresh per-transaction `ProjectCostEntryService`,
built by `build_project_cost_approval_deps`, has no `record_event` wired — `approval_service=None`
by the same P4A reasoning as every sibling `*ApprovalDeps` builder). Cost Entry's own
transaction-safety defect was narrower than Commitment's — the old `_commit()` already wrapped
`self._session.commit()` in try/except/rollback — but it was still a raw, uncanonical Session with
a post-commit legacy-signal emit; `_commit()` is deleted entirely, along with every
`self._session.commit()` call for these eight commands.

**Approval path — the canonical P19 seam, no new construction needed.**
`ProjectCostApprovalParticipant.apply`/`reject` no longer build
`ApprovalPostCommitEvent("cost_entries_changed", invalidation_scope(entry))` — they forward the
typed `CostEntryStatusChanged` the shared decision helpers already constructed, via
`ApprovalHandlerResult(domain_events=(event,))`. `ApprovalService`'s own pre-existing machinery
(the exact `for domain_event in handler_result.domain_events: uow.record_event(domain_event)` seam
`FinancialChangeApprovalParticipant` established in P19, §26.16) records it precommit on its own
UoW — unlike Financial Change, which builds its typed events directly inline in the participant,
Cost Entry's participant never constructs `CostEntryStatusChanged` itself; it only forwards what
the service-layer helper already built, since that helper is shared with the direct governed path
too and must be the single source of truth for the event's shape.

**Integration dispatchers — both now canonical, `ProcurementFinancialDispatcher`'s `_emit_refresh`
fully retired.** `apply_approved_time_source`/`apply_procurement_receipt_source` no longer commit
or emit anything themselves — they construct and *return* their typed event(s) (0–2 for the
Approved Time path, 0–1 for Procurement receipt), exactly mirroring Commitment's dispatcher-facing
return-contract shape from P36. `ApprovedTimeFinancialDispatcher` gained the identical
`SqlAlchemyUnitOfWorkBase`-wrapping shape §26.33 established for `ProcurementFinancialDispatcher`
— a genuinely new capability for this dispatcher, which never had any canonical event lifecycle
before this phase — proven by a dedicated precommit-timing/real-UoW-identity test mirroring
§26.33's own two Commitment tests exactly (real-UoW-not-dispatcher identity, and
handler-failure-rolls-back-with-zero-postcommit-event). `ProcurementFinancialDispatcher`'s
`_consume_under_unit_of_work` now records both `consumption.commitment_events` and the new
`consumption.cost_entry_events` into the SAME one UoW per delivery (a single Procurement receipt
envelope can genuinely produce both a Commitment match fact and a Cost Entry recorded fact) —
`_emit_refresh`, whose entire remaining responsibility after §26.33 was the `cost_entries_changed`
emit, is now fully dead code and deleted outright, along with the now-unused `FinanceInvalidationScope`/`domain_events` imports in that file.

**ViewInvalidation — two targets, source-justified, not copied from Commitment's one.**
`finance_snapshot_statements.py` confirms actual-cost aggregation queries filter
`ProjectCostEntryORM.status.in_(("posted", "reversed"))` — DRAFT/SUBMITTED/APPROVED entries never
count toward actuals. This directly justifies two genuinely distinct staleness surfaces:
`cost_entry_list` (every fact — the "Costs" tab lists entries of any status) and
`cost_entry_actuals` (only POSTED-affecting facts: `CostEntryRecorded` when `status=POSTED`,
`CostEntryStatusChanged(POSTED)`, `CostEntryReversed`). `on_cost_entry_list_stale` invalidates only
`"costs"`; `on_cost_entry_actuals_stale` invalidates `"overview"`/`"performance"`/`"commercial"`
(deliberately not `"costs"` again — the paired list hint every posted fact also emits already
covers it) — together reproducing the legacy signal's own exact 4-destination fan-out
(`overview`/`costs`/`performance`/`commercial`, confirmed via `financials_refresh_mixin.py`'s
former `_cost_entries_changed` callback — notably NOT including `"planning"`, unlike Commitment's
5-destination mapping; not copied automatically, source-proven independently).

**Legacy retirement and test adaptation.** `cost_entries_changed` deleted from `DomainEvents`,
added to `_DELETED_BRIDGE_NAMES`. `test_r6b_finance_invalidation.py`'s remaining cases and
`test_p7_legacy_bridge_removal.py`'s "unrelated signal" example — both previously standing in on
`cost_entries_changed` after P36 retired `commitments_changed` — moved onto `budgets_changed` (the
next still-legacy Finance signal); the "other organization" rejection sub-case was dropped rather
than faked, since `budgets_changed` is `Signal[str]` (plain project id, no tenant/org component)
and `_finance_event_matches`'s string branch never checked organization to begin with — that
capability was only ever exercised through `cost_entries_changed`'s `Signal[object]`/
`FinanceInvalidationScope` payload, which no longer exists anywhere in `DomainEvents`.
`test_p7c_zero_consumer_signal_cleanup.py`'s `_ACTIVE_FINANCE_SIGNALS` now names
`budgets_changed`/`billing_preparations_changed` (verified real producers under
`/application/financials/` for both) instead of the retired signal; its
`test_project_cost_apply_participant_emits_scoped_post_commit_events` test was rewritten to prove
the typed-event forwarding shape instead of the deleted string bridge, and its two
dispatcher-source-inspection tests were rewritten to assert the canonical
`SqlAlchemyUnitOfWorkBase`/`uow.record_event`/`uow.commit()` shape and the explicit absence of
direct `transactional_dispatcher.dispatch(`/`post_commit_bus.publish(` calls in both dispatcher
files.

**Concurrency preserved exactly, unweakened.** The pre-existing `expected_row_version`
optimistic-concurrency guard on every mutating command is untouched — a two-session
repository-level regression test proves the second writer is genuinely rejected, matching the
established pattern from every prior Finance phase.

**Regression battery.** Pre-existing `test_project_cost_entries.py` (8 tests, full
CRUD/lifecycle/idempotency/immutability/cross-currency/closed-period coverage) and
`test_project_cost_apply_participant.py` (5 tests, session-binding/actor-authorization coverage)
both pass unmodified in behavior through the newly-governed boundary — strong evidence the
convergence preserved every existing business-correctness guarantee.
`test_approved_time_labor_integration.py` (11 tests: 2 adapted from the legacy-signal-connect
pattern to typed-event/post-commit-bus observation, 2 new precommit-timing/rollback proofs added)
and `test_procurement_financial_integration.py` (9 tests, 1 adapted) both pass. A new
`test_p37_finance_cost_entry_full_modernization.py` (21 tests) covers the two-target
ViewInvalidation handler (exact mapping per event type/status, dedup), every direct command's
exact hint set (list-only vs. list+actuals), the governed-boundary audit-failure rollback and
session-reusability proof (patched at the `EnterpriseAuditService` class level, since the governed
UoW factory constructs a fresh instance per transaction — the same already-established
characteristic every other governed Finance family shares, not a P37-introduced quirk), the
pre-existing concurrency guard, and both controller consumer reactions
(`onCostEntryListStale`/`onCostEntryActualsStale`).

`cost_entries_changed` is now deleted from `DomainEvents` entirely — zero producers (all three
`.emit()` sites converted: `cost_entry_service.py` direct, `ProcurementFinancialDispatcher`,
`ApprovedTimeFinancialDispatcher`), zero consumers (the sole owning subscription removed from
`financials_refresh_mixin.py`, replaced by the typed adapter pair). `current − frozen` is now
**empty** — the P8 architecture budget is fully restored, with zero post-freeze legacy-Signal
exceptions remaining anywhere in `DomainEvents`. The legacy Signal count is 9 as of this phase (10
minus the one deletion — confirmed source-derived). Cost Entry is now fully modernized — the
third and last of P34A's Finance-first trio. No Finance capability has an open post-P8-freeze
violation; Budget and Billing Preparation remain on their own, separately-scheduled track (both
pre-freeze, frozen-allowlisted, not violations).

**26.35 P38A/P38B: Finance Budget full modernization — `budgets_changed` deleted, only
`billing_preparations_changed` remains.** P38A (audit-only) found Budget's direct-command
transaction layer already 100% converged onto `FinanceGovernanceUnitOfWork` before its own
event-modernization phase began — the only Finance capability found in that state. P38B added five
typed events (`application/financials/budgets/budget_events.py`): `BudgetVersionCreated`
(`create_budget`/`create_successor`, plus the Financial-Change-driven successor, `status`
distinguishing a plain DRAFT from an already-APPROVED one), `BudgetProfileUpdated`
(`update_budget_header` — a genuine fourth fact, not folded into `BudgetStatusChanged`),
`BudgetLineChanged` (`add_line`/`update_line`/`delete_line`, one class + `change_type`),
`BudgetStatusChanged` (`SUBMITTED`/`APPROVED`/`REJECTED`/`SUPERSEDED`/`CLOSED`), `BudgetRemoved`
(`delete_budget`). `BudgetService` gained the standard `record_event` constructor param; the shared
`_apply_approval_decision`/`_apply_rejection_decision` helpers construct-and-return
`(budget, events)`/`(budget, event)`, following the exact P36/P37 dual-use-service shape (recorded
via `record_event` on the governed direct path, forwarded via
`ApprovalHandlerResult(domain_events=...)` on the participant path). `command_boundary.py`'s
`_emit_budget` and `budget()`'s `invalidation=` callback are deleted outright — Budget was the last
family still passing a non-None `invalidation`, so the whole parameter was removed from `_execute`
rather than left as permanent dead code. The cross-capability Financial-Change→Budget edge P38A
found already transaction-safe is now typed on both sides: `ApprovedFinancialSuccessorResult`
gained a `domain_events` field (default `()`, Forecast's identical call site unaffected);
`financial_change_apply_participant.apply()` appends the returned Budget events onto its own
`FinancialChangeChanged` tuple instead of building `ApprovalPostCommitEvent("budgets_changed",
...)`. The P37-FIX permission-order bug pattern (`_project_id()` resolving via a
permission-checked public accessor before the command's own check runs) was fixed for Budget's
`add_line`/`update_line`/`delete_line` branches (switched to the private `_require_budget`) —
Commitment's `match_cost_entry` branch, flagged with the same pattern in P38A, remains untouched,
out of scope. ViewInvalidation uses two uniformly-mapped targets (`budget_planning` for the
Financials workspace, reproducing the legacy signal's exact 3-destination fan-out;
`budget_project_summary` for the Projects workspace) — every fact stales both, matching the legacy
signal's own undifferentiated behavior for both consumers; the Projects-workspace consumer is a
genuine precision improvement over the old blanket, unscoped `_request_domain_refresh()`. `budgets_
changed` is deleted from `DomainEvents`, added to `_DELETED_BRIDGE_NAMES`; `billing_preparations_
changed` is now the sole remaining Finance legacy signal. Legacy Signal count: 8 (9 minus the one
deletion). Budget is now fully modernized; Billing Preparation (both aggregates together) remains
the only capability on Finance's track.

**26.36 P39: Finance Billing full modernization — `billing_preparations_changed` deleted, the
LAST Finance legacy signal; Finance module event modernization is 100% complete.** Two genuinely
distinct aggregate families (`ProjectBillingProfile`/`ProjectBillingScheduleLine` and
`ProjectBillingPreparation`/`ProjectBillingPreparationLine`) kept as separate DomainEvent
vocabularies, never merged into a `BillingChanged` catch-all: Profile gained `BillingProfileCreated`,
`BillingProfileActivated` (the only currently-reachable status transition — `place_on_hold`/`close`
have no service command), `BillingScheduleLineAdded`, `BillingScheduleLineMarkedReady` (likewise
the only reachable line transition). Preparation gained `BillingPreparationCreated`,
`BillingPreparationLineAdded` (one class + the reused `BillableSourceType` enum for all three
source kinds), `BillingPreparationStatusChanged` (`SUBMITTED`/`APPROVED`/`REJECTED`/
`DELIVERY_PENDING`/`DELIVERED`/`ACKNOWLEDGED`/`RECONCILED`), `BillingPreparationExternalOutcome
Recorded`. A candidate `BillingPreparationDeliveryRequested` fact was investigated and found
unnecessary — `request_delivery` persists nothing beyond its own status transition.
`record_external_outcome(DELIVERY_ACCEPTED)` transitions status twice in one call (`mark_delivered`
then `acknowledge`) and records both as separate facts, mirroring Budget's approve/supersede
two-fact shape. `ProjectBillingSourceLock` is infrastructure (source-reservation uniqueness), not
an event-worthy business fact.

**No mega-UoW.** Both services already shared one `ProjectBillingRepository` — `FinanceGovernance
UnitOfWork` gained a single `billing` accessor (not a new UoW type) and both families converge onto
it via two new `FinanceGovernanceCommandBoundary` methods, the same shape 9 other Finance families
already use. The bespoke `BillingPreparationSubmissionUnitOfWork` (previously owning only
`submit_preparation`) is retired entirely — both contract and SqlAlchemy files deleted, no
compatibility alias — since its `billing`+`approvals` repo set was already a strict subset of
`FinanceGovernanceUnitOfWork`'s own. `submit_preparation` now calls the transaction-agnostic
`request_approval_using(...)` helper directly (not `ApprovalService.request_change(...)`, which
would have silently added a new `"approval.request"` permission requirement on top of the existing
`"finance.manage"` check — deliberately avoided, even though Financial Change's own `submit_change`
independently chose to require both). `BillingPreparationApprovalParticipant` dropped its
`_apply_approval_decision`/`_apply_rejection_decision` `commit: bool` flag entirely, matching every
sibling participant's unconditional-build-and-return shape.

**Zero Finance legacy signals remain — a permanent, explicit-name-set architecture guard now
proves it** (`test_zero_finance_legacy_signal_fields_remain`, not a fragile prefix heuristic, since
Finance signal names never shared one). Legacy Signal count: 7 (8 minus the one deletion). Finance
is the first business module in this engagement to reach 100% typed-event coverage — Project
Management and Auth/Security are the only tracks with legacy Signal fields left.

**26.37 P40B: PM Timesheet full modernization — `timesheet_periods_changed` deleted, first PM
capability retired.** P40A's re-audit selected Timesheet as the next target (smallest remaining
PM producer surface — one helper, six callers). Only the `TimesheetPeriod` lifecycle (`submit`/
`approve`/`reject`/`lock`/`unlock`/`reopen_for_correction`) was in scope — `TimeEntry` mutations
already published `tasks_changed` only and are untouched. One shared-family event,
`TimesheetPeriodStatusChanged(change_type: TimesheetPeriodStatusChangeType)`, replaces the six
transitions (mirrors `BudgetStatusChanged`'s precedent) rather than six near-identical classes or
one generic `TimesheetChanged`.

**Transaction convergence without a new named-repository UoW.** `TimeService` (Platform-owned,
shared by every PM Timesheet workflow) already held one long-lived, request-scoped `Session`
directly — the same shape `ApprovedTimeFinancialDispatcher` (this exact subsystem's own Approved
Time → Cost Entry dispatcher) already wraps with a bare `SqlAlchemyUnitOfWorkBase` for one
transaction's commit lifecycle, reusing the *same* session rather than opening a second one. Since
`Session.close()` (called by `UnitOfWork.commit()`) only ends the current transaction and expires
identity-mapped objects — it does not invalidate the Python `Session` object for further reuse —
`_persist_timesheet_transition` adopts the identical adapter shape instead of building a new
named-repository `TimesheetUnitOfWork`: `SqlAlchemyUnitOfWorkBase(session=self._session, ...)`
wraps the period transition, the Approved Time outbox enqueue, and `record_event(...)`, so all
three still commit atomically on the one session they always shared. This keeps `TimeService`'s
constructor-injected repositories untouched and avoids the "mega-UoW" anti-pattern from the other
direction — no repo-bag UoW was introduced where none was architecturally required.

**ViewInvalidation: one event, three targets, source-preserving.** The legacy signal reached three
consumer families uniformly with zero scoping — Task's workspace (needs the affected project),
the Resource inspector's assignments tab (needs the affected resource), and both Timesheet
workspaces themselves (personal + review queue, org-wide, since a reviewer needs every resource's
submission). `TIMESHEET_WORKSPACE_SCOPE_CODE` (`OrganizationScope`), `TIMESHEET_RESOURCE_SCOPE_CODE`
and `TIMESHEET_PROJECT_SCOPE_CODE` (both `ResourceScope`) reproduce exactly that fan-out with real
scoping instead of none. Collaboration's identical subscription was investigated and found
INCIDENTAL — `selectedPeriodKey` there is an unrelated comment-date filter, not timesheet data —
and dropped with no replacement, per the standing consumer-precision discipline.

**Legacy Signal count: 6 (7 minus the one deletion) — the first Project Management capability to
reach zero.** `timesheet_periods_changed` rejoins the historical P8 frozen allowlist's deleted-name
set (`_DELETED_BRIDGE_NAMES`); the frozen baseline itself is unchanged, per standing convention.
Remaining PM legacy signals: `project_changed`, `tasks_changed`, `register_changed`,
`collaboration_changed`, `portfolio_changed` — Register and Portfolio are next per P40A's sequence.

**26.38 P41: PM Register full modernization — `register_changed` deleted, second PM capability to
reach zero; the real two-commit business-mutation/audit split P40A found is fixed.** `RegisterEntry`
confirmed one cohesive aggregate with a `RISK`/`ISSUE`/`CHANGE` discriminator field, not three
separate aggregates — one shared-family `RegisterEntryChanged(change_type: CREATED|UPDATED|
REMOVED)` event, not three per-type classes.

**The two-commit bug.** Every mutation committed the business write first, then called
`record_activity(self, ..., commit=True)` — a second, independent commit; if that second commit
failed, the business mutation was already durably persisted with no way back. Worse: Register had
no enterprise audit at all before this phase, only the Activity feed. Both gaps close in one
converged transaction: business mutation → enterprise audit (new) → Activity feed (preserved,
`commit=False`, staged on the same UoW) → `uow.record_event(...)` → one `uow.commit()`. A
permanent test (`test_audit_failure_rolls_back_the_register_mutation_permanently`) proves this by
asserting persisted state after a simulated audit failure — `list_entries` returns empty — not by
counting commit calls.

**Canonical UoW: a new, narrow `RegisterUnitOfWork`**, not a reused shared session. Unlike
Timesheet (P40B), where the Approved Time outbox's own presence on the same shared session made
reusing that session via a bare `SqlAlchemyUnitOfWorkBase` the correctness-preserving choice,
Register had no such constraint — `RegisterService` shared the same long-lived PM session as
everything else purely by historical accident, not by any transactional necessity. The
architecturally cleaner and more consistent choice, matching Resource's/Employee's own precedent
exactly, was a first-class single-repo UoW (`entries: RegisterEntryRepository`,
`_enterprise_audit_service`, `_activity_service`) via `SqlAlchemyRegisterUnitOfWorkFactory` on its
own fresh per-command session. Named accessor only, no generic repository bag.

**ViewInvalidation: one event, two targets — a third dropped for a real architectural reason, not
laziness.** `REGISTER_WORKSPACE_SCOPE_CODE` (`OrganizationScope`) serves Register's own workspace
(its project filter defaults to "all"); `REGISTER_PROJECT_SCOPE_CODE` (`ResourceScope`) serves
Dashboard's project-scoped register widget. Platform's Control workspace also legacy-subscribed,
but `test_platform_does_not_import_business_modules.py` forbids Platform-layer QML from importing
a `project_management`-owned module — cutting Control over to a typed `RegisterViewInvalidation
Adapter` subscription would violate that guard. Dropped with no replacement; this is the first
phase in the engagement where a legacy consumer's removal was forced by an architecture boundary
rather than by the consumer being incidental.

**P41-FIX correction**: `test_platform_does_not_import_business_modules.py` only scans `src/core/
platform/` — it never covered `src/ui_qml/platform/` (the QML controller layer) at all, so the
guard cited above did not actually forbid this. The underlying ADR-005 Sec21 principle (Platform
owns no business-module implementation) still applies at the QML layer regardless, so rather than
import `RegisterViewInvalidationAdapter` directly into Control (which the principle still
correctly disallows even without an automated guard), the reaction was restored via the same
composition-root Signal/Slot dependency-inversion `shell/app.py::main()` already used for
Platform→PM wiring (tenant/organization switching), now used PM→Platform for the first time:
`ProjectManagementWorkspaceCatalog.registerWorkspaceStale` → `PlatformControlWorkspaceController.
onExternalViewStale` (generic, Register-ignorant). Neither module imports the other's
implementation. See the plan doc's own P41-FIX entry for full detail.

**Legacy Signal count: 5 (6 minus the one deletion) — second Project Management capability to
reach zero.** `register_changed` rejoins the historical P8 frozen allowlist's deleted-name set;
the frozen baseline itself is unchanged. Remaining PM legacy signals: `project_changed`, `tasks_
changed`, `collaboration_changed`, `portfolio_changed` — Portfolio is next per P40A's sequence.

**26.39 P42: PM Portfolio full modernization — `portfolio_changed` deleted, third PM capability to
reach zero; the real nested/self-owned commit hazard P40A found is fixed.** Four sub-aggregate
families kept as distinct DomainEvent vocabularies (`PortfolioIntakeItemChanged`, `PortfolioScenario
Changed`, `PortfolioScoringTemplateChanged`, `PortfolioProjectDependencyChanged`), never collapsed
into one `PortfolioChanged`.

**The nested-commit hazard.** `portfolio_support.py`'s `_ensure_scoring_templates()` — a
lazy-bootstrap helper reachable from BOTH Intake commands and Template commands themselves —
called `self._session.commit()` internally, twice, as a side effect of what looked like a read
helper. A command could durably commit a bootstrap-created or reactivated scoring template and
then fail its own actual operation immediately after (e.g. a duplicate-name `ValidationError`) —
the bootstrap write survived a failure the user's real request never completed. Fixed by making
every scoring-template helper transaction-neutral: each now takes the caller's own UoW-scoped
`templates_repo` and an `events` accumulator, never commits, never owns a session.

**Canonical UoW: one `PortfolioUnitOfWork` owning all four named repositories**
(`intake`/`scenarios`/`scoring_templates`/`dependencies`), mirroring `DocumentUnitOfWork`'s
established one-capability-several-repos shape — not a mega-UoW, since Portfolio genuinely is one
capability (one workspace) even though most single commands touch only one repository.
`activate_scoring_template` mutates two rows in the same repository within one transaction (the
newly-activated template and the previously-active one) — now provably atomic, proved by a
dedicated multi-row rollback test, not merely asserted. Enterprise audit added to three of the
four sub-aggregates (Intake, Scenario, ScoringTemplate), which had none before this phase —
mirroring Register's own P41 precedent.

**ViewInvalidation: one category, one target — and two of three legacy consumers turned out to be
incidental.** No `Portfolio` entity exists (P40A: a pure organizational grouping) — all four
sub-aggregate families genuinely stale the one org-wide workspace uniformly.
`PORTFOLIO_WORKSPACE_SCOPE_CODE` (`OrganizationScope`) is the only target. PM Dashboard's own
"portfolio" KPI (`DashboardPortfolioMixin`) is entirely Project/Task/Resource/Cost-derived and
never reads any of the four real sub-aggregates; the Projects workspace displays no
Portfolio-derived data anywhere. Both dropped with no replacement — carried-over fan-out from the
pre-modernization era, exactly what P40A's own audit anticipated finding. Only Portfolio's own
workspace was genuine.

**Legacy Signal count: 4 (5 minus the one deletion) — third Project Management capability to
reach zero.** `portfolio_changed` rejoins the historical P8 frozen allowlist's deleted-name set;
the frozen baseline itself is unchanged. Remaining PM legacy signals: `project_changed`, `tasks_
changed`, `collaboration_changed` — Project is next per P40A's tentative sequence.

**P42-FIX correction: the scoring-template bootstrap was missing enterprise audit.**
`_ensure_scoring_templates`/`_deactivate_other_templates` mutated rows and recorded a typed
`PortfolioScoringTemplateChanged` event, but never called `record_audit_entry` — only each
COMMAND's own top-level audit call covered the row the user explicitly asked for, never a
bootstrap default created as a side effect (reachable from `create_intake_item`, not just the two
scoring-template query methods). Caught by a dedicated test asserting a monkeypatched
`EnterpriseAuditService.record` failure aborts the whole bootstrap — it didn't, because audit was
never invoked. Fixed by moving `record_audit_entry` inside the shared helpers themselves so every
caller gets complete, atomic audit coverage; helper signatures changed from a bare `templates_repo`
to the full `uow` (needed for audit-service access). The bootstrap's write-on-read shape itself was
investigated and deliberately retained (no clean explicit-bootstrap command site exists, since
Portfolio has no `Portfolio` entity to hook one to, and an unpersisted in-memory default would
break id-stability) — proved safe (once-per-organization, atomic, fully audited/evented) rather
than eliminated. A related concurrent-first-bootstrap duplicate-default race was found (no DB
uniqueness constraint on scoring templates) and recorded as pre-existing debt, not fixed.

**P42-FIX2 correction: the recorded concurrent-bootstrap race is now closed at the database, not
merely characterized.** "At most one active `PortfolioScoringTemplate` per organization" was
confirmed as a genuine domain invariant (not convenience) — `create_intake_item`/
`update_intake_item` derive an intake item's scoring weights deterministically from "the" active
template, so two simultaneously-active rows would make a core prioritization calculation silently
arbitrary. Enforced with a real partial unique index, `uq_portfolio_scoring_one_active_per_org`
(`UNIQUE(organization_id) WHERE is_active`, both `postgresql_where=`/`sqlite_where=` on the ORM
and a matching Alembic migration `d8e1f4a7b2c3`), scoped by `organization_id` alone rather than
`tenant_id + organization_id` like the Budget precedent it otherwise mirrors — `tenant_id` is
nullable here, and a composite unique index over a nullable column would not enforce uniqueness
across NULL-tenant rows. The migration deterministically normalizes any pre-existing
duplicate-active rows first (keep the most-recently-updated one per organization). The idempotent
lazy-bootstrap path now catches the resulting `IntegrityError` on a lost race, relies on the
UoW's own rollback-and-close, and returns the winner's canonical state via a fresh read — zero
durable side effects for the loser, proved with a real two-independent-UoW concurrency test, not
a simulation. Explicit commands (`activate_scoring_template`, `create_scoring_template(activate=
True)`, `create_intake_item`) instead map the same `IntegrityError` to `ConcurrencyError` — the
project's existing concurrency-exception convention (the same `ConcurrencyError`/`STALE_WRITE`
class already used for optimistic-locking conflicts elsewhere in Project Management) — rather
than silently retrying, matching the general principle that idempotent reads may recover
transparently while explicit user commands must surface a genuine conflict rather than mask it.
No event vocabulary, `PortfolioUnitOfWork` shape, or ViewInvalidation target changed.

**P43: PM Project full modernization, closing the P40A-discovered silent `set_status` gap.**
`project_changed` deleted — the fourth Project Management capability to reach zero legacy Signal
fields. Reconfirmed from source (not P40A's approximate count): 7 producer sites (3 real Project
mutations, 4 `ProjectResource`-assignment sites on a different aggregate) and 11 real consumers
(10 genuine, reclassified per-consumer against current queries; 1 — Platform Control — confirmed
INCIDENTAL and removed with no replacement, since its own `build_overview`/`build_approval_queue`/
`build_audit_feed` never dereference a Project field). Event vocabulary: `ProjectCreated`,
`ProjectProfileUpdated`, `ProjectStatusChanged`, `ProjectRemoved` — matching P40A's own audited
decomposition exactly (`ProjectOwnershipChanged`/`ProjectDatesChanged` reconfirmed NOT distinct
facts). New `ProjectUnitOfWork` (`projects` + `financial_profiles` named accessors, the latter so
`create_project`'s atomic `ProjectFinancialProfile` side effect stays in the same transaction) —
the first Project-specific UoW to exist; before this phase every Project command ran on a raw,
shared `Session`. `delete_project` is a deliberate, source-justified exception mirroring P40B
Timesheet's own precedent: its Task/Dependency/Assignment/TimeEntry cascade is cross-capability
cleanup (Task stays out of scope), so it keeps the shared session via a bare
`SqlAlchemyUnitOfWorkBase` wrapper rather than moving cross-capability repos onto a foreign
session.

**The critical correctness fix: `set_status` previously persisted the status change but emitted
zero `project_changed` and had zero EnterpriseAudit coverage — the exact live bug P40A's own audit
flagged.** Closed directly with a typed `ProjectStatusChanged` plus atomic audit inside
`ProjectUnitOfWork`, no legacy-Signal intermediate step, per this ADR's own established principle
that a fix must land on the canonical mechanism, never a temporary bridge back to `Signal[str]`.
Gained an optional `expected_version` parameter for parity with `update_project`'s existing
explicit check (the DB-level `update_with_version_check` CAS already protected it implicitly via
`project.version`, so this closes a caller-visible-staleness and audit gap, not a silent-corruption
one) — confirmed by a genuine two-read/two-write concurrency test.

**A real, previously-latent atomicity bug found and fixed along the way, scoped narrowly.** The
established `record_activity(uow, ...)` call shape (used verbatim by Register/P41) leaves `commit`
at its own default of `True`, so `ActivityService.record()` commits early, *before* the same UoW's
event-dispatch/final commit runs — a later transactional-handler failure cannot roll back the
already-committed mutation. A dedicated Project transactional-handler-failure test caught this
directly. Fixed by passing `commit=False` on every `record_activity` call in Project's own
`lifecycle.py` and `project_resource_commands.py`, folding the Activity write into the same atomic
commit. Register's equivalent call sites were deliberately left untouched — out of P43's scope,
recorded as a known follow-up rather than silently fixed project-wide.

**P44A: a durable architectural rule — ephemeral coordination state MUST NOT be modeled as a
DomainEvent, even when it is persisted for TTL/coordination purposes.** Collaboration's
`collaboration_changed` legacy Signal mixed two categorically different things: 6 DURABLE
`TaskComment` mutations (create/edit/delete/react/unreact/mark-mentions-read) and 2 EPHEMERAL
`TaskPresence` operations (`touch_task_presence`/`clear_task_presence`). `TaskPresence` rows ARE
persisted (a real `task_presence` table, keyed `(task_id, username)`) and ARE queried through a
real read model (`list_task_presence`) — but a database row existing is not, by itself, evidence of
durable business history: presence has no `version` field, is blind-upserted, is TTL-windowed
(`last_seen_at >= now - N seconds`) at query time with no retained history once stale, and carries
zero EnterpriseAudit or Activity-feed coverage by design. **The rule this ADR now records:
"persisted for coordination/TTL purposes" and "durable business fact worth a DomainEvent" are
independent questions — never infer the second from the first.** The correct transport for such
state, established here as precedent for any future ephemeral/coordination feature: a direct,
synchronous `ViewInvalidationHint` notify (a real read-model projection legitimately went stale),
skipping the entire DomainEvent pipeline (no `uow.record_event`, no `TransactionalEventDispatcher`,
no `PostCommitEventPublisher`, no audit-trail implication) — narrower than a full DomainEvent, not
a workaround for lacking one. `ViewInvalidationHint`'s own category/scope-code namespacing (a new
`TASK_PRESENCE_CATEGORY`/`TASK_PRESENCE_SCOPE_CODE`, PM-owned vocabulary on the existing shared
transport shape, per this ADR's established shared-owns-transport/module-owns-vocabulary
principle) is sufficient to keep it fully distinct from every durable ViewInvalidation target
already in the system, with no new infrastructure required. `collaboration_changed` itself was
deliberately NOT deleted in this phase — category separation was the goal; the 6 durable
producers remain on it pending P44B's direct full modernization (audited and confirmed
one-phase-achievable: one aggregate, `TaskComment`, currently on a raw shared session with zero
audit of any kind — the largest audit gap found in any PM capability so far).

**P44B: durable `TaskComment` full modernization — `collaboration_changed` deleted.** One
aggregate (`TaskComment`), three semantically distinct event families rather than one catch-all:
`TaskCommentChanged(change_type=CREATED|EDITED|REMOVED)` (a shared family, mirroring
`RegisterEntryChanged`'s precedent — create/edit/soft-delete are the same kind of fact),
`TaskCommentReactionChanged(change_type=ADDED|REMOVED)`, and `TaskCommentReadStateChanged` (each
kept separate because each represents a genuinely different business fact, confirmed from source —
a reaction or read-receipt changing does not mean the comment's own content/existence changed).
New `CollaborationUnitOfWork` is the first canonical transaction owner this capability has ever
had (previously a raw shared `Session`, identical to Presence's own pre-P44A state); Enterprise
audit was added to all 6 durable operations where **zero** existed before — this ADR's audit
gap-tracking now shows Collaboration closed alongside Register/Portfolio/Project. A real latent
bug was found and fixed as a side effect of the UoW conversion, not sought out separately:
`post_comment`'s attachment-registration branch called into `DocumentIntegrationService`'s own,
always-separate `DocumentUnitOfWork` and, in doing so, skipped the comment's own session commit
entirely — silently leaving the comment row uncommitted whenever attachments were present. Fixed
by making the comment's own atomic transaction (mutation + audit + event) commit unconditionally,
first, before the pre-existing (unchanged) document-integration calls run afterward.
ViewInvalidation mapping deliberately does not treat all three event families alike:
`TaskCommentReactionChanged`/`TaskCommentReadStateChanged` stale only the exact task's own comment
list, while `TaskCommentChanged` additionally stales the organization-wide Collaboration workspace/
dashboard "recent activity" target — mapped by actual proven business meaning (does this fact
appear in the cross-project activity feed?), not uniformly, per this ADR's standing principle
against unproven broad ViewInvalidation fan-out. `collaboration_changed` is now fully deleted;
`tasks_changed` is the sole remaining PM legacy Signal, owned by Task's own future modernization.

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
