import QtQuick
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

PlatformWidgets.RecordListCard {
    id: root

    property PlatformControllers.PlatformControlWorkspaceController workspaceController

    title: root.workspaceController ? (root.workspaceController.auditFeed.title || "Recent Audit Feed") : "Recent Audit Feed"
    subtitle: root.workspaceController ? (root.workspaceController.auditFeed.subtitle || "") : ""
    emptyState: root.workspaceController ? (root.workspaceController.auditFeed.emptyState || "") : ""
    items: root.workspaceController ? (root.workspaceController.auditFeed.items || []) : []
}
