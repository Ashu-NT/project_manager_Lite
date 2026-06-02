pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
            color: Theme.AppTheme.surfaceRaised
            z: 1
            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: 1; color: Theme.AppTheme.divider
            }
            AppControls.Label {
                anchors.left: parent.left
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.verticalCenter: parent.verticalCenter
                text: "Security"
                color: Theme.AppTheme.textPrimary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                font.bold: true
            }
        }

        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: _securityContent.implicitHeight + Theme.AppTheme.marginLg * 2
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            ColumnLayout {
                id: _securityContent
                anchors {
                    top: parent.top; left: parent.left; right: parent.right
                    topMargin: Theme.AppTheme.marginLg; leftMargin: Theme.AppTheme.marginLg; rightMargin: Theme.AppTheme.marginLg
                }
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: [
                        { title: "Password Policy", rows: [
                            { label: "Minimum length",          value: "12 characters" },
                            { label: "Complexity required",     value: "Yes (upper, lower, digit, symbol)" },
                            { label: "Password expiry",         value: "90 days" },
                            { label: "Reuse restriction",       value: "Last 5 passwords" }
                        ]},
                        { title: "Session Policy", rows: [
                            { label: "Session timeout",         value: "30 minutes idle" },
                            { label: "Concurrent sessions",     value: "1 per user" },
                            { label: "Remember device",         value: "Disabled" },
                            { label: "Token lifetime",          value: "8 hours" }
                        ]},
                        { title: "RBAC Defaults", rows: [
                            { label: "Default role",            value: "Viewer" },
                            { label: "Self-service access",     value: "Disabled" },
                            { label: "Cross-org visibility",    value: "Restricted" },
                            { label: "Audit on role change",    value: "Enabled" }
                        ]},
                        { title: "Approval Thresholds", rows: [
                            { label: "Auto-approve below",      value: "Not configured" },
                            { label: "Escalate after",          value: "48 hours" },
                            { label: "Required approvers",      value: "1 (any admin)" },
                            { label: "Notify on rejection",     value: "Enabled" }
                        ]}
                    ]

                    delegate: Rectangle {
                        id: _secCard
                        required property var modelData
                        Layout.fillWidth: true
                        implicitHeight: _secCardLayout.implicitHeight + Theme.AppTheme.marginMd * 2
                        color: Theme.AppTheme.surface
                        radius: Theme.AppTheme.radiusMd
                        border.color: Theme.AppTheme.divider
                        border.width: 1

                        ColumnLayout {
                            id: _secCardLayout
                            anchors { fill: parent; margins: Theme.AppTheme.marginMd }
                            spacing: Theme.AppTheme.spacingSm

                            AppControls.Label {
                                text: _secCard.modelData.title
                                color: Theme.AppTheme.textPrimary
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.bodySize
                                font.bold: true
                            }

                            Repeater {
                                model: _secCard.modelData.rows || []
                                delegate: RowLayout {
                                    required property var modelData
                                    Layout.fillWidth: true
                                    spacing: Theme.AppTheme.spacingSm
                                    AppControls.Label { Layout.preferredWidth: 180; text: modelData.label; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                    AppControls.Label { Layout.fillWidth: true; text: modelData.value; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
