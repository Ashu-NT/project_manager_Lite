You have access to my existing repository. I want you to improve the enterprise UI/UX of my PySide6/QML desktop platform.

IMPORTANT:
- You already have access to the full repository/codebase.
- You MUST follow the existing repo architecture and conventions.
- Do NOT invent a new architecture.
- Do NOT replace the controller/presenter/API structure.
- Do NOT introduce random frameworks.
- Respect the existing:
  - QML module structure
  - controller layer
  - presenter layer
  - desktop API layer
  - typed workspace state patterns
  - route registry patterns
  - theme system
  - dialog host structure
  - workspace controller structure
  - existing import namespaces

The goal is to transform the current UI into a polished enterprise-grade ERP/EAM desktop experience while preserving the current backend architecture.


APPLICATION OVERVIEW


The platform contains multiple enterprise modules:

- Platform (shared services)
- Project Management
- Maintenance
- Inventory & Procurement

There are also shared enterprise capabilities:
- approvals
- access control
- workflow
- notifications
- documents
- shared master data
- platform services

The application is a large operational desktop platform.


DESIGN INSPIRATION


The UI should feel similar to:
- SAP Fiori
- IBM Maximo
- Microsoft Dynamics
- ServiceNow
- Jira Enterprise
- Odoo Enterprise
- industrial ERP/EAM systems

NOT:
- startup dashboards
- flashy UI
- consumer UI
- mobile-first UI
- giant card-only layouts
- heavy animations


ENTERPRISE APPLICATION LAYOUT VISION


The app should visually be partitioned into 4 major areas:

--------------------------------------------------------
1. TOP APPLICATION HEADER
--------------------------------------------------------

Purpose:
- global application identity
- workspace title
- global search
- approvals
- notifications
- user profile/session

Characteristics:
- fixed height
- subtle separation
- minimal borders
- always visible
- compact enterprise density

--------------------------------------------------------
2. LEFT NAVIGATION SIDEBAR
--------------------------------------------------------

Purpose:
- module navigation
- workspace switching

Structure:
- grouped by module
- collapsible groups optional
- selected route highlighted
- professional iconography
- flat navigation style

Groups:
- Platform
- Project Management
- Maintenance
- Inventory & Procurement

Characteristics:
- fixed width
- slightly darker surface
- subtle hover states
- selected item accent
- no giant boxed buttons

--------------------------------------------------------
3. MAIN WORKSPACE CONTENT AREA
--------------------------------------------------------

Purpose:
- operational workflows
- data management
- dashboards
- planning
- review flows

Each workspace should generally contain:

A. Workspace Header
- title
- subtitle
- actions

B. Toolbar / Filters
- search
- filters
- quick actions
- export/refresh

C. Main Data Area
Patterns:
- master-detail
- queue-review
- dashboard
- table-detail
- workflow board

D. Supporting Information
- metrics
- forecasts
- history
- analytics
- related records

--------------------------------------------------------
4. DETAIL / CONTEXT AREA
--------------------------------------------------------

Can be:
- right-side detail panel
- lower detail section
- slide-over panel
- dialog

Purpose:
- entity detail
- editing
- related data
- workflow actions


VISUAL DESIGN RULES


The application must prioritize:
- information density
- clarity
- operational efficiency
- alignment consistency
- reusable workspace patterns

Use:
- whitespace
- subtle surfaces
- typography hierarchy
- spacing rhythm
- divider lines
- soft elevation

Avoid:
- excessive borders
- too many rectangles
- nested cards everywhere
- random spacing
- oversized mobile spacing
- visually noisy layouts


DENSITY MODES


The application should support enterprise density modes.

Target modes:
- Compact (default)
- Comfortable
- Spacious (optional)

Compact mode should prioritize:
- more visible rows
- reduced vertical padding
- operational efficiency
- large dataset scanning

Density should affect:
- row height
- toolbar spacing
- form spacing
- section spacing
- sidebar spacing
- dialog spacing

Avoid mobile-sized spacing in compact mode.

Preferred compact row heights:
- tables: 28–36px
- toolbars: 36–44px
- sidebar rows: 32–40px

If settings infrastructure already exists:
- persist density preference globally.

Theme may expose:
- densityMode
- compactRowHeight
- normalRowHeight
- toolbarHeight
- sidebarRowHeight


SURFACE HIERARCHY RULES


Use visual hierarchy intentionally.

Preferred hierarchy:
- app background
- workspace surface
- raised surface
- selected surface
- dialog/modal surface

Do not use the same visual treatment everywhere.

Prefer:
- subtle surface elevation
- restrained contrast
- whitespace grouping
- divider rhythm

Avoid:
- identical white rectangles everywhere
- deep nested card structures
- visually heavy containers

Use:
- surface contrast first
- borders second
- shadows minimally


BORDER RULES


Do NOT put borders around everything.

Use borders only where useful:
- inputs
- tables
- selected records
- dialogs
- important panels

Prefer:
- spacing
- alignment
- surface contrast
- subtle shadows
- separators

Do not invent a new app architecture. Work with the existing codebase.

The main goal is to make the platform look and feel like a professional enterprise operations system similar to SAP Fiori, IBM Maximo, ServiceNow, Jira, Microsoft Dynamics, or Odoo Enterprise.

The current problem:
- The QML UI looks too boxed.
- There are too many nested borders, rectangles, and card outlines.
- The layout feels developer-built instead of product-designed.
- I need a clean enterprise UI/UX system applied across Platform, Project Management, Maintenance, and Inventory & Procurement modules.

High-level architecture:
- Final desktop UI lives in src/ui_qml/*
- QML renders state and forwards user intent only.
- Python workspace controllers/catalogs own refresh, loading, busy, error, feedback, selection, mutation orchestration, and domain-event refresh wiring.
- Presenters map desktop API DTOs into QML-safe view models.
- Desktop APIs sit behind module/platform boundaries.
- Do not let QML call repositories, SQLAlchemy, infrastructure, or domain services directly.
- QML must use existing named modules and aliases, not deep relative imports.

Allowed to modify:
- QML files
- shared QML components
- theme tokens
- QML widgets/layouts/dialogs
- QML controllers if required
- presenters if required
- view models if required
- desktop API adapters if a missing UI capability needs a clean existing-boundary extension

Allowed only if necessary:
- Add small missing fields to presenter/view-model state
- Add small controller methods for UI orchestration
- Add desktop API read methods if the UI needs data already available from application services
- Add desktop API command methods only when there is already a clear application use case/service behind it

Not allowed:
- Do not invent new business workflows that do not exist.
- Do not add fake data.
- Do not bypass existing APIs.
- Do not call repositories directly from UI/presenter/controller.
- Do not add SQLAlchemy or persistence imports in ui_qml.
- Do not add business rules in QML JavaScript.
- Do not move backend architecture.
- Do not create a new frontend framework.
- Do not use web technologies.
- Do not introduce QWidget final-state UI.
- Do not use deep relative QML imports such as ../../../../.
- Do not break existing routes, public QML properties, signals, or controller method calls unless fixing a real bug.

Repository conventions to preserve:
- Shared reusable QML: src/ui_qml/shared/qml/App/*
- Shared theme: App.Theme
- Shared controls: App.Controls
- Shared widgets: App.Widgets
- Shared layouts: App.Layouts
- Platform QML: src/ui_qml/platform/*
- Project Management QML: src/ui_qml/modules/project_management/*
- Maintenance QML: src/ui_qml/modules/maintenance/*
- Inventory & Procurement QML: src/ui_qml/modules/inventory_procurement/*
- Controllers are exposed through named QML controller modules.
- Workspaces are loaded through the shell route/loader system.
- Keep current route registry and module boundaries.

Important style setup:
- If custom Button background/contentItem warnings exist, configure the app to use a customizable Qt Quick Controls style such as Basic, Fusion, or Material.
- Prefer Basic if the app has a custom design system.
- Do not rely on native control styling if custom contentItem/background is used.

Design direction:
Create a unified enterprise platform UI.

Global shell should feel like:
- Stable top header
- Left navigation drawer
- Main workspace content area
- Module grouped navigation
- Clean user/profile area
- Notification/approval indicator area
- Optional global search placeholder if already supported or easy to add cleanly
- No heavy nested borders around everything

Visual principles:
- Use surface hierarchy instead of many borders.
- Parent layout containers should usually have no visible border.
- Cards should have at most one subtle border or light elevation.
- Do not put bordered cards inside bordered cards inside bordered cards.
- Navigation items should be flat, not button-like.
- Only selected navigation items should have strong accent indication.
- Use whitespace, headings, dividers, and background contrast for grouping.
- Inputs can keep borders.
- Focused/selected items can use accent border or accent background.
- Avoid making every Rectangle visible.
- Use fewer large rounded containers.
- Prefer predictable, dense layouts for enterprise users.

Theme work:
Audit and improve the existing App.Theme singleton instead of inventing a new theme system.

Keep existing tokens working, but add useful tokens if needed:
- appBackground
- surface
- surfaceAlt
- surfaceRaised
- surfaceSunken
- hoverSurface
- selectedSurface
- subtleBorder
- divider
- focusBorder
- navBackground
- navHoverBackground
- navSelectedBackground
- navSelectedText
- accent
- accentHover
- accentPressed
- accentSoft
- success
- warning
- danger
- info
- textPrimary
- textSecondary
- textMuted
- textOnAccent
- spacingXs
- spacingSm
- spacingMd
- spacingLg
- spacingXl
- marginSm
- marginMd
- marginLg
- marginXl
- radiusSm
- radiusMd
- radiusLg
- bodySize
- smallSize
- titleSize
- headerSize
- sectionTitleSize

Do not hardcode colors in feature QML unless absolutely unavoidable.
Use Theme.AppTheme tokens.

Global shell design:
Update the existing shell QML files without replacing routing:
- App.qml
- MainWindow.qml
- ShellHeader.qml
- ShellDrawer.qml
- HomeWorkspace.qml if relevant

Desired shell layout:
1. Top header
   - App name/product identity on left
   - Current workspace/module context if already available
   - Search placeholder or compact search field if feasible
   - Notification/approval area if available
   - User/profile/menu area if available
   - Clean height, no heavy border box

2. Sidebar/drawer
   - Group navigation by module/group label
   - Use flat rows
   - Selected row has accent left rail or soft accent background
   - Hover row uses subtle surface
   - Avoid bordered buttons for each nav item
   - Keep module labels as small uppercase/muted section headers
   - Support existing route model and selected route state

3. Workspace content
   - Use app background around content
   - WorkspaceFrame should provide title/subtitle and content padding
   - Do not wrap workspace in multiple bordered rectangles
   - Use subtle page header and clear content sections


DESKTOP RESPONSIVE BEHAVIOR


The application is desktop-first, not mobile-first.

Layouts should gracefully adapt to:
- laptops
- ultrawide monitors
- split-screen usage
- medium desktop resolutions

Preferred behavior:
- preserve table visibility
- collapse secondary panels first
- reduce spacing before stacking
- avoid mobile-card transformations

Prefer:
- SplitView
- resizable panels
- adaptive master-detail layouts

Avoid:
- giant fixed-width centered layouts
- unnecessary full-width forms


Navigation groups:
- Platform
  - Admin Console
  - Access & Security
  - Approvals
  - Audit
  - Settings
- Project Management
  - Dashboard
  - Projects
  - Tasks
  - Scheduling
  - Resources
  - Financials
  - Risk
  - Portfolio
  - Register
  - Collaboration
  - Timesheets
- Maintenance
  - Dashboard
  - Assets
  - Work Requests
  - Work Orders
  - Preventive
  - Reliability
  - Task Templates
- Inventory & Procurement
  - Dashboard
  - Catalog
  - Inventory
  - Reservations
  - Procurement
  - Pricing


ICONOGRAPHY SYSTEM


Use a unified enterprise icon system across the application.

Icons should:
- be simple
- restrained
- operational
- recognizable
- monochrome or lightly tinted

Preferred:
- outline icons
- compact icon sizes
- flat navigation icons
- contextual action icons

Typical actions:
- add
- edit
- delete
- refresh
- export
- import
- approve
- reject
- filter
- search
- notifications
- settings
- workflow
- history
- comments
- attachments

Avoid:
- decorative icons
- colorful illustrations
- oversized iconography
- inconsistent icon styles

Standard workspace patterns:
Apply these patterns across modules where compatible with existing data.

A. Dashboard workspace
Use for module dashboards.
Layout:
- Header title/subtitle
- KPI metric row
- Two-column insights area
- Alerts/recent activity/upcoming items sections
- Charts only if existing chart data exists
- Empty states if no data

B. Master-detail CRUD workspace
Use for Projects, Assets, Items, Users, Work Orders, Purchase Orders.
Layout:
- Page header + primary action
- Filter/search toolbar
- Left list/table/card area
- Right detail panel
- Related records below
- Edit/Create through existing dialogs
- Selected item state clearly visible

C. Queue/review workspace
Use for Approvals, Work Requests, Preventive Queue, Reservations.
Layout:
- Filter toolbar at top
- Queue list on left
- Selected request/detail panel on right
- Primary decision/actions clearly visible
- Activity/audit/forecast/results below when available

D. Board/workflow workspace
Use for Tasks, Work Orders, procurement pipeline where existing data supports it.
Layout:
- Toolbar filters
- Status columns or grouped records if already available
- Detail drawer/panel for selected item
- Do not invent kanban data if not available

E. Settings/admin workspace
Use for Platform Settings, Module Entitlements, Access Control.
Layout:
- Left category list or tabs
- Right configuration panel
- Clear form sections
- Save/apply actions in header/footer
- Subtle dividers, not heavy boxes


ENTERPRISE PANEL BEHAVIOR


Workspaces should support operational desktop workflows.

Preferred capabilities:
- resizable split panels
- adjustable sidebars
- collapsible detail sections
- persistent splitter sizes if feasible

Use SplitView where appropriate.

Master-detail layouts should allow users to:
- maximize table space
- resize detail panels
- preserve operational context

Avoid rigid fixed-width operational layouts.


ENTERPRISE FORM UX


Forms should follow a unified enterprise form system.

Use:
- aligned layouts
- predictable field widths
- grouped sections
- compact spacing
- inline validation
- keyboard-first navigation

Preferred patterns:
- label above field for compact dialogs
- aligned multi-column layouts for large forms
- grouped sections with subtle dividers

Avoid:
- inconsistent field alignment
- oversized spacing
- giant modal forms
- random widths

Dialogs should support:
- Enter to submit where safe
- Escape to cancel
- visible validation states
- correct tab order

Module-specific UI design:


ENTERPRISE TABLE / DATA GRID UX


This application is heavily data-driven.

The PRIMARY interaction pattern across most modules should be:
- enterprise tables
- operational data grids
- queue processing
- master-detail workflows
- dense record management

NOT:
- oversized cards
- mobile-style list layouts
- dashboard-only views
- cardified enterprise records

Most modules in this repository require table/grid-first workflows.

Examples include:
- projects
- tasks
- schedules
- resources
- financial records
- risks/registers
- approvals
- work requests
- work orders
- preventive plans
- preventive task templates
- assets
- inventory balances
- transactions
- reservations
- requisitions
- purchase orders
- supplier pricing
- audit records
- users/roles/scopes
- documents


BULK OPERATIONS UX


Enterprise tables should support multi-selection where workflows require it.

Examples:
- approve many records
- close many work orders
- assign multiple tasks
- export selected rows
- perform batch inventory operations

Preferred UX:
- checkbox selection column
- selected count indicator
- contextual bulk action toolbar

Bulk actions must always use existing controller/API boundaries.


TABLE DESIGN REQUIREMENTS


Enterprise tables should support:
- compact density
- row selection
- row highlighting
- sorting
- filtering
- multi-column display
- sticky headers where useful
- keyboard navigation
- contextual row actions
- batch operations
- status indicators
- virtualization/pagination if required

Tables should feel:
- operational
- efficient
- stable
- information-dense
- readable


MASTER-DETAIL TABLE WORKFLOW


Preferred layout patterns:

A.
[List/Table] | [Detail Panel]

OR

B.
[Table]
[Detail Section Below]

Selecting a row should:
- update detail state
- preserve workspace context
- avoid excessive dialogs
- keep the user in-flow


TABLE TOOLBAR PATTERN


Most enterprise tables should contain:

[Search]
[Filters]
[Refresh]
[Export]
[Bulk Actions]
[Create/New]

Toolbar placement and behavior should remain visually consistent across modules.


KEYBOARD-FIRST ENTERPRISE UX


The application should support enterprise keyboard workflows.

Important interactions:
- arrow navigation in tables
- tab navigation across forms
- enter to confirm/search
- escape to close dialogs
- keyboard focus visibility
- quick filtering/search
- efficient data entry flows

The UI should feel optimized for:
- planners
- operators
- procurement users
- coordinators
- maintenance supervisors
- administrators


ENTERPRISE SEARCH UX


Search and filtering should feel operational and efficient.

Use:
- debounced search where appropriate
- quick filters
- filter persistence if infrastructure exists
- consistent toolbar search placement

Search interactions should:
- preserve table state
- preserve selection where feasible
- avoid unnecessary full reloads


VISUAL TABLE RULES


Use:
- subtle row dividers
- hover states
- restrained status colors
- aligned columns
- compact row height
- clear typography hierarchy

Avoid:
- giant row spacing
- heavy borders everywhere
- oversized cards replacing tables
- visually noisy grids


TABLE PERFORMANCE RULES


Large enterprise datasets must remain responsive.

Avoid:
- large nested Repeaters
- excessive delegates
- unnecessary bindings
- recreating models repeatedly
- heavy row animations

Prefer:
- TableView virtualization
- lazy loading
- efficient delegates
- stable bindings
- lightweight reusable components

Operational tables should support large record counts smoothly.


QML TABLE IMPLEMENTATION


Evaluate existing components such as:
- RecordListCard
- catalog panels
- queue lists
- list/detail sections

Where appropriate, refactor toward reusable enterprise:
- DataTable
- DataGrid
- MasterDetailTable
- QueueTable
- EntityTable

while preserving:
- controller contracts
- presenter state contracts
- workspace APIs
- route architecture

If presenter state is currently card-oriented only:
- extend presenter/view-model state cleanly
- expose table columns/rows through presenters
- do NOT compute business logic in QML


TARGET EXPERIENCE


The final UX should feel like:
- SAP operational tables
- Maximo planning screens
- Dynamics inventory grids
- ServiceNow admin queues
- Jira enterprise management tables

Users should be able to:
- scan large datasets quickly
- process queues efficiently
- edit records rapidly
- keep context while navigating
- work primarily through tables and detail panels


CUSTOMIZABLE TABLE COLUMNS


Enterprise tables must support user-customizable columns.

Each major table/grid should have a "Customize Columns" button in the table toolbar.

The user should be able to:
- show/hide columns
- reorder columns if feasible
- reset to default columns
- save column preferences per workspace/table
- keep preferences between app sessions if existing settings/QSettings infrastructure supports it

Column customization should be implemented as a reusable shared QML pattern, not duplicated per module.

Suggested component:
- App.Widgets/DataTable.qml
- App.Dialogs/ColumnChooserDialog.qml or App.Widgets/ColumnCustomizer.qml

The table model should support:
- availableColumns
- visibleColumns
- defaultColumns
- rows
- selectedRowId
- sortKey
- sortDirection

Column metadata should include:
- key
- label
- width/defaultWidth
- alignment
- visibleByDefault
- sortable
- sensitive
- technical
- formatter/type if needed

Example column metadata:
[
  { "key": "code", "label": "Code", "visibleByDefault": true, "sortable": true },
  { "key": "name", "label": "Name", "visibleByDefault": true, "sortable": true },
  { "key": "statusLabel", "label": "Status", "visibleByDefault": true, "sortable": true },
  { "key": "createdAtLabel", "label": "Created", "visibleByDefault": false, "sortable": true }
]


COLUMN SELECTION RULES


Codex may inspect existing database models, DTOs, desktop API models, presenters, and view models to understand useful fields.

However, do NOT expose raw database columns directly to QML.

The table should expose client-friendly presenter/view-model fields only.

Do NOT show technical/internal fields by default:
- id
- uuid
- foreign keys
- database primary keys
- internal version numbers
- deleted flags
- audit metadata not useful to users
- internal tenant/org IDs
- password hashes
- tokens
- secrets
- internal permission IDs
- raw JSON blobs
- raw enum codes without labels
- system-only timestamps unless useful

IDs may still be used internally for row selection/actions, but should not appear as visible columns unless there is a clear user-facing reason.

Example:
Use internally:
- projectId
- planId
- workOrderId

Show to user:
- Project Code
- Project Name
- Status
- Owner
- Due Date
- Priority


SAFE COLUMN DISCOVERY


When deciding table columns:
1. Prefer existing presenter/view-model fields.
2. Then check desktop API DTOs.
3. Then check application DTOs/read models.
4. Database/ORM columns may be inspected only as a reference.
5. Do not bind UI directly to ORM/database rows.

If a useful field exists only in the database but not in the presenter:
- add it cleanly through the desktop API/presenter/view-model chain
- format it into a user-facing label if needed
- do not expose raw database naming directly


DEFAULT COLUMN DESIGN


Each table should have a sensible default column set.

Default visible columns should normally include:
- business code/reference
- name/title
- status
- priority/criticality if relevant
- owner/responsible party if relevant
- date/due date if relevant
- site/location if relevant
- amount/quantity if relevant
- last activity/updated label if relevant

Optional columns can include:
- created date
- updated date
- category/type
- department/site/system
- extra operational metadata

Technical columns should remain hidden or unavailable.


TABLE PREFERENCES STORAGE


If the repo already has QSettings or user preference infrastructure:
- persist visible columns per table key
- persist column order if feasible
- persist density if added
- persist sort order if safe

Example table preference keys:
- platform.users.table
- platform.audit.table
- project_management.projects.table
- project_management.tasks.table
- maintenance.preventive.plans.table
- maintenance.work_orders.table
- inventory_procurement.items.table
- inventory_procurement.purchase_orders.table

If persistence is not already available:
- implement the UI with default columns first
- keep preference persistence as a clean future extension
- do not add heavy infrastructure just for this


TABLE CUSTOMIZATION UX


The Customize Columns action should open a small dialog/popup with:
- list of available user-facing columns
- checkboxes for visible columns
- optional drag/reorder if feasible
- "Apply"
- "Reset default"
- "Cancel"

The dialog should not expose internal technical fields.

The customization should affect only the current table/workspace.


TABLE INTERACTION UX


Enterprise tables should support:
- double-click row actions where appropriate
- context menus
- row hover states
- sticky headers if useful
- keyboard row navigation
- Enter-to-open workflows
- right-click operational actions if supported

Selection state must remain visually clear.


SECURITY AND PRIVACY


Never expose sensitive data in tables.

Do not show:
- password hashes
- tokens
- secrets
- private credentials
- internal security IDs
- raw access grants
- hidden entitlement internals
- system-only technical identifiers

For access/security screens:
- show user-facing labels such as Role, Scope, Status, Last Login
- do not show internal IDs or secret fields


1. Platform module
Admin Console:
- Should feel like an enterprise control center.
- Organize organizations, sites, departments, employees, users, parties, documents, and support operations into clear sections/tabs.
- Use master-detail panels for catalogs.
- Use compact summary metrics at top.
- Avoid many boxed cards.

Access & Security:
- Emphasize users, roles, scopes, permissions, account state.
- Use role/scope list + detail/permission matrix if existing data supports it.
- Do not add fake permissions.
- If controller/presenter lacks display-ready grouped state, add it cleanly in presenter/view model.

Approvals:
- Use queue/review layout.
- Left: pending requests.
- Right: selected request detail.
- Bottom/side: decision notes/actions.
- Approve/reject actions must use existing controller/API methods.
- Audit trail if existing API exposes it.

Audit:
- Searchable timeline/feed.
- Filters at top.
- Selected audit entry detail if existing data supports it.
- Use muted timestamp/entity metadata.

Settings:
- Configuration-panel style.
- Module entitlements/lifecycle/settings should look like admin settings, not dashboard cards.
- Use toggles/lifecycle controls only if existing API supports them.

2. Project Management module
Dashboard:
- Project health, KPIs, schedule/cost/risk summary.
- Analysis panels and alert/upcoming lists if existing presenter exposes them.
- Keep dense and executive-friendly.

Projects:
- Master-detail layout.
- Left: project list with status/health.
- Right: project detail fields/actions.
- Related sections: phases, status, metrics, documents if existing.

Tasks:
- Use task list/board style depending on existing data.
- Selected task detail should show assignments, dependencies, progress, collaboration, time entries.
- Keep action buttons near selected task context.

Scheduling:
- Toolbar with project/baseline/calendar controls.
- Sections for calendar, baseline, schedule, metrics.
- Use tabs or clear stacked panels depending on existing QML.

Resources:
- Resource catalog/list.
- Detail: capacity, allocation, active state.
- Related records below.

Financials:
- Cost items list + detail.
- Insights panels for ledger/cashflow/analytics if existing data exists.
- Keep finance data aligned and readable.

Risk/Register:
- Governance register layout.
- Filters for type/status/severity.
- Urgent/high-risk items should be visually emphasized.
- Detail panel for selected entry.

Portfolio:
- Intake, scenarios, dependencies, executive summary.
- Use section cards and clear strategic decision layout.

Timesheets:
- Entries section + review queue.
- Period/project/assignment filters.
- Approve/reject/lock actions only through existing API/controller.

3. Maintenance module
Dashboard:
- Backlog, due work, asset health, reliability KPIs.
- Use metrics and operational lists.

Assets:
- Asset hierarchy/list on left.
- Asset detail on right.
- Maintenance history, documents, reliability below if exposed.

Work Requests:
- Queue/review layout.
- Selected request detail.
- Convert/approve/reject actions if existing.

Work Orders:
- Master-detail or workflow layout.
- Show tasks, labor, materials, status, schedule.
- Use strong status badges and clear action area.

Preventive:
- Keep existing tabs: Queue, Plans, Templates.
- Queue tab:
  - filters at top
  - generation queue list
  - selected plan detail
  - forecast and latest generation results below
- Plans tab:
  - filters/search/actions
  - plan list + selected plan detail
  - plan tasks + selected task detail
- Templates tab:
  - template filters/search/actions
  - template list + detail
  - step list + selected step detail
- Improve spacing, borders, hierarchy; do not change workflows.

Reliability:
- Asset health, downtime, failure codes, sensor exceptions.
- Use summary metrics + lists/details.

Task Templates:
- Template master-detail with steps below.

4. Inventory & Procurement module
Dashboard:
- Stock health, reorder signals, procurement pipeline, supplier issues.

Catalog:
- Category/item master-detail.
- Left: categories/items.
- Right: selected detail and linked documents if existing.

Inventory:
- Storerooms, stock balances, transactions.
- Master-detail with transaction history.
- Filters for site/storeroom/item/transaction type.

Reservations:
- Queue/review layout.
- Actions: issue, release, cancel if existing.

Procurement:
- Requisitions and purchase orders.
- Selected detail, lines, receipts.
- Status filters.
- Actions through existing controller/API.

Pricing:
- Stock signals and supplier pricing.
- Export actions if existing.
- Use analytics/table layout.

Shared component improvements:
Review and improve existing components first so all modules benefit:
- WorkspaceFrame
- WorkspaceCard
- MetricCard
- RecordListCard
- WorkspaceStateBanner
- AdminCatalogPanel
- DetailPanel / PreventiveDetailSection / similar detail sections
- Filter sections
- Dialog hosts
- PrimaryButton / SecondaryButton / IconButton if present
- StatusBadge if present

If a reusable component is missing and multiple modules need it, add it under the correct existing shared QML module:
- src/ui_qml/shared/qml/App/Widgets
- src/ui_qml/shared/qml/App/Controls
- src/ui_qml/shared/qml/App/Layouts

Possible useful shared components:
- AppDivider
- StatusBadge
- SectionHeader
- EmptyState
- ToolbarCard or FilterBar
- SplitWorkspace
- MasterDetailLayout
- LoadingOverlay
- InlineMessage
- PageHeader

Only add these if they reduce duplication and fit the existing structure.


EMPTY / LOADING / ERROR STATES


All workspaces should gracefully handle:
- empty datasets
- loading states
- refresh states
- partial failures
- unavailable data

Use reusable shared components:
- EmptyState
- LoadingOverlay
- InlineMessage
- ErrorBanner

Avoid blank or unexplained empty screens.

Specific border cleanup rules:
1. Remove or soften borders from:
   - app shell content wrapper
   - parent workspace containers
   - nested layout rectangles
   - sidebar item wrappers
   - large sections that already contain bordered cards

2. Keep subtle borders on:
   - actual cards
   - input fields
   - tables/lists if needed
   - focused/selected records
   - dialogs

3. Replace heavy borders with:
   - background contrast
   - spacing
   - section headers
   - subtle dividers
   - selected-state accents

4. Avoid:
   - border.color: Theme.AppTheme.border on every Rectangle
   - radiusLg on every nested container
   - multiple white cards nested inside white cards

QML behavior rules:
- Keep existing model shapes from presenters.
- Keep existing root properties.
- Keep existing signals.
- Keep existing onClicked/onActivated forwarding patterns.
- If changing a component public API, update all usages.
- Prefer backward-compatible additions.
- Use defensive fallbacks for missing controller/state:
  controller ? controller.property || {} : {}
- Do not add complex business JavaScript in QML.
- Search/filter widgets may emit user intent only.


QML PERFORMANCE RULES


QML should remain lightweight and render-focused.

Avoid:
- business logic in QML JavaScript
- excessive property bindings
- repeated model reconstruction
- unnecessary animations
- large deeply nested visual trees

Prefer:
- presenter-prepared state
- reusable lightweight delegates
- stable bindings
- virtualization
- lazy loading where useful

Large operational screens must remain responsive.


STATUS SYSTEM


Use a unified status visualization system across all modules.

Shared reusable components:
- StatusBadge
- severity indicators
- lifecycle tones

Suggested tones:
- success
- warning
- danger
- info
- neutral
- inactive

Avoid module-specific random status colors.

Status colors should remain restrained and enterprise-oriented.

Controller/presenter/API changes:
If UI improvement requires missing state, use this order:
1. Check existing controller property.
2. Check existing presenter state.
3. Check existing desktop API DTO.
4. If missing, add display-ready state to presenter/view model.
5. If presenter lacks data, extend desktop API read method cleanly.
6. If action is missing but business use case exists, add controller method that calls presenter/API.
7. Do not implement new business rules in UI or presenter.

Example:
If a workspace needs a status badge label/color:
- Add statusLabel/statusTone in presenter view model.
- QML uses StatusBadge { label: row.statusLabel; tone: row.statusTone }
- Do not compute business status rules in QML.

AUDITABILITY UX

Enterprise records should expose traceability where available.

Examples:
- created by
- updated by
- lifecycle state
- approval history
- workflow transitions
- last activity timestamps

Audit information should:
- remain secondary in hierarchy
- be compact
- avoid cluttering workflows

Testing and validation:
After implementation:
- run qmllint across src/ui_qml/**/*.qml if configured
- run QML offscreen loading tests
- run architecture guardrail tests
- run relevant platform/project/maintenance/inventory tests
- fix import errors, missing properties, style warnings, and broken bindings

Suggested commands to try:
- python -m compileall -q src
- pytest src/tests/architecture
- pytest src/tests/platform
- pytest src/tests/project_management
- pytest src/tests/inventory_procurement
- pytest tests/test_qml_offscreen_loading.py if that path exists
- qmllint src/ui_qml/**/*.qml if available in the environment


SHARED ENTERPRISE TABLE ARCHITECTURE


Design a reusable shared enterprise table framework.

Potential shared components:
- App.Widgets/DataTable.qml
- App.Widgets/TableToolbar.qml
- App.Widgets/TablePagination.qml
- App.Widgets/TableColumnCustomizer.qml
- App.Widgets/StatusBadge.qml
- App.Widgets/MasterDetailLayout.qml
- App.Widgets/QueueTable.qml

The table framework should support:
- reusable column metadata
- sorting
- filtering
- row selection
- batch actions
- keyboard navigation
- customizable columns
- persistent preferences if supported
- status rendering
- row actions

All modules should gradually migrate toward this shared table framework.

Avoid duplicating table implementations per module.


Implementation plan:
Before converting list/card views to tables, design a reusable customizable DataTable component and one column metadata contract, then apply it gradually to major module tables.
1. Inspect the existing QML theme and shared components.
2. Identify the top 10 sources of excessive borders and nested rectangles.
3. Improve theme tokens.
4. Refactor shared shell/layout/card/navigation components.
5. Improve shell header/drawer/workspace frame.
6. Improve one representative workspace per module first:
   - Platform admin/control/settings
   - Project Management dashboard/projects/tasks
   - Maintenance preventive
   - Inventory catalog/inventory/procurement
7. Reuse the improved components across other workspaces.
8. Add small presenter/controller/API state only where necessary and cleanly justified.
9. Run validation.
10. Summarize changes.

Expected final result:
- The app should feel like one unified enterprise platform.
- Navigation should be clean and grouped.
- Workspaces should have predictable layouts.
- Cards should be meaningful, not everywhere.
- Borders should be subtle and rare.
- QML should remain render-only.
- Controllers/presenters/APIs should remain the orchestration/data boundary.
- Existing repo structure must be respected.

Output format after work:
1. Short summary of what changed
2. Files changed grouped by area
3. New theme tokens/components added
4. Module UI improvements
5. Any controller/presenter/API additions and why
6. Tests/commands run and results
7. Remaining recommended UI cleanup


FINAL UX TARGET


The final platform should feel like a mature enterprise operations product.

The user experience should prioritize:
- operational efficiency
- predictability
- scalability
- dense information workflows
- reduced visual noise
- fast navigation
- long-session usability

Users should feel comfortable managing:
- thousands of records
- operational queues
- approvals
- maintenance planning
- procurement workflows
- project execution
- inventory operations

The platform should visually and behaviorally resemble:
- SAP Fiori
- IBM Maximo
- Microsoft Dynamics
- ServiceNow
- Jira Enterprise
- enterprise ERP/EAM desktop systems

The application should no longer feel:
- developer-generated
- overly boxed
- card-heavy
- mobile-inspired
- dashboard-only

It should feel:
- operational
- structured
- trustworthy
- scalable
- enterprise-grade
- workflow-oriented