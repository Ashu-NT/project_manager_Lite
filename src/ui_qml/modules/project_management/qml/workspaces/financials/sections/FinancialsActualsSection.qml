pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property bool isBusy: false
    property string selectedEntryId: ""

    signal entrySelected(string entryId)

    readonly property var _columns: [
        { "key": "title",         "label": "Reference",        "flex": 2 },
        { "key": "subtitle",      "label": "Source / Stage",   "flex": 1.5 },
        { "key": "statusLabel",   "label": "Amount",           "flex": 0, "minWidth": 110 },
        { "key": "supportingText","label": "Task / Resource",  "flex": 1.5 },
        { "key": "metaText",      "label": "Date / Policy",    "flex": 0, "minWidth": 130 }
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
                loading: root.isBusy
                emptyText: root.ledgerModel.emptyState || "No ledger entries."
                selectedRowId: root.selectedEntryId
                onRowSelected: function(rowId) {
                    root.selectedEntryId = String(rowId || "")
                    root.entrySelected(root.selectedEntryId)
                }
            }
        }
    }
}
