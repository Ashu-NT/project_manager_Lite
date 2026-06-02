pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var projectDetail: ({ "state": {} })
    property var sectionErrors: ({})

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Activity" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["activity"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["activity"] || "")
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
                    const s = root.projectDetail.state || {}
                    return s.activityItems || []
                }
                emptyText: "No project activity recorded"
            }
        }
    }
}
