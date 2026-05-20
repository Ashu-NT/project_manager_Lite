import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import App.Theme 1.0 as Theme

Item {
    id: root

    property bool open: false
    property int panelWidth: 380
    property string title: ""

    signal closeRequested()

    default property alias content: contentArea.data

    // Semi-transparent scrim
    Rectangle {
        id: scrim
        anchors.fill: parent
        color: Theme.AppTheme.overlayScrim
        opacity: root.open ? 1 : 0
        visible: opacity > 0
        z: 9

        Behavior on opacity {
            NumberAnimation { duration: 180; easing.type: Easing.InOutQuad }
        }

        MouseArea {
            anchors.fill: parent
            onClicked: root.closeRequested()
        }
    }

    // Slide-over panel from right
    Rectangle {
        id: panel
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        width: root.panelWidth
        x: root.open ? parent.width - root.panelWidth : parent.width
        color: Theme.AppTheme.surfaceRaised
        z: 10

        Rectangle {
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            width: 1
            color: Theme.AppTheme.divider
        }

        Behavior on x {
            NumberAnimation { duration: 220; easing.type: Easing.OutCubic }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Rectangle {
                Layout.fillWidth: true
                height: Theme.AppTheme.panelHeaderHeight
                color: Theme.AppTheme.surfaceRaised

                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: 1
                    color: Theme.AppTheme.divider
                }

                RowLayout {
                    anchors.fill: parent
                    anchors.leftMargin: Theme.AppTheme.marginMd
                    anchors.rightMargin: Theme.AppTheme.marginMd
                    spacing: Theme.AppTheme.spacingSm

                    Label {
                        Layout.fillWidth: true
                        text: root.title
                        color: Theme.AppTheme.textPrimary
                        font.family: Theme.AppTheme.fontFamily
                        font.pixelSize: Theme.AppTheme.bodySize
                        font.bold: true
                        elide: Text.ElideRight
                    }

                    Rectangle {
                        width: Theme.AppTheme.inputHeight
                        height: Theme.AppTheme.inputHeight
                        radius: Theme.AppTheme.radiusSm
                        color: closeHover.containsMouse
                            ? Theme.AppTheme.hoverSurface
                            : Theme.AppTheme.surfaceOverlay

                        Label {
                            anchors.centerIn: parent
                            text: "✕"
                            color: Theme.AppTheme.textMuted
                            font.pixelSize: Theme.AppTheme.captionSize
                            font.family: Theme.AppTheme.fontFamily
                        }

                        MouseArea {
                            id: closeHover
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: root.closeRequested()
                        }
                    }
                }
            }

            // Content area — children of SlideOverPanel go here
            Item {
                id: contentArea
                Layout.fillWidth: true
                Layout.fillHeight: true
            }
        }
    }
}
