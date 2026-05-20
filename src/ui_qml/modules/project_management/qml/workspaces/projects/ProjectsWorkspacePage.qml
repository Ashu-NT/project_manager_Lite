import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
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
        { "key": "title",              "label": "Project",  "flex": 2,   "sortable": true  },
        { "key": "statusLabel",        "label": "Status",   "flex": 0,   "minWidth": 110, "type": "status" },
        { "key": "clientName",         "label": "Client",   "flex": 1.5, "sortable": true  },
        { "key": "clientContact",      "label": "Contact",  "flex": 1.5                    },
        { "key": "startDateLabel",     "label": "Start",    "flex": 0,   "minWidth": 90    },
        { "key": "endDateLabel",       "label": "Finish",   "flex": 0,   "minWidth": 90    },
        { "key": "plannedBudgetLabel", "label": "Budget",   "flex": 0,   "minWidth": 100   }
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

        AppWidgets.KpiStrip {
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
            visible: false
            Layout.fillWidth: true
            migrationStatus: root.workspaceController
                ? "QML CRUD projects slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Project list, filters, create, edit, status, and delete flows now run through a typed PM controller backed by the project desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search projects…"
            showCreate: true
            createLabel: "New Project"
            showFilter: true
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
            onFilterClicked: filterPopup.open()
            onRefreshRequested: {
                if (root.workspaceController !== null) root.workspaceController.refresh()
            }
            onCreateRequested: dialogHost.openCreateDialog()
        }

        // ── Full-width table with full-page detail view ───────────────
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true

            AppWidgets.DataTable {
                id: projectsTable
                anchors.fill: parent
                columns: root._tableColumns
                rows: root.projectsModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedProjectId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectProject(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            Popup {
                id: filterPopup
                parent: projectsTable
                width: 260
                padding: 12
                x: projectsTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                background: Rectangle {
                    radius: Theme.AppTheme.radiusMd
                    color: Theme.AppTheme.surfaceRaised
                }

                contentItem: ColumnLayout {
                    spacing: 8

                    Label {
                        text: "Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }

                    ComboBox {
                        Layout.fillWidth: true
                        model: root.workspaceController ? (root.workspaceController.statusOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._statusIndexForValue(
                            root.workspaceController ? root.workspaceController.selectedStatusFilter : "all"
                        )
                        onActivated: function(index) {
                            const opt = root.workspaceController
                                ? (root.workspaceController.statusOptions || [])[index]
                                : null
                            if (opt && root.workspaceController)
                                root.workspaceController.setStatusFilter(String(opt.value || "all"))
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: Theme.AppTheme.spacingSm

                        AppControls.SecondaryButton {
                            text: "Clear"
                            iconName: "close"
                            onClicked: {
                                if (root.workspaceController !== null) {
                                    root.workspaceController.setStatusFilter("all")
                                }
                                filterPopup.close()
                            }
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        AppControls.SecondaryButton {
                            text: "Close"
                            iconName: "close"
                            implicitWidth: 88
                            onClicked: filterPopup.close()
                        }
                    }
                }
            }

            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedProjectModel.title || "Project Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Overview", "Activity", "Settings"]

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHost.openEditDialog(root.selectedProjectModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedProjectModel)

                ProjectsDetailSection {
                    width: parent.width
                    detailPage: detailPage
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
