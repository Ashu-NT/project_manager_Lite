import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

AppWidgets.EntityDialog {
    id: root

    property string action: "submit"
    property var forecast: null
    property string projectLabel: ""
    signal decided(string action, string forecastId, int version, string requestId, string notes)

    readonly property var _state: root.forecast ? (root.forecast.state || {}) : ({})

    width: 520
    title: root.action === "submit" ? "Submit Forecast"
        : root.action === "request_approval" ? "Request Forecast Approval"
        : root.action === "approve" ? "Approve Forecast Request"
        : "Reject Forecast Request"
    subtitle: root.action === "submit"
        ? "Submission freezes this revision and its source evidence for review."
        : root.action === "request_approval"
            ? "Create a Platform Approval request. A different authorized principal must decide it."
            : "This decision is executed by the shared Platform Approval authority."
    primaryText: root.action === "request_approval" ? "Request Approval"
        : root.action.charAt(0).toUpperCase() + root.action.slice(1)
    primaryIcon: root.action === "reject" ? "reject" : "approve"

    function submitDialog() {
        if (root.action === "reject" && !notesField.text.trim()) {
            root.errorMessage = "A rejection reason is required."
            notesField.forceActiveFocus()
            return
        }
        root.errorMessage = ""
        root.decided(
            root.action,
            String(root.forecast ? root.forecast.id || "" : ""),
            Number(root._state.rowVersion || 0),
            String(root._state.approvalRequestId || ""),
            notesField.text.trim()
        )
    }

    onOpened: {
        notesField.text = ""
        root.errorMessage = ""
        notesField.forceActiveFocus()
    }
    onRejected: root.close()

    ColumnLayout {
        Layout.fillWidth: true
        spacing: Theme.AppTheme.spacingMd

        AppWidgets.SectionCard {
            Layout.fillWidth: true
            title: "Decision context"

            GridLayout {
                width: parent ? parent.width : 0
                columns: width >= 420 ? 2 : 1
                columnSpacing: Theme.AppTheme.spacingMd
                rowSpacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Project\n" + (root.projectLabel || "Selected project")
                    wrapMode: Text.WordWrap
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Forecast\n" + String(root.forecast ? root.forecast.title || "" : "")
                    wrapMode: Text.WordWrap
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: "State\n" + String(root.forecast ? root.forecast.statusLabel || "" : "")
                    wrapMode: Text.WordWrap
                }
                AppControls.Label {
                    Layout.fillWidth: true
                    text: "Basis\n" + String(root.forecast ? root.forecast.subtitle || "" : "")
                    wrapMode: Text.WordWrap
                }
            }
        }

        AppWidgets.FormField {
            Layout.fillWidth: true
            label: root.action === "reject" ? "Decision reason" : "Notes"
            required: root.action === "reject"
            AppControls.TextArea {
                id: notesField
                Layout.fillWidth: true
                Layout.preferredHeight: 96
                wrapMode: TextEdit.WordWrap
                placeholderText: root.action === "reject"
                    ? "Explain what must change before a new Forecast is generated."
                    : "Optional context for the audit trail"
            }
        }
    }
}
