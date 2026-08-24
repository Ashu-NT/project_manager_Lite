# Architecture README

Project Manager Lite — Enterprise Architecture Reference

> **Scope correction (2026-08-20):** Maintenance is no longer a current product module. Any
> Maintenance roles, permissions, services, QML, or tables described below are historical audit
> or retained migration-schema context, not current runtime composition.

---

## Table of Contents

1. [Current Architecture Overview](#1-current-architecture-overview)
2. [Tenant Architecture](#2-tenant-architecture)
3. [Organization Architecture](#3-organization-architecture)
4. [Authentication](#4-authentication)
5. [Authorization](#5-authorization)
6. [RBAC](#6-rbac)
7. [Tenant Context](#7-tenant-context)
8. [Repository Scoping](#8-repository-scoping)
9. [Current Risks](#9-current-risks)
10. [Current Gaps](#10-current-gaps)

---

## 1. Current Architecture Overview

### 1.1 Summary

Project Manager Lite is a layered desktop application. The frontend is written in QML (PySide6/Qt), the backend is pure Python, persistence is managed by SQLAlchemy 2 ORM, and schema evolution is handled by Alembic migrations. The application runs as a single process with a local SQLite database. `src/api/desktop` is the only supported delivery adapter; the dormant HTTP placeholder was removed after a dependency audit. A future server mode requires a new request-scoped transport design.

The codebase is organized into four top-level source areas:

```
src/
  api/               # Delivery adapters
  |  desktop/        #   Desktop Qt bridge (QML ↔ Python)
  application/       # Cross-cutting application services and runtime orchestration
  core/              # Domain and application logic (no framework dependencies)
  |  platform/       #   Platform layer: tenancy, auth, org, access, calendar, ...
  |  modules/        #   Business modules: PM, inventory, maintenance, payroll, QHSE, HR
  |  shared/         #   Shared utilities: audit, activity, cache, events, security
  infra/             # Infrastructure: ORM, DB engine, Alembic, composition/DI
  |  composition/    #   Dependency injection container and service registries
  |  config/         #   Runtime configuration
  |  persistence/    #   SQLAlchemy ORM models, DB engine, Alembic migrations
  |  platform/       #   OS-level platform helpers (paths, logging, versioning)
  ui_qml/            # QML frontend
  |  platform/       #   Auth, org, admin console, settings QML
  |  modules/        #   Module-specific QML screens
  |  shell/          #   App shell (nav, workspace, notifications)
  |  shared/         #   Design system components
```

### 1.2 Layered Architecture

```
+------------------------------------------------------------------+
|  QML FRONTEND  (ui_qml/)                                         |
|  Screens, dialogs, design-system components, QML models          |
+------------------------------------------------------------------+
|  DESKTOP API BRIDGE  (api/desktop/)                              |
|  Python QObject controllers exposed to QML via setContextProperty|
+------------------------------------------------------------------+
|  APPLICATION SERVICES  (application/, core/platform/, core/modules/) |
|  AuthService, OrganizationService, TenantContextService,         |
|  ProjectService, InventoryService, MaintenanceWorkOrderService,  |
|  AccessControlService, ...                                       |
+------------------------------------------------------------------+
|  DOMAIN  (core/*/domain/)                                        |
|  Pure Python domain objects, value objects, domain events        |
+------------------------------------------------------------------+
|  REPOSITORY CONTRACTS  (core/*/contracts.py)                     |
|  Abstract repository interfaces (Protocol / ABC)                 |
+------------------------------------------------------------------+
|  INFRASTRUCTURE  (infra/persistence/)                            |
|  SQLAlchemy ORM, Alembic migrations, concrete repositories       |
+------------------------------------------------------------------+
|  COMPOSITION / DI  (infra/composition/)                          |
|  AppContainer, PlatformRegistry, ProjectRegistry, ...            |
+------------------------------------------------------------------+
|  DATABASE  (SQLite, single file per deployment)                  |
+------------------------------------------------------------------+
```

### 1.3 Platform Layer Components

| Sub-package | Responsibility |
|---|---|
| `platform/tenancy` | `TenantContextService`, `TenantContext` dataclass, `TenantRepository` contract |
| `platform/auth` | `AuthService`, session management, password/MFA, RBAC, SoD |
| `platform/authorization` | `SessionAuthorizationEngine`, `@requires_permission` decorator |
| `platform/org` | `OrganizationService`, `OrganizationRepository` |
| `platform/access` | `AccessControlService`, `ScopedAccessGrant`, `ProjectMembership` |
| `platform/site` | `SiteService` |
| `platform/department` | `DepartmentService` |
| `platform/employee` | `EmployeeService` |
| `platform/calendar` | Platform calendar engine, working rules, shift patterns |
| `platform/modules` | `ModuleCatalogService`, `organization_module_entitlements` |
| `platform/audit` | `EnterpriseAuditService`, `audit_entries` |
| `platform/activity` | `ActivityService`, `activity_entries` |
| `platform/approval` | `ApprovalService`, `approval_requests` |
| `platform/documents` | `DocumentService`, `documents`, `document_structures` |

### 1.4 Business Modules

| Module package | Key services |
|---|---|
| `modules/project_management` | ProjectService, TaskService, ResourceService, BaselineService, RegisterService, PortfolioService, FinancialsService |
| `modules/inventory_procurement` | ItemCategoryService, ItemMasterService, InventoryService, ProcurementService, PurchasingService |
| `modules/maintenance` | MaintenanceAssetService, MaintenanceWorkOrderService, MaintenancePreventivePlanService, MaintenanceSensorService |
| `modules/payroll` | PayrollService |
| `modules/hr_management` | HR services |
| `modules/qhse` | QHSE services |

### 1.5 Infrastructure Components

| Component | Location | Notes |
|---|---|---|
| SQLAlchemy Base | `infra/persistence/orm/base.py` | `declarative_base()` shared by all ORM models |
| DB Engine | `infra/persistence/db/engine.py` | SQLite engine, WAL mode |
| Session Factory | `infra/persistence/db/session_factory.py` | Scoped session per request |
| Optimistic locking | `infra/persistence/db/optimistic.py` | `version` column check |
| Alembic migrations | `infra/persistence/migrations/` | Linear migration chain |
| AppContainer | `infra/composition/app_container.py` | Top-level DI root |
| Platform/module registries | `infra/composition/*_registry.py` | Service factory per domain |

---

## 2. Tenant Architecture

### 2.1 Overview

The application implements a **column-based multi-tenant data isolation** model. Every row of business data is tagged with `tenant_id` (and usually `organization_id`) at write time. At read time repositories inject a `WHERE tenant_id = :active_tenant_id` clause. The mechanism is not a schema-per-tenant or database-per-tenant design; all tenants share a single SQLite file in the current desktop deployment.

The current code is **designed for multi-tenancy** but **deployed in single-tenant desktop mode**. There is exactly one tenant in the database (created by `bootstrap_defaults()`), and the context service falls back to `get_default()` when no session tenant is set, so the single-tenant desktop workflow does not break.

### 2.2 Tenant Hierarchy

```
Tenant (tenants)
  |__ tenant_code UNIQUE, display_name, is_active, version
  |
  +-- Organization (organizations)
  |     tenant_id FK NOT NULL
  |     organization_code UNIQUE per tenant (not enforced by DB — application layer only)
  |
  +----+-- Site (sites)
       |     tenant_id, organization_id FK NOT NULL
       |
       +----+-- Department (departments)
            |     tenant_id, organization_id FK NOT NULL, site_id nullable
            |     parent_department_id (self-ref hierarchy)
            |
            +----+-- Employee (employees)
                 |     tenant_id, organization_id, site_id, department_id
                 |
                 +-- Business data
                       (projects, resources, assets, stock items, work orders, ...)
                       tenant_id + organization_id on root tables,
                       inherited through FK chain on child tables
```

### 2.3 Tenant Model

```python
# tenants table
class TenantORM(Base):
    id: Mapped[str]            # UUID PK
    tenant_code: Mapped[str]   # UNIQUE — business identifier
    display_name: Mapped[str]
    is_active: Mapped[bool]
    version: Mapped[int]       # optimistic lock
```

The `tenant_code` column carries a `UNIQUE` constraint enforced at the database level. This is the public-facing identifier (e.g., `"acme"`, `"globex"`). The internal `id` (UUID) is used in all foreign keys.

### 2.4 Tenant-Root Tables (direct `tenant_id` column, 37 tables)

These tables carry `tenant_id` as a direct NOT-NULL (post-migration) foreign key to `tenants.id`:

| Domain | Tables |
|---|---|
| Platform | `organizations`, `employees`, `sites`, `departments`, `parties`, `approval_requests`, `document_structures`, `documents`, `organization_module_entitlements`, `platform_calendars`, `shift_patterns`, `time_entries`, `timesheet_periods`, `activity_entries`, `audit_entries`, `scoped_access_grants` |
| Project Management | `projects`, `resources`, `portfolio_scoring_templates`, `portfolio_intake_items`, `portfolio_scenarios` |
| Maintenance | `maintenance_locations`, `maintenance_systems`, `maintenance_assets`, `maintenance_sensors`, `maintenance_work_requests`, `maintenance_work_orders`, `maintenance_preventive_plans` |
| Inventory | `inventory_item_categories`, `inventory_stock_items`, `inventory_storerooms`, `inventory_stock_balances`, `inventory_stock_transactions`, `inventory_stock_reservations`, `inventory_purchase_requisitions`, `inventory_purchase_orders`, `inventory_receipt_headers` |

### 2.5 Scope-Inherited Tables

These tables carry no direct `tenant_id`; isolation is achieved through FK chains anchored to a tenant-root parent:

```
tasks → projects.tenant_id
task_assignments → tasks → projects.tenant_id
task_dependencies → tasks → projects.tenant_id
task_comments, task_presence → tasks → projects.tenant_id
task_skill_requirements → tasks → projects.tenant_id
project_resources → projects.tenant_id
project_baselines → projects.tenant_id
baseline_tasks → project_baselines → projects.tenant_id
baseline_variance_records.project_id → (plain String, no FK — see risks)
cost_items → projects.tenant_id
register_entries → projects.tenant_id
calendar_events → projects.tenant_id (optional)
resource_skills, resource_certifications → resources.tenant_id
resource_calendar_assignments → resources.tenant_id
project_calendar_assignments → projects.tenant_id
portfolio_project_dependencies → projects.tenant_id

maintenance_work_order_tasks → maintenance_work_orders.tenant_id
maintenance_work_order_task_steps → maintenance_work_orders.tenant_id
maintenance_work_order_material_requirements → maintenance_work_orders.tenant_id
maintenance_task_templates → organization_id only
maintenance_preventive_plan_tasks → maintenance_preventive_plans.tenant_id
maintenance_preventive_plan_instances → organization_id only
maintenance_asset_components → organization_id only (ANOMALY — siblings have tenant_id)
maintenance_sensor_readings → organization_id only
maintenance_failure_codes → organization_id only
maintenance_downtime_events → organization_id only

inventory_storage_locations → organization_id only
inventory_reorder_policies → organization_id only
inventory_cycle_counts → organization_id only
inventory_purchase_requisition_lines → purchase_requisitions.tenant_id
inventory_purchase_order_lines → purchase_orders.tenant_id
inventory_receipt_lines → receipt_headers.tenant_id

calendar_working_rules, calendar_exceptions, calendar_recurring_events → platform_calendars.tenant_id
shift_pattern_days → shift_patterns.tenant_id
site_calendar_assignments → sites.tenant_id
department_calendar_assignments → departments.tenant_id
employee_calendar_assignments → employees.tenant_id

document_links → organization_id only
```

### 2.6 Platform-Global Tables (no tenant isolation)

These tables exist outside the tenant boundary and are shared across all tenants:

- `users` — global user registry, username UNIQUE globally
- `roles` — system role definitions
- `permissions` — permission code catalog
- `role_permissions` — role-to-permission assignments
- `auth_sessions` — session metadata (contains `last_active_tenant_id` as snapshot, not isolation column)
- `runtime_executions` — async execution tracking

### 2.7 Tenant Isolation Mechanisms

#### Write-time Stamping (`_stamp_scope`)

Every repository's `add()` method calls `_stamp_scope(ctx, orm)` before inserting. This method:

1. Checks `hasattr(orm, "organization_id")` — if present and NULL, sets it from `ctx.organization_id`.
2. Checks `hasattr(orm, "tenant_id")` — if present and NULL, sets it from `ctx.tenant_id`.
3. If either field is already set but does not match the active context, raises `BusinessRuleError(ORGANIZATION_SCOPE_VIOLATION / TENANT_SCOPE_VIOLATION)`.

#### Read-time Scoping (`_apply_scope`)

`_apply_scope(stmt, orm_model, ctx)` adds WHERE clauses to every SELECT:

```python
# From ProjectManagementTenantScopedRepositorySupport
organization_column = getattr(orm_model, "organization_id", None)
if organization_column is not None:
    stmt = stmt.where(organization_column == ctx.organization_id)
tenant_column = getattr(orm_model, "tenant_id", None)
if tenant_column is not None and ctx.tenant_id is not None:
    stmt = stmt.where(tenant_column == ctx.tenant_id)
```

`getattr(orm_model, ...)` is runtime introspection on the ORM class — if the column does not exist, the filter is silently omitted (see Risks, Section 9).

#### Context Prerequisite (`_context`)

Before any scoped operation, repositories call:

```python
ctx = self._tenant_context_service.require_organization_context(operation_label=...)
```

This raises `TENANT_CONTEXT_REQUIRED` if no active tenant or organization is set.

### 2.8 Single-Tenant Desktop vs Multi-Tenant Aspiration

In the current desktop deployment:

- `bootstrap_defaults()` creates exactly one tenant row.
- `TenantContextService.get_active_tenant()` falls back to `_tenant_repo.get_default()` when no session tenant ID is set.
- All data is owned by this single tenant.
- There is no API to create additional tenants, no tenant switcher UI, and no `user_tenants` membership table.

The architecture anticipates multi-tenancy (the column structure, context service, and isolation logic are all in place) but the management plane has not been built.

---

## 3. Organization Architecture

### 3.1 ORM Model

```
organizations table
  id               UUID PK
  tenant_id        FK → tenants.id RESTRICT nullable
  organization_code  VARCHAR UNIQUE (DB-level)
  display_name     VARCHAR
  timezone_name    VARCHAR
  base_currency    VARCHAR
  is_active        BOOLEAN
  version          INTEGER (optimistic lock)
```

### 3.2 Organization Hierarchy

```
Organization (organizations)
  |
  +-- Site (sites)          organization_id FK NOT NULL
  |     |
  |     +-- Department (departments)   organization_id FK NOT NULL, site_id nullable
  |           |
  |           +-- Employee (employees)   organization_id, site_id, department_id
  |
  +-- Resource (resources)     organization_id FK NOT NULL
  +-- Project (projects)       organization_id FK NOT NULL
  +-- MaintenanceAsset (...)   organization_id FK NOT NULL
  +-- StockItem (...)          organization_id FK NOT NULL
  +-- ... all other domain entities
```

### 3.3 OrganizationService

Located at `src/core/platform/org/application/organization_service.py`.

| Method | Permission required | Behavior |
|---|---|---|
| `bootstrap_defaults()` | None | Seeds a default org if none exist; called on first run |
| `list_organizations(active_only)` | `settings.manage` | Returns all orgs; no tenant scoping applied |
| `get_active_organization()` | `settings.manage` | Returns the single `is_active=True` org; bootstraps if missing |
| `create_organization(...)` | `settings.manage` | Creates org; calls `_deactivate_other_organizations()` before insert |
| `update_organization(...)` | `settings.manage` | Updates org; calls `_deactivate_other_organizations()` if activating |
| `set_active_organization(organization_id)` | `settings.manage` | Marks one org active, deactivates all others; updates session context |

#### CRITICAL BUG: `_deactivate_other_organizations()` Is Not Tenant-Scoped

```python
def _deactivate_other_organizations(self, *, exclude_id: str | None) -> None:
    for organization in self._organization_repo.list_all(active_only=True):
        if exclude_id and organization.id == exclude_id:
            continue
        organization.is_active = False
        self._organization_repo.update(organization)
```

`list_all()` is not filtered by tenant. In a multi-tenant deployment, activating an organization in Tenant A would deactivate all active organizations in Tenant B, C, etc. This is a cross-tenant data corruption bug.

### 3.4 Organization Context Resolution

```
UserSessionContext._active_organization_id
  ↓ if not set
UserSessionPrincipal.active_organization_id  (from last auth_session)
  ↓ if not set
auto-select: if principal has exactly one organization_id in scoped_access → return it
  ↓ otherwise
None
```

Resolution code in `UserSessionContext.active_organization_id()`:

```python
organization_ids = sorted(self.organization_ids())
return organization_ids[0] if len(organization_ids) == 1 else None
```

#### Bug: `get_active()` Is Unscoped

`OrganizationRepository.get_active()` returns the first org with `is_active=True` without filtering by tenant. In single-tenant mode this is harmless; in multi-tenant mode it returns whichever organization happens to be `is_active=True` across the entire database.

### 3.5 Single-Active Invariant

The system enforces a **single active organization per deployment** through `_deactivate_other_organizations()`. This is a desktop-mode design choice — the active organization is the workspace context for the current user session. The architecture does not currently support concurrent users working in different organizations within the same tenant.

### 3.6 Organization Switching via Admin Console

The Admin Console QML screen allows administrators to call `set_active_organization(organization_id)`. This:

1. Calls `OrganizationService.set_active_organization()`.
2. Which calls `_deactivate_other_organizations(exclude_id=organization_id)`.
3. Marks the target organization `is_active = True`.
4. Sets `user_session.set_active_organization_id(organization.id)`.
5. Emits `domain_events.organizations_changed`.

### 3.7 Module Entitlements

`organization_module_entitlements` (ORM: `ModuleEntitlementORM`) controls which modules are licensed and enabled per organization:

```
organization_module_entitlements
  organization_id  FK → organizations.id CASCADE (PK part)
  module_code      VARCHAR (PK part)
  tenant_id        FK → tenants.id CASCADE (non-PK, added in Phase 3 migration)
  licensed         BOOLEAN
  enabled          BOOLEAN
```

`ModuleCatalogService` reads these rows to gate access to module-level features.

---

## 4. Authentication

### 4.1 AuthService

`AuthService` (`src/core/platform/auth/application/auth_service.py`) is the top-level facade. It composes the following application-layer modules via import delegation:

| Delegate module | Responsibility |
|---|---|
| `authentication_service` | `authenticate()`, `authenticate_federated()`, `complete_successful_authentication()`, `register_failed_login()` |
| `session_service` | `validate_session_principal()`, `revoke_session()`, `revoke_user_sessions()`, `persist_session_context()` |
| `principal_builder` | `build_principal()` — assembles `UserSessionPrincipal` from DB state |
| `bootstrap_service` | `bootstrap_defaults()` — seeds permissions, roles, and initial admin user |
| `registration_service` | `register_user()` |
| `role_assignment_service` | `assign_roles()`, `remove_roles()` |
| `password_service` | `change_password()`, `reset_password()` |
| `mfa_service` | `enable_mfa()`, `disable_mfa()` |
| `user_admin_service` | `lock_user()`, `unlock_user()`, `deactivate_user()` |

### 4.2 Authentication Flow (`authenticate()`)

```
1. Normalize username to lowercase
2. Lookup user by username (global — no tenant filter)
3. If user not found or not active → raise ValidationError(AUTH_FAILED)
4. If locked_until expired → auto-clear lockout and save
5. If still locked → raise ValidationError(AUTH_LOCKED)
6. verify_password(raw_password, user.password_hash)
   → uses PBKDF2-SHA256 with 390,000 iterations
   → If fails: increment failed_login_attempts, apply lockout at threshold
7. If user.mfa_enabled → verify_totp_code(user.mfa_secret, mfa_code)
   → If code absent: raise AUTH_MFA_REQUIRED
   → If code wrong: raise AUTH_MFA_FAILED
8. complete_successful_authentication():
   a. Reset failed_login_attempts = 0, locked_until = None
   b. Update last_login_at, last_login_auth_method, last_login_device_label
   c. Set session_expires_at via next_session_expiry()
   d. Create AuthSession row (last_active_tenant/org restored from previous session)
   e. Update user.active_session_id = auth_session.id
   f. Commit
   g. Emit domain_events.auth_changed
   h. refresh_current_session_if_user() → rebuild and set UserSessionPrincipal
9. Return UserAccount domain object
```

Lockout thresholds are configurable via environment variables:
- `PM_AUTH_LOCKOUT_ATTEMPTS` (default: 5)
- `PM_AUTH_LOCKOUT_MINUTES` (default: 15)
- `PM_AUTH_SESSION_MINUTES` (default: 480, i.e., 8 hours)

### 4.3 UserSessionPrincipal

`UserSessionPrincipal` is a **frozen dataclass** (`@dataclass(frozen=True)`) stored on `UserSessionContext`. It is rebuilt on every login and re-validated by the session validator.

| Field | Type | Description |
|---|---|---|
| `user_id` | `str` | UUID of the authenticated user |
| `username` | `str` | Normalized lowercase username |
| `display_name` | `str \| None` | Human-readable name |
| `role_names` | `frozenset[str]` | Set of role name strings |
| `permissions` | `frozenset[str]` | Effective flat permission code set |
| `scoped_access` | `dict[str, dict[str, frozenset[str]]]` | `scope_type → scope_id → permission_codes` |
| `project_access` | `dict[str, frozenset[str]]` | Shortcut alias for `scoped_access["project"]` |
| `session_expires_at` | `datetime \| None` | UTC expiry from auth_session or user record |
| `must_change_password` | `bool` | Forces password-change gate |
| `session_revision` | `int` | Incremented on forced logout / password change |
| `identity_provider` | `str \| None` | Federated IdP identifier (e.g., `"azure_ad"`) |
| `last_login_auth_method` | `str \| None` | `"password"` or `"federated:<provider>"` |
| `session_id` | `str \| None` | FK to `auth_sessions.id` |
| `active_tenant_id` | `str \| None` | Restored from last auth_session |
| `active_organization_id` | `str \| None` | Restored from last auth_session |

### 4.4 Password Hashing

Located at `src/core/platform/auth/passwords.py`.

Algorithm: custom **PBKDF2-SHA256**, 390,000 iterations, 16-byte random salt, Base64-encoded.

Hash format: `pbkdf2_sha256$390000$<salt_b64>$<digest_b64>`

Both `pbkdf2_sha256` and `pbkdf2_sha512` schemes are supported for verification (for hash migration).

**Recommendation:** Migrate to **Argon2id** (via `argon2-cffi`). PBKDF2 is acceptable but Argon2id is the current NIST-recommended password hashing algorithm, providing memory-hardness that PBKDF2 lacks.

### 4.5 Multi-Factor Authentication

Located at `src/core/platform/auth/mfa.py`.

The TOTP implementation is complete in the backend:
- `generate_mfa_secret()` — produces a Base32-encoded HMAC-SHA1 secret
- `generate_totp_code(secret, at_time)` — standard TOTP RFC 6238
- `verify_totp_code(secret, code, allowed_drift_steps=1)` — validates with ±1 time step

**Status: Non-functional.** The authentication flow correctly calls `verify_totp_code()` when `user.mfa_enabled is True`. However, the QML login form never presents a TOTP input field, so no code is ever collected from the user. `mfa_code` is always `None`. If MFA is enabled for a user account, that account becomes permanently inaccessible through the UI.

### 4.6 Session Persistence

Auth sessions are stored in the `auth_sessions` table:

```
auth_sessions
  id                            UUID PK
  user_id                       FK → users.id CASCADE
  session_revision              INTEGER
  auth_method                   VARCHAR  ("password" | "federated:<provider>")
  device_label                  VARCHAR nullable
  last_active_tenant_id         FK → tenants.id SET NULL nullable
  last_active_organization_id   FK → organizations.id SET NULL nullable
  issued_at                     DATETIME UTC
  expires_at                    DATETIME UTC
  last_validated_at             DATETIME UTC
  revoked_at                    DATETIME UTC nullable
  created_at / updated_at       DATETIME UTC
```

`last_active_tenant_id` and `last_active_organization_id` are **last-known context snapshots**, not hard isolation boundaries. They are used to restore the user's workspace on next login.

### 4.7 Session Validation Throttle

`validate_session_principal()` (called on every principal access) touches `auth_sessions.last_validated_at` via `_touch_session_validation()`, but only if more than **60 seconds** have passed since the last touch. This throttle (`_SESSION_VALIDATION_THROTTLE_SECONDS = 60`) reduces DB writes for active sessions.

Validation checks (in order):
1. User still exists and is active.
2. User's `session_expires_at` has not passed.
3. AuthSession row exists and is not revoked.
4. `auth_session.session_revision` matches `user.session_revision` (detects forced logout).
5. `auth_session.expires_at` has not passed.

### 4.8 Bootstrap and First-Run Admin

`bootstrap_defaults()` (`src/core/platform/auth/application/bootstrap_service.py`):

1. `ensure_default_permissions()` — inserts all 56 permission codes from `DEFAULT_PERMISSIONS`.
2. `ensure_default_roles()` — inserts all 18 system roles.
3. `ensure_role_permissions()` — seeds `role_permissions` from `DEFAULT_ROLE_PERMISSIONS`.
4. Looks up or creates the bootstrap admin user.
   - Username from `PM_ADMIN_USERNAME` env var (default: `"admin"`).
   - Password from `PM_ADMIN_PASSWORD` env var (falls back to a generated secret printed to logs).
   - `must_change_password = True`.
   - Role: `admin`.

---

## 5. Authorization

### 5.1 Authorization Engine

The `SessionAuthorizationEngine` (`src/core/platform/authorization/application/session_authorization_engine.py`) is a singleton registered at module load:

```python
_authorization_engine: AuthorizationEngine = SessionAuthorizationEngine()
```

It is the only implementation of `AuthorizationEngine`. The engine reads all decisions from the in-memory `UserSessionContext` / `UserSessionPrincipal` — no additional DB queries are made at authorization time.

### 5.2 `require_permission()` — Flat Permission Check

```python
# src/core/platform/auth/authorization.py
def require_permission(
    user_session: UserSessionContext | None,
    permission_code: str,
    *,
    operation_label: str,
) -> None:
    engine = get_authorization_engine()
    if engine.has_permission(user_session, permission_code):
        return
    raise BusinessRuleError(
        f"Permission denied for {operation_label}. Missing '{permission_code}'.",
        code="PERMISSION_DENIED",
    )
```

Used in service methods as the first guard:

```python
require_permission(self._user_session, "project.manage", operation_label="create project")
```

`require_any_permission()` is also available; it raises if none of the given codes are present.

### 5.3 `@requires_permission` Decorator

Located in `src/core/platform/authorization/`. Wraps service methods to enforce permission checks declaratively. Used primarily in the HTTP API layer.

### 5.4 `require_scope_permission()` — Scoped Check

Scoped authorization is evaluated through `UserSessionContext.has_scope_permission(scope_type, scope_id, permission_code)`:

```
1. If no principal → False
2. If principal has "admin" role → True (admin bypasses all scope restrictions)
3. If permission_code not in principal.permissions → False (flat check must pass first)
4. Look up scope_rows = principal.scoped_access[scope_type]
5. If scope_rows is empty → True (user has no scope restrictions for this type)
6. Return permission_code in scope_rows[scope_id]
```

Step 5 is significant: a user with no scoped_access entries for a given scope_type is treated as unrestricted for that scope type. Scope restrictions only activate when at least one entry exists.

### 5.5 `is_admin_session()` — Admin Bypass

```python
def is_admin_session(user_session: UserSessionContext | None) -> bool:
    return get_authorization_engine().is_admin_session(user_session)

# In SessionAuthorizationEngine:
def is_admin_session(self, user_session):
    principal = user_session.principal if user_session is not None else None
    return bool(principal is not None and "admin" in principal.role_names)
```

A session with the `admin` role bypasses all permission checks and all scope restrictions. This is the only `superuser` mechanism in the system.

### 5.6 `is_platform_admin()` — Dead Code

```python
# In UserSessionContext:
def is_platform_admin(self) -> bool:
    principal = self._active_principal()
    if principal is None:
        return False
    return "platform.admin" in principal.permissions
```

`"platform.admin"` is never seeded in `DEFAULT_PERMISSIONS` and is never assigned to any role. This method always returns `False` for all users. It exists as a placeholder for a future super-admin tier above the `admin` role.

### 5.7 SodEnforcer — SoD at Role Assignment Time

`enforce_separation_of_duties()` (`src/core/platform/auth/application/sod_enforcer.py`) is called by `role_assignment_service` when roles are assigned to a user:

```python
def enforce_separation_of_duties(service, role_names):
    if "admin" in normalized:
        return  # admin bypasses SoD entirely
    # compute effective permissions from all assigned roles
    # call sod_policy.find_conflicts(permission_codes)
    # raise ValidationError if conflict found
```

Two SoD rules are defined (see Section 6.5). The `admin` role bypass is intentional for superusers but creates a policy gap: an admin has all 56 permissions simultaneously, which by design violates both SoD rules, and the bypass makes this invisible.

**Proxy Bypass Vulnerability:** SoD is enforced only at role-assignment time, not at runtime. A user can be granted explicit permissions via `ScopedAccessGrant` that violate SoD rules without triggering `enforce_separation_of_duties()`. The enforcer inspects role-derived permissions only, not direct grants.

### 5.8 `authorization.py` vs `access/authorization.py`

There are two `authorization.py` files with different purposes:

| File | Purpose |
|---|---|
| `src/core/platform/auth/authorization.py` | Thin shim calling `get_authorization_engine()`. Used by all service methods. Exports `require_permission`, `require_any_permission`, `is_admin_session`. |
| `src/core/platform/access/authorization.py` | Contracts for the `AccessControlService` layer. Defines permission evaluation interfaces for scoped access grants and project memberships. |

---

## 6. RBAC

### 6.1 System Roles and Permissions

There are 18 system roles defined in `DEFAULT_ROLE_PERMISSIONS` (`src/core/platform/auth/policy.py`). They are seeded into the `roles` and `role_permissions` tables by `bootstrap_defaults()`. Roles are **platform-global** — there is no per-tenant or per-organization role customization.

#### Roles and their permission sets

| Role | Permissions |
|---|---|
| `viewer` | `organization.access`, `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `register.read`, `report.view`, `collaboration.read` |
| `team_member` | viewer + `collaboration.manage`, `timesheet.submit` |
| `planner` | team_member + `project.manage`, `task.manage`, `time.manage`, `baseline.manage`, `register.manage`, `report.export`, `portfolio.read`, `approval.request`, `import.manage` |
| `project_manager` | planner + `baseline.approve`, `cost.manage`, `finance.read`, `finance.export`, `timesheet.approve` |
| `resource_manager` | `project.read`, `task.read`, `time.read`, `resource.read`, `resource.manage`, `employee.read`, `employee.manage`, `site.read`, `department.read`, `report.view`, `report.export`, `collaboration.read`, `timesheet.approve`, `timesheet.lock` |
| `finance` | same as `finance_controller` (alias) |
| `finance_controller` | `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `cost.manage`, `party.read`, `register.read`, `report.view`, `report.export`, `finance.read`, `finance.manage`, `finance.export`, `payroll.read`, `approval.request` |
| `inventory_manager` | `inventory.read`, `inventory.manage`, `site.read`, `party.read`, `report.view`, `report.export`, `import.manage`, `approval.request` |
| `maintenance_manager` | `maintenance.read`, `maintenance.manage`, `time.read`, `time.manage`, `site.read`, `employee.read`, `party.read`, `report.view`, `report.export`, `approval.request`, `import.manage` |
| `maintenance_admin` | same as `maintenance_manager` (alias) |
| `payroll_manager` | `project.read`, `task.read`, `time.read`, `resource.read`, `employee.read`, `employee.manage`, `site.read`, `department.read`, `report.view`, `payroll.read`, `payroll.manage`, `payroll.approve`, `payroll.export`, `timesheet.approve`, `timesheet.lock`, `audit.read` |
| `portfolio_manager` | `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `register.read`, `report.view`, `report.export`, `portfolio.read`, `portfolio.manage`, `collaboration.read`, `approval.request` |
| `approver` | `baseline.approve`, `project.read`, `resource.read`, `task.read`, `time.read`, `cost.read`, `register.read`, `report.view`, `portfolio.read`, `finance.read`, `payroll.read`, `approval.decide` |
| `auditor` | `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `finance.read`, `payroll.read`, `register.read`, `report.view`, `portfolio.read`, `collaboration.read`, `audit.read` |
| `access_admin` | `project.read`, `site.read`, `auth.read`, `access.manage`, `audit.read` |
| `security_admin` | `auth.read`, `audit.read`, `settings.manage`, `security.manage` |
| `support_admin` | `project.read`, `task.read`, `time.read`, `register.read`, `report.view`, `auth.read`, `audit.read`, `support.manage` |
| `admin` | All 56 permissions |

### 6.2 Permission Code Catalog (56 codes)

Grouped by domain:

| Domain | Permission codes |
|---|---|
| Project | `project.read`, `project.manage` |
| Task | `task.read`, `task.manage` |
| Time | `time.read`, `time.manage` |
| Resource | `resource.read`, `resource.manage` |
| Employee | `employee.read`, `employee.manage` |
| Inventory | `inventory.read`, `inventory.manage` |
| Maintenance | `maintenance.read`, `maintenance.manage` |
| Directory (read-only) | `site.read`, `department.read`, `party.read` |
| Cost | `cost.read`, `cost.manage` |
| Finance | `finance.read`, `finance.manage`, `finance.export` |
| Payroll | `payroll.read`, `payroll.manage`, `payroll.approve`, `payroll.export` |
| Baseline | `baseline.manage`, `baseline.approve` |
| Register | `register.read`, `register.manage` |
| Report | `report.view`, `report.export` |
| Portfolio | `portfolio.read`, `portfolio.manage` |
| Collaboration | `collaboration.read`, `collaboration.manage` |
| Timesheet | `timesheet.submit`, `timesheet.approve`, `timesheet.lock` |
| Audit | `audit.read` |
| Support | `support.manage` |
| Access control | `access.manage` |
| Import | `import.manage` |
| Approval | `approval.request`, `approval.decide` |
| Settings | `settings.manage` |
| Auth admin | `auth.read`, `auth.manage` |
| Security | `security.manage` |
| Org/Tenant | `organization.access` |

### 6.3 `user_roles` Table and Unique Constraint Bug

```
user_roles
  user_id         FK → users.id CASCADE
  role_id         FK → roles.id CASCADE
  organization_id FK → organizations.id CASCADE nullable
  UNIQUE (user_id, role_id)    ← BUG
```

**BUG:** The `UNIQUE` constraint is on `(user_id, role_id)` only. `organization_id` is not part of the unique key. This means a user can only hold each role once globally — it is impossible to assign the same role to a user in two different organizations. The intent of having an `organization_id` column is to scope role assignments per organization, but the constraint prevents that use case. The constraint should be `UNIQUE (user_id, role_id, organization_id)`.

### 6.4 `scoped_access_grants` Table

Provides polymorphic, fine-grained access grants beyond the role system:

```
scoped_access_grants
  id                    UUID PK
  tenant_id             FK → tenants.id CASCADE nullable
  scope_type            VARCHAR  (e.g., "project", "organization")
  scope_id              VARCHAR  (FK to the target entity by type)
  user_id               FK → users.id CASCADE
  scope_role            VARCHAR  (e.g., "viewer", "member", "manager")
  permission_codes_json TEXT     (JSON array of permission code strings)
```

Grants are loaded by `build_principal()` and merged into `UserSessionPrincipal.scoped_access`.

`tenant_id` is nullable — for non-organization scope types (e.g., project-level grants), `tenant_id` may be NULL. This is a medium-severity isolation gap; grants with NULL tenant_id are visible across tenant contexts.

### 6.5 `project_memberships` Table

Project-scoped access without going through `scoped_access_grants`:

```
project_memberships
  project_id      FK → projects.id CASCADE
  user_id         FK → users.id CASCADE
  organization_id FK → organizations.id SET NULL nullable
  scope_role      VARCHAR
  permission_codes_json TEXT
```

No direct `tenant_id` column. Tenant reachability is through `project → tenant_id`. In `build_principal()`, memberships are loaded as `scoped_access["project"]` when `scoped_access_repo` is not available.

### 6.6 Separation of Duties Rules

Defined in `src/core/platform/auth/sod.py`:

| Rule | Conflicting permissions | Rationale |
|---|---|---|
| Approval SoD | `approval.request` AND `approval.decide` | A user cannot both submit and approve governed change requests |
| Access/Security SoD | `access.manage` AND `security.manage` | A user cannot both manage project memberships and manage login security controls |

### 6.7 Missing Roles

The following roles are architecturally required for multi-tenant operation but do not exist:

| Missing role | Purpose |
|---|---|
| `tenant_admin` | Manage all organizations, users, and settings within a single tenant |
| `org_admin` | Manage users and settings within a single organization |
| `site_admin` | Manage resources and operations within a single site (no site-scoped mechanism exists) |
| `department_manager` | Manage employees and time within a single department |

Without `tenant_admin` and `org_admin`, the only privileged role is `admin` (superuser), creating an all-or-nothing privilege model.

### 6.8 Role Hierarchy Proposal

```
admin (superuser, all 56 permissions)
  |
  +-- tenant_admin (all org permissions within one tenant)
  |     |
  |     +-- org_admin (all permissions within one organization)
  |           |
  |           +-- site_admin (site-scoped subset)
  |           |
  |           +-- department_manager (department-scoped subset)
  |
  +-- project_manager → planner → team_member → viewer  (project/PM hierarchy)
  +-- finance_controller → approver  (finance hierarchy)
  +-- resource_manager  (HR/resource hierarchy)
  +-- inventory_manager  (supply chain)
  +-- maintenance_manager / maintenance_admin  (CMMS)
  +-- payroll_manager  (payroll, requires SoD separation from finance)
  +-- portfolio_manager  (strategic planning)
  +-- access_admin  (access governance)
  +-- security_admin  (identity/security governance, SoD with access_admin)
  +-- auditor  (read-only compliance)
  +-- support_admin  (operational support)
```

---

## 7. Tenant Context

### 7.1 TenantContextService

Located at `src/core/platform/tenancy/tenant_context.py`.

The service is session-scoped and injected into all repositories and services that need tenant-aware operations.

#### Full API

| Method | Return type | Behavior |
|---|---|---|
| `get_active_tenant_id()` | `str \| None` | Returns `get_active_tenant().id` or None |
| `require_active_tenant_id(operation_label)` | `str` | Raises `TENANT_CONTEXT_REQUIRED` if no active tenant |
| `get_active_tenant()` | `Tenant \| None` | See resolution chain below |
| `set_active_tenant(tenant_id)` | `Tenant` | Sets tenant on session; validates existence and is_active; no membership check |
| `get_active_organization_id()` | `str \| None` | Returns `get_active_organization().id` or None |
| `require_active_organization_id(operation_label)` | `str` | Raises if no active org |
| `get_active_organization()` | `Organization \| None` | See resolution chain below |
| `set_active_organization(organization_id)` | `Organization` | Sets org on session; validates existence, is_active, and `_can_access()` |
| `require_context(operation_label)` | `TenantContext` | Returns `TenantContext(tenant, organization)` or raises |
| `require_organization_context(operation_label)` | `TenantContext` | Requires both tenant and organization to be non-None |

#### Tenant Resolution Chain

```
get_active_tenant():
  1. _session_tenant_id()
     → UserSessionContext.active_tenant_id()
       → _active_tenant_id field (mutable session state)
       → principal.active_tenant_id (restored from auth_session)
  2. If found: lookup TenantRepository.get(tenant_id)
     → If not found or not is_active: fall through to step 3
  3. Fall back: TenantRepository.get_default()
     → Returns first active tenant in the database
```

#### Organization Resolution Chain

```
get_active_organization():
  1. _session_organization_id()
     → UserSessionContext.active_organization_id()
       → _active_organization_id field
       → principal.active_organization_id (restored from auth_session)
       → auto-select if exactly one org_id in principal.scoped_access["organization"]
  2. If found: lookup OrganizationRepository.get(organization_id)
     → Validate _can_access(organization_id)
     → If access denied: clear session org and return None
  3. Return None
```

### 7.2 UserSessionContext

Located at `src/core/platform/auth/domain/session.py`.

`UserSessionContext` is a **mutable** class (not frozen) that holds the live principal and active context IDs for the current user session. It is instantiated once per session and injected into all services.

#### Full API

| Method | Description |
|---|---|
| `set_principal(principal)` | Normalizes and stores the principal; restores active context from principal fields; notifies listener |
| `clear()` | Removes principal and clears both active IDs |
| `is_authenticated()` | Returns True if principal is active and not expired |
| `has_permission(code)` | Flat permission check on principal.permissions |
| `has_scope_permission(scope_type, scope_id, code)` | Scoped permission check (see Section 5.4) |
| `has_any_scope_access(scope_type, code)` | True if any scope_id grants the permission |
| `has_project_permission(project_id, code)` | Shortcut for project scope |
| `has_any_project_access(code)` | Shortcut for project scope |
| `scope_ids_for(scope_type, code)` | Set of scope_ids where code is granted |
| `project_ids_for(code)` | Shortcut for project scope |
| `organization_ids()` | Set of organization_ids in scoped_access |
| `has_organization_access(organization_id)` | True if user has access to the given org |
| `is_platform_admin()` | Checks for "platform.admin" in permissions (always False — dead code) |
| `set_active_tenant_id(tenant_id)` | Updates mutable session state and replaces principal field |
| `active_tenant_id()` | Returns resolved tenant ID (see chain above) |
| `stored_active_tenant_id()` | Returns raw `_active_tenant_id` without fallback |
| `set_active_organization_id(organization_id)` | Updates mutable session state |
| `active_organization_id()` | Returns resolved org ID (see chain above) |
| `stored_active_organization_id()` | Returns raw `_active_organization_id` without fallback |
| `is_scope_restricted(scope_type)` | True if any scoped_access entries exist for this type (admin always False) |
| `is_project_restricted()` | Shortcut for project scope |

### 7.3 Context Flow: Login → Session → Repositories

```
Login (authenticate())
  ↓
complete_successful_authentication()
  ↓ creates AuthSession row with last_active_tenant/org
  ↓
refresh_current_session_if_user()
  ↓
build_principal(service, user, session_id=...)
  ↓ reads:
  |  - user.id, username, display_name
  |  - get_user_role_names(user.id) → roles table
  |  - get_user_permissions(user.id) → role_permissions table
  |  - scoped_access_repo.list_by_user(user.id) → scoped_access_grants
  |  - auth_session.last_active_tenant_id, .last_active_organization_id
  ↓
UserSessionContext.set_principal(principal)
  ↓ _restore_active_context_from_principal()
  |  sets _active_tenant_id, _active_organization_id from principal
  ↓ notifies context_listener (triggers UI refresh)

At repository call time:
  service → requires_organization_context(operation_label)
    → TenantContextService.require_organization_context()
      → get_active_tenant() → get_active_organization()
      → returns TenantContext(tenant_id, organization_id)
  repository._apply_scope(stmt, orm_model, ctx)
    → WHERE organization_id = ctx.organization_id
    → WHERE tenant_id = ctx.tenant_id
```

### 7.4 Context Persistence

When the user switches tenant or organization, or on session heartbeat, `persist_session_context()` is called:

```python
auth_session_repo.persist_context(
    session_id,
    last_active_tenant_id=session.stored_active_tenant_id(),
    last_active_organization_id=session.stored_active_organization_id(),
    updated_at=now,
)
```

This writes the current active context back to `auth_sessions.last_active_tenant_id / last_active_organization_id`. On next login, `build_principal()` reads these fields and restores the workspace.

### 7.5 CRITICAL: No User-Tenant Membership Check in `set_active_tenant()`

```python
def set_active_tenant(self, tenant_id: str) -> Tenant:
    tenant = self._tenant_repo.get(normalized_id)
    if not tenant.is_active:
        raise BusinessRuleError(...)
    if self._user_session is not None:
        self._user_session.set_active_tenant_id(tenant.id)  # ← no membership check
    return tenant
```

Any authenticated user can call `set_active_tenant()` with any valid tenant UUID and immediately gain context within that tenant. There is no `user_tenants` table and no check that the user is a member of the target tenant. All subsequent repository queries will be scoped to that tenant, giving the user access to all data in it.

---

## 8. Repository Scoping

All scoped repositories inherit from `TenantScopedRepositorySupport` (base) and one of the module-specific mixins. Five distinct patterns are used:

### 8.1 Pattern A — Inline WHERE in `_base_stmt`

Some repositories build the tenant/org WHERE clauses directly into the base SELECT statement construction method, before returning the stmt to the caller.

```python
def _base_stmt(self):
    ctx = self._context(operation_label="list")
    return select(ProjectORM).where(
        ProjectORM.tenant_id == ctx.tenant_id,
        ProjectORM.organization_id == ctx.organization_id,
    )
```

This pattern guarantees the filter is always present in every query that builds on `_base_stmt`, but requires every calling method to use `_base_stmt()` as its root.

### 8.2 Pattern B — `_apply_scope` Runtime Introspection

```python
def _apply_scope(self, stmt, orm_model, ctx: TenantContext):
    organization_column = getattr(orm_model, "organization_id", None)
    if organization_column is not None:
        stmt = stmt.where(organization_column == ctx.organization_id)
    tenant_column = getattr(orm_model, "tenant_id", None)
    active_tenant_id = getattr(ctx, "tenant_id", None)
    if tenant_column is not None and active_tenant_id is not None:
        stmt = stmt.where(tenant_column == active_tenant_id)
    return stmt
```

`getattr(orm_model, "organization_id", None)` performs runtime class attribute lookup. If the ORM class has been misspelled or the column has been removed, `getattr` returns `None` and the filter is silently omitted — the query runs without scope isolation.

**Silent miss risk:** There is no assertion or test that the column actually exists on the model before relying on it for isolation. A typo in a column rename migration would silently break tenant isolation without raising an exception.

### 8.3 Pattern C — `_get_in_scope` / `_require_in_scope`

Point lookups (get by ID) use:

```python
def _get_in_scope(self, orm_model, record_id: str, *, operation_label: str):
    ctx = self._context(operation_label=operation_label)
    stmt = self._apply_scope(
        select(orm_model).where(orm_model.id == record_id),
        orm_model,
        ctx,
    )
    return self.session.execute(stmt).scalars().first()

def _require_in_scope(self, orm_model, record_id, *, operation_label, not_found_message):
    obj = self._get_in_scope(orm_model, record_id, operation_label=operation_label)
    if obj is None:
        raise NotFoundError(not_found_message)
    return obj
```

`_require_in_scope` returns a `NotFoundError` if the record does not exist **or** if it belongs to a different tenant/org. This is the correct behavior (no information leakage about existence), but callers cannot distinguish the two cases if they need to.

### 8.4 Pattern D — JOIN-Anchor `ProjectManagementParentScopedRepositorySupport`

For child tables that have no direct `organization_id` or `tenant_id` (scope-inherited tables), the scope is applied to the anchor parent via a JOIN:

```python
def _scoped_stmt_for_anchor(self, row_model, anchor_model, *, joins, operation_label):
    ctx = self._context(operation_label=operation_label)
    stmt = select(row_model)
    for join_model, on_clause in joins:
        stmt = stmt.join(join_model, on_clause)
    return self._apply_scope(stmt, anchor_model, ctx)  # scope applied to anchor_model
```

Example: querying `tasks` (no direct tenant_id) by scoping through `projects` (has tenant_id):

```python
stmt = self._scoped_stmt_for_anchor(
    TaskORM,
    ProjectORM,
    joins=((ProjectORM, TaskORM.project_id == ProjectORM.id),),
    operation_label="list tasks",
)
```

`_apply_scope` reads columns from `ProjectORM`, not `TaskORM`, correctly isolating via the parent's scope columns.

### 8.5 Pattern E — Guard Before Query

Some repositories check authorization or context validity as an explicit guard statement before building any query:

```python
def list_portfolios(self):
    ctx = self._context(operation_label="list portfolios")
    # explicit guard
    if ctx.organization_id is None:
        return []
    stmt = select(PortfolioORM).where(
        PortfolioORM.organization_id == ctx.organization_id
    )
    ...
```

### 8.6 Write-Time Stamping (`_stamp_scope`)

Called in `add()` before `session.add(orm)`:

```python
def _stamp_scope(self, ctx: TenantContext, orm: object) -> None:
    if hasattr(orm, "organization_id"):
        org_id = getattr(orm, "organization_id", None)
        if org_id is None or org_id == "":
            setattr(orm, "organization_id", ctx.organization_id)
        elif not self._organization_in_scope(ctx, org_id):
            raise BusinessRuleError(code="ORGANIZATION_SCOPE_VIOLATION")
    if hasattr(orm, "tenant_id"):
        active_tenant_id = getattr(ctx, "tenant_id", None)
        tenant_id = getattr(orm, "tenant_id", None)
        if tenant_id is None and active_tenant_id is not None:
            setattr(orm, "tenant_id", active_tenant_id)
        elif not self._tenant_in_scope(ctx, tenant_id):
            raise BusinessRuleError(code="TENANT_SCOPE_VIOLATION")
```

If `organization_id` or `tenant_id` is already set to a value that is in-scope, it is preserved. This allows callers to pre-populate scope fields and have them validated rather than silently overwritten.

### 8.7 `update_with_version_check` Extra Filters

Optimistic-lock updates accept an `extra_filters` parameter that can add additional scope conditions to the UPDATE WHERE clause, preventing cross-tenant updates even on direct `session.execute(UPDATE ...)` calls. This is an additional defense-in-depth layer.

---

## 9. Current Risks

### CRITICAL

| ID | Risk | Location | Description |
|---|---|---|---|
| CR-1 | No tenant membership enforcement in `set_active_tenant()` | `TenantContextService.set_active_tenant()` | Any authenticated user can switch to any active tenant by providing its ID. There is no `user_tenants` table and no membership check. All data in the target tenant immediately becomes accessible. |
| CR-2 | `_deactivate_other_organizations()` is not tenant-scoped | `OrganizationService._deactivate_other_organizations()` | `list_all(active_only=True)` returns organizations from all tenants. Activating an org in Tenant A deactivates all active orgs in all other tenants — cross-tenant data corruption. |
| CR-3 | Username globally unique, no tenant isolation | `users` table, `UserRepository.get_by_username()` | Usernames are unique across the entire database. Two tenants cannot have a user with the same username. In multi-tenant deployment, a user in Tenant A could collide with or shadow a user in Tenant B. Authentication lookup is global. |

### HIGH

| ID | Risk | Location | Description |
|---|---|---|---|
| HR-1 | `is_platform_admin()` is dead code | `UserSessionContext.is_platform_admin()` | Checks for `"platform.admin"` permission which is never seeded. Always returns False. Any code path gated on this check is permanently disabled. |
| HR-2 | Custom PBKDF2 instead of Argon2id | `src/core/platform/auth/passwords.py` | PBKDF2-SHA256 at 390,000 iterations is acceptable but lacks memory-hardness. Argon2id is the current NIST/OWASP recommendation and should be adopted. |
| HR-3 | MFA non-functional | QML login form | Backend TOTP implementation is correct. The QML login form never collects the TOTP code. If MFA is enabled on an account, that account cannot be accessed through the UI. |
| HR-4 | `user_roles` unique constraint missing `organization_id` | `user_roles` table | `UNIQUE(user_id, role_id)` prevents assigning the same role in different organizations. The constraint must include `organization_id` to support org-scoped role assignments. |
| HR-5 | No `tenant_admin` or `org_admin` role | `policy.py`, `roles` table | The only privileged role is `admin` (superuser). No intermediate administrative roles exist for delegated tenant or organization management. |
| HR-6 | `UserRepository.list_all()` unscoped | Auth user repository | `list_all()` returns all users from all tenants. In multi-tenant mode, a tenant admin could enumerate users of other tenants. |
| HR-7 | Roles and permissions are platform-global | `roles`, `permissions`, `role_permissions` | No tenant can define custom roles or modify permission sets. All tenants share the same 18 roles and 56 permissions seeded at bootstrap. |

### MEDIUM

| ID | Risk | Location | Description |
|---|---|---|---|
| MR-1 | `ScopedAccessGrant.tenant_id` nullable for non-org scopes | `scoped_access_grants` table | Grants with `scope_type != "organization"` may have `tenant_id = NULL`. These grants match any tenant context, creating cross-tenant permission bleed. |
| MR-2 | Session validation throttled at 60s | `session_service._SESSION_VALIDATION_THROTTLE_SECONDS` | A revoked session may remain active for up to 60 seconds after revocation in high-frequency usage. |
| MR-3 | `_apply_scope` uses runtime `hasattr()` introspection | `_tenant_scope.py` in all modules | If an ORM class column is absent or misspelled, the scope filter is silently omitted without any error or log. Isolation failure is silent. |
| MR-4 | `get_default()` silent fallback to first active tenant | `TenantContextService.get_active_tenant()` | When no session tenant is set, returns the first active tenant found. In multi-tenant deployment, this default could resolve to the wrong tenant for unauthenticated or partially-authenticated contexts. |
| MR-5 | `get_active()` org repository unscoped | `OrganizationRepository.get_active()` | Returns the first org with `is_active=True` without tenant filtering. Correct in single-tenant mode; incorrect in multi-tenant mode. |
| MR-6 | `employees.organization_id` nullable | `employees` table | Employee records are not guaranteed to belong to an organization. This breaks org-scoped HR operations and allows orphaned employees. |
| MR-7 | `time_entries.organization_id` nullable | `time_entries` table | Time entry records may lack organization context. Scoped time reports may silently omit entries that lack `organization_id`. |
| MR-8 | `timesheet_periods.organization_id` nullable | `timesheet_periods` table | Same risk as MR-7 for timesheet period records. |

---

## 10. Current Gaps

### Tenant Management

| Gap | Impact |
|---|---|
| No `create_tenant` API | Tenants can only be created by directly inserting into the database. No service method, no validation, no audit. |
| No `list_tenants` / `deactivate_tenant` API | No management plane for tenant lifecycle. |
| No tenant switcher UI | Users cannot switch tenants through the application; context is fixed at the single bootstrap tenant. |
| No `user_tenants` table | No database record of which users belong to which tenants. Membership cannot be queried or enforced. |
| No tenant deactivation cascade | Deactivating a tenant does not cascade to deactivate its organizations, projects, or other owned data. |
| No tenant-level audit log | There is no segregated audit log per tenant. All audit entries share the same `audit_entries` table filtered only by `tenant_id`. |
| No default calendar seeded at org creation | `bootstrap_defaults()` for organizations does not create a default working calendar for the new org. |

### User and Identity Management

| Gap | Impact |
|---|---|
| No user invite flow | Users cannot be invited to a tenant via email. Account creation requires direct admin access. |
| Username unique globally | Must become unique per tenant (i.e., `UNIQUE(username, tenant_id)`) to support multi-tenant deployment where the same email/username should be registrable in separate tenants. |
| No email invitation system | No mechanism to send onboarding emails, password-reset emails, or MFA setup emails. |

### Role and Access Management

| Gap | Impact |
|---|---|
| `tenant_admin` role missing | No delegated tenant administration. All tenant management requires the global `admin` role. |
| `org_admin` role missing | No delegated organization administration. Organizations cannot self-manage their users and settings without a global admin. |
| `site_admin` role missing | No site-scoped mechanism exists in `scoped_access_grants`. Site-level administration is not supported. |
| `department_manager` role missing | No department-scoped role assignment mechanism. |
| `provision_organization()` missing `tenant_id` param | `OrganizationService.create_organization()` creates an organization without associating it to a specific tenant. In multi-tenant mode, the calling context's `tenant_id` must be stamped explicitly. |
| Custom per-tenant roles impossible | Roles and permissions are seeded globally at bootstrap and cannot be customized per tenant. |
| No bulk role assignment | Roles can only be assigned one user at a time. No group or batch assignment mechanism. |
| No role expiry support | `user_roles` has no `expires_at` column. Temporary role grants cannot be automatically revoked. |

### Permission Code Gaps

| Gap | Impact |
|---|---|
| `platform.admin` permission code never seeded | `is_platform_admin()` always returns False. Dead code. Must be seeded in `DEFAULT_PERMISSIONS` and assigned to a `platform_admin` role to be usable. |
| `organization.access` permission never enforced | The permission exists in `DEFAULT_PERMISSIONS` and is assigned to `viewer` and above, but no service method calls `require_permission(..., "organization.access", ...)` as a gate. It is declared but not checked. |

### Data Integrity Gaps

| Gap | Impact |
|---|---|
| `approval_requests.project_id` stored as plain String | No FK constraint to `projects.id`. Orphaned approval requests cannot be detected by the DB. |
| `baseline_variance_records.project_id` stored as plain String | Same issue — denormalized snapshot with no FK constraint. |
| `maintenance_asset_components` lacks `tenant_id` | First-class asset entity with no direct tenant column. Isolation relies solely on `organization_id`. Inconsistent with sibling `maintenance_assets` which has `tenant_id`. |
| `document_links` lacks `tenant_id` | Polymorphic document links rely only on `organization_id` for isolation. |
