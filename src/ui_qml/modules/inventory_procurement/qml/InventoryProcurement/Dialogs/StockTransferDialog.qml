import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var transferData: ({})

    signal submitted(var payload)

    width: 720
    title: "Transfer Stock"
    subtitle: "Transfer stock between storeroom locations."
    primaryText: "Transfer Stock"
    primaryIcon: "approve"
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

    function populateFromTransfer() {
        var state = root.transferData && root.transferData.state ? root.transferData.state : (root.transferData || {})
        itemCombo.currentIndex = root.indexForValue(root.itemOptions, state.stockItemId || "")
        sourceStoreroomCombo.currentIndex = root.indexForValue(root.storeroomOptions, state.storeroomId || "")
        destinationStoreroomCombo.currentIndex = root.indexForValue(root.storeroomOptions, "")
        quantityField.text = ""
        uomField.text = String(state.uom || "")
        notesField.text = ""
        root.errorMessage = ""
    }

    function buildPayload() {
        var selectedItem = root.itemOptions[itemCombo.currentIndex] || { "value": "" }
        var selectedSource = root.storeroomOptions[sourceStoreroomCombo.currentIndex] || { "value": "" }
        var selectedDestination = root.storeroomOptions[destinationStoreroomCombo.currentIndex] || { "value": "" }
        return {
            "stockItemId": String(selectedItem.value || ""),
            "sourceStoreroomId": String(selectedSource.value || ""),
            "destinationStoreroomId": String(selectedDestination.value || ""),
            "quantity": quantityField.text,
            "uom": uomField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.itemOptions[itemCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose an item before saving."
            return
        }
        if (String((root.storeroomOptions[sourceStoreroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a source storeroom before saving."
            return
        }
        if (String((root.storeroomOptions[destinationStoreroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a destination storeroom before saving."
            return
        }
        if (String((root.storeroomOptions[sourceStoreroomCombo.currentIndex] || { "value": "" }).value || "")
            === String((root.storeroomOptions[destinationStoreroomCombo.currentIndex] || { "value": "" }).value || "")) {
            root.errorMessage = "Source and destination storerooms must be different."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.errorMessage = "Quantity must be greater than zero."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromTransfer()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 620 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Item" }
        AppControls.ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }

        AppControls.Label { text: "Source storeroom" }
        AppControls.ComboBox { id: sourceStoreroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

        AppControls.Label { text: "Destination storeroom" }
        AppControls.ComboBox { id: destinationStoreroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

        AppControls.Label { text: "Quantity" }
        AppControls.TextField { id: quantityField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "UOM" }
        AppControls.TextField { id: uomField; Layout.fillWidth: true; placeholderText: "EA" }
    }

    AppControls.Label {
        text: "Notes"
        color: Theme.AppTheme.textPrimary
        font.family: Theme.AppTheme.fontFamily
    }

    AppControls.TextArea {
        id: notesField
        Layout.fillWidth: true
        Layout.preferredHeight: 96
        wrapMode: TextEdit.WordWrap
        placeholderText: "Optional transfer notes"
    }
}
