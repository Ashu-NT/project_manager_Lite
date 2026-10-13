pragma ComponentBehavior: Bound

import QtQuick
import App.Widgets 1.0 as AppWidgets

// Renders a ContextNavigationViewModel-shaped tree (the same grouped shape
// used for both the shell's Global Navigation Tree and every module's
// Context Navigation Tree) via the shared GroupedNavigationRail.
//
// groups: [{ id, label, order, expandedByDefault, items: [{ id, label,
//            iconKey, routeId, groupId, order, enabled }] }]
Item {
    id: root

    property var groups: []
    property string activeId: ""
    property bool collapsed: false
    property bool autoCollapseAtNarrowWidth: false
    property string railTitle: ""
    property bool showRailToggle: false

    signal itemActivated(string id, string routeId)

    implicitWidth: _rail.implicitWidth

    readonly property var _flatItems: {
        const sortedGroups = (root.groups || []).slice().sort(function(a, b) {
            return (a.order || 0) - (b.order || 0)
        })
        const flat = []
        for (let g = 0; g < sortedGroups.length; g += 1) {
            const group = sortedGroups[g]
            const groupItems = (group.items || []).slice().sort(function(a, b) {
                return (a.order || 0) - (b.order || 0)
            })
            for (let i = 0; i < groupItems.length; i += 1) {
                const entry = groupItems[i]
                flat.push({
                    "id": entry.id,
                    "label": entry.label,
                    "group": group.label || "",
                    "icon": entry.iconKey || "",
                    "routeId": entry.routeId || entry.id
                })
            }
        }
        return flat
    }

    readonly property int _activeIndex: {
        const items = root._flatItems
        for (let i = 0; i < items.length; i += 1) {
            if (items[i].id === root.activeId) {
                return i
            }
        }
        return -1
    }

    AppWidgets.GroupedNavigationRail {
        id: _rail
        anchors.fill: parent
        items: root._flatItems
        activeIndex: root._activeIndex
        collapsed: root.collapsed
        autoCollapseAtNarrowWidth: root.autoCollapseAtNarrowWidth
        groupsCollapsedByDefault: false
        showRailToggle: root.showRailToggle
        railTitle: root.railTitle

        onItemActivated: function(index) {
            const items = root._flatItems
            if (index < 0 || index >= items.length) {
                return
            }
            root.itemActivated(items[index].id, items[index].routeId)
        }
    }
}
