# Architecture Reference

> **Status:** Living document — reflects codebase as of 2026-06-17 (branch `refactor/safe-start`).
> Sections 1–10 cover the current state; later sections (not yet written) will cover the target state.
>
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
6. [RBAC — Roles, Permissions, and SoD](#6-rbac--roles-permissions-and-sod)
7. [Tenant Context](#7-tenant-context)
8. [Repository Scoping](#8-repository-scoping)
9. [Current Risks](#9-current-risks)
10. [Current Gaps](#10-current-gaps)

---

## 1. Current Architecture Overview

### 1.1 Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Qt / QML (desktop-native UI) |
| API bridge | Python `api/desktop/` — QML-callable Python objects |
| Application services | Pure Python, domain-driven |
| ORM | SQLAlchemy 2.x (`Mapped[]` typed columns) |
| Migrations | Alembic |
| Database | SQLite (current) / PostgreSQL-ready schema |
| Async tasks | `runtime_executions` table + `RuntimeExecutionORM` |

### 1.2 Layered Design

The application follows a strict four-layer architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│  UI LAYER  (src/ui_qml/)                                        │
│  QML screens, components, state bindings                        │
├─────────────────────────────────────────────────────────────────┤
│  API LAYER  (src/api/)                                          │
│  api/desktop/   — QProperty / Q_INVOKABLE bridge objects        │
│  desktop-only; no HTTP transport is currently supported         │
├─────────────────────────────────────────────────────────────────┤
│  APPLICATION LAYER  (src/core/)                                 │
│  core/platform/   — tenancy, auth, org, RBAC, access, docs      │
│  core/modules/    — PM, inventory, maintenance, payroll, HR     │
├─────────────────────────────────────────────────────────────────┤
│  INFRASTRUCTURE LAYER  (src/infra/)                             │
│  infra/persistence/  — SQLAlchemy ORM, Alembic, repositories    │
│  infra/composition/  — dependency injection, app wiring         │
│  infra/config/       — environment variable configuration        │
└─────────────────────────────────────────────────────────────────┘
```

### 1.3 Directory Structure

```
project_manager_Lite/
├── src/
│   ├── api/
│   │   ├── desktop/
│   │   │   └── platform/         # QML-facing platform APIs
│   │   │       ├── access.py
│   │   │       ├── approval.py
│   │   │       ├── document.py
│   │   │       ├── party.py
│   │   │       ├── runtime.py
│   │   │       ├── support.py
│   │   │       └── models/       # Pydantic / dataclass response shapes
│   ├── application/
│   │   └── runtime/              # Module entitlement runtime
│   ├── core/
│   │   ├── platform/             # Platform-wide cross-cutting concerns
│   │   │   ├── access/           # Scoped access grants, project memberships
│   │   │   ├── activity/         # Activity feed (append-only)
│   │   │   ├── approval/         # Governed change request workflow
│   │   │   ├── audit/            # Enterprise compliance audit log
│   │   │   ├── auth/             # Authentication, RBAC, sessions
│   │   │   │   ├── application/  # AuthService + sub-services
│   │   │   │   ├── contracts/    # Repository interfaces
│   │   │   │   ├── domain/       # UserAccount, AuthSession, Roles
│   │   │   │   ├── authorization.py
│   │   │   │   ├── mfa.py
│   │   │   │   ├── passwords.py
│   │   │   │   ├── policy.py     # 56 permissions + 18 role maps
│   │   │   │   └── sod.py        # Separation of duties rules
│   │   │   ├── authorization/    # AuthorizationEngine singleton
│   │   │   ├── calendar/         # Platform calendar engine
│   │   │   ├── common/           # Shared exceptions, IDs
│   │   │   ├── department/       # Department domain
│   │   │   ├── documents/        # Document management
│   │   │   ├── employee/         # Employee directory
│   │   │   ├── infrastructure/   # Platform persistence (ORM, repos)
│   │   │   ├── org/              # Organization domain + service
│   │   │   ├── party/            # Vendor/contractor/client master data
│   │   │   ├── site/             # Site domain
│   │   │   ├── tenancy/          # Tenant domain + TenantContextService
│   │   │   └── time/             # Time entries + timesheets
│   │   ├── modules/              # Business modules
│   │   │   ├── project_management/
│   │   │   │   ├── access/       # PM-specific policy
│   │   │   │   ├── application/  # Project, task, cost, financials, portfolio
│   │   │   │   ├── contracts/
│   │   │   │   ├── domain/
│   │   │   │   └── infrastructure/
│   │   │   ├── inventory_procurement/
│   │   │   ├── maintenance/
│   │   │   ├── payroll/
│   │   │   ├── hr_management/
│   │   │   └── qhse/
│   │   └── shared/               # Cross-cutting utilities (events, audit helpers)
│   ├── infra/
│   │   ├── composition/          # App-level DI wiring
│   │   ├── config/               # Environment variable loaders
│   │   └── persistence/
│   │       ├── db/               # Engine, session factory, optimistic locking
│   │       └── orm/
│   │           └── base.py       # DeclarativeBase
│   └── ui_qml/                   # QML source files
├── tests/
│   ├── core/
│   │   ├── platform/
│   │   └── modules/
│   └── ...
├── docs/                         # Architecture and migration plans
├── alembic/                      # Database migration scripts
└── resources/                    # Shared Qt resources
```

### 1.4 Platform vs Module Distinction

**Platform layer** (`src/core/platform/`) owns:
- Tenancy, organizations, sites, departments, employees, parties
- Authentication, RBAC, sessions, MFA, password management
- Authorization engine (flat and scoped permission checks)
- Approval workflows, audit log, activity feed
- Platform calendar engine, document management
- Module entitlements

**Module layer** (`src/core/modules/`) owns:
- Project management (projects, tasks, resources, costs, baselines, portfolio)
- Inventory and procurement
- Maintenance (CMMS)
- Payroll
- HR management

Each module communicates with the platform only through:
1. Injected `TenantContextService` for scope resolution
2. Injected `UserSessionContext` for permission checks
3. `record_audit_entry()` helper for compliance logging
4. Domain events via `domain_events.*` signals

---

## 2. Tenant Architecture

### 2.1 What a Tenant Is

A **tenant** is the top-level isolation boundary. Every business data record ultimately traces back to a `tenant_id` foreign key, either directly on the table or through a parent entity chain.

The ORM model is:

```python
# src/core/platform/infrastructure/persistence/orm/tenant.py
class TenantORM(Base):
    __tablename__ = "tenants"
    id:           Mapped[str]  = mapped_column(String, primary_key=True)
    tenant_code:  Mapped[str]  = mapped_column(String(64), nullable=False, unique=True)
    display_name: Mapped[str]  = mapped_column(String(256), nullable=False)
    is_active:    Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version:      Mapped[int]  = mapped_column(Integer, nullable=False, default=1)
```

`tenant_code` carries a `UNIQUE` constraint enforced both at the DB level and by a separate index `idx_tenants_code`. Codes are stored as uppercase strings (see `get_by_code()` which calls `.upper()`).

### 2.2 Tenant Hierarchy

The data hierarchy from root to leaf is:

```
Tenant
  └── Organization (tenant_id FK NOT NULL after migration r3s4t5u6v7w8)
        └── Site (organization_id FK NOT NULL, tenant_id FK)
              └── Department (organization_id FK NOT NULL, site_id nullable, tenant_id FK)
                    └── Employee (organization_id FK nullable, site_id nullable,
                    |             department_id nullable, tenant_id FK)
                    └── [Business data: projects, resources, assets, stock, etc.]
```

ASCII form:

```
┌──────────────────────────────────────────────────────────┐
│  TENANT  (tenants.id)                                    │
│  tenant_code UNIQUE, is_active, version                  │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  ORGANIZATION  (organizations.tenant_id FK)        │  │
│  │  timezone_name, base_currency                      │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  SITE  (sites.organization_id FK NOT NULL,   │  │  │
│  │  │         sites.tenant_id FK)                  │  │  │
│  │  │                                              │  │  │
│  │  │  ┌────────────────────────────────────────┐  │  │  │
│  │  │  │  DEPARTMENT  (departments.org_id FK,   │  │  │  │
│  │  │  │               departments.tenant_id FK)│  │  │  │
│  │  │  │  parent_department_id (self-ref)        │  │  │  │
│  │  │  │                                        │  │  │  │
│  │  │  │  ┌──────────────────────────────────┐  │  │  │  │
│  │  │  │  │  EMPLOYEE  (employees.org_id FK, │  │  │  │  │
│  │  │  │  │             employees.tenant_id) │  │  │  │  │
│  │  │  │  └──────────────────────────────────┘  │  │  │  │
│  │  │  │                                        │  │  │  │
│  │  │  │  ┌──────────────────────────────────┐  │  │  │  │
│  │  │  │  │  Business data (projects,        │  │  │  │  │
│  │  │  │  │  resources, assets, stock, ...)  │  │  │  │  │
│  │  │  │  └──────────────────────────────────┘  │  │  │  │
│  │  │  └────────────────────────────────────────┘  │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

### 2.3 How Tenant Isolation Works in Repositories

Two mechanisms enforce isolation at the data layer:

**Mechanism 1 — `_stamp_scope()` (write-time stamping)**

When a new ORM row is added, `_stamp_scope()` sets `organization_id` and `tenant_id` from the active `TenantContext`:

```python
def _stamp_scope(self, ctx: TenantContext, orm: object) -> None:
    if hasattr(orm, "organization_id"):
        if getattr(orm, "organization_id", None) is None:
            setattr(orm, "organization_id", ctx.organization_id)
        elif not self._organization_in_scope(ctx, orm.organization_id):
            raise BusinessRuleError("... organization is outside the active scope.")
    if hasattr(orm, "tenant_id"):
        if getattr(orm, "tenant_id", None) is None and ctx.tenant_id is not None:
            setattr(orm, "tenant_id", ctx.tenant_id)
        elif not self._tenant_in_scope(ctx, orm.tenant_id):
            raise BusinessRuleError("... tenant is outside the active scope.")
```

**Mechanism 2 — `_apply_scope()` (read-time filtering)**

Every `SELECT` statement is filtered through `_apply_scope()` before execution:

```python
def _apply_scope(self, stmt, orm_model, ctx: TenantContext):
    organization_column = getattr(orm_model, "organization_id", None)
    if organization_column is not None:
        stmt = stmt.where(organization_column == ctx.organization_id)
    tenant_column = getattr(orm_model, "tenant_id", None)
    if tenant_column is not None and ctx.tenant_id is not None:
        stmt = stmt.where(tenant_column == ctx.tenant_id)
    return stmt
```

Both use `getattr()` / `hasattr()` runtime introspection — see Section 8 for the silent-miss risk this creates.

### 2.4 Tenant-Root Tables (Direct `tenant_id`)

These 37 tables carry `tenant_id` directly:

| Domain | Tables |
|---|---|
| Platform | `organizations`, `employees`, `sites`, `departments`, `parties`, `approval_requests`, `document_structures`, `documents`, `organization_module_entitlements`, `scoped_access_grants`, `activity_entries`, `audit_entries`, `time_entries`, `timesheet_periods` |
| Calendar | `platform_calendars`, `shift_patterns` |
| Project Mgmt | `projects`, `resources`, `portfolio_scoring_templates`, `portfolio_intake_items`, `portfolio_scenarios` |
| Maintenance | `maintenance_locations`, `maintenance_systems`, `maintenance_assets`, `maintenance_sensors`, `maintenance_work_requests`, `maintenance_work_orders`, `maintenance_preventive_plans` |
| Inventory | `inventory_item_categories`, `inventory_stock_items`, `inventory_storerooms`, `inventory_stock_balances`, `inventory_stock_transactions`, `inventory_stock_reservations`, `inventory_purchase_requisitions`, `inventory_purchase_orders`, `inventory_receipt_headers` |

### 2.5 Scope-Inherited Tables (No Direct `tenant_id`)

These tables carry only `organization_id` (tenant inherited through org FK) or neither column (tenant inherited through a multi-hop FK chain to a parent with `tenant_id`):

**Organization-scoped only (23 tables):** `document_links`, `maintenance_asset_components`, `maintenance_sensor_readings`, `maintenance_integration_sources`, `maintenance_sensor_source_mappings`, `maintenance_sensor_exceptions`, `maintenance_failure_codes`, `maintenance_downtime_events`, `maintenance_work_order_tasks`, `maintenance_work_order_task_steps`, `maintenance_work_order_material_requirements`, `maintenance_task_templates`, `maintenance_task_step_templates`, `maintenance_preventive_plan_tasks`, `maintenance_preventive_plan_instances`, `inventory_storage_locations`, `inventory_reorder_policies`, `inventory_cycle_counts`, `user_roles` (org nullable)

**Fully inherited through parent FK chain (18+ tables):** `tasks`, `task_assignments`, `task_dependencies`, `task_comments`, `task_presence`, `project_resources`, `project_baselines`, `baseline_tasks`, `baseline_variance_records`, `register_entries`, `resource_skills`, `resource_certifications`, `task_skill_requirements`, `project_calendar_assignments`, `resource_calendar_assignments`, `cost_items`, `calendar_events`, `portfolio_project_dependencies`, `inventory_purchase_requisition_lines`, `inventory_purchase_order_lines`, `inventory_receipt_lines`, `calendar_working_rules`, `calendar_exceptions`, `calendar_recurring_events`, `shift_pattern_days`, `site_calendar_assignments`, `department_calendar_assignments`, `employee_calendar_assignments`

### 2.6 Platform-Global Entities (No Tenant Scope)

The following tables have no `tenant_id` or `organization_id` and are intentionally global:

| Entity | Rationale |
|---|---|
| `users` | Users are cross-tenant; a user account can be a member of multiple tenants (aspirationally) |
| `roles` | System roles are global (no per-tenant custom roles supported yet) |
| `permissions` | 56 system permission codes; global seed |
| `role_permissions` | Role-to-permission mapping; global |
| `auth_sessions` | `last_active_tenant_id` / `last_active_organization_id` are metadata snapshots, not isolation boundaries |
| `runtime_executions` | System-level async task tracking |

### 2.7 Current Single-Tenant vs Multi-Tenant Design

The codebase was written as a **single-tenant desktop application** and is being progressively retrofitted for multi-tenancy. The following design choices reflect the single-tenant origin:

- `TenantContextService.get_active_tenant()` falls back to `get_default()` (returns the first active tenant by `tenant_code` ascending) if no session tenant is set.
- `set_active_tenant()` performs no membership check — any authenticated user can switch to any tenant.
- There is no `user_tenants` join table and no API for creating tenants.
- The `organization.access` permission code exists in `DEFAULT_PERMISSIONS` but is never checked before granting organization context access.
- Username uniqueness is global across all tenants, not per-tenant.

---

## 3. Organization Architecture

### 3.1 Organization Model

```
organizations
  id                UUID string PK
  tenant_id         FK → tenants.id (RESTRICT, nullable per ORM — NOT NULL in practice after migration)
  organization_code VARCHAR(64) UNIQUE within tenant
  display_name      VARCHAR(256)
  timezone_name     VARCHAR(64)
  base_currency     VARCHAR(8)
  is_active         BOOLEAN NOT NULL
  version           INTEGER NOT NULL  (optimistic lock)
```

### 3.2 OrganizationService

Location: `src/core/platform/org/application/organization_service.py`

Key methods:

| Method | Permission Required | Description |
|---|---|---|
| `bootstrap_defaults()` | None | Seeds a default org if none exist; no `tenant_id` param |
| `list_organizations()` | `settings.manage` | Returns all orgs (unscoped by tenant) |
| `get_active_organization()` | `settings.manage` | Returns the single active org; auto-bootstraps |
| `create_organization()` | `settings.manage` | Creates org; deactivates all others |
| `update_organization()` | `settings.manage` | Updates org fields; deactivates others if set active |
| `set_active_organization()` | `settings.manage` | Flips active flag; writes to session context |

### 3.3 The `_deactivate_other_organizations()` Critical Bug

```python
def _deactivate_other_organizations(self, *, exclude_id: str | None) -> None:
    for organization in self._organization_repo.list_all(active_only=True):
        if exclude_id and organization.id == exclude_id:
            continue
        if not organization.is_active:
            continue
        organization.is_active = False
        self._organization_repo.update(organization)
```

**Bug:** `list_all()` on the organization repository is **not scoped by `tenant_id`**. In a multi-tenant deployment this would deactivate active organizations belonging to other tenants whenever any organization is activated. This function is called from `create_organization()`, `update_organization()`, and `set_active_organization()`.

### 3.4 Organization Context Resolution

`get_active_organization()` in `TenantContextService`:

```
1. Read _session_organization_id()
     └── UserSessionContext._active_organization_id
2. If found: call organization_repo.get(id)
3. If org is active AND _can_access(org.id) → return org
4. If not: clear _active_organization_id in session, return None
```

`_can_access()` logic:
- Admin role → always true
- `principal.scoped_access["organization"]` present → check membership
- Otherwise → compare against `_active_organization_id` string match

`active_organization_id()` on `UserSessionContext` includes a **single-org auto-select**:
```python
organization_ids = sorted(self.organization_ids())
return organization_ids[0] if len(organization_ids) == 1 else None
```
If the principal has exactly one organization in its `scoped_access["organization"]` map, it is auto-selected.

### 3.5 `get_active()` Unscoped Bug

The `OrganizationRepository.get_active()` call inside `OrganizationService.get_active_organization()` returns the first active organization across all tenants. In a multi-tenant context, this will return a foreign tenant's organization if the current tenant has none.

### 3.6 Single-Active Invariant

The system enforces a **single-active-organization invariant**: at any given time, at most one organization is `is_active = True`. This invariant is maintained by `_deactivate_other_organizations()`. This is a single-tenant desktop holdover — multi-tenant operation requires relaxing it to: one active organization per tenant, per user session.

### 3.7 Organization Switching (Admin Console)

The Admin Console UI allows switching the active organization:
1. User selects an organization from the list.
2. `OrganizationService.set_active_organization(org_id)` is called.
3. All other organizations are deactivated (cross-tenant bug applies here).
4. `UserSessionContext.set_active_organization_id(org.id)` updates the in-memory session.
5. `domain_events.organizations_changed.emit(org.id)` triggers UI refresh.

### 3.8 Organization Module Entitlements

```
organization_module_entitlements
  organization_id   FK → organizations.id (CASCADE) — part of composite PK
  module_code       VARCHAR — part of composite PK
  licensed          BOOLEAN
  enabled           BOOLEAN
  tenant_id         FK → tenants.id (CASCADE, nullable) — non-PK column added later
```

Module entitlements control which functional modules are available to an organization. They are checked at runtime by `EntitlementRuntime`. Notable: `tenant_id` was added as a non-PK column after the fact, creating an asymmetry with the composite PK.

### 3.9 Organization Hierarchy

```
ORGANIZATION
    │
    ├── SITE (sites.organization_id FK NOT NULL, sites.tenant_id FK)
    │     │
    │     └── DEPARTMENT (departments.site_id FK nullable,
    │               │      departments.organization_id FK NOT NULL)
    │               │
    │               ├── EMPLOYEE (employees.department_id FK nullable)
    │               └── MAINTENANCE LOCATION
    │
    ├── RESOURCE (resources.organization_id FK NOT NULL)
    ├── PROJECT (projects.organization_id FK NOT NULL)
    ├── DOCUMENT (documents.organization_id FK NOT NULL)
    ├── PARTY (parties.organization_id FK NOT NULL)
    ├── PLATFORM CALENDAR (platform_calendars.organization_id FK NOT NULL)
    └── INVENTORY (inventory_storerooms.organization_id FK NOT NULL, ...)
```

---

## 4. Authentication

### 4.1 Authentication Flow

Entry point: `AuthService.authenticate()` → delegates to `authentication_service.authenticate()`.

```
authenticate(username, raw_password, mfa_code=None, device_label=None)
│
├── 1. Normalize username to lowercase stripped string
├── 2. user_repo.get_by_username(normalized)
├── 3. If user not found or not is_active → raise ValidationError("AUTH_FAILED")
├── 4. If user.locked_until <= now → auto-unlock (clear failed_login_attempts)
├── 5. If user.locked_until > now → raise ValidationError("AUTH_LOCKED")
├── 6. verify_password(raw_password, user.password_hash)
│     └── If fails → register_failed_login() → possible lockout
│           └── raise ValidationError("AUTH_FAILED")
├── 7. If user.mfa_enabled:
│     └── verify_totp_code(user.mfa_secret, mfa_code, at_time=now)
│           └── If fails → register_failed_login()
│                 └── raise ValidationError("AUTH_MFA_REQUIRED" | "AUTH_MFA_FAILED")
└── 8. complete_successful_authentication()
      ├── Reset failed_login_attempts to 0, clear locked_until
      ├── Set last_login_at, last_login_auth_method, last_login_device_label
      ├── Compute session_expires_at (env PM_AUTH_SESSION_MINUTES, default 480m)
      ├── Create AuthSession record in auth_sessions table
      ├── Set user.active_session_id = new session id
      ├── user_repo.update(user); session.commit()
      ├── Emit domain_events.auth_changed
      ├── record_auth_event() → audit log entry
      └── refresh_current_session_if_user() → rebuild UserSessionPrincipal
```

### 4.2 Federated Authentication

`authenticate_federated(identity_provider, federated_subject, mfa_code, device_label)` follows the same flow but looks up the user by `(identity_provider, federated_subject)` via `user_repo.get_by_federated_identity()`. The `auth_method` field stored on the session is `"federated:<provider>"`.

### 4.3 Session Principal Construction (`principal_builder.py`)

After a successful authentication, `build_principal()` assembles a `UserSessionPrincipal` frozen dataclass:

```python
@dataclass(frozen=True)
class UserSessionPrincipal:
    user_id:                str
    username:               str
    display_name:           str | None
    role_names:             frozenset[str]
    permissions:            frozenset[str]
    scoped_access:          dict[str, dict[str, frozenset[str]]]
    project_access:         dict[str, frozenset[str]]
    session_expires_at:     datetime | None
    must_change_password:   bool
    session_revision:       int
    identity_provider:      str | None
    last_login_auth_method: str | None
    session_id:             str | None
    active_tenant_id:       str | None
    active_organization_id: str | None
```

Construction steps:
1. Load all `ScopedAccessGrant` rows for the user → build `scoped_access` dict keyed by `scope_type` → `scope_id` → `frozenset[permission_codes]`.
2. If no `ScopedAccessGrantRepository` is wired, fall back to `ProjectMembershipRepository` and populate `scoped_access["project"]` only.
3. Resolve `session_id` from `user.active_session_id`.
4. Load the `AuthSession` record; confirm it is not revoked.
5. Collect `role_names` via `get_user_role_names(user_id)` and `permissions` via `get_user_permissions(user_id)`.
6. Populate `active_tenant_id` and `active_organization_id` from the resolved `AuthSession.last_active_tenant_id` / `last_active_organization_id`.

### 4.4 Password Hashing

Location: `src/core/platform/auth/passwords.py`

The implementation uses **custom PBKDF2-SHA256** with 390,000 iterations and a 16-byte random salt. The stored format is:

```
pbkdf2_sha256$390000$<base64-salt>$<base64-digest>
```

Also supports `pbkdf2_sha512` for verification of legacy hashes.

**Security note:** PBKDF2 at 390,000 iterations is acceptable but not state-of-the-art. The recommended replacement is **argon2id** (memory-hard KDF). The constant `_DEFAULT_ITERATIONS = 390_000` is not configurable at runtime.

### 4.5 Multi-Factor Authentication

Location: `src/core/platform/auth/mfa.py` (referenced), `src/core/platform/auth/application/mfa_service.py`

The backend implementation is complete:
- `provision_mfa_secret()` generates a TOTP secret.
- `enable_user_mfa(user_id, verification_code)` verifies and enables MFA.
- `disable_user_mfa(user_id)` disables MFA.
- `verify_totp_code()` is called during `authenticate()`.

**Critical gap:** The UI login screen **never collects a TOTP code**. The `mfa_code` parameter is always `None` in practice. This means even users with `mfa_enabled = True` pass MFA because `verify_totp_code(secret, None)` returns `False`, which triggers the `AUTH_MFA_REQUIRED` error — but the login screen does not re-present a TOTP entry field. MFA is effectively non-functional.

### 4.6 Session Persistence (`auth_sessions`)

```
auth_sessions
  id                          UUID PK
  user_id                     FK → users.id (CASCADE)
  session_revision            INTEGER (matches users.session_revision)
  auth_method                 VARCHAR ("password" | "federated:<provider>")
  device_label                VARCHAR nullable
  last_active_tenant_id       FK → tenants.id (SET NULL, nullable)
  last_active_organization_id FK → organizations.id (SET NULL, nullable)
  issued_at                   DATETIME
  expires_at                  DATETIME
  last_validated_at           DATETIME
  revoked_at                  DATETIME nullable
  created_at                  DATETIME
  updated_at                  DATETIME
```

Session validation (`validate_session_principal()`) checks:
1. User exists and `is_active`.
2. `user.session_expires_at` not passed.
3. `auth_session` record exists, not revoked, `expires_at` not passed.
4. `auth_session.session_revision == user.session_revision` (revision bump revokes all sessions).
5. Calls `touch_validation()` to update `last_validated_at` — throttled to once per **60 seconds** (`_SESSION_VALIDATION_THROTTLE_SECONDS = 60`).

### 4.7 Lockout Policy

Configurable via environment variables:
- `PM_AUTH_LOCKOUT_ATTEMPTS` (default: 5) — failed attempts before lockout.
- `PM_AUTH_LOCKOUT_MINUTES` (default: 15) — lockout duration.
- `PM_AUTH_SESSION_MINUTES` (default: 480) — session lifetime.

On lock expiry, the next authentication attempt **auto-unlocks** the account before checking the password.

### 4.8 First-Run Bootstrap (`bootstrap_defaults()`)

Location: `src/core/platform/auth/application/bootstrap_service.py`

Sequence:
1. `ensure_default_permissions()` — seeds all 56 permission codes.
2. `ensure_default_roles()` — seeds all 18 system roles.
3. `ensure_role_permissions()` — seeds role-permission mappings from `DEFAULT_ROLE_PERMISSIONS`.
4. Look up or create the admin user (username from `PM_ADMIN_USERNAME` env var, default `"admin"`).
5. Set `must_change_password = True` on the admin user.

Admin password source (in order of precedence):
1. `PM_ADMIN_PASSWORD` environment variable.
2. Auto-generated password logged to stdout on first run.

---

## 5. Authorization

### 5.1 Flat Permission Check

**Location:** `src/core/platform/auth/authorization.py`

```python
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

`require_any_permission()` accepts an iterable of codes and passes if any one is present.

### 5.2 `@requires_permission` Decorator

Application-layer service methods that enforce RBAC call `require_permission()` at the top of the method body rather than via a decorator. The decorator pattern is used in some API-layer bridge objects.

### 5.3 Scoped Permission Check

**Location:** `src/core/platform/access/authorization.py`

```python
def require_scope_permission(
    user_session, scope_type, scope_id, permission_code, *, operation_label
) -> None:
    engine = get_authorization_engine()
    if engine.has_scope_permission(user_session, scope_type, scope_id, permission_code):
        return
    raise BusinessRuleError(...)
```

`require_project_permission()` is a convenience wrapper that hardcodes `scope_type="project"`.

`has_scope_permission()` logic on `UserSessionContext`:
1. If not authenticated → `False`.
2. If `"admin"` in `role_names` → `True` (bypass).
3. If `permission_code` not in flat `permissions` → `False`.
4. Resolve `scope_rows = principal.scoped_access.get(scope_type, {})`.
5. If `scope_rows` is empty → `True` (unrestricted, global role).
6. If `scope_rows` non-empty → check `permission_code in scope_rows.get(scope_id, frozenset())`.

### 5.4 Admin Session Bypass

```python
def is_admin_session(user_session: UserSessionContext | None) -> bool:
    return get_authorization_engine().is_admin_session(user_session)
```

The admin role receives all 56 permission codes (via `DEFAULT_ROLE_PERMISSIONS["admin"] = set(DEFAULT_PERMISSIONS.keys())`). Because the admin check (`"admin" in role_names`) happens before all scope checks, admin users bypass all scoped access controls. There is no way to restrict an admin to a subset of organizations or projects.

### 5.5 `is_platform_admin()` Dead Code

```python
# src/core/platform/auth/domain/session.py
def is_platform_admin(self) -> bool:
    principal = self._active_principal()
    if principal is None:
        return False
    return "platform.admin" in principal.permissions
```

The permission code `"platform.admin"` does not exist in `DEFAULT_PERMISSIONS` and is never seeded. No role is assigned this permission. `is_platform_admin()` will always return `False`. This is dead code.

### 5.6 Authorization Module Distinction

There are **two** authorization modules with overlapping names:

| Module | Location | Purpose |
|---|---|---|
| `src/core/platform/auth/authorization.py` | Auth package | Flat `require_permission()`, `require_any_permission()`, `is_admin_session()` |
| `src/core/platform/access/authorization.py` | Access package | Scoped `require_scope_permission()`, `require_project_permission()`, `filter_scope_rows()` |

Both delegate to `get_authorization_engine()` from `src/core/platform/authorization/` — a singleton that wraps `UserSessionContext` calls. The separation is intentional: auth-level checks vs access-level (project/scope) checks.

---

## 6. RBAC — Roles, Permissions, and SoD

### 6.1 Permission Codes (56 total)

Grouped by domain:

**Project Management**
- `project.read`, `project.manage`
- `task.read`, `task.manage`
- `time.read`, `time.manage`
- `resource.read`, `resource.manage`
- `cost.read`, `cost.manage`
- `baseline.manage`, `baseline.approve`
- `register.read`, `register.manage`
- `portfolio.read`, `portfolio.manage`
- `collaboration.read`, `collaboration.manage`

**Finance and Payroll**
- `finance.read`, `finance.manage`, `finance.export`
- `payroll.read`, `payroll.manage`, `payroll.approve`, `payroll.export`

**Timesheet**
- `timesheet.submit`, `timesheet.approve`, `timesheet.lock`

**HR and Organization**
- `employee.read`, `employee.manage`
- `site.read`, `department.read`
- `party.read`

**Inventory and Maintenance**
- `inventory.read`, `inventory.manage`
- `maintenance.read`, `maintenance.manage`

**Reporting**
- `report.view`, `report.export`

**Governance**
- `approval.request`, `approval.decide`
- `audit.read`
- `import.manage`

**Platform Administration**
- `auth.read`, `auth.manage`
- `security.manage`
- `settings.manage`
- `access.manage`
- `support.manage`
- `organization.access`

### 6.2 System Roles (18 roles)

| Role | Key Permissions | Notes |
|---|---|---|
| `viewer` | `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `register.read`, `report.view`, `collaboration.read`, `organization.access` | Read-only across PM |
| `team_member` | viewer + `collaboration.manage`, `timesheet.submit` | Field-level contributor |
| `planner` | team_member + `project.manage`, `task.manage`, `time.manage`, `baseline.manage`, `register.manage`, `report.export`, `portfolio.read`, `approval.request`, `import.manage` | Full PM planner |
| `project_manager` | planner + `baseline.approve`, `cost.manage`, `finance.read`, `finance.export`, `timesheet.approve` | Senior PM |
| `resource_manager` | `project.read`, `task.read`, `time.read`, `resource.read/manage`, `employee.read/manage`, `site.read`, `department.read`, `report.view/export`, `timesheet.approve/lock` | HR/resource focus |
| `finance` / `finance_controller` | (same set) `project/task/time/resource/cost.read`, `cost.manage`, `party.read`, `register.read`, `report.view/export`, `finance.read/manage/export`, `payroll.read`, `approval.request` | Financial controller |
| `inventory_manager` | `inventory.read/manage`, `site.read`, `party.read`, `report.view/export`, `import.manage`, `approval.request` | Inventory / procurement |
| `maintenance_manager` / `maintenance_admin` | (same set) `maintenance.read/manage`, `time.read/manage`, `site.read`, `employee.read`, `party.read`, `report.view/export`, `approval.request`, `import.manage` | CMMS operations |
| `payroll_manager` | `project/task/time/resource/employee.read`, `employee.manage`, `site.read`, `department.read`, `report.view`, `payroll.read/manage/approve/export`, `timesheet.approve/lock`, `audit.read` | Payroll processing |
| `portfolio_manager` | `project/task/time/resource/cost/register.read`, `report.view/export`, `portfolio.read/manage`, `collaboration.read`, `approval.request` | Portfolio oversight |
| `approver` | `baseline.approve`, `project/task/time/resource/cost/register/portfolio/finance/payroll.read`, `report.view`, `approval.decide` | Governs approvals |
| `auditor` | `project/task/time/resource/cost/finance/payroll/register/portfolio/collaboration.read`, `report.view`, `audit.read` | Compliance auditor |
| `access_admin` | `project.read`, `site.read`, `auth.read`, `access.manage`, `audit.read` | Manages scoped access |
| `security_admin` | `auth.read`, `audit.read`, `settings.manage`, `security.manage` | Login security controls |
| `support_admin` | `project/task/time/register.read`, `report.view`, `auth.read`, `audit.read`, `support.manage` | Product support |
| `admin` | All 56 permissions | Superuser — bypasses all scope checks |

### 6.3 `user_roles` Table and Unique Constraint Bug

```
user_roles
  user_id         FK → users.id (CASCADE)
  role_id         FK → roles.id (CASCADE)
  organization_id FK → organizations.id (CASCADE, nullable)
  UNIQUE (user_id, role_id)           ← BUG: should be (user_id, role_id, organization_id)
```

Because the unique constraint is on `(user_id, role_id)` only, a user can hold a given role in at most one organization. Assigning `project_manager` to a user in Organization B when they already have it in Organization A will fail with a constraint violation. For multi-organization users, this makes org-scoped role assignment impossible without a migration.

### 6.4 `scoped_access_grants` Table

```
scoped_access_grants
  id                  UUID PK
  tenant_id           FK → tenants.id (CASCADE, nullable)
  user_id             FK → users.id (CASCADE)
  scope_type          VARCHAR  (e.g. "project", "organization", "site")
  scope_id            VARCHAR  (PK of the target entity)
  scope_role          VARCHAR  (role name within this scope)
  permission_codes_json JSON   (serialized list of permission code strings)
```

`scoped_access_grants` implements a generic polymorphic access grant. A user can be granted explicit permissions for any scope type. The `tenant_id` is nullable, intended to be set for tenant-specific grants. For non-organization scope types (e.g. `"project"`) the `tenant_id` may be null, creating a gap in isolation.

### 6.5 `project_memberships` Scoped Access

```
project_memberships
  project_id      FK → projects.id (CASCADE)
  user_id         FK → users.id (CASCADE)
  organization_id FK → organizations.id (SET NULL, nullable)
  scope_role      VARCHAR
  permission_codes_json JSON
```

Project memberships are the primary fine-grained access control mechanism for PM data. They have no `tenant_id` — tenant is inferred through `project → tenant_id`. This creates a 2-hop FK chain for tenant validation.

### 6.6 Separation of Duties Rules

Location: `src/core/platform/auth/sod.py`

Two rules are defined:

```python
SeparationOfDutiesRule(
    required_permissions=frozenset({"approval.request", "approval.decide"}),
    message="Users cannot both request and decide the same governed approvals.",
),
SeparationOfDutiesRule(
    required_permissions=frozenset({"access.manage", "security.manage"}),
    message="Users cannot both manage scoped access and manage login security controls.",
),
```

**SoD enforcement** is called from `sod_enforcer.enforce_separation_of_duties()` during role assignment. However:

```python
def enforce_separation_of_duties(service: AuthService, role_names: Iterable[str]) -> None:
    normalized = tuple(...)
    if "admin" in normalized:
        return   # ← admin bypasses SoD entirely
    ...
```

The `admin` role is explicitly exempted from SoD. Additionally, because SoD is enforced at **role assignment time** using `DEFAULT_ROLE_PERMISSIONS`, a determined administrator can bypass it by granting individual permissions via `scoped_access_grants` without going through the role assignment path.

### 6.7 Missing Roles

The following roles are architecturally absent and would be required for proper multi-tenant RBAC:

| Missing Role | Purpose |
|---|---|
| `tenant_admin` | Manage users, organizations, and settings within a tenant |
| `org_admin` | Manage resources and settings within one organization |
| `site_admin` | Site-level administrative operations |
| `department_manager` | Department-scoped HR and resource operations |

### 6.8 Proposed Role Hierarchy

```
platform.admin (future)
    └── tenant_admin (future)
          ├── org_admin (future)
          │     ├── site_admin (future)
          │     │     └── department_manager (future)
          │     └── project_manager (exists)
          │           └── planner (exists)
          │                 └── team_member (exists)
          │                       └── viewer (exists)
          ├── resource_manager (exists)
          ├── finance_controller (exists)
          ├── inventory_manager (exists)
          ├── maintenance_manager (exists)
          ├── payroll_manager (exists)
          ├── portfolio_manager (exists)
          ├── approver (exists)
          ├── auditor (exists)
          ├── access_admin (exists)
          ├── security_admin (exists)
          └── support_admin (exists)
```

---

## 7. Tenant Context

### 7.1 `TenantContextService` Full API

Location: `src/core/platform/tenancy/tenant_context.py`

```python
class TenantContextService:
    # Tenant resolution
    get_active_tenant_id() -> str | None
    require_active_tenant_id(*, operation_label: str) -> str          # raises if None
    get_active_tenant() -> Tenant | None
    set_active_tenant(tenant_id: str) -> Tenant                       # BUG: no membership check

    # Organization resolution
    get_active_organization_id() -> str | None
    require_active_organization_id(*, operation_label: str) -> str    # raises if None
    get_active_organization() -> Organization | None
    set_active_organization(organization_id: str) -> Organization

    # Full context
    require_context(*, operation_label: str) -> TenantContext          # raises if no tenant
    require_organization_context(*, operation_label: str) -> TenantContext  # raises if no org

    # Internal helpers
    _session_tenant_id() -> str | None
    _session_organization_id() -> str | None
    _can_access(organization_id: str) -> bool
```

`TenantContext` is a frozen dataclass:
```python
@dataclass(frozen=True)
class TenantContext:
    tenant_id:       str
    tenant:          Tenant
    organization_id: str | None
    organization:    Organization | None
```

### 7.2 `UserSessionContext` Full API

Location: `src/core/platform/auth/domain/session.py`

```python
class UserSessionContext:
    # Principal management
    principal: UserSessionPrincipal | None          # property
    set_principal(principal: UserSessionPrincipal)
    clear()

    # Authentication status
    is_authenticated() -> bool
    is_platform_admin() -> bool                     # DEAD CODE — always False

    # Flat permission checks
    has_permission(permission_code: str) -> bool

    # Scoped access checks
    has_any_scope_access(scope_type, permission_code) -> bool
    has_scope_permission(scope_type, scope_id, permission_code) -> bool
    has_any_project_access(permission_code) -> bool
    has_project_permission(project_id, permission_code) -> bool
    scope_ids_for(scope_type, permission_code) -> set[str]
    project_ids_for(permission_code) -> set[str]
    is_scope_restricted(scope_type) -> bool
    is_project_restricted() -> bool

    # Organization access
    organization_ids() -> set[str]
    has_organization_access(organization_id) -> bool

    # Tenant/org context
    active_tenant_id() -> str | None
    stored_active_tenant_id() -> str | None
    set_active_tenant_id(tenant_id: str | None)
    active_organization_id() -> str | None            # includes auto-select if exactly 1 org
    stored_active_organization_id() -> str | None
    set_active_organization_id(organization_id: str | None)
```

### 7.3 Context Flow: Login → Session → Repositories

```
                    LOGIN
                      │
          AuthService.authenticate()
                      │
        complete_successful_authentication()
                      │
          ┌───────────────────────┐
          │  AuthSession created  │
          │  (last_active_tenant_id,
          │   last_active_org_id  │
          │   from prior session) │
          └───────────┬───────────┘
                      │
            build_principal()
                      │
          UserSessionPrincipal {
            active_tenant_id,
            active_organization_id,
            permissions,
            scoped_access,
            session_id, ...
          }
                      │
        UserSessionContext.set_principal()
          │
          ├── _restore_active_context_from_principal()
          │     writes _active_tenant_id, _active_organization_id
          └── _notify_context_changed()
                      │
          ┌─────────────────────────┐
          │  TenantContextService   │
          │  (injected at wiring)   │
          │                         │
          │  get_active_tenant()    │
          │    → UserSessionContext │
          │      .active_tenant_id()│
          │                         │
          │  get_active_org()       │
          │    → _session_org_id()  │
          └────────────┬────────────┘
                       │
          ┌────────────────────────────┐
          │   Repository._context()   │
          │   calls require_org_ctx() │
          │   → TenantContext{        │
          │       tenant_id,          │
          │       organization_id     │
          │     }                     │
          └────────────┬──────────────┘
                       │
               _apply_scope(stmt, orm_model, ctx)
               _stamp_scope(ctx, orm)
```

### 7.4 Context Persistence

When `AuthService.persist_session_context()` is called (typically on logout or explicit context save), it writes:

```python
auth_session_repo.persist_context(
    session_id,
    last_active_tenant_id=session_context.stored_active_tenant_id(),
    last_active_organization_id=session_context.stored_active_organization_id(),
    updated_at=now,
)
```

On next login, `_resolve_last_active_context()` reads these stored values from the preferred `AuthSession` record and restores them into the new `AuthSession` and `UserSessionPrincipal`.

### 7.5 Tenant Resolution Priority Chain

```
get_active_tenant()
  1. UserSessionContext._active_tenant_id          (in-memory runtime state)
  2. UserSessionPrincipal.active_tenant_id         (from AuthSession on login)
  3. tenant_repo.get_default()                     (first active tenant by tenant_code ASC)
     └── FALLBACK — returns a tenant without any membership validation
```

### 7.6 Organization Resolution Priority Chain

```
active_organization_id()  [on UserSessionContext]
  1. UserSessionContext._active_organization_id    (in-memory; set by set_active_organization_id)
  2. UserSessionPrincipal.active_organization_id   (from AuthSession on login)
  3. Auto-select: if exactly ONE org in principal.scoped_access["organization"] → that org
  4. None (requires explicit selection via Admin Console / switcher)
```

### 7.7 `set_active_tenant()` — Missing Membership Check

```python
def set_active_tenant(self, tenant_id: str) -> Tenant:
    tenant = self._tenant_repo.get(normalized_id)
    if tenant is None: raise NotFoundError(...)
    if not tenant.is_active: raise BusinessRuleError(...)
    # ← NO CHECK: is this user a member of this tenant?
    if self._user_session is not None:
        self._user_session.set_active_tenant_id(tenant.id)
    return tenant
```

Any authenticated user can call `set_active_tenant()` with any valid active `tenant_id` and gain that tenant's context. Because there is no `user_tenants` table, there is no membership record to check against.

---

## 8. Repository Scoping

The codebase uses five distinct patterns for applying tenant/organization scope to database queries. Understanding which pattern a repository uses is critical for security audits.

### Pattern A — Inline WHERE in `_base_stmt()`

Some repositories construct a filtered base statement in a private `_base_stmt()` method that all query methods extend:

```python
def _base_stmt(self):
    ctx = self._context(operation_label="list")
    return select(SomeORM).where(
        SomeORM.tenant_id == ctx.tenant_id,
        SomeORM.organization_id == ctx.organization_id,
    )
```

All `list_*`, `get()`, `get_by_*` methods call `_base_stmt()`. This is the safest pattern — it is impossible to accidentally issue an unscoped query.

### Pattern B — `_apply_scope()` Runtime Introspection

Used by `ProjectManagementTenantScopedRepositorySupport` and similar mixins:

```python
def _apply_scope(self, stmt, orm_model, ctx: TenantContext):
    organization_column = getattr(orm_model, "organization_id", None)
    if organization_column is not None:
        stmt = stmt.where(organization_column == ctx.organization_id)
    tenant_column = getattr(orm_model, "tenant_id", None)
    if tenant_column is not None and ctx.tenant_id is not None:
        stmt = stmt.where(tenant_column == ctx.tenant_id)
    return stmt
```

**Silent miss risk:** `getattr(orm_model, "organization_id", None)` will return `None` if the column attribute does not exist on the ORM class, silently skipping the scope filter. If a new ORM model is added with a differently named FK (e.g. `owning_org_id`) this pattern will silently produce unscoped queries.

### Pattern C — `_get_in_scope()` / `_require_in_scope()`

Helper methods that combine `_apply_scope()` with a `WHERE id = ?` condition:

```python
def _get_in_scope(self, orm_model, record_id, *, operation_label):
    ctx = self._context(operation_label=operation_label)
    stmt = self._apply_scope(
        select(orm_model).where(orm_model.id == record_id),
        orm_model, ctx,
    )
    return self.session.execute(stmt).scalars().first()
```

If the record exists but belongs to a different tenant/org, it returns `None` (treated as not found), preventing cross-tenant data disclosure. `_require_in_scope()` raises `NotFoundError` on `None`.

### Pattern D — JOIN-Anchor (`ProjectManagementParentScopedRepositorySupport`)

Used for scope-inherited tables (e.g. tasks, task_assignments) where the row itself has no `tenant_id` or `organization_id`:

```python
def _scoped_stmt_for_anchor(self, row_model, anchor_model, *, joins, operation_label):
    ctx = self._context(operation_label=operation_label)
    stmt = select(row_model)
    for join_model, on_clause in joins:
        stmt = stmt.join(join_model, on_clause)
    return self._apply_scope(stmt, anchor_model, ctx)
```

The scope filter (`organization_id`, `tenant_id`) is applied to the **anchor model** (e.g. `ProjectORM`) while selecting from the child model (e.g. `TaskORM`). The JOIN ensures the child rows are implicitly filtered to the active tenant/org scope through their parent.

### Pattern E — Guard Before Query

Some repositories perform a membership check before issuing the main query:

```python
def get_by_project(self, project_id: str) -> list[SomeRow]:
    ctx = self._context(operation_label="get by project")
    # Validate that the project is in scope first
    self._require_in_scope(ProjectORM, project_id, ...)
    # Then query children (no tenant filter needed — project scope validated)
    stmt = select(SomeORM).where(SomeORM.project_id == project_id)
    return self.session.execute(stmt).scalars().all()
```

### Write-Time Scope Stamping (`_stamp_scope`)

```python
def _stamp_scope(self, ctx: TenantContext, orm: object) -> None:
    if hasattr(orm, "organization_id"):
        organization_id = getattr(orm, "organization_id", None)
        if organization_id is None or organization_id == "":
            setattr(orm, "organization_id", ctx.organization_id)
        elif not self._organization_in_scope(ctx, organization_id):
            raise BusinessRuleError("organization is outside the active scope.")
    if hasattr(orm, "tenant_id"):
        active_tenant_id = getattr(ctx, "tenant_id", None)
        tenant_id = getattr(orm, "tenant_id", None)
        if tenant_id is None and active_tenant_id is not None:
            setattr(orm, "tenant_id", active_tenant_id)
        elif not self._tenant_in_scope(ctx, tenant_id):
            raise BusinessRuleError("tenant is outside the active scope.")
```

This is called from `add()` implementations. It auto-fills missing `organization_id` and `tenant_id` from context, and raises if a pre-set value is out of scope.

### `update_with_version_check` Extra Filters

Optimistic locking updates (`update_with_version_check()` from `infra/persistence/db/optimistic.py`) accept an optional `extra_filters` dict. Some repositories pass tenant/org filters here to prevent cross-tenant updates even via the update path. Not all repositories use this; it is applied inconsistently.

### Summary of Scope Pattern Risk Matrix

| Pattern | Read Safety | Write Safety | Silent Miss Risk |
|---|---|---|---|
| A — Inline WHERE | High | N/A | Low (explicit columns) |
| B — `_apply_scope()` | Medium | N/A | **High** (hasattr misses) |
| C — `_get_in_scope()` | High | N/A | Medium (depends on B) |
| D — JOIN-anchor | High | N/A | Medium (depends on B) |
| E — Guard before query | Medium | Medium | Low (guard explicit) |
| `_stamp_scope` | N/A | High | **High** (hasattr misses) |

---

## 9. Current Risks

### Critical

| # | Risk | Location | Impact |
|---|---|---|---|
| C-1 | `set_active_tenant()` has no membership check. Any authenticated user can switch to any active tenant. | `TenantContextService.set_active_tenant()` | Full data breach across tenants |
| C-2 | `_deactivate_other_organizations()` is not tenant-scoped. Activating an organization deactivates all organizations in other tenants. | `OrganizationService._deactivate_other_organizations()` | Cross-tenant data disruption |
| C-3 | `username` is globally unique. No per-tenant username isolation. A user from Tenant A cannot have the same username as a user in Tenant B. | `users.username UNIQUE` | User enumeration, broken tenant onboarding |

### High

| # | Risk | Location | Impact |
|---|---|---|---|
| H-1 | `is_platform_admin()` checks `"platform.admin"` permission that is never seeded. Always returns `False`. Dead code. | `UserSessionContext.is_platform_admin()` | Future code relying on this will silently grant no access |
| H-2 | Custom PBKDF2-SHA256 password hashing. State-of-the-art is argon2id. | `src/core/platform/auth/passwords.py` | Weaker resistance to GPU-accelerated cracking |
| H-3 | MFA is implemented in the backend but the UI login screen never collects a TOTP code. MFA is non-functional. | UI login screen | MFA provides no actual protection |
| H-4 | `user_roles` unique constraint is on `(user_id, role_id)` only. Prevents multi-org role assignment. | `user_roles` table schema | Broken RBAC for multi-org users |
| H-5 | No `tenant_admin` or `org_admin` role. The only role with management permissions is `admin`, which is a global superuser. | `DEFAULT_ROLE_PERMISSIONS` in `policy.py` | No delegated administration within a tenant |
| H-6 | `UserRepository.list_all()` (referenced indirectly via `AuthService.list_users()`) is not tenant-scoped. Returns all users across all tenants. | `user_admin_service.list_users()` | Information disclosure |
| H-7 | Roles and permissions are platform-global. No per-tenant custom roles are supported. | `roles`, `permissions` tables | Cannot customize RBAC per tenant |

### Medium

| # | Risk | Location | Impact |
|---|---|---|---|
| M-1 | `ScopedAccessGrant.tenant_id` is nullable. For non-organization scope types (e.g. `"project"`), the tenant link may be absent. | `scoped_access_grants.tenant_id` | Grants may persist across tenant switches |
| M-2 | Session validation is throttled to once per 60 seconds. Revoked sessions remain valid for up to 60 seconds. | `_SESSION_VALIDATION_THROTTLE_SECONDS = 60` in `session_service.py` | Short window of access after session revocation |
| M-3 | `_apply_scope()` uses `getattr(orm_model, column_name, None)`. A misspelled or missing attribute silently disables the scope filter. | `ProjectManagementTenantScopedRepositorySupport._apply_scope()` | Silent data leakage across tenants |
| M-4 | `get_default()` on `TenantRepository` returns the first active tenant by `tenant_code ASC`. Used as fallback. In a multi-tenant DB this returns an arbitrary tenant. | `TenantContextService.get_active_tenant()` | Context set to wrong tenant silently |
| M-5 | `OrganizationRepository.get_active()` is not scoped by tenant. Returns any organization with `is_active=True`. | `OrganizationService.get_active_organization()` | Returns foreign tenant's organization |
| M-6 | `employees.organization_id` is nullable. Employees without an organization are invisible to scope-filtered queries but can be created. | `EmployeeORM.organization_id` nullable | Orphaned employees bypass tenant queries |
| M-7 | `time_entries.organization_id` is nullable. Entries without an org are not scope-filtered. | `TimeEntryORM.organization_id` nullable | Time entries can escape org scope |
| M-8 | `timesheet_periods.organization_id` is nullable. Same risk as time entries. | `TimesheetPeriodORM.organization_id` nullable | Timesheet periods can escape org scope |

---

## 10. Current Gaps

### Tenant Management

| Gap | Description |
|---|---|
| No `create_tenant` API | There is no application-layer service method to create a new tenant. Tenants can only be seeded via `bootstrap_defaults()` or directly in the database. |
| No `list_tenants` API | No service method to enumerate tenants for administrative purposes. |
| No `deactivate_tenant` API | No soft-delete / deactivation flow for tenants. |
| No tenant deactivation cascade | Deactivating a tenant does not cascade to its organizations, preventing child data from remaining accessible. |
| No tenant-level audit log | `audit_entries` is scoped to `(tenant_id, organization_id)` but there is no dedicated tenant-level audit view. |
| Tenant switcher UI missing | No UI affordance for switching between tenants. The Admin Console only switches organizations. |

### User and Identity Management

| Gap | Description |
|---|---|
| No `user_tenants` table | There is no join table recording which users belong to which tenants. Membership cannot be enforced or queried. |
| No user invite flow | There is no email-based or code-based invitation system for adding users to a tenant. |
| Username globally unique | Usernames must be unique across all tenants. Per-tenant username uniqueness requires a schema change to `users`. |
| No bulk role assignment | Roles can only be assigned one at a time via `assign_role()`. |
| No role expiry support | Role assignments are permanent; there is no `expires_at` on `user_roles`. |
| No email invitation system | Users must be created by an admin. There is no self-service registration. |

### Role and Permission Gaps

| Gap | Description |
|---|---|
| `tenant_admin` role missing | No role exists for administering a single tenant without superuser access. |
| `org_admin` role missing | No role exists for administering a single organization. |
| `site_admin` role missing | No site-scoped administrative mechanism exists. |
| `department_manager` role missing | No department-scoped role exists. |
| Custom per-tenant roles impossible | All roles are platform-global. Tenants cannot define their own roles or permissions. |
| `platform.admin` permission never seeded | The permission code `"platform.admin"` is checked by `is_platform_admin()` but never added to `DEFAULT_PERMISSIONS`. |
| `organization.access` permission never enforced | The code exists in `DEFAULT_PERMISSIONS` but `_can_access()` in `TenantContextService` does not check for it explicitly. |

### Provisioning Gaps

| Gap | Description |
|---|---|
| `provision_organization()` has no `tenant_id` param | `OrganizationService.bootstrap_defaults()` creates an organization with no `tenant_id` binding. |
| No default calendar seeded at org creation | Creating an organization does not automatically seed a default platform calendar. |
| No default entitlements seeded at org creation | No initial module entitlements are created when a new organization is provisioned. |

### Access Control Gaps

| Gap | Description |
|---|---|
| `_deactivate_other_organizations()` cross-tenant bug | Described in Section 3.3. Must be scoped by `tenant_id` before multi-tenant deployment. |
| `user_roles` constraint prevents multi-org assignment | Described in Section 6.3. Requires migration to `UNIQUE(user_id, role_id, organization_id)`. |
| SoD bypassable via `scoped_access_grants` | SoD is only checked at role-assignment time via `DEFAULT_ROLE_PERMISSIONS`. Direct permission grants through `scoped_access_grants` bypass SoD enforcement entirely. |
| `admin` role bypasses SoD | The SoD enforcer explicitly skips the check if `"admin"` is in the role list. |
| No site-scoped access mechanism | `scoped_access_grants` supports arbitrary `scope_type` values, but there are no site-level checks in any service or repository. |

---

*End of Sections 1–10.*
