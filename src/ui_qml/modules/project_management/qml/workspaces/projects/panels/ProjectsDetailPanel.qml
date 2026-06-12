pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import "../sections"

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
    property var assignableResourceOptions: []
    property string selectedProjectResourceId: ""

    signal editRequested()
    signal statusRequested()
    signal deleteRequested()

    readonly property int _idx: root.detailPage ? root.detailPage.activeSectionIndex : 0
    readonly property var _sections: root.detailPage ? (root.detailPage.sections || []) : []

    function _secIdx(name) { return root._sections.indexOf(name) }

    readonly property int _activeSectionH: {
        const name = root._sections[root._idx] || ""
        if (name === "Overview")        return _sec0.implicitHeight
        if (name === "Schedule")        return _sec1.implicitHeight
        if (name === "Tasks")           return _sec2.implicitHeight
        if (name === "Resources")       return _sec3.implicitHeight
        if (name === "Financials")      return _sec4.implicitHeight
        if (name === "Risks")           return _sec5.implicitHeight
        if (name === "Documents")       return _sec6.implicitHeight
        if (name === "Activity")        return _sec7.implicitHeight
        if (name === "Material Demand") return _sec8.implicitHeight
        if (name === "Procurement")     return _sec9.implicitHeight
        return 0
    }

    implicitHeight: _activeSectionH
    height: implicitHeight

    AppWidgets.LazySectionLoader {
        id: _sec0
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
        id: _sec1
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Schedule")
        loadingMessage: "Loading schedule..."
        sourceComponent: Component {
            ProjectsScheduleSection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec2
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
        id: _sec3
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
        id: _sec4
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Financials")
        loadingMessage: "Loading financials..."
        sourceComponent: Component {
            ProjectsFinancialsSection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec5
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Risks")
        loadingMessage: "Loading risks..."
        sourceComponent: Component {
            ProjectsRisksSection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec6
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Documents")
        loadingMessage: "Loading documents..."
        sourceComponent: Component {
            ProjectsDocumentsSection {
                width: parent ? parent.width : 0
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec7
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Activity")
        loadingMessage: "Loading activity..."
        sourceComponent: Component {
            ProjectsActivitySection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec8
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Material Demand")
        loadingMessage: "Loading..."
        sourceComponent: Component {
            ProjectsMaterialDemandSection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
                sectionErrors: root.sectionErrors
            }
        }
    }

    AppWidgets.LazySectionLoader {
        id: _sec9
        anchors.left: parent.left
        anchors.right: parent.right
        active: root._idx === root._secIdx("Procurement")
        loadingMessage: "Loading..."
        sourceComponent: Component {
            ProjectsProcurementSection {
                width: parent ? parent.width : 0
                projectDetail: root.projectDetail
                sectionErrors: root.sectionErrors
            }
        }
    }
}
