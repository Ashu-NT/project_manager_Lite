import QtQuick
import QtQuick.Controls as QQC2
import App.Theme 1.0 as Theme

QQC2.Label {
    id: control

    color: enabled
        ? Theme.AppTheme.textPrimary
        : Theme.AppTheme.textMuted
    font.family: Theme.AppTheme.fontFamily
    font.pixelSize: Theme.AppTheme.bodySize
    linkColor: Theme.AppTheme.accent
    verticalAlignment: Text.AlignVCenter
    renderType: Text.NativeRendering
}
