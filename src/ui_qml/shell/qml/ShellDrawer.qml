pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Rectangle {
    id: drawer
    property ShellContexts.ShellContext shellModel

    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.surfaceAlt
    border.color: Theme.AppTheme.border

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        Label {
            text: "Navigation"
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.titleSize
            font.bold: true
        }

        Label {
            Layout.fillWidth: true
            text: "Migrated QML workspaces register routes here."
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: drawer.shellModel ? drawer.shellModel.navigationItems : []

            delegate: Rectangle {
                id: navigationCard
                required property var modelData
                property string currentRouteId: drawer.shellModel ? drawer.shellModel.currentRouteId : ""

                Layout.fillWidth: true
                height: 52
                radius: Theme.AppTheme.radiusMd
                color: navigationCard.modelData.routeId === navigationCard.currentRouteId
                    ? Theme.AppTheme.accentSoft
                    : Theme.AppTheme.surface
                border.color: navigationCard.modelData.routeId === navigationCard.currentRouteId
                    ? Theme.AppTheme.accent
                    : Theme.AppTheme.border

                Column {
                    anchors.fill: parent
                    anchors.leftMargin: 14
                    anchors.rightMargin: 14
                    anchors.topMargin: 8
                    spacing: 2

                    Label {
                        text: navigationCard.modelData.title
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.bold: true
                    }

                    Label {
                        text: navigationCard.modelData.moduleLabel + " / " + navigationCard.modelData.groupLabel
                        color: Theme.AppTheme.textSecondary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.smallSize
                    }
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: {
                        if (drawer.shellModel) {
                            drawer.shellModel.selectRoute(navigationCard.modelData.routeId)
                        }
                    }
                }
            }
        }

        Item {
            Layout.fillHeight: true
        }
    }
}
