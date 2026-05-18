import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme

Button {
    id: control

    property bool danger: false

    implicitHeight: 38
    implicitWidth: Math.max(132, contentItem.implicitWidth + 32)

    contentItem: Label {
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        text: control.text
        color: control.danger ? Theme.AppTheme.danger : Theme.AppTheme.accent
        font.family: Theme.AppTheme.fontFamily
        font.bold: true
        font.pixelSize: Theme.AppTheme.bodySize
    }

    background: Rectangle {
        radius: Theme.AppTheme.radiusMd
        color: control.down
            ? Qt.rgba(Theme.AppTheme.accent.r, Theme.AppTheme.accent.g, Theme.AppTheme.accent.b, 0.08)
            : control.hovered
                ? Qt.rgba(Theme.AppTheme.accent.r, Theme.AppTheme.accent.g, Theme.AppTheme.accent.b, 0.05)
                : "transparent"
        border.color: control.danger ? Theme.AppTheme.danger : Theme.AppTheme.accent
        border.width: 1.5
    }
}
