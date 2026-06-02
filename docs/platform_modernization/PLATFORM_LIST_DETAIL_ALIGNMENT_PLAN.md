# Platform Workspace List/Detail Alignment Plan

Status: authoritative follow-up tracker for aligning Platform workspaces to the Project Management list/detail architecture

## Purpose

This document tracks the follow-up work required to redesign all Platform
workspaces so they follow the same enterprise list/detail architecture already
established in the Project Management module.

This is a Platform UI/UX architecture alignment effort inside the shared SaaS
ecosystem. It is not a permission to build parallel widget systems or local
one-off workspace patterns.

The governing interaction model is:

List Page  
-> DataTable  
-> row activation  
-> SectionDetailPage

## Current Status

- Attachment review and plan capture: `[x] complete`
- PM pattern discovery: `[x] complete`
- Platform workspace map: `[x] complete at route/controller/shell level`
- Reusable component inventory: `[x] complete`
- Platform migration execution: `[~] organizations pilot in progress`
- Validation run: `[~] focused Platform validation complete`

## Status Legend

- `[x] complete`
- `[~] in progress`
- `[ ] not started`
- `[!] blocked`

## Critical Guardrails

- Platform must reuse the PM enterprise interaction pattern instead of creating
  a second list/detail architecture.
- Reuse existing shared QML components:
  - `AppWidgets.DataTable`
  - `AppWidgets.TableToolbar`
  - `AppWidgets.TablePaginationBar`
  - `AppWidgets.BulkActionBar`
  - `AppWidgets.BulkChangePropertyPopup`
  - `AppWidgets.ContextualActionToolbar`
  - `AppWidgets.SectionDetailPage`
  - `AppWidgets.ActivityFeed`
  - `AppWidgets.KpiStrip`
  - `AppWidgets.StatusChip`
  - `AppWidgets.InlineMessage`
  - `AppControls.PrimaryButton`
  - `AppControls.SecondaryButton`
  - `AppControls.ConfirmationDialog`
  - `Theme.AppTheme`
  - `DynamicTableModel` / source-model table architecture
- Do not introduce duplicate table, toolbar, detail-page, or inline-message
  systems for Platform.
- Do not start with blind QML rewrites. Discovery and mapping are mandatory.
- Do not show entity-level actions on every detail section.
- Do not show unauthorized or disabled-module sections as permission-denied
  placeholders if they should be hidden by RBAC or entitlement rules.

## Architecture Target

All Platform workspaces should converge on the following structure:

### List Page

- `KpiStrip` when relevant
- `InlineMessage`
- `TableToolbar`
- `DataTable`
- `TablePaginationBar` where row counts justify paging
- `BulkActionBar` where bulk actions are supported

### Detail Page

- `ContextualActionToolbar`
- `InlineMessage`
- `SectionDetailPage`
- section navigation
- lazy-loaded sections
- section-specific content

### Detail Action Rule

Only the `Overview` section shows entity-level actions such as:

- Edit
- Delete
- Set Active / Set Inactive
- Status
- Archive
- Reset Password
- Lock / Unlock
- Assign Role
- Attach Document

When the user navigates to other sections, entity-level actions must be hidden
and replaced by section-specific actions only.

Examples:

- Organization `Overview`: `Edit`, `Set Active`, `Delete`
- Organization `Sites`: `Add Site`, `Open Site`
- Organization `Documents`: `Attach Document`, `New Revision`
- Organization `Audit`: `Export Audit`

## Mandatory Discovery Phase 1 - PM Pattern Study

Status: `[x] complete`

### Goal

Map the reusable PM list/detail pattern before touching Platform.

### Mandatory inspection scope

Inspect:

- `src/ui_qml/modules/project_management/**`

Especially:

- `ProjectsWorkspace.qml`
- `TasksWorkspace.qml`
- `ResourcesWorkspace.qml`
- `TimesheetsWorkspace.qml`
- `FinancialsWorkspace.qml`
- `PortfolioWorkspace.qml`
- `RegisterWorkspace.qml`
- `SchedulingWorkspace.qml`
- `DashboardWorkspace.qml`
- `CollaborationWorkspace.qml`
- PM detail panels
- PM dialog hosts
- `ContextualActionToolbar` usage
- `SectionDetailPage` usage
- `DataTable` usage
- `InlineMessage` placement
- lazy section-loading patterns

### Required PM pattern outputs

- [x] Workspace -> list page -> detail page loading sequence
- [x] List-page structure reference
- [x] Detail-page structure reference
- [x] Row activation and page-hiding behavior
- [x] Section generation pattern
- [x] Lazy-loading pattern
- [x] Dynamic action filtering pattern by active section
- [x] `InlineMessage` placement rules
- [x] `DataTable` + source-model usage notes
- [x] dialog-host pattern reference

### Deliverable

- [x] PM pattern discovery report added to this document

### PM Pattern Discovery Report

#### Files inspected

- `src/ui_qml/modules/project_management/qml/workspaces/projects/ProjectsWorkspacePage.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/projects/ProjectsDetailSection.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspacePage.qml`
- `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksDetailPanel.qml`
- additional PM workspace hits for:
  - `ContextualActionToolbar`
  - `SectionDetailPage`
  - `LazySectionLoader`
  - `LazyObjectLoader`
  - `TableToolbar`
  - `TablePaginationBar`
  - `BulkActionBar`
  - `InlineMessage`
  - `KpiStrip`

#### Reusable PM architecture pattern

The strongest reusable PM pattern is:

1. `WorkspaceFrame` root bound to a typed workspace controller
2. stacked list page and detail page in the same workspace QML
3. list page hidden when `_detailOpen` becomes true
4. detail page created lazily through a `Loader`
5. detail page built on `AppWidgets.SectionDetailPage`
6. top-level `AppWidgets.ContextualActionToolbar`
7. detail body delegated to a dedicated detail component
8. sections loaded lazily through `AppWidgets.LazySectionLoader`

#### List-page structure

Representative list pages in PM consistently use:

- `AppWidgets.KpiStrip`
- loading/busy/error/success `AppWidgets.InlineMessage`
- `AppWidgets.TableToolbar`
- `AppWidgets.DataTable`
- `AppWidgets.TablePaginationBar`
- `AppWidgets.BulkActionBar` when bulk operations exist

This pattern is strongest in:

- `projects`
- `tasks`
- `resources`
- `financials`
- `register`
- `timesheets`
- `portfolio`

#### Detail-page structure

Representative PM detail pages use:

- `Loader { active: _detailOpen; asynchronous: true }`
- `AppWidgets.SectionDetailPage`
- top `AppWidgets.ContextualActionToolbar`
- top detail-level `InlineMessage`
- dedicated detail component such as:
  - `ProjectsDetailSection.qml`
  - `TasksDetailPanel.qml`
  - `ResourcesDetailSection.qml`
  - `RegisterDetailPanel.qml`
  - `SchedulingDetailPanel.qml`

#### Row activation and page hiding behavior

The common PM interaction cycle is:

1. row selected in `DataTable`
2. controller `activate*()` method called
3. workspace sets `_detailOpen = true`
4. list page becomes hidden
5. detail loader activates
6. pending section index is applied
7. first relevant lazy section load is triggered

#### Lazy-loading pattern

PM uses two distinct lazy-loading layers:

- `AppWidgets.LazyObjectLoader` for dialog hosts and heavier shells
- `AppWidgets.LazySectionLoader` for detail sections inside the active detail page

Section loads are usually driven by explicit controller methods such as:

- `loadProjectTasks()`
- `loadProjectResources()`
- `loadSelectedTaskAssignments()`
- `loadSelectedTaskDependencies()`
- `loadSelectedTaskTime()`
- `loadSelectedTaskCollaboration()`

The workspace page triggers these on:

- `Component.onCompleted` of the detail page
- `SectionDetailPage.onSectionChanged`

#### Dynamic action filtering

PM already demonstrates the required action-filtering model, especially in
`TasksWorkspacePage.qml`:

- overview/detail-summary sections expose entity-level actions
- other sections swap to section-specific actions or local section toolbars

Important nuance:

- not every PM workspace is perfectly uniform yet
- `tasks` is the strongest reference for active-section-aware top-level actions
- `projects` still has a more static top-level detail toolbar

For Platform alignment, the reusable rule should be extracted from the stronger
PM pattern rather than copied blindly from every PM file.

#### InlineMessage placement

PM consistently places `InlineMessage` in two layers:

- list page: loading, busy, error, feedback
- detail page: loading, busy, error, feedback for detail actions and section loads

Section-specific `InlineMessage` is also used inside heavier sections where the
section owns its own action cycle.

#### DataTable architecture notes

PM currently uses a mixed model:

- some workspaces still bind `rows: controller.*.items`
- some have already adopted `sourceModel` / `DynamicTableModel`

Platform should align to the stronger shared table direction:

- prefer Python-owned source models where available
- avoid large QML-side row transforms
- do not assume every legacy PM rows-based binding is the target end state

#### Dialog-host pattern

PM centralizes create/edit/delete/status dialogs with lazy dialog hosts, for
example:

- `ProjectsDialogHost`
- `TasksDialogHost`
- resource, financial, and register dialog hosts

This keeps the list/detail workspace shell clean and should be preserved for
Platform rather than inlining ad hoc dialogs into each page.

## Mandatory Discovery Phase 2 - Platform Workspace Map

Status: `[x] complete at route/controller/shell level`

### Goal

Map every Platform workspace, section, controller, presenter, table source,
detail shell, and dialog host before implementation begins.

### Mandatory inspection scope

Inspect:

- `src/ui_qml/platform/**`
- `src/ui_qml/modules/platform/**`
- `src/ui_qml/shared/**`

For each Platform workspace, identify:

- current QML file
- current controller
- current presenter / view-model
- current table source
- current actions
- current detail panel or side panel
- current dialogs
- current `InlineMessage` usage
- current `DataTable` usage
- current `TableToolbar` usage
- current lazy loading, if any
- missing `SectionDetailPage` usage
- duplicate actions or buttons
- shared reusable components that can be adopted

### Deliverable

- [x] Platform workspace map added to this document

Coverage note:

- route-level mapping is complete
- controller/presenter/shell mapping is complete
- list/detail gap analysis is complete
- deeper per-entity section behavior now moves into implementation work for the
  active pilot slice instead of blocking discovery closure

### Platform Workspace Map

#### Route-level Platform surfaces

The live Platform route map is:

- `platform.admin` -> `AdminWorkspace.qml`
- `platform.control` -> `ControlWorkspace.qml`
- `platform.settings` -> `SettingsWorkspace.qml`

These are backed by `PlatformWorkspaceCatalog` in
`src/ui_qml/platform/context.py`.

#### Controller and presenter map

##### Admin Console

Top-level controller:

- `PlatformAdminWorkspaceController`

Child controllers:

- `PlatformOrganizationController`
- `PlatformSiteController`
- `PlatformDepartmentController`
- `PlatformEmployeeController`
- `PlatformUserController`
- `PlatformPartyController`
- `PlatformDocumentController`
- `PlatformDocumentStructureController`

Primary presenters:

- `PlatformAdminWorkspacePresenter`
- `PlatformOrganizationCatalogPresenter`
- `PlatformSiteCatalogPresenter`
- `PlatformDepartmentCatalogPresenter`
- `PlatformEmployeeCatalogPresenter`
- `PlatformUserCatalogPresenter`
- `PlatformPartyCatalogPresenter`
- `PlatformDocumentCatalogPresenter`
- `PlatformDocumentManagementPresenter`

Current QML shell:

- `AdminConsolePage.qml`
- `AdminEntityWorkspace.qml`
- `AdminOverviewSections.qml`
- `AdminDocumentSection.qml`
- `AdminAuditSection.qml`
- `AdminSupportSection.qml`
- `AdminDialogHost.qml`

Current section map seen in the shell:

- organizations
- sites
- departments
- employees
- users
- parties
- documents
- structures
- access
- support

Current table source:

- already uses Python-owned table models through `sourceModel`

Current list-shell alignment:

- good partial alignment through `AdminEntityWorkspace`
- already uses:
  - `TableToolbar`
  - `DataTable`
  - `InlineMessage`
  - `TablePaginationBar`

Current detail behavior:

- detail opens inside the same workspace as a right-side inspector/state panel
- no `SectionDetailPage`
- no PM-style stacked list page -> detail page transition
- no section-aware top toolbar actions in the PM sense

Current lazy loading:

- dialog host is lazy-loaded
- entity catalogs are refreshed eagerly in `PlatformAdminWorkspaceController.refresh()`
- no PM-style lazy detail section loading

Primary gap:

- Admin Console is the closest Platform area to the PM list shell, but still
  lacks the PM detail architecture

##### Control Center

Top-level controller:

- `PlatformControlWorkspaceController`

Primary presenters:

- `PlatformControlWorkspacePresenter`
- `PlatformControlQueuePresenter`

Current QML shell:

- `ControlWorkspacePage.qml`
- `ApprovalQueueSection.qml`
- `AuditFeedSection.qml`
- `ControlMetricsSection.qml`

Current panel map:

- approvals
- audit
- escalations
- system events

Current list-shell alignment:

- uses `KpiStrip`
- uses `InlineMessage`
- approvals use `TableToolbar`, `DataTable`, `TablePaginationBar`
- audit and system panels are panel-based rather than full list/detail pages

Current detail behavior:

- approvals currently use a selected-row right-side inspector / decision flow
- no `SectionDetailPage`
- no PM-style stacked detail page

Current lazy loading:

- none in the PM sense
- queue and audit feed are both refreshed on controller refresh

Primary gap:

- panel navigation already exists, but detail architecture is still inspector-
  based rather than PM list/detail/page-based

##### Settings

Top-level controller:

- `PlatformSettingsWorkspaceController`

Primary presenters:

- `PlatformSettingsWorkspacePresenter`
- `PlatformSettingsCatalogPresenter`

Current QML shell:

- `SettingsWorkspacePage.qml`
- `ModuleEntitlementsSection.qml`
- `OrganizationProfileSection.qml`
- `SettingsRuntimeSection.qml`
- `SettingsOverviewSection.qml`
- `SettingsMetricsSection.qml`

Current section map seen in the shell:

- runtime
- modules
- defaults
- integrations
- security
- sysinfo

Current list-shell alignment:

- uses `KpiStrip`
- uses `InlineMessage`
- module entitlements and capability lists already use table-like shared UI
- some contextual actions already exist

Current detail behavior:

- modules and integration capability areas still behave like split panels and
  contextual inspectors
- no `SectionDetailPage`
- no PM-style row activation -> full detail page flow

Current lazy loading:

- none in the PM sense
- controller refresh eagerly rebuilds modules, org profiles, and integration
  capabilities together

Primary gap:

- Settings already has strong panel organization, but not the PM detail shell
  model or section-aware detail actions

#### Initial workspace gap summary

- `SectionDetailPage` usage in Platform: not present
- `ContextualActionToolbar` usage in Platform: present, but not yet aligned to
  PM-style section-aware detail actions
- `DataTable` usage in Platform: present in list shells, especially Admin and
  Approvals
- `InlineMessage` usage in Platform: present across all three top-level routes
- lazy detail loading in Platform: largely absent
- source-model table direction in Platform: already stronger than parts of PM

#### Implementation implication

Platform does not need a new table system. The main migration gap is the
detail-page architecture:

- move from inspector/split-panel detail behavior
- to PM-style stacked list page -> lazy-loaded `SectionDetailPage`

### Reusable Components Found

Status: `[x] complete`

Confirmed reusable shared components already used by Platform:

- `AppWidgets.DataTable`
- `AppWidgets.TableToolbar`
- `AppWidgets.TablePaginationBar`
- `AppWidgets.KpiStrip`
- `AppWidgets.InlineMessage`
- `AppWidgets.ContextualActionToolbar`
- `AppControls.ConfirmationDialog`
- `Theme.AppTheme`
- `DynamicTableModel`

Confirmed reusable PM patterns available to adopt:

- `AppWidgets.SectionDetailPage`
- `AppWidgets.LazyObjectLoader`
- `AppWidgets.LazySectionLoader`
- PM dialog-host pattern
- PM stacked list/detail page pattern

Shared-component gap to resolve before implementation:

- verify whether `ContextualActionToolbar` needs a small shared enhancement for
  cleaner section-aware actions in Platform
- decide whether Platform needs a thin reusable detail-host wrapper around
  `SectionDetailPage` or should embed `SectionDetailPage` directly per workspace

## Active Follow-Up Status

Status: `[~] in progress`

The discovery phase is now complete enough to begin execution under this plan.

Current active handoff:

1. use the PM `tasks` detail flow as the strongest reference for:
   - stacked list/detail loading
   - `SectionDetailPage`
   - lazy section loading
   - active-section-aware toolbar actions
2. use `platform.admin -> organizations` as the first migration slice
3. keep `AdminEntityWorkspace` as the list-shell bridge where possible
4. add Platform detail architecture without creating a second widget system

## Platform Workspace Backlog

### Admin Console

Status: `[~] organizations pilot in progress`

#### Organizations

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list page to PM-aligned shell
- [x] add row activation -> `SectionDetailPage`
- [ ] add sections:
  - [x] Overview
  - [x] Sites
  - [x] Departments
  - [x] Users
  - [x] Parties
  - [x] Documents
  - [x] Module Entitlements
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading for related sections
- [x] normalize detail-section layout so active content starts at top and inactive lazy sections do not reserve vertical space
- [x] split organization catch-all detail into dedicated admin entity detail pages
- [~] add RBAC and entitlement-driven section visibility

#### Sites

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list/detail flow
- [x] add sections:
  - [x] Overview
  - [x] Departments
  - [x] Structures
  - [x] Warehouses when Inventory is enabled
  - [x] Projects when PM is enabled
  - [x] Assets when Maintenance is enabled
  - [x] Documents
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading
- [x] add module-gated section visibility

Implementation note:

- `Sites` now uses a dedicated `AdminSiteDetailPage.qml` with top-anchored
  sections, filtered department rows, and module-gated PM / Inventory /
  Maintenance integration guidance instead of overloading the organization page.

#### Departments

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list/detail flow
- [x] add sections:
  - [x] Overview
  - [x] Employees
  - [x] Users
  - [x] Projects when PM is enabled
  - [x] Warehouses when Inventory is enabled
  - [x] Documents
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading

Implementation note:

- `Departments` now uses a dedicated `AdminDepartmentDetailPage.qml` with
  filtered employee rows, section-aware actions, and module-boundary guidance
  for linked PM / Inventory / identity workflows.

#### Employees

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list/detail flow
- [x] add sections:
  - [x] Overview
  - [x] User Account
  - [x] Assignments
  - [x] Timesheets when PM is enabled
  - [x] Certifications when present
  - [x] Documents
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading

Implementation note:

- `Employees` now uses a dedicated `AdminEmployeeDetailPage.qml` with
  employment summary, identity boundary guidance, and PM-routed actions for
  assignments, timesheets, and certifications instead of relying on the
  generic transitional detail shell.

#### Users

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list/detail flow
- [x] add sections:
  - [x] Overview
  - [x] Roles & Access
  - [x] Sessions
  - [x] Module Access
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading

Implementation note:

- `Users` now uses a dedicated `AdminUserDetailPage.qml` with identity
  overview, access-governance guidance, session posture notes, and
  organization-level module entitlement visibility sourced from the existing
  settings controller instead of duplicating runtime module state in Admin.

#### Parties

- [x] map current workspace/controller/presenter/dialogs
- [x] migrate list/detail flow
- [x] add sections:
  - [x] Overview
  - [x] Contacts
  - [x] Supplier Profile when Procurement is enabled
  - [x] Customer / Client Profile
  - [x] Linked Projects when PM is enabled
  - [x] Linked Procurement when Procurement is enabled
  - [x] Documents
  - [x] Audit
- [x] implement section-aware actions
- [x] add lazy loading

Implementation note:

- `Parties` now uses a dedicated `AdminPartyDetailPage.qml` with contact and
  commercial-profile sections, plus module-gated PM / Procurement linkage
  actions routed through the shared shell model instead of duplicating
  downstream business records inside Platform Admin.

#### Documents

- [ ] map current workspace/controller/presenter/dialogs
- [ ] migrate list/detail flow
- [ ] add sections:
  - [ ] Overview
  - [ ] Revisions
  - [ ] Linked Entities
  - [ ] Approvals
  - [ ] Access
  - [ ] Audit
- [ ] implement section-aware actions
- [ ] add lazy loading

#### Structures

- [ ] map current workspace/controller/presenter/dialogs
- [ ] migrate list/detail flow
- [ ] add sections:
  - [ ] Overview
  - [ ] Child Structures
  - [ ] Linked Locations when Inventory is enabled
  - [ ] Linked Assets when Maintenance is enabled
  - [ ] Linked Projects when PM is enabled
  - [ ] Documents
  - [ ] Audit
- [ ] implement section-aware actions
- [ ] add lazy loading

#### Roles & Access

- [ ] map current workspace/controller/presenter/dialogs
- [ ] migrate list/detail flow
- [ ] add sections:
  - [ ] Overview
  - [ ] Permissions
  - [ ] Scope
  - [ ] Users
  - [ ] Sessions
  - [ ] Audit
- [ ] implement section-aware actions
- [ ] add lazy loading

### Control Center

Status: `[ ] not started`

- [ ] map current panel and detail architecture
- [ ] align top-level navigation:
  - [ ] Approvals
  - [ ] Audit
  - [ ] Escalations
  - [ ] System Events

#### Approvals

- [ ] align list page with PM table shell
- [ ] add row activation -> detail page
- [ ] add sections:
  - [ ] Overview
  - [ ] Request Payload
  - [ ] Source Reference
  - [ ] Decision History
  - [ ] Audit
- [ ] limit overview actions to `Approve`, `Reject`, `Delegate`

#### Audit

- [ ] align list page with PM table/feed shell
- [ ] add row activation -> detail page when supported
- [ ] add sections:
  - [ ] Overview
  - [ ] Actor
  - [ ] Entity
  - [ ] Payload
  - [ ] Related Events
- [ ] implement section-aware actions such as `Export Event` and `Open Source`

#### Escalations / System Events

- [ ] map current runtime sources
- [ ] decide `DataTable` vs `ActivityFeed`
- [ ] add detail handling if entity identity exists
- [ ] add lazy loading and message states

### Settings

Status: `[ ] not started`

- [ ] map current section architecture
- [ ] align settings pages to list/detail or panel/detail where appropriate

#### Runtime

- [ ] align shell, detail flow, and lazy loading

#### Module Entitlements

- [ ] align list/detail flow
- [ ] add sections:
  - [ ] Overview
  - [ ] Capabilities
  - [ ] Consumers
  - [ ] Audit
- [ ] implement overview-only actions

#### Integration Capabilities

- [ ] align list/detail flow
- [ ] add sections:
  - [ ] Overview
  - [ ] Provider Module
  - [ ] Consumer Modules
  - [ ] Usage
  - [ ] Audit

#### Security

- [ ] align section shell with shared patterns
- [ ] identify which areas are list/detail and which remain structured detail pages

#### Support

- [ ] align diagnostics/runtime/support events with shared list/feed/detail patterns

## Shared Reusable Component Work

Status: `[ ] not started`

- [ ] verify whether `ContextualActionToolbar` already supports clean
  section-aware action switching
- [ ] update `ContextualActionToolbar` if needed instead of adding local action bars
- [ ] verify `SectionDetailPage` expectations for Platform entities
- [ ] verify `DataTable` source-model support in Platform controllers
- [ ] verify `InlineMessage` placement rules for list and detail pages
- [ ] verify `BulkActionBar` and `BulkChangePropertyPopup` usage for Platform entities

## Lazy Loading Rules

Status: `[ ] not started`

Required behavior:

- [ ] load overview immediately
- [ ] load related sections only when opened
- [ ] load documents only when `Documents` opens
- [ ] load audit only when `Audit` opens
- [ ] load linked module records only when their section opens
- [ ] do not load every detail section when a list row is selected

## RBAC and Entitlement Rules

Status: `[ ] not started`

- [ ] hide sections when the user lacks permission
- [ ] hide module-linked sections when the module is disabled
- [ ] avoid permission-denied placeholders for sections that should be absent
- [ ] verify action visibility follows RBAC as well as section context

Examples:

- [ ] hide `Warehouses` when Inventory is disabled
- [ ] hide `Projects` when PM is disabled
- [ ] hide `Assets` when Maintenance is disabled
- [ ] hide `Audit` when audit-read permission is absent

## Data Table Architecture Follow-Up

Status: `[ ] not started`

- [ ] inventory all Platform tables still bound through raw `rows: ...items`
- [ ] identify which Platform tables should migrate to `sourceModel`
- [ ] avoid large QML-side row mapping, filtering, or sorting
- [ ] align Platform tables with the shared `DynamicTableModel` direction

## Validation Checklist

Status: `[ ] not started`

Run:

- [ ] `python main_qt.py`

Validate:

- [ ] Admin Console loads
- [ ] each Platform entity list works
- [ ] row activation opens `SectionDetailPage`
- [ ] list page hides when detail opens
- [ ] `TableToolbar` is not shown above the detail page
- [ ] entity-level actions show only on `Overview`
- [ ] section-specific actions show only in relevant sections
- [ ] lazy loading works
- [ ] `InlineMessage` appears on both list and detail pages
- [ ] RBAC hides unauthorized sections and actions
- [ ] module entitlement hides disabled-module sections
- [ ] no QML warnings or layout warnings
- [ ] no duplicate buttons
- [ ] no broken dialogs

## Risks

Status: `[ ] open`

- [ ] Platform workspace implementations may currently vary more than PM, so the
  discovery map must happen before QML edits
- [ ] some Platform areas may still use custom or transitional detail surfaces
- [ ] entitlement-driven sections can create action/section mismatches if
  action filtering is implemented locally instead of centrally
- [ ] moving tables toward `sourceModel` may require controller/presenter changes
  rather than QML-only alignment
- [ ] Control Center and Settings may need panel/detail hybrids instead of
  literal CRUD entity clones

## First Safe Implementation Slice

Status: `[x] identified`

Recommended first implementation slice after discovery closes:

- `platform.admin` -> `Organizations`

Why this is the safest first slice:

- Admin already uses `AdminEntityWorkspace`, which is close to the PM list shell
- Admin already uses `sourceModel` table data, so table migration risk is lower
- Organizations already have dedicated controller, presenter, editor options,
  dialog host wiring, and domain refresh support
- the main missing work is the detail architecture rather than data plumbing
- it provides the clearest pilot for:
  - stacked list page hiding
  - `SectionDetailPage`
  - section-aware overview vs section actions
  - lazy-loading related sections

Follow-on slices after Organizations:

1. Sites
2. Departments
3. Employees / Users
4. Control Center approvals
5. Settings module entitlements and integration capabilities

## Required Deliverables

### Before implementation

- [x] PM pattern discovery report
- [x] Platform workspace map
- [x] reusable component inventory
- [ ] Platform workspace migration plan
- [x] risk log

### After implementation

- [ ] files changed summary
- [ ] workspaces migrated summary
- [ ] detail pages added or updated
- [ ] section-aware actions summary
- [ ] lazy loading summary
- [ ] RBAC / entitlement visibility summary
- [ ] validation result

## Recommended Execution Order

1. `[x]` complete PM pattern discovery
2. `[x]` complete Platform workspace map
3. `[x]` confirm reusable shared components and any required shared upgrades
4. `[ ]` migrate Admin Console entities
5. `[ ]` migrate Control Center panels
6. `[ ]` migrate Settings sections
7. `[ ]` harden lazy loading, RBAC, and entitlement visibility
8. `[ ]` validate end-to-end runtime and QML behavior
