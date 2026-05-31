import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Post Movement"
    property string submitLabel: "Post"
    property bool showDirection: false
    property bool showReferenceFields: true
    property bool showReleaseReservedField: false
    property var itemOptions: []
    property var storeroomOptions: []
    property var movementData: ({})
    property string defaultReferenceType: ""
    property string defaultDirection: "INCREASE"

    signal submitted(var payload)

    width: 720
    title: root.modeTitle
    subtitle: root.showDirection
        ? "Post a stock adjustment against an item and storeroom location."
        : root.defaultDirection === "DECREASE"
            ? "Post a stock decrease against an item and storeroom location."
            : "Post a stock increase against an item and storeroom location."
    primaryText: "Post Movement"
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

    function populateFromMovement() {
        var state = root.movementData && root.movementData.state ? root.movementData.state : (root.movementData || {})
        itemCombo.currentIndex = root.indexForValue(root.itemOptions, state.stockItemId || "")
        storeroomCombo.currentIndex = root.indexForValue(root.storeroomOptions, state.storeroomId || "")
        quantityField.text = ""
        uomField.text = String(state.uom || "")
        unitCostField.text = String(state.averageCost || "")
        directionCombo.currentIndex = String(state.direction || root.defaultDirection) === "DECREASE" ? 1 : 0
        releaseReservedField.text = String(state.releaseReservedQty || "0")
        referenceTypeField.text = String(state.referenceType || root.defaultReferenceType || "")
        referenceIdField.text = String(state.referenceId || "")
        notesField.text = String(state.notes || "")
        root.errorMessage = ""
    }

    function buildPayload() {
        var selectedItem = root.itemOptions[itemCombo.currentIndex] || { "value": "" }
        var selectedStoreroom = root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }
        var directionValue = directionCombo.currentIndex === 1 ? "DECREASE" : "INCREASE"
        return {
            "stockItemId": String(selectedItem.value || ""),
            "storeroomId": String(selectedStoreroom.value || ""),
            "quantity": quantityField.text,
            "uom": uomField.text,
            "unitCost": unitCostField.text,
            "direction": directionValue,
            "releaseReservedQty": releaseReservedField.text,
            "referenceType": referenceTypeField.text,
            "referenceId": referenceIdField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.itemOptions[itemCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose an item before saving."
            return
        }
        if (String((root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a storeroom before saving."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.errorMessage = "Quantity must be greater than zero."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    onOpened: root.populateFromMovement()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 620 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppControls.Label { text: "Item" }
        AppControls.ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }

        AppControls.Label { text: "Storeroom" }
        AppControls.ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }

        AppControls.Label { text: "Quantity" }
        AppControls.TextField { id: quantityField; objectName: "quantityField"; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label { text: "UOM" }
        AppControls.TextField { id: uomField; Layout.fillWidth: true; placeholderText: "EA" }

        AppControls.Label {
            visible: root.showDirection
            text: "Direction"
        }
        AppControls.ComboBox {
            id: directionCombo
            visible: root.showDirection
            Layout.fillWidth: true
            model: [
                { "value": "INCREASE", "label": "Increase" },
                { "value": "DECREASE", "label": "Decrease" }
            ]
            textRole: "label"
        }

        AppControls.Label { text: "Unit cost" }
        AppControls.TextField { id: unitCostField; Layout.fillWidth: true; placeholderText: "0.00"; inputMethodHints: Qt.ImhFormattedNumbersOnly }

        AppControls.Label {
            visible: root.showReleaseReservedField
            text: "Release reserved qty"
        }
        AppControls.TextField {
            id: releaseReservedField
            visible: root.showReleaseReservedField
            Layout.fillWidth: true
            placeholderText: "0"
            inputMethodHints: Qt.ImhFormattedNumbersOnly
        }

        AppControls.Label {
            visible: root.showReferenceFields
            text: "Reference type"
        }
        AppControls.TextField {
            id: referenceTypeField
            visible: root.showReferenceFields
            Layout.fillWidth: true
            placeholderText: "issue"
        }

        AppControls.Label {
            visible: root.showReferenceFields
            text: "Reference id"
        }
        AppControls.TextField {
            id: referenceIdField
            visible: root.showReferenceFields
            Layout.fillWidth: true
            placeholderText: "WO-100"
        }
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
        placeholderText: "Optional notes"
    }
}
