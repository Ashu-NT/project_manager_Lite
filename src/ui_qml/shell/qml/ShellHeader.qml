import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Rectangle {
    id: header
    property ShellContexts.ShellContext shellModel

    height: 48
    color: Theme.AppTheme.surface

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginLg
        anchors.rightMargin: Theme.AppTheme.marginMd
        spacing: Theme.AppTheme.spacingMd

        // App identity
        Label {
            text: header.shellModel ? header.shellModel.appTitle : "TECHASH Enterprise"
            color: Theme.AppTheme.accent
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
        }

        // Module context separator
        Rectangle {
            width: 1
            height: 20
            color: Theme.AppTheme.divider
        }

        // Current workspace title
        Label {
            Layout.preferredWidth: 200
            text: header.shellModel ? (header.shellModel.currentRouteTitle || "") : ""
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            elide: Text.ElideRight
        }

        Item { Layout.fillWidth: true }

        // Notifications placeholder
        Rectangle {
            width: 28
            height: 28
            radius: 14
            color: notifHover.containsMouse ? Theme.AppTheme.hoverSurface : "transparent"

            Label {
                anchors.centerIn: parent
                text: ""
                font.family: "Segoe MDL2 Assets"
                font.pixelSize: 14
                color: Theme.AppTheme.textMuted
                renderType: Text.NativeRendering
            }

            MouseArea {
                id: notifHover
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
            }
        }

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
