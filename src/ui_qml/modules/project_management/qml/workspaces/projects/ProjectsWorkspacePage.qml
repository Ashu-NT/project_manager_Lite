import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementProjectsWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.projectsWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.projects",
            "title": "Projects",
            "summary": "Project lifecycle, ownership, status, and project list workflows.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget projects workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var projectsModel: root.workspaceController
        ? root.workspaceController.projects
        : ({
            "title": "Project Catalog",
            "subtitle": "Create, edit, and review project lifecycle records.",
            "emptyState": "Project-management projects desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedProjectModel: root.workspaceController
        ? root.workspaceController.selectedProject
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a project from the catalog to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    ProjectsDialogHost {
        id: dialogHost

        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createProject(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateProject(payload)
            }
        }

        onStatusChangeRequested: function(projectId, statusValue) {
            if (root.workspaceController !== null) {
                root.workspaceController.setProjectStatus(projectId, statusValue)
            }
        }

        onDeleteRequested: function(projectId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteProject(projectId)
            }
        }
    }

    Flickable {
        anchors.fill: parent
        contentWidth: width
        contentHeight: contentColumn.implicitHeight
        clip: true

        ColumnLayout {
            id: contentColumn

            width: parent.width
            spacing: 12

            ProjectsMetricsSection {
                Layout.fillWidth: true
                metrics: root.overviewModel.metrics || []
            }

            ProjectManagementWidgets.WorkspaceStateBanner {
                Layout.fillWidth: true
                isLoading: root.workspaceController ? root.workspaceController.isLoading : false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
                feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
            }

            ProjectManagementWidgets.WorkspaceStatusSection {
                Layout.fillWidth: true
                migrationStatus: root.workspaceController
                    ? "QML CRUD projects slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Project list, filters, create, edit, status, and delete flows now run through a typed PM controller backed by the project desktop API."
            }

            ProjectsFiltersSection {
                Layout.fillWidth: true
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onSearchTextUpdated: function(searchText) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setSearchText(searchText)
                    }
                }

                onStatusFilterUpdated: function(statusValue) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.setStatusFilter(statusValue)
                    }
                }

                onRefreshRequested: function() {
                    if (root.workspaceController !== null) {
                        root.workspaceController.refresh()
                    }
                }

                onCreateRequested: function() {
                    dialogHost.openCreateDialog()
                }
            }

            GridLayout {
                Layout.fillWidth: true
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                ProjectsCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    projectsModel: root.projectsModel
                    selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onProjectSelected: function(projectId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectProject(projectId)
                        }
                    }

                    onEditRequested: function(projectData) {
                        if (projectData && projectData.id && root.workspaceController !== null) {
                            root.workspaceController.selectProject(projectData.id)
                        }
                        dialogHost.openEditDialog(projectData)
                    }

                    onStatusRequested: function(projectData) {
                        if (projectData && projectData.id && root.workspaceController !== null) {
                            root.workspaceController.selectProject(projectData.id)
                        }
                        dialogHost.openStatusDialog(projectData)
                    }

                    onDeleteRequested: function(projectData) {
                        if (projectData && projectData.id && root.workspaceController !== null) {
                            root.workspaceController.selectProject(projectData.id)
                        }
                        dialogHost.openDeleteDialog(projectData)
                    }
                }

                ProjectsDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    projectDetail: root.selectedProjectModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedProjectModel)
                    onStatusRequested: dialogHost.openStatusDialog(root.selectedProjectModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedProjectModel)
                }
            }
        }
    }
}
