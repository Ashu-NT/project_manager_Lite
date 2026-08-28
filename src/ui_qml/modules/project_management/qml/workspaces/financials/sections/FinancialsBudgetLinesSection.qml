pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root
    property var lines: ({ "title": "Budget Lines", "emptyState": "", "items": [] })
    property var tableModel: null
    property bool busy: false
    property string selectedBudgetId: ""
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder
    signal pageRequested(int page)
    signal sortRequested(string key, int direction)

    readonly property var _columns: [
        { "key": "title", "label": "Description", "flex": 2, "sortable": true },
        { "key": "subtitle", "label": "Cost code", "flex": 1.4, "sortable": true },
        { "key": "supportingText", "label": "Task / amount", "flex": 1.6, "sortable": true },
        { "key": "statusLabel", "label": "Budget status", "flex": 0, "minWidth": 110, "sortable": false },
        { "key": "metaText", "label": "Revision", "flex": 1.2, "sortable": true }
    ]

    implicitHeight: _column.implicitHeight
    Column {
        id: _column
        width: parent.width
        spacing: 0
        AppWidgets.SectionHeading { width: parent.width; label: "Selected Budget Lines" }
        AppWidgets.EmptyState {
            width: parent.width
            visible: root.selectedBudgetId.length === 0 || (root.lines.items || []).length === 0
            title: root.selectedBudgetId.length === 0 ? "Select a budget version" : "No budget lines"
            message: root.selectedBudgetId.length === 0
                ? "Choose a Budget Version above to load its authoritative lines."
                : (root.lines.emptyState || "The selected budget has no lines.")
        }
        Item {
            width: parent.width
            height: 260
            visible: root.selectedBudgetId.length > 0 && (root.lines.items || []).length > 0
            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.tableModel
                sortingMode: "server"
                sortKey: root.sortKey
                sortDirection: root.sortDirection
                loading: root.busy
                emptyText: root.lines.emptyState || "No budget lines."
                onSortRequested: function(key, direction) { root.sortRequested(key, direction) }
            }
        }
        AppWidgets.TablePaginationBar {
            width: parent.width
            visible: root.selectedBudgetId.length > 0
                && Number(root.lines.total || 0) > Number(root.lines.pageSize || 50)
            currentPage: Number(root.lines.page || 1)
            pageSize: Number(root.lines.pageSize || 50)
            totalItems: Number(root.lines.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.pageRequested(page) }
        }
    }
}
