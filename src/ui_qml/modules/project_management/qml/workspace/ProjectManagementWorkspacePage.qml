pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as PMControllers
import Platform.Controllers 1.0 as PlatformControllers
import Shell.Context 1.0 as ShellContexts
import "components" as Components


Item {
    id: root

    property PMControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property PlatformControllers.PlatformWorkspaceCatalog platformCatalog
    property ShellContexts.ShellContext shellModel

    readonly property var _nav: root.pmCatalog ? root.pmCatalog.pmNavigation : null
    readonly property string _activeWorkspaceKey: root._nav ? root._nav.workspaceKey : "dashboard"

    property var _activatedKeys: ({})

    function _markActiveKeyLoaded() {
        if (root._activatedKeys[root._activeWorkspaceKey] === true) {
            return
        }
        const updated = Object.assign({}, root._activatedKeys)
        updated[root._activeWorkspaceKey] = true
        root._activatedKeys = updated
    }

    Component.onCompleted: root._markActiveKeyLoaded()

    // Connects to the real, unambiguously-named Qt signal directly
    // (rather than relying on QML's synthesized change-notification
    // handler name for a local underscore-prefixed computed property,
    // which proved inconsistent to predict).
    Connections {
        target: root._nav
        function onSelectionChanged() {
            root._markActiveKeyLoaded()
        }
    }

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.workspaceBackground
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: 0

            Components.PmWorkspaceNavigation {
                objectName: "pmWorkspaceNavigation"
                Layout.fillHeight: true
                navigationItems: root._nav ? root._nav.navigationItems : []
                selectedWorkspaceKey: root._activeWorkspaceKey
                onWorkspaceSelected: function(workspaceKey) {
                    if (root._nav) root._nav.selectWorkspace(workspaceKey)
                }
            }

            Rectangle {
                Layout.preferredWidth: Theme.AppTheme.borderWidthThin
                Layout.fillHeight: true
                color: Theme.AppTheme.divider
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Repeater {
                    model: [
                        { key: "dashboard", file: "../workspaces/dashboard/DashboardWorkspacePage.qml" },
                        { key: "portfolio", file: "../workspaces/portfolio/PortfolioWorkspacePage.qml" },
                        { key: "projects", file: "../workspaces/projects/ProjectsWorkspacePage.qml" },
                        { key: "tasks", file: "../workspaces/tasks/TasksWorkspacePage.qml" },
                        { key: "scheduling", file: "../workspaces/scheduling/SchedulingWorkspacePage.qml" },
                        { key: "timesheets", file: "../workspaces/resource_timesheets/ResourceTimesheetsPage.qml" },
                        { key: "resources", file: "../workspaces/resources/ResourcesWorkspacePage.qml" },
                        { key: "review_queue", file: "../workspaces/timesheets/TimesheetsWorkspacePage.qml" },
                        { key: "financials", file: "../workspaces/financials/FinancialsWorkspacePage.qml" },
                        { key: "register", file: "../workspaces/register/RegisterWorkspacePage.qml" },
                        { key: "collaboration", file: "../workspaces/collaboration/CollaborationWorkspacePage.qml" },
                    ]

                    delegate: Loader {
                        id: _capabilityLoader
                        required property var modelData

                        anchors.fill: parent
                        active: root._activatedKeys[_capabilityLoader.modelData.key] === true
                        visible: _capabilityLoader.active
                            && root._activeWorkspaceKey === _capabilityLoader.modelData.key
                        asynchronous: false
                        source: _capabilityLoader.active
                            ? Qt.resolvedUrl(_capabilityLoader.modelData.file)
                            : ""

                        onLoaded: {
                            if (_capabilityLoader.item) {
                                _capabilityLoader.item.pmCatalog = Qt.binding(function() {
                                    return root.pmCatalog
                                })
                                if ("shellModel" in _capabilityLoader.item) {
                                    _capabilityLoader.item.shellModel = Qt.binding(function() {
                                        return root.shellModel
                                    })
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
