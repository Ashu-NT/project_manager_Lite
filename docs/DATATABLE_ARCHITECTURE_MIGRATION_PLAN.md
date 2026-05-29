# Enterprise DataTable Architecture Migration Plan

**Status:** Phase 1 Complete — Discovery & Analysis  
**Next:** Awaiting approval to begin Phase 2 — Pilot Implementation  
**Date:** 2026-05-29  
**Author:** Claude Code (architecture assessment)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture](#current-architecture)
3. [Target Architecture](#target-architecture)
4. [Reusable Infrastructure Inventory](#reusable-infrastructure-inventory)
5. [Existing Model Infrastructure](#existing-model-infrastructure)
6. [Full Module Inventory](#full-module-inventory)
7. [Dependency Map](#dependency-map)
8. [Performance Bottlenecks](#performance-bottlenecks)
9. [Files to Modify](#files-to-modify)
10. [Migration Strategy & Sequence](#migration-strategy--sequence)
11. [Pilot Workspace Recommendation](#pilot-workspace-recommendation)
12. [Risks & Mitigations](#risks--mitigations)
13. [Progress Tracker](#progress-tracker)

---

## Executive Summary

The platform already has enterprise-grade table infrastructure (`DynamicTableModel`, `DataTable`, `TableToolbar`, `TablePaginationBar`, etc.). The problem is **where the model lives**: it is instantiated inside `DataTable.qml` and fed via large `QVariantList` array transfers across the Python–QML boundary.

The migration objective is to **move model ownership to Python controllers**, so:

- Python owns the `DynamicTableModel` instance and calls `_set_rows()` directly
- QML receives a `QObject` reference, not a giant array
- Selection, sorting, filtering, pagination remain Python-owned state
- `DataTable.qml` gains a `sourceModel` property to accept a pre-built Python model
- All existing components (`TableToolbar`, `BulkActionBar`, `ContextualActionToolbar`, etc.) are preserved without visual changes

**Scale:** 46 controllers · 43 presenters · 68 DataTable instances · 25 workspace QML files

---

## Current Architecture

```
Repository / Service
        ↓
Presenter.build_workspace_state()
   → Returns WorkspaceState with list[dict] rows
        ↓
Controller stores dict: {"items": [...], "emptyState": "..."}
   → Exposes via @Property("QVariantList", notify=itemsChanged)
        ↓
QML binding: rows: controller.items.items || []
   → Full Python list crosses the QML bridge as QVariantList
        ↓
DataTable.qml receives var rows: [...]
   → Creates DynamicTableModel internally
   → Assigns rows to internal model
        ↓
TableView renders cells from DynamicTableModel
```

**What this means:**
- Every refresh crosses the Python→QML bridge with the full dataset
- QML is responsible for client-side sorting (creates new array copies)
- Scheduling workspace does filtering inside QML (`_filterRows()` called on every binding)
- Selection state is stored in controller but triggers full model resets via `selectedRowIds` rebind

---

## Target Architecture

```
Repository / Service
        ↓
Presenter.build_workspace_state()
   → Returns WorkspaceState with list[dict] rows
        ↓
Controller owns DynamicTableModel instance
   self._table_model._set_rows(rows)       ← Python-to-Python, no bridge crossing
   self._table_model._set_columns(cols)
        ↓
Controller exposes:
   @Property(QObject) tableModel → self._table_model
   @Property(int)     page
   @Property(int)     pageSize
   @Property(int)     totalCount
   @Property(list)    selectedIds
        ↓
QML binding: sourceModel: controller.tableModel
   → QObject reference only crosses bridge (no data payload)
        ↓
DataTable.qml uses model directly in TableView
        ↓
TableView renders cells (unchanged delegate logic)
```

**Benefits:**
- Zero large array bridge crossings on refresh
- Sorting/filtering in Python → no QML array copies
- Selection state updates (`selectedIds` only) → no model reset
- True server-side pagination ready (only send page N, not all rows)
- Lazy loading ready (append rows without full reset)

---

## Reusable Infrastructure Inventory

All components below **must be preserved**. No visual redesign. No replacement.

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| `DataTable` | `src/ui_qml/shared/qml/App/Widgets/DataTable.qml` | ✅ Active | Needs `sourceModel` property added |
| `TableToolbar` | `src/ui_qml/shared/qml/App/Widgets/TableToolbar.qml` | ✅ Active | No change needed |
| `TablePaginationBar` | `src/ui_qml/shared/qml/App/Widgets/TablePaginationBar.qml` | ✅ Active | No change needed |
| `BulkActionBar` | `src/ui_qml/shared/qml/App/Widgets/BulkActionBar.qml` | ✅ Active | No change needed |
| `BulkChangePropertyPopup` | `src/ui_qml/shared/qml/App/Widgets/BulkChangePropertyPopup.qml` | ✅ Active | No change needed |
| `ContextualActionToolbar` | `src/ui_qml/shared/qml/App/Widgets/ContextualActionToolbar.qml` | ✅ Active | No change needed |
| `TableColumnCustomizer` | `src/ui_qml/shared/qml/App/Widgets/TableColumnCustomizer.qml` | ✅ Active | No change needed |
| `SectionDetailPage` | `src/ui_qml/shared/qml/App/Widgets/SectionDetailPage.qml` | ✅ Active | No change needed |
| `ActivityFeed` | `src/ui_qml/shared/qml/App/Widgets/ActivityFeed.qml` | ✅ Active | No change needed |
| `KpiStrip` | `src/ui_qml/shared/qml/App/Widgets/KpiStrip.qml` | ✅ Active | No change needed |
| `StatusChip` | `src/ui_qml/shared/qml/App/Widgets/StatusChip.qml` | ✅ Active | No change needed |
| `InlineMessage` | `src/ui_qml/shared/qml/App/Widgets/InlineMessage.qml` | ✅ Active | No change needed |

---

## Existing Model Infrastructure

### `DynamicTableModel` — Already Enterprise-Grade

**File:** `src/ui_qml/shared/models/data_table_model.py`  
**Parent:** `QAbstractTableModel`  
**Import:** `App.Models 1.0`

**Roles already implemented:**

| Role Constant | QML Name | Purpose |
|---------------|----------|---------|
| `Qt.DisplayRole` | `display` | Formatted cell string |
| `RawValueRole` | `rawValue` | Unformatted raw value |
| `RowDataRole` | `rowData` | Full row dict |
| `ColumnDataRole` | `columnData` | Full column definition |
| `RowIdRole` | `rowId` | Row ID string |
| `ColumnKeyRole` | `columnKey` | Column field key |
| `ColumnLabelRole` | `columnLabel` | Column header text |
| `ColumnTypeRole` | `columnType` | "text" \| "status" \| "progress" |
| `RowIndexRole` | `rowIndex` | Row index integer |
| `ColumnIndexRole` | `columnIndex` | Column index integer |
| `SortableRole` | `sortable` | Can sort by this column |
| `MinWidthRole` | `minWidth` | Minimum pixel width |
| `FlexRole` | `flex` | Proportional fill weight |
| `AlignRole` | `align` | "left" \| "center" \| "right" |
| `EditableRole` | `editable` | Cell is editable |
| `IsRequiredRole` | `isRequired` | Field is required |
| `ColumnVisibleRole` | `columnVisible` | Column is visible |

**Roles needed for full target spec (to add):**

| Role | Purpose |
|------|---------|
| `StatusRole` | Row-level status for row highlighting |
| `MetadataRole` | Arbitrary per-row metadata dict |
| `WidthRole` | Explicit pixel width override |

**Current API:**
```python
# Already works
model.rows    = [...]   # sets rows, emits beginResetModel/endResetModel
model.columns = [...]   # sets columns, rebuilds vis_cols

# Internal setter (can be called from Python directly)
model._set_rows(list_of_dicts)
model._set_columns(list_of_col_defs)
```

**What this model is missing for the migration:**
- No `set_rows()` public method (use `_set_rows()` or assign `model.rows = ...`)
- No partial update path (currently always does `beginResetModel`)
- No selection awareness (selection stays in controller — correct separation)

---

## Full Module Inventory

### Summary Statistics

| Metric | Count |
|--------|-------|
| Total workspace controllers | 46 |
| Total presenters | 43 |
| Total DataTable instances | 68 |
| QML workspace files with DataTable | 25 |
| Anti-pattern `_filterRows()` calls | 7 (all in Scheduling) |
| Modules | Platform, PM, Inventory, Maintenance |

---

### Platform Workspaces

| Workspace | Controller File | Presenter File | Row Source | Tables | Pagination | Search |
|-----------|----------------|----------------|-----------|--------|-----------|--------|
| Organizations | `platform/controllers/admin/` | `platform/presenters/organization_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Sites | `platform/controllers/admin/` | `platform/presenters/site_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Departments | `platform/controllers/admin/` | `platform/presenters/department_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Employees | `platform/controllers/admin/` | `platform/presenters/employee_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Users | `platform/controllers/admin/` | `platform/presenters/user_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Parties | `platform/controllers/admin/` | `platform/presenters/party_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Documents | `platform/controllers/admin/` | `platform/presenters/document_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Structures | `platform/controllers/admin/` | `platform/presenters/admin_presenter.py` | `controller.items.items` | 1 | No | No |
| Approval Queue | `platform/controllers/control/` | `platform/presenters/control_queue_presenter.py` | `controller.items.items` | 2 | No | No |
| Audit | `platform/controllers/control/` | `platform/presenters/control_presenter.py` | `controller.items.items` | 1 | No | No |
| Module Entitlements | `platform/controllers/settings/` | `platform/presenters/settings_catalog_presenter.py` | `controller.items.items` | 1 | No | No |
| Integration Capabilities | `platform/controllers/settings/` | `platform/presenters/settings_presenter.py` | `controller.items.items` | 1 | No | No |
| Support | `platform/controllers/admin/` | `platform/presenters/support_workspace_presenter.py` | `controller.items.items` | 2 | No | No |
| Access / Roles | `platform/controllers/access/` | `platform/presenters/access_workspace_presenter.py` | `controller.items.items` | 1 | No | No |

---

### Project Management Workspaces

| Workspace | Controller | Presenter | Tables | Pagination | Search | Anti-Patterns |
|-----------|-----------|-----------|--------|-----------|--------|--------------|
| Dashboard | `pm/controllers/dashboard/` | `pm/presenters/dashboard_workspace_presenter.py` | 3+ | No | No | — |
| Projects | `pm/controllers/projects/` | `pm/presenters/projects_workspace_presenter.py` | 7 (main + 6 detail) | Yes | Yes | — |
| Tasks | `pm/controllers/tasks/` | `pm/presenters/tasks_workspace_presenter.py` | 4 | Yes | Yes | — |
| Resources | `pm/controllers/resources/` | `pm/presenters/resources_workspace_presenter.py` | 2 | Yes | Yes | — |
| Timesheets | `pm/controllers/timesheets/` | `pm/presenters/timesheets_workspace_presenter.py` | 3 | Yes | Partial | — |
| Financials | `pm/controllers/financials/` | `pm/presenters/financials_workspace_presenter.py` | 2 | Yes | No | — |
| Portfolio | `pm/controllers/portfolio/` | `pm/presenters/portfolio_workspace_presenter.py` | 1 | No | No | — |
| Risks | `pm/controllers/risk/` | `pm/presenters/workspace_presenter.py` | 1 | Yes | Yes | — |
| Scheduling | `pm/controllers/scheduling/` | `pm/presenters/scheduling_workspace_presenter.py` | 7 | No | In QML | **7× `_filterRows()`** |
| Collaboration | `pm/controllers/collaboration/` | `pm/presenters/collaboration_workspace_presenter.py` | 2 | Yes | No | — |
| Register | `pm/controllers/register/` | `pm/presenters/register_workspace_presenter.py` | 1 | Yes | No | — |

---

### Inventory & Procurement Workspaces

| Workspace | Controller | Presenter | Tables | Pagination | Search | Notes |
|-----------|-----------|-----------|--------|-----------|--------|-------|
| Dashboard | `inv/controllers/dashboard/` | `inv/presenters/dashboard_workspace_presenter.py` | 2 | No | No | — |
| Catalog | `inv/controllers/catalog/` | `inv/presenters/catalog_workspace_presenter.py` | 2 (items + categories) | Yes (both) | Yes | Most complex |
| Inventory | `inv/controllers/inventory/` | `inv/presenters/inventory_workspace_presenter.py` | 2 | Yes | Yes | — |
| Warehouses | None dedicated | N/A | 1 | Yes | No | No controller |
| Stock Movements | None dedicated | N/A | 1 | Yes | No | No controller |
| Reservations | `inv/controllers/reservations/` | `inv/presenters/reservations_workspace_presenter.py` | 1 | Yes | Yes | — |
| Procurement | `inv/controllers/procurement/` | `inv/presenters/procurement_workspace_presenter.py` | 3 | Yes | Yes | — |
| Pricing | `inv/controllers/pricing/` | `inv/presenters/pricing_workspace_presenter.py` | 1 | Yes | Yes | — |

---

### Maintenance Workspaces

| Workspace | Controller | Presenter | Tables | Notes |
|-----------|-----------|-----------|--------|-------|
| Dashboard | `maintenance/controllers/dashboard/` | `maintenance/presenters/dashboard_workspace_presenter.py` | 4 | — |
| Assets | `maintenance/controllers/assets/` | `maintenance/presenters/assets_workspace_presenter.py` | 4 | Most complex |
| Work Orders | `maintenance/controllers/work_orders/` | `maintenance/presenters/work_orders_workspace_presenter.py` | 2 | — |
| Work Requests | `maintenance/controllers/work_requests/` | `maintenance/presenters/work_requests_workspace_presenter.py` | 1 | — |
| Preventive | `maintenance/controllers/preventive/` | `maintenance/presenters/preventive_workspace_presenter.py` | 4 | — |
| Planner | `maintenance/controllers/planner/` | `maintenance/presenters/planner_workspace_presenter.py` | 5 | Most tables |
| Reliability | `maintenance/controllers/reliability/` | `maintenance/presenters/reliability_workspace_presenter.py` | 3 | — |

---

## Dependency Map

### Per-Workspace Dependency Template

```
[Repository / API Service]
         ↓
[WorkspacePresenter.build_workspace_state(search, filters, page, page_size)]
   returns WorkspaceState(items=[...], total_count=N, ...)
         ↓
[WorkspaceController]
   - Receives WorkspaceState
   - Calls serialize_record_view_models(state.items)
   - Stores result in self._items dict
   - Exposes @Property("QVariantList") items
   - Exposes pagination/search/filter state as @Property
         ↓
[QML WorkspacePage]
   - rows: controller.items.items || []         ← CURRENT (bridge crossing)
   - rows: controller.tableModel                ← TARGET  (QObject reference)
         ↓
[DataTable.qml]
   - Internal DynamicTableModel ← CURRENT
   - sourceModel from controller ← TARGET
         ↓
[TableView] → cell delegates → StatusChip / ProgressBar / text
```

### Catalog Workspace (Most Complex — 2 Tables)

```
InventoryCatalogWorkspacePresenter
   .build_workspace_state(search, active_filter, category_filter, item_page, category_page)
         ↓
InventoryProcurementCatalogWorkspaceController
   ├── self._items    = {items: [...], emptyState: "..."}   → DataTable (items)
   └── self._categories = {items: [...], emptyState: "..."} → DataTable (categories)

   Pagination:
   ├── itemPage / itemPageSize / itemTotalCount
   └── categoryPage / categoryPageSize / categoryTotalCount

   Selection:
   ├── selectedItemId / selectedItemIds
   └── selectedCategoryId / selectedCategoryIds
         ↓
CatalogWorkspacePage.qml
   ├── DataTable  rows: controller.items.items || []        ← items table
   └── DataTable  rows: controller.categoriesModel.items || []  ← categories table
```

### Scheduling Workspace (Anti-Pattern Location)

```
SchedulingWorkspacePresenter
         ↓
SchedulingWorkspaceController
   ├── diagnosticsRows: QVariantList
   ├── violationRows: QVariantList
   ├── resourceRows: QVariantList
   ├── baselineCompareRows: QVariantList
   ├── baselineRegisterRows: QVariantList
   ├── delayedRows: QVariantList
   └── holidayRows: QVariantList
         ↓
SchedulingWorkspacePage.qml
   ├── rows: root._filterRows(diagnosticsRows, searchText, [...])   ← ANTI-PATTERN
   ├── rows: root._filterRows(violationRows, searchText, [...])     ← ANTI-PATTERN
   ├── rows: root._filterRows(resourceRows, searchText, [...])      ← ANTI-PATTERN
   ├── rows: root._filterRows(baselineCompareRows, searchText, [...]) ← ANTI-PATTERN
   ├── rows: root._filterRows(baselineRegisterRows, searchText, [...]) ← ANTI-PATTERN
   ├── rows: root._filterRows(delayedRows, searchText, [...])       ← ANTI-PATTERN
   └── rows: root._filterRows(holidayRows, searchText, [...])       ← ANTI-PATTERN
```

---

## Performance Bottlenecks

### Critical — Fix in Pilot

| ID | Location | Problem | Impact | Fix |
|----|----------|---------|--------|-----|
| P1 | `SchedulingWorkspacePage.qml:815,834,898,1029,1039,1131,1386` | `_filterRows()` called on every binding re-evaluation | O(n²) on search input change; creates new array on every keystroke | Move filter to presenter or controller; expose `filteredRows` as readonly computed |
| P2 | All 25 workspace QML files | `rows: controller.items.items \|\| []` — full QVariantList crosses Python→QML bridge on every refresh | Memory spike + GC pressure on large datasets | Move model to controller; bind `sourceModel: controller.tableModel` |

### Medium — Fix During Migration

| ID | Location | Problem | Impact | Fix |
|----|----------|---------|--------|-----|
| P3 | `DataTable.qml:56-63` `_rebuildSelectedLookup()` | Rebuilds lookup map on every `selectedRowIds` change; triggers when full array reassigned | Checkbox feels laggy at 50+ rows | Controller tracks selection as a `set`; emit item-level signal, not full-array reassign |
| P4 | `DataTable.qml:159-173` `_displayRows` | JavaScript `.sort()` creates full array copy on every sort toggle | Extra GC on large tables | Move sort to Python controller or `QSortFilterProxyModel` |
| P5 | All controllers | `totalCount = len(items)` — presenter loads ALL rows to count | Cannot support server-side pagination | Pass `offset`/`limit` to presenter; return `total_count` from service |
| P6 | All controllers | No `order_by` passed to service; `sortRequested` signal unhandled in controllers | Sort is always client-side | Wire `sortRequested` → controller → presenter order_by |

### Low — Future Work

| ID | Location | Problem |
|----|----------|---------|
| P7 | `TableColumnCustomizer.qml` | Column visibility preferences not persisted between sessions |
| P8 | `TableToolbar.qml` export handlers | Export not wired in several workspaces (empty `onExportRequested: {}`) |
| P9 | All modules | No `QSortFilterProxyModel` — all filtering in presenter (full reload) |

---

## Files to Modify

### Phase 2A — Foundation (Touches shared code; affects all workspaces)

| File | Change | Risk |
|------|--------|------|
| `src/ui_qml/shared/models/data_table_model.py` | Add `StatusRole`, `MetadataRole`, `WidthRole`; add public `set_rows()` / `set_columns()` methods | Low — additive only |
| `src/ui_qml/shared/qml/App/Widgets/DataTable.qml` | Add `property var sourceModel: null`; when set, use it as TableView model instead of internal `_tableModel` | Medium — backward-compatible if `rows:` path preserved |

### Phase 2B — Pilot (Tasks workspace)

| File | Change | Risk |
|------|--------|------|
| `src/ui_qml/modules/project_management/controllers/tasks/tasks_workspace_controller.py` | Add `_table_model = DynamicTableModel()` instance; add `tableModel` property; remove `items` QVariantList property | Medium |
| `src/ui_qml/modules/project_management/qml/workspaces/tasks/TasksWorkspacePage.qml` | Change `rows: controller.items.items` → `sourceModel: controller.tableModel` | Low |

### Phase 2C — Scheduling Anti-Pattern Fix (Parallel to Pilot)

| File | Change | Risk |
|------|--------|------|
| `src/ui_qml/modules/project_management/qml/workspaces/scheduling/SchedulingWorkspacePage.qml` | Remove `_filterRows()` calls; bind to controller-filtered properties | Low |
| `src/ui_qml/modules/project_management/controllers/scheduling/scheduling_workspace_controller.py` | Expose pre-filtered row arrays: `filteredDiagnosticsRows`, `filteredViolationRows`, etc. | Low |

### Phase 3 — Platform (14 workspaces, all use same `AdminEntityWorkspace.qml` template)

| File | Change | Risk |
|------|--------|------|
| `src/ui_qml/platform/qml/workspaces/admin/AdminEntityWorkspace.qml` | One change covers all Platform admin workspaces | Low |
| Each of 14 platform controllers | Add `_table_model`, expose `tableModel` property | Low |

### Phase 4 — Project Management (11 workspaces)

| Files | Change | Risk |
|-------|--------|------|
| All PM workspace controllers | Add `_table_model` per table | Medium |
| All PM workspace QML files | Swap rows binding | Low |

### Phase 5 — Inventory & Procurement (8 workspaces)

| Files | Change |
|-------|--------|
| All Inventory controllers | Add `_table_model` per table |
| All Inventory workspace QML files | Swap rows binding |

### Phase 6 — Maintenance (7 workspaces)

| Files | Change |
|-------|--------|
| All Maintenance controllers | Add `_table_model` per table |
| All Maintenance workspace QML files | Swap rows binding |

---

## Mandatory Enterprise Table Model

The `DynamicTableModel` already exists and is already enterprise-grade. No new model class is needed.

**Roles to add (Phase 2A):**

```python
# src/ui_qml/shared/models/data_table_model.py

StatusRole   = Qt.UserRole + 17   # Row-level status string (for row bg tinting)
MetadataRole = Qt.UserRole + 18   # Arbitrary dict (for contextual actions)
WidthRole    = Qt.UserRole + 19   # Explicit pixel width override
```

**Public API to add:**

```python
def set_rows(self, rows: list[dict]) -> None:
    """Public entry point for controller to push rows without bridge crossing."""
    self._set_rows(rows)

def set_columns(self, columns: list[dict]) -> None:
    """Public entry point for controller to push column definitions."""
    self._set_columns(columns)

def append_rows(self, rows: list[dict]) -> None:
    """Append rows without full model reset (for lazy loading / pagination append)."""
    if not rows:
        return
    first = len(self._rows)
    last = first + len(rows) - 1
    self.beginInsertRows(QModelIndex(), first, last)
    self._rows.extend(rows)
    self.endInsertRows()
    self.rowsChanged.emit()
```

**Target controller contract:**

```python
from src.ui_qml.shared.models.data_table_model import DynamicTableModel

class MyWorkspaceController(WorkspaceControllerBase):

    tableModelChanged = Signal()

    def __init__(self, ...):
        super().__init__(...)
        self._table_model = DynamicTableModel(self)
        self._table_model.set_columns(self._build_columns())

    @Property(QObject, notify=tableModelChanged)
    def tableModel(self) -> DynamicTableModel:
        return self._table_model

    def _on_data_loaded(self, state: WorkspaceState) -> None:
        rows = serialize_record_view_models(state.items)
        self._table_model.set_rows(rows)   # Python → Python, no bridge
```

**Target QML contract:**

```qml
// In WorkspacePage.qml
DataTable {
    sourceModel: root.workspaceController ? root.workspaceController.tableModel : null
    columns:     root.workspaceController ? root.workspaceController.tableColumns : []
    // rows: binding removed
}
```

---

## Selection Architecture

### Current Problem

```python
# Controller stores full list
self._selected_item_ids: list[str] = []

def _set_selected_item_ids(self, ids: list[str]):
    self._selected_item_ids = ids
    self.selectedItemIdsChanged.emit()   # Emits → QML rebinds selectedRowIds
                                          # → DataTable._rebuildSelectedLookup()
                                          # → Rebuilds full lookup map
```

On 100+ selected rows: every checkbox toggle rebuilds the entire lookup map.

### Target (No Model Reset)

Selection state stays in the controller. The model does NOT know about selection. DataTable continues to manage selection UI state from `selectedRowIds`.

**Optimization**: Replace `list[str]` with `set[str]` in controller (O(1) lookup for `x in selected`), and emit only when the set actually changes:

```python
self._selected_ids: set[str] = set()

@Slot(str, bool)
def setItemBulkSelection(self, row_id: str, selected: bool) -> None:
    prev = frozenset(self._selected_ids)
    if selected:
        self._selected_ids.add(row_id)
    else:
        self._selected_ids.discard(row_id)
    if self._selected_ids != prev:
        self.selectedItemIdsChanged.emit()

@Property("QVariantList", notify=selectedItemIdsChanged)
def selectedItemIds(self) -> list[str]:
    return list(self._selected_ids)
```

This does NOT require model changes. Selection remains QML-side UI state fed by controller.

---

## Pagination Architecture

### Current

- Controller tracks `page`, `pageSize`, `totalCount`
- `totalCount = len(all_items)` — entire dataset loaded into memory
- `TablePaginationBar` shows correct UI but no actual result slicing occurs
- Page change triggers full reload (same data, display offset only)

### Target (True Server-Side Pagination)

```python
# Presenter signature (target)
def build_workspace_state(
    self,
    search_text: str = "",
    status_filter: str = "all",
    page: int = 1,
    page_size: int = 25,
    sort_by: str = "",
    sort_order: str = "asc",
) -> WorkspaceState:
    offset = (page - 1) * page_size
    items, total_count = self._service.list_paginated(
        search=search_text,
        status=status_filter,
        offset=offset,
        limit=page_size,
        order_by=sort_by,
        order_dir=sort_order,
    )
    return WorkspaceState(items=items, total_count=total_count)
```

**Supported page sizes:** 25 · 50 · 100 · 250 (already in `TablePaginationBar`)

**Future lazy loading:** `append_rows()` method on `DynamicTableModel` enables infinite scroll without model reset.

---

## Migration Strategy & Sequence

### Guiding Principles

1. **Never break existing workspaces** during migration
2. **One workspace at a time** — pilot, validate, then migrate the module
3. **DataTable backward-compatibility** — keep `rows:` property working throughout
4. **Parallel migration** allowed within a module once pattern is proven

### Phase Overview

| Phase | Scope | Workspaces | Risk | Est. Effort |
|-------|-------|-----------|------|------------|
| **2A** | Foundation: model + DataTable | 0 (infra only) | Medium | 1–2 days |
| **2B** | Pilot: Tasks workspace | 1 | Medium | 1–2 days |
| **2C** | Quick win: Scheduling anti-pattern fix | 1 | Low | 0.5 days |
| **3** | Platform (all admin workspaces) | 14 | Low | 2–3 days |
| **4** | Project Management | 11 | Medium | 3–5 days |
| **5** | Inventory & Procurement | 8 | Medium | 2–4 days |
| **6** | Maintenance | 7 | Medium | 2–4 days |
| **7** | Validation, cleanup, export unification | All | Low | 2–3 days |

---

## Pilot Workspace Recommendation

### Recommendation: Tasks Workspace

**Rationale:**
- Has the most sub-tables (4): tasks, assignments, dependencies, time entries
- Already has pagination wired (page, pageSize, totalCount)
- Already has search and filter in Python
- Has multi-select + bulk operations (proves selection architecture)
- Known performance concern (checkbox lag with many tasks)
- Clean controller + presenter structure (no anti-patterns)
- Success here validates the full pattern for all remaining workspaces

**Secondary pilot after Tasks:** Platform Organizations (simplest case — 1 table, no pagination, no search)

**Third pilot:** Inventory Catalog (most complex case — 2 tables, dual pagination, proves the dual-model pattern)

### Pilot Validation Criteria

Before declaring a pilot complete:

- [ ] `rows:` binding removed from QML
- [ ] `sourceModel: controller.tableModel` bound in QML
- [ ] Controller exposes `tableModel` as `@Property(QObject)`
- [ ] Controller calls `self._table_model.set_rows(rows)` in `_on_data_loaded`
- [ ] Full refresh works (data loads correctly)
- [ ] Search/filter works (controller triggers `set_rows` with filtered result)
- [ ] Pagination works (page change triggers `set_rows` with new page data)
- [ ] Multi-select works (checkbox toggles feel instant)
- [ ] Bulk actions work (`applyBulkStatus` → refresh → `set_rows`)
- [ ] Export works (export from `_table_model._rows` or controller cache)
- [ ] Column customization works (columns state round-trips correctly)
- [ ] No regression in other workspaces

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| `DataTable sourceModel` path breaks existing `rows:` bindings | Low | High | Keep `rows:` path fully working; `sourceModel` is additive only. If `sourceModel` is null, DataTable behaves as today. |
| Controller `DynamicTableModel(self)` causes QML registration conflicts | Low | Medium | Use `parent=self` but do NOT use `@QmlElement` on instances; model is passed as opaque `QObject`. |
| Scheduling workspace fix introduces new bugs | Low | Low | Fix is purely moving `_filterRows()` calls from QML to controller; logic unchanged. |
| `beginResetModel` on every `set_rows()` call causes visible flicker | Medium | Medium | For large tables, implement `append_rows()` and page-replace logic instead of full reset. Pilot with Tasks will confirm. |
| Platform admin workspaces share `AdminEntityWorkspace.qml` — one change affects 14 workspaces | Medium | High | Test all 14 Platform workspaces after Phase 3. AdminEntityWorkspace change is bounded. |
| Export currently reads from QML `rows` in some workspaces | Medium | Medium | After migration, export reads from `controller._table_model._rows` directly (all data available in Python). |
| Column customization state reset after migration | Low | Medium | `columnsStateChanged` signal from DataTable drives both `DataTable.columns` and `_table_model.set_columns()`. No change needed. |

---

## Progress Tracker

### Phase 1 — Discovery ✅ COMPLETE

- [x] Full codebase scan completed
- [x] 46 controllers inventoried
- [x] 43 presenters inventoried
- [x] 68 DataTable instances mapped
- [x] Performance bottlenecks identified
- [x] Anti-patterns documented
- [x] DynamicTableModel roles audited
- [x] Migration sequence defined
- [x] Risks assessed
- [x] Migration plan document produced

### Phase 2A — Foundation ⏳ PENDING APPROVAL

- [ ] Add `StatusRole`, `MetadataRole`, `WidthRole` to `DynamicTableModel`
- [ ] Add `set_rows()`, `set_columns()`, `append_rows()` public methods
- [ ] Add `sourceModel` property to `DataTable.qml`
- [ ] Validate backward compatibility with existing `rows:` bindings

### Phase 2B — Tasks Pilot ⏳ PENDING

- [ ] Migrate `TasksWorkspaceController` to Python-owned model
- [ ] Update `TasksWorkspacePage.qml` to use `sourceModel`
- [ ] Validate all 4 sub-tables
- [ ] Validate selection performance
- [ ] Validate pagination
- [ ] Validate export

### Phase 2C — Scheduling Fix ⏳ PENDING

- [ ] Move `_filterRows()` logic to `SchedulingWorkspaceController`
- [ ] Expose filtered arrays as controller properties
- [ ] Remove 7 anti-pattern bindings from `SchedulingWorkspacePage.qml`

### Phase 3 — Platform ⏳ PENDING (after Phase 2B validated)

- [ ] Organizations
- [ ] Sites
- [ ] Departments
- [ ] Employees
- [ ] Users
- [ ] Parties
- [ ] Documents
- [ ] Structures
- [ ] Approval Queue
- [ ] Audit
- [ ] Module Entitlements
- [ ] Integration Capabilities
- [ ] Support
- [ ] Access / Roles

### Phase 4 — Project Management ⏳ PENDING

- [ ] Dashboard
- [ ] Projects (7 tables)
- [ ] Tasks (already done in pilot — validate)
- [ ] Resources
- [ ] Timesheets
- [ ] Financials
- [ ] Portfolio
- [ ] Risks
- [ ] Scheduling (anti-pattern fixed in 2C — full migration here)
- [ ] Collaboration
- [ ] Register

### Phase 5 — Inventory & Procurement ⏳ PENDING

- [ ] Dashboard
- [ ] Catalog (2 tables — dual-model pattern)
- [ ] Inventory
- [ ] Warehouses
- [ ] Stock Movements
- [ ] Reservations
- [ ] Procurement
- [ ] Pricing

### Phase 6 — Maintenance ⏳ PENDING

- [ ] Dashboard
- [ ] Assets
- [ ] Work Orders
- [ ] Work Requests
- [ ] Preventive
- [ ] Planner
- [ ] Reliability

### Phase 7 — Validation & Unification ⏳ PENDING

- [ ] Wire `sortRequested` signal in all controllers → presenter `order_by`
- [ ] Unify export across all modules (currently only PM has `table_exporter.py`)
- [ ] Persist column visibility preferences to local settings
- [ ] Implement true server-side pagination (offset/limit in all presenters)
- [ ] Final audit: no `rows: controller.*.items` bindings remain

---

*This document lives at `docs/DATATABLE_ARCHITECTURE_MIGRATION_PLAN.md` and should be updated as each phase completes.*
