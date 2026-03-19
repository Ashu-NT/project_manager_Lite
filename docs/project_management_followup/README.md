# Project Management Follow-Up

## Purpose

This README tracks the technical follow-up for `project_management` after the shared-platform alignment work.

The PM product backlog may be functionally complete for the current roadmap, but there are still a few architecture-alignment slices needed so PM consumes the shared platform cleanly instead of carrying older local patterns forever.

The guiding rules stay the same:

- share enterprise capabilities, not business ownership
- keep PM workflow truth inside `project_management`
- integrate to shared masters and shared services through references and events

## Current Status

- Completed in the current slice:
  - PM collaboration attachments now register in the shared platform document domain
  - new task-comment attachments keep their existing readable attachment tokens in PM while also creating shared `document` + `document_link` records
  - the PM collaboration flow no longer treats attachment storage as PM-only metadata
- Completed in the current slice:
  - PM resource screens now surface shared employee `department` and `site` context for employee-backed resources
  - the resource pool table now exposes planner-facing shared workforce context without moving that ownership into the PM resource aggregate
  - the resource edit dialog now shows employee context directly and refreshes when linked employee records change
- Completed in the current slice:
  - selected PM UI surfaces now consume the module-neutral event bridge instead of depending only on hard-coded PM signals
  - the resource workspace now refreshes from generic platform and shared-master domain events relevant to employee/site/department context
  - the collaboration workspace now refreshes from generic PM and platform domain events for project, task-collaboration, and approval activity
- Still intentionally transitional:
  - existing historical PM task-comment attachments remain readable through the legacy attachment list
  - the task collaboration UI still renders attachment tokens directly instead of a richer shared-document picker/library experience
  - file-based local-only collaboration storage remains local-only and is not yet bridged to shared documents
  - PM time-entry site/department snapshots intentionally stay as historical strings
  - PM resources still do not own department/site fields; they consume shared employee context additively at the UI layer
  - not every PM tab is subscribed to the neutral event layer yet; the change is targeted to the screens where the new shared-platform seams matter most today

## Execution Order

### 1. Shared Documents For PM Collaboration

Status: completed

Scope:

- make the shared document infrastructure consumable from PM services without requiring platform-admin-only document workflows
- register PM task-comment attachments in the platform document library
- keep current PM comment rendering and attachment history compatible

Acceptance notes:

- new PM collaboration attachments create shared document metadata and link records
- PM comments still display attachments exactly as before
- no existing collaboration or import/timesheet regressions are introduced

Non-goals for this slice:

- no destructive rewrite of historical task-comment attachments
- no forced change to file-based local-only collaboration storage
- no shared-document picker UI in PM yet

### 2. Resource Context Alignment

Status: completed

Scope:

- expose shared employee context more clearly in PM resource workflows
- surface employee-linked site and department context in PM resource screens without forcing a resource-domain rewrite

Acceptance notes:

- planners can see shared workforce context directly from PM resource views
- employee-backed resources stay aligned with shared `site` and `department` masters

Non-goals for this slice:

- no migration of PM `resource` into an HR-owned model
- no replacement of PM resource planning with employee assignment logic

### 3. Shared-Master Event Adoption In PM UI

Status: completed

Scope:

- let PM surfaces react to the additive shared-master and module-neutral event layer where it improves correctness
- keep current PM-specific refresh signals intact during the transition

Acceptance notes:

- PM UI can refresh from shared-master changes without hard-coding new cross-module dependencies
- existing PM event subscribers remain compatible

Non-goals for this slice:

- no full rewrite of PM tabs to only generic events
- no broker/process-wide async event transport

### 4. Shared Document UX Deepening

Status: pending

Scope:

- expose shared document links more deliberately inside PM detail views
- prepare richer PM document reuse across collaboration, tasks, and future PM surfaces

Acceptance notes:

- PM can distinguish between raw attachment text and shared document records when the UI is ready
- future maintenance/inventory/QHSE integrations can follow the same document-link pattern

Non-goals for this slice:

- no large document-management workspace inside PM
- no duplicate document master outside the platform

## Guardrails

- additive changes first, destructive rewrites later
- keep PM runtime stable at each slice
- keep business permissions and project-scope permissions in PM, while platform services provide shared plumbing
- avoid duplicating platform masters or turning PM into a second platform

## Follow-Up Pointers

- shared-platform alignment tracker: `docs/platform_alignment_followup/README.md`
- architecture direction: `docs/ENTERPRISE_PLATFORM_EXECUTION_PLAN.md`
- product overview: `README.md`
