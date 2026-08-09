pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root
    property var versions: ({ "title": "Planned Cost Snapshots", "subtitle": "", "emptyState": "", "items": [] })
    property var lines: ({ "title": "Planned Cost Lines", "subtitle": "", "emptyState": "", "items": [] })
    implicitHeight: _column.implicitHeight
    ColumnLayout {
        id: _column; width: parent.width; spacing: Theme.AppTheme.spacingLg
        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Planned Costs" }
        FinancialsCollectionBlock { Layout.fillWidth: true; collection: root.versions }
        Rectangle { Layout.fillWidth: true; height: 1; color: Theme.AppTheme.divider }
        FinancialsCollectionBlock { Layout.fillWidth: true; collection: root.lines }
    }
}
