import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme
import App.Controls 1.0 as AppControls

Rectangle {
    id: root

    property string title: ""
    property string actionLabel: ""
    property bool outlined: false
    default property alias content: contentArea.data

    signal actionClicked()

    implicitWidth: cardLayout.implicitWidth
    implicitHeight: cardLayout.implicitHeight
    radius: Theme.AppTheme.radiusMd
    color: Theme.AppTheme.surfaceRaised
    border.color: root.outlined ? Theme.AppTheme.borderStrong : Theme.AppTheme.subtleBorder
    border.width: 1
    clip: true

    ColumnLayout {
        id: cardLayout
        anchors.fill: parent
        spacing: 0

        Item {
            Layout.fillWidth: true
            implicitHeight: headerRow.implicitHeight + (Theme.AppTheme.spacingMd * 2)
            visible: root.title.length > 0 || root.actionLabel.length > 0

            RowLayout {
                id: headerRow
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.top: parent.top
                anchors.topMargin: Theme.AppTheme.spacingMd
                anchors.leftMargin: Theme.AppTheme.marginMd
                anchors.rightMargin: Theme.AppTheme.marginMd
                spacing: Theme.AppTheme.spacingSm

                AppControls.Label {
                    Layout.fillWidth: true
                    text: root.title
                    color: Theme.AppTheme.textSecondary
                    font.family: Theme.AppTheme.fontFamily
                    font.pixelSize: Theme.AppTheme.sectionTitleSize
                    font.bold: true
                    font.letterSpacing: 0.5
                    elide: Text.ElideRight
                }

                Rectangle {
                    visible: root.actionLabel !== ""
                    implicitWidth: actionText.implicitWidth + 14
                    implicitHeight: 24
                    radius: Theme.AppTheme.radiusSm
                    color: actionHover.containsMouse
                        ? Theme.AppTheme.hoverSurface
                        : Theme.AppTheme.surfaceOverlay

                    AppControls.Label {
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

            Rectangle {
                anchors.left: parent.left
                anchors.right: parent.right
                anchors.bottom: parent.bottom
                height: 1
                color: Theme.AppTheme.divider
            }
        }

        Item {
            id: contentArea
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(childrenRect.height, 0)
            implicitHeight: Math.max(childrenRect.height, 0)
        }
    }
}
