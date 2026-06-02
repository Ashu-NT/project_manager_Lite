pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

Item {
    id: root

    property var resourceDetail: ({ "id": "", "title": "" })
    property bool isBusy: false

    readonly property bool _hasResource: String(root.resourceDetail.id || "").length > 0

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: "Calendar" }

        AppWidgets.ContextualActionToolbar {
            width: parent.width
            title: root._hasResource ? root.resourceDetail.title : "Calendar"
            subtitle: root._hasResource ? "Working schedule and availability exceptions" : ""
            busy: root.isBusy
            actions: [
                { id: "set_hours",     label: "Set Working Hours", icon: "time",     enabled: root._hasResource },
                { id: "add_exception", label: "Add Exception",     icon: "add",      enabled: root._hasResource },
                { id: "add_leave",     label: "Add Leave",         icon: "calendar", enabled: root._hasResource }
            ]
            onActionTriggered: function(actionId) {
                // Placeholder — calendar management UI to be implemented
            }
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }

        AppWidgets.InlineMessage {
            width: parent.width
            anchors.leftMargin: Theme.AppTheme.marginMd
            anchors.rightMargin: Theme.AppTheme.marginMd
            visible: root._hasResource
            tone: "info"
            message: "Work calendar configuration — shift schedules, leave periods, and availability exceptions — will be available in an upcoming release."
        }

        AppWidgets.EmptyState {
            width: parent.width
            visible: !root._hasResource
            title: "No resource selected"
            message: "Select a resource to view and configure its work calendar."
        }

        Item { width: parent.width; implicitHeight: Theme.AppTheme.spacingMd }
    }
}
