import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
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

                delegate: AppWidgets.MetricCard {
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
