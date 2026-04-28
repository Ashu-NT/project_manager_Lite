import QtQuick
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

PlatformWidgets.RecordListCard {
    id: root

    property PlatformControllers.PlatformControlWorkspaceController workspaceController

    signal approveRequested(string itemId)
    signal rejectRequested(string itemId)

    title: root.workspaceController ? (root.workspaceController.approvalQueue.title || "Approval Queue") : "Approval Queue"
    subtitle: root.workspaceController ? (root.workspaceController.approvalQueue.subtitle || "") : ""
    emptyState: root.workspaceController ? (root.workspaceController.approvalQueue.emptyState || "") : ""
    items: root.workspaceController ? (root.workspaceController.approvalQueue.items || []) : []
    actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
    primaryActionLabel: "Approve"
    secondaryActionLabel: "Reject"
    secondaryDanger: true

    onPrimaryActionRequested: function(itemId) {
        root.approveRequested(itemId)
    }

    onSecondaryActionRequested: function(itemId) {
        root.rejectRequested(itemId)
    }
}
