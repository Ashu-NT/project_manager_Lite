pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var ledgerModel: ({ "items": [] })

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Activity" }

        Item {
            width: parent.width
            implicitHeight: _activityFeed.implicitHeight + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            AppWidgets.ActivityFeed {
                id: _activityFeed
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.margins: Theme.AppTheme.spacingMd
                items: root.ledgerModel.items || []
                emptyText: "No ledger activity recorded for the selected project."
            }
        }
    }
}
