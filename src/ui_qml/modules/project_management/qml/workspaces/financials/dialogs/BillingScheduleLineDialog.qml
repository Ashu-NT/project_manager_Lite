pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingScheduleLineDialog"
    property string projectId: ""
    signal submitted(var payload)
    title: "Add Billing Schedule Line"
    subtitle: "PM Finance readiness only; it does not represent customer acceptance."
    primaryText: "Add Schedule Line"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.projectId.length > 0
    function submitDialog() {
        if (!nameField.text.trim() || !amountField.text.trim() || !dueDateField.text.trim()) {
            root.errorMessage = "Name, amount, and due date are required."
            nameField.forceActiveFocus()
            return
        }
        root.submitted({ "projectId": root.projectId, "name": nameField.text.trim(), "amount": amountField.text.trim(), "dueDate": dueDateField.text.trim(), "taskId": taskIdField.text.trim(), "acceptanceReference": acceptanceField.text.trim() })
    }
    onOpened: nameField.forceActiveFocus()
    AppWidgets.FormField { Layout.fillWidth: true; label: "Schedule line name"; required: true; AppControls.TextField { id: nameField; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Amount"; required: true; AppControls.TextField { id: amountField; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Due date"; required: true; AppControls.TextField { id: dueDateField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Task ID (optional)"; AppControls.TextField { id: taskIdField; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Acceptance reference (optional)"; AppControls.TextField { id: acceptanceField; Layout.fillWidth: true } }
}
