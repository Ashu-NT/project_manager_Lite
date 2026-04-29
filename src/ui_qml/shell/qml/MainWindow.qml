import QtQuick
import QtQuick.Layouts
import Platform.Controllers 1.0 as PlatformControllers
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Item {
    id: root
    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

        ShellHeader {
            Layout.fillWidth: true
            shellModel: root.shellModel
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingMd

            ShellDrawer {
                Layout.preferredWidth: 280
                Layout.fillHeight: true
                shellModel: root.shellModel
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: Theme.AppTheme.radiusLg
                color: Theme.AppTheme.surface
                border.color: Theme.AppTheme.border

                Loader {
                    id: workspaceLoader
                    anchors.fill: parent
                    anchors.margins: Theme.AppTheme.marginLg
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
                    }
                }
            }
        }
    }
}
