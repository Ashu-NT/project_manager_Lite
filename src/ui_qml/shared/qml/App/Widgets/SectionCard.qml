import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Rectangle {
    id: root

    property string title: ""
    property string actionLabel: ""
    default property alias content: contentArea.data

    signal actionClicked()

    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surface
    border.color: Theme.AppTheme.border
    border.width: 1
    clip: true

    ColumnLayout {
        anchors.fill: parent
        spacing: 0

        // Header strip
        Rectangle {
            Layout.fillWidth: true
            height: 32
            color: Theme.AppTheme.surfaceAlt

            RowLayout {
                anchors.fill: parent
                anchors.leftMargin: Theme.AppTheme.spacingMd
                anchors.rightMargin: Theme.AppTheme.spacingSm
                spacing: Theme.AppTheme.spacingSm

                Label {
                    Layout.fillWidth: true
                    text: root.title
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.captionSize
                    font.bold: true
                    elide: Text.ElideRight
                }

                // Action button
                Rectangle {
                    visible: root.actionLabel !== ""
                    implicitWidth: actionText.implicitWidth + 12
                    height: 22
                    radius: 3
                    color: actionHover.containsMouse ? Theme.AppTheme.accentSoft : "transparent"
                    border.color: actionHover.containsMouse ? Theme.AppTheme.accent : "transparent"
                    border.width: 1

                    Label {
                        id: actionText
                        anchors.centerIn: parent
                        text: root.actionLabel
                        color: Theme.AppTheme.accent
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.captionSize
                        font.bold: true
                    }

                    MouseArea {
                        id: actionHover
                        anchors.fill: parent
                        hoverEnabled: true
                        cursorShape: Qt.PointingHandCursor
                        onClicked: root.actionClicked()
                    }
                }
            }

            // Bottom border of header
            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.AppTheme.border
            }
        }

        // Content area
        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.fillHeight: true
        }
    }
}
