# Phase 2 → Phase 3 Hardening Findings

Pre-conditions that must be resolved before Phase 3 work begins.
Generated from the full tenant architecture audit (Phase 0–2D verification).

**Overall system score: 81 / 100**
**Domains that returned FAIL: V2 (unscoped queries), V3 (tenant context integrity), V4 (org security), V6 (RBAC)**

---

## How to use this document

Work items are ordered by severity. Complete all Critical and High items before starting Phase 3.
Each item includes the exact file and line so nothing needs to be located.

Status column — update as work progresses:

| Symbol | Meaning |
|--------|---------|
| `[ ]` | Not started |
| `[~]` | In progress |
| `[x]` | Done |

---

## Critical — Must fix before any Phase 3 work

### C-1 — Role-assignment ceiling: `tenant_admin` and `org_admin` can grant `admin`

- **Status**: `[x]`
- **Remediation**: Added `_PRIVILEGE_RANK` dict (admin=100, tenant_admin=80, org_admin=70, default=10) and `_enforce_privilege_ceiling()` in `role_assignment_service.py`. Callers with rank < 100 cannot assign roles with rank ≥ their own. Admin (rank 100) bypasses the ceiling. 8 tests added in `test_phase_2e_rbac_tenant_hardening.py`.
- **Root cause**: Both `tenant_admin` and `org_admin` include `auth.manage`. `assign_role()` requires only `auth.manage` with no ceiling constraint. Either role can grant `admin` or `platform_admin` to any user in the system.
- **Files**:
  - `src/core/platform/auth/policy.py` lines 251–271 — remove `auth.manage` from `_TENANT_ADMIN` and `_ORG_ADMIN` sets, or introduce a scoped `role.manage` permission
  - `src/core/platform/auth/application/role_assignment_service.py` lines 17–36 — add ceiling check: caller cannot assign a role whose privilege level equals or exceeds their own highest role
- **Test coverage needed**: `assign_role()` by `tenant_admin` attempting to grant `admin`; `org_admin` attempting to grant `tenant_admin`

---

### C-2 — `assign_role()` / `revoke_role()` have no tenant scope

- **Status**: `[x]`
- **Remediation**: Added `_enforce_tenant_membership()` in `role_assignment_service.py`. After permission check, validates target user has active `user_tenants` row for caller's `active_tenant_id`. Bypassed for admin/platform.admin and when no tenant repo is wired. 3 tests added.
- **Root cause**: `assign_role()` and `revoke_role()` check only `auth.manage` capability with no tenant-boundary validation. A `tenant_admin` in Tenant A can call these on a user from Tenant B.
- **Files**:
  - `src/core/platform/auth/application/role_assignment_service.py` lines 17–55 — add guard: validate the target user has an active `user_tenants` membership row for the caller's `active_tenant_id` before applying changes
- **Test coverage needed**: cross-tenant role assignment attempt should raise `TENANT_ACCESS_DENIED`

---

## High — Must fix before Phase 3

### H-1 — Cross-tenant project probe in `ApprovalRepository`

- **Status**: `[x]`
- **Remediation**: `project_in_different_organization()` now calls `self._context()` and adds `ProjectORM.tenant_id == ctx.tenant_id` to the WHERE clause. Cross-tenant project probes return `False` (project not visible = not in a different org).
- **Root cause**: `project_in_different_organization()` at line 139 runs `select(ProjectORM.organization_id).where(ProjectORM.id == project_id)` with no `tenant_id` filter. Called at runtime during approval create/read operations. Any user can probe project existence across tenant boundaries using a known UUID.
- **Files**:
  - `src/core/platform/infrastructure/persistence/repositories/approval.py` line 139 — add `.where(ProjectORM.tenant_id == caller_tenant_id)` to the query; thread `tenant_id` in from `ApprovalService._assert_project_in_active_organization()`
- **Test coverage needed**: approval operation with project UUID from a different tenant should fail

---

### H-2 — `active_organization_id()` fallbacks bypass tenant validation

- **Status**: `[x]`
- **Remediation**: `active_organization_id()` now guards the principal org fallback — if the session has an active tenant, it only returns the principal's org when the principal's tenant matches the session's active tenant. Mismatched or absent principal tenant causes the fallback to return `None`. 3 tests added.
- **Root cause**: Two fallback paths in `UserSessionContext.active_organization_id()` restore an org ID without validating it belongs to the active tenant: (1) `principal.active_organization_id` read verbatim from `AuthSession`; (2) the single-org shortcut from `principal.scoped_access['organization']`. A restored session can have `active_organization_id` pointing to an org from a previous tenant before any `_can_access()` call has run.
- **Files**:
  - `src/core/platform/auth/domain/session.py` lines 290–304 — after resolving either fallback, cross-check: if `active_tenant_id` is set, verify `org.tenant_id == active_tenant_id`; clear to `None` if mismatch
- **Test coverage needed**: session restore with org from previous tenant should clear the org, not return it

---

### H-3 — `_restore_active_context_from_principal()` reinstates cleared org after `switch_to_tenant()`

- **Status**: `[x]`
- **Remediation**: `_restore_active_context_from_principal()` now guards the org restore — only sets `_active_organization_id` from the principal if `current_tenant` is None (bootstrap mode) or exactly equals the principal's tenant. When session has an active tenant but principal's tenant doesn't match, the org restore is skipped. 2 tests added.
- **Root cause**: `switch_to_tenant()` clears `_active_organization_id`. However `_restore_active_context_from_principal()` (lines 345–360) is called by `_active_principal()` on every permission check. It unconditionally overwrites `_active_organization_id` with `AuthSession.last_active_organization_id` — the value from the DB row, which still holds the old org until `persist_session_context()` flushes. Race window: between the clear and the flush, any permission check reinjects the stale cross-tenant org.
- **Files**:
  - `src/core/platform/auth/domain/session.py` lines 345–360 — add cross-tenant validation before overwriting; skip the restore for `active_organization_id` if the org's `tenant_id` does not match the session's `active_tenant_id`
- **Test coverage needed**: permission check immediately after `switch_to_tenant()` (before persist) should not restore stale org

---

### H-4 — `build_principal()` injects `AuthSession` org with no tenant cross-validation

- **Status**: `[x]`
- **Remediation**: `principal_builder.py` now only populates `active_organization_id` in the built principal when `last_active_tenant_id` is also present. If the `AuthSession` row has no `last_active_tenant_id`, `active_organization_id` is set to `None`, preventing a dangling org from entering the session. 2 tests added.
- **Root cause**: `build_principal()` populates `active_organization_id` from `AuthSession.last_active_organization_id` without checking that this org belongs to `last_active_tenant_id`. A stale or mismatched `AuthSession` row can inject an arbitrary `(org_id, tenant_id)` pair into the session.
- **Files**:
  - `src/core/platform/auth/application/principal_builder.py` lines 78–88 — after reading `last_active_organization_id`, query `organization_repo.get_for_tenant(org_id, last_active_tenant_id)`; if None, clear `active_organization_id` in the principal
- **Test coverage needed**: `build_principal()` with mismatched `AuthSession` org/tenant should produce a principal with `active_organization_id=None`

---

### H-5 — `_can_access()` null bypass: orgs with `tenant_id=None` pass for any tenant

- **Status**: `[x]`
- **Remediation**: `_can_access()` in `tenant_context.py` now uses `if not org_tenant_id or org_tenant_id != active_tenant_id: return False` instead of the previous `if org_tenant_id and org_tenant_id != active_tenant_id`. Orgs with null/empty `tenant_id` are now denied when any active tenant is set. 4 tests added.
- **Root cause**: `TenantContextService._can_access()` lines 219–222 is conditional: if `active_tenant_id` is falsy OR `organization.tenant_id` is `None`/empty, the cross-tenant membership check is skipped entirely. Any org row with `tenant_id=None` (bootstrap-created or failed-backfill) passes the guard for any user in any tenant context.
- **Files**:
  - `src/core/platform/tenancy/tenant_context.py` lines 215–245 — remove the conditional bypass. Rule: if `active_tenant_id` is set and `org.tenant_id` is `None`/empty, return `False` (treat as cross-tenant). Only skip the check when `active_tenant_id` is also `None` (genuine bootstrap mode with no session).
- **Test coverage needed**: `_can_access()` with `org.tenant_id=None` and an active tenant should return `False`

---

### H-6 — `OrganizationORM.tenant_id` declared `nullable=True`, contradicting DB constraint

- **Status**: `[x]`
- **Remediation**: `OrganizationORM.tenant_id` changed from `Mapped[Optional[str]]` / `nullable=True` to `Mapped[str]` / `nullable=False`, aligning the ORM with the existing DB `NOT NULL` constraint from migration `r3s4t5u6v7w8`. Bootstrap sequence in `platform_registry.py` reordered — default tenant is now created before `organization_service.bootstrap_defaults()` so the org is always inserted with a valid `tenant_id`. 1 test added.
- **Root cause**: Migration `r3s4t5u6v7w8` enforces `NOT NULL` on `organizations.tenant_id` at the DB level, but the ORM model declares `Mapped[Optional[str]]` / `nullable=True`. ORM divergence means Python-level code can construct an `Organization` object with `tenant_id=None` without an immediate error — the constraint only fires at DB flush time, making H-5 bypass easier to exploit for newly created objects.
- **Files**:
  - `src/core/platform/infrastructure/persistence/orm/org.py` line 17 — change to `Mapped[str]` with `nullable=False`
- **Test coverage needed**: constructing `OrganizationORM` without `tenant_id` should raise `IntegrityError` at flush

---

### H-7 — `suspend_tenant()` / `archive_tenant()` have no target-tenant scope check

- **Status**: `[x]`
- **Remediation**: `suspend_tenant()` and `archive_tenant()` now require `platform.admin` exclusively (changed from `require_any_permission(["tenant.manage", "platform.admin"])` to `require_permission("platform.admin")`). `tenant_admin` can no longer trigger lifecycle state changes on any tenant. 4 tests added.
- **Root cause**: Both operations accept `tenant.manage` capability only. The `_guard_self_lockout` prevents suspending the caller's own active tenant, but there is no guard preventing a `tenant_admin` from suspending or archiving any *other* tenant in the system.
- **Files**:
  - `src/core/platform/tenancy/application/tenant_admin_service.py` lines 203–239 — add a guard: either (a) restrict these lifecycle operations to `platform.admin` only (remove `tenant.manage` from the OR condition), or (b) validate that `target_tenant_id == caller.active_tenant_id`
- **Test coverage needed**: `tenant_admin` of Tenant A attempting to suspend Tenant B should raise `PERMISSION_DENIED`

---

### H-8 — User admin operations (`set_user_active`, `update_user_profile`, `unlock_user_account`) have no tenant scope

- **Status**: `[x]`
- **Remediation**: Added `_enforce_user_tenant_boundary()` in `user_admin_service.py` with the same pattern as `_enforce_tenant_membership()` — admin/platform.admin bypass, otherwise validates target user is an active member of the caller's active tenant. Called after the permission check in all three methods. Error code `USER_CROSS_TENANT_DENIED`. 5 tests added.
- **Root cause**: All three methods require only `auth.manage` with no tenant boundary check. Since `org_admin` holds `auth.manage` and the `users` table has no `tenant_id` column, an `org_admin` can deactivate or modify users from other tenants.
- **Files**:
  - `src/core/platform/auth/application/user_admin_service.py` lines 39–138 — before applying changes, verify the target user has an active `user_tenants` membership row for the caller's `active_tenant_id`. Raise `TENANT_ACCESS_DENIED` if not.
- **Test coverage needed**: `org_admin` of Tenant A modifying user from Tenant B should fail

---

## Medium — Fix before Phase 3 release, not blocking start

### M-1 — `TenantContextService` calls unscoped `get()` instead of `get_for_tenant()`

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/tenancy/tenant_context.py` line 126 (`get_active_organization`) and line 140 (`set_active_organization`) — replace `organization_repo.get(id)` with `organization_repo.get_for_tenant(id, active_tenant_id)`
- **Risk**: Relies entirely on post-fetch `_can_access()` guard. Scoping should happen at the query layer.

---

### M-2 — `UserRepository.list_all()` exposes all users cross-tenant at runtime

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/infrastructure/persistence/repositories/auth.py` line 105 — rename to `_admin_list_all()` or add optional `tenant_id` parameter; add assertion that caller holds `platform.admin` for the unfiltered path
  - `src/core/platform/auth/application/user_admin_service.py` — update call site to pass `tenant_id` from session context

---

### M-3 — `ActivityRepository.list_recent()` has silent `except-pass` scope fallback

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/infrastructure/persistence/repositories/activity.py` line 38 — inherit `TenantScopedRepositorySupport` and enforce scoping via `_context()` as all other tenant-aware repositories do
  - `src/core/platform/activity/application/activity_service.py` lines 87–96 — remove the silent `except-pass` scope injection block; let the repository enforce it
- **Risk**: Any exception in the service-layer scope injection silently drops the filter and returns cross-tenant activity.

---

### M-4 — Bootstrap sets `active_organization_id` before `active_tenant_id`

- **Status**: `[ ]`
- **Files**:
  - `src/infra/composition/platform_registry.py` lines 185–199 — reorder: set tenant first (line 199 logic first), then use `list_for_tenant(tenant.id, active_only=True)` to select org; set org via `TenantContextService.set_active_organization()` instead of directly on the session object

---

### M-5 — `TenantContextService.set_active_tenant()` does not clear `active_organization_id`

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/tenancy/tenant_context.py` lines 67–104 — add `_user_session.clear_active_organization_id()` (or equivalent) at the start of `set_active_tenant()`, matching the safe behaviour of `switch_to_tenant()`
- **Risk**: Any caller using `set_active_tenant()` directly (bootstrap, tests) leaves the previous org active under the new tenant.

---

### M-6 — RBAC scope resolver for `'organization'` uses unscoped `get()`

- **Status**: `[ ]`
- **Files**:
  - `src/infra/composition/platform_registry.py` line 336 — change `lambda organization_id: repositories.organization_repo.get(organization_id) is not None` to use `get_for_tenant(organization_id, active_tenant_id)` resolved from the session at call time
- **Risk**: A privileged admin can grant scoped-access to an org in another tenant; the validator silently accepts it.

---

### M-7 — `tenant_admin` includes `tenant.create` — self-propagation risk

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/auth/policy.py` line 251–261 — remove `tenant.create` from `_TENANT_ADMIN` set; restrict tenant creation to `platform.admin` or a dedicated `platform_admin` role only
- **Risk**: A `tenant_admin` can create new tenants and is auto-granted `tenant_admin` in each, propagating indefinitely.

---

### M-8 — Add dedicated `'tenant_access'` error category in `execute_desktop_operation`

- **Status**: `[ ]`
- **Files**:
  - `src/api/desktop/platform/_support.py` lines 18–38 — add a dedicated category (e.g. `'tenant_access'`) for `TENANT_SUSPENDED`, `TENANT_ARCHIVED`, `TENANT_ACCESS_DENIED` error codes instead of mapping them to the generic `'conflict'` category
- **Impact**: QML error handling can distinguish tenant-specific access denials without brittle `error.code` string-matching.

---

### M-9 — Emit `PlatformEvent` for tenant context switches

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/tenancy/tenant_context.py` `switch_to_tenant()` — call `_emit_tenant_event()` (or equivalent) after a successful switch: `operation='switch_tenant'`, `actor_user_id`, `old_tenant_id`, `new_tenant_id`, `outcome='success'`
  - `src/api/desktop/platform/tenant.py` lines 38–43 — ensure the event is reachable from the desktop API path
- **Impact**: No audit trail currently exists for who switched to which tenant and when.

---

### M-10 — Emit `PlatformEvent` for `assign_scope_grant()`

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/access/application/access_control_service.py` line 176 — add event: `operation='assign_scope_grant'`, `resource_type='scoped_access'`, `severity='medium'`
- **Impact**: Highest-priority missing audit event. Scope grants are security-sensitive and currently have no event or audit entry.

---

### M-11 — `EnterpriseCalendarResolver` captures `organization_id` at build time

- **Status**: `[ ]`
- **Files**:
  - `src/infra/composition/platform_registry.py` lines 405–409 — replace static `organization_id` closure with a callable: `org_id_provider = lambda: tenant_context_service.get_active_organization_id()`
  - `src/core/platform/calendar/application/enterprise_calendar_resolver.py` — accept a callable `org_id_provider` and call it on each resolution instead of using the captured value
- **Risk**: If a user switches organization mid-session, the resolver continues using the old org's calendar configuration.

---

### M-12 — Expand SoD rules: payroll self-approval, finance unilateral control

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/auth/sod.py` — add at minimum:
    - `payroll.manage` + `payroll.approve` conflict (user must not prepare and approve their own payroll)
    - `cost.manage` + `finance.manage` + `report.export` conflict (unilateral financial reporting control)

---

### M-13 — `UserSessionContext.get_active_tenant()` silently falls back to default tenant without membership check

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/tenancy/tenant_context.py` lines 58–65 — when falling back to `get_default()`, validate the user has an active membership row for the default tenant before returning it; raise or return `None` if not
- **Risk**: Users with no default-tenant membership silently receive it as their active context.

---

## Low — Clean-up items, fix before Phase 3 release

### L-1 — Consolidate triplicated `_tenant_scope.py` files

- **Status**: `[ ]`
- `src/core/modules/project_management/infrastructure/persistence/repositories/_tenant_scope.py`
- `src/core/modules/maintenance/infrastructure/persistence/repositories/_tenant_scope.py`
- `src/core/modules/inventory_procurement/infrastructure/persistence/repositories/_tenant_scope.py`
- All three are ~80-line near-identical implementations of `_apply_scope`, `_stamp_scope`, `_get_in_scope`, `_require_in_scope`. Extract a shared `ModuleTenantScopedRepositorySupport` in `src/core/platform/infrastructure/persistence/repositories/_tenant_scope.py` and inherit.

---

### L-2 — `suspend_tenant` event hardcodes `old_status`

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/tenancy/application/tenant_admin_service.py` line 99 — capture `prior_status = tenant.tenant_status` before mutation and pass `old_status=prior_status`, matching the `archive_tenant` pattern

---

### L-3 — Remove duplicate role aliases

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/auth/policy.py` lines 273–294 — `'finance'` and `'finance_controller'` map to identical permission sets; `'maintenance_manager'` and `'maintenance_admin'` map to identical sets. Consolidate to one canonical name each. Migrate any existing `user_roles` rows referencing the deprecated aliases before removing.

---

### L-4 — `list_users_for_tenant()` does not filter `is_active=False` memberships

- **Status**: `[ ]`
- **Files**:
  - `src/core/platform/infrastructure/persistence/repositories/user_tenant.py` lines 50–53 — add `.where(UserTenantORM.is_active == True)` consistent with `list_tenant_ids_for_user()` (line 43)

---

### L-5 — `TaskCollaborationStore` unread-mentions query is fully unscoped

- **Status**: `[ ]`
- **Files**:
  - `src/core/modules/project_management/infrastructure/collaboration_store.py` line 203 — `TaskCommentORM` has no `tenant_id` column. Add `tenant_id` to `TaskCommentORM` and filter by it, or join through `TaskORM.tenant_id`. Not currently exposed via desktop API but latent risk when it is.

---

## Future Platform Events to emit (not blocking Phase 3)

These operations currently write to the audit log only or have no trace at all. Add `PlatformEvent` emission as part of Phase 3 or Phase 5 activity/audit expansion.

| Priority | Operation | File |
|----------|-----------|------|
| High | `assign_role` / `revoke_role` | `role_assignment_service.py` lines 26 / 45 |
| Medium | `user.register` | `registration_service.py` line 109 |
| Medium | `organization.create` | `organization_service.py` line 168 |
| Medium | `user_tenant_membership.add` | `tenant_admin_service.py` lines 188–194 |
| Low | `site.create` | `site_service.py` |
| Low | `department.create` | `department_commands.py` |

---

## Summary by severity

| Severity | Count | All resolved? |
|----------|-------|---------------|
| Critical | 2 (C-1, C-2) | `[x]` |
| High | 8 (H-1 through H-8) | `[x]` |
| Medium | 13 (M-1 through M-13) | `[ ]` |
| Low | 5 (L-1 through L-5) | `[ ]` |
| **Total** | **28** | |

**Phase 3 gate: all Critical and High items must be `[x]` before Phase 3 work begins.**
**Gate status: PASSED — all Critical and High items resolved as of 2026-06-18.**
