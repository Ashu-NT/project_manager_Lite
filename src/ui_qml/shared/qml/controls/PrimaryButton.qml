import QtQuick
import QtQuick.Controls
import "../theme" as Theme

Button {
    id: control

    property bool danger: false

    implicitHeight: 38
    implicitWidth: Math.max(132, contentItem.implicitWidth + 32)

    contentItem: Label {
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        text: control.text
        color: "#FFFFFF"
        font.family: Theme.AppTheme.fontFamily
        font.bold: true
        font.pixelSize: Theme.AppTheme.bodySize
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusMd
        color: control.danger
            ? Theme.AppTheme.danger
            : control.down
                ? Theme.AppTheme.accentPressed
                : control.hovered
                    ? Theme.AppTheme.accentHover
                    : Theme.AppTheme.accent
    }
}
