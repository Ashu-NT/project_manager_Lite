pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

// Shared entity-header "Actions" overflow menu: a single trigger button
// that opens a small anchored list of commands. Distinct from NavOverflowMenu
// (a navigation-destination picker) -- this is for imperative record actions
// (edit, lifecycle transitions, ...), each firing actionSelected(id) once.
//
// items: [{ id, label, icon, danger, enabled, separator }]. A `separator:
// true` entry renders a divider line and ignores every other field -- used
// to group related commands (e.g. a lifecycle transition block) apart from
// the rest of the menu.
Item {
    id: root

    property var items: []
    property string triggerLabel: "Actions"
    property bool enabled: true

    signal actionSelected(string id)

    implicitWidth: _row.implicitWidth + 22
    implicitHeight: Theme.AppTheme.inputHeight

    activeFocusOnTab: root.enabled
    Accessible.role: Accessible.Button
    Accessible.name: root.triggerLabel
    Accessible.onPressAction: { if (root.enabled) _popup.open() }
    Keys.onPressed: (event) => {
        if (!root.enabled) return
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            _popup.open()
            event.accepted = true
        }
    }

    Rectangle {
        anchors.fill: parent
        radius: Theme.AppTheme.radiusSm
        opacity: root.enabled ? 1.0 : 0.5
        color: _hoverArea.containsMouse ? Theme.AppTheme.hoverSurface : Theme.AppTheme.surfaceOverlay
        border.color: root.activeFocus ? Theme.AppTheme.focusBorder : Theme.AppTheme.subtleBorder
        border.width: root.activeFocus ? 2 : 1
    }

    RowLayout {
        id: _row
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingXs

        AppControls.Label {
            text: root.triggerLabel
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
        }

        AppIcons.AppIcon {
            name: "chevron_down"
            size: Theme.AppTheme.iconXs
            iconColor: Theme.AppTheme.textMuted
        }
    }

    MouseArea {
        id: _hoverArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        enabled: root.enabled
        onClicked: _popup.open()
    }

    AnchoredPopup {
        id: _popup
        anchorItem: root
        placement: "below-right"
        width: 240

        contentItem: ColumnLayout {
            spacing: Theme.AppTheme.spacingXs

            Repeater {
                model: root.items

                delegate: Loader {
                    id: entryLoader
                    required property var modelData
                    Layout.fillWidth: true

                    sourceComponent: (entryLoader.modelData && entryLoader.modelData.separator === true)
                        ? _separatorComponent
                        : _itemComponent

                    property var entryData: entryLoader.modelData

                    Component {
                        id: _separatorComponent
                        Rectangle {
                            Layout.fillWidth: true
                            Layout.topMargin: Theme.AppTheme.spacingXs
                            Layout.bottomMargin: Theme.AppTheme.spacingXs
                            implicitHeight: 1
                            color: Theme.AppTheme.divider
                        }
                    }

                    Component {
                        id: _itemComponent
                        Item {
                            id: itemDelegate
                            readonly property var entry: entryLoader.entryData
                            readonly property bool _itemEnabled: itemDelegate.entry && itemDelegate.entry.enabled !== false

                            Layout.fillWidth: true
                            implicitHeight: Theme.AppTheme.sidebarRowHeight

                            activeFocusOnTab: itemDelegate._itemEnabled
                            Accessible.role: Accessible.MenuItem
                            Accessible.name: String((itemDelegate.entry && itemDelegate.entry.label) || "")
                            Accessible.onPressAction: itemDelegate._trigger()
                            Keys.onPressed: (event) => {
                                if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
                                    itemDelegate._trigger()
                                    event.accepted = true
                                }
                            }

                            function _trigger() {
                                if (!itemDelegate._itemEnabled) return
                                root.actionSelected(String((itemDelegate.entry && itemDelegate.entry.id) || ""))
                                _popup.close()
                            }

                            Rectangle {
                                anchors.fill: parent
                                visible: itemDelegate.activeFocus || _itemHover.containsMouse
                                color: Theme.AppTheme.hoverSurface
                                border.width: itemDelegate.activeFocus ? 2 : 0
                                border.color: Theme.AppTheme.focusBorder
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: Theme.AppTheme.spacingSm
                                anchors.rightMargin: Theme.AppTheme.spacingSm
                                spacing: Theme.AppTheme.spacingXs

                                AppIcons.AppIcon {
                                    visible: String((itemDelegate.entry && itemDelegate.entry.icon) || "").length > 0
                                    name: String((itemDelegate.entry && itemDelegate.entry.icon) || "")
                                    size: Theme.AppTheme.iconXs
                                    iconColor: !itemDelegate._itemEnabled
                                        ? Theme.AppTheme.textMuted
                                        : (itemDelegate.entry && itemDelegate.entry.danger === true)
                                            ? Theme.AppTheme.error
                                            : Theme.AppTheme.textSecondary
                                }

                                AppControls.Label {
                                    Layout.fillWidth: true
                                    text: String((itemDelegate.entry && itemDelegate.entry.label) || "")
                                    color: !itemDelegate._itemEnabled
                                        ? Theme.AppTheme.textMuted
                                        : (itemDelegate.entry && itemDelegate.entry.danger === true)
                                            ? Theme.AppTheme.error
                                            : Theme.AppTheme.textPrimary
                                    font.family: Theme.AppTheme.fontFamily
                                    font.pixelSize: Theme.AppTheme.typeSupportingTextSize
                                }
                            }

                            MouseArea {
                                id: _itemHover
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: itemDelegate._itemEnabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                                onClicked: itemDelegate._trigger()
                            }
                        }
                    }
                }
            }
        }
    }
}
