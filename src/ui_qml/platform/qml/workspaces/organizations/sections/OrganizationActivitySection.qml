pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Organization Detail's Activity tab: this organization's own history
// only -- distinct from the tenant-wide Platform audit trail (Platform >
// Control > Audit). Same underlying entries as Overview's Recent Activity
// preview, shown here in full.
Column {
    id: root
    spacing: 0

    property var items: []

    Item {
        width: root.width
        implicitHeight: auditColumn.implicitHeight + Theme.AppTheme.spacingMd * 2

        ColumnLayout {
            id: auditColumn
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.margins: Theme.AppTheme.spacingMd
            spacing: Theme.AppTheme.spacingMd

            AppWidgets.ActivityFeed {
                Layout.fillWidth: true
                items: root.items
                emptyText: "No activity recorded for this organization yet."
            }
        }
    }
}
