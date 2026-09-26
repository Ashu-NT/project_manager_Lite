pragma ComponentBehavior: Bound

import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

Item {
    id: root
    objectName: "financialsPostingFailuresSection"

    property var failuresModel: ({
        "title": "",
        "subtitle": "",
        "emptyState": "",
        "items": []
    })
    property var failuresTableModel: null
    property bool isBusy: false
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder
    property string statusFilter: ""

    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal sortRequested(string key, int direction)
    signal statusRequested(string status)

    readonly property var _statusOptions: [
        { "value": "", "label": "All failure states" },
        { "value": "retry", "label": "Retry scheduled" },
        { "value": "processing", "label": "Processing" },
        { "value": "quarantined", "label": "Quarantined" },
        { "value": "dead_letter", "label": "Dead letter" }
    ]
    readonly property var _columns: [
        { "key": "title", "label": "Source", "flex": 1.4, "sortable": true },
        { "key": "statusLabel", "label": "State", "flex": 0, "minWidth": 120, "sortable": true },
        { "key": "subtitle", "label": "Failure", "flex": 2.4, "sortable": true },
        { "key": "supportingText", "label": "Recovery", "flex": 2.6, "sortable": false },
        { "key": "metaText", "label": "Work date", "flex": 0, "minWidth": 120, "sortable": true }
    ]

    function _statusIndex() {
        for (let index = 0; index < root._statusOptions.length; ++index) {
            if (String(root._statusOptions[index].value) === root.statusFilter)
                return index
        }
        return 0
    }

    implicitHeight: contentColumn.implicitHeight

    Column {
        id: contentColumn
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading {
            width: parent.width
            label: "Approved Time Posting Failures"
        }

        AppWidgets.TableToolbar {
            objectName: "financialsPostingFailuresToolbar"
            width: parent.width
            showSearch: false
            showFilter: false
            showRefresh: false
            isBusy: root.isBusy

            AppControls.ComboBox {
                id: statusCombo
                objectName: "financialsPostingFailureStatusFilter"
                implicitWidth: 180
                textRole: "label"
                model: root._statusOptions
                currentIndex: root._statusIndex()
                onActivated: {
                    const option = root._statusOptions[currentIndex]
                    root.statusRequested(option ? String(option.value) : "")
                }
            }
        }

        AppWidgets.EmptyState {
            width: parent.width
            visible: (root.failuresModel.items || []).length === 0
            title: root.failuresModel.emptyState || "No posting failures"
            message: "Approved-time labor postings for this project are healthy."
        }

        Item {
            width: parent.width
            height: 280
            visible: (root.failuresModel.items || []).length > 0

            AppWidgets.DataTable {
                objectName: "financialsPostingFailuresTable"
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.failuresTableModel
                sortingMode: "server"
                sortKey: root.sortKey
                sortDirection: root.sortDirection
                loading: root.isBusy
                emptyText: root.failuresModel.emptyState || "No posting failures."
                onSortRequested: function(key, direction) {
                    root.sortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            objectName: "financialsPostingFailuresPagination"
            width: parent.width
            visible: Number(root.failuresModel.total || 0)
                > Number(root.failuresModel.pageSize || 50)
            currentPage: Number(root.failuresModel.page || 1)
            pageSize: Number(root.failuresModel.pageSize || 50)
            totalItems: Number(root.failuresModel.total || 0)
            busy: root.isBusy
            onPageRequested: function(page) { root.pageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        }
    }
}
