# Pydantic CRUD Validation Migration

## Purpose

This document tracks the migration from passive repo-bound dataclasses plus duplicated presenter/service validation to Pydantic-validated CRUD DTOs closer to the database-facing layer.

The goal is to make the mutable write models used under services own field-level validation and normalization, while preserving service-layer business rules, tenancy enforcement, RBAC checks, repository lookups, and workflow invariants.

## Enterprise Standard Position

For this codebase, the standard enterprise SaaS pattern is:

- a shared mutable write model used by services and repositories
- field validation and normalization on that shared write model
- business-policy, tenant, RBAC, and repository-aware validation in services
- database constraints as the final persistence safety net

This means the preferred validation boundary is not:

- presenter validation
- desktop-only command DTOs
- HTTP-only request DTOs
- raw ORM models

This also means we should avoid creating an extra parallel DTO layer if the existing mutable write entity already serves as the service-to-repository contract.

The preferred boundary is the deeper shared CRUD DTO/entity that both current and future transports pass through before persistence.

## Current Findings

### 1. Transport command models are not the best long-term validation boundary

The repo currently has these command-model concentrations:

- `src/api/desktop/platform`: 43 command classes
- `src/core/modules/project_management/api/desktop`: 38 command classes
- `src/core/modules/maintenance/api/desktop`: 20 command classes
- `src/core/modules/inventory_procurement/api/desktop`: 26 command classes

These show where duplication exists today, but they are not the best final validation boundary because HTTP and any future transports would duplicate the same schemas again.

The better shared boundary in this repo is the mutable DTO/entity layer that services pass toward repositories and reconstruct from repositories.

### 2. Validation is duplicated across layers

Current duplication pattern:

- QML presenters coerce raw dialog payloads with helpers like `require_text`, `optional_date`, `require_float`, `string_value`, and `int_value`
- desktop/http command models are passive dataclasses and do not validate their own inputs
- application services still perform some overlapping input checks in addition to business-rule validation

Observed inventory:

- `21` `validation.py` files under `src`
- `16` presenter validation-import call sites in PM + platform alone

### 3. Not all dataclasses should be migrated

The repo uses dataclasses broadly for:

- mutable CRUD entities / write DTOs
- read DTOs
- view models
- report rows
- snapshots
- events

Only the repo-bound mutable CRUD models are the primary target. Replacing every dataclass would create churn without removing the actual validation duplication.

### 4. `pydantic` exists in `pmenv` but is not declared

The `pmenv` conda environment already has `pydantic 2.13.4` installed, but `requirements.txt` does not currently declare it. That means the runtime can work locally while the repo still lacks dependency truth.

## Full Entity Map

### 1. Primary migration targets

These are the mutable persisted entities that already sit behind repository `update(...)`, `save(...)`, or equivalent write contracts. These are the main migration targets because they are the repo-bound CRUD models that services already mutate.

#### Platform

Primary platform targets:

- `Organization`
- `Site`
- `Department`
- `Employee`
- `Party`
- `ProjectMembership`
- `ScopedAccessGrant`
- `UserAccount`
- `AuthSession`
- `ApprovalRequest`
- `PlatformCalendar`
- `CalendarException`
- `CalendarRecurringEvent`
- `ShiftPattern`
- `DocumentStructure`
- `Document`
- `Tenant`
- `TimeEntry`
- `TimesheetPeriod`
- `PlatformEvent`
- `RuntimeExecution`

Notes:

- `ModuleEntitlementRecord` is also persisted and mutable, but it uses repository `upsert(...)` rather than plain `update(...)`
- `CalendarWorkingRule`, `ShiftPatternDay`, and calendar assignment rows use `save(...)` contracts and belong in the secondary tier below

#### Project Management

Primary PM targets:

- `Project`
- `ProjectResource`
- `Task`
- `TaskAssignment`
- `TaskDependency`
- `Resource`
- `CostItem`
- `CalendarEvent`
- `RegisterEntry`
- `PortfolioIntakeItem`
- `PortfolioScenario`
- `PortfolioScoringTemplate`
- `TaskComment`

Notes:

- `Project` and `ProjectResource` were migrated in the first slice
- `Task`, `TaskAssignment`, and `TaskDependency` were migrated in the second slice
- `Resource` was migrated in the third slice
- `CostItem` was migrated in the fourth slice
- `CalendarEvent` was migrated in the fifth slice
- `RegisterEntry` was migrated in the sixth slice
- `PortfolioIntakeItem`, `PortfolioScenario`, and `PortfolioScoringTemplate` were migrated in the seventh slice
- `TaskComment` was migrated in the eighth slice
- `Organization` and `Site` were migrated in the ninth slice
- `Department` and `Employee` were migrated in the tenth slice
- `Party` was migrated in the eleventh slice
- `TimeEntry` and `TimesheetPeriod` were migrated in the twelfth slice
- `ProjectMembership` and `ScopedAccessGrant` were migrated in the thirteenth slice
- `UserAccount` and `AuthSession` were migrated in the fourteenth slice
- `ApprovalRequest`, `Tenant`, `PlatformEvent`, and `RuntimeExecution` were migrated in the fifteenth slice
- `DocumentLink` was migrated in the sixteenth slice
- `UserTenantMembership` was migrated in the seventeenth slice
- `Role`, `Permission`, `UserRoleBinding`, and `RolePermissionBinding` were migrated in the eighteenth slice
- `ModuleEntitlementRecord` was migrated in the nineteenth slice

#### Maintenance

Primary maintenance targets:

- `MaintenanceLocation`
- `MaintenanceSystem`
- `MaintenanceAsset`
- `MaintenanceAssetComponent`
- `MaintenanceWorkRequest`
- `MaintenanceWorkOrder`
- `MaintenanceWorkOrderTask`
- `MaintenanceWorkOrderTaskStep`
- `MaintenanceWorkOrderMaterialRequirement`
- `MaintenanceSensor`
- `MaintenanceIntegrationSource`
- `MaintenanceSensorSourceMapping`
- `MaintenanceSensorException`
- `MaintenanceFailureCode`
- `MaintenanceDowntimeEvent`
- `MaintenanceTaskTemplate`
- `MaintenanceTaskStepTemplate`
- `MaintenancePreventivePlan`
- `MaintenancePreventivePlanTask`
- `MaintenancePreventivePlanInstance`
- `MaintenanceBlackoutWindow`

#### Inventory / Procurement

Primary inventory/procurement targets:

- `InventoryItemCategory`
- `StockItem`
- `Storeroom`
- `StockBalance`
- `StockReservation`
- `StorageLocation`
- `ReorderPolicy`
- `CycleCount`
- `PurchaseRequisition`
- `PurchaseRequisitionLine`
- `PurchaseOrder`
- `PurchaseOrderLine`
- `ReceiptHeader`
- `ReceiptLine`

### 2. Secondary migration targets

These are persisted entities too, but they are lower priority because they are create-only, save-only child rows, append-oriented rows, or more tightly system-managed.

#### Platform

Secondary platform targets:

- `CalendarWorkingRule`
- `ShiftPatternDay`
- `SiteCalendarAssignment`
- `DepartmentCalendarAssignment`
- `EmployeeCalendarAssignment`
- `DocumentLink`
- `UserTenantMembership`
- `ModuleEntitlementRecord`
- `Role`
- `Permission`
- `UserRoleBinding`
- `RolePermissionBinding`

#### Project Management

Secondary PM targets:

- `ProjectCalendarAssignment`
- `ResourceCalendarAssignment`
- `ResourceSkill`
- `ResourceCertification`
- `TaskSkillRequirement`
- `PortfolioProjectDependency`
- `ProjectBaseline`
- `BaselineTask`
- `BaselineVarianceRecord`
- `TaskPresence`

#### Maintenance

Secondary maintenance targets:

- `MaintenanceSensorReading`

#### Inventory / Procurement

Secondary inventory/procurement targets:

- `StockTransaction`
- `ReceiptHeader`
- `ReceiptLine`

### 3. Non-target dataclasses

These should not be part of the first validation migration unless a later need appears:

- read DTOs and query projections
- dashboard/report/export/import preview models
- snapshots and comparison rows
- inbox/notification/workspace read models
- activity/audit append-only event rows
- frozen catalog and presentation models

Examples in the repo:

- `PortfolioExecutiveRow`
- `PortfolioRecentAction`
- `PortfolioScenarioEvaluation`
- `PortfolioProjectDependencyView`
- `CollaborationInboxItem`
- `CollaborationWorkspaceSnapshot`
- `CollaborationNotificationItem`
- `ModuleCatalogSnapshot`
- `ImportPreview`
- `ReportDocument`

## Detailed Entity Breakdown

## Validation Helper File Audit

This audit is specifically about helper files such as `validation.py`, `*_validation.py`, and similar support files that may duplicate field validation after the move to entity-based CRUD validation.

### Removed as structural duplicate

#### `src/core/modules/project_management/application/projects/commands/validation.py`

Decision:

- removed

Reason:

- after migrating `Project` to the shared mutable write-model validation pattern, this file no longer carried a distinct validation layer
- it only held a small project-name duplicate check used by one caller
- that remaining repository-aware uniqueness check belongs directly in the service/lifecycle layer, not in a separate validation file

Action taken:

- folded the remaining helper into `ProjectLifecycleMixin`
- deleted the extra file

### Keep for now: contains service/business rules

#### `src/core/modules/project_management/application/tasks/commands/validation.py`

Decision:

- keep, but trimmed

Reason:

- after migrating `Task`, `TaskAssignment`, and `TaskDependency`, the entity-local CRUD checks moved into the write models
- the remaining file now holds only service/business rules:
  - task within project date range
  - resource overallocation checks

Action taken:

- removed duplicated local helpers for:
  - task name
  - task date scalar checks
  - self-dependency guard
  - unused circular-dependency helper superseded by dependency diagnostics
- kept project-scope date-window validation and allocation policy checks in service code

#### `src/core/platform/department/application/department_validation.py`

Decision:

- keep

Reason:

- repo-aware existence and scope validation
- validates referenced site, parent department, and manager employee against active organization state
- this is service-layer validation, not duplicate field validation

#### `src/core/modules/inventory_procurement/application/catalog/item_validation.py`

Decision:

- keep, but partially revisit later

Reason:

- `_validate_party_reference(...)` is service/repository-aware and should stay outside the entity
- `_validate_reorder_quantities(...)` and `_validate_uom_configuration(...)` are more entity-local and are candidates to move when `StockItem` is migrated

Future action:

- keep party-reference validation in services
- move reorder/UOM local invariants into the `StockItem` write model during inventory migration

#### `src/core/modules/maintenance/application/work_requests/validation.py`

Decision:

- keep

Reason:

- status-transition workflow rule
- this is a service/business-policy concern, not CRUD field normalization

#### `src/core/modules/maintenance/application/work_orders/work_order_validation.py`
#### `src/core/modules/maintenance/application/work_orders/work_order_task_validation.py`
#### `src/core/modules/maintenance/application/work_orders/work_order_task_step_validation.py`

Decision:

- keep

Reason:

- these are workflow transition policy files
- they enforce allowed lifecycle/status changes
- they should remain in services even after entity migration

#### `src/core/platform/auth/application/auth_validation.py`

Decision:

- keep, but split by concern over time

Reason:

- password policy is service-level because raw passwords are not persisted as entity fields
- email normalization/format checks may eventually move closer to `UserAccount` if the repo chooses to validate persisted email shape there too

Future action:

- keep password policy in auth service
- optionally move persisted-email normalization into `UserAccount` later

#### `src/core/modules/project_management/application/portfolio/utils/portfolio_support.py`

Decision:

- keep, but trimmed

Reason:

- active-template resolution, default-template bootstrapping, and project/intake scope checks are still repository-aware service concerns
- duplicated local CRUD helpers no longer need to live outside the write models after migrating `PortfolioIntakeItem`, `PortfolioScenario`, and `PortfolioScoringTemplate`

Action taken:

- removed duplicated local helpers for:
  - intake title/sponsor required checks
  - intake score and budget/capacity scalar checks
  - intake status coercion
  - scoring-template weight range and weight-mix checks
- kept repo-aware helpers for:
  - active organization resolution
  - scoring-template lookup/activation behavior
  - accessible project filtering
  - project/intake scope validation
  - portfolio summary/audit formatting

### Platform master-data entities

#### `Organization`

Status:

- completed

Entity responsibilities:

- require `organization_code` and `display_name`
- normalize `timezone_name`, `base_currency`, and `tenant_id`
- coerce `is_active` and `version`

Service responsibilities:

- uniqueness of organization code
- active-tenant / active-organization context rules
- lifecycle decisions around switching active organization

Notes:

- `tenant_id` pinning and active-organization switching remain in service code
- duplicate code checks remain repository-aware service rules
- create/update scalar normalization now lives on the shared write model

#### `Site`

Status:

- completed

Entity responsibilities:

- require `organization_id`, `site_code`, and `name`
- normalize descriptive/location fields
- uppercase `currency_code`
- normalize `timezone`, `status`, `default_language`, `default_calendar_id`
- keep `opened_at` / `closed_at` / `is_active` date coherence

Service responsibilities:

- active organization enforcement
- site-code uniqueness within organization
- referenced calendar existence
- permission and scope filtering

Notes:

- organization-default fallback for timezone/currency/calendar remains in service code because it depends on active context
- create/update scalar normalization now lives on the shared write model
- active/inactive transition behavior remains in service code

#### `Department`

Status:

- completed

Entity responsibilities:

- require `organization_id`, `department_code`, and `name`
- normalize text and optional IDs
- uppercase `cost_center_code`
- keep `is_active`, timestamps, and notes normalized

Service responsibilities:

- active organization enforcement
- department-code uniqueness within organization
- `site_id`, `default_location_id`, `parent_department_id`, and `manager_employee_id` existence
- cross-site default-location compatibility

Notes:

- create/update scalar normalization now lives on the shared write model
- active-organization enforcement and duplicate-code checks remain in command/service code
- site, parent, manager, and default-location validation remain repo-aware service rules

#### `Employee`

Status:

- completed

Entity responsibilities:

- require `employee_code` and `full_name`
- normalize email, phone, title, department/site display text
- coerce `employment_type`
- normalize optional `organization_id`, `department_id`, and `site_id`

Service responsibilities:

- active organization enforcement
- employee-code uniqueness in organization
- department/site existence resolution
- linked resource sync and employee-resource business rules

Notes:

- create/update scalar normalization now lives on the shared write model
- employee-code uniqueness, active-organization enforcement, and department/site resolution remain service rules
- linked resource synchronization remains service-owned because it is a workflow side effect

#### `Party`

Status:

- completed

Entity responsibilities:

- require `organization_id`, `party_code`, and `party_name`
- normalize `party_type`
- normalize contact/address/website/tax/external-reference fields
- normalize `is_active`, timestamps, and notes

Service responsibilities:

- organization scoping
- uniqueness by party code
- integration-specific referential checks

Notes:

- create/update scalar normalization now lives on the shared write model
- organization scoping and duplicate-code checks remain service rules
- integration-specific referential checks remain service-owned

### Platform time, access, auth, and governance entities

#### `TimeEntry`

Status:

- completed

Entity responsibilities:

- require `work_allocation_id`, `entry_date`, and valid `hours`
- normalize owner/scope/employee/department/site metadata
- keep `assignment_id` and `owner_type` coherent
- normalize note and author fields

Service responsibilities:

- assignment/work-allocation existence
- period lock / submit / approve workflow
- timesheet ownership and approval policy
- tenant and permission enforcement

Notes:

- create/update scalar normalization now lives on the shared write model
- work-allocation existence, monthly period generation, and editability rules remain service-owned
- timesheet workflow, policy, and permission checks remain in service code

#### `TimesheetPeriod`

Status:

- completed

Entity responsibilities:

- require `resource_id`, `period_start`, and `period_end`
- validate `period_end >= period_start`
- normalize decision/submission metadata
- normalize `status`

Service responsibilities:

- resource existence
- period generation policy
- submit / approve / reject / lock transitions
- approval actor permissions

Notes:

- create/update scalar normalization now lives on the shared write model
- monthly period-bound generation remains service-owned
- submit/approve/reject/lock workflow and permission enforcement remain service rules

#### `ProjectMembership` and `ScopedAccessGrant`

Status:

- completed

Entity responsibilities:

- require scope/project and user identifiers
- normalize `scope_type` and `scope_role`
- deduplicate and normalize permission codes

Service responsibilities:

- scope existence
- allowed role-to-permission mapping
- user existence
- authorization policy matrix enforcement

Notes:

- create/update scalar normalization now lives on the shared access write models
- permission-code deduplication now happens on the shared membership/grant DTOs
- scope existence, user existence, scoped-role resolution, and RBAC/policy enforcement remain service-owned
- tenant and organization stamping remain persistence-scope concerns

#### `UserAccount`

Status:

- completed

Entity responsibilities:

- require `username` and `password_hash` on create
- normalize `display_name`, `email`, identity-provider fields, and device labels
- coerce flags and positive numeric counters
- normalize timeout/session metadata

Service responsibilities:

- password policy
- password hashing
- username uniqueness
- federated identity uniqueness
- login/lockout/MFA behavior

Notes:

- create/update scalar normalization now lives on the shared user write model
- email format, federated-identity completeness, device-label normalization, and session-timeout coercion now live on `UserAccount`
- password strength, hashing, uniqueness checks, MFA, and lockout/session workflow remain service-owned

#### `AuthSession`

Status:

- completed

Entity responsibilities:

- require `user_id`, `session_revision`, `auth_method`, and `expires_at`
- normalize `device_label`, tenant/org context memory, and UTC datetimes
- keep revision positive

Service responsibilities:

- session issuance and rotation
- revocation
- revalidation
- user/session matching and expiry policy

Notes:

- create/update scalar normalization now lives on the shared auth-session write model
- user/session identifiers, auth method, context IDs, and UTC datetime normalization now live on `AuthSession`
- session issuance, revocation, runtime revalidation, and expiry-policy decisions remain service-owned

#### `ApprovalRequest`, `Tenant`, `PlatformEvent`, `RuntimeExecution`

Status:

- completed

Entity responsibilities:

- require request/resource/tenant identifiers and core operation labels
- normalize request types, tenant codes, status strings, notes, usernames, metadata dictionaries, and runtime path/media fields
- validate UTC-capable timestamps plus positive/non-negative version and execution counters

Service responsibilities:

- workflow transitions
- bootstrap and provisioning rules
- retention / replay / execution lifecycle policy
- actor permission checks

Notes:

- create/update scalar normalization now lives on the shared approval, tenant, platform-event, and runtime-execution write models
- approval decision workflow, self-decision protection, duplicate-pending checks, and organization scoping remain service-owned
- tenant uniqueness, self-lockout protection, lifecycle transitions, and membership bootstrapping remain service-owned
- platform-event emission policy remains in services while the append-only event row now validates its own labels, metadata, and timestamp shape
- runtime retry sequencing, cancellation flow, and execution lifecycle decisions remain service-owned while counts, metadata, paths, and status normalization now live on `RuntimeExecution`

### Platform calendar and document entities

#### `PlatformCalendar`

Status:

- completed

Entity responsibilities:

- require `organization_id`, `code`, `name`, and `calendar_type`
- normalize `timezone`, locale, scope fields, and description
- validate `effective_from <= effective_to`
- normalize `priority`, `is_default`, and `is_active`

Service responsibilities:

- calendar-code uniqueness
- active organization enforcement
- scope ownership/existence
- default-calendar business rules

Notes:

- create/update scalar normalization now lives on the shared calendar write model
- update flows use final-state replacement so `effective_from` / `effective_to` pairs validate together
- historical persisted values still reconstruct cleanly through alias-friendly normalization where needed in adjacent calendar rows

#### `CalendarException`

Status:

- completed

Entity responsibilities:

- require `calendar_id`, `exception_date`, `exception_type`, `name`, and `impact_type`
- validate time-window order
- normalize scope fields, description, approval fields, and priority
- validate `hours_override >= 0` when present

Service responsibilities:

- calendar existence
- overlap policy
- approval workflow
- scope compatibility

Notes:

- create/update scalar normalization now lives on the shared exception write model
- approval workflow and any future overlap/conflict policy remain service-owned
- legacy `NON_WORKING` impact rows are normalized to the canonical unavailable impact shape at the write-model boundary

#### `CalendarRecurringEvent`

Status:

- completed

Entity responsibilities:

- require `calendar_id`, `title`, `event_type`, `recurrence_rule`, `start_time`, `end_time`, `impact_type`, and `effective_from`
- validate `end_time > start_time`
- validate `effective_to >= effective_from`
- normalize scope fields and optional capacity impact

Service responsibilities:

- RRULE parsing / policy
- calendar existence
- overlap/conflict policy
- scope compatibility

Notes:

- create/update scalar normalization now lives on the shared recurring-event write model
- RRULE parsing intentionally remains in the service because it depends on scheduling policy and parser behavior outside simple field validation
- legacy `SHIFT` event rows and `NON_WORKING` impact rows normalize into the canonical persisted shape exposed by the write model

#### `ShiftPattern`

Status:

- completed

Entity responsibilities:

- require code/name/type-like fields
- normalize labels and flags
- validate day offsets, durations, and assignmentable state

Service responsibilities:

- uniqueness
- organization scoping
- conflict policy
- references to pattern days and assignments

Notes:

- create/update scalar normalization now lives on the shared shift-pattern write model
- `ShiftPatternDay` now validates its own local create/save invariants as part of this slice because services directly construct it
- legacy `FIXED` pattern values normalize to the canonical standard pattern shape for compatibility with seeded tests and repository reconstruction

#### `DocumentStructure`, `Document`, and `DocumentLink`

Status:

- completed

Entity responsibilities:

- require owning IDs and names/codes/titles as appropriate
- require linked document, module, and entity identifiers for relationship rows
- normalize storage-related text, labels, paths, URLs, notes, and metadata fields
- normalize linked-module/entity text and optional link roles
- validate file/structure state and version counters

Service responsibilities:

- linked-entity existence
- storage backend policy
- document-type workflow
- access control and tenant scope

Notes:

- create/update scalar normalization now lives on the shared document-structure, document, and document-link write models
- document and structure codes, enum coercion, version validation, timestamp normalization, and review-date ordering are enforced at the DTO/entity boundary
- document-link module/entity normalization now comes from `document_link.py`, so platform, maintenance, and inventory document-link flows all share one normalization source
- active-organization resolution, duplicate-code checks, structure lookup, storage-derived file-name and MIME defaults, link uniqueness, and tenant-scope enforcement remain service-owned

#### `UserTenantMembership`

Status:

- completed

Entity responsibilities:

- require membership, user, and tenant identifiers
- normalize `tenant_role`
- normalize UTC-capable membership timestamps

Service responsibilities:

- user and tenant existence
- bootstrap and registration-driven membership creation
- tenant accessibility, lifecycle, and privilege policy
- repository-level uniqueness/idempotency

Notes:

- create/update scalar normalization now lives on the shared user-tenant membership write model
- membership IDs, user/tenant identifiers, role text, and UTC datetime normalization now live on `UserTenantMembership`
- bootstrap/backfill policy, tenant-switch access checks, tenant lifecycle behavior, and membership uniqueness/idempotency remain service- and repository-owned

#### `Role`, `Permission`, `UserRoleBinding`, and `RolePermissionBinding`

Status:

- completed

Entity responsibilities:

- require role, permission, user, and binding identifiers
- normalize role names and permission codes
- normalize optional descriptions and organization scope identifiers

Service responsibilities:

- privilege ceilings and separation-of-duties policy
- role and user existence checks
- global-vs-organization assignment policy
- bootstrap/default seeding and repository-level deduplication

Notes:

- create/update scalar normalization now lives on the shared RBAC write models
- role names, permission codes, binding IDs, and optional organization-scope identifiers now normalize at the DTO boundary
- privilege ceilings, tenant guards, separation-of-duties checks, bootstrap seeding, and duplicate-binding avoidance remain service- and repository-owned

#### `ModuleEntitlementRecord`

Status:

- completed

Entity responsibilities:

- require and normalize canonical module codes
- normalize lifecycle status values
- coerce licensed/enabled flags

Service responsibilities:

- licensing availability rules
- enablement-versus-license policy
- planned-module restrictions
- organization-context and provisioning workflow

Notes:

- create/update scalar normalization now lives on the shared module-entitlement write model
- module-code alias resolution and lifecycle-status normalization now happen on `ModuleEntitlementRecord`
- planned-stage restrictions, licensing policy, organization-context requirements, and runtime enablement decisions remain service- and repository-owned

### Project-management entities

#### `Project` and `ProjectResource`

Status:

- migrated in first slice

Entity responsibilities now in place:

- required IDs/names
- text normalization
- currency normalization
- non-negative planned budget / hourly rate / planned hours
- date-range validation for project dates

Service responsibilities still kept:

- code uniqueness
- organization context match
- project/resource existence and permission checks

#### `Task`

Status:

- completed

Entity responsibilities:

- require `project_id` and `name`
- normalize `code`, `description`, `constraint_type`
- validate `start_date <= end_date`
- validate `actual_start <= actual_end`
- validate `duration_days >= 0`
- validate `0 <= percent_complete <= 100`
- validate `priority` and deadline/constraint consistency

Service responsibilities:

- project existence
- project-scope permission checks
- task-code uniqueness policy if retained
- schedule-within-project rules
- dependency-aware business rules

#### `TaskAssignment`

Status:

- completed

Entity responsibilities:

- require `task_id` and `resource_id`
- validate `0 < allocation_percent <= 100`
- validate `hours_logged >= 0`
- normalize `project_resource_id`

Service responsibilities:

- task/resource/project-resource existence
- duplicate-assignment prevention
- overallocation checks
- timesheet/work-allocation cross-rules

#### `TaskDependency`

Status:

- completed

Entity responsibilities:

- require predecessor and successor IDs
- normalize dependency type
- validate no self-dependency
- validate `lag_days` numeric shape

Service responsibilities:

- task existence
- same-project constraint
- cycle detection
- scheduling semantics and impact rules

#### `Resource`

Status:

- completed

Entity responsibilities:

- require `name`
- normalize `code`, `role`, `address`, and `contact`
- validate non-negative `hourly_rate`
- validate positive `capacity_percent`
- normalize `currency_code`
- normalize/coerce `worker_type`

Service responsibilities:

- resource-code uniqueness
- employee lookup and employee-resource compatibility
- active organization context

#### `CostItem`

Status:

- completed

Entity responsibilities:

- require `project_id`, `description`, and `planned_amount`
- validate non-negative planned/committed/actual/forecast amounts
- normalize `currency_code`, `vendor_reference`, and code
- coerce `cost_type` and `commitment_status`

Service responsibilities:

- project/task existence
- approval governance
- financial policy and posting workflow

#### `CalendarEvent`

Status:

- completed

Entity responsibilities:

- require project/date/title-like fields used by the PM calendar domain
- validate event date ranges and duration-like fields
- normalize labels and optional ownership/scope fields

Service responsibilities:

- project/resource existence
- collision policy
- reporting and scheduling orchestration

#### `RegisterEntry`

Status:

- completed

Entity responsibilities:

- require owning `project_id` and core title/description fields
- normalize owner/mitigation/notes fields
- coerce severity/status/type enums
- validate local scoring/probability/exposure ranges

Service responsibilities:

- project existence
- duplicate/manual-code policy
- workflow transitions and approval rules

#### `PortfolioIntakeItem`, `PortfolioScenario`, `PortfolioScoringTemplate`

Status:

- completed

Entity responsibilities:

- require organization ownership plus title/name fields
- normalize summaries/notes and ID collections
- deduplicate scenario project/intake IDs
- validate budget/capacity numeric ranges
- validate score/weight ranges and active-template shape

Service responsibilities:

- referenced project/intake/template existence
- scenario comparison policy
- selection and governance rules

#### `TaskComment`

Status:

- completed

Entity responsibilities:

- require `task_id` and comment body
- normalize body, mentions, attachments, and read-tracking lists
- deduplicate usernames and user IDs

Service responsibilities:

- task existence
- mention resolution
- notification fan-out
- permission and visibility rules

Notes:

- the repo-bound collaboration entity/service path is now migrated
- the older `TaskCollaborationStore` import/regression path still keeps its own store-level validation and is outside this primary write-model migration slice

### Maintenance entities

#### Asset and location cluster

Status:

- completed

Entities:

- `MaintenanceLocation`
- `MaintenanceSystem`
- `MaintenanceAsset`
- `MaintenanceAssetComponent`

Entity responsibilities:

- require owning IDs/codes/names
- normalize hierarchy references, descriptions, manufacturer/supplier references, serial/model/barcode fields, strategy text, and notes
- validate non-negative numeric fields and acquisition/service date order
- normalize lifecycle/category/type/status fields

Service responsibilities:

- uniqueness by code within scope
- site/system/parent existence
- cross-module party references
- hierarchy integrity rules

Notes:

- write-model validation now lives in the maintenance domain for `MaintenanceLocation`, `MaintenanceSystem`, `MaintenanceAsset`, and `MaintenanceAssetComponent`
- asset/component date windows and non-negative numeric checks moved out of the services into the validated DTO layer
- create/update services now keep tenant, scope, hierarchy, party, and uniqueness orchestration while using `replace(...)` for validated updates

#### Work request and work order cluster

Entities:

- `MaintenanceWorkRequest`
- `MaintenanceWorkOrder`
- `MaintenanceWorkOrderTask`
- `MaintenanceWorkOrderTaskStep`
- `MaintenanceWorkOrderMaterialRequirement`

Entity responsibilities:

- require core owning IDs plus title/instruction/description fields
- normalize codes, notes, request/work types, risk labels, hint fields, measurement fields, and material references
- validate estimated/planned/actual hours and quantities are non-negative
- validate local date order and status-compatible field shape

Service responsibilities:

- workflow/status transitions
- source/asset/site existence
- procurement and time-entry integration
- labor/material planning business rules

Notes:

- write-model validation now lives in the maintenance domain for `MaintenanceWorkRequest`, `MaintenanceWorkOrder`, `MaintenanceWorkOrderTask`, `MaintenanceWorkOrderTaskStep`, and `MaintenanceWorkOrderMaterialRequirement`
- request/order/task/step DTOs now normalize IDs, codes, type/status enums, timestamps, sequence numbers, notes, and local chronology rules with assignment-time validation
- material requirement DTO validation now owns stock/non-stock field shape, positive/non-negative quantity checks, and issued-vs-required consistency, while the service still derives stock description/UOM defaults and handles inventory availability/procurement integration
- work request and work order services now use `replace(...)`-based validated updates while keeping tenant-aware uniqueness checks, source conversion, preventive-plan orchestration, failure-code repository validation, and workflow transitions in the application layer

#### Reliability cluster

Entities:

- `MaintenanceSensor`
- `MaintenanceSensorReading`
- `MaintenanceIntegrationSource`
- `MaintenanceSensorSourceMapping`
- `MaintenanceSensorException`
- `MaintenanceFailureCode`
- `MaintenanceDowntimeEvent`

Entity responsibilities:

- require owning IDs/codes/names
- normalize units, thresholds, directions, quality/status flags, mapping keys, and notes
- validate threshold/date/duration/value ranges
- validate local start/end chronology for exceptions and downtime

Service responsibilities:

- uniqueness
- asset/component/site linkage
- external integration mapping policy
- exception escalation workflow

Notes:

- write-model validation now lives in the maintenance domain for `MaintenanceSensor`, `MaintenanceSensorReading`, `MaintenanceIntegrationSource`, `MaintenanceSensorSourceMapping`, `MaintenanceSensorException`, `MaintenanceFailureCode`, and `MaintenanceDowntimeEvent`
- reliability DTOs now normalize ownership IDs, codes, integration types, sensor units, reading values, quality/status enums, mapping keys, timestamps, and notes with assignment-time validation
- downtime and sensor-exception DTO validation now owns local chronology checks, and failure-code / sensor / source / mapping DTOs now own the scalar cleanup previously duplicated in reliability services
- `MaintenanceSensorReading` now validates required sensor/document ownership fields, reading value and unit shape, quality-state coercion, source metadata cleanup, and reading timestamp normalization directly in the repository-bound DTO
- the sensor-reading create path now constructs the validated reading DTO first and refreshes the parent sensor snapshot with `replace(...)`, while keeping tenant context, scope enforcement, inactive-sensor protection, configured-unit mismatch checks, and exception-escalation workflow in the service layer
- targeted verification completed with `36` passing maintenance tests across `src/tests/maintenance/test_maintenance_domain_validation.py`, `src/tests/maintenance/test_maintenance_sensor_foundation.py`, `src/tests/maintenance/test_maintenance_phase4_foundation.py`, `src/tests/maintenance/test_maintenance_persistence_materials_sensors.py`, and `src/tests/maintenance/test_repository_tenant_hardening_secondary.py`

#### Preventive cluster

Entities:

- `MaintenanceTaskTemplate`
- `MaintenanceTaskStepTemplate`
- `MaintenancePreventivePlan`
- `MaintenancePreventivePlanTask`
- `MaintenancePreventivePlanInstance`
- `MaintenanceBlackoutWindow`

Entity responsibilities:

- require plan/template ownership and names/codes
- normalize trigger mode fields, maintenance type, skills, notes, measurement fields, and override references
- validate generation horizon/lead counts
- validate frequency/sensor-trigger local numeric ranges
- validate blackout and instance date windows

Service responsibilities:

- trigger-configuration business rules
- related asset/system/component/sensor existence
- generation workflow and approval policy
- plan-instance lifecycle transitions
- completed in `src/core/modules/maintenance/domain/preventive/schedule.py` with shared pydantic-backed normalization for task templates, step templates, plans, plan tasks, plan instances, and blackout windows
- preventive CRUD services now construct validated DTOs first and use `replace(...)` updates while keeping tenant-aware uniqueness checks, scope enforcement, context/sensor linkage, and trigger-policy rules in the application layer
- preventive scheduler/generation audit writes now keep business timestamps on `due_at`/`generated_at`/`last_generated_at` while using runtime persistence timestamps for `updated_at`, which preserves historical `as_of` generation flows without leaking invalid chronology
- preventive package exports now include `MaintenanceBlackoutWindow`, and targeted verification completed with `32` passing maintenance tests covering preventive DTO validation, task-template foundations, plan/plan-task services, generation, scheduling, and persistence flows

### Inventory and procurement entities

#### Catalog and foundation cluster

Entities:

- `InventoryItemCategory`
- `StockItem`
- `Storeroom`
- `StorageLocation`
- `ReorderPolicy`
- `CycleCount`

Entity responsibilities:

- require owning org/site/storeroom/category/item IDs/codes/names as appropriate
- normalize descriptions, units, classifications, contact/location text, and notes
- validate reorder thresholds, min/max levels, count variances, and other non-negative numeric fields
- normalize status/type fields

Service responsibilities:

- uniqueness within organizational scope
- cross-reference existence
- stock-policy business rules
- count approval and reconciliation workflow
- completed in `src/core/modules/inventory_procurement/domain/_validation.py`, `src/core/modules/inventory_procurement/domain/catalog/item.py`, `src/core/modules/inventory_procurement/domain/inventory/stock.py`, and `src/core/modules/inventory_procurement/domain/inventory/foundation.py` with shared pydantic-backed normalization for inventory codes/names, status fields, UOMs, non-negative quantities/days, dates, enums, and local chronology/range checks
- `src/core/modules/inventory_procurement/application/common/support.py` now delegates shared scalar normalization to the domain helper so catalog, inventory, and downstream stock/procurement services read from a single normalization source
- catalog and inventory foundation application writes now construct validated DTOs first and use `replace(...)` updates in `category_commands.py`, `item_commands.py`, `inventory/service.py`, and `inventory/foundation_service.py`, while keeping uniqueness, tenant/site/storeroom/category/party existence, status-transition policy, parent-location hierarchy checks, and cycle-count reconciliation workflow in the service layer
- duplicate catalog-only CRUD validators were reduced to the surviving party-reference guard in `src/core/modules/inventory_procurement/application/catalog/item_validation.py`; reorder-range and UOM-factor duplication now lives only in the shared write models
- targeted verification completed with `12` passing DTO/service tests in `test_inventory_procurement_domain_validation.py` and `test_inventory_procurement_foundation.py`, plus `10` additional passing regression tests across `test_inv_procurement_tenant_inventory.py`, `test_inventory_procurement_desktop_api_workspace_catalog.py`, `test_inventory_code_generation.py`, and the non-snapshot path in `test_inventory_procurement_desktop_api_inventory.py`
- additional regression coverage in `test_inventory_procurement_desktop_api_inventory.py` remains blocked by an unrelated module-runtime baseline drift: the runtime currently reports `inventory_procurement` and `maintenance_management` as enabled, which also reproduces outside this slice in `src/tests/platform/test_enterprise_platform_catalog.py` and conflicts with older test expectations that those modules are disabled by default

#### Stock operations cluster

Entities:

- `StockBalance`
- `StockReservation`

Entity responsibilities:

- require owning item/location/storeroom references
- validate on-hand/available/reserved/issued numeric fields
- normalize reservation status, references, and notes
- validate non-negative quantities and local quantity coherence

Service responsibilities:

- reservation lifecycle rules
- stock availability checks
- cross-module fulfillment rules
- completed in `src/core/modules/inventory_procurement/domain/_validation.py`, `src/core/modules/inventory_procurement/domain/inventory/stock.py`, `src/core/modules/inventory_procurement/application/common/support.py`, `src/core/modules/inventory_procurement/application/inventory/stock_control_adjustments.py`, `src/core/modules/inventory_procurement/application/inventory/stock_control_movements.py`, `src/core/modules/inventory_procurement/application/inventory/stock_control_support.py`, and `src/core/modules/inventory_procurement/application/inventory/reservation_service.py`
- `StockBalance` now validates required stock-position references, UOM, non-negative quantity and cost fields, available-versus-on-hand coherence, and local receipt/issue timestamp ordering directly in the repository-bound DTO
- `StockReservation` now validates required stock/source references, reservation code and UOM normalization, non-negative quantity fields, status enum normalization, source-reference normalization, closed-state timestamp coherence, and status-compatible issued versus remaining quantity rules directly in the repository-bound DTO
- shared source-reference and positive-quantity normalization now lives in the domain helper and is re-exported through `application/common/support.py`, removing one more duplicated scalar-validation branch between application services and the write models
- stock adjustment, movement, and reservation services now rebuild validated balances and reservations with `replace(...)` instead of mutating dataclass instances in place, while keeping reservation transition policy, stock availability protection, existing-balance requirements, and cross-module/reference workflow checks in the service layer
- duplicate stock/reservation CRUD validation now lives only in the DTOs for local scalar and coherence rules; service-layer checks remain only for tenant-scope, lifecycle, and fulfillment policy decisions
- targeted verification completed with `5` passing DTO tests in `src/tests/inventory_procurement/test_inventory_procurement_domain_validation.py` and `18` additional passing regression tests across `src/tests/inventory_procurement/test_inventory_procurement_movements.py`, `src/tests/inventory_procurement/test_inventory_procurement_reservations.py`, `src/tests/inventory_procurement/test_inventory_procurement_ledger.py`, `src/tests/inventory_procurement/test_inventory_procurement_desktop_api_reservations_procurement.py`, and `src/tests/inventory_procurement/test_inventory_maintenance_material_contracts.py`

#### Procurement cluster

Entities:

- `PurchaseRequisition`
- `PurchaseRequisitionLine`
- `PurchaseOrder`
- `PurchaseOrderLine`

Entity responsibilities:

- require owning IDs, supplier/requestor references, and descriptive fields
- normalize codes, currencies, units, references, receipt tracking text, and notes
- validate requested/ordered/received quantities, receipt unit costs, and processed-quantity coherence
- validate local date ranges and status-compatible fields

Service responsibilities:

- approval workflow
- supplier/site/item existence
- duplicate/open-order policy
- receipt/procurement lifecycle rules
- completed in `src/core/modules/inventory_procurement/domain/_validation.py`, `src/core/modules/inventory_procurement/domain/procurement/purchasing.py`, `src/core/modules/inventory_procurement/application/procurement/procurement_support.py`, `src/core/modules/inventory_procurement/application/procurement/procurement_lifecycle.py`, `src/core/modules/inventory_procurement/application/procurement/procurement_approval.py`, `src/core/modules/inventory_procurement/application/procurement/purchasing_support.py`, `src/core/modules/inventory_procurement/application/procurement/purchasing_lifecycle.py`, and `src/core/modules/inventory_procurement/application/procurement/purchasing_receiving.py`
- `PurchaseRequisition`, `PurchaseRequisitionLine`, `PurchaseOrder`, `PurchaseOrderLine`, `ReceiptHeader`, and `ReceiptLine` now validate required IDs and document numbers, procurement priority and currency normalization, UOM and quantity fields, optional supplier/reference identifiers, receipt tracking text, local source-reference pairing, and local chronology and status-compatible quantity coherence directly in the repository-bound DTOs
- shared procurement priority and currency normalization now lives in the inventory-procurement domain helper and is re-exported through the existing procurement support modules so the application layer and the repository-bound write models use the same scalar normalization rules
- requisition approval, purchase-order approval, purchase-order sending/closing, receipt posting, requisition-status refresh, and on-order balance adjustment paths now rebuild validated requisitions, purchase orders, lines, receipt-adjacent aggregates, and balances with `replace(...)` instead of mutating validated dataclass instances field by field
- service-layer rules remain focused on tenant and organization scope, active supplier/site/storeroom existence, item purchasing eligibility, approval workflow, remaining requisition demand checks, receipt tracking rules, and on-order or stock movement side effects
- additional runtime hardening in the same pass fixed the platform-level `SiteService.find_site_by_code` missing `normalize_code` import that was breaking inventory import previews and document imports, and the purchase-order receiving path now keeps aggregate `updated_at` monotonic while still preserving historical imported receipt dates
- targeted receipt/procurement verification completed with `24` passing DTO and workflow regression tests across `src/tests/inventory_procurement/test_inventory_procurement_domain_validation.py`, `src/tests/inventory_procurement/test_inventory_procurement_purchasing_submit.py`, `src/tests/inventory_procurement/test_inventory_procurement_purchasing_lifecycle.py`, `src/tests/inventory_procurement/test_inventory_import_export_reporting.py`, `src/tests/inventory_procurement/test_inventory_procurement_desktop_api_reservations_procurement.py`, and `src/tests/inventory_procurement/test_inventory_procurement_desktop_api_pricing.py`

## Recommended Enterprise Boundary

This document treats the following as the standard enterprise SaaS design for this repo:

- transport layers collect and pass input
- the shared mutable write model between services and repositories validates and normalizes CRUD fields
- services enforce tenant, organization, site, department, calendar, RBAC, approval, uniqueness, and other repository-aware rules
- repositories persist already-normalized write models
- the database still enforces schema and integrity constraints

Important clarification:

- tenancy stays in services
- RBAC stays in services
- repository-aware validation stays in services
- the duplication to remove is the extra CRUD field-validation logic repeated outside the shared write model
- where the mutable entity already is the shared write model, we should migrate validation into that entity instead of adding another DTO beside it

### Put in deeper CRUD DTOs / entities

Use Pydantic in the repo-bound mutable models for:

- required/optional field enforcement
- string trimming and normalization
- integer/float coercion
- enum coercion
- cross-field checks like date ranges
- assignment-time validation during service updates
- create/update validation shared by desktop, HTTP, imports, and tests

### Keep in services

Keep service validation for:

- tenant isolation
- RBAC and entitlement enforcement
- repository existence checks
- uniqueness checks that require repository reads
- cross-aggregate rules
- circular dependency checks
- schedule constraints against project ranges
- overallocation policy decisions
- concurrency/version checks
- approval/workflow invariants

This is an important boundary. Pydantic should replace field-level CRUD validation in deeper DTO/entity models, not business policy.

## Migration Strategy

### Phase 1: Shared foundation

- add `pydantic` to repo dependencies
- add a shared validated-dataclass helper for mutable repo-bound DTOs
- provide shared normalization helpers for common string/id coercion
- keep domain `ValidationError` as the surfaced exception type from validators

### Phase 2: First safe slice

Start with PM repo-bound DTOs because they clearly show the intended pattern:

- `Project`
- `ProjectResource`
- `Task`
- `TaskAssignment`
- `TaskDependency`

Then move to platform master data:

- `Organization`
- `Site`
- `Department`
- `Employee`

Then remove overlapping scalar validation from services once the DTO/entity owns it.

### Phase 3: Expand by vertical slice

After PM core entities:

1. PM resources, scheduling, register, portfolio, financials
2. platform master-data and calendar entities
3. maintenance CRUD entities
4. inventory/procurement CRUD entities

## Rollout Order

### Wave 1: PM core

- `Project`
- `ProjectResource`
- `Task`
- `TaskAssignment`
- `TaskDependency`

Why first:

- strong test coverage already exists
- direct CRUD duplication is easy to see
- these entities sit at the center of PM scheduling, timesheets, and desktop flows

### Wave 2: Platform master data

- `Organization`
- `Site`
- `Department`
- `Employee`
- `Party`
- `TimeEntry`
- `TimesheetPeriod`

Why second:

- these are reused by multiple modules
- they are high-value shared records
- they reduce repeated validation across PM, maintenance, and inventory dialogs

### Wave 3: Platform governance and calendar

- access / auth write models
- approval / tenant / runtime / platform event write models
- calendar and shift write models
- document write models

### Wave 4: Maintenance

- assets
- work requests / work orders
- preventive
- reliability

### Wave 5: Inventory / Procurement

- catalog
- storerooms / locations / policies
- reservations / balances / counts
- requisitions / purchase orders

## Implementation Options

### Option A: Direct Pydantic dataclass on each entity

Pattern:

- use `from pydantic.dataclasses import dataclass`
- configure `ConfigDict(validate_assignment=True)` on each migrated entity
- put validators directly on the entity class

Pros:

- simplest to read
- no wrapper indirection
- makes the migration obvious in each file

Cons:

- repeated config boilerplate on every entity
- shared normalization patterns are repeated unless helpers are still used

### Option B: Thin shared wrapper around Pydantic dataclass

Pattern:

- keep a tiny helper like `validated_dataclass`
- keep small shared normalizers for text / id coercion
- still put real validation logic on the entity class

Pros:

- one place for shared config
- less repeated decorator noise
- easy to change defaults later

Cons:

- one extra layer to mentally resolve
- may feel less explicit to readers who prefer raw decorators

### Option C: Convert mutable entities to `BaseModel`

Pros:

- familiar Pydantic surface
- rich validation features

Cons:

- larger rewrite
- worse fit for current mutable dataclass usage
- more friction with `replace(...)`, mapper expectations, and current service mutation style

Recommendation:

- not recommended for this repo as the main migration path

### Option D: Add service-layer Pydantic DTOs but keep entities passive

Pros:

- lower immediate churn inside domain files
- familiar if thinking in request DTOs

Cons:

- duplicates the same rules again when entities are still mutable underneath
- weaker reuse for later in-place updates
- keeps the root problem alive

Recommendation:

- not recommended as the final architecture for CRUD validation in this repo

### Option E: Keep the existing entity as the write model and remove duplicate DTO-style validation around it

Pros:

- lowest conceptual overhead
- no unnecessary extra DTO type beside the existing mutable write model
- best fit for the repo's current service/repository contracts
- keeps tenancy and RBAC exactly where they belong: in services

Cons:

- requires disciplined migration so entity validation and service business rules do not get mixed together

## Best Implementation Choice

Best technical shape for this codebase:

- Pydantic dataclass on the repo-bound mutable entity itself
- domain `ValidationError` raised directly from validators
- service keeps tenancy, RBAC, repository-aware, and business-policy validation
- final-state replacement for multi-field updates where assignment order matters

This is the same enterprise pattern described above:

- the shared mutable write model sits between service and repository
- it is the reusable CRUD validation boundary
- it is closer to the database than UI or transport DTOs, without collapsing validation into ORM classes
- if that shared write model already exists as the entity, we should use it directly rather than inventing an extra DTO beside it

Best syntax choice:

- if the team wants maximum simplicity, use direct Pydantic dataclass decorators on each entity
- if the team wants shared config with less repetition, keep the thin wrapper

Both are the same architectural approach. The difference is syntax, not design.

Best rollout strategy:

- migrate by vertical slice of related services and entities
- do not do a big-bang rewrite across all modules at once
- do not migrate read/report/snapshot models unless a concrete need appears

## First-Slice Design Notes

### DTO/entity rules

For the first deeper DTO slice, Pydantic models should:

- validate their own field values on create
- validate assignments during service updates
- normalize one internal persisted shape
- raise existing domain `ValidationError` instead of raw Pydantic exceptions

### Compatibility constraints

The first slice should preserve:

- existing transport models where they already exist
- existing controller behavior that surfaces `str(exc)` into inline/banner messages
- existing business-rule enforcement inside services

## Risks

### Risk: removing too much service validation

If service validation is removed indiscriminately, real business rules could move into the wrong layer and weaken tenant/RBAC safety.

Mitigation:

- remove only duplicated scalar/field validation in each slice
- keep business-rule validation in services

### Risk: assignment-order regressions on cross-field updates

If services update one validated field at a time, transient invalid states can fail even when the final pair is valid.

Mitigation:

- use DTO/entity replacement or equivalent final-state validation for multi-field updates

### Risk: raw Pydantic errors leaking into QML

If validators raise plain `ValueError`, raw Pydantic wrappers may leak upward.

Mitigation:

- raise existing domain `ValidationError` directly inside validators

## Progress Tracker

- [x] Repo audit of command-model and validation duplication
- [x] Identify deeper CRUD DTO boundary
- [x] Map mutable CRUD entities by module
- [x] Add shared validated-dataclass foundation
- [x] Add `pydantic` to repo dependency declarations
- [x] Migrate PM project/project-resource DTOs
- [x] Migrate PM task/task-assignment/task-dependency DTOs
- [x] Remove duplicated PM scalar validation from services where DTOs now own it
- [x] Run focused verification for PM CRUD flows
- [x] Expand to next module slice
- [x] Migrate PM portfolio intake/scenario/template DTOs
- [x] Migrate PM task-comment DTOs
- [x] Migrate platform organization/site DTOs
- [x] Migrate platform department/employee DTOs
- [x] Migrate platform party DTO
- [x] Migrate platform time-entry/timesheet-period DTOs
- [x] Migrate platform access membership/grant DTOs
- [x] Migrate platform user-account/auth-session DTOs
- [x] Migrate platform approval/tenant/event/runtime DTOs
- [x] Migrate platform calendar/shift DTOs
- [x] Migrate platform document DTOs

## Current Implementation Decision

The migration target is the deeper mutable DTO/entity layer, not the desktop boundary.

The immediate proof slice is PM project/project-resource because:

- it is clearly repo-bound and mutable
- it currently duplicates scalar validation in services
- it lets us validate both create and update paths with assignment-aware DTO rules
