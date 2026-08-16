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
    minimumWidth: 1024
    minimumHeight: 700
    visible: true
    title: app.shellModel ? app.shellModel.appTitle : "TECHASH Enterprise"
    color: Theme.AppTheme.appBackground

    // R7.1: AppTheme drives every color/spacing token app-wide but has no
    // connection of its own to ShellContext's persisted theme/density state
    // -- these are the single point where the two get kept in sync.
    Binding {
        target: Theme.AppTheme
        property: "themeMode"
        value: app.shellModel ? app.shellModel.themeMode : "light"
    }
    Binding {
        target: Theme.AppTheme
        property: "densityMode"
        value: app.shellModel ? app.shellModel.densityMode : "compact"
    }

    MainWindow {
        anchors.fill: parent
        shellModel: app.shellModel
        platformCatalog: app.platformCatalog
        pmCatalog: app.pmCatalog
        inventoryCatalog: app.inventoryCatalog
        maintenanceCatalog: app.maintenanceCatalog
    }
}
