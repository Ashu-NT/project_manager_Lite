pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

AppWidgets.EntityDialog {
    id: root
    objectName: "billingScheduleLineDialog"
    property string projectId: ""
    property var workspaceController: null
    signal submitted(var payload)
    title: "Add Billing Schedule Line"
    subtitle: "PM Finance readiness only; it does not represent customer acceptance."
    primaryText: "Add Schedule Line"
    primaryIcon: "add"
    primaryEnabled: !root.busy && root.projectId.length > 0
    initialFocusTarget: nameField
    function submitDialog() {
        if (!root.primaryEnabled) return
        if (!nameField.text.trim() || !amountField.text.trim() || !dueDateField.text.trim()) {
            root.errorMessage = "Name, amount, and due date are required."
            const missing = !nameField.text.trim() ? nameField
                : !amountField.text.trim() ? amountField : dueDateField.focusTarget
            missing.forceActiveFocus()
            return
        }
        if (!dueDateField.selectedDate) {
            root.errorMessage = "Enter a valid due date."
            dueDateField.focusTarget.forceActiveFocus()
            return
        }
        root.submitted({ "projectId": root.projectId, "name": nameField.text.trim(), "amount": amountField.text.trim(), "dueDate": dueDateField.text.trim(), "taskId": taskSelector.selectedId, "acceptanceReference": acceptanceField.text.trim() })
    }
    onOpened: {
        root.errorMessage = ""
        nameField.text = ""
        amountField.text = ""
        dueDateField.text = ""
        acceptanceField.text = ""
        taskSelector.selectedId = ""
        taskSelector.selectedLabel = ""
    }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Schedule line name"; required: true; AppControls.TextField { id: nameField; Layout.fillWidth: true } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Amount"; required: true; AppControls.TextField { id: amountField; Layout.fillWidth: true; inputMethodHints: Qt.ImhFormattedNumbersOnly } }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Due date"; required: true; AppControls.DateField { id: dueDateField; Layout.fillWidth: true; popupBoundaryItem: root.contentItem; placeholderText: "YYYY-MM-DD" } }
    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Task (optional)"
        AppControls.SearchablePagedSelector {
            id: taskSelector
            Layout.fillWidth: true
            contextKey: root.projectId
            allowEmpty: true
            emptyLabel: "Not linked to a task"
            searchPlaceholder: "Search task name, code, or WBS..."
            onLookupRequested: function(query, page, pageSize, generation, lookupContext) {
                const result = root.workspaceController
                    ? root.workspaceController.searchBudgetTasks(root.projectId, query, page, pageSize)
                    : ({ "ok": false, "message": "Finance controller is unavailable." })
                taskSelector.acceptResult(result, generation, lookupContext)
            }
        }
    }
    AppWidgets.FormField { Layout.fillWidth: true; label: "Acceptance reference (optional)"; AppControls.TextField { id: acceptanceField; Layout.fillWidth: true } }
}
