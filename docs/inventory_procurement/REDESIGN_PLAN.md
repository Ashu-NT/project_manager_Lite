# Inventory & Procurement Module — UI/UX Redesign Plan

**Status:** In Progress  
**Last Updated:** 2026-05-27  
**Branch:** refactor/safe-start

---

## Goal

Modernize all Inventory & Procurement workspaces from the old `RecordListCard` + stacked-card
pattern to the enterprise component pattern used by the PM module:

```
List Page:   KpiStrip → InlineMessage → TableToolbar → DataTable + PaginationBar + BulkActionBar
Detail Page: Lazy Loader → SectionDetailPage + ContextualActionToolbar
```

**Do not rebuild from scratch.** Reuse existing controllers, presenters, services, APIs, ORM,
and dialogs. Only touch QML workspace pages and add minimal controller additions.

---

## Architecture Decisions

### Component Pattern (Reference: TasksWorkspacePage.qml)
- `AppWidgets.KpiStrip` replaces all `*MetricsSection` components
- `AppWidgets.InlineMessage` replaces `WorkspaceStateBanner` + `WorkspaceStatusSection`
- `AppWidgets.TableToolbar` replaces all `*FiltersSection` components
- `AppWidgets.DataTable` replaces all `RecordListCard`-based `*CatalogSection` components
- `AppWidgets.TablePaginationBar` added to every list
- `AppWidgets.BulkActionBar` + `BulkChangePropertyPopup` added for multi-select operations
- `AppWidgets.AnchoredPopup` for filter panels anchored to toolbar filter button
- `AppWidgets.SectionDetailPage` + `AppWidgets.ContextualActionToolbar` replaces all `*DetailSection` components
- `AppWidgets.ActivityFeed` in detail pages (empty state until Phase 9 data wiring)
- `AppWidgets.LazyObjectLoader` preserved for dialog hosts (existing pattern, keep it)
- `Loader { asynchronous: true }` for detail page lazy loading (follow Tasks pattern)

### Controller Additions (Additive Only)
For each workspace controller, new properties added (no existing properties removed):
- `page`, `pageSize`, `totalCount` per entity list (client-side total = items.length for now)
- `selectedIds`, `selectedCount` per entity list (bulk selection state)
- `activateRow(rowId)` → sets selectedId and opens detail page
- `clearFilters()` → resets all filters + search + triggers refresh
- `setBulkSelection(rowId, selected)`, `clearBulkSelection()`, `selectVisible()` slots

### Row Shape
The current `serialize_record_view_models()` emits generic fields:
`id, title, statusLabel, subtitle, supportingText, metaText, canPrimaryAction, canSecondaryAction, canTertiaryAction, state`

DataTable columns use these generic keys for now. Domain-specific enrichment (itemCode,
categoryName, onHand, etc.) is tracked in Phase 7.

### Cross-Module Capability
- Reservation and Procurement workspace pages already have `property var platformCatalog` and
  `property var _caps` wired from Phase 8 integration work.
- Catalog and Inventory workspaces: add `platformCatalog` property; cross-module actions
  (e.g. "Create Requisition" from shortage) gate on `_caps.canInvLinkProcurement` etc.
- All detail pages: "Open Source" buttons gate on `_caps` check; tooltip "Module not enabled"
  when false.

### Deleted / Deprecated Components
The following files become obsolete after this work. **Do not delete until Phase 10 audit
confirms zero remaining imports:**
- `WorkspaceStateBanner.qml`
- `WorkspaceStatusSection.qml`
- `DashboardMetricsSection.qml`
- `CatalogMetricsSection.qml`, `InventoryMetricsSection.qml`, `ReservationsMetricsSection.qml`
- `ProcurementMetricsSection.qml`, `PricingMetricsSection.qml`
- `CatalogFiltersSection.qml`, `InventoryFiltersSection.qml`, `ReservationsFiltersSection.qml`
- `ProcurementFiltersSection.qml`, `PricingFiltersSection.qml`
- `CategoryCatalogSection.qml`, `ItemCatalogSection.qml`
- `StoreroomCatalogSection.qml`, `BalanceCatalogSection.qml`
- `ReservationsCatalogSection.qml`
- `RequisitionCatalogSection.qml`, `PurchaseOrderCatalogSection.qml`
- `ItemDetailSection.qml`, `CategoryDetailSection.qml`
- `StoreroomDetailSection.qml`, `BalanceDetailSection.qml`
- `ReservationDetailSection.qml`
- `RequisitionDetailSection.qml`, `PurchaseOrderDetailSection.qml`
- `DashboardSections.qml`

---

## Workspace Status Tracker

### WS-1: Inventory Dashboard

**Purpose:** Enterprise inventory command center with KPI strip and panel-based watchlists.

| Task | Status | Notes |
|------|--------|-------|
| Remove `WorkspaceStatusSection` / `WorkspaceStateBanner` | ✅ Done | |
| Remove `DashboardMetricsSection` (MetricCard flow) | ✅ Done | Replaced by KpiStrip |
| Remove `DashboardSections` (stacked card dump) | ✅ Done | Replaced by panel tabs + DataTable |
| Add `AppWidgets.KpiStrip` | ✅ Done | metrics from `overviewModel.metrics` |
| Add `AppWidgets.InlineMessage` (loading/error/feedback) | ✅ Done | |
| Panel tabs: Low Stock / Critical Spares / Reservations / Procurement / Movements | ✅ Done | tabbed from `sections` array |
| Each panel: DataTable with section rows | ✅ Done | generic columns (title/subtitle/status) |
| Panel: drill-down navigation | 🔲 Pending | Phase 6 — needs routes for balance/reservation/PO detail |
| Context bar: Organization / Site / Warehouse / Module scope selectors | 🔲 Pending | Phase 6 — requires platform filter API |

---

### WS-2: Catalog / Item Master

**Purpose:** Enterprise item master — materials, spares, consumables, services.

| Task | Status | Notes |
|------|--------|-------|
| Remove `RecordListCard`-based `ItemCatalogSection` | ✅ Done | |
| Remove `RecordListCard`-based `CategoryCatalogSection` | ✅ Done | |
| Remove `CatalogFiltersSection` | ✅ Done | |
| Remove `CatalogMetricsSection` | ✅ Done | |
| Remove `WorkspaceStateBanner` / `WorkspaceStatusSection` | ✅ Done | |
| Remove `ItemDetailSection` / `CategoryDetailSection` | ✅ Done | |
| Add `AppWidgets.KpiStrip` | ✅ Done | |
| Add `AppWidgets.InlineMessage` | ✅ Done | |
| Add `AppWidgets.TableToolbar` | ✅ Done | search + filter + create + export + views |
| Add `AppWidgets.DataTable` — Items | ✅ Done | columns: title/subtitle/statusLabel/metaText |
| Add `AppWidgets.DataTable` — Categories | ✅ Done | secondary view via toolbar view toggle |
| Add `AppWidgets.TablePaginationBar` | ✅ Done | client-side total |
| Add `AppWidgets.BulkActionBar` | ✅ Done | actions: change status, archive |
| Add `AppWidgets.BulkChangePropertyPopup` | ✅ Done | property: status |
| Add `AppWidgets.AnchoredPopup` filter panel | ✅ Done | active/usage/type/category filters |
| Add `AppWidgets.SectionDetailPage` | ✅ Done | sections: Overview / Documents / Activity |
| Add `AppWidgets.ContextualActionToolbar` in detail | ✅ Done | back + Edit + Toggle Active |
| Add `AppWidgets.ActivityFeed` in Activity section | ✅ Done | empty state (data Phase 9) |
| Controller: `itemPage`, `itemPageSize`, `selectedItemIds`, `activateItem` | ✅ Done | |
| Controller: `categoryPage`, `categoryPageSize`, `selectedCategoryIds`, `activateCategory` | ✅ Done | |
| Controller: `clearFilters()`, `activeView`, `setActiveView()` | ✅ Done | |
| Controller: `bulkStatusOptions` for BulkChangePropertyPopup | ✅ Done | |
| Row serializer enrichment (itemCode, categoryName, uom, etc.) | 🔲 Pending | Phase 7 |
| Specifications section (domain data) | 🔲 Pending | Phase 7 |
| Suppliers section in detail (linked parties) | 🔲 Pending | Phase 7 |
| Linked Assets section (Maintenance enabled only) | 🔲 Pending | Phase 7 |
| Linked Projects/Tasks section (PM enabled only) | 🔲 Pending | Phase 7 |

---

### WS-3: Warehouses & Locations

**Purpose:** Manage inventory storage under Platform Sites: Warehouse → Zone → Bin/Location.

> ⚠️ **NEW WORKSPACE — NOT YET IMPLEMENTED**

| Task | Status | Notes |
|------|--------|-------|
| New QML: `WarehousesWorkspacePage.qml` | 🔲 Pending | Phase 6 |
| New controller: `WarehousesWorkspaceController` | 🔲 Pending | Phase 6 |
| New presenter: `InventoryWarehousesWorkspacePresenter` | 🔲 Pending | Phase 6 |
| Route: `inventory_procurement.warehouses` | 🔲 Pending | Phase 6 |
| Platform Site lookup (no duplicate site table) | 🔲 Pending | Phase 6 |
| Warehouse hierarchy tree or DataTable | 🔲 Pending | Phase 6 |
| Detail page: Overview / Bins / Stock Balances / Movement History / Cycle Counts | 🔲 Pending | Phase 6 |

---

### WS-4: Inventory / Stock Balances

**Purpose:** Stock-on-hand positions, available quantity, reorder status.

| Task | Status | Notes |
|------|--------|-------|
| Remove `RecordListCard`-based `BalanceCatalogSection` | ✅ Done | |
| Remove `RecordListCard`-based `StoreroomCatalogSection` | ✅ Done | |
| Remove `BalanceDetailSection` / `StoreroomDetailSection` | ✅ Done | |
| Remove `InventoryFiltersSection` | ✅ Done | |
| Remove `InventoryMetricsSection` | ✅ Done | |
| Remove `WorkspaceStateBanner` / `WorkspaceStatusSection` | ✅ Done | |
| Remove `TransactionsSection` (promoted to WS-5) | ✅ Done | |
| Add `AppWidgets.KpiStrip` | ✅ Done | |
| Add `AppWidgets.InlineMessage` | ✅ Done | |
| Add `AppWidgets.TableToolbar` | ✅ Done | |
| Add `AppWidgets.DataTable` — Stock Balances | ✅ Done | |
| Add `AppWidgets.DataTable` — Storerooms (secondary view) | ✅ Done | |
| Add `AppWidgets.TablePaginationBar` | ✅ Done | |
| Add `AppWidgets.BulkActionBar` | ✅ Done | actions: adjust, transfer, reserve |
| Add `AppWidgets.AnchoredPopup` filter panel | ✅ Done | |
| Add `AppWidgets.SectionDetailPage` — balance detail | ✅ Done | Overview / Movements / Reservations / Reorder / Activity |
| Add `AppWidgets.ContextualActionToolbar` | ✅ Done | Adjust / Issue / Transfer / Reserve |
| Controller: pagination + bulk + activate per list | ✅ Done | |
| Row serializer enrichment (onHand, available, reserved, reorderPoint, unitCost) | 🔲 Pending | Phase 7 |
| Movements sub-section lazy load | 🔲 Pending | Phase 9 |
| Reservations sub-section lazy load | 🔲 Pending | Phase 9 |

---

### WS-5: Stock Movements

**Purpose:** Immutable inventory transaction ledger (Receive / Issue / Transfer / Adjust / etc).

> ⚠️ **NEW WORKSPACE — NOT YET IMPLEMENTED**

| Task | Status | Notes |
|------|--------|-------|
| New QML: `StockMovementsWorkspacePage.qml` | 🔲 Pending | Phase 6 |
| Reuse / promote existing `TransactionsSection` data | 🔲 Pending | Phase 6 |
| Controller: extend inventory controller or new `StockMovementsWorkspaceController` | 🔲 Pending | Phase 6 |
| Route: `inventory_procurement.movements` | 🔲 Pending | Phase 6 |
| Immutable movement records (no edit, only reversal) | 🔲 Pending | Phase 6 |
| Platform Audit trail in detail | 🔲 Pending | Phase 6 |

---

### WS-6: Reservations / Demand

**Purpose:** Allocate material demand to stock; cross-module reservation holds.

| Task | Status | Notes |
|------|--------|-------|
| Remove `RecordListCard`-based `ReservationsCatalogSection` | ✅ Done | |
| Remove `ReservationDetailSection` | ✅ Done | |
| Remove `ReservationsFiltersSection` | ✅ Done | |
| Remove `ReservationsMetricsSection` | ✅ Done | |
| Remove `WorkspaceStateBanner` / `WorkspaceStatusSection` | ✅ Done | |
| Add `AppWidgets.KpiStrip` | ✅ Done | |
| Add `AppWidgets.InlineMessage` | ✅ Done | |
| Add `AppWidgets.TableToolbar` | ✅ Done | |
| Add `AppWidgets.DataTable` | ✅ Done | |
| Add `AppWidgets.TablePaginationBar` | ✅ Done | |
| Add `AppWidgets.BulkActionBar` | ✅ Done | Approve / Allocate / Release / Cancel |
| Add `AppWidgets.AnchoredPopup` filter panel | ✅ Done | |
| Add `AppWidgets.SectionDetailPage` | ✅ Done | Overview / Allocation / Source / Approval / Activity |
| Add `AppWidgets.ContextualActionToolbar` | ✅ Done | Issue / Release / Cancel |
| Cross-module: PM Task link gated on `_caps.canPmLinkInventory` | ✅ Done | existing wiring preserved |
| Cross-module: Maintenance WO link gated on `_caps.canMaintLinkInventory` | ✅ Done | |
| Cross-module: "Create Requisition" on shortage gated on `_caps.canInvLinkProcurement` | ✅ Done | |
| Controller: pagination + bulk + activate | ✅ Done | |
| Row serializer enrichment (reservationNumber, qty, requiredDate, sourceModule) | 🔲 Pending | Phase 7 |
| Allocation section lazy load | 🔲 Pending | Phase 9 |
| Source demand section lazy load | 🔲 Pending | Phase 9 |

---

### WS-7: Procurement

**Purpose:** Requisitions → RFQ → Purchase Orders → Goods Receipt.

| Task | Status | Notes |
|------|--------|-------|
| Remove `RecordListCard`-based `RequisitionCatalogSection` | ✅ Done | |
| Remove `RecordListCard`-based `PurchaseOrderCatalogSection` | ✅ Done | |
| Remove `RequisitionDetailSection` / `PurchaseOrderDetailSection` | ✅ Done | |
| Remove `ProcurementFiltersSection` | ✅ Done | |
| Remove `ProcurementMetricsSection` | ✅ Done | |
| Remove `WorkspaceStateBanner` / `WorkspaceStatusSection` | ✅ Done | |
| Add `AppWidgets.KpiStrip` | ✅ Done | |
| Add `AppWidgets.InlineMessage` | ✅ Done | |
| Add `AppWidgets.TableToolbar` with view toggle | ✅ Done | Requisitions / Purchase Orders views |
| Add `AppWidgets.DataTable` — Requisitions | ✅ Done | |
| Add `AppWidgets.DataTable` — Purchase Orders | ✅ Done | |
| Add `AppWidgets.TablePaginationBar` | ✅ Done | |
| Add `AppWidgets.BulkActionBar` | ✅ Done | Submit / Approve / Reject / Convert to PO / Close |
| Add `AppWidgets.AnchoredPopup` filter panel | ✅ Done | |
| Add `AppWidgets.SectionDetailPage` — Requisition detail | ✅ Done | Overview / Line Items / Approvals / Documents / Activity |
| Add `AppWidgets.SectionDetailPage` — PO detail | ✅ Done | Overview / Line Items / Receipts / Financials / Documents / Activity |
| Add `AppWidgets.ContextualActionToolbar` | ✅ Done | |
| Cross-module: PM/Maintenance source reference gated on caps | ✅ Done | existing wiring |
| Cross-module: goods receipt → inventory movement when `_caps.canProcLinkInventory` | ✅ Done | note in detail |
| Controller: pagination + bulk + activate per list (req + PO) | ✅ Done | |
| Row serializer enrichment (poNumber, supplierName, totalValue, approvalState) | 🔲 Pending | Phase 7 |
| Line items section lazy load | 🔲 Pending | Phase 9 |
| Receipt history section lazy load | 🔲 Pending | Phase 9 |

---

### WS-8: Pricing / Valuation

**Purpose:** Supplier prices, contract prices, standard price, inventory valuation.

| Task | Status | Notes |
|------|--------|-------|
| Remove old `PricingStockSection` / `PricingSupplierPricingSection` | ✅ Done | |
| Remove `PricingExportsSection` (exports moved to TableToolbar) | ✅ Done | |
| Remove `PricingFiltersSection` | ✅ Done | |
| Remove `PricingMetricsSection` | ✅ Done | |
| Remove `WorkspaceStateBanner` / `WorkspaceStatusSection` | ✅ Done | |
| Add `AppWidgets.KpiStrip` | ✅ Done | |
| Add `AppWidgets.InlineMessage` | ✅ Done | |
| Add `AppWidgets.TableToolbar` | ✅ Done | search + filter + export |
| Add `AppWidgets.DataTable` — Price Records | ✅ Done | |
| Add `AppWidgets.TablePaginationBar` | ✅ Done | |
| Add `AppWidgets.AnchoredPopup` filter panel | ✅ Done | |
| Add `AppWidgets.SectionDetailPage` | ✅ Done | Overview / Price History / Contracts / Activity |
| Add `AppWidgets.ContextualActionToolbar` | ✅ Done | |
| Controller: pagination + activate | ✅ Done | |
| Row serializer enrichment (itemCode, supplierName, stdPrice, currency, variance) | 🔲 Pending | Phase 7 |
| Price history section lazy load | 🔲 Pending | Phase 9 |
| Contracts section lazy load | 🔲 Pending | Phase 9 |

---

## Pending Phases

### Phase 6: New Workspaces (WS-3 and WS-5)

#### WS-3: Warehouses & Locations
Files to create:
- `src/ui_qml/modules/inventory_procurement/qml/workspaces/warehouses/WarehousesWorkspacePage.qml`
- `src/ui_qml/modules/inventory_procurement/controllers/warehouses/warehouses_workspace_controller.py`
- Add presenter class: `InventoryWarehousesWorkspacePresenter`
- Add route: `inventory_procurement.warehouses` in `routes.py`
- Update `context.py` to expose `warehousesWorkspace` on the catalog

Implementation notes:
- Platform Site is the top-level node (do NOT create duplicate site table)
- Use `PlatformWorkspaceCatalog.siteOptions` for site lookup
- Warehouse → Zone → Bin hierarchy shown as tree or list with parent filter
- Detail page sections: Overview / Bins / Stock Balances / Movement History / Cycle Counts

#### WS-5: Stock Movements
Files to create:
- `src/ui_qml/modules/inventory_procurement/qml/workspaces/movements/StockMovementsWorkspacePage.qml`
- Extend or reuse `InventoryWorkspaceController` (add movements-specific pagination + filter)
- Add route: `inventory_procurement.movements` in `routes.py`

Implementation notes:
- Reuse existing `StockTransaction` data from inventory API
- Movements are immutable — no edit action, only "Create Reversal" for corrections
- Adjustments above threshold → Platform Approval Queue (show ApprovalState chip)
- Every movement row links to Platform Audit

---

### Phase 7: Row Serializer Enrichment

Add domain-specific fields to `serialize_record_view_models()` per entity type. Each enriched
record should include the fields the DataTable columns need.

**Items:**
```python
"itemCode": view_model.state.get("itemCode", ""),
"categoryName": view_model.state.get("categoryName", ""),
"itemType": view_model.state.get("itemType", ""),
"stockUom": view_model.state.get("stockUom", ""),
"supplierName": view_model.state.get("supplierName", ""),
"standardPrice": view_model.state.get("standardPrice", ""),
"criticality": view_model.state.get("criticality", ""),
```

**Stock Balances:**
```python
"itemCode": ..., "storeroomCode": ...,
"onHand": ..., "available": ..., "reserved": ...,
"reorderPoint": ..., "unitCost": ..., "stockValue": ...,
```

**Reservations:**
```python
"reservationNumber": ..., "itemCode": ...,
"quantity": ..., "requiredDate": ...,
"sourceModule": ..., "allocationState": ...,
```

**Procurement:**
```python
"docNumber": ..., "supplierName": ...,
"totalValue": ..., "approvalState": ...,
"requiredDate": ..., "sourceModule": ...,
```

After enrichment, update DataTable column definitions in each workspace page.

---

### Phase 8: Server-Side Pagination

Current client-side pagination: `totalCount = len(items)`, all rows loaded at once.

Server-side implementation requires:
1. Presenters accept `page: int`, `page_size: int` parameters
2. Services use `LIMIT / OFFSET` in queries (or keyset for large tables)
3. Controllers track page state and pass to presenter on every refresh

Estimated scope: ~1 day per workspace presenter.

---

### Phase 9: ActivityFeed and Lazy-Loaded Detail Sections

Wire up real data to ActivityFeed in all detail pages:
- Add `loadDetailActivity(entityId)` slot to each controller
- Call `PlatformAuditDesktopApi.list_events(entity_id)` 
- Emit `activityItemsChanged` signal
- QML calls slot on `SectionDetailPage.onSectionChanged` when Activity section activated

Lazy-load sub-tables in detail pages:
- `loadBalanceMovements(balanceId)` — movements ledger for selected balance
- `loadRequisitionLines(reqId)` — line items for selected requisition
- `loadPoLines(poId)` — line items for selected PO
- `loadPoReceipts(poId)` — receipt history for selected PO
- `loadReservationAllocation(resId)` — allocation state for selected reservation
- `loadPriceHistory(priceId)` — price history for selected price record

---

### Phase 10: Obsolete Component Cleanup

After Phase 6–9 complete and all imports verified:
1. Grep entire codebase for any remaining imports of deprecated components
2. Remove unused QML files listed in "Deleted / Deprecated Components" section above
3. Remove deprecated imports from qmldir files
4. Run full app validation: `python main_qt.py`

---

## Validation Checklist

Run `python main_qt.py` and verify:

- [ ] Inventory Dashboard loads — KpiStrip visible, panels tab-navigate
- [ ] Catalog loads — Items DataTable shows rows, TableToolbar works
- [ ] Catalog — view toggle to Categories works
- [ ] Catalog — filter popup opens anchored to filter button
- [ ] Catalog — click row opens SectionDetailPage
- [ ] Catalog — back button returns to list
- [ ] Catalog — BulkActionBar appears on multi-select
- [ ] Inventory/Stock Balances loads — DataTable shows rows
- [ ] Inventory — filter by site/storeroom works
- [ ] Inventory — click row opens SectionDetailPage
- [ ] Inventory — Adjust/Issue/Transfer actions in detail toolbar
- [ ] Reservations loads — DataTable shows rows
- [ ] Reservations — cross-module source link shows/hides by capability
- [ ] Procurement loads — Requisitions view works
- [ ] Procurement — view toggle to Purchase Orders works
- [ ] Procurement — detail page shows line items section
- [ ] Pricing loads — DataTable shows rows
- [ ] No duplicate components
- [ ] No QML warnings/errors in console
- [ ] All InlineMessage loading/error/feedback states work
- [ ] Disabled modules do not crash UI
- [ ] No `WorkspaceStatusSection` visible in any workspace

---

## Files Changed in This Redesign

### Python (controllers — additive additions only)
- `controllers/catalog/catalog_workspace_controller.py` — pagination + bulk + activate + clearFilters + activeView
- `controllers/inventory/inventory_workspace_controller.py` — pagination + bulk + activate + clearFilters + activeView
- `controllers/reservations/reservations_workspace_controller.py` — pagination + bulk + activate + clearFilters
- `controllers/procurement/procurement_workspace_controller.py` — pagination + bulk + activate + clearFilters + activeView
- `controllers/pricing/pricing_workspace_controller.py` — pagination + activate + clearFilters

### QML (workspace pages — full rewrites)
- `workspaces/dashboard/DashboardWorkspacePage.qml`
- `workspaces/catalog/CatalogWorkspacePage.qml`
- `workspaces/catalog/CatalogDetailContent.qml` ← **NEW** (detail sections: overview fields, documents, activity)
- `workspaces/inventory/InventoryWorkspacePage.qml`
- `workspaces/reservations/ReservationsWorkspacePage.qml`
- `workspaces/procurement/ProcurementWorkspacePage.qml`
- `workspaces/pricing/PricingWorkspacePage.qml`

#### Notes on Pricing detail
`PricingWorkspacePage` does not have full detail view models from the controller (pricing has no `selectedStockSignal`/`selectedSupplierPricing` properties). Instead, the detail panel computes a synthetic `fields` array by looking up the selected row from `stockSignals.items` / `supplierPricing.items` by ID. Phase 7 can enrich this by adding proper detail view model properties to `pricing_workspace_controller.py`.

### Docs
- `docs/inventory_procurement/REDESIGN_PLAN.md` — this file

### Not Changed (preserved as-is)
- All dialog QML files (CategoryEditorDialog, ItemEditorDialog, etc.)
- All Python presenters, view models, services, APIs, ORM
- All shared App.Widgets / App.Controls / App.Theme
- `WorkspaceStateBanner.qml` and `WorkspaceStatusSection.qml` (kept until Phase 10 audit)
- All `*CatalogSection.qml`, `*DetailSection.qml`, `*FiltersSection.qml` files
  (kept until Phase 10 audit confirms no remaining imports)
