import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Button {
    id: control

    property bool danger: false
    property string iconName: ""
    readonly property color _accentColor: control.down
        ? Theme.AppTheme.accentPressed
        : control.hovered || control.activeFocus
            ? Theme.AppTheme.accentHover
            : Theme.AppTheme.textSecondary

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
                size: Theme.AppTheme.buttonIconSize
                iconColor: control.danger
                    ? Theme.AppTheme.danger
                    : control._accentColor
                height: _label.implicitHeight
            }

            Label {
                id: _label
                verticalAlignment: Text.AlignVCenter
                text: control.text
                color: control.danger
                    ? Theme.AppTheme.danger
                    : control._accentColor
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
            : control.activeFocus
                ? Theme.AppTheme.focusBorder
                : control.hovered
                    ? Theme.AppTheme.borderStrong
                    : Theme.AppTheme.subtleBorder
        border.width: 1
    }
}
