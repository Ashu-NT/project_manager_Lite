import QtQuick
import QtQuick.Controls
import Platform.Controllers 1.0 as PlatformControllers
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

ApplicationWindow {
    id: app
    property ShellContexts.ShellContext shellModel
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog

    width: 1280
    height: 800
    visible: true
    title: app.shellModel ? app.shellModel.appTitle : "TECHASH Enterprise"
    color: Theme.AppTheme.appBackground

    MainWindow {
        anchors.fill: parent
        shellModel: app.shellModel
        platformCatalog: app.platformCatalog
        pmCatalog: app.pmCatalog
    }
}
