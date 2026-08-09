pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var versions: ({ "title": "Budget Versions", "subtitle": "", "emptyState": "", "items": [] })
    implicitHeight: _column.implicitHeight
    ColumnLayout {
        id: _column; width: parent.width; spacing: Theme.AppTheme.spacingMd
        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Budget Versions" }
        FinancialsCollectionBlock { Layout.fillWidth: true; collection: root.versions }
    }
}
