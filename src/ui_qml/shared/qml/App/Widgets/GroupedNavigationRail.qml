pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    // -- Data ---------------------------------------------------------
    // Flat list of entries. Each entry may be a plain string (label only) or
    // an object: { label, group, count, icon }.
    property var items: []
    property int activeIndex: 0
    property bool groupsCollapsedByDefault: true
    property var _expandedGroups: ({})

    // -- Rail collapse (icon-only strip) -------------------------------
    property bool collapsed: false
    // Opt-in: when true, the rail also collapses itself below a shared
    // window-width breakpoint (R7.3), independent of the manual toggle.
    property bool autoCollapseAtNarrowWidth: false
    readonly property bool _effectiveCollapsed: root.collapsed
        || (root.autoCollapseAtNarrowWidth
            && Window.width > 0
            && Window.width < Theme.AppTheme.narrowLayoutBreakpoint)
    property bool showRailToggle: false
    property string railTitle: ""
    property int expandedWidth: Theme.AppTheme.navRailExpandedWidth
    property int collapsedWidth: Theme.AppTheme.navRailCollapsedWidth

    signal itemActivated(int index)

    color: Theme.AppTheme.surfaceRaised
    implicitWidth: root._effectiveCollapsed ? root.collapsedWidth : root.expandedWidth

    Behavior on implicitWidth {
        NumberAnimation { duration: 180; easing.type: Easing.OutCubic }
    }

    Accessible.role: Accessible.Pane

    // -- Grouping (data-driven, no hardcoded group list) ---------------
    readonly property bool _hasGroups: {
        const entries = root.items || []
        for (let index = 0; index < entries.length; index += 1) {
            if (root._groupLabel(entries[index]).length > 0) {
                return true
            }
        }
        return false
    }

    readonly property var _groups: {
        const entries = root.items || []
        const groups = []
        const groupIndexes = ({})

        for (let index = 0; index < entries.length; index += 1) {
            const entry = entries[index]
            const label = root._groupLabel(entry)
            const key = label.length > 0 ? label : "__ungrouped__"
            let groupIndex = groupIndexes[key]
            if (groupIndex === undefined) {
                groupIndex = groups.length
                groupIndexes[key] = groupIndex
                groups.push({ "key": key, "label": label, "items": [] })
            }
            groups[groupIndex].items.push({ "itemIndex": index, "entry": entry })
        }
        return groups
    }

    function _groupLabel(entry) {
        return typeof entry === "object" && entry !== null
            ? String(entry.group || "").trim()
            : ""
    }

    function _itemLabel(entry) {
        return typeof entry === "string" ? entry : String(entry.label || "")
    }

    function _itemCount(entry) {
        return typeof entry === "object" && entry !== null
            ? parseInt(entry.count || 0)
            : 0
    }

    function _itemIcon(entry) {
        return typeof entry === "object" && entry !== null
            ? String(entry.icon || "")
            : ""
    }

    function _isExpanded(key) {
        if (key === "__ungrouped__" || !root._hasGroups) {
            return true
        }
        const explicitState = root._expandedGroups[key]
        return explicitState === undefined
            ? !root.groupsCollapsedByDefault
            : Boolean(explicitState)
    }

    function _setExpanded(key, expanded) {
        if (key === "__ungrouped__") {
            return
        }
        const nextState = Object.assign({}, root._expandedGroups)
        nextState[key] = Boolean(expanded)
        root._expandedGroups = nextState
    }

    function _toggleGroup(key) {
        root._setExpanded(key, !root._isExpanded(key))
    }

    function expandGroupForItem(itemIndex) {
        if (itemIndex < 0 || itemIndex >= root.items.length) {
            return
        }
        const group = root._groupLabel(root.items[itemIndex])
        if (group.length > 0) {
            root._setExpanded(group, true)
        }
    }

    onItemsChanged: root._expandedGroups = ({})

    // -- Keyboard navigation -------------------------------------------
    // Flattened, visible-only index list so Up/Down skip collapsed groups.
    readonly property var _visibleItemIndexes: {
        const indexes = []
        const groups = root._groups
        for (let g = 0; g < groups.length; g += 1) {
            const group = groups[g]
            if (!root._isExpanded(group.key)) {
                continue
            }
            for (let i = 0; i < group.items.length; i += 1) {
                indexes.push(group.items[i].itemIndex)
            }
        }
        return indexes
    }

    function _moveSelection(delta) {
        const visible = root._visibleItemIndexes
        if (visible.length === 0) {
            return
        }
        const currentPos = visible.indexOf(root.activeIndex)
        const nextPos = currentPos < 0
            ? 0
            : Math.max(0, Math.min(visible.length - 1, currentPos + delta))
        root.itemActivated(visible[nextPos])
    }

    Keys.onDownPressed: root._moveSelection(1)
    Keys.onUpPressed: root._moveSelection(-1)
    focus: true
    activeFocusOnTab: true

    Rectangle {
        anchors.right: parent.right
        width: Theme.AppTheme.borderWidthThin
        height: parent.height
        color: Theme.AppTheme.divider
    }

    // -- Optional header with rail-collapse toggle ---------------------
    Item {
        id: _header
        visible: root.showRailToggle
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        height: root.showRailToggle ? 40 : 0

        AppControls.Label {
            visible: !root._effectiveCollapsed
            anchors.left: parent.left
            anchors.leftMargin: 14
            anchors.verticalCenter: parent.verticalCenter
            anchors.right: _toggleBtn.left
            anchors.rightMargin: 4
            text: root.railTitle
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
            elide: Text.ElideRight
        }

        Rectangle {
            id: _toggleBtn
            anchors.right: parent.right
            anchors.rightMargin: 6
            anchors.verticalCenter: parent.verticalCenter
            width: 28; height: 28; radius: Theme.AppTheme.radiusSm
            color: _toggleMA.containsMouse ? Theme.AppTheme.navHoverBackground : "transparent"

            AppIcons.AppIcon {
                anchors.centerIn: parent
                name: root._effectiveCollapsed ? "chevron_right" : "chevron_left"
                size: Theme.AppTheme.iconXs
                iconColor: Theme.AppTheme.textMuted
            }

            MouseArea {
                id: _toggleMA
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.collapsed = !root.collapsed
            }
        }

        Rectangle {
            anchors { bottom: parent.bottom; left: parent.left; right: parent.right }
            height: Theme.AppTheme.borderWidthThin
            color: Theme.AppTheme.divider
        }
    }

    // -- Body -----------------------------------------------------------
    Flickable {
        id: navFlickable

        anchors.top: _header.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        anchors.margins: root._effectiveCollapsed ? Theme.AppTheme.spacingXs : Theme.AppTheme.pagePadding
        contentWidth: width
        contentHeight: navColumn.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: navColumn

            width: navFlickable.width
            spacing: Theme.AppTheme.sectionGap

            Repeater {
                model: root._groups

                delegate: Column {
                    id: navGroup

                    required property var modelData

                    width: navColumn.width
                    spacing: Theme.AppTheme.spacingXs

                    readonly property bool hasHeader: !root._effectiveCollapsed && String(navGroup.modelData.label || "").length > 0
                    readonly property bool expanded: root._isExpanded(String(navGroup.modelData.key || ""))

                    Item {
                        width: navGroup.width
                        height: navGroup.hasHeader ? Theme.AppTheme.sidebarRowHeight : 0
                        visible: navGroup.hasHeader

                        Rectangle {
                            anchors.fill: parent
                            radius: Theme.AppTheme.radiusSm
                            color: groupHover.containsMouse
                                ? Theme.AppTheme.hoverSurface
                                : Theme.AppTheme.surfaceOverlay
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: Theme.AppTheme.spacingSm
                            anchors.rightMargin: Theme.AppTheme.spacingSm
                            spacing: Theme.AppTheme.spacingXs

                            AppControls.Label {
                                Layout.fillWidth: true
                                text: String(navGroup.modelData.label || "").toUpperCase()
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                                font.bold: true
                                font.letterSpacing: 0.5
                                elide: Text.ElideRight
                            }

                            AppControls.Label {
                                text: String((navGroup.modelData.items || []).length)
                                color: Theme.AppTheme.textMuted
                                font.family: Theme.AppTheme.fontFamily
                                font.pixelSize: Theme.AppTheme.captionSize
                            }

                            AppIcons.AppIcon {
                                name: navGroup.expanded ? "chevron_down" : "chevron_right"
                                size: Theme.AppTheme.iconXs
                                iconColor: Theme.AppTheme.textMuted
                            }
                        }

                        MouseArea {
                            id: groupHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root._toggleGroup(String(navGroup.modelData.key || ""))
                        }
                    }

                    Column {
                        width: navGroup.width
                        spacing: 0
                        visible: navGroup.expanded

                        Repeater {
                            model: navGroup.modelData.items || []

                            delegate: Item {
                                id: navItem

                                required property var modelData

                                width: navGroup.width
                                height: Theme.AppTheme.sidebarRowHeight

                                readonly property int itemIndex: parseInt(navItem.modelData.itemIndex)
                                readonly property var entry: navItem.modelData.entry
                                readonly property bool isActive: root.activeIndex === navItem.itemIndex
                                readonly property string itemLabel: root._itemLabel(navItem.entry)
                                readonly property int itemCount: root._itemCount(navItem.entry)
                                readonly property string itemIcon: root._itemIcon(navItem.entry)

                                Rectangle {
                                    anchors.fill: parent
                                    anchors.leftMargin: root._effectiveCollapsed ? 0 : 4
                                    anchors.rightMargin: root._effectiveCollapsed ? 0 : 4
                                    radius: Theme.AppTheme.radiusSm
                                    color: navItem.isActive
                                        ? Theme.AppTheme.navSelectedBackground
                                        : navHover.containsMouse
                                            ? Theme.AppTheme.hoverSurface
                                            : "transparent"
                                }

                                Rectangle {
                                    anchors.left: parent.left
                                    anchors.top: parent.top
                                    anchors.bottom: parent.bottom
                                    width: 3
                                    radius: 2
                                    color: Theme.AppTheme.accent
                                    visible: navItem.isActive
                                }

                                AppIcons.AppIcon {
                                    id: _itemIco
                                    visible: navItem.itemIcon.length > 0
                                    anchors.left: parent.left
                                    anchors.leftMargin: root._effectiveCollapsed ? 13 : 11
                                    anchors.verticalCenter: parent.verticalCenter
                                    name: navItem.itemIcon.length > 0 ? navItem.itemIcon : "default"
                                    size: Theme.AppTheme.navIconSize
                                    iconColor: navItem.isActive ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
                                }

                                AppControls.Label {
                                    visible: !root._effectiveCollapsed
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: _itemIco.visible ? _itemIco.right : parent.left
                                    anchors.leftMargin: _itemIco.visible ? 9 : (navGroup.hasHeader ? 18 : 14)
                                    anchors.right: countBadge.visible ? countBadge.left : parent.right
                                    anchors.rightMargin: Theme.AppTheme.spacingSm
                                    text: navItem.itemLabel
                                    color: navItem.isActive
                                        ? Theme.AppTheme.navSelectedText
                                        : Theme.AppTheme.textSecondary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.smallSize
                                    font.bold: navItem.isActive
                                    elide: Text.ElideRight
                                }

                                Rectangle {
                                    id: countBadge
                                    anchors.right: parent.right
                                    anchors.rightMargin: Theme.AppTheme.spacingSm
                                    anchors.verticalCenter: parent.verticalCenter
                                    visible: !root._effectiveCollapsed && navItem.itemCount > 0
                                    width: countLabel.implicitWidth + 8
                                    height: 16
                                    radius: 8
                                    color: navItem.isActive
                                        ? Theme.AppTheme.accent
                                        : Theme.AppTheme.surfaceOverlay

                                    AppControls.Label {
                                        id: countLabel
                                        anchors.centerIn: parent
                                        text: String(navItem.itemCount)
                                        color: navItem.isActive
                                            ? Theme.AppTheme.textOnAccent
                                            : Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold: true
                                    }
                                }

                                ToolTip.visible: root._effectiveCollapsed && navHover.containsMouse
                                ToolTip.text: navItem.itemLabel
                                ToolTip.delay: 700

                                MouseArea {
                                    id: navHover
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.itemActivated(navItem.itemIndex)
                                }
                            }
                        }
                    }
                }
            }
        }

        ScrollBar.vertical: ScrollBar {
            policy: ScrollBar.AsNeeded
        }
    }
}
