# Enterprise UI/UX Execution Plan
# Source spec: docs/ux_design.md

Status legend:  Done |  In Progress |  Pending

---

## PHASE 1 — Foundation: Theme Tokens + Core Shared Components

Goal: Every subsequent change draws from a complete, correct token set and has reusable
primitive components to build on.

### 1.1 AppTheme.qml — Expand token set
File: `src/ui_qml/shared/qml/App/Theme/AppTheme.qml`
-  radiusSm: 4, radiusMd: 6, radiusLg: 10 (reduced from mobile scale)
-  titleSize: 20, sectionSize: 16, captionSize: 11 added
-  Add: surfaceRaised, surfaceSunken, hoverSurface, selectedSurface
-  Add: subtleBorder, divider, focusBorder
-  Add: navBackground, navHoverBackground, navSelectedBackground, navSelectedText
-  Add: info color (#0A66A8 tint / separate info token)
-  Add: spacingXl: 32, headerSize: 24, sectionTitleSize: 13
-  Add: density tokens — compactRowHeight: 32, normalRowHeight: 40, toolbarHeight: 40, sidebarRowHeight: 36

### 1.2 AppIcon.qml — Fix Unicode codepoints
File: `src/ui_qml/shared/qml/App/Icons/AppIcon.qml`
-  File created with Segoe MDL2 Assets icon map
-  Verify Unicode codepoints render correctly (write via Python to embed literals)
-  Expand icon set: filter, notifications, user, workflow, history, comments, attachments, close

### 1.3 SecondaryButton.qml
File: `src/ui_qml/shared/qml/App/Controls/SecondaryButton.qml`
-  Created — outline style, accent border 1.5px, transparent fill, danger variant

### 1.4 StatusChip.qml
File: `src/ui_qml/shared/qml/App/Widgets/StatusChip.qml`
-  Created — semantic color variants: success/info/warning/danger/neutral
-  Auto-detects variant from normalized status string

### 1.5 New shared primitive components
All under: `src/ui_qml/shared/qml/App/Widgets/`

-  AppDivider.qml — thin horizontal rule using Theme.AppTheme.divider color
-  SectionHeader.qml — uppercase muted label used as group divider in sidebars/forms
-  EmptyState.qml — centered icon + title + subtitle for zero-data states
-  PageHeader.qml — workspace page title + subtitle + optional action slot (right side)
-  InlineMessage.qml — compact info/warning/error/success banner strip
-  FilterBar.qml — horizontal toolbar: search field + filter chips + right-side action buttons
-  LoadingOverlay.qml — translucent overlay with BusyIndicator for workspace loading states

Update `src/ui_qml/shared/qml/App/Widgets/qmldir` for all new components.

### 1.6 New shared layout components
Under: `src/ui_qml/shared/qml/App/Layouts/`

-  MasterDetailLayout.qml — SplitView: left list area | right detail area, resizable
-  SplitWorkspace.qml — SplitView wrapper with stored splitter position

Update `src/ui_qml/shared/qml/App/Layouts/qmldir`.

---

## PHASE 2 — Shell Redesign

Goal: Clean enterprise shell — full-bleed header, flat grouped sidebar, no outer margins boxing the UI.

### 2.1 MainWindow.qml — Full-bleed layout
File: `src/ui_qml/shell/qml/MainWindow.qml`
-  Remove outer `anchors.margins: marginLg` — shell fills the window edge-to-edge
-  Remove the Rectangle border wrapper around the workspace Loader
-  Header flush at top (no margin above/beside it)
-  Sidebar and workspace content sit flush below header
-  Workspace Loader fills its area cleanly (no inner border rectangle)

### 2.2 ShellHeader.qml — Enterprise app header
File: `src/ui_qml/shell/qml/ShellHeader.qml`
-  Height: 48px (compact enterprise density)
-  Background: Theme.AppTheme.surface with bottom divider line (not accent fill)
-  Left: app logo/name (bold, accent color text)
-  Center: current workspace title (secondary text, reads from shellModel.currentRouteTitle)
-  Right: search placeholder icon | notifications placeholder | user display name + avatar initial
-  No heavy rounded rectangle, no full-accent background

### 2.3 ShellDrawer.qml — Enterprise collapsible sidebar  [DONE]
File: `src/ui_qml/shell/qml/ShellDrawer.qml`
-  Full enterprise sidebar redesign: collapsible (48px icon-only / 240px expanded)
-  Animated width with NumberAnimation (180ms, OutCubic)
-  Module-level grouping using moduleLabel (not groupLabel)
-  Module section headers with collapse/expand toggle (chevron)
-  Search bar filters navigation items
-  Nav items: flat rows with accent left-rail for selection, hover state
-  AppIcon per route (40-icon map in iconForRoute function)
-  ToolTip on icon-only collapsed mode showing route title
-  Bottom collapse toggle button
-  Background: navBackground

### 2.4 HomeWorkspace.qml — Enterprise home
File: `src/ui_qml/shell/qml/HomeWorkspace.qml`
-  Remove placeholder "QML shell ready" developer text
-  Show platform welcome + module navigation tiles
-  Use PageHeader component for title area
-  Use MetricCard for route summary

### 2.5 WorkspaceFrame.qml — Clean frame
File: `src/ui_qml/shared/qml/App/Layouts/WorkspaceFrame.qml`
-  Remove Rectangle border/radius wrapper — frame is transparent
-  Use PageHeader component for title/subtitle
-  Content area fills remaining space with correct padding

---

## PHASE 3 — Enterprise Table Framework

Goal: A reusable DataTable component that replaces per-module card lists with dense operational grids.

### 3.1 DataTable.qml
File: `src/ui_qml/shared/qml/App/Widgets/DataTable.qml`
-  Properties: columns (list), rows (list), selectedRowId, sortKey, sortDirection
-  Column metadata: key, label, width, alignment, sortable, visible
-  Sticky column headers with sort indicators
-  Row hover highlight (hoverSurface)
-  Selected row accent (selectedSurface + accent left border)
-  Compact row height: Theme.AppTheme.compactRowHeight (32px default)
-  StatusChip rendered for status columns
-  Keyboard navigation: Up/Down arrows, Enter to select
-  Virtualized via ListView (not Repeater)
-  Row click emits: rowSelected(string rowId)
-  Double-click emits: rowActivated(string rowId)

### 3.2 TableToolbar.qml
File: `src/ui_qml/shared/qml/App/Widgets/TableToolbar.qml`
-  Left: search TextField (debounced, emits searchChanged signal)
-  Middle: filter chips / slot for custom filters
-  Right: Refresh | Export | Create (SecondaryButton / PrimaryButton)
-  Height: Theme.AppTheme.toolbarHeight

### 3.3 TableColumnCustomizer.qml
File: `src/ui_qml/shared/qml/App/Widgets/TableColumnCustomizer.qml`
-  Popup/dialog with column checklist
-  Show/hide columns
-  Reset to defaults
-  Apply button

Update `src/ui_qml/shared/qml/App/Widgets/qmldir` for all new components.

---

## PHASE 4 — Platform Module Workspaces  [COMPLETE]

Representative workspace first, then reuse patterns.

### 4.1 Platform RecordListCard → column-style row list  [DONE]
File: `src/ui_qml/platform/qml/Platform/Widgets/RecordListCard.qml`
-  Replace stacked card delegates with flat horizontal row delegates
-  Use StatusChip for status display
-  Row dividers (AppDivider) between rows
-  Row hover state
-  Row click for selection (additive: selectedItemId + itemSelected signal)
-  Preserve exact existing signals: primaryActionRequested/secondaryActionRequested/tertiaryActionRequested(string itemId)

### 4.2 AdminCatalogPanel.qml — enterprise catalog  [DONE]
File: `src/ui_qml/platform/qml/Platform/Widgets/AdminCatalogPanel.qml`
-  Use PageHeader for title/create action
-  Use FilterBar below header
-  Reduce visual boxing (remove nested borders)

### 4.3 Platform workspace border cleanup  [DONE]
Files: `src/ui_qml/platform/qml/workspaces/**/*.qml`
-  Admin Console workspace — OverviewSectionCard, DocumentDetailPanel, AdminSupportSection, AccessSecurityPanel cleaned
-  All platform widgets: Item root, no outer borders

---

## PHASE 5 — Project Management Module Workspaces  [COMPLETE]

### 5.1 PM Widgets  [DONE]
-  RecordListCard — flat row delegates, StatusChip, hover/selection states
-  DashboardChartCard — Item root, no outer border, canvas chart preserved
-  DashboardSectionCard — Item root, flat rows with dividers, StatusChip
-  DashboardPanelCard — Item root, flat rows with dividers, toneColor function
-  TimesheetEntriesCard — Item root, no outer border
-  RegisterDetailSection — Item root, StatusChip, no field card borders
-  RegisterFiltersSection — Item root, filter controls only

### 5.2 PM Workspace sections  [DONE]
-  ProjectsWorkspacePage + ProjectsDetailSection — live page owns KPI/table/filter/detail composition; obsolete local metrics/filter/catalog helpers removed
-  TasksWorkspacePage + TasksDetailPanel — live page owns KPI/table/filter/detail composition; obsolete local metrics/filter/catalog/detail helpers removed
-  DashboardSelectionBar — Item root
-  All 19 remaining workspace sections (scheduling, resources, portfolio, financials, timesheets, collaboration, etc.) — Item root via batch transform

---

## PHASE 6 — Maintenance Module Workspaces  [COMPLETE]

### 6.1–6.3 All workspace sections  [DONE]
-  9 workspace files (detail sections + filter sections) — Item root
-  4 detail sections — Item root, StatusChip (AssetLibraryDetailSection, PreventiveDetailSection, WorkOrderDetailSection, WorkRequestDetailSection)
-  All borders removed via batch transform

---

## PHASE 7 — Inventory & Procurement Module Workspaces  [COMPLETE]

### 7.1–7.3 All workspace sections  [DONE]
-  14 workspace files — Item root via batch transform
-  7 detail sections — Item root, StatusChip (ReservationDetailSection, RequisitionDetailSection, PurchaseOrderDetailSection, StoreroomDetailSection, BalanceDetailSection, ItemDetailSection, CategoryDetailSection)

---

## PHASE 8 — Cross-cutting Border & Density Cleanup

### 8.1 Global border audit  [DONE]
-  Removed all `border.color: Theme.AppTheme.border` across entire codebase (0 remaining)
-  Removed all manual status chips (Rectangle+accentSoft+accent border → StatusChip)
-  Covered: all workspace sections, all dialogs (25 files), dialog hosts, shared widgets, LoginWindow

### 8.2 WorkspaceStateBanner improvements  [DONE]
Files: `**/Widgets/WorkspaceStateBanner.qml` (maintenance + inventory versions)
-  Converted to use InlineMessage component

### 8.3 Module RecordListCards — visual improvements  [DONE]
Files:
- `src/ui_qml/modules/maintenance/qml/Maintenance/Widgets/RecordListCard.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Widgets/RecordListCard.qml`
- `src/ui_qml/modules/project_management/qml/ProjectManagement/Widgets/RecordListCard.qml`
-  All converted to flat row style with StatusChip and hover/selection states

### 8.4 Density mode  [PENDING - future enhancement]
-  Add density preference to ShellContext or settings infrastructure
-  Expose via AppTheme density tokens
-  Compact (default) / Comfortable / Spacious

---

## PHASE 9 — Validation

-  `python -m compileall -q src` — no syntax errors
-  `pytest src/tests/architecture` — architecture guardrails pass
-  `pytest src/tests/platform` — platform tests pass
-  `pytest src/tests/project_management` — PM tests pass
-  `pytest src/tests/inventory_procurement` — inventory tests pass
-  `pytest src/tests/maintenance` — maintenance tests pass
-  QML offscreen loading test if available

---

## Completed Phases Summary

**Phases 1–8.3 are complete.** All QML files across the codebase have been migrated to the flat enterprise design system:
- Zero `border.color: Theme.AppTheme.border` remaining in the codebase
- Zero manual status chips (all replaced with `StatusChip`)
- All workspace section root elements converted from `Rectangle` to `Item`
- Enterprise sidebar with collapsible behavior, module grouping, search, and per-route icons
- All shared widgets, platform widgets, PM/Maintenance/Inventory widgets and workspace sections updated
- All dialogs cleaned of border decorations

**Remaining:**
- Phase 8.4 (density mode) — future enhancement
- Phase 9 (validation) — run when PySide6 environment is available
