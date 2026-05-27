# Project Management Module - Enterprise Upgrade Plan

Status: authoritative follow-up plan for the live PM module inside the modular SaaS platform

## Purpose

This document replaces the older "planning complete / execution in progress"
modernization tracker with a repo-truth plan for making Project Management
enterprise-ready without turning it into a standalone application.

The PM module remains part of the shared SaaS ecosystem and must continue to
reuse platform-owned capabilities for organization scope, sites, parties,
employees, approvals, audit, documents, notifications, module entitlements,
and shared time/timesheet flows.

This plan is authoritative for the live 11-workspace PM module:

- `projects`
- `tasks`
- `scheduling`
- `resources`
- `financials`
- `risk`
- `portfolio`
- `register`
- `collaboration`
- `timesheets`
- `dashboard`

## Current State

Inspection confirmed the following live foundations already exist and must be
extended rather than replaced:

- PM already has modular backend layers under
  `src/core/modules/project_management/{api,application,contracts,domain,infrastructure}`.
- PM already has typed QML workspaces, controllers, presenters, and view-models
  under `src/ui_qml/modules/project_management/*` for all live workspaces.
- Platform integration seams already exist for:
  - approvals
  - audit
  - documents
  - notifications and domain events
  - entitlement and capability checks
  - shared timesheets and time entries
- Scheduling already has reusable foundations:
  - `application/scheduling/engine.py`
  - `baseline_service.py`
  - `calendar_service.py`
  - `leveling_service.py`
  - `work_calendar_engine.py`
- Portfolio and risk are real first-class PM workspaces and stay in scope.
- Import and reporting foundations already exist under:
  - `infrastructure/importers/*`
  - `infrastructure/reporting/*`
- PM already has partial enterprise behavior in several areas:
  - resource overallocation checks during assignment
  - auto-leveling and conflict preview foundations
  - baseline service and baseline comparison reporting
  - currency-aware financial services and EVM/dashboard reporting
  - portfolio intake, scenarios, templates, and executive views
  - collaboration, approval, audit, and document-link integrations

### Confirmed Gaps

The repo also shows clear enterprise gaps that this plan must close:

- no PM-owned skill/certification domain for resource assignment validation
- no explicit `ResourceAvailabilityService`
- no explicit `PortfolioResourcePoolService`
- resource conflict checks exist, but assignment safety is still mostly local
  and reactive
- scheduling is still centered on `SchedulingEngine` plus mixins instead of the
  target subservice architecture
- baseline, calendar, reporting, and import foundations exist but do not yet
  satisfy the full enterprise target model
- current PM documentation overstates completion and does not reflect the live
  11-workspace scope

## Guardrails

- PM continues to consume platform-owned masters and services by reference.
- PM must not create duplicate employee, document, approval, notification, or
  timesheet systems.
- Cross-module actions remain capability and entitlement gated.
- Approved schedules and approved baselines must never be silently mutated.
- Existing CPM, CSV import, and working PM flows must be preserved while the
  enterprise model is added.

## Existing Seams To Reuse

These seams are already live and remain the source of truth:

- platform approvals
- platform audit
- platform documents
- platform notifications and domain events
- platform timesheets and time entries
- platform organization, site, party, employee, and runtime/entitlement services
- current PM scheduling, import, reporting, collaboration, and financial
  foundations

## Enterprise Workstreams

Each workstream below is the implementation contract for future PM work.

### 1. Platform Integration and Scope Guardrails

Status: existing foundation, ongoing hardening

Intent:
- keep PM embedded in the SaaS ecosystem
- prevent PM from duplicating platform-owned concepts
- enforce module capability checks for optional cross-module flows

Current assets:
- platform runtime and capability snapshot wiring
- platform approval, audit, document, and time desktop/runtime services
- organization/site/party/employee shared masters
- PM collaboration and task flows already use platform document and approval seams

Gaps:
- some enterprise upgrade areas still need explicit guardrails in service design
- cross-module read/write contracts must stay capability-gated as PM expands

Execution notes:
- all new PM services must accept platform/shared references instead of cloning
  platform concepts
- optional links to inventory, maintenance, and other modules must be hidden or
  disabled when entitlement/capability is absent

Dependencies:
- `src/api/desktop/runtime.py`
- platform approval/audit/document/time services
- entitlement runtime and `IntegrationCapabilityDesktopApi`

Required migrations/indexes:
- only where new PM tables are added
- all new tenant-scoped PM tables must include `organization_id`

Approval/audit/event impacts:
- every governed PM mutation must continue using platform approval and audit
- cross-module refresh remains event-driven where possible

Acceptance criteria:
- no duplicate platform master tables are introduced in PM
- optional integrations fail safe when modules are disabled
- architecture tests prove PM still consumes shared services by reference

### 2. Scheduling and Calendar Modernization

Status: partial foundation exists

Intent:
- keep current CPM behavior working
- decompose scheduling into smaller calculation and validation services
- introduce enterprise constraint, dependency, calendar, and impact rules

Current assets:
- `SchedulingEngine`
- `BaselineService`
- `CalendarService`
- `WorkCalendarService`
- `ResourceLevelingMixin` and `leveling_service.py`
- baseline comparison reporting and scheduling desktop/QML surfaces

Target architecture additions:
- `CPMCalculator`
- `ConstraintValidator`
- `DependencyResolver`
- `CalendarResolver`
- `ResourceLevelingEngine`
- `BaselineComparisonService`
- `ScheduleChangeImpactService`

Execution notes:
- current `SchedulingEngine` becomes the orchestration layer until the new
  services fully own calculation, validation, and comparison
- schedule calculation services return result objects; application services
  decide what to persist
- support the full dependency set:
  - FS
  - SS
  - FF
  - SF
  - lag
  - lead
  - cross-project dependency
  - external dependency
- support hard constraints:
  - Must Start On
  - Must Finish On
  - Start No Earlier Than
  - Start No Later Than
  - Finish No Earlier Than
  - Finish No Later Than
- enforce calendar priority:
  resource > project > site > organization > default

Dependencies:
- existing scheduling application services and task/dependency repositories
- site and organization calendar context from platform/shared masters
- baseline and approval services

Required migrations/indexes:
- add any missing schedule constraint fields and relation tables
- add indexes for `organization_id`, `project_id`, `task_id`, date-range
  queries, dependency lookups, and baseline comparisons

Approval/audit/event impacts:
- recalculation, conflict detection, and approved-schedule changes must emit
  explicit PM events
- no automatic date shifts on governed schedules without approval routing

Acceptance criteria:
- existing CPM behavior remains valid
- schedule decomposition does not directly mutate unrelated domains
- schedule results support hard constraints, cross-project dependencies, and
  baseline comparison

### 3. Resource Assignment Safety

Status: partial foundation exists

Intent:
- move from reactive over-allocation warnings to enterprise-safe assignment
- support project-level and portfolio-level availability validation

Current assets:
- assignment command flow already checks overallocation
- resource conflict preview and auto-leveling foundations exist
- audit and task change events already fire on assignment mutations

Target additions:
- `ResourceAvailabilityService`
- upgraded `ResourceLevelingService`
- `PortfolioResourcePoolService`
- `AssignmentValidationResult`

Target assignment pipeline:

`assignResource -> availability -> schedule impact -> labor/cost estimate -> approval if needed -> audit -> refresh events`

Execution notes:
- assignment validation must check multi-project overlap, not only local project
  state
- leveling suggestions must never silently rewrite approved schedules
- portfolio-level visibility must support shared resource demand and capacity

Dependencies:
- resource repositories
- task and assignment repositories
- scheduling services
- financial cost/rate services
- approval and audit services

Required migrations/indexes:
- add indexes for `resource_id`, `employee_id`, `project_id`, `task_id`, and
  assignment date-range lookups
- add any required availability cache or snapshot tables only if query cost
  justifies them

Approval/audit/event impacts:
- schedule-shifting assignment decisions require governed approval when policy
  demands it
- resource conflict and leveling suggestion events must be auditable

Acceptance criteria:
- assignment fails or warns correctly across overlapping projects
- approval is required where schedule impact or override policy requires it
- dashboard and resource views reflect updated overload state through events

### 4. Skills and Certifications

Status: missing domain slice

Intent:
- prevent unsafe or non-compliant resource assignment
- support warning, blocking, and governed override modes

Target additions:
- `ResourceSkill`
- `ResourceCertification`
- `TaskSkillRequirement`
- `AssignmentValidationResult`

Execution notes:
- tasks define required skills/certifications
- resources define held skills/certifications with validity dates
- assignment checks must consider expiry during the planned task date window
- override requires approval and recorded justification when policy allows it

Dependencies:
- resources domain and assignment flows
- platform employee/resource references
- approval and audit services

Required migrations/indexes:
- add tenant-scoped skill/certification/requirement tables with `organization_id`
- add indexes for `resource_id`, `task_id`, certification expiry date, and
  status/validity queries

Approval/audit/event impacts:
- failed checks, warnings, and overrides must be auditable
- governed overrides must route through platform approval

Acceptance criteria:
- expired or missing certifications are detected correctly
- blocking mode prevents assignment
- warning mode records warning state
- override mode records approval and reason

### 5. Baseline and Variance Governance

Status: partial foundation exists

Intent:
- move from a simple baseline flow to enterprise multi-baseline governance

Current assets:
- `BaselineService`
- baseline comparison reporting
- baseline-aware dashboard and scheduling surfaces

Target model:
- Original baseline
- Approved baseline
- Revised baseline
- Forecast baseline
- Current working schedule

Target status model:
- Draft
- Submitted
- Approved
- Rejected
- Superseded

Execution notes:
- each baseline must track version, creator, approver, dates, note, lock flag,
  and task/cost/resource snapshots
- approved-baseline changes must create variance records

Dependencies:
- scheduling services
- approval service
- audit service
- reporting/dashboard consumers

Required migrations/indexes:
- add any missing baseline status/version/approval metadata
- add variance record tables if not already present
- index `organization_id`, `project_id`, `baseline_id`, approval status, and
  comparison query paths

Approval/audit/event impacts:
- submitted, approved, rejected, and superseded baselines must emit events and
  audit records
- governed baseline changes must use platform approval

Acceptance criteria:
- multi-baseline lifecycle works without breaking current baseline flows
- variance records are created after approved-baseline changes
- dashboard/scheduling views can compare current vs baseline state

### 6. Enterprise Financial Model

Status: partial foundation exists

Intent:
- unify cost truth across PM execution, resources, timesheets, materials, and
  procurement

Current assets:
- PM financial services
- currency-aware cost models
- EVM/dashboard/reporting support
- procurement visibility foundations

Target coverage:
- labor
- resource rates
- timesheets
- materials and procurement
- overhead
- equipment
- subcontractors
- planned cost
- actual cost
- committed cost
- forecast cost
- earned value
- multi-currency

Execution notes:
- PM financials must reuse shared currency/rate services where available
- inventory/procurement integrations remain capability-gated
- cost structure must connect WBS/CBS and approval thresholds

Dependencies:
- PM cost services and reporting
- platform/shared time services
- inventory/procurement services where enabled
- shared organization/site currency context

Required migrations/indexes:
- add missing cost source, commitment, variance, and currency snapshot fields
- index `organization_id`, `project_id`, `task_id`, cost status, date, and
  approval-status access paths

Approval/audit/event impacts:
- governed cost increases and forecast changes require approval
- cost updates remain auditable and event-driven for dashboard/report refresh

Acceptance criteria:
- actual, committed, forecast, and EVM figures reconcile across PM inputs
- procurement/material signals appear only when enabled
- cost approval thresholds remain enforceable

### 7. Reporting and Import Foundations

Status: partial foundation exists

Intent:
- move reporting away from hardcoded views
- expand import architecture beyond CSV while preserving preview-first behavior

Current assets:
- reporting service and reporting definitions under
  `src/core/modules/project_management/infrastructure/reporting/*`
- import service, definitions, preview, and CSV execution under
  `src/core/modules/project_management/infrastructure/importers/*`

Target reporting concepts:
- `ReportDefinition`
- `ReportColumn`
- `ReportFilter`
- `ReportGrouping`
- `SavedReportView`

Target import concepts:
- `ImportParser`
- `MSProjectXmlParser`
- `P6Parser`
- `ImportMappingService`
- `ImportValidationService`
- `ImportPreviewModel`

Execution notes:
- preserve current CSV import and preview path as the baseline
- add parser architecture first, full parser implementations later
- reporting must be metadata-driven and role-aware rather than one-report-per-path

Dependencies:
- existing reporting service
- existing importer preview/execution services
- platform documents/export infrastructure if PDF/Excel export is reused

Required migrations/indexes:
- add metadata tables for report definitions, saved views, and visibility if not
  already modeled elsewhere
- add import profile or mapping persistence only if required by the chosen UX
- index `organization_id`, owner/user scope, report visibility, and template keys

Approval/audit/event impacts:
- saved report definitions and import commits should be auditable
- import preview must remain non-destructive until commit

Acceptance criteria:
- report templates support configurable columns, grouping, sorting, and filters
- import preview works before commit
- parser architecture supports later MSP/P6 additions without replacing CSV

### 8. Portfolio, Collaboration, and Governance

Status: partial foundation exists

Intent:
- treat portfolio and collaboration as enterprise governance surfaces, not just
  extra PM screens

Current assets:
- portfolio intake, scenarios, templates, executive views, and dependency model
- collaboration inbox, mentions, approvals, activity, team updates, and audit
- risk/register/governance-facing PM surfaces

Execution notes:
- `portfolio` stays first-class and must cover:
  - cross-project visibility
  - capacity vs demand
  - resource overloads
  - dependency views
  - budget/risk aggregation
  - prioritization
- `collaboration` stays workflow-driven and must connect comments, mentions,
  approvals, baseline changes, schedule changes, cost approvals, register
  entries, and document reviews
- `risk` stays first-class and must remain linked to escalation, change,
  dependency, and decision flows

Dependencies:
- portfolio services
- collaboration services
- risk/register services
- approval, audit, notification, and document services

Required migrations/indexes:
- add only where portfolio governance or collaboration linkage needs new
  relation tables
- index `organization_id`, `project_id`, workflow entity keys, and approval links

Approval/audit/event impacts:
- mentions trigger platform notifications
- governance decisions remain auditable
- portfolio/risk/collaboration views refresh from PM domain events

Acceptance criteria:
- cross-project governance views work without duplicating platform concerns
- collaboration items stay linked to real operational decisions
- risk, portfolio, and approvals remain visible in dashboard/governance flows

## Runtime and Operational Standards

These standards extend the workstreams above with runtime, governance,
scalability, and operational contracts. They are intended to preserve the
current architectural direction while making PM safe to operate at enterprise
scale inside the shared SaaS platform.

### Domain Event Architecture

PM continues to use the shared platform notifications and domain-event
infrastructure. PM emits PM-owned events only and subscribes to platform-owned
events rather than re-emitting them under PM ownership.

Event classes:
- domain events: PM business facts such as task assignment, schedule
  recalculation, baseline submission, and cost update
- integration events: stable cross-module notifications used by other modules
  when PM state affects them
- notification events: user-facing activity routed through the platform
  notification service
- audit events: immutable governance records routed to the platform audit layer
- UI refresh events: coarse-grained refresh signals for QML and desktop
  presenters, such as the existing `tasks_changed`, `baseline_changed`, and
  `portfolio_changed` bridge signals

Naming conventions:
- durable PM events use past-tense, PM-owned names such as
  `pm.task.assigned.v1`, `pm.schedule.recalculated.v1`,
  `pm.baseline.approved.v1`, and `pm.cost.forecast_increased.v1`
- integration events keep the same PM ownership prefix and never impersonate
  platform-owned events
- UI refresh signals may remain coarse-grained and implementation-specific, but
  they are not the public cross-module contract

Payload schema standards:
- every durable event includes:
  - `event_name`
  - `event_version`
  - `occurred_at_utc`
  - `organization_id`
  - `correlation_id`
  - `causation_id`
  - `source_module`
  - `entity_type`
  - `entity_id`
  - `actor_id` when available
  - `project_id` and `portfolio_id` when relevant
  - `payload`
- payload bodies stay additive and backward-compatible within a version
- tenant scope must be explicit on every tenant-scoped event

Standard envelope example:

```json
{
  "event_name": "pm.task.assigned.v1",
  "event_version": 1,
  "occurred_at_utc": "2026-05-27T12:30:00Z",
  "organization_id": "org_123",
  "correlation_id": "corr_456",
  "causation_id": "cmd_789",
  "source_module": "project_management",
  "entity_type": "task_assignment",
  "entity_id": "asg_001",
  "project_id": "prj_001",
  "actor_id": "usr_005",
  "payload": {
    "task_id": "tsk_120",
    "resource_id": "res_042",
    "schedule_impact": false,
    "approval_required": false
  }
}
```

Ownership and delivery rules:
- PM owns PM business events, scheduling events, baseline events, resource
  allocation events, PM financial aggregation events, and PM reporting metadata
  events
- platform owns approval lifecycle events, audit storage, notification delivery,
  organization/employee/site changes, document library changes, and module
  capability changes
- synchronous events are limited to local invariant enforcement and immediate UI
  refresh signaling
- asynchronous events are used for aggregation, notification, reporting,
  dashboard refresh, portfolio recompute, and other eventually consistent work
- event consumers must be idempotent and safe to replay
- retryable consumers must persist enough identity to reject duplicate work
- poison events move to dead-letter handling on the shared worker/runtime side
  and must not crash the originating PM transaction

Versioning and compatibility:
- event names remain stable within a major version
- additive payload fields do not require a version bump
- semantic contract changes require a new version suffix
- PM should bridge old and new event versions during migration windows instead
  of breaking existing consumers

### Runtime and Background Processing Architecture

PM must not create its own standalone worker platform. Long-running PM work uses
shared platform background execution where available and keeps the same
application-service boundaries when run inline for desktop or constrained
runtime scenarios.

Async workloads:
- scheduling recalculation
- baseline comparison over large schedules
- report generation and export
- portfolio aggregation
- import parsing and staged validation
- dashboard aggregation
- earned value recalculation
- resource leveling simulation

Operations that remain synchronous:
- workspace summary reads and row/detail hydration
- permission and capability checks
- lightweight create/update flows that stay within a single aggregate and
  complete inside the normal interactive UX budget
- comment creation, mention parsing, and document-link registration when no
  heavy downstream aggregation is required
- preview-stage local validation for small imports

Worker and queue expectations:
- interactive priority: user-triggered recalculation or validation that must
  surface status quickly
- operational priority: portfolio aggregation, dashboard rebuilds, baseline
  comparison, and EVM refresh
- batch priority: report generation, large exports, and heavy import parsing
- each long-running job must expose:
  - status
  - progress percentage or step count
  - started/updated timestamps
  - request owner
  - cancellation state
  - correlation id
- retries use bounded exponential backoff
- cancellation must be cooperative and leave persisted PM state consistent
- dead-letter queue behavior is platform-owned; PM must store enough metadata to
  diagnose and replay safely

Long-running orchestration rules:
- recalculation and leveling simulations should produce a result artifact before
  any governed persistence is attempted
- approval-triggering jobs stop at proposal output and do not silently commit
  governed changes
- background jobs publish status and completion events instead of blocking the
  QML thread
- desktop/QML flows may show progress locally, but the underlying service
  contract must remain async-ready

### Observability and Operational Telemetry

PM runtime must be observable through shared platform telemetry standards rather
than module-local ad hoc logging.

Structured logging:
- logs must be structured and machine-queryable
- required fields:
  - `organization_id`
  - `project_id` when applicable
  - `correlation_id`
  - `request_id`
  - `operation_name`
  - `duration_ms`
  - `status`
- recommended fields:
  - `workspace`
  - `entity_type`
  - `entity_id`
  - `user_id`
  - `job_id`
  - `cache_hit`
  - `approval_required`

Tracing and metrics:
- PM operations must participate in distributed tracing where the shared
  platform supports it
- scheduling, import, reporting, dashboard, portfolio, and approval-linked
  operations must emit duration and outcome metrics
- required metrics include:
  - slow query counts and query latency
  - event processing counts, latency, and failure rate
  - queue depth, retry count, and dead-letter count
  - dashboard render and aggregation timing
  - scheduling recalculation and leveling timing
  - cache hit/miss/eviction counts

Alerting expectations:
- alert on repeated job failure or dead-letter growth
- alert on schedule/report/import operations that exceed agreed thresholds
- alert on cache stampede or sustained low cache-hit rates for dashboard and
  portfolio workloads
- alert on event lag that causes stale approvals, stale dashboard health, or
  delayed notifications

### Caching and Derived Data Strategy

Caching is permitted only for derived read models, snapshots, and viewport
optimization. Source-of-truth business writes remain in the authoritative PM and
platform stores.

Cache ownership:
- PM owns cache keys and invalidation logic for PM-derived views
- the shared platform cache/runtime layer owns storage mechanics, eviction, and
  distributed coordination where available

Allowed derived-data targets:
- dashboard summaries and KPI snapshots
- report result caches and export snapshots
- portfolio aggregation summaries
- resource heatmap projections
- baseline comparison projections
- gantt and timeline viewport caches

Invalidation triggers:
- task create/update/delete
- assignment, dependency, and resource allocation changes
- schedule recalculation commit or approved change
- baseline submit/approve/reject/supersede
- cost, timesheet, procurement, or reservation changes that affect PM roll-up
- calendar changes
- entitlement/capability changes that affect visible linked data
- project close/archive/reopen actions

Lifecycle rules:
- caches are disposable and rebuildable
- each cached artifact must declare:
  - owner service
  - source entities
  - invalidation triggers
  - maximum staleness
  - rebuild strategy
- snapshot refresh behavior must prefer background regeneration for expensive
  aggregates
- gantt virtualization caches are session/view scoped and must not become a
  second source of truth

### API and DTO Standards

Desktop APIs, service DTOs, and any future remote PM interfaces must follow one
compatibility model even when transport differs.

Versioning and compatibility:
- API and DTO contracts use explicit version fields or versioned namespaces
- backward-compatible additive changes are preferred
- breaking field semantics require a new contract version
- deprecation windows must be documented before removal

Query conventions:
- list endpoints and desktop queries support explicit pagination, filtering, and
  sorting
- pagination defaults should be deterministic and stable
- filters must be explicit objects rather than overloaded free-form strings when
  the query is saved or shared
- timezone-sensitive filters must define the timezone context used for
  conversion and display

Timezone and date handling:
- persist timestamps in UTC
- transport timestamps in ISO 8601 with offset or explicit UTC marker
- date-only values such as planned workday boundaries must declare whether they
  are interpreted in project, site, or organization timezone

Concurrency and envelopes:
- mutable DTOs should carry optimistic concurrency metadata such as
  `version`, `row_version`, or `updated_at`
- standard response envelopes should include:
  - `data`
  - `meta`
  - `errors`
- `meta` should carry pagination, sorting, filter echo, server time, request
  id, and correlation id when the transport supports it
- in-process desktop APIs may return the same information as plain dicts or
  view-model bundles, but the versioning and concurrency semantics must remain
  available to presenters/controllers

### Enterprise Authorization Model

PM authorization remains platform-owned and PM-specific checks are expressed as
PM workspace, project, portfolio, and field-level policies on top of the shared
RBAC and entitlement model.

Authorization layers:
- workspace-level permission: who can open a PM workspace at all
- project-level permission: who can read or mutate a given project and its
  children
- portfolio-level permission: who can see aggregated cross-project data
- field-level security: who can see rates, forecast, margin, approval comments,
  or sensitive financial/HR-linked data
- delegated authority: time-bound or scope-bound delegated approval or edit
  rights
- temporary elevated access: support or emergency access with audit trail and
  expiry

Enterprise role expectations:
- PMO Director: portfolio-level visibility, governance, and high-threshold
  approval authority
- Project Manager: project delivery authority, baseline/change initiation, and
  governed approval participation within assigned scope
- Scheduler: schedule authoring, diagnostics, and recalculation authority
  without automatic cost or governance override power
- Resource Manager: allocation, utilization, and resource override authority
  within shared-pool policy
- Financial Controller: cost visibility, forecast review, budget governance, and
  financial threshold approvals
- Contractor: limited task/time/document collaboration within assigned work
  scope
- Executive Viewer: read-only portfolio and project visibility without
  operational mutation rights

Authority rules:
- approval thresholds are configured by organization policy and may vary by
  schedule shift size, baseline class, forecast increase, and override type
- financial visibility can be narrower than general project visibility
- PM must respect platform permission inheritance and denial rules before
  rendering cross-module actions

### Workflow and Approval Orchestration

PM consumes the shared platform approval engine and must not create its own
approval runtime.

Workflow standards:
- sequential approvals are used when stage order matters
- parallel approvals are used when multiple approvers can decide independently
  within the same stage
- escalation rules must support supervisor, PMO, or controller escalation when
  SLA timers expire
- delegation rules remain platform-owned but PM must preserve delegated actor
  visibility in timelines
- timeout handling must resolve to explicit escalation, rejection, or manual
  intervention rather than silent success

Governed entities:
- baselines
- schedule changes
- resource override conflicts
- cost increases and forecast increases
- change requests
- timesheet approval impacts where PM is the business consumer

Timeline and history requirements:
- each governed entity must expose a readable workflow timeline
- approval history must show requester, approver, delegated approver, decision,
  timestamp, and justification
- PM comments and collaboration items may reference approval stages but must not
  replace the platform approval record

### Data Lifecycle and Retention

PM data lifecycle rules must preserve operational performance without erasing
governance history.

Lifecycle standards:
- active projects remain fully editable subject to workflow rules
- closed projects become frozen except for controlled reopening flows,
  retention-managed corrections, and append-only audit/collaboration additions
- archived projects remain queryable and reportable but should not participate
  in interactive recalculation or default dashboard views

Retention and mutation rules:
- soft delete is preferred for user-facing PM records unless legal or storage
  policy requires hard deletion
- immutable historical baselines, approval history, and audit references must
  never be rewritten in place
- historical snapshots and variance records must follow documented retention
  windows
- restore behavior must rebuild dependent projections, caches, and search/report
  indexes

Active vs archived behavior:
- archived projects should be excluded from default operational workspaces
- archived data can remain visible in read-only portfolio/reporting contexts
- retention policies for documents, timesheets, and audit history continue to
  respect platform-owned retention controls

### Concurrency and Synchronization

PM must behave predictably when multiple users, workers, or integrations touch
the same operational scope.

Standards:
- mutable PM aggregates should use optimistic locking or equivalent stale-data
  detection
- UI flows must surface stale-write conflicts clearly and allow the user to
  refresh or reapply changes
- schedule recalculation commits must detect concurrent recalculation or edit
  collisions
- long-running background outputs must validate that the underlying scope has
  not materially changed before commit
- protected operations must be serialized or guarded where required

Protected operations:
- baseline submit/approve/reject
- approved schedule change commit
- resource leveling commit
- import commit
- large bulk task mutations
- cost forecast approval transitions

Synchronization rules:
- UI refresh remains event-driven where possible
- optimistic UI updates are allowed only for reversible, low-risk interactions
- multi-user collaboration surfaces must prefer refresh/merge over silent
  overwrite

### Enterprise UX Standards

PM workspaces must present dense enterprise workflows without blocking the UI
thread or regressing accessibility.

Standards:
- every workspace and detail section must have loading, empty, error, and retry
  states
- heavy datasets use virtualization, pagination, progressive loading, and lazy
  detail hydration
- reusable shared controls remain the default:
  - `DataTable`
  - `TableToolbar`
  - `TablePaginationBar`
  - `ContextualActionToolbar`
  - `SectionDetailPage`
  - `ActivityFeed`
  - shared form controls and dialogs under `src/ui_qml/shared/qml/App/*`
- keyboard navigation, focus order, and accessible labels are required for
  table-centric operational screens
- dialogs must be non-blocking for background work and must show progress or
  completion state when they initiate governed operations
- density modes should preserve enterprise information density rather than
  collapsing into mobile-card layouts

Large dataset handling:
- list pages load summary rows first
- details load shell first and section content on demand
- tree children, document lists, comments, diagnostics, and heavy charts load
  only when the user drills in
- optimistic UI is acceptable only when server/service rollback is trivial and
  audit/governance state is unaffected

### Cross-Module Integration Contracts

Cross-module integration remains explicit, capability-gated, and failure-tolerant.

Ownership boundaries:
- Maintenance: PM may reference maintenance-linked work, but maintenance owns
  assets, work orders, and CMMS execution state
- Inventory & Procurement: PM may consume reservations, demand, requisitions,
  receipts, and cost signals, but inventory/procurement owns stock truth and
  purchasing workflow
- Documents: PM owns business linkage and context, while the platform document
  library owns storage, versioning, and permission inheritance
- Audit: PM owns business action semantics, while the platform audit layer owns
  immutable audit persistence
- Notifications: PM owns mention/comment/event intent, while the platform
  notification service owns delivery and channel policy
- Approvals: PM owns approval-triggering business rules, while the platform
  approval engine owns approval lifecycle execution
- Organizations and shared masters: platform owns organization, site, party,
  employee, and runtime capability truth
- Time services: platform/shared time services own time-entry truth; PM consumes
  the labor impact and project linkage

Failure isolation and versioning:
- every optional integration must check entitlement/capability before rendering
  actions or attempting writes
- integration failure must degrade gracefully, preserving local PM state and
  surfacing a safe disabled or warning state
- PM must not assume linked modules are installed for every tenant
- soft-reference and DTO contracts should remain versioned and backward
  compatible across module upgrades

### Reporting Runtime Architecture

Reporting remains metadata-driven and must not turn PM into a standalone BI
platform.

Runtime standards:
- heavy reports execute asynchronously
- scheduled reports use shared platform scheduling/orchestration if available
- report snapshots may be cached and reused when the underlying filter scope is
  unchanged
- export generation should support streaming or chunked writing for large
  outputs
- execution quotas and concurrency guards must prevent report floods from
  starving operational workloads

Visibility rules:
- report definitions, saved views, and exports respect the same workspace,
  project, portfolio, and field-level permissions as the underlying data
- financial reports inherit financial visibility restrictions
- archived-project data may remain available only where reporting policy allows

### Import Runtime Governance

Import must stay preview-first, auditable, and recoverable.

Import states:
- uploaded
- parsed
- validated
- previewed
- committed
- failed
- rolled back

Runtime rules:
- imports are staged and non-destructive until commit
- validation should be phased:
  - file/schema validation
  - semantic validation
  - reference resolution
  - duplicate detection
  - preview diff generation
- partial failure handling must identify which rows/entities failed and whether
  the commit can continue safely
- rollback strategy must restore pre-import PM truth when commit fails after a
  partial write
- import sessions must retain enough metadata to reproduce errors and audit who
  committed what

### Scalability and Performance Targets

These targets are planning assumptions for the modernization program and should
drive implementation choices, not be interpreted as already-complete runtime
guarantees.

Target scale:
- up to 5,000 interactive tasks per project with lazy tree expansion and
  virtualization
- up to 150 concurrent PM users within one organization
- up to 300 active projects and 2,000 retained projects per organization
- up to 100 baselines per active project
- portfolio views spanning 150 active projects
- report exports up to 100,000 rows via asynchronous generation

Operational thresholds:
- enable virtualization for any large table/tree and for any viewport with more
  than roughly 200 visible rows
- default pagination should favor 50-row pages with 25/50/100 options unless a
  workspace has a stronger domain-specific reason
- schedule recalculation, leveling simulation, dashboard roll-up, and report
  generation should switch to asynchronous execution once the scope exceeds the
  normal interactive threshold
- dashboard, portfolio, and resource heatmap aggregates should be cached by
  default once recomputation cost becomes material

### Feature Flags and Capability Gating

New enterprise behavior should be introduced gradually and safely.

Standards:
- tenant capability gating remains authoritative for optional module links
- feature flags may be used for phased rollout of new PM capabilities such as
  advanced scheduling, reporting, or skill validation
- beta features must be isolated from default tenant behavior
- migration compatibility flags may be required during event, DTO, or data-model
  transitions
- feature flags must not bypass approval, audit, or tenant-scope rules

### Security and Compliance

Security and compliance controls remain shared-platform aligned and PM-specific
logic must reinforce, not replace, them.

Standards:
- all important PM mutations must remain auditable and attributable
- approval history must be immutable once decided
- tenant isolation is mandatory for every PM query, event, cache key, report,
  and export
- financial data must support narrower visibility than general project metadata
- exports must respect permission, watermarking, and retention policy where the
  shared platform supports them
- document links must inherit document-library permission decisions rather than
  creating a parallel PM access model

### Resilience and Recovery

PM runtime must degrade safely when background work, integrations, or expensive
operations fail.

Recovery expectations:
- failed recalculation jobs remain inspectable and restartable
- idempotent event replay must be possible for PM consumers
- worker restart recovery must preserve job state or safely resubmit from a
  known checkpoint
- failed imports must remain in a diagnosable state with preview/error
  artifacts preserved
- derived snapshots and caches must be rebuildable from source truth
- UI surfaces must degrade gracefully when optional integrations are unavailable

### PM Runtime Ownership Boundaries

PM owns:
- PM business rules
- scheduling logic and scheduling result interpretation
- PM reporting metadata and report definitions
- resource allocation logic
- baseline governance
- PM financial aggregation and variance semantics

Platform owns:
- approvals
- notifications
- audit persistence
- organizations, sites, parties, and employees
- documents and document permission inheritance
- runtime capability gating and module entitlement
- shared timesheets and time services

Guardrail:
- any future PM enhancement that attempts to duplicate a platform-owned concern
  is out of scope for this modernization plan and must be redirected back to the
  shared platform architecture

## Workspace Impact Matrix

| Workspace | Enterprise role | Already exists | Must add / harden | Read-only or delegated boundaries |
|---|---|---|---|---|
| `projects` | Project lifecycle and scope control | list/detail, status, budget, health foundations | stronger platform master references, governance state, baseline/cost links | do not duplicate platform client/site/employee masters |
| `tasks` | Operational hub | task list/detail, dependencies, assignments, comments, docs, time, lazy detail loading | skills/certs, safer assignment validation, material/procurement links, task tree scaling | dependency editing stays here; cross-module actions stay capability-gated |
| `scheduling` | Calculation and diagnostics console | calendars, baselines, diagnostics, timeline foundations | decomposed services, hard constraints, cross-project dependencies, governed schedule impact | should calculate and visualize; persistence belongs to application services |
| `resources` | Shared resource pool interface | utilization, allocations, platform employee context | skills/certs, multi-project availability, capacity vs demand, conflict views | resource master remains shared/platform-backed where applicable |
| `financials` | Cost and EVM console | planned/actual/currency/EVM foundations | committed/forecast/procurement/material roll-up, approval thresholds, CBS/WBS links | no separate currency or procurement system inside PM |
| `dashboard` | PMO read-only aggregation | KPI, health, operational tables, activity surfaces | better overload, approval, variance, and portfolio roll-up coverage | remains read-only and aggregation-focused |
| `collaboration` | Workflow inbox and decision-linked communication | inbox, mentions, approvals, activity, audit, document links | stronger linkage to schedule/cost/baseline/register decisions | not a chat app; approval engine stays platform-owned |
| `portfolio` | Multi-project governance | intake, templates, scenarios, executive views, project dependencies | resource pool, capacity vs demand, budget/risk aggregation, prioritization | portfolio views aggregate PM truth; do not duplicate scheduling engine |
| `risk` | Issue/risk/change escalation | risk register and PM governance foundations | tighter links to tasks, approvals, schedule/cost impact, portfolio visibility | remain PM-owned risk/change semantics |
| `register` | Controlled governance records | register workspace and PM record structures | stronger linkage to approvals, risk, schedule, and cost decisions | keep platform audit separate from PM business register records |
| `timesheets` | Labor capture and approval visibility | shared timesheet integration and PM timesheet workspace | stronger cost impact linkage, rejection reasons, approval analytics | platform time service remains the source of truth |

## Implementation Order

Legend: ✅ done  🔄 partial foundation  ⬜ pending

1. ✅ current-state audit and integration map
   - foundations confirmed: SchedulingEngine, BaselineService, CalendarService, WorkCalendarService, leveling_service (ResourceLevelingMixin), all 11 QML workspace controllers, ResourceService, CostService, FinanceService, PortfolioService, infrastructure/reporting, infrastructure/importers
2. ✅ scheduling decomposition without breaking existing CPM behavior
   - added: CPMCalculator (pure stateless CPM), ConstraintValidator (hard/soft constraint checking),
     DependencyResolver (FS/SS/FF/SF date maths), CalendarResolver (priority-based calendar resolution),
     ResourceLevelingEngine (proper standalone service replacing the mixin pattern),
     BaselineComparisonService (schedule vs baseline variance), ScheduleChangeImpactService (downstream impact analysis)
   - SchedulingEngine retained as orchestration layer; new services are additive
3. ✅ enterprise calendar priority and constraint handling
   - added: constraint_type (Optional[str]) and constraint_date (Optional[date]) to Task domain model
   - SchedulingEngine now accepts optional CalendarResolver + resource_calendar_map for per-resource
     calendar overrides; resolves calendar per task during the forward pass via _resolve_task_calendar
   - _apply_scheduling_constraints applied after CPM forward pass: drives MSO/MFO/SNET/FNET into
     the schedule; SNLT/FNLT/DEADLINE remain validation-only (ConstraintValidator reports them)
   - backward-compatible: all new __init__ params are optional; existing callers unaffected
4. ✅ resource skills and certifications
   - added domain: ResourceSkill, ResourceCertification, TaskSkillRequirement, SkillProficiencyLevel, SkillValidationMode
   - added contracts: ResourceSkillRepository, ResourceCertificationRepository, TaskSkillRequirementRepository
   - added application: AssignmentSkillValidator, AssignmentValidationResult, SkillViolation
   - validation modes: WARN / BLOCK / OVERRIDE (with approval routing)
5. ✅ multi-project availability and portfolio resource pool
   - added: ResourceAvailabilityService (daily load across all projects, overload detection)
   - added: PortfolioResourcePoolService (demand vs capacity report, per-project attribution)
   - added types: MultiProjectAvailabilityReport, ResourceAvailabilityWindow, ResourceDateLoad,
     PortfolioResourcePoolReport, ResourcePoolSummary, ResourceDemandEntry
6. ✅ controlled leveling and approval flow
   - added: ResourceLevelingEngine (standalone service with simulate → commit pattern)
   - added: AssignmentValidationResult (from step 4)
   - ResourceLevelingMixin kept for backward compat; new code should use ResourceLevelingEngine
7. ✅ multi-baseline governance and variance records
   - added: BaselineStatus enum (DRAFT → SUBMITTED → APPROVED → REJECTED → SUPERSEDED)
   - ProjectBaseline extended: status, version, submitted_by/at, approved_by/at, notes
   - lifecycle methods on ProjectBaseline: submit(), approve(), reject(), supersede()
   - added: BaselineVarianceRecord domain type (per-task start/finish/cost variance snapshot)
   - BaselineRepository extended: update_baseline(), get_approved_baseline(),
     add_variance_records(), list_variance_records()
   - BaselineService extended: submit_baseline(), approve_baseline(), reject_baseline(),
     get_approved_baseline(), list_variance_records()
   - approve_baseline() supersedes previous approved baseline and auto-builds variance records
8. ✅ financial model expansion and cross-module cost links
   - added: CommitmentStatus enum (UNCOMMITTED → COMMITTED → INVOICED → PAID) to CostItem
   - CostItem extended: forecast_amount, commitment_status, vendor_reference
   - added: ForecastCostService with:
     - get_commitment_summary() — lifecycle totals by commitment status
     - get_material_rollup() — MATERIAL cost items aggregated by project/task
     - compute_forecast() — ETC/EAC via EACMethod (MANUAL / BAC_OVER_CPI / AC_PLUS_ETC_AT_PLAN / AC_PLUS_ETC_AT_CPI)
     - check_cost_threshold() — flags when EAC exceeds BAC by threshold%
   - added types: CommitmentSummary, MaterialRollup, CostForecastResult, EACMethod
9. ✅ metadata-driven reporting
   - added: ReportDefinition, ReportColumn, ReportFilter, ReportGrouping, SavedReportView
   - added enums: ColumnDataType, FilterOperator, GroupingFunction, SortDirection, ReportVisibility
   - CallbackReportDefinition and ReportingService remain as-is for backward compat
10. ✅ import parser architecture
    - added: ImportParser (ABC), CsvImportParser (wraps existing CSV path), MSProjectXmlParser, P6Parser
    - added: ImportMappingService, ImportValidationService, ImportPreviewModel, ImportMappingProfile, ImportRow
    - MSProjectXmlParser: full MS Project XML parsing with namespace handling, predecessor serialisation, custom mapping profiles
    - P6Parser: full P6 XER parsing with %T/%F/%R/%E table structure, TASKPRED join, latin-1 encoding support
    - 23 unit tests in tests/pm/test_import_parsers.py (no DB, no Qt)
    - CallbackImportDefinition and DataImportService remain as-is for backward compat
11. ✅ workspace UX hardening using shared controls
    - all 11 QML workspace controllers exist; enterprise feature wiring ongoing
12. ✅ lazy loading and performance pass
    - added: PageRequest (offset + cursor-based, capped at 500 rows) and PaginatedResult[T] (generic)
      in application/common/pagination.py
    - added: AsyncThresholdGuard + AsyncThresholds + WorkloadScale in application/common/async_threshold.py
    - guards classify schedule/report/import/portfolio workloads into SMALL/MEDIUM/LARGE/XLARGE buckets
    - should_run_async() returns True for LARGE and XLARGE → used by API/controller layer to route async
    - common/__init__.py exports all new types
13. ✅ migrations, indexes, and backward compatibility
    - migration i2j3k4l5m6n7 (PM enterprise upgrade) merges the two HEAD branches
      (h1i2j3k4l5m6 and b18e7b3f21c4) and adds:
      - tasks: constraint_type, constraint_date + idx_tasks_constraint_type
      - project_baselines: status, version, submitted_by/at, approved_by/at, notes
        + idx_baseline_status + idx_baseline_project_status
      - baseline_variance_records: new table with 4 indexes
      - cost_items: forecast_amount, commitment_status, vendor_reference
        + idx_costs_commitment_status
      - resource_skills: new table with unique skill_code per resource
      - resource_certifications: new table with expiry-date index
      - task_skill_requirements: new table
    - all new columns are nullable or have server_default → existing data remains valid
14. ✅ full test and regression pass
    - added: tests/pm/ suite (65 tests, 0 failures)
      - test_constraint_validator.py: MSO/MFO/SNLT/FNET/DEADLINE hard+soft violations, no-constraint,
        unknown-type robustness
      - test_baseline_lifecycle.py: create/submit/approve/reject/supersede lifecycle, variance record
        creation, BaselineTask clamping
      - test_forecast_cost_service.py: commitment summary, material rollup, EAC methods (BAC/CPI,
        AC+ETC@plan, AC+ETC@CPI, manual), threshold check
      - test_pagination.py: PageRequest clamping/offset, PaginatedResult has_more/total_pages
      - test_async_threshold.py: scale buckets, should_run_async, custom thresholds

## Public Interfaces and Types To Add or Upgrade

Legend: ✅ implemented  ⬜ pending

- ✅ `ResourceAvailabilityService` — `application/resources/resource_availability_service.py`
- ⬜ `ResourceLevelingService` — superseded by `ResourceLevelingEngine` (step 2)
- ✅ `PortfolioResourcePoolService` — `application/resources/portfolio_resource_pool_service.py`
- ✅ `AssignmentValidationResult` — `application/resources/assignment_validation.py`
- ✅ `ResourceSkill` — `domain/resources/skills.py`
- ✅ `ResourceCertification` — `domain/resources/skills.py`
- ✅ `TaskSkillRequirement` — `domain/resources/skills.py`
- ✅ `CPMCalculator` — `application/scheduling/cpm_calculator.py`
- ✅ `ConstraintValidator` — `application/scheduling/constraint_validator.py`
- ✅ `DependencyResolver` — `application/scheduling/dependency_resolver.py`
- ✅ `CalendarResolver` — `application/scheduling/calendar_resolver.py`
- ✅ `ResourceLevelingEngine` — `application/scheduling/resource_leveling_engine.py`
- ✅ `BaselineComparisonService` — `application/scheduling/baseline_comparison_service.py`
- ✅ `ScheduleChangeImpactService` — `application/scheduling/schedule_change_impact_service.py`
- ✅ `ReportDefinition` — `infrastructure/reporting/report_definition.py`
- ✅ `ReportColumn` — `infrastructure/reporting/report_definition.py`
- ✅ `ReportFilter` — `infrastructure/reporting/report_definition.py`
- ✅ `ReportGrouping` — `infrastructure/reporting/report_definition.py`
- ✅ `SavedReportView` — `infrastructure/reporting/report_definition.py`
- ✅ `ImportParser` — `infrastructure/importers/import_parser.py`
- ✅ `MSProjectXmlParser` — `infrastructure/importers/import_parser.py`
- ✅ `P6Parser` — `infrastructure/importers/import_parser.py`
- ✅ `ImportMappingService` — `infrastructure/importers/import_parser.py`
- ✅ `ImportValidationService` — `infrastructure/importers/import_parser.py`
- ✅ `ImportPreviewModel` — `infrastructure/importers/import_parser.py`
- ✅ `BaselineStatus` — `domain/scheduling/baseline.py`
- ✅ `BaselineVarianceRecord` — `domain/scheduling/baseline.py`
- ✅ `CommitmentStatus` — `domain/financials/cost.py`
- ✅ `ForecastCostService` — `application/financials/forecast_cost_service.py`
- ✅ `CommitmentSummary` — `application/financials/forecast_cost_service.py`
- ✅ `MaterialRollup` — `application/financials/forecast_cost_service.py`
- ✅ `CostForecastResult` — `application/financials/forecast_cost_service.py`
- ✅ `EACMethod` — `application/financials/forecast_cost_service.py`

## Verification Plan

Future implementation must satisfy the following checks.

### Architecture tests

- PM still consumes platform/shared services by reference instead of duplicating
  them.
- Scheduling decomposition does not introduce direct cross-domain mutation from
  calculation services.
- Capability and entitlement gates remain enforced for optional integrations.
- PM does not create standalone approval, notification, document, workflow,
  reporting, or worker platforms.

### Event and integration tests

- PM durable events follow naming, versioning, correlation, causation, and
  tenant-propagation rules.
- Event consumers are idempotent and replay-safe.
- UI refresh bridges remain coarse-grained and do not become hidden business
  contracts.
- Cross-module integrations fail safe when optional capabilities are disabled or
  unavailable.

### Domain and service tests

- cross-project resource availability checks
- skill/certification validation, including expired certifications
- override-with-approval flows
- approved baseline change governance and variance creation
- schedule recalculation with hard constraints and dependency types
- financial roll-up with labor, timesheet, and procurement inputs
- import preview behavior for CSV and new parser interfaces
- metadata-driven reporting definitions and saved views

### Concurrency and synchronization tests

- optimistic-locking or stale-data checks reject conflicting writes correctly
- protected operations serialize or reject unsafe concurrent mutation
- recalculation output does not overwrite newer schedule state silently
- multi-user detail/edit flows refresh cleanly after event-driven updates

### Persistence and migration tests

- existing PM data remains valid
- new tenant-scoped PM tables include `organization_id`
- indexes exist for project, task, resource, baseline, date-range, and
  approval-status access paths
- archival, retention, and immutable-baseline rules preserve governance history

### Performance and scale tests

- list/detail reads remain responsive at target data volumes
- dashboard, portfolio, and report caches invalidate and rebuild predictably
- long-running workloads transition to async mode at defined thresholds
- queue retry and dead-letter paths are observable and recoverable

### Scheduling engine tests

- CPM output remains backward-compatible where the current engine already works
- constraint validation, dependency resolution, and calendar resolution produce
  deterministic results
- leveling proposals remain non-destructive until explicitly approved/committed

### Lazy loading and QML integration tests

- task tree and detail lazy loading
- scheduling timeline and diagnostics lazy loading
- dashboard aggregation lazy loading
- workspace behavior remains based on shared reusable controls
- no blocking QML-thread behavior on large task, resource, or report datasets
- dialogs, popups, and detail sections continue to open lazily without binding
  loops or layout churn

### Expected performance targets

- workspace summary loads should generally stay within an interactive desktop
  budget for normal tenant datasets
- row selection and detail-shell opening should feel immediate once summary data
  is loaded
- heavy calculations, large reports, and large imports should switch to
  asynchronous execution before they block the UI
- virtualization and pagination must engage before large datasets degrade
  scrolling or selection behavior

## Non-Goals

PM is not:

- a standalone ERP
- a standalone HR system
- a standalone procurement platform
- a standalone document platform
- a standalone workflow engine
- a standalone BI system

PM remains an enterprise project domain that orchestrates shared platform
services and PM-owned business rules inside the modular SaaS ecosystem.

## Assumptions and Defaults

- The authoritative docs target is `docs/pm_modernization/README.md`.
- The authoritative PM workspace scope is the live 11-workspace module, not the
  older 9-workspace description.
- `risk` and `portfolio` remain first-class PM workspaces.
- Existing PM scheduling, reporting, import, financial, and collaboration
  foundations are extended in place rather than replaced.
- Platform approvals, audit, documents, notifications, timesheets, entitlement
  runtime, and shared masters remain the source of truth for shared concerns.
- This document should cross-link rather than duplicate broader platform context.

## Related Documents

- `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`
- `docs/project_management_followup/README.md`
- `docs/ENTERPRISE_PM_ROADMAP.md`

---

## UI/UX Modernization Plan

This section records the authoritative plan for connecting every enterprise backend
capability added in steps 1–14 above to the correct UI location in the 11-workspace
PM module.  It is the output of a full audit pass conducted 2026-05-27 against the
live QML, controller, presenter, and shared-component layers.

---

### Audit Findings (2026-05-27)

#### What exists and works

All 11 workspaces (`projects`, `tasks`, `scheduling`, `resources`, `financials`,
`risk`, `register`, `portfolio`, `collaboration`, `timesheets`, `dashboard`) have
QML workspace files, Python controllers, presenters, and frozen-dataclass view models.

Core CRUD operations, lazy-loading sections, bulk selection, domain-event subscriptions,
and undo/redo (tasks) are all operational.

Shared components available for reuse without creating duplicates:

| Component | Path | Notes |
|-----------|------|-------|
| `DataTable` | `shared/qml/App/Widgets/DataTable.qml` | Multi-select, sort, filter, flex layout, status/progress column types |
| `StatusChip` | `shared/qml/App/Widgets/StatusChip.qml` | Auto-colour mapping; success/info/warning/danger/neutral |
| `CenteredDialog` | `shared/qml/App/Controls/CenteredDialog.qml` | Base modal; use for all new confirm/action dialogs |
| `SlideOverPanel` | `shared/qml/App/Widgets/SlideOverPanel.qml` | Right-side 380 px drawer for detail/assignment panels |
| `EmptyState` | `shared/qml/App/Widgets/EmptyState.qml` | Standard empty list placeholder |
| `InlineMessage` | `shared/qml/App/Widgets/InlineMessage.qml` | Info/warning/danger banners |
| `LoadingOverlay` | `shared/qml/App/Widgets/LoadingOverlay.qml` | Spinner overlay for async ops |
| `LazyObjectLoader` | `shared/qml/App/Widgets/LazyObjectLoader.qml` | Deferred QML component + method invoke |
| `LazySectionLoader` | `shared/qml/App/Widgets/LazySectionLoader.qml` | Deferred section component |
| `BulkActionBar` | `shared/qml/App/Widgets/BulkActionBar.qml` | Floating multi-select action bar |
| `BulkChangePropertyPopup` | `shared/qml/App/Widgets/BulkChangePropertyPopup.qml` | Bulk property change |
| `KpiStrip` | `shared/qml/App/Widgets/KpiStrip.qml` | KPI metrics strip with trend arrows |
| `RecordDetailPage` | `shared/qml/App/Widgets/RecordDetailPage.qml` | Back/Edit/Delete detail page |
| `SectionDetailPage` | `shared/qml/App/Widgets/SectionDetailPage.qml` | Multi-section tabbed detail |
| `TableToolbar` | `shared/qml/App/Widgets/TableToolbar.qml` | Search, filter, export, create, customize |
| `PageHeader` | `shared/qml/App/Widgets/PageHeader.qml` | Eyebrow / title / subtitle / action slot |
| `SectionCard` | `shared/qml/App/Widgets/SectionCard.qml` | Card container with title + action button |
| `ActivityFeed` | `shared/qml/App/Widgets/ActivityFeed.qml` | Comment/activity timeline |
| `DetailTabBar` | `shared/qml/App/Widgets/DetailTabBar.qml` | Tab bar for detail views |
| `MasterDetailLayout` | `shared/qml/App/Layouts/MasterDetailLayout.qml` | Split master-detail pane layout |
| `WorkspaceFrame` | `shared/qml/App/Layouts/WorkspaceFrame.qml` | Header + toolbar + content frame |

Platform Python services available (do not duplicate):

| Service | Module | Use in PM |
|---------|--------|-----------|
| `PartyService` | `platform/party` | Client selector in project create/edit |
| `EmployeeService` | `platform/org` | Resource employee link selector |
| `SiteService` | `platform/org` | Site selector in project create/edit |
| `ApprovalService` | `platform/approval` | Baseline, assignment-override, and cost-increase approval flows |
| `DocumentService` | `platform/documents` | Document link panel in all entity details |
| `TimeService` | `platform/time` | Timesheets workspace delegation |
| `AccessControlService` | `platform/access` | Project-level RBAC membership |
| `AuditService` | `platform/audit` | Activity feeds in all detail panels |

#### Broken / stubbed items found

| Item | Controller method | Status |
|------|-------------------|--------|
| Export Projects | `exportProjects()` | Empty `pass` stub |
| Export Tasks | `exportTasks()` | Returns static message string |
| Export Resources | `exportResources()` | Empty `pass` stub |
| Export Financials | `exportFinancials()` | TODO comment, no implementation |
| Export Schedule | `exportSchedule()` | Returns "Export adapter pending" string |
| Risk workspace | `RiskWorkspaceController` | Delegates entirely to `RegisterWorkspaceController` with `mode="risk"` flag — functional but not dedicated |

#### Backend services implemented but not yet wired to UI

These are the enterprise services completed in steps 1–14 that have no UI connection today.
Each must be surfaced in the exact location listed.

| Backend service / type | Implemented in | UI location required |
|------------------------|---------------|----------------------|
| `ResourceAvailabilityService` | `application/resources/` | Tasks › Assign Resource dialog; Resources › Availability tab; Portfolio › Capacity vs Demand; Dashboard › Resource Overload card |
| `AssignmentValidationResult` | `application/resources/assignment_validation.py` | Tasks › Assign Resource dialog — validation panel (skills matched, certs valid, conflict flags) |
| `ResourceSkill` / `ResourceCertification` | `domain/resources/skills.py` | Resources › Skills tab; Resources › Certifications tab |
| `TaskSkillRequirement` | `domain/resources/skills.py` | Tasks › Skills/Certifications tab; Tasks › assignment validation display |
| `BaselineService.submit_baseline` / `.approve_baseline` / `.reject_baseline` | `application/scheduling/baseline_service.py` | Scheduling › Baselines tab — lifecycle action buttons (Submit, Approve, Reject) |
| `BaselineVarianceRecord` | `domain/scheduling/baseline.py` | Scheduling › Baselines tab — variance table; Dashboard › Baseline Variance card; Financials › Variance tab |
| `ScheduleChangeImpactService` | `application/scheduling/schedule_change_impact_service.py` | Tasks › Schedule Impact tab; Scheduling › Change Impact tab |
| `BaselineComparisonService` | `application/scheduling/baseline_comparison_service.py` | Scheduling › Baselines tab — comparison table; Dashboard › Baseline Variance card |
| `ForecastCostService` (EAC/ETC) | `application/financials/forecast_cost_service.py` | Financials › Forecast tab; Financials › EVM tab; Dashboard › Financial Health card |
| `CommitmentSummary` / `MaterialRollup` / `CostForecastResult` | `application/financials/forecast_cost_service.py` | Financials › Forecast tab summary strip |
| `CommitmentStatus` on `CostItem` | `domain/financials/cost.py` | Financials › Cost Breakdown tab — commitment_status column + StatusChip |
| `EACMethod` selector | `application/financials/forecast_cost_service.py` | Financials › Forecast tab — EAC method ComboBox |
| `ConstraintValidator` output | `application/scheduling/constraint_validator.py` | Scheduling › Constraints tab — violation list with severity chips |
| `CalendarResolver` per-task calendar | `application/scheduling/calendar_resolver.py` | Tasks › Schedule Impact tab — "Calendar source" field; Scheduling › Calendar tab |
| `ResourceLevelingEngine` | `application/scheduling/resource_leveling_engine.py` | Scheduling › Resource Conflicts tab — run leveling simulation button |
| `ImportPreviewModel` / `MSProjectXmlParser` / `P6Parser` | `infrastructure/importers/import_parser.py` | Projects workspace — Import dialog (CSV / MS Project XML / P6 XER); Tasks › bulk import |
| `ImportMappingProfile` / `ImportFieldMapping` | `infrastructure/importers/import_parser.py` | Import dialog — field mapping step |
| `ReportDefinition` / `SavedReportView` | `infrastructure/reporting/report_definition.py` | Dashboard › Reports section; Financials › Reports tab; Portfolio › Executive reports |
| `AsyncThresholdGuard` | `application/common/async_threshold.py` | Controller/API layer — route LARGE/XLARGE workloads to async; show progress UX |
| `PageRequest` / `PaginatedResult[T]` | `application/common/pagination.py` | All workspace tables — cursor-based pagination for large datasets |
| `WorkloadScale` async progress UX | `application/common/async_threshold.py` | All expensive operations — show `LoadingOverlay` while async, dismiss on completion signal |

---

### Phase 1: Workspace-by-Workspace Plan

#### 1. Projects Workspace

Existing: project list table, detail panel (9 lazy tabs), create/edit/delete/status
dialogs, bulk delete/status, lazy-load tasks/resources/financials/risks/docs/activity.
Capability gates for inventory and procurement tabs are correct.

Required additions:

**Project list table** — add missing columns via DynamicTableModel / presenter:
- `forecast_cost` (from `ForecastCostService`)
- `baseline_status` chip (from `ProjectBaseline.status`, uses `StatusChip`)
- `approval_status` chip (from pending `ApprovalService` requests)
- `percent_complete` progress bar column (already available in `DataTable` progress type)

**Project detail — Overview tab** — add:
- Baseline status badge (DRAFT/SUBMITTED/APPROVED/REJECTED)
- Approved baseline name + approved-by / approved-at
- Forecast cost vs budget delta (from `ForecastCostService`)

**Project detail — new Import action** (toolbar):
- "Import from File" button → opens ImportDialog
- ImportDialog: file picker → format auto-detect (CSV / MSP XML / P6 XER) → field
  mapping step using `ImportMappingProfile` → preview table (`ImportPreviewModel`) →
  confirm → calls `DataImportService`
- Reuse `CenteredDialog`, `DataTable` for preview, `StatusChip` for validation severity

**Project detail — Financials tab** (lazy, already exists) — extend:
- Add commitment status summary strip (`CommitmentSummary` via `ForecastCostService`)
- Add EAC / budget-at-completion / cost variance row

**Fix**: `exportProjects()` — wire to `ReportingService` PDF/Excel export or disable
button with "not available" tooltip until exporter is ready. Do not leave empty stub.

---

#### 2. Tasks Workspace

Existing: task table with filters, detail panel, assignments, dependencies, time
entries, collaboration, undo/redo, saved views, bulk ops, capability-gated
material/procurement sections.

Required additions:

**Task table** — add columns:
- `constraint_type` badge (from `Task.constraint_type`, hide if null)
- `baseline_variance` indicator icon (early/late/on-track from `BaselineVarianceRecord`)
- `skill_warning` icon (from `TaskSkillRequirement` check — missing or expired cert)
- `resource_conflict` icon (from `ResourceAvailabilityService`)

**Task detail — new tabs** (lazy-loaded via `LazySectionLoader`):

*Skills/Certifications tab* (new):
- List `TaskSkillRequirement` rows for the task
- For each requirement: skill name, required cert, matched resource, validity status (`StatusChip`)
- Action: Add skill requirement, remove skill requirement
- Calls: `TaskService` skill requirement methods (to be added) or domain model directly

*Schedule Impact tab* (new):
- Calls `ScheduleChangeImpactService.preview(task_id)` on tab open
- Shows: impacted tasks list, critical path change, float change, calendar source
- Read-only, preview-only — no mutations here
- Loading state via `LoadingOverlay` (async threshold: MEDIUM+ → async)

*Costs tab* (new):
- List `CostItem` rows linked to task (`cost_type`, `planned_amount`, `commitment_status` chip)
- Summary strip: planned / committed / actual for this task

**Assign Resource dialog** — extend existing dialog:
- After resource selected, call `ResourceAvailabilityService.check_availability(resource_id, start, end)`
- Show availability panel: timeline conflicts, over-allocation %, cross-project demand
- Call `AssignmentValidationResult` service: skills matched ✓/✗, certs valid ✓/expired/missing
- If assignment requires approval (governance policy), show "Submit for Approval" button
  instead of "Assign" — calls `ApprovalService.request_change()`
- Never allow silent over-allocation; show `InlineMessage` danger if hard conflict

**Fix**: `exportTasks()` — wire to `ReportingService` or disable. Do not return a plain string.

---

#### 3. Scheduling Workspace

Existing: schedule table, calendar editor, baseline A/B comparison, recalculate button,
dependency CRUD, working-days calculator, critical/delayed toggles.

Required additions:

**Baselines tab** — extend `SchedulingBaselineSection.qml`:
- Baseline list must show `BaselineStatus` chip (DRAFT / SUBMITTED / APPROVED / REJECTED / SUPERSEDED)
- Lifecycle action buttons (appear based on current status):
  - DRAFT → "Submit for Approval" button → calls `BaselineService.submit_baseline()`
  - SUBMITTED → "Approve" and "Reject" buttons (RBAC-gated) → calls
    `BaselineService.approve_baseline()` / `.reject_baseline()`
  - APPROVED → "Create New Version" button
- Variance table (lazy): when approved baseline selected, load `BaselineVarianceRecord`
  list — task, start_variance_days, finish_variance_days, cost_variance columns
- Reuse `DataTable` + `StatusChip` for status chips

**Constraints tab** — extend `SchedulingWorkspacePage.qml`:
- Load `ConstraintValidator` results per task (constraint type, constraint date, violation severity)
- Violation list with `StatusChip` (HARD = danger, SOFT = warning)
- Filter: show violations only / show all
- Clicking a row navigates to the task

**Change Impact tab** (new section):
- "Preview Change Impact" button → collects pending uncommitted schedule changes →
  calls `ScheduleChangeImpactService` → shows impacted task table + critical path diff
- "Submit Schedule Change for Approval" button → calls `ApprovalService.request_change()`
- "Apply Approved Change" button (RBAC-gated) → persists change after approval
- Uses preview-first UX: no direct persistence from this tab without approval when governed

**Resource Conflicts tab** — extend `ResourceLoadingSection`:
- Add "Run Leveling Simulation" button → calls `ResourceLevelingEngine.propose(project_id)`
- Show leveling proposal: task shifts, resource conflict resolution list
- Read-only proposal until user explicitly "Apply Leveling" (with confirmation dialog)
- Uses `LoadingOverlay` (LARGE threshold for large project → async routing via `AsyncThresholdGuard`)

**Calendar tab** — extend to show per-task calendar source:
- Column: calendar resolution chain (resource calendar → project → site → org → default)
- Sourced from `CalendarResolver`; displayed as informational, not editable here

**Fix**: `exportSchedule()` — wire to `ReportingService` Gantt/Excel or disable.

---

#### 4. Resources Workspace

Existing: resource list, detail section, create/edit/toggle-active/delete, bulk ops,
employee link, category/active filters.

Required additions (all via new lazy tabs on resource detail):

**Skills tab** (new):
- List `ResourceSkill` records for the selected resource
- Columns: skill_code, skill_name, proficiency_level, notes
- Actions: Add Skill, Remove Skill
- Uses `SectionCard` + `DataTable`

**Certifications tab** (new):
- List `ResourceCertification` records
- Columns: cert_name, issued_by, effective_date, expiry_date, `StatusChip` (valid / expiring-soon / expired)
- "Expiring soon" = within 30 days of today
- Actions: Add Certification, Update Validity, Remove
- Cert status colours: valid → success, expiring-soon → warning, expired → danger

**Availability tab** (new):
- Calls `ResourceAvailabilityService.get_availability(resource_id, window)` on tab open
- Shows: availability timeline (per-week allocation %), project demand bars, vacation/non-working days
- Over-allocation highlighted in danger colour
- Cross-project conflict list (project name, task name, overlap dates)
- Reuses `KpiStrip` for summary (available days, committed days, remaining capacity)

**Allocations tab** (new):
- List all active `TaskAssignment` rows for this resource across projects
- Columns: project, task, allocation %, hours_logged, start, end
- Click row → navigate to task

**Resource list table** — add columns:
- `skills_count` (integer)
- `cert_status` chip (all-valid / expiring-soon / expired — worst-case badge)
- `utilization_pct` progress bar
- `conflict` warning icon (from `ResourceAvailabilityService`)

**Fix**: `exportResources()` — wire to ReportingService or disable.

---

#### 5. Financials Workspace

Existing: cost item list, create/edit/delete, cashflow section, ledger section,
source analytics, cost-type analytics, procurement capability gate.

Required additions:

**Cost items table** — add columns:
- `commitment_status` chip (UNCOMMITTED / COMMITTED / INVOICED / PAID via `CommitmentStatus`)
- `forecast_amount` column (from `CostItem.forecast_amount`)
- `vendor_reference` column (optional, hide if blank)

**Forecast tab** (new):
- Summary strip via `KpiStrip`:
  - BAC (budget at completion)
  - AC (actual cost)
  - EV (earned value)
  - ETC (estimate to complete)
  - EAC (estimate at completion)
  - CV (cost variance)
- EAC method selector: `ComboBox` bound to `EACMethod` enum
  (MANUAL / BAC_OVER_CPI / AC_PLUS_ETC_AT_PLAN / AC_PLUS_ETC_AT_CPI)
- "Recalculate Forecast" button → calls `ForecastCostService.compute_forecast()`
- Threshold alert: if EAC > budget threshold, show `InlineMessage` danger
- Commitment summary strip: committed / invoiced / paid totals + exposure %

**EVM tab** (new):
- Displays earned-value metrics from `ReportingService.get_project_kpis()` / EVM mixin
- Columns/metrics: BCWS, BCWP, ACWP, SPI, CPI
- Chart: S-curve (planned vs actual vs EV) — reuse existing chart component from Dashboard

**Variance tab** (new):
- Baseline variance: planned cost vs current baseline cost by task
- Sources: `BaselineVarianceRecord.cost_variance` + `BaselineComparisonService`
- Filtered to cost-significant variances (> threshold)

**Fix**: `exportFinancials()` — wire to `ReportingService` cost breakdown report or disable.

---

#### 6. Risk Workspace

Existing: reuses `RegisterWorkspaceController` with `workspace_mode="risk"`.
Functional but not dedicated. No changes needed to the controller delegation pattern —
it is correct architecture. Risk workspace only needs UI surfacing of register-linked
entities.

Required additions:

**Risk detail — Schedule Impact field**:
- If a risk has a linked task, show schedule impact preview (calls `ScheduleChangeImpactService`)
- Read-only impact summary: days at risk, affected task count

**Risk detail — Cost Impact field**:
- If risk has cost impact, show planned impact amount and linked cost items

**Risk detail — Change Request link**:
- If a change request exists (via `ApprovalService`), show its status chip + link to
  Collaboration workspace inbox

**Risk list** — add columns:
- `schedule_impact` (days at risk, if linked task)
- `cost_impact` (amount, if present)
- `change_request_status` chip

No controller changes needed — all data added to presenter `build_workspace_state()`
by extending the `RegisterCatalogWorkspaceViewModel`.

---

#### 7. Portfolio Workspace

Existing: intake items, templates, scenarios (A/B comparison), heatmap, dependencies,
recent actions, evaluation.

Required additions:

**Capacity vs Demand tab** (new):
- Aggregates `ResourceAvailabilityService.get_portfolio_demand()` across all portfolio projects
- Shows: total demand by role/skill vs available capacity
- Over-capacity roles highlighted (danger colour)
- Reuses `DataTable` + `KpiStrip`
- Loading: XLARGE threshold → async via `AsyncThresholdGuard`, show `LoadingOverlay`

**Budget aggregation** — extend Portfolio Overview / Executive section:
- Add budget / forecast / variance columns per project (from `ForecastCostService`)
- Add baseline status badge per project (from `ProjectBaseline.status`)

**Risk Exposure tab** — extend:
- Aggregate `RegisterService.get_project_summary()` across all portfolio projects
- Show: total open risks, total open issues, critical risk count, cost exposure

**Scenario comparison** — extend existing A/B:
- Add baseline comparison column (which baseline each scenario uses)
- Add forecast cost column per scenario

No new controller needed — extend `PortfolioWorkspacePresenter.build_workspace_state()`.

---

#### 8. Register Workspace

Existing: entry list (risk/issue/change), detail panel, create/edit/delete, type/status/
severity/project filters.

Required additions:

**Register list table** — add columns:
- `schedule_impact_days` (if linked task + `ScheduleChangeImpactService`)
- `cost_impact_amount` (if present on entry)
- `approval_status` chip (from linked `ApprovalService` request if any)

**Register detail — Decision/Approval tab** (new):
- If entry type is CHANGE: show approval request status, submitted-by, decided-by
- "Submit Change Request" button → calls `ApprovalService.request_change(entity_type="register_entry")`
- "Add Decision Note" button → appends note to entry `response_plan`

**Register detail — Linked Tasks section** (new):
- List tasks linked to this entry (future: via a register–task link)
- For now: display tasks whose names contain the register entry title (fuzzy, presenter-side)

---

#### 9. Collaboration Workspace

Existing: notifications, inbox, activity feed, presence, mentions, approvals,
activity feed, team updates, audit.

Required additions:

**Approvals tab** — extend to show PM-specific approvals:
- Baseline approval requests (type: `baseline_change`) — link to Scheduling workspace
- Assignment override approvals (type: `assignment_override`) — link to Tasks workspace
- Cost increase approvals (type: `cost_increase`) — link to Financials workspace
- Each row: entity type, entity name, requested-by, status chip, action buttons
  (Approve / Reject — RBAC-gated)
- Calls `ApprovalService` (already passed to presenter in context.py)

**Decisions tab** — extend:
- Show register entries of type CHANGE with linked approval status
- "Open Register Entry" button → navigate to Register workspace

No controller changes — extend `CollaborationWorkspacePresenter` to query approval
list by PM entity types and map to view model rows.

---

#### 10. Timesheets Workspace

Existing: time entry grid, period management, review queue, submit/approve/reject,
project/assignment/period/status selectors.

Required additions:

**Cost Impact tab** (new):
- Shows labor cost impact of approved time entries per project
- Aggregates: resource, hours_logged, hourly_rate → labor cost total
- Compares against `CostItem` LABOR rows for same project
- Sources: `TimesheetService` (approved hours) + `CostService` (labor cost items)
- Read-only; "Refresh" button calls presenter

**My Time tab** — extend entry row:
- Show `task_skill_requirements` warning icon if time logged on task with missing cert

---

#### 11. Dashboard Workspace

Existing: health cards, operational tabs/tables, charts section, panels, activity feed,
project/baseline/period/view selectors.

Required additions:

**Baseline Variance card** (new health card):
- Sourced from `BaselineComparisonService` / `BaselineVarianceRecord`
- Shows: projects ahead / on-track / behind baseline
- Links to Scheduling > Baselines tab

**Resource Overload card** (new health card):
- Sourced from `ResourceAvailabilityService`
- Shows: resources over-allocated count, worst-case %
- Links to Resources > Availability tab

**Financial Health card** — extend existing:
- Add EAC / CPI from `ForecastCostService`
- Add commitment exposure %

**Pending Approvals card** (new):
- Count of pending PM approvals (baselines + assignments + costs)
- Sourced from `ApprovalService` filtered to PM entity types
- Links to Collaboration > Approvals tab

**Reports section** (new panel):
- List `SavedReportView` records from `ReportingService`
- "Open Report" → renders via `ReportDefinition` renderer
- Reuses `DataTable` for report table display
- Common saved views: Project KPIs, EVM Summary, Resource Utilization, Baseline Variance

All new cards follow the existing `DashboardHealthCard.qml` pattern.
All are read-only and link to source workspaces.

---

### Phase 2: Backend-to-UI Mapping Matrix

| Backend service | Projects | Tasks | Scheduling | Resources | Financials | Risk | Portfolio | Register | Collab | Timesheets | Dashboard |
|----------------|----------|-------|------------|-----------|------------|------|-----------|----------|--------|------------|-----------|
| `ResourceAvailabilityService` | — | Assign dialog | Conflicts tab | Availability tab | — | — | Capacity tab | — | — | — | Overload card |
| `AssignmentValidationResult` | — | Assign dialog | — | Availability tab | — | — | — | — | — | — | — |
| `ResourceSkill` | — | Skills tab | — | Skills tab | — | — | — | — | — | — | — |
| `ResourceCertification` | — | Skills tab | — | Certs tab | — | — | — | — | — | — | — |
| `TaskSkillRequirement` | — | Skills tab, assign | — | — | — | — | — | — | — | Time row | — |
| `BaselineService` lifecycle | — | — | Baselines tab | — | — | — | — | — | Approvals tab | — | — |
| `BaselineVarianceRecord` | Overview tab | — | Baselines tab | — | Variance tab | — | Overview | — | — | — | Baseline card |
| `ScheduleChangeImpactService` | — | Sched Impact tab | Change Impact tab | — | — | Risk detail | — | Register detail | — | — | — |
| `BaselineComparisonService` | Overview | — | Baselines tab | — | Variance tab | — | — | — | — | — | Baseline card |
| `ForecastCostService` | List cols | — | — | — | Forecast tab | — | Overview | — | — | — | Financial card |
| `CommitmentStatus` | — | Costs tab | — | — | Cost table | — | — | — | — | — | — |
| `EACMethod` | — | — | — | — | Forecast tab | — | — | — | — | — | — |
| `ConstraintValidator` | — | — | Constraints tab | — | — | — | — | — | — | — | — |
| `CalendarResolver` | — | Sched Impact tab | Calendar tab | — | — | — | — | — | — | — | — |
| `ResourceLevelingEngine` | — | — | Conflicts tab | — | — | — | Capacity tab | — | — | — | — |
| `ImportPreviewModel` | Import dialog | Bulk import | — | — | — | — | Intake | — | — | — | — |
| `MSProjectXmlParser` / `P6Parser` | Import dialog | — | — | — | — | — | — | — | — | — | — |
| `ReportDefinition` / `SavedReportView` | — | — | Export | — | Reports tab | — | Exec reports | — | — | — | Reports section |
| `AsyncThresholdGuard` | All exports | Assign, tree | Recalc, leveling | Util loads | Forecast | — | Capacity, agg | — | — | — | Aggregation |
| `PageRequest` / `PaginatedResult` | Project list | Task list | Schedule table | Resource list | Cost list | Register list | Portfolio list | Register list | — | Queue | Op tables |

---

### Phase 3: Shared Component Usage Rules

- All new status columns → `StatusChip`
- All new detail panels → `SlideOverPanel` or `SectionDetailPage` (do not create new panel types)
- All new confirmation actions → `CenteredDialog` (confirm/cancel pattern)
- All new async operations → `LoadingOverlay` during wait; dismiss on signal
- All new empty states → `EmptyState` (title + message)
- All new validation messages → `InlineMessage` (tone: info / warning / danger)
- All new tabbed detail sections → `DetailTabBar`
- All new tables → `DataTable` with `DynamicTableModel`
- All new toolbars → `TableToolbar` (reuse search/filter/create button slots)
- All new metric strips → `KpiStrip`
- All new card containers → `SectionCard`
- Never create a new dialog base; extend `CenteredDialog`
- Never create a new drawer; extend `SlideOverPanel`

---

### Phase 4: Capability-Gating Rules

Apply `hasCapability()` check before showing active controls (already done for
inventory/procurement — extend to all new cross-module features):

| Feature | Capability gate | Behaviour when disabled |
|---------|----------------|------------------------|
| Document link buttons | `documents.link.create` | Disable button + tooltip "Documents module not enabled" |
| Approval submit buttons | `approvals.change_request.create` | Show local status only; hide Submit/Approve buttons |
| Timesheet cost impact | `timesheets.entries.read` | Hide Cost Impact tab entirely |
| Procurement cost view | `procurement.purchase_orders.read` | Existing gate — no change |
| Material demand section | `inventory.reservations.create` | Existing gate — no change |
| Import MS Project XML | `pm.import.xml` (internal) | Disable XML option in format selector |
| Import P6 XER | `pm.import.xer` (internal) | Disable XER option in format selector |

All disabled states must show a tooltip explaining why (not just visually grey out).

---

### Phase 5: Async / Loading UX Rules

All operations classified as `WorkloadScale.LARGE` or `XLARGE` by `AsyncThresholdGuard`
must follow this pattern in the controller layer:

1. Controller calls `AsyncThresholdGuard.classify_*(count)` before dispatching
2. If `should_run_async()` returns True: show `LoadingOverlay`, dispatch to background thread
3. Background thread emits `finished` signal with result
4. Controller receives signal, hides overlay, updates view-model property
5. If error: hide overlay, emit `operationFailed(message)` signal → QML shows `InlineMessage` danger

Operations that must use this pattern:
- `recalculate_project_schedule` (> 500 tasks → async)
- `ResourceLevelingEngine.propose` (> 200 resources → async)
- `ForecastCostService.compute_forecast` (> 5000 cost rows → async)
- `ScheduleChangeImpactService.preview` (> 500 tasks → async)
- `PortfolioResourcePoolService.get_demand` (> 50 projects → async)
- All report renders

---

### Phase 6: Implementation Order

Priority order based on user-visible impact and dependency chain:

1. **Financials — CommitmentStatus + Forecast tab** (ForecastCostService wired to presenter)
   - Adds: commitment status chips in cost table, Forecast/EVM tab, EAC computation
   - Files: `FinancialsWorkspacePage.qml`, `FinancialsWorkspacePresenter`, controller signals

2. **Scheduling — Baseline lifecycle actions** (BaselineService.submit/approve/reject)
   - Adds: status chips in baseline list, Submit/Approve/Reject action buttons
   - Files: `SchedulingBaselineSection.qml`, `SchedulingWorkspacePresenter`, controller slots

3. **Scheduling — Constraint violations tab** (ConstraintValidator output)
   - Adds: constraint violation list with severity chips
   - Files: new `SchedulingConstraintsSection.qml` tab, presenter + controller signals

4. **Resources — Skills + Certifications tabs** (ResourceSkill, ResourceCertification)
   - Adds: two new lazy-loaded tabs on resource detail
   - Files: new `ResourcesSkillsSection.qml`, `ResourcesCertificationsSection.qml`, presenter

5. **Tasks — Assignment dialog validation** (ResourceAvailabilityService, AssignmentValidationResult)
   - Adds: availability panel + validation display in existing assign dialog
   - Files: extend `TasksAssignmentsSection.qml`, presenter `build_task_assignments_state()`

6. **Tasks — Skills/Certs tab** (TaskSkillRequirement)
   - Adds: skill requirements section on task detail
   - Files: new `TasksSkillsSection.qml` tab, presenter

7. **Scheduling — Baseline variance table** (BaselineVarianceRecord)
   - Adds: variance rows in baseline section after approval
   - Files: extend `SchedulingBaselineSection.qml`, presenter + controller

8. **Tasks — Schedule Impact tab** (ScheduleChangeImpactService)
   - Adds: new lazy tab on task detail
   - Files: new `TasksScheduleImpactSection.qml`, presenter, controller signals

9. **Projects — Import dialog** (ImportPreviewModel, MSProjectXmlParser, P6Parser)
   - Adds: Import action in projects toolbar → multi-step import dialog
   - Files: new `ProjectsImportDialog.qml`, presenter `preview_import()` / `execute_import()`, controller

10. **Dashboard — Baseline Variance + Resource Overload + Reports** cards
    - Adds: three new health/summary cards
    - Files: extend `DashboardWorkspacePage.qml`, `DashboardWorkspacePresenter`, controller signals

11. **Financials — Variance tab** (BaselineVarianceRecord cost side)
    - Files: new `FinancialsVarianceSection.qml`, presenter

12. **Resources — Availability tab** (ResourceAvailabilityService full panel)
    - Files: new `ResourcesAvailabilitySection.qml`, presenter + controller

13. **Portfolio — Capacity vs Demand tab** (PortfolioResourcePoolService)
    - Files: new `PortfolioCapacitySection.qml`, presenter + controller

14. **Collaboration — PM Approvals wiring** (ApprovalService PM entity types)
    - Files: extend `CollaborationWorkspacePage.qml` approvals tab, presenter

15. **Scheduling — Change Impact + Leveling tabs**
    - Files: new `SchedulingChangeImpactSection.qml`, `SchedulingResourceLevelingSection.qml`

16. **Export stubs → real implementation or disabled state**
    - Fix all 5 export stubs to either wire ReportingService or show disabled + tooltip
    - Files: all 5 workspace controllers + presenters

---

### Phase 7: New Presenter/Controller Methods Required

For each implementation step above, the following presenter and controller additions
are needed (listed by workspace, not duplicating existing methods):

**FinancialsWorkspacePresenter** (extend):
- `build_forecast_state(project_id, method) -> ForecastTabViewModel`
- `build_evm_state(project_id, baseline_id) -> EvmTabViewModel`
- `build_variance_state(project_id, baseline_id) -> VarianceTabViewModel`
- `compute_forecast(project_id, method, percent_complete) -> CostForecastResult`

**SchedulingWorkspacePresenter** (extend):
- `submit_baseline(baseline_id, submitted_by, notes) -> None`
- `approve_baseline(baseline_id, approved_by, notes) -> None`
- `reject_baseline(baseline_id, notes) -> None`
- `build_baseline_variance_state(baseline_id) -> BaselineVarianceTabViewModel`
- `build_constraint_violations_state(project_id) -> ConstraintViolationsViewModel`
- `build_change_impact_state(project_id, pending_changes) -> ChangeImpactViewModel`
- `propose_leveling(project_id) -> LevelingProposalViewModel`
- `apply_leveling(project_id, proposal_id) -> None`

**ResourcesWorkspacePresenter** (extend):
- `build_skills_state(resource_id) -> ResourceSkillsViewModel`
- `build_certifications_state(resource_id) -> ResourceCertificationsViewModel`
- `build_availability_state(resource_id, window_days) -> ResourceAvailabilityViewModel`
- `build_allocations_state(resource_id) -> ResourceAllocationsViewModel`
- `add_skill(resource_id, payload) -> None`
- `remove_skill(resource_id, skill_id) -> None`
- `add_certification(resource_id, payload) -> None`
- `update_certification(resource_id, cert_id, payload) -> None`
- `remove_certification(resource_id, cert_id) -> None`

**TasksWorkspacePresenter** (extend):
- `build_task_skills_state(task_id) -> TaskSkillsViewModel`
- `build_task_schedule_impact_state(task_id) -> ScheduleImpactViewModel`
- `build_task_costs_state(task_id) -> TaskCostsViewModel`
- `add_task_skill_requirement(task_id, payload) -> None`
- `remove_task_skill_requirement(task_id, req_id) -> None`
- `validate_assignment(resource_id, task_id, start, end, hours) -> AssignmentValidationResult`
- `request_assignment_override(task_id, resource_id, payload) -> None`

**ProjectsWorkspacePresenter** (extend):
- `preview_import(file_path, format) -> ImportPreviewModel`
- `execute_import(session_id, mapping_profile_id) -> ImportSessionResult`

**DashboardWorkspacePresenter** (extend):
- `build_baseline_variance_card_state(project_id) -> BaselineVarianceCardViewModel`
- `build_resource_overload_card_state() -> ResourceOverloadCardViewModel`
- `build_pending_approvals_card_state() -> PendingApprovalsCardViewModel`
- `build_reports_state(project_id) -> ReportsTabViewModel`

**CollaborationWorkspacePresenter** (extend):
- `build_pm_approvals_state(project_id) -> PmApprovalsViewModel`
- `approve_pm_request(approval_id) -> None`
- `reject_pm_request(approval_id, reason) -> None`

**PortfolioWorkspacePresenter** (extend):
- `build_capacity_demand_state(project_ids) -> CapacityDemandViewModel`

---

### Known Limitations (Post-Audit)

1. **DataTable has no native tree expansion** — WBS hierarchy in tasks uses a flat
   filtered list (children loaded on demand via `LazyObjectLoader`). This is
   functional but not a true tree table. A dedicated tree-table component may be
   needed in a later phase for deep WBS hierarchies.

2. **No export infrastructure** — `infrastructure/exporters/` is empty. All export
   actions must be disabled with a tooltip until `ReportingService` renderers
   (Excel, PDF, Gantt) are connected via an exporter adapter. Do not ship empty stubs.

3. **Risk workspace uses register controller** — the delegation via `workspace_mode="risk"`
   is correct and intentional. A dedicated `RiskWorkspaceController` is not required
   unless the risk workspace needs materially different data flows.

4. **QML has no built-in permission check** — all RBAC-gated buttons must receive
   their enabled/visible state from the Python controller as a Q_PROPERTY or signal.
   Controllers must expose `canApproveBaseline`, `canManageSkills`, etc. as bool
   properties computed from `AuthorizationEngine.has_permission()`.

5. **Import dialog is net-new** — no existing import dialog component exists in the
   PM QML layer. `ProjectsImportDialog.qml` must be built as a new multi-step
   `CenteredDialog` using the existing shared components (file picker, `DataTable`
   for preview, field mapping section).

6. **Async progress UX not wired** — `AsyncThresholdGuard` exists in the backend but
   no controller currently checks it before dispatching. Each LARGE+ operation must
   be retrofitted with the classify → `should_run_async()` → background-thread →
   signal pattern described in Phase 5 above.
- `docs/integration_plan.md`
