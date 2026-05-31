import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var itemOptions: []
    property var supplierOptions: []
    property var requisitionData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    width: 720
    title: "Add Requisition Line"
    subtitle: "Add a line item to the requisition."
    errorMessage: root.validationMessage
    primaryText: "Add Line"
    primaryIcon: "add"
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

    function populateFromTarget() {
        itemCombo.currentIndex = 0
        supplierCombo.currentIndex = 0
        quantityField.text = ""
        estimatedCostField.text = ""
        descriptionField.text = ""
        neededByDateField.text = ""
        notesField.text = ""
        root.validationMessage = ""
    }

    function buildPayload() {
        var state = root.requisitionData && root.requisitionData.state ? root.requisitionData.state : (root.requisitionData || {})
        var selectedItem = root.itemOptions[itemCombo.currentIndex] || { "value": "" }
        var selectedSupplier = root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }
        return {
            "requisitionId": String(state.requisitionId || ""),
            "stockItemId": String(selectedItem.value || ""),
            "quantityRequested": quantityField.text,
            "estimatedUnitCost": estimatedCostField.text,
            "suggestedSupplierPartyId": String(selectedSupplier.value || ""),
            "description": descriptionField.text,
            "neededByDate": neededByDateField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.itemOptions[itemCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose an item before adding a requisition line."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.validationMessage = "Requested quantity must be greater than zero."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromTarget()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 620 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Item" }
        AppControls.ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }

        AppControls.Label { text: "Quantity" }
        AppControls.TextField { id: quantityField; objectName: "quantityField"; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Estimated unit cost" }
        AppControls.TextField { id: estimatedCostField; Layout.fillWidth: true; placeholderText: "0.0000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "Suggested supplier" }
        AppControls.ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }

        AppControls.Label { text: "Description" }
        AppControls.TextField { id: descriptionField; Layout.fillWidth: true; placeholderText: "Line scope or buying description" }

        AppControls.Label { text: "Needed by (YYYY-MM-DD)" }
        AppControls.DateField { id: neededByDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }
    }

    AppControls.Label {
        text: "Notes"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 100
        wrapMode: TextEdit.WordWrap
        placeholderText: "Line-specific buying notes or supplier context."
    }
}
