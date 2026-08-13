pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Layouts
import App.Controls 1.0 as AppControls
import App.Theme 1.0 as Theme

RowLayout {
    id: root
    property string rowLabel: ""
    property string rowValue: ""

    Layout.fillWidth: true
    spacing: Theme.AppTheme.spacingXs

    AppControls.Label {
        text:              root.rowLabel
        color:             Theme.AppTheme.textMuted
        font.family:       Theme.AppTheme.fontFamily
        font.pixelSize:    Theme.AppTheme.captionSize
        font.bold:         true
        Layout.preferredWidth: 100
    }
    AppControls.Label {
        Layout.fillWidth: true
        text:           root.rowValue || "-"
        color:          Theme.AppTheme.textSecondary
        font.family:    Theme.AppTheme.fontFamily
        font.pixelSize: Theme.AppTheme.smallSize
        elide:          Text.ElideRight
    }
}
