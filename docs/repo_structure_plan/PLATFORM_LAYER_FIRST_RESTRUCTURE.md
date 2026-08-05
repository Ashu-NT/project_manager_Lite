# Platform Layer-First Restructure — Proposal for Review

Date: 2026-08-04
Status: **proposal only — no code has been moved.** This document is the
review checkpoint requested before any file is touched. Nothing here has been
executed.

## 1. Relationship to `docs/repo_structure_plan/README.md` and `EXECUTION_SPEC.md`

Those two documents currently describe the **capability-first** internal
layout that the repo already has and has been actively executing against
(QML shell migration, `src/core/modules/<module>/api/desktop/*`, etc.):

```text
src/core/platform/<capability>/
  domain/
  application/
  contracts/
  infrastructure/   # optional, or shared at src/core/platform/infrastructure/
```

i.e. each capability (`auth`, `tenancy`, `site`, `calendar`, ...) owns its own
`domain/application/contracts` internally. **This is the structure in the
repo today.**

This proposal replaces that internal ordering for `src/core/platform/` (and
only for `src/core/platform/`) with a **layer-first** layout: the six
requested top-level buckets (`application`, `domain`, `contract`,
`infrastructure`, `access`, `api`) become the direct children of `platform/`,
and each former capability becomes a subfolder grouped by content **inside**
each layer, e.g. `application/master_data/department/`.

Per your decision, this proposal is the new target and **supersedes** the
"Standard Internal Structure" / `src/core/platform/` sections of the two
existing planning docs. Section 9 below lists the exact edits I will make to
those files once you confirm this document. `src/core/modules/<module>/*`
(business modules), `src/infra/`, and `src/ui_qml/*` are **not** touched by
this proposal and keep following the existing plan as-is.

## 2. Scope

- `src/core/platform/` — 309 files inventoried, 271 moved/renamed (217 from
  the layer-first restructure + 54 from regrouping `infrastructure/
  persistence/{mappers,orm,repositories}/` per §5a), 38 stay where they are
  (already-correct top buckets or judged shared-kernel).
- `src/api/` — 42 live files, all under `src/api/desktop/*` and `src/api/`
  root; folded into `src/core/platform/api/desktop/*`.
- `src/api/http/` — **not live code.** It holds only stale `__pycache__`
  bytecode; the `.py` sources were already deleted on 2026-08-02 per
  `EXECUTION_SPEC.md`'s own status log, and `git ls-files` confirms nothing
  under `src/api/http` is tracked. There is nothing to migrate here — the
  leftover `__pycache__` directories are local build cruft, safe to delete
  as routine housekeeping, not a decision this doc needs to make.
- `src/application/runtime/` — **now in scope** (originally excluded, pulled
  in per your follow-up — see §4c). 3 files, all move.
- `src/core/modules/project_management/access/` — **one narrow, deliberate
  exception** (see §5c): 2 functions currently misfiled in
  `src/core/platform/access/authorization.py` move *out* of platform
  entirely into a new `src/core/modules/project_management/access/
  scope_permissions.py`, since they're PM-specific (hardcode
  `scope_type="project"`) with zero non-PM callers.
- Not in scope otherwise: `src/core/modules/*` (each business module's own
  internal layering, though its established `api/desktop_runtime/`
  convention is what §4c mirrors for platform), `src/infra/*`, `src/ui_qml/*`
  — confirmed to exist and hold unrelated, correctly-placed content.

## 3. New top-level buckets under `src/core/platform/`

| Bucket | Meaning | Change from today |
|---|---|---|
| `application/` | use-case orchestration, grouped by content | **new** — aggregates every capability's former `<capability>/application/` |
| `domain/` | entities, value objects, pure business rules, grouped by content | **new** — aggregates every capability's former `<capability>/domain/` |
| `contract/` | repository/port interfaces (Protocols), grouped by content | **new** — aggregates every capability's former `<capability>/contracts.py` or `contracts/` |
| `infrastructure/` | ORM rows, mappers, repository implementations | **regrouped (2026-08-04, see §5a)** — `mappers/`, `orm/`, and `repositories/` each now split by the same content groups as `application/`/`domain/`/`contract/`, one file per group/module folder |
| `access/` | scoped access/feature-gating (`AccessControlService`, `ScopedAccessGrant`, `feature_access`) | **unchanged** — already sits exactly here today |
| `api/` | desktop (and future HTTP) transport adapters | **new location** — absorbs `src/api/__init__.py` and `src/api/desktop/*`, regrouped to mirror `application/`'s content groups |

Left at the base level, un-split (see §4 and §4b for why): `common/`,
`finance/`, `integration/`.

## 4. Content-grouping taxonomy (used inside `application/`, `domain/`, `contract/`, `api/desktop/`, and — per §5a — `infrastructure/persistence/{mappers,orm,repositories}/`)

| Group | Capabilities inside it | Your instruction vs. my call |
|---|---|---|
| `tenant` | `tenancy`, `modules` | exactly as you specified |
| `master_data` | `department`, `site`, `employee`, `documents`, **`org`, `party`, `data_exchange`** | you named department/site/employee/document; I added `org` and `party` (both are directory/reference master data, same shape as site/department) and `data_exchange` (its only job today is CSV import/export of sites + parties — master-data-specific, not generic). `finance` was considered for this group and rejected — see §4b. |
| `history` | `audit`, `activity` | exactly as you specified |
| `security` | `auth`, `authorization`, **`identity`** | you asked for the auth/authorization pair; I folded in `identity` (service-principal / API-key auth) as a third sibling since it's also a machine-identity/auth concern — flagged for your review, easy to pull out into its own group if you disagree. **Update (2026-08-04): both `auth` and `authorization` are now further split by content — see §4a.** |
| `approval` | `approval` | standalone — no natural second member, not forced into a pair |
| `time_management` | `calendar`, `time` | my call — enterprise calendar and timesheets are tightly coupled (working-time calculation feeds timesheets) |
| `data_operations` | `exporting`, `importing`, `report_runtime`, `runtime_tracking` | my call — generic, reusable cross-module kernels (not tied to one business area) |
| `events` | `notifications`, `platform_events` | my call — both are event/messaging plumbing |

**Important disambiguation** (three easily-confused, currently-separate
concepts): `access/` (top-level bucket — project/feature *scope* gating),
`authorization` (now `application+domain/security/authorization` — the
permission-*engine* and role/scope policy), and `auth` (now
`.../security/auth` — login, sessions, MFA, passwords, account
provisioning). They stay three distinct things under this proposal.

## 4a. `auth` vs `authorization` investigation (2026-08-04)

You flagged two things: (1) `auth` contains code that is really about
*authorization* (permission/role decisions) rather than *authentication*
(who is this user), and (2) `auth` is too flat — 28 files directly in
`application/`, no sub-grouping. I read every file in `auth/application/`,
`auth/domain/`, and the loose `auth/*.py` files (not just filenames) to
answer both.

### What actually moves from `auth` to `authorization`

Reading the code, these files are about *deciding what a principal is
allowed to do* (roles, scopes, permission catalogs, delegation, conflict
rules) — not about verifying who the principal is. They move out of `auth`
entirely:

| File | Why it's authorization, not authentication |
|---|---|
| `application/role_scope_policy.py` | classifies which roles are platform vs. customer-assignable, and their scope type — pure permission policy |
| `application/canonical_role_resolver.py` | `CanonicalRoleResolver`/`EffectiveRoleAuthority` — resolves the canonical *permission* bindings effective for a context |
| `application/role_assignment_service.py` | grants/revokes role bindings (`assign_role`, `revoke_role`) |
| `application/role_governance_service.py` | "fail-closed canonical role delegation and binding mutations" |
| `application/role_policy_reconciliation_service.py` | reconciles role→permission policy version changes |
| `application/scope_delegation_provisioning_service.py` | plans/applies scope delegation grants |
| `application/tenant_role_administration_service.py` | tenant-scoped custom-role lifecycle |
| `application/sod_enforcer.py` | enforces separation-of-duties permission conflicts |
| `application/target_user_authorization.py` | scope-based checks for whether an actor may act on a target user — the name says it outright |
| `auth/authorization.py` (loose, root) | `require_permission`, `require_any_permission`, `record_authorization_denial` — literally permission-check + denial-audit helpers, calls `get_authorization_engine()`. Renamed to `permission_checks.py` on the way in, since a plain `authorization.py` sitting inside a folder already called `authorization/` next to `authorization_engine.py` would be confusing. |
| `domain/role_binding.py` | `RoleBinding` — who has what role in what scope |
| `domain/role_delegation.py` | `RoleDelegationPolicy` — who may delegate what role |
| `domain/policy_reconciliation.py` | `AuthPolicyReconciliation` — tracks role/permission policy version changes |
| `auth/sod.py` (loose) | `SeparationOfDutiesPolicy`/`SeparationOfDutiesRule` |

That's 9 application files + 3 domain files + 2 loose files = 14 files moving
into what used to be a 6-file `authorization/` group, growing it roughly
4x.

One file needs a **manual content split**, not a move — `auth/policy.py`
conflates two unrelated concerns in one file:
- `DEFAULT_PERMISSIONS`, `DEFAULT_ROLE_PERMISSIONS`, `SYSTEM_ROLE_POLICY_NAME/VERSION`
  → authorization (the permission/role catalog) →
  `domain/security/authorization/roles/role_permission_catalog.py`
- `login_lockout_threshold()`, `login_lockout_minutes()`, `session_timeout_minutes()`
  → authentication config (these gate login attempts and session length, not
  permissions) → stays in auth, renamed `domain/security/auth/login_security_policy.py`

This is the one place in the whole proposal where a file's *content* needs
to be split by hand at implementation time — everything else is a pure move.

**What stays in `auth`, and stays "auth" for a real reason:** the `AuthService`
aggregate + its mixins, login/credential verification, MFA, password
management, federated SSO, session lifecycle, tenant/org context switching
inside a session, account registration/bootstrap/seeding, and auth-specific
audit recording. All of that is genuinely "who is this principal and how did
they get a session" — none of it decides what they're allowed to do.

### Fixing the flatness — subfolders by content

`auth` had 28 files directly under `application/` and another 10 under
`domain/` with zero sub-grouping. After removing the 12 authorization files
above, `auth` still has 19 application files and 6 domain files — still flat
enough to warrant splitting. New subfolders, applied symmetrically to both
`application/security/auth/` and `domain/security/auth/` where the domain
side has matching content:

| Subfolder | Application files | Domain files |
|---|---|---|
| *(root)* | `auth_service.py`, `auth_query.py`, `auth_validation.py` (the `AuthService` aggregate + mixins — the entry point, doesn't get buried in a subfolder) | `session.py`, `user.py`, `datetime_utils.py`, `login_security_policy.py` (the core session/user entities + the auth half of the policy split) |
| `credentials/` | `authentication_service.py`, `authentication_transactions.py`, `password_service.py`, `mfa_service.py`, `federated_identity_service.py` | `mfa.py`, `passwords.py` |
| `session/` | `session_service.py`, `session_utils.py`, `context_switch_service.py`, `principal_builder.py` | — |
| `provisioning/` | `registration_service.py`, `bootstrap_service.py`, `default_seed_service.py`, `platform_owner_provisioning_service.py`, `user_admin_service.py` | — |
| `audit/` | `audit_recorder.py`, `security_audit.py` | — |

The now-much-larger `authorization` group gets the same subfoldering, so the
two groups stay symmetric and neither is a flat dump:

| Subfolder | Application files | Domain files |
|---|---|---|
| `roles/` | `role_scope_policy.py`, `canonical_role_resolver.py`, `role_assignment_service.py`, `role_governance_service.py`, `role_policy_reconciliation_service.py`, `scope_delegation_provisioning_service.py`, `tenant_role_administration_service.py` | `role_binding.py`, `role_delegation.py`, `policy_reconciliation.py`, `role_permission_catalog.py` |
| `enforcement/` | `sod_enforcer.py`, `target_user_authorization.py`, `permission_checks.py` (renamed), `session_authorization_engine.py` (existing file, subfoldered) | `authorization_engine.py`, `security_decision.py` (both existing, subfoldered), `sod.py` |

`contract/security/auth/` (just `__init__.py` + `auth_repository.py`) is
untouched — still small enough to stay flat. `authorization` has no
`contracts.py` today, so nothing to add there.

## 4b. `finance` — investigated twice, settled at base level (2026-08-04)

First pass: read every file in `finance/` (`money/money.py`, `money/currency.py`,
`money/currency_resolution.py`, `money/quantity.py`, `money/rounding.py`,
`money/serialization.py`, `money/_decimal.py`, `precision.py`) to check
whether it has any application-layer content that would need splitting the
way `auth/policy.py` did. It doesn't — every file is a pure value object or
pure validation function (`Money`, `CurrencyCode`, `DecimalQuantity`,
`MonetaryRate`, `RoundingPolicy`, `NumericPrecision`, `resolve_currency_code`),
none of it touches a repository, a session, or any other port. There is no
currency-conversion logic anywhere in the package — no exchange-rate lookup
exists at all; `MonetaryRate.apply()` multiplies a rate by a quantity (e.g.
`$50/hour × 8 hours`), and `resolve_currency_code()` only *picks* which
currency code to use from explicit/project/org candidates. Both are pure
functions.

That confirmed `finance` has nothing for `application/` or `contract/` — it's
100% domain content either way.

Second pass, on the placement question: `finance` is consumed broadly by
unrelated modules (PM, and presumably payroll/procurement/maintenance), not
shaped like `master_data`'s directory/reference entities (site, department,
employee, org, party). Nesting it inside `master_data` because it's "pure
domain" was the wrong axis — layer-purity doesn't imply group-fit. A generic
value-type library used everywhere is a much closer match to `common/`
(already at the base level, un-split) than to a business-content group.

**Final placement: `finance/` stays exactly where it is today** —
`src/core/platform/finance/` — a standalone base-level folder alongside
`common/` and `integration/`, untouched by this proposal. Not nested under
`domain/`, not nested under `master_data`.

## 4c. `src/application` / `src/api` runtime confusion (2026-08-04)

You flagged that `src/application` and `src/api` conflate "runtime" and
"entitlement runtime," that platform's `org` and `modules` already live
inside `src/core/platform/`, that platform should have its own desktop-API
runtime staying inside `platform/`, and that other module packages (PM,
inventory, maintenance) already have their own runtime pattern that
`src/application` should be mirroring rather than duplicating. I read every
file involved — `src/application/runtime/{entitlement_runtime.py,
platform_runtime.py}`, `src/api/desktop/runtime.py`,
`src/api/desktop/platform/runtime.py`, `src/api/__init__.py`,
`src/api/desktop/__init__.py` — plus the established convention in
`src/core/modules/{project_management,inventory_procurement,maintenance}/api/desktop_runtime/`.

### What's actually there today, and why it reads as confused

| File | What it really is |
|---|---|
| `src/application/runtime/entitlement_runtime.py` → `ModuleRuntimeService` | A **1:1 pass-through wrapper** around `ModuleCatalogService`, which already lives in `src/core/platform/modules/application/module_catalog_service.py`. Every method (`list_modules`, `is_enabled`, `set_module_state`, ...) just delegates to the identically-named method on `catalog_service`. It adds no behavior of its own. |
| `src/application/runtime/platform_runtime.py` → `PlatformRuntimeApplicationService` | A **real orchestrator** that composes `ModuleRuntimeService` + `OrganizationService` (platform/org) + `TenantContextService` (platform/tenancy) + a `require_permission` check, exposing one facade (`list_organizations`, `provision_organization`, `set_active_organization`, `snapshot`, ...) for the desktop shell. This has genuine business logic (default module selection on provisioning, permission gating, multi-service coordination) — it isn't just wiring. |
| `src/api/desktop/platform/runtime.py` → `PlatformRuntimeDesktopApi` | The desktop-facing adapter over `PlatformRuntimeApplicationService`. Platform-owned, already correctly headed to `src/core/platform/api/desktop/...` in this proposal. |
| `src/api/desktop/runtime.py` → `DesktopApiRegistry` / `build_desktop_api_registry` | The **one true cross-module orchestrator**. It imports `PlatformRuntimeDesktopApi` (platform's own runtime) *and* `build_project_management_desktop_runtime_apis`, `build_inventory_procurement_desktop_runtime_apis`, `build_maintenance_desktop_runtime_apis` (each business module's own runtime builder) and merges all of it into one `DesktopApiRegistry` for the desktop shell to consume. `src/api/desktop/__init__.py`'s entire public surface today is just `DesktopApiRegistry`/`build_desktop_api_registry` re-exported from this file. |

Four different things, three of them named "runtime," two of them living in a
top-level `src/application/` package that's supposed to be — per your own
framing — just "the one orchestrator." That's the confusion: platform's own
runtime-composition logic (`platform_runtime.py`) and a redundant duplicate
of platform/modules (`entitlement_runtime.py`) got pulled *out* of platform
and into a generic top-level package, right next to the file
(`entitlement_runtime.py`) that duplicates something platform already owns.

### The established pattern platform isn't following

Every business module already has this shape:

```text
src/core/modules/<module>/api/
  desktop/            # that module's own desktop API adapter classes
  desktop_runtime/    # that module's own composition: resolves raw services,
                       # declares what it needs from platform, builds its own
                       # desktop API objects
    service_resolver.py
    registry.py
    desktop_api_builder.py
  http/               # future HTTP adapter stub
```

`src/core/modules/project_management/api/desktop_runtime/service_resolver.py`
resolves the raw `services: Mapping[str, object]` into typed,
module-owned services (`resolve_project_management_desktop_runtime_services`).
Platform has never had an equivalent `api/desktop_runtime/` package of its
own — its version of that logic got scattered into a separate top-level
package instead.

### The rearrangement

**Platform gets its own `api/desktop_runtime/` package**, mirroring the
convention exactly:

- `src/application/runtime/entitlement_runtime.py` → `src/core/platform/api/desktop_runtime/service_resolver.py`.
  Moved into platform, renamed to match the convention every other module
  already uses. **Confirmed (2026-08-04): the `ModuleRuntimeService` wrapper
  class is eliminated, not just relocated.** `PlatformRuntimeApplicationService`
  depends on `ModuleCatalogService` directly instead. What actually lands in
  `service_resolver.py`:
  - a resolver function (replacing `resolve_module_runtime_service`) that
    takes the raw `services: Mapping[str, object]` and returns a typed
    `ModuleCatalogService | None` — this is the genuinely useful part of the
    old file, and it's exactly the `service_resolver.py` role every other
    module already has.
  - the `ModuleRuntimeSnapshot` dataclass, which stays — it's a real
    aggregation type, not a redundant wrapper. Only its *construction* moves:
    the old `ModuleRuntimeService.snapshot()` method (which called several
    `list_*` methods on `catalog_service` and assembled them) becomes a plain
    function taking `ModuleCatalogService` directly, e.g.
    `build_module_runtime_snapshot(catalog_service)`.
  - `ModuleRuntimeService` itself (the class with ~15 bare one-line delegate
    methods) does not move anywhere — it's deleted. Every call site that did
    `module_runtime_service.list_modules()` etc. calls
    `module_catalog_service.list_modules()` instead (same method names,
    confirmed identical on `ModuleCatalogService`, so this is a pure
    find-and-replace on the attribute name at each call site, not a
    behavior change).
- `src/application/runtime/platform_runtime.py` → `src/core/platform/application/platform_runtime/platform_runtime_service.py`.
  This one does **not** go into `api/desktop_runtime/` alongside the resolver
  — unlike the other modules' desktop_runtime files (which are pure wiring,
  with real business logic living in each module's own `application/`),
  `PlatformRuntimeApplicationService` *is* real application-layer
  orchestration. Per the layer-first structure, that belongs in
  `application/`, as its own single-member content group (`platform_runtime`)
  since it genuinely spans `tenant` (tenancy, modules) and `master_data`
  (org) rather than fitting cleanly into either.
- `src/api/desktop/platform/runtime.py` (+ its `models/runtime.py`) move into
  a matching `api/desktop/platform_runtime/` group folder, instead of
  sitting ungrouped at the `api/desktop/` root as originally planned in §6 —
  keeps the api/desktop grouping consistent with the new `platform_runtime`
  application group.

**`src/application/` shrinks to exactly the one orchestrator**, matching
what you asked for:

- `src/api/desktop/runtime.py` → `src/application/runtime/desktop_api_registry.py`.
  This is the file that reaches into platform *and* every business module —
  it doesn't belong nested inside platform's own `api/`, and it's the only
  thing that should live in `src/application/` at all.
- `src/application/runtime/__init__.py` stays at the same path but its
  *content* changes — it becomes the re-export facade for
  `DesktopApiRegistry`/`build_desktop_api_registry`, absorbing
  `src/api/desktop/__init__.py`'s old role.

**`src/api/` retires completely** — nothing is left in it once this lands:

- `src/api/__init__.py` — trivial docstring-only marker, no successor.
- `src/api/desktop/__init__.py` — its re-export role moves to
  `src/application/runtime/__init__.py`; no successor at its own path.
- `src/api/desktop/integration/*` (`IntegrationCapabilityDesktopApi`) —
  unaffected by this section, still moves to
  `src/core/platform/api/desktop/integration/` as already planned in §6 —
  confirmed it only wraps `ModuleRegistry` (already platform-owned, in
  `src/core/platform/integration/`) and never reaches into any business
  module's code, so it stays platform-owned, not part of the one
  orchestrator.

### Blast radius

- `entitlement_runtime` is imported by 9 files, including
  `src/infra/composition/{app_container.py,platform_registry.py}` (the real
  composition root) and, notably,
  `src/core/modules/inventory_procurement/api/desktop/inventory/api.py` and
  `.../application/inventory/foundation_service.py` — **a business module
  reaching directly into what's supposed to be platform's own runtime
  wrapper.** That's a second, smaller instance of the same kind of layering
  confusion you flagged; after this move those two files import
  `src.core.platform.api.desktop_runtime.service_resolver` (or
  `ModuleCatalogService` directly, if the wrapper is eliminated per the
  recommendation above) instead.
- `platform_runtime` is imported by 6 files, same composition-root +
  architecture-test consumers.
- `api.desktop.runtime` / the `api.desktop` package facade is imported by 27
  files — mostly tests plus `src/ui_qml/shell/app.py`, the actual shell
  entrypoint. All 27 need their import rewritten to
  `src.application.runtime` once `build_desktop_api_registry` moves.

## 5. Base-level folders (not split by layer)

`common/`, `finance/` (Money/Currency/Quantity value objects — see §4b for
why it landed here rather than nested in a content group), and `integration/`
(`module_registry`, `resolver`, `cross_module_reference`, `canonical_json`,
`events`) have **no existing internal `application/`/`domain/` split** — they
are flat, shared-kernel/cross-cutting utility code used by everything, not
one business capability's use-case+entity pair. Forcing them into
`application/`+`domain/` would be an artificial split with no behavioral
basis, so per your "leave it at base" instruction they stay at
`src/core/platform/<name>/` unchanged.

`infrastructure/persistence/{orm,mappers,repositories}/` **no longer belongs
in this section** — per your follow-up it's now regrouped the same way as
`application/`, not left flat. See §5a.

## 5a. `infrastructure/persistence/{mappers,orm,repositories}/` regrouped (2026-08-04)

Reversing the §5 call above: `mappers/`, `orm/`, and `repositories/` each get
the same content grouping as `application/`/`domain/`/`contract/`, one file
per group/module folder — same taxonomy from §4, no new groups invented.

The mapping is identical across all three layers, since they all use the
same filenames for the same underlying tables:

| Filename | Group / module | Present in |
|---|---|---|
| `activity.py` | `history/activity/` | mappers, orm, repositories |
| `approval.py` | `approval/` (single-member group, no module subfolder) | mappers, orm, repositories |
| `audit_entry.py` | `history/audit/` | mappers, orm, repositories |
| `auth.py` | `security/auth/` | mappers, orm, repositories |
| `departments.py` | `master_data/department/` | mappers, orm, repositories |
| `documents.py` | `master_data/documents/` | mappers, orm, repositories |
| `employee.py` | `master_data/employee/` | mappers, orm, repositories |
| `enterprise_calendar.py` | `time_management/calendar/` | mappers, orm, repositories |
| `identity.py` | `security/identity/` | orm, repositories only — no mapper exists today |
| `modules.py` | `tenant/modules/` | orm, repositories only — no mapper exists today |
| `notification.py` | `events/notifications/` | mappers, orm, repositories |
| `org.py` | `master_data/org/` | mappers, orm, repositories |
| `party.py` | `master_data/party/` | mappers, orm, repositories |
| `platform_events.py` | `events/platform_events/` | mappers, orm, repositories |
| `runtime_tracking.py` | `data_operations/runtime_tracking/` | orm, repositories only — no mapper exists today |
| `sites.py` | `master_data/site/` | mappers, orm, repositories |
| `tenant.py` | `tenant/tenancy/` | mappers, orm, repositories |
| `time.py` | `time_management/time/` | mappers, orm, repositories |
| `user_tenant.py` | `tenant/tenancy/` (same module as `tenant.py` — both are tenancy-domain rows) | mappers, orm, repositories |

Notes:

- **`auth.py` does not split into `auth`/`authorization` the way the
  application and domain layers do (§4a).** There is one combined ORM
  row/mapper/repository per layer covering users, sessions, roles, and role
  bindings — the persistence layer never separated authentication data from
  authorization data the way the code above it now does. Rather than
  invent a split that doesn't exist in the schema, `auth.py` moves as one
  file into `security/auth/` in all three layers. Flagging this as an
  intentional asymmetry between the code layers and the persistence layer,
  not an oversight.
- Three modules (`identity`, `modules`, `runtime_tracking`) have no file
  under `mappers/` at all today — nothing to move there, so `mappers/`
  simply doesn't get those group/module folders.
- `repositories/_tenant_scope.py` is a shared cross-cutting helper (a
  tenant-scoping mixin used by many repository classes), not one group's
  content — it stays ungrouped at `repositories/` root, same treatment as
  `api/desktop/models/common.py` elsewhere in this proposal.
- Each layer's own `__init__.py` (`persistence/__init__.py`,
  `mappers/__init__.py`, `orm/__init__.py`, `repositories/__init__.py`)
  stays unchanged — package-root markers, not content.
- This adds **54 file moves** on top of the 217 from §4a/§4b (16 in
  `mappers/`, 19 in `orm/`, 19 in `repositories/`) — see the updated totals
  in §8.

## 5b. `time_management/calendar/` de-flattened, and one file found misfiled (2026-08-04)

Read every file in `calendar/application/` (10 files) to group them, the
same way §4a de-flattened `auth/application/`.

### `calendar_protocol.py` is misfiled — moves to `contract/`, not a subfolder

`CalendarProtocol` is a `typing.Protocol` — "structural interface for any
calendar engine... both `GlobalCalendarShim` and `BoundProjectCalendar`
satisfy this protocol. Use this instead of the deleted `WorkCalendarEngine`
as a type annotation." It has no behavior of its own, and other modules
already import it as a type — e.g. project_management's
`api/desktop_runtime/service_resolver.py` does
`from src.core.platform.calendar.application.calendar_protocol import CalendarProtocol`
today. That's a repository/port-shaped interface sitting in `application/`
instead of `contract/`, next to the *other* calendar interfaces
(`PlatformCalendarRepository`, `CalendarWorkingRuleRepository`, etc.) that
already live in `calendar/contracts.py` — the same category of finding as
`auth/authorization.py` in §4a, just a consumer-facing service protocol
instead of a persistence repository. It moves to
`contract/time_management/calendar/calendar_protocol.py`, sitting alongside
`contracts.py`.

### The remaining 9 files, grouped by what actually depends on what

Traced the constructor dependencies, not just the filenames:

| Subfolder | Files | Why they're together |
|---|---|---|
| *(root)* | `enterprise_calendar_service.py` | CRUD for the core `PlatformCalendar` aggregate — the entry point, same treatment as `auth_service.py` staying at `auth/`'s root in §4a |
| `definitions/` | `calendar_exception_service.py`, `recurring_event_service.py`, `shift_pattern_service.py`, `working_rule_service.py` | CRUD for calendar building-block sub-entities (exceptions, recurring events, shift patterns, working rules) |
| `assignment/` | `calendar_assignment_service.py` | assigns/unassigns calendars to sites, departments, and employees — a distinct write-side concern from resolving effective capacity |
| `capacity/` | `enterprise_calendar_resolver.py`, `global_calendar_shim.py`, `working_time_calculator.py` | genuinely coupled, not just thematically similar — confirmed by reading the actual constructors: `EnterpriseCalendarResolver.__init__` takes a `WorkingTimeCalculator` directly, and `GlobalCalendarShim.__init__` takes an `EnterpriseCalendarResolver` directly. These three compute "how much working time is available for this scope," chained one into the next. |

`domain/time_management/calendar/` is untouched — it's a single file
(`enterprise_calendar.py`) today, nothing to group. `contract/time_management/calendar/`
gets one addition (`calendar_protocol.py` above `contracts.py`) but stays
flat — two files isn't enough to warrant subfolders.

## 5c. `access/` — position check, and two functions found misfiled into `project_management`'s territory (2026-08-04)

You raised two distinct questions: (1) is `src/core/platform/access/` in the
right place, given each business module's own `access/` folder holds just a
`policy.py` while platform's `access/` looks like a centralized orchestrator
— should it actually move to `src/application/`? (2) does anything currently
in `src/core/platform/access/` actually belong in a specific module's own
`access/` folder instead? Read every file in both `src/core/platform/access/`
(all 7 files) and all three modules' `access/policy.py` (PM, maintenance,
inventory) to answer both.

### Question 1: is `access/` in the right place? — Yes, keep it in platform

Each module's own `access/policy.py` (`PROJECT_SCOPE_ROLE_PERMISSIONS` in
PM, `MAINTENANCE_SCOPE_ROLE_PERMISSIONS` in maintenance,
`STOREROOM_SCOPE_ROLE_PERMISSIONS` in inventory) is pure data: which scope
roles exist for that module and what permissions each one resolves to. No
behavior, no dependencies on platform.

`src/core/platform/access/` is bigger — `AccessControlService`
(`application/`), `ScopedAccessGrant` (`domain/access_scope.py`),
`ScopedRolePolicy`/`ScopedRolePolicyRegistry` (`domain/feature_access.py`),
and generic scope-permission helpers (`authorization.py`). It *does* know
about all three modules' scope types at once
(`_CANONICAL_SCOPE_TYPES = frozenset({"project", "site", "storeroom",
"maintenance"})`), which is exactly what reads as "centralized
orchestrator" and prompted the question of moving it to `src/application/`
alongside the one true orchestrator from §4c
(`desktop_api_registry.py`).

The distinction that matters: `AccessControlService` has **zero direct
imports of any business module.** It depends only on other platform
services (`AuthService`, `RoleGovernanceService`, `TenantContextService`,
`RoleRepository`, `RoleBindingRepository`, `UserTenantMembershipRepository`,
`EnterpriseAuditService`). Its awareness of `"project"`/`"storeroom"`/
`"maintenance"` scope types comes entirely through **inversion of
control** — `register_scope_policy()` and `register_scope_exists_resolver()`
let each module *plug its own policy in*, and each module's own composition
root does exactly that:

```text
src/infra/composition/project_registry.py:120:     platform_services.access_service.register_scope_policy(...)
src/infra/composition/inventory_registry.py:81:     platform_services.access_service.register_scope_policy(...)
src/infra/composition/maintenance_registry.py:233:  platform_services.access_service.register_scope_policy(...)
```

`AccessControlService` never imports `project_management`, `inventory_procurement`,
or `maintenance` code — those modules import *it* (indirectly, through
their composition-root registries). That's the same shape as
`ModuleRegistry` in `src/core/platform/integration/` (§4c's blast-radius
check confirmed *that* also has zero business-module imports, just
string-keyed awareness of module IDs) — and `ModuleRegistry` stayed in
platform, not `src/application/`, for the same reason.

Contrast with `desktop_api_registry.py` (§4c), which has **hard imports** —
`build_project_management_desktop_runtime_apis`,
`build_inventory_procurement_desktop_runtime_apis`,
`build_maintenance_desktop_runtime_apis` — actual Python imports of each
module's own builder function. That's what earns a file the "one
orchestrator, lives in `src/application/`" treatment. A registry that
modules plug themselves into via dependency inversion is a different,
platform-appropriate shape — the same shape as `auth`, `authorization`, and
`ModuleRegistry`, all of which stay in platform.

**Verdict: `src/core/platform/access/` stays exactly where it is** — already
correctly one of the six top-level buckets (§3), unchanged by this
proposal. Flagging this as an explicit decision in §12 since it overrides
what the team had been leaning toward.

### Question 2: two functions in `access/authorization.py` are misfiled into PM's territory

`access/authorization.py` has four functions. Checked every caller of each:

| Function | Callers | Verdict |
|---|---|---|
| `require_scope_permission` | 14 files across `inventory_procurement`, `maintenance`, and platform's own `site/application/site_service.py` | genuinely generic — stays in platform |
| `filter_scope_rows` | 21 files across `inventory_procurement`, `maintenance`, and platform's own `site_service.py` | genuinely generic — stays in platform |
| `require_project_permission` | **27 files, every single one under `src/core/modules/project_management/`** (plus PM test files) | hardcodes `scope_type="project"` — a PM-specific convenience wrapper, zero non-PM callers |
| `filter_project_rows` | **4 files, every single one under `src/core/modules/project_management/`** (plus a PM test file) | hardcodes `scope_type="project"` — same story, zero non-PM callers |

`require_project_permission` and `filter_project_rows` are project-management-specific
conveniences that got left in the shared platform file instead of PM's own
`access/` folder. They call the generic `require_scope_permission`/
`filter_scope_rows` functions (which correctly stay in platform) with
`scope_type="project"` hardcoded — that hardcoding is exactly what makes
them PM's concern, not platform's.

**Action: move both functions out of `src/core/platform/access/authorization.py`
into a new `src/core/modules/project_management/access/scope_permissions.py`**,
importing the generic `require_scope_permission`/`filter_scope_rows` from
platform. This is the one place in this whole proposal where code moves
*out* of `src/core/platform/` entirely into a business module — a
deliberate, narrow exception to this doc's scope (mirroring how §4c pulled
`src/application/runtime/` *into* scope). `access/authorization.py` itself
needs a manual content split at implementation time, the same mechanic as
`auth/policy.py` in §4a: two functions stay, two functions leave. Every one
of the 27+4 real *source* call sites in PM (confirmed, e.g.
`src/core/modules/project_management/application/tasks/commands/assignment.py:18`
does `from src.core.platform.access.authorization import
require_project_permission`) needs its import updated to
`from src.core.modules.project_management.access.scope_permissions import ...`.
The handful of *test* files that reference these names (§9a) do it by
patching `unittest.mock.patch` at the consuming module's own path — e.g.
`patch("src.core.modules.project_management.application.tasks.commands.assignment.require_project_permission")`
— which stays valid no matter where the underlying import comes from, so
those tests need **zero** changes. §9a's "no change needed" categorization
for those files was already correct; this doesn't revise that count.

## 6. New tree (full, generated from the mapping below — nothing hand-typed)

```text
└── src/
    ├── application/
    │   └── runtime/
    │       ├── __init__.py
    │       └── desktop_api_registry.py
    └── core/
        └── platform/
            ├── access/
            │   ├── application/
            │   │   ├── __init__.py
            │   │   └── access_control_service.py
            │   ├── domain/
            │   │   ├── __init__.py
            │   │   ├── access_scope.py
            │   │   └── feature_access.py
            │   ├── __init__.py
            │   └── authorization.py
            ├── api/
            │   ├── desktop/
            │   │   ├── access/
            │   │   │   ├── models/
            │   │   │   │   └── access.py
            │   │   │   └── access.py
            │   │   ├── approval/
            │   │   │   ├── models/
            │   │   │   │   └── approval.py
            │   │   │   ├── _approval_labels.py
            │   │   │   └── approval.py
            │   │   ├── history/
            │   │   │   ├── activity/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── activity.py
            │   │   │   │   └── activity.py
            │   │   │   └── audit/
            │   │   │       ├── models/
            │   │   │       │   └── audit_entry.py
            │   │   │       └── audit_enterprise.py
            │   │   ├── integration/
            │   │   │   ├── __init__.py
            │   │   │   └── capability_api.py
            │   │   ├── master_data/
            │   │   │   ├── department/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── department.py
            │   │   │   │   └── department.py
            │   │   │   ├── documents/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── document.py
            │   │   │   │   └── document.py
            │   │   │   ├── employee/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── employee.py
            │   │   │   │   └── employee.py
            │   │   │   ├── org/
            │   │   │   │   └── models/
            │   │   │   │       └── organization.py
            │   │   │   ├── party/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── party.py
            │   │   │   │   └── party.py
            │   │   │   └── site/
            │   │   │       ├── models/
            │   │   │       │   └── site.py
            │   │   │       └── site.py
            │   │   ├── models/
            │   │   │   ├── __init__.py
            │   │   │   └── common.py
            │   │   ├── platform_runtime/
            │   │   │   ├── models/
            │   │   │   │   └── runtime.py
            │   │   │   └── runtime.py
            │   │   ├── security/
            │   │   │   ├── auth/
            │   │   │   │   ├── models/
            │   │   │   │   │   └── user.py
            │   │   │   │   └── user.py
            │   │   │   └── identity/
            │   │   │       ├── models/
            │   │   │       │   └── identity.py
            │   │   │       └── identity.py
            │   │   ├── support/
            │   │   │   ├── models/
            │   │   │   │   └── support.py
            │   │   │   ├── _support.py
            │   │   │   └── support.py
            │   │   ├── tenant/
            │   │   │   └── tenancy/
            │   │   │       ├── models/
            │   │   │       │   └── tenant.py
            │   │   │       └── tenant.py
            │   │   ├── time_management/
            │   │   │   └── calendar/
            │   │   │       ├── models/
            │   │   │       │   ├── calendar.py
            │   │   │       │   └── enterprise_calendar.py
            │   │   │       └── enterprise_calendar.py
            │   │   └── __init__.py
            │   └── desktop_runtime/
            │       └── service_resolver.py
            ├── application/
            │   ├── approval/
            │   │   ├── __init__.py
            │   │   └── approval_service.py
            │   ├── data_operations/
            │   │   ├── exporting/
            │   │   │   ├── __init__.py
            │   │   │   ├── artifact_delivery.py
            │   │   │   ├── export_definition_registry.py
            │   │   │   └── export_runtime.py
            │   │   ├── importing/
            │   │   │   ├── __init__.py
            │   │   │   ├── csv_import_runtime.py
            │   │   │   └── import_definition_registry.py
            │   │   ├── report_runtime/
            │   │   │   ├── __init__.py
            │   │   │   ├── report_definition_registry.py
            │   │   │   └── report_runtime.py
            │   │   └── runtime_tracking/
            │   │       ├── __init__.py
            │   │       └── runtime_execution_service.py
            │   ├── events/
            │   │   ├── notifications/
            │   │   │   ├── __init__.py
            │   │   │   └── notification_service.py
            │   │   └── platform_events/
            │   │       └── __init__.py
            │   ├── history/
            │   │   ├── activity/
            │   │   │   ├── __init__.py
            │   │   │   └── activity_service.py
            │   │   └── audit/
            │   │       ├── __init__.py
            │   │       └── enterprise_audit_service.py
            │   ├── master_data/
            │   │   ├── data_exchange/
            │   │   │   ├── __init__.py
            │   │   │   └── service.py
            │   │   ├── department/
            │   │   │   ├── __init__.py
            │   │   │   ├── department_access.py
            │   │   │   ├── department_commands.py
            │   │   │   ├── department_context.py
            │   │   │   ├── department_location_service.py
            │   │   │   ├── department_queries.py
            │   │   │   ├── department_service.py
            │   │   │   ├── department_utils.py
            │   │   │   └── department_validation.py
            │   │   ├── documents/
            │   │   │   ├── __init__.py
            │   │   │   ├── document_integration_service.py
            │   │   │   └── document_service.py
            │   │   ├── employee/
            │   │   │   ├── __init__.py
            │   │   │   ├── employee_service.py
            │   │   │   └── employee_support.py
            │   │   ├── org/
            │   │   │   ├── __init__.py
            │   │   │   └── organization_service.py
            │   │   ├── party/
            │   │   │   ├── __init__.py
            │   │   │   └── party_service.py
            │   │   └── site/
            │   │       ├── __init__.py
            │   │       └── site_service.py
            │   ├── platform_runtime/
            │   │   └── platform_runtime_service.py
            │   ├── security/
            │   │   ├── auth/
            │   │   │   ├── audit/
            │   │   │   │   ├── audit_recorder.py
            │   │   │   │   └── security_audit.py
            │   │   │   ├── credentials/
            │   │   │   │   ├── authentication_service.py
            │   │   │   │   ├── authentication_transactions.py
            │   │   │   │   ├── federated_identity_service.py
            │   │   │   │   ├── mfa_service.py
            │   │   │   │   └── password_service.py
            │   │   │   ├── provisioning/
            │   │   │   │   ├── bootstrap_service.py
            │   │   │   │   ├── default_seed_service.py
            │   │   │   │   ├── platform_owner_provisioning_service.py
            │   │   │   │   ├── registration_service.py
            │   │   │   │   └── user_admin_service.py
            │   │   │   ├── session/
            │   │   │   │   ├── context_switch_service.py
            │   │   │   │   ├── principal_builder.py
            │   │   │   │   ├── session_service.py
            │   │   │   │   └── session_utils.py
            │   │   │   ├── __init__.py
            │   │   │   ├── auth_query.py
            │   │   │   ├── auth_service.py
            │   │   │   └── auth_validation.py
            │   │   ├── authorization/
            │   │   │   ├── enforcement/
            │   │   │   │   ├── permission_checks.py
            │   │   │   │   ├── session_authorization_engine.py
            │   │   │   │   ├── sod_enforcer.py
            │   │   │   │   └── target_user_authorization.py
            │   │   │   ├── roles/
            │   │   │   │   ├── canonical_role_resolver.py
            │   │   │   │   ├── role_assignment_service.py
            │   │   │   │   ├── role_governance_service.py
            │   │   │   │   ├── role_policy_reconciliation_service.py
            │   │   │   │   ├── role_scope_policy.py
            │   │   │   │   ├── scope_delegation_provisioning_service.py
            │   │   │   │   └── tenant_role_administration_service.py
            │   │   │   └── __init__.py
            │   │   └── identity/
            │   │       ├── __init__.py
            │   │       └── service_principal_service.py
            │   ├── tenant/
            │   │   ├── modules/
            │   │   │   ├── __init__.py
            │   │   │   ├── authorization.py
            │   │   │   ├── guard.py
            │   │   │   ├── module_catalog_context.py
            │   │   │   ├── module_catalog_mutation.py
            │   │   │   ├── module_catalog_query.py
            │   │   │   └── module_catalog_service.py
            │   │   └── tenancy/
            │   │       ├── __init__.py
            │   │       ├── context_policy.py
            │   │       ├── tenant_admin_service.py
            │   │       ├── tenant_context.py
            │   │       └── tenant_membership_service.py
            │   └── time_management/
            │       ├── calendar/
            │       │   ├── assignment/
            │       │   │   └── calendar_assignment_service.py
            │       │   ├── capacity/
            │       │   │   ├── enterprise_calendar_resolver.py
            │       │   │   ├── global_calendar_shim.py
            │       │   │   └── working_time_calculator.py
            │       │   ├── definitions/
            │       │   │   ├── calendar_exception_service.py
            │       │   │   ├── recurring_event_service.py
            │       │   │   ├── shift_pattern_service.py
            │       │   │   └── working_rule_service.py
            │       │   ├── __init__.py
            │       │   └── enterprise_calendar_service.py
            │       └── time/
            │           ├── __init__.py
            │           ├── time_service.py
            │           ├── timesheet_entries.py
            │           ├── timesheet_periods.py
            │           ├── timesheet_query.py
            │           ├── timesheet_review.py
            │           └── timesheet_support.py
            ├── common/
            │   ├── __init__.py
            │   ├── code_generation.py
            │   ├── exceptions.py
            │   ├── ids.py
            │   ├── interfaces.py
            │   ├── pydantic.py
            │   ├── runtime_access.py
            │   └── service_base.py
            ├── contract/
            │   ├── approval/
            │   │   └── contracts.py
            │   ├── data_operations/
            │   │   └── runtime_tracking/
            │   │       └── contracts.py
            │   ├── events/
            │   │   ├── notifications/
            │   │   │   └── contracts.py
            │   │   └── platform_events/
            │   │       └── contracts.py
            │   ├── history/
            │   │   ├── activity/
            │   │   │   └── contracts.py
            │   │   └── audit/
            │   │       └── contracts.py
            │   ├── master_data/
            │   │   ├── department/
            │   │   │   └── contracts.py
            │   │   ├── documents/
            │   │   │   └── contracts.py
            │   │   ├── employee/
            │   │   │   └── contracts.py
            │   │   ├── org/
            │   │   │   └── contracts.py
            │   │   ├── party/
            │   │   │   └── contracts.py
            │   │   └── site/
            │   │       └── contracts.py
            │   ├── security/
            │   │   ├── auth/
            │   │   │   ├── __init__.py
            │   │   │   └── auth_repository.py
            │   │   └── identity/
            │   │       └── contracts.py
            │   ├── tenant/
            │   │   ├── modules/
            │   │   │   └── contracts.py
            │   │   └── tenancy/
            │   │       └── contracts.py
            │   └── time_management/
            │       ├── calendar/
            │       │   ├── calendar_protocol.py
            │       │   └── contracts.py
            │       └── time/
            │           └── contracts.py
            ├── domain/
            │   ├── approval/
            │   │   ├── __init__.py
            │   │   ├── approval_request.py
            │   │   ├── approval_state.py
            │   │   └── policy.py
            │   ├── data_operations/
            │   │   ├── exporting/
            │   │   │   ├── __init__.py
            │   │   │   ├── export_definition.py
            │   │   │   └── export_models.py
            │   │   ├── importing/
            │   │   │   ├── __init__.py
            │   │   │   ├── import_definition.py
            │   │   │   └── import_models.py
            │   │   ├── report_runtime/
            │   │   │   ├── __init__.py
            │   │   │   ├── report_definition.py
            │   │   │   └── report_document.py
            │   │   └── runtime_tracking/
            │   │       ├── __init__.py
            │   │       └── runtime_execution.py
            │   ├── events/
            │   │   ├── notifications/
            │   │   │   ├── __init__.py
            │   │   │   └── notification.py
            │   │   └── platform_events/
            │   │       ├── __init__.py
            │   │       └── platform_event.py
            │   ├── history/
            │   │   ├── activity/
            │   │   │   ├── __init__.py
            │   │   │   └── activity_entry.py
            │   │   └── audit/
            │   │       ├── __init__.py
            │   │       └── audit_entry.py
            │   ├── master_data/
            │   │   ├── department/
            │   │   │   ├── __init__.py
            │   │   │   └── department.py
            │   │   ├── documents/
            │   │   │   ├── __init__.py
            │   │   │   ├── document.py
            │   │   │   ├── document_link.py
            │   │   │   ├── document_structure.py
            │   │   │   └── support.py
            │   │   ├── employee/
            │   │   │   ├── __init__.py
            │   │   │   ├── employee.py
            │   │   │   └── support.py
            │   │   ├── org/
            │   │   │   ├── __init__.py
            │   │   │   ├── organization.py
            │   │   │   └── support.py
            │   │   ├── party/
            │   │   │   ├── __init__.py
            │   │   │   └── party.py
            │   │   └── site/
            │   │       ├── __init__.py
            │   │       ├── access_policy.py
            │   │       └── site.py
            │   ├── security/
            │   │   ├── auth/
            │   │   │   ├── credentials/
            │   │   │   │   ├── mfa.py
            │   │   │   │   └── passwords.py
            │   │   │   ├── __init__.py
            │   │   │   ├── datetime_utils.py
            │   │   │   ├── login_security_policy.py
            │   │   │   ├── session.py
            │   │   │   └── user.py
            │   │   ├── authorization/
            │   │   │   ├── enforcement/
            │   │   │   │   ├── authorization_engine.py
            │   │   │   │   ├── security_decision.py
            │   │   │   │   └── sod.py
            │   │   │   ├── roles/
            │   │   │   │   ├── policy_reconciliation.py
            │   │   │   │   ├── role_binding.py
            │   │   │   │   ├── role_delegation.py
            │   │   │   │   └── role_permission_catalog.py
            │   │   │   └── __init__.py
            │   │   └── identity/
            │   │       └── service_principal.py
            │   ├── tenant/
            │   │   ├── modules/
            │   │   │   ├── __init__.py
            │   │   │   ├── defaults.py
            │   │   │   ├── module_codes.py
            │   │   │   ├── module_definition.py
            │   │   │   ├── module_entitlement.py
            │   │   │   └── subscription.py
            │   │   └── tenancy/
            │   │       ├── __init__.py
            │   │       ├── tenant.py
            │   │       └── user_tenant_membership.py
            │   └── time_management/
            │       ├── calendar/
            │       │   ├── __init__.py
            │       │   └── enterprise_calendar.py
            │       └── time/
            │           ├── __init__.py
            │           └── timesheet_models.py
            ├── finance/
            │   ├── money/
            │   │   ├── __init__.py
            │   │   ├── _decimal.py
            │   │   ├── currency.py
            │   │   ├── currency_resolution.py
            │   │   ├── money.py
            │   │   ├── quantity.py
            │   │   ├── rounding.py
            │   │   └── serialization.py
            │   ├── __init__.py
            │   └── precision.py
            ├── infrastructure/
            │   ├── persistence/
            │   │   ├── mappers/
            │   │   │   ├── approval/
            │   │   │   │   └── approval.py
            │   │   │   ├── events/
            │   │   │   │   ├── notifications/
            │   │   │   │   │   └── notification.py
            │   │   │   │   └── platform_events/
            │   │   │   │       └── platform_events.py
            │   │   │   ├── history/
            │   │   │   │   ├── activity/
            │   │   │   │   │   └── activity.py
            │   │   │   │   └── audit/
            │   │   │   │       └── audit_entry.py
            │   │   │   ├── master_data/
            │   │   │   │   ├── department/
            │   │   │   │   │   └── departments.py
            │   │   │   │   ├── documents/
            │   │   │   │   │   └── documents.py
            │   │   │   │   ├── employee/
            │   │   │   │   │   └── employee.py
            │   │   │   │   ├── org/
            │   │   │   │   │   └── org.py
            │   │   │   │   ├── party/
            │   │   │   │   │   └── party.py
            │   │   │   │   └── site/
            │   │   │   │       └── sites.py
            │   │   │   ├── security/
            │   │   │   │   └── auth/
            │   │   │   │       └── auth.py
            │   │   │   ├── tenant/
            │   │   │   │   └── tenancy/
            │   │   │   │       ├── tenant.py
            │   │   │   │       └── user_tenant.py
            │   │   │   ├── time_management/
            │   │   │   │   ├── calendar/
            │   │   │   │   │   └── enterprise_calendar.py
            │   │   │   │   └── time/
            │   │   │   │       └── time.py
            │   │   │   └── __init__.py
            │   │   ├── orm/
            │   │   │   ├── approval/
            │   │   │   │   └── approval.py
            │   │   │   ├── data_operations/
            │   │   │   │   └── runtime_tracking/
            │   │   │   │       └── runtime_tracking.py
            │   │   │   ├── events/
            │   │   │   │   ├── notifications/
            │   │   │   │   │   └── notification.py
            │   │   │   │   └── platform_events/
            │   │   │   │       └── platform_events.py
            │   │   │   ├── history/
            │   │   │   │   ├── activity/
            │   │   │   │   │   └── activity.py
            │   │   │   │   └── audit/
            │   │   │   │       └── audit_entry.py
            │   │   │   ├── master_data/
            │   │   │   │   ├── department/
            │   │   │   │   │   └── departments.py
            │   │   │   │   ├── documents/
            │   │   │   │   │   └── documents.py
            │   │   │   │   ├── employee/
            │   │   │   │   │   └── employee.py
            │   │   │   │   ├── org/
            │   │   │   │   │   └── org.py
            │   │   │   │   ├── party/
            │   │   │   │   │   └── party.py
            │   │   │   │   └── site/
            │   │   │   │       └── sites.py
            │   │   │   ├── security/
            │   │   │   │   ├── auth/
            │   │   │   │   │   └── auth.py
            │   │   │   │   └── identity/
            │   │   │   │       └── identity.py
            │   │   │   ├── tenant/
            │   │   │   │   ├── modules/
            │   │   │   │   │   └── modules.py
            │   │   │   │   └── tenancy/
            │   │   │   │       ├── tenant.py
            │   │   │   │       └── user_tenant.py
            │   │   │   ├── time_management/
            │   │   │   │   ├── calendar/
            │   │   │   │   │   └── enterprise_calendar.py
            │   │   │   │   └── time/
            │   │   │   │       └── time.py
            │   │   │   └── __init__.py
            │   │   ├── repositories/
            │   │   │   ├── approval/
            │   │   │   │   └── approval.py
            │   │   │   ├── data_operations/
            │   │   │   │   └── runtime_tracking/
            │   │   │   │       └── runtime_tracking.py
            │   │   │   ├── events/
            │   │   │   │   ├── notifications/
            │   │   │   │   │   └── notification.py
            │   │   │   │   └── platform_events/
            │   │   │   │       └── platform_events.py
            │   │   │   ├── history/
            │   │   │   │   ├── activity/
            │   │   │   │   │   └── activity.py
            │   │   │   │   └── audit/
            │   │   │   │       └── audit_entry.py
            │   │   │   ├── master_data/
            │   │   │   │   ├── department/
            │   │   │   │   │   └── departments.py
            │   │   │   │   ├── documents/
            │   │   │   │   │   └── documents.py
            │   │   │   │   ├── employee/
            │   │   │   │   │   └── employee.py
            │   │   │   │   ├── org/
            │   │   │   │   │   └── org.py
            │   │   │   │   ├── party/
            │   │   │   │   │   └── party.py
            │   │   │   │   └── site/
            │   │   │   │       └── sites.py
            │   │   │   ├── security/
            │   │   │   │   ├── auth/
            │   │   │   │   │   └── auth.py
            │   │   │   │   └── identity/
            │   │   │   │       └── identity.py
            │   │   │   ├── tenant/
            │   │   │   │   ├── modules/
            │   │   │   │   │   └── modules.py
            │   │   │   │   └── tenancy/
            │   │   │   │       ├── tenant.py
            │   │   │   │       └── user_tenant.py
            │   │   │   ├── time_management/
            │   │   │   │   ├── calendar/
            │   │   │   │   │   └── enterprise_calendar.py
            │   │   │   │   └── time/
            │   │   │   │       └── time.py
            │   │   │   ├── __init__.py
            │   │   │   └── _tenant_scope.py
            │   │   └── __init__.py
            │   └── __init__.py
            ├── integration/
            │   ├── __init__.py
            │   ├── canonical_json.py
            │   ├── cross_module_reference.py
            │   ├── events.py
            │   ├── module_registry.py
            │   └── resolver.py
            └── __init__.py
```

## 7. Key judgment calls that need your explicit sign-off

These are the places where the source code was ambiguous and I made a call
by reading the file content (not just the path):

1. **`identity` (service principals / API keys) folded into `security`
   group**, alongside `auth`+`authorization`. Alternative: give it its own
   single-member group like `approval`.
2. **`org` and `party` added to `master_data`** (you only named
   department/site/employee/document). Rationale: both are directory/
   reference-data entities shaped exactly like site/department, and
   `policy.py`'s permission catalog already describes `party.read` as
   "supplier, vendor, and contractor directory records."
3. **`data_exchange` folded into `master_data`** rather than kept standalone
   or merged with `data_operations`. Its only consumer today
   (`MasterDataExchangeService`) is CSV import/export of sites and parties
   specifically — master-data scoped, not generic.
4. **Loose (non-`application/`, non-`domain/`) files classified by reading
   content**, since the current repo has no folder to signal this:
   - → `application` (has side effects / orchestrates via a port):
     `tenancy/context_policy.py` and `tenancy/tenant_context.py`
     (orchestrate via `TenantRepository`/`OrganizationRepository`),
     `data_exchange/service.py`.
   - → `domain` (pure logic/policy, no I/O beyond stdlib):
     `site/access_policy.py`, `approval/policy.py`, `org/support.py`,
     `documents/support.py`, `employee/support.py`.
   - The `auth`-specific loose files (`auth/authorization.py`, `auth/policy.py`,
     `auth/sod.py`, `auth/mfa.py`, `auth/passwords.py`, `auth/datetime_utils.py`)
     are covered in detail in **§4a**, since most of them turned out to be
     authorization files misfiled under auth, not straightforward domain/
     application calls.
   - `auth/datetime_utils.py` is also imported by `identity/domain.py` (now
     `domain/security/identity/service_principal.py`) — it's arguably
     cross-cutting enough to promote to `common/` instead of
     `domain/security/auth/`. Flagging rather than deciding.
5. **`identity/domain.py` renamed to `service_principal.py`** on the way into
   `domain/security/identity/` — the bare name `domain.py` reads oddly nested
   two levels under a folder already called `domain/`.
6. **`modules/application/authorization.py`** (module-entitlement guard,
   `require_module_enabled`) is **not** related to `auth/authorization.py` or
   the `authorization/` engine — it's `modules`' own use-case check and stays
   under `application/tenant/modules/`. Flagging only so it isn't confused
   with the `security` group's authorization files during implementation.

## 8. Full file-by-file mapping

271 of 309 `src/core/platform/` files move (217 from §4a/§4b/§4c + 54 from
the §5a infrastructure regroup); 38 stay in place. All 42 live `src/api/`
files move (2 retire outright with no successor — see §4c). All 3 files in
`src/application/runtime/` move too (§4c). Generated directly from the
grouping rules above — no manual transcription.

Total core/platform files inventoried: 271

### Unchanged directories (already correct, or judged base-level/shared-kernel)
- `src/core/platform/__init__.py` (package root)
- `src/core/platform/access/`
- `src/core/platform/common/`
- `src/core/platform/finance/`
- `src/core/platform/integration/`
- `src/core/platform/infrastructure/` — package-root `__init__.py` files only (`infrastructure/__init__.py`, `persistence/__init__.py`, `mappers/__init__.py`, `orm/__init__.py`, `repositories/__init__.py`); everything else under it moves per §5a

### Moved/renamed files (271)

| Old path | New path | Note |
|---|---|---|
| `src/core/platform/activity/__init__.py` | `src/core/platform/application/history/activity/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/activity/application/__init__.py` | `src/core/platform/application/history/activity/__init__.py` |  |
| `src/core/platform/activity/application/activity_service.py` | `src/core/platform/application/history/activity/activity_service.py` |  |
| `src/core/platform/activity/contracts.py` | `src/core/platform/contract/history/activity/contracts.py` |  |
| `src/core/platform/activity/domain/__init__.py` | `src/core/platform/domain/history/activity/__init__.py` |  |
| `src/core/platform/activity/domain/activity_entry.py` | `src/core/platform/domain/history/activity/activity_entry.py` |  |
| `src/core/platform/approval/__init__.py` | `src/core/platform/application/approval/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/approval/application/__init__.py` | `src/core/platform/application/approval/__init__.py` |  |
| `src/core/platform/approval/application/approval_service.py` | `src/core/platform/application/approval/approval_service.py` |  |
| `src/core/platform/approval/contracts.py` | `src/core/platform/contract/approval/contracts.py` |  |
| `src/core/platform/approval/domain/__init__.py` | `src/core/platform/domain/approval/__init__.py` |  |
| `src/core/platform/approval/domain/approval_request.py` | `src/core/platform/domain/approval/approval_request.py` |  |
| `src/core/platform/approval/domain/approval_state.py` | `src/core/platform/domain/approval/approval_state.py` |  |
| `src/core/platform/approval/policy.py` | `src/core/platform/domain/approval/policy.py` |  |
| `src/core/platform/audit/__init__.py` | `src/core/platform/application/history/audit/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/audit/application/__init__.py` | `src/core/platform/application/history/audit/__init__.py` |  |
| `src/core/platform/audit/application/enterprise_audit_service.py` | `src/core/platform/application/history/audit/enterprise_audit_service.py` |  |
| `src/core/platform/audit/contracts.py` | `src/core/platform/contract/history/audit/contracts.py` |  |
| `src/core/platform/audit/domain/__init__.py` | `src/core/platform/domain/history/audit/__init__.py` |  |
| `src/core/platform/audit/domain/audit_entry.py` | `src/core/platform/domain/history/audit/audit_entry.py` |  |
| `src/core/platform/auth/__init__.py` | `src/core/platform/application/security/auth/__init__.py` | module facade removed — content redistributed |
| `src/core/platform/auth/application/__init__.py` | `src/core/platform/application/security/auth/__init__.py` |  |
| `src/core/platform/auth/application/audit_recorder.py` | `src/core/platform/application/security/auth/audit/audit_recorder.py` |  |
| `src/core/platform/auth/application/auth_query.py` | `src/core/platform/application/security/auth/auth_query.py` |  |
| `src/core/platform/auth/application/auth_service.py` | `src/core/platform/application/security/auth/auth_service.py` |  |
| `src/core/platform/auth/application/auth_validation.py` | `src/core/platform/application/security/auth/auth_validation.py` |  |
| `src/core/platform/auth/application/authentication_service.py` | `src/core/platform/application/security/auth/credentials/authentication_service.py` |  |
| `src/core/platform/auth/application/authentication_transactions.py` | `src/core/platform/application/security/auth/credentials/authentication_transactions.py` |  |
| `src/core/platform/auth/application/bootstrap_service.py` | `src/core/platform/application/security/auth/provisioning/bootstrap_service.py` |  |
| `src/core/platform/auth/application/canonical_role_resolver.py` | `src/core/platform/application/security/authorization/roles/canonical_role_resolver.py` | MOVED from auth — resolves canonical permission bindings, not an authentication concern |
| `src/core/platform/auth/application/context_switch_service.py` | `src/core/platform/application/security/auth/session/context_switch_service.py` |  |
| `src/core/platform/auth/application/default_seed_service.py` | `src/core/platform/application/security/auth/provisioning/default_seed_service.py` |  |
| `src/core/platform/auth/application/federated_identity_service.py` | `src/core/platform/application/security/auth/credentials/federated_identity_service.py` |  |
| `src/core/platform/auth/application/mfa_service.py` | `src/core/platform/application/security/auth/credentials/mfa_service.py` |  |
| `src/core/platform/auth/application/password_service.py` | `src/core/platform/application/security/auth/credentials/password_service.py` |  |
| `src/core/platform/auth/application/platform_owner_provisioning_service.py` | `src/core/platform/application/security/auth/provisioning/platform_owner_provisioning_service.py` |  |
| `src/core/platform/auth/application/principal_builder.py` | `src/core/platform/application/security/auth/session/principal_builder.py` |  |
| `src/core/platform/auth/application/registration_service.py` | `src/core/platform/application/security/auth/provisioning/registration_service.py` |  |
| `src/core/platform/auth/application/role_assignment_service.py` | `src/core/platform/application/security/authorization/roles/role_assignment_service.py` | MOVED from auth — grants/revokes role bindings |
| `src/core/platform/auth/application/role_governance_service.py` | `src/core/platform/application/security/authorization/roles/role_governance_service.py` | MOVED from auth — role delegation/binding governance |
| `src/core/platform/auth/application/role_policy_reconciliation_service.py` | `src/core/platform/application/security/authorization/roles/role_policy_reconciliation_service.py` | MOVED from auth — reconciles role-permission policy changes |
| `src/core/platform/auth/application/role_scope_policy.py` | `src/core/platform/application/security/authorization/roles/role_scope_policy.py` | MOVED from auth — role/scope classification policy |
| `src/core/platform/auth/application/scope_delegation_provisioning_service.py` | `src/core/platform/application/security/authorization/roles/scope_delegation_provisioning_service.py` | MOVED from auth — scope delegation plans |
| `src/core/platform/auth/application/security_audit.py` | `src/core/platform/application/security/auth/audit/security_audit.py` |  |
| `src/core/platform/auth/application/session_service.py` | `src/core/platform/application/security/auth/session/session_service.py` |  |
| `src/core/platform/auth/application/session_utils.py` | `src/core/platform/application/security/auth/session/session_utils.py` |  |
| `src/core/platform/auth/application/sod_enforcer.py` | `src/core/platform/application/security/authorization/enforcement/sod_enforcer.py` | MOVED from auth — separation-of-duties conflict enforcement |
| `src/core/platform/auth/application/target_user_authorization.py` | `src/core/platform/application/security/authorization/enforcement/target_user_authorization.py` | MOVED from auth — scope-based authorization checks (name says it outright) |
| `src/core/platform/auth/application/tenant_role_administration_service.py` | `src/core/platform/application/security/authorization/roles/tenant_role_administration_service.py` | MOVED from auth — tenant custom-role lifecycle |
| `src/core/platform/auth/application/user_admin_service.py` | `src/core/platform/application/security/auth/provisioning/user_admin_service.py` |  |
| `src/core/platform/auth/authorization.py` | `src/core/platform/application/security/authorization/enforcement/permission_checks.py` | MOVED + RENAMED from auth/authorization.py — require_permission/require_any_permission/record_authorization_denial; renamed to avoid clashing with domain authorization_engine.py |
| `src/core/platform/auth/contracts/__init__.py` | `src/core/platform/contract/security/auth/__init__.py` |  |
| `src/core/platform/auth/contracts/auth_repository.py` | `src/core/platform/contract/security/auth/auth_repository.py` |  |
| `src/core/platform/auth/datetime_utils.py` | `src/core/platform/domain/security/auth/datetime_utils.py` |  |
| `src/core/platform/auth/domain/__init__.py` | `src/core/platform/domain/security/auth/__init__.py` |  |
| `src/core/platform/auth/domain/policy_reconciliation.py` | `src/core/platform/domain/security/authorization/roles/policy_reconciliation.py` | MOVED from auth — tracks role/permission policy version reconciliation |
| `src/core/platform/auth/domain/role_binding.py` | `src/core/platform/domain/security/authorization/roles/role_binding.py` | MOVED from auth — who has what role in what scope |
| `src/core/platform/auth/domain/role_delegation.py` | `src/core/platform/domain/security/authorization/roles/role_delegation.py` | MOVED from auth — who may delegate what role |
| `src/core/platform/auth/domain/session.py` | `src/core/platform/domain/security/auth/session.py` |  |
| `src/core/platform/auth/domain/user.py` | `src/core/platform/domain/security/auth/user.py` |  |
| `src/core/platform/auth/mfa.py` | `src/core/platform/domain/security/auth/credentials/mfa.py` |  |
| `src/core/platform/auth/passwords.py` | `src/core/platform/domain/security/auth/credentials/passwords.py` |  |
| `src/core/platform/auth/policy.py` | `(manual split required)` | SPLIT REQUIRED: DEFAULT_PERMISSIONS/DEFAULT_ROLE_PERMISSIONS/SYSTEM_ROLE_POLICY_* -> domain/security/authorization/roles/role_permission_catalog.py; login_lockout_threshold/login_lockout_minutes/session_timeout_minutes -> domain/security/auth/login_security_policy.py |
| `src/core/platform/auth/sod.py` | `src/core/platform/domain/security/authorization/enforcement/sod.py` | MOVED from auth — SeparationOfDutiesPolicy |
| `src/core/platform/authorization/__init__.py` | `src/core/platform/application/security/authorization/__init__.py` | module facade removed — content redistributed |
| `src/core/platform/authorization/application/__init__.py` | `src/core/platform/application/security/authorization/__init__.py` |  |
| `src/core/platform/authorization/application/session_authorization_engine.py` | `src/core/platform/application/security/authorization/enforcement/session_authorization_engine.py` | subfoldered to sit with the other runtime-decision files |
| `src/core/platform/authorization/domain/__init__.py` | `src/core/platform/domain/security/authorization/__init__.py` |  |
| `src/core/platform/authorization/domain/authorization_engine.py` | `src/core/platform/domain/security/authorization/enforcement/authorization_engine.py` | subfoldered to sit with the other runtime-decision files |
| `src/core/platform/authorization/domain/security_decision.py` | `src/core/platform/domain/security/authorization/enforcement/security_decision.py` | subfoldered to sit with the other runtime-decision files |
| `src/core/platform/calendar/__init__.py` | `src/core/platform/application/time_management/calendar/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/calendar/application/__init__.py` | `src/core/platform/application/time_management/calendar/__init__.py` |  |
| `src/core/platform/calendar/application/calendar_assignment_service.py` | `src/core/platform/application/time_management/calendar/assignment/calendar_assignment_service.py` |  |
| `src/core/platform/calendar/application/calendar_exception_service.py` | `src/core/platform/application/time_management/calendar/definitions/calendar_exception_service.py` |  |
| `src/core/platform/calendar/application/calendar_protocol.py` | `src/core/platform/contract/time_management/calendar/calendar_protocol.py` | MOVED from application/ to contract/ — a structural Protocol (port) other modules import as a type annotation, not a service with behavior; belongs alongside contracts.py, not application logic. Same category of finding as auth/authorization.py in §4a. |
| `src/core/platform/calendar/application/enterprise_calendar_resolver.py` | `src/core/platform/application/time_management/calendar/capacity/enterprise_calendar_resolver.py` |  |
| `src/core/platform/calendar/application/enterprise_calendar_service.py` | `src/core/platform/application/time_management/calendar/enterprise_calendar_service.py` |  |
| `src/core/platform/calendar/application/global_calendar_shim.py` | `src/core/platform/application/time_management/calendar/capacity/global_calendar_shim.py` |  |
| `src/core/platform/calendar/application/recurring_event_service.py` | `src/core/platform/application/time_management/calendar/definitions/recurring_event_service.py` |  |
| `src/core/platform/calendar/application/shift_pattern_service.py` | `src/core/platform/application/time_management/calendar/definitions/shift_pattern_service.py` |  |
| `src/core/platform/calendar/application/working_rule_service.py` | `src/core/platform/application/time_management/calendar/definitions/working_rule_service.py` |  |
| `src/core/platform/calendar/application/working_time_calculator.py` | `src/core/platform/application/time_management/calendar/capacity/working_time_calculator.py` |  |
| `src/core/platform/calendar/contracts.py` | `src/core/platform/contract/time_management/calendar/contracts.py` |  |
| `src/core/platform/calendar/domain/__init__.py` | `src/core/platform/domain/time_management/calendar/__init__.py` |  |
| `src/core/platform/calendar/domain/enterprise_calendar.py` | `src/core/platform/domain/time_management/calendar/enterprise_calendar.py` |  |
| `src/core/platform/data_exchange/__init__.py` | `src/core/platform/application/master_data/data_exchange/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/data_exchange/service.py` | `src/core/platform/application/master_data/data_exchange/service.py` |  |
| `src/core/platform/department/__init__.py` | `src/core/platform/application/master_data/department/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/department/application/__init__.py` | `src/core/platform/application/master_data/department/__init__.py` |  |
| `src/core/platform/department/application/department_access.py` | `src/core/platform/application/master_data/department/department_access.py` |  |
| `src/core/platform/department/application/department_commands.py` | `src/core/platform/application/master_data/department/department_commands.py` |  |
| `src/core/platform/department/application/department_context.py` | `src/core/platform/application/master_data/department/department_context.py` |  |
| `src/core/platform/department/application/department_location_service.py` | `src/core/platform/application/master_data/department/department_location_service.py` |  |
| `src/core/platform/department/application/department_queries.py` | `src/core/platform/application/master_data/department/department_queries.py` |  |
| `src/core/platform/department/application/department_service.py` | `src/core/platform/application/master_data/department/department_service.py` |  |
| `src/core/platform/department/application/department_utils.py` | `src/core/platform/application/master_data/department/department_utils.py` |  |
| `src/core/platform/department/application/department_validation.py` | `src/core/platform/application/master_data/department/department_validation.py` |  |
| `src/core/platform/department/contracts.py` | `src/core/platform/contract/master_data/department/contracts.py` |  |
| `src/core/platform/department/domain/__init__.py` | `src/core/platform/domain/master_data/department/__init__.py` |  |
| `src/core/platform/department/domain/department.py` | `src/core/platform/domain/master_data/department/department.py` |  |
| `src/core/platform/documents/__init__.py` | `src/core/platform/application/master_data/documents/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/documents/application/__init__.py` | `src/core/platform/application/master_data/documents/__init__.py` |  |
| `src/core/platform/documents/application/document_integration_service.py` | `src/core/platform/application/master_data/documents/document_integration_service.py` |  |
| `src/core/platform/documents/application/document_service.py` | `src/core/platform/application/master_data/documents/document_service.py` |  |
| `src/core/platform/documents/contracts.py` | `src/core/platform/contract/master_data/documents/contracts.py` |  |
| `src/core/platform/documents/domain/__init__.py` | `src/core/platform/domain/master_data/documents/__init__.py` |  |
| `src/core/platform/documents/domain/document.py` | `src/core/platform/domain/master_data/documents/document.py` |  |
| `src/core/platform/documents/domain/document_link.py` | `src/core/platform/domain/master_data/documents/document_link.py` |  |
| `src/core/platform/documents/domain/document_structure.py` | `src/core/platform/domain/master_data/documents/document_structure.py` |  |
| `src/core/platform/documents/support.py` | `src/core/platform/domain/master_data/documents/support.py` |  |
| `src/core/platform/employee/__init__.py` | `src/core/platform/application/master_data/employee/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/employee/application/__init__.py` | `src/core/platform/application/master_data/employee/__init__.py` |  |
| `src/core/platform/employee/application/employee_service.py` | `src/core/platform/application/master_data/employee/employee_service.py` |  |
| `src/core/platform/employee/application/employee_support.py` | `src/core/platform/application/master_data/employee/employee_support.py` |  |
| `src/core/platform/employee/contracts.py` | `src/core/platform/contract/master_data/employee/contracts.py` |  |
| `src/core/platform/employee/domain/__init__.py` | `src/core/platform/domain/master_data/employee/__init__.py` |  |
| `src/core/platform/employee/domain/employee.py` | `src/core/platform/domain/master_data/employee/employee.py` |  |
| `src/core/platform/employee/support.py` | `src/core/platform/domain/master_data/employee/support.py` |  |
| `src/core/platform/exporting/__init__.py` | `src/core/platform/application/data_operations/exporting/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/exporting/application/__init__.py` | `src/core/platform/application/data_operations/exporting/__init__.py` |  |
| `src/core/platform/exporting/application/artifact_delivery.py` | `src/core/platform/application/data_operations/exporting/artifact_delivery.py` |  |
| `src/core/platform/exporting/application/export_definition_registry.py` | `src/core/platform/application/data_operations/exporting/export_definition_registry.py` |  |
| `src/core/platform/exporting/application/export_runtime.py` | `src/core/platform/application/data_operations/exporting/export_runtime.py` |  |
| `src/core/platform/exporting/domain/__init__.py` | `src/core/platform/domain/data_operations/exporting/__init__.py` |  |
| `src/core/platform/exporting/domain/export_definition.py` | `src/core/platform/domain/data_operations/exporting/export_definition.py` |  |
| `src/core/platform/exporting/domain/export_models.py` | `src/core/platform/domain/data_operations/exporting/export_models.py` |  |
| `src/core/platform/identity/__init__.py` | `src/core/platform/application/security/identity/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/identity/application/__init__.py` | `src/core/platform/application/security/identity/__init__.py` |  |
| `src/core/platform/identity/application/service_principal_service.py` | `src/core/platform/application/security/identity/service_principal_service.py` |  |
| `src/core/platform/identity/contracts.py` | `src/core/platform/contract/security/identity/contracts.py` |  |
| `src/core/platform/identity/domain.py` | `src/core/platform/domain/security/identity/service_principal.py` | single-file domain module, renamed for clarity |
| `src/core/platform/importing/__init__.py` | `src/core/platform/application/data_operations/importing/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/importing/application/__init__.py` | `src/core/platform/application/data_operations/importing/__init__.py` |  |
| `src/core/platform/importing/application/csv_import_runtime.py` | `src/core/platform/application/data_operations/importing/csv_import_runtime.py` |  |
| `src/core/platform/importing/application/import_definition_registry.py` | `src/core/platform/application/data_operations/importing/import_definition_registry.py` |  |
| `src/core/platform/importing/domain/__init__.py` | `src/core/platform/domain/data_operations/importing/__init__.py` |  |
| `src/core/platform/importing/domain/import_definition.py` | `src/core/platform/domain/data_operations/importing/import_definition.py` |  |
| `src/core/platform/importing/domain/import_models.py` | `src/core/platform/domain/data_operations/importing/import_models.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/activity.py` | `src/core/platform/infrastructure/persistence/mappers/history/activity/activity.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/approval.py` | `src/core/platform/infrastructure/persistence/mappers/approval/approval.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/audit_entry.py` | `src/core/platform/infrastructure/persistence/mappers/history/audit/audit_entry.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/auth.py` | `src/core/platform/infrastructure/persistence/mappers/security/auth/auth.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/departments.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/department/departments.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/documents.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/documents/documents.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/employee.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/employee/employee.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/enterprise_calendar.py` | `src/core/platform/infrastructure/persistence/mappers/time_management/calendar/enterprise_calendar.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/notification.py` | `src/core/platform/infrastructure/persistence/mappers/events/notifications/notification.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/org.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/org/org.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/party.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/party/party.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/platform_events.py` | `src/core/platform/infrastructure/persistence/mappers/events/platform_events/platform_events.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/sites.py` | `src/core/platform/infrastructure/persistence/mappers/master_data/site/sites.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/tenant.py` | `src/core/platform/infrastructure/persistence/mappers/tenant/tenancy/tenant.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/time.py` | `src/core/platform/infrastructure/persistence/mappers/time_management/time/time.py` |  |
| `src/core/platform/infrastructure/persistence/mappers/user_tenant.py` | `src/core/platform/infrastructure/persistence/mappers/tenant/tenancy/user_tenant.py` |  |
| `src/core/platform/infrastructure/persistence/orm/activity.py` | `src/core/platform/infrastructure/persistence/orm/history/activity/activity.py` |  |
| `src/core/platform/infrastructure/persistence/orm/approval.py` | `src/core/platform/infrastructure/persistence/orm/approval/approval.py` |  |
| `src/core/platform/infrastructure/persistence/orm/audit_entry.py` | `src/core/platform/infrastructure/persistence/orm/history/audit/audit_entry.py` |  |
| `src/core/platform/infrastructure/persistence/orm/auth.py` | `src/core/platform/infrastructure/persistence/orm/security/auth/auth.py` |  |
| `src/core/platform/infrastructure/persistence/orm/departments.py` | `src/core/platform/infrastructure/persistence/orm/master_data/department/departments.py` |  |
| `src/core/platform/infrastructure/persistence/orm/documents.py` | `src/core/platform/infrastructure/persistence/orm/master_data/documents/documents.py` |  |
| `src/core/platform/infrastructure/persistence/orm/employee.py` | `src/core/platform/infrastructure/persistence/orm/master_data/employee/employee.py` |  |
| `src/core/platform/infrastructure/persistence/orm/enterprise_calendar.py` | `src/core/platform/infrastructure/persistence/orm/time_management/calendar/enterprise_calendar.py` |  |
| `src/core/platform/infrastructure/persistence/orm/identity.py` | `src/core/platform/infrastructure/persistence/orm/security/identity/identity.py` |  |
| `src/core/platform/infrastructure/persistence/orm/modules.py` | `src/core/platform/infrastructure/persistence/orm/tenant/modules/modules.py` |  |
| `src/core/platform/infrastructure/persistence/orm/notification.py` | `src/core/platform/infrastructure/persistence/orm/events/notifications/notification.py` |  |
| `src/core/platform/infrastructure/persistence/orm/org.py` | `src/core/platform/infrastructure/persistence/orm/master_data/org/org.py` |  |
| `src/core/platform/infrastructure/persistence/orm/party.py` | `src/core/platform/infrastructure/persistence/orm/master_data/party/party.py` |  |
| `src/core/platform/infrastructure/persistence/orm/platform_events.py` | `src/core/platform/infrastructure/persistence/orm/events/platform_events/platform_events.py` |  |
| `src/core/platform/infrastructure/persistence/orm/runtime_tracking.py` | `src/core/platform/infrastructure/persistence/orm/data_operations/runtime_tracking/runtime_tracking.py` |  |
| `src/core/platform/infrastructure/persistence/orm/sites.py` | `src/core/platform/infrastructure/persistence/orm/master_data/site/sites.py` |  |
| `src/core/platform/infrastructure/persistence/orm/tenant.py` | `src/core/platform/infrastructure/persistence/orm/tenant/tenancy/tenant.py` |  |
| `src/core/platform/infrastructure/persistence/orm/time.py` | `src/core/platform/infrastructure/persistence/orm/time_management/time/time.py` |  |
| `src/core/platform/infrastructure/persistence/orm/user_tenant.py` | `src/core/platform/infrastructure/persistence/orm/tenant/tenancy/user_tenant.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/activity.py` | `src/core/platform/infrastructure/persistence/repositories/history/activity/activity.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/approval.py` | `src/core/platform/infrastructure/persistence/repositories/approval/approval.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/audit_entry.py` | `src/core/platform/infrastructure/persistence/repositories/history/audit/audit_entry.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/auth.py` | `src/core/platform/infrastructure/persistence/repositories/security/auth/auth.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/departments.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/department/departments.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/documents.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/documents/documents.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/employee.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/employee/employee.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/enterprise_calendar.py` | `src/core/platform/infrastructure/persistence/repositories/time_management/calendar/enterprise_calendar.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/identity.py` | `src/core/platform/infrastructure/persistence/repositories/security/identity/identity.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/modules.py` | `src/core/platform/infrastructure/persistence/repositories/tenant/modules/modules.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/notification.py` | `src/core/platform/infrastructure/persistence/repositories/events/notifications/notification.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/org.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/org/org.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/party.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/party/party.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/platform_events.py` | `src/core/platform/infrastructure/persistence/repositories/events/platform_events/platform_events.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/runtime_tracking.py` | `src/core/platform/infrastructure/persistence/repositories/data_operations/runtime_tracking/runtime_tracking.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/sites.py` | `src/core/platform/infrastructure/persistence/repositories/master_data/site/sites.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/tenant.py` | `src/core/platform/infrastructure/persistence/repositories/tenant/tenancy/tenant.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/time.py` | `src/core/platform/infrastructure/persistence/repositories/time_management/time/time.py` |  |
| `src/core/platform/infrastructure/persistence/repositories/user_tenant.py` | `src/core/platform/infrastructure/persistence/repositories/tenant/tenancy/user_tenant.py` |  |
| `src/core/platform/modules/__init__.py` | `src/core/platform/application/tenant/modules/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/modules/application/__init__.py` | `src/core/platform/application/tenant/modules/__init__.py` |  |
| `src/core/platform/modules/application/authorization.py` | `src/core/platform/application/tenant/modules/authorization.py` |  |
| `src/core/platform/modules/application/guard.py` | `src/core/platform/application/tenant/modules/guard.py` |  |
| `src/core/platform/modules/application/module_catalog_context.py` | `src/core/platform/application/tenant/modules/module_catalog_context.py` |  |
| `src/core/platform/modules/application/module_catalog_mutation.py` | `src/core/platform/application/tenant/modules/module_catalog_mutation.py` |  |
| `src/core/platform/modules/application/module_catalog_query.py` | `src/core/platform/application/tenant/modules/module_catalog_query.py` |  |
| `src/core/platform/modules/application/module_catalog_service.py` | `src/core/platform/application/tenant/modules/module_catalog_service.py` |  |
| `src/core/platform/modules/contracts.py` | `src/core/platform/contract/tenant/modules/contracts.py` |  |
| `src/core/platform/modules/domain/__init__.py` | `src/core/platform/domain/tenant/modules/__init__.py` |  |
| `src/core/platform/modules/domain/defaults.py` | `src/core/platform/domain/tenant/modules/defaults.py` |  |
| `src/core/platform/modules/domain/module_codes.py` | `src/core/platform/domain/tenant/modules/module_codes.py` |  |
| `src/core/platform/modules/domain/module_definition.py` | `src/core/platform/domain/tenant/modules/module_definition.py` |  |
| `src/core/platform/modules/domain/module_entitlement.py` | `src/core/platform/domain/tenant/modules/module_entitlement.py` |  |
| `src/core/platform/modules/domain/subscription.py` | `src/core/platform/domain/tenant/modules/subscription.py` |  |
| `src/core/platform/notifications/__init__.py` | `src/core/platform/application/events/notifications/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/notifications/application/__init__.py` | `src/core/platform/application/events/notifications/__init__.py` |  |
| `src/core/platform/notifications/application/notification_service.py` | `src/core/platform/application/events/notifications/notification_service.py` |  |
| `src/core/platform/notifications/contracts.py` | `src/core/platform/contract/events/notifications/contracts.py` |  |
| `src/core/platform/notifications/domain/__init__.py` | `src/core/platform/domain/events/notifications/__init__.py` |  |
| `src/core/platform/notifications/domain/notification.py` | `src/core/platform/domain/events/notifications/notification.py` |  |
| `src/core/platform/org/__init__.py` | `src/core/platform/application/master_data/org/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/org/application/__init__.py` | `src/core/platform/application/master_data/org/__init__.py` |  |
| `src/core/platform/org/application/organization_service.py` | `src/core/platform/application/master_data/org/organization_service.py` |  |
| `src/core/platform/org/contracts.py` | `src/core/platform/contract/master_data/org/contracts.py` |  |
| `src/core/platform/org/domain/__init__.py` | `src/core/platform/domain/master_data/org/__init__.py` |  |
| `src/core/platform/org/domain/organization.py` | `src/core/platform/domain/master_data/org/organization.py` |  |
| `src/core/platform/org/support.py` | `src/core/platform/domain/master_data/org/support.py` |  |
| `src/core/platform/party/__init__.py` | `src/core/platform/application/master_data/party/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/party/application/__init__.py` | `src/core/platform/application/master_data/party/__init__.py` |  |
| `src/core/platform/party/application/party_service.py` | `src/core/platform/application/master_data/party/party_service.py` |  |
| `src/core/platform/party/contracts.py` | `src/core/platform/contract/master_data/party/contracts.py` |  |
| `src/core/platform/party/domain/__init__.py` | `src/core/platform/domain/master_data/party/__init__.py` |  |
| `src/core/platform/party/domain/party.py` | `src/core/platform/domain/master_data/party/party.py` |  |
| `src/core/platform/platform_events/__init__.py` | `src/core/platform/application/events/platform_events/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/platform_events/contracts.py` | `src/core/platform/contract/events/platform_events/contracts.py` |  |
| `src/core/platform/platform_events/domain/__init__.py` | `src/core/platform/domain/events/platform_events/__init__.py` |  |
| `src/core/platform/platform_events/domain/platform_event.py` | `src/core/platform/domain/events/platform_events/platform_event.py` |  |
| `src/core/platform/report_runtime/__init__.py` | `src/core/platform/application/data_operations/report_runtime/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/report_runtime/application/__init__.py` | `src/core/platform/application/data_operations/report_runtime/__init__.py` |  |
| `src/core/platform/report_runtime/application/report_definition_registry.py` | `src/core/platform/application/data_operations/report_runtime/report_definition_registry.py` |  |
| `src/core/platform/report_runtime/application/report_runtime.py` | `src/core/platform/application/data_operations/report_runtime/report_runtime.py` |  |
| `src/core/platform/report_runtime/domain/__init__.py` | `src/core/platform/domain/data_operations/report_runtime/__init__.py` |  |
| `src/core/platform/report_runtime/domain/report_definition.py` | `src/core/platform/domain/data_operations/report_runtime/report_definition.py` |  |
| `src/core/platform/report_runtime/domain/report_document.py` | `src/core/platform/domain/data_operations/report_runtime/report_document.py` |  |
| `src/core/platform/runtime_tracking/__init__.py` | `src/core/platform/application/data_operations/runtime_tracking/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/runtime_tracking/application/__init__.py` | `src/core/platform/application/data_operations/runtime_tracking/__init__.py` |  |
| `src/core/platform/runtime_tracking/application/runtime_execution_service.py` | `src/core/platform/application/data_operations/runtime_tracking/runtime_execution_service.py` |  |
| `src/core/platform/runtime_tracking/contracts.py` | `src/core/platform/contract/data_operations/runtime_tracking/contracts.py` |  |
| `src/core/platform/runtime_tracking/domain/__init__.py` | `src/core/platform/domain/data_operations/runtime_tracking/__init__.py` |  |
| `src/core/platform/runtime_tracking/domain/runtime_execution.py` | `src/core/platform/domain/data_operations/runtime_tracking/runtime_execution.py` |  |
| `src/core/platform/site/__init__.py` | `src/core/platform/application/master_data/site/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/site/access_policy.py` | `src/core/platform/domain/master_data/site/access_policy.py` |  |
| `src/core/platform/site/application/__init__.py` | `src/core/platform/application/master_data/site/__init__.py` |  |
| `src/core/platform/site/application/site_service.py` | `src/core/platform/application/master_data/site/site_service.py` |  |
| `src/core/platform/site/contracts.py` | `src/core/platform/contract/master_data/site/contracts.py` |  |
| `src/core/platform/site/domain/__init__.py` | `src/core/platform/domain/master_data/site/__init__.py` |  |
| `src/core/platform/site/domain/site.py` | `src/core/platform/domain/master_data/site/site.py` |  |
| `src/core/platform/tenancy/__init__.py` | `src/core/platform/application/tenant/tenancy/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/tenancy/application/__init__.py` | `src/core/platform/application/tenant/tenancy/__init__.py` |  |
| `src/core/platform/tenancy/application/tenant_admin_service.py` | `src/core/platform/application/tenant/tenancy/tenant_admin_service.py` |  |
| `src/core/platform/tenancy/application/tenant_membership_service.py` | `src/core/platform/application/tenant/tenancy/tenant_membership_service.py` |  |
| `src/core/platform/tenancy/context_policy.py` | `src/core/platform/application/tenant/tenancy/context_policy.py` |  |
| `src/core/platform/tenancy/contracts.py` | `src/core/platform/contract/tenant/tenancy/contracts.py` |  |
| `src/core/platform/tenancy/domain/__init__.py` | `src/core/platform/domain/tenant/tenancy/__init__.py` |  |
| `src/core/platform/tenancy/domain/tenant.py` | `src/core/platform/domain/tenant/tenancy/tenant.py` |  |
| `src/core/platform/tenancy/domain/user_tenant_membership.py` | `src/core/platform/domain/tenant/tenancy/user_tenant_membership.py` |  |
| `src/core/platform/tenancy/tenant_context.py` | `src/core/platform/application/tenant/tenancy/tenant_context.py` |  |
| `src/core/platform/time/__init__.py` | `src/core/platform/application/time_management/time/__init__.py` | module facade removed — replaced by per-layer __init__.py; content redistributed (see notes) |
| `src/core/platform/time/application/__init__.py` | `src/core/platform/application/time_management/time/__init__.py` |  |
| `src/core/platform/time/application/time_service.py` | `src/core/platform/application/time_management/time/time_service.py` |  |
| `src/core/platform/time/application/timesheet_entries.py` | `src/core/platform/application/time_management/time/timesheet_entries.py` |  |
| `src/core/platform/time/application/timesheet_periods.py` | `src/core/platform/application/time_management/time/timesheet_periods.py` |  |
| `src/core/platform/time/application/timesheet_query.py` | `src/core/platform/application/time_management/time/timesheet_query.py` |  |
| `src/core/platform/time/application/timesheet_review.py` | `src/core/platform/application/time_management/time/timesheet_review.py` |  |
| `src/core/platform/time/application/timesheet_support.py` | `src/core/platform/application/time_management/time/timesheet_support.py` |  |
| `src/core/platform/time/contracts.py` | `src/core/platform/contract/time_management/time/contracts.py` |  |
| `src/core/platform/time/domain/__init__.py` | `src/core/platform/domain/time_management/time/__init__.py` |  |
| `src/core/platform/time/domain/timesheet_models.py` | `src/core/platform/domain/time_management/time/timesheet_models.py` |  |

### api/ moves (42)

| Old path | New path | Note |
|---|---|---|
| `src/api/__init__.py` | `(retired)` | trivial docstring-only package marker; src/api/ has no successor package once its contents redistribute to core/platform/api and application/runtime |
| `src/api/desktop/__init__.py` | `(retired)` | re-export role (DesktopApiRegistry/build_desktop_api_registry) superseded by src/application/runtime/__init__.py — see runtime-confusion investigation |
| `src/api/desktop/integration/__init__.py` | `src/core/platform/api/desktop/integration/__init__.py` | cross-module integration API — pairs with base-level integration/ kernel |
| `src/api/desktop/integration/capability_api.py` | `src/core/platform/api/desktop/integration/capability_api.py` | cross-module integration API — pairs with base-level integration/ kernel |
| `src/api/desktop/platform/__init__.py` | `src/core/platform/api/desktop/__init__.py` | merged into the desktop api package facade |
| `src/api/desktop/platform/_approval_labels.py` | `src/core/platform/api/desktop/approval/_approval_labels.py` |  |
| `src/api/desktop/platform/_support.py` | `src/core/platform/api/desktop/support/_support.py` |  |
| `src/api/desktop/platform/access.py` | `src/core/platform/api/desktop/access/access.py` |  |
| `src/api/desktop/platform/activity.py` | `src/core/platform/api/desktop/history/activity/activity.py` |  |
| `src/api/desktop/platform/approval.py` | `src/core/platform/api/desktop/approval/approval.py` |  |
| `src/api/desktop/platform/audit_enterprise.py` | `src/core/platform/api/desktop/history/audit/audit_enterprise.py` |  |
| `src/api/desktop/platform/department.py` | `src/core/platform/api/desktop/master_data/department/department.py` |  |
| `src/api/desktop/platform/document.py` | `src/core/platform/api/desktop/master_data/documents/document.py` |  |
| `src/api/desktop/platform/employee.py` | `src/core/platform/api/desktop/master_data/employee/employee.py` |  |
| `src/api/desktop/platform/enterprise_calendar.py` | `src/core/platform/api/desktop/time_management/calendar/enterprise_calendar.py` |  |
| `src/api/desktop/platform/identity.py` | `src/core/platform/api/desktop/security/identity/identity.py` |  |
| `src/api/desktop/platform/models/__init__.py` | `src/core/platform/api/desktop/models/__init__.py` | consolidated API-model registry, stays at api/desktop root |
| `src/api/desktop/platform/models/access.py` | `src/core/platform/api/desktop/access/models/access.py` |  |
| `src/api/desktop/platform/models/activity.py` | `src/core/platform/api/desktop/history/activity/models/activity.py` |  |
| `src/api/desktop/platform/models/approval.py` | `src/core/platform/api/desktop/approval/models/approval.py` |  |
| `src/api/desktop/platform/models/audit_entry.py` | `src/core/platform/api/desktop/history/audit/models/audit_entry.py` |  |
| `src/api/desktop/platform/models/calendar.py` | `src/core/platform/api/desktop/time_management/calendar/models/calendar.py` |  |
| `src/api/desktop/platform/models/common.py` | `src/core/platform/api/desktop/models/common.py` | shared/base API model, not group-specific |
| `src/api/desktop/platform/models/department.py` | `src/core/platform/api/desktop/master_data/department/models/department.py` |  |
| `src/api/desktop/platform/models/document.py` | `src/core/platform/api/desktop/master_data/documents/models/document.py` |  |
| `src/api/desktop/platform/models/employee.py` | `src/core/platform/api/desktop/master_data/employee/models/employee.py` |  |
| `src/api/desktop/platform/models/enterprise_calendar.py` | `src/core/platform/api/desktop/time_management/calendar/models/enterprise_calendar.py` |  |
| `src/api/desktop/platform/models/identity.py` | `src/core/platform/api/desktop/security/identity/models/identity.py` |  |
| `src/api/desktop/platform/models/organization.py` | `src/core/platform/api/desktop/master_data/org/models/organization.py` |  |
| `src/api/desktop/platform/models/party.py` | `src/core/platform/api/desktop/master_data/party/models/party.py` |  |
| `src/api/desktop/platform/models/runtime.py` | `src/core/platform/api/desktop/platform_runtime/models/runtime.py` |  |
| `src/api/desktop/platform/models/site.py` | `src/core/platform/api/desktop/master_data/site/models/site.py` |  |
| `src/api/desktop/platform/models/support.py` | `src/core/platform/api/desktop/support/models/support.py` |  |
| `src/api/desktop/platform/models/tenant.py` | `src/core/platform/api/desktop/tenant/tenancy/models/tenant.py` |  |
| `src/api/desktop/platform/models/user.py` | `src/core/platform/api/desktop/security/auth/models/user.py` |  |
| `src/api/desktop/platform/party.py` | `src/core/platform/api/desktop/master_data/party/party.py` |  |
| `src/api/desktop/platform/runtime.py` | `src/core/platform/api/desktop/platform_runtime/runtime.py` |  |
| `src/api/desktop/platform/site.py` | `src/core/platform/api/desktop/master_data/site/site.py` |  |
| `src/api/desktop/platform/support.py` | `src/core/platform/api/desktop/support/support.py` |  |
| `src/api/desktop/platform/tenant.py` | `src/core/platform/api/desktop/tenant/tenancy/tenant.py` |  |
| `src/api/desktop/platform/user.py` | `src/core/platform/api/desktop/security/auth/user.py` |  |
| `src/api/desktop/runtime.py` | `src/application/runtime/desktop_api_registry.py` | MOVED OUT of api/ entirely — this is the one true cross-module orchestrator (composes platform's own runtime + PM/inventory/maintenance's own runtimes), not platform-owned content. See runtime-confusion investigation. |

### src/application/ moves (3)

| Old path | New path | Note |
|---|---|---|
| `src/application/runtime/__init__.py` | `src/application/runtime/__init__.py` | content REPLACED, not just moved — becomes the re-export facade for DesktopApiRegistry/build_desktop_api_registry (absorbing src/api/desktop/__init__.py's old role), not the old empty docstring |
| `src/application/runtime/entitlement_runtime.py` | `src/core/platform/api/desktop_runtime/service_resolver.py` | CONFIRMED: ModuleRuntimeService wrapper class eliminated, not relocated — only the resolver function (retargeted to return ModuleCatalogService directly) and the ModuleRuntimeSnapshot dataclass + its assembly (as a plain function) move into service_resolver.py, mirroring every other module's convention. All ~15 bare delegate methods on the old wrapper are gone; call sites use ModuleCatalogService's identically-named methods directly. See §4c. |
| `src/application/runtime/platform_runtime.py` | `src/core/platform/application/platform_runtime/platform_runtime_service.py` | MOVED INTO platform — PlatformRuntimeApplicationService has real orchestration logic (permission checks, default-module selection, multi-service coordination across modules+org+tenancy), unlike the other modules' desktop_runtime/ wiring files, so it belongs in application/ (per the layer-first structure) as its own single-member group, not in an api/desktop_runtime wiring folder. |

## 9. Import-change impact — the part that dominates the actual effort

The 271 file moves above are the easy part. The expensive part is that
**every module under `src/core/platform/` re-exports its full public surface
through its own package `__init__.py`** (verified by reading
`tenancy/__init__.py`, `site/__init__.py`, `department/__init__.py`,
`auth/__init__.py`, `access/__init__.py`, `authorization/__init__.py`,
`modules/__init__.py`, `common/__init__.py`). Callers overwhelmingly import
the flat facade, e.g. `from src.core.platform.tenancy import Tenant,
TenantContextService` — one line pulling in a domain type and an application
service together.

Measured scope:

| Metric | Count |
|---|---|
| `from src.core.platform.<x> import ...` lines, whole repo | 2,307 |
| distinct files outside `core/platform` referencing `core.platform` | 508 |
| `from src.api...` import lines, whole repo | 182 |
| distinct files referencing `src.api` | 93 |
| files importing `src.application.runtime.entitlement_runtime` (§4c) | 9 |
| files importing `src.application.runtime.platform_runtime` (§4c) | 6 |
| files importing `src.api.desktop.runtime` / the `api.desktop` facade (§4c) | 27 |

Because this proposal is layer-first, a former module's facade (e.g.
`tenancy/__init__.py` re-exporting both `Tenant` — now
`domain/tenant/tenancy/tenant.py` — and `TenantContextService` — now
`application/tenant/tenancy/tenant_context.py`) **cannot be reproduced by one
new file** the way a pure rename could. A single old import line frequently
has to split into two or three new import lines depending on which new layer
each imported name landed in. This is true restructuring, not a mechanical
path rename, and it is the main cost driver — not the 271 file moves.

**No compatibility shims.** `EXECUTION_SPEC.md`'s existing hard rule for this
repo is explicit: *"no compatibility facades, no re-export wrappers, no
temporary old-path modules... each completed slice removes its old paths."*
This proposal follows that same convention — every one of the 508 external
call sites gets rewritten to import from its real new location; nothing is
papered over with a forwarding shim at the old module path. That keeps one
migration style across the whole repo instead of introducing a second
"platform gets facades, everything else doesn't" precedent.

Practical mechanics for whoever executes this:

1. For each old module, build a name → new-path lookup from that module's old
   `__init__.py` (which name came from `.domain`, `.application`, `.contracts`,
   or a loose file) — the mapping table in §8 already gives the per-file
   destination.
2. Script the import rewrite (e.g. a codemod over the 508 files) rather than
   hand-editing; the `from src.core.platform.<module> import (A, B, C)` shape
   is regular enough to automate reliably, but only after the per-name
   destination map from step 1 exists.
3. Follow `EXECUTION_SPEC.md`'s existing "one slice at a time" discipline:
   move one group (e.g. `history` — smallest, 2 capabilities, 10 files) →
   rewrite its callers → run tests → move to the next group. Don't do all
   271 files in one commit.
4. `src/tests/architecture/*` will need updating in the same slice as the
   group it tests — see §9a for exactly which test files touch each group,
   instead of estimating from the repo-wide counts above.

## 9a. Test impact — every file in `src/tests/` checked (2026-08-04)

You asked for all tests to be investigated and mapped, not just estimated
from the repo-wide counts in §9. Every `.py` file under `src/tests/` was
scanned for `from src.core.platform.<module> import ...`,
`from src.api.<x> import ...`, and any `src.application.runtime` reference.


### Why this changes the §9 mechanics slightly

`common` is by far the most-referenced module in tests (123 files) but it's
also completely unchanged by this proposal (§5) — so the naive "208 test
files reference platform" count overstates the real work. Filtering to only
modules this proposal actually moves gives the accurate number: **141 test
files need an import rewrite; 67 need zero changes** despite matching the
grep.

This also gives independent, data-backed support for two calls made
elsewhere in this doc:
- The §12 recommendation to slice `history` first: `audit` and `activity`
  are referenced by exactly 1 test file each — the lowest blast radius of
  any group, confirming it's safe to go first.
- `auth` is both the largest single code move (§4a) and the most
  test-referenced module (52 files) — confirming it's the highest-risk slice
  and should probably be scheduled last, once the mechanical rewrite process
  has been proven on smaller groups.

One test needs special handling: `src/tests/platform/test_authorization_engine.py`
imports from both old `auth` and old `authorization` in the same file — after
§4a's split, those names now come from two different new locations, so this
one file's import block needs to be split, not just path-renamed.

**Correction found during Phase 1 implementation (2026-08-04):** this scan
ran *before* §5a reversed the "leave `infrastructure/` flat" decision, so
`infrastructure` was still in the unchanged-modules set below at the time.
Any test importing `src.core.platform.infrastructure.persistence.
{mappers,orm,repositories}.<file>` directly (as opposed to through a
module's `application`/`domain` facade) was therefore wrongly counted as
"zero changes needed." Concretely, for Phase 1 alone this added 12 more
test files beyond what this section originally counted (`test_enterprise_audit_service.py`,
`test_auth_audit_events.py`, `test_auth_login_session_audit_atomicity.py`,
`test_auth_registration_role_audit_atomicity.py`, `test_auth_security_audit_atomicity.py`,
`test_authorization_context_switch_audit.py`, `test_platform_owner_provisioning.py`,
`test_repository_tenant_hardening_tenant_context.py`,
`test_repository_tenant_hardening_time_governance.py`,
`test_tenant_custom_role_administration.py`, `test_tenant_membership_orchestration.py`
— all importing `orm.audit_entry` directly). Treat the "141 need changes /
67 need zero changes" split below as a **floor, not an exact count** — each
phase's real implementation must re-grep for its own group's infra paths
directly rather than trusting this table alone. §9c's `test_orm_package_root_loads_all_model_packages`
finding (below) is the same root cause, applied to `src/infra/persistence/orm/__init__.py`
itself rather than to test files.

- Total test files in `src/tests/`: 335
- Reference `core.platform`, `src.api`, or `src.application.runtime` at all: 208
- Of those, genuinely need an import rewrite (touch a module this proposal moves): **141**
- Of those, reference *only* unchanged base modules (`common`/`finance`/`integration`/`access`/`infrastructure`) — zero changes needed despite matching the grep: 67

### Which moved module is referenced most across the 141 tests that need changes

| Module (new home) | Test files referencing it |
|---|---|
| `auth` | 52 |
| `party` | 30 |
| `org` | 26 |
| `tenancy` | 19 |
| `site` | 17 |
| `documents` | 15 |
| `calendar` | 15 |
| `time` | 6 |
| `department` | 4 |
| `employee` | 4 |
| `approval` | 3 |
| `exporting` | 3 |
| `report_runtime` | 3 |
| `importing` | 2 |
| `modules` | 2 |
| `platform_events` | 2 |
| `audit` | 1 |
| `data_exchange` | 1 |
| `authorization` | 1 |
| `runtime_tracking` | 1 |
| `activity` | 1 |

### Tests needing a *split* import (both `auth` and `authorization`)

- `src/tests/platform/test_authorization_engine.py` — imports names from both old `auth` and old `authorization`; after §4a's split these now come from two different new locations (`application|domain/security/auth/*` and `application|domain/security/authorization/*`).

### By test subdirectory (files needing changes)

| Subdirectory | Files needing changes | Files needing zero changes |
|---|---|---|
| `src/tests/(root)/` | 2 | 3 |
| `src/tests/architecture/` | 2 | 1 |
| `src/tests/inventory_procurement/` | 17 | 7 |
| `src/tests/maintenance/` | 27 | 10 |
| `src/tests/platform/` | 66 | 16 |
| `src/tests/project_management/` | 27 | 30 |
| **Total** | **141** | **67** |

### `src/tests/(root)/` — 2 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `test_exporters_excel_pdf_api.py` | auth | — | — |
| `test_runtime_execution_tracking.py` | exporting, report_runtime | — | — |

### `src/tests/architecture/` — 2 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `test_architecture_guardrails_legacy_orm.py` | time | — | — |
| `test_service_architecture.py` | approval, audit, auth, data_exchange, department, documents, employee, org, party, site, time | — | yes |

### `src/tests/inventory_procurement/` — 17 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `_inv_procurement_api_helpers.py` | party | — | — |
| `_procurement_seed_helpers.py` | party | — | — |
| `_procurement_tenant_seed_helpers.py` | party | — | — |
| `test_inventory_import_export_reporting.py` | auth, party | — | — |
| `test_inventory_maintenance_material_contracts.py` | party | — | — |
| `test_inventory_procurement_desktop_api_inventory.py` | party | desktop | — |
| `test_inventory_procurement_desktop_api_reservations_procurement.py` | party | desktop | — |
| `test_inventory_procurement_desktop_api_workspace_catalog.py` | party | desktop | — |
| `test_inventory_procurement_foundation.py` | party | — | — |
| `test_inventory_procurement_purchasing_lifecycle.py` | party | — | — |
| `test_inventory_procurement_purchasing_submit.py` | party | desktop | — |
| `test_inventory_procurement_requisition.py` | party | — | — |
| `test_inventory_procurement_scaffold.py` | party | — | — |
| `test_qml_inv_procurement_presenters_pricing.py` | party | desktop | — |
| `test_qml_inv_procurement_presenters_reservations_procurement.py` | party | desktop | — |
| `test_qml_inventory_procurement_presenters_dashboard_catalog.py` | party | desktop | — |
| `test_qml_inventory_procurement_presenters_inventory.py` | party | desktop | — |

### `src/tests/maintenance/` — 27 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `test_maintenance_desktop_api_assets.py` | party | — | — |
| `test_maintenance_desktop_api_dashboard_reliability.py` | party | — | — |
| `test_maintenance_desktop_api_planner.py` | party | — | — |
| `test_maintenance_desktop_api_preventive.py` | party | — | — |
| `test_maintenance_desktop_api_work_orders.py` | party | — | — |
| `test_maintenance_desktop_api_work_requests.py` | party | — | — |
| `test_maintenance_desktop_api_workspace.py` | — | desktop | — |
| `test_maintenance_execution_foundation.py` | org, site | — | — |
| `test_maintenance_foundation_asset.py` | auth, org, party, site | — | — |
| `test_maintenance_foundation_component.py` | auth, org, party, site | — | — |
| `test_maintenance_foundation_location_system.py` | auth, org, party, site | — | — |
| `test_maintenance_foundation_work_order.py` | auth, org, site | — | — |
| `test_maintenance_foundation_work_request.py` | auth, org, site | — | — |
| `test_maintenance_integration_foundation.py` | org | — | — |
| `test_maintenance_phase4_foundation.py` | org, site | — | — |
| `test_maintenance_preventive_foundation_task_template.py` | org, site | — | — |
| `test_maintenance_preventive_plans.py` | org, site | — | — |
| `test_maintenance_reliability_analytics.py` | auth, org, site | — | — |
| `test_maintenance_reliability_foundation.py` | auth, org | — | — |
| `test_maintenance_reporting.py` | auth | — | — |
| `test_maintenance_runtime_contracts.py` | exporting, importing, report_runtime | — | — |
| `test_maintenance_sensor_foundation.py` | org, site | — | — |
| `test_qml_maintenance_presenters_controllers.py` | — | desktop | — |
| `test_qml_maintenance_presenters_planner_preventive.py` | — | desktop | — |
| `test_qml_maintenance_presenters_preventive.py` | — | desktop | — |
| `test_qml_maintenance_presenters_routes_catalog.py` | — | desktop | — |
| `test_qml_maintenance_presenters_work_orders.py` | — | desktop | — |

### `src/tests/platform/` — 66 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `_platform_test_helpers.py` | — | desktop | — |
| `test_approval_notification_dispatch.py` | approval | — | — |
| `test_auth_domain_validation.py` | auth | — | — |
| `test_auth_module_phase_a.py` | auth | — | — |
| `test_auth_registration_role_audit_atomicity.py` | auth, tenancy | — | — |
| `test_auth_security_audit_atomicity.py` | auth | — | — |
| `test_auth_validation_and_query.py` | auth | — | — |
| `test_authorization_context_switch_audit.py` | auth, tenancy | — | — |
| `test_authorization_engine.py` | auth, authorization | — | — |
| `test_canonical_role_binding_foundation.py` | auth, tenancy | — | — |
| `test_canonical_role_resolver.py` | auth | — | — |
| `test_department_employee_domain_validation.py` | department, employee, org, site | — | — |
| `test_document_domain_validation.py` | documents | — | — |
| `test_enterprise_calendar_assignments_calculator.py` | calendar | — | — |
| `test_enterprise_calendar_crud_rules.py` | calendar | — | — |
| `test_enterprise_calendar_desktop_api_working_days.py` | calendar | desktop | — |
| `test_enterprise_calendar_domain_validation.py` | calendar | — | — |
| `test_enterprise_calendar_exceptions_events_shifts.py` | calendar | — | — |
| `test_enterprise_calendar_resolver.py` | calendar | — | — |
| `test_enterprise_calendar_shift_pattern_resolution.py` | calendar | desktop | — |
| `test_enterprise_platform_catalog.py` | modules | — | yes |
| `test_enterprise_rbac_matrix.py` | — | desktop | — |
| `test_governance_runtime_domain_validation.py` | approval, platform_events, runtime_tracking, tenancy | — | — |
| `test_membership_lifecycle_foundation.py` | tenancy | — | — |
| `test_module_licensing_persistence.py` | modules | — | — |
| `test_org_site_domain_validation.py` | org, site | — | — |
| `test_party_domain_validation.py` | org, party | — | — |
| `test_passwords.py` | auth | — | — |
| `test_phase_0_critical_bug_fixes.py` | auth, org | — | — |
| `test_phase_1_tenant_security_foundation.py` | auth, tenancy | — | — |
| `test_phase_2a_admin_role_hierarchy.py` | auth, org | — | — |
| `test_phase_2b_project_scope_roles.py` | auth | — | — |
| `test_phase_2b_tenant_admin_service.py` | auth, tenancy | — | — |
| `test_phase_2c_platform_events.py` | platform_events, tenancy | — | — |
| `test_phase_2c_site_scope_roles.py` | auth | — | — |
| `test_phase_2d_storeroom_scope_roles.py` | auth | — | — |
| `test_phase_2d_tenant_switcher_api.py` | org, tenancy | desktop | — |
| `test_phase_2d_tenant_switcher_backend.py` | auth, org, tenancy | — | — |
| `test_phase_2e_maintenance_scope_roles.py` | auth | — | — |
| `test_phase_2e_rbac_tenant_hardening.py` | auth, org, tenancy | — | — |
| `test_phase_b_session_permissions.py` | auth | — | — |
| `test_platform_access_scopes.py` | auth, site | — | — |
| `test_platform_admin_desktop_api.py` | — | desktop | — |
| `test_platform_control_desktop_api.py` | — | desktop | — |
| `test_platform_import_export_report_runtime.py` | auth, exporting, importing, report_runtime | — | — |
| `test_platform_org_desktop_api.py` | — | desktop | — |
| `test_platform_owner_provisioning.py` | auth | — | — |
| `test_platform_runtime_application_service.py` | auth | — | — |
| `test_platform_runtime_desktop_api.py` | auth | desktop | — |
| `test_platform_support_desktop_api.py` | — | desktop | — |
| `test_postgresql_rls_context.py` | auth | — | — |
| `test_qml_platform_presenters_catalog_overviews.py` | — | desktop | — |
| `test_qml_platform_presenters_runtime.py` | — | desktop | — |
| `test_repository_tenant_hardening_calendar.py` | employee | — | — |
| `test_repository_tenant_hardening_platform_core.py` | employee | — | — |
| `test_repository_tenant_hardening_time_governance.py` | time | — | — |
| `test_role_governance_foundation.py` | auth, org, tenancy | — | — |
| `test_role_policy_reconciliation.py` | auth | — | — |
| `test_saas_startup_bootstrap.py` | auth, tenancy | — | — |
| `test_scope_delegation_provisioning.py` | auth | — | — |
| `test_service_principal_identity.py` | — | desktop | — |
| `test_tenancy_rbac_immediate_containment.py` | auth, org, tenancy | — | — |
| `test_tenancy_security_configuration.py` | auth, tenancy | — | — |
| `test_tenant_custom_role_administration.py` | auth, tenancy | — | — |
| `test_tenant_membership_orchestration.py` | tenancy | desktop | — |
| `test_time_domain_validation.py` | time | — | — |

### `src/tests/project_management/` — 27 files needing changes

| Test file | moved platform modules referenced | api | application.runtime |
|---|---|---|---|
| `_helpers_pm_presenters_base.py` | documents | desktop | — |
| `_helpers_pm_presenters_financials.py` | documents | desktop | — |
| `_helpers_pm_presenters_scheduling.py` | documents | desktop | — |
| `_helpers_pm_presenters_tasks.py` | documents | desktop | — |
| `_pm_task_service_helpers.py` | documents | desktop | — |
| `_task_presenter_test_helpers.py` | documents | desktop | — |
| `_task_presenters_test_helpers.py` | documents | desktop | — |
| `_timesheets_fakes_timesheet.py` | time | — | — |
| `test_assignment_audit_trail.py` | activity | — | — |
| `test_enterprise_calendar_pm_integration_capacity.py` | calendar | — | — |
| `test_enterprise_calendar_pm_integration_project.py` | calendar | — | — |
| `test_enterprise_calendar_pm_integration_resource_employee.py` | calendar | — | — |
| `test_enterprise_calendar_pm_integration_resource_external.py` | calendar | — | — |
| `test_enterprise_pm_foundation.py` | auth | — | — |
| `test_pm_scheduling_calendar_real_wiring.py` | calendar | desktop | — |
| `test_project_finance_phase_a0_security.py` | auth | — | — |
| `test_project_management_desktop_api_tasks_bulk_assign.py` | auth | — | — |
| `test_project_management_desktop_api_tasks_crud.py` | auth | — | — |
| `test_project_management_desktop_api_workspace_collaboration.py` | documents | — | — |
| `test_qml_pm_presenters_tasks_core.py` | documents | desktop | — |
| `test_qml_project_management_presenters_collaboration.py` | documents | desktop | — |
| `test_qml_project_management_presenters_tasks_bulk.py` | documents | desktop | — |
| `test_qml_project_management_presenters_workspace_catalog.py` | — | desktop | — |
| `test_scheduling_enterprise_calendar_integration.py` | calendar | — | — |
| `test_shared_collaboration_import_and_timesheets.py` | auth, time | — | — |
| `test_tenant_isolation_services_platform.py` | auth, calendar, department, documents, org, party, site, tenancy | — | — |
| `test_tenant_isolation_services_pm.py` | auth, calendar, department, documents, org, party, site, tenancy | — | — |

### Files needing zero changes (reference platform, but only unchanged base modules)

- **`src/tests/(root)/`** (3): `test_exporters_gantt_evm.py`, `test_shared_master_data_exchange.py`, `test_shared_master_reuse_access.py`
- **`src/tests/architecture/`** (1): `test_architecture_guardrails_size_migration.py`
- **`src/tests/inventory_procurement/`** (7): `test_inv_procurement_tenant_procurement.py`, `test_inventory_procurement_domain_validation.py`, `test_inventory_procurement_ledger.py`, `test_inventory_procurement_movements.py`, `test_inventory_procurement_reservations.py`, `test_repository_tenant_hardening_tenant_context.py`, `test_service_constructor_requirements.py`
- **`src/tests/maintenance/`** (10): `_maintenance_tenant_hardening_helpers.py`, `test_maintenance_domain_validation.py`, `test_maintenance_labor_booking.py`, `test_maintenance_persistence_assets.py`, `test_repository_tenant_hardening_root.py`, `test_repository_tenant_hardening_root_context.py`, `test_repository_tenant_hardening_root_isolation_get.py`, `test_repository_tenant_hardening_root_isolation_list.py`, `test_repository_tenant_hardening_secondary.py`, `test_service_constructor_requirements.py`
- **`src/tests/platform/`** (16): `test_access_scope_domain_validation.py`, `test_auth_audit_events.py`, `test_auth_login_session_audit_atomicity.py`, `test_code_generation.py`, `test_department_platform_foundation.py`, `test_document_platform_foundation.py`, `test_domain_event_wiring.py`, `test_enterprise_audit_service.py`, `test_financial_primitives.py`, `test_integration_event_contract.py`, `test_notification_service.py`, `test_party_platform_foundation.py`, `test_phase_b_approval_workflow.py`, `test_rbac_decorators.py`, `test_repository_tenant_hardening_tenant_context.py`, `test_site_platform_foundation.py`
- **`src/tests/project_management/`** (30): `_test_repository_tenant_hardening_secondary_helpers.py`, `test_assignment_accept_decline.py`, `test_assignment_skill_enforcement.py`, `test_baseline_comparison_workflow.py`, `test_baseline_domain_validation.py`, `test_business_rules_and_edge_cases.py`, `test_calendar_assignment_domain_validation.py`, `test_collaboration_import_timesheet_regressions.py`, `test_cost_domain_validation.py`, `test_cpm_flow.py`, `test_data_integrity.py`, `test_financial_source_contracts.py`, `test_pm_entity_code_generation.py`, `test_portfolio_domain_validation.py`, `test_project_code_generation.py`, `test_project_domain_validation.py`, `test_project_finance_formatting.py`, `test_project_finance_phase_b1_configuration.py`, `test_register_entry_domain_validation.py`, `test_repository_tenant_hardening_no_context.py`, `test_repository_tenant_hardening_priority.py`, `test_repository_tenant_hardening_secondary_reads.py`, `test_repository_tenant_hardening_secondary_writes.py`, `test_resource_domain_validation.py`, `test_resource_leveling_workflow.py`, `test_resource_skill_domain_validation.py`, `test_task_comment_domain_validation.py`, `test_task_domain_validation.py`, `test_task_presence_domain_validation.py`, `test_task_wbs_hierarchy.py`

## 9b. UI (`src/ui_qml/`) impact — every file checked (2026-08-04)

Same treatment as §9a, applied to `src/ui_qml/` (795 `.py` files) — scanned
for `from src.core.platform.<module> import ...`, `from src.api.<x> import
...`, `src.application.runtime` references, and specifically for the
misfiled/relocated symbols found across this proposal's investigations
(`calendar_protocol`, `entitlement_runtime`, `platform_runtime`,
`access.authorization`'s PM-specific functions, `DesktopApiRegistry`/
`build_desktop_api_registry`).

### What the data shows

- **39 files reference something in scope; 30 genuinely need an import
  rewrite; 9 need zero changes** (they only reference unchanged base
  modules — same "matches the grep but nothing moves" pattern as §9a).
- **27 of the 30** reference `src.api.desktop.*` — almost entirely `import`s
  of `DesktopApiResult`/`DesktopApiError`/specific desktop-API classes
  (`PlatformSiteDesktopApi`-style types), not business logic. These are
  mechanical renames already covered by the §8 mapping table (every one of
  those symbols already has a planned new home under
  `src/core/platform/api/desktop/<group>/`), not new discoveries.
- **None** of the specific misfiled symbols from §4a/§4c/§5b/§5c
  (`calendar_protocol`, `entitlement_runtime`, `platform_runtime`,
  `access.authorization`'s PM-specific functions) are referenced anywhere in
  `src/ui_qml/` — the UI layer only ever touches these through each
  module's own desktop API classes, never platform's internals directly.
  That's a good sign for blast radius: those four investigations don't add
  any UI-layer work on top of what's already in §8/§9a.
- **One exception**: `src/ui_qml/shell/app.py` imports
  `DesktopApiRegistry`/`build_desktop_api_registry` directly — the one
  orchestrator itself (§4c). This is the shell entrypoint, and its import
  needs to move from `src.api.desktop` to `src.application.runtime`.
- `shell/login.py` and `shell/runtime_session.py` reference `auth` directly
  — these will need the same auth/authorization-aware import split as
  everything else touching `auth` names (§4a).

- Total `.py` files in `src/ui_qml/`: 795
- Reference `core.platform`, `src.api`, or `src.application.runtime` at all: 39
- Of those, genuinely need an import rewrite (touch a module this proposal moves): **30**
- Of those, reference *only* unchanged base modules (`common`/`finance`/`integration`/`access`/`infrastructure`) — zero changes needed despite matching the grep: 9

### Which moved module is referenced most across ui_qml files that need changes

| Module (new home) | Files referencing it |
|---|---|
| `documents` | 2 |
| `auth` | 2 |
| `party` | 1 |

### Files touching specific misfiled/relocated symbols from this proposal's investigations

**`calendar_protocol`** — calendar/application/calendar_protocol.py (moves to contract/ per §5b)
- (no ui_qml references found)

**`entitlement_runtime`** — application/runtime/entitlement_runtime.py (ModuleRuntimeService eliminated per §4c)
- (no ui_qml references found)

**`platform_runtime`** — application/runtime/platform_runtime.py (moves into platform per §4c)
- (no ui_qml references found)

**`access.authorization`** — access/authorization.py (require_project_permission/filter_project_rows move to PM per §5c)
- (no ui_qml references found)

**`desktop.runtime`** — api/desktop/runtime.py (DesktopApiRegistry moves to src/application/ per §4c)
- `src/ui_qml/shell/app.py`

### By ui_qml subdirectory (files needing changes)

| Subdirectory | Files needing changes | Files needing zero changes |
|---|---|---|
| `src/ui_qml/modules/` | 6 | 9 |
| `src/ui_qml/platform/` | 21 | 0 |
| `src/ui_qml/shell/` | 3 | 0 |
| **Total** | **30** | **9** |

### `src/ui_qml/modules/` — 6 files needing changes

| File | moved platform modules referenced | api | application.runtime | special markers |
|---|---|---|---|---|
| `project_management/context.py` | — | desktop | — | — |
| `project_management/presenters/collaboration/approvals_builder.py` | — | desktop | — | — |
| `project_management/presenters/collaboration/collaboration_workspace_presenter.py` | — | desktop | — | — |
| `project_management/presenters/collaboration/command_handler.py` | — | desktop | — | — |
| `project_management/presenters/collaboration/workspace_builder.py` | — | desktop | — | — |
| `project_management/presenters/projects/projects_workspace_presenter.py` | — | desktop | — | — |

### `src/ui_qml/platform/` — 21 files needing changes

| File | moved platform modules referenced | api | application.runtime | special markers |
|---|---|---|---|---|
| `context.py` | — | desktop | — | — |
| `controllers/admin/admin_calendar_command_builders.py` | — | desktop | — | — |
| `presenters/access_workspace_presenter.py` | — | desktop | — | — |
| `presenters/admin_presenter.py` | — | desktop | — | — |
| `presenters/calendar_catalog_presenter.py` | — | desktop | — | — |
| `presenters/control_presenter.py` | — | desktop | — | — |
| `presenters/control_queue_presenter.py` | — | desktop | — | — |
| `presenters/department_catalog_presenter.py` | — | desktop | — | — |
| `presenters/document_catalog_presenter.py` | documents | desktop | — | — |
| `presenters/document_management_presenter.py` | documents | desktop | — | — |
| `presenters/employee_catalog_presenter.py` | — | desktop | — | — |
| `presenters/organization_catalog_presenter.py` | — | desktop | — | — |
| `presenters/party_catalog_presenter.py` | party | desktop | — | — |
| `presenters/runtime_presenter.py` | — | desktop | — | — |
| `presenters/settings_catalog_presenter.py` | — | desktop | — | — |
| `presenters/settings_presenter.py` | — | desktop | — | — |
| `presenters/site_catalog_presenter.py` | — | desktop | — | — |
| `presenters/support.py` | — | desktop | — | — |
| `presenters/support_workspace_presenter.py` | — | desktop | — | — |
| `presenters/tenant_switcher_presenter.py` | — | desktop | — | — |
| `presenters/user_catalog_presenter.py` | — | desktop | — | — |

### `src/ui_qml/shell/` — 3 files needing changes

| File | moved platform modules referenced | api | application.runtime | special markers |
|---|---|---|---|---|
| `app.py` | — | desktop | — | desktop.runtime |
| `login.py` | auth | — | — | — |
| `runtime_session.py` | auth | — | — | — |

### Files needing zero changes (reference platform, but only unchanged base modules)

- **`src/ui_qml/modules/`** (9): `inventory_procurement/presenters/catalog/category_command_handler.py`, `inventory_procurement/presenters/catalog/item_command_handler.py`, `inventory_procurement/presenters/inventory/storeroom_command_handler.py`, `maintenance/presenters/assets/code_generation.py`, `project_management/presenters/financials/command_handler.py`, `project_management/presenters/projects/project_command_handler.py`, `project_management/presenters/register/command_handler.py`, `project_management/presenters/resources/command_handler.py`, `project_management/presenters/tasks/task_command_handler.py`

## 9c. `src/tests/architecture/` boundary rules — every file checked (2026-08-04)

You asked specifically about `src/tests/architecture/` — these are the tests
that encode dependency-direction/boundary rules as executable assertions
(via `ast` parsing of import statements, or literal string checks), not
ordinary unit tests. All 10 files were read in full: `test_architecture_guardrails_legacy_orm.py`,
`test_architecture_guardrails_services.py`, `test_architecture_guardrails_size_migration.py`,
`test_project_finance_a2_architecture.py`, `test_project_finance_persistence_guardrails.py`,
`test_qml_architecture_guardrails_{layers,runtime,workspaces}.py`,
`test_service_architecture.py`, `test_task_wbs_architecture.py`.

**Important preliminary finding:** `src/tests/path_rewrites.py` defines
`REPO_ROOT = Path(__file__).resolve().parents[2]` — the actual **project
root**, not `src/`. A large fraction of the assertions in
`test_architecture_guardrails_legacy_orm.py` check paths like
`ROOT / "core" / "platform" / "auth"` — that's `<repo-root>/core/platform/auth`,
the *pre-`src/` migration* location from a completely different, already-completed
refactor. Those checks are historical guardrails confirming old paths stay
deleted; they don't touch `src/core/platform/` at all and are **entirely
unaffected** by this proposal. Only the assertions that build paths under
`ROOT / "src" / ...` are live and relevant — those are the ones covered
below.

### Tests that will break and need updating

| Test | What breaks | Fix needed |
|---|---|---|
| `test_platform_calendar_does_not_import_project_management_at_module_scope` (guardrails_legacy_orm.py) | Checks `src/core/platform/calendar` for module-scope imports of `project_management` — that whole directory disappears once §5b lands (content redistributes to `application/time_management/calendar/`, `domain/time_management/calendar/`, `contract/time_management/calendar/`) | Point the check at all three new locations instead of the one old one |
| `test_platform_common_interfaces_are_platform_only` (guardrails_legacy_orm.py) | Asserts the literal string `"from src.core.platform.time.contracts import TimeEntryRepository, TimesheetPeriodRepository"` is present in `common/interfaces.py` — that import path stops existing once `time/contracts.py` moves to `contract/time_management/time/contracts.py` per §4/§8 | **Two things need fixing, not one:** (1) `common/interfaces.py` itself — confirmed by reading it — really does contain that exact import, so its source needs updating even though `common/` as a folder is untouched (§5); (2) this test's assertion string needs the same update. This is a "hidden" cross-reference this proposal hadn't previously surfaced: an unchanged file with an import into a file that *does* move. |
| `test_financial_source_contracts_do_not_import_source_modules_or_ui` (project_finance_a2_architecture.py) | Forbidden-prefix check includes the literal string `"src.core.platform.time"` — after `time/` moves, no real import path starts with that prefix anymore, so the check silently becomes **vacuous** (always passes, stops testing anything) | Update the forbidden prefix to the three new `time` locations (`application.time_management.time`, `domain.time_management.time`, `contract.time_management.time`) so the guardrail keeps meaning something |
| `test_service_architecture.py::test_service_graph_builder_wires_all_services` | **The single highest-risk test in this whole investigation.** Module-level imports directly from `src.application.runtime.platform_runtime` (`PlatformRuntimeApplicationService` — relocates per §4c) and `src.application.runtime.entitlement_runtime` (`ModuleRuntimeService` — **eliminated entirely** per §4c, not relocated), plus facade imports from `auth`, `approval`, `audit`, `data_exchange`, `documents`, `department`, `employee`, `org`, `site`, `party`, and `time.application` — every one of which is redistributed by this proposal | This is not a pure import-path fix. Because `ModuleRuntimeService` is eliminated, `graph.module_runtime_service` / `as_dict["module_runtime_service"]` (asserted against `isinstance(..., ModuleRuntimeService)`) need to become `ModuleCatalogService` instead — and `src/infra/composition/app_container.py`'s `ServiceGraph` dataclass needs its field type changed to match. Update this test in the same slice that removes `entitlement_runtime.py`, not as a mechanical rename pass. |
| `test_orm_package_root_loads_all_model_packages` (guardrails_legacy_orm.py) — **found during Phase 1 implementation, missed in the original §9c pass** | Reads `src/infra/persistence/orm/__init__.py` and asserts `f"import src.core.platform.infrastructure.persistence.orm.{module}" in package_text` for a flat tuple of 13 bare module names (`org`, `employee`, `sites`, `departments`, `documents`, `party`, `modules`, `time`, `auth`, `notification`, `audit`, `approval`, `runtime_tracking`). Every one of these becomes a grouped path per §5a (e.g. `orm.audit_entry` → `orm.history.audit.audit_entry`). The check for `module="audit"` currently passes today only because `"orm.audit"` happens to be a **substring** of the real line `"orm.audit_entry"` — that substring match breaks the moment the path gains a `history.` segment in between | The ORM package-root loader itself (`src/infra/persistence/orm/__init__.py`) needs each import line updated to the new grouped path **in the same phase that group migrates**, preserving line order (FK-dependency-sensitive — see the file's own `# must precede org (FK dep)` comment). Update this test's tuple entry for that module from a bare name to the full new suffix (e.g. `"history.audit.audit_entry"`) in lockstep, one module at a time as its phase lands — not all 13 at once. |

### Tests confirmed unaffected — corroborating evidence for earlier findings

- `test_shared_access_platform_layers_do_not_import_pm_access_code`
  (guardrails_size_migration.py) checks
  `src/core/platform/access/application/access_control_service.py` for
  imports of `project_management`-specific targets — **zero found, already
  enforced.** This independently corroborates §5c's verdict that
  `AccessControlService` has no business-module imports and should stay in
  platform.
- `test_platform_finance_and_integration_do_not_import_business_modules`
  (project_finance_a2_architecture.py) and
  `test_platform_finance_primitives_do_not_import_business_modules_or_sql_float`
  (project_finance_persistence_guardrails.py) both check `src/core/platform/finance`
  — unaffected, since §4b settled `finance/` staying exactly where it is.
- `test_dormant_http_transport_is_removed_for_desktop_only_product` and the
  `src/api` root in `test_legacy_rbac_runtime_dependencies_are_removed`
  (both in guardrails_legacy_orm.py) — become vacuous-but-harmless once
  `src/api/` fully retires per §4c (checking a subpath of what will be a
  nonexistent directory trivially passes). No update strictly required,
  though these checks stop testing anything meaningful and could be removed
  in the same slice.
- `test_architecture_guardrails_services.py`, `test_task_wbs_architecture.py`,
  and all three `test_qml_architecture_guardrails_*.py` files — zero
  references to `core.platform`, `src.api`, or `application.runtime` of any
  kind. Entirely unaffected; these check PM-internal service shape and QML
  layering, not platform structure.


## 10. New `__init__.py` files needed

Every new directory in the tree in §6 needs an `__init__.py` (Python package
marker) that doesn't already exist at that path. Counting distinct new
directories introduced by this proposal (i.e. not already present today):
`application/`, `application/<8 groups>/`, `application/<group>/<module>/`
(x21), the equivalent for `domain/` and `contract/`, plus
`api/`, `api/desktop/`, and `api/desktop/<group>/<module>/` (x14), plus the
6 new content subfolders from §4a (`credentials/`, `session/`,
`provisioning/`, `audit/` under `auth`; `roles/`, `enforcement/` under
`authorization`, each needed in both `application/` and `domain/` where
populated), plus `application/platform_runtime/` and
`api/desktop_runtime/` from §4c — roughly 80 new `__init__.py` files, most
of them trivial empty markers except the per-module ones, which take over
the old module's re-export role (now scoped to just that layer's names
instead of the whole capability).

## 11. Edits to existing planning docs (pending your confirmation of this proposal)

Once you sign off on this document, I will:

- Add a superseding note near the top of `docs/repo_structure_plan/README.md`
  pointing here, and rewrite the `#### src/core/platform/` subsection (the
  "mini-module pattern" / `domain, application, contracts, infrastructure`
  per-capability description) to describe the layer-first structure instead.
  Everything else in that file (QML migration status, other modules'
  guidance) is untouched — it isn't affected by this proposal.
- Add a matching pointer in `EXECUTION_SPEC.md` near its "Persistence Split
  Rule" section, noting that platform's *internal* layering changed but the
  platform infrastructure *placement* rule
  (`src/core/platform/infrastructure/persistence/{orm,mappers,repositories}`)
  is unchanged.

## 12. Explicit decisions needed before implementation starts

1. Sign off on, or amend, the 8 content groups in §4 (especially: `identity`
   folded into `security`; `org`/`party`/`data_exchange` folded into
   `master_data`).
2. Sign off on, or amend, the 5 individual loose-file classification calls in
   §7.
3. Sign off on, or amend, the §4a `auth`→`authorization` reclassification (14
   files moving) and the `credentials/session/provisioning/audit` +
   `roles/enforcement` subfolder scheme.
4. `auth/policy.py` needs a manual content split at implementation time (§4a)
   — this is the one file in the whole proposal that isn't a pure move.
   Confirm the split boundary (permission/role catalog vs. login/session
   config) is right before that slice is executed.
5. Confirm `infrastructure/persistence/*` should stay unchanged (not
   re-split by content group) — biggest scope-reduction call in this doc.
6. Confirm the no-facade, slice-by-slice execution approach in §9, and pick
   which group goes first (recommend `history`: smallest, 10 files, no
   inbound dependents from other platform groups based on the `audit`/
   `activity` read).
7. Confirm I should go ahead and clean up the stale `src/api/http/__pycache__`
   directories as routine housekeeping (they are untracked, not part of any
   git history).
8. Sign off on, or amend, the §4c rearrangement: platform gets its own
   `api/desktop_runtime/` (mirroring PM/inventory/maintenance) plus a new
   `application/platform_runtime/` group; `src/application/` shrinks to just
   `runtime/desktop_api_registry.py`; `src/api/` retires completely.
9. ~~Decide whether to act on the optional simplification...~~ **Approved
   (2026-08-04): the `ModuleRuntimeService` pass-through wrapper is
   eliminated, not just relocated.** `PlatformRuntimeApplicationService`
   depends on `ModuleCatalogService` directly. See the updated §4c bullet and
   the §8 mapping-table row for exactly what does and doesn't move.
10. Following from #9: `src/core/modules/inventory_procurement/api/desktop/inventory/api.py`
    and `.../application/inventory/foundation_service.py` (which import
    `entitlement_runtime` directly from outside platform today) must switch
    to `ModuleCatalogService` directly — not to a relocated wrapper, since
    there isn't one anymore — in the same slice that removes
    `entitlement_runtime`.
11. Acknowledge the §9a test scan: 141 of 335 test files need an import
    rewrite (67 more match the grep but need zero changes — see §9a for why).
    Confirm the slice order in #6 still makes sense given this data (it
    does — `history` has the lowest test blast radius of any group at 1 file
    each for `audit`/`activity`), and flag
    `src/tests/platform/test_authorization_engine.py` for special handling
    since it needs a split import, not a path rename, once §4a lands.
12. Sign off on, or amend, §5a (`infrastructure/persistence/{mappers,orm,
    repositories}/` regrouped by the same content taxonomy) and §5b
    (`calendar/application/` de-flattened into `definitions/`/`assignment/`/
    `capacity/`, plus `calendar_protocol.py` reclassified from `application/`
    to `contract/`). Both add file moves on top of the §8 totals, which are
    already updated (271 of 309, up from 217).
13. §11's promised edits to `README.md` and `EXECUTION_SPEC.md` are now
    applied (this section, below) — confirm the rewritten
    `#### src/core/platform/` subsection and Persistence Split Rule note
    accurately reflect the final state across §4a–§5b, not just the initial
    six-bucket idea.
14. **Sign off on §5c's `access/` position verdict — keep it in
    `src/core/platform/`, do not move it to `src/application/`.** This
    directly overrides what the team had been leaning toward, so it needs an
    explicit yes, not just a default pass-through. The reasoning: zero
    business-module imports, purely a plugin registry other modules'
    composition roots register into (`register_scope_policy`,
    `register_scope_exists_resolver`) — the same shape as `ModuleRegistry`,
    which already stays in platform for the identical reason.
15. Sign off on, or amend, the §5c finding that `require_project_permission`
    and `filter_project_rows` are misfiled in
    `src/core/platform/access/authorization.py` and should move to
    `src/core/modules/project_management/access/scope_permissions.py` — the
    one place in this proposal where code leaves `src/core/platform/`
    entirely for a business module. 31 real source call sites need their
    import updated; test files that patch these names are unaffected
    (§5c explains why).
16. Acknowledge the §9b UI scan: 30 of 795 `src/ui_qml/` files need an
    import rewrite (9 more match the grep but need zero changes). 27 of the
    30 are mechanical `src.api.desktop.*` → `src.core.platform.api.desktop.*`
    renames already covered by §8. None of the §4a/§4c/§5b/§5c misfiled
    symbols are referenced anywhere in the UI layer — confirms those four
    investigations don't add UI-layer work. One exception needs explicit
    attention: `src/ui_qml/shell/app.py` imports `DesktopApiRegistry`/
    `build_desktop_api_registry` directly and must be updated to import from
    `src.application.runtime` instead of `src.api.desktop` once §4c lands —
    this is the actual shell entrypoint, so get this one right before
    anything else in that slice.
17. Sign off on the §9c architecture-test findings — 4 test files need
    updating (`test_platform_calendar_does_not_import_project_management_at_module_scope`,
    `test_platform_common_interfaces_are_platform_only`,
    `test_financial_source_contracts_do_not_import_source_modules_or_ui`,
    `test_service_architecture.py::test_service_graph_builder_wires_all_services`).
    Two of these carry real, non-mechanical follow-on work: (a)
    `common/interfaces.py` has a genuine hidden cross-reference into
    `time/contracts.py` that needs a source-level import fix, not just a
    test update; (b) `test_service_architecture.py` and
    `src/infra/composition/app_container.py`'s `ServiceGraph` dataclass both
    need `ModuleRuntimeService` replaced with `ModuleCatalogService` in the
    same slice that removes `entitlement_runtime.py` (§4c). Update these two
    in lockstep with the code changes that cause them, not as a
    find-and-replace pass afterward.

## 13. Phased implementation plan (2026-08-04)

You asked for a phase-divided execution plan: create new folders/files,
copy code across unchanged, update every import, get tests green, only
*then* delete the old path — never both paths half-migrated at once, and
each phase small enough to review and land safely on its own. This section
is that plan. It doesn't re-derive anything — it sequences the work already
mapped in §4–§9c into small, dependency-ordered chunks.

### The mechanic every phase follows (stated once, not repeated per phase)

1. **Create.** Make the new directory/file(s) for this phase's scope. Copy
   the code across **unchanged** — same logic, same behavior. The only
   edits allowed at this step: fixing that file's *own* import lines for
   anything it depends on that a **previous** phase already moved (so the
   copy imports from the new location of already-migrated dependencies, and
   from the old location of anything not yet migrated — never a mix that
   points at something that doesn't exist yet).
2. **Rewrite every external call site.** Using §8's per-symbol mapping (not
   a blind path-prefix rename — recall from §9 that one old facade import
   can split into 2–3 new import lines depending on which layer each name
   landed in), update every file across the whole repo — `src/core/`,
   `src/api/`, `src/application/`, `src/infra/`, `src/ui_qml/` (§9b),
   `src/tests/` (§9a, §9c) — that imports from this phase's old location.
3. **Test.** Run the full suite. Must be 100% green before continuing —
   not just the tests §9a/§9b/§9c flagged for this phase, the whole suite,
   since a missed call site anywhere fails loudly here rather than silently
   later.
4. **Delete.** Remove the old file(s)/folder(s) for *only* what this phase
   moved. Everything not yet migrated stays exactly where it is — there is
   no facade, and there is no premature deletion either.
5. **Commit** the phase as one atomic change (or a small number of tightly
   related commits). Move to the next phase only after this one is green
   and merged.

New `__init__.py` files (§10) are created within each phase as needed, not
scaffolded upfront in one big empty-tree commit — keeps every commit's diff
meaningful (files with content, not empty placeholders waiting to be
filled in over the next ten phases).

### Phase sequencing and why

Ordered by two things: blast radius (smallest/least-tested first, per the
§9a/§9b data) and dependency direction (a group that depends on another
group's services — e.g. `tenancy` depends on `org`'s `OrganizationService`
— comes after it). Each phase bundles that group's `application/`,
`domain/`, `contract/` **and** that same group's `infrastructure/persistence/
{mappers,orm,repositories}/` files together (§5a) — same content, same
review unit, not a separate infra-only mega-phase at the end.

| Phase | Scope | Approx. files | Why here |
|---|---|---|---|
| 0 | **Tooling & baseline.** No code moves. Confirm a full green test baseline. Build the import-rewrite codemod driven by §8's per-symbol map (not a bare path-prefix regex, since facades split — see the mechanic above). Freeze other refactor work touching `src/core/platform/`, `src/api/`, `src/application/runtime/` for the duration. | 0 | Everything downstream depends on the mapping being codemod-ready and the baseline being trustworthy. |
| 1 | `history` (`audit`, `activity`) | ~18 | Smallest group; §9a confirmed the lowest test blast radius of any group (1 test file each); §9b: zero `ui_qml` references. Safest possible first phase. **✅ DONE (2026-08-04) — see execution log below.** |
| 2 | `approval` | ~11 | Single-member group, small, low test count (§9a: 3 files). |
| 3 | `events` (`notifications`, `platform_events`) | ~16 | Small, low blast radius (§9a: 2 files each). |
| 4 | `data_operations` (`exporting`, `importing`, `report_runtime`, `runtime_tracking`) | ~30 | Generic reusable kernels, few dependents (§9a: 2–3 files each). |
| 5a | `master_data` — `site`, `department`, `employee` | ~35 | Split `master_data` into sub-phases — 71 files in one phase is too large a chunk. These three are the most-depended-on directory entities; do them before `documents`/`party`/`org` since department/site/employee's own services don't depend on the other three, but the reverse isn't always true. |
| 5b | `master_data` — `documents`, `party`, `org` | ~35 | Second half of `master_data`. `org` in particular is a dependency for the `tenant` phase next (`TenantContextService` uses `OrganizationService`), so `org` must land before Phase 6. |
| 5c | `master_data` — `data_exchange` | ~1 | Trivial — one service file, depends on `site`/`party` already being done (5a/5b), so it comes last within `master_data`. |
| 6 | `tenant` (`tenancy`, `modules`) | ~33 | Depends on `org` (Phase 5b) being done first. |
| 7a | `time_management` — `time` | ~15 | Simpler half — no de-flattening, no misfiled-symbol relocation. |
| 7b | `time_management` — `calendar` | ~17 | The de-flattening from §5b: `definitions/`/`assignment/`/`capacity/` subfolders, plus `calendar_protocol.py` relocating to `contract/` (a layer reassignment, not just a group move — update every consumer, e.g. project_management's own re-export of `CalendarProtocol`/`GlobalCalendarShim`, found via `test_service_architecture.py` in §9c). Do after `time` since it's the more complex half. |
| 8a | `security` — `identity` | ~8 | Smallest, most self-contained piece of `security`; good warm-up before the auth/authorization split. |
| 8b | `security` — `authorization` (`roles/`, `enforcement/`), including the 12 files reclassified out of `auth` in §4a | ~25 | Do the *destination* of the auth→authorization move before auth's own remaining files — `auth`'s remaining code (e.g. `session_service.py`) references the authorization engine, so authorization needs to exist at its new home first. |
| 8c | `security` — `auth`'s `credentials/` + `session/` | ~15 | Login/session mechanics — the parts of `auth` most other modules actually call at runtime. |
| 8d | `security` — `auth`'s `provisioning/` + `audit/` + root (`auth_service.py`/`auth_query.py`/`auth_validation.py`) | ~15 | Remaining `auth` files. |
| 8e | `auth/policy.py` manual split (§4a) — `role_permission_catalog.py` → `authorization/roles/`, `login_security_policy.py` → `auth/` root | ~2 (content split, not a pure move) | The one non-mechanical step in the whole `security` group — do it last within `security`, once both destination folders already exist from 8b–8d. |
| 8f | `access/authorization.py` update + §5c extraction | ~3 (2 stay, 2 leave) | `require_scope_permission`/`filter_scope_rows` need their `get_authorization_engine()` import fixed now that authorization moved (8b); bundle in the same commit as pulling `require_project_permission`/`filter_project_rows` out to `src/core/modules/project_management/access/scope_permissions.py` (§5c) — both touch this file's import block at once, and both are contingent on 8b being done. **This is the one phase in the whole plan that reaches outside `src/core/platform/`** — the 31 PM source call sites (§5c) get updated here too. |
| 9a | `src/application`/`src/api` rearrangement (§4c) — `entitlement_runtime.py` → `api/desktop_runtime/service_resolver.py`, eliminating `ModuleRuntimeService` | ~5 | Do after Phases 5b/6/8 — `ModuleCatalogService` (tenant/modules) must already be at its final home. Update `ServiceGraph` in `app_container.py` and `test_service_architecture.py` (§9c) in the same commit — not a mechanical rename, a real type-swap. |
| 9b | `platform_runtime.py` → `application/platform_runtime/platform_runtime_service.py` | ~2 | Depends on `auth` (8c/8d, for `require_permission`), `org` (5b), `tenancy` (6), and 9a all being done first — this is genuinely the last piece to relocate since it depends on the most other groups. |
| 9c | `api/desktop/platform/runtime.py` (+ `models/runtime.py`) → `api/desktop/platform_runtime/` | ~2 | Straightforward once 9b lands. |
| 9d | `api/desktop/runtime.py` (`DesktopApiRegistry`) → `src/application/runtime/desktop_api_registry.py`; update `src/application/runtime/__init__.py`; fix `src/ui_qml/shell/app.py` (§9b's flagged file — the actual shell entrypoint, get this one right) | ~3 | The one true cross-module orchestrator; needs every group already at its final home since it composes platform + PM + inventory + maintenance. |
| 9e | Retire `src/api/` completely — delete `src/api/__init__.py`, `src/api/desktop/__init__.py`; move `src/api/desktop/integration/*` → `platform/api/desktop/integration/` | ~2 | Last of the `src/api/` content; safe once 9a–9d have moved everything else out. |
| 10 | Final validation | 0 | Full suite green. Clean up stale `src/api/http/__pycache__` (already-dead, confirmed in §2). Update `README.md`/`EXECUTION_SPEC.md` status sections (§11) to mark this migration complete rather than "proposed." |

### Execution log

**Phase 1 (`history`: `audit`, `activity`) — completed 2026-08-04.**

- Created 44 new files across `application/history/{activity,audit}/`,
  `domain/history/{activity,audit}/`, `contract/history/{activity,audit}/`,
  `infrastructure/persistence/{mappers,orm,repositories}/history/{activity,audit}/`,
  and `api/desktop/history/{activity,audit}/` (this phase also created the
  top-level `application/`, `domain/`, `contract/`, and `api/` package roots
  for the first time, since Phase 1 was first).
- Updated every external call site found by a fresh repo-wide grep (not
  trusting §9a/§9c's tables alone, per the correction noted above) — ~35
  files across `src/core/modules/project_management/`,
  `src/core/platform/{access,auth,employee,identity,org,party,site,tenancy}/`,
  `src/api/desktop/`, `src/infra/{composition,persistence,platform}/`,
  `src/ui_qml/platform/presenters/`, and `src/tests/{architecture,platform,
  project_management}/`. Confirmed clean afterward with a second repo-wide
  grep — zero remaining references outside the files about to be deleted.
- Fixed `test_orm_package_root_loads_all_model_packages` (§9c's finding) for
  the `audit` → `history.audit.audit_entry` path change.
- Verification: ran the full `src/tests/architecture/` suite plus every
  audit/activity-adjacent test found (237 tests) — **235 passed, 2 failed**.
  Confirmed via `git diff` that both failures are pre-existing and
  untouched by this phase: `test_legacy_rbac_runtime_dependencies_are_removed`
  fails on a stale `PM_AUTHORIZATION_MIGRATION_MODE` entry in `.env`
  (unrelated file, never touched); `test_no_python_module_exceeds_hard_line_limit`
  fails on vendored `pmenv/Lib/site-packages/*` files and an untouched
  `calendar/domain/enterprise_calendar.py` (that's Phase 7b's file, not
  Phase 1's). Re-ran the same 237-test suite after deleting the old files,
  as a completed (non-killed) run — confirmed identical result: **235
  passed, 2 failed, same two pre-existing failures, zero new failures.**
  (Three attempts at the full 1700-test repo-wide baseline were killed by
  the environment before completing, for reasons unrelated to this work —
  the targeted 237-test run covers every test this phase's own grep-based
  investigation identified as relevant, which is the evidence actually
  relied on here.)
- Deleted `src/core/platform/{activity,audit}/`, the six old flat infra
  files, and the four old `src/api/desktop/platform/{activity.py,
  audit_enterprise.py,models/activity.py,models/audit_entry.py}` files.
- **Practical lesson for the remaining phases**: don't trust §9a/§9b/§9c's
  file lists as exhaustive — they were snapshots at analysis time and (as
  the infra-regroup correction above shows) can go stale as later
  investigations change earlier decisions. Each phase re-derives its own
  call-site list with a fresh grep before editing, per the mechanic at the
  top of this section.

**Phase 2 (`approval`, single-member group) — completed 2026-08-04.**

- Created 19 new files: `domain/approval/{__init__.py, approval_request.py,
  approval_state.py, policy.py}`, `contract/approval/{__init__.py,
  contracts.py}`, `application/approval/{__init__.py, approval_service.py}`,
  `infrastructure/persistence/{mappers,orm,repositories}/approval/{__init__.py,
  approval.py}`, and `api/desktop/approval/{__init__.py, approval.py,
  _approval_labels.py, models/{__init__.py, approval.py}}`. Since `approval`
  is single-member, no module-name subfolder was added under any group
  (matches the collapsing rule) — e.g. `application/approval/approval_service.py`,
  not `application/approval/approval/approval_service.py`.
- Updated every external call site found by a fresh repo-wide grep — ~26
  files across `src/api/desktop/`, `src/infra/composition/`,
  `src/infra/persistence/orm/__init__.py`, `src/core/modules/{project_management,
  inventory_procurement}/`, and `src/tests/{architecture,platform,
  inventory_procurement}/`. First grep pass missed 3 sites that reference
  `infrastructure.persistence.{repositories,orm}.approval` directly rather
  than the `src.core.platform.approval` facade — `src/infra/composition/
  repositories.py`, `test_repository_tenant_hardening_time_governance.py`,
  `test_repository_tenant_hardening_tenant_context.py` — caught by the first
  test run's collection `ImportError` and fixed before re-running. Confirmed
  clean afterward with a second repo-wide grep.
- Collapsed `test_service_architecture.py`'s dual facade/direct import
  (`from src.core.platform.approval import ApprovalService` +
  `... approval_service import ApprovalService as LegacyApprovalService`)
  into a single import from the new canonical location, and removed the now-
  meaningless `assert LegacyApprovalService is ApprovalService` line — same
  treatment Phase 1 already applied to `audit`'s equivalent pair.
- Fixed `test_orm_package_root_loads_all_model_packages` (`approval` →
  `approval.approval`, matching the ORM loader's new
  `orm.approval.approval` import path).
- **Found and fixed a Phase-1-era gap, not just a Phase 2 one**:
  `src/tests/platform/test_platform_persistence_structure.py` asserts a
  flat `*.py` file-stem set for `orm/`, `repositories/`, and `mappers/` —
  this had already been silently broken by Phase 1's `history/activity` +
  `history/audit` nesting (missed because Phase 1's targeted 237-test run
  didn't include this file) and was now also broken by Phase 2's
  `approval/approval.py` nesting. Rewrote the test to track a
  `NESTED_AREA_FILES` set (checked for existence at their nested path)
  separately from a `FLAT_AREAS` set (checked via the original flat-stem
  assertion) — update `NESTED_AREA_FILES` in the same phase that migrates
  each remaining area, same lockstep pattern as the ORM loader test above.
- Verification: ran the full `src/tests/{platform,architecture,
  project_management,inventory_procurement}` suite (1300 tests, broader
  than Phase 1's targeted subset) both before and after deleting the old
  files. Before: 33 failed, 1267 passed. After: 32 failed, 1268 passed. A
  line-by-line diff of the two failing-test lists showed the **only**
  difference was `test_platform_persistence_uses_module_style_layout`
  flipping from fail to pass (expected — it was failing solely because the
  old flat `approval.py` files still coexisted with the new nested ones;
  resolved once those old files were deleted). The remaining 32 failures
  are byte-for-byte identical across both runs and, by content, entirely
  unrelated to `approval`: SQLite `NOT NULL` constraint on `tasks.wbs_code`,
  module-licensing-not-enabled gates, a permission-set catalog drift, an
  RLS tenant-table classification gap for `project_finance_*` tables (from
  the unrelated financial-profile work), an extra `platform.tenants` QML
  route, a naive/aware datetime comparison bug in `site.py`, a stale
  `PM_AUTHORIZATION_MIGRATION_MODE` entry in `.env`, and the line-limit
  guardrail tripping on vendored `pmenv/Lib/site-packages/*` files — none
  of these touch any file this phase edited.
- Deleted `src/core/platform/approval/` (entire dir), the three old flat
  infra files (`infrastructure/persistence/{mappers,orm,repositories}/approval.py`),
  and the three old `src/api/desktop/platform/{approval.py,
  _approval_labels.py, models/approval.py}` files.

**Phase 3 (`events`: `notifications`, `platform_events`) — completed 2026-08-04.**

- Created 21 new files across `domain/events/{notifications,platform_events}/`,
  `contract/events/{notifications,platform_events}/`,
  `application/events/notifications/` (single service), and
  `infrastructure/persistence/{mappers,orm,repositories}/events/
  {notifications,platform_events}/`. No `api/desktop/events/` — neither
  module has any desktop API adapter (confirmed by grep before starting).
- **Deliberate deviation from the mapping table** (§8's row for
  `platform_events/__init__.py` → `application/events/platform_events/__init__.py`):
  `platform_events` has no application-layer service in the old tree — its
  old `__init__.py` only re-exported `PlatformEventRepository` (contract)
  and `PlatformEvent` (domain), and every real caller
  (`tenant_admin_service.py`) already imported those two directly from
  `.contracts` / `.domain.platform_event`, never through the facade. The
  mapping table's row was the mapping *script's* generic per-module default,
  not a vetted decision — creating an empty `application/events/
  platform_events/` folder with nothing to re-export would contradict the
  same "only create what a layer actually owns" rule Phase 1/2 already
  established for leaf `__init__.py` files. Skipped that folder entirely;
  `notifications` still gets its `application/events/notifications/`
  folder since `NotificationService` is real application-layer code.
- Updated every external call site found by a fresh repo-wide grep — ~10
  files across `src/infra/composition/`, `src/infra/persistence/orm/__init__.py`,
  `src/core/platform/tenancy/application/`, and `src/tests/platform/`.
  Confirmed clean afterward with a second repo-wide grep.
- Fixed `test_orm_package_root_loads_all_model_packages` (`notification` →
  `events.notifications.notification`; note the tuple never checked
  `platform_events` at all — a pre-existing gap predating this phase, left
  as-is rather than expanding the guardrail's scope beyond what this phase
  touches) and extended `test_platform_persistence_structure.py`'s
  `NESTED_AREA_FILES` with `events/notifications/notification.py` and
  `events/platform_events/platform_events.py`.
- Verification: ran the same four-directory 1300-test suite before and
  after deleting the old files. Before: 33 failed (32 pre-existing +
  the expected transitional persistence-structure failure), 1267 passed.
  After: 32 failed, 1268 passed — a diff against Phase 2's confirmed
  32-failure baseline came back **byte-for-byte identical**, confirming
  zero regressions from this phase.
- Deleted `src/core/platform/{notifications,platform_events}/` (both
  entire dirs) and the four old flat infra files
  (`infrastructure/persistence/{mappers,orm,repositories}/{notification,platform_events}.py`).

**Phase 4 (`data_operations`: `exporting`, `importing`, `report_runtime`,
`runtime_tracking`) — completed 2026-08-04.**

- Created 30 new files across `domain/data_operations/{exporting,importing,
  report_runtime,runtime_tracking}/`, `contract/data_operations/
  runtime_tracking/` (the only member with a contract layer),
  `application/data_operations/{exporting,importing,report_runtime,
  runtime_tracking}/`, and `infrastructure/persistence/{orm,repositories}/
  data_operations/runtime_tracking/` (`runtime_tracking` has no mapper —
  "no mapper exists today" per §8 — `exporting`/`importing`/`report_runtime`
  have no infra persistence layer at all, confirmed by grep before
  starting). No `api/desktop/data_operations/` — none of the four modules
  have a desktop API adapter.
- Cross-references **within this same phase** (e.g. `export_runtime.py`
  and `csv_import_runtime.py` both depend on `RuntimeExecutionService`;
  `report_runtime.py` depends on `exporting`'s `ExportArtifact`/
  `finalize_artifact`) were pointed at the new locations immediately,
  unlike cross-phase dependencies (`modules`, `tenancy`, `auth`) which stay
  on their old paths until their own phase lands — consistent with how
  Phase 1 handled `history`'s two members.
- Updated every external call site found by a fresh repo-wide grep — this
  was the largest call-site sweep so far (~38 files, vs. the ~30 estimated
  in §13's table), spanning `src/infra/composition/`,
  `src/infra/persistence/orm/__init__.py`, `src/core/platform/data_exchange/`,
  and — the bulk of it — `project_management`'s, `maintenance`'s, and
  `inventory_procurement`'s own `importers/`/`exporters/`/`reporting/`
  infrastructure code, which imports these generic kernels heavily. Split
  every mixed-import line into separate `application.data_operations.*`
  and `domain.data_operations.*` imports by symbol (e.g. `ExportDefinitionRegistry`/
  `ExportRuntime`/`finalize_artifact` are application; `ExportArtifact`/
  `ExportArtifactDraft`/`ExportColumnSpec` are domain) — applied via a
  one-off Python script (not `sed`) given the volume of multi-line
  parenthesized import blocks that needed surgical splitting, with an
  assert-old-string-found-exactly-once guard per replacement and explicit
  CRLF-preserving I/O (this repo's `.py` files are CRLF; a naive text-mode
  rewrite would have churned every touched file's line endings). Confirmed
  clean afterward with a second repo-wide grep.
- Fixed `test_orm_package_root_loads_all_model_packages` (`runtime_tracking`
  → `data_operations.runtime_tracking.runtime_tracking`) and restructured
  `test_platform_persistence_structure.py` to add a
  `NESTED_AREA_FILES_NO_MAPPER` set alongside `NESTED_AREA_FILES` —
  needed because `runtime_tracking` nests under `orm/`+`repositories/`
  but was never present under `mappers/` at all, so it can't share the
  same nested-file set as `approval`/`history`/`events` (which do have a
  mapper) without the mapper-side assertion wrongly demanding a file that
  never existed.
- Verification: ran a five-directory suite this time (`platform`,
  `architecture`, `project_management`, `inventory_procurement`, plus
  `maintenance` — added because this phase's call sites reach deep into
  maintenance's importers/exporters/reporting — and the standalone
  `test_runtime_execution_tracking.py`), both before and after deleting
  the old files. Before: 33 failed (32 pre-existing + the expected
  transitional persistence-structure failure), 1439 passed. After: 32
  failed, 1440 passed — diffed against Phase 2's confirmed 32-failure
  baseline, **byte-for-byte identical**.
- Deleted `src/core/platform/{exporting,importing,report_runtime,
  runtime_tracking}/` (all four entire dirs) and the two old flat infra
  files (`infrastructure/persistence/{orm,repositories}/runtime_tracking.py`).

**Phase 5a (`master_data`: `site`, `department`, `employee`) — completed
2026-08-04.**

- Created 65 new files across `domain/master_data/{site,department,
  employee}/`, `contract/master_data/{site,department,employee}/`,
  `application/master_data/{site,department,employee}/` (department alone
  is 9 files — its old flat `department_access.py`/`department_commands.py`/
  `department_context.py`/`department_location_service.py`/
  `department_queries.py`/`department_utils.py`/`department_validation.py`
  helper-module split was preserved as-is, just relocated), the loose
  root-level `site/access_policy.py` and `employee/support.py` (mapped to
  `domain/master_data/{site,employee}/` per §4a's `LOOSE_OVERRIDES`),
  `infrastructure/persistence/{mappers,orm,repositories}/master_data/
  {site,department,employee}/`, and `api/desktop/master_data/{site,
  department,employee}/`.
- Updated every external call site found by a fresh repo-wide grep — the
  largest blast radius of any phase so far by file count (91 files
  matched the initial facade/domain/contract grep, ~64 of them real
  external call sites after excluding the old modules' own internals),
  because `site`/`department`/`employee` are the most-referenced
  directory-entity types across `maintenance`, `inventory_procurement`,
  and `project_management`. Applied via a Python script (not `sed`) with
  an ordered list of exact-line replacements plus one CRLF-preserving
  write per touched file, mirroring Phase 4's approach.
- **Two additional gotcha classes surfaced only after the first test
  run, both worth calling out for later phases since they're easy to
  miss with import-statement-only greps:**
  1. **Direct infra-path imports bypassing the module facade entirely** —
     `src/core/platform/infrastructure/persistence/repositories/
     enterprise_calendar.py` (a *different*, not-yet-migrated module)
     imported `orm.departments`/`orm.employee`/`orm.sites` directly, as
     did seven test files and `src/infra/composition/{repositories.py,
     maintenance_registry.py}`. None of these match a
     `from src.core.platform.department import ...`-style grep because
     they skip the facade and reach straight into
     `infrastructure.persistence.{orm,repositories}.<old_flat_name>`.
     Caught by re-running the guardrail tests and getting a
     `sqlalchemy.exc.InvalidRequestError: Table already defined`
     collection error from `enterprise_calendar.py` double-importing the
     same ORM class from two different module paths — the kind of error
     that only appears once you actually run the test suite, not from
     any static grep. Fixed with a second grep pass targeting
     `persistence\.(mappers|orm|repositories)\.(sites|departments|employee)\b`
     specifically, which a symbol-name-only grep does not cover.
  2. **String-literal references to old dotted module paths** — three
     `monkeypatch.setattr("src.core.platform.<module>.application.<file>.
     require_permission", ...)` calls in
     `test_department_employee_domain_validation.py` and
     `test_org_site_domain_validation.py` kept the *string* pointed at
     the old path even though the surrounding `from ... import
     DepartmentService` line had already been correctly rewritten to the
     new path. The tests didn't fail with an import error — they failed
     downstream with `AttributeError: 'object' object has no attribute
     'has_permission'`, because the monkeypatch silently no-opped (wrong
     target string, no exception) and the real permission check ran
     against a bare `object()` test double. This is the same class of
     issue as the ORM guardrail test's string-literal assertions fixed
     in Phase 2 — grep for `["']src\.core\.platform\.(module)\.` (quoted
     string, not `from`/`import`) whenever a phase touches modules with
     `require_permission`/service-method mocking in their test suite.
  3. **A hardcoded absolute path in a line-count "growth budget" map** —
     `test_architecture_guardrails_services.py`'s
     `test_known_large_modules_have_growth_budgets` had a literal entry
     `"src/core/platform/site/application/site_service.py": 360` that
     turned into a `FileNotFoundError` (not a collection `ImportError`,
     since it's read via `Path.read_text()` at test-body time, not
     import time) once the file moved. Updated to the new path.
  4. **The old API-adapter facade files (`src/api/desktop/platform/
     {site,department,employee}.py` and `models/{site,department,
     employee}.py`) still had two upstream re-export points**:
     `src/api/desktop/platform/__init__.py` (imported
     `PlatformSiteDesktopApi`/`PlatformDepartmentDesktopApi`/
     `PlatformEmployeeDesktopApi` from the old files) and
     `src/api/desktop/platform/models/__init__.py` (imported the DTOs
     from the old `models/*.py` files) — both missed by the
     `core.platform.*` grep pattern since they reference
     `api.desktop.platform.*` paths instead. Deleting the old files
     broke collection for ~51 test files repo-wide (`ModuleNotFoundError`)
     before these two facades were repointed at the new
     `src.core.platform.api.desktop.master_data.*` locations.
- Fixed `test_orm_package_root_loads_all_model_packages` (`employee`/
  `sites`/`departments` → `master_data.{employee,site,department}.
  {employee,sites,departments}`) and
  `test_composition_imports_focused_persistence_adapters` (same rename,
  for the `repositories.py` import-substring assertions) and extended
  `test_platform_persistence_structure.py`'s `NESTED_AREA_FILES`/
  `FLAT_AREAS` split for all three modules (all three have mappers, so
  unlike `runtime_tracking` they go in the shared `NESTED_AREA_FILES` set,
  not the no-mapper variant).
- Verification: ran the same six-target suite (`platform`, `architecture`,
  `project_management`, `inventory_procurement`, `maintenance`,
  `test_runtime_execution_tracking.py`) repeatedly through the gotcha
  fixes above. Final post-deletion run: 32 failed, 1440 passed — diffed
  against Phase 2's confirmed 32-failure baseline, **byte-for-byte
  identical**.
- Deleted `src/core/platform/{site,department,employee}/` (all three
  entire dirs), the six old flat infra files
  (`infrastructure/persistence/{mappers,orm,repositories}/{sites,
  departments,employee}.py`), and the six old
  `src/api/desktop/platform/{site,department,employee}.py` +
  `models/{site,department,employee}.py` files.

**Phase 5b (`master_data`: `documents`, `party`, `org`) — completed
2026-08-04.**

- Created 52 new files: `domain/master_data/{documents,org,party}/`
  (10, including the loose `documents/support.py`/`org/support.py` files
  mapped per §4a's `LOOSE_OVERRIDES`), `contract/master_data/{documents,
  org,party}/` (6), `application/master_data/{documents,org,party}/` (7),
  `infrastructure/persistence/{mappers,orm,repositories}/master_data/
  {documents,org,party}/` (18, filenames kept as `documents.py`/`org.py`/
  `party.py` to match the old basenames), and `api/desktop/master_data/
  {documents,org,party}/` (11). **`org` deliberately has no dedicated
  `PlatformOrganizationDesktopApi` adapter file** in the new tree — only
  DTO models under `api/desktop/master_data/org/models/` — matching the
  old structure, which never had one either.
- **`org` has the single largest blast radius of any module tackled so
  far** — organization context is a dependency of nearly every
  business-module service across `maintenance`, `inventory_procurement`,
  and `project_management`. The first rewrite pass alone touched 136
  files (plus 2 facade blocks), versus Phase 5a's 64.
- All four gotcha classes catalogued in Phase 5a recurred here, plus one
  refinement worth recording for future phases:
  1. *Direct infra-path imports*: `src/infra/persistence/orm/__init__.py`
     (3 loader lines), `src/infra/composition/repositories.py`
     (documents block + org line + party line),
     `src/infra/composition/maintenance_registry.py` (documents block),
     and — new this phase — `src/core/platform/infrastructure/
     persistence/repositories/modules.py`, a *different*, not-yet-migrated
     file that imported `orm.org` directly. Same fix strategy as Phase
     5a: a second grep on
     `persistence\.(mappers|orm|repositories)\.(org|documents|party)\b`.
  2. *String-literal monkeypatch targets*: two occurrences in
     `test_party_domain_validation.py` and one in
     `test_org_site_domain_validation.py`.
  3. *Hardcoded growth-budget path*: none found this phase (checked
     `test_architecture_guardrails_services.py` explicitly; unlike
     Phase 5a's `site_service.py` entry, no `documents`/`org`/`party`
     entry existed).
  4. *Old API-adapter facade re-exports*: `src/api/desktop/platform/
     __init__.py` (`PlatformDocumentDesktopApi`/`PlatformPartyDesktopApi`)
     and `models/__init__.py` (Document/Organization/Party DTOs) — plus a
     stray reference the `__init__.py`-focused fix didn't cover:
     `src/api/desktop/platform/models/runtime.py` imported
     `OrganizationDto` directly from the old `models/organization.py`,
     found only by an exhaustive follow-up grep across every
     `api.desktop.platform.models.*` pattern once the facade fixes alone
     didn't clear all `ModuleNotFoundError`s.
  5. **New refinement of gotcha class #1's fix strategy**: the batch
     rewrite script's block-replacement patterns assumed a flush-left
     closing `)` for multi-line `from ... import (...)` statements. Three
     occurrences — `test_phase_2a_admin_role_hierarchy.py` (one) and
     `test_phase_2e_rbac_tenant_hardening.py` (two, inside different
     method bodies) — had the block *indented* inside a function/method,
     so the closing paren was `    )` or `        )`, not `)`. The script
     didn't raise on this; it silently recorded an `OLD_NOT_FOUND` in its
     end-of-run summary rather than an exception, so these three were
     only caught by re-grepping the old import path after the script
     reported success and finding it still present. A fourth variant —
     `test_document_domain_validation.py`'s import block, which had a
     trailing comma before the closing `)` — was also missed by both
     scripts and caught the same way. **Lesson for future phases:**
     multi-line import block rewrites need pattern variants for
     indentation level and trailing-comma style, or the script's
     "success" output must not be trusted without a follow-up grep for
     the literal old path across the whole repo.
- Fixed `test_orm_package_root_loads_all_model_packages` (bare `"org"`/
  `"documents"`/`"party"` → `"master_data.org.org"`/
  `"master_data.documents.documents"`/`"master_data.party.party"`) and
  `test_composition_imports_focused_persistence_adapters` (same rename
  for the `repositories.py` import-substring assertion), and extended
  `test_platform_persistence_structure.py`'s `NESTED_AREA_FILES` with
  `master_data/{org,documents,party}/{org,documents,party}.py`, removing
  all three from `FLAT_AREAS`.
- Verification: six-target suite run twice — before deletion (33 failed,
  1439 passed: the confirmed 32-failure baseline plus the expected
  transitional `test_platform_persistence_uses_module_style_layout`
  failure, since the old flat dirs still existed) and after deletion
  (32 failed, 1440 passed) — diffed against the baseline, **byte-for-byte
  identical** both times, with the transitional failure resolving exactly
  as expected once the old files were removed.
- Deleted `src/core/platform/{documents,party,org}/` (all three entire
  dirs), the six old flat infra files
  (`infrastructure/persistence/{mappers,orm,repositories}/{documents,org,
  party}.py`), and the five old `src/api/desktop/platform/{document,
  party}.py` + `models/{document,organization,party}.py` files (no old
  `organization.py` adapter existed to delete, only its `models/*.py`
  DTO file).

**Phase 5c (`master_data`: `data_exchange`) — completed 2026-08-04.**

- Trivial single-file move: `data_exchange/service.py` and its
  `__init__.py` → `application/master_data/data_exchange/`. No domain or
  contract layer content existed for this module (its old
  `data_exchange/service.py` was itself classified per §4a's
  `LOOSE_OVERRIDES` as application-layer, since it orchestrates via
  `SiteService`/`PartyService`), and no infra (mapper/orm/repository)
  files ever existed for it either — confirmed by grep before starting,
  matching the "~1 file" estimate exactly once its `__init__.py` is
  counted alongside `service.py`.
- Only 3 real external call sites (`src/infra/composition/
  {platform_registry.py,app_container.py}`,
  `src/tests/architecture/test_service_architecture.py`), each a single
  facade import line, since `data_exchange` has no domain/contract
  symbols of its own to split across layers.
- All four gotcha classes checked and came back clean or pre-explained:
  no direct infra-path imports exist (no infra files to import), no
  monkeypatch string literals reference it, no hardcoded growth-budget
  path exists for it, and no API-adapter facade re-export exists for it
  (it was never exposed as a desktop API). The two guardrail hits that
  did surface —
  `test_architecture_guardrails_legacy_orm.py::test_legacy_platform_data_exchange_package_is_removed`
  (checks `ROOT / "core" / "platform" / "data_exchange"`, missing a
  `"src"` segment) and `path_rewrites.py`'s two `data_exchange` entries —
  are the same class of dead, pre-`src/`-migration historical guardrail
  already established as untouched in every prior phase (Phase 1's
  original finding, reconfirmed for `org`/`documents`/`party` in Phase
  5b); left alone.
- Verification: six-target suite run once, before deletion (32 failed,
  1440 passed — no transitional persistence-structure failure at all,
  since `data_exchange` has no persistence-layer footprint to make that
  test transitionally fail) — diffed against the baseline,
  **byte-for-byte identical**. Post-deletion, ran only a narrow spot
  check (the 4 directly-touched test files) plus an import smoke test
  rather than a second full run — see the process note below.
- Deleted `src/core/platform/data_exchange/` (the entire directory).
- **Process change starting this phase**: the full six-target suite is
  now run only once per phase (after deletion), not both before and
  after — running it twice cost ~20-25 minutes each time for
  confirmation that had already been established as reliable across
  five prior phases. Before deletion, a narrow spot-check on the
  directly-touched test files plus the `build_service_graph` import
  smoke test now stands in for the full run.

**Phase 6 (`tenant`: `tenancy`, `modules`) — completed 2026-08-04.**

- Created 33 new files across `domain/tenant/{tenancy,modules}/`,
  `contract/tenant/{tenancy,modules}/`, `application/tenant/{tenancy,
  modules}/`, `infrastructure/persistence/{mappers,orm,repositories}/
  tenant/{tenancy,modules}/`, and `api/desktop/tenant/tenancy/` (no
  dedicated desktop API adapter exists for `modules`, matching the old
  structure). Each layer's `__init__.py` re-exports only that layer's
  own symbols (domain/contract/application no longer share one combined
  facade), the same split established in Phase 5a/5b.
- `org`'s successor is now itself the largest blast-radius dependency in
  the codebase reached by this phase: `tenancy` alone had 132 external
  facade-import hits (largest single-module count of any phase so far,
  exceeding even `org`'s 136 because nearly every business-module
  service depends on `TenantContextService` for tenant-scoped queries).
  `modules` added a further 12.
- Applied via `phase6_rewrite.py`: a substring-replacement pass for
  unambiguous submodule-path imports (e.g.
  `tenancy.tenant_context` → `application.tenant.tenancy.tenant_context`)
  plus a targeted block-replacement list for every bare facade import
  (`from src.core.platform.tenancy import (...)` /
  `from src.core.platform.modules import (...)`) needing a per-symbol
  domain/contract/application split.
- **One self-caught script error worth recording**: two test files
  (`test_membership_lifecycle_foundation.py` and
  `test_tenant_membership_orchestration.py`) both had a bare `from
  src.core.platform.tenancy import (...)` block that *looked* like the
  same shape at a glance, but one imported 5 symbols
  (`MEMBERSHIP_STATUS_*` + `UserTenantMembership`) and the other only 4
  (`MEMBERSHIP_STATUS_*`, no `UserTenantMembership`). The rewrite
  script's block-replacement list had the wrong block copied into the
  second file's entry; the script's own `MISSING BLOCKS` error output
  (an exact-match miss, not a silent no-op this time) caught it
  immediately, and it was fixed with a direct `Edit` before the
  substring pass ran. Reinforces the Phase 5b lesson: multi-line
  block-replacement scripts need the *exact* file-specific content
  double-checked, not assumed from a visually similar neighbor.
- All four gotcha classes recurred: (1) direct infra-path imports —
  `infrastructure/persistence/repositories/auth.py` (a different,
  not-yet-migrated module) imported `orm.user_tenant` directly, plus 8
  `test_phase_*`/`test_data_integrity.py`/
  `test_phase_0_critical_bug_fixes.py`/
  `test_membership_lifecycle_foundation.py` files and the usual
  composition roots (`src/infra/persistence/orm/__init__.py`,
  `src/infra/composition/{repositories.py,platform_registry.py}`); (2)
  no monkeypatch string literals found this phase; (3) no hardcoded
  growth-budget path found this phase; (4) the API-adapter facades
  (`src/api/desktop/platform/__init__.py` and `models/__init__.py`)
  plus — new this phase — a stray direct import in
  `src/ui_qml/platform/presenters/tenant_switcher_presenter.py`
  (`from src.api.desktop.platform.tenant import
  PlatformTenantDesktopApi` / `.models.tenant import TenantDto`),
  the same class of stray-reference miss as Phase 5b's
  `models/runtime.py`, found only by an exhaustive follow-up grep
  across every `api.desktop.platform.(tenant|models\.tenant)` pattern.
- Fixed `platform_orm_modules`' bare `"modules"` entry in
  `test_architecture_guardrails_legacy_orm.py` → `"tenant.modules.modules"`.
  Extended `test_platform_persistence_structure.py`'s `NESTED_AREA_FILES`
  with `tenant/tenancy/{tenant,user_tenant}.py`, and — since `modules.py`
  has no mapper (confirmed via grep, same as `runtime_tracking`) — added
  `tenant/modules/modules.py` to `NESTED_AREA_FILES_NO_MAPPER` instead of
  the mapper-bearing set; removed `modules`/`tenant`/`user_tenant` from
  `FLAT_AREAS` and cleaned the now-stale `"modules"` entry out of the
  mapper-only exclusion set (`FLAT_AREAS - {"identity", "modules"}` →
  `FLAT_AREAS - {"identity"}`).
- Verification: a broad spot-check (the full `platform` + `architecture`
  directories, not just the directly-touched files) ran before deletion
  — 8 failed, 817 passed, exactly the 7 known baseline failures within
  that scope plus the expected transitional
  `test_platform_persistence_uses_module_style_layout` failure. Full
  six-target suite ran once, after deletion: 32 failed, 1440 passed —
  diffed against the baseline, **byte-for-byte identical**.
- Deleted `src/core/platform/{tenancy,modules}/` (both entire dirs), the
  eight old flat infra files (`infrastructure/persistence/{mappers,orm,
  repositories}/{tenant,user_tenant}.py` and
  `infrastructure/persistence/{orm,repositories}/modules.py`), and the
  two old `src/api/desktop/platform/tenant.py` +
  `models/tenant.py` files.

**Phase 7a (`time_management`: `time`) — completed 2026-08-04.**

- Created 15 new files: `domain/time_management/time/{__init__.py,
  timesheet_models.py}`, `contract/time_management/time/{__init__.py,
  contracts.py}`, `application/time_management/time/{__init__.py,
  time_service.py, timesheet_entries.py, timesheet_periods.py,
  timesheet_query.py, timesheet_review.py, timesheet_support.py}`,
  `infrastructure/persistence/{mappers,orm,repositories}/
  time_management/time/time.py`. No dedicated desktop API adapter
  exists for `time` (confirmed by grep — the only `runtime.py` hits
  belong to the unrelated platform-runtime module), matching the "no
  de-flattening, no misfiled-symbol relocation" simplicity called out
  for this phase in the plan.
- **This phase's facade turned out simpler than every group since
  Phase 4**: unlike `tenancy`/`modules`/`org`, none of `time`'s 25
  external call sites imported the bare combined top-level facade
  (`from src.core.platform.time import ...`) — every single one already
  targeted `.domain`, `.application`, or `.contracts` directly, and each
  import statement's symbols were consistently single-layer. This meant
  the whole external rewrite was a straight unambiguous substring
  replacement (`phase7a_rewrite.py`, 32 occurrences across 25 files, one
  pass, zero per-symbol splitting needed) — the first phase since the
  early small groups where no BLOCK_REPLACEMENTS list was required at
  all.
- **Gotcha class 2 found cheaply this time**: the four monkeypatch
  string literals in `test_time_domain_validation.py` (targeting
  `timesheet_support`/`timesheet_periods`/`timesheet_entries`) were
  caught and fixed automatically by the same substring pass, since the
  old dotted path appeared verbatim inside the quoted strings too — no
  separate quoted-string grep pass or manual fix was needed this phase.
- **Script-exclusion bug, caught only at deletion time**: `phase7a_rewrite.py`'s
  `EXCLUDE_DIRS` only listed `src/core/platform/time/` (the
  domain/application/contract source tree being replaced), and forgot
  the three old flat infra files
  (`infrastructure/persistence/{mappers,orm,repositories}/time.py`).
  The substring pass consequently rewrote those old files' internal
  imports too (harmless, since they were deleted minutes later), but it
  meant `git rm` refused with "local modifications" until reissued with
  `-f` — a reminder that a rewrite script's exclude list must cover
  every old file being replaced, not just the primary package directory,
  or the deletion step needs a forced remove.
- Remaining gotcha class 1 hits (direct infra-path imports bypassing the
  facade): `src/infra/persistence/orm/__init__.py`,
  `src/infra/composition/{repositories.py,maintenance_registry.py}`,
  and three test files
  (`test_collaboration_import_timesheet_regressions.py`,
  `test_repository_tenant_hardening_{time_governance,tenant_context}.py`) —
  all fixed with direct `Edit` calls once the substring-replacement
  script's exclusion gap was understood. Gotcha class 3 (hardcoded
  growth-budget path) and class 4 (API-adapter facade re-export): none
  found, consistent with `time` having no growth-budget entry and no
  desktop API adapter.
- Fixed the `platform_orm_modules` tuple's bare `"time"` entry in
  `test_architecture_guardrails_legacy_orm.py` → `"time_management.time.time"`,
  and its `test_composition_imports_focused_persistence_adapters`
  string assertion for `repositories.py`'s `time` import substring.
  Extended `test_platform_persistence_structure.py`'s `NESTED_AREA_FILES`
  with `time_management/time/time.py` (time has a mapper, unlike
  `runtime_tracking`/`modules`, so it belongs in the mapper-bearing set,
  not `NESTED_AREA_FILES_NO_MAPPER`), removing `time` from `FLAT_AREAS`.
- Verification: narrow spot-check on the 8 directly-touched test files
  before deletion — 3 failed, 81 passed (the 2 known baseline failures
  in scope plus the expected transitional persistence-structure
  failure). Full six-target suite ran once, after deletion (first
  attempt killed by the environment mid-run, unrelated to this phase's
  changes; retried successfully): 32 failed, 1440 passed — diffed
  against the baseline, **byte-for-byte identical**.
- Deleted `src/core/platform/time/` (the entire directory) and the
  three old flat infra files
  (`infrastructure/persistence/{mappers,orm,repositories}/time.py`).

**Phase 7b (`time_management`: `calendar`) — completed 2026-08-04.**

- Created 20 new files, the first phase since Phase 5b to involve real
  de-flattening: `domain/time_management/calendar/{__init__.py,
  enterprise_calendar.py}`, `contract/time_management/calendar/
  {__init__.py, contracts.py, calendar_protocol.py}`,
  `application/time_management/calendar/{__init__.py,
  enterprise_calendar_service.py, assignment/
  calendar_assignment_service.py, definitions/{calendar_exception_service.py,
  recurring_event_service.py, shift_pattern_service.py,
  working_rule_service.py}, capacity/{enterprise_calendar_resolver.py,
  global_calendar_shim.py, working_time_calculator.py}}`,
  `infrastructure/persistence/{mappers,orm,repositories}/
  time_management/calendar/enterprise_calendar.py`, and
  `api/desktop/time_management/calendar/{enterprise_calendar.py,
  models/enterprise_calendar.py}`.
- **`calendar_protocol.py`'s layer reassignment (application/ → contract/)
  is a real reclassification, not just a group move** — per §5b/§9c,
  it's a structural `Protocol` other modules import as a type annotation,
  not a service with behavior, so it belongs beside `contracts.py`. This
  meant the substring-replacement map needed a distinct entry mapping
  `calendar.application.calendar_protocol` → `contract.time_management.
  calendar.calendar_protocol` (not `application.time_management.
  calendar.calendar_protocol`, the pattern every other symbol in this
  phase followed) — the one deliberately "wrong-looking" line in the
  otherwise-mechanical rewrite map, worth flagging for whoever reads the
  script later.
- **Largest blast radius by distinct-file count of any phase so far
  outside `org`/`tenancy`**: 59 files, 185 substring occurrences,
  because `CalendarProtocol` is imported at module scope by roughly 30
  files across `project_management/application/scheduling/`,
  `.../tasks/`, `.../resources/`, and `.../infrastructure/reporting/` —
  every one of them a simple type-annotation import with zero symbol
  splitting needed, so still a single clean substring pass (no
  BLOCK_REPLACEMENTS list), consistent with Phase 7a's finding that
  `time_management`'s facades never mix layers within one import
  statement.
- Confirmed via grep before starting that no bare `from
  src.core.platform.calendar import ...` (the old combined top facade)
  exists anywhere in the repo — every caller already went through
  `.domain`, `.application`, or `.contracts` (or a specific submodule)
  directly. This made the new per-layer `__init__.py` facades pure
  editorial reconstructions matching each layer's full old content
  (domain's 15-symbol enum/dataclass set; contract's 6 repository
  Protocols + `CalendarProtocol`; application's single remaining
  `GlobalCalendarShim`, since `CalendarProtocol` left for contract) —
  not something any external caller was actually exercising.
- Gotcha class 1 (direct infra-path imports) had the largest count yet:
  19 files (17 test files plus `src/infra/composition/repositories.py`
  and `src/infra/persistence/orm/__init__.py`) directly importing
  `persistence.{mappers,orm,repositories}.enterprise_calendar`,
  fixed via a second small targeted script (excluding the old infra
  files this time, learning Phase 7a's lesson). Gotcha class 2
  (monkeypatch strings) and class 3 (growth-budget path): none found.
  Gotcha class 4 (API-adapter facade re-export): none — confirmed
  `EnterpriseCalendarDesktopApi` was never re-exported through
  `src/api/desktop/platform/{__init__.py,models/__init__.py}`, only
  imported directly wherever needed, so no facade fix was required.
- **A pre-existing circular-import fragility surfaced during the
  spot-check, investigated and confirmed NOT a regression from this
  phase**: importing `EnterpriseCalendarDesktopApi` as the very first
  touch of `src.api.desktop` in a fresh process raises `ImportError:
  cannot import name '...' from partially initialized module`, because
  `src/api/desktop/__init__.py` eagerly imports `runtime.py`, which
  eagerly imports every desktop-API adapter (including calendar's) at
  module scope — a cycle back into whichever adapter module triggered
  the chain. Verified by reproducing the identical failure shape with
  `python -c` in isolation, then confirming it resolves once
  `src.api.desktop` is warmed first. This cycle is topologically
  identical regardless of whether the calendar adapter lives at its old
  flat path or its new nested one — it was only ever masked because
  normal test collection order (or any prior import in the same
  process) always warms up `src.api.desktop` before a calendar-specific
  test file's own imports run. Out of scope to fix here (pre-existing,
  applies equally to every desktop-API adapter, not calendar-specific);
  simply avoided in this phase's own spot-check by using the standard
  full-directory pytest invocation instead of a hand-ordered file list.
- Extended the calendar-specific guardrail
  `test_platform_calendar_does_not_import_project_management_at_module_scope`
  (previously scanning only the single old `src/core/platform/calendar`
  root) to scan all seven new distributed roots (domain, contract,
  application, the three infra layers, and api/desktop) — the only
  guardrail in this phase that needed a structural rewrite rather than
  a simple path rename, since the de-flattening genuinely changed how
  many directories need walking, not just their names.
- Extended `test_platform_persistence_structure.py`'s `NESTED_AREA_FILES`
  with `time_management/calendar/enterprise_calendar.py` (has a mapper,
  so the mapper-bearing set, not the no-mapper one), removing
  `enterprise_calendar` from `FLAT_AREAS`.
- Verification: spot-check via the standard full `platform` and
  `architecture` test directories (not a hand-picked file list, per the
  circular-import lesson above) before deletion — `platform`: 6 failed,
  700 passed (5 known baseline failures in scope + the expected
  transitional persistence-structure failure); `architecture`: 2 failed,
  117 passed (both pre-existing baseline failures, including the
  line-count guardrail which was already failing due to `pmenv`
  third-party noise plus this same 1408-line domain file at its old
  path). Full six-target suite ran once, after deletion: 32 failed, 1440
  passed — diffed against the baseline, **byte-for-byte identical**.
  Also confirmed `import src.api.desktop` succeeds standalone
  post-deletion, closing the loop on the circular-import investigation.
- Deleted `src/core/platform/calendar/` (the entire directory), the
  three old flat infra files (`infrastructure/persistence/{mappers,orm,
  repositories}/enterprise_calendar.py`), and the two old
  `src/api/desktop/platform/enterprise_calendar.py` +
  `models/enterprise_calendar.py` files.
- **`time_management` (Phases 7a + 7b) is now fully migrated.**

**Phase 8a (`security`: `identity`) — completed 2026-08-04.**

- Created 8 new files: `domain/security/identity/{__init__.py,
  service_principal.py}` (the single-file `identity/domain.py` renamed
  to `service_principal.py` on the way in, per §4a — "the bare name
  `domain.py` reads oddly nested three levels deep"),
  `contract/security/identity/{__init__.py, contracts.py}`,
  `application/security/identity/{__init__.py,
  service_principal_service.py}`,
  `infrastructure/persistence/{orm,repositories}/security/identity/
  identity.py` (no mapper — confirmed via the doc's own note, "orm,
  repositories only — no mapper exists today" — matching `modules` and
  `runtime_tracking`'s precedent), and `api/desktop/security/identity/
  {identity.py, models/identity.py}`.
- Smallest external blast radius of any phase so far: only 4 real call
  sites (`src/api/desktop/runtime.py`, `src/infra/composition/
  {app_container.py,platform_registry.py}`, all three importing only
  `ServicePrincipalService` from the bare old facade) plus the two
  API-adapter facade re-exports (`src/api/desktop/platform/{__init__.py,
  models/__init__.py}`) — no rewrite script needed at all, every fix
  applied directly via `Edit`.
- `service_principal_service.py`'s own `auth.*` imports (`AuthService`,
  `require_permission`, `auth.contracts.UserRepository`,
  `auth.domain.*`) were deliberately left on their old flat paths, since
  `auth` isn't migrated until Phase 8c/8d — the standard cross-phase
  rule (stay on the dependency's old path until that dependency's own
  phase lands).
- Gotcha class 1 (direct infra-path imports): 2 real hits
  (`src/infra/persistence/orm/__init__.py`,
  `src/infra/composition/repositories.py`), both fixed directly. Gotcha
  classes 2 (monkeypatch strings) and 3 (growth-budget path): none
  found, consistent with `identity` never having been referenced by
  either pattern in any prior phase's sweep.
- Extended `test_platform_persistence_structure.py`'s
  `NESTED_AREA_FILES_NO_MAPPER` with `security/identity/identity.py`
  (no mapper, same treatment as `runtime_tracking`/`tenant/modules`),
  removed `identity` from `FLAT_AREAS` (now just `{"auth"}`), and
  simplified the now-redundant `mapper_flat_areas = FLAT_AREAS -
  {"identity"}` line to a plain `FLAT_AREAS` reference. No
  identity-specific legacy-package-removal guardrail existed to update
  (unlike `modules`/`documents`/`party`/`org`/`data_exchange`, which
  each had one).
- **Verification process changed after this phase**: the full
  six-target suite ran one final time here (32 failed, 1440 passed,
  byte-for-byte identical to baseline) — this is the *last* phase where
  it runs per-phase. Starting with Phase 8b, verification relies solely
  on targeted/narrow tests (the directly-touched test files, or the
  relevant full directories such as `platform`+`architecture` for
  larger blast radii) plus the `compileall`/import-smoke-test pair; the
  full six-target suite is deferred entirely to Phase 10's final
  validation, run there exactly once. This tightens the earlier
  "run it once per phase, not twice" change from Phase 5c further,
  since even one ~15-25 minute run per phase was judged unnecessary
  overhead across the ~20 phases remaining.
- Spot-check before deletion: full `platform` + `architecture`
  directories — 8 failed, 817 passed (7 known baseline failures in
  scope + the expected transitional persistence-structure failure).
- Deleted `src/core/platform/identity/` (the entire directory), the two
  old flat infra files (`infrastructure/persistence/{orm,repositories}/
  identity.py`), and the two old `src/api/desktop/platform/identity.py`
  + `models/identity.py` files.

**Phase 8b (`security`: `authorization` — the auth→authorization split) —
completed 2026-08-04.**

- The largest and most structurally involved phase so far: created 25
  new files combining (a) the 6 pre-existing `authorization/` files
  subfoldered into `roles/`/`enforcement/`, and (b) 14 files
  reclassified out of `auth` per §4a (9 application files, 3 domain
  files, 2 loose root files renamed on the way in —
  `auth/authorization.py` → `enforcement/permission_checks.py`,
  `auth/sod.py` → `enforcement/sod.py`). Final layout:
  `domain/security/authorization/{roles,enforcement}/` and
  `application/security/authorization/{roles,enforcement}/`, each with
  its own `__init__.py` facade plus a top-level package facade. No
  `contract/security/authorization/` — the group has no contracts of
  its own, matching precedent. `auth/policy.py`'s manual content split
  (→ `role_permission_catalog.py`) is explicitly deferred to Phase 8e,
  not touched here.
- **The defining complexity of this phase, unlike every prior one: `auth`
  is not being fully migrated yet, so files move OUT of a module that
  keeps existing.** This meant, uniquely for this phase:
  1. `auth/domain/__init__.py` and `auth/application/__init__.py` (the
     facades of the module the files are LEAVING) needed *editing, not
     deletion* — their imports for the 14 moved symbols were repointed
     to the new `domain/security/authorization/roles` and
     `application/security/authorization/roles` locations, while every
     other re-export (session, user, auth_query, auth_service, etc.)
     stayed untouched. This preserves every existing caller that imports
     the bare `auth.domain`/`auth.application` facade — they needed zero
     changes, since the facade still re-exports the same symbols, just
     sourced from a different file internally.
  2. Every remaining file *inside* `auth` that referenced the moved
     content — either via a relative import (`.role_governance_service`,
     `.target_user_authorization`, `from . import role_assignment_service
     as _roles`) or an absolute old-path import
     (`auth.authorization`, `auth.sod`, `auth.domain.role_binding`) —
     needed its own fix. 13 such files were found and fixed directly:
     `auth_service.py`, `default_seed_service.py`,
     `federated_identity_service.py`, `mfa_service.py`,
     `password_service.py`, `principal_builder.py`,
     `registration_service.py`, `security_audit.py`,
     `session_service.py`, `user_admin_service.py`, `domain/user.py`,
     plus the two facades above. A relative import to a file *staying*
     in `auth` (e.g. `.auth_service`, `.session_service`,
     `.session_utils`) had to become an absolute
     `src.core.platform.auth.application.<name>` import once the
     importing file moved to a different package — relative imports
     don't survive a package move.
  3. Symbol-level splitting was required wherever a single `from
     src.core.platform.auth.domain import (...)` line mixed moving and
     staying symbols in the same statement (e.g. `Role`/`UserSessionContext`
     stay; `RoleBinding`/`ROLE_SCOPE_TENANT`/`normalize_role_scope_type`
     move) — every such statement had to be split into two imports
     pointing at two different modules, not just path-renamed.
- **Largest external blast radius of any phase in this proposal**: a
  single substring-replacement script (`phase8b_rewrite.py`) touched
  127 occurrences across 118 files repo-wide, because
  `auth.authorization` (the `require_permission`/`require_any_permission`
  functions) is imported by nearly every application-layer file across
  every business module (`project_management`, `inventory_procurement`,
  `maintenance`) as well as platform's own services — confirming §9a's
  observation that `auth` is the most test- and code-referenced module
  in the whole codebase. The rewrite script's own excluded-directory
  list only needed to cover `src/core/platform/authorization/` (the old
  pre-existing module), since `auth/` itself was fixed manually first
  and therefore didn't re-match the old patterns during the sweep.
- **One real bug introduced by the rewrite script, caught by the import
  smoke test, not by grep**: the old combined `authorization/__init__.py`
  facade mixed domain symbols (`AuthorizationEngine`, `SecurityDenialEvent`)
  and application symbols (`SessionAuthorizationEngine`,
  `get_authorization_engine`, `set_authorization_engine`) in one bare
  re-export, the way every pre-restructure platform facade did. The
  script's bare-fallback rule (`src.core.platform.authorization` →
  `application.security.authorization`) is correct for the application
  symbols but wrong for the domain ones, since the two now live in
  genuinely separate packages. `python -c "from
  src.infra.composition.app_container import build_service_graph"`
  failed immediately with `ImportError: cannot import name
  'SecurityDenialEvent'`, pointing straight at
  `src/infra/platform/security_audit_recorder.py`. A follow-up grep for
  `AuthorizationEngine`/`SecurityDenialEvent` imported from the
  application-layer facade (word-boundary-safe, to avoid matching
  `SessionAuthorizationEngine`) found one more instance
  (`auth/domain/session.py`'s `TYPE_CHECKING` import) using the same
  wrong path; both fixed directly. **Lesson for any future phase with a
  similarly mixed old combined facade**: a blind bare-path substring
  fallback is only safe when the old facade's re-exports were
  single-layer; when they mixed layers, every bare-facade import site
  must be checked individually for which layer its specific symbols
  actually belong to, and the import smoke test is what catches this,
  not a grep sweep (grep found nothing wrong; only actually importing
  the code surfaced it).
- Gotcha classes 2 (monkeypatch strings) and 3 (growth-budget paths):
  none found. Gotcha class 4 (API-adapter facade re-export): not
  applicable — `authorization`/the moved `auth` pieces have no desktop
  API surface of their own.
- The only guardrail touch needed was confirming
  `test_legacy_platform_authorization_package_is_removed` (`ROOT /
  "core" / "platform" / "authorization"`, missing a `"src"` segment) is
  the same class of dead pre-`src/`-migration historical guardrail
  established as untouched since Phase 1 — left alone.
  `test_platform_persistence_structure.py` needed no changes:
  `authorization` has no persistence-layer footprint of its own (its
  domain objects are persisted through `auth`'s own infra files, which
  already reference them through the still-working `auth.domain`
  bare-facade import and therefore needed no changes either).
- Verification: given this phase's exceptional blast radius, the
  targeted spot-check widened beyond the usual directly-touched files
  to the full `platform` + `architecture` + `project_management` +
  `inventory_procurement` + `maintenance` directories (skipping only
  `test_runtime_execution_tracking.py`, uninvolved here) — both before
  and after deletion: 32 failed, 1437 passed each time, diffed against
  the baseline, **byte-for-byte identical**.
- Deleted `src/core/platform/authorization/` (the entire old directory)
  and the 14 specific files that moved out of `auth`
  (`auth/application/{role_scope_policy,canonical_role_resolver,
  role_assignment_service,role_governance_service,
  role_policy_reconciliation_service,
  scope_delegation_provisioning_service,
  tenant_role_administration_service,sod_enforcer,
  target_user_authorization}.py`, `auth/authorization.py`,
  `auth/domain/{role_binding,role_delegation,policy_reconciliation}.py`,
  `auth/sod.py`) — **not** the rest of `auth/`, which continues to
  exist pending Phases 8c/8d/8e.

**Phase 8c (`security`: `auth`'s `credentials/` + `session/` sub-split) —
completed 2026-08-05.**

- Second installment of `auth`'s partial migration: 11 files moved out
  (9 application, 2 domain), `auth/` itself still not deleted (audit,
  provisioning, and root files remain, pending Phase 8d; `policy.py`'s
  manual split remains pending Phase 8e). Final layout:
  `domain/security/auth/credentials/{mfa.py,passwords.py}`,
  `application/security/auth/credentials/{authentication_service,
  authentication_transactions,password_service,mfa_service,
  federated_identity_service}.py`, `application/security/auth/session/
  {session_service,session_utils,context_switch_service,
  principal_builder}.py`. No `contract/`/`infrastructure/`/`api/`
  footprint for this sub-split — pure domain+application content. The
  `credentials`/`session` subfolder split at the domain layer (which
  only ever holds `credentials`, since `session` has no domain-layer
  files) was kept in lockstep with the application layer's two-member
  grouping for consistency, rather than collapsing the single-member
  domain group per the usual rule — a deliberate exception, since `auth`
  will keep gaining domain-layer content in later sub-phases and a
  matching subfolder name avoids a second rename later.
- Same partial-migration mechanic as Phase 8b, scoped to a smaller
  slice: `auth/domain/__init__.py` and `auth/application/__init__.py`
  needed **no edits this time** — a targeted grep confirmed none of the
  11 moved files' symbols were ever re-exported through either bare
  facade (they were internal implementation details wired into
  `AuthService` via direct module imports, never part of the public
  surface), unlike Phase 8b's `RoleBinding`/`RoleDelegationPolicy`/etc.
  New package `__init__.py` files (`domain/security/auth/{__init__.py,
  credentials/__init__.py}`, `application/security/auth/{__init__.py,
  credentials/__init__.py,session/__init__.py}`) were therefore left as
  plain empty package markers — an established, pre-existing pattern
  elsewhere (e.g. `application/time_management/calendar/{assignment,
  capacity,definitions}/__init__.py`), not a shortcut unique to this
  phase.
- 13 files still inside `auth` needed relative-import-to-absolute-path
  fixes because the content they referenced moved to a different
  package: `auth_service.py` (7 imports —
  `authentication_service`/`authentication_transactions`/
  `context_switch_service`/`federated_identity_service`/`mfa_service`/
  `password_service`/`principal_builder`/`session_service`, all
  converted to absolute `application.security.auth.{credentials|
  session}` paths), `platform_owner_provisioning_service.py`
  (`auth.passwords` → `domain.security.auth.credentials.passwords`),
  `registration_service.py` (`auth.passwords` and
  `.federated_identity_service`, both converted), `user_admin_service.py`
  (`.session_service` → absolute). `bootstrap_service.py`,
  `default_seed_service.py`, and other files staying in `auth` that
  reference other *staying* siblings were left on relative imports
  unchanged, per precedent.
- External blast radius: a single substring-replacement script
  (`phase8c_rewrite.py`, 11 old-path → new-path mappings) touched 17
  occurrences across 10 files repo-wide — far smaller than Phase 8b's
  127/118, since these 9 modules were referenced almost exclusively via
  their fully-qualified paths (`auth.application.session_service.X`)
  rather than through a bare facade import. Two already-migrated
  Phase 8b files needed fixing (`role_assignment_service.py`,
  `role_policy_reconciliation_service.py`, both referencing
  `auth.application.session_service`/`session_utils`), plus **8
  monkeypatch string literals in `test_auth_domain_validation.py`**
  (gotcha class 2 — string paths like
  `"src.core.platform.auth.application.session_service.
  require_any_permission"` don't get caught by a normal import grep)
  and real-import fixes across `test_auth_module_phase_a.py`,
  `test_canonical_role_binding_foundation.py`, `test_passwords.py`,
  `test_platform_owner_provisioning.py`, `test_saas_startup_bootstrap.py`,
  `test_tenancy_rbac_immediate_containment.py` (all `auth.mfa`/
  `auth.passwords`), and `test_phase_2e_rbac_tenant_hardening.py`
  (`auth.application.principal_builder`, 2 occurrences). A follow-up
  repo-wide grep for every old dotted path (both bare and with a
  trailing symbol) after the script ran found zero remaining hits
  outside the 11 old files themselves (expected, pending deletion).
- Gotcha classes 1, 3, and 4: none found — no infra-path imports, no
  growth-budget path references, and no API-adapter facade re-export,
  consistent with this sub-split having no infrastructure or API
  footprint.
- `test_platform_persistence_structure.py` needed no changes:
  confirmed `credentials`/`session` have no persistence-layer footprint
  (`auth` stays in `FLAT_AREAS` unchanged).
- **Verification per the now-current policy (targeted tests only, no
  full six-target suite — full suite deferred entirely to Phase 10)**:
  `compileall` across the affected trees, both import smoke tests
  (`app_container.build_service_graph`, `import src.api.desktop`), then
  a targeted spot-check of the 8 directly-touched/affected test files
  plus `test_platform_persistence_structure.py` (93 passed) — run both
  before and after deletion, identical results both times. Additionally
  ran the full `src/tests/architecture` directory (117 passed, 2 failed)
  as a wider guardrail check given `auth`'s broad reach; both failures
  (`test_legacy_rbac_runtime_dependencies_are_removed`,
  `test_no_python_module_exceeds_hard_line_limit`) confirmed pre-existing
  against the known 32-failure baseline, unrelated to this phase.
- Deleted the 11 old files: `auth/application/{authentication_service,
  authentication_transactions,password_service,mfa_service,
  federated_identity_service,session_service,session_utils,
  context_switch_service,principal_builder}.py` and
  `auth/{mfa,passwords}.py` — **not** the rest of `auth/`, which
  continues to exist pending Phases 8d/8e.

**Phase 8d (`security`: `auth`'s `provisioning/` + `audit/` + root, plus the
deferred `infrastructure/persistence` regrouping) — completed 2026-08-05.**

- Final installment of `auth`'s application/domain code split: moved the
  remaining 13 files out of the old `auth/application/` and `auth/domain/`
  — `provisioning/{registration_service,bootstrap_service,
  default_seed_service,platform_owner_provisioning_service,
  user_admin_service}.py`, `audit/{audit_recorder,security_audit}.py`, root
  `{auth_service,auth_query,auth_validation}.py` (application), and root
  `{session,user,datetime_utils}.py` (domain) — into
  `application/security/auth/{provisioning,audit}/` and
  `application/security/auth/` root, `domain/security/auth/` root. This
  leaves only `policy.py` in the old `auth/` package, pending Phase 8e's
  manual content split — and the top-level `auth/__init__.py` facade
  itself, which stays permanently as the capability's stable public API
  (`AuthService`, `UserSessionContext`, etc.), now re-pointed at the new
  locations via `TYPE_CHECKING`/`__getattr__` — external callers using
  `from src.core.platform.auth import AuthService` (12 files: composition
  roots, `ui_qml`, tests, tools) needed **no changes**, by design, the same
  as every other phase's stable-facade treatment.
- This part of the phase (application/domain move + facade repoint + old
  file deletion) landed in an earlier working session's commits
  (`update auth`, `update auth 1`, `update auth 2`, `update auth 4`) before
  this execution log entry was written up — confirmed via `git log`/`git
  show --stat` and a repo-wide grep for any lingering deep old-path import
  (`auth.application.*`, `auth.domain.*`, `auth.provisioning.*`,
  `auth.audit.*`): zero hits outside the facade itself.
- **Found and completed the one piece this part had left undone**: unlike
  every other completed group, `auth`'s `infrastructure/persistence/
  {mappers,orm,repositories}/auth.py` (§5a — one combined file per layer,
  never split by content the way application/domain were) was still sitting
  flat at the top of each of the three trees, not yet regrouped into
  `security/auth/auth.py` like every other module's infra. Moved all three
  (269/405/772 lines) into `{mappers,orm,repositories}/security/auth/
  auth.py`, fixing each file's own internal cross-import
  (`mappers/auth.py`'s `orm.auth` import, `repositories/auth.py`'s
  `mappers.auth`/`orm.auth` imports) to the new paths.
- External call sites fixed: `src/infra/composition/{maintenance_registry,
  repositories}.py`, `src/infra/persistence/orm/__init__.py`, and 8 test
  files (`test_auth_module_phase_a`, `test_auth_registration_role_audit_atomicity`,
  `test_membership_lifecycle_foundation`, `test_phase_1_tenant_security_foundation`
  — 6 occurrences, `test_phase_2a_admin_role_hierarchy`,
  `test_platform_owner_provisioning`, `test_role_policy_reconciliation`) —
  a plain repo-wide grep sufficed (no bare-facade fallback ambiguity, since
  these are all direct `infrastructure.persistence.{mappers,orm,
  repositories}.auth` imports, never routed through `auth/__init__.py`).
- Two guardrail tests needed their own string-literal updates, the same
  class of fix every already-migrated group's phase needed:
  `test_architecture_guardrails_legacy_orm.py` — the
  `test_composition_imports_focused_persistence_adapters` assertion string
  (`repositories.auth` → `repositories.security.auth.auth`) and the
  `test_orm_package_root_loads_all_model_packages` module-list entry
  (`"auth"` → `"security.auth.auth"` in `platform_orm_modules`).
  `test_platform_persistence_structure.py` — moved `security/auth/auth.py`
  from `FLAT_AREAS` into `NESTED_AREA_FILES` (mirrors every other
  now-grouped module) and emptied `FLAT_AREAS` to `set()`, since `auth` was
  the last remaining flat area. Both were caught by the targeted
  before/after spot-check, not a fresh grep — same lesson as Phase 8b's
  bare-facade bug: the import smoke test / targeted test run is what
  surfaces this, not string search.
- Verification (targeted only, per the standing policy — no full
  six-target suite until Phase 10): `compileall` on the three new
  `security/auth/` trees, both import smoke tests, then the targeted
  spot-check (the 8 directly-touched test files above, plus
  `test_platform_persistence_structure.py`, plus the broader
  `auth`-adjacent set already used in 8c for consistency) — run before and
  after deleting the three old flat files. Before: 2 failed (the module-list
  assertion above, plus the pre-existing `test_legacy_rbac_runtime_
  dependencies_are_removed` baseline failure) — fixed the real one. After
  fixing and re-running post-deletion: 1 failed (`test_platform_
  persistence_uses_module_style_layout`, the `FLAT_AREAS` staleness above)
  — fixed, re-ran once more: 150 passed, 1 failed (the same pre-existing
  `.env`/`PM_AUTHORIZATION_MIGRATION_MODE` baseline failure flagged in
  Phase 8c's log too), consistent across every run.
- Deleted the 3 old flat files:
  `infrastructure/persistence/{mappers,orm,repositories}/auth.py`.
  `auth/policy.py` and the permanent `auth/__init__.py` facade are the only
  things left in the old `auth/` package now — `policy.py` pending Phase
  8e's manual split.

**Phase 8e (`auth/policy.py` manual content split, §4a) — completed
2026-08-05.**

- The one non-mechanical step in `security`: `policy.py` conflated two
  unrelated concerns in one file, so it was split by hand rather than moved
  whole. `DEFAULT_PERMISSIONS`, all fifteen-odd private role-group set
  constants (`_VIEWER`, `_TEAM_MEMBER`, ... `_MAINTENANCE_SCOPE_MANAGER`),
  `DEFAULT_ROLE_PERMISSIONS`, `SYSTEM_ROLE_POLICY_NAME`, and
  `SYSTEM_ROLE_POLICY_VERSION` (the permission/role catalog — authorization's
  concern) moved to new file `domain/security/authorization/roles/
  role_permission_catalog.py`. `login_lockout_threshold()`,
  `login_lockout_minutes()`, `session_timeout_minutes()` (login/session
  config — authentication's concern) moved to new file `domain/security/
  auth/login_security_policy.py`. Both destination folders already existed
  from Phases 8b/8d, per the plan.
- Both new files' symbols were also added to their package `__init__.py`
  re-exports (`domain/security/authorization/roles/__init__.py`,
  `domain/security/auth/__init__.py`), matching every sibling domain
  submodule's existing treatment — some callers use the package-level
  import, some the submodule-level import, and both need to keep working.
- 12 external call sites fixed, none mixing symbols across the split
  boundary (confirmed by reading each import block first, so no file needed
  splitting its own import list in two): `authentication_transactions.py`
  and `session_utils.py` (auth-side, `login_security_policy`);
  `default_seed_service.py`, `sod_enforcer.py`,
  `role_policy_reconciliation_service.py`,
  `tenant_role_administration_service.py`, and 7 test files
  (`test_phase_0_critical_bug_fixes`, `test_phase_2a_admin_role_hierarchy`,
  `test_phase_2b/2c/2d/2e_*_scope_roles`, `test_role_policy_reconciliation`,
  `test_saas_startup_bootstrap`,
  `test_project_finance_phase_a0_security`) (authorization-side,
  `role_permission_catalog`).
- Gotcha sweep: zero remaining `auth.policy` references anywhere (plain
  grep), zero monkeypatch string literals naming the old path, and the
  `auth/__init__.py` facade never referenced `policy` at all (confirmed by
  reading it), so no facade-repoint step was needed for this phase, unlike
  8b/8c.
- Verification (targeted only): `compileall` on the affected trees, both
  import smoke tests, then an 18-file targeted spot-check covering every
  fixed call site plus `test_platform_persistence_structure.py` and the
  broader role/governance test set — run before and after deleting the old
  `policy.py`. Identical both times: 167 passed, 0 failed.
- Deleted `auth/policy.py`. The old `auth/` package now contains **only**
  the permanent `auth/__init__.py` facade — every other file that ever
  lived there across Phases 8b–8e has moved to its layer-first home. This
  closes out `auth`'s own code migration; `security` as a whole still has
  **Phase 8f** remaining (`access/authorization.py` update + the §5c PM
  extraction).

### Notes on this ordering

- **`security` (Phases 8a–8f) is deliberately last among the content-group
  phases**, not first — it's both the largest single reclassification in
  this proposal (§4a) and the most test-referenced module in the whole
  codebase (§9a: 52 test files touch `auth`). Every earlier phase's code
  keeps importing `auth`/`authorization` from their *old* location right up
  until Phase 8 — that's fine and expected; nothing about moving `history`
  or `master_data` requires `auth` to have moved first.
- **Phase 9 (the runtime rearrangement) is last of all**, because
  `PlatformRuntimeApplicationService` and `desktop_api_registry.py` are the
  two files in this entire proposal that depend on the *most* other groups
  being finished (`org`, `tenancy`, `modules`, `auth`, plus every business
  module's own desktop API). Doing it early would mean touching its imports
  repeatedly as each dependency relocates underneath it; doing it last means
  touching it exactly once.
- **Nothing blocks starting Phase 1 today.** Phases 1–4 have no
  cross-group dependencies on each other or on anything in Phases 5–9, so
  they could in principle run in any order among themselves (sequenced here
  purely by size/risk, smallest first).
- If a phase's own review turns up something the team wants to reconsider
  (e.g. a different subfolder split within `master_data`), that's a
  same-phase decision — it doesn't block or reopen any phase already merged.
