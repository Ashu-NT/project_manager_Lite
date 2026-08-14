pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property bool isBusy: false
    property string selectedEntryId: ""
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder

    signal entrySelected(string entryId)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal sortRequested(string key, int direction)

    readonly property var _columns: [
        { "key": "title",         "label": "Reference",        "flex": 2, "sortable": true },
        { "key": "subtitle",      "label": "Source / Stage",   "flex": 1.5, "sortable": false },
        { "key": "statusLabel",   "label": "Amount",           "flex": 0, "minWidth": 110, "sortable": true },
        { "key": "supportingText","label": "Task / Resource",  "flex": 1.5, "sortable": false },
        { "key": "metaText",      "label": "Date / Policy",    "flex": 0, "minWidth": 130, "sortable": true }
    ]

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Actuals" }

        AppWidgets.EmptyState {
            width: parent.width
            visible: (root.ledgerModel.items || []).length === 0
            title: root.ledgerModel.emptyState || "No ledger entries"
            message: "No ledger entries are available for the selected project."
        }

        Item {
            width: parent.width
            height: 220
            visible: (root.ledgerModel.items || []).length > 0

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._columns
                sourceModel: root.ledgerTableModel
                sortingMode: "server"
                sortKey: root.sortKey
                sortDirection: root.sortDirection
                loading: root.isBusy
                emptyText: root.ledgerModel.emptyState || "No ledger entries."
                selectedRowId: root.selectedEntryId
                onRowSelected: function(rowId) {
                    root.selectedEntryId = String(rowId || "")
                    root.entrySelected(root.selectedEntryId)
                }
                onSortRequested: function(key, direction) {
                    root.sortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            width: parent.width
            visible: Number(root.ledgerModel.total || 0) > Number(root.ledgerModel.pageSize || 50)
            currentPage: Number(root.ledgerModel.page || 1)
            pageSize: Number(root.ledgerModel.pageSize || 50)
            totalItems: Number(root.ledgerModel.total || 0)
            busy: root.isBusy
            onPageRequested: function(page) { root.pageRequested(page) }
            onPageSizeRequested: function(pageSize) { root.pageSizeRequested(pageSize) }
        }
    }
}
