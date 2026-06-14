pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

Item {
    id: root

    // ── Inputs ────────────────────────────────────────────────────────────
    property InventoryProcurementControllers.InventoryProcurementCatalogWorkspaceController workspaceController
    property var overviewModel:    ({ "metrics": [] })
    property var itemsModel:       ({ "emptyState": "No catalog items.", "items": [] })
    property var categoriesModel:  ({ "emptyState": "No categories.", "items": [] })
    property bool detailOpen:      false

    // ── Signals ───────────────────────────────────────────────────────────
    signal rowActivated()
    signal exportRequested()
    signal createItemRequested()
    signal createCategoryRequested()

    // ── Derived ───────────────────────────────────────────────────────────
    readonly property bool _isItemsView: root.workspaceController
        ? root.workspaceController.activeView === "items"
        : true

    readonly property var _itemColumns: [
        { "key": "title",         "label": "Item Name", "flex": 2,   "sortable": true },
        { "key": "itemCode",      "label": "Code",      "flex": 1   },
        { "key": "categoryLabel", "label": "Category",  "flex": 1.5 },
        { "key": "statusLabel",   "label": "Status",    "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _categoryColumns: [
        { "key": "title",             "label": "Category", "flex": 2,   "sortable": true },
        { "key": "categoryCode",      "label": "Code",     "flex": 1   },
        { "key": "categoryTypeLabel", "label": "Type",     "flex": 1.5 },
        { "key": "statusLabel",       "label": "Status",   "flex": 0,   "minWidth": 90, "type": "status" }
    ]
    readonly property var _bulkChangeProperties: {
        const opts = root.workspaceController ? (root.workspaceController.itemStatusOptions || []) : []
        return opts.length > 0 ? [{ "id": "status", "label": "Status", "values": opts }] : []
    }

    function _optionIndexForValue(options, value) {
        const list = options || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    // ── Layout ────────────────────────────────────────────────────────────
    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.KpiStrip {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            message: "Loading catalog..."
            compact: true
            modal:   false
        }
        AppWidgets.LoadingOverlay {
            Layout.fillWidth: true
            loading: root.workspaceController
                ? root.workspaceController.isBusy
                    && String(root.workspaceController.errorMessage || "").length === 0
                : false
            message: "Saving changes..."
            compact: true
            modal:   false
        }

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: !root.detailOpen
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: !root.detailOpen
                && String(root.workspaceController ? root.workspaceController.feedbackMessage : "").length > 0
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "success"
            message: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText:        root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: root._isItemsView ? "Search items..." : "Search categories..."
            showCreate:    true
            createLabel:   root._isItemsView ? "New Item" : "New Category"
            showFilter:    true
            showCustomize: root._isItemsView
            showViews:     true
            showRefresh:   true
            showExport:    true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked:   filterPopup.open()
            onCustomizeClicked: {
                if (root._isItemsView) _itemsTable.openColumnCustomizer(tableToolbar.customizeButtonItem)
            }
            onViewsClicked:    viewsPopup.open()
            onRefreshRequested: { if (root.workspaceController !== null) root.workspaceController.refresh() }
            onExportRequested: root.exportRequested()
            onCreateRequested: {
                if (root._isItemsView) root.createItemRequested()
                else root.createCategoryRequested()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _itemsTable
                anchors.top:    parent.top
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: _paginationBar.top
                visible:        root._isItemsView
                multiSelect:    true
                columns:        root._itemColumns
                sourceModel:    root.workspaceController ? root.workspaceController.itemsTableModel : null
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.itemsModel.emptyState || "No catalog items."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedItemId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedItemIds || []) : []

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectItem(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateItem(rowId)
                    root.rowActivated()
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null) root.workspaceController.setItemBulkSelection(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleItems()
                    else             root.workspaceController.clearItemBulkSelection()
                }
            }

            AppWidgets.DataTable {
                id: _categoriesTable
                anchors.top:    parent.top
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: _paginationBar.top
                visible:        !root._isItemsView
                multiSelect:    true
                columns:        root._categoryColumns
                sourceModel:    root.workspaceController ? root.workspaceController.categoriesTableModel : null
                loading:        root.workspaceController ? root.workspaceController.isLoading : false
                emptyText:      root.categoriesModel.emptyState || "No categories."
                selectedRowId:  root.workspaceController ? root.workspaceController.selectedCategoryId : ""
                selectedRowIds: root.workspaceController ? (root.workspaceController.selectedCategoryIds || []) : []

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectCategory(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.activateCategory(rowId)
                    root.rowActivated()
                }
                onRowSelectionToggled: function(rowId, selected) {
                    if (root.workspaceController !== null) root.workspaceController.setCategoryBulkSelection(rowId, selected)
                }
                onSelectAllToggled: function(allSelected) {
                    if (root.workspaceController === null) return
                    if (allSelected) root.workspaceController.selectVisibleCategories()
                    else             root.workspaceController.clearCategoryBulkSelection()
                }
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left:   parent.left
                anchors.right:  parent.right
                anchors.bottom: parent.bottom
                currentPage: root._isItemsView
                    ? (root.workspaceController ? root.workspaceController.itemPage : 1)
                    : (root.workspaceController ? root.workspaceController.categoryPage : 1)
                pageSize: root._isItemsView
                    ? (root.workspaceController ? root.workspaceController.itemPageSize : 25)
                    : (root.workspaceController ? root.workspaceController.categoryPageSize : 25)
                totalItems: root._isItemsView
                    ? (root.workspaceController ? root.workspaceController.itemTotalCount : 0)
                    : (root.workspaceController ? root.workspaceController.categoryTotalCount : 0)
                busy: root.workspaceController ? root.workspaceController.isBusy : false

                onPageRequested: function(page) {
                    if (root.workspaceController === null) return
                    if (root._isItemsView) root.workspaceController.setItemPage(page)
                    else                   root.workspaceController.setCategoryPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController === null) return
                    if (root._isItemsView) root.workspaceController.setItemPageSize(size)
                    else                   root.workspaceController.setCategoryPageSize(size)
                }
            }

            // ── Filter popup ──────────────────────────────────────────
            AppWidgets.BulkActionBar {
                id: _itemBulkBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                active: root._isItemsView
                selectedCount: root.workspaceController ? root.workspaceController.selectedItemCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [{ "id": "change_property", "label": "Change Property", "icon": "edit", "danger": false, "enabled": true }]

                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearItemBulkSelection() }
                onActionTriggered: function(actionId) { if (actionId === "change_property") _itemBulkChangePopup.open() }
            }

            AppWidgets.BulkActionBar {
                id: _categoryBulkBar
                anchors.horizontalCenter: parent.horizontalCenter
                anchors.bottom: _paginationBar.top
                anchors.bottomMargin: Theme.AppTheme.spacingMd
                z: 10
                active: !root._isItemsView
                selectedCount: root.workspaceController ? root.workspaceController.selectedCategoryCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false
                actions: [{ "id": "archive", "label": "Archive", "icon": "delete", "danger": true, "enabled": true }]

                onCancelRequested: { if (root.workspaceController !== null) root.workspaceController.clearCategoryBulkSelection() }
                onActionTriggered: function(actionId) {}
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem:  tableToolbar.filterButtonItem
                width:       304
                padding:     Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.AppTheme.radiusLg
                    color:  Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: 1
                }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "Status";        font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model:    root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                        textRole: "label"
                        enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.activeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedActiveFilter : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setActiveFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label { text: "Category";      font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model:    root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                        textRole: "label"
                        enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.categoryOptions || []) : [], root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setCategoryFilter(String(opts[index].value || "all"))
                        }
                    }

                    AppControls.Label { text: "Category Type"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model:    root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                        textRole: "label"
                        enabled:  !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : [], root.workspaceController ? root.workspaceController.selectedCategoryTypeFilter : "all")
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.categoryTypeOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) root.workspaceController.setCategoryTypeFilter(String(opts[index].value || "all"))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Clear"; iconName: "close"
                            onClicked: { if (root.workspaceController !== null) root.workspaceController.clearFilters(); filterPopup.close() }
                        }
                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            text: "Apply"; iconName: "filter"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: filterPopup.close()
                        }
                    }
                }
            }

            // ── Views popup ───────────────────────────────────────────
            AppWidgets.AnchoredPopup {
                id: viewsPopup
                anchorItem:  tableToolbar.viewsButtonItem
                width:       220
                padding:     Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle { radius: Theme.AppTheme.radiusLg; color: Theme.AppTheme.surfaceRaised; border.color: Theme.AppTheme.divider; border.width: 1 }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label { text: "View"; font.bold: true; font.pixelSize: Theme.AppTheme.captionSize; font.family: Theme.AppTheme.fontFamily; color: Theme.AppTheme.textMuted }

                    AppControls.PrimaryButton {
                        Layout.fillWidth: true
                        text: "Items"; iconName: "inventory"
                        enabled: !root._isItemsView
                        onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("items"); viewsPopup.close() }
                    }
                    AppControls.SecondaryButton {
                        Layout.fillWidth: true
                        text: "Categories"; iconName: "register"
                        enabled: root._isItemsView
                        onClicked: { if (root.workspaceController !== null) root.workspaceController.setActiveView("categories"); viewsPopup.close() }
                    }
                }
            }

            // ── Bulk action bar (items) ────────────────────────────────
            AppWidgets.BulkChangePropertyPopup {
                id: _itemBulkChangePopup
                anchorItem:    _itemBulkBar.actionButtonForId("change_property")
                selectedCount: root.workspaceController ? root.workspaceController.selectedItemCount : 0
                busy:          root.workspaceController ? root.workspaceController.isBusy : false
                properties:    root._bulkChangeProperties

                onApplyRequested: function(payload) {
                    if (root.workspaceController === null) return
                    if (payload.propertyId === "status")
                        root.workspaceController.applyBulkStatus({ "status": payload.value })
                }
            }

            // ── Bulk action bar (categories) ──────────────────────────
        }
    }
}
