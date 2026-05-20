import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    default property alias content: contentSlot.data
    property string title: ""
    property string subtitle: ""

    Rectangle {
        anchors.fill: parent
        color: Theme.AppTheme.workspaceBackground
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.pagePadding
        spacing: Theme.AppTheme.sectionGap

        AppWidgets.PageHeader {
            Layout.fillWidth: true
            title: root.title
            subtitle: root.subtitle
        }

        Item {
            id: contentSlot
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
