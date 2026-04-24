import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets
import "../../widgets" as PlatformWidgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.control")
    property QtObject workspaceController: platformWorkspaceCatalog.controlWorkspace

    title: workspaceController.overview.title || workspaceModel.title
    subtitle: workspaceController.overview.subtitle

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

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

            PlatformWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: workspaceController.isLoading
                isBusy: workspaceController.isBusy
                errorMessage: workspaceController.errorMessage
                feedbackMessage: workspaceController.feedbackMessage
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: workspaceController.approvalQueue.title || "Approval Queue"
                subtitle: workspaceController.approvalQueue.subtitle || ""
                emptyState: workspaceController.approvalQueue.emptyState || ""
                items: workspaceController.approvalQueue.items || []
                actionsEnabled: !workspaceController.isBusy
                primaryActionLabel: "Approve"
                secondaryActionLabel: "Reject"
                secondaryDanger: true

                onPrimaryActionRequested: function(itemId) {
                    workspaceController.approveRequest(itemId)
                }

                onSecondaryActionRequested: function(itemId) {
                    workspaceController.rejectRequest(itemId)
                }
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: workspaceController.auditFeed.title || "Recent Audit Feed"
                subtitle: workspaceController.auditFeed.subtitle || ""
                emptyState: workspaceController.auditFeed.emptyState || ""
                items: workspaceController.auditFeed.items || []
            }
        }
    }
}
