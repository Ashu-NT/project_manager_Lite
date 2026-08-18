pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import workspaces.projects.sections 1.0

Item {
    id: root

    property var projectDetail: ({
        "id": "", "title": "", "statusLabel": "", "subtitle": "",
        "description": "", "emptyState": "", "fields": [], "state": {}
    })
    property bool isBusy: false
    property var detailPage: null
    property var sectionErrors: ({})
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property var projectTasksModel: ({
        "title": "Tasks", "subtitle": "", "emptyState": "Open this section to load project tasks.", "items": []
    })
    property var projectTasksTableModel: null
    property var projectResourcesModel: ({
        "title": "Resources", "subtitle": "", "emptyState": "Open this section to load project resources.", "items": []
    })
    property var projectResourcesTableModel: null
    property var projectRisksModel: ({
        "title": "Risks", "subtitle": "", "emptyState": "Open this section to load project risks.", "items": []
    })
    property var projectActivityModel: ({
        "title": "Activity", "subtitle": "", "emptyState": "Open this section to load project activity.", "items": []
    })
    property var assignableResourceOptions: []
    property string selectedProjectResourceId: ""

    signal editRequested()
    signal statusRequested()
    signal deleteRequested()

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) { return root._sections.indexOf(name) }

    function openSelectedProjectResourceEditDialog() {
        const section = _secResources.item
        if (section) {
            section.openEditSelected()
        }
    }

    function confirmSelectedProjectResourceRemoval() {
        const section = _secResources.item
        if (section) {
            section.confirmRemoveSelected()
        }
    }

    readonly property int _activeSectionH: {
        const name = root._sections[root._idx] || ""
        if (name === "Overview")   return _secOverview.implicitHeight
        if (name === "Tasks")      return _secTasks.implicitHeight
        if (name === "Resources")  return _secResources.implicitHeight
        if (name === "Risks")      return _secRisks.implicitHeight
        if (name === "Activity")   return _secActivity.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _secOverview
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Overview")
        loadingMessage: "Loading overview..."
        sourceComponent: Component {
            ProjectsOverviewSection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _secTasks
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Tasks")
        loadingMessage: "Loading tasks..."
        sourceComponent: Component {
            ProjectsTasksSection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
                projectTasksModel: root.projectTasksModel
                projectTasksTableModel: root.projectTasksTableModel
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _secResources
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Resources")
        loadingMessage: "Loading resources..."
        sourceComponent: Component {
            ProjectsResourcesSection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
                pmCatalog: root.pmCatalog
                projectDetail: root.projectDetail
                projectResourcesModel: root.projectResourcesModel
                projectResourcesTableModel: root.projectResourcesTableModel
                assignableResourceOptions: root.assignableResourceOptions
                selectedProjectResourceId: root.selectedProjectResourceId
                isBusy: root.isBusy
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _secRisks
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Risks")
        loadingMessage: "Loading risks..."
        sourceComponent: Component {
            ProjectsRisksSection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
                projectRisksModel: root.projectRisksModel
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _secActivity
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Activity")
        loadingMessage: "Loading activity..."
        sourceComponent: Component {
            ProjectsActivitySection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
                projectActivityModel: root.projectActivityModel
            }
        }
    }
}
