pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var sectionErrors: ({})
    property var projectTasksModel: ({ "items": [] })
    property var projectTasksTableModel: null
    property var workspaceController: null
    property bool isBusy: false
    property real availableHeight: 0
    readonly property var _items: root.projectTasksModel.items || []
    readonly property int _tableHeight: Math.max(
        120,
        Theme.AppTheme.normalRowHeight
            + Math.max(root._items.length, 1) * Theme.AppTheme.compactRowHeight
            + 1
    )
    implicitHeight: Math.max(content.implicitHeight, root.availableHeight)

    function _value(model, index) { return model[index] ? String(model[index].value) : "all" }
    function _applyFilters() {
        if (root.workspaceController)
            root.workspaceController.setProjectTasksFilters(_value(statusFilter.model, statusFilter.currentIndex),
                                                            _value(scheduleFilter.model, scheduleFilter.currentIndex))
    }

    ColumnLayout {
        id: content
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root.implicitHeight
        spacing: Theme.AppTheme.spacingSm
        AppWidgets.TableToolbar {
            Layout.fillWidth: true
            searchText: String(root.projectTasksModel.searchText || "")
            searchPlaceholder: "Search task name or description..."
            showFilter: false; showRefresh: true; isBusy: root.isBusy
            onSearchChanged: function(text) { if (root.workspaceController) root.workspaceController.setProjectTasksSearch(text) }
            onRefreshRequested: { if (root.workspaceController) root.workspaceController.loadProjectTasks() }
            AppControls.ComboBox {
                id: statusFilter; implicitWidth: 130; textRole: "label"
                model: [{"value":"all","label":"All statuses"},{"value":"TODO","label":"To do"},
                        {"value":"IN_PROGRESS","label":"In progress"},{"value":"BLOCKED","label":"Blocked"},
                        {"value":"DONE","label":"Done"}]
                onActivated: root._applyFilters()
            }
            AppControls.ComboBox {
                id: scheduleFilter; implicitWidth: 135; textRole: "label"
                model: [{"value":"all","label":"All schedules"},{"value":"overdue","label":"Overdue"},
                        {"value":"due_7","label":"Due in 7 days"},{"value":"no_deadline","label":"No deadline"}]
                onActivated: root._applyFilters()
            }
        }
        AppWidgets.InlineMessage {
            Layout.fillWidth: true; visible: String(root.sectionErrors["tasks"] || "").length > 0
            tone: "danger"; message: String(root.sectionErrors["tasks"] || "")
        }
        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root._tableHeight + pagination.implicitHeight
            AppWidgets.DataTable {
                anchors.top: parent.top; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: pagination.top
                columns: [
                    {key:"wbsCode",label:"WBS",minWidth:80,flex:0,sortable:true},
                    {key:"taskName",label:"Task",minWidth:180,flex:2,sortable:true},
                    {key:"statusLabel",label:"Status",minWidth:105,flex:0,type:"status",sortable:true},
                    {key:"progressValue",label:"Progress",minWidth:115,flex:0,type:"progress",sortable:true},
                    {key:"startDate",label:"Start",minWidth:105,flex:0,sortable:true},
                    {key:"endDate",label:"Finish",minWidth:105,flex:0,sortable:true},
                    {key:"duration",label:"Duration",minWidth:85,flex:0},
                    {key:"priority",label:"Priority",minWidth:80,flex:0,sortable:true}
                ]
                sourceModel: root.projectTasksTableModel; sortingMode: "server"
                sortKey: String(root.projectTasksModel.sortKey || "wbsCode")
                sortDirection: root.projectTasksModel.sortDirection === "desc" ? Qt.DescendingOrder : Qt.AscendingOrder
                loading: root.isBusy; emptyText: root.projectTasksModel.emptyState || "No tasks found."
                onSortRequested: function(key, direction) { root.workspaceController.setProjectTasksSort(key, direction) }
            }
            AppWidgets.TablePaginationBar {
                id: pagination; anchors.left: parent.left; anchors.right: parent.right; anchors.bottom: parent.bottom
                currentPage: Number(root.projectTasksModel.page || 1); pageSize: Number(root.projectTasksModel.pageSize || 25)
                totalItems: Number(root.projectTasksModel.total || 0); busy: root.isBusy
                onPageRequested: function(page) { root.workspaceController.setProjectTasksPage(page) }
                onPageSizeRequested: function(size) { root.workspaceController.setProjectTasksPageSize(size) }
            }
        }
    }
}
