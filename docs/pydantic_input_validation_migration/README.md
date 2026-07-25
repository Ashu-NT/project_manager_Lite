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

- pending

Entity responsibilities:

- require `organization_id`, `party_code`, and `party_name`
- normalize `party_type`
- normalize contact/address/website/tax/external-reference fields
- normalize `is_active`, timestamps, and notes

Service responsibilities:

- organization scoping
- uniqueness by party code
- integration-specific referential checks

### Platform time, access, auth, and governance entities

#### `TimeEntry`

Status:

- pending

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

#### `TimesheetPeriod`

Status:

- pending

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

#### `ProjectMembership` and `ScopedAccessGrant`

Status:

- pending

Entity responsibilities:

- require scope/project and user identifiers
- normalize `scope_type` and `scope_role`
- deduplicate and normalize permission codes

Service responsibilities:

- scope existence
- allowed role-to-permission mapping
- user existence
- authorization policy matrix enforcement

#### `UserAccount`

Status:

- pending

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

#### `AuthSession`

Status:

- pending

Entity responsibilities:

- require `user_id`, `session_revision`, `auth_method`, and `expires_at`
- normalize `device_label`, tenant/org context memory, and UTC datetimes
- keep revision positive

Service responsibilities:

- session issuance and rotation
- revocation
- revalidation
- user/session matching and expiry policy

#### `ApprovalRequest`, `Tenant`, `PlatformEvent`, `RuntimeExecution`

Status:

- pending

Entity responsibilities:

- validate required IDs, statuses, timestamps, labels, and free-text fields
- normalize codes, names, notes, metadata references, and version-like counters

Service responsibilities:

- workflow transitions
- bootstrap and provisioning rules
- retention / replay / execution lifecycle policy
- actor permission checks

### Platform calendar and document entities

#### `PlatformCalendar`

Status:

- pending

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

#### `CalendarException`

Status:

- pending

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

#### `CalendarRecurringEvent`

Status:

- pending

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

#### `ShiftPattern`

Status:

- pending

Entity responsibilities:

- require code/name/type-like fields
- normalize labels and flags
- validate day offsets, durations, and assignmentable state

Service responsibilities:

- uniqueness
- organization scoping
- conflict policy
- references to pattern days and assignments

#### `DocumentStructure` and `Document`

Status:

- pending

Entity responsibilities:

- require owning IDs and names/codes/titles as appropriate
- normalize storage-related text, labels, paths, URLs, notes, and metadata fields
- validate file/structure state and version counters

Service responsibilities:

- linked-entity existence
- storage backend policy
- document-type workflow
- access control and tenant scope

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

#### Reliability cluster

Entities:

- `MaintenanceSensor`
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

#### Procurement cluster

Entities:

- `PurchaseRequisition`
- `PurchaseRequisitionLine`
- `PurchaseOrder`
- `PurchaseOrderLine`

Entity responsibilities:

- require owning IDs, supplier/requestor references, and descriptive fields
- normalize codes, currencies, units, references, and notes
- validate requested/ordered/received quantities and price amounts
- validate local date ranges and status-compatible fields

Service responsibilities:

- approval workflow
- supplier/site/item existence
- duplicate/open-order policy
- receipt/procurement lifecycle rules

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
- [ ] Add `pydantic` to repo dependency declarations
- [x] Migrate PM project/project-resource DTOs
- [x] Migrate PM task/task-assignment/task-dependency DTOs
- [x] Remove duplicated PM scalar validation from services where DTOs now own it
- [x] Run focused verification for PM CRUD flows
- [x] Expand to next module slice
- [x] Migrate PM portfolio intake/scenario/template DTOs
- [x] Migrate PM task-comment DTOs
- [x] Migrate platform organization/site DTOs
- [x] Migrate platform department/employee DTOs

## Current Implementation Decision

The migration target is the deeper mutable DTO/entity layer, not the desktop boundary.

The immediate proof slice is PM project/project-resource because:

- it is clearly repo-bound and mutable
- it currently duplicates scalar validation in services
- it lets us validate both create and update paths with assignment-aware DTO rules
