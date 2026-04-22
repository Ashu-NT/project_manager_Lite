import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../shared/qml/layouts" as LayoutPrimitives
import "../../shared/qml/theme" as Theme
import "../../shared/qml/widgets" as Widgets

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

            LayoutPrimitives.WorkspaceFrame {
                Layout.fillWidth: true
                Layout.fillHeight: true
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

                    Item {
                        Layout.fillHeight: true
                    }
                }
            }
        }
    }
}
