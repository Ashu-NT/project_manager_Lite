pragma ComponentBehavior: Bound

import QtQuick
import App.Theme 1.0 as Theme

GroupedNavigationRail {
    id: root

    property alias sections: root.items
    property alias activeSectionIndex: root.activeIndex

    signal sectionRequested(int index)

    implicitWidth: Theme.AppTheme.detailRailWidth
    showRailToggle: false
    collapsed: false

    onItemActivated: function(index) {
        root.sectionRequested(index)
    }

    function expandGroupForSection(sectionIndex) {
        root.expandGroupForItem(sectionIndex)
    }
}
