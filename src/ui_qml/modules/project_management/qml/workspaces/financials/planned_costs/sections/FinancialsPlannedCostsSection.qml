pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var versions: ({ "title": "Planned Cost Snapshots", "emptyState": "", "items": [] })
    property var lines: ({ "title": "Planned Cost Lines", "emptyState": "", "items": [] })
    property var versionsTableModel: null
    property var linesTableModel: null
    property bool busy: false
    property string selectedVersionId: ""
    property string versionSortKey: "revision"
    property int versionSortDirection: Qt.DescendingOrder
    property string lineSortKey: "title"
    property int lineSortDirection: Qt.AscendingOrder

    signal versionSelected(string versionId)
    signal versionPageRequested(int page)
    signal linePageRequested(int page)
    signal versionSortRequested(string key, int direction)
    signal lineSortRequested(string key, int direction)

    readonly property var _versionColumns: [
        { "key": "title", "label": "Snapshot", "flex": 1.2, "sortable": true },
        { "key": "statusLabel", "label": "Status", "flex": 0, "minWidth": 105, "sortable": true },
        { "key": "subtitle", "label": "As of / lines", "flex": 1.3, "sortable": true },
        { "key": "supportingText", "label": "Total / hours", "flex": 1.4, "sortable": true },
        { "key": "metaText", "label": "Calculated", "flex": 1.7, "sortable": true }
    ]
    readonly property var _lineColumns: [
        { "key": "title", "label": "Task", "flex": 1.5, "sortable": true },
        { "key": "subtitle", "label": "WBS / resource", "flex": 1.5, "sortable": true },
        { "key": "supportingText", "label": "Hours x rate = amount", "flex": 2, "sortable": true },
        { "key": "statusLabel", "label": "Snapshot status", "flex": 0, "minWidth": 120, "sortable": true },
        { "key": "metaText", "label": "Cost / rate source", "flex": 1.7, "sortable": true }
    ]

    implicitHeight: contentColumn.implicitHeight

    ColumnLayout {
        id: contentColumn
        width: parent.width
        spacing: Theme.AppTheme.spacingLg

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Planned Cost Snapshots"
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: (root.versions.items || []).length === 0
            title: "No planned-cost snapshots"
            message: root.versions.emptyState || "No planned-cost snapshot has been calculated."
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 240
            visible: (root.versions.items || []).length > 0

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._versionColumns
                sourceModel: root.versionsTableModel
                sortingMode: "server"
                sortKey: root.versionSortKey
                sortDirection: root.versionSortDirection
                selectedRowId: root.selectedVersionId
                loading: root.busy
                emptyText: root.versions.emptyState || "No planned-cost snapshots."
                onRowSelected: function(rowId) {
                    root.versionSelected(String(rowId || ""))
                }
                onSortRequested: function(key, direction) {
                    root.versionSortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: Number(root.versions.total || 0) > Number(root.versions.pageSize || 50)
            currentPage: Number(root.versions.page || 1)
            pageSize: Number(root.versions.pageSize || 50)
            totalItems: Number(root.versions.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.versionPageRequested(page) }
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Theme.AppTheme.divider
        }

        AppWidgets.SectionHeading {
            Layout.fillWidth: true
            label: "Selected Snapshot Lines"
        }

        AppWidgets.EmptyState {
            Layout.fillWidth: true
            visible: root.selectedVersionId.length === 0 || (root.lines.items || []).length === 0
            title: root.selectedVersionId.length === 0 ? "Select a snapshot" : "No planned-cost lines"
            message: root.selectedVersionId.length === 0
                ? "Choose a Planned Cost Snapshot above to load its authoritative lines."
                : (root.lines.emptyState || "The selected snapshot has no lines.")
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: 280
            visible: root.selectedVersionId.length > 0 && (root.lines.items || []).length > 0

            AppWidgets.DataTable {
                anchors.fill: parent
                columns: root._lineColumns
                sourceModel: root.linesTableModel
                sortingMode: "server"
                sortKey: root.lineSortKey
                sortDirection: root.lineSortDirection
                loading: root.busy
                emptyText: root.lines.emptyState || "No planned-cost lines."
                onSortRequested: function(key, direction) {
                    root.lineSortRequested(key, direction)
                }
            }
        }

        AppWidgets.TablePaginationBar {
            Layout.fillWidth: true
            visible: root.selectedVersionId.length > 0
                && Number(root.lines.total || 0) > Number(root.lines.pageSize || 50)
            currentPage: Number(root.lines.page || 1)
            pageSize: Number(root.lines.pageSize || 50)
            totalItems: Number(root.lines.total || 0)
            busy: root.busy
            onPageRequested: function(page) { root.linePageRequested(page) }
        }
    }
}
