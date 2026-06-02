import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property var itemOptions: []
    property var storeroomOptions: []
    property var requisitionLineOptions: []
    property var purchaseOrderData: ({})

    signal submitted(var payload)

    width: 760
    title: "Add Purchase-Order Line"
    subtitle: "Add a purchase line to the order."
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
        storeroomCombo.currentIndex = 0
        sourceRequisitionLineCombo.currentIndex = 0
        quantityField.text = ""
        unitPriceField.text = ""
        expectedDeliveryDateField.text = ""
        descriptionField.text = ""
        notesField.text = ""
        root.errorMessage = ""
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
            root.errorMessage = "Choose an item before adding a purchase-order line."
            return
        }
        if (String((root.storeroomOptions[storeroomCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a destination storeroom before adding a purchase-order line."
            return
        }
        if (quantityField.text.trim().length === 0 || Number(quantityField.text) <= 0) {
            root.errorMessage = "Ordered quantity must be greater than zero."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    readonly property var formRequisitionLineOptions: [{ "value": "", "label": "None" }].concat(root.requisitionLineOptions || [])

    onOpened: root.populateFromTarget()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 640 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Item"
            required: true
            AppControls.ComboBox { id: itemCombo; Layout.fillWidth: true; model: root.itemOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Destination storeroom"
            required: true
            AppControls.ComboBox { id: storeroomCombo; Layout.fillWidth: true; model: root.storeroomOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Quantity"
            required: true
            AppControls.TextField { id: quantityField; Layout.fillWidth: true; placeholderText: "1.000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Unit price"
            AppControls.TextField { id: unitPriceField; Layout.fillWidth: true; placeholderText: "0.0000"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Source requisition line"
            AppControls.ComboBox { id: sourceRequisitionLineCombo; Layout.fillWidth: true; model: root.formRequisitionLineOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Expected delivery (YYYY-MM-DD)"
            AppControls.DateField { id: expectedDeliveryDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Description"
            AppControls.TextField { id: descriptionField; Layout.fillWidth: true; placeholderText: "Line description or supplier note" }
        }
    }

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Notes"
        AppControls.TextArea {
            id: notesField
            Layout.fillWidth: true
            Layout.preferredHeight: 100
            wrapMode: TextEdit.WordWrap
            placeholderText: "Receiving notes or line-level supplier remarks."
        }
    }
}
