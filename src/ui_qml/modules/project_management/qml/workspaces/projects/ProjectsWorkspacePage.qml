import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Layouts 1.0 as AppLayouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
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

    readonly property var _tableColumns: [
        { "key": "title",       "label": "Project",  "flex": 2, "sortable": true  },
        { "key": "statusLabel", "label": "Status",   "flex": 0, "minWidth": 120, "type": "status" },
        { "key": "subtitle",    "label": "Client",   "flex": 2, "sortable": true  },
        { "key": "metaText",    "label": "Info",     "flex": 1, "minWidth": 90    }
    ]

    function _statusIndexForValue(statusValue) {
        const opts = root.workspaceController ? (root.workspaceController.statusOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(statusValue || "")) return i
        }
        return 0
    }

    ProjectsDialogHost {
        id: dialogHost

        statusOptions: root.workspaceController ? (root.workspaceController.statusOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createProject(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateProject(payload)
        }
        onStatusChangeRequested: function(projectId, statusValue) {
            if (root.workspaceController !== null) root.workspaceController.setProjectStatus(projectId, statusValue)
        }
        onDeleteRequested: function(projectId) {
            if (root.workspaceController !== null) root.workspaceController.deleteProject(projectId)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: Theme.AppTheme.spacingSm

        // Compact metrics strip
        ProjectsMetricsSection {
            Layout.fillWidth: true
            metrics: root.overviewModel.metrics || []
        }

        // Inline state feedback (loading spinner / error / success)
        ProjectManagementWidgets.WorkspaceStateBanner {
            Layout.fillWidth: true
            isLoading: root.workspaceController ? root.workspaceController.isLoading : false
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false
            errorMessage: root.workspaceController ? root.workspaceController.errorMessage : ""
            feedbackMessage: root.workspaceController ? root.workspaceController.feedbackMessage : ""
        }

        // Table toolbar: search + status filter + refresh + create
        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search projects…"
            showCreate: true
            createLabel: "New Project"
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            // Status filter in the toolbar filter slot
            ComboBox {
                implicitWidth: 200
                model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                textRole: "label"
                enabled: !tableToolbar.isBusy
                currentIndex: root._statusIndexForValue(
                    root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                )
                onActivated: function(index) {
                    const opt = root.workspaceController
                        ? (root.workspaceController.statusOptions || [])[index]
                        : null
                    if (opt && root.workspaceController) {
                        root.workspaceController.setStatusFilter(String(opt.value || "all"))
                    }
                }
            }

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHost.openCreateDialog()
        }

        // ── Main table area ──────────────────────────────────────────────
        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.DataTable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: root._tableColumns
                rows: root.projectsModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedProjectId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                    dialogHost.openEditDialog(root.selectedProjectModel)
                }
                onSortRequested: function(key) {
                    // Wire to controller sort when backend supports it
                }
            }

            // Detail panel — shown when a project is selected
            ProjectsDetailSection {
                visible: root.selectedProjectModel && root.selectedProjectModel.id !== ""
                Layout.preferredWidth: 320
                Layout.fillHeight: true
                projectDetail: root.selectedProjectModel
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false

                onEditRequested: dialogHost.openEditDialog(root.selectedProjectModel)
                onStatusRequested: dialogHost.openStatusDialog(root.selectedProjectModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedProjectModel)
            }
        }
    }
}
