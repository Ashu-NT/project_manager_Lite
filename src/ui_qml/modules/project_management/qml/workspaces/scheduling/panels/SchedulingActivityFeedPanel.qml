pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Widgets 1.0 as AppWidgets
import App.Theme 1.0 as Theme
import "../components"

Item {
    id: root

    property var workspaceController: null
    property var activityFeedModel: ({ "items": [], "emptyState": "" })
    property string feedSearchText: ""

    signal feedSearchTextChanged(string text)

    SchedulingPanelFrame {
        anchors.fill: parent
        title: "Activity Feed"
        subtitle: "Recent planning actions, delay notices, recalculation events, and resource warnings."

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.margins: Theme.AppTheme.marginMd
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                width: parent.width
                spacing: Theme.AppTheme.spacingSm

                SchedulingActionBar {
                    Layout.fillWidth: true
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    actions: [
                        { "id": "refresh", "label": "Refresh", "icon": "refresh", "enabled": true }
                    ]
                    onActionTriggered: function(actionId) {
                        if (actionId === "refresh" && root.workspaceController !== null)
                            root.workspaceController.refresh()
                    }
                }

                AppWidgets.TableToolbar {
                    Layout.fillWidth: true
                    searchText: root.feedSearchText
                    searchPlaceholder: "Search activity..."
                    showRefresh: false
                    showExport: false
                    isBusy: root.workspaceController ? root.workspaceController.isBusy : false
                    onSearchChanged: function(text) { root.feedSearchTextChanged(text) }
                }

                AppWidgets.ActivityFeed {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 700
                    items: {
                        const sourceItems = root.activityFeedModel.items || []
                        const term = String(root.feedSearchText || "").trim().toLowerCase()
                        if (!term.length) return sourceItems
                        const filtered = []
                        for (let i = 0; i < sourceItems.length; i += 1) {
                            const item = sourceItems[i]
                            const haystack = (
                                String(item.title || "") + " " +
                                String(item.metaText || "") + " " +
                                String(item.statusLabel || "")
                            ).toLowerCase()
                            if (haystack.indexOf(term) >= 0) filtered.push(item)
                        }
                        return filtered
                    }
                    emptyText: root.activityFeedModel.emptyState || "No planning activity has been recorded."
                }

                Item { Layout.preferredHeight: Theme.AppTheme.marginMd }
            }
        }
    }
}
