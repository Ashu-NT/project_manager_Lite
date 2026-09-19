pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingPreparationDialog"
    property string projectId: ""
    property string commandId: ""
    signal submitted(var payload)
    title: "Create Billing Preparation"
    subtitle: "Creates a PM commercial handoff package. It does not create an invoice or receivable."
    primaryText: "Create Preparation"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.projectId.length > 0 && root.commandId.length > 0
    function submitDialog() {
        if (!numberField.text.trim() || !periodStartField.text.trim() || !periodEndField.text.trim()) {
            root.errorMessage = "Preparation number, period start, and period end are required."
            numberField.forceActiveFocus()
            return
        }
        root.submitted({ "projectId": root.projectId, "preparationNumber": numberField.text.trim(), "periodStart": periodStartField.text.trim(), "periodEnd": periodEndField.text.trim(), "idempotencyKey": root.commandId })
    }
    onOpened: numberField.forceActiveFocus()
    AppWidgets.FormField { Layout.fillWidth: true; label: "Preparation number"; required: true; AppControls.TextField { id: numberField; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Period start"; required: true; AppControls.TextField { id: periodStartField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Period end"; required: true; AppControls.TextField { id: periodEndField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" } }
}
