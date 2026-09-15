pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Icons 1.0 as AppIcons
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

// Shell-header organization switcher. With exactly one accessible
// organization it shows the current organization context as a plain,
// non-interactive label -- never a dropdown with nothing to choose.
Rectangle {
    id: root

    // Shell.Controllers.OrganizationSwitcherController
    property var controller: null

    readonly property var _organizations: root.controller ? (root.controller.organizations || []) : []
    readonly property string _activeId: root.controller ? root.controller.activeOrganizationId : ""
    readonly property bool _isMulti: root.controller ? root.controller.isMultiOrganization === true : false

    readonly property string _activeName: {
        const list = root._organizations
        for (let i = 0; i < list.length; i++) {
            if (list[i].id === root._activeId) {
                return String(list[i].displayName || list[i].organizationCode || "")
            }
        }
        return ""
    }

    visible: root._activeName.length > 0
    implicitWidth: visible ? (orgRow.implicitWidth + Theme.AppTheme.spacingMd) : 0
    implicitHeight: Theme.AppTheme.inputHeight
    radius: Theme.AppTheme.radiusSm
    color: root._isMulti && (switchHover.containsMouse || root.activeFocus)
        ? Theme.AppTheme.hoverSurface
        : Theme.AppTheme.surfaceOverlay
    border.width: root.activeFocus && root._isMulti ? 2 : 0
    border.color: Theme.AppTheme.focusBorder

    Behavior on color { ColorAnimation { duration: 100 } }

    // -- Keyboard / accessibility -------------------------------------
    activeFocusOnTab: root._isMulti
    Accessible.role: root._isMulti ? Accessible.Button : Accessible.StaticText
    Accessible.name: "Organization: " + root._activeName
    Accessible.onPressAction: {
        if (root._isMulti) {
            orgMenu.open()
        }
    }

    Keys.onPressed: (event) => {
        if (!root._isMulti) {
            return
        }
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            orgMenu.open()
            event.accepted = true
        }
    }

    RowLayout {
        id: orgRow
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingXs

        AppIcons.AppIcon {
            name: "organization"
            size: Theme.AppTheme.iconSm
            iconColor: Theme.AppTheme.textMuted
        }

        AppControls.Label {
            text: root._activeName
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
            elide: Text.ElideRight
            maximumLineCount: 1
        }

        AppIcons.AppIcon {
            visible: root._isMulti
            name: "chevron_down"
            size: Theme.AppTheme.iconSm
            iconColor: Theme.AppTheme.textMuted
        }
    }

    MouseArea {
        id: switchHover
        anchors.fill: parent
        hoverEnabled: true
        enabled: root._isMulti
        cursorShape: root._isMulti ? Qt.PointingHandCursor : Qt.ArrowCursor
        onClicked: {
            root.forceActiveFocus()
            orgMenu.open()
        }
    }

    Menu {
        id: orgMenu
        y: root.height + 4

        Repeater {
            model: root._organizations

            delegate: MenuItem {
                id: _item
                required property var modelData

                readonly property bool _isCurrent: root._activeId === _item.modelData.id
                readonly property bool _canSwitch: _item.modelData.isEnabled === true

                text: _item.modelData.displayName || _item.modelData.organizationCode || ""
                enabled: _item._canSwitch && !_item._isCurrent
                checkable: true
                checked: _item._isCurrent

                onTriggered: {
                    if (!_item._canSwitch || _item._isCurrent) {
                        return
                    }
                    if (root.controller) {
                        root.controller.switchToOrganization(_item.modelData.id)
                    }
                }
            }
        }
    }

    ToolTip {
        visible: switchHover.containsMouse && root._isMulti
        text: "Switch organization"
        delay: 400
    }
}
