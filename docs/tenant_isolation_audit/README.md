# Tenant Isolation Architecture Audit

Status: Phase 1 discovery complete. Initial implementation slice in progress.

This report captures the current multi-tenant posture of the modular SaaS codebase and identifies the tenant-boundary work required before implementation. The core business rule is that an `Organization` is a tenant boundary. Data from one organization must never be visible, queryable, exportable, cached into, reported with, or refreshed into another organization's UI context.

## Implementation Progress

Completed in the first tenant-hardening slice:

- Added runtime tenant-context wiring through platform runtime and desktop API composition.
- Added organization scoped-access policy support and principal/session active organization helpers.
- Hardened PM project/resource/portfolio/collaboration query paths to derive tenant scope server-side.
- Added tenant-scoped approval and audit list helpers for PM workflow/collaboration surfaces.
- Hardened platform site, department, party, document, calendar, and shift-pattern services to prefer session tenant context over the global active organization fallback.
- Added direct object reference protection for enterprise calendar and shift-pattern reads/mutations.
- Tenant-keyed PM task saved views, dashboard layouts, and table column preferences in QSettings-backed UI settings.
- Added regression coverage for tenant-scoped PM services, platform master data, documents, calendars, UI settings, and organization scoped-access registration.

Still remaining:

- Add direct `organization_id` migrations/indexes for high-risk shared workflow/runtime records where parent joins are not enough.
- Finish tenant-context replacement in employee support, inventory composition bootstrapping, maintenance services, runtime execution records, time/timesheets, document-link validation, exports, reports, and derived dashboard/report snapshots.
- Replace service-level fallback branches only after all composition paths inject tenant context.
- Add background-worker tenant propagation tests and cross-module integration isolation tests.

## Scope Inspected

The discovery pass inspected the platform foundation, Project Management, Inventory & Procurement, Maintenance, shared approval/audit/document/time services, QML controllers/presenters, dashboard/report/export paths, and runtime entitlement seams.

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

## Executive Finding

The repository already has many organization-scoped foundations, especially in Platform, Inventory, and Maintenance. However, the current tenant model is not yet safe enough for enterprise SaaS isolation.

The largest architectural risk is that the active organization appears to be represented as a global database flag on `organizations.is_active`. That is not a per-user or per-session tenant context. In a multi-user SaaS runtime, one user's tenant switch must not mutate the global active tenant for every other user. Before hardening individual repositories, the application needs an explicit runtime `TenantContext` or equivalent per-principal active organization context.

The second largest risk is uneven propagation of `organization_id`. Several shared workflow tables and PM operational roots either lack direct organization ownership or rely on inherited ownership without repository-level guardrails.

## Current Tenant Model

### Organization

Current organization foundations:

- `OrganizationORM` includes `id`, `name`, `code`, `slug`, `is_active`, `status`, and lifecycle metadata.
- `OrganizationService` supports listing, creating, updating, and setting an active organization.
- Module entitlements are organization-scoped through platform module entitlement tables.
- Sites, departments, parties, platform calendars, and documents are directly organization-scoped.

Concern:

- `OrganizationService.set_active_organization()` toggles `is_active` globally across organizations.
- `OrganizationService.get_active_organization()` reads the single globally active organization.
- Business-module tenant selection should not depend on an admin-only global active organization.

Target:

- Introduce a per-user/session tenant context such as `TenantContext.active_organization_id`.
- Keep `Organization.is_active` only for organization lifecycle status if needed, not runtime tenant selection.
- The authenticated principal should carry allowed organization IDs and the selected active organization ID.

### Entitlements and Capabilities

Current foundations:

- Module entitlements are organization-scoped.
- Runtime capability checks already exist and should be reused.

Risk:

- Capability checks are not a substitute for tenant filtering.
- Optional cross-module actions must require both tenant access and module capability.

Target:

- Every optional integration must be gated by tenant context plus entitlement/capability.
- Disabled modules should not be queried for tenant data.

## Ownership Discovery

### Platform Ownership

| Area | Current ownership | Risk |
| --- | --- | --- |
| Organizations | Root tenant entity | Safe as tenant root, but global active flag is unsafe |
| Sites | `organization_id` | Good foundation |
| Departments | `organization_id`, `site_id` | Good foundation |
| Parties | `organization_id` | Good foundation |
| Employees | `department_id`, `site_id`; no direct `organization_id` found | Organization ownership is inherited and should be guarded |
| Users | Global user table; no direct `organization_id` found | Needs explicit user-organization access model |
| Roles and permissions | Mostly global | Acceptable if assignments are tenant-aware |
| User roles | `user_id`; no direct organization scope found | Risk of global role bleed unless scoped elsewhere |
| Scoped access grants | `user_id` with scope metadata | Needs tenant validation and null-safe mapping hardening |
| Project memberships | `project_id`, `user_id` | Project-scoped, tenant inherited |
| Documents | `organization_id` on document records and structures | Good foundation |
| Document links | Link by document/source | Must ensure linked document organization matches source tenant |
| Platform calendars | Calendar definitions `organization_id`; rules/exceptions inherit through calendar | Good foundation |
| Calendar assignments | Site/department/employee/project/resource assignment targets | Needs validation that targets belong to the active tenant |
| Audit logs | `project_id` and actor metadata; no direct `organization_id` found | High risk for cross-tenant audit views |
| Approval requests | `project_id`; no direct `organization_id` found | High risk for cross-tenant workflow inboxes |
| Time entries | `employee_id`, `site_id`, `department_id`; no direct `organization_id` found | Tenant ownership is inherited and should be explicit or guarded |
| Timesheet periods | `resource_id`; no direct `organization_id` found | High risk when PM resources are not organization-scoped |
| Runtime executions | No direct organization ownership found | Needs tenant context for operational traceability |

### Project Management Ownership

| Area | Current ownership | Risk |
| --- | --- | --- |
| Projects | `organization_id`, `site_id` | Good root, but list/create/update paths need stricter tenant stamping |
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
| Collaboration comments | `task_id`, `user_id` | Tenant inherited; query paths must enforce task/project tenant |
| Task presence | `task_id`, `user_id` | Tenant inherited; background presence workers must use tenant-safe sessions |
| Portfolio intake/scenarios/templates/dependencies | No direct organization ownership found in several portfolio tables | High risk for portfolio views |
| Dashboard aggregation | Built from PM services/repositories | Inherits upstream tenant-scope gaps |

### Inventory & Procurement Ownership

Inventory is the strongest business-module tenant foundation found during this pass.

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
| Suppliers/preferred suppliers | Organization-linked in procurement structures | Need consistent entitlement gating when shared with Financials/PM |

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

## Repository and Service Risks

### Critical Risks

- Global active organization is not safe for multi-user SaaS runtime.
- PM project list paths include unscoped repository methods such as `list_all()` and rely on later filtering.
- PM resource repositories expose unscoped resource pools while resources do not carry direct organization ownership.
- Approval and audit repositories can list workflow/audit data without organization scope.
- Portfolio repositories contain several tables without direct organization ownership.
- Time and timesheet persistence lacks direct tenant ownership and depends on inherited employee/site/department/resource relationships.

### High Risks

- Project creation accepts optional `organization_id` instead of consistently stamping from active tenant context.
- Project update paths can alter project `organization_id`, which should be forbidden or governed by a tenant migration process.
- PM task/resource/collaboration/background-worker paths can operate by task/resource ID without explicit tenant arguments.
- Dashboard, portfolio, collaboration inbox, report, and export views inherit unscoped service behavior.
- QSettings-backed cache/preferences keys are not tenant-keyed.

### Medium Risks

- Some child-line repositories in Inventory and Procurement rely on caller-side parent validation.
- Document link queries should verify source and document organization match.
- Runtime execution records need tenant metadata for operational observability and replay.
- UI filtering must not be treated as a security boundary.

## Cache, Export, Report, and Dashboard Isolation

### Caches and User Preferences

Current cache/preferences examples:

- Dashboard layouts
- Task saved views
- Table column state
- Local QSettings-backed UI preferences

Risk:

- These appear to be keyed by feature/user-level names, not consistently by organization.

Target:

- Cache keys must include `organization_id` for tenant-scoped data.
- User preferences that are tenant-sensitive must be keyed by `(user_id, organization_id, feature_key)`.
- Derived dashboard/report snapshots must include `organization_id`, source version, and invalidation metadata.

### Exports

Risk:

- Exports are safe only if their upstream query is tenant-safe.
- Current PM export paths may inherit unscoped project/task/resource list APIs.

Target:

- Export services must accept tenant context and never export from client-provided filters alone.
- Export audit events must include `organization_id`, actor, source workspace, filter summary, and row count.

### Reports and Dashboards

Risk:

- Dashboard, portfolio, approval, audit, and collaboration aggregations are likely to leak data if the source service is not tenant-scoped.

Target:

- Every dashboard/report query must include `organization_id`.
- Derived report snapshots must be stored and invalidated by organization.
- Portfolio views must never aggregate across organizations unless an explicit platform-level super-admin context exists.

## Target Tenant Architecture

### Tenant Context

Introduce a runtime tenant context that is independent of the organization administration table.

Required context fields:

- `organization_id`
- `user_id`
- `allowed_organization_ids`
- `capabilities`
- `correlation_id`
- `request_id`

Rules:

- Services must receive tenant context from the authenticated principal/session.
- Repositories must not infer tenant from global active organization state.
- QML must never pass arbitrary organization IDs as a security decision.
- Admin organization management can select organizations for administration, but business workspaces must use runtime tenant context.

### Direct vs Inherited Ownership

Use direct `organization_id` for tenant-owned aggregate roots and high-risk operational records.

Use inherited ownership only for child rows that cannot be meaningful outside the parent, provided repository/service methods always join through the tenant-owned parent.

Recommended direct ownership additions or hardening candidates:

- PM resources
- PM portfolio roots and portfolio operational tables
- Approval requests
- Audit logs
- Time entries and timesheet periods
- Runtime execution records
- Collaboration presence/comments if high-volume direct tenant filtering is needed
- Import/report/export snapshot records

Recommended inherited ownership with strict joins:

- Task assignments through task/project
- Task dependencies through predecessor/successor task projects
- Baseline tasks through baseline/project
- Procurement lines through purchasing headers
- Calendar rules/exceptions through calendar definition

## Implementation Order

1. Create a tenant context design and map it to the authenticated principal/session.
2. Replace global active organization usage in business services with tenant context.
3. Define user-to-organization access and scoped role behavior.
4. Add repository contracts that require organization scope for tenant-owned aggregate roots.
5. Harden PM project, task, resource, portfolio, collaboration, dashboard, export, and report queries.
6. Harden platform approval, audit, time, document-link, runtime execution, and calendar-assignment queries.
7. Add schema migrations only where direct tenant ownership is required.
8. Add indexes for tenant-scoped access paths.
9. Tenant-key cache, dashboard, report, saved-view, and QSettings preferences.
10. Enforce capability and entitlement gates for optional cross-module integrations.
11. Add tenant-aware event payload standards.
12. Add regression tests for cross-tenant isolation.

## Required Migrations and Indexes

Do not add columns blindly. Each migration should be preceded by an ownership decision.

Likely migration candidates:

- Add `organization_id` to PM resources or introduce an organization-scoped PM resource pool root.
- Add `organization_id` to PM portfolio aggregate roots.
- Add `organization_id` to platform approval requests.
- Add `organization_id` to platform audit logs.
- Add `organization_id` to time entries and timesheet periods, or enforce joins with indexed parent ownership.
- Add `organization_id` to runtime execution records if they are tenant-observable.
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
- `(organization_id, start_date, end_date)` for schedule/resource/date-range queries

## Validation Scenarios

The implementation phase must satisfy these scenarios before it can be considered enterprise-ready.

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

## Test Plan

### Architecture Tests

- Business repositories reject tenant-owned list/query calls without organization scope.
- PM does not duplicate platform organization, employee, document, approval, audit, notification, or time systems.
- Optional integrations remain gated by entitlement and module capability.
- QML controllers and presenters receive already-scoped data.

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

### Security Tests

- Direct object references across organizations are denied.
- Tenant context cannot be overridden from QML input.
- Financial and document visibility restrictions remain enforced inside the tenant.
- Super-admin cross-tenant access, if supported, is explicit, audited, and not used by normal PM workflows.

## Acceptance Gates

Implementation should not be marked complete until:

- The runtime tenant context no longer depends on global `organizations.is_active`.
- All tenant-owned query paths accept or derive organization scope server-side.
- All high-risk shared services are tenant-aware.
- Dashboard, portfolio, collaboration, approval, audit, report, export, and cache paths are tenant-safe.
- Cross-module integrations validate both tenant match and entitlement.
- Automated tests prove Organization A cannot access Organization B data through direct APIs, QML workspaces, background refreshes, reports, exports, or cached snapshots.

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
