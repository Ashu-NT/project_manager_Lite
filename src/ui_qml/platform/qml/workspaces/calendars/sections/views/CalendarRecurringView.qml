pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Components 1.0

// Calendar tab's "Recurring" view: recurring meetings, training, and
// maintenance windows that reduce available capacity on a schedule.
Item {
    id: root
    implicitHeight: card.implicitHeight

    property var recurringEvents: []
    property string selectedRecurringEventId: ""
    property bool canWrite: true

    signal addRecurringEventRequested()
    signal deleteRecurringEventRequested()
    signal recurringEventSelected(string eventId)

    readonly property var _columns: [
        { "key": "title", "label": "Title", "flex": 1.4 },
        { "key": "eventType", "label": "Type", "flex": 0.9 },
        { "key": "recurrenceRule", "label": "Recurrence", "flex": 1.6 },
        { "key": "impactType", "label": "Impact", "flex": 0.9 },
        { "key": "isActive", "label": "Active", "flex": 0.6 }
    ]

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    AppWidgets.SectionCard {
        id: card
        width: parent ? parent.width : root.width
        implicitHeight: column.implicitHeight + Theme.AppTheme.spacingMd * 2
        title: "Recurring Rules"
        outlined: true

        ColumnLayout {
            id: column
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.AppTheme.marginMd
            spacing: Theme.AppTheme.spacingSm

            RowLayout {
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignRight
                spacing: Theme.AppTheme.spacingSm

                AppControls.SecondaryButton {
                    text: "Delete"
                    danger: true
                    enabled: root.canWrite && root.selectedRecurringEventId.length > 0
                    onClicked: root.deleteRecurringEventRequested()
                }
                AppControls.PrimaryButton {
                    text: "Add Recurring Rule"
                    enabled: root.canWrite
                    onClicked: root.addRecurringEventRequested()
                }
            }

            AdminDetailTableSection {
                Layout.fillWidth: true
                sectionLabel: "Recurring Rules"
                rows: root.recurringEvents
                columns: root._columns
                selectedRowId: root.selectedRecurringEventId
                emptyTitle: "No recurring rules"
                emptyMessage: "Add recurring events that regularly reduce available working capacity."
                tableHeight: root._tableHeightForCount(root.recurringEvents.length)
                onRowSelected: function(rowId) { root.recurringEventSelected(String(rowId || "")) }
                onRowActivated: function(rowId) { root.recurringEventSelected(String(rowId || "")) }
            }
        }
    }
}
