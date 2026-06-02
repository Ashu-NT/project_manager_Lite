import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root

    property string modeTitle: "Create Purchase Order"
    property var siteOptions: []
    property var supplierOptions: []
    property var requisitionOptions: []
    property var purchaseOrderData: ({})

    signal submitted(var payload)

    width: 760
    title: root.modeTitle
    subtitle: root.modeTitle === "Create Purchase Order"
        ? "Commit approved demand to a supplier with a clear site scope, expected delivery date, and shared source-requisition context."
        : "Update the purchase order scope, supplier details, and expected delivery before lines are committed."
    primaryText: root.modeTitle === "Create Purchase Order" ? "Create Order" : "Save Changes"
    primaryIcon: root.modeTitle === "Create Purchase Order" ? "add" : "save"
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

    function populateFromPurchaseOrder() {
        var state = root.purchaseOrderData && root.purchaseOrderData.state ? root.purchaseOrderData.state : (root.purchaseOrderData || {})
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        supplierCombo.currentIndex = root.indexForValue(root.supplierOptions, state.supplierPartyId || "")
        sourceRequisitionCombo.currentIndex = root.indexForValue(root.formRequisitionOptions, state.sourceRequisitionId || "")
        currencyCodeField.text = String(state.currencyCode || "")
        expectedDeliveryDateField.text = String(state.expectedDeliveryDateIso || "")
        supplierReferenceField.text = String(state.supplierReference || "")
        notesField.text = String(state.notes || "")
        root.errorMessage = ""
    }

    function buildPayload() {
        var selectedSite = root.siteOptions[siteCombo.currentIndex] || { "value": "" }
        var selectedSupplier = root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }
        var selectedRequisition = root.formRequisitionOptions[sourceRequisitionCombo.currentIndex] || { "value": "" }
        return {
            "siteId": String(selectedSite.value || ""),
            "supplierPartyId": String(selectedSupplier.value || ""),
            "sourceRequisitionId": String(selectedRequisition.value || ""),
            "currencyCode": currencyCodeField.text,
            "expectedDeliveryDate": expectedDeliveryDateField.text,
            "supplierReference": supplierReferenceField.text,
            "notes": notesField.text
        }
    }

    function submitDialog() {
        if (String((root.siteOptions[siteCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a site before saving the purchase order."
            return
        }
        if (String((root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.errorMessage = "Choose a supplier before saving the purchase order."
            return
        }
        root.errorMessage = ""
        root.submitted(root.buildPayload())
    }

    readonly property var formRequisitionOptions: [{ "value": "", "label": "None" }].concat(root.requisitionOptions || [])

    onOpened: root.populateFromPurchaseOrder()

    GridLayout {
        Layout.fillWidth: true
        columns: root.width > 640 ? 2 : 1
        columnSpacing: Theme.AppTheme.spacingMd
        rowSpacing: Theme.AppTheme.spacingSm

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Site"
            required: true
            AppControls.ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Supplier"
            required: true
            AppControls.ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Source requisition"
            AppControls.ComboBox { id: sourceRequisitionCombo; Layout.fillWidth: true; model: root.formRequisitionOptions; textRole: "label" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Currency"
            AppControls.TextField { id: currencyCodeField; Layout.fillWidth: true; placeholderText: "EUR" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Expected delivery (YYYY-MM-DD)"
            AppControls.DateField { id: expectedDeliveryDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: "Supplier reference"
            AppControls.TextField { id: supplierReferenceField; Layout.fillWidth: true; placeholderText: "Quote, reference, or contract number" }
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
            placeholderText: "Buying context, freight notes, or special handling instructions."
        }
    }
}
