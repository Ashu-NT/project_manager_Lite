# Platform — CQRS Existing-State Audit

Status: **Read-only existing-state audit, complete (2026-08-12).** This document follows the exact
methodology of `docs/pm_modernization/CQRS/project_management_cqrs_existing_state_audit.md` (the
"PM audit"), applied to `src/core/platform/` instead of Project Management. It is an audit only —
**no code was changed to produce it**, and no CQRS implementation work has started for Platform.
Every claim below was verified by opening the cited file and, where a call chain is described,
following it to its concrete runtime implementation; file:line citations are given wherever the
source PM audit gives them. Sections that would require dynamic/runtime confirmation beyond static
reading are flagged explicitly as unconfirmed rather than asserted.

This document was produced by five parallel, independently-verified research passes (structure and
composition; desktop API inventory; write/read path traces; repository and persistence audit;
transactions/authorization/events/tests), each instructed to match the PM audit's evidentiary
standard, then synthesized into one document with the same section numbering. Where a Platform
finding directly mirrors, contradicts, or extends a specific PM audit finding, that relationship is
called out explicitly, since the two documents are meant to be read together.

## P0 correctness/security remediation status (started 2026-08-12)

The team elected to fix correctness/security findings from this audit before any CQRS work begins.
Six items were prioritized (P0.1-P0.6); status is tracked here and updated as each is closed. This
is now a living document, not a frozen snapshot — findings below are annotated in place as fixed.

| # | Finding | Status |
|---|---|---|
| P0.1 | Organization provisioning atomicity (§6 W1) + `is_active=True` crash | **Fixed** — see inline note at W1 below |
| P0.2 | Employee → Resource pre-commit event bug (§6 W3) | **Fixed** — see inline note at W3 below |
| P0.3 | Calendar `seed_standard_week` transaction defect (§6 W9) | **Fixed** — see inline note at W9 below |
| P0.4 | `audit_entries` RLS gap (§11) | **Fixed** — see inline note below |
| P0.5 | Master-data audit atomicity policy (§10, §12) | **Fixed** — see inline note below |
| P0.6 | Calendar resolver stale-cache invalidation (§4c, §7 R7b) | **Fixed** — see inline note below |

**P0.1 — fixed 2026-08-12.** `OrganizationService.create_organization`, `OrganizationService.
set_active_organization`, and `ModuleCatalogService.provision_organization_entitlements` each gained
a `commit: bool = True` parameter; their audit calls now happen *before* the commit point
(`commit=False, fail_closed=True`) so the business write and its audit entry commit or roll back
together, closing the ADR-003 gap. `PlatformRuntimeApplicationService.provision_organization` now
stages all sub-operations with `commit=False` and issues one final commit (mirroring ADR-PF-008's
approval pattern), then emits events/rebuilds tenant context only after that commit succeeds. The
`is_active=True` crash is fixed by routing both `provision_organization` and the desktop-exposed
`set_active_organization` through `OrganizationService.set_active_organization` (which actually
persists activation) instead of calling `TenantContextService` directly (which only rebuilds
in-memory state).

Fixing this also required resolving a second, previously-undiscovered bug it exposed:
`SqlAlchemyModuleEntitlementRepository` only permitted entitlement reads/writes for the *currently
active* organization, which made `provision_organization_entitlements` fundamentally incapable of
seeding a newly-created (not-yet-active) organization's entitlements — confirmed via `git stash` to
predate all of today's changes. Resolved per an explicit product decision: ordinary/runtime
entitlement operations (`get_for_organization`, `list_all_for_organization`,
`upsert_for_organization`) remain scoped to the active organization only; a new pair of
tenant-administration/provisioning-scoped methods (`upsert_for_organization_in_tenant`,
`list_all_for_organization_in_tenant`) were added, scoped to "belongs to the authenticated tenant"
via a live DB check, and `provision_organization_entitlements` now uses those instead. Verified: the
17 previously-failing/blocked provisioning tests now pass, the two tests asserting ordinary
operations still reject non-active organizations still pass, and a full `platform`+`architecture`
regression shows zero new failures (and several previously-failing tests now pass as a side effect)
— the remaining failures are the same pre-existing, unrelated set documented throughout this audit
(calendar test fixtures, the `audit_entries` RLS gap this is itself tracking as P0.4, the Site
tz-naive/aware bug, the generated-file line-limit guard).

**P0.2 — fixed 2026-08-12.** `employee_support.py::sync_linked_employee_resources` no longer emits
`domain_events.resources_changed` itself — it now only stages the linked-resource mutations
(`resource_repo.update(...)`) and returns the tuple of touched resource IDs. `EmployeeService.
update_employee` emits `resources_changed` for each returned ID only after its own
`session.commit()` succeeds, alongside the existing (already-correct) post-commit
`employees_changed` emission. This closes the "event fired before commit, for rows that could still
roll back" gap found in §6 W3. The unused `domain_events` import was removed from
`employee_support.py`. Verified: a direct unit check confirms `sync_linked_employee_resources` no
longer emits anything and correctly returns touched IDs; all 16 employee/resource-scoped platform
tests pass; a full `platform`+`architecture` regression shows zero new failures.

**P0.3 — fixed 2026-08-12.** `WorkingRuleService.save_rule` gained a `commit: bool = True`
parameter (flush instead of commit when `False`), and `seed_standard_week` now stages all 7 weekday
rules with `commit=False` inside a `try`/`except: rollback` block, followed by exactly one
`session.commit()` — replacing the previous 7 independent, per-call commits. A mid-loop failure now
rolls back the whole week instead of leaving a partially-edited one. All other `save_rule` call
sites (direct single-rule saves from the desktop API and tests) are unaffected — they keep the
`commit=True` default. Verified: `test_working_rule_seed_standard_week` and the full
`test_enterprise_calendar_crud_rules.py`/`test_enterprise_calendar_desktop_api_working_days.py`
suites pass (aside from the two calendar tests already documented as pre-existing/unrelated
MagicMock-fixture failures), and the broader calendar-scoped platform test run shows the identical
pre-existing 6-failed/12-error set with zero new failures.

**Consolidated P0.1-P0.3 regression (2026-08-12).** A full `platform`+`architecture` run with all
three fixes combined reproduced the exact same 14-failed/853-passed/12-error baseline documented
throughout this audit (calendar `MagicMock`-fixture issues in
`test_enterprise_calendar_exceptions_events_shifts.py`/`test_enterprise_calendar_resolver.py`/
`test_enterprise_calendar_shift_pattern_resolution.py`, a flaky
`test_platform_access_scopes.py` project-membership scope assertion, the `Site` tz-naive/aware bug,
the `audit_entries` RLS gap tracked below as P0.4, `test_qml_platform_routes`, and the three
generated-file/module-size architecture guardrails) — zero tests newly failing. The specific set of
calendar tests reported as FAILED vs ERRORed varies slightly run-to-run (pre-existing test-order
sensitivity in that fixture, not something P0.1-P0.3 touch); confirmed via `git stash` that the same
failures reproduce identically with P0.2/P0.3's changes removed.

**P0.4 — fixed 2026-08-12.** `audit_entries` had no PostgreSQL RLS policy at all — worse, the
existing `test_postgresql_rls_context.py::test_every_tenant_bearing_table_has_rls_or_explicit_
bootstrap_classification` test explicitly classified it as an "identity bootstrap" table (alongside
`organizations`, `roles`, `role_bindings`, `role_delegation_policies`, `user_tenants`,
`notifications`) exempt from RLS entirely. That classification was too broad: bootstrap tables are
exempt because they must be queryable *before* `app.tenant_id` can be set (the tenant-resolution
chicken-and-egg problem during login) — but `audit_entries`' tenant-scoped write/read paths
(`add()`, `add_for_tenant()`, `list_recent()`, `list_recent_for_organization()`) all operate
*within* an already-resolved tenant context and have no such bootstrap need. Only one of its three
write paths, `add_platform()`, genuinely requires no tenant context — it explicitly asserts
`tenant_id is None and organization_id is None` and is used for platform-level security events
(login, registration, role governance, tenant/organization provisioning — confirmed via grep across
`security_audit.py`, `audit_recorder.py`, `role_governance_service.py`,
`platform_owner_provisioning_service.py`). Lumping all of `audit_entries` into the bootstrap
exemption meant its tenant-scoped rows — which can carry sensitive `old_value`/`new_value` business
data — had zero database-level tenant-isolation enforcement; if the application-layer `WHERE`
clause in `list_recent()`/`list_recent_for_organization()` were ever bypassed or buggy, or a
reporting/ad-hoc query hit the table directly, cross-tenant rows would be visible with nothing at
the database layer to stop it.

Reusing the generic `TENANT_RLS_TABLES` single-predicate policy
(`tenant_id = current_setting('app.tenant_id')`) was not an option: under `FORCE ROW LEVEL
SECURITY`, `NULL = 'sometenant'` evaluates to `NULL` (not `TRUE`), so that policy would reject every
`add_platform()` insert under `WITH CHECK` and hide every already-inserted platform row under
`USING`. New migration `pfaudit_p04_001_enable_audit_entries_rls.py` (chained onto the current head,
`pfbill_e1_001`) adds a bespoke policy scoped to `audit_entries` only:
`USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '') OR tenant_id IS NULL)`, same
predicate for `WITH CHECK` — tenant-scoped rows get the same enforcement as every other
`TENANT_RLS_TABLES` member, and `tenant_id IS NULL` platform rows pass through unconditionally, in
either direction, regardless of the calling session's tenant context. `audit_entries` was removed
from `test_postgresql_rls_context.py`'s `_IDENTITY_BOOTSTRAP_TABLES` set and now lives in a new
`_CUSTOM_POLICY_TABLES` set (sourced directly from the migration module, so the test breaks loudly
if the migration's table name ever drifts) documenting *why* it needs a bespoke predicate instead of
either the generic policy or a bootstrap exemption. Like all Platform RLS migrations, this is a
no-op on SQLite (`if bind.dialect.name != "postgresql": return`), so it does not affect the
dev/test database used throughout this audit. Verified: `python -m alembic heads` still reports a
single head (`pfaudit_p04_001`) after adding the migration; the new migration file compiles; all 39
tests exercising `add_platform()` call sites (`test_auth_security_audit_atomicity.py`,
`test_auth_registration_role_audit_atomicity.py`, `test_auth_login_session_audit_atomicity.py`,
`test_platform_owner_provisioning.py`) pass unchanged; `test_postgresql_rls_context.py`'s
classification test no longer lists `audit_entries` among its mismatches — the table is now fully
accounted for by `TENANT_RLS_TABLES | _IDENTITY_BOOTSTRAP_TABLES | _CUSTOM_POLICY_TABLES`. That test
still fails, unchanged from before this fix and unrelated to it: a set of newer PM project-finance
tables (`project_billing_profiles`, `project_finance_rate_card_lines`,
`project_finance_inbox_receipts`, `project_commitment_lines`, `project_finance_budgets`, and others)
carry `tenant_id` but were never classified into either set — a pre-existing PM-module gap outside
this Platform audit's P0 scope.

**P0.5 — fixed 2026-08-12.** Every master-data write in Platform (`create`/`update`/`delete` across
`OrganizationService` — already fixed under P0.1 — plus `EmployeeService`, `SiteService`,
`PartyService`, `department_commands.py`, `DocumentService`, and `DocumentIntegrationService`)
followed the same non-atomic shape: stage the repository write, `session.commit()`, and only *after*
that commit succeeded call `record_audit_entry(...)` using its lenient default
(`commit=True, fail_closed=False`). Two failure modes followed directly from that ordering: (i) if
the audit write itself failed for any reason, `record_audit_entry`'s lenient default silently
swallows the exception — the business mutation stands committed with no audit trail at all, and
the caller never finds out; (ii) even when the audit call succeeds, it does so as a *second*,
independent transaction, so the business row and its audit entry are never guaranteed to land or
roll back together — the exact "business mutation and successful security audit intent commit
atomically" requirement ADR-003 states for master-data operations, which P0.1 already fixed for
organization provisioning specifically. This closes it for the rest of master-data.

All 17 remaining write methods across the 6 files above were changed to the same shape P0.1
established: the repository write and `record_audit_entry(..., commit=False, fail_closed=True)` are
both staged inside the existing `try` block, *before* the single `session.commit()` that already
existed for the business write — so audit and business-row durability now share one transaction,
and a failed audit write now raises loudly (via `fail_closed=True`) and rolls back the whole
mutation instead of vanishing silently. No `commit: bool` parameter was added to these methods
(unlike P0.1's `OrganizationService`/`ModuleCatalogService`) since none of them are composed into a
larger orchestrator transaction the way organization provisioning is — each is already the outermost
unit of work for its own request. `DocumentIntegrationService.register_entity_attachments`, which
stages a variable number of document+link pairs in a loop before one shared commit, now stages an
audit entry per document inside that same loop (before the commit) and defers all `documents_changed`
event emissions to after the commit succeeds, matching P0.3's `seed_standard_week` precedent for
multi-row loops sharing one commit.

Three existing unit-test fixtures constructed these services without an `enterprise_audit_service`
(`test_org_site_domain_validation.py`'s `SiteService` fixture, `test_party_domain_validation.py`'s
`PartyService` fixture, and `test_department_employee_domain_validation.py`'s `DepartmentService`
and `EmployeeService` fixtures) — previously harmless under the lenient default, these would now
trip `fail_closed=True`'s `ENTERPRISE_AUDIT_REQUIRED` error the moment a test called `create_*`/
`update_*`. All four fixtures were given a `_FakeEnterpriseAuditService` (a bare `record(self,
**kwargs) -> None: return None`), mirroring the fix already applied to `OrganizationService`'s
fixture under P0.1; production wiring in `platform_registry.py` already passed a real
`enterprise_audit_service` to every one of these six services, so no production code needed to
change. A separate check confirmed the one other place a bare Platform `SiteService`/`DepartmentService`/
`PartyService`/`DocumentService` is constructed in tests (`test_tenant_isolation_services_platform.py`)
only exercises read-only `list_*` methods, so it needed no fixture change. Verified: all 10 tests in
the three edited domain-validation test files pass; a full `platform`+`architecture` regression
(with all of P0.1-P0.5 combined) reproduces the identical pre-existing failure/error set documented
throughout this audit, confirmed by `git stash`-isolating today's P0.2/P0.3/P0.4/P0.5 changes and
re-running — zero new failures, including for the two `test_enterprise_calendar_desktop_api_working_days.py`
tests that a fuller (untruncated) regression run surfaced for the first time in this audit but which
predate every P0 fix made here.

**P0.6 — fixed 2026-08-12.** `EnterpriseCalendarResolver` already had an `invalidate_cache()` method
(clearing `_rules_cache`, `_recurring_cache`, `_shift_pattern_cache`, `_shift_pattern_days_cache`,
and the missing-rule warning dedupe set) — but a repo-wide grep confirmed it had **zero callers
anywhere**. The resolver itself is a single process-lifetime instance (`platform_registry.py`
constructs exactly one `EnterpriseCalendarResolver`, shared by `GlobalCalendarShim` and every
PM consumer through it), so any working rule, recurring event, or shift pattern change made after
that first cache-warming read stayed invisible to every subsequent resolved-calendar read for the
rest of the application's process lifetime — not just within one request, as "cache" might suggest,
but until the desktop app itself restarts. This is exactly the finding this audit raised in §4c/§7
R7b.

Note that `CalendarException`s and calendar/assignment lookups are **not** cached by the resolver
(`_collect_exceptions`/`_build_chain` query their repositories directly on every call) — only rules,
recurring events, and shift patterns/days are, so only the services that mutate those needed wiring:
`WorkingRuleService` (`save_rule`, `seed_standard_week`, `delete_rule`), `RecurringEventService`
(`add_recurring_event`, `update_recurring_event`, `delete_recurring_event`), and
`ShiftPatternService` (`create_shift_pattern`, `update_shift_pattern`, `delete_shift_pattern`,
`set_day`, `delete_day`). Each gained an optional `on_calendar_data_changed: Callable[[], None] |
None = None` constructor parameter, called once immediately after that method's own
`session.commit()` succeeds (for `save_rule`, only on its `commit=True` path — when called with
`commit=False` from `seed_standard_week`, invalidation is deferred to `seed_standard_week`'s own
single commit, so seeding a full week invalidates the cache exactly once, not seven times).
`CalendarExceptionService` and `CalendarAssignmentService` were left unchanged since nothing they
touch is cached. In `platform_registry.py`, `EnterpriseCalendarResolver` construction was moved
earlier (it has no dependency on the write-side services) so `enterprise_calendar_resolver.
invalidate_cache` could be passed directly into the three services above — plain constructor
injection, no new global state or event bus. Verified with a standalone script (in-memory SQLite,
outside pytest, cleaned up automatically) exercising all 8 mutation paths end-to-end: each of
`save_rule`, `seed_standard_week`, `delete_rule`, `add_recurring_event`,
`delete_recurring_event`, `update_shift_pattern`, and `delete_day` correctly evicts the resolver's
corresponding cache entry, and a stale `resolve_calendar_context()` call that previously returned 0
available hours (rule not yet cached) correctly returns 8 available hours immediately after
`save_rule` adds one — no resolver restart or manual cache clear required. A full
`platform`+`architecture` regression shows the identical pre-existing failure/error set with zero
new failures.

---

## 1. Executive summary

**Architectural style today.** Platform is not a separate service or process — it is the
composition root and shared-kernel layer of the same single-process desktop application PM lives
in. **Platform and Project Management share the exact same SQLAlchemy `Session` object**, confirmed
end-to-end: `src/ui_qml/shell/app.py:59` creates one `session = SessionLocal()`, which flows into
`build_repository_bundle(session)` (`src/infra/composition/repositories.py:202`, one 66-field
dataclass holding both Platform's and PM's repositories), then into
`build_platform_service_bundle(session, repositories)` (`platform_registry.py:193`), and the
**identical** `session` object is passed again into `build_project_management_service_bundle(...)`
immediately after. Platform's bundle is built *first* (`app_container.py:401` vs PM's `:433`), and
Platform is also the layer that performs the one-time Postgres RLS wiring
(`configure_session_rls_context`/`validate_postgresql_execution_role`, `platform_registry.py:420-421`)
that PM's repositories then rely on without knowing it. There is no per-Platform-request session
boundary, no connection-pool boundary per operation, and — like PM — the existing Unit-of-Work
abstraction (`src/infra/persistence/db/unit_of_work.py`'s `session_scope()`) has **zero callers
anywhere in the repository**, confirmed by a repo-wide (not just Platform-scoped) grep.

**Structural layout.** Unlike PM's per-capability "mini-module" folders, Platform underwent a
"layer-first" restructure: `application/`, `domain/`, `contract/`, and
`infrastructure/persistence/{mappers,orm,repositories}/` are each internally grouped into the same
content taxonomy — nominally 8 groups (`tenant`, `master_data`, `history`, `security`, `approval`,
`time_management`, `data_operations`, `events`) — plus `access/`, `api/`, `common/` (flat),
`finance/` (flat, Money/Currency/Quantity value objects), and `integration/` (flat) as independent
packages. **The audit found this is actually 9 content groups in the persistence layer, not 8** —
`finance` (owning `financial_periods`) is a real, separate persistence group, not folded into an
existing one. `src/core/platform/` totals **521 Python files** (application 130, domain 81,
contract 52, mappers 40, orm 48, repositories 50, access 7, api 83, common 7, finance 12,
integration 9).

**How a desktop request reaches the database.** Same seam as PM: QML → a Platform desktop API class
(`api/desktop/<group>/<capability>.py`) → an application service → a repository contract
(`contract/**`) → a concrete `SqlAlchemy*Repository` → an ORM model → the one shared `Session`.
17 Platform desktop API classes are registered, totaling **130 public methods** — smaller in count
than PM's ~150 across 10 classes, but far more **skewed**: `EnterpriseCalendarDesktopApi` alone has
**39 methods (30% of all Platform desktop methods)**, fanning out to 7 injected collaborators —
Platform's clear structural analogue of PM's Dashboard fan-out, and larger. 12 of the other 16
classes are thin 1:1 wrappers around a single application service — a notably higher thin-wrapper
ratio than PM's ten capabilities. **Platform has no per-module desktop-API builder file analogous to
PM's `api/desktop_runtime/desktop_api_builder.py`** — all 17 Platform desktop API instances are
constructed inline, interleaved with PM/Inventory/Maintenance's own builder calls, directly inside
the single shared `src/application/runtime/desktop_api_registry.py:build_desktop_api_registry`
(lines 348-387). `src/application/` really did shrink to essentially one file, confirming
`docs/repo_structure_plan/PLATFORM_LAYER_FIRST_RESTRUCTURE.md`'s claim — but that one file is now
simultaneously the cross-module top-level orchestrator *and* Platform's own desktop-API assembly
site, a load Platform doesn't share with any other module.

**Are reads and writes currently separated?** No — same conclusion as PM, and for the same
structural reason (one shared repository contract, one shared session). Unlike PM, **no
comparable existing CQRS-shaped reader precedent was found anywhere in Platform** — PM's audit
found three pieces of pre-existing "raw material" for a clean split (`RateResolutionReader`,
`ApprovedTime/ProcurementFinancialSourceProvider`, and a `*QueryMixin` naming convention). This
audit's five research passes found no equivalent read-only `Protocol`/reader class, no
cursor-paginated generic page wrapper, and no consistent query/command method-naming split anywhere
in `src/core/platform/`. **A Platform CQRS effort would be starting from less existing precedent
than PM's did**, not more.

**Where domain entities and ORM objects cross boundaries.** Same convention as PM: domain
dataclasses, not ORM rows, cross from application services to desktop APIs, serialized once at the
desktop boundary. No repository or service was found returning a raw ORM object across a layer
boundary in any of the write/read paths traced.

**Major CQRS opportunities (evidence-backed, ranked).**

1. **Module entitlement read is a confirmed N+1, independent of scale.** `get_runtime_context` →
   `list_entitlements`/`shell_summary()` re-derives the full entitlement-record map from scratch
   *for every module in a list comprehension*, and `shell_summary()` repeats the entire
   `list_enabled`/`list_licensed`/`list_available`/`list_entitlements` cycle a second time — with
   just 5 built-in modules this issues on the order of **15-20 near-identical
   `SELECT * FROM organization_module_entitlements`** statements to answer one "what's entitled"
   question, with zero caching across calls. This is Platform's closest analogue to PM's Finance
   Snapshot finding, and it fires on **every app-context load**, not just an occasional report view.
2. **`TimesheetFinancialEventsMixin`'s per-entry loop is a confirmed, live N+1** (not just a
   structural risk): `for entry in entries: ... self._work_allocation_repo.get(entry.work_allocation_id)`
   (`application/time_management/time/timesheet_financial_events.py:31-35`) — `WorkAllocationRepository`
   exposes only `get(id)`, no batch form, so any batch of approved time entries triggers one query
   per entry.
3. **`PlatformUserDesktopApi._find_user` re-fetches and linearly scans the entire user list** after
   every `assign_role`/`revoke_role`/`reset_password` write (`security/auth/user.py:155-159`) — the
   same "write, then re-fetch the whole collection and scan for the one row just touched" shape the
   PM audit flagged for `Portfolio.create_project_dependency`.
4. **`EnterpriseCalendarDesktopApi._serialize_assignment` does a per-row `get_calendar()` lookup**
   for every assignment row returned, repeated across roughly 9 of that file's 39 methods — an N+1
   at the desktop-API layer itself, independent of what the underlying service does.
5. **Platform's own calendar-editing primitive has the exact defect the PM audit found (and
   recommended fixing) in PM's own now-deleted calendar adapter — and it is *worse* here.**
   `WorkingRuleService.save_rule` commits **inside itself**, once per call; `seed_standard_week`
   calls it 7 times sequentially for the 7 weekdays, producing **7 independent, non-atomic commits**
   for what a user experiences as "set up this calendar's working week" — a mid-loop failure leaves
   a partially-edited week with no compensating action. `CalendarWorkingRuleRepository`'s contract
   exposes only a singular `save()` — there is no batch primitive at the repository-contract level
   either, so this cannot be fixed by the caller alone.
6. **Every "totals"/rollup-shaped read in Platform is computed in Python over a materialized list**,
   exactly matching PM's module-wide finding: a repo-wide grep across all 21 Platform repository
   files for `func.sum`/`group_by` returns **zero matches**; `func.count` appears in exactly 4 narrow
   calendar-count call sites and nowhere else. No master-data rollup (employees per department,
   sites per organization, anything portfolio-shaped) exists at all — not even a materialize-then-
   `len()` version — the capability simply hasn't been built yet.

**Major risks of introducing CQRS incorrectly, specific to Platform.** (i) **Audit atomicity is
inconsistent within Platform itself, in a way a naive read-model consolidation could paper over.**
Three parallel audit-recording code paths exist: a strict, same-transaction, fail-closed tier
(approval decisions, financial periods, approved-timesheet events, role/permission governance via a
direct-repo bypass, and authentication/session events via a dedicated `add_atomic_auth_event` path
that has its own rollback-on-failure tests) and a lenient tier (all six master-data mutation
services — organization, site, employee, department, party, document — call the shared
`record_audit_entry` wrapper with its unsafe `commit=True` default, making the audit row a second,
separately-committed, silently-droppable write). A CQRS/UoW consolidation must not accidentally
promote every audit call to the lenient default, since the strict tier's behavior is deliberate and
test-verified (`test_auth_login_session_audit_atomicity.py` and siblings). (ii) **Tenant-scoping
coverage is far less uniform than PM's.** Several whole subsystems are architecturally global with
no `tenant_id` column at all (`users`, `auth_sessions`, `auth_policy_reconciliations`, `permissions`,
`role_permissions`, `notifications`), `roles`/`role_bindings`/`role_delegation_policies` use a
nullable-tenant "system vs. tenant" hybrid, and `audit_entries` has a `tenant_id` column but — unlike
its sibling `activity_entries` — **no database RLS policy at all**, an inconsistency in the wrong
direction (the more compliance-critical table is the one without the DB backstop). A CQRS reader
built naively on top of "the table has a tenant_id column" would need to separately verify RLS
actually protects it. (iii) **A confirmed, static-analysis-level bug exists in a live write path**:
`domain_events.resources_changed.emit(resource.id)` fires *inside* a per-resource loop in the
Employee→Resource cross-module sync, **before** `session.commit()` — if a later iteration or the
final commit fails, events have already fired for rows that get rolled back. Any read-model design
that trusts domain-event timing as a cache-invalidation signal must account for this. (iv) **Platform
hosts the shared `ApprovalService` but never routes its own mutations through it** — all 9 registered
approval request types belong to PM or Inventory/Procurement. Platform instead built two
disconnected, weaker pseudo-approval mechanisms of its own (a caller-suppliable, default-auto-approved
`approval_status` field on `CalendarException`, and a same-call re-review check in
`RoleGovernanceService.create_delegation_policy`). **This document does not recommend a mass
rewrite, event sourcing, a separate read database, or command/query handler classes** — the same
governing conclusion the PM audit reached, for the same reasons: the layering is sound, the
weaknesses are localized, and nothing found here requires or is helped by decomposing the process
boundary.

---

## Architectural Health Assessment

| Area | Assessment | Verified strength or weakness | Direction |
|---|---|---|---|
| Domain/persistence separation | Strong | No `relationship()` anywhere (21 ORM files checked); no ORM leakage across boundaries | Preserve |
| Layer-first composition structure | Good, with drift | Layer-first grouping is real and consistently applied, but `finance`/`integration` exist as both flat packages *and* duplicated layered application/contract/persistence models — two independent "financial period" and two independent "integration delivery" models coexist | Reconcile before building on either |
| Write transaction handling | Mixed, worse skew than PM | Every write-capable service commits its own transaction correctly (35 files); but Platform's own calendar-editing primitive re-introduces a defect PM already found and fixed on its own side | Standardize, starting with calendar |
| Audit/activity discipline | Inconsistent, three parallel implementations | A strict, test-verified tier (approval/finance/auth) coexists with a lenient, silently-droppable tier (all master-data writes) and a third hand-rolled bypass (role governance) | Consolidate onto one discipline |
| Read scalability | Weak, and starting from less precedent than PM | Full-list materialization is the default everywhere; zero SQL-side sum/group-by; a confirmed live N+1 on the most-frequently-hit read (module entitlements) | Introduce selective Readers |
| Tenant/security foundation | Good core mechanism, uneven table-by-table coverage | The two-layer (service check + DB RLS) pattern is real Platform infrastructure, turned on once for the whole process — but RLS coverage is genuinely inconsistent across tables, and `audit_entries` is a confirmed compliance-relevant gap | Correct independently, prioritize `audit_entries` |
| Session lifecycle | Structural risk, shared with PM | Identical single-process-lifetime session as PM — this is one shared risk, not two separate ones | Investigate jointly with PM, not separately |
| Approval governance | Good engine, Platform is host-only | `ApprovalService`'s own transaction handling is exemplary (handler → status → audit, one commit); Platform never uses it for its own writes and built weaker local substitutes instead | Route Platform's own governed writes through it, or explicitly decide not to |
| CQRS readiness | Lower than PM | No existing reader/Protocol precedent found anywhere in Platform, unlike PM's three | Will need to establish the pattern from scratch, likely importing PM's precedent rather than inventing a new one |

Explicitly, based on the evidence in this document:

- **No mass rewrite is justified.** Domain/persistence separation is strong and the write-commit
  discipline is fundamentally sound; weaknesses are localized to specific paths (calendar editing,
  master-data audit defaults, module-entitlement reads), not systemic.
- **No microservice split is justified.** Nothing found — not the shared session, not the audit
  inconsistency, not the entitlement N+1 — requires or benefits from a process-boundary split.
- **No event sourcing is proposed.** Platform's domain-event signals remain UI-refresh triggers (with
  one confirmed dead signal, `calendars_changed`, and one confirmed pre-commit-emission bug), not a
  candidate event store.
- **No separate read database is proposed.** The one shared session/database already supports the
  SQL-projection pattern a Platform reader would need.
- **Any Platform CQRS work should be scoped to the module-entitlement read** as the first candidate —
  it is the one finding with PM Finance-Snapshot-grade evidence (an exact, reproducible, per-call
  redundant-query count) and it fires on every session's context load, giving it outsized reach for
  a narrowly-scoped pilot.

---

## 2. Audit scope and repository areas inspected

**Platform-owned files** (primary scope, `src/core/platform/`):
- `application/**`, `domain/**`, `contract/**` — every file across all 8 declared + 1 undeclared
  (`finance`) content groups: `tenant`, `master_data`, `history`, `security` (auth + authorization +
  identity), `approval`, `time_management` (calendar + time), `data_operations`, `events`, `finance`.
- `infrastructure/persistence/{mappers,orm,repositories}/` — every file across the same groups.
- `access/**` — `AccessControlService` and its own domain objects (a package with no `contract`/
  `infrastructure` sublayer of its own, structurally distinct from every other Platform package).
- `api/desktop/**` — all 17 desktop API classes, their DTOs/commands/models, `api/desktop_runtime/
  service_resolver.py`.
- `common/**`, `finance/**` (flat value objects), `integration/**` (flat).

**Composition/infrastructure dependencies inspected** (`src/infra/`):
- `composition/app_container.py`, `composition/platform_registry.py`, `composition/repositories.py`,
  `composition/project_registry.py` (for cross-references), `composition/inventory_registry.py`
  (for cross-references), `composition/maintenance_registry.py` (for cross-references).
- `persistence/db/session_factory.py`, `persistence/db/postgresql_rls.py`,
  `persistence/db/unit_of_work.py`, `persistence/db/optimistic.py`.
- `persistence/migrations/versions/h6i7j8k9l0m1_enable_postgresql_tenant_rls.py` and
  `persistence/migrations/helpers/postgresql_rls.py` — the two independent DB-level RLS-enabling
  mechanisms.
- `application/runtime/desktop_api_registry.py` — the single cross-module top-level orchestrator.

**Shared-kernel dependencies inspected** (`src/core/shared/`):
- `events/domain_events.py`, `events/signal.py` — the signal bus, shared by Platform and every
  business module.
- `audit/audit_recorder.py`, `activity/activity_recorder.py` — the `record_audit_entry`/
  `record_activity` wrapper functions every module's services call.
- `notifications/safe_dispatch.py` — cross-referenced from PM's @mention flows into Platform's
  `NotificationService`.

**UI consumers inspected (grep-level, not redesigned)**:
- `src/ui_qml/shell/app.py`, `src/ui_qml/shell/login.py`, `src/ui_qml/shell/runtime_session.py` —
  process bootstrap, login flow, and the 30-second forced-heartbeat revalidation timer.
- `src/ui_qml/platform/**` — grepped for desktop API method call sites and for the
  `admin_domain_event_binder.py`'s signal subscriptions; not opened for redesign.

**Tests inspected**: `src/tests/platform/` (99 files, 666 `def test_` functions, flat directory, no
skip/xfail markers found), plus the 9 files under `src/tests/architecture/` that reference
`core.platform` (`test_architecture_guardrails_legacy_orm.py`,
`test_architecture_guardrails_services.py`, `test_architecture_guardrails_size_migration.py`,
`test_financial_period_architecture.py`, `test_pm_desktop_adapter_architecture.py`,
`test_pm_phase0c_repository_scope_architecture.py`, `test_project_finance_a2_architecture.py`,
`test_project_finance_persistence_guardrails.py`, `test_service_architecture.py`).

**Architecture decision records cross-checked against this audit's findings**
(`docs/architecture_decisions/`): ADR-001 (Cross-Platform Ownership), ADR-002 (Location/System
Ownership — not relevant to Platform's own findings), ADR-003 (Tenancy and Authorization
Authority), ADR-004 (Calendar Assignment Split Ownership), ADR-005 (Domain Events — status
**proposed**, not yet accepted), ADR-PF-008 (Approval Unit of Work). Corrections and corroborations
this cross-check produced are folded into §10, §11, §18, and the affected write/read-path findings
directly, with each one flagged inline as it occurs.

**Explicitly not in scope for this pass**: full semantic review of every service body in
`application/**` (§9's repository/persistence audit and §6/§7's traces cover the write/read paths
that were actually followed; a large residual of Platform service logic was not opened line-by-line).
`src/core/platform/api/desktop/support/support.py` (`PlatformSupportDesktopApi`) was inventoried in
§5 but is explicitly out of scope for any CQRS/session-based split — it performs file/OS/network I/O
with zero application-service dependency, a fundamentally different risk profile than every
DB-backed capability in this document.

---

## 3. Complete relevant repository structure

### 3a. `src/core/platform/` — full annotated tree

```text
src/core/platform/                          # 521 Python files total (excl. __init__.py/cache)
├── application/                            # 130 files — largest layer
│   ├── tenant/
│   │   ├── tenancy/        tenant_membership_service.py (826), tenant_context.py (570),
│   │   │                   tenant_admin_service.py (243), context_policy.py
│   │   └── modules/        module_catalog_mutation.py (190), module_catalog_query.py (147),
│   │                       module_catalog_service.py (137), guard.py, authorization.py
│   ├── master_data/        (24 files)
│   │   ├── documents/      document_service.py (586), document_integration_service.py (344)
│   │   ├── data_exchange/  service.py (478) — APPLICATION-ONLY, no domain/contract/persistence peer
│   │   ├── site/           site_service.py (334)
│   │   ├── org/            organization_service.py (313)
│   │   ├── party/          party_service.py (297)
│   │   ├── employee/       employee_service.py (255), employee_support.py (194)
│   │   └── department/     department_commands.py (239), department_service.py, department_queries.py,
│   │                       department_location_service.py, department_validation.py,
│   │                       department_context.py, department_access.py, department_utils.py
│   ├── history/            activity/activity_service.py, audit/enterprise_audit_service.py (≤150 each)
│   ├── security/           (41 files)
│   │   ├── auth/           credentials/ (authentication_transactions.py 312),
│   │   │                   session/ (session_service.py 355, context_switch_service.py 206,
│   │   │                   principal_builder.py 171), provisioning/ (registration_service.py 416,
│   │   │                   user_admin_service.py 215, platform_owner_provisioning_service.py 193),
│   │   │                   audit/ (security_audit.py 166), auth_service.py (380)
│   │   ├── authorization/  roles/ (role_governance_service.py 797, tenant_role_administration_service.py
│   │   │                   648, role_policy_reconciliation_service.py 403,
│   │   │                   canonical_role_resolver.py 361, role_assignment_service.py 212,
│   │   │                   scope_delegation_provisioning_service.py 167),
│   │   │                   enforcement/ (permission_checks.py 189, target_user_authorization.py 218,
│   │   │                   session_authorization_engine.py, sod_enforcer.py)
│   │   └── identity/       service_principal_service.py (499) — 3rd security sub-group, sibling of
│   │                       auth/authorization, present across application/domain/contract/orm/
│   │                       repositories but ABSENT from mappers/ (see 3c anomaly #5)
│   ├── approval/           approval_service.py (459)
│   ├── time_management/    (22 files)
│   │   ├── calendar/       capacity/enterprise_calendar_resolver.py (593),
│   │   │                   enterprise_calendar_service.py (356),
│   │   │                   assignment/calendar_assignment_service.py (288),
│   │   │                   capacity/working_time_calculator.py (233),
│   │   │                   definitions/{shift_pattern_service.py 190, recurring_event_service.py 178,
│   │   │                   calendar_exception_service.py 177, working_rule_service.py},
│   │   │                   capacity/global_calendar_shim.py
│   │   └── time/           timesheet_support.py (440), timesheet_periods.py (318),
│   │                       timesheet_entries.py (262), timesheet_review.py (201),
│   │                       timesheet_query.py (168), time_service.py,
│   │                       timesheet_financial_events.py (the confirmed N+1 file)
│   ├── data_operations/    importing/csv_import_runtime.py (228),
│   │                       runtime_tracking/runtime_execution_service.py (212),
│   │                       report_runtime/*, exporting/*, importing/import_definition_registry.py
│   ├── events/             notifications/notification_service.py (≤150)
│   ├── finance/            PSEUDO-GROUP, no domain/finance peer — financial_period_service.py (355)
│   └── integration/        PSEUDO-GROUP, no domain/integration peer — delivery_service.py (404)
├── domain/                                 # 81 files
│   ├── tenant/ (10)        tenancy/user_tenant_membership.py (493), tenancy/tenant.py (110)
│   ├── master_data/ (19)   documents/document.py (304), party/party.py (227), site/site.py (215)
│   ├── history/ (5)        ≤150 lines each
│   ├── security/ (20)      auth/user.py (579), auth/session.py (531 — UserSessionContext),
│   │                       authorization/roles/role_permission_catalog.py (440),
│   │                       identity/service_principal.py (248)
│   ├── approval/ (4)       approval_request.py (184), approval_state.py, policy.py
│   ├── time_management/ (5) calendar/enterprise_calendar.py (1408 — LARGEST FILE IN ALL OF PLATFORM),
│   │                       time/timesheet_models.py (302)
│   ├── data_operations/ (12) runtime_tracking/runtime_execution.py (290)
│   ├── events/ (5)         ≤150 lines each
│   ├── finance/            DOES NOT EXIST (0 files)
│   └── integration/        DOES NOT EXIST (0 files)
├── contract/                                # 52 files
│   ├── tenant/, master_data/, history/, approval/, time_management/, events/  — mostly ≤150 lines
│   ├── data_operations/ (3) — runtime_tracking ONLY; no exporting/importing/report_runtime contracts
│   ├── security/ (8)       auth/auth_repository.py (283, FLAT — no credentials/session/provisioning
│   │                       split unlike application/domain), authorization/enforcement/
│   │                       authorization_engine.py (77, the AuthorizationEngine Protocol — no
│   │                       roles/ subfolder despite domain+application both having one),
│   │                       identity/contracts.py (57)
│   ├── finance/ (2)        PSEUDO-GROUP — periods.py (48)
│   └── integration/ (2)    PSEUDO-GROUP — delivery.py (78)
├── infrastructure/persistence/
│   ├── mappers/ (40 files, 8 groups — data_operations mapper group ABSENT, identity mapper ABSENT)
│   ├── orm/ (48 files, 9 groups incl. finance; 40 __tablename__ tables total)
│   └── repositories/ (50 files, 9 groups incl. finance; + 1 stray `_tenant_scope.py` at the root)
├── access/ (7 files)        application/access_control_service.py (506), domain/access_scope.py (135),
│                            domain/feature_access.py (69), authorization.py (65, package-root, loose)
│                            — NO contract/ or infrastructure/ sublayer; no 8-group subdivision
├── api/ (83 files)          desktop/{access,approval,finance,history/{activity,audit},integration,
│                            master_data/{department,documents,employee,org,party,site},
│                            platform_runtime,security/{auth,identity},support,tenant/tenancy,
│                            time_management/calendar}/*.py + models/; desktop_runtime/service_resolver.py
├── common/ (7 files, flat)  code_generation.py (219), exceptions.py, ids.py, pydantic.py,
│                            runtime_access.py, service_base.py
├── finance/ (12 files, flat) money/{money,currency,quantity,rounding,serialization,
│                            currency_resolution,_decimal}.py, periods/financial_period.py (388,
│                            VALUE-OBJECT model — see 3c anomaly #2), precision.py (stray, not in money/)
└── integration/ (9 files, flat) module_registry.py (200), resolver.py (153),
                             cross_module_reference.py (83), delivery.py (326, SERVICE model —
                             see 3c anomaly #3), events.py, procurement_events.py (167),
                             time_events.py (77), canonical_json.py (47)
```

### 3b. Persistence-layer size table (mappers → ORM → repositories, per group)

| Group | mappers largest | orm largest | repositories largest |
|---|---|---|---|
| tenant | tenancy/user_tenant.py (50) | tenancy/user_tenant.py (89) | modules/modules.py (172) |
| master_data | documents/documents.py (131) | documents/documents.py (155) | documents/documents.py (324) |
| history | audit/audit_entry.py (87) | audit/audit_entry.py (61) | audit/audit_entry.py (99) |
| security | auth/auth.py (269) — no identity/ mapper | auth/auth.py (405); identity/identity.py (90) | auth/auth.py (772); identity/identity.py (287) |
| approval | approval.py (64) | approval.py (58) | approval.py (195) |
| time_management | calendar/enterprise_calendar.py (394) | calendar/enterprise_calendar.py (376); stray time_financial_outbox.py (19) | calendar/enterprise_calendar.py (**1010**); stray time_financial_outbox.py (12) |
| data_operations | does not exist | runtime_tracking.py (73) | runtime_tracking.py (189) |
| events | platform_events.py (61) | platform_events.py (38) | platform_events.py (81) |
| finance | financial_period.py (57) | financial_period.py (129) | financial_period.py (172) |

`infrastructure/persistence/repositories/_tenant_scope.py` (186 lines) sits directly under
`repositories/` with no group — the shared `TenantScopedRepositorySupport`/
`TenantParentScopedRepositorySupport` base classes most (not all — see §9a) Platform repositories
extend.

### 3c. Confirmed structural anomalies (directory/line-count inspection)

1. **`domain/finance/` and `domain/integration/` do not exist** — `finance` and `integration` are
   pseudo-content-groups under `application/`/`contract/`(/`persistence` for finance) only.
2. **Two independent "financial period" models coexist**: the layered
   `application/finance/financial_period_service.py` (355) + `contract/finance/periods.py` (48) +
   full persistence trio (a real, DB-backed, RLS'd aggregate — see §9), **versus** the flat
   `finance/periods/financial_period.py` (388), a value-object-style model with no persistence
   layer of its own. Their semantic relationship (legacy holdover vs. deliberate split) was not
   resolved in this pass and should be reconciled before any read-model work touches "financial
   period."
3. **Two independent "integration delivery" models coexist**: flat `integration/delivery.py` (326)
   vs. layered `application/integration/delivery_service.py` (404) + `contract/integration/
   delivery.py` (78).
4. **`contract/security/authorization/` has no `roles/` subfolder** despite both `domain` and
   `application` having large `authorization/roles/` content (role governance, delegation, canonical
   resolution, 797+648+403+361+212+167 = 2588 lines across 6 files) — no formal contract exists for
   role assignment/governance.
5. **`mappers/data_operations/` and `mappers/security/identity/` do not exist**, while the
   corresponding `orm/`/`repositories/` groups do — `identity.py`'s and `runtime_tracking.py`'s
   ORM↔domain translation is done inline inside the repository file rather than a separate mapper
   module (confirmed in §9b).
6. **`master_data/data_exchange` is application-layer only** (478 lines, `MasterDataExchangeService`)
   — no domain, contract, or persistence counterpart at all.
7. **`access/` has no `contract/`/`infrastructure/` sublayer** and no 8-group subdivision — a
   structurally different package shape from every other Platform package.
8. Stray files outside any group bucket: `repositories/_tenant_scope.py`,
   `orm/time_management/time_financial_outbox.py`, `repositories/time_management/
   time_financial_outbox.py`, `finance/precision.py`.

---

## 4. Runtime composition and dependency graph

### 4a. Bootstrap call chain (verified end-to-end, file:line)

```text
src/ui_qml/shell/app.py:44   build_services()
  → app.py:59   session = SessionLocal()          # ONE session, shared with PM/Inventory/Maintenance
  → app.py:62   services = build_service_dict(session)
      → app_container.py:604 build_service_graph(session)
          → app_container.py:396 repositories = build_repository_bundle(session)
                — repositories.py:202-289 — constructs BOTH Platform's and every business module's
                  repositories from the SAME `session`, in one 66-field `RepositoryBundle` dataclass
          → app_container.py:401 platform_services = build_platform_service_bundle(session, repositories)
                — platform_registry.py:193-678   [PLATFORM BUILT FIRST]
          → app_container.py:433 project_management_services = build_project_management_service_bundle(
                session, repositories, platform_services, …)
          → (inventory_procurement, maintenance service bundles, also fed platform_services)
      → app_container.py:273-390  ServiceGraph.as_dict()
  → app.py:68   desktop_api_registry = build_desktop_api_registry(services)
      → desktop_api_registry.py:155
          → constructs Platform's 17 desktop APIs INLINE at lines 348-387 — no separate
            `build_platform_desktop_runtime_apis` factory exists, unlike PM/Inventory/Maintenance
          → line 320/330/337: delegates to each business module's own desktop-runtime builder
  → app.py:69   services["desktop_api_registry"] = desktop_api_registry
```

**Confirmed: `src/application/` really did shrink to one file** (`runtime/desktop_api_registry.py`)
per the repo-structure plan's stated goal, but that file carries a double load Platform alone bears:
cross-module orchestrator *and* Platform's own desktop-API assembly site.

### 4b. Runtime object table — 20 Platform services, all constructed once in `build_platform_service_bundle`

| Service | Constructed at | Key deps | Consumed by |
|---|---|---|---|
| `user_session` (`UserSessionContext`) | `platform_registry.py:209` | none (default ctor) | every application service across all modules taking `user_session=`; wired with `set_validator`/`set_context_listener` back to `auth_service` at `:308-309` |
| `tenant_context_service` (`TenantContextService`) | `:217-225` | `tenant_repo`, `organization_repo`, `user_session`, `user_tenant_repo`, `context_policy` | 161 files repo-wide take this param; reflectively backfilled onto 2 repos post-construction (§4c) |
| `enterprise_audit_service` | `:231-236` | `session`, `audit_entry_repo`, `user_session`, `tenant_context_service` | `financial_period_service`, `organization_service`, `document_service`, `party_service`, `site_service`, `department_service`, `employee_service`, `auth_service`, `service_principal_service`, PM's `CostService` |
| `notification_service` | `:244-248` | `session`, `notification_repo`, `user_session` | `approval_service`, `tenant_membership_service`, PM's `TaskService`/`CollaborationService` |
| `activity_service` | `:249-254` | `session`, `activity_repo`, `user_session`, `tenant_context_service` | `PlatformActivityDesktopApi`; every PM write-path's `record_activity(...)` call — **never called by any Platform service itself**, confirmed by grep (§12) |
| `approval_service` | `:255-266` | `session`, `approval_repo`, `user_session`, `enterprise_audit_service`, `tenant_context_service`, `notification_service`, role/permission repos | PM's `project_registry.py` (5 apply handlers), Inventory's `inventory_registry.py` (2 request types/4 handlers), `PlatformApprovalDesktopApi` — Platform itself registers zero handlers (§4d) |
| `auth_service` | `:267-301` | `session`, user/role/permission/session repos, `user_session`, `enterprise_audit_service`, `tenant_context_service`, canonical scope resolvers | `tenant_context_service` (callbacks wired back at `:302-309`), `role_governance_service` (`:491`), `PlatformUserDesktopApi`, `service_principal_service` |
| `role_governance_service` | `:472-490` | `session`, role/delegation/permission/user/tenant/membership/audit repos, `user_session`, `tenant_context_service`, scope resolvers | `auth_service.set_role_governance_service(...)` |
| `access_service` (`AccessControlService`) | `:505-527` | `session`, `user_repo`, `auth_service`, `policy_registry`, scope resolvers, `user_session`, `enterprise_audit_service`, `tenant_context_service`, `role_governance_service`, role repos | `PlatformAccessDesktopApi`; cross-module scope-target loaders in `desktop_api_registry.py:217-259` |
| `organization_service` | `:320-326` | `session`, `organization_repo`, `user_session`, `enterprise_audit_service`, `tenant_context_service` | `PlatformRuntimeApplicationService`, `_bootstrap_local_single_tenant_context` |
| `department_service` | `:402-411` | `session`, dept/org/site/employee repos, `user_session`, `enterprise_audit_service`, `tenant_context_service` | `PlatformDepartmentDesktopApi` |
| `site_service` | `:394-401` | `session`, `site_repo`, `organization_repo`, `user_session`, `enterprise_audit_service`, `tenant_context_service` | `PlatformSiteDesktopApi`, `MasterDataExchangeService`, the access-scope loader in `desktop_api_registry.py` |
| `employee_service` | `:541-551` | `session`, employee/resource/site/dept/org repos, `tenant_context_service`, `user_session`, `enterprise_audit_service` | `PlatformEmployeeDesktopApi`; injected into PM's desktop-runtime as `ProjectManagementDesktopRuntimePlatformDependencies.employee_service` |
| `service_principal_service` | `:492-504` | `session`, principal/api-key/user/tenant/org/membership/audit repos, `auth_service`, `user_session`, `tenant_context_service` | `PlatformIdentityDesktopApi` |
| `financial_period_service` | `:237-243` | `session`, `financial_period_repo`, `tenant_context_service`, `user_session`, `enterprise_audit_service` | `FinancialPeriodDesktopApi` |
| `enterprise_calendar_service` | `:560-569` | `session`, calendar/assignment/org/working-rule/exception repos, `user_session`, `tenant_context_service` | `EnterpriseCalendarDesktopApi`; bootstraps the org's global calendar at `:622-629` |
| `enterprise_calendar_resolver` | `:607-618` | live `organization_id` closure, 7 calendar/assignment repos, `working_time_calculator`, `shift_pattern_repo` | `global_calendar_shim`; PM's `EnterpriseResourceAvailabilityService`, `ResourceCapacityCalculator`, `ProjectCalendarAdapter` |
| `global_calendar_shim` | `:619` | `resolver=enterprise_calendar_resolver` | exposed as `work_calendar_engine` (`app_container.py:251,573`); consumed by PM's `TaskService`, `SchedulingEngine`, `ReportingService`, `BaselineService`, `DashboardService` |
| `working_time_calculator` | `:559` | none | feeds `enterprise_calendar_resolver`; exposed to `EnterpriseCalendarDesktopApi` |
| `module_catalog_service` | `:422-435` | `modules`, `enabled_codes`, `licensed_codes`, `entitlement_repo`, `session`, `user_session`, `enterprise_audit_service`, org-context provider | `PlatformRuntimeApplicationService`, `ModuleRegistry`, `IntegrationResolver` — the confirmed N+1 read lives here (§7's B7) |
| `runtime_execution_service` | `:448-455` | `runtime_execution_repo`, `tenant_context_service`, `user_session` | exposed on `ServiceGraph`; no confirmed downstream `.method()` call site found — flagged unconfirmed, not asserted unused |

### 4c. Optional dependencies, unused constructions, shared singletons

- **A module-level authorization singleton bypasses composition entirely.**
  `application/security/authorization/enforcement/session_authorization_engine.py:118`:
  `_authorization_engine: AuthorizationEngine = SessionAuthorizationEngine()` — constructed at
  **import time**, not inside `build_platform_service_bundle`. Every permission check in the whole
  codebase routes through `get_authorization_engine()` (`:121-122`), including PM's
  `collaboration_comments.py:53` and `tasks/commands/assignment.py:415` — a dependency any CQRS
  reader design needs to account for explicitly, since it can't be swapped via the normal
  composition graph.
- **`UserSessionContext` — exactly one production construction site** (`platform_registry.py:209`;
  confirmed by repo-wide grep for `UserSessionContext(` outside tests), then two-way wired: `auth_service`
  patches callbacks onto it *after* it's built.
- **`TenantContextService` has a dead-in-production fallback construction path**:
  `EmployeeService.__init__` (`employee_service.py:54-61`) builds its own
  `TenantContextService(...)` if none is injected and `organization_repo` is present. In actual
  composition `EmployeeService` always receives the real singleton (`platform_registry.py:548`), so
  this branch never fires on the desktop build path — a live "constructs its own collaborator if not
  injected" pattern, distinct from but analogous to the reflective-patch finding below.
- **Reflective post-hoc dependency patching, on Platform's own repositories** —
  `repositories.py:270-277` constructs `service_principal_repo`/`api_key_credential_repo` with
  `tenant_context_service=None` (the real service doesn't exist yet at that point in bootstrap), then
  `platform_registry.py:226-230` loops every field on `RepositoryBundle` and reflectively sets
  `_repo._tenant_context_service = tenant_context_service` on any repo exposing that private
  attribute. This is "construct as `None`, patch later by reaching into private state," originating
  in Platform's own composition code — the same anti-pattern class the PM audit flagged, here found
  at its source.
- **`GlobalCalendarShim`/`EnterpriseCalendarResolver`** — each constructed exactly once
  (`platform_registry.py:607`, `:619`), deliberately shared into 5 PM application services plus 3
  more PM helper classes. **This cross-module sharing, and the `ProjectCalendarAssignment`/
  `ResourceCalendarAssignment` tables living in PM rather than Platform despite being two more
  rungs on the same calendar-assignment ladder as Site/Department/Employee, is deliberate, documented
  architecture — ADR-004 (Calendar Assignment Split Ownership, accepted) — not an anomaly this audit
  is the first to notice.** ADR-004 explains the split follows FK ownership (PM owns `project_id`/
  `resource_id`) while keeping one unified service/resolver API via `Any`-typed constructor
  parameters and function-local imports, enforced by
  `test_platform_calendar_does_not_import_project_management_at_module_scope`. ~~`EnterpriseCalendarResolver.invalidate_cache()` exists but **has zero
  callers anywhere** (grep-confirmed) — its `_rules_cache`/`_recurring_cache`, shared as a singleton
  across all those consumers, can silently serve stale rules after any calendar write in the same
  process. This matters directly for §6's finding that `working_rule_service.py` writes carry no
  cache-invalidation hook at all.~~ **FIXED 2026-08-12, P0.6** — see "P0 correctness/security
  remediation status" above.
- **`unit_of_work.py`'s `session_scope()` — zero callers repo-wide**, confirmed independently of and
  in addition to the PM audit's identical finding — this is a whole-application dead abstraction, not
  a PM-specific one.
- **Optimistic-concurrency helpers (`update_with_version_check`/`delete_with_version_check`) are used
  by 10 Platform repositories** (financial_period, all 6 master-data repos, `auth.py`,
  `tenant.py`/`user_tenant.py`) — a repository-level concurrency mechanism, contrasting with PM's
  more application-service-level `expected_version` checks; worth reconciling if a future CQRS
  write-model standardizes on one pattern.
- **No confirmed-unused services** — every field on `PlatformServiceBundle` (30 fields) is consumed
  by something, except `runtime_execution_service`, whose only confirmed consumer is a pass-through
  export on `ServiceGraph` — flagged as "consumer not verified," not "confirmed dead."

### 4d. Approval apply/reject handler registrations

`ApprovalService` is a generic engine with **zero built-in handlers** — `self._apply_handlers`/
`self._reject_handlers` start empty, populated only via `register_apply_handler`/
`register_reject_handler` called from elsewhere. **Confirmed: Platform itself registers no governed-
approval handlers of its own** — `build_platform_service_bundle` constructs `ApprovalService` but
never calls either registration method. All registrations happen in *consumer* registries:

| Registrar | request_type(s) | Handler |
|---|---|---|
| `src/infra/composition/project_registry.py:812-855` (`_register_project_management_approval_handlers`) | `baseline.create`, `dependency.add`, `dependency.remove`, `cost.add`/`update`/`delete`, `budget.approve`, `project_cost.approve`, `financial_change.apply`, `project_billing_preparation.approve` | PM's internal `_apply_*_decision(..., commit=False)` methods |
| `src/infra/composition/inventory_registry.py:255-270` | `purchase_requisition.submit`, `purchase_order.submit` | Inventory's `apply_submitted_*_approval`/`_rejection` |
| `src/infra/composition/maintenance_registry.py` | — | **none confirmed** — no `approval_service.register_*` calls found |

Platform's only role in approval is hosting the generic engine, its permission gates
(`approval.request`/`approval.decide`), and the generic decide UI (`PlatformApprovalDesktopApi`,
consumed by `ui_qml/platform/presenters/control_queue_presenter.py`). A grep for `request_change(`
confirms Platform's own application code **never submits its own governed-change requests** — it is
infrastructure for other modules' governance, not a participant. Two places Platform built weaker,
disconnected substitutes instead: `CalendarExceptionService.add_exception`/`update_exception` accepts
a caller-supplied `approval_status` (default `"APPROVED"`, i.e. auto-approved) with its own local
`ApprovalStatus` enum unconnected to the real `domain/approval/approval_state.py` enum; and
`RoleGovernanceService.create_delegation_policy`'s "staleness re-review" is a same-call validation
check, not a pending/decide-later workflow.

---

## 5. Desktop API inventory

**Migration status check**: `docs/repo_structure_plan/README.md`'s many references to
`src/api/desktop/platform/*` are **stale documentation** — `src/api/` does not exist anywhere in the
current tree (confirmed: `find src/api` returns nothing). The actual code already lives at
`src/core/platform/api/desktop/` with layer-first, content-group grouping.

### 5a. Registry — 17 Platform desktop API classes (`src/application/runtime/desktop_api_registry.py`)

| Registry key | Class | File | Methods |
|---|---|---|---|
| `integration_capability` | `IntegrationCapabilityDesktopApi` | `integration/capability_api.py` | 7 |
| `platform_runtime` | `PlatformRuntimeDesktopApi` | `platform_runtime/runtime.py` | 7 |
| `platform_enterprise_calendar` | `EnterpriseCalendarDesktopApi` | `time_management/calendar/enterprise_calendar.py` | **39** |
| `platform_site` | `PlatformSiteDesktopApi` | `master_data/site/site.py` | 4 |
| `platform_department` | `PlatformDepartmentDesktopApi` | `master_data/department/department.py` | 5 |
| `platform_employee` | `PlatformEmployeeDesktopApi` | `master_data/employee/employee.py` | 3 |
| `platform_access` | `PlatformAccessDesktopApi` | `access/access.py` | 6 |
| `platform_approval` | `PlatformApprovalDesktopApi` | `approval/approval.py` | 3 |
| `platform_activity` | `PlatformActivityDesktopApi` | `history/activity/activity.py` | 1 |
| `platform_enterprise_audit` | `PlatformEnterpriseAuditDesktopApi` | `history/audit/audit_enterprise.py` | 2 |
| `platform_financial_periods` | `FinancialPeriodDesktopApi` | `finance/financial_period.py` | 6 |
| `platform_document` | `PlatformDocumentDesktopApi` | `master_data/documents/document.py` | 10 |
| `platform_party` | `PlatformPartyDesktopApi` | `master_data/party/party.py` | 4 |
| `platform_support` | `PlatformSupportDesktopApi` | `support/support.py` | 10 |
| `platform_tenant` | `PlatformTenantDesktopApi` | `tenant/tenancy/tenant.py` | 5 |
| `platform_user` | `PlatformUserDesktopApi` | `security/auth/user.py` | 11 |
| `platform_identity` | `PlatformIdentityDesktopApi` | `security/identity/identity.py` | 7 |

(`platform_calendar` is a dead registry key, explicitly `None`, superseded by
`platform_enterprise_calendar`.) **Total: 130 public methods across 17 classes** — compare PM's
~150 methods across 10 classes (largest, Tasks, ≈17% of PM's total) vs. Platform's largest
(Enterprise Calendar, 30% of Platform's total) — a materially more skewed distribution.

**No dedicated Organization desktop API exists.** CRUD lives inside `PlatformRuntimeDesktopApi`
(`list_organizations`/`provision_organization`/`update_organization`/`set_active_organization`),
while `master_data/org/models/organization.py` holds only DTOs/commands, no facade class. Separately,
**four other capabilities each implement their own `get_context() → OrganizationDto`** (Site,
Department, Party, Document), each calling their own service's `get_context_organization()` —
**five independent code paths converging on the same `serialize_organization()` helper**
(`support/_support.py`) — a real duplication finding: four master-data services each appear to
implement their own organization-context query rather than sharing one.

### 5b. Per-capability method inventory (full detail for the largest/most notable; abbreviated for thin wrappers)

**`EnterpriseCalendarDesktopApi` (39 methods)** — fans out to 7 collaborators
(`EnterpriseCalendarService`, `WorkingRuleService`, `CalendarExceptionService`,
`RecurringEventService`, `ShiftPatternService`, `CalendarAssignmentService`,
`EnterpriseCalendarResolver`, plus optional `capacity_calculator`). Covers calendar CRUD (6),
working-rule CRUD (3), exception CRUD (4), recurring-event CRUD (4), shift-pattern + day CRUD (6),
assignment CRUD across site/department/employee/project/resource (6 assign + 1 generic remove + 4
list), plus 5 read/report methods: `resolve_calendar_context`, `calculate_working_days` (confirmed
N+1 — loops day-by-day calling the resolver once per candidate day, bounded by
`min(max(working_days*7, 730), 365*40)` iterations, with real date-arithmetic implemented directly
in the desktop API method body — structurally identical to the PM audit's flagged
`SchedulingDesktopApi.calculate_working_days` finding), `get_source_chain`,
`calculate_resource_capacity`. The private `_serialize_assignment` helper (called from 9 of the 39
methods) does one extra `get_calendar(assignment.calendar_id)` lookup per row.

**`PlatformUserDesktopApi` (11 methods)** — `list_users`, `list_roles`, `create_user`,
`update_user`, `assign_role`, `revoke_role`, `set_user_active`, `reset_password`,
`unlock_user_account`, `force_user_password_reset`, `revoke_user_sessions`. **Confirmed N+1**:
`_find_user` (`:155-159`) calls `list_users()` and linearly scans for a match, invoked after every
`assign_role`/`revoke_role`/`reset_password`.

**`PlatformDocumentDesktopApi` (10 methods)** — clean 1:1 fan-in to `DocumentService`: `get_context`,
`list_documents`, `list_document_structures`, `create_document`, `update_document`,
`create_document_structure`, `update_document_structure`, `list_links`, `add_link`, `remove_link`.

**`PlatformSupportDesktopApi` (10 methods)** — architecturally distinct from every other Platform
desktop API: constructed with **zero application services**, talks directly to
`src/infra/platform/{diagnostics,operational_support,path,update,updater,version}.py` and
`PySide6.QtCore.QSettings`. Does not use the shared `execute_desktop_operation` helper — bespoke
error handling per method. Covers incident IDs, settings load/save, path resolution (with
filesystem mkdir side effects), update checks, activity-log tail, diagnostics export, incident
report creation, and self-update install (downloads a file, hash-verifies, launches a Windows-only
installer handoff that terminates the app). **Out of scope for any Session-based CQRS split** — its
I/O is files/OS/network, not ORM.

**`PlatformRuntimeDesktopApi` (7 methods)** — `get_runtime_context` (the confirmed N+1 read),
`list_organizations`, `list_modules`, `patch_module_state`, `provision_organization`,
`update_organization`, `set_active_organization`. Reimplements `execute_desktop_operation`/error
mapping as private methods instead of reusing the shared `support/_support.py` helper every other
capability uses.

**`PlatformIdentityDesktopApi` (7 methods)** — clean 1:1 wrapper to `ServicePrincipalService`:
`list_service_principals`, `create_service_principal`, `disable_service_principal`,
`list_api_keys`, `issue_api_key`, `rotate_api_key`, `revoke_api_key`.

**`IntegrationCapabilityDesktopApi` (7 methods)** — a frozen dataclass, not a conventional class:
`is_module_enabled`, `has_capability`, `can_use_integration`, `capability_snapshot`,
`list_integration_capabilities`, `resolve_reference`, `resolve_soft_reference`. Not wrapped in the
shared `DesktopApiResult` envelope, unlike every other Platform desktop API.

**`PlatformAccessDesktopApi` (6 methods)** — `list_scope_types`, `list_scope_targets` (wired against
externally-injected, cross-module loader closures reaching into PM's `ProjectService`, Inventory's
storeroom service, Maintenance's asset/location services — the one Platform capability that is
explicitly cross-module by design), `list_scope_role_choices`, `list_scope_grants`,
`assign_scope_grant`, `remove_scope_grant`.

**`FinancialPeriodDesktopApi` (6 methods)** — `list_periods`, `get_period`, `create_period`,
`update_period`, `close_period`, `lock_period`. ISO-date parsing implemented directly in this file
rather than delegated to the service.

**`PlatformDepartmentDesktopApi` (5 methods), `PlatformTenantDesktopApi` (5 methods — the only
other capability besides Calendar/Access with more than one collaborator, fanning out to
`TenantAdminService`/`TenantContextService`/optional `TenantMembershipService`, and itself entirely
optional in the registry).**

**`PlatformPartyDesktopApi` (4), `PlatformSiteDesktopApi` (4 — also consumed internally by the
registry's own access-scope loader, i.e. one Platform desktop API feeding another's composition).**

**`PlatformEmployeeDesktopApi` (3 — no `get_context` method, unlike Site/Department/Party/Document, a
small cross-capability inconsistency), `PlatformApprovalDesktopApi` (3 — `list_requests`,
`approve_and_apply`, `reject`; label-derivation logic in `_approval_labels.py` implements real
per-`request_type` business/presentation formatting at the desktop layer).**

**`PlatformEnterpriseAuditDesktopApi` (2)** — `list_recent`; `list_for_overview` bypasses the shared
`DesktopApiResult` envelope entirely and swallows all exceptions (`except Exception: return []`), an
inconsistent error-handling convention versus every other method in the module.

**`PlatformActivityDesktopApi` (1)** — thinnest capability, a single-method 1:1 wrapper.

### 5c. Fan-out classification

- **Multi-service fan-out** (PM-Dashboard-style): `EnterpriseCalendarDesktopApi` (7 collaborators —
  Platform's clear analogue, and larger), `PlatformTenantDesktopApi` (3), `PlatformAccessDesktopApi`
  (1 service + externally-injected cross-module closures).
- **Thin 1:1 wrappers** (dominant shape — 12 of 17 classes): `PlatformApprovalDesktopApi`,
  `PlatformActivityDesktopApi`, `PlatformEnterpriseAuditDesktopApi`, `FinancialPeriodDesktopApi`,
  `PlatformDocumentDesktopApi`, `PlatformPartyDesktopApi`, `PlatformSiteDesktopApi`,
  `PlatformDepartmentDesktopApi`, `PlatformEmployeeDesktopApi`, `PlatformUserDesktopApi`,
  `PlatformIdentityDesktopApi`, plus `PlatformAccessDesktopApi`'s core grant methods.
- **Not backed by any application service at all**: `PlatformSupportDesktopApi` (direct infra/OS/
  network), `IntegrationCapabilityDesktopApi` (talks to `ModuleRegistry`/`IntegrationResolver`,
  integration-layer objects, not DDD application services).

### 5d. Notable cross-cutting findings (parallel to PM audit's adapter-boundary section)

1. Organization capability has no dedicated facade — split across `PlatformRuntimeDesktopApi` (CRUD)
   and 4 duplicated `get_context()` implementations.
2. `PlatformRuntimeDesktopApi` reimplements shared error-mapping logic instead of reusing
   `support/_support.py`.
3. `PlatformUserDesktopApi`'s write methods re-fetch-and-linear-scan the full user list — same
   anti-pattern class as PM's Portfolio dependency re-fetch.
4. `EnterpriseCalendarDesktopApi.calculate_working_days` does real calendar arithmetic in the
   desktop-API method body — same pattern PM flagged in its own Scheduling capability.
5. `_serialize_assignment`'s per-row `get_calendar()` lookup repeats across ~9 of 39 calendar
   methods.
6. `PlatformSupportDesktopApi` is architecturally an outlier and should be excluded from any
   Session-scoped CQRS split.
7. No Platform-local desktop-API builder — composition lives directly in the shared cross-module
   registry, unlike every business module.

---

## 6. Current write-path traces

Ten write paths traced end-to-end (file:line for every hop); full detail preserved from the source
research pass.

**W1 — Create Organization — confirmed to violate an already-accepted ADR, not merely inefficient.
FIXED 2026-08-12 — see "P0 correctness/security remediation status" above.**
ADR-003 (Tenancy and Authorization Authority, accepted) requires under "Audit Retention" that,
for a named list of security-relevant operations including **platform provisioning**, "the
business mutation and successful security audit intent commit atomically." `provision_organization`
is exactly that operation, and the trace below finds its business-mutation commits (#1, #3) and its
audit-intent commits (#2, #4) are **four separate, non-atomic transactions**, not one. This is a
confirmed gap against a decision the team has already accepted, not merely a style inconsistency
this audit is proposing.

`PlatformRuntimeDesktopApi.provision_organization` →
`PlatformRuntimeApplicationService.provision_organization` → `OrganizationService.create_organization`
(always called with `is_active=False`, regardless of the caller's request) → domain factory →
uniqueness check → `add` → **commit #1** → `record_audit_entry` with default `commit=True` →
**commit #2** → `module_catalog_service.provision_organization_entitlements` (loop of per-module
upserts) → **commit #3** → `record_audit_entry` default → **commit #4** → conditionally
`tenant_context_service.set_active_organization`. **Four separate, non-atomic commits for one
logical action** — worse than any PM write path the companion audit found (which never exceeded
two). **Likely-broken branch, confirmed by static reading only**: since `create_organization` is
always called with `is_active=False`, a caller requesting `is_active=True` falls into
`set_active_organization`, which requires the org to *already* be active and raises
`BusinessRuleError(ORGANIZATION_INACTIVE)` otherwise — this branch appears to fail on every real
invocation; no test exercises it directly, and no QML/controller caller passing `is_active=True` was
found. **Desktop-exposed "set active organization" never persists activation** — it only rebuilds
the in-memory principal via `tenant_context_service.set_active_organization`, never calls
`organization_repo.update()`; only the separate, non-desktop-exposed `OrganizationService` method
does that. **No `record_activity` call exists anywhere in `application/master_data/**`** (grep-
confirmed) — Platform master-data writes only ever touch the audit trail.

**W2 — Update Organization.** Same call chain, with two independently-stacking optimistic-
concurrency checks (an app-layer `version` compare, then a DB-row-level `update_with_version_check`)
that correctly close the TOCTOU gap either check alone would leave; same audit-after-commit gap.

**W3 — Update Employee (richest master-data write, chosen for its cross-module coupling).
The pre-commit event-emission bug below is FIXED (P0.2, 2026-08-12) — see "P0 correctness/
security remediation status" above.**
`PlatformEmployeeDesktopApi.update_employee` → `EmployeeService.update_employee` → (if
department/site given by name) `resolve_department_reference`/`resolve_site_reference` — each does a
**full-list fetch of the organization's departments/sites, then a Python case-insensitive name
match**, the same "uniqueness-scan-via-list" shape found elsewhere in this codebase — → uniqueness
re-check → `try: employee_repo.update(candidate)` (DB-row-versioned) → **`sync_linked_employee_resources`,
a cross-module write into project_management's `Resource` table, in the same transaction**: fetches
PM's linked resources via a structurally-typed Protocol PM's real repository satisfies, then for
each linked employee-type resource, mutates and calls `resource_repo.update(resource)` **and emits
`domain_events.resources_changed.emit(resource.id)` inside the loop, before `session.commit()`** —
`session.commit()` happens once, after the loop → `record_audit_entry` default (separate commit).
**Confirmed bug, distinct from anything in the PM audit**: the pre-commit event emission means a
later-iteration failure (or the final commit failing) leaves events already dispatched for rows that
get rolled back.

**W4 — Document upload/link/structure mutation.** `create_document` is metadata-only (no byte
content flows through this path) — factory → uniqueness check → add → commit → audit (separate
commit) → event. `add_link` does a duplicate-existence check but **no referential check that the
target entity actually exists in the linked module**. `DocumentLink` has no version field (create/
delete only) and `DocumentLinkORM` carries no `tenant_id` column at all — one hop further from the
isolation pattern every other master_data table uses.

**W5 — User registration.** `create_user` → `AuthService.onboard_tenant_user` →
`registration_service.onboard_tenant_user` → password hashing (before the transaction opens) →
uniqueness check → domain factory → **`with session.begin_nested()`: user row + tenant-membership
row + initial ("viewer") role-binding row + security audit, all inside one SAVEPOINT** → **one outer
commit for all four writes**. **This is the most atomic write path found anywhere in Platform** —
stronger than any master-data path above, and Platform's own account-provisioning discipline exceeds
what its own master-data services do.

**W6 — Login/session creation.** `LoginController.signIn()` (no desktop-API login entry point
exists — the QML shell calls `AuthService` directly) → `authenticate` →
`authentication_service.authenticate` → lookup → inactive/lockout checks → password/MFA
verification → `complete_successful_authentication`: mutate user (reset failed-attempt counter,
last-login timestamps), create `AuthSession` row, `add_atomic_auth_event("auth.login.success")` **in
the same transaction**, one commit. **On any exception during this sequence, the whole transaction
rolls back and raises `BusinessRuleError(AUTH_AUDIT_UNAVAILABLE)`** — a failed audit write undoes
the login itself, the strictest discipline found anywhere in Platform, stricter even than most
master-data writes. `build_principal`/`user_session.set_principal` (which starts the 30-second lease
clock) happen as a **separate, post-commit** step with their own reads, not part of one atomic
"login" operation.

**W7 — Role/permission assignment.** `assign_role` → `AuthService.assign_customer_role` →
`role_assignment_service.assign_customer_role` → tenant/membership checks →
`RoleGovernanceService.assign_role`: actor permission check + a dedicated **separation-of-duties
conflict check** (reads role/permission bindings) → idempotency check → `RoleBinding.create` + add →
**`self._record_audit(...)`, a third, hand-rolled audit implementation that bypasses
`EnterpriseAuditService`/`record_audit_entry` entirely, building an `AuditEntry` and calling the
repository directly** → one commit covering both the binding and this audit row → post-commit
`refresh_current_session_if_user`, which rebuilds **only the calling process's own**
`UserSessionContext.principal` synchronously; a different running client holding the same user's
stale session only picks up the change once its own 30-second lease expires or its shell heartbeat
forces revalidation (§7's B2).

**W8 — Approval request lifecycle.** `request_change`: permission check → active-org check →
project-org-mismatch guard (only if `project_id` given) → duplicate-pending guard (1 list-by-status
call) → create request row → `record_audit_entry(commit=False, fail_closed=True)`, same transaction
→ commit → post-commit event/notification dispatch. **No domain mutation of the target entity
happens on this call** — only the `ApprovalRequest` row and its audit entry. `approve_and_apply`:
permission check → fetch pending request (+ possible 2nd call for project-org check) → self-decision
guard → dict-lookup dispatch to the registered handler → **handler runs with `commit=False`, folded
into the same transaction** → request status updated → `record_audit_entry(commit=False)` → **one
commit covering the handler's domain mutation, the request-status change, and the audit row
together** → post-commit signal/notification. This exact sequence (handler → status → audit →
one commit) is unchanged from what the PM audit found for the same file, confirming the fix that
document referenced remains correctly wired. `reject` is structurally identical via
`self._reject_handlers`.

**W9 — Enterprise Calendar mutation (canonical Platform Admin write path).
The `seed_standard_week` non-atomic-commit defect below is FIXED (P0.3, 2026-08-12) — see "P0
correctness/security remediation status" above.**
`save_working_rule` → `WorkingRuleService.save_rule`: permission check → calendar-existence check
(no version read) → fetch-or-create the weekday's rule row → **`self._session.commit()` — inside
`save_rule` itself, one commit per weekday**. `seed_standard_week` calls `save_rule` **7 times
sequentially, one per weekday, each an independent commit** — a mid-loop failure leaves a partially-
edited week with no compensating action. `CalendarWorkingRuleRepository`'s contract exposes only a
singular `save()` — no batch primitive exists to fix this from the caller side either. No audit call,
no domain-event emission, and no optimistic-concurrency check exist anywhere in
`working_rule_service.py`, `calendar_exception_service.py`, or `enterprise_calendar_service.py` —
calendar mutations are silent to both the audit trail and the shared event bus. This directly answers
the open question of whether Platform's own calendar path already solved the batched-operation
problem the PM audit flagged in PM's (now-deleted) calendar adapter: **it has not** — Platform's own
implementation reproduces the same defect, and commits more granularly (per-call, not per-batch),
making it strictly worse than what PM used to have.

**W10 — Module entitlement/licensing toggle.** `patch_module_state` →
`PlatformRuntimeApplicationService.set_module_state` (pure pass-through) →
`ModuleCatalogService.set_module_state`: permission check → pre-read via `get_entitlement` (itself a
full `_effective_records()` cycle) → licensing/enablement/lifecycle state-machine logic implemented
in Python inside the mutation mixin, not on a domain entity → `_persist_state` → `entitlement_repo.
upsert` (select-then-upsert, **no version/row-lock predicate** — `ModuleEntitlementORM` has no
version column at all, so two concurrent toggles of the same module silently last-write-wins) →
commit → `record_audit_entry` default (**separate commit, and silently no-ops with zero error surfaced
if `_enterprise_audit_service` isn't wired**, since it's an optional constructor parameter — a
license/enable/disable change could leave zero audit trail undetected) → `modules_changed.emit` →
a **second full `get_entitlement` re-read cycle just to build the return value**. The batch sibling
`provision_organization_entitlements` (used in W1) commits once for the whole batch but only emits
`modules_changed` if the newly-provisioned org happens to already be the active one.

---

## 7. Current read-path traces

**R1 — Master-data list/detail (Organization/Site/Department/Employee/Party).** All five
repositories push tenant/org scoping (and any active-flag filter) into SQL, but **none does DB-side
LIMIT/OFFSET pagination** — every `list_for_organization`/`list_for_tenant` materializes the entire
filtered result set via `.all()`. Free-text search is Python-side substring matching, applied *after*
the SQL fetch (`DepartmentService.search_departments`), and any per-row authorization filtering
(`SiteService.list_sites`'s `filter_scope_rows`) is likewise applied in Python on the already-
materialized list.

**R2 — Auth/session validation ("the 30-second lease"), confirmed as a genuine Platform mechanism.**
`UserSessionContext.__init__` (`domain/security/auth/session.py:217-240`) takes
`validation_interval_seconds: float = 30.0`. Instantiated with defaults at
`platform_registry.py:209`, wired to its validator at `:308`
(`user_session.set_validator(auth_service.validate_session_principal)`). Every permission check
routes through `_active_principal()` (`session.py:456-490`): if `(monotonic() - last_validation) <
30.0`, the check is a **pure in-memory frozenset lookup, zero DB round trips**. On the call that
crosses the 30-second boundary (amortized to at most once per ~30 seconds of session lifetime),
`validate_session_principal` does `user_repo.get()`, `auth_session_repo.get()`, a throttled
`touch_validation` (only if ≥60s since last touch), then `build_principal(...)`, which **re-fetches
the session again (redundant with the earlier call) and runs `CanonicalRoleResolver._resolve()`
twice** (once directly, once via `resolve_principal_authority`), each doing a full permission-catalog
+ role-binding + role-permission read. **A separate, coincidentally-identical 30-second mechanism**
also exists: `ShellRuntimeSessionController` (`ui_qml/shell/runtime_session.py`) runs a `QTimer` at
30,000ms that calls `revalidate_principal()` **unconditionally** (`force_validation=True`, ignoring
the lease clock), and also fires on app-foreground transitions — this is the "forced shell heartbeat"
referenced elsewhere in this codebase's documentation. Both mechanisms are entirely Platform/shell-
owned; no PM-module code defines or wraps either.

**R3 — Role/permission resolution.** `require_permission` → `get_authorization_engine()` (module-
level singleton, zero construction cost) → `engine.has_permission()` → `user_session.has_permission()`
→ the R2 lease check → in-memory frozenset test. `role_permission_catalog.py`'s `DEFAULT_PERMISSIONS`
dict is a **static bootstrap/seed catalog**, confirmed not consulted on the runtime permission-check
hot path at all (only used by the default-seed service, SoD enforcer, and role-policy reconciliation).
**Exact DB cost of one `require_permission()` call: zero within the lease window; amortized ~4-6
round trips absorbed into whichever call happens to cross the 30-second boundary.**

**R4 — Approval queue read.** `list_pending`/`list_requests` → permission check (in-memory) →
`_list_approval_rows` → **exactly 1 repository call**: `list_by_status_for_organization`, which does
org-scoping (via `outerjoin` to PM's `ProjectORM` + `or_` fallback for non-project-scoped rows),
status/project/entity filtering, ordering, and `.limit()` **all in one SQL statement** — the one read
path in Platform matching full SQL-side pagination/filter discipline. **Layering smell**: this
"shared platform" repository imports `ProjectORM` directly from `project_management`'s ORM module to
build the outer join — a compile-time dependency on one specific consumer's model living inside
capability-agnostic infrastructure code.

**R5 — Audit feed / activity feed read.** Both `EnterpriseAuditService.list_recent` and
`ActivityService.list_recent` filter, order, and cap results **in SQL**, not fetch-all-then-slice.
However neither exposes an offset/cursor parameter — both are "most-recent-N" queries (`limit`
only), not true multi-page pagination; there is no way to page further back through either feed via
the current desktop API.

**R6 — Notification inbox read.** A fully-built, SQL-paginated notification store exists
(`list_my_notifications(unread_only=, limit=)`, correctly filtered/ordered/limited in SQL) and the
write side is actively used (wired into `approval_service`/`tenant_membership_service`; PM's
@mention flows dispatch into it). **But no desktop-exposed read path exists anywhere** — an
exhaustive grep across all of `api/desktop/**` and all of `src/ui_qml/**` for
`list_my_notifications|mark_read|NotificationService|NotificationRepository` returns zero real
matches. **Notifications today are write-only from the UI's perspective** — dispatched and stored,
never surfaced as a viewable inbox; exercised only at the service-test layer. **This matches
ADR-001 (Cross-Platform Ownership, accepted)'s own status tracking**, which lists "platform
notifications and inbox awareness" as `[~]` partially implemented — "not yet a full standalone
platform-owned generic inbox workflow" — a known, already-tracked gap rather than a surprise this
audit is the first to surface.

**R7 — "Totals"/rollup-shaped reads (SQL-side aggregation audit).** Grepped `func.sum`,
`func.count`, `group_by` across all 21 Platform repository files: **`func.sum` — zero occurrences
anywhere**; **`group_by` — zero occurrences anywhere**; **`func.count` — exactly 4 occurrences, all
in `enterprise_calendar.py`** (`count_for_calendar`, `count_active_assignments_for_calendar` — the
latter itself doing 3 separate SQL counts summed in Python). **No master-data rollup exists at all**
— not even a materialize-then-`len()` version — "employees per department," "sites per
organization," or any portfolio-shaped Platform report simply hasn't been built yet. **This exactly
matches PM's module-wide finding** — the sole DB-side aggregation primitives anywhere in Platform's
persistence layer are `.limit()`-bounded "recent N" reads and these 4 narrow counts; nothing else.

**R7a (bonus) — Module entitlement read: the confirmed N+1.** `get_runtime_context` →
`list_entitlements`/`shell_summary()`: `_build_entitlement` re-derives the full entitlement-record
map from scratch **per module, in a list comprehension**, and `shell_summary()` repeats the entire
`list_enabled`/`list_licensed`/`list_available`/`list_entitlements` cycle **a second time** — with
just 5 built-in modules this issues on the order of **15-20 near-identical
`SELECT * FROM organization_module_entitlements`** statements to answer one "what's entitled"
question, with zero caching across calls. This read fires on every app-context load — the single
highest-frequency, most concretely evidenced CQRS opportunity found in this audit (§1's ranked
opportunity #1).

**R7b (bonus) — Enterprise Calendar range read is genuinely SQL-bounded**, confirmed as a real,
correctly-implemented WHERE-bounded read (`exception_date BETWEEN start AND end`, tenant/org-scoped
join), O(calendars-in-chain) not O(days) — but its `_rules_cache`/`_recurring_cache` have zero
invalidation callers wired anywhere, a stale-read risk given the singleton is shared across 5+ PM
consumer services (§4c).

---

## 8. Boundary and model mapping

Domain entities (not ORM objects) cross from application services to desktop APIs in every write/
read path traced in §6/§7 — the same convention as PM, confirmed by inspection of every trace above;
no repository or service was found returning a raw ORM row across a layer boundary. The one
confirmed real boundary violation, distinct from the "domain entity leaked to UI" concern PM's audit
addressed, is the **cross-module compile-time dependency**: `ApprovalRepository` (a Platform-owned,
capability-agnostic infrastructure file) imports `ProjectORM` from `project_management` directly to
build its organization-scoping join (§7's R4). This is architecturally the same class of concern as
PM's private-collaborator-reach-through findings — a "supposedly generic" layer carrying an
undocumented dependency on one specific consumer's internals — but manifests as an ORM-level import
rather than a private-attribute reach-through.

A second, narrower instance: `EmployeeService.sync_linked_employee_resources` (§6's W3) reaches into
project_management's `Resource` aggregate through a structurally-typed Protocol that PM's concrete
repository happens to satisfy — a legitimate cross-module port by this codebase's own established
convention (the same shape as `TaskReservationGateway`/`ProcurementFinancialSourceProvider`), but
worth flagging here since it's the one place a Platform *write* path directly mutates another
module's aggregate rows within its own transaction.

---

## 9. Repository and persistence audit

### 9a. Repository classification summary

37 concrete repository classes across 21 files, grouped by the 9 content groups (finance is real,
not folded into another group — see §3). **`Commits?` is No for all 37**, confirmed by
`grep -rn "\.commit(" repositories/` returning zero matches, matching PM's convention exactly.

**Tenant scoping is genuinely inconsistent, unlike PM's more uniform pattern**:

| Table family | Scoping |
|---|---|
| `tenants`, `users`, `auth_sessions`, `auth_policy_reconciliations`, `permissions`, `role_permissions`, `notifications` | **Global — no `tenant_id` column at all** |
| `roles`, `role_bindings`, `role_delegation_policies` | **Nullable hybrid** — `tenant_id` nullable (NULL = system-scope role), hand-rolled branching, no shared scoping mixin |
| `departments`, `documents`/`document_structures`, `employees`, `parties`, `sites`, `service_principals`, `financial_periods`, `runtime_executions`, `module_entitlements` | Direct `tenant_id`(+`organization_id`) column, via `TenantScopedRepositorySupport` mixin |
| `organizations` | **Inconsistent**: direct `tenant_id` column exists, but **no scoping mixin at all** — `get`, `get_by_code`, `get_active`, and **`list_all` return cross-tenant rows unfiltered** |
| `document_links` | No `tenant_id` column — transitive only via `organization_id` + parent |
| `api_key_credentials` | `tenant_id` only, **no `organization_id` column** — org-scoping only transitive via parent principal, never checked |
| calendar child tables (working rules, exceptions, recurring events, shift-pattern days, all 3 assignment tables) | No `tenant_id` column at all — transitive via parent `platform_calendars`/`shift_patterns` row |
| `activity_entries`, `platform_events`, `audit_entries` | Direct scoping, but via three *different* mechanisms (§9d) |

None of the 8 classes in `auth.py` import `_tenant_scope` at all — a deliberate outlier from the rest
of Platform's own scoping convention.

### 9b. ORM → mapper → table map

Platform owns **40 distinct tables** across 21 ORM files. **Mapper file count is 17, not 21** —
`identity.py`/`runtime_tracking.py` define mapping functions inline in the repository file rather
than a separate module; `modules.py` maps by direct attribute copy with no helper functions;
`time_financial_outbox.py` needs none (thin subclass of a shared generic outbox repository).

**Is Platform a money-bearing layer? Confirmed: effectively no.** `grep -rn "financial_numeric"
orm/` → zero matches anywhere in Platform; `grep -rn "Numeric(" orm/` → zero matches — no
`Numeric`/`Decimal` columns exist at all. Platform's one finance-adjacent table, `financial_periods`,
is pure calendar/lifecycle metadata (dates, fiscal year, open/closed/locked status) with no amount
columns — the ADR-PF-005 `financial_numeric()`/`info`-marker convention is genuinely N/A there. The
one quantity-shaped value family Platform does carry — **hours** (`time_entries.hours`,
`calendar_exceptions.hours_override`, `shift_pattern_days.hours`,
`calendar_recurring_events.hours_override`) — uses **plain `Float`, no marker**, the same pre-ADR
legacy pattern PM found in `cost_items`. All real money columns in the whole application live in
`project_management` (17 `financial_numeric` hits, confirmed by a separate repo-wide grep, all under
PM's ORM directory).

**Version-column coverage**: `version` ✅ present on `FinancialPeriod`, `Employee`, `Department`,
`Document`/`DocumentStructure` (not `DocumentLink`), `Organization`, `Party`, `Site`, `Tenant`,
`UserTenantMembership`, `PlatformCalendar`, `Role` (nullable-tenant hybrid). **No `version` column at
all** on `TimeEntry`, `TimesheetPeriod`, `UserAccount`, `AuthSession`, `Permission`/`RolePermission`,
`ModuleEntitlementORM` (the entitlement-toggle write in §6's W10 has zero concurrency protection as a
direct consequence), or any of the notification/event/audit/activity log-shaped tables — deliberate
for pure link/log/ephemeral rows, but means no optimistic-concurrency guard is even structurally
possible on those tables.

**Structural finding, matching PM exactly**: `grep -rn "relationship(" orm/` → **zero matches**
across all 21 ORM files. Every cross-entity read is an explicit `select().join(...)` in a repository
method (e.g. `ApprovalRepository`'s `outerjoin` to `ProjectORM`, the calendar repositories'
`_scoped_calendar_stmt`/`_scoped_assignment_stmt` helpers).

### 9c. Pagination, sorting, filtering — module-wide default

- **`.limit(` — 11 calls** (vs. PM's 3): `approval.py` (×2, default 200), `runtime_tracking.py` (200),
  `notification.py`, `platform_events.py` (×2), `financial_period.py` (`.limit(1)` inside an
  `overlaps()` existence check, not pagination), `activity.py`, `audit_entry.py` (×2), `time.py`.
  Every genuine pagination-shaped one bounds an audit/log/event-shaped table ("recent N"), not real
  page-2/page-3 pagination — **zero `.offset(` calls anywhere.**
- **`func.sum` — 0. `group_by` — 0. `func.count` — 4**, all in `enterprise_calendar.py` — Platform's
  one genuine divergence from PM's "zero SQL-side aggregation" finding, though still extremely
  narrow (calendar row counts, not business rollups).

### 9d. N+1 / over-fetching risk register

1. **Confirmed live, not just structural** — `TimesheetFinancialEventsMixin`
   (`timesheet_financial_events.py:31-35`): `for entry in entries: ... work_allocation_repo.get(entry.
   work_allocation_id)`. `WorkAllocationRepository` exposes only `get(id)`/`list_by_resource(id)` —
   no batch form — so any batch of approved time entries triggers one query per entry.
2. `CalendarAssignmentRepository.get_employee_assignment`/`get_department_assignment`/
   `get_site_assignment` — single-entity only; used by `EnterpriseCalendarResolver._build_chain`,
   which resolves one chain per call. No confirmed multi-resource loop invoking it was found — flagged
   as structural risk (no batch form exists), not a confirmed hot path.
3. Auth/identity/permission repositories are systemically single-id only — `UserRepository.get`,
   `RoleRepository.get`, `RoleBindingRepository.get`, `PermissionRepository.get`,
   `ServicePrincipalRepository.get`, `ApiKeyCredentialRepository.get` — none has a `list_by_ids`/
   `get_many` sibling.
4. `NotificationRepository.list_for_user`, `PlatformEventRepository.list_for_resource` — single-
   parent only.
5. Master-data batch gap, same shape as PM's §9d finding #4: `DepartmentRepository`,
   `SiteRepository`, `PartyRepository`, `DocumentRepository`, `DocumentStructureRepository`,
   `EmployeeRepository` all lack batch `get`/`list_by_ids` siblings; a cross-organization rollup
   would loop per organization.
6. `DocumentLinkRepository.list_for_document`/`list_for_entity` — single-parent only; a list view of
   N documents needing their links loops per document.

---

## 10. Transaction, session and Unit of Work audit

**Session identity, definitively confirmed**: Platform and PM share the identical `session` object —
see §1/§4a for the full trace. Platform's registry is built first and performs the one-time RLS
wiring PM's repositories then depend on.

**Are Platform repositories allowed to commit?** No — zero `.commit()` calls confirmed across all 21
repository files. Three files call `.flush()` only (`runtime_tracking.py`, `auth.py`, `identity.py`)
— never commit.

**Which Platform services commit their own transactions?** 35 files under `application/**` call
`.commit()` directly — essentially every write-capable Platform service (approval, notification,
financial period, activity, enterprise audit, all six master-data services, all auth/credentials/
provisioning/session services, role governance/policy-reconciliation/tenant-role-administration,
service principal, module catalog, tenant membership, every calendar/time-management service) — the
same "every write-capable application service commits its own transaction" discipline PM's audit
found.

**Is there a Unit-of-Work abstraction used in Platform?** No — `session_scope()` has zero callers
anywhere in the whole repository, not just PM, independently confirmed here.

**How does `ApprovalService.approve_and_apply`/`reject` handle its transaction boundary?** Read
directly (`approval_service.py:211-253`/`:171-209`): handler runs first (folded in via
`commit=False`) → request status mutated → `approval_repo.update` → `record_audit_entry(commit=False,
fail_closed=True)` → **one single commit** covers the handler's mutation, the status change, and the
audit row together. Post-commit signal/notification only after that commit succeeds. Identical in
shape to what the PM audit found for the same file (line numbers drifted slightly due to unrelated
changes; the sequence is unchanged). **This is not incidental — it is the deliberate, already-
accepted outcome of ADR-PF-008 (Approval Unit of Work, accepted 2026-08-02)**, which decided
exactly this shape ("the outer approve-and-apply application use case owns one database
transaction... financial mutation, approval decision, Enterprise Audit intent/row... commit
atomically") specifically to close a real prior gap where a financial mutation could commit while
its approval remained pending. This audit's finding corroborates that the decision is correctly
implemented today, not merely a coincidentally-good pattern.

**Cross-reference: ADR-005 (Domain Events) is a proposed, not-yet-accepted, module-agnostic
redesign that directly targets this section's core gap.** ADR-005 (status: proposed, extensively
reviewed) would replace today's dead `session_scope()` with a real `UnitOfWork` abstraction and
split domain-event dispatch into a transactional phase (runs before commit, rolls back the whole
transaction on failure) and a post-commit phase (best-effort, UI-refresh only) — precisely the
distinction this audit's three-tier audit-atomicity finding below shows Platform's own code needs
but does not yet have uniformly. ADR-005 is written generically for any module's Unit of Work, not
Platform-specific, and its own text independently confirms this audit's finding that
`src/infra/persistence/db/unit_of_work.py`'s `session_scope()` has zero callers repo-wide. If ADR-005
is accepted, a future Platform Unit of Work should follow its shape rather than this audit
inventing a second design; until then, Platform's audit-atomicity inconsistency described below
remains real and unaddressed.

**Can nested Platform services commit independently (double-commit risk)?** No instance of PM's
`TaskAssignmentBridgeMixin`-style double-commit was found; `EmployeeService.create_employee`'s
inline department/site reference-resolution helpers do not commit independently.

**Audit/activity persistence — three parallel implementations, a genuine Platform-specific
divergence from PM.**

1. **The shared wrapper** `record_audit_entry()` defaults `commit=True, fail_closed=False` —
   despite `EnterpriseAuditService.record()`'s own default actually being the safer `commit=False`,
   the wrapper's default overrides it unless a call site explicitly overrides back. **All six
   master-data mutation services call it with no override** — audit becomes a second, separately-
   committed, non-fail-closed transaction issued after the primary write already succeeded (the
   functional mirror of PM's `record_activity` finding, except here it's Platform's own *audit*
   trail behaving that way). Only 3 of 12 calling files override the defaults
   (`approval_service.py`, `financial_period_service.py`, and inconsistently within
   `timesheet_periods.py` itself — `submit_timesheet_period` uses the unsafe default while
   `approve_timesheet_period` explicitly passes `commit=False`).
2. **A direct-repository bypass**: `RoleGovernanceService._record_audit()` builds an `AuditEntry`
   and calls the repository directly, relying entirely on the caller's own commit — always same-
   transaction by construction (since no separate commit is possible), but bypasses the shared
   service/wrapper entirely.
3. **A dedicated, stricter auth-audit path**: `security/auth/audit/audit_recorder.py::
   add_atomic_auth_event()` — same direct-repo shape as (2), but explicitly raises
   `BusinessRuleError("AUTH_AUDIT_REQUIRED")` if unwired, and any persistence failure propagates
   uncaught so the caller's own rollback fires. Three dedicated tests
   (`test_auth_login_session_audit_atomicity.py` and siblings) assert this rollback-on-failure
   behavior as a contract.

**Answering "is audit always same-transaction, fail-closed?" for Platform specifically: only for
approval decisions, financial periods, approved-timesheet events, role/permission governance (via
the direct-repo bypass), and authentication/session events — not for org/site/employee/department/
party/document master-data mutations**, which behave like PM's weaker "activity" pattern instead.
Notably, **Platform's own services never call `record_activity`/`ActivityService` at all** (zero
matches) — the PM-style Activity-vs-Audit split doesn't exist as a live pattern *inside* Platform;
instead the split runs along "audit via the lenient shared wrapper" vs. "audit via a strict direct-
repo path," split by which mutations are treated as security/compliance-critical.

**Self-referential check**: `EnterpriseAuditService`/`ActivityService`'s own transactional behavior
is entirely determined by the `commit=`/`fail_closed=` arguments passed at each call site, not by
which module calls them — the divergence above comes from call-site discipline (or its absence), not
from the services behaving differently for Platform vs. PM callers.

**What must a future Platform CQRS/UoW effort preserve?** The same three constraints PM's audit
listed (reuse the shared session for parity; preserve any `commit: bool`-threaded governed paths —
here, `approve_timesheet_period`'s explicit `commit=False`; don't fold a new Reader onto a repository
mid-refactor), plus one Platform-specific addition: **any consolidation of the three audit paths must
not silently promote the strict auth/role-governance paths to the lenient master-data default**,
since their same-transaction/fail-closed behavior is deliberate and test-verified.

---

## 11. Authorization, tenancy and security flow

**Establishment mechanism**: identical to PM's, and Platform *is* where it's built — `UserSessionContext`
and `TenantContextService` are each constructed exactly once in `platform_registry.py` and shared by
constructor injection into every Platform and PM service.

**RLS wiring is a Platform responsibility, performed once, upstream of every business module.**
`configure_session_rls_context`/`validate_postgresql_execution_role` are called at
`platform_registry.py:420-421`, before PM's bundle is built — the "two-layer" (service check + DB
RLS) pattern is not merely similar to PM's, it is the literal same infrastructure, turned on by
Platform for the whole process.

**Two distinct DB-level RLS mechanisms exist**: (a) one centralized migration enabling a
`tenant_id`-only policy on a fixed table list; (b) a decentralized per-table helper
(`enable_tenant_organization_rls()`) enabling a stricter dual-predicate (`tenant_id` AND
`organization_id`) policy, called individually from table-creation migrations — confirmed used for
`financial_periods` and `platform_time_financial_outbox`. Combining both, **confirmed Platform
tables with real DB RLS**: `activity_entries`, `approval_requests`, `departments`,
`document_structures`, `documents`, `employees`, `organization_module_entitlements`, `parties`,
`platform_calendars`, `platform_events`, `service_principal_api_keys`, `service_principals`,
`shift_patterns`, `sites`, `time_entries`, `timesheet_periods`, `financial_periods`,
`platform_time_financial_outbox`, `runtime_executions`.

**Confirmed RLS-exempt tables, checked against every table in Platform's ORM against both enabling
mechanisms** — no table appears under either that isn't listed above:

- ~~**`audit_entries`** — has a nullable `tenant_id` column but **no RLS at all**, unlike its sibling
  `activity_entries`, which *is* protected. A real inconsistency, and in the wrong direction: the
  more compliance-critical table is the one without the DB backstop.~~ **FIXED 2026-08-12, P0.4** —
  see "P0 correctness/security remediation status" above. `audit_entries` now has its own bespoke
  RLS policy (`pfaudit_p04_001` migration) that enforces tenant isolation on its tenant-scoped rows
  while still permitting `add_platform()`'s deliberate `tenant_id IS NULL` rows through.
- **`notifications`** — has `tenant_id`, no RLS.
- **RBAC/identity root tables** (`roles`, `role_bindings`, `role_delegation_policies`, `permissions`,
  `role_permissions`, `auth_sessions`, `auth_policy_reconciliations`, `users`) — none RLS'd;
  `roles`/`role_bindings`' nullable `tenant_id` is enforced by a CHECK constraint. **Corrected from
  this audit's own first-pass finding**: this is not merely "plausibly intentional" — ADR-003
  (Tenancy and Authorization Authority, accepted) explicitly defines this as the canonical scope
  model: `platform` scope is `tenant_id`/`actual_scope_id` both null by design, `tenant` scope
  requires `tenant_id`, and "a platform-managed role definition is a reusable template, not a global
  grant." The nullable hybrid on `roles`/`role_bindings` is the accepted, documented architecture,
  not an unreviewed gap.
- **`organizations`, `tenants`, `user_tenants`** — root bootstrap tables, exempt for the same
  chicken-and-egg reason.
- **Calendar child tables** (`calendar_working_rules`, `calendar_exceptions`,
  `calendar_recurring_events`, `shift_pattern_days`, all 3 assignment tables) — no `tenant_id` column
  at all; transitively scoped through their parent `platform_calendars`/`shift_patterns` row, which
  *is* RLS'd — the same "transitively-scoped child table" pattern PM's audit flagged for
  Task/TaskAssignment.

**A separate, non-DB `rls_scope` metadata convention must not be confused with actual RLS.** Many
finance ORM tables (Platform's `financial_periods` and PM's `project_finance_*` tables) set
`info={"rls_scope": "tenant_organization"}` on `__table_args__`, checked by
`test_financial_period_architecture.py` — but that test only asserts the Python metadata marker and
column constraints, not that a real `CREATE POLICY` exists in Postgres. For `financial_periods` the
real policy was independently confirmed via the decentralized migration mechanism — but the marker
alone is not proof of enforcement, and a future table could carry it without ever calling the real
enabling helper.

**Confirmed missing/inconsistent permission checks in Platform's own services** — a direct analogue
of PM's §11 finding list:

1. **`CalendarAssignmentService` — every read method has zero permission check**: `get_site_calendar`,
   `list_site_assignments`, `get_department_calendar`, `list_department_assignments`,
   `get_employee_calendar`, `list_employee_assignments`, `get_project_calendar`,
   `get_resource_calendar`, `list_calendar_assignments`. Only the paired `assign_*`/`remove_*` write
   methods check `task.manage`. This service takes no `tenant_context_service` dependency at all and
   trusts whatever RLS exists on the underlying calendar row — which, per the finding above, doesn't
   exist for the assignment tables themselves.
2. **`get_authorization_engine()` direct calls exist only inside the standard scoped-permission
   helper's own internals** (`access/authorization.py`'s `require_scope_permission`/
   `filter_scope_rows`) — no Platform service outside the authorization-enforcement module itself was
   found bypassing the standard `require_permission`/`require_scope_permission` helpers the way PM's
   `TaskAssignmentMixin`/`CollaborationService` did. **This specific PM anti-pattern was not
   reproduced in Platform's own code**, as far as this audit's grep could verify.
3. **At least three independently-written "require active organization" implementations exist**,
   duplicating the same guarantee instead of sharing one call: `financial_period_service.py` uses
   the true raising helper (`tenant_context_service.require_active_scope_ids`); `organization_service.py`
   reimplements its own private `_require_current_tenant_id()` wrapping the raw session check;
   `document_service.py`/`department_context.py`/`site_service.py` each locally wrap the **soft,
   non-raising** `tenant_context_service.get_active_organization()` getter in their own private
   helper that raises if `None`. Functionally all still enforce the guarantee (no silent skip found)
   — a maintainability/consistency gap, not a live security hole.
4. **RoleGovernanceService's audit bypass** (§10) is also authorization-adjacent: role/permission
   mutations — arguably the most security-sensitive writes in the app — use a hand-rolled audit path
   instead of the standard service, meaning future hardening of the standard path wouldn't
   automatically apply to role-binding audit rows.

**No Platform equivalent of PM's finding #1** (`PortfolioResourcePoolService`, a cross-cutting report
with literally zero permission check) was found among Platform's cross-cutting/administrative
services — `AccessControlService` checks `access.manage` on every scope-grant method.

---

## 12. Events, audit, activity and refresh behavior

**Signal catalog**: Platform doesn't have its own separate event-catalog file — it shares
`src/core/shared/events/domain_events.py` with every business module. Platform-owned signals:
`approvals_changed`, `auth_changed`, `employees_changed`, `organizations_changed`, `sites_changed`,
`departments_changed`, `calendars_changed`, `documents_changed`, `parties_changed`, `access_changed`,
`modules_changed`, plus `timesheet_periods_changed` (categorized as PM-module-facing even though
Platform's `timesheet_periods.py` emits it, since timesheets surface in the PM UI). Platform
*consumes* PM/Inventory/Maintenance signals only via the generic `domain_changed` auto-wired bridge —
no direct per-signal `.connect()` in production code, matching PM's finding about this bus's usage
convention exactly.

**Confirmed dead signal**: `calendars_changed` is declared, bridged, and actively subscribed to by
`ui_qml/platform/controllers/admin/admin_domain_event_binder.py`, but is **never emitted anywhere in
the codebase** — confirmed by a repo-wide grep, and by direct inspection finding zero
`domain_events.` references anywhere in the entire `time_management/calendar/` application package.
Calendar-admin UI screens wired to this signal receive no reactive refresh from any calendar CRUD
operation; any refresh they see must come from an explicit reload call in the QML controller, not
this event.

**Emitters confirmed live for everything else**: `employees_changed`, `organizations_changed`,
`sites_changed`, `departments_changed`, `documents_changed` (6 call sites), `parties_changed`,
`access_changed`, `modules_changed`, `auth_changed` (23 call sites across every auth/session/role/
tenant-membership service). Emission timing follows the "after commit" convention in every case
checked — with the one exception already flagged in §6's W3 (`resources_changed` emitted mid-loop,
before commit).

**Audit/activity pattern, restated from §10 for completeness**: Platform never calls
`record_activity` for its own writes (zero matches); its own audit calls split into a strict,
test-verified tier and a lenient, silently-droppable tier, along a security/compliance-relevance
line rather than PM's Activity-vs-Audit line.

---

## 13. Existing tests and architecture enforcement

**Scale**: `src/tests/platform/` — **99 files, 666 `def test_` functions**, flat directory (no
`src/tests/pm`-style parallel/duplicate suite). **Zero skip/xfail markers found** anywhere in the
directory (source-searched, not executed).

**Platform-specific architecture guardrails**: no file matches `*platform*` by name, but nine files
under `src/tests/architecture/` explicitly reference `core.platform`:
`test_architecture_guardrails_legacy_orm.py` (18 `test_legacy_platform_*_package_is_removed`
checks — the densest Platform coverage in that directory), `test_architecture_guardrails_services.py`
(includes a line-count growth budget for `site_service.py`), `test_architecture_guardrails_size_
migration.py`, `test_financial_period_architecture.py` (RLS-metadata/schema-constraint checks, plus
a source-text check that the period-domain package stays free of `src.core.modules`/
`time_management`/`sqlalchemy` imports), `test_pm_desktop_adapter_architecture.py`,
`test_pm_phase0c_repository_scope_architecture.py`, `test_project_finance_a2_architecture.py`,
`test_project_finance_persistence_guardrails.py`, and `test_service_architecture.py`.

**A genuine composition-level instantiation test exists — stronger than what PM's audit found for
PM's own composition objects.** `test_service_architecture.py::
test_service_graph_builder_wires_all_services(session)` actually calls the real
`build_service_graph(session)` entry point — which internally builds Platform's *and* PM's *and*
Inventory's *and* Maintenance's full service bundles — and asserts `isinstance()` plus identity
checks on ~50 concrete services, including `organization_service`, `document_service`,
`party_service`, `department_service`, `site_service`, `employee_service`, `approval_service`,
`auth_service`, `access_service`, `enterprise_audit_service`. The PM audit's own claim that "no
composition-level test instantiates and exercises [PM's registry] end-to-end" remains true for the
three PM-specific objects it named, but this test directly and transitively covers Platform's (and
therefore, partially, everyone's) bundle-building.

**Cross-tenant isolation coverage, Platform-specific analogue of PM's hardening suite**:
`test_repository_tenant_hardening_calendar.py`, `test_repository_tenant_hardening_platform_core.py`,
`test_repository_tenant_hardening_tenant_context.py`, `test_repository_tenant_hardening_time_
governance.py` (one test each, but each targets a distinct hardening surface), plus
`test_postgresql_rls_context.py` (4 tests, directly exercising the `after_begin` GUC-setting
mechanism), and a large RBAC cluster: `test_enterprise_rbac_matrix.py`,
`test_tenancy_rbac_immediate_containment.py`, `test_tenancy_rbac_inventory.py`,
`test_phase_2e_rbac_tenant_hardening.py`, `test_canonical_role_binding_foundation.py`,
`test_role_governance_foundation.py`.

**Audit-atomicity is explicitly, deliberately tested for the strict tier identified in §10/§12**:
`test_auth_login_session_audit_atomicity.py`, `test_auth_registration_role_audit_atomicity.py`,
`test_auth_security_audit_atomicity.py` — named tests like
`test_successful_login_rolls_back_user_and_session_when_audit_fails`. **No equivalent atomicity test
exists for the master-data mutation services** (org/site/employee/department/party/document) this
audit identified as using the lenient default — the weaker tier's behavior would go uncaught by any
existing test if it regressed further, in either direction.

**Coverage by capability** (file-name-based categorization): master-data — well covered, with paired
`*_domain_validation.py` + `*_platform_foundation.py` files per entity. Auth/identity/session — very
heavily covered (audit atomicity, login/session, MFA/password, federated identity, service-principal
identity, bootstrap/provisioning). RBAC/authorization — extensively covered via phased
`test_phase_2*`/`test_phase_b_*`/`test_phase_1_*` series plus the RBAC matrix/decorator/resolver
files. Enterprise calendar — well covered (7 dedicated files: CRUD rules, exceptions/events/shifts,
resolver, assignment calculator, desktop-API working-days, domain validation) but **no test file
specifically exercises the `calendars_changed` signal**, consistent with the dead-signal finding.
Approval — `test_approval_notification_dispatch.py` plus phase-B files; no file specifically named
for `approve_and_apply`/`reject` transaction-boundary behavior beyond incidental phase-test coverage.
Financial period, notifications, data operations/runtime tracking, and the QML desktop-API/presenter
layer each have dedicated coverage (see file-name list in the underlying research pass).

---

## 14. Current architectural problems relevant to CQRS

Synthesized ranking across all five research passes, ordered by evidence strength and reach:

1. **Module entitlement read N+1** (§7 R7a) — the single most PM-Finance-Snapshot-comparable finding:
   exact, reproducible, fires on every app-context load.
2. ~~**Platform's own calendar-editing write path reproduces the exact defect PM already fixed on
   its own side, and is worse** (§6 W9) — 7 sequential, individually-committed weekday saves, with
   no repository-level batch primitive to fix it from the caller side.~~ **Fixed (P0.3,
   2026-08-12)** — `seed_standard_week` now stages all 7 saves and commits once.
3. ~~**Three-tier audit-atomicity inconsistency, and — for organization provisioning specifically —
   a confirmed violation of an already-accepted decision** (§10, §12; §6 W1).~~ **Fully resolved
   (P0.1 + P0.5, 2026-08-12).** The organization-provisioning half was fixed under P0.1 —
   `provision_organization`'s four separate commits are now one, per ADR-003. The broader
   atomicity gap across the rest of master-data (site/employee/department/party/document) was
   fixed under P0.5 — see "P0 correctness/security remediation status" above.
4. **Tenant-scoping non-uniformity** (§9a, §11) — several whole subsystems architecturally global,
   `organizations.list_all()` genuinely cross-tenant, ~~`audit_entries` missing RLS unlike its
   sibling `activity_entries`~~ **fixed (P0.4, 2026-08-12)** — see "P0 correctness/security
   remediation status" above.
5. ~~**Confirmed pre-commit event emission bug** (§6 W3) — `resources_changed.emit()` inside a loop,
   before commit, in a live cross-module write path.~~ **Fixed (P0.2, 2026-08-12).**
6. **`PlatformUserDesktopApi` / `EnterpriseCalendarDesktopApi` desktop-layer N+1s** (§5, §9d) —
   confirmed at the desktop-API layer independent of what the underlying services do.
7. **Notifications: fully-built backend, zero UI read path** (§7 R6) — not a CQRS problem per se, but
   a completeness gap worth noting since any Platform read-model work would naturally also want to
   expose this.
8. ~~**`EnterpriseCalendarResolver`'s cache has no invalidation path** (§4c, §7 R7b) — a stale-read
   risk shared by 5+ PM consumer services through the `GlobalCalendarShim` singleton.~~ **Fixed
   (P0.6, 2026-08-12)** — see "P0 correctness/security remediation status" above.
9. **Two unreconciled "financial period" and two unreconciled "integration delivery" models** (§3c)
   — should be resolved before any read-model work touches either concept, to avoid building a
   Reader against the wrong one or against both.
10. **A likely-broken `is_active=True` branch in organization provisioning** (§6 W1) — flagged as a
    static-reading-only finding requiring dynamic confirmation, per this audit's own methodology
    discipline.

---

## 15. CQRS fit analysis

**Write side — what changes, what doesn't.** The write-commit discipline itself (service commits,
repositories never commit, no relationship() indirection) is sound and needs no structural change.
What a CQRS effort should *not* do is wrap any of Platform's `commit: bool`-threaded governed paths
(the approval handler dispatch, `approve_timesheet_period`'s explicit `commit=False`) in a generic
"Command" abstraction that hardcodes `commit=True` — that would silently break the one part of
Platform's transaction handling that's already correctly governed.

**Read side — where the real work belongs.** Unlike PM, Platform has **no existing reader precedent**
to extend — no `Protocol`-based read-only class, no cursor-paginated generic page wrapper, no
consistent query/command naming split. A Platform CQRS effort would need to **establish** the
pattern, and the most defensible way to do that is to reuse PM's already-built, already-tested
`RateResolutionReader`-style shape rather than invent a second one. The clearest, most evidence-
backed first candidate is the **module entitlement read** (§7 R7a, §14 #1): a single
`ModuleEntitlementReader`-style class returning one purpose-built dataclass per organization,
replacing the current 15-20-query cycle with one SQL statement, mirroring exactly how the PM audit's
own pilot chose Finance Snapshot for its combination of measured redundancy and high call frequency.

**Which capabilities should remain mixed (write+read)?** Everything not named above. `PlatformSupport`
(file/OS/network I/O, no session involvement) should never be pulled into a session-based CQRS
design at all. `EnterpriseCalendarDesktopApi`'s read methods (`resolve_calendar_context`,
`get_source_chain`, `calculate_resource_capacity`) are real fan-out reads worth watching but do not
yet have PM-Finance-Snapshot-grade redundant-call evidence the way the entitlement read does — they
are candidates for a *future* pass, not this document's recommended first pilot.

---

## 16. Proposed target structure (light-touch)

Platform's persistence layer is already grouped by content taxonomy (the 9 groups), so — unlike PM,
which needed a `repositories/` flattening fix earlier in this engagement — **no directory
restructuring is proposed for Platform's persistence layer as a CQRS prerequisite.** The one
structural change this audit would recommend, if a Reader is built, is placing it alongside its
group's existing repository (e.g. `infrastructure/persistence/repositories/tenant/modules/` for a
`ModuleEntitlementReader`), following the same "sibling of the repository it reads from" convention
PM's `RateResolutionReader` already established (`contracts/repositories/finance/rate_cards/
rate_resolution.py` sits beside `rate_cards.py`).

---

## 17. Recommended first CQRS pilot

**Candidate: Module entitlement read (`ModuleCatalogService.get_entitlement`/`list_entitlements`/
`shell_summary`).**

**Why this one, specifically.** It has the same shape of evidence that made Finance Snapshot PM's
pilot choice: an exact, reproducible, per-call redundant-query count (15-20 near-identical
`SELECT`s for one logical question), verified by direct code reading, not estimation. Unlike PM's
pilot, this read fires on **every session's app-context load** (`get_runtime_context`), not just an
occasional report view — giving a successful pilot outsized, immediately-felt reach. It also touches
a table with **no version column and a confirmed-unprotected concurrent-write path** (§6 W10), so a
read-model pass would naturally surface (though not by itself fix) that gap too.

**Pilot scope (explicit)**: a single `ModuleEntitlementReader` (Protocol or concrete class, matching
whichever shape a follow-on design phase decides fits the existing `RateResolutionReader` precedent
best) exposing one method returning a purpose-built, per-organization entitlement snapshot dataclass
— replacing the `_effective_records()`-per-module loop with one SQL statement scoped by
organization. Reuses the existing shared session, per this audit's session-lifecycle findings. Out
of scope for the pilot: any change to the *write* side (`set_module_state`/`patch_module_state`),
any change to `PlatformSupportDesktopApi`, and any attempt to also fix the calendar-editing atomicity
defect (§6 W9) in the same pass — that is a separate, write-side fix with its own scope.

---

## 18. Open questions and decisions

0. ~~`provision_organization`'s non-atomic audit commits appear to violate ADR-003's accepted
   audit-retention requirement for platform provisioning (§6 W1, §14 #3)~~ — **Resolved (P0.1,
   2026-08-12).** Fixed as a direct bug-fix against the already-accepted ADR-003 standard,
   independent of any CQRS pilot decision, exactly as recommended here. See "P0 correctness/
   security remediation status" at the top of this document for what changed.
1. ~~**Should Platform's own calendar-editing writes (`seed_standard_week`) be fixed to use one
   batched commit before or independently of any CQRS work?**~~ — **Resolved (P0.3, 2026-08-12).**
   Fixed independently of any CQRS pilot decision, exactly as recommended here — see "P0
   correctness/security remediation status" at the top of this document.
2. **Which of the two "financial period" models is authoritative**, and should the flat
   `finance/periods/financial_period.py` value-object model be retired, merged, or kept deliberately
   separate from the layered/persisted one? Needs resolution before any Reader is built against
   "financial period."
3. **Same question for the two "integration delivery" models.**
4. ~~**Should `audit_entries` gain the same RLS protection `activity_entries` already has?**~~ —
   **Resolved (P0.4, 2026-08-12).** Fixed with a bespoke policy rather than reusing
   `activity_entries`' generic one, since `audit_entries` has a legitimate `tenant_id IS NULL`
   write path (`add_platform()`) that the generic policy would have broken — see "P0
   correctness/security remediation status" at the top of this document.
5. ~~**Should Platform's own master-data mutations (org/site/employee/department/party/document) be
   moved onto the strict, same-transaction audit tier**, matching approval/finance/auth, or is the
   lenient tier an accepted tradeoff for those specific capabilities?~~ — **Resolved (P0.5,
   2026-08-12).** Moved onto the strict tier — every master-data write now stages its audit entry
   with `commit=False, fail_closed=True` inside the same transaction as the business write, matching
   approval/finance/auth's existing pattern. See "P0 correctness/security remediation status" at the
   top of this document.
6. **Is the `is_active=True` branch of `provision_organization` genuinely unreachable/broken, or is
   there a caller this audit didn't find?** Requires dynamic confirmation (running the actual code
   path), not resolvable from static reading alone.
7. **Should Platform expose a notifications inbox read path at all**, given the backend already
   exists and is fully SQL-paginated? This is a product decision, not purely a CQRS one, but is a
   near-zero-cost addition if a Reader-style pattern is being established anyway.

---

## Terminal summary

Platform is architecturally sound at the layer level — no `relationship()` indirection, no
repository-level commits, a real and consistently-applied 8-plus-1-group content taxonomy, and a
genuinely atomic user-registration write path that exceeds its own master-data services' discipline.
Its CQRS readiness, however, starts from a weaker position than PM's did: no existing reader
precedent exists anywhere in Platform to extend, tenant-scoping coverage is meaningfully less
uniform than PM's, and its own audit-atomicity story is split across three parallel, inconsistently-
applied implementations rather than PM's more uniform (if imperfect) one. The clearest, most
evidence-backed opportunity is the module-entitlement read — a confirmed, exact N+1 that fires on
every session's context load — and the clearest write-side risk is that Platform's own calendar-
editing primitive reproduces a defect PM already found and fixed on its own side, only worse. No
mass rewrite, microservice split, event sourcing, or separate read database is justified by anything
found in this audit; every finding here is addressable as a narrowly-scoped, incremental change,
consistent with the same governing conclusion the companion PM audit reached.

This document is an audit only. No code was changed. No CQRS implementation, migration plan
execution, or write-path fix has been started for Platform as a result of this pass.
