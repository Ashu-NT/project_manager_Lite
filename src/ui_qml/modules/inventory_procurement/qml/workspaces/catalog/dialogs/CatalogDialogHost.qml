import QtQuick
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var workspaceController: null
    property var categoryTypeOptions: []
    property var categoryOptions: []
    property var itemStatusOptions: []
    property var businessPartyOptions: []
    property var availableDocuments: []
    property var categoryEditTarget: ({})
    property var itemEditTarget: ({})
    property var linkTarget: ({})

    function _handleResult(dialog, result) {
        if (!result || result.ok === false) {
            dialog.errorMessage = String((result && (result.error || result.message)) || "Operation failed. Please try again.")
        } else {
            dialog.errorMessage = ""
            dialog.close()
        }
    }

    function openCreateCategoryDialog() {
        root.categoryEditTarget = {
            "state": {
                "isActive": true
            }
        }
        categoryEditor.modeTitle = "Create Category"
        categoryEditor.categoryData = root.categoryEditTarget
        categoryEditor.errorMessage = ""
        categoryEditor.open()
    }

    function openEditCategoryDialog(categoryData) {
        root.categoryEditTarget = categoryData || ({})
        categoryEditor.modeTitle = "Edit Category"
        categoryEditor.categoryData = root.categoryEditTarget
        categoryEditor.errorMessage = ""
        categoryEditor.open()
    }

    function openCreateItemDialog() {
        root.itemEditTarget = {
            "state": {
                "status": root.itemStatusOptions.length > 0 ? String(root.itemStatusOptions[0].value || "") : "DRAFT",
                "stockUom": "EA",
                "orderUomRatio": "1.000",
                "issueUomRatio": "1.000",
                "minQty": "0.000",
                "maxQty": "0.000",
                "reorderPoint": "0.000",
                "reorderQty": "0.000",
                "isStocked": true,
                "isPurchaseAllowed": true
            }
        }
        itemEditor.modeTitle = "Create Item"
        itemEditor.itemData = root.itemEditTarget
        itemEditor.errorMessage = ""
        itemEditor.open()
    }

    function openEditItemDialog(itemData) {
        root.itemEditTarget = itemData || ({})
        itemEditor.modeTitle = "Edit Item"
        itemEditor.itemData = root.itemEditTarget
        itemEditor.errorMessage = ""
        itemEditor.open()
    }

    function openLinkDocumentDialog(itemData) {
        root.linkTarget = itemData || ({})
        var linkedIds = {}
        var linkedDocs = itemData && itemData.linkedDocuments ? itemData.linkedDocuments : []
        for (var index = 0; index < linkedDocs.length; index += 1) {
            linkedIds[String(linkedDocs[index].value || "")] = true
        }
        var remainingOptions = root.availableDocuments.filter(function(option) {
            return !linkedIds[String(option.value || "")]
        })
        documentLinkDialog.documentOptions = remainingOptions
        documentLinkDialog.errorMessage = ""
        documentLinkDialog.open()
    }

    InventoryDialogs.CategoryEditorDialog {
        id: categoryEditor
        objectName: "categoryEditorDialog"

        categoryTypeOptions: root.categoryTypeOptions
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            var state = root.categoryEditTarget && root.categoryEditTarget.state ? root.categoryEditTarget.state : (root.categoryEditTarget || {})
            if (state.categoryId) {
                payload.categoryId = state.categoryId
                payload.expectedVersion = state.version
                root._handleResult(categoryEditor, root.workspaceController.updateCategory(payload))
            } else {
                root._handleResult(categoryEditor, root.workspaceController.createCategory(payload))
            }
        }
    }

    InventoryDialogs.ItemEditorDialog {
        id: itemEditor
        objectName: "itemEditorDialog"

        itemStatusOptions: root.itemStatusOptions
        categoryOptions: root.categoryOptions
        businessPartyOptions: root.businessPartyOptions
        workspaceController: root.workspaceController
        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(payload) {
            var state = root.itemEditTarget && root.itemEditTarget.state ? root.itemEditTarget.state : (root.itemEditTarget || {})
            if (state.itemId) {
                payload.itemId = state.itemId
                payload.expectedVersion = state.version
                root._handleResult(itemEditor, root.workspaceController.updateItem(payload))
            } else {
                root._handleResult(itemEditor, root.workspaceController.createItem(payload))
            }
        }
    }

    InventoryDialogs.DocumentLinkDialog {
        id: documentLinkDialog
        objectName: "documentLinkDialog"

        busy: root.workspaceController ? root.workspaceController.isBusy : false

        onSubmitted: function(documentId) {
            var state = root.linkTarget && root.linkTarget.state ? root.linkTarget.state : (root.linkTarget || {})
            if (state.itemId) {
                root._handleResult(documentLinkDialog, root.workspaceController.linkDocument(String(state.itemId || ""), documentId))
            }
        }
    }
}
