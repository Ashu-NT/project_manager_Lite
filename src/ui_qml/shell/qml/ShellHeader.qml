import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Rectangle {
    id: header

    property ShellContexts.ShellContext shellModel
    property bool sidebarCollapsed: false

    signal toggleSidebar()

    height: 48
    color: Theme.AppTheme.surface

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.spacingMd
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: 0

        // Sidebar toggle button
        Rectangle {
            width: 32
            height: 32
            radius: Theme.AppTheme.radiusSm
            color: toggleHover.containsMouse
                ? Theme.AppTheme.hoverSurface
                : "transparent"

            Text {
                anchors.centerIn: parent
                font.family: "Segoe MDL2 Assets"
                font.pixelSize: 14
                renderType: Text.NativeRendering
                color: Theme.AppTheme.textMuted
                Component.onCompleted: text = String.fromCodePoint(0xE700)
            }

            MouseArea {
                id: toggleHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: header.toggleSidebar()
            }

            ToolTip {
                visible: toggleHover.containsMouse
                text: header.sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"
                delay: 500
            }
        }

        Item { width: Theme.AppTheme.spacingMd }

        // App identity
        Label {
            text: header.shellModel ? header.shellModel.appTitle : "TECHASH Enterprise"
            color: Theme.AppTheme.accent
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        // Divider
        Rectangle {
            width: 1
            height: 20
            color: Theme.AppTheme.divider
            Layout.leftMargin: Theme.AppTheme.spacingMd
            Layout.rightMargin: Theme.AppTheme.spacingMd
        }

        // Current workspace title
        Label {
            Layout.preferredWidth: 220
            text: header.shellModel ? (header.shellModel.currentRouteTitle || "") : ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            elide: Text.ElideRight
        }

        Item { Layout.fillWidth: true }

        // Notifications
        Rectangle {
            width: 30
            height: 30
            radius: 15
            color: notifHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

            Text {
                anchors.centerIn: parent
                font.family: "Segoe MDL2 Assets"
                font.pixelSize: 14
                renderType: Text.NativeRendering
                color: Theme.AppTheme.textMuted
                Component.onCompleted: text = String.fromCodePoint(0xEA8F)
            }

            MouseArea {
                id: notifHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
            }
        }

        Item { width: Theme.AppTheme.spacingSm }

        // User avatar + name
        RowLayout {
            spacing: Theme.AppTheme.spacingSm

            Rectangle {
                width: 28
                height: 28
                radius: 14
                color: Theme.AppTheme.accentSoft

                Label {
                    anchors.centerIn: parent
                    text: {
                        const name = header.shellModel ? (header.shellModel.userDisplayName || "") : ""
                        return name.length > 0 ? name.charAt(0).toUpperCase() : "U"
                    }
                    color: Theme.AppTheme.accent
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    font.bold: true
                }
            }

            Label {
                text: header.shellModel ? (header.shellModel.userDisplayName || "") : ""
                color: Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.smallSize
                elide: Text.ElideRight
            }
        }
    }
}
