# Enterprise Cache Service Strategy

This document captures a documentation-only cache strategy for the existing modular SaaS application. It does not implement runtime code. It is intended as a follow-up blueprint for introducing service-level caching safely across Platform, Project Management, Inventory & Procurement, Maintenance, and shared runtime services.

## Inspection Basis

Fresh automated scanning was blocked by the local tool sandbox/escalation limit during this pass. This strategy is therefore based on the already-inspected architecture from recent platform and PM work, including:

- Platform QML workspaces/controllers and shared typed controller metadata.
- PM dashboard, tasks, scheduling, collaboration, financials, portfolio, and lazy-loading workspaces.
- Platform admin calendar management, entitlement/capability seams, document/audit/approval integration, and reusable QML controls.
- PM scheduling/reporting/import/financial/collaboration foundations previously inspected during modernization planning.
- Inventory & Procurement foundation requirements around catalog, stock balance, ledger, reservation, replenishment, valuation, and audit.
- Existing shared event infrastructure under `src/core/shared/events`, including `Signal`, `DomainChangeEvent`, `DomainEvents`, named module/platform signals, `shared_master_changed`, and the canonical `domain_changed` bridge.

Before implementation, run a fresh code scan and confirm the exact existing cache/snapshot helpers so this plan extends current patterns rather than duplicating them. The event integration guidance in this document is based on the inspected `src/core/shared/events` package and should be reused rather than replaced.

## Executive Recommendation

Introduce a shared service-level cache capability owned by the platform/runtime layer and consumed by modules through narrow interfaces. The cache should support:

- Tenant-safe keys using `organization_id` and optional site/project/user/role dimensions.
- Short-lived in-memory caching for frequently repeated read models.
- Derived snapshot caching for expensive dashboard, portfolio, report, Gantt, financial, and heatmap aggregations.
- Event-driven invalidation from domain events, approval events, audit-relevant mutations, and cross-module updates.
- Permission-aware caching so financial, document, approval, and employee data is never leaked across users or tenants.

Do not place cache logic directly in QML views. QML should request view models from controllers/presenters; services decide whether data is served fresh, cached, or refreshed asynchronously.

## Non-Goals

This cache strategy is not:

- A replacement for database indexes.
- A standalone BI/data warehouse.
- A standalone workflow engine.
- A substitute for authorization checks.
- A way to hide slow blocking UI calls without fixing async/lazy loading.
- A reason to duplicate platform-owned services.

## Proposed Cache Architecture

### Shared Interfaces

Target interfaces can be introduced under the platform/runtime or infrastructure layer:

- `CacheService`: get/set/delete operations with TTL, tags, and tenant scope.
- `CacheKeyBuilder`: canonical key construction for organization, module, entity, filters, user, and capability dimensions.
- `CacheInvalidationService`: invalidates keys by tag, entity reference, module, project, or organization.
- `DerivedSnapshotService`: manages expensive computed snapshots and refresh state.
- `CachePolicyRegistry`: declares TTL, invalidation tags, permission rules, and refresh behavior per read model.

These interfaces should be consumed by module application services or presenters, not by QML components.

### Cache Tiers

Use multiple tiers deliberately:

- Request/session memoization: Prevent repeated service calls during one user action or controller refresh.
- Process-local TTL cache: Small, fast cache for low-risk reference data and repeated view models.
- Persistent derived snapshots: Database-backed or durable cache records for dashboards, portfolio summaries, reports, financial rollups, schedule diagnostics, and import previews.
- Future distributed cache: Optional later tier for multi-process/server deployment, not required for the current desktop runtime unless deployment architecture changes.

### Key Design

Cache keys must include enough scope to prevent data leaks:

```text
tenant:{organization_id}:module:{module}:model:{read_model}:scope:{scope_id}:filters:{hash}:user:{user_or_role_scope}:version:{schema_version}
```

Use user or role scope when output is permission-sensitive. Examples include financial views, document visibility, approvals, employee records, audit records, and module entitlement state.

### Cache Metadata

Each cached value should track:

- `organization_id`
- `module`
- `read_model`
- `scope_type`
- `scope_id`
- `filters_hash`
- `schema_version`
- `created_at`
- `expires_at`
- `source_event_id` or `source_version`
- `refresh_status`
- `duration_ms`

## Existing Shared Event Foundation

The repo already has a lightweight framework-agnostic event foundation in `src/core/shared/events`.

Current public exports:

- `Signal`: observer-style signal/slot primitive with `connect`, `disconnect`, `clear`, and `emit`.
- `DomainChangeEvent`: normalized event payload with `category`, `scope_code`, `entity_type`, `entity_id`, and `source_event`.
- `DomainEvents`: shared event hub containing named signals plus bridge wiring.
- `domain_events`: singleton `DomainEvents` instance used by modules/platform services.

Current bridge behavior:

- Named `Signal[str]` events emit an entity id.
- `DomainEvents._BRIDGE_SPECS` maps named signals to normalized `DomainChangeEvent` records.
- Shared-master events also emit through `shared_master_changed`.
- Every bridged event emits through `domain_changed`.

This is a strong fit for cache invalidation. A future `CacheInvalidationService` should subscribe to `domain_events.domain_changed` as the primary broad invalidation stream, then optionally subscribe to specific named signals for hot paths where a smaller refresh is needed.

Do not introduce a separate cache-only event bus. Cache invalidation should be a subscriber to the existing shared event hub.

### Existing Event Groups

Platform and shared-master events already present:

- `organizations_changed`
- `sites_changed`
- `departments_changed`
- `calendars_changed`
- `documents_changed`
- `parties_changed`
- `employees_changed`
- `auth_changed`
- `access_changed`
- `approvals_changed`
- `modules_changed`

Project Management events already present:

- `project_changed`
- `tasks_changed`
- `timesheet_periods_changed`
- `costs_changed`
- `resources_changed`
- `baseline_changed`
- `register_changed`
- `collaboration_changed`
- `portfolio_changed`

Inventory & Procurement events already present:

- `inventory_items_changed`
- `inventory_item_categories_changed`
- `inventory_storerooms_changed`
- `inventory_balances_changed`
- `inventory_reservations_changed`
- `inventory_requisitions_changed`
- `inventory_purchase_orders_changed`
- `inventory_receipts_changed`
- `inventory_maintenance_materials_changed`
- `inventory_locations_changed`
- `inventory_reorder_policies_changed`
- `inventory_cycle_counts_changed`

Known gap:

- Maintenance-specific cache invalidation should use existing Maintenance events if they exist elsewhere, or add named Maintenance signals to `DomainEvents` before caching Maintenance dashboards/backlogs heavily. Do not wire Maintenance cache invalidation through ad-hoc callbacks hidden inside services.

### Event-to-Cache Mapping

Use `DomainChangeEvent` fields to derive invalidation tags:

- `category`: separates `platform`, `shared_master`, and module events.
- `scope_code`: maps to the owning module or platform scope, such as `project_management`, `inventory_procurement`, or `platform`.
- `entity_type`: maps to cache entity tags like `project`, `project_tasks`, `stock_balance`, or `working_calendar`.
- `entity_id`: maps to the changed entity/scope id.
- `source_event`: maps to the original named signal, such as `tasks_changed` or `inventory_balances_changed`.

Suggested normalized tag derivation:

```text
event:{source_event}
category:{category}
scope:{scope_code}
entity:{entity_type}:{entity_id}
module:{scope_code}
```

When the event payload does not include `organization_id`, the invalidation service should either:

- Resolve tenant scope from the changed entity before invalidating tenant-scoped entries.
- Invalidate only low-risk process-local entries for that entity.
- Fall back to a scoped module/entity invalidation policy that is conservative but not global.

## Event-Driven Invalidation Policies

Recommended policy examples:

- `organizations_changed`: Invalidate organization profile, runtime scope, entitlement summary, platform navigation, and tenant-level reference caches.
- `sites_changed`: Invalidate site catalogs, calendar inheritance chains, PM project/site lookups, inventory location lookups, and maintenance site lookups.
- `departments_changed`: Invalidate department catalogs, employee assignment lookups, calendar assignment context, and approval routing summaries.
- `calendars_changed`: Invalidate working-day calculations, calendar assignment context, Gantt/scheduling snapshots, resource availability windows, and PM/Maintenance schedule views.
- `documents_changed`: Invalidate document metadata catalogs, linked-record summaries, collaboration context, and document review workflow views.
- `employees_changed`: Invalidate employee catalogs, resource lookup lists, assignment validation caches, timesheet approver lists, and workforce capacity summaries.
- `auth_changed` and `access_changed`: Invalidate user/role scoped caches, workspace access snapshots, project access summaries, and permission-sensitive read models.
- `approvals_changed`: Invalidate approval queue counts, collaboration inboxes, dashboard approval bottlenecks, governed baseline/schedule/cost views, and audit-linked workflow summaries.
- `modules_changed`: Invalidate entitlement/capability snapshots, cross-module action availability, workspace navigation, and optional integration flags.
- `project_changed`: Invalidate project list rows, project detail shells, dashboard project health, portfolio summaries, and project lookup dialogs.
- `tasks_changed`: Invalidate task lists, WBS tree pages, task detail sections, scheduling inputs, Gantt rows, dashboard delayed-task counts, collaboration activity, and financial task cost rollups.
- `resources_changed`: Invalidate resource pool rows, utilization heatmaps, assignment validation, portfolio capacity, labor cost estimates, and dashboard overload summaries.
- `baseline_changed`: Invalidate baseline comparison snapshots, scheduling diagnostics, variance summaries, dashboard baseline KPIs, and approval workflow context.
- `costs_changed`: Invalidate financial rollups, EVM metrics, dashboard budget variance, portfolio budget summaries, and report snapshots.
- `timesheet_periods_changed`: Invalidate timesheet tables, labor actuals, cost rollups, resource utilization, approval queues, and dashboard timesheet metrics.
- `register_changed`: Invalidate risk/register tables, dashboard risk/issue/change summaries, collaboration workflow context, and portfolio risk rollups.
- `collaboration_changed`: Invalidate inbox counts, mentions, activity feed pages, workflow detail pages, and dashboard activity summaries.
- `portfolio_changed`: Invalidate portfolio dashboards, cross-project dependency views, prioritization views, and capacity-vs-demand snapshots.
- `inventory_items_changed`: Invalidate catalog search, item lookup dialogs, material demand views, replenishment summaries, and PM/Maintenance material selectors.
- `inventory_balances_changed`: Invalidate balance snapshots, availability views, reservation/demand summaries, stock-health dashboards, and material issue readiness.
- `inventory_reservations_changed`: Invalidate demand/reservation views, PM task material demand, Maintenance material planning, and procurement recommendations.
- `inventory_requisitions_changed`, `inventory_purchase_orders_changed`, and `inventory_receipts_changed`: Invalidate procurement status, committed cost, inventory availability, PM financial committed cost, and replenishment dashboards.
- `inventory_locations_changed` and `inventory_storerooms_changed`: Invalidate warehouse/location/bin hierarchy, balance browsing, and material availability views.
- `inventory_reorder_policies_changed`: Invalidate replenishment recommendations and stock-health KPIs.
- `inventory_cycle_counts_changed`: Invalidate cycle-count dashboards, balance confidence indicators, and audit-ready inventory views.

## Invalidation Rules

Cache invalidation should be event-driven first and TTL-driven second.

Invalidate by entity and tag when existing `DomainEvents` signals occur:

- Platform/shared master changes: `organizations_changed`, `sites_changed`, `departments_changed`, `employees_changed`, `calendars_changed`, `documents_changed`, `parties_changed`, `modules_changed`, `auth_changed`, and `access_changed`.
- Governance/workflow changes: `approvals_changed` and audit-relevant mutation events.
- PM changes: `project_changed`, `tasks_changed`, `resources_changed`, `baseline_changed`, `costs_changed`, `timesheet_periods_changed`, `register_changed`, `collaboration_changed`, and `portfolio_changed`.
- Inventory changes: all existing `inventory_*_changed` signals.
- Maintenance changes: future or existing Maintenance events should be bridged through `DomainEvents` before broad caching is introduced for Maintenance read models.

Avoid global cache clears except for schema migrations, tenant reset, or explicit admin maintenance.

## High-Value Cache Areas

### Platform/Foundation

Recommended cache candidates:

- Module entitlement and capability snapshots.
- Organization, site, department, employee, user, party, and document metadata catalogs.
- Runtime scope and navigation/workspace catalog metadata.
- Approval queue counts and status summaries.
- Audit feed pages and audit counters.
- Calendar assignment context and calendar inheritance chains.
- Working-day calculations and recurring calendar expansions.

Notes:

- Include user/role scope for approval, audit, document, employee, and entitlement-sensitive views.
- Calendar caches should invalidate on calendar rules, exceptions, recurring events, assignment, site, department, employee, or project calendar changes.
- Do not cache document file content unless platform document storage explicitly supports it.

### Project Management

Recommended cache candidates:

- Dashboard KPI strip, portfolio status charts, risk summaries, budget variance, delayed milestones, approval bottlenecks, and activity summaries.
- Project list summary rows and project detail read models.
- Task list summary rows, WBS tree pages, task count buckets, and section-specific detail read models.
- Scheduling Gantt rows, diagnostics, critical path summaries, float buckets, open-end counts, and baseline comparison results.
- Resource utilization heatmaps, availability windows, overload summaries, and multi-project allocation snapshots.
- Financial rollups, EVM metrics, cost breakdown summaries, committed/forecast/actual cost snapshots, and currency-normalized totals.
- Collaboration inbox counts, mentions counts, activity feed pages, and workflow item summaries.
- Timesheet approval summaries and labor-cost impact snapshots.
- Report definitions, saved views, report result snapshots, and export job metadata.
- Import preview models, validation results, duplicate detection output, and staged import diffs.

Notes:

- Dashboard caches should be read-only derived snapshots and refresh after PM domain events.
- Task detail sections should remain lazy loaded; cache only active section view models after permission checks.
- Scheduling calculations should return deterministic results first; cache result snapshots by project, baseline, calendar version, dependency version, and task schedule version.
- Financial caches must be permission-aware and invalidate on timesheet, procurement, resource rate, currency, budget, commitment, and task cost events.

### Inventory & Procurement

Recommended cache candidates:

- Catalog item search and material master lookup.
- Warehouse/site/location/bin hierarchy.
- Inventory balance snapshots by item/location/lot/serial.
- Reorder policy summaries and replenishment recommendation snapshots.
- Supplier/preferred supplier lookup.
- Pricing and valuation summaries.
- Reservation and demand summaries for PM, Maintenance, and procurement workflows.
- Stock movement ledger pages with stable filters.
- Cycle count status dashboards.

Notes:

- Ledger writes remain authoritative and should never be skipped because of cache.
- Balance cache invalidates on stock movement, count adjustment, reservation, receipt, issue, transfer, lot/serial/expiry update, or valuation update.
- Cross-module demand snapshots should be capability-gated because not every tenant has PM or Maintenance enabled.

### Maintenance/CMMS

Recommended cache candidates:

- Asset hierarchy and asset summary cards.
- Work order backlog KPIs.
- Preventive maintenance schedule summaries.
- Labor/material demand summaries.
- Maintenance calendar availability and crew schedule views.
- Reliability dashboards and defect/failure trend summaries.
- PM-linked or inventory-linked work order reference snapshots.

Notes:

- Invalidate asset/work-order dashboards on work order status, assignment, completion, material issue, inspection result, failure report, or schedule update.
- Optional PM/Inventory integrations must remain entitlement-gated.

### Shared UI/Presentation

Recommended cache candidates:

- Server/service-side table query results for stable filters, not QML delegates.
- Saved table views, column layouts, filters, and density preferences.
- Pagination metadata and total counts for expensive tables.
- Lookup lists used by dialogs, such as projects, employees, sites, resources, suppliers, calendars, and cost codes.

Notes:

- QML should not rebuild large arrays repeatedly.
- Controllers should expose cached or lazily loaded read models.
- DataTable pagination and sorting should remain service-backed for large datasets.

## Workloads That Should Use Derived Snapshots

Use durable or refreshable derived snapshots for:

- Executive dashboards.
- Portfolio aggregations.
- PM schedule diagnostics and critical path summaries.
- Baseline comparisons.
- Resource heatmaps and capacity vs demand.
- Financial EVM and forecast rollups.
- Inventory valuation and stock-health summaries.
- Maintenance backlog and reliability dashboards.
- Scheduled reports and exports.
- Import preview/diff results.

Snapshots should expose:

- `status`: `fresh`, `stale`, `refreshing`, `failed`
- `last_refreshed_at`
- `source_version`
- `refresh_duration_ms`
- `error_summary`

## Workloads That Should Stay Synchronous

Keep these synchronous and strongly consistent:

- Permission checks.
- Mutations and validation before mutation.
- Approval decisions.
- Audit event creation.
- Stock movement ledger writes.
- Timesheet submission/approval writes.
- Task/resource assignment validation.
- Baseline approval state transitions.
- User-visible confirmation of create/update/delete commands.

Caching can accelerate surrounding read models, but it must not decide whether a protected mutation is allowed without checking current authorization and current domain state.

## Permission and Security Rules

All cache reads must enforce:

- Tenant isolation.
- Workspace/module entitlement checks.
- Project/resource/site access checks.
- Financial visibility restrictions.
- Document permission inheritance.
- Approval authority rules.
- Field-level security where applicable.

Never share a cached read model across users unless the output is proven role-independent and permission-independent.

## Event and Refresh Strategy

Cache invalidation should subscribe to the existing `domain_events` singleton from `src.core.shared.events`.

Primary subscription:

- `domain_events.domain_changed`: broad normalized event stream for platform, shared-master, PM, and Inventory changes.

Optional targeted subscriptions:

- `domain_events.shared_master_changed`: fast-path invalidation for organization/site/department/calendar/document/party reference caches.
- Named signals such as `tasks_changed`, `resources_changed`, `calendars_changed`, `approvals_changed`, and `inventory_balances_changed` when a cache policy needs a narrow refresh path.

Suggested cache tags derived from `DomainChangeEvent`:

- `organization:{id}`
- `site:{id}`
- `department:{id}`
- `employee:{id}`
- `project:{id}`
- `task:{id}`
- `resource:{id}`
- `baseline:{id}`
- `calendar:{id}`
- `approval:{id}`
- `document:{id}`
- `inventory_item:{id}`
- `warehouse:{id}`
- `work_order:{id}`
- `event:{source_event}`
- `category:{category}`
- `scope:{scope_code}`
- `entity:{entity_type}:{entity_id}`

Refresh behavior:

- Direct invalidation for small read models.
- Mark stale and refresh asynchronously for expensive snapshots.
- Serve stale data only when the UI clearly labels it and the operation is read-only.
- Do not serve stale data for approval, financial mutation, stock ledger mutation, or schedule-change authorization decisions.
- Treat event handlers as idempotent because the same logical change may arrive through a specific named signal and the normalized `domain_changed` bridge.
- Keep event handlers lightweight. They should mark or invalidate cache entries, then enqueue expensive refresh work instead of recomputing synchronously inside `Signal.emit`.

## Performance Targets

Initial targets for future implementation:

- Workspace list page from warm cache: under 150 ms service time.
- Dashboard snapshot retrieval: under 200 ms service time.
- Task/project detail shell load: under 150 ms before lazy section content.
- Cached lookup dialog data: under 100 ms service time.
- Expensive snapshot refresh jobs: asynchronous above 500 ms expected compute time.
- Large table queries: paginated by default, with totals cached or computed asynchronously when expensive.

## Implementation Order

1. Complete a fresh repository scan for existing cache/snapshot helpers.
2. Map existing `DomainEvents` signals to cache tags and cache policies.
3. Define shared `CacheService`, key builder, policy, and invalidation contracts.
4. Add cache policy registry entries for low-risk platform reference data.
5. Add derived snapshot support for dashboards and portfolio aggregation.
6. Add schedule/resource/financial snapshot policies for PM.
7. Add inventory balance, valuation, and replenishment snapshot policies.
8. Add Maintenance event bridge coverage before caching Maintenance backlog and schedule summaries broadly.
9. Wire invalidation to `domain_events.domain_changed`, `shared_master_changed`, selected named signals, and approval/audit mutations.
10. Add telemetry for hit/miss, refresh duration, stale serves, invalidation counts, and slow queries.
11. Add tests for tenant isolation, permission-safe caching, invalidation, snapshot refresh, and stale-state UI labels.

## Testing Requirements

Future implementation should include:

- Cache key tests for organization, user, role, module, filters, and schema version.
- Permission-leak tests for financial, approval, document, employee, and audit views.
- Invalidation tests for create/update/delete across Platform, PM, Inventory, and Maintenance.
- Snapshot freshness tests for dashboard, scheduling, portfolio, financial, inventory, and maintenance read models.
- Existing event bridge tests proving named `DomainEvents` signals invalidate the right tags through `domain_changed`.
- Event replay/idempotency tests for invalidation handlers.
- Performance tests comparing cold, warm, stale, and refresh-in-progress states.
- QML integration tests confirming controllers expose cached/lazy data without blocking the UI thread.

## Acceptance Criteria

The cache service is enterprise-ready when:

- Modules consume shared cache interfaces rather than implementing ad-hoc caches.
- All cache keys are tenant-scoped.
- Permission-sensitive read models include user/role/capability scope.
- Mutations remain strongly consistent and auditable.
- Expensive dashboards/reports/schedule/resource/financial aggregations use derived snapshots.
- Existing `DomainEvents` signals invalidate or refresh affected read models through `domain_changed` and targeted named subscriptions.
- No duplicate cache-specific event bus is introduced.
- QML views remain cache-agnostic and receive normal controller/view-model outputs.
- Telemetry reports hit rate, miss rate, stale serve count, refresh duration, and invalidation volume.

## Known Risks

- Over-caching can hide missing indexes or inefficient queries.
- User-scoped caching can explode memory use if keys are too granular.
- Under-scoped keys can leak data across tenants or roles.
- Stale dashboard data can mislead executives unless refresh state is visible.
- Event-driven invalidation can become unreliable without idempotency and retry handling.
- Local desktop/runtime caches may need rethinking if the app moves to multi-process or distributed deployment.

## Recommended Next Step

Run a fresh code scan once tooling is available, then create a small cache architecture spike around one low-risk Platform reference cache and one high-value PM dashboard snapshot. Use those two pilots to validate key structure, invalidation, telemetry, and QML non-blocking behavior before expanding across modules.
