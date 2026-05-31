import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Item"
    property var itemStatusOptions: []
    property var categoryOptions: []
    property var businessPartyOptions: []
    property var itemData: ({})
    readonly property var formCategoryOptions: categoryOptions.filter(function(option) {
        return String(option.value || "") !== "all"
    })

    signal submitted(var payload)

    width: 760
    title: root.modeTitle
    subtitle: root.modeTitle === "Create Item"
        ? "Create a reusable inventory item with operational fields, replenishment settings, and supplier context."
        : "Update item settings, preferred party, replenishment, and linked operational attributes."
    primaryText: root.modeTitle === "Create Item" ? "Create Item" : "Save Changes"
    primaryIcon: root.modeTitle === "Create Item" ? "add" : "save"
    onAccepted: root.submitDialog()
    onRejected: root.close()

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
        root.errorMessage = ""
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
            root.errorMessage = "Item code is required."
            return
        }
        if (nameField.text.trim().length === 0) {
            root.errorMessage = "Item name is required."
            return
        }
        if (stockUomField.text.trim().length === 0) {
            root.errorMessage = "Stock UOM is required."
            return
        }
        if (String((root.itemStatusOptions[statusCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose an item status before saving."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromItem()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 680 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Item code" }
        AppControls.TextField { id: itemCodeField; Layout.fillWidth: true; placeholderText: "BRG-100" }

        AppControls.Label { text: "Name" }
        AppControls.TextField { id: nameField; Layout.fillWidth: true; placeholderText: "Bearing 100" }

        AppControls.Label { text: "Status" }
        AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.itemStatusOptions; textRole: "label" }

        AppControls.Label { text: "Item type" }
        AppControls.TextField { id: itemTypeField; Layout.fillWidth: true; placeholderText: "ROTATING" }

        AppControls.Label { text: "Category" }
        AppControls.ComboBox { id: categoryCombo; Layout.fillWidth: true; model: root.formCategoryOptions; textRole: "label" }

        AppControls.Label { text: "Preferred party" }
        AppControls.ComboBox { id: preferredPartyCombo; Layout.fillWidth: true; model: root.businessPartyOptions; textRole: "label" }

        AppControls.Label { text: "Stock UOM" }
        AppControls.TextField { id: stockUomField; Layout.fillWidth: true; placeholderText: "EA" }

        AppControls.Label { text: "Order UOM" }
        AppControls.TextField { id: orderUomField; Layout.fillWidth: true; placeholderText: "BOX" }

        AppControls.Label { text: "Issue UOM" }
        AppControls.TextField { id: issueUomField; Layout.fillWidth: true; placeholderText: "EA" }

        AppControls.Label { text: "Order ratio" }
        AppControls.TextField { id: orderRatioField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Issue ratio" }
        AppControls.TextField { id: issueRatioField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Commodity code" }
        AppControls.TextField { id: commodityCodeField; Layout.fillWidth: true; placeholderText: "MECH-SPARE" }

        AppControls.Label { text: "Reorder policy" }
        AppControls.TextField { id: reorderPolicyField; Layout.fillWidth: true; placeholderText: "MIN_MAX" }

        AppControls.Label { text: "Min qty" }
        AppControls.TextField { id: minQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Max qty" }
        AppControls.TextField { id: maxQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Reorder point" }
        AppControls.TextField { id: reorderPointField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Reorder qty" }
        AppControls.TextField { id: reorderQtyField; Layout.fillWidth: true; placeholderText: "0.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Lead time (days)" }
        AppControls.TextField { id: leadTimeDaysField; Layout.fillWidth: true; placeholderText: "14"; inputMethodHints: Qt.ImhDigitsOnly }

        AppControls.Label { text: "Shelf life (days)" }
        AppControls.TextField { id: shelfLifeDaysField; Layout.fillWidth: true; placeholderText: "0"; inputMethodHints: Qt.ImhDigitsOnly }
    }

    AppControls.CheckBox { id: stockedCheck; text: "Item is stocked" }
    AppControls.CheckBox { id: purchaseAllowedCheck; text: "Item can be purchased" }
    AppControls.CheckBox { id: lotTrackedCheck; text: "Lot tracking required" }
    AppControls.CheckBox { id: serialTrackedCheck; text: "Serial tracking required" }

    AppControls.Label {
        text: "Description"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: descriptionField
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        wrapMode: TextEdit.WordWrap
        placeholderText: "Optional item description"
    }

    AppControls.Label {
        text: "Notes"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 88
        wrapMode: TextEdit.WordWrap
        placeholderText: "Planning or replenishment notes"
    }
}
