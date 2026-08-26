# Platform Domain Event Implementation Plan

- Status: **implemented, P0-P8 complete** — see the Completion Ledger immediately below for the
  authoritative per-phase status, artifact, deviation, and remaining-debt record. This document's
  original phase-by-phase prose is retained below the ledger as the detailed historical record of
  what each phase actually built (several phases' own implementation diverged from their original
  plan text where current-source evidence contradicted an earlier assumption; each such divergence
  is called out inline in that phase's own "implementation report" subsection, not silently
  smoothed over).
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
business module). **All phases P0-P8 are now implemented** — see the Completion Ledger below for
the authoritative status of each, and each phase's own "implementation report" subsection (where
one exists) for what was actually built versus originally planned.

## Completion Ledger (P8 closeout)

| Phase | Status | Major artifact | Important deviation | Remaining debt |
|---|---|---|---|---|
| P0 | Implemented | Architecture-guardrail/baseline characterization tests | None | — |
| P1 | Implemented | `EventScope`/`ViewInvalidationHint`/`ScopeFilter` contracts, `DomainEvent`/`DomainEventContext`/`RecordsDomainEvents` | None | — |
| P2 | Implemented | `InProcessTransactionalEventDispatcher`, `InProcessPostCommitEventBus`, `InProcessViewInvalidationChannel` | None | — |
| P3 | Implemented | Canonical `UnitOfWork`/`UnitOfWorkFactory` protocol + SQLAlchemy base | None | — |
| P4-PRE | Implemented (Round 8 scope) | 8 approval-backed PM/Inventory services converged onto session-parameterized apply/reject participants | Collapsed from a 4-step adapter-first plan to 2 direct steps (pre-release, no back-compat needed) | — |
| P4 | Implemented | `ApprovalService` on canonical `UnitOfWork`; `commit=False` removed everywhere | 4th caller (`submit_purchase_order`) discovered during implementation, converged alongside the other 3 | — |
| P4B | Implemented | Organization capability transaction convergence | None | — |
| P5A | Implemented | `OrganizationCreated` → ViewInvalidation → `OrganizationViewInvalidationAdapter` | `update_organization`/`set_active_organization` deliberately NOT typed — Organization is PARTIALLY MODERNIZED (§26.4 of ADR-005) | Organization update/set-active still legacy |
| P5B / P5B-3 | Implemented | 5 Module Entitlement `DomainEvent`s, `modules_changed` fully retired | None | — |
| P5C / P5C-3 | Implemented | `RoleBindingAssigned`/`Revoked`, polymorphic scope mapper (Platform/Tenant/Resource), dual-subscription adapter | `PlatformScope()` hint path proven unreachable in practice (governance denies platform-scope assignment before any event fires) — documented, not "fixed" | — |
| P5D / P5D-3 | Implemented | 4 TenantMembership `DomainEvent`s, tenant-only (never org-rescoped) adapter | None | — |
| P5 Closeout | Implemented | Residual `auth_changed` audit; RoleBinding legacy cleanup | None | 7 auth-adjacent capabilities remain, by design (§10 below) |
| Approval-SEM | Implemented (design-only) | Semantic discovery, no code | None | — |
| Approval-P1/P1A | Implemented | `tenant_id`/`organization_id` on `ApprovalRequest`; transaction-agnostic participant; 4 host workflows converged; `commit=False` removed | 4th caller (`submit_purchase_order`) found during P1 itself | — |
| Approval-P2 | Implemented | `ApprovalRequested`/`Approved`/`Rejected` typed events, `Clock`-driven `occurred_at` | None | — |
| Approval-P3 | Implemented | Approval ViewInvalidation, Control workspace + PM Collaboration migrated, `approvals_changed` deleted | PM Dashboard's incidental subscription found and dropped (not migrated) | PM catalog has no QML-wired tenant/org-switch hook (pre-existing, unrelated) |
| P6 | Implemented | `ScopedViewInvalidationSubscription` (composition, mechanics-only), all 5 adapters migrated | Original plan assumed adapter lifecycle lived on `PlatformWorkspaceControllerBase` — audit found it lives at the catalog level instead; all 3 controller bases KEPT unchanged | — |
| P7 | Implemented (narrowed scope, superseded by P7A) | Removed 4 dead Platform-signal bridge entries + `shared_master_changed` | Scope was narrower than "delete the whole bridge" — corrected by P7A | — |
| P7A | Implemented | Entire generic bridge (`_BRIDGE_SPECS`/`_wire_bridges`/`_build_bridge`/`domain_changed`/`DomainChangeEvent`/`_subscribe_domain_change`) deleted; 17 PM/Inventory consumers direct-wired | None | — |
| P7B | Implemented | `costs_changed`/`calendars_changed` deleted (zero producers) | P7's own report had wrongly named 4 different signals as "dead" — corrected by re-auditing from source | — |
| P7C | Implemented | `cost_entries_changed`/`commitments_changed`/`forecasts_changed`/`financial_changes_changed` deleted (zero consumers), producers removed | None | 26→29 signal-count correction (P7C's own "26" was a miscount; the true post-P7C count, verified in P8, is 29) |
| P8 | Implemented | ADR-005 §26 canonical-architecture closeout, frozen legacy-signal allowlist guard, final migration ledger (below) | **29 signals, not 26** — P8's own re-audit found and corrected P7C's count error | See §26.8 of ADR-005 for the full deferred-debt list |

## Final Migration Ledger

| Capability | Transaction model | Typed DomainEvent | ViewInvalidation | Legacy Signal | Status | Future action |
|---|---|---|---|---|---|---|
| Organization create | Canonical UoW | `OrganizationCreated` | YES (`organization_list`, `organization_details` unconsumed) | NO | Fully modernized (create only) | — |
| Organization update/set-active | Legacy service call | NO | NO | `organizations_changed` (direct) | Partially modernized | Future semantic migration slice |
| Module Entitlement | Canonical UoW | 5 events | YES | NO (`modules_changed` retired) | Fully modernized | — |
| RoleBinding | Canonical UoW | `RoleBindingAssigned`/`Revoked` | YES (dual tenant+org subscription) | NO | Fully modernized | — |
| Tenant Membership | Canonical UoW | 4 events | YES (tenant-only, never org-rescoped) | NO (no `auth_changed` bridge) | Fully modernized | — |
| Approval | Canonical UoW | `ApprovalRequested`/`Approved`/`Rejected` | YES | NO (`approvals_changed` deleted) | Fully modernized | — |
| Custom Role Definition | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Authentication/Session | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| User Account | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Password | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| MFA | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Federated Identity | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Registration/Bootstrap | Legacy service call | NO | NO | `auth_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Employee | Legacy service call | NO | NO | `employees_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Department | Legacy service call | NO | NO | `departments_changed` (direct) | Grandfathered legacy | Future semantic migration slice |
| Site (shared-master) | Legacy service call | NO | NO | `sites_changed` (direct, cross-module) | Grandfathered legacy | Future semantic migration slice |
| Working Calendar (shared-master) | Legacy service call | NO | NO | none remaining (`calendars_changed` deleted P7B — zero producers) | Dead signal deleted | — |
| Document (shared-master) | Legacy service call | NO | NO | `documents_changed` (direct, cross-module) | Grandfathered legacy | Future semantic migration slice |
| Party (shared-master) | Legacy service call | NO | NO | `parties_changed` (direct, cross-module) | Grandfathered legacy | Future semantic migration slice |
| PM: project/tasks/timesheets/resources/baseline/register/collaboration/portfolio | Legacy service call | NO | NO | 8 distinct signals (direct-wired, P7A) | Module-migration backlog | Future PM module migration |
| PM: budgets/billing-preparations/planned-costs | Legacy service call | NO | NO | 3 distinct signals (real producer + real consumer) | Module-migration backlog | Future PM Finance migration |
| PM: cost-entries/commitments/forecasts/financial-changes | Legacy service call | NO | NO | none remaining (all 4 deleted P7C — zero consumers) | Dead signals deleted | Future PM Finance migration would need genuinely new semantic events, not a revival of these names |
| Inventory/Procurement (10 entity families) | Legacy service call | NO | NO | 10 distinct signals (direct-wired, P7A) | Module-migration backlog | Future Inventory module migration |

*29 total remaining `Signal[str]` fields on `DomainEvents` — see
`test_p8_platform_event_architecture_canonicalization.py::FROZEN_LEGACY_SIGNAL_ALLOWLIST` for the
exact, source-verified list this ledger's "Legacy Signal" column summarizes.*

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

## Approval-SEM — Prerequisite / Semantic Discovery (complete; no code changes)

**Status:** discovery only, as instructed. Resolves both prerequisites `platform_p5_event_
discovery.md` §17 items 1-2 flagged as blocking. No DomainEvent, ViewInvalidation, or Qt work
implemented. No production code changed; two narrow test-observation notes below, no fixes.

### Current model (re-audited from source, not from prior ADR assumptions)

`ApprovalRequest` (`domain/approval/approval_request.py`) is a **plain frozen-ish
`@validated_dataclass`, not a `RecordsDomainEvents` aggregate** -- `id`, `request_type`,
`entity_type`, `entity_id`, `project_id`, `payload`, `organization_id` (optional, but the ORM
column is `NOT NULL` and every real caller resolves it via `require_active_organization_id`
before construction -- effectively always populated), `status: ApprovalStatus` (`PENDING`/
`APPROVED`/`REJECTED` only -- no `applied`/`failed`/`cancelled`), `requested_by_user_id`/
`requested_by_username`, `requested_at`, `decided_by_user_id`/`decided_by_username`,
`decided_at`, `decision_note`. **No `.approve()`/`.reject()`/`.request()` methods exist** --
`ApprovalService` mutates `request.status`/`decided_*` fields by bare attribute assignment.

**Transaction architecture is already canonical for the primary paths.** `PlatformUnitOfWork`
(`contract/persistence/unit_of_work.py`) + `SqlAlchemyPlatformUnitOfWork`
(`infrastructure/persistence/unit_of_work.py`) is a thin `SqlAlchemyUnitOfWorkBase` subclass --
fresh Session per `create()` call, `approvals`/`_enterprise_audit_service` typed accessors,
already inherits `record_event`/`commit`/the transactional dispatcher/post-commit bus. `request_
change` (transaction-owning branch), `approve_and_apply`, `reject` all use `with self._uow_
factory.create(...) as uow:`. **The UoW-level infrastructure a future Approval event needs
already exists and needs zero new plumbing** -- unlike P5D-1, there is no "build a new UoW from
scratch" prerequisite here.

**The grandfathered caller-owned `request_change(commit=False)` path is still real, and its
count was stale in the source docstring (said "two", is actually THREE).** All three still use a
shared, process-lifetime `Session` with inline `try:`/`.commit()`/`except:`/`.rollback()` --
none has been converged to a canonical UoW:

1. `inventory_procurement/application/procurement/procurement_lifecycle.py` --
   `submit_requisition()` (`purchase_requisition.submit`).
2. `project_management/application/financials/financial_changes/service.py` --
   `FinancialChangeService.submit_change()` (`financial_change.apply`).
3. `project_management/application/financials/invoicing/preparation_service.py` --
   `ProjectBillingPreparationService.submit_preparation()`
   (`project_billing_preparation.approve`).

Each stages its own prior mutation (requisition status flip / financial change submission /
billing preparation submission) and the `ApprovalRequest` insert on the SAME shared `Session`,
then commits once. Two of the three (`FinancialChangeService`/`ProjectBillingPreparationService`)
correctly call `ApprovalService.publish_requested(request)` afterward for the canonical
post-commit signal+notification path; the third (`procurement_lifecycle.submit_requisition`)
**does not** -- it duplicates `domain_events.approvals_changed.emit(request.id)` inline itself
and skips `_notify_approval_requested` entirely, a pre-existing notification gap, unrelated to
this discovery's scope but flagged for whoever eventually converges that caller.

**`commit=False` is NOT obsolete** -- P4/PF has not converged these three callers to canonical
UoWs, so removing the parameter now would silently split their atomicity across two physical
transactions. A future `ApprovalRequested` event recorded at request-creation time must be
recordable from BOTH the canonical-UoW path (`uow.record_event(...)`, trivial) AND these three
callers' own shared-Session path -- which means either (a) those three callers get their own
transaction convergence first (a real, separate prerequisite phase, likely Approval-P0 or folded
into each caller's own PF/PM modernization), or (b) a transaction-agnostic
`ApprovalMutationParticipant.request_using(...)` (mirroring `role_binding_mutation_participant.py`
exactly: takes the caller's own session-bound `approval_repo`/`audit_repo`/`clock`/
`record_event` callback, never commits/rolls back/opens a Session) is built so the three legacy
callers can record the SAME event through their own transaction without adopting a full UoW.
**Recommendation: (b) is the smaller, lower-risk prerequisite** -- it does not require touching
three other capabilities' own transaction ownership, and the pattern is already proven twice
(RoleBinding, then reused verbatim by TenantMembership).

**Apply-handler atomicity is fully proven, not assumed.** 18 handler registrations across 12
`request_type`s (`project_registry.py`: baseline.create, dependency.add/remove/update,
task.constraint.update, scheduling.leveling.apply, budget.approve, project_cost.approve,
financial_change.apply, project_billing_preparation.approve; `inventory_registry.py`:
purchase_requisition.submit, purchase_order.submit -- 14 apply + 4 reject handlers, confirming
the "18 approval participants" figure exactly). Every handler is `(request, deps) ->
ApprovalHandlerResult | None`; every `dependencies_factory(session)` builds fresh, session-bound
collaborators from the SAME `uow._session` `approve_and_apply`/`reject` pass in; zero `.commit(`/
`.rollback(`/`UnitOfWorkFactory`/`Session(` calls found in any of the participant modules; every
underlying target-capability mutation call passes `commit=False` explicitly; no participant
emits a legacy signal directly -- all go through `ApprovalHandlerResult.post_commit_events`
(`ApprovalPostCommitEvent(signal_name, payload)`), drained by `ApprovalService._emit_handler_
events` strictly after `uow.commit()` succeeds. This matches ADR-PF-008's own accepted decision
record exactly ("apply handlers may validate and stage repository/domain mutations but must not
commit, roll back, dispatch notifications, or emit process-local success signals") -- confirmed
implemented as designed, not just documented.

**`approve_and_apply`'s exact order (settles item 3/13/20's "what does Approved mean" question):**
load pending request -> self-decision guard -> resolve handler (raise `APPROVAL_HANDLER_MISSING`
if none registered) -> **invoke the apply handler FIRST** -> only then set `status=APPROVED`/
`decided_*` fields -> audit (`fail_closed=True`) -> `uow.commit()`. **If the apply handler
raises, nothing commits -- the request remains PENDING, unchanged, forever (no `failed` status
exists to fall into).** This conclusively answers item 3: `ApprovalApproved` can only ever mean
"the decision succeeded AND the approved change was atomically applied" (Option B) -- there is no
source-supported reading where a request becomes "approved but unapplied." The prior discovery's
rejection of a separate `ApprovalApplied` event is **reconfirmed, not just carried forward**.

**`reject` has no apply handler requirement** -- a `reject_handler` is optional (only 4 of 12
request types register one, e.g. releasing a reserved resource); if none is registered, rejection
proceeds with just the status flip + audit. Symmetric atomicity guarantee: if a registered reject
handler raises, the same rollback applies -- request stays PENDING.

**No-op/invalid transitions are hard errors, never silent no-ops.** `_require_pending_using`
raises `APPROVAL_ALREADY_DECIDED` for ANY non-PENDING status before either commit path is ever
reached -- approve-already-approved, reject-already-rejected, approve-a-rejected-request, etc.
all raise before any mutation, audit, or event recording occurs. There is no idempotent-no-op
branch (unlike RoleBinding's `create_role_binding_using`) -- command invocation on an
already-decided request is always an error, so "zero DomainEvent on invalid transition" is
guaranteed structurally, not by a design choice that needs enforcing later.

### The critical open decision: tenant ownership (§17 item 1) -- RESOLVED

**`ApprovalRequest` (the domain dataclass) has no `tenant_id` field -- confirmed, re-verified.**
But the persisted row DOES have one: `ApprovalRequestORM.tenant_id` (nullable at the schema
level, but the repository's `add()` unconditionally stamps `ctx.tenant_id` -- resolved from
`TenantContextService.require_active_scope_ids()`, i.e. the ACTOR's own ambient active tenant at
write time -- so it is always populated in practice) is used correctly for READ isolation
(`get()`/`list_by_status()`/`list_by_status_for_organization()` all filter `tenant_id ==
ctx.tenant_id` first). **The mapper (`mappers/approval/approval.py`) simply never round-trips
`tenant_id` between the ORM and the domain dataclass in either direction** -- a clean, narrow,
already-half-solved gap, not a missing column or a missing isolation mechanism.

**Today's tenant isolation is real and correctly enforced, just ambient (the established,
codebase-wide `TenantScopedRepositorySupport` pattern every other tenant-scoped repository
already uses -- not a defect unique to Approval).** `reject`/`approve_and_apply` both call
`uow.approvals.get(request_id)` first, which already filters by the ACTING user's own ambient
tenant -- a cross-tenant `get()` returns `None`, raising `APPROVAL_NOT_FOUND` before any
mutation. Tenant A genuinely cannot approve/reject Tenant B's request today. **This is not a
live security hole; it is a DomainEvent-readiness gap** -- a future event needs `event.
tenant_id` as a plain, explicit fact read off the request, not re-derived from ambient
`TenantContextService` state at record time (ADR-005 §3's rule, and the exact trap `assign_scope_
grant`/`Module.set_module_state` fell into before their own P5C/P5B fixes).

**Recommendation (matches the task's own stated enterprise-SaaS default, and is unusually
low-risk here since the data already exists): add `tenant_id: str` to the `ApprovalRequest`
dataclass, and map it both directions in `approval_to_orm`/`approval_from_orm`.** No schema
migration needed (the column already exists and is already correctly populated by the
repository on every write) -- this is a pure domain-model/mapper correction, not an
infrastructure change. Once present, every future event can read `request.tenant_id` directly,
with zero ambient re-derivation and zero post-commit re-query.

### Approval's actual scope shape (§7's over-generalization corrected)

**Approval is organization-scoped, not tenant-wide** -- `organization_id` is `NOT NULL` at the
schema level and every real caller resolves an active organization before creating a request;
reads filter on `(tenant_id, organization_id)` together (with a project-fallback join for rows
whose own `organization_id` might diverge from their project's). This is a genuinely different
scope shape than `TenantMembership`/`RoleGovernance`'s tenant-wide bindings -- it mirrors
RoleBinding's own *resource*-scope shape (`OrganizationScope(tenant_id, organization_id)`) more
than Membership's `TenantScope(tenant_id)`. A future Approval ViewInvalidation target must use
`OrganizationScope`, never `TenantScope`, and never `organization_id=None`-as-tenant-wide.

### Aggregate-vs-application event recording (§17 item 2) -- RESOLVED

**Recommendation: APPLICATION-AUTHORED (`uow.record_event(...)` from `ApprovalService`), not
aggregate-authored.** `ApprovalRequest` does not currently own its transitions (no `.approve()`/
`.reject()` methods, no invariants encapsulated on the entity) -- promoting it to a
`RecordsDomainEvents` aggregate purely to satisfy ADR-005's stated *preference* would be
aesthetic, not evidence-driven, and the task's own item 18 explicitly warns against forcing
aggregate recording for that reason. More decisively: the `ApprovalApproved` fact, per the
`approve_and_apply` trace above, is NOT fully determined by `ApprovalRequest` alone -- it also
depends on the apply handler's own orchestration OUTCOME (a fact external to the aggregate,
produced by `dependencies_factory`/the target-capability participant), which is exactly item 18's
textbook case for application-authored recording. Adding `.approve()`/`.reject()` methods to
`ApprovalRequest` (§17 item 2's first option) would only correctly express the STATUS half of the
fact and would still need an external application-level check (did the handler succeed?) before
it could honestly be called -- a partial aggregate would be worse than no aggregate. This
decision is the opposite of P5D's aggregate audit (`UserTenantMembership` DOES own real,
invariant-checked transition methods already) precisely because the source evidence differs.

### Actor/requester/target field decision

**Business-identity fields belong on the events, unlike the four already-converged
capabilities.** `ApprovalRequest` already persists `requested_by_user_id`/`decided_by_user_id` as
durable business data (not merely audit metadata) -- the requester and the approver/rejector are
first-class governance participants a consumer legitimately needs without a second query (e.g. "
whose request is this", "who decided it"), unlike Organization/Module/RoleBinding/Membership
where the acting admin's identity was correctly excluded as pure `DomainEventContext`/audit
concern. Recommendation: include `requested_by_user_id` on `ApprovalRequested`, `decided_by_user_
id` on `ApprovalApproved`/`Rejected` (never a display name/username -- durable identifiers only,
matching every other event's own convention).

### Recommended event fields (documentation only -- not implemented)

- `ApprovalRequested`: `approval_id`, `tenant_id`, `organization_id`, `request_type`,
  `entity_type`, `entity_id`, `project_id`, `requested_by_user_id`, `occurred_at`.
- `ApprovalApproved`: `approval_id`, `tenant_id`, `organization_id`, `request_type`,
  `entity_type`, `entity_id`, `decided_by_user_id`, `occurred_at`.
- `ApprovalRejected`: same shape as `Approved` plus `decision_note` (matches the domain object's
  own existing field; omit if empty, never invent one).

No raw `payload` (may carry financial/resource/security details) on any event -- consumers needing
more than the identifiers above should re-query by `approval_id`, matching item 26's explicit
instruction and every other converged capability's own restraint.

### Event vocabulary verdict

`ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected` -- **reconfirmed, unchanged.** No
`ApprovalChanged`/`ApprovalStatusChanged`/`ApprovalUpdated`, no `ApprovalApplied` (redundant, per
above), no new invitation-style eventless-transition additions needed: PENDING is the only
"created" state (no separate request-vs-materialize split), and the two decision transitions
(`PENDING -> APPROVED`, `PENDING -> REJECTED`) are the only two decision facts source evidence
supports.

### Notification / audit / PlatformEvent / outbox separation (all confirmed correctly separate
already, none need to change)

- **Notifications** (`_notify_approval_requested`/`_notify_approval_decided` via `safe_dispatch_
  notification`) are POST-commit, outside the `with uow:` block, called only after a successful
  commit -- already correctly separate from the future DomainEvent and never merged with it.
- **Audit** goes through the SAME generic `AuditEntry`/`record_audit_entry` mechanism every other
  converged capability uses (`operation`, `entity_type="approval_request"`, `fail_closed=True`,
  inside the transaction) -- not the separate `PlatformEvent` immutable governance log.
- **`PlatformEvent`** (`domain/events/platform_events/platform_event.py`, requiring an explicit
  `tenant_id`) is a DIFFERENT mechanism entirely, currently used only by `TenantAdminService` for
  tenant lifecycle facts (create/suspend/archive) -- Approval does not use it today and this
  discovery recommends no change.
- **Integration outbox** genuinely exists for at least the purchasing/procurement family
  (ADR-PF-008/ADR-PF-011 govern it explicitly: "Financial mutation, approval decision, Enterprise
  Audit intent/row, idempotency/inbox state, and durable outbox records commit atomically" /
  "the current post-commit process-local signals remain UI refresh notifications and are not a
  substitute for durable integration delivery"). A future Approval DomainEvent replaces ONLY the
  process-local-signal presentation layer, exactly as ADR-PF-011 already anticipates -- it must
  never touch or duplicate the outbox staging, which stays exactly as-is.

### Legacy `approvals_changed` inventory (production only)

**5 producers:** `approval_service.py`'s own three commands (`request_change`'s fresh-UoW path,
`reject`, `approve_and_apply`, all via the canonical `_emit_signal_safely`/`publish_requested`
path) + the two caller-owned-transaction paths' own direct emissions
(`procurement_lifecycle.submit_requisition` duplicates the emit inline instead of calling
`publish_requested`; `preparation_service.submit_preparation`/`financial_changes.submit_change`
correctly call `publish_requested`).

**3 real production consumers**, all coarse (no narrow approval-specific reaction exists yet
anywhere):

1. `PlatformControlWorkspaceController._bind_domain_events` -- subscribes `approvals_changed`
   alongside 6 unrelated signals (`project_changed`/`tasks_changed`/`costs_changed`/
   `resources_changed`/`baseline_changed`/`register_changed`), all routed through one coarse
   `refresh()` reloading the control-workspace overview, the approval queue, AND the audit feed
   regardless of which signal fired.
2. `bind_collaboration_domain_events` (PM module) -- subscribes `approvals_changed` +
   `timesheet_periods_changed` into one coarse panel refresh.
3. `approvals_builder.py` (the Collaboration tab's own Approvals list) -- reads the SAME
   `PlatformApprovalDesktopApi.list_requests(...)` as the other two, filtered additionally by
   `project_id` -- a third real consumer of identical data, not a separate concept.

**Real read models, all backed by the SAME `ApprovalService.list_requests`/`_list_approval_rows_
using` query** (organization-scoped: `tenant_id == ctx.tenant_id AND (organization_id == ctx.
organization_id OR project.organization_id == ctx.organization_id)`): the Control workspace's
approval queue, the Control workspace overview's approval count (not yet traced to its exact
field name -- flagged for the implementation phase, not re-derived here), and the PM
Collaboration tab's project-filtered approvals list.

**Proposed ViewInvalidation target (documentation only, not implemented): one target,
`approval_requests`, `OrganizationScope(tenant_id, organization_id)`-scoped**, mirroring the
"one target covers all three real consumers, all read the same authoritative data" pattern
`tenant_memberships` established for P5D-3 -- `ApprovalRequested`/`Approved`/`Rejected` would all
map onto it via one shared handler. Tenant switch must re-scope (dispose+resubscribe, mirroring
every existing adapter); since Approval genuinely IS organization-scoped (unlike Membership), an
organization switch WITHIN the same tenant SHOULD re-scope too (mirroring RoleBinding/Module's own
adapters, not Membership's tenant-only one) -- this is a real, source-confirmed difference from
the P5D-3 precedent, not an oversight if a future implementer only re-scopes on tenant switch.

### Prerequisite blockers found

**None are hard blockers for typed-event implementation itself** -- both explicit design
questions this pass was asked to resolve are now resolved with a clear recommendation and
low-risk fix shape. The one genuine sequencing dependency: **the three `commit=False` callers'
own transaction architecture must be addressed (via option (a) or (b) above) before `Approval
Requested` can be recorded consistently across ALL request-creation paths** -- recording it only
from the canonical-UoW branch and leaving the three legacy callers silent would be an incomplete,
inconsistent event producer, not a genuine blocker to defer indefinitely.

### Recommended implementation phases

- **Approval-P1 (prerequisite convergence):** add `tenant_id` to `ApprovalRequest` + mapper;
  build `ApprovalMutationParticipant.request_using(...)` (transaction-agnostic, mirroring `role_
  binding_mutation_participant.py`) so the three legacy `commit=False` callers can eventually
  record `ApprovalRequested` through their own transaction without a full UoW migration. No new
  UoW needed (already canonical) -- this phase is narrower than P5D-1's.
- **Approval-P2 (typed DomainEvents):** `ApprovalRequested`/`Approved`/`Rejected`, application-
  authored via `uow.record_event(...)`, recorded at the exact points traced above (Approved only
  after the apply handler succeeds, before commit).
- **Approval-P3 (ViewInvalidation + direct UI cutover):** one `approval_requests`
  `OrganizationScope` target, migrate the 3 real consumers off `approvals_changed` (retain the
  signal for nothing else -- unlike `auth_changed`, no other capability shares it), organization-
  switch re-scoping (unlike Membership).

Do not manufacture a P0 -- the canonical UoW and apply-handler atomicity are already sufficient;
Approval-P1 is genuinely the smallest first step, not busywork.

**Explicit non-goals of this discovery pass:** no DomainEvent, ViewInvalidation, or Qt migration
implemented; `approvals_changed` not removed; no custom-role/authentication modernization
started; no production code changed.

### Approval-P1 — Tenant Ownership + Request Transaction Convergence (implemented)

**Tenant ownership.** `ApprovalRequest` now carries authoritative `tenant_id: str` (required,
non-optional, never derived from ambient `TenantContextService`/active org/Qt workspace after
construction) alongside its existing `organization_id`. No schema migration was needed -- the
`approval_requests.tenant_id` column already existed; the gap was purely the mapper never
round-tripping it. `approval_to_orm`/`approval_from_orm` now carry it both directions;
`SqlAlchemyApprovalRepository.add()`/`update()` stamp it via the same `TenantScopedRepositorySupport
._stamp_scope(...)` every tenant-scoped repository already uses (validate-if-set, stamp-if-absent
-- never blind overwrite). Every production and test construction site across the repo was updated
to supply `tenant_id` explicitly; there is no default, so a caller that forgets it fails loudly
with `APPROVAL_TENANT_ID_REQUIRED`.

**The transaction-agnostic request participant.** `approval_mutation_participant.py`
(`request_approval_using(...)`) now owns the common request-creation semantics previously
duplicated inside `ApprovalService.request_change`: duplicate/open-request guard (org-scoped when
available), cross-organization project guard, `ApprovalRequest.create(...)`, `approval_repo.add()`,
and the fail-closed audit entry (`build_request_audit_details(...)`). It takes already-constructed
collaborators (`approval_repo`, `enterprise_audit_service`) as plain parameters -- it never commits,
rolls back, opens a Session/UnitOfWork, publishes notifications, or emits `approvals_changed`; the
transaction owner (the standalone `ApprovalService.request_change` or one of the four converged host
commands below) does that, strictly after `uow.commit()`. This lets every caller share identical
request-creation mechanics without ever nesting a UnitOfWork inside another.

**Caller-owned transaction convergence.** All caller-owned-transaction paths that used to compose
`ApprovalService.request_change(commit=False)` onto their own shared, process-lifetime Session are
converged onto their own narrow, capability-specific canonical UnitOfWork, calling
`request_approval_using(...)` directly instead:

- `ProcurementLifecycleMixin.submit_requisition` -> `RequisitionSubmissionUnitOfWork`
  (`requisitions`, `requisition_lines`, `approvals`, `_enterprise_audit_service`).
- `FinancialChangeService.submit_change` -> `FinancialChangeSubmissionUnitOfWork` (`changes`,
  `budgets`, `forecasts`, `approvals`, `_enterprise_audit_service`).
- `ProjectBillingPreparationService.submit_preparation` -> `BillingPreparationSubmissionUnitOfWork`
  (`billing`, `approvals`, `_enterprise_audit_service`).
- `PurchasingLifecycleMixin.submit_purchase_order` -> `PurchaseOrderSubmissionUnitOfWork`
  (`purchase_orders`, `approvals`, `_enterprise_audit_service`) -- discovered during this phase (not
  in the original three-caller inventory) still composing `request_change(commit=False)`; converged
  identically rather than left to crash once `commit` was removed.

Each factory opens a genuinely fresh Session per call (never the shared legacy Session), shares the
SAME composition-owned `TransactionalEventDispatcher`/`PostCommitEventPublisher` every other
Platform/P5 canonical UoW factory uses, and is wired in `project_registry.py`/`inventory_registry.py`
with `submission_uow_factory`/`*_submission_uow_factory` constructor parameters that default to
`None` (so existing test doubles that never call the submit method stay valid) but are always
supplied in production composition; the submit method itself raises a `BusinessRuleError` if the
factory is missing, rather than silently falling back to caller-owned semantics.

`request_change(commit=False)` was removed completely: `ApprovalService.request_change` has no
`commit` parameter at all, and no production caller anywhere in `src/core` passes `commit=False` to
it (enforced by `test_approval_p1_architecture_guards.py`). No replacement boolean transaction-
ownership flag was introduced -- callers now participate in their own transaction explicitly via
`request_approval_using(...)`.

**Notifications preserved, unchanged.** `ApprovalService.publish_requested(...)` (the standalone
path's existing post-commit notification + `approvals_changed` emission) is now called by every
converged host command too, post-commit, from the host's own method -- never from the participant.
This incidentally fixed a pre-existing gap: `submit_requisition` and `submit_purchase_order`
previously emitted `approvals_changed` directly, bypassing `ApprovalService`'s permission-holder
notification fan-out (`_notify_approval_requested`); they now go through `publish_requested` like
every other request path. `approvals_changed` itself is retained unchanged for now (removal is
Approval-P3 scope, not P1).

**Verification added:** mapper round-trip test; a cross-tenant repository-read isolation test
(two genuinely different tenant contexts against the same database, never an "active organization"
switch within one tenant); a fresh-Session test for each of the four converged paths plus the
standalone path (already existing); a commit-failure rollback test proving the financial-change
write and its `ApprovalRequest` roll back together; and the architecture guards described above
(no `RecordsDomainEvents`, no Approval DomainEvent classes, no Approval ViewInvalidation, no
`commit` parameter, no production `commit=False` caller, participant purity).

**Not done in this phase (by design):** `ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected`
events, Approval ViewInvalidation, Qt consumer migration, `approvals_changed` removal, and any
change to `approve_and_apply`/`reject`'s own (already-canonical) atomicity beyond reusing
`build_request_audit_details(...)` from the participant module instead of a private duplicate.

### Approval-P1A — Verification Closure (implemented)

A follow-up pass closing the two verification gaps the Approval-P1 report explicitly flagged as
incomplete: same-tenant cross-organization authorization coverage, and audit-failure rollback
coverage for all four converged outer request workflows. No production redesign; two real,
narrow production fixes surfaced and applied along the way (below). No DomainEvents/ViewInvalidation/
Qt migration/`approvals_changed` removal -- still P1/P1A scope only.

**Same-tenant, cross-organization authorization semantics (clarified, not changed).**
`ApprovalService.approve_and_apply`/`reject` require only the GLOBAL role permission
`approval.decide` -- there is no per-organization-scoped "decide" grant for Approval anywhere in
this codebase. The organization boundary is enforced entirely by
`SqlAlchemyApprovalRepository.get()`'s ambient `TenantScopedRepositorySupport._context()` filter,
which requires the SESSION's active organization (`TenantContextService`, driven by
`UserSessionContext.active_organization_id()` -- a different, unrelated concept from
`OrganizationService.get_active_organization()`'s DB-level "single business-active organization
per tenant" flag) to match the request's own `organization_id` (or its project's organization).
`OrganizationService.set_active_organization` itself requires only the global `settings.manage`
permission, with no per-organization membership check -- switching which organization is active
is the ONLY mechanism that changes which organization's Approval requests are visible.

Proven in `test_approval_same_tenant_cross_org_authorization.py`:
- **Negative case:** an actor holding `approval.decide`, with Org A2 active, cannot
  `approve_and_apply`/`reject` an Approval belonging to Org A1 in the same tenant -- `NotFoundError`,
  before any apply/reject handler, decision-audit write, notification, or `approvals_changed`
  signal runs (the request is invisible to `uow.approvals.get(...)`, not merely permission-denied).
- **§3 (explicit cross-org authority while a different org remains active) is N/A:** nothing in
  this authorization model grants decide authority over a non-active organization's request while
  a different organization is active. Evidence: the SAME actor, holding the SAME permission,
  fails against Org A1's request while Org A2 is active and succeeds against the IDENTICAL
  request once Org A1 becomes active -- proving decide authority tracks the active organization
  matching the request's authoritative `organization_id`, with no simultaneous multi-org decide
  capability to test as a distinct code path.
- **Cross-tenant isolation (§4) is unchanged** and re-verified via the existing
  `test_platform_unit_of_work.py::test_cross_tenant_context_cannot_read_another_tenants_approval_
  request` -- not duplicated here.

**Audit-failure rollback, all five request-creation paths.** Forcing the Approval audit write
itself to fail (distinct from a commit failure) rolls back the WHOLE owning transaction in every
case -- no `ApprovalRequest`, no host mutation, no notification/`approvals_changed`:
- Standalone `ApprovalService.request_change` (`test_approval_service_unit_of_work_cutover.py::
  test_request_change_fails_closed_when_the_approval_audit_write_fails`).
- `submit_requisition`/`submit_purchase_order`: each has exactly ONE in-transaction audit write
  today (the Approval request's own, inside `request_approval_using`) -- neither has a separate
  host-level audit entry yet (tracked debt, unchanged by this pass). Forcing that one write to
  fail is the full atomicity proof available for these two paths.
- `submit_change`/`submit_preparation`: each has TWO in-transaction audit writes (the Approval
  request's own, then a separate, later host-level audit entry --
  `_audit_change_using`/`_audit_using`). The tests force failure specifically on the SECOND call,
  proving atomicity even when the failure occurs strictly after both the host mutation and the
  ApprovalRequest have already been staged in the same transaction.

**Two narrow production fixes surfaced by this pass (test-exposed, not scope creep):**
1. A duplicate `resource_id: str | None = None,` parameter in
   `TaskQueryMixin.query_workspace_page` (`task_query.py`) made the ENTIRE test suite fail to
   collect (`SyntaxError: duplicate argument`). Unrelated to Approval; resolved independently by
   the user's own concurrent work before this pass needed to touch it -- noted here only because
   it briefly blocked running the regression suite this verification pass depends on.
2. None found inside Approval-P1/P1A's own code paths themselves -- all gaps closed were test
   coverage gaps, not production defects.

### Approval-P2 — Typed Approval DomainEvents (implemented)

Implements exactly `ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected`
(`src/core/platform/domain/approval/events.py`) -- frozen, `slots=True`, keyword-only dataclasses,
no infrastructure imports, no `ApprovalApplied`/`ApprovalChanged`/`ApprovalStatusChanged`. No
DomainEvents/ViewInvalidation/Qt migration/`approvals_changed` removal beyond this.

**Fields (locked, all identical shape except the actor field):**
```
ApprovalRequested(approval_id, tenant_id, organization_id, approval_type, entity_type,
                   entity_id, requested_by_user_id, occurred_at)
ApprovalApproved(approval_id, tenant_id, organization_id, approval_type, entity_type,
                  entity_id, decided_by_user_id, occurred_at)
ApprovalRejected(approval_id, tenant_id, organization_id, approval_type, entity_type,
                 entity_id, decided_by_user_id, occurred_at)
```
No `payload`, `project_id`, `correlation_id`/`causation_id`/`command_id` (those stay on
`DomainEventContext`), free-text rejection reason, display name, or schema version.
`tenant_id`/`organization_id` always come from the authoritative `ApprovalRequest`, never
re-derived from `TenantContextService`/active org/Qt context.

**Ownership: application-authored, one recording responsibility per event.**
`ApprovalRequest` still does NOT implement `RecordsDomainEvents` (reconfirmed).
`approval_mutation_participant.request_approval_using(...)` is the ONE place `ApprovalRequested`
is constructed -- proven by an architecture guard (`test_approval_events.py::
test_approval_requested_has_exactly_one_recording_responsibility`) that greps all of `src/core`
for `ApprovalRequested(` and requires exactly one hit. `ApprovalService.approve_and_apply`/
`reject` record `ApprovalApproved`/`ApprovalRejected` directly -- no host service, repository, or
UI facade constructs any of the three.

**Recording mechanism: a narrow callback, never a concrete UoW type.** `request_approval_using`
gained two new required keyword parameters -- `clock: Clock` and
`record_event: Callable[[object], None]` -- mirroring `role_binding_mutation_participant.py
::create_role_binding_using`'s own established shape exactly. The module still imports no
SQLAlchemy/Session/concrete UnitOfWork (guarded). Every one of the five call sites passes its own
owning UoW's bound method (`uow.record_event`) and its own `Clock` instance:
1. `ApprovalService.request_change` -> `self._clock` (new; guarded via `_require_clock()`,
   raising `APPROVAL_CLOCK_REQUIRED` if unset) + `uow.record_event`.
2. `submit_requisition` -> `self._clock` (new on `ProcurementService`, optional/guarded exactly
   like `requisition_submission_uow_factory` was in P1, for the apply-participant's own
   submission-unrelated instance) + `uow.record_event`.
3. `submit_purchase_order` -> `self._clock` (new on `PurchasingService`, same optional/guarded
   shape) + `uow.record_event`.
4. `submit_change` -> the EXISTING `self._clock` on `FinancialChangeService` + `uow.record_event`.
5. `submit_preparation` -> the EXISTING `self._clock` on `ProjectBillingPreparationService` +
   `uow.record_event`.

All five `Clock` instances are `SystemClock()` in production composition
(`platform_registry.py`/`inventory_registry.py`) -- no `datetime.now()`/`datetime.utcnow()` calls
were introduced for event `occurred_at`; determinism proven via `_FixedClock` test doubles.

**`ApprovalRequested` recording point.** Inside `request_approval_using`, immediately after
`approval_repo.add(request)` and the fail-closed request audit entry -- i.e. right after the
business fact (a valid, invariant-checked, PENDING `ApprovalRequest`) is staged, never deferred
to just-before-commit. All five request contexts (standalone + the four converged host
workflows, including the fourth-caller purchase-order path) record exactly one, proven by
per-path `_spy_recorded_events`-style tests plus a two-request ordering test.

**`ApprovalApproved` recording point.** `approve_and_apply`'s existing ordering already matched
the locked semantics without needing reordering: apply participant runs and must succeed FIRST;
only then does `request.status = APPROVED` execute, `uow.approvals.update(request)` persists it,
and `uow.record_event(ApprovalApproved(...))` runs immediately after that `update()` call, before
the decision audit entry and `uow.commit()`. If the apply participant raises, execution never
reaches the status transition, the event recording, or commit -- proven by a dedicated
apply-handler-failure test asserting zero recorded events, zero postcommit publication, and the
request still PENDING. Any target-capability DomainEvent the apply participant itself records
(e.g. `BudgetApprovalParticipant`'s own) commits in the SAME transaction, strictly BEFORE
`ApprovalApproved` in committed order -- verified, never suppressed, never duplicated into
`ApprovalApproved`'s own fields.

**`ApprovalRejected` recording point.** `reject`'s existing ordering already matched the locked
semantics too: any registered reject participant runs before `uow.approvals.update(request)`;
`uow.record_event(ApprovalRejected(...))` runs immediately after that `update()` call. A reject-
participant failure emits zero events, request stays PENDING.

**Invalid transitions.** A second decision attempt on an already-decided request
(`APPROVAL_ALREADY_DECIDED`) is a command that never re-enters the decision body -- zero new
events, zero new audit, zero postcommit reaction (proven for both approve and reject).

**Cross-tenant / cross-org event isolation.** Re-verifies Approval-P1A's own authorization
findings at the event layer: a same-tenant, non-active-organization decision denial emits zero
`ApprovalApproved`/`ApprovalRejected`; a genuinely different tenant (two independent
`TenantContextService` fakes over the same database, sharing only the transactional
dispatcher/post-commit bus so a leak would be observable) cannot reach another tenant's request
at all -- `NotFoundError`, zero events, before any dispatch could occur.

**Transactional (pre-commit, FAIL_FAST) vs. post-commit (ISOLATE_AND_CONTINUE) semantics.**
Unchanged, generic `SqlAlchemyUnitOfWorkBase` behavior, exercised for Approval specifically: a
failing transactional handler rolls back the WHOLE owning transaction (no `ApprovalRequest`
persists, no postcommit publication follows); a failing post-commit subscriber is isolated (the
sibling subscriber and the already-committed decision are both unaffected). No Approval-specific
event-bus behavior was added.

**Audit/commit failure still suppresses observable events.** Re-run and extended: forcing the
Approval audit write to fail, or forcing `uow.commit()` to fail, now additionally asserts zero
events reach a real post-commit subscriber (not merely that the ApprovalRequest/host mutation is
absent from the database, as P1A already proved).

**Notification / PlatformEvent / outbox: unchanged, still separate.** `publish_requested`/
`_notify_approval_decided` remain post-commit, unmodeled as DomainEvents. No `PlatformEvent` is
constructed from an Approval DomainEvent. No Approval event is mapped into any outbox; the
existing ADR-PF-011 procurement outbox mapping (unrelated target-capability concern) is untouched.
`approvals_changed` is retained, fired directly from `ApprovalService`/the host commands exactly
as before -- no `ApprovalRequested`/`Approved`/`Rejected` -> `approvals_changed` bridge was built.

**Latent test-infrastructure bug found and fixed while adding these guards.** Approval-P1's own
`test_approval_p1_architecture_guards.py` computed `_SRC_CORE` as `Path(__file__).resolve()
.parents[3] / "core"` -- one level too high (resolves to the repo root's nonexistent `core/`,
not `src/core/`), so every guard built on `_SRC_CORE.rglob(...)` was vacuously passing (`rglob`
on a nonexistent directory yields nothing, matching nothing, including a real violation). Fixed
to `parents[2]`; the same, correctly-computed pattern is used in this phase's own new guards.
`test_no_approval_domain_event_classes_exist_yet` (P1's phase-boundary assertion that the three
events did NOT exist yet) is retired now that P2 has legitimately implemented them; its forward-
looking replacement (`ApprovalApplied`/`ApprovalChanged`/`ApprovalStatusChanged` must not exist)
lives in `test_approval_events.py`.

**Not done in this phase (by design):** Approval ViewInvalidation, Qt consumer migration,
`approvals_changed` removal, any redesign of `approve_and_apply`/`reject`'s own atomicity beyond
adding event recording at the already-correct point, any change to the 18 apply/reject
participants' own target-capability logic.

### Approval-P3 — Approval ViewInvalidation + Direct UI Consumer Cutover (implemented)

Maps all three typed events (`ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected`) to ONE
ViewInvalidation target -- category `"approval"`, `scope_code="approval_requests"`, scope
`OrganizationScope(event.tenant_id, event.organization_id)` (never `TenantWide`/`AllTenants`,
never re-derived from ambient context) -- and cuts the two genuine UI consumers over to it
directly. No event-vocabulary change, no `ApprovalApplied`, no apply-participant change, no P6
Qt-adapter-consolidation work (this builds one more capability-specific adapter, following the
existing Module Entitlement/RoleBinding/TenantMembership precedent exactly, not the future shared
one).

**`approvals_changed` re-audit from current source (not trusted from any earlier estimate).**
Exactly 3 producers, all in `ApprovalService` (`publish_requested`/`reject`/`approve_and_apply`) --
matches P2's own inventory. 4 consumers found (one more than previously tracked): Control
workspace's approval queue + Control/Admin overview pending-approval count (same controller, same
read models -- genuine); PM Collaboration's approvals panel (genuine, direct signal subscription);
and a previously-unlisted 4th, PM Dashboard, reached only through the legacy
`X_changed` -> `domain_changed` auto-bridge (`DomainEvents._wire_bridges()`) via
`_subscribe_domain_change("approval_request", scope_code="platform")` -- classified INCIDENTAL and
dropped, not migrated, after confirming by grep that `PlatformDashboard`'s own
`build_workspace_state(...)` never reads any Approval data.

**One mapper, one adapter (capability-specific, not the P6 shared adapter).**
`src/core/platform/application/approval/event_handlers/view_invalidation.py` --
`build_approval_view_invalidation_handler(channel)` maps all three event types to the one hint
above; no Qt/`domain_events` import (guarded). `src/ui_qml/platform/adapters/
approval_view_invalidation_adapter.py` -- `ApprovalViewInvalidationAdapter(QObject)`, one
`approvalsStale` Signal, `set_active_scope(*, tenant_id, organization_id)` (dispose-then-
resubscribe, at most one live subscription), filters by category+scope_code, `dispose()`; no
`ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected`/`DomainEvent` import (guarded, source
scanned with docstrings/comments stripped so prose mentioning those names in the class's own
explanatory docstring cannot false-positive the guard). Wired in `platform_registry.py`
(`platform_post_commit_bus.subscribe(EventType, handler)` for all three event types, reusing the
one shared `platform_view_invalidation_channel`) and constructed in both `PlatformWorkspaceCatalog`
and `ProjectManagementWorkspaceCatalog` (`context.py`).

**Control workspace: narrow refresh, audit feed untouched.** `PlatformControlWorkspaceController.
refresh()` split into `_refresh_approval_state()` (overview + approval queue only --
`PlatformControlWorkspacePresenter.build_overview()` was already 100% approval+audit-derived, so
this was a clean extraction, not a dashboard redesign) and the full `refresh()` (adds the audit
feed on top, still used for filter changes/manual reload/other domain events). The new
`refresh_approvals()` -- gated by the existing `_loaded`/`_is_loading`/`_is_busy` lazy-loading
contract (queues via `_pending_domain_refresh` if busy, no-ops if never visited) -- calls only
`_refresh_approval_state()`, and the adapter's `approvalsStale` connects to it. The
`domain_events.approvals_changed` entry was removed from `_bind_domain_events()`'s subscription
tuple; the other six (`project_changed`/`tasks_changed`/`costs_changed`/`resources_changed`/
`baseline_changed`/`register_changed`) are unchanged, pre-existing, out of scope.

**PM Collaboration: full `refresh()`, by deliberate, documented choice.** `build_overview(inbox=,
mentions=, approvals=, active_users_count=)` needs all four current values together -- there is no
narrow "approvals-only" recompute without a deeper `overview_builder.py`/panel restructuring, which
this phase does not do. `refresh_approvals()` therefore calls the existing
`_request_domain_refresh()` (same debounce-aware scheduling as every other domain event this
controller already reacts to). This still satisfies the phase's actual requirement for PM (exact
tenant/org-scoped reaction, no legacy signal fallback) even though it is not the minimal-recompute
shape Control got. `bind_collaboration_domain_events()`'s `approvals_changed` subscription was
removed; PM Dashboard's incidental `_subscribe_domain_change("approval_request",
scope_code="platform")` was dropped outright (not migrated -- see audit above).

**Controllers stay ignorant of the event vocabulary (guarded).** Neither
`control_workspace_controller.py` nor `collaboration_workspace_controller.py` imports
`ApprovalRequested`/`ApprovalApproved`/`ApprovalRejected`/`DomainEvent`/`ViewInvalidationHint`/
`ScopeFilter`/`EventScope`/the postcommit bus -- both only ever see the adapter's narrow
`approvalsStale` Qt signal.

**Proven end-to-end, exactly once each, no legacy signal:** standalone `request_change`; a host
workflow (`FinancialChangeService.submit_change`); `approve_and_apply`; `reject` -- all assert the
narrow reaction fires exactly once and that `domain_events` no longer even has an
`approvals_changed` attribute.

**Proven isolation:** cross-org (Org A2's own request does not stale an adapter still scoped to
Org A1); cross-tenant (two independent `TenantContextService` fakes sharing only the transactional
dispatcher/post-commit bus -- zero callback); adapter never subscribes via `AllTenants`/
`TenantWide`, only `ExactOrganization`.

**Proven organization/tenant switch lifecycle** (the property explicitly called out as different
from TenantMembership's tenant-only scoping): `set_active_scope(...)` disposes the old
subscription before adding the new one (`len(channel._subscriptions)` never grows across a
switch); a full A/A1 -> A/A2 -> B/B1 -> A/A1 sequence ends with exactly one live subscription,
correct final scope, no duplicate callbacks; the real `refreshCurrentPermissions()` hook (Platform
shell's already-QML-wired tenant/org-switch entrypoint, same one Module Entitlement/RoleBinding/
TenantMembership adapters rescope from) correctly rewires the Approval adapter too.

**Proven failure-path suppression, all producing zero UI refresh:** apply-handler failure,
reject-handler failure, audit failure, commit failure, transactional-handler failure (whole
transaction rolls back, zero postcommit invalidation), and one broken postcommit subscriber
(ISOLATE_AND_CONTINUE -- the Control workspace's own sibling subscription is unaffected).

**`approvals_changed` deleted -- zero remaining producers or consumers.** All 3 producer call
sites removed from `ApprovalService` (the underlying `_emit_signal_safely` static helper is
retained; it still serves the 18 unrelated apply/reject participants' own target-capability
signals). The `Signal[str]` field and its `_BRIDGE_SPECS` entry were both removed from
`DomainEvents` (`src/core/shared/events/domain_events.py`) -- confirmed via
`not hasattr(domain_events, "approvals_changed")`. No typed-event -> legacy-signal bridge was
built, matching every prior P5 phase's own precedent.

**Genuine architectural gap discovered (documented, not fixed here).**
`ProjectManagementWorkspaceCatalog` had zero pre-existing tenant-resolution mechanism (no
`tenant_switcher`, no tenant field on `PlatformRuntimeContextDto`/`OrganizationDto`) -- resolved
locally by constructing a lightweight `TenantSwitcherPresenter(tenant_api=...)` inside PM's own
catalog. Separately, and pre-existing/wider than Approval: PM's `refreshAllWorkspaces()`/
`refreshCapabilities()` are never called from any `.qml` file today, for any capability -- so while
the Approval adapter's rescope call is correctly wired into `refreshCapabilities()`, PM has no
automatic QML-triggered tenant/org-switch rescoping yet for anything. This is out of scope for
Approval-P3 and is not claimed as fixed.

**P6 design inputs surfaced by this phase (not acted on):** the fifth near-identical adapter
(construction/`set_active_scope`/`_on_hint`/`dispose()` shape duplicated once more, now across
Organization/Module Entitlement/RoleBinding/TenantMembership/Approval); the org-scoped vs.
tenant-only rescoping split (`ExactOrganization` vs. tenant-wide filters) a shared adapter would
need to parameterize; Qt signal naming conventions across the five adapters; and the PM
catalog's own switch-lifecycle wiring gap noted above.

**Not done in this phase (by design):** any change to the Approval event vocabulary or apply
participants; the P6 generalized/shared Qt adapter; modernizing any remaining `auth_changed`
capability.

## P6 — Qt Invalidation Adapter Consolidation (implemented, revised scope)

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

### P6 implementation report: what was actually built (revised from the plan above)

**Parity audit finding that changed the plan's own premise.** The planning text above assumed
the ViewInvalidation subscription lifecycle lived on `PlatformWorkspaceControllerBase`
(`_subscribe_domain_change`/`_subscribe_domain_signal`/etc.). Re-auditing all five capability
adapters (Organization, Module Entitlement, RoleBinding, TenantMembership, Approval) from current
source found this was never true: every adapter is constructed and owned by
`PlatformWorkspaceCatalog.__init__` (or, for Approval's PM Collaboration consumer,
`ProjectManagementWorkspaceCatalog`), `parent=self` on the catalog, with its Qt signal connected
directly to a controller method (`refresh_approvals`, `refresh_role_bindings`,
`refresh_organizations`, `refresh_module_entitlements`, `refresh_users`,
`refresh_security_users`, `refresh_organization_profiles`). `PlatformWorkspaceControllerBase`'s
own `_subscribe_domain_change`/`_subscribe_domain_signal`/`_request_domain_refresh`/
`_disconnect_domain_event_subscriptions` machinery is a completely separate mechanism -- the
legacy `domain_events`/`domain_changed` bridge -- and contains zero ViewInvalidation-adapter code
to consolidate. All three controller bases (`platform/controllers/common`,
`project_management/controllers/common`, `inventory_procurement/controllers/common`) were
audited and confirmed to reference no ViewInvalidation adapter at all: **KEEP all three,
unmodified** -- there is nothing there for this phase to consolidate, and forcing a change onto
them would be scope creep the spec explicitly prohibited (§21-23). The actual duplication lives
entirely across the five adapter files' own bespoke `_subscription`/`_dispose_subscription()`
bookkeeping -- that is what P6 consolidates.

**Duplication classification (§2).**
- **(A) Generic subscription lifecycle mechanics -- centralized:** construct-time subscribe,
  dispose-before-resubscribe on every rescope, safe/idempotent `dispose()`, at-most-one-live-
  subscription-per-instance. Identical byte-for-byte across all five adapters before this phase.
- **(B) Capability invalidation vocabulary -- left alone:** each adapter's own `_on_hint`
  category/scope_code filter, its own Qt Signal name (`organizationCollectionStale`/
  `moduleEntitlementsStale`/`roleBindingsStale`/`membershipDataStale`/`approvalsStale`).
- **(C) Capability scope semantics -- left alone:** tenant-only (Organization, TenantMembership)
  vs. organization-scoped (Module Entitlement, Approval) vs. polymorphic dual-subscription
  (RoleBinding) -- each adapter's own `set_active_scope`/`set_active_tenant` still decides which
  `ScopeFilter` to construct, the helper never sees a tenant_id/organization_id string.
- **(D) Qt/controller-specific signal naming -- left alone.**

**Chosen abstraction: composition, not inheritance (§5/§6).** A new pure-Python (no `QObject`,
no PySide6 import at all) `ScopedViewInvalidationSubscription`
(`src/ui_qml/platform/adapters/scoped_view_invalidation_subscription.py`) owns exactly (A) above:
`replace_filter(filter: ScopeFilter | None)` (dispose-then-resubscribe, or go inert on `None`)
and `dispose()`. Each capability adapter remains its own thin `QObject` owning its own Signal, and
holds one `ScopedViewInvalidationSubscription` instance per live subscription it needs -- one for
four of the five adapters, two (`_tenant_subscription` + `_organization_subscription`) for
RoleBinding. Inheritance (a shared `QObject` base) was considered and rejected: Qt `Signal`
declarations are class-level, each adapter's signal name is deliberately distinct presentation
vocabulary worth keeping legible (§18/§19), and RoleBinding's two-simultaneous-subscriptions shape
composes trivially as two helper instances but would strain a single-subscription base class.

**No service locator (§4).** Composition wiring in `context.py` (both catalogs) is unchanged --
each capability's adapter is still constructed explicitly by name
(`ApprovalViewInvalidationAdapter(channel=..., tenant_id=..., organization_id=..., parent=self)`),
never through an `adapter_for(...)`/registry lookup (guarded).

**RoleBinding, the hard case (§11), preserved in full.** Its mapper's `_to_event_scope` still maps
`RoleBindingPlatformScope` -> `PlatformScope()`, `RoleBindingTenantScope`/an ownerless
`RoleBindingResourceScope` -> `TenantScope`, and an owned `RoleBindingResourceScope` ->
`OrganizationScope` -- untouched. Its adapter still holds two simultaneous subscriptions
(`TenantWide(tenant_id)` + `ExactOrganization(tenant_id, organization_id)`, no `PlatformWide()`
subscription -- confirmed via the existing P5C-3 reference test that platform-scope role-binding
assignment is unconditionally denied by `RoleGovernanceService` before any event fires, so this is
proven-dead-in-practice, not a gap this phase introduced or should paper over). No generic
abstraction was forced onto it; it simply holds two `ScopedViewInvalidationSubscription`
instances instead of two raw `Subscription | None` fields.

**One-live-subscription invariant (§13) / idempotent rescope (§14).** Structurally guaranteed by
`replace_filter`'s own unconditional dispose-before-subscribe. Idempotence (skip
dispose/resubscribe when the filter is unchanged) was deliberately **not** added: no pre-P6
adapter ever had it, `ScopeFilter` dataclasses being frozen+eq would make it safe to add later,
but adding it now would be an unrequested behavior change (subscription-identity churn) outside a
consolidation-only phase -- characterized and tested as the preserved-as-is current behavior
(`test_replace_filter_with_the_same_filter_still_unconditionally_resubscribes`).

**Empty/unresolved scope (§15) / dispose semantics (§16).** `replace_filter(None)` goes inert --
never a fabricated `AllTenants()`/`TenantWide()` fallback; each adapter's own
`set_active_scope`/`set_active_tenant` decides when to pass `None` (mirrors every adapter's
pre-P6 `if tenant_id and organization_id:` guard exactly). `dispose()` is safe and idempotent,
mirroring `InProcessViewInvalidationChannel`'s own subscription `dispose()` idempotence; a
disposed adapter can still be reactivated by a later `set_active_scope(...)` call, matching every
adapter's existing contract (unchanged).

**Behavioral parity (§27), proven, not assumed.** All five pre-existing capability test files
(2945 lines total: `test_organization_view_invalidation_qt_cutover.py`,
`test_module_entitlement_view_invalidation_qt_cutover.py`,
`test_role_binding_view_invalidation_qt_cutover.py`,
`test_tenant_membership_view_invalidation_qt_cutover.py`,
`test_approval_view_invalidation.py`) pass unmodified against the migrated adapters, except two
tests (`test_organization_view_invalidation_qt_cutover.py::
test_real_tenant_switch_through_the_catalog_rewires_the_adapter_end_to_end` and
`test_tenant_membership_view_invalidation_qt_cutover.py::
test_real_tenant_switch_through_the_catalog_rewires_the_adapter` /
`test_organization_switch_does_not_re_scope_the_membership_subscription`) whose own white-box
assertions reached into `adapter._subscription` expecting the RAW channel `Subscription` -- these
were updated to reach one level deeper (`adapter._subscription._subscription`, the helper's own
raw handle) since `adapter._subscription` is now the always-present
`ScopedViewInvalidationSubscription` wrapper. The semantic assertions themselves (subscription
identity preserved across an unrelated organization switch; filters resolved by subscription id)
are unchanged.

**New tests added (§38/§39):** `test_p6_view_invalidation_adapter_consolidation.py` -- pure-Python
unit tests for `ScopedViewInvalidationSubscription` (no channel, none-filter-inert, dispose-before-
resubscribe, unconditional resubscribe on an equal filter, idempotent dispose, at-most-one-live-
subscription-across-many-rescopes) plus architecture guards: the helper has no Qt/DomainEvent/
capability-vocabulary/repository/SQLAlchemy imports and never sees a tenant_id/organization_id
string; all five adapter modules import the shared helper; no adapter references
`AllTenants`/`AnyOrganizationInTenant`; no legacy signal name (`approvals_changed`/
`organizations_changed`/`modules_changed`/`access_changed`/`auth_changed`/`domain_changed`)
appears in any adapter or the helper; RoleBinding constructs exactly two helper instances, the
other four exactly one; no service locator in either catalog; the Approval event contract and the
`ViewInvalidationHint`/`EventScope`/`ScopeFilter` contract fields are byte-for-byte unchanged from
before this phase.

**Explicit non-goals honored:** no controller-base code changed (none needed changing -- see the
parity-audit finding above); `admin_console/domain_event_binder.py` untouched, still bridging its
own legacy signals until P7; no Approval/P5 event vocabulary or mapper semantics changed; no
`auth_changed` capability modernized; no generic/shared Qt adapter base class introduced.

**Lines/classes deleted or consolidated:** one new 90-line pure-Python helper class; each of the
five adapters lost its own bespoke `_subscription`/`_dispose_subscription()` pair (net: roughly
30 lines of duplicated lifecycle bookkeeping removed across the five files, replaced by one shared
implementation) -- a modest, expected reduction, not the success metric (§40): the actual gain is
one correct subscription-lifecycle implementation instead of five independently-maintained copies.

**Remaining adapter/UI debt (unchanged by this phase, explicitly out of scope):** the PM catalog's
own pre-existing lack of any QML-triggered tenant/org-switch rescoping hook (noted in the
Approval-P3 report above) is untouched; Organization's own unconsumed `organization_details`
ViewInvalidation target remains unconsumed; RoleBinding's `PlatformScope()` hint path remains
unreachable in practice (proven dead by `RoleGovernanceService`'s own denial, not by this phase).

## P7 — Platform Legacy Compatibility Bridge and Cutover (implemented, revised scope)

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

### P7 implementation report: what was actually built (revised from the plan above, pre-release)

**Why the plan above's premise didn't hold.** The planning text assumed all 11 Platform-owned
legacy signals could be deleted once P5/P6 closed, and that `admin_console/domain_event_binder.py`
would simply be deleted as dead compatibility scaffolding. A repo-wide re-audit from current
source (not the plan's own earlier estimate) found neither was true: `organizations_changed`/
`auth_changed`/`employees_changed`/`departments_changed` each still have a real, still-required
DIRECT consumer (none of these transitions were ever modernized -- P5A only ever covered
`OrganizationCreated`; Employees/Departments/Auth/Session/Password/MFA/Custom-Role/Federated-
Identity/Registration were never in scope of any P5x phase at all); and
`admin_console/domain_event_binder.py` was never a generic bridge in the first place -- it
subscribes directly to 8 specific signals (`_subscribe_domain_signal`, never
`_subscribe_domain_change`/`domain_changed`/`_BRIDGE_SPECS`) and owns a real, still-needed
UI-coordination responsibility (coalescing 9 admin-console sub-controllers into one refresh
cycle), explicitly deferred to its own already-planned "R2" phase, not this one.

**Producer -> bridge -> consumer graph, built from current source.** Every one of the 30
`_BRIDGE_SPECS` entries was checked against the full repo for a real `_subscribe_domain_change
(...)`-based consumer of its bridge-routed `domain_changed` output:
- **Alive (kept unchanged):** all `project_management`-scoped entries (`project`, `project_tasks`,
  `project_costs`, `resource`, `project_baseline`, `project_budget`, `project_planned_cost`,
  `project_billing_preparation`, `register_scope`, `task_collaboration`, `portfolio_entity`,
  `timesheet_period`) -- extensively consumed across PM's own dashboard/collaboration/portfolio/
  projects/register/resources/scheduling/tasks/timesheets/financials/resource-timesheets
  controllers. All 10 `inventory_procurement`-scoped entries -- consumed via each Inventory
  controller's own broad `scope_code="inventory_procurement"` subscription (no entity_type
  filter). The 4 remaining `shared_master` entries `sites_changed`/`calendars_changed`/
  `documents_changed`/`parties_changed` -- consumed cross-module, by name, via
  `scope_code="platform"` subscriptions in both Inventory's and PM's own binders (e.g. Inventory's
  catalog/inventory/pricing/procurement/reservations controllers all react to Platform-level
  site/party/document changes; PM's resources/scheduling controllers react to
  `working_calendar`).
- **Dead bridge routing, direct consumer still real (bridge entry removed, signal + consumer
  untouched):** `organizations_changed`, `auth_changed`, `employees_changed`,
  `departments_changed` -- zero `_subscribe_domain_change(...)` call anywhere filters entity_type
  "organization"/"user_account"/"employee"/"department" (confirmed by exhaustive repo grep), so
  their bridge-routed `domain_changed`/`shared_master_changed` emission reached no one -- but each
  still has a real, unaffected DIRECT subscriber (`admin_console/domain_event_binder.py` for all
  four; `settings_workspace_controller.py` additionally for `organizations_changed`;
  `access_workspace_controller.py` additionally for `auth_changed`).
- **100% dead, deleted entirely:** `shared_master_changed` itself -- zero production consumers
  anywhere (only its own declaration/emit site, plus one test that existed solely to preserve the
  signal). Nothing anywhere subscribed to `shared_master_changed` specifically; every real
  shared_master consumer already went through `domain_changed` + an explicit entity_type filter.
- **Found, explicitly out of scope, left untouched:** `cost_entries_changed`/`commitments_changed`/
  `forecasts_changed`/`financial_changes_changed` -- all four are actively, heavily produced by
  real PM financial business logic (`cost_entry_service.py`, `commitment_service.py`, the
  forecasts generation/version services, `financial_changes/service.py`, the approved-time and
  procurement-financial dispatchers, the financial-change apply participant) but have **zero**
  consumers anywhere, bridge or direct -- a pre-existing PM financial-module UI-reaction gap,
  unrelated to Platform legacy-bridge cleanup. Deleting actively-produced business-event
  infrastructure with unknown blast radius is not "removing dead compatibility scaffolding"; left
  fully alone and documented here for whoever eventually picks up PM's own financials-module
  modernization.

**`domain_event_binder.py`: KEPT, evidence-based, unchanged.** Never touched `_BRIDGE_SPECS`/
`domain_changed`/`_subscribe_domain_change` at all -- it already was the §6-preferred "specific
signal -> explicit consumer" shape. Its own docstring already documents both the real
responsibility (coalesce 9 sub-controllers into one refresh, rather than 9 independent
subscriptions) and its own removal point ("R2, when each capability controller manages its own
domain-event subscriptions independently") -- narrowing any one of its 8 signals now would
partially pre-empt that already-planned, distinct future phase for no benefit this phase asked
for. No changes made.

**`_BRIDGE_SPECS`: KEPT as a mechanism, 4 dead entries removed.** Not deletable outright (§4's
"if it is a compatibility registry... DELETE it" is conditioned on the registry itself being dead
weight -- it is not: dozens of real PM/Inventory `_subscribe_domain_change(...)` consumers
genuinely depend on the entries that remain). `organizations_changed`/`auth_changed`/
`employees_changed`/`departments_changed` were removed from the registry -- each entry's *bridge
routing specifically* was proven dead, while each underlying signal and its real direct
consumer(s) are completely unaffected (verified by regression: their own direct-subscription
tests still pass unmodified).

**`shared_master_changed`: DELETED entirely.** Field removed from `DomainEvents`; the
`if category == "shared_master": self.shared_master_changed.emit(event)` branch removed from
`_build_bridge` (the unconditional `self.domain_changed.emit(event)` line, which every real
consumer actually uses, is untouched); the one bridge-only test that existed solely to preserve
this signal (`test_shared_master_changed_bridges_specific_shared_master_events`) retired with a
comment pointing to the still-passing `sites_changed`/`documents_changed` -> `domain_changed`
coverage that remains. Confirmed via `not hasattr(domain_events, "shared_master_changed")`.

**`domain_changed` itself: KEPT, not dead.** Real, current production dependency for dozens of
still-unmodernized PM/Inventory entity types -- §5's deletion condition ("zero real production
producers/consumers") does not hold.

**Access Workspace (§10): already correct, no change needed.** Re-audited
`PlatformAdminAccessWorkspaceController._on_auth_changed` from current source: it calls only
`_refresh_after_security_change()` (`_refresh_security_users()` + `_refresh_empty_state()`) --
never `_refresh_scope_grants()` (RoleBinding's own read model). `refresh_role_bindings()` (the
typed RoleBinding reaction) and `refresh_security_users()` (the typed TenantMembership reaction,
whose own docstring already documented this exact separation) touch disjoint state. Confirmed by
source that `TenantMembershipService` never emits `auth_changed` anywhere (P5D already fully
collapsed membership transitions into the typed path with no legacy bridge) -- so a membership
change triggers exactly one reaction (the typed one), never two. No duplicate-refresh coupling
existed to remove.

**Admin Console (§11): already correct, no change needed.** Organization's typed slice
(`create_organization`) connects only to the narrow `refresh_organizations`, never through
`domain_event_binder.py`; Module Entitlement has no legacy signal left at all (`modules_changed`
fully retired in P5B-3); Approval has no legacy signal left at all (`approvals_changed` fully
deleted in P3, confirmed still absent). Only the genuinely-still-unmodernized update/activate
slice of Organization (plus Employees/Departments/Auth) reaches admin console through the direct
binder -- exactly the "still-unmodernized capability may cause direct legacy refresh" case §11
permits.

**PM Dashboard (§12): confirmed still absent, no regression.** `dashboard_refresh_mixin.py`'s own
`_bind_domain_events()` has no `approval_request`/`scope_code="platform"` entry and no other
cross-capability subscription -- Approval-P3's removal is intact.

**Representative unmodernized capability, proven end-to-end (§18):** a real `forcePasswordReset`
call -> `auth_changed` fires -> `AccessWorkspaceController._on_auth_changed` -> narrow
`_refresh_after_security_change()` only (never the full `refresh()`); RoleBinding's, Organization's,
Module Entitlement's, and Approval's own Qt adapter signals all stay silent. (The mutation's own
`on_success` callback also self-refreshes immediately, independent of the event path -- the same
accepted "self-refresh after your own action" pattern already proven and accepted for
Organization's own `createOrganization`; not confused with the event-driven reaction, isolated
separately in the test.)

**New tests added:** `test_p7_legacy_bridge_removal.py` -- the producer/bridge/consumer inventory
assertions above as executable guards; per-capability zero-legacy-dependency proofs for all five
modernized capabilities (Organization creation never touches `organizations_changed`; Module
Entitlement/RoleBinding/Approval have no legacy signal at all; a real TenantMembership
`accept_invitation` never emits `auth_changed`); the representative-capability end-to-end proof
above; `admin_console/domain_event_binder.py`'s own architecture guard (never imports/uses
`_subscribe_domain_change`/`domain_changed`/`_BRIDGE_SPECS`) plus its still-real composite-refresh
behavior test; the PM Dashboard non-regression check; and architecture guards for no generic
bridge registry outside `domain_events.py`, no typed-event -> legacy-bridge import in any of the
five mappers, no wildcard ViewInvalidation listener anywhere touched by this phase, no service
locator, and `ScopedViewInvalidationSubscription`'s public surface unchanged from P6.

**Explicit non-goals honored:** no further capability modernized to typed events; PM/Inventory's
own extensive `_subscribe_domain_change` usage untouched *by P7 itself* (see the P7A report below,
which does eliminate it); `ScopedViewInvalidationSubscription` unchanged; no Approval/P5 event
contract or ViewInvalidation contract touched; no new business DomainEvent introduced.

**Remaining legacy debt after P7 (superseded by P7A below):** ~~PM/Inventory's own extensive
`_subscribe_domain_change` usage~~ -- eliminated in P7A. Custom Role Definition,
Authentication/Session, User Account, Password, MFA, Federated Identity, and Registration/
Bootstrap all remain on `auth_changed` (direct-wired, narrow, no bridge -- already compliant with
§16's "unmodernized temporary capability" target shape); modernizing any of these to typed
DomainEvents is a future, separate phase, not started here. The four dead-producer financial
signals noted above remain a distinct, pre-existing PM-module gap.

### P7A implementation report: complete removal of the generic bridge architecture

P7 (above) removed only the *dead-bridge residue* of four Platform signals while leaving the
generic mechanism itself (`_BRIDGE_SPECS`/`_wire_bridges`/`domain_changed`/`DomainChangeEvent`/
`_subscribe_domain_change`) in place, since it still had ~26 genuinely alive entries serving
PM/Inventory's own business-module controllers. P7A completes the pre-release mandate: eliminate
that entire generic architecture, not just its dead parts.

**Direct-wiring migration.** All 17 production caller files (11 in `project_management`, 6 in
`inventory_procurement`) that called `_subscribe_domain_change(...)` were converted to connect
directly to the actual `domain_events.<specific_signal>` objects the removed call's entity_type
arguments mapped to 1:1 (via the now-deleted `_BRIDGE_SPECS` table, which was itself the source of
truth for this mapping): `project_management/controllers/{collaboration,dashboard,financials,
portfolio,projects,register,resources,resource_timesheets,scheduling,tasks,timesheets}` and
`inventory_procurement/controllers/{catalog,dashboard,inventory,pricing,procurement,reservations}`.
Each now uses the exact same `_subscribe_domain_signal(signal, callback)` mechanics helper that
already existed and was already fully compliant with §8's "mechanics only" requirement -- no new
utility was introduced. Scope filtering is preserved exactly: a consumer that used to filter
`_subscribe_domain_change("project", "project_tasks", scope_code="project_management")` now
connects directly to `project_changed` and `tasks_changed` -- the specific signal *is* the filter,
since each surviving entity_type mapped to exactly one signal in the deleted table. Bare,
entity_type-less Inventory subscriptions (`_subscribe_domain_change(scope_code="inventory_procurement")`)
were expanded to all 10 inventory signals explicitly, per consumer file (no shared constant --
plain, explicit, duplicated lists, matching every other direct-wire file's style). One consumer
(`resources/resource_domain_event_binder.py`) already had a real duplicate-reaction pattern for
`resources_changed` (a full refresh from the generic path alongside an existing narrow
`_reload_if_loaded("activity")` reaction) -- preserved exactly, not simplified, per §16's "do not
change business semantics" rule.

**No incidental subscriptions found to delete.** Every one of the 17 consumers' entity_type sets
was checked against what that controller's own presenter/read model actually consumes; all were
genuine dependencies (Category A). None were incidental (Category B) or dead (Category C) at the
consumer level.

**Deleted entirely, zero production references remaining:** `_BRIDGE_SPECS`, `_wire_bridges`,
`_build_bridge`, `domain_changed` (the `Signal[DomainChangeEvent]` field), `DomainChangeEvent`
(the dataclass, plus its export from `src/core/shared/events/__init__.py`), and
`_subscribe_domain_change` (removed from all three controller bases -- Platform, PM, Inventory).
`domain_events.py` itself shrank from a 30-entry bridge-spec registry + 33 signal fields to
exactly the 32 real, still-needed `Signal[str]` fields and nothing else.

**Organization lifecycle status corrected.** Prior documentation (including earlier in this same
plan) imprecisely described Organization as "fully typed / zero legacy" alongside Module
Entitlement/RoleBinding/TenantMembership/Approval. Corrected: Organization is **PARTIALLY
MODERNIZED** -- `create_organization` is fully typed DomainEvent -> ViewInvalidation with zero
legacy involvement; `update_organization`/`set_active_organization` (never in P5A's scope) still
emit the direct, un-bridged `organizations_changed` signal, consumed directly by
`settings_workspace_controller.py` and `admin_console/domain_event_binder.py`. This is not a P7A
blocker -- `organizations_changed` was already direct-wired, never routed through the now-deleted
bridge -- but the ownership-matrix claim is corrected here rather than left inaccurate. Module
Entitlement, RoleBinding, TenantMembership, and Approval remain the four capabilities with
genuinely zero legacy presentation dependency of any kind.

**`admin_console/domain_event_binder.py`: unchanged, KEPT.** Re-confirmed unchanged from P7's own
finding -- it was never part of the bridge, already direct-wired, still owns its real composite
coalesced-refresh responsibility.

**New tests added:** `test_p7_legacy_bridge_removal.py` extended with -- absence guards for
`_BRIDGE_SPECS`/`domain_changed`/`DomainChangeEvent`/`_wire_bridges`/`_subscribe_domain_change`
(zero production references anywhere, all controller bases); a forbidden-replacement-shape guard
(`LegacySignalRouter`/`DomainSignalRegistry`/`EntityChangeRouter`/`SignalDispatchMap`/
`CapabilitySignalRegistry` -- none introduced); representative direct-wiring proofs across PM
(register/scheduling), Inventory (dashboard/catalog), and shared-master (documents/parties/sites/
calendars) signals, each proving the specific signal reaches its real consumer exactly once and a
genuinely unrelated signal reaches zero consumers (no accidental scope widening). `test_domain_events.py`
trimmed to the signal-mechanics tests that remain valid (connect/emit/disconnect, deleted-Qt-callback
pruning, RuntimeError propagation, `reset()` clearing every signal) -- its bridge-specific tests
retired along with the mechanism they exercised. `test_qml_domain_event_bridges_pm.py`'s Portfolio
coalescing test rewritten to emit the actual `portfolio_changed`/`project_changed` signals directly
instead of the deleted `domain_changed`/`DomainChangeEvent`.

**Explicit non-goals honored:** no PM/Inventory business semantics changed (no signal emission
site touched, no transaction boundary touched, no signal renamed); no new DomainEvent introduced;
no Approval/P5/P6 contract touched; `ScopedViewInvalidationSubscription` unchanged.

**Remaining legacy debt after P7A:** every still-unmodernized capability's own specific `Signal`
now direct-wired with no generic routing of any kind -- there is no third architecture left in the
codebase. The seven auth-adjacent capabilities (Custom Role Definition, Authentication/Session,
User Account, Password, MFA, Federated Identity, Registration/Bootstrap) and every PM/Inventory
business-module signal remain un-migrated to typed DomainEvents -- that is genuinely separate,
future, per-capability modernization work, not a P7A gap. ~~The four dead-producer PM financial
signals (`cost_entries_changed`/`commitments_changed`/`forecasts_changed`/`financial_changes_changed`)
remain a distinct, pre-existing, out-of-scope PM-module UI-reaction gap, unchanged by P7A.~~
**Corrected in P7B below: these four signals are NOT dead-producer -- see P7B's audit.**

### P7B implementation report: deleting the two genuinely zero-producer signals

P7A's own closing report imprecisely characterized `cost_entries_changed`/`commitments_changed`/
`forecasts_changed`/`financial_changes_changed` as "dead-producer" PM financial signals. P7B
re-audited from current source, per its own explicit instruction not to trust that summary, and
found this was wrong: a repo-wide search for BOTH direct `domain_events.X.emit(...)` call sites
AND the reflective `ApprovalPostCommitEvent(signal_name, payload)` ->
`ApprovalService._emit_signal_safely` -> `getattr(domain_events, signal_name).emit(...)` mechanism
(used by 6 apply participants across PM and Inventory/Procurement, running after every real
approve/reject decision) shows all four have real, active production producers. Their actual
problem -- confirmed unchanged, still correctly out of scope -- is zero UI consumers, the
*opposite* of what P7B targets.

The two signals that genuinely have zero producers of any kind, direct or reflective, are
**`costs_changed`** and **`calendars_changed`** -- both had several real, live UI consumers
(Control workspace, PM dashboard/financials/portfolio/scheduling/resources workspaces, the admin
console binder) that could structurally never have fired, since nothing in production ever emits
either signal. Both deleted entirely: the `Signal[str]` field, and every one of their 7 combined
consumer subscriptions (`dashboard_refresh_mixin.py`, `financials_refresh_mixin.py`,
`portfolio/domain_event_binder.py`, `control_workspace_controller.py` for `costs_changed`;
`resources/resource_domain_event_binder.py`, `scheduling/domain_event_binder.py`,
`admin_console/domain_event_binder.py` for `calendars_changed`). No replacement signal or event
was introduced; each consumer's *other* real subscriptions were preserved exactly and verified via
regression.

**Behavior lost: NONE.** Neither signal ever had a production emission path, so no consumer's
reaction could ever have fired in production regardless of this deletion -- removing the dead
subscription changes nothing an end user could ever have observed.

**New tests:** `test_p7b_dead_signal_cleanup.py` -- absence guards for both deleted signals
(zero production references anywhere, word-boundary-matched to avoid a false positive against the
still-alive `planned_costs_changed`); a correction test proving the four named PM financial
signals are NOT dead (real direct + reflective producers, confirmed by source); a
no-replacement-signal guard; regression proofs that every *other* subscription on the six touched
consumer files still fires correctly; `admin_console/domain_event_binder.py` re-confirmed
unchanged in responsibility (still real, still 7 signals instead of 8); `organizations_changed`
re-confirmed untouched.

**Explicit non-goals honored:** no new DomainEvent or replacement signal introduced; PM Finance
business semantics untouched (no emission site added, no transaction boundary touched, no signal
renamed); Organization's legacy signal untouched; `admin_console/domain_event_binder.py` kept,
unchanged in responsibility; no generic bridge reintroduced.

**Final signal invariant (superseded by P7C below).** ~~Every remaining `DomainEvents` `Signal`
field now has at least one real production producer. `cost_entries_changed`/`commitments_changed`/
`forecasts_changed`/`financial_changes_changed` remain the one documented, deliberate exception to
"producer AND consumer both > 0" -- real producers, zero consumers, a pre-existing PM
financial-module UI-reaction gap explicitly left for a future, separate PM Finance semantic
migration.~~ **P7C deleted these four signals entirely, producers included -- see below. The
"exception" is now closed, not merely documented.**

### P7C implementation report: deleting the four zero-consumer signals and their producers

P7B closed with one documented exception: `cost_entries_changed`/`commitments_changed`/
`forecasts_changed`/`financial_changes_changed` had real production producers but zero UI
consumers, left in place as a "pre-existing PM financial-module UI-reaction gap." P7C revisited
that exception under the pre-release rule that a Signal with no consumer has no production
effect, regardless of how many producers still fire into it -- and deleted all four.

**Consumer audit, reconfirmed from current source.** A repo-wide search across `src/ui_qml/**`
for `domain_events.<signal_name>` found zero UI references for all four -- no `.connect(`, no
`_subscribe_domain_signal(...)`, no binder entry, anywhere. A separate check confirmed no non-UI
consumer either (no audit/notification-persistence/outbox/cache-invalidation subscriber reads
these `Signal` objects -- `AuditEntry`/`Notification`/`IntegrationEventEnvelope` are genuinely
separate mechanisms, written directly by the same service methods, never through these Signals).
Confirmed emit-into-the-void.

**Every producer deleted, not merely the consumers.** Unlike P7A/P7B (bridge routing / dead
signals with real UI consumers still attached), P7C's four signals had real producers that had to
be removed too, or the `Signal` field deletion would crash the first time that code path ran.
Removed:
- **Reflective (`ApprovalPostCommitEvent`) producers:** `project_cost_apply_participant.py`'s
  `apply()`/`reject()` (`cost_entries_changed`, both methods -- now emit zero post-commit events);
  `financial_change_apply_participant.py`'s `apply()` (`financial_changes_changed`/
  `forecasts_changed` removed, `budgets_changed`/`tasks_changed` kept -- both real, both still
  fire conditionally exactly as before) and `reject()` (`financial_changes_changed` removed -- now
  emits zero post-commit events, there was nothing else to notify).
- **Direct `.emit(` producers:** `cost_entry_service.py` (`_commit_and_emit` renamed to `_commit`,
  emit line removed, 8 call sites updated); `commitment_service.py` (same rename pattern, 3 call
  sites); `financial_changes/service.py` (4 standalone inline emits removed from
  `create_change`/`add_impact`/`submit_change`; the dead, zero-caller `_commit_and_emit` helper
  deleted outright; `_emit_applied`'s `financial_changes_changed`/`forecasts_changed` lines
  removed, `budgets_changed`/`tasks_changed` kept; `_apply_rejection_decision`'s now-empty
  `if commit:` emit block removed); `forecasts/generation_service.py` (1 inline emit removed);
  `forecasts/version_service.py` (`_commit_and_emit` renamed to `_commit`, 8 call sites updated);
  `approved_time_dispatcher.py` (the whole `if project_id: try: ... emit(...) except: ...`
  isolation block removed, including the now-unused `project_id`/`entry` locals);
  `procurement_financial_dispatcher.py` (`_emit_local_refresh` -- a method whose ENTIRE body only
  emitted `commitments_changed`/`cost_entries_changed` -- deleted outright, along with its sole
  call site and the now-unused `result` local).

**Business mutation, audit, and integration/outbox behavior: unchanged.** Every removal was
strictly the dead notification-emission line/block; no business method's actual mutation,
`record_audit_entry`/enterprise-audit call, transaction boundary, or `IntegrationOutboxService`/
`IntegrationInboxService` interaction was touched. Proven by a real end-to-end budget-approval
regression test (asserting `budgets_changed` -- a real, kept signal -- still fires correctly) and
by the full PM Finance/Approval-participant/Approved-Time-integration regression suites.

**Remaining `ApprovalPostCommitEvent` inventory, verified exhaustively.** Every surviving
construction site (`inventory_requisitions_changed`/`inventory_purchase_orders_changed`/
`inventory_balances_changed` in the two Inventory procurement participants; `baseline_changed`;
`billing_preparations_changed`; `budgets_changed`; `tasks_changed`) resolves to a `DomainEvents`
field that both exists and has a real UI consumer -- confirmed by an AST-based scan of every
`ApprovalPostCommitEvent(...)` call site's literal signal-name argument, cross-checked against
`domain_events`'s own fields and against `src/ui_qml/**`'s own consumer references. No
emit-into-the-void `ApprovalPostCommitEvent` remains.

**`ApprovalService._emit_signal_safely`: kept.** 19 real callers remain across the participants
listed above -- the reflective mechanism itself is still genuinely needed, only 5 of its call
sites (the ones naming a now-deleted signal) were removed.

**New tests:** `test_p7c_zero_consumer_signal_cleanup.py` -- absence guards for all four deleted
signals (word-boundary-matched); a guard that no `ApprovalPostCommitEvent` references a deleted
signal name; the AST-based "every remaining `ApprovalPostCommitEvent` resolves to a real signal
with a real consumer" guard; `_emit_signal_safely` retention proof; participant-level proofs that
`apply()`/`reject()` now construct zero `ApprovalPostCommitEvent`s for the deleted signals while
keeping the real ones; the real end-to-end budget-approval regression; structural guards that no
`_commit_and_emit`-named helper remains anywhere and that the two dispatcher files no longer
reference any deleted signal; a final-invariant guard (every remaining `DomainEvents` field has
some production reference) with no more documented exceptions; a no-replacement-event guard.
P7B's own three tests that asserted these four signals still existed with real producers were
retired (superseded, not contradicted -- P7B's finding was correct at the time; P7C is a
subsequent, deliberate deletion). Five pre-existing test files that manually subscribed to/emitted
one of the four dead signals were updated: two whole tests characterizing dead compatibility
behavior were retired outright (a `cost_entries_changed`-emission characterization test, and an
Approved-Time dispatcher failure-isolation test whose isolated failure mode no longer exists) with
one new equivalent-coverage test added; three tests' `post_commit_events` assertions were updated
to reflect the narrower (or now-empty) tuples the participants return.

**Explicit non-goals honored:** no PM Finance DomainEvent introduced; no ViewInvalidation added;
no UI consumer added merely to justify a producer's continued existence; no PM Finance business
mutation changed; Approval DomainEvent behavior unchanged; no generic bridge reintroduced.

**Final legacy signal invariant, now fully closed.** Every remaining `DomainEvents` `Signal` field
has both a real production producer and a real production consumer. Zero known zero-producer
signals remain (P7B). Zero known zero-consumer signals remain (P7C). There is no longer any
documented exception.

**PM Finance read-model invalidation gap: none newly discovered.** The four deleted signals'
absence changes nothing observable -- no production code path ever reached a real UI consumer
through them, so their removal is not evidence of (and does not create) a PM Finance UI-staleness
bug. Whether PM Finance's UI should react to cost-entry/commitment/forecast/financial-change
approvals via some future *typed* mechanism is a separate, not-yet-investigated product question,
correctly left for a dedicated semantic migration rather than resurrected here via legacy Signal
names.

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
