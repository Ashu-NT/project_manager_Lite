import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets
import "../../widgets" as PlatformWidgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.admin")
    property var overview: platformWorkspaceCatalog.adminOverview()

    title: overview.title || workspaceModel.title
    subtitle: overview.subtitle

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            Repeater {
                model: overview.metrics

                delegate: Widgets.MetricCard {
                    required property var modelData

                    width: 210
                    label: modelData.label
                    value: modelData.value
                    supportingText: modelData.supportingText
                }
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            Repeater {
                model: overview.sections

                delegate: PlatformWidgets.OverviewSectionCard {
                    required property var modelData

                    width: 320
                    title: modelData.title
                    rows: modelData.rows
                    emptyState: modelData.emptyState
                }
            }
        }
    }
}
