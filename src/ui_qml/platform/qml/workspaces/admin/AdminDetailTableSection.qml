pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property string sectionLabel: ""
    property string infoMessage: ""
    property bool gateBlocked: false
    property string gateTitle: "Runtime context required"
    property string gateMessage: ""
    property string emptyTitle: "No records yet"
    property string emptyMessage: ""
    property var rows: []
    property var columns: []
    property bool loading: false
    property real tableHeight: Theme.AppTheme.headerHeight + Theme.AppTheme.normalRowHeight + Theme.AppTheme.spacingLg

    signal rowActivated(string rowId)

    readonly property var _rows: root.rows || []
    readonly property bool _showInfo: root.infoMessage.length > 0
    readonly property bool _showGate: root.gateBlocked
    readonly property bool _showEmpty: !root.gateBlocked && root._rows.length === 0
    readonly property bool _showTable: !root.gateBlocked && root._rows.length > 0

    width: parent ? parent.width : 0
    implicitHeight: sectionColumn.implicitHeight

    Column {
        id: sectionColumn
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading {
            width: parent.width
            label: root.sectionLabel
        }

        Item {
            width: parent.width
            implicitHeight: contentColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

            ColumnLayout {
                id: contentColumn
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                spacing: Theme.AppTheme.spacingMd

                AppWidgets.InlineMessage {
                    Layout.fillWidth: true
                    visible: root._showInfo
                    tone: "info"
                    message: root.infoMessage
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._showGate
                    title: root.gateTitle
                    message: root.gateMessage
                }

                AppWidgets.EmptyState {
                    Layout.fillWidth: true
                    visible: root._showEmpty
                    title: root.emptyTitle
                    message: root.emptyMessage
                }

                AppWidgets.DataTable {
                    Layout.fillWidth: true
                    Layout.preferredHeight: root.tableHeight
                    visible: root._showTable
                    rows: root._rows
                    columns: root.columns
                    emptyText: root.emptyMessage
                    loading: root.loading
                    onRowActivated: function(rowId) {
                        root.rowActivated(rowId)
                    }
                }
            }
        }
    }
}
