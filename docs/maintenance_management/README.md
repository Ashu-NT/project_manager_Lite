# Maintenance Management Module Blueprint

Status: active blueprint and phased implementation tracker, benchmark refresh completed on 2026-03-28  
Scope: enterprise CMMS design, data model, workflow, integration, import, and implementation backlog  
Implementation state: maintenance now has persisted foundations through `location`, `system`, `asset`, `asset_component`, `work_request`, `work_order`, `work_order_task`, `work_order_task_step`, `work_order_material_requirement`, `sensor`, `sensor_reading`, `integration_source`, `sensor_source_mapping`, `sensor_exception`, `failure_code`, `downtime_event`, `maintenance_task_template`, `maintenance_task_step_template`, `preventive_plan`, and `preventive_plan_task`, plus a live preventive due-generation engine, reliability analytics/report-pack services, and first shell/UI workspaces for `Maintenance Dashboard`, `Assets`, `Sensors`, `Requests`, `Work Orders`, `Documents`, `Planner`, and `Reliability`; broader technician execution flows are still pending

## Purpose

The `Maintenance Management` module should be a professional enterprise CMMS for plants, facilities, mobile equipment, and industrial operations.

It should support:

- asset hierarchy and maintainable equipment master data
- system and location structure
- corrective, preventive, inspection, calibration, and condition-based work
- preventive tasks triggered by calendar rules or sensor rules
- sensors, counters, and running-hours triggers
- reusable maintenance tasks and task steps
- supplier and manufacturer traceability
- document control across assets, sensors, tasks, and work orders
- planning, scheduling, execution, verification, and closure
- company-system integration for telemetry, runtime, and operational counters
- spreadsheet-based mass import for initial rollout

This document combines:

- earlier CMMS ideas already discussed
- the user requirement for a clean real-world maintenance flow
- the explicit table ideas: `location`, `system`, `assets`, `tasks`, `task_steps`, `sensor`, `document`, `supplier/manufacturer info`, and `document structure`

## Product Vision

This module should not feel like a generic asset list.

It should behave like a real maintenance operation:

- operators submit issues
- planners triage and schedule work
- preventive plans generate due work
- technicians execute guided steps
- supervisors verify and close
- reliability teams analyze repeated failures

The UI should be queue-first.

That means:

- notifications are awareness only
- work happens in queues, planners, boards, and detail pages
- users should never need to hunt across random tabs to find what requires action

## Design Principles

- Use enterprise master data, not free-text blobs.
- Use stable business keys for import and cross-references.
- Reuse documents across many records with linking tables.
- Keep sensors and integrations first-class, not as notes fields.
- Separate templates from execution records.
- Keep reusable task templates trigger-neutral, and place trigger logic on preventive plans or plan-task assignments.
- Track both current state and history.
- Support auditability for every important status change.
- Refresh UI in place with `reload/update`, not rebuild whole screens.
- Keep expensive planning and analytics async.

## Blueprint Availability

This README is the authoritative maintenance blueprint for the repo.

No maintenance code should be started until the ownership boundary, workflows,
master data, and rollout phases in this document are accepted.

That means this file is not only a wishlist. It is the intended contract for:

- module ownership
- service boundaries
- table catalog
- queue and execution UX direction
- inventory, document, and party integration
- import, reporting, and analytics scope
- desktop-first delivery with future web parity

## 2026 Market Benchmark Refresh

As of 2026-03-28, this blueprint has been refreshed against official product or
documentation sources from:

- IBM Maximo Manage
- SAP Asset Management / SAP Service and Asset Manager
- Oracle Maintenance
- Fiix
- UpKeep
- Limble

The benchmark matters because the maintenance module should be stronger than a
lightweight work-order app, but also more usable and modular than a heavy
legacy EAM rollout.

### Repeating Patterns In Leading CMMS/EAM Products

Across those products, the same enterprise patterns show up repeatedly:

- a reusable maintenance template layer such as job plans, task lists, or work definitions
- execution copies that are detached from the source template once work is issued
- asset, location, and system hierarchy as a first-class navigation model
- preventive maintenance based on time, usage, condition, or threshold logic
- parts, reservations, and purchasing linked directly to work execution
- measurement, meter, counter, or sensor readings that can trigger maintenance
- documents, history, and compliance evidence attached to work and assets
- spreadsheet or bulk-load capability for enterprise rollout
- planner/scheduler views instead of only flat work-order lists
- mobile/web-friendly execution patterns for technicians in the field

### What The Current Repo Already Has

Compared with a greenfield CMMS build, this codebase already gives Maintenance a
stronger enterprise starting point:

- shared organization, site, department, party, document, auth, access, approval, audit, and notification services already exist under `platform`
- the shared document library already supports preview state, metadata, and cross-module links
- the shared auth/access layer already supports scoped access, session persistence, MFA groundwork, and SoD evolution seams
- the `inventory_procurement` module already exists for item categories, item master, storerooms, balances, reservations, requisitions, purchase orders, receiving, and inventory import/export/reporting
- the inventory module already carries maintenance-oriented concepts such as spare/equipment categories, lot/serial/shelf-life rules, and maintenance-facing source references
- the codebase already has application and transport seams for a future desktop + web product instead of forcing Maintenance to be desktop-only forever

## Pre-Implementation Hardening Needed In Existing Platform And Modules

Before the broader `maintenance_management` rollout continues, the current repo
should finish a small but important hardening block so Maintenance can keep
plugging into the shared platform cleanly instead of adding another round of
compatibility debt.

### Ready Enough Today

These seams are already strong enough to be consumed from the maintenance
module with normal module-owned adapters:

- shared auth, audit, approvals, notifications, organization, site, department, and party foundations
- shared `DocumentIntegrationService` for module-level document browsing and linking without forcing platform-admin-only document workflows
- inventory-owned item categories, storerooms, balances, reservations, requisitions, purchase orders, receipts, and maintenance-facing source-reference types
- shared import/export/report runtime foundation with persisted execution tracking

### Hardening Checklist Before Maintenance Buildout

#### 1. Broader scoped access for maintenance objects

Current state:

- platform access now supports `project`, `site`, and `storeroom`
- `project` and `storeroom` scope policies can now register from their owning module service bundles instead of being hard-coded in the platform bundle
- the access roadmap still calls out future `asset` and `maintenance-area` scopes

Why this matters:

- maintenance needs tighter access boundaries than project-only or org-wide reads
- planners, supervisors, contractors, and technicians often need access limited by site, area, system, asset family, or assigned work

Required hardening:

- add module-owned scope policies for `asset`, `location`/`maintenance_area`, and later `system`
- make those scopes available through the shared access admin surface and authorization engine

#### 2. Module-neutral governance queue and approval UX

Current state:

- `ApprovalService` is platform-owned and generic
- a shared `Approvals` control workspace now exposes module-neutral approval review
- the Project Management `Governance` screen now keeps PM-only concerns such as PM governance mode and timesheet review

Why this matters:

- maintenance will need approval queues for governed work-order release, shutdown work, permit-sensitive jobs, vendor work, plan changes, and other operational decisions
- those flows should not inherit a PM-shaped governance screen

Required hardening:

- extract a module-neutral governance queue surface or platform control workspace
- keep module request-type meaning in the owning module, but stop making approval review feel PM-specific
- keep PM-only controls such as PM governance mode and timesheet review separate from the shared approval queue

#### 3. Shared time and labor booking generalization

Current state:

- shared time now persists a neutral `work_allocation_id` alongside PM compatibility `assignment_id`
- shared time entries now carry owner and scope snapshots such as `owner_label`, `scope_type`, and `scope_id`
- the platform time service now exposes neutral `work allocation` read/write aliases while keeping PM assignment wrappers intact
- shared time permissions now include `time.read` and `time.manage`, while PM compatibility still accepts `task.read` and `task.manage`

Why this matters:

- maintenance needs labor booking against work orders, operations, task steps, crews, and possibly contractor work packages
- maintenance should consume the shared time engine, not fork it

Required hardening:

- done: widen the shared time boundary from project-task wording toward neutral work-owner semantics
- done: support future maintenance work-order / operation references without pretending they are PM task assignments in storage
- done: make labor-booking permissions and review flows stop depending only on PM task naming

#### 4. Shared document taxonomy and lifecycle hardening

Current state:

- shared document metadata and linking are live
- shared `document_structures` are live in the platform document library
- documents now carry a dedicated business-facing version / revision label without colliding with optimistic-lock `version`
- future web-facing upload/file-handling plumbing is still a runtime follow-up item

Why this matters:

- maintenance will be document-heavy from day one: manuals, drawings, SOPs, permits, photos, certificates, calibration evidence, and vendor reports
- QHSE and HR will also consume the same shared document spine later

Required hardening:

- done: add the shared `document_structure` domain before the maintenance document library grows
- done: define business-facing document version/revision handling that does not conflict with optimistic locking
- keep growing the shared upload/storage abstraction so desktop and future web can use one document model

#### 5. Explicit inventory-to-maintenance material contracts

Current state:

- inventory now exposes an explicit maintenance-material contract for availability, reservation, issue, return, and procurement escalation through the inventory service graph
- stable maintenance-facing statuses and the `inventory_maintenance_materials_changed` domain event now exist so maintenance planners can refresh against one contract seam instead of reading inventory internals directly

Why this matters:

- maintenance needs clear contracts for reserve, issue, return, shortage, direct-charge procurement, and material-availability status
- those flows should be explicit module integration points, not free-text references sprinkled through services

Required hardening:

- done: define the maintenance-side contract for work-order material demand, reservation, issue, return, and purchasing escalation
- done: emit stable domain events and shared statuses that planners can use without reading inventory internals directly

#### 6. Maintenance-specific import/export/report runtime contracts

Current state:

- the platform runtime foundation exists and inventory is already using it
- persisted runtime execution tracking now records retry lineage, cancellation requests, and richer artifact metadata such as output file name, media type, and output metadata across shared import/export/report runs
- a dormant maintenance runtime contract scaffold now exists under `core/modules/maintenance_management/importing`, `exporting`, and `reporting`
- the maintenance workbook contract now separates module-owned sheets such as `Locations`, `Assets`, `PreventivePlans`, and `DocumentLinks` from shared reference sheets owned by `platform` and `inventory_procurement`
- a pre-implementation contract-catalog service can now generate a rollout workbook template, contract matrix export, and neutral report catalog directly from that contract scaffold
- live maintenance workbook handlers, export builders, and report renderers are still pending

Why this matters:

- maintenance rollout will need large workbook imports for locations, systems, assets, components, meters, plans, and documents
- enterprise maintenance users will also expect exportable backlog, compliance, downtime, and execution reports

Required hardening:

- done: define the canonical maintenance workbook, export-pack, and report-pack contract keys before module services exist
- keep growing async runtime control from the new retry/cancellation/artifact groundwork toward real queue-worker controls, retries, and cancellation handling for large rollout jobs
- wire those dormant contract definitions to real maintenance handlers when the first maintenance service slice starts

#### 7. Shared org-to-maintenance location reference path

Current state:

- ADR-002 already freezes ownership so `maintenance_management` owns `location` and `system`
- module-owned `location` and `system` core domain, repository contracts, SQLAlchemy repositories, migration coverage, and service-graph wiring now exist under `core/modules/maintenance_management`, `infra/modules/maintenance_management`, and the platform service-registration layer
- shared `Department` records can now persist a neutral `default_location_id` reference to maintenance-owned locations through the platform org layer without pushing location ownership back into platform

Why this matters:

- maintenance work assignment, crews, permits, and workforce planning will eventually want stable location references from shared organization/employee context

Required hardening:

- done: the platform org layer now uses a neutral location-reference resolver port, and the maintenance bundle registers the live maintenance-location adapter into `DepartmentService`

### Recommended Pre-Maintenance Hardening Order

1. Broader maintenance scopes in auth/access. Done.
2. Module-neutral governance queue and approval UX. Done.
3. Shared time boundary generalization for labor booking. Done.
4. Shared document taxonomy and lifecycle hardening. Done.
5. Explicit inventory-to-maintenance material contracts. Done.
6. Maintenance-specific import/export/report contracts and async runtime controls. In progress.
7. Shared org-to-maintenance location reference path on top of the new persisted location/system foundation. Done.

### What Does Not Need To Block The First Maintenance Slice

These items are important, but they do not have to be finished before phase-1
maintenance master data and work-order implementation starts:

- hosted web auth middleware rollout
- broader ABAC-style contextual authorization beyond the current engine seam
- fully mature async orchestration for every runtime use case
- full QHSE and HR document workflows

### Superior Product Target

To be stronger than typical mid-market CMMS products while staying cleaner than
heavy EAM suites, this module should deliberately aim for the following:

- enterprise asset hierarchy like an EAM, but with a simpler queue-first execution UX
- true cross-module materials planning by consuming the live inventory/procurement module instead of maintaining a duplicate parts ledger
- a shared document library that can serve maintenance, QHSE, HR, and project workflows from one controlled source
- maintenance templates with revision safety, copied execution records, and task-step evidence capture
- hybrid preventive logic that handles calendar, usage, condition, and stale-sensor exception cases explicitly
- planner-grade scheduling views for backlog, shutdowns, crew loading, and material readiness
- stronger scope-aware access for site, storeroom, asset, and maintenance-area boundaries
- import/export/reporting that is ready for large rollout and future web/API automation
- desktop execution that still maps cleanly to future web/mobile field workflows
- reliability and compliance features that are native design goals, not later add-ons

## Fit With The Current Repo Architecture

This repo already separates shared enterprise concerns under `platform/` and business workflows under `modules/`.

That means the maintenance design should follow the same pattern:

- shared master data and enterprise engines belong under `core/platform`, `infra/platform`, and `ui/platform` when they are truly cross-module
- maintenance-specific operational workflows belong under `core/modules/maintenance_management`, `infra/modules/maintenance_management`, and `ui/modules/maintenance_management`

Based on the current codebase, the shared platform spine already exists for:

- auth and RBAC
- access
- audit
- approvals
- organizations and employees
- module runtime and licensing
- shared time
- documents and notifications

The repo now includes a standalone `Inventory & Procurement` module with item master,
storerooms, stock balances and movements, reservations, requisitions, purchase orders,
receiving, and module-owned import/export/reporting.

After comparing your architecture direction with how established CMMS/EAM products typically handle this area, the better fit is:

- keep `platform` for cross-cutting technical and shared-enterprise concerns
- introduce a separate business module for `Inventory & Procurement`
- let `Maintenance Management` integrate to that module for stock, reservations, issue/return, and purchase demand

Recommended ownership split:

- `platform` owns cross-cutting concerns such as party master when it is shared across modules
- `inventory_procurement` owns item master, storerooms, stock balances, stock movements, reservations, requisitions, purchase orders, and receiving
- `maintenance_management` owns work-order material planning, spare recommendations, and the maintenance-side demand for parts and services

This matches the module-oriented direction of the repo better than treating inventory and procurement as low-level platform utilities.

### Cross-Module Boundary Rules

The maintenance design should follow a stricter ownership model so implementation stays scalable:

- `maintenance_management` owns maintenance truth: requests, work orders, PM plans, execution records, downtime, and reliability context
- `inventory_procurement` owns stock truth: items, storerooms, balances, movements, reservations, requisitions, purchase orders, and receiving
- `platform` owns enterprise shared services and reference masters: auth, organization and site context, party master, document plumbing, approvals, audit, notifications, and shared time
- cross-module integrations should use stable references, business keys, and domain events rather than copied master data
- documents are shared infrastructure, but maintenance owns the operational meaning of those documents and how they are linked into maintenance workflows
- party records are shared identities, but maintenance owns vendor, supplier, and manufacturer usage across assets, components, plans, and work
- notifications remain awareness-only; operational action stays in module queues, planners, boards, and detail screens
- implementation should avoid embedding inventory, HR, or platform workflow logic inside maintenance services and should keep module-owned read/write boundaries explicit even when UI flows link across modules

## Benchmark Patterns From Established CMMS

When compared with established CMMS and EAM products, the most important
patterns to preserve are:

- an admin-controlled job plan, checklist, or task library
- preventive logic that generates execution work instead of editing templates directly
- work-order tasks that technicians complete in dedicated execution screens
- assignee-driven task ownership where needed
- materials, tools, services, and purchasing tied to planned work
- inventory, spare-parts, and procurement processes linked to work orders
- revision-safe templates so old history is not changed when templates evolve

This blueprint should follow those patterns.

Observed enterprise pattern across the benchmarked products:

- IBM Maximo uses job plans, work plans, meters, scheduling views, and separate inventory/storeroom processes while still linking materials, services, tools, and safety context to the work order
- SAP Asset Management separates maintenance from materials while supporting maintenance task lists, measuring points, counters, and threshold-driven notification generation
- Oracle Maintenance uses work definitions, work-order operations, components, resources, exceptions, document references, history, and multi-asset work-order patterns
- Fiix emphasizes hierarchy, spreadsheet bulk import, and work-order parts usage against location-based stock
- UpKeep and Limble reinforce the importance of modern PM generation, planner-friendly usability, mobile execution, and tightly linked parts / PO visibility

Implication for this product:

- stock and purchasing should not be hidden as a small sub-feature inside Maintenance only
- they should be modeled as a standalone business module that Maintenance integrates with

### Benchmark Source Notes

Reference sources used for this refresh:

- IBM Maximo Manage overview, job plans, work plans, meters, and planning/scheduling:
  - https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=overview-work-order-management-plans
  - https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=module-meters
  - https://www.ibm.com/docs/en/masv-and-l/maximo-manage/cd?topic=managing-planning-scheduling-work
- SAP Asset Management measuring points, thresholds, counters, and maintenance materials planning:
  - https://help.sap.com/doc/b183ce53118d4308e10000000a174cb4/700_SFIN3E%20006/en-US/de29bf53d25ab64ce10000000a174cb4.html
  - https://help.sap.com/docs/SAP_S4HANA_ON-PREMISE/efc7922405fd4d56b7571930c5eaa798/3dc9b65334e6b54ce10000000a174cb4.html
- Oracle Maintenance work orders, work definitions, operations, materials, resources, exceptions, and history:
  - https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/24b/faumm/overview-of-maintenance-work-orders.html
  - https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/25d/faumm/overview-of-maintenance-work-definitions.html
  - https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/26a/faumm/overview-of-maintenance-work-execution.html
  - https://docs.oracle.com/en/cloud/saas/supply-chain-and-manufacturing/24c/inv24c/24C-inventory-wn-f33528.htm
- Fiix hierarchy, bulk import, and parts-on-work-order patterns:
  - https://helpdesk.fiixsoftware.com/hc/en-us/articles/211107603-Add-equipment-assets
  - https://helpdesk.fiixsoftware.com/hc/en-us/articles/212767823-Bulk-import-assets
  - https://helpdesk.fiixsoftware.com/hc/en-us/articles/15389271862932-Add-parts-to-a-work-order
- UpKeep PM, work-order, and parts visibility patterns:
  - https://help.onupkeep.com/en/articles/398039-what-is-a-cmms
  - https://help.onupkeep.com/en/articles/4753592-how-to-stop-a-preventive-maintenance-trigger
  - https://help.onupkeep.com/en/articles/9621157-preventive-maintenance-section-overview
  - https://help.onupkeep.com/en/articles/9746146-how-to-track-incoming-part-quantities-on-purchase-orders
  - https://help.onupkeep.com/en/articles/6699722-location-based-permissions-for-users-in-upkeep
  - https://help.onupkeep.com/en/articles/12325916-using-the-provider-portal-in-upkeep
- Limble CMMS work, PM, inventory, and desktop/mobile positioning:
  - https://limble.com/learn/cmms
  - https://limblecmms.com/cmms/maintenance-scheduling-software/

## Real CMMS Operating Model

### Main Roles

Recommended personas:

- `requester`: raises maintenance requests
- `planner`: triages, plans, and schedules work
- `supervisor`: approves, dispatches, verifies, closes
- `technician`: executes work orders and records results
- `reliability_engineer`: analyzes failures and recurring patterns
- `storekeeper`: manages spare parts and reservations
- `maintenance_manager`: controls backlog, compliance, and KPIs

### Clean Real-World Flow

The normal enterprise CMMS flow should be:

1. Master data is configured.
2. An asset issue or preventive trigger creates a pending demand.
3. Demand is reviewed and prioritized.
4. A work order is created or approved.
5. Planning decides labor, steps, tools, parts, shutdown, and target dates.
6. Scheduling assigns people and time windows.
7. Technicians execute with guided task steps.
8. Measurements, notes, photos, parts, and labor are recorded.
9. Supervisor verifies completion quality.
10. Work order is closed.
11. History feeds KPIs, compliance, and reliability analysis.

### Request-to-Close Lifecycle

#### A. Request Intake

Sources:

- operator raises fault
- technician identifies follow-up work
- preventive plan becomes due
- sensor threshold is reached
- inspection finds a defect
- external system sends an exception

Outputs:

- work request
- or directly generated preventive work order depending on policy

#### B. Triage

Planner or supervisor decides:

- valid or invalid request
- asset affected
- system affected
- urgency and priority
- work type
- safety implications
- shutdown needed or not
- approval needed or not

Possible results:

- reject request
- convert to work order
- merge into existing work order
- defer to backlog

#### C. Planning

Planner adds:

- task package
- task steps
- required skill
- estimated hours
- permits
- tools
- spare parts
- vendor or contractor
- planned dates

#### D. Scheduling

Scheduler assigns:

- technician or crew
- calendar slot
- outage/shutdown window
- material availability

#### E. Execution

Technician performs:

- start work
- execute task steps
- record findings
- attach measurements
- attach photos
- consume parts
- book labor
- pause or complete

#### F. Verification

Supervisor checks:

- steps complete
- failure resolved
- documents attached if required
- readings within limits
- test or restart successful

#### G. Closure

Closure captures:

- final failure code
- root cause
- downtime duration
- actual labor
- actual parts cost
- close date
- lessons learned

## Information Model Overview

The module should be built from a set of clean master tables plus transactional tables.

### Core Hierarchy

Recommended hierarchy:

- `organization`
- `site`
- `location`
- `system`
- `asset`
- `asset_component`
- `sensor`

This allows:

- plant-level navigation
- system-level reporting
- asset and sub-asset maintenance history
- component-level supplier/manufacturer traceability
- sensor-linked triggers

## Canonical Table Set

The following is the recommended initial enterprise CMMS table catalog.

### 1. `location`

Purpose:

- physical hierarchy for where things are installed

Examples:

- Plant A
- Utility Building
- Line 2
- Packing Area
- Workshop

Recommended fields:

- `id`
- `location_code`
- `name`
- `description`
- `location_type`
- `parent_location_id`
- `site_code`
- `status`
- `cost_center`
- `owning_department`
- `timezone`
- `is_active`
- `notes`

Recommended `location_type` values:

- `site`
- `building`
- `floor`
- `area`
- `line`
- `room`
- `yard`
- `warehouse`

### 2. `system`

Purpose:

- represent a functional or process system between location and asset

Examples:

- cooling water system
- compressed air system
- packaging system
- fire suppression system

Recommended fields:

- `id`
- `system_code`
- `name`
- `description`
- `location_id`
- `parent_system_id`
- `system_type`
- `criticality`
- `status`
- `is_active`
- `notes`

Recommended design rules:

- a system belongs to one location
- a system can contain child systems
- a system can own many assets

### 3. `asset`

Purpose:

- master record for each maintainable equipment item

Recommended fields:

- `id`
- `asset_code`
- `name`
- `description`
- `asset_type`
- `category`
- `status`
- `criticality`
- `location_id`
- `system_id`
- `parent_asset_id`
- `manufacturer_party_id`
- `supplier_party_id`
- `model_number`
- `serial_number`
- `barcode`
- `install_date`
- `commission_date`
- `warranty_start`
- `warranty_end`
- `expected_life_years`
- `replacement_cost`
- `maintenance_strategy`
- `service_level`
- `requires_shutdown_for_major_work`
- `is_active`
- `notes`

Recommended `status` values:

- `in_service`
- `out_of_service`
- `standby`
- `under_repair`
- `retired`
- `disposed`

Recommended `criticality` values:

- `low`
- `medium`
- `high`
- `critical`

### 4. `asset_component`

Purpose:

- track important serviceable or replaceable sub-items

Examples:

- motor
- gearbox
- bearing assembly
- seal cartridge
- drive board

Recommended fields:

- `id`
- `asset_id`
- `component_code`
- `name`
- `description`
- `component_type`
- `manufacturer_party_id`
- `supplier_party_id`
- `manufacturer_part_number`
- `supplier_part_number`
- `model_number`
- `serial_number`
- `install_date`
- `warranty_end`
- `expected_life_hours`
- `expected_life_cycles`
- `is_critical_component`
- `notes`

### 5. `sensor`

Purpose:

- store counters, meters, and condition inputs used by monitoring and preventive triggers

Recommended fields:

- `id`
- `sensor_code`
- `sensor_name`
- `sensor_tag`
- `sensor_type`
- `asset_id`
- `component_id`
- `system_id`
- `source_type`
- `source_name`
- `source_key`
- `unit`
- `current_value`
- `last_read_at`
- `last_quality_state`
- `is_active`
- `notes`

Recommended `sensor_type` values:

- `running_hours`
- `cycle_count`
- `temperature`
- `pressure`
- `vibration`
- `flow`
- `energy`
- `oil_quality`
- `custom`

Recommended `last_quality_state` values:

- `valid`
- `stale`
- `estimated`
- `error`

Critical rule:

- preventive plans must link to the sensor record, not only store a sensor name string
- the named sensor must stay connected to the source mapping used for integration

### 6. `maintenance_task_template`

Purpose:

- reusable task library for preventive or standard corrective work

Examples:

- inspect pump coupling
- grease motor bearings
- replace suction filter
- perform vibration check

Recommended fields:

- `id`
- `task_template_code`
- `name`
- `description`
- `maintenance_type`
- `revision_no`
- `template_status`
- `estimated_minutes`
- `required_skill`
- `requires_shutdown`
- `requires_permit`
- `is_active`
- `notes`

Important design rule:

- `maintenance_task_template` should describe the work content only
- it should not be tied to one fixed schedule or one fixed sensor
- trigger behavior belongs to `preventive_plan` or `preventive_plan_task`
- this allows the same task template to be reused in daily, weekly, monthly, yearly, or sensor-driven plans

### 7. `maintenance_task_step_template`

Purpose:

- reusable step-by-step instructions for a task template

Recommended fields:

- `id`
- `task_template_id`
- `step_number`
- `instruction`
- `expected_result`
- `hint_level`
- `hint_text`
- `requires_confirmation`
- `requires_measurement`
- `requires_photo`
- `measurement_unit`
- `sort_order`

Recommended `hint_level` values:

- `note`
- `caution`
- `warning`
- `danger`

Attachment rule:

- task templates and task step templates should use `document_link`
- this allows instructions, drawings, photos, manuals, and procedures to be attached to the library definition

### Administrative Maintenance Library

The module should include an administration-oriented setup area where only authorized users can edit the maintenance library.

This area should control:

- task templates
- task step templates
- task attachments
- step attachments
- trigger defaults
- safety hints
- revisions
- status and activation

Recommended access:

- admins, planners, reliability engineers, and maintenance managers can edit library records
- technicians can view generated work but should not change the master template library from execution screens

Critical enterprise rule:

- when a work order is generated, the system must copy the relevant template and step information into execution records
- later template edits must not change historical work already issued to technicians

### 8. `preventive_plan`

Purpose:

- define recurring or condition-driven maintenance logic

Recommended fields:

- `id`
- `plan_code`
- `asset_id`
- `component_id`
- `system_id`
- `name`
- `description`
- `status`
- `plan_type`
- `priority`
- `trigger_mode`
- `calendar_frequency_unit`
- `calendar_frequency_value`
- `sensor_id`
- `sensor_threshold`
- `sensor_direction`
- `sensor_reset_rule`
- `last_generated_at`
- `last_completed_at`
- `next_due_at`
- `next_due_counter`
- `requires_shutdown`
- `approval_required`
- `auto_generate_work_order`
- `is_active`
- `notes`

Recommended `plan_type` values:

- `preventive`
- `inspection`
- `lubrication`
- `calibration`
- `condition_based`

Recommended `trigger_mode` values:

- `calendar`
- `sensor`
- `hybrid`

Recommended `calendar_frequency_unit` values:

- `daily`
- `weekly`
- `monthly`
- `quarterly`
- `yearly`
- `custom_days`

Recommended `sensor_direction` values:

- `greater_or_equal`
- `less_or_equal`
- `equal`

Mandatory business rule:

- if a plan is `hybrid`, the sensor trigger has priority over the calendar trigger

Operational rule:

- if hybrid logic is used and sensor values are stale, planners should see an exception queue instead of silent generation

### 9. `preventive_plan_task`

Purpose:

- attach one or more reusable tasks to a preventive plan

Recommended fields:

- `id`
- `plan_id`
- `task_template_id`
- `trigger_scope`
- `trigger_mode_override`
- `calendar_frequency_unit_override`
- `calendar_frequency_value_override`
- `sensor_id_override`
- `sensor_threshold_override`
- `sensor_direction_override`
- `sequence_no`
- `is_mandatory`
- `default_assigned_employee_id`
- `default_assigned_team_id`
- `estimated_minutes_override`
- `notes`

Recommended `trigger_scope` values:

- `inherit_plan`
- `task_override`

Important rule:

- user-facing preventive tasks can be calendar-triggered or sensor-triggered
- by default, a preventive task inherits the trigger from its parent `preventive_plan`
- when a task needs its own trigger, `preventive_plan_task` may override the plan trigger
- this supports cases such as one plan having a general monthly inspection plus a second task driven by running hours

### 10. `document`

Purpose:

- store reusable document metadata

Recommended fields:

- `id`
- `document_code`
- `title`
- `document_type`
- `document_structure_id`
- `version`
- `revision`
- `file_name`
- `storage_uri`
- `mime_type`
- `source_system`
- `uploaded_at`
- `uploaded_by_user_id`
- `effective_date`
- `review_date`
- `is_current`
- `confidentiality_level`
- `notes`

Recommended `document_type` values:

- `manual`
- `datasheet`
- `drawing`
- `procedure`
- `instruction`
- `certificate`
- `warranty`
- `photo`
- `report`
- `other`

### 11. `document_structure`

Purpose:

- classify and organize document categories and folders logically

This table is important because enterprise CMMS deployments often need controlled document taxonomy.

Recommended fields:

- `id`
- `structure_code`
- `name`
- `description`
- `parent_structure_id`
- `object_scope`
- `default_document_type`
- `sort_order`
- `is_active`

Examples:

- Asset Manuals
- Sensor Datasheets
- PM Procedures
- Calibration Certificates
- Work Order Photos

### 12. `document_link`

Purpose:

- link one document to many business objects

Recommended fields:

- `id`
- `document_id`
- `linked_object_type`
- `linked_object_id`
- `relationship_type`
- `is_primary`
- `sort_order`
- `notes`

Recommended `linked_object_type` values:

- `asset`
- `asset_component`
- `system`
- `sensor`
- `preventive_plan`
- `task_template`
- `work_order`
- `work_order_task`

### 13. `party`

Purpose:

- unified master for suppliers, manufacturers, vendors, and service contractors

This is better than creating many almost-identical tables.

Ownership recommendation:

- `party` should be a shared platform domain, not maintenance-only data

Recommended fields:

- `id`
- `party_code`
- `party_name`
- `party_type`
- `legal_name`
- `contact_name`
- `email`
- `phone`
- `address_line_1`
- `address_line_2`
- `city`
- `country`
- `website`
- `tax_reference`
- `is_active`
- `notes`

Recommended `party_type` values:

- `supplier`
- `manufacturer`
- `vendor`
- `contractor`
- `service_provider`

### 14. `work_request`

Purpose:

- capture incoming maintenance demand before formal work planning

Recommended fields:

- `id`
- `request_code`
- `source_type`
- `request_type`
- `asset_id`
- `component_id`
- `system_id`
- `location_id`
- `title`
- `description`
- `priority`
- `status`
- `requested_at`
- `requested_by_user_id`
- `requested_by_name_snapshot`
- `triaged_at`
- `triaged_by_user_id`
- `failure_symptom_code`
- `safety_risk_level`
- `production_impact_level`
- `notes`

Recommended `source_type` values:

- `manual`
- `preventive_plan`
- `sensor_trigger`
- `inspection`
- `integration`

Recommended `status` values:

- `new`
- `triaged`
- `approved`
- `rejected`
- `converted`
- `deferred`

### 15. `work_order`

Purpose:

- execution record for planned maintenance work

Recommended fields:

- `id`
- `work_order_code`
- `work_order_type`
- `source_type`
- `source_id`
- `asset_id`
- `component_id`
- `system_id`
- `location_id`
- `title`
- `description`
- `priority`
- `status`
- `requested_by_user_id`
- `planner_user_id`
- `supervisor_user_id`
- `assigned_team_id`
- `assigned_employee_id`
- `planned_start`
- `planned_end`
- `actual_start`
- `actual_end`
- `requires_shutdown`
- `permit_required`
- `approval_required`
- `failure_code`
- `root_cause_code`
- `downtime_minutes`
- `parts_cost`
- `labor_cost`
- `vendor_party_id`
- `is_preventive`
- `is_emergency`
- `closed_at`
- `closed_by_user_id`
- `notes`

Recommended `work_order_type` values:

- `corrective`
- `preventive`
- `inspection`
- `calibration`
- `emergency`
- `condition_based`

Recommended `status` values:

- `draft`
- `planned`
- `waiting_parts`
- `waiting_approval`
- `waiting_shutdown`
- `scheduled`
- `released`
- `in_progress`
- `paused`
- `completed`
- `verified`
- `closed`
- `cancelled`

### 16. `work_order_task`

Purpose:

- execution-time task rows copied from templates or entered manually

Recommended fields:

- `id`
- `work_order_id`
- `task_template_id`
- `task_name`
- `description`
- `assigned_employee_id`
- `assigned_team_id`
- `estimated_minutes`
- `actual_minutes`
- `required_skill`
- `status`
- `started_at`
- `completed_at`
- `sequence_no`
- `is_mandatory`
- `completion_rule`
- `notes`

Recommended `completion_rule` values:

- `no_steps_required`
- `all_steps_required`

Recommended `status` values:

- `not_started`
- `in_progress`
- `completed`
- `blocked`
- `skipped`

Execution rule:

- this is the technician-facing task record
- it is generated from templates or entered by planners or supervisors
- tasks can be assigned to one person or one team
- if a task has steps, the task can only be completed when all required steps are completed
- if a task has no steps, the task can be completed directly

### 17. `work_order_task_step`

Purpose:

- execution-time step rows copied from task step templates

Recommended fields:

- `id`
- `work_order_task_id`
- `source_step_template_id`
- `step_number`
- `instruction`
- `expected_result`
- `hint_level`
- `hint_text`
- `status`
- `requires_confirmation`
- `requires_measurement`
- `requires_photo`
- `measurement_value`
- `measurement_unit`
- `completed_by_user_id`
- `completed_at`
- `confirmed_by_user_id`
- `confirmed_at`
- `notes`

Recommended `status` values:

- `not_started`
- `in_progress`
- `done`
- `skipped`
- `failed`

### Maintenance-side Material Planning

Because stock and purchasing are better modeled as a separate `inventory_procurement` module, Maintenance should still keep its own demand-side records for work.

Recommended maintenance-owned concept:

- `work_order_material_requirement`

Purpose:

- define what a work order needs before that demand becomes a reservation, issue, or purchase action

Recommended fields:

- `id`
- `work_order_id`
- `stock_item_id`
- `description`
- `required_qty`
- `issued_qty`
- `is_stock_item`
- `preferred_storeroom_id`
- `procurement_status`
- `notes`

Recommended rule:

- Maintenance defines demand
- `inventory_procurement` fulfills that demand through reservation, issue, transfer, receipt, requisition, and purchase-order flows

### 18. `sensor_reading`

Purpose:

- time series or sampled values used for history and trigger decisions

Recommended fields:

- `id`
- `sensor_id`
- `reading_value`
- `reading_unit`
- `reading_timestamp`
- `quality_state`
- `source_name`
- `source_batch_id`
- `received_at`
- `raw_payload_ref`

### 19. `integration_source`

Purpose:

- connection definition for external company systems

Recommended fields:

- `id`
- `integration_code`
- `name`
- `integration_type`
- `endpoint_or_path`
- `authentication_mode`
- `schedule_expression`
- `last_successful_sync_at`
- `last_failed_sync_at`
- `last_error_message`
- `is_active`

Recommended `integration_type` values:

- `rest_api`
- `file_drop`
- `database_sync`
- `iot_gateway`
- `erp_bridge`

### 20. `sensor_source_mapping`

Purpose:

- map incoming external fields to internal sensor records

Recommended fields:

- `id`
- `integration_source_id`
- `sensor_id`
- `external_equipment_key`
- `external_measurement_key`
- `transform_rule`
- `unit_conversion_rule`
- `is_active`

### 21. `downtime_event`

Purpose:

- capture downtime separately from work order status so analytics stay clean

Recommended fields:

- `id`
- `asset_id`
- `system_id`
- `work_order_id`
- `started_at`
- `ended_at`
- `duration_minutes`
- `downtime_type`
- `reason_code`
- `impact_notes`

### 22. `failure_code`

Purpose:

- standardize symptoms, causes, and remedies

Recommended fields:

- `id`
- `failure_code`
- `name`
- `description`
- `code_type`
- `parent_code_id`
- `is_active`

Recommended `code_type` values:

- `symptom`
- `cause`
- `remedy`

### 23. `stock_item`

Purpose:

- master record for spare parts, consumables, and stocked maintenance items

Ownership recommendation:

- `stock_item` should be owned by the `inventory_procurement` module and consumed by Maintenance

Recommended fields:

- `id`
- `item_code`
- `name`
- `description`
- `item_type`
- `uom`
- `manufacturer_party_id`
- `supplier_party_id`
- `manufacturer_part_number`
- `supplier_part_number`
- `preferred_storeroom_id`
- `reorder_point`
- `reorder_quantity`
- `lead_time_days`
- `unit_cost`
- `is_critical_spare`
- `is_active`
- `notes`

Recommended `item_type` values:

- `spare_part`
- `consumable`
- `tool`
- `service_item`

### 24. `storeroom`

Purpose:

- represent physical or virtual stock locations

Ownership recommendation:

- `storeroom` should be owned by the `inventory_procurement` module because it is part of the stock operating model

Recommended fields:

- `id`
- `storeroom_code`
- `name`
- `location_id`
- `status`
- `is_active`
- `notes`

### 25. `stock_balance`

Purpose:

- current quantity of a stock item in a storeroom

Ownership recommendation:

- `stock_balance` should be owned by the `inventory_procurement` module as the central stock state

Recommended fields:

- `id`
- `stock_item_id`
- `storeroom_id`
- `on_hand_qty`
- `reserved_qty`
- `available_qty`
- `reorder_point_override`
- `last_counted_at`

### 26. `stock_transaction`

Purpose:

- audit movement of maintenance inventory

Ownership recommendation:

- `stock_transaction` should be owned by the `inventory_procurement` module, even when movements originate from maintenance work

Recommended fields:

- `id`
- `stock_item_id`
- `storeroom_id`
- `work_order_id`
- `transaction_type`
- `quantity`
- `unit_cost`
- `transaction_at`
- `performed_by_user_id`
- `reference_no`
- `notes`

Recommended `transaction_type` values:

- `receipt`
- `issue`
- `return`
- `adjustment`
- `transfer_in`
- `transfer_out`

### 27. `material_reservation`

Purpose:

- reserve stock for planned work before execution begins

Ownership recommendation:

- `material_reservation` should be owned by the `inventory_procurement` module, with links back to maintenance work orders

Recommended fields:

- `id`
- `work_order_id`
- `stock_item_id`
- `storeroom_id`
- `reserved_qty`
- `issued_qty`
- `status`
- `reserved_at`
- `reserved_by_user_id`
- `notes`

Recommended `status` values:

- `reserved`
- `partially_issued`
- `issued`
- `cancelled`

### 28. `purchase_requisition`

Purpose:

- internal request to buy missing stock or direct-charge maintenance items

Ownership recommendation:

- `purchase_requisition` should be owned by the `inventory_procurement` module

Recommended fields:

- `id`
- `requisition_no`
- `requested_by_user_id`
- `status`
- `work_order_id`
- `supplier_party_id`
- `requested_at`
- `approved_at`
- `approved_by_user_id`
- `notes`

Recommended `status` values:

- `draft`
- `submitted`
- `approved`
- `rejected`
- `ordered`
- `cancelled`

### 29. `purchase_order`

Purpose:

- supplier order for stock or direct work-order material

Ownership recommendation:

- `purchase_order` should be owned by the `inventory_procurement` module

Recommended fields:

- `id`
- `po_number`
- `supplier_party_id`
- `status`
- `work_order_id`
- `ordered_at`
- `expected_delivery_at`
- `received_at`
- `currency_code`
- `total_amount`
- `notes`

Recommended `status` values:

- `draft`
- `approved`
- `issued`
- `partially_received`
- `received`
- `closed`
- `cancelled`

### 30. `purchase_order_line`

Purpose:

- line-level detail for each purchased spare, consumable, or service

Ownership recommendation:

- `purchase_order_line` should be owned by the `inventory_procurement` module

Recommended fields:

- `id`
- `purchase_order_id`
- `stock_item_id`
- `line_no`
- `description`
- `ordered_qty`
- `received_qty`
- `unit_price`
- `target_storeroom_id`
- `target_work_order_id`
- `notes`

## Relationship Summary

Important core relationships:

- one `location` can have many child `location`
- one `location` can have many `system`
- one `system` can have many child `system`
- one `system` can have many `asset`
- one `asset` can have many child `asset`
- one `asset` can have many `asset_component`
- one `asset` or `asset_component` can have many `sensor`
- one `asset`, `sensor`, `task`, or `work_order` can link to many `document`
- one `preventive_plan` can have many `preventive_plan_task`
- one `work_order` can have many `work_order_task`
- one `work_order_task` can have many `work_order_task_step`
- one `stock_item` can have many `stock_balance`
- one `work_order` can have many `material_reservation`
- one `work_order` can have many purchasing references

## Real Preventive Maintenance Logic

### Supported Trigger Modes

The system must support:

- calendar-based maintenance
- sensor/counter-based maintenance
- hybrid maintenance

### Calendar Examples

- daily
- weekly
- monthly
- quarterly
- yearly
- every 7 days
- every month
- every quarter
- every year

Calendar trigger meaning:

- `daily` means every day or every configured N days
- `weekly` means every week or every configured N weeks
- `monthly` means every month or every configured N months
- `quarterly` means every 3 months or every configured N quarters
- `yearly` means every year or every configured N years

### Sensor Examples

- after 200 running hours
- every 5,000 cycles
- when vibration exceeds threshold

### Task-Level Trigger Interpretation

For business users, it is valid to say that a preventive maintenance task can be:

- calendar triggered
- sensor triggered
- hybrid triggered

For system design, this should be interpreted as:

- reusable task templates stay generic
- the preventive plan provides the default trigger
- the plan-task row may optionally override the trigger for that specific task instance

This keeps the model scalable while matching how maintenance teams think about due work.

### Hybrid Rule

If both calendar and sensor logic exist:

- sensor trigger is prioritized

Recommended behavior:

1. evaluate sensor due state first
2. if sensor condition is due, mark plan due immediately
3. if sensor is not due, evaluate calendar due state
4. if sensor feed is stale for a hybrid plan, raise `sensor_exception` for planner review

### Sensor Exception Queue

The module should expose a queue for:

- missing sensor feed
- stale reading
- unit mismatch
- invalid threshold mapping
- external sync failures

## Work Execution Rules

Enterprise CMMS execution should include strong operational controls.

Recommended business rules:

- no work order should close while mandatory tasks remain incomplete
- no work order should close while mandatory task steps remain incomplete
- a task can be completed only when all required steps are completed, except when that task has no steps
- assigned tasks should clearly show the responsible technician or team
- templates should be editable only in the admin or library area, not in technician execution views
- if a step requires a photo, closure should be blocked until attached or waived with reason
- if a step requires a measurement, capture value and unit
- emergency work can bypass some approvals but must still create audit history
- shutdown-required work should not move to released/in-progress without shutdown clearance

## Admin Setup vs Technician Execution

To match real industrial CMMS behavior, the system should separate configuration from execution.

### Admin or Planner Setup Area

This section is where authorized users manage:

- task templates
- task step templates
- trigger logic
- default assignees
- safety hints
- library attachments
- template revisions
- preventive plan definitions

### Technician Execution Area

This section is where technicians see:

- assigned work orders
- generated work-order tasks
- generated work-order task steps
- their own completion status
- required measurements
- required photos
- attached procedures and drawings

Technicians should update execution records, not template definitions.

## Stock, Spares, and Purchasing

For industrial readiness, the module should include maintenance materials control.

Recommended capabilities:

- spare-part master
- storerooms
- stock balances
- stock movement history
- reservations against work orders
- direct issue to jobs
- purchase requisitions for missing parts
- purchase orders to suppliers
- receipt against purchase orders

This is a major enterprise CMMS differentiator and should be planned into the design early, even if some runtime screens ship after the first asset and work-order slice.

## Documents and Control Rules

The document model should support:

- multiple document versions
- one current version flag
- many-to-many links to business records
- classification by document structure
- source tracking if documents originate in another system

Examples:

- pump manual linked to asset
- vibration sensor datasheet linked to sensor
- lubrication SOP linked to task template
- as-built drawing linked to system
- completion photos linked to work order

## Enterprise UI Direction

Recommended maintenance shell tabs:

- `Dashboard`
- `Requests`
- `Work Orders`
- `Planner`
- `Assets`
- `Preventive Plans`
- `Sensors`
- `Documents`
- `Analytics`

Optional later tabs:

- `Reliability`
- `Vendors`

### Dashboard

Should summarize:

- open requests
- open work orders
- overdue work
- PM compliance
- sensor exceptions
- downtime trend
- top failing assets
- labor utilization

### Requests

Primary queue for:

- new requests
- deferred requests
- rejected requests
- requests waiting triage

### Work Orders

Primary queue for:

- assigned to me
- assigned to my team
- waiting approval
- waiting parts
- waiting shutdown
- in progress
- completed pending verification
- recently closed

Each work order detail should expose:

- generated tasks
- task steps
- assignees
- attachments
- material requirements
- reservation status
- purchase status
- labor and downtime

### Planner

Should support:

- backlog prioritization
- drag/drop scheduling
- weekly plan
- shutdown planning
- crew loading
- due preventive plans

### Assets

Each asset detail screen should expose:

- hierarchy path
- current status
- latest sensor values
- open work orders
- preventive plans
- document links
- maintenance history
- downtime history
- component list
- supplier/manufacturer references

### Preventive Plans

Should support:

- due now
- due soon
- hybrid-trigger exceptions
- inactive plans
- last execution summary

### Sensors

Should support:

- latest reading
- source mapping
- quality state
- stale sensors
- integration errors

### Documents

Should support:

- category browsing by document structure
- linked objects
- current version filter
- expiring review dates

### Inventory & Procurement Module

The separate `Inventory & Procurement` module should own the stock and purchasing workspaces.

Recommended shell tabs for that module:

- `Inventory Dashboard`
- `Items`
- `Storerooms`
- `Stock`
- `Requisitions`
- `Purchase Orders`
- `Receiving`

Recommended integrated behaviors:

- Maintenance work orders show material demand and fulfillment status
- users can open the stock or purchasing module from linked material actions
- inventory users can see which reservations and purchases are tied back to maintenance work orders

## Service Boundary Proposal

Recommended service packages:

- `core/platform/party`
- `core/modules/inventory_procurement/services/item_master`
- `core/modules/inventory_procurement/services/inventory`
- `core/modules/inventory_procurement/services/procurement`
- `core/modules/inventory_procurement/services/receiving`
- `core/modules/maintenance_management/services/location`
- `core/modules/maintenance_management/services/system`
- `core/modules/maintenance_management/services/asset`
- `core/modules/maintenance_management/services/sensor`
- `core/modules/maintenance_management/services/document`
- `core/modules/maintenance_management/services/preventive`
- `core/modules/maintenance_management/services/work_request`
- `core/modules/maintenance_management/services/work_order`
- `core/modules/maintenance_management/services/planning`
- `core/modules/maintenance_management/services/materials`
- `core/modules/maintenance_management/services/vendor_execution`
- `core/modules/maintenance_management/services/integration`
- `core/modules/maintenance_management/services/analytics`

Recommended UI packages:

- `ui/modules/inventory_procurement/dashboard`
- `ui/modules/inventory_procurement/items`
- `ui/modules/inventory_procurement/storerooms`
- `ui/modules/inventory_procurement/stock`
- `ui/modules/inventory_procurement/purchasing`
- `ui/modules/maintenance_management/dashboard`
- `ui/modules/maintenance_management/requests`
- `ui/modules/maintenance_management/work_orders`
- `ui/modules/maintenance_management/planner`
- `ui/modules/maintenance_management/assets`
- `ui/modules/maintenance_management/preventive`
- `ui/modules/maintenance_management/sensors`
- `ui/modules/maintenance_management/documents`
- `ui/modules/maintenance_management/analytics`

## Shared Platform Reuse

The maintenance module should reuse:

- user and role management
- organizations and entitlements
- employees and teams
- shared audit service
- shared approvals/governance
- collaboration feed
- document storage plumbing when available
- shared time/work-entry boundary for labor booking
- shared party master for suppliers, manufacturers, and vendors
- `inventory_procurement` services for item, storeroom, balance, reservation, purchasing, and receiving flows

## Import Workbook Design

The system should provide a connected Excel or spreadsheet template that mirrors the main master tables.

### Recommended Workbook Sheets

- `Locations`
- `Systems`
- `Assets`
- `AssetComponents`
- `Sensors`
- `Parties`
- `TaskTemplates`
- `TaskStepTemplates`
- `PreventivePlans`
- `PreventivePlanTasks`
- `StockItems`
- `Storerooms`
- `StockBalances`
- `Documents`
- `DocumentStructures`
- `DocumentLinks`

### Workbook Key Rules

- each sheet must use stable business keys
- child sheets must reference parent business keys
- imports must support dry-run validation
- errors must be returned by row and column
- examples should be included in sample template versions

### Suggested Business Keys

- `location_code`
- `system_code`
- `asset_code`
- `component_code`
- `sensor_code`
- `party_code`
- `task_template_code`
- `plan_code`
- `document_code`
- `structure_code`

### Example Linking Rules

- `Assets.system_code` references `Systems.system_code`
- `Assets.location_code` references `Locations.location_code`
- `Sensors.asset_code` references `Assets.asset_code`
- `PreventivePlans.asset_code` references `Assets.asset_code`
- `PreventivePlans.sensor_code` references `Sensors.sensor_code`
- `PreventivePlanTasks.plan_code` references `PreventivePlans.plan_code`
- `PreventivePlanTasks.task_template_code` references `TaskTemplates.task_template_code`

Recommended trigger import columns:

- `PreventivePlans.trigger_mode`
- `PreventivePlans.calendar_frequency_unit`
- `PreventivePlans.calendar_frequency_value`
- `PreventivePlans.sensor_code`
- `PreventivePlans.sensor_threshold`
- `PreventivePlanTasks.trigger_scope`
- `PreventivePlanTasks.trigger_mode_override`
- `PreventivePlanTasks.calendar_frequency_unit_override`
- `PreventivePlanTasks.calendar_frequency_value_override`
- `PreventivePlanTasks.sensor_code_override`
- `PreventivePlanTasks.sensor_threshold_override`
- `DocumentLinks.document_code` references `Documents.document_code`

## Implementation Phases

### Phase 1: Core Master Data and Work Basics

Build first:

- location
- system
- asset
- asset component
- party
- document
- document structure
- document link
- work request
- work order

Current kickoff status:

- started: module-owned `location`, `system`, `asset`, `asset_component`, `work_request`, `work_order`, `work_order_task`, `work_order_task_step`, `work_order_material_requirement`, `sensor`, `sensor_reading`, `integration_source`, `sensor_source_mapping`, `sensor_exception`, `failure_code`, and `downtime_event` domain models, repository contracts, lifecycle services, SQLAlchemy persistence, migration coverage, and service-graph wiring
- started: first shell/UI surfaces for `Maintenance Dashboard`, `Assets`, `Sensors`, `Requests`, `Work Orders`, `Documents`, `Planner`, and `Reliability`, backed by the live asset, sensor, request, work-order, document, and reliability services
- started: preventive-maintenance foundation for `maintenance_task_template`, `maintenance_task_step_template`, `preventive_plan`, and `preventive_plan_task`, including lifecycle services, SQLAlchemy persistence, migration coverage, and service-graph wiring
- started: preventive due-generation engine for calendar, sensor, and hybrid plans, including work-request/work-order generation and template-to-execution task/step copying
- pending: broader technician execution runtimes

Phase 1 UI:

- Maintenance Dashboard
- Reliability
- Assets
- Sensors
- Requests
- Work Orders
- Documents
- Planner

### Phase 2: Preventive Maintenance and Task Library

Build next:

- maintenance task templates. Started.
- task step templates. Started.
- preventive plans. Started.
- preventive plan tasks. Started.
- due generation engine. Started.

Phase 2 UI:

- Preventive Plans
- Planner

### Phase 3: Stock, Spares, and Purchasing

Build next:

- `inventory_procurement` module scaffold
- shared or reusable party master alignment
- stock item
- storeroom
- stock balance
- stock transaction
- material reservation
- purchase requisition
- purchase order
- purchase order line

Phase 3 UI:

- Inventory & Procurement module workspaces

### Phase 4: Sensors and Integration

Build next:

- integration status cards. Started.
- exception queue UI. Started.
- sensor-driven preventive trigger bridge. Started.

Phase 4 UI:

- Sensors
- integration status cards
- exception queue

### Phase 5: Reliability and Advanced Control

Build next:

- reliability dashboard and reliability-engineer workbench UI. Started.
- planner-facing recurring-failure and root-cause review queues. Started.
- deeper rendered reliability packs such as recurring-failure and exception-review workbooks once preventive and exception UI flows exist

## Initial Development Backlog

### Domain and Data

- started: define enums for maintenance statuses, priorities, criticality, and trigger modes
- started: create the first phase-1 domain models for `location`, `system`, `asset`, and `asset_component`
- started: add repository interfaces for `location`, `system`, `asset`, and `asset_component`
- started: add SQLAlchemy mappings and migrations for `location`, `system`, `asset`, and `asset_component`
- define cross-table unique business keys
- define template revision behavior
- define task completion gate logic

### Services

- started: asset and asset-component master services, work request services, work order lifecycle services, and work-order task execution services
- document and document-link services
- preventive trigger evaluation service. Started.
- inventory and reservation services
- purchase requisition and purchase order services
- started: sensor ingestion and validation service
- started: reliability analytics helpers for KPI snapshot, root-cause suggestion, and recurring-failure detection

### UI

- started: workspace registration, module licensing, `Maintenance Dashboard`, `Assets`, `Sensors`, `Requests`, `Work Orders`, `Documents`, `Planner`, and `Reliability` workbench surfaces
- asset list/detail runtime
- work request queue
- work order queue and detail runtime
- started: planner runtime
- started: sensors exception runtime
- stock runtime
- purchasing runtime
- documents browser runtime

### Import

- workbook template generator
- workbook validation services
- row-level import diagnostics
- dry-run preview UI

### Reporting and Audit

- started: maintenance dashboard KPI/report foundations
- started: work order lead-time and backlog metrics
- started: PM compliance metrics
- started: downtime metrics
- audit coverage for status and master-data changes

## Key Business Rules

- every asset belongs to a location
- every maintainable asset should optionally belong to a system
- every hybrid preventive plan prioritizes sensor logic over calendar logic
- every preventive task may inherit the plan trigger or override it through `preventive_plan_task`
- every technician-facing task is a generated execution record, not a live template row
- every task with steps must block task completion until required steps are done
- inventory and purchasing should be owned by a dedicated `inventory_procurement` business module
- maintenance should consume inventory and procurement services instead of owning duplicate stock ledgers
- every document can be linked to multiple objects through `document_link`
- every enterprise rollout should plan for spares, stock, and procurement even if it is phased after core work orders
- every reusable instruction should live in task templates and task-step templates
- every execution record should copy templates into work-order-specific records
- every important status transition should be audited
- every external sensor sync should preserve raw source traceability

## What "Pro Enterprise CMMS" Means Here

For this product, a professional enterprise CMMS should provide:

- strong master data
- controlled document taxonomy
- reusable maintenance task libraries
- guided execution with step hints
- clean planner and work queues
- admin-controlled maintenance libraries separate from technician execution
- stock, spare-part, and purchasing control linked to work
- formal preventive trigger logic
- integration-ready sensor architecture
- supplier and manufacturer traceability
- auditability and structured import for rollout at scale

## Next Product Questions

These are the best questions to answer before implementation starts:

1. Should `site` be its own table in phase 1, or is `location` enough initially?
2. Do you want `party` as one unified table, or separate `supplier` and `manufacturer` tables?
3. Should preventive plans generate work requests first, or direct work orders by default?
4. Should technicians record labor through the shared time boundary from day one?
5. Should the `inventory_procurement` module skeleton ship before Maintenance runtime screens, or in parallel?

## Summary

This maintenance blueprint is now aligned around the exact enterprise CMMS structure requested:

- `location` table
- `system` table
- `asset` table
- `asset_component` table
- `sensor` table
- `maintenance_task_template` table
- `maintenance_task_step_template` table
- `preventive_plan` and `preventive_plan_task` tables
- `document`, `document_structure`, and `document_link` tables
- `party` table for supplier/manufacturer/vendor information
- `work_request` and `work_order` tables
- `stock_item`, `storeroom`, `stock_balance`, `stock_transaction`, and `material_reservation` tables
- `purchase_requisition`, `purchase_order`, and `purchase_order_line` tables
- integration and sensor reading tables

It also defines a clean real-world CMMS operating flow from request through closure, an admin-only maintenance library versus technician execution model, and a separate `inventory_procurement` module strategy so stock and purchasing integrate cleanly with the current repo architecture.
