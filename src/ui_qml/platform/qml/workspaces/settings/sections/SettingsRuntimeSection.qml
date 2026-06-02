pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme

Item {
    id: root

    property var workspaceController: null
    property var shellModel: null
    property var workspaceModel: ({ "summary": "" })
    property bool busy: false

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // ── Header bar ────────────────────────────────────────────────────
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Theme.AppTheme.toolbarHeight - 6
            color: Theme.AppTheme.surfaceRaised
            z: 1

            Rectangle {
                anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
                height: 1; color: Theme.AppTheme.divider
            }

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: 8
                spacing: Theme.AppTheme.spacingXs

                AppControls.Label {
                    text: "Runtime Configuration"
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
                Item { Layout.fillWidth: true }
                Rectangle {
                    implicitWidth: 26; implicitHeight: 26; radius: 4
                    color: _rtRefreshMA.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"
                    AppIcons.AppIcon { anchors.centerIn: parent; name: "refresh"; size: 12; iconColor: Theme.AppTheme.textMuted }
                    MouseArea {
                        id: _rtRefreshMA
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        enabled: !root.busy
                        onClicked: { if (root.workspaceController) root.workspaceController.refresh() }
                    }
                }
            }
        }

        // ── Property rows ─────────────────────────────────────────────────
        Flickable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            contentWidth: width
            contentHeight: _runtimeCol.implicitHeight
            clip: true
            boundsBehavior: Flickable.StopAtBounds

            ColumnLayout {
                id: _runtimeCol
                width: parent.width
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    color: "transparent"
                    Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.rightMargin: Theme.AppTheme.marginMd; spacing: Theme.AppTheme.spacingMd
                        AppControls.Label { Layout.preferredWidth: 120; text: "Theme Mode"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root.shellModel ? root.shellModel.themeMode : "—"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    color: Theme.AppTheme.surfaceOverlay
                    Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.rightMargin: Theme.AppTheme.marginMd; spacing: Theme.AppTheme.spacingMd
                        AppControls.Label { Layout.preferredWidth: 120; text: "Platform API"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root.workspaceController ? (root.workspaceController.overview.statusLabel || "—") : "—"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true; Layout.preferredHeight: 38
                    color: "transparent"
                    Rectangle { anchors { bottom: parent.bottom; left: parent.left; right: parent.right }; height: 1; color: Theme.AppTheme.divider }
                    RowLayout {
                        anchors.fill: parent; anchors.leftMargin: Theme.AppTheme.marginMd; anchors.rightMargin: Theme.AppTheme.marginMd; spacing: Theme.AppTheme.spacingMd
                        AppControls.Label { Layout.preferredWidth: 120; text: "Summary"; color: Theme.AppTheme.textMuted; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; font.bold: true }
                        AppControls.Label { Layout.fillWidth: true; text: root.workspaceModel.summary || "—"; color: Theme.AppTheme.textPrimary; font.family: Theme.AppTheme.fontFamily; font.pixelSize: Theme.AppTheme.smallSize; elide: Text.ElideRight }
                    }
                }
            }
        }
    }
}
