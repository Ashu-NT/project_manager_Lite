pragma ComponentBehavior: Bound

import QtQuick
import App.Theme 1.0 as Theme

GroupedNavigationRail {
    id: root

    property alias sections: root.items
    property alias activeSectionIndex: root.activeIndex

    signal sectionRequested(int index)

    // Auto-collapses to an icon rail at narrow widths, the same mechanism
    // the global navigation tree already uses (GroupedNavigationRail's own
    // `_effectiveCollapsed`) -- previously this always claimed a fixed
    // `detailRailWidth` regardless of viewport width, which is exactly what
    // starved the content column of room on a narrow Organization Detail
    // panel (nav rail + section rail together left too little width for
    // the Sites toolbar's buttons).
    expandedWidth: Theme.AppTheme.detailRailWidth
    autoCollapseAtNarrowWidth: true
    showRailToggle: false
    collapsed: false

    onItemActivated: function(index) {
        root.sectionRequested(index)
    }

    function expandGroupForSection(sectionIndex) {
        root.expandGroupForItem(sectionIndex)
    }
}
