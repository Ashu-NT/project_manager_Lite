import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme

QQC2.RadioButton {
    id: control

    spacing: Theme.AppTheme.spacingSm
    implicitHeight: Math.max(Theme.AppTheme.inputHeight, contentItem.implicitHeight)

    indicator: Rectangle {
        implicitWidth: Theme.AppTheme.iconMd + 4
        implicitHeight: Theme.AppTheme.iconMd + 4
        radius: implicitHeight / 2
        color: Theme.AppTheme.surfaceRaised
        border.width: 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.checked
                ? Theme.AppTheme.accent
                : control.hovered
                    ? Theme.AppTheme.borderStrong
                    : Theme.AppTheme.subtleBorder

        Rectangle {
            anchors.centerIn: parent
            visible: control.checked
            width: Theme.AppTheme.iconSm - 1
            height: Theme.AppTheme.iconSm - 1
            radius: width / 2
            color: Theme.AppTheme.accent
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
