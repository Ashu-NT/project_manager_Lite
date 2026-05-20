import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var transferData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 720
    title: "Transfer Stock"
    closePolicy: Popup.CloseOnEscape

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
        root.validationMessage = ""
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
            root.validationMessage = "Choose an item before saving."
            return
        }
        if (String((root.storeroomOptions[sourceStoreroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a source storeroom before saving."
            return
        }
        if (String((root.storeroomOptions[destinationStoreroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a destination storeroom before saving."
            return
        }
        if (String((root.storeroomOptions[sourceStoreroomCombo.currentIndex] || { "value": "" }).value || "")
            === String((root.storeroomOptions[destinationStoreroomCombo.currentIndex] || { "value": "" }).value || "")) {
            root.validationMessage = "Source and destination storerooms must be different."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.validationMessage = "Quantity must be greater than zero."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromTransfer()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

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
            columns: root.width > 620 ? 2 : 1
            columnSpacing: Theme.AppTheme.spacingMd
            rowSpacing: Theme.AppTheme.spacingSm

            Label { text: "Item" }
            ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }

            Label { text: "Source storeroom" }
            ComboBox { id: sourceStoreroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

            Label { text: "Destination storeroom" }
            ComboBox { id: destinationStoreroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

            Label { text: "Quantity" }
            TextField { id: quantityField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

            Label { text: "UOM" }
            TextField { id: uomField; Layout.fillWidth: true; placeholderText: "EA" }
        }

        Label {
            text: "Notes"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
        }

        TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 96
            wrapMode: TextEdit.WordWrap
            placeholderText: "Optional transfer notes"
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
            text: "Post Transfer"
            onClicked: root.submitDialog()
        }
    }
}
