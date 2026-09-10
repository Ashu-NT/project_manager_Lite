pragma ComponentBehavior: Bound
import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets

Item {
    id: root
    objectName: "financialsActualsSection"

    property var ledgerModel: ({ "title": "", "subtitle": "", "emptyState": "", "items": [] })
    property var ledgerTableModel: null
    property bool isBusy: false
    property string selectedEntryId: ""
    property string sortKey: "metaText"
    property int sortDirection: Qt.DescendingOrder
    property string statusFilter: ""
    property string sourceFilter: ""

    signal entrySelected(string entryId)
    signal pageRequested(int page)
    signal pageSizeRequested(int pageSize)
    signal sortRequested(string key, int direction)
    signal filtersRequested(string status, string source)

    readonly property var _statusOptions: [
        { "value": "", "label": "All statuses" },
        { "value": "draft", "label": "Draft" },
        { "value": "submitted", "label": "Submitted" },
        { "value": "approved", "label": "Approved" },
        { "value": "posted", "label": "Posted" },
        { "value": "reversed", "label": "Reversed" }
    ]
    readonly property var _sourceOptions: [
        { "value": "", "label": "All sources" },
        { "value": "project_management", "label": "Manual Actual" },
        { "value": "platform_time", "label": "Approved Time" },
        { "value": "inventory_procurement", "label": "Procurement Gateway" }
    ]

    function _indexOf(model, value) {
        for (let index = 0; index < model.length; ++index) {
            if (String(model[index].value) === String(value || "")) return index
        }
        return 0
    }

    function _applyFilters() {
        const status = root._statusOptions[statusCombo.currentIndex]
        const source = root._sourceOptions[sourceCombo.currentIndex]
        root.filtersRequested(
            status ? String(status.value) : "",
            source ? String(source.value) : ""
        )
    }

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

        AppWidgets.TableToolbar {
            objectName: "financialsActualsFilterToolbar"
            width: parent.width
            showSearch: false
            showFilter: false
            showRefresh: false
            isBusy: root.isBusy

            AppControls.ComboBox {
                id: statusCombo
                objectName: "financialsActualsStatusFilter"
                implicitWidth: 145
                textRole: "label"
                model: root._statusOptions
                currentIndex: root._indexOf(root._statusOptions, root.statusFilter)
                onActivated: root._applyFilters()
            }

            AppControls.ComboBox {
                id: sourceCombo
                objectName: "financialsActualsSourceFilter"
                implicitWidth: 190
                textRole: "label"
                model: root._sourceOptions
                currentIndex: root._indexOf(root._sourceOptions, root.sourceFilter)
                onActivated: root._applyFilters()
            }
        }

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
                objectName: "financialsActualsTable"
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
            objectName: "financialsActualsPagination"
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
