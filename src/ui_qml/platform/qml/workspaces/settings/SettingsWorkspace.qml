import QtQuick
import QtQuick.Layouts
import "../../../../shared/qml/layouts" as LayoutPrimitives
import "../../../../shared/qml/theme" as Theme
import "../../../../shared/qml/widgets" as Widgets
import "../../widgets" as PlatformWidgets

LayoutPrimitives.WorkspaceFrame {
    property var workspaceModel: platformWorkspaceCatalog.workspace("platform.settings")
    property QtObject workspaceController: platformWorkspaceCatalog.settingsWorkspace

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

            RowLayout {
                Layout.fillWidth: true
                spacing: Theme.AppTheme.spacingMd

                Widgets.MetricCard {
                    Layout.preferredWidth: 240
                    label: "Theme"
                    value: shellContext.themeMode
                    supportingText: "Theme state is exposed through shellContext for QML binding."
                }

                Widgets.MetricCard {
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

                onPrimaryActionRequested: function(itemId) {
                    workspaceController.toggleModuleLicensed(itemId)
                }

                onSecondaryActionRequested: function(itemId) {
                    workspaceController.toggleModuleEnabled(itemId)
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
}
