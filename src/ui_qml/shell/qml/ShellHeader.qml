import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Shell.Context 1.0 as ShellContexts
import App.Theme 1.0 as Theme

Rectangle {
    id: header
    property ShellContexts.ShellContext shellModel

    height: 68
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.accent

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginLg
        anchors.rightMargin: Theme.AppTheme.marginLg

        Label {
            text: header.shellModel ? header.shellModel.appTitle : "TECHASH Enterprise"
            color: "#FFFFFF"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.titleSize
            font.bold: true
        }

        Item {
            Layout.fillWidth: true
        }

        Label {
            text: header.shellModel
                ? (header.shellModel.userDisplayName || "QML migration shell")
                : "QML migration shell"
            color: Theme.AppTheme.textOnAccent
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
        }
    }
}
