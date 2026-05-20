import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Item"
    property var itemStatusOptions: []
    property var categoryOptions: []
    property var businessPartyOptions: []
    property var itemData: ({})
    property string validationMessage: ""
    readonly property var formCategoryOptions: categoryOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    modal: true
    width: 760
    height: Math.min(860, parent ? parent.height - (Theme.AppTheme.marginLg * 2) : 860)
    title: root.modeTitle
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromItem() {
        var state = root.itemData && root.itemData.state ? root.itemData.state : (root.itemData || {})
        itemCodeField.text = String(state.itemCode || "")
        nameField.text = String(state.name || "")
        descriptionField.text = String(state.description || "")
        itemTypeField.text = String(state.itemType || "")
        statusCombo.currentIndex = root.indexForValue(root.itemStatusOptions, state.status || "")
        stockUomField.text = String(state.stockUom || "")
        orderUomField.text = String(state.orderUom || "")
        issueUomField.text = String(state.issueUom || "")
        orderRatioField.text = String(state.orderUomRatio || "1.000")
        issueRatioField.text = String(state.issueUomRatio || "1.000")
        categoryCombo.currentIndex = root.indexForValue(root.formCategoryOptions, state.categoryCode || "")
        commodityCodeField.text = String(state.commodityCode || "")
        reorderPolicyField.text = String(state.defaultReorderPolicy || "")
        preferredPartyCombo.currentIndex = root.indexForValue(root.businessPartyOptions, state.preferredPartyId || "")
        minQtyField.text = String(state.minQty || "0.000")
        maxQtyField.text = String(state.maxQty || "0.000")
        reorderPointField.text = String(state.reorderPoint || "0.000")
        reorderQtyField.text = String(state.reorderQty || "0.000")
        leadTimeDaysField.text = String(state.leadTimeDays || "")
        shelfLifeDaysField.text = String(state.shelfLifeDays || "")
        stockedCheck.checked = state.isStocked !== false
        purchaseAllowedCheck.checked = state.isPurchaseAllowed !== false
        lotTrackedCheck.checked = state.isLotTracked === true
        serialTrackedCheck.checked = state.isSerialTracked === true
        notesField.text = String(state.notes || "")
        root.validationMessage = ""
    }

    function buildPayload() {
        var selectedStatus = root.itemStatusOptions[statusCombo.currentIndex] || { "value": "" }
        var selectedCategory = root.formCategoryOptions[categoryCombo.currentIndex] || { "value": "" }
        var selectedParty = root.businessPartyOptions[preferredPartyCombo.currentIndex] || { "value": "" }
        return {
            "itemCode": itemCodeField.text,
            "name": nameField.text,
            "description": descriptionField.text,
            "itemType": itemTypeField.text,
            "status": String(selectedStatus.value || ""),
            "stockUom": stockUomField.text,
            "orderUom": orderUomField.text,
            "issueUom": issueUomField.text,
            "orderUomRatio": orderRatioField.text,
            "issueUomRatio": issueRatioField.text,
            "categoryCode": String(selectedCategory.value || ""),
            "commodityCode": commodityCodeField.text,
            "isStocked": stockedCheck.checked,
            "isPurchaseAllowed": purchaseAllowedCheck.checked,
            "defaultReorderPolicy": reorderPolicyField.text,
            "minQty": minQtyField.text,
            "maxQty": maxQtyField.text,
            "reorderPoint": reorderPointField.text,
            "reorderQty": reorderQtyField.text,
            "leadTimeDays": leadTimeDaysField.text,
            "shelfLifeDays": shelfLifeDaysField.text,
            "isLotTracked": lotTrackedCheck.checked,
            "isSerialTracked": serialTrackedCheck.checked,
            "preferredPartyId": String(selectedParty.value || ""),
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (itemCodeField.text.trim().length === 0) {
            root.validationMessage = "Item code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.validationMessage = "Item name is required."
            return
        }
        if (stockUomField.text.trim().length === 0) {
            root.validationMessage = "Stock UOM is required."
            return
        }
        if (String((root.itemStatusOptions[statusCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose an item status before saving."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromItem()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: Flickable {
        id: dialogFlickable

        contentWidth: width
        contentHeight: formLayout.implicitHeight
        clip: true

        ColumnLayout {
            id: formLayout

            width: dialogFlickable.width
            spacing: Theme.AppTheme.spacingMd

            Label {
                Layout.fillWidth: true
                text: root.modeTitle === "Create Item"
                    ? "Create a reusable inventory item with operational fields, replenishment settings, and supplier context."
                    : "Update item settings, preferred party, replenishment, and linked operational attributes."
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.bodySize
                wrapMode: Text.WordWrap
            }

            Label {
                Layout.fillWidth: true
                visible: root.validationMessage.length > 0
                text: root.validationMessage
                color: "#8B1E1E"
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                wrapMode: Text.WordWrap
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 680 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingSm

                Label { text: "Item code" }
                TextField { id: itemCodeField; Layout.fillWidth: true; placeholderText: "BRG-100" }

                Label { text: "Name" }
                TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Bearing 100" }

                Label { text: "Status" }
                ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.itemStatusOptions; textRole: "label" }

                Label { text: "Item type" }
                TextField { id: itemTypeField; Layout.fillWidth: true; placeholderText: "ROTATING" }

                Label { text: "Category" }
                ComboBox { id: categoryCombo; Layout.fillWidth: true; model: root.formCategoryOptions; textRole: "label" }

                Label { text: "Preferred party" }
                ComboBox { id: preferredPartyCombo; Layout.fillWidth: true; model: root.businessPartyOptions; textRole: "label" }

                Label { text: "Stock UOM" }
                TextField { id: stockUomField; Layout.fillWidth: true; placeholderText: "EA" }

                Label { text: "Order UOM" }
                TextField { id: orderUomField; Layout.fillWidth: true; placeholderText: "BOX" }

                Label { text: "Issue UOM" }
                TextField { id: issueUomField; Layout.fillWidth: true; placeholderText: "EA" }

                Label { text: "Order ratio" }
                TextField { id: orderRatioField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Issue ratio" }
                TextField { id: issueRatioField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Commodity code" }
                TextField { id: commodityCodeField; Layout.fillWidth: true; placeholderText: "MECH-SPARE" }

                Label { text: "Reorder policy" }
                TextField { id: reorderPolicyField; Layout.fillWidth: true; placeholderText: "MIN_MAX" }

                Label { text: "Min qty" }
                TextField { id: minQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Max qty" }
                TextField { id: maxQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Reorder point" }
                TextField { id: reorderPointField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Reorder qty" }
                TextField { id: reorderQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

                Label { text: "Lead time (days)" }
                TextField { id: leadTimeDaysField; Layout.fillWidth: true; placeholderText: "14"; inputMethodHints: Qt.ImhDigitsOnly }

                Label { text: "Shelf life (days)" }
                TextField { id: shelfLifeDaysField; Layout.fillWidth: true; placeholderText: "0"; inputMethodHints: Qt.ImhDigitsOnly }
            }

            CheckBox { id: stockedCheck; text: "Item is stocked" }
            CheckBox { id: purchaseAllowedCheck; text: "Item can be purchased" }
            CheckBox { id: lotTrackedCheck; text: "Lot tracking required" }
            CheckBox { id: serialTrackedCheck; text: "Serial tracking required" }

            Label {
                text: "Description"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: descriptionField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
                placeholderText: "Optional item description"
            }

            Label {
                text: "Notes"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
            }

            TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 88
                wrapMode: TextEdit.WordWrap
                placeholderText: "Planning or replenishment notes"
            }
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item {
            Layout.fillWidth: true
        }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Save"
            onClicked: root.submitDialog()
        }
    }
}
