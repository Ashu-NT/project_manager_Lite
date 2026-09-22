pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

// Placeholder shape shared by Employees and Documents until each gets its
// own tenant-scoped, paginated tab (the same upgrade already done for
// Sites and Departments) -- a client-side filter of the existing
// session-active-organization-only catalog. Delete this file once both
// entities have their own real sections.
Column {
    id: root
    spacing: 0

    property var rows: []
    property var columns: []
    property string emptyText: ""

    AppWidgets.DataTable {
        width: root.width
        height: 320
        columns: root.columns
        rows: root.rows
        emptyText: root.emptyText
    }
}
