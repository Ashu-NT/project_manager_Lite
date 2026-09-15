import QtQuick
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root
    objectName: "mainWindow"

    property ShellContexts.ShellContext shellModel
    property var platformCatalog
    property var pmCatalog
    property var globalOverviewController
    property var organizationSwitcherController
    property var notificationsController
    property bool _notificationsPanelOpen: false
    property bool _globalNavCollapsed: false
    readonly property string _currentRouteSource: root.shellModel
        ? String(root.shellModel.currentRouteSource || "")
        : ""
    readonly property string _currentModuleCode: root.shellModel
        ? String(root.shellModel.currentModuleCode || "")
        : ""
    readonly property bool _showContextNav: root._currentModuleCode === "platform"
        || root._currentModuleCode === "project_management"

    readonly property var _contextGroups: {
        if (root._currentModuleCode === "platform" && root.platformCatalog) {
            return root.platformCatalog.contextNavigation
        }
        if (root._currentModuleCode === "project_management" && root.pmCatalog) {
            return root.pmCatalog.pmNavigation.contextNavigation
        }
        return []
    }

    readonly property string _contextActiveId: {
        if (root._currentModuleCode === "platform" && root.platformCatalog) {
            return root.platformCatalog.currentDestinationId
        }
        if (root._currentModuleCode === "project_management" && root.pmCatalog) {
            return root.pmCatalog.pmNavigation.workspaceKey
        }
        return ""
    }

    readonly property var _breadcrumb: {
        if (root._currentModuleCode === "platform" && root.platformCatalog) {
            return root.platformCatalog.breadcrumb
        }
        if (root._currentModuleCode === "project_management" && root.pmCatalog) {
            return root.pmCatalog.pmNavigation.breadcrumb
        }
        return []
    }

    function _selectContextDestination(destinationId) {
        if (root._currentModuleCode === "platform" && root.platformCatalog) {
            root.platformCatalog.selectDestination(destinationId)
            return
        }
        if (root._currentModuleCode === "project_management" && root.pmCatalog) {
            root.pmCatalog.pmNavigation.selectWorkspace(destinationId)
            return
        }
    }

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
            platformCatalog: root.platformCatalog
            organizationSwitcherController: root.organizationSwitcherController
            notificationsController: root.notificationsController
            sidebarCollapsed: root._globalNavCollapsed
            onToggleSidebar: root._globalNavCollapsed = !root._globalNavCollapsed
            onNotificationsRequested: root._notificationsPanelOpen = true
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            AppWidgets.NavigationTree {
                id: globalNavTree
                objectName: "globalNavigationTree"
                Layout.preferredWidth: globalNavTree.implicitWidth
                Layout.fillHeight: true
                groups: root.shellModel ? root.shellModel.globalNavigation : []
                activeId: root.shellModel ? root.shellModel.currentRouteId : ""
                collapsed: root._globalNavCollapsed
                autoCollapseAtNarrowWidth: true
                onItemActivated: function(id, routeId) {
                    if (root.shellModel) {
                        root.shellModel.selectRoute(routeId)
                    }
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                color: Theme.AppTheme.divider
            }

            Loader {
                id: contextNavLoader
                Layout.fillHeight: true
                Layout.preferredWidth: item ? item.implicitWidth : 0
                active: root._showContextNav
                visible: active
                sourceComponent: Component {
                    AppWidgets.NavigationTree {
                        objectName: "contextNavigationTree"
                        railTitle: root._currentModuleCode === "platform" ? "Platform" : "Project Management"
                        showRailToggle: true
                        groups: root._contextGroups
                        activeId: root._contextActiveId
                        onItemActivated: function(id, _routeId) {
                            root._selectContextDestination(id)
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 1
                visible: contextNavLoader.active
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
                        if ("globalOverviewController" in item) {
                            item.globalOverviewController = root.globalOverviewController
                        }
                        if ("breadcrumb" in item) {
                            item.breadcrumb = Qt.binding(function() { return root._breadcrumb })
                        }
                    }
                }
            }
        }
    }

    NotificationsPanel {
        anchors.fill: parent
        controller: root.notificationsController
        open: root._notificationsPanelOpen
        onCloseRequested: root._notificationsPanelOpen = false
    }
}
