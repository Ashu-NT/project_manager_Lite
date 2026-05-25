import QtQuick
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Item {
    id: root

    property ShellContexts.ShellContext shellModel
    property var platformCatalog
    property var pmCatalog
    property var inventoryCatalog
    property var maintenanceCatalog
    readonly property string _currentRouteSource: root.shellModel
        ? String(root.shellModel.currentRouteSource || "")
        : ""

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.background
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        ShellHeader {
            Layout.fillWidth: true
            shellModel: root.shellModel
            sidebarCollapsed: shellDrawer.collapsed
            onToggleSidebar: shellDrawer.collapsed = !shellDrawer.collapsed
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

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: Theme.AppTheme.divider
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                color: Theme.AppTheme.workspaceBackground

                Loader {
                    id: workspaceLoader
                    anchors.fill: parent
                    active: root._currentRouteSource.length > 0
                    asynchronous: true
                    source: root._currentRouteSource

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

