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
    property bool showHeading: true
    property bool showInlineError: true
    property bool showSearch: true
    property bool clientSideSearch: true
    property string selectedItemId: ""

    property string _searchQuery: ""

    signal itemSelected(string itemId)

    readonly property var _filteredItems: {
        const query = root._searchQuery.trim().toLowerCase()
        const items = root.activityModel.items || []
        if (!root.clientSideSearch || query.length === 0) {
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

        AppWidgets.SectionHeading {
            width: parent.width
            visible: root.showHeading
            height: visible ? implicitHeight : 0
            label: root.label
        }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: root.showInlineError
                && String(root.sectionErrors[root.errorKey] || "").length > 0
            height: visible ? implicitHeight : 0
            tone: "danger"
            message: String(root.sectionErrors[root.errorKey] || "")
        }

        Item {
            width: parent.width
            implicitHeight: _activityCard.implicitHeight
                + (root.showSearch
                    ? _searchRow.implicitHeight + Theme.AppTheme.spacingMd * 2 + Theme.AppTheme.spacingSm
                    : 0)
            height: implicitHeight

            AppControls.SearchField {
                id: _searchRow
                anchors.top: parent.top
                anchors.left: parent.left
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.spacingMd
                implicitWidth: 260
                visible: root.showSearch
                placeholderText: "Search by name..."
                onTextEdited: (text) => { root._searchQuery = text }
            }

            RecordListCard {
                id: _activityCard
                anchors.top: root.showSearch ? _searchRow.bottom : parent.top
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: root.showSearch ? Theme.AppTheme.spacingSm : 0
                anchors.leftMargin: root.showSearch ? Theme.AppTheme.spacingMd : 0
                anchors.rightMargin: root.showSearch ? Theme.AppTheme.spacingMd : 0
                subtitle: root.activityModel.subtitle || ""
                emptyState: root._searchQuery.trim().length > 0
                    ? "No activity matches \"" + root._searchQuery.trim() + "\"."
                    : (root.activityModel.emptyState || "No activity has been recorded yet.")
                items: root._filteredItems
                selectedItemId: root.selectedItemId
                onItemSelected: function(itemId) {
                    root.selectedItemId = itemId
                    root.itemSelected(itemId)
                }
            }
        }
    }
}
