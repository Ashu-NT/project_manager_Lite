pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var resourceDetail: ({ "id": "", "title": "", "state": {} })

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: root._hasResource ? root.resourceDetail.title : "Activity"
            subtitle: root._hasResource ? "Change history and audit trail for this resource" : ""
            actions: []
        }

        Item {
            width: parent.width
            implicitHeight: Math.max(_activityFeed.implicitHeight, 80) + Theme.AppTheme.spacingMd * 2
            height: implicitHeight

            AppWidgets.ActivityFeed {
                id: _activityFeed
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                items: {
                    const s = root.resourceDetail.state || {}
                    return s.activityItems || []
                }
                emptyText: "No resource activity recorded"
            }
        }
    }
}
