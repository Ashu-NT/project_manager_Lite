pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property bool hasResource: false
    property var resourceAssignmentsTableModel: null
    property bool isBusy: false

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Assignments" }

        Item {
            width: parent.width
            implicitHeight: Theme.AppTheme.spacingMd
        }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root.hasResource
            title: "No resource selected"
            message: "Select a resource to view its project and task assignments."
        }

        AppWidgets.DataTable {
            width: parent.width
            height: Math.min(480, Math.max(200, implicitHeight))
            visible: root.hasResource
            columns: [
                { key: "title",       label: "Task",         flex: 2,  sortable: true },
                { key: "subtitle",    label: "Project",      flex: 2 },
                { key: "statusLabel", label: "Allocation",   flex: 0,  minWidth: 100, type: "status" },
                { key: "metaText",    label: "Hours Logged", flex: 1,  minWidth: 100 }
            ]
            sourceModel: root.resourceAssignmentsTableModel
            loading: root.isBusy
            emptyText: root.hasResource
                ? "No task assignments found for this resource."
                : "Select a resource to view assignments."
        }

        Item {
            width: parent.width
            implicitHeight: Theme.AppTheme.spacingMd
        }
    }
}
