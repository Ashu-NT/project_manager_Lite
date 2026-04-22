import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../../shared/qml/theme" as Theme

Rectangle {
    id: header
    height: 68
    radius: Theme.AppTheme.radiusLg
    color: Theme.AppTheme.accent

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: Theme.AppTheme.marginLg
        anchors.rightMargin: Theme.AppTheme.marginLg

        Label {
            text: shellContext.appTitle
            color: "#FFFFFF"
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.titleSize
            font.bold: true
        }

        Item {
            Layout.fillWidth: true
        }

        Label {
            text: shellContext.userDisplayName || "QML migration shell"
            color: Theme.AppTheme.textOnAccent
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
        }
    }
}
