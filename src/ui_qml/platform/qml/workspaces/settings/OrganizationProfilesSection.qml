import QtQuick
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

PlatformWidgets.RecordListCard {
    id: root

    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController

    title: root.workspaceController ? (root.workspaceController.organizationProfiles.title || "Organization Profiles") : "Organization Profiles"
    subtitle: root.workspaceController ? (root.workspaceController.organizationProfiles.subtitle || "") : ""
    emptyState: root.workspaceController ? (root.workspaceController.organizationProfiles.emptyState || "") : ""
    items: root.workspaceController ? (root.workspaceController.organizationProfiles.items || []) : []
}
