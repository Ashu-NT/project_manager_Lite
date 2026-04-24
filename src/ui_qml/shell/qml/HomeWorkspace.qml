import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

AppLayouts.WorkspaceFrame {
    title: "QML shell ready for migrated workspaces"
    subtitle: "Current route: " + shellContext.currentRouteId

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.MetricCard {
                Layout.preferredWidth: 220
                label: "Migration mode"
                value: "QML"
                supportingText: "Widget shell stays active until parity is verified."
            }

            AppWidgets.MetricCard {
                Layout.preferredWidth: 220
                label: "Routes"
                value: shellContext.navigationItems.length + ""
                supportingText: "Navigable QML routes currently registered."
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            Repeater {
                model: shellContext.navigationItems

                delegate: AppWidgets.MetricCard {
                    required property var modelData

                    width: 220
                    label: modelData.title
                    value: modelData.moduleLabel
                    supportingText: modelData.groupLabel
                }
            }
        }
    }
}
