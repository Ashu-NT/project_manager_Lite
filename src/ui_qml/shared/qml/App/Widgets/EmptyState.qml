import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: "No records found"
    property string message: ""

    implicitHeight: column.implicitHeight + Theme.AppTheme.spacingLg * 2

    ColumnLayout {
        id: column
        anchors.centerIn: parent
        spacing: Theme.AppTheme.spacingSm
        width: Math.min(parent.width, 320)

        Label {
            Layout.fillWidth: true
            text: root.title
            color: Theme.AppTheme.textSecondary
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.bodySize
            font.bold: true
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }

        Label {
            Layout.fillWidth: true
            visible: root.message.length > 0
            text: root.message
            color: Theme.AppTheme.textMuted
            font.family: Theme.AppTheme.fontFamily
            font.pixelSize: Theme.AppTheme.smallSize
            horizontalAlignment: Text.AlignHCenter
            wrapMode: Text.WordWrap
        }
    }
}
