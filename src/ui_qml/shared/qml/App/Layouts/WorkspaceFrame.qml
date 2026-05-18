import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    default property alias content: contentSlot.data
    property string title: ""
    property string subtitle: ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Theme.AppTheme.marginLg
        spacing: Theme.AppTheme.spacingMd

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
