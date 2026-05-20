import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Dialog {
    id: root

    property string modeTitle: "Create Purchase Order"
    property var siteOptions: []
    property var supplierOptions: []
    property var requisitionOptions: []
    property var purchaseOrderData: ({})
    property string validationMessage: ""

    signal submitted(var payload)

    modal: true
    width: 760
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

    function populateFromPurchaseOrder() {
        var state = root.purchaseOrderData && root.purchaseOrderData.state ? root.purchaseOrderData.state : (root.purchaseOrderData || {})
        siteCombo.currentIndex = root.indexForValue(root.siteOptions, state.siteId || "")
        supplierCombo.currentIndex = root.indexForValue(root.supplierOptions, state.supplierPartyId || "")
        sourceRequisitionCombo.currentIndex = root.indexForValue(root.formRequisitionOptions, state.sourceRequisitionId || "")
        currencyCodeField.text = String(state.currencyCode || "")
        expectedDeliveryDateField.text = String(state.expectedDeliveryDateIso || "")
        supplierReferenceField.text = String(state.supplierReference || "")
        notesField.text = String(state.notes || "")
        root.validationMessage = ""
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
            root.validationMessage = "Choose a site before saving the purchase order."
            return
        }
        if (String((root.supplierOptions[supplierCombo.currentIndex] || { "value": "" }).value || "").length === 0) {
            root.validationMessage = "Choose a supplier before saving the purchase order."
            return
        }
        root.validationMessage = ""
        root.submitted(root.buildPayload())
    }

    readonly property var formRequisitionOptions: [{ "value": "", "label": "None" }].concat(root.requisitionOptions || [])

    onOpened: root.populateFromPurchaseOrder()

    background: Rectangle {
        radius: Theme.AppTheme.radiusLg
        color: Theme.AppTheme.surface
    }

    contentItem: ColumnLayout {
        spacing: Theme.AppTheme.spacingMd

        Label {
            Layout.fillWidth: true
            text: "Commit approved demand to a supplier with a clear site scope, expected delivery date, and shared source-requisition context."
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

            Label { text: "Site" }
            ComboBox { id: siteCombo; Layout.fillWidth: true; model: root.siteOptions; textRole: "label" }

            Label { text: "Supplier" }
            ComboBox { id: supplierCombo; Layout.fillWidth: true; model: root.supplierOptions; textRole: "label" }

            Label { text: "Source requisition" }
            ComboBox { id: sourceRequisitionCombo; Layout.fillWidth: true; model: root.formRequisitionOptions; textRole: "label" }

            Label { text: "Currency" }
            TextField { id: currencyCodeField; Layout.fillWidth: true; placeholderText: "EUR" }

            Label { text: "Expected delivery (YYYY-MM-DD)" }
            TextField { id: expectedDeliveryDateField; Layout.fillWidth: true; placeholderText: "2026-05-30" }

            Label { text: "Supplier reference" }
            TextField { id: supplierReferenceField; Layout.fillWidth: true; placeholderText: "Quote, reference, or contract number" }
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
            placeholderText: "Buying context, freight notes, or special handling instructions."
        }
    }

    footer: RowLayout {
        spacing: Theme.AppTheme.spacingSm

        Item { Layout.fillWidth: true }

        AppControls.SecondaryButton {
            objectName: "dialogCancelButton"
            text: "Cancel"
            iconName: "close"
            onClicked: root.close()
        }

        AppControls.PrimaryButton {
            objectName: "dialogSubmitButton"
            text: "Save"
            iconName: "save"
            onClicked: root.submitDialog()
        }
    }
}
