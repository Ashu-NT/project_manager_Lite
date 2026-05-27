import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme

QQC2.TextField {
    id: control

    implicitHeight: Theme.AppTheme.inputHeight
    leftPadding: Theme.AppTheme.spacingSm + 2
    rightPadding: Theme.AppTheme.spacingSm + 2
    topPadding: 0
    bottomPadding: 0
    verticalAlignment: TextInput.AlignVCenter
    color: enabled
        ? Theme.AppTheme.textPrimary
        : Theme.AppTheme.textMuted
    placeholderTextColor: Theme.AppTheme.textMuted
    selectedTextColor: Theme.AppTheme.textPrimary
    selectionColor: Theme.AppTheme.accentSoft
    font.family: Theme.AppTheme.fontFamily
    font.pixelSize: Theme.AppTheme.bodySize

    background: Rectangle {
        radius: Theme.AppTheme.radiusSm
        color: control.enabled
            ? Theme.AppTheme.surfaceRaised
            : Theme.AppTheme.surfaceOverlay
        border.width: 1
        border.color: control.activeFocus
            ? Theme.AppTheme.focusBorder
            : control.hovered
                ? Theme.AppTheme.borderStrong
                : Theme.AppTheme.subtleBorder
    }
}
