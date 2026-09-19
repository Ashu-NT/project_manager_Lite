pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingProfileDialog"
    property string projectId: ""
    property var profile: ({})
    signal submitted(var payload)
    title: "Create Billing Profile"
    subtitle: "PM commercial setup only. Accounting customer and receivables truth remain external."
    primaryText: "Create Billing Profile"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.projectId.length > 0

    function submitDialog() {
        if (!contractReference.text.trim() || !contractValue.text.trim()) {
            root.errorMessage = "Contract reference and value are required."
            contractReference.forceActiveFocus()
            return
        }
        root.submitted({
            "projectId": root.projectId,
            "contractReference": contractReference.text.trim(),
            "contractValue": contractValue.text.trim(),
            "customerPartyId": customerParty.text.trim(),
            "externalCustomerReference": externalReference.text.trim(),
            "purchaseOrderReference": purchaseOrder.text.trim(),
            "costPlusMarkupPercent": markup.text.trim() || "0",
            "paymentTermsDays": paymentTerms.text.trim() || "30",
            "retentionYears": retentionYears.text.trim() || "7"
        })
    }
    onOpened: contractReference.forceActiveFocus()

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Contract reference"
        required: true
        AppControls.TextField { id: contractReference; Layout.fillWidth: true; maximumLength: 160 }
    }
    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Contract value"
        required: true
        AppControls.TextField { id: contractValue; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly }
    }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Customer party reference"; AppControls.TextField { id: customerParty; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "External customer reference"; AppControls.TextField { id: externalReference; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Purchase order reference"; AppControls.TextField { id: purchaseOrder; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Cost-plus markup (%)"; AppControls.TextField { id: markup; Layout.fillWidth: true; text: "0"; inputMethodHints: Qt.ImhFormattedNumbersOnly } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Payment terms (days)"; AppControls.TextField { id: paymentTerms; Layout.fillWidth: true; text: "30"; inputMethodHints: Qt.ImhDigitsOnly } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Retention (years)"; AppControls.TextField { id: retentionYears; Layout.fillWidth: true; text: "7"; inputMethodHints: Qt.ImhDigitsOnly } }
}
