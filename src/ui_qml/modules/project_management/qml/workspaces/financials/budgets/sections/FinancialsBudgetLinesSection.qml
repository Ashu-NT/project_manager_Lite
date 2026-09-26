pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var lines: ({ "title": "Budget Lines", "emptyState": "", "items": [] })
    property var tableModel: null
    property bool busy: false
    property string selectedBudgetId: ""
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder
    property var selectedBudget: null
    property string selectedLineId: ""
    signal pageRequested(int page)
    signal sortRequested(string key, int direction)
    signal addRequested(var budget)
    signal editRequested(var budget, var line)
    signal deleteRequested(var budget, var line)

    readonly property var selectedLine: {
        const items = root.lines.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (String(items[index].id || "") === root.selectedLineId) return items[index]
        }
        return null
    }
    readonly property var selectedLineState: root.selectedLine
        ? (root.selectedLine.state || {}) : ({})
    readonly property var selectedBudgetState: root.selectedBudget
        ? (root.selectedBudget.state || {}) : ({})

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
        Flow {
            width: parent.width
            topPadding: Theme.AppTheme.spacingSm
            bottomPadding: Theme.AppTheme.spacingSm
            leftPadding: Theme.AppTheme.spacingMd
            rightPadding: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingSm
            visible: root.selectedBudget !== null

            AppControls.SecondaryButton {
                visible: Boolean(root.selectedBudgetState.canAddLine)
                text: "Add Line"
                iconName: "add"
                onClicked: root.addRequested(root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedLineState.canEdit)
                text: "Edit Line"
                iconName: "edit"
                onClicked: root.editRequested(root.selectedBudget, root.selectedLine)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedLineState.canDelete)
                text: "Delete Line"
                iconName: "delete"
                danger: true
                onClicked: root.deleteRequested(root.selectedBudget, root.selectedLine)
            }
        }
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
                selectedRowId: root.selectedLineId
                emptyText: root.lines.emptyState || "No budget lines."
                onRowSelected: function(rowId) { root.selectedLineId = String(rowId || "") }
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
