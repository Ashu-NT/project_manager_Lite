import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ShellHeader {
            Layout.fillWidth: true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingMd

            ShellDrawer {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.AppTheme.radiusLg
                color: Theme.AppTheme.surface
                border.color: Theme.AppTheme.border

                Loader {
                    id: workspaceLoader
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginLg
                    source: shellContext.currentRouteSource
                }
            }
        }
    }
}
