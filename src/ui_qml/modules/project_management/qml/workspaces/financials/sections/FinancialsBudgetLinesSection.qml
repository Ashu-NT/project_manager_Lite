pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var lines: ({ "title": "Budget Lines", "subtitle": "", "emptyState": "", "items": [] })
    property bool busy: false
    signal pageRequested(int page)
    implicitHeight: _column.implicitHeight
    ColumnLayout {
        id: _column; width: parent.width; spacing: Theme.AppTheme.spacingMd
        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Budget Lines" }
        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.lines
            busy: root.busy
            onPageRequested: function(page) { root.pageRequested(page) }
        }
    }
}
