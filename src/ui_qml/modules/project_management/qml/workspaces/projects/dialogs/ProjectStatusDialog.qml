import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var statusOptions: []
    property var projectData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(string statusValue)

    title:       "Change Project Status"
    subtitle:    root.projectData && root.projectData.title
        ? "Update the lifecycle state for " + root.projectData.title + "."
        : "Update the lifecycle state for the selected project."
    primaryText: "Update Status"
    primaryIcon: "approve"
    width: 420

    onOpened: {
        var state = root.projectData && root.projectData.state ? root.projectData.state : (root.projectData || {})
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "PLANNED")
    }
    onAccepted: {
        var option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "PLANNED" }
        root.submitted(String(option.value || "PLANNED"))
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

    // ── Form content ──────────────────────────────────────────────────────────

    AppWidgets.FormField {
        Layout.fillWidth: true
        label: "New Status"

        AppControls.ComboBox {
            id: statusCombo
            Layout.fillWidth: true
            model: root.workflowStatusOptions
            textRole: "label"
        }
    }
}
