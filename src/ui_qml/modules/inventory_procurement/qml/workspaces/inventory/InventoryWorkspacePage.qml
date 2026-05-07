import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementInventoryWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.inventoryWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.inventory",
            "title": "Inventory",
            "summary": "Storerooms, stock balances, adjustments, issues, returns, and transfer movements.",
            "migrationStatus": "QML stock operations slice active",
            "legacyRuntimeStatus": "Existing QWidget inventory workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var storeroomsModel: root.workspaceController
        ? root.workspaceController.storerooms
        : ({
            "title": "Storerooms",
            "subtitle": "Govern stock locations, operational permissions, and manager ownership.",
            "emptyState": "Inventory desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedStoreroomModel: root.workspaceController
        ? root.workspaceController.selectedStoreroom
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a storeroom to review governance settings, manager ownership, and operational flags.",
            "fields": [],
            "state": {}
        })
    readonly property var balancesModel: root.workspaceController
        ? root.workspaceController.balances
        : ({
            "title": "Stock Balances",
            "subtitle": "Inspect on-hand, reserved, available, and on-order positions by storeroom.",
            "emptyState": "Inventory desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedBalanceModel: root.workspaceController
        ? root.workspaceController.selectedBalance
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a balance row to inspect stock position or launch movement actions.",
            "fields": [],
            "state": {}
        })
    readonly property var transactionsModel: root.workspaceController
        ? root.workspaceController.transactions
        : ({
            "title": "Recent Movements",
            "subtitle": "Opening balances, adjustments, issues, returns, and transfer history.",
            "emptyState": "Inventory desktop API is not connected in this QML preview.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    InventoryDialogHost {
        id: dialogHost

        siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
        storeroomStatusOptions: root.workspaceController ? (root.workspaceController.storeroomStatusOptions || []) : []
        managerPartyOptions: root.workspaceController ? (root.workspaceController.managerPartyOptions || []) : []
        itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
        storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []

        onCreateStoreroomRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createStoreroom(payload)
            }
        }

        onUpdateStoreroomRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateStoreroom(payload)
            }
        }

        onPostOpeningBalanceRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.postOpeningBalance(payload)
            }
        }

        onPostAdjustmentRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.postAdjustment(payload)
            }
        }

        onIssueStockRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.issueStock(payload)
            }
        }

        onReturnStockRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.returnStock(payload)
            }
        }

        onTransferStockRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.transferStock(payload)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            InventoryMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            InventoryWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            InventoryWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML stock operations slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Storeroom CRUD, stock balance review, and opening balance, adjustment, issue, return, and transfer flows now run through a typed inventory controller backed by the split inventory desktop APIs."
            }

            InventoryFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                activeOptions: root.workspaceController ? (root.workspaceController.activeOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
                transactionTypeOptions: root.workspaceController ? (root.workspaceController.transactionTypeOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedActiveFilter: root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                selectedStoreroomFilter: root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                selectedItemFilter: root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                selectedTransactionTypeFilter: root.workspaceController ? root.workspaceController.selectedTransactionTypeFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onSiteFilterUpdated: function(siteId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSiteFilter(siteId)
                    }
                }

                onActiveFilterUpdated: function(activeValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setActiveFilter(activeValue)
                    }
                }

                onStoreroomFilterUpdated: function(storeroomId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStoreroomFilter(storeroomId)
                    }
                }

                onItemFilterUpdated: function(itemId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setItemFilter(itemId)
                    }
                }

                onTransactionTypeFilterUpdated: function(transactionType) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setTransactionTypeFilter(transactionType)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateStoreroomRequested: dialogHost.openCreateStoreroomDialog()

                onOpenOpeningBalanceRequested: dialogHost.openOpeningBalanceDialog(
                    root.selectedBalanceModel,
                    root.selectedStoreroomModel,
                    root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                )
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                StoreroomCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    storeroomsModel: root.storeroomsModel
                    selectedStoreroomId: root.workspaceController ? root.workspaceController.selectedStoreroomId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onStoreroomSelected: function(storeroomId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectStoreroom(storeroomId)
                        }
                    }

                    onEditRequested: function(storeroomData) {
                        if (storeroomData && storeroomData.id && root.workspaceController !== null) {
                            root.workspaceController.selectStoreroom(storeroomData.id)
                        }
                        dialogHost.openEditStoreroomDialog(storeroomData)
                    }

                    onToggleRequested: function(storeroomData) {
                        if (!storeroomData || !storeroomData.state || root.workspaceController === null) {
                            return
                        }
                        root.workspaceController.toggleStoreroomActive(
                            String(storeroomData.state.storeroomId || ""),
                            parseInt(String(storeroomData.state.version || "0"), 10)
                        )
                    }
                }

                StoreroomDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    storeroomDetail: root.selectedStoreroomModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditStoreroomDialog(root.selectedStoreroomModel)

                    onToggleRequested: {
                        var state = root.selectedStoreroomModel && root.selectedStoreroomModel.state
                            ? root.selectedStoreroomModel.state
                            : {}
                        if (root.workspaceController !== null && state.storeroomId) {
                            root.workspaceController.toggleStoreroomActive(
                                String(state.storeroomId || ""),
                                parseInt(String(state.version || "0"), 10)
                            )
                        }
                    }

                    onOpeningBalanceRequested: dialogHost.openOpeningBalanceDialog(
                        root.selectedBalanceModel,
                        root.selectedStoreroomModel,
                        root.workspaceController ? root.workspaceController.selectedItemFilter : "all"
                    )
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                BalanceCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    balancesModel: root.balancesModel
                    selectedBalanceId: root.workspaceController ? root.workspaceController.selectedBalanceId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onBalanceSelected: function(balanceId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectBalance(balanceId)
                        }
                    }

                    onIssueRequested: function(balanceData) {
                        if (balanceData && balanceData.id && root.workspaceController !== null) {
                            root.workspaceController.selectBalance(balanceData.id)
                        }
                        dialogHost.openIssueDialog(balanceData)
                    }

                    onAdjustmentRequested: function(balanceData) {
                        if (balanceData && balanceData.id && root.workspaceController !== null) {
                            root.workspaceController.selectBalance(balanceData.id)
                        }
                        dialogHost.openAdjustmentDialog(balanceData)
                    }

                    onTransferRequested: function(balanceData) {
                        if (balanceData && balanceData.id && root.workspaceController !== null) {
                            root.workspaceController.selectBalance(balanceData.id)
                        }
                        dialogHost.openTransferDialog(balanceData)
                    }
                }

                BalanceDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    balanceDetail: root.selectedBalanceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onAdjustmentRequested: dialogHost.openAdjustmentDialog(root.selectedBalanceModel)
                    onIssueRequested: dialogHost.openIssueDialog(root.selectedBalanceModel)
                    onReturnRequested: dialogHost.openReturnDialog(root.selectedBalanceModel)
                    onTransferRequested: dialogHost.openTransferDialog(root.selectedBalanceModel)
                }
            }

            TransactionsSection {
                Layout.fillWidth: true
                transactionsModel: root.transactionsModel
            }
        }
    }
}
