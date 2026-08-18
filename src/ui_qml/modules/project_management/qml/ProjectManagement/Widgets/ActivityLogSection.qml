pragma ComponentBehavior: Bound
import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme

// Shared "Activity" detail-section design: a section heading, an optional
// error banner, a client-side name search, and a RecordListCard feed of
// audit-log entries (create/update/delete with an actor name, a status
// chip classified from the action word, and a diff-summary supporting
// line). Originally built for Projects; any PM workspace section backed
// by `presenters/common/activity_log_builder.py` can reuse this directly
// instead of re-deriving the search/list/empty-state wiring per workspace.
Item {
    id: root

    property string label: "Activity"
    property var sectionErrors: ({})
    property string errorKey: "activity"
    property var activityModel: ({
        "title": "Activity", "subtitle": "", "emptyState": "No activity has been recorded yet.", "items": []
    })

    property string _searchQuery: ""

    readonly property var _filteredItems: {
        const query = root._searchQuery.trim().toLowerCase()
        const items = root.activityModel.items || []
        if (query.length === 0) {
            return items
        }
        return items.filter(function (item) {
            return String(item.title || "").toLowerCase().includes(query)
        })
    }

    implicitHeight: _col.implicitHeight

    Column {
        id: _col
        width: parent.width
        spacing: 0

        AppWidgets.SectionHeading { width: parent.width; label: root.label }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors[root.errorKey] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors[root.errorKey] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _searchRow.implicitHeight + _activityCard.implicitHeight + Theme.AppTheme.spacingMd * 2 + Theme.AppTheme.spacingSm
            height: implicitHeight

            AppControls.SearchField {
                id: _searchRow
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                implicitWidth: 260
                placeholderText: "Search by name..."
                onTextEdited: (text) => { root._searchQuery = text }
            }

            RecordListCard {
                id: _activityCard
                anchors.top: _searchRow.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingSm
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                subtitle: root.activityModel.subtitle || ""
                emptyState: root._searchQuery.trim().length > 0
                    ? "No activity matches \"" + root._searchQuery.trim() + "\"."
                    : (root.activityModel.emptyState || "No activity has been recorded yet.")
                items: root._filteredItems
            }
        }
    }
}
