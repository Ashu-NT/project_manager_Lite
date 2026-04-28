import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import Platform.Controllers 1.0 as PlatformControllers
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

AppLayouts.WorkspaceFrame {
    id: root

    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property var workspaceModel: root.platformCatalog
        ? root.platformCatalog.workspace("platform.settings")
        : ({
            "routeId": "platform.settings",
            "title": "Settings",
            "summary": ""
        })
    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController: root.platformCatalog
        ? root.platformCatalog.settingsWorkspace
        : null

    function moduleItemById(itemId) {
        const items = root.workspaceController ? (root.workspaceController.moduleEntitlements.items || []) : []
        for (let index = 0; index < items.length; index += 1) {
            if (items[index].id === itemId) {
                return items[index]
            }
        }
        return null
    }

    title: root.workspaceController ? (root.workspaceController.overview.title || root.workspaceModel.title) : root.workspaceModel.title
    subtitle: root.workspaceController ? root.workspaceController.overview.subtitle : ""

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: Theme.AppTheme.spacingMd

            SettingsMetricsSection {
                Layout.fillWidth: true
                metrics: root.workspaceController ? (root.workspaceController.overview.metrics || []) : []
            }

            SettingsRuntimeSection {
                Layout.fillWidth: true
                themeMode: root.shellModel ? root.shellModel.themeMode : "light"
                platformStatusLabel: root.workspaceController ? (root.workspaceController.overview.statusLabel || "") : ""
                workspaceSummary: root.workspaceModel.summary || ""
            }

            PlatformWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ModuleEntitlementsSection {
                Layout.fillWidth: true
                workspaceController: root.workspaceController

                onLifecycleRequested: function(itemId) {
                    const item = root.moduleItemById(itemId)
                    if (item !== null && root.workspaceController !== null) {
                        lifecycleDialog.openForItem(item, root.workspaceController.lifecycleOptions || [])
                    }
                }
            }

            OrganizationProfilesSection {
                Layout.fillWidth: true
                workspaceController: root.workspaceController
            }

            SettingsOverviewSections {
                Layout.fillWidth: true
                sections: root.workspaceController ? (root.workspaceController.overview.sections || []) : []
            }
        }
    }

    PlatformDialogs.ModuleLifecycleDialog {
        id: lifecycleDialog

        onStatusConfirmed: function(moduleCode, lifecycleStatus) {
            if (root.workspaceController !== null) {
                root.workspaceController.changeModuleLifecycleStatus(moduleCode, lifecycleStatus)
            }
            lifecycleDialog.close()
        }
    }
}
