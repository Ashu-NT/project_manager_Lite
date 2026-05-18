import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property string title: ""
    property string subtitle: ""
    default property alias actions: actionSlot.data

    implicitHeight: headerRow.implicitHeight + Theme.AppTheme.spacingMd

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: 2

        RowLayout {
            id: headerRow
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingMd

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Label {
                    Layout.fillWidth: true
                    visible: root.title.length > 0
                    text: root.title
                    color: Theme.AppTheme.textPrimary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.titleSize
                    font.bold: true
                    elide: Text.ElideRight
                }

                Label {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.smallSize
                    wrapMode: Text.WordWrap
                }
            }

            Row {
                id: actionSlot
                spacing: Theme.AppTheme.spacingSm
            }
        }

        Rectangle {
            Layout.fillWidth: true
            height: 1
            color: Theme.AppTheme.divider
        }
    }
}
