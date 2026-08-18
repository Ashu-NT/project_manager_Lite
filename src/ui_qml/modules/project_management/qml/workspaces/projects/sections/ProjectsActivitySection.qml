pragma ComponentBehavior: Bound
import QtQuick
import App.Controls 1.0 as AppControls
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import ProjectManagement.Widgets 1.0 as PMWidgets

Item {
    id: root

    property var sectionErrors: ({})
    property var projectActivityModel: ({
        "title": "Activity", "subtitle": "", "emptyState": "No activity has been recorded for this project yet.", "items": []
    })

    property string _searchQuery: ""

    readonly property var _filteredItems: {
        const query = root._searchQuery.trim().toLowerCase()
        const items = root.projectActivityModel.items || []
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

        AppWidgets.SectionHeading { width: parent.width; label: "Activity" }

        AppWidgets.InlineMessage {
            width: parent.width
            visible: String(root.sectionErrors["activity"] || "").length > 0
            tone: "danger"
            message: String(root.sectionErrors["activity"] || "")
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

            PMWidgets.RecordListCard {
                id: _activityCard
                anchors.top: _searchRow.bottom
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.topMargin: Theme.AppTheme.spacingSm
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingMd
                subtitle: root.projectActivityModel.subtitle || ""
                emptyState: root._searchQuery.trim().length > 0
                    ? "No activity matches \"" + root._searchQuery.trim() + "\"."
                    : (root.projectActivityModel.emptyState || "No activity has been recorded for this project yet.")
                items: root._filteredItems
            }
        }
    }
}
