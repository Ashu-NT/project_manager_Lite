pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var cards: ({ "title": "Rate Cards", "subtitle": "", "emptyState": "", "items": [] })
    property var lines: ({ "title": "Rate Lines", "subtitle": "", "emptyState": "", "items": [] })
    property bool busy: false
    signal linePageRequested(int page)
    implicitHeight: _column.implicitHeight
    ColumnLayout {
        id: _column; width: parent.width; spacing: Theme.AppTheme.spacingLg
        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Rate Cards" }
        FinancialsCollectionBlock { Layout.fillWidth: true; collection: root.cards }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.AppTheme.divider }
        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.lines
            busy: root.busy
            onPageRequested: function(page) { root.linePageRequested(page) }
        }
    }
}
