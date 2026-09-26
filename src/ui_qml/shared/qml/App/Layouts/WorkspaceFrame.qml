import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Widgets 1.0 as AppWidgets

Item {
    id: root

    default property alias content: contentSlot.data
    property string title: ""
    property string subtitle: ""
    property var breadcrumb: []
    // Hidden when this workspace has pushed its own full-page detail view
    // (e.g. AdminOrganizationDetailPage) -- that view owns its own header
    // (back button, object title, breadcrumb context), so the list page's
    // header would otherwise show redundantly above it.
    property bool showHeader: true

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
            visible: root.showHeader
            title: root.title
            subtitle: root.subtitle
            breadcrumb: root.breadcrumb
        }

        Item {
            id: contentSlot
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
