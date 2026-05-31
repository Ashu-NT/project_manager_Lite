import QtQuick
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var workspaceController: null
    property var siteOptions: []
    property var storeroomStatusOptions: []
    property var managerPartyOptions: []
    property var itemOptions: []
    property var storeroomOptions: []
    property var storeroomEditTarget: ({})
    property var movementTarget: ({})
    property var transferTarget: ({})

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

    function openCreateStoreroomDialog() {
        root.storeroomEditTarget = {
            "state": {
                "status": root.storeroomStatusOptions.length > 0 ? String(root.storeroomStatusOptions[0].value || "") : "DRAFT",
                "allowsIssue": true,
                "allowsTransfer": true,
                "allowsReceiving": true
            }
        }
        storeroomEditor.modeTitle = "Create Storeroom"
        storeroomEditor.storeroomData = root.storeroomEditTarget
        storeroomEditor.errorMessage = ""
        storeroomEditor.open()
    }

    function openEditStoreroomDialog(storeroomData) {
        root.storeroomEditTarget = storeroomData || ({})
        storeroomEditor.modeTitle = "Edit Storeroom"
        storeroomEditor.storeroomData = root.storeroomEditTarget
        storeroomEditor.errorMessage = ""
        storeroomEditor.open()
    }

    function buildMovementSeed(balanceData, storeroomData, itemFilterValue) {
        var balanceState = balanceData && balanceData.state ? balanceData.state : (balanceData || {})
        var storeroomState = storeroomData && storeroomData.state ? storeroomData.state : (storeroomData || {})
        var stockItemId = String(balanceState.stockItemId || "")
        if (stockItemId.length === 0 && String(itemFilterValue || "") !== "all") {
            stockItemId = String(itemFilterValue || "")
        }
        return {
            "state": {
                "stockItemId": stockItemId,
                "storeroomId": String(balanceState.storeroomId || storeroomState.storeroomId || ""),
                "uom": String(balanceState.uom || ""),
                "averageCost": String(balanceState.averageCost || "")
            }
        }
    }

    function openOpeningBalanceDialog(balanceData, storeroomData, itemFilterValue) {
        root.movementTarget = root.buildMovementSeed(balanceData, storeroomData, itemFilterValue)
        movementDialog.modeTitle = "Post Opening Balance"
        movementDialog.submitLabel = "Post"
        movementDialog.showDirection = false
        movementDialog.showReferenceFields = false
        movementDialog.showReleaseReservedField = false
        movementDialog.defaultReferenceType = ""
        movementDialog.defaultDirection = "INCREASE"
        movementDialog.movementData = root.movementTarget
        movementDialog.errorMessage = ""
        movementDialog.visible = true
        movementDialog.open()
        root._movementMode = "opening"
    }

    function openAdjustmentDialog(balanceData) {
        root.movementTarget = root.buildMovementSeed(balanceData, null, "")
        movementDialog.modeTitle = "Post Adjustment"
        movementDialog.submitLabel = "Post"
        movementDialog.showDirection = true
        movementDialog.showReferenceFields = true
        movementDialog.showReleaseReservedField = false
        movementDialog.defaultReferenceType = "adjustment"
        movementDialog.defaultDirection = "INCREASE"
        movementDialog.movementData = root.movementTarget
        movementDialog.errorMessage = ""
        movementDialog.open()
        root._movementMode = "adjustment"
    }

    function openIssueDialog(balanceData) {
        root.movementTarget = root.buildMovementSeed(balanceData, null, "")
        movementDialog.modeTitle = "Issue Stock"
        movementDialog.submitLabel = "Issue"
        movementDialog.showDirection = false
        movementDialog.showReferenceFields = true
        movementDialog.showReleaseReservedField = true
        movementDialog.defaultReferenceType = "issue"
        movementDialog.defaultDirection = "DECREASE"
        movementDialog.movementData = root.movementTarget
        movementDialog.errorMessage = ""
        movementDialog.open()
        root._movementMode = "issue"
    }

    function openReturnDialog(balanceData) {
        root.movementTarget = root.buildMovementSeed(balanceData, null, "")
        movementDialog.modeTitle = "Return Stock"
        movementDialog.submitLabel = "Return"
        movementDialog.showDirection = false
        movementDialog.showReferenceFields = true
        movementDialog.showReleaseReservedField = false
        movementDialog.defaultReferenceType = "return"
        movementDialog.defaultDirection = "INCREASE"
        movementDialog.movementData = root.movementTarget
        movementDialog.errorMessage = ""
        movementDialog.open()
        root._movementMode = "return"
    }

    function openTransferDialog(balanceData) {
        root.transferTarget = root.buildMovementSeed(balanceData, null, "")
        transferDialog.transferData = root.transferTarget
        transferDialog.errorMessage = ""
        transferDialog.open()
    }

    property string _movementMode: ""

    InventoryDialogs.StoreroomEditorDialog {
        id: storeroomEditor
        objectName: "storeroomEditorDialog"

        siteOptions: root.siteOptions
        statusOptions: root.storeroomStatusOptions
        managerPartyOptions: root.managerPartyOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            var state = root.storeroomEditTarget && root.storeroomEditTarget.state ? root.storeroomEditTarget.state : (root.storeroomEditTarget || {})
            if (state.storeroomId) {
                payload.storeroomId = state.storeroomId
                payload.expectedVersion = state.version
                root._handleResult(storeroomEditor, root.workspaceController.updateStoreroom(payload))
            } else {
                root._handleResult(storeroomEditor, root.workspaceController.createStoreroom(payload))
            }
        }
    }

    InventoryDialogs.StockMovementDialog {
        id: movementDialog
        objectName: "stockMovementDialog"

        itemOptions: root.itemOptions
        storeroomOptions: root.storeroomOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            if (root._movementMode === "opening") {
                root._handleResult(movementDialog, root.workspaceController.postOpeningBalance(payload))
            } else if (root._movementMode === "adjustment") {
                root._handleResult(movementDialog, root.workspaceController.postAdjustment(payload))
            } else if (root._movementMode === "issue") {
                root._handleResult(movementDialog, root.workspaceController.issueStock(payload))
            } else if (root._movementMode === "return") {
                root._handleResult(movementDialog, root.workspaceController.returnStock(payload))
            }
        }
    }

    InventoryDialogs.StockTransferDialog {
        id: transferDialog
        objectName: "stockTransferDialog"

        itemOptions: root.itemOptions
        storeroomOptions: root.storeroomOptions
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            root._handleResult(transferDialog, root.workspaceController.transferStock(payload))
        }
    }
}
