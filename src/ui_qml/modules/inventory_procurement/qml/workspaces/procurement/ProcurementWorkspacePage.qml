import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import InventoryProcurement.Widgets 1.0 as InventoryWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property InventoryProcurementControllers.InventoryProcurementProcurementWorkspaceController workspaceController: root.inventoryCatalog
        ? root.inventoryCatalog.procurementWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "inventory_procurement.procurement",
            "title": "Procurement",
            "summary": "Requisitions, purchase orders, receiving, and supplier-facing fulfillment workflows.",
            "migrationStatus": "QML procurement slice active",
            "legacyRuntimeStatus": "Existing QWidget procurement workspaces remain active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var requisitionsModel: root.workspaceController
        ? root.workspaceController.requisitions
        : ({
            "title": "Requisitions",
            "subtitle": "",
            "emptyState": "Procurement desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedRequisitionModel: root.workspaceController
        ? root.workspaceController.selectedRequisition
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a requisition to review demand details.",
            "fields": [],
            "state": {}
        })
    readonly property var requisitionLinesModel: root.workspaceController
        ? root.workspaceController.requisitionLines
        : ({
            "title": "Requisition Lines",
            "subtitle": "",
            "emptyState": "Select a requisition to review its demand lines.",
            "items": []
        })
    readonly property var purchaseOrdersModel: root.workspaceController
        ? root.workspaceController.purchaseOrders
        : ({
            "title": "Purchase Orders",
            "subtitle": "",
            "emptyState": "Procurement desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedPurchaseOrderModel: root.workspaceController
        ? root.workspaceController.selectedPurchaseOrder
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a purchase order to review supplier commitments.",
            "fields": [],
            "state": {}
        })
    readonly property var purchaseOrderLinesModel: root.workspaceController
        ? root.workspaceController.purchaseOrderLines
        : ({
            "title": "Purchase-Order Lines",
            "subtitle": "",
            "emptyState": "Select a purchase order to review its supplier commitment lines.",
            "items": []
        })
    readonly property var receiptsModel: root.workspaceController
        ? root.workspaceController.receipts
        : ({
            "title": "Receipt History",
            "subtitle": "",
            "emptyState": "Select a purchase order to review receipt history.",
            "items": []
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    ProcurementDialogHost {
        id: dialogHost

        siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
        storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
        supplierOptions: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
        itemOptions: root.workspaceController ? (root.workspaceController.itemOptions || []) : []
        requisitionOptions: root.workspaceController ? (root.workspaceController.requisitionOptions || []) : []
        requisitionLineOptions: root.workspaceController ? (root.workspaceController.requisitionLineOptions || []) : []

        onCreateRequisitionRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createRequisition(payload)
            }
        }

        onUpdateRequisitionRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateRequisition(payload)
            }
        }

        onAddRequisitionLineRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.addRequisitionLine(payload)
            }
        }

        onCreatePurchaseOrderRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createPurchaseOrder(payload)
            }
        }

        onUpdatePurchaseOrderRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updatePurchaseOrder(payload)
            }
        }

        onAddPurchaseOrderLineRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.addPurchaseOrderLine(payload)
            }
        }

        onPostReceiptRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.postReceipt(payload)
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

            ProcurementMetricsSection {
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
                    ? "QML procurement slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Requisition capture, supplier-facing purchase-order commitments, and receipt posting now run through a typed procurement controller backed by the split procurement desktop API."
            }

            ProcurementFiltersSection {
                Layout.fillWidth: true
                siteOptions: root.workspaceController ? (root.workspaceController.siteOptions || []) : []
                storeroomOptions: root.workspaceController ? (root.workspaceController.storeroomOptions || []) : []
                supplierOptions: root.workspaceController ? (root.workspaceController.supplierOptions || []) : []
                requisitionStatusOptions: root.workspaceController ? (root.workspaceController.requisitionStatusOptions || []) : []
                purchaseOrderStatusOptions: root.workspaceController ? (root.workspaceController.purchaseOrderStatusOptions || []) : []
                selectedSiteFilter: root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                selectedStoreroomFilter: root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                selectedSupplierFilter: root.workspaceController ? root.workspaceController.selectedSupplierFilter : "all"
                selectedRequisitionStatusFilter: root.workspaceController ? root.workspaceController.selectedRequisitionStatusFilter : "all"
                selectedPurchaseOrderStatusFilter: root.workspaceController ? root.workspaceController.selectedPurchaseOrderStatusFilter : "all"
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

                onStoreroomFilterUpdated: function(storeroomId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStoreroomFilter(storeroomId)
                    }
                }

                onSupplierFilterUpdated: function(supplierId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSupplierFilter(supplierId)
                    }
                }

                onRequisitionStatusFilterUpdated: function(status) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setRequisitionStatusFilter(status)
                    }
                }

                onPurchaseOrderStatusFilterUpdated: function(status) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setPurchaseOrderStatusFilter(status)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateRequisitionRequested: dialogHost.openCreateRequisitionDialog(
                    root.workspaceController ? root.workspaceController.selectedSiteFilter : "all",
                    root.workspaceController ? root.workspaceController.selectedStoreroomFilter : "all"
                )

                onCreatePurchaseOrderRequested: dialogHost.openCreatePurchaseOrderDialog(
                    root.selectedRequisitionModel,
                    root.workspaceController ? root.workspaceController.selectedSiteFilter : "all"
                )
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                RequisitionCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    requisitionsModel: root.requisitionsModel
                    selectedRequisitionId: root.workspaceController ? root.workspaceController.selectedRequisitionId : ""

                    onRequisitionSelected: function(requisitionId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectRequisition(requisitionId)
                        }
                    }
                }

                RequisitionDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    requisitionDetail: root.selectedRequisitionModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditRequisitionDialog(root.selectedRequisitionModel)
                    onAddLineRequested: dialogHost.openRequisitionLineDialog(root.selectedRequisitionModel)

                    onSubmitRequested: {
                        var state = root.selectedRequisitionModel && root.selectedRequisitionModel.state
                            ? root.selectedRequisitionModel.state
                            : {}
                        if (root.workspaceController !== null && state.requisitionId) {
                            root.workspaceController.submitRequisition(String(state.requisitionId || ""))
                        }
                    }

                    onCancelRequested: {
                        var state = root.selectedRequisitionModel && root.selectedRequisitionModel.state
                            ? root.selectedRequisitionModel.state
                            : {}
                        if (root.workspaceController !== null && state.requisitionId) {
                            root.workspaceController.cancelRequisition(String(state.requisitionId || ""))
                        }
                    }
                }
            }

            RequisitionLinesSection {
                Layout.fillWidth: true
                lineModel: root.requisitionLinesModel
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                PurchaseOrderCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    purchaseOrdersModel: root.purchaseOrdersModel
                    selectedPurchaseOrderId: root.workspaceController ? root.workspaceController.selectedPurchaseOrderId : ""

                    onPurchaseOrderSelected: function(purchaseOrderId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectPurchaseOrder(purchaseOrderId)
                        }
                    }
                }

                PurchaseOrderDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    purchaseOrderDetail: root.selectedPurchaseOrderModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditPurchaseOrderDialog(root.selectedPurchaseOrderModel)
                    onAddLineRequested: dialogHost.openPurchaseOrderLineDialog(root.selectedPurchaseOrderModel)

                    onSubmitRequested: {
                        var state = root.selectedPurchaseOrderModel && root.selectedPurchaseOrderModel.state
                            ? root.selectedPurchaseOrderModel.state
                            : {}
                        if (root.workspaceController !== null && state.purchaseOrderId) {
                            root.workspaceController.submitPurchaseOrder(String(state.purchaseOrderId || ""))
                        }
                    }

                    onSendRequested: {
                        var state = root.selectedPurchaseOrderModel && root.selectedPurchaseOrderModel.state
                            ? root.selectedPurchaseOrderModel.state
                            : {}
                        if (root.workspaceController !== null && state.purchaseOrderId) {
                            root.workspaceController.sendPurchaseOrder(String(state.purchaseOrderId || ""))
                        }
                    }

                    onCancelRequested: {
                        var state = root.selectedPurchaseOrderModel && root.selectedPurchaseOrderModel.state
                            ? root.selectedPurchaseOrderModel.state
                            : {}
                        if (root.workspaceController !== null && state.purchaseOrderId) {
                            root.workspaceController.cancelPurchaseOrder(String(state.purchaseOrderId || ""))
                        }
                    }

                    onCloseRequested: {
                        var state = root.selectedPurchaseOrderModel && root.selectedPurchaseOrderModel.state
                            ? root.selectedPurchaseOrderModel.state
                            : {}
                        if (root.workspaceController !== null && state.purchaseOrderId) {
                            root.workspaceController.closePurchaseOrder(String(state.purchaseOrderId || ""))
                        }
                    }

                    onPostReceiptRequested: dialogHost.openReceiptPostDialog(
                        root.selectedPurchaseOrderModel,
                        root.purchaseOrderLinesModel.items || []
                    )
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                PurchaseOrderLinesSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    lineModel: root.purchaseOrderLinesModel
                }

                ReceiptHistorySection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    receiptsModel: root.receiptsModel
                }
            }
        }
    }
}
