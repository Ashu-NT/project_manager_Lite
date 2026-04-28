import QtQuick
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Widgets 1.0 as PlatformWidgets

PlatformWidgets.RecordListCard {
    id: root

    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController

    signal lifecycleRequested(string itemId)

    title: root.workspaceController ? (root.workspaceController.moduleEntitlements.title || "Module Entitlements") : "Module Entitlements"
    subtitle: root.workspaceController ? (root.workspaceController.moduleEntitlements.subtitle || "") : ""
    emptyState: root.workspaceController ? (root.workspaceController.moduleEntitlements.emptyState || "") : ""
    items: root.workspaceController ? (root.workspaceController.moduleEntitlements.items || []) : []
    actionsEnabled: root.workspaceController ? !root.workspaceController.isBusy : false
    primaryActionLabel: "Toggle License"
    secondaryActionLabel: "Toggle Enabled"
    tertiaryActionLabel: "Change Status"

    onPrimaryActionRequested: function(itemId) {
        if (root.workspaceController !== null) {
            root.workspaceController.toggleModuleLicensed(itemId)
        }
    }

    onSecondaryActionRequested: function(itemId) {
        if (root.workspaceController !== null) {
            root.workspaceController.toggleModuleEnabled(itemId)
        }
    }

    onTertiaryActionRequested: function(itemId) {
        root.lifecycleRequested(itemId)
    }
}
