pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts

// Thin repeater wrapper around ActionCenterRow -- Action Center's own
// empty/error/loading presentation is handled by the page (it needs a
// two-line title+message empty state the row/list components don't own),
// this component only renders the successful-rows case.
Item {
    id: root

    property var items: []

    signal itemActivated(var item)

    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        width: parent.width
        spacing: 0

        Repeater {
            model: root.items

            delegate: ActionCenterRow {
                id: _row
                required property var modelData

                Layout.fillWidth: true
                title: String(_row.modelData.title || "")
                moduleLabel: String(_row.modelData.moduleLabel || "")
                subjectDisplay: String(_row.modelData.subjectDisplay || "")
                actionState: String(_row.modelData.actionState || "")
                statusLabel: String(_row.modelData.statusLabel || "")
                priorityLabel: String(_row.modelData.priorityLabel || "")
                dueLabel: String(_row.modelData.dueLabel || "")
                routeId: String(_row.modelData.routeId || "")
                onActivated: root.itemActivated(_row.modelData)
            }
        }
    }
}
