import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property string eyebrow: ""
    property string title: ""
    property string subtitle: ""
    property bool showDivider: true
    default property alias actions: actionSlot.data

    implicitHeight: headerBlock.implicitHeight + (root.showDivider ? Theme.AppTheme.spacingMd : 0)

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Theme.AppTheme.spacingSm

        RowLayout {
            id: headerBlock
            Layout.fillWidth: true
            spacing: Theme.AppTheme.spacingLg

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 3

                Label {
                    Layout.fillWidth: true
                    visible: root.eyebrow.length > 0
                    text: root.eyebrow.toUpperCase()
                    color: Theme.AppTheme.textMuted
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    font.letterSpacing: 0.8
                    elide: Text.ElideRight
                }

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
            visible: root.showDivider
        }
    }
}

