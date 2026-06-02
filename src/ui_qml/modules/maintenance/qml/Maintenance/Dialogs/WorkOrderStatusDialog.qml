import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var statusOptions: []
    property var workOrderData: ({})
    readonly property var workflowStatusOptions: (root.statusOptions || []).filter(function(option) {
        return String(option.value || "").toLowerCase() !== "all"
    })

    signal submitted(string statusValue)

    title:       "Change Work Order Status"
    subtitle:    root.workOrderData && root.workOrderData.title
        ? "Update the execution lifecycle state for " + root.workOrderData.title + "."
        : "Update the lifecycle state for the selected work order."
    primaryText: "Update Status"
    primaryIcon: "approve"
    width: 420

    onOpened: {
        const state = root.workOrderData && root.workOrderData.state ? root.workOrderData.state : (root.workOrderData || {})
        statusCombo.currentIndex = root.statusIndexForValue(state.status || "DRAFT")
    }
    onAccepted: {
        const option = root.workflowStatusOptions[statusCombo.currentIndex] || { "value": "DRAFT" }
        root.submitted(String(option.value || "DRAFT"))
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
            objectName: "statusCombo"
            Layout.fillWidth: true
            model: root.workflowStatusOptions
            textRole: "label"
        }
    }
}
