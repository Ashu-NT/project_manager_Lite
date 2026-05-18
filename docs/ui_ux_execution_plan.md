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

### 2.3 ShellDrawer.qml — Grouped flat navigation
File: `src/ui_qml/shell/qml/ShellDrawer.qml`
-  Remove placeholder developer text ("Migrated QML workspaces register routes here.")
-  Group routes by `groupLabel` using section headers (SectionHeader component)
-  Nav items: flat rows, no border Rectangle per item
-  Selected item: accent left rail (3px) + navSelectedBackground fill + navSelectedText color
-  Hover item: navHoverBackground fill
-  AppIcon on left of each nav row
-  Route title text right of icon
-  Background: navBackground (slightly darker than appBackground)
-  No outer radius/border on the drawer panel

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

## PHASE 4 — Platform Module Workspaces

Representative workspace first, then reuse patterns.

### 4.1 Platform RecordListCard → column-style row list
File: `src/ui_qml/platform/qml/Platform/Widgets/RecordListCard.qml`
-  Replace stacked card delegates with flat horizontal row delegates
-  Use StatusChip for status display
-  Row dividers (AppDivider) between rows
-  Row hover state
-  Row click for selection (additive: selectedItemId + itemSelected signal)
-  Preserve exact existing signals: primaryActionRequested/secondaryActionRequested/tertiaryActionRequested(string itemId)

### 4.2 AdminCatalogPanel.qml — enterprise catalog
File: `src/ui_qml/platform/qml/Platform/Widgets/AdminCatalogPanel.qml`
-  Use PageHeader for title/create action
-  Use FilterBar below header
-  Reduce visual boxing (remove nested borders)

### 4.3 Platform workspace border cleanup
Files: `src/ui_qml/platform/qml/workspaces/**/*.qml`
-  Admin Console workspace
-  Access & Security workspace
-  Approvals workspace (queue/review layout)
-  Audit workspace
-  Settings workspace (config-panel style)

---

## PHASE 5 — Project Management Module Workspaces

### 5.1 Representative workspace: Projects (master-detail)
Files: `src/ui_qml/modules/project_management/qml/workspaces/`
-  Use MasterDetailLayout (SplitView)
-  Left: DataTable or column-row list with search/filter toolbar
-  Right: detail panel with fields, status, actions
-  Consistent PageHeader + FilterBar pattern

### 5.2 Dashboard workspace
-  KPI metric row
-  Two-column insights/alerts layout
-  Dense, executive-friendly

### 5.3 Remaining workspaces (reuse patterns)
-  Tasks, Scheduling, Resources, Financials, Risk, Portfolio, Timesheets

---

## PHASE 6 — Maintenance Module Workspaces

### 6.1 Representative workspace: Preventive (existing tabs preserved)
Files: `src/ui_qml/modules/maintenance/qml/workspaces/planner/`
-  Queue tab: FilterBar + queue list + detail panel + forecast section
-  Plans tab: FilterBar + plan list + plan detail + tasks sub-list
-  Templates tab: FilterBar + template list + detail + steps sub-list
-  Keep existing tab structure, improve spacing/hierarchy/borders

### 6.2 Assets workspace (master-detail)
-  Asset list left, asset detail right
-  Maintenance history below

### 6.3 Remaining workspaces
-  Dashboard, Work Requests, Work Orders, Reliability, Task Templates

---

## PHASE 7 — Inventory & Procurement Module Workspaces

### 7.1 Representative workspace: Catalog (master-detail)
Files: `src/ui_qml/modules/inventory_procurement/qml/workspaces/catalog/`
-  Category list + item list + item detail
-  MasterDetailLayout SplitView

### 7.2 Procurement workspace
-  Requisitions + Purchase Orders
-  Selected detail + lines + receipts
-  Status filters

### 7.3 Remaining workspaces
-  Dashboard, Inventory, Reservations, Pricing

---

## PHASE 8 — Cross-cutting Border & Density Cleanup

### 8.1 Global border audit
-  Remove `border.color: Theme.AppTheme.border` from parent layout containers
-  Remove radiusLg from every nested container
-  Replace heavy borders with surface contrast + spacing
-  Audit all workspaces for triple-nested bordered Rectangles

### 8.2 WorkspaceStateBanner improvements
Files: `**/Widgets/WorkspaceStateBanner.qml` (maintenance + inventory versions)
-  Use InlineMessage component
-  Consistent error/loading/feedback display

### 8.3 Module RecordListCards — visual improvements
Files:
- `src/ui_qml/modules/maintenance/qml/Maintenance/Widgets/RecordListCard.qml`
- `src/ui_qml/modules/inventory_procurement/qml/InventoryProcurement/Widgets/RecordListCard.qml`
-  Apply same column-row visual style as platform version
-  Use StatusChip for status display
-  Keep existing API (passes var itemData, not string)

### 8.4 Density mode
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

## Files Changed So Far

### New files created
- `src/ui_qml/shared/qml/App/Controls/SecondaryButton.qml`
- `src/ui_qml/shared/qml/App/Widgets/StatusChip.qml`
- `src/ui_qml/shared/qml/App/Icons/qmldir`
- `src/ui_qml/shared/qml/App/Icons/AppIcon.qml`

### Modified files
- `src/ui_qml/shared/qml/App/Theme/AppTheme.qml` — radii + type scale
- `src/ui_qml/shared/qml/App/Controls/qmldir` — +SecondaryButton
- `src/ui_qml/shared/qml/App/Widgets/qmldir` — +StatusChip

---

## Execution Order (current session)

1.  AppTheme.qml — radii + type scale
2.  SecondaryButton.qml
3.  StatusChip.qml
4.  AppIcon.qml (Unicode fix needed)
5.  AppTheme.qml — expand full token set (Phase 1.1 remaining)
6.  New shared components — AppDivider, SectionHeader, EmptyState, PageHeader, FilterBar, InlineMessage (Phase 1.5)
7.  MasterDetailLayout, WorkspaceFrame refactor (Phase 1.6 + 2.5)
8.  MainWindow.qml — full-bleed shell (Phase 2.1)
9.  ShellHeader.qml — enterprise header (Phase 2.2)
10.  ShellDrawer.qml — grouped flat nav (Phase 2.3)
11.  Platform RecordListCard — column-row style (Phase 4.1)
12.  DataTable.qml framework (Phase 3.1)
