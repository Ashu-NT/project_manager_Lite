import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets
import "../../widgets" as PlatformWidgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.admin")
    property QtObject workspaceController: platformWorkspaceCatalog.adminWorkspace

    title: workspaceController.overview.title || workspaceModel.title
    subtitle: workspaceController.overview.subtitle

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingMd

        PlatformWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading: workspaceController.isLoading
            isBusy: workspaceController.isBusy
            errorMessage: workspaceController.errorMessage
            feedbackMessage: workspaceController.feedbackMessage
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            Repeater {
                model: workspaceController.overview.metrics || []

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
                model: workspaceController.overview.sections || []

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
