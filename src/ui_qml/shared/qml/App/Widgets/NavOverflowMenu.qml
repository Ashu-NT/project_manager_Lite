pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

// Shared secondary-tier navigation affordance: a single "More" trigger that
// opens a small anchored list of destinations. Intended for workspaces whose
// primary tab strip is capped and want to demote lower-traffic destinations
// behind one compact control instead of a second persistent tab row.
Item {
    id: root

    // Array of { id, label, count } entries.
    property var items: []
    property string activeId: ""
    property string triggerLabel: "More"

    signal itemSelected(string id)

    readonly property var _activeItem: {
        const list = root.items || []
        for (let i = 0; i < list.length; i++) {
            if (String(list[i].id || "") === root.activeId) return list[i]
        }
        return null
    }
    readonly property bool _hasActiveItem: root._activeItem !== null

    implicitWidth: _row.implicitWidth + 22
    implicitHeight: Theme.AppTheme.inputHeight

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusSm
        color: root._hasActiveItem
            ? Theme.AppTheme.navSelectedBackground
            : _hoverArea.containsMouse
                ? Theme.AppTheme.hoverSurface
                : Theme.AppTheme.surfaceOverlay
        border.color: root._hasActiveItem ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder
        border.width: root._hasActiveItem ? 1 : 0
    }

    RowLayout {
        id: _row
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingXs

        AppControls.Label {
            text: root._hasActiveItem ? String(root._activeItem.label || "") : root.triggerLabel
            color: root._hasActiveItem ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: root._hasActiveItem
        }

        AppIcons.AppIcon {
            name: "chevron_down"
            size: Theme.AppTheme.iconXs
            iconColor: root._hasActiveItem ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textMuted
        }
    }

    MouseArea {
        id: _hoverArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: _popup.open()
    }

    AnchoredPopup {
        id: _popup
        anchorItem: root
        placement: "below-right"
        width: 220

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: root.items

                delegate: Item {
                    id: itemDelegate
                    required property var modelData

                    readonly property bool _isActive: String(itemDelegate.modelData.id || "") === root.activeId

                    Layout.fillWidth: true
                    implicitHeight: Theme.AppTheme.sidebarRowHeight

                    Rectangle {
                        anchors.fill: parent
                        visible: itemDelegate._isActive
                        color: Theme.AppTheme.navSelectedBackground
                    }

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: Theme.AppTheme.spacingSm
                        anchors.rightMargin: Theme.AppTheme.spacingSm
                        spacing: Theme.AppTheme.spacingXs

                        AppControls.Label {
                            Layout.fillWidth: true
                            text: String(itemDelegate.modelData.label || "")
                            color: itemDelegate._isActive ? Theme.AppTheme.navSelectedText : Theme.AppTheme.textPrimary
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                            font.bold: itemDelegate._isActive
                        }

                        AppControls.Label {
                            visible: parseInt(itemDelegate.modelData.count || 0, 10) > 0
                            text: String(itemDelegate.modelData.count || "")
                            color: Theme.AppTheme.textMuted
                            font.family: Theme.AppTheme.fontFamily
                            font.pixelSize: Theme.AppTheme.captionSize
                        }
                    }

                    MouseArea {
                        anchors.fill: parent
                        cursorShape: Qt.PointingHandCursor
                        onClicked: {
                            root.itemSelected(String(itemDelegate.modelData.id || ""))
                            _popup.close()
                        }
                    }
                }
            }
        }
    }
}
