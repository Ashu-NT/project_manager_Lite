import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var assignmentData: ({})

    signal submitted(var payload)

    title:       "Edit Planned Work"
    subtitle:    root.assignmentData && root.assignmentData.title
        ? "Set the planned work allocated to " + root.assignmentData.title + " for this task."
        : "Set the planned work allocated to the selected assignment for this task."
    primaryText: "Save Planned Work"
    primaryIcon: "save"
    width: 460

    onOpened: {
        const state = root.assignmentState()
        plannedHoursField.text = String(state.plannedHours || "0")
        root.errorMessage = ""
    }
    onAccepted: root.submitDialog()
    onRejected: root.close()

    function assignmentState() {
        return root.assignmentData && root.assignmentData.state
            ? root.assignmentData.state
            : (root.assignmentData || {})
    }

    function submitDialog() {
        if (plannedHoursField.text.trim().length === 0) {
            root.errorMessage = "Planned work is required."
            return
        }
        root.errorMessage = ""
        const state = root.assignmentState()
        root.submitted({
            "assignmentId": String(state.assignmentId || ""),
            "plannedHours": plannedHoursField.text,
            "version": state.version !== undefined ? String(state.version) : "",
            "projectResourceVersion": state.projectResourceVersion !== undefined
                ? String(state.projectResourceVersion)
                : ""
        })
    }

    // ── Form content ──────────────────────────────────────────────────────────

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "Planned work (h)"
        required: true
        AppControls.TextField { id: plannedHoursField; Layout.fillWidth: true; placeholderText: "0.00" }
    }
}
