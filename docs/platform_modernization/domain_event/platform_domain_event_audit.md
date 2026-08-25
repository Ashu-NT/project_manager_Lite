# Platform Domain Event Architecture — Deep Current-State Audit

- Status: audit complete, awaiting review. Not an ADR. Not an implementation plan.
- Date: 2026-08-25
- Scope: `src/core/platform/`, `src/core/shared/`, the platform-relevant parts of `src/infra/` (`composition/`, `platform/`, `persistence/db/`, `integration/`), and `src/ui_qml/platform/`. Business modules (`project_management`, `inventory_procurement`, `hr_management`, `payroll`, `qhse`) are cited only as consumer/comparison evidence, never audited for their own sake.
- Companion documents: [ADR-005: Domain Events](../../architecture_decisions/ADR-005-domain-events.md) (status: proposed — treated here as context, not ground truth), [ADR-005 Execution Plan](../../architecture_decisions/ADR-005-execution-plan.md), [ADR-PF-008: Approval Unit of Work](../../architecture_decisions/ADR-PF-008-approval-unit-of-work.md) (accepted, implemented), [ADR-PF-011: Durable Integration Outbox and Inbox](../../architecture_decisions/ADR-PF-011-durable-integration-outbox-inbox.md) (accepted, implemented).

---

## 1. Executive Summary

Platform's current event-like machinery is not one mechanism wearing one name — it is **at least five architecturally distinct mechanisms**, three of which happen to share the word "events" in their package paths despite having nothing to do with each other:

1. `src/core/shared/events/domain_events.py`'s `DomainEvents`/`DomainChangeEvent`/`Signal` — a mutable global singleton that is, by actual producer/consumer behavior, a **post-commit UI-refresh/invalidation bus**, not a domain-event mechanism. Every sampled payload is a bare opaque ID; no tenant, no correlation, no business-fact content anywhere.
2. `ApprovalService` (`src/core/platform/application/approval/approval_service.py`, governed by the accepted ADR-PF-008) — Platform's own, already-shipped, already-tested "outer transaction owns commit; handlers stage only; post-commit reactions dispatch after commit and are isolated from failure" pattern. **ADR-005 never references this document or this code**, despite ADR-005 proposing a *second*, more general version of almost the same guarantee.
3. `PlatformEvent` (`src/core/platform/domain/events/platform_events/platform_event.py`) — an immutable, append-only, tenant-scoped **audit-log record**, not a dispatched event at all. It lives in a package literally named `events/` and shares no code, no base class, and no purpose with (1) or (2).
4. `Notification`/`NotificationService` — a persisted, user-facing, multi-channel **in-app notification feature**, also living under a package named `events/`, also unrelated to (1)-(3).
5. `IntegrationEventEnvelope`/the outbox-inbox mechanism (`src/core/platform/integration/`, governed by the accepted ADR-PF-011) — a mature, generic, schema-versioned, tenant-scoped, durable at-least-once delivery mechanism. This one is genuinely well-built and correctly kept separate from everything else; it should be treated as a **positive precedent** for parts of a future in-process domain-event design (specifically its `correlation_id`/`causation_id`/`schema_version` fields), not merged with it.

The single most important finding for anyone about to revise ADR-005: **ADR-005's Unit-of-Work design is not landing on a blank slate inside Platform.** Five distinct, live transaction-boundary conventions already coexist in Platform code today (plain inline try/commit, `ApprovalService`'s outer-transaction pattern, a caller-controlled `commit: bool` flag used by two different services, a lightly-used `ServiceBase.commit()` primitive, and — cited for comparison — `project_management`'s module-owned `Resource*UnitOfWork` classes). None of them match ADR-005's proposed "fresh `Session` per transaction, dynamic aggregate tracking" model. `ApprovalService`'s "unit of work" is a *logical* convention (only one method calls `.commit()`) enforced over the *same single process-lifetime `Session`* every other Platform service shares — not a physically isolated transaction. ADR-005's revision needs its own explicit phase for Platform's own services; it cannot assume Platform is exempt from the same convergence problem it's solving for business modules.

Second most important finding: **today's mechanism has zero tenant isolation at the event-dispatch level, and zero test coverage for it.** `DomainChangeEvent` carries no `tenant_id` field at all; no QML binder anywhere filters by tenant; and PostgreSQL RLS — the mechanism this codebase already trusts for tenant isolation everywhere else — protects only outbox/inbox *table reads*, not in-process event *payloads already in memory*. This is tolerable today only because the desktop process holds one active tenant context at a time in a mutable session object, not a contextvar or per-request scope — a model that does not generalize to a concurrent multi-tenant web server without a separate redesign.

Third: **architecture-enforcement tooling already exists in this repo** (real AST-based import-boundary tests under `src/tests/architecture/`), correcting an earlier, less-thorough assumption that no such tooling exists. The gap is coverage, not absence: no existing test checks "Platform must not import a concrete business module," which is exactly where this audit found a real, ungoverned violation (`SqlAlchemyApprovalRepository` importing and joining against `project_management`'s `ProjectORM`).

Fourth: the codebase already shows **organic pressure converging toward exactly what ADR-005 proposes** — `ApprovalService`'s handler-returns-typed-post-commit-events pattern, and (outside Platform, cited for contrast) `project_management`'s `Resource*UnitOfWork` classes with real frozen-dataclass events — both independently reinvented pieces of ADR-005's design without a shared abstraction. This is evidence *for* building the general mechanism, not evidence that it's unnecessary.

This audit implements nothing, changes nothing, and does not update ADR-005. See §29 (Explicit Non-Goals) and §32 (Final Verdict).

---

## 2. Scope and Non-Goals

**In scope:** the actual, current-state architecture of Platform-owned event-like mechanisms — UI-refresh/invalidation, transaction/Unit-of-Work boundaries, audit recording, user notifications, and the durable integration-event boundary — evaluated with direct code evidence, independent of what ADR-005 or any other document claims.

**Out of scope:** a full audit of any business module's own internals. Module code (`project_management`'s `Resource*UnitOfWork`, its CQRS audit findings, etc.) is cited only where it demonstrates how Platform infrastructure is consumed or provides a directly relevant comparison point.

**This audit explicitly does NOT:**

- implement ADR-005
- update ADR-005
- refactor production code
- migrate Project Management, Inventory/Procurement, or Finance
- implement WebSockets or FastAPI
- implement outbox workers
- implement new UnitOfWork infrastructure
- delete legacy events
- rename production code
- move repository packages
- create commits

All read-only. No file under `src/` or `docs/architecture_decisions/` was modified in the course of this work — only this one new document was created.

---

## 3. Audit Methodology

Evidence was gathered by eight parallel, independently-scoped investigations (structural topology; event-mechanism inventory and `domain_events.py` deep-dive; UI refresh/invalidation tracing; transaction/UoW mapping; integration/outbox boundary; dependency-direction and DI/lifecycle/enforcement; multi-tenancy/concurrency/failure-semantics; testing/observability/versioning), each instructed to search by behavior — imports, `.emit(`/`.publish(`/`.dispatch(`/`.subscribe(`/`.notify(` call sites, class names, decorators, session commit/rollback calls, composition-root wiring — rather than by expected filenames, and each required to cite `path:line` evidence and tag every claim `CONFIRMED FACT` or `ARCHITECTURAL INTERPRETATION`. Findings were then cross-checked against ADR-005, ADR-005's execution plan, ADR-PF-008, and ADR-PF-011, and against a prior same-session general codebase audit (which established, among other things, that the `maintenance` module referenced throughout the execution plan's Phase 5 was deleted on 2026-08-20 and no longer exists). Where two investigations produced adjacent or slightly divergent findings (e.g. test-isolation for the `domain_events` singleton), both are reported and reconciled explicitly rather than silently resolved in one direction.

Throughout this document: **CONFIRMED FACT** means directly observed in code with a citable location; **ARCHITECTURAL INTERPRETATION** means a reasoned conclusion drawn from confirmed facts; **RECOMMENDATION** is this audit's own judgment, clearly marked as such and never presented as established fact.

---

## 4. Current Platform Repository Topology

`src/core/platform/` is organized as **repeated vertical capability slices** — `security`, `tenant`, `master_data`, `time_management`, `history`, `events`, `approval`, `data_operations`, `finance`, `integration` — each (mostly) getting its own `domain/`, `application/`, `contract/` (further split into `repositories/`, `port/`, `read/`, `models/`, `interface/`) sub-trees, on top of one shared `infrastructure/persistence/` and one shared `api/desktop/`. This is not a single flat domain/application/infrastructure split at the top of `platform/` — it repeats per capability.

| Package/path | Responsibility | Layer | Key consumers | Dependencies | Architectural concern |
|---|---|---|---|---|---|
| `platform/domain/security/{auth,authorization,identity}` | User/session/role/permission domain model | domain | `platform/application/security/*`; most modules via `TenantContextService`/permission checks | none outside `common/` | none |
| `platform/application/security/*` | Auth flows, MFA, federated identity, role governance, session service | application | desktop API, `ui_qml` controllers | `domain_events` singleton directly (coupling — see §7) | direct singleton import from application layer |
| `platform/domain/tenant/{tenancy,modules}` | Tenant/org scope, module entitlement domain | domain | `platform/application/tenant/*`, virtually every module's `TenantContextService` consumer | — | none |
| `platform/domain/master_data/{org,site,department,employee,party,documents}` | Shared-master entities | domain | `platform/application/master_data/*` | — | none |
| `platform/domain/time_management/{calendar,time}` | Calendars, time/timesheet domain | domain | `platform/application/time_management/*`, PM timesheet consumers | — | none |
| `platform/domain/approval` | Approval request/decision domain | domain | `platform/application/approval/approval_service.py` (ADR-PF-008) | — | none |
| `platform/domain/data_operations/*` | Import/export & report-runtime domain | domain | `platform/application/data_operations/*` | — | none |
| `platform/domain/history/{activity,audit}` | `AuditEntry` (compliance/security audit) + activity-log domain objects | domain | `EnterpriseAuditService`, activity services | — | none |
| `platform/domain/events/platform_events` | `PlatformEvent` — a **governance/tenant-admin audit record**, not a pub-sub event | domain | `tenant_admin_service.py` (its only real construction site) | — | **naming collision**: package literally named `events/`, structurally an audit record, unrelated to `AuditEntry` above and unrelated to `src/core/shared/events/` |
| `platform/domain/events/notifications` | `Notification` — persisted, user-facing in-app notification | domain | `platform/application/events/notifications/notification_service.py` | — | second, unrelated concept sharing the `events/` package name |
| `platform/application/events/notifications/notification_service.py` | Persist notification + best-effort multi-channel fan-out | application | `src/core/shared/notifications/safe_dispatch.py` | `sqlalchemy.orm.Session` directly (a raw infra type held by an application-layer constructor) | application layer typed against a concrete `Session`, not a contract |
| `platform/contract/*` | ABC/Protocol contracts per capability | contract | every application/infrastructure pair in the same capability | — | used as intended — one clean seam per capability |
| `platform/infrastructure/persistence/*` | SQLAlchemy repos/mappers/ORM per capability | infrastructure | `infra/composition/platform_registry.py` | `sqlalchemy` | **no `infrastructure/events/` package exists at all** — confirms no in-process event-bus infra exists yet for Platform |
| `platform/api/desktop/*` | Desktop-facing façade per capability (`Platform*DesktopApi`), mirroring modules' `*DesktopApi` convention | presentation-adjacent | `ui_qml/platform/controllers/*` | application layer | none |
| `platform/access/{domain,application}` | A **second, smaller** access-control home, separate from `domain/security/authorization` | domain+application | `access_control_service.py` | `domain_events` singleton (coupling) | relationship to `domain/security/authorization` not established by this audit — flagged as open (§31) |
| `platform/common/*` (7 files) | `exceptions.py`, `ids.py`, `pydantic.py` (shared validators used by `PlatformEvent`/`Notification`/`AuditEntry` alike), `service_base.py`, `runtime_access.py`, `code_generation.py` | cross-cutting utility | everything under `platform/` | pydantic, stdlib | **not** a dumping ground — small, single-purpose, disciplined |
| `platform/finance/{money,periods}` | Money/currency value objects, financial-period domain | domain-ish shared | PM Finance, `platform/application/finance/*` | — | sits directly under `platform/`, not `platform/domain/` — placement inconsistent with every sibling capability |
| `platform/integration/*` (8 files, flat) | ADR-PF-011's outbox/inbox (`events.py`, `delivery.py`, `canonical_json.py`) **plus** an unrelated capability-gating/cross-module-navigation concern (`module_registry.py`, `resolver.py`, `cross_module_reference.py`) | infra+contract mixed in one flat package | `infra/integration/*Dispatcher` classes, PM Finance consumers | — | only Platform package that is flat rather than domain/application/contract/infra-split; two unrelated concerns share one directory name |
| `src/core/shared/events/{domain_events.py, signal.py}` | The ADR-005 target: `DomainEvents`/`Signal`/`DomainChangeEvent` | — | 66+ files across Platform + modules (25 confirmed inside `platform/` alone) | none | the one package genuinely living **outside** `platform/`, in the repo's lower `shared` tier |
| `src/core/shared/audit/audit_recorder.py`, `.../notifications/safe_dispatch.py`, `.../activity/activity_recorder.py` | Three **identically-shaped duck-typed facade functions** (`getattr(owner, "_enterprise_audit_service"/"_notification_service"/"_activity_service", None)`) delegating to Platform's real services | shared helper | callers across modules wanting an optional, DI-light collaborator | `platform/common/exceptions` only | not duplicate implementations — a deliberate, repeated house idiom worth a naming/consistency decision later, not a defect |
| `src/infra/platform/security_audit_recorder.py` (`DurableSecurityDenialRecorder`) | Persists `AuditEntry`/`SecurityDenialEvent` in a session **isolated from the business transaction**, so denial evidence survives a rollback | infrastructure | authorization-denial call sites | own `sessionmaker` | a genuine, deliberate third *persistence strategy* for the same `AuditEntry` type — good precedent for "some records must escape the triggering transaction's fate," worth keeping |
| `src/infra/composition/{app_container.py, platform_registry.py, repositories.py}` | Composition root: builds `RepositoryBundle`, per-capability service bundles | infrastructure/composition | `ui_qml/shell/app.py` | `sqlalchemy`, every module's registry | confirmed single process-lifetime `Session` |
| `src/ui_qml/platform/controllers/common/workspace_controller_base.py` | Shared base for Platform's own QML workspace controllers | presentation | Platform QML controllers | `domain_events` (subscribe side) | one of **three** independently-implemented `workspace_controller_base.py` copies (Platform, `project_management`, `inventory_procurement`) — see §8 |
| `src/ui_qml/platform/controllers/admin_console/{domain_event_binder.py, signal_binder.py, refresh_coordinator.py}` | Three separate, co-located UI-refresh-coordination files for **one** controller | presentation | `admin_console_controller.py` | `domain_events` | three different-sounding mechanisms in one folder for one screen; `domain_event_binder.py` self-identifies as a temporary legacy facade |

**Duplicate/competing infrastructure — resolved, not duplicated.** The audit and notification "duplication" question resolves cleanly: `EnterpriseAuditService`/`AuditEntry` is the one real compliance/security audit trail; `audit_recorder.py` is a thin duck-typed facade over it, not a second implementation; `DurableSecurityDenialRecorder` reuses the same `AuditEntry` type through a deliberately separate transaction for a specific, legitimate reason (denial evidence must outlive a rollback). `PlatformEvent` is a **fourth, narrower, unrelated** record (tenant-governance action log, one real construction site in `tenant_admin_service.py`) that happens to share the word "events" — a real naming collision, not a duplicate mechanism. `NotificationService`/`safe_dispatch.py` is the same facade idiom as the audit case, confirmed as a deliberate repeated convention (the third instance, `activity_recorder.py`, matches exactly).

**Is `src/core/shared/events/` itself "Platform"?** No convention states this explicitly, but structurally `src/core/shared/` sits as a peer of `src/core/platform/` under `src/core/{shared,platform,modules}/`, consumed by both — i.e. it behaves as a genuinely lower, more-shared tier than Platform, not a Platform subpackage. This matters directly for §22: the existing `shared/` tier is already the "below Platform, below modules" home, and ADR-005 placing new contracts there (not under `platform/`) is consistent with existing convention, not a deviation.

**Boundary enforcement — holds for domain, looser for application.** Grep confirms zero `sqlalchemy`/`ui_qml`/`PySide` imports anywhere in `platform/domain/**`. The application layer is looser: `NotificationService` types a constructor parameter directly as `sqlalchemy.orm.Session` rather than a repository contract — a smaller-scale instance of exactly the anti-pattern ADR-005 §2.5/§2.6 had to correct for its own proposed handlers. 25 of the 66 codebase-wide `domain_events` singleton imports live inside `platform/` itself — Platform is not exempt from the coupling problem ADR-005 targets.

---

## 5. Current Platform Responsibilities

Mapping each significant Platform responsibility to its actual current ownership:

| Responsibility | Current owner | Classification |
|---|---|---|
| Access/security, tenancy, identity | `platform/domain/security/*`, `platform/domain/tenant/*` | Correct Platform responsibility |
| Shared-master data (org/site/department/employee/party/document) | `platform/domain/master_data/*` | Correct Platform responsibility |
| Approval workflow + transaction ownership | `platform/application/approval/approval_service.py` (ADR-PF-008) | Correct Platform responsibility; also Platform's most mature transaction-boundary precedent (§9) |
| Compliance/security audit trail | `platform/domain/history/audit` + `EnterpriseAuditService` | Correct Platform responsibility |
| Tenant-governance action log | `PlatformEvent` | Correct Platform responsibility, **misleadingly named** (§21) |
| User-facing in-app notifications | `Notification`/`NotificationService` | Correct Platform responsibility, unrelated to domain events |
| Durable cross-module integration events | `platform/integration/*` (ADR-PF-011) | Correct Platform responsibility, mature, well-separated |
| UI refresh / view invalidation | `domain_events.py`/`Signal`, `workspace_controller_base.py`, `*_domain_event_binder.py` | **Unclear ownership / legacy concern** — functions as UI invalidation but is named and structured as a generic cross-cutting "domain events" mechanism, imported directly by both Platform and module application-layer code with no capability boundary |
| Transaction/Unit-of-Work boundary | No single owner — five distinct live conventions (§9) | **Unclear ownership** — no canonical Platform-wide answer exists today |
| Dependency injection / composition | `src/infra/composition/{app_container.py, platform_registry.py}` | Correct Platform (infra) responsibility, and the actual working DI convention (§13) |
| Serialization / DTO conversion | Per-capability, hand-written `serialize_*`/`build_*` at the desktop-API layer (confirmed by the earlier same-session CQRS audit, cited for context only) | Application/presentation-boundary concern, not Platform-core |
| Repositories / database session management | `RepositoryBundle` (one process-lifetime `Session`), per-capability `Sqlalchemy*Repository` | Correct Platform (infra) responsibility, but architecturally singular (one session for the whole process) — directly relevant to §9's UoW findings |
| Logging/observability for event-like mechanisms | Ad hoc, three independent hand-written try/except-log sites; no metrics, no tracing | **Legacy/absent concern** — no owner, no convention (§19) |

---

## 6. Event Mechanism Inventory

Every Platform-owned event-like mechanism found, classified by actual producer/consumer behavior rather than name:

| Mechanism | Location | Owner layer | Producers (sample) | Consumers | Sync/async | Before/after commit | Durable? | Tenant-aware? | Failure behavior | Actual purpose |
|---|---|---|---|---|---|---|---|---|---|---|
| `Signal[T]` | `src/core/shared/events/signal.py:9-56` | shared primitive | `DomainEvents`, module-owned `resource_master_changed`, etc. | anything holding a reference | sync, in-process | commit-agnostic (caller decides) | no | no | Qt "already deleted"/`ReferenceError` isolated+pruned; **any other exception propagates and aborts remaining subscribers mid-loop** | Generic Observer primitive — classification depends entirely on the caller |
| `DomainEvents`/`DomainChangeEvent`/`domain_events` singleton | `src/core/shared/events/domain_events.py:1-251` | shared, imported everywhere | 66+ application-layer call sites (25 inside Platform) | `PlatformWorkspaceControllerBase`, `domain_event_binder.py`, per-module QML binders | sync | **after** commit at every sampled real call site | no | **no** (`DomainChangeEvent` has no `tenant_id` field) | inherits `Signal`'s fail-fast-on-non-Qt-exception behavior; no wrapping try/except at most emit call sites | **LEGACY GLOBAL NOTIFICATION functioning as DESKTOP UI SIGNAL / VIEW INVALIDATION** |
| `PlatformWorkspaceControllerBase._subscribe_domain_change`/`_subscribe_domain_signal` | `src/ui_qml/platform/controllers/common/workspace_controller_base.py:184-234` | UI (`ui_qml`) | n/a (consumer-side registration) | itself → calls `refresh()` | sync, Qt main thread implied | after commit | no | no (filters on `scope_code`/`entity_type`/`category` strings only) | per-callback disconnect wrapped in try/except-log; one bad disconnect doesn't block others | VIEW / READ-MODEL INVALIDATION |
| `admin_console/domain_event_binder.py::bind_domain_events` | `src/ui_qml/platform/controllers/admin_console/domain_event_binder.py:21-38` | UI | n/a | `PlatformAdminWorkspaceController` (coalesces 9 sub-controllers) | sync | after commit | no | no | delegates to `Signal`/base | VIEW INVALIDATION — **self-documented as a temporary legacy facade, scheduled for removal in phase "R2"** |
| `ApprovalService._emit_handler_events`/`_emit_signal_safely` | `src/core/platform/application/approval/approval_service.py:294-312` | Platform application | `ApprovalHandlerResult.post_commit_events` (handler-authored `(signal_name: str, payload: str)` pairs) | resolves via `getattr(domain_events, signal_name)` then `.emit(payload)` | sync | after commit (ADR-PF-008's own rule) | no | no | **own** try/except-log per event — the only Platform site that defends against `Signal.emit()`'s fail-fast default | POST-COMMIT APPLICATION REACTION, reflectively re-entering the legacy notification mechanism via string keys |
| `PlatformEvent` + ORM mapper | `platform/domain/events/platform_events/platform_event.py`, `.../infrastructure/persistence/mappers/events/platform_events/platform_events.py:31-40` | Platform domain+infra | `tenant_admin_service.py` | audit readers/reports | n/a — persisted row | n/a | **yes**, own table, append-only enforced | **yes**, required field | n/a (a DB write, not a dispatch) | **AUDIT EVENT** — never emitted/subscribed to as an event despite the package name |
| `Notification`/`NotificationService` | `platform/domain/events/notifications/notification.py`, `.../application/events/notifications/notification_service.py:35-72` | Platform domain+application | `safe_dispatch_notification`, direct callers | `NotificationChannel` implementations, in-app notification list | sync | caller-controlled via explicit `commit: bool` | **yes**, persisted | tenant_id optional | per-channel try/except-log; one channel failure doesn't block others | **Business feature** (user-facing notification with delivery fan-out), not an architecture-level event bus |
| `IntegrationEventEnvelope`/outbox-inbox | `platform/integration/events.py`, `delivery.py` | Platform integration | source-module outbox writers | `ApprovedTimeFinancialDispatcher`, `ProcurementFinancialDispatcher` (`src/infra/integration/`) | async-capable, durable | written **during** the transaction, delivered after | **yes**, by design | **yes** | bounded retry + dead-letter | **DURABLE OUTBOX EVENT** — see §11 |
| Native `PySide6.QtCore.Signal` on `PlatformWorkspaceControllerBase` | `workspace_controller_base.py:22-28` | UI, Qt framework | the controller itself | QML bindings | sync, Qt main thread | n/a (UI state, not domain state) | no | no | Qt's own signal/slot semantics | DESKTOP UI SIGNAL, correctly scoped — but shares its bare name with the unrelated `shared/events/signal.py::Signal`, requiring an import alias (`Signal as DomainSignal`) in the same file |

**Confirmed:** no `@dataclass(frozen=True)` class named `*Changed`/`*Created`/`*Approved`/`*Completed`/`*Assigned`/`*Reversed`/`*Posted`/`*Rejected` exists anywhere under `src/core/platform/`. **Platform itself owns zero typed domain-event classes today** — narrower and more precise than saying "the whole codebase is greenfield" (it is not, once `project_management`'s module-owned events are counted), but true for Platform specifically.

---

## 7. Current DomainEvents Mechanism — Deep Dive

Answering the twenty specified questions with direct evidence:

1. **Mutable global singleton** — CONFIRMED. `domain_events = DomainEvents()` at module scope (`domain_events.py:243`), instantiated once at import time. No factory, no DI, no per-tenant instance.
2. **Who imports it** — CONFIRMED, by layer. Application services (Platform and module) and UI controller base classes. **Zero hits under any `domain/` package** — the coupling is confined to application+UI layers.
3. **Subscription registration** — a fresh closure per binder call (`_subscribe_domain_change`, `bind_domain_events`, etc.).
4. **Disposal** — via Qt's native `destroyed` signal on `PlatformWorkspaceControllerBase`, disconnecting every tracked subscription; each disconnect independently try/except-wrapped.
5. **Duplicate subscription possible?** — **Yes, in practice.** `Signal.connect()` dedups only by exact callable identity; every real binder constructs a *fresh* closure per call, so calling the same subscribe helper twice on one controller instance genuinely double-subscribes. Nothing prevents this if a setup path runs twice.
6. **Weak or strong references?** — **Strong.** `Signal._subscribers` holds strong references, including bound methods (which strongly reference `self`). Leak mitigation is reactive, not preventive: a stale Qt callback is only pruned the *next time that specific signal fires*, and a signal that never fires again leaves the dead reference for the process's remaining life.
7. **Errors propagate or isolated?** — **Narrower isolation than it looks.** `Signal.emit()` catches exactly two cases (Qt-deleted-object `RuntimeError`, `ReferenceError`); every other exception propagates immediately and **aborts the remaining subscribers in that call's snapshot loop.** None of the sampled production emit sites (`session_service.py`, `employee_service.py`) wrap their own emit call — only `ApprovalService._emit_signal_safely` does.
8. **Dispatch ordering?** — insertion order per signal; no documented guarantee.
9. **Re-entrant?** — **Yes, and depth-first by accident.** The lock is released before the subscriber loop runs, so a subscriber calling `.emit()` again does not deadlock — but the nested call runs to full completion before the outer loop's next subscriber runs. This is the *opposite* of the breadth-first ordering ADR-005 proposes for its own new mechanism; today's actual behavior is an accident of implementation, not a design choice.
10. **Can events recursively generate events?** — mechanically yes (via re-entrant emit, above); no code path currently does this on purpose.
11. **Tenant context included?** — **No.** `DomainChangeEvent` has no `tenant_id` field; every sampled `Signal[str]` payload is a bare opaque ID.
12. **Correlation/causation available?** — No, absent from `Signal`, `DomainChangeEvent`, `PlatformEvent`, and `Notification` alike.
13. **Dispatch observable/logged?** — `signal.py` itself contains zero `logger` calls (not on emit, connect, disconnect, or stale-pruning). The only logging near this mechanism lives in `ApprovalService`'s wrapper and the UI controller's own DEBUG-level subscribe/refresh logs.
14. **Before or after commit?** — **After, at every sampled site** (`session_service.py:138→142`, `employee_service.py:138→145`, `:239→250-251`; `ApprovalService` by explicit ADR-PF-008 design).
15. **Business-event mechanism or UI-refresh mechanism?** — ARCHITECTURAL INTERPRETATION, strongly evidenced: every real Platform payload is a bare ID with no business-fact content, every real consumer only decides whether to call `refresh()`, dispatch is always post-commit. This is textbook invalidation semantics wearing a "domain events" name. Countervailing evidence: `ApprovalService` and module code are already straining against it by inventing typed/richer payloads on top — evidence of unmet need, not evidence the current mechanism already meets it.
16. **Leaks UI/PySide concerns into application/domain code?** — No PySide leakage into `domain/` (confirmed zero imports); the `Signal` primitive itself is framework-agnostic. The leakage runs the other direction: application-layer business code depends directly on a mechanism whose only real consumers are UI controllers.
17. **Does naming accurately reflect its role?** — No. See §21.
18. **Producer → mechanism → consumer map** — for Platform's own signals, see §8's end-to-end traces (`organizations_changed`, `employees_changed`).
19. **Coarse fan-out, confirmed concretely for Platform's own signals:** `documents_changed` has **9 confirmed emit sites** across `document_service.py` (structure creation, metadata update, upload, delete) and `document_integration_service.py` (link/unlink) — at least 4-5 semantically distinct operations behind one signal. `organizations_changed` has 3 sites spanning 2 different services. `employees_changed` is narrower (2 sites: create, update) but even there the *consumer* side discards the entity ID and calls a full, undifferentiated `refresh()` regardless.
20. **Silent gap in the `commit: bool` pattern:** `OrganizationService.create_organization`'s emit is gated by the same `commit: bool` parameter that governs whether the method commits at all — if a caller passes `commit=False` (composing into an outer transaction), the row is flushed but **no event is ever emitted at that call site**, and nothing performs a deferred emit later. This is a real "callers must remember to emit" gap in the current mechanism, not a hypothetical one.

---

## 8. UI Refresh / View Invalidation Architecture

**Platform's base controller** (`PlatformWorkspaceControllerBase`, `src/ui_qml/platform/controllers/common/workspace_controller_base.py`): `_subscribe_domain_change(*entity_types, scope_code=None, category=None)` does not subscribe to named per-entity signals directly — it subscribes one closure to the single generic bridge signal `domain_events.domain_changed`, then filters by `category`/`scope_code`/`entity_type` in-process before calling `_request_domain_refresh()`. Disposal is automatic and reliable: `self.destroyed.connect(self._disconnect_domain_event_subscriptions)` guarantees every subscription is disconnected when Qt destroys the controller, each disconnect independently try/except-wrapped. Refresh scheduling has anti-thundering-herd logic: it no-ops for never-loaded lazy controllers, and defers into a pending-refresh flag while `is_loading`/`is_busy`, flushing once that clears.

**Not a shared base — three independent reimplementations.** `project_management`'s and `inventory_procurement`'s `workspace_controller_base.py` both duplicate this ~50-80 line mechanism rather than inheriting from `PlatformWorkspaceControllerBase` or a common ancestor (confirmed: no import/subclass relationship). They diverge *functionally*, not just cosmetically: `project_management`'s version uses a `QTimer`-based debounce (a genuinely different scheduling algorithm) where Platform's and `inventory_procurement`'s use flag-based deferral (matching each other closely, including method names and line-number regions). Disposal via `destroyed.connect(...)` is the one consistent invariant across all three.

**`admin_console/domain_event_binder.py`** (39 lines, read in full): its own docstring explains the "why" — `PlatformAdminWorkspaceController` composes 9 single-entity sub-controllers under one coalesced refresh cycle rather than each subscribing individually. It explicitly preserves "byte-for-byte the same subscription list and behavior" as a prior file and is **self-scheduled for removal in phase "R2."** It subscribes to 8 of Platform's 11 named signals (`organizations_changed`, `calendars_changed`, `sites_changed`, `departments_changed`, `employees_changed`, `auth_changed`, `parties_changed`, `documents_changed`), each routed through one closure that **discards the payload entirely** and calls `_request_domain_refresh()` unconditionally. **Not wired here:** `access_changed`, `modules_changed`, `approvals_changed` — whether these three are consumed elsewhere was not established by this audit (§31).

**End-to-end trace, `organizations_changed`:**
```
OrganizationService.create_organization(...)
  → self._organization_repo.add(...) / record_audit_entry(..., commit=False)
  → if commit: self._session.commit()  else: self._session.flush()
  → except IntegrityError/Exception: self._session.rollback(); raise
  → if commit: domain_events.organizations_changed.emit(organization.id)
  → _wire_bridges() bridge fires domain_events.domain_changed(DomainChangeEvent(category="shared_master", scope_code="platform", entity_type="organization", entity_id=organization.id, source_event="organizations_changed"))
  → admin_console binder's direct subscription, OR PlatformWorkspaceControllerBase's filtered domain_changed subscription
  → controller._request_domain_refresh() → refresh() → QML re-binds whatever refresh() repopulates
```
Confirmed: the emit call is textually after the try/except that owns commit/rollback — an exception returns via `raise` inside the except block, so emit is unreachable on failure; it **cannot fire after a rollback**, and never fires before commit. It **can** be silently skipped entirely when `commit=False` (§7, item 20). The payload is `organization.id` only — no tenant_id — and refresh is broad, not granular.

**End-to-end trace, `employees_changed`:** same shape (`employee_service.py:138→145`), but with no `commit: bool` parameter — commit and emit are unconditional at this call site, so this particular one doesn't have the silent-skip gap.

**Duplicate/leak risk:** no evidence of duplicate subscription from the same controller instance in practice (each binder is invoked once per controller construction), though nothing structurally prevents it if a binder were invoked twice. Disposal is reliable by construction across all three controller-base copies.

**Granularity verdict:** even where the *emitter* side is relatively narrow (`employees_changed`, 2 sites), the *consumer* side never exploits it — neither `admin_console`'s binder nor `PlatformWorkspaceControllerBase`'s filter path passes the entity ID through to `refresh()`. Granularity is lost twice: once by coarse emitters (`documents_changed`), and again by consumers that discard whatever ID they do receive.

---

## 9. Transaction and Unit of Work Architecture

**`ApprovalService.approve_and_apply`** (`src/core/platform/application/approval/approval_service.py:212-254`) is Platform's most mature transaction-boundary precedent:

- Nobody explicitly "opens" a transaction (SQLAlchemy autobegins); `ApprovalService` owns the *close* — it is the only caller of `.commit()`/`.rollback()` for this operation.
- The apply handler (`Callable[[ApprovalRequest], ApprovalHandlerResult | None]`, registered via `register_apply_handler`) runs **before** commit and may stage repository/domain writes. Nothing structural prevents a handler from calling `.commit()` itself — the "handlers must not commit" rule is a documented convention (ADR-PF-008), not a type-level guarantee.
- **No aggregate-event collection exists at all** — no `RecordsDomainEvents`, no `tracked_aggregates()`, nothing resembling ADR-005 §2.7's draining loop. Instead, the handler itself hand-constructs and *returns* `ApprovalHandlerResult(post_commit_events=(signal_name: str, payload: str), ...)` — a third, distinct, even-less-typed event shape than `DomainChangeEvent`.
- Commit happens after handler execution, status mutation, and a `commit=False`-staged audit row — the audit row rides in the *same* transaction as the business mutation.
- Post-commit dispatch (`_emit_handler_events` → `domain_events.<signal_name>.emit(...)`, then `approvals_changed.emit(...)`, then notification dispatch) runs strictly after a clean commit; none of it runs if an exception propagated.
- Handler exceptions and commit-failure exceptions share **one** except block (`except Exception: rollback(); raise`) — no distinction between "the business logic was wrong" and "the database failed."
- **No dispatch-round cap or re-entrancy handling exists** — `_emit_handler_events` iterates a fixed tuple exactly once; nothing here would detect or bound a handler that itself triggered another approval.
- **A second, independent commit hides inside "post-commit."** `_notify_approval_decided` → `safe_dispatch_notification` → `NotificationService.dispatch(commit=True)` commits *again* on the **same shared `Session`** — "post-commit" here means "a second transaction on the same session object," not merely "reacting to an already-closed one." This only works safely because it happens after the approval's own commit already succeeded.

**Other Platform commit sites, grouped by pattern (not by file):**

| Pattern | Representative | Commit owner | Rollback? | Event dispatch timing | Scope |
|---|---|---|---|---|---|
| (a) Inline try/commit/except-rollback per method | `time_management/time/timesheet_entries.py` | The method itself | Per-method, inconsistent presence | Ad hoc or absent | Platform |
| (b) Outer-transaction-owns-everything + manual post-commit result object | `ApprovalService.approve_and_apply`/`.reject` | `ApprovalService` | Yes, unconditional | Strictly post-commit, via `ApprovalHandlerResult` | Platform |
| (c) Caller-controlled `commit: bool` flag | `ApprovalService.request_change`, `NotificationService.dispatch` | Whoever passes `commit=True` | Only on the commit-owning path | Deferred / caller-decided | Platform |
| (d) `ServiceBase.commit()` primitive | `service_base.py`, 1 real subclass (PM's `reporting_service.py`) | Subclass caller | Generic try/rollback | None — no event concept at all | Platform (shared, lightly used) |
| (e) `Resource*UnitOfWork.execute()` (cited for comparison, module-owned) | `project_management/application/resources/resource_master_uow.py` | The UoW object | Yes | Post-commit, typed dataclass + legacy Signal dual-emit | Module |
| (f) Dead `session_scope()` | `src/infra/persistence/db/unit_of_work.py` | N/A — zero callers anywhere in `src/` (re-confirmed) | try/commit/except-rollback/finally-close, unreachable | N/A | Shared infra, unused |

**None of (a)-(e) is a structural Unit of Work in ADR-005's sense** (fresh `Session` per transaction, dynamic aggregate tracking, dispatcher-mediated event collection). `SessionLocal` (the real `sessionmaker` at `src/infra/persistence/db/session_factory.py`) has exactly three references in all of `src/`: its own definition, the dead `session_scope()`, and one call at process startup in `src/ui_qml/shell/app.py:59` — used **once**, ever, to build the single long-lived `Session`. **ADR-005's proposed `UnitOfWorkFactory` closing over `SessionLocal` would be the first real per-transaction use of it in this codebase's history.**

**Actual `ApprovalService` flow:**
```text
Command: approve_and_apply(request_id, note)
    ↓
require_permission("approval.decide") + self-decision guard
    ↓
apply handler runs (pre-commit) — may stage writes on the SAME shared Session,
    hand-builds ApprovalHandlerResult(post_commit_events=(signal_name, payload), ...)
    ↓
request.status = APPROVED; approval_repo.update(request)
    ↓
record_audit_entry(..., commit=False, fail_closed=True)   [staged, same transaction]
    ↓
Commit owner: ApprovalService — self._session.commit()
    (ANY exception above → self._session.rollback(); raise — one shared except block)
    ↓
Post-commit (only if commit succeeded):
    ├── _emit_handler_events → domain_events.<signal_name>.emit(payload)  [isolate-and-continue, ad hoc]
    ├── domain_events.approvals_changed.emit(request.id)                 [same wrapper]
    └── _notify_approval_decided → safe_dispatch_notification
          → NotificationService.dispatch(commit=True)  [a SECOND, independent commit
            on the SAME shared Session, itself try/except-log wrapped]
```

**Are any of these incompatible if combined in one request?** Concretely yes: a single "approve this request" action already spans two sequential, non-atomic commits on the same session. If the second (notification) commit failed, the exception is caught and logged inside `dispatch`'s already-wrapped channel loop and never surfaces — the notification silently doesn't exist while the approval is already durably committed. This is an intentional consequence of layering pattern (b) and (c) together, not a bug, but it is a direct illustration of what happens when two different transaction-boundary conventions compose without a shared model.

---

## 10. Existing Typed Event Patterns

None originate in Platform code. The only typed, tenant-scoped, frozen-dataclass event pattern in the codebase (`ResourceMasterChanged`/`ResourceCapabilityChanged`, `project_management/application/resources/resource_*_uow.py`) is module-owned, cited here only for contrast — it independently reinvents a UoW-shaped commit/rollback wrapper, a typed frozen-dataclass event (tenant_id, version, change_type), and post-commit dispatch wrapped in try/except-log that fires **both** the new typed event **and** the legacy `domain_events.resources_changed` signal.

Platform's closest analogues are architecturally distinct, not precedents for the same concept:

- `PlatformEvent` — typed (Pydantic-validated) but persisted/audit, never dispatched.
- `Notification` — typed and persisted, a user-facing feature, never subscribed to as a domain fact.
- `ApprovalHandlerResult.post_commit_events` — the closest thing to a "typed post-commit event" in Platform, but its items are a generic `(signal_name: str, payload: str)` pair — **less** typed than `DomainChangeEvent`, adding a layer of string-keyed reflection (`getattr(domain_events, signal_name)`) on top of it.

**Answering the required question directly: is the proposed Platform architecture greenfield, partially implemented, or competing with existing patterns?** For Platform specifically: **greenfield** — zero typed domain-event classes exist under `src/core/platform/` today. But Platform is **not** free of a competing transaction-boundary pattern: `ApprovalService` (ADR-PF-008, accepted and implemented) already occupies almost the same conceptual space ADR-005's `UnitOfWork`/post-commit dispatch is designed to formalize, without ADR-005 referencing it anywhere. Any ADR-005 revision must treat this as "partially implemented, under a different name and a narrower scope" for Platform's transaction model, even though it can correctly treat Platform's *event typing* as greenfield.

---

## 11. Integration Events / Outbox Boundary

**`IntegrationEventEnvelope`** (`src/core/platform/integration/events.py:17-94`) is a frozen (`extra="forbid"`), Pydantic `BaseModel` — not a dataclass — with `event_id`, `event_type`, `schema_version: int` (validated ≥1), `tenant_id` (required), `organization_id: str | None`, `aggregate_type`, `aggregate_id`, `aggregate_version: int`, `occurred_at` (normalized to UTC), `correlation_id: str | None`, `causation_id: str | None`, `payload: dict[str, JsonValue]`. Two computed hashes: `payload_hash` (over payload only) and `envelope_hash` (over the full model, used for conflict detection). `inbox_deduplication_key(consumer_name)` hashes `{consumer, tenant_id, event_id}` — matches ADR-PF-011's stated dedup design exactly.

**Delivery ownership is transaction-neutral by design.** `IntegrationOutboxService`/`IntegrationInboxService` (`platform/application/integration/delivery_service.py`) never call `session.commit()` themselves (docstring-confirmed) — they call `repository.add()`/`.update()`/`.flush()` only. The calling module's own application service must commit the outbox write in the same transaction as its business mutation; Platform provides the mechanism, the module owns the atomicity. (This audit did not chase into Time/Procurement code to verify they actually do this correctly — that's module-scope, out of bounds here — but the *contract* itself is correctly shaped to make that guarantee possible.)

Claim/lease logic (`claim_batch`/`mark_published`/`mark_failed`, `lease_token`/`lease_expires_at`), retry/backoff (`IntegrationRetryPolicy`, exponential, generic and injected), and dead-lettering (`attempt_count >= max_attempts`, both outbox and inbox sides) are **genuinely generic — not coupled to Time/Procurement vocabulary.** Every class operates on opaque `owner_module`/`consumer_name` strings and the generic envelope; a third module could reuse this by injecting its own repository and a name string, with no subclassing or copying required. This is solid, reusable Platform infrastructure.

**`module_registry.py`/`resolver.py`** (both modified 2026-08-20, the newest files in this package) are an **unrelated concern** sharing the directory: `ModuleRegistry` is a capability/entitlement gateway, `IntegrationResolver` resolves soft cross-module reference links for UI deep-linking. They don't touch delivery semantics; they simply share a folder name with the durable-messaging code, which is a naming/cohesion finding (§4), not a delivery-semantics one.

**Tenant/versioning comparison:**

| Mechanism | Tenant field | Schema/version field | Immutable? |
|---|---|---|---|
| `IntegrationEventEnvelope` | `tenant_id: str` (required) + `organization_id: str \| None` | `schema_version: int`, `aggregate_version: int` | Yes (Pydantic frozen) |
| `PlatformEvent` | `tenant_id: str` (required) | none | Not enforced immutable at the dataclass level (append-only enforced at the repository level instead, per test evidence in §17) |
| `Notification` | `tenant_id: str \| None` (optional) | none | Not enforced immutable |
| `DomainChangeEvent` | **none at all** | none | `frozen=True` dataclass, but nothing tenant-related to be immutable about |

**Boundary separation — clean, confirmed.** No blurring found in either direction: `IntegrationInboxService`/`IntegrationOutboxService` never touch `Signal`/`domain_events`/`Notification`/`PlatformEvent`, and none of those ever construct or reference `IntegrationEventEnvelope`. Five genuinely separate code paths, no shared base class, no shared dispatch mechanism.

**What a future domain-event design should and shouldn't reuse:** **should** reuse the `correlation_id`/`causation_id` pair — already a live, proven convention in production (e.g. a receipt event's `causation_id` pointing at its originating purchase order) — and the simple monotonic `schema_version: int` convention. **Should not** import the full envelope shape (transport wrapper, hashing, dedup keys) into an in-process `DomainEvent` — that's solving a durable, cross-process, at-least-once problem an in-process, same-transaction event doesn't have. ADR-PF-011 already states, and this code confirms, that domain events and integration events meet only at a deliberate mapping step, never a shared class hierarchy — this audit found no evidence to revisit that.

---

## 12. Dependency Direction and Layering

**Platform domain/application → UI/ORM:** zero `PySide6`/`ui_qml` imports anywhere in `platform/domain/` or `platform/application/`; zero real `sqlalchemy`/`Session` imports in `domain/`. 32 files in `application/` type a constructor parameter as `sqlalchemy.orm.Session` — this is the codebase's established, accepted constructor-injection convention, not a violation.

**Platform → specific business module — two real inversions, differently governed:**

- `platform/application/time_management/calendar/assignment/calendar_assignment_service.py:205,248` imports `project_management.domain.calendar.assignment` types (local, function-scoped). **Classification: acceptable transitional dependency** — explicitly governed by [ADR-004](../../architecture_decisions/ADR-004-calendar-assignment-split-ownership.md).
- `platform/infrastructure/persistence/repositories/approval/approval.py:6,66-175` — `SqlAlchemyApprovalRepository` imports `ProjectORM` from `project_management.infrastructure.persistence.orm.project` directly and joins against it in `select()` statements (tenant/org scoping, not incidental). **Classification: clear violation / architectural debt.** No ADR governs this one. Platform's own approval infrastructure is structurally coupled to one business module's concrete ORM table — a second module needing project-scoped approval visibility has no contract to extend.

**Business modules → Platform:** expected direction, contract-respecting; no sampled module reaches into `platform.infrastructure.*` directly, bypassing Platform's own application/contract layer.

**`shared/` ↔ `platform/` — one real inversion:** `src/core/shared/security/decorators.py:7` imports `platform.application.security.authorization.enforcement.permission_checks`, and `src/core/shared/audit/audit_recorder.py:5` imports `platform.common.exceptions`. Per this codebase's own convention (`shared` is the lower, framework-agnostic layer both Platform and modules build on), this is backwards. **Classification: requires decision** — plausibly `platform/common/exceptions` is simply misplaced (base exception types that belong in `shared/`), which would resolve this cheaply. Zero `shared → src.core.modules.*` imports found.

| Finding | Classification |
|---|---|
| `calendar_assignment_service.py` → PM domain | Acceptable transitional dependency (ADR-004 governs it) |
| `approval.py` → `ProjectORM` | **Clear violation** — no governing ADR |
| `shared/security/decorators.py` → `platform/...` | Requires decision |
| `shared/audit/audit_recorder.py` → `platform/common/exceptions` | Requires decision |
| Application layer → `sqlalchemy.orm.Session` (32 files) | Intentional, established convention |
| Modules → Platform contracts/services | Intentional, correct direction |

---

## 13. Lifecycle / Composition / Dependency Injection

`domain_events = DomainEvents()` (`domain_events.py:243`) is a **true global singleton**, instantiated once at import time with no composition-root involvement — architecturally distinct from everything else in this codebase's actual DI convention. `NotificationService` and `ApprovalService` are both constructed **inside** `src/infra/composition/platform_registry.py`, receiving `session`, repositories, `tenant_context_service`, `user_session` as explicit constructor parameters — the codebase's real, working DI pattern. `domain_events` doesn't follow it; it's reached by direct import at 66+ sites, never passed in.

**Test isolation — reconciled finding across two independent investigations.** One investigation found the direct unit test of `Signal`/`DomainEvents` (`src/tests/platform/test_domain_events.py`) manually calling `.disconnect()` at the end of its own test body with no enforced teardown — a risk if an assertion above that line ever fails. A second investigation found that `src/tests/conftest.py:37-43` has an **autouse fixture calling `domain_events.reset()` both before and after every test** — meaning the suite-wide risk is actually low despite that one test's self-contained fragility. Both are true simultaneously: the global singleton would be a real cross-test leak risk *without* the conftest fixture, and the conftest fixture is exactly the kind of structural mitigation a bare module-level singleton makes necessary in the first place — evidence for, not against, moving off the singleton pattern.

**Composition-root convention for anything new:** based on `ApprovalService`/`NotificationService`, a new Platform-owned dispatcher/bus should be constructed inside `platform_registry.py`, receiving its collaborators as constructor parameters, threaded into consumers the same way `notification_service=notification_service` is passed into `ApprovalService`'s constructor today. It should **not** follow `domain_events`'s bare-singleton pattern, which is the outlier here, not the norm.

---

## 14. Multi-Tenancy

**Tenant context is ambient via a shared mutable object, not a contextvar or explicit parameter.** `TenantContextService.require_active_scope_ids(...)` (`platform/application/tenant/tenancy/tenant_context.py`) reads `_active_tenant_id`/`_active_organization_id` off a `UserSessionContext` instance (`platform/domain/security/auth/session.py`) — plain mutable instance attributes, set via `set_principal`/context-switch calls, no `contextvars.ContextVar`, no thread-local. This is safe today only because the desktop process is single-user/single-active-tenant-at-a-time; **it does not generalize to a concurrent multi-tenant server without a separate redesign** (relevant to §23, not decided here).

**No mechanism filters by tenant at dispatch time.** Grep for `tenant_id` inside every `*domain_event_binder*.py` file returns zero matches. `DomainChangeEvent` has no `tenant_id` field at all; `ApprovalService`'s emitted signal payloads carry no tenant_id either (only the separate notification side-channel passes `tenant_id=self._active_tenant_id()` into `safe_dispatch_notification`). **Today's UI-refresh mechanism carries no tenant identity and enforces no tenant boundary at dispatch time — full stop.** This is tolerable only because of the single-active-tenant desktop model above, not because any code enforces it.

**RLS protects data reads, not event payloads — these are different guarantees.** ADR-PF-011's "forced PostgreSQL RLS" applies to outbox/inbox *tables* (rows a consumer later `SELECT`s) — a database-engine-enforced data-access boundary. It provides zero protection to an in-process `Signal.emit(payload)` call or an already-constructed `Notification` object in memory, since neither ever passes through a tenant-scoped `SELECT`. This distinction must not be conflated when reasoning about "is this tenant-safe."

**Zero test coverage for cross-tenant event/signal isolation exists anywhere.** `test_domain_events.py` contains zero occurrences of "tenant." Fifteen files test tenant isolation broadly (RLS, service-level data isolation), but none intersect "signal"/"emit"/"subscribe"/"notification."

---

## 15. Ordering / Reentrancy / Concurrency

`Signal.emit()`'s lock is held only for the subscriber-list snapshot and stale-callback pruning, **never during callback execution** — a subscriber calling `.emit()` again (same or different signal) cannot deadlock, but the nested call runs to full completion, synchronously, before the outer loop's next subscriber runs. **Current dispatch is depth-first under recursion**, which is the opposite of the breadth-first behavior ADR-005 deliberately chooses for its *proposed* mechanism — today's behavior is an accident of implementation, not a documented guarantee anything currently depends on.

**No dynamic re-collection/re-entrant event-gathering exists anywhere.** Both `Resource*UnitOfWork.execute()` (cited for comparison) and `ApprovalService.approve_and_apply`/`.reject` construct exactly one event object after the operation/handler returns, then commit — there is no loop re-checking for newly-recorded events. This is confirmed **absent, not merely undocumented**, and is architecturally consistent with the current model (events are hand-constructed post-hoc, not aggregate-recorded) — "missing" only relative to ADR-005's proposed aggregate-recording model.

**No cycle guard, no `MAX_DISPATCH_ROUNDS`-equivalent, exists anywhere** — a non-issue today only because there's no re-collection loop for a cycle to occur in.

**No cross-thread emission of any Platform event mechanism exists today.** Zero `QThread`/`threading.Thread`/`concurrent.futures`/`asyncio` usage found inside `src/core/platform`; every sampled emit/dispatch happens synchronously in the same call stack as the triggering application-service method. Stated as current fact only — no inference drawn about future needs.

---

## 16. Failure Semantics

| Mechanism | Subscriber/handler raises → actual behavior | Evidence |
|---|---|---|
| `Signal.emit()` — generic `Exception` | **Propagates immediately**, aborting remaining subscribers in that call's snapshot loop. Only Qt-deleted-object `RuntimeError`/`ReferenceError` are caught. | `signal.py:37-50` — no `except Exception` branch exists |
| `ApprovalService` — handler raises *before* commit | Whole transaction rolled back (`except Exception: rollback(); raise`); no post-commit signal/notification is ever reached | `approval_service.py:227-250`, `187-206` |
| `ApprovalService` — post-commit signal/notification raises *after* commit | **Isolated and swallowed**: `_emit_signal_safely`/`safe_dispatch_notification` both try/except+`logger.exception`, never re-raise. Business transaction stays committed regardless. | `approval_service.py:299-312`, `safe_dispatch.py:27-42` |
| `Resource*UnitOfWork` — post-commit dispatch raises (cited for comparison) | Same isolate-and-continue convention, independently re-implemented | `resource_master_uow.py:52-59`, `resource_capability_uow.py:57-68` |
| `NotificationService.dispatch()` — one channel raises | Isolated per-channel; remaining channels still attempt delivery; the `Notification` is already persisted | `notification_service.py:63-71` |
| Integration outbox/inbox consumer failure | Structured, not ad hoc: explicit `RETRY`/`DEAD_LETTER` states, lease-based claiming | `delivery.py:19-31, 69-173` |

**Key pattern:** the "isolate and continue" policy ADR-005 proposes to formalize is **already the de facto convention today, enforced by repetition at three independent call sites**, not by the underlying `Signal` primitive itself. Any *new* call site that emits a signal without hand-wrapping it in try/except silently regresses to fail-fast-and-abort-remaining-subscribers, because `Signal.emit()` only catches Qt-lifecycle exceptions, not business exceptions. This is a real, currently-unenforced gap between the codebase's evident intent and what the shared primitive actually guarantees.

**Undefined behavior, explicitly flagged rather than guessed at:** what happens if a `Signal` subscriber calls `.disconnect()` on the same signal from within its own callback (mutating `_subscribers` after the snapshot was taken but before the loop finishes) has no test and no documented guarantee.

---

## 17. Testing

`src/tests/conftest.py:37-43` autouse-resets `domain_events` before/after every test — global-state leak risk is mitigated at the suite level (see §13's reconciliation). `src/tests/test_qml_domain_event_bridges_pm.py` exercises **real end-to-end subscription wiring**, not just the `Signal` primitive in isolation — it builds real workspace catalogs/controllers, monkeypatches `refresh`, emits real named signals, and asserts refresh fires (or defers while busy, or coalesces multiple emits) across 9 workspaces including Platform's own Control/Settings/AdminAccess/Admin. This is materially better coverage than "only the primitive is tested," but it does **not** test the `*_domain_event_binder.py` files by name/import, and no test asserts binder disposal/teardown or double-subscription behavior.

`src/tests/platform/test_phase_2c_platform_events.py` (8 tests) thoroughly covers `PlatformEvent` emission, append-only enforcement (`update()`/`delete()` raise `OperationNotPermittedError`), and tenant/resource scoping. `src/tests/platform/test_approval_notification_dispatch.py` tests `ApprovalService`'s notification fan-out logic against fully hand-rolled fakes — no test wires a real `ApprovalService` → real `NotificationService` → real repository in one integration test. `src/tests/platform/test_integration_delivery_foundation.py`/`test_integration_event_contract.py` give the outbox/inbox mechanism solid coverage matching ADR-PF-011's own stated test scope.

| Concern | Existing tests | Strength | Missing scenarios | Risk |
|---|---|---|---|---|
| `Signal`/`DomainEvents` primitives | `test_domain_events.py` (6 tests) | Thorough for the primitive: connect/emit/disconnect, Qt-deleted auto-prune, bridge wiring, `reset()` | No concurrent-emit test; no reentrancy test (subscriber added mid-dispatch) | Medium |
| Real controller subscription wiring | `test_qml_domain_event_bridges_pm.py` (9 workspaces) | Good breadth via real catalogs/controllers | No disposal/teardown test; no duplicate-subscription test; no cross-tenant test (none of these emits carry tenant) | Medium-High (tenant gap) |
| `ApprovalService` notification fan-out | `test_approval_notification_dispatch.py` | Good unit coverage of recipient/category logic | Entirely fake collaborators; no failure-injection test for notification dispatch itself | Medium |
| `NotificationService` | Indirect only, via faked approval tests | Weak — no direct unit test file for `NotificationService` itself | Channel-failure isolation, concurrent `mark_read` | Medium |
| `PlatformEvent`/audit trail | `test_phase_2c_platform_events.py` (8 tests) | Thorough: emission, immutability, tenant/resource scoping | Concurrent-writer tenant scoping under RLS | Low |
| Integration outbox/inbox | `test_integration_delivery_foundation.py`, `test_integration_event_contract.py` | Thorough for stated scope | End-to-end "domain event fires → outbox row written in same transaction," proven per-module elsewhere, not here | Low (by design) |
| Cross-tenant leakage on any event/signal mechanism | **None found** | — | No test anywhere asserts tenant-A emit doesn't reach a tenant-B-scoped handler, because the underlying mechanism has no tenant dimension to test | **High** |

---

## 18. Architecture Enforcement

**Correction to a provisional assumption made earlier in this same session's broader investigation: automated layering enforcement DOES exist.** `src/tests/architecture/` contains real, AST-based (`ast.parse`/`ast.walk`, not string grep) guardrail tests: `test_qml_architecture_guardrails_layers.py` (`test_core_does_not_import_qml_or_widget_ui`, plus QML-layer-specific checks), `test_pm_inventory_module_boundary.py` (`test_pm_and_inventory_modules_do_not_import_each_other`), and several other `test_*_architecture.py`/`test_architecture_guardrails_*.py` files for PM desktop-adapter and CQRS-reader boundaries.

**The gap is coverage, not absent tooling.** None of these tests check the specific axis that actually has a violation: "Platform must not import a specific business module's domain/infrastructure." `test_core_does_not_import_qml_or_widget_ui` only checks UI-layer leakage into `core/`; `test_pm_and_inventory_modules_do_not_import_each_other` only checks PM↔Inventory. Neither would have caught `calendar_assignment_service.py`'s or `approval.py`'s imports found in §12 — there is no `test_platform_does_not_import_business_modules`-shaped test today. **The enforcement technique and infrastructure are already proven in this codebase; the missing piece is one more test using the same technique, not a new capability to build.** No `pyproject.toml`, `.importlinter` config, or CI type-checker exists anywhere — enforcement that does exist is pytest-based, not a separate lint/CI gate.

---

## 19. Observability

Failure-path logging exists at exactly three hand-written call sites (`NotificationService.dispatch`, `resource_master_uow.py`, `resource_capability_uow.py`, all cited above) — each a `logger.exception(...)` on failure only, with minimal `extra={...}` context (e.g. `resource_id`, `change_type` — never a correlation ID, never `tenant_id` in the log record itself even when the triggering event had one). **Zero success-path logging exists anywhere** for any of these mechanisms — no log line records that a dispatch *succeeded*. No `prometheus`/`statsd`/metrics/counter/histogram pattern, and no dispatch- or handler-duration timing, was found anywhere near any of these mechanisms.

**Correlation/causation IDs exist as real fields only on `IntegrationEventEnvelope`.** They are absent from `PlatformEvent`, `Notification`, `DomainChangeEvent`, and the entire `Signal`/`domain_events` path — propagation stops at the durable-integration boundary and never reaches in-process signals, notifications, or the audit trail.

**Plain characterization:** for a SaaS ERP, diagnosing "why didn't tenant X's UI refresh after this commit" today would rely entirely on reading source code, not logs or telemetry — there is no operational signal to look at.

---

## 20. Event Evolution

Three distinct event-shaped concepts in Platform sit at three different versioning maturity levels, with **zero written policy connecting them**:

- `DomainChangeEvent`/`Signal` — no version field, no deprecation policy, no field-rename convention anywhere in code or docstrings.
- `Notification` categories already follow an **informal**, unenforced string convention (`"approval.requested.v1"`, `"approval.approved.v1"`) — evidence of one developer's local convention, not a documented or repository-wide rule. `PlatformEvent` has no schema/version field at all.
- `IntegrationEventEnvelope` has an explicit, validated `schema_version: int` field (rejecting `schema_version=0` per its own test), but grep for usage beyond the definition/test shows only two producer files, both almost certainly hardcoding `schema_version=1`. **No upcasting, version-branching, or backward-compatible-read logic exists anywhere** — the field is infrastructure-ready but not yet exercised as an active mechanism.

No ADR, docstring, or comment anywhere documents an evolution policy (add/remove/rename fields, deprecation window, consumer migration) for any of these classes.

---

## 21. Naming Analysis

The word **"event"** already means at least four unrelated things in this codebase before ADR-005 introduces a fifth: an audit-log record (`PlatformEvent`), a user notification (`Notification`), a UI-refresh signal (`domain_events`), and a durable transport envelope (`IntegrationEventEnvelope`). The word **"Signal"** means two unrelated things in the same file (`workspace_controller_base.py`): a generic, framework-agnostic Observer primitive (`shared/events/signal.py::Signal`) and Qt's own native signal/slot mechanism (`PySide6.QtCore.Signal`), forcing an import alias (`Signal as DomainSignal`) just to let both exist in one module.

| Term | Recommended name | Responsibility | Reason | Alternatives considered | Why weaker |
|---|---|---|---|---|---|
| `DomainEvent` (protocol) | Keep `DomainEvent` | Typing contract: "a business fact happened" | Not currently claimed by anything else in this codebase — safe to introduce | `BusinessFact`, `Fact` | Unprecedented in this codebase's vocabulary; less legible to an engineer who already knows DDD terminology |
| `RecordsDomainEvents` | Keep as proposed | Aggregate mixin for recording pending events | Matches this codebase's existing capability-then-role naming style (`TenantContextService`, `ProjectManagementUnitOfWork`) | `EventRecordingMixin` | The generic "Mixin" suffix isn't a convention used anywhere else here |
| `TransactionalEventDispatcher` | Keep as proposed | Synchronous, same-transaction event dispatch, FAIL_FAST | Already matches the *behavior* `ApprovalService`'s pre-commit handler execution has today — a name that correctly describes something with a real precedent | — | n/a — validated by existing behavior |
| `PostCommitEventPublisher` | Keep as proposed | Queued, best-effort, ISOLATE_AND_CONTINUE post-commit dispatch | No existing terminology collision found for "Publisher"/"Dispatcher" in this codebase | — | n/a |
| `ViewInvalidation`/`ViewInvalidationHint`/`ViewInvalidationChannel` | Keep as proposed | UI/read-model refresh signaling, decoupled from domain-event content | Correctly separates "something changed, go refresh" from "here is the business fact" — the exact separation today's mechanism lacks | — | n/a — but recommend retiring `_subscribe_domain_change`/`_request_domain_refresh`/`domain_event_binder`/`bind_domain_events` naming during migration, since "domain change"/"domain event" naming on the UI-refresh side is precisely the misleading collision this audit documents |
| `IntegrationEvent`/`IntegrationEventEnvelope` | Keep exactly as-is | Durable, transport-neutral, cross-process delivery | Already shipped, already correct, already well-separated — no reason to touch it | — | n/a |
| `UnitOfWork` | Keep the term, but do not reuse it unqualified for `ApprovalService`'s/`Resource*UnitOfWork`'s existing shared-session, logical-boundary pattern | Physical, per-transaction, fresh-`Session`-owning transaction boundary (ADR-005's meaning) | Conflating "logical convention over one shared session" and "physically isolated per-transaction session" under the identical name is itself a naming risk this audit surfaces | Calling the existing `ApprovalService` pattern a `TransactionBoundary` or explicitly "logical unit of work" | Avoids two different guarantees silently sharing one name once both exist side by side |
| `PlatformEvent` | **Rename** — e.g. `PlatformAuditEntry`, or merge into the existing `AuditEntry` type | Tenant-governance audit record | It is structurally an audit record; keeping "Event" in its name actively collides with the entire vocabulary this audit is trying to disambiguate | Keep as-is | Leaves a real, avoidable collision in place indefinitely once new "Event" vocabulary ships alongside it |
| `Signal[T]` (`shared/events/signal.py`) | **Rename** — e.g. `Observable` or `EventEmitter` | Generic, framework-agnostic Observer primitive | Eliminates the same-file collision with `PySide6.QtCore.Signal` that already requires an import alias today | Keep as-is | "Signal" evokes Qt too strongly for a class specifically meant to be Qt-independent |
| `Notification`/`NotificationService` | Keep as-is | User-facing in-app notification feature | Not part of the domain-event vocabulary at all; its only collision is *repository location* (§22), not naming | — | n/a |

---

## 22. Repository Location Analysis

Confirmed existing conventions this recommendation builds on: `src/core/shared/` is genuinely cross-cutting, sitting **below** both Platform and modules (§4); `src/core/platform/{domain,application,contract,infrastructure}/` holds Platform's own capability slices; `src/core/modules/<module>/` is module-owned; `src/ui_qml/` is presentation, Qt-specific; `src/infra/` holds concrete, cross-cutting infrastructure and composition.

- **Base `DomainEvent` contract** → `src/core/shared/events/domain_event.py`. Matches ADR-005 §2.1's own placement and is consistent with `shared/` already being the "below everything" tier — exactly where `Signal` already lives.
- **Event-recording behavior (`RecordsDomainEvents`)** → `src/core/shared/events/aggregate_events.py`. Same tier — used by aggregates in both Platform and modules.
- **Transactional dispatch** → contract in `shared/events/`; concrete `InProcessTransactionalEventDispatcher` in `src/infra/events/`, mirroring how `src/infra/persistence/db/` and `src/infra/composition/` already hold concrete, cross-cutting infrastructure rather than living under `platform/infrastructure/`, which is scoped to Platform's *own* capabilities.
- **Post-commit publication** → same split: contract in `shared/events/`, concrete `InProcessPostCommitEventBus` in `src/infra/events/`.
- **Handler registration** → per-capability, mirroring ADR-005's own module convention: `src/core/platform/application/<capability>/event_handlers/` for Platform's own capabilities, `src/core/modules/<module>/application/event_handlers/` for modules. The composition root (`platform_registry.py`/`app_container.py`) calls each capability's/module's registration function — ADR-005 §2.11's design is already sound here and needs no change.
- **`ViewInvalidation`** → `src/core/shared/events/view_invalidation.py` — cross-cutting, needed by every module and Platform alike.
- **Qt/PySide adapter** → `src/ui_qml/infrastructure/events/qt_view_invalidation_channel.py`, **and this migration is the natural forcing function to finally consolidate the three duplicate `workspace_controller_base.py` copies (§8) into one shared adapter**, rather than building a fourth parallel implementation alongside three existing ones.
- **Integration-event mapping infrastructure** → stays exactly where it is (`src/core/platform/integration/`, `platform/application/integration/`). Confirmed clean, mature, generic (§11) — do not move or merge it.
- **Module-specific events** → `src/core/modules/<module>/domain/events.py`, per ADR-005 — consistent with where `Resource*Changed` events already organically live in `project_management` today.
- **Platform-capability-specific events**, if Platform ever adopts typed events for its own facts (e.g. a real `EmployeeHired`) → `src/core/platform/domain/<capability>/events.py`, mirroring the module convention. **Explicitly reject** dumping these into the *existing* `src/core/platform/domain/events/` package — that path is already claimed by the unrelated audit/notification concepts (§4, §21) and doing so would deepen, not resolve, the naming collision this audit documents. This directly answers, and rejects, the prompt's own example of `platform/events/project_management_events.py`-style module events living under Platform — and extends the rejection one step further: even *Platform's own* new capability events should not land in the already-occupied `platform/domain/events/` path.

---

## 23. Desktop-to-SaaS Evolution

- **Should QML/PySide consume internal `DomainEvent`s directly?** No. Today's QML controllers already only ever decide "should I refresh" — none inspect event business content beyond filtering strings — so enforcing "QML only ever sees `ViewInvalidationHint`, never a `DomainEvent`" is a low-regret boundary to formalize now, not a hypothetical constraint invented for the future.
- **Should a web browser consume internal `DomainEvent`s directly?** No, more strongly. `DomainEvent`s are in-process/same-address-space by design (confirmed: zero cross-thread/cross-process usage exists today, §15) and were never meant to cross a network boundary. A web client should consume a WebSocket/SSE transport fed by the *same* `ViewInvalidationChannel` abstraction, via a new adapter analogous to the Qt one — not by reaching into `DomainEvent`/`Signal` directly.
- **Should Platform expose an intermediate invalidation/notification concept?** Yes — `ViewInvalidationHint`/`ViewInvalidationChannel` already is exactly this, and it's pitched at the right level: transport-agnostic, entity/tenant-scoped, carrying no business payload.
- **What should be adapter-specific?** Qt signal marshaling (main-thread dispatch) today; WebSocket/SSE per-connection session multiplexing later.
- **What belongs in core Platform?** `DomainEvent`/`RecordsDomainEvents`/`UnitOfWork`/`TransactionalEventDispatcher`/`PostCommitEventPublisher`/`ViewInvalidationHint` contracts — all framework/transport-agnostic. Confirmed today's Platform domain layer is *already* clean of Qt/SQLAlchemy imports (§12) — this constraint is an existing, working discipline, not an aspiration.
- **What should remain outside Platform?** The Qt adapter (`ui_qml`), a future WebSocket/SSE adapter (no such package exists yet), and all business-specific event content (module-owned).
- **The one real blocker for this evolution, flagged as an open question rather than decided here:** `TenantContextService`'s ambient, mutable-session-object tenant model (§14) would leak tenant context across concurrent requests if reused unchanged behind a multi-request-concurrent server. Deciding between request-scoped DI and a `contextvars`-based tenant context is a *tenancy-architecture* decision, not a domain-event decision — it belongs to a separate ADR, but any future Platform event design should be written assuming that decision has not yet been made, not assuming today's ambient model will simply carry over.

---

## 24. Legacy Compatibility

| Mechanism | Classification | Rationale |
|---|---|---|
| `domain_events` singleton / `Signal` / `DomainChangeEvent` | BRIDGE TEMPORARILY → REMOVE EVENTUALLY | Still load-bearing across 66+ sites; cannot be removed atomically, consistent with ADR-005's own phased plan |
| `admin_console/domain_event_binder.py` | REMOVE EVENTUALLY (already self-scheduled, phase "R2") | Platform's own ADR-005 migration phase should absorb/complete this already-planned removal rather than leave it as a separate, uncoordinated cleanup effort |
| Three `workspace_controller_base.py` copies | GENERALIZE | Consolidate into one shared Qt adapter (§22) rather than bridging each of the three separately |
| `ApprovalService`'s existing outer-transaction/post-commit-result pattern (PF-008) | ADAPT | Generalize its proven, accepted, tested shape into `TransactionalEventDispatcher`/`PostCommitEventPublisher` rather than replace it outright |
| `Resource*UnitOfWork` (module-owned, cited for comparison only) | UNKNOWN UNTIL MODULE MIGRATION | Decision belongs to Phase 4 of the execution plan — out of this audit's Platform-only scope |
| `PlatformEvent` | RENAME | Resolve the naming collision (§21) once new "Event" vocabulary ships alongside it — not urgent, low risk, but should not be deferred indefinitely |
| `NotificationService`/`Notification` | KEEP | Unrelated to this migration |
| `IntegrationEventEnvelope`/outbox-inbox (ADR-PF-011) | KEEP | Unrelated mechanism, already correct |
| `SessionLocal`/single process-lifetime `Session` | ADAPT | The per-transaction `UnitOfWorkFactory` closes over `SessionLocal` *alongside*, not instead of, the existing single session — already ADR-005's own plan, confirmed compatible with current wiring |
| Dead `session_scope()` | REMOVE EVENTUALLY (reclaim) | Zero callers, confirmed twice now — no migration cost |

---

## 25. Findings Registry

**PLAT-STRUCT-001 — "Events" names four unrelated concepts across Platform packages**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §4, §6, §21 — `PlatformEvent` (audit record), `Notification` (user notification), `domain_events`/`Signal` (UI invalidation), `IntegrationEventEnvelope` (durable transport) all live under paths or vocabulary containing "event(s)."
Current behavior: a new engineer searching for "domain event" in this codebase will find four unrelated things before finding the one ADR-005 means.
Why it matters: naming collisions compound migration risk and onboarding cost; this one is pre-existing, not hypothetical.
Architectural consequence: any new `DomainEvent`/`RecordsDomainEvents` vocabulary introduced by ADR-005's revision must be chosen with this collision explicitly in mind.
Recommended decision/direction: resolve naming *before* Phase 0 of any implementation (§21's table).
Implementation implication: low-cost now (nothing built yet under the colliding names for domain events specifically); expensive if deferred until after new classes ship.

**PLAT-STRUCT-002 — `platform/integration/` mixes two unrelated concerns in one flat package**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §4, §11 — `events.py`/`delivery.py`/`canonical_json.py` (durable messaging) vs. `module_registry.py`/`resolver.py`/`cross_module_reference.py` (capability gating/navigation).
Why it matters: a reader auditing "the integration boundary" (as this document was asked to) has to first separate two concerns sharing a directory name.
Recommended decision/direction: not urgent; worth a package split in a future cleanup, not blocking any domain-event decision.

**PLAT-EVT-001 — `domain_events.py`/`Signal` is a UI-refresh/invalidation bus, not a domain-event mechanism**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §7, §8 — every sampled payload is a bare opaque ID, always post-commit, no business-fact content, no tenant, no correlation.
Why it matters: this is the central, load-bearing misconception ADR-005 is built to correct — this audit independently confirms the diagnosis from first-hand evidence.
Recommended decision/direction: ADR-005's core direction (separate typed `DomainEvent`s from `ViewInvalidationHint`) is validated by this audit; no change of direction indicated.

**PLAT-EVT-002 — `DomainChangeEvent` carries no tenant identity at all**
Severity: CRITICAL · Confidence: CONFIRMED
Evidence: §7, §14.
Why it matters: the mechanism cannot express tenant identity structurally, and (see PLAT-TENANT-002) nothing downstream filters by tenant either.
Recommended decision/direction: ADR-005's required-`tenant_id`-on-`ViewInvalidationHint` design directly and correctly targets this gap.

**PLAT-EVT-003 — Coarse fan-out confirmed for Platform's own signals**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §7, §8 — `documents_changed` (9 emit sites, ≥4-5 distinct operations), `organizations_changed` (3 sites across 2 services).
Why it matters: this is not solely a module-scale problem (as the earlier, broader same-session audit found for `project_management`/`maintenance`) — it's present in Platform's own 11 named signals too.
Recommended decision/direction: Platform needs its own Phase 2A/4A-style discovery-before-typing step (per the execution plan's own discipline) when it eventually adopts typed events for its own capabilities.

**PLAT-EVT-004 — Granularity is lost twice: coarse emitters, then consumers that discard the entity ID anyway**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §8 — even `employees_changed`'s relatively narrow 2-site emitter is consumed via an undifferentiated `refresh()` that discards the ID.
Why it matters: fixing only the emitter side (typed events) without also fixing the consumer side (granular invalidation) would not actually improve UI refresh precision.
Recommended decision/direction: `ViewInvalidationHint`'s `entity_id` field must actually be read and used by binders in the target design, not merely carried.

**PLAT-EVT-005 — `ApprovalHandlerResult.post_commit_events` reflectively re-enters the legacy bus via string keys**
Severity: MEDIUM-HIGH · Confidence: CONFIRMED
Evidence: §6, §9 — `getattr(domain_events, signal_name)` then `.emit(payload)`.
Why it matters: this is a third, even-less-typed event shape, invented specifically to bridge ADR-PF-008's structured post-commit design onto the legacy bus — organic evidence of the exact gap ADR-005 exists to close.
Recommended decision/direction: treat as precedent to generalize (§24, ADAPT), not to preserve as-is.

**PLAT-EVT-006 — Platform itself owns zero typed domain-event classes today**
Severity: INFORMATIONAL · Confidence: CONFIRMED
Evidence: §6, §10.
Why it matters: nuances the earlier, broader same-session finding that ADR-005's "fully greenfield" claim is false for the codebase overall (it's false for `project_management`) — for Platform specifically, the claim is true.
Recommended decision/direction: ADR-005's revision should state this distinction explicitly rather than generalizing in either direction.

**PLAT-EVT-007 — `Signal` (generic primitive) and Qt's native `Signal` collide by name in the same file**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §6, §21 — `workspace_controller_base.py` requires `Signal as DomainSignal` to let both coexist.
Recommended decision/direction: rename the generic primitive (§21).

**PLAT-EVT-008 — `Signal.emit()`'s fail-fast default is only defended against at 3 hand-written call sites**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §7, §16.
Why it matters: any new emit call site that doesn't hand-wrap itself silently regresses to abort-remaining-subscribers-on-exception behavior; the "isolate and continue" behavior the codebase clearly intends is not enforced by the shared primitive.
Recommended decision/direction: a centralized `PostCommitEventPublisher`/bus (ADR-005's design) closes this gap structurally instead of by convention.

**PLAT-UOW-001 — Five distinct, live transaction-boundary conventions coexist in Platform, none matching ADR-005's model**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §9.
Why it matters: ADR-005's revision cannot assume Platform is a clean target for its `UnitOfWork` design — Platform has its own convergence problem, just like the business modules do.
Recommended decision/direction: add an explicit Platform-scoped migration phase to the execution plan, not folded silently into "modules migrate one at a time."

**PLAT-UOW-002 — ADR-PF-008's "Unit of Work" is a logical convention over one shared `Session`, not a physically isolated transaction, and ADR-005 never references it**
Severity: CRITICAL · Confidence: CONFIRMED
Evidence: §9.
Why it matters: this is the single most consequential documentation gap this audit found. ADR-005 is designing a second, more general "Unit of Work" abstraction without acknowledging or reconciling with the one that already shipped and is accepted (ADR-PF-008), risking a third/fourth competing convention rather than convergence.
Recommended decision/direction: ADR-005's revision must add an explicit "Related Decisions" reconciliation with ADR-PF-008, deciding whether `ApprovalService` adopts the new `UnitOfWork` outright, is bridged, or is explicitly and permanently left as a distinct, narrower pattern.

**PLAT-UOW-003 — A single logical action can span two non-atomic commits on the same shared `Session`**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §9 — `approve_and_apply` → `NotificationService.dispatch(commit=True)`.
Why it matters: illustrates concretely what happens when two different transaction-boundary conventions compose without a shared model — a silently-missing notification is possible today, already in production, by design (best-effort is intentional for notifications) but worth naming explicitly.
Recommended decision/direction: no urgent fix needed (intentional trade-off), but document it as a known, accepted trade-off rather than an undiscovered one.

**PLAT-UI-001 — Three independent, non-shared `workspace_controller_base.py` implementations, two different scheduling algorithms**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §8.
Why it matters: real, unforced technical debt independent of ADR-005 — three copies of the same intent, one genuinely different in behavior (`QTimer` debounce vs. flag-based deferral).
Recommended decision/direction: use the ADR-005 Qt-adapter migration as the forcing function to consolidate to one shared implementation (§22).

**PLAT-UI-002 — Emit-then-refresh is provably safe against pre-commit/post-rollback firing at every sampled Platform site**
Severity: INFORMATIONAL (positive) · Confidence: CONFIRMED
Evidence: §7, §8.
Why it matters: this correctness property already holds today, ad hoc, and should be preserved (not silently assumed) as an explicit requirement in any new design.

**PLAT-UI-003 — `admin_console/domain_event_binder.py` is pre-existing, self-scheduled legacy debt (phase "R2") that ADR-005 doesn't reference**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §8.
Recommended decision/direction: fold this already-planned removal into Platform's own ADR-005 migration phase rather than treating it as a separate cleanup effort.

**PLAT-UI-004 — `commit: bool` composability gap: an emit can be silently skipped when a caller composes into an outer transaction**
Severity: MEDIUM-HIGH · Confidence: CONFIRMED
Evidence: §7 (item 20), §8.
Recommended decision/direction: any new dispatch mechanism should make "did this transaction's events get dispatched" structurally guaranteed (as ADR-005's `UnitOfWork`-owns-dispatch model already does), not caller-remembered.

**PLAT-DEP-001 — Platform's `SqlAlchemyApprovalRepository` imports and joins against a concrete business-module ORM class, with no governing ADR**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §12.
Why it matters: a genuine, ungoverned layering violation, distinct from the `calendar_assignment_service.py` case (which IS governed by ADR-004) — and it sits in exactly the kind of Platform infrastructure any new domain-event design would also need to touch.
Recommended decision/direction: either introduce a project-scoping contract Platform can depend on, or explicitly document this as an accepted, scoped exception.

**PLAT-DEP-002 — `shared/` (the lower tier) imports from `platform/` in two files, inverting the codebase's own layering convention**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §12.
Recommended decision/direction: likely resolved cheaply by relocating `platform/common/exceptions`'s base types into `shared/` — requires a decision, not large effort.

**PLAT-DEP-003 — Architecture-enforcement tooling exists and is proven, but has no test for the Platform→business-module axis**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §18.
Why it matters: PLAT-DEP-001 is exactly the kind of violation this coverage gap would let through indefinitely.
Recommended decision/direction: add one `test_platform_does_not_import_business_modules`-style AST test using the same proven technique already in `src/tests/architecture/`.

**PLAT-DEP-004 — `domain_events` is a bare module-level singleton, inconsistent with the codebase's own established DI convention**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §13.
Recommended decision/direction: any new Platform-owned dispatcher/bus should be constructed inside `platform_registry.py` like `ApprovalService`/`NotificationService`, not as a bare singleton.

**PLAT-TENANT-001 — Tenant context is ambient via a mutable shared object, not a contextvar or explicit parameter**
Severity: CRITICAL (for SaaS evolution) · Confidence: CONFIRMED
Evidence: §14, §23.
Why it matters: this model does not generalize to a concurrent multi-tenant server; it is a prerequisite decision for the desktop-to-SaaS evolution, not itself a domain-event decision.
Recommended decision/direction: flagged as an explicit open dependency (§31), not decided by this audit.

**PLAT-TENANT-002 — Zero tenant filtering exists anywhere in the current dispatch path**
Severity: CRITICAL · Confidence: CONFIRMED
Evidence: §14.
Recommended decision/direction: ADR-005's structural, required-`tenant_id` `ViewInvalidationChannel.subscribe()` design directly and correctly targets this; treat as a high-priority section of the eventual implementation, not an optional hardening pass.

**PLAT-TEST-001 — Zero test coverage exists for cross-tenant event/signal isolation**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §14, §17.
Recommended decision/direction: any new mechanism's Phase 0 test suite (per ADR-005's own execution-plan discipline) must include this from the start, since it cannot be retrofitted onto the current mechanism at all (there's nothing to test against).

**PLAT-OBS-001 — Zero success-path observability, zero metrics, correlation IDs stop at the integration boundary**
Severity: HIGH · Confidence: CONFIRMED
Evidence: §19.
Recommended decision/direction: a minimal, scoped observability addition (structured dispatch logging including correlation_id, not a full metrics/tracing platform) should be budgeted into the eventual implementation plan, not treated as optional polish.

**PLAT-VER-001 — Three different, disconnected versioning maturity levels across the "event" family**
Severity: MEDIUM · Confidence: CONFIRMED
Evidence: §20.
Recommended decision/direction: adopt a lightweight, explicit policy (simple monotonic `schema_version: int`, additive-only convention) mirroring the integration envelope's already-validated shape.

---

## 26. ADR-005 Documentation Contradictions

| Document claim | Actual implementation | Evidence | Status | Required future ADR correction |
|---|---|---|---|---|
| "`UnitOfWork` ... is new; it does not exist in this codebase today" (ADR-005 §2.6) | True for Platform's own typed-event vocabulary (zero typed events under `platform/`), but Platform's `ApprovalService` (ADR-PF-008) already implements a UoW-shaped outer-transaction-owns-commit-and-post-commit-dispatch convention; `project_management`'s `Resource*UnitOfWork` classes (module-owned, cited for comparison) exist too | PLAT-EVT-006, PLAT-UOW-002, §9-10 | **PARTIALLY MATCHES / STALE** | Explicitly reconcile with ADR-PF-008; state the "greenfield" claim only for typed event *vocabulary*, not for the transaction-boundary *concept* |
| (implicit) ADR-005 never mentions ADR-PF-008 anywhere | ADR-PF-008 (accepted, implemented) already establishes "outer transaction owns commit; handlers stage, never commit/dispatch until after commit" — near-identical intent to ADR-005 §2.4/§2.6 | PLAT-UOW-002, §9 | **NOT ADDRESSED** | Add a "Related Decisions" section reconciling the two, deciding whether `ApprovalService` adopts, bridges to, or stays permanently distinct from the new `UnitOfWork` |
| Execution-plan Phase 5 targets `maintenance` module (25 raw `DomainChangeEvent` sites, "highest risk," "do last") | `maintenance` module was deleted in its entirety (`git` commit `1aa1a589`, 2026-08-20), after the ADR's 2026-08-05 date; zero raw `DomainChangeEvent(...)` sites remain anywhere in `src/` (verified this session, outside strict Platform scope but bearing directly on the execution plan's factual accuracy) | prior same-session general audit | **CONTRADICTED** | Strike or fully rewrite Phase 5 |
| Execution-plan's "Current State Snapshot" table sizes migration scope by named-`Signal`-field count per module | 66 application-layer files import the `domain_events` singleton directly (25 of them inside Platform alone) — a materially larger coupling surface than named-field counts imply | prior same-session general audit + §4/§6/§13 (25-in-platform figure) | **STALE / UNDERSTATED** | Add an import-site count alongside named-field counts in the snapshot table |
| ADR-005 §2.9 fixes a hypothetical queued/stateful transactional-bus bug from "the previous revision" | Confirmed no such bus exists anywhere in current code; the actual current isolate-and-continue convention (3 hand-written try/except-log sites) is simpler and already correct in intent, just not centralized | PLAT-EVT-008, §16 | **NOT IMPLEMENTED (design-stage only)** | No contradiction — ADR-005's design section predates any implementation; optionally cite the existing hand-rolled precedent as validation |
| ADR-005 §2.1 designs `DomainEvent` as typed and tenant-aware from day one | Confirmed current `DomainChangeEvent` has no tenant_id at all, and nothing downstream filters by tenant | PLAT-EVT-002, PLAT-TENANT-002 | **MATCHES the gap it targets** | None — reinforces this section's priority |
| ADR-005 §2.10 proposes a tenant-safe `ViewInvalidationChannel.subscribe(tenant_id=...)` as a new structural guarantee | Confirmed: today's mechanism has genuinely zero tenant filtering anywhere in its dispatch path — total absence, not a partial gap | PLAT-TENANT-002, §14 | **MATCHES (correctly identifies a severe, total gap)** | None |
| ADR-005 is silent on the pre-existing `PlatformEvent`/`Notification`/Qt-`Signal` naming collisions | Confirmed real, pre-existing collisions across four unrelated "event(s)" concepts and two unrelated "Signal" concepts | PLAT-STRUCT-001, PLAT-EVT-007 | **NOT ADDRESSED** | The ADR revision must pick vocabulary that doesn't collide with already-shipped names (§21) |
| ADR-005 §2.6 assumes application services will depend on `UnitOfWork` + `Clock` only | Confirmed current reality: five distinct live transaction conventions coexist in Platform alone; none matches this shape; the closest analogue shares one process-lifetime `Session` across the whole application, not a per-transaction fresh session | PLAT-UOW-001, PLAT-UOW-002 | **NOT IMPLEMENTED / CONTRADICTED by current reality** (not by the ADR's own design intent) | Add an explicit Platform-scoped migration phase; do not assume "modules migrate one at a time" covers Platform's own services |
| ADR-005's execution plan cites `SessionLocal` as "a genuine session factory callable, confirmed to exist and usable" | True, but confirmed here that it has exactly three references in all of `src/` and has been invoked exactly once, ever (process startup) — the ADR's proposed usage would be its first-ever per-transaction use | §9 | **MATCHES, with an important clarifying detail added** | Optionally note this as a "first real use" fact, not just "exists and usable" |

---

## 27. Decision Matrix

| Decision | Current state | Options | Recommendation | Confidence | Why |
|---|---|---|---|---|---|
| Event base abstraction | None in Platform; ADR-005's minimal `Protocol` not built | (a) adopt as-is (b) extend with `correlation_id`/`causation_id`/`schema_version` from day one (c) defer | (b) | MEDIUM | The integration envelope already proves those fields are load-bearing in production; cheap now, expensive to retrofit into 66+ call sites later — exact final field list still needs the ADR-revision pass |
| Event recording | None; events are hand-constructed post-hoc today (`ApprovalService`, `Resource*UnitOfWork`) | (a) ADR-005's aggregate-self-records model (b) keep hand-construction, formalize only dispatch (c) defer | **DECISION DEFERRED** | LOW | Whether Platform's own aggregates (`User`, `Employee`, `Organization`, `ApprovalRequest`, ...) should adopt `RecordsDomainEvents` isn't evidenced either way by this audit — needs a deliberate, per-capability decision in the ADR revision |
| Transactional dispatch | No dispatcher; `ApprovalService`'s inline handler-before-commit pattern is the closest analogue | (a) ADR-005's stateless dispatcher as designed (b) generalize `ApprovalService`'s existing, accepted pattern | (b), informed by (a)'s stateless-dispatcher correctness fix | MEDIUM | `ApprovalService` is Platform's own most mature, already-accepted precedent — better to generalize proven code than import an untested design wholesale |
| Post-commit dispatch | 3 independent hand-rolled try/except-log sites, no shared bus | ADR-005's `PostCommitEventPublisher`/in-process bus | Adopt, using the already-proven isolate-and-continue behavior as the acceptance criterion | HIGH | The correct behavior already exists in 3 places; centralizing removes PLAT-EVT-008's "new call site silently regresses" risk |
| UoW ownership | 5 competing conventions; `SessionLocal` used exactly once, ever | ADR-005's `UnitOfWork`/`UnitOfWorkFactory` | Adopt, but with an explicit Platform-scoped migration phase covering `ApprovalService`/`NotificationService` | MEDIUM | ADR-005 currently has no phase for Platform's own services; PLAT-UOW-001/002 show Platform is not exempt |
| UI invalidation | `Signal`/`domain_events` functioning as invalidation, zero tenant awareness, entity IDs often discarded even when available | ADR-005's `ViewInvalidationHint`/`PlatformViewInvalidationHint` split | Adopt | HIGH | Best-evidenced, most urgent gap in the whole audit (PLAT-TENANT-002); ADR-005's structural fix is well-designed for it |
| Qt adapter | 3 independent, duplicated `workspace_controller_base.py` copies, 2 different scheduling algorithms | Consolidate to one shared adapter implementing ADR-005's `qt_view_invalidation_channel.py` | Adopt, and use it to retire all 3 duplicates | HIGH | Confirmed real, unforced technical debt independent of ADR-005; the migration is a natural moment to fix it |
| Integration-event boundary | Clean, mature, generic (ADR-PF-011) | Keep separate; do not merge into a domain-event bus | Keep as-is; align field vocabulary only (`correlation_id`/`causation_id`/`schema_version`) | HIGH | Confirmed already correctly separated and reusable; no evidence supports merging |
| Tenant propagation | Ambient, mutable-session-based; zero dispatch-path enforcement; zero tests | ADR-005's required `tenant_id` on `ViewInvalidationHint`, distinct `PlatformViewInvalidationHint` for tenant-less facts | Adopt; also require it on any new typed Platform domain event | CRITICAL/HIGH | This audit's clearest CRITICAL-severity gap for SaaS readiness |
| Correlation/causation | Exists only on the integration envelope | Propagate the same two fields into any new typed domain-event base | Adopt | MEDIUM-HIGH | Proven pattern already in production; free to reuse, expensive to invent differently later |
| Dispatch ordering | Depth-first by accident (re-entrant `emit` runs to completion before the outer loop resumes); no documented guarantee | ADR-005 proposes explicit breadth-first for the post-commit bus | Adopt breadth-first explicitly; document today's Signal as (undocumented) depth-first so nothing silently assumes today's accidental order carries forward | MEDIUM | No production code currently depends on any ordering guarantee (none exists to depend on), so the change is safe, but must be stated as a real behavior change |
| Cycle handling | None exists; no re-collection loop exists to cycle in | ADR-005's `MAX_DISPATCH_ROUNDS` guard | Adopt once/if aggregate self-recording + re-collection is adopted; not needed otherwise | **DEFERRED**, contingent on the "Event recording" decision above | Cycle guards only matter once dynamic re-collection exists |
| Handler registration | `domain_events` is a bare singleton; `ApprovalService`/`NotificationService` use real constructor-injected DI | Follow the `ApprovalService`/`NotificationService` convention | Adopt DI-based registration via `platform_registry.py`; reject the bare-singleton pattern | HIGH | Confirmed as the actual, working, established convention; `domain_events` is the outlier |
| Error semantics | Fail-fast by default (`Signal`); hand-isolated at exactly 3 call sites | ADR-005's FAIL_FAST (transactional) / ISOLATE_AND_CONTINUE (post-commit) split | Adopt | HIGH | Directly validated by existing, accepted (PF-008) production behavior |
| Observability | Failure-only logging at 3 sites; zero metrics; correlation ID only on the integration envelope | Add structured dispatch logging (success + failure) and correlation_id propagation | Adopt a minimal version scoped to diagnosing "why didn't tenant X's UI refresh" | MEDIUM | Real production diagnosability gap (PLAT-OBS-001); doesn't require full metrics/tracing infrastructure to start |
| Event evolution | 3 different maturity levels, zero written policy | Adopt a lightweight, explicit policy (`schema_version: int`, additive-only) mirroring the integration envelope's validated shape | Adopt | MEDIUM | Cheap to decide once; expensive to retrofit; a validated shape already exists to copy |
| Architecture enforcement | AST-based tests exist and work; no test covers Platform→business-module imports, exactly where the one clear violation lives | Add one more AST test using the existing technique | Adopt | HIGH | Tooling and technique are already proven in this codebase; this is a coverage gap, not new capability to build |
| Naming | "events" means 4+ unrelated things; "Signal" means 2 unrelated things in one file | Adopt disambiguated vocabulary (§21) before writing any new class | Adopt, resolved before Phase 0 of any implementation | HIGH | Confirmed real collision risk; cheap now, confusing and costly to unwind after code ships |
| Repository locations | `shared/events/` (below Platform) vs. `platform/*/events/` (audit + notification) vs. `platform/integration/` (durable) — three tiers already in active, working use | Follow the same already-established tiering ADR-005 already (mostly) proposes | Adopt ADR-005's placement, informed by the confirmed existing convention (§22) | HIGH | The tiering ADR-005 proposes matches how this repo already organizes comparable concerns — validates rather than invents |
| Legacy compatibility | 3 duplicate controller bases; `admin_console` binder self-marked temporary; `Signal`-based dispatch fail-fast by default at most sites | Bridge incrementally; explicitly fold the `admin_console` "R2" removal into Platform's own ADR-005 phase | Adopt with explicit reconciliation (§24) | HIGH | This debt already carries its own removal marker in code; ADR-005's migration should absorb it, not leave a second, uncoordinated cleanup effort |

---

## 28. Recommended Target Platform Architecture

The following is offered as a starting point for the ADR-005 revision, grounded only in evidence gathered above — not a final decision, and not implemented by this audit.

**Principles:**
1. Separate "a business fact happened" (`DomainEvent`) from "something changed, go refresh" (`ViewInvalidationHint`) — today's mechanism conflates them; every piece of evidence in this audit supports un-conflating them.
2. The Unit of Work — not application services, not a bare global singleton — is the single place that collects, dispatches, and clears events, matching both ADR-005's own design and the *closest working precedent already in Platform* (`ApprovalService`'s outer-transaction-owns-everything convention).
3. Transactional (pre-commit, FAIL_FAST) and post-commit (ISOLATE_AND_CONTINUE) dispatch are genuinely different contracts with different handler signatures — validated directly by this audit's failure-semantics findings (§16), not merely asserted by ADR-005's design text.
4. Tenant identity is a required, structurally-enforced field on anything crossing the UI-invalidation boundary — the single highest-priority gap this audit found (PLAT-TENANT-002).
5. Naming is resolved before any new class ships, given the four-way "event" collision and two-way "Signal" collision already documented in production code (§21).
6. Platform is not exempt from its own transaction-boundary convergence problem — `ApprovalService`, `NotificationService`, and any future Platform-owned typed events need their own explicit place in the migration sequence, not an assumption that "Platform infrastructure" is already done once modules start migrating.

**Responsibility boundaries:** Platform owns the shared contracts (`DomainEvent`, `RecordsDomainEvents`, `UnitOfWork`/`UnitOfWorkFactory`, `TransactionalEventDispatcher`, `PostCommitEventPublisher`, `ViewInvalidationHint`/`Channel`) and their in-process concrete implementations; modules own their own typed event classes and their own `<Module>UnitOfWork` extensions; `ui_qml` owns the Qt adapter; a future web layer owns its own adapter. Platform does **not** own module-specific event vocabulary (rejecting the prompt's own `platform/events/project_management_events.py` example, §22), and does not own business-specific invalidation logic beyond the generic hint contract.

**Event taxonomy** (validated against §6's inventory, not invented fresh): typed, tenant-scoped `DomainEvent`s (new); `ViewInvalidationHint`/`PlatformViewInvalidationHint` (new, tenant-required vs. genuinely tenant-less); `PlatformEvent`-as-audit-record (existing, keep, eventually rename); `Notification` (existing, keep, unrelated); `IntegrationEventEnvelope` (existing, keep, unrelated, but donates its `correlation_id`/`causation_id`/`schema_version` field shape to the new `DomainEvent`).

**Transaction model:** a `UnitOfWork` per transaction, backed by a fresh `Session` from a session factory (validating ADR-005's own design, and confirming — via `SessionLocal`'s three-total-references finding — that this really would be new usage, not a rename of something already working this way). `ApprovalService`'s existing pattern is the template to generalize, not a competing pattern to ignore.

**Failure model:** FAIL_FAST for transactional dispatch (matches `ApprovalService`'s existing single-except-block behavior), ISOLATE_AND_CONTINUE for post-commit dispatch (matches the 3 existing hand-rolled try/except-log sites) — both already de facto conventions in this codebase, now proposed to be structurally enforced rather than repeated by hand at each new call site.

**Tenant requirements:** required `tenant_id` on every tenant-scoped `DomainEvent` and on `ViewInvalidationHint`; a distinct, separately-named type for genuinely platform-wide facts; structural (not binder-discipline) tenant enforcement at the channel's `subscribe()` boundary — directly targeting PLAT-TENANT-002.

**Desktop/SaaS compatibility:** QML and any future web client consume `ViewInvalidationHint` only, never `DomainEvent` directly (§23); the Qt adapter and a future WebSocket/SSE adapter are the only transport-specific code.

**Dependency direction:** Platform's domain/application layers stay free of Qt/SQLAlchemy imports (already true today, §12 — a discipline to preserve, not introduce); the one confirmed real violation (`SqlAlchemyApprovalRepository` → `ProjectORM`) should be resolved or explicitly, permanently documented as an accepted exception, independent of this migration.

**Lifecycle/composition:** built and wired inside `platform_registry.py`/`app_container.py`, constructor-injected like `ApprovalService`/`NotificationService` — never a bare module-level singleton like today's `domain_events`.

**Testing requirements:** cross-tenant isolation tests from day one (none exist today to build on, §17); disposal/teardown tests for whatever Qt adapter replaces the 3 duplicated controller bases; failure-injection tests for both dispatch policies, matching the rigor already demonstrated in `test_phase_2c_platform_events.py` and `test_integration_delivery_foundation.py`.

**Architecture enforcement requirement:** one new AST-based test (using the exact technique already proven in `src/tests/architecture/`) asserting Platform's domain/application layers never import a concrete business module — closing PLAT-DEP-003 as part of this migration, not as a separate follow-up.

**Indicative flow** (adapted from ADR-005 §2.7, validated rather than altered by this audit's evidence):

```text
Command
    ↓
Application Service
    ↓
Aggregate
    ↓
records DomainEvent (tenant-scoped, correlation/causation-carrying)
    ↓
UnitOfWork (fresh Session per transaction — genuinely new usage of SessionLocal)
    ↓
TransactionalEventDispatcher (FAIL_FAST — generalizes ApprovalService's existing,
    accepted pre-commit-handler convention)
    ↓
Commit (repository update()/add() staged explicitly beforehand — commit() alone
    does not persist a mutation, per this codebase's own confirmed mixed
    persistence mechanisms)
    ↓
PostCommitEventPublisher (ISOLATE_AND_CONTINUE — generalizes the 3 existing
    hand-rolled try/except-log sites into one shared, structurally-guaranteed policy)
    ├── ViewInvalidation handler → tenant-scoped hint → Qt adapter (today) /
    │     future web adapter (later) → consolidates the 3 duplicated controller bases
    ├── local projection handler (if/when needed)
    └── integration-event mapper (unchanged — ADR-PF-011 territory, written
          during the transactional phase, never as a reaction to a published
          in-process event)
```

---

## 29. Recommended Repository Structure

```text
src/core/shared/
  events/
    domain_event.py                  # DomainEvent marker protocol
    aggregate_events.py              # RecordsDomainEvents mixin
    domain_event_publisher.py        # TransactionalEventDispatcher + PostCommitEventPublisher (protocols)
    domain_event_subscriber.py       # handler-shape protocols + subscriber protocols
    subscription.py                  # Subscription (dispose) protocol
    view_invalidation.py             # ViewInvalidationHint + PlatformViewInvalidationHint + channel contract
    signal.py                        # existing generic primitive — RECOMMEND renaming the class
                                      #   itself (e.g. Observable) to resolve the Qt-Signal collision;
                                      #   filename may stay if desired, class name should not
  persistence/
    unit_of_work.py                  # UnitOfWork + UnitOfWorkFactory protocols (module-agnostic)
  time/
    clock.py                         # Clock protocol (general-purpose, not events-specific)

src/core/platform/
  domain/
    events/
      platform_events/               # UNCHANGED — RECOMMEND renaming PlatformEvent itself
                                      #   (e.g. PlatformAuditEntry) to resolve the naming collision;
                                      #   do NOT add new domain-event vocabulary to this path
      notifications/                 # UNCHANGED — unrelated to this migration
    <capability>/
      events.py                      # NEW, per-capability, only if/when a Platform capability
                                      #   adopts typed domain events for its own facts — explicitly
                                      #   NOT placed under domain/events/ (already occupied, §22)
  application/
    <capability>/
      event_handlers/
        transactional.py             # NEW, per capability, mirrors module convention
        view_invalidation.py         # NEW, per capability, mirrors module convention
  integration/                       # UNCHANGED — keep separate (§11, §22); consider a
                                      #   package split (events.py/delivery.py vs.
                                      #   module_registry.py/resolver.py) as an independent,
                                      #   lower-priority cleanup (PLAT-STRUCT-002)

src/infra/
  events/
    in_process_transactional_event_dispatcher.py   # NEW — generalizes ApprovalService's
                                                     #   existing pre-commit handler pattern
    in_process_post_commit_event_bus.py             # NEW — generalizes the 3 existing
                                                     #   hand-rolled try/except-log sites
    in_process_view_invalidation_channel.py         # NEW — tenant-enforcing, non-marshaling
  persistence/db/
    unit_of_work.py                  # RECLAIMED from dead session_scope() (0 callers,
                                      #   confirmed twice) — SqlAlchemyUnitOfWorkBase

src/core/platform/infrastructure/persistence/
  unit_of_work.py                    # NEW, Platform's own SqlAlchemyPlatformUnitOfWork
                                      #   (or per-capability, if Platform's capabilities
                                      #   diverge enough to warrant it — decide during the
                                      #   ADR revision, not here) — the vehicle for
                                      #   generalizing ApprovalService onto the new model

src/core/modules/<module>/
  domain/events.py                   # UNCHANGED convention — module-owned typed events
  contracts/unit_of_work.py          # UNCHANGED convention — module-owned UoW extension
  infrastructure/persistence/unit_of_work.py   # UNCHANGED convention

src/ui_qml/
  infrastructure/events/
    qt_view_invalidation_channel.py  # NEW — the single, shared adapter replacing the
                                      #   3 duplicated workspace_controller_base.py copies
  platform/controllers/common/
    workspace_controller_base.py     # SIMPLIFIED once the shared adapter above exists —
                                      #   subscribe/dispose logic moves into the adapter
  platform/controllers/admin_console/
    domain_event_binder.py           # REMOVED as part of this migration, completing its
                                      #   own pre-existing "R2" self-scheduled removal
```

For every new directory: **why it belongs there** — matches this audit's confirmed tiering (`shared` below Platform and modules; `platform/<layer>/<capability>` for Platform's own concerns; `infra` for concrete cross-cutting implementations; `ui_qml` for the Qt-specific adapter). **What may depend on it** — modules and Platform capabilities may depend on `shared/events/` contracts; only `infra/composition/` may construct the concrete `infra/events/` implementations; only `ui_qml/` may import the Qt adapter. **What must not depend on it** — `shared/events/` must never import from `platform/` or `src.core.modules.*`; `platform/domain/`/`platform/application/` must never import `sqlalchemy`/`PySide6`/`ui_qml`/a concrete business module (closing PLAT-DEP-001 for anything newly written here, even if the pre-existing `approval.py` violation is handled separately).

---

## 30. Platform Migration Dependency Order

High-level dependency order only — not a task-by-task implementation plan (that is explicitly a separate, later deliverable per §29 of the original request).

```text
Naming resolution (§21) — decided before any code, cheapest point to fix it
    ↓
Architecture-enforcement coverage gap closed (§18) — one new AST test,
    using the existing proven technique, so nothing built next can
    silently repeat PLAT-DEP-001's shape
    ↓
Base contracts (DomainEvent, RecordsDomainEvents, Subscription) — shared/events/
    ↓
UnitOfWork / UnitOfWorkFactory contracts — shared/persistence/
    (design decision still open, §27: aggregate-self-recording vs.
    formalized hand-construction — resolve before this step, not during it)
    ↓
Transaction/UoW convergence for PLATFORM'S OWN services —
    ApprovalService and NotificationService's existing patterns generalized
    onto the new contracts (this is Platform's own version of what the
    execution plan already requires per business module — do not skip it
    on the assumption Platform is "infrastructure" and therefore exempt)
    ↓
TransactionalEventDispatcher (concrete, in-process)
    ↓
PostCommitEventPublisher (concrete, in-process)
    ↓
ViewInvalidationHint / PlatformViewInvalidationHint / channel abstraction —
    tenant-enforcing from the start (PLAT-TENANT-002 is not deferrable)
    ↓
Qt adapter — consolidating the 3 duplicated workspace_controller_base.py
    copies into one shared implementation, retiring admin_console's
    self-scheduled "R2" legacy binder in the same step
    ↓
Legacy Platform compatibility bridge — Platform's own 11 named signals
    migrate onto the new mechanism, old domain_events fields for those
    11 retired only once the new path is proven end-to-end
    ↓
Platform migration complete
    ↓
Module migrations later (per the existing execution plan's Phase 2/4/5
    sequencing — out of this audit's scope to re-sequence)
```

---

## 31. Risks and Open Questions

- **`platform/access/{domain,application}` vs. `platform/domain/security/authorization`** — two access-control homes exist; this audit did not establish whether this is a deliberate seam or drift. Needs a targeted follow-up before any event-handler registration logic is placed near either.
- **Three of Platform's 11 named signals (`access_changed`, `modules_changed`, `approvals_changed`) have no confirmed subscriber** in the `admin_console` binder audited here — they may be consumed elsewhere in the codebase; this was not established.
- **Tenant-context concurrency model for a future web/SaaS adapter** is explicitly not decided by this audit (§23) — it is a prerequisite for any WebSocket/SSE `ViewInvalidationChannel` adapter and belongs to a separate tenancy-architecture decision.
- **Whether `ApprovalService`/`NotificationService` should be the *first* real consumers of ADR-005's `UnitOfWork`**, or whether Platform gets its own bespoke bridging step, is a judgment call for the ADR revision, not resolved here (Decision Matrix marks the closest related row MEDIUM confidence).
- **Historical-layout verification** (`git log --follow` on the shared-vs-platform audit/notification pairs, and on the `admin_console`'s three-file coordinator split) was flagged by one investigation as not completed, time-boxed out. If a definitive "was this a restructure that never finished" answer is needed, that specific follow-up remains open.
- **Thread-safety of `ApprovalService`'s shared `Session` under concurrent calls** was not established either way — no evidence of concurrent use was found, but SQLAlchemy `Session` objects are documented as not thread-safe in general, and this was not stress-tested or further investigated.
- **Whether Time/Procurement's outbox writes are actually issued inside the same transaction as their business mutation** (ADR-PF-011's core atomicity claim) was not re-verified by this audit — it is module-scoped, explicitly out of bounds here, and was only confirmed at the *contract* level (the delivery service is transaction-neutral, which makes the guarantee possible, not automatic).
- Where this audit could not establish something from the repository, it says so explicitly above rather than guessing (see each "not established"/"UNKNOWN" marker in the relevant section) — this list collects those in one place for the reviewer's convenience.

---

## 32. Final Architectural Verdict

**1. What is the current Platform event architecture really doing?** Coordinating post-commit UI refresh (`domain_events`/`Signal`) under a misleading "domain events" name, alongside four other, genuinely separate concerns that happen to share overlapping vocabulary: an audit trail (`PlatformEvent`), a user-notification feature (`Notification`), an already-shipped narrower transaction-boundary pattern (`ApprovalService`, ADR-PF-008), and a mature, correctly-separated durable integration mechanism (ADR-PF-011).

**2. What are its most important weaknesses?** In order: (a) zero tenant isolation anywhere in the event-dispatch path, with zero test coverage to catch a regression even if that changed; (b) five competing, unreconciled transaction-boundary conventions, with ADR-005's own proposed `UnitOfWork` design never referencing the one that's already accepted and shipped (ADR-PF-008); (c) a naming system that already means four different things for "event" and two different things for "Signal"; (d) three independently duplicated, behaviorally divergent copies of the same UI-refresh controller base; (e) a shared primitive (`Signal.emit`) whose fail-fast default is only defended against by hand, at three call sites, with no structural guarantee for the next one.

**3. Which parts are already architecturally sound and should be preserved?** ADR-PF-011's integration/outbox-inbox mechanism (mature, generic, correctly separated, well-tested) — do not merge it into anything. `ApprovalService`'s transaction-boundary discipline (outer-transaction-owns-commit, handlers stage only, post-commit reactions isolated) — generalize it, don't replace it. `PlatformWorkspaceControllerBase`'s disposal-via-Qt's-`destroyed`-signal pattern — reliable, worth keeping as the model for whatever Qt adapter consolidates the three duplicates. The `EnterpriseAuditService`/`AuditEntry`/`DurableSecurityDenialRecorder` audit trail, including its deliberate separate-transaction persistence strategy for denial evidence — sound, keep as-is.

**4. Should the current `DomainEvents` mechanism remain, evolve, be renamed, or eventually be replaced?** Replaced, in the sense ADR-005 already proposes — split into typed `DomainEvent`s (new) and `ViewInvalidationHint`s (new), retiring `DomainChangeEvent`/the bare `Signal`-bag mechanism module-by-module and Platform-signal-by-Platform-signal. This audit finds no evidence favoring "evolve in place" over "replace via the phased plan ADR-005 already outlines."

**5. Should UI refresh/invalidation be separated from Domain Events?** Yes, unambiguously — every piece of evidence in this audit (bare-ID-only payloads, always-post-commit timing, entity-id-discarding consumers, zero tenant awareness) supports treating them as two different concepts that happen to share one mechanism today by accident of history, not by design.

**6. What should Platform own?** The shared contracts and their in-process concrete implementations (§28's responsibility boundaries); its own capabilities' eventual typed events, under their own capability paths, never under the already-occupied `platform/domain/events/`; the Qt adapter's eventual consolidation point (constructed centrally, used by all controller families).

**7. What should business modules own?** Their own typed event vocabulary and their own `<Module>UnitOfWork` extensions — unchanged from ADR-005's existing design, validated rather than altered by this Platform-scoped audit.

**8. What should the canonical transaction/UoW model be?** A per-transaction `UnitOfWork` backed by a fresh `Session` from a session factory, generalizing `ApprovalService`'s proven outer-transaction-owns-commit-and-post-commit-dispatch shape — with an explicit, first-class migration step for Platform's own services (`ApprovalService`, `NotificationService`), not an assumption that Platform is exempt because it's "infrastructure."

**9. What names should be standardized?** See §21 in full; most consequential: rename `PlatformEvent` (audit record, not an event) and rename the generic `Signal[T]` primitive (collides with Qt's own `Signal` in the same file) before any new "Event"/"Signal"-named class ships.

**10. Where should the new abstractions live?** See §22 and §29 in full — `shared/events/` for contracts (below both Platform and modules, matching existing convention), `infra/events/` for concrete in-process implementations, `ui_qml/infrastructure/events/` for the Qt adapter, module/capability-owned paths for business-specific event vocabulary.

**11. What existing mechanisms will require compatibility bridges?** The `domain_events` singleton itself (66+ call sites, cannot move atomically); `admin_console/domain_event_binder.py` (already self-scheduled for removal — fold into this migration rather than treating separately); the three duplicated controller bases (generalize into one, don't bridge three); `ApprovalService`'s existing pattern (adapt/generalize, don't discard).

**12. What must ADR-005 change later?** At minimum: add a "Related Decisions" section reconciling with ADR-PF-008; add an explicit Platform-scoped migration phase; strike or rewrite the execution plan's Phase 5 (targets a deleted module); correct the "fully greenfield"/"UnitOfWork is new" claims to be precise about *what* is greenfield (Platform's typed-event vocabulary) versus what already exists under a different name (the transaction-boundary concept); resolve the naming collisions this audit documents before finalizing any new class names; add a Platform-specific import-boundary test to its own exit criteria, given the one confirmed violation this audit found in Platform's own approval infrastructure.

**13. What questions remain unresolved?** See §31 in full — the `platform/access` vs. `platform/domain/security/authorization` relationship, the three unaccounted-for named signals, the tenant-context concurrency model for a future web adapter, whether `ApprovalService`/`NotificationService` become the first consumers of the new `UnitOfWork` or get a bespoke bridge, and two explicitly time-boxed-out historical/thread-safety checks.

**14. Is the Platform architecture sufficiently understood to proceed to ADR-005 revision and a concrete implementation plan?**

> **READY WITH EXPLICIT CONDITIONS**

The evidence gathered here is deep enough, and consistent enough across eight independent investigations, to support revising ADR-005 and drafting a concrete Platform implementation plan. The explicit conditions: (a) ADR-005's revision must add the ADR-PF-008 reconciliation and a Platform-scoped migration phase before implementation begins — proceeding without this risks building a *third* transaction-boundary convention rather than converging the existing ones; (b) the naming decisions in §21 should be finalized as part of the ADR revision itself, not left to be decided ad hoc during implementation; (c) the execution plan's Phase 5 must be corrected before it is used to sequence any work; (d) the tenant-context concurrency question (§31) should be explicitly acknowledged as a separate, not-yet-made decision in the revised ADR, rather than silently assumed away.
