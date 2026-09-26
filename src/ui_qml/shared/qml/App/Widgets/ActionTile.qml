pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons
import App.Controls 1.0 as AppControls

// Compact interactive action affordance: icon + label + optional chevron.
// For short lists of real navigable actions (e.g. Detail Overview's
// "Related Actions") laid out in a responsive row/wrap/stack -- never a
// plain text link. Not a substitute for ModuleCard, which carries a
// description/summary and is sized for a full destination tile.
Rectangle {
    id: root

    property string label: ""
    property string iconName: ""
    property bool showChevron: true

    signal activated()

    readonly property bool _highlighted: root.activeFocus || _hover.hovered

    implicitHeight: Theme.AppTheme.normalRowHeight
    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceOverlay
    border.width: root.activeFocus ? 2 : 1
    border.color: root.activeFocus
        ? Theme.AppTheme.focusBorder
        : (_hover.hovered ? Theme.AppTheme.accent : Theme.AppTheme.subtleBorder)

    Behavior on border.color { ColorAnimation { duration: 120 } }

    activeFocusOnTab: true
    Accessible.role: Accessible.Button
    Accessible.name: root.label
    Accessible.onPressAction: root.activated()

    Keys.onPressed: (event) => {
        if (event.key === Qt.Key_Return || event.key === Qt.Key_Enter || event.key === Qt.Key_Space) {
            root.activated()
            event.accepted = true
        }
    }

    RowLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: Theme.AppTheme.spacingSm
        anchors.rightMargin: Theme.AppTheme.spacingSm
        spacing: Theme.AppTheme.spacingSm

        AppIcons.AppIcon {
            visible: root.iconName.length > 0
            Layout.alignment: Qt.AlignVCenter
            name: root.iconName
            iconColor: root._highlighted ? Theme.AppTheme.accent : Theme.AppTheme.textSecondary
            size: Theme.AppTheme.iconMd
        }

        AppControls.Label {
            Layout.fillWidth: true
            text: root.label
            color: Theme.AppTheme.textPrimary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            font.bold: true
            elide: Text.ElideRight
        }

        AppIcons.AppIcon {
            visible: root.showChevron
            Layout.alignment: Qt.AlignVCenter
            name: "chevron_right"
            size: Theme.AppTheme.iconSm
            iconColor: root._highlighted ? Theme.AppTheme.accent : Theme.AppTheme.textMuted
        }
    }

    HoverHandler {
        id: _hover
        cursorShape: Qt.PointingHandCursor
    }

    TapHandler {
        onTapped: {
            root.forceActiveFocus()
            root.activated()
        }
    }
}
