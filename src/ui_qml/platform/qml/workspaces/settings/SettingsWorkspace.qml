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
    property var workspaceModel: root.platformCatalog.workspace("platform.settings")
    property PlatformControllers.PlatformSettingsWorkspaceController workspaceController: root.platformCatalog.settingsWorkspace

    function moduleItemById(itemId) {
        const items = root.workspaceController.moduleEntitlements.items || []
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

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.MetricCard {
                    Layout.preferredWidth: 240
                    label: "Theme"
                    value: shellContext.themeMode
                    supportingText: "Theme state is exposed through shellContext for QML binding."
                }

                AppWidgets.MetricCard {
                    Layout.preferredWidth: 240
                    label: "Platform API"
                    value: root.workspaceController.overview.statusLabel || ""
                    supportingText: root.workspaceModel.summary
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
                title: root.workspaceController.moduleEntitlements.title || "Module Entitlements"
                subtitle: root.workspaceController.moduleEntitlements.subtitle || ""
                emptyState: root.workspaceController.moduleEntitlements.emptyState || ""
                items: root.workspaceController.moduleEntitlements.items || []
                actionsEnabled: !root.workspaceController.isBusy
                primaryActionLabel: "Toggle License"
                secondaryActionLabel: "Toggle Enabled"
                tertiaryActionLabel: "Change Status"

                onPrimaryActionRequested: function(itemId) {
                    root.workspaceController.toggleModuleLicensed(itemId)
                }

                onSecondaryActionRequested: function(itemId) {
                    root.workspaceController.toggleModuleEnabled(itemId)
                }

                onTertiaryActionRequested: function(itemId) {
                    const item = root.moduleItemById(itemId)
                    if (item !== null) {
                        lifecycleDialog.openForItem(item, root.workspaceController.lifecycleOptions || [])
                    }
                }
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: root.workspaceController.organizationProfiles.title || "Organization Profiles"
                subtitle: root.workspaceController.organizationProfiles.subtitle || ""
                emptyState: root.workspaceController.organizationProfiles.emptyState || ""
                items: root.workspaceController.organizationProfiles.items || []
            }

            Flow {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Repeater {
                    model: root.workspaceController.overview.sections || []

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

    PlatformDialogs.ModuleLifecycleDialog {
        id: lifecycleDialog

        onStatusConfirmed: function(moduleCode, lifecycleStatus) {
            root.workspaceController.changeModuleLifecycleStatus(moduleCode, lifecycleStatus)
            lifecycleDialog.close()
        }
    }
}
