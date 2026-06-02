pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property var sectionErrors: ({})
    property var projectTasksModel: ({
        "title": "Tasks", "subtitle": "", "emptyState": "Open this section to load project tasks.", "items": []
    })
    property var projectTasksTableModel: null
    property bool isBusy: false

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Tasks" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["tasks"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["tasks"] || "")
        }

        AppWidgets.DataTable {
            width: parent.width
            height: Math.min(400, Math.max(200, implicitHeight))
            columns: [
                { key: "title",          label: "Task",     flex: 2,   sortable: true },
                { key: "statusLabel",    label: "Status",   flex: 0,   minWidth: 110, type: "status" },
                { key: "subtitle",       label: "Progress", flex: 0,   minWidth: 100 },
                { key: "supportingText", label: "Dates",    flex: 1.5, minWidth: 140 }
            ]
            sourceModel: root.projectTasksTableModel
            loading: root.isBusy
            emptyText: root.projectTasksModel.emptyState || "No tasks found for this project."
        }
    }
}
