# Enterprise Platform Architecture

> **Status:** Living Document · **Version:** 1.0 · **Date:** 2026-06-17
>
> This document captures the complete enterprise architecture review of the Project Manager Lite platform.
>
> **Scope correction (2026-08-20):** Maintenance is no longer a current product module. Any
> Maintenance roles, permissions, services, QML, or tables described below are historical audit,
> proposal, or retained migration-schema context, not current runtime composition.
> It consolidates all findings from the Tenant Architecture Review (Deliverables 1–5) and extends them
> with 14 additional architectural analyses covering data ownership, RBAC, lifecycle management, security,
> governance, and deployment readiness.
>
> **Do not modify code based on this document without going through the formal planning process.**

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
11. [Deliverable 6 — Data Ownership Model](#11-deliverable-6--data-ownership-model)
12. [Deliverable 7 — Global vs Tenant vs Organization Matrix](#12-deliverable-7--global-vs-tenant-vs-organization-matrix)
13. [Deliverable 8 — Enterprise RBAC Hierarchy](#13-deliverable-8--enterprise-rbac-hierarchy)
14. [Deliverable 9 — Context Model](#14-deliverable-9--context-model)
15. [Deliverable 10 — User Lifecycle Management](#15-deliverable-10--user-lifecycle-management)
16. [Deliverable 11 — Tenant Lifecycle Management](#16-deliverable-11--tenant-lifecycle-management)
17. [Deliverable 12 — Organization Lifecycle Management](#17-deliverable-12--organization-lifecycle-management)
18. [Deliverable 13 — Site & Department Security Model](#18-deliverable-13--site--department-security-model)
19. [Deliverable 14 — Module Entitlement Strategy](#19-deliverable-14--module-entitlement-strategy)
20. [Deliverable 15 — Tenant Readiness Assessment](#20-deliverable-15--tenant-readiness-assessment)
21. [Deliverable 16 — Repository Governance Standard](#21-deliverable-16--repository-governance-standard)
22. [Deliverable 17 — Audit vs Activity vs Domain Events](#22-deliverable-17--audit-vs-activity-vs-domain-events)
23. [Deliverable 18 — Platform Governance Model](#23-deliverable-18--platform-governance-model)
24. [Deliverable 19 — Migration Readiness Report](#24-deliverable-19--migration-readiness-report)
25. [Recommended Future Roadmap](#25-recommended-future-roadmap)

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

Location: `src/core/platform/domain/security/auth/credentials/passwords.py`

The implementation uses **Argon2id** through `argon2-cffi`, with explicit costs of 19 MiB memory, 2 iterations, parallelism 1, a 16-byte random salt, and a 32-byte hash. The stored value uses standard PHC encoding:

```
$argon2id$v=19$m=19456,t=2,p=1$<salt>$<hash>
```

PBKDF2 and non-Argon2id hashes are rejected because the product is pre-release. Valid Argon2id hashes with obsolete costs are upgraded after password and MFA verification and persisted atomically with successful authentication.

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

---

# 11. DELIVERABLE 6 — DATA OWNERSHIP MODEL

---

## 11.1 Ownership Level Definitions

The codebase recognises eight discrete ownership levels. Each level defines the authoritative scope at which an entity is created, governed, and deleted. These levels form a strict hierarchy; data at a lower level always falls within the boundary of the level above it and can never exist outside that boundary.

| # | Ownership Level | Definition |
|---|-----------------|------------|
| 1 | **GLOBAL** | Entity belongs to the platform itself and is shared across all tenants and organisations. No tenant_id or org_id column is present. Changes to global entities affect every tenant simultaneously. Includes the identity primitives: `users`, `roles`, `permissions`, `role_permissions`. |
| 2 | **TENANT** | Entity carries a `tenant_id NOT NULL` column that directly binds it to one tenant. The tenant boundary is the outermost hard isolation wall. No cross-tenant read or write is ever permitted regardless of user privilege. Includes organisational structure tables, audit machinery, document management, scheduling primitives, resource pools, portfolio constructs, module entitlements, and all domain tables owned at the tenant level (inventory, maintenance roots, etc.). |
| 3 | **ORGANIZATION** | Entity carries both `tenant_id` and `organization_id`, placing it inside a specific organisation within a tenant. The organisation boundary controls which business unit owns and operates the data. The primary example is `projects`, which are owned by an organisation but are hard-scoped to its parent tenant. |
| 4 | **SITE** | Entity is scoped to a physical or logical site within a tenant. `departments` are associated with a site, meaning their lifecycle and visibility follow site boundaries in addition to tenant boundaries. |
| 5 | **DEPARTMENT** | Entity is scoped to a department within a site and organisation. `employees` belong to a department, establishing the most granular unit of the organisational hierarchy (Tenant → Organization → Site → Department → Employee). |
| 6 | **PROJECT** | Entity has no direct `tenant_id` column but inherits tenant scope through its parent project. All project sub-entities (`tasks`, `task_assignments`, `project_resources`, `baselines`, `baseline_tasks`, `cost_items`, `register_items`, `collaboration_threads`) obtain their security and lifecycle boundaries entirely from the project that owns them. Deletion of the project cascades through the entire project scope. |
| 7 | **ASSET** | Entity has no direct `tenant_id` column but inherits tenant scope through its parent asset or work order. Maintenance sub-entities (`work_order_tasks`, `asset_components`, `sensor_readings`) are owned by a specific maintenance asset or work order rather than by an organisation or project. |
| 8 | **USER** | Entity stores per-session metadata for a specific user. `auth_sessions` carry `last_active_tenant_id` and `last_active_organization_id` as informational fields only. These values describe the user's last known context but are non-authoritative. |

---

## 11.2 Complete Entity Classification

| Entity | Ownership Level | Mechanism | Security Boundary | Lifecycle Boundary | Parent Entity |
|--------|----------------|-----------|-------------------|--------------------|---------------|
| `users` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `roles` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `permissions` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `role_permissions` | GLOBAL | No tenant_id / org_id column | Platform administrator | Role lifecycle | `roles` + `permissions` |
| `user_roles` | GLOBAL + optional org FK | No tenant_id; optional organization_id FK | Platform admin / org admin (org-scoped) | Role assignment lifecycle | `users` + `roles` |
| `auth_sessions` | USER | last_active_tenant_id / last_active_organization_id are metadata only | User (self only) | User session lifecycle | `users` |
| `organizations` | TENANT | `tenant_id NOT NULL` | Tenant administrator | Tenant provisioning | Tenant |
| `sites` | TENANT | `tenant_id NOT NULL` + org FK | Tenant / org administrator | Organisation lifecycle | `organizations` |
| `departments` | TENANT / SITE | `tenant_id NOT NULL`; scoped to site | Org / site administrator | Site lifecycle | `sites` |
| `employees` | TENANT / DEPARTMENT | `tenant_id NOT NULL`; scoped to department | Org / department administrator | Department lifecycle | `departments` |
| `parties` | TENANT | `tenant_id NOT NULL` | Tenant administrator | Tenant lifecycle | Tenant |
| `approval_requests` | TENANT | `tenant_id NOT NULL` | Tenant / org administrator | Business process lifecycle | Tenant |
| `audit_logs` | TENANT | `tenant_id NOT NULL` | Read-only; platform/tenant administrator | Retention policy / tenant lifecycle | Tenant |
| `document_structures` | TENANT | `tenant_id NOT NULL` | Tenant / org administrator | Tenant lifecycle | Tenant |
| `documents` | TENANT | `tenant_id NOT NULL` | Tenant / org administrator | Document structure lifecycle | `document_structures` |
| `platform_calendars` | TENANT | `tenant_id NOT NULL` | Tenant administrator | Tenant lifecycle | Tenant |
| `shift_patterns` | TENANT | `tenant_id NOT NULL` | Tenant / org administrator | Tenant lifecycle | Tenant |
| `resources` | TENANT | `tenant_id NOT NULL` | Tenant / org administrator | Tenant lifecycle | Tenant |
| `time_entries` | TENANT | `tenant_id NOT NULL` | Employee / org administrator | Timesheet period lifecycle | `timesheet_periods` |
| `timesheet_periods` | TENANT | `tenant_id NOT NULL` | Org / HR administrator | Payroll calendar lifecycle | Tenant |
| `portfolio_scoring_templates` | TENANT | `tenant_id NOT NULL` | Portfolio manager / tenant admin | Tenant lifecycle | Tenant |
| `portfolio_intake_items` | TENANT | `tenant_id NOT NULL` | Portfolio manager / org admin | Portfolio scenario lifecycle | `portfolio_scenarios` |
| `portfolio_scenarios` | TENANT | `tenant_id NOT NULL` | Portfolio manager / tenant admin | Tenant lifecycle | Tenant |
| `organization_module_entitlements` | TENANT | `tenant_id NOT NULL` | Tenant administrator | Tenant subscription lifecycle | Tenant |
| `scoped_access_grants` | TENANT | `tenant_id NOT NULL`; polymorphic scope_type + scope_id | Tenant / org administrator | Scope object lifecycle | Tenant + scope object |
| `projects` | ORGANIZATION | `tenant_id NOT NULL` + `organization_id` FK | Org administrator / project manager | Organisation lifecycle | `organizations` |
| `tasks` | PROJECT | No tenant_id; scoped through parent project | Project manager / task assignee | Project lifecycle | `projects` |
| `task_assignments` | PROJECT | No tenant_id; scoped through parent task | Project manager | Task lifecycle | `tasks` |
| `project_resources` | PROJECT | No tenant_id; join of project + resource | Project manager | Project lifecycle | `projects` + `resources` |
| `project_baselines` | PROJECT | No tenant_id; scoped through parent project | Project manager | Project lifecycle | `projects` |
| `baseline_tasks` | PROJECT | No tenant_id; scoped through parent baseline | Project manager | Baseline lifecycle | `project_baselines` |
| `cost_items` | PROJECT | No tenant_id; scoped through parent project | Project manager / finance admin | Project lifecycle | `projects` |
| `register_items` | PROJECT | No tenant_id; scoped through parent project | Project manager | Project lifecycle | `projects` |
| `collaboration_threads` | PROJECT | No tenant_id; scoped through parent project | Project member | Project lifecycle | `projects` |
| `project_memberships` | PROJECT | project_id + user_id + organization_id + scope_role | Project manager / org admin | Project lifecycle | `projects` |
| `portfolio_calendar_assignments` | PROJECT (scope-inherited) | Scoped through portfolio/project reference | Portfolio manager | Portfolio lifecycle | Portfolio / `projects` |
| `inventory_items` | TENANT | `tenant_id NOT NULL` | Inventory manager | Tenant lifecycle | Tenant |
| `storerooms` | TENANT | `tenant_id NOT NULL` | Inventory manager / org admin | Tenant lifecycle | Tenant |
| `purchase_orders` | TENANT | `tenant_id NOT NULL` | Procurement manager | Tenant lifecycle | Tenant |
| `po_receipts` | TENANT | `tenant_id NOT NULL` | Warehouse / procurement staff | Purchase order lifecycle | `purchase_orders` |
| `inventory_reservations` | TENANT | `tenant_id NOT NULL` | Inventory manager | Tenant lifecycle | Tenant |
| `item_catalog_entries` | TENANT | `tenant_id NOT NULL` | Inventory / catalog administrator | Tenant lifecycle | Tenant |
| `inventory_lots` | TENANT | `tenant_id NOT NULL` on root; inherited via item/storeroom | Inventory manager | Item / storeroom lifecycle | `inventory_items` / `storerooms` |
| `reservation_lines` | TENANT (scope-inherited) | Scoped through parent reservation | Inventory manager | Reservation lifecycle | `inventory_reservations` |
| `assets` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `work_orders` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `work_requests` | TENANT | `tenant_id NOT NULL` | Any authorised user | Tenant lifecycle | Tenant |
| `sensors` | TENANT | `tenant_id NOT NULL` | Maintenance / IoT administrator | Tenant lifecycle | Tenant |
| `reliability_records` | TENANT | `tenant_id NOT NULL` | Maintenance engineer | Tenant lifecycle | Tenant |
| `preventive_maintenance_plans` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `preventive_maintenance_templates` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `work_order_tasks` | ASSET | No tenant_id; scoped through work_orders | Maintenance technician | Work order lifecycle | `work_orders` |
| `asset_components` | ASSET | No tenant_id; scoped through assets | Maintenance manager | Asset lifecycle | `assets` |
| `sensor_readings` | ASSET | No tenant_id; scoped through sensors | IoT pipeline | Sensor lifecycle | `sensors` |

---

## 11.3 ASCII Ownership Hierarchy Diagram

```
GLOBAL
├── users
├── roles
├── permissions
├── role_permissions
└── user_roles  (GLOBAL with nullable organization_id FK)

TENANT
├── organizations
├── sites                              ← tenant_id + org FK
├── departments                        ← tenant_id + site FK
├── employees                          ← tenant_id + department FK
├── parties
├── approval_requests
├── audit_logs
├── documents
├── document_structures
├── platform_calendars
├── shift_patterns
├── resources
├── time_entries
├── timesheet_periods
├── portfolio_scenarios
├── portfolio_intake_items             ← child of portfolio_scenarios
├── portfolio_scoring_templates
├── organization_module_entitlements
└── scoped_access_grants

ORGANIZATION  (scoped through tenant)
└── projects                           ← tenant_id NOT NULL + organization_id FK

PROJECT  (scope-inherited through organization → tenant)
├── tasks
├── task_assignments                   ← child of tasks
├── project_resources                  ← join: projects + resources
├── project_baselines
├── baseline_tasks                     ← child of project_baselines
├── cost_items
├── register_items
├── collaboration_threads
├── project_memberships
└── portfolio_calendar_assignments

MAINTENANCE  (TENANT root → ASSET sub-scope)
├── [TENANT]  assets
├── [TENANT]  work_orders
├── [TENANT]  work_requests
├── [TENANT]  sensors
├── [TENANT]  reliability_records
├── [TENANT]  preventive_maintenance_plans
├── [TENANT]  preventive_maintenance_templates
└── [ASSET scope-inherited]
    ├── work_order_tasks               ← child of work_orders
    ├── asset_components               ← child of assets
    └── sensor_readings                ← child of sensors

INVENTORY  (TENANT)
├── inventory_items
├── storerooms
├── purchase_orders
├── po_receipts                        ← child of purchase_orders
├── inventory_reservations
├── item_catalog_entries
└── [scope-inherited]
    ├── inventory_lots                 ← via inventory_items / storerooms
    └── reservation_lines              ← child of inventory_reservations

USER  (session metadata — non-authoritative)
└── auth_sessions
    ├── last_active_tenant_id          (informational metadata only)
    └── last_active_organization_id    (informational metadata only)
```

---

## 11.4 Security Boundary Analysis

| Ownership Level | Create | Read | Update | Delete |
|-----------------|--------|------|--------|--------|
| **GLOBAL** | Platform admin only | Platform admin; read-only subsets for role assignment exposed to lower levels | Platform admin only | Platform admin only; role/permission deletion is a breaking platform operation |
| **TENANT** | Platform admin (tenant provisioning) or tenant admin for sub-entities | Tenant admin and any principal whose resolved tenant_id matches the record | Tenant admin (structural); authorised org/dept principals for domain entities within their scope | Tenant admin; cascades through all child entities |
| **ORGANIZATION** | Tenant admin or org admin with module entitlement | Org admin and any member whose organization_id matches; always filtered by parent tenant_id | Org admin or project manager (for projects) | Org admin; cascades through all project-scoped children |
| **SITE** | Tenant / org admin | Org and site admins; employees within the site | Site admin | Org / tenant admin; cascades through departments and employees |
| **DEPARTMENT** | Org / site admin | Dept admin; employees assigned to the department | Dept admin | Site / org admin; cascades through employee assignments |
| **PROJECT** | Org admin or project manager (subject to module entitlement) | Project members (via project_memberships and scoped_access_grants) | Project manager; task assignees may update their own tasks | Project manager or org admin; cascades through all scope-inherited project children |
| **ASSET** | Maintenance manager or authorised technician | Maintenance team members; IoT pipeline for sensor_readings | Technician (work_order_tasks); maintenance manager (asset_components); automated pipeline (sensor_readings) | Maintenance manager; cascades to work_order_tasks, asset_components, sensor_readings |
| **USER** | System only (on authentication) | User (self only); platform admin for audit | System only | System on session expiry or explicit logout |

---

## 11.5 Lifecycle Boundary Analysis

| Ownership Level | Created When | Archived When | Deleted When | Parent Deletion Cascade |
|-----------------|-------------|--------------|-------------|-------------------------|
| **GLOBAL** | Platform provisioning; users on registration | Users may be soft-deactivated | Platform admin explicit action | Role deletion cascades to role_permissions and user_roles |
| **TENANT** | Tenant admin provisions new org/site/dept/domain record | Soft-archived (status flag) on decommission | Tenant admin explicit delete; bulk cascade on tenant deprovisioning | All TENANT-level entities cascade when tenant is deprovisioned |
| **ORGANIZATION** | Org admin creates project; platform/tenant admin creates org | Projects archived on completion; orgs suspended without deletion | Org admin deletes project; tenant admin deletes org | Org deletion cascades to all projects and their scope-inherited children |
| **SITE** | Org / tenant admin creates site | Site decommissioned (soft archive) | Org / tenant admin explicit delete | Cascades to departments and employees |
| **DEPARTMENT** | Site / org admin creates department | Department merged or archived | Site / org admin explicit delete | Cascades to employee department assignments |
| **PROJECT** | Project manager or org admin | Marked complete or on-hold; baselines snapshot state | Project manager or org admin (usually archived not deleted) | Cascades to all scope-inherited project children |
| **ASSET** | Maintenance manager registers asset / raises work order | Assets decommissioned; work orders closed on completion | Maintenance manager archives or deletes root entity | Asset → asset_components + sensor_readings; work_order → work_order_tasks |
| **USER** | Authentication machinery on login | Sessions not archived | Session TTL expiry or explicit logout | No child entities |

---

## 11.6 Design Principles

**1. Tenant isolation is the outermost hard boundary.**
Every entity that belongs to a tenant carries `tenant_id NOT NULL` as a direct column, or inherits tenant scope through an unbroken chain of FK relationships to a tenant-scoped parent. No query, API endpoint, or background job may return data from more than one tenant in the same result set.

**2. Scope inheritance never crosses tenant boundaries.**
Entities that inherit scope from a parent (tasks from projects, work_order_tasks from work_orders) do so through a chain that always terminates at a TENANT-level root. A child entity cannot be associated with a parent in a different tenant.

**3. Direct and inherited tenant scope are enforced with equal rigour.**
The absence of a `tenant_id` column on a scope-inherited entity does not represent a weaker security posture. The owning service resolves tenant context through the parent chain and applies the same isolation predicate.

**4. Platform-global entities must never carry tenant context.**
`users`, `roles`, `permissions`, and `role_permissions` have no `tenant_id` and must never have one added. Tenant-specific behaviour is achieved through `user_roles` (with nullable `organization_id`), `scoped_access_grants`, and `project_memberships`.

**5. Session metadata is non-authoritative for access control.**
`auth_sessions.last_active_tenant_id` and `last_active_organization_id` are convenience metadata fields. No access-control decision, data filter, or audit record may use these fields as a source of truth.

**6. Project membership scope is independent of the organisational hierarchy.**
A user's membership in a project (via `project_memberships`) grants rights within that project's boundary regardless of whether the user holds a role in the parent organisation. The two access axes are evaluated independently.

**7. Asset scope and inventory scope are orthogonal and must not be conflated.**
Maintenance domain entities (assets, work orders, sensors) and inventory domain entities (inventory items, storerooms, purchase orders) are both rooted at the TENANT level but represent independent ownership trees. Services operating across domains must resolve each entity through its own ownership chain independently.

---

# 12. DELIVERABLE 7 — GLOBAL VS TENANT VS ORGANIZATION MATRIX

This section defines the ownership and filtering scope for every entity in the system. It is derived directly from ORM source inspection, the complete entity catalog, and the auth/policy seeding layer. It supersedes any informal descriptions elsewhere in this document.

---

## Scope Matrix

Column key:
- **PRIMARY** — This is the authoritative isolation boundary for the entity. Queries are hard-filtered at this level.
- **INHERITED** — No direct column exists; the scope is reached by walking a FK chain to a parent that carries the column.
- **FILTER** — A column exists but is nullable or is metadata rather than a hard isolation boundary; it narrows queries but is not the primary constraint.
- *(blank)* — Not applicable at this level.

| Entity | ORM Class | Global (No Scope) | Tenant | Organization | Site | Department | Project | Notes |
|---|---|---|---|---|---|---|---|---|
| **PLATFORM IDENTITY** | | | | | | | | |
| tenants | TenantORM | | PRIMARY | | | | | Root SaaS boundary. No parent FK. |
| organizations | OrganizationORM | | FILTER (tenant_id nullable) | PRIMARY | | | | tenant_id nullable in schema — should be NOT NULL. |
| users | UserORM | PRIMARY | | | | | | No tenant_id. Username globally unique — isolation gap. |
| auth_sessions | AuthSessionORM | | FILTER (last_active_tenant_id) | FILTER (last_active_organization_id) | | | | Scope columns are snapshot metadata, not hard isolation. Crosses user + tenant boundary. |
| **AUTHORIZATION** | | | | | | | | |
| roles | RoleORM | PRIMARY | | | | | | System-level lookup; no scope columns. 18 seeded system roles. |
| permissions | PermissionORM | PRIMARY | | | | | | System-level lookup; no scope columns. 56 seeded codes. |
| role_permissions | RolePermissionORM | PRIMARY | | | | | | Join table; no scope columns. |
| user_roles | UserRoleORM | | | FILTER (organization_id nullable) | | | | No tenant_id. Unique constraint on (user_id, role_id) only — misses organization_id, causing duplicate org-scoped assignments to silently collapse. |
| scoped_access_grants | ScopedAccessGrantORM | | FILTER (tenant_id nullable) | | | | | Polymorphic scope via scope_type + scope_id. Direct but nullable tenant_id. |
| project_memberships | ProjectMembershipORM | | INHERITED (via project) | FILTER (organization_id nullable) | | | PRIMARY | No direct tenant_id. Tenant reachable only through project → tenant_id chain. organization_id nullable. |
| **ORGANIZATION STRUCTURE** | | | | | | | | |
| sites | SiteORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. |
| departments | DepartmentORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | Self-referential parent_department_id hierarchy. tenant_id should be NOT NULL. |
| employees | EmployeeORM | | FILTER (tenant_id nullable) | FILTER (organization_id nullable) | FILTER (site_id nullable) | FILTER (department_id nullable) | | Direct tenant_id and full dimensional FKs — all nullable at ORM level. |
| parties | PartyORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | Vendor/contractor/client master data. tenant_id should be NOT NULL. |
| **ACCESS / CALENDAR ASSIGNMENTS** | | | | | | | | |
| site_calendar_assignments | SiteCalendarAssignmentORM | | INHERITED (via site) | INHERITED (via site) | PRIMARY | | | No direct scope columns. Scope through site_id → sites. |
| department_calendar_assignments | DepartmentCalendarAssignmentORM | | INHERITED (via dept) | INHERITED (via dept) | | PRIMARY | | Scope through department_id → departments. |
| employee_calendar_assignments | EmployeeCalendarAssignmentORM | | INHERITED (via employee) | INHERITED (via employee) | | | | Scope through employee_id → employees. |
| **CALENDAR ENGINE** | | | | | | | | |
| platform_calendars | PlatformCalendarORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. Polymorphic scope_type/scope_id for fine-grained assignment. |
| calendar_working_rules | CalendarWorkingRuleORM | | INHERITED (via calendar) | INHERITED (via calendar) | | | | No direct scope columns. Scope through calendar_id → platform_calendars. |
| calendar_exceptions | CalendarExceptionORM | | INHERITED (via calendar) | INHERITED (via calendar) | | | | Scope through calendar_id. Also carries its own polymorphic scope_type/scope_id. |
| calendar_recurring_events | CalendarRecurringEventORM | | INHERITED (via calendar) | INHERITED (via calendar) | | | | Scope through calendar_id. Also carries its own polymorphic scope_type/scope_id. |
| shift_patterns | ShiftPatternORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. |
| shift_pattern_days | ShiftPatternDayORM | | INHERITED (via shift_pattern) | INHERITED (via shift_pattern) | | | | Scope through shift_pattern_id → shift_patterns. |
| **PROJECT MANAGEMENT** | | | | | | | | |
| projects | ProjectORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id nullable) | | | tenant_id should be NOT NULL. Anchor for all PM inherited-scope entities. |
| project_resources | ProjectResourceORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | No direct scope columns. |
| tasks | TaskORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | No direct scope columns. |
| task_assignments | TaskAssignmentORM | | INHERITED (via task→project) | INHERITED (via task→project) | | | INHERITED | Two-hop inheritance: task_id → tasks → projects. |
| task_dependencies | TaskDependencyORM | | INHERITED (via task→project) | INHERITED (via task→project) | | | INHERITED | Scope via predecessor_task_id / successor_task_id → tasks → projects. |
| task_comments | TaskCommentORM | | INHERITED (via task→project) | INHERITED (via task→project) | | | INHERITED | Scope through task_id → tasks → projects. author_user_id is a plain string, no FK. |
| task_presence | TaskPresenceORM | | INHERITED (via task→project) | INHERITED (via task→project) | | | INHERITED | RTT presence record; scope through task_id → tasks → projects. |
| task_skill_requirements | TaskSkillRequirementORM | | INHERITED (via task→project) | INHERITED (via task→project) | | | INHERITED | Scope through task_id → tasks → projects. |
| project_baselines | ProjectBaselineORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | No direct scope columns. |
| baseline_tasks | BaselineTaskORM | | INHERITED (via baseline→project) | INHERITED (via baseline→project) | | | INHERITED | task_id stored as plain String with no FK constraint. |
| baseline_variance_records | BaselineVarianceRecordORM | | INHERITED (via baseline→project) | INHERITED (via baseline→project) | | | FILTER (denorm) | project_id stored as plain String — no FK constraint. Two-hop via new_baseline_id / superseded_baseline_id → project_baselines. |
| register_entries | RegisterEntryORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | Risk/issue/opportunity register. No direct scope columns. |
| cost_items | CostItemORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | Optional task_id FK. No direct scope columns. |
| calendar_events | CalendarEventORM | | INHERITED (via project) | INHERITED (via project) | | | FILTER (nullable) | Both project_id and task_id optional. Orphaned events (no project_id) have no isolating scope at all. |
| resources | ResourceORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | Direct tenant_id. Also FK to employees.id. tenant_id should be NOT NULL. |
| resource_skills | ResourceSkillORM | | INHERITED (via resource) | INHERITED (via resource) | | | | Scope through resource_id → resources. |
| resource_certifications | ResourceCertificationORM | | INHERITED (via resource) | INHERITED (via resource) | | | | Scope through resource_id → resources. |
| project_calendar_assignments | ProjectCalendarAssignmentORM | | INHERITED (via project) | INHERITED (via project) | | | PRIMARY | Scope through project_id → projects. |
| resource_calendar_assignments | ResourceCalendarAssignmentORM | | INHERITED (via resource) | INHERITED (via resource) | | | | Scope through resource_id → resources. |
| **PORTFOLIO** | | | | | | | | |
| portfolio_scoring_templates | PortfolioScoringTemplateORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. |
| portfolio_intake_items | PortfolioIntakeItemORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. |
| portfolio_scenarios | PortfolioScenarioORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. project_ids stored as JSON string — no FK enforcement. |
| portfolio_project_dependencies | PortfolioProjectDependencyORM | | INHERITED (via project pair) | INHERITED (via project pair) | | | PRIMARY | Scope via predecessor_project_id / successor_project_id → projects. |
| **MAINTENANCE** | | | | | | | | |
| maintenance_locations | MaintenanceLocationORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | Self-referential parent_location_id hierarchy. tenant_id should be NOT NULL. |
| maintenance_systems | MaintenanceSystemORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | Self-referential parent_system_id. tenant_id should be NOT NULL. |
| maintenance_assets | MaintenanceAssetORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | Self-referential parent_asset_id. tenant_id should be NOT NULL. |
| maintenance_asset_components | MaintenanceAssetComponentORM | | INHERITED (via org or asset) | PRIMARY (NOT NULL) | | | | No tenant_id despite being a first-class asset child. Asymmetric with siblings that carry tenant_id. |
| maintenance_sensors | MaintenanceSensorORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. |
| maintenance_sensor_readings | MaintenanceSensorReadingORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. Scope only through organization_id. |
| maintenance_integration_sources | MaintenanceIntegrationSourceORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. |
| maintenance_sensor_source_mappings | MaintenanceSensorSourceMappingORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. |
| maintenance_sensor_exceptions | MaintenanceSensorExceptionORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. acknowledged_by_user_id and resolved_by_user_id are nullable user FKs. |
| maintenance_failure_codes | MaintenanceFailureCodeORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. Self-referential parent_code_id hierarchy. |
| maintenance_downtime_events | MaintenanceDowntimeEventORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FKs to assets, systems, work orders. |
| maintenance_work_requests | MaintenanceWorkRequestORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. |
| maintenance_work_orders | MaintenanceWorkOrderORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. Multiple user FKs (planner, supervisor, closer). |
| maintenance_work_order_tasks | MaintenanceWorkOrderTaskORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FK to maintenance_work_orders. |
| maintenance_work_order_task_steps | MaintenanceWorkOrderTaskStepORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. completed_by_user_id and confirmed_by_user_id as nullable user FKs. |
| maintenance_work_order_material_requirements | MaintenanceWorkOrderMaterialRequirementORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FKs to inventory entities. |
| maintenance_task_templates | MaintenanceTaskTemplateORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. |
| maintenance_task_step_templates | MaintenanceTaskStepTemplateORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FK to maintenance_task_templates. |
| maintenance_preventive_plans | MaintenancePreventivePlanORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. |
| maintenance_preventive_plan_tasks | MaintenancePreventivePlanTaskORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FK to maintenance_preventive_plans. |
| maintenance_preventive_plan_instances | MaintenancePreventivePlanInstanceORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FKs to plans, work_requests, work_orders. |
| **INVENTORY AND PROCUREMENT** | | | | | | | | |
| inventory_item_categories | InventoryItemCategoryORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. |
| inventory_stock_items | StockItemORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. FK to parties (preferred_party_id). |
| inventory_storerooms | StoreroomORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. |
| inventory_stock_balances | StockBalanceORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. FKs to stock_items and storerooms. |
| inventory_stock_transactions | StockTransactionORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. performed_by_user_id nullable user FK. |
| inventory_stock_reservations | StockReservationORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | tenant_id should be NOT NULL. requested_by_user_id nullable user FK. |
| inventory_storage_locations | StorageLocationORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. Self-referential hierarchy. FK to storerooms. |
| inventory_reorder_policies | ReorderPolicyORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. FKs to stock_items, storerooms, storage_locations, parties. |
| inventory_cycle_counts | CycleCountORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. counted_by_user_id nullable user FK. |
| inventory_purchase_requisitions | PurchaseRequisitionORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (requesting_site_id) | | | tenant_id should be NOT NULL. requester_user_id nullable user FK. |
| inventory_purchase_requisition_lines | PurchaseRequisitionLineORM | | INHERITED (via requisition) | INHERITED (via requisition) | | | | No direct scope columns. Scope via purchase_requisition_id → inventory_purchase_requisitions. |
| inventory_purchase_orders | PurchaseOrderORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (site_id) | | | tenant_id should be NOT NULL. FK to parties (supplier). |
| inventory_purchase_order_lines | PurchaseOrderLineORM | | INHERITED (via PO) | INHERITED (via PO) | | | | No direct scope columns. Scope via purchase_order_id → inventory_purchase_orders. |
| inventory_receipt_headers | ReceiptHeaderORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | FILTER (received_site_id) | | | tenant_id should be NOT NULL. received_by_user_id nullable user FK. |
| inventory_receipt_lines | ReceiptLineORM | | INHERITED (via receipt) | INHERITED (via receipt) | | | | No direct scope columns. Scope via receipt_header_id → inventory_receipt_headers. |
| **TIME AND PAYROLL** | | | | | | | | |
| time_entries | TimeEntryORM | | FILTER (tenant_id nullable) | FILTER (organization_id nullable) | FILTER (site_id nullable) | FILTER (department_id nullable) | | All scope columns nullable. Polymorphic owner_type/owner_id + scope_type/scope_id. Also FKs to task_assignments and employees. tenant_id + organization_id should be NOT NULL. |
| timesheet_periods | TimesheetPeriodORM | | FILTER (tenant_id nullable) | FILTER (organization_id nullable) | | | | Both nullable. FK to resources. Should be NOT NULL. |
| **DOCUMENTS** | | | | | | | | |
| document_structures | DocumentStructureORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | Self-referential parent_structure_id hierarchy. tenant_id should be NOT NULL. |
| documents | DocumentORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | | uploaded_by_user_id nullable user FK. tenant_id should be NOT NULL. |
| document_links | DocumentLinkORM | | INHERITED (via org) | PRIMARY (NOT NULL) | | | | No tenant_id. Polymorphic entity reference. |
| **APPROVALS** | | | | | | | | |
| approval_requests | ApprovalRequestORM | | FILTER (tenant_id nullable) | PRIMARY (NOT NULL) | | | FILTER (project_id as string) | project_id stored as plain String with no FK constraint to projects. |
| **OBSERVABILITY** | | | | | | | | |
| activity_entries | ActivityEntryORM | | FILTER (tenant_id nullable) | FILTER (organization_id nullable) | | | | Both nullable. Append-only domain event feed. Also carries workspace_id (plain string, no FK). |
| audit_entries | AuditEntryORM | | FILTER (tenant_id nullable) | FILTER (organization_id nullable) | | | | Both nullable. Compliance log; must never be deleted or updated. workspace_id plain string. |
| **MODULE LICENSING** | | | | | | | | |
| organization_module_entitlements | ModuleEntitlementORM | | FILTER (tenant_id nullable, non-PK) | PRIMARY (PK part) | | | | Composite PK is (organization_id, module_code). tenant_id added as non-PK nullable FK for tenant-level queries. PK structure is incomplete for multi-tenant isolation. |
| **SYSTEM** | | | | | | | | |
| runtime_executions | RuntimeExecutionORM | PRIMARY | | | | | | No scope columns at all. Async execution tracking. requested_by_user_id is a plain string, no FK. |

---

## Scope Pattern Legend

### 1. Direct Column — tenant_id NOT NULL (target/ideal state)

The entity carries its own `tenant_id` column with a FK to `tenants.id` and a NOT NULL constraint. Repository `_apply_scope()` can filter directly without any join. This is the correct pattern for any first-class aggregate root.

**Tables currently in this target state (zero nullable overrides required):** None. Every table that carries tenant_id in this codebase declares it as `nullable=True` at the ORM level, even where the migration added NOT NULL at the DB level. The ORM declaration and the DB constraint are out of sync.

**Tables that carry tenant_id (nullable at ORM layer, intended to be NOT NULL):** organizations, sites, departments, employees, parties, approval_requests, document_structures, documents, platform_calendars, shift_patterns, time_entries, timesheet_periods, activity_entries, audit_entries, scoped_access_grants, projects, resources, portfolio_scoring_templates, portfolio_intake_items, portfolio_scenarios, maintenance_locations, maintenance_systems, maintenance_assets, maintenance_sensors, maintenance_work_requests, maintenance_work_orders, maintenance_preventive_plans, inventory_item_categories, inventory_stock_items, inventory_storerooms, inventory_stock_balances, inventory_stock_transactions, inventory_stock_reservations, inventory_purchase_requisitions, inventory_purchase_orders, inventory_receipt_headers.

### 2. FK Inheritance — Scope Through Parent Chain

The entity has no direct scope column. Its scope is derived by walking one or more FK hops to a parent entity that carries the scope column. The depth of the chain determines query complexity:

- **One hop:** project_resources, project_baselines, register_entries, cost_items, project_calendar_assignments (via projects); resource_skills, resource_certifications, resource_calendar_assignments (via resources); calendar_working_rules (via platform_calendars); shift_pattern_days (via shift_patterns); site_calendar_assignments (via sites); department_calendar_assignments (via departments); employee_calendar_assignments (via employees); document_links (via organizations); inventory_storage_locations, inventory_reorder_policies, inventory_cycle_counts (via organizations); maintenance_asset_components, maintenance_sensor_readings, maintenance_integration_sources, maintenance_sensor_source_mappings, maintenance_sensor_exceptions, maintenance_failure_codes, maintenance_downtime_events, maintenance_work_order_tasks, maintenance_work_order_task_steps, maintenance_work_order_material_requirements, maintenance_task_templates, maintenance_task_step_templates, maintenance_preventive_plan_tasks, maintenance_preventive_plan_instances (via organizations); portfolio_project_dependencies (via projects pair); inventory_purchase_requisition_lines (via purchase_requisitions); inventory_purchase_order_lines (via purchase_orders); inventory_receipt_lines (via receipt_headers).

- **Two hops:** tasks (project_id → projects → tenant_id), task_assignments (task_id → tasks → projects), task_dependencies (task_id → tasks → projects), task_comments (task_id → tasks → projects), task_presence (task_id → tasks → projects), task_skill_requirements (task_id → tasks → projects), calendar_exceptions (calendar_id → platform_calendars → tenant_id), calendar_recurring_events (same).

- **Three hops:** baseline_tasks (baseline_id → project_baselines → project_id → projects), baseline_variance_records (new_baseline_id → project_baselines → project_id → projects).

The `_apply_scope()` method uses `hasattr()` runtime introspection to detect scope columns. Inherited-scope entities have no scope column to detect, meaning they silently receive no tenant filter unless the calling query explicitly joins to the scoped parent. This is the most significant latent cross-tenant data leak vector in the system.

### 3. Platform-Global (No Tenant or Organization Column)

The entity is intentionally cross-tenant. No scope filtering applies. Access must be controlled at the application layer, not the database layer.

**Entities:** users, roles, permissions, role_permissions, runtime_executions.

**Risk:** `users` being platform-global means a user object exists once globally. There is no per-tenant user deactivation. Disabling a user in one tenant deactivates them across all tenants. There is no `user_tenants` membership table to record which tenants a user belongs to.

### 4. Partial Scope — Nullable tenant_id or organization_id

The column exists but is nullable, meaning rows may exist with NULL tenant_id. These rows are invisible to tenant-scoped queries and effectively become platform-global orphans. This pattern is present on every entity that should carry a direct tenant_id, because the ORM models declare `nullable=True` even where the migration enforced NOT NULL at the database layer.

**Additionally, the following entities carry both tenant_id AND organization_id as nullable, creating a two-level partial-scope problem:**
- `time_entries` — all four scope columns (tenant_id, organization_id, site_id, department_id) are nullable.
- `timesheet_periods` — tenant_id and organization_id both nullable.
- `activity_entries` — tenant_id and organization_id both nullable; domain events may be written with neither.
- `audit_entries` — tenant_id and organization_id both nullable; compliance log rows may have no scope anchor.

**Scoped Access Grants specifically:** `scoped_access_grants.tenant_id` is nullable. A grant with NULL tenant_id is a platform-global permission override, which is not the same as a tenant-scoped grant. The unique constraint on (tenant_id, scope_type, scope_id, user_id) permits one NULL-tenant grant per (scope_type, scope_id, user_id) tuple. This is exploitable.

### 5. Session Metadata Scope (Special Case)

`auth_sessions` carries `last_active_tenant_id` and `last_active_organization_id`. These are not isolation boundaries. They record the tenant and organization context that was active when the session was last used. They change with every context switch. They must never be used as a data access filter; they exist only to restore the user's last working context on login.

---

## Cross-Cutting Concerns

The following entities are structurally designed to cross ownership boundaries. Each one requires deliberate handling in the authorization layer.

### auth_sessions — User Crosses Tenant

`auth_sessions` links a globally-scoped `users.id` to a nullable `tenants.id` (last active) and a nullable `organizations.id` (last active). A single session record therefore touches three different scoping layers: the global user identity, the tenant context, and the organization context. Because `set_active_tenant()` performs no membership check before recording the chosen tenant into the session, a user can set any tenant_id into their session metadata without proof of membership.

### user_roles — Missing Tenant Scope

`user_roles` has an optional `organization_id` but no `tenant_id`. The unique constraint is on `(user_id, role_id)` only, ignoring organization_id. This means: (a) a user can only hold each role once globally regardless of which organization or tenant the assignment is for; and (b) org-scoped role assignments for different organizations cannot coexist for the same user+role pair.

### project_memberships — Tenant Reachable Only Through Project Chain

`project_memberships` has no direct tenant_id and only an optional organization_id. Tenant context must be resolved by joining to projects. This makes bulk membership queries across tenants impossible without a multi-table join, and means that deleting a project cascades the memberships without leaving any orphan-detection mechanism.

### scoped_access_grants — Polymorphic Scope With Nullable Tenant

The `scope_type` + `scope_id` polymorphism means the grant applies to any entity type. Because `tenant_id` is nullable, a grant can be issued without being anchored to a specific tenant. Platform-level support operations could exploit this to create cross-tenant access grants by omitting tenant_id.

### approval_requests — Unenforceable Project FK

`approval_requests.project_id` is stored as a plain `String` with no FK constraint to `projects`. This means: (a) deleting a project leaves dangling approval references; (b) the repository cannot join approval_requests to projects to apply tenant scope; and (c) cross-tenant project IDs can be placed in this field without a DB-layer rejection.

### baseline_tasks and baseline_variance_records — Unenforceable task_id

`baseline_tasks.task_id` and `baseline_variance_records.task_id` are plain strings with no FK constraints. Task deletion does not cascade to these records. Tenant scope is not inferable from these fields without resolving the string to a live task and then joining to its project.

### activity_entries and audit_entries — Nullable Both Scope Columns

Both observability tables allow rows where both `tenant_id` and `organization_id` are NULL. This means that audit and activity records for platform-level operations (e.g., user creation, role assignment) have no scope anchor. When a compliance query filters by `tenant_id = X`, these platform-level records are excluded, creating invisible gaps in the audit trail for cross-tenant operations.

### runtime_executions — No Scope, User Referenced as String

`runtime_executions` carries no scope columns. `requested_by_user_id` is stored as a plain string with no FK. There is no mechanism to know which tenant's data an async execution operated on. For compliance and multi-tenant forensics this is a gap.

### organization_module_entitlements — PK Does Not Include Tenant

The composite PK is `(organization_id, module_code)`. `tenant_id` was added later as a non-PK nullable FK. This means the entitlement record is uniquely identified without reference to the tenant. A module_code per organization is globally unique, which is correct only if organization codes are globally unique (they are, via a unique constraint). However, tenant-level licensing queries must join to organizations to resolve the tenant context rather than filtering directly on tenant_id in the PK.

### calendar_events — Orphaned Records Possible

`calendar_events.project_id` is nullable and `calendar_events.task_id` is also nullable. A calendar event with both NULL has no scope anchor whatsoever — it is not global, not tenant-scoped, not org-scoped, and not project-scoped. Such a record is invisible to any scoped query.

---

## Recommended Changes to Scope Model

The following changes are ordered from highest isolation risk to lowest. Each item identifies the entity, its current incorrect or incomplete scope, and the target state.

### R1 — Introduce user_tenants membership table (CRITICAL)

**Current state:** No `user_tenants` table exists. Users are globally registered. Any user can attempt to activate any tenant via `set_active_tenant()` without a membership gate.

**Required change:** Add `user_tenants(id, user_id FK users.id, tenant_id FK tenants.id, is_active, joined_at)` with a unique constraint on `(user_id, tenant_id)`. The `set_active_tenant()` method must query this table before accepting the switch. Deactivating a user within a specific tenant must set `user_tenants.is_active = false` for that row rather than deactivating the global `users` record.

### R2 — Add tenant_id to user_roles and fix unique constraint (CRITICAL)

**Current state:** `user_roles` has no `tenant_id`. Unique constraint is `(user_id, role_id)` only, preventing the same role from being held in two different organizations.

**Required change:** Add `tenant_id FK tenants.id NOT NULL` to `user_roles`. Change the unique constraint to `(user_id, role_id, tenant_id, organization_id)` where `organization_id` participates in uniqueness (using a coalesced sentinel value for NULL to allow multiple NULL-org rows per tenant). This aligns role assignment with the tenant isolation boundary.

### R3 — Make tenant_id NOT NULL at the ORM layer for all direct-scope entities

**Current state:** Every entity that carries `tenant_id` declares it as `nullable=True` in the SQLAlchemy ORM model, even though the migration enforced NOT NULL at the database level. This allows Python code to construct ORM objects without setting tenant_id, which will fail only at the DB commit boundary rather than at object construction time.

**Required change:** Change `nullable=True` to `nullable=False` on `tenant_id` columns in: organizations, sites, departments, employees, parties, approval_requests, document_structures, documents, platform_calendars, shift_patterns, projects, resources, portfolio_scoring_templates, portfolio_intake_items, portfolio_scenarios, maintenance_locations, maintenance_systems, maintenance_assets, maintenance_sensors, maintenance_work_requests, maintenance_work_orders, maintenance_preventive_plans, inventory_item_categories, inventory_stock_items, inventory_storerooms, inventory_stock_balances, inventory_stock_transactions, inventory_stock_reservations, inventory_purchase_requisitions, inventory_purchase_orders, inventory_receipt_headers. Also: time_entries, timesheet_periods, activity_entries, audit_entries, scoped_access_grants.

### R4 — Add tenant_id to maintenance_asset_components (HIGH)

**Current state:** `maintenance_asset_components` has no `tenant_id` despite its parent (`maintenance_assets`) and all sibling entities in the maintenance module carrying one.

**Required change:** Add `tenant_id FK tenants.id NOT NULL` to `maintenance_asset_components`. Apply a migration that back-fills from the parent asset's tenant_id.

### R5 — Add tenant_id to the 14 maintenance and inventory entities that carry only organization_id (HIGH)

**Affected entities:** maintenance_sensor_readings, maintenance_integration_sources, maintenance_sensor_source_mappings, maintenance_sensor_exceptions, maintenance_failure_codes, maintenance_downtime_events, maintenance_work_order_tasks, maintenance_work_order_task_steps, maintenance_work_order_material_requirements, maintenance_task_templates, maintenance_task_step_templates, maintenance_preventive_plan_tasks, maintenance_preventive_plan_instances, inventory_storage_locations, inventory_reorder_policies, inventory_cycle_counts, document_links.

**Required change:** Add `tenant_id FK tenants.id NOT NULL` to each. Back-fill from `organizations.tenant_id` through the existing organization_id FK. This eliminates the two-query join needed to resolve tenant scope and enables `_apply_scope()` to filter directly.

### R6 — Add tenant_id to project_memberships (HIGH)

**Current state:** `project_memberships` has no `tenant_id`. Tenant is resolvable only through project → tenant_id, a two-hop join.

**Required change:** Add `tenant_id FK tenants.id NOT NULL` as a denormalized column. Enforce a check that `project.tenant_id == project_membership.tenant_id` at the service layer. This enables direct tenant filtering on membership queries without joining to projects.

### R7 — Fix the unique constraint on user_roles to include organization_id (HIGH)

**Current state:** Unique constraint is `(user_id, role_id)`. An org-scoped role assignment for org A and a global role assignment for the same (user, role) pair cannot coexist.

**Required change (interim, before R2):** Change the unique constraint to `(user_id, role_id, organization_id)` using a coalesced sentinel. The full fix is R2 above.

### R8 — Add a FK constraint on approval_requests.project_id (MEDIUM)

**Current state:** `approval_requests.project_id` is a plain String with no FK to `projects.id`.

**Required change:** Convert to `ForeignKey("projects.id", ondelete="SET NULL")` with `nullable=True`. Add a migration to clean up any orphaned project_id values.

### R9 — Add FK constraints on baseline_tasks.task_id and baseline_variance_records.task_id (MEDIUM)

**Current state:** Both are plain String fields with no FK constraint.

**Required change:** `baseline_tasks.task_id` should be `ForeignKey("tasks.id", ondelete="SET NULL")` nullable. `baseline_variance_records.task_id` can remain a denormalized string (it is a historical snapshot) but should be documented as such.

### R10 — Enforce NOT NULL on activity_entries and audit_entries scope columns (MEDIUM)

**Current state:** Both `tenant_id` and `organization_id` are nullable on these tables, allowing unanchored compliance and event records.

**Required change:** For `activity_entries`, set `tenant_id NOT NULL` (platform-level events that span tenants should use a dedicated system tenant or a separate platform-event table). For `audit_entries`, same rule applies. Events written during tenant-scoped operations must always carry the tenant_id.

### R11 — Add tenant_id to the PK of organization_module_entitlements (LOW/STRUCTURAL)

**Current state:** Composite PK is `(organization_id, module_code)`. `tenant_id` is a non-PK nullable FK added after the fact.

**Required change:** Reconstruct the PK as `(tenant_id, organization_id, module_code)`. This requires a table rebuild migration. Organization codes are currently globally unique so this is not blocking, but it is architecturally incorrect and will cause problems if the uniqueness constraint is ever relaxed.

### R12 — Add scope to runtime_executions (LOW)

**Current state:** No scope columns. No FK on `requested_by_user_id`.

**Required change:** Add `tenant_id FK tenants.id NOT NULL` and `organization_id FK organizations.id NOT NULL` to `runtime_executions`. Add a proper FK on `requested_by_user_id`. This enables compliance queries to identify which tenant's data each async job processed.

### R13 — Handle orphaned calendar_events (LOW)

**Current state:** `calendar_events` with both `project_id` and `task_id` as NULL have no scope anchor.

**Required change:** Add a DB CHECK constraint or application-layer validation requiring at least one of `project_id` or a new `organization_id` column to be non-null. Alternatively add `organization_id FK organizations.id NOT NULL` as a direct scope column to serve as the fallback isolation boundary for calendar events not attached to a project.


---

# 13. DELIVERABLE 8 — ENTERPRISE RBAC HIERARCHY

---

## 13.1 Current RBAC Implementation

### 13.1.1 Role Model

The system defines **18 platform-global system roles** seeded via `DEFAULT_ROLE_PERMISSIONS` in `src/core/platform/auth/policy.py`. All roles exist in the `roles` table with no `tenant_id` column; they are shared across every tenant in the platform.

| # | Role Name | Type |
|---|-----------|------|
| 1 | viewer | Business |
| 2 | team_member | Business |
| 3 | planner | Business |
| 4 | project_manager | Business |
| 5 | resource_manager | Business |
| 6 | finance | Business (alias for finance_controller) |
| 7 | finance_controller | Business |
| 8 | inventory_manager | Business |
| 9 | maintenance_manager | Business |
| 10 | maintenance_admin | Business (alias for maintenance_manager) |
| 11 | payroll_manager | Business |
| 12 | portfolio_manager | Business |
| 13 | approver | Business |
| 14 | auditor | Business |
| 15 | access_admin | Administrative |
| 16 | security_admin | Administrative |
| 17 | support_admin | Administrative |
| 18 | admin | Superuser |

**Storage schema:**

```
user_roles(user_id FK, role_id FK, organization_id FK nullable)
UNIQUE(user_id, role_id)   -- BUG: organization_id excluded from constraint
```

The `UNIQUE(user_id, role_id)` constraint without `organization_id` means a user can only hold a given role once across the entire platform. This prevents assigning a user `project_manager` in Org A and `viewer` in Org B as distinct scoped bindings via the same role row — it silently collapses to one row, whichever was inserted last. This is a critical schema defect.

---

### 13.1.2 Permission Model

The system defines **56 permission codes** in `DEFAULT_PERMISSIONS` (`src/core/platform/auth/policy.py`). The full catalogue, grouped by domain:

**Project & Task domain**
- `project.read` — View projects
- `project.manage` — Create and edit projects
- `task.read` — View tasks
- `task.manage` — Create and edit tasks

**Time & Scheduling domain**
- `time.read` — View shared labor bookings and time entries
- `time.manage` — Create and edit shared labor bookings and time entries
- `timesheet.submit` — Submit timesheet periods
- `timesheet.approve` — Approve or reject timesheet periods
- `timesheet.lock` — Lock or unlock timesheet periods

**Resource domain**
- `resource.read` — View resources
- `resource.manage` — Create and edit resources

**Employee & People domain**
- `employee.read` — View employee directory records
- `employee.manage` — Create and edit employee directory records

**Inventory & Procurement domain**
- `inventory.read` — View inventory and procurement workspaces
- `inventory.manage` — Create and edit inventory and procurement records

**Maintenance domain**
- `maintenance.read` — View maintenance master data and operational records
- `maintenance.manage` — Create and edit maintenance master data and operational records

**Directory / Reference domain**
- `site.read` — View shared site directory records
- `department.read` — View shared department directory records
- `party.read` — View shared supplier, vendor, and contractor directory records

**Cost & Finance domain**
- `cost.read` — View costs
- `cost.manage` — Create and edit costs
- `finance.read` — View finance snapshots and ledgers
- `finance.manage` — Manage finance controls and adjustments
- `finance.export` — Export finance analytics and ledgers

**Payroll domain**
- `payroll.read` — View payroll periods and summaries
- `payroll.manage` — Manage payroll configuration and prepared runs
- `payroll.approve` — Approve or release payroll runs
- `payroll.export` — Export payroll reports and payment files

**Baseline domain**
- `baseline.manage` — Create baselines
- `baseline.approve` — Approve or reject baselines

**Risk & Register domain**
- `register.read` — View risk, issue, and change register data
- `register.manage` — Create and edit register entries

**Portfolio domain**
- `portfolio.read` — View portfolio intake and scenarios
- `portfolio.manage` — Manage portfolio intake and scenarios

**Collaboration domain**
- `collaboration.read` — View team collaboration activity
- `collaboration.manage` — Post team collaboration updates

**Reporting domain**
- `report.view` — View reports
- `report.export` — Export reports

**Audit domain**
- `audit.read` — View audit history

**Governance / Approvals domain**
- `approval.request` — Submit governed change requests
- `approval.decide` — Approve or reject governed change requests

**Access & Security domain**
- `access.manage` — Manage project memberships and access scope
- `auth.read` — View user and role directory data
- `auth.manage` — Manage users and roles
- `security.manage` — Manage login security, lockouts, and session controls

**Platform / Settings domain**
- `settings.manage` — Manage app settings
- `organization.access` — Access tenant organization context
- `import.manage` — Run governed module data imports
- `support.manage` — Access product support operations

---

### 13.1.3 Role-Permission Matrix (Current 18 Roles)

The following matrix maps each existing role to its permission codes as defined in `policy.py`. A tick (Y) marks granted permissions; a dash (-) marks absent.

| Permission Code | viewer | team_member | planner | project_manager | resource_manager | finance_controller | inventory_manager | maintenance_manager | payroll_manager | portfolio_manager | approver | auditor | access_admin | security_admin | support_admin | admin |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| organization.access | Y | Y | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| project.read | Y | Y | Y | Y | Y | Y | - | - | Y | Y | Y | Y | Y | - | Y | Y |
| project.manage | - | - | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| task.read | Y | Y | Y | Y | Y | Y | - | - | Y | Y | Y | Y | - | - | Y | Y |
| task.manage | - | - | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| time.read | Y | Y | Y | Y | Y | Y | - | Y | Y | Y | Y | Y | - | - | Y | Y |
| time.manage | - | - | Y | Y | - | - | - | Y | - | - | - | - | - | - | - | Y |
| resource.read | Y | Y | Y | Y | Y | Y | - | - | Y | Y | Y | Y | - | - | - | Y |
| resource.manage | - | - | - | - | Y | - | - | - | - | - | - | - | - | - | - | Y |
| employee.read | - | - | - | - | Y | - | - | Y | Y | - | - | - | - | - | - | Y |
| employee.manage | - | - | - | - | Y | - | - | - | Y | - | - | - | - | - | - | Y |
| inventory.read | - | - | - | - | - | - | Y | - | - | - | - | - | - | - | - | Y |
| inventory.manage | - | - | - | - | - | - | Y | - | - | - | - | - | - | - | - | Y |
| maintenance.read | - | - | - | - | - | - | - | Y | - | - | - | - | - | - | - | Y |
| maintenance.manage | - | - | - | - | - | - | - | Y | - | - | - | - | - | - | - | Y |
| site.read | - | - | - | - | Y | - | Y | Y | Y | - | - | - | Y | - | - | Y |
| department.read | - | - | - | - | Y | - | - | - | Y | - | - | - | - | - | - | Y |
| party.read | - | - | - | - | - | Y | Y | Y | - | - | - | - | - | - | - | Y |
| cost.read | Y | Y | Y | Y | - | Y | - | - | - | Y | Y | Y | - | - | - | Y |
| cost.manage | - | - | - | Y | - | Y | - | - | - | - | - | - | - | - | - | Y |
| finance.read | - | - | - | Y | - | Y | - | - | - | - | Y | Y | - | - | - | Y |
| finance.manage | - | - | - | - | - | Y | - | - | - | - | - | - | - | - | - | Y |
| finance.export | - | - | - | Y | - | Y | - | - | - | - | - | - | - | - | - | Y |
| payroll.read | - | - | - | - | - | Y | - | - | Y | - | Y | Y | - | - | - | Y |
| payroll.manage | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | - | Y |
| payroll.approve | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | - | Y |
| payroll.export | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | - | Y |
| baseline.manage | - | - | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| baseline.approve | - | - | - | Y | - | - | - | - | - | - | Y | - | - | - | - | Y |
| register.read | Y | Y | Y | Y | - | Y | - | - | - | Y | Y | Y | - | - | Y | Y |
| register.manage | - | - | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| portfolio.read | - | - | Y | - | - | - | - | - | - | Y | Y | Y | - | - | - | Y |
| portfolio.manage | - | - | - | - | - | - | - | - | - | Y | - | - | - | - | - | Y |
| collaboration.read | Y | Y | Y | Y | Y | - | - | - | - | Y | - | Y | - | - | - | Y |
| collaboration.manage | - | Y | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| report.view | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | Y | - | - | Y | Y |
| report.export | - | - | Y | Y | Y | Y | Y | Y | - | Y | - | - | - | - | - | Y |
| audit.read | - | - | - | - | - | - | - | - | Y | - | - | Y | Y | Y | Y | Y |
| timesheet.submit | - | Y | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |
| timesheet.approve | - | - | - | Y | Y | - | - | - | Y | - | - | - | - | - | - | Y |
| timesheet.lock | - | - | - | - | Y | - | - | - | Y | - | - | - | - | - | - | Y |
| access.manage | - | - | - | - | - | - | - | - | - | - | - | - | Y | - | - | Y |
| auth.read | - | - | - | - | - | - | - | - | - | - | - | - | Y | Y | Y | Y |
| auth.manage | - | - | - | - | - | - | - | - | - | - | - | - | - | - | - | Y |
| security.manage | - | - | - | - | - | - | - | - | - | - | - | - | - | Y | - | Y |
| settings.manage | - | - | - | - | - | - | - | - | - | - | - | - | - | Y | - | Y |
| import.manage | - | - | Y | Y | - | - | Y | Y | - | - | - | - | - | - | - | Y |
| approval.request | - | - | Y | Y | - | Y | Y | Y | - | Y | - | - | - | - | - | Y |
| approval.decide | - | - | - | - | - | - | - | - | - | - | Y | - | - | - | - | Y |
| support.manage | - | - | - | - | - | - | - | - | - | - | - | - | - | - | Y | Y |
| organization.access | Y | Y | Y | Y | - | - | - | - | - | - | - | - | - | - | - | Y |

Notes:
- `finance` role is a direct alias for `finance_controller` (identical permission set in `DEFAULT_ROLE_PERMISSIONS`).
- `maintenance_admin` role is a direct alias for `maintenance_manager` (identical permission set).
- `admin` role receives all 56 permission codes via `set(DEFAULT_PERMISSIONS.keys())`.

---

### 13.1.4 Scoped Access Model

**ScopedAccessGrant** (`scoped_access_grants` table):

```
scoped_access_grants(
    tenant_id,
    scope_type   TEXT,   -- e.g., "project", "site", "department"
    scope_id     TEXT,   -- PK of the scoped entity
    user_id      FK,
    scope_role   TEXT,
    permission_codes_json  TEXT
)
```

The `UserSessionPrincipal` loads these at login via `principal_builder.py` into `scoped_access: dict[scope_type, dict[scope_id, frozenset[permissions]]]`. Authorization checks in `UserSessionContext` then use `has_scope_permission(scope_type, scope_id, permission_code)`.

**ProjectMembership** (`project_memberships` table):

```
project_memberships(
    project_id  FK,
    user_id     FK,
    organization_id FK,
    scope_role  TEXT,  -- "viewer" | "contributor" | "lead" | "owner"
    permission_codes_json TEXT
)
```

Project memberships are a specialised shortcut: they are loaded into `scoped_access["project"]` at principal build time. If `ScopedAccessGrantRepository` is wired, it takes precedence; `ProjectMembershipRepository` is a fallback. Both paths converge to the same `scoped_access["project"]` structure.

**Current scope_type values in use:** `"project"` only (confirmed by codebase scan). `"site"` and `"department"` are structurally available via the grant table but no seeding or UI path creates those grants today.

---

## 13.2 Proposed Enterprise RBAC Hierarchy

### 13.2.1 Role Definitions

#### Role 1 — Platform Admin

| Attribute | Value |
|-----------|-------|
| Role name | `platform_admin` |
| Scope level | Global — all tenants |
| Responsibilities | Full platform control. Cross-tenant visibility. System configuration. Infrastructure-level user management. Incident response. Tenant lifecycle (create, suspend, delete). |
| Permission set | All 56 current codes + new platform management codes: `tenant.manage`, `tenant.suspend`, `platform.config`, `platform.monitor` |
| Limitations | Must be restricted to internal Dintegra staff. Should never hold any business role simultaneously (SoD rule — see Section 13.2.6). Must be provisioned out-of-band, not via the standard user-registration flow. |
| Inheritance | Supersedes all other roles. SoD enforcer must bypass the `admin` shortcut and explicitly check for this role. |
| Storage | Requires new `platform_admin` role row. `is_platform_admin()` in `UserSessionContext` must check `"platform.admin"` permission, which must be seeded into `DEFAULT_PERMISSIONS` and added to this role's permission set. |

**Implementation gap:** `is_platform_admin()` in `UserSessionContext` already checks `"platform.admin" in principal.permissions`, but that permission code is not present in `DEFAULT_PERMISSIONS` and is never seeded by `bootstrap_defaults()`. The check is permanently dead.

---

#### Role 2 — Tenant Admin

| Attribute | Value |
|-----------|-------|
| Role name | `tenant_admin` |
| Scope level | Tenant-scoped — cannot access other tenants |
| Responsibilities | Manage organizations within their tenant. Invite and manage users. Configure modules. Set organization-level settings. View tenant-level audit trail. |
| Permission set | `settings.manage`, `auth.read`, `auth.manage`, `organization.access`, `audit.read`, plus new codes: `org.create`, `org.configure`, `user.invite`, `module.configure` |
| Limitations | Cannot modify platform-global configuration. Cannot suspend tenants. Cannot access data belonging to other tenants. All `auth.manage` calls must be scoped to their `tenant_id`. |
| Inheritance | Inherits no business module permissions. Grants are administrative only. |
| Storage | Requires new `tenant_admin` role row plus a `user_tenants` join table so that this role can be bound to `(user_id, tenant_id)` rather than a platform-global row. |

---

#### Role 3 — Organization Admin

| Attribute | Value |
|-----------|-------|
| Role name | `org_admin` |
| Scope level | Organization-scoped |
| Responsibilities | Manage sites, departments, employees, module configuration within their organization. Approve access grants for subordinate scopes. |
| Permission set | `settings.manage` (org-scoped), `auth.read`, `auth.manage` (org-scoped), `employee.manage`, `employee.read`, `site.read`, `department.read`, `organization.access`, `audit.read`, plus new code: `module.read` |
| Limitations | Cannot create new organizations. Cannot manage users outside their org. `auth.manage` writes must be rejected by the repository layer if the target user is not in the same org. |
| Storage | Requires new `org_admin` role row. Binding stored in `user_roles(user_id, role_id, organization_id)` with `organization_id NOT NULL`. |

---

#### Role 4 — Site Admin

| Attribute | Value |
|-----------|-------|
| Role name | `site_admin` (scope role, not a system role row) |
| Scope level | Site-scoped — via `ScopedAccessGrant(scope_type="site", scope_id=<site_id>)` |
| Responsibilities | Manage employees and resources at a specific site. Approve timesheets for site employees. |
| Permission set (scoped) | `employee.manage`, `resource.manage`, `timesheet.approve`, `department.read`, `site.read`, `employee.read` |
| Limitations | Cannot access data for other sites. No org-level write permissions. Cannot modify site configuration or create new sites. |
| Delivery mechanism | Granted via `scoped_access_grants(scope_type="site")`. No new system role row required. The `scope_role` field carries `"site_admin"` as a label. |

---

#### Role 5 — Department Manager

| Attribute | Value |
|-----------|-------|
| Role name | `department_manager` (scope role) |
| Scope level | Department-scoped — via `ScopedAccessGrant(scope_type="department", scope_id=<dept_id>)` |
| Responsibilities | Manage employees and timesheet approvals within a specific department. |
| Permission set (scoped) | `employee.read`, `timesheet.approve`, `resource.read`, `department.read` |
| Limitations | Read-only on all entities outside the department scope. Cannot approve timesheets for employees in other departments. |
| Delivery mechanism | Granted via `scoped_access_grants(scope_type="department")`. |

---

#### Role 6 — Project Manager

| Attribute | Value |
|-----------|-------|
| Role name | `project_manager` (existing system role) |
| Scope level | Organization-scoped, with project-level access granted via `ProjectMembership(scope_role="lead")` |
| Responsibilities | Manage projects, tasks, baselines, resources, costs, and timesheets. Submit and approve governance items within their project scope. |
| Permission set | All current `_PROJECT_MANAGER` permissions: `organization.access`, `project.read`, `project.manage`, `task.read`, `task.manage`, `time.read`, `time.manage`, `resource.read`, `cost.read`, `cost.manage`, `baseline.manage`, `baseline.approve`, `register.read`, `register.manage`, `report.view`, `report.export`, `finance.read`, `finance.export`, `collaboration.read`, `collaboration.manage`, `timesheet.submit`, `timesheet.approve`, `approval.request`, `import.manage`, `portfolio.read` |
| Inheritance | Additive: `project.manage` supersedes `project.read` etc. Project-level grants from `ProjectMembership(scope_role="lead")` add `access.manage` within that project. |

---

#### Role 7 — Supervisor

| Attribute | Value |
|-----------|-------|
| Role name | `supervisor` (new system role) |
| Scope level | Organization-scoped with an employee subset (managed via `ScopedAccessGrant(scope_type="department")` or a direct reports list) |
| Responsibilities | Approve timesheets for direct reports. View employee records for their team. |
| Permission set | `organization.access`, `timesheet.approve`, `employee.read`, `resource.read`, `report.view` |
| Limitations | `timesheet.approve` must be scoped to employees they manage. Without scoped grant enforcement, this role approves all timesheets in the org — the scoped grant mechanism must be used. |

---

#### Role 8 — Power User

| Attribute | Value |
|-----------|-------|
| Role name | `power_user` (new system role) |
| Scope level | Organization-scoped |
| Responsibilities | Full access to all business modules without administrative capabilities. Suitable for senior operational staff who cross module boundaries. |
| Permission set | All domain-specific `.manage` and `.read` codes excluding: `auth.manage`, `security.manage`, `settings.manage`, `access.manage`, `support.manage`. Explicitly: `organization.access`, `project.read`, `project.manage`, `task.read`, `task.manage`, `time.read`, `time.manage`, `resource.read`, `resource.manage`, `employee.read`, `employee.manage`, `inventory.read`, `inventory.manage`, `maintenance.read`, `maintenance.manage`, `site.read`, `department.read`, `party.read`, `cost.read`, `cost.manage`, `finance.read`, `finance.manage`, `finance.export`, `payroll.read`, `payroll.manage`, `payroll.approve`, `payroll.export`, `baseline.manage`, `baseline.approve`, `register.read`, `register.manage`, `portfolio.read`, `portfolio.manage`, `collaboration.read`, `collaboration.manage`, `report.view`, `report.export`, `audit.read`, `timesheet.submit`, `timesheet.approve`, `timesheet.lock`, `import.manage`, `approval.request`, `approval.decide` |
| Limitations | No `auth.manage`, `security.manage`, `settings.manage`, `access.manage`. SoD rules apply: `approval.request` + `approval.decide` conflict must be split off if assigned alongside approver duties. |

---

#### Role 9 — Standard User / Team Member

| Attribute | Value |
|-----------|-------|
| Role name | `team_member` (existing system role) |
| Scope level | Organization-scoped; project-scoped through `ProjectMembership` |
| Responsibilities | Day-to-day task execution, time tracking, collaboration. |
| Permission set | Current `_TEAM_MEMBER`: `organization.access`, `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `register.read`, `report.view`, `collaboration.read`, `collaboration.manage`, `timesheet.submit` |
| Inheritance | Gains `task.manage` (own tasks only) and project-scoped permissions via `ProjectMembership(scope_role="contributor")`. |

---

#### Role 10 — Read-Only User / Viewer

| Attribute | Value |
|-----------|-------|
| Role name | `viewer` (existing system role) |
| Scope level | Organization-scoped |
| Responsibilities | Reporting and observation. No data writes. |
| Permission set | Current `_VIEWER`: `organization.access`, `project.read`, `task.read`, `time.read`, `resource.read`, `cost.read`, `register.read`, `report.view`, `collaboration.read` |

---

#### Role 11 — Guest

| Attribute | Value |
|-----------|-------|
| Role name | `guest` (new role, scope-role only — no system role row required) |
| Scope level | Project-scoped only — via `ProjectMembership(scope_role="viewer")` |
| Responsibilities | Limited external access for contractors and clients. Can see assigned tasks and project summary only. |
| Permission set (scoped) | `project.read`, `task.read` (scoped to assigned tasks only, enforced at query layer) |
| Limitations | No `organization.access`. No org-level data visibility. Cannot view any entity outside the explicitly granted project. Must not appear in `user_roles` with any org-scoped role. |
| Delivery mechanism | Provisioned via `ProjectMembership` only. No org-level `user_roles` row. |

---

### 13.2.2 Role Hierarchy Diagram

```
Platform Admin
  (global, all tenants)
    |
    +-- Tenant Admin
          (tenant-scoped)
            |
            +-- Organization Admin
                  (org-scoped)
                    |
                    +-- Site Admin [scoped grant: scope_type="site"]
                    |     |
                    |     +-- Department Manager [scoped grant: scope_type="department"]
                    |
                    +-- Project Manager [system role + ProjectMembership scope_role="lead"]
                    |     |
                    |     +-- Supervisor [system role + dept scoped grant]
                    |     |
                    |     +-- Team Member [system role + ProjectMembership scope_role="contributor"]
                    |           |
                    |           +-- Viewer [system role]
                    |                 |
                    |                 +-- Guest [ProjectMembership scope_role="viewer", no org role]
                    |
                    +-- Power User [system role, all domain perms, no admin perms]
                          |
                          +-- Standard User / Team Member
                                |
                                +-- Viewer
                                      |
                                      +-- Guest
```

**Inheritance semantics:** The diagram reflects administrative authority hierarchy, not permission inheritance via subclassing. Permissions are additive sets defined per role. "Supersedes" means an admin at a higher scope can manage identities at lower scopes, not that lower-scope permissions are a subset of higher-scope ones.

---

### 13.2.3 Permission Matrix — Proposed Full Role Set

The following extends the current matrix with proposed new roles. New permission codes are marked with `[NEW]`.

| Permission Code | platform_admin | tenant_admin | org_admin | supervisor | power_user | guest | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| tenant.manage [NEW] | Y | - | - | - | - | - | Create/suspend/delete tenants |
| tenant.suspend [NEW] | Y | - | - | - | - | - | Emergency suspension |
| platform.config [NEW] | Y | - | - | - | - | - | Platform-level config |
| platform.monitor [NEW] | Y | - | - | - | - | - | Cross-tenant observability |
| platform.admin [SEED] | Y | - | - | - | - | - | Unlocks is_platform_admin() |
| org.create [NEW] | Y | Y | - | - | - | - | Create new organizations |
| org.configure [NEW] | Y | Y | Y | - | - | - | Configure org settings |
| user.invite [NEW] | Y | Y | Y | - | - | - | Invite users to tenant/org |
| module.configure [NEW] | Y | Y | - | - | - | - | Enable/disable modules |
| module.read [NEW] | Y | Y | Y | - | - | - | View module entitlements |
| organization.access | Y | Y | Y | Y | Y | - | Standard org context |
| project.read | Y | Y | Y | - | Y | Y | |
| project.manage | Y | - | - | - | Y | - | |
| task.read | Y | Y | Y | - | Y | Y | |
| task.manage | Y | - | - | - | Y | - | |
| time.read | Y | - | - | Y | Y | - | |
| time.manage | Y | - | - | - | Y | - | |
| resource.read | Y | - | - | Y | Y | - | |
| resource.manage | Y | - | - | - | Y | - | |
| employee.read | Y | Y | Y | Y | Y | - | |
| employee.manage | Y | Y | Y | - | Y | - | |
| inventory.read | Y | - | - | - | Y | - | |
| inventory.manage | Y | - | - | - | Y | - | |
| maintenance.read | Y | - | - | - | Y | - | |
| maintenance.manage | Y | - | - | - | Y | - | |
| site.read | Y | Y | Y | - | Y | - | |
| department.read | Y | Y | Y | Y | Y | - | |
| party.read | Y | - | - | - | Y | - | |
| cost.read | Y | - | - | - | Y | - | |
| cost.manage | Y | - | - | - | Y | - | |
| finance.read | Y | - | - | - | Y | - | |
| finance.manage | Y | - | - | - | Y | - | |
| finance.export | Y | - | - | - | Y | - | |
| payroll.read | Y | - | - | - | Y | - | |
| payroll.manage | Y | - | - | - | Y | - | |
| payroll.approve | Y | - | - | - | Y | - | SoD risk: see Section 13.2.5 |
| payroll.export | Y | - | - | - | Y | - | |
| baseline.manage | Y | - | - | - | Y | - | |
| baseline.approve | Y | - | - | - | Y | - | SoD risk: see Section 13.2.5 |
| register.read | Y | - | - | - | Y | - | |
| register.manage | Y | - | - | - | Y | - | |
| portfolio.read | Y | - | - | - | Y | - | |
| portfolio.manage | Y | - | - | - | Y | - | |
| collaboration.read | Y | - | - | - | Y | - | |
| collaboration.manage | Y | - | - | - | Y | - | |
| report.view | Y | Y | Y | Y | Y | - | |
| report.export | Y | - | - | - | Y | - | |
| audit.read | Y | Y | Y | - | Y | - | |
| timesheet.submit | Y | - | - | Y | Y | - | |
| timesheet.approve | Y | - | - | Y | Y | - | Must be scoped |
| timesheet.lock | Y | - | - | - | Y | - | |
| access.manage | Y | Y | Y | - | - | - | Manage memberships |
| auth.read | Y | Y | Y | - | - | - | |
| auth.manage | Y | Y | Y | - | - | - | Must be tenant/org scoped |
| security.manage | Y | - | - | - | - | - | Platform Admin only |
| settings.manage | Y | Y | Y | - | - | - | |
| import.manage | Y | - | - | - | Y | - | |
| approval.request | Y | - | - | - | Y | - | SoD: cannot hold approval.decide |
| approval.decide | Y | - | - | - | - | - | Excluded from power_user to avoid SoD conflict |
| support.manage | Y | - | - | - | - | - | |

---

### 13.2.4 Scope Matrix

The following table defines at which scope level each role's permissions are enforced. "Enforced" means the permission check is further filtered by scope before returning data. "Unrestricted" means the role sees all data at that level.

| Role | Global (Platform) | Tenant | Org | Site | Dept | Project | Notes |
|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| Platform Admin | Unrestricted | All | All | All | All | All | Must have `platform.admin` seeded |
| Tenant Admin | — | Own only | All in tenant | — | — | — | Requires `user_tenants` table |
| Org Admin | — | Own | Own only | — | — | — | Bound via `user_roles.organization_id` |
| Site Admin | — | Own | Own | Own site(s) only | — | — | Via `scoped_access_grants(scope_type="site")` |
| Department Manager | — | Own | Own | — | Own dept(s) only | — | Via `scoped_access_grants(scope_type="department")` |
| Project Manager | — | Own | Own | — | — | Assigned projects | Via `ProjectMembership(scope_role="lead")` |
| Supervisor | — | Own | Own | — | Managed team | — | Requires dept scoped grant for timesheet.approve |
| Power User | — | Own | Own | — | — | — | No scope filter applied beyond org |
| Team Member | — | Own | Own | — | — | Assigned projects | Via `ProjectMembership(scope_role="contributor")` |
| Viewer | — | Own | Own | — | — | — | Org-wide read, no project restriction unless granted |
| Guest | — | — | — | — | — | Granted project(s) only | `ProjectMembership(scope_role="viewer")`, no org role |

---

### 13.2.5 Separation of Duties Matrix

#### Existing SoD Rules (from `src/core/platform/auth/sod.py`)

| Rule | Permission A | Permission B | Conflict? | Rule Source | Enforcement |
|---|---|---|:---:|---|---|
| SoD-1 | `approval.request` | `approval.decide` | YES | `sod.py` line 36–39 | `SodEnforcer.enforce_separation_of_duties()` |
| SoD-2 | `access.manage` | `security.manage` | YES | `sod.py` line 40–43 | `SodEnforcer.enforce_separation_of_duties()` |

**Known bypass:** `sod_enforcer.py` returns immediately when `"admin"` is in `normalized` role names (line 18: `if "admin" in normalized: return`). This means the superuser `admin` role bypasses all SoD checks. Similarly, a proxy assignment (granting permissions via `scoped_access_grants.permission_codes_json` directly rather than through role assignment) bypasses the enforcer entirely because `enforce_separation_of_duties()` is only called from `assign_role()`, not from grant creation.

#### Recommended New SoD Rules

| Rule ID | Role A | Role B | Compatible? | Reason | Enforcement Action |
|---|---|---|:---:|---|---|
| SoD-3 | `platform_admin` | Any business role | NOT COMPATIBLE | Platform administration must be segregated from business operations to prevent an operator from both controlling access infrastructure and executing business transactions | Block via SoD policy; raise at role assignment time |
| SoD-4 | `tenant_admin` | `finance_controller` | REVIEW — NOT RECOMMENDED | Tenant admin controls who has finance roles; also holding finance_controller creates a self-grant risk where tenant admin can grant themselves elevated financial access | Treat as incompatible pending governance review |
| SoD-5 | `access_admin` | `security_admin` | NOT COMPATIBLE (existing SoD-2) | Unchanged — same as existing rule | Already enforced |
| SoD-6 | `project_manager` | `approver` | REVIEW — CONDITIONAL | A PM can `approval.request` via planner inheritance; `approver` role holds `approval.decide`. If same user holds both, they can self-approve project baselines and change requests | Recommend: block `approval.decide` for any user already holding `project_manager` on the same project scope |
| SoD-7 | `finance` / `finance_controller` | `payroll_manager` | REVIEW — HIGH RISK | Finance controller can manage finance ledgers; payroll manager can approve and export payroll runs. Combined, a single user can initiate, process, and release payroll without a second reviewer | Recommend: flag as incompatible; enforce at assignment |
| SoD-8 | `payroll_manager` | `approver` | NOT COMPATIBLE | Payroll manager holds `payroll.approve`; approver role holds `approval.decide`. Combined, this user can both produce and sign off payroll-related governed approvals | Block via new SoD policy rule |
| SoD-9 | `platform_admin` | `auditor` | NOT COMPATIBLE | Platform admin can alter audit configuration; also holding auditor creates an ability to audit one's own actions and potentially suppress evidence | Block; audit roles should be held by independent staff |
| SoD-10 | `auth.manage` | `audit.read` | CONDITIONAL | Users who can manage user/role assignments should not have sole custody of the audit log that records those changes | Acceptable only when a separate immutable audit sink exists; flag as advisory |

#### Full SoD Rule Table — Consolidated

| Rule ID | Permission / Role A | Permission / Role B | Compatible? | Classification |
|---|---|---|:---:|---|
| SoD-1 | `approval.request` | `approval.decide` | NO | Existing — enforced |
| SoD-2 | `access.manage` | `security.manage` | NO | Existing — enforced |
| SoD-3 | `platform_admin` role | Any business role | NO | New — required |
| SoD-4 | `tenant_admin` role | `finance_controller` role | NO (recommended) | New — governance review |
| SoD-5 | `project_manager` role | `approver` role (same scope) | NO (conditional) | New — scope-aware |
| SoD-6 | `finance_controller` role | `payroll_manager` role | NO | New — high risk |
| SoD-7 | `payroll_manager` role | `approver` role | NO | New — required |
| SoD-8 | `platform_admin` role | `auditor` role | NO | New — required |
| SoD-9 | `auth.manage` | `audit.read` (sole) | Advisory | New — advisory |

---

## 13.3 Architecture Assessment

### 13.3.1 Can the Current Architecture Support This Hierarchy?

**Partially.** The `scoped_access_grants` mechanism with its generic `(scope_type, scope_id)` design is architecturally sound and can accommodate site-scoped and department-scoped grants without schema changes to that table. The `ProjectMembership` mechanism is adequate for the Guest and Team Member project scope. The `SodEnforcer` is extensible by adding new `SeparationOfDutiesRule` entries.

However, the following structural gaps prevent the full hierarchy from being implemented without migrations and new code.

---

### 13.3.2 What Must Change

**1. `user_roles` unique constraint fix (CRITICAL)**

Current constraint: `UNIQUE(user_id, role_id)`
Required constraint: `UNIQUE(user_id, role_id, organization_id)` (treating NULL as a distinct value per ISO SQL semantics, or using a partial unique index for the global case)

Without this fix, a user cannot hold different scoped role bindings for different organizations. Any attempt to assign a second org-scoped binding silently fails or overwrites.

Migration: `ALTER TABLE user_roles DROP CONSTRAINT <uc_name>; CREATE UNIQUE INDEX ...`

**2. `user_tenants` table (REQUIRED for Tenant Admin)**

A new join table is required to bind users to tenants:

```sql
CREATE TABLE user_tenants (
    user_id         UUID NOT NULL REFERENCES users(id),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tenant_id)
);
```

Without this table, `set_active_tenant()` cannot perform a membership check (current critical bug: it accepts any tenant_id without validating membership).

**3. `tenant_admin` and `org_admin` roles (REQUIRED)**

Two new rows must be added to the `roles` table and seeded into `DEFAULT_ROLE_PERMISSIONS` in `policy.py`. `bootstrap_defaults()` in `default_seed_service.py` must create these roles on first run.

**4. `supervisor` and `power_user` roles (REQUIRED)**

Two new system role rows and corresponding permission sets in `DEFAULT_ROLE_PERMISSIONS`.

**5. `platform.admin` permission code seeded (CRITICAL)**

The permission code `"platform.admin"` must be added to `DEFAULT_PERMISSIONS` in `policy.py` and assigned to the new `platform_admin` role. `is_platform_admin()` in `UserSessionContext` already references this code but it is never present in any principal's permission set, making the check permanently return `False`.

**6. `is_platform_admin()` wired to enforcement (REQUIRED)**

Call sites that require platform-level authorization must replace bare `require_permission(..., "auth.manage")` checks with `is_platform_admin()` or the new `"platform.admin"` permission check. The tenant creation API, tenant suspension API, and cross-tenant user management endpoints all require this guard.

**7. New platform-management permission codes seeded (REQUIRED)**

`tenant.manage`, `tenant.suspend`, `platform.config`, `platform.monitor`, `org.create`, `org.configure`, `user.invite`, `module.configure`, `module.read` must all be added to `DEFAULT_PERMISSIONS`.

**8. Site and department scoped grant enforcement in repositories (REQUIRED)**

`_apply_scope()` in the repository layer currently uses `hasattr()` runtime introspection and silently misses if the column is absent. For site-scoped and department-scoped grants to be effective, query filters must be reliably applied. This requires replacing the `hasattr()` pattern with explicit interface contracts (abstract base class or protocol with `has_org_id: ClassVar[bool]` etc.).

**9. `_deactivate_other_organizations()` tenant-scope fix (CRITICAL BUG)**

The method currently deactivates organizations across all tenants for a user rather than only within the current tenant. It must be updated to filter by `tenant_id` before any tenant-switching logic is deployed.

**10. SoD bypass via `admin` role removed (REQUIRED)**

`sod_enforcer.py` line 18 (`if "admin" in normalized: return`) must be removed or replaced with a check that only exempts `platform_admin` and only for intra-platform assignments, not for business role combinations.

**11. SoD bypass via direct permission grants closed (REQUIRED)**

`SodEnforcer` must also be called from the `ScopedAccessGrant` and `ProjectMembership` creation paths, not only from `assign_role()`. Otherwise, SoD rules are trivially bypassed by granting conflicting permissions directly via JSON rather than via role assignment.

**12. Username global uniqueness (MEDIUM — architecture decision)**

`username UNIQUE` in the `users` table prevents multi-tenant scenarios where two tenants both have a user named `admin` or `john.smith`. Resolution options: (a) enforce `username` uniqueness within a tenant via a partial index and accept the platform-global uniqueness constraint as a guard for now; (b) switch to email-as-username with domain disambiguation; (c) introduce a `tenant_qualified_username` column. This is an architectural decision that must be made before Tenant Admin provisioning is implemented.

**13. MFA enforcement (MEDIUM)**

MFA is non-functional: the UI never collects a TOTP code and `mfa_service.py` exists but is not called in the authentication path for platform-level or tenant-admin accounts. Platform Admin accounts must enforce MFA as a prerequisite to role activation.

**14. Password hashing upgrade (COMPLETE)**

All password creation and verification paths use Argon2id. PBKDF2 compatibility was intentionally removed before release, and platform/tenant administrators use the same canonical password primitive.

**15. Tenant creation API (MISSING)**

No `create_tenant` endpoint exists. Tenant Admin cannot be provisioned until a tenant exists. A privileged `POST /platform/tenants` endpoint, guarded by `platform.admin`, must be created.

---

### 13.3.3 What Can Remain Unchanged

| Component | Status | Notes |
|---|---|---|
| `viewer`, `team_member`, `planner`, `project_manager`, `resource_manager`, `finance_controller`, `inventory_manager`, `maintenance_manager`, `payroll_manager`, `portfolio_manager`, `approver`, `auditor`, `access_admin`, `security_admin`, `support_admin` roles | Retain as-is | Permission sets are appropriate for their scope |
| `scoped_access_grants` table and mechanism | Retain, extend | Add `scope_type="site"` and `scope_type="department"` seeding; table schema is already capable |
| `project_memberships` table and mechanism | Retain | Already supports `scope_role` labels; add `"guest"` as valid scope_role value |
| `UserSessionPrincipal.scoped_access` structure | Retain | Generic `dict[scope_type, dict[scope_id, frozenset[perms]]]` correctly models the site/dept/project hierarchy |
| `SodEnforcer` and `SeparationOfDutiesPolicy` | Retain, extend | Add new `SeparationOfDutiesRule` entries for SoD-3 through SoD-9 |
| `organization_module_entitlements` | Retain | Already has `(organization_id, module_code, licensed, enabled, tenant_id)` — compatible with Tenant Admin module configuration |
| `TenantContextService` resolution chain | Retain after bug fix | Resolution via `UserSessionContext._active_tenant_id` → `principal.active_tenant_id` → `get_default()` is correct after the membership check bug is resolved |
| `DEFAULT_PERMISSIONS` dict in `policy.py` | Retain, extend | Add new codes; existing 56 codes stay as-is |
| `audit.read` on Tenant Admin and Org Admin | Retain | Both roles already need audit trail visibility for their scope |

---

### 13.3.4 Implementation Priority Order

| Priority | Change | Risk if Deferred |
|---|---|---|
| P0 — Before any multi-tenant go-live | `user_roles` unique constraint fix | Silent data loss on org-scoped role binding |
| P0 — Before any multi-tenant go-live | `_deactivate_other_organizations()` tenant-scope fix | Data leakage across tenants |
| P0 — Before any multi-tenant go-live | `set_active_tenant()` membership check | Any user can switch to any tenant |
| P1 — Before Tenant Admin provisioning | `user_tenants` table + migration | Tenant Admin cannot be scoped |
| P1 — Before Tenant Admin provisioning | `tenant_admin` role + seed | Tenant Admin has no role to assign |
| P1 — Before Tenant Admin provisioning | `platform.admin` permission seeded + `is_platform_admin()` wired | Platform Admin enforcement is dead code |
| P1 — Before Tenant Admin provisioning | Tenant creation API | No way to create tenants |
| P2 — Before Site/Dept Admin provisioning | `org_admin` role + seed | Org Admin has no role |
| P2 — Before Site/Dept Admin provisioning | Site/dept scoped grant seeding and UI | Site Admin and Dept Manager cannot be assigned |
| P2 — Before Site/Dept Admin provisioning | `_apply_scope()` `hasattr()` replacement | Site/dept grants granted but silently not enforced |
| P3 — Security hardening | SoD bypass via `admin` shortcut removed | `admin` can hold conflicting permissions |
| P3 — Security hardening | SoD check on grant creation paths | SoD bypassed via direct JSON grants |
| P3 — Security hardening | New SoD rules SoD-3 through SoD-9 added | Role combinations above create undetected conflicts |
| P3 — Security hardening | MFA enforcement for admin tiers | Platform/Tenant Admin accounts are single-factor |
| P4 — Architecture decision | Username global uniqueness resolution | Blocks multi-tenant user onboarding at scale |
| P4 — Architecture decision | argon2id password hashing | Security improvement, not a functional blocker |


---

# 14. DELIVERABLE 9 — CONTEXT MODEL

## Context Definitions

A "context" in this architecture is a piece of session-bound state that scopes all downstream data access, authorization checks, and UI rendering. Each context type is defined below with its current implementation status.

---

### 1. Tenant Context

**What it represents:** The active company (tenant) the user is operating within. All 34 directly tenant-scoped tables require a resolved tenant_id before any repository query can execute. Without a resolved tenant context, no business data is accessible.

**Where it is stored:**
- In-memory: `UserSessionContext._active_tenant_id`
- Persisted: `auth_sessions.last_active_tenant_id`

**How it is resolved:** `TenantContextService.get_active_tenant()` applies the following priority chain:
1. `UserSessionContext._active_tenant_id` (explicit session override)
2. `principal.active_tenant_id` (loaded from last auth_sessions row on login)
3. `TenantContextService.get_default()` (fallback — returns the only active tenant if exactly one exists)

**Who sets it:** `TenantContextService.set_active_tenant()`. Currently called only during bootstrap and login restoration. There is no user-facing tenant-switch flow.

**When it changes:** On login (restored from `auth_sessions.last_active_tenant_id`); on explicit call to `set_active_tenant()` (no UI path today).

**UI visibility recommendation:** HIDDEN from all org-level UIs. Visible only in the Platform Admin console for super-admin accounts. Org-level users should never need to be aware of the tenant boundary.

**Current code:** `src/core/platform/tenancy/tenant_context.py`

**Known gaps:**
- `set_active_tenant()` performs no membership check — any user can be pointed at any tenant_id if the call is made programmatically.
- No `user_tenants` table exists; tenant membership cannot be validated.
- No `list_tenants_for_user()` API exists.
- No tenant switcher UI.

---

### 2. Organization Context

**What it represents:** The active operational division (organization) within the resolved tenant. All business entities — projects, tasks, sites, departments, employees, resources, financials — are scoped to an `organization_id`. This is the primary data-isolation boundary for day-to-day operations.

**Where it is stored:**
- In-memory: `UserSessionContext._active_organization_id`
- Persisted: `auth_sessions.last_active_organization_id`

**How it is resolved:** Priority chain:
1. `UserSessionContext._active_organization_id` (session override)
2. `principal.active_organization_id` (restored from auth_sessions on login)
3. Auto-select if the user has a `scoped_access_grant` for exactly one organization within the active tenant

**Who sets it:** `TenantContextService.set_active_organization()`, surfaced via the Admin Console controller. End users have no shell-level switcher today.

**When it changes:** On login (restored); on explicit org switch via Admin Console; on auto-selection at login if only one org is accessible.

**UI visibility recommendation:** REQUIRED. The active organization name must be visible in the shell header at all times. Users operating across multiple organizations need a shell-level switcher to change it without navigating into the Admin Console.

**Current code:** `src/core/platform/tenancy/tenant_context.py`

**Known gaps:**
- No org switcher in the shell header.
- `_deactivate_other_organizations()` is not tenant-scoped — a bug that could deactivate org sessions across tenant boundaries.
- Multi-org UX is entirely absent from the standard workspace shell.

---

### 3. Site Context

**What it represents:** The active physical site (facility, plant, warehouse, office) within the active organization. Sites carry their own timezone, currency, and calendar, making site context relevant for scheduling, inventory, and maintenance operations.

**Where it is stored:** NOT CURRENTLY IMPLEMENTED. No site_id field exists in `UserSessionContext` or `auth_sessions`.

**How it is resolved:** Not implemented.

**Who sets it:** Not implemented.

**When it changes:** Not applicable today.

**UI visibility recommendation:** REQUIRED in multi-site organizations; OPTIONAL (auto-defaulted) in single-site organizations. In multi-site orgs, the active site name should appear in the shell header alongside org context, with a user-accessible switcher.

**Recommended implementation:**
- Add `site_id` (nullable) to `UserSessionContext` and `auth_sessions`.
- On login, auto-resolve from `employee.site_id` for the authenticated user.
- In `_apply_scope()`, extend scope filtering to include `site_id` for repositories where site-level isolation is needed (inventory, maintenance, calendar).
- Site context is subordinate to org context: switching org must clear and re-resolve site context.

**ORM readiness:** `SiteORM` carries `tenant_id` (nullable FK) and `organization_id` (NOT NULL FK). `SqlAlchemy SiteRepository` already filters by both. The site scoped-access policy is fully registered (`SITE_SCOPE_ROLE_CHOICES`: viewer, operator, manager).

---

### 4. Department Context

**What it represents:** The active organizational unit (business group, functional team) within an organization. Departments carry a cost center code and a manager reference, making department context relevant for financial allocation and approval routing.

**Where it is stored:** NOT CURRENTLY IMPLEMENTED. No department_id field exists in `UserSessionContext` or `auth_sessions`.

**How it is resolved:** Not implemented as session state. The only codebase reference to `scope_type="department"` is in `calendar_exception_service.py` as a metadata label on `CalendarException` records — it is not a security grant.

**Who sets it:** Not applicable. Recommendation is to derive it, not store it.

**UI visibility recommendation:** OPTIONAL. Department context should be derived automatically from `employee.department_id` for the authenticated user rather than stored as an explicit session field. It does not need a user-facing switcher. UI components that need the active department (e.g. approval routing, cost allocation) should read it from the resolved employee record.

**Recommendation:** Do not add `department_id` to `UserSessionContext`. Resolve it lazily from the employee record when needed. If department-scoped access control is ever required (e.g. department-scoped calendar or resource visibility), register a `ScopedRolePolicy` for `"department"` in `platform_registry.py` first.

**ORM readiness:** `DepartmentORM` carries `tenant_id` (nullable FK), `organization_id` (NOT NULL FK), and a self-referential `parent_department_id` for hierarchy. `SqlAlchemy DepartmentRepository` filters by both tenant and org. No `ScopedRolePolicy` is registered for `"department"` today.

---

### 5. Project Context

**What it represents:** The active project the user is currently viewing or editing within a project workspace. Project context gates project-level permission grants (`project_memberships`) and determines which task tree, baseline, and cost data is visible.

**Where it is stored:** NOT in session state. Project context is entirely navigation-driven — it lives in QML workspace state and is passed as a URL/navigation parameter when entering a project workspace.

**How it is resolved:** Navigation parameter in the QML workspace router. The `project_id` is passed explicitly to all presenters and service calls within the project workspace.

**Who sets it:** The user navigating to a project. No session persistence.

**When it changes:** On every workspace navigation event (open project, close project, switch project).

**UI visibility recommendation:** REQUIRED when inside a project workspace (project name visible in workspace header); HIDDEN in all non-project workspaces.

**Note:** `project_memberships(project_id, user_id, organization_id, scope_role, permission_codes_json)` provides project-level permission grants independently of session context. These are resolved per-request by checking membership rows directly, not by reading session state.

---

### 6. Permission Context

**What it represents:** The fully resolved set of permissions available to the current user in the current scope. This is not a single flat set — effective permissions are the union of role-level grants, organization-scoped role grants, scoped_access_grant rows, and project_membership rows, evaluated in order.

**Where it is stored:**
- `UserSessionPrincipal.permissions` (frozenset) — role-level union, built at login
- `scoped_access_grants` rows — evaluated per-request for scoped checks
- `project_memberships` rows — evaluated per-request for project checks

**How it is resolved:** Built at login by `principal_builder.build_principal()`, which unions all `role_permission` rows for the user's active roles. Scoped permissions are not cached in the principal — they are checked live via `require_scope_permission()` and `filter_scope_rows()`.

**Cached:** In-memory for 60 seconds (session validation throttle). After 60 seconds, the session is re-validated against the DB.

**UI visibility recommendation:** HIDDEN from end users. Used internally by `authorization.py`. The Admin Console exposes role assignments (a proxy for permission context) to access administrators.

**Known gap:** `is_platform_admin()` checks for the permission code `"platform.admin"`, which is never seeded into `DEFAULT_PERMISSIONS`. This function always returns False and is effectively dead code.

---

### 7. Role Context

**What it represents:** The set of roles held by the current user — both globally (no org binding) and per-organization. Roles are the mechanism through which permissions are granted in bulk. The 18 system roles span viewer through admin.

**Where it is stored:** `UserSessionPrincipal.role_names` (frozenset), built at login from `user_roles` rows.

**How it is resolved:** At login, `user_roles WHERE user_id = ?` is queried. Rows with `organization_id IS NULL` contribute global roles; rows with `organization_id = active_org` contribute org-scoped roles.

**Known bug:** The unique constraint on `user_roles` is `(user_id, role_id)` only — it does not include `organization_id`. This means a user cannot hold the same role in two different organizations simultaneously, which breaks multi-org deployments.

**UI visibility recommendation:** HIDDEN from end users. Visible in the Admin Console to users with `access.manage` permission. The current user's own roles should not be directly exposed in the shell.

**Known gaps:**
- No `tenant_admin` role exists. Cross-org administrative functions within a tenant have no dedicated role.
- No `org_admin` role exists. Organization-level administration is handled solely by the global `admin` role, which bypasses all scope checks.

---

### 8. Session Context

**What it represents:** The top-level authenticated session object, combining user identity, active tenant, active organization, resolved permissions, and session metadata (last active timestamps, MFA state).

**Where it is stored:**
- In-memory: `UserSessionContext` (process-local, one instance per active user session)
- Persisted: `auth_sessions` (DB row per active session, keyed by session token)

**How it is resolved:** Populated at login by `AuthService` → `authentication_service` → `principal_builder`. On subsequent requests, the session token is validated against `auth_sessions`; re-validation against the DB is throttled to once per 60 seconds.

**UI visibility recommendation:** HIDDEN from end users as a concept. The shell header may surface: display_name, active org name (see Organization Context above), and a logout control.

**Known gaps:**
- MFA is non-functional: the UI never collects a TOTP code. `auth_sessions.mfa_verified` is never set to True via a real TOTP check.
- Password hashing uses canonical Argon2id with explicit OWASP baseline costs; the former PBKDF2 gap is closed.
- The 60-second re-validation window means a revoked session (e.g. after role change) remains valid for up to 60 seconds.

---

## Context Interaction Diagram

The following diagram shows how each context type depends on and is nested within its parent context. All data access operations require the full resolved chain from Session down to at minimum Organization before any business-layer query can execute.

```
Session Context  (auth_sessions + UserSessionContext)
    │
    ├── User Identity  (user_id, username, display_name)
    │
    ├── Tenant Context  ─────────────────────────────── required for ALL data operations
    │       │                                            (tenant_id NOT NULL on 34 tables)
    │       └── Organization Context  ─────────────────  required for ALL business data
    │               │                                    (organization_id NOT NULL on all
    │               │                                     business entities)
    │               │
    │               ├── Site Context  (future)  ──────── optional; auto-default in
    │               │       │                            single-site orgs
    │               │       └── Department Context  ──── derived from employee record,
    │               │               (future)             not stored in session
    │               │
    │               └── Project Context  ───────────────  navigation-driven; not in
    │                       (QML navigation state)        session; resolved per-workspace
    │
    ├── Role Context  ────────────────────────────────── resolved from user_roles at login
    │       (UserSessionPrincipal.role_names)
    │
    └── Permission Context  ─────────────────────────── resolved from role → permissions
            (UserSessionPrincipal.permissions           union + scoped_access_grants
             + scoped_access_grants rows                + project_memberships
             + project_memberships rows)                evaluated per-request
```

Switching any parent context invalidates all child contexts. Specifically:

- Switching Tenant Context must clear and re-resolve Organization, Site, Department, Role, and Permission contexts.
- Switching Organization Context must clear and re-resolve Site, Department, and the org-scoped portion of Role and Permission contexts.
- Switching Site Context (when implemented) must clear and re-resolve Department Context.
- Project Context is stateless with respect to the above chain — it is purely navigation-local and does not affect session state.

---

## Context Requirement Matrix

| Context | Mandatory | Default Behavior | UI Visible | API Required | Notes |
|---|---|---|---|---|---|
| Session Context | Yes | Created at login | No (internal) | Yes — all endpoints | 60s re-validation TTL |
| Tenant Context | Yes | Auto-resolved (single tenant) | No (Platform Admin only) | Yes — all data queries | Missing membership check |
| Organization Context | Yes | Auto-selected if exactly one org accessible | Yes — shell header | Yes — all business queries | No shell switcher today |
| Site Context | No (future) | Auto-default from employee.site_id | Yes in multi-site orgs | Conditional | Not implemented |
| Department Context | No | Derived from employee.department_id | No | No | Not stored in session |
| Project Context | No (workspace-local) | None — must be navigated to | Yes — inside project workspace | Per-workspace | No session persistence |
| Role Context | Yes | Built at login from user_roles | No (Admin Console only) | Yes — permission checks | Missing tenant_admin/org_admin |
| Permission Context | Yes | Built at login from role union | No (internal) | Yes — all authorization checks | Scoped grants checked per-request |

---

## Recommended Context Architecture

### Near-Term (no schema changes required)

1. **Keep Tenant Context hidden and auto-resolved.** For the current single-tenant deployment profile, `get_default()` is sufficient. Do not expose a tenant switcher until `user_tenants` is introduced.

2. **Add organization switcher to the shell header.** The `set_active_organization()` path already exists in `TenantContextService`. Wire it to a shell-level control so users with multi-org access can switch without entering the Admin Console. The active organization name should always be visible in the header.

3. **Auto-default to the single accessible org at login.** The auto-select logic already exists when exactly one org is in scoped_access. Verify this fires reliably on every login path, not just on the happy path through `principal_builder`.

4. **Fix the `user_roles` unique constraint bug.** Alter the constraint from `(user_id, role_id)` to `(user_id, role_id, organization_id)` to support multi-org role assignments.

5. **Fix `_deactivate_other_organizations()` to be tenant-scoped.** This method must filter by `tenant_id` when deactivating org sessions to prevent cross-tenant side effects.

### Medium-Term (requires `user_tenants` schema addition)

1. **Introduce `user_tenants(user_id, tenant_id, granted_at, granted_by)` table.** This table is the prerequisite for all tenant-level access control. `set_active_tenant()` must validate membership here before switching.

2. **Add tenant switcher to the shell header for Platform Admin accounts.** Once `user_tenants` exists, a tenant-aware user (Platform Admin) can be shown a dropdown of their accessible tenants. Standard org-level users never see this control.

3. **Surface tenant name in the shell for multi-tenant deployments.** In a deployment where a Platform Admin operates across multiple tenants, the active tenant name must be visible in the shell header alongside the org name.

4. **Introduce `tenant_admin` role.** Scoped to a single tenant, this role should allow management of all organizations within that tenant without the global bypass behavior of `admin`.

### Long-Term (requires `auth_sessions` and `UserSessionContext` schema extensions)

1. **Add Site Context to `UserSessionContext` and `auth_sessions`.** Add a nullable `site_id` field. Populate it at login from `employee.site_id` for the authenticated user. Persist it in `auth_sessions.last_active_site_id` for session restoration.

2. **Extend `_apply_scope()` for site-aware repositories.** Where applicable (inventory, maintenance, calendar), add site_id to the scope filter chain. This requires moving away from the current `hasattr()` runtime introspection pattern — which silently skips the filter if the column is absent — toward explicit repository interface declarations.

3. **Register a `ScopedRolePolicy` for `"department"` only if department-scoped access control becomes a requirement.** Today, department is not a security boundary — it is an organizational metadata attribute. Do not register it as a scope type preemptively. If department-level access grants are needed (e.g. department-scoped report visibility or approval routing), add the policy registration to `platform_registry.py` and add `filter_scope_rows()` calls to `DepartmentService.list_departments()` at that time.

4. **Resolve Department Context derivatively, not from session state.** When a presenter or service needs the active department, it should read `employee.department_id` for the current user — not a stored session field. This avoids a third explicit context that users must manage.

5. **Harden MFA before adding any new context surface area.** Session context integrity depends on MFA being functional. The current non-functional TOTP implementation (`auth_sessions.mfa_verified` never set to True) means session assurance is weaker than the schema implies. Fix MFA before surfacing tenant or site switchers that could expand a user's data access scope.

---

## Current Architecture Validation

The table below assesses whether the current codebase fully supports each context type as defined in this model.

| Context | Implemented | Complete | Known Gaps |
|---|---|---|---|
| Tenant Context | Yes | Partial | No membership check in `set_active_tenant()`; no `user_tenants` table; no tenant switcher UI; `list_tenants_for_user()` missing |
| Organization Context | Yes | Partial | No shell-level org switcher; `_deactivate_other_organizations()` not tenant-scoped; multi-org UX absent from workspace shell |
| Site Context | No | No | Not implemented anywhere in session layer; `SiteRepository` and `ScopedRolePolicy` are ready but session integration is absent |
| Department Context | No | No | Not implemented; correctly absent from session — should remain derivative of employee record |
| Project Context | Navigation-only | Acceptable | No session persistence is by design; `project_memberships` handles project-level grants correctly |
| Permission Context | Yes | Complete | `is_platform_admin()` dead code (checks unseeded `"platform.admin"` code); otherwise fully functional |
| Role Context | Yes | Partial | Missing `tenant_admin` and `org_admin` roles; `user_roles` unique constraint bug breaks multi-org assignments |
| Session Context | Yes | Partial | Argon2id password hashing is complete; MFA and the 60s session re-validation window remain separate concerns |

---

# 15. DELIVERABLE 10 — USER LIFECYCLE MANAGEMENT

## Current Implementation Assessment

---

### Create User

**Status: PARTIAL**

**Service/method:** `registration_service.register_user()` (module function), exposed as `AuthService.register_user()` in `src/core/platform/auth/application/auth_service.py`.

**What it does:** Normalises username to lowercase, optionally validates email, validates password, checks for duplicate username and duplicate federated identity, applies SoD enforcement on the requested role set, creates a `UserAccount` domain object via `UserAccount.create()`, persists it via `_user_role_repo.add()`, assigns initial roles, and commits. Emits `domain_events.auth_changed` and writes an audit entry (`operation="create"`, `severity="high"`, `compliance_tag="SOC2"`).

**Table/columns set:** `users.id`, `users.username` (normalised lower), `users.password_hash` (Argon2id PHC string via `hash_password()`), `users.display_name`, `users.email` (nullable), `users.is_active` (default True), `users.must_change_password`, `users.session_revision=1`, `users.password_changed_at=now`, `users.created_at`, `users.updated_at`, `users.version=1`. Identity-provider fields populated if federated.

**What is present that the outline assumed missing:**
- `email` column exists on `UserORM` and `UserAccount` (`String(256), nullable=True`).
- `must_change_password` column exists and is set at registration time.

**What is genuinely missing:**
- No `user_tenants` table — new users are not associated with a tenant at creation time. Tenant context is only established via session-context resolution at login.
- No `invited_by_user_id`, `invited_at`, `activation_status`, `email_verified` columns.
- No invitation token flow — users are created directly by an admin with `auth.manage` permission, not through an email acceptance path.
- `email` is stored but never validated for uniqueness. Two users can share an email address.
- No `timezone` user preference column.

---

### Invite User

**Status: NO**

No `InvitationService`, no `invitation_tokens` table, no email delivery integration, no time-limited token generation, and no invitation acceptance endpoint or UI flow exist anywhere in the codebase. The registration path requires the caller (an admin) to directly supply a username and plaintext password. New users cannot self-register.

**Enterprise standard gap:** Users should receive a time-limited invitation token (24–72 h), follow a link to set their own password, and be automatically associated with the target tenant and organisation on acceptance. None of this infrastructure exists.

---

### Activate User

**Status: PARTIAL**

`users.is_active` (`Boolean`, default `True`, `server_default="1"`) is the sole activation-state column. There is no dedicated `activate_user()` service method distinct from `set_user_active(user_id, is_active=True)`.

**Service/method:** `user_admin_service.set_user_active()` (exposed as `AuthService.set_user_active()`). It requires `auth.manage` permission, flips `users.is_active`, commits, records an audit entry (`operation="update"`, `field="is_active"`, `severity="medium"`), emits `auth_changed`, and calls `refresh_current_session_if_user()` which will clear the in-memory session if `is_active` is now False.

**What is missing:**
- Single boolean `is_active` cannot distinguish between `invited`, `active`, `suspended`, `deactivated`, and `deleted` states. Transitioning from `invited` to `active` (email confirmation) is indistinguishable from an admin toggling the account on.
- No `activation_status` enum column.
- No `activated_at` timestamp.

---

### Deactivate User

**Status: PARTIAL**

Handled by `AuthService.set_user_active(user_id, is_active=False)` in `user_admin_service.set_user_active()`.

**What it does correctly:** Flips `is_active` to False, commits, audits the change, and calls `refresh_current_session_if_user()`. Inside that function, if the user is found to be inactive the in-memory `UserSessionContext` is cleared (`.clear()`). Persisted `auth_sessions` rows are NOT automatically revoked at deactivation time — `revoke_all_persisted_sessions()` is only called from password-change and force-reset paths, not from `set_user_active()`.

**Critical gap:** Deactivating a user does not revoke existing `auth_sessions` rows. A session token held by another process (API call, background job) that resolves via `validate_session_principal()` will detect `is_active=False` and refuse — this is correct. But session rows remain in the database with `revoked_at=NULL`, creating audit noise and a potential attack surface if `is_active` is restored without explicit session cleanup.

**What is missing:**
- `revoke_all_persisted_sessions()` should be called inside `set_user_active(is_active=False)`.
- No separate `deactivate_user()` method with an explicit audit action distinct from a generic toggle.
- Audit entry uses `action="user.set_active"` and `metadata={"is_active": "False"}` — not semantically labelled as a deactivation event.

---

### Suspend User

**Status: NO**

There is no suspension concept in the codebase. The only temporary lockout mechanism is the brute-force lockout: `users.locked_until` is set by `register_failed_login()` when `failed_login_attempts >= login_lockout_threshold()` and is automatically cleared on next successful authentication attempt if `locked_until <= now`.

`unlock_user_account()` in `user_admin_service.py` exists to manually zero `failed_login_attempts` and clear `locked_until` — this is an admin unlock, not a suspension restore path.

**Enterprise standard gap:** Suspension is a deliberate administrator action (e.g., HR hold, security investigation) that differs from deactivation in intent and expected duration. It requires a distinct `activation_status` value, a `suspended_until` or `suspended_at` column, a different audit compliance tag, and a separate `unsuspend_user()` service method.

---

### Delete User

**Status: NO (hard-delete pattern only implied)**

No `delete_user()` service method exists. The `UserRoleORM` and `AuthSessionORM` tables both declare `ForeignKey("users.id", ondelete="CASCADE")`, meaning a hard DELETE of a `users` row would cascade-delete all role bindings and session records. There is no soft-delete, anonymisation, or GDPR pseudonymisation path.

**What is missing:**
- `deleted_at` column with soft-delete semantics.
- `is_deleted` flag or `activation_status="deleted"` state.
- PII anonymisation (username → `deleted_<hash>`, email → NULL, display_name → "Deleted User") after a retention period.
- Audit trail preservation after deletion — currently a hard-delete would remove the user row while audit entries referencing `actor_id` would retain a stale FK.
- Record-transfer logic: tasks, projects, cost items, etc. owned by the user have no `deleted_by` or transfer mechanism.

---

### Restore User

**Status: NO**

No `restore_user()` service method exists. The only path to re-enable a user is `set_user_active(user_id, is_active=True)`, which is a generic toggle with no restore-specific audit event, no re-invitation flow, and no role-restoration logic if roles were stripped at deactivation time.

---

### Password Reset

**Status: PARTIAL — admin-only reset, no token-based self-service**

Three methods exist in `password_service.py`, all exposed via `AuthService`:

1. `change_password(user_id, current_password, new_password)` — self-service change. Verifies the current password, validates the new one, rotates `session_revision`, sets `password_changed_at`, sets `must_change_password=False`, calls `revoke_all_persisted_sessions()`, and commits. Audit: `severity="high"`, `action="password.change"`.

2. `force_user_password_reset(user_id)` — requires `auth.manage`. Sets `must_change_password=True`, rotates `session_revision`, calls `revoke_all_persisted_sessions()`, commits. Does NOT set a new password. Audit: `severity="high"`, `action="password.force_reset"`.

3. `reset_user_password(user_id, new_password)` — requires `auth.manage`. Admin directly sets a new password hash, forces `must_change_password=True`, rotates session, revokes persisted sessions. Audit: `severity="high"`, `action="password.reset"`.

**What is present and correct:** `must_change_password` column on `users` table is populated and respected. Session revocation on password change is implemented. Password hashing uses Argon2id with the explicit OWASP baseline profile; PBKDF2 hashes are rejected.

**What is missing:**
- No token-based self-service reset flow. There is no `password_reset_tokens` table, no token generation, no email delivery, and no token-acceptance endpoint. The only way a user can reset a forgotten password is for an admin to call `reset_user_password()` directly.
- `must_change_password` is stored on `users` but the authentication path (`authenticate()`) does not block login when it is True — it returns the `UserAccount` with the flag set and expects the UI layer to redirect to a change-password screen. There is no enforcement at the service layer.

---

### MFA Enrollment

**Status: PARTIAL — backend functional, UI collection absent**

Three methods exist in `mfa_service.py`:

1. `provision_mfa_secret(user_id)` — requires `auth.manage` or `security.manage`. Generates a random 20-byte base32 secret via `generate_mfa_secret()` (custom implementation using `os.urandom` + `base64.b32encode`), stores it in `users.mfa_secret`, sets `users.mfa_enabled=False`. Returns the raw secret string for QR code generation. Audit: `severity="high"`, `action="mfa.provision"`.

2. `enable_user_mfa(user_id, verification_code)` — requires `auth.manage` or `security.manage`. Calls `verify_totp_code()` with the stored secret; if valid, sets `users.mfa_enabled=True`. Audit: `severity="medium"`, `action="mfa.enable"`.

3. `disable_user_mfa(user_id)` — requires `auth.manage` or `security.manage`. Sets `users.mfa_enabled=False`. Audit: `severity="high"`, `action="mfa.disable"`.

**TOTP implementation:** Custom — `mfa.py` implements TOTP per RFC 6238 using Python's `hmac` + `hashlib.sha1`, with a 30-second window and ±1 step drift allowance. This is functionally correct but is a hand-rolled implementation rather than the `pyotp` library. The secret is stored as raw base32 in `users.mfa_secret` (`String(128), nullable=True`).

**Authentication integration:** `authenticate()` correctly checks `mfa_enabled` and calls `verify_totp_code()` when True. If the MFA code is absent or invalid, `AUTH_MFA_REQUIRED` / `AUTH_MFA_FAILED` errors are raised.

**What is missing:**
- The UI layer (QML) never presents a TOTP code input field at login. The `mfa_code` parameter reaches the backend as `None` on every login attempt, making MFA non-functional end-to-end despite the backend logic being correct.
- No `mfa_backup_codes` table and no backup code generation or consumption path.
- No `mfa_enrolled_at` timestamp column.
- No per-tenant MFA enforcement policy — MFA is always optional and must be provisioned per-user individually.
- `provision_mfa_secret()` requires `auth.manage` or `security.manage` — users cannot self-enroll; enrollment must be initiated by an admin.

---

### Role Assignment

**Status: YES — functional but with structural bugs**

**Service/method:** `role_assignment_service.assign_role(user_id, role_name)` and `revoke_role(user_id, role_name)`, both exposed via `AuthService`.

`assign_role()` requires `auth.manage`, loads the user, loads the existing role set, runs `enforce_separation_of_duties()` against the combined set, looks up the role by name, checks `user_role_repo.exists(user_id, role_id)` to avoid duplicate insertion, adds a `UserRoleBinding`, commits, audits (`operation="permission_change"`, `severity="medium"`), emits `auth_changed`, and calls `refresh_current_session_if_user()` to rebuild the in-memory principal.

`revoke_role()` follows the symmetric path with `operation="delete"`.

**Structural bug:** `user_roles` has `UniqueConstraint("user_id", "role_id")` only — there is no `organization_id` in the unique key. `UserRoleBinding` carries an `organization_id` field (nullable) and the ORM column exists with an FK to `organizations`, but the unique constraint means a user can only hold each role once globally, not once per org. Org-scoped role assignment is silently impossible.

**What is missing:**
- Bulk role assignment across multiple users.
- Role assignment via invitation acceptance (new-user onboarding).
- Role expiry (`expires_at` column on `user_roles`).
- Organisation-scoped uniqueness constraint — the current schema prevents org-level role isolation.

---

### Tenant Assignment

**Status: NO**

There is no `user_tenants` table. No method exists to explicitly associate a user with a tenant. The `users` table has no `tenant_id` column — users are platform-global identities.

Tenant context is established entirely at runtime via `TenantContextService`, which resolves from `UserSessionContext._active_tenant_id` → `principal.active_tenant_id` → `get_default()`. There is no persistence record asserting that a given user is a member of a given tenant. The bug noted in the tenant architecture review applies here: `set_active_tenant()` has no membership check, so any user can set their session context to any tenant ID.

**What is missing:**
- `user_tenants(id, user_id FK users, tenant_id FK tenants, tenant_role, invited_by, invited_at, accepted_at, is_active)` table.
- `TenantMembershipService` with `invite_to_tenant()`, `accept_tenant_invitation()`, `remove_from_tenant()` methods.
- Membership check in `set_active_tenant()`.
- `tenant_admin` role scoped to a specific tenant.

---

### Organisation Assignment

**Status: PARTIAL — scoped grants exist, no explicit membership service**

Organisation-level access is modelled via two overlapping mechanisms:

1. `user_roles` rows where `organization_id IS NOT NULL` — these are intended to represent org-scoped role bindings. Due to the unique constraint bug (`user_id, role_id` only), adding the same role for two different `organization_id` values would violate uniqueness.

2. `scoped_access_grants(tenant_id, scope_type, scope_id, user_id, scope_role, permission_codes_json)` — when `scope_type="organization"`, this represents an organisation-level grant. `AccessControlService.assign_scope_grant(scope_type="organization", ...)` is the path to set this up, but it requires a registered `ScopedRolePolicy` for the `"organization"` scope type.

No dedicated `assign_user_to_organization()` method exists. There is no `organization_memberships` table. The `ScopedAccessGrant` path works but is a generic mechanism rather than a first-class organisation membership concept.

**What is missing:**
- First-class `organization_memberships` table analogous to `project_memberships`.
- `assign_user_to_organization()` / `remove_user_from_organization()` service methods.
- Organisation assignment as part of invitation acceptance flow.
- `org_admin` role scoped to a single organisation.

---

## User State Machine

The current system implements only a binary `is_active` boolean with a transient lockout overlay. The enterprise target state machine is:

```
[Not Registered]
     |
     | register_user() [admin direct] — EXISTS
     | invite_user() + accept_invitation() — MISSING
     v
[Active]  <----------------------------------------------+
     |                                                    |
     | set_user_active(False) — EXISTS (partial)          | set_user_active(True)
     | deactivate_user() — MISSING (named method)         | restore_user() — MISSING
     v                                                    |
[Deactivated] ------------------------------------------>+
     |
     | (no path defined — hard delete only implied)
     v
[Deleted / Anonymised]  — MISSING

[Active]
     |
     | suspend_user() — MISSING
     v
[Suspended] (temporary, expected reversal)
     |
     | unsuspend_user() — MISSING
     v
[Active]

[Active or Deactivated]
     |
     | Brute-force threshold reached — EXISTS (auto)
     v
[Locked] (transient, auto-expiring, not a true state)
     |
     | Auto-expire at locked_until — EXISTS
     | unlock_user_account() — EXISTS
     v
[Active]
```

Columns currently tracking state on `users` table:

| Column | Type | Purpose |
|---|---|---|
| `is_active` | `Boolean` | Main activation gate; False blocks login |
| `locked_until` | `DateTime, nullable` | Temporary lockout after brute-force |
| `failed_login_attempts` | `Integer` | Counter for lockout calculation |
| `must_change_password` | `Boolean` | Force password change on next login (not enforced at service layer) |
| `mfa_enabled` | `Boolean` | MFA gate in `authenticate()` |
| `session_expires_at` | `DateTime, nullable` | Token expiry |
| `session_revision` | `Integer` | Rotated on password change to invalidate stale tokens |

---

## User Data Model — Full Column Inventory

**Columns that exist on `UserORM` (`users` table):**

| Column | ORM Type | Nullable | Notes |
|---|---|---|---|
| `id` | `String` PK | No | Platform-generated UUID-style |
| `username` | `String(128)` UNIQUE | No | Normalised to lowercase |
| `password_hash` | `String` | No | Argon2id PHC-encoded string |
| `display_name` | `String(256)` | Yes | |
| `email` | `String(256)` | Yes | Not unique; not verified |
| `identity_provider` | `String(128)` | Yes | Federated SSO provider key |
| `federated_subject` | `String(256)` | Yes | Federated SSO subject; UNIQUE with identity_provider |
| `mfa_secret` | `String(128)` | Yes | Base32-encoded TOTP secret |
| `mfa_enabled` | `Boolean` | No | Default False |
| `session_timeout_minutes_override` | `Integer` | Yes | Per-user session TTL override |
| `session_revision` | `Integer` | No | Rotated on password change |
| `last_login_auth_method` | `String(64)` | Yes | e.g. `"password"`, `"federated:google"` |
| `last_login_device_label` | `String(256)` | Yes | User-agent label |
| `is_active` | `Boolean` | No | Default True |
| `failed_login_attempts` | `Integer` | No | Default 0 |
| `locked_until` | `DateTime` | Yes | Auto-lockout expiry |
| `last_login_at` | `DateTime` | Yes | Set on successful auth |
| `session_expires_at` | `DateTime` | Yes | Rolling session expiry |
| `password_changed_at` | `DateTime` | Yes | Set on create and every password change |
| `must_change_password` | `Boolean` | No | Default False |
| `created_at` | `DateTime` | No | |
| `updated_at` | `DateTime` | No | |
| `version` | `Integer` | No | Default 1 |

Note: `active_session_id` exists on the `UserAccount` domain dataclass (`src/core/platform/auth/domain/user.py`) but is NOT a column on `UserORM`. It is populated in memory from `AuthSession` queries and is not persisted on the users row.

**Columns missing relative to enterprise standard:**

| Missing Column | Purpose | Priority |
|---|---|---|
| `activation_status` | Enum (`invited`/`active`/`suspended`/`deactivated`/`deleted`) replacing boolean `is_active` | High |
| `email_verified` | `Boolean` — email ownership confirmed | High |
| `invited_by_user_id` | FK `users.id` — audit trail for who created the account | High |
| `invited_at` | `DateTime` — when the invitation was issued | High |
| `deleted_at` | `DateTime` — soft-delete timestamp | High |
| `timezone` | `String(64)` — user preference for display | Medium |
| `locale` | `String(16)` — language/region preference | Low |
| `mfa_enrolled_at` | `DateTime` — when MFA was first enabled | Medium |
| `last_failed_login_at` | `DateTime` — timestamp of most recent failed attempt | Medium |

---

## Enterprise Best Practices Assessment

### 1. Identity vs Access Separation
The codebase correctly separates the `users` table (identity) from `user_roles`, `scoped_access_grants`, and `project_memberships` (access grants). The `UserAccount` domain object is loaded independently of role resolution; `build_principal()` in `principal_builder.py` assembles the full permission set at session-build time. **This pattern is sound.**

### 2. Soft Deletes
Not implemented. The cascade-delete FK on `user_roles` and `auth_sessions` means a hypothetical hard DELETE of a user row would physically remove all role bindings and session history. Audit entries in `audit_entries` reference `actor_id` as a raw string with no FK — these would be orphaned but would survive deletion. This must be corrected before any GDPR-regulated deployment.

### 3. Invitation-First Onboarding
Not implemented. All user creation today requires an administrator with `auth.manage` to call `register_user()` and supply a password directly. This is not acceptable for multi-tenant SaaS where tenant administrators must be able to self-provision team members without platform operator involvement.

### 4. Session Invalidation on State Change
**Partial.** Password changes and force-resets correctly call `revoke_all_persisted_sessions()`. Deactivation via `set_user_active(False)` clears the in-memory session via `refresh_current_session_if_user()` if the deactivated user is currently logged in on the same process, but does NOT call `revoke_all_persisted_sessions()`. Persisted `auth_sessions` rows remain with `revoked_at=NULL` until they naturally expire. In a multi-process or API-driven deployment, another process holding a valid session token for a deactivated user will correctly be rejected by `validate_session_principal()` (which checks `user.is_active`), but the session rows are not cleaned up.

### 5. Audit Coverage
Every lifecycle operation that exists produces an `audit_entries` row. The audit schema supports `severity`, `compliance_tag`, `actor_id`, `actor_username`, `actor_ip`, `actor_user_agent`, and field-level `old_value`/`new_value`. However, `set_user_active()` does not record `old_value` (previous `is_active` state), only the new value in `metadata`. Field-level diff capture is not used for user lifecycle events.

### 6. MFA Grace Period and Enforcement Policy
MFA has no enforcement policy. It is optional per user with no per-tenant or per-role mandate. A tenant administrator cannot require MFA for their members. There is no grace period concept because MFA cannot be mandated. The planned fix (per the context note) would require a `tenant_mfa_policy` or `organization_mfa_policy` table and enforcement at the `authenticate()` path.

### 7. Password Hashing
Argon2id via `argon2-cffi`, using 19 MiB memory, 2 iterations, parallelism 1, a 16-byte random salt, and a 32-byte hash. Only Argon2id PHC strings authenticate. Valid hashes with obsolete Argon2id costs are rehashed after complete credential verification; PBKDF2 migration code is intentionally absent because the product is pre-release.

---

## Gap Summary Table

| # | Lifecycle Event | Status | Service / Method | Table / Column | Missing |
|---|---|---|---|---|---|
| 1 | **Create User** | PARTIAL | `AuthService.register_user()` → `registration_service.register_user()` | `users.*` | No tenant association at creation; no email uniqueness; no invitation token path; no `activation_status` |
| 2 | **Invite User** | NO | — | — | `InvitationService`, `invitation_tokens` table, email delivery, token expiry, acceptance flow, tenant/org assignment on acceptance |
| 3 | **Activate User** | PARTIAL | `AuthService.set_user_active(True)` → `user_admin_service.set_user_active()` | `users.is_active` | No distinct activation event; no `activated_at`; no email-verification path; no `activation_status` enum |
| 4 | **Deactivate User** | PARTIAL | `AuthService.set_user_active(False)` → `user_admin_service.set_user_active()` | `users.is_active` | Does not call `revoke_all_persisted_sessions()`; no named deactivation audit action; no `activation_status` |
| 5 | **Suspend User** | NO | — | — | No suspend state; `users.locked_until` is brute-force-only; needs `suspend_user()` / `unsuspend_user()`, `suspended_at`, `activation_status="suspended"` |
| 6 | **Delete User** | NO | — | — | No `delete_user()` method; no soft-delete; no PII anonymisation; cascade-delete FKs imply destructive hard delete |
| 7 | **Restore User** | NO | — | — | Only path is `set_user_active(True)` toggle with no restore audit event and no role-restoration logic |
| 8 | **Password Reset (self-service token)** | NO | — | — | No `password_reset_tokens` table; no email delivery; no token-based flow |
| 8b | **Password Reset (admin-initiated)** | YES | `AuthService.reset_user_password()` / `force_user_password_reset()` → `password_service.py` | `users.password_hash`, `users.must_change_password`, `users.session_revision` | `must_change_password=True` not enforced at service layer during `authenticate()` |
| 9 | **MFA Enrollment** | PARTIAL | `AuthService.provision_mfa_secret()` + `enable_user_mfa()` → `mfa_service.py` | `users.mfa_secret`, `users.mfa_enabled` | UI never collects TOTP at login; no backup codes; no `mfa_enrolled_at`; no per-tenant enforcement policy; admin-only provisioning (users cannot self-enroll) |
| 10 | **Role Assignment** | YES (with bugs) | `AuthService.assign_role()` / `revoke_role()` → `role_assignment_service.py` | `user_roles(user_id, role_id, organization_id)` | Unique constraint `(user_id, role_id)` prevents org-scoped role isolation; no bulk assignment; no role expiry |
| 11 | **Tenant Assignment** | NO | — | — | No `user_tenants` table; no `TenantMembershipService`; `set_active_tenant()` has no membership check |
| 12 | **Organisation Assignment** | PARTIAL | `AccessControlService.assign_scope_grant(scope_type="organization", ...)` | `scoped_access_grants` | No first-class `organization_memberships` table; no named `assign_user_to_organization()` method; no join on invitation acceptance; org-scoped `user_roles` broken by unique constraint |

---

# 16. DELIVERABLE 11 — TENANT LIFECYCLE MANAGEMENT

---

## 16.1 Current Tenant Model — What Actually Exists

### Database Layer

The `tenants` table is defined in `src/core/platform/infrastructure/persistence/orm/tenant.py`:

```
TenantORM
  id            String  PK
  tenant_code   String(64)  NOT NULL  UNIQUE
  display_name  String(256) NOT NULL
  is_active     Boolean     NOT NULL  DEFAULT 1
  version       Integer     NOT NULL  DEFAULT 1

Indexes:
  idx_tenants_code  (tenant_code) UNIQUE
  idx_tenants_active (is_active)
```

The `is_active` boolean is the only lifecycle signal. There is no status enum, no suspension reason, no archived-at timestamp, no deleted-at timestamp, and no provisioning state. The `version` column exists solely to support optimistic locking via `update_with_version_check()`.

The tenants table was created in migration `y9z0a1b2c3d4_create_tenants_table.py`. Tenant_id was propagated as NOT NULL to 34 tables in migration `r3s4t5u6v7w8_phase_c_tenant_id_not_null.py`. All FK declarations currently use the default SQLAlchemy `ondelete=RESTRICT` strategy — no CASCADE is in place.

### Domain Layer

`src/core/platform/tenancy/domain/tenant.py` defines a plain dataclass:

```python
@dataclass
class Tenant:
    id: str
    tenant_code: str
    display_name: str
    is_active: bool = True
    version: int = 1

    @staticmethod
    def create(tenant_code, display_name, *, is_active=True) -> "Tenant":
        ...
```

`Tenant.create()` strips and uppercases `tenant_code`. No validation of code format beyond that exists in the domain object. No state transition methods exist on the domain object.

### Repository Layer

`src/core/platform/infrastructure/persistence/repositories/tenant.py` — `SqlAlchemyTenantRepository` implements:

- `add(tenant)` — INSERT
- `update(tenant)` — optimistic-lock UPDATE (writes `tenant_code`, `display_name`, `is_active`)
- `get(tenant_id)` — lookup by PK
- `get_by_code(tenant_code)` — lookup by unique code
- `get_default()` — returns first `is_active=True` row ordered by `tenant_code ASC`; this is the single-tenant desktop bootstrap fallback
- `list_all(*, active_only)` — filtered list ordered by `display_name ASC`

`TenantRepository` (ABC) in `src/core/platform/tenancy/contracts.py` exactly mirrors these six methods.

### Service Layer

`TenantContextService` in `src/core/platform/tenancy/tenant_context.py` is the only service that references `TenantRepository`. Its entire scope is context resolution — it does not create, suspend, archive, or delete tenants. Its six methods are:

- `get_active_tenant_id()` / `require_active_tenant_id()`
- `get_active_tenant()` — resolves from session → fallback to `get_default()`
- `set_active_tenant(tenant_id)` — switches context; checks `is_active` but does NOT check user membership in that tenant (confirmed bug)
- `get_active_organization_id()` / `require_active_organization_id()`
- `get_active_organization()` / `set_active_organization()`
- `require_context()` / `require_organization_context()`

**No `TenantAdminService` exists anywhere in the codebase.** There is no `create_tenant`, no `suspend_tenant`, no `archive_tenant`, no `delete_tenant`, and no `restore_tenant` method anywhere.

### Permission Layer

`src/core/platform/auth/policy.py` defines 56 permission codes in `DEFAULT_PERMISSIONS`. None of them are tenant-scoped administrative permissions. The codes most relevant to tenant management that do exist are:

- `settings.manage` — used by `OrganizationService` to gate org CRUD
- `auth.manage` — user/role management
- `security.manage` — session controls

The following codes are entirely absent:
- `tenant.create`
- `tenant.manage`
- `tenant.suspend`
- `tenant.delete`
- `tenant.read`

The `admin` role receives all 56 existing permissions via `set(DEFAULT_PERMISSIONS.keys())`. This is the only role that functions as a superuser, and it operates at the organization level through `user_roles`. There is no platform-admin role scoped above the tenant.

### Audit Layer

`src/core/platform/audit/domain/audit_entry.py` — `AuditEntry` carries a `tenant_id: str | None` field, so existing infrastructure can theoretically record tenant-level events. However, `organization_id` is also present and the current `OrganizationService` writes audit entries scoped to `module="platform"` with no `tenant_id` populated. There is no platform-level audit sink distinct from the org-scoped `audit_logs` table. The `audit_entries` table (from migration `t5u6v7w8x9y0_create_audit_entries.py`) is the current security-class audit store; it does carry `tenant_id` as a column (per the AuditEntry domain model), which means tenant lifecycle events CAN be written there without a schema change, but the writer must explicitly populate `tenant_id` and omit `organization_id`.

---

## 16.2 Tenant Lifecycle States

### Required State Machine

The current boolean `is_active` can only represent two states: Active (`True`) and Inactive (`False`). The required lifecycle has six distinguishable states:

```
  [Provisioning]
       |
       | create_tenant() completes all steps
       v
  [Active]  <--------------------------------------------+
       |                                                  |
       | suspend_tenant()          | archive_tenant()     | restore_tenant()
       v                           v                      |
  [Suspended]               [Archived] -------------------+
       |                           |
       | restore_tenant()          | restore_tenant()
       +---------------------------+
                   |
                   v
              [Active]
                   |
                   | delete_tenant()  (soft delete only)
                   v
            [Soft Deleted]
                   |
                   | after legal retention period (scheduled purge job)
                   v
              [Purged]
```

Transitions not shown are illegal and must raise `BusinessRuleError`:
- Active → Purged (must pass through Soft Deleted)
- Suspended → Purged (must pass through Soft Deleted)
- Purged → any state (terminal)
- Provisioning → Suspended / Archived / Deleted (must complete provisioning first)

### State Definitions

**Provisioning** — Tenant row has been inserted but the auto-provisioning sequence (default org, admin user, module entitlements) has not yet committed. This state must be durable so a partial failure does not leave a half-configured tenant that appears Active. Currently the code has no concept of this state; `Tenant.create()` defaults `is_active=True` immediately.

**Active** — Normal operating state. Users with membership in this tenant can authenticate and access data. `is_active=True` in the current schema maps to this state.

**Suspended** — Operational hold. Triggered by billing delinquency, security incident, or administrative action. New logins must be blocked. Existing sessions must be invalidated. Data is preserved and read-write at the DB level but all application-layer access is gated. `is_active=False` partially represents this but carries no reason, no timestamp, and does not distinguish Suspended from Archived.

**Archived** — Intentional long-term deactivation. The customer relationship has ended but data must be retained for regulatory or contractual reasons. Unlike Suspended, Archive is not expected to be reversed in normal operations — `restore_tenant()` is available but exceptional. Users cannot log in. No application access.

**Soft Deleted** — Marks the tenant for eventual purge. Data is preserved. No access of any kind. A scheduled purge job inspects `deleted_at` and purges when the retention window has elapsed (typically 7 years for business records under most jurisdictions).

**Purged** — All tenant-owned data has been hard-deleted. The `tenants` row itself may be retained as a tombstone with the purge timestamp for audit trail continuity.

---

## 16.3 Required Schema Changes

### 16.3.1 tenants Table — Add Status Column

The `is_active` boolean must be replaced by a `status` enum. A migration must:

1. Add `status VARCHAR(32) NOT NULL DEFAULT 'active'`
2. Backfill: `UPDATE tenants SET status = 'active' WHERE is_active = 1; UPDATE tenants SET status = 'archived' WHERE is_active = 0`
3. Add `suspended_at DATETIME NULL`, `suspended_reason TEXT NULL`
4. Add `archived_at DATETIME NULL`
5. Add `deleted_at DATETIME NULL`
6. Add `provisioning_completed_at DATETIME NULL`
7. Retain `is_active` as a generated/computed column or remove it — if retained for backward compatibility it must be kept in sync by the service layer, not independently set

Valid status values: `provisioning`, `active`, `suspended`, `archived`, `deleted`

The `get_default()` fallback in `SqlAlchemyTenantRepository` filters on `is_active=True`. After this migration it must filter on `status = 'active'`.

### 16.3.2 No CASCADE Changes Required for Soft Delete

The current `ondelete=RESTRICT` strategy on all `tenant_id` FK columns is correct for the soft-delete pattern. A hard purge must be performed only by a platform-level purge job that explicitly deletes child data in dependency order before deleting the tenant row. Changing FK to CASCADE would make accidental hard-deletes destructive with no recovery path.

### 16.3.3 auth_sessions — Tenant Suspension Cascade

`auth_sessions` carries `last_active_tenant_id`. On `suspend_tenant()`, the service must:

```sql
UPDATE auth_sessions
SET revoked_at = NOW()
WHERE last_active_tenant_id = :tenant_id
  AND revoked_at IS NULL
```

This requires the `AuthSessionRepository` (or a dedicated `SessionRevocationService`) to expose a `revoke_all_for_tenant(tenant_id)` method. No such method exists today.

---

## 16.4 Required Services

### 16.4.1 TenantAdminService (to be built)

Location: `src/core/platform/tenancy/application/tenant_admin_service.py`

This service is the only entry point for tenant lifecycle operations. All methods require the `tenant.manage` permission (except `create_tenant`, which requires `tenant.create`, and `delete_tenant`, which requires `tenant.delete`). All methods emit a platform-level audit entry.

```
TenantAdminService
  __init__(
      session: Session,
      tenant_repo: TenantRepository,
      org_repo: OrganizationRepository,
      user_repo: UserRepository,
      session_repo: AuthSessionRepository,
      audit_service: EnterpriseAuditService,
      user_session: UserSessionContext | None,
  )

  create_tenant(
      code: str,
      display_name: str,
      *,
      admin_username: str,
      admin_password: str,
      auto_provision: bool = True,
  ) -> Tenant
      Permission: tenant.create
      Steps:
        1. Validate code format (uppercase alphanumeric, 2–32 chars)
        2. Validate display_name non-empty
        3. Check uniqueness via tenant_repo.exists_by_code()
        4. Create Tenant with status=provisioning
        5. tenant_repo.add(tenant); session.flush()
        6. If auto_provision:
             a. Create default Organization (org_code=code, same display_name)
             b. Create admin User (username=admin_username, role=admin, org=default org)
             c. Seed organization_module_entitlements for all modules, licensed=True
        7. Set status=active, provisioning_completed_at=now()
        8. session.commit()
        9. Audit: operation=tenant_created, severity=high, compliance_tag=tenant_lifecycle
      Rollback: full transaction — if step 6 fails, tenant row is not committed

  activate_tenant(tenant_id: str) -> Tenant
      Permission: tenant.manage
      Guard: status must be suspended (not archived or deleted)
      Steps: set status=active; audit tenant_activated

  suspend_tenant(tenant_id: str, *, reason: str) -> Tenant
      Permission: tenant.suspend
      Guard: status must be active
      Steps:
        1. Set status=suspended, suspended_at=now(), suspended_reason=reason
        2. Revoke all active auth_sessions for this tenant
        3. Audit: operation=tenant_suspended, severity=high, metadata={reason}

  archive_tenant(tenant_id: str, *, reason: str) -> Tenant
      Permission: tenant.manage
      Guard: status must be active or suspended
      Steps:
        1. Set status=archived, archived_at=now()
        2. Revoke all active auth_sessions for this tenant (if not already revoked)
        3. Audit: operation=tenant_archived, severity=high, compliance_tag=tenant_lifecycle

  delete_tenant(tenant_id: str, *, reason: str) -> Tenant
      Permission: tenant.delete
      Guard: status must be archived (cannot soft-delete an active tenant)
      Steps:
        1. Set status=deleted, deleted_at=now()
        2. Audit: operation=tenant_soft_deleted, severity=critical, compliance_tag=data_retention
      Note: This does NOT delete data. A separate scheduled purge job handles hard deletion
            after the retention period has elapsed.

  restore_tenant(tenant_id: str) -> Tenant
      Permission: tenant.manage
      Guard: status must be suspended or archived (not deleted or purged)
      Steps:
        1. Set status=active, clear suspended_at/suspended_reason/archived_at
        2. Audit: operation=tenant_restored, severity=high

  list_tenants(*, include_inactive: bool = False) -> list[Tenant]
      Permission: tenant.read
      Delegates to tenant_repo.list_all()

  get_tenant_stats(tenant_id: str) -> TenantStats
      Permission: tenant.read
      Returns: user count (via user_tenants once that table exists),
               org count, project count, data summary
```

### 16.4.2 TenantPurgeJob (scheduled, to be built)

A background job (separate from the web/desktop process) that runs on a configurable schedule:

```
TenantPurgeJob.run()
  1. Query tenants WHERE status='deleted' AND deleted_at < NOW() - retention_days
  2. For each such tenant, in FK dependency order:
       DELETE FROM maintenance_work_order_tasks WHERE ... (cascade down)
       ...
       DELETE FROM organizations WHERE tenant_id = :tenant_id
  3. Mark tenants row as status='purged', purged_at=now() (or DELETE the row)
  4. Emit platform audit entry: operation=tenant_purged, severity=critical
```

The retention period defaults to 2555 days (7 years) and must be configurable via environment variable `PM_TENANT_RETENTION_DAYS`.

---

## 16.5 Required Permissions

The following permission codes must be added to `DEFAULT_PERMISSIONS` in `src/core/platform/auth/policy.py`:

| Permission Code   | Description                                                    |
|-------------------|----------------------------------------------------------------|
| `tenant.read`     | View tenant list and tenant statistics                         |
| `tenant.create`   | Create new tenants and trigger auto-provisioning               |
| `tenant.manage`   | Activate, suspend, archive, and restore tenants                |
| `tenant.suspend`  | Suspend an active tenant (separated for SOD — narrower grant)  |
| `tenant.delete`   | Soft-delete an archived tenant (restricted, requires approval) |

These must be added to `DEFAULT_PERMISSIONS` and also to the `admin` role's permission set (which is already `set(DEFAULT_PERMISSIONS.keys())`, so the admin role picks them up automatically).

No existing role other than `admin` should receive any `tenant.*` permission by default. A new `platform_admin` role (not yet defined) is the intended future bearer.

`tenant.delete` must additionally be gated behind an approval workflow (`ApprovalRequest` with a dedicated approval type) before the service method executes — the permission alone is not sufficient. This approval integration is out of scope for the initial TenantAdminService build but must be noted in the API contract.

---

## 16.6 Required Auditing

### Current State

`AuditEntry` (in `src/core/platform/audit/domain/audit_entry.py`) already supports `tenant_id: str | None` and `organization_id: str | None` fields. The `audit_entries` table (migration `t5u6v7w8x9y0_create_audit_entries.py`) is the current security-grade audit store.

### Tenant Lifecycle Audit Requirements

All tenant lifecycle events must be written to `audit_entries` (not `audit_logs` — that is the business activity log). Each entry must populate:

| Field            | Value                                              |
|------------------|----------------------------------------------------|
| `module`         | `"platform"`                                       |
| `entity_type`    | `"tenant"`                                         |
| `entity_id`      | the tenant's id                                    |
| `tenant_id`      | the tenant's id                                    |
| `organization_id`| `None` — this is a platform-level event            |
| `actor_id`       | the platform admin's user_id                       |
| `severity`       | `"high"` for create/activate/restore/archive; `"critical"` for suspend/delete/purge |
| `compliance_tag` | `"tenant_lifecycle"`                               |

The required `metadata` dict per operation:

| Operation           | Required metadata keys                                    |
|---------------------|-----------------------------------------------------------|
| `tenant_created`    | `tenant_code`, `display_name`, `auto_provision`           |
| `tenant_activated`  | `tenant_code`, `previous_status`                          |
| `tenant_suspended`  | `tenant_code`, `reason`, `sessions_revoked_count`         |
| `tenant_archived`   | `tenant_code`, `reason`                                   |
| `tenant_restored`   | `tenant_code`, `previous_status`                          |
| `tenant_soft_deleted` | `tenant_code`, `reason`, `deleted_at`                  |
| `tenant_purged`     | `tenant_code`, `purged_at`, `rows_deleted_count`          |

### Gap: No Platform-Level Audit Query API

The existing `EnterpriseAuditService` and audit query endpoints filter by `organization_id`. A platform admin viewing tenant lifecycle events must be able to query `audit_entries WHERE entity_type = 'tenant' AND tenant_id = :id AND organization_id IS NULL`. This requires either a new query method in `EnterpriseAuditService` or a dedicated `PlatformAuditService`. This is a build item.

---

## 16.7 Tenant Creation Auto-Provisioning

When `TenantAdminService.create_tenant()` runs with `auto_provision=True`, the following must be created within the same database transaction before status is set to `active`:

1. **Default Organization**
   - `organization_code` = `tenant_code` (same string)
   - `display_name` = `tenant display_name + " (Default)"`
   - `tenant_id` = new tenant id
   - `is_active` = True
   - Delegated to `OrganizationService.create_organization()` — but that method currently calls `_deactivate_other_organizations()` with no tenant scope (confirmed bug D10). The provisioning path must call the repository directly or pass tenant context explicitly to avoid cross-tenant deactivation.

2. **Admin User**
   - `username` = caller-supplied `admin_username`
   - `password_hash` = Argon2id-hashed `admin_password`
   - `is_active` = True
   - `must_change_password` = True (force password change on first login)
   - A `user_roles` row: `role_id = admin role id`, `organization_id = default org id`
   - When `user_tenants` table is built (D10 prerequisite), also insert `user_tenants(user_id, tenant_id)`

3. **Module Entitlements**
   - Insert `organization_module_entitlements` rows for all known module codes with `licensed=True`, `enabled=True`, `tenant_id = new tenant id`, `organization_id = default org id`
   - The module code list must be sourced from a constant registry, not hardcoded inline

If any of these steps fails, the entire transaction must roll back. The tenant must not appear in `get_default()` or any query until provisioning is complete (enforced by keeping `status=provisioning` until the final commit).

---

## 16.8 Impact on Existing Code

### TenantContextService.get_active_tenant()

Currently returns any tenant where `is_active=True`. After the status migration this must be updated to:

```python
def get_active_tenant(self) -> Tenant | None:
    tenant_id = self._session_tenant_id()
    if tenant_id:
        tenant = self._tenant_repo.get(tenant_id)
        if tenant is not None and tenant.status == "active":
            return tenant
    return self._tenant_repo.get_default()
```

`get_default()` must likewise filter `status = 'active'` rather than `is_active = True`.

### TenantContextService.set_active_tenant()

Currently checks `tenant.is_active`. Must check `tenant.status == "active"`. The existing `TENANT_INACTIVE` error code is adequate but the error message should distinguish suspended from archived.

### SqlAlchemyTenantRepository.update()

The `update()` method currently writes `is_active` to the DB. After the schema migration it must write `status` (and the new timestamp columns) instead. The `list_all(active_only=True)` filter must be updated to `WHERE status = 'active'`.

### OrganizationService._deactivate_other_organizations()

This method iterates all active orgs with no tenant filter — a confirmed cross-tenant bug. It is called from `create_organization()` and `set_active_organization()`. The provisioning path in `TenantAdminService` must not use this method until the bug is fixed. Fix is: add `tenant_id` filter to the repository query inside `_deactivate_other_organizations()`.

---

## 16.9 Architecture Readiness Summary

| Component                        | Status    | Gap Description                                                             |
|----------------------------------|-----------|-----------------------------------------------------------------------------|
| `tenants` table                  | Partial   | `is_active` boolean only; needs status enum + timestamp columns              |
| `Tenant` domain object           | Partial   | No state transition methods; `is_active` field only                          |
| `TenantRepository` (ABC)         | Partial   | `update()` supports only `is_active`; needs status-aware update              |
| `SqlAlchemyTenantRepository`     | Partial   | `get_default()` / `list_all()` filter on `is_active`; needs status filter    |
| `TenantContextService`           | Partial   | Context resolution only; no lifecycle operations                             |
| `TenantAdminService`             | Missing   | Does not exist                                                               |
| `TenantPurgeJob`                 | Missing   | Does not exist                                                               |
| `tenant.*` permissions           | Missing   | None of the 5 required codes exist in `DEFAULT_PERMISSIONS`                  |
| `platform_admin` role            | Missing   | No role defined above org-level `admin`                                      |
| Session revocation on suspend    | Missing   | No `revoke_all_for_tenant()` method on session repository                    |
| Platform-level audit query       | Missing   | `EnterpriseAuditService` filters by `organization_id`; no platform query path|
| Auto-provisioning sequence       | Missing   | No transaction-safe create_tenant → org → user → entitlements flow           |
| `user_tenants` table             | Missing   | Required for user-to-tenant membership and suspend cascade                   |
| `create_tenant` API endpoint     | Missing   | No HTTP or desktop API surface for tenant creation                           |

---

## 16.10 Build Sequence

The following order is required due to dependencies:

1. **Schema migration** — Add `status`, `suspended_at`, `suspended_reason`, `archived_at`, `deleted_at`, `provisioning_completed_at` to `tenants` table. Backfill `status` from `is_active`.
2. **Update `Tenant` domain object** — Add `status: str` field; deprecate `is_active` (keep as property: `return self.status == "active"`).
3. **Update `SqlAlchemyTenantRepository`** — Filter by `status`; write `status` in `update()`.
4. **Add `tenant.*` permissions to `policy.py`** — Five new codes; `admin` role picks them up automatically.
5. **Add `revoke_all_for_tenant(tenant_id)` to `AuthSessionRepository`** — Required before `suspend_tenant` can cascade.
6. **Build `TenantAdminService`** — Depends on steps 1–5.
7. **Fix `_deactivate_other_organizations()` cross-tenant bug** — Required before provisioning path is safe.
8. **Build `user_tenants` table and repository** — Required for membership-aware context switching and suspend cascade.
9. **Wire `TenantAdminService` into desktop and HTTP API layers** — Gated by platform_admin role.
10. **Build `TenantPurgeJob`** — Can be deferred until after core lifecycle is operational.
11. **Build platform audit query API** — Can be deferred; the data is already being written to `audit_entries`.

---

# 17. DELIVERABLE 12 — ORGANIZATION LIFECYCLE MANAGEMENT

## Current Organization Model

**Table:** `organizations(id, tenant_id FK NOT NULL, organization_code UNIQUE, display_name, timezone_name, base_currency, is_active, version)`

**Service:** `OrganizationService` in `org/application/organization_service.py`
- `create_organization(code, name, timezone, currency, *, is_active, tenant_id)`
- `_deactivate_other_organizations()` — CRITICAL BUG: not tenant-scoped
- `set_active_organization(organization_id)`

**Repository:** `SqlAlchemyOrganizationRepository`
- `get(id)`, `get_by_code(code)`, `get_active()`, `list_all()`
- `get_active()` BUG: no `tenant_id` filter

---

## Organization Lifecycle States

### Create Organization

| Attribute | Value |
|-----------|-------|
| **Exists** | YES — `OrganizationService.create_organization()` |
| **Current behavior** | Creates org record; calls `_deactivate_other_organizations()` — BUG |
| **Also** | `PlatformRuntimeApplicationService.provision_organization()` creates org and seeds module entitlements |
| **Missing** | `tenant_id` parameter on `provision_organization()`; tenant-scoped uniqueness for `organization_code` |

The `organization_code UNIQUE` constraint is currently database-global. In a multi-tenant deployment, uniqueness must be enforced within a tenant, not across all tenants. Two separate tenant organizations should be permitted to share the same `organization_code` (e.g., both using `"HQ"`). The constraint must be changed to `UNIQUE(tenant_id, organization_code)`.

---

### Activate Organization

| Attribute | Value |
|-----------|-------|
| **Exists** | PARTIAL — `organizations.is_active = True` is set on create |
| **Gap** | No dedicated `activate_organization()` service method |
| **Invariant enforcer** | `_deactivate_other_organizations()` — problematic for multi-org |

The single-active invariant was a desktop-era simplification. In multi-organization SaaS, multiple organizations within the same tenant must be simultaneously active. The concept of "currently selected organization" is a session-level concern, already handled by `active_organization_id` in `UserSessionContext`, and must not be conflated with the operational status of an organization record.

---

### Deactivate Organization

| Attribute | Value |
|-----------|-------|
| **Exists** | PARTIAL — `_deactivate_other_organizations()` deactivates all other orgs |
| **Bug** | Cross-tenant blast: deactivates orgs in ALL tenants, not just the current one |
| **Missing** | Proper `deactivate_organization(org_id, *, tenant_id)` method with tenant scope |

Deactivation is intended to be a reversible operational state, meaning the organization's data remains intact and the org can be reactivated. It must not cascade destructive effects to child records.

---

### Archive Organization

| Attribute | Value |
|-----------|-------|
| **Exists** | NO |
| **Required** | `OrganizationService.archive_organization(org_id, *, tenant_id)` |
| **Side effects** | Preserve all data; prevent creation of new business records (projects, work orders, employees, etc.); allow read-only access to historical data |
| **Distinction from Deactivate** | Archive is an intentional long-term state, typically following org consolidation or wind-down. Deactivation is a short-term operational toggle. |

Archive requires a guard in all create paths on child entities: any attempt to create a new record scoped to an archived organization must be rejected with a clear error. Read operations must remain permitted for audit and reporting.

---

### Delete Organization

| Attribute | Value |
|-----------|-------|
| **Exists** | NO |
| **Constraint** | `tenant_id FK` uses `ondelete=RESTRICT`; `organization_id` FK on all child tables also `RESTRICT` |
| **Required** | Soft delete only — `OrganizationService.soft_delete_organization(org_id, *, tenant_id)` |
| **Side effects** | Must handle cascade soft-delete for all org-owned data: sites, departments, employees, projects, work orders, cost items, and all scope-inherited records |
| **Risk level** | VERY HIGH — equivalent to destroying all business data for that organization |
| **Enterprise pattern** | Hard delete is prohibited. Archive first, then schedule GDPR purge via a separate retention-policy job that runs on a configurable schedule (e.g., 7-year retention). |

No API endpoint or UI action must be permitted to trigger hard deletion of an organization record or its child data outside of a formally scheduled, audited GDPR purge pipeline.

---

### Merge Organizations

| Attribute | Value |
|-----------|-------|
| **Exists** | NO |
| **Complexity** | VERY HIGH |
| **Use case** | Two companies merge into one; all business data from Org B must be re-parented under Org A |
| **Challenges** | Every record carrying `organization_id` must be migrated; foreign-key constraints require ordered migration; all event history and audit logs must be preserved with original `organization_id` for legal traceability |
| **Enterprise pattern** | Requires a dedicated `OrgMergeService` with a dry-run mode, a pre-merge validation report (duplicate codes, conflicting employees, overlapping project codes), a staged rollback capability, and a post-merge audit record. This is a platform-admin-only operation requiring two-admin approval. |

---

## The `_deactivate_other_organizations()` Critical Bug — Deep Analysis

**Location:** `OrganizationService._deactivate_other_organizations()` in `org/application/organization_service.py`

**Current behavior:** Issues an UPDATE against the `organizations` table with the predicate `id != exclude_id` and no `tenant_id` filter.

**Call sites:**
- `create_organization(is_active=True)` — called immediately after insert
- `set_active_organization(organization_id)` — called on every org switch

**Impact by deployment mode:**

| Deployment Mode | Impact |
|-----------------|--------|
| Single-tenant desktop (current) | Harmless — only one tenant exists, only one org ever active |
| Multi-tenant SaaS (target) | CATASTROPHIC — activating any org in any tenant silently deactivates every other org in every other tenant |

**Failure mode:** This bug is silent. No exception is raised. No log line is emitted at WARNING or above. An admin in Tenant ACME switching their active organization will deactivate all organizations in Tenant GLOBEX, Tenant INITECH, and every other tenant simultaneously. Users in those tenants will receive failures that appear as unrelated data access errors, making the root cause very difficult to diagnose in production.

**Immediate fix required:**

The deactivation query must be scoped to the current tenant. The method signature must accept `tenant_id` as a required parameter, and the UPDATE predicate must be:

```sql
UPDATE organizations
SET is_active = False
WHERE tenant_id = :tenant_id
  AND id != :exclude_id
```

Additionally, the broader question of whether the single-active invariant should be retained at all must be resolved before this method is retained in any form (see next section).

---

## Single-Active-Organization Invariant Assessment

**Current design:** Only one organization per tenant (in practice: globally) may have `is_active = True` at any time.

**Origin:** Desktop-era simplification. A single-user desktop application has one active context at a time; making it a persistent database column was a reasonable shortcut when multi-tenancy was not a requirement.

**Why this invariant is incorrect for enterprise SaaS:**

1. A tenant may operate multiple simultaneously active organizations (e.g., regional subsidiaries, acquired entities during integration periods, or holding-company structures with independent P&L centers).
2. `UserSessionContext` already carries `active_organization_id` as a session-level concept. This is the correct place to track "which org is the user currently working in."
3. Conflating "operationally enabled" (`is_active`) with "currently selected in session" creates the conditions for the cross-tenant deactivation bug described above.

**Recommendation:**

| Column | New Semantic |
|--------|-------------|
| `organizations.is_active` | "This organization is enabled and not archived or deleted." All enabled orgs within a tenant may simultaneously have `is_active = True`. |
| `UserSessionContext.active_organization_id` | "This is the organization the user is currently working within during this session." |

Under this model:
- `_deactivate_other_organizations()` is removed entirely from `create_organization()` and `set_active_organization()`.
- `is_active = False` is set only by an explicit `deactivate_organization()` call or by the archive/delete pipeline.
- The session switcher (org selector in the shell header) writes to `auth_sessions.last_active_organization_id`, not to `organizations.is_active`.

---

## Organization Switching — Current Flow

```
Admin Console QML
    └─► workspaceController.setActiveOrganization(itemId)
            └─► PlatformAdminWorkspaceController
                    └─► PlatformRuntimeDesktopApi.set_active_organization()
                            └─► PlatformRuntimeApplicationService.set_active_organization()
                                    [requires settings.manage permission]
                                    └─► TenantContextService.set_active_organization(organization_id)
                                            [validates is_active + _can_access()]
                                            └─► UserSessionContext.set_active_organization_id()
                                                    └─► persisted to auth_sessions.last_active_organization_id
```

**Gaps in the current flow:**

| Gap | Description |
|-----|-------------|
| Permission gate too restrictive | `settings.manage` is an admin-tier permission. A regular user switching between orgs they are a member of should not require admin permission. The gate should be `org.read` or membership verification only. |
| No org membership check | `_can_access()` validates `is_active` but does not verify the requesting user has any role or grant in the target organization. Any authenticated user who knows an `organization_id` can switch to it. |
| Admin Console only | The org switcher exists only in the Admin Console QML path. Non-admin users have no mechanism to switch organizations via the shell header. |
| No audit log on switch | Organization context switches are not recorded in the activity or audit log, making it impossible to reconstruct which org a user was working in when a particular action was taken. |

---

## Cross-Tenant Impact Analysis — All OrganizationService Methods

| Method | Tenant-Scoped? | Risk | Required Fix |
|--------|---------------|------|--------------|
| `create_organization()` | YES — has `tenant_id` param | MEDIUM | Remove call to non-scoped `_deactivate_other_organizations()` |
| `_deactivate_other_organizations()` | NO | CRITICAL | Add `tenant_id` filter or remove entirely |
| `get_active()` | NO | HIGH | Add required `tenant_id` parameter; return list not single row |
| `get_by_code()` | NO | HIGH | Add `tenant_id` parameter; `organization_code` uniqueness is currently global |
| `list_all()` | UNKNOWN — requires verification | MEDIUM | Verify and add `tenant_id` filter if absent |
| `set_active_organization()` | NO — no membership check | HIGH | Add tenant scope + membership verification |
| `provision_organization()` | NO — missing `tenant_id` param | HIGH | Add `tenant_id` as required parameter |

---

## Organization State Machine

```
  [Provisioned]
       │
       │  create_organization() / provision_organization()
       │
       ▼
  ┌─────────────────┐
  │     ACTIVE      │  ◄────────────────────────────────┐
  │  (is_active=T)  │                                   │
  └────────┬────────┘                                   │
           │                                            │
     deactivate()                                  activate()
           │                                            │
           ▼                                            │
  ┌─────────────────┐                                   │
  │    INACTIVE     │ ──────────────────────────────────┘
  │  (is_active=F)  │
  └────────┬────────┘
           │
       archive()
           │
           ▼
  ┌─────────────────┐
  │    ARCHIVED     │ ◄── read-only; no new business records
  │  (status=arch)  │
  └────────┬────────┘
           │
      restore()             delete() [platform-admin only]
           │                         │
           ▼                         ▼
        [ACTIVE]           ┌──────────────────┐
                           │   SOFT DELETED   │
                           │ (status=deleted) │
                           └────────┬─────────┘
                                    │
                            GDPR purge schedule
                            (retention policy job)
                                    │
                                    ▼
                              [Hard deleted —
                               audit log only]
```

**Valid transitions:**

| From | To | Trigger | Guard |
|------|----|---------|-------|
| (new) | ACTIVE | `create_organization()` | `tenant_id` required; `org_code` unique within tenant |
| ACTIVE | INACTIVE | `deactivate_organization()` | tenant-scoped; requires `org.manage` |
| INACTIVE | ACTIVE | `activate_organization()` | tenant-scoped; requires `org.manage` |
| ACTIVE | ARCHIVED | `archive_organization()` | requires `org.manage`; blocks new child records |
| INACTIVE | ARCHIVED | `archive_organization()` | same |
| ARCHIVED | ACTIVE | `restore_organization()` | requires platform-admin; audit log entry mandatory |
| ARCHIVED | SOFT DELETED | `soft_delete_organization()` | requires platform-admin + second-admin approval |
| SOFT DELETED | (none) | GDPR purge job | scheduled; irreversible; full audit trail preserved |

---

## Enterprise Recommendations

### Immediate — Bug Fixes (Sprint 0)

| Priority | Item | Location | Action |
|----------|------|----------|--------|
| P0 | Fix `_deactivate_other_organizations()` cross-tenant blast | `org/application/organization_service.py` | Add `WHERE tenant_id = :tenant_id` to deactivation query |
| P0 | Fix `get_active()` missing tenant filter | `SqlAlchemyOrganizationRepository` | Add required `tenant_id` parameter; return list |
| P0 | Fix `organization_code` global uniqueness constraint | `organizations` table DDL | Change to `UNIQUE(tenant_id, organization_code)` |
| P0 | Add org membership check to `set_active_organization()` | `TenantContextService` | Verify user has at least one role or grant in the target org |
| P0 | Add `tenant_id` to `provision_organization()` | `PlatformRuntimeApplicationService` | Make parameter required; propagate to all call sites |

### Short Term (Sprint 1–2)

| Priority | Item | Action |
|----------|------|--------|
| P1 | Remove single-active-org invariant from service layer | Remove `_deactivate_other_organizations()` calls from `create_organization()` and `set_active_organization()`; update `UserSessionContext` flow to be the sole owner of "selected org" state |
| P1 | Add `organizations.status` enum column | Values: `active`, `inactive`, `archived`, `deleted`; migrate `is_active` boolean to this enum; keep `is_active` as a generated column or view for backwards compatibility during migration |
| P1 | Add `deactivate_organization()` and `activate_organization()` service methods | Tenant-scoped; emit audit log entry |
| P1 | Downgrade org-switch permission gate | Replace `settings.manage` requirement with org membership verification in `set_active_organization()` |
| P1 | Audit log on org context switch | Record `(user_id, from_org_id, to_org_id, timestamp)` in activity log |

### Medium Term (Sprint 3–5)

| Priority | Item | Action |
|----------|------|--------|
| P2 | Implement `archive_organization()` | Service method + guard hooks on all child-record create paths |
| P2 | Add org switcher to shell header | Visible to any user with membership in more than one org; writes to session only, not to `organizations.is_active` |
| P2 | Implement `restore_organization()` | Platform-admin only; mandatory audit entry |
| P2 | Implement `soft_delete_organization()` | Platform-admin + second-admin approval workflow; cascades soft-delete to all child tables |
| P2 | Fix `list_all()` tenant scoping | Verify and enforce `tenant_id` filter |

### Long Term (Sprint 6+)

| Priority | Item | Action |
|----------|------|--------|
| P3 | Build `OrgMergeService` | Dry-run mode; pre-merge validation report; staged rollback; two-admin approval; full audit trail; platform-admin only |
| P3 | GDPR retention policy job | Scheduled hard-purge pipeline for soft-deleted organizations; configurable retention period (default: 7 years); purge confirmation audit record |
| P3 | Organization provisioning API | REST endpoint for `POST /tenants/{tenant_id}/organizations` replacing desktop-only provision flow |

---

# 18. DELIVERABLE 13 — SITE AND DEPARTMENT SECURITY MODEL

---

## D13.1 Current Site Data Model

**Table:** `sites`
**File:** `src/core/platform/infrastructure/persistence/orm/sites.py`

| Column | Type | Constraint |
|---|---|---|
| id | String | PK |
| tenant_id | String | FK → tenants.id RESTRICT, nullable |
| organization_id | String | FK → organizations.id CASCADE, NOT NULL |
| site_code | String(64) | NOT NULL |
| name | String(256) | NOT NULL |
| description | Text | nullable |
| country, region, city | String(128) | nullable |
| address_line_1, address_line_2 | String(256) | nullable |
| postal_code | String(64) | nullable |
| timezone | String(128) | nullable |
| currency_code | String(8) | nullable |
| site_type | String(128) | nullable |
| status | String(64) | nullable |
| default_calendar_id | String(64) | nullable (legacy field, see note) |
| default_language | String(32) | nullable |
| is_active | Boolean | NOT NULL, default True |
| opened_at, closed_at | DateTime | nullable |
| created_at, updated_at | DateTime | NOT NULL |
| notes | Text | nullable |
| version | Integer | NOT NULL, default 1 |

**Unique constraint:** `(organization_id, site_code)` — codes are unique within an org, not globally.

**Indexes:** `tenant_id`, `organization_id`, `(organization_id, is_active)`

**Note on default_calendar_id:** This is a legacy field referencing `working_calendars.id`. The enterprise CalendarResolver does not read it — it uses `site_calendar_assignments` and falls back to the global platform calendar. The field is retained for backward-compatible data export only.

**Tenant isolation pattern:** Both `tenant_id` and `organization_id` are present. All repository queries filter on both. The `tenant_id` column is nullable in the ORM definition (legacy migration artifact) but is populated at write time by `SqlAlchemySiteRepository.add()` via `TenantScopedRepositorySupport._context()`.

---

## D13.2 Current Department Data Model

**Table:** `departments`
**File:** `src/core/platform/infrastructure/persistence/orm/departments.py`

| Column | Type | Constraint |
|---|---|---|
| id | String | PK |
| tenant_id | String | FK → tenants.id RESTRICT, nullable |
| organization_id | String | FK → organizations.id CASCADE, NOT NULL |
| department_code | String(64) | NOT NULL |
| name | String(256) | NOT NULL |
| description | Text | nullable |
| site_id | String | FK → sites.id SET NULL, nullable |
| default_location_id | String | FK → maintenance_locations.id SET NULL, nullable |
| parent_department_id | String | FK → departments.id SET NULL, nullable (self-referential) |
| department_type | String(128) | nullable |
| cost_center_code | String(64) | nullable |
| manager_employee_id | String | FK → employees.id SET NULL, nullable |
| is_active | Boolean | NOT NULL, default True |
| created_at, updated_at | DateTime | NOT NULL |
| notes | Text | nullable |
| version | Integer | NOT NULL, default 1 |

**Unique constraint:** `(organization_id, department_code)` — codes are unique within an org.

**Indexes:** `tenant_id`, `organization_id`, `(organization_id, is_active)`, `site_id`, `default_location_id`

**Hierarchy:** `parent_department_id` enables an arbitrary-depth tree within one organization. `DepartmentService.create_department()` and `update_department()` call `validate_parent_department_id()` to prevent self-reference cycles at one level; deep-cycle detection is not enforced by the ORM.

**Site relationship:** `site_id` is a soft FK (SET NULL on site deletion). A department belongs to at most one site. `DepartmentService` validates at write time that the referenced `site_id` belongs to the active organization.

---

## D13.3 Employee Site and Department Denormalization

**File:** `src/core/platform/infrastructure/persistence/orm/employee.py`

`EmployeeORM` carries direct FKs to both tables:

- `site_id` FK → `sites.id` SET NULL, nullable
- `site_name` String(256) — denormalized name cache
- `department_id` FK → `departments.id` SET NULL, nullable
- `department` String(256) — denormalized name cache

Dedicated indexes: `idx_employees_site`, `idx_employees_department`

Resolution at write time is handled in `src/core/platform/employee/application/employee_support.py`:
- `resolve_employee_site_reference()` — looks up by `site_id`, falls back to name-match within the active org. Raises `EMPLOYEE_SITE_INVALID` if the site is not in the active org.
- `resolve_employee_department_reference()` — same pattern. Raises `EMPLOYEE_DEPARTMENT_INVALID`.

These FK columns are the structural prerequisite for any future site-scoped or department-scoped employee queries.

---

## D13.4 SiteService — Business Logic and Access Control

**File:** `src/core/platform/site/application/site_service.py`

`SiteService` is a concrete service class (not a facade). It requires `TenantContextService` for org context and optionally `UserSessionContext` for authorization.

**Read operations:**
- `list_sites(active_only)` — calls `require_any_permission(("settings.manage", "site.read"))`, fetches all org sites, then passes the result through `filter_scope_rows(..., scope_type="site", permission_code="site.read")`. Users with a site-scoped grant see only their granted sites; users with the org-level `settings.manage` permission see all.
- `get_site(site_id)` — checks `require_any_permission` then calls `require_scope_permission("site", site.id, "site.read")` for the specific site.
- `search_sites()` — delegates to `list_sites()` then filters by text.
- `find_site_by_code()` — permission check only, no scope row filter.

**Write operations:**
- `create_site()` and `update_site()` — both require `settings.manage` only. No site-scoped write permission exists.
- `update_site()` enforces optimistic concurrency via `expected_version`.
- Both operations emit `domain_events.sites_changed` and write an audit entry.

**Key finding:** `SiteService.list_sites()` already enforces site-scoped read filtering through `filter_scope_rows`. This is live and tested. Site-scoped access grants are architecturally operative for read access today.

---

## D13.5 DepartmentService — Business Logic and Access Control

**Files:** `src/core/platform/department/application/department_service.py` (facade), `department_queries.py`, `department_commands.py`, `department_access.py`

`DepartmentService` is a facade that delegates to sub-modules.

**Read operations (`department_queries.py`):**
- `list_departments(active_only)` — calls `require_any_permission(("settings.manage", "department.read"))`, fetches all org departments. No `filter_scope_rows` call. There is no department-scoped row filtering.
- `get_department(department_id)` — permission check plus org membership check. No scope grant check.
- `search_departments()` — same pattern; text filter over the full org list.

**Write operations (`department_commands.py`):**
- `create_department()` and `update_department()` — both require `settings.manage`.
- Cross-entity validation is performed: `site_id` must belong to active org, `default_location_id` must be valid for the site, `parent_department_id` cannot be self, `manager_employee_id` must exist.
- Both emit `domain_events.departments_changed` and write an audit entry.

**Key finding:** Unlike `SiteService`, `DepartmentService` does NOT call `filter_scope_rows`. There is no department-scoped access filtering anywhere in the service layer.

---

## D13.6 Site Access Policy — Registered ScopedRolePolicy

**File:** `src/core/platform/site/access_policy.py`

The `site` scope type has a fully defined policy:

```
SITE_SCOPE_ROLE_CHOICES: ("viewer", "operator", "manager")
SITE_SCOPE_ROLE_ALIASES: {"editor": "operator"}

viewer:   {site.read}
operator: {site.read, inventory.read, report.view}
manager:  {site.read, inventory.read, inventory.manage, import.manage, report.view, report.export}
```

**File:** `src/infra/composition/platform_registry.py` lines 294–316

The `site` policy is registered as a `ScopedRolePolicy` in the `ScopedRolePolicyRegistry` alongside `organization`. The `scope_exists_resolver` for `site` calls `site_repo.get(site_id) is not None`.

The registry currently contains exactly two platform-level scope policies: `organization` and `site`. The full app has five registered scopes: `organization`, `site`, `project`, `storeroom`, `maintenance`.

**There is no registered ScopedRolePolicy for `department`.** The word "department" appears as a `scope_type` value only in `calendar_exception_service.py` as a metadata label on `CalendarException` domain entities — it is not a security grant scope.

---

## D13.7 Permission Codes: Site and Department in DEFAULT_PERMISSIONS

**File:** `src/core/platform/auth/policy.py`

The 56-entry `DEFAULT_PERMISSIONS` dictionary contains:
- `"site.read"`: "View shared site directory records"
- `"department.read"`: "View shared department directory records"

There is no `site.manage`, `site.admin`, `department.manage`, or `department.admin` permission code. Write access to both entities is gated exclusively on `settings.manage`.

**Role assignments that include site.read:**
- `resource_manager`, `inventory_manager`, `maintenance_manager`, `payroll_manager`, `access_admin`

**Roles that include department.read:**
- `resource_manager`, `payroll_manager`

The `admin` role receives all 56 permission codes via `set(DEFAULT_PERMISSIONS.keys())`.

---

## D13.8 Repository Query Scope: Current Gaps

Both `SqlAlchemySiteRepository` and `SqlAlchemyDepartmentRepository` extend `TenantScopedRepositorySupport`. Every query filters on both `tenant_id` and `organization_id`.

**Existing query methods:**

| Repository | Methods |
|---|---|
| SqlAlchemySiteRepository | `add`, `update`, `get(site_id)`, `get_by_code(org_id, site_code)`, `list_for_organization(org_id, active_only)` |
| SqlAlchemyDepartmentRepository | `add`, `update`, `get(dept_id)`, `get_by_code(org_id, dept_code)`, `list_for_organization(org_id, active_only)` |

**Missing:** Neither repository has a method to list by `site_id` or `department_id`. For employees specifically, `EmployeeORM.site_id` and `EmployeeORM.department_id` carry indexed FKs but `SqlAlchemyEmployeeRepository` exposes no `list_for_site()` or `list_for_department()` method.

---

## D13.9 Assessment: What Works Today vs. What Is Missing

### What works today (no changes needed)

1. **Site-scoped read filtering is live.** `SiteService.list_sites()` calls `filter_scope_rows(scope_type="site", permission_code="site.read")`. A `ScopedAccessGrant` row with `scope_type="site"` and `scope_id=<site_id>` will correctly restrict visibility in the list view. This is confirmed by integration test `test_access_service_supports_site_scope_grants_and_site_filtering`.

2. **Site ScopedRolePolicy is registered.** Roles `viewer`, `operator`, and `manager` are defined with correct permission sets. The `scope_exists_resolver` is wired. `AccessControlService.assign_site_grant()` can be called against these roles today.

3. **`get_site()` enforces per-site scope permission.** `require_scope_permission("site", site.id, "site.read")` is called on direct lookup. A user without a site-scoped grant or org-level `settings.manage` cannot retrieve a site by ID.

4. **Cross-entity FK validation exists.** Department creation validates `site_id` org membership. Employee resolution validates `site_id` and `department_id` org membership.

5. **Optimistic concurrency** is enforced on both site and department writes via the `version` column.

### What is missing or incomplete

**Issue 1 — No site-scoped write permission.**
`create_site()` and `update_site()` require `settings.manage`. There is no `site.manage` permission code. An org-level site admin who should be able to manage one site but not org settings cannot be granted that capability.

**Issue 2 — No department-scoped access filtering.**
`DepartmentService.list_departments()` does not call `filter_scope_rows`. There is no `ScopedRolePolicy` for `department`. A user with any org-level `department.read` permission sees all departments in the org.

**Issue 3 — No department write permission code.**
`create_department()` and `update_department()` require only `settings.manage`. There is no `department.manage` permission code for delegated department administration.

**Issue 4 — No repository methods for site/department-scoped entity lists.**
Neither `EmployeeRepository` nor `TimesheetRepository` exposes `list_for_site()` or `list_for_department()`. Site-scoped and department-scoped filtering at the service layer cannot be applied without these methods. The structural prerequisites (indexed FKs on `EmployeeORM`) exist; the repository methods do not.

**Issue 5 — tenant_id nullable on sites and departments.**
Both `SiteORM.tenant_id` and `DepartmentORM.tenant_id` are defined as `nullable=True`. While `TenantScopedRepositorySupport` populates tenant_id at write time and filters on it at read time, the ORM constraint does not enforce it at the DB layer. A direct SQL insert bypassing the repository would produce a site or department without tenant isolation.

**Issue 6 — department scope_type has no ScopedRolePolicy.**
The calendar exception service uses `scope_type="department"` as a metadata label on `CalendarException` records, not as an access grant. If a `ScopedAccessGrant` row were inserted manually with `scope_type="department"`, the `ScopedRolePolicyRegistry` would have no policy to validate or resolve it. No department-level access grant can be issued through `AccessControlService` today.

---

## D13.10 Proposed Remediation

The following changes are ordered by effort and impact.

### Phase A — Permission codes (no schema change, low risk)

Add to `DEFAULT_PERMISSIONS` in `src/core/platform/auth/policy.py`:

```
"site.manage": "Create and edit site records",
"department.manage": "Create and edit department records",
```

Update `SiteService.create_site()` and `update_site()` to accept `site.manage` as an alternative to `settings.manage`:
```python
require_any_permission(user_session, ("settings.manage", "site.manage"), ...)
```

Do the same for `DepartmentService.create_department()` and `update_department()`.

This decouples site/department administration from full org settings access.

### Phase B — Department ScopedRolePolicy (no schema change, low risk)

Create `src/core/platform/department/access_policy.py` modeled on `site/access_policy.py`:

```
DEPARTMENT_SCOPE_ROLE_CHOICES: ("viewer", "manager")
viewer:  {department.read}
manager: {department.read, department.manage, employee.read, timesheet.approve}
```

Register in `platform_registry.py` alongside `organization` and `site`, with `scope_exists_resolver` that calls `department_repo.get(department_id) is not None`.

Update `DepartmentService.list_departments()` to call `filter_scope_rows(scope_type="department", permission_code="department.read")` mirroring the site pattern.

Update `DepartmentService.get_department()` to call `require_scope_permission("department", dept.id, "department.read")`.

### Phase C — Repository scope queries (targeted code addition, medium risk)

Add to `SqlAlchemyEmployeeRepository`:
```python
def list_for_site(self, site_id: str, *, active_only: bool | None = None) -> list[Employee]
def list_for_department(self, department_id: str, *, active_only: bool | None = None) -> list[Employee]
```

Both queries must include `tenant_id` and `organization_id` filters from `TenantScopedRepositorySupport._context()` in addition to the site/department FK filter.

Add equivalent methods to the timesheet repository if timesheet approval is to be department-scoped.

### Phase D — DB constraint hardening (schema migration, higher risk)

Issue a migration to set `tenant_id NOT NULL` on `sites` and `departments`, matching the pattern applied to the 34 other tables in the `r3s4t5u6v7w8` migration referenced in the tenant isolation audit.

This requires a data backfill pass to populate any existing rows with a null `tenant_id` before applying the constraint.

---

## D13.11 Summary Table

| Capability | Site | Department |
|---|---|---|
| ORM model | Complete | Complete |
| Tenant isolation (nullable ORM, enforced at repo layer) | Partial — tenant_id nullable | Partial — tenant_id nullable |
| Read permission code | site.read — exists | department.read — exists |
| Write permission code | site.manage — MISSING | department.manage — MISSING |
| Scoped role policy registered | Yes (viewer/operator/manager) | No — not registered |
| list() scope row filtering | Yes — filter_scope_rows active | No — not implemented |
| get() scope permission check | Yes — require_scope_permission | No — not implemented |
| Employee FK for scoped queries | employees.site_id indexed | employees.department_id indexed |
| Repository list_for_X() method | Not present | Not present |
| Audit trail on write | Yes — record_audit_entry | Yes — record_audit_entry |
| Optimistic concurrency | Yes — version column | Yes — version column |
| Self-referential hierarchy | No | Yes — parent_department_id |
| Manager designation | No | Yes — manager_employee_id |

---

# 19. DELIVERABLE 14 — MODULE ENTITLEMENT STRATEGY

## Current Implementation

**Table:** `organization_module_entitlements`

**Columns (as-built):**

| Column | Type | Notes |
|---|---|---|
| `organization_id` | String, FK → organizations.id CASCADE | Part of composite PK |
| `module_code` | String(128) | Part of composite PK |
| `tenant_id` | String, FK → tenants.id CASCADE, nullable | Non-PK FK, added in migration q2r3s4t5u6v7 |
| `licensed` | Boolean NOT NULL, default False | Commercial entitlement flag |
| `enabled` | Boolean NOT NULL, default False | Operational deployment flag |
| `lifecycle_status` | String(32) NOT NULL, default "inactive" | One of: inactive, active, trial, suspended, expired |
| `updated_at` | DateTime NOT NULL | Last mutation timestamp |

**Indexes:** `idx_org_module_entitlements_org` on `organization_id`; `idx_org_module_entitlements_tenant` on `tenant_id`.

A comment in the ORM (`src/core/platform/infrastructure/persistence/orm/modules.py`, line 30) explicitly defers the primary key to a future Phase C full table reconstruction: "PK stays (organization_id, module_code) until Phase C full table reconstruction. tenant_id added as a non-PK FK to support tenant-level entitlement queries."

**Canonical module codes** (from `src/core/platform/modules/domain/defaults.py`):

| Code | Label | Stage | default_enabled |
|---|---|---|---|
| `project_management` | Project Management | enabled | True |
| `inventory_procurement` | Inventory & Procurement | available | False |
| `maintenance_management` | Maintenance Management | available | False |
| `qhse` | QHSE | planned | False |
| `hr_management` | HR Management | planned | False |

**Legacy alias:** `"payroll"` normalizes to `"hr_management"` via `normalize_module_code()` in `src/core/platform/modules/domain/module_codes.py`. The `module_storage_codes()` function returns both canonical and legacy codes so that legacy DB rows are found and cleaned up on upsert.

**Stage semantics:**
- `"enabled"` — fully available; can be licensed and enabled.
- `"available"` — can be licensed and enabled.
- `"planned"` — cannot be licensed, enabled, or given a non-inactive lifecycle status; raises `ValidationError(code="MODULE_NOT_AVAILABLE")`.

**Always-on platform capabilities (not module-gated):** `users`, `access`, `audit`, `approvals`, `employees`, `documents`, `inbox`, `notifications`, `settings`. These are defined in `DEFAULT_PLATFORM_CAPABILITIES` in `defaults.py` and the `ModuleRegistry` always returns `True` for the `"platform"` module ID.

---

## Two-Tier Model: licensed vs enabled

The codebase already implements a two-tier boolean model per organization entitlement:

- **`licensed=True`** — The module is commercially entitled for this organization. This is the billing/procurement concern. Setting `licensed=False` automatically forces `enabled=False` and `lifecycle_status="inactive"`.
- **`enabled=True`** — The module is switched on for runtime use. This is the operational deployment concern. A module can be licensed but not enabled (purchased but awaiting configuration or staged rollout).

Enforcement in `ModuleCatalogMutationMixin.set_module_state()` (`src/core/platform/modules/application/module_catalog_mutation.py`):
1. Enabling requires licensing: `enabled=True` without `licensed=True` raises `ValidationError(code="MODULE_NOT_LICENSED")`.
2. Non-inactive lifecycle requires licensing: changing `lifecycle_status` away from `"inactive"` without being licensed raises `MODULE_NOT_LICENSED`.
3. Lifecycle must permit enablement: `enabled=True` is only allowed when `lifecycle_status in {"active", "trial"}`; otherwise raises `ValidationError(code="MODULE_STATUS_BLOCKS_ENABLEMENT")`.
4. Unlicensing cascades: forces `lifecycle_status="inactive"` and `enabled=False` automatically.
5. Licensing with no explicit status: auto-promotes `lifecycle_status` from `"inactive"` to `"active"`.

**Runtime access condition** (from `ModuleEntitlement.runtime_enabled`): `licensed AND enabled AND lifecycle_status in {"active", "trial"}`.

---

## Should Licensing Exist at Tenant Level?

### Current reality

There is no tenant-level entitlement entity. The `tenant_id` column in `organization_module_entitlements` is informational — it is backfilled from `organizations.tenant_id` on upsert and supports the `idx_org_module_entitlements_tenant` index, but no application-layer API queries across all organizations for a tenant using this index. The ORM comment confirms this is deferred to "Phase C".

`ModuleCatalogService` always resolves entitlements for the **active organization** only. If no active organization is set, all modules report `licensed=False` and `enabled=False`.

### Analysis

**Tenant-level licensing:**
- Advantage: One commercial record covers all organizations within a tenant. Simpler for billing ("Acme Corp has licensed modules X, Y, Z").
- Advantage: Prevents an organization from being provisioned with modules the tenant has not purchased.
- Disadvantage: Too coarse for selective rollout — Organization A might deploy `project_management` while Organization B deploys only `maintenance_management`.
- Disadvantage: Does not support phased activation within a single tenant.

**Organization-level licensing (current):**
- Advantage: Granular per-org control. Supports phased rollout.
- Disadvantage: Complex to aggregate for billing — requires summing across all organizations.
- Disadvantage: No guardrail prevents provisioning an organization with modules the tenant's commercial agreement does not cover. A tenant with no commercial agreement for `inventory_procurement` can currently have it enabled on any of its organizations without platform enforcement.

**Two-layer model (recommended):**
- Tenant level defines the **maximum permitted set** — what the tenant has commercially purchased.
- Organization level defines **deployment scope** — which of those modules are deployed to each specific organization.
- Constraint: `org.module.licensed=True` is only valid if `tenant.module.licensed=True`. Attempting to license a module at org level that is not licensed at tenant level raises a validation error.

---

## Recommended Two-Layer Model

### Layer 1 — Tenant Module License (new table: `tenant_module_licenses`)

**Purpose:** What has the tenant commercially purchased? Managed exclusively by Platform Admin.

**Proposed columns:**

| Column | Type | Notes |
|---|---|---|
| `tenant_id` | String, FK → tenants.id CASCADE, PK | |
| `module_code` | String(128), PK | |
| `is_licensed` | Boolean NOT NULL, default False | Commercial purchase flag |
| `license_type` | String(32) | trial, standard, enterprise |
| `licensed_at` | DateTime nullable | When license was granted |
| `expires_at` | DateTime nullable | NULL = perpetual |
| `updated_at` | DateTime NOT NULL | |

This table does not exist today. It must be added in a future migration. The existing `tenant_id` FK on `organization_module_entitlements` provides the DB-level linkage to anchor the cross-table constraint once the new table exists.

### Layer 2 — Organization Entitlement (existing: `organization_module_entitlements`)

No schema change required for the constraint model, except that `set_module_state()` and `provision_organization_entitlements()` must begin consulting Layer 1 before accepting `licensed=True` writes. The optional `module_version` column (for future compatibility tracking) can be deferred.

**Constraint at service layer:**
Before any operation that sets `licensed=True` on an organization entitlement, the service must verify `tenant_module_licenses.is_licensed=True` for the same tenant and module code. If no row exists or `is_licensed=False`, the operation raises `BusinessRuleError(code="MODULE_NOT_LICENSED_FOR_TENANT")`.

### Layer interaction summary

```
tenant_module_licenses (tenant_id, module_code, is_licensed, license_type, expires_at)
         |
         |  [tenant must hold license before org can license]
         v
organization_module_entitlements (organization_id, module_code, licensed, enabled, lifecycle_status)
         |
         |  [org must be licensed+enabled+active before runtime access]
         v
ModuleEntitlement.runtime_enabled  →  ModuleGuardedServiceMixin gate
```

---

## Module Lifecycle State Machine

Per module per organization:

```
[Not Entitled / licensed=False]
    |
    | set licensed=True → lifecycle_status auto-set to "active"
    v
[Licensed, Disabled]  (licensed=True, enabled=False, lifecycle_status in {"active","trial"})
    |                       |
    | set enabled=True      | set lifecycle_status="suspended" or "expired"
    v                       v
[Licensed, Enabled]   [Licensed, Blocked]
(runtime_enabled=True) (runtime_enabled=False — data preserved, features locked)
    |
    | set licensed=False → enabled forced False, lifecycle_status forced "inactive"
    v
[Revoked]  (licensed=False, enabled=False, lifecycle_status="inactive")
```

Key invariants enforced by `set_module_state()`:
- `enabled=True` requires `lifecycle_status in {"active", "trial"}`.
- `lifecycle_status` not `"inactive"` requires `licensed=True`.
- `licensed=False` cascades to `enabled=False` and `lifecycle_status="inactive"` unconditionally.
- Stage `"planned"` modules are fully blocked at all three fields.

---

## Module Guard Enforcement — Current State vs Recommended

### Current: `ModuleGuardedServiceMixin` (implemented)

File: `src/core/platform/modules/application/guard.py`

`ModuleGuardedServiceMixin` overrides `__getattribute__` to wrap every public method of a service class. Any class with `_module_guard_code` set and `_module_catalog_service` injected gets automatic pre-call enforcement via `require_module_enabled()`.

Currently used by: `ProjectManagementModuleGuardMixin` sets `_module_guard_code = "project_management"` and is inherited by all PM application services (`ProjectService`, `TaskService`, `ResourceService`, `PortfolioService`, `BaselineService`, `RiskRegisterService`, `CalendarService`, `TimesheetService`, `DashboardService`, `FinanceService`, `CostService`, `ForecastService`, `CollaborationService`, `ReportingService`, `DataImportService`, `ProjectResourceService`).

For `inventory_procurement` and `maintenance_management` modules, the guard is not applied via a dedicated mixin. Instead, `DocumentIntegrationService` methods call `require_module_enabled()` explicitly (passing `module_code` as a parameter). Inventory and maintenance services delegate to document integration with the appropriate module code.

`BusinessRuleError(code="MODULE_DISABLED")` is raised when the module is not runtime-enabled. The error message varies by lifecycle status: suspended / expired / trial-but-not-enabled / generic not enabled.

### Current: `require_module_enabled()` (implemented)

File: `src/core/platform/modules/application/authorization.py`

Accepts `module_catalog_service` (can be `None` — silently passes if not injected) and `module_code`. Returns `None` if `entitlement is None` (silently passes if no row found). This silent-pass behavior on a missing entitlement is a gap: an organization that has never had `provision_organization_entitlements()` called will have no rows, and all module checks will pass by default.

### Current: `ModuleRegistry` (implemented)

File: `src/core/platform/integration/module_registry.py`

Wraps `ModuleRuntimeService` and exposes:
- `is_module_enabled(module_id)` — returns `True` unconditionally for `"platform"`.
- `has_capability(capability_id)` — resolves capability to module via `_CAPABILITY_MODULE` dict.
- `can_use_integration(source, target, capability)` — checks static `_INTEGRATION_RULES` frozenset and requires both modules enabled at runtime.
- `capability_snapshot()` — flat dict for QML binding, covering all 5 modules and 4 cross-module integration pairs.

Used by QML contexts, desktop API capability checks, and cross-module integration resolution.

### Gaps in current enforcement

1. **Silent pass on missing entitlement row:** `require_module_enabled()` returns without error if `get_entitlement()` returns `None`. An org with no entitlement rows passes all module checks. This should fail-closed: a missing row should be treated as `runtime_enabled=False`.

2. **`inventory_procurement` and `maintenance_management` lack a mixin guard.** These two modules depend on explicit `require_module_enabled()` call-sites in `DocumentIntegrationService`. Any service method that does not pass through document integration has no automatic guard.

3. **No guard for `qhse` and `hr_management`.** These are currently `"planned"` stage, so licensing is blocked by `set_module_state()`. However, no runtime service guard exists for when these modules eventually move to `"available"` stage.

4. **`module_catalog_service=None` silently disables all checks.** If a service is instantiated without `_module_catalog_service`, the mixin passes every call. This is appropriate in test environments but creates a deployment risk if dependency injection is misconfigured.

### Recommended enforcement changes

1. **Fail-closed on missing entitlement row:** Change `require_module_enabled()` to treat `entitlement is None` as `MODULE_DISABLED` rather than silently passing.

2. **Add `InventoryModuleGuardMixin` and `MaintenanceModuleGuardMixin`** following the same pattern as `ProjectManagementModuleGuardMixin`, setting `_module_guard_code = "inventory_procurement"` and `"maintenance_management"` respectively. Apply to all Inventory and Maintenance application services.

3. **Require Layer 1 check in `set_module_state()` and `provision_organization_entitlements()`** once `tenant_module_licenses` is added: before accepting `licensed=True`, assert `tenant_module_licenses.is_licensed=True`.

4. **Add `_module_guard_code` for `qhse` and `hr_management`** to future service classes before those modules move out of `"planned"` stage.

---

## Module Code Registry — Current vs Recommended

### Current

Module codes are plain strings defined in `DEFAULT_ENTERPRISE_MODULES` in `defaults.py`. There is no runtime enum. Callers pass string literals. The only normalization is `normalize_module_code()` which resolves the one known legacy alias (`"payroll"` → `"hr_management"`).

The `ModuleRegistry` in `module_registry.py` documents the canonical IDs in a module-level docstring (lines 7–13) but does not enforce them at the type level.

### Recommended

Replace free-form strings with a module code constant registry:

```python
# src/core/platform/modules/domain/module_codes.py  (extend existing file)

MODULE_CODE_PROJECT_MANAGEMENT   = "project_management"
MODULE_CODE_INVENTORY_PROCUREMENT = "inventory_procurement"
MODULE_CODE_MAINTENANCE_MANAGEMENT = "maintenance_management"
MODULE_CODE_QHSE                 = "qhse"
MODULE_CODE_HR_MANAGEMENT        = "hr_management"

ALL_MODULE_CODES: frozenset[str] = frozenset({
    MODULE_CODE_PROJECT_MANAGEMENT,
    MODULE_CODE_INVENTORY_PROCUREMENT,
    MODULE_CODE_MAINTENANCE_MANAGEMENT,
    MODULE_CODE_QHSE,
    MODULE_CODE_HR_MANAGEMENT,
})
```

Use these constants everywhere instead of inline string literals. This does not require changing the DB schema or the `EnterpriseModule` dataclass (which already uses `code: str`). A Python `Literal` type annotation can be added to enforce codes at static analysis time without a runtime Enum.

---

## Default Entitlement Seeding

### Current behavior

`provision_organization_entitlements()` is called from `PlatformRuntimeApplicationService.provision_organization()`. If `initial_module_codes` is `None`, it auto-selects all modules where `module.default_enabled=True AND module.stage != "planned"`. Currently only `project_management` satisfies this (stage `"enabled"`, `default_enabled=True`).

All five modules receive rows in `organization_module_entitlements`: the selected modules get `licensed=True, enabled=True, lifecycle_status="active"`; the rest get `licensed=False, enabled=False, lifecycle_status="inactive"`. This means every organization always has a full set of five rows after provisioning — eliminating the silent-pass gap for organizations provisioned through the normal flow.

The gap remains for any organization created directly via `OrganizationService.create_organization()` without going through `provision_organization()`.

### Recommended

1. **Make `provision_organization_entitlements()` mandatory in `create_organization()`** — or enforce at the repository layer that an org cannot have zero entitlement rows at first use.

2. **Tenant-tier defaults:** Once `tenant_module_licenses` exists, seed it with a default set determined by the tenant's license tier (trial, standard, enterprise). `provision_organization()` should then derive `initial_module_codes` from `tenant_module_licenses` rather than from module `default_enabled` flags. This ensures org-level entitlements never exceed tenant-level purchase.

---

## Module Enablement Audit Trail

`set_module_state()` already calls `record_audit_entry()` after every state mutation with:
- `entity_type="module_entitlement"`, `entity_id=module.code`
- `metadata` includes `action`, `module_code`, `licensed`, `enabled`, `lifecycle_status`, `stage`
- `domain_events.modules_changed.emit(module.code)` is fired for downstream cache invalidation

`provision_organization_entitlements()` also calls `record_audit_entry()` with:
- `entity_type="organization"`, `entity_id=organization_id`
- `metadata` includes `licensed_modules` and `enabled_modules` as comma-separated sorted strings

This is sufficient for basic audit trail. No gaps at the service layer for mutations that go through `ModuleCatalogMutationMixin`.

---

## Architecture Decision Summary

| Question | Current State | Finding / Recommendation |
|---|---|---|
| Licensing granularity | Organization only | Gap: no tenant-level ceiling. Add `tenant_module_licenses` table as Layer 1. |
| licensed vs enabled distinction | Implemented — two separate booleans | Correct design. Retain as-is. |
| lifecycle_status | Five statuses (inactive/active/trial/suspended/expired) | Correct. Runtime access requires status in {active, trial}. |
| Guard mechanism | `ModuleGuardedServiceMixin` via `__getattribute__` | Implemented for PM. Gap: INV and MNT lack a mixin guard; rely on explicit call-sites. |
| Missing entitlement silent-pass | `require_module_enabled()` returns None if no row | Gap. Should fail-closed: missing row = MODULE_DISABLED. |
| Module code type | Free-form string literals | Gap. Add named constants in `module_codes.py`; no schema change required. |
| Tenant license table | Absent | Missing. `tenant_id` FK in org entitlements is a placeholder; Phase C reconstruction needed. |
| Default entitlement seeding | Via `provision_organization()` only | Gap: orgs created directly via `create_organization()` skip seeding. |
| Planned-module guard | Blocked at `set_module_state()` | Correct for write path. Runtime guard for qhse/hr_management must be added before stages advance. |
| Audit trail | `record_audit_entry()` in `set_module_state()` and `provision_organization_entitlements()` | Adequate for current scope. |
| Cross-module integration rules | `ModuleRegistry._INTEGRATION_RULES` frozenset | Static rules. Correct pattern. |

---

## Implementation Sequence

**Phase C-1 (deferred, as noted in ORM):** Add `tenant_module_licenses` table and migrate `tenant_id` from non-PK FK to a participant in a proper tenant-level entitlement model. Re-key `organization_module_entitlements` PK if required.

**Phase C-2:** Update `set_module_state()` and `provision_organization_entitlements()` to validate against `tenant_module_licenses` before accepting `licensed=True`.

**Phase C-3:** Add `InventoryModuleGuardMixin` and `MaintenanceModuleGuardMixin` following the `ModuleGuardedServiceMixin` pattern. Apply to all Inventory and Maintenance application services.

**Phase C-4:** Change `require_module_enabled()` to fail-closed on `entitlement is None`.

**Phase C-5:** Replace inline module code string literals with named constants from an extended `module_codes.py`.

---

# 20. DELIVERABLE 15 — TENANT READINESS ASSESSMENT

Evaluate the current architecture's readiness for each deployment model.

## Deployment Model 1 — Desktop Single Tenant

**Description:** One installation, one company, one database, one user running on desktop.

**Current Readiness: 85/100**

**What works:**
- Full business functionality (PM, inventory, maintenance)
- User auth, roles, permissions
- Tenant isolation is present (even if only one tenant)
- All repository scoping patterns work correctly
- Bootstrap defaults create admin user and seed roles/permissions
- Module entitlements configurable

**Blockers:** None for this deployment model

**Risks:**
- MFA non-functional (MEDIUM)

**Required changes for full 100:**
- Fix MFA UI to collect and validate TOTP code

---

## Deployment Model 2 — Desktop Multi-Organization

**Description:** One installation, one company, multiple operational divisions (orgs), single database.

**Current Readiness: 60/100**

**What works:**
- Multiple orgs can exist in the database
- Org-scoped role bindings in user_roles
- ScopedAccessGrant supports org scope
- Module entitlements per-org

**Blockers:**
1. `_deactivate_other_organizations()` BUG — activating one org deactivates all others globally, not per-tenant (CRITICAL)
2. No org switcher in shell header; users must navigate to Admin Console (CRITICAL UX)
3. `user_roles` unique constraint is on `(user_id, role_id)` only — prevents a user holding the same role at both global and org scope simultaneously
4. No `org_admin` role; the full `admin` role is required for org management, violating least-privilege
5. `get_active()` on org repository is not tenant-scoped (minor in single-tenant but structurally incorrect)

**Required changes:**
1. Fix `_deactivate_other_organizations()` to scope deactivation to the current tenant only (CRITICAL)
2. Remove or explicitly scope the single-active-org invariant per tenant rather than globally
3. Add org switcher to shell header
4. Add `org_admin` role with org-management permissions only
5. Fix `user_roles` unique constraint to `(user_id, role_id, organization_id)` to allow scoped duplicates

---

## Deployment Model 3 — On-Premise Server

**Description:** Server installation at customer site, single tenant, multi-user concurrent access.

**Current Readiness: 55/100**

**What works:**
- Data model is complete and correctly scoped
- Repository scoping patterns are correct
- Auth, roles, and permissions are functional for a single concurrent user

**Blockers:**
1. Application is built as a desktop app (QML/PyQt) — it is not a web service and has no server process model
2. No concurrent-user session management (architecture assumes single-user desktop)
3. No REST API or GraphQL layer
4. No web frontend
5. Database defaults to SQLite — no production PostgreSQL configuration documented or enforced
6. No connection pooling configuration
7. No horizontal scaling support

**Required changes:**
1. Database: Switch to PostgreSQL with a properly configured connection pool (e.g., SQLAlchemy pool + pgBouncer)
2. API layer: Build a REST or GraphQL API; the current desktop API layer is insufficient for multi-user server deployment
3. Session management: Replace in-memory `UserSessionContext` with a distributed or persistent session store
4. Web frontend: Build a web UI or formally document that thin-client QML remoting is supported
5. MFA must be fully functional for server deployment (HIGH priority at this tier)

**Note:** This model requires a significant architectural shift from the current desktop-first design. The data model is sound; the delivery layer must be rebuilt.

---

## Deployment Model 4 — Multi-Tenant Server

**Description:** SaaS-style deployment, multiple companies, shared infrastructure, one database.

**Current Readiness: 30/100**

**What works:**
- `tenant_id` columns exist and are NOT NULL on all 34 data tables
- `TenantContextService` resolves active tenant context
- Repository `_apply_scope()` patterns are tenant-aware
- Per-org module entitlements exist via `organization_module_entitlements`

**Blockers (CRITICAL — all must be resolved before this model is viable):**
1. No `user_tenants` table — there is no enforcement of which users belong to which tenant
2. `set_active_tenant()` performs no membership check — any user can switch to any tenant (security breach)
3. `_deactivate_other_organizations()` is not tenant-scoped — activating an org in Tenant A can deactivate orgs in Tenant B (data corruption)
4. `users.username` is globally unique — two tenants cannot have a user with the same username, a hard constraint in any shared-infrastructure model
5. No tenant management API (`create_tenant`, `list_tenants`, `deactivate_tenant`)
6. No tenant switcher UI
7. `users`, `roles`, and `permissions` are platform-global with no tenant isolation
8. `User.list_all()` is unscoped — Tenant A can enumerate Tenant B's users
9. No `tenant_admin` or `org_admin` roles; `admin` role bypasses all scope checks and grants all 56 permissions globally
10. Application architecture is desktop, not a web service (same blocker as On-Premise Server)

**Required changes:** All 20+ items from the Prioritized Action List, including at minimum: adding `user_tenants`, scoping `set_active_tenant()`, fixing the username uniqueness model, building tenant management APIs, and completing the architectural shift to a server model.

---

## Deployment Model 5 — Private Cloud

**Description:** Customer-hosted cloud instance (AWS/Azure/GCP), potentially single-tenant but cloud-native.

**Current Readiness: 35/100**

**What works:**
- Same data-layer foundation as Multi-Tenant Server
- Core scoping patterns would survive containerization if the data layer is migrated to PostgreSQL

**Blockers:**
1. Not containerized — no Dockerfile or container build configuration found
2. No cloud configuration management (all config is file-based or hardcoded)
3. No secrets management integration (no Vault, AWS Secrets Manager, or equivalent)
4. No health check endpoints for load balancer or orchestrator integration
5. No observability infrastructure (no metrics, distributed tracing, or structured logging)
6. No graceful shutdown handling for SIGTERM (container orchestrator requirement)
7. SQLite is not suitable for any cloud deployment; PostgreSQL migration is mandatory
8. All On-Premise Server blockers apply in full

**Additional required changes:**
1. Containerization via Docker or Podman with a production-grade entrypoint
2. All configuration driven by environment variables (12-factor app compliance)
3. Secrets management integration (no credentials in config files or source)
4. Health check endpoint (`/healthz` or equivalent) returning service status and DB connectivity
5. Structured JSON logging with correlation IDs
6. Prometheus-compatible metrics endpoint
7. PostgreSQL with a cloud-managed instance (RDS, Cloud SQL, Azure Database)

---

## Deployment Model 6 — SaaS

**Description:** Fully managed, multi-tenant, cloud-native, self-service onboarding, subscription billing.

**Current Readiness: 20/100**

**What works:**
- Core data model is solid and well-normalized
- Multi-tenant data isolation foundation exists at the schema level
- Module entitlement concept (`organization_module_entitlements`) is present and aligns with feature-flag and licensing patterns

**Blockers (all of the above plus the following):**
- No user invitation or self-service registration workflow
- No subscription billing integration (Stripe, Paddle, or equivalent)
- No automated tenant provisioning workflow (schema migration, seeding, onboarding)
- No tenant self-service admin portal
- No usage metering or per-tenant resource quotas
- No SSO / SAML / OIDC support (enterprise SaaS requirement)
- No API rate limiting or per-tenant throttling
- No data export or GDPR/right-to-erasure tooling
- Application architecture is fundamentally desktop; complete delivery-layer rebuild required

**Assessment:** This is a 12-24 month engineering effort from current state. The data model provides a viable foundation, but every layer above the ORM — session management, API, auth, frontend, billing, and operations — must be built from scratch or replaced.

---

## Readiness Summary

| Deployment Model | Readiness | Critical Blockers | Estimated Effort |
|---|---|---|---|
| Desktop Single Tenant | 85/100 | 0 critical | 2-4 weeks (hardening only) |
| Desktop Multi-Org | 60/100 | 2 critical bugs | 4-8 weeks |
| On-Premise Server | 55/100 | Architectural shift required | 3-6 months |
| Multi-Tenant Server | 30/100 | 10+ critical | 6-12 months |
| Private Cloud | 35/100 | Containerization + all server blockers | 4-8 months |
| SaaS | 20/100 | Complete delivery-layer rebuild | 12-24 months |

---

## Recommended Progression Path

The architecture should advance through deployment tiers sequentially. Skipping tiers introduces compounding risk because each phase's fixes are prerequisites for the next.

**Phase A — Critical Bug Fixes (now, 8 weeks):** Fix `_deactivate_other_organizations()`, fix `set_active_tenant()` membership check, fix `user_roles` unique constraint, add `org_admin` role, add org switcher to shell header. Target: Desktop Multi-Org readiness reaches 85+.

**Phase B — Multi-Tenant Security Controls (3 months):** Add `user_tenants` table with membership enforcement, scope `User.list_all()`, fix username uniqueness model, add `tenant_admin` role, add tenant management API, fix `is_platform_admin()` dead code. Target: Multi-Tenant Server readiness reaches 60+.

**Phase C — API Layer and Database (6 months):** Migrate to PostgreSQL, build REST or GraphQL API layer, replace in-memory session management, implement functional MFA. Target: On-Premise Server readiness reaches 80+.

**Phase D — Cloud-Native Operations (12 months):** Containerize, add environment-variable configuration, integrate secrets management, implement health checks, structured logging, and metrics. Target: Private Cloud readiness reaches 80+.

**Phase E — SaaS Features (18-24 months):** Add self-service onboarding, subscription billing, SSO/SAML/OIDC, rate limiting, usage metering, GDPR tooling, and tenant self-service admin portal. Target: SaaS readiness reaches 75+.

---

# 21. DELIVERABLE 16 — REPOSITORY GOVERNANCE STANDARD

## 21.1 Purpose and Scope

This deliverable establishes the authoritative governance standard for all SQLAlchemy repository classes in the codebase. It defines allowed patterns, forbidden patterns, required scoping rules, naming conventions, and the PR checklist that must be satisfied before any new or modified repository is merged. The standard covers approximately 80 repository classes across four modules (Platform, Project Management, Inventory & Procurement, Maintenance) and applies retroactively to all future work.

The standard is derived from the repository scan catalogued above and from the critical tenant isolation findings documented in prior deliverables.

---

## 21.2 Repository Taxonomy

Every repository in the codebase falls into exactly one of three categories. Misclassifying a repository is itself a governance violation.

### Category 1 — Tenant-and-Org-Scoped Repository

A repository whose entity rows belong to a specific (tenant_id, organization_id) pair. Every read, write, update, and delete operation MUST carry both filters.

Current examples: SqlAlchemyDepartmentRepository, SqlAlchemyEmployeeRepository, SqlAlchemySiteRepository, SqlAlchemyPartyRepository, SqlAlchemyProjectRepository, SqlAlchemyResourceRepository, SqlAlchemyTaskRepository, all Inventory module repos, all Maintenance module repos, enterprise calendar repos.

Required base class: one of ProjectManagementTenantScopedRepositorySupport, InventoryTenantScopedRepositorySupport, MaintenanceTenantScopedRepositorySupport, or TenantScopedRepositorySupport (Platform).

### Category 2 — Tenant-Scoped-Only Repository

A repository whose entity rows belong to a tenant but span all organizations within that tenant. Only tenant_id is required as a mandatory filter; organization_id is an optional refinement parameter.

Current examples: SqlAlchemyOrganizationRepository.list_for_tenant(tenant_id).

These are rare and must be explicitly justified. A Category 2 classification requires a written comment on the class or method explaining why organization_id is not applicable.

### Category 3 — Platform-Global Repository

A repository whose entity rows have no tenant or org affiliation. tenant_id and organization_id filters MUST NOT be applied.

Current examples: SqlAlchemyUserRepository, SqlAlchemyRoleRepository, SqlAlchemyPermissionRepository, SqlAlchemyRolePermissionRepository, SqlAlchemyTenantRepository, SqlAlchemyRuntimeExecutionRepository.

Required marker: the class MUST carry a `# PLATFORM-GLOBAL: no tenant/org scoping by design` comment on the class declaration and MUST NOT inherit from any TenantScopedRepositorySupport base class.

---

## 21.3 Current Implementation Patterns

### Pattern A — Inline WHERE in _base_stmt or _project_scoped_stmt

```python
def _base_stmt(self, ctx) -> Select:
    return select(ProjectORM).where(
        ProjectORM.tenant_id == ctx.tenant_id,
        ProjectORM.organization_id == ctx.organization_id,
    )
```

Used by: SqlAlchemyProjectRepository, SqlAlchemyResourceRepository, SqlAlchemyTaskRepository, SqlAlchemyBaselineRepository, SqlAlchemyRegisterRepository, and their child variants.

Assessment: PREFERRED. Explicit, readable, type-checked at the column reference level. No runtime introspection. The column reference ProjectORM.tenant_id will raise an AttributeError at import or first call if the column is absent, giving a loud failure rather than a silent miss.

### Pattern B — _apply_scope() via Mixin with hasattr() Introspection

```python
def _apply_scope(self, stmt, orm_model, ctx):
    if hasattr(orm_model, "organization_id"):
        stmt = stmt.where(orm_model.organization_id == ctx.organization_id)
    if hasattr(orm_model, "tenant_id"):
        stmt = stmt.where(orm_model.tenant_id == ctx.tenant_id)
    return stmt
```

Used by: ProjectManagementTenantScopedRepositorySupport, InventoryTenantScopedRepositorySupport, MaintenanceTenantScopedRepositorySupport, and all repos inheriting from them.

Assessment: CONDITIONALLY ACCEPTABLE for existing code only. The hasattr() check produces a SILENT MISS if an ORM model is missing a column — the filter is omitted and the method returns cross-tenant data without raising. New repositories MUST NOT introduce new uses of this pattern without replacing hasattr() with a static assertion. The migration path is described in Section 21.5.

### Pattern C — _get_in_scope / _require_in_scope

Single-row fetch variants that apply _apply_scope before execution:

```python
def _get_in_scope(self, orm_model, record_id, operation_label):
    ctx = self._context(operation_label)
    stmt = select(orm_model).where(orm_model.id == record_id)
    stmt = self._apply_scope(stmt, orm_model, ctx)
    return self._session.scalar(stmt)

def _require_in_scope(self, orm_model, record_id, operation_label, not_found_message):
    result = self._get_in_scope(orm_model, record_id, operation_label)
    if result is None:
        raise NotFoundError(not_found_message)
    return result
```

Used by: Inventory and Maintenance module repos for all single-entity fetches.

Assessment: GOOD. Centralises the PK-plus-scope lookup pattern and prevents the common mistake of fetching by PK alone. All new repos that inherit from a scoped mixin MUST use _require_in_scope rather than a bare session.get().

### Pattern D — JOIN-anchor scoping via ParentScopedRepositorySupport

Child entities without their own tenant_id column are scoped through a JOIN to their anchor (parent) entity:

```python
def _scoped_stmt_for_anchor(self, row_model, anchor_model, joins, operation_label):
    ctx = self._context(operation_label)
    stmt = select(row_model)
    for join in joins:
        stmt = stmt.join(join)
    stmt = self._apply_scope(stmt, anchor_model, ctx)
    return stmt
```

Used by: work order tasks, asset components, project resources, task assignments, task dependencies, baselines, register items, PM calendar assignments, portfolio project dependencies.

Assessment: CORRECT and REQUIRED for child entities. A child entity row inherits its scope from its anchor. Attempting to add a tenant_id column to every child table would be redundant and would not improve security. The anchor chain must terminate at a row that carries both tenant_id and organization_id directly.

### Pattern E — Guard Check Before Query Execution

An explicit method-level guard applied after the base statement is constructed:

```python
if not self._organization_in_scope(ctx, organization_id):
    return []
```

Used by: get_by_code variants in DepartmentRepository, EmployeeRepository, SiteRepository, and their equivalents.

Assessment: DEFENSIVE EXTRA LAYER. This guard catches the case where a caller passes an organization_id that belongs to a different tenant. It is not a substitute for the WHERE clause but is a valuable secondary check. It SHOULD be applied in all list_for_organization and get_by_code methods that accept an explicit organization_id parameter.

---

## 21.4 Required Scoping Rules

The following rules are unconditional. There are no exceptions unless the repository is explicitly classified as Category 3 (Platform-Global) or the method is explicitly classified as a Platform Admin operation (Section 21.6).

**Rule R1 — ALL read operations on Category 1 repos must include a tenant_id WHERE clause.**
Failure mode: rows from foreign tenants are returned to the caller. This is a data breach.

**Rule R2 — ALL read operations on Category 1 repos must include an organization_id WHERE clause.**
Failure mode: rows from foreign organizations within the same tenant are returned. This is an authorization breach.

**Rule R3 — ALL write operations (INSERT) on Category 1 repos must stamp tenant_id and organization_id onto the new ORM object before flushing.**
Failure mode: a new row is created with NULL or incorrect tenant/org, making it unreachable or globally readable depending on which index is hit first.

**Rule R4 — ALL update operations on Category 1 repos must include tenant_id and organization_id in the WHERE clause or extra_filters argument, not only the primary key.**
Rationale: a bare UPDATE WHERE id = :id can update a row belonging to another tenant if the caller has been given a foreign ID through any path. The extra tenant+org filter makes this attack inert.

**Rule R5 — ALL delete operations on Category 1 repos must include tenant_id and organization_id in the WHERE clause.**
Same rationale as R4.

**Rule R6 — count() and exists() queries must apply full tenant+org scope.**
A count or boolean response that leaks the existence of records in another tenant is an information disclosure vulnerability.

**Rule R7 — _apply_scope() implementations must replace hasattr() with a static assertion.**
The standard enforcement mechanism is a class-level Protocol or ABC that requires concrete repos to declare a SCOPED_MODEL class variable. The migration plan is in Section 21.5.

**Rule R8 — No repository method may accept a raw SQL string parameter.**
All query construction must use SQLAlchemy ORM column references or Core expression constructs. This prevents SQL injection through repository interfaces.

**Rule R9 — The _context() call must be the first statement in every repository method on Category 1 repos.**
This ensures that a missing or expired tenant context raises before any DB I/O occurs, giving a clean error rather than an unscoped query.

---

## 21.5 Remediation Plan for Pattern B hasattr() Risk

The current hasattr() implementation in all three module-level _apply_scope() methods is a latent bug. The following migration replaces it without changing the external interface of any repository.

### Step 1 — Define a Protocol for scoped ORM models

In each module's _tenant_scope.py, add:

```python
from typing import Protocol, ClassVar
from sqlalchemy.orm import DeclarativeBase

class TenantScopedORM(Protocol):
    tenant_id: ClassVar[str]         # mapped column name for type checking
    organization_id: ClassVar[str]
```

This is a documentation-level protocol only — SQLAlchemy ORM classes do not inherit from it. The real enforcement is in Step 2.

### Step 2 — Replace hasattr() with direct attribute access

```python
# BEFORE (silent miss):
def _apply_scope(self, stmt, orm_model, ctx):
    if hasattr(orm_model, "organization_id"):
        stmt = stmt.where(orm_model.organization_id == ctx.organization_id)
    if hasattr(orm_model, "tenant_id"):
        stmt = stmt.where(orm_model.tenant_id == ctx.tenant_id)
    return stmt

# AFTER (loud fail):
def _apply_scope(self, stmt, orm_model, ctx):
    stmt = stmt.where(orm_model.organization_id == ctx.organization_id)
    stmt = stmt.where(orm_model.tenant_id == ctx.tenant_id)
    return stmt
```

If an ORM model lacks the column, SQLAlchemy will raise AttributeError at the point of column access, which is a loud and immediately actionable failure during development or CI, not a silent data leak in production.

### Step 3 — Add a test fixture that catches missing columns

```python
def test_apply_scope_requires_tenant_columns(scoped_repo, orm_model_without_tenant_id):
    with pytest.raises(AttributeError):
        scoped_repo._apply_scope(select(orm_model_without_tenant_id), orm_model_without_tenant_id, mock_ctx)
```

This fixture is added to the shared repository test suite and runs in CI for all module scoped support classes.

---

## 21.6 Platform Admin Repository Pattern

Some operations require intentional cross-tenant access. These are not governance violations but must be explicitly designated and gated.

### Designation

A method that intentionally operates cross-tenant must carry the following decorator or inline comment:

```python
# PLATFORM-ADMIN-OPERATION: cross-tenant read. Caller must hold tenant.manage permission.
def list_all_tenants(self) -> list[TenantORM]: ...
```

### Mandatory permission gate

Every Platform Admin operation MUST be called from a service layer method that begins with:

```python
require_permission(session, principal, "tenant.manage")
```

or, for organization-level admin operations that cross organizations within a single tenant:

```python
require_permission(session, principal, "org.manage")
```

Calling a Platform Admin repo method from a service that does not perform this check is a governance violation.

### Current Platform Admin methods (pre-approved)

| Repository | Method | Required Permission |
|---|---|---|
| SqlAlchemyTenantRepository | all methods | tenant.manage |
| SqlAlchemyOrganizationRepository | add, update, get, get_by_code, get_active, list_all | org.manage |
| SqlAlchemyOrganizationRepository | list_for_tenant(tenant_id) | org.manage |
| SqlAlchemyUserRepository | all methods | access.manage or security.manage |
| SqlAlchemyRoleRepository | all methods | access.manage |
| SqlAlchemyPermissionRepository | all methods | access.manage |
| SqlAlchemyRolePermissionRepository | all methods | access.manage |
| SqlAlchemyRuntimeExecutionRepository | all methods | support.admin |
| SqlAlchemyModuleEntitlementRepository | *_for_organization variants | org.manage |
| SqlAlchemyApprovalRepository | project_in_different_organization | Internal use only — no external caller |
| SqlAlchemyActivityRepository | list_recent (no filters) | audit or support.admin |

---

## 21.7 Allowed Standard Interface

Every Category 1 repository MUST implement the following core methods. All must apply full tenant+org scope. The signatures below are the normative interface — implementation details may vary (Pattern A or C), but the contract is fixed.

### Mandatory methods

```python
def get(self, entity_id: str) -> Entity | None
    # Returns None if not found in current tenant+org scope.
    # MUST NOT raise for a missing row. MUST raise if context is missing.

def require(self, entity_id: str) -> Entity
    # Returns entity or raises NotFoundError.
    # Implemented as: result = self.get(entity_id); if not result: raise NotFoundError(...)

def add(self, entity: Entity) -> None
    # Stamps tenant_id and organization_id on entity before write.

def update(self, entity: Entity) -> None
    # Includes tenant_id and organization_id in WHERE / extra_filters.
    # Uses optimistic locking (version check) where the ORM model carries a version column.

def delete(self, entity_id: str) -> None
    # Includes tenant_id and organization_id in WHERE.
```

### Standard optional methods

```python
def exists(self, entity_id: str) -> bool
    # Scoped COUNT query returning bool.

def list_all(self) -> list[Entity]
    # All rows for current tenant+org. Avoid on large tables — pagination required.

def list_for_organization(self, organization_id: str, active_only: bool = True) -> list[Entity]
    # Filtered by organization_id with _organization_in_scope guard.

def count(self) -> int
    # Scoped row count.
```

---

## 21.8 Forbidden Methods

The following method signatures MUST NOT appear on any Category 1 or Category 2 repository. A PR introducing any of these will be rejected at review.

| Forbidden signature | Reason |
|---|---|
| list_all_unscoped() | Returns cross-tenant rows to the caller |
| get_unscoped(entity_id) | Can return a row belonging to another tenant |
| delete_all() | Mass deletion without scope; destructive across tenants |
| Any method accepting a raw str as sql_fragment parameter | SQL injection surface |
| Any method that calls session.execute(text(...)) | Same — raw SQL |
| Any method that calls _apply_scope conditionally based on a flag | The scope is not optional |
| Any method that wraps a Platform Admin operation without a permission gate | Privilege escalation |

The ActivityRepository.add() method that does not stamp scope (currently Category 3 by accident) must be treated as a known exception. It is documented in Section 21.6 and must be migrated to stamp scope before the next major release.

---

## 21.9 Repository Naming Conventions

### Class naming

```
SqlAlchemy{Entity}Repository
    — primary scoped repository for a top-level entity

{Module}TenantScopedRepositorySupport
    — base mixin for all top-level entity repos in a module

{Module}ParentScopedRepositorySupport
    — base mixin for all child entity repos in a module
```

Module values: ProjectManagement, Inventory, Maintenance, Platform (for the Platform module, TenantScopedRepositorySupport is used without a module prefix).

### Method naming

| Pattern | Example |
|---|---|
| get_{entity}(entity_id) | get_work_order(work_order_id) |
| require_{entity}(entity_id) | require_work_order(work_order_id) |
| list_{entities}() | list_work_orders() |
| list_{entities}_for_{parent}(parent_id) | list_work_orders_for_asset(asset_id) |
| list_{entities}_for_organization(organization_id) | list_work_orders_for_organization(organization_id) |
| add_{entity}(entity) | add_work_order(work_order) |
| update_{entity}(entity) | update_work_order(work_order) |
| delete_{entity}(entity_id) | delete_work_order(work_order_id) |
| count_{entities}() | count_work_orders() |
| exists_{entity}(entity_id) | exists_work_order(work_order_id) |

Methods that deviate from this scheme must include a docstring explaining the deviation.

---

## 21.10 Implementation Checklist for New Repositories

When writing a new repository class from scratch, the following steps must be followed in order.

**Step 1 — Classify the repository.**
Determine Category 1, 2, or 3. Write the classification as a class-level comment.

**Step 2 — Select the correct base class.**
Category 1 in PM module: inherit from ProjectManagementTenantScopedRepositorySupport (top-level) or ProjectManagementParentScopedRepositorySupport (child).
Category 1 in Inventory module: inherit from InventoryTenantScopedRepositorySupport or InventoryParentScopedRepositorySupport.
Category 1 in Maintenance module: inherit from MaintenanceTenantScopedRepositorySupport or MaintenanceParentScopedRepositorySupport.
Category 1 in Platform module: inherit from TenantScopedRepositorySupport.
Category 3: no base class, add PLATFORM-GLOBAL comment.

**Step 3 — Implement _base_stmt or confirm _apply_scope coverage.**
Preferred (Pattern A): implement a private _base_stmt(self, ctx) method that returns a SELECT with both WHERE clauses.
Acceptable (Pattern C): confirm that _get_in_scope and _require_in_scope are inherited and called correctly.

**Step 4 — Implement the mandatory interface.**
get(), add(), update(), delete() are the minimum. require() and exists() should be added if the calling service uses them.

**Step 5 — Stamp scope on add().**
Either call self._stamp_scope(ctx, orm_object) or directly assign orm_object.tenant_id = ctx.tenant_id and orm_object.organization_id = ctx.organization_id before the session flush.

**Step 6 — Include tenant+org in update() and delete().**
Do not rely on the primary key alone. Pass tenant_id and organization_id as extra_filters to update_with_version_check() or as explicit WHERE clauses in delete statements.

**Step 7 — Apply _organization_in_scope guard on list_for_organization methods.**
Before executing any query that accepts an explicit organization_id from the caller, call if not self._organization_in_scope(ctx, organization_id): return [] (or raise PermissionDeniedError for write paths).

**Step 8 — Write isolation tests.**
The repository's test module must include the two tests described in Section 21.11.

---

## 21.11 Mandatory Test Requirements

Every Category 1 repository test module MUST include the following tests. These are minimum requirements; additional tests for domain-specific behaviour are expected.

### Test T1 — Cross-tenant isolation

```python
def test_cross_tenant_isolation(session_factory, tenant_a_ctx, tenant_b_ctx):
    repo = SqlAlchemy{Entity}Repository(session_factory)

    # Create entity in Tenant A
    entity = build_{entity}(tenant_id=tenant_a_ctx.tenant_id, organization_id=tenant_a_ctx.organization_id)
    with tenant_a_ctx:
        repo.add(entity)

    # Attempt to read it in Tenant B context
    with tenant_b_ctx:
        result = repo.get(entity.id)

    assert result is None, "Entity created in Tenant A must not be visible in Tenant B"
```

### Test T2 — Cross-organization isolation within a tenant

```python
def test_cross_org_isolation(session_factory, tenant_ctx_org1, tenant_ctx_org2):
    repo = SqlAlchemy{Entity}Repository(session_factory)

    entity = build_{entity}(tenant_id=tenant_ctx_org1.tenant_id, organization_id=tenant_ctx_org1.organization_id)
    with tenant_ctx_org1:
        repo.add(entity)

    with tenant_ctx_org2:
        result = repo.get(entity.id)

    assert result is None, "Entity created in Org 1 must not be visible in Org 2 of the same tenant"
```

### Test T3 — Scope stamping on add()

```python
def test_add_stamps_scope(session_factory, tenant_ctx):
    repo = SqlAlchemy{Entity}Repository(session_factory)
    entity = build_{entity}_without_scope()

    with tenant_ctx:
        repo.add(entity)
        persisted = repo.get(entity.id)

    assert persisted.tenant_id == tenant_ctx.tenant_id
    assert persisted.organization_id == tenant_ctx.organization_id
```

### Test T4 — Update respects optimistic locking

This test is required only if the ORM model carries a version column.

```python
def test_update_version_conflict_raises(session_factory, tenant_ctx):
    repo = SqlAlchemy{Entity}Repository(session_factory)
    entity = build_{entity}()

    with tenant_ctx:
        repo.add(entity)
        stale = repo.get(entity.id)
        stale.version = stale.version - 1  # simulate stale read

    with pytest.raises(ConflictError):
        with tenant_ctx:
            repo.update(stale)
```

---

## 21.12 PR Governance Checklist

The following checklist must be completed by the author and verified by the reviewer before any PR that introduces or modifies a repository is merged.

```
Repository Governance Checklist

Classification
  [ ] Repository is classified as Category 1, 2, or 3 with a class-level comment
  [ ] If Category 3, PLATFORM-GLOBAL comment is present and no scoped base class is used
  [ ] If Category 2, written justification for absence of org scope is present

Inheritance
  [ ] Category 1 repo inherits from the correct module scoped support base class
  [ ] No Category 1 repo inherits from a Category 3 base (e.g., no plain object)

Read operations (Category 1 only)
  [ ] All get/list/count/exists methods include tenant_id WHERE
  [ ] All get/list/count/exists methods include organization_id WHERE
  [ ] list_for_organization methods include _organization_in_scope guard
  [ ] No method calls session.get(ORM, id) or session.execute(text(...))

Write operations (Category 1 only)
  [ ] add() stamps tenant_id and organization_id on the ORM object before flush
  [ ] update() passes tenant_id and organization_id in extra_filters or explicit WHERE
  [ ] delete() includes tenant_id and organization_id in WHERE

Pattern compliance
  [ ] _apply_scope (if used) does NOT use hasattr() — uses direct attribute access
  [ ] No list_all_unscoped(), get_unscoped(), or delete_all() methods exist
  [ ] No raw SQL string parameters anywhere in the class

Platform Admin operations (if any)
  [ ] Each cross-tenant method carries PLATFORM-ADMIN-OPERATION comment
  [ ] Each cross-tenant method is called only from a service that calls require_permission first

Naming
  [ ] Class name follows SqlAlchemy{Entity}Repository convention
  [ ] Methods follow {verb}_{entity}[_for_{parent}] convention

Tests
  [ ] T1 cross-tenant isolation test is present and passes
  [ ] T2 cross-org isolation test is present and passes
  [ ] T3 scope stamping test is present and passes
  [ ] T4 version conflict test is present (if ORM model has version column)
```

---

## 21.13 Known Deviations and Migration Backlog

The following known deviations from this standard exist in the current codebase. Each has a tracking reference and an assigned remediation phase.

| Deviation | Location | Severity | Remediation Phase |
|---|---|---|---|
| hasattr() in _apply_scope | All three module scoped support classes | HIGH — silent miss risk | Phase 5 (tenant isolation backlog) |
| ActivityRepository.add() does not stamp scope | src/core/platform/infrastructure/persistence/repositories/activity.py | HIGH — rows may be created with NULL tenant/org | Phase 5 |
| ActivityRepository.list_recent() unscoped by default | Same file | MEDIUM — cross-tenant data visible if caller omits filters | Phase 5 |
| Access repos use soft optional scoping — no scope if context is None | src/core/platform/infrastructure/persistence/repositories/access.py | HIGH — if context is None, all scoping is skipped | Phase 5 |
| SqlAlchemyUserRoleRepository.list_role_ids() filters only IS NULL — no tenant check | Same auth.py file | MEDIUM — all global roles visible across tenants (by design but undocumented) | Document in Phase 5, evaluate in Phase 6 |
| user_roles unique constraint is (user_id, role_id) only — missing organization_id | Database schema | HIGH — duplicate org-scoped role bindings possible | Phase 5 DB migration |

All deviations above are pre-existing and were present before this governance standard was adopted. New code MUST comply with this standard immediately. Existing code carrying these deviations MUST be remediated in Phase 5 of the tenant isolation roadmap.


---

# 22. DELIVERABLE 17 — AUDIT vs ACTIVITY vs DOMAIN EVENTS

## Definitions

### Activity
What: A record of meaningful business actions performed by users, visible to end users in a feed.
Purpose: User-facing "what happened recently" in a project, org, or entity.
Audience: End users — they see it in a timeline or activity feed.
Examples: "Alice created Task #23", "Bob updated the project budget", "Shipment received from Vendor X"
Retention: Short-term (30–90 days), soft-purge is acceptable.
Visibility: Scoped to entity (project, org) — user sees activity for entities they have access to.
Format: Human-readable message + actor + timestamp + entity link.
Storage: `activity_entries` table.

### Audit
What: An immutable, tamper-evident record of security-relevant and compliance-relevant events.
Purpose: Security review, compliance, incident investigation, regulatory reporting.
Audience: Auditors, security admins, compliance officers — NOT end users.
Examples: "User login failed (3rd attempt)", "Role assigned to user", "Permission changed", "Data exported", "User deactivated"
Retention: Long-term (7 years for SOX/PCI, depends on regulation); MUST NOT be deleted.
Visibility: Restricted to roles holding the `audit.read` permission.
Format: Structured — actor, operation, resource, outcome, severity, IP address, user agent, session ID, timestamp, field-level old/new value.
Storage: `audit_entries` table (APPEND-ONLY — no UPDATE or DELETE ever).

### Domain Events
What: Internal system signals that something changed in the domain model.
Purpose: Decouple producers from consumers; trigger side effects — UI cache invalidation, saga coordination, cross-module refresh.
Audience: Internal application services and QML controllers — NOT end users.
Examples: `auth_changed` (triggers session/UI refresh after a role assignment), `tasks_changed` (triggers Gantt/task-list reload), `inventory_items_changed` (triggers catalog UI refresh).
Retention: Ephemeral — in-memory only; lost on process exit.
Visibility: Internal (in-process) only.
Format: Typed `Signal[str]` carrying the mutated entity's ID; normalized into a `DomainChangeEvent` envelope on the aggregate bridge signals.
Storage: In-memory observer callbacks (no database table, no outbox).

---

## Current Implementation

### Domain Events

**Files:**
- `src/core/shared/events/signal.py` — generic thread-safe `Signal[T]` observer primitive with RLock and auto-pruning of stale Qt callbacks.
- `src/core/shared/events/domain_events.py` — `DomainChangeEvent` (frozen dataclass envelope) + `DomainEvents` (singleton hub); module-level instance `domain_events`.
- `src/core/shared/events/__init__.py` — re-exports both.

**Signal inventory (31 named `Signal[str]` fields):**

Project Management: `project_changed`, `tasks_changed`, `timesheet_periods_changed`, `costs_changed`, `resources_changed`, `baseline_changed`, `approvals_changed`, `register_changed`, `collaboration_changed`, `portfolio_changed`

Platform: `auth_changed`, `employees_changed`, `access_changed`, `modules_changed`

Shared masters: `organizations_changed`, `sites_changed`, `departments_changed`, `calendars_changed`, `documents_changed`, `parties_changed`

Inventory/Procurement (12 signals): `inventory_items_changed`, `inventory_item_categories_changed`, `inventory_storerooms_changed`, `inventory_balances_changed`, `inventory_reservations_changed`, `inventory_requisitions_changed`, `inventory_purchase_orders_changed`, `inventory_receipts_changed`, `inventory_maintenance_materials_changed`, `inventory_locations_changed`, `inventory_reorder_policies_changed`, `inventory_cycle_counts_changed`

Aggregate bridges: `shared_master_changed: Signal[DomainChangeEvent]` (fires only for category `shared_master`); `domain_changed: Signal[DomainChangeEvent]` (fires for every named signal).

**Bridge wiring:** `DomainEvents._BRIDGE_SPECS` defines 30 5-tuples `(signal_name, category, scope_code, entity_type, source_event)`. `__post_init__` wires each named signal to emit a `DomainChangeEvent` on `domain_changed` (and on `shared_master_changed` where applicable). Every `.emit(entity_id)` call therefore fans out automatically to `domain_changed`.

**Publishers (77 application service files):** Publish synchronously after a successful DB commit — commit-then-emit is the invariant. Key callers: task lifecycle, dependency, assignment commands; project lifecycle commands; resource commands; auth services (authentication, session, user admin, role assignment, MFA, password, registration, federated identity); approval service; timesheet periods and entries; employee support; inventory/procurement lifecycle services.

**Subscribers (production only):** All subscriptions go through one of four `WorkspaceControllerBase` classes (PM, Platform, Inventory, Maintenance) which call `_subscribe_domain_change(*entity_types)` or `_subscribe_domain_signal(signal, callback)`. These register on `domain_changed` with an entity-type filter, store subscription handles for auto-cleanup on QObject destruction, and debounce refresh via a `QTimer(interval=0)` single-shot that calls `self.refresh()` once the Qt event loop is idle.

No production code subscribes directly to a named signal. Tests connect directly via `domain_events.<signal>.connect(callback)`.

**Current gaps:**
- No event persistence — events are lost on process exit or crash occurring between commit and emit.
- No outbox/transactional publish guarantee — a crash between DB commit and `.emit()` silently drops the event.
- No event retry or replay.
- Maintenance module signals are absent from the named-signal inventory; maintenance services emit into PM/platform signals by overlap rather than dedicated signals.
- No typed event payload beyond the entity ID string — consumers cannot inspect what field changed without re-querying the database.

---

### Activity Log

**Files:**
- `src/core/platform/activity/domain/activity_entry.py` — `ActivityEntry` dataclass.
- `src/core/platform/infrastructure/persistence/orm/activity.py` — `ActivityEntryORM`, table `activity_entries`.
- `src/core/platform/activity/application/activity_service.py` — `ActivityService`.
- `src/core/platform/activity/contracts.py` — `ActivityRepository` ABC.
- `src/core/platform/infrastructure/persistence/repositories/activity.py` — concrete repository.
- `src/core/platform/infrastructure/persistence/mappers/activity.py` — ORM↔domain mapper.
- `src/core/shared/activity/activity_recorder.py` — `record_activity()` duck-typed helper.
- `src/api/desktop/platform/activity.py` — `PlatformActivityDesktopApi`.

**Table schema (`activity_entries`):**
`id`, `action` (e.g. `"project.create"`), `entity_type`, `entity_id`, `actor_id`, `actor_role`, `module`, `workspace_id`, `tenant_id` (FK tenants, NOT NULL), `organization_id` (FK organizations), `timestamp`, `type` (`info`/`warning`/`system`/`user`), `human_message`, `details_json`, `context_json`, `parent_entity_id`, `icon`, `color`, `visibility` (`public`/`workspace`/`private`).

Seven composite indexes: tenant+timestamp, org+timestamp, entity, workspace+timestamp, module+entity+id, actor+timestamp.

**Recording pattern:** `record_activity(owner, ...)` uses `getattr(owner, "_activity_service", None)` — silently no-ops if the service is not injected. `ActivityService.record()` resolves `actor_id` from `UserSessionContext.principal`, resolves `tenant_id`/`organization_id` from `TenantContextService`, adds the entry, and commits.

**Callers (43 application service files):** Task lifecycle (create/update/delete/status), project lifecycle, dependencies, assignments, resource commands, baselines, risk register, cost items, portfolio dependencies, inventory catalog, stock control, procurement/purchasing lifecycle, reservations, maintenance work orders/requests/assets/components/sensors/preventive plans.

**Desktop API:** `PlatformActivityDesktopApi` wraps `ActivityService.list_recent()` and serializes to `ActivityEntryDto`; exposed on the desktop runtime as `platform_activity`.

**Current gaps:**
- `list_recent()` does not filter by the `visibility` column — the field exists but is not enforced on the read path.
- No retention policy enforced in code or at DB level.
- No UI activity feed surface in QML (the API exists; no viewer widget was found).
- `_activity_service` is optional injection — recording silently skips in any service where it is not wired, creating coverage blind spots.

**Scheduling in-memory log (separate concern):** `src/ui_qml/modules/project_management/controllers/scheduling/activity_log_service.py` — a non-persisted, UI-only ring buffer (max 12 entries) used exclusively by the scheduling workspace controller. It is not related to `activity_entries` and should not be confused with the platform activity system.

---

### Audit Log

**Files:**
- `src/core/platform/audit/domain/audit_entry.py` — `AuditEntry` dataclass.
- `src/core/platform/infrastructure/persistence/orm/audit_entry.py` — `AuditEntryORM`, table `audit_entries`.
- `src/core/platform/audit/application/enterprise_audit_service.py` — `EnterpriseAuditService`.
- `src/core/platform/audit/contracts.py` — `AuditRepository` ABC.
- `src/core/platform/infrastructure/persistence/repositories/audit_entry.py` — concrete repository.
- `src/core/platform/infrastructure/persistence/mappers/audit_entry.py` — ORM↔domain mapper.
- `src/core/shared/audit/audit_recorder.py` — `record_audit_entry()` duck-typed helper.
- `src/core/platform/auth/application/audit_recorder.py` — auth-specific `record_auth_event()`.

**Table schema (`audit_entries`):**
`id`, `timestamp`, `actor_id`, `actor_type` (`user`/`system`/`api`), `actor_username`, `actor_ip`, `actor_user_agent`, `entity_type`, `entity_id`, `entity_parent_id`, `operation` (e.g. `"create"`, `"update"`, `"delete"`, `"login"`, `"permission_change"`), `field`, `old_value`, `new_value`, `module`, `tenant_id` (FK), `organization_id` (FK), `workspace_id`, `request_id`, `source` (`api`/`auth`/`system`), `severity` (`low`/`medium`/`high`), `compliance_tag` (`none`/`SOC2`/`access-control`/...), `metadata_json`.

Seven composite indexes: tenant+timestamp, org+timestamp, entity, actor+timestamp, operation+timestamp, compliance+timestamp, severity+timestamp.

The migration comment states explicitly: **"This table is append-only — no UPDATE or DELETE operations should ever be issued against it."**

**Recording pattern:** Identical duck-typed pattern to activity — `record_audit_entry(owner, ...)` uses `getattr(owner, "_enterprise_audit_service", None)`. `EnterpriseAuditService.record()` resolves actor, org, and tenant from session/context; creates an `AuditEntry`; adds to repo; optionally commits (default `commit=False`; auth recorder overrides to `commit=True` for immediate flush). Auth events use `record_auth_event()` which computes severity via `_severity_for_action()`.

**Callers (63 files):** Auth events (login, logout, failed_login, MFA) with `compliance_tag="access-control"`; user management (create, deactivate, set_active) with `severity=medium`, `compliance_tag=SOC2`; role/permission changes (role create/update/delete, permission add, user role assignment); access control (scope grant/revoke); approval operations; timesheet state transitions (submit, approve, reject, recall); module entitlement changes; business data mutations in PM, inventory, and maintenance (these call both `record_audit_entry` and `record_activity` in the same service method).

**Permission to read:** `EnterpriseAuditService.list_recent()` calls `require_permission("audit.read")` — access is explicitly gated. No end-user-facing API exposes audit entries.

**Current gaps:**
- Append-only is stated in a migration comment but is NOT enforced at the database level (no DB trigger, no REVOKE of UPDATE/DELETE on the table). Any code path with a writable session could issue an UPDATE.
- No audit retention policy enforced in code or schema. There is no archiving or partition strategy.
- No QML AuditLog viewer has been built. The service and permission gate exist; the UI surface does not.
- `tenant_id` and `organization_id` are both on the table but platform-level events (e.g., tenant creation) have no organization context — `organization_id` would be NULL for those events, which is acceptable but unspecified in current policy.
- The `compliance_tag` enum is a freeform string in the domain model; no canonical list is enforced in the application layer beyond what individual callers pass.

**Legacy `audit_logs` table:** The prior single-table audit system has been fully migrated out. Non-security rows were backfilled to `activity_entries` (migration `u6v7w8x9y0z1`); security rows were backfilled to `audit_entries` with severity and compliance_tag mappings (migration `v7w8x9y0z1a2`). No application code writes to `audit_logs` today — it is referenced only in migration files.

---

## Comparison Matrix

| Dimension | Domain Events | Activity (`activity_entries`) | Audit (`audit_entries`) |
|---|---|---|---|
| Audience | Internal services / QML controllers | End users | Auditors / security admins |
| Visibility | In-process only | User-scoped (entity/workspace/org) | `audit.read` permission required |
| Mutability | Ephemeral — no persistence | Mutable (no append-only enforcement) | Explicitly append-only |
| Retention | None — lost on process exit | No policy enforced | No policy enforced (should be 7 years) |
| Triggering | Every domain write (commit-then-emit) | User-initiated business operations (43 services) | Security + compliance events (63 services) |
| Payload | Entity ID string only | human_message + actor + details JSON | operation + field + old_value + new_value + actor IP/UA |
| Actor tracking | None | actor_id, actor_role | actor_id + actor_username + actor_ip + actor_user_agent |
| Field-level diffs | No | No | Yes (`field`, `old_value`, `new_value`) |
| Compliance metadata | No | No | `severity` (low/medium/high) + `compliance_tag` (SOC2, access-control, …) |
| Storage | In-memory (Signal callbacks) | `activity_entries` DB table | `audit_entries` DB table |
| Scope | Process-internal | tenant_id + organization_id + workspace_id | tenant_id + organization_id |
| Purpose | UI cache invalidation; cross-service decoupling | "What happened" feed for users | Forensics; compliance reporting; incident investigation |
| Read permission | None (in-process) | No explicit service-layer permission check | `audit.read` enforced in service |
| Append-only enforced | N/A | No | Comment only — not DB-enforced |

---

## Gap Analysis

### Gap 1 — Domain Events: No transactional publish guarantee
The commit-then-emit pattern is correct in intent but not atomic. If the process crashes between the DB commit and the in-memory `.emit()` call, the event is silently lost. For the current desktop deployment this is acceptable because the user session is local. For any multi-process or server deployment this becomes a reliability defect. The fix is an outbox table (`domain_events_outbox`) written in the same transaction as the business row, with a background relay that emits and marks sent.

### Gap 2 — Domain Events: No typed payloads
Every named signal carries only a `str` entity ID. Consumers cannot determine what changed without issuing a follow-up database query. This forces unnecessary re-reads and prevents consumers from doing conditional logic based on the change type. Typed frozen dataclasses (e.g., `TaskStatusChanged(task_id, project_id, old_status, new_status)`) would eliminate this.

### Gap 3 — Domain Events: Maintenance module has no dedicated signals
The maintenance module emits into existing PM and platform signals rather than owning distinct signals. This blurs categorical boundaries and may cause unintended UI refreshes in unrelated controllers.

### Gap 4 — Activity: `visibility` column not enforced on read
`ActivityRepository.list_recent()` does not filter by the `visibility` column. The `public`/`workspace`/`private` distinction is written but never enforced on queries. Until this is corrected, any caller of `list_recent()` receives all entries regardless of visibility intent.

### Gap 5 — Activity: No retention policy
There is no scheduled purge, partition rotation, or archiving job for `activity_entries`. In production this table will grow without bound. A rolling 90-day retention window with configurable override per organization is the standard approach.

### Gap 6 — Activity: Optional injection creates silent coverage gaps
`record_activity()` silently skips if `_activity_service` is not injected into a service. This is a deliberate fault-tolerance design, but it means omitting the injection in a new service leaves a silent coverage gap with no warning. A lint rule or base-class enforcement pattern should flag services that write to the domain but do not wire `_activity_service`.

### Gap 7 — Audit: Append-only not enforced at DB level
The migration comment declares append-only intent, but no database-level control enforces it. Any SQLAlchemy session with write access to `audit_entries` can issue an UPDATE or DELETE. Enforcement requires one or more of: a DB trigger that raises on UPDATE/DELETE; REVOKE of UPDATE/DELETE privileges from the application DB user; a row-level security policy. At minimum, `EnterpriseAuditService` should assert no update path exists.

### Gap 8 — Audit: No retention or archiving
`audit_entries` has no time-based retention strategy. SOC 2 Type II and most enterprise compliance frameworks require audit records to be retained for a minimum of one year (commonly three to seven years). A partitioning scheme (by tenant + month) or a cold-storage archiving pipeline should be designed before production.

### Gap 9 — Audit: No QML viewer
The service layer, permission gate, and structured schema are in place. No QML AuditLog screen exists. Auditors and security admins have no in-application surface to query audit entries. This is a blocker for any compliance audit.

### Gap 10 — Audit: `compliance_tag` is an unvalidated freeform string
Individual callers pass arbitrary strings. There is no canonical enum, no validation in the domain model, and no index-level enforcement. Inconsistent tagging degrades the value of compliance queries. A `ComplianceTag` enum should be defined and enforced in `AuditEntry`.

### Gap 11 — Cross-system: No event definitions for tenant and platform lifecycle
No domain events, activity entries, or audit entries are defined for: `TenantCreated`, `TenantSuspended`, `OrganizationCreated`, `OrganizationDeactivated`. These are the highest-severity events in a multi-tenant system and should be the first entries in all three systems.

### Gap 12 — Cross-system: MFA and password events are structurally incomplete
MFA is non-functional (UI never collects the TOTP code). Password hashing now uses canonical Argon2id. Auth audit events for MFA (`mfa.enabled`, `mfa.disabled`, `mfa.challenge_failed`) exist as code paths but produce no verified audit trail because the flows are never exercised. When MFA is fixed, the audit path must be validated end-to-end.

---

## Recommended Architecture

### Audit Log — Harden existing system
1. Enforce append-only at DB level: add a BEFORE UPDATE / BEFORE DELETE trigger on `audit_entries` that raises an exception unconditionally; revoke UPDATE and DELETE privileges from the application DB role on this table.
2. Define `ComplianceTag` as a Python `StrEnum` and validate in `AuditEntry.__post_init__`; update all callers to use the enum.
3. Design a retention and archiving strategy: partition `audit_entries` by tenant + year-month; move partitions older than the retention threshold to cold storage; never DELETE from the hot table.
4. Build an `AuditLogViewer` QML component gated behind the `audit.read` permission. Expose filter controls for: date range, severity, compliance_tag, actor, entity_type, operation.
5. Add platform-level audit entries (no `organization_id`) for `TenantCreated`, `TenantSuspended`, `UserCreated` (cross-tenant), and module entitlement grant/revoke.

### Activity Feed — Harden existing system
1. Enforce `visibility` filtering in `ActivityRepository.list_recent()`: add a `visibility` parameter (default `["workspace", "public"]`) and apply a WHERE clause.
2. Implement a retention job: delete `activity_entries` rows older than a configurable threshold (default 90 days) per tenant; run as a scheduled platform maintenance task.
3. Build an `ActivityFeed` QML component for the project workspace and org dashboard, consuming `PlatformActivityDesktopApi`.
4. Establish a convention: every application service that calls `record_audit_entry` for a business operation must also call `record_activity` for the human-readable counterpart. Document this as a coding standard and add a test fixture that validates both recorders are wired in new services.

### Domain Events — Extend for reliability and expressiveness
1. For the current desktop deployment: no outbox is required. The synchronous commit-then-emit pattern is acceptable.
2. For any future server deployment: introduce an `events_outbox` table written in the same transaction as the business row. A background relay reads unprocessed rows, emits events, and marks them sent. This gives at-least-once delivery.
3. Add dedicated signals for the maintenance module to remove cross-module signal sharing.
4. Define typed event dataclasses where consumers need field-level change information, rather than requiring a follow-up DB query. Start with high-frequency cases: `TaskStatusChanged`, `ProjectStatusChanged`, `RoleAssigned`, `TimeEntrySubmitted`.
5. The following events are absent and should be added across all three systems as a coordinated set:

| Event | Domain Signal | Activity Entry | Audit Entry |
|---|---|---|---|
| TenantCreated | organizations_changed | "tenant.create" | operation="create", compliance_tag="SOC2", severity=high |
| TenantSuspended | organizations_changed | "tenant.suspend" | operation="update", compliance_tag="SOC2", severity=high |
| OrganizationCreated | organizations_changed | "organization.create" | operation="create", compliance_tag="SOC2", severity=medium |
| UserCreated | auth_changed | "user.create" | operation="create", compliance_tag="SOC2", severity=medium |
| UserDeactivated | auth_changed | "user.deactivate" | operation="update", compliance_tag="SOC2", severity=medium |
| RoleAssigned | auth_changed | "user.role.assign" | operation="permission_change", compliance_tag="access-control", severity=medium |
| MFAEnabled | auth_changed | "mfa.enable" | operation="update", compliance_tag="access-control", severity=medium |
| ModuleEntitlementChanged | modules_changed | "module_entitlement.update" | operation="update", compliance_tag="SOC2", severity=medium |
| ProjectCreated | project_changed | "project.create" | operation="create", compliance_tag="none", severity=low |
| ProjectArchived | project_changed | "project.archive" | operation="update", compliance_tag="none", severity=low |
| TimesheetApproved | timesheet_periods_changed | "timesheet.approve" | operation="update", compliance_tag="none", severity=low |
| WorkOrderCompleted | (add maintenance_changed) | "work_order.complete" | operation="update", compliance_tag="none", severity=low |
| PurchaseOrderApproved | approvals_changed | "purchase_order.approve" | operation="update", compliance_tag="none", severity=low |

---

# 23. DELIVERABLE 18 — PLATFORM GOVERNANCE MODEL

---

## 23.1 Overview

This deliverable defines the authoritative governance model for the platform: which administrative roles exist, what each role can do, the scope boundaries each role operates within, the hierarchy of trust between roles, and the gaps between this model and the current codebase state.

The governance model covers five administrative levels. Each level is strictly more restricted than the level above it, and no upward escalation is possible through any permission path.

---

## 23.2 What Platform Admin Can Do

**Scope:** Global — full access to all tenants, all organizations, all data  
**Required role:** `platform_admin` (NEW — distinct from the current `admin` role)  
**Required permission:** `platform.admin` (currently dead code: present in no `DEFAULT_PERMISSIONS` seed; must be added and seeded)

### Responsibilities

| Responsibility | Notes |
|---|---|
| Create / manage / suspend / delete tenants | Full CRUD on the `tenants` table |
| View all tenants and their operational stats | Requires cross-tenant aggregate query path |
| Access any tenant's admin console for support | Cross-tenant read; every access must be audit-logged |
| Manage platform-level configuration | Feature flags, module catalog entries, license capacity |
| View platform-level audit log (`platform_events`) | Distinct from per-tenant audit log |
| Manage platform-global roles and permissions | Roles and permissions tables have no `tenant_id` |
| Bootstrap new tenant admins | Seed the first `tenant_admin` user for a new tenant |
| Emergency (break-glass) access to any tenant's data | Must produce a mandatory approval request (future: 4-eyes) |
| Manage the module catalog | Add new `module_code` entries to the license catalog |
| Manage tenant license records (`tenant_module_licenses`) | Grant or revoke module capacity per tenant |

### Security Boundaries

- Platform Admin **cannot modify business data** (projects, tasks, inventory, timesheets) except in explicit break-glass scenarios — access to business data is read-only by default.
- Every Platform Admin action must be recorded in `platform_events` with `severity = ELEVATED`.
- Platform Admin sessions **require MFA** — MFA must be enforced at session creation, not just at login UI. The current MFA implementation is non-functional (UI never collects the TOTP code); this must be resolved before `platform_admin` role can be safely issued.
- Break-glass access must be explicitly requested and recorded; it is not inherited from the `platform_admin` role automatically.
- `platform_admin` role **cannot coexist** with any business role. The SoD enforcer must add this incompatibility rule.

### Current State

The existing `admin` role is seeded globally via `DEFAULT_ROLE_PERMISSIONS` and receives all 56 permissions via `set(DEFAULT_PERMISSIONS.keys())`. It is not a platform admin; it is a tenant-unscoped superuser that bypasses all isolation checks in `TenantContextService._can_access()` (line 181: `if "admin" in getattr(principal, "role_names", frozenset())`). The `platform.admin` permission code does not appear in `DEFAULT_PERMISSIONS` and is never seeded. The distinction between `admin` (current, business superuser) and `platform_admin` (new, infrastructure operator) must be formalized.

---

## 23.3 What Tenant Admin Can Do

**Scope:** Tenant-scoped — full access within their tenant; zero access to any other tenant  
**Required role:** `tenant_admin` (NEW)  
**Required permissions:** `tenant.manage` (new), `auth.manage`, `settings.manage`

### Responsibilities

| Responsibility | Notes |
|---|---|
| Create / manage organizations within their tenant | Scoped to the tenant's `tenant_id` |
| Configure module entitlements for their orgs | Subject to the tenant's licensed module capacity |
| Invite and register users to their tenant | Creates `user_tenants` row and initial `scoped_access_grants` |
| Assign tenant-level roles to users | Can assign any role except `platform_admin` |
| View tenant-level audit log | Filtered to their tenant's `tenant_id` |
| Manage tenant-level settings | Timezone defaults, base currency, branding |
| Create `org_admin` users within their orgs | Grants `org_admin` role with org-scoped grant |

### Security Boundaries

- Cannot modify platform-global roles or permissions — those tables are writable only by `platform_admin`.
- Cannot access data belonging to another tenant — all queries must carry `tenant_id` predicate.
- Cannot modify their own tenant's license capacity — that is `platform_admin`-only.
- Cannot delete the tenant itself — `platform_admin` only.
- `tenant_admin` in tenant A receiving a `scoped_access_grants` row for tenant B is a critical bug that `set_active_tenant()` currently does not prevent. The missing `user_tenants` membership check (identified in the audit as a critical bug) must be enforced here.

### Current State

No `tenant_admin` role exists. No `tenant.manage` permission exists. The `user_roles` table has a uniqueness constraint on `(user_id, role_id)` only — there is no `tenant_id` column on `user_roles`, meaning any role assignment is implicitly global. Tenant-scoped role assignment is structurally impossible until `user_roles` carries `tenant_id`.

---

## 23.4 What Organization Admin Can Do

**Scope:** Org-scoped — full access within their organization  
**Required role:** `org_admin` (NEW)  
**Required permissions:** `settings.manage` (org-scoped), `auth.manage` (org-scoped), `employee.manage`

### Responsibilities

| Responsibility | Notes |
|---|---|
| Create / manage sites within their org | `sites` table scoped to `organization_id` |
| Create / manage departments within their org | `departments` table scoped to `organization_id` |
| Create / manage employees within their org | Direct `organization_id` column needed on `employees` table (currently derived transitively through `site_id`) |
| Assign org-scoped roles to users in their org | Via `scoped_access_grants(scope_type="organization", scope_id=org_id)` |
| Configure org-level calendar and shift patterns | Calendar and shift services, scoped to org |
| View org-level audit log | Filtered to their `organization_id` |
| Configure module settings for their org | `organization_module_entitlements` within licensed capacity |

### Security Boundaries

- Cannot create new organizations — that is `tenant_admin` only.
- Cannot access data from other organizations within the same tenant — the query layer must enforce `organization_id` predicate even within a single tenant.
- Cannot escalate to `tenant_admin` through any permission path.
- Cannot assign roles beyond org scope — `scoped_access_grants` rows created by an `org_admin` must be validated to ensure `scope_type` is `organization` or below, never `tenant`.

### Current State

No `org_admin` role exists. The `employees` table has no `organization_id` column; org scope for employees is derived transitively through `site_id`, which means an employee without a site is entirely unscoped. This must be corrected before org-admin employee management is safe.

---

## 23.5 What Site Admin Can Do

**Scope:** Site-scoped — access limited to their specific site  
**Required role:** `site_admin` (NEW)  
**Required access grant:** `scoped_access_grants(scope_type="site", scope_id=<site_id>)`  
**Required permissions:** `employee.manage` (site-filtered), `resource.manage` (site-filtered), `timesheet.approve`

### Responsibilities

| Responsibility | Notes |
|---|---|
| Manage employees at their site | Queries filtered by `site_id` |
| Manage departments at their site | Department records scoped to their site |
| Approve timesheets for site employees | Timesheet rows where employee's `site_id` matches |
| Configure site-level calendar overrides | Site-specific working day and holiday rules |
| View reports for their site | Filtered by `site_id` throughout |

### Security Boundaries

- Cannot see employees, timesheets, or data from other sites — the repository `_apply_scope()` must filter by `site_id` when the grant is site-scoped.
- Cannot create new sites — `org_admin` only.
- Cannot modify org-level settings.

### Current State

No `site_admin` role exists. `scoped_access_grants` supports `scope_type` as a freeform string; site-scoped grants are technically representable but no enforcement code reads them at the repository layer for site-level filtering. The `_apply_scope()` method uses `hasattr()` runtime introspection for `tenant_id` and `organization_id`; it does not handle `site_id` scoping.

---

## 23.6 What Department Manager Can Do

**Scope:** Department-scoped — access limited to their specific department  
**Required role:** `department_manager` (NEW)  
**Required access grant:** `scoped_access_grants(scope_type="department", scope_id=<dept_id>)`  
**Required permissions:** `employee.read` (dept-filtered), `timesheet.approve` (dept-filtered), `resource.read`

### Responsibilities

| Responsibility | Notes |
|---|---|
| Approve timesheets for their department's employees | Filtered by `department_id` on the employee |
| View employees in their department | Read-only directory filtered by `department_id` |
| View resource allocation for their department | `resource.read` within dept scope |
| View department-level reports | Aggregated and filtered to their department |

### Security Boundaries

- Read-only on all entities except timesheet approval — cannot create, edit, or delete any records.
- Cannot modify employee records (timesheet approval only).
- Cannot see employees or data from other departments.

### Current State

No `department_manager` role exists. Department-scoped filtering is not implemented at the repository layer. Timesheet approval is currently controlled by `timesheet.approve` as a flat permission with no department predicate.

---

## 23.7 Administrative Hierarchy

```
Platform Admin (Global)
    │
    ├─ Tenant Admin (Tenant-scoped)
    │       │
    │       ├─ Organization Admin (Org-scoped)
    │       │       │
    │       │       ├─ Site Admin (Site-scoped)
    │       │       │       │
    │       │       │       └─ Department Manager (Dept-scoped)
    │       │       │
    │       │       └─ Project Manager (Project-scoped via ProjectMembership)
    │       │
    │       └─ (cross-org read: Tenant Admin can view all orgs in their tenant)
    │
    └─ (cross-tenant read: Platform Admin can access all tenants)
```

Each level is strictly contained within its parent scope. No level can acquire the permissions of its parent through any combination of grants, role assignments, or `scoped_access_grants` rows. The `admin` bypass in `TenantContextService._can_access()` must be narrowed so it applies only to `platform_admin`, not to the general-purpose `admin` role.

---

## 23.8 Cross-Tenant Access Rules

| Rule | Statement |
|---|---|
| Rule 1 | No user below Platform Admin can access another tenant's data. The missing `user_tenants` membership check in `set_active_tenant()` is a critical bug that must be fixed. |
| Rule 2 | Every Platform Admin cross-tenant access must produce an audit log entry in `platform_events` with `actor_id`, `target_tenant_id`, `action`, and `severity = ELEVATED`. |
| Rule 3 | Tenant Admin cannot escalate to Platform Admin through any permission path. `platform_admin` is seeded by system bootstrap only; there is no API path for any user to assign it to themselves or another user. |
| Rule 4 | There is no managed-services hierarchy where one tenant can read another's data. Each tenant is an independent isolation boundary. |
| Rule 5 | Emergency break-glass access by Platform Admin is explicit and recorded; it is never inherited from role membership alone. |

---

## 23.9 Cross-Organization Access Rules

| Rule | Statement |
|---|---|
| Rule 1 | No user below Tenant Admin can access another org's data within the same tenant. Repository-level `organization_id` filtering must be enforced even within a single tenant. |
| Rule 2 | Tenant Admin can view all organizations within their tenant for administrative purposes. This access must still be audit-logged. |
| Rule 3 | Org Admin cannot escalate to Tenant Admin through any permission path. |
| Rule 4 | Project Managers with access to cross-org projects see only data covered by their explicit `ProjectMembership` rows; there is no implicit cross-org data access from project membership. |

---

## 23.10 Escalation Paths

| From | To | Mechanism | Notes |
|---|---|---|---|
| Department Manager | Site Admin | Site Admin explicitly grants elevated `scoped_access_grants` | Requires Site Admin or Org Admin action |
| Site Admin | Org Admin | Org Admin or Tenant Admin grants `org_admin` role | Cannot self-escalate |
| Org Admin | Tenant Admin | Tenant Admin or Platform Admin grants `tenant_admin` role | Cannot self-escalate |
| Tenant Admin | Platform Admin | CANNOT escalate | `platform_admin` is system-seeded only; no API path exists |

---

## 23.11 Separation of Duties at the Administrative Level

The current `SeparationOfDutiesPolicy` in `src/core/platform/auth/sod.py` defines two rules: `(approval.request, approval.decide)` conflict and `(access.manage, security.manage)` conflict. The `enforce_separation_of_duties()` function in `sod_enforcer.py` (line 18) short-circuits for `admin` role, making SoD entirely bypassable for the current superuser. The following rules must be added when the new administrative roles are introduced.

| Pairing | Verdict | Rationale |
|---|---|---|
| `platform_admin` + `tenant_admin` | INCOMPATIBLE | Platform operator role must not carry tenant business access |
| `platform_admin` + any business role | INCOMPATIBLE | Platform operations are strictly separated from business data management |
| `tenant_admin` + `finance_controller` | REVIEW | Billing data conflict — tenant admin should not also control financial records within their tenant; review per deployment policy |
| `org_admin` + `auditor` | COMPATIBLE | Org admin can be audited by an auditor role; the two roles do not conflict |
| `org_admin` + `access_admin` | REVIEW | Self-grant risk: `access_admin` holds `access.manage` which can expand the holder's own scope; must be monitored |
| `site_admin` + `payroll_manager` | REVIEW | Site admin with payroll approval creates conflict over site employee pay records |

The SoD bypass for `admin` (line 18 in `sod_enforcer.py`: `if "admin" in normalized: return`) must be removed or narrowed. When `platform_admin` is introduced, the bypass must apply only to `platform_admin` in contexts where platform-level operations are explicitly exempted — it must not apply in tenant-scoped role assignment flows.

---

## 23.12 Current Architecture vs. Governance Model — Gap Table

| Governance Concept | Exists in Code? | Specific Gap |
|---|---|---|
| `platform_admin` role | NO (partial: `admin` is global but not platform-distinct) | Add `platform_admin` to `DEFAULT_ROLE_PERMISSIONS`; seed `platform.admin` permission in `DEFAULT_PERMISSIONS` |
| `tenant_admin` role | NO | Add role, add `tenant.manage` permission, add `tenant_id` column to `user_roles` |
| `org_admin` role | NO | Add role, add org-scoped grant enforcement |
| `site_admin` role | NO | Add role, add site-scoped `_apply_scope()` path in repositories |
| `department_manager` role | NO | Add role, add dept-scoped filtering at timesheet and employee repositories |
| `user_tenants` membership table | NO | `set_active_tenant()` does no membership check; any user can switch to any tenant |
| `platform_events` audit table | NO | All admin actions go to the same audit log with no elevated severity path |
| Administrative hierarchy enforcement | PARTIAL | SoD rules exist but `admin` bypasses them entirely (line 18 `sod_enforcer.py`) |
| Cross-tenant access control | NO | `_can_access()` checks org scope but not tenant membership |
| MFA enforcement for elevated roles | NO | MFA infrastructure exists (`auth/mfa.py`) but UI never collects TOTP; non-functional |
| Break-glass approval workflow | NO | No approval mechanism for emergency access |
| `platform.admin` permission seeded | NO | Code references it in `is_platform_admin()` but it is absent from `DEFAULT_PERMISSIONS` |

---

## 23.13 Implementation Sequence

The following sequence minimizes regression risk given the current live codebase.

**Step 1 — Permission layer (no behavior change, additive only)**  
Add `platform.admin`, `tenant.manage` to `DEFAULT_PERMISSIONS` in `src/core/platform/auth/policy.py`. This is non-breaking; no code reads these codes yet.

**Step 2 — Role definitions (additive only)**  
Add `platform_admin`, `tenant_admin`, `org_admin`, `site_admin`, `department_manager` entries to `DEFAULT_ROLE_PERMISSIONS`. Define their permission sets. Run `ensure_default_roles()` and `ensure_role_permissions()` via the existing seed path.

**Step 3 — SoD rules (additive — new rules, remove `admin` bypass)**  
Add `platform_admin` incompatibility rules to `default_separation_of_duties_rules()`. Remove the `if "admin" in normalized: return` short-circuit in `enforce_separation_of_duties()` — replace with a narrower `if "platform_admin" in normalized and is_platform_context: return` guard if needed.

**Step 4 — Tenant membership check**  
Create `user_tenants(user_id, tenant_id, granted_at, granted_by)` table. Add membership check to `TenantContextService.set_active_tenant()` before writing to session.

**Step 5 — `user_roles` tenant scoping**  
Add `tenant_id` column (nullable initially, then NOT NULL for non-platform roles) to `user_roles`. Update the uniqueness constraint from `(user_id, role_id)` to `(user_id, role_id, tenant_id)`.

**Step 6 — Site and department scoping in `_apply_scope()`**  
Extend repository scope application to handle `scope_type = "site"` and `scope_type = "department"` grants from `scoped_access_grants`. Replace `hasattr()` introspection with explicit column registration.

**Step 7 — `platform_events` audit table**  
Add table, wire into `TenantContextService` cross-tenant access paths and all `platform_admin` service methods.

**Step 8 — MFA enforcement for `platform_admin` sessions**  
Fix the TOTP collection gap in the authentication UI before issuing any `platform_admin` grants.


---

# 24. DELIVERABLE 19 — MIGRATION READINESS REPORT

## Overview

This report evaluates readiness to execute each major architectural change identified in this review. For each change: complexity, risk, dependencies, migration requirements, and recommended execution order.

## 1. user_tenants Table

**Complexity:** HIGH
**Risk:** CRITICAL (must be done carefully — changes core security model)

**Dependencies:**
- Schema migration: new table `user_tenants(id, user_id, tenant_id, is_active, tenant_role, invited_at, joined_at)`
- `TenantContextService.set_active_tenant()` — add `_can_access_tenant()` check
- `AuthService.register_user()` — accept `tenant_id` param, auto-create `user_tenants` row
- `SqlAlchemyUserRepository` — add `list_for_tenant()` method
- Bootstrap admin — exempt from `user_tenants` check via `"admin"` role bypass
- Username uniqueness — MUST be resolved concurrently (see section 2)
- Desktop mode fallback — if user has exactly one tenant, auto-assign without prompt

**Migration requirements:**
- `CREATE TABLE user_tenants`
- `INSERT INTO user_tenants` for all existing users with the default tenant (`get_default()`)
- Data validation: every existing user must have at least one `user_tenants` row
- No downtime migration (additive table)

**Execution order:** Priority 1 (foundation for all other tenant isolation work)

---

## 2. Username Per-Tenant Uniqueness

**Complexity:** MEDIUM
**Risk:** HIGH (changes fundamental user identity model)

**Dependencies:**
- Depends on: `user_tenants` table
- Schema change: `DROP UNIQUE` constraint on `users.username`, `ADD UNIQUE` on `(username, tenant_id)` — but `users` has no `tenant_id` column
- Preferred approach: username stays globally unique; use email as per-tenant invite key
- Alternative: add `users.email` and make username local to tenant (major change)
- Requires: `email` field on `users` table
- Requires: registration flow to use email for invite matching

**Migration requirements:**
- `ALTER TABLE users ADD COLUMN email VARCHAR NULLABLE`
- Backfill email from username if username is email-format
- No existing data conflict (usernames remain globally unique for now, per-tenant in future)

**Execution order:** Priority 2 (alongside or after `user_tenants`)

---

## 3. tenant_admin Role

**Complexity:** LOW
**Risk:** LOW

**Dependencies:**
- New permission codes: `tenant.create`, `tenant.manage`, `tenant.read`, `org.create`
- `DEFAULT_PERMISSIONS` update in `auth/policy.py`
- `DEFAULT_ROLE_PERMISSIONS` update — add `tenant_admin` role with its permission set
- SoD rules: `tenant_admin` + `finance_controller` (review), `tenant_admin` + `platform_admin` (incompatible)
- `bootstrap_service.py` — seed new role in `ensure_default_roles()`
- No schema migration needed (roles table is code-seeded)

**Migration requirements:**
- Data migration: `INSERT INTO roles (name="tenant_admin", ...) IF NOT EXISTS`
- `INSERT INTO role_permissions` for all `tenant_admin` permission codes
- No existing data affected

**Execution order:** Priority 3 (needed for tenant onboarding workflow)

---

## 4. org_admin Role

**Complexity:** LOW
**Risk:** LOW

**Dependencies:**
- Same pattern as `tenant_admin`
- New permission codes: `org.manage` (if not existing), `employee.manage`
- `user_roles` unique constraint fix must precede (to allow org-scoped `org_admin` binding)
- `org_admin` role binding must be `organization_id`-scoped in `user_roles`

**Migration requirements:**
- Same as `tenant_admin` (`INSERT roles` + `role_permissions`)
- Fix `user_roles` unique constraint: `ALTER TABLE user_roles DROP CONSTRAINT unique_user_role`, `ADD CONSTRAINT unique_user_role_org UNIQUE (user_id, role_id, organization_id)`

**Execution order:** Priority 4 (after `user_roles` constraint fix)

---

## 5. user_roles Unique Constraint Fix

**Complexity:** LOW
**Risk:** MEDIUM (may surface existing duplicate data)

**Dependencies:**
- Need to check for existing `(user_id, role_id)` duplicates with different `organization_id` values
- If duplicates exist: they are valid multi-org bindings that were previously blocked — retain all rows
- If no duplicates: simple constraint change

**Migration requirements:**
- Check for existing duplicates: `SELECT user_id, role_id, COUNT(*) FROM user_roles GROUP BY user_id, role_id HAVING COUNT(*) > 1`
- `ALTER TABLE user_roles DROP CONSTRAINT user_roles_user_id_role_id_key` (or equivalent)
- `ALTER TABLE user_roles ADD CONSTRAINT uq_user_role_org UNIQUE (user_id, role_id, organization_id NULLS NOT DISTINCT)`
- Note: `NULLS NOT DISTINCT` is PostgreSQL 15+ only — for SQLite, a partial unique index is required

**Execution order:** Priority 1a (low risk, high impact — unblocks `org_admin` role)

---

## 6. _deactivate_other_organizations() Fix

**Complexity:** LOW
**Risk:** LOW (one-line code fix)

**Dependencies:** None
**Migration requirements:** None (pure code change)
**Change:** Add `tenant_id` filter to the deactivation query

**Execution order:** Priority 1 CRITICAL (one-line fix — do this immediately)

---

## 7. Fix get_active() and list_all() on Organization Repository

**Complexity:** LOW
**Risk:** LOW

**Dependencies:** None (code change only)
**Migration requirements:** None

**Execution order:** Priority 1 alongside `_deactivate_other_organizations()` fix

---

## 8. site_admin + department_manager Roles

**Complexity:** MEDIUM
**Risk:** LOW

**Dependencies:**
- `user_roles` constraint fix (to allow site-scoped and dept-scoped role bindings with `organization_id`)
- `ScopedAccessGrant` already supports arbitrary `scope_type` — no schema change needed
- New permission codes: `site.manage`, `site.admin`, `department.manage`, `department.admin`
- New repository methods: `list_for_site()`, `list_for_department()` on employee and timesheet repos
- `AccessControlService.assign_site_grant()` and `assign_dept_grant()` methods

**Migration requirements:**
- `INSERT roles` + `role_permissions` (same pattern as `tenant_admin` / `org_admin`)

**Execution order:** Priority 5 (after core tenant/org fixes)

---

## 9. Activity Service

**Complexity:** MEDIUM
**Risk:** LOW

**Dependencies:**
- New table: `activity_entries(id, tenant_id, org_id, entity_type, entity_id, actor_user_id, action_code, message, created_at)`
- Domain events must be expanded (new event types)
- `ActivityService` subscribes to domain events
- QML `ActivityFeed` component

**Migration requirements:**
- `CREATE TABLE activity_entries`
- Backfill: not needed (activity is forward-looking only)

**Execution order:** Priority 6 (nice-to-have, not blocking)

---

## 10. Audit Redesign

**Complexity:** MEDIUM
**Risk:** MEDIUM (changes compliance-critical table)

**Dependencies:**
- Current `audit_logs` is org-scoped — needs platform-level events
- New table: `platform_events(id, operation, actor_user_id, tenant_id, resource_type, resource_id, outcome, severity, created_at)`
- Existing `audit_logs`: add APPEND-ONLY enforcement (PostgreSQL row-level security or application-level `DELETE` restriction)
- `AuditViewer` QML screen

**Migration requirements:**
- `CREATE TABLE platform_events`
- `ALTER audit_logs`: add any missing columns

**Execution order:** Priority 6 (alongside activity service)

---

## 11. Validation Framework

**Complexity:** MEDIUM
**Risk:** LOW

**Dependencies:**
- Domain object validation is currently inline in service methods
- Recommendation: centralized validation via pydantic or custom `Validator` classes
- All existing validation code must be migrated

**Migration requirements:** Pure code refactor — no schema changes

**Execution order:** Priority 7 (maintenance / quality)

---

## 12. Decorator Framework (@requires_module, expanded @requires_permission)

**Complexity:** LOW
**Risk:** LOW

**Dependencies:**
- `@requires_permission` decorator exists at `src/core/shared/security/decorators.py`
- Needs: `@requires_module(module_code)` decorator
- Needs: `@requires_scope(scope_type, scope_id_arg, permission_code)` decorator

**Migration requirements:** None (additive)

**Execution order:** Priority 5

---

## Recommended Execution Order

| Priority | Item | Complexity | Risk | Weeks |
|---|---|---|---|---|
| P1 | Fix `_deactivate_other_organizations()` | LOW | CRITICAL | 0.5 |
| P1 | Fix `get_active()` / `list_all()` org repo | LOW | HIGH | 0.5 |
| P1a | Fix `user_roles` unique constraint | LOW | MEDIUM | 1 |
| P2 | Add `user_tenants` table + service | HIGH | CRITICAL | 3 |
| P2 | Membership check in `set_active_tenant()` | LOW | CRITICAL | 0.5 |
| P3 | Seed `platform.admin` permission + fix `is_platform_admin()` | LOW | HIGH | 0.5 |
| P3 | Add `tenant_admin` role | LOW | LOW | 1 |
| P4 | Add `org_admin` role | LOW | LOW | 1 |
| P5 | Scope `list_all()` `UserRepository` to tenant | LOW | HIGH | 1 |
| P5 | Add `@requires_module` decorator | LOW | LOW | 1 |
| P5 | Add `site_admin` + `department_manager` roles | MEDIUM | LOW | 2 |
| P6 | Argon2id password hashing | COMPLETE | COMPLETE | 0 |
| P6 | Fix MFA UI (collect TOTP code) | LOW | HIGH | 1 |
| P6 | Replace custom TOTP with pyotp | LOW | LOW | 1 |
| P7 | Harden nullable `org_id` columns (employees, time_entries) | LOW | MEDIUM | 1 |
| P7 | Add `activity_entries` table + `ActivityService` | MEDIUM | LOW | 3 |
| P7 | Add `platform_events` table (tenant-level audit) | MEDIUM | MEDIUM | 2 |
| P8 | Tenant lifecycle service (create/suspend/archive) | MEDIUM | MEDIUM | 3 |
| P8 | Org lifecycle improvements (remove single-active-org invariant) | MEDIUM | MEDIUM | 2 |

**Total estimated: 26-30 weeks for P1-P8**

---

# 25. RECOMMENDED FUTURE ROADMAP

## Phase 0 — Critical Bug Fixes (Weeks 1-2)

These are single-day fixes that MUST happen before any other work proceeds.

1. Fix `_deactivate_other_organizations()` — add `tenant_id` filter to the deactivation query so that switching organizations within one tenant does not deactivate organizations belonging to the same user in other tenants.
2. Fix `OrganizationRepository.get_active()` — add `tenant_id` parameter so that the active organization is always resolved within the caller's tenant scope.
3. Seed `platform.admin` permission in `DEFAULT_PERMISSIONS` and assign it to the `admin` role so that `is_platform_admin()` returns correct results rather than always returning `False`.
4. Fix `user_roles` unique constraint to `(user_id, role_id, organization_id)` so that org-scoped role bindings are expressible and `org_admin` assignments become possible.

**Exit criteria:** All four fixes merged, test suite green, no regressions in auth or organization switching flows.

---

## Phase 1 — Tenant Security Foundation (Weeks 3-6)

1. Create `user_tenants` table + Alembic migration. Backfill all existing users against the default tenant returned by `get_default()`. Validate that every user row has at least one `user_tenants` row before allowing the migration to complete.
2. Add `_can_access_tenant(user_id, tenant_id)` check in `TenantContextService.set_active_tenant()`. Return `PermissionDeniedError` if the user has no active `user_tenants` row for the requested tenant. Exempt users holding the `admin` role.
3. Update `AuthService.register_user()` to accept an optional `tenant_id` parameter and auto-create the corresponding `user_tenants` row on registration.
4. Scope `SqlAlchemyUserRepository.list_all()` to the calling tenant so that user enumeration never crosses tenant boundaries.
5. Add `list_tenants_for_user(user_id)` to `TenantRepository` to support tenant switcher UI and session bootstrap.

**Exit criteria:** A user created in Tenant A cannot call `set_active_tenant(tenant_b_id)` and succeed. Existing integration tests for auth and session management remain green.

---

<!--
  PHASE 2 SPLIT RATIONALE
  =======================
  The original Phase 2 violated four architectural principles:

  1. Single Responsibility — it mixed RBAC layer changes (roles/permissions),
     a new domain service (TenantAdminService), platform-event infrastructure
     (platform_events table — not defined until Phase 5), and a UI component
     (tenant switcher) into one phase. A regression in any area would block
     delivery of all others.

  2. Dependency ordering — Task 4 ("emit a platform_events entry, see Phase 5")
     is a forward dependency. Phase 2 tasks cannot be completed without
     platform_events, which lives in Phase 5. This makes Phase 2 undeliverable
     as written without reordering Phase 5.

  3. Incremental delivery — RBAC changes can be tested and merged independently
     of TenantAdminService and of the UI. Bundling them prevents incremental
     validation and forces a large, risky batch merge.

  4. Risk isolation — RBAC changes affect the entire auth system (high blast
     radius). TenantAdminService introduces new persistence. UI changes are
     presentational. These carry different risk profiles and should be isolated
     so that a UI regression cannot block a security fix.

  The phase is split into: 2A (RBAC), 2B (TenantAdminService without events),
  2C (platform_events, moved forward from Phase 5), and 2D (tenant switcher UI).
  Phase 5 retains the activity/audit expansion items that do not belong here.
-->

## Phase 2A — RBAC & Admin Role Hierarchy (Weeks 7-8)  ✅ COMPLETE (2026-06-17)

**Depends on:** Phase 0 (`platform.admin` seeded, `user_roles` constraint fixed), Phase 1 (tenant membership table exists)

**Scope:** Pure RBAC layer. No service layer, no events, no UI.

1. ✅ Added `tenant.create`, `tenant.manage`, `tenant.read`, `org.create`, `org.manage` to `DEFAULT_PERMISSIONS` in `auth/policy.py`.
2. ✅ Added `tenant_admin` role with permissions: `tenant.create`, `tenant.manage`, `tenant.read`, `org.create`, `org.manage`, `organization.access`, `settings.manage`, `auth.read`, `auth.manage`. Seeded via `DEFAULT_ROLE_PERMISSIONS`.
3. ✅ Added `org_admin` role with permissions: `org.manage`, `employee.read`, `employee.manage`, `organization.access`, `settings.manage`, `auth.read`, `auth.manage`. Platform-level permissions (`tenant.*`, `platform.admin`) explicitly excluded.
4. ✅ Verified `is_platform_admin()` end-to-end. Tests: admin → `True`, `tenant_admin` / `org_admin` → `False`.

**Tests:** `src/tests/platform/test_phase_2a_admin_role_hierarchy.py` (20 tests — 10 policy-level, 10 integration). 345/345 platform tests pass.

---

## Phase 2B — Tenant Administration Services (Weeks 9-10)  ✅ COMPLETE (2026-06-18)

**Depends on:** Phase 2A (`tenant_admin` role + permissions)

**Scope:** New `TenantAdminService` domain service. No platform events. No UI.

1. ✅ Built `TenantAdminService` (`src/core/platform/tenancy/application/tenant_admin_service.py`) with: `create_tenant()`, `get_tenant()`, `list_tenants()`, `suspend_tenant()`, `archive_tenant()`, `restore_tenant()`.
2. ✅ `create_tenant()` seeds the calling user's `user_tenants` membership in the new tenant (`tenant_role="tenant_admin"`).
3. ✅ `suspend_tenant()` and `archive_tenant()` reject the calling user's own active tenant (`TENANT_SELF_LOCKOUT`).
4. ✅ `restore_tenant()` is `platform.admin` only; `tenant_admin` is denied.
5. ✅ `_emit_tenant_event()` was a no-op stub — replaced in Phase 2C with real `platform_events` emission.
6. ✅ `Tenant.is_active` refactored to a `@property` derived from `tenant_status` (`active` / `suspended` / `archived`). Migration: `y2z3a4b5c6d7_add_tenant_status`.
7. ✅ `TenantContextService.set_active_tenant()` raises `TENANT_SUSPENDED` / `TENANT_ARCHIVED` specifically.
8. ✅ Wired into `PlatformServiceBundle`, `ServiceGraph`, and `build_service_dict` as `"tenant_admin_service"`.

**Permission model:**
- `create_tenant` → `tenant.create` or `platform.admin`
- `get_tenant` / `list_tenants` → `tenant.read` or `platform.admin`
- `suspend_tenant` / `archive_tenant` → `tenant.manage` or `platform.admin`
- `restore_tenant` → `platform.admin` only

**Tests:** `src/tests/platform/test_phase_2b_tenant_admin_service.py` (24 tests — domain, permissions, lifecycle, self-lockout, context rejection). 369/369 platform tests pass.

---

## Phase 2C — Platform Events Foundation (Weeks 11-12) ✅ COMPLETE (2026-06-18)

**Depends on:** Phase 2B (`TenantAdminService`)

**Note:** The original roadmap placed `platform_events` in Phase 5. It is pulled forward because Phase 2B emits tenant lifecycle events and requires the table. Phase 5 retains the activity/audit expansion items (domain event bus integration, `AuditViewer` UI, `ActivityFeed` component).

**Scope:** `platform_events` table and event publishing infrastructure.

1. ✅ Added `platform_events` table: `(id, operation, actor_user_id, tenant_id, resource_type, resource_id, outcome, severity, created_at, metadata_json)`. Migration: `z3a4b5c6d7e8_create_platform_events` (revises `y2z3a4b5c6d7`). 5 indexes.
2. ✅ Added `OperationNotPermittedError` to `src/core/platform/common/exceptions.py`.
3. ✅ Created `PlatformEvent` domain model (`src/core/platform/platform_events/domain/platform_event.py`) with `create()` factory.
4. ✅ Created `PlatformEventRepository` ABC (`src/core/platform/platform_events/contracts.py`). Append-only — `update()`/`delete()` raise `OperationNotPermittedError`.
5. ✅ Created `SqlAlchemyPlatformEventRepository` (`src/core/platform/infrastructure/persistence/repositories/platform_events.py`) — `add()`, `list_for_tenant()`, `list_for_resource()`. No `list_all()`.
6. ✅ Replaced the no-op `_emit_tenant_event()` stub in `TenantAdminService` with real emission: `create_tenant` → severity low; `suspend_tenant` → medium; `archive_tenant` → high (captures `old_status` before mutation); `restore_tenant` → medium. `platform_event_repo` is optional (`None` = no-op, for backward compat in tests).
7. ✅ Wired `SqlAlchemyPlatformEventRepository` into `RepositoryBundle` and `platform_registry.py` (passed to `TenantAdminService`).

**Tests:** `src/tests/platform/test_phase_2c_platform_events.py` (8 tests — 4 emission, 2 append-only enforcement, 2 tenant/resource scoping). 377/377 platform tests pass.

**Alembic HEAD:** `z3a4b5c6d7e8` (revises `y2z3a4b5c6d7`)

---

## Phase 2D — Tenant Switcher (Weeks 13-14)

**Depends on:** Phase 2A (tenant_admin role), Phase 2B (TenantAdminService), Phase 2C (platform_events), Phase 1 (`list_tenant_ids_for_user()` + membership enforcement in `set_active_tenant()`)

**Scope:** Two backend prerequisites (complete), then UI.

> The original spec listed this phase as "UI-only." A review against the implemented backend revealed two missing service methods and a `_can_access` cross-tenant leak. These are now complete.

---

### Backend prerequisites ✅ COMPLETE (2026-06-18)

**1. `TenantAdminService.list_accessible_tenants()` — implemented**

- No permission guard — accessing one's own memberships is always allowed.
- Regular users: active-only tenants from `user_tenant_repo.list_tenant_ids_for_user()`.
- `platform.admin` / `admin`: all tenants including suspended/archived (so UI can show status).
- `list_tenants()` is unchanged and remains admin-only.

**2. `TenantContextService.switch_to_tenant(tenant_id)` — implemented**

Atomic tenant switch:
1. `set_active_tenant(tenant_id)` — validates status, enforces membership.
2. `user_session.set_active_organization_id(None)` — clears stale org immediately.
3. `org_repo.list_for_tenant(tenant_id, active_only=True)` — find orgs in new tenant.
4. If exactly one → auto-select via `set_active_organization_id(orgs[0].id)`; otherwise leave None.

Principal rebuild is automatic — `set_active_tenant_id()` and `set_active_organization_id()` both call `replace()` + `_notify_context_changed()`.

**3. `TenantContextService._can_access(organization: Organization)` — fixed**

Cross-tenant guard added: if `organization.tenant_id` is set and does not match `active_tenant_id`, access is denied regardless of session org ID. Also added missing `platform.admin` permission bypass. Signature changed from `(organization_id: str)` to `(organization: Organization)`.

**Tests:** `src/tests/platform/test_phase_2d_tenant_switcher_backend.py` (10 tests). 387/387 platform tests pass.

---

### UI work (pending — Phase 2D-UI)

1. Add tenant switcher to the platform admin shell UI, driven by `TenantAdminService.list_accessible_tenants()`.
2. On switch: call `TenantContextService.switch_to_tenant(tenant_id)` — atomically updates both tenant and organization context.
3. A user with a single tenant sees the switcher disabled (greyed out).
4. Switcher must reflect the current active tenant as the selected item on open.

---

**Exit criteria:** Platform admin can switch between tenants from the shell UI without session corruption. A non-admin with membership in two tenants can switch. A single-tenant user cannot trigger a switch. After switching, `get_active_organization()` returns an org belonging to the new tenant.

---

## Phase 3 — Auth Hardening (Weeks 11-12)

1. **Complete:** Argon2id is canonical in `domain/security/auth/credentials/passwords.py`. This is a clean pre-release PBKDF2 cutover; only obsolete Argon2id cost profiles are rehashed after successful credential verification.
2. Fix MFA UI to collect the TOTP code at login time. The current implementation stores the TOTP secret but never validates it during authentication.
3. Replace the custom TOTP implementation with `pyotp` to reduce maintenance surface and align with RFC 6238.
4. Add `organizations.status` enum (`active`, `suspended`, `archived`) to replace the `is_active` boolean. Retain `is_active` as a computed property for backward compatibility during the transition period.

**Exit criteria:** Argon2id creation/verification and cost-profile rehash are covered end-to-end. PBKDF2 fails closed by design. MFA enrollment and login still require their independent exit-gate validation.

---

## Phase 4 — Site and Department Security (Weeks 13-16)

1. Add `site_admin` and `department_manager` roles with their respective permission codes (`site.manage`, `site.admin`, `department.manage`, `department.admin`). Seed via `bootstrap_service.py`.
2. Add `site.*` and `department.*` permission codes to `DEFAULT_PERMISSIONS` in `auth/policy.py`.
3. Add `list_for_site(site_id, tenant_id)` and `list_for_department(department_id, tenant_id)` methods to employee and timesheet repositories. Enforce tenant scoping at the repository layer.
4. Add `AccessControlService.assign_site_grant()` and `assign_dept_grant()` using the existing `ScopedAccessGrant` infrastructure (no schema change needed).
5. Add `@requires_module(module_code)` decorator in `src/core/shared/security/decorators.py`. Add `@requires_scope(scope_type, scope_id_arg, permission_code)` decorator for granular scope-level enforcement.

**Exit criteria:** A `site_admin` user can manage employees at their site only and cannot read data for other sites in the same organization. Module decorator correctly rejects calls when the requesting organization has the module disabled.

---

## Phase 5 — Audit and Activity (Weeks 17-20)

1. Add `platform_events` table for tenant-level audit: `(id, operation, actor_user_id, tenant_id, resource_type, resource_id, outcome, severity, created_at)`. This captures cross-organization events that `audit_logs` cannot represent.
2. Harden `audit_logs` to be append-only. In PostgreSQL: add a row-level security policy denying `DELETE` and `UPDATE`. In SQLite (current target): add an application-level guard in `SqlAlchemyAuditLogRepository` that raises `OperationNotPermittedError` on delete/update calls.
3. Add `activity_entries` table: `(id, tenant_id, org_id, entity_type, entity_id, actor_user_id, action_code, message, created_at)`. No backfill needed — activity is forward-looking only.
4. Expand domain events: add `ProjectCreated`, `TaskAssigned`, `MilestoneReached`, `MemberInvited`, `RoleChanged`, `TenantSuspended` event types. `ActivityService` subscribes to the domain event bus and writes to `activity_entries`.
5. Build `AuditViewer` QML screen for platform admins. Build `ActivityFeed` QML component for project and organization detail views.

**Exit criteria:** All write operations on projects, tasks, and user management produce `activity_entries` rows. Tenant lifecycle operations produce `platform_events` rows. `audit_logs` cannot be deleted via the application layer.

---

## Phase 6 — Data Integrity Hardening (Weeks 21-24)

1. Harden `employees.organization_id` to `NOT NULL`. Audit all code paths that create employee records and ensure `organization_id` is always provided. Add migration with a pre-check that aborts if any `NULL` rows exist.
2. Harden `time_entries.organization_id` to `NOT NULL` using the same pattern.
3. Harden `timesheet_periods.organization_id` to `NOT NULL` using the same pattern.
4. Replace `hasattr()` runtime introspection in `_apply_scope()` with compile-time ORM column enforcement. Define a `TenantScoped` mixin with `tenant_id: Mapped[int]` and `OrgScoped` mixin with `organization_id: Mapped[int]`. Use `isinstance()` checks against these mixins rather than `hasattr()` so that a missing column raises an error at import time rather than silently skipping scope enforcement.
5. Add cross-tenant isolation tests for every repository: assert that a repository call authenticated to Tenant A returns zero rows when the database contains rows belonging only to Tenant B.

**Exit criteria:** All three `organization_id NOT NULL` migrations applied with zero data loss. `_apply_scope()` raises `AttributeError` immediately at startup if a model is missing an expected column. Cross-tenant isolation test suite passes with 100% coverage across all repository classes.

---

## Phase 7 — User Lifecycle (Weeks 25-30)

1. Add `users.email` column (`VARCHAR NULLABLE` initially, `NOT NULL` after backfill). Backfill from username where username matches email format.
2. Build `InvitationService`: generate signed invite tokens with expiry, associate invites with a target `tenant_id` and optional `organization_id`. Invited user creates their account by accepting the token.
3. Add user lifecycle states: `invited`, `active`, `suspended`, `deactivated`, `deleted`. Store in `users.lifecycle_state`. Replace bare `is_active` boolean semantics where they conflict with lifecycle state.
4. Build user deactivation with session invalidation: deactivating a user must expire all active `auth_sessions` rows for that user immediately.
5. Add org switcher to the shell header, driven by `list_active_organizations_for_user(user_id, tenant_id)`. The switcher must only show organizations within the user's active tenant.
6. Build tenant provisioning end-to-end workflow in the platform admin UI: create tenant, assign `tenant_admin`, create first organization, invite first `org_admin`.

**Exit criteria:** Full invite-to-active user lifecycle exercised in integration tests. Session invalidation verified by asserting that a deactivated user's existing session token is rejected on the next authenticated call. Tenant provisioning workflow operates without manual database intervention.

---

## Long-Term (Post Phase 7)

The following items are architecturally significant but require Phase 1-7 to be complete before they can be executed without rework.

- **Module licensing at tenant level:** Add `tenant_module_licenses` table to replace or complement `organization_module_entitlements`. Allows licensing at the tenant level with org-level overrides.
- **Organization merge service:** Allow two organizations within the same tenant to be merged, with full data migration of projects, employees, and memberships.
- **Two-layer module entitlement model:** Tenant licenses what modules are available; organization enables/disables within that set. Enforce at the `@requires_module` decorator layer.
- **REST API layer for server deployment:** The current architecture is desktop-first. A REST API layer (FastAPI recommended, given the existing SQLAlchemy and Pydantic usage) would enable web client and mobile client deployment without changing the domain or service layers.
- **PostgreSQL migration from SQLite:** Required before production multi-tenant deployment at any scale. The ORM layer is largely database-agnostic but several partial index constructs and the `NULLS NOT DISTINCT` constraint require PostgreSQL-specific migrations.
- **Containerization:** Docker image for the platform service layer, separate from the Qt desktop client. Required for server deployment.
- **SSO / OIDC integration:** Allow tenant users to authenticate via their organization's identity provider. Map OIDC claims to internal roles via `user_tenants` and `user_roles`. `pyotp` (Phase 3) is a prerequisite to ensure the internal MFA baseline is sound before adding federated auth.
