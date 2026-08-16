import QtQuick
import ProjectManagement.Controllers 1.0 as PMControllers
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts


Loader {
    id: bridge

    anchors.fill: parent

    property PMControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ShellContexts.ShellContext shellModel

    source: Qt.resolvedUrl("../ProjectManagementWorkspacePage.qml")

    function _syncProperties() {
        if (!bridge.item) {
            return
        }
        bridge.item.pmCatalog = bridge.pmCatalog
        bridge.item.platformCatalog = bridge.platformCatalog
        bridge.item.shellModel = bridge.shellModel
        if (bridge.pmCatalog) {
            bridge.pmCatalog.pmNavigation.applyRoute("project_management.resources")
        }
    }

    onLoaded: bridge._syncProperties()
    onPmCatalogChanged: bridge._syncProperties()
    onPlatformCatalogChanged: bridge._syncProperties()
    onShellModelChanged: bridge._syncProperties()
}
