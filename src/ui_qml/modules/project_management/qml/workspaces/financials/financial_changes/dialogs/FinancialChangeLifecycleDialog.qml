import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string action: "submit"
    property var change: null
    property var impact: null
    signal decided(string action, var payload)

    readonly property var _changeState: root.change ? (root.change.state || {}) : ({})
    readonly property var _impactState: root.impact ? (root.impact.state || {}) : ({})
    readonly property bool _rejecting: root.action === "reject"

    width: 520
    title: root.action === "submit" ? "Submit Change Request"
        : root.action === "approve" ? "Approve & Apply Change"
        : root.action === "reject" ? "Reject Change Request"
        : "Remove Change Impact"
    subtitle: root.action === "approve"
        ? "Approval atomically creates authoritative successors and applies Schedule effects."
        : root.action === "submit"
            ? "Submission freezes the request and sends it to Platform Approval."
            : "This governed action is recorded in the enterprise audit trail."
    primaryText: root.action === "approve" ? "Approve & Apply"
        : root.action === "remove_impact" ? "Remove Impact"
        : root.action.charAt(0).toUpperCase() + root.action.slice(1)
    primaryIcon: root.action === "reject" || root.action === "remove_impact"
        ? "delete" : "approve"

    function submitDialog() {
        if (root._rejecting && !notesField.text.trim()) {
            root.errorMessage = "A rejection reason is required."
            notesField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.decided(root.action, {
            "changeId": String(root.change ? root.change.id || "" : ""),
            "rowVersion": Number(root._changeState.version || 0),
            "changeVersion": Number(root._changeState.version || 0),
            "approvalRequestId": String(root._changeState.approvalRequestId || ""),
            "impactId": String(root.impact ? root.impact.id || "" : ""),
            "impactVersion": Number(root._impactState.version || 0),
            "notes": notesField.text.trim()
        })
    }

    onOpened: {
        notesField.text = ""
        root.errorMessage = ""
        if (root._rejecting) notesField.forceActiveFocus()
    }
    onRejected: root.close()

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppControls.Label {
            Layout.fillWidth: true
            text: String(root.change ? root.change.title || "Selected Change Request" : "")
            font.bold: true
            wrapMode: Text.WordWrap
        }
        AppWidgets.FormField {
            Layout.fillWidth: true
            visible: root.action === "approve" || root.action === "reject"
            label: root._rejecting ? "Decision reason" : "Decision note"
            required: root._rejecting
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 90
                wrapMode: TextEdit.WordWrap
            }
        }
    }
}
