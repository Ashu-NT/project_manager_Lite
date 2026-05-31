import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var statusOptions: []
    property var workRequestData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(string statusValue)

    title:       "Change Work Request Status"
    subtitle:    root.workRequestData && root.workRequestData.title
        ? "Update the triage lifecycle state for " + root.workRequestData.title + "."
        : "Update the lifecycle state for the selected work request."
    primaryText: "Update Status"
    primaryIcon: "approve"
    width: 420

    onOpened: {
        const state = root.workRequestData && root.workRequestData.state ? root.workRequestData.state : (root.workRequestData || {})
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "NEW")
    }
    onAccepted: {
        const option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "NEW" }
        root.submitted(String(option.value || "NEW"))
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

    AppControls.ComboBox {
        id: statusCombo
        objectName: "statusCombo"
        Layout.fillWidth: true
        model: root.workflowStatusOptions
        textRole: "label"
    }
}
