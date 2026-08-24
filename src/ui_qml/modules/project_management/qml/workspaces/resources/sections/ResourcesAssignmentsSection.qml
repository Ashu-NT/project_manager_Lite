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
        ? root.workspaceController.resourceAssignments : ({ "items": [] })
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

    function _applyFilters() {
        if (!root.workspaceController) return
        root.workspaceController.setResourceAssignmentsFilters(
            root._value(lifecycleFilter.model, lifecycleFilter.currentIndex),
            root._value(taskStatusFilter.model, taskStatusFilter.currentIndex),
            root._value(responseFilter.model, responseFilter.currentIndex)
        )
    }

    function _openTask(row) {
        const state = row ? (row.state || {}) : {}
        const taskId = String(state.taskId || "")
        if (!taskId.length || state.canOpenTask !== true || !root.pmCatalog) return
        root.pmCatalog.pmNavigation.openEntity("tasks", taskId, "details")
    }

    implicitHeight: content.implicitHeight

    Component.onCompleted: {
        if (root.workspaceController) root.workspaceController.loadResourceAssignments()
    }
    onResourceIdChanged: {
        root.selectedRowId = ""
        if (root.workspaceController && root.resourceId.length)
            root.workspaceController.loadResourceAssignments()
    }

    ColumnLayout {
        id: content
        width: parent.width
        spacing: Theme.AppTheme.spacingSm

        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: root.workspaceController ? root.workspaceController.resourceAssignmentsSearch : ""
            searchPlaceholder: "Search visible tasks or projects..."
            showFilter: false
            showRefresh: true
            isBusy: root.workspaceController ? root.workspaceController.resourceAssignmentsLoading : false
            onSearchChanged: function(text) {
                if (root.workspaceController) root.workspaceController.setResourceAssignmentsSearch(text)
            }
            onRefreshRequested: {
                if (root.workspaceController) root.workspaceController.loadResourceAssignments()
            }

            AppControls.ComboBox {
                id: lifecycleFilter
                implicitWidth: 132
                model: [
                    { "value": "current", "label": "Current work" },
                    { "value": "history", "label": "History" },
                    { "value": "all", "label": "All work" }
                ]
                textRole: "label"
                onActivated: root._applyFilters()
            }
            AppControls.ComboBox {
                id: taskStatusFilter
                implicitWidth: 128
                model: [
                    { "value": "all", "label": "All tasks" },
                    { "value": "TODO", "label": "To do" },
                    { "value": "IN_PROGRESS", "label": "In progress" },
                    { "value": "BLOCKED", "label": "Blocked" },
                    { "value": "DONE", "label": "Done" }
                ]
                textRole: "label"
                onActivated: root._applyFilters()
            }
            AppControls.ComboBox {
                id: responseFilter
                implicitWidth: 128
                model: [
                    { "value": "all", "label": "All responses" },
                    { "value": "pending", "label": "Pending" },
                    { "value": "accepted", "label": "Accepted" },
                    { "value": "declined", "label": "Declined" }
                ]
                textRole: "label"
                onActivated: root._applyFilters()
            }
        }

        Flow {
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingSm

            AppControls.DateField { id: fromDate; width: 180; placeholderText: "From date" }
            AppControls.DateField { id: toDate; width: 180; placeholderText: "To date" }
            AppControls.SecondaryButton {
                text: "Apply range"
                iconName: "calendar"
                onClicked: {
                    if (root.workspaceController)
                        root.workspaceController.setResourceAssignmentsDateRange(fromDate.text, toDate.text)
                }
            }
        }

        AppWidgets.ContextualActionToolbar {
            Layout.fillWidth: true
            Layout.preferredHeight: visible ? implicitHeight : 0
            visible: root._selectedRow !== null
            title: root._selectedRow ? String(root._selectedRow.taskName || "Task") : ""
            subtitle: "Task-owned assignment | Read only"
            actions: [{ "id": "open", "label": "Open Task", "icon": "open", "enabled": true }]
            onActionTriggered: function(actionId) {
                if (actionId === "open") root._openTask(root._selectedRow)
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 416

            AppWidgets.DataTable {
                id: assignmentsTable
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: pagination.top
                columns: [
                    { "key": "taskName", "label": "Task", "flex": 2.0, "minWidth": 180, "sortable": true },
                    { "key": "projectName", "label": "Project", "flex": 1.5, "minWidth": 150, "sortable": true },
                    { "key": "scheduledStart", "label": "Schedule", "flex": 1.4, "minWidth": 180, "sortable": true },
                    { "key": "plannedHours", "label": "Planned", "flex": 0, "minWidth": 90, "sortable": true },
                    { "key": "allocationPercent", "label": "Allocation", "flex": 0, "minWidth": 95, "sortable": true },
                    { "key": "actualHours", "label": "Actual", "flex": 0, "minWidth": 90, "sortable": true },
                    { "key": "statusLabel", "label": "Task status", "flex": 0, "minWidth": 105, "type": "status", "sortable": true },
                    { "key": "responseStatus", "label": "Response", "flex": 0, "minWidth": 100, "type": "status" }
                ]
                sourceModel: root.workspaceController ? root.workspaceController.resourceAssignmentsTableModel : null
                sortingMode: "server"
                sortKey: root.workspaceController ? root.workspaceController.resourceAssignmentsSortKey : "scheduledStart"
                sortDirection: root.workspaceController ? root.workspaceController.resourceAssignmentsSortDirection : Qt.AscendingOrder
                loading: root.workspaceController ? root.workspaceController.resourceAssignmentsLoading : false
                selectedRowId: root.selectedRowId
                emptyText: "No assignments match this Resource and the selected filters."
                onRowSelected: function(rowId) { root.selectedRowId = rowId }
                onRowActivated: function(rowId) {
                    root.selectedRowId = rowId
                    root._openTask(root._selectedRow)
                }
                onSortRequested: function(key, direction) {
                    if (root.workspaceController) root.workspaceController.setResourceAssignmentsSort(key, direction)
                }
            }

            AppWidgets.TablePaginationBar {
                id: pagination
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                currentPage: root.workspaceController ? root.workspaceController.resourceAssignmentsPage : 1
                pageSize: root.workspaceController ? root.workspaceController.resourceAssignmentsPageSize : 25
                totalItems: root.workspaceController ? root.workspaceController.resourceAssignmentsTotal : 0
                busy: root.workspaceController ? root.workspaceController.resourceAssignmentsLoading : false
                onPageRequested: function(page) { root.workspaceController.setResourceAssignmentsPage(page) }
                onPageSizeRequested: function(size) { root.workspaceController.setResourceAssignmentsPageSize(size) }
            }
        }
    }
}
