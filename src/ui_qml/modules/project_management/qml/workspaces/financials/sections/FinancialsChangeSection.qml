pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var changes: ({ "items": [] })
    property var impacts: ({ "items": [] })
    property string selectedChangeId: ""
    signal changeSelected(string changeId)

    implicitHeight: _column.implicitHeight

    ColumnLayout {
        id: _column
        width: parent.width
        spacing: Theme.AppTheme.spacingLg

        AppWidgets.SectionHeading { Layout.fillWidth: true; label: "Change Control" }
        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.changes
            selectable: true
            selectedId: root.selectedChangeId
            onItemSelected: function(itemId) { root.changeSelected(itemId) }
        }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.AppTheme.divider }
        FinancialsCollectionBlock {
            Layout.fillWidth: true
            collection: root.impacts
        }
    }
}
