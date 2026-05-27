import QtQuick
import QtQuick.Controls
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

AppControls.Label {
    color: Theme.AppTheme.textMuted
    font.family: Theme.AppTheme.fontFamily
    font.pixelSize: Theme.AppTheme.sectionTitleSize
    font.bold: true
    font.letterSpacing: 0.6
    font.capitalization: Font.AllUppercase
}
