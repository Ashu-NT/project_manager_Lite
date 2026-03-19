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
- Still intentionally transitional:
  - employees still store `site_name` as a compatibility string
  - approved/shared time entries still keep site and department snapshot strings
  - employee editing does not yet use shared site or department selectors

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

Status: planned

Scope:

- create a real shared platform document service
- cover storage metadata, classification, linking, and future versioning support
- keep module-specific document meaning in the owning business module

Acceptance notes:

- attachments are no longer only capability labels or module-local blobs
- maintenance, inventory, HR, and QHSE can link to the same shared document infrastructure

### 4. Shared Party Domain

Status: planned

Scope:

- add canonical shared `party` identity for suppliers, manufacturers, vendors, contractors, and service providers
- keep operational relationships inside the consuming modules

Acceptance notes:

- one shared party identity spine exists
- modules reference party records instead of duplicating supplier or vendor masters

### 5. Module-Neutral Domain Events

Status: planned

Scope:

- expand the event hub additively with shared-master and module-neutral refresh signals
- keep existing PM-focused events intact during the transition

Acceptance notes:

- cross-module synchronization uses domain events instead of direct coupling
- new modules can subscribe without inheriting PM-specific assumptions

### 6. Modular Service Registration

Status: planned

Scope:

- split central service wiring into clearer platform and module seams
- keep current runtime behavior unchanged while reducing PM-centric composition pressure

Acceptance notes:

- shared platform services are assembled separately from business-module services
- new modules can register cleanly without expanding one monolithic builder forever

### 7. UI Alignment and Selector Migration

Status: planned

Scope:

- move existing admin forms from free-text shared masters toward selectors and linked references
- keep legacy fields readable until each downstream workflow is migrated

Acceptance notes:

- employee, maintenance, inventory, and HR surfaces consume shared masters consistently
- UI deep-links keep read/write ownership clear across module boundaries

## Guardrails

- additive changes first, destructive rewrites later
- keep PM runtime stable during each slice
- reference shared or external records by stable IDs and business keys
- use contracts and domain events for cross-module coordination
- avoid direct cross-module table ownership crossover
- do not let any business module quietly become a second platform

## Follow-Up Pointers

- architecture direction: `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`
- maintenance boundary rules: `docs/maintenance_management/README.md`
- product overview: `README.md`
