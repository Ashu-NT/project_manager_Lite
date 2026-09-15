pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var reviewData: ({})
    property var actions: []
    property bool busy: false
    property string errorMessage: ""

    readonly property var _state: root.reviewData.state || ({})

    signal closeRequested()
    signal actionRequested(string actionId)

    AppWidgets.InspectorPanel {
        anchors.fill: parent
        title: root.reviewData.title || "Timesheet Period"
        statusLabel: root.reviewData.statusLabel || ""
        sections: root.reviewData.fields || []
        busy: root.busy
        showEditAction: false
        onCloseRequested: root.closeRequested()

        AppWidgets.InlineMessage {
            Layout.fillWidth: true
            visible: root.errorMessage.length > 0
            tone: "danger"
            message: root.errorMessage
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: String(root._state.submittedAt || "").length > 0
                || String(root._state.decidedAt || "").length > 0
            spacing: Theme.AppTheme.spacingXs

            AppControls.Label {
                Layout.fillWidth: true
                text: "Decision evidence"
                color: Theme.AppTheme.textMuted
                font.bold: true
            }
            AppControls.Label {
                Layout.fillWidth: true
                visible: String(root._state.submittedAt || "").length > 0
                text: "Submitted by " + String(root._state.submittedBy || "-")
                    + " at " + String(root._state.submittedAt || "-")
                color: Theme.AppTheme.textSecondary
                wrapMode: Text.WordWrap
            }
            AppControls.Label {
                Layout.fillWidth: true
                visible: String(root._state.decidedAt || "").length > 0
                text: "Latest decision by " + String(root._state.decidedBy || "-")
                    + " at " + String(root._state.decidedAt || "-")
                color: Theme.AppTheme.textSecondary
                wrapMode: Text.WordWrap
            }
            AppWidgets.InlineMessage {
                Layout.fillWidth: true
                visible: String(root._state.decisionNote || "").length > 0
                tone: "info"
                message: String(root._state.decisionNote || "")
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: root.actions.length > 0
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: root.actions

                delegate: AppControls.SecondaryButton {
                    required property var modelData
                    Layout.fillWidth: true
                    text: String(modelData.label || "")
                    iconName: String(modelData.icon || "")
                    danger: modelData.danger === true
                    enabled: !root.busy && modelData.enabled !== false
                    onClicked: root.actionRequested(String(modelData.id || ""))
                }
            }
        }
    }
}
