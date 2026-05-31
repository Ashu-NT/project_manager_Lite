import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property var assignmentData: ({})

    signal submitted(var payload)

    title:       "Update Assignment Effort"
    subtitle:    root.assignmentData && root.assignmentData.title
        ? "Set aggregate effort for " + root.assignmentData.title + "."
        : "Set aggregate effort for the selected assignment."
    primaryText: "Save Hours"
    primaryIcon: "save"
    width: 460

    onOpened: {
        const state = root.assignmentState()
        hoursField.text = String(state.hoursLogged || "")
    }
    onAccepted: root.submitted({
        "assignmentId": String(root.assignmentState().assignmentId || ""),
        "hoursLogged": hoursField.text
    })
    onRejected: root.close()

    function assignmentState() {
        return root.assignmentData && root.assignmentData.state
            ? root.assignmentData.state
            : (root.assignmentData || {})
    }

    // ── Form content ──────────────────────────────────────────────────────────

    AppControls.Label { text: "Hours logged"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily }
    AppControls.TextField { id: hoursField; Layout.fillWidth: true; placeholderText: "0.00" }
}
