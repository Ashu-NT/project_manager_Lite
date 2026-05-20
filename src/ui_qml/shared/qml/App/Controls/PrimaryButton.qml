import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Icons 1.0 as AppIcons

Button {
    id: control

    property bool danger: false
    property string iconName: ""

    implicitHeight: Theme.AppTheme.toolbarHeight
    implicitWidth: Math.max(120, contentItem.implicitWidth + 28)

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
                iconColor: "#FFFFFF"
                height: _label.implicitHeight
            }

            Label {
                id: _label
                verticalAlignment: Text.AlignVCenter
                text: control.text
                color: "#FFFFFF"
                font.family: Theme.AppTheme.fontFamily
                font.bold: true
                font.pixelSize: Theme.AppTheme.smallSize
            }
        }
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: control.danger
            ? Theme.AppTheme.danger
            : control.down
                ? Theme.AppTheme.accentPressed
                : control.hovered
                    ? Theme.AppTheme.accentHover
                    : Theme.AppTheme.accent
        border.color: control.activeFocus ? Theme.AppTheme.focusBorder : "transparent"
        border.width: control.activeFocus ? 1 : 0
    }
}
