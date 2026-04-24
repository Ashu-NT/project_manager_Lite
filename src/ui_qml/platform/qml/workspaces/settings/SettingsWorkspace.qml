import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets
import Platform.Dialogs 1.0 as PlatformDialogs
import Platform.Widgets 1.0 as PlatformWidgets

AppLayouts.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.settings")
    property QtObject workspaceController: platformWorkspaceCatalog.settingsWorkspace

    function moduleItemById(itemId) {
        const items = workspaceController.moduleEntitlements.items || []
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
                    value: workspaceController.overview.statusLabel || ""
                    supportingText: workspaceModel.summary
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
                title: workspaceController.moduleEntitlements.title || "Module Entitlements"
                subtitle: workspaceController.moduleEntitlements.subtitle || ""
                emptyState: workspaceController.moduleEntitlements.emptyState || ""
                items: workspaceController.moduleEntitlements.items || []
                actionsEnabled: !workspaceController.isBusy
                primaryActionLabel: "Toggle License"
                secondaryActionLabel: "Toggle Enabled"
                tertiaryActionLabel: "Change Status"

                onPrimaryActionRequested: function(itemId) {
                    workspaceController.toggleModuleLicensed(itemId)
                }

                onSecondaryActionRequested: function(itemId) {
                    workspaceController.toggleModuleEnabled(itemId)
                }

                onTertiaryActionRequested: function(itemId) {
                    const item = moduleItemById(itemId)
                    if (item !== null) {
                        lifecycleDialog.openForItem(item, workspaceController.lifecycleOptions || [])
                    }
                }
            }

            PlatformWidgets.RecordListCard {
                Layout.fillWidth: true
                title: workspaceController.organizationProfiles.title || "Organization Profiles"
                subtitle: workspaceController.organizationProfiles.subtitle || ""
                emptyState: workspaceController.organizationProfiles.emptyState || ""
                items: workspaceController.organizationProfiles.items || []
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

    PlatformDialogs.ModuleLifecycleDialog {
        id: lifecycleDialog

        onStatusConfirmed: function(moduleCode, lifecycleStatus) {
            workspaceController.changeModuleLifecycleStatus(moduleCode, lifecycleStatus)
            close()
        }
    }
}
