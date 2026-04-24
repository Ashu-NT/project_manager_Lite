import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog: platformWorkspaceCatalog
    property var workspaceModel: root.platformCatalog.workspace("platform.control")
    property PlatformControllers.PlatformControlWorkspaceController workspaceController: root.platformCatalog.controlWorkspace

    function approvalItemById(itemId) {
        const items = root.workspaceController.approvalQueue.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (items[index].id === itemId) {
                return items[index]
            }
        }
        return null
    }

    title: root.workspaceController.overview.title || root.workspaceModel.title
    subtitle: root.workspaceController.overview.subtitle

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
                    model: root.workspaceController.overview.metrics || []

                    delegate: AppWidgets.MetricCard {
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
                isLoading: root.workspaceController.isLoading
                isBusy: root.workspaceController.isBusy
                errorMessage: root.workspaceController.errorMessage
                feedbackMessage: root.workspaceController.feedbackMessage
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: root.workspaceController.approvalQueue.title || "Approval Queue"
                subtitle: root.workspaceController.approvalQueue.subtitle || ""
                emptyState: root.workspaceController.approvalQueue.emptyState || ""
                items: root.workspaceController.approvalQueue.items || []
                actionsEnabled: !root.workspaceController.isBusy
                primaryActionLabel: "Approve"
                secondaryActionLabel: "Reject"
                secondaryDanger: true

                onPrimaryActionRequested: function(itemId) {
                    const item = root.approvalItemById(itemId)
                    if (item !== null) {
                        decisionDialog.openForDecision("approve", item)
                    }
                }

                onSecondaryActionRequested: function(itemId) {
                    const item = root.approvalItemById(itemId)
                    if (item !== null) {
                        decisionDialog.openForDecision("reject", item)
                    }
                }
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: root.workspaceController.auditFeed.title || "Recent Audit Feed"
                subtitle: root.workspaceController.auditFeed.subtitle || ""
                emptyState: root.workspaceController.auditFeed.emptyState || ""
                items: root.workspaceController.auditFeed.items || []
            }
        }
    }

    PlatformDialogs.ApprovalDecisionDialog {
        id: decisionDialog

        onDecisionConfirmed: function(mode, requestId, note) {
            if (mode === "reject") {
                root.workspaceController.rejectRequestWithNote(requestId, note)
            } else {
                root.workspaceController.approveRequestWithNote(requestId, note)
            }
            decisionDialog.close()
        }
    }
}
