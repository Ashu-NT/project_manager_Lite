import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var requisitionLineOptions: []
    property var purchaseOrderData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 760
    title: "Add Purchase-Order Line"
    closePolicy: Popup.CloseOnEscape

    function indexForValue(options, targetValue) {
        for (var index = 0; index < options.length; index += 1) {
            if (String(options[index].value || "") === String(targetValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromTarget() {
        itemCombo.currentIndex = 0
        storeroomCombo.currentIndex = 0
        sourceRequisitionLineCombo.currentIndex = 0
        quantityField.text = ""
        unitPriceField.text = ""
        expectedDeliveryDateField.text = ""
        descriptionField.text = ""
        notesField.text = ""
        root.validationMessage = ""
    }

    function buildPayload() {
        var state = root.purchaseOrderData && root.purchaseOrderData.state ? root.purchaseOrderData.state : (root.purchaseOrderData || {})
        var selectedItem = root.itemOptions[itemCombo.currentIndex] || { "value": "" }
        var selectedStoreroom = root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }
        var selectedSourceLine = root.formRequisitionLineOptions[sourceRequisitionLineCombo.currentIndex] || { "value": "" }
        return {
            "purchaseOrderId": String(state.purchaseOrderId || ""),
            "stockItemId": String(selectedItem.value || ""),
            "destinationStoreroomId": String(selectedStoreroom.value || ""),
            "quantityOrdered": quantityField.text,
            "unitPrice": unitPriceField.text,
            "sourceRequisitionLineId": String(selectedSourceLine.value || ""),
            "expectedDeliveryDate": expectedDeliveryDateField.text,
            "description": descriptionField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.itemOptions[itemCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose an item before adding a purchase-order line."
            return
        }
        if (String((root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a destination storeroom before adding a purchase-order line."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.validationMessage = "Ordered quantity must be greater than zero."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    readonly property var formRequisitionLineOptions: [{ "value": "", "label": "None" }].concat(root.requisitionLineOptions || [])

    onOpened: root.populateFromTarget()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
        border.color: Theme.AppTheme.border
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Create a supplier commitment line with the final receiving destination and, when useful, the originating requisition line."
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
            columns: root.width > 640 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Item" }
            ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }

            Label { text: "Destination storeroom" }
            ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

            Label { text: "Quantity" }
            TextField { id: quantityField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

            Label { text: "Unit price" }
            TextField { id: unitPriceField; Layout.fillWidth: true; placeholderText: "0.0000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

            Label { text: "Source requisition line" }
            ComboBox { id: sourceRequisitionLineCombo; Layout.fillWidth: true; model: root.formRequisitionLineOptions; textRole: "label" }

            Label { text: "Expected delivery (YYYY-MM-DD)" }
            TextField { id: expectedDeliveryDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }

            Label { text: "Description" }
            TextField { id: descriptionField; Layout.fillWidth: true; placeholderText: "Line description or supplier note" }
        }

        Label {
            text: "Notes"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            wrapMode: TextEdit.WordWrap
            placeholderText: "Receiving notes or line-level supplier remarks."
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        Button {
            text: "Cancel"
            onClicked: root.close()
        }

        Button {
            text: "Add Line"
            onClicked: root.submitDialog()
        }
    }
}
