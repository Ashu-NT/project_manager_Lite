# 11. DELIVERABLE 6 — DATA OWNERSHIP MODEL

---

## 11.1 Ownership Level Definitions

The codebase recognises eight discrete ownership levels. Each level defines the authoritative scope at which an entity is created, governed, and deleted. These levels form a strict hierarchy; data at a lower level always falls within the boundary of the level above it and can never exist outside that boundary.

| # | Ownership Level | Definition |
|---|-----------------|------------|
| 1 | **GLOBAL** | Entity belongs to the platform itself and is shared across all tenants and organisations. No tenant_id or org_id column is present. Changes to global entities affect every tenant simultaneously. Includes the identity primitives: `users`, `roles`, `permissions`, `role_permissions`. |
| 2 | **TENANT** | Entity carries a `tenant_id NOT NULL` column that directly binds it to one tenant. The tenant boundary is the outermost hard isolation wall. No cross-tenant read or write is ever permitted regardless of user privilege. Includes organisational structure tables, audit machinery, document management, scheduling primitives, resource pools, portfolio constructs, module entitlements, and all domain tables that are owned at the tenant level (inventory, maintenance roots, etc.). |
| 3 | **ORGANIZATION** | Entity carries both `tenant_id` and `organization_id`, placing it inside a specific organisation within a tenant. The organisation boundary controls which business unit owns and operates the data. The primary example is `projects`, which are owned by an organisation but are hard-scoped to its parent tenant. |
| 4 | **SITE** | Entity is scoped to a physical or logical site within a tenant. `departments` are associated with a site, meaning their lifecycle and visibility follow site boundaries in addition to tenant boundaries. |
| 5 | **DEPARTMENT** | Entity is scoped to a department within a site and organisation. `employees` belong to a department, establishing the most granular unit of the organisational hierarchy (Tenant → Organization → Site → Department → Employee). |
| 6 | **PROJECT** | Entity has no direct `tenant_id` column but inherits tenant scope through its parent project. All project sub-entities (`tasks`, `task_assignments`, `project_resources`, `baselines`, `baseline_tasks`, `cost_items`, `register_items`, `collaboration_threads`) obtain their security and lifecycle boundaries entirely from the project that owns them. Deletion of the project cascades through the entire project scope. |
| 7 | **ASSET** | Entity has no direct `tenant_id` column but inherits tenant scope through its parent asset or work order. Maintenance sub-entities (`work_order_tasks`, `asset_components`, `sensor_readings`) are owned by a specific maintenance asset or work order rather than by an organisation or project. The asset scope is orthogonal to the inventory scope and is not interchangeable with it. |
| 8 | **USER** | Entity stores per-session metadata for a specific user. `auth_sessions` carry `last_active_tenant_id` and `last_active_organization_id` as informational fields only. These values describe the user's last known context but are non-authoritative: they do not grant, restrict, or imply any access rights and are never used as a security predicate. |

---

## 11.2 Complete Entity Classification Table

The table below classifies every entity in the codebase. The **Mechanism** column describes how the ownership boundary is enforced at the data layer. The **Security Boundary** column identifies the principal required to operate on the entity. The **Lifecycle Boundary** column identifies what drives creation and deletion. The **Parent Entity** column names the direct owner.

| Entity | Ownership Level | Mechanism | Security Boundary | Lifecycle Boundary | Parent Entity |
|--------|----------------|-----------|-------------------|--------------------|---------------|
| `users` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `roles` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `permissions` | GLOBAL | No tenant_id / org_id column | Platform administrator | Platform provisioning | Platform |
| `role_permissions` | GLOBAL | No tenant_id / org_id column | Platform administrator | Role lifecycle | `roles` + `permissions` |
| `user_roles` | GLOBAL + nullable org FK | No tenant_id; optional organization_id FK | Platform administrator / org admin (when org-scoped) | Role assignment lifecycle | `users` + `roles` |
| `auth_sessions` | USER | Carries last_active_tenant_id / last_active_organization_id as metadata only (non-authoritative) | User (self only) | User session lifecycle | `users` |
| `organizations` | TENANT | `tenant_id NOT NULL` | Tenant administrator | Tenant provisioning | Tenant |
| `sites` | TENANT | `tenant_id NOT NULL` (plus org FK) | Tenant / org administrator | Organisation lifecycle | `organizations` |
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
| `scoped_access_grants` | TENANT | `tenant_id NOT NULL`; scope_type + scope_id + user_id + scope_role + permission_codes_json | Tenant / org administrator | Scope object lifecycle | Tenant + scope object |
| `projects` | ORGANIZATION | `tenant_id NOT NULL` + `organization_id` FK | Org administrator / project manager | Organisation lifecycle | `organizations` |
| `tasks` | PROJECT | No tenant_id; scoped through parent project | Project manager / task assignee | Project lifecycle | `projects` |
| `task_assignments` | PROJECT | No tenant_id; scoped through parent task | Project manager | Task lifecycle | `tasks` |
| `project_resources` | PROJECT | No tenant_id; join of project + resource | Project manager | Project lifecycle | `projects` + `resources` |
| `project_baselines` | PROJECT | No tenant_id; scoped through parent project | Project manager | Project lifecycle | `projects` |
| `baseline_tasks` | PROJECT | No tenant_id; scoped through parent baseline | Project manager | Baseline lifecycle | `project_baselines` |
| `cost_items` | PROJECT | No tenant_id; scoped through parent project | Project manager / finance admin | Project lifecycle | `projects` |
| `register_items` | PROJECT | No tenant_id; scoped through parent project | Project manager | Project lifecycle | `projects` |
| `collaboration_threads` | PROJECT | No tenant_id; scoped through parent project | Project member | Project lifecycle | `projects` |
| `project_memberships` | PROJECT | No tenant_id; project_id + user_id + organization_id + scope_role + permission_codes_json | Project manager / org admin | Project lifecycle | `projects` |
| `portfolio_calendar_assignments` | PROJECT (scope-inherited) | No tenant_id; scoped through portfolio/project reference | Portfolio manager | Portfolio lifecycle | Portfolio / `projects` |
| `inventory_items` | TENANT | `tenant_id NOT NULL` | Inventory manager / tenant admin | Tenant lifecycle | Tenant |
| `storerooms` | TENANT | `tenant_id NOT NULL` | Inventory manager / org admin | Tenant lifecycle | Tenant |
| `purchase_orders` | TENANT | `tenant_id NOT NULL` | Procurement manager / org admin | Tenant lifecycle | Tenant |
| `po_receipts` | TENANT | `tenant_id NOT NULL` | Warehouse / procurement staff | Purchase order lifecycle | `purchase_orders` |
| `inventory_reservations` | TENANT | `tenant_id NOT NULL` | Inventory manager / project manager | Tenant lifecycle | Tenant |
| `item_catalog_entries` | TENANT | `tenant_id NOT NULL` | Inventory / catalog administrator | Tenant lifecycle | Tenant |
| `inventory_lots` | TENANT (scope-inherited in sub-context) | `tenant_id NOT NULL` on root; lot records inherit via item/storeroom | Inventory manager | Item / storeroom lifecycle | `inventory_items` / `storerooms` |
| `reservation_lines` | TENANT (scope-inherited) | No direct tenant_id; scoped through parent reservation | Inventory manager | Reservation lifecycle | `inventory_reservations` |
| `assets` | TENANT | `tenant_id NOT NULL` | Maintenance manager / org admin | Tenant lifecycle | Tenant |
| `work_orders` | TENANT | `tenant_id NOT NULL` | Maintenance manager / org admin | Tenant lifecycle | Tenant |
| `work_requests` | TENANT | `tenant_id NOT NULL` | Any authorised user / maintenance manager | Tenant lifecycle | Tenant |
| `sensors` | TENANT | `tenant_id NOT NULL` | Maintenance / IoT administrator | Tenant lifecycle | Tenant |
| `reliability_records` | TENANT | `tenant_id NOT NULL` | Maintenance engineer / org admin | Tenant lifecycle | Tenant |
| `preventive_maintenance_plans` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `preventive_maintenance_templates` | TENANT | `tenant_id NOT NULL` | Maintenance manager | Tenant lifecycle | Tenant |
| `work_order_tasks` | ASSET | No tenant_id; scoped through parent work order → asset | Maintenance technician / manager | Work order lifecycle | `work_orders` |
| `asset_components` | ASSET | No tenant_id; scoped through parent asset | Maintenance manager | Asset lifecycle | `assets` |
| `sensor_readings` | ASSET | No tenant_id; scoped through parent sensor → asset | IoT pipeline / maintenance system | Sensor lifecycle | `sensors` |

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
└── portfolio_calendar_assignments     ← scope-inherited via portfolio/project ref

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

ACCESS / IDENTITY
└── [see GLOBAL: user_roles, scoped_access_grants, project_memberships above]

USER  (session metadata — non-authoritative)
└── auth_sessions
    ├── last_active_tenant_id          (informational metadata only)
    └── last_active_organization_id    (informational metadata only)
```

---

## 11.4 Security Boundary Analysis

The table below defines who is authorised to perform create, read, update, and delete operations at each ownership level. "Platform admin" denotes a super-administrator with cross-tenant reach. "Tenant admin" operates within one tenant. "Org admin" operates within one organisation. All principals are subject to the ownership level above them.

| Ownership Level | Create | Read | Update | Delete |
|-----------------|--------|------|--------|--------|
| **GLOBAL** | Platform administrator only | Platform administrator; read-only subsets exposed to tenant/org admins for role assignment | Platform administrator only | Platform administrator only; deletion of a role or permission is a breaking operation requiring platform-level approval |
| **TENANT** | Platform administrator (tenant provisioning) or tenant administrator for sub-entities | Tenant administrator and any principal whose resolved tenant_id matches the record's tenant_id | Tenant administrator (structural entities); authorised org/department principals for domain entities within their scope | Tenant administrator; cascade deletes all child entities within the tenant boundary |
| **ORGANIZATION** | Tenant administrator or organisation administrator with appropriate module entitlement | Organisation administrator and any member whose resolved organization_id matches the record; always filtered by parent tenant_id | Organisation administrator or project manager (for projects) | Organisation administrator; cascades through all project-scoped children |
| **SITE** | Tenant / organisation administrator | Organisation and site administrators; any employee or department within the site | Site administrator | Organisation / tenant administrator; cascades through departments and employees |
| **DEPARTMENT** | Organisation / site administrator | Department administrator; any employee assigned to the department | Department administrator | Site / org administrator; cascades through employee assignments |
| **PROJECT** | Organisation administrator or project manager (subject to module entitlement) | Project members (via project_memberships and scoped_access_grants); scope_role determines read depth | Project manager; specific sub-entity owners (e.g., task assignees may update their own tasks) | Project manager or organisation administrator; cascades through all scope-inherited project children |
| **ASSET** | Maintenance manager or authorised technician within tenant | Maintenance team members whose tenant resolves correctly; IoT pipeline for sensor_readings | Maintenance technician (for work_order_tasks); maintenance manager (for asset_components); automated pipeline (for sensor_readings) | Maintenance manager; work_order_task deletion follows work order closure; asset_components follow asset archival; sensor_readings may be pruned by retention policy |
| **USER** | System only (created on authentication) | User (self only); platform administrator for audit purposes | System only (last_active fields updated by authentication machinery) | System on session expiry or explicit logout; no business logic may delete another user's session |

---

## 11.5 Lifecycle Boundary Analysis

| Ownership Level | Created When | Archived When | Deleted When | Parent Deletion Cascade |
|-----------------|-------------|--------------|-------------|-------------------------|
| **GLOBAL** | Platform is provisioned; roles and permissions are seeded at deployment; users are created on registration or SSO provisioning | Roles and permissions are not archived; users may be deactivated (soft delete) | Platform administrator explicitly removes the record; user deletion is a deliberate offboarding action | No parent; deletion of a role cascades to role_permissions and user_roles |
| **TENANT** | Tenant administrator provisions a new organisation, site, department, or domain record; system creates audit_logs on any write event | Tenant-level entities may be soft-archived (status flag) when a business unit is decommissioned | Tenant administrator explicitly deletes the record; bulk deletion occurs when the tenant itself is deprovisioned | Deletion of the tenant cascades to all TENANT-level entities across all domains; this is an irreversible platform operation |
| **ORGANIZATION** | Organisation administrator creates a project; platform administrator creates an organisation | Projects may be archived on completion; organisations may be suspended without deletion | Organisation administrator deletes the project; tenant administrator deletes the organisation | Deletion of an organisation cascades to all its projects; deletion of a project cascades to all PROJECT-scoped children |
| **SITE** | Organisation / tenant administrator creates a site | Site may be decommissioned (soft archive) | Org / tenant administrator deletes the site | Deletion cascades to departments and their employees |
| **DEPARTMENT** | Site / org administrator creates a department | Department may be merged or archived | Org / site administrator deletes the department | Deletion cascades to employee department assignments |
| **PROJECT** | Project manager or org admin initiates a new project | Project is marked complete or on-hold; baselines snapshot state at a point in time | Project manager or org admin hard-deletes the project (rare; usually archived) | Cascade deletes tasks, task_assignments, project_resources, baselines, baseline_tasks, cost_items, register_items, collaboration_threads, project_memberships, portfolio_calendar_assignments |
| **ASSET** | Maintenance manager registers an asset, raises a work order, or adds a sensor | Assets may be decommissioned; work orders are closed on completion | Maintenance manager archives or deletes the root entity | Deletion of an asset cascades to asset_components and related sensor_readings; deletion of a work order cascades to work_order_tasks; deletion of a sensor cascades to its sensor_readings |
| **USER** | Authentication machinery creates a session on login | Sessions are not archived | Session expires (TTL) or user logs out explicitly; platform admin may invalidate sessions | No child entities; last_active fields are metadata with no downstream cascade |

---

## 11.6 Design Principles

The following seven principles govern data ownership in this codebase. They are architectural invariants; violations constitute a security defect, not a design trade-off.

**1. Tenant isolation is the outermost hard boundary.**
Every entity that belongs to a tenant carries `tenant_id NOT NULL` as a direct column, or inherits tenant scope through an unbroken chain of foreign-key relationships to a tenant-scoped parent. No query, API endpoint, background job, or migration may return data from more than one tenant in the same result set. The tenant filter is applied at the repository layer before any other predicate and is never made optional by caller-supplied arguments.

**2. Scope inheritance never crosses tenant boundaries.**
Entities that inherit scope from a parent (e.g., tasks inherit from projects, work_order_tasks inherit from work_orders) do so through a chain that always terminates at a TENANT-level root. The inheritance chain is validated at write time: a child entity cannot be associated with a parent that belongs to a different tenant, even if both tenants are accessible to the same platform administrator. Cross-tenant foreign-key relationships are structurally prohibited.

**3. Direct tenant_id columns and inherited scope are enforced with equal rigour.**
The absence of a `tenant_id` column on a scope-inherited entity (e.g., `tasks`, `sensor_readings`) does not represent a weaker security posture. The owning service resolves the tenant through the parent chain and applies the same isolation predicate. Repositories for scope-inherited entities receive a resolved tenant context from the caller and must validate it against the parent before executing any DML.

**4. Platform-global entities must never carry tenant context.**
`users`, `roles`, `permissions`, and `role_permissions` have no `tenant_id` column and must never have one added. Global entities are shared infrastructure. Tenant-specific behaviour is achieved through `user_roles` (with its nullable `organization_id` FK), `scoped_access_grants`, and `project_memberships`, all of which carry the tenant context externally without contaminating the global identity tables.

**5. Session metadata is non-authoritative for access control.**
`auth_sessions.last_active_tenant_id` and `auth_sessions.last_active_organization_id` are convenience metadata fields that record the user's last known context. They are written by the authentication machinery and may be stale. No access-control decision, data filter, or audit record may use these fields as a source of truth. Authoritative tenant and organisation context must be derived from the verified token claim or explicit request parameter, validated against `scoped_access_grants` or `project_memberships`.

**6. Project membership scope is independent of the organisational hierarchy.**
A user's membership in a project (via `project_memberships`) grants rights within that project's boundary regardless of whether the user holds a role in the parent organisation. Conversely, holding an organisational role does not automatically grant membership in all projects under that organisation. The two access axes — organisational hierarchy and project scope — are evaluated independently, and neither subsumes the other. `ScopedAccessGrant` provides the bridge when cross-scope delegation is required.

**7. Asset scope and inventory scope are orthogonal and must not be conflated.**
The maintenance domain (assets, work orders, sensors, and their scope-inherited children) and the inventory domain (inventory items, storerooms, purchase orders, and their scope-inherited children) are both rooted at the TENANT level but represent independent ownership trees. An `asset_component` is owned by an `asset`, not by an `inventory_item`, even if it references one. A `reservation_line` is owned by an `inventory_reservation`, not by a project or a work order. Services operating across domain boundaries must resolve each entity through its own ownership chain independently; they must not assume that a relationship between two entities implies shared ownership scope.
