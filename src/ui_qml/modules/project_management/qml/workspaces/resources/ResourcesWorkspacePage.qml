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
        { "key": "title",          "label": "Resource",      "flex": 2,   "sortable": true  },
        { "key": "statusLabel",    "label": "Status",        "flex": 0,   "minWidth": 100, "type": "status" },
        { "key": "subtitle",       "label": "Category",      "flex": 1.5, "sortable": true  },
        { "key": "supportingText", "label": "Role / Type",   "flex": 2                      },
        { "key": "metaText",       "label": "Capacity",      "flex": 1,   "minWidth": 90    }
    ]

    function _activeIndexForValue(v) {
        const opts = root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
        // active filter uses a separate simple list; fall back to 0
        return 0
    }

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

        ResourcesMetricsSection {
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

            // Active filter
            ComboBox {
                implicitWidth: 150
                model: [
                    { "label": "All",      "value": "all"    },
                    { "label": "Active",   "value": "active" },
                    { "label": "Inactive", "value": "inactive" }
                ]
                textRole: "label"
                enabled: !tableToolbar.isBusy
                currentIndex: {
                    const v = root.workspaceController ? root.workspaceController.selectedActiveFilter : "all"
                    return v === "active" ? 1 : v === "inactive" ? 2 : 0
                }
                onActivated: function(index) {
                    const vals = ["all", "active", "inactive"]
                    if (root.workspaceController !== null) root.workspaceController.setActiveFilter(vals[index] || "all")
                }
            }

            // Category filter
            ComboBox {
                implicitWidth: 180
                model: root.workspaceController ? (root.workspaceController.categoryOptions || []) : []
                textRole: "label"
                enabled: !tableToolbar.isBusy
                currentIndex: root._categoryIndexForValue(
                    root.workspaceController ? root.workspaceController.selectedCategoryFilter : "all"
                )
                onActivated: function(index) {
                    const opt = root.workspaceController
                        ? (root.workspaceController.categoryOptions || [])[index]
                        : null
                    if (opt && root.workspaceController) {
                        root.workspaceController.setCategoryFilter(String(opt.value || "all"))
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

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.DataTable {
                Layout.fillWidth: true
                Layout.fillHeight: true
                columns: root._tableColumns
                rows: root.resourcesModel.items || []
                selectedRowId: root.workspaceController ? root.workspaceController.selectedResourceId : ""

                onRowSelected: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                }
                onRowActivated: function(rowId) {
                    if (root.workspaceController !== null) root.workspaceController.selectResource(rowId)
                    dialogHost.openEditDialog(root.selectedResourceModel)
                }
                onSortRequested: function(key) {}
            }

            ResourcesDetailSection {
                visible: root.selectedResourceModel && root.selectedResourceModel.id !== ""
                Layout.preferredWidth: 320
                Layout.fillHeight: true
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
