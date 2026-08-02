import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string mode: "accept"
    property var assignmentData: ({})

    signal submitted(var payload)

    width: 560
    title: root.mode === "decline" ? "Decline Assignment" : "Accept Assignment"
    subtitle: {
        const resourceName = String(root.assignmentData.title || "this assignment")
        return root.mode === "decline"
            ? "Decline " + resourceName + " and provide planning context for the project team."
            : "Confirm that you accept " + resourceName + " and its current allocation."
    }
    infoMessage: root.mode === "decline"
        ? "The project team will retain the reason in assignment activity history."
        : "Acceptance confirms the assignment handoff. A manager must reassign it before another response can be made."
    primaryText: "Accept Assignment"
    primaryIcon: "approve"
    showPrimary: root.mode === "accept"
    destructiveText: "Decline Assignment"
    destructiveIcon: "close"
    showDestructive: root.mode === "decline"
    destructiveEnabled: String(reasonArea.text || "").trim().length > 0
    closePolicy: Popup.CloseOnEscape

    function selectedState() {
        return root.assignmentData && root.assignmentData.state
            ? root.assignmentData.state
            : (root.assignmentData || {})
    }

    function submitDialog() {
        const state = root.selectedState()
        const assignmentId = String(state.assignmentId || root.assignmentData.id || "")
        const reason = String(reasonArea.text || "").trim()
        if (!assignmentId) {
            root.errorMessage = "Select an assignment before responding."
            return
        }
        if (root.mode === "decline" && !reason) {
            root.errorMessage = "Provide a reason for declining this assignment."
            return
        }
        root.errorMessage = ""
        root.submitted({
            "assignmentId": assignmentId,
            "reason": reason
        })
    }

    onOpened: {
        reasonArea.text = ""
        root.errorMessage = ""
    }
    onAccepted: root.submitDialog()
    onDestructiveRequested: root.submitDialog()
    onRejected: root.close()

    AppWidgets.FormField {
        Layout.fillWidth: true
        visible: root.mode === "decline"
        label: "Decline reason"
        required: true

        AppControls.TextArea {
            id: reasonArea
            Layout.fillWidth: true
            Layout.preferredHeight: 120
            placeholderText: "Explain the capacity, timing, or scope conflict."
            wrapMode: TextEdit.WordWrap
        }
    }

    AppControls.Label {
        Layout.fillWidth: true
        visible: root.mode === "accept"
        text: {
            const state = root.selectedState()
            const allocation = String(state.allocationPercent || "0")
            return "Current allocation: " + allocation + "%"
        }
        color: Theme.AppTheme.textSecondary
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.bodySize
        wrapMode: Text.WordWrap
    }
}
