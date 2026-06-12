# TENANT / ORGANIZATION ARCHITECTURE AUDIT REPORT

**Classification:** Internal Architecture Audit  
**Date:** 2026-06-12  
**Scope:** Full-stack — ORM, Migrations, Repositories, Services, Controllers, QML  
**Status:** Pre-implementation — no code changes made  

---

## 1. Executive Summary

The application currently has **no Tenant model**. The `Organization` entity serves as the top-level isolation boundary across all modules (Project Management, Inventory/Procurement, Maintenance, Platform), with `organization_id` used as the de-facto tenant discriminator on every business table. The `TenantContext` object is a thin wrapper around `Organization`, making "tenant" and "organization" synonymous at the domain level — which is architecturally incorrect for a multi-tenant ERP where one tenant (a company) may operate multiple organizations (subsidiaries, divisions, legal entities).

Phases 1–4 of prior "tenant isolation" work added `organization_id` columns to portfolio, approval, audit log, and resource tables via migrations `p9q0r1s2t3u4`, `q0r1s2t3u4v5`, `r1s2t3u4v5w6`, and `s2t3u4v5w6x7`. These migrations hardened org-level scoping but did so using the wrong column name (`organization_id` instead of `tenant_id`) and against the wrong boundary model. They improved intra-organization isolation but did not introduce true multi-tenancy — they are all built on the assumption that **organization = tenant**.

### Critical Risks in Current State

- A freshly registered user with no explicit org grant has `has_organization_access()` return `True` for every organization in the system, because empty `organization_ids` is interpreted as "unrestricted."
- The global `admin` role bypasses all org isolation checks unconditionally in three separate code paths.
- 17 repositories expose bare `get(pk)` with no org or tenant predicate, and 14 repositories expose unscoped list methods returning cross-org data.
- The `employees` table has no `organization_id` or `tenant_id` column — org scope is derived transitively through `site_id`, meaning an employee with no site is unscoped entirely.
- QML exposes `setActiveOrganization()` as an unguarded slot callable by any QML object holding an `adminWorkspace` reference.

---

## 2. Current Architecture Findings

### 2.1 TenantContext — Current Broken State

`TenantContext` is defined in `src/core/platform/tenancy/tenant_context.py` as a frozen dataclass:

```python
@dataclass(frozen=True)
class TenantContext:
    organization_id: str
    organization: Organization
```

It carries exactly two fields: an `organization_id` string and the loaded `Organization` domain object. There is **no `tenant_id` field, no `Tenant` model**, and no distinction between the concepts of "tenant" and "organization."

`TenantContextService` resolves the active organization from `UserSessionContext.active_organization_id()`, loads it via `OrganizationRepository.get()`, validates it against `principal.scoped_access["organization"]`, and stores it in-memory only. The method `set_active_organization()` writes only to the in-memory session — the active org is never persisted to the `auth_sessions` row in the database.

Issues:
1. On every new login, the org context is re-derived by heuristic (single-element org set falls through to `organization_ids()[0]`), creating non-deterministic org assignment when users belong to multiple organizations.
2. `require_context()` and `require_active_organization_id()` raise `TenantContextError(TENANT_CONTEXT_REQUIRED)` when organization is not resolved — but the underlying concept being required is an organization, not a tenant.
3. No audit trail of which tenant context was active when a mutation was performed.

### 2.2 Organization Model — Currently Acting as Tenant

`OrganizationORM` columns: `id`, `organization_code`, `display_name`, `timezone_name`, `base_currency`, `is_active`, `version`. **No `tenant_id` FK. No parent scope.**

`SqlAlchemyOrganizationRepository.get_active()` returns the first active organization globally — a single-tenant assumption baked into the data access layer.

`OrganizationService._deactivate_other_organizations()` enforces a single-active-org-as-tenant pattern — this is fundamentally wrong and must be removed.

The `organization_module_entitlements` table uses `(organization_id, module_code)` as its composite PK, treating each organization as an independent licensing unit. Must be re-keyed to `(tenant_id, module_code)`.

### 2.3 Missing Tenant Model

**No `Tenant` ORM class, no `tenants` table, no `tenant_id` column, and no migration creating any of these exists anywhere in the codebase.**

Target `TenantContext`:
```python
@dataclass(frozen=True)
class TenantContext:
    tenant_id: str
    tenant: Tenant
    organization_id: str | None
    organization: Organization | None
```

### 2.4 Auth / User / Session Issues

- **User-tenant binding:** `UserORM` has no `tenant_id` or `organization_id` column. Users are platform-global. Tenant membership is derived entirely at runtime from `scoped_access_grants` rows.
- **Empty-set bypass:** `has_organization_access()` with zero grants returns `True` unconditionally for any org — any newly registered user can access all organizations.
- **Global roles cross tenant boundaries:** `user_roles` has no `organization_id`. The `admin` role is global — an admin in one tenant is admin in all tenants.
- **Session persistence gap:** `auth_sessions` stores no `organization_id` or `tenant_id`. Active organization context is reconstructed in-memory on each login.
- **`register_user()` creates org-unscoped users** — no `scoped_access_grants` row is created at registration time.

---

## 3. Table Ownership Map

| Entity | Current Isolation Column | Missing Column | Classification | Risk Level |
|---|---|---|---|---|
| `organizations` | none (IS the root) | `tenant_id` | org_business_unit | **CRITICAL** |
| `sites` | `organization_id` | `tenant_id` | org_business_unit | High |
| `departments` | `organization_id` | `tenant_id` | org_business_unit | High |
| `users` | none | none (intentional global) | platform_global | Low |
| `auth_sessions` | none | `last_active_tenant_id`, `last_active_organization_id` | platform_global | Medium |
| `roles` | none | none (intentional global) | platform_global | Medium |
| `permissions` | none | none (intentional global) | platform_global | Low |
| `user_roles` | none | `organization_id` (for org-scoped roles) | platform_global | High |
| `role_permissions` | none | none | platform_global | Low |
| `organization_module_entitlements` | `organization_id` (PK) | `tenant_id` (replace PK) | platform_global | High |
| `scoped_access_grants` | `scope_type/scope_id` | `tenant_id` | platform_global | High |
| `project_memberships` | none (via project FK) | `organization_id` | tenant_child | High |
| `approval_requests` | `organization_id` (nullable) | make NOT NULL; future: `tenant_id` | tenant_root | High |
| `audit_logs` | `organization_id` (nullable) | make NOT NULL; future: `tenant_id` | tenant_root | High |
| `document_structures` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `documents` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `document_links` | `organization_id` (NOT NULL) | `tenant_id` | tenant_child | Medium |
| `employees` | **none (CRITICAL GAP)** | `organization_id` (immediate) + `tenant_id` | tenant_root | **CRITICAL** |
| `parties` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `time_entries` | none | `organization_id` (immediate) + `tenant_id` | tenant_child | High |
| `timesheet_periods` | none | `organization_id` (immediate) + `tenant_id` | tenant_child | High |
| `platform_calendars` | `organization_id` | `tenant_id` | tenant_root | Medium |
| `calendar_working_rules` | none (via calendar FK) | inherit | tenant_child | Low |
| `calendar_exceptions` | none (via calendar FK) | inherit | tenant_child | Low |
| `calendar_recurring_events` | none (via calendar FK) | inherit | tenant_child | Low |
| `shift_patterns` | `organization_id` | `tenant_id` | tenant_root | Medium |
| `projects` | `organization_id` (nullable) | make NOT NULL; `tenant_id` | tenant_root | **CRITICAL** |
| `project_resources` | none (via project FK) | inherit | tenant_child | Medium |
| `tasks` | none (via project FK) | inherit | tenant_child | High |
| `task_assignments` | none (via task FK) | inherit | tenant_child | Medium |
| `task_dependencies` | none (via task FK) | inherit | tenant_child | Medium |
| `resources` | `organization_id` (nullable) | make NOT NULL; `tenant_id` | tenant_root | High |
| `portfolio_scoring_templates` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `portfolio_intake_items` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `portfolio_scenarios` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `register_entries` | none (via project FK) | `organization_id` | tenant_child | High |
| `cost_items` | none (via project FK) | inherit | tenant_child | High |
| `calendar_events` | none (via project FK) | inherit | tenant_child | Medium |
| `project_baselines` | none (via project FK) | inherit | tenant_child | High |
| `task_comments` | none (via task FK) | `organization_id` | tenant_child | **CRITICAL** |
| `inventory_item_categories` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `inventory_stock_items` | `organization_id` (NOT NULL) | `tenant_id` | tenant_root | Medium |
| `inventory_storerooms` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `inventory_stock_balances` | `organization_id` (NOT NULL) | `tenant_id` | tenant_child | Medium |
| `inventory_stock_transactions` | `organization_id` (NOT NULL) | `tenant_id` | tenant_child | Medium |
| `inventory_stock_reservations` | `organization_id` (NOT NULL) | `tenant_id` | tenant_child | Medium |
| `inventory_purchase_requisitions` | `organization_id` + `requesting_site_id` | `tenant_id` | tenant_root | Medium |
| `inventory_purchase_orders` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `inventory_receipt_headers` | `organization_id` + `received_site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_locations` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_systems` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_assets` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_asset_components` | `organization_id` | `tenant_id` | tenant_child | Medium |
| `maintenance_sensors` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_sensor_readings` | `organization_id` (NOT NULL, high-volume) | `tenant_id` | tenant_child | High |
| `maintenance_work_requests` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_work_orders` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_work_order_tasks` | `organization_id` | `tenant_id` | tenant_child | Medium |
| `maintenance_preventive_plans` | `organization_id` + `site_id` | `tenant_id` | tenant_root | Medium |
| `maintenance_preventive_plan_instances` | `organization_id` | `tenant_id` | tenant_child | Medium |

---

## 4. Repository Risk Map

| Repository | Scoping Method | Risk | Gap |
|---|---|---|---|
| `SqlAlchemyProjectRepository` | `list_for_organization(org_id)` | High | `get(pk)` has no org predicate |
| `SqlAlchemyProjectResourceRepository` | `list_by_project(project_id)` only | **CRITICAL** | No org or tenant filter anywhere |
| `SqlAlchemyTaskRepository` | `list_by_project(project_id)` only | **CRITICAL** | Task graph accessible by guessable project UUID |
| `SqlAlchemyAssignmentRepository` | FK only (`task_id`, `resource_id`) | **CRITICAL** | All methods fully unscoped |
| `SqlAlchemyDependencyRepository` | Subquery on `TaskORM.project_id` | **CRITICAL** | No org filter |
| `SqlAlchemyBaselineRepository` | `project_id` FK only | **CRITICAL** | All methods unscoped; approved baseline data exposed |
| `SqlAlchemyTaskCommentRepository` | `task_id` FK only | **CRITICAL** | Fully unscoped; bare `get(pk)` |
| `SqlAlchemyCostRepository` | `project_id` FK only | **CRITICAL** | Financial cost items fully unscoped |
| `SqlAlchemyCalendarEventRepository` | Date range only | **CRITICAL** | `list_range()` returns ALL events across all orgs globally |
| `SqlAlchemyRegisterEntryRepository` | Optional `project_id` | **CRITICAL** | Defaults to ALL entries globally when `project_id` is None |
| `SqlAlchemyPurchaseRequisitionLineRepository` | `requisition_id` FK only | **CRITICAL** | Financial procurement lines fully unscoped |
| `SqlAlchemyPurchaseOrderLineRepository` | parent FK only | **CRITICAL** | PO line pricing data fully unscoped |
| `SqlAlchemyReceiptLineRepository` | `receipt_header_id` FK only | **CRITICAL** | Unscoped receipt lines |
| `SqlAlchemyTimeEntryRepository` | `work_allocation_id` FK only | **CRITICAL** | Billable time data fully unscoped |
| `SqlAlchemyTimesheetPeriodRepository` | `resource_id` only; `list_review_candidates()` unscoped | **CRITICAL** | `list_review_candidates()` returns all timesheet periods globally |
| `SqlAlchemyUserRepository` | None | **CRITICAL** | `list_all()` returns ALL user accounts globally |
| `SqlAlchemyPortfolioIntakeRepository` | `list_for_organization` + `get_for_organization` | High | Bare `get(pk)` has no org check |
| `SqlAlchemyPortfolioScenarioRepository` | `list_for_organization` + `get_for_organization` | High | Bare `get(pk)` has no org check |
| `SqlAlchemyResourceRepository` | `list_for_organization` + `get_for_organization` | High | `list_by_employee()` has no org filter |
| `SqlAlchemyDepartmentRepository` | `list_for_organization(org_id)` | High | Bare `get(pk)` unscoped |
| `SqlAlchemyEmployeeRepository` | JOIN on `SiteORM` or `DepartmentORM` | High | Org scope is indirect and fragile; breaks for org-less employees |
| `SqlAlchemySiteRepository` | `list_for_organization(org_id)` | High | Bare `get(pk)` unscoped |
| `SqlAlchemyAuditLogRepository` | Dual methods (scoped + unscoped coexist) | High | Easy to accidentally call the unscoped one |
| `SqlAlchemyApprovalRepository` | Dual methods (scoped + unscoped coexist) | High | Same dual-method problem as audit log |
| `SqlAlchemyScopedAccessGrantRepository` | `user_id` only | High | `list_by_user()` returns grants for ALL orgs |
| `SqlAlchemyRuntimeExecutionRepository` | `module_code`/`status` only | High | Exposes cross-org operation metadata and output paths |
| `SqlAlchemyModuleEntitlementRepository` | `organization_id` via provider | High | Dual global/org API; global `get()` silently returns None |
| All Maintenance Repositories (25+) | `list_for_organization(org_id)` | High | Every bare `get(pk)` is unscoped |

---

## 5. Service Risk Map

| Service | Risk | Gap |
|---|---|---|
| `TaskService` (`project_management/application/tasks/service.py`) | **HIGH** | No `TenantContext` or `organization_id` anywhere; task domain model has no org field |
| `RegisterService` (`project_management/application/risk/register_service.py`) | **HIGH** | No `TenantContext` or `organization_id`; risk register entries unscoped |
| `CalendarAssignmentService` | **HIGH** | No `TenantContext`; can assign any calendar to any entity across org boundaries |
| `CalendarExceptionService` | **HIGH** | No `TenantContext`; exceptions can be added to any org's calendar |
| `WorkingRuleService` | **HIGH** | No `TenantContext`; rules can be written to any org's calendar |
| `RecurringEventService` | **HIGH** | No `TenantContext`; events can be added to any org's calendar |
| `TimesheetService` | Medium | `TimesheetEntriesMixin`: `add_work_entry()` — no org guard, no org stamp on `TimeEntry` |
| `CollaborationService` | Medium | Comments and presence records not org-stamped; could leak if `project_id` is known cross-org |
| `MaintenanceLaborAdapters` | Medium | Uses `get_active_organization_id()` not `require_active_organization_id()` — silent None on missing context |
| `ExportRuntime` | Medium | Org isolation depends entirely on individual export handler implementations |
| `CsvImportRuntime` | Medium | Cross-org import contamination possible if handlers lack org scoping |
| All Inventory services | Low | Correctly scoped via `require_context()` + org stamp |
| All Maintenance services | Low | Correctly scoped via `require_context()` + org stamp |
| All core Platform services (Approval, Audit, Dept, Document, Party, Site) | Low | Correctly scoped |

---

## 6. Controller / QML Risk Map

| Controller / Component | Risk | Gap |
|---|---|---|
| `PlatformRuntimeDesktopApi` (`src/api/desktop/platform/runtime.py`) | **CRITICAL** | `set_active_organization()` callable from any presenter with no API-layer permission check |
| `PlatformOrganizationController` (`controllers/admin/organization_controller.py`) | **CRITICAL** | `setActiveOrganization()` raw QML `Slot` with no guard; any QML code with controller reference can switch org context |
| `PlatformOrganizationCatalogPresenter` | **CRITICAL** | `build_catalog()` lists all orgs including inactive; no caller-identity check on `set_active_organization()` |
| `AdminConsolePage.qml` | High | Two `setActiveOrganization(adminState.selectedRowId)` call sites; raw UUID passed directly to backend |
| `AdminEntityDetailPanel.qml` | High | 'Activate' button directly triggers org switch with no client-side role check |
| `PlatformAdminWorkspaceController` | High | Re-exposes `setActiveOrganization()` at admin console level |
| `ProjectManagementWorkspaceCatalog` | Medium | `_active_organization_id()` duck-typed `snapshot()` call; silently returns `None` on failure |
| `AppSettingsStore` (`src/infra/platform/app_settings.py`) | Medium | `_tenant_key()` falls back to bare key on None `org_id`; all tenant-keyed settings collapse into shared global namespace |
| `TaskViewStore` | Medium | Falls back to global unscoped QSettings key `task/saved_views` when `org_id` is None |

---

## 7. Migration Plan (Ordered Steps)

### Phase A — Immediate Integrity Fixes (No Tenant Model Yet)

1. **Fix migration chain conflict** — Resolve duplicate `p9q0r1s2t3u4` filename; run `alembic check` + `alembic history` to validate chain
2. **Make nullable `organization_id` NOT NULL** on `projects`, `resources`, `approval_requests`, `audit_logs`
3. **Add `organization_id` to `employees`** — backfill from `site.organization_id`; add index
4. **Add `organization_id` to `time_entries`** — backfill via `work_allocation_id → project → organization_id`
5. **Add `organization_id` to `timesheet_periods`** — backfill via `resource_id → resources.organization_id`
6. **Fix empty-org-access-grants security bypass** — change `has_organization_access()` so zero grants = zero access; add `is_platform_admin()` check
7. **Add `organization_id` to `user_roles`** — nullable, NULL = global/platform role; add org-scoped role query support

### Phase B — Tenant Model Introduction

8. **Create `tenants` table** — `id`, `tenant_code` (UNIQUE), `display_name`, `is_active`, `plan_tier`, `created_at`, `version`; create `TenantORM` + `Tenant` domain model
9. **Add `tenant_id` to `organizations`** — add column NULLABLE, create default tenant, backfill all orgs, make NOT NULL, add index
10. **Add `tenant_id` to all `tenant_root` tables** — see full list in §3; backfill via `organization_id → organizations.tenant_id`; add indexes
11. **Re-key `organization_module_entitlements`** — change PK from `(organization_id, module_code)` to `(tenant_id, module_code)`
12. **Add `tenant_id` to `scoped_access_grants`** — backfill from referenced scope entity's org → tenant chain
13. **Add `organization_id` to `project_memberships`** — backfill via `project_id → projects.organization_id`
14. **Add `last_active_tenant_id` + `last_active_organization_id` to `auth_sessions`** — eliminate non-deterministic login org selection
15. **Add composite indexes** — `(tenant_id, organization_id, <date>)` on high-volume tables

### Phase C — Schema Hardening

16. **Apply NOT NULL constraints** — promote all `tenant_id` columns; remove nullable intermediate columns
17. **Add Row Level Security** (optional) — PostgreSQL RLS policies as defense-in-depth

---

## 8. Files That Must Change

### NEW Files
- `src/core/platform/tenancy/domain/tenant.py` — `Tenant` domain dataclass
- `src/core/platform/infrastructure/persistence/orm/tenant.py` — `TenantORM`

### Core Domain Models
- `src/core/platform/tenancy/tenant_context.py` — Add `tenant_id`/`Tenant`; separate `require_tenant_context()` from `require_organization_context()`
- `src/core/platform/auth/domain/session.py` — Fix empty-set bypass; add `is_platform_admin()`; carry `active_tenant_id` in principal
- `src/core/platform/auth/domain/user.py` — Add optional `organization_id` to `UserRoleBinding`
- `src/core/platform/access/domain/access_scope.py` — `ScopedAccessGrant` + `ProjectMembership` gain `tenant_id` / `organization_id`
- Task, RegisterEntry, TimeEntry domain models — Add `organization_id` field

### ORM Models
- `src/core/platform/infrastructure/persistence/orm/org.py` — Add `tenant_id` column + FK
- `src/core/platform/infrastructure/persistence/orm/employee.py` — Add `organization_id` + `tenant_id`
- `src/core/platform/infrastructure/persistence/orm/time.py` — Add `organization_id` + `tenant_id` to `TimeEntryORM` + `TimesheetPeriodORM`
- `src/core/platform/infrastructure/persistence/orm/auth.py` — Add `organization_id` to `UserRoleORM`; add tenant/org to `AuthSessionORM`
- `src/core/platform/infrastructure/persistence/orm/access.py` — Add `tenant_id` to `ScopedAccessGrantORM`; `organization_id` to `ProjectMembershipORM`
- `src/core/platform/infrastructure/persistence/orm/modules.py` — Replace `organization_id` PK component with `tenant_id`
- All 45 `tenant_root` ORM files — Add `tenant_id` column

### Repository Contracts
- All repository abstract bases — Add `get_scoped(pk, organization_id)` or `get_for_tenant(pk, tenant_id)`; deprecate bare `get(pk)` on business-data contracts
- `src/core/platform/modules/contracts.py` — Remove dual global/org API; collapse to tenant-scoped only

### Repository Implementations (80+)
- Add `tenant_id` predicate to every `list_*` method
- Replace bare `session.get(pk)` with scoped queries
- Special fixes: `SqlAlchemyCalendarEventRepository.list_range()`, `SqlAlchemyRegisterEntryRepository.list_entries()`, `SqlAlchemyTimesheetPeriodRepository.list_review_candidates()`

### Services
- `TaskService` — Add `TenantContextService`; guard all task operations; stamp `organization_id` on create
- `RegisterService` — Same as TaskService
- `CalendarAssignmentService`, `CalendarExceptionService`, `WorkingRuleService`, `RecurringEventService` — Add `TenantContextService`; validate cross-entity org ownership
- `TimesheetService` / `TimeService` — Fix `TimesheetEntriesMixin`: add org guard + stamp on `add_work_entry()`
- `CollaborationService` — Add org stamp to comment and presence creates
- `principal_builder.py` — Filter `scoped_access_grants` by active tenant at login
- `registration_service.py` — Require explicit `tenant_id`/`organization_id` at user registration

### Controllers / API
- `src/api/desktop/platform/runtime.py` — Add permission check to `set_active_organization()` at API adapter layer
- `src/core/platform/tenancy/tenant_context.py` — Update `TenantContextService` to resolve `Tenant` + `Organization`; persist to session

### QML / Presenters
- `src/ui_qml/platform/controllers/admin/organization_controller.py` — Add permission guard before `setActiveOrganization()`
- `src/ui_qml/platform/presenters/organization_catalog_presenter.py` — Add authorization check
- `src/ui_qml/modules/project_management/context.py` — Replace `snapshot()` duck-type with typed API method
- `src/infra/platform/app_settings.py` — Require non-None `org_id` in `_tenant_key()`; add dedicated `_global_key()` method

---

## 9. Remaining Risks After Implementation

| Risk | Severity | Description |
|---|---|---|
| Global admin bypass | High | `if "admin" in principal.role_names: return True` crosses all tenant boundaries; requires `platform_admin` vs `tenant_admin` role split |
| ExportRuntime / CsvImportRuntime unscoped at framework level | Medium | Any new handler added in future will be unscoped by default |
| SchedulingEngine is tenant-agnostic | Medium | If caller assembles graph from mixed-tenant data, engine computes cross-tenant schedules silently |
| Backfill integrity for employees and time entries | High | Employees with no site_id cannot be deterministically backfilled; pre-migration data audit required |
| Multi-session conflict on `last_active_organization_id` | Medium | Two concurrent sessions writing to shared `auth_sessions` row; add `active_org_session_revision` counter |
| UI modules don't react to org-switch events | Medium | Inventory/Maintenance workspaces hold no runtime API reference; data goes stale after org switch |
| `project_memberships` cross-org visibility | High | Until Step 13, users carry all project permissions across all orgs simultaneously |
| Unique constraints using `organization_id` | High | Many `UNIQUE(organization_id, <code>)` constraints must be re-evaluated for tenant vs org scope |
| `maintenance_sensor_readings` high-volume migration | High | Table rewrite required; must use multi-step online migration in production |
| Alembic chain complexity | Medium | Existing duplicate filename collision must be resolved before adding 15+ new migrations |
