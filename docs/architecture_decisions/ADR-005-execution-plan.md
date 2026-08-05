# ADR-005 Execution Plan: Domain Events Migration

- Companion to [ADR-005-domain-events.md](ADR-005-domain-events.md) — that
  document owns the design decisions and rationale; this document owns
  sequencing, scope per phase, and exit criteria.
- Status: draft — no phase started yet (ADR-005 itself is still "proposed,"
  not "accepted"; do not begin Phase 0 until it's accepted).
- Date: 2026-08-05, based on a direct codebase survey (module file counts,
  grep for `DomainChangeEvent(`, `_subscribe_domain_change(`, `unit_of_work`
  callers) run the same day — see "Current State Snapshot" below.

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
   `UnitOfWorkFactory`, `Clock`, and repository/domain contracts — never on
   `src.ui_qml` or any `PySide6`/Qt import. This is what the repo's own
   `EXECUTION_SPEC.md` already anticipates with its future HTTP call chain
   (`HTTP router/controller -> module HTTP API -> application handler ->
   domain + contracts -> infrastructure`) sharing the same `application
   handler` layer as today's desktop path. A FastAPI adapter, when it
   arrives, is a new thin module under `src/core/modules/<module>/api/http/`
   or `src/api/http/` calling the *same* application handlers the desktop
   presenters call today — not a reason to touch `domain/` or
   `application/`. Each phase's exit criteria includes a grep check for
   this (see "Design Guardrails" below). Writing application-service tests
   directly against `UnitOfWorkFactory`/`Clock`/repositories (no Qt test
   doubles) is how this gets proven per phase, not just asserted.
3. **No compatibility facades, no straddling code.** Matches this repo's
   existing hard rule in `EXECUTION_SPEC.md`: finish one slice, delete the
   old path for that slice, don't leave both mechanisms live for a module
   past its own phase's close.

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
- `src/infra/composition/app_container.py`'s `build_service_graph(session)`
  and `src/ui_qml/shell/app.py`'s `build_services()` are the two places a
  `UnitOfWorkFactory` needs to be constructed and threaded through.
- No `domain/events.py` or `RecordsDomainEvents` pattern exists anywhere —
  this is fully greenfield.
- No FastAPI/Flask/web framework is present in `requirements*.txt` or
  `pyproject.toml` yet — confirmed clean slate, nothing to integrate
  against today.

## Phase 0 — Foundational Contracts (Zero Behavior Change)

**Scope:** `src/core/shared/events/*`, `src/core/shared/time/*`,
`src/infra/events/*`, `src/infra/time/*` only. No existing file touched, no
module wired in.

Tasks:

- Create `domain_event.py`, `aggregate_events.py`, `domain_event_publisher.py`,
  `domain_event_subscriber.py`, `subscription.py`, `unit_of_work.py`
  (protocols only), `view_invalidation.py` under `src/core/shared/events/`
  per ADR-005 §2.1–§2.6, §2.10.
- Create `src/core/shared/time/clock.py` (protocol only).
- Create `src/infra/events/{in_process_transactional_event_bus.py,
  in_process_post_commit_event_bus.py, in_process_view_invalidation_channel.py}`
  per §2.9/§2.10, including the race-free drain loop and the identity-map
  aggregate tracker.
- Create `src/infra/time/system_clock.py`.
- Full unit test coverage per ADR-005's "Test Impact" list items that don't
  require a real module: bus thread-safety, the empty-queue/`_dispatching`
  race, `FAIL_FAST` queue-clear-on-exception, tenant isolation on
  `ViewInvalidationChannel.subscribe()`, rollback-discards-instances.

**Exit criteria:** every new file has unit tests passing in isolation;
`git diff` touches nothing outside these four new directory trees; the app
boots unchanged (nothing imports these yet).

## Phase 1 — `UnitOfWork` Wired Into Composition Root, Unused By Any Service

**Scope:** `src/infra/persistence/db/unit_of_work.py` (reclaimed),
`src/infra/composition/app_container.py`.

Tasks:

- Replace `session_scope()`'s body with `SqlAlchemyUnitOfWork` per
  §2.6.1/§2.7 — fold the existing try/commit/rollback/close shape in as a
  private helper used by `__enter__`/`__exit__`. Nothing imports
  `session_scope` today, so nothing else changes.
- `build_service_graph(session)` builds one `UnitOfWorkFactory` and adds it
  as a new field on `ServiceGraph` — additive only, no existing field
  changes shape.
- Integration test: open a `SqlAlchemyUnitOfWork` against a real test
  session, register a plain (non-domain-event) object via
  `register_touched`, commit, confirm `tracked_aggregates()` clears.

**Exit criteria:** app boots; `UnitOfWorkFactory` is constructible and
usable in isolation; zero application services reference it yet.

## Phase 2 — Pilot Module: `inventory_procurement`

**Rationale:** fewest real touch points among modules that actually use
the mechanism (1 subscribe site, 0 raw `DomainChangeEvent` constructions,
12 named Signals to retire) — enough real usage to prove the pattern
end-to-end without the blast radius of `project_management` or
`maintenance`.

Tasks (backend first, QML step deliberately last):

1. Add `src/core/modules/inventory_procurement/domain/events.py` — typed,
   tenant-aware events replacing the 12 named Signals
   (`inventory_items_changed`, `_item_categories_changed`,
   `_storerooms_changed`, `_balances_changed`, `_reservations_changed`,
   `_requisitions_changed`, `_purchase_orders_changed`,
   `_receipts_changed`, `_maintenance_materials_changed`,
   `_locations_changed`, `_reorder_policies_changed`,
   `_cycle_counts_changed`).
2. Adopt `RecordsDomainEvents` + injected `Clock` on the aggregates that
   raise these.
3. Repository `register_touched` calls on load/add for inventory
   repositories.
4. Add `application/event_handlers/view_invalidation.py` with
   module-owned constants (mirroring §2.11's
   `ProjectManagementInvalidation` example); add a
   `transactional.py` only if a real cross-aggregate case turns up during
   this work (none is evident from the survey — confirm before writing
   one speculatively).
5. Wire `register_post_commit_handlers` into the composition root's
   `SubscriptionRegistry`.
6. Full test pass on 1–5 before touching anything QML-facing.
7. **Only now:** update the one existing `_subscribe_domain_change` call
   site (the dashboard) to consume `ViewInvalidationChannel` instead.
8. Delete the 12 inventory-owned fields out of the old `DomainEvents`
   dataclass.

**Exit criteria:** inventory module tests green; dashboard refresh behavior
unchanged from a user's perspective; zero inventory-owned fields left in
the old `DomainEvents` dataclass; grep confirms no `ui_qml`/`PySide6`
import in `inventory_procurement/domain/` or `/application/`.

## Phase 3 — `hr_management`, `payroll`, `qhse`: No Migration Needed Yet

These three have **zero** current domain-event usage — there is nothing to
migrate and no old Signal fields to retire. Do not manufacture events for
them speculatively. When one of these modules first needs a domain event
for a real feature, it adopts the Phase 0 contracts directly as a new
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

Tasks: same shape as Phase 2 (steps 1–8), scaled to the 9 signals
(`project_changed`, `tasks_changed`, `timesheet_periods_changed`,
`costs_changed`, `resources_changed`, `baseline_changed`,
`register_changed`, `collaboration_changed`, `portfolio_changed`) and the 2
subscribe sites (dashboard, financials refresh mixins).

**Exit criteria:** same shape as Phase 2, plus: no regression in the
PM Collaboration Upgrade's own in-flight work (run its existing test
suite, not just the new event tests).

## Phase 5 — `maintenance` (Highest Risk — Do Last)

**Rationale for going last:** this module has the heaviest actual abuse of
the old pattern — 25 raw `DomainChangeEvent(...)` constructions scattered
directly across `application/*_service.py` files, plus 6 subscribe sites —
despite having *zero* dedicated Signal fields (it rides the generic
`domain_changed`/`shared_master_changed` bridge entirely). A raw
`DomainChangeEvent(category, scope_code, entity_type, entity_id,
source_event)` construction doesn't self-document which typed event it
should become, so this phase needs a by-hand mapping (all 25 sites, before
touching any of them) that the named-Signal modules didn't require.
Deliberately scheduled after Phases 2 and 4 so the pattern has been proven
twice on modules with cleaner starting points first.

Tasks: same shape as Phase 2 (steps 1–8), preceded by an explicit
construction-site-to-typed-event mapping table checked in as part of the
phase's own working notes before any code changes.

## Phase 6 — Platform/Shared-Master Signals: Needs a Decision First

The 11 signals not owned by any business module (`auth_changed`,
`employees_changed`, `organizations_changed`, `sites_changed`,
`departments_changed`, `calendars_changed`, `documents_changed`,
`parties_changed`, `access_changed`, `modules_changed`,
`approvals_changed`) plus the 2 generic bridge signals
(`shared_master_changed`, `domain_changed`) are platform-wide facts, not a
single module's business events. **ADR-005 does not decide where these
go**, and this plan should not decide it silently either. Open question for
the user before this phase starts:

- Do these become typed platform domain events under
  `src/core/platform/domain/events.py` (consistent with the layer-first
  restructure's home for platform concerns), or do they stay permanently
  as generic UI-refresh Signals on the grounds that they may never need
  transactional/typed domain semantics?

This phase is blocked on that decision, not on engineering effort.

## Phase 7 — Retire the Old Mechanism

Once every module and the platform layer have migrated (or Phase 6 has
explicitly decided some signals stay generic and are kept on purpose),
delete `src/core/shared/events/domain_events.py` — the `DomainEvents`
dataclass, `_wire_bridges()`, `_BRIDGE_SPECS` — entirely. No facade, no
re-export shim, per this repo's existing no-facade rule.

## Design Guardrails Enforced Every Phase

- The QML-facing step is always the *last* task within a phase (see
  Constraint 1) — never a co-requisite of the domain/application design
  for that phase.
- Before closing any phase: grep that module's `domain/` and
  `application/` for `PySide6`/`ui_qml` imports — must be zero. This is the
  same discipline that makes a future FastAPI HTTP adapter a pure addition
  alongside `src/ui_qml/`, sharing the same application-handler layer,
  rather than a rewrite (see Constraint 2).
- Application-service tests for the phase are written directly against
  `UnitOfWorkFactory`/`Clock`/repositories — no Qt/QML test doubles — as
  the concrete proof of Constraint 2, not just a design claim.
- No silent scope drift: if a phase's module turns out to need something
  ADR-005 didn't anticipate (e.g. a real cross-aggregate transactional
  handler in `inventory_procurement`), that's a correction to ADR-005
  itself, raised before the phase closes — not a local workaround.

## Sequencing Summary

| Phase | Scope | Size / Risk | Blocking dependency |
|---|---|---|---|
| 0 | Shared contracts | None, additive | ADR-005 accepted |
| 1 | `UnitOfWork` + composition root | None, additive | Phase 0 |
| 2 | `inventory_procurement` (pilot) | Small, real usage | Phase 1 |
| 3 | `hr_management` / `payroll` / `qhse` | No-op until a module needs it | Phase 0 only |
| 4 | `project_management` | Large; in-flight PM Collaboration Upgrade | Phase 2 proven; PM Collaboration Upgrade backend stable + user confirmation |
| 5 | `maintenance` | Large; most tangled call sites (25 raw constructions) | Phases 2 and 4 proven |
| 6 | Platform/shared-master signals | Blocked on a decision, not effort | User decision on final home |
| 7 | Retire old mechanism | — | All prior phases closed |
