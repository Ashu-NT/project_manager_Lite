# Platform Domain Event Implementation Plan

- Status: draft — awaiting review. Not yet approved for implementation.
- Companion documents: [ADR-005: Domain Events](../../architecture_decisions/ADR-005-domain-events.md)
  (owns WHAT/WHY/semantics — this document does not re-litigate any decision made there, only
  applies it), [ADR-005 Execution Plan](../../architecture_decisions/ADR-005-execution-plan.md)
  (owns cross-Platform-and-module sequencing — this document's P0-P8 phases below implement that
  plan's single "Phase 2 — Platform Foundation"), [ADR-PF-008](../../architecture_decisions/ADR-PF-008-approval-unit-of-work.md),
  [ADR-PF-011](../../architecture_decisions/ADR-PF-011-durable-integration-outbox-inbox.md),
  [Platform Domain Event Audit](platform_domain_event_audit.md) (the evidence base).
- Scope: Platform only (`src/core/platform/`, `src/core/shared/`, `src/infra/`, `src/ui_qml/platform/`).
  No business module migration is planned or scoped here — see the execution plan's Phases 3-5.
- **This document is executable**: another engineer or Claude session should be able to implement
  every phase below without re-deriving any architectural decision. Where a genuinely new,
  narrow design question arose while writing this plan (not already resolved by ADR-005), it is
  resolved explicitly inline, tagged **PLAN DECISION**, with rationale — not left ambiguous.

## How to Use This Document

Each phase (P0-P8) is a self-contained unit of work with explicit exit criteria. Phases are
ordered by dependency, not by convenience — do not skip ahead. Every phase states its own
**Explicit Non-Goals** to prevent scope creep into adjacent, tempting-but-out-of-scope work (most
importantly: this migration is not a QML controller-hierarchy refactor, and it does not touch any
business module). Nothing in this plan is implemented yet — see the final validation section for
the current, unimplemented state confirmed.

## Human Approval Gates

**P0 → P8 does not run as one automatic, unattended implementation pass.** Each gate below
requires an explicit human review and go-ahead before the next group starts — this is a plan for
phased approval, not a script to execute end-to-end unsupervised. A phase's own "Exit criteria"
being met is necessary but not sufficient to proceed past a gate; the gate itself is where a human
reviews the actual diff, not just the checklist.

| Gate | After | Why this grouping | What review should focus on |
|---|---|---|---|
| **Gate 1** | P0 complete | Test-only phase — lowest risk, but the guardrail test's two exceptions must be reviewed by a human before anything is built on top of it | Does the guardrail test actually catch a reverted exception? Are the two allowlisted exceptions exactly the two the audit found — no more, no fewer? |
| **Gate 2** | P1-P2 complete | Contracts and infrastructure only, still nothing wired into production — but this is where the `EventScope`/`ScopeFilter` design and the `DomainEventContext` shape get locked in for everything downstream | Does the tenant/organization test matrix (below) actually pass against the concrete channel? Is the breadth-first-dispatch change clearly asserted as deliberate, not incidental? |
| **Gate 3** | P3 complete | **The fresh-session `UnitOfWork` is a major transaction-model change** — the first time anything in this codebase opens a session per transaction rather than per process. Isolated review before it has a real caller | Are the independent-session tests genuinely proving isolation, not just absence of an error? Is `MAX_DISPATCH_ROUNDS` failure behavior verified, not assumed? |
| **Gate 4** | P4-PRE's Step 1 complete (all 8 services) | **NEW, revised Round 8.** Porting 8 apply-handler-backing services' logic directly into session-parameterized participants is real, repetitive, easy-to-shortcut work — a review before Step 2 (the transaction cutover) begins catches a rushed or partial port before it's load-bearing | For each of the 8 services: does the ported participant reproduce the exact same business logic (staged mutation, validation, error behavior) as the deleted method, proven by the *existing*, unmodified approval regression suite passing? Are the old approval-facing methods actually deleted, not left dead? Is there a test confirming the ~22 out-of-scope PM/Inventory services, `ProjectCommitmentService`/`StockControlService`, and `Resource*UnitOfWork` were not touched? |
| **Gate 5** | P4-PRE's Step 2 + P4 complete | **`ApprovalService` migration is the highest-risk single phase in this plan** — it changes a live, accepted (ADR-PF-008), financially-adjacent transaction boundary, and every module with a registered apply handler must be updated in the same change | Are ALL registered apply handlers (PM, Inventory, any other module) actually updated, not just a sample? Does the failure-injection suite prove atomicity under the fresh-session model as rigorously as ADR-PF-008 required for the old one? Is the `dependencies_factory` mechanism (§ P4, revised Round 7/8) actually narrow, or has it grown back into a general lookup? Did `request_change()` migrate in this same change, not before or after? Has the legacy shared-session apply-handler construction path actually been removed (it should already be gone since Step 1)? |
| **Gate 6** | P5-P6 complete | Typed events and the Qt adapter together — P6 depends on at least one real P5 event, so reviewing them separately would be artificial | Is every one of Platform's 11 signals in the discovery table actually classified with evidence, not guessed? Does the Qt adapter genuinely leave the other two controller bases and the non-invalidation responsibilities of Platform's own base untouched? |
| **Gate 7 (final)** | P7-P8 complete | This is the "Platform Domain Event Foundation Ready" declaration — the gate every business module migration (Execution Plan Phase 3 onward) is blocked on | Does the full TO-1..TO-14 matrix pass against real, migrated Platform signals, not only synthetic fixtures? Is there genuinely no uncited legacy dependency left? |

No implementation work covered by this document proceeds past a gate without that gate's review
having actually happened — a phase's own internal "Exit criteria" is what the implementer checks
before requesting the gate review; it is not a substitute for it.

## Cross-Cutting Requirements (apply to every phase below)

### File and Test Conventions

- Every new production file under `src/core/shared/`, `src/core/platform/`, `src/infra/`, or
  `src/ui_qml/platform/` gets a corresponding test file under the mirrored path in `src/tests/`.
- No new file imports `PySide6`/`ui_qml` from `src/core/platform/{domain,application}/` or
  `src/core/shared/` (unchanged rule, now enforced by the P0 guardrail test rather than manual
  review).
- No new file constructs a concrete SQLAlchemy repository or exposes a raw `Session` from
  anything typed as `UnitOfWork` (base or Platform-extended). `UnitOfWork` never gains a generic
  `repository_for(contract)`-style method — see P4's `dependencies_factory` design (ADR-005 §24,
  Round 7) for the one, narrow, `ApprovalService`-specific mechanism that resolves the one genuine
  cross-module need this codebase has, without turning `UnitOfWork` into a service locator.

### The Tenant + Organization Test Matrix (referenced by every phase from P1 onward)

**Revised to match ADR-005 §12's typed-`EventScope`/`ScopeFilter` design** (a critical review
replaced the earlier five-method `ViewInvalidationChannel` API with one `subscribe(filter,
handler)` method parameterized by a small, closed `ScopeFilter` hierarchy — see ADR-005 §12 for
the full design and rationale). Every phase that introduces or migrates an event/hint type must
pass this matrix for that type, per ADR-005 §12/Test Impact and Execution Plan Constraint 6.
Stated once here, referenced by ID from each phase below rather than repeated verbatim:

| ID | Scenario | Expected result |
|---|---|---|
| TO-1 | `ViewInvalidationHint(scope=OrganizationScope("A", "A1"), ...)` published | Reaches a subscriber registered via `subscribe(ExactOrganization("A", "A1"), handler)` |
| TO-2 | Same hint as TO-1 | Does **not** reach a subscriber registered via `subscribe(ExactOrganization("A", "A2"), handler)` |
| TO-3 | Same hint as TO-1 | Does **not** reach any Tenant B subscriber, registered any way (unless via `AllTenants()`) |
| TO-4 | Same hint as TO-1 | Reaches a subscriber registered via `subscribe(AnyOrganizationInTenant("A"), handler)` |
| TO-5 | Same hint as TO-1 | Does **not** reach a subscriber registered via `subscribe(TenantWide("A"), handler)` |
| TO-6 | `ViewInvalidationHint(scope=TenantScope("A"), ...)` (genuinely tenant-wide fact) published | Reaches `TenantWide("A")` and `AnyOrganizationInTenant("A")` subscribers |
| TO-7 | Same hint as TO-6 | Does **not** reach any `ExactOrganization("A", ...)` subscriber, for any organization value |
| TO-8 | Any tenant-scoped `ViewInvalidationHint` (`TenantScope` or `OrganizationScope`) | Reaches every `AllTenants()` subscriber regardless of its actual tenant/organization; a `PlatformScope`-scoped hint does **not** reach `AllTenants()` (§ TO-9 covers `PlatformScope` separately) |
| TO-9 | `ViewInvalidationHint(scope=PlatformScope(), ...)` published | Reaches only `PlatformWide()` subscribers; never reaches `AllTenants()`, `TenantWide(...)`, `AnyOrganizationInTenant(...)`, or `ExactOrganization(...)` subscribers |
| TO-10 | `OrganizationScope("A")` (missing `organization_id`) or `TenantScope("A", organization_id="A1")` construction attempts | **Structurally impossible, not merely rejected** — a construction-time `TypeError` from the dataclass's own required-argument signature, not a runtime validation check inside the channel or a downstream dispatch-time surprise |
| TO-11 | A command that mutates Organization A1 while the desktop session's "current organization" UI state is set to A2 | The resulting event's/hint's scope is `OrganizationScope(tenant_id, "A1")` (read from the mutated aggregate/command), never `"A2"` — never derived from mutable session state |
| TO-12 | Organization switch in the desktop application mid-session | A controller subscribed via `ExactOrganization` for the previously-active organization does not receive hints for the newly-active one until it re-subscribes; no stale cross-organization subscription lingers (disposal proven, not assumed) |
| TO-13 **(new)** | A mutation known to affect exactly `{A1, A2}` within Tenant A, not A3 | Represented as **two** `notify()` calls, each `ViewInvalidationHint(scope=OrganizationScope("A", ...), ...)` — one for A1, one for A2 — **never** a single `TenantScope("A")` hint; an `ExactOrganization("A", "A3")` subscriber receives neither call (§3a) |
| TO-14 **(new)** | Code-level review of every `TenantScope`/`PlatformScope` construction site introduced in P5 | Each one is an explicit, deliberate construction at a point where the fact is genuinely known to be tenant-wide or platform-wide — **never** a fallback/default path reached because an `organization_id` happened to be unavailable or omitted. This is a review-time check (does the surrounding code *decide* tenant-wide-ness, or *arrive at it by omission*?), not something a unit test alone can fully prove — but a unit test can and must assert that no helper function silently converts "organization unknown" into `TenantScope` |

### The Architecture Guardrail Test

One AST-based test, using the existing technique already proven in
`src/tests/architecture/test_qml_architecture_guardrails_layers.py`:

```python
# src/tests/architecture/test_platform_does_not_import_business_modules.py (new, P0)
GOVERNED_EXCEPTIONS = {
    "src/core/platform/application/time_management/calendar/assignment/calendar_assignment_service.py":
        "ADR-004: Calendar Assignment Split Ownership",
    "src/core/platform/infrastructure/persistence/repositories/approval/approval.py":
        "ADR-005 §22: pre-existing, separately tracked debt — SqlAlchemyApprovalRepository "
        "imports ProjectORM directly; no project-scoping contract exists yet. "
        "DO NOT add a new exception to this dict without an equivalent governing citation.",
}

def test_platform_core_does_not_import_business_modules() -> None:
    # Walk the WHOLE src/core/platform/**/*.py tree (domain, application, infrastructure,
    # contract, api, etc. -- not domain/application only; see the P0 implementation note
    # below for why the scope was corrected from an earlier draft), ast.parse each file,
    # ast.walk for Import/ImportFrom nodes whose module starts with "src.core.modules.",
    # fail with the offending file:line unless the file's relative path is a key in
    # GOVERNED_EXCEPTIONS above.
    ...
```

Any PR adding a new exception must add a citation to this dict in the same change, and that
citation must reference an accepted ADR — not merely a comment.

**P0 implementation note (documentation correction, not a new decision):** an earlier draft of
this section scoped the walk to `src/core/platform/{domain,application}/` only. That was
inconsistent with `GOVERNED_EXCEPTIONS` itself — `.../infrastructure/persistence/repositories/
approval/approval.py` lives under `infrastructure/`, which a domain/application-only scan would
never reach, making the exception meaningless. Corrected when P0 was actually implemented to scan
the whole `src/core/platform/` tree — confirmed against the real codebase that this surfaces
exactly the same two violations already listed above, no more.

## P0 — Architecture Guardrails and Baseline Tests

**Goal:** establish the one missing piece of enforcement the audit found, and characterize
today's legacy behavior precisely enough that later phases can prove they haven't silently
changed something no one noticed depended on it.

**Architectural decision being implemented:** ADR-005 §21 (Architecture Guardrails).

**Exact expected files:**
- `src/tests/architecture/test_platform_does_not_import_business_modules.py` (new)
- `src/tests/platform/test_legacy_signal_characterization.py` (new — pins down current `Signal.emit()`
  behavior: depth-first-under-recursion, fail-fast on non-Qt exceptions, Qt-deleted-object
  auto-pruning, no logging — as an explicit regression baseline, not a design endorsement)

**Files likely modified:** none in `src/core/` or `src/infra/` or `src/ui_qml/` — test-only phase.

**Dependencies/prerequisites:** ADR-005 accepted.

**Production behavior affected:** none.

**Compatibility behavior:** none — purely additive tests.

**Tests to add:** both files above. The guardrail test must fail loudly (not silently pass) if
someone deletes an entry from `GOVERNED_EXCEPTIONS` while the corresponding import still exists —
i.e., the test itself must be exercised once against a deliberately-reverted exception during
review to prove it actually catches the violation it's meant to catch.

**Failure scenarios:** a future PR adds a new Platform→module import with no citation → guardrail
test fails with a clear message naming the offending file and pointing at
`GOVERNED_EXCEPTIONS`.

**Tenant + organization scenarios:** none yet — no event/hint types exist at this phase.

**Exit criteria:** both new tests pass against current, unmodified code; the guardrail test's
two exceptions are exactly the two the audit found, no more, no fewer.

**Explicit non-goals:** no contract code, no event classes, no `UnitOfWork` code. Do not fix the
`SqlAlchemyApprovalRepository → ProjectORM` violation — allowlist it with its citation, per
ADR-005 §22.

**Rollback/recovery:** trivial — delete the two new test files if this phase needs to be reverted;
nothing else is affected.

## P1 — Shared Contracts

**Goal:** create the Core Shared contracts ADR-005 defines, with zero behavior change (nothing
wired in, nothing imports these yet).

**Architectural decision being implemented:** ADR-005 §4 (Domain Event Contract), §5 (Event
Metadata Decision), §6 (Event Recording Decision), §7 (Transactional Dispatch, contract only),
§8 (Post-Commit Publication, contract only), §12 (View Invalidation, contract only).

**Exact expected files:**
```text
src/core/shared/events/
  domain_event.py              # DomainEvent marker Protocol
  domain_event_context.py      # DomainEventContext frozen dataclass
  aggregate_events.py          # RecordsDomainEvents mixin
  domain_event_publisher.py    # TransactionalEventDispatcher + PostCommitEventPublisher protocols
  domain_event_subscriber.py   # TransactionalEventHandler/PostCommitEventHandler +
                                #   TransactionalEventSubscriber/PostCommitEventSubscriber protocols
  subscription.py              # Subscription protocol (dispose)
  view_invalidation.py         # EventScope/PlatformScope/TenantScope/OrganizationScope,
                                #   one ViewInvalidationHint (carrying scope: EventScope),
                                #   ScopeFilter + its 5 concrete filter dataclasses
                                #   (ExactOrganization/TenantWide/AnyOrganizationInTenant/
                                #   AllTenants/PlatformWide), ViewInvalidationHandler,
                                #   ViewInvalidationChannel (single notify/subscribe contract)
src/core/shared/time/
  clock.py                     # Clock protocol
```

**Files likely modified:** none — all new files, zero existing imports touched.

**Dependencies/prerequisites:** P0 complete (guardrail test exists so nothing added here can
silently violate it).

**Production behavior affected:** none.

**Compatibility behavior:** none — additive only, nothing consumes these yet.

**Tests to add:** structural tests only at this phase (protocol conformance, dataclass
immutability; that `OrganizationScope` genuinely cannot be constructed without `organization_id`,
and `TenantScope` genuinely has no `organization_id` field to pass — TO-10). The full tenant/org
*routing* matrix (TO-1 through TO-9, TO-13) is exercised against the **concrete** channel in P2,
not here — P1 has no concrete implementation to route anything through yet.

**Failure scenarios:** none applicable — no behavior exists yet to fail.

**Tenant + organization scenarios:** TO-10 is testable at this phase (construction-time type
checking on a worked example event class), the rest are deferred to P2.

**Exit criteria:** every file above exists with passing structural tests; `git diff` touches
nothing outside `src/core/shared/events/` and `src/core/shared/time/`; the app boots unchanged.

**Explicit non-goals:** no concrete `InProcess*` implementations (P2). No `UnitOfWork` (P3). No
wiring into `platform_registry.py`/`app_container.py` (P4 onward).

**Rollback/recovery:** trivial — delete the new directory trees; nothing imports them yet.

## P2 — In-Process Infrastructure

**Goal:** build the concrete, technology-agnostic implementations of P1's contracts, including
the full tenant/organization routing logic.

**Architectural decision being implemented:** ADR-005 §7 (stateless transactional dispatcher),
§8 (queued, race-fixed post-commit bus, breadth-first, explicit deliberate change from legacy
depth-first), §12 (`ViewInvalidationChannel`'s single `notify`/`subscribe` contract, its
`EventScope`/`ScopeFilter` routing model, and the `matches()`-based dispatch this implementation
must not branch on by hand).

**Exact expected files:**
```text
src/infra/events/
  in_process_transactional_event_dispatcher.py
  in_process_post_commit_event_bus.py
  in_process_view_invalidation_channel.py
src/infra/time/
  system_clock.py
```

**Files likely modified:** none.

**Dependencies/prerequisites:** P1.

**Production behavior affected:** none — still not wired into any real service.

**Compatibility behavior:** none.

**Tests to add:**
- `TO-1` through `TO-9` (channel routing) against `InProcessViewInvalidationChannel` directly.
- Post-commit bus: the original ADR-005 test set — empty-queue/`_dispatching`-flip race (an
  adversarial test forcing the exact interleaving), lock-held handler-registry snapshot semantics
  under concurrent subscribe/dispose, one failing adapter doesn't block another, two threads
  calling `publish()` concurrently don't corrupt the queue or double-dispatch.
- **Explicit breadth-first assertion**: register three handlers for the same event type where the
  first handler's callback itself calls `publish()` on a second event; assert the second event's
  handlers run only after all of the first event's handlers have completed — with an inline
  comment noting this is a deliberate design choice, contrasted against the legacy `Signal`'s
  depth-first-under-recursion behavior pinned down in P0's characterization test.
- Transactional dispatcher: stateless under concurrent `dispatch(event, uow)` calls with different
  `uow`s (confirms no cross-transaction bug is possible by construction, since there is no shared
  per-call state to corrupt).

**Failure scenarios:** a handler raising inside `InProcessPostCommitEventBus` is caught, logged,
and does not block sibling handlers or subsequent events (ISOLATE_AND_CONTINUE); a handler raising
inside `InProcessTransactionalEventDispatcher.dispatch` propagates immediately (FAIL_FAST) — both
proven by dedicated tests, not inferred from code reading.

**Tenant + organization scenarios:** TO-1 through TO-9 and TO-13, fully, against the concrete
channel (TO-13 synthetically: two `notify()` calls with different `OrganizationScope`s, asserting
neither reaches an `ExactOrganization` subscriber for a third, unaffected organization).

**Exit criteria:** every file above exists with passing tests, including the full TO-1..TO-9 and
TO-13 matrix and the breadth-first assertion; `git diff` touches only `src/infra/events/` and
`src/infra/time/`; the app boots unchanged (still nothing imports these in production code paths).

**Explicit non-goals:** no `UnitOfWork` (P3). No real Platform service uses any of this yet.

**Rollback/recovery:** trivial — delete the new files; nothing production-facing references them.

## P3 — UnitOfWork Foundation

**Goal:** reclaim the dead `session_scope()` file into the real, physical `UnitOfWork`
implementation, and prove the session-factory shape works end-to-end with a throwaway subclass.

**Architectural decision being implemented:** ADR-005 §9 (UnitOfWork Semantics), §10 (dynamic
aggregate discovery, `MAX_DISPATCH_ROUNDS`), §5/§6 (`context` property, `record_event`).

**Exact expected files:**
```text
src/core/shared/persistence/
  unit_of_work.py               # UnitOfWork + UnitOfWorkFactory protocols
src/infra/persistence/db/
  unit_of_work.py                # REPLACED: SqlAlchemyUnitOfWorkBase (session lifecycle,
                                  #   id()-keyed aggregate tracking, dispatch/outbox coordination,
                                  #   context property, record_event) — module/capability-agnostic
```

**Files likely modified:**
- `src/infra/composition/app_container.py` — additive plumbing so `build_service_graph` *can*
  construct a `SqlAlchemy<Name>UnitOfWorkFactory` per migrated capability/module; no real factory
  exists yet (that's P4's first real consumer).

**Dependencies/prerequisites:** P1, P2.

**Production behavior affected:** none — `session_scope()` had zero callers (confirmed twice by
the audit), so reclaiming its file has no runtime effect until P4 adds a real consumer.

**Compatibility behavior:** none.

**Tests to add:** two independent `create()` calls open genuinely independent `Session`s
(committing/rolling back one has no effect on the other); rollback discards tracked aggregate
instances and they are never reusable in a later `UnitOfWork`; `register_touched` accepts a
`RecordsDomainEvents` subclass that defines `__eq__` without `__hash__` (unhashable) without
raising, dedups by identity not equality; `record_event(event)` stages an application-authored
event that the next collection round picks up alongside aggregate-recorded ones; a deliberately
cyclical transactional-handler setup (handler A's dispatch causes handler B to record a new event
that re-triggers handler A) fails loudly at `MAX_DISPATCH_ROUNDS` rather than hanging; `uow.context`
returns exactly what `UnitOfWorkFactory.create(context=...)` was given.

**Failure scenarios:** an exception during a `with uow:` block rolls back and discards the
`UnitOfWork`'s tracked aggregates; a `MAX_DISPATCH_ROUNDS` overflow raises a specific, named
exception (not a bare `RecursionError` or silent truncation).

**Tenant + organization scenarios:** none new at this phase — `DomainEventContext` doesn't carry
tenant/organization (that lives on the events themselves, per ADR-005 §5), so this phase's tests
are transaction-mechanics-only.

**Exit criteria:** app boots; `SqlAlchemyUnitOfWorkBase` is constructible (via a throwaway test
subclass) and produces a genuinely fresh session per `create()` call, tested not assumed; zero
real Platform services reference it yet.

**Explicit non-goals:** no real Platform capability gets its own `UnitOfWork` subclass yet (P4).
No aggregate in Platform adopts `RecordsDomainEvents` yet (P5).

**Rollback/recovery:** since `session_scope()` had zero callers, reverting this phase is
equivalent to restoring the old file content — no production code path is affected either way.

## P4-PRE — Approval Transaction-Participant Convergence (revised Round 8 — 2 direct steps)

**Goal:** port each of the 18 real approval apply/reject handlers' logic directly into
standalone, session-parameterized participants (no legacy-session adapter stage), so that P4 can
cut `ApprovalService` over to a genuinely fresh session.

**Architectural decision being implemented:** ADR-005 §24 (Round 8) — the revised
`dependencies_factory` mechanism, built directly per Round 8's pre-release scope decision, not
Round 7's four-step, adapter-first sequencing. Execution Plan Phase 2A-PRE (revised).

**Why this phase exists, and why it is two steps, not four (evidence, not assumption):** the
original P4A investigation inventoried all 18 real `register_apply_handler`/
`register_reject_handler` registrations and found every one calls into one of 8 long-lived
application services (`BaselineService`, `TaskService`, `BudgetService`, `ProjectCostEntryService`,
`FinancialChangeService`, `ProjectBillingPreparationService`, `ProcurementService`,
`PurchasingService`), each bound to the single process-lifetime `Session` and each holding a
circular `approval_service=platform_services.approval_service` constructor reference (confirmed
8-for-8). Round 7 staged the fix as four steps (extract an adapter still on the shared session;
separately make it session-parameterizable; cut `ApprovalService` over; delete the old path)
specifically to prove parity before touching transaction mechanics — appropriate caution for a
live system. **An explicit user decision established this application is pre-release, with no
external users and no backward-compatibility requirement for the current process-lifetime
`Session` architecture** — building a Step-A adapter only to delete it again once its
session-parameterized replacement exists (Step B) is exactly the "temporary architecture that will
immediately be deleted" that decision rejects. Steps A and B collapse into one direct step; Steps C
and D (unchanged in substance) become Step 2.

A wider, 30-service PM/Inventory audit (performed to confirm this stays correctly scoped, not
sized by assumption) found: ~20 services are pure transaction-owning commands with no
approval relationship at all (`ProjectService`, `PortfolioService`, `CollaborationService`,
`RegisterService`, `ProjectResourceService`, `ProjectRateCardService`, `PlannedCostService`,
`ProjectBillingProfileService`, `ForecastVersionService`, `ForecastGenerationService`,
`FinancialConfigurationService`, `ReservationService`, `InventoryService`,
`InventoryFoundationService`, and others) — **explicitly out of scope**, their migration is
Execution Plan Phase 3/5's job; `ProjectCommitmentService` and `StockControlService` already have
the identical `commit: bool` staging pattern as the 8 but no relationship to approval —
**explicitly out of scope**, flagged as separately-tracked debt exactly like §22's allowlisted
`SqlAlchemyApprovalRepository`→`ProjectORM` violation; `project_management`'s own
`ResourceMasterUnitOfWork`/`ResourceCapabilityUnitOfWork` are confirmed (by direct read) to be
built with an already-created `Session`, not a session factory, and are themselves not real Units
of Work by ADR-005 §9's definition — **explicitly out of scope**, unrelated to this phase;
`build_repository_bundle(session)` already returns all 69 repository fields spanning every PM,
Inventory, and Platform repository these 30 services use — confirming the repository-construction
half of a fresh-session convergence was never the hard part.

### Step 1 — Build `PlatformUnitOfWork`/`Factory`; port each of the 8 services' approval-facing logic into standalone, session-parameterized participants

For each of the 8 services, the approval-facing logic currently living as a method on the
long-lived instance (`_apply_*_decision`/`apply_submitted_*_approval`/
`apply_submitted_*_rejection`) is **ported** — moved and adapted, not delegated-to via a
resurrected copy of the whole service — into a small, module-owned participant (a plain function
or thin stateless class) whose repositories/collaborators are constructed fresh, per call, from
the session `ApprovalService`'s `PlatformUnitOfWork` supplies via
`dependencies_factory(session) -> TDeps`. A participant is not the whole service object, so **it
never holds an `approval_service=` reference at all** — the old service instance (unchanged, still
used for its own other, non-approval commands) keeps its existing reference as-is. The now-dead
old approval-facing methods are **deleted from the 8 service classes in this same step** — not
left unused pending a later cleanup pass, since dead code awaiting deletion is itself temporary
architecture.

**Exact expected files:**
```text
src/core/modules/project_management/infrastructure/approval/
  baseline_apply_participant.py, task_apply_participant.py, budget_apply_participant.py,
  project_cost_apply_participant.py, financial_change_apply_participant.py,
  billing_preparation_apply_participant.py
src/core/modules/inventory_procurement/infrastructure/approval/
  procurement_apply_participant.py, purchasing_apply_participant.py
src/infra/composition/approval_apply_dependencies/
  project_management.py   # build_baseline_approval_deps, build_task_approval_deps,
                           #   build_budget_approval_deps, build_project_cost_approval_deps,
                           #   build_financial_change_approval_deps,
                           #   build_billing_preparation_approval_deps
  inventory_procurement.py  # build_procurement_approval_deps, build_purchasing_approval_deps
```

**Files modified:** `project_registry.py:709-932` / `inventory_registry.py:253-268` register the
new participants via `dependencies_factory=`; the 8 service classes lose their now-dead
approval-facing methods.

**Tests to add:** the existing PM/Inventory approval regression suite (per ADR-PF-008's own test
discipline) passes unmodified against the new participants — this is the parity proof, since the
suite exercises real `approve_and_apply`/`reject` flows end-to-end; a test per participant proving
it constructs its own repositories fresh (never reaches into the old service instance); a test
confirming none of the other 22 PM/Inventory services, `ProjectCommitmentService`/
`StockControlService`, or `Resource*UnitOfWork` were touched.

**Exit criteria:** all 8 participants exist and are registered; the 8 old approval-facing methods
are deleted (not merely unused); full existing approval regression suite green; the ~22
out-of-scope services are provably unchanged (`git diff` scoped check).

### Step 2 — Cut `ApprovalService` over to `PlatformUnitOfWork` (this is P4 itself, below)

Only begins once Step 1 is reviewed (Gate 4) for all 8 services. See P4, below, for the full
detail — P4's content **is** this step, restated at the granularity P4 already specifies.

**Dependencies/prerequisites:** P3.

**Production behavior affected:** through Step 1, none for `ApprovalService` itself — it still
commits on the shared session; the 8 services' approval-facing behavior is exercised through the
new participants but should be observably identical (proven by the unmodified regression suite).
Step 2's production impact is P4's own, described there.

**Explicit non-goals:** does not migrate any of the ~22 out-of-scope PM/Inventory services listed
above. Does not converge `ProjectCommitmentService`/`StockControlService`. Does not touch
`Resource*UnitOfWork`. Does not remove the process-lifetime `Session` from `app_container`/
`build_service_graph` — **that can only happen once Execution Plan Phase 3
(`inventory_procurement`) and Phase 5 (`project_management`) have both closed**, migrating every
other command in the application off that shared session; this phase removes only the
approval-apply path's own dependency on it. Does not change any of the 8 services' approval
*business rules* — the logic is ported, not rewritten.

**Rollback/recovery:** reverting Step 1 means restoring the deleted methods on the 8 service
classes and reverting the two registration files — a mechanical revert, since the ported logic is
unchanged business behavior, only its location and construction model.

## P4 — Platform Transaction Convergence

**Goal:** migrate Platform's own competing transaction conventions onto the canonical
`UnitOfWork`, per ADR-005 §24's explicit reconciliation. **Assumes P4-PRE's Step 1 is complete and
reviewed (Gate 4) for all 8 approval apply-handler-backing services** — this phase is Step 2 of
P4-PRE.

**Architectural decision being implemented:** ADR-005 §24 (`ApprovalService`: **ADAPT**).

### P4 Design Resolution — the cross-module apply-handler problem (**PLAN DECISION, revised twice**)

**This section supersedes two earlier drafts of this plan.** The first proposed
`PlatformUnitOfWork.repository_for(contract: type[R]) -> R` — an open, contract-keyed lookup any
handler could call with any repository contract type at any point in its body. **A critical
architecture review correctly identified this as a hidden general-purpose service locator**:
`uow.repository_for(ProjectRepository)`, `uow.repository_for(EmployeeRepository)`,
`uow.repository_for(AnythingAtAll)` — which would make a handler's real dependencies invisible at
its registration site, undiscoverable by the architecture guardrail test (P0), and hard to unit
test without faking an entire `UnitOfWork`'s lookup behavior. This directly contradicts ADR-005
§9's own principle: `UnitOfWork` exposes the transaction boundary; it must not become a general
application dependency container.

**The second draft (this document's original P4, ADR-005 §24 Round 6) replaced it with a
repository-shaped `TDeps` resolved from a generic binder registry — also superseded.** A
pre-implementation investigation (required by this document's own instruction to inspect real
source before writing code) inventoried all 18 real `register_apply_handler`/
`register_reject_handler` registrations and found every one calls into a long-lived PM/Inventory
*application service* (8 distinct services), never a bare repository, with every one of the 8 also
holding a circular `approval_service=` reference back to `ApprovalService` itself. A
repository-shaped `TDeps` sits one layer below where every real handler actually operates — see
ADR-005 §24 (Round 7) for the full evidence and reasoning. **The design below is the Round 7
revision: `dependencies_factory: Callable[[Session], TDeps]`, module-supplied, not a repository
bundle resolved from a generic registry.** P4-PRE (above) is the new, separately gated phase this
revision requires before this section's mechanism has anything real to attach to. **`repository_for` is removed from this plan entirely — no
version of it ships in any phase.**

The underlying problem is still real and still needs solving: `ApprovalService.approve_and_apply`
invokes apply handlers registered by *other* modules (PM's baseline/dependency/cost handlers,
Inventory's requisition/PO handlers) that today mutate those modules' own repositories directly,
sharing Platform's single process-lifetime `Session`. Moving `ApprovalService` onto a genuinely
fresh, per-call `Session` (required for it to be a real `UnitOfWork` per ADR-005 §9) means those
module-owned handlers need a way to reach their own repository *contracts* bound to that same
fresh session.

**Decision (ADR-005 §24, Round 7): an explicit, per-handler dependency *factory*, supplied by the
owning module and invoked by `ApprovalService`'s own dispatch logic — never a method on
`UnitOfWork` itself, and never a generic registry keyed by type.**

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
    dependencies_factory: Callable[[Session], TDeps],   # module-owned; builds TDeps fresh,
                                  #   bound to the CURRENT approve_and_apply/reject call's session
) -> None: ...
```

`PlatformUnitOfWork` itself stays minimal — it does **not** gain `repository_for` or any
equivalent open lookup:

```python
class PlatformUnitOfWork(UnitOfWork, Protocol):
    approvals: ApprovalRepository   # Platform's own repository, a named accessor like any
                                      #   other module's UnitOfWork extension — nothing special
```

`TDeps` is declared **at the same call site** as `register_apply_handler` — e.g.
`project_management` declares `build_budget_approval_deps(session: Session) -> BudgetApprovalDeps`
(a P4-PRE Step B deliverable) and registers with `dependencies_factory=build_budget_approval_deps`.
`ApprovalService` calls that factory directly, at dispatch time, passing the current call's fresh
session — there is no generic, type-keyed binder registry to populate or consult.
`build_budget_approval_deps` is free to reconstruct the module's own existing `BudgetService`
(unchanged business logic) bound to the supplied session, using `build_repository_bundle(session)`
for its repositories, and to keep the service's outbound `approval_service=` reference pointed at
the *original* long-lived `ApprovalService` (P4-PRE Step B) — the handler itself only ever
receives a fully-constructed `deps: TDeps`, typed against contracts, never a raw `Session` and
never a method it could call with an arbitrary type.

**Allowed usage:** only `ApprovalService`'s own internal dispatch logic calls a handler's
registered `dependencies_factory`. **Forbidden usage:** no handler body calls anything resembling
an open lookup or a generic `resolve(TDeps)`; no such method exists on `UnitOfWork`, base or
Platform-extended, in any phase of this plan. No other module's `UnitOfWork` extension gains an
equivalent mechanism — this is scoped to `ApprovalService`'s own registration API, not offered as
a reusable pattern.

**Rationale:** preserves ADR-PF-008's core atomicity guarantee (approval decision + module
mutation commit together, in one physical transaction) while achieving ADR-005's fresh-session and
framework-agnostic-handler goals, and keeps a handler's dependencies statically visible at its own
registration call site — a reviewer or a future static-analysis pass can read
`register_apply_handler(..., dependencies_factory=build_budget_approval_deps)`, then read that one
factory function, and know exactly what that handler can reach and how it is built, without
tracing runtime calls through its body or cross-referencing a separate registry. **Alternatives
considered:** (a) the rejected `repository_for(contract)` open lookup, above; (b) a
repository-shaped `TDeps` resolved from a generic, type-keyed binder registry (this document's own
original P4 design, ADR-005 §24 Round 6) — rejected after the real apply-handler inventory found
every one of the 18 registrations calls into a long-lived application service, never a bare
repository, making the repository-shaped design one layer too low; (c) give `ApprovalService`'s
handlers a raw `Session` — rejected, breaks ADR-005 §7/§9's core guarantee outright; (d) don't
migrate `ApprovalService` to a fresh session at all, keep it on the shared process-lifetime session
forever — rejected as PERMANENTLY KEEP DISTINCT in disguise, which ADR-005 §24 already rejected;
(e) require every module with an apply handler to also expose a `PlatformUnitOfWork`-compatible
extension ahead of time — rejected as unnecessarily rigid given apply handlers are registered
dynamically per `request_type`, not known statically at `PlatformUnitOfWork`'s own definition time.
**Testing implications:** a handler is unit-tested by constructing its own `TDeps` directly with
fakes — no need to fake an entire `PlatformUnitOfWork`, a binder registry, or intercept a lookup
method.

**Exact expected files:**
```text
src/core/platform/contracts/
  unit_of_work.py                       # PlatformUnitOfWork (minimal — just `approvals`) +
                                         #   PlatformUnitOfWorkFactory
  approval.py                           # ApprovalApplyHandler[TDeps] protocol,
                                         #   register_apply_handler(..., dependencies_factory=...)
src/core/platform/infrastructure/persistence/
  unit_of_work.py                       # SqlAlchemyPlatformUnitOfWork(SqlAlchemyUnitOfWorkBase),
                                         #   SqlAlchemyPlatformUnitOfWorkFactory
```

**No `dependency_binder_registry.py`** — the earlier draft's generic, type-keyed binder registry
is removed per the Round 7 revision above; each handler's `dependencies_factory` is supplied
directly at its own `register_apply_handler(...)` call site (P4-PRE Step B produces these), with
nothing for `ApprovalService` to consult beyond the one factory function registered alongside that
handler.

**Files likely modified:**
- `src/core/platform/application/approval/approval_service.py` — `approve_and_apply`/`reject`
  construct a `PlatformUnitOfWork` via the injected factory instead of using `self._session`
  directly; look up the registered handler's `dependencies_factory` for the request's
  `request_type`, call it with the current call's session to obtain `deps: TDeps`, and call
  `handler(request, uow, deps)` — no `uow.repository_for(...)`-style call or generic resolve
  exists anywhere; `ApprovalHandlerResult.post_commit_events` changes shape from
  `(signal_name: str, payload: str)` to `tuple[DomainEvent, ...]` (typed events, no more
  string-keyed reflection into the legacy bus).
- `src/core/platform/domain/approval/*` — if `ApprovalRequest` itself should record its own
  `ApprovalDecided`/`ApprovalRejected` events via `RecordsDomainEvents` (assessed per the P5
  criteria table below — approval decisions are a strong candidate for aggregate-recorded events,
  since "an approval request transitioned to APPROVED" is exactly an aggregate invariant/state
  transition per ADR-005 §6's criteria).
- `src/infra/composition/platform_registry.py` — construct `SqlAlchemyPlatformUnitOfWorkFactory`
  (closing over `SessionLocal` and a `DomainEventContext` supplied per call); each existing
  `register_apply_handler(request_type, handler)` call site (per P4-PRE Step B) gains
  `dependencies_factory=build_<x>_approval_deps` — no separate binder-registry population step.
- `src/core/platform/application/events/notifications/notification_service.py` — assessed per
  call site: `dispatch(commit=True)` sites that compose with a migrating command move onto
  `uow.commit()` instead of an independent second commit (closing the audit's PLAT-UOW-003
  two-non-atomic-commits finding for those specific call sites); standalone notification sends
  unrelated to any migrating command are left as-is, since `NotificationService` itself is
  explicitly out of this ADR's taxonomy (ADR-005 §1).
- `src/core/platform/common/service_base.py` — its one real subclass
  (`project_management/infrastructure/reporting/services/reporting_service.py`) is **out of
  Platform's own scope** (it's module-owned code); `ServiceBase.commit()` itself is left
  unmodified in this phase — assessed only, not migrated, since its only real consumer belongs to
  a business module's own future migration phase, not Platform's.

**Dependencies/prerequisites:** P3.

**Production behavior affected:** `ApprovalService.approve_and_apply`/`.reject` now open a fresh
`Session` per call instead of sharing the process-lifetime one; observable effect should be none
under correct implementation (same commit/rollback semantics, same atomicity guarantee) — proven
by the failure-injection tests below, not assumed.

**Compatibility behavior:** `ApprovalHandlerResult.post_commit_events`'s shape change is a
breaking change to every registered apply handler across every module that has one (PM
baseline/dependency/cost, Inventory requisition/PO, per ADR-PF-008's own implementation evidence)
— **this phase must update every existing registered handler in the same change**, per Constraint
3 (no straddling): a handler still returning the old `(signal_name, payload)` shape after this
phase closes is a bug, not a supported transitional state. `domain_events.approvals_changed`
(the legacy Signal) continues to fire during this phase via an explicit, time-boxed bridge adapter
inside the new `PostCommitEventPublisher` registration (translating the new typed
`ApprovalDecided`/`ApprovalRejected` events into the old signal's `.emit(request.id)` call) — this
bridge is deleted in P7 once every consumer of the legacy `approvals_changed` signal has migrated
to the new `ViewInvalidationChannel`.

**Tests to add:** failure injection before/after handler staging, audit, outbox, and decision
update (mirroring ADR-PF-008's own existing test discipline, now against the fresh-session
`UnitOfWork`) — cost/approval state must remain unchanged when decision persistence or required
audit fails, and no post-commit event/notification must escape a rolled-back transaction, for the
fresh-session model exactly as it was already proven for the shared-session one; a registered
apply handler receiving `deps: TDeps` produced by its own registered `dependencies_factory` and
mutating a repository through it commits atomically with the approval decision, and rolls back
atomically with it on failure; **a handler can reach only the collaborators its own
`dependencies_factory` constructs — a test asserting this is the *only* way it obtains a
repository or service, not an incidental fact about the current implementation**
(directly exercising ADR-005 §24's dependency-visibility rationale, not just its atomicity
guarantee); two concurrent `approve_and_apply` calls (different requests) each get genuinely
independent sessions and don't interfere with each other (this is new — the shared-session model
couldn't be tested this way since there was only ever one session).

**Failure scenarios:** an apply handler raises before `uow.commit()` → whole transaction (approval
decision, audit row, module mutation) rolls back together, exactly as ADR-PF-008 requires today,
now proven under a genuinely isolated session; a post-commit handler (view invalidation, legacy
bridge, notification) raises after a successful commit → isolated, logged, does not affect the
already-committed approval.

**Tenant + organization scenarios:** `ApprovalRequest`'s new typed events (if adopted per the P5
assessment) carry `tenant_id`/`organization_id` per ADR-005 §3 — TO-1 through TO-9 and TO-14 apply
once Platform's approval-related invalidation is migrated (P5/P6), not fully exercised in P4 itself
(P4 is transaction-mechanics-focused; P5 is where the typed events and their scope fields are
actually defined).

**Exit criteria:** `ApprovalService` uses `PlatformUnitOfWork` exclusively for `approve_and_apply`/
`.reject`/`request_change` (all three migrate together, per P4-PRE Step 2); every registered apply
participant across every module dispatches through `dependencies_factory` per the same change (the
legacy shared-session construction path was already removed in P4-PRE Step 1 — this phase has
nothing left to delete); the architecture guardrail test still passes; `ApprovalService`'s own
existing test suite (per ADR-PF-008) passes unmodified in intent (same guarantees), updated only
where the fresh-session model requires new fixture setup.

**Explicit non-goals:** this phase does not rewrite any apply handler's *business* logic — only
how it obtains repositories and how it returns post-commit reactions. Does not touch
`NotificationService`'s standalone (non-approval-composed) call sites. Does not touch
`ServiceBase.commit()`'s module-owned subclass.

**Rollback/recovery:** `ApprovalService` reverts to constructing repositories from
`self._session` directly and `ApprovalHandlerResult` reverts to the string-keyed shape — a
mechanical revert since the business logic inside handlers is unchanged, only their
repository-access and result-construction code.

## P4B — Organization Capability Transaction Convergence (implemented)

**Status:** implemented. Discovered as a hard prerequisite during the P5A (`OrganizationCreated`)
attempt: `OrganizationService`'s mutation methods were still on the shared, process-lifetime
`Session`, so `uow.record_event()` had no `uow` to call. P5A stopped and reported "P5A
TRANSACTION-BOUNDARY PREREQUISITE" rather than faking the event via a post-commit Signal
callback; this phase resolves that prerequisite. P5A itself remains unimplemented — no
`OrganizationCreated` class, no `record_event(` call, and no ViewInvalidation producer exist as of
this phase (enforced by `test_p4b_does_not_add_p5a_event_vocabulary`).

**Goal:** migrate `OrganizationService`'s own competing transaction convention onto the canonical
`UnitOfWork`, mirroring P4's `ApprovalService` cutover but scoped to the Organization capability
only — the same "one business operation → one transaction owner" principle, applied to
Organization's own mutations rather than Approval's.

**Architectural decision:** a new, narrow `OrganizationUnitOfWork(UnitOfWork, Protocol)` —
`organizations: OrganizationRepository` and `_enterprise_audit_service: EnterpriseAuditService` —
sibling to `PlatformUnitOfWork`, not a growth of it (ADR-005 §9/§24 rejects one Platform-wide UoW
accumulating a named accessor per capability). Concrete: `SqlAlchemyOrganizationUnitOfWork`
(`src/core/platform/infrastructure/persistence/organization_unit_of_work.py`), built on the same
P3 `SqlAlchemyUnitOfWorkBase` foundation Approval uses, wired through
`platform_registry.py`'s `organization_uow_factory` (derived from `session.bind`, same reasoning
as `approval_uow_session_factory`).

**Migrated (fresh `OrganizationUnitOfWork` per call, default/`commit=True` mode):**
`create_organization`, `update_organization` (no bifurcation needed — no caller composes it into
a larger transaction), `set_active_organization`, `bootstrap_defaults`. `update_organization`'s
audit entry is now staged *before* `uow.commit()` (previously staged after `session.commit()` via
a second, non-atomic commit — a pre-existing gap against ADR-003's own atomicity invariant; fixing
the ordering is a necessary consequence of the UoW's commit-then-close lifecycle, not opportunistic
cleanup).

**Grandfathered caller-owned exception (mirrors P4-PRE/P4's `request_change(commit=False)`
precedent exactly):** `create_organization(commit=False)` and `set_active_organization(commit=False)`
remain on the shared, process-lifetime Session, byte-for-byte unchanged. Sole real caller:
`PlatformRuntimeService.provision_organization`, which composes organization creation + module
entitlement provisioning + optional activation into one outer transaction, committed once. Forcing
this onto an independent fresh UoW would break that real cross-capability atomicity requirement.

**P5A readiness confirmed:** `organization_id`/`tenant_id` are both known before any flush
(application-side `generate_id()` in `Organization.create()`; tenant resolved from
`UserSessionContext` before the domain object is even constructed) — no database round-trip is
needed before a future `uow.record_event(OrganizationCreated(...))` call in `create_organization`'s
`commit=True` branch.

**Exit criteria met:** fresh Session per transaction-owning Organization command (proven);
Organization repository/audit service session-identical to the active UoW's session (proven); no
partial state / no legacy signal on validation or commit failure (proven); shared legacy Session
untouched by the migrated path (proven); `provision_organization`'s real caller-owned atomicity
unaffected (proven); tenant isolation preserved through the new UoW-based mutation path (proven);
architecture guardrail and full P0-P4/Approval/legacy-signal regression suites show no new failures
(same pre-existing, unrelated failure set as before this phase — calendar/site/department/access
tests, none of which touch Organization).

**Explicit non-goals:** no `OrganizationCreated`/`OrganizationUpdated`/etc. DomainEvent, no
`uow.record_event()` call, no ViewInvalidation producer, no other Platform capability's
transaction migrated, no removal of the global process-lifetime Session (still required by every
other, not-yet-migrated Platform/PM/Inventory service).

## P5 — Platform Typed Events / Platform Invalidation (Per-Capability Discovery)

**Goal:** classify Platform's 11 named signals per-capability, exactly as the (now-struck)
original Phase 6 intended, but performed here, before any module migrates, per the corrected
execution-plan sequencing.

**Architectural decision being implemented:** ADR-005 §1 (Event Taxonomy), §3 (Scope Semantics —
every newly-typed event gets explicit `organization_id`), §6 (Event Recording Decision applied
per-capability).

### Platform Capability Discovery Table (to be filled in with real emitter evidence during this
phase — seeded here with the audit's findings as a starting point, not a final answer)

| Signal | Emitting capability | Confirmed emitter count (audit) | Likely classification | Event-recording model (§6 criteria) |
|---|---|---|---|---|
| `organizations_changed` | `master_data` (organization) | 3 sites across 2 services (`organization_service.py`, `platform_runtime_service.py`) | Split — at least `OrganizationCreated`/`OrganizationRenamed`/`OrganizationDeactivated` as real business facts | **Corrected by the P5 discovery pass and P4B:** `Organization` (`src/core/platform/domain/master_data/org/organization.py`) is a plain validated dataclass with no `.rename()`/`.archive()`/state-transition methods — not aggregate-shaped. Application-authored via `uow.record_event()` inside `OrganizationService`, not aggregate-recorded. **P4B (implemented, see above) gives `create_organization`'s transaction-owning mode a real `uow` to call `record_event()` on** — the transaction-boundary prerequisite P5A originally stopped on is resolved. |
| `employees_changed` | `master_data` (employee) | 2 sites (`employee_service.py` create/update) | Likely `EmployeeHired`/`EmployeeUpdated` — narrower emitter already, closest to 1:1 | Aggregate-recorded |
| `documents_changed` | `master_data` (documents) | 9 sites across 2 services — confirmed coarsest Platform signal | Split into ≥4-5 distinct facts (`DocumentStructureCreated`, `DocumentMetadataUpdated`, `DocumentUploaded`, `DocumentDeleted`, integration-link facts) — do not collapse back to one event | Aggregate-recorded for document lifecycle; the integration-link facts may be orchestration-level (assess during discovery) |
| `sites_changed`, `departments_changed`, `calendars_changed`, `parties_changed` | `master_data`/`time_management` | Not yet inventoried by the audit (Platform-scope only; emitter counts not sampled) | To be discovered fresh in this phase — do not assume 1:1 with the signal name | To be determined per-emitter |
| `auth_changed` | `security` | Not sampled | Likely split — some emitters may be real business facts (`UserSignedIn`, `RoleAssignmentsChanged`), others pure session/UI invalidation with no underlying domain event | To be determined per-emitter |
| `approvals_changed` | `approval` | Covered in P4 (`ApprovalDecided`/`ApprovalRejected`) | Aggregate-recorded, already resolved in P4 | Aggregate-recorded |
| `access_changed` | `access` (relationship to `domain/security/authorization` unresolved — see Appendix) | **Corrected by the P5 Event Discovery pass** (`platform_p5_event_discovery.md`): a real, direct consumer exists (`access_workspace_controller.py:237-240`) — the earlier "no confirmed subscriber" claim was wrong. Producers: `AccessControlService.assign_scope_grant`/`remove_scope_grant`. | Split into `ScopeAccessGranted`/`ScopeAccessRevoked`, blocked on fixing an ambient-tenant/missing-organization scope-derivation bug found in both producers — see the P5 Event Discovery document's Section 17 | Proposed as slice P5C, gated on the scope-derivation fix |
| `modules_changed` | `tenant` (module entitlements) | Not sampled | Likely UI/config invalidation only — confirm no domain-meaningful emitter exists before settling this | Likely `ViewInvalidationHint` only, no underlying `DomainEvent` |

This table is a **starting point, not a final decision** — per ADR-005 §6, each row's
classification must be confirmed against real emitter evidence gathered during this phase, the
same discipline the (struck) original Phase 6 already required. A signal row that turns out to
have no domain-meaningful emitter (`modules_changed` is the leading candidate) gets a
`ViewInvalidationHint`-only treatment with no corresponding `DomainEvent` at all — this is a
valid, expected outcome, not a gap.

**Exact expected files (per assessed capability, created only as each capability's discovery
confirms it needs one):**
```text
src/core/platform/domain/<capability>/events.py       # e.g. domain/master_data/organization/events.py
src/core/platform/application/<capability>/event_handlers/
  transactional.py            # only if a real cross-aggregate case is found
  view_invalidation.py        # module/capability-owned invalidation-hint constants
```

**Files likely modified:** the aggregate/service files for whichever capabilities are typed in
this phase (e.g. `Organization.rename()` adopts `RecordsDomainEvents`); composition-root
registration of each capability's `register_post_commit_handlers`/`register_transactional_handlers`.

**Dependencies/prerequisites:** P1-P4.

**Production behavior affected:** none until P6's Qt adapter and P7's legacy bridge actually wire
these into the UI — this phase produces typed events and their invalidation-hint mapping, but
does not yet change what the desktop UI does.

**Compatibility behavior:** each newly-typed capability continues to also fire its legacy
`domain_events.<signal>.emit(...)` call via an explicit bridge adapter during this phase (mirrors
`project_management`'s own `Resource*UnitOfWork` precedent of dual-emitting during transition) —
removed per-capability in P7 once its consumers have migrated.

**Tests to add:** per newly-typed event: aggregate records the correct event with accurate
previous/new state, `tenant_id`, and `organization_id`, using an injected fixed `Clock`; no event
recorded on a no-op mutation; the full TO-1..TO-11 and TO-14 matrix for that event's resulting
`ViewInvalidationHint`; where discovery surfaces a genuine multi-organization effect (§3a), TO-13
concretely, not only synthetically.

**Failure scenarios:** unchanged from P2-P4's already-proven mechanics — this phase adds new event
*types*, not new dispatch machinery.

**Tenant + organization scenarios:** TO-1 through TO-11 and TO-14, per newly-typed event, using
real Platform data shapes (not synthetic test fixtures only) — at least one worked example per
capability typed in this phase must be tested against a scenario with two organizations in one
tenant, proving TO-1/TO-2/TO-4 concretely for that capability, not only for the generic P2 tests.

**Exit criteria:** the discovery table above is filled in with confirmed evidence for every one
of Platform's 11 named signals (not left partially assessed); every signal classified as a real
business fact has a typed event with explicit `organization_id`; every signal classified as
UI-only has a documented rationale for why (not silently skipped); the architecture guardrail
test still passes.

**Explicit non-goals:** does not delete any legacy signal yet (P7). Does not touch the Qt
controller layer (P6). Does not migrate any business module's own signals.

**Rollback/recovery:** each capability's new event types and handlers are additive alongside the
still-live legacy bridge — reverting one capability's typing work does not affect any other
capability or any already-completed phase.

## P6 — Qt Invalidation Adapter Consolidation

**Goal:** build the one shared Qt adapter, and migrate the three existing controller bases to
delegate their invalidation slice to it — explicitly not a controller-hierarchy unification.

**Architectural decision being implemented:** ADR-005 §13 (Desktop Adapter Boundary, bounded
consolidation scope), §25 (non-goal: this is not a general QML controller refactor).

**Exact expected files:**
```text
src/ui_qml/infrastructure/events/
  qt_view_invalidation_channel.py   # the ONE shared adapter: subscribes to the in-process
                                     #   ViewInvalidationChannel (P2), marshals to the Qt main
                                     #   thread, exposes a narrow controller-facing API for
                                     #   subscribe/dispose/coalesced-refresh-scheduling
```

**Files likely modified:**
- `src/ui_qml/platform/controllers/common/workspace_controller_base.py` — its
  `_subscribe_domain_change`/`_subscribe_domain_signal`/`_disconnect_domain_event_subscriptions`/
  refresh-coalescing logic is **replaced with delegation** to the new shared adapter. Every other
  method on this class (loading/busy-state management, lazy-load gating) is **untouched**.
- `project_management/.../workspace_controller_base.py`,
  `inventory_procurement/.../workspace_controller_base.py` — **out of this phase's Platform-only
  scope.** Their own migration to the shared adapter happens as part of *their own module's*
  migration phase (Execution Plan Phases 3/5), not here. This phase only builds the shared adapter
  and proves it works for Platform's own controller base — it does not reach into module code.

**Dependencies/prerequisites:** P2 (concrete `ViewInvalidationChannel`), P5 (at least one real
typed Platform event to invalidate on, to prove the adapter end-to-end against something real
rather than only synthetic tests).

**Production behavior affected:** Platform's own QML controllers' refresh-triggering mechanism
changes internally; observable behavior (when and how a Platform workspace refreshes) must be
unchanged from a user's perspective — proven by Constraint 5's staleness test, not assumed.

**Compatibility behavior:** `admin_console/domain_event_binder.py` is **not yet deleted** in this
phase — it continues to bridge the legacy signals it currently covers until P7, when its
already-self-scheduled "R2" removal is finally completed.

**Tests to add:** the disposal/teardown test the audit found missing — a controller subscribed via
the shared adapter, then destroyed, must have its subscription actually removed (assert the
underlying channel's subscriber list no longer contains it, not merely that no crash occurred);
duplicate-subscription test (subscribing the same controller instance twice must not silently
double-deliver, or must raise — decide and test one behavior explicitly, since the legacy
mechanism's silent-double-subscription-via-fresh-closures gap must not be carried forward
unexamined); Qt-thread-marshaling test (a `notify()` call from a non-Qt-main-thread context still
delivers its callback on the Qt main thread — using the same threading test approach P0's
characterization test established for baseline behavior).

**Failure scenarios:** one controller's refresh callback raising does not prevent a sibling
controller's callback from running (channel-level isolation, per ADR-005 §12's two-independent-
failure-isolation-responsibilities design) — tested as its own case, distinct from the post-commit
bus's own adapter-level isolation (P2).

**Tenant + organization scenarios:** TO-12 (organization switching mid-session) is exercised here
concretely for the first time against a real Qt controller, not only a synthetic channel test.

**Exit criteria:** the shared adapter exists and is used by Platform's own controller base;
Platform's refresh behavior is unchanged from a user's perspective for every signal migrated in
P5 (a real test, per Constraint 5); the disposal and duplicate-subscription tests both pass with
an explicit, documented answer (not left as "whatever happens to happen").

**Explicit non-goals:** does **not** touch `project_management`'s or `inventory_procurement`'s
own controller bases. Does **not** unify the three controller bases' non-invalidation
responsibilities. Does **not** delete `admin_console/domain_event_binder.py` yet.

**Rollback/recovery:** Platform's controller base can revert to its own inline
subscribe/dispose/coalesce logic (unchanged since before this phase, still present in git
history) if the shared adapter needs to be rolled back; no module code is affected either way
since this phase never touched any.

## P7 — Platform Legacy Compatibility Bridge and Cutover

**Goal:** retire every legacy-bridge adapter this plan introduced along the way, once — and only
once — every consumer it served has migrated to the new mechanism.

**Architectural decision being implemented:** ADR-005 §23 (Legacy Compatibility), Execution Plan
Constraint 3/4 (no straddling past a phase's close).

**Exact expected files:** none new — this phase deletes/shrinks existing files.

**Files likely modified:**
- `src/core/shared/events/domain_events.py` — remove the 11 Platform-owned fields
  (`organizations_changed`, `employees_changed`, etc.) from `DomainEvents` once every real
  consumer has migrated to `ViewInvalidationChannel`; **do not remove the 2 generic bridge
  signals or any module-owned field yet** — those remain until every module's own phase closes
  (Execution Plan Phases 3-5), since this document is Platform-scoped only.
- `src/ui_qml/platform/controllers/admin_console/{domain_event_binder.py, signal_binder.py,
  refresh_coordinator.py}` — `domain_event_binder.py` is deleted, completing its own
  already-self-scheduled "R2" removal; `signal_binder.py`/`refresh_coordinator.py` are assessed
  for the same treatment (their exact current responsibilities were not fully characterized by
  the audit — confirm during this phase before deleting, don't assume they're redundant).
- `src/core/platform/application/approval/approval_service.py` — the P4 legacy-bridge adapter
  (dual-emitting the old `approvals_changed` signal alongside the new typed events) is removed.
- Each P5-typed capability's own legacy-bridge adapter is removed per-capability, as that
  capability's consumers finish migrating — not necessarily all at once.

**Dependencies/prerequisites:** P4, P5, P6 all complete; every consumer of every Platform-owned
legacy signal confirmed migrated (a checklist, not an assumption — enumerate every known consumer
found during P5's discovery and confirm each one individually).

**Production behavior affected:** none, if done correctly — this phase only removes now-dead
code paths, it does not change what the UI does. A regression here means a consumer was missed
during P5's discovery, not that the new mechanism itself is wrong.

**Compatibility behavior:** this is the phase where compatibility bridges *end* — by design, no
new compatibility behavior is introduced here.

**Tests to add:** a repo-wide grep-equivalent test (or reuse of the architecture guardrail
technique) asserting zero remaining `.emit(...)` call sites for any of the 11 removed
`DomainEvents` fields anywhere under `src/core/platform/`.

**Failure scenarios:** if this phase's exit criteria are enforced correctly, there should be no
new failure modes — removing dead code cannot introduce a runtime failure by definition, only
reveal one that was already latent (a consumer P5 missed). If the grep-equivalent test above finds
a remaining reference, that is this phase's own failure signal, caught before deletion.

**Tenant + organization scenarios:** a final full run of TO-1 through TO-14 against every
migrated Platform capability, as a closing regression gate.

**Exit criteria — "Platform Domain Event Foundation Ready" (this is the gate Execution Plan Phase
3 onward is blocked on):**
- No Platform producer depends on the legacy `domain_events` bus except an explicitly-approved,
  time-boxed compatibility edge (if any genuinely remains, it is named, dated, and justified —
  not silently left in place).
- Tenant **and** organization isolation proven by the full TO-1..TO-14 matrix, against real
  migrated Platform signals.
- Rollback behavior, post-commit failure isolation, and integration-outbox semantics
  (unchanged, ADR-PF-011) all proven for `ApprovalService`'s migrated path.
- Qt refresh behavior for every migrated Platform signal unchanged from a user's perspective (a
  real test).
- The architecture guardrail test passes, with only its two originally-cited exceptions.
- Zero of the 11 Platform-owned fields remain in `DomainEvents` for anything this plan migrated.

**Explicit non-goals:** does not touch any module-owned field on `DomainEvents` (`tasks_changed`,
`inventory_items_changed`, etc.) — those are Execution Plan Phases 3-5's responsibility, not this
plan's.

**Rollback/recovery:** if a missed consumer is discovered after a signal's bridge is removed, the
fastest safe recovery is re-adding that one signal's bridge adapter (not reverting the whole
phase) while the missed consumer is migrated properly — treat this as a signal-by-signal
operation, not an all-or-nothing one.

## P8 — Platform Cutover Validation

**Goal:** an explicit, final validation pass before declaring Platform's foundation ready for
business modules to build on, separate from P7's own exit criteria so that "we deleted the old
code" and "we proved the new code is correct in production-like conditions" are two distinct,
both-required gates.

**Architectural decision being implemented:** none new — this phase validates P0-P7's decisions
were actually implemented as specified, not a new decision itself.

**Exact expected files:** none new — validation-only phase, plus a short written report (this
document's own future revision, or a dated addendum) recording the outcome.

**Files likely modified:** none.

**Dependencies/prerequisites:** P7's exit criteria all met.

**Production behavior affected:** none by this phase itself — it observes, does not change,
behavior.

**Compatibility behavior:** n/a.

**Tests to add:** none new — this phase re-runs everything from P0-P7 together, once, as a full
regression pass, plus a manual (or scripted) exploratory pass through the actual desktop
application exercising organization switching, approval decisions, and master-data edits across
at least two organizations in one tenant and two different tenants, confirming the automated
TO-1..TO-14 matrix's results match observed behavior in the running app, not only in unit tests.

**Failure scenarios:** any regression found here sends the responsible phase (P0-P7) back for a
fix — this phase does not itself introduce new failure-handling logic.

**Tenant + organization scenarios:** the full TO-1..TO-14 matrix, run once more as a whole-system
regression, plus the manual/exploratory pass above.

**Exit criteria — "Platform Domain Event Foundation Ready" declared (formally, in writing, dated,
in this document or a linked addendum):** every P0-P7 exit criterion holds simultaneously; the
manual/exploratory pass finds no discrepancy from the automated matrix; the architecture guardrail
test passes; `git log`/`git diff` show a clean, reviewable history for the whole Platform
migration with no unresolved TODOs referencing this ADR revision.

**Explicit non-goals:** does not begin any business module's own migration (Execution Plan Phase
3 begins only after this phase's exit criteria are met and explicitly declared, not automatically).

**Rollback/recovery:** if this phase finds a regression, the fix happens in the responsible
earlier phase, re-validated, then this phase re-runs — this phase itself has nothing to roll back.

## Appendix: Open Items Specific to This Implementation Plan

- **`platform/access/{domain,application}` vs. `platform/domain/security/authorization`**
  (audit-flagged, unresolved): P5's discovery table defers `access_changed`'s classification
  pending this. Resolve with a short, separate investigation before P5 closes, not by guessing
  which package should own the resulting event.
- **`sites_changed`, `departments_changed`, `calendars_changed`, `parties_changed`, `auth_changed`**
  emitter counts were not sampled by the Platform audit (it sampled `organizations_changed`,
  `employees_changed`, and `documents_changed` as representative examples, not all 11
  exhaustively) — P5's discovery phase must inventory these from scratch, not assume they mirror
  the three sampled signals' shape.
- **Thread-safety of `ApprovalService` under concurrent calls** was not established either way by
  the audit (no evidence of concurrent use found, but not stress-tested). P4's move to a
  genuinely fresh per-call `Session` incidentally removes the specific shared-`Session` concurrency
  risk the audit flagged — confirm this is actually true via the new concurrent-`approve_and_apply`
  test in P4, not merely assumed as a side effect.
- **`signal_binder.py`/`refresh_coordinator.py`** (the other two files co-located with
  `admin_console/domain_event_binder.py`) were not fully characterized by the audit. P7 must read
  and understand both before deciding their fate — do not assume they're redundant with the
  binder simply because they live in the same folder.

## Final Validation Note

This document, ADR-005, and the ADR-005 execution plan were written and revised together in one
documentation-only pass. No file under `src/` was modified. No test was added. No production
behavior changed. No business module was touched. Confirmed by `git status`/`git diff` at the end
of this work (see the completion report for the exact output).

**Second pass (2026-08-25, same day) — P4A investigation and P4-PRE insertion.** Before Phase P4
was allowed to begin writing any code, its own instruction to inspect real source and stop-and-
report on conflict (rather than silently redesign) was followed: a full inventory of all 18 real
`register_apply_handler`/`register_reject_handler` registrations found the originally-specified
`TDeps` design (a repository-shaped dataclass resolved from a generic binder registry) did not
match how any of them actually work — all 18 call into one of 8 long-lived application services,
each holding a circular `approval_service=` reference. This is a genuine, evidence-backed
architecture/implementation mismatch, not a preference. Resolution: ADR-005 §24 is revised (Round
7) to a module-supplied `dependencies_factory(session) -> TDeps` mechanism; a new, separately
gated Phase P4-PRE (Execution Plan Phase 2A-PRE) is inserted before P4 to make the 8 backing
services session-parameterizable first; P4's own Design Resolution, exact/likely-modified file
lists, and exit criteria are updated to match. `request_change()` is deliberately not migrated
ahead of `approve_and_apply`/`reject` — it moves together with them in P4-PRE's Step C, to avoid
running two live transaction models in one service without a documented transitional reason. This
second pass was, again, documentation-only: no file under `src/` was modified, no test was added,
no production code changed, no commit was made — confirmed by `git status` showing only these
three documents changed.

**Third pass (2026-08-25, same day) — direct convergence, pre-release scope decision (Round 8).**
An attempt to actually implement P4-PRE Step A began (re-confirming the 18 registrations and the 8
backing services' current source, matching the P4A investigation exactly — no plan/source
mismatch found). Before any file was written, an explicit user decision arrived: this application
is pre-release, with no external users and no backward-compatibility requirement for the current
process-lifetime `Session` architecture, and the four-step Round 7 sequencing (extract an adapter
still on the shared session, then separately make it session-parameterizable) builds exactly the
kind of temporary architecture that gets deleted almost immediately once its replacement lands. A
wider, 30-service PM/Inventory audit was performed to re-scope this correctly rather than simply
widening it on assumption — confirming ~20 services are pure transaction-owning commands
(out of scope, belongs to Execution Plan Phase 3/5), 2 more (`ProjectCommitmentService`,
`StockControlService`) already share the 8's `commit: bool` pattern with no approval relationship
(out of scope, separately tracked), the pre-existing `Resource*UnitOfWork` classes are themselves
not real Units of Work by §9's definition (out of scope, unrelated), and
`build_repository_bundle(session)` already covers all 69 repositories these 30 services use
(confirming the repository layer was never the blocker). Resolution: ADR-005 §24 (Round 8) and the
Execution Plan's Phase 2A-PRE collapse Round 7's four steps into two — port the 8 services'
approval-facing logic directly into standalone, session-parameterized participants (Step 1,
formerly A+B), then cut `ApprovalService` over (Step 2, formerly C, with D's cleanup folded in
since nothing is left to delete afterward). This document's own P4-PRE and P4 sections, and the
Human Approval Gates table, are updated to match. This third pass was, again, documentation/design
only: no file under `src/` was modified, no test was added, no production code changed, no commit
was made — confirmed by `git status` showing only these three documents changed.

**Fourth pass (2026-08-25, same day) — P4B (Organization Capability Transaction Convergence),
discovered mid-P5A.** P5A (`OrganizationCreated`) began per its own instruction to inspect the
real Organization mutation path before writing any event code. `OrganizationService.create_organization`
was confirmed still on the shared, process-lifetime `Session` (`self._session.commit()`, wired
from `platform_registry.py`'s shared `session`), with no Organization-specific or reusable
general-purpose Platform UnitOfWork anywhere in the codebase, and `SqlAlchemyUnitOfWorkBase.commit()`
confirmed to close its Session unconditionally — so wrapping the shared Session in a UoW as a
stopgap would have closed it out from under every other unmigrated Platform service. P5A stopped
per its own explicit gate and reported "P5A TRANSACTION-BOUNDARY PREREQUISITE" rather than faking
the event via a post-commit Signal callback or silently migrating Organization's transaction
architecture inside P5A's own scope. A new, separately gated Phase P4B is inserted between P4 and
P5 to resolve exactly this prerequisite, mirroring P4's own `ApprovalService`/`PlatformUnitOfWork`
cutover pattern but scoped to the Organization capability only. P4B has since been implemented (see
the P4B section above) and reviewed; P5A remains not started — no `OrganizationCreated` class, no
`record_event(` call, and no ViewInvalidation producer exist anywhere in the codebase as of this
pass, enforced by `test_p4b_does_not_add_p5a_event_vocabulary`. This pass's own documentation edit
(this section plus the new P4B section and the `organizations_changed` discovery-table row above)
is separate from, and follows, the P4B implementation itself.
