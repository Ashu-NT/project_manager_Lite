pragma ComponentBehavior: Bound
import QtQuick
import App.Widgets 1.0 as AppWidgets


AppWidgets.GroupedNavigationRail {
    id: root

    property var navigationItems: []
    property string selectedWorkspaceKey: ""

    signal workspaceSelected(string workspaceKey)

    items: root.navigationItems
    autoCollapseAtNarrowWidth: true
    groupsCollapsedByDefault: false
    showRailToggle: true
    railTitle: "Project Management"
    activeIndex: {
        const entries = root.navigationItems || []
        for (let i = 0; i < entries.length; i += 1) {
            if (String(entries[i].id || "") === root.selectedWorkspaceKey) {
                return i
            }
        }
        return -1
    }

    onItemActivated: function(index) {
        const entries = root.navigationItems || []
        const entry = entries[index]
        if (entry) {
            root.workspaceSelected(String(entry.id || ""))
        }
    }
}
