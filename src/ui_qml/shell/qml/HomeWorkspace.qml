import QtQuick
import QtQuick.Layouts
import "../../shared/qml/layouts" as LayoutPrimitives
import "../../shared/qml/theme" as Theme
import "../../shared/qml/widgets" as Widgets

LayoutPrimitives.WorkspaceFrame {
    title: "QML shell ready for migrated workspaces"
    subtitle: "Current route: " + shellContext.currentRouteId

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        RowLayout {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            Widgets.MetricCard {
                Layout.preferredWidth: 220
                label: "Migration mode"
                value: "QML"
                supportingText: "Widget shell stays active until parity is verified."
            }

            Widgets.MetricCard {
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

                delegate: Widgets.MetricCard {
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
