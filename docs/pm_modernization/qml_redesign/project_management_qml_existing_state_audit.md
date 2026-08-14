# Project Management QML Existing-State Audit

Status: audit complete; R0.1 and behavior-preserving R0.5 complete; R1.1 query-integrity mapping in progress  
Audit date: 2026-08-14  
Primary scope: `src/ui_qml/modules/project_management/`

## 1. Executive summary

The PM desktop UI is functional and substantially backed by real application services. It is not a prototype shell: Projects, Tasks, Scheduling, Resources, Financials, Portfolio, Register, Collaboration, Timesheets, and Dashboard all have active routes, controllers, presenters, view models, loading/error states, and real desktop API wiring.

The architecture is only partly coherent. Capability-oriented Python packages are a good base, and shared `App.*` controls provide strong theming, table, dialog, sticky-detail, and density infrastructure. The main weaknesses are product structure and query semantics:

- Ten peer PM destinations are exposed directly in the application drawer. Global, portfolio, project, execution, commercial, and team concepts are flattened into one level.
- Each project-aware workspace owns a separate selected-project value. There is no authoritative PM-wide project context, so users can see different projects in Financials, Scheduling, Dashboard, Register, Collaboration, and Timesheets.
- `DataTable` sorts only the rows currently loaded into its model. On server-paginated lists this looks like global sorting but is page-local.
- Collaboration fetches at most 200 records and then searches, filters, and paginates locally. Results beyond that bound are invisible.
- Timesheets presents a review queue but advertises inert search and filters that do not constrain that queue. Existing time-entry CRUD is not exposed in this workspace.
- Portfolio's visible Rebalance action only refreshes. Collaboration's settings and filter popups also contain no-op or placeholder behavior.
- Finance displays a broad canonical read model, but almost all modern configuration, budget, forecast, change, commitment, and billing command surfaces remain absent from QML.
- Fixed navigation rails and single-row action toolbars do not adapt adequately at 1024x768. Local PM QML adds almost no accessibility metadata.
- Several large files mix orchestration and presentation. `TasksTimeEntriesSection.qml` (1,306 lines), `scheduling_workspace_controller.py` (762), and `tasks_workspace_controller.py` (704) are the clearest examples.

R0.1 is approved. The target is one canonical Project Management module/workspace route with PM-local navigation for six capability groups: Overview, Portfolio, Work, People & Time, Finance, and Governance. The ten current route IDs remain migration/deep-link compatibility routes only until their dependencies are removed. R0.5 does not change route behavior.

No P0 security or data-loss defect was proven in the UI audit. Authorization remains enforced below QML. There are, however, P1 misleading-capability and incomplete-workflow issues that should be resolved before visual polish.

## 2. Scope and method

The audit followed active routes from `routes.py` into each workspace wrapper and page, then traced local QML components, `qmldir` registrations, Python context injection, controllers, presenters, view models, desktop API calls, query contracts, domain-event refresh binders, and relevant tests. Shared `App.Controls`, `App.Layouts`, `App.Widgets`, `App.Theme`, `App.Icons`, and shell components were read where PM depends on their behavior.

Backend inspection was limited to proving authoritative capabilities, supported commands, query semantics, authorization boundaries, pagination, and read-model ownership. This document does not propose domain changes and does not treat QML as an authorization boundary.

Static reference results are conservative. A registered but apparently unused QML type is not approved for deletion until an engine type-load and route smoke pass proves that no dynamic dependency exists.

## 3. Inventory

| Artifact | Count | Notes |
|---|---:|---|
| QML files | 178 | Includes generated `plugins.qmltypes`; 177 authored QML files |
| `qmldir` files | 59 | Many capability subfolders have their own module contract |
| JavaScript helpers | 6 | Column definitions for Financials, Projects, Register, Resources, Tasks, and Timesheets |
| Controller-layer Python files | 146 | 133 excluding `__init__.py`; 46 declared classes plus functional helpers/mixins |
| Presenter-layer Python files | 171 | 160 excluding `__init__.py`; 14 facade classes plus functional builders/mappers |
| View-model Python files | 12 | 11 excluding `__init__.py`; 104 frozen view-model classes |
| Active route/workspace pairs | 10 | All injected through `ProjectManagementWorkspaceCatalog` |
| PM-local QML type-info fragments | 12 | Generated controller QML type descriptions |

### 3.1 Directory ownership

```text
src/ui_qml/modules/project_management/
|-- context.py                     # controller construction, caching, integration capabilities
|-- routes.py                      # 10 shell routes and QML paths
|-- controllers/
|   |-- common/                    # controller base, mutation runner, capability flags, serializers
|   |-- collaboration/             # 15 files
|   |-- dashboard/                 # 7 files
|   |-- financials/                # 7 files
|   |-- portfolio/                 # 8 files
|   |-- projects/                  # 13 files
|   |-- register/                  # 10 files
|   |-- resources/                 # 12 files
|   |-- scheduling/                # 18 files
|   |-- tasks/                     # 23 files
|   `-- timesheets/                # 12 files
|-- presenters/
|   |-- collaboration/             # 16 files
|   |-- dashboard/                 # 13 files
|   |-- financials/                # 16 files
|   |-- portfolio/                 # 18 files
|   |-- projects/                  # 19 files
|   |-- register/                  # 13 files
|   |-- resources/                 # 16 files
|   |-- scheduling/                # 15 files
|   |-- tasks/                     # 28 files
|   `-- timesheets/                # 15 files
|-- view_models/                   # one capability file plus workspace.py
`-- qml/
    |-- ProjectManagement/         # PM Controllers, Dialogs, and Widgets modules
    `-- workspaces/                # ten active capabilities plus unrouted risk/
```

### 3.2 Exhaustive QML manifest

Generated type information:

- `ProjectManagement/Controllers/typeinfo/plugins.qmltypes`

PM dialog module:

- `ActualLifecycleDialog.qml`, `ManualActualEditorDialog.qml`
- `ProjectEditorDialog.qml`, `ProjectsImportDialog.qml`, `ProjectStatusDialog.qml`
- `RegisterEntryEditorDialog.qml`
- `ResourceCertificationEditorDialog.qml`, `ResourceEditorDialog.qml`, `ResourceSkillEditorDialog.qml`
- `TaskAssignmentEditorDialog.qml`, `TaskAssignmentHoursDialog.qml`, `TaskAssignmentResponseDialog.qml`, `TaskCollaborationComposerDialog.qml`, `TaskCommentDeleteDialog.qml`, `TaskDependencyEditorDialog.qml`, `TaskEditorDialog.qml`, `TaskProgressDialog.qml`, `TaskWbsMoveDialog.qml`

PM widget module:

- `DashboardChartCard.qml`, `DashboardPanelCard.qml`, `DashboardSectionCard.qml`
- `RecordListCard.qml`
- `RegisterCatalogSection.qml`, `RegisterDetailSection.qml`, `RegisterDialogHost.qml`, `RegisterFiltersSection.qml`, `RegisterMetricsSection.qml`, `RegisterUrgentSection.qml`
- `TimesheetEntriesCard.qml`
- `WorkspacePlaceholderPage.qml`, `WorkspaceStateBanner.qml`, `WorkspaceStatusSection.qml`

Collaboration:

- Root: `CollaborationWorkspace.qml`, `CollaborationWorkspacePage.qml`, `CollaborationWorkspaceState.qml`
- Components: `CollaborationFilterPopup.qml`, `CollaborationSettingsPopup.qml`, `CollaborationViewsPopup.qml`
- Panels/sections: `CollaborationDetailPanel.qml`, `CollaborationMetricsSection.qml`, `CollaborationToolbarSection.qml`

Dashboard:

- Root: `DashboardWorkspace.qml`, `DashboardWorkspacePage.qml`
- Components: `DashboardHealthCard.qml`, `DashboardPanelFrame.qml`
- Panels: `DashboardInsightPanel.qml`, `DashboardOperationalPanel.qml`, `DashboardTablePanel.qml`
- Sections: `DashboardAnalysisPanels.qml`, `DashboardChartsSection.qml`, `DashboardMetricsSection.qml`, `DashboardOverviewSections.qml`, `DashboardPanelsSection.qml`, `DashboardSelectionBar.qml`

Financials:

- Root/helper: `FinancialsWorkspace.qml`, `FinancialsWorkspacePage.qml`, `FinancialsColumnConfig.js`
- Dialog/panel: `FinancialsDialogHost.qml`, `FinancialsDetailPanel.qml`
- Sections: `FinancialsActivitySection.qml`, `FinancialsActualsSection.qml`, `FinancialsBillingPreparationSection.qml`, `FinancialsBudgetLinesSection.qml`, `FinancialsBudgetVersionsSection.qml`, `FinancialsChangeSection.qml`, `FinancialsCollectionBlock.qml`, `FinancialsCommitmentsSection.qml`, `FinancialsForecastSection.qml`, `FinancialsMetricsSection.qml`, `FinancialsPlannedCostsSection.qml`, `FinancialsProfileSection.qml`, `FinancialsPurchaseOrdersSection.qml`, `FinancialsRateCardsSection.qml`, `FinancialsReportsSection.qml`, `FinancialsVarianceSection.qml`

Portfolio:

- Root: `PortfolioWorkspace.qml`, `PortfolioWorkspacePage.qml`, `PortfolioWorkspaceState.qml`
- Panels: `PortfolioBottomPanel.qml`, `PortfolioDetailPanel.qml`
- Sections: `PortfolioDependenciesSection.qml`, `PortfolioExecutiveSection.qml`, `PortfolioGovernanceToolbar.qml`, `PortfolioIntakeSection.qml`, `PortfolioScenariosSection.qml`, `PortfolioSummaryCard.qml`, `PortfolioTemplatesSection.qml`, `PortfolioToolbarSection.qml`

Projects:

- Root/helper: `ProjectsWorkspace.qml`, `ProjectsWorkspacePage.qml`, `ProjectsWorkspaceState.qml`, `ProjectsColumnConfig.js`
- Components/dialog/panel: `ProjectsFilterPopup.qml`, `ProjectsListPage.qml`, `ProjectsDialogHost.qml`, `ProjectsDetailPanel.qml`
- Sections: `ProjectsActivitySection.qml`, `ProjectsDocumentsSection.qml`, `ProjectsFinancialsSection.qml`, `ProjectsMaterialDemandSection.qml`, `ProjectsOverviewSection.qml`, `ProjectsProcurementSection.qml`, `ProjectsResourcesSection.qml`, `ProjectsRisksSection.qml`, `ProjectsScheduleSection.qml`, `ProjectsTasksSection.qml`

Register:

- Root/helper: `RegisterWorkspace.qml`, `RegisterWorkspacePage.qml`, `RegisterWorkspaceState.qml`, `RegisterColumnConfig.js`
- Components/panels: `RegisterListPage.qml`, `RegisterDetailPanel.qml`

Resources:

- Root/helper: `ResourcesWorkspace.qml`, `ResourcesWorkspacePage.qml`, `ResourcesWorkspaceState.qml`, `ResourcesColumnConfig.js`
- Components/dialog/panel: `ResourcesFilterPopup.qml`, `ResourcesListPage.qml`, `ResourcesDialogHost.qml`, `ResourcesDetailPanel.qml`
- Sections: `ResourcesActivitySection.qml`, `ResourcesAssignmentsSection.qml`, `ResourcesAvailabilitySection.qml`, `ResourcesCalendarSection.qml`, `ResourcesCapacitySection.qml`, `ResourcesCertificationsSection.qml`, `ResourcesCostRatesSection.qml`, `ResourcesOverviewSection.qml`, `ResourcesSkillsSection.qml`

Scheduling:

- Root: `SchedulingWorkspace.qml`, `SchedulingWorkspacePage.qml`, `SchedulingWorkspaceState.qml`
- Components/dialog: `SchedulingActionBar.qml`, `SchedulingPanelFrame.qml`, `SchedulingDialogHost.qml`
- Panels: `SchedulingActivityFeedPanel.qml`, `SchedulingActivityTimelinePanel.qml`, `SchedulingBaselinesPanel.qml`, `SchedulingCalendarsPanel.qml`, `SchedulingDelaysPanel.qml`, `SchedulingDetailPanel.qml`, `SchedulingDiagnosticsPanel.qml`, `SchedulingResourcesPanel.qml`, `SchedulingTimelinePanel.qml`
- Legacy-looking sections: `SchedulingBaselineSection.qml`, `SchedulingCalendarSection.qml`, `SchedulingMetricsSection.qml`, `SchedulingPlanningToolbar.qml`, `SchedulingScheduleSection.qml`, `SchedulingToolbarSection.qml`

Tasks:

- Root/helper: `TasksDialogHost.qml`, `TasksWorkspace.qml`, `TasksWorkspacePage.qml`, `TasksWorkspaceState.qml`, `TasksColumnConfig.js`
- Components: `TasksBulkActions.qml`, `TasksExportDialog.qml`, `TasksFilterPopup.qml`, `TasksListPage.qml`, `TasksSavedViewsPopup.qml`
- Detail/panel: `TasksDetailMessages.qml`, `TasksDetailPage.qml`, `TasksDetailPanel.qml`
- Sections: `TaskCommentCard.qml`, `TasksAssignmentsSection.qml`, `TasksCollaborationSection.qml`, `TasksDependenciesSection.qml`, `TasksDetailsSection.qml`, `TasksMaterialDemandSection.qml`, `TasksProcurementSection.qml`, `TasksReservationsSection.qml`, `TasksScheduleImpactSection.qml`, `TasksSkillsSection.qml`, `TasksTimeEntriesSection.qml`

Timesheets:

- Root/helper: `TimesheetsWorkspace.qml`, `TimesheetsWorkspacePage.qml`, `TimesheetsWorkspaceState.qml`, `TimesheetsColumnConfig.js`
- Components/panel: `TimesheetsFilterPopup.qml`, `TimesheetsListPage.qml`, `TimesheetsViewsPopup.qml`, `TimesheetsDetailPanel.qml`

Unrouted:

- `workspaces/risk/RiskWorkspace.qml`

All 59 `qmldir` files were inspected. They cover `ProjectManagement.Controllers`, `ProjectManagement.Dialogs`, `ProjectManagement.Widgets`, each workspace root, and most local `components`, `dialogs`, `detail`, `panels`, and `sections` folders. Several empty subfolder modules remain and add move risk without providing types.

### 3.3 Python UI layer

The active QML-facing facades are:

| Capability | Primary controller | Primary presenter | View-model file |
|---|---|---|---|
| Catalog | `ProjectManagementWorkspaceCatalog` in `context.py` | `ProjectManagementWorkspacePresenter` | `workspace.py` |
| Projects | `ProjectManagementProjectsWorkspaceController` | `ProjectsWorkspacePresenter` | `projects.py` |
| Tasks | `ProjectManagementTasksWorkspaceController`, plus task/list/assignment/dependency/time/collaboration subcontrollers | `TasksWorkspacePresenter` | `tasks.py` |
| Scheduling | `ProjectManagementSchedulingWorkspaceController` | `SchedulingWorkspacePresenter` | `scheduling.py` |
| Resources | `ProjectManagementResourcesWorkspaceController` | `ResourcesWorkspacePresenter` | `resources.py` |
| Financials | `ProjectManagementFinancialsWorkspaceController` | `FinancialsWorkspacePresenter` | `financials.py` |
| Portfolio | `ProjectManagementPortfolioWorkspaceController` | `PortfolioWorkspacePresenter` | `portfolio.py` |
| Register | `ProjectManagementRegisterWorkspaceController` | `RegisterWorkspacePresenter` | `register.py` |
| Collaboration | `ProjectManagementCollaborationWorkspaceController` | `ProjectCollaborationWorkspacePresenter` | `collaboration.py` |
| Timesheets | `ProjectManagementTimesheetsWorkspaceController` | `TimesheetsWorkspacePresenter` | `timesheets.py` |
| Dashboard | `ProjectManagementDashboardWorkspaceController` | `ProjectDashboardWorkspacePresenter` | `dashboard.py` |

Controller helper files split table models, selection, state setters, mutation handling, export, pagination, lazy detail hydration, and event binding. Presenter helper files split workspace construction, records, metrics, formatting, options, collections, and command payload mapping. This functional decomposition is generally sound even though several facade classes remain too large.

### 3.4 Shared dependencies

PM imports these shared modules directly:

- `App.Theme` in 135 QML files.
- `App.Widgets` in 124 QML files.
- `App.Controls` in 107 QML files.
- `App.Layouts` in 11 QML files.
- `App.Icons` directly in one QML file; buttons otherwise consume semantic `iconName` strings.
- `App.Mock` in 18 QML files, primarily as empty/default view-model factories rather than sample production rows.

The most-used shared types are `FormField` (82), `LazySectionLoader` (66), `InlineMessage` (63), `EmptyState` (43), `DataTable` (42), `SectionHeading` (32), `ContextualActionToolbar` (29), `EntityDialog` (22), `StatusChip` (20), `SectionScopedInlineMessage` (20), `LoadingOverlay` (17), `TableToolbar` (15), `AnchoredPopup` (13), `ActivityFeed` (12), `SectionCard` (10), `TablePaginationBar` (10), `SectionDetailPage` (10), and `KpiStrip` (9).

Shell dependencies are `QmlRoute`, the drawer route catalog, the `ApplicationWindow` at 1280x800, and `ProjectManagementWorkspaceCatalog`. Cross-module UI dependencies are capability-gated route links to inventory reservations, procurement requests, and purchase orders. PM does not directly import those module packages in QML or Python UI code.

## 4. Routes and current information architecture

`ProjectManagementWorkspaceDesktopApi` defines this shell order:

1. `project_management.projects`
2. `project_management.tasks`
3. `project_management.scheduling`
4. `project_management.resources`
5. `project_management.financials`
6. `project_management.portfolio`
7. `project_management.register`
8. `project_management.collaboration`
9. `project_management.timesheets`
10. `project_management.dashboard`

Each route loads a thin `<Capability>Workspace.qml` wrapper, which injects `pmCatalog` into `<Capability>WorkspacePage.qml`. Controllers are lazily created and cached by `context.py`; therefore each workspace normally preserves its own in-memory filters and selection while the application session remains alive. That persistence is local, not synchronized.

Current taxonomy:

```text
Application drawer
`-- Project Management / Workspaces
    |-- Projects           global catalog -> project detail
    |-- Tasks              cross-project execution list -> task detail
    |-- Scheduling         selected-project planning console -> activity detail
    |-- Resources          global resource catalog -> resource detail
    |-- Financials         selected-project section workspace
    |-- Portfolio          global portfolio/scenario console -> project decision detail
    |-- Register           global/project risk, issue, change list -> entry detail
    |-- Collaboration      global/project work inbox -> item detail
    |-- Timesheets         review queue -> timesheet detail
    `-- Dashboard          selected-project executive/operational dashboard
```

There is no separate PM module landing page and no PM-level navigation model. The application drawer is simultaneously module navigation and workspace navigation.

## 5. Shared shell and detail behavior

`WorkspaceFrame` pins the page header above a fill-height content slot and applies tokenized page padding. List pages place messages, KPIs, toolbar, table, pagination, loading, and bulk actions in that slot.

`SectionDetailPage` uses a fixed 220-pixel section rail and one active section. Children marked `detailPagePinned` are reparented into a sticky region above the scrollable section body. Projects, Tasks, Resources, Register, Portfolio, Financials, Scheduling, Collaboration, and Timesheets use this mechanism, so contextual action bars and scoped messages remain visible while body content scrolls.

`ContextualActionToolbar` is one non-wrapping row. It reserves up to 200 pixels for title and 160 for subtitle, then renders every action as a full text button. It has no overflow menu or compact mode.

At 1024 pixels with an expanded 248-pixel shell drawer, 40 pixels of page margins, and a 220-pixel section rail, approximately 516 pixels remain before scrollbars and local padding. This is insufficient for many financial/task action sets and table details.

## 6. Workspace reconstruction

### 6.1 Dashboard

Controller: `ProjectManagementDashboardWorkspaceController`  
Entry: shell route; project, baseline, period, and view selectors are local controller state.  
Data: executive metrics, health, charts, analysis panels, operational tabs, activity.  
Actions: refresh and export. Selection in the operational table is not an entity inspector flow.

```text
+------------------------------------------------------------------+
| PageHeader: Dashboard                                            |
+------------------------------------------------------------------+
| Project [........] Baseline [....] Period [...] View [...] Refresh|
+------------------------------------------------------------------+
| fixed messages | KPI strip                                      |
+------------------------------------------------------------------+
| Scroll body                                                       |
| +-----------------------+ +------------------------------------+ |
| | analysis/health       | | charts                             | |
| +-----------------------+ +------------------------------------+ |
| | overview panels                                               | |
| +---------------------------------------------------------------+ |
| | operational tabs + toolbar + table + pagination               | |
| +---------------------------------------------------------------+ |
| | activity feed                                                  | |
| +---------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

Only one coarse width check at 1360 changes a preferred section height. The selector bar has several fixed preferred widths and can crowd at 1024.

### 6.2 Portfolio

Controller: `ProjectManagementPortfolioWorkspaceController` (554 lines).  
Data: intake, templates, scenarios, heatmap, dependencies, capacity/evaluation summaries, and recent decisions.  
Selection: heatmap row selection; activation opens full section detail. No inspector.  
Mutations: intake/template/scenario/dependency commands and evaluation are real; visible Rebalance is not.

```text
+------------------------------------------------------------------+
| PageHeader: Portfolio                                            |
+------------------------------------------------------------------+
| Scenario [..] Base [..] Compare [..] Refresh Compare Rebalance   |
+------------------------------------------------------------------+
| KPI strip                                                        |
| Search | Filter | Export                                         |
| Heatmap DataTable                                      page bar  |
+------------------------------------------------------------------+
| fixed 268px bottom panel: intake/templates/scenarios/dependencies|
| capacity/activity and their local actions/tables                 |
+------------------------------------------------------------------+
| row activation -> full 220px-rail PortfolioDetailPanel           |
+------------------------------------------------------------------+
```

The 268-pixel bottom panel carries too many workflows and is the most cramped current page. `onRebalanceRequested` calls `refresh()` and does not rebalance.

### 6.3 Projects

Controller: `ProjectManagementProjectsWorkspaceController` (500 lines).  
List query: server search, status, page, and page size. Site options exist for project forms, not for the catalog query.  
Selection: single click selects; double click/activation calls `activateProject` and opens a full detail page. No inspector.  
Actions: create, import, export, edit, status, delete, resource assignment, bulk status/delete.

```text
+------------------------------------------------------------------+
| PageHeader: Projects                                             |
| messages | KPI strip                                             |
| Search | Filter | Views? | Import | Export | New Project         |
| checkbox DataTable                                     page bar  |
| bottom-center bulk actions when checked                         |
+------------------------------------------------------------------+
| activation -> sticky actions/messages                            |
| +--------------------+------------------------------------------+ |
| | 220px section rail | active project section                  | |
| | Overview           | Overview/Resources/Tasks/Schedule/...   | |
| | Resources          | capability-gated Materials/Procurement  | |
| | ...                |                                          | |
| +--------------------+------------------------------------------+ |
+------------------------------------------------------------------+
```

Documents and Risks currently render empty-state integration messages rather than full project-local workflows. Inventory/procurement sections correctly expose route navigation only when capabilities exist.

### 6.4 Tasks

Controller: `ProjectManagementTasksWorkspaceController` (704 lines), with five QML-facing subcontrollers.  
List query: server search, status, project, page, and page size; saved views are local.  
Selection: single click selects; activation opens full detail. No inspector.  
Actions: create/edit/delete, progress, WBS move, assignment, dependency, time entry, collaboration, bulk status/delete, import-adjacent reservations/procurement links.

```text
+------------------------------------------------------------------+
| PageHeader: Tasks                                                |
| messages | KPI strip                                             |
| Search | Filter | Saved Views | Export | New Task                |
| checkbox DataTable                                     page bar  |
| bottom-center bulk actions                                       |
+------------------------------------------------------------------+
| activation -> sticky contextual actions and scoped messages      |
| +--------------------+------------------------------------------+ |
| | 220px grouped rail | Details / Assignments / Dependencies     | |
| | Delivery           | Time / Collaboration / Skills            | |
| | Execution          | Schedule impact / Materials / Purchasing | |
| +--------------------+------------------------------------------+ |
+------------------------------------------------------------------+
```

`TasksTimeEntriesSection.qml` contains selection, entry CRUD, period selection, approvals, locking, summaries, tables, and multiple tabs in 1,306 lines. It is a maintainability hotspot, not a dead file.

### 6.5 Scheduling

Controller: `ProjectManagementSchedulingWorkspaceController` (762 lines).  
Entry/context: local project, baseline, and calendar selectors.  
Data/actions: paginated activity timeline, CPM, critical/delayed filters, diagnostics, leveling/resource load, baseline register and comparison, delays, calendars/holidays, and activity feed.  
Selection: activity activation opens full detail with dependencies, constraints, calendars, baselines, resources, and schedule impact.

```text
+------------------------------------------------------------------+
| Project [..] Baseline [..] Calendar [..] Run CPM                 |
| messages | KPI strip                                             |
| [Activity][Diagnostics][Resources][Baselines][Delays][Calendars] |
| [Activity Feed]                                                   |
+------------------------------------------------------------------+
| active StackLayout panel                                          |
| timeline panel: search/filter + table/timeline + pagination       |
| other panels: complete selected-project collections + local search|
+------------------------------------------------------------------+
| activity detail -> fixed section rail + one active detail section |
+------------------------------------------------------------------+
```

The active page uses a handcrafted tab row. Several older section components remain registered but are not imported by production pages.

### 6.6 Resources

Controller: `ProjectManagementResourcesWorkspaceController` (389 lines).  
List query: server search, active status, resource category, page, page size.  
Selection: single click selects; activation opens full detail. No inspector.  
Actions: create/edit/delete, assignments, skills, certifications, capacity/calendar review, bulk delete.

```text
+------------------------------------------------------------------+
| PageHeader: Resources                                            |
| messages | KPI strip                                             |
| Search | Filter | Export | New Resource                          |
| checkbox DataTable                                     page bar  |
+------------------------------------------------------------------+
| detail: 220px rail | Overview, Assignments, Availability,        |
|                    | Capacity, Calendar, Cost Rates, Skills,      |
|                    | Certifications, Activity                    |
+------------------------------------------------------------------+
```

Department and site are visible in records and editor options, but not exposed as list filters.

### 6.7 Financials

Controller: `ProjectManagementFinancialsWorkspaceController` (296 lines plus four mixins).  
Context: a local project selector is pinned above the section action bar.  
Data: financial profile, budget versions/lines, rate cards, planned costs, canonical actuals, forecast, change control, commitments, billing preparation, capability-gated purchase orders, variance, reports, and activity.  
Actions exposed: manual actual creation and actual lifecycle, plus report export.

```text
+------------------------------------------------------------------+
| PageHeader: Financials                                           |
| Project [..............................] Refresh                  |
| sticky active-section actions and messages                       |
+----------------------+-------------------------------------------+
| 220px grouped rail  | one active section                         |
| Configuration       | Profile / Rate Cards                       |
| Planning            | Budgets / Planned Costs / Forecast         |
| Cost Control        | Actuals / Changes / Commitments             |
| Commercial          | Billing Preparation / Purchase Orders      |
| Insights            | Variance / Reports / Activity               |
+----------------------+-------------------------------------------+
```

The grouped rail solves section discoverability and starts groups collapsed. The UI remains mostly read-only despite a modern command API. Billing explicitly preserves the ownership boundary: PM prepares commercial evidence; Accounting owns invoices, receivables, payments, tax, and ledger truth.

### 6.8 Register

Controller: `ProjectManagementRegisterWorkspaceController` (349 lines).  
List query: server project, type, status, severity, search, page, and page size.  
Selection: activation opens full detail; no inspector.  
Actions: create risk/issue/change, edit, delete, bulk status/severity/delete.

```text
+------------------------------------------------------------------+
| PageHeader: Register                                             |
| KPI strip | search | project/type/status/severity filters        |
| checkbox unified DataTable                            page bar    |
+------------------------------------------------------------------+
| detail: fixed rail | Details | Impact | Response | Links          |
+------------------------------------------------------------------+
```

### 6.9 Collaboration

Controller: `ProjectManagementCollaborationWorkspaceController` (324 lines).  
Data: inbox, mentions, approval requests, team updates, activity, detail, and presence context.  
Query: snapshots and approvals are capped at 200, then QML/Python apply client-side filtering and pagination.  
Selection: row selection enables contextual actions; activation opens full detail.

```text
+------------------------------------------------------------------+
| Project [..] Team [..] Period [..] Unread [..] | KPI strip       |
| [Inbox][Mentions][Approvals][Team Updates][Activity]              |
| Search | Filter | Views | Customize | Export | Refresh            |
| DataTable + local pagination                                     |
+------------------------------------------------------------------+
| selected item -> actions: read/approve/reject/open source         |
| activation -> Overview | Activity | Related detail sections       |
+------------------------------------------------------------------+
```

`CollaborationSettingsPopup` says settings may be added in a later iteration. `CollaborationFilterPopup` redirects users to context controls and its Apply action changes no filter. These are active placeholder controls.

### 6.10 Timesheets

Controller: `ProjectManagementTimesheetsWorkspaceController` (385 lines).  
Displayed data: server-paginated review queue filtered only by workflow status.  
Secondary state: project, assignment, and period selectors hydrate an assignment snapshot, but that snapshot is not the main list.  
Selection: activation opens entries, approval history, and labor notes detail.  
Actions: submit, approve, reject, lock, unlock; backend also supports entry add/update/delete and period reopening.

```text
+------------------------------------------------------------------+
| PageHeader: Timesheets                                           |
| KPI strip | Search (inert) | Filter | Views                      |
| review queue DataTable                                page bar   |
+------------------------------------------------------------------+
| filter popup: project/assignment/period (not queue constraints)   |
| detail: Entries | Approval History | Labor Notes                  |
| lifecycle actions in sticky contextual toolbar                   |
+------------------------------------------------------------------+
```

The workspace name and summary promise time entry, but the active page is primarily an approval queue. Time capture exists in task detail and shared/backend contracts, not as a coherent Timesheets flow.

## 7. Interaction model

| Area | Current model | Assessment |
|---|---|---|
| Projects/Tasks/Resources/Register | click selects; activate/double-click opens full detail | Consistent, but no preview inspector |
| Portfolio | click selects heatmap row; activation opens detail; bottom panel is independent | Competing list/detail and fixed multi-tool panel |
| Scheduling | tabs select planning panel; activity activation opens detail | Appropriate full workspace, custom tabs duplicate shared behavior |
| Financials | project selector plus section rail; no list/detail transition | Appropriate full workspace, command-light |
| Collaboration | tab + row selection + contextual action + full detail | Strong pattern, but query and popup semantics undermine trust |
| Timesheets | review list + full detail | Does not cover advertised entry workflow |
| Dashboard | selectors + scroll dashboard + operational tabs | Suitable for analysis, weak narrow-width behavior |

Back behavior is provided by sticky detail toolbars on entity detail pages. There are no breadcrumbs. Native context menus and right-click actions are not used. Bulk actions appear only after checkbox selection and are rendered bottom-center in a `RowLayout` for the applicable list pages.

Mutations generally flow:

```text
QML action -> dialog/slot -> presenter command mapper -> desktop API
           -> mutation result -> controller message/state -> refresh
           -> domain-event binder may invalidate/refresh related workspace
```

`ProjectManagementWorkspaceControllerBase` standardizes busy, error, feedback, result handling, and table state. Capability packages also contain event binders. This is good reuse, although refresh breadth and repeated full workspace reconstruction can be expensive.

## 8. Table and query audit

`DataTable` is used 42 times. It supports dynamic columns, Python source models, selection, multi-selection, loading/empty states, and keyboard row activation. `TableToolbar` is used 15 times, pagination bars 10 times, and bulk bars 7 times.

### 8.1 Major table matrix

| Workspace/table | Search/filter location | Pagination | Sorting | Selection/bulk | Finding |
|---|---|---|---|---|---|
| Projects catalog | DB search/status | DB | loaded page only | multi/bulk | Sort is misleading; site filter is not a reader option |
| Tasks catalog | DB search/status/project | DB | loaded page only | multi/bulk | Cross-project scale is otherwise correct |
| Scheduling activity | backend workspace query | DB | loaded page only | single | Other selected-project panels are bounded/local |
| Resources catalog | DB search/active/category | DB | loaded page only | multi/bulk | Department/site filters absent |
| Register | DB search/project/type/status/severity | DB | loaded page only | multi/bulk | Query contract is strong |
| Timesheet review queue | DB status only | DB | loaded page only | single | Search and context filters do not query queue |
| Portfolio heatmap | presenter/controller page/search | server/read query | loaded page only | single/bulk-evaluate | Bottom panel collections are separate |
| Collaboration panels | local over max 200 | QML/Python local | loaded slice | single | Partial-data filtering is incorrect at scale |
| Dashboard operational | dashboard snapshot/query | controller paging | loaded page only | single | Must verify global query before adding filters |
| Financial actuals/commitments | canonical reads, currently limit 50 | page metadata varies | loaded page only | single actual | Bound can hide older rows |
| Finance configuration collections | DB pages for budget/rate/planned/billing | DB where exposed | loaded page only | mostly none | Read-only surface |
| Detail subtables | selected entity collections | none | local | local | Valid only while bounded by selected entity |

### 8.2 Sorting defect

All PM tables set sortable column metadata, but no PM QML page handles `sortRequested`. When `sourceModel` is present, `DataTable._toggleSort()` calls `DynamicTableModel.toggleSort()`, which sorts only the current model rows. For DB-paginated lists, changing pages loses the apparent global order.

Required correction is a backend/query contract: add `sort_key` and `sort_direction` to paginated readers, include a stable ID tie-breaker, and make `DataTable` explicitly server-sorted for those pages. Hiding sort affordances is the safe interim option.

### 8.3 Valid client filtering

Client filtering is valid for complete, explicitly bounded selected-project or selected-entity collections such as a task's dependencies or a schedule's diagnostics. It is not valid for collaboration's capped cross-project snapshot or for any DB page.

## 9. Dialog and form audit

There are 18 PM `EntityDialog` definitions in `ProjectManagement.Dialogs`, plus capability-local dialog hosts and confirmation dialogs. `EntityDialog` provides a scrollable form body with pinned header/footer, message priority, busy handling, and content-driven height capped to the window. `DateField` positions its popup against the application overlay by default, so date pickers do not inherently overflow the window; only `ProjectEditorDialog` currently supplies a tighter form boundary.

| Dialog family | Widths found | Notes |
|---|---|---|
| Financial actuals | 480, 620 | Real lifecycle and manual-entry commands |
| Project | 420, 560, 680 | Status, editor, and two-stage import |
| Register | 680 | Long but cohesive risk/issue/change form |
| Resource | 480, 620 | Editor plus skills/certifications |
| Task | 460, 480, 520, 560, 640 | Nine dialogs; assignment editor is 324 lines |
| Scheduling baseline | 420 | Small purpose-built command dialog |
| Confirmations | mostly shared compact token; some 420/480 literals | Destructive flows generally explicit |

Good behavior:

- Shared footer order and busy/error handling are consistent.
- Dialog hosts keep forms open on backend validation errors and close after success.
- Date inputs use the shared popup-clamping implementation.
- Project, task, resource, register, and scheduling forms use authoritative selector options rather than free-text IDs where options exist.

Problems:

- Widths use nine local numeric values instead of the compact/standard/wide theme tiers.
- `ProjectsImportDialog.qml` (405 lines) and `TaskAssignmentEditorDialog.qml` (324) combine multiple states and deserve internal component splits, not conversion to full pages.
- Currency is still free text in project/resource forms even though enterprise currency options exist elsewhere.
- Several date fields do not provide a dialog/form boundary; global overlay clamping is safe, but a dialog boundary gives better placement inside narrow forms.
- Bulk timesheet approve/reject lacks a reason/confirmation flow even where governance may require one.

## 10. Workflow and backend reality

| Capability | Current UI | Backend support | Status | Recommendation |
|---|---|---|---|---|
| Project create/edit/status/delete | Full dialogs/actions | Full | Fully backed | Retain; improve context and inspector |
| Project import/export | Two-step import and file export | Full | Fully backed | Retain; split internal dialog states |
| Project resources | Add/update/remove | Full | Fully backed | Retain in detail |
| Project documents/risks sections | Empty/integration messages | Separate register/document capability incomplete here | Placeholder | Link to authoritative workspace or hide |
| Task CRUD/progress/WBS | Full | Full | Fully backed | Retain |
| Task assignment/dependency | Full dialogs/tables | Full | Fully backed | Retain |
| Task time entry | Rich task-detail section | Full | Fully backed | Reuse business flow in My Time workspace |
| Task materials/reservations/procurement | Capability-gated navigation | Integration contracts | Partially backed | Keep links; do not duplicate module UI |
| CPM/baselines/calendars/leveling | Active planning panels | Full | Fully backed | Keep as full planning workspace |
| Resource CRUD/skills/certifications | Full | Full | Fully backed | Retain |
| Resource department/site filtering | No list controls | Reader does not expose all desired filters | UI/query missing | Backend dependency |
| Portfolio intake/templates/scenarios | Active controls | Full | Fully backed | Move out of 268px bottom panel |
| Portfolio rebalance | Button refreshes only | No called rebalance command | UI no-op | Remove the no-op UI; do not invent a backend command |
| Register CRUD/bulk | Full | Full | Fully backed | Retain |
| Collaboration read/approve/reject | Active | Full for fetched snapshot | Partially backed | Add true query paging/search |
| Collaboration Settings | Placeholder popup | No settings contract traced | UI placeholder | Remove until supported |
| Timesheet review lifecycle | Active | Full | Fully backed | Retain as Review Queue |
| Timesheet entry CRUD | Not exposed in workspace | Full | UI missing | Add My Time using existing commands |
| Reopen period | Not exposed | Full | UI missing | Add permission-aware correction action |
| Finance canonical reads | Broad section coverage | Full | Fully backed reads | Improve hierarchy |
| Manual actual lifecycle | Full | Full | Fully backed | Retain |
| Finance profile/budget/rate/planned/forecast/change commands | Mostly read-only | Command services exist | UI missing | Phase by financial ownership and permissions |
| Billing preparation command lifecycle | Read-only profile/schedule/preparations | Create/activate/add/ready/submit/delivery commands exist | UI missing | Add PM evidence-preparation UI only |
| Accounting invoice/receivable/payment records | Explicitly not created | Accounting-owned | Correctly absent | Preserve boundary |
| Profitability/commercial projection | Backend projection exists | Full read support | UI incomplete | Add decision-support presentation, no duplicate truth |

## 11. Finance-specific assessment

The finance read model is aligned with the modernized backend in terminology and ownership, but the interaction surface is not aligned in breadth.

Currently shown:

- project financial profile and currency context;
- budget versions and DB-paginated budget lines;
- rate cards and paginated rates;
- planned-cost versions and paginated lines;
- canonical actual-cost ledger and actual lifecycle;
- forecast versions and source lines;
- change control;
- procurement-owned commitments and optional purchase orders;
- billing profile, schedule, and preparation reads;
- baseline variance, reports, and activity.

Backend capabilities not exposed or only weakly exposed include configuration commands, governed budget lifecycle, planned-cost/forecast/change commands, commitment drill-through, billing profile activation, schedule-line creation, readiness, preparation source composition, submission/delivery, and profitability projection presentation.

This gap should not be solved with editable local QML models. Every finance mutation must remain a command through the canonical finance desktop API. Read projections and snapshots are disposable presentation models, never an additional financial source of truth.

## 12. Design-system assessment

| Classification | Components |
|---|---|
| Good reuse | `AppTheme`, semantic button icons, `WorkspaceFrame`, `DataTable`, `EntityDialog`, `ConfirmationDialog`, `LoadingOverlay`, `EmptyState`, `InlineMessage`, `SectionDetailPage`, `SectionNavigationRail` |
| Partial reuse | `ContextualActionToolbar` lacks overflow; dialog width tokens exist but PM uses literals; `GroupedNavigationRail` capability exists but PM responsiveness is fixed |
| Local duplication | Scheduling and Collaboration hand-built tab strips; capability-local filter/view popups; repeated list page composition; repeated project selectors |
| Legacy PM components | old scheduling sections, old metrics wrappers, placeholder widgets, unused task detail wrappers |
| Should migrate/adapt | responsive action overflow, query-aware table sorting, a PM context bar, optional desktop inspector, permission-state presentation |

Theme usage is strong: no authored PM hard-coded named/hex colors were found, and approximately 2,293 `AppTheme` references are present. Dark-mode color readiness is therefore good. Density tokens exist, but hard-coded widths/heights and local fixed toolbars limit true density responsiveness.

## 13. Permissions, loading, errors, and refresh

`PMCapabilityController` exposes six flags: baseline approval, leveling, skill management, assignment override, import, and PM request approval. The controller is fully permissive when no authorization engine is injected, and `_check()` returns `true` on exceptions. This is inappropriate as a presentation policy for an enterprise UI, although services remain authoritative and prevent QML from becoming a security boundary.

Most row-level state permissions are carried in view-model `state` fields, especially finance lifecycle actions. Many general CRUD buttons are not proactively hidden/disabled by a complete capability model; denied commands therefore depend on backend errors reaching the shared inline-message path.

Loading and mutation feedback are generally consistent because controllers inherit `ProjectManagementWorkspaceControllerBase`. Detail messages are section-scoped and pinned, so a message from one detail section is not intended to scroll with or leak visually into another section. Domain-event binders refresh Projects, Tasks, Scheduling, Resources, Portfolio, Register, Collaboration, and Timesheets after relevant events; finance/dashboard refresh through their own state paths. Full workspace rebuilds remain a performance consideration.

## 14. Responsiveness and accessibility

### 14.1 1024x768

- Expanded shell drawer: 248 pixels.
- PM page horizontal padding: 40 pixels in compact density.
- Detail rail: fixed 220 pixels.
- Remaining detail content before local margins: about 516 pixels.
- Finance project selector prefers 300 and can grow to 420.
- Action toolbar title/subtitle can reserve 360 before buttons.
- Portfolio bottom panel is fixed at 268 pixels high.
- Dashboard has several selectors between 150 and 220 pixels in one action area.

The shell can collapse its drawer, but PM does not coordinate that state or change its detail navigation into a compact/dropdown form. Horizontal action loss and dense table degradation are likely at 1024.

### 14.2 Larger desktop

At 1280x800 the list pages are usable, though large detail action sets remain crowded. At 1440 and above Dashboard becomes more comfortable and its 1360 conditional height is active. Wide screens are not used for inspectors, so list-detail workflows leave useful horizontal space unexploited.

### 14.3 Accessibility

Currently implemented:

- Shared buttons, text fields, combo boxes, tables, dialogs, and rails inherit keyboard/focus behavior.
- `DataTable` supports keyboard selection/activation.
- `GroupedNavigationRail` supports arrow navigation.
- Date fields accept keyboard text and expose a shared picker.

Infrastructure exists but is weakly wired:

- Local QML contains almost no `Accessible.*`, `activeFocusOnTab`, `KeyNavigation`, or tooltip metadata.
- Custom tab `Rectangle`/`MouseArea` controls in Scheduling and Collaboration do not provide the semantics of a shared tab control.
- Icon-only back controls in `ContextualActionToolbar` rely on a `MouseArea` without an accessible name.
- Resource availability bars are one of the few local controls with tooltips.

Missing target behavior includes consistent focus order, keyboard shortcuts for create/open/search, accessible names for icon-only controls, visible focus across custom composites, and screen-reader announcements for loading/mutation messages.

## 15. Dead, legacy, and placeholder inventory

### 15.1 Confirmed dead

At audit time, none were pre-approved under the strict definition because every high-confidence candidate was named by a test or registered in a `qmldir`. R0.5F subsequently completed the required engine/runtime gate and confirmed all 23 files below as dead.

### 15.2 Confirmed and deleted by R0.5F

No production importer was found for these authored types:

- `workspaces/risk/RiskWorkspace.qml` (unrouted; architecture test reference only)
- `workspaces/tasks/detail/TasksDetailPage.qml`
- `workspaces/tasks/detail/TasksDetailMessages.qml`
- `workspaces/tasks/components/TasksBulkActions.qml` (shared primitive test and `qmldir` only)
- `workspaces/dashboard/panels/DashboardTablePanel.qml`
- `workspaces/dashboard/sections/DashboardMetricsSection.qml`
- `workspaces/collaboration/sections/CollaborationMetricsSection.qml`
- `workspaces/financials/sections/FinancialsMetricsSection.qml`
- `workspaces/scheduling/sections/SchedulingMetricsSection.qml`
- `workspaces/scheduling/sections/SchedulingPlanningToolbar.qml`
- `workspaces/scheduling/sections/SchedulingScheduleSection.qml`
- `workspaces/scheduling/sections/SchedulingToolbarSection.qml`
- `workspaces/scheduling/sections/SchedulingBaselineSection.qml`
- `workspaces/scheduling/sections/SchedulingCalendarSection.qml`
- `ProjectManagement/Widgets/DashboardPanelCard.qml`
- `ProjectManagement/Widgets/DashboardSectionCard.qml`
- `ProjectManagement/Widgets/RegisterCatalogSection.qml`
- `ProjectManagement/Widgets/RegisterFiltersSection.qml`
- `ProjectManagement/Widgets/RegisterMetricsSection.qml`
- `ProjectManagement/Widgets/TimesheetEntriesCard.qml`
- `ProjectManagement/Widgets/WorkspaceStateBanner.qml`
- `ProjectManagement/Widgets/WorkspacePlaceholderPage.qml` and its only consumer `WorkspaceStatusSection.qml`

All listed files had zero active production/dynamic references, remained unused after temporary deregistration, and passed route/offscreen, dialog, shared primitive, and architecture verification before deletion.

### 15.3 Active placeholders/no-ops

- `CollaborationSettingsPopup.qml`: explicitly next-iteration placeholder.
- `CollaborationFilterPopup.qml`: Apply does not modify state.
- `PortfolioWorkspacePage.qml`: Rebalance calls refresh.
- `TimesheetsListPage.qml`: search control has no search handler.
- `ProjectsDocumentsSection.qml` and `ProjectsRisksSection.qml`: active empty/integration states, not fake data.

No hard-coded production demo rows were proven. `App.Mock.MockFactory` uses are mostly null/default models that are replaced by controller data; they should be renamed to neutral empty-model factories later, but are not evidence of fake runtime data.

## 16. Architecture and maintainability findings

Largest/cohesion hotspots:

| File | Lines | Reason |
|---|---:|---|
| `TasksTimeEntriesSection.qml` | 1,306 | CRUD, selection, tabs, workflow, period, approval, lock, and summaries |
| `scheduling_workspace_controller.py` | 762 | selectors, tabs, state, properties, paging, calculations, detail, mutations |
| `tasks_workspace_controller.py` | 704 | facade over many task subdomains and QML signals |
| `PortfolioDetailPanel.qml` | 594 | many governance sections and view mappings |
| `TasksWorkspacePage.qml` | 584 | route/page orchestration plus all action routing |
| `pm_task_list_controller.py` | 575 | list state and mutation surface |
| `portfolio_workspace_controller.py` | 554 | global portfolio state and multiple workflows |
| `DashboardChartCard.qml` | 535 | rendering variants in one component |
| `SchedulingDetailPanel.qml` | 529 | eight schedule detail domains |
| `ProjectsWorkspaceController` | 500 | list/detail/import/export/resources/state |
| `TasksDialogHost.qml` | 478 | nine dialog workflows |

Size alone is not the split criterion. The recommended split boundary is independently testable responsibility while preserving the existing QML facade.

Other structural problems:

- `ProjectManagement.Dialogs` mixes five capability owners.
- `ProjectManagement.Widgets` mixes active shared primitives, capability-specific widgets, and stale placeholders.
- QML packages combine URI imports and many local relative aliases, increasing move risk.
- Empty `components`, `detail`, `dialogs`, or `sections` module folders exist in some workspaces.
- QML state objects sometimes duplicate controller filtering and row construction, especially Collaboration.
- Local project selection is represented and serialized differently by multiple controllers.

## 17. Ranked findings

### P0

No proven P0 UI issue. Service/API authorization and tenancy remain the enforcement boundary; this audit found no QML path that bypasses them.

### P1

| ID | Evidence and behavior | Impact | Dependency/phase |
|---|---|---|---|
| PM-QML-01 | `DataTable.qml` plus all DB-paginated PM lists sort only loaded rows | Misleading order and wrong cross-page decisions | Query API; query integrity phase |
| PM-QML-02 | Collaboration snapshot/approvals use `limit=200`, then local filter/page | Missing results at scale | Backend query reader; Collaboration phase |
| PM-QML-03 | Timesheet search is inert and project/assignment/period filters do not constrain the review queue | Misleading controls | Reader search/filter contract; Timesheets phase |
| PM-QML-04 | Timesheets does not expose existing add/update/delete time entry or period correction | Core advertised workflow missing | UI/controller wiring exists partly; Timesheets phase |
| PM-QML-05 | Portfolio Rebalance only refreshes | Action label promises a mutation that does not occur | Remove the no-op UI in R1; do not invent a backend command |
| PM-QML-06 | Collaboration Settings and Apply Filter are active no-op/placeholder controls | Erodes trust | UI-only removal until contracts exist |
| PM-QML-07 | Ten flat PM drawer destinations and no synchronized project context | High navigation cost and cross-workspace context errors | PM context contract; navigation phase |
| PM-QML-08 | Fixed 220 rail plus non-overflow action row at 1024 | Actions/content can become unusable | Shared responsive primitives |
| PM-QML-09 | Finance UI is primarily read-only while canonical commands/projections exist | Modern backend cannot be operated from desktop | Finance interaction phases |
| PM-QML-10 | Capability presentation is six flags and fail-open on errors | UI advertises denied actions; poor permission UX | Deny-safe capability projection |

### P2

- PM-QML-11: large mixed-responsibility QML/controller files increase regression cost.
- PM-QML-12: Portfolio's fixed bottom panel compresses multiple full workflows.
- PM-QML-13: repeated tab, filter, project-selector, and list-page composition creates inconsistent interaction.
- PM-QML-14: Finance actuals/commitments use fixed 50-row reads in workspace construction.
- PM-QML-15: local controller states persist independently and have no route/deep-link synchronization.
- PM-QML-16: PM shared modules contain capability-specific and likely dead types.
- PM-QML-17: QML `App.Mock` naming obscures that most values are empty/default models.
- PM-QML-18: Resources lacks department/site list filters despite enterprise scope fields.

### P3

- PM-QML-19: numeric dialog widths bypass existing width tiers.
- PM-QML-20: local custom controls lack accessibility semantics and tooltips.
- PM-QML-21: no breadcrumbs or direct deep-link model for portfolio -> project -> task.
- PM-QML-22: icon vocabulary is semantic but locally assembled without PM-level action policy.

## 18. Technical and redesign constraints

- Preserve service/API tenancy and RBAC enforcement; QML capability state is presentation only.
- Do not introduce client-side filtering over partial pages or bounded global snapshots.
- Do not make a UI snapshot/read model authoritative. It must remain disposable and rebuildable.
- Preserve Accounting ownership of invoices, receivables, payments, tax, and statutory ledger truth.
- Keep inventory/procurement integrations behind desktop capability contracts and shell routing; no direct package imports.
- Preserve current QML-facing controller names during structural moves.
- Add a shared project context only after a controller contract defines synchronization, opt-out, lifecycle, and tenant/organization reset behavior.
- Treat 1024x768 as a supported compact desktop, not a scaled-down wide layout.
- Remove or hide no-op controls before adding visual sophistication.

## 19. Direct answers and approved R0.1 decisions

1. Current architecture: technically functional, but product navigation and shared state are not coherent enough for scale.
2. Current navigation: too flat; drawer-level destinations mix distinct scopes.
3. Chrome: excessive on detail pages at compact width; Portfolio also has excessive vertical panel chrome.
4. Hardest pages to use: Portfolio, Timesheets, and narrow-width Financials/Tasks detail.
5. Hardest pages to maintain: Tasks time, Scheduling controller/detail, Portfolio controller/detail, Tasks page/dialog host.
6. God QML: `TasksTimeEntriesSection`, `PortfolioDetailPanel`, `TasksWorkspacePage`, `SchedulingDetailPanel`, `TasksDialogHost`.
7. God Python facades: Scheduling, Tasks, task list, Portfolio, Projects.
8. Inconsistent models: list/full-detail, tab consoles, and fixed bottom panel all compete; inspectors are absent.
9. Fake/dead controls: Rebalance, Collaboration Settings/Apply Filter, Timesheet search; likely dead files are listed above.
10. Backend capability missing from UI: Timesheet CRUD/correction and much of Finance command/profitability/billing flow.
11. Finance alignment: read alignment is good; interaction alignment is incomplete.
12. Project context: visible but duplicated and inconsistent.
13. Persistent project context: approved as explicit controller-owned pinning; implementation waits for the real PM context contract and is never faked in QML.
14. Inspector candidates: Projects, Tasks, Resources, and Register on wide screens.
15. Full detail candidates: Project, Task, Resource, Register entry, scheduling activity, and portfolio decision/item.
16. Dialog candidates: bounded create/edit/lifecycle/assignment/dependency/baseline commands.
17. Query policy: server search/filter/page/sort for global lists; local only for complete selected-entity collections.
18. Shared adoption: responsive context toolbar, inspector, permission state, query-aware table, width tokens, existing detail/dialog primitives.
19. PM-specific primitives: project context bar, PM list-detail shell, schedule canvas shell, finance command section shell.
20. Restructure before redesign: yes, but only the limited behavior-preserving R0.5 scope in the restructure plan.

Approved R0.1 decisions:

1. Use six PM capability groups: Overview, Portfolio, Work, People & Time, Finance, and Governance.
2. Prefer one canonical Project Management module/workspace route with PM-local navigation. Keep the ten current route IDs only as migration/deep-link compatibility routes until dependencies are removed. Do not create six unrelated global drawer entries unless a proven shell constraint makes the unified route impossible.
3. Active project is explicitly pinned. Project row selection/opening does not silently alter global PM context. Planning and Finance require explicit project context. "All projects" remains capability- and query-contract-dependent.
4. Timesheets defaults to My Time for users with personal time-entry capability. Reviewer-only users may default to Review Queue.
5. Remove the current Portfolio Rebalance no-op UI. Redesign does not invent a backend implementation.
6. Use the approved Finance intent hierarchy and phased command rollout while preserving Accounting ownership of statutory and receivables truth.
7. R1 includes query integrity, truthful controls, and deny-safe capability presentation. Fail-open permission presentation is not deferred to final polish.
8. R0.5 is limited to 18 dialog moves, four capability widget moves, eight precise private Python renames, the task presenter utility split, the characterized internal `TasksTimeEntriesSection` split, and guarded dead-QML verification. It does not restructure QML-facing facades, redesign visuals, or change routes.
9. The exact approved baseline deletion count is 17 artifacts: two empty Python files plus up to 15 net empty `qmldir` files. Dead-QML deletion remains conditional on runtime verification and is not included in that baseline count.

## 20. Audit boundary

This document reconstructs the pre-redesign behavior and records the approved R0.1 decisions. The separately authorized R0.5B-R0.5G repository preparation completed on 2026-08-14 without starting R1.

R0.5 changed private names, file ownership, internal QML decomposition, registrations, and proven-dead structural artifacts only. It did not change a route ID, query/filter/sort/page contract, desktop API, QML-facing facade, product interaction, or visual design. The exact implementation and regression evidence is maintained in `project_management_ui_repository_restructure_plan.md`.

## 21. R0.5 audit reconciliation

- The ten audited PM route IDs remain registered and load offscreen.
- `ProjectManagement.Dialogs` was removed after all 18 dialogs moved to capability ownership.
- `ProjectManagement.Widgets` now retains only the active shared `RecordListCard`; four active capability widgets moved and nine dead widget files were proven unused and deleted.
- `TasksTimeEntriesSection` remains the consumed root type and now delegates to five private same-directory children behind characterization coverage.
- All 23 guarded QML candidates passed deregistration, static-reference, route, dialog, shared primitive, and architecture gates before deletion; none were retained.
- The broad PM comparison is 188 passed and the same 13 pre-existing failures recorded before R0.5. No R0.5 regression remains.
- R1 findings and priorities in this audit remain open. The fresh baseline and
  post-R0.5 query map are recorded below before implementation begins.

## 22. R1.1 query-integrity baseline

The R1 baseline was rerun against the post-R0.5 working tree on 2026-08-14.
No R1 production change had been made when these results were captured.

| Gate | Result | Classification |
|---|---:|---|
| Broad focused PM comparison | 188 passed, 13 failed | Same known pre-R1 failures |
| PM route/QML offscreen smoke | 44 passed | Pass |
| Adapter, pagination, and event tests | 75 passed | Pass |
| Dashboard/Portfolio performance tests | 4 passed | Pass |
| Dashboard performance sample | 0.132 s, 91 SQL statements | Within existing gate |
| Portfolio performance sample | 0.092 s, 68 SQL statements | Within existing gate |
| `qmllint` | Unavailable in `pmenv` | Tooling limitation, unchanged |
| Full repository suite | Not run | Focused baseline is the comparison gate |

The 13 known failures remain outside R1 changes: one Projects test fixture uses
a forbidden binary float for budget, seven Scheduling baseline lifecycle tests
expect the former `ValueError`/clamping behavior rather than current Pydantic
validation, and five Scheduling constraint-validator tests expect violations
that the current validator does not produce. They are baseline failures, not an
acceptable reason to weaken R1 tests.

## 23. R1.1 current query/control map

Classification vocabulary:

- **ASQ**: authoritative server query; scope, filtering/count, and paging occur
  before the result page is materialized.
- **VCC**: valid client complete-data operation; the client owns a deliberately
  complete selected-entity or bounded analytical set.
- **PCC**: partial/capped client operation presented as a larger collection.
- **PLACEHOLDER**: visible affordance without the stated backend behavior.
- **UNSUPPORTED**: no current contract exists and no control should claim it.

All new or changed R1 readers must retain explicit tenant and organization
scope plus existing project-level authorization. QML-selected IDs remain query
state, not authorization evidence.

| Capability | Post-R0.5 pipeline | Search / filters | Sort | Page / total | Export / completeness | R1 classification and action |
|---|---|---|---|---|---|---|
| Projects catalog | `ProjectsListPage` -> `ProjectsWorkspaceController` -> projects presenter/desktop API -> `ProjectQuery.query_catalog_page` -> `ProjectCatalogReader` -> `SqlAlchemyProjectCatalogReader` -> page DTO/model -> `DataTable` | Search and status are SQL-side and authorization-scoped | Reader has fixed name/ID order; table header reorders only loaded page | SQL offset/limit and filtered total | Export walks all matching pages; complete for the same search/status query | Search/filter/page/total/export **ASQ**; visible sort **PCC**. Add allowlisted server sort and controller query state. Site/owner/organization filters remain **UNSUPPORTED**. |
| Tasks catalog | `TasksListPage` -> tasks controller -> tasks presenter/desktop API -> `TaskQuery.query_workspace_page` -> `TaskWorkspaceReader` -> `SqlAlchemyTaskWorkspaceReader` -> page DTO/model -> `DataTable` | Search, status, project, priority band, schedule, and parsed status/priority/progress/start/end/deadline conditions are SQL-side | Reader has fixed project/WBS/order/ID ordering; header reorders one page | SQL offset/limit and filtered total; summary is scoped but intentionally independent of row filters | Export walks all matching pages using the same query definition | Search/filter/page/total/export **ASQ**; visible sort **PCC**. Add allowlisted server sort. Assignee is **UNSUPPORTED**; date predicates already exist through the parsed query contract, not a separate fake filter. |
| Scheduling activity | `SchedulingActivityTimelinePanel` -> scheduling controller/state loader -> scheduling presenter `workspace_builder` -> scheduling engine/desktop API full selected-project schedule -> presenter filter/page -> model -> `DataTable` | Search, status, critical, and delayed are applied to the complete selected-project calculated schedule | Current header reorders only the presenter-produced page | Presenter filters complete schedule, computes total, then slices page | No scalable list export; CPM/baseline/calendar calculations require the complete project graph | Filters/page/total are **VCC**, not DB catalog pagination. Visible sort is **PCC** because it occurs after page slicing. Add authoritative sort state before slicing without changing CPM behavior or the QML-facing facade. |
| Resources catalog | `ResourcesListPage` -> resources controller -> presenter/desktop API -> resource query -> `ResourceCatalogReader` -> `SqlAlchemyResourceCatalogReader` -> page DTO/model -> `DataTable` | Search plus active/category are SQL-side | Fixed active/name/ID order; header reorders one page | SQL offset/limit and filtered total | Export walks all matching pages | Search/filter/page/total/export **ASQ**; visible sort **PCC**. Add allowlisted server sort. Department/site/project filters remain **UNSUPPORTED** until reader support exists. |
| Register catalog | `RegisterListPage` -> register controller -> presenter/desktop API -> `RegisterQuery.query_catalog_page` -> `RegisterCatalogReader` -> `SqlAlchemyRegisterCatalogReader` -> page DTO/model -> `DataTable` | Project, type, status, severity, and search are SQL-side | Fixed severity/overdue/due/title/ID triage order; header reorders one page | SQL offset/limit and filtered total; urgent list is deliberately top five | Export uses the authorized query rather than the visible page | Main catalog controls are **ASQ**; visible sort **PCC**. Add allowlisted server sort while preserving the explicit triage default. Urgent list is a valid bounded **VCC** projection. |
| Timesheet Review Queue | `TimesheetsListPage` -> timesheets controller -> presenter -> desktop API -> `TimesheetService.query_review_queue_page` -> `TimesheetReviewReader` -> `SqlAlchemyTimesheetReviewReader` -> page DTO/model -> `DataTable` | Only status reaches SQL. Workspace project/assignment/period controls belong to the assignment snapshot and do not constrain Review Queue; toolbar search is not a reader parameter | Fixed submitted-at/period/ID order; header reorders one page | SQL offset/limit and total for status/project-authorization scope | No truthful all-results queue export proven | Status/page/total **ASQ**; search, visible project/period/assignee expectations and sort are **UNSUPPORTED/PCC**. Add a typed review query with real resource/employee, project, period/date, search, sort, page, and total semantics derived from the schema. |
| Collaboration | `CollaborationWorkspacePage` -> collaboration controller/presenter -> desktop API `build_snapshot(limit=200)` -> collaboration service/workspace reader plus Platform approvals -> Python builders -> controller-local filter/table models -> QML | Project/team/period/unread and per-panel searches run after the capped snapshot; period is not consistently applied | Table-model sort is local | No authoritative panel paging/count; panel counts are lengths of capped data | Export serializes the currently filtered panel; comments and approvals are capped at 200 | Inbox, Mentions, Activity, Approvals and Team Updates have materially different semantics. Current scalable presentation is **PCC**. Replace the generic snapshot with purpose-specific authorized page readers; presence may remain a deliberately bounded live-status projection. Remove placeholder Settings and fake Apply Filter rather than inventing contracts. |
| Portfolio heatmap and collections | portfolio page -> portfolio controller/presenter -> portfolio desktop API/application readers -> complete authorized heatmap/scenario/intake/dependency facts -> controller heatmap filter/page -> model -> `DataTable` | Heatmap search and intake status are client-side over the returned authorized facts | Header sort is local; no explicit authoritative sort state | Heatmap page/total are controller-computed from the complete facts | Collections are rebuilt snapshots; no arbitrary reader cap was found | Current heatmap search/page/total are **VCC** while the authorized portfolio facts remain complete, but sort must occur before slicing or be disabled. Rebalance is a **PLACEHOLDER** and must be removed. Global KPI totals come from complete reader facts, not the visible page. |
| Dashboard operational tables | dashboard page -> dashboard controller/presenter -> desktop dashboard snapshot -> dashboard application services/builders -> complete or deliberately selected rows -> controller-local search/page -> model -> `DataTable` | Search is local across each materialized operational table | Header sort is local on the visible page | Controller pages materialized rows; counts are row lengths | Selected-project tasks/resources are loaded as complete sets, but critical watchlist and milestones are capped at 8, portfolio upcoming at 20, activity at 24, and approvals at 120 | Some tables are **VCC**; capped watchlist/approval tables become **PCC** when generic search/paging implies completeness. R1 must either provide authoritative collection queries or remove generic paging/search/sort affordances from deliberately bounded summaries. KPI totals must remain independent of table pages. |
| Finance Actuals | Finance page -> financials controller/presenter -> desktop API `list_cost_entries(offset=0, limit=50)` -> cost-entry service/repository -> page DTO -> ledger model -> `DataTable` | Service supports status, but workspace does not expose authoritative collection query state | Header sorts only first 50 | Backend returns offset/limit/total, but workspace always requests offset 0 and renders no pagination | First 50 silently presented as collection | **PCC**. Wire controller-owned page/page-size/total and explicit sorting/filter support appropriate to the repository; do not change Accounting ownership. |
| Finance Commitments | Finance page -> financials controller/presenter -> desktop API `list_commitments(offset=0, limit=50)` -> commitment service/repository -> page DTO -> model -> `DataTable` | No workspace query controls | Header sorts only first 50 | Backend returns offset/limit/total, but workspace always requests first 50 and renders no pagination | First 50 silently presented as collection | **PCC**. Wire authoritative pagination and truthful sort semantics; keep PM as the managerial commitment projection, not procurement/accounting truth owner. |
| Finance configuration/billing pages | Finance controller/presenter -> finance workspace query/billing API -> page metadata -> section-local tables/cards | Existing selected-project query contracts | Repository/application paging exists for configuration lines and billing preparations | Page/page-size/total metadata exists and is controller-driven for supported sections | Selected project scope | Generally **ASQ** where pagination is visible; verify each visible section and mark bounded selector/reference lists **VCC**. Do not broaden command surface in R1. |

### 23.1 Shared `DataTable` evidence

`DataTable.qml` currently defaults `clientSideSorting: true`, owns `sortKey` and
`sortDirection`, and calls `sourceModel.toggleSort()` on every sortable header.
`DynamicTableModel.toggleSort()` then mutates its currently loaded rows. This is
valid only when that model contains the complete collection.

The current repository has 29 PM and 20 non-PM `DataTable` consumer files.
None of the 20 non-PM consumers explicitly declares sorting ownership. R1 must
therefore preserve the current client behavior as the backward-compatible
default and make `server`/`none` opt-in. PM scalable tables will opt in
explicitly; bounded child tables may retain client mode.

### 23.2 R1.1 implementation boundary

The map does not authorize R2 navigation, PM-local destinations,
`ProjectContextBar`, My Time UI, inspectors, visual redesign, facade splitting,
or route migration. All ten current PM route IDs remain compatibility routes.
R1.2 begins only with explicit shared sorting semantics and focused primitive
tests; server-query migrations follow after that contract is stable.

### 23.3 R1.2 closure - explicit sorting ownership

R1.2 is complete. `DataTable.sortingMode` now has three explicit behaviors:

- `client` preserves the legacy complete-collection behavior, including local
  `sortKey`/`sortDirection` mutation and optional `sourceModel.toggleSort()`.
- `server` is intent-only. A header click computes the requested next direction
  and emits `sortRequested(key, direction)` without mutating `sortKey`,
  `sortDirection`, the loaded rows, or the source model. Controller/query state
  remains authoritative and drives the sort indicator through bindings.
- `none` disables sort interaction and indicators. Any invalid explicit
  `sortingMode` also resolves to `none`; a typo can never re-enable page-local
  sorting on a paginated collection.

The default remains bound to the legacy `clientSideSorting` flag, so the 20
existing non-PM consumer files retain client behavior without source changes.
Focused shared-primitive and offscreen workspace verification passes (10 tests),
including a repository-wide compatibility assertion for those non-PM consumers.

### 23.4 R1 core collection sorting implementation

The first authoritative sorting slice is complete:

- Projects, Tasks, Resources, and Register carry normalized semantic sort state
  from QML through controller, presenter, desktop API, application query, read
  contract, and allowlisted SQL expressions. Stable IDs break ties and exports
  retain the same query order.
- Historical defaults remain deliberate: Projects `title asc`, Tasks `WBS asc`,
  Resources active-first catalog order, and Register severity/overdue triage.
  Hidden product defaults do not claim a visible column sort.
- Scheduling sorts the complete filtered calculated project graph before page
  slicing. CPM, diagnostics, critical-path, and other derived projections keep
  their calculation order. Generated Activity ID and constant Calendar columns
  are explicitly non-sortable.
- Unsafe or unknown keys never become SQL. They normalize to the product default.

Cross-page database, presenter/controller, shared primitive, and offscreen QML
coverage is green in the combined R1 gate.

### 23.5 R1 Timesheet Review authoritative query

Timesheet Review now owns a typed criteria contract containing status, search,
project, resource, period-start range, sort, page, and page size. Candidate
periods are matched in SQL, aggregate totals remain period-level, sorting occurs
before offset/limit, and unsafe keys fall back to `submittedAt desc`.

The list-page filter popup no longer presents the unrelated assignment snapshot
controls as queue filters. It exposes explicit review project, resource, and date
range state; toolbar search and table sort are controller/query-owned. Column
labels now match the rendered values, and the multi-project label is explicitly
non-sortable. Database tests prove filter semantics and ordering across pages.

Focused R1 core and Timesheet verification: 45 passed. Collaboration, Portfolio,
Dashboard, Finance collection truthfulness, no-op removal, and deny-safe
capability presentation remain pending in R1.
