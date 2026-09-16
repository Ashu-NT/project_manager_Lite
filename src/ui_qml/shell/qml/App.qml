import QtQuick
import QtQuick.Controls
import QtQuick.Window
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

ApplicationWindow {
    id: app
    property ShellContexts.ShellContext shellModel
    property var platformCatalog
    property var pmCatalog
    property var globalOverviewController
    property var organizationSwitcherController
    property var notificationsController

    // Capped to the launch screen's available work area (excludes the
    // taskbar) -- a fixed 1280x800 default overflows a 13" laptop panel
    // (commonly 1280x800 or 1366x768 physical, less after the taskbar),
    // pushing the window itself (and anything anchored near its bottom,
    // like a dialog's footer buttons) below the visible screen edge.
    width: Math.min(1280, Screen.desktopAvailableWidth)
    height: Math.min(800, Screen.desktopAvailableHeight)
    minimumWidth: Math.min(1024, Screen.desktopAvailableWidth)
    minimumHeight: Math.min(700, Screen.desktopAvailableHeight)
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
        globalOverviewController: app.globalOverviewController
        organizationSwitcherController: app.organizationSwitcherController
        notificationsController: app.notificationsController
    }
}
