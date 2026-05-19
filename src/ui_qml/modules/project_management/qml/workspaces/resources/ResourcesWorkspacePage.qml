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
    property ProjectManagementControllers.ProjectManagementResourcesWorkspaceController workspaceController: root.pmCatalog
        ? root.pmCatalog.resourcesWorkspace
        : null
    readonly property var workspaceModel: root.workspaceController
        ? root.workspaceController.workspace
        : ({
            "routeId": "project_management.resources",
            "title": "Resources",
            "summary": "Resource capacity, allocation, project assignments, and utilization views.",
            "migrationStatus": "QML landing zone ready",
            "legacyRuntimeStatus": "Existing QWidget resources workspace remains active"
        })
    readonly property var overviewModel: root.workspaceController
        ? root.workspaceController.overview
        : ({
            "title": root.workspaceModel.title,
            "subtitle": root.workspaceModel.summary,
            "metrics": []
        })
    readonly property var resourcesModel: root.workspaceController
        ? root.workspaceController.resources
        : ({
            "title": "Resource Pool",
            "subtitle": "Manage capacity, worker types, and resource availability.",
            "emptyState": "Project-management resources desktop API is not connected in this QML preview.",
            "items": []
        })
    readonly property var selectedResourceModel: root.workspaceController
        ? root.workspaceController.selectedResource
        : ({
            "id": "",
            "title": "",
            "statusLabel": "",
            "subtitle": "",
            "description": "",
            "emptyState": "Select a resource from the pool to review details or edit its setup.",
            "fields": [],
            "state": {}
        })

    title: root.overviewModel.title || root.workspaceModel.title
    subtitle: root.overviewModel.subtitle || root.workspaceModel.summary

    readonly property var _tableColumns: [
        { "key": "title",            "label": "Resource",  "flex": 2,   "sortable": true  },
        { "key": "statusLabel",      "label": "Status",    "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "role",             "label": "Role",      "flex": 1.5, "sortable": true  },
        { "key": "workerTypeLabel",  "label": "Type",      "flex": 1                       },
        { "key": "costTypeLabel",    "label": "Category",  "flex": 1,   "sortable": true  },
        { "key": "utilizationValue", "label": "Capacity",  "flex": 0,   "minWidth": 110, "type": "progress" }
    ]

    function _categoryIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        for (let i = 0; i < opts.length; i++) {
            if (String(opts[i].value || "") === String(v || "")) return i
        }
        return 0
    }

    ResourcesDialogHost {
        id: dialogHost

        workerTypeOptions: root.workspaceController ? (root.workspaceController.workerTypeOptions || []) : []
        categoryOptions: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        employeeOptions: root.workspaceController ? (root.workspaceController.employeeOptions || []) : []

        onCreateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.createResource(payload)
        }
        onUpdateRequested: function(payload) {
            if (root.workspaceController !== null) root.workspaceController.updateResource(payload)
        }
        onDeleteRequested: function(resourceId) {
            if (root.workspaceController !== null) root.workspaceController.deleteResource(resourceId)
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
                ? "QML CRUD resources slice active"
                : (root.workspaceModel.migrationStatus || "")
            legacyRuntimeStatus: root.workspaceModel.legacyRuntimeStatus || ""
            architectureStatus: "Desktop API + typed controller"
            architectureSummary: "Resource pool filters, employee-linked worker setup, create, edit, active toggle, and delete flows now run through a typed PM controller backed by the resources desktop API."
        }

        AppWidgets.TableToolbar {
            id: tableToolbar
            Layout.fillWidth: true
            searchPlaceholder: "Search resources…"
            showCreate: true
            createLabel: "New Resource"
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.isBusy : false

            onSearchChanged: function(text) {
                if (root.workspaceController !== null) root.workspaceController.setSearchText(text)
            }
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
                id: resourcesTable
                anchors.fill: parent
                columns: root._tableColumns
                rows: root.resourcesModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedResourceId : ""
                showFilter: true

                onFilterClicked: filterPopup.open()
                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                }
                onViewDetailRequested: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                    detailPage.open = true
                }
                onSortRequested: function(key) {}
            }

            Popup {
                id: filterPopup
                parent: resourcesTable
                width: 260
                padding: 12
                x: resourcesTable.width - width - 4
                y: 30
                closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

                Column {
                    width: parent.width
                    spacing: 8

                    Label {
                        text: "Active Status"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: [
                            { "label": "All",      "value": "all"      },
                            { "label": "Active",   "value": "active"   },
                            { "label": "Inactive", "value": "inactive" }
                        ]
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: {
                            const v = root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                            return v === "active" ? 1 : v === "inactive" ? 2 : 0
                        }
                        onActivated: function(index) {
                            const vals = ["all", "active", "inactive"]
                            if (root.workspaceController !== null)
                                root.workspaceController.setActiveFilter(vals[index] || "all")
                        }
                    }

                    Label {
                        text: "Category"
                        font.bold: true
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.family: Theme.AppTheme.fontFamily
                        color: Theme.AppTheme.textMuted
                    }
                    ComboBox {
                        width: parent.width
                        model: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                        textRole: "label"
                        enabled: !(root.workspaceController ? root.workspaceController.isBusy : false)
                        currentIndex: root._categoryIndexForValue(
                            root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                        )
                        onActivated: function(index) {
                            const opt = root.workspaceController
                                ? (root.workspaceController.categoryOptions || [])[index]
                                : null
                            if (opt && root.workspaceController)
                                root.workspaceController.setCategoryFilter(String(opt.value || "all"))
                        }
                    }
                }
            }

            AppWidgets.SectionDetailPage {
                id: detailPage
                anchors.fill: parent
                title: root.selectedResourceModel.title || "Resource Details"
                open: false
                isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                sections: ["Profile", "Assignments", "Capacity"]

                onBackRequested: detailPage.open = false
                onEditRequested: dialogHost.openEditDialog(root.selectedResourceModel)
                onDeleteRequested: dialogHost.openDeleteDialog(root.selectedResourceModel)

                ResourcesDetailSection {
                    width: parent.width
                    detailPage: detailPage
                    resourceDetail: root.selectedResourceModel
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onEditRequested: dialogHost.openEditDialog(root.selectedResourceModel)
                    onToggleRequested: {
                        const state = root.selectedResourceModel && root.selectedResourceModel.state
                            ? root.selectedResourceModel.state : {}
                        if (root.workspaceController !== null && state.resourceId) {
                            root.workspaceController.toggleResourceActive(
                                String(state.resourceId || ""),
                                parseInt(String(state.version || "0"), 10)
                            )
                        }
                    }
                    onDeleteRequested: dialogHost.openDeleteDialog(root.selectedResourceModel)
                }
            }
        }
    }
}
