import QtQuick
import InventoryProcurement.Dialogs 1.0 as InventoryDialogs

Item {
    id: root

    property var categoryTypeOptions: []
    property var categoryOptions: []
    property var itemStatusOptions: []
    property var businessPartyOptions: []
    property var availableDocuments: []
    property var categoryEditTarget: ({})
    property var itemEditTarget: ({})
    property var linkTarget: ({})

    signal createCategoryRequested(var payload)
    signal updateCategoryRequested(var payload)
    signal createItemRequested(var payload)
    signal updateItemRequested(var payload)
    signal linkDocumentRequested(string itemId, string documentId)

    function openCreateCategoryDialog() {
        root.categoryEditTarget = {
            "state": {
                "isActive": true
            }
        }
        categoryEditor.modeTitle = "Create Category"
        categoryEditor.categoryData = root.categoryEditTarget
        categoryEditor.open()
    }

    function openEditCategoryDialog(categoryData) {
        root.categoryEditTarget = categoryData || ({})
        categoryEditor.modeTitle = "Edit Category"
        categoryEditor.categoryData = root.categoryEditTarget
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
        itemEditor.open()
    }

    function openEditItemDialog(itemData) {
        root.itemEditTarget = itemData || ({})
        itemEditor.modeTitle = "Edit Item"
        itemEditor.itemData = root.itemEditTarget
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
        documentLinkDialog.open()
    }

    InventoryDialogs.CategoryEditorDialog {
        id: categoryEditor
        objectName: "categoryEditorDialog"

        categoryTypeOptions: root.categoryTypeOptions

        onSubmitted: function(payload) {
            var state = root.categoryEditTarget && root.categoryEditTarget.state ? root.categoryEditTarget.state : (root.categoryEditTarget || {})
            if (state.categoryId) {
                payload.categoryId = state.categoryId
                payload.expectedVersion = state.version
                root.updateCategoryRequested(payload)
            } else {
                root.createCategoryRequested(payload)
            }
            categoryEditor.close()
        }
    }

    InventoryDialogs.ItemEditorDialog {
        id: itemEditor
        objectName: "itemEditorDialog"

        itemStatusOptions: root.itemStatusOptions
        categoryOptions: root.categoryOptions
        businessPartyOptions: root.businessPartyOptions

        onSubmitted: function(payload) {
            var state = root.itemEditTarget && root.itemEditTarget.state ? root.itemEditTarget.state : (root.itemEditTarget || {})
            if (state.itemId) {
                payload.itemId = state.itemId
                payload.expectedVersion = state.version
                root.updateItemRequested(payload)
            } else {
                root.createItemRequested(payload)
            }
            itemEditor.close()
        }
    }

    InventoryDialogs.DocumentLinkDialog {
        id: documentLinkDialog
        objectName: "documentLinkDialog"

        onSubmitted: function(documentId) {
            var state = root.linkTarget && root.linkTarget.state ? root.linkTarget.state : (root.linkTarget || {})
            if (state.itemId) {
                root.linkDocumentRequested(String(state.itemId || ""), documentId)
            }
            documentLinkDialog.close()
        }
    }
}
