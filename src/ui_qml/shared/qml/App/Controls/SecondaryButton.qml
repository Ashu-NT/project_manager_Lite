import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Button {
    id: control

    property bool danger: false
    property string iconName: ""

    implicitHeight: Theme.AppTheme.toolbarHeight
    implicitWidth: Math.max(108, contentItem.implicitWidth + 28)

    contentItem: Item {
        implicitWidth: _row.implicitWidth
        implicitHeight: _row.implicitHeight

        Row {
            id: _row
            anchors.centerIn: parent
            spacing: Theme.AppTheme.spacingXs

            AppIcons.AppIcon {
                visible: control.iconName.length > 0
                name: control.iconName.length > 0 ? control.iconName : "default"
                size: 12
                iconColor: control.danger
                    ? Theme.AppTheme.danger
                    : control.down || control.hovered || control.activeFocus
                        ? Theme.AppTheme.accent
                        : Theme.AppTheme.textSecondary
                height: _label.implicitHeight
            }

            Label {
                id: _label
                verticalAlignment: Text.AlignVCenter
                text: control.text
                color: control.danger
                    ? Theme.AppTheme.danger
                    : control.down || control.hovered || control.activeFocus
                        ? Theme.AppTheme.accent
                        : Theme.AppTheme.textSecondary
                font.family: Theme.AppTheme.fontFamily
                font.bold: true
                font.pixelSize: Theme.AppTheme.smallSize
            }
        }
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: control.down
            ? Theme.AppTheme.hoverSurface
            : control.hovered
                ? Theme.AppTheme.surfaceOverlay
                : Theme.AppTheme.surfaceRaised
        border.color: control.danger
            ? Theme.AppTheme.danger
            : control.activeFocus || control.hovered
                ? Theme.AppTheme.focusBorder
                : Theme.AppTheme.subtleBorder
        border.width: 1
    }
}
