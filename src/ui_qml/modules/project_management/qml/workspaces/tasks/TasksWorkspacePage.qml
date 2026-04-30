import QtQuick
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers
import ProjectManagement.Widgets 1.0 as ProjectManagementWidgets

AppLayouts.WorkspaceFrame {
    id: root

    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property ProjectManagementControllers.ProjectManagementTasksWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.tasksWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.tasks",
            "title": "Tasks",
            "summary": "Task planning, progress, dependencies, assignments, and execution state.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget tasks workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var tasksModel: root.workspaceController
        ? root.workspaceController.tasks
        : ({
            "title": "Task Catalog",
            "subtitle": "Edit delivery tasks, progress, and execution priorities.",
            "emptyState": "Project-management tasks desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedTaskModel: root.workspaceController
        ? root.workspaceController.selectedTask
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a task from the catalog to review details or update progress.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    TasksDialogHost {
        id: dialogHost

        selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.createTask(payload)
            }
        }

        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateTask(payload)
            }
        }

        onProgressRequested: function(payload) {
            if (root.workspaceController !== null) {
                root.workspaceController.updateProgress(payload)
            }
        }

        onDeleteRequested: function(taskId) {
            if (root.workspaceController !== null) {
                root.workspaceController.deleteTask(taskId)
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

            TasksMetricsSection {
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
                    ? "QML CRUD tasks slice active"
                    : (root.workspaceModel.migrationStatus || "")
                legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
                architectureStatus: "Desktop API + typed controller"
                architectureSummary: "Task list, project filtering, create, edit, progress, and delete flows now run through a typed PM controller backed by the task desktop API."
            }

            TasksFiltersSection {
                Layout.fillWidth: true
                projectOptions: root.workspaceController ? (root.workspaceController.projectOptions || []) : []
                selectedProjectId: root.workspaceController ? root.workspaceController.selectedProjectId : ""
                statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                selectedStatusFilter: root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                searchText: root.workspaceController ? root.workspaceController.searchText : ""
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onProjectSelected: function(projectId) {
                    if (root.workspaceController !== null) {
                        root.workspaceController.selectProject(projectId)
                    }
                }

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

                TasksCatalogSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    tasksModel: root.tasksModel
                    selectedTaskId: root.workspaceController ? root.workspaceController.selectedTaskId : ""
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onTaskSelected: function(taskId) {
                        if (root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskId)
                        }
                    }

                    onEditRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openEditDialog(taskData)
                    }

                    onProgressRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openProgressDialog(taskData)
                    }

                    onDeleteRequested: function(taskData) {
                        if (taskData && taskData.id && root.workspaceController !== null) {
                            root.workspaceController.selectTask(taskData.id)
                        }
                        dialogHost.openDeleteDialog(taskData)
                    }
                }

                TasksDetailSection {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    taskDetail: root.selectedTaskModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                    onEditRequested: dialogHost.openEditDialog(root.selectedTaskModel)
                    onProgressRequested: dialogHost.openProgressDialog(root.selectedTaskModel)
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedTaskModel)
                }
            }
        }
    }
}
