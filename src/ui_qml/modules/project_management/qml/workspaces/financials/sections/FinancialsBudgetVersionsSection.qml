pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root
    property var versions: ({ "title": "Budget Versions", "emptyState": "", "items": [] })
    property var tableModel: null
    property bool busy: false
    property string selectedBudgetId: ""
    property string sortKey: "revision"
    property int sortDirection: Qt.DescendingOrder
    signal budgetSelected(string budgetId)
    signal pageRequested(int page)
    signal sortRequested(string key, int direction)

    readonly property var _columns: [
        { "key": "title", "label": "Budget version", "flex": 2, "sortable": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 105, "sortable": true },
        { "key": "subtitle", "label": "Lines", "flex": 0, "minWidth": 80, "sortable": false },
        { "key": "supportingText", "label": "Authorized total", "flex": 1.4, "sortable": true },
        { "key": "metaText", "label": "Approval / version", "flex": 1.5, "sortable": true }
    ]

    implicitHeight: _column.implicitHeight
    Column {
        id: _column
        width: parent.width
        spacing: 0
        AppWidgets.SectionHeading { width: parent.width; label: "Budget Versions" }
        AppWidgets.EmptyState {
            width: parent.width
            visible: (root.versions.items || []).length === 0
            title: "No budget versions"
            message: root.versions.emptyState || "No budget version exists for this project."
        }
        Item {
            width: parent.width
            height: 240
            visible: (root.versions.items || []).length > 0
            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.tableModel
                sortingMode: "server"
                sortKey: root.sortKey
                sortDirection: root.sortDirection
                selectedRowId: root.selectedBudgetId
                loading: root.busy
                emptyText: root.versions.emptyState || "No budget versions."
                onRowSelected: function(rowId) { root.budgetSelected(String(rowId || "")) }
                onSortRequested: function(key, direction) { root.sortRequested(key, direction) }
            }
        }
        AppWidgets.TablePaginationBar {
            width: parent.width
            visible: Number(root.versions.total || 0) > Number(root.versions.pageSize || 50)
            currentPage: Number(root.versions.page || 1)
            pageSize: Number(root.versions.pageSize || 50)
            totalItems: Number(root.versions.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.pageRequested(page) }
        }
    }
}
