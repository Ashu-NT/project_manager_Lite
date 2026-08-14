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
    readonly property var _projectContext: root.pmCatalog ? root.pmCatalog.pmProjectContext : null
    readonly property string _activeWorkspaceKey: root._nav ? root._nav.workspaceKey : "dashboard"
    readonly property string _activePolicy: root._nav ? root._nav.projectContextPolicy : "optional"
    readonly property bool _contextSatisfied: root.pmCatalog
        ? root.pmCatalog.projectContextRequirementSatisfied
        : true

    // R2.12: lazy on first activation only. A destination's Loader turns
    // on the first time it's both selected AND context-satisfied, and then
    // stays on -- switching away only hides it (Loader.visible), it never
    // tears the page back down. This is deliberate, not just an
    // optimization: several capability pages host the shared
    // SectionDetailPage, which schedules a Qt.callLater() reparent that
    // can fire after its context is destroyed if the page is torn down and
    // recreated while such a call is pending. Keeping a visited
    // destination mounted sidesteps that shared-widget hazard entirely
    // instead of patching a widely-used primitive as a side effect of R2.
    property var _activatedKeys: ({})

    function _markActiveKeyLoaded() {
        if (!root._contextSatisfied) {
            return
        }
        if (root._activatedKeys[root._activeWorkspaceKey] === true) {
            return
        }
        const updated = Object.assign({}, root._activatedKeys)
        updated[root._activeWorkspaceKey] = true
        root._activatedKeys = updated
    }

    Component.onCompleted: root._markActiveKeyLoaded()

    // Connects to the real, unambiguously-named Qt signals directly
    // (rather than relying on QML's synthesized change-notification
    // handler name for a local underscore-prefixed computed property,
    // which proved inconsistent to predict).
    Connections {
        target: root._nav
        function onSelectionChanged() {
            root._markActiveKeyLoaded()
        }
    }

    Connections {
        target: root.pmCatalog
        function onProjectContextRequirementChanged() {
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

        Components.ProjectContextBar {
            objectName: "pmProjectContextBar"
            Layout.fillWidth: true
            // Only rendered for destinations that actually consume project
            // context (OPTIONAL/REQUIRED) -- destinations like Portfolio and
            // Projects operate across all projects by definition, so a
            // project picker there is meaningless chrome, not a feature.
            visible: root._activePolicy !== "not_applicable"
            Layout.preferredHeight: visible ? implicitHeight : 0
            platformCatalog: root.platformCatalog
            projectContext: root._projectContext
            currentPolicy: root._activePolicy
        }

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

                Components.ProjectContextRequiredState {
                    objectName: "pmProjectContextRequiredState"
                    anchors.fill: parent
                    visible: !root._contextSatisfied
                    destinationLabel: root._activeWorkspaceKey
                }

                // R2.6: each capability page is loaded dynamically by URL
                // (Qt.resolvedUrl, resolved relative to THIS file) rather
                // than a static cross-folder `import` -- this codebase's
                // architecture guardrails forbid parent-relative QML
                // imports, and each capability's own qmldir `module` name
                // doesn't match its physical folder path, so neither a
                // relative import nor a dotted-module import resolves
                // cross-folder. A dynamic Loader.source URL needs neither.
                Repeater {
                    model: [
                        { key: "dashboard", file: "../workspaces/dashboard/DashboardWorkspacePage.qml" },
                        { key: "portfolio", file: "../workspaces/portfolio/PortfolioWorkspacePage.qml" },
                        { key: "projects", file: "../workspaces/projects/ProjectsWorkspacePage.qml" },
                        { key: "tasks", file: "../workspaces/tasks/TasksWorkspacePage.qml" },
                        { key: "scheduling", file: "../workspaces/scheduling/SchedulingWorkspacePage.qml" },
                        { key: "resources", file: "../workspaces/resources/ResourcesWorkspacePage.qml" },
                        { key: "timesheets", file: "../workspaces/timesheets/TimesheetsWorkspacePage.qml" },
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
                            && root._contextSatisfied
                        asynchronous: false
                        source: _capabilityLoader.active
                            ? Qt.resolvedUrl(_capabilityLoader.modelData.file)
                            : ""

                        onLoaded: {
                            if (_capabilityLoader.item) {
                                _capabilityLoader.item.pmCatalog = Qt.binding(function() {
                                    return root.pmCatalog
                                })
                            }
                        }
                    }
                }
            }
        }
    }
}
