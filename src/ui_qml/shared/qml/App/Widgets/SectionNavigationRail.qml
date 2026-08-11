pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    property var sections: []
    property int activeSectionIndex: 0
    property bool groupsCollapsedByDefault: true
    property var _expandedGroups: ({})

    signal sectionRequested(int index)

    color: Theme.AppTheme.surfaceRaised

    readonly property bool _hasGroups: {
        const entries = root.sections || []
        for (let index = 0; index < entries.length; index += 1) {
            if (root._groupLabel(entries[index]).length > 0) {
                return true
            }
        }
        return false
    }

    readonly property var _groups: {
        const entries = root.sections || []
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
            groups[groupIndex].items.push({ "sectionIndex": index, "entry": entry })
        }
        return groups
    }

    function _groupLabel(entry) {
        return typeof entry === "object" && entry !== null
            ? String(entry.group || "").trim()
            : ""
    }

    function _sectionLabel(entry) {
        return typeof entry === "string" ? entry : String(entry.label || "")
    }

    function _sectionCount(entry) {
        return typeof entry === "object" && entry !== null
            ? parseInt(entry.count || 0)
            : 0
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

    function expandGroupForSection(sectionIndex) {
        if (sectionIndex < 0 || sectionIndex >= root.sections.length) {
            return
        }
        const group = root._groupLabel(root.sections[sectionIndex])
        if (group.length > 0) {
            root._setExpanded(group, true)
        }
    }

    onSectionsChanged: root._expandedGroups = ({})

    Rectangle {
        anchors.right: parent.right
        width: 1
        height: parent.height
        color: Theme.AppTheme.divider
    }

    Flickable {
        id: navFlickable

        anchors.fill: parent
        anchors.margins: Theme.AppTheme.pagePadding
        contentWidth: width
        contentHeight: navColumn.implicitHeight
        boundsBehavior: Flickable.StopAtBounds
        clip: true

        Column {
            id: navColumn

            width: navFlickable.width
            spacing: Theme.AppTheme.sectionGap

            AppControls.Label {
                width: parent.width
                visible: root.sections.length > 0
                text: "SECTIONS"
                color: Theme.AppTheme.textMuted
                font.family: Theme.AppTheme.fontFamily
                font.pixelSize: Theme.AppTheme.captionSize
                font.bold: true
                font.letterSpacing: 0.8
            }

            Repeater {
                model: root._groups

                delegate: Column {
                    id: navGroup

                    required property var modelData

                    width: navColumn.width
                    spacing: Theme.AppTheme.spacingXs

                    readonly property bool hasHeader: String(navGroup.modelData.label || "").length > 0
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

                                readonly property int sectionIndex: parseInt(navItem.modelData.sectionIndex)
                                readonly property var entry: navItem.modelData.entry
                                readonly property bool isActive: root.activeSectionIndex === navItem.sectionIndex
                                readonly property string sectionLabel: root._sectionLabel(navItem.entry)
                                readonly property int sectionCount: root._sectionCount(navItem.entry)

                                Rectangle {
                                    anchors.fill: parent
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

                                AppControls.Label {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: navGroup.hasHeader ? 18 : 14
                                    anchors.right: countBadge.visible ? countBadge.left : parent.right
                                    anchors.rightMargin: Theme.AppTheme.spacingSm
                                    text: navItem.sectionLabel
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
                                    visible: navItem.sectionCount > 0
                                    width: countLabel.implicitWidth + 8
                                    height: 16
                                    radius: 8
                                    color: navItem.isActive
                                        ? Theme.AppTheme.accent
                                        : Theme.AppTheme.surfaceOverlay

                                    AppControls.Label {
                                        id: countLabel

                                        anchors.centerIn: parent
                                        text: String(navItem.sectionCount)
                                        color: navItem.isActive
                                            ? Theme.AppTheme.textOnAccent
                                            : Theme.AppTheme.textMuted
                                        font.family: Theme.AppTheme.fontFamily
                                        font.pixelSize: Theme.AppTheme.captionSize
                                        font.bold: true
                                    }
                                }

                                MouseArea {
                                    id: navHover

                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.sectionRequested(navItem.sectionIndex)
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
