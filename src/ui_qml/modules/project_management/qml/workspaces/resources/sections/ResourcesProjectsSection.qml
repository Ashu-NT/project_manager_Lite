pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Controllers 1.0 as ProjectManagementControllers

Item {
    id: root

    property string resourceId: ""
    property var workspaceController: null
    property ProjectManagementControllers.ProjectManagementWorkspaceCatalog pmCatalog
    property string selectedRowId: ""

    readonly property var _page: root.workspaceController
        ? root.workspaceController.resourceProjects : ({ "items": [] })
    readonly property var _selectedRow: {
        const rows = root._page.items || []
        for (let i = 0; i < rows.length; i += 1) {
            if (String(rows[i].id || "") === root.selectedRowId) return rows[i]
        }
        return null
    }

    function _value(model, index) {
        const item = model[index]
        return item ? String(item.value || "") : "all"
    }

    function _openProject(row) {
        const state = row ? (row.state || {}) : {}
        const projectId = String(state.projectId || "")
        if (!projectId.length || state.canOpenProject !== true || !root.pmCatalog) return
        root.pmCatalog.pmNavigation.openEntity("projects", projectId, "overview")
    }

    implicitHeight: content.implicitHeight

    Component.onCompleted: {
        if (root.workspaceController) root.workspaceController.loadResourceProjects()
    }
    onResourceIdChanged: {
        root.selectedRowId = ""
        if (root.workspaceController && root.resourceId.length)
            root.workspaceController.loadResourceProjects()
    }

    ColumnLayout {
        id: content
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.resourceProjectsSearch : ""
            searchPlaceholder: "Search visible projects..."
            showFilter: false
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.resourceProjectsLoading : false
            onSearchChanged: function(text) {
                if (root.workspaceController) root.workspaceController.setResourceProjectsSearch(text)
            }
            onRefreshRequested: {
                if (root.workspaceController) root.workspaceController.loadResourceProjects()
            }

            AppControls.ComboBox {
                id: activeFilter
                implicitWidth: 128
                model: [
                    { "value": "all", "label": "All staffing" },
                    { "value": "active", "label": "Active" },
                    { "value": "inactive", "label": "Inactive" }
                ]
                textRole: "label"
                onActivated: function(index) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceProjectsActive(root._value(model, index))
                }
            }

            AppControls.ComboBox {
                id: statusFilter
                implicitWidth: 140
                model: [
                    { "value": "all", "label": "All statuses" },
                    { "value": "PLANNED", "label": "Planned" },
                    { "value": "ACTIVE", "label": "Active" },
                    { "value": "ON_HOLD", "label": "On hold" },
                    { "value": "COMPLETED", "label": "Completed" }
                ]
                textRole: "label"
                onActivated: function(index) {
                    if (root.workspaceController)
                        root.workspaceController.setResourceProjectsStatus(root._value(model, index))
                }
            }
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            visible: root._selectedRow !== null
            title: root._selectedRow ? String(root._selectedRow.projectName || "Project") : ""
            subtitle: "Project-owned staffing relationship"
            actions: [{ "id": "open", "label": "Open Project", "icon": "open", "enabled": true }]
            onActionTriggered: function(actionId) {
                if (actionId === "open") root._openProject(root._selectedRow)
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 396

            AppWidgets.DataTable {
                id: projectsTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: pagination.top
                columns: [
                    { "key": "projectName", "label": "Project", "flex": 2.0, "minWidth": 180, "sortable": true },
                    { "key": "projectCode", "label": "Code", "flex": 0, "minWidth": 100, "sortable": true },
                    { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 105, "type": "status", "sortable": true },
                    { "key": "plannedHours", "label": "Planned envelope", "flex": 0, "minWidth": 135, "sortable": true },
                    { "key": "activeLabel", "label": "Staffing", "flex": 0, "minWidth": 90, "type": "status" },
                    { "key": "dateRange", "label": "Project dates", "flex": 1.4, "minWidth": 170 }
                ]
                sourceModel: root.workspaceController ? root.workspaceController.resourceProjectsTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController ? root.workspaceController.resourceProjectsSortKey : "projectName"
                sortDirection: root.workspaceController ? root.workspaceController.resourceProjectsSortDirection : Qt.AscendingOrder
                loading: root.workspaceController ? root.workspaceController.resourceProjectsLoading : false
                selectedRowId: root.selectedRowId
                emptyText: "Resource is not assigned to any visible projects."
                onRowSelected: function(rowId) { root.selectedRowId = rowId }
                onRowActivated: function(rowId) {
                    root.selectedRowId = rowId
                    root._openProject(root._selectedRow)
                }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController) root.workspaceController.setResourceProjectsSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: pagination
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.resourceProjectsPage : 1
                pageSize: root.workspaceController ? root.workspaceController.resourceProjectsPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.resourceProjectsTotal : 0
                busy: root.workspaceController ? root.workspaceController.resourceProjectsLoading : false
                onPageRequested: function(page) { root.workspaceController.setResourceProjectsPage(page) }
                onPageSizeRequested: function(size) { root.workspaceController.setResourceProjectsPageSize(size) }
            }
        }
    }
}
