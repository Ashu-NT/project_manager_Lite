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
  - platform admin `Documents` workspace for managing shared document records and links
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
- Completed in the current slice:
  - module-neutral `DomainChangeEvent` envelope for generic refresh and integration subscribers
  - additive `domain_changed` bridge that mirrors specific platform and module events without removing them
  - additive `shared_master_changed` bridge for shared reference/master-data refresh flows
- Completed in the current slice:
  - service registration now builds repository, platform, and `project_management` bundles separately under `infra/platform/service_registration`
  - `infra/platform/services.py` now acts as a thin coordinator that assembles the stable `ServiceGraph`
  - module-specific approval handler registration now lives with the `project_management` registration layer instead of the central service graph builder
- Completed in the current slice:
  - employee administration now prefers shared `site` and `department` selectors while keeping readable compatibility strings underneath
  - the employee UI now exposes explicit links back to the `Sites` and `Departments` workspaces so shared-master ownership stays visible
  - selector-backed employee editing now refreshes with shared-master change events without forcing a risky storage migration yet
- Still intentionally transitional:
  - employees still store `site_name` as a compatibility string
  - approved/shared time entries still keep site and department snapshot strings
  - PM task-comment attachments still use their existing module-local storage path until the later UI/integration slice migrates them
  - `site.integration_profile_id` is deferred until a shared integration-profile domain exists
  - `department.default_location_id` is deferred until the shared `location` master is implemented
  - `document.document_structure_id` is deferred until a document structure domain exists
  - business-facing document `version` labels are deferred because `version` is currently reserved for optimistic concurrency in the shared document service

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
- maintenance boundary rules: `docs/maintenance_management/README.md`
- product overview: `README.md`
