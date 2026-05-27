import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme

QQC2.Switch {
    id: control

    spacing: Theme.AppTheme.spacingSm
    implicitHeight: Math.max(Theme.AppTheme.inputHeight, contentItem.implicitHeight)

    indicator: Rectangle {
        implicitWidth: 42
        implicitHeight: 24
        radius: implicitHeight / 2
        color: control.checked
            ? Theme.AppTheme.accent
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.checked
                ? Theme.AppTheme.accent
                : control.hovered
                    ? Theme.AppTheme.borderStrong
                    : Theme.AppTheme.subtleBorder

        Rectangle {
            x: control.checked
                ? parent.width - width - 2
                : 2
            y: 2
            width: parent.height - 4
            height: parent.height - 4
            radius: width / 2
            color: Theme.AppTheme.surfaceRaised

            Behavior on x {
                NumberAnimation { duration: 140; easing.type: Easing.OutCubic }
            }
        }
    }

    contentItem: Text {
        leftPadding: control.indicator.width + control.spacing
        text: control.text
        color: control.enabled
            ? Theme.AppTheme.textPrimary
            : Theme.AppTheme.textMuted
        font.family: Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.bodySize
        verticalAlignment: Text.AlignVCenter
        wrapMode: Text.WordWrap
    }
}
