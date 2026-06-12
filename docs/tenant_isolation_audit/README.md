# Tenant Isolation Architecture Audit

Status: Authoritative tenant-isolation architecture reference. Implementation must continue only against the target architecture defined here.

This document captures the required multi-tenant posture for the modular SaaS codebase across Platform, Project Management, Inventory & Procurement, and Maintenance. `Organization` is the tenant boundary. Data from one organization must never be visible, queryable, exportable, cached into, reported with, refreshed into, counted for, or processed inside another organization's runtime context.

This is not a standalone module plan. Tenant isolation is a platform-wide runtime architecture concern.

## Executive Finding

The repository already has many organization-scoped foundations, especially in Platform, Inventory & Procurement, Maintenance, and several Project Management roots. The remaining risk is architectural consistency: runtime tenant selection must be explicit per user/session and must not rely on a globally active organization row.

The target runtime architecture is:

```text
UserSession
  -> TenantContext
  -> Repository
  -> Database
```

`Organization.is_active` is an organization lifecycle/admin state only. It is not runtime tenant selection.

The second largest risk is uneven tenant ownership and enforcement. Several workflow/runtime records and PM operational roots either lack direct `organization_id` ownership or still rely on inherited ownership without repository-level guardrails. Approval requests and audit logs are `CRITICAL` risk because they are frequently displayed globally and cross-tenant leakage would be a major security incident.

## Scope Inspected

The discovery pass inspected the platform foundation, Project Management, Inventory & Procurement, Maintenance, shared approval/audit/document/time services, QML controllers/presenters, dashboard/report/export paths, background/runtime seams, and entitlement/capability checks.

Key inspected areas:

- `src/core/platform/org/**`
- `src/core/platform/auth/**`
- `src/core/platform/authorization/**`
- `src/core/platform/infrastructure/persistence/orm/**`
- `src/core/platform/infrastructure/persistence/repositories/**`
- `src/core/platform/{approval,audit,documents,time}/**`
- `src/application/runtime/**`
- `src/core/modules/project_management/**`
- `src/core/modules/inventory_management/**`
- `src/core/modules/maintenance_management/**`
- `src/ui_qml/platform/**`
- `src/ui_qml/modules/project_management/**`
- `src/infra/platform/app_settings.py`

## Target Tenant Context

Runtime services must receive tenant scope from the authenticated principal/session through a `TenantContext`.

Required context fields:

- `active_organization_id`
- `user_id`
- `allowed_organization_ids`
- `permissions`
- `capabilities`
- `request_id`
- `correlation_id`

Rules:

- `TenantContext.active_organization_id` is the runtime tenant selector.
- `TenantContext.allowed_organization_ids` defines the tenant set the user may access.
- `Organization.is_active` must not be used by runtime services, repositories, controllers, presenters, QML, workers, dashboard refreshes, reports, exports, or caches to choose tenant data.
- QML may select display context, but it must never be trusted as a tenant authorization boundary.
- Admin organization screens may display organization lifecycle state, but business workspaces must use runtime tenant context.

## Current Tenant Model

### Organization

Current organization foundations:

- `OrganizationORM` includes identity, code/slug/name, lifecycle status, `is_active`, and metadata.
- `OrganizationService` supports listing, creating, updating, and organization administration workflows.
- Module entitlements are organization-scoped through platform entitlement tables.
- Sites, departments, parties, platform calendars, and documents are directly organization-scoped.

Target clarification:

- `Organization.is_active` means organization lifecycle/admin availability.
- `Organization.is_active` does not mean the active runtime tenant for a user.
- Business-module tenant selection must come from `UserSession -> TenantContext`.

### Entitlements and Capabilities

Current foundations:

- Module entitlements are organization-scoped.
- Runtime capability checks already exist and must be reused.

Rules:

- Capability checks are not a substitute for tenant filtering.
- Optional cross-module actions require tenant access plus entitlement/capability.
- Disabled modules must not be queried for tenant data.

## Target Repository Architecture

The requirement is not "every method must accept `organization_id` forever." The requirement is "every runtime query must be tenant-scoped before data is returned."

Transitional implementation helpers are acceptable during migration:

```python
repo.get_for_organization(project_id, organization_id)
repo.list_for_organization(organization_id)
repo.search_for_organization(organization_id, filters)
```

Target repository architecture:

```python
repo.get(project_id)
repo.list(filters)
repo.search(filters)
```

In the target architecture, repositories derive scope automatically from injected `TenantContext`:

```text
WHERE organization_id = tenant_context.active_organization_id
```

Repository rules:

- Tenant-owned repositories must not expose runtime `list_all()`, `get_all()`, `search_all()`, `export_all()`, `count_all()`, or `fetch_all()` paths.
- Transitional scoped methods must remain explicit until repository-level tenant context enforcement is complete.
- Unsafe compatibility wrappers must not remain reachable from runtime services, APIs, controllers, presenters, workers, or QML.
- Service-level filtering after an unscoped repository fetch is transitional risk, not target architecture.

## Direct Object Reference Protection

Tenant filtering must occur before the object is returned from persistence.

Unsafe:

```sql
SELECT *
FROM projects
WHERE id = :project_id
```

Preferred transitional query:

```sql
SELECT *
FROM projects
WHERE id = :project_id
  AND organization_id = :organization_id
```

Target repository behavior:

```text
repo.get(project_id)
  -> applies TenantContext.active_organization_id internally
```

Examples that must be protected:

- Projects: load by `id + organization_id`.
- Tasks: load through task/project tenant ownership before returning a task.
- Inventory items: load by `item_id + organization_id`.
- Assets: load by `asset_id + organization_id`.
- Documents: load by `document_id + organization_id` and verify link target tenant.
- Approvals: load by `approval_id + organization_id`.
- Audit logs: load by `audit_id + organization_id` or explicit super-admin audit scope.

Cross-tenant direct object references must return safe not-found or permission-denied responses without revealing whether the foreign record exists.

## Ownership Discovery

### Platform Ownership

| Area | Current ownership | Risk |
| --- | --- | --- |
| Organizations | Root tenant entity | Safe as tenant root; `is_active` is lifecycle only |
| Sites | `organization_id` | Good foundation |
| Departments | `organization_id`, `site_id` | Good foundation |
| Parties | `organization_id` | Good foundation |
| Employees | `department_id`, `site_id`; no direct `organization_id` found | Organization ownership is inherited and must be guarded |
| Users | Global user table; no direct `organization_id` found | Requires explicit user-organization access model |
| Roles and permissions | Mostly global | Acceptable if assignments are tenant-aware |
| User roles | `user_id`; no direct organization scope found | Risk of global role bleed unless scoped elsewhere |
| Scoped access grants | `user_id` with scope metadata | Needs tenant validation and null-safe mapping hardening |
| Project memberships | `project_id`, `user_id` | Project-scoped, tenant inherited |
| Documents | `organization_id` on document records and structures | Good foundation |
| Document links | Link by document/source | Must ensure linked document organization matches source tenant |
| Platform calendars | Calendar definitions `organization_id`; rules/exceptions inherit through calendar | Good foundation |
| Calendar assignments | Site/department/employee/project/resource assignment targets | Needs validation that targets belong to active tenant |
| Approval requests | `project_id`; no direct `organization_id` found | `CRITICAL` risk for workflow inboxes |
| Audit logs | `project_id` and actor metadata; no direct `organization_id` found | `CRITICAL` risk for global audit views |
| Time entries | `employee_id`, `site_id`, `department_id`; no direct `organization_id` found | Tenant ownership is inherited and should be explicit or guarded |
| Timesheet periods | `resource_id`; no direct `organization_id` found | High risk when PM resources are not organization-scoped |
| Runtime executions | No direct organization ownership found | Needs tenant context for operational traceability |

### Project Management Ownership

| Area | Current ownership | Risk |
| --- | --- | --- |
| Projects | `organization_id`, `site_id` | Good root; list/create/update paths must stamp tenant from context |
| Tasks | `project_id` | Tenant inherited through project |
| Task assignments | `task_id`, `resource_id` | Tenant inherited; resource ownership gap increases risk |
| Task dependencies | Task references | Tenant inherited; cross-project dependencies need explicit tenant rules |
| Project resources | `project_id` | Tenant inherited through project |
| PM resources | `employee_id`; no direct `organization_id` found | High risk for cross-tenant resource pool leakage |
| Resource skills/certifications | Resource references | Inherits resource risk |
| Task skill requirements | Task references | Tenant inherited through task/project |
| Baselines | `project_id` | Tenant inherited through project |
| Baseline tasks | `baseline_id`, `task_id` | Tenant inherited |
| Variance records | `project_id`, `task_id` | Tenant inherited |
| Calendar events | `project_id`, `task_id` | Tenant inherited |
| Cost items | `project_id`, `task_id` | Tenant inherited |
| Register entries | `project_id` | Tenant inherited |
| Collaboration comments | `task_id`, `user_id` | Tenant inherited; queries must enforce task/project tenant |
| Task presence | `task_id`, `user_id` | Tenant inherited; workers must use tenant-safe sessions |
| Portfolio roots | Several tables historically lacked direct tenant ownership | High risk for dashboard-heavy aggregation |
| Dashboard aggregation | Built from PM services/repositories | Inherits upstream tenant-scope gaps |

### Inventory Ownership

Inventory & Procurement already has the strongest business-module tenant foundation found during the audit.

| Area | Current ownership | Risk |
| --- | --- | --- |
| Catalog categories/items | `organization_id` | Good foundation |
| Storerooms/warehouses | `organization_id`, `site_id` | Good foundation |
| Balances | `organization_id`, storeroom/item references | Good foundation |
| Transactions | `organization_id`, source references | Good foundation |
| Reservations | `organization_id`, project/task links where applicable | Good foundation |
| Reorder policies | `organization_id` | Good foundation |
| Cycle count headers | `organization_id` | Good foundation |
| Procurement headers | `organization_id`, `site_id` | Good foundation |
| Procurement lines | Parent/header inheritance | Must validate parent organization in repository/service methods |
| Suppliers/preferred suppliers | Organization-linked in procurement structures | Need entitlement gating when shared with Financials/PM |

### Maintenance Ownership

Maintenance also has a strong organization-scoped foundation.

| Area | Current ownership | Risk |
| --- | --- | --- |
| Locations/systems/assets/components | `organization_id`, site/location references | Good foundation |
| Sensors/readings/sources/exceptions | `organization_id` on operational roots | Good foundation |
| Failure/downtime records | `organization_id` | Good foundation |
| Work requests/orders/tasks/steps | `organization_id` on core records | Good foundation |
| Material requirements | `organization_id` | Good foundation |
| Preventive plans/tasks/instances | `organization_id` | Good foundation |
| Calendar/site/resource links | Organization/site inherited | Must use tenant context, not global active organization |

## PM Resource Ownership

PM resources should carry direct `organization_id`.

Relying entirely on:

```text
employee -> department -> site -> organization
```

is not sufficient as the target architecture for PM resource queries because resources are used constantly by scheduling, assignments, utilization, dashboards, timesheets, and portfolio capacity.

Target:

- Add direct `PMResource.organization_id`.
- Stamp from `TenantContext.active_organization_id` on create.
- Load/update/delete resources by tenant-scoped query.
- Keep references to platform employees/vendors/equipment as shared master data links, not duplicated PM-owned master data.
- Validate linked employee/vendor/equipment belongs to or is visible in the active tenant.

## Portfolio Ownership

Portfolio roots should carry direct `organization_id` because portfolio is dashboard-heavy, aggregation-heavy, and frequently queried across many PM surfaces.

Direct ownership targets:

- Portfolio scenarios
- Portfolio scoring templates
- Portfolio roadmaps
- Portfolio dependencies
- Portfolio funding models
- Portfolio intake records

Rules:

- Portfolio dashboards and heatmaps must query by `organization_id` at source.
- Cross-project dependency views must validate both sides belong to the same active tenant unless an explicit governed cross-tenant enterprise feature exists.
- Portfolio aggregation must never silently aggregate across organizations.

## Approval and Audit Ownership

Approval requests and audit logs are `CRITICAL` tenant-isolation surfaces.

Reason:

- They are frequently displayed in global inboxes, dashboards, detail timelines, collaboration feeds, and administrative views.
- Cross-tenant leakage exposes sensitive decisions, financial changes, identity metadata, and operational history.

Target:

- Approval requests must include direct `organization_id` or enforce an indexed tenant-owned parent join before return.
- Audit logs must include direct `organization_id` for tenant-observable audit streams.
- Super-admin cross-tenant audit must be an explicit separate mode, guarded by platform permission, and audited itself.
- PM must consume the platform approval/audit services by reference and must not create standalone approval or audit systems.

## Repository and Service Risks

### Critical Risks

- Runtime fallback from missing tenant context to global `Organization.is_active`.
- Approval and audit repositories/views without organization scope.
- Dashboard/report/export/cache paths that aggregate tenant-owned records without tenant keys.
- Background workers that run without propagated tenant context.
- Direct object references that load by ID before tenant filtering.

### High Risks

- PM resource repositories exposing unscoped resource pools while PM resources lack direct organization ownership.
- Portfolio roots without direct organization ownership.
- PM task/resource/collaboration/background-worker paths that operate by task/resource ID without tenant-scope enforcement.
- Time and timesheet persistence that depends only on inherited employee/site/department/resource relationships.
- Document links that do not validate source and document tenant match.

### Medium Risks

- Inventory/procurement child-line repositories relying on caller-side parent validation.
- Runtime execution records without tenant metadata.
- QSettings-backed cache/preferences keys that are not tenant-keyed.
- UI filtering treated as a security boundary.

## Cache Isolation

Tenant cache leakage is a security bug.

Target cache pattern:

```text
org:{organization_id}:...
```

Examples:

- `org:{organization_id}:projects:list`
- `org:{organization_id}:dashboard:portfolio`
- `org:{organization_id}:inventory:stock`
- `org:{organization_id}:pm:tasks:saved-view:{user_id}:{view_id}`
- `org:{organization_id}:reports:snapshot:{report_id}`

Rules:

- Cache ownership must include organization ID for tenant-owned data.
- User preferences that are tenant-sensitive must be keyed by `(user_id, organization_id, feature_key)`.
- Dashboard/report snapshots must include `organization_id`, source version, generated timestamp, and invalidation metadata.
- Cache invalidation must trigger on tenant-owned mutations, approval state changes, import commits, baseline updates, schedule recalculations, resource changes, and cross-module linked-record updates.

## Export Isolation

Exports are safe only if their upstream query is tenant-safe.

Rules:

- Export services must derive tenant scope server-side from `TenantContext`.
- Export services must never rely on client/QML filters as the security boundary.
- Export audit events must include `organization_id`, actor, source workspace, filter summary, row count, request ID, and correlation ID.
- Cross-tenant super-admin exports, if supported, must be separate workflows with explicit permission and audit logging.

## Dashboard Isolation

Dashboards, portfolio heatmaps, KPI strips, workflow inboxes, activity feeds, reports, and aggregation snapshots must be tenant-scoped at the query source.

Rules:

- Every dashboard/report query must include tenant scope before rows are loaded.
- Derived snapshots must be stored and invalidated by organization.
- Portfolio views must never aggregate across organizations unless an explicit platform super-admin report context exists.
- QML filtering does not contribute to tenant security.

## Background Worker Tenant Propagation

Background work must receive tenant context explicitly.

Tenant context must propagate across:

- Async workers
- QThreadPool jobs
- Background refreshes
- Scheduled jobs
- Notification processing
- Activity feed processing
- Import parsing
- Report generation
- Dashboard aggregation
- Schedule recalculation
- Cache snapshot refreshes

Rules:

- Workers must never rely on `Organization.is_active`.
- Worker payloads must include `organization_id`, `user_id` when applicable, `request_id`, and `correlation_id`.
- Worker retries must preserve tenant context.
- Dead-letter records must include tenant metadata for safe recovery and audit.
- UI refresh events must include tenant context and must be ignored by mismatched tenant sessions.

## Required Migrations and Indexes

Do not add columns blindly. Each migration must follow an ownership decision.

Likely migration candidates:

- Add `organization_id` to PM resources.
- Add `organization_id` to PM portfolio aggregate roots.
- Add `organization_id` to platform approval requests.
- Add `organization_id` to platform audit logs.
- Add `organization_id` to time entries and timesheet periods, or enforce indexed parent joins.
- Add `organization_id` to runtime execution records if tenant-observable.
- Add tenant-aware cache/snapshot tables if not already available.

Required indexes:

- `(organization_id, id)`
- `(organization_id, site_id)`
- `(organization_id, project_id)`
- `(organization_id, task_id)`
- `(organization_id, resource_id)`
- `(organization_id, status)`
- `(organization_id, created_at)`
- `(organization_id, approval_status)`
- `(organization_id, start_date, end_date)`

Backfill rules:

- Prefer deterministic parent ownership.
- Use default organization only when no deterministic parent owner exists.
- Keep one-time unscoped backfill queries inside migration files only.
- Add `NOT NULL` constraints only after safe backfill where migration tooling supports it.

## Strict Runtime Enforcement

This section supersedes any earlier wording that implies tenant isolation can be achieved while leaving unsafe runtime fallbacks in place.

Forbidden in runtime code for tenant-owned data:

- `list_all()`, `get_all()`, `search_all()`, `export_all()`, `count_all()`, `fetch_all()`
- `session.query(...).all()` without tenant scope
- `select(...)` without tenant scope
- Repository `get(id)` usage that returns tenant-owned objects before ownership filtering
- Dashboard/report/export/cache/search/metric aggregation without `organization_id`
- QML-side tenant filtering as a security boundary
- Runtime fallback from missing tenant context to globally active organization

Allowed only inside migration scripts:

- Controlled one-time backfill queries
- Local migration-only unscoped reads used to assign tenant ownership
- Queries that are not imported by runtime services, APIs, controllers, presenters, or background workers

## Mandatory Scan Targets

Every tenant-isolation implementation pass must scan runtime code for:

- `list_all(`, `.list_all`, `get_all(`, `.get_all`, `search_all(`, `export_all(`, `count_all(`, `fetch_all(`
- `query(`, `session.query`, `select(`, `.all()`
- `get_by_id(`, `find_by_id(`, `search(`, `export(`
- `dashboard`, `aggregate`, `summary`, `metrics`, `overview`, `cache`, `report`
- `get_active(`, `Organization.is_active`, `organization_repo.get_active`

Required scan roots:

- `src/core/**`
- `src/infra/**`
- `src/ui_qml/**`
- `src/modules/**`
- `src/platform/**`
- `src/shared/**`

## Implementation Phases

### Phase 1: TenantContext Foundation

- Define runtime `TenantContext`.
- Integrate `UserSession` active organization, allowed organizations, permissions, capabilities, request ID, and correlation ID.
- Remove runtime dependency on global active organization selection.

### Phase 2: Repository Tenant Enforcement

- Use transitional scoped methods where needed.
- Move toward repositories deriving scope from injected `TenantContext`.
- Remove unsafe runtime `list_all` and unscoped direct object reference paths.

### Phase 3: PM Hardening

- Harden projects, tasks, resources, and portfolio.
- Add direct PM resource ownership.
- Add direct portfolio root ownership.
- Ensure dashboards, task details, collaboration, and scheduling derive scoped data only.

### Phase 4: Approval and Audit Hardening

- Add or enforce tenant ownership for approval requests and audit logs.
- Separate normal tenant audit views from explicit super-admin cross-tenant audit.

### Phase 5: Dashboard, Report, and Export Hardening

- Tenant-scope all aggregate sources.
- Tenant-key derived snapshots and exports.
- Add export audit records with tenant metadata.

### Phase 6: Cache and Snapshot Hardening

- Tenant-key cache entries, saved views, QSettings preferences, dashboard layouts, and report snapshots.
- Add invalidation triggers for tenant-owned mutations.

### Phase 7: Async Worker Propagation

- Propagate tenant context through workers, scheduled jobs, notifications, activity feeds, report generation, imports, and dashboard refreshes.
- Add retry/dead-letter tenant metadata.

### Phase 8: Final Tenant Penetration Testing

- Validate direct API, QML, background refresh, export, report, dashboard, cache, import, approval, and audit isolation across at least two organizations.

## Validation Scenarios

The implementation phase must satisfy these scenarios before it can be considered enterprise-ready:

- User in Organization A cannot list, search, open, export, or aggregate Organization B projects.
- PM dashboard for Organization A includes only Organization A tasks, risks, resources, approvals, audit rows, and financials.
- Collaboration inbox shows only tenant-authorized mentions, approvals, activity, and workflow items.
- Portfolio heatmap does not aggregate projects across organizations.
- PM resource pool does not show employees/resources from another organization.
- Maintenance work orders linked to PM remain visible only when both modules are enabled and tenant matches.
- Inventory reservations linked to PM tasks remain visible only when both modules are enabled and tenant matches.
- Documents linked to projects/tasks inherit document permissions and tenant ownership.
- Audit log views are tenant-scoped unless a platform super-admin context explicitly requests cross-tenant audit.
- Approval queues are tenant-scoped and preserve approval history.
- Cached dashboards and saved table views do not bleed between organizations.
- Exports include only tenant-scoped rows and write tenant-aware audit events.
- Background workers preserve tenant context across async boundaries.
- Cross-tenant direct object references return safe not-found or permission-denied responses.

## Test Plan

### Architecture Tests

- Business repositories reject tenant-owned runtime list/query calls without tenant scope.
- PM does not duplicate platform organization, employee, document, approval, audit, notification, or time systems.
- Optional integrations remain gated by entitlement and module capability.
- QML controllers and presenters receive already-scoped data.
- Repository target architecture derives tenant scope from `TenantContext` once transitional methods are retired.

### Persistence Tests

- Tenant-owned root tables include direct organization ownership or enforced parent joins.
- Cross-tenant ID access returns not found or permission denied.
- Indexes exist for organization/date/status/project/resource access paths.
- Existing data migrations backfill organization ownership deterministically.

### Service/API Tests

- Project, task, resource, portfolio, dashboard, collaboration, financial, and scheduling APIs are tenant-scoped.
- Approval, audit, document, notification, and time APIs preserve tenant context.
- Background workers receive tenant context and cannot refresh another tenant's data.

### UI/QML Tests

- Workspace selectors do not expose unauthorized organizations.
- List pages, detail pages, tables, pagination, search, filters, and exports stay tenant-scoped.
- Dashboard/report/cache refreshes cannot display stale data from another tenant.
- QML filtering is never treated as a security control.

### Security Tests

- Direct object references across organizations are denied.
- Tenant context cannot be overridden from QML input.
- Financial and document visibility restrictions remain enforced inside the tenant.
- Approval and audit streams do not leak cross-tenant rows.
- Super-admin cross-tenant access, if supported, is explicit, audited, and not used by normal workflows.

## Acceptance Gates

Implementation must not be marked complete until:

- Runtime tenant context no longer depends on global `organizations.is_active`.
- All tenant-owned query paths accept or derive organization scope server-side before returning data.
- All high-risk shared services are tenant-aware.
- Approval requests and audit logs are tenant-owned or tenant-joined before return.
- PM resources and portfolio roots have direct ownership or an approved transitional guard with a migration plan.
- Dashboard, portfolio, collaboration, approval, audit, report, export, and cache paths are tenant-safe.
- Cross-module integrations validate both tenant match and entitlement.
- Background workers propagate tenant context.
- Automated tests prove Organization A cannot access Organization B data through direct APIs, QML workspaces, background refreshes, reports, exports, approval queues, audit views, or cached snapshots.

## Transitional Patterns Identified

These may exist temporarily during migration but are not target architecture:

- `list_for_organization()` and `get_for_organization()` repository methods.
- Service-level joins that validate tenant ownership after fetching a parent row.
- Parent-inherited ownership where direct ownership is planned.
- Default-organization backfill inside migration scripts.
- Admin lifecycle usage of `Organization.is_active`.

These are not acceptable target patterns:

- Runtime fallback to global active organization.
- Repository `get(id)` followed by tenant validation after the tenant-owned object is returned.
- QML-side tenant filtering for security.
- Unscoped dashboard/report/export/cache aggregation.

## Sections Removed or Reworded

Removed:

- No valid sections were intentionally removed.

Reworded:

- Any wording that implied global active organization is acceptable runtime architecture.
- Any wording that implied service-level filtering alone is sufficient as the target state.
- Any wording that implied QML filtering contributes to tenant security.
- Any wording that classified approval and audit risk below `CRITICAL`.

## Change Summary

This revision clarifies:

- `TenantContext` is the target runtime tenant selector.
- `Organization.is_active` is lifecycle/admin state only.
- Repository-scoped helper methods are transitional, not the long-term ideal.
- Tenant filtering must happen before direct object references are returned.
- PM resources and portfolio roots should carry direct tenant ownership.
- Approval requests and audit logs are `CRITICAL` isolation surfaces.
- Background workers, caches, exports, dashboards, and reports require explicit tenant propagation and tenant-keyed data.
- The implementation roadmap is phased and platform-wide.

## Non-Goals

This tenant-isolation work must not create standalone duplicate systems for shared platform concerns.

PM and other modules must not introduce:

- Standalone organization or tenant systems
- Standalone employee or HR systems
- Standalone document stores
- Standalone approval engines
- Standalone notification systems
- Standalone audit systems
- Standalone time-entry systems
- Standalone cache/reporting platforms disconnected from platform runtime

The correct direction is to harden and consume shared platform services by reference while enforcing tenant isolation at every boundary.
