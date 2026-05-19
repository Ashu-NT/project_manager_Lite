import QtQuick
import QtQuick.Layouts
import InventoryProcurement.Controllers 1.0 as InventoryProcurementControllers
import Maintenance.Controllers 1.0 as MaintenanceControllers
import Platform.Controllers 1.0 as PlatformControllers
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Item {
    id: root
    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property InventoryProcurementControllers.InventoryProcurementWorkspaceCatalog inventoryCatalog
    property MaintenanceControllers.MaintenanceWorkspaceCatalog maintenanceCatalog

    // Full-bleed layout: header at top, sidebar + content fill the rest
    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ShellHeader {
            Layout.fillWidth: true
            shellModel: root.shellModel
            sidebarCollapsed: shellDrawer.collapsed
            onToggleSidebar: shellDrawer.collapsed = !shellDrawer.collapsed
        }

        // Single-pixel divider below header
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            ShellDrawer {
                id: shellDrawer
                Layout.preferredWidth: shellDrawer.implicitWidth
                Layout.fillHeight: true
                shellModel: root.shellModel
            }

            // Vertical divider between drawer and content
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: Theme.AppTheme.divider
            }

            // Main workspace content — no border wrapper
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Loader {
                    id: workspaceLoader
                    anchors.fill: parent
                    source: root.shellModel ? root.shellModel.currentRouteSource : ""

                    onLoaded: {
                        if (item === null) {
                            return
                        }
                        if ("shellModel" in item) {
                            item.shellModel = root.shellModel
                        }
                        if ("platformCatalog" in item) {
                            item.platformCatalog = root.platformCatalog
                        }
                        if ("pmCatalog" in item) {
                            item.pmCatalog = root.pmCatalog
                        }
                        if ("inventoryCatalog" in item) {
                            item.inventoryCatalog = root.inventoryCatalog
                        }
                        if ("maintenanceCatalog" in item) {
                            item.maintenanceCatalog = root.maintenanceCatalog
                        }
                    }
                }
            }
        }
    }
}
