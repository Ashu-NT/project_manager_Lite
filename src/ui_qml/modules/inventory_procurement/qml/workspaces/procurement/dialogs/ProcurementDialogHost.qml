import QtQuick
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var workspaceController: null
    property var siteOptions: []
    property var storeroomOptions: []
    property var supplierOptions: []
    property var itemOptions: []
    property var requisitionOptions: []
    property var requisitionLineOptions: []
    property var requisitionEditTarget: ({})
    property var purchaseOrderEditTarget: ({})
    property var lineTarget: ({})

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

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
        requisitionEditor.errorMessage = ""
        requisitionEditor.open()
    }

    function openEditRequisitionDialog(requisitionData) {
        root.requisitionEditTarget = requisitionData || ({})
        requisitionEditor.modeTitle = "Edit Requisition"
        requisitionEditor.requisitionData = root.requisitionEditTarget
        requisitionEditor.errorMessage = ""
        requisitionEditor.open()
    }

    function openRequisitionLineDialog(requisitionData) {
        root.lineTarget = requisitionData || ({})
        requisitionLineDialog.requisitionData = root.lineTarget
        requisitionLineDialog.errorMessage = ""
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
        purchaseOrderEditor.errorMessage = ""
        purchaseOrderEditor.open()
    }

    function openEditPurchaseOrderDialog(purchaseOrderData) {
        root.purchaseOrderEditTarget = purchaseOrderData || ({})
        purchaseOrderEditor.modeTitle = "Edit Purchase Order"
        purchaseOrderEditor.purchaseOrderData = root.purchaseOrderEditTarget
        purchaseOrderEditor.errorMessage = ""
        purchaseOrderEditor.open()
    }

    function openPurchaseOrderLineDialog(purchaseOrderData) {
        root.lineTarget = purchaseOrderData || ({})
        purchaseOrderLineDialog.purchaseOrderData = root.lineTarget
        purchaseOrderLineDialog.errorMessage = ""
        purchaseOrderLineDialog.open()
    }

    function openReceiptPostDialog(purchaseOrderData, purchaseOrderLines) {
        receiptDialog.purchaseOrderData = purchaseOrderData || ({})
        receiptDialog.purchaseOrderLines = purchaseOrderLines || []
        receiptDialog.errorMessage = ""
        receiptDialog.open()
    }

    InventoryDialogs.RequisitionEditorDialog {
        id: requisitionEditor
        objectName: "requisitionEditorDialog"

        siteOptions: root.siteOptions
        storeroomOptions: root.storeroomOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            var state = root.requisitionEditTarget && root.requisitionEditTarget.state ? root.requisitionEditTarget.state : (root.requisitionEditTarget || {})
            if (state.requisitionId) {
                payload.requisitionId = state.requisitionId
                payload.expectedVersion = state.version
                root._handleResult(requisitionEditor, root.workspaceController.updateRequisition(payload))
            } else {
                root._handleResult(requisitionEditor, root.workspaceController.createRequisition(payload))
            }
        }
    }

    InventoryDialogs.RequisitionLineDialog {
        id: requisitionLineDialog
        objectName: "requisitionLineDialog"

        itemOptions: root.itemOptions
        supplierOptions: root.supplierOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            root._handleResult(requisitionLineDialog, root.workspaceController.addRequisitionLine(payload))
        }
    }

    InventoryDialogs.PurchaseOrderEditorDialog {
        id: purchaseOrderEditor
        objectName: "purchaseOrderEditorDialog"

        siteOptions: root.siteOptions
        supplierOptions: root.supplierOptions
        requisitionOptions: root.requisitionOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            var state = root.purchaseOrderEditTarget && root.purchaseOrderEditTarget.state ? root.purchaseOrderEditTarget.state : (root.purchaseOrderEditTarget || {})
            if (state.purchaseOrderId) {
                payload.purchaseOrderId = state.purchaseOrderId
                payload.expectedVersion = state.version
                root._handleResult(purchaseOrderEditor, root.workspaceController.updatePurchaseOrder(payload))
            } else {
                root._handleResult(purchaseOrderEditor, root.workspaceController.createPurchaseOrder(payload))
            }
        }
    }

    InventoryDialogs.PurchaseOrderLineDialog {
        id: purchaseOrderLineDialog
        objectName: "purchaseOrderLineDialog"

        itemOptions: root.itemOptions
        storeroomOptions: root.storeroomOptions
        requisitionLineOptions: root.requisitionLineOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            root._handleResult(purchaseOrderLineDialog, root.workspaceController.addPurchaseOrderLine(payload))
        }
    }

    InventoryDialogs.ReceiptPostDialog {
        id: receiptDialog
        objectName: "receiptPostDialog"

        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            root._handleResult(receiptDialog, root.workspaceController.postReceipt(payload))
        }
    }
}
