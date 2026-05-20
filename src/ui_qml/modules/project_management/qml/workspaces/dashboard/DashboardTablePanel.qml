import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    property string emptyText: "No records available."
    property var columns: []
    property var rows: []
    property bool loading: false
    property real tablePreferredHeight: 220

    implicitHeight: panel.implicitHeight

    DashboardPanelFrame {
        id: panel
        anchors.fill: parent
        title: root.title
        subtitle: root.subtitle

        AppWidgets.DataTable {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: root.tablePreferredHeight
            columns: root.columns
            rows: root.rows
            loading: root.loading
            emptyText: root.emptyText
        }
    }
}
