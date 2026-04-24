import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.control")
    property QtObject workspaceController: platformWorkspaceCatalog.controlWorkspace

    function approvalItemById(itemId) {
        const items = workspaceController.approvalQueue.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (items[index].id === itemId) {
                return items[index]
            }
        }
        return null
    }

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
                    const item = approvalItemById(itemId)
                    if (item !== null) {
                        decisionDialog.openForDecision("approve", item)
                    }
                }

                onSecondaryActionRequested: function(itemId) {
                    const item = approvalItemById(itemId)
                    if (item !== null) {
                        decisionDialog.openForDecision("reject", item)
                    }
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

    PlatformDialogs.ApprovalDecisionDialog {
        id: decisionDialog

        onDecisionConfirmed: function(mode, requestId, note) {
            if (mode === "reject") {
                workspaceController.rejectRequestWithNote(requestId, note)
            } else {
                workspaceController.approveRequestWithNote(requestId, note)
            }
            close()
        }
    }
}
