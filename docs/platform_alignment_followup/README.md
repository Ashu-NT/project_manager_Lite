# Platform Alignment Follow-Up

## Purpose

This README tracks the concrete implementation follow-up that comes after the recent cross-platform architecture clarification.

The guiding rule remains:

**share enterprise capabilities, not business ownership.**

This tracker exists so the next implementation slices stay visible, ordered, and auditable inside the repo instead of being scattered across chat history.

## Current Status

- Completed in this slice:
  - shared `site` master data foundation under `core/platform/org`
  - persistent `sites` table and repository wiring
  - platform admin `Sites` workspace for managing shared site records by active organization
  - additive `sites_changed` domain event for future cross-module refresh
- Completed in the current slice:
  - shared `department` reference model under `core/platform/org`
  - persistent `departments` table and repository wiring
  - platform admin `Departments` workspace for managing shared department records by active organization
  - additive `departments_changed` domain event for future cross-module refresh
- Completed in the current slice:
  - shared `documents` domain foundation under `core/platform/documents`
  - persistent `documents` and `document_links` tables with org-scoped link infrastructure
  - platform admin `Documents` workspace now behaves as a shared document library with preview state, richer metadata, and cross-module link visibility
  - additive `documents_changed` domain event for future cross-module refresh
- Expanded in the current slice:
  - `site` now carries operational metadata such as geography, timezone, currency, lifecycle status, calendar defaults, timestamps, and notes
  - `department` now carries hierarchy and business metadata such as site reference, parent department, type, cost center, manager reference, timestamps, and notes
  - `document` now carries richer library metadata such as document type, file/storage details, source system, upload metadata, review/effective dates, confidentiality, revision, and current-state flags
- Completed in the current slice:
  - shared `party` domain foundation under `core/platform/party`
  - persistent `parties` table and repository wiring
  - platform admin `Parties` workspace for managing shared supplier, manufacturer, vendor, contractor, and service-provider identities
  - additive `parties_changed` domain event for future cross-module refresh
- Expanded after the initial inventory kickoff:
  - `inventory_procurement` now includes real phase-1 runtime workflows for item master, storerooms, stock balances, stock transactions, reservations, requisitions, purchase orders, and receiving
  - inventory UI workspaces now surface those phase-1 flows through the enterprise shell when the module is licensed and enabled
  - shared `site`, `party`, `documents`, `approvals`, and `audit` seams are now exercised by a real non-PM business module
- Completed in the current slice:
  - module-neutral `DomainChangeEvent` envelope for generic refresh and integration subscribers
  - additive `domain_changed` bridge that mirrors specific platform and module events without removing them
  - additive `shared_master_changed` bridge for shared reference/master-data refresh flows
- Completed in the current slice:
  - service registration now builds repository, platform, and `project_management` bundles separately under `infra/platform/service_registration`
  - `infra/platform/services.py` now acts as a thin coordinator that assembles the stable `ServiceGraph`
  - module-specific approval handler registration now lives with the `project_management` registration layer instead of the central service graph builder
- Completed in the current slice:
  - shared `core/platform/authorization` engine seam for future auth/access policy evolution
  - auth and access authorization helpers now delegate through one shared decision path
  - dedicated auth/access scaling tracker in `docs/platform_alignment_followup/auth_access_scaling/README.md`
- Completed in the current slice:
  - employee administration now prefers shared `site` and `department` selectors while keeping readable compatibility strings underneath
  - the employee UI now exposes explicit links back to the `Sites` and `Departments` workspaces so shared-master ownership stays visible
  - selector-backed employee editing now refreshes with shared-master change events without forcing a risky storage migration yet
- Still intentionally transitional:
  - employees still store `site_name` as a compatibility string
  - approved/shared time entries still keep site and department snapshot strings
  - PM task-comment attachments still use their existing module-local storage path until the later UI/integration slice migrates them
  - `site.integration_profile_id` is deferred until a shared integration-profile domain exists
  - `department.default_location_id` now stores a neutral reference to maintenance-owned locations without moving location ownership into platform
  - shared document storage/upload transport is still desktop-first and will need a fuller web-facing storage adapter later

## Execution Order

### 1. Shared Site Master

Status: completed

Scope:

- add a canonical shared `Site` domain model
- scope sites to the active organization context
- keep employee and time-entry string snapshots compatible
- expose a platform admin surface so sites can be managed now

Acceptance notes:

- `site` exists as a real shared platform concept, not only free text
- site records are stored centrally and retrieved per active organization
- no existing PM employee or timesheet workflows are broken

Non-goals for this slice:

- no forced migration of employee `site_name` to foreign keys yet
- no site-aware reporting refactor yet
- no maintenance or inventory coupling yet

### 2. Shared Department Reference Model

Status: completed

Scope:

- introduce a canonical shared `department` reference model
- keep current employee and time-entry department strings during transition
- prepare for a future handoff where `hr_management` may become the richer business owner while the platform keeps a stable shared reference

Acceptance notes:

- department stops being only ad hoc text in platform admin workflows
- module code can reference department by stable IDs and business keys

Non-goals for this slice:

- no forced migration of employee `department` to foreign keys yet
- no change to shared time snapshot storage yet
- no HR-owned organizational model handoff yet

### 3. Shared Documents Domain

Status: completed

Scope:

- create a real shared platform document service
- cover storage metadata, classification, linking, and future versioning support
- keep module-specific document meaning in the owning business module

Acceptance notes:

- attachments are no longer only capability labels or module-local blobs
- maintenance, inventory, HR, and QHSE can link to the same shared document infrastructure

Non-goals for this slice:

- no forced rewrite of PM collaboration attachment storage yet
- no file-upload transport abstraction yet beyond storing shared metadata and references
- no module-specific document business rules inside the platform service

### 4. Shared Party Domain

Status: completed

Scope:

- add canonical shared `party` identity for suppliers, manufacturers, vendors, contractors, and service providers
- keep operational relationships inside the consuming modules

Acceptance notes:

- one shared party identity spine exists
- modules reference party records instead of duplicating supplier or vendor masters

Non-goals for this slice:

- no module-specific vendor qualification, purchase, or maintenance relationship workflows yet
- no party-to-document link matrix yet beyond the shared document infrastructure already in place
- no cross-module replacement of existing free-text vendor labels yet

### 5. Module-Neutral Domain Events

Status: completed

Scope:

- expand the event hub additively with shared-master and module-neutral refresh signals
- keep existing PM-focused events intact during the transition

Acceptance notes:

- cross-module synchronization uses domain events instead of direct coupling
- new modules can subscribe without inheriting PM-specific assumptions

Non-goals for this slice:

- no rewrite of existing PM tabs away from their current specific subscriptions yet
- no event-bus persistence, replay, or asynchronous broker layer yet
- no cross-process integration transport yet beyond the in-process signal hub

### 6. Modular Service Registration

Status: completed

Scope:

- split central service wiring into clearer platform and module seams
- keep current runtime behavior unchanged while reducing PM-centric composition pressure

Acceptance notes:

- shared platform services are assembled separately from business-module services
- new modules can register cleanly without expanding one monolithic builder forever

Non-goals for this slice:

- no dynamic plugin discovery or runtime module auto-loading yet
- no replacement of the stable `build_service_graph()` / `build_service_dict()` public entry points
- no broad repository-layer rewrite beyond grouping the existing registration wiring

### 7. UI Alignment and Selector Migration

Status: completed

Scope:

- move existing admin forms from free-text shared masters toward selectors and linked references
- keep legacy fields readable until each downstream workflow is migrated

Acceptance notes:

- employee, maintenance, inventory, and HR surfaces consume shared masters consistently
- UI deep-links keep read/write ownership clear across module boundaries

Non-goals for this slice:

- no forced migration of employee storage from `department` / `site_name` text to foreign keys yet
- no retrofit of future module surfaces before `maintenance_management`, `inventory_procurement`, or `hr_management` have real runtime workflows
- no rewrite of time-entry snapshot storage, which intentionally stays readable and historical for now

## Next Execution Block

The next implementation block should now follow this order:

### 8. Shared-Master Read Access Hardening

Status: completed

Scope:

- close the module-safe read/query gaps for `site`, `department`, and `party`
- let future modules search and resolve these shared masters without `settings.manage`
- keep write ownership constrained to platform-admin workflows

Acceptance notes:

- future modules can search sites safely
- future modules can resolve departments safely
- future modules can select supplier, vendor, and contractor identities safely
- shared-master reuse no longer requires admin-only permissions for read scenarios

Non-goals for this slice:

- no change to admin ownership of create/update operations
- no inventory or maintenance workflow implementation yet

Completion notes:

- `site.read`, `department.read`, and `party.read` now provide module-safe read/query seams for shared masters
- shared-master reads no longer require `settings.manage`

### 9. Canonical Employee Reference Tightening

Status: completed

Scope:

- add canonical `employee.site_id` and `employee.department_id` references
- keep readable compatibility strings during the transition
- begin carrying canonical shared-master IDs where shared time and work-entry context benefit from them

Acceptance notes:

- `employee` references shared `site` and `department` through IDs
- current readable site and department text remains compatible during transition
- new shared-time/work-entry records can carry canonical IDs without losing readable snapshots

Non-goals for this slice:

- no destructive removal of `site_name` or `department` compatibility fields yet
- no forced rewrite of historical time-entry text snapshots

Completion notes:

- `employee.site_id` and `employee.department_id` now exist as canonical reference fields
- shared time entries now carry canonical `site_id` and `department_id` alongside readable snapshots

### 10. Location Ownership ADR

Status: completed

Scope:

- freeze the remaining ownership ambiguity around `location`
- decide whether `location` stays platform-owned or remains fully inside `maintenance_management`
- keep `system` ownership explicit alongside that decision

Acceptance notes:

- the next ADR clearly answers the location/system ownership question
- maintenance and inventory work can proceed without hidden ownership drift

Non-goals for this slice:

- no runtime `location` implementation yet
- no maintenance domain rollout yet

Completion notes:

- the ownership decision is frozen in `docs/architecture_decisions/ADR-002-location-and-system-ownership.md`
- `platform` keeps `site`; `maintenance_management` owns both `location` and `system`

### 11. Inventory Kickoff

Status: completed

Scope:

- start the real `inventory_procurement` scaffold as soon as shared-master read access is ready
- use `site` and `party` through the hardened shared-master seams from day one

Acceptance notes:

- inventory starts as a standalone business module, not as a maintenance sub-feature
- the scaffold already consumes shared sites and parties through safe read/query paths

Non-goals for this slice:

- no broad purchasing or stock workflow implementation in the same slice as the shared-master hardening

Completion notes:

- the first module-side scaffold started through `InventoryReferenceService`
- inventory now consumes shared `site` and `party` reads instead of inventing local copies
- phase-1 inventory services and UI now cover item master, storerooms, balances, transactions, reservations, requisitions, purchase orders, and receiving
- the remaining follow-up is deeper enterprise hardening, maintenance-facing integration, and richer warehouse control rather than basic module scaffolding

### 12. Shared Import Export Report Runtime

Status: in progress

Detailed follow-up design:
`docs/platform_alignment_followup/import_export_report_runtime/README.md`

Scope:

- extract platform-owned import, export, and report runtime machinery
- keep business mappings, report definitions, and formulas in the owning module
- preserve current PM behavior through compatibility-first wrappers
- use inventory phase-1 as the first non-PM proving ground for shared import/export machinery once the platform runtime exists

Acceptance notes:

- platform owns the machinery
- modules own the meaning
- the ADR rule stays visible in code structure, not only in docs

Non-goals for this slice:

- no migration of PM KPI, EVM, gantt, baseline, or cost semantics into `platform`
- no platform-owned PM report definitions
- no direct platform ownership of module repositories or workflow truth

Completion notes:

- `core/platform/importing`, `core/platform/exporting`, and `core/platform/report_runtime` now exist as platform-owned runtime packages with neutral registries, envelopes, and dispatch seams
- PM import and reporting entry points now delegate through compatibility wrappers instead of owning the runtime machinery themselves
- shared runtime dispatch now enforces module-entitlement and permission checks when connected to the live platform session/runtime context
- platform-owned shared master data exchange now covers `site` and `party` import/export through `MasterDataExchangeService`
- inventory now uses the shared runtimes for requisition, purchase-order, and receipt import/export plus stock/procurement report rendering
- persisted runtime execution tracking now records shared import, export, and report runs across platform and inventory operations
- runtime execution tracking now also records cancellation requests, retry lineage, attempt counts, and richer artifact metadata such as output file name, media type, and metadata payloads
- remaining follow-up is richer writer/background-job orchestration, maintenance-specific bulk import/export contracts, and real async job-worker controls on top of that tracking seam

### 13. Maintenance Readiness Hardening

Status: in progress

Detailed functional target:
`docs/maintenance_management/README.md`

Scope:

- harden the existing platform and module seams that Maintenance will consume from day one
- avoid starting maintenance implementation on top of PM-shaped governance/time/access leftovers
- keep ownership rules from ADR-001 and ADR-002 intact while making the shared seams more maintenance-ready

Acceptance notes:

- access can handle maintenance scopes such as asset and maintenance-area
- approval review is no longer tied to PM-only governance UX
- shared time can book labor against maintenance-owned work records cleanly
- shared document taxonomy is ready for a document-heavy module
- inventory integration points for maintenance material demand are explicit and stable
- maintenance import/export/report contracts have a clean runtime path before rollout-scale data loads begin

Non-goals for this slice:

- no full maintenance module implementation yet
- no relocation of `location` or `system` ownership into platform
- no second stock, document, approval, or time engine inside Maintenance

Progress notes:

- shared `document_structures` are now live as an organization-scoped master under the platform document domain
- documents now carry `document_structure_id` plus a business-facing version/revision label without colliding with optimistic-concurrency `version`
- the platform document admin UI can manage structures, assign them to documents, and filter the shared library by taxonomy

- scoped-access policy ownership now keeps `site` platform-owned while module-owned scopes register from the owning service-registration bundle
- approval review now has a shared platform control workspace, while PM governance keeps PM-only controls such as governance mode and timesheet review
- shared time now persists neutral `work_allocation_id`, owner/scope snapshots, and platform-level `time.read` / `time.manage` permissions while keeping PM assignment APIs as wrappers
- inventory now exposes a dedicated maintenance-material contract service for availability, reservation, issue, return, shortage escalation, and linked requisition lookup
- the `inventory_maintenance_materials_changed` bridge now provides a stable maintenance-facing material refresh event without leaking inventory internals into future maintenance workflows
- shared runtime execution tracking now has the retry/cancellation/artifact groundwork needed before maintenance workbook imports and report runs start
- dormant maintenance import/export/report contract catalogs now exist under `core/modules/maintenance_management` so the future module has canonical operation keys and workbook sheet ownership before service implementation begins
- a maintenance contract-catalog service can now emit rollout workbook and contract-matrix artifacts directly from that scaffold without starting live maintenance workflows
- the first module-owned maintenance core foundation now exists for `location` and `system`, including SQLAlchemy repositories, migration coverage, and service-graph wiring, which unblocks the later org-to-maintenance location reference seam without pushing location ownership back into platform
- shared `Department` records can now persist a neutral `default_location_id` reference through a platform-owned resolver port, with the live adapter registered from the maintenance bundle rather than from `core/platform`
- the first maintenance asset master slice now exists too, with module-owned asset domain, validation service, SQLAlchemy table/repository, migration coverage, and service-graph exposure on top of the persisted location/system foundation
- maintenance now also has the first asset-component slice, including component hierarchy validation, shared-party references, SQLAlchemy persistence, migration coverage, and service-graph exposure on top of the new asset foundation
- maintenance now also has the first work-request and work-order slices, including lifecycle validation, source-request linkage, persistence coverage, service-graph exposure, and regression tests for real create/update flows before phase-1 execution tables continue
- maintenance now also has the first `work_order_task` execution slice, including technician-facing task rows, status transitions, persistence, migration coverage, service-graph exposure, and regression tests ahead of the later `work_order_task_step` slice
- maintenance now also has the first `work_order_task_step` execution slice, including step-level completion rules, confirmation/measurement capture, persistence, migration coverage, service-graph exposure, and regression tests before material-demand planning starts
- maintenance now also has the first `work_order_material_requirement` slice, including demand-side material records, availability refresh against the inventory contract, requisition escalation linkage, persistence, migration coverage, and service-graph exposure
- maintenance now also has the first `sensor` and `sensor_reading` slices, including anchored sensor master data, time-series reading capture, current-value snapshot refresh, persistence, migration coverage, and service-graph exposure
- maintenance now also has the first `integration_source` slice, including sync-endpoint master data, last-success/last-failure tracking, persistence, migration coverage, and service-graph exposure
- maintenance now also has the first `sensor_source_mapping` and `sensor_exception` slices, including external-to-internal sensor binding, exception queue records, persistence, migration coverage, service-graph exposure, and regression coverage for stale/unit-mismatch/sync-failure cases
- maintenance now also has the first reliability foundations for `failure_code` and `downtime_event`, including controlled failure-code master data, downtime duration tracking, work-order downtime rollup, persistence, migration coverage, and service-graph exposure
- maintenance now also has a first reliability analytics foundation on top of those records, including KPI snapshot assembly, root-cause suggestion helpers, recurring-failure rollups, service-graph exposure, and regression coverage for both in-memory and persisted flows
- maintenance now also has the first rendered report-pack layer on top of that analytics seam, including backlog, PM compliance, downtime, and execution overview Excel/PDF outputs wired through the shared report runtime
- maintenance is now cataloged as an available-but-disabled module by default, and the shell can expose the first `Maintenance Dashboard`, `Assets`, `Sensors`, `Requests`, `Work Orders`, `Documents`, `Preventive Plans`, `Planner`, and `Reliability` workspaces when the module is licensed and enabled
- maintenance now also has the first preventive-library foundation for `maintenance_task_template`, `maintenance_task_step_template`, `preventive_plan`, and `preventive_plan_task`, including lifecycle validation, SQLAlchemy persistence, migration coverage, service-graph exposure, and focused regression tests before the due-generation engine starts
- maintenance now also has the first preventive due-generation engine, including calendar/sensor/hybrid evaluation, task-level trigger overrides with persisted runtime state, work-request/work-order generation, and template-to-execution task/step copying through the existing work-order runtime
- the maintenance `Planner` workspace now folds preventive due, due-soon, and blocked review into the same planning surface as backlog, material-risk, and recurring-failure review

## Guardrails

- additive changes first, destructive rewrites later
- keep PM runtime stable during each slice
- reference shared or external records by stable IDs and business keys
- use contracts and domain events for cross-module coordination
- avoid direct cross-module table ownership crossover
- do not let any business module quietly become a second platform

## Follow-Up Pointers

- architecture direction: `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`
- shared-master reuse gate: `docs/platform_alignment_followup/SHARED_MASTER_READINESS_CHECKLIST.md`
- import/export/report runtime follow-up:
  `docs/platform_alignment_followup/import_export_report_runtime/README.md`
- maintenance boundary rules: `docs/maintenance_management/README.md`
- product overview: `README.md`
