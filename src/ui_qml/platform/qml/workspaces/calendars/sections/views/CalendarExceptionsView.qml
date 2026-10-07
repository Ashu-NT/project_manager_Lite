pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import Platform.Components 1.0

// Calendar tab's "Exceptions" view: holidays, shutdowns, and other
// date-specific overrides for this calendar.
Item {
    id: root
    implicitHeight: card.implicitHeight

    property var exceptions: []
    property string selectedExceptionId: ""
    property bool canWrite: true

    signal addExceptionRequested()
    signal deleteExceptionRequested()
    signal exceptionSelected(string exceptionId)

    readonly property var _columns: [
        { "key": "exceptionDate", "label": "Date", "flex": 0.9 },
        { "key": "exceptionType", "label": "Type", "flex": 1.0 },
        { "key": "name", "label": "Name", "flex": 1.4 },
        { "key": "impactType", "label": "Impact", "flex": 1.0 },
        { "key": "approvalStatus", "label": "Status", "flex": 0.8 }
    ]

    function _tableHeightForCount(count) {
        const visibleRows = Math.max(1, Math.min(count, 8))
        return Theme.AppTheme.headerHeight + (visibleRows * Theme.AppTheme.normalRowHeight) + Theme.AppTheme.spacingLg
    }

    AppWidgets.SectionCard {
        id: card
        width: parent ? parent.width : root.width
        implicitHeight: column.implicitHeight + Theme.AppTheme.spacingMd * 2
        title: "Exceptions"
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
                    enabled: root.canWrite && root.selectedExceptionId.length > 0
                    onClicked: root.deleteExceptionRequested()
                }
                AppControls.PrimaryButton {
                    text: "Add Exception"
                    enabled: root.canWrite
                    onClicked: root.addExceptionRequested()
                }
            }

            AdminDetailTableSection {
                Layout.fillWidth: true
                sectionLabel: "Exceptions"
                rows: root.exceptions
                columns: root._columns
                selectedRowId: root.selectedExceptionId
                emptyTitle: "No exceptions defined"
                emptyMessage: "Add exceptions for holidays, shutdowns, or other non-standard days."
                tableHeight: root._tableHeightForCount(root.exceptions.length)
                onRowSelected: function(rowId) { root.exceptionSelected(String(rowId || "")) }
                onRowActivated: function(rowId) { root.exceptionSelected(String(rowId || "")) }
            }
        }
    }
}
