import QtQuick
import QtQuick.Controls
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

ApplicationWindow {
    id: app
    property ShellContexts.ShellContext shellModel
    property var platformCatalog
    property var pmCatalog
    property var inventoryCatalog
    property var maintenanceCatalog

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
        inventoryCatalog: app.inventoryCatalog
        maintenanceCatalog: app.maintenanceCatalog
    }
}

