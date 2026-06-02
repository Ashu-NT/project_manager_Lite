# Workspace Refactoring Plan — Tasks Pattern Alignment

**Date:** 2026-06-02  
**Branch:** refactor/safe-start  
**Reference pattern:** `src/ui_qml/modules/project_management/qml/workspaces/tasks/`

---

## Target Architecture (per workspace)

```
workspace_name/
├── Workspace.qml                  # thin redirect → WorkspacePage
├── WorkspacePage.qml              # orchestrator: imports state, sub-components
├── WorkspaceState.qml             # ALL model properties, RBAC, lazy-load helpers
├── ColumnConfig.js                # column definition functions (table workspaces only)
├── qmldir                         # module declaration
├── components/
│   ├── ListPage.qml               # list page UI (KPI + toolbar + table + pagination + bulk)
│   ├── FilterPopup.qml            # filter popup
│   ├── ViewsPopup.qml             # saved views popup (where applicable)
│   └── qmldir
├── detail/
│   └── qmldir
├── dialogs/
│   ├── DialogHost.qml             # lazy-loaded dialog orchestrator
│   └── qmldir
└── sections/
    ├── DetailPanel.qml            # detail section panel
    └── qmldir
```

### Key Rules
- `WorkspacePage.qml` should be ≤ 300 lines after refactoring
- `WorkspaceState.qml` contains no UI — pure `Item {}` with properties and functions
- `ColumnConfig.js` provides `baseColumns()`, `applyColumnState()`, `buildColumnState()`, `visibleColumnsForExport()`
- Components import sub-folders with relative paths: `import "components" as Components`
- `pragma ComponentBehavior: Bound` on all QML files that bind `required property`
- No `anchors` inside `Layout`-managed children — use `Layout.preferred*`
- `LazyObjectLoader` for dialog hosts (lazy instantiation)
- `Loader { asynchronous: true }` for detail page (avoids stutter on open)

---

## Progress Status

### Project Management Module

| Workspace | State | ColumnConfig | Folders | ListPage | FilterPopup | DialogHost | DetailPanel | WorkspacePage | Status |
|-----------|:-----:|:------------:|:-------:|:--------:|:-----------:|:----------:|:-----------:|:-------------:|--------|
| **tasks** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **projects** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **resources** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **timesheets** | ✅ | ✅ | ✅ | ✅ | ✅ | — | ✅ | ✅ | **COMPLETE** |
| **financials** | ✅ | ✅ | ✅ | 🔲 | 🔲 | ✅ | ✅ | ✅ | Struct done |
| **register** | ✅ | ✅ | ✅ | 🔲 | 🔲 | — | ✅ | ✅ | Struct done |
| portfolio | 🔲 | 🔲 | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | Folders only |
| scheduling | 🔲 | 🔲 | ✅ | 🔲 | 🔲 | ✅ (moved) | 🔲 | 🔲 | Folders only |
| dashboard | 🔲 | — | ✅ | 🔲 | 🔲 | — | 🔲 | 🔲 | Folders only |
| collaboration | 🔲 | — | ✅ | 🔲 | 🔲 | 🔲 | 🔲 | 🔲 | Folders only |

### Inventory & Procurement Module

| Workspace | State | ColumnConfig | Folders | DialogHost | DetailPanel | WorkspacePage | Status |
|-----------|:-----:|:------------:|:-------:|:----------:|:-----------:|:-------------:|--------|
| **catalog** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **procurement** | ✅ | ✅ | ✅ | ✅ | 🔲 | ✅ | Struct done |
| **reservations** | ✅ | ✅ | ✅ | ✅ | 🔲 | ✅ | Struct done |
| **inventory** | ✅ | ✅ | ✅ | ✅ | 🔲 | ✅ | Struct done |
| **warehouses** | ✅ | ✅ | ✅ | — | 🔲 | ✅ | Struct done |
| dashboard | 🔲 | — | ✅ | — | 🔲 | 🔲 | Folders only |
| movements | 🔲 | 🔲 | ✅ | 🔲 | 🔲 | 🔲 | Folders only |
| pricing | 🔲 | 🔲 | ✅ | 🔲 | 🔲 | 🔲 | Folders only |

### Maintenance Module

| Workspace | State | ColumnConfig | Folders | DialogHost | DetailPanel | WorkspacePage | Status |
|-----------|:-----:|:------------:|:-------:|:----------:|:-----------:|:-------------:|--------|
| **work_orders** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | **COMPLETE** |
| **work_requests** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | Struct done |
| **assets** | ✅ | ✅ | ✅ | ✅ | 🔲 | ✅ | Struct done |
| **preventive** | ✅ | ✅ | ✅ | ✅ | 🔲 | ✅ | Struct done |
| dashboard | 🔲 | — | ✅ | — | 🔲 | 🔲 | Folders only |
| planner | 🔲 | — | ✅ | — | 🔲 | 🔲 | Folders only |
| reliability | 🔲 | — | ✅ | — | 🔲 | 🔲 | Folders only |

### Platform Module

| Workspace | Folders | DialogHost | Sections | Status |
|-----------|:-------:|:----------:|:--------:|--------|
| admin console | ✅ | ✅ (moved) | 🔲 (15+ files) | Folders only |
| control | ✅ | — | 🔲 | Folders only |
| settings | ✅ | — | 🔲 | Folders only |

Legend: ✅ Done | 🔲 Pending | — Not applicable

---

## Phase 2 — Remaining Work

### Priority 1: Extract ListPage components (all "Struct done" workspaces)

For financials, register, work_requests, assets, preventive, procurement, reservations, inventory, warehouses:
- Create `components/<Workspace>ListPage.qml`
- Extract list page UI from WorkspacePage.qml inline code
- Add bulk action bar inside ListPage
- Update WorkspacePage to instantiate `Components.<Workspace>ListPage`
- WorkspacePage shrinks to ~150 lines (state + dialog + list/detail stacks)

### Priority 2: Extract DetailPanel components (same workspaces)

For each workspace where DetailPanel is 🔲:
- The detail sections content is currently inline in WorkspacePage.qml (in the `_detailPageComponent`)
- Extract into `sections/<Workspace>DetailPanel.qml`
- WorkspaceState should contain `lazyLoadDetailSection()` function

### Priority 3: Portfolio + Scheduling (PM) full refactoring

Portfolio — existing section files at workspace root to move to `sections/`:
- `PortfolioDependenciesSection.qml` → `sections/`
- `PortfolioDetailPanel.qml` → `sections/`
- `PortfolioExecutiveSection.qml` → `sections/`
- `PortfolioGovernanceToolbar.qml` → `components/`
- `PortfolioIntakeSection.qml` → `sections/`
- `PortfolioScenariosSection.qml` → `sections/`
- `PortfolioSummaryCard.qml` → `sections/`
- `PortfolioTemplatesSection.qml` → `sections/`
- `PortfolioToolbarSection.qml` → `components/`
- Create `PortfolioWorkspaceState.qml`
- Create `PortfolioColumnConfig.js`

Scheduling — existing files to move:
- `SchedulingDialogHost.qml` → `dialogs/` ✅ done
- `SchedulingBaselineSection.qml` → `sections/`
- `SchedulingCalendarSection.qml` → `sections/`
- `SchedulingDetailPanel.qml` → `sections/`
- `SchedulingMetricsSection.qml` → `sections/`
- `SchedulingPanelFrame.qml` → `sections/`
- `SchedulingScheduleSection.qml` → `sections/`
- `SchedulingTimelinePanel.qml` → `sections/`
- `SchedulingActionBar.qml` → `components/`
- `SchedulingPlanningToolbar.qml` → `components/`
- `SchedulingToolbarSection.qml` → `components/`
- Create `SchedulingWorkspaceState.qml`

### Priority 4: Dashboard workspaces (all modules)

Dashboard workspaces are read-only with no dialogs or detail pages. Minimal refactoring:
- Move section files (`DashboardMetricsSection.qml`, etc.) → `sections/`
- Move panel components → `components/`
- Create `DashboardWorkspaceState.qml` (minimal — just model bindings)
- Update WorkspacePage.qml imports

### Priority 5: Platform workspaces

Admin Console has 15+ section files. Recommended approach:
- Move `Admin*Section.qml`, `Admin*DetailPage.qml` → `sections/`
- Move `AdminNavSidebar.qml` → `components/`
- `AdminDialogHost.qml` → `dialogs/` ✅ done
- Create `AdminWorkspaceState.qml`
- Control, Settings: simpler structure, similar to Priority 4

---

## Files Created / Modified (Phase 1)

### New files (Phase 1):
**PM — projects:** WorkspaceState, ColumnConfig, qmldir, components/{ListPage, FilterPopup, qmldir}, detail/qmldir, dialogs/{DialogHost, qmldir}, sections/{DetailPanel, qmldir}  
**PM — resources:** WorkspaceState, ColumnConfig, qmldir, components/{ListPage, FilterPopup, qmldir}, detail/qmldir, dialogs/{DialogHost, qmldir}, sections/{DetailPanel, qmldir}  
**PM — timesheets:** WorkspaceState, ColumnConfig, qmldir, components/{ListPage, FilterPopup, ViewsPopup, qmldir}, detail/qmldir, dialogs/qmldir, sections/{DetailPanel, qmldir}  
**PM — financials:** WorkspaceState, ColumnConfig, qmldir, components/qmldir, detail/qmldir, dialogs/{DialogHost, qmldir}, sections/{DetailPanel, MetricsSection, qmldir}  
**PM — register:** WorkspaceState, ColumnConfig, qmldir, components/qmldir, detail/qmldir, dialogs/qmldir, sections/{DetailPanel, qmldir}  
**PM — portfolio/scheduling/dashboard/collaboration:** folder structure + qmldir files  
**Maintenance — work_orders:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost, sections/{DetailPanel, FiltersSection}  
**Maintenance — work_requests:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost, sections/DetailPanel  
**Maintenance — assets:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost  
**Maintenance — preventive:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost  
**Maintenance — dashboard/planner/reliability:** folder structure + qmldir files  
**Inventory — catalog:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost, sections/DetailPanel  
**Inventory — procurement:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost  
**Inventory — reservations:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost  
**Inventory — inventory:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs, dialogs/DialogHost  
**Inventory — warehouses:** WorkspaceState, ColumnConfig, qmldir, all subfolders + qmldirs  
**Inventory — dashboard/movements/pricing:** folder structure + qmldir files  
**Platform — admin/control/settings:** folder structure + qmldir files, admin/dialogs/DialogHost  

### Files updated (WorkspacePage.qml imports fixed):
- `projects/ProjectsWorkspacePage.qml` — imports state, components, dialogs, sections
- `resources/ResourcesWorkspacePage.qml` — same
- `timesheets/TimesheetsWorkspacePage.qml` — same
- `financials/FinancialsWorkspacePage.qml` — imports dialogs, sections; updates component refs
- `register/RegisterWorkspacePage.qml` — imports sections; updates component refs
- `work_orders/WorkOrdersWorkspacePage.qml` — imports dialogs, sections; updates component refs
- `work_requests/WorkRequestsWorkspacePage.qml` — imports dialogs, sections
- `assets/AssetsWorkspacePage.qml` — imports dialogs
- `preventive/PreventiveWorkspacePage.qml` — imports dialogs
- `catalog/CatalogWorkspacePage.qml` — imports dialogs, sections; fixes CatalogDetailPanel ref
- `procurement/ProcurementWorkspacePage.qml` — imports dialogs, sections
- `reservations/ReservationsWorkspacePage.qml` — imports dialogs, sections
- `inventory/InventoryWorkspacePage.qml` — imports dialogs, sections
- `warehouses/WarehousesWorkspacePage.qml` — updates import from `../inventory` to `../inventory/dialogs`

### Files deleted (moved to subfolders):
- `projects/ProjectsDetailSection.qml` → `sections/ProjectsDetailPanel.qml`
- `projects/ProjectsDialogHost.qml` → `dialogs/ProjectsDialogHost.qml`
- `resources/ResourcesDetailSection.qml` → `sections/ResourcesDetailPanel.qml`
- `resources/ResourcesDialogHost.qml` → `dialogs/ResourcesDialogHost.qml`
- `resources/ResourcesCatalogSection.qml` → deleted (legacy RecordListCard pattern)
- `resources/ResourcesFiltersSection.qml` → deleted (embedded in ListPage)
- `resources/ResourcesMetricsSection.qml` → deleted (embedded in ListPage)
- `timesheets/TimesheetsDetailSection.qml` → `sections/TimesheetsDetailPanel.qml`
- `timesheets/TimesheetsEntriesSection.qml` → deleted (empty placeholder)
- `timesheets/TimesheetsReviewSection.qml` → deleted (empty placeholder)
- `timesheets/TimesheetsToolbarSection.qml` → deleted (empty placeholder)
- `financials/FinancialsDetailSection.qml` → `sections/FinancialsDetailPanel.qml`
- `financials/FinancialsDialogHost.qml` → `dialogs/FinancialsDialogHost.qml`
- `financials/FinancialsCatalogSection.qml` → deleted (legacy)
- `financials/FinancialsFiltersSection.qml` → deleted (embedded)
- `financials/FinancialsMetricsSection.qml` → `sections/FinancialsMetricsSection.qml`
- `work_orders/WorkOrdersDialogHost.qml` → `dialogs/WorkOrdersDialogHost.qml`
- `work_orders/WorkOrderDetailSection.qml` → `sections/WorkOrderDetailPanel.qml`
- `work_orders/WorkOrdersFiltersSection.qml` → `sections/WorkOrdersFiltersSection.qml`
- `work_orders/WorkOrdersMetricsSection.qml` → deleted (embedded)
- `work_orders/WorkOrdersCatalogSection.qml` → deleted (legacy)
- `work_requests/WorkRequestsDialogHost.qml` → `dialogs/WorkRequestsDialogHost.qml`
- `work_requests/WorkRequestDetailSection.qml` → `sections/WorkRequestDetailPanel.qml`
- `assets/AssetsDialogHost.qml` → `dialogs/AssetsDialogHost.qml`
- `preventive/PreventiveDialogHost.qml` → `dialogs/PreventiveDialogHost.qml`
- `catalog/CatalogDialogHost.qml` → `dialogs/CatalogDialogHost.qml`
- `catalog/CatalogDetailContent.qml` → `sections/CatalogDetailPanel.qml`
- `procurement/ProcurementDialogHost.qml` → `dialogs/ProcurementDialogHost.qml`
- `reservations/ReservationsDialogHost.qml` → `dialogs/ReservationsDialogHost.qml`
- `inventory/InventoryDialogHost.qml` → `dialogs/InventoryDialogHost.qml`

---

## Remaining Risks

1. **QML module cache**: After moving files, QML engine may cache old module locations.
   Clear `~/.cache/qml` or equivalent if workspaces fail to open after refactoring.

2. **Phase 2 workspaces**: Portfolio, Scheduling, Dashboard (all modules), Collaboration,
   Movements, Pricing, Reliability, Planner remain incomplete (folder structure only).
   WorkspaceState.qml and ListPage extraction still pending for these.

3. **Warehouses dialog host path change**: `WarehousesWorkspacePage.qml` now imports from
   `../inventory/dialogs` instead of `../inventory`. This is a runtime-resolved path —
   verify the QML engine correctly resolves it on app start.

4. **Platform workspaces**: Admin Console, Control, Settings use RecordListCard pattern
   (not DataTable). Full Tasks pattern alignment requires separate planning.
   Admin workspace has 15+ section files — move to sections/ before Phase 2.

5. **ListPage extraction pending**: For 9 workspaces (financials, register, work_requests,
   assets, preventive, procurement, reservations, inventory, warehouses) — list page content
   is still inline in WorkspacePage.qml. These work correctly but are not fully extracted.

6. **Financials InsightsSection**: `FinancialsInsightsSection.qml` exists at workspace root.
   Not yet moved to sections/ — add to Phase 2.

---

## Validation Checklist

After each workspace refactoring:
- [ ] Workspace route opens (no QML errors in console)
- [ ] List page renders with KPI strip, toolbar, table
- [ ] Search / filter / export / refresh work
- [ ] Column customizer persists state
- [ ] Pagination works (page change, page size change)
- [ ] Row selection and bulk actions work
- [ ] Detail page opens (covers list page, z:20)
- [ ] Detail page back button returns to list
- [ ] All detail sections lazy-load correctly
- [ ] Detail page actions (Edit/Delete/Status) open correct dialogs
- [ ] Dialog forms submit correctly
- [ ] Error/success InlineMessages appear in both list and detail views
- [ ] No broken imports in QML console
- [ ] No stale qmldir entries
