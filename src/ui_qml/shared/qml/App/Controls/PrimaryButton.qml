import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Button {
    id: control

    property bool danger: false

    implicitHeight: Theme.AppTheme.toolbarHeight
    implicitWidth: Math.max(120, contentItem.implicitWidth + 28)

    contentItem: Label {
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        text: control.text
        color: "#FFFFFF"
        font.family: Theme.AppTheme.fontFamily
        font.bold: true
        font.pixelSize: Theme.AppTheme.smallSize
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
