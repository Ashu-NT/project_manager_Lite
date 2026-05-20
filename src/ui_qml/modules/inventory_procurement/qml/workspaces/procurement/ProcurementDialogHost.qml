import QtQuick
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var siteOptions: []
    property var storeroomOptions: []
    property var supplierOptions: []
    property var itemOptions: []
    property var requisitionOptions: []
    property var requisitionLineOptions: []
    property var requisitionEditTarget: ({})
    property var purchaseOrderEditTarget: ({})
    property var lineTarget: ({})

    signal createRequisitionRequested(var payload)
    signal updateRequisitionRequested(var payload)
    signal addRequisitionLineRequested(var payload)
    signal createPurchaseOrderRequested(var payload)
    signal updatePurchaseOrderRequested(var payload)
    signal addPurchaseOrderLineRequested(var payload)
    signal postReceiptRequested(var payload)

    function openCreateRequisitionDialog(defaultSiteId, defaultStoreroomId) {
        root.requisitionEditTarget = {
            "state": {
                "requestingSiteId": String(defaultSiteId || "") === "all" ? "" : String(defaultSiteId || ""),
                "requestingStoreroomId": String(defaultStoreroomId || "") === "all" ? "" : String(defaultStoreroomId || ""),
                "priority": "NORMAL"
            }
        }
        requisitionEditor.modeTitle = "Create Requisition"
        requisitionEditor.requisitionData = root.requisitionEditTarget
        requisitionEditor.open()
    }

    function openEditRequisitionDialog(requisitionData) {
        root.requisitionEditTarget = requisitionData || ({})
        requisitionEditor.modeTitle = "Edit Requisition"
        requisitionEditor.requisitionData = root.requisitionEditTarget
        requisitionEditor.open()
    }

    function openRequisitionLineDialog(requisitionData) {
        root.lineTarget = requisitionData || ({})
        requisitionLineDialog.requisitionData = root.lineTarget
        requisitionLineDialog.open()
    }

    function openCreatePurchaseOrderDialog(requisitionData, defaultSiteId) {
        var requisitionState = requisitionData && requisitionData.state ? requisitionData.state : (requisitionData || {})
        root.purchaseOrderEditTarget = {
            "state": {
                "siteId": String(requisitionState.requestingSiteId || (String(defaultSiteId || "") === "all" ? "" : String(defaultSiteId || ""))),
                "sourceRequisitionId": String(requisitionState.requisitionId || ""),
                "currencyCode": ""
            }
        }
        purchaseOrderEditor.modeTitle = "Create Purchase Order"
        purchaseOrderEditor.purchaseOrderData = root.purchaseOrderEditTarget
        purchaseOrderEditor.open()
    }

    function openEditPurchaseOrderDialog(purchaseOrderData) {
        root.purchaseOrderEditTarget = purchaseOrderData || ({})
        purchaseOrderEditor.modeTitle = "Edit Purchase Order"
        purchaseOrderEditor.purchaseOrderData = root.purchaseOrderEditTarget
        purchaseOrderEditor.open()
    }

    function openPurchaseOrderLineDialog(purchaseOrderData) {
        root.lineTarget = purchaseOrderData || ({})
        purchaseOrderLineDialog.purchaseOrderData = root.lineTarget
        purchaseOrderLineDialog.open()
    }

    function openReceiptPostDialog(purchaseOrderData, purchaseOrderLines) {
        receiptDialog.purchaseOrderData = purchaseOrderData || ({})
        receiptDialog.purchaseOrderLines = purchaseOrderLines || []
        receiptDialog.open()
    }

    InventoryDialogs.RequisitionEditorDialog {
        id: requisitionEditor
        objectName: "requisitionEditorDialog"

        siteOptions: root.siteOptions
        storeroomOptions: root.storeroomOptions

        onSubmitted: function(payload) {
            var state = root.requisitionEditTarget && root.requisitionEditTarget.state ? root.requisitionEditTarget.state : (root.requisitionEditTarget || {})
            if (state.requisitionId) {
                payload.requisitionId = state.requisitionId
                payload.expectedVersion = state.version
                root.updateRequisitionRequested(payload)
            } else {
                root.createRequisitionRequested(payload)
            }
            requisitionEditor.close()
        }
    }

    InventoryDialogs.RequisitionLineDialog {
        id: requisitionLineDialog
        objectName: "requisitionLineDialog"

        itemOptions: root.itemOptions
        supplierOptions: root.supplierOptions

        onSubmitted: function(payload) {
            root.addRequisitionLineRequested(payload)
            requisitionLineDialog.close()
        }
    }

    InventoryDialogs.PurchaseOrderEditorDialog {
        id: purchaseOrderEditor
        objectName: "purchaseOrderEditorDialog"

        siteOptions: root.siteOptions
        supplierOptions: root.supplierOptions
        requisitionOptions: root.requisitionOptions

        onSubmitted: function(payload) {
            var state = root.purchaseOrderEditTarget && root.purchaseOrderEditTarget.state ? root.purchaseOrderEditTarget.state : (root.purchaseOrderEditTarget || {})
            if (state.purchaseOrderId) {
                payload.purchaseOrderId = state.purchaseOrderId
                payload.expectedVersion = state.version
                root.updatePurchaseOrderRequested(payload)
            } else {
                root.createPurchaseOrderRequested(payload)
            }
            purchaseOrderEditor.close()
        }
    }

    InventoryDialogs.PurchaseOrderLineDialog {
        id: purchaseOrderLineDialog
        objectName: "purchaseOrderLineDialog"

        itemOptions: root.itemOptions
        storeroomOptions: root.storeroomOptions
        requisitionLineOptions: root.requisitionLineOptions

        onSubmitted: function(payload) {
            root.addPurchaseOrderLineRequested(payload)
            purchaseOrderLineDialog.close()
        }
    }

    InventoryDialogs.ReceiptPostDialog {
        id: receiptDialog
        objectName: "receiptPostDialog"

        onSubmitted: function(payload) {
            root.postReceiptRequested(payload)
            receiptDialog.close()
        }
    }
}
