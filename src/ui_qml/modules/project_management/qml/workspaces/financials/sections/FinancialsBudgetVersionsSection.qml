pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var versions: ({ "title": "Budget Versions", "emptyState": "", "items": [] })
    property var tableModel: null
    property bool busy: false
    property string selectedBudgetId: ""
    property string sortKey: "revision"
    property int sortDirection: Qt.DescendingOrder
    property bool showCreateVersion: false
    property bool canCreateVersion: false
    property string createVersionDisabledReason: ""
    signal budgetSelected(string budgetId)
    signal pageRequested(int page)
    signal sortRequested(string key, int direction)
    signal createVersionRequested()
    signal editRequested(var budget)
    signal successorRequested(var budget)
    signal lifecycleRequested(string action, var budget)

    readonly property var selectedBudget: {
        const items = root.versions.items || []
        for (let index = 0; index < items.length; index += 1) {
            if (String(items[index].id || "") === root.selectedBudgetId) return items[index]
        }
        return null
    }
    readonly property var selectedState: root.selectedBudget
        ? (root.selectedBudget.state || {}) : ({})

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
        Flow {
            width: parent.width
            topPadding: Theme.AppTheme.spacingSm
            bottomPadding: Theme.AppTheme.spacingSm
            leftPadding: Theme.AppTheme.spacingMd
            rightPadding: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingSm

            AppControls.SecondaryButton {
                visible: root.showCreateVersion && !Boolean(root.selectedState.canCreateSuccessor)
                enabled: root.canCreateVersion && !root.busy
                text: "Create Version"
                iconName: "add"
                onClicked: root.createVersionRequested()
            }
            AppWidgets.InfoTip {
                visible: root.showCreateVersion
                    && !root.canCreateVersion
                    && !Boolean(root.selectedState.canCreateSuccessor)
                message: root.createVersionDisabledReason
                    || "Complete the open budget workflow before creating another version."
                title: "Create Version unavailable"
                accessibleLabel: "Why Create Version is unavailable"
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canCreateSuccessor)
                text: "Create Successor"
                iconName: "add"
                onClicked: root.successorRequested(root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canEdit)
                text: "Edit"
                iconName: "edit"
                onClicked: root.editRequested(root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canSubmit)
                text: "Submit"
                iconName: "approve"
                onClicked: root.lifecycleRequested("submit", root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canRequestApproval)
                text: "Request Approval"
                iconName: "approve"
                onClicked: root.lifecycleRequested("request_approval", root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canApprove)
                text: "Approve"
                iconName: "approve"
                onClicked: root.lifecycleRequested("approve", root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canReject)
                text: "Reject"
                iconName: "reject"
                danger: true
                onClicked: root.lifecycleRequested("reject", root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canClose)
                text: "Close"
                iconName: "close"
                onClicked: root.lifecycleRequested("close", root.selectedBudget)
            }
            AppControls.SecondaryButton {
                visible: Boolean(root.selectedState.canDelete)
                text: "Delete Draft"
                iconName: "delete"
                danger: true
                onClicked: root.lifecycleRequested("delete_budget", root.selectedBudget)
            }
        }
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
