import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var statusOptions: []
    property var taskData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(var payload)

    title:       "Update Progress"
    subtitle:    root.taskData && root.taskData.title
        ? "Update progress, actual dates, and execution status for " + root.taskData.title + "."
        : "Update progress, actual dates, and execution status for the selected task."
    primaryText: "Update Progress"
    primaryIcon: "approve"
    width: 460

    onOpened:   root.populateFromTask()
    onAccepted: {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        var option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "TODO" }
        root.submitted({
            "taskId": String(state.taskId || ""),
            "expectedVersion": state.version,
            "percentComplete": percentField.text,
            "actualStart": actualStartField.text,
            "actualEnd": actualEndField.text,
            "status": String(option.value || "TODO")
        })
    }
    onRejected: root.close()

    function statusIndexForValue(statusValue) {
        for (let index = 0; index < root.workflowStatusOptions.length; index += 1) {
            if (String(root.workflowStatusOptions[index].value || "") === String(statusValue || "")) {
                return index
            }
        }
        return 0
    }

    function populateFromTask() {
        var state = root.taskData && root.taskData.state ? root.taskData.state : (root.taskData || {})
        percentField.text = String(state.percentComplete || "")
        actualStartField.text = String(state.actualStart || "")
        actualEndField.text = String(state.actualEnd || "")
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "TODO")
    }

    // ── Form content ──────────────────────────────────────────────────────────

    AppControls.Label { text: "Progress (%)"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
    AppControls.TextField { id: percentField; Layout.fillWidth: true; placeholderText: "0-100" }

    AppControls.Label { text: "Status"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
    AppControls.ComboBox { id: statusCombo; Layout.fillWidth: true; model: root.workflowStatusOptions; textRole: "label" }

    AppControls.Label { text: "Actual start"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
    AppControls.DateField { id: actualStartField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }

    AppControls.Label { text: "Actual end"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
    AppControls.DateField { id: actualEndField; Layout.fillWidth: true; placeholderText: "YYYY-MM-DD" }
}
