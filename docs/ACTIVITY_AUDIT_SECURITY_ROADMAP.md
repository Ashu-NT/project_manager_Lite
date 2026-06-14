# Activity, Audit & Security Roadmap

**Status:** In Progress — Phases 1–5 complete  
**Date:** 2026-06-14  
**Branch:** `refactor/safe-start`

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Definitions](#2-definitions)
3. [Current Codebase Map](#3-current-codebase-map)
4. [Classification of Current Audit Usages](#4-classification-of-current-audit-usages)
5. [Target File and Folder Structure](#5-target-file-and-folder-structure)
6. [Target Activity Schema](#6-target-activity-schema)
7. [Target Audit Schema](#7-target-audit-schema)
8. [Database Migration Plan](#8-database-migration-plan)
9. [Decorator Architecture](#9-decorator-architecture)
10. [RBAC Decorator Architecture](#10-rbac-decorator-architecture)
11. [Naming Convention](#11-naming-convention)
12. [UI Migration Plan](#12-ui-migration-plan)
13. [API / Presenter / Controller Migration Plan](#13-api--presenter--controller-migration-plan)
14. [Test Plan](#14-test-plan)
15. [Execution Phases](#15-execution-phases)
16. [Risks](#16-risks)

---

## 1. Problem Statement

The codebase has a single `AuditService` / `audit_logs` table that currently serves two fundamentally different purposes:

| Purpose | Example actions | Who sees it |
|---|---|---|
| **User-facing activity feed** | `task.create`, `inventory_item.update`, `resource.add` | Business users in PM, Inventory, Maintenance workspaces |
| **Compliance / security ledger** | `auth.login`, `auth.failed_login`, governance approvals | Platform admin / compliance officers only |

These are stored in the same table and served by the same `AuditService.record()` call via `record_audit()`. This must be separated.

The `build_audit_collection()` presenter in PM Collaboration even labels comment trails and notifications as "Audit" — these are unambiguously user-facing activity records, not compliance data.

Inventory detail pages (`inventory_activity_handler.py`, `reservations_activity_handler.py`, etc.) call `_platform_audit.list_recent()` to populate what are clearly **activity feeds** — they serialize results with `success/danger/warning` colour labels for the UI. This is activity, not audit.

---

## 2. Definitions

### Activity
A user-facing timeline entry recording business operations for the "what happened here?" question.

- Shown inside workspace detail pages and collaboration panels
- Human-readable messages with icon/colour
- Scoped to a specific entity (task, project, inventory item, asset)
- Tenant + org scoped
- Replaces current "audit" labels in PM Collaboration, Inventory detail pages, Maintenance detail pages
- **Not a compliance ledger** — records may eventually be pruned

### Audit
An immutable compliance and security change ledger.

- **Never shown** in normal PM / Inventory / Maintenance workspaces
- Only visible in Platform Admin Console / Control Center (currently placeholder)
- Records login/logout/failed_login, permission changes, role changes, approval decisions, critical admin operations
- Supports field-level old/new values
- Carries compliance tags (GDPR, SOC2, ISO27001, HIPAA)
- Records must not be updated or deleted — append-only

---

## 3. Current Codebase Map

### 3.1 ORM / Database Models

| File | Table | Note |
|---|---|---|
| `src/core/platform/infrastructure/persistence/orm/audit.py` | `audit_logs` | Single table for both activity and audit. Columns: id, tenant_id, occurred_at, actor_user_id, actor_username, action, entity_type, entity_id, project_id, organization_id, details_json |

**Current `AuditLogORM` lacks:** operation type, field-level old/new values, actor_type, actor_ip, actor_user_agent, request_id, source, severity, compliance_tag, module, workspace_id.

### 3.2 Domain Model

| File | Class | Fields |
|---|---|---|
| `src/core/platform/audit/domain/audit_entry.py` | `AuditLogEntry` | id, occurred_at, actor_user_id, actor_username, action, entity_type, entity_id, project_id, organization_id, details (dict) |

`AuditLogEntry` is missing tenant_id, module, workspace_id, human_message, visibility, icon, color for Activity; and is missing operation, field, old_value, new_value, actor_type, actor_ip, severity, compliance_tag, request_id, source for Audit.

### 3.3 Repository

| File | Class |
|---|---|
| `src/core/platform/audit/contracts.py` | `AuditLogRepository` (ABC): add, list_recent, list_recent_for_organization |
| `src/core/platform/infrastructure/persistence/repositories/audit.py` | `SqlAlchemyAuditLogRepository` |

### 3.4 Service

| File | Class | Key methods |
|---|---|---|
| `src/core/platform/audit/application/audit_service.py` | `AuditService` | `record(action, entity_type, entity_id, ...)`, `list_recent(limit, project_id, entity_type)` |

`list_recent()` calls `require_permission(user_session, "audit.read")` — this is currently used by inventory activity handlers, meaning business users need `audit.read` just to see their own item history. Wrong.

### 3.5 Helper Functions

| File | Function | Used by |
|---|---|---|
| `src/core/platform/audit/helpers.py` | `record_audit(owner, action, entity_type, entity_id, project_id, details)` | All service modules via `self._audit_service` attribute |
| `src/core/platform/auth/application/audit_recorder.py` | `record_auth_event(service, action, username, user_id, details)` | Auth service for login/logout events |
| `src/core/modules/project_management/application/tasks/commands/assignment_audit.py` | `record_assignment_action(...)` | Task assignment service |
| `src/core/platform/department/application/department_audit.py` | `record_department_create()`, `record_department_update()` | Department service |
| `src/core/modules/inventory_procurement/application/catalog/catalog_audit.py` | `record_inventory_item_*_audit()` × 6 | Inventory catalog service |

### 3.6 API Adapters

| File | Class | Role |
|---|---|---|
| `src/api/desktop/platform/audit.py` | `PlatformAuditDesktopApi` | Serializes `AuditLogEntry` → `AuditLogEntryDto` with entity name resolution. Used by both inventory activity handlers AND Platform Admin Console |
| `src/api/desktop/platform/models/audit.py` | `AuditLogEntryDto` | DTO with: id, occurred_at, actor_user_id, actor_username, action, entity_type, entity_id, project_id, details, project_label, entity_label, details_label |

### 3.7 Presenters and Controllers (UI layer)

| File | Function/Class | Current label | Should be |
|---|---|---|---|
| `src/ui_qml/modules/project_management/presenters/collaboration/audit_builder.py` | `build_audit_collection()` | "Audit" (title="Audit") | **Activity** — shows notifications + comment trails |
| `src/ui_qml/modules/project_management/presenters/collaboration/activity_builder.py` | `build_activity_collection()` | "Activity" (panelId="activity") | Activity — correct label already |
| `src/ui_qml/modules/project_management/presenters/collaboration/workspace_builder.py` | — | Aggregates audit + activity | Keep activity builder, remove audit builder |
| `src/ui_qml/modules/inventory_procurement/controllers/inventory/inventory_activity_handler.py` | `load_detail_activity()` | Calls `_platform_audit.list_recent()` | Should call ActivityService |
| `src/ui_qml/modules/inventory_procurement/controllers/reservations/reservations_activity_handler.py` | `load_detail_activity()` | Same pattern | Should call ActivityService |
| `src/ui_qml/modules/inventory_procurement/controllers/pricing/pricing_activity_handler.py` | `load_detail_activity()` | Same pattern | Should call ActivityService |
| `src/ui_qml/modules/inventory_procurement/controllers/procurement/procurement_activity_handler.py` | `load_detail_activity()` | Same pattern | Should call ActivityService |
| `src/ui_qml/modules/inventory_procurement/controllers/catalog/catalog_activity_handler.py` | `load_detail_activity()` | Same pattern | Should call ActivityService |
| `src/ui_qml/modules/inventory_procurement/controllers/common/serializers/audit_activity_serializer.py` | `serialize_audit_entries_for_activity()` | Named audit but renders activity | Rename to `serialize_activity_entries()` |
| `src/ui_qml/modules/project_management/controllers/scheduling/activity_log_service.py` | `ActivityLogService` | Already named activity | Keep, wire to ActivityService |
| `src/ui_qml/modules/project_management/presenters/scheduling/activity_feed_builder.py` | — | Scheduling activity feed | Wire to ActivityService |
| `src/ui_qml/modules/project_management/presenters/projects/activity_builder.py` | — | Project activity | Wire to ActivityService |

### 3.8 QML Files

| File | Current role | Action |
|---|---|---|
| `src/ui_qml/platform/qml/workspaces/admin/sections/AdminAuditSection.qml` | Platform Admin governance overview — shows activity feed from `_overview.activityFeed` | Keep "Audit" label here — this is the Admin Console placeholder. Wire to true Audit system in Phase 5 |
| `src/ui_qml/modules/project_management/qml/workspaces/*/sections/*ActivitySection.qml` | Activity sections in PM workspaces | Keep, wire to ActivityService |
| `src/ui_qml/modules/project_management/qml/workspaces/tasks/sections/TasksCollaborationSection.qml` | Tasks collaboration section | Remove audit panel, keep activity |
| `src/ui_qml/shared/qml/App/Widgets/ActivityFeed.qml` | Shared activity feed widget | Keep, extend if needed |
| `src/ui_qml/modules/project_management/qml/workspaces/collaboration/CollaborationWorkspacePage.qml` | PM Collaboration workspace | Remove "Audit" collection/panel |

### 3.9 Migrations

| File | What it does |
|---|---|
| `versions/2c7fb73e21aa_add_audit_and_approval_tables.py` | Creates `audit_logs` (original schema without tenant/org) |
| `versions/r1s2t3u4v5w6_add_audit_log_tenant_ownership.py` | Adds `tenant_id` and `organization_id` to `audit_logs` |
| `versions/q2r3s4t5u6v7_tenant_schema_hardening.py` | Tenant isolation hardening |

### 3.10 Tests

| File | Coverage |
|---|---|
| `src/tests/platform/test_phase_b_audit_log.py` | Audit entry creation, append-only contract, governance approval audit, dependency audit details, assignment audit labels |
| `src/tests/platform/test_phase_b_session_permissions.py` | Permission enforcement |
| `src/tests/platform/test_enterprise_rbac_matrix.py` | RBAC matrix |
| `src/tests/platform/test_authorization_engine.py` | Authorization engine |
| `src/tests/architecture/test_architecture_guardrails.py` | Architecture constraints |
| `src/tests/architecture/test_service_architecture.py` | Service layer architecture |

### 3.11 RBAC / Permission Enforcement

| Location | Permission code | Method |
|---|---|---|
| `AuditService.list_recent()` | `audit.read` | `require_permission()` |
| `AccessControlService.list_scope_grants()` | `access.manage` | `require_permission()` |
| `TaskLifecycleMixin.create_task()` | `task.manage` | `require_permission()` + `require_project_permission()` |
| `TaskLifecycleMixin.set_status()` | `task.manage` | Same |
| `ProjectLifecycleMixin.*` | Various | `require_permission()` + `require_project_permission()` |
| `SiteService.*` | `settings.manage`, `site.read` | `require_permission()`, `require_any_permission()` |
| All services calling `record_audit()` | — | None (fire-and-forget helper) |

Current `require_permission` and `require_any_permission` live in `src/core/platform/auth/authorization.py`. They are already shared across all modules — no per-module duplication. The gap is that there is no `@requires_permission` decorator form, only function calls.

---

## 4. Classification of Current Audit Usages

### 4.1 → ACTIVITY (move to ActivityEntry / activity_entries)

These are business operation records that power UI timelines. They should become `ActivityEntry` records.

| Action / Source | Entity types affected |
|---|---|
| `task.create`, `task.update` | task |
| `task.status.set` | task |
| `task.assign`, `task.unassign` | task_assignment |
| `task.dependency.add`, `task.dependency.remove` | task_dependency |
| `project.create`, `project.update` | project |
| `resource.create`, `resource.update` | resource |
| `cost_item.*` | cost_item |
| `project_baseline.*` | project_baseline |
| `risk_register.*` | risk_register |
| `inventory_item_category.create`, `*.update` | inventory_item_category |
| `inventory_item.create`, `*.update` | inventory_item (stock_item) |
| `inventory_item.link_document`, `*.unlink_document` | inventory_item |
| `stock_reservation.*` | stock_reservation |
| `purchase_requisition.*` | purchase_requisition |
| `purchase_order.*` | purchase_order |
| All comment/notification entries in `build_audit_collection()` | — |

**Source files to migrate:**
- `src/core/platform/audit/helpers.py` → `record_audit()` callers that are business ops
- `src/core/modules/project_management/application/tasks/commands/assignment_audit.py`
- `src/core/modules/inventory_procurement/application/catalog/catalog_audit.py`
- `record_audit()` calls in lifecycle.py, dependency.py, cost_lifecycle.py, register_lifecycle.py, resource_commands.py

### 4.2 → AUDIT (keep in AuditEntry / audit_entries)

These are security, compliance, and admin governance records. They must stay as Audit.

| Action / Source | Entity types affected | Why Audit |
|---|---|---|
| `auth.login`, `auth.logout`, `auth.failed_login` | auth_session | Security event |
| Approval grant/reject from governance workflow | approval_request | Compliance decision |
| `user.create`, `user.update`, `user.deactivate` | user | Identity management |
| `role.create`, `role.update`, `role.delete` | role | RBAC change |
| `role.permission.add`, `role.permission.remove` | role_permission | RBAC change |
| `user.role.assign`, `user.role.revoke` | user_role | RBAC change |
| `module_entitlement.grant`, `*.revoke` | module_entitlement | Access control |
| `access_scope.grant`, `*.revoke` | scoped_access_grant | Access control |
| Future: `export.sensitive_data` | — | Compliance |

**Source files:**
- `src/core/platform/auth/application/audit_recorder.py` → `record_auth_event()` → keep as Audit
- Future: wrap auth service, user service, role service, permission service with Audit recording

### 4.3 → BORDERLINE (admin settings — classify as Audit for traceability)

These are admin settings operations. They are not security events but they change system configuration. Recommended: keep as Audit (admin traceability), do not show in UI activity feeds.

| Action | Entity |
|---|---|
| `site.create`, `site.update` | site |
| `department.create`, `department.update` | department |
| `organization.update` | organization |
| `tenant.*` | tenant |

### 4.4 → DELETE / RENAME (collaboration panel mislabeling)

| Item | Action |
|---|---|
| `build_audit_collection()` in `audit_builder.py` — title="Audit" | Rename function to `build_activity_collection_legacy()` or remove; the data it shows (notifications + comments) is already handled by `activity_builder.py` |
| `panelId: "audit"` in collaboration ViewModels | Remove or merge into `panelId: "activity"` |
| `serialize_audit_entries_for_activity()` | Rename to `serialize_activity_entries()` |

### 4.5 → PLACEHOLDER (keep as-is for now)

| Item | Action |
|---|---|
| `AdminAuditSection.qml` | Keep "Audit" label. Currently shows `_overview.activityFeed` but will be wired to true AuditService in Phase 5 |
| `PlatformAuditDesktopApi` | Keep for now, split into `PlatformActivityDesktopApi` + `PlatformAuditDesktopApi` in Phase 3/5 |
| `AuditLogEntryDto` | Keep for now; replace with `ActivityEntryDto` + `AuditEntryDto` in Phases 3 and 5 |

---

## 5. Target File and Folder Structure

### 5.1 Activity System — New Files

```
src/core/platform/activity/
├── __init__.py
├── contracts.py                          # ActivityRepository ABC
├── domain/
│   ├── __init__.py
│   └── activity_entry.py                 # ActivityEntry dataclass
└── application/
    ├── __init__.py
    └── activity_service.py               # ActivityService

src/core/platform/infrastructure/persistence/
├── orm/activity.py                       # ActivityEntryORM → activity_entries table
├── mappers/activity.py                   # ORM ↔ domain mappers
└── repositories/activity.py             # SqlAlchemyActivityRepository

src/api/desktop/platform/
├── activity.py                           # PlatformActivityDesktopApi
└── models/activity.py                    # ActivityEntryDto

src/ui_qml/modules/inventory_procurement/controllers/common/serializers/
└── activity_serializer.py               # serialize_activity_entries() (renamed)

src/core/shared/activity/
├── __init__.py
├── decorators.py                         # @record_activity decorator
├── activity_context.py                   # ActivityContext helper
└── activity_recorder.py                  # record_activity() helper function
```

### 5.2 Audit System — New Files (following platform service pattern like site/department)

```
src/core/platform/audit_v2/             # NEW — enterprise audit (replaces current audit/)
├── __init__.py
├── contracts.py                          # AuditRepository ABC
├── domain/
│   ├── __init__.py
│   └── audit_entry.py                    # AuditEntry dataclass (full compliance schema)
└── application/
    ├── __init__.py
    └── audit_service.py                  # AuditService (enterprise version)

src/core/platform/infrastructure/persistence/
├── orm/audit_entry.py                    # AuditEntryORM → audit_entries table
├── mappers/audit_entry.py               # ORM ↔ domain mappers
└── repositories/audit_entry.py          # SqlAlchemyAuditRepository

src/api/desktop/platform/
├── audit_enterprise.py                   # PlatformAuditDesktopApi (enterprise)
└── models/audit_entry.py                 # AuditEntryDto

src/core/shared/audit/
├── __init__.py
├── decorators.py                         # @audit_change decorator
├── audit_context.py                      # AuditContext helper
└── audit_recorder.py                     # record_audit_entry() helper
```

**Note on naming collision:** The existing `src/core/platform/audit/` folder holds the current combined system. The new enterprise Audit system can be placed at `src/core/platform/audit/` after current contents are migrated, OR temporarily use `audit_v2/` to avoid a flag-day rename. The migration plan (Phase 5) should do this as a deliberate step.

### 5.3 Shared Security — New Files

```
src/core/shared/security/
├── __init__.py
├── decorators.py                         # @requires_permission, @requires_any_permission
└── permissions.py                        # Permission constants / helpers
```

### 5.4 Files to Modify

```
src/core/platform/audit/helpers.py       → split: record_activity() helper + record_audit_entry()
src/core/platform/auth/application/audit_recorder.py → route to new AuditService
src/core/modules/project_management/application/tasks/commands/assignment_audit.py → route to ActivityService
src/core/platform/department/application/department_audit.py → route to AuditService (borderline admin)
src/core/modules/inventory_procurement/application/catalog/catalog_audit.py → route to ActivityService
src/infra/composition/repositories.py   → add ActivityRepository, AuditRepository bundles
src/infra/composition/platform_registry.py → register ActivityService, AuditService
src/infra/composition/project_registry.py  → wire ActivityService into PM services
src/infra/composition/inventory_registry.py → wire ActivityService into inventory controllers
```

### 5.5 Files to Delete (after migration complete)

```
src/ui_qml/modules/project_management/presenters/collaboration/audit_builder.py
  (or gutted and renamed — confirm no QML references remain)
src/ui_qml/modules/inventory_procurement/controllers/common/serializers/audit_activity_serializer.py
  (replaced by activity_serializer.py)
```

---

## 6. Target Activity Schema

```python
@dataclass
class ActivityEntry:
    id: str
    action: str                    # machine-readable, e.g. "task.update"
    entity_type: str               # "task" | "project" | "resource" | "inventory_item" | ...
    entity_id: str
    actor_id: str | None           # user_id
    actor_role: str | None         # role at time of action (optional)
    module: str                    # "project_management" | "platform" | "inventory_procurement" | "maintenance"
    workspace_id: str | None       # workspace context
    tenant_id: str | None          # tenant isolation boundary
    organization_id: str | None    # business organization scope
    timestamp: datetime            # UTC
    type: str                      # "info" | "warning" | "system" | "user"
    human_message: str             # pre-rendered UI message, e.g. "Task 'Deploy' updated by Alice"
    details: dict                  # JSON metadata for UI cards
    context: dict                  # JSON scoping metadata (project_id, etc.)
    parent_entity_id: str | None   # optional parent entity id
    icon: str | None               # optional UI icon name
    color: str | None              # optional UI color
    visibility: str                # "public" | "workspace" | "private"
```

**`activity_entries` table columns:**

| Column | Type | Note |
|---|---|---|
| id | String PK | |
| action | String(128) | NOT NULL |
| entity_type | String(64) | NOT NULL |
| entity_id | String | NOT NULL |
| actor_id | String | nullable |
| actor_role | String(64) | nullable |
| module | String(64) | NOT NULL |
| workspace_id | String | nullable |
| tenant_id | String FK(tenants.id) | required except system/bootstrap records |
| organization_id | String FK(organizations.id) | optional |
| timestamp | DateTime | NOT NULL, UTC |
| type | String(32) | "info"/"warning"/"system"/"user" |
| human_message | Text | NOT NULL |
| details_json | Text | default '{}' |
| context_json | Text | default '{}' |
| parent_entity_id | String | nullable |
| icon | String(64) | nullable |
| color | String(32) | nullable |
| visibility | String(32) | "public"/"workspace"/"private", NOT NULL |

**Indexes:**
```sql
idx_activity_tenant_timestamp         (tenant_id, timestamp)
idx_activity_org_timestamp            (organization_id, timestamp)
idx_activity_entity                   (entity_type, entity_id)
idx_activity_workspace                (workspace_id, timestamp)
idx_activity_module_entity            (module, entity_type, entity_id)
idx_activity_actor                    (actor_id, timestamp)
```

---

## 7. Target Audit Schema

```python
@dataclass
class AuditEntry:
    id: str
    timestamp: datetime            # UTC, NOT NULL

    actor_id: str | None           # user_id / service account id
    actor_type: str                # "user" | "system" | "service_account"
    actor_username: str | None
    actor_ip: str | None           # IP address if available
    actor_user_agent: str | None   # user agent if available

    entity_type: str               # "task" | "user" | "role" | "auth_session" | ...
    entity_id: str
    entity_parent_id: str | None   # optional parent

    operation: str                 # "create" | "update" | "delete" | "access" |
                                   # "permission_change" | "login" | "logout" | "failed_login"

    field: str | None              # changed field (null for create/delete)
    old_value: str | None          # previous value (serialized)
    new_value: str | None          # new value (serialized)

    module: str                    # origin module
    tenant_id: str | None
    organization_id: str | None
    workspace_id: str | None

    request_id: str | None         # correlation / request ID
    source: str                    # "api" | "ui" | "automation" | "integration"

    severity: str                  # "low" | "medium" | "high" | "critical"
    compliance_tag: str            # "GDPR" | "SOC2" | "ISO27001" | "HIPAA" | "none"

    metadata: dict                 # JSON technical metadata
```

**`audit_entries` table columns:**

| Column | Type | Note |
|---|---|---|
| id | String PK | |
| timestamp | DateTime | NOT NULL, UTC |
| actor_id | String | nullable |
| actor_type | String(32) | NOT NULL ("user"/"system"/"service_account") |
| actor_username | String(128) | nullable |
| actor_ip | String(64) | nullable |
| actor_user_agent | Text | nullable |
| entity_type | String(64) | NOT NULL |
| entity_id | String | NOT NULL |
| entity_parent_id | String | nullable |
| operation | String(64) | NOT NULL |
| field | String(128) | nullable |
| old_value | Text | nullable |
| new_value | Text | nullable |
| module | String(64) | NOT NULL |
| tenant_id | String FK(tenants.id) | nullable |
| organization_id | String FK(organizations.id) | nullable |
| workspace_id | String | nullable |
| request_id | String | nullable |
| source | String(32) | NOT NULL |
| severity | String(16) | NOT NULL |
| compliance_tag | String(32) | NOT NULL, default "none" |
| metadata_json | Text | default '{}' |

**Indexes:**
```sql
idx_audit_tenant_timestamp            (tenant_id, timestamp)
idx_audit_org_timestamp               (organization_id, timestamp)
idx_audit_entity                      (entity_type, entity_id)
idx_audit_actor                       (actor_id, timestamp)
idx_audit_operation                   (operation, timestamp)
idx_audit_compliance                  (compliance_tag, timestamp)
idx_audit_severity                    (severity, timestamp)
```

**Immutability constraint:** The `AuditRepository.add()` is the only write method. There is no `update()` or `delete()`. The service layer must enforce this. A DB-level trigger can be added in a later phase.

---

## 8. Database Migration Plan

### Decision

**Recommendation: Option B — Keep `audit_logs` temporarily, create new tables**

Rationale:
- `audit_logs` currently stores a mix of business activity AND security events (auth.login, governance approvals)
- The two record types need different schemas going forward
- A blind rename of `audit_logs` → `activity_entries` would lose security records
- Creating both new tables allows each to have the correct schema from the start
- `audit_logs` remains unchanged during the migration window; services cut over gradually

### Phase 7 Migration Steps

**Migration A — Create `activity_entries`**

```sql
CREATE TABLE activity_entries (
    id VARCHAR PRIMARY KEY,
    action VARCHAR(128) NOT NULL,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR NOT NULL,
    actor_id VARCHAR,
    actor_role VARCHAR(64),
    module VARCHAR(64) NOT NULL DEFAULT 'platform',
    workspace_id VARCHAR,
    tenant_id VARCHAR REFERENCES tenants(id) ON DELETE RESTRICT,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE RESTRICT,
    timestamp DATETIME NOT NULL,
    type VARCHAR(32) NOT NULL DEFAULT 'info',
    human_message TEXT NOT NULL DEFAULT '',
    details_json TEXT NOT NULL DEFAULT '{}',
    context_json TEXT NOT NULL DEFAULT '{}',
    parent_entity_id VARCHAR,
    icon VARCHAR(64),
    color VARCHAR(32),
    visibility VARCHAR(32) NOT NULL DEFAULT 'workspace'
);
-- Indexes as defined in Section 6
```

**Migration B — Create `audit_entries`**

```sql
CREATE TABLE audit_entries (
    id VARCHAR PRIMARY KEY,
    timestamp DATETIME NOT NULL,
    actor_id VARCHAR,
    actor_type VARCHAR(32) NOT NULL DEFAULT 'user',
    actor_username VARCHAR(128),
    actor_ip VARCHAR(64),
    actor_user_agent TEXT,
    entity_type VARCHAR(64) NOT NULL,
    entity_id VARCHAR NOT NULL,
    entity_parent_id VARCHAR,
    operation VARCHAR(64) NOT NULL,
    field VARCHAR(128),
    old_value TEXT,
    new_value TEXT,
    module VARCHAR(64) NOT NULL DEFAULT 'platform',
    tenant_id VARCHAR REFERENCES tenants(id) ON DELETE RESTRICT,
    organization_id VARCHAR REFERENCES organizations(id) ON DELETE RESTRICT,
    workspace_id VARCHAR,
    request_id VARCHAR,
    source VARCHAR(32) NOT NULL DEFAULT 'api',
    severity VARCHAR(16) NOT NULL DEFAULT 'low',
    compliance_tag VARCHAR(32) NOT NULL DEFAULT 'none',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
-- Indexes as defined in Section 7
```

**Migration C — Backfill `audit_logs` → `activity_entries`**

Criteria for backfill (activity-type records):
```
action NOT IN (
    'auth.login', 'auth.logout', 'auth.failed_login',
    'approval.grant', 'approval.reject', 'approval.request',
    'user.create', 'user.update', 'user.deactivate',
    'role.create', 'role.update', 'role.delete',
    'role.permission.add', 'role.permission.remove',
    'user.role.assign', 'user.role.revoke',
    'module_entitlement.grant', 'module_entitlement.revoke',
    'access_scope.grant', 'access_scope.revoke'
)
```

Insert into `activity_entries`:
- `id` ← `audit_logs.id`
- `action` ← `audit_logs.action`
- `entity_type` ← `audit_logs.entity_type`
- `entity_id` ← `audit_logs.entity_id`
- `actor_id` ← `audit_logs.actor_user_id`
- `module` ← derive from `entity_type` prefix (task/project/resource → project_management, inventory_item/stock → inventory_procurement)
- `tenant_id` ← `audit_logs.tenant_id`
- `organization_id` ← `audit_logs.organization_id`
- `timestamp` ← `audit_logs.occurred_at`
- `human_message` ← `audit_logs.action` (placeholder; Phase 3 adds proper messages)
- `details_json` ← `audit_logs.details_json`
- `visibility` ← `'workspace'` (default)

**Migration D — Backfill `audit_logs` security records → `audit_entries`**

Auth/security-type records from `audit_logs`:
```
action IN (
    'auth.login', 'auth.logout', 'auth.failed_login',
    'approval.grant', 'approval.reject', 'approval.request'
)
```

Insert into `audit_entries`:
- Map fields as far as the schema allows
- `operation` ← map from action (auth.login → 'login', auth.failed_login → 'failed_login', etc.)
- `actor_type` ← 'user' by default
- `source` ← 'api'
- `severity` ← 'high' for auth events, 'medium' for approvals
- `compliance_tag` ← 'none' (refine in Phase 5)

**Migration E — Drop `audit_logs` (final step, after all services migrated)**

Only after:
- All `record_audit()` callers converted to `record_activity()` or `record_audit_entry()`
- All `_platform_audit.list_recent()` callers converted to `ActivityService`
- All test suites pass
- Confirmed no remaining FK references

**Rollback strategy:** Keep `audit_logs` table intact (do not drop FK constraints). Each migration has a `downgrade()` that removes the new table. The switch-over in application code is done at the service/repository layer — toggling back is a one-line change per service.

---

## 9. Decorator Architecture

### 9.1 `@record_activity` Decorator

**Location:** `src/core/shared/activity/decorators.py`

**Design:**

```python
def record_activity(
    *,
    action: str,
    entity_type: str,
    module: str,
    workspace_id: str | None = None,
    message: str = "",
    visibility: str = "workspace",
    type: str = "info",
):
    """
    Decorator that records an ActivityEntry after a successful service method call.

    Derives tenant_id and organization_id from TenantContextService on the owner.
    Derives actor_id from UserSessionContext on the owner.
    Does NOT fire if the decorated method raises an exception.
    Silently skips if no ActivityService is found on the owner.

    Usage:
        @record_activity(
            action="task.update",
            entity_type="task",
            module="project_management",
            workspace_id="tasks",
            message="Task updated",
        )
        def update_task(self, task_id: str, ...) -> Task:
            ...
    """
```

**Behaviour rules:**
- Runs AFTER the method completes successfully (wraps in try/finally — only records on success)
- Derives `entity_id` from the return value if it has an `.id` attribute; otherwise from the first positional argument that looks like an ID
- Alternatively: decorator accepts `entity_id_arg` parameter to name the argument to use
- Derives `tenant_id` from `self._tenant_context_service.get_active_tenant_id()` if available
- Derives `organization_id` from `self._tenant_context_service.get_active_organization_id()` if available
- Derives `actor_id` from `self._user_session.principal.user_id` if available
- Does NOT swallow business exceptions — re-raises cleanly
- Does NOT commit the session — the service method manages commit
- Is optional: if `self._activity_service` is None the decorator dev/test: warning|production critical paths: fail or log error

**Alternative — helper function (simpler, safer for Phase 3):**

For Phase 3, a helper function is safer than a decorator because service methods vary in their argument shapes. The decorator form can be added in Phase 4+.

```python
# src/core/shared/activity/activity_recorder.py

def record_activity(
    owner: object,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    module: str,
    workspace_id: str | None = None,
    message: str = "",
    details: dict | None = None,
    parent_entity_id: str | None = None,
    type: str = "info",
    visibility: str = "workspace",
) -> None:
    activity_service = getattr(owner, "_activity_service", None)
    if activity_service is None:
        return
    activity_service.record(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        module=module,
        workspace_id=workspace_id,
        human_message=message,
        details=details or {},
        parent_entity_id=parent_entity_id,
        type=type,
        visibility=visibility,
        commit=True,
    )
```

### 9.2 `@audit_change` Decorator

**Location:** `src/core/shared/audit/decorators.py`

**Design:**

```python
def audit_change(
    *,
    operation: str,
    entity_type: str,
    module: str,
    severity: str = "low",
    compliance_tag: str = "none",
    source: str = "api",
):
    """
    Decorator that records an immutable AuditEntry after a successful service method call.

    Only use for:
    - Security-sensitive operations (login, permission change, role change)
    - Compliance-critical operations (approval decisions, sensitive data export)
    - Critical admin create/update/delete operations

    Does NOT fire if the method raises. Does NOT commit. Re-raises exceptions.
    """
```

**Helper function (Phase 5 preferred form):**

```python
# src/core/shared/audit/audit_recorder.py

def record_audit_entry(
    owner: object,
    *,
    operation: str,
    entity_type: str,
    entity_id: str,
    module: str,
    field: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    severity: str = "low",
    compliance_tag: str = "none",
    source: str = "api",
    metadata: dict | None = None,
) -> None:
    audit_service = getattr(owner, "_audit_service", None)
    if audit_service is None:
        return
    audit_service.record(
        operation=operation,
        entity_type=entity_type,
        entity_id=entity_id,
        module=module,
        field=field,
        old_value=old_value,
        new_value=new_value,
        severity=severity,
        compliance_tag=compliance_tag,
        source=source,
        metadata=metadata or {},
        commit=True,
    )
```

**Use Audit (not Activity) for:**
- `auth.login` / `auth.logout` / `auth.failed_login`
- `user.create` / `user.update` / `user.deactivate`
- `role.*` / `role.permission.*` / `user.role.*`
- `module_entitlement.*`
- `access_scope.*`
- `approval.grant` / `approval.reject`
- Future: `export.sensitive_data`, `data.bulk_delete`

### 9.3 Auth Event Migration

`src/core/platform/auth/application/audit_recorder.py` currently calls `audit_service.record()` with `entity_type="auth_session"`. In Phase 5 this should be migrated to call `record_audit_entry()` with `operation="login"/"logout"/"failed_login"` and `severity="high"` / `compliance_tag="SOC2"`.

---

## 10. RBAC Decorator Architecture

### 10.1 Current State

`require_permission()` and `require_any_permission()` already live in `src/core/platform/auth/authorization.py` and are imported across all modules. There is no per-module duplication. This is already close to the target.

**Gaps:**
- No decorator form (`@requires_permission`) — only function call form
- No `require_all_permissions()` variant
- Permission codes are string literals scattered across services — no central registry
- `require_project_permission()` exists in PM but is not in the shared location

### 10.2 Target Design

**Location:** `src/core/shared/security/decorators.py`

```python
def requires_permission(permission_code: str, *, operation_label: str = ""):
    """
    Method decorator that calls require_permission before executing.
    Requires self._user_session to be set on the owner object.

    Usage:
        @requires_permission("task.manage", operation_label="update task")
        def update_task(self, task_id: str, ...) -> Task:
            ...
    """

def requires_any_permission(permission_codes: list[str], *, operation_label: str = ""):
    """Decorator form of require_any_permission."""

def requires_all_permissions(permission_codes: list[str], *, operation_label: str = ""):
    """Decorator form — user must hold ALL listed permissions."""
```

**Location:** `src/core/shared/security/permissions.py`

```python
class Permissions:
    """Central registry of permission code strings."""

    # Audit
    AUDIT_READ = "audit.read"
    AUDIT_MANAGE = "audit.manage"

    # Activity
    ACTIVITY_READ = "activity.read"

    # Tasks
    TASK_MANAGE = "task.manage"
    TASK_READ = "task.read"

    # Projects
    PROJECT_MANAGE = "project.manage"
    PROJECT_READ = "project.read"

    # Settings
    SETTINGS_MANAGE = "settings.manage"
    SITE_READ = "site.read"

    # Access
    ACCESS_MANAGE = "access.manage"

    # ... extend as needed
```

### 10.3 Migration Strategy for RBAC Decorators

**Do not do a flag-day migration.** The current `require_permission()` function calls work correctly. The decorator form is additive.

Steps:
1. Phase 6: Create `src/core/shared/security/decorators.py` with decorator wrappers around the existing `require_permission()` functions
2. Re-export from `src/core/platform/auth/authorization.py` for backward compat
3. Gradually migrate service methods to decorator form — prioritize new services (ActivityService, AuditService enterprise) first
4. Migrate existing services only when touching them for other reasons — do not create pure-refactor PRs

**Do not break existing function-call form** — keep `require_permission()` and `require_any_permission()` at their current import path. The decorator is additive, not a replacement.

---

## 11. Naming Convention

### Python Symbols

| Old name | New name | Layer |
|---|---|---|
| `AuditLogEntry` | `ActivityEntry` | Activity domain |
| `AuditLogRepository` | `ActivityRepository` | Activity contract |
| `AuditService` (UI-facing) | `ActivityService` | Activity service |
| `SqlAlchemyAuditLogRepository` | `SqlAlchemyActivityRepository` | Activity infra |
| `AuditLogORM` (activity table) | `ActivityEntryORM` | Activity ORM |
| `audit_logs` (table) | `activity_entries` (table) | DB |
| `AuditLogEntryDto` (activity) | `ActivityEntryDto` | Activity DTO |
| `PlatformAuditDesktopApi` (activity) | `PlatformActivityDesktopApi` | Activity API adapter |
| `record_audit()` (for activity) | `record_activity()` | Activity helper |
| `build_audit_collection()` | Delete or rename to `build_activity_legacy()` | Presenter |
| `serialize_audit_entries_for_activity()` | `serialize_activity_entries()` | Serializer |
| — | `AuditEntry` | Audit domain (new) |
| — | `AuditRepository` | Audit contract (new) |
| `AuditService` (enterprise) | `AuditService` (same name, new impl) | Audit service |
| — | `SqlAlchemyAuditRepository` | Audit infra (new) |
| — | `AuditEntryORM` | Audit ORM (new) |
| — | `audit_entries` (table) | DB (new) |
| — | `AuditEntryDto` | Audit DTO (new) |
| — | `PlatformAuditDesktopApi` (enterprise) | Audit API (replaced) |
| `record_audit()` (for audit) | `record_audit_entry()` | Audit helper |

### QML / UI Labels

| Old label | New label | Where |
|---|---|---|
| "Audit" (PM Collaboration panel) | Remove or merge into "Activity" | `CollaborationWorkspacePage.qml` |
| "Audit" (AdminAuditSection.qml title) | Keep "Audit" | Platform Admin Console only |
| `panelId: "audit"` (collaboration ViewModels) | Remove | `audit_builder.py` |
| "Comment Trail" (audit collection items) | Move to Activity collection | `audit_builder.py` |

---

## 12. UI Migration Plan

### 12.1 PM Collaboration Workspace

**Current state:**
- `build_audit_collection()` creates a "Audit" panel with notifications + comment trail
- `build_activity_collection()` creates an "Activity" panel (separate)
- Both are shown in `CollaborationWorkspacePage.qml`

**Target:**
- Remove `build_audit_collection()` from the workspace
- Merge its content (notifications + comments) into the Activity section via `build_activity_collection()` — or confirm they are already duplicated there
- Remove "Audit" panel from `CollaborationViewsPopup.qml`
- Keep the Activity section

**Files to change:**
- `src/ui_qml/modules/project_management/presenters/collaboration/workspace_builder.py` — remove `build_audit_collection()` call
- `src/ui_qml/modules/project_management/presenters/collaboration/audit_builder.py` — delete after confirming activity_builder covers the same data
- Confirm `CollaborationWorkspacePage.qml` and `CollaborationViewsPopup.qml` have no hardcoded "Audit" panel references remaining

### 12.2 Inventory Detail Pages

**Current state:**
All five inventory activity handlers call `ctrl._platform_audit.list_recent(entity_type=..., limit=200)` and serialize with `serialize_audit_entries_for_activity()`.

**Target:**
- Wire `_activity_service` into inventory controllers (via `infra/composition/inventory_registry.py`)
- Replace `ctrl._platform_audit.list_recent(...)` with `ctrl._activity_service.list_recent(entity_type=..., entity_id=...)`
- Replace `serialize_audit_entries_for_activity()` with `serialize_activity_entries()` using `ActivityEntryDto`
- Remove `_platform_audit` from inventory controller constructors (or keep for backward compat during transition)

**Files to change:**
- `src/ui_qml/modules/inventory_procurement/controllers/inventory/inventory_activity_handler.py`
- `src/ui_qml/modules/inventory_procurement/controllers/reservations/reservations_activity_handler.py`
- `src/ui_qml/modules/inventory_procurement/controllers/pricing/pricing_activity_handler.py`
- `src/ui_qml/modules/inventory_procurement/controllers/procurement/procurement_activity_handler.py`
- `src/ui_qml/modules/inventory_procurement/controllers/catalog/catalog_activity_handler.py`
- `src/ui_qml/modules/inventory_procurement/controllers/common/serializers/audit_activity_serializer.py` → rename + update

### 12.3 PM Activity Sections (workspace detail pages)

PM workspaces already have `*ActivitySection.qml` components. These should be wired directly to ActivityService for entity-scoped records:
- `ProjectsActivitySection.qml` → load activity for selected project
- `ResourcesActivitySection.qml` → load activity for selected resource
- `FinancialsActivitySection.qml` → load activity for selected cost item/financial
- `TasksCollaborationSection.qml` → load activity for selected task

Each section loads via a controller. Controllers currently use `_platform_audit.list_recent(entity_type=..., limit=...)`. These must be updated to use `ActivityService.list_recent(entity_type=..., entity_id=..., module=...)` after ActivityService is created.

### 12.4 Platform Admin Console — Audit Section

`AdminAuditSection.qml` currently displays `_overview.activityFeed`. This must remain labelled "Audit" and will be wired to the enterprise AuditService in Phase 5.

**Do not change the "Audit" label here.**  
**Do not wire it to ActivityService.**

In Phase 5: create a `PlatformAuditDesktopApi.list_recent()` that reads from `audit_entries` and returns `AuditEntryDto` objects. Wire into the admin workspace controller and `AdminAuditSection.qml`.

---

## 13. API / Presenter / Controller Migration Plan

### 13.1 New ActivityService API

```python
class ActivityService:
    def record(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str,
        module: str,
        workspace_id: str | None = None,
        human_message: str = "",
        details: dict | None = None,
        parent_entity_id: str | None = None,
        type: str = "info",
        visibility: str = "workspace",
        commit: bool = False,
    ) -> ActivityEntry: ...

    def list_recent(
        self,
        limit: int = 200,
        *,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
    ) -> list[ActivityEntry]: ...
        # No require_permission("audit.read") — business users can read their own activity
        # Requires tenant/org context for scoping
```

### 13.2 New PlatformActivityDesktopApi

Replaces the current inventory handler usage of `PlatformAuditDesktopApi`:

```python
class PlatformActivityDesktopApi:
    def list_recent(
        self,
        *,
        limit: int = 200,
        entity_type: str | None = None,
        entity_id: str | None = None,
        module: str | None = None,
        workspace_id: str | None = None,
    ) -> DesktopApiResult[tuple[ActivityEntryDto, ...]]: ...
```

`ActivityEntryDto` fields: id, action, entity_type, entity_id, actor_id, module, timestamp, type, human_message, details, icon, color, visibility.

### 13.3 Enterprise AuditService API (Phase 5)

```python
class AuditService:
    def record(
        self,
        *,
        operation: str,
        entity_type: str,
        entity_id: str,
        module: str,
        field: str | None = None,
        old_value: str | None = None,
        new_value: str | None = None,
        severity: str = "low",
        compliance_tag: str = "none",
        source: str = "api",
        metadata: dict | None = None,
        commit: bool = False,
    ) -> AuditEntry: ...

    def list_recent(
        self,
        limit: int = 500,
        *,
        entity_type: str | None = None,
        operation: str | None = None,
        severity: str | None = None,
        compliance_tag: str | None = None,
    ) -> list[AuditEntry]: ...
        # Requires "audit.read" permission — admin only
```

---

## 14. Test Plan

### 14.1 Activity Tests

| Test | Verifies |
|---|---|
| `test_activity_entry_created_on_task_create` | ActivityService.record() called after task.create |
| `test_activity_scoped_by_entity` | list_recent(entity_id=X) returns only X's activity |
| `test_activity_scoped_by_tenant` | activity from tenant A not visible to tenant B |
| `test_activity_no_permission_required_for_business_user` | list_recent() does NOT require audit.read |
| `test_activity_human_message_populated` | human_message is non-empty |
| `test_inventory_detail_page_shows_activity` | inventory activity handler returns ActivityEntryDto |
| `test_pm_collaboration_shows_no_audit_label` | build_audit_collection not in workspace |

### 14.2 Audit Tests

| Test | Verifies |
|---|---|
| `test_audit_entry_created_on_login` | AuditService.record() called for auth.login with operation="login" |
| `test_audit_entry_created_on_failed_login` | auth.failed_login → severity="high" |
| `test_audit_append_only` | No update() or delete() methods exist on AuditRepository |
| `test_audit_requires_audit_read_permission` | list_recent() raises PERMISSION_DENIED without audit.read |
| `test_audit_not_visible_in_pm_workspaces` | No AuditService in PM controller constructors |
| `test_audit_field_level_tracking` | old_value / new_value populated for update operations |
| `test_audit_compliance_tag_recorded` | compliance_tag persisted correctly |

### 14.3 RBAC Decorator Tests

| Test | Verifies |
|---|---|
| `test_requires_permission_blocks_without_permission` | @requires_permission raises PERMISSION_DENIED |
| `test_requires_permission_passes_with_permission` | @requires_permission allows through |
| `test_requires_any_permission` | Passes if user has any of listed codes |
| `test_requires_all_permissions` | Fails if user is missing any of listed codes |

### 14.4 Migration Tests

| Test | Verifies |
|---|---|
| `test_activity_entries_table_exists` | activity_entries table created by migration |
| `test_audit_entries_table_exists` | audit_entries table created by migration |
| `test_backfill_excludes_auth_events` | auth.login records NOT in activity_entries after backfill |
| `test_backfill_includes_business_events` | task.create records IN activity_entries after backfill |
| `test_audit_logs_intact_after_migration` | audit_logs not modified by new migrations |

---

## 15. Execution Phases

### Phase 1 — Discovery (COMPLETE)

- Full audit/activity/RBAC scan ✓
- Classification of current usages ✓
- Codebase map ✓
- Produce `docs/ACTIVITY_AUDIT_SECURITY_ROADMAP.md` ✓

### Phase 2 — Documentation Review (COMPLETE)

- Plan reviewed and approved ✓
- Classification decisions confirmed ✓
- Database migration option B confirmed ✓
- Helper function approach confirmed for Phase 3 ✓

### Phase 3 — Activity Foundation (COMPLETE)

**Goal:** Create ActivityEntry/ActivityService/ActivityRepository and wire PM + Inventory to it.

Completed:
1. ✓ `src/core/platform/activity/domain/activity_entry.py` — `ActivityEntry` dataclass
2. ✓ `src/core/platform/activity/contracts.py` — `ActivityRepository` ABC
3. ✓ `src/core/platform/activity/application/activity_service.py` — `ActivityService`
4. ✓ `src/core/shared/activity/activity_recorder.py` — `record_activity()` helper
5. ✓ `src/core/platform/infrastructure/persistence/orm/activity.py` — `ActivityEntryORM`
6. ✓ `src/core/platform/infrastructure/persistence/mappers/activity.py` — mappers
7. ✓ `src/core/platform/infrastructure/persistence/repositories/activity.py` — `SqlAlchemyActivityRepository`
8. ✓ `src/api/desktop/platform/activity.py` — `PlatformActivityDesktopApi`
9. ✓ `src/api/desktop/platform/models/activity.py` — `ActivityEntryDto`
10. ✓ `ActivityService` wired into `ServiceGraph`, `platform_registry.py`, `app_container.py`, `runtime.py`
11. ✓ All business-ops `record_audit()` → `record_activity()` migrations:
    - `task/commands/lifecycle.py` (task.create, task.set_status, task.delete, task.update, task.update_progress)
    - `task/commands/assignment_audit.py` (task.assign, task.unassign)
    - `task/commands/dependency.py` (dependency.add, dependency.remove, dependency.update)
    - `projects/commands/lifecycle.py` (project.create, project.set_status, project.update, project.delete)
    - `resources/commands/resource_commands.py` (resource.create, resource.update, resource.delete)
    - `resources/commands/project_resource_commands.py` (project_resource.add, project_resource.update, project_resource.set_active, project_resource.delete)
    - `financials/costs/commands/cost_lifecycle.py` (cost.add, cost.update, cost.delete)
    - `risk/commands/register_lifecycle.py` (register.create, register.update, register.delete)
    - `scheduling/baselines/baseline_service.py` (baseline.create, delete, submit, approve, reject)
    - `portfolio/commands/portfolio_dependencies.py` (portfolio.project_dependency.add, portfolio.project_dependency.remove)
    - `inventory/application/catalog/catalog_audit.py` (6 inventory catalog operations)
12. ✓ `ActivityService` wired into PM services via `project_registry.py`: project_service, task_service, project_resource_service, register_service, resource_service, cost_service, baseline_service
13. ✓ `ActivityService` wired into Inventory services via `inventory_registry.py`: ItemCategoryService, ItemMasterService
14. ✓ Inventory activity handlers rewritten to use `_activity_api` (not `_platform_audit`): catalog, inventory, reservations, pricing, procurement
15. ✓ `serialize_audit_entries_for_activity()` → `serialize_activity_entries()` in all serializer/handler files
16. ✓ `PlatformActivityDesktopApi` registered in `DesktopApiRegistry` and `runtime.py`

**Test gate:** 189 PM tests pass (13 pre-existing data integrity failures unrelated to this work). ✓

### Phase 4 — Remove Audit Labels from Business Modules (COMPLETE)

**Goal:** No "Audit" labels visible in PM Collaboration workspace.

Completed:
1. ✓ Removed `build_audit_collection()` call and `audit_feed` variable from `workspace_builder.py`
2. ✓ Deleted `audit_builder.py`
3. ✓ Removed `audit_feed` field from `CollaborationWorkspaceViewModel`
4. ✓ Removed `audit_feed` param from `build_context_view_model()` and `build_workspace_empty_state()` in `context_builder.py`
5. ✓ Removed `auditPanelModel`, `auditSearchText`, `_auditFeedItems`, and all `"audit"` branches from `CollaborationWorkspaceState.qml`
6. ✓ Removed all `"audit"` panel conditions from `CollaborationWorkspacePage.qml`; activity feed now always uses `_activityFeedItems`
7. ✓ Removed "Audit Trail" entry from `CollaborationViewsPopup.qml`
8. ✓ `AdminAuditSection.qml` (Platform Admin Console) confirmed untouched

**Test gate:** 57 collaboration/presenter/workspace tests pass. No `audit_feed`/`audit_builder` references remain in PM presenter or QML workspace layer. ✓

### Phase 5 — Enterprise Audit Foundation (COMPLETE)

**Goal:** Create true AuditEntry/AuditService and wire Platform Admin Console to it.

1. `AuditEntry` dataclass added to `src/core/platform/audit/domain/audit_entry.py` ✓
2. `AuditRepository` ABC added to `src/core/platform/audit/contracts.py` ✓
3. `EnterpriseAuditService` created at `src/core/platform/audit/application/enterprise_audit_service.py` ✓
4. `record_audit_entry()` helper created at `src/core/shared/audit/audit_recorder.py` ✓
5. `AuditEntryORM` → `audit_entries` table created at `src/core/platform/infrastructure/persistence/orm/audit_entry.py` ✓
6. Mapper functions created at `src/core/platform/infrastructure/persistence/mappers/audit_entry.py` ✓
7. `SqlAlchemyAuditRepository` created at `src/core/platform/infrastructure/persistence/repositories/audit_entry.py` ✓
8. `PlatformEnterpriseAuditDesktopApi` created at `src/api/desktop/platform/audit_enterprise.py` ✓
9. `AuditEntryDto` created at `src/api/desktop/platform/models/audit_entry.py` ✓
10. `record_auth_event()` migrated — tries `_enterprise_audit_service` first, falls back to `_audit_service` ✓
11. `AuthService.__init__` gains `enterprise_audit_service` param ✓
12. `RepositoryBundle` gains `audit_entry_repo: SqlAlchemyAuditRepository` ✓
13. `PlatformServiceBundle` gains `enterprise_audit_service: EnterpriseAuditService`; created alongside `AuditService` ✓
14. `DesktopApiRegistry` gains `platform_enterprise_audit: PlatformEnterpriseAuditDesktopApi | None` ✓
15. `PlatformWorkspaceOverviewViewModel` gains `activityFeed: tuple[dict, ...]` ✓
16. `serialize_workspace_overview()` includes `"activityFeed"` key ✓
17. `PlatformAdminWorkspacePresenter` gains `audit_api` param; populates `activityFeed` in `build_overview()` ✓
18. `PlatformWorkspaceCatalog` wires `platform_enterprise_audit` → `audit_api` on the admin presenter ✓
19. All new symbols exported via `__init__.py` files ✓

**Test gate:** Auth events appear in admin audit view. PM/Inventory activity not in audit view. Append-only contract test passes.

### Phase 6 — Architecture Cleanup & Simplification

**Goal:** Remove obsolete code, duplicate validations, legacy audit wiring, and temporary migration artifacts after the Activity/Audit split and tenant hardening work are complete.

#### 6.1 Repository Cleanup

- [ ] Remove unsafe repository methods:
  - `list_all()`
  - `get_all()`
  - `search_all()`
  - `count_all()`
  - Other unscoped global queries

- [ ] Remove temporary tenant migration helpers no longer required.

- [ ] Verify all repository CRUD operations are tenant-scoped.

- [ ] Verify all organization-owned entities are organization-scoped.

- [ ] Remove legacy compatibility wrappers created during tenant migration.

---

#### 6.2 Service Cleanup

- [ ] Remove duplicate tenant/organization ownership checks already enforced by repositories.

Examples:

- `_is_project_in_active_organization()`
- `_is_task_in_active_organization()`
- `_is_resource_in_active_organization()`
- `_is_*_in_active_context()`

**Rule:**

```text
Repository = Security Boundary
Service = Business Rules
````

Keep:

* Workflow validation
* Status transition validation
* Approval validation
* Capacity validation
* Scheduling validation
* Business-rule enforcement

Remove:

* Duplicate tenant validation
* Duplicate organization validation
* Duplicate ownership validation

---

#### 6.3 Activity / Audit Cleanup

* [ ] Remove obsolete audit infrastructure replaced by Activity.

Examples:

* `record_audit()`

* `audit_builder.py`

* `build_audit_collection()`

* `serialize_audit_entries_for_activity()`

* [ ] Rename remaining activity-related audit code to Activity equivalents.

* [ ] Verify no Activity functionality depends on Audit implementations.

---

#### 6.4 Presenter / Controller Cleanup

Remove obsolete Audit presenters/controllers from business modules.

Examples:

* `AuditController`
* `AuditPresenter`
* `AuditDto`
* `AuditFeed`
* `AuditCollection`

Modules:

* Project Management
* Inventory & Procurement
* Maintenance

Tasks:

* [ ] Replace with Activity implementations where applicable.
* [ ] Remove obsolete wiring.
* [ ] Keep Audit placeholder only in Admin Console / Control Center.

---

#### 6.5 QML Cleanup

Scan all QML files for:

```text
Audit
audit
auditFeed
auditCollection
auditPanel
auditSection
```

Rules:

* Project Management → Activity only
* Inventory & Procurement → Activity only
* Maintenance → Activity only
* Platform Admin Console → Audit

Tasks:

* [ ] Remove obsolete Audit UI.
* [ ] Replace with Activity sections where required.
* [ ] Verify Activity sections load entity-scoped records only.

---

#### 6.6 Helper & Utility Cleanup

Audit helper files:

```text
*_helper.py
*_builder.py
*_handler.py
*_mixin.py
```

Tasks:

* [ ] Remove single-use helpers.
* [ ] Remove obsolete migration helpers.
* [ ] Consolidate reusable logic into shared services.

Rule:

```text
Keep helper only if:
- Used by multiple bounded contexts
- Provides reusable business logic
```

---

#### 6.7 Dead Code Audit

Generate a report for every deletion candidate:

| File | Used By | Replacement | Safe To Delete |
| ---- | ------- | ----------- | -------------- |

Tasks:

* [ ] Remove unused DTOs.
* [ ] Remove unused ViewModels.
* [ ] Remove unused Builders.
* [ ] Remove unused Serializers.
* [ ] Remove unused Controllers.
* [ ] Remove unused Presenters.
* [ ] Remove unused Helpers.
* [ ] Remove orphan imports and references.

---

#### 6.8 Dependency & Wiring Cleanup

Tasks:

* [ ] Verify API → Presenter → Controller → QML wiring remains valid.
* [ ] Remove obsolete Activity/Audit compatibility layers.
* [ ] Remove deprecated service registrations.
* [ ] Remove unused dependency injection registrations.
* [ ] Verify application startup remains clean.

---

#### 6.9 Final Architecture Validation

Target architecture:

```text
Repository
    ↓
Service
    ↓
Desktop API
    ↓
Presenter
    ↓
Controller
    ↓
QML
```

Verify:

* [ ] No duplicate validation layers.
* [ ] No legacy audit chains.
* [ ] No redundant helper chains.
* [ ] No orphaned Activity/Audit wiring.
* [ ] No service-layer ownership checks already enforced by repositories.

---

#### 6.10 Final Verification

Verify:

* [ ] No Audit UI remains in Project Management.
* [ ] No Audit UI remains in Inventory & Procurement.
* [ ] No Audit UI remains in Maintenance.
* [ ] Activity sections function correctly.
* [ ] Admin Console Audit remains available.
* [ ] Tenant isolation remains enforced.
* [ ] Organization isolation remains enforced.
* [ ] All tests pass.
* [ ] No dead code remains.

#### Deliverables

* Architecture cleanup report
* Dead code report
* Dependency cleanup report
* Removed file inventory
* Final validation report

```

### Phase 7 — RBAC Decorators

**Goal:** Create shared security decorator form.

Steps:
1. Create `src/core/shared/security/decorators.py` with `@requires_permission`, `@requires_any_permission`, `@requires_all_permissions`
2. Create `src/core/shared/security/permissions.py` with `Permissions` constant class
3. Re-export from `src/core/platform/auth/authorization.py` for backward compat
4. Apply decorator form to new services (ActivityService, enterprise AuditService) first
5. Gradually adopt in existing services — no flag-day migration

**Test gate:** Decorator tests pass. No existing function-call imports broken.

### Phase 8 — Database Migrations

**Goal:** Create `activity_entries` and `audit_entries` tables and backfill.

Steps:
1. Write Alembic migration: create `activity_entries` (Migration A)
2. Write Alembic migration: create `audit_entries` (Migration B)
3. Write Alembic migration: backfill `audit_logs` → `activity_entries` (Migration C) — business events only
4. Write Alembic migration: backfill `audit_logs` security events → `audit_entries` (Migration D)
5. Write Alembic migration: drop `audit_logs` (Migration E) — run LAST, after Phase 3/5 complete

**Each migration is a separate Alembic revision.** Migrations A and B are independent and can be applied together. Migrations C and D depend on A and B respectively. Migration E depends on all prior phases and code migrations being complete.

### Phase 9 — Tests

**Goal:** Full test coverage for new systems.

Steps:
1. Activity visibility tests (entity scoping, tenant scoping)
2. Audit immutability tests (append-only contract)
3. RBAC decorator tests
4. Tenant isolation tests for both systems
5. UI wiring tests (no "Audit" in PM collaboration)
6. Migration integrity tests

---

## 16. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Breaking `audit_logs` FK references during rename/drop | High | Keep `audit_logs` intact throughout; only drop in final Migration E after verifying zero code references |
| Inventory controllers losing activity data during cutover | High | Keep `_platform_audit` as fallback in controllers until `_activity_service` is confirmed working; use try/fallback pattern during transition |
| `build_audit_collection()` removal breaks QML if there's a hidden reference | Medium | Search all QML files for `"audit"` before deleting the builder; also grep Python presenters |
| `require_permission("audit.read")` currently gates inventory activity | High | Phase 3 ActivityService.list_recent() must NOT require audit.read — different permission or no permission gate for own-entity reads |
| Auth events lost during transition (auth_recorder → enterprise audit) | High | Do not touch `audit_recorder.py` until enterprise AuditService is confirmed working; transition in Phase 5 only |
| New `activity_entries` / `audit_entries` tables missing tenant isolation | Medium | Both schemas include `tenant_id` from day 1; repository queries must always filter by tenant_id |
| Tests targeting `AuditLogEntry` break when domain model is renamed | Medium | Keep `AuditLogEntry` as an alias until all tests are updated; do not rename in a single commit |
| `AdminAuditSection.qml` accidentally wired to ActivityService | Medium | Explicit rule: AdminAuditSection controller references ONLY AuditService (enterprise), never ActivityService |
| Decorator form causes unexpected silent failures | Low | Decorator must log warnings when activity/audit service is None — do not silently pass in production |
| Overlong migration backfill on large datasets | Low | Migration C/D use batched INSERTs (1000 rows at a time); provide rollback step in Alembic downgrade |

---

## Appendix A — Complete File Inventory by System

### Files That Become Activity System

```
src/core/activity/                           # NEW
src/core/shared/activity/                    # NEW
src/core/platform/infrastructure/persistence/orm/activity.py        # NEW
src/core/platform/infrastructure/persistence/mappers/activity.py    # NEW
src/core/platform/infrastructure/persistence/repositories/activity.py # NEW
src/api/desktop/platform/activity.py        # NEW
src/api/desktop/platform/models/activity.py # NEW
src/ui_qml/modules/inventory_procurement/controllers/common/serializers/activity_serializer.py  # RENAMED

# Records converted to record_activity():
src/core/modules/project_management/application/tasks/commands/lifecycle.py
src/core/modules/project_management/application/tasks/commands/assignment_audit.py
src/core/modules/project_management/application/tasks/commands/dependency.py
src/core/modules/project_management/application/projects/commands/lifecycle.py
src/core/modules/project_management/application/resources/commands/resource_commands.py
src/core/modules/project_management/application/financials/costs/commands/cost_lifecycle.py
src/core/modules/project_management/application/risk/commands/register_lifecycle.py
src/core/modules/inventory_procurement/application/catalog/catalog_audit.py
# + reservation, requisition, purchase order service files
```

### Files That Become Audit System

```
src/core/platform/audit/domain/audit_entry.py         # REPLACED (new schema)
src/core/platform/audit/contracts.py                   # REPLACED (AuditRepository)
src/core/platform/audit/application/audit_service.py  # REPLACED (enterprise)
src/core/shared/audit/                                 # NEW
src/core/platform/infrastructure/persistence/orm/audit_entry.py        # NEW
src/core/platform/infrastructure/persistence/repositories/audit_entry.py # NEW
src/api/desktop/platform/audit_enterprise.py           # NEW / REPLACES current audit.py
src/api/desktop/platform/models/audit_entry.py         # NEW

# Records converted to record_audit_entry():
src/core/platform/auth/application/audit_recorder.py  # UPDATED
# + future: user_service, role_service, permission_service
```

### Files That Are Deleted (after migration)

```
src/ui_qml/modules/project_management/presenters/collaboration/audit_builder.py
src/ui_qml/modules/inventory_procurement/controllers/common/serializers/audit_activity_serializer.py
```

### Files That Keep "Audit" Label (do not rename)

```
src/ui_qml/platform/qml/workspaces/admin/sections/AdminAuditSection.qml
# Admin Console audit placeholder — intentionally keeps "Audit" branding
```

---

*This document is the planning artifact for the Activity / Audit / Security split. Implementation begins only after this plan is reviewed and approved.*
