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

## P5A — OrganizationCreated (implemented)

**Status:** implemented, reviewed. Unblocked by P4C (both real Organization-creation paths --
standalone `create_organization` and `PlatformRuntimeApplicationService.provision_organization`
-- already used canonical fresh-session UnitOfWorks calling the same shared
`OrganizationService._create_organization_using` business operation).

**Event:** `OrganizationCreated` (`src/core/platform/domain/master_data/org/events.py`) --
exactly the platform_p5_event_discovery.md §7 field set: `tenant_id`, `organization_id`, `name`,
`code`, `occurred_at`. Application-authored via `uow.record_event(...)` from
`_create_organization_using` (both `OrganizationUnitOfWork` and `PlatformProvisioningUnitOfWork`
satisfy the same duck-typed `record_event`/`_enterprise_audit_service` shape -- the shared
operation never imports either concrete UoW class). `Clock` (`src/core/shared/time/clock.py`,
concrete `SystemClock`) is now injected into `OrganizationService` -- its first real consumer.
Recorded before `uow.commit()`; exactly one event per successful creation, on either path;
nothing observable on rollback or commit failure (proven for both paths).

**ViewInvalidation:** `src/core/platform/application/master_data/org/event_handlers/view_invalidation.py`
maps `OrganizationCreated` to exactly the two discovery-matrix targets --
`TenantScope(tenant_id)`/`organization_list` (tenant-wide) and
`OrganizationScope(tenant_id, organization_id)`/`organization_details` (per-organization, no
current UI consumer, produced for future use per ADR-005 §3a). Registered once on a
composition-owned `InProcessPostCommitEventBus`/`InProcessViewInvalidationChannel` pair now
shared by every Platform capability UnitOfWork factory (Approval/Organization/Provisioning),
replacing each factory's previous throwaway dispatcher/bus instances.

**Organization-specific P6A cutover (pulled forward from P6, scope limited to Organization):**
after tracing both real `organizations_changed` consumer chains end-to-end (admin console
organization list, settings organization-profiles list -- both ultimately read
`list_organizations()`, a tenant-wide read), a temporary `OrganizationCreated ->
organizations_changed` compatibility bridge was rejected as unnecessary: this is pre-release, the
consumer set is exactly two, and both were migrated directly onto `ViewInvalidationChannel` via a
new `OrganizationViewInvalidationAdapter` (`src/ui_qml/platform/adapters/`) -- the Qt-facing
translation layer ADR-005 §13 assigns to P6, implemented here only for the Organization slice.
Controllers/presenters never import `DomainEvent`/`OrganizationCreated`/`ScopeFilter` -- they
connect to the adapter's plain `organizationCollectionStale` Qt signal. `create_organization`/
`provision_organization` no longer emit `organizations_changed` at all (neither directly nor via
a bridge); `update_organization`/`set_active_organization` still do, unchanged -- the legacy
signal remains genuinely required for those two operations and was not removed.

**Exit criteria met:** exactly-once event recording (both paths, explicit tests); no event
observable on validation/commit/late-provisioning failure; deterministic `Clock`; cross-org and
cross-tenant `ScopeFilter` routing proven against the real channel; one failing post-commit
handler does not block the ViewInvalidation reaction (ISOLATE_AND_CONTINUE); real end-to-end
proof through `PlatformWorkspaceCatalog` that both UI consumers refresh after standalone and
provisioning creation, and do not refresh on a rolled-back attempt; update/activation UI refresh
proven unaffected; architecture guardrails and full P0-P4C/PM/Inventory regression suites show no
new failure identity.

**Explicit non-goals:** P5B (Module Entitlements)/P5C (Access-RBAC)/P5D (Tenant Membership)/
Approval events not started. No other Platform capability's Qt consumers migrated (calendar,
documents, access, modules, approval all still solely on legacy signals). The legacy event
framework (`domain_events`) is not retired -- `organizations_changed` remains live for
update/activation and every other still-legacy signal.

## P5B — Module Entitlement Transaction/Scope Convergence (prerequisite complete; event implementation blocked)

**Status:** transaction/scope convergence prerequisite complete and tested. Typed event
implementation (`ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled`) deliberately NOT started --
blocked on a confirmed event-vocabulary mismatch requiring a business-owner decision (see below).

**Prerequisite gate findings (before any event code was considered):**

- **Ambient-scope bug, confirmed and fixed.** The pre-P5B `set_module_state` wrote through
  `ModuleCatalogService`'s repo `upsert()` -> `upsert_for_organization()` ->
  `TenantScopedRepositorySupport._require_organization_scope()`, which hard-required
  `organization_id == ctx.organization_id` (the currently active organization). Targeting a
  non-active organization was not merely "ambient by default" -- it was structurally
  impossible through the old public API. Fixed by adding
  `ModuleEntitlementRepository.get_for_organization_in_tenant(...)` and rewriting
  `set_module_state(organization_id, module_code, ...)` to take an explicit, required
  `organization_id` targeting any organization within the caller's own authenticated tenant --
  never derived from `UserSessionContext`/`TenantContextService`.
  `PlatformRuntimeApplicationService.set_module_state` now resolves the active organization
  itself and passes its id explicitly; it no longer relies on ambient resolution inside the
  catalog service.
- **Second, independent audit-atomicity bug, confirmed and fixed** (same pattern as
  Organization's pre-existing `update_organization` bug found during P4B). The audit entry was
  written via a separate `record_audit_entry(..., commit=True)` call *after* the entitlement
  write's own commit -- never atomic; a crash between the two calls left an unaudited mutation.
  Fixed by staging the audit entry with `commit=False` inside the same fresh
  `ModuleEntitlementUnitOfWork` before its single `uow.commit()`.
- **Transaction ownership converged onto a canonical UoW.** New narrow
  `ModuleEntitlementUnitOfWork`/Factory (`src/core/platform/contract/persistence/module_entitlement_unit_of_work.py`,
  `src/core/platform/infrastructure/persistence/module_entitlement_unit_of_work.py`) mirrors
  `SqlAlchemyOrganizationUnitOfWork`'s exact pattern; wired in `platform_registry.py` onto the
  same shared `platform_transactional_dispatcher`/`platform_post_commit_bus` triple as
  Organization/Approval/Provisioning. `set_module_state` now opens a fresh session per call via
  this factory, never touching the legacy process-lifetime `Session`. No leftover
  `commit: bool` switch was found on `set_module_state` itself (it never had one);
  `provision_organization_entitlements`'s own `commit: bool` was left untouched -- out of scope,
  a separate provisioning-time operation with its own caller contract, not part of this
  convergence.
- **Event-vocabulary mismatch, confirmed -- the reason event implementation is blocked.**
  `set_module_state`'s real state model is three independent fields
  (`licensed`/`enabled`/`lifecycle_status`, the last a 5-value enum:
  inactive/active/trial/suspended/expired) all changeable in one call, plus a real, reachable UI
  action (`toggle_module_license`) that flips `licensed` in either direction through the
  identical control. The proposed 3-name vocabulary
  (`ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled`) has no event name for license *revocation*,
  and no event name at all for `lifecycle_status` transitions (active->suspended,
  active->trial, active->expired). Whether a revocation that cascades into forcing
  `enabled=False`/`lifecycle_status=inactive` is one compound business fact or up to three
  separate ones is a business-owner decision, not an engineering guess -- matching the same kind
  of open question already flagged, and left open, for `OrganizationActivated`'s
  sibling-deactivation case in P5A's own discovery pass. Recorded in
  `platform_p5_event_discovery.md` §17 item #4's resolution note.

**What was NOT implemented, by design:** no `ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled`
DomainEvent type; no `uow.record_event(...)` call anywhere in the Module Entitlement capability;
no ViewInvalidation producer/adapter for modules; the legacy `modules_changed` signal remains the
sole notification path for module-entitlement changes, unchanged. A dedicated architecture-guard
test (`test_module_entitlement_prerequisite_does_not_add_event_vocabulary`) enforces this
boundary by source inspection.

**Explicit non-goals:** Access/RBAC (P5C), Tenant Membership (P5D), Approval events; the
Organization slice (untouched); any other Platform capability's Qt consumers.

**Rollback/recovery:** the new `ModuleEntitlementUnitOfWork` and `get_for_organization_in_tenant`
addition are additive; the `set_module_state` signature change (explicit, required
`organization_id`) is the only breaking change, confined to its ~13 known call sites, all
updated.

## P5B-SEM — Module Entitlement Business Transition Design (design only, not implemented)

**Status:** design/investigation complete. No production code or tests changed in this pass. No
`DomainEvent` classes, no `ViewInvalidation`, no Qt migration, no P5C.

**Domain model finding:** `ModuleEntitlement` (`domain/tenant/modules/module_entitlement.py`) is a
plain frozen dataclass/read projection with no transition methods (`license()`/`enable()`/etc.
do not exist) -- it does not currently own its own invariants. Every state-machine rule
(license-before-enable, lifecycle-forces-enablement, planned-module blocking) lives in
`_set_module_state_using`, an application-layer function, not the aggregate.

**Real business commands** (identified from the three real presenter methods in
`settings_catalog_presenter.py`, never from field names):

| Command | Presenter entry point | Fields touched | Cascade | Requires |
|---|---|---|---|---|
| `LICENSE_MODULE` / `REVOKE_MODULE_LICENSE` | `toggle_module_license` (one bidirectional toggle) | `licensed` | Revoke forces `enabled=False`, `lifecycle_status=inactive`; grant always lands on `inactive->active` (never enables) | not planned |
| `ENABLE_MODULE` / `DISABLE_MODULE` | `toggle_module_enabled` | `enabled` | none | licensed; lifecycle not in {suspended, expired} |
| `TRANSITION_MODULE_LIFECYCLE` | `change_module_lifecycle_status` (dropdown: active/trial/suspended/expired -- `inactive` is never user-selectable, only reached via revocation) | `lifecycle_status` | Moving into suspended/expired forces `enabled=False` | licensed |

No real caller ever combines more than one dimension in a single call, even though the
underlying `set_module_state`/desktop-API `patch_module_state` signature is generic across all
three. The genericity is plumbing, not actual usage.

**Provisioning is a separate bootstrap fact, not N licensing facts:**
`provision_organization_entitlements` (single caller: `provision_organization`) bulk-materializes
entitlement rows for every catalog module on a brand-new organization -- most left
unlicensed/inactive by default. This is "default entitlements materialized for a new
organization," not decomposable into per-module `ModuleLicensed` events.

**Previously-undocumented fourth producer found (silent, out of scope for this design):**
`ModuleCatalogContextMixin._ensure_context_defaults` lazily seeds default entitlement rows on
first read for an organization with none yet -- no event, no `modules_changed` emit, no audit
entry today. Flagged for the P5B-1 audit-vocabulary review, not resolved here.

**Scope finding:** all three fields (`licensed`/`enabled`/`lifecycle_status`) are stored per
`(tenant_id, organization_id, module_code)` -- confirmed from the `organization_module_entitlements`
schema. No tenant-vs-organization split is needed; every event is `OrganizationScope(tenant_id,
organization_id)`, matching the original discovery assumption.

**Audit/permission evidence:** both `set_module_state` and `provision_organization_entitlements`
enforce the same single permission (`settings.manage`) and write the same generic audit action
name (`module.entitlement.update` / `organization.modules.provision`) regardless of which
dimension changed -- weak evidence on its own, but consistent with (not contradicting) the
three-command model derived from the UI layer.

**Recommended target command API** (`ModuleEntitlementService`, replacing the generic
`set_module_state` as the public mutation surface -- pre-release, no compatibility shim kept):

- `license_module(organization_id, module_code)`
- `revoke_module_license(organization_id, module_code)`
- `enable_module(organization_id, module_code)`
- `disable_module(organization_id, module_code)`
- `transition_module_lifecycle(organization_id, module_code, lifecycle_status)`

Each validates its own preconditions explicitly (no shared generic patch-and-infer-what-changed
path) and returns the updated `ModuleEntitlement` projection. `provision_organization_entitlements`
keeps its own, separate bootstrap-shaped signature -- not folded into this command set.

**Aggregate vs. service ownership:** recommend keeping recording at the application/service layer
(`uow.record_event(...)` from inside each new command method), not moving to aggregate-recorded
events. `ModuleEntitlement` would need to become a real aggregate with its own `license()`/
`enable()`/etc. methods to record events itself, which is a larger, separately-scoped refactor
that P5B-SEM's task boundaries explicitly exclude; the five-command service split already makes
each transition unambiguous without it.

**Recommended event vocabulary (5 events, Strategy A -- semantic transition events, not one
generic `ModuleEntitlementTransitioned`):**

| Event | Meaning | Trigger | Fields | Provisioning emits it? |
|---|---|---|---|---|
| `ModuleLicensed` | module licensed for an organization | `license_module` | `tenant_id`, `organization_id`, `module_code`, `occurred_at` | No |
| `ModuleLicenseRevoked` | module license revoked (also ends enablement/lifecycle -- one compound fact) | `revoke_module_license` | same | No |
| `ModuleEnabled` | module runtime-activated | `enable_module` | same | No |
| `ModuleDisabled` | module runtime-deactivated (explicit command only -- see below) | `disable_module` | same | No |
| `ModuleLifecycleTransitioned` | lifecycle moved to a new status | `transition_module_lifecycle` | same + `lifecycle_status` | No |

**Rejected candidates:** `ModuleUnlicensed` (grant/revoke terminology fits a SaaS entitlement
model better than a bare negation); one event per persisted field
(`LicensedChanged`/`EnabledChanged`/`LifecycleStatusChanged` -- rejected per this pass's own
"business facts, not field patches" constraint); one generic `ModuleEntitlementTransitioned`
carrying before/after state (rejected -- pushes interpretation onto every consumer and
reintroduces `ModuleChanged` under a new name); per-module `ModuleLicensed` events fired from
provisioning (rejected -- provisioning is a bootstrap fact, not N licensing facts).

**Cascade → event count decision:** a suspend/expire lifecycle transition that internally forces
`enabled=False` emits only `ModuleLifecycleTransitioned` -- never also `ModuleDisabled` -- because
the enablement change is an implementation consequence of the one lifecycle command, not an
independent business action (mirrors this same pass's own §9 example). Symmetrically, revoking a
license emits only `ModuleLicenseRevoked`, never also `ModuleDisabled`/a lifecycle event.

**ViewInvalidation / Qt implications (not implemented, recorded for P5B-3):** discovery's
existing matrix already names three real consumers of `modules_changed` -- settings, control, and
access workspace controllers, all currently full-refreshing. All five recommended events map to
the same `OrganizationScope(tenant_id, organization_id)` / `module_entitlement` category; a single
shared handler can normalize all five into one `ViewInvalidationHint`, since all three current
consumers react identically today regardless of which sub-fact changed.

**Recommended implementation sequence:**

- **P5B-1** — replace `set_module_state` with the five explicit command methods on
  `ModuleEntitlementService` (no `DomainEvent`s yet); update the ~13 existing call sites and the
  three presenter methods; resolve the silent fourth-producer audit gap found above. → review.
- **P5B-2** — add the 5 `DomainEvent`s at the now-unambiguous command boundaries, recorded via
  `uow.record_event(...)`. → review.
- **P5B-3** — map to `ViewInvalidationHint`/`OrganizationScope` and migrate the three real Qt
  consumers directly (pre-release direct convergence, no bridge), per the same policy already
  applied to Organization in P5A/P6A. → review.

**Explicit non-goals:** no `DomainEvent` classes added; no `ViewInvalidation`; no Qt consumer
migration; no change to `provision_organization_entitlements`'s own signature or the silent
fourth producer's behavior; P5C not started; no commits.

### P5B-1 — Module Entitlement Semantic Command Model (implemented)

**Status:** implemented, reviewed. The generic `set_module_state(licensed=..., enabled=...,
lifecycle_status=...)` mutation API is retired -- direct pre-release convergence, no compatibility
wrapper kept.

**Command API** (`ModuleCatalogMutationMixin`, `src/core/platform/application/tenant/modules/module_catalog_mutation.py`):
`license_module`, `revoke_module_license`, `enable_module`, `disable_module`,
`transition_module_lifecycle` -- each requires an explicit `organization_id` (unchanged from the
P5B prerequisite pass), enforces its own preconditions, and shares one private transaction/audit
helper (`_run_module_transition`/`_apply_module_transition_using`) that opens exactly one fresh
`ModuleEntitlementUnitOfWork`, applies one pure transition function, stages the audit entry in the
same Session, and commits once. `PlatformRuntimeApplicationService` and
`PlatformRuntimeDesktopApi` grew matching five-method surfaces (resolving/forwarding the active
organization respectively); `ModuleStatePatchCommand` is deleted. The settings-workspace
presenter's three UI actions (`toggle_module_license`/`toggle_module_enabled`/
`change_module_lifecycle_status`) now route to the matching semantic call directly -- no QML
change was needed, since QML already called presenter/controller intentions, not raw state.

**Idempotency:** each command always persists (preserving the legacy-storage-code normalization,
e.g. `payroll` -> `hr_management`, that any real mutation call performs), but a value-for-value
no-op (e.g. enabling an already-enabled module) never changes the resulting business state --
`license_module` on an already-licensed module explicitly preserves the current
`lifecycle_status`/`enabled` (never resets a trial back to `active`).

**Naming decision:** kept `ModuleLicensed`/`ModuleEnabled`/`ModuleDisabled` for the eventual P5B-2
vocabulary rather than switching to `ModuleLicenseGranted` -- the command method is named
`license_module` (not `grant_module_license`), and "license"/"revoke" already reads clearly as a
grant/revoke pair without needing the extra word; `ModuleLicenseRevoked` stays as originally
proposed since a bare `ModuleUnlicensed` reads less clearly than its counterpart.

**Remaining debt (explicitly not resolved in P5B-1):** `ModuleCatalogContextMixin._ensure_context_defaults`
still silently seeds default entitlement rows on first read for an organization with none yet, with
no audit entry and no signal -- flagged, not fixed, since resolving it is unrelated to the command
API refactor and was never in scope.

**Exit criteria met:** all five commands implemented and unit-tested against the full state
machine (grant/revoke, enable/disable, all four user-selectable lifecycle targets, rejected
`inactive` target, idempotency, non-active-organization scope, UoW/audit atomicity, commit-failure
rollback); zero `DomainEvent`/`record_event(` occurrences in the Module Entitlement capability
(enforced by an updated architecture guard test); architecture guardrail suite (13 failed/160
passed), full Platform suite (13 failed/12 errors/912 passed), and PM/Inventory suite (14
failed/1481 passed) all show the same pre-existing failure identities as the established baseline
-- no new regression.

### P5B-2 — Module Entitlement Typed DomainEvents (implemented)

**Status:** implemented, reviewed. Adds the five business events at P5B-1's now-unambiguous
command boundaries. Still no ViewInvalidation, no Qt adapter, no `modules_changed` removal --
P5B-3 owns that consumer/invalidation cutover, exactly mirroring how P5A's event work preceded
P6A's Qt cutover for Organization.

**Events** (`src/core/platform/domain/tenant/modules/events.py`): `ModuleLicensed`,
`ModuleLicenseRevoked`, `ModuleEnabled`, `ModuleDisabled` (each `tenant_id`, `organization_id`,
`module_code`, `occurred_at`), and `ModuleLifecycleTransitioned` (adds
`previous_lifecycle_status`/`lifecycle_status`). All frozen/slots/kw-only dataclasses, no
ViewInvalidation/Qt/legacy-signal import, no execution metadata (that stays on
`DomainEventContext`).

**Recording location:** application-authored via `uow.record_event(...)` inside
`ModuleCatalogMutationMixin._apply_module_transition_using` (the same shared transaction/audit
helper P5B-1 introduced) -- `ModuleEntitlement` remains a plain projection with no transition
methods, so this is the same application-recorded escape hatch `OrganizationCreated` established
in P5A, not aggregate-recording.

**No-op/transition detection:** authoritative, not guessed from caller input -- the shared helper
compares the transition function's returned `(licensed, enabled, lifecycle_status)` tuple against
the entitlement's state *before* the transition ran; an event is recorded only when that tuple
actually changed. This single check correctly implements every P5B-SEM no-op/cascade rule at once
(idempotent license/revoke/enable/disable, same-target lifecycle transitions) without a separate
per-command no-op flag, because each transition function itself already encodes the correct
cascade/no-op behavior in what it returns.

**License idempotency confirmed, not reopened:** licensing an already-licensed module (e.g.
`licensed=True, lifecycle_status=trial`) is a true no-op -- `_license_module_transition` returns
the entitlement completely unchanged in that case, preserving `trial` rather than resetting to
`active`. No `ModuleLicensed` is recorded. Verified by source inspection and a dedicated
regression test before any event code was trusted to depend on it.

**Cascade single-fact policy, protected by tests:** `revoke_module_license` records exactly one
`ModuleLicenseRevoked`, never also `ModuleDisabled`/`ModuleLifecycleTransitioned`, even though it
forces `enabled=False`/`lifecycle_status=inactive`. `transition_module_lifecycle` into
suspended/expired records exactly one `ModuleLifecycleTransitioned`, never also `ModuleDisabled`,
even though it forces `enabled=False`.

**Clock:** `ModuleCatalogService` gained an optional `clock: Clock | None = None` constructor
parameter (composition passes `SystemClock()`); the shared transaction helper raises
`RuntimeError` if a real transition needs to record an event but no Clock is configured -- mirrors
the existing `_uow_factory is None` guard pattern, checked only where actually needed so the
`build_default_module_catalog`/provisioning-throwaway construction sites (which never reach event
code) don't need a Clock at all.

**Explicitly excluded from event semantics (tested):** `provision_organization_entitlements`
(bootstrap/default-row materialization) and `ModuleCatalogContextMixin._ensure_context_defaults`
(silent read-time seeding, remaining tracked debt, unchanged) both bypass the semantic command
pipeline entirely and therefore structurally cannot emit any of the five events -- proven, not
just asserted.

**Legacy `modules_changed` unchanged:** every semantic command still emits it unconditionally
after a successful commit (never on rollback/commit-failure), exactly as before P5B-2 -- no bridge
built, no rewiring, per the explicit "keep it for one more review phase" instruction.

**Exit criteria met:** all 5 events implemented and tested (contract/architecture guards,
exactly-one-event-per-real-transition, zero-events-on-no-op for every command, cascade
single-fact protection, non-active-organization and foreign-tenant-rejection scoping, Clock
determinism, DomainEventContext carries execution metadata separately from the event,
rollback/commit-failure produces zero observable events, one failing post-commit handler doesn't
block another or the commit); the retired P5B-1 phase-boundary guard was replaced with a
P5B-2→P5B-3 boundary guard (no ViewInvalidation/Qt vocabulary yet); architecture guardrail suite
(13 failed/160 passed), full Platform suite, and PM/Inventory suite all show the same pre-existing
failure identities as the established baseline -- no new regression.

**Explicit non-goals:** ViewInvalidation, Qt module adapter, `modules_changed` removal/bridge,
P5C. All deferred to P5B-3.

### P5B-3 — Module Entitlement ViewInvalidation + Direct Qt Consumer Cutover (implemented)

**Status:** implemented, reviewed. Direct pre-release convergence -- no
`ModuleEnabled -> modules_changed` bridge. `modules_changed` is retired completely (Signal field
and bridge-spec entry both removed from `domain_events.py`).

**Producer inventory (before cutover):** exactly two, both in `module_catalog_mutation.py` --
the shared `_run_module_transition` helper (fired for all five semantic commands, unconditional
post-commit) and `provision_organization_entitlements`'s conditional emit (only when the
provisioned organization was already the active one, and only when called with `commit=True`).

**Consumer inventory and end-to-end trace (before cutover) -- three subscribers, one real:**

- **Settings workspace** (`refresh()` -> `build_module_entitlements()`): **Category A, real.**
  Directly displays the module entitlement collection. Migrated.
- **Control workspace** (`refresh()` -> approval queue + audit feed only): **Category C,
  unrelated.** Traced end-to-end -- never reads any module-entitlement state. Subscription
  dropped, not migrated.
- **Access workspace** (`refresh()` -> `scope_type_options`/user/role/scope-grant/security-user
  lists): initially suspected **Category A** (the fake QML-preview test helper crafts a
  storeroom-scope-type-disabled-when-inventory-off example), but tracing the REAL desktop-API
  wiring (`desktop_api_registry.py`'s `access_scope_type_choices`/`access_scope_option_loaders`)
  found the storeroom scope type is gated purely by whether the Inventory service object was
  composed at startup (`inventory_service is not None`), never by live
  `module_catalog_service.is_enabled(...)` state. **Corrected to Category C.** Subscription
  dropped, not migrated. (This correction is recorded explicitly because the fake test data's
  crafted example was initially mistaken for real behavior -- a caution for any future consumer
  trace that leans on `_platform_test_helpers.py`'s fakes instead of the real composition wiring.)

**ViewInvalidation target:** one category, `module_entitlement`, one scope code,
`module_entitlements`, `OrganizationScope(tenant_id, organization_id)` -- never
`TenantWide`/`AllTenants` (Organization P6A's hardening rule applied from the start this time).
All five events collapse onto the SAME mapping handler
(`src/core/platform/application/tenant/modules/event_handlers/view_invalidation.py`) -- one
function, five `post_commit_bus.subscribe(...)` registrations in `platform_registry.py`, never
five copies.

**Provisioning invalidation decision:** `provision_organization_entitlements` itself never
actually reaches its own `commit=True` branch in production -- its one real caller
(`PlatformRuntimeApplicationService.provision_organization`) always passes `commit=False` and
commits everything together via its own outer UoW (this was already true of the retired legacy
`modules_changed` emit in the exact same spot -- not a P5B-3 regression, a pre-existing dead
branch now documented rather than silently carried forward). The REAL provisioning-activation
invalidation is wired in `provision_organization` itself: when `is_active=True`, immediately
after `self._tenant_context_service.set_active_organization(...)` succeeds (post-commit), it
calls the new public `ModuleCatalogService.notify_module_entitlements_stale(organization_id)` --
direct ViewInvalidation, never one of the five DomainEvents, since materializing default rows for
a new organization is not a licensing fact. Provisioning a non-active organization (`is_active=
False`, the overwhelmingly common case) produces neither an event nor an invalidation, proven by
test.

**Read-time default seeding:** unchanged, still silent (no event, no invalidation) -- the read
that triggers `_ensure_context_default_rows` returns the freshly materialized rows directly, so
no other already-loaded view needs a nudge. Remains tracked debt, not resolved here.

**Qt adapter:** `ModuleEntitlementViewInvalidationAdapter`
(`src/ui_qml/platform/adapters/module_entitlement_view_invalidation_adapter.py`), mirroring
`OrganizationViewInvalidationAdapter`'s shape exactly (`set_active_scope(tenant_id=...,
organization_id=...)` disposes-then-resubscribes, `dispose()`), emitting
`moduleEntitlementsStale`. Connected only to `PlatformSettingsWorkspaceController`'s new narrow
`refresh_module_entitlements()` (re-reads the module entitlement list and its derived metrics,
not organization profiles/integration capabilities).

**Tenant AND organization switch lifecycle:** re-scoped via
`PlatformWorkspaceCatalog.refreshCurrentPermissions()` -- the existing hook the QML shell already
calls immediately after BOTH a tenant switch and an organization switch
(`PlatformWorkspacePage.qml`'s `ContextBar.onTenantSelected`/`onOrganizationSelected`), since this
desktop shell has no dedicated "organization switched" Qt signal the way
`TenantSwitcherController.tenantSwitched` exists for tenants. Proven structurally (live
subscription's `ExactOrganization` filter correctly follows both switch kinds, old scope disposed
before the new one is added, never two live at once).

**Exit criteria met:** all five events map to exactly one `ViewInvalidationHint` with the correct
`OrganizationScope`/category/scope_code; no-op commands produce zero invalidation (inherited
directly from P5B-2's zero-event guarantee); rollback/commit-failure produces zero invalidation;
non-active-organization mutation does not refresh the active organization's UI; a foreign-tenant
organization is rejected before any invalidation; real end-to-end proof through
`PlatformWorkspaceCatalog` that the settings workspace refreshes after a real mutation and does
not refresh after a no-op/rolled-back one; Control and Access workspaces proven to no longer react
at all; tenant-switch and organization-switch lifecycle proven with no stale/duplicate
subscription; provisioning's two branches (active/non-active) proven correct; architecture
guardrail suite (13 failed/160 passed), full Platform suite, and PM/Inventory suite all show the
same pre-existing failure identities as the established baseline -- no new regression.

**Explicit non-goals:** P5C not started. Organization slice untouched.

## P5C — Access/RBAC Transaction & Scope Convergence

### P5C Prerequisite / Discovery Audit (complete)

Access-security-sensitive, so P5C began with an investigation-only pass before any event
vocabulary was proposed. Key findings:

- **Access and RBAC are ONE persistence/business-fact capability, not two.**
  `AccessControlService.assign_scope_grant`/`remove_scope_grant` (canonical scope types
  `project`/`site`/`storeroom`) are thin facades that delegate entirely to
  `RoleGovernanceService.assign_role`/`revoke_role_binding` -- there is no separate
  `ScopedAccessGrant` persistence table; it is a read/write DTO facade over the canonical
  `RoleBinding` model.
- **Future assignment event vocabulary decided:** `RoleBindingAssigned`/`RoleBindingRevoked`
  (not implemented until P5C-2).
- **Confirmed ambient-organization bug in the storeroom scope resolver:** `_storeroom_exists`
  (`inventory_registry.py`) compared `storeroom.organization_id` against the CURRENTLY ACTIVE
  organization, making it structurally impossible to grant/revoke storeroom-scoped access for a
  storeroom in any non-active organization within the caller's own tenant. A narrow fix was
  applied at the time (`organization_repo.get_for_tenant(storeroom.organization_id, tenant_id)`
  instead of an ambient comparison) and validated by a new regression test.
- Custom-role *definition* CRUD (`TenantRoleAdministrationService`) is a separate, unrelated
  capability, explicitly out of scope for P5C.

**Outcome:** P5C PREREQUISITE COMPLETE — DESIGN DECISION REQUIRED. P5C-1 (below) was scoped as
transaction/scope convergence only, deferring the event vocabulary to P5C-2.

### P5C-1 — Role Governance Transaction & Scope Convergence (implemented)

**Status:** implemented, reviewed. `RoleGovernanceService`'s four mutation methods
(`assign_role`/`revoke_role_binding`/`create_delegation_policy`/`revoke_delegation_policy`) cut
over from the shared process-lifetime `Session` and inline `commit()`/`rollback()` onto a
canonical `RoleGovernanceUnitOfWork` -- one fresh `Session` per call, matching the established
`OrganizationUnitOfWork`/`ModuleEntitlementUnitOfWork`/`PlatformProvisioningUnitOfWork` pattern.
No `RoleBindingAssigned`/`RoleBindingRevoked` events, no ViewInvalidation, no Qt migration, no
`access_changed`/`auth_changed` removal -- all explicitly deferred to P5C-2/P5C-3.

**Scope resolution model:** a new closed union, `ResolvedRoleBindingScope`
(`PlatformBindingScope`/`TenantBindingScope`/`ResourceBindingScope`), resolved INSIDE the
transaction before commit -- `organization_id=None` is never used as a magic "tenant-wide"
signal; `ResourceBindingScope.organization_id` is `None` only when the resource genuinely has no
organization owner.

**REOPENED FINDING — the P5C prerequisite's storeroom fix was incomplete (discovered and closed
during P5C-1):** the prerequisite fix corrected `_storeroom_exists`'s own comparison logic, but
its FIRST line, `storeroom_repo.get(storeroom_id)`, itself unconditionally filters to the
ambient active organization (`TenantScopedRepositorySupport._apply_scope`, via
`require_active_scope_ids()` reading the SESSION-level active organization) -- so for a
storeroom in a non-active organization, that read still returned `None` before the "fixed"
comparison logic was ever reached. The prerequisite's own regression test
(`test_storeroom_scope_grant_targets_a_non_active_organization`) was a **false negative**: it
only flipped `Organization.is_active` in the database (via
`create_organization(is_active=True)`), a completely different mechanism from the
SESSION-level active organization (`tenant_context_service`/`user_session
.active_organization_id()`) that `require_active_scope_ids()` actually reads -- the ambient
session org never moved off the original organization, so the test never exercised the bug it
claimed to prove fixed.

**Resource-resolver audit (repository call chain, traced to the actual filter, not just the
resolver function):**

| Scope type | `scope_exists_resolver` registered? | Underlying repository read | Ambient-org-scoped? | Organization ownership | Fixed in P5C-1 |
|---|---|---|---|---|---|
| `organization` | Yes (`platform_registry.py`, at `RoleGovernanceService` construction) | `OrganizationRepository.get_for_tenant()` | No (never was -- an organization cannot be scoped to itself) | Identity (`organization_id` == the resource id) | N/A, already correct |
| `project` | Yes (`project_registry.py`) | Was `ProjectRepository.get()` (ambient); now `ProjectRepository.get_for_tenant()` (new, tenant-scoped only) | Was YES, now NO | `Project.organization_id` (optional in the domain model -- some projects genuinely have none) | **Yes** |
| `site` | Yes (`platform_registry.py`, at `RoleGovernanceService` construction -- a registration the P5C prerequisite pass's own resolver inventory missed entirely, since it only grepped for `register_scope_exists_resolver(...)` calls) | Was `SiteRepository.get()` (ambient); now `SiteRepository.get_for_tenant()` (new, tenant-scoped only) | Was YES, now NO | `Site.organization_id` (required) | **Yes** |
| `storeroom` | Yes (`inventory_registry.py`) | Was `StoreroomRepository.get()` (ambient, the reopened finding); now `StoreroomRepository.get_for_tenant()` (new, tenant-scoped only) | Was YES, now NO | `Storeroom.organization_id` (required) | **Yes** |
| `department` | **No** -- not registered anywhere in composition | `DepartmentRepository.get()` is ALSO ambient-org-scoped, but this is moot | Unreachable regardless | `Department.organization_id` (required) | Not fixed -- enabling a brand-new resource scope from scratch (a `ScopedRolePolicy`, role choices, a catalog role, a delegation-namespace convention) is a materially larger feature addition than closing an existing resolver's ambient-scope defect, and stays out of P5C-1's boundary. Documented, not implemented. |

**Fix mechanics:** each of `ProjectRepository`/`SiteRepository`/`StoreroomRepository` gained a
new `get_for_tenant(resource_id, tenant_id)` method (contract + implementation), mirroring
`OrganizationRepository.get_for_tenant`'s existing shape -- a plain tenant-id filter, never the
ambient active organization. `RoleGovernanceService`'s own `ScopeExistsResolver`/
`OrganizationOwnerResolver` callables were additionally changed to take the calling
`RoleGovernanceUnitOfWork`'s own `Session` as their first argument (`RoleGovernanceUnitOfWork`
now exposes `session` as a capability-specific typed accessor, per ADR-005 §9's guidance that
the shared `UnitOfWork` Protocol itself stays session-free) -- composition constructs a fresh,
capability-appropriate repository bound to that Session per call, so the resource-scope
existence/ownership check reads within the SAME transaction as the binding mutation and audit
entry it gates, never a separate legacy Session. `AccessControlService`'s own (separate,
non-transactional) pre-flight `_assert_scope_exists` check and `AuthService`'s effective-
permissions resolver keep the older `(tenant_id, scope_id) -> bool` signature, now backed by the
same fixed `get_for_tenant` reads for correctness, without adopting the session parameter (out
of scope -- `AuthService`'s `CanonicalRoleResolver` is a read-time, non-transactional
effective-permissions computation, not audited further in this pass).

**Organization-ownership resolvers registered:** `organization` (identity), `project`, `site`,
`storeroom` -- all now resolve a RESOURCE-scoped binding's authoritative `organization_id`
inside the transaction, so a future P5C-2 event never needs a post-commit re-query. `department`
has none (unreachable).

**Final resource ownership matrix (every `RESOURCE_ROLE_SCOPE_TYPES` member, plus the two
non-resource scope kinds):**

| Scope kind | `tenant_id` source | `organization_id` source | Repository method | Active-org-scoped? | Non-active-org administration works? | Organization ownership explicit? |
|---|---|---|---|---|---|---|
| `platform` | N/A (no tenant) | N/A (never) | N/A -- no repository read; platform-role assignment is denied outright in `assign_role`/`revoke_role_binding` (`PLATFORM_ROLE_ASSIGNMENT_DENIED`) | N/A | N/A | N/A -- `PlatformBindingScope` carries neither field |
| `tenant` | The caller's own authenticated active tenant (`require_active_tenant_id`), never ambient-organization-derived | N/A (never) | N/A -- no resource repository involved | N/A | N/A (tenant-wide by definition) | N/A -- `TenantBindingScope` carries only `tenant_id` |
| `organization` | Resolver parameter (the active tenant) | Identity -- the scope IS the organization | `OrganizationRepository.get_for_tenant(id, tenant_id)` | No -- never was | **Yes**, proven by test | Yes -- identity |
| `project` | Resolver parameter | `Project.organization_id` (optional in the domain model) | `ProjectRepository.get_for_tenant(id, tenant_id)` (new, P5C-1) | Was yes, now **no** | **Yes**, proven by test (both directions) | Yes -- resolved via `organization_owner_resolver` |
| `site` | Resolver parameter | `Site.organization_id` (required) | `SiteRepository.get_for_tenant(id, tenant_id)` (new, P5C-1) | Was yes, now **no** | **Yes**, proven by test | Yes -- resolved via `organization_owner_resolver` |
| `storeroom` | Resolver parameter | `Storeroom.organization_id` (required) | `StoreroomRepository.get_for_tenant(id, tenant_id)` (new, P5C-1) | Was yes, now **no** (the reopened finding) | **Yes**, proven by test (both directions) + cross-tenant rejection | Yes -- resolved via `organization_owner_resolver` |
| `department` | N/A -- unreachable, no resolver registered | `Department.organization_id` (required; trivially derivable, confirmed directly against a real row) | `DepartmentRepository.get()` only (no `get_for_tenant`) | **Yes**, confirmed by direct repository test -- shares the SAME defect class, unfixed | No -- unreachable regardless (no `scope_exists_resolver`, no catalog role declares `allowed_scope_type == "department"`) | Ownership model itself is NOT a blocker (a plain required column, same shape as `Site`/`Storeroom`) -- what's missing is the whole feature (policy/role/resolver wiring), which is out of P5C-1's transaction/scope-convergence boundary |

No organization-owned resource scope that IS reachable depends on the ambient active
organization. `department`'s gap is a "never wired up" gap, not an ownership-model gap, and is
therefore not a `P5C-1 RESOURCE OWNERSHIP MODEL BLOCKER`.

**Session-refresh characterization:** `RoleGovernanceService.assign_role`/`revoke_role_binding`
themselves never call `refresh_current_session_if_user` -- that is deliberately the calling
facade's responsibility (`role_assignment_service.py`'s legacy tenant-role functions,
`AccessControlService`). The already-established fail-closed mechanism
(`refresh_current_session_if_user` clearing the session if rebuilding the principal fails after
a successful commit) needed no redesign; `AccessControlService`'s own weaker, non-fail-closed
duplicate was fixed to delegate to the canonical helper.

**Retained legacy duplication (documented, not resolved):** going through the Access facade
fires both `auth_changed` (from `RoleGovernanceService`) and `access_changed` (from
`AccessControlService`) for the same underlying mutation, while the legacy tenant-role facade
fires only `auth_changed`. Left for P5C-3.

**P5C-2 field readiness (explicit decision, not yet implemented):** at the point `assign_role`/
`revoke_role_binding` call `uow.commit()`, every field a future `RoleBindingAssigned`/
`RoleBindingRevoked` event will need is already available without a post-commit re-query:
`target.id` (principal_id), `role.id`, the resolved scope kind plus its `tenant_id`/
`scope_type`/`scope_id`/`organization_id` (via `ResolvedRoleBindingScope`), and `binding.id`
(assigned client-side by `RoleBinding.create()` before the row is even inserted). **Decision:
`binding_id` SHOULD be included** in the P5C-2 event payload -- `RoleBinding` is a durable
business identity already referenced by `revoke_role_binding(binding_id)`, by every audit entry
(`entity_id=binding.id`), and by `AccessControlService`'s `ScopedAccessGrant.id`, so a consumer
reacting to the event (permission-cache invalidation, audit correlation, a future UI list) can
reasonably need to correlate back to the specific binding without a second query. This follows
the recommended default (a durable, externally-referenced identity is included; a purely
persistence-internal one would be omitted) rather than defaulting to omission.

**Test coverage:** `test_role_governance_unit_of_work_cutover.py` (fresh-session-per-mutation,
shared-UoW-session repository/audit, no global-Session touch, commit-failure rollback with zero
legacy notification, non-active-organization success for storeroom/project/site/organization,
cross-tenant storeroom rejection, department's confirmed non-reachability, self-assignment
session-refresh ordering, fail-closed refresh-failure characterization, facade non-transaction-
ownership, architecture guards for no inline commit/rollback and no P5C-2 event vocabulary) plus
a corrected `test_storeroom_scope_grant_targets_a_non_active_organization` (now manipulating the
real session-level active organization, with an added inverse-direction test) in
`test_platform_access_scopes.py`.

**Regression:** architecture suite, full Platform suite (`src/tests/platform`), and PM/Inventory
suites all run against a single stable HEAD (no concurrent-commit drift observed); failures
present are the same pre-existing/unrelated identities already tracked before this phase (the
two `Site` domain-validator datetime-comparison failures were independently confirmed present in
the very first commit of this working session, unrelated to any P5C-1 change).

**Explicit non-goals:** `RoleBindingAssigned`/`RoleBindingRevoked` events (P5C-2), ViewInvalidation
and Qt migration (P5C-3), `access_changed`/`auth_changed` removal, custom-role CRUD, Tenant
Membership (P5D), and enabling `department` as a new role-assignment scope.

### P5C-2 — RoleBinding Typed DomainEvents (implemented)

**Status:** implemented, reviewed. `RoleGovernanceService.assign_role`/`revoke_role_binding`
now record exactly ONE canonical business fact per real transition -- `RoleBindingAssigned`/
`RoleBindingRevoked` -- via `uow.record_event(...)`, before `uow.commit()`, mirroring
`OrganizationCreated`/`ModuleLicensed`'s own application-authored precedent (`RoleBinding` has
no transition methods to record itself on). No ViewInvalidation, no Qt migration, no
`access_changed`/`auth_changed` removal, no delegation-policy or custom-role events -- all still
explicitly deferred to P5C-3 (or, for custom-role CRUD, indefinitely out of RoleBinding's own
event family).

**Event vocabulary and location:** `RoleBindingAssigned`/`RoleBindingRevoked`
(`src/core/platform/domain/security/authorization/roles/events.py`) -- Platform's RBAC domain
capability owns them, matching Organization/Module's own package-per-capability convention. Pure
business vocabulary: no ViewInvalidation/Qt/SQLAlchemy import, no dispatch/execution metadata
(`correlation_id`/`causation_id`/`command_id` stay on `DomainEventContext`, never duplicated).

**Fields (both events):** `binding_id`, `principal_id`, `role_id`, `scope`, `occurred_at`.
`binding_id` is included deliberately (the P5C-1 review's explicit decision, confirmed again
here) -- `RoleBinding.id` is a durable identity already referenced by
`revoke_role_binding(binding_id)`, every audit entry, and `ScopedAccessGrant.id`. The acting
administrator is never a field -- audit already records that separately; the event's subject is
the affected principal.

**Typed scope, not flattened nullable IDs:** a new domain-facing union,
`RoleBindingScope = RoleBindingPlatformScope | RoleBindingTenantScope | RoleBindingResourceScope`
(`role_binding_scope.py`, same package). Deliberately NOT a reuse of P5C-1's own
`ResolvedRoleBindingScope` (`PlatformBindingScope`/`TenantBindingScope`/`ResourceBindingScope`)
-- that is application/orchestration terminology resolved mid-transaction against UoW-bound
repositories, and importing it into a domain event would have the domain layer depend on the
application layer, backwards. Also deliberately NOT a reuse of
`src/core/shared/events/view_invalidation.py`'s own `PlatformScope`/`TenantScope`/
`OrganizationScope` names (ViewInvalidation targeting infrastructure, P5C-3's concern) --
distinct names (`RoleBindingPlatformScope`/etc.) make the two families impossible to confuse.
`RoleGovernanceService._to_domain_scope()` converts its resolved `ResolvedRoleBindingScope` into
the domain-facing type when recording `RoleBindingAssigned`; `revoke_role_binding` has no
pre-resolved scope on hand (the binding already exists), so a sibling
`_resolve_domain_scope_for_binding()` re-resolves the authoritative organization ownership from
the binding's own recorded `actual_scope_type`/`actual_scope_id` (captured BEFORE the revoke
mutation, never re-derived from the current desktop UI scope after the fact) via the same
session-bound `organization_owner_resolver`.

**Recording points:** exactly one per method, staged inside the same transaction as the binding
mutation and audit entry, immediately before `uow.commit()` -- never from
`AccessControlService`, never from `role_assignment_service.py`'s tenant-role facade, never
after commit, never twice. Both facades converge on `RoleGovernanceService.assign_role`/
`revoke_role_binding`, so exactly one `RoleBindingAssigned`/`RoleBindingRevoked` is produced
regardless of which facade the caller used (proven by test; `access_changed`/`auth_changed`
still additionally fire per the pre-existing, documented legacy duplication -- unchanged by this
phase).

**No-op semantics preserved exactly:** assigning an identical already-active binding and
revoking an already-revoked binding both still short-circuit before any write/audit/event --
zero `RoleBindingAssigned`/`RoleBindingRevoked` for a no-op, matching P5C-1's own established
rule ("no transition -> no event").

**Clock:** `RoleGovernanceService` now takes an injected `clock: Clock` (`SystemClock()` from
composition, mirroring Organization/Module) for `occurred_at` -- never a direct
`datetime.now()`/`utcnow()` call for the event's own timestamp (pre-existing `revoked_at`/audit
timestamps elsewhere in the service are unchanged, out of this phase's narrow scope).

**Non-active-organization / cross-tenant proof:** the event's `scope.organization_id` is proven,
by test, to carry the resource's OWN authoritative organization (via the P5C-1-corrected
`get_for_tenant` repository reads) for storeroom/project/site even while a different
organization is ambiently active -- never the ambient one. A cross-tenant storeroom target
produces zero events (rejected before any resolution succeeds). Platform-scope assignment is
proven to still be denied by the pre-existing business rule (never weakened to manufacture a
platform-scoped event).

**Failure/rollback/isolation proofs:** delegation-denied and SoD-conflict failures produce zero
mutation/audit/event; audit-staging failure and commit failure both roll back the binding and
leave zero event observable to a post-commit subscriber; one failing post-commit handler does
not block another subscriber or the underlying commit (ISOLATE_AND_CONTINUE, unchanged); a
post-commit subscriber receives the command's own `DomainEventContext`, with no execution
metadata duplicated onto the event itself.

**Current-principal refresh remains independent of event subscribers:** proven by test -- a
RoleBindingRevoked subscriber that raises does not prevent the existing, explicit post-commit
self-refresh flow (established in P5C-1) from running; fail-closed semantics on refresh failure
are unaffected by this phase (unchanged, not moved behind event dispatch).

**Test coverage:** `test_role_binding_events.py` (32 tests) -- event contract/architecture
guards (dataclass shape, frozen, approved-fields-only, no UI/ViewInvalidation/SQLAlchemy import
in the two new domain modules, shared `domain_event.py` does not import RoleBinding events,
neither facade records events, no P5C-3 production code, no new arbitrary Session usage in
`RoleGovernanceService`), Clock injection, assign/revoke recording + no-op, platform/tenant/
resource scope variants (storeroom/project/site, non-active-org and cross-tenant), delegation-
denied/SoD-conflict/audit-failure/commit-failure/handler-failure isolation, context propagation,
current-principal-refresh independence, legacy-signal coexistence, delegation-policy
eventlessness, and committed-order sequencing.

**Regression:** focused Access/RBAC suite 117 passed / 1 pre-existing failure; architecture
suite 142 passed / 13 pre-existing failures (identical identities to P5C-1's own run); full
Platform suite 1015 passed / 15 failures / 12 errors (identical identities to P5C-1's own run).
PM/Inventory not re-run -- no repository code changed in this phase (P5C-2 only added domain
events and wired `RoleGovernanceService`; the P5C-1 `get_for_tenant` repository additions are
unchanged).

**Explicit non-goals:** ViewInvalidation and Qt migration (P5C-3), `access_changed`/
`auth_changed` removal, delegation-policy events, custom-role CRUD events, Tenant Membership
(P5D).

### P5C-3 — RoleBinding ViewInvalidation + Direct UI Cutover (implemented; P5C now complete)

**Status:** implemented, reviewed. Both RoleBinding events map onto ONE `ViewInvalidationHint`
target (`role_binding`/`role_binding_assignments`); the real UI consumer (Access workspace's
`scopeGrants` list) is migrated directly onto `RoleBindingViewInvalidationAdapter` --
`access_changed` is retired entirely (no bridge), and `auth_changed` is kept but narrowed (see
below). P5C's three sub-phases (prerequisite audit, P5C-1 transaction/scope convergence, P5C-2
typed events, P5C-3 this section) are now all complete.

**`auth_changed`/`access_changed` full producer/consumer trace (mandatory first step):**
`access_changed` had exactly two producers, both in `AccessControlService.assign_scope_grant`/
`remove_scope_grant` -- both delegating to the SAME canonical `RoleGovernanceService.assign_role`/
`revoke_role_binding` mutation `auth_changed` (and now `RoleBindingAssigned`/`RoleBindingRevoked`)
already covers, and exactly one real consumer (`access_workspace_controller.py`'s coarse
`refresh()` reaction). `auth_changed` has TWELVE producer files: `RoleGovernanceService` (now
redundant with the typed event for that ONE fact) plus eleven genuinely unrelated,
still-untyped security facts -- session/authentication lifecycle, MFA, password changes,
federated identity, user registration/bootstrap, user admin actions, policy reconciliation, and
tenant membership. It has TWO real consumers: the Access workspace (migrating here) and the
temporary Admin Console composite (`admin_console/domain_event_binder.py`, explicitly documented
as removed wholesale in the already-planned R2 migration, decomposing 9 sub-controllers into
independent ones) -- whose user-catalog sub-controller genuinely displays `role_names` and calls
the legacy tenant-role facade's own `assign_role`/`revoke_role`, so it is a real, currently-live
RoleBinding-derived consumer, not dead code.

**Producer classification:**

| Producer | Classification | Disposition |
|---|---|---|
| `RoleGovernanceService.assign_role`/`revoke_role_binding` | A -- now covered by `RoleBindingAssigned`/`RoleBindingRevoked` | **Kept, not deleted** -- the Admin Console user-catalog consumer (Category B relative to this producer, since it is NOT the Access workspace and is out of P5C-3's own boundary) still needs it. Removing it would silently break a real, currently-shipping feature for an unrelated, already-planned migration this phase does not own. |
| Session/authentication, MFA, password, federated identity, registration/bootstrap, user admin, policy reconciliation, tenant membership (11 files) | B -- real, distinct, still-untyped security facts | Retained unchanged -- each is its own future event slice, not RoleBinding's. |

**Consumer classification and disposition:**

- **Access workspace `scopeGrants`** (Category A, RoleBinding-derived): migrated to
  `RoleBindingViewInvalidationAdapter` -> `refresh_role_bindings()` (narrow: only
  `_refresh_scope_grants()`/`_refresh_empty_state()`).
- **Access workspace `security_users`** (Category B, genuinely depends on the OTHER
  `auth_changed` producers -- lockout/session state can change for any user in the tenant):
  kept on `auth_changed`, but re-routed from the old coarse `_on_domain_event` (-> full
  `refresh()`) to a new narrow `_on_auth_changed` (-> `_refresh_after_security_change()` only).
- **Access workspace `scope_type_options`/`user_options`/`role_options`/`scope_options`**
  (Category C, incidental over-refresh -- traced end-to-end, none of these ever depended on
  `auth_changed`/`access_changed` at all): no longer reloaded on either signal -- the single
  largest concrete benefit of this cutover.
- **Admin Console user catalog** (Category B, real, but not this phase's workspace):
  untouched, out of P5C-3's boundary.

**ViewInvalidation target:** one category, `role_binding`, one scope code,
`role_binding_assignments` (`src/core/platform/application/security/authorization/roles/
event_handlers/view_invalidation.py`), reused for both events -- the real consumer re-reads via
one call (`AccessControlService.list_scope_grants(scope_type, scope_id)`) regardless of
assignment vs. revocation.

**Scope routing, faithful to the typed union, never collapsed:** `RoleBindingPlatformScope` ->
`PlatformScope()`; `RoleBindingTenantScope(tenant_id)` -> `TenantScope(tenant_id)`;
`RoleBindingResourceScope(tenant_id, organization_id, ...)` -> `OrganizationScope(tenant_id,
organization_id)` when `organization_id` is present, else `TenantScope(tenant_id)` -- never a
fabricated organization for a genuinely ownerless resource. The authoritative `organization_id`
always comes from the event itself (resolved inside the RoleGovernance transaction per
P5C-1/P5C-2), never the desktop's ambient active organization.

**Qt adapter -- two subscriptions, not one:** `RoleBindingViewInvalidationAdapter`
(`src/ui_qml/platform/adapters/`) deliberately differs from `ModuleEntitlementViewInvalidationAdapter`'s
single-`ExactOrganization` shape: it holds BOTH a `TenantWide(tenant_id)` subscription (catches
tenant-scoped RoleBinding facts regardless of which organization is active -- the Access
workspace's `scopeGrants` list is not confined to one organization) AND an
`ExactOrganization(tenant_id, organization_id)` subscription (catches resource-scoped facts for
the currently active organization only). Neither `AllTenants()` nor
`AnyOrganizationInTenant(...)` is ever used. Re-scoped via the SAME `refreshCurrentPermissions()`
hook the module entitlement adapter uses, since a resource-scoped RoleBinding fact must follow
an organization switch exactly like module entitlements do, while a tenant-scoped fact must
survive it.

**Non-active-organization isolation, proven both ways:** a resource-scoped mutation for a
non-active organization produces no callback while a different organization is active, and
exactly one callback once switched to the matching organization -- and, symmetrically, a
tenant-scoped mutation produces a callback regardless of which organization happens to be
active (the `TenantWide` subscription is organization-independent by design).

**Facade audit (`AccessControlService`, mandatory before wiring consumers):** every
responsibility was classified. Categories A/genuine-application-policy (kept): the "Access" UI's
own `access.manage` permission gate (distinct from RoleGovernance's `auth.role.assign`), its
`_CANONICAL_SCOPE_TYPES` restriction to `{project, site, storeroom}` (a UI/use-case scope,
narrower than RoleGovernance's own broader support), the `scope_role` <-> canonical-role-name
<-> permission-set translation vocabulary, and the `ScopedAccessGrant` read-model DTO shape.
Category D (duplication, now retired): `domain_events.access_changed.emit(...)` -- the only
actual business-event duplication found; removed. The pre-existing `_assert_scope_exists`/
`_require_target_membership`/`_require_active_tenant_id` validation helpers are NOT pure
duplication despite overlapping with RoleGovernance's own internal checks -- `list_scope_grants`/
`list_user_scope_grants` (read paths) have no RoleGovernance mutation call to lean on and need
their own validation regardless; removing them from the write paths purely for minimalism risked
changing observable error-code behavior for existing consumers/tests for no correctness benefit,
so they were left in place.

**Decision: `AccessControlService` KEPT, not renamed.** It retains a real, non-redundant
responsibility (above) and remains thin, non-transaction-owning (delegates every mutation to
`RoleGovernanceService.assign_role`/`revoke_role_binding`), and now non-event-owning (the one
event-owning line was the retired `access_changed.emit`). A rename was considered (12 non-test
call sites) but not pursued -- "strongly consider if safe" is not "must," and the mechanical
rename cost was not justified by a correctness or clarity gain proportionate to this phase's
narrow mandate.

**Legacy signal final status:** `access_changed` -- **fully deleted** (Signal field,
`_BRIDGE_SPECS` entry, both producers, the one real consumer's subscription, and the one
test-only producer/consumer reference, all removed; confirmed zero remaining references
repository-wide). `auth_changed` -- **kept**, RoleGovernance's own two producer call sites
retained (a real remaining non-Access consumer still needs them), routed through a narrower
consumer-side handler for the one migrated workspace. No new typed-event -> legacy bridge was
created for either signal, per instruction.

**Test coverage:** `test_role_binding_view_invalidation_qt_cutover.py` (mapper contract and
scope routing including the ownerless-resource case, no Qt dependency in the mapper module,
real end-to-end Access-workspace-refresh-on-real-mutation, coarse-refresh retirement proof,
pre-commit/commit-failure/no-op non-observability, non-active-org isolation both directions,
tenant-scope organization-independence, cross-tenant no-invalidation, adapter dual-subscription
shape with no `AllTenants`/`AnyOrganizationInTenant`, tenant- and organization-switch lifecycle
through the real `refreshCurrentPermissions()`/`switchToTenant()` hooks with no subscription
accumulation, platform-scope denial with no fabricated hint) plus updated coverage in
`test_qml_domain_event_bridges_pm.py`, `test_secondary_workspace_lazy_loading.py`, and
`test_access_scope_domain_validation.py` for the retired `access_changed`/narrowed `auth_changed`
paths. One pre-existing, unrelated test (`test_organization_view_invalidation_qt_cutover.py`'s
own real-tenant-switch proof) needed a narrow fix: it scanned the WHOLE channel for any
`TenantWide` subscription, which the new RoleBinding adapter's own (independent) `TenantWide`
subscription now also satisfies -- fixed to resolve the Organization adapter's own tracked
subscription by id instead of a channel-wide type scan.

**Regression:** focused Access/RBAC + Qt cutover suite 154 passed / 1 pre-existing failure;
architecture suite 142 passed / 13 pre-existing failures (identical identities); full Platform
suite 1037 passed / 15 failures / 12 errors (identical identities to P5C-2's own run, after
fixing the one collision described above). PM/Inventory not re-run -- no shared/resource
repository behavior changed in this phase.

**Explicit non-goals:** delegation-policy events, custom-role lifecycle events, Tenant
Membership events, P5D.

## P5D — Tenant Membership

### P5D-SEM / Prerequisite Audit (complete; design decision required)

**Status:** investigation/design only, no code changes. Traced the complete real capability
(`UserTenantMembership` domain model, `TenantMembershipService`,
`SqlAlchemyUserTenantMembershipRepository`) before proposing any event.

**Real state machine (`src/core/platform/domain/tenant/tenancy/user_tenant_membership.py`):**
four persisted statuses -- `invited`/`active`/`suspended`/`removed` (`MEMBERSHIP_STATUSES`).
Unlike every prior P5 capability (Organization/Module/RoleBinding), `UserTenantMembership` is a
REAL aggregate with its own genuine transition methods encoding real invariants (not a plain
projection): `create()` (direct, no invitation), `invite()`, `accept_invitation()`, `suspend()`,
`reactivate()` (suspended -> active ONLY), `remove()` (active/suspended -> removed),
`revoke_invitation()` (invited -> removed, never accepted), `reinvite()` (invited/removed ->
invited). Membership identity is durable across the entire lifecycle -- confirmed at the
repository layer: `SqlAlchemyUserTenantMembershipRepository` has no delete method at all,
`update()` is an in-place, version-checked UPDATE on the same row/id (never a new one), and
`add()` explicitly rejects a second row for the same `(user_id, tenant_id)` pair
(`USER_TENANT_MEMBERSHIP_EXISTS`). "Removed" is a genuine soft-delete/tombstone status, never
physical deletion.

**Real mutation command inventory (`TenantMembershipService`):** `issue_invitation` (creates OR
reinvites), `accept_invitation`/`accept_invitation_for_tenant` (self-service, invited -> active,
also creates a default RoleBinding), `revoke_invitation` (invited -> removed, never accepted),
`suspend_member` (active -> suspended; guards last-tenant-admin, revokes affected sessions),
`reactivate_member` (suspended -> active only), `remove_member` (active/suspended -> removed;
guards last-tenant-admin, revokes affected sessions, AND bulk-revokes every active RoleBinding
for that principal in that tenant). A `deactivate(user_id, tenant_id)` convenience method exists
on the repository CONTRACT itself but has zero production callers anywhere in the repository --
a latent, currently-inert bypass of all authorization/audit/session-revocation logic (item 9's
"generic update API" concern, confirmed present but dormant; P5D-1 should either wire it
properly or remove it -- not decided here).

**Transaction ownership: CONFIRMED LEGACY -- this is the decisive finding.**
`TenantMembershipService` is constructed with the SAME shared, process-lifetime `session` object
`platform_registry.py` threads through the whole composition graph, and every mutation method
uses inline `self._session.commit()`/`self._session.rollback()` (`issue_invitation`,
`_accept_membership`, `_persist_administrative_transition` -- the shared helper behind
`revoke_invitation`/`suspend_member`/`reactivate_member`/`remove_member`), exactly the pattern
P5C-1 had to converge `RoleGovernanceService` away from. Per the mandatory gate: **no
TenantMembership DomainEvents may be implemented before this capability converges to a narrow
canonical UoW** (a `TenantMembershipUnitOfWork`, mirroring `RoleGovernanceUnitOfWork`'s own
shape) -- this is P5D-1's real, non-optional job, not a decision this audit can approve past.

**Cross-cutting architectural gap discovered (not caused by P5D, pre-existing since before
P5C):** `TenantMembershipService` owns TWO of its own direct RoleBinding mutations that bypass
`RoleGovernanceService` entirely -- `_ensure_default_role_bindings` (called from
`_accept_membership`) calls `role_binding_repo.add(RoleBinding.create(...))` directly, and
`remove_member` calls `role_binding_repo.revoke_active_for_principal_tenant(...)`, a raw bulk
SQL `UPDATE` -- neither ever goes through `RoleGovernanceService.assign_role`/
`revoke_role_binding`, so neither can currently produce a `RoleBindingAssigned`/
`RoleBindingRevoked` event even though each is a genuine RoleBinding mutation. This predates and
was not caught by any P5C audit (which only traced the Access/RBAC-facade paths). P5D-1/P5D-2
must explicitly decide whether to route these through the canonical RoleGovernance path (letting
membership-driven RoleBinding changes participate in the typed RoleBinding event stream) or
document them as a permanently-separate, event-less persistence-level cascade -- **not**
resolved by bulk-generating events from the cascade rows without semantic evidence (item 18's
explicit prohibition; heeded here, not violated).

**Current-user membership removal: NOT a security blocker.** `_require_manageable_target`
explicitly forbids `target.id == actor.user_id` for every admin-initiated mutation (invite,
suspend, reactivate, remove) -- `TENANT_MEMBERSHIP_SELF_LOCKOUT`. It is structurally impossible,
via any code path, for an actor to change their own membership through these commands (only
`accept_invitation`/`accept_invitation_for_tenant`, both self-service and both `active`-going
transitions, ever act on the CURRENT principal). In this desktop architecture (one process, one
live `UserSessionContext`/principal per user, no server pushing state across processes), the
"another live session for the same user" scenario the prompt worried about cannot arise within
a single process, and cross-process propagation (an admin on one machine revoking a user active
on a different machine) is an inherent, pre-existing characteristic of this desktop app
unrelated to eventing -- already equally true for every other security-sensitive mutation
(password changes, RoleBinding changes) and not something P5D introduces or must solve.
`suspend_member`/`remove_member` DO correctly revoke the target's persisted `AuthSession` rows
(`_revoke_affected_sessions`), so a NEW action from that user's own process (after their session
is revoked) fails closed via the already-established `AuthSession.revoked_at` check --
consistent with P5C-1's own established fail-closed precedent, not a new mechanism.

**Activated vs. Reactivated -- evidence-based decision, correcting the original proposal:**
the domain model itself answers this. The "removed member comes back" path
(`remove()` -> `reinvite()` -> `accept_invitation()`) terminates in the EXACT SAME method
(`accept_invitation()`, invited -> active) as first-time activation -- the model draws no
distinction between "never was a member" and "was removed, now re-invited and accepted." Both
are the SAME business fact: an invitation was accepted. `reactivate()` (suspended -> active), by
contrast, IS a genuinely distinct method with its own precondition (must be suspended), its own
administrator-invoked command (`reactivate_member`, not self-service), and its own audit action
(`"tenant.membership.reactivated"`, distinct from `"tenant.membership.invitation_accepted"`).
**Decision: `TenantMembershipActivated`** covers `accept_invitation()`/
`accept_invitation_for_tenant()` regardless of whether the membership is brand new or was
previously removed-then-reinvited (Option A's INSERT-vs-UPDATE framing was the wrong axis;
method identity is the right one). **`TenantMembershipReactivated`** covers `reactivate_member()`
only. Direct `create()` (registration-time, no invitation -- `AuthService.register_user` with a
`tenant_id`) is bootstrap materialization, not a business activation -- mirrors Organization/
Module's own provisioning-is-not-a-licensing-fact precedent; no event for it.

**Removed vs. Deactivated -- and a genuine gap in the original 3-event proposal:**
`remove()` (a tombstone requiring re-invitation to return) and `suspend()` (a temporary,
directly-reversible-via-`reactivate()` state) are two DIFFERENT, already-distinctly-named,
already-distinctly-audited business facts, and the service's own vocabulary
(`"tenant.membership.removed"` vs. `"tenant.membership.suspended"`) already uses "Removed"
correctly for `remove()`. But **the original three-event proposal has no event at all for
`suspend_member`'s own transition** -- `TenantMembershipSuspended` is a real, missing fourth
event name, not an oversight to paper over with `Removed`. Recommended final vocabulary is FOUR
events, not three: `TenantMembershipActivated`, `TenantMembershipSuspended`,
`TenantMembershipReactivated`, `TenantMembershipRemoved`. Invitation issuance/revocation
(`issue_invitation`/`revoke_invitation`, both on `invited`, never yet a granted membership) are
real, distinct facts too but lower priority -- a secondary decision for P5D-2, not blocking.

**No-op semantics (from the aggregate's own transition guards, already enforced):**
`accept_invitation()` raises `USER_TENANT_MEMBERSHIP_ACCEPT_INVALID_TRANSITION` if not
`invited`; `suspend()` raises `..._SUSPEND_INVALID_TRANSITION` if not `active`; `reactivate()`
raises `..._REACTIVATE_INVALID_TRANSITION` if not `suspended`; `remove()` raises
`..._REMOVE_INVALID_TRANSITION` if not `active`/`suspended`. Every "invalid state for this
transition" case is already a hard validation error, not a silent no-op -- there is no existing
"idempotent success" case to preserve; a future P5D-2 event only needs the ordinary
"exception raised -> zero event" rule already established for every other P5 capability.

**Legacy signal inventory:** no dedicated membership signal exists -- `auth_changed` is the ONLY
legacy signal touching tenant membership (`_accept_membership`/`suspend_member`/
`reactivate_member`/`remove_member` each emit it; `issue_invitation`/`revoke_invitation` emit
nothing at all today). Two real consumers, BOTH already inventoried in P5C-3
(`access_workspace_controller.py`'s `security_users` list, Admin Console's user catalog) --
and BOTH have a genuine, newly-confirmed dependency on membership status specifically:
`AuthService.list_users()`'s tenant branch calls `UserRepository.list_for_tenant(tenant_id)`,
which filters `UserTenantORM.status == MEMBERSHIP_STATUS_ACTIVE` -- a suspended or removed
member genuinely disappears from both lists. This is Category A (real dependency), not the
Category C incidental over-refresh P5C-3 found for the OTHER `auth_changed` producers relative
to those same two consumers.

**UI consumer trace -- there is currently no admin membership-management UI at all.**
`PlatformTenantDesktopApi` (the only desktop-API surface touching `TenantMembershipService`)
exposes exactly `list_pending_invitations`/`accept_invitation` (self-service only).
`issue_invitation`/`revoke_invitation`/`suspend_member`/`reactivate_member`/`remove_member` have
**zero callers anywhere outside `TenantMembershipService` itself and tests** -- no desktop API,
no controller, no QML. A future P5D-3 Qt cutover has no existing admin-side consumer to migrate
for those five commands; only the two `auth_changed`-driven list refreshes (Category A, above)
would need a ViewInvalidation-based replacement, symmetrical to P5C-3's own `scopeGrants`
migration but smaller in surface area.

**ViewInvalidation candidates (documented, not implemented):** `tenant_memberships` (a future
membership-administration list, once one exists) and, per the confirmed Category A dependency
above, the SAME `security_users`/user-catalog read models P5C-3 already serves for RoleBinding
-- membership status changes are a second, independent reason those two lists go stale, not
covered by `role_binding_assignments`. Both would be `TenantScope(tenant_id)` -- never
`organization_id`, confirmed nothing in the membership model or its mutation commands derives
from or depends on the ambient active organization (verified: `_require_tenant_administrator`
resolves `tenant_id` via `tenant_context_service.require_active_tenant_id()` only, never touches
organization context at all). An organization switch inside the same tenant must not, and
structurally cannot, affect a future membership ViewInvalidation subscription.

**Recommended subphases:** **P5D-1** (mandatory, not optional) -- converge
`TenantMembershipService` onto a canonical `TenantMembershipUnitOfWork`; resolve the
RoleGovernance-bypass question for the default-role-grant-on-accept and the bulk-revoke-on-remove
cascades; decide the `deactivate()` dead-code question. **P5D-2** -- implement
`TenantMembershipActivated`/`TenantMembershipSuspended`/`TenantMembershipReactivated`/
`TenantMembershipRemoved` (plus, if approved, invitation issuance/revocation) via
`uow.record_event(...)` (service-controlled; `UserTenantMembership` is a real aggregate with
genuine transition methods, but does not implement `RecordsDomainEvents`, and forcing that
protocol onto it is not required to record correctly -- P5C's own established application-
authored pattern applies unchanged). **P5D-3** -- ViewInvalidation + the two existing
`auth_changed` consumers' membership-dependent portions migrated; no Qt adapter/consumer exists
yet for the admin mutation commands themselves, so this phase is narrower than P5C-3.

**No code changes made in this audit** (investigation/design only, per instruction) -- no
TenantMembership DomainEvents, no ViewInvalidation, no Qt migration, no legacy signal removal,
no `deactivate()` decision executed.

### P5D-1 — Tenant Membership Transaction Convergence (implemented)

**Status:** implemented, reviewed. `TenantMembershipService`'s six real mutation commands
(`issue_invitation`, `accept_invitation`/`accept_invitation_for_tenant` via the shared
`_accept_membership`, `revoke_invitation`, `suspend_member`, `reactivate_member`,
`remove_member`) cut over from the shared process-lifetime `Session` and inline
`commit()`/`rollback()` onto a canonical `TenantMembershipUnitOfWork` -- one fresh `Session` per
call, matching the established `OrganizationUnitOfWork`/`ModuleEntitlementUnitOfWork`/
`RoleGovernanceUnitOfWork` pattern. No `TenantMembership*` DomainEvents (P5D-2's job), no
membership ViewInvalidation, no membership Qt adapter, no Approval events.

**Dead API removed:** `UserTenantMembershipRepository.deactivate()` -- confirmed zero production
callers (P5D-SEM), bypassed authorization/audit/session-revocation entirely. Deleted from the
contract and the SqlAlchemy implementation; its two test-only call sites now use the equivalent
direct `get()` + `update(membership.suspend())` sequence.

**The transaction-agnostic mutation participant (new pattern, first reuse across two transaction
owners in this whole ADR-005 migration):** P5D-SEM found two RoleGovernance-bypassing RoleBinding
mutations inside `TenantMembershipService` -- `_ensure_default_role_bindings` (on accept)
directly called `role_binding_repo.add(RoleBinding.create(...))`, and `remove_member` called a
raw bulk-SQL `revoke_active_for_principal_tenant` UPDATE. Both are real business facts and must
emit the SAME P5C `RoleBindingAssigned`/`RoleBindingRevoked` events `RoleGovernanceService`
emits -- but `TenantMembershipUnitOfWork` calling `RoleGovernanceService.assign_role(...)` would
nest two independent transactions, and duplicating the identity/no-op/audit/event mechanics would
diverge from the canonical behavior over time. Resolved by extracting `RoleGovernanceService`'s
own binding mutation mechanics into a new shared, transaction-agnostic module,
`role_binding_mutation_participant.py` (`create_role_binding_using`/`revoke_role_binding_using`/
`resolve_domain_scope_for_binding`/`resolved_scope_to_domain_scope`/
`record_role_binding_audit_entry`/`recover_from_concurrent_assignment`) -- pure functions that
take the calling UoW's own `role_bindings`/`audit` repos, `clock`, and `record_event` callback as
parameters, and never open a Session, commit, or roll back. `RoleGovernanceService.assign_role`/
`revoke_role_binding` were refactored onto this SAME module (no behavior change; 71+68 tests
re-verified passing before `TenantMembershipService` itself was touched), then
`TenantMembershipService` was wired onto it too. Both callers own their own transaction and their
own repos; the participant module owns neither.

**Explicit policy distinction (documented, not just implemented):** the default-role grant on
self-service acceptance and the cascade revoke on removal are system/membership-lifecycle
operations, not an admin interactively delegating a role to someone else -- so neither goes
through `RoleGovernanceService.assign_role`/`revoke_role_binding`'s delegation-namespace or
permission-snapshot SoD checks. They reuse ONLY the canonical identity/no-op/revocation/audit/
event mechanics, never the interactive-admin authorization policy layered on top of it in
`RoleGovernanceService` itself.

**Removal cascade — a real (minor, correct) semantic tightening, not a behavior-preserving
port:** the old `revoke_active_for_principal_tenant` bulk UPDATE matched every non-revoked
binding row for the tenant regardless of expiry, so an already-expired-but-not-yet-revoked row
would silently get `revoked_at` stamped with no audit entry and no event. The new cascade
iterates `role_bindings.list_active_for_principal(target_id, tenant_id=tenant_id)` (excludes
already-expired rows) and calls `revoke_role_binding_using` once per genuinely active binding --
one real `RoleBindingRevoked` per real transition, never a bulk-generated event for a row that
had already lapsed on its own.

**Verified (not assumed), per explicit instruction: `suspend_member`/`reactivate_member` never
touch RoleBinding rows.** Read directly from the pre-refactor source before converting: both
commands only transition the membership's own status and (`suspend_member` only) revoke the
target's affected `AuthSession` rows via `_revoke_affected_sessions`. Neither calls any
RoleBinding repository method, so neither emits (and neither should ever emit) a
`RoleBindingAssigned`/`RoleBindingRevoked` event -- confirmed by a dedicated test asserting zero
observable events across a suspend+reactivate cycle, not inferred from the absence of a call.

**Correcting prior documentation (per explicit instruction): P5C did not have complete
RoleBinding producer coverage before this phase.** The P5C-1/P5C-2/P5C-3 passes converged and
instrumented `RoleGovernanceService`'s own two mutation methods, but did not audit
`TenantMembershipService`, which held its own independent, unaudited RoleBinding-mutating code
path (the two bypasses above) the whole time. P5D-SEM discovered this gap and P5D-1 closed it --
every RoleBinding mutation in the codebase now goes through the one canonical mechanics module,
and every genuine RoleBinding business fact (however triggered) now emits the P5C event
vocabulary consistently.

**Composition wiring:** `platform_registry.py` builds a `TenantMembershipUnitOfWorkFactory`
(fresh `sessionmaker` bound to the same engine, the same `platform_transactional_dispatcher`/
`platform_post_commit_bus` every other Platform UoW factory shares) and constructs
`TenantMembershipService` with `uow_factory`, `clock=SystemClock()`, and the SAME
`organization_owner_resolvers` dict already built for `RoleGovernanceService` -- the removal
cascade can revoke resource-scoped bindings too, so it needs the same organization-ownership
derivation the default tenant-wide grant does not.

**Test coverage:** `test_tenant_membership_unit_of_work_cutover.py` (fresh-session-per-command,
shared-UoW-session repository/audit, no global-Session touch, exactly-one
`RoleBindingAssigned`/`RoleBindingRevoked` per real acceptance/removal, audit-failure and
commit-failure rollback with zero observable event, suspend+reactivate emitting zero RoleBinding
events, last-tenant-admin guard atomicity, architecture guards for no inline commit/rollback, no
direct RoleBinding repository bypass, no nested `RoleGovernanceService` call, no P5D-2 event
vocabulary, and the participant module owning no transaction) plus the existing
`test_tenant_membership_orchestration.py` (updated to read persisted state via a fresh repository
on the shared test session, mirroring the established post-cutover pattern from
`test_role_governance_unit_of_work_cutover.py`, since the service no longer exposes
per-repository instance attributes).

**Regression:** full Platform suite (`src/tests/platform`) and the architecture suite both run at
the same failure identities/counts as the established baseline (15 failed/12 errors in Platform,
none touching security/tenancy/role-governance; 13 pre-existing failures/142 passed in
architecture) -- passing-test count increased by exactly the 15 new P5D-1 tests, zero
regressions.

**Explicit non-goals:** `TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed` events
(P5D-2), membership ViewInvalidation and Qt adapter (P5D-3), Approval events.

### P5D-2 — Tenant Membership Typed DomainEvents (implemented)

**Status:** implemented, reviewed. Four events added --
`TenantMembershipActivated`/`Suspended`/`Reactivated`/`Removed`, in
`src/core/platform/domain/tenant/tenancy/events.py`. No ViewInvalidation, no Qt migration, no
`auth_changed` bridging/removal, no P5C RoleBinding event vocabulary change, no Approval events.

**Transition -> event mapping (exactly one non-trivial aggregate transition method per event,
never derived from destination status):**

| Command | Aggregate method | Event recorded | RoleBinding events in the same transaction |
|---|---|---|---|
| `issue_invitation` (fresh) | `UserTenantMembership.invite()` | none | none |
| `issue_invitation` (reinvite) | `UserTenantMembership.reinvite()` | none | none |
| `accept_invitation` / `accept_invitation_for_tenant` | `UserTenantMembership.accept_invitation()` | `TenantMembershipActivated` | `RoleBindingAssigned` per default binding actually created (recorded first) |
| `revoke_invitation` | `UserTenantMembership.revoke_invitation()` | **none** (see decision below) | none |
| `suspend_member` | `UserTenantMembership.suspend()` | `TenantMembershipSuspended` | none (verified, P5D-1) |
| `reactivate_member` | `UserTenantMembership.reactivate()` | `TenantMembershipReactivated` | none (verified, P5D-1) |
| `remove_member` | `UserTenantMembership.remove()` | `TenantMembershipRemoved` | `RoleBindingRevoked` per genuinely active binding revoked (recorded first) |

Because `accept_invitation()`/`reactivate()` each has exactly one legal source status (`invited`
and `suspended` respectively, enforced by the aggregate's own guard), the membership's prior
history never changes which event fires: `removed -> reinvite -> invited -> accept` still
produces exactly `TenantMembershipActivated` at the final transition, never `Reactivated`.

**`revoke_invitation` decision (documented, not inferred from `status == "removed"`):
invitation revocation is a distinct invitation-lifecycle fact, not a membership-removal fact, and
emits NO membership event in P5D-2.** Evidence: (1) an `invited` principal was never an active
tenant member -- every membership-facing guard (self-lockout, `is_active_member`, the last-admin
count) gates on ACTIVE status, never INVITED; (2) the audit vocabulary already distinguishes the
two facts (`tenant.membership.invitation_revoked` vs `tenant.membership.removed`); (3) the
aggregate method itself sets a field `remove()` never touches (`revoked_at`), and
`revoke_invitation` never calls `_revoke_affected_sessions` or touches any RoleBinding row --
there is nothing to invalidate, since acceptance (the only path that ever creates a
session/binding footprint) never happened. A separate `TenantInvitationRevoked` fact was
considered and deliberately NOT added -- no concrete consumer needs it yet.

**Event shape:** `membership_id`, `tenant_id`, `user_id`, `occurred_at` -- frozen, `slots=True`,
keyword-only, mirroring `RoleBindingAssigned`/`RoleBindingRevoked`'s own dataclass shape. No
`organization_id` (Tenant Membership is tenant-scoped only; an organization switch never affects
a membership event's identity -- proven directly). No `actor_id`, role IDs, permission snapshot,
audit action, correlation/causation/command id, or schema version -- `DomainEventContext` stays
the separate dispatch-metadata carrier, exactly as ADR-005 §5 already established for P5C.

**Recording ownership:** exactly one responsibility, held by `TenantMembershipService` via
`uow.record_event(...)` at each command's canonical transition boundary, atomically with that
same UoW's commit. `UserTenantMembership` was NOT changed to implement `RecordsDomainEvents` --
it stays a plain aggregate owning only its own state invariants, per P5D-SEM's original decision.

**Event ordering (P5D-2A correction, 2026-08-26): event recording follows business-transition
order, not merely `record_event()` call placement near `commit()`.** The initial P5D-2 pass
recorded the membership event LAST in each composite command (after the RoleBinding
mutation participant call), which happened to match where the code was convenient to write but
did NOT match the actual order the two business facts occur in: `membership.accept_invitation()`
and `membership.remove()` are the FIRST transition in their respective commands --
`_ensure_default_role_bindings`/the cascade revoke loop are consequences that run strictly AFTER
them in the source. P5D-2A moved `uow.record_event(TenantMembershipActivated/Removed(...))` to
immediately after the membership's own aggregate transition (right after
`uow.memberships.update(...)`), before the RoleBinding mutation call, so the committed order now
is:

- Acceptance: `TenantMembershipActivated`, then `RoleBindingAssigned` per default binding created.
- Removal: `TenantMembershipRemoved`, then `RoleBindingRevoked` per genuinely active binding revoked.

This carries no rollback-safety cost: the canonical UoW never calls `self._session.commit()` or
publishes anything until `uow.commit()`'s `_drain_and_dispatch()` completes, so an early
`record_event()` call is observationally identical to a late one whenever the surrounding
transaction later fails (audit write, the RoleBinding participant, a transactional handler, or
`commit()` itself) -- re-verified by the full failure-mode test suite after the reorder, with
identical results.

**Clock:** every `occurred_at` comes from `self._clock.now()` (the same `Clock` P5D-1 wired in) --
no direct `datetime.now()`/`datetime.utcnow()` call for an event timestamp. `reactivate_member`
was additionally changed to thread its own `now` into `membership.reactivate(reactivated_at=now)`
(previously relying on the aggregate's own internal default), so the event's `occurred_at` and
the aggregate's own `updated_at` never diverge by a stray microsecond within one transaction.

**Failure/isolation guarantees (all proven by dedicated tests):** an audit-write failure or a
`uow.commit()` failure leaves zero observable membership (and zero observable RoleBinding) event
-- the whole transaction, including any already-called `uow.record_event(...)`, rolls back
together. A FAIL_FAST pre-commit (`TransactionalEventDispatcher`) handler failure rolls back the
same way. A post-commit (`PostCommitEventPublisher`) handler failure is isolated
(ISOLATE_AND_CONTINUE, the existing shared bus semantics, unchanged) -- the DB transaction stays
committed and a sibling subscriber still receives the event. An invalid aggregate transition
(e.g. `suspend_member` on a still-`invited` membership) records nothing at all -- command
invocation is never treated as a business transition.

**Test coverage:** `test_tenant_membership_typed_events.py` (22 tests) -- activation event +
ordering, `accept_invitation_for_tenant` parity, issue/reinvite eventlessness, the
reinvite-then-accept never-Reactivated proof, suspend+reactivate zero-RoleBinding-event proof,
removal event + ordering (both from active and from suspended), `revoke_invitation`'s explicit
no-event proof, invalid-transition no-event proof, audit/commit/transactional-handler-failure
rollback, post-commit handler isolation, tenant-scope-only (survives an organization switch) and
cross-tenant-denial proofs, `DomainEventContext` separation, and five architecture guards (no
forbidden imports in the events module, exact approved field set on all four events, no
forbidden fields, no disapproved event names, `issue_invitation`/`revoke_invitation` source never
records a membership event). `test_tenant_membership_unit_of_work_cutover.py`'s own P5D-1
"no P5D-2 vocabulary" guard was renamed to `test_tenant_membership_service_adds_no_p5d3_ui_vocabulary`
and narrowed to the ViewInvalidation/Qt check that is still true, since the four event names it
previously forbade are now legitimate P5D-2 vocabulary.

**Regression:** full Platform suite and architecture suite both run at the same failure
identities/counts as the established baseline (15 failed/12 errors in Platform, 13 pre-existing
failures/142 passed in architecture) -- passing-test count increased by exactly the 22 new P5D-2
tests, zero regressions. `git rev-parse HEAD` was identical before and after both long suite runs.

**Explicit non-goals:** membership ViewInvalidation and Qt adapter (P5D-3), `auth_changed`
removal or a new `TenantMembershipActivated -> auth_changed` bridge, any P5C RoleBinding event
vocabulary change, Approval events.

### P5D-3 — Tenant Membership ViewInvalidation + Direct UI/Consumer Cutover (implemented; P5D now complete)

**Status:** implemented, reviewed. All four membership events now reach their real UI consumers
through `TenantMembership* -> ViewInvalidationHint -> TenantMembershipViewInvalidationAdapter`,
never the legacy `auth_changed` signal -- which the five membership-lifecycle emit sites
(`accept_invitation`, `accept_invitation_for_tenant`, `suspend_member`, `reactivate_member`,
`remove_member`) no longer call at all.

**`auth_changed` re-audit (full repository inventory, post-P5C-3):** 27 `.emit(...)` call sites
existed before this phase. Classified:

- **Category A (Tenant Membership lifecycle) -- removed, 5 sites:** all five in
  `tenant_membership_service.py`, listed above.
- **Category B (legitimate non-membership security facts) -- retained, 22 sites, unchanged:**
  `role_governance_service.py` (2 -- P5C's own retained legacy duplication, unchanged by this
  phase), `tenant_role_administration_service.py` (2, custom-role policy create/retire),
  `role_policy_reconciliation_service.py` (1, permission-set reconciliation),
  `session_service.py` (2, login/session lifecycle), `user_admin_service.py` (3, platform-level
  `UserAccount.is_active` toggle / profile update -- a DIFFERENT flag from
  `UserTenantMembership.status`), `registration_service.py` (1, new-account creation),
  `bootstrap_service.py` (1, initial platform-admin bootstrap), `password_service.py` (3),
  `mfa_service.py` (3), `federated_identity_service.py` (1), `authentication_transactions.py`
  (2). None of these touch `UserTenantMembership` -- confirmed by reading each site, not
  inferred from filenames alone.
- **Category C (obsolete/coarse legacy signal) -- none found.** No producer was purely
  vestigial; every remaining site serves a real, currently-consumed, non-membership fact.

**`auth_changed` deletion verdict: NOT deleted -- 22 legitimate non-membership producers remain,
each with a real consumer.** Exactly two production subscribers exist in the whole codebase
(confirmed by grep, not assumed): `AccessWorkspaceController._on_auth_changed` and the Admin
Console's coarse composite `domain_event_binder.py`. Both are RETAINED for the 22 Category-B
producers, and BOTH gained a second, independent wiring to the new membership adapter for the
membership-driven case -- never a bridge from the new event to the old signal, two genuinely
separate presentation-invalidation paths for two genuinely separate sets of business facts.

**Real membership-status-dependent consumers -- re-traced from current source, not assumed from
the P5D-SEM prior finding (which named exactly two; this pass found a third):**

1. `AccessWorkspaceController._refresh_security_users()` -> `PlatformAccessWorkspacePresenter.
   build_security_users()` -> `PlatformUserDesktopApi.list_users()` -> `AuthService.list_users()`
   -> (tenant branch) `UserRepository.list_for_tenant(tenant_id)`, filtered on
   `UserTenantORM.status == ACTIVE`.
2. `PlatformAdminWorkspaceController`'s user catalog -> `PlatformUserCatalogPresenter.
   build_catalog()` -> the SAME `list_users()` call path as (1).
3. **Newly confirmed this phase:** `PlatformAdminWorkspacePresenter.build_overview()`'s
   `user_summary` metric -> `AuthService.get_user_rollup_summary()` -> (tenant branch)
   `SqlAlchemyPlatformOverviewRollupReader.get_user_summary(tenant_id=...)`, which joins
   `UserTenantORM` and filters `status == ACTIVE` directly in SQL -- same membership dependency,
   independently verified at the query level, not by resemblance to (1)/(2).

All three ultimately read the SAME underlying membership-status-filtered fact -- per item 5,
ONE invalidation target (`tenant_memberships`) covers all three; they are not over-split into
per-consumer targets.

**Invalidation target and event mapping:** `tenant_memberships`
(`TENANT_MEMBERSHIP_CATEGORY = "tenant_membership"`, `TENANT_MEMBERSHIPS_SCOPE_CODE =
"tenant_memberships"`), `src/core/platform/application/tenant/tenancy/event_handlers/
view_invalidation.py`. One handler, reused for all four event types (mirrors
`build_role_binding_view_invalidation_handler`'s own one-handler-four-call-sites shape). Scope is
always `TenantScope(event.tenant_id)` -- never `OrganizationScope`/`AllTenants()`: membership has
no organization dimension (P5D-1/P5D-2 already confirmed no mutation command derives from or
depends on the active organization).

**Adapter:** `TenantMembershipViewInvalidationAdapter`
(`src/ui_qml/platform/adapters/tenant_membership_view_invalidation_adapter.py`), mirroring
`OrganizationViewInvalidationAdapter`'s shape exactly (tenant-only, `set_active_tenant(...)`,
single `membershipDataStale` Signal, `dispose()`) rather than
`RoleBindingViewInvalidationAdapter`/`ModuleEntitlementViewInvalidationAdapter`'s
tenant-plus-organization shape -- there is no organization axis to track. Re-scoped ONLY on a
real tenant switch (`context.py`'s `_on_tenant_switched`); deliberately NOT re-scoped on
`refreshCurrentPermissions()` (the organization-switch hook that DOES re-scope the RoleBinding/
Module adapters) -- proven directly: an organization switch within the same tenant leaves the
adapter's live subscription object identical (`is` comparison), and a subsequent membership
event for that tenant still fires exactly once.

**Controller wiring (narrow, mirroring `refresh_organizations()`'s existing precedent, never
the coarse `do_refresh()`/`refresh()` cascade):**

- `PlatformAdminAccessWorkspaceController.refresh_security_users()` (new) -- narrows to
  `_refresh_security_users()` + `_refresh_empty_state()`, exactly like the existing
  `refresh_role_bindings()`.
- `PlatformAdminWorkspaceController.refresh_users()` (new) -- delegates to
  `self._user_controller.refresh()` AND `refresh_overview(self)` (both genuinely
  membership-status-dependent per consumers (2) and (3) above), never the other 7 entity
  sub-controllers.

`context.py` connects `membershipDataStale` to both narrow methods -- the same one-signal,
multiple-narrow-consumer pattern already used for `organizationCollectionStale`.

**Invitation lifecycle (`issue_invitation`/`reinvite`/`revoke_invitation`) -- no direct
invalidation added, evidence-based:** traced every QML/presenter reference to
`list_pending_invitations`/`accept_invitation`/`PlatformTenantDesktopApi` -- **zero** current UI
consumers exist (`TenantSwitcherPresenter` holds a reference to the same desktop API only for
unrelated tenant-list/switch methods). Per item 17/18's option A ("current UI does not consume
that data: no invalidation needed"), none of the three eventless commands got a direct
`ViewInvalidationChannel.notify(...)` call. No `TenantInvitationRevoked`/`TenantMembershipInvited`
event was added either, per explicit instruction.

**RoleBinding invalidation stays separate, proven directly:** a `remove_member` call commits
`TenantMembershipRemoved` + one `RoleBindingRevoked` (the default binding) in the SAME
transaction -- `refresh_users()` (membership) and `refresh_role_bindings()` (RoleBinding) each
fire exactly once, for their own reason, never merged into one generic invalidation and never
duplicated.

**No coarse over-refresh reproduced:** a pure membership transition (suspend, in isolation) was
proven to touch none of the admin console's other seven entity sub-controllers
(organization/calendar/site/department/employee/party/document) -- the OLD coarse `auth_changed`
composite binder's over-refresh is not reproduced by the new narrow wiring. (The coarse binder
itself remains, unchanged, for the 22 retained Category-B producers -- e.g. registering a new
user or authenticating legitimately still cascades the full admin-console reload today, exactly
as before this phase; that pre-existing behavior is untouched, not expanded.)

**AuthSession revocation stays a persistence/security concern, confirmed unchanged:**
`suspend_member`/`remove_member`'s `_revoke_affected_sessions` call remains inside the canonical
transaction, never moved behind ViewInvalidation or the Qt adapter.

**Test coverage:** `test_tenant_membership_view_invalidation_qt_cutover.py` (16 tests) -- mapper
unit tests (all four event types map to the identical tenant-scoped hint), architecture guards
(mapper has no Qt/SQLAlchemy import, adapter has no DomainEvent/postcommit-bus/organization-axis
dependency, controllers import no event infrastructure), tenant-scope-only isolation, tenant
switch lifecycle (dispose-then-resubscribe, no leak, proven both behaviorally and via the
channel's own subscription count), a real end-to-end tenant switch through
`TenantSwitcherController.switchToTenant()`, the organization-switch non-effect proof, two
genuine end-to-end content proofs (activation/removal actually changing what a tenant-scoped
caller's `list_users()` returns -- using a real registered `tenant_admin` actor, since the
default test principal is a platform operator and bypasses the membership filter entirely),
invalid-transition/audit-failure/commit-failure/transactional-handler-failure zero-refresh
proofs, post-commit handler isolation, the RoleBinding-stays-separate proof, and the
no-coarse-over-refresh proof.

**Regression:** full Platform suite and architecture suite both run at the same failure
identities/counts as the established baseline (15 failed/12 errors in Platform, 13 pre-existing
failures/142 passed in architecture) -- passing-test count increased by exactly the new P5D-3
tests, zero regressions. `git rev-parse HEAD` was identical before and after the long suite runs.
The pre-existing `test_secondary_workspace_lazy_loading.py`/`test_qml_domain_event_bridges_pm.py`
tests (which synthetically emit `auth_changed` directly to test the UNCHANGED
`_on_auth_changed`/coarse-binder wiring itself) were re-verified passing, confirming that wiring
is untouched.

**Remaining Tenant Membership debt (explicit, not resolved by P5D-3):** no admin
membership-management UI exists yet (unchanged from P5D-SEM's finding) -- if one is ever built,
it is the first real consumer of `issue_invitation`/`revoke_invitation`'s own data and would need
its own direct-invalidation or event decision at that time, not before. The Admin Console's own
composite `auth_changed` binder (`domain_event_binder.py`) remains coarse for its 22 retained
Category-B producers -- explicitly out of P5D's scope, deferred to R2's own controller-hierarchy
work per that file's existing docstring.

**Explicit non-goals:** Approval events, any P5C RoleBinding event/ViewInvalidation change, any
change to the four membership events' fields or semantics.

## P5 Closeout — Residual `auth_changed` Audit and RoleBinding Legacy Cleanup (implemented)

**Status:** implemented, reviewed. The P5D-3 final report flagged one residual defect:
`RoleGovernanceService.assign_role`/`revoke_role_binding` still emitted the legacy `auth_changed`
signal even though P5C-2/P5C-3 had already given RoleBinding its own typed
event -> ViewInvalidation -> narrow-consumer path. This closeout removed those two emit sites,
re-verified no compatibility bridge was needed, and produced the final auth_changed inventory
below. No new DomainEvent, no new ViewInvalidation target, no membership-event change.

**Full production `auth_changed` re-inventory (before this pass, 22 producers, re-counted from
source, not assumed from the prior report):**

| File | Emits | Business fact |
|---|---|---|
| `role_governance_service.py` | 2 | `assign_role`/`revoke_role_binding` -- **removed this pass** |
| `tenant_role_administration_service.py` | 2 | custom-role definition create/retire |
| `role_policy_reconciliation_service.py` | 1 | permission-set reconciliation for affected users |
| `session_service.py` | 2 | session/login lifecycle |
| `user_admin_service.py` | 3 | `UserAccount.is_active` toggle / profile update -- a platform-level flag, distinct from `UserTenantMembership.status` |
| `registration_service.py` | 1 | new-account creation |
| `bootstrap_service.py` | 1 | initial platform-admin bootstrap |
| `password_service.py` | 3 | password change/reset |
| `mfa_service.py` | 3 | MFA enroll/disable |
| `federated_identity_service.py` | 1 | federated identity link/update |
| `authentication_transactions.py` | 2 | login/lockout transactions |

Exactly 2 production consumers exist repository-wide (confirmed by grep, not assumed):
`AccessWorkspaceController._on_auth_changed` and the Admin Console's coarse composite
`domain_event_binder.py`. Neither was touched -- both remain, for the 22 (now 20) legitimate
non-RoleBinding producers.

**RoleGovernanceService producer analysis:** both were pure legacy duplicates of
`RoleBindingAssigned`/`RoleBindingRevoked`'s own already-implemented ViewInvalidation path, with
no independent responsibility. Verified directly, not assumed: current-principal refresh
(`refresh_current_session_if_user`) is called explicitly by BOTH calling facades
(`role_assignment_service.assign_role`/`revoke_role`, `AccessControlService.assign_scope_grant`/
`remove_scope_grant`), as a separate, unconditional step after the `RoleGovernanceService` call
returns -- never wired through `auth_changed` (confirmed: zero `.connect()`/`.subscribe()` calls
to `auth_changed` exist anywhere outside the two UI controllers named above). `access_changed`
was already retired from `AccessControlService` in P5C-3. Neither facade has its own separate
`auth_changed.emit(...)` call, so removing the two sites inside `RoleGovernanceService` leaves
**zero** `auth_changed` emission from any RoleBinding mutation, through any path.

**Removed, no bridge:** the two `domain_events.auth_changed.emit(...)` calls in `assign_role`/
`revoke_role_binding`, and the now-unused `domain_events` import. No
`RoleBindingAssigned -> auth_changed` compatibility shim was added — pre-release direct
convergence, per the same policy P5C-3/P5D-3 already established.

**Custom Role Definition, session/authentication, user-account, and password/identity
producers:** deliberately NOT touched. None represent a RoleBinding fact — `TenantRole
AdministrationService`'s two producers are custom role-definition lifecycle (a distinct,
not-yet-modernized capability); the rest are session/registration/bootstrap/credential facts
with no typed-event/ViewInvalidation equivalent yet. They remain legacy until their own
capability is modernized — out of this closeout's scope by explicit instruction.

**Double-refresh proof (real end-to-end):** a real `assign_role`/`revoke_role_binding` call
through the normal application path now produces exactly one narrow `refresh_role_bindings()`
call and zero `_refresh_after_security_change()` (the `auth_changed`-driven reaction) calls --
proven for both assignment and revocation. The admin console's coarse composite binder is also
proven unreached by an isolated RoleBinding mutation (it never had a narrow RoleBinding reaction
to begin with; P5C-3 wired that to the access workspace only).

**Membership-removal composition re-verified:** `TenantMembershipRemoved` +
`RoleBindingRevoked` (the default grant) still produce exactly one membership refresh and
exactly one RoleBinding refresh, with zero coarse `auth_changed`-driven refresh from either fact
-- unchanged in outcome from P5D-3, re-proven after this pass's edits.

**Current-user / other-user security regression:** both re-verified directly. Self-assignment
still refreshes the caller's own principal (and still fails closed if rebuilding it raises) via
the facade's own explicit call, completely unaffected by the signal's removal. An admin mutating
a different user's binding still updates the correct binding, fires the narrow ViewInvalidation
once, and leaves the acting admin's own principal untouched.

**Legacy Signal Ownership Matrix (the boundary for future modernization work):**

| Capability | Typed events | ViewInvalidation | Legacy `auth_changed` |
|---|---|---|---|
| Organization | YES | YES | NO |
| Module Entitlements | YES | YES | NO |
| RoleBinding | YES | YES | NO (removed this pass) |
| Tenant Membership | YES | YES | NO |
| Custom Role Definition | NO | NO | YES |
| Session/Authentication | NO | NO | YES |
| User-account activation/profile | NO | NO | YES |
| Password/credential security | NO | NO | YES |
| MFA | NO | NO | YES |
| Federated identity | NO | NO | YES |
| Registration/bootstrap | NO | NO | YES |

**Test coverage:** `test_p5_closeout_auth_changed_audit.py` (10 tests) -- source-level guards
(neither `RoleGovernanceService` nor `TenantMembershipService` reference `auth_changed`/
`domain_events` at all; exactly the 2 expected production consumers remain), the real
double-refresh proof for both assignment and revocation, the admin-console-coarse-binder
isolation proof, rollback-silence (unaffected by the removal), current-principal
regression, other-user regression, and the membership-removal composition re-proof. Three
pre-existing test files updated to stop asserting the now-removed emission:
`test_role_governance_unit_of_work_cutover.py` (dropped its `auth_changed`
connect/disconnect scaffolding from the commit-failure test since there was nothing left to
observe either way; renamed and corrected its vocabulary guard to assert `emitted_signals ==
set()`), `test_role_binding_events.py` (renamed `test_legacy_auth_changed_still_fires_alongside_
the_new_typed_event` to `test_legacy_auth_changed_no_longer_fires_for_role_binding_mutations`,
asserting `seen_signals == []`).

**Regression:** full Platform suite and architecture suite both run at the same failure
identities/counts as the established baseline (15 failed/12 errors in Platform, 13 pre-existing
failures/142 passed in architecture) -- zero regressions. `git rev-parse HEAD` was identical
before and after the long suite runs.

**Explicit non-goals:** any new DomainEvent, any new ViewInvalidation target, any change to
membership events, Approval work, modernizing Custom Role Definition/session/user-account/
password/MFA/federated-identity/registration capabilities (all remain legitimate `auth_changed`
producers, deliberately untouched).

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

**Fifth pass (2026-08-25, same day) — P4C, then P5A, then the Organization-specific
Qt-cutover correction.** P4B's own report identified a second, real prerequisite gap:
`PlatformRuntimeApplicationService.provision_organization` still composed
`create_organization(commit=False)` + module-entitlement provisioning + `set_active_organization
(commit=False)` on the shared Session -- a second real Organization-creation path with no
canonical UoW. P4C resolved it: a narrow `PlatformProvisioningUnitOfWork`
(`organizations`/`entitlements`/`_enterprise_audit_service`), the `commit: bool` switch removed
entirely from `create_organization`/`set_active_organization` (confirmed the sole real caller),
and their actual business logic extracted into `_create_organization_using`/
`_activate_organization_using` -- shared, transaction-agnostic operations both the standalone
fresh UoW and the provisioning UoW call directly, never a nested UnitOfWork.

P5A then implemented `OrganizationCreated` on top of both now-canonical paths. Before finalizing
the ViewInvalidation targets, an end-to-end trace of both real `organizations_changed` UI
consumers (admin console organization list, settings organization-profiles list) confirmed the
discovery's proposed targets were correct (both consumers read a tenant-wide organization list;
neither reads a distinct "active organization" context from mere creation). A first pass wired a
temporary `OrganizationCreated -> organizations_changed` compatibility handler for those two
consumers; this was explicitly rejected and replaced: since the app is pre-release and the
consumer set is exactly two, both were migrated directly onto `ViewInvalidationChannel` via a new
`OrganizationViewInvalidationAdapter`, pulling forward only the Organization slice of P6 (not a
general P6 migration) rather than shipping a bridge that would be dead code from day one.
`update_organization`/`set_active_organization` keep emitting `organizations_changed` directly,
unchanged -- confirmed still required, not removed. This pass changed real production code (P4C
and P5A implementation) and added tests; no commit was made by the assistant at any point
(self-committed by the user between turns, per this project's established pattern).
