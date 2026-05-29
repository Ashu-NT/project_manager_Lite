pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.inventoryWorkspace
        : null

    readonly property var transactionsModel: root.workspaceController
        ? root.workspaceController.transactions
        : ({ "items": [], "emptyState": "No stock movements." })

    title: "Stock Movements"
    subtitle: "Opening balances, adjustments, issues, returns, and transfer history."

    readonly property var _columns: [
        { "key": "title",       "label": "Movement",        "flex": 2,   "sortable": true  },
        { "key": "subtitle",    "label": "Item / Storeroom","flex": 1.5 },
        { "key": "statusLabel", "label": "Type",            "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "metaText",    "label": "Qty / Date",      "flex": 1 }
    ]

    function _optionIndexForValue(options, value) {
        const optList = options || []
        for (let i = 0; i < optList.length; i++) {
            if (String(optList[i].value || "") === String(value || "")) return i
        }
        return 0
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: (root.workspaceController ? root.workspaceController.isLoading : false)
                && String(root.workspaceController ? root.workspaceController.errorMessage : "").length === 0
            tone: "info"
            message: "Loading movements..."
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: String(root.workspaceController ? root.workspaceController.errorMessage : "").length > 0
            tone: "danger"
            message: root.workspaceController ? root.workspaceController.errorMessage : ""
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.searchText : ""
            searchPlaceholder: "Search movements..."
            showCreate: false
            showFilter: true
            showViews: false
            showRefresh: true
            showExport: false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked: filterPopup.open()
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: _movementsTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: _paginationBar.top
                multiSelect: false
                columns: root._columns
                sourceModel: root.workspaceController ? root.workspaceController.transactionsTableModel : null
                rows: root.transactionsModel.items || []
                loading: root.workspaceController ? root.workspaceController.isLoading : false
                emptyText: root.transactionsModel.emptyState || "No stock movements."

                onSortRequested: function(key) {}
            }

            AppWidgets.TablePaginationBar {
                id: _paginationBar
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.movementPage : 1
                pageSize: root.workspaceController ? root.workspaceController.movementPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.movementTotalCount : 0
                busy: root.workspaceController ? root.workspaceController.isBusy : false

                onPageRequested: function(page) {
                    if (root.workspaceController !== null) root.workspaceController.setMovementPage(page)
                }
                onPageSizeRequested: function(size) {
                    if (root.workspaceController !== null) root.workspaceController.setMovementPageSize(size)
                }
            }

            AppWidgets.AnchoredPopup {
                id: filterPopup
                anchorItem: tableToolbar.filterButtonItem
                width: 304
                padding: Theme.AppTheme.marginMd
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.AppTheme.radiusLg
                    color: Theme.AppTheme.surfaceRaised
                    border.color: Theme.AppTheme.divider
                    border.width: 1
                }

                contentItem: ColumnLayout {
                    spacing: Theme.AppTheme.spacingSm

                    AppControls.Label {
                        text: "Movement Type"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.transactionTypeOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.transactionTypeOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedTransactionTypeFilter : "all"
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.transactionTypeOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) {
                                root.workspaceController.setTransactionTypeFilter(String(opts[index].value || "all"))
                            }
                        }
                    }

                    AppControls.Label {
                        text: "Site"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.siteOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) {
                                root.workspaceController.setSiteFilter(String(opts[index].value || "all"))
                            }
                        }
                    }

                    AppControls.Label {
                        text: "Storeroom"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.storeroomOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) {
                                root.workspaceController.setStoreroomFilter(String(opts[index].value || "all"))
                            }
                        }
                    }

                    AppControls.Label {
                        text: "Item"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    AppControls.ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._optionIndexForValue(
                            root.workspaceController ? (root.workspaceController.itemOptions || []) : [],
                            root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                        )
                        onActivated: function(index) {
                            const opts = root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                            if (root.workspaceController !== null && opts[index]) {
                                root.workspaceController.setItemFilter(String(opts[index].value || "all"))
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.SecondaryButton {
                            Layout.fillWidth: true
                            text: "Clear"
                            iconName: "close"
                            onClicked: {
                                if (root.workspaceController !== null) root.workspaceController.clearFilters()
                                filterPopup.close()
                            }
                        }
                        AppControls.PrimaryButton {
                            Layout.fillWidth: true
                            text: "Apply"
                            iconName: "filter"
                            enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                            onClicked: filterPopup.close()
                        }
                    }
                }
            }
        }
    }
}
