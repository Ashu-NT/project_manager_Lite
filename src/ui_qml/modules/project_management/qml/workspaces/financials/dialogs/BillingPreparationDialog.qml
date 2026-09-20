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
    property string correctionOfPreparationId: ""
    signal submitted(var payload)
    title: root.correctionOfPreparationId.length > 0 ? "Create Billing Correction" : "Create Billing Preparation"
    subtitle: "Creates a PM commercial handoff package. It does not create an invoice or receivable."
    primaryText: "Create Preparation"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.projectId.length > 0 && root.commandId.length > 0
    initialFocusTarget: numberField
    function submitDialog() {
        if (!root.primaryEnabled) return
        if (!numberField.text.trim() || !periodStartField.text.trim() || !periodEndField.text.trim()) {
            root.errorMessage = "Preparation number, period start, and period end are required."
            const missing = !numberField.text.trim() ? numberField
                : !periodStartField.text.trim() ? periodStartField.focusTarget : periodEndField.focusTarget
            missing.forceActiveFocus()
            return
        }
        if (!periodStartField.selectedDate || !periodEndField.selectedDate
                || periodStartField.text > periodEndField.text) {
            root.errorMessage = "Enter valid period dates with the end on or after the start."
            const invalid = !periodStartField.selectedDate ? periodStartField : periodEndField
            invalid.focusTarget.forceActiveFocus()
            return
        }
        root.submitted({ "projectId": root.projectId, "preparationNumber": numberField.text.trim(), "periodStart": periodStartField.text.trim(), "periodEnd": periodEndField.text.trim(), "idempotencyKey": root.commandId, "correctionOfPreparationId": root.correctionOfPreparationId })
    }
    onOpened: {
        root.errorMessage = ""
        numberField.text = ""
        periodStartField.text = ""
        periodEndField.text = ""
    }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Preparation number"; required: true; AppControls.TextField { id: numberField; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Period start"; required: true; AppControls.DateField { id: periodStartField; Layout.fillWidth: true; popupBoundaryItem: root.contentItem; placeholderText: "YYYY-MM-DD" } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Period end"; required: true; AppControls.DateField { id: periodEndField; Layout.fillWidth: true; popupBoundaryItem: root.contentItem; placeholderText: "YYYY-MM-DD" } }
}
